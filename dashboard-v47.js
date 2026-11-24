// Ortak Analiz V4.7 - Smart Dashboard
(function () {
  "use strict";

  const translations = {
    "Insufficient validated matches":
      "Yeterli sayıda doğrulanmış maç yok.",
    "Model not approved for live use":
      "Yeni model canlı kullanım için onaylanmadı.",
    "Live mode disabled":
      "Canlı kullanım kapalı.",
    "Data quality gate failed":
      "Veri kalite kontrolü başarısız.",
    "Data quality not healthy":
      "Veri kalitesi uygun değil.",
    "Data quality issues detected":
      "Veri kalitesinde sorun tespit edildi.",
    "Model validation errors":
      "Model doğrulamasında hata var."
  };

  function start() {
    if (document.getElementById("dashboardV47")) return;

    const panel = document.createElement("section");
    panel.id = "dashboardV47";
    panel.className = "card hero";

    panel.innerHTML = `
      <h2>🛡️ Akıllı Kontrol Paneli V4.7</h2>
      <div id="v47Status" class="big">PAS</div>
      <p id="v47Health" class="muted">Kontrol ediliyor...</p>

      <div class="stats">
        <div class="stat">
          <b id="v47Recorded">—</b>
          <small>Arşiv</small>
        </div>
        <div class="stat">
          <b id="v47Tested">—</b>
          <small>Doğrulanan</small>
        </div>
        <div class="stat">
          <b id="v47Pending">—</b>
          <small>Bekleyen</small>
        </div>
      </div>

      <p>Model doğrulama ilerlemesi</p>
      <progress id="v47Progress"
        max="500" value="0"
        style="width:100%;height:18px;accent-color:#7ee0b4">
      </progress>

      <p id="v47ProgressText" class="note">— / 500</p>
      <div id="v47Details"></div>

      <p id="v47Time" class="note"></p>

      <button id="v47Refresh" type="button"
        style="width:100%">
        Kontrol panelini yenile
      </button>

      <p class="note">
        Araştırma modu. Model başarısı henüz
        doğrulanmamıştır. Bahis önerisi değildir.
      </p>
    `;

    const target = document.getElementById("marketPanel");

    if (target) {
      target.before(panel);
    } else {
      document.body.prepend(panel);
    }

    const by = id => document.getElementById(id);

    function line(message, cls = "note") {
      const p = document.createElement("p");
      p.className = cls;
      p.textContent = message;
      by("v47Details").appendChild(p);
    }

    async function get(file) {
      const response = await fetch(
        "./" + file + "?ts=" + Date.now(),
        { cache: "no-store" }
      );

      if (!response.ok) throw Error(file);

      const data = await response.json();

      if (!data || typeof data !== "object"
          || Array.isArray(data)) {
        throw Error("Invalid report");
      }

      return data;
    }

    function fresh(data) {
      const age = Date.now() - Date.parse(data.updatedAt);
      return Number.isFinite(age)
        && age >= -60000
        && age <= 24 * 3600000;
    }

    function count(value) {
      return Number.isInteger(value) && value >= 0;
    }

    function score(value) {
      return Number.isFinite(value)
        ? value.toFixed(6) : "Henüz yok";
    }

    async function refresh() {
      const button = by("v47Refresh");
      button.disabled = true;

      by("v47Status").textContent = "PAS";
      by("v47Health").textContent = "Veriler kontrol ediliyor...";
      by("v47Details").replaceChildren();
      by("v47Time").textContent = "";
      by("v47Recorded").textContent = "—";
      by("v47Tested").textContent = "—";
      by("v47Pending").textContent = "—";
      by("v47Progress").value = 0;
      by("v47ProgressText").textContent = "— / 500";

      try {
        const [d, q, v] = await Promise.all([
          get("decision.json"),
          get("data_quality.json"),
          get("prospective_validation.json")
        ]);

        if (![d, q, v].every(fresh)) {
          throw Error("Eski veya geçersiz rapor");
        }

        const times = [d, q, v].map(
          x => Date.parse(x.updatedAt)
        );

        if (Math.max(...times) - Math.min(...times)
            > 600000) {
          throw Error("Rapor zamanları uyumsuz");
        }

        if (![v.recorded, v.tested, v.pending].every(count)
            || v.recorded !== v.tested + v.pending
            || d.testedMatches !== v.tested
            || q.settled !== v.tested
            || q.archiveRecords !== v.recorded
            || v.minimumMatches !== 500) {
          throw Error("Rapor sayıları uyumsuz");
        }

        by("v47Recorded").textContent = v.recorded;
        by("v47Tested").textContent = v.tested;
        by("v47Pending").textContent = v.pending;

        by("v47Progress").value = Math.min(v.tested, 500);

        const percent = Math.min(
          100, v.tested / 500 * 100
        ).toFixed(1);

        by("v47ProgressText").textContent =
          v.tested + " / 500 maç · %" + percent;

        const healthy =
          q.status === "healthy"
          && q.qualityGate === "PASS"
          && d.qualityGate === "PASS"
          && [q.errors, q.warnings, d.errors, v.errors]
            .every(x => Array.isArray(x) && x.length === 0);

        by("v47Health").textContent = healthy
          ? "Veri kalite kontrolü: PASS"
          : "Veri kalite kontrolü: PAS";

        by("v47Health").className =
          healthy ? "good" : "bad";

        line("Çalışma modu: Araştırma");
        line("Canlı model: Kapalı");
        line("Model: Ağırlıklı gol tahmin motoru");
        line("Test kategorisi: 2.5 Üst");

        line("Geçerli oran bulunan maç: "
          + (q.validOddsEvents ?? "Bilinmiyor"));

        line("Eski model Brier: " + score(v.scores?.old));
        line("Yeni model Brier: " + score(v.scores?.candidate));
        line("Referans Brier: " + score(v.scores?.baseline));

        line("PAS gerekçeleri:", "muted");

        for (const reason of d.reasons || []) {
          line("• " + (translations[reason] || reason));
        }

        for (const issue of [
          ...(q.errors || []),
          ...(q.warnings || []),
          ...(d.errors || []),
          ...(v.errors || [])
        ]) {
          line("• " + issue, "bad");
        }

        by("v47Time").textContent =
          "Son güncelleme: " +
          new Date(d.updatedAt).toLocaleString("tr-TR", {
            timeZone: "Europe/Istanbul"
          }) + " TSİ";

      } catch (error) {
        by("v47Health").textContent =
          "Raporlar doğrulanamadı";
        by("v47Health").className = "bad";

        line("Güncel ve tutarlı veri alınamadı. PAS.", "bad");
        line(error.message);
      } finally {
        button.disabled = false;
      }
    }

    by("v47Refresh").onclick = refresh;
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
