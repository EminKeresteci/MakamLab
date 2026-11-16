"""Canli ney sentezi: taksim.seslendir recetesinin tusla calinan, blok blok ureten hali."""
import queue

import numpy as np

ORAN = 44100
BLOK = 512
KAZANC = 0.26


class _Ortalama:
    def __init__(self, n):
        self.n = max(1, int(n))
        self.kuyruk = np.zeros(self.n)

    def __call__(self, x):
        c = np.cumsum(np.concatenate([self.kuyruk, x]))
        self.kuyruk = np.concatenate([self.kuyruk, x])[-self.n:]
        return (c[self.n:] - c[:-self.n]) / self.n


class CanliNey:
    def __init__(self, oran=ORAN, blok=BLOK, yanki=True, kazanc=KAZANC, tohum=0):
        self.oran = oran
        self.blok = blok
        self.kazanc = kazanc
        self.rnd = np.random.default_rng(tohum)
        self.istekler = queue.SimpleQueue()
        self.basili = []
        self.akim = None

        self.kapi = False
        self.zarf = 0.0
        self.hedef = 60.0
        self.cikis = 60.0
        self.simdi = 60.0
        self.kayma_boy = 1
        self.kayma_konum = 1
        self.kayma_bagli = False
        self.nota_yasi = 0
        self.titresim_hizi = 5.0
        self.atak_yasi = 10 ** 9
        self.cukur_yasi = 10 ** 9
        self.faz = 0.0
        self.sapma_faz = self.rnd.uniform(0, 2 * np.pi, 2)

        self.nefes_ort = _Ortalama(oran * 0.01)
        self.his_alcak = _Ortalama(oran / 1500)
        self.his_yumusak = _Ortalama(oran / 9000)

        self.yanki = yanki
        if yanki:
            boy = int(0.5 * oran)
            tepki = self.rnd.standard_normal(boy) * np.exp(-np.arange(boy) / (0.12 * oran))
            tepki *= np.cos(np.linspace(0, np.pi / 2, boy)) ** 2
            tepki = _Ortalama(oran / 6000)(tepki)
            tepki[0] = 0
            tepki /= np.sqrt(np.sum(tepki ** 2))
            self.m = 1 << int(np.ceil(np.log2(blok + boy)))
            self.tepki_f = np.fft.rfft(tepki, self.m)
            self.islak = np.zeros(self.m)

    def bas(self, anahtar, midi):
        self.basili = [(a, m) for a, m in self.basili if a != anahtar] + [(anahtar, midi)]
        self.istekler.put(float(midi))

    def birak(self, anahtar):
        ustte = bool(self.basili) and self.basili[-1][0] == anahtar
        self.basili = [(a, m) for a, m in self.basili if a != anahtar]
        if not self.basili:
            self.istekler.put(None)
        elif ustte:
            self.istekler.put(float(self.basili[-1][1]))

    def sus(self):
        self.basili = []
        self.istekler.put(None)

    def _istek_isle(self):
        while True:
            try:
                midi = self.istekler.get_nowait()
            except queue.Empty:
                return
            if midi is None:
                self.kapi = False
                continue
            bagli = self.kapi or self.zarf > 0.05
            if bagli and midi == self.hedef and self.kapi:
                continue
            self.kayma_bagli = bagli
            if bagli:
                self.cikis = self.simdi
                self.kayma_boy = int(0.07 * self.oran)
                self.cukur_yasi = 0
            else:
                self.cikis = midi - 0.3
                self.kayma_boy = int(0.06 * self.oran)
                self.atak_yasi = 0
            self.hedef = midi
            self.kayma_konum = 0
            self.nota_yasi = 0
            self.titresim_hizi = self.rnd.uniform(4.6, 5.4)
            self.kapi = True

    def _blok(self, n):
        self._istek_isle()
        oran = self.oran
        sira = np.arange(n)

        p = np.clip((self.kayma_konum + sira + 1) / self.kayma_boy, 0, 1)
        sekil = 0.5 - 0.5 * np.cos(np.pi * p) if self.kayma_bagli else 1 - np.cos(np.pi / 2 * p)
        midi = self.cikis + (self.hedef - self.cikis) * sekil
        self.kayma_konum += n
        self.simdi = float(midi[-1])

        t = (self.nota_yasi + sira) / oran
        midi = midi + 0.12 * np.clip((t - 0.3) / 0.6, 0, 1) * np.sin(2 * np.pi * self.titresim_hizi * t)
        self.nota_yasi += n

        adim = 2 * np.pi * np.array([0.37, 0.83]) / oran
        sf = self.sapma_faz[:, None] + adim[:, None] * (sira + 1)
        midi = midi + 0.025 * np.sin(sf[0]) + 0.02 * np.sin(sf[1])
        self.sapma_faz = sf[:, -1] % (2 * np.pi)

        f = 440.0 * 2 ** ((midi - 69) / 12)
        faz = self.faz + 2 * np.pi * np.cumsum(f) / oran
        self.faz = float(faz[-1] % (2 * np.pi))

        hiz = 1 / (0.09 * oran) if self.kapi else -1 / (0.16 * oran)
        z = np.clip(self.zarf + hiz * (sira + 1), 0, 1)
        self.zarf = float(z[-1])
        genlik = np.sin(np.pi / 2 * z) ** 2
        cukur = np.clip((self.cukur_yasi + sira) / (0.05 * oran), 0, 1)
        genlik = genlik * (1 - 0.18 * np.sin(np.pi * cukur))
        self.cukur_yasi += n
        if self.kapi and t[-1] > 0.8:
            genlik = genlik * (1 - 0.1 * np.clip((t - 0.8) / 2.5, 0, 1))

        atak = np.clip(1 - (self.atak_yasi + sira) / (0.12 * oran), 0, 1) ** 2
        self.atak_yasi += n

        nefes_mod = 1 + 0.4 * self.nefes_ort(self.rnd.standard_normal(n))
        ton = (np.sin(faz) + 0.22 * np.sin(2 * faz) + 0.08 * np.sin(3 * faz)
               + 0.03 * np.sin(4 * faz)) * nefes_mod
        gurultu = self.rnd.standard_normal(n)
        hisilti = self.his_yumusak(gurultu - self.his_alcak(gurultu))
        kuru = genlik * (ton + hisilti * (0.12 + 0.4 * atak))

        if not self.yanki:
            return kuru * self.kazanc
        self.islak += np.fft.irfft(np.fft.rfft(kuru, self.m) * self.tepki_f, self.m)
        islak = self.islak[:n].copy()
        self.islak = np.concatenate([self.islak[n:], np.zeros(n)])
        return (kuru + 0.25 * islak) * self.kazanc

    def uret(self, n):
        parcalar = []
        while n > 0:
            k = min(n, self.blok)
            parcalar.append(self._blok(k))
            n -= k
        return np.clip(np.concatenate(parcalar), -1, 1).astype(np.float32)

    def _geri_cagri(self, cikti, n, zaman, durum):
        cikti[:, 0] = self.uret(n)

    def ac(self):
        if self.akim is None:
            import sounddevice as sd
            ortak = dict(samplerate=self.oran, channels=1, dtype="float32",
                         blocksize=self.blok, latency="low", callback=self._geri_cagri)
            try:
                wasapi = next(h for h in sd.query_hostapis() if "WASAPI" in h["name"])
                self.akim = sd.OutputStream(device=wasapi["default_output_device"],
                                            extra_settings=sd.WasapiSettings(auto_convert=True),
                                            **ortak)
            except Exception:
                self.akim = sd.OutputStream(**ortak)
            self.akim.start()

    def kapat(self):
        if self.akim is not None:
            self.akim.stop()
            self.akim.close()
            self.akim = None
