import unittest
from cross_source_match import match
class MatchTest(unittest.TestCase):
    def test_strict(self):
        p=dict(eventId=1,league="en.1",home="A",away="B",kickoff="2026-11-27T12:00:00Z",score=[1,0])
        s=dict(eventId=2,competitionId=2021,home="a",away="b",kickoff="2026-11-27T12:00:00+00:00",score=[1,0])
        self.assertTrue(match([p],[s],{"en.1":2021})["pairs"][0]["scoreAgreement"])
        self.assertFalse(match([p],[s,s],{"en.1":2021})["pairs"])
        self.assertFalse(match([p],[s],{})["pairs"])
        self.assertFalse(match([p],[dict(s,away="C")],{"en.1":2021})["pairs"])
        self.assertFalse(match([p],[dict(s,score=[0,0])],{"en.1":2021})["pairs"][0]["scoreAgreement"])

    def test_alias_collision(self):
        p=dict(eventId=1,league="en.1",home="Chelsea",away="Arsenal",kickoff="2026-11-27T12:00:00Z")
        s=dict(eventId=2,competitionId=2021,home="Chelsea FC",away="Arsenal FC",kickoff=p["kickoff"])
        self.assertEqual(len(match([p],[s],{"en.1":2021})["pairs"]),1)
        self.assertFalse(match([p,dict(p,eventId=3)],[s],{"en.1":2021})["pairs"])
        self.assertFalse(match([p,p],[s],{"en.1":2021})["pairs"])
        self.assertFalse(match([p],[s,dict(s,home="Other")],{"en.1":2021})["pairs"])
