from models.governance import compare_and_promote

models = [
    ("ADAUSDT", "1h", "storage/models/candidates/ADAUSDT_1h_lightgbm_20260623_081343.pkl"),
    ("ADAUSDT", "4h", "storage/models/candidates/ADAUSDT_4h_lightgbm_20260623_081628.pkl"),

    ("ZECUSDT", "1h", "storage/models/candidates/ZECUSDT_1h_lightgbm_20260623_090633.pkl"),
    ("ZECUSDT", "4h", "storage/models/candidates/ZECUSDT_4h_xgboost_20260623_090908.pkl"),

    ("SUIUSDT", "1h", "storage/models/candidates/SUIUSDT_1h_lightgbm_20260623_092312.pkl"),
    ("SUIUSDT", "4h", "storage/models/candidates/SUIUSDT_4h_xgboost_20260623_092703.pkl"),

    ("LINKUSDT", "1h", "storage/models/candidates/LINKUSDT_1h_lightgbm_20260623_083329.pkl"),
    ("LINKUSDT", "4h", "storage/models/candidates/LINKUSDT_4h_xgboost_20260623_083629.pkl"),

    ("XRPUSDT", "1h", "storage/models/candidates/XRPUSDT_1h_xgboost_20260623_094112.pkl"),
    ("XRPUSDT", "4h", "storage/models/candidates/XRPUSDT_4h_xgboost_20260623_094543.pkl"),

    ("LTCUSDT", "1h", "storage/models/candidates/LTCUSDT_1h_xgboost_20260623_085013.pkl"),
    ("LTCUSDT", "4h", "storage/models/candidates/LTCUSDT_4h_lightgbm_20260623_085248.pkl"),
]

for symbol, tf, path in models:
    print(f"\n{'='*80}")
    print(f"PROMOTING {symbol} {tf}")
    print('='*80)

    result = compare_and_promote(
        candidate_path=path,
        symbol=symbol,
        timeframe=tf,
        improvement_threshold=1.00  # cukup lebih baik sedikit
    )

    print(result)
