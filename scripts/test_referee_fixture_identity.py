import copy,unittest
from referee_fixture_identity import match,combined_evidence
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
    def test_alias_shadow_never_promotes(self):
        doc=provider()
        groups=targets()
        doc["response"][0]["teams"]["home"]["name"]="Dortmund"
        groups[0]["rows"][0]["home"]="Borussia Dortmund"
        r=match(doc,groups)
        self.assertEqual(r["matched"],0)
        self.assertEqual(r["aliasShadow"]["additionalCandidates"],1)
        self.assertFalse(r["aliasShadow"]["verified"])
        self.assertEqual(r["rows"],[])
        doc["response"].append(copy.deepcopy(doc["response"][0]))
        doc["response"][1]["fixture"]["id"]=43
        doc["response"][1]["teams"]["home"]["name"]="Borussia Dortmund"
        doc["results"]=2
        r=match(doc,groups)
        self.assertEqual(r["aliasShadow"]["additionalCandidates"],0)
    def test_explicit_source_name_shadow(self):
        doc=provider(); groups=targets()
        row=groups[0]["rows"][0]
        row["home"]="Test Athletic"
        row["sourceTeamNames"]={"home":["Test Athletic","Test A"],"away":["Test B"]}
        r=match(doc,groups)
        self.assertEqual(r["matched"],0)
        self.assertEqual(r["sourceNameShadow"]["additionalCandidates"],1)
        self.assertFalse(r["sourceNameShadow"]["verified"])
        row["sourceTeamNames"]["away"].append("Test A")
        self.assertEqual(match(doc,groups)["sourceNameShadow"]["additionalCandidates"],0)
    def test_combined_evidence_dedup_and_conflict(self):
        a=("de.1","100",42)
        b=("de.1","101",43)
        c=("de.1","102",44)
        r=combined_evidence({a:True,b:False},{a:True,c:True},5,1)
        self.assertEqual((r["sharedCandidates"],r["aliasOnly"],r["sourceOnly"]),(1,1,1))
        self.assertEqual((r["additionalCandidates"],r["candidatesWithReferee"],r["remainingIdentities"]),(3,2,1))
        r=combined_evidence({a:True,b:False},{("de.1","100",44):True,("de.1","102",43):True},5,1)
        self.assertEqual(r["conflictingPairs"],4)
        self.assertEqual(r["additionalCandidates"],0)
        self.assertFalse(r["verified"])
        self.assertFalse(r["predictionsEnabled"])
        self.assertNotIn("100",str(r))
    def test_incomplete(self):
        doc=provider();doc["paging"]["total"]=2
        with self.assertRaises(ValueError):match(doc,targets())
if __name__=="__main__":unittest.main()
