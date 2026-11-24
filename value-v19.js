/* Ortak Analiz V1.9 */
(function () {
  'use strict';
  const anchor = document.getElementById('valuePanel');
  if (!anchor || document.getElementById('valuePanel19')) return;

  const section = document.createElement('section');
  section.className = 'card';
  section.id = 'valuePanel19';
  section.innerHTML = `
    <h2>Üçlü oran karşılaştırması — V1.9</h2>
    <p class="muted">Kalibre edilmemiş model. Sonuçlar yalnızca matematiksel karşılaştırmadır.</p>
    <label>Maç</label>
    <select id="v19match"></select>
    <label>1.5 Üst oranı</label>
    <input id="v19o1" inputmode="decimal" placeholder="1.22">
    <label>2.5 Üst oranı</label>
    <input id="v19o2" inputmode="decimal" placeholder="1.68">
    <label>KG Var oranı</label>
    <input id="v19o3" inputmode="decimal" placeholder="1.53">
    <button id="v19calc" type="button">Üç oranı karşılaştır</button>
    <div id="v19result" aria-live="polite"></div>
  `;
  anchor.insertAdjacentElement('afterend', section);

  const get = id => document.getElementById(id);
  const select = get('v19match');
  const result = get('v19result');
  let candidates = [];

  async function load() {
    candidates = [];
    select.replaceChildren();
    result.textContent = 'Veriler yükleniyor...';
    try {
      const response = await fetch('./daily.json?ts=' + Date.now(), {cache:'no-store'});
      if (!response.ok) throw Error('Veri alınamadı');
      const report = await response.json();
      candidates = Array.isArray(report.candidates) ? report.candidates : [];
      candidates.forEach((item, i) => {
        const option = document.createElement('option');
        option.value = String(i);
        option.textContent = item.date + ' - ' + item.match;
        select.appendChild(option);
      });
      result.textContent = candidates.length ? 'Oranları gir.' : 'Maç adayı yok.';
    } catch (error) {
      result.textContent = 'Veri yükleme hatası.';
    }
  }

  get('v19calc').onclick = function () {
    result.replaceChildren();
    const item = candidates[Number(select.value)];
    if (!item) {
      result.textContent = 'Geçerli maç bulunamadı.';
      return;
    }

    const markets = ['1.5 Üst', '2.5 Üst', 'KG Var'];

    for (let i = 0; i < markets.length; i++) {
      const raw = get('v19o' + (i + 1)).value.trim();
      const odds = Number(raw.replace(',', '.'));
      const p = item.markets?.[markets[i]];
      if (!raw || !Number.isFinite(odds) || odds <= 1 || odds > 1000 || !Number.isFinite(p) || p < 0 || p > 100) {
        result.textContent = 'Üç geçerli oran ve model verisi gerekli.';
        return;
      }
      const line = document.createElement('p');
      line.textContent = markets[i] +
        ' | Model: %' + p.toFixed(1) +
        ' | Başabaş: %' + (100 / odds).toFixed(1) +
        ' | Fark: ' + (p - 100 / odds).toFixed(1) + ' puan';
      result.appendChild(line);
    }

    const note = document.createElement('p');
    note.textContent = 'Karar: PAS — Model kalibre edilmedi, oranlar doğrulanmadı.';
    result.appendChild(note);
  };

  select.addEventListener('change', () => {
    result.textContent = 'Yeni maçın oranlarını gir.';
    ['v19o1','v19o2','v19o3'].forEach(id => get(id).value = '');
  });

  get('remoteRefresh')?.addEventListener('click', load);
  load();
})();
