from datetime import date
from source_discovery import discover,REPOS
def fake(url):
    if "trees/" not in url:
        return {"default_branch":"master"}
    return {"tree":[{"type":"blob","path":"country/2026-27/1.txt"},{"type":"blob","path":"country/2010/1.txt"}]}
r=discover(date(2026,11,25),fake)
assert r["candidateFileCount"]==len(REPOS)
assert r["status"]=="discovery_only"
