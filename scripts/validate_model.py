# Ortak Analiz V4.3 - Independent validation
import json
import math
from datetime import date
from pathlib import Path

START = date(2026, 11, 25)
ROOT = Path(__file__).resolve().parent.parent

from backtest import (
    LEAGUES, seasons, fetch, team,
    predict, weighted_predict
)

rows = []
errors = []

for league in LEAGUES:
    matches = {}

    for season in seasons:
        try:
            for m in fetch(season, league):
                d = date.fromisoformat(m["date"][:10])
                h = team(m.get("team1"))
                a = team(m.get("team2"))
                score = m.get("score")
                ft = score.get("ft") if isinstance(score, dict) else None

                if (
                    d < date.today()
                    and h and a
                    and isinstance(ft, list)
                    and len(ft) == 2
                    and all(type(x) is int and x >= 0 for x in ft)
                ):
                    matches[(d, h, a)] = tuple(ft)

        except Exception as exc:
            errors.append(f"{league}/{season}: {exc}")

    history = sorted(
        (d, h, a, s[0], s[1])
        for (d, h, a), s in matches.items()
    )

    for d, h, a, hg, ag in history:
        if d < START:
            continue

        past = [x for x in history if x[0] < d]

        old = predict(past, h, a)
        new = weighted_predict(past, h, a)

        if old is None or new is None:
            continue

        baseline = sum(
            int(x[3] + x[4] >= 3)
            for x in past
        ) / len(past)

        rows.append({
            "date": d.isoformat(),
            "league": league,
            "home": h,
            "away": a,
            "old": old[1],
            "candidate": new[1],
            "baseline": baseline,
            "actual": int(hg + ag >= 3)
        })

n = len(rows)

report = {
    "version": "4.3",
    "market": "2.5 Ust",
    "candidate": "weightedBrier",
    "validationStart": START.isoformat(),
    "updatedAt": date.today().isoformat(),
    "tested": n,
    "minimumMatches": 500,
    "liveEnabled": False,
    "status": "collecting_data",
    "errors": errors
}

if n:
    scores = {
        key: sum(
            (r[key] - r["actual"]) ** 2
            for r in rows
        ) / n
        for key in ("old", "candidate", "baseline")
    }

    report["scores"] = scores

    report["improvement"] = (
        scores["baseline"] - scores["candidate"]
    )

    if n >= 500 and not errors:
        eligible = (
            scores["candidate"] < scores["old"]
            and report["improvement"] >= 0.001
        )

        report["status"] = (
            "review_required"
            if eligible else "not_qualified"
        )

(ROOT / "validation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(json.dumps(report, ensure_ascii=False, indent=2))
