"""
Comandos personalizados (estilo Nightbot)

Gestión (solo staff):
    !comando add <nombre> <respuesta>
    !comando edit <nombre> <nueva respuesta>
    !comando remove <nombre>
    !comando cooldown <nombre> <segundos> [segundos_por_usuario]
    !comando level <nombre> <everyone|sub|vip|mod|owner>
    !comando info <nombre>
    !comando list

Variables disponibles en la respuesta: ver utils/command_vars.py
({user}, {touser}, {args}, {1}..{9}, {count}, {random:1-100}, {pick:a|b|c},
 {uptime}, {game}, {title}, {channel}, {random_emote})
"""

import re

from twitchio.ext import commands as twitch_commands

from services.config_service import config_service
from utils.cooldowns import cooldowns
from services.log_service import log_service
from bot.permissions import permission_checker
from utils import command_vars
from utils.logger import get_logger

logger = get_logger(__name__)

# Se mantiene por compatibilidad con el dashboard; la comprobación real usa
# bot.get_command(), que conoce también los alias.
BASE_COMMANDS = ['hola', 'ping', 'comandos', 'title', 'game', 'slow', 'followers',
                 'emote', 'subscribers', 'vip', 'timeout', 'ban', '8ball', 'dado',
                 'moneda', 'elige', 'lurk', 'uptime', 'viewers', 'shoutout',
                 'announce', 'warn', 'sr', 'current', 'skip', 'pause', 'resume',
                 'queue', 'remove', 'clearqueue', 'volumen', 'clip', 'followage',
                 'quote', 'timer', 'permit']

LEVEL_ORDER = {'everyone': 0, 'sub': 1, 'vip': 2, 'mod': 3, 'owner': 4}
LEVEL_NAMES = {'everyone': 'todos', 'sub': 'suscriptores', 'vip': 'VIP', 'mod': 'moderadores', 'owner': 'el streamer'}
NAME_RE = re.compile(r'^[a-z0-9_áéíóúñü]{1,25}$')

_command_cache = {}


def refresh_cache():
    global _command_cache
    _command_cache = dict(config_service.get_custom_commands())
    return _command_cache


def get_cached_commands():
    return _command_cache


def user_level(message) -> int:
    author = message.author
    if permission_checker.get_user_level(message) >= 4:
        return LEVEL_ORDER['owner']
    if getattr(author, 'is_mod', False):
        return LEVEL_ORDER['mod']
    if getattr(author, 'is_vip', False):
        return LEVEL_ORDER['vip']
    if getattr(author, 'is_subscriber', False):
        return LEVEL_ORDER['sub']
    return LEVEL_ORDER['everyone']


def setup_custom_commands(bot):
    refresh_cache()

    def _is_reserved(name: str) -> bool:
        return name in BASE_COMMANDS or bot.get_command(name) is not None

    @bot.command(name="comando", aliases=["custom", "cmd"])
    async def custom_command_root(ctx: twitch_commands.Context):
        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !comando add|edit|remove|cooldown|level|info|list")
            return

        subcommand = parts[1].lower()
        if subcommand == "list":
            await _list_commands(ctx)
            return

        if not permission_checker.is_staff(ctx.message):
            return

        handlers = {
            "add": _add_command,
            "edit": _edit_command,
            "remove": _remove_command,
            "delete": _remove_command,
            "del": _remove_command,
            "cooldown": _set_cooldown,
            "cd": _set_cooldown,
            "level": _set_level,
            "nivel": _set_level,
            "info": _info_command,
        }
        handler = handlers.get(subcommand)
        if handler:
            await handler(ctx, parts)
        else:
            await ctx.send("🕯️ Subcomandos: add, edit, remove, cooldown, level, info, list")

    def _clean_name(raw: str) -> str:
        return raw.lower().lstrip('!')

    async def _add_command(ctx, parts):
        if len(parts) < 4:
            await ctx.send("🕯️ Uso: !comando add <nombre> <respuesta>")
            return

        name = _clean_name(parts[2])
        response = " ".join(parts[3:])

        if not NAME_RE.match(name):
            await ctx.send("❌ Nombre inválido (letras, números o _; máx. 25 caracteres)")
            return
        if _is_reserved(name):
            await ctx.send(f"❌ '{name}' es un eco base del relicario")
            return
        if name in _command_cache:
            await ctx.send(f"⚠️ !{name} ya existe. Usa !comando edit {name} <respuesta>")
            return

        if config_service.add_custom_command(name, response):
            refresh_cache()
            await ctx.send(f"✅ El eco !{name} ha sido grabado en el vacío.")
            log_service.add_log('info', f'Comando !{name} creado por {ctx.author.name}', 'bot_commands')
        else:
            await ctx.send("❌ El hechizo falló... no se pudo crear el eco.")

    async def _edit_command(ctx, parts):
        if len(parts) < 4:
            await ctx.send("🕯️ Uso: !comando edit <nombre> <nueva respuesta>")
            return
        name = _clean_name(parts[2])
        if config_service.update_custom_command(name, response=" ".join(parts[3:])):
            refresh_cache()
            await ctx.send(f"✏️ El eco !{name} ha sido reescrito.")
            log_service.add_log('info', f'Comando !{name} editado por {ctx.author.name}', 'bot_commands')
        else:
            await ctx.send(f"❌ El eco !{name} no existe en los anales.")

    async def _remove_command(ctx, parts):
        if len(parts) < 3:
            await ctx.send("🕯️ Uso: !comando remove <nombre>")
            return

        name = _clean_name(parts[2])
        if config_service.remove_custom_command(name):
            refresh_cache()
            cooldowns.reset(f"custom:{name}")
            await ctx.send(f"✅ El eco !{name} ha sido borrado del vacío.")
        else:
            await ctx.send(f"❌ El eco !{name} no existe en los anales.")

    async def _set_cooldown(ctx, parts):
        if len(parts) < 4 or not parts[3].isdigit() or (len(parts) > 4 and not parts[4].isdigit()):
            await ctx.send("🕯️ Uso: !comando cooldown <nombre> <segundos> [segundos_por_usuario]")
            return
        name = _clean_name(parts[2])
        fields = {"cooldown": min(int(parts[3]), 3600)}
        if len(parts) > 4:
            fields["user_cooldown"] = min(int(parts[4]), 86400)
        if config_service.update_custom_command(name, **fields):
            refresh_cache()
            extra = f", {fields['user_cooldown']}s por usuario" if "user_cooldown" in fields else ""
            await ctx.send(f"⏳ !{name}: cooldown de {fields['cooldown']}s{extra}.")
        else:
            await ctx.send(f"❌ El eco !{name} no existe en los anales.")

    async def _set_level(ctx, parts):
        if len(parts) < 4 or parts[3].lower() not in LEVEL_ORDER:
            await ctx.send("🕯️ Uso: !comando level <nombre> <everyone|sub|vip|mod|owner>")
            return
        name = _clean_name(parts[2])
        level = parts[3].lower()
        if config_service.update_custom_command(name, level=level):
            refresh_cache()
            await ctx.send(f"🔐 !{name} ahora solo lo pueden usar: {LEVEL_NAMES[level]}.")
        else:
            await ctx.send(f"❌ El eco !{name} no existe en los anales.")

    async def _info_command(ctx, parts):
        if len(parts) < 3:
            await ctx.send("🕯️ Uso: !comando info <nombre>")
            return
        name = _clean_name(parts[2])
        cmd = _command_cache.get(name)
        if not cmd:
            await ctx.send(f"❌ El eco !{name} no existe en los anales.")
            return
        level = cmd.get('level', 'everyone')
        await ctx.send(
            f"📜 !{name} | nivel: {LEVEL_NAMES.get(level, level)} | cooldown: {cmd.get('cooldown', 0)}s"
            f" (usuario {cmd.get('user_cooldown', 0)}s) | usos: {cmd.get('count', 0)} | "
            f"respuesta: {cmd.get('response', '')[:200]}"
        )

    async def _list_commands(ctx):
        if not _command_cache:
            refresh_cache()

        if not _command_cache:
            await ctx.send("📜 No hay ecos personalizados grabados.")
            return

        names = sorted(f"!{name}" for name in _command_cache.keys())
        # Un único mensaje (máx. 500 caracteres) para no inundar el chat
        header = f"📜 Ecos grabados ({len(names)}): "
        shown = []
        for n in names:
            if len(header) + len(", ".join(shown + [n])) > 470:
                break
            shown.append(n)
        text = header + ", ".join(shown)
        if len(shown) < len(names):
            text += f" … y {len(names) - len(shown)} más"
        await ctx.send(text)

    async def _resolve_dynamic(template: str) -> dict:
        needed = command_vars.needed_dynamic_vars(template)
        if not needed:
            return {}
        from services.stats_service import stats_service
        values = {}
        try:
            if "uptime" in needed:
                text = await stats_service.format_uptime()
                values["uptime"] = text.replace("⏱️ Stream activo por: ", "").replace("⏱️ ", "")
            if needed & {"game", "title"}:
                info = await stats_service.get_channel_info() or {}
                values["game"] = info.get("game_name") or "sin categoría"
                values["title"] = info.get("title") or ""
        except Exception as e:
            logger.error(f"Error resolviendo variables dinámicas: {e}")
        return values

    original_handle = bot.handle_commands

    async def custom_handle_commands(message):
        prefix = getattr(bot, '_prefix', '!')
        if isinstance(prefix, (list, tuple)):
            prefix = prefix[0]
        content = message.content or ""

        if not content.startswith(prefix):
            await original_handle(message)
            return

        tokens = content[len(prefix):].split()
        if not tokens:
            await original_handle(message)
            return

        command_name = tokens[0].lower()
        custom_cmd = _command_cache.get(command_name)
        if not custom_cmd:
            await original_handle(message)
            return

        # Permisos
        level = custom_cmd.get('level', 'everyone')
        if user_level(message) < LEVEL_ORDER.get(level, 0):
            return

        # Cooldowns (el staff se los salta, igual que en Nightbot)
        is_staff = permission_checker.is_staff(message)
        key = f"custom:{command_name}"
        user_id = str(message.author.id)
        if is_staff:
            cooldowns.trigger(key, user_id)
        elif not cooldowns.try_use(
            key,
            global_seconds=custom_cmd.get('cooldown', 0),
            user_id=user_id,
            user_seconds=custom_cmd.get('user_cooldown', 0),
        ):
            return

        template = custom_cmd.get('response', '')
        count = custom_cmd.get('count', 0)
        if command_vars.uses_counter(template):
            count = config_service.increment_custom_command_count(command_name)
            custom_cmd['count'] = count

        response = command_vars.render(
            template,
            user=message.author.display_name or message.author.name,
            args=tokens[1:],
            channel=message.channel.name,
            count=count,
            extra=await _resolve_dynamic(template),
        )
        if response:
            await message.channel.send(response)

    bot.handle_commands = custom_handle_commands
