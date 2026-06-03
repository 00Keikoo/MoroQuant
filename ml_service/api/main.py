"""FastAPI main application for ML trading system."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .routes import router

app = FastAPI(
    title="ML Trading Intelligence API",
    description="Real-time trading signals powered by machine learning",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

dashboard_path = Path(__file__).parent.parent / "dashboard.html"

@app.get("/")
async def serve_dashboard():
    """Serve the dashboard HTML."""
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "ML Trading Intelligence API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
