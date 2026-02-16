# main.py  ← this becomes your app entrypoint

from fastapi import FastAPI
from ai_tutor_service import router as ai_router     # adjust import names as needed
from tutoring_service import router as tutor_router   # example
# from fatigue_detector import ...                   # import if it has routes

app = FastAPI(
    title="Winscorr AI Tutor API",
    description="Backend for AI-powered SSAT and 8th-grade tutoring",
    version="0.1.0"
)

# Include routers from your service files (if they use APIRouter)
app.include_router(ai_router, prefix="/ai")
app.include_router(tutor_router, prefix="/tutor")
# app.include_router(other_router, prefix="/other")   # add more as needed

# Simple health check endpoint (required for Railway)
@app.get("/")
@app.get("/health")
@app.head("/")
async def health_check():
    return {"status": "healthy", "service": "winscorr-ai-backend"}