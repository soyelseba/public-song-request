"""Configuración leída desde variables de entorno / archivo .env."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


STATIC_DIR = BASE_DIR / "static"
DATA_DIR = Path(os.getenv("DATA_DIR") or BASE_DIR / "data")
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "songs.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = _int("PORT", 8000)
PUBLIC_URL = os.getenv("PUBLIC_URL", "").strip()  # URL que se mostrará en el QR (opcional)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


def _secret_key() -> str:
    key = os.getenv("SECRET_KEY")
    if key:
        return key
    path = DATA_DIR / ".secret"
    if path.exists():
        return path.read_text().strip()
    key = secrets.token_hex(32)
    path.write_text(key)
    return key


SECRET_KEY = _secret_key()
COOKIE_NAME = "sr_admin"

MAX_PENDING_PER_GUEST = _int("MAX_PENDING_PER_GUEST", 3)
MAX_DURATION_SECONDS = _int("MAX_DURATION_SECONDS", 900)  # 0 = sin límite
MAX_PARALLEL_DOWNLOADS = max(1, _int("MAX_PARALLEL_DOWNLOADS", 2))
AUDIO_QUALITY = os.getenv("AUDIO_QUALITY", "192")

FFMPEG_LOCATION = os.getenv("FFMPEG_LOCATION") or None  # carpeta o ruta de ffmpeg si no está en PATH
FFPLAY_PATH = os.getenv("FFPLAY_PATH", "ffplay")
