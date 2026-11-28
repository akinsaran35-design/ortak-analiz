const assert=require("node:assert/strict");
const {liveRows,lastLiveRows}=require("../mobile-v487.js");
const now=Date.parse("2026-11-28T12:00:00Z");
function makeRow(i,age=0){
 return {league:"en.1",eventId:String(i),home:"A"+i,away:"B"+i,quality:"observation_ready",receivedAt:new Date(now-age).toISOString(),observation:{state:"in",score:[1,0],clock:"54'",metrics:{corners:[4,1],shots:[8,3],shotsOnTarget:[3,1],yellowCards:[1,0],redCards:[0,0],possession:[60,40]}}};
}
function report(rows,age=0){return {version:"5.15",mode:"live_analysis_quality_only",predictionsEnabled:false,sourceTimestampVerified:false,decision:"PAS",updatedAt:new Date(now-age).toISOString(),rows};}
assert.equal(liveRows(report(Array.from({length:48},(_,i)=>makeRow(i))),now).length,48);
assert.equal(liveRows(report(Array.from({length:49},(_,i)=>makeRow(i))),now).length,0);
const old=report([makeRow(1,180000)],180000);
assert.equal(liveRows(old,now).length,0);
assert.equal(lastLiveRows(old,now).length,1);
assert.equal(lastLiveRows(old,now+21*60000).length,0);
assert.equal(lastLiveRows(report([makeRow(1)]),now).length,0);
assert.equal(lastLiveRows(report([makeRow(1,180000),makeRow(1,180000)],180000),now).length,0);
assert.equal(lastLiveRows({...old,predictionsEnabled:true},now).length,0);
assert.equal(lastLiveRows(report([makeRow(1,-1000)]),now).length,0);
console.log("Live radar capacity and age tests passed");
