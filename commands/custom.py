from twitchio.ext import commands as twitch_commands
from services.config_service import config_service
from bot.permissions import permission_checker
import random

BASE_COMMANDS = ['hola', 'ping', 'comandos', 'title', 'game', 'slow', 'followers',
                 'emote', 'subscribers', 'vip', 'timeout', 'ban', '8ball', 'dado',
                 'moneda', 'elige', 'lurk', 'uptime', 'viewers', 'shoutout',
                 'announce', 'warn', 'sr', 'current', 'skip', 'pause', 'resume',
                 'queue', 'remove', 'clearqueue', 'volumen', 'clip']

EMOTES = ['🕯️', '⚔️', '🔥', '📜', '👁️', '🎭', '🌙']


_command_cache = {}


def refresh_cache():
    global _command_cache
    _command_cache = config_service.get_custom_commands()
    return _command_cache


def setup_custom_commands(bot):
    refresh_cache()

    @bot.command(name="comando", aliases=["custom", "cmd"])
    async def custom_command_root(ctx: twitch_commands.Context):
        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Ecos secundarios disponibles: add, remove, list")
            return

        subcommand = parts[1].lower()
        if subcommand == "add":
            await _add_command(ctx, parts)
        elif subcommand in ["remove", "delete"]:
            await _remove_command(ctx, parts)
        elif subcommand == "list":
            await _list_commands(ctx)
        else:
            await ctx.send("🕯️ Ecos secundarios: add, remove, list")

    async def _add_command(ctx, parts):
        if not permission_checker.is_staff(ctx.message):
            return

        if len(parts) < 4:
            await ctx.send("🕯️ Invocación: !comando add <nombre> <respuesta>")
            return

        name = parts[2].lower()
        response = " ".join(parts[3:])

        if name in BASE_COMMANDS:
            await ctx.send(f"❌ '{name}' es un eco base del relicario")
            return

        success = config_service.add_custom_command(name, response)
        if success:
            refresh_cache()
            await ctx.send(f"✅ El eco !{name} ha sido grabado en el vacío.")
        else:
            await ctx.send("❌ El hechizo falló... no se pudo crear el eco.")

    async def _remove_command(ctx, parts):
        if not permission_checker.is_staff(ctx.message):
            return

        if len(parts) < 3:
            await ctx.send("🕯️ Invocación: !comando remove <nombre>")
            return

        name = parts[2].lower()
        success = config_service.remove_custom_command(name)

        if success:
            refresh_cache()
            await ctx.send(f"✅ El eco !{name} ha sido borrado del vacío.")
        else:
            await ctx.send(f"❌ El eco !{name} no existe en los anales.")

    async def _list_commands(ctx):
        global _command_cache
        if not _command_cache:
            refresh_cache()

        if not _command_cache:
            await ctx.send("📜 No hay ecos personalizados grabados.")
            return

        names = [f"!{name}" for name in _command_cache.keys()]
        if len(names) > 10:
            await ctx.send(f"📜 Ecos grabados ({len(names)}):")
            for i in range(0, len(names), 10):
                await ctx.send("  " + ", ".join(names[i:i+10]))
        else:
            await ctx.send(f"📜 Ecos grabados: {', '.join(names)}")

    original_handle = bot.handle_commands

    async def custom_handle_commands(message):
        ctx = twitch_commands.Context(message=message, bot=bot)
        prefix = getattr(bot, '_prefix', '!')

        if not message.content.startswith(prefix):
            await original_handle(message)
            return

        try:
            command_name = message.content[len(prefix):].split()[0].lower()
        except IndexError:
            await original_handle(message)
            return

        global _command_cache
        custom_cmd = _command_cache.get(command_name)

        if custom_cmd:
            response = custom_cmd.get('response', '')
            response = response.replace('{user}', ctx.author.name)
            response = response.replace('{channel}', ctx.channel.name)
            response = response.replace('{random_emote}', random.choice(EMOTES))
            await ctx.send(response)
            return

        await original_handle(message)

    bot.handle_commands = custom_handle_commands