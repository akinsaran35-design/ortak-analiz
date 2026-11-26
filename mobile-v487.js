(function(){
"use strict";
const FILES=["daily","matching","odds","performance","prospective_validation","data_quality","unified_decision","snapshot_integrity","prospective_leagues"];
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
function eventFor(row,data,now){if(!["daily","matching","odds"].every(k=>bound(data,k,now)))return null;const m=arr(data.matching.matched).filter(x=>x.match===row.match&&Number.isFinite(Date.parse(x.kickoff))&&dateTR(x.kickoff)===row.date);if(m.length!==1)return null;const e=arr(data.odds.events).filter(x=>x.id===m[0].eventId&&x.kickoff===m[0].kickoff&&x.league===LEAGUES[row.league]);return e.length===1?e[0]:null;}
function rowsFor(data,now){const candidates=new Map(arr(data.daily?.candidates).map(c=>[key(c),c])),unique=new Map();for(const r of arr(data.daily?.upcoming)){if(r&&typeof r.match==="string"&&typeof r.league==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&!unique.has(key(r)))unique.set(key(r),{...r,candidate:candidates.get(key(r))||null,event:eventFor(r,data,now)});}return [...unique.values()].sort((a,b)=>a.date.localeCompare(b.date)||String(a.event?.kickoff||"z").localeCompare(String(b.event?.kickoff||"z"))||a.league.localeCompare(b.league,"tr"));}
function filterRows(rows,q,d,l,t){const s=String(q||"").trim().toLocaleLowerCase("tr");return rows.filter(r=>(!s||r.match.toLocaleLowerCase("tr").includes(s))&&(!d||r.date===d)&&(!l||r.league===l)&&(!t||(r.event&&((hourTR(r.event.kickoff)<"17:00")===(t==="day")))));}
if(typeof module!=="undefined"&&module.exports)module.exports={topScores,eventFor,rowsFor,filterRows,bound,leagueReport};
if(typeof document==="undefined")return;
const by=id=>document.getElementById(id),node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let data={},rows=[],loadedAt=0;
function metrics(values){const box=node("div",undefined,"metrics");for(const [label,value] of values){const c=node("div",undefined,"metric");c.append(node("b",value),node("small",label));box.append(c);}return box;}
function detail(r){const x=node("div",undefined,"detail"),tabs=node("div",undefined,"detail-tabs"),out=node("div"),c=r.candidate;
const views={
"Goller":()=>{if(!c){out.append(node("p","Model tahmini yok.","subtle"));return;}out.append(node("p","Kalibre edilmemiş model olasılığı; kazanma garantisi değildir.","subtle"),metrics(MARKETS.map(m=>[m,pct(c.markets?.[m])])));},
"Skor":()=>{const s=topScores(c?.expectedGoals?.home,c?.expectedGoals?.away);out.append(node("p",s.length?"Bağımsız Poisson modelinin en olası 3 skor senaryosu.":"Skor modeli verisi yok.","subtle"));for(const y of s)out.append(node("p",y.score+" · "+pct(y.p)));},
"Oranlar":()=>{if(!r.event){out.append(node("p","Kesin eşleşen güncel oran kaydı yok.","subtle"));return;}for(const p of [1.5,2.5]){const v=arr(r.event.bookmakers).flatMap(b=>arr(b.lines).filter(l=>l.point===p&&fresh(l.lastUpdate,Date.now())&&typeof l.over==="number"&&l.over>1).map(l=>l.over));out.append(node("p",p+" Üst: "+(v.length?v.length+" kaynak · "+Math.min(...v).toFixed(2)+"–"+Math.max(...v).toFixed(2):"Veri yok")));}out.append(node("p","Oran hareketleri: ayrıntılı raporlarda. Gerçek para akışı verisi yok.","subtle"));},
"Diğer":()=>out.append(node("p","İY/MS, iki yarı KG Var, kartlar ve para akışı için doğrulanmış veri/model henüz bağlı değil.","subtle"))};
for(const name of Object.keys(views)){const b=node("button",name);b.type="button";b.setAttribute("aria-pressed","false");b.onclick=()=>{for(const t of tabs.children)t.setAttribute("aria-pressed",String(t===b));out.replaceChildren();views[name]();};tabs.append(b);}x.append(tabs,out);tabs.firstChild.click();return x;}
function renderList(){const result=filterRows(rows,by("search").value,by("date-filter").value,by("league-filter").value,by("time-filter").value),box=by("match-list");by("match-count").textContent=result.length+" maç";box.replaceChildren();for(const r of result){const card=node("details",undefined,"match-card"),s=node("summary");s.append(node("span",r.league+" · "+r.date+" · "+(r.event?hourTR(r.event.kickoff):"Saat belirsiz"),"match-meta"),node("span",r.match,"match-title"));card.append(s);card.addEventListener("toggle",()=>{if(card.open&&card.children.length===1)card.append(detail(r));});box.append(card);}if(!result.length)box.append(node("p",rows.length?"Filtreye uygun maç bulunamadı.":"Yayımlanan maç listesi okunamadı.","subtle"));}
function options(id,values,label){const e=by(id),old=e.value;e.replaceChildren(node("option",label));e.firstChild.value="";for(const v of values){const o=node("option",v);o.value=v;e.append(o);}if(values.includes(old))e.value=old;}
function panel(root,title,body){const p=node("article",undefined,"panel");p.append(node("h3",title));for(const el of body)p.append(el);root.append(p);}
function render(){loadedAt=Date.now();rows=rowsFor(data,loadedAt);const current=["daily","matching","odds","prospective_validation","data_quality","unified_decision"].every(k=>bound(data,k,loadedAt))&&data.data_quality?.qualityGate==="PASS";const conn=by("connection");conn.className="status "+(current?"fresh":"stale");conn.textContent=current?"Güncel rapor · "+num(data.daily?.leaguesLoaded)+" lig · Araştırma modu":"Eksik veya eski rapor · PAS";options("date-filter",[...new Set(rows.map(x=>x.date))],"Tüm tarihler");options("league-filter",[...new Set(rows.map(x=>x.league))].sort((a,b)=>a.localeCompare(b,"tr")),"Tüm ligler");renderList();
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
 const c=by("coupon-summary");c.replaceChildren();panel(c,"PAS",[node("p","Onaylanmış otomatik kupon yok."),node("p","Kazanma olasılığı: doğrulanmadı. Model kalibrasyonu tamamlanmadı.","subtle")]);
 const s=by("settings-summary");s.replaceChildren(node("p","Son bildirilen API kredisi: "+num(data.odds?.remainingCredits)),node("p","Bütünlük: "+(current?"PASS":"Güncel doğrulama yok")),node("p","Ücretsiz araştırma • Türkiye dışı oran kaynakları","subtle"));
}
async function refresh(){by("refresh").disabled=true;by("connection").textContent="Raporlar okunuyor…";const next={};await Promise.all(FILES.map(async k=>{try{const r=await fetch("./"+k+".json?ts="+Date.now(),{cache:"no-store"});if(r.ok)next[k]=await r.json();}catch(_){}}));data=next;try{render();}catch(_){by("connection").textContent="Rapor biçimi doğrulanamadı · PAS";}finally{by("refresh").disabled=false;}}
for(const id of ["search","date-filter","league-filter","time-filter"])by(id).addEventListener(id==="search"?"input":"change",renderList);
const buttons=[...document.querySelectorAll("[data-tab]")];for(const b of buttons)b.onclick=()=>{for(const t of buttons){const active=t===b;by("view-"+t.dataset.tab).hidden=!active;if(active)t.setAttribute("aria-current","page");else t.removeAttribute("aria-current");}window.scrollTo(0,0);};
function theme(value){const resolved=value==="system"?(matchMedia("(prefers-color-scheme:light)").matches?"light":"dark"):value;document.documentElement.dataset.theme=resolved;try{localStorage.setItem("oa_theme",value);}catch(_){}}
let pref="dark";try{pref=localStorage.getItem("oa_theme")||"dark";}catch(_){}if(!["dark","light","system"].includes(pref))pref="dark";by("theme").value=pref;theme(pref);by("theme").onchange=e=>theme(e.target.value);
by("refresh").onclick=refresh;if("serviceWorker"in navigator)navigator.serviceWorker.register("./sw.js").catch(()=>{});refresh();
})();