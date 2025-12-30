from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import asyncio
from datetime import datetime

from app.database import SessionLocal
from app.websocket import manager

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
    rows = db.execute(
        text("""
        SELECT t.*
        FROM node_data t
        JOIN (
            SELECT node, MAX(received_at) AS max_time
            FROM node_data
            GROUP BY node
        ) latest
        ON t.node = latest.node
        AND t.received_at = latest.max_time
        """)
    ).mappings().all()

    return {r["node"]: dict(r) for r in rows}


def fetch_active_incidents(db):
    rows = db.execute(
        text("""
        SELECT *
        FROM node_data
        WHERE flame = 1 OR smoke = 1
        """)
    ).mappings().all()

    return list(rows)

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
