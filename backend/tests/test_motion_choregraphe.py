# -*- coding: utf-8 -*-
"""t234 (lot « Studio : Animation », 17/10/2026) — le chorégraphe : script + direction → éléments du nœud Animation.

Plan docs/superpowers/plans/2026-10-17-studio-animation.md (t234), option A validée par l'utilisateur : un moteur de
texte choisi chorégraphie le nœud Animation en JSON BORNÉ. `POST /api/motion/choregraphier {script, direction:{style,
source, consigne}, moteur, modele, aspect, duree_s, marque}` → `{elements, moteur, modele, cout}`.

Zéro dépense : un FAUX OLLAMA écoute sur 127.0.0.1 (port tiré au hasard, jamais 8765) dans ce processus ; il rend, dans
l'ordre, les réponses mises dans sa file et note chaque requête. Un faux « hôte d'images » note toute requête : une URL
rendue par le modèle ne doit JAMAIS y arriver. Ce que ce banc garde :
  [M] le module : `choregraphier`, `valider`, `repli`, `systeme`, les bornes du plan ;
  [S] le prompt système impose le schéma (types, bornes, easings, presets, 24 éléments / 8 clés, filename présent
      seulement) et porte la consigne du style, du prompt / skill de la bibliothèque, ou la consigne éditée ;
  [V] JSON valide → éléments du nœud (keyframes triées, t dans 0..1), appel par tirer_garde (json, catégorie motion),
      plafond vérifié AVANT la requête ; `moteur`, `modele`, `cout` rendus ;
  [B] bornes et réparation : nombres hors bornes ramenés, NaN / infini / texte → défaut, 24 éléments et 8 clés au plus,
      easing inconnu → linear, cubic-bezier accepté (borné), preset inconnu → null, clés inconnues retirées, textes
      tronqués et nettoyés ;
  [P] sortie piégée : URL d'image jamais suivie, chemin hors dossier refusé, type inconnu retiré, code jamais évalué ;
  [R] sortie invalide : une seconde tentative, puis le repli déterministe ;
  [N] sans moteur (vide, non configuré) : le repli, sans erreur et sans requête ; plafond dépassé → 402 sans requête ;
  [D] le repli : une ligne = un élément texte, presets du style, temps proportionnel aux mots, déterministe ;
  [K] couleurs et police : le kit de marque de l'espace actif et sa typographie d'identité (connue), `marque` borné ;
  [T] le rendu suit la chorégraphie : `transform_at` et un vrai calque `render_element` mesuré ;
  [H] la route : 200, 400 (script vide, traduit FR / EN), 404 (style inconnu), 403 depuis un autre appareil ;
  [E] chaque message d'erreur neuf est traduit (scripts/i18n_l10_erreurs.py --check vert).
Run (depuis backend/) : & $PY tests/test_motion_choregraphe.py"""
import asyncio, json, math, os, pathlib, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzchor_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("GEMINI_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER",
           "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_k, None)
(_tmp / ".env").write_text("# fichier de l'utilisateur\n", encoding="utf-8")
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi import HTTPException                                   # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


# ── [M] le module ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[M] module")
try:
    from app.services import motion_choregraphe as CH               # noqa: E402
except ImportError as e:
    check("M0 app.services.motion_choregraphe existe", False, e)
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1)
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import motion_biblio as MB                        # noqa: E402
from app.services import plafonds as PLAF                           # noqa: E402
from app.services import brand_kits as BK                           # noqa: E402
from app.services import espaces as ES                              # noqa: E402
from app.services import identite as IDV                            # noqa: E402
from app.services import animation_service as AS                    # noqa: E402

CAC.appliquer({"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "ANTHROPIC_API_KEY": "", "OLLAMA_MODEL": "",
               "SUMMARIZER_PROVIDER": "", "PLANNER_PROVIDER": ""})

check("M1 fonctions publiques", all(callable(getattr(CH, n, None)) for n in ("choregraphier", "valider", "repli", "systeme")))
check("M2 bornes du plan", getattr(CH, "MAX_ELEMENTS", 0) == 24 and getattr(CH, "MAX_CLES", 0) == 8
      and getattr(CH, "BORNES", {}).get("x") == (0, 100) and CH.BORNES.get("y") == (0, 100)
      and CH.BORNES.get("scale") == (0.1, 4) and CH.BORNES.get("rotation") == (-720, 720)
      and CH.BORNES.get("opacity") == (0, 1), getattr(CH, "BORNES", None))
check("M3 presets et easings = ceux de la bibliothèque (nœud Animation)",
      tuple(CH.PRESETS) == MB.PRESETS and tuple(CH.EASINGS) == MB.EASINGS)
check("M4 types connus", tuple(CH.TYPES) == ("text", "sticker", "image"))

# ── faux Ollama + faux hôte d'images ──────────────────────────────────────────────────────────────────────────────
OLL = []                                    # corps reçus
FILE = []                                   # réponses à rendre, dans l'ordre (la dernière se répète)
HOTE = []                                   # requêtes reçues par le faux hôte d'images


class _Ollama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _rendre(self, code, obj):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/img"):
            HOTE.append(self.path)
            return self._rendre(200, {})
        self._rendre(200, {"models": [{"name": "llama3"}]})

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        OLL.append(corps)
        txt = FILE.pop(0) if len(FILE) > 1 else (FILE[0] if FILE else "{}")
        if self.path == "/api/generate":
            return self._rendre(200, {"response": txt, "done": True})
        self._rendre(404, {})


_srv = ThreadingHTTPServer(("127.0.0.1", 0), _Ollama)
PORT = _srv.server_address[1]
assert PORT != 8765
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{PORT}"
settings.OLLAMA_URL = URL
CAC.appliquer({"OLLAMA_MODEL": "llama3"})

# une image « déjà présente » dans le dossier des images de l'application
settings.images_path.mkdir(parents=True, exist_ok=True)
from PIL import Image                                               # noqa: E402
Image.new("RGBA", (40, 40), (255, 0, 0, 255)).save(settings.images_path / "logo_banc.png")

# la marque de l'espace actif : un kit aux couleurs reconnaissables, une typographie d'identité connue
KID = BK.enregistrer({"id": "kit_banc", "name": "Banc", "brand_color": "#112233", "accent_color": "#44AA66"})
BK.activer(KID)
EID = ES.espace_courant()
IDV.ecrire(EID, {"typographies": [{"nom": "Bebas Neue", "usage": "titres"}]})

SCRIPT = "Le fond marin s'éveille\nDeepotus plonge\nRejoins la meute dès ce soir"


def tirer(corps):
    return asyncio.run(CH.choregraphier(corps))


def el(**k):
    base = {"type": "text", "text": "Bonjour", "start": 0, "dur": 1, "hold": 1,
            "keyframes": [{"t": 0, "x": 20, "y": 50, "scale": 1, "rotation": 0, "opacity": 0, "easing": "easeOut"},
                          {"t": 1, "x": 80, "y": 50, "scale": 1, "rotation": 0, "opacity": 1}]}
    base.update(k)
    return base


def rep(*elements, enveloppe=True):
    return json.dumps({"elements": list(elements)} if enveloppe else list(elements))


# ── [S] le prompt système ─────────────────────────────────────────────────────────────────────────────────────────
print("[S] prompt système")
fiche = MB.lire("style-kinetic-type")
sy = CH.systeme(CH.direction({"style": "style-kinetic-type"}), aspect="9:16", duree_s=12, images=["logo_banc.png"])
check("S1 types text / sticker / image", all(t in sy for t in ('"text"', '"sticker"', '"image"')), sy[:400])
check("S2 bornes chiffrées", all(b in sy for b in ("0-100", "0.1-4", "-720", "720", "0-1")), sy[:600])
check("S3 easings et presets listés", all(e in sy for e in MB.EASINGS) and all(p in sy for p in MB.PRESETS)
      and "cubic-bezier" in sy)
check("S4 24 éléments et 8 clés au plus", "24" in sy and "8" in sy)
check("S5 filename : seulement une image déjà présente (listée), jamais d'URL",
      "logo_banc.png" in sy and "URL" in sy)
check("S6 la consigne du style (FR) et son rythme y sont", fiche["consigne"]["fr"][:80] in sy
      and fiche["rythme"]["fr"][:40] in sy)
sy_en = CH.systeme(CH.direction({"style": "style-kinetic-type"}, langue="en"), aspect="9:16", duree_s=12)
check("S6b en anglais : la consigne EN", fiche["consigne"]["en"][:80] in sy_en)
imp = MB.importer_prompt({"titre": "Ma fiche", "texte": "CONSIGNE-IMPORT-ZETA : tout en rebonds",
                          "url": "https://exemple.org/fiche", "auteur": "moi", "themes": ["shapes"]})
d = CH.direction({"style": "style-shapes", "source": imp["id"]})
check("S7 la source (prompt importé) entre dans la consigne", "CONSIGNE-IMPORT-ZETA" in CH.systeme(d, "16:9", 8))
d2 = CH.direction({"style": "style-shapes", "source": {"id": imp["id"]}, "consigne": "CONSIGNE-EDITEE-OMEGA"})
s2 = CH.systeme(d2, "16:9", 8)
check("S8 la consigne éditée (nœud) prime sur le texte de la source", "CONSIGNE-EDITEE-OMEGA" in s2
      and "CONSIGNE-IMPORT-ZETA" not in s2)
d3 = CH.direction({"consigne": "x" * 50_000})
check("S9 consigne tronquée (bornée)", len(CH.systeme(d3, "16:9", 8)) < 30_000)
try:
    CH.direction({"style": "style-inexistant"})
    e404 = None
except LookupError as e:
    e404 = e
check("S10 style inconnu → LookupError", e404 is not None)
try:
    CH.direction({"source": "prompt-absent"})
    e404 = None
except LookupError as e:
    e404 = e
check("S11 source inconnue → LookupError", e404 is not None)

# ── [V] JSON valide ───────────────────────────────────────────────────────────────────────────────────────────────
print("[V] JSON valide")
ORDRE = []
_v0 = PLAF.verifier


async def _espion(o, categorie="", ref=None, confirme=None):
    ORDRE.append((o.get("provider"), categorie, len(OLL)))
    return await _v0(o, categorie, ref, confirme)


PLAF.verifier = _espion
OLL.clear()
FILE[:] = [rep(el(text="Le fond marin", keyframes=[
    {"t": 1, "x": 80, "y": 50, "scale": 1, "rotation": 0, "opacity": 1},
    {"t": 0, "x": 20, "y": 50, "scale": 1, "rotation": 0, "opacity": 0, "easing": "easeOutBack"}]),
    el(type="image", filename="logo_banc.png", start=1))]
r = tirer({"script": SCRIPT, "direction": {"style": "style-kinetic-type"}, "moteur": "ollama", "modele": "",
           "aspect": "9:16", "duree_s": 8, "images": ["logo_banc.png"]})
PLAF.verifier = _v0
els = r.get("elements", [])
check("V1 deux éléments rendus", len(els) == 2, r)
check("V2 moteur / modèle / coût rendus", r.get("moteur") == "ollama" and r.get("modele") == "llama3"
      and r.get("cout", {}).get("nature") == "gratuit" and r.get("repli") is False, {k: r.get(k) for k in ("moteur", "modele", "cout", "repli")})
check("V3 appel en JSON (format natif Ollama) au modèle choisi", OLL and OLL[0].get("format") == "json"
      and OLL[0].get("model") == "llama3", OLL[:1])
check("V4 plafond vérifié AVANT la requête, catégorie motion", ORDRE and ORDRE[0] == ("ollama", "motion", 0), ORDRE)
k0 = els[0].get("keyframes", []) if els else []
check("V5 keyframes triées par t", [k["t"] for k in k0] == [0, 1] and k0[0]["x"] == 20, k0)
check("V6 forme du nœud : id, type, style, start / dur / hold, preset",
      els and all(set(("id", "type", "style", "keyframes", "start", "dur", "hold", "preset")) <= set(e) for e in els), els[:1])
check("V7 l'image présente est gardée telle quelle", len(els) > 1 and els[1]["type"] == "image"
      and els[1]["filename"] == "logo_banc.png" and "text" not in els[1], els[1:])
check("V8 ids uniques", len({e["id"] for e in els}) == len(els))
check("V9 le prompt envoyé porte le script et le schéma", OLL and "Deepotus plonge" in OLL[0].get("prompt", "")
      and "cubic-bezier" in OLL[0].get("system", ""))

# ── [B] bornes et réparation ──────────────────────────────────────────────────────────────────────────────────────
print("[B] bornes")
brut = {"elements": [
    {"type": "text", "text": "A\x00B\x07C" + "z" * 900, "start": -5, "dur": 9999, "hold": "long",
     "keyframes": [{"t": 7, "x": 500, "y": -40, "scale": 99, "rotation": 99999, "opacity": -3, "easing": "rebond"},
                   {"t": -2, "x": float("nan"), "y": float("inf"), "scale": 0, "rotation": True, "opacity": "0",
                    "easing": "cubic-bezier(0.2, 5, 0.3, 1)"}],
     "eval": "__import__('os')", "onload": "x", "preset": "explosion", "style": {"size": 99999, "font": "Comic"}}]
    + [el(text=f"n{i}") for i in range(40)]}
v = CH.valider(brut, images=[], marque=CH.marque(None), duree_s=10)
e0 = v[0] if v else {}
k = sorted(e0.get("keyframes", []), key=lambda q: q["t"])
check("B1 24 éléments au plus", len(v) == 24, len(v))
check("B2 t ramené dans 0..1 et trié", [q["t"] for q in k] == [0, 1], k)
check("B3 x / y / scale / rotation / opacity bornés",
      k and k[1]["x"] == 100 and k[1]["y"] == 0 and k[1]["scale"] == 4 and k[1]["rotation"] == 720 and k[1]["opacity"] == 0, k)
check("B4 NaN / infini / texte / booléen → valeur par défaut, finie",
      k and all(isinstance(k[0][c], (int, float)) and not isinstance(k[0][c], bool) and math.isfinite(k[0][c])
                for c in ("x", "y", "scale", "rotation", "opacity")) and k[0]["scale"] >= 0.1
      and k[0]["x"] == 50 and k[0]["y"] == 50 and k[0]["rotation"] == 0 and k[0]["opacity"] == 1, k)
check("B5 easing inconnu → linear ; cubic-bezier borné", k and k[1]["easing"] == "linear"
      and k[0]["easing"].startswith("cubic-bezier(") and "5" not in k[0]["easing"].split(",")[1], k)
check("B6 clés inconnues retirées, preset inconnu → null", "eval" not in e0 and "onload" not in e0 and e0.get("preset") is None, e0)
check("B7 texte nettoyé (sans caractère de contrôle) et tronqué", e0.get("text", "").startswith("ABC")
      and len(e0["text"]) <= CH.MAX_TEXTE, len(e0.get("text", "")))
check("B8 start / dur / hold bornés et numériques", e0.get("start") == 0 and 0 < e0.get("dur", 0) <= 10
      and e0.get("hold") == 0, {c: e0.get(c) for c in ("start", "dur", "hold")})
check("B9 taille bornée, police inconnue → celle de la marque", e0.get("style", {}).get("size", 0) <= 400
      and e0["style"]["font"] == "Bebas Neue", e0.get("style"))
neuf = el(keyframes=[{"t": i / 11, "x": i * 5, "y": 50, "scale": 1, "rotation": 0, "opacity": 1} for i in range(12)])
v = CH.valider({"elements": [neuf]}, images=[], marque=CH.marque(None), duree_s=10)
check("B10 8 clés au plus par élément", v and len(v[0]["keyframes"]) == 8, v and len(v[0]["keyframes"]))
v = CH.valider([el(keyframes=[], preset="pop")], images=[], marque=CH.marque(None), duree_s=10)
check("B11 sans clés mais preset connu → les deux clés du preset (comme le nœud)",
      v and v[0]["preset"] == "pop" and len(v[0]["keyframes"]) == 2 and v[0]["keyframes"][0]["scale"] == 0.3
      and v[0]["keyframes"][0]["easing"] == "easeOutBack", v)
v = CH.valider([el(keyframes=[{"t": 0.5, "x": 30, "y": 30}])], images=[], marque=CH.marque(None), duree_s=10)
check("B12 une seule clé → complétée en deux clés (t 0 et 1), valeurs complétées",
      v and [q["t"] for q in v[0]["keyframes"]] == [0, 1] and v[0]["keyframes"][0]["x"] == 30
      and v[0]["keyframes"][0]["opacity"] == 1, v)
try:
    CH.valider({"rien": 1}, images=[], marque=CH.marque(None), duree_s=8)
    vb = None
except ValueError as e:
    vb = e
check("B13 un objet sans éléments valides → ValueError", vb is not None)

# ── [P] sortie piégée ─────────────────────────────────────────────────────────────────────────────────────────────
print("[P] piégée")
SENTINELLE = _tmp / "piege_evalue.txt"
piege = [el(type="image", filename=f"{URL}/img/a.png"), el(type="sticker", filename="https://exemple.org/x.png"),
         el(type="image", filename="../../secrets.png"), el(type="image", filename="C:\\Windows\\win.ini"),
         el(type="image", filename="absente.png"), el(type="script", text="alert(1)"),
         el(type="html", text="<img src=x>"), el(text=f"__import__('pathlib').Path(r'{SENTINELLE}').touch()"),
         el(type="sticker", filename="logo_banc.png"), el(type="video", filename="logo_banc.png")]
v = CH.valider({"elements": piege}, images=["logo_banc.png", "../../secrets.png"], marque=CH.marque(None), duree_s=8)
types_ = [(e["type"], e.get("filename"), e.get("text")) for e in v]
check("P1 URL d'image : élément retiré, et JAMAIS demandée au réseau", not any("http" in str(t[1]) for t in types_)
      and not HOTE, (types_, HOTE))
check("P2 chemin hors dossier / absolu / absent → retiré", not any(t[1] in ("../../secrets.png", "C:\\Windows\\win.ini",
                                                                             "absente.png") for t in types_), types_)
check("P3 types inconnus retirés", all(t[0] in CH.TYPES for t in types_), types_)
check("P4 le texte piégé reste un TEXTE, jamais évalué", any(t[0] == "text" and "__import__" in (t[2] or "") for t in types_)
      and not SENTINELLE.exists())
check("P5 le sticker présent est gardé", ("sticker", "logo_banc.png", None) in types_, types_)
OLL.clear()
FILE[:] = [f"__import__('pathlib').Path(r'{SENTINELLE}').touch()"]
r = tirer({"script": SCRIPT, "direction": {"style": "style-kinetic-type"}, "moteur": "ollama", "duree_s": 8})
check("P6 une réponse en code (pas en JSON) n'est jamais exécutée → repli", r.get("repli") is True
      and not SENTINELLE.exists() and len(OLL) == 2, (r.get("repli"), len(OLL)))
check("P7 aucune URL suivie pendant tout le banc", not HOTE, HOTE)

# ── [R] invalide → seconde tentative → repli ──────────────────────────────────────────────────────────────────────
print("[R] tentatives")
OLL.clear()
FILE[:] = ["je ne sais pas faire de JSON", rep(el(text="Seconde chance"))]
r = tirer({"script": SCRIPT, "moteur": "ollama", "duree_s": 8})
check("R1 première réponse illisible → seconde tentative, rendue", len(OLL) == 2 and r.get("repli") is False
      and [e.get("text") for e in r.get("elements", [])] == ["Seconde chance"] and r.get("tentatives") == 2, r)
OLL.clear()
FILE[:] = ['{"elements": [{"type": "html"}]}', '{"elements": "aucun"}']
r = tirer({"script": SCRIPT, "direction": {"style": "style-kinetic-type"}, "moteur": "ollama", "duree_s": 8})
check("R2 deux sorties invalides → repli déterministe, sans erreur", len(OLL) == 2 and r.get("repli") is True
      and [e.get("text") for e in r.get("elements", [])] == SCRIPT.split("\n"), r)
check("R3 le repli garde moteur / modèle demandés et dit pourquoi", r.get("moteur") == "ollama" and r.get("raison"), r)

# ── [N] sans moteur ───────────────────────────────────────────────────────────────────────────────────────────────
print("[N] sans moteur")
OLL.clear()
r = tirer({"script": SCRIPT, "direction": {"style": "style-kinetic-type"}, "moteur": "", "duree_s": 8})
check("N1 moteur vide → repli, aucune requête, aucune erreur", r.get("repli") is True and not OLL
      and r.get("raison") == "sans_moteur" and r.get("tentatives") == 0
      and len(r.get("elements", [])) == 3 and r.get("cout", {}).get("nature") == "gratuit", r)
r = tirer({"script": SCRIPT, "moteur": "anthropic", "modele": "claude-x", "duree_s": 8})
check("N2 moteur non configuré → repli sans requête", r.get("repli") is True and not OLL
      and r.get("raison") == "non_configure" and r.get("tentatives") == 0, r)
r = tirer({"script": SCRIPT, "moteur": "inconnu", "duree_s": 8})
check("N3 moteur inconnu → repli", r.get("repli") is True and not OLL and r.get("raison") == "moteur_inconnu")
CAC.appliquer({"OPENAI_API_KEY": "sk-faux-banc-t234-000000000000000000"})
r = tirer({"script": SCRIPT, "moteur": "openai", "modele": "sk-proj-abcdefghijklmnopqrstuvwxyz0123", "duree_s": 8})
check("N3b modèle qui ressemble à une clé → repli AVANT toute garde de dépense, clé non recopiée",
      r.get("raison") == "modele_fautif" and r.get("tentatives") == 0 and "abcdefghij" not in json.dumps(r), r)
CAC.appliquer({"OPENAI_API_KEY": ""})
PLAF.enregistrer({"global_usd": 0.000001, "par_moteur": {}})
CAC.appliquer({"OPENAI_API_KEY": "sk-faux-banc-t234-000000000000000000"})
try:
    tirer({"script": SCRIPT, "moteur": "openai", "modele": "gpt-x", "duree_s": 8})
    r402 = None
except HTTPException as e:
    r402 = e
check("N4 plafond dépassé → 402 dz_plafond, AUCUNE requête", r402 is not None and r402.status_code == 402
      and not OLL, r402)
CAC.appliquer({"OPENAI_API_KEY": ""})
PLAF.enregistrer({"global_usd": 0, "par_moteur": {}})

# ── [D] le repli ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[D] repli")
fk = MB.lire("style-kinetic-type")
rp = CH.repli("Un\nDeux mots ici\n\n  \nTrois mots là encore", fk, CH.marque(None), duree_s=12)
check("D1 une ligne non vide = un élément texte", [e["text"] for e in rp] == ["Un", "Deux mots ici", "Trois mots là encore"], rp)
check("D2 presets pris dans le style, dans l'ordre", [e["preset"] for e in rp] == fk["presets"][:3], [e["preset"] for e in rp])
check("D3 les clés sont celles du preset", rp[0]["keyframes"][0]["scale"] == 0.3 and rp[0]["keyframes"][1]["scale"] == 1)
starts = [e["start"] for e in rp]
check("D4 temps proportionnel aux mots (1 / 3 / 4 mots sur 12 s)", abs(starts[1] - 1.5) < 0.01 and abs(starts[2] - 6) < 0.01, starts)
fin = rp[-1]["start"] + rp[-1]["dur"] + rp[-1]["hold"]
check("D5 le dernier tient jusqu'à la fin, aucun ne déborde", abs(fin - 12) < 0.01
      and all(e["start"] + e["dur"] + e["hold"] <= 12 + 1e-6 for e in rp), fin)
check("D6 déterministe (deux appels identiques)", rp == CH.repli("Un\nDeux mots ici\n\n  \nTrois mots là encore", fk,
                                                                  CH.marque(None), duree_s=12))
check("D7 sans style : fade-in", [e["preset"] for e in CH.repli("a\nb", None, CH.marque(None), 4)] == ["fade-in", "fade-in"])
check("D8 24 lignes au plus", len(CH.repli("\n".join(f"l{i}" for i in range(60)), None, CH.marque(None), 30)) == 24)

# ── [K] marque ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] marque")
m = CH.marque(None)
check("K1 couleurs du kit de l'espace actif, police de son identité", m.get("couleur") == "#44AA66"
      and m.get("marque") == "#112233" and m.get("police") == "Bebas Neue", m)
check("K2 éléments du repli habillés de la marque", all(e["style"]["color"] == "#44AA66" and e["style"]["font"] == "Bebas Neue"
                                                          for e in rp), rp[0]["style"])
v = CH.valider([el(role="marque"), el(style={"color": "#FFFFFF"})], images=[], marque=m, duree_s=8)
check("K3 role « marque » → couleur de marque ; sinon l'accent (couleur du modèle ignorée)",
      v[0]["style"]["color"] == "#112233" and v[1]["style"]["color"] == "#44AA66", [e["style"] for e in v])
m2 = CH.marque({"couleur": "#ABCDEF", "police": "Anton", "marque": "pas une couleur"})
check("K4 `marque` explicite : couleur et police connue prises, valeur fautive ignorée",
      m2["couleur"] == "#ABCDEF" and m2["police"] == "Anton" and m2["marque"] == "#112233", m2)
check("K5 police inconnue → celle de l'identité", CH.marque({"police": "Wingdings"})["police"] == "Bebas Neue")
IDV.ecrire(EID, {"typographies": [{"nom": "Police Fantaisie", "usage": "titres"}]})
check("K6 typographie d'identité non livrée → Anton (défaut du nœud)", CH.marque(None)["police"] == "Anton")
IDV.ecrire(EID, {"typographies": [{"nom": "Bebas Neue", "usage": "titres"}]})
check("K7 marque=False → couleurs par défaut du nœud", CH.marque(False)["couleur"] == "#00e5ff")

# ── [T] le rendu suit la chorégraphie ─────────────────────────────────────────────────────────────────────────────
print("[T] rendu")
v = CH.valider([el(start=0.5, dur=1, hold=1)], images=[], marque=m, duree_s=8)[0]
check("T1 transform_at : invisible avant start", AS.transform_at(v, 0.4) is None)
a, b = AS.transform_at(v, 0.5), AS.transform_at(v, 1.5)
check("T2 transform_at : x 20 au début, 80 à la fin de l'entrée", a and abs(a["x"] - 20) < 1e-6 and b and abs(b["x"] - 80) < 1e-6, (a, b))
check("T3 invisible après start + dur + hold", AS.transform_at(v, 2.6) is None)


def centre_x(e, t, W=400, H=400):
    lay = AS.render_element(e, AS.transform_at(e, t), W, H)
    bb = lay.getbbox()
    return None if bb is None else (bb[0] + bb[2]) / 2 / W * 100


v["keyframes"][0]["opacity"] = 1
v["style"]["size"] = 24
cx0, cx1 = centre_x(v, 0.5), centre_x(v, 1.5)
check("T4 calque réel : le texte est centré à x 20 puis à x 80 (± 3)", cx0 is not None and abs(cx0 - 20) < 3
      and cx1 is not None and abs(cx1 - 80) < 3, (cx0, cx1))
for i, e in enumerate(rp):
    s = e["start"]
    vis = AS.transform_at(e, s + 0.01) is not None and AS.transform_at(e, max(0, s - 0.05)) is None if s > 0 else True
    check(f"T5.{i} repli : élément {i} visible dans sa tranche seulement", vis)
fin_ = AS.transform_at(rp[-1], 11.99)
check("T6 repli : la dernière ligne est pleinement visible à la fin", fin_ and abs(fin_["opacity"] - 1) < 1e-6, fin_)

# ── [H] la route ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[H] route")
c = TestClient(app)
OLL.clear()
FILE[:] = [rep(el(text="Par la route"))]
r = c.post("/api/motion/choregraphier", json={"script": SCRIPT, "direction": {"style": "style-kinetic-type"},
                                               "moteur": "ollama", "aspect": "9:16", "duree_s": 8})
check("H1 200 et éléments", r.status_code == 200 and [e["text"] for e in r.json().get("elements", [])] == ["Par la route"],
      (r.status_code, r.text[:300]))
r = c.post("/api/motion/choregraphier", json={"script": "   ", "moteur": ""})
check("H2 script vide → 400 en français", r.status_code == 400 and "script" in r.json().get("detail", "").lower(), r.text)
r = c.post("/api/motion/choregraphier", json={"script": "  "}, headers={"Accept-Language": "en"})
check("H3 … et en anglais avec Accept-Language", r.status_code == 400 and "empty" in r.json().get("detail", "").lower(), r.text)
r = c.post("/api/motion/choregraphier", json={"script": "a", "direction": {"style": "style-zzz"}})
check("H4 style inconnu → 404", r.status_code == 404, r.status_code)
r = c.post("/api/motion/choregraphier", content=b"[1,2]", headers={"Content-Type": "application/json"})
check("H5 corps non objet → 400", r.status_code == 400, r.status_code)
r = c.post("/api/motion/choregraphier", json={"script": "a\nb", "moteur": "", "aspect": "21:9", "duree_s": 9999})
j = r.json() if r.status_code == 200 else {}
check("H6 aspect inconnu → 9:16, durée bornée", r.status_code == 200 and j.get("aspect") == "9:16"
      and j.get("duree_s") == CH.DUREE_MAX, j)
cd = TestClient(app, client=("192.168.1.50", 5000))
check("H7 autre appareil → refusé", cd.post("/api/motion/choregraphier", json={"script": "a"}).status_code in (401, 403))

# ── [E] traductions ───────────────────────────────────────────────────────────────────────────────────────────────
print("[E] traductions")
p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], cwd=str(RACINE),
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
check("E1 i18n_l10_erreurs --check vert (messages neufs traduits)", p.returncode == 0, (p.stdout + p.stderr)[-400:])

import types                                                        # noqa: E402
from app.api import motion_biblio_routes as MR                      # noqa: E402
try:
    asyncio.run(MR.choregraphier(types.SimpleNamespace(client=types.SimpleNamespace(host="192.168.1.50"))))
    g = 0
except HTTPException as e:
    g = e.status_code
check("H8 la route a sa propre garde de boucle locale (403, même appairé)", g == 403, g)

_srv.shutdown()
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
