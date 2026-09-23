"""Conversation tests: real Dispatcher and routers, fake Telegram and backend."""
import asyncio
import datetime
import itertools

import pytest
from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, MessageEntity, ReplyKeyboardMarkup, Update, User

from main import build_dispatcher
from services.grpc_client.client import grpc_client
from services.grpc_client.price_pb2 import Product
from tg_bot.handlers.add_product import AddProductStates
from tg_bot.handlers.del_product import DeleteProductStates
from tg_bot.handlers.updt_product_price import UpdatePriceStates
from tg_bot.utils.messages import (
    BTN_ADD,
    BTN_CANCEL,
    BTN_CHANGE,
    BTN_DEL,
    BTN_MY_PDT,
    MAIN_MENU_BUTTONS,
    MSG_ASK_NAME,
    MSG_BAD_ID,
    MSG_BAD_PRICE,
    MSG_BAD_URL,
    MSG_CANCELLED,
    MSG_DELETED,
    MSG_NO_PRODUCTS,
    MSG_SERVER_ERROR,
    MSG_START,
    MSG_UNEXPECTED_ERROR,
    MSG_UNKNOWN,
)

USER_ID = 42


class FakeBot(Bot):
    def __init__(self) -> None:
        super().__init__("123456:TEST")
        self.sent = []

    async def __call__(self, method, request_timeout=None):
        self.sent.append(method)
        return True


class FakeBackend:
    def __init__(self) -> None:
        self.products = [Product(product_id=7, name="JBL", url="https://shop.ua/jbl", target_price=1500)]
        self.fail = False
        self.calls = []

    async def register_user(self, user_id, user_name):
        self.calls.append(("register_user", user_id))
        return True

    async def get_products(self, user_id):
        self.calls.append(("get_products", user_id))
        return None if self.fail else list(self.products)

    async def new_product(self, user_id, url, name, target_price):
        self.calls.append(("new_product", user_id, url, name, target_price))
        return 101

    async def del_product(self, product_id, user_id):
        self.calls.append(("del_product", product_id, user_id))
        return True

    async def update_product_price(self, user_id, product_id, target_price):
        self.calls.append(("update_product_price", user_id, product_id, target_price))
        return True


@pytest.fixture(scope="module")
def runner():
    with asyncio.Runner() as runner:
        yield runner


@pytest.fixture(scope="module")
def dispatcher():
    # Routers are module level singletons and can be attached only once.
    return build_dispatcher()


@pytest.fixture
def backend(monkeypatch):
    fake = FakeBackend()
    for name in ("register_user", "get_products", "new_product", "del_product", "update_product_price"):
        monkeypatch.setattr(grpc_client, name, getattr(fake, name))
    return fake


class Conversation:
    _ids = itertools.count(1)

    def __init__(self, dispatcher, runner) -> None:
        self.dispatcher = dispatcher
        self.runner = runner
        self.bot = FakeBot()
        self.key = StorageKey(bot_id=self.bot.id, chat_id=USER_ID, user_id=USER_ID)
        self.runner.run(self.dispatcher.storage.set_state(self.key, None))
        self.runner.run(self.dispatcher.storage.set_data(self.key, {}))

    def send(self, text: str, entities: list[MessageEntity] | None = None) -> list[str]:
        """Send a message as the user and return the texts the bot answered with."""
        self.bot.sent.clear()
        update_id = next(self._ids)
        update = Update(
            update_id=update_id,
            message=Message(
                message_id=update_id,
                date=datetime.datetime.now(),
                chat=Chat(id=USER_ID, type="private"),
                from_user=User(id=USER_ID, is_bot=False, first_name="Test"),
                text=text,
                entities=entities,
            ),
        )
        self.runner.run(self.dispatcher.feed_update(self.bot, update))
        return [method.text for method in self.bot.sent if isinstance(method, SendMessage)]

    @property
    def state(self) -> str | None:
        return self.runner.run(self.dispatcher.storage.get_state(self.key))

    @property
    def data(self) -> dict:
        return self.runner.run(self.dispatcher.storage.get_data(self.key))

    @property
    def last_keyboard(self) -> list[str]:
        markups = [
            method.reply_markup for method in self.bot.sent
            if isinstance(method, SendMessage) and isinstance(method.reply_markup, ReplyKeyboardMarkup)
        ]
        return [button.text for row in markups[-1].keyboard for button in row] if markups else []


@pytest.fixture
def chat(dispatcher, runner, backend):
    return Conversation(dispatcher, runner)


def test_start_leaves_an_unfinished_flow(chat):
    chat.send(BTN_ADD)
    assert chat.state == AddProductStates.waiting_for_url.state

    assert chat.send("/start") == [MSG_START]
    assert chat.state is None
    assert chat.last_keyboard == list(MAIN_MENU_BUTTONS)


def test_menu_button_is_not_taken_as_an_answer(chat, backend):
    chat.send(BTN_ADD)

    replies = chat.send(BTN_MY_PDT)

    assert chat.state is None
    assert "url" not in chat.data
    assert "JBL" in replies[0]


def test_menu_button_switches_between_flows(chat):
    chat.send(BTN_DEL)
    assert chat.state == DeleteProductStates.waiting_for_product_id.state

    chat.send(BTN_CHANGE)

    assert chat.state == UpdatePriceStates.waiting_for_product_id.state


def test_cancel_brings_the_main_menu_back(chat):
    chat.send(BTN_ADD)

    assert chat.send(BTN_CANCEL) == [MSG_CANCELLED]
    assert chat.state is None
    assert chat.last_keyboard == list(MAIN_MENU_BUTTONS)


def test_add_product(chat, backend):
    chat.send(BTN_ADD)
    chat.send("https://rozetka.com.ua/jbl/")
    chat.send("<JBL> навушники")
    replies = chat.send("1 499,50")

    assert ("new_product", USER_ID, "https://rozetka.com.ua/jbl/", "<JBL> навушники", 1499.5) in backend.calls
    assert "<b>&lt;JBL&gt; навушники</b>" in replies[0]
    assert chat.state is None
    assert chat.last_keyboard == list(MAIN_MENU_BUTTONS)


def test_add_product_rejects_bad_input(chat, backend):
    chat.send(BTN_ADD)
    assert chat.send("просто текст") == [MSG_BAD_URL]
    assert chat.state == AddProductStates.waiting_for_url.state

    chat.send("https://shop.ua/item")
    chat.send("Item")
    for bad_price in ("²", "0", "дорого"):
        assert chat.send(bad_price) == [MSG_BAD_PRICE]
    assert chat.state == AddProductStates.waiting_for_price.state
    assert not any(call[0] == "new_product" for call in backend.calls)


def test_link_sent_outside_of_a_flow_starts_adding_it(chat):
    text = "Дивись https://rozetka.com.ua/jbl/ класна"
    url = "https://rozetka.com.ua/jbl/"
    entity = MessageEntity(type="url", offset=text.index(url), length=len(url))

    assert chat.send(text, entities=[entity]) == [MSG_ASK_NAME]
    assert chat.state == AddProductStates.waiting_for_name.state
    assert chat.data["url"] == url


def test_backend_failure_is_not_shown_as_an_empty_list(chat, backend):
    backend.fail = True
    assert chat.send(BTN_MY_PDT) == [MSG_SERVER_ERROR]

    backend.fail = False
    backend.products = []
    assert chat.send(BTN_MY_PDT) == [MSG_NO_PRODUCTS]


def test_delete_accepts_only_ids_from_the_list(chat, backend):
    chat.send(BTN_DEL)

    assert chat.send("8") == [MSG_BAD_ID]
    assert chat.state == DeleteProductStates.waiting_for_product_id.state

    assert chat.send("7") == [MSG_DELETED]
    assert ("del_product", 7, USER_ID) in backend.calls
    assert chat.state is None


def test_update_target_price(chat, backend):
    chat.send(BTN_CHANGE)
    chat.send("7")
    chat.send("1200")

    assert ("update_product_price", USER_ID, 7, 1200.0) in backend.calls
    assert chat.state is None


def test_unknown_message_gets_a_hint(chat):
    assert chat.send("привіт") == [MSG_UNKNOWN]


def test_handler_error_is_reported_and_the_flow_is_reset(chat, backend, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(grpc_client, "new_product", broken)
    chat.send(BTN_ADD)
    chat.send("https://shop.ua/item")
    chat.send("Item")

    assert chat.send("100") == [MSG_UNEXPECTED_ERROR]
    assert chat.state is None
