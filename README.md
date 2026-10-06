# MakamLab

Türk makam müziğini 53 eşit koma (AEU) üzerinden modelleyen, çalan ve
dinleyerek tahlil eden bir kütüphane ve araç seti.

## Özellikler

- **53-TET nazariyat motoru** — perde, çeşni ve makam dizileri; her perde
  `mutlak_koma` üzerinden tek hesapla seslendirilir
- **43 makam**, TDV İslâm Ansiklopedisi'yle teyitli diziler; gövde aileleri
  için bkz. [`aileler.md`](aileler.md)
- **Klavye** (`klavye.py`) — Türkçe Q üzerinde izomorfik ızgara, 30 saz,
  8 tema, koma kaydırma
- **Akort** (`akort.py`) — mikrofondan makam perdelerine göre akort ve
  isabet ölçümü
- **Tahlil** (`tahlil.py`) — makam bulma, mukayese ve dizi talimi
- **Taksim** — `Makam.taksim()`, deneysel ve rastgele

## Klavye

Satır = oktav, sütun = derece. Ana satırda `A` yeden, `S` durak; her makamda
aynı. Normal modda tek satır, `F11` tam ekranda dört satır (41 tuş).

| Tuş | İşlev |
|---|---|
| `F11` | Tam ekran / normal |
| `<` / `>` | Izgarayı bir oktav aşağı / yukarı |
| `Shift` (basılı) | Bütün perdeler +5 koma |
| `Ctrl` (basılı) | Bütün perdeler −5 koma |
| `Alt+M` / `Alt+I` | Makam / saz seçimi |
| `Alt+D` | Çapraz / düz düzen |

Yeden yeşil, durak mavi, güçlü turuncu gösterilir.

## Kullanım

```python
from nazariyat import Nazariyat, Makam, seslendir

naz = Nazariyat()
rast = Makam(isim="Rast", nazariyat=naz)
print(rast.perdeler)
rast.seslendir()

seslendir("sol,-1,0", duration=1.5, nazariyat=naz)
```

## Perde formatı

`"esas,koma,oktav"` — örn. `"sol,0,0"` (rast), `"si,-1,0"` (segâh),
`"la,0,1"` (muhayyer). Rast = sol = 0 koma; naturaller
`la=9, si=18, do=22, re=31, mi=40, fa=44`.

```python
midi = 55 + nazariyat.mutlak_koma(perde) * 12 / 53
```

## Dosyalar

| Dosya | İçerik |
|---|---|
| `nazariyat.py` | `Nazariyat`, `Makam`, `seslendir`, `nota_baslat` |
| `klavye.py`, `akort.py`, `tahlil.py` | Uygulamalar |
| `tema.py` | Renk temaları |
| `dizi.txt` | Makamlar: alt/üst çeşni, durak, yeden, seyir, güçlü, tiz |
| `perde.txt` | Perde adları ve koma değerleri |
| `çeşni.txt` | Çeşni aralık şifreleri (`b=4 s=5 k=8 t=9 a=12`) |
| `aileler.md` | Makam aileleri, TDV kaynaklı |

## Kurulum

```bash
pip install -r requirements.txt
```

Ses için önerilen kütüphane GeneralUser GS'dir:
[GeneralUser-GS.sf2](https://github.com/mrbumpy409/GeneralUser-GS) dosyasını
`data/sf2/` altına koyun; yoksa scamp'ın varsayılan kütüphanesi kullanılır.

## Lisans

—
