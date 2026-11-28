import unittest
from datetime import datetime,timezone,timedelta
from sportmonks_fixture_coverage import probe
NOW=datetime(2026,11,28,14,tzinfo=timezone.utc)
def fixture(id,state,offset):
    return dict(id=id,league_id=501,state_id=state,state={"id":state},starting_at_timestamp=int((NOW+timedelta(hours=offset)).timestamp()),scores=[{"private":"never output"}],statistics=[{"value":4}])
class Tests(unittest.TestCase):
    def test_states_and_bound(self):
        calls=[]
        def read(*args):
            calls.append(args)
            return {"data":[fixture(1,5,-24),fixture(2,2,-1),fixture(3,1,24),fixture(4,1,-2)],"pagination":{"has_more":False}}
        r=probe("token",NOW,read)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][1:],("2026-11-21","2026-11-30"))
        self.assertTrue(r["paginationComplete"])
        self.assertEqual(r["groups"][1]["states"]["completed_reported"]["eligible"],1)
        self.assertEqual(r["groups"][1]["states"]["in_play_reported"]["eligible"],1)
        self.assertEqual(r["groups"][1]["states"]["upcoming"]["eligible"],1)
        self.assertNotIn("never output",str(r))
        self.assertEqual(r["xgStatus"],"documented_paid_addon_not_requested")
        self.assertFalse(r["predictionsEnabled"])
    def test_duplicate_and_pagination(self):
        row=fixture(1,5,-24)
        r=probe("token",NOW,lambda *_:{"data":[row,row],"pagination":{"has_more":True}})
        self.assertEqual(r["base"]["eligible"],0)
        self.assertFalse(r["paginationComplete"])
    def test_missing(self):
        self.assertEqual(probe("",NOW)["requestsAttempted"],0)
if __name__=="__main__":unittest.main()
