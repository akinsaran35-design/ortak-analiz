# Ortak Analiz V4.6 - Decision Engine

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []
reasons = []

def load(name):
    try:
        data = json.loads(
            (ROOT / name).read_text(encoding="utf-8")
        )
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON")
        return data
    except Exception as exc:
        errors.append(f"{name}: {exc}")
        return {}

quality = load("data_quality.json")
validation = load("prospective_validation.json")

minimum = 500
tested = validation.get("tested", 0)

if type(tested) is not int or tested < 0:
    errors.append("Invalid tested count")
    tested = 0

if quality.get("qualityGate") != "PASS":
    reasons.append("Data quality gate failed")

if quality.get("status") != "healthy":
    reasons.append("Data quality not healthy")

if quality.get("errors") or quality.get("warnings"):
    reasons.append("Data quality issues detected")

if tested < minimum:
    reasons.append("Insufficient validated matches")

if validation.get("errors"):
    reasons.append("Model validation errors")

if validation.get("liveEnabled") is not True:
    reasons.append("Model not approved for live use")

if quality.get("liveEnabled") is not True:
    reasons.append("Live mode disabled")

report = {
    "version": "4.6",
    "updatedAt": datetime.now(timezone.utc).isoformat(),
    "decision": "PAS",
    "mode": "shadow",
    "liveEnabled": False,
    "qualityGate": quality.get("qualityGate", "PAS"),
    "testedMatches": tested,
    "minimumMatches": minimum,
    "remainingMatches": max(0, minimum - tested),
    "validationProgress": round(
        min(100, tested / minimum * 100), 2
    ),
    "maximumSelections": 2,
    "selections": [],
    "reasons": reasons,
    "errors": errors
}

(ROOT / "decision.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(
    report, ensure_ascii=False, indent=2
))
