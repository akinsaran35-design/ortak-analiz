"""Research-only exact-score probabilities."""
from dixon_coles import distribution

def score_report(home, away, rho=0.0):
    p=distribution(home,away,rho)
    ranked=sorted(p.items(),key=lambda item:(-item[1],item[0]))
    return {"topScores":[{"home":h,"away":a,"probability":v} for (h,a),v in ranked[:5]],
            "homeWin":sum(v for (h,a),v in p.items() if h>a),
            "draw":sum(v for (h,a),v in p.items() if h==a),
            "awayWin":sum(v for (h,a),v in p.items() if h<a),
            "expectedHome":sum(h*v for (h,a),v in p.items()),
            "expectedAway":sum(a*v for (h,a),v in p.items())}
