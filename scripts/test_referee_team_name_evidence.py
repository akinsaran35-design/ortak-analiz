import copy,unittest
from referee_team_name_evidence import attach_names

def payload():
    return {"events":[{"id":"123","date":"2026-11-28T12:00:00Z",
        "competitions":[{"competitors":[
            {"homeAway":"home","team":{"displayName":"Alpha Athletic","shortDisplayName":"Alpha"}},
            {"homeAway":"away","team":{"displayName":"Beta FC","shortDisplayName":"Beta"}}],
            "status":{"type":{"state":"pre","name":"STATUS_SCHEDULED"}}}]}]}

class EvidenceTests(unittest.TestCase):
    def test_names_from_same_source(self):
        rows,bad=attach_names(payload(),"2026-11-28")
        self.assertEqual(bad,0)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["sourceTeamNames"],{"home":["Alpha","Alpha Athletic"],"away":["Beta","Beta FC"]})
    def test_conflicting_duplicate_names(self):
        p=payload()
        other=copy.deepcopy(p["events"][0])
        other["competitions"][0]["competitors"][0]["team"]["shortDisplayName"]="Other"
        p["events"].append(other)
        rows,_=attach_names(p,"2026-11-28")
        self.assertEqual(len(rows),1)
        self.assertNotIn("sourceTeamNames",rows[0])
    def test_wrong_day(self):
        self.assertEqual(attach_names(payload(),"2026-11-29")[0],[])

if __name__=="__main__":unittest.main()
