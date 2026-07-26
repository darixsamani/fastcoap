"""
FastAPI-style parameter descriptors + Depends().
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class PathParam:
    name: str
    default: Any = ...
    description: str = ""


@dataclass
class QueryParam:
    name: str
    default: Any = None
    description: str = ""


@dataclass
class BodyParam:
    model: type | None = None
    description: str = ""


@dataclass
class DependsMarker:
    dependency: Callable
    use_cache: bool = True


def Path(name: str = "", *, default: Any = ..., description: str = "") -> PathParam:  # noqa: N802
    return PathParam(name=name, default=default, description=description)


def Query(name: str = "", *, default: Any = None, description: str = "") -> QueryParam:  # noqa: N802
    return QueryParam(name=name, default=default, description=description)


def Body(*, model=None, description: str = "") -> BodyParam:  # noqa: N802
    return BodyParam(model=model, description=description)


def Depends(dependency: Callable, *, use_cache: bool = True) -> DependsMarker:  # noqa: N802
    return DependsMarker(dependency=dependency, use_cache=use_cache)