from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from html import escape
from urllib.parse import urlsplit

from core.validators import is_http_url
from services.grpc_client.price_pb2 import Product
from tg_bot.utils.messages import MSG_PRODUCTS_HEADER

TELEGRAM_TEXT_LIMIT = 4096
MAX_NAME_DISPLAY_LENGTH = 100

_CENTS = Decimal("0.01")
# A non-breaking space keeps "1 999" from being split across two lines.
_THOUSANDS_SEPARATOR = " "


def format_price(value: float | None) -> str:
    """Format an amount as ``1 999`` or ``1 999.50``; unknown prices become a dash."""
    if value is None or value <= 0:
        return "—"
    amount = Decimal(str(value)).quantize(_CENTS, rounding=ROUND_HALF_UP)
    digits = 0 if amount == amount.to_integral_value() else 2
    return f"{amount:,.{digits}f}".replace(",", _THOUSANDS_SEPARATOR)


def domain_of(url: str) -> str:
    hostname = urlsplit(url).hostname or url
    return hostname.removeprefix("www.")


def _shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit - 1]}…"


def format_product(product: Product) -> str:
    name = product.name or f"Товар #{product.product_id}"
    lines = [f"<code>#{product.product_id}</code> <b>{escape(_shorten(name, MAX_NAME_DISPLAY_LENGTH))}</b>"]

    prices = f"💰 Зараз: {format_price(product.current_price)} · 🎯 Ціль: {format_price(product.target_price)}"
    if 0 < product.current_price <= product.target_price:
        prices += " ✅"
    lines.append(prices)

    if is_http_url(product.url):
        link = escape(product.url, quote=True)
        lines.append(f'🔗 <a href="{link}">{escape(domain_of(product.url))}</a>')
    return "\n".join(lines)


def render_products(products: Sequence[Product]) -> list[str]:
    """Render the product list as HTML messages that each fit into one Telegram message."""
    messages = []
    current = MSG_PRODUCTS_HEADER.format(count=len(products))
    for product in products:
        entry = format_product(product)
        if len(current) + 2 + len(entry) > TELEGRAM_TEXT_LIMIT:
            messages.append(current)
            current = entry
        else:
            current = f"{current}\n\n{entry}"
    messages.append(current)
    return messages
