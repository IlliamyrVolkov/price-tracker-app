import ipaddress
import socket

import pytest

from src.core import validators
from src.core.validators import validate_public_http_url
from src.exceptions import InvalidUrlError

PUBLIC_IP = "93.184.216.34"
HOSTS = {
    "localhost": "127.0.0.1",
    "internal.example.com": "10.1.2.3",
    "postgres_db": "172.18.0.2",
}
UNRESOLVABLE = {"missing.invalid"}


@pytest.fixture(autouse=True)
def stub_dns(monkeypatch):
    """Resolve ip literals to themselves and hostnames through the HOSTS map."""

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host in UNRESOLVABLE:
            raise socket.gaierror("name or service not known")
        try:
            address = str(ipaddress.ip_address(host))
        except ValueError:
            address = HOSTS.get(host, PUBLIC_IP)
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, port))]

    monkeypatch.setattr(validators.socket, "getaddrinfo", fake_getaddrinfo)


@pytest.mark.parametrize(
    "url",
    [
        "https://ua.puma.com/uk/puma-fade-sneakers-406203-09.html",
        "http://example.com",
        "https://example.com:443/product?id=1#anchor",
        "  https://example.com/spaces-are-trimmed  ",
    ],
)
def test_public_urls_are_accepted(url):
    assert validate_public_http_url(url) == url.strip()


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "javascript:alert(1)",
        "gopher://example.com",
        "//example.com/no-scheme",
    ],
)
def test_non_http_schemes_are_rejected(url):
    with pytest.raises(InvalidUrlError):
        validate_public_http_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://0.0.0.0/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://internal.example.com/",
    ],
)
def test_private_targets_are_rejected(url):
    with pytest.raises(InvalidUrlError):
        validate_public_http_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://postgres_db:5432/",
        "http://example.com:6379/",
        "http://example.com:8080/",
    ],
)
def test_unexpected_ports_are_rejected(url):
    with pytest.raises(InvalidUrlError):
        validate_public_http_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        None,
        "https://",
        "https://user:password@example.com/",
        "http://example.com:not-a-port/",
        "https://example.com/" + "x" * validators.MAX_URL_LENGTH,
        "http://missing.invalid/",
    ],
)
def test_malformed_urls_are_rejected(url):
    with pytest.raises(InvalidUrlError):
        validate_public_http_url(url)
