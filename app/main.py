from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.websocket import manager
from app.schemas import NodeData
from app.state import nodes, incidents
from datetime import datetime

app = FastAPI(title="F.L.A.M.E.S Backend")

# -------------------------
# WebSocket (Real-Time)
# -------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(ws)

# -------------------------
# Receive Node Data (MQTT → HTTP hook)
# -------------------------
@app.post("/ingest")
async def ingest_data(data: NodeData):
    nodes[data.node_id] = data

    # Fire detection logic
    if data.flame or data.smoke > 300 or data.temperature > 60:
        incident = {
            "node_id": data.node_id,
            "location": "UNKNOWN",
            "severity": "HIGH",
            "timestamp": datetime.utcnow().isoformat()
        }
        incidents.append(incident)

        await manager.broadcast({
            "type": "incident",
            "data": incident
        })

    # Broadcast node update
    await manager.broadcast({
        "type": "node_update",
        "data": data.dict()
    })

    return {"status": "ok"}

# -------------------------
# REST APIs (Initial Load)
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
