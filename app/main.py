from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, func
import asyncio
from datetime import datetime

from app.database import SessionLocal
from app.websocket import manager

from app.models import Node

app = FastAPI()

# -------------------------
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# DB helpers
# -------------------------
def fetch_latest_nodes(db):
    subq = (
        db.query(
            Node.node,
            func.max(Node.received_at).label("max_time")
        )
        .group_by(Node.node)
        .subquery()
    )

    rows = (
        db.query(Node)
        .join(
            subq,
            (Node.node == subq.c.node) &
            (Node.received_at == subq.c.max_time)
        )
        .all()
    )

    return {
        r.node: {
            "node": r.node,
            "lat": r.lat,
            "lon": r.lon,
            "temp": r.temp,
            "hum": r.hum,
            "smoke": r.smoke,
            "flame": r.flame,
            "received_at": r.received_at.isoformat(),
        }
        for r in rows
    }


def fetch_active_incidents(db):
    rows = (
        db.query(Node)
        .filter((Node.flame == True) | (Node.smoke == True))
        .all()
    )

    return [
        {
            "node": r.node,
            "flame": r.flame,
            "smoke": r.smoke,
            "received_at": r.received_at.isoformat(),
        }
        for r in rows
    ]

# -------------------------
# WebSocket endpoint
# -------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # keep connection alive
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(ws)

# -------------------------
# Background broadcaster
# -------------------------
async def periodic_broadcast():
    while True:
        db = SessionLocal()
        try:
            nodes = fetch_latest_nodes(db)
            incidents = fetch_active_incidents(db)

            payload = {
                "type": "snapshot",
                "data": {
                    "nodes": nodes,
                    "incidents": incidents,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

            await manager.broadcast(payload)

        except Exception as e:
            print("Broadcast error:", e)

        finally:
            db.close()

        await asyncio.sleep(2)  # REALTIME interval

# -------------------------
# Startup
# -------------------------
@app.on_event("startup")
async def startup():
    asyncio.create_task(periodic_broadcast())
