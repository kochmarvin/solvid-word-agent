"""
Main FastAPI application entry point
Minimal app initialization following best practices
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import MODEL_NAME
from api.routes import generate_edit_plan_endpoint
from models import GenerateEditPlanRequest, EditPlanResponse

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

# Register routes
app.post("/api/generate-edit-plan", response_model=EditPlanResponse)(
    generate_edit_plan_endpoint
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": MODEL_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
