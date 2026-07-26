"""
Content-Format negotiation: JSON (50) and CBOR (60).
"""
from __future__ import annotations
import json
from enum import IntEnum
from typing import Any

import cbor2


class ContentFormat(IntEnum):
    TEXT = 0
    JSON = 50
    CBOR = 60


def encode_payload(data: Any, content_format: ContentFormat) -> bytes:
    if content_format == ContentFormat.CBOR:
        return cbor2.dumps(data)
    return json.dumps(data, default=str).encode()


def decode_payload(raw: bytes, content_format: ContentFormat) -> Any:
    if not raw:
        return None
    if content_format == ContentFormat.CBOR:
        return cbor2.loads(raw)
    return json.loads(raw.decode())


def detect_format(coap_message) -> ContentFormat:
    """Read the content-format option from an aiocoap Message."""
    try:
        cf = coap_message.opt.content_format
        if cf == 60:
            return ContentFormat.CBOR
    except Exception:
        pass
    return ContentFormat.JSON