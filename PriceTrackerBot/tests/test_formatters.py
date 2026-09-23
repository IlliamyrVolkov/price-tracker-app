import pytest

from services.grpc_client.price_pb2 import Product
from tg_bot.utils.formatters import (
    TELEGRAM_TEXT_LIMIT,
    format_price,
    format_product,
    render_products,
)

NBSP = " "


@pytest.mark.parametrize("value, expected", [
    (1999.0, f"1{NBSP}999"),
    (1999.5, f"1{NBSP}999.50"),
    (1234567.891, f"1{NBSP}234{NBSP}567.89"),
    (15.0, "15"),
    (None, "—"),
    (0.0, "—"),
])
def test_format_price(value, expected):
    assert format_price(value) == expected


def test_format_product_escapes_the_name_and_shows_the_domain():
    product = Product(
        product_id=7,
        name="<JBL> & co",
        url="https://www.rozetka.com.ua/jbl/?a=1&b=2",
        target_price=1500,
        current_price=2199,
    )

    text = format_product(product)

    assert "<b>&lt;JBL&gt; &amp; co</b>" in text
    assert "<code>#7</code>" in text
    assert f"Зараз: 2{NBSP}199" in text
    assert f"Ціль: 1{NBSP}500" in text
    assert "✅" not in text
    assert 'href="https://www.rozetka.com.ua/jbl/?a=1&amp;b=2"' in text
    assert ">rozetka.com.ua</a>" in text


def test_format_product_marks_reached_target_and_hides_bad_links():
    product = Product(product_id=1, name="X", url="javascript:alert(1)", target_price=100, current_price=90)

    text = format_product(product)

    assert "✅" in text
    assert "href" not in text


def test_format_product_shows_dash_for_a_price_not_checked_yet():
    text = format_product(Product(product_id=1, name="X", target_price=100))
    assert "Зараз: —" in text


def test_render_products_splits_long_lists_by_the_telegram_limit():
    products = [
        Product(product_id=i, name="n" * 100, url=f"https://shop.ua/{'p' * 300}/{i}", target_price=10)
        for i in range(1, 60)
    ]

    messages = render_products(products)

    assert len(messages) > 1
    assert all(len(message) <= TELEGRAM_TEXT_LIMIT for message in messages)
    joined = "".join(messages)
    assert all(f"<code>#{i}</code>" in joined for i in range(1, 60))
    assert messages[0].startswith("📋 <b>Ваші товари</b> (59)")
