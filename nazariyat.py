def seslendir(perde, koma=0, oktav=0, volume=0.7, duration=1, alet=0, session=None, nazariyat=None, print_midi=False):
    """
    :param perde:
    :param koma:
    :param oktav:
    :param volume:
    :param duration:
    :param alet:
    :param session:
    :param nazariyat:
    :return:
    """
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
    if print_midi: print(midi)
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

        self.perde = pd.read_csv("perde.txt", sep=":")
        self.çeşni = pd.read_csv("çeşni.txt", sep=":")
        self.dizi = pd.read_csv("dizi.txt", sep=":")

        self.fıtri_dizi = "TTBTTBT"
        self.fıtri_perdeler = ["sol", "la", "si", "do", "re", "mi", "fa"]
        self.yarım_perdeler = ["si", "mi"], ["do", "fa"]
        self.koma = {'b':4, 's':5, 'm':6, 'k':8, 't': 9, 'a':12,
                     '!':0, '%':1, '&':2, '/':3, '(':7, ')':10, '=':11} # normalde kullanılmayan koma değerleri

    def perdeden_isme(self, perde):
        eslesme = self.perde.loc[self.perde["perde"] == perde, "isim"].values
        if len(eslesme) > 0: return eslesme[0]
        else:  raise ValueError("Perde bulunamadı!!!", perde)

    def isimden_perdeye(self, isim):
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

        i_1 = self.fıtri_perdeler.index(esas_1)
        i_2 = self.fıtri_perdeler.index(esas_2)
        esas_fark = 0
        if i_1 > i_2:
            for i in range(i_2,i_1):
                esas_fark += 4 if self.fıtri_perdeler[i] in self.yarım_perdeler[0] else 9
        elif i_1 < i_2:
            for i in range(i_2,i_1,-1):
                esas_fark += -4 if self.fıtri_perdeler[i] in self.yarım_perdeler[1] else -9

        return 53*(int(oktav_1)-int(oktav_2)) + esas_fark + int(koma_1) - int(koma_2)

    def aralaıklardan_perdelere(self, durak, alt, üst):
        perdeler = [durak]
        for k in alt: perdeler.append(self.koma_ekle(perdeler[-1], self.koma[k.lower()]))
        güçlü = perdeler[-1]
        for k in üst: perdeler.append(self.koma_ekle(perdeler[-1], self.koma[k.lower()]))
        return güçlü, perdeler

    def perdelerden_aralıklara(self, perdeler=None, isim=None):
        if perdeler is not None:
            komalar = []
            önceki_perde = perdeler[0]
            for perde in perdeler[1:]:
                komalar.append(find_key(self.koma, abs(self.koma_fark(perde, önceki_perde))))
                önceki_perde = perde
            return komalar
        elif isim is not None:
            alt, üst, durak = self.dizi.loc[self.dizi["isim"].apply(tasfiye) == tasfiye(isim), ["alt", "üst", "durak"]].values[0]
            return self.çeşni_bul(alt) + self.çeşni_bul(üst)

    def çeşni_bul(self, isim):
        return self.çeşni.loc[self.çeşni["isim"].apply(tasfiye) == tasfiye(isim), "çeşni"].values[0]

    def dizi_bul(self, isim):
        #TODO: yeden, seyr
        alt, üst, durak = self.dizi.loc[self.dizi["isim"].apply(tasfiye) == tasfiye(isim), ["alt", "üst", "durak"]].values[0]
        return self.aralaıklardan_perdelere(self.isimden_perdeye(durak), self.çeşni_bul(alt), self.çeşni_bul(üst))

class Makam():
    def __init__(self, isim="Rast", durak=None, güçlü=None, yeden=None, seyir=None, aralıklar=None, perdeler=None, nazariyat=None):
        if nazariyat is None: self.nazariyat = Nazariyat()
        else: self.nazariyat = nazariyat

        self.isim = isim

        if perdeler is not None and aralıklar is not None:
            self.perdeler = perdeler
            self.aralıklar = aralıklar

            if durak is None: self.durak = perdeler[0]
            elif durak in self.nazariyat.perde.perde.values: self.durak = durak
            elif durak in self.nazariyat.perde.isim.values: self.durak = self.nazariyat.isimden_perdeye(durak)
            elif durak in self.nazariyat.fıtri_perdeler: self.durak = durak + ",0,0"
            else: raise ValueError("Durak tanınamadı !!!")

            if güçlü is None: self.güçlü = self.perdeler[4]
            elif güçlü in self.nazariyat.perde.perde.values: self.güçlü = güçlü
            elif güçlü in self.nazariyat.perde.isim.values: self.güçlü = self.nazariyat.isimden_perdeye(güçlü)
            elif güçlü in self.nazariyat.fıtri_perdeler: self.güçlü = güçlü + ",0,0"
            else: raise ValueError("Güçlü tanınamadı !!!")

        elif perdeler is None and aralıklar is not None:
            self.aralıklar = aralıklar
            if durak is None: self.durak = self.nazariyat.isimden_perdeye(isim)
            self.güçlü, self.perdeler = self.nazariyat.aralaıklardan_perdelere(self.durak, self.aralıklar)

        elif perdeler is not None and aralıklar is None:
            self.perdeler = perdeler
            self.durak, self.güçlü, self.aralıklar = self.nazariyat.perdelerden_aralıklara(perdeler)

        else:
            self.güçlü, self.perdeler = self.nazariyat.dizi_bul(isim)
            self.aralıklar = self.nazariyat.perdelerden_aralıklara(isim=isim)

        self.arıza = ""

        for perde in self.perdeler:
            perde, koma, oktav = perde.split(",")
            if int(koma)>0: self.arıza += f"{perde} {koma} koma diyez\n"
            elif int(koma)<0: self.arıza += f"{perde} {koma[1:]} koma bemol\n"

    def seslendir(self, volume=0.7, duration=1, alet=0, print_midi=False):
        for perde in self.perdeler:
            seslendir(perde, volume=volume, duration=duration, alet=alet, nazariyat=self.nazariyat, print_midi=print_midi)

    def taksim(self, volume=0.7, duration=1, alet=0):
        #TODO:
        self.seslendir(volume, duration, alet)


#Deprecated do not use
class Perde():
    def __init__(self, isim=None, perde=None, koma=0, oktav=0, nazariyat=None):
        if nazariyat is None: self.nazariyat = Nazariyat()

        if perde is not None: self.perde = perde
        else: self.perde = Nazariyat().isimden_perdeye(isim)

        if isim is None: self.isim = isim
        else: self.isim = Nazariyat().perdeden_isme(perde)

    def seslendir(self, volume=0.7, duration=1, alet=0):
        seslendir(self.perde, volume=volume, duration=duration, alet=alet, nazariyat=self.nazariyat)

class çeşni():
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