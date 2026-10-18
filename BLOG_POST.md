# How We Built RippleGraph: A Graph-Powered Change Rehearsal Agent for Microservices

*Taming cascading microservice outages with FalkorDB, Multi-Agent Coordination, and Episodic Memory.*

---

![RippleGraph Interface](https://raw.githubusercontent.com/bhavesh-018/RippleGraph/main/assets/ripplegraph_ui.jpg)

## The 3:00 AM Microservice Nightmare

Imagine this: An engineer on the Auth team renames a JWT claim in their token generation service. A simple rename—`sub` becomes `subject_id`, and `roles` becomes `scopes`. It passes all unit tests, passes linting, and is approved.

Thirty minutes after deploying to production, pagers fire across five different teams:
- The **Payment Service** can no longer verify checkout tokens.
- The **Order Service** queues backlog and drops requests.
- The **Analytics Service** starts dropping audit events because the header schema doesn't match.

In modern distributed microservice ecosystems, **an API change in Service A triggers silent, catastrophic ripples across Services B, C, and D.**

When engineering teams ask today’s AI coding assistants to evaluate the risk of an architectural change, the LLMs suffer from **"Topological Blindness."** They hallucinate dependencies that don't exist, miss transitive downstream consumers three hops away, and have zero episodic memory of past outages.

To solve this, we built **RippleGraph**—a Graph-Powered Change Rehearsal Agent built for **WeMakeDevs x FalkorDB Graph Hacks 2026** (competing in **Track 01: Agents That Act on Connected Data** and **Track 02: Agent Memory and Coordination**).

---

## What is RippleGraph?

RippleGraph is an automated change rehearsal agent. Before any code or API contract change hits staging, RippleGraph runs a 4-stage rehearsal:

1. **Stage 1 (Investigator):** Traverses the live microservice topology to determine the exact multi-hop blast radius with deterministic graph proof paths.
2. **Stage 2 (Memory Recall):** Queries graph-persisted episodic memory to retrieve relevant past incidents and mitigations, scored with temporal decay.
3. **Stage 3 (Reviewer):** Synthesizes graph facts with LLM reasoning to evaluate risk and identify contract breakage points.
4. **Stage 4 (Persist & Action):** Emits a structured, 4-phase rollout checklist and commits the rehearsal outcome back to FalkorDB as new episodic memory.

---

## Why Vector Search Fails and Why We Needed FalkorDB

Most modern AI agent memory architectures rely on vector databases and RAG (Retrieval-Augmented Generation). But microservice architectures are inherently **graphs**, not isolated chunks of text:

- `Service A` **DEPENDS_ON** `Service B`
- `Service B` **PROVIDES_API** `Endpoint X`
- `Endpoint X` **HAS_VERSION** `Contract v1`
- `Incident INC-101` **AFFECTED_SERVICE** `Service C`
- `Mitigation M-101` **RESOLVED** `Incident INC-101`

Vector similarity cannot tell you that Service D depends on Service A *through* Service B.

### Enter FalkorDB: Ultra-Fast Graph Traversals with GraphBLAS

FalkorDB gave us the exact superpowers we needed:

#### 1. Deterministic Multi-Hop Blast Radius (Sub-Millisecond Cypher)
To find all services affected by an Auth Service change up to 4 hops away:

```cypher
MATCH path = (origin:Service {id: $service_id})<-[:DEPENDS_ON*1..4]-(consumer:Service)
RETURN consumer.id, consumer.name, consumer.tier, length(path) AS hops
ORDER BY hops ASC
```

Powered by FalkorDB's GraphBLAS sparse matrix engine, deep path traversals return in **under 2 milliseconds**.

#### 2. Episodic Memory with Temporal Decay (Track 02)
Instead of stuffing unbounded text into context windows, previous rehearsal outcomes and real incidents are stored as `:InvestigationMemory` and `:IncidentRecord` nodes.

FalkorDB dynamically scores memory relevance using exponential temporal decay:

$$\text{Relevance} = \text{BaseScore} \times e^{-0.05 \cdot \Delta t}$$

When rehearsing a token rename, RippleGraph surfaces a high-confidence match from 14 days ago where an unversioned token broke the Payment gateway, warning the engineer *before* they push code.

---

## The "Money Shot": Proof Mode

A core requirement of the Graph Hacks Hackathon is **Rule 3**: proving that the graph is truly doing the work, not just acting as decorative storage for an LLM prompt.

We built a live **Proof Mode Toggle** directly into the RippleGraph UI:

| Feature | 🔴 FalkorDB Disconnected (Proof Mode) | 🟢 FalkorDB Connected (Live Engine) |
|---|---|---|
| **Blast Radius** | Hallucinated / Incomplete (misses 3rd-hop downstream services) | **Deterministic 5-service blast radius** with verified Cypher paths |
| **Evidence** | Zero verifiable graph paths | **Clickable multi-hop path proofs** (`auth` $\to$ `session` $\to$ `checkout`) |
| **Episodic Memory** | Zero historical recall (amnesia) | **Recalls INC-101 & INC-104** with exponential time-decay scores |
| **Mitigation Plan** | Generic recommendations ("write tests") | **Actionable, phased rollout checklist** with rollback triggers |

When you disconnect FalkorDB, the agent visibly stumbles. When connected, it delivers ironclad, mathematically provable insights.

---

## Model Context Protocol (FastMCP)

RippleGraph doesn't keep its graph intelligence locked in a silo. We implemented a **FastMCP** server exposing three typed tools:
- `inspect_blast_radius(service_id, change_type)`: Variable-length dependency path traversal.
- `query_service_dependencies(service_id)`: Direct and upstream contract inspection.
- `fetch_incident_memory(service_id, limit)`: Episodic incident and mitigation retrieval.

Any MCP-compliant client (such as Claude Desktop or custom LangGraph agents) can directly consume RippleGraph’s live topology.

---

## What We Learned Building on FalkorDB

1. **Cypher is the Ultimate Agent Query Language:** Giving an LLM the ability to write or consume structured Cypher paths produces 100x more reliable results than prompt engineering over flat JSON documents.
2. **Speed is Crucial for SSE Streaming:** Because FalkorDB traverses graphs in single-digit milliseconds, our Server-Sent Events (SSE) pipeline streams Stage 1 through Stage 4 updates to the UI in real-time without buffering lag.
3. **Graph + Memory is the Future of DevOps Agents:** Combining knowledge graphs (static topology) with episodic memory graphs (dynamic outcomes) creates an AI agent that genuinely gets smarter with every deployment.

---

## Try RippleGraph Live!

- 🌐 **Live Web Application:** [https://ripple-graph-eight.vercel.app](https://ripple-graph-eight.vercel.app)
- 💻 **Open Source GitHub Repo:** [https://github.com/bhavesh-018/RippleGraph](https://github.com/bhavesh-018/RippleGraph)
- 🎥 **YouTube Video Demo:** [Watch the 3-minute Walkthrough](https://www.youtube.com/watch?v=OKwlv2P6BrY)

*Built with FalkorDB, FastAPI, React Flow, Gemini 2.0 Flash, and FastMCP for the Graph Hacks Hackathon 2026.*
