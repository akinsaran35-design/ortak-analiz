"""League-scoped ESPN to football-data aliases.
Reviewed against V7.10 source artifact 15261705545.
Do not use for odds, settlement, cross-league or fuzzy matching.
"""
from nine_league_results_pilot import result_key

ALIASES={
    "sco.1":{"Heart of Midlothian":"hearts"},
    "bel.1":{
        "KVC Westerlo":"westerlo","Cercle Brugge KSV":"cercle brugge",
        "KV Mechelen":"mechelen","Zulte-Waregem":"waregem",
        "Royal Charleroi SC":"charleroi","Waasland-Beveren":"beveren",
        "Sint-Truidense":"st truiden","Racing Genk":"genk",
        "Standard Liege":"standard","Union St.-Gilloise":"st gilloise",
        "KAA Gent":"gent",
    },
    "ger.2":{
        "Dynamo Dresden":"dresden","Hertha Berlin":"hertha",
        "Karlsruher SC":"karlsruhe","VfL Osnabruck":"osnabruck",
        "Hannover 96":"hannover","1. FC Magdeburg":"magdeburg",
        "Energie Cottbus":"cottbus","SpVgg Greuther Fürth":"greuther furth",
        "Arminia Bielefeld":"bielefeld","TSV Eintracht Braunschweig":"braunschweig",
        "VfL Wolfsburg":"wolfsburg",
    },
    "esp.2":{
        "Real Valladolid":"valladolid","Real Sociedad II":"sociedad b",
        "Sporting Gijón":"sp gijon","Real Oviedo":"oviedo",
        "RC Celta Fortuna":"celta b",
    },
    "ita.2":{"Hellas Verona":"verona","US Avellino":"avellino"},
}

def fixture_team_key(name,code,sport):
    key=result_key(name,code,sport)
    aliases={result_key(k,code,sport):v for k,v in ALIASES.get(code,{}).items()}
    return aliases.get(key,key)
