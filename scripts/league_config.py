"""Shared configured football coverage; source and provider availability checked at runtime."""
LEAGUES = (
    ("İngiltere Premier Lig", "en.1", "soccer_epl"),
    ("İngiltere Championship", "en.2", "soccer_efl_champ"),
    ("Almanya Bundesliga", "de.1", "soccer_germany_bundesliga"),
    ("İspanya La Liga", "es.1", "soccer_spain_la_liga"),
    ("İtalya Serie A", "it.1", "soccer_italy_serie_a"),
    ("Fransa Ligue 1", "fr.1", "soccer_france_ligue_one"),
    ("Hollanda Eredivisie", "nl.1", "soccer_netherlands_eredivisie"),
    ("Portekiz Primeira Liga", "pt.1", "soccer_portugal_primeira_liga"),
)
FIXTURE_CODES = {name: code for name, code, odds in LEAGUES}
ODDS_CODES = {name: odds for name, code, odds in LEAGUES}
RESULT_CODES = {odds: code for name, code, odds in LEAGUES}
