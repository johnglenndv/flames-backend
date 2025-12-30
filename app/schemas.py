from pydantic import BaseModel
from datetime import datetime


class TelemetryIn(BaseModel):
    node: str
    session: int | None = None
    seq: int | None = None

    temp: float | None = None
    hum: float | None = None

    lat: float | None = None
    lon: float | None = None

    flame: int | None = None
    smoke: int | None = None

    gateway: str | None = None
    rssi: int | None = None
    snr: float | None = None

    received_at: datetime

class UserSignup(BaseModel):
    username: str
    password: str
    organization: str

class UserLogin(BaseModel):
    username: str
    password: str