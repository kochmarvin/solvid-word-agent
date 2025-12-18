# Document Editing Agent Backend

Python backend service for generating EditPlan JSON from user prompts using Azure OpenAI.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (optional - defaults are set in code):
```bash
cp .env.example .env
# Edit .env with your credentials
```

Or set environment variables:
```bash
export AZURE_OPENAI_ENDPOINT_GPT5="https://offic-mhomh003-swedencentral.openai.azure.com/"
export AZURE_OPENAI_API_KEY_GPT5="your_api_key_here"
```

## Running the Server

```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST `/api/generate-edit-plan`

Generate an EditPlan from a user prompt.

**Request:**
```json
{
  "prompt": "Write an introduction about climate change"
}
```

**Response:**
```json
{
  "response": "I'll create an introduction section about climate change with a heading and paragraph.",
  "edit_plan": {
    "version": "1.0",
    "actions": [
      {
        "type": "replace_section",
        "anchor": "main",
        "blocks": [
          {
            "type": "heading",
            "level": 1,
            "text": "Introduction to Climate Change"
          },
          {
            "type": "paragraph",
            "text": "Climate change refers to long-term shifts in global temperatures and weather patterns..."
          }
        ]
      }
    ]
  }
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "model": "gpt-5-mini"
}
```

## Configuration

The backend uses:
- **Model**: `gpt-5-mini`
- **Azure OpenAI Endpoint**: Configured via environment variable
- **API Version**: `2024-02-15-preview` (supports structured JSON output)

## CORS

CORS is enabled for all origins by default. In production, configure `allow_origins` in `main.py` to restrict access.

