(function(){
"use strict";
const FILES=["daily","matching","odds","performance","prospective_validation","data_quality","unified_decision","snapshot_integrity","prospective_leagues","scoreboard_snapshot","fixture_coverage_audit","kickoff_confirmation","model_research","football_statistics_pilot"];
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
if(typeof module!=="undefined"&&module.exports)module.exports={liveRows,topScores,eventFor,rowsFor,filterRows,bound,leagueReport,fixtureCheck,confirmedRows,lastKnownSchedule,timeLabel,researchFor,historicalStatsFor};
if(typeof document==="undefined")return;
const by=id=>document.getElementById(id),node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let data={},rows=[],loadedAt=0,refreshing=false,opened=null,listScroll=0;
function expirySignature(data,now){return liveRows(data.live_analysis_quality,now).length+':'+FILES.map(k=>fresh(data[k]?.updatedAt,now)?1:0).join('')+dateTR(now)+':'+confirmedRows(data,now).length+":"+confirmedRows(data,now,true).length+':'+FILES.map(k=>scheduleBound(data,k,now)?1:0).join('')+':'+rowsFor(data,now).filter(r=>r.lastKnown).length;}
function expireView(){if(!refreshing&&loadedAt&&expirySignature(data,loadedAt)!==expirySignature(data,Date.now()))render();}
function metrics(values){const box=node("div",undefined,"metrics");for(const [label,value] of values){const c=node("div",undefined,"metric");c.append(node("b",value),node("small",label));box.append(c);}return box;}
function teamTitle(match){const parts=match.split(" – "),title=node("span",undefined,"match-title");if(parts.length!==2){title.textContent=match;return title;}for(const [i,name] of parts.entries()){if(i)title.append(node("span","VS","versus"));const team=node("span",undefined,"team-name"),crest=node("span",name.split(/\s+/).slice(0,2).map(w=>w[0]).join("").toUpperCase(),"team-crest"+(i?" away":""));crest.setAttribute("aria-hidden","true");team.append(crest,node("span",name));title.append(team);}return title;}
function probabilityBars(markets){const root=node("div");for(const m of MARKETS){const value=markets?.[m],row=node("div",undefined,"prob-row"),track=node("div",undefined,"prob-track"),fill=node("div",undefined,"prob-fill");fill.style.width=(typeof value==="number"&&Number.isFinite(value)&&value>=0&&value<=100?value:0)+"%";track.append(fill);row.append(node("span",m),track,node("b",pct(value)));root.append(row);}return root;}
function oddsRange(event,point,now){const v=arr(event?.bookmakers).flatMap(b=>arr(b.lines).filter(l=>l.point===point&&fresh(l.lastUpdate,now)&&typeof l.over==="number"&&Number.isFinite(l.over)&&l.over>1).map(l=>l.over));return v.length?Math.min(...v).toFixed(2)+(Math.max(...v)!==Math.min(...v)?"–"+Math.max(...v).toFixed(2):""):"—";}
function personalPanel(r){const box=node("article",undefined,"panel personal-detail");box.append(node("h3","Kişisel para kaydı"));for(const [label,value] of [["Yatırılan tutar","— TL"],["2.5 Üst oran aralığı",oddsRange(r.event,2.5,Date.now())],["Gerçek geri dönüş","— TL"],["Net sonuç","— TL"]]){const line=node("div",undefined,"personal-line");line.append(node("span",label),node("strong",value));box.append(line);}box.append(node("p","Bu maçla eşleştirilmiş kişisel kayıt yok. Önerilen bahis tutarı üretilmiyor.","subtle"));const b=node("button","Kişisel kayıt defterini aç","action");b.type="button";b.onclick=()=>{closeDetail();by("tab-coupons").click();};box.append(b);return box;}
function volumePanel(){const box=node("div",undefined,"panel volume-panel");
 box.append(node("h3","Uluslararası bahis hacmi"),metrics([["Dünya toplamı (TL)","—"],["Ölçülen hacim (TL)","—"],["Kaynak","Bağlı değil"]]),node("p","Dünya toplamı kamuya açık değil. Ölçülen hacim yalnızca izinli veri sağlayıcısının kapsadığı piyasalarda gösterilebilir. Oran değişimi, bahis miktarı değildir.","subtle"));return box;}
function showDetail(r,remember=true){
 if(remember)listScroll=window.scrollY;
 opened=key(r);
 by("view-matches").hidden=true;
 by("match-detail-screen").hidden=false;
 document.body.classList.add("detail-active");
 const hero=by("detail-hero");hero.replaceChildren(node("p","⚽ "+r.league,"detail-league"),teamTitle(r.match),node("p",r.date+" · "+timeLabel(r),"detail-time"));
 by("detail-content").replaceChildren(detail(r));
 if(remember){window.scrollTo(0,0);by("detail-back").focus({preventScroll:true});}
}
function closeDetail(){
 if(opened===null)return;
 opened=null;by("match-detail-screen").hidden=true;document.body.classList.remove("detail-active");by("view-matches").hidden=false;window.scrollTo(0,listScroll);
}
function detail(r){if(r.confirmed){
 const box=node("div",undefined,"detail");
 box.append(node("p","ESPN ve uluslararası oran kaynağında aynı başlama saati.","subtle"));
 if(r.originalDate&&r.originalDate!==r.date)box.append(node("p","Eski fikstür tarihi: "+r.originalDate+". Arşivdeki tahmin değiştirilmedi.","subtle"));
 box.append(node("p","Bu görünüm yalnızca fikstür doğrulamasıdır. Model tahmini veya bahis seçimi aktarılmaz.","subtle"),volumePanel());return box;
 }r={...r,event:eventFor(r,data,Date.now())};const x=node("div",undefined,"detail"),tabs=node("div",undefined,"detail-tabs"),out=node("div"),c=r.candidate;
const views={
"Analiz":()=>{const probabilities=node("article",undefined,"panel analysis-panel");probabilities.append(node("h3","◉ Model olasılıkları"));
 if(c)probabilities.append(probabilityBars(c.markets),node("p","Kalibre edilmemiş model; kazanma garantisi değildir.","subtle"));
 else probabilities.append(node("p","Model tahmini yok.","subtle"));
 const scores=topScores(c?.expectedGoals?.home,c?.expectedGoals?.away),score=node("article",undefined,"panel score-panel");score.append(node("h3","▥ En olası skorlar"),node("strong",scores.length?scores.map(s=>s.score).join(", "):"—","score-line"),node("p","Poisson model senaryoları","subtle"));
 out.append(probabilities,score,personalPanel(r),volumePanel());},
"Skor":()=>{const s=topScores(c?.expectedGoals?.home,c?.expectedGoals?.away);out.append(node("p",s.length?"Bağımsız Poisson modelinin en olası 3 skor senaryosu.":"Skor modeli verisi yok.","subtle"));for(const y of s)out.append(node("p",y.score+" · "+pct(y.p)));},
"Oranlar":()=>{if(!r.event){out.append(node("p","Kesin eşleşen güncel oran kaydı yok.","subtle"));return;}for(const p of [1.5,2.5]){const v=arr(r.event.bookmakers).flatMap(b=>arr(b.lines).filter(l=>l.point===p&&fresh(l.lastUpdate,Date.now())&&typeof l.over==="number"&&l.over>1).map(l=>l.over));out.append(node("p",p+" Üst: "+(v.length?v.length+" kaynak · "+Math.min(...v).toFixed(2)+"–"+Math.max(...v).toFixed(2):"Veri yok")));}out.append(node("p","Oran hareketleri: ayrıntılı raporlarda. Gerçek para akışı verisi yok.","subtle"));},
"Para akışı":()=>out.append(volumePanel()),
"İstatistik":()=>{renderHistoricalStats(out,r);const model=researchFor(r,data,Date.now());out.append(node("h3","Gol modeli karşılaştırması"));if(!model){out.append(node("p","Bütünlüğü kontrol edilmiş model raporu yok.","subtle"));return;}out.append(node("p","Aynı gol beklentisinden üretilen deneysel dağılımlar. Bağımsız tahminler veya doğrulanmış kazanma olasılıkları değildir.","subtle"));for(const [name,k] of [["1.5 Üst","over15"],["2.5 Üst","over25"],["KG Var","btts"]]){out.append(node("h3",name),metrics([["Poisson",pct(100*model.poisson?.[k])],["Dixon-Coles",pct(100*model.experimentalDixonColes?.[k])],["Monte Carlo",pct(100*model.simulation?.markets?.[k]?.probability)]]));}out.append(node("p","Dixon-Coles katsayısı sabit deneysel değerdir; Monte Carlo aynı dağılımın 20.000 örnekli sayısal kontrolüdür. Kadro ve sakatlık verileri henüz bağlı değil.","subtle"));},
"H2H":()=>{const f=scheduleBound(data,"daily",Date.now())&&r.formResearch?.version==="5.06"?r.formResearch:null;out.append(node("h3","Son karşılaşmalar"));if(!f||!arr(f.h2h).length)out.append(node("p","Doğrulanmış tarihli geçmiş kayıt yok.","subtle"));else for(const y of f.h2h)out.append(node("p",y.date+" · "+y.home+" "+y.score.join("–")+" "+y.away));out.append(node("p","Yalnızca mevcut lig geçmişi; tüm organizasyonları kapsamaz.","subtle"));},
"Form":()=>{const f=scheduleBound(data,"daily",Date.now())&&r.formResearch?.version==="5.06"?r.formResearch:null;out.append(node("h3","Son 5 lig maçı"));if(!f){out.append(node("p","Güncel form raporu yok.","subtle"));return;}for(const [label,side] of [["Ev sahibi",f.home],["Deplasman",f.away]]){out.append(node("h3",label+" · "+side.sample+" maç"),metrics([["Galibiyet",num(side.wins)],["Beraberlik",num(side.draws)],["Mağlubiyet",num(side.losses)]]));for(const y of arr(side.rows))out.append(node("p",y.date+" · "+y.opponent+" · "+y.gf+"–"+y.ga+" · "+(y.venue==="home"?"İç saha":"Dış saha"),"subtle"));}out.append(node("p","Lig geçmişi; kadro ve sakatlık verileri bağlı değil.","subtle"));},
"Diğer":()=>out.append(node("p","İY/MS, iki yarı KG Var ve kartlar için doğrulanmış veri/model henüz bağlı değil.","subtle"))};
for(const name of Object.keys(views)){const b=node("button",name);b.type="button";b.setAttribute("aria-pressed","false");b.onclick=()=>{for(const t of tabs.children)t.setAttribute("aria-pressed",String(t===b));out.replaceChildren();views[name]();};tabs.append(b);}const check=fixtureCheck(r,data,Date.now());if(check?.status==="date_difference")x.append(node("p","Tarih uyuşmazlığı: mevcut liste "+r.date+" / ESPN "+check.sourceDate+". Orijinal kayıt değiştirilmedi.","subtle"));else if(check?.status==="same_date")x.append(node("p","Fikstür tarihi ESPN ile eşleşiyor.","subtle"));else if(check)x.append(node("p","İkinci kaynakta kesin fikstür eşleşmesi yok.","subtle"));x.append(tabs,out);tabs.firstChild.click();return x;}
function quickMarkets(r){const el=node("span",undefined,"quick-markets");if(r.candidate&&!r.confirmed){for(const m of MARKETS){const p=pct(r.candidate.markets?.[m]);const tile=node("span");tile.append(node("small",m),node("strong",p));el.append(tile);}}else el.append(node("span","Model yüzdesi yok"));return el;}
function volumeStrip(){const row=node("span",undefined,"volume-strip");row.append(node("span","Uluslararası bahis hacmi"),node("strong","— TL"));return row;}
function renderList(){const result=filterRows(rows,by("search").value,by("date-filter").value,by("league-filter").value,by("time-filter").value),box=by("match-list");by("match-count").textContent=result.length+" maç";box.replaceChildren();for(const r of result){const card=node("article",undefined,"match-card"),s=node("button",undefined,"match-open");s.type="button";s.append(node("span","⚽ "+r.league+(r.confirmed?(r.event?" · İki kaynak":" · Son eşleşme"):r.fixtureCheck?.status==="date_difference"?" · Tarih farkı":""),"match-meta"),teamTitle(r.match),node("span",r.date+" · "+timeLabel(r),"match-time"),node("span",r.confirmed?"Fikstür doğrulaması":r.candidate?"Model analizi • Kalibre edilmedi":"Tahmin verisi yok","match-summary-label"),quickMarkets(r),node("span","2.5 Üst oran aralığı: "+oddsRange(r.event,2.5,Date.now()),"odds-summary"),volumeStrip());card.append(s);s.onclick=()=>showDetail(r);box.append(card);}if(!result.length)box.append(node("p",rows.length?"Filtreye uygun maç bulunamadı.":by("fixture-mode").value==="confirmed"?"Güncel çift kaynaklı saat kaydı yok. Genel listeyi seçebilirsin.":by("fixture-mode").value==="last-confirmed"?"Son 24 saatte eşleşen ileri tarihli fikstür yok.":"Yayımlanan maç listesi okunamadı.","subtle"));}
function options(id,values,label){const e=by(id),old=e.value;e.replaceChildren(node("option",label));e.firstChild.value="";for(const v of values){const o=node("option",v);o.value=v;e.append(o);}if(values.includes(old))e.value=old;}
function panel(root,title,body){const p=node("article",undefined,"panel");p.append(node("h3",title));for(const el of body)p.append(el);root.append(p);}
function render(){loadedAt=Date.now();rows=by("fixture-mode").value==="confirmed"?confirmedRows(data,loadedAt):by("fixture-mode").value==="last-confirmed"?confirmedRows(data,loadedAt,true):rowsFor(data,loadedAt);const current=["daily","matching","odds","prospective_validation","data_quality","unified_decision"].every(k=>bound(data,k,loadedAt))&&data.data_quality?.qualityGate==="PASS";if(opened!==null){const found=rows.find(r=>key(r)===opened);if(found)showDetail(found,false);else closeDetail();}const conn=by("connection");conn.className="status "+(current?"fresh":"stale");conn.textContent=current?"Güncel rapor · "+num(data.daily?.leaguesLoaded)+" lig · Araştırma modu":"Eksik veya eski rapor · PAS";options("date-filter",[...new Set(rows.map(x=>x.date))],"Tüm tarihler");options("league-filter",[...new Set(rows.map(x=>x.league))].sort((a,b)=>a.localeCompare(b,"tr")),"Tüm ligler");renderList();
 const root=by("performance-summary");root.replaceChildren();const v=data.prospective_validation;const verified=bound(data,"prospective_validation",loadedAt);panel(root,"İleriye dönük doğrulama",[metrics([["Sonuç",num(v?.tested)],["Bekleyen",num(v?.pending)],["Hedef",num(v?.minimumMatches)]]),node("p",verified?"Araştırma sürüyor; model henüz onaylı değil.":"Rapor eski veya eksik; değerler arşiv niteliğinde.","subtle")]);if(v?.marketResearch)for(const m of MARKETS){const x=v.marketResearch[m];if(x)panel(root,m,[node("p",num(x.tested)+" sonuç · "+num(x.pending)+" bekleyen"),node("p",x.tested&&typeof x.scores?.candidate==="number"?"Brier: "+x.scores.candidate.toFixed(4)+" (düşük daha iyi)":"Henüz karşılaştırılabilir sonuç yok.","subtle")]);}
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
     for(const m of MARKETS){const x=entry.markets?.[m];if(!x)continue;card.append(node("p",m+" · "+num(x.tested)+" sonuç · "+num(x.pending)+" bekleyen","subtle"));if(x.tested>0&&["old","candidate","baseline"].every(k=>Number.isFinite(x.scores?.[k])))card.append(node("p","Brier: klasik "+x.scores.old.toFixed(4)+" / ağırlıklı "+x.scores.candidate.toFixed(4)+" / lig "+x.scores.baseline.toFixed(4),"subtle"));}
     leagueDetails.append(card);
   }
 }else leagueDetails.append(node("p","Güncel, doğrulanmış lig raporu bekleniyor.","subtle"));
 root.append(leagueDetails);
 const radar=by("scoreboard-summary");radar.replaceChildren();
 const live=data.live_analysis_quality, recent=liveRows(live,loadedAt);
 panel(radar,"ESPN · periyodik maç istatistikleri",[node("p",Number.isFinite(Date.parse(live?.updatedAt))?"Son sorgu: "+dateTR(live.updatedAt)+" "+hourTR(live.updatedAt)+" TSİ":"Henüz yayımlanmış sorgu yok.","subtle"),node("p","15 dakikalık pilot; veri alım süresi 120 saniye ile sınırlıdır. Kaynağın gerçek zamanlı güncelliği doğrulanmadı.","subtle")]);
 if(!recent.length)radar.append(node("p","Gösterilebilir yeni maç gözlemi yok. Bu, devam eden maç olmadığı anlamına gelmez.","subtle"));
 for(const r of recent){const o=r.observation;panel(radar,r.home+" – "+r.away,[node("p",o.score.join(" – ")+" · "+o.clock),metrics([["Korner",o.metrics.corners.join(" – ")],["Şut",o.metrics.shots.join(" – ")],["İsabetli şut",o.metrics.shotsOnTarget.join(" – ")],["Sarı kart",o.metrics.yellowCards.join(" – ")],["Kırmızı kart",o.metrics.redCards.join(" – ")],["Topa sahip olma",o.metrics.possession.join(" – ")+" %"]]),node("p","Alım: "+hourTR(r.receivedAt)+" TSİ · Gözlem, tahmin değil.","subtle")]);}
 const board=data.scoreboard_snapshot;
 if(board?.version==="4.90"&&board.mode==="scoreboard_snapshot"&&board.realTime===false&&Array.isArray(board.groups)){
   const isCurrent=bound(data,"scoreboard_snapshot",loadedAt)&&board.date===dateTR(loadedAt);
   panel(radar,isCurrent?"Son skor görüntüsü":"Eski skor görüntüsü — canlı değil",[node("p",board.date+" · "+(Number.isFinite(Date.parse(board.updatedAt))?hourTR(board.updatedAt):"—")+" TSİ · ESPN"),node("p",num(board.loadedLeagues)+" / 9 lig yanıt verdi. "+num(board.eventCount)+" maç kaydı.","subtle")]);
   if(isCurrent){for(const group of board.groups){if(group.error||!Array.isArray(group.rows))continue;for(const r of group.rows){if(r.state!=="in"&&r.state!=="post")continue;const score=Array.isArray(r.score)&&r.score.length===2?r.score.join(" – "):"Skor yok";panel(radar,r.home+" – "+r.away,[node("p",score),node("p",group.leagueName+" · "+(r.state==="in"?"Görüntü alındığında sürüyordu":"Kaynakta sona ermiş / durmuş")+(r.clock?" · "+r.clock:""),"subtle")]);}}if(board.inProgress===0)radar.append(node("p","Son görüntüde devam eden maç yok. Bu, şu anda maç olmadığı anlamına gelmez.","subtle"));}
 }else radar.append(node("p","Skor görüntüsü henüz yayımlanmadı.","subtle"));
 const c=by("coupon-summary");c.replaceChildren();panel(c,"PAS",[node("p","Onaylanmış otomatik kupon yok."),node("p","Kazanma olasılığı: doğrulanmadı. Model kalibrasyonu tamamlanmadı.","subtle")]);
 const s=by("settings-summary");s.replaceChildren(node("p","Son bildirilen API kredisi: "+num(data.odds?.remainingCredits)),node("p","Bütünlük: "+(current?"PASS":"Güncel doğrulama yok")),node("p","Ücretsiz araştırma • Türkiye dışı oran kaynakları","subtle"));
}
async function refresh(){if(refreshing)return;refreshing=true;by("refresh").disabled=true;by("connection").textContent="Raporlar okunuyor…";const next={};await Promise.all(FILES.map(async k=>{try{const r=await fetch("./"+k+".json?ts="+Date.now(),{cache:"no-store"});if(r.ok)next[k]=await r.json();}catch(_){}}));try{const r=await fetch(LIVE_URL+"?ts="+Date.now(),{cache:"no-store"});if(r.ok)next.live_analysis_quality=await r.json();}catch(_){}data=next;try{render();}catch(_){by("connection").textContent="Rapor biçimi doğrulanamadı · PAS";}finally{refreshing=false;by("refresh").disabled=false;}}
by("detail-back").onclick=closeDetail;
by("date-shortcut").onclick=()=>{document.querySelector(".filter-panel").open=true;by("date-filter").focus();};
by("fixture-mode").onchange=()=>{by("date-filter").value="";by("league-filter").value="";render();};
for(const id of ["search","date-filter","league-filter","time-filter"])by(id).addEventListener(id==="search"?"input":"change",renderList);
const buttons=[...document.querySelectorAll("[data-tab]")];for(const b of buttons)b.onclick=()=>{for(const t of buttons){const active=t===b;by("view-"+t.dataset.tab).hidden=!active;if(active)t.setAttribute("aria-current","page");else t.removeAttribute("aria-current");}window.scrollTo(0,0);};
function theme(value){const resolved=value==="system"?(matchMedia("(prefers-color-scheme:light)").matches?"light":"dark"):value;document.documentElement.dataset.theme=resolved;try{localStorage.setItem("oa_theme",value);}catch(_){}}
let pref="dark";try{pref=localStorage.getItem("oa_theme")||"dark";}catch(_){}if(!["dark","light","system"].includes(pref))pref="dark";by("theme").value=pref;theme(pref);by("theme").onchange=e=>theme(e.target.value);
setInterval(expireView,15000);setInterval(()=>{if(!document.hidden)refresh();},120000);document.addEventListener("visibilitychange",()=>{if(!document.hidden){expireView();refresh();}});
by("refresh").onclick=refresh;if("serviceWorker"in navigator)navigator.serviceWorker.register("./sw.js").catch(()=>{});refresh();
})();