"""
RippleGraph - Change Proposals Catalog API

Provides endpoints to discover and inspect available Change Proposals:
  GET /api/changes       - List all built-in and active change proposals
  GET /api/changes/{id}  - Fetch a single change proposal by ID
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from orchestrator.pipeline import BUILTIN_CHANGES
from schemas.graph import ChangeCatalogItem

router = APIRouter(prefix="/api/changes", tags=["Changes"])


@router.get("", response_model=List[ChangeCatalogItem])
async def list_change_proposals():
    """
    List all available built-in change proposals with risk levels and impact scopes.
    """
    items: List[ChangeCatalogItem] = []
    for change_id, change in BUILTIN_CHANGES.items():
        items.append(
            ChangeCatalogItem(
                id=change["id"],
                title=change["title"],
                proposing_service=change["proposing_service"],
                proposing_service_name=change.get("proposing_service_name", change["proposing_service"]),
                target_api=change["target_api"],
                target_api_name=change.get("target_api_name", change["target_api"]),
                proposed_contract_id=change["proposed_contract_id"],
                risk_level=change.get("risk_level", "HIGH"),
                impact_scope=change.get("impact_scope", "Direct Blast Radius"),
                claim_types=change.get("claim_types", []),
                description=change["description"],
            )
        )
    return items


@router.get("/{change_id}", response_model=ChangeCatalogItem)
async def get_change_proposal(change_id: str):
    """
    Fetch a single change proposal by ID.
    """
    if change_id not in BUILTIN_CHANGES:
        raise HTTPException(
            status_code=404,
            detail=f"Change proposal '{change_id}' not found. Available: {list(BUILTIN_CHANGES.keys())}",
        )
    change = BUILTIN_CHANGES[change_id]
    return ChangeCatalogItem(
        id=change["id"],
        title=change["title"],
        proposing_service=change["proposing_service"],
        proposing_service_name=change.get("proposing_service_name", change["proposing_service"]),
        target_api=change["target_api"],
        target_api_name=change.get("target_api_name", change["target_api"]),
        proposed_contract_id=change["proposed_contract_id"],
        risk_level=change.get("risk_level", "HIGH"),
        impact_scope=change.get("impact_scope", "Direct Blast Radius"),
        claim_types=change.get("claim_types", []),
        description=change["description"],
    )
