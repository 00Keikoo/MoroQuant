"""
Model Artifact Filename Parser
"""

from pathlib import Path

def parse_model_filename(path: str):

	name = Path(path).stem

	parts = name.split("_")

	try:
		# normal crypto
		if len(parts) >= 5 and parts[1] in ["1h", "4h", "15m", "1d"]:
			return {
				"symbol": parts[0],
				"timeframe": parts[1],
				"model_type": parts[2],
				"trained_at": "_".join(parts[3:5]),
				"asset_class": "crypto"
			}

		# proxy macro
		elif len(parts) >= 6 and parts[1] == "proxy":
			return {
				"symbol": parts[0],
				"asset_class": "proxy",
				"timeframe": parts[2],
				"model_type": parts[3],
				"trained_at": "_".join(parts[4:6])
			}

		else:
			raise ValueError(
				f"Unknown model filename schema: {name}"
			)

	except IndexError:
		raise ValueError(
			f"Malformed model filename: {name}"
		)
