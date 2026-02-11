import json
import logging
import os
from dataclasses import dataclass, field

from config import Config
from downloader import download_video, enumerate_profile_videos, extract_audio, save_metadata
from transcriber import transcribe_audio
from utils import ensure_directory, extract_profile_name

logger = logging.getLogger(__name__)


@dataclass
class PipelineEvent:
    type: str  # "info", "progress", "error", "complete"
    message: str
    current: int = 0
    total: int = 0
    video_id: str = ""
    extra: dict = field(default_factory=dict)

    def to_sse(self) -> str:
        data = {
            "type": self.type,
            "message": self.message,
            "current": self.current,
            "total": self.total,
            "video_id": self.video_id,
        }
        if self.extra:
            data["extra"] = self.extra
        return f"data: {json.dumps(data)}\n\n"


def run_profile_pipeline(url: str, config: Config):
    """Generator that yields PipelineEvents for the full download pipeline."""
    profile_name = extract_profile_name(url)
    yield PipelineEvent("info", f"Fetching video list for @{profile_name}...")

    # Phase 1: Enumerate videos
    try:
        videos = enumerate_profile_videos(url)
    except Exception as e:
        logger.exception("Failed to enumerate videos")
        yield PipelineEvent("error", f"Failed to fetch video list: {e}")
        return

    total = len(videos)
    if total == 0:
        yield PipelineEvent("complete", "No videos found for this profile.")
        return

    yield PipelineEvent("info", f"Found {total} video(s). Starting downloads...", total=total)

    # Phase 2: Process each video
    # Files are organized by type: videos/, audio/, metadata/, captions/, transcripts/
    profile_dir = os.path.join(config.DOWNLOAD_DIR, "tiktok", profile_name)
    videos_dir = os.path.join(profile_dir, "videos")
    audio_dir = os.path.join(profile_dir, "audio")
    metadata_dir = os.path.join(profile_dir, "metadata")
    captions_dir = os.path.join(profile_dir, "captions")
    transcripts_dir = os.path.join(profile_dir, "transcripts")
    for d in (videos_dir, audio_dir, metadata_dir, captions_dir, transcripts_dir):
        ensure_directory(d)

    success_count = 0
    for idx, info in enumerate(videos, start=1):
        video_id = str(info.get("id", f"unknown_{idx}"))
        title = info.get("title", "Untitled")[:80]

        yield PipelineEvent(
            "progress",
            f"[{idx}/{total}] Downloading: {title}",
            current=idx,
            total=total,
            video_id=video_id,
        )

        has_error = False

        # Download video
        try:
            video_path = download_video(info, videos_dir, video_id)
        except Exception as e:
            logger.exception("Failed to download video %s", video_id)
            yield PipelineEvent("error", f"[{idx}/{total}] Download failed: {e}", current=idx, total=total, video_id=video_id)
            continue

        # Extract audio
        audio_path = os.path.join(audio_dir, f"{video_id}.mp3")
        try:
            extract_audio(video_path, audio_path)
        except Exception as e:
            logger.exception("Failed to extract audio for %s", video_id)
            yield PipelineEvent("error", f"[{idx}/{total}] Audio extraction failed: {e}", current=idx, total=total, video_id=video_id)
            has_error = True

        # Save metadata + caption
        try:
            save_metadata(info, metadata_dir, captions_dir, video_id)
        except Exception as e:
            logger.exception("Failed to save metadata for %s", video_id)
            yield PipelineEvent("error", f"[{idx}/{total}] Metadata save failed: {e}", current=idx, total=total, video_id=video_id)
            has_error = True

        # Transcribe
        if config.ENABLE_TRANSCRIPTION and os.path.isfile(audio_path):
            transcript_path = os.path.join(transcripts_dir, f"{video_id}.txt")
            try:
                yield PipelineEvent(
                    "progress",
                    f"[{idx}/{total}] Transcribing: {title}",
                    current=idx,
                    total=total,
                    video_id=video_id,
                )
                transcribe_audio(
                    audio_path,
                    transcript_path,
                    model_name=config.WHISPER_MODEL,
                    language=config.WHISPER_LANGUAGE,
                )
            except Exception as e:
                logger.exception("Failed to transcribe %s", video_id)
                yield PipelineEvent("error", f"[{idx}/{total}] Transcription failed: {e}", current=idx, total=total, video_id=video_id)
                has_error = True

        if not has_error:
            success_count += 1
        yield PipelineEvent(
            "progress",
            f"[{idx}/{total}] Complete: {title}",
            current=idx,
            total=total,
            video_id=video_id,
        )

    yield PipelineEvent(
        "complete",
        f"Done! {success_count}/{total} videos processed successfully.",
        current=total,
        total=total,
    )
