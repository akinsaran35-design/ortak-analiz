"""V6.84 research reference: V1.6-style formula on the ML capture feature snapshot.
Not a reproduction of the published V1.6 forecasts or a production model.
"""
import math
from extra_ml_prospective import digest
from extra_prospective_reliability import probabilities

def reference(features):
    def recent(side):
        venue=side+"Venue_last10"
        general=side+"_last10"
        prefix=venue if features[venue+"_matches"]>=5 else general
        n=features[prefix+"_matches"]
        gf=features[prefix+"_goals_for"]
        ga=features[prefix+"_goals_against"]
        if type(n) is not int or not 5<=n<=10 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in (gf,ga)):
            raise ValueError("invalid reference goal history")
        return n,gf,ga,prefix==venue
    hn,hgf,hga,hv=recent("home")
    an,agf,aga,av=recent("away")
    home=max(.15,min(4.,(hgf+aga)/2))
    away=max(.15,min(4.,(agf+hga)/2))
    total=home+away
    def rounded(p):return round(100*min(1,max(0,p)),1)/100
    def over(k):return rounded(1-sum(math.exp(-total)*total**i/math.factorial(i) for i in range(k+1)))
    p=dict(over15=over(1),over25=over(2),btts=rounded((1-math.exp(-home))*(1-math.exp(-away))))
    if not probabilities(p):raise ValueError("incoherent reference")
    return dict(version="6.84",probabilities=p,featureFingerprint=digest(features),
        sample=dict(home=hn,away=an),venueSpecific=dict(home=hv,away=av),
        publishedLegacyReproduction=False,productionEnabled=False)
