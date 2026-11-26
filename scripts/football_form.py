"""Descriptive historical football statistics, never a betting recommendation."""
from datetime import date

def form(history,home,away,cutoff):
    if not isinstance(cutoff,date) or not home or not away or home==away:
        raise ValueError("invalid fixture")
    unique={};conflicts=set()
    for d,h,a,hg,ag in history:
        if not isinstance(d,date) or d>=cutoff or not h or not a or h==a:
            continue
        if not all(type(x) is int and x>=0 for x in (hg,ag)):continue
        k=(d,h,a)
        if k in unique and unique[k]!=(hg,ag):conflicts.add(k)
        unique[k]=(hg,ag)
    rows=[(*k,*v) for k,v in unique.items() if k not in conflicts]
    rows.sort(reverse=True)
    def team(name):
        out=[]
        for d,h,a,hg,ag in rows:
            if name==h:op,gf,ga,venue=a,hg,ag,"home"
            elif name==a:op,gf,ga,venue=h,ag,hg,"away"
            else:continue
            out.append(dict(date=d.isoformat(),opponent=op,gf=gf,ga=ga,venue=venue,
                            result="W" if gf>ga else "D" if gf==ga else "L"))
            if len(out)==5:break
        n=len(out)
        return dict(sample=n,rows=out,wins=sum(x["result"]=="W" for x in out),
            draws=sum(x["result"]=="D" for x in out),losses=sum(x["result"]=="L" for x in out),
            goalsFor=sum(x["gf"] for x in out),goalsAgainst=sum(x["ga"] for x in out))
    h2h=[dict(date=d.isoformat(),home=h,away=a,score=[hg,ag]) for d,h,a,hg,ag in rows if {h,a}=={home,away}][:5]
    return dict(version="5.06",asOfExclusive=cutoff.isoformat(),scope="available_league_history_only",
        sourceConflictsExcluded=len(conflicts),home=team(home),away=team(away),h2h=h2h,
        injuriesAvailable=False,lineupsAvailable=False,advancedStatsAvailable=False)
