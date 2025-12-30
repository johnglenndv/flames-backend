from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, func
import asyncio
from datetime import datetime

from app.database import SessionLocal
from app.websocket import manager

from app.models import Telemetry

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
            Telemetry.node,
            func.max(Telemetry.received_at).label("max_time")
        )
        .group_by(Telemetry.node)
        .subquery()
    )

    rows = (
        db.query(Telemetry)
        .join(
            subq,
            (Telemetry.node == subq.c.node) &
            (Telemetry.received_at == subq.c.max_time)
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
        db.query(Telemetry)
        .filter((Telemetry.flame == True) | (Telemetry.smoke == True))
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
<<<<<<< HEAD
@app.on_event("startup")
async def startup():
    asyncio.create_task(periodic_broadcast())
=======
@app.post("/auth/signup")
def signup(user: UserSignup):
    db = SessionLocal()

    # check duplicate username
    if db.query(User).filter(User.username == user.username).first():
        db.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    password = user.password.encode("utf-8")[:72].decode("utf-8")
    hashed = pwd_context.hash(password)


    new_user = User(
        username=user.username,
        organization=user.organization,
        password_hash=hashed
    )

    db.add(new_user)
    db.commit()
    db.close()

    return {"message": "User registered successfully"}


@app.post("/auth/login")
def login(user: UserLogin):
    db = SessionLocal()

    db_user = db.query(User).filter(User.username == user.username).first()
    db.close()
    
    password = password.encode("utf-8")[:72].decode("utf-8")

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "message": "Login successful",
        "username": db_user.username,
        "organization": db_user.organization
    }

>>>>>>> parent of 2e73fe4 (Update main.py)
