import unittest
from extra_xt_source_audit import inspect_events,coordinate_pair

class XtTests(unittest.TestCase):
    def setUp(self):
        self.fixture=dict(eventId="123",teams={"home":"1","away":"2"})
        self.payload=dict(header=dict(id="123",competitions=[dict(
            status=dict(type=dict(completed=True,name="STATUS_FULL_TIME")),
            competitors=[dict(homeAway="home",team=dict(id="1")),dict(homeAway="away",team=dict(id="2"))])]))
    def test_explicit_coordinates_are_candidates_only(self):
        self.payload["plays"]=[dict(type=dict(text="Pass"),start=dict(x=10,y=20),end=dict(x=25,y=30),outcome="successful",team=dict(id="1"))]
        r=inspect_events(self.payload,self.fixture)
        self.assertEqual(r["status"],"coordinate_candidates_unverified")
        self.assertEqual(r["collections"]["plays"]["movementsWithStartEnd"],1)
        self.assertFalse(r["xtComputed"])
        self.assertFalse(r["attackingDirectionVerified"])
    def test_text_is_not_location(self):
        self.payload["commentary"]=[dict(text="Pass into the box")]
        self.assertEqual(inspect_events(self.payload,self.fixture)["status"],"movement_coordinates_not_found")
    def test_invalid_coordinates(self):
        self.assertIsNone(coordinate_pair(dict(x=float("nan"),y=0)))
        self.assertIsNone(coordinate_pair(dict(x=True,y=0)))
        self.assertIsNone(coordinate_pair(dict(x="10",y=0)))
        self.payload["plays"]=[dict(type="Pass",start=dict(x=0,y=0))]
        self.assertEqual(inspect_events(self.payload,self.fixture)["status"],"movement_coordinates_not_found")
    def test_identity_and_status(self):
        self.payload["header"]["id"]="999"
        self.assertEqual(inspect_events(self.payload,self.fixture)["status"],"event_mismatch")
        self.payload["header"]["id"]="123"
        self.payload["header"]["competitions"][0]["competitors"][0]["team"]["id"]="9"
        self.assertEqual(inspect_events(self.payload,self.fixture)["status"],"team_mismatch")
if __name__=="__main__":
    unittest.main()
