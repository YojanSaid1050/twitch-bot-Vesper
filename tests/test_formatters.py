from utils.formatters import format_duration_long


def test_format_duration_long():
    assert format_duration_long(30) == "menos de un minuto"
    assert format_duration_long(60) == "1 minuto"
    assert format_duration_long(86400 + 3 * 3600) == "1 día y 3 horas"
    assert format_duration_long(400 * 86400) == "1 año, 1 mes y 5 días"
