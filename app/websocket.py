from fastapi import WebSocket
from typing import Dict, List

class WebSocketManager:
    def __init__(self):
        self.clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.remove(ws)

    async def broadcast(self, message: Dict):
        for client in self.clients:
            await client.send_json(message)

manager = WebSocketManager()
