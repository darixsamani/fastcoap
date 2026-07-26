from __future__ import annotations
from typing import Any
import aiocoap
import aiocoap.numbers.codes as codes

from fastcoap.encodings import ContentFormat, encode_payload


_CODE_MAP: dict[int, aiocoap.numbers.codes.Code] = {
    200: codes.CHANGED,
    201: codes.CREATED,
    204: codes.DELETED,
    400: codes.BAD_REQUEST,
    401: codes.UNAUTHORIZED,
    403: codes.FORBIDDEN,
    404: codes.NOT_FOUND,
    405: codes.METHOD_NOT_ALLOWED,
    500: codes.INTERNAL_SERVER_ERROR,
}

_GET_OK = codes.CONTENT


class CoapResponse:
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        content_format: ContentFormat = ContentFormat.JSON,
    ):
        self.content = content
        self.status_code = status_code
        self.content_format = content_format

    def to_message(self, is_get: bool = False) -> aiocoap.Message:
        if self.status_code == 200 and is_get:
            code = _GET_OK
        else:
            code = _CODE_MAP.get(self.status_code, codes.CHANGED)

        if self.content is None:
            return aiocoap.Message(code=code)

        payload = encode_payload(self.content, self.content_format)
        msg = aiocoap.Message(code=code, payload=payload)
        msg.opt.content_format = int(self.content_format)
        return msg