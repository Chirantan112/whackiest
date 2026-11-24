"""
TASKORA - Voice & Text-to-Speech Module
Handles ElevenLabs API integration, language-aware audio caching, and
graceful browser-fallback responses when configuration or network is unavailable.
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_CACHE_DIR = BASE_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


def get_audio_hash(
    text: str,
    voice_id: str,
    model_id: str,
    language: str = "en",
) -> str:
    """Return a deterministic cache key for text, voice, model, and language.

    The default language keeps existing three-argument callers compatible.
    """
    normalized_language = (language or "en").strip().lower()
    key_str = f"{text.strip()}:{voice_id}:{model_id}:{normalized_language}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


def generate_speech(
    text: str,
    language: str = "en",
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate and cache ElevenLabs speech, or request browser TTS fallback."""
    if not text or not text.strip():
        return {
            "success": False,
            "fallback": True,
            "error": "Empty text provided",
            "audio_url": None,
        }

    clean_text = text.strip()
    normalized_language = (language or "en").strip().lower()
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    active_voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    active_model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID)

    cache_hash = get_audio_hash(
        clean_text, active_voice_id, active_model_id, normalized_language
    )
    cache_file = AUDIO_CACHE_DIR / f"{cache_hash}.mp3"

    if cache_file.exists() and cache_file.stat().st_size > 0:
        return {
            "success": True,
            "cached": True,
            "fallback": False,
            "audio_url": f"/audio_cache/{cache_hash}.mp3",
        }

    if not api_key or api_key == "your_elevenlabs_api_key_here":
        return {
            "success": False,
            "fallback": True,
            "reason": "ElevenLabs API key not configured. Using client-side speech synthesis.",
            "audio_url": None,
        }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{active_voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }
    payload = {
        "text": clean_text,
        "model_id": active_model_id,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.RequestException:
        # Do not expose exception details, request metadata, or credentials to clients.
        return {
            "success": False,
            "fallback": True,
            "reason": "ElevenLabs is temporarily unavailable. Using client-side speech synthesis.",
            "audio_url": None,
        }

    if response.status_code != 200:
        return {
            "success": False,
            "fallback": True,
            "reason": "ElevenLabs could not generate audio. Using client-side speech synthesis.",
            "audio_url": None,
        }

    try:
        cache_file.write_bytes(response.content)
    except OSError:
        return {
            "success": False,
            "fallback": True,
            "reason": "Audio could not be cached. Using client-side speech synthesis.",
            "audio_url": None,
        }

    return {
        "success": True,
        "cached": False,
        "fallback": False,
        "audio_url": f"/audio_cache/{cache_hash}.mp3",
    }
