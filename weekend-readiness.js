(function () {
  "use strict";
  const files = ["daily.json","odds.json","data_quality.json","prospective_validation.json","unified_decision.json"];
  const integer = n => Number.isInteger(n) && n >= 0 ? n : null;
  const fresh = (v, now) => {
    const t = Date.parse(v);
    return Number.isFinite(t) && now >= t && now-t <= 1800000;
  };
  const dateTR = t => new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Istanbul",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(t));
  function summarize(data, now) {
    const [daily, odds, quality, validation, decision] = files.map(f=>data[f] || {});
    const today = dateTR(now);
    const upcoming = Array.isArray(daily.upcoming) ? daily.upcoming : [];
    const weekend = {"2026-11-28":0,"2026-11-29":0};
    for (const row of upcoming) {
      if (row && Object.hasOwn(weekend,row.date)) weekend[row.date]++;
    }
    const missing = files.filter(f=>!data[f]);
    const stale = files.filter(f=>!fresh(data[f]?.updatedAt,now));
    const healthy = quality.status==="healthy" && quality.qualityGate==="PASS" &&
      Array.isArray(quality.errors) && quality.errors.length===0 &&
      Array.isArray(quality.warnings) && quality.warnings.length===0;
    return {today, weekend, missing, stale, healthy, dailyDate:daily.date || null,
      leagues:integer(daily.leaguesLoaded), fixtures:integer(daily.fixturesToday),
      fixtureCoverageComplete:daily.fixtureCoverageComplete===true && daily.upcomingCount===upcoming.length,
      events:integer(odds.eventCount), credits:integer(odds.remainingCredits),
      tested:integer(validation.tested), pending:integer(validation.pending),
      minimum:integer(validation.minimumMatches), calibrated:decision.modelCalibrated===true,
      dataCurrent:missing.length===0 && stale.length===0 && healthy && daily.date===today,
      mode:"research_only", decision:"PAS", realBettingEnabled:false};
  }
  if (typeof module !== "undefined" && module.exports) module.exports={summarize,files};
  if (typeof document === "undefined") return;
  const panel=document.createElement("section");
  panel.className="card";
  panel.id="weekendReadiness";
  const h=document.createElement("h2");
  h.textContent="Ortak Analiz V4.47 — Hafta sonu hazırlığı";
  const out=document.createElement("div");
  out.setAttribute("aria-live","polite");
  const button=document.createElement("button");
  button.type="button";
  button.textContent="Yayımlanan durumu yenile";
  panel.append(h,out,button);
  const target=document.getElementById("marketPanel");
  if(target) target.before(panel); else document.body.prepend(panel);
  function line(s,cls) {
    const p=document.createElement("p");
    p.textContent=s;
    if(cls) p.className=cls;
    out.append(p);
  }
  async function refresh() {
    button.disabled=true;
    out.replaceChildren();
    line("Raporlar kontrol ediliyor…");
    const data={};
    try {
      await Promise.all(files.map(async f=>{
        try {
          const response=await fetch("./"+f+"?ts="+Date.now(),{cache:"no-store"});
          if(!response.ok) return;
          const value=await response.json();
          if(value && typeof value==="object" && !Array.isArray(value)) data[f]=value;
        } catch (_) {}
      }));
      const r=summarize(data,Date.now());
      const val=x=>x===null?"Bilinmiyor":String(x);
      out.replaceChildren();
      line(r.dataCurrent?"Veri durumu: güncel":"Veri durumu: eksik, eski veya kalite kontrolü başarısız",r.dataCurrent?"good":"bad");
      line("28 Kasım: "+r.weekend["2026-11-28"]+" • 29 Kasım: "+r.weekend["2026-11-29"]+" (yayımlanmış liste; kesin fikstür sayısı değildir)");
      line("Fikstür kaynağı: "+val(r.leagues)+" lig • Bugün: "+val(r.fixtures));
      line(r.fixtureCoverageComplete?"Yapılandırılan kaynakların iki sezonu okundu.":"Fikstür kapsamı eksik veya henüz doğrulanmadı.","note");
      line("Oran raporu: "+val(r.events)+" etkinlik • Son bildirilen API kredisi: "+val(r.credits));
      line("İleriye dönük doğrulama: "+val(r.tested)+" / "+val(r.minimum)+" • Bekleyen: "+val(r.pending));
      line("Kalibrasyon: "+(r.calibrated?"Rapor onaylı":"Onay bekliyor"));
      line("Karar: PAS • Gerçek bahis kapalı. Geçmiş araştırma bağımsız ileriye dönük doğrulama değildir.","note");
      if(r.missing.length) line("Okunamayan: "+r.missing.join(", "),"muted");
      if(r.stale.length) line("30 dakikayı aşan veya zamanı belirsiz: "+r.stale.join(", "),"muted");
      line("Bu düğme yayımlanan raporları okur; yeni API çağrısı başlatmaz. Hafta sonu planlanan veri saatleri TSİ 08:00, 11:10, 14:10, 16:10, 18:00, 21:10. GitHub çalışması gecikebilir; 30 dakika sonrası arşiv olarak işaretlenir.","note");
      line("Kapsam tüm dünya ligleri veya basketbol değildir. Veri yoksa seçim oluşturulmaz.","note");
    } catch (_) {
      out.replaceChildren();
      line("Durum doğrulanamadı. PAS.","bad");
    } finally {button.disabled=false;}
  }
  button.onclick=refresh;
  refresh();
})();
