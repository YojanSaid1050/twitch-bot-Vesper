"""
Comandos personalizados por el streamer
"""

from twitchio.ext import commands

from services.custom_commands import custom_commands_service
from bot.permissions import permission_checker


def setup_custom_commands(bot):
    """Configurar sistema de comandos personalizados"""
    
    @bot.command(name="comando", aliases=["custom", "cmd"])
    async def custom_command_root(ctx: commands.Context):
        """Comando base para gestionar comandos personalizados"""
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Subcomandos: !comando add <nombre> <respuesta>, !comando remove <nombre>, !comando list")
            await ctx.send("Ejemplo: !comando add saludo Hola {user}, bienvenido!")
            return
        
        subcommand = parts[1].lower()
        
        if subcommand == "add":
            await _add_command(ctx, parts)
        elif subcommand == "remove" or subcommand == "delete":
            await _remove_command(ctx, parts)
        elif subcommand == "list":
            await _list_commands(ctx)
        else:
            await ctx.send("🕯️ Subcomandos válidos: add, remove, list")
    
    async def _add_command(ctx, parts):
        """Agregar comando personalizado"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        if len(parts) < 4:
            await ctx.send("🕯️ Uso: !comando add <nombre> <respuesta>")
            await ctx.send("Variables disponibles: {user}, {channel}, {random_emote}")
            return
        
        name = parts[2].lower()
        response = " ".join(parts[3:])
        
        success, message = custom_commands_service.add_command(
            name, response, ctx.author.name
        )
        
        if success:
            await ctx.send(f"✅ Comando !{name} creado: {response[:50]}...")
        else:
            await ctx.send(f"❌ {message}")
    
    async def _remove_command(ctx, parts):
        """Eliminar comando personalizado"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        if len(parts) < 3:
            await ctx.send("🕯️ Uso: !comando remove <nombre>")
            return
        
        name = parts[2].lower()
        
        success, message = custom_commands_service.remove_command(name)
        
        if success:
            await ctx.send(f"✅ Comando !{name} eliminado")
        else:
            await ctx.send(f"❌ {message}")
    
    async def _list_commands(ctx):
        """Listar comandos personalizados"""
        commands_list = custom_commands_service.list_commands()
        
        if not commands_list:
            await ctx.send("📜 No hay comandos personalizados aún. ¡Crea uno con !comando add!")
            return
        
        cmd_names = [f"!{cmd['command_name']}" for cmd in commands_list]
        
        # Enviar en grupos de 10 para no saturar
        if len(cmd_names) > 10:
            await ctx.send(f"📜 Comandos disponibles ({len(cmd_names)}):")
            for i in range(0, len(cmd_names), 10):
                batch = cmd_names[i:i+10]
                await ctx.send("  " + ", ".join(batch))
        else:
            await ctx.send(f"📜 Comandos disponibles: {', '.join(cmd_names)}")
    
    # Interceptor para comandos personalizados
    original_handle_commands = bot.handle_commands
    
    async def custom_handle_commands(message):
        """Manejador que también busca comandos personalizados"""
        ctx = commands.Context(message=message, bot=bot)
        
        # Usar _prefix en lugar de prefix (atributo interno de twitchio)
        prefix = getattr(bot, '_prefix', '!')
        
        if not message.content.startswith(prefix):
            return
        
        # Extraer nombre del comando
        try:
            command_name = message.content[len(prefix):].split()[0].lower()
        except IndexError:
            return
        
        # Verificar si es comando personalizado
        custom_cmd = custom_commands_service.get_command(command_name)
        
        if custom_cmd:
            # Ejecutar comando personalizado
            response = custom_commands_service.process_response(custom_cmd["response"], ctx)
            await ctx.send(response)
            return
        
        # Si no es personalizado, usar manejador original
        await original_handle_commands(message)
    
    bot.handle_commands = custom_handle_commands