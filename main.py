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
class DocumentHeading(BaseModel):
    text: str = Field(..., description="Heading text")
    level: int = Field(..., ge=1, le=3, description="Heading level (1-3)")


class DocumentContext(BaseModel):
    headings: list = Field(default=[], description="List of headings in the document")
    content_summary: Optional[str] = Field(default="", description="Summary of document content for context")
    has_content: Optional[bool] = Field(default=False, description="Whether the document has existing content")


class GenerateEditPlanRequest(BaseModel):
    prompt: str = Field(..., description="User prompt describing document changes")
    conversation_history: Optional[list] = Field(default=[], description="Previous conversation messages for context")
    document_context: Optional[DocumentContext] = Field(default=None, description="Current document structure (headings) for context awareness")


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


class CorrectTextAction(BaseModel):
    type: str = Field("correct_text", literal=True)
    search_text: str = Field(..., description="Text to search for in the document")
    replacement_text: str = Field(..., description="Text to replace the search text with")
    case_sensitive: Optional[bool] = Field(False, description="Whether the search should be case sensitive")


class InsertTextAction(BaseModel):
    type: str = Field("insert_text", literal=True)
    anchor: str = Field(..., description="Anchor identifier (usually 'main')")
    location: str = Field(..., description="Where to insert: 'start', 'end', or 'after_heading'")
    heading_text: Optional[str] = Field(None, description="Heading text to find (required when location is 'after_heading')")
    blocks: list = Field(..., description="List of paragraph or heading blocks to insert")


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

CRITICAL: Make MINIMAL, TARGETED changes. Only change what the user explicitly requests.
- If the user asks to fix a typo, ONLY fix that typo, don't replace the whole text
- If the user asks to insert text at the start, ONLY insert at the start, don't delete existing content
- If the user asks to change specific text, ONLY change that text, preserve everything else
- Preserve all existing content unless explicitly asked to replace it

The document editor supports ONLY:
- Paragraphs
- Headings
- Basic formatting (color)

CONTENT AWARENESS (CRITICAL):
- You will receive the current document structure (headings and content summary) in the user message
- ALWAYS check if the document has existing content before making changes
- Use document headings and content to understand context and make intelligent placement decisions

Heading Matching:
- When the user refers to a heading (e.g., "john f", "early life"), match it to existing headings
- Use partial matching: "john f" should match "John F Kennedy", "early life" should match "Early Life of John F Kennedy"
- Match headings case-insensitively and by partial text
- When inserting content "under" or "to" a heading, use insert_text with location: "after_heading" and the matching heading text

Semantic Context Understanding:
- When user says "insert more about X", "add information about Y", "add details about Z", analyze the document content
- Look for related headings or topics in the document that semantically relate to the user's request
- Match ANY type of content: persons, topics, concepts, objects, etc.
- Examples:
  * "insert more about his career" with heading "John F Kennedy" → insert after "John F Kennedy"
  * "add methodology section" with heading "Bachelor Thesis" → insert after "Bachelor Thesis"
  * "add information about construction" with heading "Pyramids" → insert after "Pyramids"
  * "add more about history" with heading "Ancient Egypt" → insert after "Ancient Egypt"
- Use the content_summary to understand what the document is about
- Make intelligent decisions about where content fits best based on semantic relationships
- Match topics, concepts, and any entities mentioned in headings to user requests

Initial Prompts on Existing Documents:
- If document has_content is true, DO NOT use replace_section unless explicitly asked to replace
- Instead, use insert_text to add new content while preserving existing content
- Analyze existing headings to understand document structure
- Place new content in the most appropriate location based on context

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
- Replaces the ENTIRE content of a section identified by an anchor
- ONLY use this when the user explicitly asks to rewrite, replace, or recreate a section
- DO NOT use this for minor corrections, typos, or insertions
- This action DELETES all existing content in the section and replaces it

2) update_heading_style
- Updates formatting for existing headings
- Used for requests like "change headings to blue"

3) correct_text
- Finds and replaces SPECIFIC text in the document WITHOUT affecting other content
- Use this for: typos, word replacements, small text corrections
- Example: "fix the typo 'teh' to 'the'" → only changes 'teh' to 'the', keeps everything else
- Example: "change 'climate change' to 'global warming'" → only changes that phrase
- The search_text should be the EXACT text to find (or close approximation)
- The replacement_text should be what to replace it with
- This is the PREFERRED action for corrections and small changes
- DO NOT use replace_section for simple corrections - use correct_text instead

4) insert_text
- Inserts new content at the start, end, or after a specific heading WITHOUT deleting existing content
- Use this when the user asks to "insert", "add at the start", "add at the end", "add to this heading/section"
- Example: "insert 'Introduction' at the start" → adds heading at start, keeps existing content
- Example: "add a paragraph at the end" → adds paragraph at end, keeps existing content
- Example: "add a starting paragraph to this heading" → adds paragraph after the heading mentioned in conversation
- location must be "start", "end", or "after_heading"
- When location is "after_heading", heading_text is REQUIRED - extract the heading text from conversation history
- If user says "this heading", "this section", "to this content", look at conversation history to find the heading text
- anchor is usually "main" for document-level insertions
- This is the PREFERRED action for insertions - preserves all existing content

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
      },
      {
        "type": "correct_text",
        "search_text": "climate change",
        "replacement_text": "global warming",
        "case_sensitive": false
      },
      {
        "type": "insert_text",
        "anchor": "main",
        "location": "start",
        "blocks": [
          {
            "type": "heading",
            "level": 1,
            "text": "Introduction"
          }
        ]
      },
      {
        "type": "insert_text",
        "anchor": "main",
        "location": "after_heading",
        "heading_text": "Introduction",
        "blocks": [
          {
            "type": "paragraph",
            "text": "This is a paragraph added after the Introduction heading"
          }
        ]
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
   - BUT: Only use replace_section if the user explicitly wants to replace a whole section
   - For insertions at the start, use replace_section with anchor "main" but PRESERVE existing content in blocks

7) Text corrections and minimal changes:
   - ALWAYS prefer "correct_text" for: typos, word changes, small corrections
   - When the user asks to "fix", "correct", "change [specific text]", use correct_text
   - Look at conversation history to understand what text was previously mentioned
   - Extract the exact or approximate text to search for from the conversation
   - If the user says "change that" or "fix it", refer to the conversation history to find what "that" or "it" refers to
   - Use case_sensitive: false by default unless the user specifically mentions case sensitivity

8) Insertions and intelligent content placement:
   - ALWAYS use "insert_text" when the user asks to "insert", "add", "add more about", "insert information about"
   - insert_text preserves ALL existing content - it only adds new content
   - If user says "insert X at the start", use insert_text with location: "start"
   - If user says "add X at the end", use insert_text with location: "end"
   - If user mentions a specific heading (e.g., "add early life of john f"):
     * Check the document structure (headings list) provided in the user message
     * Match the user's reference to an existing heading using partial matching
     * Use insert_text with location: "after_heading" and heading_text: "<matched heading text from document>"
   
   - SEMANTIC CONTEXT MATCHING (for phrases like "insert more about X", "add information about Y"):
     * Analyze the document content_summary and headings to understand context
     * Look for semantic relationships between user request and document headings
     * Works for ANY content type: persons, topics, concepts, objects, subjects, etc.
     * Examples of semantic matching:
       - "his career" / "his early life" → find person headings (e.g., "John F Kennedy")
       - "methodology" / "results" → find academic headings (e.g., "Bachelor Thesis", "Research Paper")
       - "construction" / "architecture" → find object/topic headings (e.g., "Pyramids", "Ancient Buildings")
       - "history" / "origins" → find topic headings (e.g., "Ancient Egypt", "Roman Empire")
     * Match user's topic/concept to the most relevant heading in the document
     * Use intelligent matching: if document has "Pyramids" heading and user says "construction methods",
       insert after "Pyramids" heading
     * If multiple headings match, choose the most semantically relevant one
     * Examples:
       - "insert more about his career" with heading "John F Kennedy" → insert after "John F Kennedy"
       - "add methodology section" with heading "Bachelor Thesis" → insert after "Bachelor Thesis"
       - "add information about construction" with heading "Pyramids" → insert after "Pyramids"
   
   - Context awareness priority:
     1. Document structure (headings + content_summary) - PRIMARY source
     2. Semantic analysis of user request vs document content
     3. Conversation history - TERTIARY source
   
   - DO NOT use replace_section for insertions - use insert_text instead

9) Content preservation:
   - correct_text: ONLY changes the specified text, preserves everything else
   - insert_text: ONLY adds new content, preserves all existing content
   - replace_section: Replaces entire section - ONLY use when user explicitly wants to replace/rewrite
   - If user says "fix typo", use correct_text to ONLY fix that typo
   - If user says "change X to Y", use correct_text to ONLY change X to Y
   - If user says "insert X", use insert_text to ONLY add X
   - NEVER delete content unless explicitly asked to replace/rewrite

10) Output rules:
   - Output EXACTLY one JSON object
   - No comments
   - No trailing text
   - No explanations outside the "response" field

────────────────────────────────
EXAMPLES OF USER REQUESTS YOU MUST HANDLE
────────────────────────────────

- "Write an introduction about climate change" (use replace_section with anchor "main")
- "Rewrite this section more professionally" (use replace_section - user explicitly wants rewrite)
- "Add a heading and two paragraphs" (use replace_section, but preserve existing content)
- "Change all headings to blue" (use update_heading_style)
- "Improve the text and make headings blue" (use replace_section if rewriting, update_heading_style for color)
- "Fix the typo 'teh' to 'the'" (use correct_text - ONLY fixes the typo)
- "Change 'climate change' to 'global warming'" (use correct_text - ONLY changes that phrase)
- "Insert 'Introduction' at the start" (use insert_text with location: "start" - preserves existing content)
- "Add a paragraph at the end" (use insert_text with location: "end" - preserves existing content)
- "Add a starting paragraph to this heading" (use insert_text with location: "after_heading", heading_text from conversation)
- "Add content to this section" (use insert_text with location: "after_heading", find heading from conversation history)
- "Insert more about his career" (analyze document, find person heading, use insert_text with location: "after_heading")
- "Add information about early life" (analyze document, find relevant heading, use insert_text with location: "after_heading")
- "Add methodology section" (analyze document, find thesis/research heading, use insert_text with location: "after_heading")
- "Add information about construction" (analyze document, find pyramids/building heading, use insert_text with location: "after_heading")
- "Change that to 'new text'" (use correct_text, refer to conversation history)

Think first.
Then produce the final JSON object."""


def generate_edit_plan(prompt: str, conversation_history: Optional[list] = None, document_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate EditPlan JSON from user prompt using Azure OpenAI
    """
    logger.info(f"Generating edit plan for prompt: {prompt[:100]}...")
    try:
        # Build messages with conversation history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    # Convert "ai" role to "assistant" for OpenAI API compatibility
                    role = msg["role"]
                    if role == "ai":
                        role = "assistant"
                    elif role not in ["system", "assistant", "user", "function", "tool", "developer"]:
                        # Skip invalid roles
                        logger.warning(f"Skipping message with invalid role: {role}")
                        continue
                    
                    messages.append({
                        "role": role,
                        "content": msg["content"]
                    })
        
        # Build user message with document context
        user_message = f"User request: {prompt}\n\n"
        
        # Add document context (headings and content) if provided
        if document_context:
            headings = document_context.get("headings", [])
            content_summary = document_context.get("content_summary", "")
            has_content = document_context.get("has_content", False)
            
            if has_content:
                user_message += "⚠️ IMPORTANT: This document already has content. Preserve existing content unless explicitly asked to replace it.\n\n"
            
            if headings:
                user_message += "Current document structure (headings):\n"
                for heading in headings:
                    if isinstance(heading, dict) and "text" in heading:
                        level = heading.get("level", 1)
                        text = heading.get("text", "")
                        user_message += f"  - Heading {level}: {text}\n"
                user_message += "\n"
            
            if content_summary:
                user_message += f"Document content summary (for context): {content_summary[:500]}...\n\n"
            
            if headings or content_summary:
                user_message += "CONTEXT AWARENESS INSTRUCTIONS:\n"
                user_message += "- Use these headings to understand document structure\n"
                user_message += "- When user refers to a heading (e.g., 'john f', 'early life'), match it to the closest heading above using partial matching\n"
                user_message += "- When user says 'insert more about X' or 'add information about Y', analyze the document to find the best location\n"
                user_message += "- Look for semantic relationships: match user's topic to relevant headings (persons, topics, concepts, objects, etc.)\n"
                user_message += "- Examples: 'his career' → person heading, 'methodology' → thesis/research heading, 'construction' → object/topic heading\n"
                user_message += "- Make intelligent placement decisions based on document structure and content\n"
                user_message += "- If document has existing content, use insert_text instead of replace_section unless explicitly asked to replace\n\n"
        
        user_message += "Generate the EditPlan JSON:"
        messages.append({"role": "user", "content": user_message})

        # Call Azure OpenAI with structured output
        # Note: response_format may not be supported in all Azure OpenAI deployments
        # If it fails, we'll parse JSON from the response text
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
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
    Generate an EditPlan from a user prompt with optional conversation history and document context
    """
    try:
        document_context_dict = None
        if request.document_context:
            document_context_dict = request.document_context.dict() if hasattr(request.document_context, 'dict') else request.document_context
        result = generate_edit_plan(request.prompt, request.conversation_history, document_context_dict)
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

