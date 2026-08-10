from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
import json
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests

from src.core.logger import logger
from src.core.validators import validate_public_http_url
from src.exceptions import PriceFetchError, PriceFormatError, PriceNotFoundError

# Everything that is not a digit or a separator is noise: currency symbols,
# letters, regular and non-breaking spaces, narrow spaces, apostrophes.
_NOISE = re.compile(r"[^\d.,]")
_SEPARATORS = re.compile(r"[.,]")

_CENTS = Decimal("0.01")
_MIN_PRICE = Decimal("0.01")
_MAX_PRICE = Decimal("100000000")

# The browser profile also supplies a matching User-Agent, so setting one by
# hand would only make the fingerprint inconsistent.
_IMPERSONATE = "chrome110"
_DEFAULT_HEADERS = {"Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8"}
_REQUEST_TIMEOUT = 15.0
_MAX_REDIRECTS = 5
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class Parser:
    def __init__(self, url: str, timeout: float = _REQUEST_TIMEOUT) -> None:
        self.url = url
        self.timeout = timeout
        self.headers = dict(_DEFAULT_HEADERS)

    def _get_html(self) -> str:
        url = validate_public_http_url(self.url)

        with requests.Session() as session:
            for _ in range(_MAX_REDIRECTS + 1):
                try:
                    response = session.get(
                        url,
                        headers=self.headers,
                        impersonate=_IMPERSONATE,
                        timeout=self.timeout,
                        allow_redirects=False,
                    )
                except Exception as error:
                    raise PriceFetchError(f"request to {url} failed: {error}") from error

                if response.status_code not in _REDIRECT_STATUSES:
                    if response.status_code >= 400:
                        raise PriceFetchError(f"{url} returned HTTP {response.status_code}")
                    return response.text

                location = response.headers.get("location")
                if not location:
                    raise PriceFetchError(
                        f"{url} returned HTTP {response.status_code} without a location header"
                    )
                url = validate_public_http_url(urljoin(url, location))
                logger.info("Following redirect to %s", url)

        raise PriceFetchError(f"more than {_MAX_REDIRECTS} redirects starting from {self.url}")

    @staticmethod
    def _is_thousands_grouping(digits: str, separator: str) -> bool:
        """Tell whether ``separator`` splits ``digits`` into thousands groups.

        A thousands separator always produces groups of exactly three digits
        after the first one: ``1.999``, ``12,499``, ``1.234.567``.  Anything
        else (``1999.99``, ``1999,5``, ``1999.994``) is a decimal separator.
        """
        groups = digits.split(separator)
        if len(groups) < 2:
            return False
        return 1 <= len(groups[0]) <= 3 and all(len(group) == 3 for group in groups[1:])

    @classmethod
    def _normalize_number(cls, text: str) -> str:
        """Turn a human formatted amount into a plain ``123.45`` string.

        ``.`` and ``,`` are used both as decimal and as thousands separators
        depending on the locale, so the separator role has to be guessed::

            "1 999,50"  -> "1999.50"    comma is decimal
            "1.999,00"  -> "1999.00"    right-most separator is decimal
            "1,299.99"  -> "1299.99"    right-most separator is decimal
            "1,299"     -> "1299"       valid thousands grouping
            "1.234.567" -> "1234567"    valid thousands grouping
        """
        digits = _NOISE.sub("", text)
        if not any(char.isdigit() for char in digits):
            raise PriceFormatError(f"no digits in price value {text!r}")

        has_dot = "." in digits
        has_comma = "," in digits

        if has_dot and has_comma:
            # Two different separators: the right-most one is the decimal one.
            decimal_pos = max(digits.rfind("."), digits.rfind(","))
        elif has_dot or has_comma:
            separator = "." if has_dot else ","
            if cls._is_thousands_grouping(digits, separator):
                decimal_pos = -1
            else:
                decimal_pos = digits.rfind(separator)
        else:
            decimal_pos = -1

        if decimal_pos < 0:
            return _SEPARATORS.sub("", digits)

        whole = _SEPARATORS.sub("", digits[:decimal_pos]) or "0"
        fraction = _SEPARATORS.sub("", digits[decimal_pos + 1:])
        return f"{whole}.{fraction}" if fraction else whole

    @classmethod
    def _clean_price(cls, raw_value: Any) -> float:
        """Normalize a raw price into a positive amount rounded to cents.

        :raises PriceFormatError: the value is missing, unreadable, not
            positive or far outside of a plausible price range.
        """
        if raw_value is None or isinstance(raw_value, bool):
            raise PriceFormatError(f"unsupported price value: {raw_value!r}")

        if isinstance(raw_value, (int, float, Decimal)):
            try:
                value = Decimal(str(raw_value))
            except InvalidOperation as error:
                raise PriceFormatError(f"unsupported price value: {raw_value!r}") from error
        else:
            text = str(raw_value).strip()
            if not text:
                raise PriceFormatError("empty price value")
            try:
                value = Decimal(cls._normalize_number(text))
            except InvalidOperation as error:
                raise PriceFormatError(f"cannot read price value {raw_value!r}") from error
            if text.startswith("-"):
                value = -value

        if not value.is_finite():
            raise PriceFormatError(f"price value is not finite: {raw_value!r}")
        if not _MIN_PRICE <= value <= _MAX_PRICE:
            raise PriceFormatError(
                f"price {value} is outside of the plausible range "
                f"[{_MIN_PRICE}, {_MAX_PRICE}]"
            )

        return float(value.quantize(_CENTS, rounding=ROUND_HALF_UP))

    @staticmethod
    def _iter_json_ld_prices(soup: BeautifulSoup) -> Iterator[tuple[str, Any]]:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.text)
            except (json.JSONDecodeError, AttributeError):
                continue

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("@graph") or [data]
            else:
                continue
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                item_type = item.get("@type")
                types = item_type if isinstance(item_type, list) else [item_type]
                if "Product" not in types:
                    continue

                offers = item.get("offers")
                if isinstance(offers, dict):
                    offers = [offers]
                if not isinstance(offers, list):
                    continue

                for offer in offers:
                    if not isinstance(offer, dict):
                        continue
                    raw_price = offer.get("price")
                    if raw_price is None:
                        raw_price = offer.get("lowPrice")
                    if raw_price is not None:
                        yield "ld+json", raw_price

    def _iter_price_candidates(self, soup: BeautifulSoup) -> Iterator[tuple[str, Any]]:
        """Yield ``(source, raw_value)`` pairs, most reliable source first."""
        og_price = soup.find("meta", property="product:price:amount")
        if og_price and og_price.get("content"):
            yield "og:product:price:amount", og_price.get("content")

        main_block = soup.find("div", class_="product-info-main")
        if main_block:
            price_wrapper = main_block.find("span", attrs={"data-price-type": "finalPrice"})
            if price_wrapper:
                price_span = price_wrapper.find("span", class_="price")
                if price_span:
                    yield "product-info-main", price_span.get_text()

        yield from self._iter_json_ld_prices(soup)

        meta_price = soup.find("meta", attrs={"itemprop": "price"})
        if meta_price and meta_price.get("content"):
            yield "itemprop:price", meta_price.get("content")

    def get_price(self) -> float:
        soup = BeautifulSoup(self._get_html(), "html.parser")

        for source, raw_value in self._iter_price_candidates(soup):
            try:
                price = self._clean_price(raw_value)
            except PriceFormatError as error:
                logger.warning("Skipping price from %s (%r): %s", source, raw_value, error)
                continue
            logger.info("Price %.2f found in %s", price, source)
            return price

        raise PriceNotFoundError("Unable to find price: site does not use standard SEO tags")
