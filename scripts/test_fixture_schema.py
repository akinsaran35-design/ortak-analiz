import unittest
from fixture_schema import matches_in

class FixtureSchemaTest(unittest.TestCase):
    def test_shapes(self):
        row={"date":"2026-11-25","team1":"A","team2":"B","score":{"ft":[0,0]}}
        for payload in ([row],{"matches":[row]},{"rounds":[{"matches":[row]}]}):
            self.assertEqual(matches_in(payload),[row])
    def test_invalid(self):
        for payload in ({},{"matches":None},[None],{"rounds":[{}]}):
            with self.assertRaises(ValueError):
                matches_in(payload)
    def test_empty(self):
        self.assertEqual(matches_in([]),[])
        self.assertEqual(matches_in({"matches":[]}),[])

if __name__=="__main__": unittest.main()
