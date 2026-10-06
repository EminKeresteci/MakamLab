import sys
import math
import queue

import numpy as np
try:
    from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                                   QGridLayout, QPushButton, QLabel, QComboBox,
                                   QFrame, QDoubleSpinBox, QSpinBox, QCheckBox,
                                   QSizePolicy)
    from PySide6.QtCore import Qt, QThread, Signal, QSettings, QTimer, QRectF
    from PySide6.QtGui import (QPainter, QColor, QPen, QFont, QKeySequence,
                               QShortcut, QKeyEvent)
except ImportError:
    from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                                 QGridLayout, QPushButton, QLabel, QComboBox,
                                 QFrame, QDoubleSpinBox, QSpinBox, QCheckBox,
                                 QSizePolicy)
    from PyQt6.QtCore import (Qt, QThread, QSettings, QTimer, QRectF,
                              pyqtSignal as Signal)
    from PyQt6.QtGui import (QPainter, QColor, QPen, QFont, QKeySequence,
                             QShortcut, QKeyEvent)

from nazariyat import Nazariyat, Makam, nota_baslat, ses_kutuphanesi
from tema import TEMALAR


DEGERLER = {"sol": 0, "la": 2, "si": 4, "do": 5, "re": 7, "mi": 9, "fa": 10}
SENT_KOMA = 1200.0 / 53.0
AZAMI_SENT = 50.0
NETLIK_ESIGI = 0.93

RENK_ISABET = "#4caf50"
RENK_ORTA = "#ffc107"
RENK_UZAK = "#ef5350"

ORNEK_HIZI = 44100
PENCERE = 8192
ATLAMA = 2048
ASGARI_FREKANS = 55.0
AZAMI_FREKANS = 1600.0


def perde_midi(perde):
    esas, koma, oktav = str(perde).split(",")
    return 55 + DEGERLER[esas.lower()] + int(oktav) * 12 + int(koma) * (12.0 / 53.0)


def perde_kaydir(perde, oktav_farki):
    esas, koma, oktav = str(perde).split(",")
    return f"{esas},{koma},{int(oktav) + oktav_farki}"


def midi_frekans(midi, a4=440.0):
    return a4 * (2.0 ** ((midi - 69.0) / 12.0))


def frekans_midi(frekans, a4=440.0):
    return 69.0 + 12.0 * math.log2(frekans / a4)


def yin(y, sr, fmin=ASGARI_FREKANS, fmax=AZAMI_FREKANS, esik=0.15):
    n = len(y)
    if n < 512:
        return 0.0, 0.0
    y = y - y.mean()
    w = n // 2
    nfft = 1 << int(3 * w).bit_length()
    pencere_izdusum = np.fft.rfft(y[:w], nfft)
    cerceve_izdusum = np.fft.rfft(y[:2 * w], nfft)
    ozilinti = np.fft.irfft(cerceve_izdusum * np.conj(pencere_izdusum), nfft)[:w + 1]

    guc = np.concatenate(([0.0], np.cumsum(y ** 2)))
    ilk = guc[w] - guc[0]
    kayan = guc[w:2 * w + 1] - guc[0:w + 1]
    fark = ilk + kayan - 2.0 * ozilinti
    fark[0] = 0.0

    birikim = np.cumsum(fark[1:])
    normal = fark[1:] * np.arange(1, w + 1) / np.maximum(birikim, 1e-12)
    normal = np.concatenate(([1.0], normal))

    tau_alt = max(2, int(sr / fmax))
    tau_ust = min(w - 1, int(sr / fmin))
    if tau_ust <= tau_alt:
        return 0.0, 0.0

    dilim = normal[tau_alt:tau_ust + 1]
    altinda = np.where(dilim < esik)[0]
    if len(altinda):
        i = int(altinda[0])
        while i + 1 < len(dilim) and dilim[i + 1] < dilim[i]:
            i += 1
    else:
        i = int(np.argmin(dilim))
    tau = tau_alt + i

    for bolen in (4, 3, 2):
        aday = int(round(tau / bolen))
        if aday >= tau_alt and normal[aday] < min(0.4, normal[tau] + 0.22):
            tau = aday
            break

    netlik = 1.0 - float(np.clip(normal[tau], 0.0, 1.0))

    if 1 <= tau < len(normal) - 1:
        a, b, c = normal[tau - 1], normal[tau], normal[tau + 1]
        payda = a - 2.0 * b + c
        if abs(payda) > 1e-12:
            tau = tau + 0.5 * (a - c) / payda

    if tau <= 0:
        return 0.0, 0.0
    return sr / tau, netlik


class DinleyiciIplik(QThread):
    olcum = Signal(float, float, float)
    hata = Signal(str)

    def __init__(self, cihaz=None, parent=None):
        super().__init__(parent)
        self.cihaz = cihaz
        self.esik_rms = 0.0008
        self.alt_sinir = 70.0
        self._calisiyor = True

    def durdur(self):
        self._calisiyor = False

    def run(self):
        try:
            import sounddevice as sd
        except ImportError:
            self.hata.emit("sounddevice kurulu degil  ->  pip install sounddevice")
            return

        kuyruk = queue.Queue()

        def geri_cagir(veri, cerceve, zaman, durum):
            kuyruk.put(veri[:, 0].copy())

        try:
            akim = sd.InputStream(device=self.cihaz, channels=1,
                                  samplerate=ORNEK_HIZI, blocksize=ATLAMA,
                                  dtype="float32", callback=geri_cagir)
        except Exception as e:
            self.hata.emit(f"Mikrofon acilamadi: {e}")
            return

        tampon = np.zeros(PENCERE, dtype=np.float32)
        try:
            with akim:
                while self._calisiyor:
                    try:
                        blok = kuyruk.get(timeout=0.3)
                    except queue.Empty:
                        continue
                    k = len(blok)
                    if k >= PENCERE:
                        tampon = blok[-PENCERE:].copy()
                    else:
                        tampon = np.roll(tampon, -k)
                        tampon[-k:] = blok
                    rms = float(np.sqrt(np.mean(tampon ** 2)))
                    if rms < self.esik_rms:
                        self.olcum.emit(0.0, rms, 0.0)
                        continue
                    frekans, netlik = yin(tampon.astype(np.float64), ORNEK_HIZI,
                                          fmin=float(self.alt_sinir))
                    self.olcum.emit(frekans, rms, netlik)
        except Exception as e:
            self.hata.emit(f"Dinleme kesildi: {e}")


class SeviyeCubugu(QWidget):
    def __init__(self, tema, parent=None):
        super().__init__(parent)
        self.tema = tema
        self.seviye = 0.0
        self.desibel = -90.0
        self.setFixedHeight(18)

    def temayi_kur(self, tema):
        self.tema = tema
        self.update()

    def deger_kur(self, rms):
        self.desibel = 20.0 * math.log10(max(rms, 1e-6))
        self.seviye = float(np.clip((self.desibel + 66.0) / 66.0, 0.0, 1.0))
        self.update()

    def paintEvent(self, event):
        boya = QPainter(self)
        boya.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        boya.setPen(QPen(QColor(self.tema["tus_kenar"]), 1))
        boya.setBrush(QColor(self.tema["tus_bg"]))
        boya.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 4, 4)

        if self.desibel < -48.0:
            renk = QColor(RENK_UZAK)
        elif self.desibel > -3.0:
            renk = QColor(RENK_UZAK)
        elif self.desibel < -36.0:
            renk = QColor(RENK_ORTA)
        else:
            renk = QColor(RENK_ISABET)

        boya.setPen(Qt.PenStyle.NoPen)
        boya.setBrush(renk)
        boya.drawRoundedRect(QRectF(2, 2, max(0.0, (w - 4) * self.seviye), h - 4), 3, 3)

        yazi = QFont()
        yazi.setPointSize(8)
        boya.setFont(yazi)
        boya.setPen(QPen(QColor(self.tema["baslik"]), 1))
        if self.desibel < -48.0:
            metin = f"giriş seviyesi çok düşük  ({self.desibel:.0f} dBFS)"
        elif self.desibel > -3.0:
            metin = f"giriş kırpıyor  ({self.desibel:.0f} dBFS)"
        else:
            metin = f"{self.desibel:.0f} dBFS"
        boya.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, metin)


class AkortGostergesi(QWidget):
    def __init__(self, tema, parent=None):
        super().__init__(parent)
        self.tema = tema
        self.sapma = 0.0
        self.aktif = False
        self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def temayi_kur(self, tema):
        self.tema = tema
        self.update()

    def deger_kur(self, sapma, aktif=True):
        self.sapma = max(-AZAMI_SENT, min(AZAMI_SENT, sapma))
        self.aktif = aktif
        self.update()

    def _renk(self):
        if not self.aktif:
            return QColor(self.tema["tus_kenar"])
        m = abs(self.sapma)
        if m <= 5.0:
            return QColor(RENK_ISABET)
        if m <= 15.0:
            return QColor(RENK_ORTA)
        return QColor(RENK_UZAK)

    def _nokta(self, cx, cy, r, sapma):
        aci = math.radians(90.0 - (sapma / AZAMI_SENT) * 110.0)
        return cx + r * math.cos(aci), cy - r * math.sin(aci)

    def paintEvent(self, event):
        boya = QPainter(self)
        boya.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx = w / 2.0
        cy = h - 26.0
        r = min(w / 2.0 - 30.0, h - 55.0)
        if r < 40:
            return

        yay = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        boya.setPen(QPen(QColor(self.tema["tus_kenar"]), 3))
        boya.drawArc(yay, -20 * 16, 220 * 16)

        kalem_ince = QPen(QColor(self.tema["perde"]), 1)
        kalem_kalin = QPen(QColor(self.tema["baslik"]), 2)

        for sent in range(-40, 41, 10):
            boya.setPen(kalem_ince)
            x1, y1 = self._nokta(cx, cy, r, sent)
            x2, y2 = self._nokta(cx, cy, r - 9, sent)
            boya.drawLine(int(x1), int(y1), int(x2), int(y2))

        yazi = QFont()
        yazi.setPointSize(9)
        boya.setFont(yazi)
        for koma in (-2, -1, 0, 1, 2):
            sent = koma * SENT_KOMA
            if abs(sent) > AZAMI_SENT:
                continue
            boya.setPen(kalem_kalin)
            x1, y1 = self._nokta(cx, cy, r, sent)
            x2, y2 = self._nokta(cx, cy, r - 18, sent)
            boya.drawLine(int(x1), int(y1), int(x2), int(y2))
            tx, ty = self._nokta(cx, cy, r - 34, sent)
            boya.setPen(QPen(QColor(self.tema["perde"]), 1))
            etiket = "0" if koma == 0 else f"{koma:+d}k"
            boya.drawText(QRectF(tx - 22, ty - 10, 44, 20),
                          Qt.AlignmentFlag.AlignCenter, etiket)

        renk = self._renk()
        boya.setPen(QPen(renk, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        ix, iy = self._nokta(cx, cy, r - 22, self.sapma if self.aktif else 0.0)
        boya.drawLine(int(cx), int(cy), int(ix), int(iy))

        boya.setBrush(renk)
        boya.setPen(QPen(renk, 1))
        boya.drawEllipse(QRectF(cx - 7, cy - 7, 14, 14))

        yazi.setPointSize(15)
        yazi.setBold(True)
        boya.setFont(yazi)
        boya.setPen(QPen(renk, 1))
        if self.aktif:
            metin = f"{self.sapma:+.1f} sent   ({self.sapma / SENT_KOMA:+.2f} koma)"
        else:
            metin = "— dinleniyor —"
        boya.drawText(QRectF(0, cy - r * 0.42, w, 34),
                      Qt.AlignmentFlag.AlignCenter, metin)


class AnaPencere(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mizan-i Makam — Akort")
        self.resize(1040, 760)

        self.aktif_tema = TEMALAR["Celik"]
        self.ayarlar = QSettings("MakamNN", "MizanMakam")
        self.dinleyici = None
        self.daimi_meclis = None
        self.dem_notasi = None
        self.dem_enstruman = None

        self.hedefler = []
        self.makam_perdeleri = []
        self.perde_dugmeleri = {}
        self.kilitli_hedef = None
        self.gecmis = []
        self.sessiz = 0
        self.test_ornekleri = []
        self.test_aktif = False
        self._tam_ekran = False

        try:
            self.nazariyat = Nazariyat()
        except Exception as e:
            print(f"Nazariyat yuklenemedi: {e}")
            self.nazariyat = None

        self.isim_onbellek = {}
        self.isim_haritasi = {}
        if self.nazariyat is not None:
            for satir in self.nazariyat.perde.itertuples(index=False):
                try:
                    self.isim_haritasi[self.koma_sirasi(satir.perde)] = satir.isim
                except Exception:
                    continue

        self.setup_ui()
        self._ayarlari_yukle()
        self._hedefleri_kur()
        self._tema_uygula(self.combo_tema.currentText())
        self.dinlemeyi_baslat()

    def setup_ui(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(18, 16, 18, 14)
        ana.setSpacing(12)

        ust = QFrame()
        ust_l = QHBoxLayout(ust)
        ust_l.setContentsMargins(0, 0, 0, 0)
        ust_l.setSpacing(8)

        self.lbl_mod = QLabel("Mod:")
        self.combo_mod = QComboBox()
        self.combo_mod.addItems(["Makam perdeleri", "Tüm perdeler"])
        self.combo_mod.currentIndexChanged.connect(self._hedefleri_kur)

        self.lbl_makam = QLabel("Makam [Ctrl+M]:")
        self.combo_makam = QComboBox()
        if self.nazariyat is not None:
            self.combo_makam.addItems(self.nazariyat.dizi["isim"].tolist())
        self.combo_makam.currentIndexChanged.connect(self._hedefleri_kur)

        self.lbl_sistem = QLabel("Ses sistemi:")
        self.combo_sistem = QComboBox()
        self.combo_sistem.addItems(["12-TET + koma", "Saf 53-TET"])
        self.combo_sistem.currentIndexChanged.connect(self._hedefleri_kur)

        self.lbl_ahenk = QLabel("Ahenk (yarım ses):")
        self.spin_ahenk = QSpinBox()
        self.spin_ahenk.setRange(-12, 12)
        self.spin_ahenk.valueChanged.connect(self._hedefleri_kur)

        self.lbl_diyapazon = QLabel("Diyapazon A4:")
        self.spin_diyapazon = QDoubleSpinBox()
        self.spin_diyapazon.setRange(392.0, 466.0)
        self.spin_diyapazon.setDecimals(1)
        self.spin_diyapazon.setSingleStep(0.5)
        self.spin_diyapazon.setValue(440.0)
        self.spin_diyapazon.setSuffix(" Hz")
        self.spin_diyapazon.valueChanged.connect(self._hedefleri_kur)

        self.lbl_tema = QLabel("Tema:")
        self.combo_tema = QComboBox()
        self.combo_tema.addItems(TEMALAR.keys())
        self.combo_tema.currentTextChanged.connect(self._tema_uygula)

        for w in [self.lbl_mod, self.combo_mod, self.lbl_makam, self.combo_makam,
                  self.lbl_sistem, self.combo_sistem,
                  self.lbl_ahenk, self.spin_ahenk, self.lbl_diyapazon,
                  self.spin_diyapazon, self.lbl_tema, self.combo_tema]:
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            ust_l.addWidget(w)
        ust_l.addStretch()

        orta = QFrame()
        orta_l = QHBoxLayout(orta)
        orta_l.setContentsMargins(0, 0, 0, 0)
        orta_l.setSpacing(8)
        self.lbl_cihaz = QLabel("Mikrofon:")
        self.combo_cihaz = QComboBox()
        self.combo_cihaz.setMinimumWidth(280)
        self._cihazlari_doldur()
        self.combo_cihaz.currentIndexChanged.connect(self.dinlemeyi_baslat)
        self.lbl_alt = QLabel("Alt sınır:")
        self.spin_alt = QSpinBox()
        self.spin_alt.setRange(40, 800)
        self.spin_alt.setSingleStep(10)
        self.spin_alt.setValue(70)
        self.spin_alt.setSuffix(" Hz")
        self.spin_alt.setToolTip("Bu frekansın altında perde aranmaz. "
                                 "Kalimba için 200, insan sesi için 70")
        self.spin_alt.valueChanged.connect(self._alt_sinir_degisti)

        self.chk_dem = QCheckBox("Dem (referans ton)")
        self.chk_dem.toggled.connect(self._dem_degisti)
        self.btn_oto = QPushButton("Oto hedef")
        self.btn_oto.clicked.connect(self._hedef_serbest)
        for w in [self.lbl_cihaz, self.combo_cihaz, self.lbl_alt, self.spin_alt,
                  self.chk_dem, self.btn_oto]:
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            orta_l.addWidget(w)
        orta_l.addStretch()

        self.lbl_perde = QLabel("—")
        f = QFont()
        f.setPointSize(34)
        f.setBold(True)
        self.lbl_perde.setFont(f)
        self.lbl_perde.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_ayrinti = QLabel("Mikrofona bir ses ver")
        f2 = QFont()
        f2.setPointSize(11)
        self.lbl_ayrinti.setFont(f2)
        self.lbl_ayrinti.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gosterge = AkortGostergesi(self.aktif_tema)
        self.seviye = SeviyeCubugu(self.aktif_tema)

        self.perde_paneli = QFrame()
        self.perde_yerlesim = QGridLayout(self.perde_paneli)
        self.perde_yerlesim.setContentsMargins(0, 0, 0, 0)
        self.perde_yerlesim.setSpacing(6)

        alt = QFrame()
        alt_l = QHBoxLayout(alt)
        alt_l.setContentsMargins(0, 0, 0, 0)
        alt_l.setSpacing(10)
        self.btn_test = QPushButton("Ses Testi (5 sn)")
        self.btn_test.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_test.clicked.connect(self._test_basla)
        self.lbl_test = QLabel("Bir perdeyi tutup ölç: sapma ortalaması, kararlılık ve isabet oranı")
        alt_l.addWidget(self.btn_test)
        alt_l.addWidget(self.lbl_test, 1)

        ana.addWidget(ust)
        ana.addWidget(orta)
        ana.addWidget(self.lbl_perde)
        ana.addWidget(self.lbl_ayrinti)
        ana.addWidget(self.gosterge, 1)
        ana.addWidget(self.seviye)
        ana.addWidget(self.perde_paneli)
        ana.addWidget(alt)

        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(self.combo_makam.showPopup)

        self.test_zamanlayici = QTimer(self)
        self.test_zamanlayici.setSingleShot(True)
        self.test_zamanlayici.timeout.connect(self._test_bitir)

    def _cihazlari_doldur(self):
        self.cihaz_kimlikleri = [None]
        self.combo_cihaz.addItem("Varsayılan giriş")
        try:
            import sounddevice as sd
            for i, c in enumerate(sd.query_devices()):
                if c.get("max_input_channels", 0) > 0:
                    self.combo_cihaz.addItem(f"{i}: {c['name'][:40]}")
                    self.cihaz_kimlikleri.append(i)
        except Exception as e:
            print(f"Cihazlar listelenemedi: {e}")

    def _ayarlari_yukle(self):
        for kutu, anahtar, varsayilan in [(self.combo_tema, "tema", "Celik"),
                                          (self.combo_makam, "makam", "Rast"),
                                          (self.combo_mod, "mod", "Makam perdeleri"),
                                          (self.combo_sistem, "sistem", "Saf 53-TET")]:
            i = kutu.findText(self.ayarlar.value(anahtar, varsayilan))
            if i >= 0:
                kutu.setCurrentIndex(i)
        try:
            self.spin_diyapazon.setValue(float(self.ayarlar.value("diyapazon", 440.0)))
            self.spin_ahenk.setValue(int(self.ayarlar.value("ahenk", 0)))
            self.spin_alt.setValue(int(self.ayarlar.value("alt_sinir", 70)))
        except (TypeError, ValueError):
            pass

    def _ayarlari_kaydet(self):
        self.ayarlar.setValue("tema", self.combo_tema.currentText())
        self.ayarlar.setValue("makam", self.combo_makam.currentText())
        self.ayarlar.setValue("mod", self.combo_mod.currentText())
        self.ayarlar.setValue("sistem", self.combo_sistem.currentText())
        self.ayarlar.setValue("diyapazon", self.spin_diyapazon.value())
        self.ayarlar.setValue("ahenk", self.spin_ahenk.value())

    def koma_sirasi(self, perde):
        return self.nazariyat.koma_fark(str(perde), "sol,0,0")

    def perde_midi_hesap(self, perde):
        if self.nazariyat is not None and self.combo_sistem.currentIndex() == 1:
            return 55.0 + self.koma_sirasi(perde) * (12.0 / 53.0)
        return perde_midi(perde)

    def perde_ismi(self, perde):
        if perde in self.isim_onbellek:
            return self.isim_onbellek[perde]
        isim = perde
        if self.nazariyat is not None:
            try:
                sira = self.koma_sirasi(perde)
            except Exception:
                sira = None
            if sira is not None:
                if sira in self.isim_haritasi:
                    isim = self.isim_haritasi[sira]
                else:
                    for k in (1, -1, 2, -2):
                        if sira - 53 * k in self.isim_haritasi:
                            isim = f"{self.isim_haritasi[sira - 53 * k]} {k:+d} oktav"
                            break
        self.isim_onbellek[perde] = isim
        return isim

    def _hedefleri_kur(self):
        if self.nazariyat is None:
            return
        ahenk = self.spin_ahenk.value()
        makam_modu = self.combo_mod.currentIndex() == 0
        self.makam_perdeleri = []

        if makam_modu:
            try:
                makam = Makam(isim=self.combo_makam.currentText(), nazariyat=self.nazariyat)
                self.makam_perdeleri = list(dict.fromkeys(makam.perdeler))
                self.durak = self.nazariyat.isimden_perdeye(makam.durak)
                self.guclu = self.nazariyat.isimden_perdeye(makam.güçlü)
            except Exception as e:
                print(f"Makam kurulamadi: {e}")
                self.makam_perdeleri = []
                self.durak = self.guclu = None
            kaynak = self.makam_perdeleri
            kaydirmalar = range(-2, 3)
        else:
            kaynak = list(self.nazariyat.perde["perde"].values)
            self.durak = self.guclu = None
            kaydirmalar = range(-1, 2)

        gorulen = {}
        for perde in kaynak:
            for k in kaydirmalar:
                tam = perde_kaydir(perde, k)
                try:
                    m = self.perde_midi_hesap(tam) + ahenk
                except (KeyError, ValueError):
                    continue
                if not 20.0 <= m <= 108.0:
                    continue
                anahtar = round(m, 3)
                if anahtar not in gorulen:
                    gorulen[anahtar] = (tam, m)
        self.hedefler = sorted(gorulen.values(), key=lambda h: h[1])

        self.kilitli_hedef = None
        self._perde_seridini_kur()
        self._ayarlari_kaydet()
        self.setFocus()

    def _perde_seridini_kur(self):
        for dugme in self.perde_dugmeleri.values():
            dugme.deleteLater()
        self.perde_dugmeleri = {}
        if not self.makam_perdeleri:
            self.perde_paneli.hide()
            return
        self.perde_paneli.show()
        sutun = 0
        satir = 0
        for perde in self.makam_perdeleri:
            dugme = QPushButton(f"{self.perde_ismi(perde)}\n{perde}")
            dugme.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            dugme.setMinimumHeight(46)
            dugme.clicked.connect(lambda _=False, p=perde: self._hedef_kilitle(p))
            self.perde_yerlesim.addWidget(dugme, satir, sutun)
            self.perde_dugmeleri[perde] = dugme
            sutun += 1
            if sutun >= 9:
                sutun = 0
                satir += 1
        self._perde_stilleri()

    def _perde_stilleri(self, vurgulu=None):
        t = self.aktif_tema
        for perde, dugme in self.perde_dugmeleri.items():
            if perde == self.kilitli_hedef:
                kenar, yazi = RENK_ORTA, RENK_ORTA
            elif perde == vurgulu:
                kenar, yazi = RENK_ISABET, RENK_ISABET
            elif perde == getattr(self, "durak", None):
                kenar, yazi = t["durak_kenar"], t["durak_nota"]
            elif perde == getattr(self, "guclu", None):
                kenar, yazi = t["gucu_kenar"], t["gucu_nota"]
            else:
                kenar, yazi = t["tus_kenar"], t["perde"]
            dugme.setStyleSheet(
                f"QPushButton {{ background:{t['tus_bg']}; color:{yazi};"
                f" border:2px solid {kenar}; border-radius:7px; padding:4px;"
                f" font-size:11px; }}"
                f"QPushButton:hover {{ background:{t['tus_hover']}; }}")

    def _hedef_kilitle(self, perde):
        ahenk = self.spin_ahenk.value()
        self.kilitli_hedef = perde
        self.hedef_kilit_midi = self.perde_midi_hesap(perde) + ahenk
        self._perde_stilleri()
        if self.chk_dem.isChecked():
            self._dem_durdur()
            self._dem_basla()

    def _hedef_serbest(self):
        self.kilitli_hedef = None
        self._perde_stilleri()
        if self.chk_dem.isChecked():
            self.chk_dem.setChecked(False)

    def _tema_uygula(self, isim):
        if isim not in TEMALAR:
            return
        t = self.aktif_tema = TEMALAR[isim]
        self.setStyleSheet(
            f"QWidget {{ background:{t['pencere']}; color:{t['baslik']}; }}"
            f"QLabel {{ color:{t['perde']}; }}"
            f"QComboBox, QSpinBox, QDoubleSpinBox {{ background:{t['combo_bg']};"
            f" color:{t['baslik']}; border:1px solid {t['tus_kenar']};"
            f" border-radius:5px; padding:4px 8px; }}"
            f"QComboBox QAbstractItemView {{ background:{t['combo_bg']};"
            f" color:{t['baslik']}; selection-background-color:{t['tus_basili']}; }}"
            f"QCheckBox {{ color:{t['perde']}; }}"
            f"QPushButton {{ background:{t['tus_bg']}; color:{t['baslik']};"
            f" border:1px solid {t['tus_kenar']}; border-radius:6px; padding:6px 12px; }}"
            f"QPushButton:hover {{ background:{t['tus_hover']}; }}")
        self.lbl_perde.setStyleSheet(f"color:{t['nota']};")
        self.gosterge.temayi_kur(t)
        self.seviye.temayi_kur(t)
        self._perde_stilleri()
        self._ayarlari_kaydet()

    def dinlemeyi_baslat(self):
        if self.dinleyici is not None:
            self.dinleyici.durdur()
            self.dinleyici.wait(1500)
            self.dinleyici = None
        i = self.combo_cihaz.currentIndex()
        cihaz = self.cihaz_kimlikleri[i] if 0 <= i < len(self.cihaz_kimlikleri) else None
        self.dinleyici = DinleyiciIplik(cihaz)
        self.dinleyici.alt_sinir = float(self.spin_alt.value())
        self.dinleyici.olcum.connect(self._olcum_geldi)
        self.dinleyici.hata.connect(self._hata_geldi)
        self.dinleyici.start()
        self.setFocus()

    def _alt_sinir_degisti(self):
        if self.dinleyici is not None:
            self.dinleyici.alt_sinir = float(self.spin_alt.value())
        self.gecmis.clear()
        self.ayarlar.setValue("alt_sinir", self.spin_alt.value())

    def _hata_geldi(self, mesaj):
        self.lbl_perde.setText("—")
        self.lbl_ayrinti.setText(mesaj)

    def _olcum_geldi(self, frekans, rms, netlik):
        self.seviye.deger_kur(rms)
        if frekans <= 0.0 or netlik < NETLIK_ESIGI:
            self.sessiz += 1
            if self.sessiz > 6:
                self.gecmis.clear()
                self.gosterge.deger_kur(0.0, False)
                self.lbl_perde.setText("—")
                if frekans > 0.0:
                    self.lbl_ayrinti.setText(
                        f"ses belirsiz — netlik %{netlik * 100:.0f}, "
                        f"gereken %{NETLIK_ESIGI * 100:.0f}"
                        "   (vuruş anı ve sönüm kuyruğu güvenilmez)")
                else:
                    self.lbl_ayrinti.setText("Mikrofona bir ses ver")
                self._perde_stilleri()
            return

        self.sessiz = 0
        self.gecmis.append(frekans)
        if len(self.gecmis) > 5:
            self.gecmis.pop(0)
        f = float(np.median(self.gecmis))

        a4 = self.spin_diyapazon.value()
        midi = frekans_midi(f, a4)

        if self.kilitli_hedef is not None:
            hedef_perde = self.kilitli_hedef
            hedef_midi = self.hedef_kilit_midi
            fark_oktav = round((midi - hedef_midi) / 12.0)
            hedef_midi += fark_oktav * 12.0
        elif self.hedefler:
            hedef_perde, hedef_midi = min(self.hedefler, key=lambda h: abs(h[1] - midi))
        else:
            return

        sapma = (midi - hedef_midi) * 100.0
        self.gosterge.deger_kur(sapma, True)

        self.lbl_perde.setText(self.perde_ismi(hedef_perde))
        hedef_frekans = midi_frekans(hedef_midi, a4)
        self.lbl_ayrinti.setText(
            f"{f:.2f} Hz   |   hedef {hedef_perde}  =  {hedef_frekans:.2f} Hz"
            f"   |   netlik {netlik * 100:.0f}%")
        self._perde_stilleri(vurgulu=hedef_perde)

        if self.test_aktif and abs(sapma) < AZAMI_SENT:
            self.test_ornekleri.append(sapma)

    def _test_basla(self):
        self.test_ornekleri = []
        self.test_aktif = True
        self.btn_test.setEnabled(False)
        self.lbl_test.setText("Ölçülüyor… perdeyi düz tut")
        self.test_zamanlayici.start(5000)

    def _test_bitir(self):
        self.test_aktif = False
        self.btn_test.setEnabled(True)
        n = len(self.test_ornekleri)
        if n < 5:
            self.lbl_test.setText("Yeterli ses alınamadı — daha gür ve sürekli bir ses ver")
            return
        dizi = np.array(self.test_ornekleri)
        ortalama = float(np.mean(dizi))
        kararlilik = float(np.std(dizi))
        isabet_koma = float(np.mean(np.abs(dizi) <= SENT_KOMA / 2)) * 100.0
        isabet_dar = float(np.mean(np.abs(dizi) <= 10.0)) * 100.0
        self.lbl_test.setText(
            f"{n} ölçüm  |  ortalama sapma {ortalama:+.1f} sent ({ortalama / SENT_KOMA:+.2f} koma)"
            f"  |  kararlılık ±{kararlilik:.1f} sent"
            f"  |  ½ koma isabet %{isabet_koma:.0f}  |  ±10 sent isabet %{isabet_dar:.0f}")

    def _meclis_kur(self):
        if self.daimi_meclis is None:
            try:
                from scamp import Session
                self.daimi_meclis = Session(default_soundfont=ses_kutuphanesi())
                self.daimi_meclis.master_clock.pool_size = 20
            except Exception as e:
                print(f"Meclis hatasi: {e}")
        return self.daimi_meclis

    def _dem_degisti(self, durum):
        if durum:
            self._dem_basla()
        else:
            self._dem_durdur()

    def _dem_basla(self):
        perde = self.kilitli_hedef
        if perde is None:
            self.lbl_test.setText("Dem için önce bir perde düğmesine bas")
            self.chk_dem.setChecked(False)
            return
        meclis = self._meclis_kur()
        if meclis is None:
            self.chk_dem.setChecked(False)
            return
        try:
            if self.dem_enstruman is None:
                import contextlib, io
                with contextlib.redirect_stdout(io.StringIO()):
                    self.dem_enstruman = meclis.new_part(preset=77)
            esas, koma, oktav = perde.split(",")
            kaydirilmis = f"{esas},{koma},{int(oktav)}"
            nota, _, _, _ = nota_baslat(kaydirilmis, volume=0.5,
                                        session=meclis, instrument=self.dem_enstruman,
                                        nazariyat=self.nazariyat)
            self.dem_notasi = nota
        except Exception as e:
            print(f"Dem calinamadi: {e}")
            self.chk_dem.setChecked(False)

    def _dem_durdur(self):
        if self.dem_notasi is not None:
            try:
                self.dem_notasi.end()
            except Exception:
                pass
            self.dem_notasi = None

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_F11:
            self._tam_ekran = not self._tam_ekran
            self.showFullScreen() if self._tam_ekran else self.showNormal()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._dem_durdur()
        if self.dinleyici is not None:
            self.dinleyici.durdur()
            self.dinleyici.wait(1500)
        self._ayarlari_kaydet()
        super().closeEvent(event)


if __name__ == "__main__":
    uygulama = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(uygulama.exec())
