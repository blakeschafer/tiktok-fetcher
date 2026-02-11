import logging

logger = logging.getLogger(__name__)

_model_cache: dict = {}


def get_model(model_name: str = "base"):
    """Lazy-load and cache a Whisper model."""
    if model_name not in _model_cache:
        import whisper
        logger.info("Loading Whisper model '%s' (first load may take a moment)...", model_name)
        _model_cache[model_name] = whisper.load_model(model_name)
    return _model_cache[model_name]


def transcribe_audio(
    audio_path: str,
    transcript_path: str,
    model_name: str = "base",
    language: str = "en",
) -> str:
    """Transcribe an audio file and save the text. Returns the transcript text."""
    model = get_model(model_name)
    result = model.transcribe(audio_path, language=language)
    text = result.get("text", "").strip()

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(text)

    return text
