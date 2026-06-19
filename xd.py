#!/usr/bin/env python3
"""
Script para verificar y refrescar tokens de Twitch
- Refresca los tokens usando los refresh tokens del .env
- Verifica los scopes obtenidos
- Muestra qué scopes faltan
"""

import os
import re
import json
import base64
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime

# ============================================================
# 1. LECTURA DEL .env
# ============================================================

def load_env(env_path: str = ".env") -> Dict[str, str]:
    env_vars = {}
    if not Path(env_path).exists():
        print(f"❌ No se encontró el archivo {env_path}")
        sys.exit(1)

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
# 3. REFRESCAR TOKENS DE TWITCH
# ============================================================

def refresh_twitch_token(client_id: str, client_secret: str, refresh_token: str, token_type: str) -> Tuple[Optional[Dict], Optional[str]]:
    """Refresca un token de Twitch usando el refresh_token."""
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    response, error = curl_post("https://id.twitch.tv/oauth2/token", data)
    if error:
        return None, error
    if response and "access_token" in response:
        return response, None
    return None, "No se obtuvo access_token"

# ============================================================
# 4. VALIDAR TOKEN Y OBTENER SCOPES
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
# 5. SCOPES REQUERIDOS
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

    # ===== MODERACIÓN ESPECÍFICA =====
    "moderator:read:followers",
    "moderator:manage:banned_users",
    "moderator:manage:chat_messages",
    "moderator:manage:chat_settings",
    "moderator:manage:shoutouts",
    "moderator:manage:shield_mode",
    "moderator:manage:unban_requests",
    "moderator:read:suspicious_users",
    "moderator:manage:automod",
    "moderator:read:chatters",
    "moderator:read:chat_messages",
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

    # ===== Gestión del canal =====
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

# ============================================================
# 6. FUNCIONES DE ANÁLISIS
# ============================================================

def analyze_scopes(obtained_scopes: List[str], required_scopes: List[str], token_type: str) -> Dict:
    """Analiza qué scopes faltan y cuáles están presentes."""
    obtained_set = set(obtained_scopes)
    required_set = set(required_scopes)
    
    present = sorted(list(obtained_set & required_set))
    missing = sorted(list(required_set - obtained_set))
    extra = sorted(list(obtained_set - required_set))
    
    return {
        "present": present,
        "missing": missing,
        "extra": extra,
        "total_obtained": len(obtained_scopes),
        "total_required": len(required_scopes),
        "total_present": len(present),
        "total_missing": len(missing),
        "is_complete": len(missing) == 0
    }

def print_analysis(analysis: Dict, token_type: str):
    """Imprime el análisis de scopes de forma legible."""
    print(f"\n{'='*70}")
    print(f"📊 ANÁLISIS DE SCOPES: {token_type.upper()}")
    print(f"{'='*70}")
    
    print(f"\n📋 Resumen:")
    print(f"   • Scopes requeridos: {analysis['total_required']}")
    print(f"   • Scopes obtenidos: {analysis['total_obtained']}")
    print(f"   • Scopes presentes: {analysis['total_present']} ✅")
    print(f"   • Scopes faltantes: {analysis['total_missing']} ❌")
    print(f"   • Estado: {'✅ COMPLETO' if analysis['is_complete'] else '❌ INCOMPLETO'}")
    
    if analysis['present']:
        print(f"\n✅ Scopes PRESENTES ({len(analysis['present'])}):")
        for scope in analysis['present']:
            print(f"   ✓ {scope}")
    
    if analysis['missing']:
        print(f"\n❌ Scopes FALTANTES ({len(analysis['missing'])}):")
        for scope in analysis['missing']:
            print(f"   ✗ {scope}")
    
    if analysis['extra']:
        print(f"\n📌 Scopes ADICIONALES (no requeridos, {len(analysis['extra'])}):")
        for scope in analysis['extra']:
            print(f"   • {scope}")

# ============================================================
# 7. GENERAR URL DE AUTORIZACIÓN
# ============================================================

def generate_auth_url(client_id: str, scopes: List[str]) -> str:
    import urllib.parse
    scope_str = " ".join(scopes)
    encoded_scopes = urllib.parse.quote(scope_str, safe="")
    return f"https://id.twitch.tv/oauth2/authorize?client_id={client_id}&redirect_uri=http://localhost&response_type=code&scope={encoded_scopes}"

# ============================================================
# 8. MAIN
# ============================================================

def main():
    print("="*70)
    print("🔐 VERIFICADOR DE SCOPES DE TWITCH")
    print("="*70)
    print("\n⚠️ Este script refrescará los tokens usando los refresh tokens del .env")
    print("   y verificará los scopes obtenidos.\n")
    
    # Cargar .env
    env = load_env()
    
    # Verificar variables necesarias
    required = ["CLIENT_ID", "CLIENT_SECRET", "BOT_REFRESH_TOKEN", "BROADCASTER_REFRESH_TOKEN"]
    for r in required:
        if r not in env:
            print(f"❌ Falta {r} en el .env")
            return
    
    client_id = env["CLIENT_ID"]
    client_secret = env["CLIENT_SECRET"]
    
    print("📋 Configuración encontrada:")
    print(f"   • CLIENT_ID: {client_id[:8]}...")
    print(f"   • BOT_REFRESH_TOKEN: {env['BOT_REFRESH_TOKEN'][:12]}...")
    print(f"   • BROADCASTER_REFRESH_TOKEN: {env['BROADCASTER_REFRESH_TOKEN'][:12]}...")
    print()
    
    # ============================================================
    # REFRESCAR TOKEN DEL BOT
    # ============================================================
    print("[1] REFRESCANDO TOKEN DEL BOT...")
    print("-" * 50)
    
    bot_response, error = refresh_twitch_token(
        client_id, 
        client_secret, 
        env["BOT_REFRESH_TOKEN"],
        "bot"
    )
    
    if error:
        print(f"❌ Error refrescando token del bot: {error}")
        print("\n💡 Si el refresh token expiró, necesitas reautorizar manualmente.")
        print("   Ejecuta el script regenerate_tokens_updated.py")
        return
    
    bot_token = bot_response.get("access_token")
    bot_refresh = bot_response.get("refresh_token", env["BOT_REFRESH_TOKEN"])
    expires_in = bot_response.get("expires_in", 0)
    
    print(f"✅ Token del bot refrescado correctamente")
    print(f"   • Expira en: {expires_in//60} minutos")
    if bot_refresh != env["BOT_REFRESH_TOKEN"]:
        print(f"   • Nuevo refresh_token: {bot_refresh[:12]}... (actualizar en .env)")
    
    # Validar token del bot
    bot_info, error = validate_twitch_token(bot_token)
    if error:
        print(f"❌ Error validando token del bot: {error}")
        return
    
    bot_scopes = bot_info.get("scopes", [])
    user_id = bot_info.get("user_id")
    login = bot_info.get("login", "Desconocido")
    
    print(f"\n👤 Información del token:")
    print(f"   • Usuario: {login} (ID: {user_id})")
    print(f"   • Scopes obtenidos: {len(bot_scopes)}")
    
    # Analizar scopes del bot
    bot_analysis = analyze_scopes(bot_scopes, BOT_SCOPES, "bot")
    print_analysis(bot_analysis, "BOT")
    
    # ============================================================
    # REFRESCAR TOKEN DEL BROADCASTER
    # ============================================================
    print("\n[2] REFRESCANDO TOKEN DEL BROADCASTER...")
    print("-" * 50)
    
    broadcaster_response, error = refresh_twitch_token(
        client_id, 
        client_secret, 
        env["BROADCASTER_REFRESH_TOKEN"],
        "broadcaster"
    )
    
    if error:
        print(f"❌ Error refrescando token del broadcaster: {error}")
        print("\n💡 Si el refresh token expiró, necesitas reautorizar manualmente.")
        print("   Ejecuta el script regenerate_tokens_updated.py")
        return
    
    broadcaster_token = broadcaster_response.get("access_token")
    broadcaster_refresh = broadcaster_response.get("refresh_token", env["BROADCASTER_REFRESH_TOKEN"])
    expires_in = broadcaster_response.get("expires_in", 0)
    
    print(f"✅ Token del broadcaster refrescado correctamente")
    print(f"   • Expira en: {expires_in//60} minutos")
    if broadcaster_refresh != env["BROADCASTER_REFRESH_TOKEN"]:
        print(f"   • Nuevo refresh_token: {broadcaster_refresh[:12]}... (actualizar en .env)")
    
    # Validar token del broadcaster
    broadcaster_info, error = validate_twitch_token(broadcaster_token)
    if error:
        print(f"❌ Error validando token del broadcaster: {error}")
        return
    
    broadcaster_scopes = broadcaster_info.get("scopes", [])
    user_id = broadcaster_info.get("user_id")
    login = broadcaster_info.get("login", "Desconocido")
    
    print(f"\n👤 Información del token:")
    print(f"   • Usuario: {login} (ID: {user_id})")
    print(f"   • Scopes obtenidos: {len(broadcaster_scopes)}")
    
    # Analizar scopes del broadcaster
    broadcaster_analysis = analyze_scopes(broadcaster_scopes, BROADCASTER_SCOPES, "broadcaster")
    print_analysis(broadcaster_analysis, "BROADCASTER")
    
    # ============================================================
    # RESUMEN FINAL
    # ============================================================
    print("\n" + "="*70)
    print("📊 RESUMEN FINAL")
    print("="*70)
    
    print(f"\n🔹 TOKEN DEL BOT: {'✅ COMPLETO' if bot_analysis['is_complete'] else '❌ INCOMPLETO'}")
    if not bot_analysis['is_complete']:
        print(f"   • Scopes faltantes: {bot_analysis['total_missing']}")
        for scope in bot_analysis['missing'][:5]:
            print(f"     - {scope}")
        if len(bot_analysis['missing']) > 5:
            print(f"     ... y {len(bot_analysis['missing']) - 5} más")
    
    print(f"\n🔹 TOKEN DEL BROADCASTER: {'✅ COMPLETO' if broadcaster_analysis['is_complete'] else '❌ INCOMPLETO'}")
    if not broadcaster_analysis['is_complete']:
        print(f"   • Scopes faltantes: {broadcaster_analysis['total_missing']}")
        for scope in broadcaster_analysis['missing'][:5]:
            print(f"     - {scope}")
        if len(broadcaster_analysis['missing']) > 5:
            print(f"     ... y {len(broadcaster_analysis['missing']) - 5} más")
    
    # ============================================================
    # RECOMENDACIONES
    # ============================================================
    print("\n" + "="*70)
    print("💡 RECOMENDACIONES")
    print("="*70)
    
    if not bot_analysis['is_complete'] or not broadcaster_analysis['is_complete']:
        print("\n⚠️ Hay scopes faltantes. Para obtener todos los scopes necesarios:")
        print("\n   1. Ejecuta el script de regeneración de tokens:")
        print("      python regenerate_tokens_updated.py")
        print("\n   2. Durante la autorización, asegúrate de aceptar TODOS los permisos.")
        print("\n   3. Los scopes faltantes más comunes son los de moderación específica:")
        print("      - moderator:manage:banned_users")
        print("      - moderator:manage:chat_messages")
        print("      - moderator:manage:chat_settings")
        print("      - moderator:manage:shoutouts")
        print("      - moderator:manage:shield_mode")
        print("      - moderator:manage:unban_requests")
        print("      - moderator:read:suspicious_users")
        print("      - moderator:manage:automod")
        print("      - moderator:read:chatters")
        print("      - moderator:read:chat_messages")
        print("      - moderator:read:banned_users")
        
        # Generar URLs de autorización con los scopes faltantes
        print("\n📋 Para reautorizar manualmente, usa estas URLs:")
        
        # Si faltan scopes del bot
        if not bot_analysis['is_complete']:
            print(f"\n   🔹 URL para el BOT (VesperBotx):")
            bot_missing = bot_analysis['missing']
            if bot_missing:
                auth_url = generate_auth_url(client_id, bot_missing)
                print(f"   {auth_url}")
        
        # Si faltan scopes del broadcaster
        if not broadcaster_analysis['is_complete']:
            print(f"\n   🔹 URL para el BROADCASTER (xyojansaidx):")
            broadcaster_missing = broadcaster_analysis['missing']
            if broadcaster_missing:
                auth_url = generate_auth_url(client_id, broadcaster_missing)
                print(f"   {auth_url}")
    else:
        print("\n✅ ¡Todos los scopes están presentes!")
        print("   Los tokens son válidos y tienen todos los permisos necesarios.")
    
    # ============================================================
    # ACTUALIZAR .env con nuevos tokens
    # ============================================================
    print("\n" + "="*70)
    print("📝 ACTUALIZAR .env")
    print("="*70)
    
    # Verificar si los refresh tokens cambiaron
    needs_update = False
    if bot_refresh != env["BOT_REFRESH_TOKEN"]:
        print(f"\n🔄 El refresh_token del BOT ha cambiado:")
        print(f"   Antes: {env['BOT_REFRESH_TOKEN'][:12]}...")
        print(f"   Ahora: {bot_refresh[:12]}...")
        needs_update = True
    
    if broadcaster_refresh != env["BROADCASTER_REFRESH_TOKEN"]:
        print(f"\n🔄 El refresh_token del BROADCASTER ha cambiado:")
        print(f"   Antes: {env['BROADCASTER_REFRESH_TOKEN'][:12]}...")
        print(f"   Ahora: {broadcaster_refresh[:12]}...")
        needs_update = True
    
    if needs_update:
        print("\n💾 ¿Quieres actualizar el .env con los nuevos tokens?")
        response = input("   (s/N): ").strip().lower()
        if response in ("s", "si", "y", "yes"):
            # Leer el .env actual
            with open(".env", "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Actualizar las líneas
            new_lines = []
            for line in lines:
                if line.startswith("BOT_REFRESH_TOKEN="):
                    new_lines.append(f"BOT_REFRESH_TOKEN={bot_refresh}\n")
                elif line.startswith("BROADCASTER_REFRESH_TOKEN="):
                    new_lines.append(f"BROADCASTER_REFRESH_TOKEN={broadcaster_refresh}\n")
                elif line.startswith("BOT_TOKEN="):
                    new_lines.append(f"BOT_TOKEN={bot_token}\n")
                elif line.startswith("BROADCASTER_TOKEN="):
                    new_lines.append(f"BROADCASTER_TOKEN={broadcaster_token}\n")
                else:
                    new_lines.append(line)
            
            # Guardar
            with open(".env", "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            
            print("✅ .env actualizado correctamente")
    else:
        print("\n✅ Los refresh tokens no han cambiado.")
    
    print("\n✨ Verificación completada.")

if __name__ == "__main__":
    main()