"""
Pydantic models for request/response validation
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DocumentHeading(BaseModel):
    text: str = Field(..., description="Heading text")
    level: int = Field(..., ge=1, le=3, description="Heading level (1-3)")


class RelevantContentSection(BaseModel):
    heading: str = Field(..., description="Heading text for this section")
    paragraphs: list = Field(..., description="Relevant paragraphs from this section")


class DocumentContext(BaseModel):
    headings: list = Field(default=[], description="List of headings in the document")
    heading_hierarchy: Optional[str] = Field(default=None, description="Hierarchical representation of document structure")
    relevant_content: Optional[list] = Field(default=[], description="Relevant content sections based on user query")
    content_summary: Optional[str] = Field(default="", description="Summary of document content for context")
    has_content: Optional[bool] = Field(default=False, description="Whether the document has existing content")


class SemanticDocument(BaseModel):
    sections: list = Field(default=[], description="List of document sections with IDs")
    blocks: Dict[str, Any] = Field(default={}, description="Map of block_id to block content")


class GenerateEditPlanRequest(BaseModel):
    prompt: str = Field(..., description="User prompt describing document changes")
    conversation_history: Optional[list] = Field(default=[], description="Previous conversation messages for context")
    document_context: Optional[DocumentContext] = Field(default=None, description="Current document structure (headings) for context awareness")
    semantic_document: Optional[SemanticDocument] = Field(default=None, description="Semantic document structure with sections and blocks with IDs")
    selected_range: Optional[Dict[str, Any]] = Field(default=None, description="Selected text range with tag and text")


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
    anchor: str = Field(..., description="Anchor identifier for the section (e.g., 'main', 'selected')")
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
    location: str = Field(..., description="Where to insert: 'start', 'end', 'after_heading', or 'at_position'")
    heading_text: Optional[str] = Field(None, description="Heading text to find (required when location is 'after_heading')")
    position: Optional[int] = Field(None, description="Position to insert at (required when location is 'at_position')")
    blocks: list = Field(..., description="List of paragraph or heading blocks to insert")


class EditPlan(BaseModel):
    version: str = Field("1.0", literal=True)
    actions: list = Field(..., description="List of edit actions")


class EditPlanResponse(BaseModel):
    response: str = Field(..., description="Natural language explanation of what was done")
    edit_plan: EditPlan
    ops: Optional[list] = Field(None, description="Semantic edit operations (used when semantic_document is provided)")

