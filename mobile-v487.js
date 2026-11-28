(function(){
"use strict";
const FILES=["extra_markets","extra_market_archive","main_ml_matched_pairs","main_ml_prospective_ledger","main_ml_frozen_manifest","observed_totals_report","extra_ml_prospective_ledger","extra_ml_frozen_manifest","shadow_performance","nov27_match_review","fixture_evidence_summary","market_movement","team_logos","daily","matching","odds","performance","prospective_validation","data_quality","unified_decision","snapshot_integrity","prospective_leagues","scoreboard_snapshot","fixture_coverage_audit","kickoff_confirmation","model_research","football_statistics_pilot"];
const MARKETS=["1.5 Üst","2.5 Üst","KG Var"];
const LEAGUES={"İngiltere Premier Lig":"soccer_epl","İngiltere Championship":"soccer_efl_champ","Almanya Bundesliga":"soccer_germany_bundesliga","İspanya La Liga":"soccer_spain_la_liga","İtalya Serie A":"soccer_italy_serie_a","Fransa Ligue 1":"soccer_france_ligue_one","Hollanda Eredivisie":"soccer_netherlands_eredivisie","Portekiz Primeira Liga":"soccer_portugal_primeira_liga","Türkiye Süper Lig":"soccer_turkey_super_league"};
const arr=x=>Array.isArray(x)?x:[],num=x=>Number.isInteger(x)&&x>=0?String(x):"—";
const pct=x=>typeof x==="number"&&Number.isFinite(x)&&x>=0&&x<=100?"%"+x.toLocaleString("tr-TR",{maximumFractionDigits:1}):"—";
const key=x=>JSON.stringify([x.date,x.league,x.match]);
const dateTR=t=>new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Istanbul",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(t));
const hourTR=t=>new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Istanbul",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).format(new Date(t));
const fresh=(t,now)=>Number.isFinite(Date.parse(t))&&now>=Date.parse(t)&&now-Date.parse(t)<=1800000;
function bound(data,k,now){const m=data.snapshot_integrity;return m?.status==="PASS"&&Array.isArray(m.errors)&&m.errors.length===0&&fresh(m.updatedAt,now)&&fresh(data[k]?.updatedAt,now)&&m.reportTimestamps?.[k+".json"]===data[k].updatedAt;}
function topScores(x,y){if(![x,y].every(v=>typeof v==="number"&&Number.isFinite(v)&&v>=0&&v<=10))return [];const p=l=>{const a=[Math.exp(-l)];for(let i=1;i<=25;i++)a.push(a[i-1]*l/i);return a;};const a=p(x),b=p(y),out=[];for(let i=0;i<a.length;i++)for(let j=0;j<b.length;j++)out.push({score:i+"–"+j,p:a[i]*b[j]*100});return out.sort((u,v)=>v.p-u.p).slice(0,3);}
function leagueReport(data,now){
 const r=data.prospective_leagues,v=data.prospective_validation;
 if(!bound(data,"prospective_leagues",now)||!bound(data,"prospective_validation",now)||r.version!=="4.88"||r.mode!=="research_only"||r.realBettingEnabled!==false||r.decision!=="PAS"||r.updatedAt!==v.updatedAt||r.recorded!==v.recorded||!r.leagues||typeof r.leagues!=="object")return null;
 return r.leagues;
}
function fixtureCheck(row,data,now){
 const a=data.fixture_coverage_audit;
 if(!bound(data,"fixture_coverage_audit",now)||!bound(data,"daily",now)||a.version!=="4.92"||a.dailyUpdatedAt!==data.daily.updatedAt||a.archivesModified!==false||a.mode!=="research_only"||a.decision!=="PAS"||!arr(a.dates).includes(row.date))return null;
 const matches=arr(a.rows).filter(x=>arr(x.published).some(p=>key(p)===key(row)));
 if(matches.length!==1)return null;
 const x=matches[0];return {status:x.status,sourceDate:arr(x.espn).length===1?x.espn[0].date:null};
}
function scheduleBound(data,k,now){
 const m=data.snapshot_integrity,t=data[k]?.updatedAt;
 const age=s=>Number.isFinite(Date.parse(s))&&Date.parse(s)<=now&&now-Date.parse(s)<=86400000;
 return m?.status==="PASS"&&Array.isArray(m.errors)&&m.errors.length===0&&age(m.updatedAt)&&age(t)&&m.reportTimestamps?.[k+".json"]===t;
}
function lastKnownSchedule(row,data,now){
 if(!["daily","matching","odds"].every(k=>scheduleBound(data,k,now)))return null;
 if(data.odds.source!=="The Odds API"||data.odds.region!=="uk"||!Array.isArray(data.odds.errors)||data.odds.errors.length)return null;
 const matches=arr(data.matching.matched).filter(x=>x.match===row.match&&Number.isFinite(Date.parse(x.kickoff))&&dateTR(x.kickoff)===row.date);
 if(matches.length!==1)return null;
 const m=matches[0],events=arr(data.odds.events).filter(x=>x.id===m.eventId);
 if(events.length!==1||events[0].league!==LEAGUES[row.league]||events[0].kickoff!==m.kickoff||Date.parse(m.kickoff)<=now)return null;
 return {kickoff:m.kickoff,observedAt:data.odds.updatedAt};
}
function historicalStatsFor(row,data,now){
 const r=data.football_statistics_pilot;
 if(!scheduleBound(data,"daily",now)||!scheduleBound(data,"football_statistics_pilot",now)||r?.version!=="5.09"||r.source!=="football-data.co.uk"||r.mode!=="descriptive_research"||r.predictionsEnabled!==false||r.realBettingEnabled!==false||r.dailyUpdatedAt!==data.daily.updatedAt)return null;
 const matches=arr(r.groups).filter(g=>g.leagueName===row.league&&g.error===null).flatMap(g=>arr(g.rows).filter(x=>key(x)===key(row)));
 return matches.length===1?matches[0]:null;
}
function renderHistoricalStats(out,row){
 const r=historicalStatsFor(row,data,Date.now());
 out.append(node("h3","Son 10 lig maçı · tarihsel istatistik"));
 if(!r){out.append(node("p","Güncel istatistik kaynağı yok.","subtle"));return;}
 const fmt=x=>typeof x==="number"&&Number.isFinite(x)&&x>=0?x.toLocaleString("tr-TR",{maximumFractionDigits:2}):"—";
 for(const [label,k] of [["Korner","corners"],["Sarı kart","yellowCards"],["Kırmızı kart","redCards"],["Şut","shots"],["İsabetli şut","shotsOnTarget"],["İlk yarı gol","halfTimeGoals"]]){
   out.append(node("h3",label));
   for(const [side,title] of [["home","Ev sahibi"],["away","Deplasman"]]){
     const x=r[side]?.metrics?.[k];
     out.append(node("p",title+" · "+num(x?.sample)+" maç"),metrics([["Takım ort.",fmt(x?.forAverage)],["Rakip ort.",fmt(x?.againstAverage)]]));
   }
 }
 out.append(node("p","Kaynak: football-data.co.uk. Geçmiş gözlemler, tahmin değildir; eksik değerler sıfır sayılmaz.","subtle"));
}
function researchFor(row,data,now){
 const report=data.model_research;
 if(!scheduleBound(data,"daily",now)||!scheduleBound(data,"model_research",now)||report?.version!=="4.21"||report.mode!=="research_only"||report.rhoFitted!==false||report.modelCalibrated!==false||report.realBettingEnabled!==false||report.sourceUpdatedAt!==data.daily.updatedAt)return null;
 const matches=arr(report.rows).filter(x=>key(x)===key(row));
 return matches.length===1?matches[0]:null;
}
function scheduleFor(r){return r.event?.kickoff||r.lastKnown?.kickoff||null;}
function timeLabel(r){const t=scheduleFor(r);return t?hourTR(t)+" TSİ"+(r.event?"":" · Son bilinen"):"Saat belirsiz";}
function eventFor(row,data,now){if(!["daily","matching","odds"].every(k=>bound(data,k,now)))return null;const m=arr(data.matching.matched).filter(x=>x.match===row.match&&Number.isFinite(Date.parse(x.kickoff))&&dateTR(x.kickoff)===row.date);if(m.length!==1)return null;const e=arr(data.odds.events).filter(x=>x.id===m[0].eventId&&x.kickoff===m[0].kickoff&&x.league===LEAGUES[row.league]);return e.length===1?e[0]:null;}
function rowsFor(data,now){const candidates=new Map(arr(data.daily?.candidates).map(c=>[key(c),c])),unique=new Map();for(const r of arr(data.daily?.upcoming)){if(r&&typeof r.match==="string"&&typeof r.league==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&!unique.has(key(r)))unique.set(key(r),{...r,candidate:candidates.get(key(r))||null,event:eventFor(r,data,now),lastKnown:lastKnownSchedule(r,data,now),fixtureCheck:fixtureCheck(r,data,now)});}return [...unique.values()].sort((a,b)=>a.date.localeCompare(b.date)||String(scheduleFor(a)||"z").localeCompare(String(scheduleFor(b)||"z"))||a.league.localeCompare(b.league,"tr"));}
function confirmedRows(data,now,allowLastKnown=false){
 const verify=allowLastKnown?scheduleBound:bound;
 const k=data.kickoff_confirmation;
 if(!["daily","odds","fixture_coverage_audit","kickoff_confirmation"].every(x=>verify(data,x,now))||k.version!=="4.94"||k.available!==true||k.mode!=="research_only"||k.archivesModified!==false||k.decision!=="PAS"||k.dailyUpdatedAt!==data.daily.updatedAt||k.oddsUpdatedAt!==data.odds.updatedAt||k.coverageUpdatedAt!==data.fixture_coverage_audit.updatedAt)return [];
 const names={"en.1":"İngiltere Premier Lig","en.2":"İngiltere Championship","de.1":"Almanya Bundesliga","es.1":"İspanya La Liga","it.1":"İtalya Serie A","fr.1":"Fransa Ligue 1","nl.1":"Hollanda Eredivisie","pt.1":"Portekiz Primeira Liga","tr.1":"Türkiye Süper Lig"};
 const current=["daily","odds","fixture_coverage_audit","kickoff_confirmation"].every(x=>bound(data,x,now));
 const eligible=arr(k.rows).filter(x=>x.status==="agreed");
 const count=new Map();for(const x of eligible)count.set(x.oddsEventId,(count.get(x.oddsEventId)||0)+1);
 const out=[];
 for(const x of eligible){
   const league=names[x.league];
   if(!league||!x.oddsEventId||count.get(x.oddsEventId)!==1||!Number.isFinite(Date.parse(x.kickoff))||Date.parse(x.kickoff)<=now||dateTR(x.kickoff)!==x.date)continue;
   const events=arr(data.odds.events).filter(e=>e.id===x.oddsEventId&&e.league===LEAGUES[league]&&Date.parse(e.kickoff)===Date.parse(x.kickoff));
   if(events.length!==1)continue;
   const original=arr(x.published);
   out.push({date:x.date,league,match:x.match,event:current?{kickoff:x.kickoff}:null,lastKnown:current?null:{kickoff:x.kickoff,observedAt:k.updatedAt},candidate:null,confirmed:true,originalDate:original.length===1?original[0].date:null});
 }
 return out.sort((a,b)=>Date.parse(scheduleFor(a))-Date.parse(scheduleFor(b))||a.league.localeCompare(b.league,"tr"));
}
function filterRows(rows,q,d,l,t){const s=String(q||"").trim().toLocaleLowerCase("tr");return rows.filter(r=>(!s||r.match.toLocaleLowerCase("tr").includes(s))&&(!d||r.date===d)&&(!l||r.league===l)&&(!t||(scheduleFor(r)&&((hourTR(scheduleFor(r))<"17:00")===(t==="day")))));}
const LIVE_URL="https://raw.githubusercontent.com/akinsaran35-design/ortak-analiz/live-data/live_analysis_quality.json";
function liveRows(report,now){
 const age=t=>Number.isFinite(Date.parse(t))&&Date.parse(t)<=now&&now-Date.parse(t)<=120000;
 if(report?.version!=="5.15"||report.mode!=="live_analysis_quality_only"||report.predictionsEnabled!==false||report.sourceTimestampVerified!==false||report.decision!=="PAS"||!age(report.updatedAt)||!Array.isArray(report.rows)||report.rows.length>12)return [];
 const seen=new Map();
 for(const r of report.rows){const k=JSON.stringify([r?.league,r?.eventId]);seen.set(k,(seen.get(k)||0)+1);}
 const pair=x=>Array.isArray(x)&&x.length===2&&x.every(v=>Number.isFinite(v)&&v>=0);
 return report.rows.filter(r=>r&&seen.get(JSON.stringify([r.league,r.eventId]))===1&&r.quality==="observation_ready"&&typeof r.eventId==="string"&&/^[0-9]+$/.test(r.eventId)&&typeof r.home==="string"&&typeof r.away==="string"&&r.home!==r.away&&age(r.receivedAt)&&r.observation?.state==="in"&&pair(r.observation.score)&&typeof r.observation.clock==="string"&&["corners","shots","shotsOnTarget","yellowCards","redCards","possession"].every(k=>pair(r.observation.metrics?.[k])));
}
function teamLogo(catalog,league,name){
 if(catalog?.version!==1||catalog.source!=="ESPN team directory"||typeof name!=="string")return null;
 const entry=catalog.leagues?.[league]?.[name];
 if(typeof entry?.id!=="string"||!/^\d+$/.test(entry.id)||typeof entry.url!=="string")return null;
 return entry.url==="https://a.espncdn.com/i/teamlogos/soccer/500/"+entry.id+".png"||entry.url==="https://a.espncdn.com/i/teamlogos/soccer/500-dark/"+entry.id+".png"?entry.url:null;
}
function matchOverview(row,data,now){
 const model=researchFor(row,data,now),p=model?.scoreProbabilities,g=model?.expectedGoals;
 const valid=v=>typeof v==="number"&&Number.isFinite(v)&&v>=0&&v<=1;
 const outcomes=[p?.homeWin,p?.draw,p?.awayWin];
 const result=outcomes.every(valid)&&Math.abs(outcomes.reduce((a,b)=>a+b,0)-1)<1e-6?outcomes.map(v=>100*v):null;
 const goals=[g?.home,g?.away];
 return {result,goals:goals.every(v=>typeof v==="number"&&Number.isFinite(v)&&v>=0&&v<=10)?goals:null};
}
function movementFor(row,data,now){
 const event=eventFor(row,data,now),report=data.market_movement;
 if(!event||!bound(data,"market_movement",now)||report?.version!=="4.11"||report.mode!=="research_only"||report.decision!=="PAS"||!Array.isArray(report.errors)||report.errors.length)return [];
 return arr(report.markets).filter(x=>x.eventId===event.id&&x.kickoff===event.kickoff&&x.home===event.home&&x.away===event.away&&typeof x.market==="string"&&Number.isInteger(x.movementBookmakers)&&x.movementBookmakers>=3&&Number.isFinite(x.medianChangePP));
}
function statisticalExpectation(stats,k){
 const h=stats?.home?.metrics?.[k],a=stats?.away?.metrics?.[k];
 if(![h,a].every(x=>x&&Number.isInteger(x.sample)&&x.sample>=5&&x.sample<=10&&[x.forAverage,x.againstAverage].every(v=>typeof v==="number"&&Number.isFinite(v)&&v>=0)))return null;
 const home=(h.forAverage+a.againstAverage)/2,away=(a.forAverage+h.againstAverage)/2;
 return {home,away,total:home+away,homeSample:h.sample,awaySample:a.sample};
}
function formGoalAverages(side){
 const n=side?.sample,rows=side?.rows;
 if(!Number.isInteger(n)||n<1||n>5||!Array.isArray(rows)||rows.length!==n||!rows.every(x=>x&&Number.isInteger(x.gf)&&x.gf>=0&&Number.isInteger(x.ga)&&x.ga>=0))return null;
 const gf=rows.reduce((a,x)=>a+x.gf,0),ga=rows.reduce((a,x)=>a+x.ga,0);
 if(gf!==side.goalsFor||ga!==side.goalsAgainst)return null;
 return {scored:gf/n,conceded:ga/n,total:(gf+ga)/n,sample:n};
}
function accuracyCounts(x){
 if(!x||![x.tested,x.correct,x.incorrect].every(n=>Number.isSafeInteger(n)&&n>=0)||x.correct+x.incorrect!==x.tested)return null;
 return {...x,rate:x.tested?100*x.correct/x.tested:null};
}
function classificationFor(x){const a=x?.classification;if(a?.threshold!==.5||a.model!=="candidate"||a.descriptiveOnly!==true||a.tested!==x.tested)return null;return accuracyCounts(a);}
function shadowHistory(report,now){
 if(report?.version!=="4.8"||report.mode!=="shadow"||report.liveEnabled!==false||!Number.isFinite(Date.parse(report.updatedAt))||Date.parse(report.updatedAt)>now)return null;
 const keys=["recorded","settled","pending","won","lost"];
 function counts(x){
   if(!x||!keys.every(k=>Number.isSafeInteger(x[k])&&x[k]>=0)||x.settled+x.pending!==x.recorded||x.won+x.lost!==x.settled)return null;
   if(x.settled?(!Number.isFinite(x.winRate)||Math.abs(x.winRate-x.won/x.settled)>1e-10):x.winRate!==null)return null;
   return Object.fromEntries(keys.map(k=>[k,x[k]]).concat([["rate",x.settled?100*x.won/x.settled:null]]));
 }
 const total=counts(report.overall),sizes=[1,2,3].map(n=>counts(report.bySize?.[String(n)]));
 if(!total||sizes.some(x=>!x)||!keys.every(k=>sizes.reduce((sum,x)=>sum+x[k],0)===total[k]))return null;
 return {total,sizes,updatedAt:report.updatedAt};
}
// V6.61: read-only, separate prospective ML evidence. Never used for match-card predictions.
function mlResearchSummary(ledger,manifest,now,cohort="extra"){
 const config=cohort==="extra"?{version:"6.59",training:1791,leagues:["sco.1","bel.1","ger.2","esp.2","ita.2","fra.2"]}:cohort==="main"?{version:"6.67",training:2848,leagues:["en.1","en.2","de.1","es.1","it.1","fr.1","nl.1","pt.1","tr.1"]}:null;
 if(!config)return null;
 const obj=x=>x&&typeof x==="object"&&!Array.isArray(x);
 const hash=x=>typeof x==="string"&&/^[0-9a-f]{64}$/.test(x);
 const timestamp=x=>typeof x==="string"&&/(Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x));
 const markets=["over15","over25","btts"],models=["poisson","catboost","candidate"];
 const prob=p=>obj(p)&&Object.keys(p).length===3&&markets.every(k=>typeof p[k]==="number"&&Number.isFinite(p[k])&&p[k]>=0&&p[k]<=1)&&p.over15+1e-10>=Math.max(p.over25,p.btts);
 if(!obj(ledger)||!obj(manifest)||ledger.version!==config.version||manifest.version!==config.version||manifest.model!=="catboost"||manifest.weight!==.5||manifest.trainingMatches!==config.training||manifest.trainingSourceVerification!=="single_source_only"||manifest.trainingCutoff!=="2024-07-01"||!hash(manifest.modelSha256)||ledger.modelSha256!==manifest.modelSha256||!hash(manifest.trainingFingerprint)||!timestamp(manifest.frozenAt)||Date.parse(manifest.frozenAt)>now||!Array.isArray(manifest.featureKeys)||manifest.featureKeys.length!==119||new Set(manifest.featureKeys).size!==119||!["forecasts","settlements","quarantine"].every(k=>obj(ledger[k])))return null;
 const f=ledger.forecasts,s=ledger.settlements,q=ledger.quarantine;
 if([...Object.keys(s),...Object.keys(q)].some(k=>!Object.prototype.hasOwnProperty.call(f,k)))return null;
 const ids=new Set(),dates=new Set(),valid=[];let pending=0,last=Date.parse(manifest.frozenAt);
 for(const [k,r] of Object.entries(f)){
  if(!obj(r)||r.policyVersion!==config.version||r.modelSha256!==manifest.modelSha256||r.featureCount!==119||!hash(r.featureFingerprint)||r.trainingSourceVerification!=="single_source_only"||!config.leagues.includes(r.league)||typeof r.eventId!=="string"||!/^\d+$/.test(r.eventId)||typeof r.home!=="string"||typeof r.away!=="string"||!r.home||!r.away||r.home===r.away||k!==JSON.stringify([r.league,r.date,r.home,r.away])||!timestamp(r.recordedAt)||!timestamp(r.kickoff)||Date.parse(r.recordedAt)<Date.parse(manifest.frozenAt)||Date.parse(r.recordedAt)>now||Date.parse(r.recordedAt)>=Date.parse(r.kickoff)||dateTR(r.kickoff)!==r.date||dateTR(r.recordedAt)>=r.date||typeof r.historyThrough!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(r.historyThrough)||r.historyThrough>=dateTR(r.recordedAt)||!models.every(m=>prob(r[m]))||markets.some(m=>Math.abs(r.candidate[m]-(r.poisson[m]+r.catboost[m])/2)>1e-10))return null;
  const id=r.league+":"+r.eventId;if(ids.has(id))return null;ids.add(id);last=Math.max(last,Date.parse(r.recordedAt));
  if(Object.prototype.hasOwnProperty.call(s,k)){
   const v=s[k];if(!obj(v)||v.eventId!==r.eventId||!Array.isArray(v.sources)||v.sources.length!==2||!v.sources.includes("espn")||!v.sources.includes("football-data")||!Array.isArray(v.score)||v.score.length!==2||!v.score.every(x=>Number.isInteger(x)&&x>=0)||!timestamp(v.settledAt)||Date.parse(v.settledAt)>now||Date.parse(v.settledAt)<=Date.parse(r.kickoff)||dateTR(v.settledAt)<=r.date)return null;
   last=Math.max(last,Date.parse(v.settledAt));
   if(!Object.prototype.hasOwnProperty.call(q,k)){valid.push([r,v.score]);dates.add(r.date);}
  }else if(!Object.prototype.hasOwnProperty.call(q,k))pending++;
 }
 const n=valid.length,stats={};
 for(const [i,m] of markets.entries()){
  stats[m]={};for(const name of models){
   let correct=0,brier=0;for(const [r,[h,a]] of valid){const y=[h+a>=2,h+a>=3,h>0&&a>0][i],p=r[name][m];correct+=Number((p>=.5)===y);brier+=(p-Number(y))**2;}
   stats[m][name]={accuracyPct:n?100*correct/n:null,brier:n?brier/n:null};
  }
 }
 return {recorded:Object.keys(f).length,settled:n,pending,quarantined:Object.keys(q).length,days:dates.size,stats,lastEvidenceAt:new Date(last).toISOString()};
}
// V6.74: compare only locked pairs and independently settled scores, not all model forecasts.
function matchedMlSummary(pairs,ledger,manifest,now){
 const summary=mlResearchSummary(ledger,manifest,now,"main");
 const obj=x=>x&&typeof x==="object"&&!Array.isArray(x);
 const stamp=x=>typeof x==="string"&&/(Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x));
 const markets=["over15","over25","btts"],has=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
 const prob=p=>obj(p)&&Object.keys(p).length===3&&markets.every(k=>typeof p[k]==="number"&&Number.isFinite(p[k])&&p[k]>=0&&p[k]<=1)&&p.over15+1e-10>=Math.max(p.over25,p.btts);
 if(!summary||!obj(pairs)||pairs.version!=="6.69"||pairs.modelSha256!==manifest.modelSha256||!obj(pairs.pairs))return null;
 const valid=[],dates=new Set(),oldIds=new Set();let pending=0,quarantined=0,closeTiming=0;
 for(const [k,p] of Object.entries(pairs.pairs)){
  if(!has(ledger.forecasts,k)||!obj(p))return null;
  const f=ledger.forecasts[k];
  if(p.legacyVersion!=="1.6"||typeof p.legacyKey!=="string"||oldIds.has(p.legacyKey)||!prob(p.legacy)||!prob(p.candidate)||markets.some(m=>p.candidate[m]!==f.candidate[m])||typeof p.forecastFingerprint!=="string"||! /^[0-9a-f]{64}$/.test(p.forecastFingerprint)||!stamp(p.legacyRecordedAt)||!stamp(p.pairedAt)||dateTR(p.legacyRecordedAt)>=f.date||Date.parse(p.pairedAt)<Math.max(Date.parse(p.legacyRecordedAt),Date.parse(f.recordedAt))||Date.parse(p.pairedAt)>now||Date.parse(p.pairedAt)>=Date.parse(f.kickoff))return null;
  try{const a=JSON.parse(p.legacyKey);if(!Array.isArray(a)||a.length!==3||a[0]!==f.date||typeof a[1]!=="string"||typeof a[2]!=="string"||a[2].split(" – ").length!==2)return null;}catch(_){return null;}
  oldIds.add(p.legacyKey);
  if(Math.abs(Date.parse(p.legacyRecordedAt)-Date.parse(f.recordedAt))<=86400000)closeTiming++;
  if(has(ledger.quarantine,k)){quarantined++;continue;}
  if(!has(ledger.settlements,k)){pending++;continue;}
  valid.push([p,ledger.settlements[k].score]);dates.add(f.date);
 }
 const n=valid.length,stats={};
 for(const [i,m] of markets.entries()){
  stats[m]={};
  for(const name of ["legacy","candidate"]){
   let correct=0,brier=0;
   for(const [p,[h,a]] of valid){const y=[h+a>=2,h+a>=3,h>0&&a>0][i],v=p[name][m];correct+=Number((v>=.5)===y);brier+=(v-Number(y))**2;}
   stats[m][name]={accuracyPct:n?100*correct/n:null,brier:n?brier/n:null};
  }
 }
 return {paired:Object.keys(pairs.pairs).length,settled:n,pending,quarantined,days:dates.size,closeTiming,stats};
}
// V6.77: archive coverage is not current evidence; compute again at view time.
function extraMarketCoverage(data,now){
 const s=data?.extra_markets,a=data?.extra_market_archive;
 const stamp=x=>typeof x==="string"&&/(Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x));
 const price=x=>typeof x==="number"&&Number.isFinite(x)&&x>1;
 if(!s)return {status:"not_published",current:false,markets:null};
 if(s.source!=="The Odds API"||s.region!=="uk"||s.mode!=="research_only"||s.decision!=="PAS"||s.quotaPolicyVersion!=="6.89"||!stamp(s.updatedAt)||Date.parse(s.updatedAt)>now||!Array.isArray(s.errors)||!Array.isArray(s.events)||s.eventCount!==s.events.length)return {status:"invalid",current:false,markets:null};
 const archiveOK=a?.mode==="research_only"&&a?.integrityVersion==="6.85"&&a.quarantine&&typeof a.quarantine==="object"&&!Array.isArray(a.quarantine)&&bound(data,"extra_market_archive",now);
 const current=bound(data,"extra_markets",now)&&bound(data,"odds",now)&&s.oddsSnapshotAt===data.odds.updatedAt&&archiveOK&&s.errors.length===0;
 const status=s.errors.length?"source_error":s.quotaStatus==="quota_guard"?"quota_guard":s.quotaStatus==="no_eligible_events"?"no_eligible_events":s.quotaStatus==="reserve_preserved"?"observed":"not_checked";
 const ids=new Map(),base=new Map();
 for(const e of s.events)if(typeof e?.id==="string"&&e.id)ids.set(e.id,(ids.get(e.id)||0)+1);
 for(const e of arr(data.odds?.events))if(typeof e?.id==="string"&&e.id){if(base.has(e.id))base.set(e.id,null);else base.set(e.id,e);}
 const markets={};
 for(const [m,names] of [["over15",["Over","Under"]],["btts",["Yes","No"]]]){
  let observed=0,threeBooks=0,currentThree=0;
  for(const e of s.events){
   if(typeof e?.id!=="string"||!e.id||ids.get(e.id)!==1||Object.prototype.hasOwnProperty.call(a?.quarantine||{},e.id)||!stamp(e.kickoff)||Date.parse(e.kickoff)<=Date.parse(s.updatedAt))continue;
   const books=arr(e[m]),keys=new Map();
   for(const b of books)if(typeof b?.bookmaker==="string"&&b.bookmaker)keys.set(b.bookmaker,(keys.get(b.bookmaker)||0)+1);
   let n=0,f=0;
   for(const b of books){
    if(typeof b?.bookmaker!=="string"||!b.bookmaker||keys.get(b.bookmaker)!==1||!b.prices||!names.every(k=>price(b.prices[k]))||!stamp(b.lastUpdate)||Date.parse(b.lastUpdate)>Date.parse(s.updatedAt)||Date.parse(s.updatedAt)-Date.parse(b.lastUpdate)>1800000)continue;
    n++;if(fresh(b.lastUpdate,now))f++;
   }
   observed+=Number(n>=1);threeBooks+=Number(n>=3);
   const original=base.get(e.id);
   if(current&&original&&original.league===e.league&&original.home===e.home&&original.away===e.away&&stamp(original.kickoff)&&Date.parse(original.kickoff)===Date.parse(e.kickoff)&&Date.parse(e.kickoff)>now&&f>=3)currentThree++;
  }
  markets[m]={observed,threeBooks,currentThree:current?currentThree:null};
 }
 return {status,current,updatedAt:s.updatedAt,markets,attempts:Number.isInteger(s.paidRequestsAttempted)&&s.paidRequestsAttempted>=0&&s.paidRequestsAttempted<=3?s.paidRequestsAttempted:null};
}
function marketCoverageSummary(data,now){
 const s=data?.odds;
 const stamp=x=>typeof x==="string"&&/(Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x));
 const price=x=>typeof x==="number"&&Number.isFinite(x)&&x>1;
 if(!s||s.source!=="The Odds API"||s.region!=="uk"||s.market!=="totals"||!Array.isArray(s.errors)||s.errors.length||!stamp(s.updatedAt)||Date.parse(s.updatedAt)>now||!Array.isArray(s.events))return null;
 const counts=new Map();
 for(const e of s.events){if(typeof e?.id==="string"&&e.id)counts.set(e.id,(counts.get(e.id)||0)+1);}
 const current=bound(data,"odds",now),markets={};
 for(const point of [1.5,2.5]){
  let observed=0,threeBooks=0,currentThree=0;
  for(const e of s.events){
   if(typeof e?.id!=="string"||!e.id||counts.get(e.id)!==1||!stamp(e.kickoff)||Date.parse(e.kickoff)<=Date.parse(s.updatedAt))continue;
   const books=arr(e.bookmakers),keys=new Map();
   for(const b of books){if(typeof b?.key==="string"&&b.key)keys.set(b.key,(keys.get(b.key)||0)+1);}
   let n=0,f=0;
   for(const b of books){
    if(typeof b?.key!=="string"||!b.key||keys.get(b.key)!==1)continue;
    const lines=arr(b.lines).filter(l=>l?.point===point);
    if(lines.length!==1)continue;
    const l=lines[0];
    if(!price(l.over)||!price(l.under)||!stamp(l.lastUpdate)||Date.parse(l.lastUpdate)>Date.parse(s.updatedAt))continue;
    n++;if(fresh(l.lastUpdate,now))f++;
   }
   observed+=Number(n>=1);threeBooks+=Number(n>=3);
   currentThree+=Number(current&&Date.parse(e.kickoff)>now&&f>=3);
  }
  markets[point]={observed,threeBooks,currentThree:current?currentThree:null};
 }
 return {snapshotAt:s.updatedAt,archivedEvents:s.events.length,current,markets,bttsRequested:false};
}
// V6.64: same-event, same-book observations; no opening-price claim.
function observedTotalsFor(row,data,now,point){
 const event=eventFor(row,data,now),report=data.observed_totals_report;
 const validPrice=x=>typeof x==="number"&&Number.isFinite(x)&&x>1;
 const median=v=>{const a=[...v].sort((x,y)=>x-y),i=Math.floor(a.length/2);return a.length?(a.length%2?a[i]:(a[i-1]+a[i])/2):null;};
 if(!event||!Number.isFinite(Date.parse(event.kickoff))||Date.parse(event.kickoff)<=now||![1.5,2.5].includes(point))return null;
 const books=arr(event.bookmakers),counts=new Map();for(const b of books)counts.set(b.key,(counts.get(b.key)||0)+1);
 const current=new Map();
 for(const b of books){
   if(typeof b.key!=="string"||!b.key||counts.get(b.key)!==1)continue;
   const lines=arr(b.lines).filter(l=>l.point===point);
   if(lines.length!==1)continue;
   const l=lines[0];if(validPrice(l.over)&&validPrice(l.under)&&fresh(l.lastUpdate,now)&&Date.parse(l.lastUpdate)<=Date.parse(data.odds.updatedAt))current.set(b.key,l);
 }
 const result={current:median([...current.values()].map(l=>l.over)),currentCount:current.size,first:null,dropPct:null,comparableCount:0};
 if(data.odds.source!=="The Odds API"||data.odds.region!=="uk"||data.odds.market!=="totals"||!Array.isArray(data.odds.errors)||data.odds.errors.length||report?.version!=="6.63"||report.mode!=="research_only"||report.realBettingEnabled!==false||report.firstObservedIsOpening!==false||report.status!=="observed"||report.oddsUpdatedAt!==data.odds.updatedAt||!fresh(report.updatedAt,now)||Date.parse(report.updatedAt)<Date.parse(report.oddsUpdatedAt))return result;
 const rows=arr(report.events).filter(x=>x.eventId===event.id&&x.point===point);if(rows.length!==1)return result;
 const r=rows[0],seen=new Set(),pairs=[];
 for(const b of arr(r.books)){
   if(seen.has(b.bookmaker))return result;seen.add(b.bookmaker);
   const l=current.get(b.bookmaker);
   if(!l||!validPrice(b.firstObserved)||b.current!==l.over||b.currentLastUpdate!==l.lastUpdate||!Number.isFinite(Date.parse(b.firstObservedAt))||Date.parse(b.firstObservedAt)>=Date.parse(data.odds.updatedAt)||b.dropPct===null||typeof b.dropPct!=="number"||!Number.isFinite(b.dropPct)||Math.abs(b.dropPct-100*(b.firstObserved-b.current)/b.firstObserved)>1e-8)continue;
   pairs.push(b);
 }
 if(pairs.length>=3){result.comparableCount=pairs.length;result.first=median(pairs.map(b=>b.firstObserved));result.current=median(pairs.map(b=>b.current));result.dropPct=median(pairs.map(b=>b.dropPct));}
 return result;
}
if(typeof module!=="undefined"&&module.exports)module.exports={extraMarketCoverage,marketCoverageSummary,observedTotalsFor,mlResearchSummary,matchedMlSummary,shadowHistory,accuracyCounts,classificationFor,formGoalAverages,statisticalExpectation,matchOverview,movementFor,teamLogo,liveRows,topScores,eventFor,rowsFor,filterRows,bound,leagueReport,fixtureCheck,confirmedRows,lastKnownSchedule,timeLabel,researchFor,historicalStatsFor};
if(typeof document==="undefined")return;
const by=id=>document.getElementById(id),node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let data={},rows=[],loadedAt=0,refreshing=false,opened=null,listScroll=0;
function expirySignature(data,now){return liveRows(data.live_analysis_quality,now).length+':'+FILES.map(k=>fresh(data[k]?.updatedAt,now)?1:0).join('')+dateTR(now)+':'+confirmedRows(data,now).length+":"+confirmedRows(data,now,true).length+':'+FILES.map(k=>scheduleBound(data,k,now)?1:0).join('')+':'+rowsFor(data,now).filter(r=>r.lastKnown).length;}
function expireView(){if(!refreshing&&loadedAt&&expirySignature(data,loadedAt)!==expirySignature(data,Date.now()))render();}
function metrics(values){const box=node("div",undefined,"metrics");for(const [label,value] of values){const c=node("div",undefined,"metric");c.append(node("b",value),node("small",label));box.append(c);}return box;}
function displayNumber(v){return typeof v==="number"&&Number.isFinite(v)?v.toLocaleString("tr-TR",{maximumFractionDigits:2}):"—";}
function overviewPanel(r){
 const v=matchOverview(r,data,Date.now()),box=node("article",undefined,"panel overview-panel");
 box.append(node("h3","Maç sonucu · MS 1 / X / 2"),metrics([["MS 1",pct(v.result?.[0])],["Beraberlik",pct(v.result?.[1])],["MS 2",pct(v.result?.[2])]]),node("h3","Maç öncesi gol beklentisi"),metrics([["Ev sahibi",displayNumber(v.goals?.[0])],["Toplam",displayNumber(v.goals?v.goals[0]+v.goals[1]:null)],["Deplasman",displayNumber(v.goals?.[1])]]),node("p","Model güvenilirliği: kalibrasyon tamamlanmadı. Gol beklentisi istatistiksel maç öncesi modeldir; canlı xG veya tempo değildir.","subtle"));
 return box;
}
function unavailablePanel(title,labels,note){
 const b=node("article",undefined,"panel");b.append(node("h3",title),metrics(labels.map(k=>[k,"—"])),node("p",note,"subtle"));return b;
}
function signalPanel(r){
 const b=node("article",undefined,"panel radar-signals");
 b.append(node("h3","Maç sinyalleri"),node("p",r?"Son gözlem: "+hourTR(r.receivedAt)+" TSİ · ESPN":"Canlı veri bekleniyor","subtle"));
 for(const [label,cls] of [["Yüksek tempo","hot"],["Gol beklentisi","goal"],["Düşük tempo","cold"],["Kalan sürede gol olmayabilir","cold"]]){
   const line=node("div",undefined,"signal-line "+cls);line.append(node("span",label),node("strong","Veri bekleniyor"));b.append(line);
 }
 b.append(metrics([["Son 5 dk","—"],["Son 10 dk","—"],["Son 15 dk","—"]]),node("p","Son dakika olay geçmişi, canlı xG ve doğrulanmış sinyal modeli henüz bağlı değil. Bildirimler etkin değil.","subtle"));return b;
}
function returnCalculator(){
 const b=node("article",undefined,"panel return-calc"),amount=node("input"),odds=node("input"),total=node("strong","— TL"),net=node("strong","— TL");
 amount.type=odds.type="number";amount.min="0";amount.step="0.01";odds.min="1";odds.step="0.01";
 amount.placeholder="0,00";odds.placeholder="Örn. 1,80";amount.setAttribute("aria-label","Kendi tutarın");odds.setAttribute("aria-label","Ondalık oran");
 const fields=node("div",undefined,"return-fields"),a=node("label","Kendi tutarın (TL)"),o=node("label","Ondalık oran");a.append(amount);o.append(odds);fields.append(a,o);
 const values=node("div",undefined,"metrics");for(const [label,value] of [["Olası brüt dönüş",total],["Olası net sonuç",net]]){const m=node("div",undefined,"metric");m.append(value,node("small",label));values.append(m);}
 const recalc=()=>{const x=amount.valueAsNumber,y=odds.valueAsNumber,ok=Number.isFinite(x)&&Number.isFinite(y)&&x>=0&&x<=1e8&&y>=1&&y<=1e5;const fmt=v=>v.toLocaleString("tr-TR",{style:"currency",currency:"TRY"});total.textContent=ok?fmt(x*y):"— TL";net.textContent=ok?fmt(x*(y-1)):"— TL";};amount.oninput=odds.oninput=recalc;
 b.append(node("h3","Elle geri dönüş hesabı"),fields,values,node("p","Yalnızca kendi girdiğin tutar ve oranla aritmetik hesap. Bahis tutarı önerisi veya garanti değildir.","subtle"));return b;
}
function teamTitle(match,league){const parts=match.split(" – "),title=node("span",undefined,"match-title");if(parts.length!==2){title.textContent=match;return title;}for(const [i,name] of parts.entries()){if(i)title.append(node("span","VS","versus"));const team=node("span",undefined,"team-name"),crest=node("span",name.split(/\s+/).slice(0,2).map(w=>w[0]).join("").toUpperCase(),"team-crest"+(i?" away":""));crest.setAttribute("aria-hidden","true");const url=teamLogo(data.team_logos,league,name);if(url){const img=node("img");img.alt="";img.loading="lazy";img.decoding="async";img.referrerPolicy="no-referrer";img.addEventListener("load",()=>crest.classList.add("has-logo"),{once:true});img.addEventListener("error",()=>{img.remove();crest.classList.remove("has-logo");},{once:true});img.src=url;crest.append(img);}team.append(crest,node("span",name,"team-label"));title.append(team);}return title;}
function probabilityBars(markets){const root=node("div");for(const m of MARKETS){const value=markets?.[m],row=node("div",undefined,"prob-row"),track=node("div",undefined,"prob-track"),fill=node("div",undefined,"prob-fill");fill.style.width=(typeof value==="number"&&Number.isFinite(value)&&value>=0&&value<=100?value:0)+"%";track.append(fill);row.append(node("span",m),track,node("b",pct(value)));root.append(row);}return root;}
function oddsRange(event,point,now){const v=arr(event?.bookmakers).flatMap(b=>arr(b.lines).filter(l=>l.point===point&&fresh(l.lastUpdate,now)&&typeof l.over==="number"&&Number.isFinite(l.over)&&l.over>1).map(l=>l.over));return v.length?Math.min(...v).toFixed(2)+(Math.max(...v)!==Math.min(...v)?"–"+Math.max(...v).toFixed(2):""):"—";}
function personalPanel(r){const box=node("article",undefined,"panel personal-detail");box.append(node("h3","Kişisel para kaydı"));for(const [label,value] of [["Yatırılan tutar","— TL"],["2.5 Üst oran aralığı",oddsRange(r.event,2.5,Date.now())],["Gerçek geri dönüş","— TL"],["Net sonuç","— TL"]]){const line=node("div",undefined,"personal-line");line.append(node("span",label),node("strong",value));box.append(line);}box.append(node("p","Bu maçla eşleştirilmiş kişisel kayıt yok. Önerilen bahis tutarı üretilmiyor.","subtle"));const b=node("button","Kişisel kayıt defterini aç","action");b.type="button";b.onclick=()=>{closeDetail();by("tab-coupons").click();};box.append(b);return box;}
function showDetail(r,remember=true){
 if(remember)listScroll=window.scrollY;
 opened=key(r);
 by("view-matches").hidden=true;
 by("match-detail-screen").hidden=false;
 document.body.classList.add("detail-active");
 const hero=by("detail-hero");hero.replaceChildren(node("p",r.league,"detail-league"),teamTitle(r.match,r.league),node("p",r.date+" · "+timeLabel(r),"detail-time"));
 const priorTab=remember?null:by("detail-content").querySelector("[data-detail-tab][aria-pressed=true]")?.dataset.detailTab;by("detail-content").replaceChildren(detail(r));if(priorTab)for(const tab of by("detail-content").querySelectorAll("[data-detail-tab]"))if(tab.dataset.detailTab===priorTab)tab.click();
 if(remember){window.scrollTo(0,0);by("detail-back").focus({preventScroll:true});}
}
function closeDetail(){
 if(opened===null)return;
 opened=null;by("match-detail-screen").hidden=true;document.body.classList.remove("detail-active");by("view-matches").hidden=false;window.scrollTo(0,listScroll);
}
function historyForm(r){return scheduleBound(data,"daily",Date.now())&&r.formResearch?.version==="5.06"?r.formResearch:null;}
function resultChip(v){const chip=node("span",({W:"G",D:"B",L:"M"})[v]||"—","history-result "+(({W:"win",D:"draw",L:"loss"})[v]||""));chip.title=({W:"Galibiyet",D:"Beraberlik",L:"Mağlubiyet"})[v]||"Sonuç yok";return chip;}
function historyPanel(title){const b=node("article",undefined,"panel history-panel");b.append(node("h3",title));return b;}
function historyNote(b,message){b.append(node("p",message,"subtle"));}
function h2hPanel(r){
 const b=historyPanel("Karşılıklı maçlar · H2H"),f=historyForm(r),names=r.match.split(" – "),seen=new Set(),matches=arr(f?.h2h).filter(y=>{
 if(!y||typeof y.date!=="string"||y.date>=r.date||!names.includes(y.home)||!names.includes(y.away)||y.home===y.away||!Array.isArray(y.score)||y.score.length!==2||!y.score.every(v=>Number.isInteger(v)&&v>=0))return false;
 const k=JSON.stringify([y.date,y.home,y.away]);if(seen.has(k))return false;seen.add(k);return true;
 }).sort((a,b)=>b.date.localeCompare(a.date));
 if(!matches.length){historyNote(b,"Doğrulanmış tarihli geçmiş kayıt yok.");return b;}
 let w=0,d=0,l=0,gf=0,ga=0,over=0,btts=0;
 for(const y of matches){const [h,a]=y.home===names[0]?y.score:[y.score[1],y.score[0]];gf+=h;ga+=a;if(h>a)w++;else if(h<a)l++;else d++;if(h+a>=3)over++;if(h&&a)btts++;}
 b.append(node("p",matches.length+" kayıtlı lig karşılaşması","history-count"),metrics([[names[0]+" galibiyet",String(w)],["Beraberlik",String(d)],[names[1]+" galibiyet",String(l)]]),metrics([["Gol · "+names[0],String(gf)],["2.5 Üst",over+"/"+matches.length],["Gol · "+names[1],String(ga)]]),node("p","KG Var: "+btts+"/"+matches.length+" maç","history-count"));
 for(const y of matches){const card=node("div",undefined,"history-match");card.append(node("span",y.date,"history-date"),teamTitle(y.home+" – "+y.away,r.league),node("strong",y.score.join(" – "),"history-score"));b.append(card);}
 historyNote(b,"Sadece erişilebilen lig geçmişi; kupa ve diğer organizasyonlar dahil değil. Sayılar tarihsel örneklemdir, gelecek maç olasılığı değildir.");return b;
}
function formGoalComparison(f,names){
 const b=node("section",undefined,"form-team form-goal-comparison"),h=formGoalAverages(f.home),a=formGoalAverages(f.away);
 b.append(node("h3","Maç başına gol ortalamaları"));
 const head=node("div",undefined,"history-compare-head");head.append(node("strong",names[0]),node("span","ORTALAMA"),node("strong",names[1]));b.append(head);
 for(const [label,k] of [["Atılan gol","scored"],["Yenilen gol","conceded"],["Toplam gol","total"]]){
 const row=node("div",undefined,"history-compare-row");row.append(node("strong",displayNumber(h?.[k])),node("div",label,"history-compare-label"),node("strong",displayNumber(a?.[k])));b.append(row);
 }
 const samples=node("div",undefined,"history-samples");samples.append(node("span",h?h.sample+" maç":"Veri yok"),node("span",a?a.sample+" maç":"Veri yok"));b.append(samples);historyNote(b,"Son en fazla 5 kayıtlı lig maçı. Geçmiş gol ortalaması, maç tahmini değildir.");return b;
}
function formPanels(r){
 const b=historyPanel("Son 5 kayıtlı lig maçı"),f=historyForm(r),names=r.match.split(" – ");
 if(!f){historyNote(b,"Güncel form raporu yok.");return b;}
 b.append(formGoalComparison(f,names));
 for(const [i,side] of [f.home,f.away].entries()){
 if(!side)continue;
 const card=node("section",undefined,"form-team"),header=node("div",undefined,"form-team-head");
 header.append(node("strong",names[i]||"Takım"),node("span",String(side.sample)+" maç","history-count"));card.append(header);
 const strip=node("div",undefined,"form-strip");for(const y of arr(side.rows))strip.append(resultChip(y.result));card.append(strip,metrics([["Galibiyet",num(side.wins)],["Beraberlik",num(side.draws)],["Mağlubiyet",num(side.losses)]]),metrics([["Attığı gol",num(side.goalsFor)],["Yediği gol",num(side.goalsAgainst)],["Puan",Number.isInteger(side.wins)&&Number.isInteger(side.draws)?String(side.wins*3+side.draws):"—"]]));
 for(const y of arr(side.rows)){const line=node("div",undefined,"form-match"),left=node("div",undefined,"form-opponent");left.append(node("strong",y.opponent),node("small",y.date+" · "+(y.venue==="home"?"İç saha":"Dış saha")));line.append(resultChip(y.result),left,node("strong",num(y.gf)+" – "+num(y.ga),"form-score"));card.append(line);}
 const latest=arr(side.rows)[0]?.date;if(latest)historyNote(card,"Son kayıt: "+latest+" · Daha yeni maçlar kaynakta eksik olabilir.");b.append(card);
 }
 historyNote(b,"G = galibiyet, B = beraberlik, M = mağlubiyet. Mevcut lig geçmişi; kadro ve sakatlık verileri dahil değil.");return b;
}
function historicalComparison(r,title,fields){
 const b=historyPanel(title),stats=historicalStatsFor(r,data,Date.now()),names=r.match.split(" – ");
 if(!stats){historyNote(b,"Güncel ve bütünlüğü doğrulanmış istatistik kaynağı yok.");return b;}
 const head=node("div",undefined,"history-compare-head");head.append(node("strong",names[0]||"Ev sahibi"),node("span","ORTALAMA"),node("strong",names[1]||"Deplasman"));b.append(head);
 for(const [label,k,which] of fields){
 const h=stats.home?.metrics?.[k],a=stats.away?.metrics?.[k],line=node("div",undefined,"history-compare-row");
 line.append(node("strong",h?.sample>0?displayNumber(h[which]):"—"),node("div",label,"history-compare-label"),node("strong",a?.sample>0?displayNumber(a[which]):"—"));b.append(line);
 const samples=node("div",undefined,"history-samples");samples.append(node("span",num(h?.sample)+" maç"),node("span",num(a?.sample)+" maç"));b.append(samples);
 }
 historyNote(b,"Kaynak: football-data.co.uk · Son en fazla 10 lig maçı. Gözlem ortalamaları, tahmin değildir.");return b;
}
function expectationPanel(r,title,fields){
 const b=historyPanel(title),stats=historicalStatsFor(r,data,Date.now()),names=r.match.split(" – "),grid=node("div",undefined,"expectation-grid");
 for(const [label,k,cls] of fields){
 const v=statisticalExpectation(stats,k),card=node("section",undefined,"expectation-card "+cls);
 card.append(node("span",label,"expectation-label"),node("strong",displayNumber(v?.total),"expectation-total"));
 if(v){const details=node("div",undefined,"expectation-split");details.append(node("span",names[0]+" · "+displayNumber(v.home)),node("span",names[1]+" · "+displayNumber(v.away)));card.append(details,node("small",v.homeSample+" / "+v.awaySample+" geçmiş maç","subtle"));}
 else card.append(node("small","Yeterli veri yok · en az 5 maç/takım","subtle"));
 grid.append(card);
 }
 b.append(grid,node("p","Basit istatistiksel beklenti: takım ortalaması ile rakip ortalamasının aritmetik ortalaması. Kesin sonuç, bahis olasılığı veya kalibre edilmiş tahmin değildir.","subtle"));return b;
}
function modelPending(title,description){const b=historyPanel(title);historyNote(b,description);return b;}
function detail(r){if(r.confirmed){
 const box=node("div",undefined,"detail");
 box.append(node("p","ESPN ve uluslararası oran kaynağında aynı başlama saati.","subtle"));
 if(r.originalDate&&r.originalDate!==r.date)box.append(node("p","Eski fikstür tarihi: "+r.originalDate+". Arşivdeki tahmin değiştirilmedi.","subtle"));
 box.append(node("p","Bu görünüm yalnızca fikstür doğrulamasıdır. Model tahmini veya bahis seçimi aktarılmaz.","subtle"));return box;
 }r={...r,event:eventFor(r,data,Date.now())};const x=node("div",undefined,"detail"),tabs=node("div",undefined,"detail-tabs"),out=node("div"),c=r.candidate;
const views={
"Analiz":()=>{const probabilities=node("article",undefined,"panel analysis-panel");probabilities.append(node("h3","◉ Model olasılıkları"));
 if(c)probabilities.append(probabilityBars(c.markets),node("p","Kalibre edilmemiş model; kazanma garantisi değildir.","subtle"));
 else probabilities.append(node("p","Model tahmini yok.","subtle"));
 const scores=topScores(c?.expectedGoals?.home,c?.expectedGoals?.away),score=node("article",undefined,"panel score-panel");score.append(node("h3","▥ En olası skorlar"),node("strong",scores.length?scores.map(s=>s.score).join(", "):"—","score-line"),node("p","Poisson model senaryoları","subtle"));
 out.append(overviewPanel(r),probabilities,score,personalPanel(r));},
"Skor":()=>{const s=topScores(c?.expectedGoals?.home,c?.expectedGoals?.away),box=node("article",undefined,"panel score-scenarios");box.append(node("h3","En olası skor senaryoları"),node("p",s.length?"Bağımsız Poisson modelinin en olası 3 skor senaryosu.":"Skor modeli verisi yok.","subtle"));for(const [i,y] of s.entries()){const card=node("div",undefined,"score-scenario"),top=node("div",undefined,"score-scenario-top"),label=node("span",i===0?"En yüksek model olasılığı":"Senaryo "+(i+1),"score-rank"),score=node("strong",y.score,"score-value"),prob=node("strong",pct(y.p),"score-percent"),track=node("div",undefined,"prob-track"),fill=node("div",undefined,"prob-fill");fill.style.width=Math.max(0,Math.min(100,y.p))+"%";track.append(fill);top.append(score,prob);card.append(label,top,track);box.append(card);}box.append(node("p","Skor senaryoları toplam olasılığın yalnızca bir bölümüdür. Kalibrasyon tamamlanmadı.","subtle"));out.append(box,overviewPanel(r));},
"Oranlar":()=>{const now=Date.now();for(const point of [2.5,1.5]){const h=observedTotalsFor(r,data,now,point);const p=node("article",undefined,"panel");p.append(node("h3",point+" Üst · Oran geçmişi"),metrics([["İlk gözlenen",h?.first!=null?h.first.toFixed(2):"—"],["Güncel",h?.current!=null?h.current.toFixed(2):"—"],["Düşüş %",h?.dropPct!=null?displayNumber(h.dropPct)+"%":"—"]]),node("p",h?.comparableCount>=3?h.comparableCount+" aynı kaynak · medyan değişim; ilk gözlenen gerçek açılış değildir.":(h?.currentCount||0)+" güncel kaynak · değişim için en az üç aynı kaynağın iki ayrı kaydı gerekir. İlk gözlenen gerçek açılış değildir.","subtle"));out.append(p);}if(!r.event){out.append(node("p","Kesin eşleşen güncel oran kaydı yok.","subtle"));return;}for(const p of [1.5,2.5]){const v=arr(r.event.bookmakers).flatMap(b=>arr(b.lines).filter(l=>l.point===p&&fresh(l.lastUpdate,Date.now())&&typeof l.over==="number"&&l.over>1).map(l=>l.over));out.append(node("p",p+" Üst: "+(v.length?v.length+" kaynak · "+Math.min(...v).toFixed(2)+"–"+Math.max(...v).toFixed(2):"Veri yok")));}const movement=movementFor(r,data,Date.now());for(const m of movement)out.append(node("p",m.market+" · "+m.movementBookmakers+" kaynak · "+displayNumber(m.medianChangePP)+" yüzde puan"));if(!movement.length)out.append(node("p","Doğrulanmış oran hareketi yok.","subtle"));},
"İstatistik":()=>{renderHistoricalStats(out,r);const model=researchFor(r,data,Date.now());out.append(node("h3","Gol modeli karşılaştırması"));if(!model){out.append(node("p","Bütünlüğü kontrol edilmiş model raporu yok.","subtle"));return;}out.append(node("p","Aynı gol beklentisinden üretilen deneysel dağılımlar. Bağımsız tahminler veya doğrulanmış kazanma olasılıkları değildir.","subtle"));for(const [name,k] of [["1.5 Üst","over15"],["2.5 Üst","over25"],["KG Var","btts"]]){out.append(node("h3",name),metrics([["Poisson",pct(100*model.poisson?.[k])],["Dixon-Coles",pct(100*model.experimentalDixonColes?.[k])],["Monte Carlo",pct(100*model.simulation?.markets?.[k]?.probability)]]));}out.append(node("p","Dixon-Coles katsayısı sabit deneysel değerdir; Monte Carlo aynı dağılımın 20.000 örnekli sayısal kontrolüdür. Kadro ve sakatlık verileri henüz bağlı değil.","subtle"));},
"H2H":()=>out.append(h2hPanel(r)),
"Form":()=>out.append(formPanels(r)),
"İlk yarı":()=>out.append(expectationPanel(r,"İlk yarı gol beklentisi",[["Toplam ilk yarı golü","halfTimeGoals","corners"]]),historicalComparison(r,"İlk yarı · tarihsel gol ortalamaları",[["Atılan gol","halfTimeGoals","forAverage"],["Yenilen gol","halfTimeGoals","againstAverage"]]),modelPending("İlk yarı tahminleri","İY 0.5 Üst, İY 1.5 Üst, İY KG Var, İY/MS ve iki yarı KG Var modelleri doğrulanmadı.")),
"Korner / kart":()=>out.append(expectationPanel(r,"Maç geneli beklentisi",[["Korner","corners","corners"],["Sarı kart","yellowCards","yellow"],["Kırmızı kart","redCards","red"]]),historicalComparison(r,"Korner ve kart · tarihsel ortalamalar",[["Kullanılan korner","corners","forAverage"],["Verilen korner","corners","againstAverage"],["Sarı kart","yellowCards","forAverage"],["Rakip sarı kart","yellowCards","againstAverage"],["Kırmızı kart","redCards","forAverage"],["Rakip kırmızı kart","redCards","againstAverage"]]),modelPending("Korner ve kart tahmini","Bu pazarlar için doğrulanmış tahmin modeli henüz yok.")),
"Sinyaller":()=>out.append(signalPanel(null)),
"Diğer":()=>out.append(returnCalculator(),unavailablePanel("Model güvenilirliği",["Kalibrasyon","Canlı doğrulama","Örneklem"],"Doğrulanmış canlı model henüz yok."))};
for(const name of Object.keys(views)){const b=node("button",name);b.type="button";b.setAttribute("aria-pressed","false");b.dataset.detailTab=name;b.onclick=()=>{for(const t of tabs.children)t.setAttribute("aria-pressed",String(t===b));out.replaceChildren();views[name]();};tabs.append(b);}const check=fixtureCheck(r,data,Date.now());if(check?.status==="date_difference")x.append(node("p","Tarih uyuşmazlığı: mevcut liste "+r.date+" / ESPN "+check.sourceDate+". Orijinal kayıt değiştirilmedi.","subtle"));else if(check?.status==="same_date")x.append(node("p","Fikstür tarihi ESPN ile eşleşiyor.","subtle"));else if(check)x.append(node("p","İkinci kaynakta kesin fikstür eşleşmesi yok.","subtle"));x.append(tabs,out);tabs.firstChild.click();return x;}
function quickMarkets(r){const el=node("span",undefined,"quick-markets");if(r.candidate&&!r.confirmed){for(const m of MARKETS){const p=pct(r.candidate.markets?.[m]);const tile=node("span");const track=node("span",undefined,"quick-track"),fill=node("span",undefined,"quick-fill");const v=r.candidate.markets?.[m];fill.style.width=(Number.isFinite(v)&&v>=0&&v<=100?v:0)+"%";track.append(fill);tile.append(node("small",m),node("strong",p),track);el.append(tile);}}else el.append(node("span","Model yüzdesi yok"));return el;}
function renderDateRail(){const rail=by("date-rail"),selected=by("date-filter").value;rail.replaceChildren();const dates=[...new Set(rows.map(r=>r.date))].sort();for(const d of ["",...dates]){const b=node("button",undefined,"date-chip");b.type="button";b.setAttribute("aria-pressed",String(d===selected));if(d){const t=new Date(d+"T12:00:00+03:00");b.append(node("small",d===dateTR(Date.now())?"BUGÜN":d===dateTR(Date.now()+86400000)?"YARIN":new Intl.DateTimeFormat("tr-TR",{weekday:"short",timeZone:"Europe/Istanbul"}).format(t)),node("strong",new Intl.DateTimeFormat("tr-TR",{day:"numeric",month:"short",timeZone:"Europe/Istanbul"}).format(t)));}else b.append(node("small","FİKSTÜR"),node("strong","Tümü"));b.onclick=()=>{by("date-filter").value=d;renderList();};rail.append(b);}}
function renderList(){renderDateRail();const result=filterRows(rows,by("search").value,by("date-filter").value,by("league-filter").value,by("time-filter").value),box=by("match-list");by("match-count").textContent=result.length+" maç";box.replaceChildren();let lastDate=null;for(const r of result){if(r.date!==lastDate){lastDate=r.date;const label=new Intl.DateTimeFormat("tr-TR",{weekday:"long",day:"numeric",month:"long",timeZone:"Europe/Istanbul"}).format(new Date(r.date+"T12:00:00+03:00"));const group=node("div",undefined,"date-group");group.append(node("strong",label),node("small",result.filter(x=>x.date===r.date).length+" maç"));box.append(group);}const card=node("article",undefined,"match-card"),s=node("button",undefined,"match-open");s.type="button";s.append(node("span","⚽ "+r.league+(r.confirmed?(r.event?" · İki kaynak":" · Son eşleşme"):r.fixtureCheck?.status==="date_difference"?" · Tarih farkı":""),"match-meta"),teamTitle(r.match,r.league),node("span",r.date+" · "+timeLabel(r),"match-time"),node("span",r.confirmed?"Fikstür doğrulaması":r.candidate?"Model analizi • Kalibre edilmedi":"Tahmin verisi yok","match-summary-label"),quickMarkets(r),node("span","2.5 Üst oran aralığı: "+oddsRange(r.event,2.5,Date.now()),"odds-summary"));card.append(s);s.onclick=()=>showDetail(r);box.append(card);}if(!result.length)box.append(node("p",rows.length?"Filtreye uygun maç bulunamadı.":by("fixture-mode").value==="confirmed"?"Güncel çift kaynaklı saat kaydı yok. Genel listeyi seçebilirsin.":by("fixture-mode").value==="last-confirmed"?"Son 24 saatte eşleşen ileri tarihli fikstür yok.":"Yayımlanan maç listesi okunamadı.","subtle"));}
function options(id,values,label){const e=by(id),old=e.value;e.replaceChildren(node("option",label));e.firstChild.value="";for(const v of values){const o=node("option",v);o.value=v;e.append(o);}if(values.includes(old))e.value=old;}
function panel(root,title,body){const p=node("article",undefined,"panel");p.append(node("h3",title));for(const el of body)p.append(el);root.append(p);}
function render(){loadedAt=Date.now();rows=by("fixture-mode").value==="confirmed"?confirmedRows(data,loadedAt):by("fixture-mode").value==="last-confirmed"?confirmedRows(data,loadedAt,true):rowsFor(data,loadedAt);const current=["daily","matching","odds","prospective_validation","data_quality","unified_decision"].every(k=>bound(data,k,loadedAt))&&data.data_quality?.qualityGate==="PASS";if(opened!==null){const found=rows.find(r=>key(r)===opened);if(found)showDetail(found,false);else closeDetail();}const conn=by("connection");conn.className="status "+(current?"fresh":"stale");conn.textContent=current?"Güncel rapor · Araştırma modu":"Son yayımlanan veri · Güncellik doğrulanmadı";const labels={daily:"Maç listesi",matching:"Maç eşleştirme",odds:"Oranlar",prospective_validation:"Model doğrulaması",data_quality:"Veri kalitesi",unified_decision:"Karar raporu",snapshot_integrity:"Veri bütünlüğü"};const problems=[];for(const k of Object.keys(labels)){const report=data[k];if(!report){problems.push(labels[k]+": rapor yok");continue;}const ts=Date.parse(report.updatedAt);if(!Number.isFinite(ts)||ts>loadedAt){problems.push(labels[k]+": geçersiz zaman");continue;}if(!fresh(report.updatedAt,loadedAt)){problems.push(labels[k]+": "+Math.floor((loadedAt-ts)/60000)+" dk önce");continue;}if(k!=="snapshot_integrity"&&!bound(data,k,loadedAt))problems.push(labels[k]+": bütünlük doğrulanmadı");}if(data.data_quality?.qualityGate!=="PASS")problems.push("Veri kalite kontrolü geçilmedi");if(data.snapshot_integrity?.status!=="PASS"||!Array.isArray(data.snapshot_integrity?.errors)||data.snapshot_integrity.errors.length)problems.push("Bütünlük raporu onaylı değil");const diagnostic=node("details",undefined,"panel");diagnostic.append(node("summary","Veri durumu ve PAS açıklaması"));diagnostic.append(node("p","Veri güncelliği ile modelin araştırma kararı ayrı kontrollerdir.","subtle"));const published=data.daily?.updatedAt;if(Number.isFinite(Date.parse(published))&&Date.parse(published)<=loadedAt)diagnostic.append(node("p","Son maç listesi yayını: "+dateTR(published)+" "+hourTR(published)+" TSİ · Güncel rapor sınırı 30 dakika.","subtle"));diagnostic.append(node("p","Ana raporlar planlı toplu çalıştırmalarla yayımlanır; ekrandan yenileme yalnızca yayımlanmış raporları okur.","subtle"));for(const problem of problems)diagnostic.append(node("p",problem,"subtle"));if(!problems.length)diagnostic.append(node("p","Güncellik ve bütünlük kontrolleri geçti.","subtle"));const validation=data.prospective_validation;diagnostic.append(node("p","Model sonucu: "+num(validation?.tested)+" / "+num(validation?.minimumMatches)+" · araştırma verisi","subtle"));diagnostic.append(node("p","PAS: Onaylı model ve yeterli kanıt bulunmadan otomatik seçim yayımlanmaz.","subtle"));const previous=by("data-status-details");if(previous)previous.remove();diagnostic.id="data-status-details";conn.after(diagnostic);options("date-filter",[...new Set(rows.map(x=>x.date))],"Tüm tarihler");options("league-filter",[...new Set(rows.map(x=>x.league))].sort((a,b)=>a.localeCompare(b,"tr")),"Tüm ligler");renderList();
 const root=by("performance-summary");root.replaceChildren();const coverage=marketCoverageSummary(data,loadedAt);if(coverage){const body=[node("p","Oran kaydı: "+dateTR(coverage.snapshotAt)+" "+hourTR(coverage.snapshotAt)+" TSİ · "+num(coverage.archivedEvents)+" arşiv maçı. "+(coverage.current?"Güncel kaynak bağı doğrulandı.":"Güncellik veya kaynak bağı doğrulanmadı; mevcut oran kapsamı gösterilmiyor."),"subtle")];for(const point of [1.5,2.5]){const m=coverage.markets[point];body.push(node("h3",point+" gol çizgisi"),metrics([["Arşivde en az 1 kaynak",num(m.observed)],["Arşivde en az 3 kaynak",num(m.threeBooks)],["Güncel ≥3 kaynak",num(m.currentThree)]]));}body.push(node("p","KG Var/Yok: mevcut totals sorgusunun kapsamında değil. Arşivdeki sayılar tahmin doğruluğu veya bahis miktarı değildir.","subtle"));panel(root,"Oran kaynağı · kapsam ve güncellik",body);}else panel(root,"Oran kaynağı · kapsam ve güncellik",[node("p","Geçerli oran arşivi bulunamadı; kapsam gösterilmiyor.","subtle")]);const extraCov=extraMarketCoverage(data,loadedAt);const extraBody=[node("p",({not_published:"Henüz ek oran raporu yayımlanmadı.",invalid:"Ek oran raporu doğrulanamadı.",source_error:"Son denemede kaynak hatası.",quota_guard:"Son denemede kota koruması nedeniyle ek sorgu ertelendi.",no_eligible_events:"Son denemede uygun maç bulunmadı.",observed:"Son ek oran araştırması kaydedildi.",not_checked:"Ek sorgu durumu doğrulanmadı."})[extraCov.status]+(extraCov.updatedAt?" · "+dateTR(extraCov.updatedAt)+" "+hourTR(extraCov.updatedAt)+" TSİ.":""),"subtle")];if(extraCov.markets){extraBody.push(metrics([["Son ücretli sorgu",num(extraCov.attempts)]]));for(const [k,label] of [["over15","1.5 Üst/Alt"],["btts","KG Var/Yok"]]){const m=extraCov.markets[k];extraBody.push(node("h3",label),metrics([["Son raporda ≥1 kaynak",num(m.observed)],["Son raporda ≥3 kaynak",num(m.threeBooks)],["Güncel ≥3 kaynak",num(m.currentThree)]]));}if(!extraCov.current)extraBody.push(node("p","Güncel kaynak bağı yok; sayılar yalnızca son rapora aittir.","subtle"));}extraBody.push(node("p","Araştırma verisi; tahmin onayı veya bahis miktarı değildir.","subtle"));panel(root,"Ek oran araştırması · 1.5 ve KG",extraBody);const mainMl=mlResearchSummary(data.main_ml_prospective_ledger,data.main_ml_frozen_manifest,loadedAt,"main");if(mainMl){const body=[metrics([["Kayıt",num(mainMl.recorded)],["Sonuç",num(mainMl.settled)],["Bekleyen",num(mainMl.pending)]]),metrics([["Karantina",num(mainMl.quarantined)],["Maç günü",num(mainMl.days)],["Hedef","500 / 30 gün"]]),node("p","Ana 9 lig · 119 değişken · 2.848 eğitim maçı · %50 Poisson / %50 CatBoost. Model onaylı değil; maç kartları değişmedi. Son kanıt: "+dateTR(mainMl.lastEvidenceAt)+" "+hourTR(mainMl.lastEvidenceAt)+" TSİ.","subtle")];for(const [k,label] of [["over15","1.5 Üst/Alt"],["over25","2.5 Üst/Alt"],["btts","KG Var/Yok"]]){body.push(node("h3",label),metrics([["Poisson",pct(mainMl.stats[k].poisson.accuracyPct)],["CatBoost",pct(mainMl.stats[k].catboost.accuracyPct)],["Birleşik",pct(mainMl.stats[k].candidate.accuracyPct)]]),metrics([["Poisson Brier",displayNumber(mainMl.stats[k].poisson.brier)],["CatBoost Brier",displayNumber(mainMl.stats[k].catboost.brier)],["Birleşik Brier",displayNumber(mainMl.stats[k].candidate.brier)]]));}if(!mainMl.settled)body.push(node("p","İki kaynakla doğrulanmış maç sonucu bekleniyor; başarı oranı henüz yok.","subtle"));panel(root,"Ana 9 lig · yeni model araştırması",body);}else panel(root,"Ana 9 lig · yeni model araştırması",[node("p","Ana lig model arşivi yayımlanmamış veya tutarlılık kontrolünü geçmedi. Başarı oranı gösterilmiyor.","subtle")]);const pairedMl=matchedMlSummary(data.main_ml_matched_pairs,data.main_ml_prospective_ledger,data.main_ml_frozen_manifest,loadedAt);if(pairedMl){const body=[metrics([["Eşleşen",num(pairedMl.paired)],["Sonuç",num(pairedMl.settled)],["Bekleyen",num(pairedMl.pending)]]),metrics([["Karantina",num(pairedMl.quarantined)],["Maç günü",num(pairedMl.days)],["Zaman farkı ≤24 saat",num(pairedMl.closeTiming)]]),node("p","Aynı maçlar · eski V1.6 ve yeni birleşik V6.67. Tahmin zamanları farklı olabilir; aynı bilgi kesimi doğrulanmadı. Araştırma; model onaylı değil.","subtle")];for(const [k,label] of [["over15","1.5 Üst/Alt"],["over25","2.5 Üst/Alt"],["btts","KG Var/Yok"]]){body.push(node("h3",label),metrics([["Eski doğruluk",pct(pairedMl.stats[k].legacy.accuracyPct)],["Yeni doğruluk",pct(pairedMl.stats[k].candidate.accuracyPct)]]),metrics([["Eski Brier",displayNumber(pairedMl.stats[k].legacy.brier)],["Yeni Brier",displayNumber(pairedMl.stats[k].candidate.brier)]]));}if(!pairedMl.settled)body.push(node("p","Eşleşen maçların doğrulanmış sonuçları bekleniyor.","subtle"));panel(root,"Eski / yeni · ortak maç karşılaştırması",body);}else panel(root,"Eski / yeni · ortak maç karşılaştırması",[node("p","Eşleşme arşivi eksik veya tutarsız; karşılaştırma gösterilmiyor.","subtle")]);const ml=mlResearchSummary(data.extra_ml_prospective_ledger,data.extra_ml_frozen_manifest,loadedAt);if(ml){const body=[metrics([["Kayıt",num(ml.recorded)],["Sonuç",num(ml.settled)],["Bekleyen",num(ml.pending)]]),metrics([["Karantina",num(ml.quarantined)],["Maç günü",num(ml.days)],["Hedef", "500 / 30 gün"]]),node("p","119 değişken · %50 Poisson / %50 CatBoost · son kanıt: "+dateTR(ml.lastEvidenceAt)+" "+hourTR(ml.lastEvidenceAt)+" TSİ. Araştırma; model onaylı değil. Arşiv biçimi ve tutarlılığı denetlendi, canlı veri değil.","subtle")];for(const [k,label] of [["over15","1.5 Üst/Alt"],["over25","2.5 Üst/Alt"],["btts","KG Var/Yok"]]){body.push(node("h3",label),metrics([["Poisson",pct(ml.stats[k].poisson.accuracyPct)],["CatBoost",pct(ml.stats[k].catboost.accuracyPct)],["Birleşik",pct(ml.stats[k].candidate.accuracyPct)]]));}if(!ml.settled)body.push(node("p","İki kaynakla doğrulanmış maç sonucu bekleniyor; başarı oranı henüz yok.","subtle"));panel(root,"Yeni model · ileriye dönük araştırma",body);}else panel(root,"Yeni model · ileriye dönük araştırma",[node("p","Yeni model arşivi henüz yayımlanmamış veya tutarlılık kontrolünü geçmedi. Başarı oranı gösterilmiyor.","subtle")]);const archive=data.fixture_evidence_summary;if(archive?.mode==="research_only"&&archive.productionEnabled===false&&Number.isInteger(archive.uniqueVerifiedCount)&&archive.uniqueVerifiedCount>=0&&Number.isInteger(archive.passingWindowUniqueCount)&&archive.passingWindowUniqueCount>=0&&Number.isInteger(archive.otherWindowUniqueCount)&&archive.otherWindowUniqueCount>=0&&archive.passingWindowUniqueCount+archive.otherWindowUniqueCount===archive.uniqueVerifiedCount&&archive.conflictCount===0){panel(root,"Geçmiş futbol veri arşivi",[metrics([["Benzersiz",num(archive.uniqueVerifiedCount)],["Kalite testi geçen dönem",num(archive.passingWindowUniqueCount)],["Diğer dönem",num(archive.otherWindowUniqueCount)]]),node("p","Arşiv verisi; canlı skor veya tahmin başarısı değildir.","subtle")]);}else panel(root,"Geçmiş futbol veri arşivi",[node("p","Doğrulanmış arşiv özeti yayımlanmamış.","subtle")]);const v=data.prospective_validation;const verified=bound(data,"prospective_validation",loadedAt);panel(root,"İleriye dönük doğrulama",[metrics([["Sonuç",num(v?.tested)],["Bekleyen",num(v?.pending)],["Hedef",num(v?.minimumMatches)]]),node("p",verified?"Araştırma sürüyor; model henüz onaylı değil.":"Rapor eski veya eksik; değerler arşiv niteliğinde.","subtle")]);if(v?.marketResearch)for(const m of MARKETS){const x=v.marketResearch[m];if(x)panel(root,m,[node("p",num(x.tested)+" sonuç · "+num(x.pending)+" bekleyen"),node("p",x.tested&&typeof x.scores?.candidate==="number"?"Brier: "+x.scores.candidate.toFixed(4)+" (düşük daha iyi)":"Henüz karşılaştırılabilir sonuç yok.","subtle")]);}
 const classificationAvailable=scheduleBound(data,"prospective_validation",loadedAt)&&v?.classificationVersion==="6.19"&&Array.isArray(v.errors)&&!v.errors.length;
 const cards=[];
 if(classificationAvailable){
   let total={tested:0,correct:0,incorrect:0},valid=true;
   for(const m of MARKETS){
     const x=classificationFor(v.marketResearch?.[m]);if(!x){valid=false;continue;}
     for(const k of ["tested","correct","incorrect"])total[k]+=x[k];
     const part=node("details",undefined,"panel");part.append(node("summary",m+" · "+(x.tested?pct(x.rate):"Veri bekleniyor")));
     part.append(metrics([["Doğru",num(x.correct)],["Yanlış",num(x.incorrect)],["Test",num(x.tested)]]));
     part.append(node("p",x.tested>=500?"Örneklem eşiği sağlandı; model onayı ayrı.":"Örneklem yetersiz; kesin performans sonucu çıkarılamaz.","subtle"));
     for(const [days,label] of [["1","Son 1 gün"],["7","Son 7 gün"],["30","Son 30 gün"]]){
       const p=accuracyCounts(x.periods?.[days]);
       if(p&&p.tested<=x.tested&&p.correct<=x.correct&&p.incorrect<=x.incorrect)part.append(node("p",label+": "+(p.tested?pct(p.rate)+" · "+p.correct+"/"+p.tested:"Veri bekleniyor"),"subtle"));
     }cards.push(part);
   }
   if(valid){const a=accuracyCounts(total);panel(root,"Tahmin doğruluğu · araştırma",[metrics([["Genel",a.tested?pct(a.rate):"Veri bekleniyor"],["Doğru",num(a.correct)],["Yanlış",num(a.incorrect)],["Test",num(a.tested)]]),node("p","Sabit %50 sınıflandırma eşiği: gerçekleşti / gerçekleşmedi. Toplam, maç değil tahmin türü sayısıdır. Kazanç veya seçim başarısı değildir. "+(verified?"":"Rapor güncel olmayabilir. ")+ "Veri tarihi: "+dateTR(v.updatedAt)+".","subtle"),...cards]);}
   else panel(root,"Tahmin doğruluğu · araştırma",[node("p","Doğruluk raporu eksik veya tutarsız.","subtle")]);
 }else panel(root,"Tahmin doğruluğu · araştırma",[node("p","Doğrulanmış doğruluk raporu bekleniyor.","subtle")]);
 const review=data.nov27_match_review;
 if(review?.version==="6.19"&&review.mode==="research_only"&&review.sourceRun===46058594856&&Array.isArray(review.rows)&&review.rows.length===2&&Number.isFinite(Date.parse(review.observedAt))&&Date.parse(review.observedAt)<=loadedAt){
   const items=[node("p","27 Kasım tarihli kaynak incelemesi. Tek kaynaklı skorlar başarı hesabına dahil değildir. Bu sabit rapor canlı skor değildir.","subtle")];
   for(const m of review.rows){
     if(m.date!=="2026-11-27"||m.league!=="tr.1"||!["alanyaspor – konyaspor","rizespor – kasimpasa"].includes(m.home+" – "+m.away)||m.resultStatus!=="incomplete"||m.result!==null||!Array.isArray(m.espnScore)||m.espnScore.length!==2||!m.espnScore.every(x=>Number.isInteger(x)&&x>=0))continue;
     const detail=node("div",undefined,"panel");detail.append(node("h3",m.home+" – "+m.away),node("p","ESPN: "+m.espnScore.join("–")+" · İkinci kaynak bekleniyor"),node("p",m.archiveStatus==="pre_date_archive_pending"?"Önceden kayıtlı tahmin var.":"Tahmin zamanı kesinleşmedi; başarı hesabı dışında.","subtle"));
     for(const market of MARKETS){const p=m.markets?.[market];if(Number.isFinite(p)&&p>=0&&p<=100)detail.append(node("p",market+" · "+pct(p),"subtle"));}
     items.push(detail);
   }
   if(items.length===3)panel(root,"27 Kasım maç incelemesi",items);
 }
 const pending=v?.pendingDateStatus;if(v?.pendingDateStatusAsOf===dateTR(loadedAt)&&pending&&["future","today","past","invalidDate"].every(k=>Number.isInteger(pending[k])&&pending[k]>=0)&&pending.future+pending.today+pending.past+pending.invalidDate===v.pending){panel(root,"Bekleyen sonuçların tarih dağılımı",[metrics([["İleri tarih",num(pending.future)],["Bugün",num(pending.today)],["Geçmiş tarih",num(pending.past)]]),node("p","Tarih bazlı arşiv durumu; geçmiş tarih, maçın tamamlandığını tek başına kanıtlamaz. "+(verified?"":"Rapor eski olabilir. ")+(pending.invalidDate?"Geçersiz tarih: "+num(pending.invalidDate):""),"subtle")]);}
 const leagueRows=leagueReport(data,loadedAt);
 const diag=data.prospective_leagues;
 if(scheduleBound(data,"prospective_leagues",loadedAt)&&scheduleBound(data,"prospective_validation",loadedAt)&&diag?.calibrationVersion==="5.03"&&diag.mode==="research_only"&&diag.realBettingEnabled===false&&diag.decision==="PAS"&&diag.updatedAt===v?.updatedAt&&diag.recorded===v?.recorded){
   const block=node("details",undefined,"panel");block.append(node("summary","Olasılık kalibrasyonu · araştırma"));
   block.append(node("p","Gerçekleşen oran ile ortalama model tahmini. Bu karşılaştırma model onayı değildir.","subtle"));
   for(const m of MARKETS){
     const x=diag.overallCalibration?.[m];if(!x||x.descriptiveOnly!==true||!Number.isInteger(x.sample)||x.sample!==v?.marketResearch?.[m]?.tested)continue;
     const items=[node("p",m+" · "+x.sample+" sonuç")];
     if(x.sample>0&&Number.isFinite(x.observedRate)&&Number.isFinite(x.meanPrediction?.candidate)&&Number.isFinite(x.gapPP?.candidate))items.push(metrics([["Gerçekleşen",pct(100*x.observedRate)],["Ortalama tahmin",pct(100*x.meanPrediction.candidate)],["Fark",x.gapPP.candidate.toFixed(1)+" yp"]]));
     items.push(node("p",x.sampleAdequate?"Örneklem eşiği sağlandı; ek doğrulama gerekli.":"Örneklem yetersiz; güvenilir kalibrasyon sonucu çıkarılamaz.","subtle"));
     block.append(...items);
   }root.append(block);
 }
 const leagueDetails=node("details",undefined,"panel");leagueDetails.append(node("summary","Lig bazında model karşılaştırması"));
 if(leagueRows){
   const names={"en.1":"İngiltere Premier Lig","en.2":"İngiltere Championship","de.1":"Almanya Bundesliga","es.1":"İspanya La Liga","it.1":"İtalya Serie A","fr.1":"Fransa Ligue 1","nl.1":"Hollanda Eredivisie","pt.1":"Portekiz Primeira Liga","tr.1":"Türkiye Süper Lig"};
   for(const [code,entry] of Object.entries(leagueRows)){
     const card=node("details",undefined,"panel");card.append(node("summary",(names[code]||code)+" · "+num(entry.recorded)+" kayıt"));
     for(const m of MARKETS){const x=entry.markets?.[m];if(!x)continue;card.append(node("p",m+" · "+num(x.tested)+" sonuç · "+num(x.pending)+" bekleyen","subtle"));const accuracy=classificationAvailable?classificationFor(x):null;if(accuracy)card.append(node("p","Doğruluk: "+(accuracy.tested?pct(accuracy.rate)+" · "+accuracy.correct+"/"+accuracy.tested:"Veri bekleniyor"),"subtle"));if(x.tested>0&&["old","candidate","baseline"].every(k=>Number.isFinite(x.scores?.[k])))card.append(node("p","Brier: klasik "+x.scores.old.toFixed(4)+" / ağırlıklı "+x.scores.candidate.toFixed(4)+" / lig "+x.scores.baseline.toFixed(4),"subtle"));}
     leagueDetails.append(card);
   }
 }else leagueDetails.append(node("p","Güncel, doğrulanmış lig raporu bekleniyor.","subtle"));
 root.append(leagueDetails);
 const radar=by("scoreboard-summary");radar.replaceChildren();
 const live=data.live_analysis_quality, recent=liveRows(live,loadedAt);
 panel(radar,"ESPN · periyodik maç istatistikleri",[node("p",Number.isFinite(Date.parse(live?.updatedAt))?"Son sorgu: "+dateTR(live.updatedAt)+" "+hourTR(live.updatedAt)+" TSİ":"Henüz yayımlanmış sorgu yok.","subtle"),node("p","15 dakikalık pilot; veri alım süresi 120 saniye ile sınırlıdır. Kaynağın gerçek zamanlı güncelliği doğrulanmadı.","subtle")]);
 if(!recent.length)radar.append(signalPanel(null),node("p","Gösterilebilir yeni maç gözlemi yok. Bu, devam eden maç olmadığı anlamına gelmez.","subtle"));
 for(const r of recent){const o=r.observation;panel(radar,r.home+" – "+r.away,[node("p",o.score.join(" – ")+" · "+o.clock),metrics([["Korner",o.metrics.corners.join(" – ")],["Şut",o.metrics.shots.join(" – ")],["İsabetli şut",o.metrics.shotsOnTarget.join(" – ")],["Sarı kart",o.metrics.yellowCards.join(" – ")],["Kırmızı kart",o.metrics.redCards.join(" – ")],["Topa sahip olma",o.metrics.possession.join(" – ")+" %"]]),node("p","Alım: "+hourTR(r.receivedAt)+" TSİ · Gözlem, tahmin değil.","subtle"),signalPanel(r)]);}
 const board=data.scoreboard_snapshot;
 if(board?.version==="4.90"&&board.mode==="scoreboard_snapshot"&&board.realTime===false&&Array.isArray(board.groups)){
   const isCurrent=bound(data,"scoreboard_snapshot",loadedAt)&&board.date===dateTR(loadedAt);
   panel(radar,isCurrent?"Son skor görüntüsü":"Eski skor görüntüsü — canlı değil",[node("p",board.date+" · "+(Number.isFinite(Date.parse(board.updatedAt))?hourTR(board.updatedAt):"—")+" TSİ · ESPN"),node("p",num(board.loadedLeagues)+" / 9 lig yanıt verdi. "+num(board.eventCount)+" maç kaydı.","subtle")]);
   if(isCurrent){for(const group of board.groups){if(group.error||!Array.isArray(group.rows))continue;for(const r of group.rows){if(r.state!=="in"&&r.state!=="post")continue;const score=Array.isArray(r.score)&&r.score.length===2?r.score.join(" – "):"Skor yok";panel(radar,r.home+" – "+r.away,[node("p",score),node("p",group.leagueName+" · "+(r.state==="in"?"Görüntü alındığında sürüyordu":"Kaynakta sona ermiş / durmuş")+(r.clock?" · "+r.clock:""),"subtle")]);}}if(board.inProgress===0)radar.append(node("p","Son görüntüde devam eden maç yok. Bu, şu anda maç olmadığı anlamına gelmez.","subtle"));}
 }else radar.append(node("p","Skor görüntüsü henüz yayımlanmadı.","subtle"));
 const c=by("coupon-summary");c.replaceChildren();panel(c,"PAS",[node("p","Onaylanmış otomatik kupon yok."),node("p","Model kalibrasyonu tamamlanmadı.","subtle")]);
 const history=shadowHistory(data.shadow_performance,loadedAt);
 if(history){
   const x=history.total,body=[node("p","Yayımlanmış geçmiş sanal test kayıtları; gerçek para veya yeni maç seçimi yok. Veri tarihi: "+dateTR(history.updatedAt)+".","subtle"),metrics([["Kayıt",num(x.recorded)],["Sonuçlanan",num(x.settled)],["Bekleyen",num(x.pending)]]),metrics([["Doğru",num(x.won)],["Yanlış",num(x.lost)],["Geçmiş doğruluk",x.settled?pct(x.rate):"Veri yok"]])];
   for(let i=0;i<history.sizes.length;i++){const y=history.sizes[i];body.push(node("p",(i+1)+" maçlı test: "+(y.settled?pct(y.rate)+" · "+y.won+"/"+y.settled:"Veri yok")+" · "+num(y.pending)+" bekleyen","subtle"));}
   body.push(node("p",x.settled?"Geçmiş sanal sonuçlar gelecekteki başarıyı garanti etmez; model onayı değildir.":"Henüz sonuçlanmış sanal test kaydı bulunmuyor.","subtle"));
   panel(c,"Sanal test geçmişi",body);
 }else panel(c,"Sanal test geçmişi",[node("p","Doğrulanabilir biçimde yayımlanmış sanal test özeti yok.","subtle")]);
 const s=by("settings-summary");s.replaceChildren(node("p","Son bildirilen API kredisi: "+num(data.odds?.remainingCredits)),node("p","Bütünlük: "+(current?"PASS":"Güncel doğrulama yok")),node("p","Ücretsiz araştırma • Türkiye dışı oran kaynakları","subtle"));
}
async function refresh(){if(refreshing)return;refreshing=true;by("refresh").disabled=true;by("connection").textContent="Raporlar okunuyor…";const next={};await Promise.all(FILES.map(async k=>{try{const r=await fetch("./"+k+".json?ts="+Date.now(),{cache:"no-store"});if(r.ok)next[k]=await r.json();}catch(_){}}));try{const r=await fetch(LIVE_URL+"?ts="+Date.now(),{cache:"no-store"});if(r.ok)next.live_analysis_quality=await r.json();}catch(_){}data=next;try{render();}catch(_){by("connection").textContent="Rapor biçimi doğrulanamadı · PAS";}finally{refreshing=false;by("refresh").disabled=false;}}
let sport="football";
function setSport(value){
 sport=value==="basketball"?"basketball":"football";
 const basketball=sport==="basketball";
 for(const b of document.querySelectorAll("[data-sport]"))b.setAttribute("aria-pressed",String(b.dataset.sport===sport));
 for(const id of ["date-shortcut","match-list","scoreboard-summary"])by(id).hidden=basketball;
 for(const el of document.querySelectorAll("#view-matches .match-tools,#view-matches .filter-panel"))el.hidden=basketball;
 by("basketball-matches").hidden=!basketball;by("basketball-live").hidden=!basketball;
}
for(const b of document.querySelectorAll("[data-sport]"))b.onclick=()=>setSport(b.dataset.sport);
by("detail-back").onclick=closeDetail;
by("date-shortcut").onclick=()=>{by("date-rail").scrollIntoView({block:"nearest"});by("date-rail").querySelector("button")?.focus();};
by("fixture-mode").onchange=()=>{by("date-filter").value="";by("league-filter").value="";render();};
for(const id of ["search","date-filter","league-filter","time-filter"])by(id).addEventListener(id==="search"?"input":"change",renderList);
const buttons=[...document.querySelectorAll("[data-tab]")];for(const b of buttons)b.onclick=()=>{for(const t of buttons){const active=t===b;by("view-"+t.dataset.tab).hidden=!active;if(active)t.setAttribute("aria-current","page");else t.removeAttribute("aria-current");}window.scrollTo(0,0);};
function theme(value){const resolved=value==="system"?(matchMedia("(prefers-color-scheme:light)").matches?"light":"dark"):value;document.documentElement.dataset.theme=resolved;try{localStorage.setItem("oa_theme",value);}catch(_){}}
let pref="dark";try{pref=localStorage.getItem("oa_theme")||"dark";}catch(_){}if(!["dark","light","system"].includes(pref))pref="dark";by("theme").value=pref;theme(pref);by("theme").onchange=e=>theme(e.target.value);
setInterval(expireView,15000);setInterval(()=>{if(!document.hidden)refresh();},120000);document.addEventListener("visibilitychange",()=>{if(!document.hidden){expireView();refresh();}});
by("refresh").onclick=refresh;if("serviceWorker"in navigator){
 let reloaded=false,hadController=Boolean(navigator.serviceWorker.controller);
 navigator.serviceWorker.addEventListener("controllerchange",()=>{if(hadController&&!reloaded){reloaded=true;location.reload();}});
 navigator.serviceWorker.register("./sw.js",{updateViaCache:"none"}).then(reg=>reg.update()).catch(()=>{});
}refresh();
})();