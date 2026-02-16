from fastapi import FastAPI

app = FastAPI(title="Winscorr Minimal")

@app.get("/")
@app.get("/health")
@app.head("/")
async def health():
    return {
        "status": "healthy",
        "timestamp": "now",
        "path": "reached root or health"
    }