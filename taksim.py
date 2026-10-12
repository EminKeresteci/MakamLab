"""Taksim uretecleri.

Her uretec ayni cagriyi karsilar:

    uret(makam, uzunluk=40, tohum=None, naz=None) -> [(perde, sure_sn), ...]

perde None ise o sure kadar sus demektir. Ureteclerin hepsi URETECLER
sozlugune kayitlidir; kiyas ve calicilar oradan secer.
"""
import glob
import json
import os
import random

import numpy as np

KOK = os.path.dirname(os.path.abspath(__file__))
TAHLIL = os.path.join(KOK, "data", "ney_taksimleri", "tahlil")
URETECLER = {}


def uretec(ad):
    def kaydet(f):
        URETECLER[ad] = f
        return f
    return kaydet


def _naz(naz):
    if naz is None:
        from nazariyat import Nazariyat
        naz = Nazariyat()
    return naz


def cetvel(makam, naz, alt=1, ust=1):
    """Dizinin derecelerini alt..ust cevrim boyunca, pestten tize siralar."""
    perdeler = list(makam.perdeler)
    cevrim = naz.mutlak_koma(perdeler[-1]) - naz.mutlak_koma(perdeler[0])
    temel = perdeler[:-1]
    sonuc = []
    for c in range(-alt, ust + 1):
        sonuc += [naz.koma_ekle(p, c * cevrim) for p in temel]
    sonuc.append(naz.koma_ekle(perdeler[-1], ust * cevrim))
    return sonuc, alt * len(temel)


SUS_ESIK = 1.0


def kayittan(tahlil_json, sus_esik=SUS_ESIK):
    """Tahlil ciktisini [(perde, sure)] dizisine cevirir; aradaki
    bosluk sus_esik'ten uzunsa sus (None) olarak girer."""
    sonuc, son = [], None
    for n in tahlil_json["notalar"]:
        if son is not None and n["t"] - son >= sus_esik:
            sonuc.append((None, round(n["t"] - son, 2)))
        sonuc.append((n["perde"], n["sure"]))
        son = n["t"] + n["sure"]
    return sonuc


def _derece(naz, makam, perde):
    """Duraga gore (derece, oktav, dizi_ici). Dizi disi perde en yakin dereceye
    yuvarlanir ama dizi_ici False doner."""
    perdeler = list(makam.perdeler)
    taban = naz.mutlak_koma(perdeler[0])
    cevrim = naz.mutlak_koma(perdeler[-1]) - taban
    ofs = [naz.mutlak_koma(p) - taban for p in perdeler[:-1]]
    k = naz.mutlak_koma(perde) - taban
    oktav, kalan = divmod(k, cevrim)
    uzak = [min(abs(kalan - o), abs(kalan - o - cevrim)) for o in ofs]
    d = min(range(len(ofs)), key=lambda i: uzak[i])
    if kalan - ofs[d] > cevrim / 2:
        oktav += 1
    return d, oktav, uzak[d] == 0


def olcutler(notalar, makam, naz=None, normalle=False):
    """normalle: kayitlarda tahlilin oktavi keyfidir; notalarin en cok kaldigi
    yeden..tiz durak araligi ana oktav sayilir. Uretec ciktisinda kapali."""
    naz = _naz(naz)
    perdeler = list(makam.perdeler)
    n = len(perdeler) - 1
    try:
        g = str(makam.güçlü)
        g = g if "," in g else naz.isimden_perdeye(g)
        gd, go, _ = _derece(naz, makam, g)
        guclu_k = gd + go * n
    except Exception:
        guclu_k = None
    dizi, sinir = [], []
    for perde, sure in notalar:
        if perde is None:
            sinir.append(len(dizi))
            continue
        d, o, ici = _derece(naz, makam, perde)
        dizi.append([d + o * n, ici, sure])
    adaylar = {(k // n) * n for k, _, _ in dizi} or {0}
    kay = max(sorted(adaylar), key=lambda c: sum(s for k, _, s in dizi if -1 <= k - c <= n)) \
        if normalle else 0
    for x in dizi:
        x[0] -= kay
    konum = [k for k, _, _ in dizi]
    cumleler = [c for c in (konum[a:b] for a, b in zip([0] + sinir, sinir + [len(konum)])) if c]
    toplam = sum(s for *_, s in dizi) or 1.0
    dagilim = [0.0] * n
    for k, _, s in dizi:
        dagilim[k % n] += s / toplam
    adimlar = {}
    for a, b in zip(konum, konum[1:]):
        a = max(-4, min(4, b - a))
        adimlar[a] = adimlar.get(a, 0) + 1
    adim_top = sum(adimlar.values()) or 1

    def pay(hedef):
        return round(sum(s for k, _, s in dizi if k == hedef) / toplam, 3)

    def son(hedef):
        return round(sum(1 for c in cumleler if c[-1] == hedef) / max(1, len(cumleler)), 3)

    return {
        "nota": len(dizi),
        "sure": round(sum(s for _, s in notalar), 1),
        "derece": [round(x, 3) for x in dagilim],
        "adim": {a: round(c / adim_top, 3) for a, c in sorted(adimlar.items())},
        "cumle_nota": round(len(dizi) / max(1, len(cumleler)), 1),
        "durak_payi": pay(0),
        "guclu_payi": pay(guclu_k) if guclu_k is not None else None,
        "alan": (min(konum), max(konum)) if konum else (0, 0),
        "son_durak": son(0),
        "son_guclu": son(guclu_k) if guclu_k is not None else None,
        "dizi_disi": round(sum(s for _, ici, s in dizi if not ici) / toplam, 3),
    }


def kayitlar(makam_adi=None):
    sonuc = []
    for yol in sorted(glob.glob(os.path.join(TAHLIL, "*.json"))):
        with open(yol, encoding="utf-8") as f:
            j = json.load(f)
        if makam_adi is None or j["makam"] == makam_adi:
            sonuc.append(j)
    return sonuc


@uretec("kayıt")
def kayit(makam, uzunluk=None, tohum=None, naz=None):
    """Gercek taksimin tahlilden cikan perde/sure dizisi; yoksa bos."""
    adaylar = kayitlar(makam.isim)
    if not adaylar:
        return []
    return oktav_duzelt(kayittan(random.Random(tohum).choice(adaylar)), makam, _naz(naz))


def oktav_duzelt(notalar, makam, naz):
    """Tahlilin keyfi sectigi oktavi, notalarin en cok kaldigi yeden..tiz
    durak araligi makamin kendi oktavina dusecek sekilde kaydirir."""
    taban = naz.mutlak_koma(makam.perdeler[0])
    komalar = [(naz.mutlak_koma(p) - taban, s) for p, s in notalar if p is not None]
    if not komalar:
        return notalar
    adaylar = sorted({k // 53 for k, _ in komalar})
    kay = max(adaylar, key=lambda c: sum(s for k, s in komalar if -9 <= k - 53 * c <= 53))
    if kay == 0:
        return notalar
    sonuc = []
    for p, s in notalar:
        if p is not None:
            esas, koma, oktav = p.split(",")
            p = "%s,%s,%d" % (esas, koma, int(oktav) - kay)
        sonuc.append((p, s))
    return sonuc


ADIM = {0: 0.31, 1: 0.26, -1: 0.19, 2: 0.06, -2: 0.09, 3: 0.03, -3: 0.03, 4: 0.02, -4: 0.02}
CUMLE_NOTA = 7

PLAN = {
    "çıkıcı": (0, [(0, "asma"), ("g", "asma"), ("t", "tepe"), ("g", "asma"), (0, "asma")]),
    "inici": ("t", [("t", "asma"), ("g", "asma"), (0, "asma"), ("g", "asma"), (1, "asma")]),
    "çıkıcı-inici": ("g", [("g", "asma"), ("t", "tepe"), (0, "asma"), ("g", "asma"), (1, "asma")]),
    "inici-çıkıcı": ("g", [(0, "asma"), ("g", "asma"), ("t", "tepe"), (0, "asma"), (1, "asma")]),
}
TEKRAR_CARPANI = 0.7


def _konum(naz, makam, perde):
    d, o, _ = _derece(naz, makam, perde)
    return d + o * (len(makam.perdeler) - 1)


def _plan(makam, naz, uzunluk, rnd):
    """Seyir tipinden cumle hedefleri: (n, guclu, yeden, baslangic, [(hedef, tur)])."""
    n = len(makam.perdeler) - 1
    try:
        g = str(makam.güçlü)
        guclu = _konum(naz, makam, g if "," in g else naz.isimden_perdeye(g))
    except Exception:
        guclu = n // 2
    try:
        y = str(makam.yeden)
        yeden = _konum(naz, makam, y if "," in y else naz.isimden_perdeye(y))
    except Exception:
        yeden = -1
    if not -3 <= yeden < 0:
        yeden = -1

    def coz(h):
        return {"g": guclu, "t": n}.get(h, h)

    bas, hedefler = PLAN.get(str(makam.seyir).strip(), PLAN["çıkıcı"])
    cumle_sayisi = max(2, round(uzunluk / CUMLE_NOTA))
    ara = [d for d in range(1, n + 1) if d != guclu] or [1]
    while len(hedefler) < cumle_sayisi - 1:
        i = rnd.randrange(1, len(hedefler) + 1)
        hedefler = hedefler[:i] + [(rnd.choice(ara), "asma")] + hedefler[i:]
    hedefler = hedefler[:cumle_sayisi - 1] + [(0, "karar")]
    return n, guclu, yeden, coz(bas), [(coz(h), tur) for h, tur in hedefler]


def _cek(p, k, yeni, hedef, kalan):
    cekim = abs(yeni - hedef) - abs(k - hedef)
    return p * (0.35 ** cekim if abs(k - hedef) >= kalan else 0.7 ** cekim)


@uretec("kural")
def kural(makam, uzunluk=48, tohum=None, naz=None):
    """Seyir planina gore cumle cumle yuruyus: guclude asma karar, tize
    dokunus, yedenden duraga karar. Adim olasiliklari gercek taksimlerden."""
    naz = _naz(naz)
    rnd = random.Random(tohum)
    sira, durak_i = cetvel(makam, naz, alt=1, ust=2)
    n, guclu, yeden, k, hedefler = _plan(makam, naz, uzunluk, rnd)
    alt_sinir, ust_sinir = -2, n + 2

    def perde(k):
        return sira[durak_i + k]

    adimlar = list(ADIM)
    agirlik = [p * (TEKRAR_CARPANI if a == 0 else 1.0) for a, p in ADIM.items()]
    sonuc = []
    for hedef, tur in hedefler:
        boy = max(3, round(rnd.gauss(CUMLE_NOTA, 2)))
        for i in range(boy - 1):
            kalan = boy - 1 - i
            w = [_cek(p, k, k + a, hedef, kalan) if alt_sinir <= k + a <= ust_sinir else 0.0
                 for a, p in zip(adimlar, agirlik)]
            k += rnd.choices(adimlar, w)[0]
            sonuc.append((perde(k), max(0.12, rnd.lognormvariate(-1.2, 0.35))))
        if tur == "karar":
            if k != yeden:
                sonuc.append((perde(yeden), 0.45))
            sonuc.append((perde(0), 2.4))
            break
        k = hedef
        sonuc.append((perde(k), rnd.uniform(1.0, 1.8) if tur == "asma" else rnd.uniform(0.6, 1.0)))
        sonuc.append((None, rnd.uniform(0.6, 1.1)))
    return sonuc


AGIRLIK = {"kendi": 1.0, "aile": 0.5, "diger": 0.1}
_KOMA_PERDE = {}


def _koma_perde(naz):
    if not _KOMA_PERDE:
        for p in naz.perde.perde.values:
            try:
                _KOMA_PERDE.setdefault(naz.mutlak_koma(p), p)
            except Exception:
                pass
    return _KOMA_PERDE


def _kayit_dizisi(j, makam, naz):
    """Kaydi [(konum | None, sure, duraga_koma | None)] dizisine cevirir."""
    n = len(makam.perdeler) - 1
    taban = naz.mutlak_koma(makam.perdeler[0])
    sonuc = []
    for p, s in oktav_duzelt(kayittan(j), makam, naz):
        if p is None:
            sonuc.append((None, s, None))
        else:
            d, o, _ = _derece(naz, makam, p)
            sonuc.append((d + o * n, s, naz.mutlak_koma(p) - taban))
    return sonuc


_MODELLER = {}


def markov_modeli(makam, naz, haric=()):
    anahtar = (makam.isim, tuple(sorted(haric)))
    if anahtar not in _MODELLER:
        _MODELLER[anahtar] = _markov_modeli(makam, naz, haric)
    return _MODELLER[anahtar]


def _kaynaklar(makam, naz, haric):
    """Ayni derece sayisindaki kayitlar: (tur, agirlik, konum dizisi)."""
    from nazariyat import Makam
    n = len(makam.perdeler) - 1
    imza = [naz.mutlak_koma(p) - naz.mutlak_koma(makam.perdeler[0]) for p in makam.perdeler]
    for j in kayitlar():
        if j["id"] in haric:
            continue
        try:
            km = makam if j["makam"] == makam.isim else Makam(j["makam"], nazariyat=naz)
        except Exception:
            continue
        if len(km.perdeler) - 1 != n:
            continue
        kimza = [naz.mutlak_koma(p) - naz.mutlak_koma(km.perdeler[0]) for p in km.perdeler]
        tur = "kendi" if km.isim == makam.isim else "aile" if kimza == imza else "diger"
        yield tur, AGIRLIK[tur], _kayit_dizisi(j, km, naz)


def _markov_modeli(makam, naz, haric):
    n = len(makam.perdeler) - 1
    say2, say1, say0 = {}, {}, {}
    sure, cesit = {}, {}
    for tur, w, dizi in _kaynaklar(makam, naz, haric):
        semboller = ["|"] + ["|" if k is None else k for k, _, _ in dizi]
        for a, b, c in zip(semboller, semboller[1:], semboller[2:]):
            say2.setdefault((a, b), {}).setdefault(c, 0.0)
            say2[(a, b)][c] += w
        for b, c in zip(semboller, semboller[1:]):
            say1.setdefault(b, {}).setdefault(c, 0.0)
            say1[b][c] += w
        for (k, s, rk), sem in zip(dizi, semboller[1:]):
            say0[sem] = say0.get(sem, 0.0) + w
            sure.setdefault(sem, []).append((s, w))
            if k is not None and tur == "kendi":
                cesit.setdefault(k, []).append((rk, w))
    return {"n": n, "say2": say2, "say1": say1, "say0": say0, "sure": sure, "cesit": cesit}


def _sec(rnd, sozluk):
    anahtarlar = list(sozluk)
    return rnd.choices(anahtarlar, [sozluk[a] for a in anahtarlar])[0]


def _markov_araclari(model, makam, naz, rnd, sira, durak_i):
    """Modelden konum -> perde (dizi disi cesitlemeyle) ve konum -> sure secicileri."""
    taban = naz.mutlak_koma(makam.perdeler[0])
    koma_perde = _koma_perde(naz)
    alt_sinir, ust_sinir = -durak_i, len(sira) - 1 - durak_i

    def perde(k):
        k = max(alt_sinir, min(ust_sinir, k))
        cesit = model["cesit"].get(k)
        if cesit:
            rk = rnd.choices([r for r, _ in cesit], [w for _, w in cesit])[0]
            p = koma_perde.get(taban + rk)
            if p is not None:
                return p
        return sira[durak_i + k]

    def sure(sem, varsayilan):
        liste = model["sure"].get(sem)
        if not liste:
            return varsayilan
        return rnd.choices([s for s, _ in liste], [w for _, w in liste])[0]

    return perde, sure


@uretec("markov")
def markov(makam, uzunluk=48, tohum=None, naz=None, haric=()):
    """Gercek taksimlerden ogrenilmis 2. dereceden zincir; kendi makamin verisi
    yoksa ayni dizidekilere, o da yoksa ayni derece sayisindakilere dayanir."""
    naz = _naz(naz)
    rnd = random.Random(tohum)
    model = markov_modeli(makam, naz, haric)
    if not model["say0"]:
        return []
    sira, durak_i = cetvel(makam, naz, alt=1, ust=2)
    perde, sure = _markov_araclari(model, makam, naz, rnd, sira, durak_i)

    a, b, sonuc, nota = "|", "|", [], 0
    while nota < uzunluk:
        aday = model["say2"].get((a, b))
        if not aday or sum(aday.values()) < 2:
            aday = model["say1"].get(b) or model["say0"]
        c = _sec(rnd, aday)
        if c == "|":
            if b != "|":
                sonuc.append((None, sure("|", 0.8)))
        else:
            sonuc.append((perde(c), sure(c, 0.35)))
            nota += 1
        a, b = b, c
    while sonuc and sonuc[-1][0] is None:
        sonuc.pop()
    son = _konum(naz, makam, sonuc[-1][0]) if sonuc else None
    if son != 0:
        if son != -1:
            sonuc.append((sira[durak_i - 1], 0.45))
        sonuc.append((sira[durak_i], 2.4))
    return sonuc


@uretec("karma")
def karma(makam, uzunluk=48, tohum=None, naz=None, haric=()):
    """kural'in cumle plani (hedef, asma karar, nefes, karar); notadan notaya
    gecis ve sureler markov modelinden, hedefe cekimle tartilarak."""
    naz = _naz(naz)
    rnd = random.Random(tohum)
    model = markov_modeli(makam, naz, haric)
    if not model["say0"]:
        return kural(makam, uzunluk, tohum, naz)
    sira, durak_i = cetvel(makam, naz, alt=1, ust=2)
    perde, sure = _markov_araclari(model, makam, naz, rnd, sira, durak_i)
    n, guclu, yeden, k, hedefler = _plan(makam, naz, uzunluk, rnd)
    alt_sinir, ust_sinir = max(-2, -durak_i), min(n + 2, len(sira) - 1 - durak_i)

    a, sonuc = "|", []
    for hedef, tur in hedefler:
        boy = max(3, round(rnd.gauss(CUMLE_NOTA, 2)))
        for i in range(boy - 1):
            kalan = boy - 1 - i
            aday = model["say2"].get((a, k))
            if not aday or sum(aday.values()) < 2:
                aday = model["say1"].get(k) or {}
            w = {c: _cek(p, k, c, hedef, kalan) for c, p in aday.items()
                 if c != "|" and alt_sinir <= c <= ust_sinir}
            if not any(w.values()):
                w = {k + d: _cek(p, k, k + d, hedef, kalan) for d, p in ADIM.items()
                     if alt_sinir <= k + d <= ust_sinir}
            a, k = k, _sec(rnd, w)
            sonuc.append((perde(k), sure(k, 0.35)))
        if tur == "karar":
            if k != yeden:
                sonuc.append((sira[durak_i + yeden], 0.45))
            sonuc.append((sira[durak_i], 2.4))
            break
        a, k = k, hedef
        sonuc.append((sira[durak_i + k], rnd.uniform(1.0, 1.8) if tur == "asma" else rnd.uniform(0.6, 1.0)))
        sonuc.append((None, sure("|", 0.8)))
        a = "|"
    return sonuc


def cumle_kutuphanesi(makam, naz, haric=()):
    """Kayitlari sus yerlerinden cumlelere boler: cumleler ve sus sureleri."""
    anahtar = ("kalıp", makam.isim, tuple(sorted(haric)))
    if anahtar not in _MODELLER:
        cumleler, suslar = [], []
        for tur, w, dizi in _kaynaklar(makam, naz, haric):
            cumle = []
            for k, s, rk in dizi + [(None, 0.0, None)]:
                if k is not None:
                    cumle.append((k, s, rk))
                    continue
                if len(cumle) >= 2:
                    cumleler.append({"notalar": cumle, "w": w, "kendi": tur == "kendi"})
                if s:
                    suslar.append((min(s, 2.5), w))
                cumle = []
        _MODELLER[anahtar] = {"cumleler": cumleler, "suslar": suslar}
    return _MODELLER[anahtar]


@uretec("kalıp")
def kalip(makam, uzunluk=48, tohum=None, naz=None, haric=()):
    """Gercek taksimlerden kesilmis cumleler seyir planina gore dizilir: her
    hedef icin sonu oraya varan cumle secilir, gerekirse derece kaydirilir.
    Perde, ritim ve cesni icradan gelir."""
    naz = _naz(naz)
    rnd = random.Random(tohum)
    kut = cumle_kutuphanesi(makam, naz, haric)
    if not kut["cumleler"]:
        return kural(makam, uzunluk, tohum, naz)
    sira, durak_i = cetvel(makam, naz, alt=1, ust=2)
    alt_sinir, ust_sinir = -durak_i, len(sira) - 1 - durak_i
    taban = naz.mutlak_koma(makam.perdeler[0])
    koma_perde = _koma_perde(naz)
    n, guclu, yeden, k, hedefler = _plan(makam, naz, uzunluk, rnd)

    kullanilan, sonuc = {}, []
    for hedef, tur in hedefler:
        adaylar, agirlik = [], []
        for i, c in enumerate(kut["cumleler"]):
            notalar = c["notalar"]
            kay = hedef - notalar[-1][0]
            if not all(alt_sinir <= x + kay <= ust_sinir for x, _, _ in notalar):
                continue
            adaylar.append((i, kay))
            agirlik.append(c["w"] * 0.25 ** abs(kay) * 0.6 ** abs(notalar[0][0] + kay - k)
                           * 0.15 ** kullanilan.get(i, 0))
        if not adaylar:
            continue
        i, kay = rnd.choices(adaylar, agirlik)[0]
        kullanilan[i] = kullanilan.get(i, 0) + 1
        c = kut["cumleler"][i]
        for x, s, rk in c["notalar"]:
            p = koma_perde.get(taban + rk) if kay == 0 and c["kendi"] else None
            sonuc.append((p or sira[durak_i + x + kay], s))
        k = hedef
        if tur == "karar":
            break
        sonuc.append((None, rnd.choices([s for s, _ in kut["suslar"]],
                                        [w for _, w in kut["suslar"]])[0] if kut["suslar"] else 0.8))
    while sonuc and sonuc[-1][0] is None:
        sonuc.pop()
    son = _konum(naz, makam, sonuc[-1][0]) if sonuc else None
    if son != 0:
        if son != yeden:
            sonuc.append((sira[durak_i + yeden], 0.45))
        sonuc.append((sira[durak_i], 2.4))
    return sonuc


@uretec("rastgele")
def rastgele(makam, uzunluk=40, tohum=None, naz=None):
    """Eski Makam.taksim(): +-2 derece rastgele yuruyus. Kiyasta taban cizgisi."""
    naz = _naz(naz)
    rnd = random.Random(tohum)
    sira, durak = cetvel(makam, naz, alt=0, ust=1)
    i, sonuc = durak, []
    for _ in range(uzunluk):
        sonuc.append((sira[i], 0.35))
        i = min(len(sira) - 1, max(0, i + rnd.randint(-2, 2)))
    return sonuc


ORAN = 44100


def _yumusat(x, n):
    n = max(1, int(n))
    c = np.cumsum(np.concatenate([np.zeros(n // 2 + 1), x, np.zeros(n - n // 2)]))
    return (c[n:n + len(x)] - c[:len(x)]) / n


def seslendir(notalar, naz=None, oran=ORAN, oktav=1, tohum=0):
    """Ney benzeri kesintisiz sentez: notalar arasi kayma, uzun notada
    gecikmeli titresim, nefes hisiltisi, cumle boyu sisip sonme, kisa yanki."""
    from nazariyat import perde_midi
    naz = _naz(naz)
    rnd = np.random.default_rng(tohum)
    toplam = int(oran * (sum(s for _, s in notalar) + 0.7))
    midi = np.zeros(toplam)
    genlik = np.zeros(toplam)
    i, onceki = 0, None
    cumle = []

    def cumle_bitir():
        if not cumle:
            return
        a, b = cumle[0], cumle[-1]
        boy = b - a
        z = np.ones(boy)
        acilis, kapanis = min(boy, int(0.09 * oran)), min(boy, int(0.16 * oran))
        z[:acilis] *= np.sin(np.linspace(0, np.pi / 2, acilis)) ** 2
        z[boy - kapanis:] *= np.cos(np.linspace(0, np.pi / 2, kapanis)) ** 2
        genlik[a:b] *= z
        cumle.clear()

    for perde, sure in notalar:
        n = int(sure * oran)
        if perde is None:
            cumle_bitir()
            midi[i:i + n] = midi[i - 1] if i else 0
            onceki = None
            i += n
            continue
        hedef = perde_midi(perde, nazariyat=naz) + 12 * oktav
        egri = np.full(n, hedef)
        if onceki is None:
            k = min(n, int(0.06 * oran))
            egri[:k] -= 0.3 * np.cos(np.linspace(0, np.pi / 2, k))
        else:
            k = min(n // 2, int(min(0.07, 0.25 * sure) * oran))
            egri[:k] = onceki + (hedef - onceki) * (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k)))
        if sure > 0.45:
            t = np.arange(n) / oran
            derinlik = 0.12 * np.clip((t - 0.3) / 0.6, 0, 1)
            egri += derinlik * np.sin(2 * np.pi * rnd.uniform(4.6, 5.4) * t)
        z = np.ones(n)
        if onceki is not None:
            k = min(n, int(0.05 * oran))
            z[:k] = 1 - 0.18 * np.sin(np.linspace(0, np.pi, k))
        if sure > 0.8:
            t = np.linspace(0, 1, n)
            z *= 0.85 + 0.25 * np.sin(np.pi * np.minimum(1, t * 1.6)) - 0.15 * t
        midi[i:i + n] = egri
        genlik[i:i + n] = z
        if not cumle:
            cumle.append(i)
        cumle[1:] = [i + n]
        onceki = hedef
        i += n
    cumle_bitir()
    midi[i:] = midi[i - 1] if i else 0

    sapma = _yumusat(rnd.standard_normal(toplam), oran * 0.25) * 4
    f = 440.0 * 2 ** ((midi + sapma - 69) / 12)
    faz = 2 * np.pi * np.cumsum(f) / oran
    nefes_mod = 1 + 0.04 * _yumusat(rnd.standard_normal(toplam), oran * 0.01) * 10
    ton = (np.sin(faz) + 0.22 * np.sin(2 * faz) + 0.08 * np.sin(3 * faz)
           + 0.03 * np.sin(4 * faz)) * nefes_mod
    gurultu = rnd.standard_normal(toplam)
    hisilti = _yumusat(gurultu - _yumusat(gurultu, oran / 1500), oran / 9000)
    atak = np.zeros(toplam)
    fark = np.diff(np.concatenate([[0], (genlik > 0.05).astype(float)]))
    for b in np.flatnonzero(fark > 0):
        k = min(toplam - b, int(0.12 * oran))
        atak[b:b + k] = np.linspace(1, 0, k) ** 2
    kuru = genlik * (ton + hisilti * (0.12 + 0.4 * atak))
    yanki_boy = int(0.5 * oran)
    tepki = rnd.standard_normal(yanki_boy) * np.exp(-np.arange(yanki_boy) / (0.12 * oran))
    tepki *= np.cos(np.linspace(0, np.pi / 2, yanki_boy)) ** 2
    tepki = _yumusat(tepki, oran / 6000)
    tepki[0] = 0
    m = 1 << int(np.ceil(np.log2(toplam + yanki_boy)))
    islak = np.fft.irfft(np.fft.rfft(kuru, m) * np.fft.rfft(tepki, m), m)[:toplam]
    islak *= np.abs(kuru).max() / (np.abs(islak).max() or 1)
    dalga = kuru + 0.25 * islak
    return (0.8 * dalga / (np.abs(dalga).max() or 1)).astype(np.float32)


def wav_yaz(yol, dalga, oran=ORAN):
    import wave
    with wave.open(yol, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(oran)
        w.writeframes((np.clip(dalga, -1, 1) * 32767).astype("<i2").tobytes())


def olc(uretec_adi="rastgele", atla=("Hüzzam",)):
    """Gercek taksimlerin olcutlerini bir uretecinkiyle yan yana basar."""
    from nazariyat import Nazariyat, Makam
    naz = Nazariyat()
    sablon = "{:20} {:>4} {:>5} {:>6} {:>6} {:>5} {:>7} {:>5} {:>5}  {}"
    print(sablon.format("makam", "nota", "cümle", "durak%", "güçlü%", "dışı%", "alan",
                        "sonD%", "sonG%", "adım -4..+4 (%)"))
    ozet = {"gerçek": [], uretec_adi: []}
    for j in kayitlar():
        if j["makam"] in atla:
            continue
        m = Makam(j["makam"], nazariyat=naz)
        uretilen = URETECLER[uretec_adi](m, uzunluk=len(j["notalar"]), tohum=1, naz=naz)
        for ad, notalar, norm in (("gerçek", kayittan(j), True), (uretec_adi, uretilen, False)):
            o = olcutler(notalar, m, naz, normalle=norm)
            ozet[ad].append(o)
            etiket = j["makam"] if ad == "gerçek" else "  " + ad
            print(sablon.format(etiket[:20], o["nota"], o["cumle_nota"],
                                round(100 * o["durak_payi"]), round(100 * (o["guclu_payi"] or 0)),
                                round(100 * o["dizi_disi"]), "%d..%d" % o["alan"],
                                round(100 * o["son_durak"]), round(100 * (o["son_guclu"] or 0)),
                                " ".join("%2d" % round(100 * o["adim"].get(a, 0)) for a in range(-4, 5))))
    print()
    for ad, liste in ozet.items():
        if not liste:
            continue
        orta = lambda k: sorted(x[k] or 0 for x in liste)[len(liste) // 2]
        adim = " ".join("%2d" % round(100 * sorted(x["adim"].get(a, 0) for x in liste)[len(liste) // 2])
                        for a in range(-4, 5))
        print("%-10s medyan: cümle %.1f, durak %%%d, güçlü %%%d, dışı %%%d, sonD %%%d, sonG %%%d, adım %s" % (
            ad, orta("cumle_nota"), 100 * orta("durak_payi"), 100 * orta("guclu_payi"),
            100 * orta("dizi_disi"), 100 * orta("son_durak"), 100 * orta("son_guclu"), adim))


BILESENLER = ("adım", "derece", "durak", "güçlü", "dışı", "sonD", "sonG", "cümle", "süre")


def uzaklik(o, g):
    """Iki olcut kumesi arasinda bilesen bilesen uzaklik, her biri 0..1."""
    adim = 0.5 * sum(abs(o["adim"].get(a, 0) - g["adim"].get(a, 0)) for a in range(-4, 5))
    derece = 0.5 * sum(abs(x - y) for x, y in zip(o["derece"], g["derece"]))
    fark = lambda k: abs((o[k] or 0) - (g[k] or 0))
    oran = lambda k: min(1.0, abs(o[k] - g[k]) / max(g[k], 1e-6))
    return dict(zip(BILESENLER, (adim, derece, fark("durak_payi"), fark("guclu_payi"),
                                 fark("dizi_disi"), fark("son_durak"), fark("son_guclu"),
                                 oran("cumle_nota"), oran("sure"))))


def kiyas(ureteçler=("rastgele", "kural", "markov", "karma", "kalıp"), tohumlar=5, atla=("Hüzzam",)):
    """Her kayit icin ureteclerin olcutlerinin gercege uzakligi; ogrenen
    ureteclerde o kayit modelden cikarilir (birini disarida birak)."""
    import inspect
    from nazariyat import Nazariyat, Makam
    naz = Nazariyat()
    sonuc = {ad: [] for ad in ureteçler}
    makam_satiri = []
    for j in kayitlar():
        if j["makam"] in atla:
            continue
        m = Makam(j["makam"], nazariyat=naz)
        gercek = olcutler(kayittan(j), m, naz, normalle=True)
        satir = {}
        for ad in ureteçler:
            f = URETECLER[ad]
            ek = {"haric": (j["id"],)} if "haric" in inspect.signature(f).parameters else {}
            for t in range(tohumlar):
                notalar = f(m, uzunluk=len(j["notalar"]), tohum=t, naz=naz, **ek)
                u = uzaklik(olcutler(notalar, m, naz), gercek)
                sonuc[ad].append(u)
                satir[ad] = satir.get(ad, 0) + sum(u.values()) / len(u) / tohumlar
        makam_satiri.append((j["makam"], satir))

    print("%-20s " % "makam" + " ".join("%8s" % ad for ad in ureteçler) + "  en yakın")
    for makam, satir in makam_satiri:
        print("%-20s " % makam[:20] + " ".join("%8.3f" % satir[ad] for ad in ureteçler)
              + "  " + min(satir, key=satir.get))
    print()
    print("%-10s " % "uzaklık" + " ".join("%6s" % b for b in BILESENLER) + "   ortalama")
    for ad, liste in sonuc.items():
        ort = {b: sum(u[b] for u in liste) / len(liste) for b in BILESENLER}
        print("%-10s " % ad + " ".join("%6.3f" % ort[b] for b in BILESENLER)
              + "   %.3f" % (sum(ort.values()) / len(ort)))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "olc":
        olc(*sys.argv[2:3])
    elif len(sys.argv) > 1 and sys.argv[1] == "kiyas":
        kiyas()
    else:
        print(__doc__)
        print("    python taksim.py olc [" + "|".join(URETECLER) + "]")
        print("    python taksim.py kiyas")
