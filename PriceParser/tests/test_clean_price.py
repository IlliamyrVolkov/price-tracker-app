import pytest

from src.exceptions import PriceFormatError
from src.parser import Parser


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        # plain numbers
        ("1999", 1999.0),
        (1999, 1999.0),
        (1999.99, 1999.99),
        ("0.01", 0.01),
        # dot as a decimal separator
        ("1999.99", 1999.99),
        ("1999.5", 1999.5),
        # comma as a decimal separator - the regression this table guards
        ("1999,50", 1999.5),
        ("1 999,50", 1999.5),
        ("1\xa0999,50", 1999.5),
        ("1 999,00 грн", 1999.0),
        # thousands separators must not become part of the amount
        ("12 499", 12499.0),
        ("1,299", 1299.0),
        ("1.999", 1999.0),
        ("1.234.567", 1234567.0),
        ("1 234 567,89", 1234567.89),
        # mixed locales: the right-most separator is the decimal one
        ("1.999,00", 1999.0),
        ("1,299.99", 1299.99),
        # more than two decimals is still a decimal separator, not a grouping
        ("1999.994", 1999.99),
        ("1999.995", 2000.0),
        # currency noise around the amount
        ("₴1 499.00", 1499.0),
        ("USD 25.30", 25.3),
        ("25.30 €", 25.3),
        ("1999.", 1999.0),
    ],
)
def test_clean_price_normalizes_value(raw_value, expected):
    assert Parser._clean_price(raw_value) == pytest.approx(expected)


@pytest.mark.parametrize(
    "raw_value",
    [None, "", "   ", "UAH", "грн", "-500", "-1999,50", "0", "0.00", True, False, [], {}],
)
def test_clean_price_rejects_invalid_value(raw_value):
    with pytest.raises(PriceFormatError):
        Parser._clean_price(raw_value)


@pytest.mark.parametrize("raw_value", ["999999999999", "100000000.01"])
def test_clean_price_rejects_implausible_value(raw_value):
    with pytest.raises(PriceFormatError):
        Parser._clean_price(raw_value)
