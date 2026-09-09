import sys
import threading
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QLabel, QComboBox, QFrame)
from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut
from nazariyat import seslendir, nota_baslat, Nazariyat, Makam


from tema import TEMALAR

# İzomorfik ızgara: satır = oktav, sütun = derece.
# A satırı ana oktav; sütun 0 = yeden, sütun 1 = durak (DERECE_OFSET).
IZGARA_SATIRLARI = [
    (list("1234567890"),   2),
    (list("QWERTYUIOP"),   1),
    (list("ASDFGHJKLŞİ"),  0),
    (list("ZXCVBNMÖÇ."),  -1),
]
NORMAL_OKTAVLAR = (0,)
IZGARA_SUTUN = max(len(h) for h, _ in IZGARA_SATIRLARI)
DERECE_OFSET = 1  # sütun 0 yedene ayrıldı, dereceler bir sağa kaydı
SANAL_TUS = {"Ş": 0xBA, "İ": 0xDE}
SANAL_KODLAR = frozenset(SANAL_TUS.values())

# Fizikî klavyenin çapraz kaçıklığı, tuş genişliği biriminde
CAPRAZ_OFSET = {2: 0.0, 1: 0.5, 0: 0.75, -1: 1.25}
DUZENLER = ("Çapraz", "Düz")

KOMA_ADIM = 5  # Shift: +5 koma, Ctrl: -5 koma (basılı tutulduğu sürece)

MIN_TUS_W = 56
MIN_TUS_H = 64
MAX_TUS_W = 124
MAX_TUS_H = 152
OLCEK_TUS_W = 95   # yazı ölçeğinin referansı, tuş boyu bundan büyüyünce yazı da büyür
OLCEK_TUS_H = 110
TUS_ARALIK = 6
SATIR_ARALIK = 8


def renk_kaydir(renk, oran):
    h = renk.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if oran >= 0:
        r, g, b = (min(255, int(k + (255 - k) * oran)) for k in (r, g, b))
    else:
        r, g, b = (max(0, int(k * (1 + oran))) for k in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def egim(renk, ust=0.12, alt=-0.16):
    return (f"qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {renk_kaydir(renk, ust)},stop:1 {renk_kaydir(renk, alt)})")


def perde_base(p):
    parts = p.split(",")
    return f"{parts[0]}:{parts[1]}"


def komayla(p, k):
    if k == 0:
        return p
    esas, koma, oktav = p.split(",")
    return f"{esas},{int(koma) + k},{oktav}"


class MusikiTusu(QPushButton):
    def __init__(self, harf, w, h, ana_pencere, oktav=0, derece=0, parent=None):
        super().__init__(parent)
        self.klavye_harfi = harf
        self.ana_pencere = ana_pencere
        self.oktav = oktav
        self.derece = derece
        self.taban_perde = "sol,0,0"
        self.tam_perde = "sol,0,0"
        self.rol = "normal"
        self._basili = False
        # Ölçek: 95x110 tuşta tam 1.0, büyük tuşlarda >1
        self._olcek = min(w / OLCEK_TUS_W, h / OLCEK_TUS_H)
        self._stop_event = threading.Event()
        self._stop_event.set()

        self.setFixedSize(w, h)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 6, 4, 6)

        self.lbl_nota = QLabel("...")
        self.lbl_nota.setAlignment(Qt.AlignCenter)
        self.lbl_perde = QLabel("...")
        self.lbl_perde.setAlignment(Qt.AlignCenter)
        self.lbl_tus = QLabel(f"[{harf}]")
        self.lbl_tus.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(self.lbl_nota)
        layout.addWidget(self.lbl_perde)
        layout.addStretch()
        layout.addWidget(self.lbl_tus)

        self.clicked.connect(self.cal)
        self._stil_guncelle()

    def _t(self):
        return self.ana_pencere.aktif_tema

    def _fs(self, taban, ust=50):
        return min(ust, max(7, round(taban * self._olcek)))

    def _koma(self):
        return self.ana_pencere.koma_kaydirma

    def _nota_rengi(self):
        t = self._t()
        if self._koma():        return t["koma"]
        if self.rol == "durak": return t["durak_nota"]
        if self.rol == "gucu":  return t["gucu_nota"]
        if self.rol == "yeden": return t["yeden_nota"]
        return t["nota"]

    def _stil_guncelle(self):
        t = self._t()
        self.lbl_nota.setStyleSheet(
            f"background-color:transparent;font-weight:bold;"
            f"font-size:{self._fs(16)}px;color:{self._nota_rengi()};")
        self.lbl_perde.setStyleSheet(
            f"background-color:transparent;font-style:italic;"
            f"font-size:{self._fs(11)}px;color:{t['perde']};")
        self.lbl_tus.setStyleSheet(
            f"background-color:transparent;font-weight:bold;"
            f"font-size:{self._fs(13)}px;color:{t['tus_lbl']};")
        self.setStyleSheet(self._normal_stil())

    def tusu_kur(self, taban_perde, rol="normal"):
        self.taban_perde = taban_perde
        self.rol = rol
        self.perdeyi_tazele()

    def perdeyi_tazele(self):
        k = self._koma()
        self.tam_perde = komayla(self.taban_perde, k)
        nota_adi = self.tam_perde.split(",")[0].capitalize()
        try:
            perde_ismi = self.ana_pencere.nazariyat.perdeden_isme(self.tam_perde)
        except Exception:
            perde_ismi = nota_adi
        maks_harf = max(4, self.width() // 7)
        self.lbl_nota.setText(f"{nota_adi} {k:+d}" if k else nota_adi)
        self.lbl_perde.setText(perde_ismi[:maks_harf])
        if not self._basili:
            self._stil_guncelle()

    def _normal_stil(self):
        t = self._t()
        if self.rol == "durak":   bg, border = t["durak_bg"], t["durak_kenar"]
        elif self.rol == "gucu":  bg, border = t["gucu_bg"],  t["gucu_kenar"]
        elif self.rol == "yeden": bg, border = t["yeden_bg"], t["yeden_kenar"]
        else:                     bg, border = t["tus_bg"],   t["tus_kenar"]
        if self._koma():
            border = t["koma"]
        return (f"QPushButton{{background:{egim(bg)};border:2px solid {border};"
                f"border-radius:10px;}}"
                f"QPushButton:hover{{background:{egim(t['tus_hover'], 0.16, -0.10)};"
                f"border:2px solid {renk_kaydir(border, 0.22)};}}")

    def _basili_stil(self):
        t = self._t()
        border = (t["koma"] if self._koma()
                  else t["durak_kenar"] if self.rol == "durak"
                  else t["gucu_kenar"] if self.rol == "gucu"
                  else t["yeden_kenar"] if self.rol == "yeden" else "#ffffff")
        return (f"QPushButton{{background:{egim(t['tus_basili'], -0.12, 0.14)};"
                f"border:3px solid {border};border-radius:10px;}}")

    def bas(self):
        self._basili = True
        self.setStyleSheet(self._basili_stil())
        self.lbl_nota.setStyleSheet(
            f"background-color:transparent;font-weight:bold;"
            f"font-size:{self._fs(20)}px;color:#ffffff;")
        self._stop_event.set()
        self._stop_event = threading.Event()
        alet = self.ana_pencere.secili_alet_kodu()
        meclis = self.ana_pencere.meclis_getir()
        enstruman = self.ana_pencere.enstruman_getir(alet)
        naz = self.ana_pencere.nazariyat
        stop = self._stop_event
        threading.Thread(target=self._nota_tut,
                         args=(alet, meclis, enstruman, naz, stop),
                         daemon=True).start()

    def birak(self):
        self._basili = False
        self.perdeyi_tazele()
        self._stop_event.set()

    def cal(self):
        alet = self.ana_pencere.secili_alet_kodu()
        threading.Thread(target=self._seslendir_wrapper,
                         args=(alet,
                               self.ana_pencere.meclis_getir(),
                               self.ana_pencere.enstruman_getir(alet),
                               self.ana_pencere.nazariyat),
                         daemon=True).start()

    def _seslendir_wrapper(self, alet, meclis, enstruman, naz):
        try:
            seslendir(self.tam_perde, duration=0.5, volume=1.0,
                      alet=alet, session=meclis, instrument=enstruman, nazariyat=naz)
        except Exception as e:
            print(f"Icra hatasi: {e}")

    def _nota_tut(self, alet, meclis, enstruman, naz, stop_event):
        try:
            nota, _, _, _ = nota_baslat(
                self.tam_perde, volume=1.0, alet=alet,
                session=meclis, instrument=enstruman, nazariyat=naz)
            stop_event.wait()
            nota.end()
        except Exception as e:
            print(f"Icra hatasi: {e}")


class AnaPencere(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sebeke-i Musiki")
        self.tus_sozlugu = {}
        self.tus_paneli = QFrame()
        self.daimi_meclis = None
        self.aktif_enstruman = None
        self.aktif_alet_kodu = None
        self.aktif_tema = TEMALAR["Celik"]
        self._aktif_makam = None
        self._yukleniyor = False
        self.aile_rozetleri = {}
        self._tam_ekran = False
        self.oktav_kaydirma = 0
        self.koma_kaydirma = 0

        try:
            self.nazariyat = Nazariyat()
        except Exception as e:
            print(f"Nazariyat yuklenemedi: {e}")
            self.nazariyat = None

        self.meclis_kur()
        self.enstrumanlar = {
            # Tuşlu
            "Piyano": 0, "Rhodes": 4, "Klavsen": 6, "Org": 19,
            "Çelesta": 8, "Vibrafon": 11, "Elektro Org": 16, "Akordeon": 21,
            # Mızraplı
            "Ud": 24, "Tanbur": 104, "Kanun": 15, "Cümbüş": 105, "Harp": 46,
            "Bağlama": 25, "Lavta": 26, "Kopuz": 32,
            # Yaylı
            "Keman": 40, "Viyola": 41, "Kemençe": 110,
            "Çello": 42, "Kontrbas": 43, "Yaylı Takım": 48,
            # Nefesli
            "Ney": 77, "Flüt": 73, "Mıskal": 75, "Zurna": 68,
            "Girift": 72, "Mey": 69, "Klarnet": 71, "Kaval": 74,
        }

        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._klavyeyi_yenile)

        self.ayarlar = QSettings("MakamNN", "SebekeMusiki")

        self.setup_ui()
        self.resize(IZGARA_SUTUN * (MAX_TUS_W + TUS_ARALIK) + 40, MAX_TUS_H + 210)
        self._ayarlari_yukle()
        self._klavyeyi_kur()

    def _ayarlari_yukle(self):
        self._yukleniyor = True
        tema = self.ayarlar.value("tema", "Celik")
        idx = self.combo_tema.findText(tema)
        if idx >= 0:
            self.combo_tema.setCurrentIndex(idx)

        saz = self.ayarlar.value("saz", "Piyano")
        idx = self.combo_alet.findText(saz)
        if idx >= 0:
            self.combo_alet.setCurrentIndex(idx)

        duzen = self.ayarlar.value("duzen", DUZENLER[0])
        idx = self.combo_duzen.findText(duzen)
        if idx >= 0:
            self.combo_duzen.setCurrentIndex(idx)

        makam = self.ayarlar.value("makam", "Rast")
        try:
            temsilci = self.nazariyat.aile_temsilcisi(makam)
        except Exception:
            temsilci = makam
        idx = self.combo_makam.findText(temsilci)
        if idx >= 0:
            self.combo_makam.setCurrentIndex(idx)
        self._aktif_makam = makam if idx >= 0 else self.combo_makam.currentText()
        self._aile_seridini_kur(self.combo_makam.currentText())
        self._yukleniyor = False

    def meclis_kur(self):
        if self.daimi_meclis is None:
            try:
                from scamp import Session
                self.daimi_meclis = Session()
                self.daimi_meclis.master_clock.pool_size = 100
            except Exception as e:
                print(f"Meclis hatasi: {e}")

    def meclis_getir(self):
        return self.daimi_meclis

    def enstruman_getir(self, alet_kodu):
        if self.aktif_enstruman is None or self.aktif_alet_kodu != alet_kodu:
            if self.daimi_meclis:
                import contextlib, io
                with contextlib.redirect_stdout(io.StringIO()):
                    self.aktif_enstruman = self.daimi_meclis.new_part(preset=alet_kodu)
                self.aktif_alet_kodu = alet_kodu
        return self.aktif_enstruman

    def setup_ui(self):
        self.ana_layout = QVBoxLayout(self)
        self.ana_layout.setSpacing(15)
        self.ana_layout.setContentsMargins(20, 20, 20, 15)

        ust = QFrame()
        ust_layout = QHBoxLayout(ust)
        ust_layout.setContentsMargins(0, 0, 0, 0)
        ust_layout.setSpacing(10)

        self.lbl_alet = QLabel("Saz:")
        self.combo_alet = QComboBox()
        self.combo_alet.addItems(self.enstrumanlar.keys())
        self.combo_alet.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combo_alet.currentIndexChanged.connect(self._alet_degisti)

        self.lbl_makam = QLabel("Makam:")
        self.combo_makam = QComboBox()
        self.combo_makam.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if self.nazariyat and hasattr(self.nazariyat, "dizi"):
            self.combo_makam.addItems(self.nazariyat.temsilciler_sirali())
        self.combo_makam.currentIndexChanged.connect(self._temsilci_degisti)

        self.aile_serit = QFrame()
        self.aile_layout = QHBoxLayout(self.aile_serit)
        self.aile_layout.setContentsMargins(0, 0, 0, 0)
        self.aile_layout.setSpacing(4)
        self.aile_rozetleri = {}

        self.lbl_tema = QLabel("Tema:")
        self.combo_tema = QComboBox()
        self.combo_tema.addItems(TEMALAR.keys())
        self.combo_tema.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combo_tema.currentTextChanged.connect(self._tema_uygula)

        self.lbl_duzen = QLabel("Düzen:")
        self.combo_duzen = QComboBox()
        self.combo_duzen.addItems(DUZENLER)
        self.combo_duzen.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combo_duzen.currentTextChanged.connect(self._duzen_degisti)

        ust_layout.addStretch()
        for w in [self.lbl_alet, self.combo_alet,
                  self.lbl_makam, self.combo_makam, self.aile_serit,
                  self.lbl_tema, self.combo_tema,
                  self.lbl_duzen, self.combo_duzen]:
            ust_layout.addWidget(w)
        ust_layout.addStretch()

        leg = QFrame()
        leg_layout = QHBoxLayout(leg)
        leg_layout.setContentsMargins(0, 0, 0, 0)
        leg_layout.addStretch()
        self.lbl_yeden_leg = QLabel("Yeden")
        self.lbl_durak_leg = QLabel("Durak")
        self.lbl_gucu_leg = QLabel("Guclu")
        self.lbl_oktav_leg = QLabel("Oktav 0")
        self.lbl_koma_leg = QLabel("Koma 0")
        self.lbl_f11_leg = QLabel("[F11] Tam Ekran   [< >] Oktav   [Shift/Ctrl] ±5 Koma   [Alt+M] Makam   [Alt+I] Saz   [Alt+D] Düzen")
        leg_layout.addWidget(self.lbl_yeden_leg)
        leg_layout.addWidget(self.lbl_durak_leg)
        leg_layout.addWidget(self.lbl_gucu_leg)
        leg_layout.addSpacing(12)
        leg_layout.addWidget(self.lbl_oktav_leg)
        leg_layout.addWidget(self.lbl_koma_leg)
        leg_layout.addSpacing(20)
        leg_layout.addWidget(self.lbl_f11_leg)
        leg_layout.addStretch()

        self.ana_layout.addWidget(ust)
        self.ana_layout.addWidget(self.tus_paneli)
        self.ana_layout.addWidget(leg)
        self.ana_layout.addStretch()

        # Ctrl koma kaydırmasına ayrıldığı için dropdown kısayolları Alt'ta
        QShortcut(QKeySequence("Alt+M"), self).activated.connect(
            lambda: self.combo_makam.showPopup())
        QShortcut(QKeySequence("Alt+I"), self).activated.connect(
            lambda: self.combo_alet.showPopup())
        QShortcut(QKeySequence("Alt+D"), self).activated.connect(self._duzen_cevir)

    def _tus_paneli_degistir(self, yeni):
        idx = self.ana_layout.indexOf(self.tus_paneli)
        self.ana_layout.removeWidget(self.tus_paneli)
        self.tus_paneli.deleteLater()
        self.tus_paneli = yeni
        self.ana_layout.insertWidget(max(idx, 1), yeni)

    def _gorunur_satirlar(self):
        if self._tam_ekran:
            return IZGARA_SATIRLARI
        return [s for s in IZGARA_SATIRLARI if s[1] in NORMAL_OKTAVLAR]

    def _tus_olcusu(self, satir_sayisi):
        avail_w = self.width() - 40
        if avail_w > 10:
            kw = int((avail_w - (IZGARA_SUTUN - 1) * TUS_ARALIK) / IZGARA_SUTUN)
        else:
            kw = MAX_TUS_W
        if not self._tam_ekran:
            kw = min(kw, MAX_TUS_W)
        kw = max(MIN_TUS_W, kw)

        kh = int(kw * 1.15)
        if self._tam_ekran:
            avail_h = self.height() - 170  # üst panel + legenda + boşluklar
            sinir = (avail_h - (satir_sayisi - 1) * SATIR_ARALIK) // satir_sayisi
            kh = min(kh, sinir)
        else:
            kh = min(kh, MAX_TUS_H)
        return kw, max(MIN_TUS_H, kh)

    def _capraz_mi(self):
        return self.combo_duzen.currentText() == "Çapraz"

    def _duzen_degisti(self, isim):
        self.ayarlar.setValue("duzen", isim)
        self._klavyeyi_kur()
        self.setFocus()

    def _duzen_cevir(self):
        self.combo_duzen.setCurrentIndex(
            (self.combo_duzen.currentIndex() + 1) % self.combo_duzen.count())

    def _klavyeyi_kur(self):
        self.tus_sozlugu.clear()
        satirlar = self._gorunur_satirlar()
        kw, kh = self._tus_olcusu(len(satirlar))

        yeni = QFrame()
        dis = QHBoxLayout(yeni)
        dis.setContentsMargins(0, 0, 0, 0)
        dis.addStretch()

        yigin = QVBoxLayout()
        yigin.setSpacing(SATIR_ARALIK)
        yigin.setContentsMargins(0, 0, 0, 0)

        capraz = self._capraz_mi()
        taban = min(CAPRAZ_OFSET.get(o, 0.0) for _, o in satirlar) if capraz else 0.0

        for harfler, oktav in satirlar:
            satir = QHBoxLayout()
            satir.setSpacing(TUS_ARALIK)
            satir.setContentsMargins(0, 0, 0, 0)
            if capraz:
                kacik = (CAPRAZ_OFSET.get(oktav, 0.0) - taban) * (kw + TUS_ARALIK)
                if kacik >= 1:
                    satir.addSpacing(int(kacik))
            for c, harf in enumerate(harfler):
                tus = MusikiTusu(harf, kw, kh, ana_pencere=self,
                                 oktav=oktav, derece=c, parent=yeni)
                satir.addWidget(tus)
                self.tus_sozlugu[SANAL_TUS.get(harf, ord(harf))] = tus
            satir.addStretch()
            yigin.addLayout(satir)

        dis.addLayout(yigin)
        dis.addStretch()
        self._tus_paneli_degistir(yeni)
        self.makam_degisti()

    def _klavyeyi_yenile(self):
        self._klavyeyi_kur()

    def _tema_uygula(self, isim):
        if isim not in TEMALAR:
            return
        self.aktif_tema = TEMALAR[isim]
        t = self.aktif_tema
        self.setStyleSheet(f"background-color:{t['pencere']};")

        combo_stil = (
            f"QComboBox{{padding:5px;border-radius:5px;background-color:{t['combo_bg']};"
            f"color:{t['baslik']};font-size:13px;min-width:130px;}}"
            f"QComboBox::drop-down{{border:0px;}}"
            f"QComboBox QAbstractItemView{{background-color:{t['combo_bg']};color:{t['baslik']};}}"
        )
        lbl_stil = f"color:{t['baslik']};font-size:13px;font-weight:bold;"
        for combo in [self.combo_alet, self.combo_makam,
                      self.combo_tema, self.combo_duzen]:
            combo.setStyleSheet(combo_stil)
        for lbl in [self.lbl_alet, self.lbl_makam, self.lbl_tema, self.lbl_duzen]:
            lbl.setStyleSheet(lbl_stil)

        self.lbl_yeden_leg.setStyleSheet(
            f"color:{t['yeden_kenar']};font-size:12px;font-weight:bold;"
            f"border:1px solid {t['yeden_kenar']};padding:2px 8px;border-radius:4px;"
            f"margin-right:8px;")
        self.lbl_durak_leg.setStyleSheet(
            f"color:{t['durak_kenar']};font-size:12px;font-weight:bold;"
            f"border:1px solid {t['durak_kenar']};padding:2px 8px;border-radius:4px;")
        self.lbl_gucu_leg.setStyleSheet(
            f"color:{t['gucu_kenar']};font-size:12px;font-weight:bold;"
            f"border:1px solid {t['gucu_kenar']};padding:2px 8px;border-radius:4px;margin-left:8px;")
        self.lbl_oktav_leg.setStyleSheet(
            f"color:{t['baslik']};font-size:12px;font-weight:bold;"
            f"border:1px solid {t['tus_kenar']};padding:2px 8px;border-radius:4px;")
        self.lbl_f11_leg.setStyleSheet(f"color:{t['perde']};font-size:11px;")
        self._koma_legendasi()
        self._rozetleri_boya()
        self.ayarlar.setValue("tema", isim)

        for tus in self.tus_sozlugu.values():
            tus._stil_guncelle()

    def secili_alet_kodu(self):
        return self.enstrumanlar.get(self.combo_alet.currentText(), 0)

    def _alet_degisti(self):
        self.aktif_enstruman = None
        self.aktif_alet_kodu = None
        self.ayarlar.setValue("saz", self.combo_alet.currentText())
        self.setFocus()

    def _derece_cetveli(self, perdeler):
        cevrim = (self.nazariyat.mutlak_koma(perdeler[-1])
                  - self.nazariyat.mutlak_koma(perdeler[0]))
        if cevrim == 0:
            cevrim = 53
        return perdeler[:-1], cevrim

    def _kaydir(self, perde, koma):
        if koma == 0:
            return perde
        return self.nazariyat.koma_ekle(perde, koma)

    def _derece_perdesi(self, cetvel, cevrim, oktav, derece):
        n = len(cetvel)
        return self._kaydir(cetvel[derece % n], (oktav + derece // n) * cevrim)

    def _sutun_perdesi(self, cetvel, cevrim, yeden_perde, oktav, sutun):
        if sutun == 0 and yeden_perde:
            return self._kaydir(yeden_perde, oktav * cevrim)
        return self._derece_perdesi(cetvel, cevrim, oktav, sutun - DERECE_OFSET)

    def _aile_uyeleri(self, temsilci):
        try:
            return self.nazariyat.makam_aileleri().get(temsilci, [temsilci])
        except Exception:
            return [temsilci]

    def _aile_seridini_kur(self, temsilci):
        for rozet in self.aile_rozetleri.values():
            self.aile_layout.removeWidget(rozet)
            rozet.deleteLater()
        self.aile_rozetleri = {}
        üyeler = self._aile_uyeleri(temsilci)
        self.aile_serit.setHidden(len(üyeler) < 2)
        if len(üyeler) < 2:
            return
        for isim in üyeler:
            rozet = QPushButton(isim)
            rozet.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            rozet.setCursor(Qt.CursorShape.PointingHandCursor)
            rozet.clicked.connect(lambda _=False, i=isim: self._aile_uyesi_sec(i))
            self.aile_layout.addWidget(rozet)
            self.aile_rozetleri[isim] = rozet
        self._rozetleri_boya()

    def _rozetleri_boya(self):
        t = self.aktif_tema
        for isim, rozet in self.aile_rozetleri.items():
            aktif = isim == self._aktif_makam
            kenar = t["gucu_kenar"] if aktif else t["tus_kenar"]
            renk = t["gucu_nota"] if aktif else t["perde"]
            rozet.setStyleSheet(
                f"QPushButton{{background-color:{t['combo_bg']};color:{renk};"
                f"border:1px solid {kenar};border-radius:5px;padding:4px 8px;"
                f"font-size:12px;font-weight:{'bold' if aktif else 'normal'};}}"
                f"QPushButton:hover{{border:1px solid {t['gucu_kenar']};}}")

    def _temsilci_degisti(self):
        temsilci = self.combo_makam.currentText()
        self._aktif_makam = temsilci
        self._aile_seridini_kur(temsilci)
        self.makam_degisti()

    def _aile_uyesi_sec(self, isim):
        self._aktif_makam = isim
        self._rozetleri_boya()
        self.makam_degisti()

    def makam_degisti(self):
        secilen = self._aktif_makam or self.combo_makam.currentText()
        if not secilen or not self.tus_sozlugu:
            return
        try:
            makam = Makam(isim=secilen, nazariyat=self.nazariyat)
            if not makam.perdeler:
                return
            cetvel, cevrim = self._derece_cetveli(makam.perdeler)
            try:
                gucu_base = perde_base(self.nazariyat.isimden_perdeye(makam.güçlü))
                durak_base = perde_base(self.nazariyat.isimden_perdeye(makam.durak))
            except Exception:
                gucu_base = durak_base = None
            try:
                yeden_perde = self.nazariyat.isimden_perdeye(makam.yeden)
            except Exception:
                yeden_perde = self._derece_perdesi(cetvel, cevrim, 0, -1)
            yeden_base = perde_base(yeden_perde)

            for tus in self.tus_sozlugu.values():
                perde = self._sutun_perdesi(
                    cetvel, cevrim, yeden_perde,
                    tus.oktav + self.oktav_kaydirma, tus.derece)
                pb = perde_base(perde)
                if pb == durak_base:     rol = "durak"
                elif pb == gucu_base:    rol = "gucu"
                elif pb == yeden_base:   rol = "yeden"
                else:                    rol = "normal"
                tus.tusu_kur(perde, rol)
        except Exception as e:
            print(f"Makam teskilati hatasi: {e}")
        if not self._yukleniyor:
            self.ayarlar.setValue("makam", secilen)
        self.setFocus()

    def _oktav_kaydir(self, adim):
        yeni = max(-3, min(3, self.oktav_kaydirma + adim))
        if yeni == self.oktav_kaydirma:
            return
        self.oktav_kaydirma = yeni
        self._oktav_legendasi()
        self.makam_degisti()

    def _oktav_legendasi(self):
        k = self.oktav_kaydirma
        self.lbl_oktav_leg.setText(f"Oktav {k:+d}" if k else "Oktav 0")

    def _koma_hesapla(self, event, basildi):
        mods = event.modifiers()
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        if event.key() == Qt.Key.Key_Shift:
            shift = basildi
        elif event.key() == Qt.Key.Key_Control:
            ctrl = basildi
        return (KOMA_ADIM if shift else 0) - (KOMA_ADIM if ctrl else 0)

    def _koma_kaydir(self, yeni):
        if yeni == self.koma_kaydirma:
            return
        self.koma_kaydirma = yeni
        self._koma_legendasi()
        for tus in self.tus_sozlugu.values():
            tus.perdeyi_tazele()

    def _koma_legendasi(self):
        t = self.aktif_tema
        k = self.koma_kaydirma
        if k:
            self.lbl_koma_leg.setText(f"KOMA {k:+d}")
            self.lbl_koma_leg.setStyleSheet(
                f"color:{t['pencere']};background-color:{t['koma']};"
                f"font-size:12px;font-weight:bold;"
                f"border:1px solid {t['koma']};padding:2px 8px;border-radius:4px;")
        else:
            self.lbl_koma_leg.setText("Koma 0")
            self.lbl_koma_leg.setStyleSheet(
                f"color:{t['perde']};font-size:12px;font-weight:bold;"
                f"border:1px solid {t['tus_kenar']};padding:2px 8px;border-radius:4px;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(200)

    def focusOutEvent(self, event):
        self._koma_kaydir(0)
        super().focusOutEvent(event)

    def _tus_bul(self, event: QKeyEvent):
        vk = event.nativeVirtualKey()
        if vk in SANAL_KODLAR:
            return self.tus_sozlugu.get(vk)
        return self.tus_sozlugu.get(int(event.key()))

    def keyPressEvent(self, event: QKeyEvent):
        self._koma_kaydir(self._koma_hesapla(event, True))
        key = event.key()
        if key == Qt.Key.Key_F11:
            self._tam_ekran = not self._tam_ekran
            if self._tam_ekran:
                self.showFullScreen()
            else:
                self.showNormal()
            return
        if key == Qt.Key.Key_Less:
            self._oktav_kaydir(-1)
            return
        if key == Qt.Key.Key_Greater:
            self._oktav_kaydir(1)
            return
        tus = self._tus_bul(event)
        if tus is not None and not event.isAutoRepeat():
            tus.bas()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        self._koma_kaydir(self._koma_hesapla(event, False))
        tus = self._tus_bul(event)
        if tus is not None and not event.isAutoRepeat():
            tus.birak()
        else:
            super().keyReleaseEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec())
