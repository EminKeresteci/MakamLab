import sys
import threading
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QLabel, QComboBox, QFrame)
from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut
from nazariyat import seslendir, nota_baslat, Nazariyat, Makam


TEMALAR = {
    "Celik": {
        "pencere": "#263238",
        "tus_bg": "#37474f", "tus_kenar": "#546e7a", "tus_hover": "#455a64", "tus_basili": "#78909c",
        "durak_bg": "#1a3a4a", "durak_kenar": "#29b6f6",
        "gucu_bg": "#3a2a1a", "gucu_kenar": "#ff8a65",
        "nota": "#ffca28", "durak_nota": "#29b6f6", "gucu_nota": "#ff8a65",
        "perde": "#b0bec5", "tus_lbl": "#546e7a",
        "baslik": "#eceff1", "combo_bg": "#455a64",
    },
    "Kehribar": {
        "pencere": "#1a1200",
        "tus_bg": "#2d1f00", "tus_kenar": "#6d4c00", "tus_hover": "#3d2a00", "tus_basili": "#8d6500",
        "durak_bg": "#001428", "durak_kenar": "#4499dd",
        "gucu_bg": "#3a1500", "gucu_kenar": "#ff8533",
        "nota": "#ffc107", "durak_nota": "#4499dd", "gucu_nota": "#ff8533",
        "perde": "#a08040", "tus_lbl": "#6d5000",
        "baslik": "#ffe080", "combo_bg": "#3d2a00",
    },
    "Lacivert": {
        "pencere": "#0d1b2a",
        "tus_bg": "#1b2d3e", "tus_kenar": "#2e4a63", "tus_hover": "#253d52", "tus_basili": "#3a6080",
        "durak_bg": "#0a2030", "durak_kenar": "#00bcd4",
        "gucu_bg": "#2a1a0a", "gucu_kenar": "#ff7043",
        "nota": "#e0f0ff", "durak_nota": "#00bcd4", "gucu_nota": "#ff7043",
        "perde": "#7090b0", "tus_lbl": "#2e4a63",
        "baslik": "#cce0ff", "combo_bg": "#253d52",
    },
    "Krem": {
        "pencere": "#f5f0e8",
        "tus_bg": "#e8e0d0", "tus_kenar": "#b0a090", "tus_hover": "#d8cfc0", "tus_basili": "#c8b898",
        "durak_bg": "#d0e8f8", "durak_kenar": "#1565c0",
        "gucu_bg": "#fce8d8", "gucu_kenar": "#bf360c",
        "nota": "#3d2b00", "durak_nota": "#1565c0", "gucu_nota": "#bf360c",
        "perde": "#6d5c40", "tus_lbl": "#b0a090",
        "baslik": "#2d1b00", "combo_bg": "#d8cfc0",
    },
}

# Tam ekranda ekran üstünden alta = yüksek perdeden alçak perdeye
# (fiziksel klavyeyle birebir: sayı satırı üstte, Z satırı altta)
SATIR_TUSLARI = [
    list("1234567890"),
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    list("ZXCVBNMÖÇ"),
]
# Sol kenar girintisi (key_unit = kw + ks cinsinden)
SATIR_OFFSETLERI = [0.0, 0.5, 0.75, 1.25]

# Perde sırası: Z = en alçak, 0 = en yüksek
TUM_TUSLAR = [
    "Z","X","C","V","B","N","M","Ö","Ç",
    "A","S","D","F","G","H","J","K","L",
    "Q","W","E","R","T","Y","U","I","O","P",
    "1","2","3","4","5","6","7","8","9","0",
]  # 38 tuş

NORMAL_TUS_SAYISI = 14
MAX_TUS_W = 95
MAX_TUS_H = 110
TUS_ARALIK = 6
SATIR_ARALIK = 8


def perde_base(p):
    parts = p.split(",")
    return f"{parts[0]}:{parts[1]}"


class MusikiTusu(QPushButton):
    def __init__(self, harf, w, h, ana_pencere, parent=None):
        super().__init__(parent)
        self.klavye_harfi = harf
        self.ana_pencere = ana_pencere
        self.tam_perde = "sol,0,0"
        self.rol = "normal"
        # Ölçek: normal modda (95x110) tam 1.0, büyük tuşlarda >1
        self._olcek = min(w / MAX_TUS_W, h / MAX_TUS_H)
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

    def _nota_rengi(self):
        t = self._t()
        if self.rol == "durak": return t["durak_nota"]
        if self.rol == "gucu":  return t["gucu_nota"]
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

    def tusu_kur(self, tam_perde, rol="normal"):
        self.tam_perde = tam_perde
        self.rol = rol
        parts = tam_perde.split(",")
        nota_adi = parts[0].capitalize() if parts else "?"
        try:
            perde_ismi = self.ana_pencere.nazariyat.perdeden_isme(tam_perde)
        except Exception:
            perde_ismi = nota_adi
        self.lbl_nota.setText(nota_adi)
        maks_harf = max(4, self.width() // 7)
        self.lbl_perde.setText(perde_ismi[:maks_harf])
        self._stil_guncelle()

    def _normal_stil(self):
        t = self._t()
        if self.rol == "durak":   bg, border = t["durak_bg"], t["durak_kenar"]
        elif self.rol == "gucu":  bg, border = t["gucu_bg"],  t["gucu_kenar"]
        else:                     bg, border = t["tus_bg"],   t["tus_kenar"]
        return (f"QPushButton{{background-color:{bg};border:2px solid {border};border-radius:8px;}}"
                f"QPushButton:hover{{background-color:{t['tus_hover']};}}")

    def _basili_stil(self):
        t = self._t()
        border = (t["durak_kenar"] if self.rol == "durak"
                  else t["gucu_kenar"] if self.rol == "gucu" else "#ffffff")
        return (f"QPushButton{{background-color:{t['tus_basili']};"
                f"border:3px solid {border};border-radius:8px;}}")

    def bas(self):
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
        self.setStyleSheet(self._normal_stil())
        self._stil_guncelle()
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
        self._tam_ekran = False

        try:
            self.nazariyat = Nazariyat()
        except Exception as e:
            print(f"Nazariyat yuklenemedi: {e}")
            self.nazariyat = None

        self.meclis_kur()
        self.enstrumanlar = {
            # Tuşlu
            "Piyano": 0, "Rhodes": 4, "Klavsen": 6, "Org": 19,
            # Mızraplı
            "Ud": 24, "Tanbur": 104, "Kanun": 15, "Cümbüş": 105, "Harp": 46,
            # Yaylı
            "Keman": 40, "Viyola": 41, "Kemençe": 110,
            # Nefesli
            "Ney": 77, "Flüt": 73, "Mıskal": 75, "Zurna": 68,
        }

        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._klavyeyi_yenile)

        self.ayarlar = QSettings("MakamNN", "SebekeMusiki")

        self.setup_ui()
        self._ayarlari_yukle()
        self._klavyeyi_kur_normal()

    def _ayarlari_yukle(self):
        tema = self.ayarlar.value("tema", "Celik")
        idx = self.combo_tema.findText(tema)
        if idx >= 0:
            self.combo_tema.setCurrentIndex(idx)

        saz = self.ayarlar.value("saz", "Piyano (Grand)")
        idx = self.combo_alet.findText(saz)
        if idx >= 0:
            self.combo_alet.setCurrentIndex(idx)

        makam = self.ayarlar.value("makam", "Rast")
        idx = self.combo_makam.findText(makam)
        if idx >= 0:
            self.combo_makam.setCurrentIndex(idx)

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

        self.lbl_alet = QLabel("Saz [Ctrl+I]:")
        self.combo_alet = QComboBox()
        self.combo_alet.addItems(self.enstrumanlar.keys())
        self.combo_alet.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combo_alet.currentIndexChanged.connect(self._alet_degisti)

        self.lbl_makam = QLabel("Makam [Ctrl+M]:")
        self.combo_makam = QComboBox()
        self.combo_makam.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if self.nazariyat and hasattr(self.nazariyat, "dizi"):
            self.combo_makam.addItems(self.nazariyat.dizi["isim"].tolist())
        self.combo_makam.currentIndexChanged.connect(self.makam_degisti)

        self.lbl_tema = QLabel("Tema:")
        self.combo_tema = QComboBox()
        self.combo_tema.addItems(TEMALAR.keys())
        self.combo_tema.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combo_tema.currentTextChanged.connect(self._tema_uygula)

        ust_layout.addStretch()
        for w in [self.lbl_alet, self.combo_alet,
                  self.lbl_makam, self.combo_makam,
                  self.lbl_tema, self.combo_tema]:
            ust_layout.addWidget(w)
        ust_layout.addStretch()

        leg = QFrame()
        leg_layout = QHBoxLayout(leg)
        leg_layout.setContentsMargins(0, 0, 0, 0)
        leg_layout.addStretch()
        self.lbl_durak_leg = QLabel("Durak")
        self.lbl_gucu_leg = QLabel("Guclu")
        self.lbl_f11_leg = QLabel("[F11] Tam Ekran")
        leg_layout.addWidget(self.lbl_durak_leg)
        leg_layout.addWidget(self.lbl_gucu_leg)
        leg_layout.addSpacing(20)
        leg_layout.addWidget(self.lbl_f11_leg)
        leg_layout.addStretch()

        self.ana_layout.addWidget(ust)
        self.ana_layout.addWidget(self.tus_paneli)
        self.ana_layout.addWidget(leg)
        self.ana_layout.addStretch()

        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(
            lambda: self.combo_makam.showPopup())
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(
            lambda: self.combo_alet.showPopup())

    def _tus_paneli_degistir(self, yeni):
        idx = self.ana_layout.indexOf(self.tus_paneli)
        self.ana_layout.removeWidget(self.tus_paneli)
        self.tus_paneli.deleteLater()
        self.tus_paneli = yeni
        self.ana_layout.insertWidget(max(idx, 1), yeni)

    def _klavyeyi_kur_normal(self):
        self.tus_sozlugu.clear()
        yeni = QFrame()
        hbox = QHBoxLayout(yeni)
        hbox.setSpacing(TUS_ARALIK)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addStretch()

        avail = self.width() - 40
        if avail > 10:
            bosluk = (NORMAL_TUS_SAYISI - 1) * TUS_ARALIK
            kw = max(70, min(MAX_TUS_W, (avail - bosluk) // NORMAL_TUS_SAYISI))
            kh = max(90, min(MAX_TUS_H, int(kw * 1.15)))
        else:
            kw, kh = MAX_TUS_W, MAX_TUS_H

        for harf in TUM_TUSLAR[:NORMAL_TUS_SAYISI]:
            tus = MusikiTusu(harf, kw, kh, ana_pencere=self, parent=yeni)
            hbox.addWidget(tus)
            self.tus_sozlugu[Qt.Key(ord(harf))] = tus

        hbox.addStretch()
        self._tus_paneli_degistir(yeni)
        self.makam_degisti()

    def _klavyeyi_kur_tam_ekran(self):
        self.tus_sozlugu.clear()

        avail_w = self.width() - 40
        avail_h = self.height() - 160  # üst panel + legenda + boşluklar

        # Q satırı en geniş: 10 tuş + 0.5 key_unit offset = 10.5kw + 9.5ks
        ks = TUS_ARALIK
        kw = max(50, int((avail_w - 9.5 * ks) / 10.5))
        kh = max(60, (avail_h - 3 * SATIR_ARALIK) // 4)
        key_unit = kw + ks

        yeni = QFrame()
        vbox = QVBoxLayout(yeni)
        vbox.setSpacing(SATIR_ARALIK)
        vbox.setContentsMargins(0, 0, 0, 0)

        for satir_tuslar, offset_ku in zip(SATIR_TUSLARI, SATIR_OFFSETLERI):
            hbox = QHBoxLayout()
            hbox.setSpacing(ks)
            hbox.setContentsMargins(0, 0, 0, 0)
            offset_px = int(offset_ku * key_unit)
            if offset_px > 0:
                hbox.addSpacing(offset_px)
            for harf in satir_tuslar:
                tus = MusikiTusu(harf, kw, kh, ana_pencere=self, parent=yeni)
                hbox.addWidget(tus)
                self.tus_sozlugu[Qt.Key(ord(harf))] = tus
            hbox.addStretch()
            vbox.addLayout(hbox)

        vbox.addStretch()
        self._tus_paneli_degistir(yeni)
        self.makam_degisti()

    def _klavyeyi_yenile(self):
        if self._tam_ekran:
            self._klavyeyi_kur_tam_ekran()
        else:
            self._klavyeyi_kur_normal()

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
        for combo in [self.combo_alet, self.combo_makam, self.combo_tema]:
            combo.setStyleSheet(combo_stil)
        for lbl in [self.lbl_alet, self.lbl_makam, self.lbl_tema]:
            lbl.setStyleSheet(lbl_stil)

        self.lbl_durak_leg.setStyleSheet(
            f"color:{t['durak_kenar']};font-size:12px;font-weight:bold;"
            f"border:1px solid {t['durak_kenar']};padding:2px 8px;border-radius:4px;")
        self.lbl_gucu_leg.setStyleSheet(
            f"color:{t['gucu_kenar']};font-size:12px;font-weight:bold;"
            f"border:1px solid {t['gucu_kenar']};padding:2px 8px;border-radius:4px;margin-left:8px;")
        self.lbl_f11_leg.setStyleSheet(f"color:{t['perde']};font-size:11px;")
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

    def _perde_havuzu(self, perdeler, n):
        if not perdeler or n == 0:
            return ["sol,0,0"] * n
        oktav_diff = int(perdeler[-1].split(",")[2]) - int(perdeler[0].split(",")[2])
        if oktav_diff == 0:
            oktav_diff = 1
        cycle = perdeler[:-1]
        cycle_len = len(cycle)

        def shift(p, k):
            e, ko, o = p.split(",")
            return f"{e},{ko},{int(o) + k * oktav_diff}"

        pool = [shift(p, k) for k in range(-6, 10) for p in cycle]
        base = 6 * cycle_len
        start = max(0, base - n // 4)
        end = min(len(pool), start + n)
        start = max(0, end - n)
        result = pool[start:end]
        while len(result) < n:
            result.append("sol,0,0")
        return result

    def makam_degisti(self):
        secilen = self.combo_makam.currentText()
        if not secilen or not self.tus_sozlugu:
            return
        try:
            makam = Makam(isim=secilen, nazariyat=self.nazariyat)
            n = len(self.tus_sozlugu)
            try:
                gucu_base = perde_base(self.nazariyat.isimden_perdeye(makam.güçlü))
                durak_base = perde_base(self.nazariyat.isimden_perdeye(makam.durak))
            except Exception:
                gucu_base = durak_base = None

            tam_perdeler = self._perde_havuzu(makam.perdeler, n)
            for tus, perde in zip(self.tus_sozlugu.values(), tam_perdeler):
                pb = perde_base(perde)
                if pb == durak_base:     rol = "durak"
                elif pb == gucu_base:    rol = "gucu"
                else:                    rol = "normal"
                tus.tusu_kur(perde, rol)
        except Exception as e:
            print(f"Makam teskilati hatasi: {e}")
        self.ayarlar.setValue("makam", self.combo_makam.currentText())
        self.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(200)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_F11:
            self._tam_ekran = not self._tam_ekran
            if self._tam_ekran:
                self.showFullScreen()
            else:
                self.showNormal()
            return
        if key in self.tus_sozlugu and not event.isAutoRepeat():
            self.tus_sozlugu[key].bas()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        key = event.key()
        if key in self.tus_sozlugu and not event.isAutoRepeat():
            self.tus_sozlugu[key].birak()
        else:
            super().keyReleaseEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec())
