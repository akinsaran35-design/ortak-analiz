import unittest
from results_source_pilot import csv_results,espn_results,compare

class SourcePilotTests(unittest.TestCase):
    def test_exact_scores_and_conflicts(self):
        raw=b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n25/11/26,Bolton,West Brom,1,3\n"
        csv=csv_results(raw)
        row={"date":"2026-11-25","home":"Bolton Wanderers FC","away":"West Bromwich Albion FC","result":[1,3]}
        event={"date":"2026-11-25T19:45:00Z","competitions":[{"status":{"type":{"completed":True,"name":"STATUS_FULL_TIME"}},"competitors":[{"homeAway":"away","team":{"displayName":"West Bromwich Albion"},"score":"3"},{"homeAway":"home","team":{"displayName":"Bolton Wanderers"},"score":"1"}]}]}
        espn=espn_results({"events":[event]},row["date"])
        self.assertEqual(compare([row],csv,espn)[0]["status"],"corroborated")
        self.assertEqual(compare([dict(row,result=[0,0])],csv,espn)[0]["status"],"archive_conflict")
        self.assertEqual(compare([row],csv,{})[0]["status"],"incomplete")
        self.assertEqual(compare([row],csv,{k:[0,0] for k in espn})[0]["status"],"conflict")
        self.assertEqual(csv_results(raw+b"25/11/26,Bolton,West Brom,0,0\n"),{})
        event["competitions"][0]["status"]["type"]["completed"]=False
        self.assertEqual(espn_results({"events":[event]},row["date"]),{})
if __name__=="__main__": unittest.main()
