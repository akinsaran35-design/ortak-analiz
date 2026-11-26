from historical_baseline import evaluate
from datetime import date
assert evaluate([],date(2026,11,26))["metrics"]=={}

from historical_baseline import market_metrics
m=market_metrics([(0.8,1),(0.75,0),(0.4,0)])
assert m["selected"]==2 and m["hits"]==1 and m["hitRate"]==0.5
assert m["accuracy"]==2/3
assert market_metrics([(0.4,1)])["hitRate"] is None
