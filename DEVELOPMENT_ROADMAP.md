# Ortak Analiz PRO — geliştirme sırası

2026-11-28: V6.70 ana sürümde; 24 eşleşmenin kalıcı kaydı doğrulandı. Tahmin zaman farkı medyanı yaklaşık 43 saat. 38 yeni tahminin kalıcı kaydı doğrulandı. Ana 9 ligde 39 gelecek maçın 38'i için 119 değişkenli girdi kontrolü başarılı; 1 kimlik uyuşmazlığı dışlandı. V6.65: 3292 geçmiş test maçı; 2.5 Üst/Alt sınıflandırmasında iyileşme sınırlı, KG Var/Yok için iyileşme kanıtlanmadı. Geçmiş test gerçek maç öncesi bağımsız doğrulama değildir.

## Ana öncelik — araştırmadan mevcut maç analiz motoruna

- [x] Ana 9 lig geçmiş test ve girdi kontrolü (V6.65–66).
- [x] Ana liglerde ayrı sabit model ve maç öncesi arşiv (V6.67, 38 kayıt doğrulandı).
- [x] Ana ligler için iki bağımsız kaynakla sonuç eşleştirmesi, çelişki karantinası ve otomatik ölçüm (V6.68 test/merge tamamlandı; gerçek sonuç bekleniyor).
- [x] Mevcut maç kartı motoruyla eşleştirilmiş karşılaştırma; maç öncesi zaman damgaları (V6.69, 24 kalıcı eşleşme doğrulandı).
- [ ] Kalibrasyon, Brier/log loss, tarih blokları, yeterli örneklem, lig ve market bazında güvenilirlik (V6.70 test/merge tamamlandı, sonuç bekleniyor; V6.71 zaman farkı duyarlılık analizi PR); bağımsız onay.
- [ ] Onaylanan modelleri yalnızca uygun lig/market için mevcut tasarımı koruyarak ana analiz motoruna bağla; eski tahmin arşivlerini değiştirme. Onaylanmayanlar araştırma olarak kalır.

## Açık veri işleri

- [x] V6.63–64 ilk gözlenen oran geçmişi ve ekran bağlantısı; gerçek açılış olmadığı açıkça belirtilir.
- [ ] Oran geçmişi yeterli eşleşmiş gözlemle doğrulanmalı.
- [ ] 1.5 Üst ve KG Var kaynak kapsamı ve API kota kontrolü; eksik veriye sayı uydurma.
- [ ] İkinci sonuç kaynağı kapsamı ve gecikme nedenleri.
- [ ] Güncel veri yayınını, kaynak bütünlüğünü ve mevcut UI tasarımını koru.

Kullanıcı soruları bu sırayı sıfırlamaz. Her adımda test sonucu ve ana sürüm kaydı doğrulanır. Nihai onay otomatik değildir. Bahis kazancı veya başarı garantisi verilmez.
