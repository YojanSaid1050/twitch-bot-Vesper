"""
Comandos de interacción y entretenimiento
"""

import random
from twitchio.ext import commands

from utils.formatters import format_choice


def setup_interaction_commands(bot):
    """Registrar comandos de interacción"""
    
    @bot.command(name="8ball", aliases=["8b", "bola8"])
    async def eight_ball(ctx: commands.Context):
        """Responde preguntas mágicamente"""
        parts = ctx.message.content.split(" ", 1)
        
        if len(parts) < 2:
            await ctx.send("🕯️ Conjura tu pregunta al vacío: !8ball ¿Voy a ganar hoy?")
            return
        
        question = parts[1]
        
        respuestas = [
            "✨ Sí, definitivamente.", "🔮 Sin duda alguna.",
            "✅ Es cierto.", "🎯 Sí, confía en ello.",
            "🤔 Respuesta confusa, intenta de nuevo.",
            "❓ Pregunta de nuevo más tarde.",
            "🚫 No cuentes con ello.", "🌙 Mis fuentes dicen que no.",
            "💀 Muy dudoso.", "⚡ El silencio dice que no."
        ]
        
        await ctx.send(f"🔮 {ctx.author.name}: {question} → {random.choice(respuestas)}")
    
    @bot.command(name="dado", aliases=["roll", "dice"])
    async def roll_dice(ctx: commands.Context):
        """Lanza un dado de 1-6"""
        result = random.randint(1, 6)
        emotes = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        await ctx.send(f"🎲 {ctx.author.name} lanzó el dado: {emotes[result]} {result}")
    
    @bot.command(name="moneda", aliases=["coin", "caraocruz"])
    async def flip_coin(ctx: commands.Context):
        """Lanza una moneda"""
        result = random.choice(["🪙 Cara", "💰 Cruz"])
        await ctx.send(f"{result} → {ctx.author.name}")
    
    @bot.command(name="elige", aliases=["choose"])
    async def choose_option(ctx: commands.Context):
        """Elige entre opciones separadas por 'o'"""
        parts = ctx.message.content.split(" ", 1)
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !elige Pizza o Hamburguesa o Ensalada")
            return
        
        options = [opt.strip() for opt in parts[1].split(" o ")]
        
        if len(options) < 2:
            await ctx.send("❌ Separa las opciones con 'o'")
            return
        
        chosen = random.choice(options)
        await ctx.send(f"🤔 {ctx.author.name} pregunta... → {chosen}")
    
    @bot.command(name="lurk", aliases=["modolurk"])
    async def lurk_mode(ctx: commands.Context):
        """Activar modo ausente"""
        await ctx.send(f"🌑 {ctx.author.name} se sumerge en las sombras. Que la oscuridad te proteja.")
    
    @bot.command(name="unlurk", aliases=["regresar"])
    async def unlurk_mode(ctx: commands.Context):
        """Desactivar modo ausente"""
        await ctx.send(f"👁️ {ctx.author.name} ha regresado de las tinieblas...")