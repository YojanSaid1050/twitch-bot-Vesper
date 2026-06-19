#!/usr/bin/env python3
"""
Script para regenerar tokens de Twitch y Spotify con todos los scopes necesarios.
Basado en la documentación oficial de Twitch Helix API (2026).
"""

import os
import re
import json
import base64
import subprocess
import webbrowser
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple

# ============================================================
# 1. LECTURA DEL .env ACTUAL
# ============================================================

def load_env(env_path: str = ".env") -> Dict[str, str]:
    env_vars = {}
    if not Path(env_path).exists():
        print(f"❌ No se encontró el archivo {env_path}")
        exit(1)

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()
    return env_vars

# ============================================================
# 2. FUNCIONES PARA CURL
# ============================================================

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
            response = json.loads(result.stdout)
            if "error" in response:
                error_msg = response.get("error_description") or response.get("error") or "Error desconocido"
                return None, error_msg
            return response, None
        except json.JSONDecodeError:
            return None, f"Respuesta no JSON: {result.stdout[:200]}"
    except subprocess.TimeoutExpired:
        return None, "Timeout"

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

# ============================================================
# 3. TWITCH - AUTORIZACIÓN Y CANJE DE CÓDIGO
# ============================================================

def build_twitch_auth_url(client_id: str, scopes: list, redirect_uri: str = "http://localhost") -> str:
    scope_str = " ".join(scopes)
    encoded_scopes = urllib.parse.quote(scope_str, safe="")
    return (
        f"https://id.twitch.tv/oauth2/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={encoded_scopes}"
    )

def exchange_twitch_code(client_id: str, client_secret: str, code: str, redirect_uri: str = "http://localhost") -> Tuple[Optional[Dict], Optional[str]]:
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }
    return curl_post("https://id.twitch.tv/oauth2/token", data)

def twitch_authorization_flow(client_id: str, client_secret: str, scopes: list, name: str, browser_name: str = None) -> Tuple[Optional[Dict], Optional[str]]:
    redirect_uri = "http://localhost"
    auth_url = build_twitch_auth_url(client_id, scopes, redirect_uri)

    print(f"\n{'='*60}")
    print(f"🔐 AUTORIZACIÓN PARA: {name}")
    print(f"{'='*60}")
    print(f"📋 URL de autorización (copia y pega en el navegador si no se abre):")
    print(f"\n{auth_url}\n")

    try:
        if browser_name:
            if browser_name.lower() == "brave":
                webbrowser.register('brave', None, webbrowser.GenericBrowser('brave-browser'))
                webbrowser.get('brave').open(auth_url)
            elif browser_name.lower() == "chrome":
                webbrowser.register('chrome', None, webbrowser.GenericBrowser('google-chrome'))
                webbrowser.get('chrome').open(auth_url)
            else:
                webbrowser.open(auth_url)
        else:
            webbrowser.open(auth_url)
        print("🌐 Navegador abierto (si no se abre, copia la URL de arriba)")
    except Exception as e:
        print(f"⚠️ No se pudo abrir el navegador: {e}")

    print("\n🔑 Después de autorizar, serás redirigido a una URL con 'code='.")
    print("👉 Copia el valor completo del parámetro 'code' o pega toda la URL.")
    code_input = input("\n📥 Pega el código (o la URL completa): ").strip()

    if "code=" in code_input:
        match = re.search(r"code=([^&]+)", code_input)
        if match:
            code = match.group(1)
        else:
            return None, "No se pudo extraer el código de la URL"
    else:
        code = code_input

    if not code:
        return None, "Código vacío"

    print("🔄 Canjeando código por tokens...")
    return exchange_twitch_code(client_id, client_secret, code, redirect_uri)

# ============================================================
# 4. TWITCH - APP ACCESS TOKEN (client_credentials)
# ============================================================

def get_app_access_token(client_id: str, client_secret: str) -> Tuple[Optional[str], Optional[str]]:
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    response, error = curl_post("https://id.twitch.tv/oauth2/token", data)
    if error:
        return None, error
    if response and "access_token" in response:
        return response["access_token"], None
    return None, "No se obtuvo access_token"

# ============================================================
# 5. TWITCH - VALIDAR TOKEN
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
# 6. SPOTIFY - AUTORIZACIÓN Y CANJE
# ============================================================

SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

def build_spotify_auth_url(client_id: str, scopes: list) -> str:
    scope_str = " ".join(scopes)
    encoded_scopes = urllib.parse.quote(scope_str, safe="")
    return (
        f"https://accounts.spotify.com/authorize?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"redirect_uri={SPOTIFY_REDIRECT_URI}&"
        f"scope={encoded_scopes}"
    )

def exchange_spotify_code(client_id: str, client_secret: str, code: str) -> Tuple[Optional[Dict], Optional[str]]:
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI
    }
    return curl_post("https://accounts.spotify.com/api/token", data, headers)

def spotify_authorization_flow(client_id: str, client_secret: str, scopes: list) -> Tuple[Optional[Dict], Optional[str]]:
    auth_url = build_spotify_auth_url(client_id, scopes)

    print(f"\n{'='*60}")
    print(f"🔐 AUTORIZACIÓN PARA: SPOTIFY")
    print(f"{'='*60}")
    print(f"📋 URL de autorización (copia y pega en el navegador):")
    print(f"\n{auth_url}\n")
    print(f"📌 Redirect URI registrado: {SPOTIFY_REDIRECT_URI}")

    try:
        webbrowser.open(auth_url)
        print("🌐 Navegador abierto (si no se abre, copia la URL de arriba)")
    except Exception as e:
        print(f"⚠️ No se pudo abrir el navegador: {e}")

    print("\n🔑 Después de autorizar, serás redirigido a una URL con 'code='.")
    code_input = input("📥 Pega el código (o la URL completa): ").strip()

    if "code=" in code_input:
        match = re.search(r"code=([^&]+)", code_input)
        if match:
            code = match.group(1)
        else:
            return None, "No se pudo extraer el código"
    else:
        code = code_input

    if not code:
        return None, "Código vacío"

    print("🔄 Canjeando código por tokens...")
    return exchange_spotify_code(client_id, client_secret, code)

# ============================================================
# 7. GENERAR .env ACTUALIZADO
# ============================================================

def build_env_content(env_vars: Dict[str, str], updates: Dict[str, str]) -> str:
    with open(".env", "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    updated_keys = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            key, _, _ = stripped.partition("=")
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")
    return "".join(new_lines)

# ============================================================
# 8. SCOPES CORREGIDOS SEGÚN DOCUMENTACIÓN OFICIAL TWITCH 2026
# ============================================================

BROADCASTER_SCOPES = [
    # ===== Bits y comerciales =====
    "bits:read",
    "channel:edit:commercial",

    # ===== Gestión del canal =====
    "channel:manage:broadcast",
    "channel:manage:moderators",
    "channel:manage:polls",
    "channel:manage:predictions",
    "channel:manage:raids",
    "channel:manage:redemptions",
    "channel:manage:schedule",
    "channel:manage:vips",

    # ===== Lectura del canal =====
    "channel:read:goals",
    "channel:read:hype_train",
    "channel:read:polls",
    "channel:read:predictions",
    "channel:read:redemptions",
    "channel:read:stream_key",
    "channel:read:subscriptions",
    "channel:read:vips",

    # ===== Chat =====
    "chat:read",
    "chat:edit",

    # ===== Clips =====
    "clips:edit",

    # ===== Moderación general =====
    "moderation:read",

    # ===== MODERACIÓN ESPECÍFICA (según docs oficiales 2026) =====
    # Para channel.follow
    "moderator:read:followers",

    # Para channel.ban y channel.unban
    "moderator:manage:banned_users",

    # Para channel.chat.message_delete, channel.chat.clear, channel.chat.clear_user_messages
    "moderator:manage:chat_messages",

    # Para channel.chat_settings.update
    "moderator:manage:chat_settings",

    # Para channel.shoutout.create y channel.shoutout.receive
    "moderator:manage:shoutouts",

    # Para channel.shield_mode.begin y channel.shield_mode.end
    "moderator:manage:shield_mode",

    # Para channel.unban_request.create y channel.unban_request.resolve
    "moderator:manage:unban_requests",

    # Para channel.suspicious_user.message y channel.suspicious_user.update
    "moderator:read:suspicious_users",

    # Para automod.message.hold y automod.message.update
    "moderator:manage:automod",

    # Para leer usuarios en el chat
    "moderator:read:chatters",

    # Para leer mensajes del chat
    "moderator:read:chat_messages",

    # Para leer baneados
    "moderator:read:banned_users",

    # ===== Usuario =====
    "user:read:blocked_users",
    "user:read:email",
    "user:read:follows"
]

BOT_SCOPES = [
    # ===== Chat =====
    "chat:read",
    "chat:edit",

    # ===== Gestión del canal (para moderación) =====
    "channel:manage:moderators",
    "channel:manage:predictions",
    "channel:manage:redemptions",
    "channel:read:subscriptions",

    # ===== Moderación general =====
    "moderation:read",

    # ===== Moderación específica =====
    "moderator:manage:announcements",
    "moderator:manage:banned_users",
    "moderator:manage:chat_messages",
    "moderator:manage:chat_settings",
    "moderator:manage:shoutouts",

    "moderator:read:banned_users",
    "moderator:read:chat_messages",
    "moderator:read:chatters",
    "moderator:read:followers"
]

SPOTIFY_SCOPES = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-currently-playing"
]

# ============================================================
# 9. MAIN
# ============================================================

def main():
    print("="*60)
    print("🔄  REGENERADOR DE TOKENS - Scopes actualizados 2026")
    print("="*60)
    print("\n⚠️ Este script regenerará TODOS los tokens desde cero.")
    print("   Necesitarás autorizar manualmente en el navegador.\n")

    env = load_env()
    required = ["CLIENT_ID", "CLIENT_SECRET", "BOT_NICK", "CHANNEL",
                "BROADCASTER_ID", "BOT_ID", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"]
    for r in required:
        if r not in env:
            print(f"❌ Falta {r} en el .env")
            return

    client_id = env["CLIENT_ID"]
    client_secret = env["CLIENT_SECRET"]

    # ============================================================
    #  TWITCH BROADCASTER
    # ============================================================
    print("\n[1] REGENERANDO TOKEN DE BROADCASTER (xyojansaidx)")
    print(f"   Scopes: {len(BROADCASTER_SCOPES)} permisos")
    print("\n📋 Scopes solicitados:")
    for scope in sorted(BROADCASTER_SCOPES):
        print(f"   - {scope}")

    broadcaster_token_data, error = twitch_authorization_flow(
        client_id, client_secret, BROADCASTER_SCOPES,
        "BROADCASTER (xyojansaidx)",
        browser_name="brave"
    )
    if error:
        print(f"❌ Error: {error}")
        return

    broadcaster_access = broadcaster_token_data.get("access_token")
    broadcaster_refresh = broadcaster_token_data.get("refresh_token")
    if not broadcaster_access or not broadcaster_refresh:
        print("❌ No se obtuvieron tokens completos para el Broadcaster")
        return

    broadcaster_info, error = validate_twitch_token(broadcaster_access)
    if error:
        print(f"⚠️ No se pudo validar el token: {error}")
    else:
        scopes_obtenidos = broadcaster_info.get('scopes', [])
        print(f"\n✅ Token de Broadcaster válido:")
        print(f"   - Usuario ID: {broadcaster_info.get('user_id')}")
        print(f"   - Scopes obtenidos: {len(scopes_obtenidos)}")
        
        # Verificar scopes faltantes
        scopes_faltantes = [s for s in BROADCASTER_SCOPES if s not in scopes_obtenidos]
        if scopes_faltantes:
            print(f"\n⚠️ Scopes NO otorgados (puede que no los necesites o no estén disponibles):")
            for s in scopes_faltantes:
                print(f"   - {s}")
        else:
            print("   ✅ Todos los scopes solicitados fueron otorgados")
        
        print(f"   - Expira en: {broadcaster_info.get('expires_in')} segundos")

    # ============================================================
    #  TWITCH BOT
    # ============================================================
    print("\n[2] REGENERANDO TOKEN DE BOT (VesperBotx)")
    print(f"   Scopes: {len(BOT_SCOPES)} permisos")

    bot_token_data, error = twitch_authorization_flow(
        client_id, client_secret, BOT_SCOPES,
        "BOT (VesperBotx)",
        browser_name="chrome"
    )
    if error:
        print(f"❌ Error: {error}")
        return

    bot_access = bot_token_data.get("access_token")
    bot_refresh = bot_token_data.get("refresh_token")
    if not bot_access or not bot_refresh:
        print("❌ No se obtuvieron tokens completos para el Bot")
        return

    bot_info, error = validate_twitch_token(bot_access)
    if error:
        print(f"⚠️ No se pudo validar el token: {error}")
    else:
        print(f"✅ Token de Bot válido:")
        print(f"   - Usuario ID: {bot_info.get('user_id')}")
        print(f"   - Scopes: {len(bot_info.get('scopes', []))}")
        print(f"   - Expira en: {bot_info.get('expires_in')} segundos")

    # ============================================================
    #  APP ACCESS TOKEN
    # ============================================================
    print("\n[3] GENERANDO APP ACCESS TOKEN")
    app_token, error = get_app_access_token(client_id, client_secret)
    if error:
        print(f"❌ Error: {error}")
        return
    print(f"✅ App Access Token generado")

    # ============================================================
    #  SPOTIFY
    # ============================================================
    print("\n[4] REGENERANDO TOKEN DE SPOTIFY")
    spotify_client_id = env["SPOTIFY_CLIENT_ID"]
    spotify_client_secret = env["SPOTIFY_CLIENT_SECRET"]

    spotify_token_data, error = spotify_authorization_flow(
        spotify_client_id, spotify_client_secret, SPOTIFY_SCOPES
    )
    if error:
        print(f"❌ Error: {error}")
        return

    spotify_access = spotify_token_data.get("access_token")
    spotify_refresh = spotify_token_data.get("refresh_token")
    if not spotify_access:
        print("❌ No se obtuvo access_token para Spotify")
        return
    if not spotify_refresh:
        print("⚠️ No se recibió refresh_token de Spotify. Reintentando...")
        spotify_token_data, error = spotify_authorization_flow(
            spotify_client_id, spotify_client_secret, SPOTIFY_SCOPES
        )
        if error:
            print(f"❌ Error: {error}")
            return
        spotify_access = spotify_token_data.get("access_token")
        spotify_refresh = spotify_token_data.get("refresh_token")
        if not spotify_refresh:
            print("❌ No se pudo obtener refresh_token de Spotify")
            return

    print(f"✅ Token de Spotify renovado (refresh_token obtenido)")

    # ============================================================
    #  CONSTRUIR .env
    # ============================================================
    print("\n[5] GENERANDO NUEVO .env")
    updates = {
        "BOT_TOKEN": bot_access,
        "BOT_REFRESH_TOKEN": bot_refresh,
        "BROADCASTER_TOKEN": broadcaster_access,
        "BROADCASTER_REFRESH_TOKEN": broadcaster_refresh,
        "APP_ACCESS_TOKEN": app_token,
        "SPOTIFY_REFRESH_TOKEN": spotify_refresh,
    }

    new_env = build_env_content(env, updates)

    print("\n" + "="*60)
    print("📄 NUEVO .env (copiar y pegar):")
    print("="*60)
    print(new_env)
    print("="*60)

    save = input("\n💾 ¿Guardar este nuevo .env? (s/N): ").strip().lower()
    if save in ("s", "si", "y", "yes"):
        with open(".env.new", "w", encoding="utf-8") as f:
            f.write(new_env)
        print("✅ .env.new guardado. Reemplaza manualmente si lo deseas.")

    print("\n✨ Proceso completado.")

if __name__ == "__main__":
    main()