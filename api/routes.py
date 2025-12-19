"""
API routes with fail-early approach
"""
import logging
from typing import Dict, Any

from fastapi import HTTPException
from models import GenerateEditPlanRequest, EditPlanResponse
from services.edit_plan_generator import generate_edit_plan

logger = logging.getLogger(__name__)


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Convert Pydantic model or dict to dict"""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, 'dict'):
        return obj.dict()
    return obj


async def generate_edit_plan_endpoint(request: GenerateEditPlanRequest) -> EditPlanResponse:
    """
    Generate an EditPlan from a user prompt with optional conversation history and document context
    Uses fail-early approach
    """
    # Convert Pydantic models to dicts early
    document_context_dict = _to_dict(request.document_context) if request.document_context else None
    semantic_document_dict = _to_dict(request.semantic_document) if request.semantic_document else None
    selected_range_dict = _to_dict(request.selected_range) if request.selected_range else None
    
    # Generate edit plan
    result = generate_edit_plan(
        request.prompt,
        request.conversation_history,
        document_context_dict,
        semantic_document_dict,
        selected_range_dict
    )
    
    # Log response details
    logger.info(f"Returning EditPlanResponse with keys: {list(result.keys())}")
    if "ops" in result and result["ops"] is not None:
        logger.info(f"Returning EditPlanResponse with {len(result['ops'])} ops")
    elif "ops" in result:
        logger.info("Returning EditPlanResponse with ops=None (legacy plan)")
    
    # Create response model
    response = EditPlanResponse(**result)
    logger.info(f"EditPlanResponse object has ops: {response.ops is not None}")
    if response.ops is not None:
        logger.info(f"EditPlanResponse.ops has {len(response.ops)} operations")
    
    return response

