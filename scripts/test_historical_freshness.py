from historical_freshness import report
from datetime import date
r=report([dict(date="2026-11-25",source="a"),dict(date="2026-09-01",source="a"),dict(date="2026-11-26",source="a")],date(2026,11,26))
assert r["total"]["recent"]=={"7":1,"30":1,"61":1}
assert r["total"]["latest"]=="2026-11-25"
assert report([],date(2026,11,26))["total"]["latest"] is None
