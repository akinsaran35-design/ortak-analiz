import unittest
from match_odds import canonical
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

if __name__ == "__main__":
    unittest.main()
