"""
Semantic edit plan generator
Uses semantic document structure with block IDs
"""
import json
import logging
from typing import Dict, Any, Optional, List

from .base import BaseEditPlanGenerator
from prompts import SEMANTIC_SYSTEM_PROMPT
from utils.response_parser import validate_semantic_response

logger = logging.getLogger(__name__)


class SemanticEditPlanGenerator(BaseEditPlanGenerator):
    """
    Generator for semantic edit plans using block IDs
    """
    
    def __init__(
        self,
        prompt: str,
        semantic_document: Dict[str, Any],
        conversation_history: Optional[List] = None
    ):
        super().__init__(prompt, conversation_history)
        self.semantic_document = semantic_document
        sections_count = len(semantic_document.get("sections", []))
        blocks_count = len(semantic_document.get("blocks", {}))
        self.logger.info(
            f"Using semantic document model - {sections_count} sections, "
            f"{blocks_count} blocks - expecting 'ops' format in response"
        )
    
    def get_system_prompt(self) -> str:
        """Return semantic system prompt"""
        return SEMANTIC_SYSTEM_PROMPT
    
    def build_user_message(
        self,
        document_context: Optional[Dict[str, Any]] = None,
        semantic_document: Optional[Dict[str, Any]] = None,
        selected_range: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build user message for semantic mode"""
        # Use instance semantic_document if not provided
        semantic_doc = semantic_document or self.semantic_document
        sections = semantic_doc.get("sections", [])
        blocks = semantic_doc.get("blocks", {})
        
        user_message = f"User request: {self.prompt}\n\n"
        user_message += "DOCUMENT STRUCTURE (with stable block IDs):\n"
        user_message += json.dumps({
            "sections": sections,
            "blocks": blocks
        }, indent=2)
        user_message += "\n\n"
        user_message += "IMPORTANT: Use the block IDs above to reference specific blocks. Do NOT invent block IDs.\n"
        user_message += "When choosing where to insert content, analyze the semantic structure and choose the most appropriate block_id.\n\n"
        user_message += "IMPORTANT: You MUST respond with JSON in this exact format:\n"
        user_message += '{\n  "response": "Your explanation",\n  "ops": [\n    {\n      "action": "insert_after",\n      "target_block_id": "b1",\n      "content": "Text to insert",\n      "reason": "Why this location"\n    }\n  ]\n}\n'
        user_message += "Do NOT use 'edit_plan' format. Use 'ops' format only.\n"
        
        return user_message
    
    def validate_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate semantic response format"""
        if "ops" not in result:
            raise ValueError("Semantic response missing 'ops' field")
        
        result = validate_semantic_response(result)
        self.logger.info(f"Successfully generated semantic edit plan with {len(result['ops'])} operations")
        return result

