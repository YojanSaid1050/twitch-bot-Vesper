"""
Comandos extra estilo Nightbot:

    !followage [usuario]                  Cuánto tiempo lleva siguiendo el canal
    !quote [número]                       Muestra una cita (aleatoria o la indicada)
    !quote add <texto>                    (staff) Guarda una cita
    !quote del <número>                   (staff) Borra una cita
    !timer add <nombre> <minutos> <msg>   (staff) Mensaje automático periódico
    !timer remove|on|off <nombre>         (staff)
    !timer list                           (staff)
    !permit <usuario> [segundos]          (staff) Permite enviar un enlace
"""

import random
from datetime import datetime, timezone

from twitchio.ext import commands

from bot.permissions import permission_checker
from services.config_service import config_service
from utils.cooldowns import cooldowns
from services.link_manager import link_manager
from services.log_service import log_service
from services.moderation_actions import ModerationActions
from services.timers_service import timers_service
from exceptions import TwitchAPIError
from utils.formatters import format_duration_long


def setup_extra_commands(bot):
    mod_actions = ModerationActions()

    # ------------------------------------------------------------------
    # !followage
    # ------------------------------------------------------------------
    @bot.command(name="followage", aliases=["seguimiento", "fa"])
    async def followage_command(ctx: commands.Context):
        if not permission_checker.is_staff(ctx.message) and not cooldowns.try_use(
            "followage", global_seconds=3, user_id=str(ctx.author.id), user_seconds=30
        ):
            return

        parts = ctx.message.content.split()
        if len(parts) > 1:
            user = await mod_actions.get_user(parts[1])
            if not user:
                await ctx.send(f"❌ No encuentro a {parts[1].lstrip('@')} en los anales")
                return
            user_id, name = user["id"], user.get("display_name") or user["login"]
        else:
            user_id, name = str(ctx.author.id), ctx.author.display_name or ctx.author.name

        if name.lower() == bot.channel_name.lower():
            await ctx.send(f"🕯️ {name} es el invocador del relicario, no puede seguirse a sí mismo.")
            return

        try:
            followed_at = await mod_actions.get_follow_date(user_id)
        except TwitchAPIError as e:
            await ctx.send("❌ No pude consultar los seguidores (¿falta el permiso moderator:read:followers?)")
            log_service.add_log('error', f'Error en !followage: {e}', 'twitch_api')
            return

        if not followed_at:
            await ctx.send(f"🌑 {name} aún no sigue al canal.")
            return

        since = datetime.fromisoformat(followed_at.replace("Z", "+00:00"))
        elapsed = datetime.now(timezone.utc) - since
        await ctx.send(
            f"👁️ {name} sigue al canal desde hace {format_duration_long(elapsed.total_seconds())} "
            f"(desde el {since.strftime('%d/%m/%Y')})."
        )

    # ------------------------------------------------------------------
    # !quote
    # ------------------------------------------------------------------
    @bot.command(name="quote", aliases=["cita"])
    async def quote_command(ctx: commands.Context):
        parts = ctx.message.content.split(" ", 2)
        sub = parts[1].lower() if len(parts) > 1 else ""

        if sub in ("add", "añadir"):
            if not permission_checker.is_staff(ctx.message):
                return
            if len(parts) < 3 or not parts[2].strip():
                await ctx.send("🕯️ Uso: !quote add <texto de la cita>")
                return
            game = ""
            try:
                from services.stats_service import stats_service
                info = await stats_service.get_channel_info()
                game = (info or {}).get("game_name", "")
            except Exception:
                pass
            quote_id = config_service.add_quote(parts[2].strip(), ctx.author.name, game)
            await ctx.send(f"📜 Cita #{quote_id} grabada en los anales.")
            return

        if sub in ("del", "delete", "remove", "borrar"):
            if not permission_checker.is_staff(ctx.message):
                return
            if len(parts) < 3 or not parts[2].strip().lstrip("#").isdigit():
                await ctx.send("🕯️ Uso: !quote del <número>")
                return
            quote_id = int(parts[2].strip().lstrip("#"))
            if config_service.remove_quote(quote_id):
                await ctx.send(f"🗑️ Cita #{quote_id} borrada.")
            else:
                await ctx.send(f"❌ No existe la cita #{quote_id}.")
            return

        if not permission_checker.is_staff(ctx.message) and not cooldowns.try_use("quote", global_seconds=10):
            return

        quotes = config_service.get_quotes()
        if not quotes:
            await ctx.send("📜 Aún no hay citas. El staff puede añadirlas con !quote add <texto>")
            return

        if sub.lstrip("#").isdigit():
            wanted = int(sub.lstrip("#"))
            quote = next((q for q in quotes if q.get("id") == wanted), None)
            if not quote:
                await ctx.send(f"❌ No existe la cita #{wanted}.")
                return
        else:
            quote = random.choice(quotes)

        game = f" [{quote['game']}]" if quote.get("game") else ""
        await ctx.send(f"📜 #{quote['id']}: \"{quote['text']}\"{game} — {quote.get('date', '')}")

    # ------------------------------------------------------------------
    # !timer
    # ------------------------------------------------------------------
    @bot.command(name="timer", aliases=["timers"])
    async def timer_command(ctx: commands.Context):
        if not permission_checker.is_staff(ctx.message):
            return

        parts = ctx.message.content.split(" ", 4)
        sub = parts[1].lower() if len(parts) > 1 else "list"

        if sub == "add":
            if len(parts) < 5 or not parts[3].isdigit():
                await ctx.send("🕯️ Uso: !timer add <nombre> <minutos> <mensaje>  (ej: !timer add discord 20 Únete a nuestro Discord!)")
                return
            name, minutes, message = parts[2].lower(), int(parts[3]), parts[4].strip()
            if minutes < 5:
                await ctx.send("❌ El intervalo mínimo es de 5 minutos.")
                return
            config_service.set_timer(name, message, minutes)
            timers_service.reset_timer(name)
            await ctx.send(f"⏲️ Timer '{name}' creado: cada {minutes} min (si hay actividad en el chat).")
            log_service.add_log('info', f'Timer {name} creado por {ctx.author.name}', 'bot_commands')
            return

        if sub in ("remove", "delete", "del"):
            if len(parts) < 3:
                await ctx.send("🕯️ Uso: !timer remove <nombre>")
                return
            name = parts[2].lower()
            if config_service.remove_timer(name):
                await ctx.send(f"🗑️ Timer '{name}' eliminado.")
            else:
                await ctx.send(f"❌ No existe el timer '{name}'.")
            return

        if sub in ("on", "off"):
            if len(parts) < 3:
                await ctx.send(f"🕯️ Uso: !timer {sub} <nombre>")
                return
            name = parts[2].lower()
            if config_service.toggle_timer(name, sub == "on"):
                if sub == "on":
                    timers_service.reset_timer(name)
                await ctx.send(f"⏲️ Timer '{name}' {'activado' if sub == 'on' else 'pausado'}.")
            else:
                await ctx.send(f"❌ No existe el timer '{name}'.")
            return

        timers = config_service.get_timers()
        if not timers:
            await ctx.send("⏲️ No hay timers. Crea uno con !timer add <nombre> <minutos> <mensaje>")
            return
        summary = ", ".join(
            f"{name} ({t.get('interval')}m{'' if t.get('enabled', True) else ', pausado'})"
            for name, t in sorted(timers.items())
        )
        await ctx.send(f"⏲️ Timers: {summary}"[:500])

    # ------------------------------------------------------------------
    # !permit
    # ------------------------------------------------------------------
    @bot.command(name="permit", aliases=["permitir"])
    async def permit_command(ctx: commands.Context):
        if not permission_checker.is_staff(ctx.message):
            return
        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !permit @usuario [segundos]")
            return
        username = parts[1].lstrip("@")
        seconds = 60
        if len(parts) > 2 and parts[2].isdigit():
            seconds = max(10, min(int(parts[2]), 600))
        link_manager.grant_permit(username, seconds)
        await ctx.send(f"🔗 {username} puede enviar un enlace durante los próximos {seconds} segundos.")
        log_service.add_log('info', f'Permit concedido a {username} ({seconds}s) por {ctx.author.name}', 'moderation')
