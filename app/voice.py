"""
TASKORA - Voice & Text-to-Speech Module
Handles ElevenLabs API integration, audio disk caching with SHA-256 hash keys,
and graceful browser-fallback responses when API keys are absent or network is unavailable.
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_CACHE_DIR = BASE_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Default configuration
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (calm, clear voice)
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


def get_audio_hash(text: str, voice_id: str, model_id: str, language: str = "en") -> str:
    """
    Computes a deterministic SHA-256 hash of the text, voice, and model
    to serve as the cache filename.
    """
    key_str = f"{text.strip()}:{voice_id}:{model_id}:{language.strip().lower()}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


def generate_speech(
    text: str,
    language: str = "en",
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates speech for the given text using ElevenLabs API.
    Caches the MP3 on disk. If cached, serves directly without network calls.
    If the API key is missing or the external call fails, returns fallback=True
    so the frontend seamlessly falls back to browser speechSynthesis.
    """
    if not text or not text.strip():
        return {
            "success": False,
            "fallback": True,
            "error": "Empty text provided",
            "audio_url": None
        }

    clean_text = text.strip()
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    active_voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    active_model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID)

    # Check cache first
    cache_hash = get_audio_hash(clean_text, active_voice_id, active_model_id, language=language)
    cache_file = AUDIO_CACHE_DIR / f"{cache_hash}.mp3"

    if cache_file.exists() and cache_file.stat().st_size > 0:
        return {
            "success": True,
            "cached": True,
            "fallback": False,
            "audio_url": f"/audio_cache/{cache_hash}.mp3"
        }

    # If no valid API key is configured or placeholder is present, signal fallback
    if not api_key or api_key == "your_elevenlabs_api_key_here":
        return {
            "success": False,
            "fallback": True,
            "reason": "ElevenLabs API key not configured. Using client-side speech synthesis.",
            "audio_url": None
        }

    # Official ElevenLabs Text-to-Speech API
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{active_voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    payload = {
        "text": clean_text,
        "model_id": active_model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(cache_file, "wb") as f:
                f.write(response.content)

            return {
                "success": True,
                "cached": False,
                "fallback": False,
                "audio_url": f"/audio_cache/{cache_hash}.mp3"
            }
        else:
            return {
                "success": False,
                "fallback": True,
                "reason": f"ElevenLabs API responded with status {response.status_code}",
                "audio_url": None
            }
    except Exception as e:
        return {
            "success": False,
            "fallback": True,
            "reason": f"ElevenLabs network request failed: {str(e)}",
            "audio_url": None
        }
