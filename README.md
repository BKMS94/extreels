# Extreels

Extractor de enlaces y descargas de videos de TikTok desde mensajes privados usando Brave y Playwright.

## Descripción

Este proyecto automatiza la extracción de URLs de videos de TikTok dentro de la sección de mensajes privados, navegando por un chat seleccionado y descargando videos con `yt-dlp`.

## Características

- Conexión a Brave mediante `--remote-debugging-port`
- Uso de `playwright` para interactuar con la interfaz web de TikTok
- Extracción de enlaces TikTok en mensajes
- Descarga de videos con `yt-dlp` en formato MP4 compatible con reproductores generales
- Detección de duplicados mediante SQLite
- Registro de actividad en `logs/`

## Estructura del proyecto

- `main.py` - Script principal de automatización
- `requirements.txt` - Dependencias Python necesarias
- `.gitignore` - Exclusiones de Git para entornos, logs, bases de datos y videos
- `start_brave.ps1` - Script recomendado para iniciar Brave con depuración remota
- `descargados.db` - Base de datos SQLite de descargas (no versionada)
- `logs/` - Carpeta de registros de ejecución (no versionada)
- `videos_tiktok/` y `videos_mecanica/` - Carpetas de salida de video (no versionadas)

## Requisitos

- Python 3.10+ o 3.11
- Brave instalado
- `playwright` y `yt-dlp` instalados

## Instalación

1. Crear un entorno virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

3. Instalar navegadores de Playwright:

```powershell
python -m playwright install
```

## Uso

1. Iniciar Brave con depuración remota:

```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222
```

2. Ejecutar el script:

```powershell
python main.py
```

3. Seguir las instrucciones en consola y seleccionar manualmente el video inicial en la ventana de Brave.

## Buenas prácticas

- No subir `venv/`, `logs/`, `*.db`, ni los videos descargados.
- Usar `requirements.txt` para mantener dependencias consistentes.
- Mantener `main.py` como único punto de entrada.

## Nota

El proyecto está preparado para ejecutarse con Brave en modo remote debugging en el puerto `9222`. Asegúrate de cerrar cualquier otra instancia que use el mismo puerto antes de iniciar.
