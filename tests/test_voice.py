"""
Unit tests for TASKORA Voice & Audio Module (app/voice.py).
Tests hashing, disk caching, graceful fallback, and empty input handling.
"""

import os
from pathlib import Path
import pytest
from app.voice import (
    get_audio_hash,
    generate_speech,
    AUDIO_CACHE_DIR,
    DEFAULT_VOICE_ID,
    DEFAULT_MODEL_ID
)


def test_audio_hash_deterministic():
    """Verify SHA-256 hash is deterministic for same text, voice, and model."""
    h1 = get_audio_hash("Hello world", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID)
    h2 = get_audio_hash("Hello world", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID)
    assert h1 == h2
    assert len(h1) == 64

    # Different text should produce different hash
    h3 = get_audio_hash("Hello Bengaluru", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID)
    assert h1 != h3


def test_audio_hash_separates_languages():
    """The same text must not reuse audio generated for a different language."""
    english = get_audio_hash("Namaskara", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "en")
    kannada = get_audio_hash("Namaskara", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "kn")
    hindi = get_audio_hash("Namaskara", DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, "hi")
    assert len({english, kannada, hindi}) == 3


def test_empty_text_handling():
    """Verify empty or whitespace text fails gracefully without crash."""
    res = generate_speech("")
    assert res["success"] is False
    assert res["fallback"] is True
    assert res["audio_url"] is None


def test_fallback_when_no_api_key():
    """Verify fallback=True and reason is provided when ElevenLabs API key is placeholder."""
    # Ensure no valid key is present in environment for this test
    original_key = os.environ.get("ELEVENLABS_API_KEY")
    os.environ["ELEVENLABS_API_KEY"] = ""

    try:
        res = generate_speech("Electrician in Hebbal", language="en")
        assert res["success"] is False
        assert res["fallback"] is True
        assert "not configured" in res["reason"].lower()
    finally:
        if original_key is not None:
            os.environ["ELEVENLABS_API_KEY"] = original_key


def test_disk_cache_retrieval(tmp_path):
    """Verify that existing cache files on disk are served directly without external requests."""
    test_text = "Disk cache test sample text"
    cache_hash = get_audio_hash(test_text, DEFAULT_VOICE_ID, DEFAULT_MODEL_ID)
    cached_file = AUDIO_CACHE_DIR / f"{cache_hash}.mp3"

    # Simulate existing audio file in cache
    with open(cached_file, "wb") as f:
        f.write(b"MOCK_MP3_DATA_FOR_TESTING")

    try:
        res = generate_speech(test_text)
        assert res["success"] is True
        assert res["cached"] is True
        assert res["fallback"] is False
        assert res["audio_url"] == f"/audio_cache/{cache_hash}.mp3"
    finally:
        # Clean up mock file
        if cached_file.exists():
            cached_file.unlink()
