"""Hub de WebSockets: difunde el estado en tiempo real a invitados, admin y reproductores."""
from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from fastapi import WebSocket

from . import config
from .db import public_view

if TYPE_CHECKING:
    from .db import Database
    from .player import PlayerManager


class Hub:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, dict] = {}
        self.progress: dict[int, float] = {}  # progreso de descarga por petición
        self.loop: asyncio.AbstractEventLoop | None = None
        self.db: Database | None = None
        self.player: PlayerManager | None = None
        self._scheduled = False

    def bind(self, db: "Database", player: "PlayerManager") -> None:
        self.db, self.player = db, player

    # ---- conexiones ------------------------------------------------------
    async def connect(self, ws: WebSocket, role: str, admin: bool) -> None:
        await ws.accept()
        self.clients[ws] = {"role": role, "admin": admin}
        await self._send(ws, json.dumps(self.snapshot(admin)))
        if role == "player":
            self.notify()

    def disconnect(self, ws: WebSocket) -> None:
        info = self.clients.pop(ws, None)
        if info and info["role"] == "player":
            self.notify()

    def players_online(self) -> int:
        return sum(1 for c in self.clients.values() if c["role"] == "player")

    # ---- snapshot --------------------------------------------------------
    def snapshot(self, admin: bool) -> dict:
        assert self.db and self.player
        from .network import get_available_ips, resolve_share_url
        rows = self.db.active_requests() + self.db.recent_finished(30)
        share_url = resolve_share_url(self.db)
        return {
            "type": "state",
            "admin": admin,
            "requests": [public_view(r, admin, self.progress.get(r["id"])) for r in rows],
            "player": self.player.state(),
            "settings": {
                "requests_open": self.db.get_setting("requests_open") == "1",
                "auto_approve": self.db.get_setting("auto_approve") == "1",
                "server_ip": self.db.get_setting("server_ip") or "",
                "max_pending": config.MAX_PENDING_PER_GUEST,
                "max_duration": config.MAX_DURATION_SECONDS,
            },
            "share_url": share_url,
            "available_ips": get_available_ips() if admin else [],
            "players_online": self.players_online(),
        }

    # ---- difusión --------------------------------------------------------
    def notify(self) -> None:
        """Programa una difusión del estado (con debounce)."""
        if self._scheduled or not self.loop:
            return
        self._scheduled = True
        self.loop.call_later(0.06, lambda: asyncio.ensure_future(self._flush()))

    def notify_threadsafe(self) -> None:
        if self.loop:
            self.loop.call_soon_threadsafe(self.notify)

    async def _flush(self) -> None:
        self._scheduled = False
        if not self.clients:
            return
        payloads: dict[bool, str] = {}
        tasks = []
        for ws, info in list(self.clients.items()):
            admin = info["admin"]
            if admin not in payloads:
                payloads[admin] = json.dumps(self.snapshot(admin))
            tasks.append(self._send(ws, payloads[admin]))
        await asyncio.gather(*tasks)

    async def broadcast(self, message: dict) -> None:
        text = json.dumps(message)
        await asyncio.gather(*(self._send(ws, text) for ws in list(self.clients)))

    async def _send(self, ws: WebSocket, text: str) -> None:
        try:
            await asyncio.wait_for(ws.send_text(text), timeout=5)
        except Exception:
            self.clients.pop(ws, None)
