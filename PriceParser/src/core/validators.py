import ipaddress
import socket
from urllib.parse import urlsplit

from src.exceptions import InvalidUrlError

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})
MAX_URL_LENGTH = 2048

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def _port_of(scheme: str, netloc_port: str | None) -> int:
    if netloc_port is not None:
        return netloc_port
    return 443 if scheme == "https" else 80


def _resolve(hostname: str, port: int) -> list[IpAddress]:
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise InvalidUrlError(f"host {hostname!r} cannot be resolved") from error

    addresses = []
    for info in infos:
        raw_address = info[4][0].split("%")[0]
        try:
            addresses.append(ipaddress.ip_address(raw_address))
        except ValueError:
            raise InvalidUrlError(f"host {hostname!r} resolved to {raw_address!r}") from None
    if not addresses:
        raise InvalidUrlError(f"host {hostname!r} cannot be resolved")
    return addresses


def _is_public(address: IpAddress) -> bool:
    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        address = mapped
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def validate_public_http_url(url: str) -> str:
    """Return the url if it is safe to fetch, otherwise raise InvalidUrlError.

    Urls come from end users, so a plain fetch would let anyone reach services
    that are only reachable from inside the network.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidUrlError("url is empty")

    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise InvalidUrlError(f"url is longer than {MAX_URL_LENGTH} characters")

    try:
        parts = urlsplit(url)
        port = _port_of(parts.scheme, parts.port)
    except ValueError as error:
        raise InvalidUrlError(f"url cannot be parsed: {error}") from error

    if parts.scheme not in ALLOWED_SCHEMES:
        raise InvalidUrlError(f"unsupported scheme {parts.scheme!r}, expected http or https")
    if "@" in parts.netloc:
        raise InvalidUrlError("credentials in the url are not allowed")
    if not parts.hostname:
        raise InvalidUrlError("url has no host")
    if port not in ALLOWED_PORTS:
        raise InvalidUrlError(f"port {port} is not allowed, expected one of {sorted(ALLOWED_PORTS)}")

    for address in _resolve(parts.hostname, port):
        if not _is_public(address):
            raise InvalidUrlError(
                f"host {parts.hostname!r} resolves to the non-public address {address}"
            )

    return url
