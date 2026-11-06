"""
Variables para comandos personalizados (estilo Nightbot).

Variables soportadas en la respuesta de un comando:
    {user}            Nombre de quien usa el comando
    {touser}          Primer argumento sin @ (o {user} si no hay argumentos)
    {args}            Todo el texto después del comando
    {1} ... {9}       Argumento N (vacío si no existe)
    {channel}         Nombre del canal
    {count}           Número de veces que se ha usado el comando
    {random:1-100}    Número aleatorio entre 1 y 100 (ambos incluidos)
    {pick:a|b|c}      Elige una opción al azar
    {random_emote}    Emote aleatorio de la temática del bot
    {uptime}          Tiempo en directo (lo resuelve el bot)
    {game}            Categoría actual (lo resuelve el bot)
    {title}           Título actual (lo resuelve el bot)

Las variables dinámicas ({uptime}, {game}, {title}) se pasan ya resueltas en
`extra`; usa `needed_dynamic_vars()` para saber si hace falta pedirlas a Twitch.
"""

import random
import re
from typing import Dict, Iterable, List, Optional, Set

EMOTES = ['🕯️', '⚔️', '🔥', '📜', '👁️', '🎭', '🌙']
DYNAMIC_VARS = ("uptime", "game", "title")

_TOKEN_RE = re.compile(r"\{([a-zA-Z_0-9]+)(?::([^{}]*))?\}")
MAX_CHAT_LENGTH = 500


def needed_dynamic_vars(template: str) -> Set[str]:
    found = set()
    for match in _TOKEN_RE.finditer(template or ""):
        name = match.group(1).lower()
        if name in DYNAMIC_VARS:
            found.add(name)
    return found


def uses_counter(template: str) -> bool:
    return any(m.group(1).lower() == "count" for m in _TOKEN_RE.finditer(template or ""))


def render(
    template: str,
    user: str,
    args: Optional[Iterable[str]] = None,
    channel: str = "",
    count: int = 0,
    extra: Optional[Dict[str, str]] = None,
    rng: Optional[random.Random] = None,
) -> str:
    rng = rng or random
    arg_list: List[str] = [a for a in (args or []) if a]
    extra = {k.lower(): v for k, v in (extra or {}).items()}

    def replace(match: "re.Match") -> str:
        name = match.group(1).lower()
        param = match.group(2)

        if name == "user":
            return user
        if name == "touser":
            return arg_list[0].lstrip("@") if arg_list else user
        if name == "args":
            return " ".join(arg_list)
        if name.isdigit():
            idx = int(name) - 1
            return arg_list[idx] if 0 <= idx < len(arg_list) else ""
        if name == "channel":
            return channel
        if name == "count":
            return str(count)
        if name == "random_emote":
            return rng.choice(EMOTES)
        if name == "random" and param:
            m = re.fullmatch(r"\s*(-?\d+)\s*-\s*(-?\d+)\s*", param)
            if m:
                low, high = int(m.group(1)), int(m.group(2))
                if low > high:
                    low, high = high, low
                return str(rng.randint(low, high))
            return match.group(0)
        if name == "pick" and param:
            options = [o.strip() for o in param.split("|") if o.strip()]
            return rng.choice(options) if options else ""
        if name in extra:
            return str(extra[name])
        # Variable desconocida: se deja tal cual para que el streamer la vea
        return match.group(0)

    result = _TOKEN_RE.sub(replace, template or "")
    return sanitize_output(result, allow_me=(template or "").lstrip().lower().startswith("/me "))


def sanitize_output(text: str, allow_me: bool = False) -> str:
    """
    Evita que una respuesta empiece por '/' o '.', que Twitch interpretaría como
    un comando de chat (p. ej. si alguien pasa '/ban' a través de {args}).
    Solo se permite '/me' cuando la plantilla original empieza así.
    """
    text = (text or "").strip()
    if allow_me and text.lower().startswith("/me "):
        body = text[4:].lstrip("/. ")
        return ("/me " + body)[:MAX_CHAT_LENGTH]
    return text.lstrip("/. ")[:MAX_CHAT_LENGTH]
