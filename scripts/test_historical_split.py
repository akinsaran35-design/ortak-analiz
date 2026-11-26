from datetime import date,timedelta
from historical_split import split
d=date(2026,11,26)
rows=[{"date":(d-timedelta(days=i)).isoformat()} for i in range(367)]
g,r=split(rows,d)
assert r["counts"]=={"train":243,"validation":61,"test":61}
assert r["rejected"]==2
assert max(x["date"] for x in g["train"])<min(x["date"] for x in g["validation"])
assert max(x["date"] for x in g["validation"])<min(x["date"] for x in g["test"])
