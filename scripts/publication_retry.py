"""Permit publication retry only over isolated research ledger changes."""
import json,subprocess,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path

ALLOWED={"extra_league_prospective_ledger.json","extra_ml_prospective_ledger.json",
         "extra_ml_frozen_manifest.json","extra_ml_frozen.cbm"}
MAX_AGE=timedelta(minutes=30)

def git(*args):
    return subprocess.check_output(["git",*args])

def safe_paths(paths):
    return bool(paths) and paths<=ALLOWED

def fresh_reports(now,root=Path(".")):
    try:
        for path in ("daily.json","snapshot_integrity.json"):
            doc=json.loads((root/path).read_text(encoding="utf-8"))
            t=datetime.fromisoformat(doc["updatedAt"].replace("Z","+00:00"))
            if t.tzinfo is None or not timedelta(0)<=now-t<=MAX_AGE:
                return False
            if path=="snapshot_integrity.json" and (doc.get("status")!="PASS" or doc.get("errors")!=[]):
                return False
        return True
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return False

def permitted(base,remote,now):
    if not fresh_reports(now):
        return False
    if subprocess.run(["git","merge-base","--is-ancestor",base,remote],check=False).returncode!=0:
        return False
    changed={p.decode("utf-8") for p in git("diff","--no-renames","--name-only","-z",base,remote).split(b"\0") if p}
    # Never rebase over a path included in the publication commit itself.
    staged={p.decode("utf-8") for p in git("diff","--no-renames","--name-only","-z",base,"HEAD").split(b"\0") if p}
    return safe_paths(changed) and not changed&staged

if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit(2)
    allowed=permitted(sys.argv[1],sys.argv[2],datetime.now(timezone.utc))
    print("Publication retry:", "isolated research files only" if allowed else "refused; rerun fresh pipeline")
    raise SystemExit(0 if allowed else 1)
