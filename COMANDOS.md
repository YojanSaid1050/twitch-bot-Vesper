# Guía de comandos de VesperBot

## Comandos personalizados (estilo Nightbot)

Solo staff (mods y streamer):

| Comando | Qué hace |
|---|---|
| `!comando add <nombre> <respuesta>` | Crea un comando |
| `!comando edit <nombre> <respuesta>` | Cambia la respuesta |
| `!comando remove <nombre>` | Lo borra |
| `!comando cooldown <nombre> <seg> [seg_por_usuario]` | Cooldown global y por usuario |
| `!comando level <nombre> <everyone\|sub\|vip\|mod\|owner>` | Quién puede usarlo |
| `!comando info <nombre>` | Nivel, cooldown, usos y respuesta |
| `!comando list` | Lista (cualquiera puede usarlo) |

El staff se salta los cooldowns.

### Variables en la respuesta

| Variable | Resultado |
|---|---|
| `{user}` | Quien usa el comando |
| `{touser}` | Primer argumento sin `@` (o `{user}` si no hay) |
| `{args}` / `{1}`…`{9}` | Todo el texto / el argumento N |
| `{count}` | Veces que se ha usado (se guarda) |
| `{random:1-100}` | Número aleatorio |
| `{pick:a\|b\|c}` | Elige una opción al azar |
| `{uptime}` `{game}` `{title}` | Datos del directo |
| `{channel}` `{random_emote}` | Canal / emote de la temática |

Ejemplos:

```
!comando add abrazo {user} abraza a {touser} 🤗
!comando add muertes El streamer ha muerto {count} veces 💀
!comando add amor {user} y {touser} son {random:0-100}% compatibles
```

Por seguridad, una respuesta nunca puede empezar por `/` o `.` (salvo `/me`
escrito en la propia plantilla), así nadie puede colar `/ban` a través de `{args}`.

## Nuevos comandos

| Comando | Quién | Qué hace |
|---|---|---|
| `!followage [usuario]` | Todos | Cuánto tiempo lleva siguiendo el canal |
| `!quote [número]` | Todos | Cita aleatoria o la indicada |
| `!quote add <texto>` / `!quote del <n>` | Staff | Gestiona citas |
| `!timer add <nombre> <min> <mensaje>` | Staff | Mensaje automático cada X minutos (mín. 5) |
| `!timer remove\|on\|off <nombre>` / `!timer list` | Staff | Gestiona timers |
| `!permit <usuario> [seg]` | Staff | Deja enviar UN enlace durante 60 s (o los indicados) |
| `!announce [blue\|green\|orange\|purple] <msg>` | Staff | Anuncio destacado nativo de Twitch |

Los timers solo se envían con el directo en vivo y si han llegado al menos
5 mensajes al chat desde el último envío (para no hablar solo).

## Cambios de comportamiento

- `!ban` ahora es **permanente** (antes era un timeout de 14 días). Las sanciones
  automáticas del anti-spam siguen siendo baneos temporales de 14 días.
- El silencio automático usa los minutos configurados en el dashboard
  (`auto_timeout_minutes`) en lugar de 10 fijos, y `!warn` respeta el máximo de
  advertencias configurado.
- `!clip` tiene cooldown (30 s global, 2 min por usuario; el staff se lo salta).
- `!shoutout` también lanza el shoutout oficial de Twitch cuando es posible.

## Permisos (scopes) de Twitch necesarios

Token del **bot** (moderador):
`moderator:manage:banned_users`, `moderator:manage:chat_messages`,
`moderator:manage:chat_settings`, `moderator:manage:announcements` *(nuevo)*,
`moderator:manage:shoutouts` *(nuevo)*, `moderator:read:followers` *(nuevo, para !followage)*.

Token del **streamer**:
`channel:manage:broadcast`, `channel:edit:commercial`, `clips:edit`,
`channel:manage:vips`, `channel:read:subscriptions`.

Si falta `moderator:manage:announcements`, `!announce` envía un mensaje normal.
Si falta `moderator:manage:shoutouts`, `!so` envía solo el mensaje de texto.

## Variables de entorno recomendadas

- `DASHBOARD_SECRET_KEY`: obligatoria en producción. Si no se define se usa una
  clave aleatoria y las sesiones del dashboard se cierran al reiniciar.
- `TWITCH_WEBHOOK_SECRET`: sin ella el webhook de EventSub rechaza todas las peticiones.
- `DASHBOARD_SECURE_COOKIES=1`: envía la cookie de sesión solo por HTTPS (en Render se activa sola).

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```
