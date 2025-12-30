from pydantic import BaseModel
from datetime import datetime

class NodeData(BaseModel):
    node_id: str
    lat: float
    lng: float
    temperature: float
    humidity: float
    smoke: float
    flame: bool
    timestamp: datetime

class Incident(BaseModel):
    node_id: str
    location: str
    severity: str
    timestamp: datetime
