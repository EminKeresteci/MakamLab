def seslendir(perde, koma=0, oktav=0, volume=0.7, duration=1, alet=0, session=None, instrument=None, nazariyat=None, print_midi=False):
    if session is None:
        from scamp import Session
        session = Session()
    if nazariyat is None: nazariyat = Nazariyat()

    if instrument is None:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            instrument = session.new_part(preset=alet)

    degerler = {"sol": 0, "la": 2, "si": 4, "do": 5, "re": 7, "mi": 9, "fa": 10}

    perde = perde.split(",")
    if len(perde) == 3: perde, koma, oktav = perde
    elif len(perde) == 2: perde, koma = perde
    else: perde = perde[0]
    koma = int(koma)
    oktav = int(oktav)

    koma_kesir = koma * (12 / 53)

    midi = 55 + degerler[perde.lower()] + oktav*12 + koma_kesir
    if print_midi: print(midi)
    import time
    nota = instrument.start_note(midi, volume)
    time.sleep(duration)
    nota.end()

    return session, instrument, nazariyat


def nota_baslat(perde, koma=0, oktav=0, volume=0.7, alet=0, session=None, instrument=None, nazariyat=None):
    """Notayı başlatır ve bir NoteHandle döndürür. nota.end() ile kesilir."""
    if session is None:
        from scamp import Session
        session = Session()
    if nazariyat is None: nazariyat = Nazariyat()
    if instrument is None:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            instrument = session.new_part(preset=alet)

    degerler = {"sol": 0, "la": 2, "si": 4, "do": 5, "re": 7, "mi": 9, "fa": 10}

    perde_parcalari = str(perde).split(",")
    if len(perde_parcalari) == 3: perde, koma, oktav = perde_parcalari
    elif len(perde_parcalari) == 2: perde, koma = perde_parcalari
    else: perde = perde_parcalari[0]
    koma = int(koma)
    oktav = int(oktav)

    koma_kesir = koma * (12 / 53)
    midi = 55 + degerler[perde.lower()] + oktav * 12 + koma_kesir

    nota = instrument.start_note(midi, volume)
    return nota, session, instrument, nazariyat


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

    def aralıklardan_perdelere(self, durak, alt, üst):
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
        try: alt, üst, durak, yeden, güçlü, seyir = self.dizi.loc[self.dizi["isim"].apply(tasfiye) == tasfiye(isim), ["alt", "üst", "durak","yeden","güçlü","seyir"]].values[0]
        except IndexError: raise ValueError(f"{isim} makamı bulunamadı.")
        alt, üst = self.çeşni_bul(alt), self.çeşni_bul(üst)
        aralıklar = alt + üst
        return self.aralıklardan_perdelere(self.isimden_perdeye(durak), alt, üst)[1], aralıklar, durak, yeden, güçlü, seyir


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
            self.güçlü, self.perdeler = self.nazariyat.aralıklardan_perdelere(self.durak, self.aralıklar)

        elif perdeler is not None and aralıklar is None:
            self.perdeler = perdeler
            self.durak, self.güçlü, self.aralıklar = self.nazariyat.perdelerden_aralıklara(perdeler)

        else:
            self.perdeler, self.aralıklar, self.durak, self.yeden, self.güçlü, self.seyir = self.nazariyat.dizi_bul(isim)
            self.aralıklar = self.nazariyat.perdelerden_aralıklara(isim=isim)

        self.arıza = ""
        for perde in self.perdeler:
            perde, koma, oktav = perde.split(",")
            if int(koma)>0: self.arıza += f"{perde} {koma} koma diyez\n"
            elif int(koma)<0: self.arıza += f"{perde} {koma[1:]} koma bemol\n"

        self.seyir = self.seyir if seyir is None else seyir
        self.yeden = self.yeden if yeden is None else yeden
        self.güçlü = self.güçlü if güçlü is None else güçlü
        self.durak = self.durak if durak is None else durak

    def seslendir(self, volume=0.7, duration=1, alet=0, print_midi=False):
        import time
        session, instrument, _ = seslendir(self.perdeler[0], volume=volume, duration=0.001, alet=alet, nazariyat=self.nazariyat)
        i = self.perdeler.index(self.nazariyat.isimden_perdeye(self.güçlü))
        for perde in self.perdeler[:i+1]:
            seslendir(perde, volume=volume, duration=duration, alet=alet, session=session, instrument=instrument, nazariyat=self.nazariyat, print_midi=print_midi)
        time.sleep(duration)
        for perde in self.perdeler[i:]:
            seslendir(perde, volume=volume, duration=duration, alet=alet, session=session, instrument=instrument, nazariyat=self.nazariyat, print_midi=print_midi)

    def taksim(self, başlangıç_perdesi=0, volume=0.7, duration=1, alet=0, uzunluk=20, ):
        c, i = 0, başlangıç_perdesi
        try:
            f = open(f"{self.isim}.pth", "r")
            # load model
            while c < uzunluk if uzunluk else True:
                seslendir(self.perdeler[i], volume=volume, duration=duration, alet=alet, nazariyat=self.nazariyat)
                # i = model(i)
        except FileNotFoundError:
            print(f"{self.isim} makamı için model dosyası bulunamadı")
            import random
            while c < uzunluk if uzunluk else True:
                seslendir(self.perdeler[i], volume=volume, duration=duration, alet=alet, nazariyat=self.nazariyat)
                i += random.randint(-2,2) #TODO: seyir tabanlı perde geçişi
                #TODO: bazı makamlar atlamayı sever, mesela Rast
                i = 6 if i > 6 else i if i >= 0 else 0
                c += 1



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