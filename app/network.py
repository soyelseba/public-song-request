"""Detección de red y resolución de la URL para invitados / código QR."""
from __future__ import annotations

import socket
from typing import TYPE_CHECKING

from . import config

if TYPE_CHECKING:
    from .db import Database


def lan_ip() -> str:
    """Devuelve la IP de la ruta por defecto."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def get_available_ips() -> list[str]:
    """Lista las IPs IPv4 disponibles en las interfaces de red de la máquina."""
    ips = set()
    try:
        primary = lan_ip()
        if primary and not primary.startswith("127."):
            ips.add(primary)
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    if not ips:
        ips.add("127.0.0.1")
    return sorted(list(ips))


def resolve_share_url(db: "Database" | None = None) -> str:
    """Calcula la URL final que abrirán los invitados al escanear el QR.
    
    Prioridad:
      1. IP o URL registrada manualmente por el administrador en el panel.
      2. PUBLIC_URL si está definida en variables de entorno / .env.
      3. IP local autodetectada (lan_ip) con el puerto configurado.
    """
    saved = db.get_setting("server_ip") if db else None
    if saved and saved.strip():
        val = saved.strip()
        # Si no tiene protocolo, asumir http://
        if not val.startswith("http://") and not val.startswith("https://"):
            # Si no incluye puerto y parece una IP o host simple, añadir el puerto configurado
            if ":" not in val:
                val = f"http://{val}:{config.PORT}/"
            else:
                val = f"http://{val}/"
        if not val.endswith("/"):
            val += "/"
        return val

    if config.PUBLIC_URL:
        url = config.PUBLIC_URL.strip()
        return url if url.endswith("/") else f"{url}/"

    return f"http://{lan_ip()}:{config.PORT}/"
