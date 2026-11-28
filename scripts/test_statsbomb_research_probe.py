import unittest
from statsbomb_research_probe import inspect,coords,build

class ResearchTests(unittest.TestCase):
    def test_coords(self):
        self.assertTrue(coords([120,80]))
        self.assertFalse(coords([121,80]))
        self.assertFalse(coords([True,0]))
        self.assertFalse(coords([float("nan"),0]))
    def test_event_coverage(self):
        e=[dict(id="1",period=1,type=dict(name="Shot"),team=dict(id=1),shot=dict(statsbomb_xg=.4)),
           dict(id="2",period=1,type=dict(name="Pass"),team=dict(id=2),location=[2,3],pass_={})]
        e[1]["pass"]=dict(end_location=[5,6])
        r=inspect(e,{1,2})
        self.assertTrue(r["xgComplete"])
        self.assertTrue(r["xgaDerivable"])
        self.assertTrue(r["movementCoordinatesPresent"])
        self.assertFalse(r["xtComputed"])
        e[0]["shot"]={}
        self.assertFalse(inspect(e,{1,2})["xgComplete"])
        e[0]["shot"]={"statsbomb_xg":.5}
        self.assertFalse(inspect(e+[e[0]],{1,2})["xgComplete"])
    def test_missing_catalog(self):
        r=build(lambda path:[])
        self.assertEqual(r["sampled"],0)
        self.assertEqual(len(r["errors"]),2)
        self.assertFalse(r["usedForTraining"])
if __name__=="__main__":
    unittest.main()
