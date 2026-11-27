"""Independent public competition catalog, not fixture verification."""
import json
from pathlib import Path
from results_source_pilot import read
URL="https://api.football-data.org/v4/competitions"
def parse(payload):
    rows=payload["competitions"]
    if not isinstance(rows,list):raise ValueError("catalog schema")
    result={}
    for row in rows:
        ident=row["id"]; name=row["name"]; area=row["area"]["name"]
        if type(ident)!=int or not isinstance(name,str) or not name.strip() or not isinstance(area,str) or not area.strip() or ident in result:raise ValueError("invalid competition identity")
        result[ident]=dict(id=ident,name=name,area=area,code=row.get("code"),plan=row.get("plan"))
    return list(result.values())
if __name__=="__main__":
    rows=parse(json.loads(read(URL)))
    Path("independent_catalog.json").write_text(json.dumps(dict(version="5.66",source=URL,mode="catalog_only",fixtureAccessVerified=False,rows=rows),ensure_ascii=False,indent=2))
    print("Catalog count:",len(rows))
    print("Catalog areas:",sorted({r["area"] for r in rows}))
    assert rows
