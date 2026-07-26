"""
Dependency injection resolver.
Supports sync and async callables; caches results per-request.
"""
from __future__ import annotations
import inspect
import typing
from typing import Any, Callable

from fastcoap.request import CoapRequest


def _get_type_hints(func: Callable) -> dict[str, Any]:
    """
    Resolve annotations to actual types, handling 'from __future__ import
    annotations' (PEP 563) where all annotations are lazy strings.
    Falls back to the raw __annotations__ dict if resolution fails.
    """
    try:
        return typing.get_type_hints(func)
    except Exception:
        return getattr(func, "__annotations__", {})


async def resolve_dependency(
    func: Callable,
    request: CoapRequest,
    cache: dict,
) -> Any:
    from fastcoap.params import DependsMarker

    if func in cache:
        return cache[func]

    sig = inspect.signature(func)
    hints = _get_type_hints(func)
    kwargs: dict[str, Any] = {}

    for param_name, param in sig.parameters.items():
        default = param.default
        annotation = hints.get(param_name, inspect.Parameter.empty)

        if isinstance(default, DependsMarker):
            kwargs[param_name] = await resolve_dependency(
                default.dependency, request, cache
            )
        elif annotation is CoapRequest or param_name == "request":
            kwargs[param_name] = request
        else:
            val = request.query_params.get(param_name)
            if val is not None:
                if annotation not in (inspect.Parameter.empty, str):
                    try:
                        val = annotation(val)
                    except (ValueError, TypeError):
                        pass
                kwargs[param_name] = val
            elif (
                default is not inspect.Parameter.empty
                and not isinstance(default, DependsMarker)
            ):
                kwargs[param_name] = default

    result = await func(**kwargs) if inspect.iscoroutinefunction(func) else func(**kwargs)
    cache[func] = result
    return result


async def resolve_handler_kwargs(
    handler: Callable,
    request: CoapRequest,
    path_params: dict[str, str],
) -> dict[str, Any]:
    from fastcoap.params import DependsMarker, BodyParam, QueryParam, PathParam
    import pydantic

    sig = inspect.signature(handler)
    hints = _get_type_hints(handler)
    kwargs: dict[str, Any] = {}
    dep_cache: dict = {}

    for param_name, param in sig.parameters.items():
        default = param.default
        annotation = hints.get(param_name, inspect.Parameter.empty)

        if isinstance(default, DependsMarker):
            kwargs[param_name] = await resolve_dependency(
                default.dependency, request, dep_cache
            )

        elif annotation is CoapRequest or param_name == "request":
            kwargs[param_name] = request

        elif isinstance(default, PathParam):
            raw = path_params.get(param_name) or path_params.get(default.name)
            if raw is None and default.default is ...:
                raise ValueError(f"Missing path parameter: {param_name}")
            kwargs[param_name] = _coerce(raw if raw is not None else default.default, annotation)

        elif isinstance(default, QueryParam):
            raw = (
                request.query_params.get(param_name)
                or request.query_params.get(default.name)
            )
            kwargs[param_name] = _coerce(
                raw if raw is not None else default.default, annotation
            )

        elif isinstance(default, BodyParam):
            body_data = request.body
            if default.model and issubclass(default.model, pydantic.BaseModel):
                kwargs[param_name] = default.model.model_validate(body_data)
            else:
                kwargs[param_name] = body_data

        elif param_name in path_params:
            kwargs[param_name] = _coerce(path_params[param_name], annotation)

        elif (
            annotation is not inspect.Parameter.empty
            and isinstance(annotation, type)
            and issubclass(annotation, pydantic.BaseModel)
        ):
            kwargs[param_name] = annotation.model_validate(request.body or {})

        elif param_name in request.query_params:
            kwargs[param_name] = _coerce(
                request.query_params[param_name], annotation
            )

        elif default is not inspect.Parameter.empty:
            kwargs[param_name] = default

    return kwargs


def _coerce(value: Any, annotation: Any) -> Any:
    if annotation is inspect.Parameter.empty or annotation is str or value is None:
        return value
    try:
        return annotation(value)
    except (TypeError, ValueError):
        return value