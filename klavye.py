import sys
import threading
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QLabel, QComboBox, QFrame)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QKeyEvent, QFont
from nazariyat import seslendir, tasfiye


class MusikiTusu(QPushButton):
    def __init__(self, klavye_harfi, nota_adi, perde_ismi, oktav, parent=None):
        super().__init__(parent)
        self.klavye_harfi = klavye_harfi.upper()
        self.nota_adi = nota_adi
        self.perde_ismi = perde_ismi
        self.oktav = oktav
        self.ana_pencere = parent

        # Tuş ebadını kare (murabba) yapıyoruz
        self.setFixedSize(120, 120)
        self.setStyleSheet(self._normal_stil())

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)

        # Nota İsmi (Sol, La vs.)
        lbl_nota = QLabel(nota_adi.capitalize())
        lbl_nota.setAlignment(Qt.AlignCenter)
        lbl_nota.setStyleSheet(
            "background-color: transparent; font-weight: bold; font-size: 16px; color: #ffca28;")  # Altın sarısı

        # Perde İsmi (Rast, Dügah vs.)
        lbl_perde = QLabel(perde_ismi)
        lbl_perde.setAlignment(Qt.AlignCenter)
        lbl_perde.setStyleSheet(
            "background-color: transparent; font-style: italic; font-size: 11px; color: #b0bec5;")  # Açık gri

        # Klavye Tuşu Harfi
        lbl_tus = QLabel(f"[{self.klavye_harfi}]")
        lbl_tus.setAlignment(Qt.AlignCenter)
        lbl_tus.setStyleSheet(
            "background-color: transparent; font-weight: bold; font-size: 14px; color: #29b6f6; margin-top: 10px;")  # Açık mavi

        layout.addWidget(lbl_nota)
        layout.addWidget(lbl_perde)
        layout.addWidget(lbl_tus)

        self.clicked.connect(self.cal)

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
        # Ana pencereden alet ve oturum bilgisini alıyoruz
        secili_alet = self.ana_pencere.secili_alet_kodu()
        meclis = self.ana_pencere.meclis_getir()

        # İcra işlemini ayrı bir izlekte (thread) yapıyoruz ki arayüz donmasın
        t = threading.Thread(target=self._seslendir_wrapper, args=(secili_alet, meclis))
        t.daemon = True
        t.start()

    def _seslendir_wrapper(self, alet_kodu, meclis_objesi):
        try:
            # Sizin seslendir fonksiyonunuza mevcut oturumu (session) yolluyoruz.
            seslendir(self.nota_adi, oktav=self.oktav, duration=0.5, alet=alet_kodu, session=meclis_objesi)
        except Exception as e:
            print(f"İcra hatası: {e}")


class AnaPencere(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Şebeke-i Musiki")  # Pencere Başlığı
        self.setStyleSheet("background-color: #263238;")  # Koyu Zemin
        self.tus_sozlugu = {}

        # Musiki Meclisini (Session) burada bir kez kuruyoruz.
        # Böylece seslendir fonksiyonuna hep aynı oturumu göndereceğiz.
        # WinError 6 hatasının önüne geçmek için elzemdir.
        try:
            from scamp import Session
            self.daimi_meclis = Session()
            print("Musiki meclisi teşkil edildi.")
        except Exception as e:
            print(f"Meclis kurulamadı: {e}")
            self.daimi_meclis = None

        self.enstrumanlar = {
            "Piyano (Grand)": 0,
            "Piyano (Rhodes)": 4,
            "Klavsen": 6,
            "Ney (Shakuhachi)": 77,
            "Tanbur/Ud (Sitar)": 104,
            "Kanun/Santur (Dulcimer)": 15,
            "Keman": 40,
            "Viyolonsel": 42,
            "Klasik Gitar": 24,
            "Kudüm (Taiko)": 116
        }
        self.setup_ui()

    def meclis_getir(self):
        return self.daimi_meclis

    def setup_ui(self):
        ana_layout = QVBoxLayout(self)
        ana_layout.setSpacing(20)
        ana_layout.setContentsMargins(30, 30, 30, 30)

        # --- ÜST PANEL (Alet Seçimi) ---
        ust_panel = QFrame()
        ust_layout = QHBoxLayout(ust_panel)
        ust_layout.setContentsMargins(0, 0, 0, 0)

        lbl_secim = QLabel("Saz Seçimi:")
        lbl_secim.setStyleSheet("color: #eceff1; font-size: 14px; font-weight: bold;")

        self.combo_alet = QComboBox()
        self.combo_alet.addItems(self.enstrumanlar.keys())
        self.combo_alet.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border-radius: 5px;
                background-color: #455a64;
                color: white;
                font-size: 14px;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: 0px;
            }
        """)

        ust_layout.addStretch()
        ust_layout.addWidget(lbl_secim)
        ust_layout.addWidget(self.combo_alet)
        ust_layout.addStretch()

        # --- ALT PANEL (Tuşlar) ---
        tus_paneli = QFrame()
        tus_layout = QHBoxLayout(tus_paneli)
        tus_layout.setSpacing(15)

        # Klavye Haritası: (Tuş, Nota, Perde, Oktav)
        konfigurasyon = [
            ("A", "sol", "Rast", 0),
            ("S", "la", "Dügah", 0),
            ("D", "si", "Segah", 0),
            ("F", "do", "Çargah", 0),
            ("G", "re", "Neva", 0),
            ("H", "mi", "Hüseyni", 0),
            ("J", "fa", "Acem", 0),
            ("K", "sol", "Gerdaniye", 1),
        ]

        for harf, nota, perde, oktav in konfigurasyon:
            tus = MusikiTusu(harf, nota, perde, oktav, parent=self)
            tus_layout.addWidget(tus)
            self.tus_sozlugu[Qt.Key(ord(harf))] = tus

        ana_layout.addWidget(ust_panel)
        ana_layout.addWidget(tus_paneli)
        ana_layout.addStretch()

    def secili_alet_kodu(self):
        secilen_isim = self.combo_alet.currentText()
        return self.enstrumanlar.get(secilen_isim, 0)

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
    import os

    # Gerekli dosyaların kontrolü
    if not os.path.exists("perde.txt"):
        with open("perde.txt", "w", encoding="utf-8") as f:
            f.write("sol,0,0: R a s t\nla,0,0: D ü g a h")
    if not os.path.exists("cesni.txt"):
        with open("cesni.txt", "w", encoding="utf-8") as f:
            f.write("Rast:sol,0,0-la,0,0")

    app = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec())