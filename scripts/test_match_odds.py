import unittest
from match_odds import canonical, build_report
from datetime import datetime, timezone
class AliasTests(unittest.TestCase):
    def test_aliases(self):
        for a,b in [("FC Bayern München","Bayern Munich"),("SV Werder Bremen","Werder Bremen"),("1. FC Union Berlin","Union Berlin"),("1. FSV Mainz 05","FSV Mainz 05")]:
            self.assertEqual(canonical(a,"soccer_germany_bundesliga"),canonical(b,"soccer_germany_bundesliga"))
        for a,b in [("Stade Brestois 29","Brest"),("Le Havre AC","Le Havre"),("RC Strasbourg Alsace","Strasbourg")]:
            self.assertEqual(canonical(a,"soccer_france_ligue_one"),canonical(b,"soccer_france_ligue_one"))
    def test_isolation(self):
        self.assertNotEqual(canonical("FC Bayern München","soccer_epl"),canonical("Bayern Munich","soccer_epl"))
        self.assertNotEqual(canonical("Everton FC","soccer_epl"),canonical("Liverpool FC","soccer_epl"))
class ObservedAliases(unittest.TestCase):
    def test_observed_pairs(self):
        for league, a, b in [
            ("soccer_netherlands_eredivisie","FC Twente '65","FC Twente Enschede"),
            ("soccer_portugal_primeira_liga","Sport Lisboa e Benfica","Benfica"),
            ("soccer_france_ligue_one","Olympique Lyonnais","Lyon"),
            ("soccer_spain_la_liga","RC Celta de Vigo","Celta Vigo"),
            ("soccer_italy_serie_a","FC Internazionale Milano","Inter Milan"),
            ("soccer_epl","Brighton & Hove Albion FC","Brighton and Hove Albion"),
            ("soccer_germany_bundesliga","Bayer 04 Leverkusen","Bayer Leverkusen"),
        ]:
            self.assertEqual(canonical(a,league),canonical(b,league))
        self.assertNotEqual(canonical("Sporting Lisbon","soccer_portugal_primeira_liga"),canonical("Braga","soccer_portugal_primeira_liga"))

class ReplayTests(unittest.TestCase):
    def test_exact_date_and_ambiguity(self):
        now=datetime(2026,11,26,13,tzinfo=timezone.utc)
        daily={"candidates":[{"league":"İngiltere Premier Lig","date":"2026-11-28","match":"Everton FC – Liverpool FC"}]}
        event={"league":"soccer_epl","home":"Everton","away":"Liverpool","kickoff":"2026-11-28T19:00:00Z","id":"one"}
        self.assertEqual(build_report(daily,{"events":[event]},now)["matchedCount"],1)
        late=dict(event,kickoff="2026-11-28T22:00:00Z")
        result=build_report(daily,{"events":[late]},now)
        self.assertEqual(result["matchedCount"],0)
        self.assertEqual(result["unmatched"][0]["reason"],"date_mismatch")
        self.assertEqual(result["unmatched"][0]["providerDates"],["2026-11-29"])
        self.assertEqual(build_report(daily,{"events":[event,dict(event,id="two")]},now)["unmatched"][0]["reason"],"ambiguous")
        self.assertEqual(build_report(daily,{"events":[dict(event,league="soccer_efl_champ")]},now)["matchedCount"],0)

if __name__ == "__main__":
    unittest.main()
