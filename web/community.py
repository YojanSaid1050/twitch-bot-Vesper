# web/community.py
"""
Páginas y API del dashboard para timers (mensajes periódicos) y citas.
Usan los mismos datos que los comandos !timer y !quote del chat.
"""

import re

from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from services.config_service import config_service
from services.log_service import log_service
from utils.logger import get_logger
from web.dashboard import app

logger = get_logger(__name__)

TIMER_NAME_RE = re.compile(r"^[a-z0-9_\-áéíóúñü]{1,25}$")
MIN_TIMER_INTERVAL = 5


def _reset_timer(name: str):
    try:
        from services.timers_service import timers_service
        timers_service.reset_timer(name)
    except Exception as e:
        logger.debug(f"No se pudo reiniciar el timer {name}: {e}")


# ============================================================
# TIMERS
# ============================================================

@app.route("/timers")
@login_required
def timers_page():
    return render_template("timers.html", active_page="timers")


@app.route("/api/timers")
@login_required
def api_get_timers():
    timers = config_service.get_timers()
    return jsonify([
        {
            "name": name,
            "message": t.get("message", ""),
            "interval": t.get("interval", 15),
            "min_lines": t.get("min_lines", 5),
            "enabled": t.get("enabled", True),
        }
        for name, t in sorted(timers.items())
    ])


@app.route("/api/timers", methods=["POST"])
@login_required
def api_save_timer():
    data = request.json or {}
    name = str(data.get("name", "")).strip().lower()
    message = str(data.get("message", "")).strip()
    try:
        interval = int(data.get("interval", 15))
        min_lines = int(data.get("min_lines", 5))
    except (TypeError, ValueError):
        return jsonify({"error": "El intervalo y las líneas mínimas deben ser números"}), 400

    if not TIMER_NAME_RE.match(name):
        return jsonify({"error": "Nombre inválido (letras, números, - o _; máx. 25)"}), 400
    if not message:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400
    if len(message) > 500:
        return jsonify({"error": "El mensaje no puede pasar de 500 caracteres"}), 400
    if interval < MIN_TIMER_INTERVAL or interval > 1440:
        return jsonify({"error": f"El intervalo debe estar entre {MIN_TIMER_INTERVAL} y 1440 minutos"}), 400
    if min_lines < 0 or min_lines > 500:
        return jsonify({"error": "Las líneas mínimas deben estar entre 0 y 500"}), 400

    existed = name in config_service.get_timers()
    previous_enabled = config_service.get_timers().get(name, {}).get("enabled", True)
    if not config_service.set_timer(name, message, interval, min_lines):
        return jsonify({"error": "No se pudo guardar el timer"}), 500
    if existed and not previous_enabled:
        config_service.toggle_timer(name, False)
    _reset_timer(name)
    log_service.add_log("info", f"Timer {name} {'editado' if existed else 'creado'} por {current_user.username}", "dashboard")
    return jsonify({"success": True, "message": f"Timer «{name}» {'actualizado' if existed else 'creado'}"})


@app.route("/api/timers/<name>/toggle", methods=["POST"])
@login_required
def api_toggle_timer(name):
    enabled = bool((request.json or {}).get("enabled", True))
    if not config_service.toggle_timer(name, enabled):
        return jsonify({"error": "Timer no encontrado"}), 404
    if enabled:
        _reset_timer(name)
    log_service.add_log("info", f"Timer {name} {'activado' if enabled else 'pausado'} por {current_user.username}", "dashboard")
    return jsonify({"success": True, "message": f"Timer «{name}» {'activado' if enabled else 'pausado'}"})


@app.route("/api/timers/<name>", methods=["DELETE"])
@login_required
def api_delete_timer(name):
    if not config_service.remove_timer(name):
        return jsonify({"error": "Timer no encontrado"}), 404
    log_service.add_log("info", f"Timer {name} eliminado por {current_user.username}", "dashboard")
    return jsonify({"success": True, "message": f"Timer «{name}» eliminado"})


# ============================================================
# CITAS
# ============================================================

@app.route("/quotes")
@login_required
def quotes_page():
    return render_template("quotes.html", active_page="quotes")


@app.route("/api/quotes")
@login_required
def api_get_quotes():
    quotes = sorted(config_service.get_quotes(), key=lambda q: q.get("id", 0), reverse=True)
    return jsonify(quotes)


@app.route("/api/quotes", methods=["POST"])
@login_required
def api_add_quote():
    data = request.json or {}
    text = str(data.get("text", "")).strip()
    game = str(data.get("game", "")).strip()[:100]
    if not text:
        return jsonify({"error": "La cita no puede estar vacía"}), 400
    if len(text) > 400:
        return jsonify({"error": "La cita no puede pasar de 400 caracteres"}), 400
    quote_id = config_service.add_quote(text, current_user.username + " (panel)", game)
    log_service.add_log("info", f"Cita #{quote_id} añadida por {current_user.username}", "dashboard")
    return jsonify({"success": True, "id": quote_id, "message": f"Cita #{quote_id} guardada"})


@app.route("/api/quotes/<int:quote_id>", methods=["PUT"])
@login_required
def api_update_quote(quote_id):
    data = request.json or {}
    text = str(data.get("text", "")).strip()
    if not text or len(text) > 400:
        return jsonify({"error": "La cita debe tener entre 1 y 400 caracteres"}), 400
    game = data.get("game")
    if not config_service.update_quote(quote_id, text=text, game=None if game is None else str(game).strip()):
        return jsonify({"error": "Cita no encontrada"}), 404
    return jsonify({"success": True, "message": f"Cita #{quote_id} actualizada"})


@app.route("/api/quotes/<int:quote_id>", methods=["DELETE"])
@login_required
def api_delete_quote(quote_id):
    if not config_service.remove_quote(quote_id):
        return jsonify({"error": "Cita no encontrada"}), 404
    log_service.add_log("info", f"Cita #{quote_id} eliminada por {current_user.username}", "dashboard")
    return jsonify({"success": True, "message": f"Cita #{quote_id} eliminada"})
