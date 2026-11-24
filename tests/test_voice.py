"""
Unit tests for TASKORA Voice & Audio Module (app/voice.py).
Covers cache keys, disk cache retrieval, and safe browser fallback behaviour.
"""


import requests

from app.voice import (
    AUDIO_CACHE_DIR,
    DEFAULT_MODEL_ID,
    DEFAULT_VOICE_ID,
    generate_speech,
    get_audio_hash,
)


def test_audio_hash_deterministic_and_language_aware():
    """Cache keys are stable but differ when the requested language differs."""
    h1 = get_audio_hash("Hello world", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID)
    h2 = get_audio_hash("Hello world", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "en")
    assert h1 == h2
    assert len(h1) == 64

    assert h1 != get_audio_hash(
        "Hello Bengaluru", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID
    )
    assert h1 != get_audio_hash(
        "Hello world", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "hi"
    )


def test_audio_hash_separates_english_hindi_and_kannada():
    """The same text must not reuse cached audio across supported languages."""
    english = get_audio_hash("Namaskara", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "en")
    hindi = get_audio_hash("Namaskara", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "hi")
    kannada = get_audio_hash("Namaskara", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "kn")
    assert len({english, hindi, kannada}) == 3


def test_empty_text_handling():
    """Empty or whitespace-only text fails gracefully."""
    for text in ("", "   "):
        result = generate_speech(text)
        assert result["success"] is False
        assert result["fallback"] is True
        assert result["audio_url"] is None


def test_fallback_when_no_api_key(monkeypatch):
    """A missing API key requests browser speech synthesis."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    result = generate_speech("Electrician in Hebbal", language="en")

    assert result["success"] is False
    assert result["fallback"] is True
    assert "not configured" in result["reason"].lower()


def test_disk_cache_retrieval():
    """Existing cache files are served without making an external request."""
    test_text = "Disk cache test sample text"
    cache_hash = get_audio_hash(
        test_text, DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "en"
    )
    cached_file = AUDIO_CACHE_DIR / f"{cache_hash}.mp3"
    cached_file.write_bytes(b"MOCK_MP3_DATA_FOR_TESTING")

    try:
        result = generate_speech(test_text, language="en")
        assert result["success"] is True
        assert result["cached"] is True
        assert result["fallback"] is False
        assert result["audio_url"] == f"/audio_cache/{cache_hash}.mp3"
    finally:
        cached_file.unlink(missing_ok=True)


def test_network_error_uses_safe_fallback(monkeypatch):
    """Network exceptions do not leak internal exception details to clients."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("private request details")

    monkeypatch.setattr("app.voice.requests.post", raise_connection_error)
    result = generate_speech("Test network fallback")

    assert result["success"] is False
    assert result["fallback"] is True
    assert "temporarily unavailable" in result["reason"].lower()
    assert "private request details" not in result["reason"]


def test_api_error_uses_safe_fallback(monkeypatch):
    """Non-success API responses return a generic, non-sensitive reason."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    class FakeResponse:
        status_code = 401

    monkeypatch.setattr("app.voice.requests.post", lambda *args, **kwargs: FakeResponse())
    result = generate_speech("Test API fallback")

    assert result["success"] is False
    assert result["fallback"] is True
    assert "could not generate audio" in result["reason"].lower()
    assert "401" not in result["reason"]
