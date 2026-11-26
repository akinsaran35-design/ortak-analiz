const assert=require("node:assert/strict");
const {chromium}=require("playwright");
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:360,height:800},isMobile:true,hasTouch:true,deviceScaleFactor:2,serviceWorkers:"block"});
  const page=await context.newPage();
  const errors=[];page.on("pageerror",e=>errors.push(e.message));
  const now=Date.parse("2026-11-26T15:00:00Z"),updatedAt=new Date(now).toISOString();
  await page.clock.install({time:new Date(now)});
  const row={date:"2026-11-27",league:"İngiltere Premier Lig",match:"SV Werder Bremen – Borussia Mönchengladbach"};
  const event={id:"1",league:"soccer_epl",kickoff:"2026-11-27T18:00:00Z",bookmakers:[]};
  const d={daily:{updatedAt,upcoming:[row],candidates:[{...row,markets:{"1.5 Üst":80,"2.5 Üst":60,"KG Var":50},expectedGoals:{home:1.5,away:1}}],leaguesLoaded:9},matching:{updatedAt,matched:[{match:row.match,eventId:"1",kickoff:event.kickoff}]},odds:{updatedAt,events:[event],remainingCredits:100},data_quality:{updatedAt,qualityGate:"PASS"},unified_decision:{updatedAt,decision:"PAS"},prospective_validation:{updatedAt,tested:4,pending:86,minimumMatches:500},fixture_coverage_audit:{version:"4.92",updatedAt,dailyUpdatedAt:updatedAt,mode:"research_only",decision:"PAS",archivesModified:false,dates:[row.date],rows:[{status:"same_date",published:[row],espn:[{date:row.date}]}]},kickoff_confirmation:{version:"4.94",updatedAt,available:true,mode:"research_only",decision:"PAS",archivesModified:false,dailyUpdatedAt:updatedAt,coverageUpdatedAt:updatedAt,oddsUpdatedAt:updatedAt,rows:[{league:"en.1",date:row.date,match:row.match,kickoff:event.kickoff,oddsEventId:event.id,status:"agreed",published:[row]}]}};
  d.snapshot_integrity={updatedAt,status:"PASS",errors:[],reportTimestamps:Object.fromEntries(Object.keys(d).map(k=>[k+".json",updatedAt]))};
  await page.route(/\.json(?:\?|$)/,route=>{const k=new URL(route.request().url()).pathname.split("/").pop().replace(/\.json$/,"");return route.fulfill(d[k]?{status:200,json:d[k]}:{status:404,body:"missing"});});
  await page.goto("http://127.0.0.1:8765/index.html");
  await page.locator("#match-count").filter({hasText:"1 maç"}).waitFor();
  await page.locator(".volume-strip").getByText("Uluslararası bahis hacmi",{exact:true}).waitFor();
  await page.locator(".match-card summary").click();
  await page.locator(".prob-row").getByText("%80",{exact:true}).waitFor();
  for(const width of [320,360,393,412]){
    await page.setViewportSize({width,height:800});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    for(const selector of [".match-card",".prob-row b",".bankroll-card",".bottom-nav"]){
      const boxes=await page.locator(selector).evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return [r.left,r.right]}));
      assert.ok(boxes.length>0&&boxes.every(([l,r])=>l>=-1&&r<=width+1),selector+" clipped at "+width);
    }
    const nav=await page.locator(".bottom-nav").boundingBox();
    assert.ok(nav.y>=0&&nav.y+nav.height<=801);
  }
  await page.setViewportSize({width:393,height:852});
  await page.screenshot({path:"mobile-reference-detail.png"});
  await page.getByRole("button",{name:"Para akışı",exact:true}).click();
  await page.getByText("Dünya toplamı (TL)",{exact:true}).waitFor();
  await page.getByText("Bağlı değil",{exact:true}).waitFor();
  await page.getByRole("button",{name:"Skor",exact:true}).click();
  await page.getByText("Bağımsız Poisson modelinin en olası 3 skor senaryosu.").waitFor();
  await page.locator(".filter-panel summary").click();
  await page.locator("#search").fill("ZZZ");
  await page.getByText("Filtreye uygun maç bulunamadı.").waitFor();
  await page.locator("#search").fill("");
  await page.locator("#fixture-mode").selectOption("confirmed");
  await page.getByText(/İki kaynak/).waitFor();
  await page.locator(".match-card summary").click();
  await page.getByText("Bu görünüm yalnızca fikstür doğrulamasıdır.",{exact:false}).waitFor();
  for(const tab of ["live","performance","coupons","settings","matches"]){
    await page.locator("#tab-"+tab).click();
    assert.equal(await page.locator("#view-"+tab).isVisible(),true);
    assert.equal(await page.locator(".view:visible").count(),1);
  }
  await page.locator("#tab-settings").click();
  await page.locator("#budget-value").fill("5000");
  await page.locator("#budget-form button").click();
  await page.locator("#tab-coupons").click();
  await page.getByText("Elle bahis kaydı ekle",{exact:true}).click();
  await page.locator("#record-label").fill("Test kaydı");
  await page.locator("#record-stake").fill("200");
  await page.getByRole("button",{name:"Geçmiş bahis kaydı ekle"}).click();
  await page.locator('input[id^="return-"]').fill("372");
  await page.getByRole("button",{name:"Sonucu kaydet"}).click();
  await page.locator("#tab-performance").click();
  await page.locator("#money-performance").getByText("Net sonuç",{exact:true}).waitFor();
  assert.equal(await page.locator("#money-performance .money-tile").filter({hasText:"Net sonuç"}).locator("strong").innerText(),(172).toLocaleString("tr-TR",{style:"currency",currency:"TRY",maximumFractionDigits:2}));
  await page.locator("#tab-settings").click();
  await page.locator("#theme").selectOption("light");
  assert.equal(await page.locator("html").getAttribute("data-theme"),"light");
  await page.locator("#tab-matches").click();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.clock.fastForward(31*60*1000);
  await page.getByText("Güncel çift kaynaklı saat kaydı yok.",{exact:false}).waitFor();
  assert.deepEqual(errors,[]);
  console.log("Mobile Chromium: navigation, match detail, search, corroborated view, theme, width and expiry passed");
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
