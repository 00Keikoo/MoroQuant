"""FastAPI main application for ML trading system."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import asyncio
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .routes import router
from ml_service.services.crypto_price_service import get_crypto_service
from ml_service.services.proxy_price_service import get_proxy_service
from ml_service.scheduler import start_scheduler

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

@app.on_event("startup")
async def startup_event():
    """Initialize price services and auto-retrain scheduler."""
    get_crypto_service()
    get_proxy_service()
    print("✅ Price services ready (on-demand fetching)")

    start_scheduler()
    print("✅ Auto-retrain scheduler started (runs every 24h)")

@app.get("/")
async def serve_dashboard():
    """Serve the dashboard HTML."""
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "ML Trading Intelligence API", "docs": "/docs"}

@app.get("/health/prices")
async def health_prices():
    """Check price service health."""
    crypto_service = get_crypto_service()
    proxy_service = get_proxy_service()

    return {
        "crypto": {
            "symbols": list(crypto_service.price_cache.keys()),
            "live_count": sum(1 for p in crypto_service.price_cache.values() if p.get('live')),
            "total": len(crypto_service.price_cache),
            "prices": crypto_service.price_cache
        },
        "proxy": {
            "symbols": list(proxy_service.price_cache.keys()),
            "live_count": sum(1 for p in proxy_service.price_cache.values() if p.get('live')),
            "total": len(proxy_service.price_cache),
            "prices": proxy_service.price_cache
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
