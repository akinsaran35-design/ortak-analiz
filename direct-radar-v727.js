/* Direct browser scoreboard observation, no keys, no proxy, no forecast. */
(function(){
"use strict";
const BASE="https://site.api.espn.com/apis/site/v2/sports/soccer/";
const CODES=["eng.1","eng.2","ger.1","esp.1","ita.1","fra.1","ned.1","por.1","tur.1","eng.3","eng.4","ger.2","esp.2","ita.2","sco.1"];
const INTERVAL=120000, MAX_AGE=120000;
const dateTR=t=>new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Istanbul",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(t));
function parse(doc,day,now){
 if(!Array.isArray(doc?.events))throw Error("schema");
 const rows=new Map(),duplicates=new Set();
 for(const e of doc.events){
  const c=e?.competitions?.length===1?e.competitions[0]:null,k=c?.status?.type;
  if(k?.state!=="in"||!c||!Array.isArray(c.competitors)||c.competitors.length!==2)continue;
  const id=String(e.id??""),start=Date.parse(c.date??e.date);
  if(!/^[0-9]+$/.test(id)||!Number.isFinite(start)||start>now||dateTR(start)!==day)continue;
  const h=c.competitors.find(t=>t?.homeAway==="home"),a=c.competitors.find(t=>t?.homeAway==="away");
  if(!h||!a)continue;
  const names=[h.team?.displayName,a.team?.displayName],scores=[h.score,a.score].map(v=>String(v??""));
  if(names.some(v=>typeof v!=="string"||!v.trim())||names[0]===names[1]||scores.some(v=>!/^\d+$/.test(v)||!Number.isSafeInteger(Number(v))))continue;
  const clock=c.status?.displayClock;
  if(typeof clock!=="string"||!clock.trim())continue;
  if(rows.has(id))duplicates.add(id);
  rows.set(id,{id,home:names[0],away:names[1],score:scores.map(Number),clock});
 }
 return [...rows.values()].filter(r=>!duplicates.has(r.id));
}
async function request(url,fetcher){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);
 try{
  const response=await fetcher(url,{cache:"no-store",credentials:"omit",signal:controller.signal});
  if(!response.ok)throw Error("http");
  return await response.json();
 }finally{clearTimeout(timer);}
}
async function collect(fetcher=fetch,now=()=>Date.now(),codes=CODES){
 const day=dateTR(now()),results=[];
 for(let i=0;i<codes.length;i+=4){
  const batch=codes.slice(i,i+4);
  results.push(...await Promise.all(batch.map(async code=>{
   try{
    const doc=await request(BASE+code+"/scoreboard?dates="+day.replace(/-/g,""),fetcher);
    const receivedAt=now();
    return {code,ok:true,receivedAt,rows:parse(doc,day,receivedAt)};
   }catch(_){return {code,ok:false,rows:[]};}
  })));
 }
 return {day,results,updatedAt:now(),sourceTimestampVerified:false,predictionsEnabled:false};
}
function retryDelay(report,manual=false){
 if(report&&report.results.length&&report.results.every(g=>!g.ok))return manual?60000:900000;
 return manual?30000:INTERVAL;
}
function visible(report,now){
 if(!report||report.day!==dateTR(now)||report.predictionsEnabled!==false)return [];
 return report.results.flatMap(g=>g.ok&&now>=g.receivedAt&&now-g.receivedAt<=MAX_AGE?g.rows.map(r=>({...r,league:g.code,receivedAt:g.receivedAt})):[]);
}
if(typeof module!=="undefined"&&module.exports)module.exports={parse,collect,visible,CODES,retryDelay};
if(typeof document==="undefined")return;
const host=document.getElementById("direct-radar"),view=document.getElementById("view-live");
if(!host||!view)return;
let report=null,busy=false,lastAttempt=0;
const el=(tag,txt,cls)=>{const n=document.createElement(tag);n.textContent=txt;if(cls)n.className=cls;return n;};
const allowed=()=>!document.hidden&&!view.hidden&&view.querySelector('[data-sport="football"]')?.getAttribute("aria-pressed")==="true";
const time=t=>new Intl.DateTimeFormat("tr-TR",{timeZone:"Europe/Istanbul",hour:"2-digit",minute:"2-digit",second:"2-digit"}).format(t);
function render(){
 host.hidden=!allowed();
 if(host.hidden)return;
 const now=Date.now(),rows=visible(report,now);
 const title=el("h3","Doğrudan skor kaynağı · ESPN");
 const note=el("p","Tarayıcıdan sorgu; sağlayıcı zaman damgası doğrulanmadı. Tahmin ve xG üretmez.","subtle");
 const refresh=el("button",busy?"Sorgulanıyor…":"Skorları yenile");refresh.type="button";refresh.disabled=busy||now-lastAttempt<retryDelay(report,true);refresh.onclick=()=>run(true);
 const state=el("p",busy?"Kaynak kontrol ediliyor…":report?report.results.filter(g=>g.ok).length+"/"+report.results.length+" lig yanıt verdi · Alım "+time(report.updatedAt)+" TSİ":"Sorgu bekleniyor.","subtle");
 host.replaceChildren(title,note,refresh,state);
 if(report&&!rows.length)host.append(el("p",report.results.some(g=>g.ok)?"Taze maç gözlemi yok; diğer kaynak aşağıda.":"Doğrudan erişim başarısız; otomatik sorgu 15 dakika ertelendi. Yayımlanmış radar aşağıda.","subtle"));
 for(const r of rows){
  const item=el("article","","panel");
  item.append(el("h3",r.home+" – "+r.away),el("p",r.score.join(" – ")+" · "+r.clock),el("p",r.league+" · Alım "+time(r.receivedAt)+" TSİ","subtle"));
  host.append(item);
 }
}
async function run(manual=false){
 if(!allowed()||busy||Date.now()-lastAttempt<retryDelay(report,manual))return;
 lastAttempt=Date.now();busy=true;render();
 try{report=await collect();}finally{busy=false;render();}
}
document.addEventListener("click",e=>{
 if(e.target.closest?.("[data-tab],[data-sport]")){render();void run();}
});
document.addEventListener("visibilitychange",()=>{render();void run();});
setInterval(()=>{if(allowed()){render();void run();}},15000);
render();
})();
