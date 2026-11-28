import unittest,copy,json
from datetime import datetime
from xg_source_catalog import inspect,probe,URL
NOW=datetime.fromisoformat("2026-11-28T15:00:00+03:00")
def sample():
    return dict(schema_version=1,generated_at="2026-11-27T23:18:06Z",competitions=[dict(slug="epl",seasons=[dict(year=2026,source="Sportmonks",team_xg_source="Sportmonks",fixtures=380,results=111,stages=[dict(id=1,fixtures=380,results=111,with_xg=110)])])])
class CatalogTests(unittest.TestCase):
    def test_coverage_only(self):
        result=inspect(sample(),NOW,2026)
        self.assertEqual(result["reportedWithXg"],110)
        self.assertTrue(result["catalogFresh"])
        self.assertFalse(result["individualMatchesValidated"])
        self.assertFalse(result["redistributionPermissionVerified"])
        self.assertFalse(result["predictionsEnabled"])
    def test_inconsistent_counts(self):
        d=sample();d["competitions"][0]["seasons"][0]["stages"][0]["with_xg"]=112
        with self.assertRaises(ValueError):inspect(d,NOW,2026)
        d=sample();d["competitions"]*=2
        with self.assertRaises(ValueError):inspect(d,NOW,2026)
    def test_stale_and_future(self):
        d=sample();d["generated_at"]="2026-11-01T00:00:00Z"
        self.assertFalse(inspect(d,NOW,2026)["catalogFresh"])
        d["generated_at"]="2026-12-01T00:00:00Z"
        with self.assertRaises(ValueError):inspect(d,NOW,2026)
    def test_one_request(self):
        paths=[]
        def reader(url):
            paths.append(url);return json.dumps(sample())
        r=probe(NOW,reader)
        self.assertEqual(paths,[URL])
        self.assertEqual(r["status"],"checked")
if __name__=="__main__":unittest.main()
