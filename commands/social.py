"""
Comandos para enlaces de redes sociales
"""

import re
from twitchio.ext import commands

from database import db
from bot.permissions import permission_checker


def is_valid_url(url: str, platform: str) -> bool:
    """Validar URL según la plataforma"""
    patterns = {
        "discord": r'^https?://(discord\.gg|discord\.com/invite)/[\w-]+$',
        "twitter": r'^https?://(twitter\.com|x\.com)/[\w]+$',
        "instagram": r'^https?://(instagram\.com)/[\w.]+$',
        "youtube": r'^https?://(youtube\.com|youtu\.be)/(c/|channel/|@|user/)?[\w-]+$',
        "tiktok": r'^https?://(tiktok\.com)/@[\w.]+$'
    }
    
    pattern = patterns.get(platform)
    if pattern:
        return re.match(pattern, url) is not None
    return True


def setup_social_commands(bot):
    """Registrar comandos de redes sociales"""
    
    @bot.command(name="discord")
    async def discord_command(ctx: commands.Context):
        """Mostrar enlace de Discord"""
        url = db.get_social_link("discord")
        await ctx.send(f"💬 Únete al Discord: {url}")
    
    @bot.command(name="twitter")
    async def twitter_command(ctx: commands.Context):
        """Mostrar Twitter"""
        url = db.get_social_link("twitter")
        await ctx.send(f"🐦 Sígueme en Twitter: {url}")
    
    @bot.command(name="instagram")
    async def instagram_command(ctx: commands.Context):
        """Mostrar Instagram"""
        url = db.get_social_link("instagram")
        await ctx.send(f"📸 Instagram: {url}")
    
    @bot.command(name="youtube")
    async def youtube_command(ctx: commands.Context):
        """Mostrar YouTube"""
        url = db.get_social_link("youtube")
        await ctx.send(f"🎬 YouTube: {url}")
    
    @bot.command(name="tiktok")
    async def tiktok_command(ctx: commands.Context):
        """Mostrar TikTok"""
        url = db.get_social_link("tiktok")
        await ctx.send(f"🎵 TikTok: {url}")
    
    # ========== COMANDOS PARA STAFF CON VALIDACIÓN ==========
    
    @bot.command(name="setdiscord")
    async def set_discord_command(ctx: commands.Context):
        """Actualizar enlace de Discord (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !setdiscord https://discord.gg/invite")
            await ctx.send("Formatos válidos: discord.gg/xxx o discord.com/invite/xxx")
            return
        
        url = parts[1]
        
        if not is_valid_url(url, "discord"):
            await ctx.send("❌ URL de Discord inválida. Debe ser: discord.gg/invite o discord.com/invite/xxx")
            return
        
        db.set_social_link("discord", url)
        await ctx.send(f"✅ Enlace de Discord actualizado")
    
    @bot.command(name="settwitter")
    async def set_twitter_command(ctx: commands.Context):
        """Actualizar Twitter (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !settwitter https://twitter.com/usuario")
            return
        
        url = parts[1]
        
        if not is_valid_url(url, "twitter"):
            await ctx.send("❌ URL de Twitter inválida. Debe ser: twitter.com/usuario o x.com/usuario")
            return
        
        db.set_social_link("twitter", url)
        await ctx.send(f"✅ Twitter actualizado")
    
    @bot.command(name="setinstagram")
    async def set_instagram_command(ctx: commands.Context):
        """Actualizar Instagram (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !setinstagram https://instagram.com/usuario")
            return
        
        url = parts[1]
        
        if not is_valid_url(url, "instagram"):
            await ctx.send("❌ URL de Instagram inválida. Debe ser: instagram.com/usuario")
            return
        
        db.set_social_link("instagram", url)
        await ctx.send(f"✅ Instagram actualizado")
    
    @bot.command(name="setyoutube")
    async def set_youtube_command(ctx: commands.Context):
        """Actualizar YouTube (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !setyoutube https://youtube.com/c/canal")
            await ctx.send("Formatos válidos: youtube.com/c/xxx, youtube.com/@xxx, youtube.com/channel/xxx")
            return
        
        url = parts[1]
        
        if not is_valid_url(url, "youtube"):
            await ctx.send("❌ URL de YouTube inválida")
            return
        
        db.set_social_link("youtube", url)
        await ctx.send(f"✅ YouTube actualizado")
    
    @bot.command(name="settiktok")
    async def set_tiktok_command(ctx: commands.Context):
        """Actualizar TikTok (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !settiktok https://tiktok.com/@usuario")
            return
        
        url = parts[1]
        
        if not is_valid_url(url, "tiktok"):
            await ctx.send("❌ URL de TikTok inválida. Debe ser: tiktok.com/@usuario")
            return
        
        db.set_social_link("tiktok", url)
        await ctx.send(f"✅ TikTok actualizado")