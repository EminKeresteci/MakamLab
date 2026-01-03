# MakamNN

Türk Makam Müziği teorisini dijital ortama aktarmayı amaçlayan bir kütüphane ve araç seti.

## Özellikler

- **Nazariyat Motoru**: Türk Makam Müziği sistemindeki perdeleri (koma değerleri dahil), çeşnileri ve dizileri modelleyen sınıflar.
- **Ses Sentezleme**: `scamp` kütüphanesini kullanarak makam dizilerini ve perdeleri mikrotonal olarak seslendirme imkanı.
- **Veri Seti**: Geleneksel Türk müziği perde, çeşni ve dizi bilgilerini içeren metin tabanlı veri dosyaları (`perde.txt`, `cesni.txt`, `dizi.txt`).
- **Etkileşimli Klavye**: Makam perdelerini içeren klavye arayüzü (`makam_klavye.py`).

## Dosya Yapısı

- `nazariyat.py`: Ana teorik çerçeveyi çizen sınıfları (`Nazariyat`, `Makam`, `Cesni`) içerir.
- `makam_klavye.py`: Makam perdeleriyle etkileşimli bir arayüz sunar.
- `perde.txt`, `cesni.txt`, `dizi.txt`: Teori için gerekli temel veri dosyaları.

## Kullanım Örneği

```python
from nazariyat import Makam

# Rast makamı oluştur
rast = Makam("Rast")

# Makamın perdelerini gör
print(rast.perdeler)

# Makamı seslendir (scamp kütüphanesi gerektirir)
rast.seslendir()
```

## Lisans

--