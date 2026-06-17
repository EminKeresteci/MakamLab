# MakamNN

Türk makam müziğini bilgisayar ortamında modelleyen, çalan ve analiz eden bir kütüphane ve araç seti.

## Özellikler

- **53-TET Sistemi** — Oktav 53 eşit adıma bölünür; koma hassasiyetiyle mikrotonal ses üretimi
- **Nazariyat Motoru** — Perdeler, çeşniler, makam dizileri ve koma hesaplama sınıfları
- **Etkileşimli Klavye** (`klavye.py`) — PySide6 tabanlı GUI; 38 perde, 4 tema, 16 enstrüman, tam ekran modu
- **Taksim Algoritması** — Makam seyrini taklit eden rastgele/model tabanlı taksim
- **Analiz Araçları** — FFT, spektrogram, perde/nota tespiti

## Klavye (`klavye.py`)

Türkçe Q klavye düzeninde, fiziksel tuş dizilişiyle birebir eşleşen 4 satırlı klavye arayüzü.

**Modlar:**
- Normal: 14 perde (tek satır)
- Tam ekran (`F11`): 38 perde (4 satır — Z…0 arası)

**Özellikler:**
- Durak perdesi mavi, güçlü perdesi turuncu renkte gösterilir
- 4 tema: Çelik, Kehribar, Lacivert, Krem
- 16 enstrüman: Piyano, Ud, Ney, Keman ve daha fazlası
- Son seçilen makam, saz ve tema otomatik kaydedilir

**Kısayollar:**

| Tuş | İşlev |
|-----|--------|
| `F11` | Tam ekran / normal geçiş |
| `Ctrl+M` | Makam seçimi |
| `Ctrl+I` | Saz seçimi |

## Kullanım Örneği

```python
from nazariyat import Makam, seslendir

# Makam oluştur ve seslendir
rast = Makam("Rast")
print(rast.perdeler)
rast.seslendir()

# Tek perde çal
seslendir("sol,-1,0", volume=1.0, duration=1.5)
```

## Perde Formatı

`"esas,koma,oktav"` — örn. `"sol,-1,0"` (Rast), `"la,0,1"` (Neva)

```python
koma_kesir = koma * (12 / 53)
midi = 55 + degerler[esas] + oktav * 12 + koma_kesir
```

## Dosya Yapısı

| Dosya | Açıklama |
|-------|----------|
| `nazariyat.py` | Ana kütüphane: `Nazariyat`, `Makam`, `seslendir`, `nota_baslat` |
| `klavye.py` | PySide6 GUI klavye çalıcı |
| `dizi.txt` | 38 makam (alt çeşni, üst çeşni, durak, yeden, güçlü, seyir) |
| `perde.txt` | Perde adları ve koma/oktav değerleri |
| `çeşni.txt` | Çeşni aralık şifreleri |
| `fft.py` | FFT / frekans analizi |
| `tesbit.py` | Perde/nota tespiti |
| `waterfall.py` | Spektrogram görselleştirme |

## Kurulum

```bash
pip install scamp PySide6 pandas numpy
```

> `scamp` için FluidSynth kurulu olmalıdır.

## Lisans

—
