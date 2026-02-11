import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
    WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")
    ENABLE_TRANSCRIPTION = os.getenv("ENABLE_TRANSCRIPTION", "true").lower() == "true"

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1MB
    RATE_LIMIT = os.getenv("RATE_LIMIT", "5 per minute")
