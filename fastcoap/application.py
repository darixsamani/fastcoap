"""
Core FastCOAP application.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, AsyncGenerator

import aiocoap
import aiocoap.resource as resource
import aiocoap.interfaces as interfaces

from fastcoap.routing import Router, Route
from fastcoap.request import CoapRequest
from fastcoap.response import CoapResponse
from fastcoap.exceptions import CoapException
from fastcoap.middleware import MiddlewareStack
from fastcoap.dependencies import resolve_handler_kwargs

log = logging.getLogger("fastcoap")


class _WildcardSite(interfaces.Resource, resource.PathCapable):
    def __init__(self, app: "FastCOAP"):
        super().__init__()
        self._app = app

    async def needs_blockwise_assembly(self, request) -> bool:
        return False

    async def render(self, request: aiocoap.Message) -> aiocoap.Message:
        return await self._app._dispatch(request)


class FastCOAP(Router):
    def __init__(
        self,
        *,
        title: str = "FastCOAP",
        version: str = "0.1.0",
        description: str = "A FastAPI-style CoAP framework",
        lifespan: Callable | None = None,
    ):
        super().__init__()
        self.title = title
        self.version = version
        self.description = description
        self._lifespan = lifespan
        self._middleware = MiddlewareStack()
        self._startup_handlers: list[Callable] = []
        self._shutdown_handlers: list[Callable] = []
        self.state: dict[str, Any] = {}

    # ── router inclusion ──────────────────────────────────────────────────────

    def include_router(
        self,
        router: Router,
        *,
        prefix: str = "",
        tags: list[str] | None = None,
    ) -> None:
        for route in router.routes:
            self.routes.append(Route(
                path=prefix + route.path,
                method=route.method,
                handler=route.handler,
                summary=route.summary,
                description=route.description,
                tags=(tags or []) + route.tags,
                response_model=route.response_model,
            ))

    # ── middleware ────────────────────────────────────────────────────────────

    def add_middleware(self, mw) -> None:
        self._middleware.add(mw)

    # ── lifecycle hooks ───────────────────────────────────────────────────────

    def on_startup(self, func: Callable) -> Callable:
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Callable) -> Callable:
        self._shutdown_handlers.append(func)
        return func

    # ── dispatch ──────────────────────────────────────────────────────────────

    async def _dispatch(self, raw: aiocoap.Message) -> aiocoap.Message:
        coap_req = CoapRequest(raw)
        method = coap_req.method
        path = coap_req.path

        async def endpoint(req: CoapRequest) -> CoapResponse:
            route, path_params = self.find_route(method, path)

            if route is None:
                for r in self.routes:
                    if r.match(path) is not None:
                        from fastcoap.exceptions import MethodNotAllowed
                        raise MethodNotAllowed()
                from fastcoap.exceptions import NotFound
                raise NotFound(f"No route for {method} {path}")

            req.path_params = path_params
            kwargs = await resolve_handler_kwargs(route.handler, req, path_params)

            if inspect.iscoroutinefunction(route.handler):
                result = await route.handler(**kwargs)
            else:
                result = route.handler(**kwargs)

            if isinstance(result, CoapResponse):
                return result
            if isinstance(result, (dict, list)):
                return CoapResponse(content=result)
            if hasattr(result, "model_dump"):
                return CoapResponse(content=result.model_dump())
            return CoapResponse(content=result)

        try:
            response = await self._middleware.run(coap_req, endpoint)
            return response.to_message(is_get=(method == "GET"))
        except CoapException as exc:
            # CoapException subclasses (NotFound, BadRequest, etc.) raised
            # inside handlers are caught here and converted to CoAP error
            # responses automatically — no decorator needed.
            return _error_response(exc.status_code, exc.detail)
        except Exception as exc:
            log.exception("Unhandled exception in dispatch")
            return _error_response(500, str(exc))

    # ── lifespan ──────────────────────────────────────────────────────────────

    async def _run_startup(self) -> None:
        if self._lifespan is not None:
            gen = self._lifespan(self)
            if hasattr(gen, "__aenter__"):
                self._lifespan_cm = gen
                state = await gen.__aenter__()
                if state:
                    self.state.update(state)
            else:
                self._lifespan_cm = None
                self._lifespan_gen = gen
                try:
                    val = await gen.__anext__()
                    if isinstance(val, dict):
                        self.state.update(val)
                except StopAsyncIteration:
                    pass
        else:
            self._lifespan_cm = None
            self._lifespan_gen = None
            for h in self._startup_handlers:
                await _maybe_await(h)

    async def _run_shutdown(self) -> None:
        if self._lifespan is not None:
            if self._lifespan_cm is not None:
                await self._lifespan_cm.__aexit__(None, None, None)
            else:
                try:
                    await self._lifespan_gen.__anext__()
                except StopAsyncIteration:
                    pass
        else:
            for h in self._shutdown_handlers:
                await _maybe_await(h)

    # ── serve ─────────────────────────────────────────────────────────────────

    async def serve(self, host: str = "0.0.0.0", port: int = 5683) -> None:
        await self._run_startup()
        try:
            site = _WildcardSite(self)
            coap_server = await aiocoap.Context.create_server_context(
                site, bind=(host, port)
            )
            log.info(f"FastCOAP listening on coap://{host}:{port}")
            try:
                while True:
                    await asyncio.sleep(3600)
            except (asyncio.CancelledError, KeyboardInterrupt):
                pass
            finally:
                await coap_server.shutdown()
        finally:
            await self._run_shutdown()


# ── helpers ───────────────────────────────────────────────────────────────────

def _error_response(status: int, detail: Any) -> aiocoap.Message:
    import json
    import aiocoap.numbers.codes as codes

    _map = {
        400: codes.BAD_REQUEST,
        401: codes.UNAUTHORIZED,
        403: codes.FORBIDDEN,
        404: codes.NOT_FOUND,
        405: codes.METHOD_NOT_ALLOWED,
        500: codes.INTERNAL_SERVER_ERROR,
    }
    code = _map.get(status, codes.INTERNAL_SERVER_ERROR)
    payload = json.dumps({"detail": str(detail)}).encode()
    msg = aiocoap.Message(code=code, payload=payload)
    msg.opt.content_format = 50
    return msg


async def _maybe_await(func: Callable) -> None:
    if inspect.iscoroutinefunction(func):
        await func()
    else:
        func()