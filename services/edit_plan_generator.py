"""
Edit plan generation service with fail-early approach
Uses Strategy Pattern via factory for extensibility
"""
import logging
from typing import Dict, Any, Optional, List

from fastapi import HTTPException
from .generators.factory import EditPlanGeneratorFactory

logger = logging.getLogger(__name__)


def generate_edit_plan(
    prompt: str,
    conversation_history: Optional[List] = None,
    document_context: Optional[Dict[str, Any]] = None,
    semantic_document: Optional[Dict[str, Any]] = None,
    selected_range: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate EditPlan JSON from user prompt using Azure OpenAI
    Uses Strategy Pattern via factory for extensibility
    Delegates to factory which handles generator selection and execution
    """
    try:
        return EditPlanGeneratorFactory.generate(
            prompt,
            conversation_history,
            document_context,
            semantic_document,
            selected_range
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating edit plan: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating edit plan: {str(e)}"
        )

