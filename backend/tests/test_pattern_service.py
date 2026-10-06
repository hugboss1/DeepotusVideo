# -*- coding: utf-8 -*-
"""Générateurs paramétriques locaux (R10c D1) — le socle : bruit de valeur
fractal SEAMLESS PAR CONSTRUCTION, et son budget en secondes.

« Par construction » n'est pas une figure de style, et c'est ce que ce banc
mesure : le réseau est périodique, il est bordé CYCLIQUEMENT avant
l'agrandissement, et le recadrage retombe sur une période entière. Le témoin
— la même chose sans le bordage — est là pour montrer ce que coûte l'oubli.

Run (depuis backend/) : python tests/test_pattern_service.py
"""
import os
import pathlib
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402

from app.services import pattern_service as PS                 # noqa: E402
from app.services import pbr_service as PBR                    # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def jonction(img):
    """La définition EXACTE de « sans couture » pour une tuile périodique : la
    marche moyenne à la jonction (dernière colonne -> première, dernière rangée
    -> première) ne dépasse pas la PIRE marche intérieure, sur chaque axe.

    Pourquoi pas le rapport de couture seul : il compare la jonction à la marche
    MOYENNE, et sur un motif à arêtes franches (damier, rayures) une arête qui
    tombe au bord le fait exploser (54 sur le damier, mesuré le 06/10) alors que
    la tuile est parfaitement périodique. Le plan exigeait « ≤ 2,0 pour les dix » :
    jamais tenable, jamais mesuré. Rend [(jonction, pire intérieure)] par axe."""
    from PIL import ImageChops
    L = img.convert("L")
    w, h = L.size
    out = []
    for axe in "xy":
        d = ImageChops.difference(L, ImageChops.offset(L, -1, 0) if axe == "x" else ImageChops.offset(L, 0, -1))
        prof = d.resize((w, 1) if axe == "x" else (1, h), Image.BOX).tobytes()
        out.append((prof[-1], max(prof[:-1])))
    return out


# ══ 1 · la maille DIVISE toujours le côté ══════════════════════════════════
# 384 n'est PAS une puissance de deux, et c'est tout l'objet de ce cas :
# sur un cote en puissance de deux, n'importe quelle puissance de deux le
# divise, et la garde de divisibilite ne se voit jamais.
for cote in (256, 384, 512, 1024):
    for voulu in (3, 5, 8, 13, 100, 999, 1, 0, -4):
        c = PS.cells(cote, voulu)
        assert cote % c == 0, (cote, voulu, c)
        assert 2 <= c <= cote, (cote, voulu, c)
ok("cells() rend toujours un diviseur du côté, entre 2 et le côté — sans "
   "divisibilité exacte, le recadrage ne retomberait pas sur une période")

# ══ 2 · le raccord, et son témoin ══════════════════════════════════════════
b = PS.bruit(256, cellules=8, octaves=4, graine=17)
assert b.size == (256, 256) and b.mode == "L"
r_bon = PBR.seam_report(b)
assert r_bon["ratio"] <= 1.5, r_bon
# VINGT graines et pas une : sur une tuile parfaitement périodique, le rapport
# fluctue autour de 1 (la jonction n'est qu'une colonne de plus), donc le grade
# « invisible » (≤ 1,0) d'UNE graine est un pile ou face. Le plan l'exigeait ;
# la version du plan montait d'ailleurs à 1,98 sur certaines graines (octaves
# alignées) — d'où le roulement par octave de `bruit`.
lot = [PBR.seam_report(PS.bruit(256, 8, 4, graine=g))["ratio"] for g in range(20)]
assert max(lot) <= 1.5 and sum(lot) / len(lot) <= 1.15, lot
naif = PS._octave_naive(256, 8, 17)          # témoin : sans bordage cyclique
r_naif = PBR.seam_report(naif)
assert r_naif["ratio"] > 2.0 * r_bon["ratio"], (r_bon, r_naif)
assert all(j <= m for j, m in jonction(b)), jonction(b)
assert all(j > 3 * m for j, m in jonction(naif)), jonction(naif)
ok(f"raccord : sur 20 graines, max {max(lot)} et moyenne {sum(lot) / len(lot):.2f} ; le même "
   f"bruit sans bordage cyclique monte à {r_naif['ratio']}")

# ══ 3 · déterministe, et la graine change quelque chose ════════════════════
assert PS.bruit(128, 8, 3, graine=5).tobytes() == \
       PS.bruit(128, 8, 3, graine=5).tobytes()
assert PS.bruit(128, 8, 3, graine=5).tobytes() != \
       PS.bruit(128, 8, 3, graine=6).tobytes()
ok("déterministe à graine égale, différent à graine différente — un aperçu "
   "qui bouge tout seul ne se règle pas")

# ══ 4 · les octaves apportent du détail ════════════════════════════════════
un = PBR.stats(PS.bruit(256, 8, 1, graine=3))
cinq = PBR.stats(PS.bruit(256, 8, 5, graine=3))
def grain(img):
    from PIL import ImageChops, ImageFilter, ImageStat
    return ImageStat.Stat(ImageChops.difference(
        img, img.filter(ImageFilter.GaussianBlur(1.5)))).mean[0]
g1, g5 = grain(PS.bruit(256, 8, 1, graine=3)), grain(PS.bruit(256, 8, 5, graine=3))
assert g5 > 1.5 * g1, (g1, g5)
assert un["span"] > 40 and cinq["span"] > 40, (un, cinq)
ok(f"cinq octaves portent {g5 / g1:.1f} fois le grain d'une seule, et les "
   f"deux gardent une amplitude utile")

# ══ 5 · l'étirement reste raccordable ══════════════════════════════════════
etire = PS.etirer(PS.bruit(256, 8, 4, graine=9), 1, 16)
assert etire.size == (256, 256)
r_et = PBR.seam_report(etire)
assert r_et["ratio"] <= 2.0, r_et
ok(f"étirement anisotrope (x1, y16) : raccord {r_et['ratio']} — le bordage "
   f"cyclique suit l'échelle")

# ══ 6 · budget ═════════════════════════════════════════════════════════════
t0 = time.perf_counter()
gros = PS.bruit(1024, cellules=8, octaves=6, graine=1)
dt = time.perf_counter() - t0
assert gros.size == (1024, 1024)
assert dt < PS.BUDGET_BRUIT_1024, (dt, PS.BUDGET_BRUIT_1024)
print(f"\n  bruit 1024² 6 octaves : {dt:.2f} s "
      f"(budget {PS.BUDGET_BRUIT_1024:.1f} s)")

# ══ 7 · les DIX générateurs, un par un ═════════════════════════════════════
assert len(PS.GENERATEURS) == 10, len(PS.GENERATEURS)
assert len({g["id"] for g in PS.GENERATEURS}) == 10
temps = {}
for g in PS.GENERATEURS:
    gid = g["id"]
    p = PS.clean_params(gid, {})
    t0 = time.perf_counter()
    m = PS.generer(gid, 256, p)
    temps[gid] = time.perf_counter() - t0
    assert set(m) >= {"basecolor", "height"}, (gid, sorted(m))
    assert m["basecolor"].size == (256, 256) and m["basecolor"].mode == "RGB"
    assert m["height"].size == (256, 256) and m["height"].mode == "L"
    for carte in ("basecolor", "height"):
        jj = jonction(m[carte])
        assert all(j <= mx for j, mx in jj), (gid, carte, jj)
    st = PBR.stats(m["height"])
    assert st["span"] > 8, (gid, st)
    # déterminisme
    assert PS.generer(gid, 128, p)["basecolor"].tobytes() == \
           PS.generer(gid, 128, p)["basecolor"].tobytes(), gid
    # un réglage change quelque chose : on bouge le PREMIER paramètre numérique
    num = next((c for c in g["params"] if c["type"] == "f"), None)
    if num:
        autre = dict(p)
        autre[num["k"]] = num["max"] if p[num["k"]] < num["max"] else num["min"]
        assert PS.generer(gid, 128, PS.clean_params(gid, autre))["height"] \
            .tobytes() != PS.generer(gid, 128, p)["height"].tobytes(), \
            (gid, num["k"])
ok("dix générateurs : jonction jamais pire que l'intérieur (couleur ET hauteur), hauteur non plate, déterministes, et "
   "leur premier réglage numérique change vraiment la carte "
   f"({', '.join(g['id'] for g in PS.GENERATEURS)})")

# ══ 8 · budget d'un motif complet à 1024 ═══════════════════════════════════
lent = max(PS.GENERATEURS, key=lambda g: temps[g["id"]])["id"]
t0 = time.perf_counter()
PS.generer(lent, 1024, PS.clean_params(lent, {}))
dt2 = time.perf_counter() - t0
assert dt2 < PS.BUDGET_MOTIF_1024, (lent, dt2)
print(f"  le plus lent ({lent}) à 1024² : {dt2:.2f} s "
      f"(budget {PS.BUDGET_MOTIF_1024:.1f} s)")

# ══ 9 · une entrée pourrie ne lève jamais ══════════════════════════════════
for mauvais in (None, {}, {"x": 1}, {"rangs": "beaucoup"}, {"rangs": -9},
                {"rangs": 10 ** 9}, [], "briques"):
    p = PS.clean_params("briques", mauvais)
    assert isinstance(p, dict) and p, mauvais
    assert PS.generer("briques", 64, p)["height"].size == (64, 64)
try:
    PS.generer("nexistepas", 64, {})
    raise AssertionError("aurait dû lever")
except ValueError as e:
    assert "nexistepas" in str(e), str(e)
ok("réglages pourris -> défauts, générateur inconnu -> ValueError nommée")

# ══ 10 · `cyclique` REPLIE ce qui déborde (absent du plan) ══════════════════
# Les motifs en grille débordent déjà des deux côtés par leurs indices (-1 à
# n+1) : ne tracer qu'UNE copie ne s'y verrait pas. Une forme qui sort à droite
# doit rentrer à gauche — c'est ce que les galets et le cuir, posés au hasard,
# exigent.
toile = PS.cyclique(64, lambda d, dx, dy: d.ellipse([58 + dx, 28 + dy, 70 + dx, 40 + dy], fill=255))
assert toile.getpixel((2, 34)) == 255 and toile.getpixel((62, 34)) == 255, "le débord n'est pas replié"
toile = PS.cyclique(64, lambda d, dx, dy: d.ellipse([28 + dx, 58 + dy, 40 + dx, 70 + dy], fill=255))
assert toile.getpixel((34, 2)) == 255, "le débord vertical n'est pas replié"
# la GRAINE de chaque générateur change la carte (le plan ne le vérifiait que
# pour le bruit) : un réglage « graine » qui ne ferait rien serait un mensonge
for g in PS.GENERATEURS:
    p = PS.clean_params(g["id"], {})
    assert PS.generer(g["id"], 128, p, 0)["basecolor"].tobytes() != \
        PS.generer(g["id"], 128, p, 1)["basecolor"].tobytes(), g["id"]
# et pour les sept dont le DESSIN est aléatoire (teintes, positions, fil), la
# HAUTEUR change aussi — la couleur seule changeait par le grain ajouté, et
# laissait passer des teintes de briques figées quelle que soit la graine
for gid in ("briques", "carrelage", "hexagones", "galets", "cuir", "planches", "metal_brosse"):
    p = PS.clean_params(gid, {})
    assert PS.generer(gid, 128, p, 0)["height"].tobytes() != \
        PS.generer(gid, 128, p, 1)["height"].tobytes(), gid
ok("cyclique replie le débord des deux côtés ; la graine de CHACUN des dix change sa carte, et le "
   "DESSIN des sept aléatoires")

print(f"\nOK — {PASS} assertions groupées vertes (pattern_service, socle)")
