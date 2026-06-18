import re
from twitchio.ext import commands
from services.config_service import config_service
from bot.permissions import permission_checker

URL_PATTERNS = {
    "discord": r'^https?://(discord\.gg|discord\.com/invite)/[\w-]+$',
    "twitter": r'^https?://(twitter\.com|x\.com)/[\w]+$',
    "instagram": r'^https?://(instagram\.com)/[\w.]+$',
    "youtube": r'^https?://(youtube\.com|youtu\.be)/(c/|channel/|@|user/)?[\w-]+$',
    "tiktok": r'^https?://(tiktok\.com)/@[\w.]+$'
}


def is_valid_url(url: str, platform: str) -> bool:
    pattern = URL_PATTERNS.get(platform)
    return bool(re.match(pattern, url)) if pattern else True


def setup_social_commands(bot):
    @bot.command(name="discord")
    async def discord_cmd(ctx):
        url = config_service.get_social_link("discord")
        await ctx.send(f"💬 Discord: {url}")

    @bot.command(name="twitter")
    async def twitter_cmd(ctx):
        url = config_service.get_social_link("twitter")
        await ctx.send(f"🐦 Twitter: {url}")

    @bot.command(name="instagram")
    async def instagram_cmd(ctx):
        url = config_service.get_social_link("instagram")
        await ctx.send(f"📸 Instagram: {url}")

    @bot.command(name="youtube")
    async def youtube_cmd(ctx):
        url = config_service.get_social_link("youtube")
        await ctx.send(f"🎬 YouTube: {url}")

    @bot.command(name="tiktok")
    async def tiktok_cmd(ctx):
        url = config_service.get_social_link("tiktok")
        await ctx.send(f"🎵 TikTok: {url}")

    @bot.command(name="setdiscord")
    async def set_discord(ctx):
        if not permission_checker.is_staff(ctx.message):
            return
        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !setdiscord <url>")
            return
        url = parts[1]
        if not is_valid_url(url, "discord"):
            await ctx.send("❌ URL inválida")
            return
        config_service.set_social_link("discord", url)
        await ctx.send("✅ Enlace de Discord actualizado.")

    @bot.command(name="settwitter")
    async def set_twitter(ctx):
        if not permission_checker.is_staff(ctx.message):
            return
        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !settwitter <url>")
            return
        url = parts[1]
        if not is_valid_url(url, "twitter"):
            await ctx.send("❌ URL inválida")
            return
        config_service.set_social_link("twitter", url)
        await ctx.send("✅ Enlace de Twitter actualizado.")

    @bot.command(name="setinstagram")
    async def set_instagram(ctx):
        if not permission_checker.is_staff(ctx.message):
            return
        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !setinstagram <url>")
            return
        url = parts[1]
        if not is_valid_url(url, "instagram"):
            await ctx.send("❌ URL inválida")
            return
        config_service.set_social_link("instagram", url)
        await ctx.send("✅ Enlace de Instagram actualizado.")

    @bot.command(name="setyoutube")
    async def set_youtube(ctx):
        if not permission_checker.is_staff(ctx.message):
            return
        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !setyoutube <url>")
            return
        url = parts[1]
        if not is_valid_url(url, "youtube"):
            await ctx.send("❌ URL inválida")
            return
        config_service.set_social_link("youtube", url)
        await ctx.send("✅ Enlace de YouTube actualizado.")

    @bot.command(name="settiktok")
    async def set_tiktok(ctx):
        if not permission_checker.is_staff(ctx.message):
            return
        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !settiktok <url>")
            return
        url = parts[1]
        if not is_valid_url(url, "tiktok"):
            await ctx.send("❌ URL inválida")
            return
        config_service.set_social_link("tiktok", url)
        await ctx.send("✅ Enlace de TikTok actualizado.")