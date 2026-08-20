"""FastAPI main application for ML trading system."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import asyncio
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.api.routes import router
from ml_service.api.explorer_routes import router as explorer_router
from ml_service.lab.experiments.api import router as experiment_router
from ml_service.research.model_registry.api import router as model_registry_router
from ml_service.research.research_dashboard.api import router as research_router
from ml_service.research.orchestrator_api import router as orchestrator_router
from ml_service.research.registry_api.router import router as registry_router
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
app.include_router(explorer_router)
app.include_router(experiment_router, prefix="/api/lab")
app.include_router(model_registry_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(orchestrator_router)
app.include_router(registry_router)

dashboard_path = Path(__file__).parent.parent / "dashboard.html"

@app.on_event("startup")
async def startup_event():
    """Initialize price services and auto-retrain scheduler."""
    import threading
    from scheduler import trade_sync_job

    get_crypto_service()
    get_proxy_service()
    print("✅ Price services ready (on-demand fetching)")

    start_scheduler()
    print("✅ Auto-retrain scheduler started (runs every 24h)")

    # Fire one trade sync immediately so recently closed positions appear
    # without waiting for the next scheduled run. Run in a daemon thread
    # so it never blocks server startup.
    def _initial_sync():
        try:
            print("🔄 Running initial trade sync on startup...")
            trade_sync_job()
            print("✅ Initial trade sync complete")
        except Exception as e:
            print(f"⚠️  Initial trade sync failed: {e}")

        # Capture an initial Binance equity snapshot so the equity-history
        # chart has at least one point without waiting for the 5-min job.
        try:
            from scheduler import account_equity_snapshot_job
            print("📸 Capturing initial account equity snapshot...")
            account_equity_snapshot_job()
            print("✅ Initial account equity snapshot complete")
        except Exception as e:
            print(f"⚠️  Initial account equity snapshot failed: {e}")

    threading.Thread(target=_initial_sync, daemon=True).start()

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
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        limit_concurrency=20,
        timeout_keep_alive=5,
        workers=1
    )
