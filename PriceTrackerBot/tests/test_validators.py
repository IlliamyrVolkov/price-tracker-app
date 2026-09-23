import pytest

from core.validators import normalize_url, parse_id, parse_price


@pytest.mark.parametrize("text, expected", [
    ("1499", 1499.0),
    ("1499.99", 1499.99),
    ("1499,5", 1499.5),
    ("1 499", 1499.0),
    ("1 499,50", 1499.5),
    ("  1499  ", 1499.0),
    ("1499 грн", 1499.0),
    ("1499₴", 1499.0),
])
def test_parse_price_accepts_common_formats(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text", [
    None, "", "abc", "0", "0.00", "-5", "²", "١٢٣", "1499.999", "1.499,50", "100000001",
])
def test_parse_price_rejects_invalid_amounts(text):
    assert parse_price(text) is None


@pytest.mark.parametrize("text, expected", [("7", 7), (" 42 ", 42)])
def test_parse_id_accepts_positive_numbers(text, expected):
    assert parse_id(text) == expected


@pytest.mark.parametrize("text", [None, "", "0", "-1", "7a", "²", "1" * 19])
def test_parse_id_rejects_everything_else(text):
    assert parse_id(text) is None


@pytest.mark.parametrize("value, expected", [
    ("https://rozetka.com.ua/p1/", "https://rozetka.com.ua/p1/"),
    ("rozetka.com.ua/p1/", "https://rozetka.com.ua/p1/"),
    ("http://shop.ua", "http://shop.ua"),
])
def test_normalize_url_accepts_links(value, expected):
    assert normalize_url(value) == expected


@pytest.mark.parametrize("value", [None, "", "ftp://shop.ua/file", "https://", "https://x.ua/" + "a" * 2048])
def test_normalize_url_rejects_non_links(value):
    assert normalize_url(value) is None
