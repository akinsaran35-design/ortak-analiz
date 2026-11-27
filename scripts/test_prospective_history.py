import unittest
from datetime import date
from prospective_history import canonical_history,team_counts
TODAY=date(2026,11,27)
class Tests(unittest.TestCase):
    def test_exact_alias_and_duplicate(self):
        d=date(2026,11,20)
        rows=[(d,"Man City","Arsenal",2,1),(d,"Manchester City FC","Arsenal FC",2,1)]
        clean,audit=canonical_history("en.1",rows,TODAY)
        self.assertEqual(len(clean),1)
        self.assertEqual(team_counts(clean,"manchester city","arsenal"),dict(home=1,away=1))
        self.assertEqual(audit["conflicts"],0)
    def test_conflict_and_cutoff(self):
        d=date(2026,11,20)
        rows=[(d,"Man City","Arsenal",2,1),(d,"Manchester City FC","Arsenal FC",1,2),(TODAY,"Man City","Arsenal",9,0)]
        clean,audit=canonical_history("en.1",rows,TODAY)
        self.assertEqual(clean,[])
        self.assertEqual(audit["conflicts"],1)
    def test_distinct_clubs(self):
        d=date(2026,11,20)
        clean,audit=canonical_history("en.1",[(d,"Man City","Man United",1,0)],TODAY)
        self.assertEqual(len(clean),1)
        self.assertNotEqual(clean[0][1],clean[0][2])
if __name__=="__main__":unittest.main()
