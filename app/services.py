"""Lógica de negocio de las peticiones: resolver, aprobar, descargar, reordenar."""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Coroutine

from . import config
from .db import Database
from .hub import Hub
from .player import PlayerManager
from .resolver import ResolveError, download_audio, resolve

log = logging.getLogger("songrequest")

db = Database(config.DB_PATH)
hub = Hub()
player = PlayerManager(db, hub)
hub.bind(db, player)

_download_sem = asyncio.Semaphore(config.MAX_PARALLEL_DOWNLOADS)
_tasks: set[asyncio.Task] = set()


def spawn(coro: Coroutine) -> None:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _fail(rid: int, message: str) -> None:
    db.update_request(rid, status="error", error=message)
    hub.progress.pop(rid, None)
    hub.notify()


# ---------------------------------------------------------------- resolución
async def process_new_request(rid: int) -> None:
    req = db.get_request(rid)
    if not req:
        return
    try:
        meta = await asyncio.to_thread(resolve, req["query"])
    except ResolveError as e:
        return _fail(rid, str(e))
    except Exception as e:  # noqa: BLE001
        log.exception("Error resolviendo %s", req["query"])
        return _fail(rid, f"Error inesperado: {e}")

    if not meta.get("webpage_url"):
        return _fail(rid, "No se encontró una fuente reproducible")
    dur = meta.get("duration") or 0
    if config.MAX_DURATION_SECONDS and dur > config.MAX_DURATION_SECONDS:
        db.update_request(rid, **meta)
        return _fail(rid, f"Demasiado larga ({int(dur // 60)} min). Máximo {config.MAX_DURATION_SECONDS // 60} min")
    if db.find_active_duplicate(meta["webpage_url"], rid):
        db.update_request(rid, **meta)
        return _fail(rid, "Esa canción ya está en la cola")

    req = db.get_request(rid)
    if not req or req["status"] != "resolving":  # borrada / rechazada mientras tanto
        return
    db.update_request(rid, **meta, status="pending", error=None)
    if db.get_setting("auto_approve") == "1":
        await approve(rid)
    else:
        hub.notify()


# ---------------------------------------------------------------- aprobación / descarga
async def approve(rid: int) -> None:
    req = db.get_request(rid)
    if not req or req["status"] not in ("pending", "rejected", "played", "error"):
        return
    if not req.get("webpage_url"):
        return await retry(rid)
    db.update_request(rid, status="approved", position=db.next_position(), error=None)
    hub.notify()
    spawn(download(rid))


async def download(rid: int) -> None:
    async with _download_sem:
        req = db.get_request(rid)
        if not req or req["status"] != "approved":
            return
        db.update_request(rid, status="downloading")
        hub.progress[rid] = 0
        hub.notify()

        last = [0.0]

        def on_progress(pct: float) -> None:
            hub.progress[rid] = pct
            now = time.monotonic()
            if now - last[0] > 0.6:
                last[0] = now
                hub.notify_threadsafe()

        try:
            path = await asyncio.to_thread(download_audio, req["webpage_url"], on_progress)
        except ResolveError as e:
            return _fail(rid, str(e))
        except Exception as e:  # noqa: BLE001
            log.exception("Error descargando %s", req["webpage_url"])
            return _fail(rid, f"Error en la descarga: {e}")

        hub.progress.pop(rid, None)
        req = db.get_request(rid)
        if not req or req["status"] != "downloading":
            hub.notify()
            return
        db.update_request(rid, status="ready", file_path=str(path))
        hub.notify()
    await player.track_ready()


async def retry(rid: int) -> None:
    db.update_request(rid, status="resolving", error=None, position=None)
    hub.notify()
    spawn(process_new_request(rid))


async def requeue(rid: int) -> None:
    """Vuelve a poner en cola una canción del historial (aprobada directamente)."""
    req = db.get_request(rid)
    if not req:
        return
    if not req.get("webpage_url"):
        return await retry(rid)
    db.update_request(rid, status="approved", position=db.next_position(), error=None)
    hub.notify()
    spawn(download(rid))


async def reject(rid: int) -> None:
    if player.current_id == rid:
        await player.remove_current("rejected")
    else:
        db.update_request(rid, status="rejected")
    hub.progress.pop(rid, None)
    hub.notify()


async def delete(rid: int) -> None:
    if player.current_id == rid:
        await player.remove_current("played")
    db.delete_request(rid)
    hub.progress.pop(rid, None)
    hub.notify()


# ---------------------------------------------------------------- orden de la cola
def move(rid: int, direction: str) -> None:
    items = db.queue_items()
    idx = next((i for i, r in enumerate(items) if r["id"] == rid), None)
    if idx is None:
        return
    if direction == "top":
        db.update_request(rid, position=items[0]["position"] - 1)
    elif direction == "bottom":
        db.update_request(rid, position=items[-1]["position"] + 1)
    elif direction in ("up", "down"):
        j = idx - 1 if direction == "up" else idx + 1
        if 0 <= j < len(items):
            a, b = items[idx], items[j]
            db.update_request(a["id"], position=b["position"])
            db.update_request(b["id"], position=a["position"])
    hub.notify()


async def play_now(rid: int) -> None:
    req = db.get_request(rid)
    if not req:
        return
    if req["status"] in ("pending", "played", "rejected", "error"):
        await requeue(rid) if req["status"] != "pending" else await approve(rid)
    db.update_request(rid, position=db.top_position())
    req = db.get_request(rid)
    if req and req["status"] == "ready":
        await player.next()
    hub.notify()


# ---------------------------------------------------------------- arranque
def recover() -> None:
    """Restaura el estado tras un reinicio del servidor."""
    for r in db.requests_with_status("playing"):
        db.update_request(r["id"], status="ready", position=db.top_position())
    for r in db.requests_with_status("ready"):
        if not r.get("file_path") or not Path(r["file_path"]).exists():
            db.update_request(r["id"], status="approved")
    for r in db.requests_with_status("downloading", "approved"):
        db.update_request(r["id"], status="approved")
        spawn(download(r["id"]))
    for r in db.requests_with_status("resolving"):
        spawn(process_new_request(r["id"]))
