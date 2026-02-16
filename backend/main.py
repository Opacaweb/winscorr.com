# main.py
from fastapi import FastAPI

# Import your routers / services
from ai_tutor_service import router as ai_router      # adjust if the name is different
from tutoring_service import router as tutor_router    # adjust if needed
# from fatigue_detector import router as fatigue_router  # uncomment if it exists and has a router

# Create the FastAPI application instance
app = FastAPI(
    title="Winscorr AI Tutor API",
    description="Backend for AI-powered SSAT and 8th-grade tutoring",
    version="0.1.0",
    # You can add more settings later, e.g.:
    # docs_url="/docs",
    # redoc_url=None,
    # openapi_url="/openapi.json",
)

# Mount / include the routers from your service modules
app.include_router(ai_router, prefix="/ai")
app.include_router(tutor_router, prefix="/tutor")
# app.include_router(fatigue_router, prefix="/fatigue")   # example

# Health check endpoints (only define once)
@app.get("/")
@app.get("/health")
@app.head("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "winscorr-ai-backend",
        "message": "OK"
    }


# ────────────────────────────────────────────────
# Optional: add a simple root message if you want
# ────────────────────────────────────────────────
@app.get("/api")
async def api_root():
    return {
        "message": "Welcome to the Winscorr AI Tutor Backend API",
        "docs": "/docs",
        "health": "/health"
    }