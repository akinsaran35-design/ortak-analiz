"""Canonical historical identity fallback for new research forecasts only."""
from prospective_capture_window import identity
from collections import Counter

def canonical_history(league,history,today):
    rows={};conflicts=set();invalid=0
    for day,h,a,hg,ag in history:
        if day>=today:continue
        try:
            _,_,hk,ak=identity(league,day.isoformat(),h,a)
            if not all(type(x) is int and x>=0 for x in (hg,ag)):raise ValueError("score")
        except (ValueError,KeyError,TypeError):
            invalid+=1;continue
        key=(day,hk,ak);score=(hg,ag)
        if key in rows and rows[key]!=score:conflicts.add(key)
        rows[key]=score
    clean=sorted((*key,*score) for key,score in rows.items() if key not in conflicts)
    return clean,dict(conflicts=len(conflicts),invalid=invalid)

def team_counts(history,h,a):
    return {side:sum(t in (x[1],x[2]) for x in history) for side,t in (("home",h),("away",a))}
