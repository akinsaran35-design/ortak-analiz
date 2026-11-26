(function(){
"use strict";
const FILES=["daily","matching","odds","performance","prospective_validation","data_quality","unified_decision","snapshot_integrity","prospective_leagues","scoreboard_snapshot","fixture_coverage_audit","kickoff_confirmation"];
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
function eventFor(row,data,now){if(!["daily","matching","odds"].every(k=>bound(data,k,now)))return null;const m=arr(data.matching.matched).filter(x=>x.match===row.match&&Number.isFinite(Date.parse(x.kickoff))&&dateTR(x.kickoff)===row.date);if(m.length!==1)return null;const e=arr(data.odds.events).filter(x=>x.id===m[0].eventId&&x.kickoff===m[0].kickoff&&x.league===LEAGUES[row.league]);return e.length===1?e[0]:null;}
function rowsFor(data,now){const candidates=new Map(arr(data.daily?.candidates).map(c=>[key(c),c])),unique=new Map();for(const r of arr(data.daily?.upcoming)){if(r&&typeof r.match==="string"&&typeof r.league==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&!unique.has(key(r)))unique.set(key(r),{...r,candidate:candidates.get(key(r))||null,event:eventFor(r,data,now),fixtureCheck:fixtureCheck(r,data,now)});}return [...unique.values()].sort((a,b)=>a.date.localeCompare(b.date)||String(a.event?.kickoff||"z").localeCompare(String(b.event?.kickoff||"z"))||a.league.localeCompare(b.league,"tr"));}
function confirmedRows(data,now){
 const k=data.kickoff_confirmation;
 if(!["daily","odds","fixture_coverage_audit","kickoff_confirmation"].every(x=>bound(data,x,now))||k.version!=="4.94"||k.available!==true||k.mode!=="research_only"||k.archivesModified!==false||k.decision!=="PAS"||k.dailyUpdatedAt!==data.daily.updatedAt||k.oddsUpdatedAt!==data.odds.updatedAt||k.coverageUpdatedAt!==data.fixture_coverage_audit.updatedAt)return [];
 const names={"en.1":"İngiltere Premier Lig","en.2":"İngiltere Championship","de.1":"Almanya Bundesliga","es.1":"İspanya La Liga","it.1":"İtalya Serie A","fr.1":"Fransa Ligue 1","nl.1":"Hollanda Eredivisie","pt.1":"Portekiz Primeira Liga","tr.1":"Türkiye Süper Lig"};
 const eligible=arr(k.rows).filter(x=>x.status==="agreed");
 const count=new Map();for(const x of eligible)count.set(x.oddsEventId,(count.get(x.oddsEventId)||0)+1);
 const out=[];
 for(const x of eligible){
   const league=names[x.league];
   if(!league||!x.oddsEventId||count.get(x.oddsEventId)!==1||!Number.isFinite(Date.parse(x.kickoff))||Date.parse(x.kickoff)<=now||dateTR(x.kickoff)!==x.date)continue;
   const events=arr(data.odds.events).filter(e=>e.id===x.oddsEventId&&e.league===LEAGUES[league]&&Date.parse(e.kickoff)===Date.parse(x.kickoff));
   if(events.length!==1)continue;
   const original=arr(x.published);
   out.push({date:x.date,league,match:x.match,event:{kickoff:x.kickoff},candidate:null,confirmed:true,originalDate:original.length===1?original[0].date:null});
 }
 return out.sort((a,b)=>Date.parse(a.event.kickoff)-Date.parse(b.event.kickoff)||a.league.localeCompare(b.league,"tr"));
}
function filterRows(rows,q,d,l,t){const s=String(q||"").trim().toLocaleLowerCase("tr");return rows.filter(r=>(!s||r.match.toLocaleLowerCase("tr").includes(s))&&(!d||r.date===d)&&(!l||r.league===l)&&(!t||(r.event&&((hourTR(r.event.kickoff)<"17:00")===(t==="day")))));}
if(typeof module!=="undefined"&&module.exports)module.exports={topScores,eventFor,rowsFor,filterRows,bound,leagueReport,fixtureCheck,confirmedRows};
if(typeof document==="undefined")return;
const by=id=>document.getElementById(id),node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let data={},rows=[],loadedAt=0,refreshing=false;
function expirySignature(data,now){return FILES.map(k=>fresh(data[k]?.updatedAt,now)?1:0).join('')+dateTR(now)+':'+confirmedRows(data,now).length;}
function expireView(){if(!refreshing&&loadedAt&&expirySignature(data,loadedAt)!==expirySignature(data,Date.now()))render();}
function metrics(values){const box=node("div",undefined,"metrics");for(const [label,value] of values){const c=node("div",undefined,"metric");c.append(node("b",value),node("small",label));box.append(c);}return box;}
function teamTitle(match){const parts=match.split(" – "),title=node("span",undefined,"match-title");if(parts.length!==2){title.textContent=match;return title;}for(const [i,name] of parts.entries()){if(i)title.append(node("span","VS","versus"));const team=node("span",undefined,"team-name"),crest=node("span",name.split(/\s+/).slice(0,2).map(w=>w[0]).join("").toUpperCase(),"team-crest"+(i?" away":""));crest.setAttribute("aria-hidden","true");team.append(crest,node("span",name));title.append(team);}return title;}
function probabilityBars(markets){const root=node("div");for(const m of MARKETS){const value=markets?.[m],row=node("div",undefined,"prob-row"),track=node("div",undefined,"prob-track"),fill=node("div",undefined,"prob-fill");fill.style.width=(typeof value==="number"&&Number.isFinite(value)&&value>=0&&value<=100?value:0)+"%";track.append(fill);row.append(node("span",m),track,node("b",pct(value)));root.append(row);}return root;}
function volumePanel(){const box=node("div",undefined,"panel volume-panel");
 box.append(node("h3","Uluslararası bahis hacmi"),metrics([["Dünya toplamı (TL)","—"],["Ölçülen hacim (TL)","—"],["Kaynak","Bağlı değil"]]),node("p","Dünya toplamı kamuya açık değil. Ölçülen hacim yalnızca izinli veri sağlayıcısının kapsadığı piyasalarda gösterilebilir. Oran değişimi, bahis miktarı değildir.","subtle"));return box;}
function detail(r){if(r.confirmed){
 const box=node("div",undefined,"detail");
 box.append(node("p","ESPN ve uluslararası oran kaynağında aynı başlama saati.","subtle"));
 if(r.originalDate&&r.originalDate!==r.date)box.append(node("p","Eski fikstür tarihi: "+r.originalDate+". Arşivdeki tahmin değiştirilmedi.","subtle"));
 box.append(node("p","Bu görünüm yalnızca fikstür doğrulamasıdır. Model tahmini veya bahis seçimi aktarılmaz.","subtle"),volumePanel());return box;
 }r={...r,event:eventFor(r,data,Date.now())};const x=node("div",undefined,"detail"),tabs=node("div",undefined,"detail-tabs"),out=node("div"),c=r.candidate;
const views={
"Goller":()=>{if(!c){out.append(node("p","Model tahmini yok.","subtle"));return;}out.append(node("p","Kalibre edilmemiş model olasılığı; kazanma garantisi değildir.","subtle"),probabilityBars(c.markets));},
"Skor":()=>{const s=topScores(c?.expectedGoals?.home,c?.expectedGoals?.away);out.append(node("p",s.length?"Bağımsız Poisson modelinin en olası 3 skor senaryosu.":"Skor modeli verisi yok.","subtle"));for(const y of s)out.append(node("p",y.score+" · "+pct(y.p)));},
"Oranlar":()=>{if(!r.event){out.append(node("p","Kesin eşleşen güncel oran kaydı yok.","subtle"));return;}for(const p of [1.5,2.5]){const v=arr(r.event.bookmakers).flatMap(b=>arr(b.lines).filter(l=>l.point===p&&fresh(l.lastUpdate,Date.now())&&typeof l.over==="number"&&l.over>1).map(l=>l.over));out.append(node("p",p+" Üst: "+(v.length?v.length+" kaynak · "+Math.min(...v).toFixed(2)+"–"+Math.max(...v).toFixed(2):"Veri yok")));}out.append(node("p","Oran hareketleri: ayrıntılı raporlarda. Gerçek para akışı verisi yok.","subtle"));},
"Para akışı":()=>out.append(volumePanel()),
"Diğer":()=>out.append(node("p","İY/MS, iki yarı KG Var ve kartlar için doğrulanmış veri/model henüz bağlı değil.","subtle"))};
for(const name of Object.keys(views)){const b=node("button",name);b.type="button";b.setAttribute("aria-pressed","false");b.onclick=()=>{for(const t of tabs.children)t.setAttribute("aria-pressed",String(t===b));out.replaceChildren();views[name]();};tabs.append(b);}const check=fixtureCheck(r,data,Date.now());if(check?.status==="date_difference")x.append(node("p","Tarih uyuşmazlığı: mevcut liste "+r.date+" / ESPN "+check.sourceDate+". Orijinal kayıt değiştirilmedi.","subtle"));else if(check?.status==="same_date")x.append(node("p","Fikstür tarihi ESPN ile eşleşiyor.","subtle"));else if(check)x.append(node("p","İkinci kaynakta kesin fikstür eşleşmesi yok.","subtle"));x.append(tabs,out);tabs.firstChild.click();return x;}
function quickMarkets(r){const el=node("span",undefined,"quick-markets");if(r.candidate&&!r.confirmed){for(const m of MARKETS){const p=pct(r.candidate.markets?.[m]);el.append(node("span",m+" "+p));}}else el.append(node("span","Model yüzdesi yok"));return el;}
function renderList(){const result=filterRows(rows,by("search").value,by("date-filter").value,by("league-filter").value,by("time-filter").value),box=by("match-list");by("match-count").textContent=result.length+" maç";box.replaceChildren();for(const r of result){const card=node("details",undefined,"match-card"),s=node("summary");s.append(node("span","⚽ "+r.league+(r.confirmed?" · İki kaynak":r.fixtureCheck?.status==="date_difference"?" · Tarih farkı":""),"match-meta"),teamTitle(r.match),node("span",r.date+" · "+(r.event?hourTR(r.event.kickoff)+" TSİ":"Saat belirsiz"),"match-time"),node("span",r.confirmed?"Fikstür doğrulaması":r.candidate?"Model analizi • Kalibre edilmedi":"Tahmin verisi yok","match-summary-label"),quickMarkets(r),node("span","Uluslararası bahis hacmi · TL: —","volume-strip"));card.append(s);card.addEventListener("toggle",()=>{if(card.open&&card.children.length===1)card.append(detail(r));});box.append(card);}if(!result.length)box.append(node("p",rows.length?"Filtreye uygun maç bulunamadı.":by("fixture-mode").value==="confirmed"?"Güncel çift kaynaklı saat kaydı yok. Genel listeyi seçebilirsin.":"Yayımlanan maç listesi okunamadı.","subtle"));}
function options(id,values,label){const e=by(id),old=e.value;e.replaceChildren(node("option",label));e.firstChild.value="";for(const v of values){const o=node("option",v);o.value=v;e.append(o);}if(values.includes(old))e.value=old;}
function panel(root,title,body){const p=node("article",undefined,"panel");p.append(node("h3",title));for(const el of body)p.append(el);root.append(p);}
function render(){loadedAt=Date.now();rows=by("fixture-mode").value==="confirmed"?confirmedRows(data,loadedAt):rowsFor(data,loadedAt);const current=["daily","matching","odds","prospective_validation","data_quality","unified_decision"].every(k=>bound(data,k,loadedAt))&&data.data_quality?.qualityGate==="PASS";const conn=by("connection");conn.className="status "+(current?"fresh":"stale");conn.textContent=current?"Güncel rapor · "+num(data.daily?.leaguesLoaded)+" lig · Araştırma modu":"Eksik veya eski rapor · PAS";options("date-filter",[...new Set(rows.map(x=>x.date))],"Tüm tarihler");options("league-filter",[...new Set(rows.map(x=>x.league))].sort((a,b)=>a.localeCompare(b,"tr")),"Tüm ligler");renderList();
 const root=by("performance-summary");root.replaceChildren();const v=data.prospective_validation;const verified=bound(data,"prospective_validation",loadedAt);panel(root,"İleriye dönük doğrulama",[metrics([["Sonuç",num(v?.tested)],["Bekleyen",num(v?.pending)],["Hedef",num(v?.minimumMatches)]]),node("p",verified?"Araştırma sürüyor; model henüz onaylı değil.":"Rapor eski veya eksik; değerler arşiv niteliğinde.","subtle")]);if(v?.marketResearch)for(const m of MARKETS){const x=v.marketResearch[m];if(x)panel(root,m,[node("p",num(x.tested)+" sonuç · "+num(x.pending)+" bekleyen"),node("p",x.tested&&typeof x.scores?.candidate==="number"?"Brier: "+x.scores.candidate.toFixed(4)+" (düşük daha iyi)":"Henüz karşılaştırılabilir sonuç yok.","subtle")]);}
 const leagueRows=leagueReport(data,loadedAt);
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
 const board=data.scoreboard_snapshot;
 if(board?.version==="4.90"&&board.mode==="scoreboard_snapshot"&&board.realTime===false&&Array.isArray(board.groups)){
   const isCurrent=bound(data,"scoreboard_snapshot",loadedAt)&&board.date===dateTR(loadedAt);
   panel(radar,isCurrent?"Son skor görüntüsü":"Eski skor görüntüsü — canlı değil",[node("p",board.date+" · "+(Number.isFinite(Date.parse(board.updatedAt))?hourTR(board.updatedAt):"—")+" TSİ · ESPN"),node("p",num(board.loadedLeagues)+" / 9 lig yanıt verdi. "+num(board.eventCount)+" maç kaydı.","subtle")]);
   if(isCurrent){for(const group of board.groups){if(group.error||!Array.isArray(group.rows))continue;for(const r of group.rows){if(r.state!=="in"&&r.state!=="post")continue;const score=Array.isArray(r.score)&&r.score.length===2?r.score.join(" – "):"Skor yok";panel(radar,r.home+" – "+r.away,[node("p",score),node("p",group.leagueName+" · "+(r.state==="in"?"Görüntü alındığında sürüyordu":"Kaynakta sona ermiş / durmuş")+(r.clock?" · "+r.clock:""),"subtle")]);}}if(board.inProgress===0)radar.append(node("p","Son görüntüde devam eden maç yok. Bu, şu anda maç olmadığı anlamına gelmez.","subtle"));}
 }else radar.append(node("p","Skor görüntüsü henüz yayımlanmadı.","subtle"));
 const c=by("coupon-summary");c.replaceChildren();panel(c,"PAS",[node("p","Onaylanmış otomatik kupon yok."),node("p","Kazanma olasılığı: doğrulanmadı. Model kalibrasyonu tamamlanmadı.","subtle")]);
 const s=by("settings-summary");s.replaceChildren(node("p","Son bildirilen API kredisi: "+num(data.odds?.remainingCredits)),node("p","Bütünlük: "+(current?"PASS":"Güncel doğrulama yok")),node("p","Ücretsiz araştırma • Türkiye dışı oran kaynakları","subtle"));
}
async function refresh(){if(refreshing)return;refreshing=true;by("refresh").disabled=true;by("connection").textContent="Raporlar okunuyor…";const next={};await Promise.all(FILES.map(async k=>{try{const r=await fetch("./"+k+".json?ts="+Date.now(),{cache:"no-store"});if(r.ok)next[k]=await r.json();}catch(_){}}));data=next;try{render();}catch(_){by("connection").textContent="Rapor biçimi doğrulanamadı · PAS";}finally{refreshing=false;by("refresh").disabled=false;}}
by("fixture-mode").onchange=()=>{by("date-filter").value="";by("league-filter").value="";render();};
for(const id of ["search","date-filter","league-filter","time-filter"])by(id).addEventListener(id==="search"?"input":"change",renderList);
const buttons=[...document.querySelectorAll("[data-tab]")];for(const b of buttons)b.onclick=()=>{for(const t of buttons){const active=t===b;by("view-"+t.dataset.tab).hidden=!active;if(active)t.setAttribute("aria-current","page");else t.removeAttribute("aria-current");}window.scrollTo(0,0);};
function theme(value){const resolved=value==="system"?(matchMedia("(prefers-color-scheme:light)").matches?"light":"dark"):value;document.documentElement.dataset.theme=resolved;try{localStorage.setItem("oa_theme",value);}catch(_){}}
let pref="dark";try{pref=localStorage.getItem("oa_theme")||"dark";}catch(_){}if(!["dark","light","system"].includes(pref))pref="dark";by("theme").value=pref;theme(pref);by("theme").onchange=e=>theme(e.target.value);
setInterval(expireView,15000);document.addEventListener("visibilitychange",()=>{if(!document.hidden){expireView();refresh();}});
by("refresh").onclick=refresh;if("serviceWorker"in navigator)navigator.serviceWorker.register("./sw.js").catch(()=>{});refresh();
})();