"""
FastCOAP example app.

    fastcoap run examples.main:app --reload
    fastcoap routes examples.main:app
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from pydantic import BaseModel, Field

from fastcoap import (
    FastCOAP,
    Router,
    CoapRequest,
    CoapResponse,
    Path,
    Query,
    Body,
    Depends,
    NotFound,
    BadRequest,
)


class SensorReading(BaseModel):
    sensor_id: str = Field(..., description="Unique sensor identifier")
    temperature: float = Field(..., ge=-100, le=100)
    humidity: float = Field(..., ge=0, le=100)
    unit: str = Field(default="celsius")


class SensorReadingOut(SensorReading):
    id: int


_DB: dict[int, SensorReadingOut] = {
    1: SensorReadingOut(id=1, sensor_id="s-001", temperature=22.5, humidity=55.0),
    2: SensorReadingOut(id=2, sensor_id="s-002", temperature=18.0, humidity=70.0),
}
_counter = 3


@asynccontextmanager
async def lifespan(app: FastCOAP) -> AsyncGenerator[dict, None]:
    print("🚀  FastCOAP starting…")
    app.state["sensor_count"] = len(_DB)
    yield {"db": _DB}
    print("🛑  FastCOAP shutting down.")


async def get_db() -> dict:
    return _DB


sensors_router = Router(prefix="/sensors", tags=["sensors"])


@sensors_router.get("/", summary="List all sensors")
async def list_sensors(
    db: dict = Depends(get_db),
    limit: Optional[int] = Query("limit", default=10),
):
    items = list(db.values())[:limit]
    return CoapResponse(content=[i.model_dump() for i in items])


@sensors_router.get("/{sensor_id}", summary="Get a sensor by ID")
async def get_sensor(
    sensor_id: int = Path("sensor_id"),
    db: dict = Depends(get_db),
):
    item = db.get(sensor_id)
    if not item:
        raise NotFound(f"Sensor {sensor_id} not found")
    return item.model_dump()


@sensors_router.post("/", summary="Create sensor reading")
async def create_sensor(
    reading: SensorReading,
    db: dict = Depends(get_db),
):
    global _counter
    out = SensorReadingOut(id=_counter, **reading.model_dump())
    db[_counter] = out
    _counter += 1
    return CoapResponse(content=out.model_dump(), status_code=201)


@sensors_router.put("/{sensor_id}", summary="Update a sensor reading")
async def update_sensor(
    sensor_id: int = Path("sensor_id"),
    reading: SensorReading = Body(model=SensorReading),
    db: dict = Depends(get_db),
):
    if sensor_id not in db:
        raise NotFound(f"Sensor {sensor_id} not found")
    db[sensor_id] = SensorReadingOut(id=sensor_id, **reading.model_dump())
    return CoapResponse(content=db[sensor_id].model_dump())


@sensors_router.delete("/{sensor_id}", summary="Delete a sensor reading")
async def delete_sensor(
    sensor_id: int = Path("sensor_id"),
    db: dict = Depends(get_db),
):
    if sensor_id not in db:
        raise NotFound(f"Sensor {sensor_id} not found")
    del db[sensor_id]
    return CoapResponse(status_code=204)


app = FastCOAP(
    title="IoT Sensor API",
    version="1.0.0",
    description="CoAP-native IoT API with JSON & CBOR support",
    lifespan=lifespan,
)

app.include_router(sensors_router)


@app.get("/", tags=["system"])
async def root():
    return {"status": "ok", "framework": "FastCOAP", "protocol": "CoAP"}
