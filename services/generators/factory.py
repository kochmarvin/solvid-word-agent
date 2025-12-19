"""
Factory for creating appropriate edit plan generators
Following Factory Pattern for extensibility
"""
import logging
from typing import Dict, Any, Optional, List

from .base import BaseEditPlanGenerator
from .semantic_generator import SemanticEditPlanGenerator
from .legacy_generator import LegacyEditPlanGenerator
from openai_client import client
from config import MODEL_NAME
from utils.response_parser import parse_json_response

logger = logging.getLogger(__name__)


class EditPlanGeneratorFactory:
    """
    Factory for creating and executing edit plan generators
    Handles the OpenAI API call and response parsing
    """
    
    @staticmethod
    def should_use_semantic(semantic_document: Optional[Dict[str, Any]]) -> bool:
        """Determine if semantic mode should be used"""
        if not semantic_document:
            return False
        
        has_sections = bool(semantic_document.get("sections"))
        has_blocks = bool(semantic_document.get("blocks"))
        
        if not has_sections or not has_blocks:
            if semantic_document:
                logger.warning(
                    f"Semantic document provided but invalid: "
                    f"sections={has_sections}, blocks={has_blocks}"
                )
            return False
        
        return True
    
    @staticmethod
    def create_generator(
        prompt: str,
        conversation_history: Optional[List] = None,
        semantic_document: Optional[Dict[str, Any]] = None
    ) -> BaseEditPlanGenerator:
        """
        Factory method to create the appropriate generator
        Can be extended to support more generator types
        """
        use_semantic = EditPlanGeneratorFactory.should_use_semantic(semantic_document)
        
        if use_semantic:
            return SemanticEditPlanGenerator(prompt, semantic_document, conversation_history)
        
        return LegacyEditPlanGenerator(prompt, conversation_history)
    
    @staticmethod
    def _call_openai(messages: List[Dict[str, str]], use_semantic: bool) -> str:
        """Call OpenAI API and return response content"""
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                response_format={"type": "json_object"},
                max_completion_tokens=4000
            )
        except Exception as e:
            # Fallback if response_format is not supported
            if "response_format" not in str(e).lower():
                raise
            
            from prompts import SEMANTIC_SYSTEM_PROMPT, SYSTEM_PROMPT
            system_prompt = SEMANTIC_SYSTEM_PROMPT if use_semantic else SYSTEM_PROMPT
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": messages[-1]["content"] + "\n\nIMPORTANT: Respond with ONLY valid JSON, no markdown, no code blocks, just the JSON object."}
                ],
                max_completion_tokens=4000
            )
        
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Empty response from OpenAI")
        
        return response.choices[0].message.content.strip()
    
    @staticmethod
    def generate(
        prompt: str,
        conversation_history: Optional[List] = None,
        document_context: Optional[Dict[str, Any]] = None,
        semantic_document: Optional[Dict[str, Any]] = None,
        selected_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate edit plan using the appropriate generator strategy
        This is the main entry point for edit plan generation
        """
        logger.info(f"Generating edit plan for prompt: {prompt[:100]}...")
        
        # Create appropriate generator
        generator = EditPlanGeneratorFactory.create_generator(
            prompt,
            conversation_history,
            semantic_document
        )
        
        # Build messages
        messages = generator.build_messages(document_context, semantic_document, selected_range)
        
        # Determine if semantic mode
        use_semantic = isinstance(generator, SemanticEditPlanGenerator)
        
        # Call OpenAI
        content = EditPlanGeneratorFactory._call_openai(messages, use_semantic)
        logger.info(f"Raw AI response (first 500 chars): {content[:500]}")
        
        # Parse JSON
        result = parse_json_response(content)
        logger.info(f"Parsed JSON keys: {list(result.keys())}")
        
        # Validate using generator's validation
        result = generator.validate_response(result)
        
        # Ensure ops is always present
        if "ops" not in result:
            result["ops"] = None
        
        logger.info(f"Final result keys before return: {list(result.keys())}")
        if result.get("ops"):
            logger.info(f"Final result has {len(result['ops'])} ops")
        
        return result

