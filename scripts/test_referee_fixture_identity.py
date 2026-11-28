import copy,unittest
from referee_fixture_identity import match
def provider():
    return dict(errors=[],results=1,paging=dict(current=1,total=1),response=[dict(
        fixture=dict(id=42,date="2026-11-28T15:00:00+03:00",status=dict(short="NS"),referee="Test Ref"),
        league=dict(id=78,country="Germany",name="Bundesliga"),
        teams=dict(home=dict(name="Test Ä"),away=dict(name="Test B")))])
def targets():
    return [dict(league="de.1",rows=[dict(eventId="100",home="Test A",away="Test B",
        kickoff="2026-11-28T12:00:00Z",state="pre",status="STATUS_SCHEDULED")])]
class IdentityTests(unittest.TestCase):
    def test_unique(self):
        result=match(provider(),targets())
        self.assertEqual((result["matched"],result["withReferee"]),(1,1))
        self.assertFalse(result["publicationAllowed"])
        self.assertFalse(result["predictionsEnabled"])
    def test_wrong_league_time_or_teams(self):
        for field,value in (("league",dict(id=78,country="Germany",name="2. Bundesliga")),
                            ("teams",dict(home=dict(name="Test B"),away=dict(name="Test A")))):
            doc=provider();doc["response"][0][field]=value
            self.assertEqual(match(doc,targets())["matched"],0)
        doc=provider();doc["response"][0]["fixture"]["date"]="2026-11-28T15:01:00+03:00"
        self.assertEqual(match(doc,targets())["matched"],0)
    def test_duplicate_and_missing(self):
        doc=provider();doc["response"].append(copy.deepcopy(doc["response"][0]));doc["results"]=2
        self.assertEqual(match(doc,targets())["matched"],0)
        doc=provider();doc["response"][0]["fixture"]["referee"]=None
        self.assertEqual(match(doc,targets())["matched"],1)
        self.assertEqual(match(doc,targets())["withReferee"],0)
        groups=targets();groups[0]["rows"]*=2
        self.assertEqual(match(provider(),groups)["matched"],0)
    def test_diagnostic_partition(self):
        def counts(doc,groups):
            r=match(doc,groups)
            c=next(x["counts"] for x in r["diagnostics"] if x["league"]=="de.1")
            self.assertEqual(c["eligible"],sum(v for k,v in c.items() if k!="eligible"))
            return c
        doc=provider()
        doc["response"][0]["fixture"]["date"]="2026-11-28T15:01:00+03:00"
        self.assertEqual(counts(doc,targets())["kickoff_difference"],1)
        doc=provider()
        doc["response"][0]["teams"]["home"]["name"]="Other"
        self.assertEqual(counts(doc,targets())["same_time_team_identity_unresolved"],1)
        doc=provider()
        doc["response"][0]["league"]["name"]="Other"
        self.assertEqual(counts(doc,targets())["league_metadata_unverified"],1)
        doc=provider()
        doc["response"][0]["fixture"]["referee"]=None
        self.assertEqual(counts(doc,targets())["matched_missing_referee"],1)
    def test_incomplete(self):
        doc=provider();doc["paging"]["total"]=2
        with self.assertRaises(ValueError):match(doc,targets())
if __name__=="__main__":unittest.main()
