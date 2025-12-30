from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from datetime import datetime
from passlib.context import CryptContext

from app.schemas import NodeData, UserSignup, UserLogin
from app.state import nodes, incidents
from app.websocket import manager

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="F.L.A.M.E.S Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
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
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# -------------------------
# Sensor Ingest
# -------------------------
@app.post("/ingest")
async def ingest_data(data: NodeData):
    nodes[data.node_id] = data.dict()

    fire_detected = (
        data.flame
        or data.temperature >= 60
        or data.smoke >= 300
    )

    if fire_detected:
        incident = {
            "node_id": data.node_id,
            "severity": "HIGH",
            "timestamp": datetime.utcnow().isoformat()
        }
        incidents.append(incident)

        await manager.broadcast({
            "type": "incident",
            "data": incident
        })

    await manager.broadcast({
        "type": "node_update",
        "data": data.dict()
    })

    return {"status": "ok"}


# -------------------------
# Dashboard APIs
# -------------------------
@app.get("/nodes")
def get_nodes():
    return nodes


@app.get("/nodes/{node_id}")
def get_node(node_id: str):
    return nodes.get(node_id)


@app.get("/incidents")
def get_incidents():
    return incidents


# -------------------------
# Authentication APIs
# -------------------------
@app.post("/auth/signup")
def signup(user: UserSignup):
    hashed = pwd_context.hash(user.password)
    # TODO: store in MySQL
    return {"message": "User registered"}


@app.post("/auth/login")
def login(user: UserLogin):
    # TODO: verify from MySQL
    return {"message": "Login successful"}
