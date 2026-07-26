from __future__ import annotations
from typing import Callable, Awaitable
from fastcoap.request import CoapRequest
from fastcoap.response import CoapResponse


Middleware = Callable[[CoapRequest, Callable], Awaitable[CoapResponse]]


class MiddlewareStack:
    def __init__(self):
        self._middlewares: list[Middleware] = []

    def add(self, mw: Middleware) -> None:
        self._middlewares.append(mw)

    async def run(self, request: CoapRequest, endpoint: Callable) -> CoapResponse:
        idx = 0
        middlewares = self._middlewares

        async def call_next(req: CoapRequest) -> CoapResponse:
            nonlocal idx
            if idx < len(middlewares):
                mw = middlewares[idx]
                idx += 1
                return await mw(req, call_next)
            return await endpoint(req)

        return await call_next(request)