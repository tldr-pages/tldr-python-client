"""Minimal HTTP GET on top of urllib, with the client's TLS options."""

from __future__ import annotations

import ssl
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tldr import __version__

USER_AGENT = f"tldr-python-client/{__version__}"


class NotFound(Exception):
    pass


class NetworkError(Exception):
    pass


class Http:
    def __init__(self, timeout: float = 10, allow_insecure: bool = False, cafile: Path | None = None):
        self.timeout = timeout
        self.context: ssl.SSLContext | None = None
        if allow_insecure:
            self.context = ssl.create_default_context()
            self.context.check_hostname = False
            self.context.verify_mode = ssl.CERT_NONE
        elif cafile:
            self.context = ssl.create_default_context(cafile=cafile)

    def get(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=self.timeout, context=self.context) as response:
                return response.read()
        except HTTPError as error:
            if error.code == 404:
                raise NotFound(url) from error
            raise NetworkError(f"{url}: HTTP {error.code}") from error
        except (URLError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise NetworkError(f"{url}: {reason}") from error
