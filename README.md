<p align="center">
  <a href="https://github.com/your-org/fastcoap">
    <img src="https://github.com/user-attachments/assets/2448451a-9625-4f02-885f-45b0c8d1505d" alt="FastCOAP">
  </a>
</p>

<p align="center">
    <em>FastCOAP — a modern, high-performance Python framework for building CoAP applications and APIs.</em>
</p>

<p align="center">
<a href="https://python.org">
    <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
</a>
<a href="https://github.com/your-org/fastcoap/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/darixsamani/fastcoap/tests.yml?label=tests" alt="Tests">
</a>
<a href="https://pypi.org/project/fastcoap">
    <img src="https://img.shields.io/pypi/v/fastcoap?color=%23009688&label=PyPI" alt="PyPI Version">
</a>
<a href="https://pypi.org/project/fastcoap">
    <img src="https://img.shields.io/pypi/pyversions/fastcoap?color=%23009688" alt="Python Versions">
</a>
<a href="LICENSE">
    <img src="https://img.shields.io/github/license/darixsamani/fastcoap" alt="License">
</a>
</p>

---

## Documentation

Coming soon...

## Source Code

https://github.com/darixsamani/fastcoap

---

**FastCOAP** is a modern, fast (high-performance) Python framework for building **CoAP (Constrained Application Protocol)** applications based on standard Python type hints.

Inspired by **FastAPI**, FastCOAP brings the same developer experience to the Internet of Things, making it easy to build scalable, maintainable, and production-ready CoAP services.

## Key Features

- ⚡ **Fast** — High-performance asynchronous framework built for CoAP communication.
- 🌐 **IoT-first** — Designed specifically for connected devices, edge computing, and constrained networks.
- 📡 **Native CoAP** — Full support for the Constrained Application Protocol.
- 🧩 **Simple & Intuitive** — Clean API inspired by FastAPI, with minimal boilerplate.
- 🚀 **Developer Friendly** — Modern Python features, type hints, dependency injection, and automatic validation.
- 📦 **Production Ready** — Modular architecture suitable for embedded systems, gateways, and cloud IoT platforms.
- 🔒 **Reliable** — Built with robustness, scalability, and maintainability in mind.
- 🐍 **Pythonic** — Leverages standard Python type annotations for an excellent developer experience.

## Why FastCOAP?

Building CoAP applications shouldn't feel different from building modern HTTP APIs.

FastCOAP provides an elegant programming model inspired by FastAPI while embracing the CoAP ecosystem. Whether you're developing applications for IoT devices, smart homes, industrial automation, or sensor networks, FastCOAP helps you write less code and ship faster.


---

## Project Structure

```
fastcoap/
├── pyproject.toml          # uv project file, dependencies, CLI entry point
├── README.md
├── fastcoap/
│   ├── __init__.py         # Public API re-exports
│   ├── application.py      # FastCOAP class, dispatcher, aiocoap bridge, serve()
│   ├── routing.py          # Router, Route, path-to-regex compiler
│   ├── request.py          # CoapRequest wrapper around aiocoap.Message
│   ├── response.py         # CoapResponse → aiocoap.Message conversion
│   ├── params.py           # Path(), Query(), Body(), Depends() descriptors
│   ├── dependencies.py     # Dependency injection resolver
│   ├── exceptions.py       # CoapException hierarchy + handler registry
│   ├── middleware.py       # Async middleware chain
│   └── encodings.py        # JSON / CBOR encode + decode, ContentFormat enum
└── examples/
    ├── main.py             # Full demo app (sensors CRUD)
    └── cbor_client.py      # Test client — JSON and CBOR requests
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  fastcoap CLI (Typer)                │
│           fastcoap run main:app --reload             │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                  FastCOAP application                │
│        lifespan · routers · middleware ·             │
│                                  │
└──────┬──────────────────────────────┬───────────────┘
       │                              │
┌──────▼──────┐               ┌───────▼──────────────┐
│   Router    │               │     Dispatcher        │
│  GET/POST   │               │  path match           │
│  PUT/DELETE │               │  DI resolve           │
└─────────────┘               └───────┬───────────────┘
                                      │
              ┌───────────────┬───────┴───────────────┐
              │               │                        │
     ┌────────▼──────┐ ┌──────▼──────┐  ┌────────────▼──────┐
     │  Dependency   │ │  Validation │  │    Encoding        │
     │  injection    │ │  Pydantic   │  │  JSON (CF=50)      │
     │  Depends()    │ │  v2 models  │  │  CBOR (CF=60)      │
     └───────────────┘ └─────────────┘  └───────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────┐
│              aiocoap UDP server                      │
│              coap://0.0.0.0:5683                     │
└──────────────────────────────────────────────────────┘
```

### Request lifecycle

```
CoAP UDP packet
      │
      ▼
aiocoap.Context  →  _WildcardSite  →  _RouteResource.render()
      │
      ▼
FastCOAP._dispatch()
  1. Wrap aiocoap.Message → CoapRequest
  2. Detect Content-Format (JSON or CBOR)
  3. Run middleware stack
  4. Router.find_route(method, path)  →  Route + path_params
  5. resolve_handler_kwargs()
       ├── resolve Depends() dependencies (cached)
       ├── extract + coerce path params
       ├── extract + coerce query params
       └── parse + validate body with Pydantic
  7. Normalise result → CoapResponse
  8. CoapResponse.to_message() → aiocoap.Message
      │
      ▼
CoAP UDP response
```

---

## Quick Start

### 1. Create a project with uv

```bash
uv init my-iot-api
cd my-iot-api
uv add aiocoap pydantic cbor2 typer rich anyio watchfiles
uv pip install -e .
```

### 2. Write your app

```python
# main.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pydantic import BaseModel
from fastcoap import FastCOAP, CoapResponse, Depends, Path, NotFound

class Sensor(BaseModel):
    name: str
    value: float

_db: dict[int, Sensor] = {}

@asynccontextmanager
async def lifespan(app: FastCOAP) -> AsyncGenerator[dict, None]:
    print("startup")
    yield {"db": _db}
    print("shutdown")

app = FastCOAP(title="Sensor API", lifespan=lifespan)

async def get_db() -> dict:
    return _db

@app.get("/sensors/{id}")
async def get_sensor(id: int = Path("id"), db: dict = Depends(get_db)):
    item = db.get(id)
    if not item:
        raise NotFound(f"Sensor {id} not found")
    return item.model_dump()

@app.post("/sensors/")
async def create_sensor(sensor: Sensor, db: dict = Depends(get_db)):
    db[len(db) + 1] = sensor
    return CoapResponse(content=sensor.model_dump(), status_code=201)
```

### 3. Run

```bash
fastcoap run main:app
fastcoap run main:app --reload          # auto-reload on file changes
fastcoap run main:app --host 0.0.0.0 --port 5683
```

### 4. Inspect routes

```bash
fastcoap routes main:app
```

---

## CLI Reference

```
fastcoap run MODULE:APP [OPTIONS]

  --host TEXT        Bind host            [default: 0.0.0.0]
  --port INTEGER     CoAP UDP port        [default: 5683]
  --reload           Auto-reload on file changes
  --log-level TEXT   Logging level        [default: info]

fastcoap routes MODULE:APP
  List all registered routes in a Rich table.
```

---

## Routing

### Path parameters

```python
@app.get("/devices/{device_id}/sensors/{sensor_id}")
async def get_sensor(
    device_id: int = Path("device_id"),
    sensor_id: str = Path("sensor_id"),
):
    ...
```

### Query parameters

```python
@app.get("/sensors/")
async def list_sensors(
    limit: int = Query("limit", default=20),
    unit: str = Query("unit", default="celsius"),
):
    ...
```

### Sub-routers

```python
from fastcoap import Router

sensors_router = Router(prefix="/sensors", tags=["sensors"])

@sensors_router.get("/")
async def list_sensors(): ...

@sensors_router.post("/")
async def create_sensor(): ...

app.include_router(sensors_router)
# or with an additional prefix:
app.include_router(sensors_router, prefix="/v2")
```

---

## Request Body & Validation

Annotate a handler parameter with a Pydantic model and FastCOAP automatically parses and validates the incoming payload — JSON or CBOR, whichever Content-Format the client sent.

```python
from pydantic import BaseModel, Field

class SensorReading(BaseModel):
    sensor_id: str = Field(..., min_length=1)
    temperature: float = Field(..., ge=-100, le=100)
    humidity: float = Field(..., ge=0, le=100)

@app.post("/sensors/")
async def create(reading: SensorReading):
    return CoapResponse(content=reading.model_dump(), status_code=201)
```

You can also use the explicit `Body()` descriptor:

```python
from fastcoap import Body

@app.put("/sensors/{id}")
async def update(
    id: int = Path("id"),
    reading: SensorReading = Body(model=SensorReading),
):
    ...
```

---

## Dependency Injection

`Depends()` works for both sync and async callables. Results are cached for the duration of a single request.

```python
from fastcoap import Depends

async def get_db():
    return _db

async def get_current_token(request: CoapRequest):
    token = request.query_params.get("token")
    if not token:
        raise Unauthorized("Missing token")
    return token

@app.get("/secure/")
async def secure_route(
    db: dict = Depends(get_db),
    token: str = Depends(get_current_token),
):
    ...
```

---

## Encodings

FastCOAP reads the CoAP `Content-Format` option on every incoming message and dispatches to the right codec automatically:

| Content-Format | Value | Codec |
|---|---|---|
| JSON | 50 | `json.loads` / `json.dumps` |
| CBOR | 60 | `cbor2.loads` / `cbor2.dumps` |

Responses default to JSON. To reply with CBOR:

```python
from fastcoap import CoapResponse, ContentFormat

@app.get("/data/")
async def get_data():
    return CoapResponse(
        content={"value": 42},
        content_format=ContentFormat.CBOR,
    )
```

---

## Lifespan

Two styles are supported — pick whichever feels natural.

### Context-manager style (recommended)

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastCOAP):
    # startup — runs before the server accepts connections
    db = await connect_db()
    yield {"db": db}          # dict is merged into app.state
    # shutdown — runs after the server stops
    await db.close()

app = FastCOAP(lifespan=lifespan)
```

### Hook style

```python
app = FastCOAP()

@app.on_startup
async def startup():
    app.state["db"] = await connect_db()

@app.on_shutdown
async def shutdown():
    await app.state["db"].close()
```

---

### Built-in exceptions

| Class | CoAP code |
|---|---|
| `BadRequest` | 4.00 |
| `Unauthorized` | 4.01 |
| `NotFound` | 4.04 |
| `MethodNotAllowed` | 4.05 |
| `InternalServerError` | 5.00 |

---

## Middleware

```python
from fastcoap import CoapRequest, CoapResponse

async def logging_middleware(request: CoapRequest, call_next):
    print(f"→ {request.method} {request.path}")
    response = await call_next(request)
    print(f"← {response.status_code}")
    return response

app.add_middleware(logging_middleware)
```

---


## Dependencies

| Package | Purpose |
|---|---|
| `aiocoap` | Async CoAP server and client |
| `pydantic >= 2.0` | Request body validation and serialisation |
| `cbor2` | CBOR encoding / decoding |
| `typer` | CLI (`fastcoap run`, `fastcoap routes`) |
| `rich` | Pretty terminal output |
| `anyio` | Async primitives |
| `watchfiles` | `--reload` file watcher |

---



