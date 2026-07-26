from __future__ import annotations
from typing import Any


class CoapException(Exception):
    def __init__(self, status_code: int, detail: Any = None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


class BadRequest(CoapException):
    def __init__(self, detail: Any = "Bad Request"):
        super().__init__(400, detail)


class Unauthorized(CoapException):
    def __init__(self, detail: Any = "Unauthorized"):
        super().__init__(401, detail)


class NotFound(CoapException):
    def __init__(self, detail: Any = "Not Found"):
        super().__init__(404, detail)


class MethodNotAllowed(CoapException):
    def __init__(self, detail: Any = "Method Not Allowed"):
        super().__init__(405, detail)


class InternalServerError(CoapException):
    def __init__(self, detail: Any = "Internal Server Error"):
        super().__init__(500, detail)