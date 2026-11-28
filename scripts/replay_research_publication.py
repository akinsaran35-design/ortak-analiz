"""CI-only replay on the original snapshot date; never publish a refreshed timestamp."""
import json
from pathlib import Path
from datetime import datetime
from h2h_history_research import build as h2h
from football_context_research import build as context
from historical_metric_coverage import build as coverage
from chronological_statistics_research import build as validation
from football_context_manifest import main as manifest

def run():
    daily_path=Path("daily.json")
    daily=json.loads(daily_path.read_text(encoding="utf-8"))
    original_stamp=daily["updatedAt"]
    snapshot_time=datetime.fromisoformat(original_stamp)
    if snapshot_time.tzinfo is None:
        raise ValueError("snapshot must include timezone")
    # Work on checkout-local data only. All historical inputs use original cutoff.
    reports={"h2h_history_research.json":h2h(daily,snapshot_time),
             "football_context_research.json":context(daily,snapshot_time),
             "historical_metric_coverage.json":coverage(snapshot_time),
             "chronological_statistics_research.json":validation(snapshot_time)}
    if daily["updatedAt"]!=original_stamp:
        raise ValueError("snapshot timestamp changed")
    for name,report in reports.items():
        Path(name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    daily_path.write_text(json.dumps(daily,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    manifest()
    print("CI historical replay only; original snapshot:",original_stamp)

if __name__=="__main__":
    run()
