"""Experimental Dixon-Coles score distribution; not a calibrated betting model."""
import math

def distribution(home, away, rho=0.0):
    if not all(math.isfinite(x) for x in (home,away,rho)) or not (0<home<=4 and 0<away<=4):
        raise ValueError("invalid rates")
    corrections={(0,0):1-home*away*rho,(0,1):1+home*rho,(1,0):1+away*rho,(1,1):1-rho}
    if min(corrections.values())<0:
        raise ValueError("invalid rho")
    rows={}
    for h in range(25):
        for a in range(25):
            rows[h,a]=math.exp(-home-away)*home**h*away**a/(math.factorial(h)*math.factorial(a))*corrections.get((h,a),1)
    total=sum(rows.values())
    return {k:v/total for k,v in rows.items()}

def markets(home,away,rho=0.0):
    rows=distribution(home,away,rho)
    return {"over15":sum(v for (h,a),v in rows.items() if h+a>=2),"over25":sum(v for (h,a),v in rows.items() if h+a>=3),"btts":sum(v for (h,a),v in rows.items() if h>0 and a>0)}
