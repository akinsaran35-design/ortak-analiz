(function () {
  "use strict";

  const panel = document.createElement("section");
  panel.className = "card";
  panel.id = "unifiedDashboard";

  const heading = document.createElement("h2");
  heading.textContent = "Ortak Analiz V4.14";
  panel.appendChild(heading);

  const output = document.createElement("div");
  panel.appendChild(output);

  const button = document.createElement("button");
  button.textContent = "Raporu yenile";
  button.type = "button";
  panel.appendChild(button);

  document.body.appendChild(panel);

  const labels = {
    insufficient_validated_matches: "Yetersiz doğrulanmış maç",
    validation_not_approved: "Doğrulama onayı yok",
    model_not_calibrated: "Model kalibre edilmedi",
    real_betting_locked: "Gerçek bahis kilitli",
    no_eligible_candidates: "Uygun aday bulunamadı",
    low_probability: "Düşük olasılık",
    low_ev: "Düşük beklenen değer"
  };

  function line(value) {
    const p = document.createElement("p");
    p.textContent = value;
    output.appendChild(p);
  }

  async function refresh() {
    button.disabled = true;
    output.replaceChildren();
    line("Rapor okunuyor...");

    try {
      const response = await fetch(
        "./unified_decision.json?ts=" + Date.now(),
        { cache: "no-store" }
      );

      if (!response.ok) {
        throw new Error("Rapor bulunamadı");
      }

      const r = await response.json();

      if (
        !r ||
        r.version !== "4.13" ||
        !Array.isArray(r.reasons) ||
        !Array.isArray(r.errors) ||
        !Number.isFinite(r.testedMatches) ||
        !Number.isFinite(r.minimumValidatedMatches) ||
        r.minimumValidatedMatches <= 0
      ) {
        throw new Error("Geçersiz rapor");
      }

      output.replaceChildren();

      const age = Date.now() - Date.parse(r.updatedAt);
      const fresh = Number.isFinite(age) &&
        age >= 0 && age <= 1800000;

      line("Mod: Araştırma ve doğrulama");
      line("Karar: PAS");
      line("Gerçek bahis: KAPALI");
      line("Marketler: 1.5 Üst / 2.5 Üst / KG Var");
      line("Veri: " + (fresh ? "Güncel" : "Eski veya belirsiz"));
      line("Maksimum seçim: " + r.maximumSelections);
      line("Araştırma adayı: " + r.candidateCount);

      line(
        "Doğrulama: " + r.testedMatches +
        " / " + r.minimumValidatedMatches
      );

      const progress = document.createElement("progress");
      progress.max = r.minimumValidatedMatches;
      progress.value = Math.max(
        0,
        Math.min(r.testedMatches, progress.max)
      );
      progress.style.width = "100%";
      output.appendChild(progress);

      line(
        "Model kalibrasyonu: " +
        (r.modelCalibrated === true ? "Tamamlandı" : "Bekliyor")
      );

      line("Elenme nedenleri:");

      for (const [key, count] of Object.entries(r.rejected || {})) {
        line((labels[key] || key) + ": " + count);
      }

      line("Karar gerekçeleri:");

      for (const reason of r.reasons) {
        line(labels[reason] || reason);
      }

      line("Raporlanan hata: " + r.errors.length);

      line(
        "Rapor zamanı: " +
        new Date(r.updatedAt).toLocaleString("tr-TR", {
          timeZone: "Europe/Istanbul"
        })
      );

    } catch (error) {
      output.replaceChildren();
      line("Rapor alınamadı.");
      line("Karar: PAS");
      line("Gerçek bahis: KAPALI");
    } finally {
      button.disabled = false;
    }
  }

  button.addEventListener("click", refresh);
  refresh();
})();
