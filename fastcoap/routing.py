"""
Router: stores route definitions and matches incoming CoAP paths.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Callable


_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")


def _path_to_regex(path: str) -> tuple[re.Pattern, list[str]]:
    param_names: list[str] = []

    def replacer(m: re.Match) -> str:
        param_names.append(m.group(1))
        return r"([^/]+)"

    pattern = "^" + _PATH_PARAM_RE.sub(replacer, path) + r"$"
    return re.compile(pattern), param_names


@dataclass
class Route:
    path: str
    method: str
    handler: Callable
    summary: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    response_model: type | None = None
    _regex: re.Pattern = field(init=False)
    _param_names: list[str] = field(init=False)

    def __post_init__(self):
        self._regex, self._param_names = _path_to_regex(self.path)

    def match(self, path: str) -> dict[str, str] | None:
        m = self._regex.match(path)
        if m:
            return dict(zip(self._param_names, m.groups()))
        return None


class Router:
    def __init__(self, prefix: str = "", tags: list[str] | None = None):
        self.prefix = prefix
        self.default_tags: list[str] = tags or []
        self.routes: list[Route] = []

    def _add_route(
        self,
        path: str,
        method: str,
        *,
        summary: str = "",
        description: str = "",
        tags: list[str] | None = None,
        response_model: type | None = None,
    ):
        full_tags = (tags or []) + self.default_tags

        def decorator(func: Callable) -> Callable:
            self.routes.append(
                Route(
                    path=self.prefix + path,
                    method=method,
                    handler=func,
                    summary=summary or func.__name__.replace("_", " ").title(),
                    description=description or (func.__doc__ or ""),
                    tags=full_tags,
                    response_model=response_model,
                )
            )
            return func

        return decorator

    def get(self, path: str, **kw):    return self._add_route(path, "GET", **kw)
    def post(self, path: str, **kw):   return self._add_route(path, "POST", **kw)
    def put(self, path: str, **kw):    return self._add_route(path, "PUT", **kw)
    def delete(self, path: str, **kw): return self._add_route(path, "DELETE", **kw)

    def find_route(
        self, method: str, path: str
    ) -> tuple[Route, dict[str, str]] | tuple[None, None]:
        for route in self.routes:
            if route.method == method:
                params = route.match(path)
                if params is not None:
                    return route, params
        return None, None