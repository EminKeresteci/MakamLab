import sys, threading, random, time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QListWidget,
    QListWidgetItem, QTabWidget, QFrame, QSplitter, QScrollArea,
    QGroupBox, QSlider, QLineEdit, QSizePolicy, QSpacerItem,
    QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QTimer, QRectF, QPointF, QSize
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient,
    QFontMetrics, QPainterPath, QKeyEvent
)

try:
    from nazariyat import Nazariyat, Makam, seslendir, nota_baslat, ses_kutuphanesi
except ImportError as e:
    print(f"nazariyat bulunamadı: {e}")
    sys.exit(1)


C_BG     = '#1a2327'
C_PNL    = '#263238'
C_PNL2   = '#2c393f'
C_PNL3   = '#37474f'
C_TXT    = '#eceff1'
C_TXT2   = '#b0bec5'
C_TXT3   = '#78909c'
C_GOLD   = '#ffca28'
C_ORG    = '#ff8f00'
C_BLUE   = '#29b6f6'
C_GREEN  = '#66bb6a'
C_RED    = '#ef5350'
C_PUR    = '#ab47bc'

ARALIK_RENK = {
    't': '#4caf50', 'k': '#8bc34a', 's': '#cddc39',
    'b': '#ff9800', 'a': '#f44336', 'm': '#9c27b0',
}
ARALIK_ISMI = {
    't': 'Tanini (9♩)', 'k': 'K.Mücennep (8♩)', 's': 'Büy.Bakiye (5♩)',
    'b': 'Bakiye (4♩)', 'a': 'Artık İkili (12♩)', 'm': 'Mücennep (6♩)',
}
SEYİR_İKON = {
    'çıkıcı': '▲', 'inici': '▼',
    'çıkıcı-inici': '▲▼', 'inici-çıkıcı': '▼▲', 'inici:': '▼',
}


def stil(w: QWidget, arka='', metin=C_TXT, kenarl=None, radius=6, dolgu='6px 12px'):
    css = f"background-color:{arka or C_PNL};color:{metin};border-radius:{radius}px;padding:{dolgu};"
    if kenarl:
        css += f"border:1px solid {kenarl};"
    else:
        css += "border:none;"
    w.setStyleSheet(css)


def buton(metin, renk=C_PNL3, metin_renk=C_TXT, boyut='normal') -> QPushButton:
    b = QPushButton(metin)
    fs = {'kucuk': 11, 'normal': 13, 'buyuk': 15}.get(boyut, 13)
    b.setStyleSheet(f"""
        QPushButton {{
            background-color:{renk}; color:{metin_renk};
            border:1px solid #546e7a; border-radius:6px;
            padding:7px 16px; font-size:{fs}px; font-weight:bold;
        }}
        QPushButton:hover  {{ background-color:#455a64; border-color:#78909c; }}
        QPushButton:pressed {{ background-color:#263238; }}
        QPushButton:disabled {{ background-color:#263238; color:#546e7a; border-color:#37474f; }}
    """)
    return b


def etiket(metin, renk=C_TXT, boyut=13, kalin=False) -> QLabel:
    lbl = QLabel(metin)
    lbl.setStyleSheet(
        f"color:{renk}; font-size:{boyut}px;"
        + ("font-weight:bold;" if kalin else "")
        + "background:transparent; border:none;"
    )
    return lbl


def ayrac() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"color:{C_PNL3}; background:{C_PNL3}; border:none; max-height:1px;")
    return f


class KartBilgi(QFrame):
    def __init__(self, baslik, deger, renk=C_BLUE, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_PNL2}; border-radius:8px; border:1px solid {C_PNL3};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        self.lbl_baslik = etiket(baslik, C_TXT3, 10)
        self.lbl_deger  = etiket(deger,  renk,   14, kalin=True)
        lay.addWidget(self.lbl_baslik)
        lay.addWidget(self.lbl_deger)

    def guncelle(self, deger, renk=None):
        self.lbl_deger.setText(deger)
        if renk:
            self.lbl_deger.setStyleSheet(
                f"color:{renk}; font-size:14px; font-weight:bold; background:transparent; border:none;"
            )


class MezanDiyagrami(QWidget):
    nota_secildi = Signal(str)

    def __init__(self, etiket_goster=True, parent=None):
        super().__init__(parent)
        self.perdeler   = []
        self.durak_p    = None
        self.guclu_p    = None
        self.araliklar  = ''
        self.naz        = None
        self.vurgu_set  = set()
        self.aktif_idx  = -1
        self.etiket_goster = etiket_goster
        self.setMinimumSize(380, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(210)
        self.setMouseTracking(True)
        self._hover_idx = -1

    def makam_yukle(self, makam: Makam, naz: Nazariyat, vurgu: set = None):
        self.perdeler  = list(makam.perdeler)
        self.araliklar = makam.aralıklar
        self.naz       = naz
        self.vurgu_set = vurgu or set()
        self.aktif_idx = -1

        self.durak_p = self.perdeler[0] if self.perdeler else None

        try:
            gp_str = naz.isimden_perdeye(makam.güçlü)
            ge, gk, _ = gp_str.split(',')
            self.guclu_p = next(
                (p for p in self.perdeler
                 if p.split(',')[0] == ge and p.split(',')[1] == gk),
                None
            )
        except Exception:
            self.guclu_p = None

        self.update()

    def temizle(self):
        self.perdeler = []
        self.durak_p  = None
        self.guclu_p  = None
        self.araliklar = ''
        self.update()

    def aktif_goster(self, idx: int):
        self.aktif_idx = idx
        self.update()

    def _koma_poz(self, p: str) -> int:
        if not self.perdeler or not self.naz:
            return 0
        try:
            return max(0, self.naz.koma_fark(p, self.perdeler[0]))
        except Exception:
            return 0

    def _x(self, koma_pos, margin_l, bar_w) -> float:
        return margin_l + koma_pos * bar_w / 53

    def paintEvent(self, event):
        if not self.perdeler:
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(C_PNL))
            p.setPen(QColor(C_TXT3))
            p.setFont(QFont('Arial', 11))
            p.drawText(self.rect(), Qt.AlignCenter, 'Makam seçilmedi')
            p.end()
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        ML, MR, MT, MB = 14, 14, 42, 60
        bw   = w - ML - MR
        bar_y = MT + (h - MT - MB) // 2

        p.fillRect(0, 0, w, h, QColor(C_PNL))

        poz_listesi = [self._koma_poz(prd) for prd in self.perdeler]

        for i, ch in enumerate(self.araliklar):
            if i >= len(self.perdeler) - 1:
                break
            x1 = self._x(poz_listesi[i],   ML, bw)
            x2 = self._x(poz_listesi[i+1], ML, bw)
            renk = QColor(ARALIK_RENK.get(ch.lower(), C_PNL3))
            renk.setAlpha(55)
            p.fillRect(QRectF(x1, bar_y - 5, x2 - x1, 10), renk)

        p.setPen(QPen(QColor(C_PNL3), 2, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(ML), bar_y, int(ML + bw), bar_y)

        for i, ch in enumerate(self.araliklar):
            if i >= len(self.perdeler) - 1:
                break
            x1  = self._x(poz_listesi[i],   ML, bw)
            x2  = self._x(poz_listesi[i+1], ML, bw)
            mid = (x1 + x2) / 2
            renk = QColor(ARALIK_RENK.get(ch.lower(), C_PNL3))

            p.setPen(QPen(renk.darker(110), 1))
            p.drawLine(int(x1), bar_y - 12, int(x2), bar_y - 12)
            p.drawLine(int(x1), bar_y - 12, int(x1), bar_y - 9)
            p.drawLine(int(x2), bar_y - 12, int(x2), bar_y - 9)

            p.setFont(QFont('Arial', 8, QFont.Bold))
            p.setPen(QPen(renk))
            p.drawText(QRectF(mid - 14, bar_y - 28, 28, 16), Qt.AlignCenter, ch.upper())

        for i, prd in enumerate(self.perdeler):
            pos  = poz_listesi[i]
            x    = self._x(pos, ML, bw)
            prts = prd.split(',')
            nota = prts[0].capitalize()
            koma = int(prts[1]) if len(prts) > 1 else 0

            aktif = (i == self.aktif_idx)
            vurgulu = (prd in self.vurgu_set)

            if aktif:
                dot_renk, dot_r = QColor(C_GREEN), 9
            elif prd == self.durak_p:
                dot_renk, dot_r = QColor(C_GOLD), 9
            elif prd == self.guclu_p:
                dot_renk, dot_r = QColor(C_ORG), 7
            elif vurgulu:
                dot_renk, dot_r = QColor(C_GREEN), 7
            elif i == self._hover_idx:
                dot_renk, dot_r = QColor(C_BLUE).lighter(130), 6
            else:
                dot_renk, dot_r = QColor(C_BLUE), 5

            halka = dot_renk.darker(150)
            p.setBrush(QBrush(dot_renk))
            p.setPen(QPen(halka, 1.5))
            p.drawEllipse(QRectF(x - dot_r, bar_y - dot_r, dot_r * 2, dot_r * 2))

            if self.etiket_goster:
                koma_str = (f'+{koma}' if koma > 0 else str(koma)) if koma != 0 else ''
                p.setFont(QFont('Arial', 8, QFont.Bold if prd in (self.durak_p, self.guclu_p) else QFont.Normal))
                p.setPen(QPen(dot_renk))
                p.drawText(QRectF(x - 22, bar_y + dot_r + 3, 44, 16), Qt.AlignCenter, nota + koma_str)

                try:
                    isim = self.naz.perdeden_isme(prd)
                    kisalt = isim.split()[-1][:9]
                except Exception:
                    kisalt = nota

                p.setFont(QFont('Arial', 7))
                p.setPen(QPen(QColor(C_TXT3)))
                p.drawText(QRectF(x - 24, bar_y + dot_r + 18, 48, 14), Qt.AlignCenter, kisalt)

                p.setFont(QFont('Arial', 7))
                p.setPen(QPen(QColor(C_TXT3)))
                p.drawText(QRectF(x - 10, h - 14, 20, 14), Qt.AlignCenter, str(pos))

        if self.etiket_goster:
            p.setFont(QFont('Arial', 8, QFont.Bold))
            p.setPen(QPen(QColor(C_GOLD)))
            p.drawText(QRectF(ML - 2, bar_y + 4, 12, 12), Qt.AlignCenter, '○')

        p.end()

    def mouseMoveEvent(self, ev):
        if not self.perdeler:
            return
        ML, MR = 14, 14
        bw = self.width() - ML - MR
        px = ev.position().x()
        best, bi = 99, -1
        for i, prd in enumerate(self.perdeler):
            pos = self._koma_poz(prd)
            x   = self._x(pos, ML, bw)
            if abs(px - x) < best:
                best, bi = abs(px - x), i
        if bi != self._hover_idx:
            self._hover_idx = bi
            self.update()

    def mousePressEvent(self, ev):
        if self._hover_idx >= 0 and self._hover_idx < len(self.perdeler):
            self.nota_secildi.emit(self.perdeler[self._hover_idx])


class PerdeBadge(QLabel):
    def __init__(self, perde_str, naz, durak_p=None, guclu_p=None, parent=None):
        super().__init__(parent)
        prts = perde_str.split(',')
        nota = prts[0].capitalize()
        koma = int(prts[1]) if len(prts) > 1 else 0
        koma_str = (f'+{koma}' if koma > 0 else str(koma)) if koma != 0 else ''
        try:
            isim = naz.perdeden_isme(perde_str)
        except Exception:
            isim = nota

        self.setText(f"{nota}{koma_str}\n{isim}")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(76, 48)

        if perde_str == durak_p:
            bg, fg, brd = C_GOLD, '#1a2327', C_GOLD
        elif perde_str == guclu_p:
            bg, fg, brd = C_PNL3, C_ORG, C_ORG
        else:
            bg, fg, brd = C_PNL2, C_TXT2, C_PNL3

        self.setStyleSheet(f"""
            QLabel {{
                background:{bg}; color:{fg};
                border:1px solid {brd}; border-radius:6px;
                font-size:10px; padding:2px;
            }}
        """)


class AnalizSekmesi(QWidget):
    def __init__(self, meclis, naz, parent=None):
        super().__init__(parent)
        self.meclis  = meclis
        self.naz     = naz
        self.makam   = None
        self.enstruman = None
        self._stop   = threading.Event()
        self._stop.set()
        self.setStyleSheet(f"background:{C_BG};")
        self._kurulum()

    def _kurulum(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(16, 12, 16, 12)
        ana.setSpacing(12)

        self.diyagram = MezanDiyagrami()
        ana.addWidget(self.diyagram)

        kart_satir = QHBoxLayout()
        kart_satir.setSpacing(8)
        self.k_durak  = KartBilgi('Durak', '—', C_GOLD)
        self.k_guclu  = KartBilgi('Güçlü', '—', C_ORG)
        self.k_yeden  = KartBilgi('Yeden', '—', C_BLUE)
        self.k_seyir  = KartBilgi('Seyir', '—', C_GREEN)
        for k in (self.k_durak, self.k_guclu, self.k_yeden, self.k_seyir):
            kart_satir.addWidget(k)
        ana.addLayout(kart_satir)

        ana.addWidget(ayrac())

        self.lbl_perdeler_baslik = etiket('Perdeler', C_TXT2, 11)
        ana.addWidget(self.lbl_perdeler_baslik)

        self.perde_alan = QWidget()
        self.perde_alan.setStyleSheet(f"background:{C_BG};")
        self.perde_satir = QHBoxLayout(self.perde_alan)
        self.perde_satir.setContentsMargins(0, 0, 0, 0)
        self.perde_satir.setSpacing(6)
        ana.addWidget(self.perde_alan)

        ana.addWidget(ayrac())

        aralik_satir = QHBoxLayout()
        aralik_satir.setSpacing(4)
        aralik_satir.addWidget(etiket('Aralıklar:', C_TXT3, 11))
        self.lbl_araliklar = etiket('—', C_TXT, 11)
        aralik_satir.addWidget(self.lbl_araliklar)
        aralik_satir.addStretch()
        self.lbl_ariza = etiket('', C_TXT2, 11)
        aralik_satir.addWidget(self.lbl_ariza)
        ana.addLayout(aralik_satir)

        efsane_satir = QHBoxLayout()
        efsane_satir.setSpacing(10)
        for k, ad in ARALIK_ISMI.items():
            dot = QLabel('●')
            dot.setStyleSheet(f"color:{ARALIK_RENK[k]}; background:transparent; border:none; font-size:11px;")
            efsane_satir.addWidget(dot)
            efsane_satir.addWidget(etiket(ad, C_TXT3, 10))
        efsane_satir.addStretch()
        ana.addLayout(efsane_satir)

        ana.addWidget(ayrac())

        buton_satir = QHBoxLayout()
        self.btn_cal        = buton('▶  Dizini Çal',     C_PNL3,  C_TXT)
        self.btn_guclu_cal  = buton('♩  Güçlüye Kadar', C_PNL3,  C_TXT, 'kucuk')
        self.btn_dur        = buton('■  Dur',            '#37474f', C_RED, 'kucuk')
        self.btn_dur.setEnabled(False)
        self.tempo_slider   = QSlider(Qt.Horizontal)
        self.tempo_slider.setRange(1, 5)
        self.tempo_slider.setValue(3)
        self.tempo_slider.setFixedWidth(90)
        self.tempo_slider.setStyleSheet(f"QSlider::groove:horizontal{{background:{C_PNL3};height:4px;border-radius:2px;}}QSlider::handle:horizontal{{background:{C_BLUE};width:12px;height:12px;margin:-4px 0;border-radius:6px;}}")
        lbl_tempo = etiket('Hız', C_TXT3, 10)

        for w in (self.btn_cal, self.btn_guclu_cal, self.btn_dur, lbl_tempo, self.tempo_slider):
            buton_satir.addWidget(w)
        buton_satir.addStretch()
        ana.addLayout(buton_satir)
        ana.addStretch()

        self.btn_cal.clicked.connect(self._tam_dizi_cal)
        self.btn_guclu_cal.clicked.connect(self._gucluye_cal)
        self.btn_dur.clicked.connect(self._dur)

    def makam_goster(self, makam: Makam):
        self.makam = makam
        self.diyagram.makam_yukle(makam, self.naz)

        try:
            durak_ismi = self.naz.perdeden_isme(makam.perdeler[0]).strip()
        except Exception:
            durak_ismi = makam.durak

        seyir_ikon = SEYİR_İKON.get(makam.seyir, '')
        self.k_durak.guncelle(durak_ismi,         C_GOLD)
        self.k_guclu.guncelle(str(makam.güçlü),   C_ORG)
        self.k_yeden.guncelle(str(makam.yeden),    C_BLUE)
        self.k_seyir.guncelle(f"{seyir_ikon} {makam.seyir}", C_GREEN)

        for i in reversed(range(self.perde_satir.count())):
            item = self.perde_satir.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        guclu_p = self.diyagram.guclu_p
        for prd in makam.perdeler:
            badge = PerdeBadge(prd, self.naz, makam.perdeler[0], guclu_p)
            self.perde_satir.addWidget(badge)
        self.perde_satir.addStretch()

        self.lbl_araliklar.setText('  '.join(
            f"[{ch.upper()}]" for ch in makam.aralıklar
        ))

        ariza = makam.arıza.strip()
        self.lbl_ariza.setText(ariza if ariza else '')

    def _enstruman_getir(self):
        if self.meclis and self.enstruman is None:
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                self.enstruman = self.meclis.new_part(preset=0)
        return self.enstruman

    def _sure(self):
        hiz = self.tempo_slider.value()
        return [1.2, 0.9, 0.65, 0.45, 0.28][hiz - 1]

    def _tam_dizi_cal(self):
        if not self.makam:
            return
        self._dur()
        self._stop = threading.Event()
        t = threading.Thread(target=self._cal_thread,
                             args=(list(self.makam.perdeler), self._stop),
                             daemon=True)
        t.start()
        self.btn_dur.setEnabled(True)

    def _gucluye_cal(self):
        if not self.makam:
            return
        self._dur()
        prd = self.makam.perdeler
        gp  = self.diyagram.guclu_p
        idx = next((i for i, p in enumerate(prd) if p == gp), len(prd) - 1)
        altta = prd[:idx + 1]
        ustte = prd[idx:]
        self._stop = threading.Event()
        t = threading.Thread(target=self._cal_thread,
                             args=(list(altta) + list(ustte), self._stop),
                             daemon=True)
        t.start()
        self.btn_dur.setEnabled(True)

    def _dur(self):
        self._stop.set()
        self.btn_dur.setEnabled(False)
        self.diyagram.aktif_goster(-1)

    def _cal_thread(self, prd_listesi, stop):
        ens = self._enstruman_getir()
        sure = self._sure()
        for i, prd in enumerate(prd_listesi):
            if stop.is_set():
                break
            self.diyagram.aktif_goster(
                self.makam.perdeler.index(prd) if prd in self.makam.perdeler else -1
            )
            try:
                seslendir(prd, duration=sure, session=self.meclis,
                          instrument=ens, nazariyat=self.naz)
            except Exception as e:
                print(f"Çalma hatası: {e}")
        self.diyagram.aktif_goster(-1)
        self.btn_dur.setEnabled(False)


KART_RENKLERI = [C_GOLD, C_BLUE, C_GREEN, C_PUR, C_ORG, '#26c6da', '#ec407a', C_RED]


class MakamKarti(QFrame):
    def __init__(self, isim, makam_obj, naz, vurgu_kume,
                 meclis, enstruman_fn, sure_fn, renk, kaldir_fn, parent=None):
        super().__init__(parent)
        self.isim = isim
        self.makam = makam_obj
        self.naz = naz
        self.meclis = meclis
        self._enstruman_fn = enstruman_fn
        self._sure_fn = sure_fn
        self._stop = threading.Event()
        self._stop.set()

        self.setStyleSheet(
            f"background:{C_PNL};border-radius:8px;border:1px solid {C_PNL3};"
        )

        ana = QVBoxLayout(self)
        ana.setContentsMargins(10, 8, 10, 8)
        ana.setSpacing(6)

        bas = QHBoxLayout()
        self.lbl_isim = etiket(isim, renk, 14, kalin=True)
        seyir_lbl = etiket(
            f"  {SEYİR_İKON.get(makam_obj.seyir, '')} {makam_obj.seyir}"
            f"  ·  Durak: {makam_obj.durak}  ·  Güçlü: {makam_obj.güçlü}",
            C_TXT3, 11
        )
        btn_kaldir = QPushButton('✕')
        btn_kaldir.setFixedSize(24, 24)
        btn_kaldir.setStyleSheet(
            f"QPushButton{{background:{C_PNL3};color:{C_RED};border:none;"
            f"border-radius:4px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{C_RED};color:white;}}"
        )
        btn_kaldir.clicked.connect(lambda: kaldir_fn(isim))
        bas.addWidget(self.lbl_isim)
        bas.addWidget(seyir_lbl)
        bas.addStretch()
        bas.addWidget(btn_kaldir)
        ana.addLayout(bas)

        self.diyagram = MezanDiyagrami()
        self.diyagram.setFixedHeight(75)
        self.diyagram.makam_yukle(makam_obj, naz, vurgu=vurgu_kume)
        ana.addWidget(self.diyagram)

        cal_satir = QHBoxLayout()
        self.btn_cal = buton('▶  Çal', renk, '#1a2327', 'kucuk')
        self.btn_dur = buton('■', C_PNL3, C_RED, 'kucuk')
        self.btn_dur.setFixedWidth(32)
        self.btn_dur.setEnabled(False)
        cal_satir.addWidget(self.btn_cal)
        cal_satir.addWidget(self.btn_dur)
        cal_satir.addStretch()
        ana.addLayout(cal_satir)

        self.btn_cal.clicked.connect(self._cal)
        self.btn_dur.clicked.connect(self.dur)

    def dur(self):
        self._stop.set()
        self.btn_dur.setEnabled(False)
        self.btn_cal.setEnabled(True)
        self.diyagram.aktif_goster(-1)

    def _cal(self):
        self._stop.set()
        self._stop = threading.Event()
        self.btn_cal.setEnabled(False)
        self.btn_dur.setEnabled(True)
        stop = self._stop
        t = threading.Thread(target=self._cal_thread, args=(stop,), daemon=True)
        t.start()

    def _cal_thread(self, stop):
        ens = self._enstruman_fn()
        sure = self._sure_fn()
        for i, prd in enumerate(self.makam.perdeler):
            if stop.is_set():
                break
            self.diyagram.aktif_goster(i)
            try:
                seslendir(prd, duration=sure, session=self.meclis,
                          instrument=ens, nazariyat=self.naz)
            except Exception as e:
                print(f"Kart çalma hatası: {e}")
        self.diyagram.aktif_goster(-1)
        self.btn_dur.setEnabled(False)
        self.btn_cal.setEnabled(True)


class MukayeseSekmesi(QWidget):
    def __init__(self, meclis, naz, makam_listesi, parent=None):
        super().__init__(parent)
        self.meclis = meclis
        self.naz    = naz
        self.makam_listesi = list(makam_listesi)
        self._enstruman = None
        self._secili_isimler = []
        self._kartlar = []
        self._sirayla_stop = threading.Event()
        self._sirayla_stop.set()
        self.setStyleSheet(f"background:{C_BG};")
        self._kurulum()

    def _kurulum(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(16, 12, 16, 12)
        ana.setSpacing(8)

        ust = QHBoxLayout()
        ust.setSpacing(8)

        self.combo_ekle = QComboBox()
        self.combo_ekle.addItems(self.makam_listesi)
        self.combo_ekle.setStyleSheet(
            f"QComboBox{{background:{C_PNL3};color:{C_TXT};padding:5px;"
            f"border-radius:5px;font-size:13px;min-width:150px;}}"
            f"QComboBox::drop-down{{border:0;}}"
        )
        btn_ekle = buton('+ Ekle', C_GREEN, '#1a2327')
        btn_ekle.clicked.connect(self._makam_ekle)
        btn_temizle = buton('Temizle', C_PNL3, C_RED, 'kucuk')
        btn_temizle.clicked.connect(self._hepsini_kaldir)

        self.btn_sirayla = buton('▶▶  Sırayla Çal', C_PNL3, C_TXT)
        self.btn_sirayla.setEnabled(False)
        self.btn_dur_hepsi = buton('■  Dur', C_PNL3, C_RED, 'kucuk')
        self.btn_dur_hepsi.setEnabled(False)

        self.hiz_slider = QSlider(Qt.Horizontal)
        self.hiz_slider.setRange(1, 5)
        self.hiz_slider.setValue(3)
        self.hiz_slider.setFixedWidth(80)
        self.hiz_slider.setStyleSheet(
            f"QSlider::groove:horizontal{{background:{C_PNL3};height:4px;border-radius:2px;}}"
            f"QSlider::handle:horizontal{{background:{C_BLUE};width:12px;height:12px;margin:-4px 0;border-radius:6px;}}"
        )

        ust.addWidget(etiket('Makam:', C_TXT2, 12))
        ust.addWidget(self.combo_ekle)
        ust.addWidget(btn_ekle)
        ust.addWidget(btn_temizle)
        ust.addStretch()
        ust.addWidget(self.btn_sirayla)
        ust.addWidget(self.btn_dur_hepsi)
        ust.addWidget(etiket('Hız:', C_TXT3, 10))
        ust.addWidget(self.hiz_slider)
        ana.addLayout(ust)

        ana.addWidget(ayrac())

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            f"QScrollArea{{background:{C_BG};border:none;}}"
            f"QScrollBar:vertical{{background:{C_PNL3};width:8px;border-radius:4px;}}"
            f"QScrollBar::handle:vertical{{background:{C_PNL};border-radius:4px;}}"
        )
        self.kart_container = QWidget()
        self.kart_container.setStyleSheet(f"background:{C_BG};")
        self.kart_layout = QVBoxLayout(self.kart_container)
        self.kart_layout.setSpacing(8)
        self.kart_layout.setContentsMargins(0, 0, 4, 0)
        self.kart_layout.addStretch()
        self.scroll.setWidget(self.kart_container)
        ana.addWidget(self.scroll, stretch=1)

        ana.addWidget(ayrac())

        istat_satir = QHBoxLayout()
        istat_satir.setSpacing(8)
        self.k_sayi    = KartBilgi('Seçili Makam', '0', C_ORG)
        self.k_ortaklar = KartBilgi('Ortak Perdeler', '—', C_GREEN)
        self.k_benzerl  = KartBilgi('Ort. Benzerlik', '—', C_PUR)
        self.k_seyir    = KartBilgi('Seyir Türleri', '—', C_BLUE)
        for k in (self.k_sayi, self.k_ortaklar, self.k_benzerl, self.k_seyir):
            istat_satir.addWidget(k)
        ana.addLayout(istat_satir)

        self.lbl_detay = etiket('', C_TXT2, 11)
        self.lbl_detay.setWordWrap(True)
        ana.addWidget(self.lbl_detay)

        self.btn_sirayla.clicked.connect(self._sirayla_cal)
        self.btn_dur_hepsi.clicked.connect(self._dur_hepsi)

    def makam_listesini_guncelle(self, liste):
        self.makam_listesi = list(liste)
        mevcut = self.combo_ekle.currentText()
        self.combo_ekle.clear()
        self.combo_ekle.addItems(liste)
        if mevcut in liste:
            self.combo_ekle.setCurrentText(mevcut)

    def _enstruman_getir(self):
        if self.meclis and self._enstruman is None:
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                self._enstruman = self.meclis.new_part(preset=0)
        return self._enstruman

    def _sure(self):
        h = self.hiz_slider.value()
        return [1.2, 0.85, 0.6, 0.42, 0.25][h - 1]

    def _perde_kume(self, makam):
        sonuc = set()
        for p in makam.perdeler:
            prts = p.split(',')
            sonuc.add((prts[0], prts[1]))
        return sonuc

    def _makam_ekle(self):
        isim = self.combo_ekle.currentText()
        if not isim or isim in self._secili_isimler:
            return
        try:
            Makam(isim=isim, nazariyat=self.naz)
        except Exception as e:
            self.lbl_detay.setText(f'Hata: {e}')
            return
        self._secili_isimler.append(isim)
        self._yeniden_ciz()

    def _makam_kaldir(self, isim):
        if isim in self._secili_isimler:
            self._secili_isimler.remove(isim)
        self._yeniden_ciz()

    def _hepsini_kaldir(self):
        self._dur_hepsi()
        self._secili_isimler.clear()
        self._yeniden_ciz()

    def _yeniden_ciz(self):
        self._dur_hepsi()
        for kart in self._kartlar:
            self.kart_layout.removeWidget(kart)
            kart.deleteLater()
        self._kartlar.clear()

        if not self._secili_isimler:
            self._istatistik_guncelle([])
            self.btn_sirayla.setEnabled(False)
            return

        makamlar = []
        for isim in self._secili_isimler:
            try:
                makamlar.append(Makam(isim=isim, nazariyat=self.naz))
            except Exception:
                pass

        if makamlar:
            ortak = self._perde_kume(makamlar[0])
            for m in makamlar[1:]:
                ortak &= self._perde_kume(m)
        else:
            ortak = set()

        vurgu = {f"{e},{k},0" for e, k in ortak}

        son = self.kart_layout.takeAt(self.kart_layout.count() - 1)
        for i, (isim, makam) in enumerate(zip(self._secili_isimler, makamlar)):
            renk = KART_RENKLERI[i % len(KART_RENKLERI)]
            kart = MakamKarti(
                isim, makam, self.naz, vurgu,
                self.meclis, self._enstruman_getir, self._sure,
                renk, self._makam_kaldir
            )
            self._kartlar.append(kart)
            self.kart_layout.addWidget(kart)
        self.kart_layout.addStretch()

        self._istatistik_guncelle(makamlar, ortak)
        self.btn_sirayla.setEnabled(len(makamlar) > 0)

    def _istatistik_guncelle(self, makamlar, ortak=None):
        self.k_sayi.guncelle(str(len(makamlar)), C_ORG)
        if not makamlar:
            self.k_ortaklar.guncelle('—', C_GREEN)
            self.k_benzerl.guncelle('—', C_PUR)
            self.k_seyir.guncelle('—', C_BLUE)
            self.lbl_detay.setText('')
            return

        def perde_ismi(esas, koma):
            try:
                return self.naz.perdeden_isme(f'{esas},{koma},0')
            except Exception:
                return esas.capitalize()

        ortak_str = ', '.join(perde_ismi(e, k) for e, k in ortak) if ortak is not None else '—'
        self.k_ortaklar.guncelle(ortak_str or 'Yok', C_GREEN)

        if len(makamlar) >= 2:
            toplam_ben, adet = 0, 0
            for i in range(len(makamlar)):
                for j in range(i + 1, len(makamlar)):
                    k1 = self._perde_kume(makamlar[i])
                    k2 = self._perde_kume(makamlar[j])
                    birlesen = k1 | k2
                    if birlesen:
                        toplam_ben += 100 * len(k1 & k2) / len(birlesen)
                    adet += 1
            ort_ben = int(toplam_ben / adet) if adet else 0
            self.k_benzerl.guncelle(f'%{ort_ben}', C_PUR)
        else:
            self.k_benzerl.guncelle('—', C_PUR)

        seyirler = set(m.seyir for m in makamlar)
        self.k_seyir.guncelle(', '.join(sorted(seyirler)), C_BLUE)

        detay_satirlar = [
            f"{m.isim}: durak={m.durak}, güçlü={m.güçlü}, seyir={m.seyir}"
            for m in makamlar
        ]
        self.lbl_detay.setText('\n'.join(detay_satirlar))

    def _dur_hepsi(self):
        self._sirayla_stop.set()
        for kart in self._kartlar:
            kart.dur()
        self.btn_dur_hepsi.setEnabled(False)

    def _sirayla_cal(self):
        if not self._kartlar:
            return
        self._dur_hepsi()
        self._sirayla_stop = threading.Event()
        self.btn_dur_hepsi.setEnabled(True)
        self.btn_sirayla.setEnabled(False)
        stop = self._sirayla_stop
        kartlar = list(self._kartlar)
        t = threading.Thread(target=self._sirayla_thread, args=(kartlar, stop), daemon=True)
        t.start()

    def _sirayla_thread(self, kartlar, stop):
        ens = self._enstruman_getir()
        sure = self._sure()
        for kart in kartlar:
            if stop.is_set():
                break
            for i, prd in enumerate(kart.makam.perdeler):
                if stop.is_set():
                    break
                kart.diyagram.aktif_goster(i)
                try:
                    seslendir(prd, duration=sure, session=self.meclis,
                              instrument=ens, nazariyat=self.naz)
                except Exception as e:
                    print(f"Sırayla çalma hatası: {e}")
            kart.diyagram.aktif_goster(-1)
            if not stop.is_set():
                time.sleep(0.4)
        self.btn_dur_hepsi.setEnabled(False)
        self.btn_sirayla.setEnabled(True)


class TalimSekmesi(QWidget):
    def __init__(self, meclis, naz, makam_listesi, parent=None):
        super().__init__(parent)
        self.meclis = meclis
        self.naz    = naz
        self.tum_makamlar = list(makam_listesi)
        self.secili_makamlar = list(makam_listesi)
        self._enstruman = None
        self._stop   = threading.Event()
        self._stop.set()
        self._soru_makam = None
        self._dogru_cevap = ''
        self._skor_dogru = 0
        self._skor_toplam = 0
        self.setStyleSheet(f"background:{C_BG};")
        self._kurulum()

    def _kurulum(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(16, 12, 16, 12)
        ana.setSpacing(14)

        self.sekmeler = QTabWidget()
        self.sekmeler.setStyleSheet(f"""
            QTabWidget::pane {{ background:{C_PNL}; border:1px solid {C_PNL3}; border-radius:8px; }}
            QTabBar::tab {{ background:{C_PNL3}; color:{C_TXT2}; padding:7px 18px; margin-right:2px; border-radius:4px; font-size:12px; }}
            QTabBar::tab:selected {{ background:{C_BLUE}; color:#000; font-weight:bold; }}
        """)

        self.sekmeler.addTab(self._makam_bul_sekme(), '🎵 Makam Bul')
        self.sekmeler.addTab(self._dizi_talim_sekme(), '🎹 Dizi Talimi')
        ana.addWidget(self.sekmeler)

    def _makam_bul_sekme(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{C_PNL};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        ust = QHBoxLayout()
        self.lbl_skor = etiket('Skor: 0 / 0', C_TXT2, 12)
        self.btn_sifirla = buton('Sıfırla', C_PNL3, C_TXT, 'kucuk')
        self.btn_sifirla.clicked.connect(self._skor_sifirla)
        ust.addWidget(self.lbl_skor)
        ust.addStretch()
        ust.addWidget(etiket('Güçlük:', C_TXT3, 11))
        self.combo_gucl = QComboBox()
        self.combo_gucl.addItems(['Kolay (Tam dizi)', 'Orta (5 perde)', 'Zor (3 perde)'])
        self.combo_gucl.setStyleSheet(f"QComboBox{{background:{C_PNL3};color:{C_TXT};padding:4px;border-radius:4px;font-size:11px;}}QComboBox::drop-down{{border:0;}}")
        ust.addWidget(self.combo_gucl)
        ust.addWidget(self.btn_sifirla)
        lay.addLayout(ust)

        self.lbl_soru = etiket('Bir makam çalınacak. Hangisi olduğunu tahmin edin.', C_TXT2, 13)
        self.lbl_soru.setWordWrap(True)
        self.lbl_soru.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_soru)

        self.btn_yeni = buton('▶  Yeni Soru', C_BLUE, '#000', 'buyuk')
        self.btn_tekrar = buton('↺  Tekrar Dinle', C_PNL3, C_TXT, 'kucuk')
        self.btn_tekrar.setEnabled(False)

        cal_satir = QHBoxLayout()
        cal_satir.addStretch()
        cal_satir.addWidget(self.btn_yeni)
        cal_satir.addWidget(self.btn_tekrar)
        cal_satir.addStretch()
        lay.addLayout(cal_satir)

        self.cevap_grid = QGridLayout()
        self.cevap_grid.setSpacing(8)
        self.cevap_butonlari = []
        for i in range(4):
            b = buton(f'—', C_PNL3, C_TXT, 'buyuk')
            b.setEnabled(False)
            b.setFixedHeight(48)
            r, c = divmod(i, 2)
            self.cevap_grid.addWidget(b, r, c)
            self.cevap_butonlari.append(b)
        lay.addLayout(self.cevap_grid)

        self.lbl_geri_bildirim = etiket('', C_TXT, 15, kalin=True)
        self.lbl_geri_bildirim.setAlignment(Qt.AlignCenter)
        self.lbl_geri_bildirim.setWordWrap(True)
        lay.addWidget(self.lbl_geri_bildirim)
        lay.addStretch()

        self.btn_yeni.clicked.connect(self._yeni_soru)
        self.btn_tekrar.clicked.connect(self._tekrar_dinle)
        return w

    def _dizi_talim_sekme(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{C_PNL};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        ust = QHBoxLayout()
        ust.addWidget(etiket('Makam:', C_TXT2, 12))
        self.combo_talim = QComboBox()
        self.combo_talim.addItems(self.tum_makamlar)
        self.combo_talim.setStyleSheet(f"QComboBox{{background:{C_PNL3};color:{C_TXT};padding:5px;border-radius:5px;font-size:13px;min-width:160px;}}QComboBox::drop-down{{border:0;}}")
        ust.addWidget(self.combo_talim)
        ust.addStretch()

        self.talim_hiz = QSlider(Qt.Horizontal)
        self.talim_hiz.setRange(1, 5)
        self.talim_hiz.setValue(2)
        self.talim_hiz.setFixedWidth(80)
        self.talim_hiz.setStyleSheet(f"QSlider::groove:horizontal{{background:{C_PNL3};height:4px;border-radius:2px;}}QSlider::handle:horizontal{{background:{C_BLUE};width:12px;height:12px;margin:-4px 0;border-radius:6px;}}")
        ust.addWidget(etiket('Tempo:', C_TXT3, 11))
        ust.addWidget(self.talim_hiz)

        self.btn_talim_cal  = buton('▶  Çal', C_GREEN, '#000')
        self.btn_talim_dur  = buton('■  Dur', C_PNL3, C_RED, 'kucuk')
        self.btn_talim_dur.setEnabled(False)
        ust.addWidget(self.btn_talim_cal)
        ust.addWidget(self.btn_talim_dur)
        lay.addLayout(ust)

        self.talim_diyagram = MezanDiyagrami()
        lay.addWidget(self.talim_diyagram)

        self.lbl_talim_nota = etiket('', C_GOLD, 26, kalin=True)
        self.lbl_talim_nota.setAlignment(Qt.AlignCenter)
        self.lbl_talim_perde = etiket('', C_TXT2, 16)
        self.lbl_talim_perde.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_talim_nota)
        lay.addWidget(self.lbl_talim_perde)
        lay.addStretch()

        self.btn_talim_cal.clicked.connect(self._talim_baslat)
        self.btn_talim_dur.clicked.connect(self._talim_dur)
        self.combo_talim.currentIndexChanged.connect(self._talim_makam_degisti)
        self._talim_makam_degisti()
        return w

    def makam_listesini_guncelle(self, liste):
        self.secili_makamlar = list(liste)
        self.tum_makamlar    = list(liste)
        self.combo_talim.clear()
        self.combo_talim.addItems(liste)

    def _enstruman_getir(self):
        if self.meclis and self._enstruman is None:
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                self._enstruman = self.meclis.new_part(preset=0)
        return self._enstruman

    def _skor_sifirla(self):
        self._skor_dogru = 0
        self._skor_toplam = 0
        self.lbl_skor.setText('Skor: 0 / 0')

    def _yeni_soru(self):
        if len(self.secili_makamlar) < 4:
            self.lbl_geri_bildirim.setText('En az 4 makam seçili olmalı.')
            return
        self._stop_cal()
        self.btn_yeni.setEnabled(False)
        for b in self.cevap_butonlari:
            b.setEnabled(False)
            b.setText('—')
            b.setStyleSheet(buton('').styleSheet())
        self.lbl_geri_bildirim.setText('')
        self.lbl_soru.setText('Dinleniyor…')

        self._soru_makam = Makam(
            isim=random.choice(self.secili_makamlar), nazariyat=self.naz
        )
        self._dogru_cevap = self._soru_makam.isim
        self._stop = threading.Event()
        t = threading.Thread(target=self._soru_cal_thread, daemon=True)
        t.start()

    def _soru_cal_thread(self):
        gucl_idx = self.combo_gucl.currentIndex()
        n_perde  = {0: None, 1: 5, 2: 3}[gucl_idx]
        perdeler = self._soru_makam.perdeler
        if n_perde:
            perdeler = perdeler[:n_perde]

        ens  = self._enstruman_getir()
        sure = 0.55
        for prd in perdeler:
            if self._stop.is_set():
                return
            try:
                seslendir(prd, duration=sure, session=self.meclis,
                          instrument=ens, nazariyat=self.naz)
            except Exception as e:
                print(f"Talim çalma hatası: {e}")

        if self._stop.is_set():
            return

        yanlis_secim = [m for m in self.secili_makamlar if m != self._dogru_cevap]
        random.shuffle(yanlis_secim)
        secenekler = [self._dogru_cevap] + yanlis_secim[:3]
        random.shuffle(secenekler)

        for i, b in enumerate(self.cevap_butonlari):
            metin = secenekler[i] if i < len(secenekler) else '—'
            b.setText(metin)
            b.setEnabled(True)
            try:
                b.clicked.disconnect()
            except RuntimeError:
                pass
            b.clicked.connect(lambda checked, m=metin: self._cevap_ver(m))

        self.btn_tekrar.setEnabled(True)
        self.lbl_soru.setText('Hangi makam?')

    def _cevap_ver(self, secim):
        for b in self.cevap_butonlari:
            b.setEnabled(False)
        self._skor_toplam += 1

        for b in self.cevap_butonlari:
            if b.text() == self._dogru_cevap:
                b.setStyleSheet(b.styleSheet() + f"background:{C_GREEN}; color:#000;")
            elif b.text() == secim and secim != self._dogru_cevap:
                b.setStyleSheet(b.styleSheet() + f"background:{C_RED}; color:#fff;")

        if secim == self._dogru_cevap:
            self._skor_dogru += 1
            self.lbl_geri_bildirim.setText(f'✓  Doğru!  —  {self._dogru_cevap}')
            self.lbl_geri_bildirim.setStyleSheet(f"color:{C_GREEN};font-size:16px;font-weight:bold;background:transparent;border:none;")
        else:
            self.lbl_geri_bildirim.setText(f'✗  Yanlış.  Doğru cevap: {self._dogru_cevap}')
            self.lbl_geri_bildirim.setStyleSheet(f"color:{C_RED};font-size:16px;font-weight:bold;background:transparent;border:none;")

        self.lbl_skor.setText(f'Skor: {self._skor_dogru} / {self._skor_toplam}')
        self.btn_yeni.setEnabled(True)
        self.btn_tekrar.setEnabled(False)

    def _tekrar_dinle(self):
        if not self._soru_makam:
            return
        self._stop.set()
        self._stop = threading.Event()
        t = threading.Thread(target=self._soru_cal_thread, daemon=True)
        t.start()

    def _stop_cal(self):
        self._stop.set()

    def _talim_makam_degisti(self):
        isim = self.combo_talim.currentText()
        if not isim:
            return
        try:
            m = Makam(isim=isim, nazariyat=self.naz)
            self.talim_diyagram.makam_yukle(m, self.naz)
            self._talim_makam = m
            self.lbl_talim_nota.setText('')
            self.lbl_talim_perde.setText('')
        except Exception as e:
            print(f"Talim makam hatası: {e}")

    def _talim_sure(self):
        h = self.talim_hiz.value()
        return [1.2, 0.85, 0.6, 0.42, 0.25][h - 1]

    def _talim_baslat(self):
        if not hasattr(self, '_talim_makam'):
            return
        self._stop.set()
        self._stop = threading.Event()
        self.btn_talim_dur.setEnabled(True)
        self.btn_talim_cal.setEnabled(False)
        t = threading.Thread(target=self._talim_thread, daemon=True)
        t.start()

    def _talim_dur(self):
        self._stop.set()
        self.btn_talim_dur.setEnabled(False)
        self.btn_talim_cal.setEnabled(True)
        self.talim_diyagram.aktif_goster(-1)
        self.lbl_talim_nota.setText('')
        self.lbl_talim_perde.setText('')

    def _talim_thread(self):
        makam = self._talim_makam
        perdeler = makam.perdeler
        ens  = self._enstruman_getir()
        sure = self._talim_sure()

        for i, prd in enumerate(perdeler):
            if self._stop.is_set():
                break
            self.talim_diyagram.aktif_goster(i)
            prts = prd.split(',')
            nota = prts[0].capitalize()
            koma = int(prts[1]) if len(prts) > 1 else 0
            koma_str = (f'+{koma}' if koma > 0 else str(koma)) if koma != 0 else ''
            try:
                isim = self.naz.perdeden_isme(prd)
            except Exception:
                isim = nota
            self.lbl_talim_nota.setText(nota + koma_str)
            self.lbl_talim_perde.setText(isim)
            try:
                seslendir(prd, duration=sure, session=self.meclis,
                          instrument=ens, nazariyat=self.naz)
            except Exception as e:
                print(f"Talim çalma hatası: {e}")

        if not self._stop.is_set():
            self.talim_diyagram.aktif_goster(-1)
            self.lbl_talim_nota.setText('')
            self.lbl_talim_perde.setText('Tamamlandı')
            self.btn_talim_dur.setEnabled(False)
            self.btn_talim_cal.setEnabled(True)


class FiltrePaneli(QWidget):
    makam_secildi   = Signal(str)
    filtre_degisti  = Signal(list)

    def __init__(self, naz: Nazariyat, parent=None):
        super().__init__(parent)
        self.naz = naz
        self.setFixedWidth(260)
        self.setStyleSheet(f"background:{C_PNL};")
        self._tum_makamlar = naz.dizi['isim'].tolist()
        self._kurulum()
        self._filtrele()

    def _kurulum(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(8)

        lay.addWidget(etiket('⚗  Filtrele', C_TXT, 14, kalin=True))

        self.arama = QLineEdit()
        self.arama.setPlaceholderText('Makam ara…')
        self.arama.setStyleSheet(f"background:{C_PNL3};color:{C_TXT};border:1px solid #546e7a;border-radius:5px;padding:5px;font-size:12px;")
        self.arama.textChanged.connect(self._filtrele)
        lay.addWidget(self.arama)

        filtre_grup = QGroupBox('Özellikler')
        filtre_grup.setStyleSheet(f"QGroupBox{{color:{C_TXT2};font-size:11px;border:1px solid {C_PNL3};border-radius:6px;margin-top:8px;padding-top:6px;}}QGroupBox::title{{subcontrol-origin:margin;left:8px;padding:0 4px;}}")
        fg_lay = QVBoxLayout(filtre_grup)
        fg_lay.setSpacing(5)

        self.filtreler = {}
        dz = self.naz.dizi

        secenekler = {
            'Durak':     ['(Tümü)'] + sorted(dz['durak'].unique().tolist()),
            'Güçlü':     ['(Tümü)'] + sorted(dz['güçlü'].unique().tolist()),
            'Seyir':     ['(Tümü)'] + sorted(dz['seyir'].unique().tolist()),
            'Alt Çeşni': ['(Tümü)'] + sorted({v.split(',')[0] for v in dz['alt'].tolist()}),
            'Üst Çeşni': ['(Tümü)'] + sorted({v.split(',')[0] for v in dz['üst'].tolist()}),
        }

        for ad, sec_list in secenekler.items():
            sat = QHBoxLayout()
            sat.addWidget(etiket(ad + ':', C_TXT3, 10))
            cb = QComboBox()
            cb.addItems(sec_list)
            cb.setStyleSheet(f"QComboBox{{background:{C_PNL3};color:{C_TXT};padding:3px;border-radius:4px;font-size:11px;}}QComboBox::drop-down{{border:0;}}")
            cb.currentIndexChanged.connect(self._filtrele)
            sat.addWidget(cb)
            fg_lay.addLayout(sat)
            self.filtreler[ad] = cb

        lay.addWidget(filtre_grup)
        lay.addWidget(ayrac())

        lay.addWidget(etiket('Makamlar', C_TXT2, 12, kalin=True))

        self.makam_listesi = QListWidget()
        self.makam_listesi.setStyleSheet(f"""
            QListWidget {{background:{C_PNL2};color:{C_TXT};border:none;border-radius:6px;font-size:12px;}}
            QListWidget::item {{padding:5px 8px;}}
            QListWidget::item:selected {{background:{C_BLUE};color:#000;border-radius:4px;}}
            QListWidget::item:hover {{background:{C_PNL3};}}
        """)
        self.makam_listesi.currentTextChanged.connect(self._makam_sec)
        lay.addWidget(self.makam_listesi, stretch=1)

        self.lbl_sayac = etiket('', C_TXT3, 10)
        lay.addWidget(self.lbl_sayac)

    def _filtrele(self):
        arama_txt = self.arama.text().strip().lower()
        dz = self.naz.dizi
        maske = dz['isim'].notna()

        d_sec  = self.filtreler['Durak'].currentText()
        g_sec  = self.filtreler['Güçlü'].currentText()
        s_sec  = self.filtreler['Seyir'].currentText()
        al_sec = self.filtreler['Alt Çeşni'].currentText()
        us_sec = self.filtreler['Üst Çeşni'].currentText()

        if d_sec  != '(Tümü)': maske &= (dz['durak'] == d_sec)
        if g_sec  != '(Tümü)': maske &= (dz['güçlü'] == g_sec)
        if s_sec  != '(Tümü)': maske &= (dz['seyir'] == s_sec)
        if al_sec != '(Tümü)': maske &= dz['alt'].str.startswith(al_sec)
        if us_sec != '(Tümü)': maske &= dz['üst'].str.startswith(us_sec)

        filtreli = dz.loc[maske, 'isim'].tolist()

        if arama_txt:
            filtreli = [m for m in filtreli if arama_txt in m.lower()]

        onceki = self.makam_listesi.currentItem()
        onceki_isim = onceki.text() if onceki else None

        self.makam_listesi.clear()
        for isim in filtreli:
            self.makam_listesi.addItem(QListWidgetItem(isim))

        self.lbl_sayac.setText(f'{len(filtreli)} makam')

        if onceki_isim in filtreli:
            for i in range(self.makam_listesi.count()):
                if self.makam_listesi.item(i).text() == onceki_isim:
                    self.makam_listesi.setCurrentRow(i)
                    break
        elif filtreli:
            self.makam_listesi.setCurrentRow(0)

        self.filtre_degisti.emit(filtreli)

    def _makam_sec(self, isim):
        if isim:
            self.makam_secildi.emit(isim)

    def secili_makamlar(self):
        return [self.makam_listesi.item(i).text()
                for i in range(self.makam_listesi.count())]


class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Şebeke-i Musiki  —  Makam Analiz Merkezi')
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(f"background:{C_BG}; color:{C_TXT};")

        self.naz = Nazariyat()
        self.meclis = None
        self._meclis_kur()

        self._kurulum()

    def _meclis_kur(self):
        try:
            from scamp import Session
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                self.meclis = Session(default_soundfont=ses_kutuphanesi())
            self.meclis.master_clock.pool_size = 100
        except Exception as e:
            print(f'Meclis kurulamadı: {e}')

    def _kurulum(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:#2c393f;width:2px;}")

        self.filtre = FiltrePaneli(self.naz)
        splitter.addWidget(self.filtre)

        sag = QWidget()
        sag.setStyleSheet(f"background:{C_BG};")
        sag_lay = QVBoxLayout(sag)
        sag_lay.setContentsMargins(0, 0, 0, 0)
        sag_lay.setSpacing(0)

        baslik_bar = QWidget()
        baslik_bar.setFixedHeight(44)
        baslik_bar.setStyleSheet(f"background:{C_PNL}; border-bottom:1px solid {C_PNL3};")
        bb_lay = QHBoxLayout(baslik_bar)
        bb_lay.setContentsMargins(16, 4, 16, 4)
        self.lbl_makam_baslik = etiket('—', C_GOLD, 18, kalin=True)
        self.lbl_makam_alt = etiket('', C_TXT3, 11)
        bb_lay.addWidget(self.lbl_makam_baslik)
        bb_lay.addWidget(self.lbl_makam_alt)
        bb_lay.addStretch()
        sag_lay.addWidget(baslik_bar)

        tum_makamlar = self.naz.dizi['isim'].tolist()

        self.sekmeler = QTabWidget()
        self.sekmeler.setStyleSheet(f"""
            QTabWidget::pane {{ background:{C_BG}; border:none; }}
            QTabBar::tab {{ background:{C_PNL3}; color:{C_TXT2}; padding:9px 22px;
                            margin-right:2px; border-radius:0; font-size:13px; }}
            QTabBar::tab:selected {{ background:{C_BG}; color:{C_GOLD}; font-weight:bold;
                                     border-bottom:2px solid {C_GOLD}; }}
            QTabBar::tab:hover {{ background:{C_PNL2}; }}
        """)

        self.analiz    = AnalizSekmesi(self.meclis, self.naz)
        self.mukayese  = MukayeseSekmesi(self.meclis, self.naz, tum_makamlar)
        self.talim     = TalimSekmesi(self.meclis, self.naz, tum_makamlar)

        self.sekmeler.addTab(self.analiz,   '🔍 Analiz')
        self.sekmeler.addTab(self.mukayese, '⚖  Mukayese')
        self.sekmeler.addTab(self.talim,    '🎓 Talim')
        sag_lay.addWidget(self.sekmeler, stretch=1)

        splitter.addWidget(sag)
        splitter.setSizes([260, 840])
        self.setCentralWidget(splitter)

        self.filtre.makam_secildi.connect(self._makam_degisti)
        self.filtre.filtre_degisti.connect(self._filtre_guncelle)

        if tum_makamlar:
            self.filtre.makam_listesi.setCurrentRow(0)

    def _makam_degisti(self, isim):
        if not isim:
            return
        try:
            makam = Makam(isim=isim, nazariyat=self.naz)
            self.analiz.makam_goster(makam)

            try:
                durak_isim = self.naz.perdeden_isme(makam.perdeler[0]).strip()
            except Exception:
                durak_isim = makam.durak

            seyir_ikon = SEYİR_İKON.get(makam.seyir, '')
            self.lbl_makam_baslik.setText(isim)
            self.lbl_makam_alt.setText(
                f"  durak: {durak_isim}  ·  güçlü: {makam.güçlü}  ·  seyir: {seyir_ikon} {makam.seyir}"
            )
        except Exception as e:
            print(f'Makam yüklenemedi ({isim}): {e}')

    def _filtre_guncelle(self, liste):
        self.mukayese.makam_listesini_guncelle(liste)
        self.talim.makam_listesini_guncelle(liste)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec())
