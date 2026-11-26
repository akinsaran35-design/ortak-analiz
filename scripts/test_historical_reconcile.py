from historical_reconcile import reconcile
a=dict(date="2026-01-01",home="A",away="B",ft=[1,0],ht=None)
b=dict(a,home="C")
c=dict(a,ft=[2,0])
assert reconcile([a],[a,b,b])["counts"]=={"overlap":1,"conflicts":0,"unverifiedNew":1}
assert reconcile([a],[c])["counts"]["conflicts"]==1
