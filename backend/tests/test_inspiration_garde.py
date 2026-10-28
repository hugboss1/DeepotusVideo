# -*- coding: utf-8 -*-
"""t313 (28/10/2026) (C3 Inspiration, tâche 1) — banc des gardes anti-copie (inspiration_garde, module PUR).
Ce que ce banc garde, par sections numérotées :
  1. mots() : casse, accents, ponctuation, apostrophes et retours à la ligne neutres ; chiffres gardés.
  2. plus_longue_suite() : 11 mots repris -> 11, 12 -> 12, l'extrait rendu dans la forme du TEXTE jugé ; suite trouvée
     même coupée par des retours à la ligne, de la ponctuation ou des majuscules ; textes vides.
  3. juger() : ok tant que suite < SEUIL_SUITE (12) ; refus à 12 ; proximité 0 (texte neuf) et 100 (copie) ;
     une capture de 20 000 caractères jugée en moins d'une seconde.
  4. empreinte() / meme_image() : même image recompressée en JPEG et réduite de moitié -> même ; image différente -> non ;
     octets illisibles -> ValueError.
Aucun réseau, aucun fichier.
Run (depuis backend/) : & $PY tests/test_inspiration_garde.py"""
import io, pathlib, random, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import inspiration_garde as G   # noqa: E402

# ---- 1. mots
check("1a casse et accents neutres", G.mots("Élan ÉTÉ été") == ["elan", "ete", "ete"], G.mots("Élan ÉTÉ été"))
check("1b ponctuation et retours à la ligne neutres", G.mots("Un, deux ;\n trois !") == ["un", "deux", "trois"])
check("1c apostrophe : l'arbre -> l arbre", G.mots("l'arbre l’été") == ["l", "arbre", "l", "ete"], G.mots("l'arbre l’été"))
check("1d chiffres gardés", G.mots("3 pas, 12 mots") == ["3", "pas", "12", "mots"])
check("1e vide", G.mots("") == [] and G.mots(None) == [])

# ---- 2. plus_longue_suite
CAPTE = ("Le matin, la ville respire lentement : les cafés ouvrent, les vélos glissent sur les pavés mouillés et "
         "chacun cherche sa place dans la lumière grise qui annonce une journée ordinaire.")
cm = CAPTE.replace(",", "").replace(":", "").replace(".", "").split()
onze = " ".join(cm[3:14])
douze = " ".join(cm[3:15])
n, ex = G.plus_longue_suite(CAPTE, "Voici notre version : " + onze + " et puis autre chose.")
check("2a 11 mots repris -> 11", n == 11, (n, ex))
n, ex = G.plus_longue_suite(CAPTE, "Voici notre version : " + douze + " et puis autre chose.")
check("2b 12 mots repris -> 12", n == 12, (n, ex))
check("2c l'extrait est pris dans le texte jugé", ex.split()[0] == cm[3] and len(ex.split()) == 12, ex)
deguise = "LA VILLE,\nrespire — lentement ; les CAFÉS ouvrent... les velos glissent sur les paves mouilles et chacun"
n, _ = G.plus_longue_suite(CAPTE, deguise)
check("2d déguisé (casse, accents, ponctuation, retours) -> suite trouvée", n >= 12, n)
check("2e textes vides -> 0", G.plus_longue_suite("", "abc")[0] == 0 and G.plus_longue_suite("abc", "")[0] == 0)
n, _ = G.plus_longue_suite(CAPTE, "Une tout autre histoire de montagne et de neige, sans rapport aucun.")
check("2f texte neuf -> suite courte", n <= 2, n)

# ---- 3. juger
j = G.juger(CAPTE, "Voici : " + onze + ".")
check("3a 11 mots : ok", j["ok"] is True and j["suite"] == 11, j)
j = G.juger(CAPTE, "Voici : " + douze + ".")
check("3b 12 mots : refus", j["ok"] is False and j["suite"] == 12 and j["extrait"], j)
check("3c SEUIL_SUITE vaut 12", G.SEUIL_SUITE == 12)
check("3d proximité d'une copie = 100", G.juger(CAPTE, CAPTE)["proximite"] == 100, G.juger(CAPTE, CAPTE))
check("3e proximité d'un texte neuf = 0",
      G.juger(CAPTE, "Une tout autre histoire de montagne et de neige, sans rapport aucun.")["proximite"] == 0)
check("3f proximité entre 0 et 100 pour un mélange", 0 < G.juger(CAPTE, "Voici : " + onze + " puis une montagne de "
      "neige sans aucun rapport avec la ville ni ses cafés ouverts tard.")["proximite"] < 100)
check("3g texte vide : ok, suite 0, proximité 0", G.juger(CAPTE, "") == {"suite": 0, "proximite": 0, "extrait": "", "ok": True},
      G.juger(CAPTE, ""))
check("3h capture vide : ok", G.juger("", "un texte quelconque")["ok"] is True)
random.seed(7)
voc = ["mot%d" % i for i in range(800)]
grand = " ".join(random.choice(voc) for _ in range(3300))[:20000]
autre = " ".join(random.choice(voc) for _ in range(900))
t0 = time.perf_counter()
G.juger(grand, autre)
check("3i capture de 20 000 caractères jugée en < 1 s", time.perf_counter() - t0 < 1.0, time.perf_counter() - t0)

# ---- 4. empreintes d'image
from PIL import Image, ImageDraw   # noqa: E402


def image(couleur, forme, taille=(400, 300), fmt="PNG", q=None):
    im = Image.new("RGB", taille, couleur)
    d = ImageDraw.Draw(im)
    if forme == "rond":
        d.ellipse((60, 40, 260, 240), fill=(250, 250, 250))
    else:
        d.rectangle((200, 20, 380, 120), fill=(10, 10, 10))
        d.rectangle((20, 180, 120, 280), fill=(240, 30, 30))
    b = io.BytesIO()
    im.save(b, fmt, **({"quality": q} if q else {}))
    return b.getvalue()


a = image((20, 60, 160), "rond")
a_jpeg = image((20, 60, 160), "rond", fmt="JPEG", q=60)
with Image.open(io.BytesIO(a)) as im0:
    b = io.BytesIO()
    im0.resize((200, 150)).save(b, "WEBP", quality=70)
    a_petit = b.getvalue()
autre_img = image((200, 200, 40), "carres")
ea = G.empreinte(a)
check("4a empreinte : sha256 et ahash", len(ea["sha256"]) == 64 and len(ea["ahash"]) == 16, ea)
check("4b même image recompressée JPEG -> même", G.meme_image(ea, G.empreinte(a_jpeg)))
check("4c même image réduite de moitié en WEBP -> même", G.meme_image(ea, G.empreinte(a_petit)))
check("4d image différente -> non", not G.meme_image(ea, G.empreinte(autre_img)))
check("4e sha256 identique -> même", G.meme_image(ea, dict(ea)))
try:
    G.empreinte(b"pas une image")
    check("4f octets illisibles -> ValueError", False)
except ValueError:
    check("4f octets illisibles -> ValueError", True)
check("4g empreinte absente ou partielle -> non", not G.meme_image(ea, {}) and not G.meme_image({}, {}))
# 4h : recadrée de 8 px et éclaircie de 15 % -> quelques bits d'écart, toujours la même (mesuré : 3 bits)
from PIL import ImageEnhance   # noqa: E402
im8 = Image.new("RGB", (400, 300), (20, 60, 160))
d8 = ImageDraw.Draw(im8)
d8.ellipse((60, 40, 260, 240), fill=(250, 250, 250))
d8.rectangle((300, 200, 390, 290), fill=(200, 120, 40))
b8, c8 = io.BytesIO(), io.BytesIO()
im8.save(b8, "PNG")
ImageEnhance.Brightness(im8.crop((8, 8, 392, 292))).enhance(1.15).save(c8, "PNG")
e8, f8 = G.empreinte(b8.getvalue()), G.empreinte(c8.getvalue())
check("4h recadrée et éclaircie (quelques bits d'écart) -> même", e8["ahash"] != f8["ahash"] and G.meme_image(e8, f8),
      (e8, f8))

print(f"\n{ok} PASS, {fail} FAIL")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
