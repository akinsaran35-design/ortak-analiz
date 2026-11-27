import unittest
from referee_sample_research import audit
class Tests(unittest.TestCase):
    def test_weighted(self):
        def row(n,m):
            return dict(label="A",matches=n,yellowCards=dict(sample=n,totalAverage=m),redCards=dict(sample=0,totalAverage=None))
        r=audit(dict(cutoffExclusive="2026-11-27",groups=[dict(league="x",completedMatches=30,assignedFixtures=30,coverage=1,errors=[],seasons=[dict(season=2025,labels=[row(10,2)]),dict(season=2026,labels=[row(20,5)])])]))
        p=r["groups"][0]["profiles"][0]
        self.assertEqual(p["metrics"]["yellowCards"]["mean"],4)
        self.assertTrue(p["metrics"]["yellowCards"]["minimumSampleMet"])
        self.assertIsNone(p["metrics"]["redCards"]["mean"])
        self.assertFalse(p["identityVerified"])
if __name__=="__main__":unittest.main()
