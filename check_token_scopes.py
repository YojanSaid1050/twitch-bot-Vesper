#!/usr/bin/env python3
"""
Script para verificar los scopes y validez de los tokens de Twitch y Spotify.
Lee los tokens del archivo .env (o permite pasarlos como argumentos).
Muestra información detallada de cada token.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ python-dotenv no instalado. Ejecuta: pip install python-dotenv")
    sys.exit(1)

# ============================================================
# 1. LECTURA DEL .env
# ============================================================

def load_env(env_path: str = ".env") -> Dict[str, str]:
    env_vars = {}
    if Path(env_path).exists():
        load_dotenv(env_path)
        # Leer manualmente también
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
        return env_vars
    else:
        # Intentar desde variables de entorno del sistema
        for key in ["BOT_TOKEN", "BROADCASTER_TOKEN", "APP_ACCESS_TOKEN", "SPOTIFY_REFRESH_TOKEN"]:
            if os.environ.get(key):
                env_vars[key] = os.environ.get(key)
        return env_vars

# ============================================================
# 2. FUNCIONES PARA CURL
# ============================================================

def curl_get(url: str, headers: Dict[str, str]) -> Tuple[Optional[Dict], Optional[str]]:
    cmd = ["curl", "-s", "-X", "GET", url]
    for k, v in headers.items():
        cmd.extend(["-H", f"{k}: {v}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None, f"curl error: {result.stderr}"
        try:
            return json.loads(result.stdout), None
        except json.JSONDecodeError:
            return None, f"Respuesta no JSON: {result.stdout[:200]}"
    except subprocess.TimeoutExpired:
        return None, "Timeout"

def curl_post(url: str, data: Dict[str, str], headers: Optional[Dict[str, str]] = None) -> Tuple[Optional[Dict], Optional[str]]:
    cmd = ["curl", "-s", "-X", "POST", url]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    data_parts = [f"{k}={v}" for k, v in data.items()]
    cmd.extend(["-d", "&".join(data_parts)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None, f"curl error: {result.stderr}"
        try:
            return json.loads(result.stdout), None
        except json.JSONDecodeError:
            return None, f"Respuesta no JSON: {result.stdout[:200]}"
    except subprocess.TimeoutExpired:
        return None, "Timeout"

# ============================================================
# 3. VALIDAR TOKEN DE TWITCH
# ============================================================

def validate_twitch_token(access_token: str) -> Tuple[Optional[Dict], Optional[str]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    response, error = curl_get("https://id.twitch.tv/oauth2/validate", headers)
    if error:
        return None, error
    if response and "client_id" in response:
        return response, None
    return None, "Token inválido"

# ============================================================
# 4. VERIFICAR TOKEN DE SPOTIFY (haciendo una llamada simple)
# ============================================================

def check_spotify_token(access_token: str) -> Tuple[Optional[Dict], Optional[str]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    response, error = curl_get("https://api.spotify.com/v1/me", headers)
    if error:
        return None, error
    if response and "id" in response:
        return response, None
    return None, "Token inválido o sin permisos"

def refresh_spotify_token(client_id: str, client_secret: str, refresh_token: str) -> Tuple[Optional[Dict], Optional[str]]:
    import base64
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    return curl_post("https://accounts.spotify.com/api/token", data, headers)

# ============================================================
# 5. MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Verifica los scopes y validez de los tokens de Twitch y Spotify.")
    parser.add_argument("--env", default=".env", help="Ruta al archivo .env")
    parser.add_argument("--token", help="Token específico a verificar (si no se usa .env)")
    parser.add_argument("--type", choices=["bot", "broadcaster", "app", "spotify"], help="Tipo de token (si se usa --token)")
    args = parser.parse_args()

    if args.token and args.type:
        tokens = {args.type: args.token}
    else:
        env_vars = load_env(args.env)
        tokens = {
            "bot": env_vars.get("BOT_TOKEN"),
            "broadcaster": env_vars.get("BROADCASTER_TOKEN"),
            "app": env_vars.get("APP_ACCESS_TOKEN"),
            "spotify": env_vars.get("SPOTIFY_REFRESH_TOKEN"),  # Solo refresh, necesitamos access
        }
        # Obtener access token de Spotify si tenemos refresh
        if tokens["spotify"]:
            spotify_client_id = env_vars.get("SPOTIFY_CLIENT_ID")
            spotify_client_secret = env_vars.get("SPOTIFY_CLIENT_SECRET")
            if spotify_client_id and spotify_client_secret:
                print("🔄 Refrescando token de Spotify para obtener access_token...")
                token_data, error = refresh_spotify_token(spotify_client_id, spotify_client_secret, tokens["spotify"])
                if error:
                    print(f"❌ Error refrescando Spotify: {error}")
                    tokens["spotify"] = None
                else:
                    tokens["spotify"] = token_data.get("access_token")
                    print("✅ Access token de Spotify obtenido.")
            else:
                print("⚠️ No se encontraron SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en .env para refrescar.")
                tokens["spotify"] = None

    # Verificar Twitch tokens
    for token_type in ["bot", "broadcaster", "app"]:
        token = tokens.get(token_type)
        if not token:
            print(f"❌ No se encontró token para {token_type}")
            continue
        print(f"\n{'='*60}")
        print(f"🔍 Verificando token: {token_type.upper()}")
        print(f"{'='*60}")
        info, error = validate_twitch_token(token)
        if error:
            print(f"❌ Error: {error}")
            continue
        print(f"✅ Token válido")
        print(f"  - Cliente ID: {info.get('client_id')}")
        print(f"  - Usuario ID: {info.get('user_id')}")
        print(f"  - Login: {info.get('login', 'No disponible')}")
        scopes = info.get('scopes', [])
        if scopes:
            print(f"  - Scopes ({len(scopes)}):")
            for scope in sorted(scopes):
                print(f"    • {scope}")
        else:
            print("  - Scopes: Ninguno (token de aplicación o sin scopes)")
        expires_in = info.get('expires_in')
        if expires_in:
            hours = expires_in // 3600
            minutes = (expires_in % 3600) // 60
            print(f"  - Expira en: {hours}h {minutes}m")

    # Verificar Spotify
    spotify_token = tokens.get("spotify")
    if spotify_token:
        print(f"\n{'='*60}")
        print(f"🔍 Verificando token: SPOTIFY")
        print(f"{'='*60}")
        info, error = check_spotify_token(spotify_token)
        if error:
            print(f"❌ Error: {error}")
            # Intentar refrescar
            spotify_refresh = env_vars.get("SPOTIFY_REFRESH_TOKEN")
            if spotify_refresh:
                print("🔄 Intentando refrescar token de Spotify...")
                spotify_client_id = env_vars.get("SPOTIFY_CLIENT_ID")
                spotify_client_secret = env_vars.get("SPOTIFY_CLIENT_SECRET")
                if spotify_client_id and spotify_client_secret:
                    token_data, error2 = refresh_spotify_token(spotify_client_id, spotify_client_secret, spotify_refresh)
                    if error2:
                        print(f"❌ Error refrescando: {error2}")
                    else:
                        print("✅ Spotify refrescado. Verificando de nuevo...")
                        new_token = token_data.get("access_token")
                        info, error = check_spotify_token(new_token)
                        if error:
                            print(f"❌ Error después de refrescar: {error}")
                        else:
                            print("✅ Token de Spotify válido")
                            print(f"  - Usuario: {info.get('display_name', info.get('id', 'Desconocido'))}")
                            print(f"  - ID: {info.get('id')}")
                            print(f"  - Email: {info.get('email', 'No disponible')}")
                            print(f"  - País: {info.get('country', 'No disponible')}")
                else:
                    print("⚠️ No se encontraron credenciales de Spotify en .env para refrescar.")
        else:
            print("✅ Token de Spotify válido")
            print(f"  - Usuario: {info.get('display_name', info.get('id', 'Desconocido'))}")
            print(f"  - ID: {info.get('id')}")
            print(f"  - Email: {info.get('email', 'No disponible')}")
            print(f"  - País: {info.get('country', 'No disponible')}")

    print("\n✨ Verificación completada.")

if __name__ == "__main__":
    main()