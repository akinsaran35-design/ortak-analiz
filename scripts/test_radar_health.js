const assert=require("node:assert/strict");
const handler=require("../api/radar-health");
function call(method){
 const result={headers:{}};
 const res={setHeader(k,v){result.headers[k]=v;},status(s){result.status=s;return this;},json(v){result.body=v;return this;}};
 handler({method},res);return result;
}
const r=call("GET");
assert.equal(r.status,200);
assert.equal(r.headers["Cache-Control"],"no-store");
assert.equal(r.body.status,"server_ready");
assert.equal(r.body.upstreamRequests,0);
assert.equal(r.body.liveDataAvailable,false);
assert.equal(r.body.predictionsEnabled,false);
assert.ok(Number.isFinite(Date.parse(r.body.checkedAt)));
assert.equal(call("POST").status,405);
assert.equal(call("POST").headers.Allow,"GET");
console.log("Vercel radar health tests passed");
