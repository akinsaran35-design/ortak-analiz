# Ortak Analiz PRO — geliştirme sırası

2026-11-28: V6.81 ana sürümde; 24/24 eski kaynak tahmini testte doğrulandı. çift referanslı değerlendirme test/merge tamamlandı. 24 kalıcı eşleşme eski arşivle birebir uyumlu. tek kaynak kesintisinde skor revizyonu denetimi test/merge tamamlandı. 38 tahmin henüz doğrulamaya uygun değil, sonuç kaydı 0; 24 eşleşme kalıcı. oran kapsamı ekranı test/merge tamamlandı. oran zaman damgası ve geçersiz veri kontrolleri test/merge tamamlandı. kapsam denetimi 3 iş akışında başarılı. eski/yeni ortak maç paneli test/merge tamamlandı. ana lig araştırma paneli test/merge tamamlandı. %50/%50 ağırlık korundu. 24 eşleşmenin tümünde yeni model 24–48 saat daha geç üretildi. 24 eşleşmenin kalıcı kaydı doğrulandı. Tahmin zaman farkı medyanı yaklaşık 43 saat. 38 yeni tahminin kalıcı kaydı doğrulandı. Ana 9 ligde 39 gelecek maçın 38'i için 119 değişkenli girdi kontrolü başarılı; 1 kimlik uyuşmazlığı dışlandı. V6.65: 3292 geçmiş test maçı; 2.5 Üst/Alt sınıflandırmasında iyileşme sınırlı, KG Var/Yok için iyileşme kanıtlanmadı. Geçmiş test gerçek maç öncesi bağımsız doğrulama değildir.

## Ana öncelik — araştırmadan mevcut maç analiz motoruna

- [x] Ana 9 lig geçmiş test ve girdi kontrolü (V6.65–66).
- [x] Ana liglerde ayrı sabit model ve maç öncesi arşiv (V6.67, 38 kayıt doğrulandı).
- [x] Ana ligler için iki bağımsız kaynakla sonuç eşleştirmesi, çelişki karantinası ve otomatik ölçüm (V6.68 test/merge tamamlandı; gerçek sonuç bekleniyor).
- [x] Mevcut maç kartı motoruyla eşleştirilmiş karşılaştırma; maç öncesi zaman damgaları (V6.69, 24 kalıcı eşleşme doğrulandı).
- [ ] Kalibrasyon, Brier/log loss, tarih blokları, yeterli örneklem, lig ve market bazında güvenilirlik (V6.70 test/merge tamamlandı, sonuç bekleniyor; V6.71 zaman farkı duyarlılık analizi test/merge tamamlandı; V6.80 test/merge tamamlandı: aynı eşleşmiş sonuç kümesinde hem eski model hem Poisson temel modeli karşısında ayrı değerlendirme koşulu; V6.81 test/merge tamamlandı: kilitli eski tahmin alanlarının kaynak arşivle yeniden doğrulanması); bağımsız onay.
- [ ] Onaylanan modelleri yalnızca uygun lig/market için mevcut tasarımı koruyarak ana analiz motoruna bağla; eski tahmin arşivlerini değiştirme. Onaylanmayanlar araştırma olarak kalır.

- [x] Sabit %50/%50 ağırlık ile ayrı geçmiş ayarlama diliminde seçilen ortak ağırlığın karşılaştırması (V6.72 test/merge tamamlandı; eşik karşılanmadı); tekrar kullanılan test kümesi bağımsız onay sayılmaz, dondurulmuş model değiştirilmez.

- [x] Ana 9 lig araştırma performansını mevcut Performans ekranında ayrı göster (V6.73 test/merge); maç kartlarını değiştirme.

- [x] Eski/yeni ortak maç karşılaştırmasını Performans ekranında ayrı göster (V6.74 test/merge); tahmin zaman farkı ve doğrulanmış sonuç eksikliği açıkça belirtilir.

- [x] Mevcut oran arşivinin kapsamını ve güncelliğini ayrı göster (V6.77 test/merge); güncel kaynak bağı yoksa güncel sayı boş, KG Var sorgulanmadıysa açıkça belirtilir.

- [ ] V6.82 PR: dondurulmuş modelin eğitim verisi parmak izini her yeni çalıştırmada yeniden kontrol et; veri değişirse tahmin üretimini durdur, mevcut model/arşiv değiştirilmez.

## Açık veri işleri

- [x] V6.63–64 ilk gözlenen oran geçmişi ve ekran bağlantısı; gerçek açılış olmadığı açıkça belirtilir.
- [ ] Oran geçmişi yeterli eşleşmiş gözlemle doğrulanmalı.
- [ ] 1.5 Üst ve KG Var kaynak kapsamı ve API kota kontrolü (V6.75 test/merge tamamlandı: mevcut veriyle kapsam ve güncellik denetimi, ilave API sorgusu yok); eksik veriye sayı uydurma.
- [ ] İkinci sonuç kaynağı kapsamı ve gecikme nedenleri (V6.78 test/merge tamamlandı: lig bazlı eksik skor/kaynak hatası/karantina teşhisi, bozuk ESPN şemasına karşı güvenli bekleme; V6.79 test/merge tamamlandı: tek kaynak kesintisinde diğer kaynaktaki skor değişikliğini kaçırma, yeni sonuç için iki kaynak şartı korunur).
- [ ] Güncel veri yayınını, kaynak bütünlüğünü ve mevcut UI tasarımını koru (V6.76 test/merge tamamlandı: oran çekimi bitiş zaman damgası, mükerrer ve geçersiz oranları dışla; mevcut kota ve sorgu kapsamı korunur).

Kullanıcı soruları bu sırayı sıfırlamaz. Her adımda test sonucu ve ana sürüm kaydı doğrulanır. Nihai onay otomatik değildir. Bahis kazancı veya başarı garantisi verilmez.
