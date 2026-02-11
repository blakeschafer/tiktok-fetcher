import json
import logging
import os
import subprocess

import yt_dlp

logger = logging.getLogger(__name__)


def enumerate_profile_videos(url: str) -> list[dict]:
    """Extract video info from a TikTok profile without downloading."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return []

    # Profile pages return a playlist of entries
    entries = info.get("entries")
    if entries is None:
        # Single video URL — wrap it
        return [info]

    # entries can be a generator, materialize it
    return [e for e in entries if e is not None]


def download_video(info_dict: dict, output_dir: str) -> str:
    """Download a single video to output_dir/video.mp4. Returns the file path."""
    video_url = info_dict.get("webpage_url") or info_dict.get("url")
    output_path = os.path.join(output_dir, "video.mp4")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": os.path.join(output_dir, "video.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    # yt-dlp may produce video.mp4 or merge to it
    if os.path.isfile(output_path):
        return output_path

    # Fallback: find whatever video file was created
    for f in os.listdir(output_dir):
        if f.startswith("video.") and not f.endswith(".part"):
            return os.path.join(output_dir, f)

    raise FileNotFoundError(f"Video file not found in {output_dir}")


def extract_audio(video_path: str, audio_path: str) -> str:
    """Extract audio from video to mp3 using ffmpeg. Returns audio path."""
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "2",
        "-y",
        audio_path,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return audio_path


def save_metadata(info_dict: dict, output_dir: str) -> None:
    """Save metadata.json and caption.txt from video info."""
    metadata_path = os.path.join(output_dir, "metadata.json")
    metadata = {
        "id": info_dict.get("id"),
        "title": info_dict.get("title"),
        "description": info_dict.get("description"),
        "uploader": info_dict.get("uploader"),
        "uploader_id": info_dict.get("uploader_id"),
        "upload_date": info_dict.get("upload_date"),
        "duration": info_dict.get("duration"),
        "view_count": info_dict.get("view_count"),
        "like_count": info_dict.get("like_count"),
        "comment_count": info_dict.get("comment_count"),
        "webpage_url": info_dict.get("webpage_url"),
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    caption = info_dict.get("description") or info_dict.get("title") or ""
    caption_path = os.path.join(output_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption)
