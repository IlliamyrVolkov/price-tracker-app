import pytest
from src.parser import Parser


def test_get_price_success_puma():
    test_url = "https://ua.puma.com/uk/puma-fade-sneakers-unisex-406203-09.html"
    parser = Parser(url=test_url)
    price = parser.get_price()
    assert 5990 == price


def test_get_price_success_rozetka():
    test_url = "https://rozetka.com.ua/ua/jbl_jblt720btblk/p369896661/"
    parser = Parser(url=test_url)
    price = parser.get_price()
    assert 1999 == price


def test_get_price_unsupported_site_raises_error():
    test_url = "https://www.newyorker.de/ua/products/detail/06.04.115.0270/001"
    parser = Parser(url=test_url)
    with pytest.raises(ValueError) as e:
        parser.get_price()

    assert "Unable to find price: site does not use standard SEO tags" in str(e.value)
