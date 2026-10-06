def ses_kutuphanesi():
    import os
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sf2", "GeneralUser-GS.sf2")
    if not os.path.exists(yol): return "general_midi"
    if os.name != "nt": return yol
    import ctypes
    from ctypes import wintypes
    kisalt = ctypes.windll.kernel32.GetShortPathNameW
    kisalt.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    tampon = ctypes.create_unicode_buffer(1024)
    return tampon.value if kisalt(yol, tampon, 1024) else yol


def perde_midi(perde, koma=0, oktav=0, nazariyat=None):
    if nazariyat is None: nazariyat = Nazariyat()
    parcalar = str(perde).split(",")
    if len(parcalar) == 3: esas, koma, oktav = parcalar
    elif len(parcalar) == 2: esas, koma = parcalar
    else: esas = parcalar[0]
    return 55 + nazariyat.mutlak_koma(f"{esas},{int(koma)},{int(oktav)}") * 12 / 53


def seslendir(perde, koma=0, oktav=0, volume=0.7, duration=1, alet=0, session=None, instrument=None, nazariyat=None, print_midi=False):
    if session is None:
        from scamp import Session
        session = Session(default_soundfont=ses_kutuphanesi())
    if nazariyat is None: nazariyat = Nazariyat()

    if instrument is None:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            instrument = session.new_part(preset=alet)

    midi = perde_midi(perde, koma, oktav, nazariyat)
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
        session = Session(default_soundfont=ses_kutuphanesi())
    if nazariyat is None: nazariyat = Nazariyat()
    if instrument is None:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            instrument = session.new_part(preset=alet)

    midi = perde_midi(perde, koma, oktav, nazariyat)
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


MAKAM_ONCELIK = ("Saba", "Uşşak", "Rast", "Segah", "Hicaz")
AILE_ONCELIK = MAKAM_ONCELIK + ("Hüseyni", "Kürdi", "Sultaniyegah")
TR_ALFABE = "abcçdefgğhıijklmnoöprsştuüvyzqwx"


def tr_anahtar(ibare):
    return [TR_ALFABE.find(h) if h in TR_ALFABE else len(TR_ALFABE)
            for h in str(ibare).lower()]


def tr_sirala(isimler):
    return sorted(isimler, key=tr_anahtar)


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
                     '!':0, '%':1, '&':2, '/':3, '(':7, ')':10, '=':11, '*':13} # normalde kullanılmayan koma değerleri

        self.koma_degerleri = {"sol": 0, "la": 9, "si": 18, "do": 22,
                               "re": 31, "mi": 40, "fa": 44}
        self._aileler = None
        self.komadan_isme = {}
        for p, ad in zip(self.perde["perde"], self.perde["isim"]):
            try:
                self.komadan_isme.setdefault(self.mutlak_koma(p.strip()), ad)
            except (KeyError, ValueError):
                pass

    def mutlak_koma(self, perde):
        esas, koma, oktav = perde.split(",")
        return (self.koma_degerleri[esas.strip().lower()]
                + int(koma) + int(oktav) * 53)

    def perdeden_isme(self, perde):
        eslesme = self.perde.loc[self.perde["perde"] == perde, "isim"].values
        if len(eslesme) > 0: return eslesme[0]
        try:
            ad = self.komadan_isme.get(self.mutlak_koma(perde))
        except (KeyError, ValueError):
            ad = None
        if ad is not None: return ad
        raise ValueError("Perde bulunamadı!!!", perde)

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

    def çeşni_çöz(self, hücre):
        çözüm = []
        if hücre is None or str(hücre).strip().lower() in ("", "nan"):
            return çözüm
        for parça in str(hücre).split("+"):
            parça = parça.strip()
            if not parça: continue
            if "@" in parça:
                ad, demir = parça.rsplit("@", 1)
                çözüm.append((self.çeşni_bul(ad.strip()), int(demir)))
            else:
                çözüm.append((self.çeşni_bul(parça), 0))
        return çözüm

    def adlıya_çek(self, perde):
        k = self.mutlak_koma(perde)
        if k in self.komadan_isme: return perde
        en_yakın = min(self.komadan_isme, key=lambda a: (abs(a - k), a))
        return self.isimden_perdeye(self.komadan_isme[en_yakın])

    def aralıklardan_perdelere(self, durak, *çeşniler, tiz=None):
        perdeler = [durak]
        güçlü = None
        def sirala(liste):
            tekil = {}
            for p in liste: tekil.setdefault(self.mutlak_koma(p), p)
            return [tekil[k] for k in sorted(tekil)]

        for çeşni in çeşniler:
            sifre, demir = çeşni if isinstance(çeşni, tuple) else (çeşni, 0)
            perde = perdeler[demir - 1] if demir else perdeler[-1]
            for k in sifre:
                perde = self.koma_ekle(perde, self.koma[k.lower()])
                perdeler.append(perde)
            perdeler = sirala(perdeler)
            if güçlü is None: güçlü = perdeler[-1]

        perdeler = sirala([self.adlıya_çek(p) for p in perdeler])

        if tiz is not None:
            sinir = self.mutlak_koma(tiz)
            perdeler = [p for p in perdeler if self.mutlak_koma(p) <= sinir]
            if self.mutlak_koma(perdeler[-1]) < sinir: perdeler.append(tiz)

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
            return "".join(self.perdelerden_aralıklara(perdeler=self.dizi_bul(isim)[0]))

    def çeşni_bul(self, isim):
        return self.çeşni.loc[self.çeşni["isim"].apply(tasfiye) == tasfiye(isim), "çeşni"].values[0]

    def dizi_bul(self, isim):
        try: alt, üst, durak, yeden, güçlü, seyir, tiz = self.dizi.loc[self.dizi["isim"].apply(tasfiye) == tasfiye(isim), ["alt", "üst", "durak","yeden","güçlü","seyir","tiz"]].values[0]
        except IndexError: raise ValueError(f"{isim} makamı bulunamadı.")
        çeşniler = self.çeşni_çöz(alt) + self.çeşni_çöz(üst)
        tiz_perde = None
        if tiz is not None and str(tiz).strip().lower() not in ("", "nan"):
            tiz_perde = self.isimden_perdeye(str(tiz).strip())
        perdeler = self.aralıklardan_perdelere(self.isimden_perdeye(durak),
                                               *çeşniler, tiz=tiz_perde)[1]
        aralıklar = "".join(self.perdelerden_aralıklara(perdeler=perdeler))
        return perdeler, aralıklar, durak, yeden, güçlü, seyir

    def makam_sirasi(self):
        isimler = [str(i) for i in self.dizi["isim"]]
        oncelik = [i for i in MAKAM_ONCELIK if i in isimler]
        return oncelik + tr_sirala(i for i in isimler if i not in oncelik)

    def dizi_imzasi(self, makam):
        return tuple(self.mutlak_koma(p) for p in makam.perdeler)

    def makam_aileleri(self):
        if self._aileler is None:
            oncelik = {isim: i for i, isim in enumerate(AILE_ONCELIK)}
            anahtar = lambda i: (oncelik.get(i, len(oncelik)), tr_anahtar(i))
            imzalar = {}
            for isim in self.makam_sirasi():
                try:
                    imza = self.dizi_imzasi(Makam(isim, nazariyat=self))
                except Exception:
                    imza = (isim,)
                imzalar.setdefault(imza, []).append(isim)
            self._aileler = {}
            for üyeler in imzalar.values():
                sirali = sorted(üyeler, key=anahtar)
                self._aileler[sirali[0]] = sirali
        return self._aileler

    def aile_temsilcisi(self, isim):
        for temsilci, üyeler in self.makam_aileleri().items():
            if isim in üyeler:
                return temsilci
        return isim

    def temsilciler_sirali(self):
        aileler = self.makam_aileleri()
        return [i for i in self.makam_sirasi() if i in aileler]


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