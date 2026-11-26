/* PRO personal record book. No connection to a betting provider. */
(function(){
"use strict";
const KEY="oa_pro_ledger_v497";
const cents=v=>v===""?null:Number.isFinite(Number(v))&&Number(v)>=0&&Number(v)<=1e8?Math.round(Number(v)*100):null;
const amount=v=>Number.isSafeInteger(v)&&v>=0;
const money=v=>v===null?"—":(v/100).toLocaleString("tr-TR",{style:"currency",currency:"TRY",maximumFractionDigits:2});
const day=t=>new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Istanbul",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(t));
function empty(){return {budget:null,limit:10,records:[]};}
function valid(s){return s&& (s.budget===null||amount(s.budget))&&Number.isInteger(s.limit)&&s.limit>=0&&s.limit<=100&&Array.isArray(s.records)&&s.records.every(r=>typeof r.id==="string"&&typeof r.label==="string"&&r.label.trim()&&/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&amount(r.stake)&&r.stake>0&&(r.returned===null||amount(r.returned)))&&new Set(s.records.map(r=>r.id)).size===s.records.length;}
function totals(records){
 let invested=0,returned=0,settledStake=0,open=0,won=0,lost=0,even=0;
 for(const r of records){invested+=r.stake;if(r.returned===null){open++;continue;}settledStake+=r.stake;returned+=r.returned;if(r.returned>r.stake)won++;else if(r.returned<r.stake)lost++;else even++;}
 const net=returned-settledStake;
 return {invested,returned,settledStake,open,won,lost,even,net,roi:settledStake?net/settledStake*100:null};
}
function summary(s,today){const all=totals(s.records),spent=totals(s.records.filter(r=>r.date===today)).invested;return {...all,spent,balance:s.budget===null?null:s.budget-all.invested+all.returned,dailyCap:s.budget===null?null:Math.round(s.budget*s.limit/100)};}
function periodRecords(records,period,today){let start=today;if(period==="month")start=today.slice(0,7)+"-01";if(period==="week"){const d=new Date(today+"T12:00:00Z");d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));start=d.toISOString().slice(0,10);}return records.filter(r=>r.date>=start&&r.date<=today);}
if(typeof module!=="undefined"&&module.exports)module.exports={cents,totals,summary,periodRecords,valid,empty};
if(typeof document==="undefined")return;
const by=id=>document.getElementById(id),el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let state=empty(),error="",period="month",view="active";
try{const raw=localStorage.getItem(KEY);if(raw){const v=JSON.parse(raw);if(!valid(v))throw Error("invalid");state=v;}}catch(_){error="Yerel kayıt okunamadı. Mevcut verinin üzerine yazılmadı.";}
let locked=!!error;
function save(next){if(locked)return false;try{if(!valid(next))throw Error("invalid");localStorage.setItem(KEY,JSON.stringify(next));state=next;error="";render();return true;}catch(_){error="Kayıt kaydedilemedi; önceki veriler korundu.";render();return false;}}
function tile(label,value,cls=""){const t=el("div",undefined,"money-tile "+cls);t.append(el("small",label),el("strong",value));return t;}
function tiles(items){const d=el("div",undefined,"money-grid");for(const args of items)d.append(tile(...args));return d;}
function heading(title){return el("h3",title);}
function panel(title,...children){const d=el("article",undefined,"panel money-panel");d.append(heading(title),...children);return d;}
function choices(items,value,on){const d=el("div",undefined,"money-tabs");for(const [id,label] of items){const b=el("button",label);b.type="button";b.setAttribute("aria-pressed",String(id===value));b.onclick=()=>{on(id);render();};d.append(b);}return d;}
function field(label,id,type,props={}){const l=el("label",label),i=el("input");i.id=id;i.type=type;Object.assign(i,props);l.append(i);return l;}
function chart(records){const d=el("div",undefined,"ledger-chart");const settled=records.filter(r=>r.returned!==null).sort((a,b)=>a.date.localeCompare(b.date));if(!settled.length){d.append(el("p","Grafik için sonuçlanmış kayıt yok.","subtle"));return d;}let net=0;const values=[0,...settled.map(r=>(net+=r.returned-r.stake))],lo=Math.min(0,...values),hi=Math.max(0,...values),range=hi-lo||1;const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 300 100");svg.setAttribute("role","img");svg.setAttribute("aria-label","Kayıt sırasına göre birikimli net sonuç: "+money(net));const line=document.createElementNS(svg.namespaceURI,"polyline");line.setAttribute("points",values.map((v,i)=>(8+i*284/(values.length-1))+","+(90-(v-lo)*80/range)).join(" "));line.setAttribute("fill","none");line.setAttribute("stroke","currentColor");line.setAttribute("stroke-width","2.6");svg.append(line);d.append(svg,el("p","Birikimli net sonuç: "+money(net),"subtle"));return d;}
function render(){const today=day(Date.now()),s=summary(state,today),home=by("bankroll-summary");home.replaceChildren();const top=el("div",undefined,"balance-top");top.append(el("span","◉","coin-icon"),tile("Bankroll · kayıtlı bakiye",money(s.balance),"balance-value"));home.append(top,tiles([["Günlük limit",state.limit+"%"],["Bugün yatırılan",money(s.spent)],["Kalan günlük limit",money(s.dailyCap===null?null:Math.max(0,s.dailyCap-s.spent))]]),el("p",state.budget===null?"Başlangıç bütçeni Ayarlar'da gir.":"Kişisel kayıt defteri · bahis hesabına bağlı değil","subtle"));if(error)home.append(el("p",error,"subtle"));
 const perf=by("money-performance"),rec=periodRecords(state.records,period,today),p=totals(rec);
 perf.replaceChildren(choices([["day","Bugün"],["week","Bu Hafta"],["month","Bu Ay"]],period,v=>period=v),tiles([["Toplam yatırılan",money(p.invested)],["Toplam geri dönüş",money(p.returned)],["Net sonuç",money(p.net),p.net<0?"negative":"positive"],["ROI",p.roi===null?"—":"%"+p.roi.toLocaleString("tr-TR",{maximumFractionDigits:1})],["Kazanan kayıt",String(p.won),"positive"],["Kaybeden kayıt",String(p.lost),"negative"]]),panel("Net sonuç grafiği",chart(rec),el("p","Dönem, bahis kayıt tarihine göre; net sonuç ve ROI yalnızca sonuçlanan kayıtlar.","subtle")));
 const cp=by("money-coupons");cp.replaceChildren(choices([["active","Aktif"],["settled","Sonuçlanan"],["all","Arşiv"]],view,v=>view=v),tiles([["Açık kayıt",String(s.open)],["Sonuçlanan",String(s.won+s.lost+s.even)],["Toplam yatırılan",money(s.invested)]]));
 const form=el("form");form.append(field("Kupon açıklaması","record-label","text",{required:true,maxLength:120,placeholder:"Önceden oynanmış kupon"}),field("Yatırılan tutar (TL)","record-stake","number",{required:true,min:"0.01",max:"100000000",step:"0.01"}),field("Kayıt tarihi","record-date","date",{required:true,max:today,value:today}));const submit=el("button","Geçmiş bahis kaydı ekle","action");submit.type="submit";submit.disabled=locked;form.append(submit);form.onsubmit=e=>{e.preventDefault();const stake=cents(by("record-stake").value),label=by("record-label").value.trim(),date=by("record-date").value;if(!stake||!label||date>today||!date)return;save({...state,records:[...state.records,{id:crypto.randomUUID(),label,date,stake,returned:null}]});};const add=el("details",undefined,"panel money-panel");add.append(el("summary","Elle bahis kaydı ekle"),el("p","Sadece daha önce yatırdığın parayı kaydet; uygulama bahis yapmaz.","subtle"),form);cp.append(add);
 const list=state.records.filter(r=>view==="all"||(view==="active"?r.returned===null:r.returned!==null)).slice().reverse();if(!list.length)cp.append(panel("Kayıt yok",el("p","Bu görünümde henüz kişisel kayıt yok.","subtle")));
 for(const r of list){const card=panel(r.label,el("p",r.date+" · "+(r.returned===null?"Açık":"Sonuçlandı"),"subtle"),tiles([["Yatırılan",money(r.stake)],["Gerçek dönüş",money(r.returned)],["Net",r.returned===null?"—":money(r.returned-r.stake)]]));if(r.returned===null){const f=el("form"),l=field("Gerçek geri dönüş (TL; kayıp için 0)","return-"+r.id,"number",{min:"0",max:"100000000",step:"0.01",required:true}),b=el("button","Sonucu kaydet","action");b.type="submit";b.disabled=locked;f.append(l,b);f.onsubmit=e=>{e.preventDefault();const v=cents(l.querySelector("input").value);if(v!==null)save({...state,records:state.records.map(x=>x.id===r.id?{...x,returned:v}:x)});};card.append(f);}cp.append(card);}
}
by("budget-value").value=state.budget===null?"":state.budget/100;by("budget-limit").value=state.limit;
by("budget-form").onsubmit=e=>{e.preventDefault();const budget=cents(by("budget-value").value),limit=Number(by("budget-limit").value);if(budget!==null&&Number.isInteger(limit)&&limit>=0&&limit<=100)save({...state,budget,limit});};
render();
})();
