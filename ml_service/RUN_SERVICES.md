# Running ML Trading Services

## Microservice Architecture

The system now runs with independent background services:

### 1. **Crypto Price Service** (Port: N/A - Background Task)
- Fetches live prices from Binance Futures API
- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT
- Update interval: **5 seconds**
- Status: Auto-starts with main API

### 2. **Proxy Price Service** (Port: N/A - Background Task)
- Fetches live prices from Yahoo Finance
- Symbols: ES_proxy (SPY), NQ_proxy (QQQ), GC_proxy (GLD), CL_proxy (USO), ZB_proxy (TLT)
- Update interval: **10 seconds**
- Status: Auto-starts with main API

## Start the Services

```bash
cd ml_service
python -m api.main
```

The main FastAPI server will:
- Start on `http://localhost:8000`
- Auto-launch both price services in background
- Display startup logs:
  ```
  🚀 Starting price fetching microservices...
  ✅ Crypto & Proxy price services running
  ```

## Health Check

Check service status and live prices:

```bash
curl http://localhost:8000/health/prices
```

Response shows:
- Number of symbols being tracked
- Live vs delayed status for each
- Current cached prices
- Last update timestamps

## How It Works

1. **On startup**: Both services start background asyncio tasks
2. **Continuous polling**: 
   - Crypto service polls Binance every 5s
   - Proxy service polls Yahoo Finance every 10s
3. **Price caching**: All prices cached in memory
4. **API routes**: `/api/signals` endpoint reads from cache (no blocking API calls)
5. **On shutdown**: Both services gracefully stop

## Benefits

- ✅ No blocking API calls on signal generation
- ✅ Always fresh prices (5-10s latency max)
- ✅ Independent failure domains (crypto fails ≠ proxy fails)
- ✅ Easy to scale (can move to separate processes/containers)
- ✅ Health monitoring built-in

## Logs

Services log updates:
```
INFO:__main__:Updated BTCUSDT: $98234.50
INFO:__main__:Updated ES_proxy (SPY): $567.89
```
