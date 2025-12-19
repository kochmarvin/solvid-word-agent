"""
Legacy edit plan generator
Uses traditional document context (headings, content summary)
"""
from typing import Dict, Any, Optional, List
import logging

from .base import BaseEditPlanGenerator
from prompts import SYSTEM_PROMPT
from utils.response_parser import validate_legacy_response

logger = logging.getLogger(__name__)


class LegacyEditPlanGenerator(BaseEditPlanGenerator):
    """
    Generator for legacy edit plans using document context
    """
    
    def __init__(
        self,
        prompt: str,
        conversation_history: Optional[List] = None
    ):
        super().__init__(prompt, conversation_history)
        self.logger.info("Using legacy document model - expecting 'edit_plan' format in response")
    
    def get_system_prompt(self) -> str:
        """Return legacy system prompt"""
        return SYSTEM_PROMPT
    
    def build_user_message(
        self,
        document_context: Optional[Dict[str, Any]] = None,
        semantic_document: Optional[Dict[str, Any]] = None,
        selected_range: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build user message for legacy mode"""
        user_message = f"User request: {self.prompt}\n\n"
        
        # Add selected range if provided
        if selected_range and isinstance(selected_range, dict):
            selected_text = selected_range.get("text", "")
            selected_tag = selected_range.get("tag", "")
            if selected_text and selected_tag:
                user_message += f"IMPORTANT: The user has selected specific text in the document:\n"
                user_message += f'Selected text: "{selected_text}"\n\n'
                user_message += "You MUST use replace_section with anchor 'selected' to replace ONLY this selected section. The selection is marked with a Content Control tag. Do NOT replace the entire document.\n\n"
        
        # Add document context if provided
        if not document_context:
            user_message += "Generate the EditPlan JSON:"
            return user_message
        
        headings = document_context.get("headings", [])
        heading_hierarchy = document_context.get("heading_hierarchy", "")
        relevant_content = document_context.get("relevant_content", [])
        content_summary = document_context.get("content_summary", "")
        has_content = document_context.get("has_content", False)
        
        if has_content:
            user_message += "⚠️ IMPORTANT: This document already has content. Preserve existing content unless explicitly asked to replace it.\n\n"
        
        # Add hierarchical structure
        if heading_hierarchy:
            user_message += "Document structure (hierarchical view - use this to understand parent-child relationships):\n"
            user_message += heading_hierarchy
            user_message += "\n\n"
        elif headings:
            user_message += "Current document structure (headings):\n"
            for heading in headings:
                if isinstance(heading, dict) and "text" in heading:
                    level = heading.get("level", 1)
                    text = heading.get("text", "")
                    user_message += f"  - Heading {level}: {text}\n"
            user_message += "\n"
        
        # Add relevant content sections
        if relevant_content:
            user_message += "Relevant document content (sections matching your query):\n"
            for section in relevant_content:
                if isinstance(section, dict) and "heading" in section:
                    heading_text = section.get("heading", "")
                    level = section.get("level", 1)
                    paragraphs = section.get("paragraphs", [])
                    user_message += f"\nSection (Heading {level}): {heading_text}\n"
                    for para in paragraphs[:3]:
                        if para:
                            user_message += f"  {para[:200]}...\n"
            user_message += "\n"
            user_message += "INTELLIGENT PLACEMENT INSTRUCTIONS:\n"
            user_message += "- Use the hierarchical structure above to understand parent-child relationships between headings\n"
            user_message += "- Analyze the document structure to find the BEST placement location\n"
            user_message += "- When user says 'add X about Y' or 'insert more about X':\n"
            user_message += "  1. Identify the main topic Y from the user request (e.g., 'his career' → person, 'methodology' → thesis)\n"
            user_message += "  2. Find the most relevant main heading (e.g., 'John F Kennedy' for person, 'Bachelor Thesis' for thesis)\n"
            user_message += "  3. Check the hierarchy for a more specific subsection that matches X:\n"
            user_message += "     - If 'Career' (H2) exists under 'John F Kennedy' (H1) and user says 'add more about career' → insert after 'Career' (H2)\n"
            user_message += "     - If 'Methodology' (H2) exists under 'Bachelor Thesis' (H1) and user says 'add methodology' → insert after 'Methodology' (H2)\n"
            user_message += "     - If NO subsection exists, insert after the main heading\n"
            user_message += "  4. Always prefer the MOST SPECIFIC matching heading (lower level number = more specific)\n"
            user_message += "  5. Use semantic matching: 'career' matches 'Career', 'methodology' matches 'Methodology', etc.\n"
            user_message += "- Examples:\n"
            user_message += "  * User: 'add more about career' + Doc has 'John F Kennedy' (H1) with 'Career' (H2) → insert after 'Career' (H2)\n"
            user_message += "  * User: 'add methodology' + Doc has 'Bachelor Thesis' (H1) with 'Methodology' (H2) → insert after 'Methodology' (H2)\n"
            user_message += "  * User: 'add methodology' + Doc has 'Bachelor Thesis' (H1) but NO 'Methodology' → insert after 'Bachelor Thesis' (H1)\n"
            user_message += "  * User: 'add construction details' + Doc has 'Pyramids' (H1) → insert after 'Pyramids' (H1)\n\n"
        elif content_summary:
            user_message += f"Document content summary (for context): {content_summary[:500]}...\n\n"
        
        if headings or relevant_content or content_summary:
            user_message += "CONTEXT AWARENESS INSTRUCTIONS:\n"
            user_message += "- Use the headings and relevant content above to understand document structure and context\n"
            user_message += "- When user refers to a heading (e.g., 'john f', 'early life'), match it to the closest heading above using partial matching\n"
            user_message += "- When user says 'insert more about X' or 'add information about Y', analyze the relevant content sections to find the best location\n"
            user_message += "- Look for semantic relationships: match user's topic to relevant headings and content (persons, topics, concepts, objects, etc.)\n"
            user_message += "- Examples: 'his career' → person heading, 'methodology' → thesis/research heading, 'construction' → object/topic heading\n"
            user_message += "- Use the relevant content sections to understand what already exists and where new content should be placed\n"
            user_message += "- Make intelligent placement decisions based on document structure and relevant content\n"
            user_message += "- If document has existing content, use insert_text instead of replace_section unless explicitly asked to replace\n\n"
        
        user_message += "Generate the EditPlan JSON:"
        return user_message
    
    def validate_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate legacy response format"""
        if "edit_plan" not in result:
            raise ValueError("Legacy response missing 'edit_plan' field")
        
        result = validate_legacy_response(result, use_semantic=False)
        self.logger.info(f"Successfully generated edit plan with {len(result['edit_plan']['actions'])} actions")
        return result

