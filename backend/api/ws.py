"""
WebSocket Connection Manager

DESIGN DECISION: In-memory connection map vs. Redis pub/sub.

For the demo: in-memory dict is fine. One server process, < 10 concurrent agents.

For production: When you have multiple server instances behind a load balancer,
WebSocket connections land on different servers. An in-memory map on Server A
won't know about connections on Server B. Redis pub/sub solves this — every server
subscribes to the same channel and broadcasts to its local connections.

The API is identical either way; only this file changes.
"""

from fastapi import WebSocket
from typing import Dict


class ConnectionManager:
    def __init__(self):
        # ticket_id → WebSocket connection
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, ticket_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[ticket_id] = websocket

    def disconnect(self, ticket_id: str):
        self._connections.pop(ticket_id, None)

    async def send_event(self, ticket_id: str, event: dict):
        """Push a JSON event to the dashboard watching this ticket."""
        ws = self._connections.get(ticket_id)
        if ws:
            try:
                await ws.send_json(event)
            except Exception:
                self.disconnect(ticket_id)

    async def broadcast(self, event: dict):
        """Send an event to ALL connected agents (e.g., new ticket arrived)."""
        dead = []
        for ticket_id, ws in self._connections.items():
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ticket_id)
        for d in dead:
            self.disconnect(d)


manager = ConnectionManager()
