"""
Feature Schema Fingerprint
Sprint 3.9D-4
"""

import hashlib
import json

def feature_fingerprint(features):

	normalized = sorted(features)

	payload = json.dumps(
		normalized,
		separators=(",", ":")
	)

	return hashlib.sha256(
		payload.encode("utf-8")
	).hexdigest()
