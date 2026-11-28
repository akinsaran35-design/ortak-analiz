const assert=require("node:assert/strict");
const {parse,collect,visible,CODES}=require("../direct-radar-v727.js");
const now=Date.parse("2026-11-28T12:00:00Z"),day="2026-11-28";
function event(id="1"){
 return {id,date:"2026-11-28T11:00:00Z",competitions:[{date:"2026-11-28T11:00:00Z",status:{type:{state:"in"},displayClock:"60'"},competitors:[{homeAway:"home",team:{displayName:"A"},score:"1"},{homeAway:"away",team:{displayName:"B"},score:"0"}]}]};
}
(async()=>{
 assert.equal(CODES.length,15);
 assert.deepEqual(parse({events:[event()]},day,now),[{id:"1",home:"A",away:"B",score:[1,0],clock:"60'"}]);
 assert.deepEqual(parse({events:[event(),event()]},day,now),[]);
 const e=event();e.competitions[0].status.type.state="post";assert.equal(parse({events:[e]},day,now).length,0);
 const bad=event();bad.competitions[0].competitors[0].score="";assert.equal(parse({events:[bad]},day,now).length,0);
 assert.equal(parse({events:[event()]},"2026-11-27",now).length,0);
 assert.throws(()=>parse({},day,now));
 const urls=[];
 const report=await collect(async(url,opts)=>{
   urls.push(url);assert.equal(opts.credentials,"omit");assert.equal(opts.cache,"no-store");
   if(url.includes("/eng.2/"))throw Error("network");
   return {ok:true,json:async()=>({events:[event()]})};
 },()=>now,["eng.1","eng.2"]);
 assert.equal(urls.length,2);assert.equal(report.results[1].ok,false);assert.equal(visible(report,now).length,1);
 assert.equal(visible(report,now+120001).length,0);assert.equal(visible(report,now-1).length,0);
 assert.equal(report.predictionsEnabled,false);
 console.log("Direct scoreboard tests passed");
})().catch(e=>{console.error(e);process.exitCode=1;});
