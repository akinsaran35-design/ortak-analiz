"""Discover openfootball text candidates without treating them as matches."""
import json
import re
from datetime import date
from pathlib import Path
from historical_data import get

REPOS=("europe","south-america","world","belgium","world.more","champions-league")
def discover(today,fetch=get):
    report={"version":"4.22","status":"discovery_only","asOf":today.isoformat(),"sources":[]}
    years={str(today.year-1),str(today.year)}
    for repo in REPOS:
        row={"repository":repo,"candidatePaths":[],"error":None}
        try:
            root=f"https://api.github.com/repos/openfootball/{repo}"
            branch=fetch(root)["default_branch"]
            tree=fetch(f"{root}/git/trees/{branch}?recursive=1")
            if tree.get("truncated"):
                raise ValueError("truncated tree")
            for entry in tree["tree"]:
                p=entry["path"]
                if entry["type"]=="blob" and p.endswith(".txt") and any(re.search(r"(?<!\\d)"+y+r"(?!\\d)",p) for y in years):
                    row["candidatePaths"].append(p)
            row["candidatePaths"].sort()
        except Exception as exc:
            row["error"]=type(exc).__name__
        report["sources"].append(row)
    report["candidateFileCount"]=sum(len(r["candidatePaths"]) for r in report["sources"])
    return report
if __name__=="__main__":
    Path("source_discovery.json").write_text(json.dumps(discover(date.today()),indent=2)+"\n")
