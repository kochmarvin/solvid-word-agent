"""
JSON response parsing utilities with fail-early approach
"""
import json
import logging

logger = logging.getLogger(__name__)


def parse_json_response(content: str) -> dict:
    """
    Parse JSON from AI response, handling various formats (markdown code blocks, plain JSON, etc.)
    Raises ValueError if JSON cannot be parsed
    """
    content = content.strip()
    
    # Try direct JSON parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code blocks
    if "```json" in content:
        json_start = content.find("```json") + 7
        json_end = content.find("```", json_start)
        if json_end > json_start:
            return json.loads(content[json_start:json_end].strip())
    
    if "```" in content:
        json_start = content.find("```") + 3
        json_end = content.find("```", json_start)
        if json_end > json_start:
            return json.loads(content[json_start:json_end].strip())
    
    # Try finding JSON object boundaries
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    
    if first_brace < 0 or last_brace <= first_brace:
        raise ValueError(f"Could not find valid JSON in response: {content[:200]}")
    
    return json.loads(content[first_brace:last_brace + 1])


def validate_semantic_response(result: dict) -> dict:
    """
    Validate semantic format response (has 'ops' field)
    Raises ValueError if validation fails
    """
    if "response" not in result:
        result["response"] = "Semantic edit plan generated successfully"
    
    if "ops" not in result:
        raise ValueError("Semantic response missing 'ops' field")
    
    if not isinstance(result["ops"], list):
        raise ValueError("'ops' must be an array")
    
    if len(result["ops"]) == 0:
        raise ValueError("Semantic edit plan must have at least one operation in 'ops' array")
    
    # Convert to legacy format for compatibility
    result["edit_plan"] = {
        "version": "1.0",
        "actions": []
    }
    
    return result


def validate_legacy_response(result: dict, use_semantic: bool) -> dict:
    """
    Validate legacy format response (has 'edit_plan' field)
    Raises ValueError if validation fails
    """
    if "response" not in result:
        result["response"] = "Edit plan generated successfully"
    
    if "edit_plan" not in result:
        raise ValueError("Legacy response missing 'edit_plan' field")
    
    # Ensure edit_plan has required structure
    if "version" not in result["edit_plan"]:
        result["edit_plan"]["version"] = "1.0"
    
    if "actions" not in result["edit_plan"]:
        result["edit_plan"]["actions"] = []
    
    # Validate actions
    if len(result["edit_plan"]["actions"]) == 0:
        if use_semantic:
            raise ValueError(
                "AI returned legacy format with 0 actions when semantic format was expected. "
                "The AI should return 'ops' format when semantic document is provided."
            )
        logger.warning("Legacy edit plan has 0 actions - this might indicate an issue")
    
    # Ensure ops is None for legacy plans
    if "ops" not in result:
        result["ops"] = None
    
    return result

