"""Motor de reproducción.

Dos modos:
  * browser -> el audio suena en la página /player (cualquier navegador con sesión de admin).
  * local   -> el audio suena en el propio servidor usando ffplay (incluido con ffmpeg).

El servidor es la fuente de verdad del estado (canción actual, play/pausa, posición, volumen).
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from . import config
from .db import public_view

if TYPE_CHECKING:
    from .db import Database
    from .hub import Hub


class PlayerManager:
    def __init__(self, db: "Database", hub: "Hub") -> None:
        self.db, self.hub = db, hub
        self.mode = db.get_setting("player_mode") or "browser"
        self.volume = int(db.get_setting("volume") or 80)
        self.playing = False          # intención de reproducir
        self.current_id: int | None = None
        self.position = 0.0           # posición en el instante _stamp
        self._stamp = time.monotonic()
        self.track_token = 0          # cambia cada vez que empieza una canción
        self.seek_token = 0           # cambia en cada salto de posición
        self.last_error: str | None = None
        self._proc: subprocess.Popen | None = None
        self._lock = asyncio.Lock()
        self._watcher: asyncio.Task | None = None
        self.ffplay = shutil.which(config.FFPLAY_PATH)
        if self.mode == "local" and not self.ffplay:
            self.mode = "browser"

    # ---- ciclo de vida -------------------------------------------------
    def start(self) -> None:
        self._watcher = asyncio.create_task(self._watch())

    def shutdown(self) -> None:
        self._kill()
        if self._watcher:
            self._watcher.cancel()

    # ---- estado --------------------------------------------------------
    def current_position(self) -> float:
        pos = self.position
        if self.playing and self.current_id is not None:
            pos += time.monotonic() - self._stamp
        cur = self.db.get_request(self.current_id)
        if cur and cur.get("duration"):
            pos = min(pos, float(cur["duration"]))
        return max(0.0, pos)

    def _set_position(self, pos: float) -> None:
        self.position = max(0.0, pos)
        self._stamp = time.monotonic()

    def state(self) -> dict:
        return {
            "mode": self.mode,
            "volume": self.volume,
            "playing": self.playing,
            "current": public_view(self.db.get_request(self.current_id)),
            "position": round(self.current_position(), 2),
            "track_token": self.track_token,
            "seek_token": self.seek_token,
            "local_available": bool(self.ffplay),
            "error": self.last_error,
        }

    # ---- motor local (ffplay) ------------------------------------------
    def _spawn(self, start: float) -> None:
        cur = self.db.get_request(self.current_id)
        if not cur or not cur.get("file_path") or not Path(cur["file_path"]).exists():
            return
        args = [
            self.ffplay or config.FFPLAY_PATH, "-nodisp", "-autoexit", "-loglevel", "error",
            "-volume", str(self.volume), "-ss", f"{start:.2f}", cur["file_path"],
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self._proc = subprocess.Popen(
                args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, creationflags=flags,
            )
            self.last_error = None
        except OSError as e:
            self._proc = None
            self.last_error = f"No se pudo iniciar ffplay: {e}"
            self.mode = "browser"
            self.db.set_setting("player_mode", "browser")
        self._set_position(start)

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _engine_start(self) -> None:
        self._set_position(self.position)
        if self.mode == "local" and self.playing:
            self._kill()
            self._spawn(self.position)

    # ---- lógica de cola ------------------------------------------------
    def _advance(self, finished_status: str = "played", error: str | None = None) -> None:
        """Termina la canción actual y carga la siguiente lista (requiere _lock)."""
        self._kill()
        if self.current_id is not None:
            fields = {"status": finished_status}
            if error:
                fields["error"] = error
            self.db.update_request(self.current_id, **fields)
        self.current_id = None
        self._set_position(0)
        nxt = self.db.next_ready()
        if nxt is None:
            return
        self.current_id = nxt["id"]
        self.db.update_request(nxt["id"], status="playing", played_at=time.time())
        self.track_token += 1
        self._engine_start()

    async def _watch(self) -> None:
        """Detecta el fin de la canción en modo local."""
        while True:
            await asyncio.sleep(0.5)
            proc = self._proc
            if proc is None or proc.poll() is None:
                continue
            async with self._lock:
                if self._proc is not proc:
                    continue
                self._proc = None
                if proc.returncode not in (0, None) and self.current_position() < 2:
                    self._advance("error", "ffplay no pudo reproducir el archivo")
                else:
                    self._advance()
            self.hub.notify()

    # ---- acciones ------------------------------------------------------
    async def play(self) -> None:
        async with self._lock:
            self.playing = True
            if self.current_id is None:
                self._advance()
            else:
                self._engine_start()
        self.hub.notify()

    async def pause(self) -> None:
        async with self._lock:
            if self.playing:
                self._set_position(self.current_position())
                self.playing = False
                self._kill()
        self.hub.notify()

    async def toggle(self) -> None:
        await (self.pause() if self.playing else self.play())

    async def next(self) -> None:
        async with self._lock:
            self.playing = True
            self._advance()
        self.hub.notify()

    async def stop(self) -> None:
        async with self._lock:
            self._kill()
            self.playing = False
            self._set_position(0)
            self.seek_token += 1
        self.hub.notify()

    async def seek(self, pos: float) -> None:
        async with self._lock:
            if self.current_id is None:
                return
            self._set_position(pos)
            self.seek_token += 1
            self._engine_start()
        self.hub.notify()

    async def set_volume(self, value: float) -> None:
        async with self._lock:
            self.volume = int(max(0, min(100, value)))
            self.db.set_setting("volume", self.volume)
            if self.mode == "local" and self.playing:
                self._set_position(self.current_position())
                self._engine_start()
        self.hub.notify()

    async def set_mode(self, mode: str) -> None:
        if mode not in ("browser", "local"):
            return
        async with self._lock:
            if mode == "local" and not self.ffplay:
                self.last_error = "ffplay no está disponible en el servidor"
            elif mode != self.mode:
                pos = self.current_position()
                self._kill()
                self.mode = mode
                self.db.set_setting("player_mode", mode)
                self._set_position(pos)
                self.seek_token += 1
                self._engine_start()
        self.hub.notify()

    async def track_ready(self) -> None:
        """Llamado cuando una canción termina de descargarse."""
        async with self._lock:
            if self.playing and self.current_id is None:
                self._advance()
        self.hub.notify()

    async def remove_current(self, status: str) -> None:
        async with self._lock:
            self._advance(status)
        self.hub.notify()

    # ---- eventos del reproductor web -----------------------------------
    async def browser_progress(self, token: int, position: float) -> None:
        if self.mode == "browser" and token == self.track_token and self.playing:
            self._set_position(position)
            await self.hub.broadcast({"type": "progress", "token": token, "position": round(position, 2)})

    async def browser_ended(self, token: int) -> None:
        async with self._lock:
            if self.mode == "browser" and token == self.track_token:
                self._advance()
        self.hub.notify()

    async def browser_error(self, token: int, message: str | None) -> None:
        async with self._lock:
            if self.mode == "browser" and token == self.track_token:
                self._advance("error", message or "Error de reproducción en el navegador")
        self.hub.notify()
