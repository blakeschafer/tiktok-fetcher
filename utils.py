import os
import re
from urllib.parse import urlparse


TIKTOK_HOSTNAMES = {
    "www.tiktok.com",
    "tiktok.com",
    "m.tiktok.com",
    "vm.tiktok.com",
}

PROFILE_PATTERN = re.compile(r"^/@[\w.-]+/?$")


def validate_tiktok_url(url: str) -> str | None:
    """Validate a TikTok URL. Returns error message or None if valid."""
    if not url or not isinstance(url, str):
        return "URL is required"

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return "URL must start with http:// or https://"

    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL format"

    if parsed.hostname not in TIKTOK_HOSTNAMES:
        return f"Not a TikTok URL. Allowed hosts: {', '.join(sorted(TIKTOK_HOSTNAMES))}"

    if not PROFILE_PATTERN.match(parsed.path):
        return "URL must be a TikTok profile (e.g. https://www.tiktok.com/@username)"

    return None


def sanitize_filename(name: str) -> str:
    """Remove unsafe characters from a filename."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(". ")
    return name or "unnamed"


def extract_profile_name(url: str) -> str:
    """Extract the @username from a TikTok profile URL."""
    parsed = urlparse(url.strip())
    # path is like /@username
    name = parsed.path.lstrip("/").lstrip("@")
    return sanitize_filename(name)


def ensure_directory(path: str) -> str:
    """Create directory if it doesn't exist. Returns the path."""
    os.makedirs(path, exist_ok=True)
    return path


def list_downloads(base_dir: str) -> list[dict]:
    """List all downloaded profiles and their videos.

    Scans the type-based folder structure:
        tiktok/{profile}/videos/{id}.mp4
        tiktok/{profile}/audio/{id}.mp3
        tiktok/{profile}/metadata/{id}.json
        tiktok/{profile}/captions/{id}.txt
        tiktok/{profile}/transcripts/{id}.txt
    """
    tiktok_dir = os.path.join(base_dir, "tiktok")
    if not os.path.isdir(tiktok_dir):
        return []

    # Folders to scan and their label for display
    type_folders = ["videos", "audio", "metadata", "captions", "transcripts"]

    profiles = []
    for profile_name in sorted(os.listdir(tiktok_dir)):
        profile_path = os.path.join(tiktok_dir, profile_name)
        if not os.path.isdir(profile_path):
            continue

        # Collect all video IDs and their files across type folders
        video_files: dict[str, list[dict]] = {}
        for folder in type_folders:
            folder_path = os.path.join(profile_path, folder)
            if not os.path.isdir(folder_path):
                continue
            for f in sorted(os.listdir(folder_path)):
                filepath = os.path.join(folder_path, f)
                if not os.path.isfile(filepath):
                    continue
                video_id = os.path.splitext(f)[0]
                video_files.setdefault(video_id, []).append({
                    "name": f"{folder}/{f}",
                    "size": os.path.getsize(filepath),
                    "path": os.path.join("tiktok", profile_name, folder, f),
                })

        videos = [
            {"id": vid, "files": files}
            for vid, files in sorted(video_files.items())
        ]

        if videos:
            profiles.append({"name": profile_name, "videos": videos})

    return profiles
