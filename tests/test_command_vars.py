import random

from utils import command_vars as cv


def render(template, **kw):
    kw.setdefault("user", "Ana")
    kw.setdefault("rng", random.Random(1))
    return cv.render(template, **kw)


def test_basic_variables():
    out = render("Hola {user}, bienvenida a {channel}", channel="vesper")
    assert out == "Hola Ana, bienvenida a vesper"


def test_touser_and_args():
    assert render("{user} abraza a {touser}", args=["@Luis"]) == "Ana abraza a Luis"
    assert render("{user} abraza a {touser}") == "Ana abraza a Ana"
    assert render("dijo: {args}", args=["hola", "mundo"]) == "dijo: hola mundo"
    assert render("{1}-{2}-{3}", args=["a", "b"]) == "a-b-"


def test_count_and_random():
    assert render("usado {count} veces", count=7) == "usado 7 veces"
    value = int(render("{random:1-6}"))
    assert 1 <= value <= 6
    assert int(render("{random:10-5}")) in range(5, 11)
    assert render("{pick:sí|no}") in ("sí", "no")


def test_dynamic_and_unknown():
    assert cv.needed_dynamic_vars("en {game} desde hace {uptime}") == {"game", "uptime"}
    assert cv.needed_dynamic_vars("sin variables") == set()
    assert render("{game}", extra={"game": "Minecraft"}) == "Minecraft"
    assert render("{desconocida}") == "{desconocida}"
    assert cv.uses_counter("{count} muertes")
    assert not cv.uses_counter("{user}")


def test_args_are_not_reparsed():
    # Un usuario no puede inyectar variables a través de los argumentos
    assert render("{args}", args=["{random:1-1000000}"]) == "{random:1-1000000}"


def test_chat_command_injection_is_blocked():
    assert render("{args}", args=["/ban", "streamer"]) == "ban streamer"
    assert render("{args}", args=[".timeout", "x"]) == "timeout x"
    assert render("/me baila con {user}") == "/me baila con Ana"
    assert render("/me {args}", args=["/ban", "x"]) == "/me ban x"


def test_output_is_truncated():
    assert len(render("x" * 1000)) == cv.MAX_CHAT_LENGTH
