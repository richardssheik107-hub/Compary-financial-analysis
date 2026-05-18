from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Iterator


_PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")
_NO_PROXY_KEYS = ("NO_PROXY", "no_proxy")


def is_proxy_error(exc: Exception) -> bool:
    text = str(exc).lower()
    proxy_signals = (
        "proxyerror",
        "unable to connect to proxy",
        "failed to establish a new connection",
        "connection refused",
        "max retries exceeded",
    )
    return any(signal in text for signal in proxy_signals)


@contextmanager
def temporary_disable_proxy() -> Iterator[None]:
    backup: dict[str, str] = {}
    removed_keys: list[str] = []
    for key in _PROXY_KEYS:
        if key in os.environ:
            backup[key] = os.environ[key]
            removed_keys.append(key)
            os.environ.pop(key, None)

    no_proxy_backup: dict[str, str] = {}
    for key in _NO_PROXY_KEYS:
        if key in os.environ:
            no_proxy_backup[key] = os.environ[key]
        os.environ[key] = "*"

    try:
        yield
    finally:
        for key in removed_keys:
            os.environ[key] = backup[key]
        for key in _NO_PROXY_KEYS:
            if key in no_proxy_backup:
                os.environ[key] = no_proxy_backup[key]
            else:
                os.environ.pop(key, None)
