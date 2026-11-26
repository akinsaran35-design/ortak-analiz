(function () {
  "use strict";
  const files = ["daily.json","odds.json","data_quality.json","prospective_validation.json","unified_decision.json","matching.json"];
  const integer = n => Number.isInteger(n) && n >= 0 ? n : null;
  const fresh = (v, now) => {
    const t = Date.parse(v);
    return Number.isFinite(t) && now >= t && now-t <= 1800000;
  };
  const dateTR = t => new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Istanbul",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(t));
  function summarize(data, now) {
    const [daily, odds, quality, validation, decision, matching] = files.map(f=>data[f] || {});
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
    const sport="soccer_turkey_super_league";
    const trDiagnostic=Array.isArray(daily.leagueDiagnostics)?daily.leagueDiagnostics.find(x=>x?.league==="Türkiye Süper Lig"):null;
    const trQueried=Array.isArray(odds.queriedLeagues)&&odds.queriedLeagues.includes(sport);
    const trInactive=Array.isArray(odds.inactiveLeagues)&&odds.inactiveLeagues.includes(sport);
    const trEvents=trQueried&&Array.isArray(odds.events)?odds.events.filter(x=>x?.league===sport).length:null;
    const turkey={results:integer(trDiagnostic?.completedMatches),fixtureScope:trDiagnostic?.fixtureScope||null,oddsEvents:trEvents,
      oddsStatus:trInactive?"inactive":!trQueried?"unverified":!fresh(odds.updatedAt,now)?"stale":"snapshot"};
    const matched=integer(matching.matchedCount), unmatched=integer(matching.unmatchedCount);
    const mismatch=Array.isArray(matching.unmatched)?matching.unmatched.filter(x=>x?.reason==="date_mismatch"):[];
    const matchConsistent=matched!==null && unmatched!==null && matched+unmatched===integer(daily.candidateCount) && Array.isArray(matching.unmatched) && matching.unmatched.length===unmatched;
    const coverage={matched,unmatched,mismatch,consistent:matchConsistent,current:matchConsistent&&fresh(matching.updatedAt,now)&&fresh(odds.updatedAt,now)};
    const integrity=data["snapshot_integrity.json"]||{};
    const manifestCurrent=integrity.version==="4.81" && integrity.status==="PASS" && Array.isArray(integrity.errors) && integrity.errors.length===0 && fresh(integrity.updatedAt,now);
    const bound=f=>manifestCurrent && typeof data[f]?.updatedAt==="string" && integrity.reportTimestamps?.[f]===data[f].updatedAt && fresh(data[f].updatedAt,now);
    const calendar=data["fixture_reconciliation.json"]||{};
    const calendarCurrent=bound("fixture_reconciliation.json") && calendar.status==="research_only" && calendar.oddsFresh===true && fresh(calendar.updatedAt,now) && fresh(odds.updatedAt,now) && calendar.oddsUpdatedAt===odds.updatedAt && calendar.dailyUpdatedAt===daily.updatedAt && typeof daily.updatedAt==="string" && typeof odds.updatedAt==="string";
    const reconciliation={current:calendarCurrent,matched:calendarCurrent?integer(calendar.reconciledMatched):null,corrections:calendarCurrent&&Array.isArray(calendar.proposedCorrections)?calendar.proposedCorrections.length:null,dates:calendarCurrent?calendar.candidateCountsByDate||{}:{}};
    const evidence=data["archive_calendar_evidence_status.json"]||{};
    const replay=data["archive_calendar_result_replay.json"]||{};
    const results=data["multi_league_results.json"]||{};
    const evidenceCurrent=bound("archive_calendar_evidence_status.json") && evidence.version==="4.71" && evidence.mode==="research_only" && fresh(evidence.updatedAt,now);
    const counts=replay.counts||{};
    const replayTotal=Object.values(counts).reduce((sum,n)=>integer(n)===null?NaN:sum+n,0);
    const replayCurrent=evidenceCurrent && bound("archive_calendar_result_replay.json") && replay.version==="4.72" && replay.mode==="research_only" && fresh(replay.updatedAt,now) && Date.parse(replay.updatedAt)>=Date.parse(evidence.updatedAt) && replayTotal===integer(evidence.archiveIdentities) && Array.isArray(replay.rows) && replay.rows.length===replayTotal && Array.isArray(replay.sourceErrors);
    const resultCurrent=bound("multi_league_results.json") && results.version==="4.69" && fresh(results.updatedAt,now) && Array.isArray(results.approvedLeagues) && new Set(results.approvedLeagues).size===results.approvedLeagues.length && Array.isArray(results.groups);
    const archiveAudit={evidenceCurrent,replayCurrent,observations:evidenceCurrent?integer(evidence.observations):null,identities:evidenceCurrent?integer(evidence.archiveIdentities):null,awaiting:replayCurrent?integer(counts.awaiting_match??0):null,verified:replayCurrent?integer(counts.research_score_verified??0):null,errors:replayCurrent?replay.sourceErrors.length:null,leagues:resultCurrent?results.approvedLeagues.length:null,automaticVerified:resultCurrent?integer(results.automaticVerifiedCount):null};
    const integrityCurrent=manifestCurrent && files.every(bound);
    const provenance=data["score_provenance.json"]||{};
    const provenanceCurrent=bound("score_provenance.json") && provenance.version==="4.80" && provenance.mode==="research_only" && Array.isArray(provenance.rows) && Array.isArray(provenance.crossArchiveConflicts) && integer(provenance.feedDisagreements)!==null && provenance.settledArchiveRecords===provenance.rows.length;
    const scoreAudit={current:provenanceCurrent,unique:provenanceCurrent?integer(provenance.uniqueSettledMatches):null,corroborated:provenanceCurrent?new Set(provenance.rows.filter(x=>x.status==="currently_corroborated").map(x=>JSON.stringify([x.league,x.date,x.home,x.away]))).size:null,conflicts:provenanceCurrent?provenance.crossArchiveConflicts.length:null,feedDisagreements:provenanceCurrent?provenance.feedDisagreements:null,archiveMismatches:provenanceCurrent?provenance.rows.filter(x=>x.status==="source_conflict"||x.status==="invalid_score").length:null};
    const scoreHealthy=provenanceCurrent && scoreAudit.conflicts===0 && scoreAudit.feedDisagreements===0 && scoreAudit.archiveMismatches===0;
    return {today, weekend, missing, stale, healthy, turkey, coverage, reconciliation, archiveAudit, integrityCurrent, scoreAudit, dailyDate:daily.date || null,
      leagues:integer(daily.leaguesLoaded), fixtures:integer(daily.fixturesToday),
      fixtureCoverageComplete:daily.fixtureCoverageComplete===true && daily.upcomingCount===upcoming.length,
      events:integer(odds.eventCount), credits:integer(odds.remainingCredits),
      tested:integer(validation.tested), pending:integer(validation.pending),
      minimum:integer(validation.minimumMatches), calibrated:decision.modelCalibrated===true,
      dataCurrent:missing.length===0 && stale.length===0 && healthy && daily.date===today && integrityCurrent && scoreHealthy,
      mode:"research_only", decision:"PAS", realBettingEnabled:false};
  }
  if (typeof module !== "undefined" && module.exports) module.exports={summarize,files};
  if (typeof document === "undefined") return;
  const panel=document.createElement("section");
  panel.className="card";
  panel.id="weekendReadiness";
  const h=document.createElement("h2");
  h.textContent="Ortak Analiz V4.81 — Hafta sonu hazırlığı";
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
      await Promise.all([...files,"fixture_reconciliation.json","archive_calendar_evidence_status.json","archive_calendar_result_replay.json","multi_league_results.json","snapshot_integrity.json","score_provenance.json"].map(async f=>{
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
      line(r.integrityCurrent?"Yayın bütünlüğü: PASS — rapor zamanları eşleşiyor":"Yayın bütünlüğü: eksik, eski veya farklı raporlar","note");
      line("28 Kasım: "+r.weekend["2026-11-28"]+" • 29 Kasım: "+r.weekend["2026-11-29"]+" (yayımlanmış liste; kesin fikstür sayısı değildir)");
      line("Fikstür kaynağı: "+val(r.leagues)+" lig • Bugün: "+val(r.fixtures));
      line(r.fixtureCoverageComplete?"Yapılandırılan kaynakların iki sezonu okundu.":"Fikstür kapsamı eksik veya henüz doğrulanmadı.","note");
      line("Oran raporu: "+val(r.events)+" etkinlik • Son bildirilen API kredisi: "+val(r.credits));
      const cov=r.coverage;
      line("Eşleşen aday: "+val(cov.matched)+" • Eşleşmeyen: "+val(cov.unmatched)+" • "+(cov.current?"Güncel rapor":"Eski veya doğrulanmamış rapor"));
      if(cov.consistent && cov.mismatch.length){
        const detail=document.createElement("details");
        const summary=document.createElement("summary");
        summary.textContent="Tarih uyuşmazlığı: "+cov.mismatch.length+" maç (analiz dışında)";
        detail.append(summary);
        for(const m of cov.mismatch){
          const item=document.createElement("p");
          item.textContent=(m.match||"")+" · "+(m.league||"")+" · Fikstür: "+(m.date||"?")+" · Oran kaynağı: "+(Array.isArray(m.providerDates)?m.providerDates.join(", "):"?");
          detail.append(item);
        }
        out.append(detail);
      }
      const cal=r.reconciliation;
      if(cal.current){
        line("Tarih düzeltme araştırması: "+val(cal.matched)+" eşleşen aday • "+val(cal.corrections)+" önerilen düzeltme");
        line("Düzeltilmiş araştırma adayları: 28 Kasım "+val(integer(cal.dates["2026-11-28"]??0))+" • 29 Kasım "+val(integer(cal.dates["2026-11-29"]??0))+" (fikstür toplamı değildir)","note");
      } else line("Tarih düzeltme araştırması: güncel ve aynı veri setine ait rapor bekleniyor.","note");
      line("Araştırma tarihleri ana fikstür veya arşive uygulanmadı.","note");
      const audit=r.archiveAudit;
      line("Otomatik skor kontrolü: "+val(audit.leagues)+" yapılandırılmış lig • "+val(audit.automaticVerified)+" çift kaynaklı sonuç (güncel rapor).");
      if(audit.evidenceCurrent) line("Tarih kanıtı: "+val(audit.observations)+" gözlem • "+val(audit.identities)+" arşiv kaydı (aynı maç iki arşivde bulunabilir).");
      if(audit.replayCurrent) line("Tarih değişikliği araştırması: "+val(audit.awaiting)+" sonuç bekleyen kayıt • "+val(audit.verified)+" doğrulanan araştırma kaydı • "+val(audit.errors)+" kaynak hatası.");
      else line("Tarih değişikliği sonuç araştırması: güncel, tutarlı rapor bekleniyor.","note");
      line("Araştırma sonuçları ana performans hesabına dahil edilmez.","note");
      const sc=r.scoreAudit;
      if(sc.current){
        line("Skor kaynağı denetimi: "+val(sc.corroborated)+" / "+val(sc.unique)+" benzersiz maç iki kaynakla doğrulandı.");
        line("Kaynak çelişkisi: "+val(sc.feedDisagreements)+" • Arşivler arası çelişki: "+val(sc.conflicts)+" • Arşiv skor hatası: "+val(sc.archiveMismatches),sc.feedDisagreements||sc.conflicts||sc.archiveMismatches?"bad":"note");
      }else line("Skor kaynağı denetimi: güncel ve tutarlı rapor bekleniyor.","note");
      const tr=r.turkey;
      const labels={inactive:"Sağlayıcıda etkin değil",unverified:"Henüz doğrulanmadı",stale:"Eski veri",snapshot:"Güncel anlık görüntü"};
      line("Türkiye Süper Lig: "+val(tr.results)+" geçmiş sonuç • Oran kaydı: "+val(tr.oddsEvents)+" • "+labels[tr.oddsStatus]);
      line("Süper Lig fikstürü yalnızca sağlayıcının kapsadığı maçlarla sınırlıdır.","note");
      line("TFF 1. Lig: otomatik sonuç/oran entegrasyonu henüz yok.","note");
      const link=document.createElement("a");
      link.href="https://www.tff.org/default.aspx?pageID=142";
      link.textContent="TFF 1. Lig resmî fikstürü";
      link.target="_blank"; link.rel="noopener noreferrer";
      out.append(link);
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
