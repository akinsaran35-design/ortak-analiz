import unittest,json
from datetime import datetime,timedelta
from extra_league_score_audit import audit_league,build,TR,team_key,unmatched_names,REVIEWED_ALIASES,HISTORY_WINDOW_DAYS,SAMPLE_DATE_LIMIT,outcome_baseline,chronological_backtest,team_form_backtest,team_goal_means,hybrid_holdout,dc_tau,dc_probabilities,fit_dc_rho,dixon_coles_backtest,goal_probabilities,simulation_points,simulate_scores,simulation_audit,SIMULATION_METHODS,gamma_poisson_probabilities,bayesian_simulation,bayesian_backtest,bivariate_probabilities,fit_shared_intensity,bivariate_backtest,fit_nb_dispersion,nb_low_mass,nb_probabilities,negative_binomial_backtest,paired_date_bootstrap,bootstrap_model_comparison,markov_transition,markov_score_probabilities,markov_numerical_audit,elo_expected,elo_delta,elo_goal_means,elo_backtest
class AuditTests(unittest.TestCase):
    def test_names_require_explicit_review_and_league_scope(self):
        from unittest.mock import patch
        with patch.dict(REVIEWED_ALIASES,{"sco.1":{"example town":"example town united"}},clear=True):
            self.assertEqual(team_key("sco.1","Example Town"),"example town united")
            self.assertEqual(team_key("bel.1","Example Town"),"example town")
            self.assertEqual(team_key("sco.1","Unrelated Town"),"unrelated town")
        rows=[dict(home="a",away="b",status="csv_only"),dict(home="a",away="c",status="espn_only"),dict(home="d",away="e",status="corroborated")]
        self.assertEqual(unmatched_names(rows),{"csv_only":["a","b"],"espn_only":["a","c"]})
    def test_reviewed_names(self):
        for code,names in REVIEWED_ALIASES.items():
            for short,full in names.items():
                self.assertEqual(team_key(code,short),team_key(code,full))
                self.assertEqual(team_key("unrelated",short),short)
                self.assertNotEqual(short,full)
        self.assertNotEqual(team_key("esp.2","celta"),team_key("esp.2","celta b"))
        self.assertNotEqual(team_key("sco.1","dundee"),team_key("sco.1","dundee united"))
    def test_extended_history_window(self):
        now=datetime(2026,11,27,22,tzinfo=TR)
        self.assertEqual(HISTORY_WINDOW_DAYS,90)
        self.assertEqual(SAMPLE_DATE_LIMIT,90)
        dates=[now.date()-timedelta(days=d) for d in range(-1,92)]
        csv=("Date,HomeTeam,AwayTeam,FTHG,FTAG\n"+"".join(f"{d:%d/%m/%y},A,B,2,1\n" for d in dates)).encode()
        urls=[]
        def reader(url):
            urls.append(url)
            return csv if url.endswith(".csv") else b'{"events":[]}'
        report=audit_league("sco.1","SC0",now,reader)
        self.assertEqual(report["days"],[(now.date()-timedelta(days=d)).isoformat() for d in range(1,91)])
        self.assertEqual(len(urls),91)
        self.assertEqual(len(report["rows"]),90)
        self.assertTrue(all(r["status"]=="csv_only" for r in report["rows"]))
    def test_cross_season_history(self):
        now=datetime(2026,7,15,22,tzinfo=TR)
        def reader(url):
            if "/2526/" in url:
                return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n20/06/26,A,B,2,1\n"
            if "/2627/" in url:
                return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n10/07/26,C,D,1,0\n"
            return b'{"events":[]}'
        report=audit_league("sco.1","SC0",now,reader)
        self.assertEqual(report["days"],["2026-07-10","2026-06-20"])
        self.assertEqual(len(report["sourceUrls"]),4)
        self.assertFalse(report["errors"])
    def test_outcome_baseline(self):
        def row(home,score,status="corroborated",league="sco.1"):
            return dict(league=league,date="2026-11-25",home=home,away="z",csv=score,espn=score,status=status)
        rows=[row("a",[1,1]),row("b",[3,0]),row("c",[0,0]),row("d",[9,9],"conflict"),row("e",[2,2]),row("e",[2,2]),row("a",[0,1],league="bel.1"),row("f",[True,2])]
        result=outcome_baseline(rows)
        self.assertEqual(result["matches"],4)
        self.assertEqual(result["excludedRows"],4)
        self.assertEqual(result["markets"]["over15"],dict(occurred=2,ratePct=50.0))
        self.assertEqual(result["markets"]["over25"]["ratePct"],25.0)
        self.assertEqual(result["markets"]["btts"]["ratePct"],25.0)
        self.assertIsNone(result["predictionAccuracy"])
        self.assertIsNone(outcome_baseline([])["markets"]["btts"]["ratePct"])
    def test_chronological_backtest(self):
        def row(day,home,score,league="sco.1",status="corroborated"):
            return dict(league=league,date=day,home=home,away="z",csv=score,espn=score,status=status)
        rows=[row("2026-11-01",str(i),[0,0]) for i in range(19)]
        rows.extend([row("2026-11-02","a",[0,0]),row("2026-11-02","b",[0,0]),row("2026-11-03","c",[3,2]),row("2026-11-03","d",[0,0]),row("2026-11-03","e",[5,5],league="bel.1"),row("2026-11-03","f",[5,5],status="conflict")])
        result=chronological_backtest(rows)
        self.assertEqual(result["evaluatedMatches"],2)
        self.assertEqual(result["warmupMatches"],22)
        self.assertEqual(result["markets"]["over15"]["accuracyPct"],50.0)
        self.assertEqual(result["markets"]["over15"]["brier"],0.5)
        self.assertEqual(result["markets"]["btts"]["calibrationBins"][0]["meanProbability"],0.0)
        self.assertEqual(result,chronological_backtest(list(reversed(rows))))
        self.assertFalse(result["productionModelValidated"])
        self.assertIsNone(chronological_backtest([])["markets"]["btts"]["brier"])
    def test_team_form_backtest(self):
        def row(day,home,away,score,league="sco.1"):
            return dict(league=league,date=day,home=home,away=away,csv=score,espn=score,status="corroborated")
        past=[row(f"2026-10-{i:02d}","a",f"b{i}",[4,0]) for i in range(1,11)]
        past += [row(f"2026-10-{i:02d}","c",f"d{i}",[0,2]) for i in range(11,21)]
        self.assertGreater(team_goal_means(past,"a","unknown")[0],team_goal_means(past,"c","unknown")[0])
        self.assertEqual(team_goal_means(past,"unknown","unknown"),(2.0,1.0))
        rows=past+[row("2026-10-21","a","z",[5,0]),row("2026-10-21","c","y",[0,0])]
        result=team_form_backtest(rows)
        self.assertEqual(result["evaluatedMatches"],2)
        self.assertEqual(result,team_form_backtest(list(reversed(rows))))
        self.assertEqual(result["markets"]["over15"]["leagueMean"]["brier"],chronological_backtest(rows)["markets"]["over15"]["brier"])
        self.assertFalse(result["productionModelValidated"])
        self.assertIsNone(team_form_backtest([])["markets"]["btts"]["team"]["brier"])
    def test_hybrid_holdout(self):
        def row(day,i,score):
            return dict(league="sco.1",date=day,home=f"a{i}",away=f"b{i}",csv=score,espn=score,status="corroborated")
        start=datetime(2026,8,1)
        rows=[row((start+timedelta(days=d)).date().isoformat(),i,[i%3,(i+d)%3]) for d in range(30) for i in range(10)]
        result=hybrid_holdout(rows)
        self.assertEqual(result,hybrid_holdout(list(reversed(rows))))
        self.assertEqual(result["markets"]["over15"]["tuneMatches"]+result["markets"]["over15"]["holdoutMatches"],280)
        self.assertTrue(result["markets"]["over15"]["enoughForComparison"])
        changed=[dict(r,csv=[9,9],espn=[9,9]) if r["date"]>=result["holdoutStart"] else r for r in rows]
        modified=hybrid_holdout(changed)
        for k in result["markets"]:
            self.assertEqual(result["markets"][k]["teamWeight"],modified["markets"][k]["teamWeight"])
        self.assertFalse(result["productionModelValidated"])
        empty=hybrid_holdout([])
        self.assertIsNone(empty["markets"]["btts"]["hybrid"]["brier"])
        self.assertFalse(empty["markets"]["btts"]["enoughForComparison"])
    def test_dixon_coles(self):
        self.assertEqual(dc_probabilities(1.4,1.1,0),goal_probabilities(1.4,1.1))
        self.assertEqual(dc_probabilities(1.4,1.1,-0.1)[1],goal_probabilities(1.4,1.1)[1])
        self.assertGreater(dc_probabilities(1.4,1.1,-0.1)[2],goal_probabilities(1.4,1.1)[2])
        self.assertLess(fit_dc_rho([[0,0],[1,1]]*15,1,1),0)
        with self.assertRaises(ValueError):
            dc_probabilities(3,3,1)
        start=datetime(2026,8,1)
        rows=[dict(league="sco.1",date=(start+timedelta(days=d)).date().isoformat(),home=f"a{i}",away=f"b{i}",csv=[i%3,d%3],espn=[i%3,d%3],status="corroborated") for d in range(30) for i in range(10)]
        result=dixon_coles_backtest(rows)
        self.assertEqual(result,dixon_coles_backtest(list(reversed(rows))))
        self.assertEqual(result["markets"]["over25"]["poisson"],result["markets"]["over25"]["dixonColes"])
        self.assertEqual(result["markets"]["over15"]["n"],hybrid_holdout(rows)["markets"]["over15"]["holdoutMatches"])
        self.assertFalse(result["productionModelValidated"])
        self.assertIsNone(dixon_coles_backtest([])["markets"]["btts"]["dixonColes"]["brier"])
    def test_simulation_methods(self):
        for method in SIMULATION_METHODS:
            points=list(simulation_points(method,1024,42))
            self.assertEqual(points,list(simulation_points(method,1024,42)))
            self.assertTrue(all(0<=u<1 and 0<=v<1 for u,v in points))
            for rho in (0,-0.1):
                result=simulate_scores(1.4,1.1,rho,method,16384,42)
                self.assertTrue(all(v["absoluteError"]<0.025 for v in result["markets"].values()))
            zero=simulate_scores(0,0,0,method,32,42)
            self.assertTrue(all(v["simulated"]==0 for v in zero["markets"].values()))
        for method in ("sobol","latin_hypercube"):
            points=list(simulation_points(method,1024,42))
            self.assertEqual(len({int(u*1024) for u,v in points}),1024)
            self.assertEqual(len({int(v*1024) for u,v in points}),1024)
        with self.assertRaises(ValueError):
            list(simulation_points("sobol",100,42))
        self.assertIsNone(simulation_audit([])["summary"]["sobol"]["meanAbsoluteError"])
    def test_bayesian_predictive(self):
        self.assertEqual(gamma_poisson_probabilities(0,0,0),(0.5,0.3125,0.25))
        result=bayesian_simulation(30,20,20,8192,42)
        self.assertTrue(all(m["absoluteError"]<0.01 for m in result["markets"].values()))
        start=datetime(2026,8,1)
        rows=[dict(league="sco.1",date=(start+timedelta(days=d)).date().isoformat(),home=f"a{i}",away=f"b{i}",csv=[i%3,d%3],espn=[i%3,d%3],status="corroborated") for d in range(30) for i in range(10)]
        report=bayesian_backtest(rows)
        self.assertEqual(report,bayesian_backtest(list(reversed(rows))))
        self.assertEqual(report["markets"]["over15"]["n"],hybrid_holdout(rows)["markets"]["over15"]["holdoutMatches"])
        self.assertEqual(report["markets"]["over15"]["poisson"],dixon_coles_backtest(rows)["markets"]["over15"]["poisson"])
        self.assertFalse(report["productionModelValidated"])
        self.assertIsNone(bayesian_backtest([])["markets"]["btts"]["bayesian"]["brier"])
    def test_bivariate_poisson(self):
        import math
        self.assertEqual(bivariate_probabilities(1.4,1.1,0),goal_probabilities(1.4,1.1))
        self.assertEqual(bivariate_probabilities(0,0,0),(0,0,0))
        p=bivariate_probabilities(1,1,1)
        self.assertAlmostEqual(p[0],1-math.exp(-1))
        self.assertAlmostEqual(p[1],1-2*math.exp(-1))
        self.assertAlmostEqual(p[2],p[0])
        self.assertGreater(fit_shared_intensity([[0,0],[2,2]]*10,1,1),0)
        self.assertEqual(fit_shared_intensity([[0,2],[2,0]]*10,1,1),0)
        with self.assertRaises(ValueError):
            bivariate_probabilities(1,2,1.1)
        start=datetime(2026,8,1)
        rows=[dict(league="sco.1",date=(start+timedelta(days=d)).date().isoformat(),home=f"a{i}",away=f"b{i}",csv=[i%3,i%3],espn=[i%3,i%3],status="corroborated") for d in range(30) for i in range(10)]
        result=bivariate_backtest(rows)
        self.assertEqual(result,bivariate_backtest(list(reversed(rows))))
        self.assertEqual(result["markets"]["over15"]["poisson"],bayesian_backtest(rows)["markets"]["over15"]["poisson"])
        self.assertEqual(result["markets"]["btts"]["nonzeroSharedMatches"],result["markets"]["btts"]["n"])
        self.assertFalse(result["productionModelValidated"])
        self.assertIsNone(bivariate_backtest([])["markets"]["btts"]["bivariate"]["brier"])
    def test_negative_binomial(self):
        self.assertEqual(nb_probabilities(1.4,1.1,0,0),goal_probabilities(1.4,1.1))
        self.assertEqual(nb_low_mass(1,1),(0.5,0.25,0.125))
        p=nb_probabilities(1,1,1,1)
        for actual,expected in zip(p,(0.5,0.3125,0.25)):
            self.assertAlmostEqual(actual,expected)
        self.assertEqual(nb_probabilities(0,0,1,1),(0,0,0))
        self.assertGreater(fit_nb_dispersion([0,4]*10,2),0)
        self.assertEqual(fit_nb_dispersion([2]*20,2),0)
        with self.assertRaises(ValueError):
            nb_probabilities(1,2,-1,0)
        start=datetime(2026,8,1)
        rows=[dict(league="sco.1",date=(start+timedelta(days=d)).date().isoformat(),home=f"a{i}",away=f"b{i}",csv=[4*(i%2),4*(d%2)],espn=[4*(i%2),4*(d%2)],status="corroborated") for d in range(30) for i in range(10)]
        report=negative_binomial_backtest(rows)
        self.assertEqual(report,negative_binomial_backtest(list(reversed(rows))))
        self.assertEqual(report["markets"]["over15"]["poisson"],bivariate_backtest(rows)["markets"]["over15"]["poisson"])
        self.assertEqual(report["markets"]["btts"]["overdispersedMatches"],report["markets"]["btts"]["n"])
        self.assertFalse(report["productionModelValidated"])
        self.assertIsNone(negative_binomial_backtest([])["markets"]["btts"]["negativeBinomial"]["brier"])
    def test_paired_bootstrap(self):
        constant={str(i):[0.125]*(i+1) for i in range(10)}
        result=paired_date_bootstrap(constant,256)
        self.assertEqual(result["matches"],55)
        self.assertEqual(result["interval95"],[0.125,0.125])
        self.assertEqual(result,paired_date_bootstrap(dict(reversed(list(constant.items()))),256))
        self.assertIsNone(paired_date_bootstrap({"one":[0.1]},256)["interval95"])
        self.assertIsNone(paired_date_bootstrap({},256)["meanImprovement"])
        with self.assertRaises(ValueError):
            paired_date_bootstrap({},0)
        start=datetime(2026,8,1)
        rows=[dict(league="sco.1",date=(start+timedelta(days=d)).date().isoformat(),home=f"a{i}",away=f"b{i}",csv=[i%3,d%3],espn=[i%3,d%3],status="corroborated") for d in range(30) for i in range(10)]
        report=bootstrap_model_comparison(rows,256)
        self.assertEqual(report,bootstrap_model_comparison(list(reversed(rows)),256))
        baseline=negative_binomial_backtest(rows)["markets"]["over15"]
        comparison=report["markets"]["over15"]["negativeBinomial"]
        self.assertEqual(comparison["matches"],baseline["n"])
        self.assertAlmostEqual(comparison["meanImprovement"],baseline["poisson"]["brier"]-baseline["negativeBinomial"]["brier"],places=5)
        self.assertFalse(report["productionModelValidated"])
    def test_markov_score_states(self):
        for row in markov_transition(0.05):
            self.assertAlmostEqual(sum(row),1.0)
            self.assertTrue(all(p>=0 for p in row))
        for h,a in ((0,0),(1.4,1.1),(3.0,0.8)):
            result=markov_score_probabilities(h,a)
            for actual,expected in zip(result["markets"].values(),goal_probabilities(h,a)):
                self.assertAlmostEqual(actual,expected,places=11)
            self.assertLess(result["massError"],1e-11)
        half=markov_score_probabilities(1.4,1.1,45)
        for actual,expected in zip(half["markets"].values(),goal_probabilities(0.7,0.55)):
            self.assertAlmostEqual(actual,expected,places=11)
        self.assertEqual(markov_score_probabilities(1,1,90,2,1)["markets"],dict(over15=1,over25=1,btts=1))
        self.assertEqual(markov_score_probabilities(1,1,90,0,0)["markets"],dict(over15=0,over25=0,btts=0))
        self.assertEqual(markov_score_probabilities(1,1,60,5,1)["markets"],dict(over15=1,over25=1,btts=1))
        with self.assertRaises(ValueError):
            markov_score_probabilities(1,1,91)
        with self.assertRaises(ValueError):
            markov_score_probabilities(1,1,30,-1,0)
        report=markov_numerical_audit([])
        self.assertIsNone(report["maxPrematchError"])
        self.assertFalse(report["liveValidation"])
    def test_elo_strength(self):
        self.assertAlmostEqual(elo_expected(1500,1500,0),0.5)
        self.assertGreater(elo_delta(1500,1500,2,0),0)
        self.assertLess(elo_delta(1500,1500,0,2),0)
        self.assertEqual(elo_goal_means(1.4,1.1,1600,1400,0),(1.4,1.1))
        h,a=elo_goal_means(1.4,1.1,1600,1400,1)
        self.assertGreater(h,1.4)
        self.assertAlmostEqual(h+a,2.5)
        for i in (0,1):
            self.assertAlmostEqual(goal_probabilities(h,a)[i],goal_probabilities(1.4,1.1)[i])
        start=datetime(2026,8,1)
        rows=[dict(league="sco.1",date=(start+timedelta(days=d)).date().isoformat(),home=f"a{i}",away=f"b{i}",csv=[i%3,d%3],espn=[i%3,d%3],status="corroborated") for d in range(30) for i in range(10)]
        result=elo_backtest(rows)
        self.assertEqual(result,elo_backtest(list(reversed(rows))))
        self.assertEqual(result["markets"]["over15"]["poisson"],negative_binomial_backtest(rows)["markets"]["over15"]["poisson"])
        self.assertEqual(result["markets"]["over25"]["poisson"]["brier"],result["markets"]["over25"]["elo"]["brier"])
        self.assertFalse(result["productionModelValidated"])
        self.assertIsNone(elo_backtest([])["markets"]["btts"]["elo"]["brier"])
    def test_scope_and_score_comparison(self):
        now=datetime(2026,11,27,22,tzinfo=TR)
        csv=b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n25/11/26,A,B,2,1\n25/11/26,C,D,0,0\n25/11/26,E,F,1,0\n27/11/26,G,H,1,0\n"
        def event(h,a,score):
            return {"date":"2026-11-25T18:00:00Z","competitions":[{"status":{"type":{"completed":True,"name":"STATUS_FULL_TIME"}},"competitors":[{"homeAway":"home","team":{"displayName":h},"score":str(score[0])},{"homeAway":"away","team":{"displayName":a},"score":str(score[1])}]}]}
        def reader(url):
            if url.endswith(".csv"):return csv
            return json.dumps({"events":[event("A","B",[2,1]),event("C","D",[1,0]),event("X","Y",[3,0])]}).encode()
        report=audit_league("sco.1","SC0",now,reader)
        self.assertEqual(report["days"],["2026-11-25"])
        self.assertEqual([r["status"] for r in report["rows"]],["corroborated","conflict","csv_only","espn_only"])
        all_reports=build(now,reader)
        self.assertEqual(all_reports["corroborated"],6)
        self.assertEqual(all_reports["outcomeBaseline"]["matches"],6)
        self.assertEqual(all_reports["outcomeBaseline"]["markets"]["btts"]["ratePct"],100.0)
        self.assertFalse(all_reports["archivesModified"])
        self.assertFalse(all_reports["predictionsEnabled"])
        self.assertFalse(all_reports["realBettingEnabled"])
        self.assertEqual(audit_league("bel.1","B1",now,lambda url:b"bad")["rows"],[])
if __name__=="__main__":unittest.main()
