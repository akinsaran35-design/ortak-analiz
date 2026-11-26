import unittest
from league_config import LEAGUES, FIXTURE_CODES, ODDS_CODES, RESULT_CODES
from match_odds import LEAGUES as MATCH_CODES

class LeagueConfigTest(unittest.TestCase):
    def test_consistency(self):
        self.assertEqual(len(LEAGUES),9)
        self.assertEqual(len(FIXTURE_CODES),9)
        self.assertEqual(len(set(FIXTURE_CODES.values())),9)
        self.assertEqual(len(RESULT_CODES),9)
        self.assertEqual(MATCH_CODES,ODDS_CODES)
        for name, fixture, odds in LEAGUES:
            self.assertEqual(RESULT_CODES[ODDS_CODES[name]],fixture)
        self.assertEqual(FIXTURE_CODES["Hollanda Eredivisie"],"nl.1")
        self.assertEqual(FIXTURE_CODES["Portekiz Primeira Liga"],"pt.1")
        self.assertEqual(FIXTURE_CODES["Türkiye Süper Lig"],"tr.1")

if __name__=="__main__": unittest.main()
