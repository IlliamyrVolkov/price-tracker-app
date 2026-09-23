import json

import pytest

from services.kafka_consumer import (
    PriceDropEvent,
    _build_alert,
    _is_stale,
    _parse_event,
)

NBSP = " "


def _raw(payload) -> bytes:
    return json.dumps(payload).encode()


def test_parse_event_reads_ids_and_prices():
    event = _parse_event(_raw({"user_id": "42", "product_id": 7, "old_price": 2199, "new_price": "1899.5"}))

    assert event == PriceDropEvent(user_id=42, product_id=7, old_price=2199.0, new_price=1899.5)


def test_parse_event_takes_name_and_url_when_the_backend_sends_them():
    event = _parse_event(_raw({
        "user_id": 1, "product_id": 2, "old_price": 10, "new_price": 5,
        "name": "  JBL  ", "url": "https://shop.ua/jbl",
    }))

    assert event.name == "JBL"
    assert event.url == "https://shop.ua/jbl"


@pytest.mark.parametrize("raw", [
    None,
    b"",
    b"not json",
    _raw([1, 2]),
    _raw({"product_id": 1}),
    _raw({"UserID": 1, "ProductID": 2}),
    _raw({"user_id": 0, "product_id": 1}),
])
def test_parse_event_rejects_malformed_messages(raw):
    with pytest.raises((ValueError, KeyError, TypeError)):
        _parse_event(raw)


def test_alert_shows_the_drop_and_escapes_user_text():
    event = PriceDropEvent(user_id=1, product_id=2, old_price=2000, new_price=1500)

    text = _build_alert(event, "<JBL>", "https://shop.ua/?a=1&b=2")

    assert text.startswith("🔔 Ціна на <b>&lt;JBL&gt;</b> знизилась!")
    assert f"<s>2{NBSP}000</s> → <b>1{NBSP}500</b>  (−25%)" in text
    assert 'href="https://shop.ua/?a=1&amp;b=2"' in text


def test_alert_without_old_price_or_link():
    event = PriceDropEvent(user_id=1, product_id=2, old_price=None, new_price=1500)

    text = _build_alert(event, "JBL", "")

    assert f"Нова ціна: <b>1{NBSP}500</b>" in text
    assert "href" not in text


def test_alert_hides_a_rounded_down_zero_percent():
    event = PriceDropEvent(user_id=1, product_id=2, old_price=1000, new_price=999)
    assert "%" not in _build_alert(event, "JBL", "")


def test_is_stale():
    now = 1_700_000_000.0
    assert not _is_stale(int(now * 1000) - 60_000, now=now)
    assert _is_stale(int(now * 1000) - 25 * 3600 * 1000, now=now)
    assert not _is_stale(None, now=now)
    assert not _is_stale(-1, now=now)
