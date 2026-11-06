# web/connections.py
"""
Conexiones: estado de los tokens y reconexión de cuentas desde el dashboard.

- El bot ya renueva solo los tokens con el refresh token (token_manager).
- Si el refresh token deja de servir (cambio de contraseña, permisos revocados,
  app desautorizada...), antes había que generar uno nuevo a mano y meterlo en
  PostgreSQL. Ahora basta con pulsar "Reconectar" en /connections: se abre el
  login de Twitch/Spotify y los tokens nuevos se guardan y activan sin reiniciar.

URLs de redirección que hay que registrar (se muestran también en la página):
    Twitch:  <URL pública>/oauth/twitch/callback
    Spotify: <URL pública>/oauth/spotify/callback
"""

import secrets
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode, urlparse

import requests
from flask import jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from config import settings
from services.log_service import log_service
from services.oauth_manager import TokenType
from services.token_manager import token_manager
from utils.logger import get_logger
from web.dashboard import app

logger = get_logger(__name__)

TWITCH_AUTHORIZE_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

# Permisos que pide cada cuenta. El bot modera y escribe en el chat; el
# streamer gestiona el canal y autoriza las suscripciones de EventSub.
TWITCH_SCOPES: Dict[str, List[str]] = {
    "bot": [
        "chat:read", "chat:edit",
        "moderator:manage:banned_users", "moderator:manage:chat_messages",
        "moderator:manage:chat_settings", "moderator:manage:announcements",
        "moderator:manage:shoutouts", "moderator:read:followers",
        "moderator:manage:automod", "moderator:manage:shield_mode",
        "moderator:manage:unban_requests", "moderator:read:suspicious_users",
    ],
    "broadcaster": [
        "channel:manage:broadcast", "channel:edit:commercial", "clips:edit",
        "channel:manage:vips", "channel:read:vips", "channel:read:subscriptions",
        "channel:manage:moderators", "channel:read:redemptions", "channel:read:polls",
        "channel:read:predictions", "channel:read:goals", "channel:read:hype_train",
        "bits:read", "moderator:read:followers", "moderator:manage:shoutouts",
        "moderator:manage:banned_users", "moderator:manage:chat_messages",
        "moderator:manage:automod", "moderator:manage:shield_mode",
        "moderator:manage:unban_requests", "moderator:read:suspicious_users",
    ],
}
SPOTIFY_SCOPES = [
    "user-modify-playback-state", "user-read-playback-state", "user-read-currently-playing",
]

ACCOUNT_TOKEN_TYPES = {
    "bot": TokenType.BOT,
    "broadcaster": TokenType.BROADCASTER,
    "spotify": TokenType.SPOTIFY,
}
ACCOUNT_LABELS = {"bot": "cuenta del bot", "broadcaster": "cuenta del streamer", "spotify": "Spotify"}

_STATE_TTL_SECONDS = 600
_validate_cache: Dict[str, tuple] = {}
_VALIDATE_CACHE_SECONDS = 60


# ============================================================
# Utilidades
# ============================================================

def public_base_url() -> str:
    """
    URL pública del dashboard. Orden: PUBLIC_URL, el origen de
    EVENTSUB_CALLBACK_URL (ya apunta a este mismo servidor) y la petición actual.
    """
    import os
    explicit = os.getenv("PUBLIC_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    callback = (settings.EVENTSUB_CALLBACK_URL or "").strip()
    if callback:
        parsed = urlparse(callback)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    proto = request.headers.get("X-Forwarded-Proto", request.scheme).split(",")[0].strip()
    host = request.headers.get("X-Forwarded-Host", request.host).split(",")[0].strip()
    return f"{proto}://{host}"


def redirect_uri(provider: str) -> str:
    return f"{public_base_url()}/oauth/{provider}/callback"


def _new_state(account: str) -> str:
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = {"value": state, "account": account, "created": time.time()}
    return state


def _pop_state(received: str) -> Optional[str]:
    """Devuelve la cuenta asociada si el state es válido (protección CSRF)."""
    saved = session.pop("oauth_state", None) or {}
    if not received or not saved.get("value"):
        return None
    if not secrets.compare_digest(saved["value"], received):
        return None
    if time.time() - saved.get("created", 0) > _STATE_TTL_SECONDS:
        return None
    return saved.get("account")


def validate_twitch_token(access_token: str) -> Optional[Dict]:
    """Llama a /oauth2/validate (login, user_id, scopes, expires_in) con caché de 60 s."""
    if not access_token:
        return None
    token = access_token[6:] if access_token.startswith("oauth:") else access_token
    cached = _validate_cache.get(token)
    if cached and time.time() - cached[0] < _VALIDATE_CACHE_SECONDS:
        return cached[1]
    try:
        resp = requests.get(TWITCH_VALIDATE_URL, headers={"Authorization": f"OAuth {token}"}, timeout=10)
        data = resp.json() if resp.status_code == 200 else None
    except requests.RequestException as e:
        logger.warning(f"No se pudo validar el token: {e}")
        return None
    _validate_cache[token] = (time.time(), data)
    return data


def _result_redirect(ok: bool, message: str):
    session["connections_flash"] = {"ok": ok, "message": message}
    return redirect(url_for("connections_page"))


# ============================================================
# Página
# ============================================================

@app.route("/connections")
@login_required
def connections_page():
    flash = session.pop("connections_flash", None)
    return render_template(
        "connections.html",
        active_page="connections",
        flash=flash,
        twitch_redirect=redirect_uri("twitch"),
        spotify_redirect=redirect_uri("spotify"),
        spotify_configured=bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET),
    )


# ============================================================
# Estado de los tokens
# ============================================================

def _twitch_account_status(account: str) -> Dict:
    token = settings.BOT_TOKEN if account == "bot" else settings.BROADCASTER_TOKEN
    expected_id = settings.BOT_ID if account == "bot" else settings.BROADCASTER_ID
    state = token_manager.states[ACCOUNT_TOKEN_TYPES[account]]
    info = validate_twitch_token(token)
    if not info:
        return {
            "account": account, "valid": False, "login": None, "expires_in": None,
            "has_refresh_token": bool(state.refresh_token), "missing_scopes": [],
            "wrong_account": False,
        }
    granted = set(info.get("scopes") or [])
    return {
        "account": account,
        "valid": True,
        "login": info.get("login"),
        "expires_in": info.get("expires_in"),
        "has_refresh_token": bool(state.refresh_token),
        "missing_scopes": [s for s in TWITCH_SCOPES[account] if s not in granted],
        "wrong_account": bool(expected_id) and str(info.get("user_id")) != str(expected_id),
    }


def _spotify_status() -> Dict:
    state = token_manager.states[TokenType.SPOTIFY]
    expires_in = int(state.expires_at - time.time()) if state.expires_at else None
    return {
        "account": "spotify",
        "configured": bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET),
        "valid": bool(state.valid and state.access_token and not state.is_expired()),
        "expires_in": max(0, expires_in) if expires_in is not None else None,
        "has_refresh_token": bool(state.refresh_token),
    }


@app.route("/api/tokens/status")
@login_required
def api_tokens_status():
    try:
        return jsonify({
            "bot": _twitch_account_status("bot"),
            "broadcaster": _twitch_account_status("broadcaster"),
            "spotify": _spotify_status(),
        })
    except Exception as e:
        logger.error(f"Error obteniendo estado de tokens: {e}", exc_info=True)
        return jsonify({"error": "No se pudo obtener el estado de los tokens"}), 500


@app.route("/api/tokens/refresh", methods=["POST"])
@login_required
def api_tokens_refresh():
    account = (request.json or {}).get("account", "")
    refreshers = {
        "bot": token_manager.refresh_bot_token,
        "broadcaster": token_manager.refresh_broadcaster_token,
        "spotify": token_manager.refresh_spotify_token,
    }
    if account not in refreshers:
        return jsonify({"error": "Cuenta desconocida"}), 400

    ok = refreshers[account]()
    if ok and account == "spotify":
        _reload_spotify()
    _validate_cache.clear()
    label = ACCOUNT_LABELS[account]
    if ok:
        log_service.add_log("info", f"Token de {label} renovado manualmente por {current_user.username}", "token_manager")
        return jsonify({"success": True, "message": f"Token de {label} renovado"})
    return jsonify({
        "success": False,
        "error": f"No se pudo renovar el token de {label}. Pulsa «Reconectar» para iniciar sesión de nuevo.",
    }), 400


def _reload_spotify():
    try:
        from services.spotify_service import spotify_service
        if spotify_service:
            spotify_service._authenticate()
    except Exception as e:
        logger.error(f"Error recargando Spotify: {e}")


# ============================================================
# OAuth de Twitch (cuenta del bot o del streamer)
# ============================================================

@app.route("/oauth/twitch/start")
@login_required
def oauth_twitch_start():
    account = request.args.get("account", "")
    if account not in ("bot", "broadcaster"):
        return _result_redirect(False, "Cuenta desconocida")
    if not settings.CLIENT_ID or not settings.CLIENT_SECRET:
        return _result_redirect(False, "Faltan CLIENT_ID / CLIENT_SECRET en las variables de entorno")

    params = {
        "response_type": "code",
        "client_id": settings.CLIENT_ID,
        "redirect_uri": redirect_uri("twitch"),
        "scope": " ".join(TWITCH_SCOPES[account]),
        "state": _new_state(account),
        # Obliga a mostrar la pantalla de Twitch para poder elegir la cuenta correcta
        "force_verify": "true",
    }
    return redirect(f"{TWITCH_AUTHORIZE_URL}?{urlencode(params)}")


@app.route("/oauth/twitch/callback")
@login_required
def oauth_twitch_callback():
    account = _pop_state(request.args.get("state", ""))
    if account not in ("bot", "broadcaster"):
        return _result_redirect(False, "La solicitud caducó o no es válida. Inténtalo de nuevo.")
    if request.args.get("error"):
        return _result_redirect(False, f"Twitch canceló la autorización: {request.args.get('error_description') or request.args.get('error')}")

    code = request.args.get("code", "")
    try:
        resp = requests.post(TWITCH_TOKEN_URL, data={
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri("twitch"),
        }, timeout=15)
    except requests.RequestException as e:
        return _result_redirect(False, f"No se pudo contactar con Twitch: {e}")
    if resp.status_code != 200:
        logger.error(f"Error canjeando código de Twitch: {resp.status_code} {resp.text}")
        return _result_redirect(False, "Twitch rechazó el código. Revisa que la URL de redirección esté registrada en tu app de Twitch.")

    data = resp.json()
    access, refresh = data.get("access_token", ""), data.get("refresh_token", "")
    info = validate_twitch_token(access) or {}
    expected_id = settings.BOT_ID if account == "bot" else settings.BROADCASTER_ID
    if expected_id and str(info.get("user_id")) != str(expected_id):
        return _result_redirect(
            False,
            f"Iniciaste sesión como «{info.get('login', '?')}», que no es la {ACCOUNT_LABELS[account]}. "
            "Cierra sesión en twitch.tv (o usa una ventana privada) y vuelve a intentarlo con la cuenta correcta."
        )

    token_manager.store_authorized_tokens(
        ACCOUNT_TOKEN_TYPES[account], access, refresh, int(data.get("expires_in", 14400))
    )
    _validate_cache.clear()
    log_service.add_log("info", f"{ACCOUNT_LABELS[account].capitalize()} reconectada ({info.get('login')}) por {current_user.username}", "token_manager")
    return _result_redirect(True, f"✅ {ACCOUNT_LABELS[account].capitalize()} reconectada como {info.get('login')}.")


# ============================================================
# OAuth de Spotify
# ============================================================

@app.route("/oauth/spotify/start")
@login_required
def oauth_spotify_start():
    if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
        return _result_redirect(False, "Faltan SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET en las variables de entorno")
    params = {
        "response_type": "code",
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "redirect_uri": redirect_uri("spotify"),
        "scope": " ".join(SPOTIFY_SCOPES),
        "state": _new_state("spotify"),
        "show_dialog": "true",
    }
    return redirect(f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}")


@app.route("/oauth/spotify/callback")
@login_required
def oauth_spotify_callback():
    if _pop_state(request.args.get("state", "")) != "spotify":
        return _result_redirect(False, "La solicitud caducó o no es válida. Inténtalo de nuevo.")
    if request.args.get("error"):
        return _result_redirect(False, f"Spotify canceló la autorización: {request.args.get('error')}")

    try:
        resp = requests.post(SPOTIFY_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": request.args.get("code", ""),
            "redirect_uri": redirect_uri("spotify"),
        }, auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET), timeout=15)
    except requests.RequestException as e:
        return _result_redirect(False, f"No se pudo contactar con Spotify: {e}")
    if resp.status_code != 200:
        logger.error(f"Error canjeando código de Spotify: {resp.status_code} {resp.text}")
        return _result_redirect(False, "Spotify rechazó el código. Revisa que la URL de redirección esté registrada en tu app de Spotify.")

    data = resp.json()
    token_manager.store_authorized_tokens(
        TokenType.SPOTIFY, data.get("access_token", ""), data.get("refresh_token", ""), int(data.get("expires_in", 3600))
    )
    _reload_spotify()
    log_service.add_log("info", f"Spotify reconectado por {current_user.username}", "token_manager")
    return _result_redirect(True, "✅ Spotify reconectado.")
