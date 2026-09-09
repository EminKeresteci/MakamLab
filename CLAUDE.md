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

Bestenigâr da demirlenmiş: `irak,4:saba,4@3+hicaz,5@5`, durak ırak, güçlü
çargâh, yeden acem aşiran, tiz **evîç**. Otorite Bestenigâr'a tiz durak
vermez (mürekkeb makam, sekizliyle değil bileşenleri ve kararıyla tanımlı);
evîç bir çıkarım — ırak'ın oktavı olduğu için dizi 53 komaya kapanıyor ve
aralıklar `stkssasb` = 5,9,8,5,5,12,5,4 hepsi meşru AEU aralığı. Bedeli
şehnazın (58) ızgaraya düşmemesi; gerdaniye tuşuna Shift ile erişiliyor.

**Aynı dereceye iki çeşni.** Müstear iki çeşniyi *birleştirir*, zincirlemez:
`mustear,5+segah,5@1`. TDV Müstear'ı "segâh seyrine müstear çeşnisinin arada
bir katılması" diye tarif ettiği için dizide hem çargâh (segâh beşlisinden)
hem nim hicaz (müstear beşlisinden) bulunur — 8 dereceli bir dizi. Müstear'ı
Segâh'tan ayıran perde budur; alt çeşniyi yalnız `segah,5` yapmak dizisini
Segâh'la birebir aynı kılardı.

`aralıklardan_perdelere(durak, *çeşniler, tiz=None)` her çeşniyi kendi
demirinden zincirler, perdeleri **her çeşniden sonra** `mutlak_koma`ya göre
tekilleyip sıralar, `tiz`de kırpar. Sıralamanın her adımda yapılması şart:
`@derece` artan listeye göre sayar, ekleme sırasına göre değil — birleştiren
çeşnilerde ikisi ayrışıyor. `Makam.aralıklar` artık `alt + üst`
birleştirmesi değil, sıralı perde listesinden `perdelerden_aralıklara` ile
türetilir.

### Adı olmayan perdeler
`perde.txt` 53 konumun hepsini adlandırmaz, o yüzden 12 komalık artık ikili
bazı transpozisyonlarda adlı perdeye denk gelmez. Üç yerde çıkıyor:
`la,3,1` (Segâh, Hüzzam, Evîç, Ferahnâk, Müstear), `la,3,0` ve `fa,-1,0`
(Evcârâ — hicaz dizisinin ırak'a göçürülmesinden). Perdenin *sesi* doğru,
yalnız adı yok; tuşta nota adına düşülür. AEU'nun kendi çelişkisi, bkz. TODO.

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
A S D F G H J K L Ş İ  ← ana oktav (A = YEDEN, S = DURAK, her makamda sabit)
Z X C V B N M Ö Ç .    ← −1 oktav
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
konmaz: 40 makamın 12'sinde bu ikisi ayrışıyor (Nihavend, Segâh, Hüzzam, Sabâ,
Mahur, Ferahnâk, Zinciran, Acem, Evîç, Hisar, Müstear, Evcârâ). Yeden bir derece
basamağı değil, muayyen bir perdedir.

Bunun iki neticesi:
- **Sütun hizası birebir**: Q sütun *c* = A sütun *c* + 1 oktav. Oktav atlaması aynı
  parmağın bir satır yukarısı.
- **Satır oktavdan uzun** (10-11 tuş, 7 derece), artan tuşlar üst oktavın ilk
  derecelerine taşar; satır değiştirmeden kısa geçiş yapılabilir.

**Türkçe Q'ya has tuşlar.** Ana satır `L`'den sonra `Ş` ve `İ` ile, alt satır
`Ç`'den sonra `.` ile devam eder. Tuşlar `tus_sozlugu`'nda `ord(harf)` ile
adreslenir, ama iki tuşta bu tutmaz ve `SANAL_TUS` sözlüğü sanal tuş koduna
(`nativeVirtualKey`) düşer:

| Tuş | Sorun | Anahtar |
|---|---|---|
| `Ş` | Qt `0x15E` verir, `Qt.Key` üyesi değil | VK `0xBA` |
| `İ` | `'i'`nin Unicode büyüğü `I`, yani üst satırdaki `ı` tuşuyla aynı kod | VK `0xDE` |

`.` tuşunda sorun yok: Türkçe Q'da VK `0xBE`, karakteri `.`, Qt `Key_Period`
(`0x2E`) verir. `Ö` (`0xD6`) ve `Ç` (`0xC7`) Latin-1'de oldukları için zaten
`ord` ile tutuyordu. `_tus_bul()` evvela sanal kodu, sonra `key()`'i dener.

- Normal (başlangıç) modda yalnız ana satır gösterilir (`NORMAL_OKTAVLAR = (0,)`,
  11 tuş). Pencere açılışta `IZGARA_SUTUN * (MAX_TUS_W + TUS_ARALIK) + 40` genişliğe
  kurulur (1470 px), tuşlar 124x142'ye çıkar
- F11 tam ekranda 4 satır, 41 tuş
- **Çapraz / Düz düzen** (`combo_duzen`, `Alt+D`, QSettings `duzen`). Çaprazda her
  satır `CAPRAZ_OFSET`'e göre sağa kaçar: `{2: 0.0, 1: 0.5, 0: 0.75, -1: 1.25}` tuş
  genişliği birimiyle, yani fizikî klavyenin kaçıklığı (124 px tuşta 0, 65, 97, 162
  px). Düzde bütün satırlar hizalı. Izgara `QGridLayout` değil, satır başına bir
  `QHBoxLayout`; kaçıklık baştaki `addSpacing` ile verilir
- Yazı ölçeği `OLCEK_TUS_W/H` (95x110) referansına göre, `MAX_TUS_W/H`'ye göre değil;
  tuş büyüdükçe yazı da büyür (124x142'de ölçek 1.29)
- Tuş boyutu `_tus_olcusu()` ile pencereye göre ölçeklenir; tam ekranda `MAX_TUS_W`
  üst sınırı uygulanmaz

### Kısayollar
- `F11`: Tam ekran / normal geçiş
- `<` / `>`: Bütün ızgarayı bir oktav aşağı / yukarı kaydırır (±3 ile sınırlı)
- `Shift` (basılı): bütün perdeleri **+5 koma**
- `Ctrl` (basılı): bütün perdeleri **−5 koma**
- `Alt+M`: Makam dropdown
- `Alt+I`: Saz dropdown
- `Alt+D`: Çapraz / düz düzen arasında geçiş

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

### Makam sırası ve aileleri
`nazariyat.py`'de:
- `MAKAM_ONCELIK = ("Saba", "Uşşak", "Rast", "Segah", "Hicaz")` — dropdown sırası;
  kalanı `tr_sirala` ile Türk alfabesine göre (`locale` yerine harf haritası, zira
  Windows'ta `locale.strxfrm` güvenilmez).
- `dizi_imzasi(makam)` perdelerin **mutlak koma** dizisini verir; `makam_aileleri()`
  aynı imzayı paylaşanları gruplar, ilk çağrıda hesaplanıp saklanır (40 `Makam`
  nesnesi 0.11 sn). Temsilci `AILE_ONCELIK`'e göre, yoksa alfabetik ilk.

Dört aile var, 12 makam; 28 makam tek başına, dropdown 32 satır:

| Temsilci | Üyeler |
|---|---|
| Hüseyni | Gerdaniye, Gülizar, Muhayyer, Neva |
| Uşşak | Arazbar, Bayati |
| Hicaz | Uzzal |
| Kürdi | Muhayyerkürdi |

Aile üyeleri **perdede değil güçlüde ve seyirde** ayrışır. Klavyede combonun yanında
rozet olarak dizilirler; rozete basmak ızgarayı yeniden kurmaz, yalnız rollerini
tazeler. QSettings `makam` fiilî üyeyi tutar, açılışta temsilcisi combo'ya kurulur.

Rol eşleşmesi `perde_base()` ile oktav yok sayılarak yapıldığı için iki çakışma var:
Muhayyer ve Muhayyerkürdî'nin güçlüsü durağın oktavı olduğundan turuncu hiç yanmaz
(mavi durak kazanır), Gerdâniye'de ise güçlü (gerdaniye) ile yeden (rast) aynı tabana
düştüğü için yeşil yeden görünmez.

### Bilinen veri kusurları
- **Ferahnâk**: kaynak güçlüyü `neva` veriyor, ama durak `ırak` olunca neva dizide
  bulunmuyor; kaynağın kendi ikinci ihtimali olan `evic` yazıldı. Dizinin kuruluşu
  (`ferahnak,5:rast,4`) gözden geçirilmeli, muhtemelen `@derece` demiri gerekiyor.
- **Acem**: dosya `çargah,5:çargah,4`'ü dügâh'a koyup dügâh'ta majör bir dizi
  üretiyor; kaynak "acem perdesinde çargâh beşlisi + beyâtî" diyor, yani Beyâtî
  ailesinden olmalı. Güçlüsü de bu yüzden `acem` yapılamadı (dizide yok).
- **Hisar**: kaynak "hüseynî üzerinde zirgüleli hicaz" diyor; bir sekizliye ancak
  dörtlüsü sığdığı için `hicaz,4` alındı — bu bir çıkarım.

### Tema sistemi
`TEMALAR` sözlüğünde tanımlı: Celik, Kehribar, Lacivert, Krem, Zümrüt, Gül,
Mürekkep, Sedef. Krem ve Sedef açık, ötekiler koyu.
Her tema: pencere, tuş, hover, basılı, durak, güçlü, koma renkleri.

## klavye.py Enstrümanlar

| Kategori | İsim | GM MIDI |
|---|---|---|
| Tuşlu | Piyano, Rhodes, Klavsen, Org, Çelesta, Vibrafon, Elektro Org, Akordeon | 0, 4, 6, 19, 8, 11, 16, 21 |
| Mızraplı | Ud, Tanbur, Kanun, Cümbüş, Harp, Bağlama, Lavta, Kopuz | 24, 104, 15, 105, 46, 25, 26, 32 |
| Yaylı | Keman, Viyola, Kemençe, Çello, Kontrbas, Yaylı Takım | 40, 41, 110, 42, 43, 48 |
| Nefesli | Ney, Flüt, Mıskal, Zurna, Girift, Mey, Klarnet, Kaval | 77, 73, 75, 68, 72, 69, 71, 74 |

Not: Hepsi en yakın GM karşılığı — Ud=24 (Nylon Guitar), Tanbur=104 (Sitar),
Kanun=15 (Dulcimer), Kemençe=110 (Fiddle), Ney=77 (Shakuhachi), Mıskal=75 (Pan
Flute), Zurna=68 (Oboe), Bağlama=25 (Steel Guitar), Lavta=26 (Jazz Guitar),
Kopuz=32 (Acoustic Bass), Girift=72 (Piccolo), Mey=69 (English Horn), Kaval=74
(Recorder). Hiçbir iki saz aynı presete düşmüyor.


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
Tam ekranda 41 tuş sabit; bazı makamlar daha geniş aralık gerektirebilir.

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
