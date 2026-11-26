from datetime import date
from historical_text import parse
s="""Sat Apr 5 2026
  15:00 Ilves Tampere v HJK Helsinki 3-2 (1-2)
  IFK Mariehamn v FF Jaro 0-2 (0-1)
Fri Apr 11
  KTP v Vaasan PS
  A v B 1-0 (2-0)
"""
r=parse(s,"fixture",date(2026,11,26))
assert len(r)==3
assert r[0]["ht"]==[1,2]
assert r[2]["ht"] is None
assert not parse(s,"fixture",date(2028,1,1))
