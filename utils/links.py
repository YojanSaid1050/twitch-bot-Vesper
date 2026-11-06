"""
Utilidades puras para analizar enlaces del chat.
"""

import re
from urllib.parse import urlparse

# Antes el patrón cortaba los enlaces con subdominio ("https://open.spotify.com"
# se leía como "open.spotify"), así que se bloqueaban enlaces permitidos.
_LINK_RE = re.compile(
    r'https?://[^\s/]+\.[^\s/]+\S*'
    r'|\bwww\.[^\s/]+\.[^\s/]+\S*'
    r'|\b(?:[a-zA-Z0-9-]+\.)+(?:com|net|org|es|io|gg|tv|ly|co|it|eu|me|xyz|link|app|dev|info|ru|cn|be)\b(?:/\S*)?',
    re.IGNORECASE,
)


def extract_links(message: str) -> list:
    """Encuentra los enlaces de un mensaje (con o sin http://)."""
    return _LINK_RE.findall(message or "")


# Dominios siempre permitidos (song requests y clips)
BUILTIN_ALLOWED_DOMAINS = ("spotify.com", "spotify.link", "clips.twitch.tv")


def extract_domain(link: str) -> str:
    """Devuelve el dominio en minúsculas, sin 'www.' ni puerto."""
    link = (link or "").strip()
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', link):
        link = "http://" + link
    domain = (urlparse(link).hostname or "").lower().rstrip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def domain_matches(domain: str, allowed_domains) -> bool:
    """True si `domain` es igual a un dominio permitido o es subdominio suyo."""
    domain = (domain or "").lower()
    for allowed in allowed_domains:
        allowed = (allowed or "").lower().strip().strip(".")
        if allowed.startswith("www."):
            allowed = allowed[4:]
        if allowed and (domain == allowed or domain.endswith("." + allowed)):
            return True
    return False
