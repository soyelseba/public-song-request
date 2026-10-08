"""Aplicación FastAPI: páginas, API REST y WebSocket."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import logging
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import qrcode
import qrcode.image.svg
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, services
from .resolver import detect_platform
from .services import db, hub, player

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("songrequest")


from .network import get_available_ips, lan_ip, resolve_share_url


# ---------------------------------------------------------------- utilidades
def share_url() -> str:
    return resolve_share_url(db)


def admin_token() -> str:
    return hmac.new(config.SECRET_KEY.encode(), config.ADMIN_PASSWORD.encode(), hashlib.sha256).hexdigest()


def is_admin(conn: Request | WebSocket) -> bool:
    token = conn.cookies.get(config.COOKIE_NAME)
    return bool(token) and hmac.compare_digest(token, admin_token())


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(401, "Necesitas iniciar sesión como administrador")


# ---------------------------------------------------------------- app
@asynccontextmanager
async def lifespan(_: FastAPI):
    import asyncio
    hub.loop = asyncio.get_running_loop()
    services.recover()
    player.start()
    url = share_url()
    log.info("=" * 60)
    log.info("  SongRequest listo")
    log.info("  Invitados:     %s", url)
    log.info("  Administrador: %sadmin", url)
    log.info("  Reproductor:   %splayer", url)
    log.info("  ffplay (modo local): %s", player.ffplay or "NO ENCONTRADO")
    log.info("=" * 60)
    yield
    player.shutdown()


app = FastAPI(title="SongRequest", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


def page(name: str) -> FileResponse:
    return FileResponse(config.STATIC_DIR / name, headers={"Cache-Control": "no-cache"})


@app.get("/", include_in_schema=False)
async def guest_page():
    return page("index.html")


@app.get("/admin", include_in_schema=False)
async def admin_page(request: Request):
    if not is_admin(request):
        return RedirectResponse("/login?next=/admin")
    return page("admin.html")


@app.get("/player", include_in_schema=False)
async def player_page(request: Request):
    if not is_admin(request):
        return RedirectResponse("/login?next=/player")
    return page("player.html")


@app.get("/login", include_in_schema=False)
async def login_page():
    return page("login.html")


# ---------------------------------------------------------------- auth
class LoginBody(BaseModel):
    password: str


@app.post("/api/login")
async def login(body: LoginBody):
    if not hmac.compare_digest(body.password.encode(), config.ADMIN_PASSWORD.encode()):
        raise HTTPException(401, "Contraseña incorrecta")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(config.COOKIE_NAME, admin_token(), max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax")
    return resp


@app.post("/api/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(config.COOKIE_NAME)
    return resp


# ---------------------------------------------------------------- estado / compartir
@app.get("/api/state")
async def get_state(request: Request):
    return hub.snapshot(is_admin(request))


@app.get("/api/share")
async def get_share():
    return {
        "url": share_url(),
        "server_ip": db.get_setting("server_ip") or "",
        "available_ips": get_available_ips(),
        "port": config.PORT,
    }


@app.get("/qr.svg", include_in_schema=False)
async def qr_svg(request: Request, url: str | None = None):
    target = url or share_url()
    img = qrcode.make(target, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=1)
    buf = io.BytesIO()
    img.save(buf)
    return Response(
        buf.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


# ---------------------------------------------------------------- peticiones
class NewRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    guest_name: str = Field(default="", max_length=40)
    guest_id: str = Field(default="", max_length=64)


@app.post("/api/requests")
async def create_request(body: NewRequest, request: Request):
    admin = is_admin(request)
    if db.get_setting("requests_open") != "1" and not admin:
        raise HTTPException(403, "Las peticiones están cerradas por ahora")
    ip = request.client.host if request.client else "?"
    guest_id = body.guest_id.strip() or ip
    if not admin:
        n = db.count_open_for_guest(guest_id)
        if n >= config.MAX_PENDING_PER_GUEST:
            raise HTTPException(429, f"Ya tienes {n} peticiones en revisión. Espera a que el DJ las apruebe.")
    query = body.query.strip()
    rid = db.create_request(
        query=query,
        platform=detect_platform(query),
        guest_name=body.guest_name.strip() or "Anónimo",
        guest_id=guest_id,
        guest_ip=ip,
    )
    services.spawn(services.process_new_request(rid))
    hub.notify()
    return {"id": rid}


class ActionBody(BaseModel):
    direction: Literal["up", "down", "top", "bottom"] | None = None


@app.post("/api/requests/{rid}/{action}", dependencies=[Depends(require_admin)])
async def request_action(rid: int, action: str, body: ActionBody | None = None):
    if not db.get_request(rid):
        raise HTTPException(404, "Petición no encontrada")
    match action:
        case "approve":
            await services.approve(rid)
        case "reject":
            await services.reject(rid)
        case "retry":
            await services.retry(rid)
        case "requeue":
            await services.requeue(rid)
        case "play_now":
            await services.play_now(rid)
        case "move":
            if not body or not body.direction:
                raise HTTPException(400, "Falta la dirección")
            services.move(rid, body.direction)
        case _:
            raise HTTPException(400, "Acción desconocida")
    return {"ok": True}


@app.delete("/api/requests/{rid}", dependencies=[Depends(require_admin)])
async def delete_request(rid: int):
    await services.delete(rid)
    return {"ok": True}


@app.post("/api/history/clear", dependencies=[Depends(require_admin)])
async def clear_history():
    db.clear_history()
    hub.notify()
    return {"ok": True}


@app.post("/api/approve-all", dependencies=[Depends(require_admin)])
async def approve_all():
    for r in db.requests_with_status("pending"):
        await services.approve(r["id"])
    return {"ok": True}


class SettingsBody(BaseModel):
    requests_open: bool | None = None
    auto_approve: bool | None = None
    server_ip: str | None = None


@app.post("/api/settings", dependencies=[Depends(require_admin)])
async def update_settings(body: SettingsBody):
    if body.requests_open is not None:
        db.set_setting("requests_open", int(body.requests_open))
    if body.auto_approve is not None:
        db.set_setting("auto_approve", int(body.auto_approve))
        if body.auto_approve:
            for r in db.requests_with_status("pending"):
                await services.approve(r["id"])
    if body.server_ip is not None:
        db.set_setting("server_ip", body.server_ip.strip())
    hub.notify()
    return {"ok": True, "share_url": share_url()}


# ---------------------------------------------------------------- reproductor
class PlayerBody(BaseModel):
    value: float | None = None
    mode: Literal["browser", "local"] | None = None


@app.post("/api/player/{action}", dependencies=[Depends(require_admin)])
async def player_action(action: str, body: PlayerBody | None = None):
    body = body or PlayerBody()
    match action:
        case "play":
            await player.play()
        case "pause":
            await player.pause()
        case "toggle":
            await player.toggle()
        case "next":
            await player.next()
        case "stop":
            await player.stop()
        case "seek" if body.value is not None:
            await player.seek(body.value)
        case "volume" if body.value is not None:
            await player.set_volume(body.value)
        case "mode" if body.mode:
            await player.set_mode(body.mode)
        case _:
            raise HTTPException(400, "Acción no válida")
    return player.state()


@app.get("/media/{rid}", dependencies=[Depends(require_admin)])
async def media(rid: int):
    req = db.get_request(rid)
    if not req or not req.get("file_path") or not Path(req["file_path"]).exists():
        raise HTTPException(404, "Audio no disponible")
    return FileResponse(req["file_path"], media_type="audio/mpeg")


# ---------------------------------------------------------------- websocket
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    admin = is_admin(ws)
    role = ws.query_params.get("role", "guest")
    if role not in ("guest", "admin", "player") or (role != "guest" and not admin):
        role = "guest"
    await hub.connect(ws, role, admin)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if role != "player":
                continue
            kind, token = msg.get("type"), msg.get("token")
            if kind == "progress":
                await player.browser_progress(token, float(msg.get("position") or 0))
            elif kind == "ended":
                await player.browser_ended(token)
            elif kind == "error":
                await player.browser_error(token, msg.get("message"))
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        log.exception("WebSocket error")
    finally:
        hub.disconnect(ws)
