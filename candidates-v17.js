/* Ortak Analiz V1.7: read-only statistical candidates, never betting picks */
(function () {
  'use strict';
  const existing = document.getElementById('candidatePanel');
  if (existing) return;
  const anchor = document.getElementById('daily');
  if (!anchor) return;
  const section = document.createElement('section');
  section.className = 'card';
  section.id = 'candidatePanel';
  section.innerHTML = '<h2>📊 İstatistiksel maç adayları — V1.7</h2>' +
    '<p class="note">Yüzdeler kalibre edilmemiş model hesaplarıdır. Bahis önerisi değildir. Maç tarihleri ve saatleri ayrıca doğrulanmalıdır.</p>' +
    '<div class="row"><div><label for="candidateDate">Tarih</label><select id="candidateDate"><option value="all">Tüm tarihler</option></select></div>' +
    '<div><label for="candidateMarket">Sıralama</label><select id="candidateMarket"><option>1.5 Üst</option><option>2.5 Üst</option><option>KG Var</option></select></div></div>' +
    '<p class="muted" id="candidateInfo">Veriler yükleniyor…</p><div id="candidateRows"></div>';
  anchor.insertAdjacentElement('afterend', section);
  const dateSelect = section.querySelector('#candidateDate');
  const marketSelect = section.querySelector('#candidateMarket');
  const box = section.querySelector('#candidateRows');
  const info = section.querySelector('#candidateInfo');
  let report = null;
  const node = (tag, value, cls) => {
    const e = document.createElement(tag);
    if (value !== undefined) e.textContent = value;
    if (cls) e.className = cls;
    return e;
  };
  const localDate = (d) => {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(d);
    const v = Object.fromEntries(parts.map(p => [p.type, p.value]));
    return `${v.year}-${v.month}-${v.day}`;
  };
  function render() {
    box.replaceChildren();
    if (!report) return;
    const all = report.candidates;
    const market = marketSelect.value;
    const rows = all.filter(x => dateSelect.value === 'all' || x.date === dateSelect.value)
      .slice().sort((a, b) => (Number(b.markets?.[market]) || 0) - (Number(a.markets?.[market]) || 0));
    info.textContent = `${report.date} raporu · ${rows.length} gösterilen / ${report.candidateCount ?? all.length} toplam aday · Karar: ${report.decision}` +
      (report.date !== localDate(new Date()) ? ' · Eski tarihli rapor' : '');
    if (!rows.length) {
      box.append(node('p', 'Seçilen tarihte görüntülenebilir aday yok.', 'muted'));
      return;
    }
    for (const x of rows) {
      const card = node('div', undefined, 'pick');
      card.append(node('b', x.match || 'Maç adı yok'), node('div', `${x.date || ''} · ${x.league || ''}`, 'muted'));
      const grid = node('div', undefined, 'stats');
      grid.style.marginTop = '10px';
      for (const key of ['1.5 Üst', '2.5 Üst', 'KG Var']) {
        const cell = node('div', undefined, 'stat');
        cell.append(node('small', key), node('b', typeof x.markets?.[key] === 'number' ? `%${x.markets[key].toFixed(1)}` : '—'));
        grid.append(cell);
      }
      card.append(grid);
      const s = x.sample || {}, modes = x.sampleMode || {};
      const mode = v => v === 'venue_specific' ? 'iç/dış saha' : v === 'all_venues_fallback' ? 'genel saha' : 'belirsiz';
      card.append(node('p', `Örneklem: ev ${s.home ?? '—'} (${mode(modes.home)}), dep ${s.away ?? '—'} (${mode(modes.away)})`, 'note'));
      box.append(card);
    }
  }
  async function load() {
    try {
      const res = await fetch('./daily.json?ts=' + Date.now(), {cache: 'no-store'});
      if (!res.ok) throw Error('Rapor alınamadı');
      const data = await res.json();
      if (!data || !Array.isArray(data.candidates)) throw Error('Aday listesi bulunamadı');
      report = data;
      const dates = [...new Set(data.candidates.map(x => x.date).filter(Boolean))].sort();
      dateSelect.replaceChildren();
      const all = node('option', 'Tüm tarihler'); all.value = 'all'; dateSelect.append(all);
      for (const d of dates) { const opt = node('option', d); opt.value = d; dateSelect.append(opt); }
      const tomorrow = new Date(Date.now() + 86400000);
      const target = localDate(tomorrow);
      dateSelect.value = dates.includes(target) ? target : 'all';
      render();
    } catch (e) {
      report = null;
      box.replaceChildren();
      info.textContent = 'Adaylar yüklenemedi: ' + e.message;
    }
  }
  dateSelect.addEventListener('change', render);
  marketSelect.addEventListener('change', render);
  document.getElementById('remoteRefresh')?.addEventListener('click', load);
  load();
})();
