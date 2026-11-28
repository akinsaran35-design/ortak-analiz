import unittest
from extra_fixture_aliases import fixture_team_key
from extra_historical_metric_coverage import LEAGUES

# Real unresolved pairs and expected CSV identities from artifact 15261705545.
CASES={
"sco.1":[("Heart of Midlothian","Celtic","hearts","celtic")],
"bel.1":[("KVC Westerlo","RAAL La Louvière","westerlo","raal la louviere"),
("Cercle Brugge KSV","KV Mechelen","cercle brugge","mechelen"),
("Lommel SK","Zulte-Waregem","lommel sk","waregem"),
("Royal Charleroi SC","Waasland-Beveren","charleroi","beveren"),
("Sint-Truidense","Racing Genk","st truiden","genk"),
("Standard Liege","Club Brugge","standard","club brugge"),
("Union St.-Gilloise","KAA Gent","st gilloise","gent")],
"ger.2":[("Dynamo Dresden","St. Pauli","dresden","st pauli"),
("Hertha Berlin","Karlsruher SC","hertha","karlsruhe"),
("VfL Osnabruck","Hannover 96","osnabruck","hannover"),
("1. FC Magdeburg","Energie Cottbus","magdeburg","cottbus"),
("SpVgg Greuther Fürth","Arminia Bielefeld","greuther furth","bielefeld"),
("TSV Eintracht Braunschweig","VfL Wolfsburg","braunschweig","wolfsburg")],
"esp.2":[("Real Valladolid","Real Sociedad II","valladolid","sociedad b"),
("Almería","Sporting Gijón","almeria","sp gijon"),
("Real Oviedo","RC Celta Fortuna","oviedo","celta b")],
"ita.2":[("Empoli","Hellas Verona","empoli","verona"),("Catanzaro","US Avellino","catanzaro","avellino")]
}
class AliasTests(unittest.TestCase):
    def test_observed_pairs(self):
        sports={c:s for _,c,s,_ in LEAGUES}
        self.assertEqual(sum(map(len,CASES.values())),19)
        for code,pairs in CASES.items():
            for home,away,h,a in pairs:
                with self.subTest(league=code,home=home,away=away):
                    self.assertEqual(fixture_team_key(home,code,sports[code]),h)
                    self.assertEqual(fixture_team_key(away,code,sports[code]),a)
    def test_scoped_and_no_guess(self):
        self.assertEqual(fixture_team_key("Real Sociedad II","sco.1","soccer_spl"),"real sociedad ii")
        self.assertEqual(fixture_team_key("Celta Vigo","esp.2","soccer_spain_segunda_division"),"celta vigo")
        self.assertEqual(fixture_team_key("Unknown Team","ita.2","soccer_italy_serie_b"),"unknown team")

if __name__=="__main__":unittest.main()
