# Sahayak AI — HITL Agent Assist Platform

Flipkart-inspired production replica. AI handles cognitive work (intent parsing, SOP retrieval, OMS querying). Human agent is the final gatekeeper.

## Quickstart

```bash
# 1. Copy env and add your Anthropic key
cp .env.example .env

# 2. Install dependencies
make install

# 3. Index SOP documents into ChromaDB (run once)
make seed

# 4. Start backend (new terminal)
make backend

# 5. Start frontend (new terminal)
make frontend
```

Dashboard: http://localhost:5173  
API docs: http://localhost:8000/docs

## Submitting a test ticket

```bash
curl -X POST http://localhost:8000/api/tickets/ingest \
  -H "Content-Type: application/json" \
  -d @data/mock_tickets.json | python -m json.tool
```

Or submit a single ticket:

```bash
curl -X POST http://localhost:8000/api/tickets/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-001",
    "customer_name": "Priya Sharma",
    "customer_email": "priya@example.com",
    "customer_id": "CUST-4821",
    "order_id": "ORD-78234",
    "raw_text": "My TV was marked delivered but I never received it. I want a full refund immediately.",
    "channel": "email"
  }'
```

## Architecture

```
intent_parser (Haiku) → rag_retriever (Sonnet) → tool_matcher (Sonnet)
                                                          ↓
                                              ⛔ HITL BREAKPOINT
                                                          ↓
                                              Human reviews workspace
                                                          ↓
                                              execute_action (resumes)
```

## Key design decisions

| Decision | Tradeoff |
|---|---|
| `interrupt_before` not `interrupt_after` | Graph pauses before any mutation — zero blast radius if model hallucinates |
| SqliteSaver for checkpoints | Dev-friendly; swap one line for PostgresSaver in prod |
| Haiku for Node 1, Sonnet for Nodes 2-3 | ~60-70% LLM cost reduction; classification ≠ reasoning |
| Local embeddings (all-MiniLM) | No extra API key; good enough for small SOP corpus |
| Agentic RAG retry on confidence < 0.7 | Adds 1-2 calls in ~30% of cases; prevents wrong policy citations |
| Read-only OMS tools | Agent can never write to OMS; writes only via approved executor |
| Single WS channel | Simple for demo; use Redis pub/sub for multi-server prod |
