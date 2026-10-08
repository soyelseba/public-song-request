# 🎧 SongRequest

Aplicación web colaborativa en **Python** para fiestas, bares, eventos o streaming donde los invitados pueden pedir canciones desde su móvil (YouTube, Spotify, SoundCloud o búsqueda libre) y el administrador/DJ aprueba y gestiona la cola en tiempo real.

---

## 🚀 Características principales

- **Tres vistas especializadas**:
  1. **Vista de Invitados (`/`)**:
     - Interfaz móvil ultra limpia y oscura con diseño tipo Aurora Glassmorphism.
     - Detección automática de enlaces (**YouTube**, **Spotify**, **SoundCloud**) o búsqueda directa por texto (título y artista).
     - Seguimiento del estado de las peticiones propias en vivo (En revisión, Aprobada, Descargando, En cola, Sonando).
     - Tarjeta "Sonando ahora" con visualizador ecualizador en tiempo real y progreso.
  2. **Panel de Administrador / DJ (`/admin`)**:
     - Protegido por contraseña (sesión persistente en cookie).
     - Columna de **Peticiones pendientes** con acciones rápidas: Aprobar (✔), Aprobar y reproducir ya (⚡), Rechazar (✖).
     - Botón para **Aprobar todas** con un solo clic.
     - Posibilidad de añadir canciones directamente desde cabina.
     - Columna de **Cola** con reordenación (Subir, Bajar, Poner al inicio) y estimación de tiempo total.
     - Columna de **Historial** con opción de reintentar errores o volver a encolar canciones.
     - Control de ajustes en vivo: abrir/cerrar peticiones a invitados y modo auto-aprobar.
     - **Configuración de IP de Red & QR dinámico**:
       - El admin puede seleccionar con un clic entre las IPs detectadas en el servidor (ej. Wi-Fi, Ethernet) o ingresar una IP/dominio personalizado.
       - La IP registrada se guarda en SQLite y actualiza al instante el código QR en toda la app.
       - Botón **Ampliar QR** para proyectar el código en pantalla grande para que los invitados escaneen con la cámara de su móvil y entren directamente a pedir música.
  3. **Vista de Reproductor (`/player`)**:
     - Pantalla de reproducción dedicada estilo escenario o festival.
     - **Doble modo de reproducción**:
       - 🌐 **Navegador**: El audio suena en la propia pestaña del navegador (HTML5 Audio streaming directo desde el servidor).
       - 🖥️ **Servidor (Local)**: El audio suena por los altavoces de la computadora donde corre el servidor usando `ffplay` (de FFmpeg).
     - Portada gigante con resplandor ambiental (*ambient glow*), título, artista, quién pidió la canción y barra de búsqueda/progreso interactiva.
     - Barra de volumen y controles completos (Play, Pausa, Siguiente, Detener, Atajos de teclado: Barra espaciadora y Shift+Flecha derecha).
     - Código QR grande interactivo en pantalla lateral con modal de ampliación para que los invitados escaneen desde la pista de baile.

- **Soporte de plataformas**:
  - **YouTube / YouTube Music**: Enlaces directos o búsqueda por texto mediante `yt-dlp`.
  - **Spotify**: Enlaces de canciones (`open.spotify.com/track/...`). Extrae metadatos públicos sin requerir cuenta Premium ni API keys y empareja el mejor audio descargable automáticamente.
  - **SoundCloud**: Enlaces directos de pistas individuales.
  - **Búsqueda por texto**: Los invitados simplemente pueden escribir *"Coldplay Yellow"* o *"Dua Lipa Houdini"* sin buscar enlaces.

- **Tecnología robusta**:
  - Backend asíncrono con **FastAPI** y **WebSockets**.
  - Sincronización instantánea en milisegundos con patrón hub de eventos.
  - Descarga y conversión de audio a MP3 de alta fidelidad con **FFmpeg** en segundo plano con caché por hash (no vuelve a descargar canciones repetidas).
  - Base de datos ligera **SQLite con WAL mode** (recupera estado y cola tras reinicios del servidor).

---

## 📦 Requisitos

1. **Python 3.10+** (probado con Python 3.14).
2. **FFmpeg / FFplay** instalado en el sistema y disponible en el `PATH` (ya instalado en tu equipo).

---

## ⚡ Instalación y Arranque Rápido

### En Windows (con doble clic)
Simplemente ejecuta:
```cmd
start.bat
```
El script creará automáticamente el entorno virtual `.venv`, instalará las dependencias y arrancará el servidor.

---

### Manualmente por terminal (PowerShell o CMD)

1. Crear y activar el entorno virtual:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Instalar dependencias:
   ```powershell
   pip install -r requirements.txt
   ```

3. (Opcional) Configurar `.env`:
   ```powershell
   copy .env.example .env
   ```
   Edita `.env` para cambiar la contraseña del administrador:
   ```env
   ADMIN_PASSWORD=tu_clave_secreta
   PORT=8000
   ```

4. Ejecutar la aplicación:
   ```powershell
   python run.py
   ```

El servidor estará listo en:
- **Invitados**: `http://localhost:8000/` (o la IP de red local mostrada en consola)
- **Panel DJ**: `http://localhost:8000/admin`
- **Reproductor**: `http://localhost:8000/player`

Contraseña por defecto: `admin` (configurable en `.env`).

---

## 📱 Cómo conectar a los invitados

1. **En la misma red WiFi**:
   - Al iniciar, la app detecta automáticamente la IP de red local (ej. `http://192.168.1.15:8000/`).
   - El código QR generado en el panel `/admin` y en el reproductor `/player` apunta directamente a esa IP para que cualquier invitado conectado al WiFi escanee con su teléfono y pida canciones.

2. **Por Internet (remoto / streaming)**:
   - Si usas herramientas como Cloudflare Tunnel o Ngrok:
     ```bash
     cloudflared tunnel --url http://localhost:8000
     ```
   - Puedes configurar `PUBLIC_URL=https://tu-dominio.trycloudflare.com` en tu `.env` para que el QR apunte a tu dominio público.

---

## 🎹 Atajos de Teclado (Vista Reproductor `/player`)

| Tecla | Acción |
|---|---|
| `Espacio` | Reproducir / Pausar |
| `Shift` + `→` | Siguiente canción |
| Clic en barra de progreso | Saltar a ese segundo (*seek*) |
