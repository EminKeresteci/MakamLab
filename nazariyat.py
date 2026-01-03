def seslendir(perde, koma=0, oktav=0, volume=0.7, duration=1, alet=0, session=None, nazariyat=None):
    if session is None:
        from scamp import Session
        session = Session()
    if nazariyat is None: nazariyat = Nazariyat()
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        instrument = session.new_part(preset=alet)

    degerler = {"sol": 0, "la": 2, "si": 4, "do": 5, "re": 7, "mi": 9, "fa": 10}

    perde = perde.split(",")
    if len(perde) == 3: perde, koma, oktav = perde
    elif len(perde) == 2: perde, koma = perde
    else: perde = perde[0]
    koma = int(koma)
    oktav = int(oktav)

    tam = 4 if perde in nazariyat.yarım_perdeler[0 if koma > 0 else 1] else 9
    koma_kesir = koma / tam

    midi = 55 + degerler[perde.lower()] + oktav*12 + koma_kesir
    print(midi)
    instrument.play_note(midi, volume, duration)
    #TODO: perde doğruluğu

    return session, nazariyat

def tasfiye(ibare):
    if not ibare: return ""

    tebdil_haritasi = str.maketrans({
        "â": "a", "î": "i", "û": "u",
        "ı": "i", "ü": "u", "ö": "o",
        "ş": "s", "ğ": "g", "ç": "c"
    })

    return str(ibare).lower().translate(tebdil_haritasi).strip().replace(" ","")

def find_key(diz, value):
    for key, val in diz.items():
        if val == value:
            return key

class Nazariyat():
    def __init__(self):
        import pandas as pd

        with open("perde.txt", "r", encoding="utf-8") as f:
            self. perde = pd.DataFrame([line.split(":") for line in f.read().splitlines()], columns=["perde", "isim"])
        with open("cesni.txt", "r", encoding="utf-8") as f:
            self.cesni = pd.DataFrame([line.split(":") for line in f.read().splitlines()], columns=["isim", "cesni"])
        with open("dizi.txt", "r", encoding="utf-8") as f:
            self.dizi = pd.DataFrame([line.split(":") for line in f.read().splitlines()], columns=["isim", "alt", "ust", "durak"])

        self.fıtri_dizi = "TTBTTBT"
        self.fıtri_perdeler = ["sol", "la", "si", "do", "re", "mi", "fa"]
        self.yarım_perdeler = ["si", "mi"], ["do", "fa"]
        self.koma = {'b':4, 's':5, 'm':6, 'k':8, 't': 9, 'a':12,
                     '!':0, '%':1, '&':2, '/':3, '(':7, ')':10, '=':11} # normalde kullanılmayan koma değerleri

    def isme(self, perde):
        eslesme = self.perde.loc[self.perde["perde"] == perde, "isim"].values
        if len(eslesme) > 0: return eslesme[0]
        else:  raise ValueError("Perde bulunamadı!!!", perde)

    def perdeye(self, isim):
        eslesme = self.perde.loc[self.perde["isim"].apply(tasfiye) == tasfiye(isim), "perde"].values
        if len(eslesme) > 0: return eslesme[0]
        else: raise ValueError("İsim bulunamadı!!!", isim)
        return

    def koma_ekle(self, perde, eklenecek_koma):

        esas, koma, oktav = perde.split(",")


        i = self.fıtri_perdeler.index(esas)

        tam = 4 if esas in self.yarım_perdeler[0 if eklenecek_koma > 0 else 1] else 9

        if eklenecek_koma + int(koma) >= tam / 2:
            if i == 6:
                yeni_esas = self.fıtri_perdeler[0]
                yeni_oktav = int(oktav) + 1
            else:
                yeni_esas = self.fıtri_perdeler[i+1]
                yeni_oktav = oktav
            yeni_koma = eklenecek_koma + int(koma) - tam

        elif eklenecek_koma + int(koma) >= tam / -2:
            yeni_oktav = oktav
            yeni_esas = esas
            yeni_koma = eklenecek_koma + int(koma)

        else:
            if i == 0:
                yeni_esas = self.fıtri_perdeler[-1]
                yeni_oktav = int(oktav) - 1
            else:
                yeni_esas = self.fıtri_perdeler[i-1]
                yeni_oktav = oktav
            yeni_koma = eklenecek_koma + int(koma) + tam

        yeni_tam = 4 if yeni_esas in self.yarım_perdeler[0 if eklenecek_koma > 0 else 1] else 9
        if yeni_koma > yeni_tam/2:
            return self.koma_ekle(f"{yeni_esas},{0},{yeni_oktav}", yeni_koma)
        elif yeni_koma < yeni_tam/-2:
            return self.koma_ekle(f"{yeni_esas},{0},{yeni_oktav}", yeni_koma)
        else:
            return f"{yeni_esas},{yeni_koma},{yeni_oktav}"

    def koma_fark(self, perde_1, perde_2):
        esas_1, koma_1, oktav_1 = perde_1.split(",")
        esas_2, koma_2, oktav_2 = perde_2.split(",")


        return 53*(int(oktav_1)-int(oktav_2)) + int(koma_1) - int(koma_2)

    def perdelere(self, durak, alt, ust):
        perdeler = [durak]
        for k in alt: perdeler.append(self.koma_ekle(perdeler[-1], self.koma[k.lower()]))
        guclu = perdeler[-1]
        for k in ust: perdeler.append(self.koma_ekle(perdeler[-1], self.koma[k.lower()]))
        return guclu, perdeler

    def aralıklara(self, perdeler):
        komalar = []
        önceki_perde = perdeler[0]
        for perde in perdeler[1:]:
            komalar.append(find_key(self.koma, self.koma_fark(perde, önceki_perde)))
        return komalar

    def cesniye(self, isim):
        return self.cesni.loc[self.cesni["isim"].apply(tasfiye) == tasfiye(isim), "cesni"].values[0]

    def diziye(self, isim):
        #TODO: yeden, seyr
        alt, ust, durak = self.dizi.loc[self.dizi["isim"].apply(tasfiye) == tasfiye(isim), ["alt", "ust", "durak"]].values[0]
        return self.perdelere(self.perdeye(durak), self.cesniye(alt), self.cesniye(ust))

class Makam():
    def __init__(self, isim="Rast", durak=None, guclu=None, aralıklar=None, perdeler=None, nazariyat=None):
        if nazariyat is None: self.nazariyat = Nazariyat()
        else: self.nazariyat = nazariyat

        self.isim = isim

        if perdeler is not None and aralıklar is not None:
            self.perdeler = perdeler
            self.aralıklar = aralıklar

            if durak is None: self.durak = perdeler[0]
            elif durak in self.nazariyat.perde.perde.values: self.durak = durak
            elif durak in self.nazariyat.perde.isim.values: self.durak = self.nazariyat.perdeye(durak)
            elif durak in self.nazariyat.fıtri_perdeler: self.durak = durak + ",0,0"
            else: raise ValueError("Durak tanınamadı !!!")

            if guclu is None: self.guclu = self.perdeler[4]
            elif guclu in self.nazariyat.perde.perde.values: self.guclu = guclu
            elif guclu in self.nazariyat.perde.isim.values: self.guclu = self.nazariyat.perdeye(guclu)
            elif guclu in self.nazariyat.fıtri_perdeler: self.guclu = guclu + ",0,0"
            else: raise ValueError("Güçlü tanınamadı !!!")

        elif perdeler is None and aralıklar is not None:
            self.aralıklar = aralıklar
            if durak is None: self.durak = self.nazariyat.perdeye(isim)
            self.guclu, self.perdeler = self.nazariyat.perdelere(self.durak, self.aralıklar)

        elif perdeler is not None and aralıklar is None:
            self.perdeler = perdeler
            self.durak, self.guclu, self.aralıklar = self.nazariyat.aralıklara(perdeler)

        else:
            self.guclu, self.perdeler = self.nazariyat.diziye(isim)

        self.arıza = ""

        for perde in self.perdeler:
            perde, koma, oktav = perde.split(",")
            if int(koma)>0: self.arıza += f"{perde} {koma} koma diyez\n"
            elif int(koma)<0: self.arıza += f"{perde} {koma[1:]} koma bemol\n"

    def seslendir(self, volume=0.7, duration=1, alet=0):
        for perde in self.perdeler:
            seslendir(perde, volume=volume, duration=duration, alet=alet, nazariyat=self.nazariyat)

class Perde():
    def __init__(self, isim=None, perde=None, koma=0, oktav=0, nazariyat=None):
        if nazariyat is None: self.nazariyat = Nazariyat()

        if perde is not None: self.perde = perde
        else: self.perde = Nazariyat().perdeye(isim)

        if isim is None: self.isim = isim
        else: self.isim = Nazariyat().isme(perde)

    def seslendir(self, volume=0.7, duration=1, alet=0):
        seslendir(self.perde, volume=volume, duration=duration, alet=alet, nazariyat=self.nazariyat)

class Cesni():
    def __init__(self, isim="Rast", perde="sol", mebde=None, uzunluk=5, sifre=None, perdeler=[], nazariyat=None):
        if mebde is None: self.mebde = isim.lower()
        if nazariyat is None: self.nazariyat = Nazariyat()
        self.isim = isim
        if sifre is not None: self.uzunluk = len(sifre)
        else: self.uzunluk = uzunluk

        if len(perdeler) == 0:
            self.perdeler = [perde] * uzunluk

    def seslendir(self, volume=0.7, duration=1, alet=0):
        for perde in self.perdeler: seslendir(perde, volume=volume, duration=duration, alet=alet, nazariyat=self.nazariyat)