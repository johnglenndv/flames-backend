from fastapi import WebSocket
from typing import List, Dict
import asyncio

class WebSocketManager:
    def __init__(self):
        self.clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, message: Dict):
        dead_clients = []

        for client in self.clients:
            try:
                await client.send_json(message)
            except Exception:
                dead_clients.append(client)

        # Cleanup dead connections
        for dc in dead_clients:
            self.disconnect(dc)

manager = WebSocketManager()
