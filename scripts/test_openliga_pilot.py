from openliga_pilot import normalize
from datetime import date
m=dict(matchIsFinished=True,matchDateTime="2026-11-20T12:00",matchID=1,team1={"teamId":1},team2={"teamId":2},matchResults=[dict(resultTypeID=2,pointsTeam1=2,pointsTeam2=1)])
assert normalize([m,m],"bl1",date(2026,11,26))[0]["ft"]==[2,1]
assert len(normalize([m,m],"bl1",date(2026,11,26)))==1
assert normalize([dict(m,matchIsFinished=False)],"bl1",date(2026,11,26))==[]
