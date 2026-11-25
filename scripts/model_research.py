"""Daily research comparison, using existing model rates, not independent forecasts."""
import json
from pathlib import Path
from datetime import datetime, timezone
from dixon_coles import markets
from monte_carlo import simulate

def build(data):
    rows=[]
    rejected=0
    for c in data.get("candidates",[]):
        try:
            h=float(c["expectedGoals"]["home"])
            a=float(c["expectedGoals"]["away"])
            rows.append({"date":c["date"],"league":c["league"],"match":c["match"],
                         "expectedGoals":{"home":h,"away":a},
                         "poisson":markets(h,a,0),
                         "experimentalDixonColes":markets(h,a,-0.05),
                         "simulation":simulate(h,a,-0.05)})
        except (KeyError,TypeError,ValueError,OverflowError):
            rejected+=1
    return {"version":"4.20","mode":"research_only","updatedAt":datetime.now(timezone.utc).isoformat(),
            "sourceUpdatedAt":data.get("updatedAt"),"rho":-0.05,"rhoFitted":False,
            "modelCalibrated":False,"realBettingEnabled":False,"rejected":rejected,"rows":rows}

if __name__=="__main__":
    data=json.loads(Path("daily.json").read_text(encoding="utf-8"))
    Path("model_research.json").write_text(json.dumps(build(data),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
