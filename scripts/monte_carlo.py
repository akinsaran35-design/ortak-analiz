"""Research-only Monte Carlo check of the Dixon-Coles score distribution."""
import random
import math
from dixon_coles import distribution

def simulate(home, away, rho=0.0, trials=20000, seed=42):
    if not isinstance(trials,int) or not 100<=trials<=1000000:
        raise ValueError("invalid trials")
    dist=distribution(home,away,rho)
    scores=random.Random(seed).choices(list(dist),weights=list(dist.values()),k=trials)
    counts={"over15":0,"over25":0,"btts":0}
    for h,a in scores:
        counts["over15"]+=h+a>=2
        counts["over25"]+=h+a>=3
        counts["btts"]+=h>0 and a>0
    return {"trials":trials,"seed":seed,"markets":{k:{"probability":v/trials,"sampling_se":math.sqrt((v/trials)*(1-v/trials)/trials)} for k,v in counts.items()}}
