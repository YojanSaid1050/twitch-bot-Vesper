#!/usr/bin/env python3
"""
Generador de tokens OAuth para Twitch (versión manual)
- Genera la URL de autorización y la abre en el navegador que elijas.
- Tú copias el código de la URL de redirección y lo pegas en el script.
- Intercambia el código por tokens y actualiza el archivo .env.
"""

import os
import subprocess
import webbrowser
import requests
from pathlib import Path

# ============================================
# CONFIGURACIÓN - AJUSTA SEGÚN TU APP
# ============================================
CLIENT_ID = "rbh1xnq6nyre67hz3q8btq7id6n1r1"
CLIENT_SECRET = "90zk3l5khv8wrua0zaf59vlumwym79"

# **IMPORTANTE**: Debe coincidir EXACTAMENTE con el redirect_uri registrado en la app de Twitch.
# Si tu app usa "http://localhost:3000" cámbialo aquí.
REDIRECT_URI = "http://localhost:3000"  # O "http://localhost:8080/callback" o el que tengas

# Scopes para el streamer (lectura y gestión)
SCOPES_STREAMER = [
    "bits:read",
    "channel:edit:commercial",
    "channel:manage:broadcast",
    "channel:manage:moderators",
    "channel:manage:polls",
    "channel:manage:predictions",
    "channel:manage:raids",
    "channel:manage:redemptions",
    "channel:manage:schedule",
    "channel:manage:vips",
    "channel:read:goals",
    "channel:read:hype_train",
    "channel:read:polls",
    "channel:read:predictions",
    "channel:read:redemptions",
    "channel:read:stream_key",
    "channel:read:subscriptions",
    "channel:read:vips",
    "chat:edit",
    "chat:read",
    "clips:edit",
    "moderation:read",
    "moderator:read:followers",
    "user:read:blocked_users",
    "user:read:email",
    "user:read:follows"
]

# Scopes para el bot (moderación y chat)
SCOPES_BOT = [
    "channel:manage:moderators",
    "channel:manage:predictions",
    "channel:manage:redemptions",
    "channel:read:subscriptions",
    "chat:edit",
    "chat:read",
    "moderation:read",
    "moderator:manage:announcements",
    "moderator:manage:banned_users",
    "moderator:manage:chat_messages",
    "moderator:manage:chat_settings",
    "moderator:manage:shoutouts",
    "moderator:read:followers"
]

# Rutas de navegadores (Windows) - ajústalas si es necesario
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# Archivo .env
ENV_PATH = Path(__file__).parent / ".env"

# ============================================
# FUNCIONES
# ============================================

def open_browser(url, browser_path=None):
    """Abre una URL en el navegador especificado o en el predeterminado."""
    if browser_path and os.path.exists(browser_path):
        subprocess.Popen([browser_path, url], shell=False)
    else:
        if browser_path:
            print(f"⚠️ No se encontró el navegador en {browser_path}. Usando el predeterminado.")
        webbrowser.open(url)

def build_auth_url(scopes):
    """Construye la URL de autorización con los scopes dados."""
    scope_str = " ".join(scopes)
    url = (
        "https://id.twitch.tv/oauth2/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        "response_type=code&"
        f"scope={scope_str}&"
        "force_verify=true"
    )
    return url

def exchange_code_for_token(code):
    """Intercambia el código por tokens usando la API de Twitch."""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post("https://id.twitch.tv/oauth2/token", data=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"ERROR: {response.status_code} - {response.text}")
        return None

def get_app_access_token():
    """Obtiene un App Access Token (client_credentials)."""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post("https://id.twitch.tv/oauth2/token", data=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"ERROR al obtener App Token: {response.status_code} - {response.text}")
        return None

def update_env_file(updates):
    """Actualiza el archivo .env con los nuevos tokens (sin borrar otras variables)."""
    if not ENV_PATH.exists():
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write("# Tokens generados manualmente\n")

    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    updated_keys = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        key, _, val = stripped.partition("=")
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"✅ {ENV_PATH} actualizado.")

# ============================================
# MENÚ PRINCIPAL
# ============================================

def main():
    print("=" * 60)
    print("🔑 GENERADOR MANUAL DE TOKENS PARA TWITCH")
    print("=" * 60)
    print(f"CLIENT_ID: {CLIENT_ID}")
    print(f"REDIRECT_URI: {REDIRECT_URI}")
    print("Asegúrate de que el redirect_uri coincida con el registrado en tu app de Twitch.")
    print("=" * 60)

    print("\nOpciones:")
    print("1. Generar token del STREAMER (abre Brave)")
    print("2. Generar token del BOT (abre Chrome)")
    print("3. Generar ambos tokens (streamer primero, luego bot)")
    print("4. Generar solo App Access Token (client_credentials)")
    print("5. Salir")

    choice = input("\nSelecciona una opción (1-5): ").strip()

    if choice == "5":
        print("👋 Hasta luego.")
        return

    # Generar App Token si se va a usar
    app_token = None
    if choice in ["1", "2", "3"]:
        print("\n🔐 Generando App Access Token (client_credentials)...")
        app_data = get_app_access_token()
        if app_data:
            app_token = app_data["access_token"]
            print("✅ App Access Token generado.")
        else:
            print("⚠️ No se pudo generar App Token. Continuamos sin él.")

    if choice == "4":
        if app_token:
            update_env_file({"APP_ACCESS_TOKEN": app_token})
            print("✅ App Access Token guardado.")
        else:
            print("❌ No se pudo generar App Token.")
        return

    # Función auxiliar para obtener token de un tipo
    def get_token_for(label, scopes, browser_path, env_keys):
        print("\n" + "=" * 60)
        print(f"🎯 Generando token para {label}")
        print("=" * 60)

        url = build_auth_url(scopes)
        print("\n📌 Abriendo navegador...")
        open_browser(url, browser_path)

        print(f"\n✅ Si no se abrió, copia esta URL en el navegador:\n{url}\n")
        code = input("👉 Pega el código de la URL (ej: ...?code=XXXXX): ").strip()

        # Limpiar posibles parámetros adicionales
        if "?code=" in code:
            code = code.split("?code=")[1]
        if "&" in code:
            code = code.split("&")[0]
        code = code.strip()

        if not code:
            print("❌ Código vacío. Cancelando.")
            return False

        print("🔄 Intercambiando código por tokens...")
        token_data = exchange_code_for_token(code)
        if not token_data:
            print("❌ Falló el intercambio. Verifica el código y el redirect_uri.")
            return False

        print("✅ Tokens obtenidos correctamente.")
        updates = {
            env_keys["access"]: token_data["access_token"],
            env_keys["refresh"]: token_data["refresh_token"]
        }
        if app_token:
            updates["APP_ACCESS_TOKEN"] = app_token

        update_env_file(updates)
        print(f"✅ Tokens de {label} guardados en .env.")
        return True

    # Ejecutar según opción
    if choice in ["1", "3"]:
        ok = get_token_for(
            "STREAMER",
            SCOPES_STREAMER,
            BRAVE_PATH,
            {"access": "BROADCASTER_TOKEN", "refresh": "BROADCASTER_REFRESH_TOKEN"}
        )
        if not ok:
            print("❌ Falló la generación del token del streamer.")
            return

    if choice in ["2", "3"]:
        ok = get_token_for(
            "BOT",
            SCOPES_BOT,
            CHROME_PATH,
            {"access": "BOT_TOKEN", "refresh": "BOT_REFRESH_TOKEN"}
        )
        if not ok:
            print("❌ Falló la generación del token del bot.")
            return

    print("\n🎉 Todos los tokens generados y guardados en .env")
    print("Reinicia el bot para usar los nuevos tokens.")

if __name__ == "__main__":
    main()