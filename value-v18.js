/* Ortak Analiz V1.8 — manual odds comparison; not a betting recommendation. */
(function () {
  'use strict';
  const anchor = document.getElementById('candidatePanel');
  if (!anchor || document.getElementById('valuePanel')) return;
  const section = document.createElement('section');
  section.className = 'card';
  section.id = 'valuePanel';
  section.innerHTML = '<h2>🔎 Oran karşılaştırması — V1.8</h2>' +
    '<p class="muted">Oranlar otomatik doğrulanmaz. Kaynağını ve güncelliğini kendin kontrol et. Model yüzdeleri kalibre edilmediğinden hesaplanan fark gerçek bahis avantajı değildir.</p>' +
    '<label for="valueMatch">Maç</label><select id="valueMatch"></select>' +
    '<label for="valueMarket">Bahis pazarı</label><select id="valueMarket"><option>1.5 Üst</option><option>2.5 Üst</option><option>KG Var</option></select>' +
    '<label for="valueOdds">Kontrol ettiğin ondalık oran</label><input id="valueOdds" type="number" inputmode="decimal" min="1.01" max="1000" step="0.01" placeholder="Örn. 1.65">' +
    '<label for="valueSource">Oran kaynağı (isteğe bağlı)</label><input id="valueSource" type="text" maxlength="120" placeholder="Kaynak ve kontrol saati">' +
    '<button id="valueCalculate" type="button">Karşılaştır</button><div id="valueResult" class="item" aria-live="polite"></div>';
  anchor.insertAdjacentElement('afterend', section);
  const match = section.querySelector('#valueMatch');
  const market = section.querySelector('#valueMarket');
  const odds = section.querySelector('#valueOdds');
  const source = section.querySelector('#valueSource');
  const result = section.querySelector('#valueResult');
  let candidates = [];
  const addText = (tag, value) => { const el = document.createElement(tag); el.textContent = value; result.append(el); };
  async function load() {
    try {
      const res = await fetch('./daily.json?ts=' + Date.now(), {cache:'no-store'});
      if (!res.ok) throw Error('Günlük veri alınamadı');
      const report = await res.json();
      candidates = Array.isArray(report.candidates) ? report.candidates : [];
      match.replaceChildren();
      for (const [i, x] of candidates.entries()) {
        const option = document.createElement('option');
        option.value = String(i);
        option.textContent = `${x.date || ''} · ${x.match || 'Bilinmeyen maç'}`;
        match.append(option);
      }
      result.textContent = candidates.length ? 'Karşılaştırmak istediğin maçı ve kontrol ettiğin oranı seç.' : 'Raporda aday bulunamadı.';
    } catch (error) { result.textContent = 'Veri hatası: ' + error.message; }
  }
  section.querySelector('#valueCalculate').addEventListener('click', () => {
    result.replaceChildren();
    const item = candidates[Number(match.value)];
    const p = item?.markets?.[market.value];
    const o = Number(odds.value.replace(',', '.'));
    if (!item || typeof p !== 'number' || !Number.isFinite(o) || o <= 1 || o > 1000 || !odds.value.trim()) {
      addText('p', 'Geçerli bir maç, pazar ve 1.00 üzerinde oran gir.'); return;
    }
    const implied = 100 / o;
    const difference = p - implied;
    const breakEven = 100 / p;
    addText('p', `${item.match} · ${market.value}`);
    addText('p', `Model hesabı: %${p.toFixed(1)} · Oranın başabaş eşiği: %${implied.toFixed(1)}`);
    addText('p', `Matematiksel fark: ${difference >= 0 ? '+' : ''}${difference.toFixed(1)} yüzde puan · Modelin başabaş oranı: ${breakEven.toFixed(2)}`);
    addText('p', source.value.trim() ? `Kullanıcının belirttiği kaynak: ${source.value.trim()}` : 'Oran kaynağı belirtilmedi.');
    addText('p', 'Karar: PAS — model kalibre edilmedi, oran bağımsız doğrulanmadı. Pozitif fark bahis değeri kanıtı değildir.');
  });
  document.getElementById('remoteRefresh')?.addEventListener('click', load);
  load();
})();
