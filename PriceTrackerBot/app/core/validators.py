import re
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_URL_LENGTH = 2048
MAX_PRICE = Decimal("100000000")

_CENTS = Decimal("0.01")
# re.ASCII keeps \d to 0-9: str.isdigit() also accepts "²", which int() rejects.
_PRICE = re.compile(r"\d+(?:[.,]\d{1,2})?", re.ASCII)
_ID = re.compile(r"\d{1,18}", re.ASCII)
_CURRENCY_SUFFIX = re.compile(r"(₴|грн\.?|uah)$", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def is_http_url(value: str | None) -> bool:
    if not value:
        return False
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return False
    return parts.scheme in ALLOWED_SCHEMES and bool(parts.netloc)


def normalize_url(value: str | None) -> str | None:
    """Return a fetchable http(s) url, or None if ``value`` is not one.

    Telegram highlights ``rozetka.com.ua/...`` as a link even without a
    scheme, so such links get ``https://`` added.
    """
    if not value:
        return None
    url = value.strip()
    if "://" not in url:
        url = f"https://{url}"
    if len(url) > MAX_URL_LENGTH or not is_http_url(url):
        return None
    return url


def parse_price(text: str | None) -> float | None:
    """Read a user typed amount such as ``1499``, ``1 499,50`` or ``1499.99 грн``."""
    if not text:
        return None
    compact = _CURRENCY_SUFFIX.sub("", _WHITESPACE.sub("", text))
    if not _PRICE.fullmatch(compact):
        return None
    value = Decimal(compact.replace(",", "."))
    if not 0 < value <= MAX_PRICE:
        return None
    return float(value.quantize(_CENTS, rounding=ROUND_HALF_UP))


def parse_id(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip()
    if not _ID.fullmatch(text):
        return None
    value = int(text)
    return value if value > 0 else None
