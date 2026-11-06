from utils.links import BUILTIN_ALLOWED_DOMAINS, domain_matches, extract_domain


def test_extract_domain():
    assert extract_domain("https://www.YouTube.com/watch?v=1") == "youtube.com"
    assert extract_domain("youtube.com/x") == "youtube.com"
    assert extract_domain("http://m.youtube.com:8080/") == "m.youtube.com"


def test_exact_and_subdomain_match():
    assert domain_matches("youtube.com", ["youtube.com"])
    assert domain_matches("m.youtube.com", ["youtube.com"])
    assert domain_matches("youtube.com", ["www.youtube.com"])


def test_partial_names_do_not_match():
    # Antes se usaba "x in dominio": "x.com" permitía "evilx.com"
    assert not domain_matches("evilx.com", ["x.com"])
    assert not domain_matches("spotify.com.malware.xyz", BUILTIN_ALLOWED_DOMAINS)
    assert domain_matches("open.spotify.com", BUILTIN_ALLOWED_DOMAINS)
    assert domain_matches("clips.twitch.tv", BUILTIN_ALLOWED_DOMAINS)
    assert not domain_matches("twitch.tv", BUILTIN_ALLOWED_DOMAINS)


def test_extract_links_keeps_subdomains():
    from utils.links import extract_links
    assert extract_links("mira https://open.spotify.com/track/1 ya") == ["https://open.spotify.com/track/1"]
    assert extract_links("clip: clips.twitch.tv/Abc") == ["clips.twitch.tv/Abc"]
    assert extract_links("www.google.es y evil.xyz/x") == ["www.google.es", "evil.xyz/x"]
    assert extract_links("hola qué tal... 3.5 puntos") == []
