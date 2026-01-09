import sys
import threading
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QLabel, QComboBox, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from nazariyat import seslendir, Nazariyat, Makam


class MusikiTusu(QPushButton):
    def __init__(self, klavye_harfi, parent=None):
        super().__init__(parent)
        self.klavye_harfi = klavye_harfi.upper()
        self.ana_pencere = parent
        self.tam_perde = "sol,0,0"

        self.setFixedSize(120, 120)
        self.setStyleSheet(self._normal_stil())

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)

        self.lbl_nota = QLabel("...")
        self.lbl_nota.setAlignment(Qt.AlignCenter)
        self.lbl_nota.setStyleSheet(
            "background-color: transparent; font-weight: bold; font-size: 16px; color: #ffca28;")

        self.lbl_perde = QLabel("...")
        self.lbl_perde.setAlignment(Qt.AlignCenter)
        self.lbl_perde.setStyleSheet(
            "background-color: transparent; font-style: italic; font-size: 11px; color: #b0bec5;")

        self.lbl_tus = QLabel(f"[{self.klavye_harfi}]")
        self.lbl_tus.setAlignment(Qt.AlignCenter)
        self.lbl_tus.setStyleSheet(
            "background-color: transparent; font-weight: bold; font-size: 14px; color: #29b6f6; margin-top: 10px;")

        layout.addWidget(self.lbl_nota)
        layout.addWidget(self.lbl_perde)
        layout.addWidget(self.lbl_tus)

        self.clicked.connect(self.cal)

    def tusu_kur(self, tam_perde):
        self.tam_perde = tam_perde
        parts = tam_perde.split(',')
        nota_adi = parts[0].capitalize() if len(parts) > 0 else "?"

        # Perdenin ismini (Rast, Dügah vb.) bulmak için Nazariyat'ın 'isme' fonksiyonunu kullanıyoruz.
        try:
            perde_ismi = self.ana_pencere.nazariyat.perdeden_isme(tam_perde)
        except:
            perde_ismi = nota_adi

        self.lbl_nota.setText(nota_adi)
        self.lbl_perde.setText(perde_ismi)

    def _normal_stil(self):
        return """
            QPushButton {
                background-color: #37474f; 
                border: 2px solid #546e7a;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #455a64;
                border-color: #78909c;
            }
        """

    def _basili_stil(self):
        return """
            QPushButton {
                background-color: #546e7a;
                border: 2px solid #ffca28;
                border-radius: 8px;
            }
        """

    def bas(self):
        self.setStyleSheet(self._basili_stil())
        self.cal()

    def birak(self):
        self.setStyleSheet(self._normal_stil())

    def cal(self):
        secili_alet = self.ana_pencere.secili_alet_kodu()
        meclis = self.ana_pencere.meclis_getir()
        nazariyat = self.ana_pencere.nazariyat

        t = threading.Thread(target=self._seslendir_wrapper, args=(secili_alet, meclis, nazariyat))
        t.daemon = True
        t.start()

    def _seslendir_wrapper(self, alet_kodu, meclis_objesi, nazariyat_objesi):
        try:
            seslendir(self.tam_perde, duration=0.5, alet=alet_kodu, session=meclis_objesi, nazariyat=nazariyat_objesi)
        except Exception as e:
            print(f"İcra hatası: {e}")


class AnaPencere(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Şebeke-i Musiki")
        self.setStyleSheet("background-color: #263238;")
        self.tus_sozlugu = {}
        self.daimi_meclis = None

        # Nazariyat sınıfını başlatıyoruz. Tüm veriler (dizi, perde, çeşni) hafızaya burada yükleniyor.
        try:
            self.nazariyat = Nazariyat()
        except Exception as e:
            print(f"Nazariyat yüklenemedi: {e}")
            self.nazariyat = None

        self.meclis_kur()

        self.enstrumanlar = {
            "Piyano (Grand)": 0, "Piyano (Rhodes)": 4, "Klavsen": 6,
            "Ney": 77, "Tanbur": 104, "Kanun": 15, "Keman": 40, "Ud": 105
        }
        self.setup_ui()

        # İlk açılışta listenin başındaki makamı yükleyelim
        if self.combo_makam.count() > 0:
            self.combo_makam.setCurrentIndex(0)
            self.makam_degisti()

    def meclis_kur(self):
        if self.daimi_meclis is None:
            try:
                from scamp import Session
                self.daimi_meclis = Session()
            except Exception as e:
                print(f"Meclis hatası: {e}")

    def meclis_getir(self):
        return self.daimi_meclis

    def setup_ui(self):
        ana_layout = QVBoxLayout(self)
        ana_layout.setSpacing(20)
        ana_layout.setContentsMargins(30, 30, 30, 30)

        ust_panel = QFrame()
        ust_layout = QHBoxLayout(ust_panel)
        ust_layout.setContentsMargins(0, 0, 0, 0)

        # --- Alet Seçimi ---
        lbl_secim = QLabel("Saz:")
        lbl_secim.setStyleSheet("color: #eceff1; font-size: 14px; font-weight: bold;")
        self.combo_alet = QComboBox()
        self.combo_alet.addItems(self.enstrumanlar.keys())
        self.combo_alet.setStyleSheet("""
            QComboBox { padding: 5px; border-radius: 5px; background-color: #455a64; color: white; font-size: 14px; min-width: 150px; }
            QComboBox::drop-down { border: 0px; }
        """)

        # --- Makam Seçimi ---
        lbl_makam = QLabel("Makam:")
        lbl_makam.setStyleSheet("color: #eceff1; font-size: 14px; font-weight: bold; margin-left: 15px;")
        self.combo_makam = QComboBox()

        # Nazariyat sınıfının hafızasındaki (self.dizi) makam isimlerini doğrudan alıyoruz.
        if self.nazariyat and hasattr(self.nazariyat, "dizi"):
            makam_listesi = self.nazariyat.dizi["isim"].tolist()
            self.combo_makam.addItems(makam_listesi)

        self.combo_makam.setStyleSheet("""
            QComboBox { padding: 5px; border-radius: 5px; background-color: #455a64; color: white; font-size: 14px; min-width: 150px; }
            QComboBox::drop-down { border: 0px; }
        """)
        self.combo_makam.currentIndexChanged.connect(self.makam_degisti)

        ust_layout.addStretch()
        ust_layout.addWidget(lbl_secim)
        ust_layout.addWidget(self.combo_alet)
        ust_layout.addWidget(lbl_makam)
        ust_layout.addWidget(self.combo_makam)
        ust_layout.addStretch()

        # --- Tuşlar ---
        tus_paneli = QFrame()
        tus_layout = QHBoxLayout(tus_paneli)
        tus_layout.setSpacing(15)

        self.klavye_harfleri = ["A", "S", "D", "F", "G", "H", "J", "K"]
        for harf in self.klavye_harfleri:
            tus = MusikiTusu(harf, parent=self)
            tus_layout.addWidget(tus)
            self.tus_sozlugu[Qt.Key(ord(harf))] = tus

        ana_layout.addWidget(ust_panel)
        ana_layout.addWidget(tus_paneli)
        ana_layout.addStretch()

    def secili_alet_kodu(self):
        secilen_isim = self.combo_alet.currentText()
        return self.enstrumanlar.get(secilen_isim, 0)

    def makam_degisti(self):
        secilen_makam = self.combo_makam.currentText()
        if not secilen_makam: return

        try:
            # Nazariyat sınıfının içindeki 'diziye' ve 'perdeye' fonksiyonlarına güveniyoruz.
            # Harici hiçbir müdahale yok, sadece ismi veriyoruz, o hallediyor.
            makam = Makam(isim=secilen_makam, nazariyat=self.nazariyat)
            perdeler = makam.perdeler

            for i, harf in enumerate(self.klavye_harfleri):
                key = Qt.Key(ord(harf))
                if i < len(perdeler):
                    self.tus_sozlugu[key].tusu_kur(perdeler[i])
                else:
                    self.tus_sozlugu[key].tusu_kur("sol,0,0")
        except Exception as e:
            print(f"Makam teşkili hatası: {e}")

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in self.tus_sozlugu:
            if not event.isAutoRepeat():
                self.tus_sozlugu[key].bas()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        key = event.key()
        if key in self.tus_sozlugu:
            if not event.isAutoRepeat():
                self.tus_sozlugu[key].birak()
        else:
            super().keyReleaseEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec())