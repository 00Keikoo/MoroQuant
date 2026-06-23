import json
import glob
import os

PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "HYPEUSDT", "ZECUSDT", "ADAUSDT", "SUIUSDT", "LINKUSDT", "XRPUSDT", "LTCUSDT"]
TIMEFRAMES = ["1h", "4h"]

active = {}

for pair in PAIRS:
    active[pair] = {}

    for tf in TIMEFRAMES:
        files = sorted(
            glob.glob(f"storage/models/production/{pair}_{tf}*.pkl"),
            key=os.path.getmtime,
            reverse=True
        )

        files = [f for f in files if "calibration" not in f]

        if files:
            active[pair][tf] = os.path.basename(files[0])

with open("storage/models/active_models.json", "w") as f:
    json.dump(active, f, indent=2)

print("active_models.json updated successfully")
