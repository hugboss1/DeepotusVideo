# -*- coding: utf-8 -*-
"""t312 (28/10/2026) (C1 Scan, tâche 4) — banc des routes /api/scan/* et de scan_pages.
La lecture Windows passe par la VRAIE scan_ocr.lire_page, sa couture `_executer` remplacée (jamais de PowerShell) ;
Claude passe par le vrai scan_vision, le POST HTTP de moteurs_texte remplacé (jamais de réseau).
Sections :
  1. scan_pages : charger (images, PDF textuel, PDF scanné, mixte, refus 400/413/415/422), cache (ranger/obtenir,
     expiration 1 h, 20 scans au plus).
  2. POST /lire : 2 images -> texte nettoyé + scan_id ; auto = deux passes par page ; PDF textuel -> aucun OCR ;
     PDF scanné -> images incorporées lues ; mixte ; refus 400/413/415/422 ; langue invalide.
  3. pont absent, bloqué, trop lent, JSON illisible (Review Focus 2) : 503 (secours_vision + scan_id) / 504 / 502,
     aucun PNG temporaire laissé.
  4. devis-vision, vision : montant (raison traduite), 409 max_usd trop bas, 409 coût changé (autre modèle, aucun
     appel — Review Focus 4), 402 plafond, 503 Claude indisponible, rendu partiel, 404 inconnu / expiré.
  5. découpage : chapitres de segment_chapters, debut, 413, 400.
  6. hors machine locale : 403 partout ; journaux sans texte lu.
  7. revue finale t312 : échéance globale de la lecture locale (partiel / 504, m1) ; argent (I1) : delai_s au devis,
     transcription payée gardée (GET /vision, POST sans nouvel appel, nouvelle: true), 409 vision_en_cours, drapeau
     levé après chaque issue ; erreur réseau au premier lot 502 / délai 504 (m2) ; plafond jugé sur le total (m4) ;
     premiere_page_non_lue (m5) ; découpage : texte exact de chaque chapitre (I2).
Run (depuis backend/) : & $PY tests/test_scan_routes.py"""
import io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzscanrt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_TEMP = _tmp / "temp"
_TEMP.mkdir()
tempfile.tempdir = str(_TEMP)            # les PNG temporaires du pont atterrissent ici : on peut les compter
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()
_JOURNAL = []
logger.add(lambda m: _JOURNAL.append(str(m)), level="DEBUG")
import subprocess                                                   # noqa: E402
from fastapi import HTTPException                                   # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402
from PIL import Image                                               # noqa: E402
from pypdf import PdfWriter, PdfReader                              # noqa: E402
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.config import settings                                     # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import manuscript_agent as MA                     # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import plafonds as PL                             # noqa: E402
from app.services import scan_ocr as O                              # noqa: E402
from app.services import scan_pages as SP                           # noqa: E402
from app.services import scan_vision as V                           # noqa: E402
from app.api import scan_routes as SR                               # noqa: E402
import httpx                                                        # noqa: E402
import time as _time                                                # noqa: E402

settings.ANTHROPIC_API_KEY = "cle-de-banc"
settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

SECRET = "Licorne"           # un mot du texte lu : jamais dans les journaux
TEXTES = {                   # largeur de la page -> ses lignes (fr ; l'anglais lit « B0njour » : plus incertain)
    1300: ["Bonjour le monde", f"La {SECRET} dort ici."],
    1400: ["Deuxième page du livre", "Elle continue encore."],
    1500: ["Page scannée dans un PDF", "Fin de la page."],
}


# ------------------------------------------------------------------ fabriques
def img(w, h=900, fmt="PNG"):
    b = io.BytesIO()
    Image.new("RGB", (w, h), (250, 250, 250)).save(b, fmt)
    return b.getvalue()


def pdf_images(*largeurs):
    ims = [Image.new("RGB", (w, 900), (250, 250, 250)) for w in largeurs]
    b = io.BytesIO()
    ims[0].save(b, "PDF", save_all=True, append_images=ims[1:])
    return b.getvalue()


def pdf_texte(*pages):
    w = PdfWriter()
    for t in pages:
        p = w.add_blank_page(612, 792)
        if t is None:
            continue
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        p[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): w._add_object(font)})})
        s = DecodedStreamObject()
        lignes = b" ".join(b"BT /F1 12 Tf 72 %d Td (%s) Tj ET" % (700 - 16 * i, li.encode("latin-1"))
                           for i, li in enumerate(t.split("\n")))
        s.set_data(lignes)
        p[NameObject("/Contents")] = w._add_object(s)
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


def pdf_concat(*pdfs):
    w = PdfWriter()
    for d in pdfs:
        w.append(PdfReader(io.BytesIO(d)))
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


# ------------------------------------------------------------------ couture du pont
APPELS_OCR = []
MODE = {"exc": None, "rc": 0, "brut": None}


def _ligne(texte, y):
    mots, x = [], 40
    for m in texte.split():
        mots.append({"texte": m, "x": x, "y": y, "l": 18 * len(m), "h": 30})
        x += 18 * len(m) + 16
    return {"texte": texte, "mots": mots}


def faux_executer(args, timeout):
    chemin = args[args.index("-Image") + 1]
    tag = args[args.index("-Langue") + 1]
    with Image.open(chemin) as im:
        w = im.size[0]
    APPELS_OCR.append((w, tag))
    if MODE["exc"] is not None:
        raise MODE["exc"]
    if MODE["rc"]:
        return MODE["rc"], "", "erreur"
    if MODE["brut"] is not None:
        return 0, MODE["brut"], ""
    lignes = TEXTES.get(w, ["Page inconnue"])
    if tag == "en-US":
        lignes = [li.replace("Bonjour", "B0njour") for li in lignes]
    return 0, json.dumps({"langue": tag, "angle": 0,
                          "lignes": [_ligne(li, 100 + 44 * i) for i, li in enumerate(lignes)]}), ""


O._executer = faux_executer
O._dispo = {"ok": True, "langues": ["fr-FR", "en-US"], "raison": ""}


def temporaires():
    return [p.name for p in _TEMP.iterdir() if p.name.startswith("dzscan_")]


# ------------------------------------------------------------------ couture de Claude
APPELS_IA = []


class _Rep:
    status_code = 200
    text = ""
    def __init__(self, txt): self._t = txt
    def json(self): return {"content": [{"type": "text", "text": self._t}]}


def faux_post(url, headers=None, json=None, timeout=None, verify=None):
    APPELS_IA.append(json)
    return _Rep(f"Transcription Claude du [[?lot]] {len(APPELS_IA)} {SECRET}.")


MT.httpx.post = faux_post


def refus(f, *a, **k):
    try:
        f(*a, **k)
        return None
    except Exception as e:  # noqa: BLE001
        return e


def multipart(*fichiers, langue=None):
    files = [("pages", (nom, octets, "application/octet-stream")) for nom, octets in fichiers]
    return {"files": files, "data": ({"langue": langue} if langue else {})}


# ====================================================================== 1. scan_pages
print("[1] scan_pages : charger et cache")
r = SP.charger([("a.png", img(1300)), ("b.jpg", img(1400, fmt="JPEG"))])
check("1a deux images -> deux pages image", [p["genre"] for p in r] == ["image", "image"]
      and all(isinstance(p["octets"], bytes) for p in r), r)
for fmt in ("WEBP", "BMP", "TIFF"):
    r = SP.charger([("x", img(1300, fmt=fmt))])
    check(f"1b format {fmt} accepté", r and r[0]["genre"] == "image", r)
e = refus(SP.charger, [("x.gif", img(1300, fmt="GIF"))])
check("1c GIF -> refus 415", isinstance(e, SP.RefusPages) and e.statut == 415, repr(e))
e = refus(SP.charger, [("x.txt", "du texte simple".encode())])
check("1d texte brut -> refus 415", isinstance(e, SP.RefusPages) and e.statut == 415, repr(e))
e = refus(SP.charger, [("x.png", b"\x89PNG" + b"\0" * (20 * 1024 * 1024))])
check("1e fichier > 20 Mo -> refus 413", isinstance(e, SP.RefusPages) and e.statut == 413, repr(e))
e = refus(SP.charger, [(f"{i}.png", img(1300, 40)) for i in range(11)])
check("1f 11 fichiers -> refus 400", isinstance(e, SP.RefusPages) and e.statut == 400, repr(e))
e = refus(SP.charger, [])
check("1g aucun fichier -> refus 400", isinstance(e, SP.RefusPages) and e.statut == 400, repr(e))
TXT1 = "Chapitre premier : le texte selectionnable\nUne seconde ligne assez longue pour compter."
r = SP.charger([("t.pdf", pdf_texte(TXT1))])
check("1h PDF textuel -> page texte", len(r) == 1 and r[0]["genre"] == "texte" and "selectionnable" in r[0]["texte"], r)
r = SP.charger([("s.pdf", pdf_images(1500, 1400))])
check("1i PDF scanné -> images incorporées", [p["genre"] for p in r] == ["image", "image"], r)
with Image.open(io.BytesIO(r[0]["octets"])) as _im:
    check("1j l'image incorporée est la page (1500 px)", _im.size[0] == 1500, _im.size)
e = refus(SP.charger, [("v.pdf", pdf_texte(None, None))])
check("1k PDF sans texte ni image -> refus 422", isinstance(e, SP.RefusPages) and e.statut == 422, repr(e))
r = SP.charger([("m.pdf", pdf_concat(pdf_texte(TXT1), pdf_images(1500), pdf_texte(None)))])
check("1l PDF mixte : texte, image, page vide sautée", [p["genre"] for p in r] == ["texte", "image"], r)
e = refus(SP.charger, [("g.pdf", pdf_images(*([1300] * 11)))])
check("1m PDF de 11 pages image -> refus 400", isinstance(e, SP.RefusPages) and e.statut == 400, repr(e))
e = refus(SP.charger, [("a.pdf", pdf_images(*([1300] * 6))), ("b.pdf", pdf_images(*([1300] * 5)))])
check("1n 6 + 5 pages après dépliage -> refus 400", isinstance(e, SP.RefusPages) and e.statut == 400, repr(e))
e = refus(SP.charger, [("c.pdf", b"%PDF-1.4 casse")])
check("1o PDF illisible -> refus 422", isinstance(e, SP.RefusPages) and e.statut == 422, repr(e))


def png_mono(w, h):                       # 1 bit par pixel : une très grande image qui pèse peu
    b = io.BytesIO()
    Image.new("1", (w, h), 1).save(b, "PNG")
    return b.getvalue()


GRANDE = png_mono(8000, 8000)             # 64 Mpx : au-dessus du plafond de 60 Mpx, sous l'alerte de Pillow
e = refus(SP.charger, [("g.png", GRANDE)])
check("1u image de 64 Mpx -> refus 413 (pas 415)", isinstance(e, SP.RefusPages) and e.statut == 413, repr(e))
e = refus(SP.charger, [("b.png", png_mono(14000, 14000))])
check("1v bombe de 196 Mpx (refusée par Pillow à l'ouverture) -> 413, pas 415",
      isinstance(e, SP.RefusPages) and e.statut == 413, repr(e))
_b = io.BytesIO()
Image.new("L", (8000, 8000), 250).save(_b, "PDF")
from pypdf import PageObject                                        # noqa: E402
_vrai_images, _decode = PageObject.images, []
PageObject.images = property(lambda self: _decode.append(1) or _vrai_images.fget(self))
try:
    e = refus(SP.charger, [("g.pdf", _b.getvalue())])
finally:
    PageObject.images = _vrai_images
check("1w PDF dont l'image incorporée fait 64 Mpx -> refus 413 avant décodage (page.images jamais lu)",
      isinstance(e, SP.RefusPages) and e.statut == 413 and _decode == [], (repr(e), _decode))
_w = PdfWriter()
for _ in range(201):
    _w.add_blank_page(612, 792)
_b = io.BytesIO(); _w.write(_b)
e = refus(SP.charger, [("long.pdf", _b.getvalue())])
check("1x PDF de 201 pages -> refus 400 sans le parcourir", isinstance(e, SP.RefusPages) and e.statut == 400
      and "200" in str(e), repr(e))
SP.MAX_OCTETS_IMAGE = 1000
e = refus(SP.charger, [("s.pdf", pdf_images(1500))])
SP.MAX_OCTETS_IMAGE = SP.MAX_OCTETS
check("1y image de page PDF plus lourde que le plafond -> refus 413", isinstance(e, SP.RefusPages)
      and e.statut == 413, repr(e))

SP._CACHE.clear()
sid = SP.ranger({"texte": "x"}, [{"genre": "image", "octets": b"1"}])
got = SP.obtenir(sid)
check("1p ranger / obtenir", got["resultat"] == {"texte": "x"} and got["images"][0]["octets"] == b"1", got)
SP._CACHE[sid]["cree"] -= SP.TTL + 1
check("1q expiré après 1 h -> KeyError", isinstance(refus(SP.obtenir, sid), KeyError))
check("1r expiré purgé du cache", sid not in SP._CACHE)
check("1s inconnu -> KeyError", isinstance(refus(SP.obtenir, "inconnu"), KeyError))
ids = [SP.ranger(None, []) for _ in range(SP.MAX_SCANS + 1)]
check("1t 20 scans au plus : le plus ancien est évincé",
      len(SP._CACHE) == SP.MAX_SCANS and ids[0] not in SP._CACHE and ids[-1] in SP._CACHE, len(SP._CACHE))
SP._CACHE.clear()
check("1t2 budget par défaut : 256 Mo", SP.BUDGET == 256 * 1024 * 1024, SP.BUDGET)
SP.BUDGET = 5000
a = SP.ranger(None, [{"genre": "image", "octets": b"a" * 2000}])
b = SP.ranger(None, [{"genre": "image", "octets": b"b" * 2000}, {"genre": "texte", "texte": "x" * 9000}])
check("1t3 sous le budget : les deux gardés (le texte ne compte pas)", a in SP._CACHE and b in SP._CACHE)
c3 = SP.ranger(None, [{"genre": "image", "octets": b"c" * 2000}])
check("1t4 au-delà du budget : le plus ancien évincé", a not in SP._CACHE and b in SP._CACHE and c3 in SP._CACHE
      and sum(v["poids"] for v in SP._CACHE.values()) <= SP.BUDGET, list(SP._CACHE))
d4 = SP.ranger(None, [{"genre": "image", "octets": b"d" * 6000}])
check("1t5 un scan plus lourd que le budget n'est pas gardé (None), le cache reste intact",
      d4 is None and b in SP._CACHE and c3 in SP._CACHE, (d4, list(SP._CACHE)))
SP.BUDGET = 256 * 1024 * 1024
SP._CACHE.clear()


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    # ================================================================== 2. lire
    print("\n[2] POST /api/scan/lire")
    APPELS_OCR.clear()
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), ("p2.png", img(1400))))
    d = rp.json() if rp.status_code == 200 else {}
    check("2a 2 images -> 200", rp.status_code == 200, f"{rp.status_code} {rp.text[:300]}")
    check("2b forme du rendu", set(d) >= {"scan_id", "moteur", "langue", "pages", "texte", "incertains", "stats",
                                          "duree_ms"} and d.get("moteur") == "windows" and d.get("pages") == 2, d)
    check("2c texte nettoyé des deux pages, dans l'ordre",
          d.get("texte", "").find("Bonjour le monde") == 0 and d["texte"].find("Bonjour") < d["texte"].find("Deuxième"),
          d.get("texte"))
    check("2d langue fr par défaut : une passe fr-FR par page", APPELS_OCR == [(1300, "fr-FR"), (1400, "fr-FR")],
          APPELS_OCR)
    check("2e scan gardé en cache", d.get("scan_id") in SP._CACHE)
    check("2f aucun PNG temporaire laissé", temporaires() == [], temporaires())

    APPELS_OCR.clear()
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), langue="auto"))
    d = rp.json() if rp.status_code == 200 else {}
    check("2g auto : deux passes (fr-FR et en-US) par page", sorted(t for _, t in APPELS_OCR) == ["en-US", "fr-FR"],
          APPELS_OCR)
    check("2h auto : la passe fr (moins d'incertains) est gardée, « B0njour » écarté",
          d.get("langue") == "fr" and "Bonjour" in d.get("texte", "") and "B0njour" not in d.get("texte", ""), d)
    APPELS_OCR.clear()
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), langue="en"))
    check("2i langue en : une passe en-US", rp.status_code == 200 and APPELS_OCR == [(1300, "en-US")], APPELS_OCR)
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), langue="de"))
    check("2j langue inconnue -> 400", rp.status_code == 400, rp.status_code)

    APPELS_OCR.clear()
    O._dispo = None                      # un PDF textuel ne doit même pas interroger le pont
    rp = c.post("/api/scan/lire", **multipart(("t.pdf", pdf_texte(TXT1))))
    d = rp.json() if rp.status_code == 200 else {}
    check("2k PDF textuel -> 200, texte direct", rp.status_code == 200 and "selectionnable" in d.get("texte", ""),
          f"{rp.status_code} {rp.text[:200]}")
    check("2l PDF textuel -> AUCUN appel au pont (ni lecture ni langues)", APPELS_OCR == [] and O._dispo is None,
          APPELS_OCR)
    check("2m PDF textuel : moteur texte, aucun incertain", d.get("moteur") == "texte" and d.get("incertains") == [], d)
    O._dispo = {"ok": True, "langues": ["fr-FR", "en-US"], "raison": ""}

    APPELS_OCR.clear()
    rp = c.post("/api/scan/lire", **multipart(("s.pdf", pdf_images(1500))))
    d = rp.json() if rp.status_code == 200 else {}
    check("2n PDF scanné -> l'image incorporée est lue", rp.status_code == 200 and APPELS_OCR == [(1500, "fr-FR")]
          and "Page scannée" in d.get("texte", ""), f"{APPELS_OCR} {rp.text[:200]}")

    APPELS_OCR.clear()
    rp = c.post("/api/scan/lire", **multipart(("m.pdf", pdf_concat(pdf_texte(TXT1), pdf_images(1500))),
                                              ("p.png", img(1300))))
    d = rp.json() if rp.status_code == 200 else {}
    t = d.get("texte", "")
    check("2o mixte : pages texte et images dans l'ordre", rp.status_code == 200 and d.get("pages") == 3
          and 0 <= t.find("selectionnable") < t.find("Page scannée") < t.find("Bonjour"), t)
    inc_ok = all(t[i["debut"]:i["fin"]].strip() and " " not in t[i["debut"]:i["fin"]] for i in d.get("incertains", []))
    check("2p mixte : positions incertaines décalées sur le texte final", inc_ok, d.get("incertains"))
    check("2q mixte : stats additionnées (pages_texte)", d.get("stats", {}).get("pages_texte") == 1
          and d.get("stats", {}).get("pages") == 2, d.get("stats"))

    rp = c.post("/api/scan/lire", **multipart(*[(f"{i}.png", img(1300, 40)) for i in range(11)]))
    check("2r 11 pages -> 400", rp.status_code == 400, rp.status_code)
    rp = c.post("/api/scan/lire", **multipart(("g.png", b"\x89PNG" + b"\0" * (21 * 1024 * 1024))))
    check("2s fichier 21 Mo -> 413", rp.status_code == 413, rp.status_code)
    rp = c.post("/api/scan/lire", **multipart(("g.gif", img(1300, fmt="GIF"))))
    check("2t format inconnu -> 415", rp.status_code == 415, rp.status_code)
    rp = c.post("/api/scan/lire", **multipart(("v.pdf", pdf_texte(None))))
    check("2u PDF sans texte ni image -> 422 avec message", rp.status_code == 422 and rp.json().get("detail"),
          rp.status_code)
    rp = c.post("/api/scan/lire", data={"langue": "fr"})
    check("2v aucune page -> 422 (champ `pages` requis)", rp.status_code == 422, rp.status_code)
    rp = c.post("/api/scan/lire", **multipart(("g.png", GRANDE)))
    check("2w image de 64 Mpx -> 413 avec message", rp.status_code == 413 and "60" in str(rp.json().get("detail")),
          f"{rp.status_code} {rp.text[:200]}")
    SP.BUDGET = 100
    APPELS_OCR.clear()
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300))))
    d = rp.json() if rp.status_code == 200 else {}
    check("2x scan plus lourd que le cache : texte rendu, scan_id null, en_cache false", rp.status_code == 200
          and d.get("scan_id") is None and d.get("en_cache") is False and "Bonjour" in d.get("texte", ""), d)
    SP.BUDGET = 256 * 1024 * 1024
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300))))
    check("2y scan ordinaire : en_cache true", rp.status_code == 200 and rp.json().get("en_cache") is True)

    # ================================================================== 3. pont en échec
    print("\n[3] pont absent, bloqué, lent, illisible")
    O._dispo = {"ok": False, "langues": [], "raison": "La lecture de texte locale n'existe que sous Windows."}
    APPELS_OCR.clear()
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), ("p2.png", img(1400))))
    d = rp.json().get("detail") if rp.status_code == 503 else {}
    check("3a OCR indisponible -> 503", rp.status_code == 503, f"{rp.status_code} {rp.text[:200]}")
    check("3b 503 : code ocr_indisponible, message clair", isinstance(d, dict) and d.get("code") == "ocr_indisponible"
          and "Windows" in d.get("message", ""), d)
    sv = (d or {}).get("secours_vision") or {}
    check("3c 503 : secours_vision = devis de 2 pages", sv.get("disponible") is True and sv.get("usd", 0) > 0
          and sv.get("pages") == 2, sv)
    check("3d 503 : scan_id rangé (le secours payant peut le relire)", d.get("scan_id") in SP._CACHE, d)
    check("3e aucun appel au pont quand il est déclaré indisponible", APPELS_OCR == [], APPELS_OCR)
    SCAN_503 = d.get("scan_id")
    O._dispo = {"ok": True, "langues": ["fr-FR", "en-US"], "raison": ""}

    MODE["exc"] = FileNotFoundError(2, "introuvable", "powershell")
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300))))
    d = rp.json().get("detail") if rp.status_code == 503 else {}
    check("3f PowerShell absent -> 503 avec secours", rp.status_code == 503 and isinstance(d, dict)
          and d.get("secours_vision"), f"{rp.status_code} {rp.text[:200]}")
    check("3g … aucun PNG temporaire laissé", temporaires() == [], temporaires())
    MODE["exc"] = subprocess.TimeoutExpired(["powershell"], 60)
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300))))
    check("3h trop lent -> 504", rp.status_code == 504, f"{rp.status_code} {rp.text[:200]}")
    check("3i … aucun PNG temporaire laissé", temporaires() == [], temporaires())
    MODE["exc"] = None
    MODE["brut"] = "{pas du json"
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300))))
    check("3j JSON illisible -> 502", rp.status_code == 502, f"{rp.status_code} {rp.text[:200]}")
    MODE["brut"] = None
    MODE["rc"] = 1
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300))))
    check("3k code de sortie 1 -> 502", rp.status_code == 502, rp.status_code)
    check("3l … aucun PNG temporaire laissé", temporaires() == [], temporaires())
    MODE["rc"] = 0
    O._dispo = {"ok": True, "langues": ["fr-FR"], "raison": ""}
    APPELS_OCR.clear()
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), langue="auto"))
    check("3m auto avec la seule langue fr installée : une passe fr, 200",
          rp.status_code == 200 and APPELS_OCR == [(1300, "fr-FR")], f"{rp.status_code} {APPELS_OCR}")
    O._dispo = {"ok": True, "langues": ["fr-FR", "en-US"], "raison": ""}

    # ================================================================== 4. vision
    print("\n[4] devis-vision et vision")
    APPELS_IA.clear()
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), ("p2.png", img(1400))))
    SCAN = rp.json()["scan_id"]
    rp = c.get(f"/api/scan/{SCAN}/devis-vision")
    dv = rp.json() if rp.status_code == 200 else {}
    check("4a devis-vision -> montant", rp.status_code == 200 and dv.get("usd", 0) > 0 and dv.get("disponible") is True
          and dv.get("pages") == 2, f"{rp.status_code} {rp.text[:200]}")
    check("4b devis = scan_vision.devis(2)", abs(dv.get("usd", 0) - V.devis(2)["usd"]) < 1e-9, dv)
    check("4c le devis n'appelle pas Claude", APPELS_IA == [], len(APPELS_IA))
    check("4d devis-vision d'un scan inconnu -> 404", c.get("/api/scan/inconnu/devis-vision").status_code == 404)
    settings.ANTHROPIC_MODEL = "claude-2.1"
    rp = c.get(f"/api/scan/{SCAN}/devis-vision", headers={"Accept-Language": "en"})
    dv2 = rp.json() if rp.status_code == 200 else {}
    check("4e modèle sans vision : disponible False, raison traduite en anglais",
          dv2.get("disponible") is False and dv2.get("raison") and dv2["raison"] != V.RAISON_SANS_VISION, dv2)
    rp = c.post(f"/api/scan/{SCAN}/vision", json={"max_usd": 1.0})
    check("4f vision avec un modèle sans vision -> 503, aucun appel", rp.status_code == 503 and APPELS_IA == [],
          f"{rp.status_code} {rp.text[:200]}")
    settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

    rp = c.post(f"/api/scan/{SCAN}/vision", json={"max_usd": 0.00001})
    d = rp.json().get("detail") if rp.status_code == 409 else {}
    check("4g max_usd trop bas -> 409 {message, usd}", rp.status_code == 409 and isinstance(d, dict)
          and d.get("usd", 0) > 0 and d.get("message"), f"{rp.status_code} {rp.text[:200]}")
    check("4h … aucun appel Claude", APPELS_IA == [], len(APPELS_IA))
    devis_haiku = c.get(f"/api/scan/{SCAN}/devis-vision").json()["usd"]
    settings.ANTHROPIC_MODEL = "claude-sonnet-4-5"          # l'utilisateur change de modèle entre devis et lecture
    rp = c.post(f"/api/scan/{SCAN}/vision", json={"max_usd": devis_haiku})
    check("4i coût changé (autre modèle réglé) -> 409, aucun appel", rp.status_code == 409 and APPELS_IA == [],
          f"{rp.status_code} {len(APPELS_IA)}")
    settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
    rp = c.post(f"/api/scan/{SCAN}/vision", json={"max_usd": "beaucoup"})
    check("4j max_usd invalide -> 400", rp.status_code == 400, rp.status_code)
    rp = c.post(f"/api/scan/{SCAN}/vision", json={})
    check("4k max_usd absent -> 400", rp.status_code == 400, rp.status_code)

    verif = PL.verifier
    async def verif_402(op, categorie="", ref=None, *a, **k):
        raise HTTPException(402, {"code": "dz_plafond", "dz_plafond": {"motif": "global"}})
    PL.verifier = verif_402
    try:
        rp = c.post(f"/api/scan/{SCAN}/vision", json={"max_usd": 1.0})
    finally:
        PL.verifier = verif
    check("4l plafond -> 402 propagé, aucun appel", rp.status_code == 402 and APPELS_IA == [],
          f"{rp.status_code} {rp.text[:200]}")

    rp = c.post(f"/api/scan/{SCAN}/vision", json={"max_usd": 1.0})
    d = rp.json() if rp.status_code == 200 else {}
    check("4m vision -> 200, moteur claude, texte transcrit", rp.status_code == 200 and d.get("moteur") == "claude"
          and "Transcription Claude" in d.get("texte", "") and d.get("scan_id") == SCAN, f"{rp.status_code} {rp.text[:200]}")
    check("4n [[?mot]] -> position incertaine", any(d["texte"][i["debut"]:i["fin"]] == "lot"
                                                    for i in d.get("incertains", [])), d.get("incertains"))
    check("4o un appel (2 pages = un lot), usd payé", len(APPELS_IA) == 1 and d.get("usd", 0) > 0, len(APPELS_IA))
    check("4p le résultat remplace celui du cache", SP.obtenir(SCAN)["resultat"]["moteur"] == "claude")

    APPELS_IA.clear()
    rp = c.post(f"/api/scan/{SCAN_503}/vision", json={"max_usd": 1.0})
    check("4q le scan refusé en 503 se relit par Claude", rp.status_code == 200 and len(APPELS_IA) == 1,
          f"{rp.status_code} {rp.text[:200]}")

    # mixte : la page texte garde sa place, seule l'image part chez Claude
    APPELS_IA.clear()
    rp = c.post("/api/scan/lire", **multipart(("m.pdf", pdf_concat(pdf_texte(TXT1), pdf_images(1500)))))
    sm = rp.json()["scan_id"]
    dvm = c.get(f"/api/scan/{sm}/devis-vision").json()
    rp = c.post(f"/api/scan/{sm}/vision", json={"max_usd": 1.0})
    d = rp.json() if rp.status_code == 200 else {}
    t = d.get("texte", "")
    check("4r mixte : le devis ne compte que les pages image", dvm.get("pages") == 1, dvm)
    check("4s mixte : page texte puis transcription, positions recalées",
          0 <= t.find("selectionnable") < t.find("Transcription")
          and all(t[i["debut"]:i["fin"]] == "lot" for i in d.get("incertains", [])) and d.get("incertains"), d)
    rp = c.post("/api/scan/lire", **multipart(("t.pdf", pdf_texte(TXT1))))
    st = rp.json()["scan_id"]
    check("4t scan sans page image : devis-vision -> 422", c.get(f"/api/scan/{st}/devis-vision").status_code == 422)
    check("4u scan sans page image : vision -> 422", c.post(f"/api/scan/{st}/vision", json={"max_usd": 1}).status_code == 422)

    # rendu partiel : le second lot échoue
    APPELS_IA.clear()
    rp = c.post("/api/scan/lire", **multipart(*[(f"{i}.png", img(1300)) for i in range(6)]))
    s6 = rp.json()["scan_id"]
    n = {"i": 0}
    def post_partiel(url, headers=None, json=None, timeout=None, verify=None):
        n["i"] += 1
        if n["i"] == 2:
            raise RuntimeError("réseau coupé")
        return faux_post(url, headers=headers, json=json, timeout=timeout, verify=verify)
    MT.httpx.post = post_partiel
    try:
        rp = c.post(f"/api/scan/{s6}/vision", json={"max_usd": 1.0})
    finally:
        MT.httpx.post = faux_post
    d = rp.json() if rp.status_code == 200 else {}
    check("4v lot suivant en échec -> 200 partiel (pages_lues 4, erreur appel)", rp.status_code == 200
          and d.get("partiel") is True and d.get("pages_lues") == 4 and d.get("erreur") == "appel",
          f"{rp.status_code} {rp.text[:300]}")

    sx = SP.ranger(None, [{"genre": "image", "octets": img(1300)}])
    SP._CACHE[sx]["cree"] -= SP.TTL + 5
    check("4w scan expiré : devis -> 404", c.get(f"/api/scan/{sx}/devis-vision").status_code == 404)
    check("4x scan inconnu : vision -> 404", c.post("/api/scan/inconnu/vision", json={"max_usd": 1}).status_code == 404)
    settings.ANTHROPIC_API_KEY = ""
    rp = c.post(f"/api/scan/{SCAN}/vision", json={"max_usd": 1.0, "nouvelle": True}, headers={"Accept-Language": "en"})
    check("4y Claude non configuré -> 503 traduit", rp.status_code == 503
          and rp.json().get("detail") != V.RAISON_SANS_CLE, f"{rp.status_code} {rp.text[:200]}")
    settings.ANTHROPIC_API_KEY = "cle-de-banc"

    # ================================================================== 5. découpage
    print("\n[5] découpage")
    corps = ("Chapitre 1\n\n" + "Il était une fois un long texte. " * 10 + "\n\nChapitre 2\n\n"
             + "La suite arrive enfin, bien plus loin. " * 10)
    rp = c.post("/api/scan/decoupage", json={"texte": corps})
    d = rp.json() if rp.status_code == 200 else {}
    attendu = MA.segment_chapters(corps)
    ch = d.get("chapitres", [])
    check("5a chapitres de segment_chapters", [x.get("titre") for x in ch] == [a["title"] for a in attendu]
          and len(ch) == 2, d)
    check("5b caracteres = longueur du texte du chapitre", [x.get("caracteres") for x in ch]
          == [len(a["text"]) for a in attendu], ch)
    check("5c debut pointe sur le texte du chapitre", all(corps[x["debut"]:].startswith(a["text"][:30])
                                                          for x, a in zip(ch, attendu)), ch)
    rp = c.post("/api/scan/decoupage", json={"texte": "é" * (1024 * 1024 + 1)})
    check("5d texte > 2 Mo -> 413", rp.status_code == 413, rp.status_code)
    check("5e texte vide -> 400", c.post("/api/scan/decoupage", json={"texte": "   "}).status_code == 400)
    check("5f texte absent -> 400", c.post("/api/scan/decoupage", json={}).status_code == 400)

    # ================================================================== 7. revue finale
    print("\n[7] revue finale : échéance, argent, découpage exact")
    # m1 — échéance globale de la lecture locale
    lent = {"s": 0.0}
    def executer_lent(args, timeout):
        _time.sleep(lent["s"])
        return faux_executer(args, timeout)
    O._executer = executer_lent
    ech = SR.ECHEANCE_LIRE
    try:
        SR.ECHEANCE_LIRE = 0.5
        rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), ("p2.png", img(1400))))
        check("7a échéance passée avant toute page -> 504, message du délai total", rp.status_code == 504
              and "deux minutes" in rp.json().get("detail", ""), f"{rp.status_code} {rp.text[:200]}")
        SR.ECHEANCE_LIRE = 3.0
        lent["s"] = 1.2
        APPELS_OCR.clear()
        rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), ("p2.png", img(1400)), ("p3.png", img(1500))))
        d = rp.json() if rp.status_code == 200 else {}
        check("7b échéance au milieu : 200 partiel, pages_lues 2, la 3e jamais lue", rp.status_code == 200
              and d.get("partiel") is True and d.get("pages_lues") == 2 and "Deuxième" in d.get("texte", "")
              and "Page scannée" not in d.get("texte", "") and [w for w, _ in APPELS_OCR] == [1300, 1400],
              f"{rp.status_code} {rp.text[:200]} {APPELS_OCR}")
    finally:
        SR.ECHEANCE_LIRE = ech
        O._executer = faux_executer
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300))))
    check("7c lecture dans les temps : pas de partiel", rp.status_code == 200 and "partiel" not in rp.json())

    # I1 (a) — le devis porte le délai du serveur
    check("7d devis : delai_s = somme des délais des lots (10 pages = 180 + 180 + 120)",
          V.devis(10).get("delai_s") == 480 and V.devis(2).get("delai_s") == 120, V.devis(10))
    rp = c.get(f"/api/scan/{SCAN}/devis-vision")
    check("7e devis-vision porte delai_s", rp.status_code == 200 and rp.json().get("delai_s") == 120, rp.text[:200])

    # I1 (c)(d) — la transcription payée est gardée et rendue sans payer
    APPELS_IA.clear()
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300)), ("p2.png", img(1400))))
    SV1 = rp.json()["scan_id"]
    check("7f GET /vision sans lecture payée -> 404", c.get(f"/api/scan/{SV1}/vision").status_code == 404)
    check("7g GET /vision d'un scan inconnu -> 404", c.get("/api/scan/inconnu/vision").status_code == 404)
    rp = c.post(f"/api/scan/{SV1}/vision", json={"max_usd": 1.0})
    paye = rp.json() if rp.status_code == 200 else {}
    check("7h première lecture payée : un appel", rp.status_code == 200 and len(APPELS_IA) == 1 and not paye.get("deja_payee"),
          f"{rp.status_code} {len(APPELS_IA)}")
    check("7i drapeau levé après la lecture", SP.vision_en_cours(SV1) is False)
    rp = c.get(f"/api/scan/{SV1}/vision")
    g = rp.json() if rp.status_code == 200 else {}
    check("7j GET /vision rend la transcription payée (deja_payee), aucun appel", rp.status_code == 200
          and g.get("deja_payee") is True and g.get("texte") == paye.get("texte") and len(APPELS_IA) == 1, rp.text[:200])
    rp = c.post(f"/api/scan/{SV1}/vision", json={"max_usd": 1.0})
    g = rp.json() if rp.status_code == 200 else {}
    check("7k second POST sans nouvelle : la même transcription, aucun nouvel appel", rp.status_code == 200
          and g.get("deja_payee") is True and g.get("texte") == paye.get("texte") and len(APPELS_IA) == 1,
          f"{rp.status_code} {len(APPELS_IA)}")
    rp = c.post(f"/api/scan/{SV1}/vision", json={"max_usd": 1.0, "nouvelle": True})
    check("7l nouvelle: true -> une nouvelle lecture payée", rp.status_code == 200 and len(APPELS_IA) == 2
          and not rp.json().get("deja_payee"), f"{rp.status_code} {len(APPELS_IA)}")

    # I1 (b) — une seule lecture payante à la fois par scan
    rp = c.post("/api/scan/lire", **multipart(("p1.png", img(1300))))
    SV2 = rp.json()["scan_id"]
    APPELS_IA.clear()
    check("7m drapeau posé une fois seulement", SP.vision_debut(SV2) is True
          and isinstance(refus(SP.vision_debut, SV2), SP.VisionEnCours))
    rp = c.post(f"/api/scan/{SV2}/vision", json={"max_usd": 1.0})
    dd = rp.json().get("detail") if rp.status_code == 409 else {}
    check("7n POST pendant une lecture en cours -> 409 vision_en_cours, aucun appel", rp.status_code == 409
          and isinstance(dd, dict) and dd.get("code") == "vision_en_cours" and dd.get("message") and APPELS_IA == [],
          f"{rp.status_code} {rp.text[:200]}")
    rp = c.get(f"/api/scan/{SV2}/vision", headers={"Accept-Language": "en"})
    dd = rp.json().get("detail") if rp.status_code == 409 else {}
    check("7o GET pendant la lecture -> 409 vision_en_cours (message traduit)", rp.status_code == 409
          and dd.get("code") == "vision_en_cours" and dd.get("message") and "Claude" in dd["message"] and "déjà" not in dd["message"], rp.text[:200])
    SP.vision_fin(SV2)
    rp = c.post(f"/api/scan/{SV2}/vision", json={"max_usd": 0.00001})
    check("7p drapeau levé aussi après un refus (409 coût)", rp.status_code == 409 and SP.vision_en_cours(SV2) is False)

    # m2 — erreur réseau / délai au premier lot
    for exc, code, nom in ((httpx.ReadTimeout("lent"), 504, "délai"), (httpx.ConnectError("coupé"), 502, "réseau")):
        def post_ko(url, headers=None, json=None, timeout=None, verify=None, _e=exc):
            raise _e
        MT.httpx.post = post_ko
        try:
            rp = c.post(f"/api/scan/{SV2}/vision", json={"max_usd": 1.0})
        finally:
            MT.httpx.post = faux_post
        msg = rp.json().get("detail", "") if rp.status_code == code else ""
        check(f"7q premier lot en {nom} -> {code}, message « peut-être facturée »", rp.status_code == code
              and "facturée" in msg, f"{rp.status_code} {rp.text[:200]}")
        check(f"7r … drapeau levé, rien de gardé ({nom})", SP.vision_en_cours(SV2) is False
              and c.get(f"/api/scan/{SV2}/vision").status_code == 404)
    rp = c.post(f"/api/scan/{SV2}/vision", json={"max_usd": 1.0}, headers={"Accept-Language": "en"})
    check("7s (contrôle) la lecture réussit ensuite", rp.status_code == 200)

    # m4 — plusieurs lots : le plafond est jugé sur le TOTAL de la requête
    rp = c.post("/api/scan/lire", **multipart(*[(f"{i}.png", img(1300)) for i in range(6)]))
    SV3 = rp.json()["scan_id"]
    total = c.get(f"/api/scan/{SV3}/devis-vision").json()["usd"]
    charger = PL.charger
    PL.charger = lambda: {"global_usd": 0.000001, "par_moteur": {}}
    APPELS_IA.clear()
    try:
        rp = c.post(f"/api/scan/{SV3}/vision", json={"max_usd": total, "langue": "auto"})
    finally:
        PL.charger = charger
    pz = ((rp.json().get("detail") or {}).get("dz_plafond") or {}) if rp.status_code == 402 else {}
    un_lot = V._couts(4, "auto", MT.modele_sain("anthropic"))[0]
    check("7t 402 au montant TOTAL des deux lots (pas d'un seul), aucun appel", rp.status_code == 402
          and abs(pz.get("devis_usd", 0) - total) < 0.0002 and pz.get("devis_usd", 0) > un_lot + 1e-6 and APPELS_IA == [],
          f"{rp.status_code} {pz} total={total} lot={un_lot}")
    check("7u … drapeau levé après le 402", SP.vision_en_cours(SV3) is False)
    import sqlite3
    def registre():
        with sqlite3.connect(str(_tmp / "t.db")) as db:
            return db.execute("select count(*), coalesce(sum(estime_usd), 0) from depenses").fetchone()
    n0, u0 = registre()
    rp = c.post(f"/api/scan/{SV3}/vision", json={"max_usd": total, "langue": "auto"})
    n1, u1 = registre()
    # (le montant écrit par lot suit moteurs_texte.estimer, sans le modèle : constat hors lot de la revue finale)
    check("7z le jugement préalable sur le total n'écrit rien : une ligne de registre par lot (2)",
          rp.status_code == 200 and n1 - n0 == 2 and u1 > u0, f"{rp.status_code} {n1 - n0} {u1 - u0} {total}")

    # m5 — numéro dans le dépôt de la première page non lue (une page texte devant)
    rp = c.post("/api/scan/lire", **multipart(("m.pdf", pdf_concat(pdf_texte(TXT1), pdf_images(*[1300] * 6)))))
    SV4 = rp.json()["scan_id"]
    n = {"i": 0}
    def post_partiel2(url, headers=None, json=None, timeout=None, verify=None):
        n["i"] += 1
        if n["i"] == 2:
            raise RuntimeError("réseau coupé")
        return faux_post(url, headers=headers, json=json, timeout=timeout, verify=verify)
    MT.httpx.post = post_partiel2
    try:
        rp = c.post(f"/api/scan/{SV4}/vision", json={"max_usd": 1.0})
    finally:
        MT.httpx.post = faux_post
    d = rp.json() if rp.status_code == 200 else {}
    check("7v partiel : pages_lues 4 (images), premiere_page_non_lue 6 (page texte comptée)", rp.status_code == 200
          and d.get("pages_lues") == 4 and d.get("premiere_page_non_lue") == 6, f"{rp.status_code} {rp.text[:300]}")

    # I2 — le découpage rend le texte EXACT de chaque chapitre
    corps3 = ("CHAPITRE PREMIER\n\n" + "Il était une fois un long texte. " * 10 + "\n\nCHAPITRE DEUX\n\n"
              + "La suite arrive enfin, bien plus loin. " * 10 + "\n\nCHAPITRE TROIS\n\n" + "Et voici la fin. " * 12)
    rp = c.post("/api/scan/decoupage", json={"texte": corps3})
    ch = rp.json().get("chapitres", []) if rp.status_code == 200 else []
    attendu = MA.segment_chapters(corps3)
    check("7w trois chapitres, texte = segment_chapters", len(ch) == 3 and [x.get("texte") for x in ch]
          == [a["text"] for a in attendu], ch)
    check("7x aucun chapitre ne contient le titre du suivant", len(ch) == 3 and "CHAPITRE DEUX" not in ch[0]["texte"]
          and "CHAPITRE TROIS" not in ch[1]["texte"], [x.get("texte", "")[-40:] for x in ch])
    rp = c.post("/api/scan/decoupage", json={"texte": corps})
    ch2 = rp.json().get("chapitres", []) if rp.status_code == 200 else []
    check("7y deux chapitres : texte exact, caracteres = len(texte)", len(ch2) == 2
          and all(x["caracteres"] == len(x["texte"]) for x in ch2) and "Chapitre 2" not in ch2[0]["texte"], ch2)

# ====================================================================== 6. hors machine locale, journaux
print("\n[6] hors machine locale, journaux")
import _jeton_appareil as _JA                                       # noqa: E402
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    APPELS_OCR.clear(); APPELS_IA.clear()
    check("6a lire -> 403", c2.post("/api/scan/lire", **multipart(("p1.png", img(1300)))).status_code == 403)
    check("6b devis-vision -> 403", c2.get(f"/api/scan/{SCAN}/devis-vision").status_code == 403)
    check("6c vision -> 403", c2.post(f"/api/scan/{SCAN}/vision", json={"max_usd": 1.0}).status_code == 403)
    check("6d découpage -> 403", c2.post("/api/scan/decoupage", json={"texte": "abc"}).status_code == 403)
    check("6e rien n'a été lu ni envoyé", APPELS_OCR == [] and APPELS_IA == [], (APPELS_OCR, len(APPELS_IA)))

log = "\n".join(_JOURNAL)
check("6f aucun texte lu dans les journaux", SECRET not in log and "Bonjour" not in log and "selectionnable" not in log
      and "Transcription" not in log, [ln for ln in _JOURNAL if SECRET in ln or "Bonjour" in ln][:3])
check("6g journal de comptes des routes", "scan_routes" in log, log[-300:])
check("6h aucun PNG temporaire laissé au total", temporaires() == [], temporaires())

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
