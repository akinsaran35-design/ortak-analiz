const {chromium}=require("playwright");
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();
  const origin="https://akinsaran35-design.github.io";
  await page.route(origin+"/ortak-analiz/__cors_probe__",r=>r.fulfill({status:200,contentType:"text/html",body:"<!doctype html><title>Origin test</title>"}));
  await page.goto(origin+"/ortak-analiz/__cors_probe__");
  const result=await page.evaluate(async()=>{
   const day=new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Istanbul",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date()).replace(/-/g,"");
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
   try{
    const r=await fetch("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates="+day,{credentials:"omit",cache:"no-store",signal:controller.signal});
    const j=await r.json();
    return {accessible:r.ok&&Array.isArray(j.events),httpStatus:r.status,eventCount:Array.isArray(j.events)?j.events.length:null};
   }catch(e){return {accessible:false,error:e.name};}finally{clearTimeout(timer);}
  });
  console.log("DIRECT_RADAR_CORS",JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
