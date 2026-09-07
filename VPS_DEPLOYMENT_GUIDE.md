# MoroQuant Production API Exposure Remediation - VPS Deployment Guide

**Date:** 2026-09-07
**Status:** Code changes complete, awaiting VPS deployment
**Operator:** CTO/zafka

---

## LOCAL CODE CHANGES COMPLETED ✓

All repository code changes have been implemented and tested:

### Frontend API Migration (4 files)
- ✓ `lib/api/ml-trading.ts` - Browser uses `/ml-api`, SSR uses `localhost:8000/api`
- ✓ `lib/api/system-status.ts` - Browser uses `/ml-api`, SSR uses `localhost:8000/api`
- ✓ `lib/services/terminalService.ts` - Browser uses `/ml-api`, SSR uses `localhost:8000/api`
- ✓ `lib/services/performanceService.ts` - Browser uses `/ml-api`, SSR uses `localhost:8000/api`

### Uvicorn Configuration (3 files)
- ✓ `ml_service/start.sh` - Changed `--host 0.0.0.0` → `--host 127.0.0.1`
- ✓ `ml_service/production-startup.service` - Changed `--host 0.0.0.0` → `--host 127.0.0.1`
- ✓ `ml_service/api/main.py` - Changed `host="0.0.0.0"` → `host="127.0.0.1"`

### Build Verification
- ✓ Next.js production build: **SUCCESS**
- ✓ No browser-side `:8000` references remain in API clients
- ✓ All `0.0.0.0` bindings changed to `127.0.0.1`

---

## VPS DEPLOYMENT SEQUENCE

Execute these steps **ON THE PRODUCTION VPS** as user `zafka`.

### PHASE 1: NGINX CONFIGURATION

#### Step 1.1: Verify nginx source path
```bash
readlink -f /etc/nginx/sites-enabled/qualitrack
```

**Expected output:** `/etc/nginx/sites-available/qualitrack` (or similar)

#### Step 1.2: Backup current nginx configuration
```bash
sudo cp /etc/nginx/sites-available/qualitrack /etc/nginx/sites-available/qualitrack.backup.$(date +%Y%m%d_%H%M%S)
```

#### Step 1.3: Edit nginx configuration
```bash
sudo nano /etc/nginx/sites-available/qualitrack
```

**Add this block BEFORE the existing `location /` block:**

```nginx
    location /ml-api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_connect_timeout 3s;
        proxy_read_timeout 30s;
        proxy_next_upstream error timeout http_502 http_503 http_504;
        proxy_next_upstream_tries 2;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
```

**IMPORTANT:**
- Use `127.0.0.1` NOT `127.0.1`
- Trailing slashes are intentional: `/ml-api/` and `/api/`
- Do NOT modify the existing `location /` Qualitrack block

#### Step 1.4: Test nginx configuration
```bash
sudo nginx -t
```

**Expected output:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**If test fails:** Restore backup and investigate syntax error.

#### Step 1.5: Reload nginx
```bash
sudo nginx -s reload
```

#### Step 1.6: Verify nginx proxy works
```bash
# Test ML API through nginx
curl -i http://127.0.0.1/ml-api/trading/mode

# Test database info
curl -i http://127.0.0.1/ml-api/db/info

# Verify Qualitrack unchanged
curl -i http://127.0.0.1/
```

**Expected:** All return HTTP 200 with valid responses.

**If nginx proxy fails, STOP. Do not proceed to Phase 2.**

---

### PHASE 2: DEPLOY FRONTEND CHANGES

#### Step 2.1: Navigate to repository
```bash
cd ~/trade-dashboard  # Or actual production path
```

#### Step 2.2: Pull code changes
```bash
git pull origin quant-research  # Or appropriate branch
```

**Verify these files changed:**
- `lib/api/ml-trading.ts`
- `lib/api/system-status.ts`
- `lib/services/terminalService.ts`
- `lib/services/performanceService.ts`

#### Step 2.3: Install dependencies (if needed)
```bash
npm install
```

#### Step 2.4: Build frontend
```bash
npm run build
```

**Expected:** Build succeeds with no errors.

#### Step 2.5: Restart Next.js frontend
```bash
# If using PM2:
pm2 restart moroquant-frontend  # Or your actual PM2 process name

# Verify it's running:
pm2 status
```

---

### PHASE 3: FRONTEND VERIFICATION GATE

**CRITICAL: Do NOT proceed to Phase 4 until ALL these checks PASS.**

#### Step 3.1: Browser network inspection

Open browser and navigate to:
- `http://<production-hostname>/terminal`
- `http://<production-hostname>/dashboard`

Open browser DevTools → Network tab and verify:
- ✓ Requests go to `/ml-api/trading/mode` NOT `:8000/api/trading/mode`
- ✓ Requests go to `/ml-api/paper/account/live` NOT `:8000/api/paper/account/live`
- ✓ All ML API requests use `/ml-api/*` namespace
- ✓ No 404 errors
- ✓ No CORS errors
- ✓ Trading mode displays correctly
- ✓ Account equity/balance displays
- ✓ Performance stats load

#### Step 3.2: Test critical features

**Terminal page:**
- ✓ Trading mode displays (PAPER/LIVE/OFF)
- ✓ Account equity shows value
- ✓ Open positions table loads (or shows empty state)
- ✓ Recent trades panel loads (or shows empty state)
- ✓ Performance stats display
- ✓ Model intelligence panel loads

**Dashboard page:**
- ✓ Equity chart renders
- ✓ Model health indicators load
- ✓ KPI cards display

**Trading features:**
- ✓ Trading mode switch works (toggle and verify POST succeeds)
- ✓ Emergency stop button accessible

#### Step 3.3: Check nginx access logs
```bash
sudo tail -f /var/log/nginx/access.log | grep ml-api
```

**Expected:** See requests to `/ml-api/*` endpoints with 200 status codes.

#### Step 3.4: Check ML service logs
```bash
pm2 logs moroquant-api --lines 50
```

**Expected:** No errors, requests being served normally.

### ⚠️ GATE CHECKPOINT

**If ANY frontend feature fails or still uses `:8000`, STOP HERE.**

Debug the issue before proceeding. Possible rollback:
```bash
# Revert to previous frontend version
git checkout HEAD~1 -- lib/api/ lib/services/
npm run build
pm2 restart moroquant-frontend
```

---

### PHASE 4: UVICORN LOCKDOWN (DESTRUCTIVE)

**ONLY proceed if Phase 3 gate PASSED completely.**

#### Step 4.1: Verify current ML service binding
```bash
sudo ss -lntp | grep ':8000'
```

**Current expected:** `0.0.0.0:8000` (public)

#### Step 4.2: Verify PM2 is managing ML service
```bash
pm2 list | grep moroquant-api
```

**Confirm:** Process exists and is using `ml_service/start.sh`

#### Step 4.3: Restart ML service (applies new localhost-only binding)
```bash
pm2 restart moroquant-api
```

#### Step 4.4: Verify new binding
```bash
sudo ss -lntp | grep ':8000'
```

**New expected:** `127.0.0.1:8000` (localhost only)

**If still shows `0.0.0.0:8000`, investigate:**
```bash
# Check what command PM2 is actually running
pm2 info moroquant-api

# Verify start.sh was updated
cat ml_service/start.sh | grep "host"
```

#### Step 4.5: Verify internal API still works
```bash
curl -i http://127.0.0.1:8000/api/trading/mode
```

**Expected:** HTTP 200, valid JSON response.

#### Step 4.6: Verify nginx proxy still works
```bash
curl -i http://127.0.0.1/ml-api/trading/mode
```

**Expected:** HTTP 200, valid JSON response.

---

### PHASE 5: SECURITY VERIFICATION

#### Step 5.1: Test external port 8000 access

**From your local machine (NOT the VPS):**
```bash
curl --max-time 5 http://<PRODUCTION_VPS_PUBLIC_IP>:8000/api/trading/mode
```

**Expected:** Connection refused or timeout (NOT a valid API response).

#### Step 5.2: Verify port 80 still works externally
```bash
curl -i http://<PRODUCTION_VPS_PUBLIC_IP>/ml-api/trading/mode
```

**Expected:** HTTP 200, valid JSON response.

#### Step 5.3: Monitor connection count
```bash
# Check active connections to port 8000
sudo ss -H -nt state established '( sport = :8000 )' | wc -l
```

**Expected:** Low number (only internal connections).

Previously during incident: **22 connections** (above limit of 20).

#### Step 5.4: Monitor for errors (5-10 minutes)
```bash
# Watch nginx logs
sudo tail -f /var/log/nginx/access.log | grep -E "(502|503|504)"

# Watch PM2 logs
pm2 logs moroquant-api --lines 20 --timestamp
```

**Expected:** No 502/503 errors, no connection saturation.

---

### PHASE 6: FINAL VERIFICATION

#### Step 6.1: Browser retest (from external network)

Navigate to production site and verify:
- ✓ Terminal loads without errors
- ✓ Dashboard loads without errors
- ✓ Trading mode displays correctly
- ✓ All data loads normally
- ✓ No console errors
- ✓ Network tab shows `/ml-api/*` requests only

#### Step 6.2: Document listening ports
```bash
sudo ss -lntp | grep -E ':(80|8000|5144)'
```

**Expected output:**
```
0.0.0.0:80    nginx
127.0.0.1:8000  python (uvicorn)
*:5144        (Qualitrack backend)
```

---

## ROLLBACK PROCEDURES

### If frontend issues occur (before Phase 4):
```bash
cd ~/trade-dashboard
git checkout HEAD~1 -- lib/api/ lib/services/
npm run build
pm2 restart moroquant-frontend
```

### If ML API becomes unreachable (after Phase 4):
```bash
# Emergency: revert Uvicorn to public binding
cd ~/trade-dashboard/ml_service
nano start.sh
# Change: --host 127.0.0.1 back to --host 0.0.0.0
pm2 restart moroquant-api
```

### If nginx causes issues:
```bash
# Restore backup
sudo cp /etc/nginx/sites-available/qualitrack.backup.* /etc/nginx/sites-available/qualitrack
sudo nginx -t
sudo nginx -s reload
```

---

## POST-DEPLOYMENT MONITORING

### First 30 minutes:
```bash
# Monitor connection count every 5 minutes
watch -n 300 'sudo ss -H -nt state established "( sport = :8000 )" | wc -l'

# Watch for 503 errors
sudo tail -f /var/log/nginx/access.log | grep -E " 503 "
```

### First 24 hours:
- Check connection count stays < 20
- Verify no 503 errors in nginx logs
- Confirm browser clients use `/ml-api` exclusively
- Monitor PM2 process stability

---

## VERIFICATION CHECKLIST

```
[ ] Phase 1: nginx proxy configured and tested
[ ] Phase 2: Frontend deployed and built successfully
[ ] Phase 3: Browser uses /ml-api, all features work
[ ] Phase 4: Uvicorn bound to 127.0.0.1:8000 only
[ ] Phase 5: External :8000 blocked, /ml-api accessible
[ ] Phase 6: All production features verified working
[ ] Monitoring: No 503 errors, connections < 20
```

---

## DEPLOYMENT DEBT (Not Blockers)

1. **Stale systemd path** in `ml_service/production-startup.service:8`
   - Contains `/home/zafka/trade-dashboard/ml_service`
   - Verify this matches actual production path
   - Not blocking if PM2 is the actual process manager

2. **Polling architecture** - Multiple components create independent 30s intervals
   - Not addressed in this remediation
   - Recommend separate task to consolidate polling

3. **PM2 ecosystem config** - No explicit `ecosystem.config.js` found
   - Document actual PM2 configuration for reproducibility

---

## SUPPORT INFORMATION

If issues occur during deployment:
- Review Phase 3 verification gate carefully
- Check browser DevTools Network tab for actual request URLs
- Verify nginx proxy configuration syntax
- Confirm PM2 is using updated `start.sh`
- Test internal API access before external

For questions or issues, contact CTO/zafka.

---

**END OF DEPLOYMENT GUIDE**
