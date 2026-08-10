from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})


def is_http_url(value: str | None) -> bool:
    if not value:
        return False
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return False
    return parts.scheme in ALLOWED_SCHEMES and bool(parts.netloc)
