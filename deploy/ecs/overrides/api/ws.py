"""
ECS WebSocket Manager — Redis Pub/Sub

WHY THIS FILE EXISTS (diff from EC2 ws.py):

EC2 runs one process. The in-memory dict works perfectly:
    _connections: Dict[str, WebSocket]  ← all connections live here

ECS runs N Fargate tasks behind an ALB. Browser connects to Task A.
Pipeline fires on Task B. Task B calls manager.broadcast() — but Task B's
_connections dict is EMPTY for this browser. Event is silently dropped.
The dashboard never lights up.

FIX: Replace the in-memory dict with Redis pub/sub.
  - Any task publishes events to a Redis channel.
  - Every task subscribes and forwards to its own local WebSocket connections.
  - Now it doesn't matter which task the pipeline ran on.

TRADEOFF:
  Pro: Horizontal scaling works. N tasks, all get the event.
  Con: Adds ElastiCache dependency (~$15-50/month for cache.t3.micro).
       Adds complexity: a background asyncio subscriber task must run per process.
       publish/subscribe adds ~1ms latency vs. direct in-memory call.
"""

import json
import asyncio
from typing import Dict
from fastapi import WebSocket
import redis.asyncio as aioredis
from backend.config import settings  # uses ECS config

CHANNEL = "sahayak:events"


class RedisConnectionManager:
    def __init__(self):
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        # Local connections on THIS task only
        self._local_connections: Dict[str, WebSocket] = {}

    async def connect(self, connection_id: str, websocket: WebSocket):
        await websocket.accept()
        self._local_connections[connection_id] = websocket

    def disconnect(self, connection_id: str):
        self._local_connections.pop(connection_id, None)

    async def send_event(self, event: dict):
        """
        Publish to Redis. Every task (including this one) will receive it
        via the subscriber loop and forward to its local WebSocket connections.
        """
        await self._redis.publish(CHANNEL, json.dumps(event))

    # Alias kept for API compatibility with EC2 version
    async def broadcast(self, event: dict):
        await self.send_event(event)

    async def _forward_to_local(self, event: dict):
        """Called by the subscriber loop — send to every connection on THIS task."""
        dead = []
        for conn_id, ws in self._local_connections.items():
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(conn_id)
        for d in dead:
            self.disconnect(d)

    async def run_subscriber(self):
        """
        Background task: subscribe to Redis channel and forward events locally.
        Started once at app startup in main.py lifespan.
        Each Fargate task runs its own copy of this loop.
        """
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    await self._forward_to_local(event)
                except Exception:
                    pass


manager = RedisConnectionManager()
