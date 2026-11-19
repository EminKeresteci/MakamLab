"""Notaya dokulmus ezgiden makam tahmini: dizi uyumu, karar, guclu ve seyir puani."""
import collections
import glob
import json
import math
import os
import sys

from nazariyat import Nazariyat, Makam, tasfiye

SYMBTR_RAST = 296
SYMBTR_ADLARI = {
    "nihavent": "nihavend", "beyati": "bayati", "beyati_araban": "bayatiaraban",
    "hicaz_humayun": "humayun", "hicaz_uzzal": "uzzal", "hicaz_zirgule": "zirgulelihicaz",
}
YAKIN_PUAN = 0.25
SEYIRLER = ['çıkıcı', 'inici', 'inici-çıkıcı', 'çıkıcı-inici']
KATSAYI = {
    "uyum": 15.165,
    "dolu": 11.035,
    "karar": 5.440,
    "karar_sekizli": 1.884,
    "guclu": 15.248,
    "durak": 7.149,
    "bas2": -2.469,
    "gen2": -3.672,
    "bas:çıkıcı": -3.966,
    "gen:çıkıcı": -1.126,
    "sabit:çıkıcı": 3.610,
    "bas:inici": 4.959,
    "gen:inici": 3.671,
    "sabit:inici": -3.006,
    "bas:inici-çıkıcı": 0.525,
    "gen:inici-çıkıcı": 1.539,
    "sabit:inici-çıkıcı": 0.860,
    "bas:çıkıcı-inici": -0.761,
    "gen:çıkıcı-inici": 5.298,
    "sabit:çıkıcı-inici": -0.173,
}
KUTU, KAYMA, SABLON_ALFA = 159, 53, 1.0
SABLON_YOLU = os.path.join("data", "symbtr", "sablon.json")
KATSAYI_SABLON = {
    "uyum": 2.701,
    "dolu": 2.490,
    "karar": 4.088,
    "karar_sekizli": 2.435,
    "guclu": 7.615,
    "durak": 10.734,
    "bas2": 0.376,
    "gen2": 0.063,
    "bas:çıkıcı": -6.247,
    "gen:çıkıcı": 5.111,
    "sabit:çıkıcı": -0.156,
    "bas:inici": 1.156,
    "gen:inici": -3.847,
    "sabit:inici": 0.057,
    "bas:inici-çıkıcı": -2.255,
    "gen:inici-çıkıcı": 0.773,
    "sabit:inici-çıkıcı": -0.086,
    "bas:çıkıcı-inici": -3.210,
    "gen:çıkıcı-inici": -0.980,
    "sabit:çıkıcı-inici": 0.567,
    "sablon": 13.439,
}


def symbtr_oku(yol):
    notalar = []
    with open(yol, encoding="utf-8") as f:
        satirlar = f.read().splitlines()
    baslik = satirlar[0].split("\t")
    i_koma, i_ms = baslik.index("KomaAE"), baslik.index("Ms")
    for satir in satirlar[1:]:
        p = satir.split("\t")
        if len(p) <= max(i_koma, i_ms):
            continue
        koma, ms = int(p[i_koma]), int(p[i_ms])
        if ms <= 0:
            continue
        if koma > 0:
            notalar.append((koma - SYMBTR_RAST, ms / 1000))
        elif koma == -1:
            notalar.append((None, ms / 1000))
    return notalar


def ezgi_oku(yol, naz):
    with open(yol, encoding="utf-8") as f:
        b = json.load(f)
    return [(None if p is None else naz.mutlak_koma(p), s * b.get("birim_sn", 1))
            for ad in b["sira"] for p, s in b["bolumler"][ad]]


def oku(yol, naz):
    return ezgi_oku(yol, naz) if yol.lower().endswith(".json") else symbtr_oku(yol)


def _perde(naz, x):
    x = str(x).strip()
    return naz.mutlak_koma(x if "," in x else naz.isimden_perdeye(x))


def dagilim(notalar):
    h = [0.0] * KUTU
    for k, s, *_ in notalar:
        if k is not None:
            h[min(max(k + KAYMA, 0), KUTU - 1)] += s
    toplam = sum(h)
    return [x / toplam for x in h]


def onsel(sinif):
    kutu = {b for b in range(KUTU) if (b - KAYMA) % 53 in sinif}
    return [0.3 / KUTU + (0.7 / len(kutu) if b in kutu else 0.0) for b in range(KUTU)]


def log_sablon(toplam, say, sinif):
    on = onsel(sinif)
    T = [(toplam[b] + SABLON_ALFA * on[b]) / (say + SABLON_ALFA) for b in range(KUTU)]
    return [math.log(0.5 * T[b] + 0.25 * (T[b - 1] if b else 0.0)
                     + 0.25 * (T[b + 1] if b < KUTU - 1 else 0.0) + 1e-6) for b in range(KUTU)]


def derlem(klasor, profil):
    adlar = {tasfiye(p["isim"]): p["isim"] for p in profil}
    for yol in sorted(glob.glob(os.path.join(klasor, "*.txt"))):
        ham = os.path.basename(yol).split("--")[0]
        dogru = adlar.get(SYMBTR_ADLARI.get(ham, ham))
        if dogru is None:
            continue
        notalar = symbtr_oku(yol)
        if any(k is not None for k, _ in notalar):
            yield dogru, notalar


def sablon_kur(klasor, profil, yol=SABLON_YOLU):
    toplam = {p["isim"]: [0.0] * KUTU for p in profil}
    say = collections.Counter()
    for dogru, notalar in derlem(klasor, profil):
        say[dogru] += 1
        for b, x in enumerate(dagilim(notalar)):
            toplam[dogru][b] += x
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"say": say, "toplam": {m: [round(x, 6) for x in toplam[m]] for m in say}}, f)
    print(f"{yol}: {len(say)} makam, {sum(say.values())} eser")


def profiller(naz, sablon=True):
    veri = None
    if sablon and os.path.exists(SABLON_YOLU):
        with open(SABLON_YOLU, encoding="utf-8") as f:
            veri = json.load(f)
    liste = []
    for isim in naz.dizi["isim"]:
        try:
            m = Makam(isim, nazariyat=naz)
            durak = _perde(naz, m.durak)
            liste.append({
                "isim": isim,
                "sinif": {naz.mutlak_koma(p) % 53 for p in m.perdeler},
                "durak": durak,
                "guclu": _perde(naz, m.güçlü),
                "seyir": str(m.seyir).strip() if str(m.seyir).strip() in SEYIRLER else SEYIRLER[2],
            })
            if veri:
                liste[-1]["sablon"] = log_sablon(veri["toplam"].get(isim, [0.0] * KUTU),
                                                 veri["say"].get(isim, 0), liste[-1]["sinif"])
        except Exception as e:
            print(f"{isim}: profil kurulamadi ({e})", file=sys.stderr)
    return liste


def _dilim(sesli, toplam, a, b):
    konum, agirlikli, sure = 0.0, 0.0, 0.0
    for k, s in sesli:
        alt, ust = max(konum, a * toplam), min(konum + s, b * toplam)
        if ust > alt:
            agirlikli += k * (ust - alt)
            sure += ust - alt
        konum += s
    return agirlikli / sure


def ozet(notalar):
    sesli = [(k, s) for k, s, *_ in notalar if k is not None]
    toplam = sum(s for _, s in sesli)
    sinif = collections.Counter()
    for k, s in sesli:
        sinif[k % 53] += s / toplam
    return {"sinif": sinif, "son": sesli[-1][0], "dagilim": dagilim(notalar),
            "baslangic": _dilim(sesli, toplam, 0, 0.15),
            "genel": _dilim(sesli, toplam, 0, 1),
            "sure": toplam, "nota": len(sesli)}


def _uzaklik(sinif, kume):
    return min(min((sinif - k) % 53, (k - sinif) % 53) for k in kume)


def _pay(o, perde):
    return sum(pay for s, pay in o["sinif"].items()
               if min((s - perde) % 53, (perde - s) % 53) <= 1)


def ozellik(o, p):
    fark = o["son"] - p["durak"]
    bas = (o["baslangic"] - p["durak"]) / 53
    gen = (o["genel"] - p["durak"]) / 53
    f = {
        "uyum": sum(pay * {0: 1.0, 1: YAKIN_PUAN}.get(_uzaklik(s, p["sinif"]), 0.0)
                    for s, pay in o["sinif"].items()),
        "dolu": sum(1 for k in p["sinif"] if _pay(o, k) >= 0.01) / len(p["sinif"]),
        "karar": float(fark == 0),
        "karar_sekizli": float(fark != 0 and fark % 53 == 0),
        "guclu": _pay(o, p["guclu"]),
        "durak": _pay(o, p["durak"]),
        "bas2": bas * bas,
        "gen2": gen * gen,
    }
    for s in SEYIRLER:
        f["bas:" + s] = bas * (p["seyir"] == s)
        f["gen:" + s] = gen * (p["seyir"] == s)
        f["sabit:" + s] = float(p["seyir"] == s)
    if "sablon" in p:
        f["sablon"] = sum(x * l for x, l in zip(o["dagilim"], p["sablon"]) if x)
    return f


def puanla(o, p):
    f = ozellik(o, p)
    kat = KATSAYI_SABLON if "sablon" in p else KATSAYI
    katki = {a: kat[a] * f[a] for a in kat}
    parca = {"uyum": katki["uyum"] + katki["dolu"],
             "sablon": katki.get("sablon", 0.0),
             "karar": katki["karar"] + katki["karar_sekizli"],
             "guclu": katki["guclu"] + katki["durak"],
             "seyir": sum(v for a, v in katki.items() if ":" in a or a in ("bas2", "gen2"))}
    return sum(katki.values()), parca


def tahmin(notalar, profil):
    o = ozet(notalar)
    return sorted(((p["isim"],) + puanla(o, p) for p in profil), key=lambda x: -x[1])


def dok(yol, naz, profil, adet=5):
    notalar = oku(yol, naz)
    o = ozet(notalar)
    print(f"{os.path.basename(yol)}: {o['nota']} nota, {o['sure']:.0f} sn, "
          f"karar {naz.komadan_isme.get(o['son'], o['son'])}")
    for isim, puan, parca in tahmin(notalar, profil)[:adet]:
        print(f"  {isim:<18}{puan:6.2f}   dizi {parca['uyum']:5.2f}  karar {parca['karar']:5.2f}"
              f"  güçlü {parca['guclu']:5.2f}  seyir {parca['seyir']:5.2f}"
              f"  şablon {parca['sablon']:6.2f}")


def olc(klasor, naz, profil):
    adlar = {tasfiye(p["isim"]): p["isim"] for p in profil}
    makam_say = collections.Counter()
    bir = collections.Counter()
    uc = collections.Counter()
    karisan = collections.Counter()
    disarida = 0
    for yol in sorted(glob.glob(os.path.join(klasor, "*.txt"))):
        ham = os.path.basename(yol).split("--")[0]
        dogru = adlar.get(SYMBTR_ADLARI.get(ham, ham))
        if dogru is None:
            disarida += 1
            continue
        notalar = symbtr_oku(yol)
        if not any(k is not None for k, _ in notalar):
            continue
        sira = [isim for isim, _, _ in tahmin(notalar, profil)]
        makam_say[dogru] += 1
        if sira[0] == dogru:
            bir[dogru] += 1
        else:
            karisan[(dogru, sira[0])] += 1
        if dogru in sira[:3]:
            uc[dogru] += 1
    n = sum(makam_say.values())
    print(f"eser {n}, listede olmayan makam {disarida}")
    print(f"ilk tahmin {sum(bir.values()) / n:.1%}, ilk üç {sum(uc.values()) / n:.1%}")
    print(f"{'makam':<18}{'eser':>5}{'ilk':>6}{'ilk üç':>8}")
    for m, s in makam_say.most_common():
        print(f"{m:<18}{s:>5}{bir[m] / s:>6.0%}{uc[m] / s:>8.0%}")
    print("en çok karışan (doğru → tahmin):")
    for (d, t), s in karisan.most_common(15):
        print(f"  {d} → {t}: {s}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    naz = Nazariyat()
    if len(sys.argv) > 1 and sys.argv[1] == "sablon":
        sablon_kur(os.path.join("data", "symbtr", "txt"), profiller(naz, sablon=False))
        sys.exit()
    profil = profiller(naz)
    if len(sys.argv) > 1 and sys.argv[1] == "olc":
        if len(sys.argv) > 2:
            secili = {tasfiye(a) for a in sys.argv[2].split(",")}
            profil = [p for p in profil if tasfiye(p["isim"]) in secili]
        olc(os.path.join("data", "symbtr", "txt"), naz, profil)
    else:
        for yol in sys.argv[1:]:
            dok(yol, naz, profil)
