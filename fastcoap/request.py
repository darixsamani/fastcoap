from __future__ import annotations
from typing import Any
import aiocoap
from fastcoap.encodings import ContentFormat, decode_payload, detect_format


class CoapRequest:
    def __init__(
        self,
        message: aiocoap.Message,
        path_params: dict[str, str] | None = None,
    ):
        self._message = message
        self.path_params: dict[str, str] = path_params or {}
        self.content_format: ContentFormat = detect_format(message)
        self._body: Any = None
        self._body_parsed = False

    @property
    def message(self) -> aiocoap.Message:
        return self._message

    @property
    def method(self) -> str:
        return self._message.code.name

    @property
    def path(self) -> str:
        return "/" + "/".join(self._message.opt.uri_path or [])

    @property
    def query_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        for item in self._message.opt.uri_query or []:
            if "=" in item:
                k, v = item.split("=", 1)
                params[k] = v
            else:
                params[item] = ""
        return params

    @property
    def body(self) -> Any:
        if not self._body_parsed:
            self._body = decode_payload(self._message.payload, self.content_format)
            self._body_parsed = True
        return self._body