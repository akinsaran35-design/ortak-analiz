"""Conservative cross-provider fixture matching; no automatic settlement."""
from datetime import datetime
import unicodedata
def norm(s):
    return " ".join(unicodedata.normalize("NFKC",s).casefold().split())
# League-scoped observed aliases from V5.72; not verified provider team IDs.
ALIASES={"en.1":{"Nottingham Forest FC":"Nottingham Forest","Chelsea FC":"Chelsea","Leeds United FC":"Leeds United","Coventry City FC":"Coventry City","Manchester United FC":"Manchester United","Brentford FC":"Brentford","Ipswich Town FC":"Ipswich Town","Aston Villa FC":"Aston Villa"},"en.2":{"Southampton FC":"Southampton","Middlesbrough FC":"Middlesbrough","Blackburn Rovers FC":"Blackburn Rovers","Charlton Athletic FC":"Charlton Athletic","Lincoln City FC":"Lincoln City","Wolverhampton Wanderers FC":"Wolverhampton Wanderers","Preston North End FC":"Preston North End","Norwich City FC":"Norwich City","Birmingham City FC":"Birmingham City","Bolton Wanderers FC":"Bolton Wanderers","Derby County FC":"Derby County","Watford FC":"Watford","Millwall FC":"Millwall","Burnley FC":"Burnley","Queens Park Rangers FC":"Queens Park Rangers","Sheffield United FC":"Sheffield United","West Bromwich Albion FC":"West Bromwich Albion","Bristol City FC":"Bristol City","West Ham United FC":"West Ham United","Stoke City FC":"Stoke City","Portsmouth FC":"Portsmouth","Wrexham AFC":"Wrexham"},"de.1":{"SV Werder Bremen":"Werder Bremen","1. FC Köln":"FC Cologne","SV 07 Elversberg":"SV Elversberg","Hamburger SV":"Hamburg SV","FC Bayern München":"Bayern Munich","1. FSV Mainz 05":"Mainz","FC Schalke 04":"Schalke 04"},"es.1":{"Levante UD":"Levante","Real Racing Club de Santander":"Racing Santander","Real Betis Balompié":"Real Betis","Rayo Vallecano de Madrid":"Rayo Vallecano","Málaga CF":"Málaga","Elche CF":"Elche","Club Atlético de Madrid":"Atlético Madrid","Real Madrid CF":"Real Madrid","Deportivo Alavés":"Alavés"},"it.1":{"Venezia FC":"Venezia","Bologna FC 1909":"Bologna","Frosinone Calcio":"Frosinone","Parma Calcio 1913":"Parma","Torino FC":"Torino","SS Lazio":"Lazio","FC Internazionale Milano":"Internazionale","Genoa CFC":"Genoa"},"fr.1":{"Stade Brestois 29":"Brest","Angers SCO":"Angers","Racing Club de Lens":"Lens","RC Strasbourg Alsace":"Strasbourg","Le Mans FC":"Le Mans","Lille OSC":"Lille","OGC Nice":"Nice","ES Troyes AC":"Troyes","Paris Saint-Germain FC":"Paris Saint-Germain","FC Lorient":"Lorient"},"nl.1":{"Willem II Tilburg":"Willem II","SBV Excelsior":"Excelsior","Telstar 1963":"Telstar","PSV":"PSV Eindhoven","SC Cambuur-Leeuwarden":"SC Cambuur"},"pt.1":{"CS Marítimo":"Maritimo","CD Nacional":"C.D. Nacional","FC Arouca":"Arouca","Rio Ave FC":"Rio Ave","Moreirense FC":"Moreirense","CD Santa Clara":"Santa Clara","Académico de Viseu FC":"Académico de Viseu","FC Alverca":"Alverca","Vitória SC":"Vitória de Guimaraes","CF Estrela da Amadora":"Estrela"}}
for league,names in {"en.1":{"Manchester City FC":"Manchester City","Fulham FC":"Fulham","Newcastle United FC":"Newcastle United","Arsenal FC":"Arsenal"},"es.1":{"RCD Espanyol de Barcelona":"Espanyol","RC Deportivo La Coruña":"Deportivo","Valencia CF":"Valencia","Sevilla FC":"Sevilla","RC Celta de Vigo":"Celta Vigo"},"it.1":{"SSC Napoli":"Napoli"},"nl.1":{"NEC":"NEC Nijmegen"}}.items():
    ALIASES.setdefault(league,{}).update(names)
for league,names in {"en.1":{"Sunderland AFC":"Sunderland","Crystal Palace FC":"Crystal Palace","Tottenham Hotspur FC":"Tottenham Hotspur"},"en.2":{"Cardiff City FC":"Cardiff City","Swansea City AFC":"Swansea City"},"de.1":{"Bayer 04 Leverkusen":"Bayer Leverkusen","TSG 1899 Hoffenheim":"TSG Hoffenheim"},"it.1":{"Como 1907":"Como","Cagliari Calcio":"Cagliari","US Lecce":"Lecce"},"fr.1":{"AS Monaco FC":"AS Monaco","Toulouse FC":"Toulouse","Olympique Lyonnais":"Lyon"},"nl.1":{"SC Heerenveen":"Heerenveen"}}.items():
    ALIASES.setdefault(league,{}).update(names)
ALIASES={league:{norm(k):norm(v) for k,v in names.items()} for league,names in ALIASES.items()}
def secondary_name(league,name):
    return ALIASES.get(league,{}).get(norm(name),norm(name))
def match(primary,secondary,competition_map):
    pairs=[]; unmatched=[]; proposals=[]
    for p in primary:
        candidates=[]
        for s in secondary:
            if competition_map.get(p["league"])!=s["competitionId"]:continue
            if norm(p["home"])!=secondary_name(p["league"],s["home"]) or norm(p["away"])!=secondary_name(p["league"],s["away"]):continue
            if datetime.fromisoformat(p["kickoff"].replace("Z","+00:00"))!=datetime.fromisoformat(s["kickoff"].replace("Z","+00:00")):continue
            candidates.append(s)
        if len(candidates)!=1:
            unmatched.append(p["eventId"]);continue
        proposals.append((p,candidates[0]))
    from collections import Counter
    pc=Counter(p["eventId"] for p in primary)
    sc=Counter(s["eventId"] for s in secondary)
    claims=Counter(s["eventId"] for p,s in proposals)
    for p,s in proposals:
        if pc[p["eventId"]]!=1 or sc[s["eventId"]]!=1 or claims[s["eventId"]]!=1:
            unmatched.append(p["eventId"]);continue
        a=p.get("score");b=s.get("score")
        pairs.append(dict(primaryId=p["eventId"],secondaryId=s["eventId"],scoreAgreement=(a==b if a is not None and b is not None else None)))
    return dict(pairs=pairs,unmatched=unmatched,settlementEnabled=False)
