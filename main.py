"""
Python backend for document editing agent
Generates EditPlan JSON from user prompts using Azure OpenAI
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import AzureOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT_GPT5 = os.getenv(
    "AZURE_OPENAI_ENDPOINT_GPT5",
    "https://offic-mhomh003-swedencentral.openai.azure.com/"
)
AZURE_OPENAI_API_KEY_GPT5 = os.getenv(
    "AZURE_OPENAI_API_KEY_GPT5",
    "5Xt61rTN84oi6yyobiEzwlnQS2fUj2fjs1v6kpWxC4IkUajSvyhmJQQJ99BKACfhMk5XJ3w3AAAAACOGE0yI"
)
MODEL_NAME = "gpt-5-mini"

# Initialize FastAPI app
app = FastAPI(title="Document Editing Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY_GPT5,
    api_version="2024-08-01-preview",  # Use version that supports structured output
    azure_endpoint=AZURE_OPENAI_ENDPOINT_GPT5
)


# Request/Response Models
class GenerateEditPlanRequest(BaseModel):
    prompt: str = Field(..., description="User prompt describing document changes")


class BlockStyle(BaseModel):
    color: Optional[str] = Field(None, description="CSS color value (hex, rgb, or named color)")


class ParagraphBlock(BaseModel):
    type: str = Field("paragraph", literal=True)
    text: str = Field(..., description="Paragraph text (no newlines)")


class HeadingBlock(BaseModel):
    type: str = Field("heading", literal=True)
    level: int = Field(..., ge=1, le=3, description="Heading level (1-3)")
    text: str = Field(..., description="Heading text")
    style: Optional[BlockStyle] = None


class ReplaceSectionAction(BaseModel):
    type: str = Field("replace_section", literal=True)
    anchor: str = Field(..., description="Anchor identifier for the section")
    blocks: list = Field(..., description="List of paragraph or heading blocks")


class UpdateHeadingStyleAction(BaseModel):
    type: str = Field("update_heading_style", literal=True)
    target: str = Field("all", literal=True)
    style: BlockStyle = Field(..., description="Style to apply to all headings")


class EditPlan(BaseModel):
    version: str = Field("1.0", literal=True)
    actions: list = Field(..., description="List of edit actions")


class EditPlanResponse(BaseModel):
    response: str = Field(..., description="Natural language explanation of what was done")
    edit_plan: EditPlan


# System prompt for the AI agent
SYSTEM_PROMPT = """You are a basic document editing agent for a Word-like editor.

Your job:
- Read the user prompt.
- Produce TWO things:
  1) A short natural-language response to the user (what you did / will do).
  2) A structured EditPlan describing exactly how the document should be edited.

The document editor supports ONLY:
- Paragraphs
- Headings
- Basic formatting (color)

You must express ALL document changes using the EditPlan schema below.
Do NOT describe edits in prose.
Do NOT output markdown.
Do NOT output anything outside the final JSON.

────────────────────────────────
SUPPORTED BLOCK TYPES
────────────────────────────────

1) paragraph
- Normal body text

2) heading
- A heading (level 1–3)

────────────────────────────────
SUPPORTED ACTIONS
────────────────────────────────

1) replace_section
- Replaces the content of a section identified by an anchor

2) update_heading_style
- Updates formatting for existing headings
- Used for requests like "change headings to blue"

────────────────────────────────
EDIT PLAN SCHEMA (STRICT)
────────────────────────────────

{
  "response": "<short explanation for the user>",
  "edit_plan": {
    "version": "1.0",
    "actions": [
      {
        "type": "replace_section",
        "anchor": "<string>",
        "blocks": [
          {
            "type": "heading",
            "level": 1,
            "text": "<heading text>",
            "style": {
              "color": "<optional>"
            }
          },
          {
            "type": "paragraph",
            "text": "<paragraph text>"
          }
        ]
      },
      {
        "type": "update_heading_style",
        "target": "all",
        "style": {
          "color": "blue"
        }
      }
    ]
  }
}

────────────────────────────────
RULES (VERY IMPORTANT)
────────────────────────────────

1) Always return BOTH:
   - "response" (user-facing explanation)
   - "edit_plan" (machine-executable)

2) Only use the supported actions and block types.
   - No tables
   - No lists
   - No inline formatting except color on headings

3) Paragraph rules:
   - Each paragraph is ONE block
   - Do NOT include newline characters inside paragraph text

4) Heading rules:
   - Use block type "heading"
   - Include a numeric level (1–3)
   - Heading text must be plain text
   - Formatting goes into the "style" object

5) Formatting changes:
   - If the user asks to change heading color (e.g. "make headings blue"),
     you MUST use the action "update_heading_style"
   - Do NOT rewrite the headings unless explicitly asked

6) Anchors:
   - If the user does not specify a section, use anchor "main"

7) Output rules:
   - Output EXACTLY one JSON object
   - No comments
   - No trailing text
   - No explanations outside the "response" field

────────────────────────────────
EXAMPLES OF USER REQUESTS YOU MUST HANDLE
────────────────────────────────

- "Write an introduction about climate change"
- "Rewrite this section more professionally"
- "Add a heading and two paragraphs"
- "Change all headings to blue"
- "Improve the text and make headings blue"

Think first.
Then produce the final JSON object."""


def generate_edit_plan(prompt: str) -> Dict[str, Any]:
    """
    Generate EditPlan JSON from user prompt using Azure OpenAI
    """
    logger.info(f"Generating edit plan for prompt: {prompt[:100]}...")
    try:
        # Create the user message
        user_message = f"User request: {prompt}\n\nGenerate the EditPlan JSON:"

        # Call Azure OpenAI with structured output
        # Note: response_format may not be supported in all Azure OpenAI deployments
        # If it fails, we'll parse JSON from the response text
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},  # Force JSON output
                max_completion_tokens=4000
            )
        except Exception as e:
            # Fallback if response_format is not supported
            if "response_format" in str(e).lower():
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message + "\n\nIMPORTANT: Respond with ONLY valid JSON, no markdown, no code blocks, just the JSON object."}
                    ],
                    max_completion_tokens=4000
                )
            else:
                raise

        # Extract the JSON response
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Empty response from OpenAI")
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                if json_end > json_start:
                    content = content[json_start:json_end].strip()
                    result = json.loads(content)
                else:
                    raise ValueError(f"Invalid JSON response: {e}")
            elif "```" in content:
                # Try to extract from generic code block
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                if json_end > json_start:
                    content = content[json_start:json_end].strip()
                    result = json.loads(content)
                else:
                    raise ValueError(f"Invalid JSON response: {e}")
            else:
                # Try to find JSON object in the response
                # Look for first { and last }
                first_brace = content.find("{")
                last_brace = content.rfind("}")
                if first_brace >= 0 and last_brace > first_brace:
                    content = content[first_brace:last_brace + 1]
                    result = json.loads(content)
                else:
                    raise ValueError(f"Invalid JSON response: {e}")

        # Validate structure
        if "edit_plan" not in result:
            raise ValueError("Response missing 'edit_plan' field")
        
        if "response" not in result:
            result["response"] = "Edit plan generated successfully"

        # Ensure edit_plan has required structure
        if "version" not in result["edit_plan"]:
            result["edit_plan"]["version"] = "1.0"
        if "actions" not in result["edit_plan"]:
            result["edit_plan"]["actions"] = []

        logger.info(f"Successfully generated edit plan with {len(result['edit_plan']['actions'])} actions")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating edit plan: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating edit plan: {str(e)}"
        )


@app.post("/api/generate-edit-plan", response_model=EditPlanResponse)
async def generate_edit_plan_endpoint(request: GenerateEditPlanRequest):
    """
    Generate an EditPlan from a user prompt
    """
    try:
        result = generate_edit_plan(request.prompt)
        return EditPlanResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": MODEL_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

