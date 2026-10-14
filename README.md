# RippleGraph

> **See the ripple before you ship.**

RippleGraph is a graph-powered **Change Rehearsal Agent** — an automated pre-flight system that simulates the blast radius of a breaking API change across a microservice ecosystem before it reaches production.

Built for the **Graph Hacks: Context for AI Agents** hackathon, powered by FalkorDB.
**Tracks:** Track 1 (Agents That Act on Connected Data) · Track 2 (Agent Memory & Coordination)

---

## The Problem

In distributed architectures, engineers are **blind to transitive impact.** When `auth-service` renames a JWT field (`sub` → `subject_id`), the direct callers get notified — but `checkout-service`, which depends on `payment-service`, which depends on `auth-service`, silently breaks 3 hops downstream.

Static linters, OpenAPI specs, and vector databases cannot discover this. Multi-hop relational joins are too slow. Code review cannot hold 100 services in a human mind.

## The Solution

RippleGraph agents traverse the live service dependency graph in FalkorDB to:

1. **Discover the full blast radius** — not just direct callers, but every transitive downstream service.
2. **Evaluate contract compatibility** — deterministic claim diffing (`sub` vs `subject_id`) before any LLM reasoning.
3. **Surface historical precedent** — past incidents tied to the same services and claim types, with automated **Red Herring rejection** for irrelevant incidents.
4. **Persist structured findings** — agent memory as typed `(:Finding)` graph nodes, not lossy transcripts.
5. **Learn across investigations** — Investigation B recalls Investigation A's findings with mathematical confidence decay.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         3-Panel React Flow UI (Vite + TS)                   │
│  [Left: Controls & History]  [Center: Live Graph Canvas]  [Right: Findings] │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ REST + SSE
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                          FastAPI Backend (Python 3.12)                      │
│   Stage 1: Investigator → Stage 2: Memory → Stage 3: Reviewer → Stage 4: Persist │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ falkordb-py
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                  FalkorDB  ·  10 Services  ·  6 Incidents  ·  3 Contracts   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Graph Database | FalkorDB (falkordb-py) |
| Backend | Python 3.12 · FastAPI · Uvicorn |
| Frontend | React 18 · TypeScript · Vite · React Flow |
| Styling | Vanilla CSS — Linear/Vercel Dark Design System |
| Orchestration | Docker Compose |
| Query Language | Cypher |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 22+

### 1. Start FalkorDB + Backend

```bash
docker compose up -d falkordb
pip install -r backend/requirements.txt
python backend/graph/seed.py
uvicorn backend.main:app --reload --port 8000
```

### 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

### 3. Reset & Re-seed

```bash
curl -X POST http://localhost:8000/api/seed/reset
```

---

## Project Structure

```
RippleGraph/
├── docker-compose.yml
├── README.md
├── plan/                          # Pre-hackathon architecture docs
├── backend/
│   ├── main.py                    # FastAPI app & API routes
│   ├── config.py                  # Environment configuration
│   ├── graph/
│   │   ├── client.py              # FalkorDB connection singleton
│   │   ├── seed.py                # Seed 10-service synthetic ecosystem
│   │   ├── tools.py               # 6 deterministic Cypher graph tools
│   │   └── queries.py             # Parameterized Cypher strings
│   ├── orchestrator/
│   │   ├── pipeline.py            # 4-stage pipeline coordinator + SSE
│   │   ├── investigator.py        # Stage 1: Blast radius discovery
│   │   ├── memory.py              # Stage 2: Cross-run finding retrieval
│   │   ├── reviewer.py            # Stage 3: Adversarial audit + red-herring filter
│   │   └── persist.py             # Stage 4: Graph persistence of findings
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   └── tests/
│       ├── test_seed.py           # 8-point graph verification
│       └── test_pipeline.py       # End-to-end integration tests
└── frontend/
    ├── src/
    │   ├── index.css              # Linear dark design tokens
    │   ├── App.tsx                # 3-panel layout root
    │   ├── api/                   # REST + SSE client
    │   └── components/
    │       ├── LeftPanel.tsx
    │       ├── CenterGraph.tsx
    │       ├── ServiceNode.tsx
    │       ├── RightPanel.tsx
    │       ├── EvidenceModal.tsx
    │       └── ProofModeBanner.tsx
    └── vite.config.ts
```

---

## Key Graph Model

```cypher
// Direct consumers of the Auth API
MATCH (s:Service)-[:ACCEPTS_CONTRACT]->(cv:ContractVersion)<-[:HAS_CONTRACT]-(a:API {id: 'auth-token-api'})
RETURN s, cv

// Full downstream blast radius (4-hop max)
MATCH path = (ds:Service)-[:DEPENDS_ON*1..4]->(provider:Service {id: 'auth-service'})
RETURN path, length(path) AS depth ORDER BY depth

// Retrieve prior findings with evidence
MATCH (inv:Investigation)-[:PRODUCED]->(f:Finding)-[:ABOUT_SERVICE]->(s:Service)
WHERE s.id IN $service_ids
OPTIONAL MATCH (f)-[:SUPPORTED_BY]->(i:Incident)
OPTIONAL MATCH (f)-[:RECOMMENDS]->(m:Mitigation)
RETURN f, s, i, m, inv ORDER BY inv.created_at DESC
```

---

## Proof: Why FalkorDB is Not Decorative

Enable **Proof Mode** in the UI. With FalkorDB disabled:
- Multi-hop downstream service discovery drops from **7 services → 0**
- Cross-investigation memory retrieval: **< 10ms → broken**
- Contract compatibility evaluation: **deterministic → undefined**

---

## AI Usage Disclosure

This project uses AI coding assistance (Antigravity IDE). All architecture decisions, Cypher queries, graph schema, and business logic have been designed, verified, and tested by the participant. AI was used to accelerate implementation of settled design decisions.

---

*Built with ❤️ for Graph Hacks 2026 · FalkorDB · WeMakeDevs*
