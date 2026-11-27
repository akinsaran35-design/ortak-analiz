import unittest
from live_tempo_audit import audit
from live_observation_history import COUNT_METRICS
class Tests(unittest.TestCase):
    def test_observed(self):
        def p(m,n,g):
            return dict(minute=m,receivedAt=f"2026-11-27T12:{m:02d}:00+00:00",score=[g,0],metrics={k:[n,0] for k in COUNT_METRICS})
        r=audit({"a":{"points":[p(5,0,0),p(10,2,0),p(15,3,1)]}})
        self.assertEqual(r["counts"]["5:labelled"],1)
        self.assertEqual(r["samples"][0]["futureGoals"],[1,0])
        self.assertEqual(r["samples"][0]["rates"]["shots"],[0.4,0])
        self.assertFalse(r["predictionsEnabled"])
    def test_empty(self):
        self.assertEqual(audit({})["samples"],[])
if __name__=="__main__":unittest.main()
