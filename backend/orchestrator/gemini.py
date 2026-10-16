"""
RippleGraph - Gemini LLM Integration

Converts natural language questions about the service dependency graph
into read-only FalkorDB Cypher queries using the Gemini API.

Flow:
  1. Receive a natural language question from the user
  2. Build a schema-aware prompt describing the RippleGraph node/edge model
  3. Call Gemini to generate a Cypher query
  4. Validate the query is strictly READ-ONLY (no mutations)
  5. Return the safe Cypher string for execution

Safety: Any Cypher containing write operations (CREATE, DELETE, SET,
MERGE, REMOVE, DROP) is rejected with a ValueError before it reaches
the graph database.
"""

import logging
import re
from typing import Optional

import google.genai as genai

from config import settings

logger = logging.getLogger("ripplegraph.orchestrator.gemini")

# ── Graph schema description sent to Gemini ──────────────────────────────────
# Keep this in sync with graph/seed.py node labels and relationships.

GRAPH_SCHEMA = """
You are a Cypher query generator for a FalkorDB property graph database
called RippleGraph. The graph models a microservices ecosystem used to
reason about the blast radius of API contract changes.

NODE LABELS and KEY PROPERTIES:
  Service(id, name, tier, owner_team, description, runtime, version, port)
    - tier values: "platform", "core", "supporting"
    - Example IDs: "auth-service", "payment-service", "api-gateway"

  API(id, name, protocol, path, service_id)
    - Example IDs: "auth-token-api", "payment-charge-api"

  ContractVersion(id, name, version, status, breaking_change, description)
    - status values: "active", "proposed", "transitional"
    - Example IDs: "cv-auth-v1", "cv-auth-v2"

  Incident(id, title, severity, description, root_cause, occurred_at)
    - severity values: "critical", "high", "medium", "low"
    - Example IDs: "INC-101", "INC-102"

  Mitigation(id, title, description, validation_method)
    - Example IDs: "MIT-101", "MIT-102"

  Finding(id, service_id, service_name, category, status, confidence, hop_depth)
    - status values: "incompatible", "potential_downstream", "compatible", "unaffected"
    - category values: "DIRECT_INCOMPATIBILITY", "TRANSITIVE_RISK", "COMPATIBLE_CONSUMER", "UNAFFECTED"
    - confidence: float 0.0-1.0

  Investigation(id, change_id, change_title, status, memory_enabled, created_at)

RELATIONSHIPS:
  (Service)-[:EXPOSES]->(API)
  (Service)-[:DEPENDS_ON]->(Service)
  (Service)-[:ACCEPTS_CONTRACT]->(ContractVersion)
  (API)-[:HAS_CONTRACT]->(ContractVersion)
  (Incident)-[:AFFECTED]->(Service)
  (Incident)-[:MITIGATED_BY]->(Mitigation)
  (Investigation)-[:PRODUCED]->(Finding)
  (Finding)-[:ABOUT_SERVICE]->(Service)

RULES:
- Generate ONLY the Cypher query — no explanation, no markdown, no backticks
- The query MUST be read-only: use only MATCH, RETURN, WHERE, WITH, ORDER BY, LIMIT, OPTIONAL MATCH
- Do NOT use CREATE, DELETE, SET, MERGE, REMOVE, DROP
- Use LIMIT 20 unless the user asks for more
- Use case-insensitive matching where appropriate: toLower(n.name) CONTAINS toLower($value)
- Always alias columns meaningfully: RETURN s.name AS service_name
- When the question is ambiguous, prefer to return more columns for context
"""

# Write-operation keywords that are never allowed in user-generated Cypher
_FORBIDDEN_OPS = frozenset(
    ["CREATE", "DELETE", "SET", "MERGE", "REMOVE", "DROP", "DETACH"]
)


def _is_safe_cypher(cypher: str) -> bool:
    """Return True if the Cypher query contains no write operations."""
    upper = cypher.upper()
    for op in _FORBIDDEN_OPS:
        # Match as whole word to avoid false positives (e.g. "CREATED_AT")
        if re.search(rf"\b{op}\b", upper):
            return False
    return True


def _clean_cypher(raw: str) -> str:
    """Strip markdown code fences and leading/trailing whitespace."""
    # Remove ```cypher ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:cypher)?\s*", "", raw, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    return cleaned


def nl_to_cypher(question: str, extra_context: Optional[str] = None) -> str:
    """
    Convert a natural language question into a safe, read-only Cypher query
    using the Gemini LLM.

    Args:
        question:      The user's natural language question about the graph.
        extra_context: Optional additional context to append to the prompt
                       (e.g., currently selected change ID).

    Returns:
        A validated, read-only Cypher query string.

    Raises:
        ValueError: If the API key is not configured, or if Gemini returns
                    a query containing write operations.
        RuntimeError: If the Gemini API call fails.
    """
    api_key = settings.gemini_api_key
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to backend/.env to enable "
            "natural language graph queries."
        )

    prompt_parts = [
        GRAPH_SCHEMA,
        f'\nUser question: "{question}"',
    ]
    if extra_context:
        prompt_parts.append(f"\nAdditional context: {extra_context}")

    prompt = "\n".join(prompt_parts)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        raw_cypher = response.text or ""
    except Exception as exc:
        logger.exception("Gemini API call failed: %s", exc)
        raise RuntimeError(f"Gemini API error: {exc}") from exc

    cypher = _clean_cypher(raw_cypher)

    if not cypher:
        raise ValueError("Gemini returned an empty query. Please rephrase your question.")

    if not _is_safe_cypher(cypher):
        logger.warning("Rejected unsafe Cypher from Gemini: %s", cypher)
        raise ValueError(
            "Generated query contains write operations and was rejected for safety. "
            "Please ask a read-only question about the graph."
        )

    logger.info("NL query '%s' -> Cypher: %s", question, cypher)
    return cypher
