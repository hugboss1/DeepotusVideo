# -*- coding: utf-8 -*-
"""t312 (28/10/2026) (C1 Scan, tâche 1) — banc du pont Windows.Media.Ocr (scan_ocr).
Ce que ce banc garde, par sections numérotées :
  1. preparer : niveaux de gris, agrandi ×2 sous 1200 px de large, réduit au-dessus de 10 000 px, image illisible refusée.
  2. lire_page avec la couture `_executer` remplacée : JSON nominal -> structure (boîtes ramenées à l'image d'origine),
     langue inconnue, délai, code d'erreur, JSON illisible, langue absente, PowerShell introuvable ; jamais de chemin ni
     de texte de l'image dans un message ; le PNG temporaire toujours supprimé.
  3. disponible : lecture des langues par PowerShell, mise en cache par processus, refus propre.
  4. Lecture RÉELLE (seulement si disponible()["ok"]) : « Bonjour le monde » rendu par Pillow en Arial, relu.
Données isolées (DEEPOTUS_DATA_DIR temporaire), aucun réseau, rien de payé.
Run (depuis backend/) : & $PY tests/test_scan_ocr.py"""
import io, json, os, pathlib, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzscanocr_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image, ImageDraw, ImageFont                         # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def png(w, h, couleur=(200, 30, 30)):
    b = io.BytesIO()
    Image.new("RGB", (w, h), couleur).save(b, "PNG")
    return b.getvalue()


from app.services import scan_ocr as S                              # noqa: E402

print("[1] preparer")
p = Image.open(io.BytesIO(S.preparer(png(600, 300))))
check("1a 600 px de large -> 1200", p.size == (1200, 600), p.size)
check("1b niveaux de gris", p.mode == "L", p.mode)
check("1c PNG rendu", p.format == "PNG", p.format)
p = Image.open(io.BytesIO(S.preparer(png(12000, 60))))
check("1d 12 000 px -> au plus 10 000", max(p.size) <= 10000 and p.size[0] >= 9990, p.size)
p = Image.open(io.BytesIO(S.preparer(png(1500, 800))))
check("1e 1500 px inchange", p.size == (1500, 800), p.size)
b = io.BytesIO(); Image.new("RGBA", (1300, 100), (0, 0, 0, 0)).save(b, "PNG")
p = Image.open(io.BytesIO(S.preparer(b.getvalue())))
check("1f transparence posee sur du blanc", p.getpixel((5, 5)) == 255, p.getpixel((5, 5)))
for lab, octets in (("octets quelconques", b"pas une image du tout"), ("vide", b""), ("PNG tronque", png(50, 50)[:40])):
    try:
        S.preparer(octets); check(f"1g image illisible ({lab}) -> ValueError", False, "aucune erreur")
    except ValueError as e:
        check(f"1g image illisible ({lab}) -> ValueError", "illisible" in str(e).lower(), str(e))

print("\n[2] lire_page, couture _executer remplacee")
NOMINAL = {"langue": "fr-FR", "angle": 0.5, "lignes": [
    {"texte": "Bonjour le monde", "mots": [
        {"texte": "Bonjour", "x": 100, "y": 40, "l": 300, "h": 60},
        {"texte": "le", "x": 420, "y": 40, "l": 60, "h": 60},
        {"texte": "monde", "x": 500, "y": 40, "l": 220, "h": 60}]},
    {"texte": "Deuxième ligne", "mots": [
        {"texte": "Deuxième", "x": 100, "y": 140, "l": 320, "h": 60},
        {"texte": "ligne", "x": 440, "y": 140, "l": 200, "h": 60}]}]}
appels = []


def faux(reponse=None, rc=0, err="", exc=None, attendre=None):
    def _f(args, timeout):
        i = args.index("-Image") if "-Image" in args else -1
        chemin = args[i + 1] if i >= 0 else None
        vu = {"args": list(args), "timeout": timeout, "chemin": chemin,
              "existait": bool(chemin) and os.path.exists(chemin),
              "taille": Image.open(chemin).size if chemin and os.path.exists(chemin) else None}
        appels.append(vu)
        if exc is not None:
            raise exc
        return rc, (json.dumps(reponse, ensure_ascii=False) if isinstance(reponse, dict) else (reponse or "")), err
    return _f


S._executer = faux(NOMINAL)
appels.clear()
r = S.lire_page(png(600, 300), "fr")
a = appels[-1]
check("2a script lance avec -Image et -Langue fr-FR", a["args"][-4:-2] == ["-Image", a["chemin"]] and a["args"][-2:] == ["-Langue", "fr-FR"]
      and "-File" in a["args"] and a["args"][a["args"].index("-File") + 1].endswith("scan_ocr.ps1"), a["args"])
check("2b options PowerShell sans profil ni interaction", all(o in a["args"] for o in ("-NoProfile", "-NonInteractive", "-ExecutionPolicy")))
check("2c delai 60 s", a["timeout"] == 60, a["timeout"])
check("2d PNG temporaire present pendant l'appel (image preparee 1200x600)", a["existait"] and a["taille"] == (1200, 600), a)
check("2e PNG temporaire supprime apres", not os.path.exists(a["chemin"]))
check("2f structure", set(r) == {"langue", "angle", "lignes", "largeur", "hauteur"} and r["langue"] == "fr"
      and r["angle"] == 0.5 and len(r["lignes"]) == 2, r)
check("2g dimensions de l'image d'origine", (r["largeur"], r["hauteur"]) == (600, 300), (r["largeur"], r["hauteur"]))
m = r["lignes"][0]["mots"][0]
check("2h boites ramenees a l'image d'origine (x2 -> /2)", (m["texte"], m["x"], m["y"], m["l"], m["h"]) == ("Bonjour", 50, 20, 150, 30), m)
check("2i textes et accents gardes", r["lignes"][1]["texte"] == "Deuxième ligne" and r["lignes"][1]["mots"][0]["texte"] == "Deuxième")
check("2j mots : exactement texte,x,y,l,h", all(set(w) == {"texte", "x", "y", "l", "h"} for li in r["lignes"] for w in li["mots"]))

S._executer = faux(dict(NOMINAL, langue="en-US", angle=None))
r = S.lire_page(png(1500, 900), "en")
check("2k langue en -> en-US, angle absent -> 0", appels[-1]["args"][-1] == "en-US" and r["langue"] == "en" and r["angle"] == 0, r["angle"])
check("2l image >= 1200 px : boites inchangees", r["lignes"][0]["mots"][0]["x"] == 100 and r["largeur"] == 1500)

S._executer = faux({"langue": "fr-FR", "angle": 0, "lignes": []})
r = S.lire_page(png(1300, 400))
check("2m page vide -> aucune ligne, langue fr par defaut", r["lignes"] == [] and r["langue"] == "fr" and appels[-1]["args"][-1] == "fr-FR")

n = len(appels)
for lab, lg in (("de", "de"), ("vide", ""), ("fr-FR", "fr-FR"), ("auto (passe double : route)", "auto")):
    try:
        S.lire_page(png(1300, 400), lg); check(f"2n langue {lab} -> ValueError", False, "aucune erreur")
    except ValueError as e:
        check(f"2n langue {lab} -> ValueError", "langue" in str(e).lower(), str(e))
check("2o langue refusee avant tout lancement", len(appels) == n)
try:
    S.lire_page(b"\x89PNG pas vraiment"); check("2p image illisible -> ValueError", False)
except ValueError as e:
    check("2p image illisible -> ValueError, sans lancement", "illisible" in str(e).lower() and len(appels) == n, str(e))


def doit_lever(lab, classe, mots_interdits=()):
    try:
        S.lire_page(png(600, 300), "fr")
    except classe as e:
        msg = str(e)
        a = appels[-1]
        propre = not any(x and x.lower() in msg.lower() for x in (a["chemin"], os.path.basename(a["chemin"] or "-"), tempfile.gettempdir(), *mots_interdits))
        check(f"{lab} -> {classe.__name__}", True)
        check(f"{lab} : message sans chemin ni texte lu", propre and msg.strip() != "", msg)
        check(f"{lab} : PNG temporaire supprime", a["existait"] and not os.path.exists(a["chemin"]))
        return
    except Exception as e:  # noqa: BLE001
        check(f"{lab} -> {classe.__name__}", False, f"{type(e).__name__}: {e}")
        return
    check(f"{lab} -> {classe.__name__}", False, "aucune erreur")


S._executer = faux(exc=subprocess.TimeoutExpired(["powershell"], 60))
doit_lever("2q delai", S.ScanErreur)
S._executer = faux(rc=1, err="Exception at C:\\Users\\olivi\\AppData\\Local\\Temp\\dzscan_x.png : Bonjour secret")
doit_lever("2r code 1 avec chemin dans stderr", S.ScanErreur, ("C:\\Users", "Bonjour secret", "olivi"))
S._executer = faux(reponse="{pas du json Bonjour")
doit_lever("2s JSON illisible", S.ScanErreur, ("Bonjour",))
S._executer = faux(reponse='["une", "liste"]')
doit_lever("2t JSON de mauvaise forme", S.ScanErreur)
S._executer = faux(reponse={"langue": "fr-FR", "lignes": [{"texte": "x", "mots": [{"texte": "x", "x": "a"}]}]})
doit_lever("2u mot sans boite numerique", S.ScanErreur)
S._executer = faux(rc=2, err="langue absente")
doit_lever("2v code 2 (langue non installee)", S.ScanIndisponible)
S._executer = faux(exc=FileNotFoundError(2, "introuvable", "powershell"))
doit_lever("2w PowerShell introuvable", S.ScanIndisponible, ("powershell.exe",))
S._executer = faux(exc=PermissionError(13, "refuse"))
doit_lever("2x PowerShell bloque", S.ScanIndisponible)
check("2y classes : RuntimeError", issubclass(S.ScanErreur, RuntimeError) and issubclass(S.ScanIndisponible, RuntimeError))

_plat = S.sys.platform
try:
    S.sys.platform = "linux"
    S._executer = faux(NOMINAL)
    n = len(appels)
    try:
        S.lire_page(png(600, 300)); check("2z hors Windows -> ScanIndisponible", False)
    except S.ScanIndisponible:
        check("2z hors Windows -> ScanIndisponible, sans lancement", len(appels) == n)
finally:
    S.sys.platform = _plat

print("\n[2b] revue t312 : ecriture temporaire, suppression, facteurs x/y")
S._executer = faux(NOMINAL)
_mkstemp = S.tempfile.mkstemp
def _mk_refus(*a, **k):
    raise OSError(28, "No space left on device", os.path.join(tempfile.gettempdir(), "dzscan_secret.png"))
S.tempfile.mkstemp = _mk_refus
try:
    n = len(appels)
    try:
        S.lire_page(png(600, 300)); check("2ba mkstemp en echec -> ScanErreur", False, "aucune erreur")
    except S.ScanErreur as e:
        check("2ba mkstemp en echec -> ScanErreur sans chemin, sans lancement",
              tempfile.gettempdir().lower() not in str(e).lower() and "dzscan" not in str(e)
              and e.__suppress_context__ and len(appels) == n, str(e))
    except Exception as e:  # noqa: BLE001
        check("2ba mkstemp en echec -> ScanErreur", False, f"{type(e).__name__}: {e}")
finally:
    S.tempfile.mkstemp = _mkstemp
cree = []
def _mk_note(*a, **k):
    fd, ch = _mkstemp(*a, **k); cree.append(ch); return fd, ch
_fdopen = S.os.fdopen
def _fdopen_refus(fd, *a, **k):
    os.close(fd); raise OSError(28, "No space left on device")
S.tempfile.mkstemp, S.os.fdopen = _mk_note, _fdopen_refus
try:
    try:
        S.lire_page(png(600, 300)); check("2bb ecriture en echec -> ScanErreur", False, "aucune erreur")
    except S.ScanErreur as e:
        check("2bb ecriture en echec -> ScanErreur, fichier retire", cree and not os.path.exists(cree[-1]), str(e))
    except Exception as e:  # noqa: BLE001
        check("2bb ecriture en echec -> ScanErreur", False, f"{type(e).__name__}: {e}")
finally:
    S.tempfile.mkstemp, S.os.fdopen = _mkstemp, _fdopen
journal = []
_sink = logger.add(lambda m: journal.append(str(m)), level="WARNING")
_unlink, essais = S.os.unlink, []
reste = None
def _unlink_une_fois(ch):
    essais.append(ch)
    if len(essais) == 1:
        raise PermissionError(32, "tenu par un autre programme")
    _unlink(ch)
def _unlink_jamais(ch):
    essais.append(ch)
    raise PermissionError(32, "tenu")
S.os.unlink = _unlink_une_fois
try:
    S.lire_page(png(600, 300))
    check("2bc suppression reessayee une fois puis reussie", len(essais) == 2 and not os.path.exists(essais[0]), essais)
    essais.clear()
    S.os.unlink = _unlink_jamais
    r = S.lire_page(png(600, 300))
    reste = essais[0]
    check("2bd suppression impossible : lecture rendue quand meme, deux essais", bool(r["lignes"]) and len(essais) == 2)
    check("2be journal 'non supprime' sans chemin", any("non supprim" in j for j in journal)
          and not any(reste in j or os.path.basename(reste) in j for j in journal), journal)
finally:
    S.os.unlink = _unlink
    logger.remove(_sink)
    if reste and os.path.exists(reste):
        os.unlink(reste)
S._executer = faux({"langue": "fr-FR", "angle": 0, "lignes": [{"texte": "x", "mots": [
    {"texte": "x", "x": 1000, "y": 1, "l": 1000, "h": 4}]}]})
r = S.lire_page(png(12000, 7))
m = r["lignes"][0]["mots"][0]
check("2bf bande 12000x7 preparee en 10000x5", appels[-1]["taille"] == (10000, 5), appels[-1]["taille"])
check("2bg facteurs x et y separes (y = 1 * 7/5 = 1.4, h = 5.6)", (m["x"], m["l"], m["y"], m["h"]) == (1200, 1200, 1.4, 5.6), m)

print("\n[3] disponible")
S._dispo = None
S._executer = faux('{"langues": ["en-US", "fr-FR"]}')
d1 = S.disponible(); n = len(appels); d2 = S.disponible()
check("3a ok + langues", d1 == {"ok": True, "langues": ["en-US", "fr-FR"], "raison": ""}, d1)
check("3b une seule commande -Langues", appels[-1]["args"][-1] == "-Langues" and "-File" in appels[-1]["args"])
check("3c mis en cache par processus", d2 == d1 and len(appels) == n)
S._dispo = None
S._executer = faux('{"langues": []}')
d = S.disponible()
check("3d aucune langue -> ok False + raison", d["ok"] is False and d["langues"] == [] and d["raison"], d)
S._dispo = None
S._executer = faux(exc=FileNotFoundError(2, "introuvable"))
d = S.disponible()
check("3e PowerShell introuvable -> ok False + raison", d["ok"] is False and d["raison"], d)
S._dispo = None
S._executer = faux(rc=1, err="C:\\chemin\\secret")
d = S.disponible()
check("3f code 1 -> ok False, raison sans stderr", d["ok"] is False and "secret" not in d["raison"], d)
S._dispo = None
S._executer = faux(exc=subprocess.TimeoutExpired(["powershell"], 20))
check("3g delai -> ok False", S.disponible()["ok"] is False)
S._dispo = None
S._executer = faux(exc=subprocess.TimeoutExpired(["powershell"], 20))
d = S.disponible()
n = len(appels)
S._executer = faux('{"langues": ["fr-FR"]}')
d2 = S.disponible()
check("3i delai non retenu : l'appel suivant relance et reussit", d["ok"] is False and d2["ok"] is True and len(appels) == n + 1, (d, d2))
S._dispo = None
S._executer = faux(exc=PermissionError(13, "refuse"))
d = S.disponible()
check("3j OSError non retenue", d["ok"] is False and S._dispo is None, S._dispo)
S._dispo = None
S._executer = faux(rc=1)
S.disponible()
check("3k echec franc (code 1) retenu", S._dispo is not None and S._dispo["ok"] is False)
S._dispo = None
_plat = S.sys.platform
try:
    S.sys.platform = "darwin"
    n = len(appels)
    d = S.disponible()
    check("3h hors Windows -> ok False sans lancement", d["ok"] is False and len(appels) == n and d["raison"], d)
finally:
    S.sys.platform = _plat

print("\n[4] lecture reelle (Windows.Media.Ocr)")
S._executer = S._executer_reel
S._dispo = None
t0 = time.perf_counter()
d = S.disponible()
t_dispo = time.perf_counter() - t0
if not d["ok"]:
    print(f"  SAUTE lecture reelle : {d['raison']}")
else:
    check("4a fr-FR disponible", "fr-FR" in d["langues"], d)
    im = Image.new("RGB", (900, 200), "white")
    police = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 72)
    ImageDraw.Draw(im).text((40, 50), "Bonjour le monde", fill="black", font=police)
    b = io.BytesIO(); im.save(b, "PNG")
    t0 = time.perf_counter()
    r = S.lire_page(b.getvalue(), "fr")
    t_lire = time.perf_counter() - t0
    mots = [w["texte"] for li in r["lignes"] for w in li["mots"]]
    print(f"  lu : {' | '.join(li['texte'] for li in r['lignes'])}  (disponible {t_dispo:.2f} s, lecture {t_lire:.2f} s)")
    check("4b « Bonjour » et « monde » retrouves", "Bonjour" in mots and "monde" in mots, mots)
    check("4c dimensions d'origine", (r["largeur"], r["hauteur"]) == (900, 200), (r["largeur"], r["hauteur"]))
    w = next((w for li in r["lignes"] for w in li["mots"] if w["texte"] == "Bonjour"), None)
    check("4d boite de « Bonjour » dans l'image d'origine", w and 20 <= w["x"] <= 80 and 40 <= w["y"] <= 110 and 150 <= w["l"] <= 400, w)
    reste = [f for f in os.listdir(tempfile.gettempdir()) if f.startswith("dzscan_")]
    check("4e aucun PNG temporaire laisse", reste == [], reste)
    r = S.lire_page(b.getvalue(), "en")
    check("4f passe en-US aussi", r["langue"] == "en" and any("monde" in li["texte"] for li in r["lignes"]), r["lignes"])

print(f"\n{ok} PASS, {fail} FAIL")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
