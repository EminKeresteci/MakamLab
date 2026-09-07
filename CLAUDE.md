# MakamLab

Türk makam müziği için nazariyat (kuram) motoru, klavye çalıcı ve analiz araçları.

## Amaç

Makamları bilgisayar ortamında modellemek, çalmak ve analiz etmek. Temel hedefler:
- 53 eşit tampere (53-TET) sistemini doğru uygulamak
- Makam perdelerini, çeşnilerini ve geçkilerini hesaplamak
- Gerçek zamanlı MIDI çalıcı (klavye.py)
- Taksim algoritması geliştirmek

## Dosya Yapısı

| Dosya | Amaç |
|---|---|
| `nazariyat.py` | Ana kütüphane: `Nazariyat`, `Makam`, `seslendir`, `nota_baslat` |
| `klavye.py` | PySide6 GUI klavye çalıcı |
| `dizi.txt` | Makam listesi (alt çeşni, üst çeşni, durak, yeden, güçlü, seyir) |
| `perde.txt` | Perde adları ve koma/oktav değerleri |
| `çeşni.txt` | Çeşni aralık şifreleri |
| `fft.py` | FFT / frekans analizi |
| `makam_analiz.py` | Makam tanıma |
| `tesbit.py`, `tesbit-v2.py` | Perde/nota tespiti |
| `waterfall.py` | Spektrogram görselleştirme |

## Temel Kavramlar

### 53-TET (53 Eşit Tampere)
Türk makam müziğinde oktav 53 eşit adıma bölünür. 1 koma ≈ 22.6 sent (12/53 yarım ton).
```python
koma_kesir = koma * (12 / 53)
midi = 55 + degerler[perde] + oktav * 12 + koma_kesir
```

### Perde Formatı
`"esas,koma,oktav"` — örn. `"sol,-1,0"` (Rast perdesi), `"la,0,1"` (Neva)

**Esas notalar (degerler):**
`sol=0, la=2, si=4, do=5, re=7, mi=9, fa=10` (semitone offset from G3=MIDI 55)

**Mutlak koma (saf 53-TET):**
`sol=0, la=9, si=18, do=22, re=31, mi=40, fa=44`

`Nazariyat.mutlak_koma(perde)` = `koma_degerleri[esas] + koma + oktav*53`.
Aynı perdenin iki yazımı bu değerde birleşir: `la,8,0` ile `si,-1,0` ikisi de
17 — ikisi de segâh. `perde.txt` arızalı perdeyi alttaki naturalden yukarı
adlandırır (`la,8`), `çeşni.txt` ise üstteki naturalden aşağı üretir (`si,-1`).
Bu yüzden `perdeden_isme` metin eşleşmesi tutmazsa `komadan_isme` indeksine
düşer. Bu olmadan makamlarda kullanılan 38 perdenin 14'ü adsız kalıyordu.

Not: `seslendir()` hâlâ naturalleri 12-TET, komaları 53-TET hesaplıyor
(`degerler` + `koma*(12/53)`), yani icrada iki yazım 4 sent ayrışır. Bkz. TODO.

### Koma Şifreleri (çeşni.txt)
`b=4, s=5, m=6, k=8, t=9, a=12` koma aralıkları

Dörtlü 22, beşli 31 koma etmeli. İstisna: `saba,4:KSS` = 18 koma, otorite
"eksik bir dörtlüdür" der, kasten öyle. `nişabur,5:MTST` = 29 koma ve `m`
(6 koma) AEU'da hiç yok — kırık, ama hiçbir makamda kullanılmıyor.

### Makam Yapısı
Her makam: alt çeşni (duraktan güçlüye) + üst çeşni (güçlüden tize).

`dizi.txt` sütunları: `isim:alt:üst:durak:yeden:seyir:güçlü:tiz`

**Demirlenmiş çeşni (`@derece`).** `üst` hücresi `+` ile birden fazla çeşni
alır; her biri `@derece` ile hangi dereceye oturduğunu söyler (1'den sayılır,
perde adı değil derece indisi — makam başka duraka transpoze edilirse
bozulmasın). `@` yoksa çeşni bir öncekinin tepesinden zincirlenir, yani
mevcut davranış.

```
Saba:saba,4:hicaz,5@3+hicaz,4@7:dügah:rast:çıkıcı-inici:çargah:şehnaz
```

Bu Sabâ için zaruri: TDV "sabâ dörtlüsü + **çargâhta** zirgüleli hicaz
dizisi" diyor, çargâh ise Sabâ'nın 3'üncü derecesi (güçlüsü). Zincirleme
kuralı üst çeşniyi alt çeşninin tepesinden (hicaz) başlattığı için 5. ve
7. dereceler yanlış çıkıyordu (`dik neva` ve `mahur`; doğrusu `dik hisar`
ve `gerdaniye`).

**`tiz` sütunu** dizinin nerede kapandığını söyler; boşsa perde listesi
kırpılmaz. Sabâ'da `şehnaz`, zira durak dügâh ile tiz durak şehnaz arası
tam sekizli değildir (49 koma) — otorite de böyle diyor, kusur değil.

`aralıklardan_perdelere(durak, *çeşniler, tiz=None)` her çeşniyi kendi
demirinden zincirler, perdeleri `mutlak_koma`ya göre tekilleyip sıralar,
`tiz`de kırpar. `Makam.aralıklar` artık `alt + üst` birleştirmesi değil,
sıralı perde listesinden `perdelerden_aralıklara` ile türetilir.

## Bağımlılıklar

```
scamp        # MIDI/ses motoru (FluidSynth arka uç)
PySide6      # GUI
pandas       # dizi/perde/çeşni CSV okuma
numpy        # sayısal hesaplar (fft.py vb.)
```

## klavye.py Klavye Düzeni

**İzomorfik ızgara: satır = oktav, sütun = derece.**

```
1 2 3 4 5 6 7 8 9 0    ← +2 oktav
Q W E R T Y U I O P    ← +1 oktav
A S D F G H J K L      ← ana oktav (A = YEDEN, S = DURAK, her makamda sabit)
Z X C V B N M Ö Ç      ← −1 oktav
```

`IZGARA_SATIRLARI` sabitinde `(harfler, oktav_ofseti)` çiftleri tutulur. Her tuş
kendi `oktav` ve sütun (`derece`) bilgisini taşır. `_sutun_perdesi()`:

```python
cetvel = makam.perdeler[:-1]          # bir çevrimlik derece dizisi, [0] = durak
cevrim = mutlak_koma(perdeler[-1]) - mutlak_koma(perdeler[0])   # koma cinsinden
n = len(cetvel)                       # tipik olarak 7
if sutun == 0:                        # sütun 0 makamın kendi yedeni
    perde = koma_ekle(makam.yeden, oktav * cevrim)
else:
    d = sutun - DERECE_OFSET          # DERECE_OFSET = 1
    perde = koma_ekle(cetvel[d % n], (oktav + d // n) * cevrim)
```

Satır kaydırması oktav alanına değil **komaya** bağlı. Makamların 36'sında
`cevrim` 53'tür, ama Sabâ ve Bestenigâr'da 49 — oktav alanını artırmak bu
ikisinde satırları 4 koma şaşırtırdı.

Sütun 0'a `makam.yeden` konur, derece dizisinin bir alt basamağı (`derece = -1`)
konmaz: 38 makamın 13'ünde bu ikisi ayrışıyor (Nihavend, Sabâ, Mahur, Hüzzam,
Segâh, Acem, Bestenigâr, Şedaraban, Zinciran, Ferahnâk, Evîç, Bûselik,
Zirgüleli Hicaz). Yeden bir derece basamağı değil, muayyen bir perdedir.

Bunun iki neticesi:
- **Sütun hizası birebir**: Q sütun *c* = A sütun *c* + 1 oktav. Oktav atlaması aynı
  parmağın bir satır yukarısı.
- **Satır oktavdan uzun** (9-10 tuş, 7 derece), artan tuşlar üst oktavın ilk
  derecelerine taşar; satır değiştirmeden kısa geçiş yapılabilir.

- Normal modda `NORMAL_OKTAVLAR` satırları gösterilir (Q ve A satırı, 19 tuş)
- F11 tam ekranda 4 satır, 38 tuş
- Tuş boyutu `_tus_olcusu()` ile pencereye göre ölçeklenir; tam ekranda `MAX_TUS_W`
  üst sınırı uygulanmaz

### Kısayollar
- `F11`: Tam ekran / normal geçiş
- `<` / `>`: Bütün ızgarayı bir oktav aşağı / yukarı kaydırır (±3 ile sınırlı)
- `Shift` (basılı): bütün perdeleri **+5 koma**
- `Ctrl` (basılı): bütün perdeleri **−5 koma**
- `Alt+M`: Makam dropdown
- `Alt+I`: Saz dropdown

Ctrl musikî kaydırmasına ayrıldığı için dropdown kısayolları `Alt`'a taşındı;
aksi halde `Ctrl+M` ve `Ctrl+I` iki notayı yutuyordu.

### Koma kaydırma (`KOMA_ADIM = 5`)
Modifier basılı tutulduğu sürece geçerli; bırakınca sıfırlanır (`focusOutEvent`
de sıfırlar). Tuşta iki perde tutulur: `taban_perde` makamın verdiği perde,
`tam_perde = komayla(taban_perde, koma_kaydirma)` fiilen çalınan perde.
Çalmakta olan nota kaydırmadan etkilenmez — perde basıldığı anda dondurulur.

Ekranda üç yerden görünür:
- Legendada dolgulu `KOMA +5` rozeti (tema `koma` rengi)
- Her tuşun nota yazısı `Sol +5` şekline girer ve `koma` rengine döner
- Tuş border'ı `koma` rengine döner (durak/güçlü dolgusu korunur)

Not: `perde.txt` yalnız yukarı arızalı perdeleri adlandırdığı için `+5`'te
gerçek perde adı çıkar (rast→zirgûle, çargâh→hicaz, neva→hisar), `−5`'te
çoğunlukla ad bulunmaz ve nota adına düşülür.

### Görsel kodlama
- Yeşil border/metin = Yeden perdesi
- Mavi border/metin = Durak perdesi
- Turuncu border/metin = Güçlü perdesi
- Mor (tema `koma`) border/metin = koma kaydırması etkin
- Tuşa basıldığında nota yazısı büyüyüp beyazlaşır

Roller `perde_base()` ile (oktav yok sayılarak) eşleştiği için her oktavda
işaretlenir; sütun 0 dışındaki bir tuş da yedene denk gelirse yeşil yanar.

### Bilinen veri kusuru
`dizi.txt:14` — Nihavend'in yedeni `rast` yazılmış, durağı da `rast`. Bu yüzden
A ile S aynı perdeye düşen tek makam odur; yeden `ırak` olmalı.

### Tema sistemi
`TEMALAR` sözlüğünde tanımlı: Celik, Kehribar, Lacivert, Krem.
Her tema: pencere, tuş, hover, basılı, durak, güçlü, koma renkleri.

## klavye.py Enstrümanlar

| Kategori | İsim | GM MIDI |
|---|---|---|
| Tuşlu | Piyano, Rhodes, Klavsen, Org | 0, 4, 6, 19 |
| Mızraplı | Ud, Tanbur, Kanun, Cümbüş, Harp | 24, 104, 15, 105, 46 |
| Yaylı | Keman, Viyola, Kemençe | 40, 41, 110 |
| Nefesli | Ney, Flüt, Mıskal, Zurna | 77, 73, 75, 68 |

Not: Ud=24 (Nylon Guitar), Tanbur=104 (Sitar), Kanun=15 (Dulcimer), Kemençe=110 (Fiddle), Ney=77 (Shakuhachi), Mıskal=75 (Pan Flute), Zurna=68 (Oboe) en yakın GM karşılıkları.


### Temel Perde (Pitch Base) İnceleme
Mevcut taban: `midi = 55 + ...` → MIDI 55 = G3 = 196 Hz. Bu bazı makamlar için alçak gelebilir.

- [ ] MIDI 67 (G4 = 392 Hz) ile karşılaştırmalı test
- [ ] UI'a transpozisyon kontrolü: +/- oktav ve +/- koma butonları
- [ ] `seslendir()` ve `nota_baslat()`'a `transpoze` parametresi ekle

### Makam Listesi Sıralaması
`dizi.txt`'te makamlar alfabetik; daha kullanışlı bir sıra olabilir.

- [ ] Yaygın kullanılan makamları başa al (Rast, Uşşak, Hicaz, Segah, Hüzzam…)
- [ ] Seyir tipine göre grupla veya kullanıcı favorileri öne çıkar

### Oktav Navigasyonu
Tam ekranda 38 tuş sabit; bazı makamlar daha geniş aralık gerektirebilir.

- [x] Klavyeyi oktav kaydıran `<` / `>` kısayolu
- [x] Aktif oktav kaydırmasını legendada göster (`lbl_oktav_leg`)

### Makam Bilgi Paneli
Seçilen makamın teorik özeti anlık görünür olmalı.

- [ ] Kenar panel veya tooltip: durak, güçlü, yeden, seyir, arıza listesi
- [ ] Makam aralık şemasını görsel olarak göster (perde → koma basamakları)

### Taksim Algoritması
Şu an `taksim()` rastgele perde geçişi yapıyor; seyir mantığı yok.

- [ ] Seyir tipine göre perde geçiş ağırlıkları (çıkıcı / inici / çıkıcı-inici)
- [ ] Güçlü perdede duraksamayı modelle (uzun nota / tekrar)
- [ ] Makam özelinde atlamayı tercih eden davranış (ör. Rast atlamayı sever)
- [ ] LSTM / Markov zinciri ile geçiş olasılıklarını öğren (`Makam.pth` modeli)
- [ ] Taksim çıktısını MIDI dosyasına kaydet

### Nota Yazıp Çalma
Ayrı bir uygulama / sekme: metin olarak yazılan nota dizisini çal.

- [ ] Basit sözdizimi: `rast neva çargah neva rast` → `seslendir()` zinciri
- [ ] Tempo ve süre kontrolü
- [ ] Kaydedip tekrar yükleme

## Önemli Notlar

- `seslendir()` ve `nota_baslat()` thread-safe değil; her çağrı ayrı thread'de çalışır
- `Nazariyat()` nesnesi pahalıdır (CSV yükler), paylaşılarak kullanılmalı
- `scamp.Session` bir kez başlatılmalı (`daimi_meclis`), her nota için yenilenmemeli
