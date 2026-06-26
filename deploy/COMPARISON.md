# EC2 vs ECS — Side-by-Side Deployment Comparison

## Architecture Diagrams

### EC2 (Single Instance)
```
Browser
   │
   ▼
EC2 t3.medium
┌─────────────────────────────────────────┐
│  Nginx :80                              │
│    ├── /          → frontend/dist/      │  ← React static files on disk
│    ├── /api/      → FastAPI :8000       │
│    └── /ws/       → FastAPI :8000       │
│                                         │
│  FastAPI (uvicorn, 1 worker)            │
│    ├── SQLite  (sahayak.db)             │  ← App DB on disk
│    ├── SQLite  (checkpoints.db)         │  ← LangGraph state on disk
│    ├── ChromaDB (chroma_db/)            │  ← Vector index on disk
│    └── In-memory WS dict               │  ← WebSocket connections in RAM
└─────────────────────────────────────────┘
```

### ECS (Fargate, horizontally scalable)
```
Browser
   │
   ▼
CloudFront ──→ S3 (React static files)
   │
   ▼
ALB (Application Load Balancer)
   │         │
   ▼         ▼
Fargate    Fargate          ← N tasks, auto-scaled
Task A     Task B
  │           │
  └─────┬─────┘
        │
        ├──→ RDS Postgres    ← App DB + LangGraph checkpoints
        ├──→ ElastiCache Redis ← WebSocket pub/sub
        └──→ EFS Volume      ← ChromaDB vector index
```

---

## The Three State Dependencies That Drive Everything

This is the core teaching point. The current codebase has three pieces of state that are
local to the process. Moving to ECS means each one must become an external shared resource.

| State | EC2 | ECS | File that changes |
|---|---|---|---|
| App DB (tickets, audit logs) | `sahayak.db` on disk | RDS Postgres | `config.py` — one env var |
| LangGraph checkpoints | `checkpoints.db` on disk | RDS Postgres (same instance) | `main.py` — SqliteSaver → AsyncPostgresSaver |
| WebSocket connections | In-memory Python dict | ElastiCache Redis pub/sub | `api/ws.py` — full rewrite |
| Vector index (ChromaDB) | `chroma_db/` on disk | EFS volume mount | `config.py` + task definition |
| React frontend | Served by Nginx from disk | S3 + CloudFront | Infrastructure only |

---

## Code Diffs: What Actually Changes

### 1. LangGraph Checkpointer (`main.py`)

**EC2:**
```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
graph = build_graph(checkpointer)
```

**ECS:**
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async with AsyncPostgresSaver.from_conn_string(settings.postgres_url) as checkpointer:
    await checkpointer.setup()
    graph = build_graph(checkpointer)
```

**What changed:** 3 lines. The graph, nodes, pipeline — untouched.
**Why it matters:** With SqliteSaver, Task A pauses a thread. Task B gets the resume request.
Task B has never seen that checkpoint. 404. With PostgresSaver, both tasks hit the same RDS.

---

### 2. WebSocket Manager (`api/ws.py`)

**EC2:**
```python
class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}  # lives in THIS process only

    async def broadcast(self, event: dict):
        for ws in self._connections.values():
            await ws.send_json(event)
```

**ECS:**
```python
class RedisConnectionManager:
    async def broadcast(self, event: dict):
        # Publish to Redis channel — every Fargate task receives it
        await self._redis.publish("sahayak:events", json.dumps(event))

    async def run_subscriber(self):
        # Background task: forward Redis messages to local WebSocket connections
        pubsub = self._redis.pubsub()
        await pubsub.subscribe("sahayak:events")
        async for message in pubsub.listen():
            await self._forward_to_local(json.loads(message["data"]))
```

**What changed:** The `broadcast` call now goes through Redis instead of a local dict.
**Why it matters:** Without this, 50% of `review_ready` events are silently dropped
(whenever the pipeline runs on a different task than the one the browser is connected to).

---

### 3. Config (`config.py`)

**EC2:**
```python
database_url: str = "sqlite:///./sahayak.db"
graph_checkpoint_db: str = "./checkpoints.db"
chroma_persist_dir: str = "./chroma_db"
```

**ECS:**
```python
postgres_url: str                              # replaces both SQLite vars
redis_url: str                                 # new
chroma_persist_dir: str = "/mnt/efs/chroma_db" # EFS mount path
```

**What changed:** 2 vars removed, 2 added. Everything else identical.

---

## Cost Comparison

| Resource | EC2 | ECS |
|---|---|---|
| Compute | t3.medium ~$30/mo | 2x Fargate 1vCPU/2GB ~$60/mo |
| Database | Included (SQLite) | RDS db.t3.micro Postgres ~$15/mo |
| Cache | Included (in-memory) | ElastiCache cache.t3.micro ~$15/mo |
| File storage | Included (EBS) | EFS ~$0.30/GB/mo |
| Frontend CDN | Included (Nginx) | S3 + CloudFront ~$1-5/mo |
| **Total (est.)** | **~$30/mo** | **~$95/mo** |
| **Ops overhead** | SSH + manual deploy | CI/CD rolling deploy |
| **Scales to N users** | No | Yes |
| **Zero-downtime deploy** | No | Yes (rolling update) |

---

## Decision Framework: Which to Use When

```
Is this a demo / workshop / prototype?
    └── YES → EC2. Zero infra overhead. Make seed once. Works in 20 minutes.

Is this serving real users?
    └── How many concurrent support agents?
        ├── 1-3 agents, no HA needed → EC2 + daily snapshots
        └── 4+ agents or need zero-downtime deploys → ECS
            └── Add RDS, ElastiCache, EFS
            └── 3 file changes in the codebase (config, main, ws)
```

---

## What Stays Identical Between EC2 and ECS

Everything else in the project. The LangGraph pipeline, all three nodes, the HITL
mechanism, the React dashboard, the SOP documents, the mock OMS tools — none of it
changes. The deployment target is purely an infrastructure concern, not an application
architecture concern. This is the value of designing stateless application logic from
the start.
