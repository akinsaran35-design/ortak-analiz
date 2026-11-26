import unittest
from datetime import date
from football_form import form
class FormTests(unittest.TestCase):
    def test_cutoff_orientation_and_conflicts(self):
        d=date.fromisoformat
        rows=[(d("2026-11-22"),"A","B",2,1),(d("2026-11-22"),"A","B",2,1),
              (d("2026-11-20"),"C","A",1,3),(d("2026-11-19"),"B","A",0,0),
              (d("2026-11-18"),"A","C",1,0),(d("2026-11-18"),"A","C",2,0),
              (d("2026-11-26"),"A","B",9,0)]
        r=form(rows,"A","B",d("2026-11-26"))
        self.assertEqual(r["home"]["sample"],3)
        self.assertEqual(r["home"]["wins"],2)
        self.assertEqual(r["home"]["goalsFor"],5)
        self.assertEqual(r["away"]["losses"],1)
        self.assertEqual(r["home"]["rows"][1]["venue"],"away")
        self.assertEqual(len(r["h2h"]),2)
        self.assertEqual(r["sourceConflictsExcluded"],1)
        self.assertFalse(r["injuriesAvailable"])
    def test_empty(self):
        r=form([],"A","B",date(2026,11,26))
        self.assertEqual(r["home"]["sample"],0)
        self.assertEqual(r["h2h"],[])
if __name__=="__main__":unittest.main()
