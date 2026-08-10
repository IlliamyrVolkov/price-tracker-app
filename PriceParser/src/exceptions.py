"""Errors raised by the price parser.

Every error also inherits from a builtin exception type, so existing callers
that only catch ``ValueError`` keep working.
"""


class PriceParserError(Exception):
    """Base class for every error raised by the parser."""


class InvalidUrlError(PriceParserError, ValueError):
    """The url is malformed or points to something the parser must not fetch."""


class PriceFetchError(PriceParserError, RuntimeError):
    """The page could not be downloaded."""


class PriceNotFoundError(PriceParserError, ValueError):
    """The page was fetched, but no price could be located on it."""


class PriceFormatError(PriceParserError, ValueError):
    """A price value was located, but it cannot be read as a valid amount."""
