"""Conditional score scenarios, not a fitted or deployed live prediction model."""
import math
from collections import defaultdict

def poisson(rate):
    p=math.exp(-rate)
    rows=[p]
    for k in range(1,40):
        p*=rate/k
        rows.append(p)
    total=sum(rows)
    return [v/total for v in rows]

def scenario(score,minute,home_rate,away_rate):
    """Independent remaining goals, fixed full-match rates; regulation only."""
    if not isinstance(score,(list,tuple)) or len(score)!=2 or any(type(x) is not int or not 0<=x<=30 for x in score):
        raise ValueError("invalid score")
    if type(minute) is not int or not 0<=minute<=90:raise ValueError("invalid minute")
    if any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=4 for x in (home_rate,away_rate)):
        raise ValueError("invalid rates")
    fraction=(90-minute)/90
    remaining=[home_rate*fraction,away_rate*fraction]
    scores=defaultdict(float)
    for h,p in enumerate(poisson(remaining[0])):
        for a,q in enumerate(poisson(remaining[1])):
            scores[(score[0]+h,score[1]+a)]+=p*q
    def prob(fn):return min(1.0,max(0.0,math.fsum(v for (h,a),v in scores.items() if fn(h,a))))
    return dict(mode="conditional_research_scenario",modelCalibrated=False,predictionsEnabled=False,decision="PAS",
                minute=minute,score=list(score),inputRates=[home_rate,away_rate],remainingRates=remaining,
                homeWin=prob(lambda h,a:h>a),draw=prob(lambda h,a:h==a),awayWin=prob(lambda h,a:h<a),
                over15=prob(lambda h,a:h+a>=2),over25=prob(lambda h,a:h+a>=3),btts=prob(lambda h,a:h>0 and a>0),
                assumptions=["independent Poisson","constant goal rates","no added time","no live-statistic coefficients"])

