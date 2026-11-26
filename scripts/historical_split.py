"""Chronological research split; never train on future results."""
from datetime import date,timedelta
import json
from pathlib import Path

def split(rows,as_of):
    start=as_of-timedelta(days=365)
    first=start+timedelta(days=243)
    second=start+timedelta(days=304)
    groups={"train":[],"validation":[],"test":[]}
    rejected=0
    for row in rows:
        try: d=date.fromisoformat(row["date"])
        except (ValueError,KeyError,TypeError):
            rejected+=1
            continue
        if not start<=d<as_of:
            rejected+=1
            continue
        groups["train" if d<first else "validation" if d<second else "test"].append(row)
    return groups,dict(status="research_only",modelCalibrated=False,realBettingEnabled=False,asOf=as_of.isoformat(),validationStart=first.isoformat(),testStart=second.isoformat(),counts={k:len(v) for k,v in groups.items()},rejected=rejected)

if __name__=="__main__":
    archive=json.loads(Path("historical_data.json").read_text())
    _,report=split(archive["matches"],date.fromisoformat(archive["asOf"]))
    Path("historical_split.json").write_text(json.dumps(report,indent=2))
    print(report)
