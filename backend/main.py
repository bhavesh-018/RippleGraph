"""
RippleGraph - FastAPI Application Entry Point

Provides REST and SSE endpoints for the Change Rehearsal Agent:
  - System health checks and graph connectivity
  - Graph topology endpoints for React Flow canvas
  - Change Rehearsal investigation orchestrator (Stages 1-4)
  - Real-time SSE streaming for live node state updates
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from graph.client import health_check

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ripplegraph")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown events."""
    logger.info("Initializing RippleGraph API server...")
    hc = health_check()
    if hc.get("falkordb") == "ok":
        logger.info("FalkorDB connection healthy. Connected to graph: %s", hc.get("graph"))
    else:
        logger.warning("FalkorDB connection check failed: %s", hc.get("detail"))
    yield
    logger.info("Shutting down RippleGraph API server...")


app = FastAPI(
    title="RippleGraph API",
    description="Graph-powered Change Rehearsal Agent for simulating breaking API changes.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for React frontend (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
async def root():
    """Root endpoint providing service metadata and API documentation link."""
    return {
        "service": "RippleGraph API",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
    }


@app.get("/health", tags=["General"])
async def health():
    """Health check endpoint checking graph database connectivity."""
    status = health_check()
    is_healthy = status.get("falkordb") == "ok"
    return {
        "status": "healthy" if is_healthy else "degraded",
        **status,
    }
