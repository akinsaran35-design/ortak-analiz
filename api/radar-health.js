// V7.28: deployment health only. No provider requests, secrets or forecasts.
function handler(req,res) {
  res.setHeader("Cache-Control","no-store");
  res.setHeader("Content-Type","application/json; charset=utf-8");
  if(req.method!=="GET"){
    res.setHeader("Allow","GET");
    return res.status(405).json({error:"method_not_allowed"});
  }
  return res.status(200).json({
    version:"7.28",
    service:"ortak-analiz-radar",
    status:"server_ready",
    checkedAt:new Date().toISOString(),
    upstreamEnabled:false,
    upstreamRequests:0,
    liveDataAvailable:false,
    predictionsEnabled:false,
    decision:"PAS"
  });
}
module.exports=handler;
