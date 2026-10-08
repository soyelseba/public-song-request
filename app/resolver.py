"""Resolución de metadatos y descarga de audio (YouTube, Spotify, SoundCloud, búsqueda libre)."""
from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path
from typing import Callable

import httpx
import yt_dlp

from . import config

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


class ResolveError(Exception):
    """Error mostrado tal cual al usuario."""


def detect_platform(text: str) -> str:
    t = text.strip().lower()
    if re.search(r"(youtube\.com|youtu\.be|music\.youtube)", t):
        return "youtube"
    if "spotify.com" in t or t.startswith("spotify:"):
        return "spotify"
    if "soundcloud.com" in t or "snd.sc" in t:
        return "soundcloud"
    if re.match(r"^https?://", t):
        return "web"
    return "search"


# --------------------------------------------------------------------------- yt-dlp
def _base_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "noprogress": True,
        "socket_timeout": 20,
    }
    if config.FFMPEG_LOCATION:
        opts["ffmpeg_location"] = config.FFMPEG_LOCATION
    return opts


def _extract(target: str, allow_playlist_first: bool) -> dict:
    opts = _base_opts() | {"skip_download": True, "extract_flat": "in_playlist"}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target, download=False)
    except yt_dlp.utils.DownloadError as e:
        msg = re.sub(r"^ERROR:\s*", "", str(e))
        raise ResolveError(f"No se pudo obtener la canción: {msg[:160]}") from e
    if not info:
        raise ResolveError("No se encontraron resultados")
    if info.get("_type") == "playlist" or "entries" in info:
        if not allow_playlist_first:
            raise ResolveError("Solo se aceptan canciones individuales, no listas/álbumes")
        entries = [e for e in (info.get("entries") or []) if e]
        if not entries:
            raise ResolveError("No se encontraron resultados para esa búsqueda")
        info = entries[0]
    return info


def _thumbnail(info: dict) -> str | None:
    vid = info.get("id")
    extractor = (info.get("ie_key") or info.get("extractor_key") or info.get("extractor") or "").lower()
    if vid and "youtube" in extractor:
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    if info.get("thumbnail"):
        return info["thumbnail"]
    thumbs = info.get("thumbnails") or []
    return thumbs[-1].get("url") if thumbs else None


def _clean_artist(name: str | None) -> str | None:
    if not name:
        return None
    return re.sub(r"\s*-\s*Topic$|VEVO$", "", name).strip() or None


def _meta_from_info(info: dict, platform: str) -> dict:
    url = info.get("webpage_url") or info.get("url")
    if url and not url.startswith("http") and info.get("id"):
        url = f"https://www.youtube.com/watch?v={info['id']}"
    title = info.get("track") or info.get("title") or "Sin título"
    artist = _clean_artist(info.get("artist") or info.get("creator") or info.get("uploader") or info.get("channel"))
    return {
        "title": title,
        "artist": artist,
        "thumbnail": _thumbnail(info),
        "duration": info.get("duration"),
        "webpage_url": url,
        "platform": platform,
    }


# --------------------------------------------------------------------------- Spotify
def _meta_tag(page: str, prop: str) -> str | None:
    m = re.search(rf'<meta[^>]+(?:property|name)="{re.escape(prop)}"[^>]+content="([^"]*)"', page)
    return html.unescape(m.group(1)).strip() if m else None


def _spotify_track(url: str) -> tuple[str, str | None, str | None]:
    """Devuelve (título, artista, portada) de una canción de Spotify sin API key."""
    m = re.search(r"track[/:]([A-Za-z0-9]{10,})", url)
    if not m:
        raise ResolveError("De Spotify solo se aceptan enlaces de canciones (open.spotify.com/track/...)")
    track_url = f"https://open.spotify.com/track/{m.group(1)}"
    title = artist = cover = None
    try:
        r = httpx.get(track_url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
                      follow_redirects=True, timeout=12)
        page = r.text
        title = _meta_tag(page, "og:title")
        cover = _meta_tag(page, "og:image")
        artist = _meta_tag(page, "music:musician_description")
        if not artist:
            t = re.search(r"<title>(.*?)</title>", page, re.S)
            if t:
                mt = re.search(r"by (.+?) \| Spotify", html.unescape(t.group(1)))
                if mt:
                    artist = mt.group(1)
        if not artist:
            desc = _meta_tag(page, "og:description") or ""
            parts = [p.strip() for p in desc.split("·")]
            if len(parts) >= 2:
                artist = parts[0]
    except httpx.HTTPError:
        pass
    if not title:  # fallback oEmbed
        try:
            r = httpx.get("https://open.spotify.com/oembed", params={"url": track_url}, timeout=10)
            data = r.json()
            title, cover = data.get("title"), cover or data.get("thumbnail_url")
        except Exception:
            pass
    if not title:
        raise ResolveError("No se pudo leer la canción de Spotify")
    return title, artist, cover


# --------------------------------------------------------------------------- API pública
def resolve(query: str) -> dict:
    """Obtiene metadatos y una URL descargable para la petición (bloqueante)."""
    query = query.strip()
    platform = detect_platform(query)

    if platform == "spotify":
        title, artist, cover = _spotify_track(query)
        search = f"{artist} - {title}" if artist else title
        info = _extract(f"ytsearch1:{search} audio", allow_playlist_first=True)
        meta = _meta_from_info(info, "spotify")
        meta.update(title=title, artist=artist or meta["artist"], thumbnail=cover or meta["thumbnail"])
        return meta

    if platform == "search":
        info = _extract(f"ytsearch1:{query}", allow_playlist_first=True)
        return _meta_from_info(info, "youtube")

    info = _extract(query, allow_playlist_first=False)
    return _meta_from_info(info, platform)


def cache_path(webpage_url: str) -> Path:
    key = hashlib.sha1(webpage_url.encode()).hexdigest()[:20]
    return config.MEDIA_DIR / f"{key}.mp3"


def download_audio(webpage_url: str, progress: Callable[[float], None] | None = None) -> Path:
    """Descarga y convierte a MP3 (bloqueante). Usa caché por URL."""
    target = cache_path(webpage_url)
    if target.exists() and target.stat().st_size > 0:
        return target

    def hook(d: dict) -> None:
        if not progress:
            return
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                progress(min(95.0, d.get("downloaded_bytes", 0) * 95 / total))
        elif d.get("status") == "finished":
            progress(97.0)

    opts = _base_opts() | {
        "format": "bestaudio/best",
        "outtmpl": str(target.with_suffix(".%(ext)s")),
        "progress_hooks": [hook],
        "retries": 3,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": config.AUDIO_QUALITY,
        }],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([webpage_url])
    except yt_dlp.utils.DownloadError as e:
        msg = re.sub(r"^ERROR:\s*", "", str(e))
        raise ResolveError(f"Falló la descarga: {msg[:160]}") from e
    if not target.exists():
        raise ResolveError("La descarga terminó pero no se encontró el archivo de audio")
    return target
