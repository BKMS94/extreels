#!/usr/bin/env python3
"""
Extractor de videos TikTok desde mensajes privados
Flujo: Seleccionar video → Descargar → Click "Siguiente" → Repetir
"""

import time
import logging
import sqlite3
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
import yt_dlp

# Configurar UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ========== CONFIGURACIÓN ==========
CONFIG = {
    "nombre_chat": "chino",
    "carpeta_destino": "./videos_tiktok",
    "puerto_brave": 9222,
    "db_path": "./descargados.db",
    "pausa_entre_descargas": 2,
    "timeout_elementos": 10000,
}

# Crear carpetas necesarias
Path(CONFIG["carpeta_destino"]).mkdir(parents=True, exist_ok=True)
Path("./logs").mkdir(parents=True, exist_ok=True)

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"./logs/tiktok_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ========== BASE DE DATOS ==========
def ya_descargado(url):
    """Verifica si un video ya fue descargado antes"""
    try:
        conn = sqlite3.connect(CONFIG["db_path"])
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS descargados (url TEXT PRIMARY KEY, fecha TEXT)")
        c.execute("SELECT 1 FROM descargados WHERE url = ?", (url,))
        existe = c.fetchone() is not None
        conn.close()
        return existe
    except:
        return False

def marcar_descargado(url):
    """Registra video como descargado"""
    try:
        conn = sqlite3.connect(CONFIG["db_path"])
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO descargados VALUES (?, ?)", (url, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except:
        pass

# ========== DESCARGA ==========
def descargar_video(url, carpeta):
    """Descarga un video con yt-dlp"""
    if ya_descargado(url):
        log.info(f"⏭️  Saltando (ya descargado)")
        return True
    
    Path(carpeta).mkdir(parents=True, exist_ok=True)
    
    opts = {
        'outtmpl': f'{carpeta}/%(title)s.%(ext)s',
        'format': 'best',
        'quiet': False,
        'no_warnings': False,
    }
    
    try:
        log.info(f"📥 Descargando...")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        marcar_descargado(url)
        log.info(f"✅ Completado")
        return True
    except Exception as e:
        log.error(f"❌ Error: {str(e)[:100]}")
        return False

# ========== SELECTORES PARA TIKTOK ==========
def obtener_url_video_actual(page):
    """Obtiene la URL del video actualmente visible en el chat"""
    selectores = [
        'a[href*="tiktok.com/@"]',
        'a[href*="vm.tiktok.com"]',
        '[data-e2e="video-url"] a',
        '.message-item a[href*="tiktok"]'
    ]
    
    for selector in selectores:
        try:
            enlaces = page.locator(selector).all()
            for enlace in enlaces:
                if enlace.is_visible():
                    url = enlace.get_attribute("href")
                    if url and ("tiktok.com" in url):
                        return url
        except:
            continue
    
    # Método alternativo: buscar en todo el HTML
    try:
        content = page.content()
        import re
        match = re.search(r'https?://(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+', content)
        if match:
            return match.group(0)
    except:
        pass
    
    return None

def boton_siguiente_visible(page):
    """Verifica si el botón 'siguiente video' está presente"""
    selectores = [
        'button[data-e2e="arrow-right"]',
        'button[aria-label="Next"]',
        'button[aria-label="Siguiente"]',
        'div[role="button"][aria-label*="next"]',
        '[class*="arrow-right"] button',
        'button:has(svg[data-icon="chevron-right"])'
    ]
    
    for selector in selectores:
        try:
            btn = page.locator(selector).first
            if btn.count() and btn.is_visible():
                return btn
        except:
            continue
    return None

# ========== FUNCIONES DE NAVEGACIÓN ==========
def abrir_chat(page, nombre_chat):
    """Abre el chat de la persona especificada"""
    log.info(f"🔍 Buscando chat: '{nombre_chat}'")
    
    # Esperar que cargue la lista de chats
    time.sleep(3)
    
    # Selectores múltiples para encontrar el chat
    selectores_chat = [
        f'div:has-text("{nombre_chat}")',
        f'span:has-text("{nombre_chat}")',
        f'[data-e2e="chat-list"] div:has-text("{nombre_chat}")',
        f'.chat-list-item:has-text("{nombre_chat}")'
    ]
    
    for selector in selectores_chat:
        try:
            elemento = page.locator(selector).first
            if elemento.count():
                elemento.click(timeout=5000)
                log.info(f"✓ Chat '{nombre_chat}' abierto")
                time.sleep(2)
                return True
        except:
            continue
    
    log.error(f"❌ No se encontró el chat: {nombre_chat}")
    log.info("💡 Consejo: Asegúrate de que el nombre sea EXACTAMENTE como aparece en TikTok")
    log.info("💡 También puedes hacer click MANUALMENTE en el chat y luego presionar Enter")
    input(">>> Haz click MANUALMENTE en el chat y presiona ENTER <<<")
    return True

def esperar_seleccion_manual(page):
    """Pausa hasta que el usuario haga click en un video"""
    log.info("=" * 50)
    log.info("🎯 INSTRUCCIÓN:")
    log.info("   1. Ve a la ventana de Brave")
    log.info("   2. Haz CLICK en el PRIMER video que quieras descargar")
    log.info("   3. El video debe estar visible/enfocado")
    log.info("   4. Vuelve aquí y presiona ENTER")
    log.info("=" * 50)
    input(">>> Presiona ENTER después de seleccionar el video <<<")
    
    # Verificar que se detectó un video
    url = obtener_url_video_actual(page)
    if url:
        log.info(f"✓ Video detectado: {url[:80]}...")
    else:
        log.warning("⚠️ No se detectó automáticamente, pero continuamos...")
    return url

# ========== FUNCIÓN PARA ABRIR BRAVE ==========
def abrir_brave():
    """Abre Brave con depuración remota"""
    brave_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
    ]
    
    brave_exe = None
    for path in brave_paths:
        if Path(path).exists():
            brave_exe = path
            break
    
    if not brave_exe:
        log.error("❌ No se encontró Brave Browser")
        return False
    
    # Cerrar Brave si está abierto
    try:
        subprocess.run(["taskkill", "/f", "/im", "brave.exe"], capture_output=True)
        time.sleep(2)
    except:
        pass
    
    # Abrir Brave con depuración
    log.info(f"🚀 Abriendo Brave desde: {brave_exe}")
    subprocess.Popen([
        brave_exe,
        "--remote-debugging-port=9222",
        "--no-first-run",
        "--new-window",
        "https://www.tiktok.com/messages"
    ])
    
    time.sleep(5)
    return True

# ========== BUCLE PRINCIPAL ==========
def main():
    log.info("=" * 60)
    log.info("🎬 EXTRACTOR DE TIKTOK v2.0")
    log.info("=" * 60)
    
    # Abrir Brave automáticamente
    if not abrir_brave():
        log.error("No se pudo abrir Brave. Abrelo manualmente con:")
        log.error('brave.exe --remote-debugging-port=9222')
        input("Presiona Enter cuando Brave esté listo...")
    
    with sync_playwright() as p:
        navegador = None
        page = None
        try:
            # Intentar conectar varias veces
            for intento in range(3):
                try:
                    log.info(f"🔌 Intentando conectar a Brave (intento {intento+1}/3)...")
                    navegador = p.chromium.connect_over_cdp(f"http://localhost:{CONFIG['puerto_brave']}")
                    log.info("✅ Conectado a Brave correctamente")
                    break
                except Exception as e:
                    log.warning(f"Fallo conexión: {e}")
                    if intento < 2:
                        time.sleep(3)
                    else:
                        raise
            
            if not navegador:
                raise Exception("No se pudo conectar a Brave")
            
            # Obtener página
            page = navegador.contexts[0].new_page()
            page.set_default_timeout(CONFIG["timeout_elementos"])
            
            # Ir a mensajes
            log.info("📱 Navegando a TikTok Messages...")
            page.goto("https://www.tiktok.com/messages", wait_until="domcontentloaded")
            time.sleep(5)
            
            # Abrir chat
            if not abrir_chat(page, CONFIG["nombre_chat"]):
                return
            
            # Usuario selecciona el primer video
            esperar_seleccion_manual(page)
            
            # BUCLE: descargar y pasar al siguiente
            contador = 0
            urls_procesadas = set()
            sin_cambio_consecutivo = 0
            
            while True:
                contador += 1
                log.info(f"\n{'='*40}")
                log.info(f"📹 Video #{contador}")
                log.info(f"{'='*40}")
                
                # 1. Obtener URL actual
                url_actual = obtener_url_video_actual(page)
                if not url_actual:
                    log.warning("No se pudo obtener URL - puede ser el final")
                    break
                
                if url_actual in urls_procesadas:
                    sin_cambio_consecutivo += 1
                    log.info(f"⚠️ Video repetido ({sin_cambio_consecutivo}/3)")
                    if sin_cambio_consecutivo >= 3:
                        log.info("🏁 Deteniendo - no hay más videos nuevos")
                        break
                else:
                    sin_cambio_consecutivo = 0
                    urls_procesadas.add(url_actual)
                    log.info(f"🎯 Nuevo video encontrado")
                
                # 2. Descargar
                descargar_video(url_actual, CONFIG["carpeta_destino"])
                time.sleep(CONFIG["pausa_entre_descargas"])
                
                # 3. Buscar botón siguiente
                btn_sig = boton_siguiente_visible(page)
                if not btn_sig:
                    log.info("🏁 No hay más videos - botón 'siguiente' no disponible")
                    break
                
                # 4. Hacer click para avanzar
                log.info("⬇️ Pasando al siguiente video...")
                btn_sig.click()
                time.sleep(3)
                
                # Verificar que cambió el video
                nueva_url = obtener_url_video_actual(page)
                if nueva_url == url_actual:
                    log.warning("⚠️ El video no cambió - reintentando...")
                    time.sleep(2)
                    continue
            
            # Resumen final
            log.info("\n" + "=" * 60)
            log.info(f"✅ PROCESO COMPLETADO")
            log.info(f"📊 Videos procesados: {len(urls_procesadas)}")
            log.info(f"📁 Carpeta: {CONFIG['carpeta_destino']}")
            log.info(f"💾 Base de datos: {CONFIG['db_path']}")
            log.info("=" * 60)
            
        except Exception as e:
            log.error(f"❌ Error crítico: {e}", exc_info=True)
            log.info("💡 Soluciones:")
            log.info("   1. Cierra todas las ventanas de Brave")
            log.info("   2. Vuelve a ejecutar el script")
            log.info("   3. Si persiste, abre Brave manualmente con el flag --remote-debugging-port=9222")
            
        finally:
            if page:
                try:
                    page.close()
                except:
                    pass
            log.info("👋 Script finalizado")

# ========== ENTRADA ==========
if __name__ == "__main__":
    main()