# Ortak Analiz PRO — geliştirme sırası

2026-11-28: V6.92 ana sürümde; model-piyasa kaynak bağı test/merge tamamlandı. ham fiyat hareketi doğrulaması test/merge tamamlandı. ek oran kapsamı paneli 8 iş akışında test/merge tamamlandı, canlı ek rapor henüz yok. kota korumalı ek market araştırma bağlantısı 7 iş akışında test/merge tamamlandı, yeni canlı kayıt henüz yok. otomatik ek hafta sonu kota koruması 7 iş akışında test/merge tamamlandı. öncelik bütçesi test/merge tamamlandı, 5 temel ve 7 ek çalışma, 1 ek çalışma bütçeye sığıyor. kota planı test/merge tamamlandı, 80 kredi kaydına karşı 128 planlanan toplam, 48 açık. ek market arşivi karantina test/merge tamamlandı. ek market pilotu veri bütünlüğü test/merge tamamlandı. eşit takvim kesimi denetimi test/merge tamamlandı, mevcut 24 eşleşmede kesim kaydı yok. yeni eski-motor kayıtları için üretim zamanı ve geçmiş veri kesim tarihi test/merge tamamlandı. eski tahmin kaynak arşivi denetimi test/merge tamamlandı. çift referanslı değerlendirme test/merge tamamlandı. 24 kalıcı eşleşme eski arşivle birebir uyumlu. tek kaynak kesintisinde skor revizyonu denetimi test/merge tamamlandı. 38 tahmin henüz doğrulamaya uygun değil, sonuç kaydı 0; 24 eşleşme kalıcı. oran kapsamı ekranı test/merge tamamlandı. oran zaman damgası ve geçersiz veri kontrolleri test/merge tamamlandı. kapsam denetimi 3 iş akışında başarılı. eski/yeni ortak maç paneli test/merge tamamlandı. ana lig araştırma paneli test/merge tamamlandı. %50/%50 ağırlık korundu. 24 eşleşmenin tümünde yeni model 24–48 saat daha geç üretildi. 24 eşleşmenin kalıcı kaydı doğrulandı. Tahmin zaman farkı medyanı yaklaşık 43 saat. 38 yeni tahminin kalıcı kaydı doğrulandı. Ana 9 ligde 39 gelecek maçın 38'i için 119 değişkenli girdi kontrolü başarılı; 1 kimlik uyuşmazlığı dışlandı. V6.65: 3292 geçmiş test maçı; 2.5 Üst/Alt sınıflandırmasında iyileşme sınırlı, KG Var/Yok için iyileşme kanıtlanmadı. Geçmiş test gerçek maç öncesi bağımsız doğrulama değildir.

## Ana öncelik — araştırmadan mevcut maç analiz motoruna

- [x] Ana 9 lig geçmiş test ve girdi kontrolü (V6.65–66).
- [x] Ana liglerde ayrı sabit model ve maç öncesi arşiv (V6.67, 38 kayıt doğrulandı).
- [x] Ana ligler için iki bağımsız kaynakla sonuç eşleştirmesi, çelişki karantinası ve otomatik ölçüm (V6.68 test/merge tamamlandı; gerçek sonuç bekleniyor).
- [x] Mevcut maç kartı motoruyla eşleştirilmiş karşılaştırma; maç öncesi zaman damgaları (V6.69, 24 kalıcı eşleşme doğrulandı).
- [ ] Kalibrasyon, Brier/log loss, tarih blokları, yeterli örneklem, lig ve market bazında güvenilirlik (V6.70 test/merge tamamlandı, sonuç bekleniyor; V6.71 zaman farkı duyarlılık analizi test/merge tamamlandı; V6.80 test/merge tamamlandı: aynı eşleşmiş sonuç kümesinde hem eski model hem Poisson temel modeli karşısında ayrı değerlendirme koşulu; V6.81 test/merge tamamlandı: kilitli eski tahmin alanlarının kaynak arşivle yeniden doğrulanması; V6.82 test/merge tamamlandı: yeni eski-motor tahminlerinde üretim aralığı ve tarihsel veri kesim tarihi kaydı, eski kayıtlar geriye dönük doldurulmaz; V6.83 test/merge tamamlandı: yeni eşleşmelerde kesim tarihini kilitle ve eşit takvim kesimli alt örneklemi ayrı raporla; aynı takvim kesimi aynı veri kaynağı değildir); bağımsız onay.
- [ ] Onaylanan modelleri yalnızca uygun lig/market için mevcut tasarımı koruyarak ana analiz motoruna bağla; eski tahmin arşivlerini değiştirme. Onaylanmayanlar araştırma olarak kalır.

- [x] Sabit %50/%50 ağırlık ile ayrı geçmiş ayarlama diliminde seçilen ortak ağırlığın karşılaştırması (V6.72 test/merge tamamlandı; eşik karşılanmadı); tekrar kullanılan test kümesi bağımsız onay sayılmaz, dondurulmuş model değiştirilmez.

- [x] Ana 9 lig araştırma performansını mevcut Performans ekranında ayrı göster (V6.73 test/merge); maç kartlarını değiştirme.

- [x] Eski/yeni ortak maç karşılaştırmasını Performans ekranında ayrı göster (V6.74 test/merge); tahmin zaman farkı ve doğrulanmış sonuç eksikliği açıkça belirtilir.

- [x] Mevcut oran arşivinin kapsamını ve güncelliğini ayrı göster (V6.77 test/merge); güncel kaynak bağı yoksa güncel sayı boş, KG Var sorgulanmadıysa açıkça belirtilir.

## API kesintisi ve yedek çalışma

- [ ] V6.93 PR: Türkiye fikstüründe güncel Odds API kaydı yoksa bağımsız ESPN fikstür kaynağı, mükerrer ve başlamış maç reddi, eksik kapsam açık; sıfır kredi ile ücretli sorgu yapılmadığı test edilir.
- [ ] Son geçerli oran arşivi ve açık kaynak durum raporu; eski oranlar güncel gösterilmez.
- [ ] Yedek mod arayüzü ve otomatik geri dönüş doğrulaması.
- [ ] Bağımsız tarihsel kaynak kesintileri ve tam iş akışı testi.

## Açık veri işleri

- [x] V6.63–64 ilk gözlenen oran geçmişi ve ekran bağlantısı; gerçek açılış olmadığı açıkça belirtilir.
- [ ] Oran geçmişi yeterli eşleşmiş gözlemle doğrulanmalı (V6.91 test/merge tamamlandı: hareket hesaplaması ham iki taraflı fiyatlardan yeniden türetilir; bozuk zaman, kimlik, fiyat ve hesap dışlanır; V6.92 test/merge tamamlandı: model-piyasa araştırma karşılaştırmasında kesin maç/rapor kimliği, mükerrer kaynak reddi ve ana kaynak 1.5 çizgisi kullanımı; farklı anlık görüntüler karıştırılmaz).
- [ ] 1.5 Üst ve KG Var kaynak kapsamı ve API kota kontrolü (V6.75 test/merge tamamlandı: mevcut veriyle kapsam ve güncellik denetimi, ilave API sorgusu yok; V6.84 test/merge tamamlandı: ek market pilotunda kesin maç kimliği, mükerrer kaynak/sonuç, sonlu oran ve bitiş zamanı denetimi; main üzerinde ek sorgu henüz açılmaz; V6.85 test/merge tamamlandı: arşivde maç kimliği ve aynı zaman damgası fiyat çelişkisi karantinası, hareket raporu karantina dışı; V6.86 test/merge tamamlandı: mevcut takvim ve 9 lig için ay sonuna kadar salt-okunur kota planı, 20 kredi rezervi, eski bakiye ile ek sorgu açılmaz; V6.87 test/merge tamamlandı: temel sabah/akşam ve ek hafta sonu sorgularını ayıran öncelik bütçesi, canlı takvim değişikliği yok; V6.88 test/merge tamamlandı: yalnızca ek hafta sonu cron çalışmasında canlı kredi başlığı ile temel sorgu rezervini koru, ertelemede mevcut zaman damgası korunur; V6.89 test/merge tamamlandı: ana dalda yalnızca temel zamanlanmış çalışmada ekstra market araştırma pilotu, canlı bakiyeden kalan bütün planlı temel oran sorguları ve 20 kredi rezervi düşülmeden ücretli ek maç sorgusu yok; V6.90 test/merge tamamlandı: ek raporu yayımla ve Performans ekranında son sorgu durumu, kapsam, kaynak bağını ayrı göster); eksik veriye sayı uydurma.
- [ ] İkinci sonuç kaynağı kapsamı ve gecikme nedenleri (V6.78 test/merge tamamlandı: lig bazlı eksik skor/kaynak hatası/karantina teşhisi, bozuk ESPN şemasına karşı güvenli bekleme; V6.79 test/merge tamamlandı: tek kaynak kesintisinde diğer kaynaktaki skor değişikliğini kaçırma, yeni sonuç için iki kaynak şartı korunur).
- [ ] Güncel veri yayınını, kaynak bütünlüğünü ve mevcut UI tasarımını koru (V6.76 test/merge tamamlandı: oran çekimi bitiş zaman damgası, mükerrer ve geçersiz oranları dışla; mevcut kota ve sorgu kapsamı korunur).

Kullanıcı soruları bu sırayı sıfırlamaz. Her adımda test sonucu ve ana sürüm kaydı doğrulanır. Nihai onay otomatik değildir. Bahis kazancı veya başarı garantisi verilmez.
