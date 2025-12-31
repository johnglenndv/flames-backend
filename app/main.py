import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from datetime import datetime
from passlib.context import CryptContext
from app.models import User

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas import TelemetryIn, UserSignup, UserLogin
from app.state import nodes, incidents
from app.websocket import manager

from app.database import SessionLocal, get_db
from app.models import Telemetry
from app.schemas import TelemetryIn


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="F.L.A.M.E.S Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://flames-testing.vercel.app",
        "https://flames-backend-hbu0.onrender.com",
        "http://localhost",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------
# Health Check
# -------------------------
@app.get("/")
def root():
    return {"status": "backend running"}


# -------------------------
# WebSocket
# -------------------------
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep connection open forever
        await asyncio.Future()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# -------------------------
# Sensor Ingest
# -------------------------
@app.post("/ingest")
async def ingest(data: TelemetryIn):
    db = SessionLocal()

    row = Telemetry(
        node=data.node,
        session=data.session,
        seq=data.seq,
        temp=data.temp,
        hum=data.hum,
        lat=data.lat,
        lon=data.lon,
        flame=data.flame,
        smoke=data.smoke,
        gateway=data.gateway,
        rssi=data.rssi,
        snr=data.snr,
        received_at=data.received_at
    )

    db.add(row)
    db.commit()
    db.close()

    # Fire detection
    if data.flame == 1 or (data.temp and data.temp >= 60) or (data.smoke and data.smoke >= 300):
        incident = {
            "node": data.node,
            "severity": "HIGH",
            "timestamp": data.received_at.isoformat()
        }

        await manager.broadcast({
            "type": "incident",
            "data": incident
        })

    # ✅ JSON-SAFE NODE UPDATE
    payload = data.model_dump()
    payload["received_at"] = payload["received_at"].isoformat()

    await manager.broadcast({
        "type": "node_update",
        "data": payload
    })
    
    print("CLIENTS COUNT:", len(manager.clients))


    return {"status": "stored"}




# -------------------------
# Dashboard APIs
# -------------------------
@app.get("/nodes")
def get_nodes():
    db = SessionLocal()

    rows = (
        db.query(Telemetry)
        .order_by(Telemetry.received_at.desc())
        .all()
    )

    db.close()

    latest = {}
    for r in rows:
        if r.node not in latest:
            latest[r.node] = {
                "node": r.node,
                "lat": r.lat,
                "lon": r.lon,
                "temp": r.temp,
                "hum": r.hum,
                "smoke": r.smoke,
                "flame": bool(r.flame),
                "received_at": r.received_at
            }

    return latest


@app.get("/nodes/{node_id}")
def get_node(node_id: str):
    db = SessionLocal()

    row = (
        db.query(Telemetry)
        .filter(Telemetry.node == node_id)
        .order_by(Telemetry.received_at.desc())
        .first()
    )

    db.close()

    if not row:
        return []

    return {
        "node": row.node,
        "lat": row.lat,
        "lon": row.lon,
        "temp": row.temp,
        "hum": row.hum,
        "smoke": row.smoke,
        "flame": bool(row.flame),
        "received_at": row.received_at
    }



@app.get("/incidents")
def get_incidents():
    db = SessionLocal()

    rows = (
        db.query(Telemetry)
        .filter(
            (Telemetry.flame == 1) |
            (Telemetry.temp >= 60) |
            (Telemetry.smoke >= 300)
        )
        .order_by(Telemetry.received_at.desc())
        .limit(20)
        .all()
    )

    db.close()

    incidents = []
    seen_nodes = set()

    for r in rows:
        if r.node not in seen_nodes:
            incidents.append({
                "node": r.node,
                "severity": "HIGH",
                "lat": r.lat,
                "lon": r.lon,
                "timestamp": r.received_at
            })
            seen_nodes.add(r.node)

    return incidents



# -------------------------
# Authentication APIs
# -------------------------
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
    if not db_user:
        db.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    password = user.password.encode("utf-8")[:72].decode("utf-8")

    if not pwd_context.verify(password, db_user.password_hash):
        db.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    db.close()

    return {
        "message": "Login successful",
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "organization": db_user.organization
        }
    }


# latest update
@app.get("/nodes/latest")
def get_latest_nodes(db: Session = Depends(get_db)):
    query = text("""
        SELECT t.*
        FROM telemetry t
        JOIN (
            SELECT node, MAX(received_at) AS max_time
            FROM telemetry
            GROUP BY node
        ) latest
        ON t.node = latest.node
        AND t.received_at = latest.max_time
        ORDER BY t.node
    """)

    rows = db.execute(query).mappings().all()

    nodes = []
    for r in rows:
        nodes.append({
            "node": r["node"],
            "lat": r["lat"],
            "lon": r["lon"],
            "temp": r["temp"],
            "hum": r["hum"],
            "smoke": r["smoke"],
            "flame": bool(r["flame"]),
            "received_at": r["received_at"].isoformat()
        })

    return nodes


