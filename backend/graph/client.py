"""
RippleGraph - FalkorDB Connection Singleton

Provides a single, lazily-initialized FalkorDB graph client shared across
the entire application lifecycle. Includes health check and retry logic.
"""

import logging
import time
from functools import lru_cache

import falkordb

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
_client: falkordb.FalkorDB | None = None
_graph: falkordb.Graph | None = None


def _connect_with_retry(max_retries: int = 5, delay: float = 2.0) -> falkordb.FalkorDB:
    """Attempt to connect to FalkorDB with exponential backoff retry."""
    for attempt in range(1, max_retries + 1):
        try:
            client = falkordb.FalkorDB(
                host=settings.falkordb_host,
                port=settings.falkordb_port,
            )
            # Verify connectivity with a lightweight ping
            client.connection.ping()
            logger.info(
                "Connected to FalkorDB at %s:%s on attempt %d",
                settings.falkordb_host,
                settings.falkordb_port,
                attempt,
            )
            return client
        except Exception as exc:
            wait = delay * (2 ** (attempt - 1))
            logger.warning(
                "FalkorDB connection attempt %d/%d failed: %s. Retrying in %.1fs...",
                attempt,
                max_retries,
                exc,
                wait,
            )
            if attempt == max_retries:
                raise ConnectionError(
                    f"Could not connect to FalkorDB at "
                    f"{settings.falkordb_host}:{settings.falkordb_port} "
                    f"after {max_retries} attempts."
                ) from exc
            time.sleep(wait)


def get_client() -> falkordb.FalkorDB:
    """Return the global FalkorDB client, creating it on first call if needed."""
    global _client
    if _client is None:
        _client = _connect_with_retry()
    return _client


def get_graph() -> falkordb.Graph:
    """Return the named FalkorDB graph, creating it on first call if needed."""
    global _graph
    if _graph is None:
        _graph = get_client().select_graph(settings.falkordb_graph_name)
        logger.info("Selected graph: %s", settings.falkordb_graph_name)
    return _graph


def reset_graph() -> None:
    """
    Delete and re-initialize the graph. Used by the /api/seed/reset endpoint.
    Resets module-level singletons so the next call to get_graph() starts fresh.
    """
    global _client, _graph
    try:
        if _client is not None:
            g = _client.select_graph(settings.falkordb_graph_name)
            g.delete()
            logger.info("Graph '%s' deleted.", settings.falkordb_graph_name)
    except Exception as exc:
        logger.warning("Could not delete graph (may not exist yet): %s", exc)
    finally:
        _graph = None  # force re-selection on next get_graph() call


def health_check() -> dict:
    """Return a dict describing FalkorDB health for the /health endpoint."""
    try:
        get_client().connection.ping()
        return {"falkordb": "ok", "graph": settings.falkordb_graph_name}
    except Exception as exc:
        return {"falkordb": "error", "detail": str(exc)}
