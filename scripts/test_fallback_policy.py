import unittest
from fallback_policy import decide
class PolicyTest(unittest.TestCase):
    def test_gate(self):
        self.assertEqual(decide("error","observed",43,35,0,True)["mode"],"unavailable")
        self.assertEqual(decide("error","observed",100,95,0,True)["mode"],"secondary_fixture_candidate")
        for args in [(100,94,0,True),(100,100,1,True),(100,100,0,False),(0,0,0,True),(100,101,0,True)]:
            self.assertFalse(decide("error","observed",*args)["eligible"])
        self.assertEqual(decide("observed","observed",100,100,0,True)["mode"],"primary")
        self.assertFalse(decide("error","credentials_missing",100,100,0,True)["eligible"])
        self.assertFalse(decide("error","observed",100,100,0,True)["automaticFallbackEnabled"])
if __name__=="__main__":unittest.main()
