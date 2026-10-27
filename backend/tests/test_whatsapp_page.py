# -*- coding: utf-8 -*-
"""t311 tâche 7 (27/10/2026) — la page WhatsApp autonome (`/whatsapp/`).

Plan docs/superpowers/plans/2026-10-27-t311-agent-whatsapp.md (tâche 7).
[1] le montage    main.py monte frontend/whatsapp comme /plateau : index.html servi avec `no-cache, must-revalidate`,
                  GET /whatsapp -> 307 vers /whatsapp/, montage AVANT la SPA ;
[2] les fichiers  index.html charge, dans l'ordre, dz-i18n-dico.js, dz-i18n.js, icons/dz-icons.js, dz-plafonds.js (et
                  dialogue.js, la boîte du 402), puis whatsapp.js et ses onglets ; tokens /shared/deepotus.tokens.css ;
[3] les textes    chaque clé dzT("whatsapp.…") employée existe en FR et en EN avec les mêmes {variables} ; l'assemblé
                  est à jour ; aucun littéral français dans les scripts (scan des chaînes : accents, mots courants) ;
                  aucune chaîne dans index.html hors attributs techniques (le texte vient de dzT) ;
[4] les icônes    chaque dzIcone("dz-…") existe dans la suite (frontend/shared/icons/dz-icons.js) ; aucun emoji ;
[5] le banc node  frontend/whatsapp/qa/whatsapp.test.mjs (faux DOM, faux fetch) passe ;
[6] le backend    `noms_parametres` des modèles (les champs nommés de la page) ; aucun secret dans la page.
Run : & $PY tests/test_whatsapp_page.py   (depuis backend/)
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwapage_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["KAPSO_API_KEY"] = ""
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(REPO / "scripts"))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


PAGE = REPO / "frontend" / "whatsapp"
SH = REPO / "frontend" / "shared"
SCRIPTS = ["whatsapp.js", "onglets-conversations.js", "onglets-gestion.js"]


def lire(p):
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


HTML = lire(PAGE / "index.html")
JS = {n: lire(PAGE / n) for n in SCRIPTS}
CSS = lire(PAGE / "whatsapp.css")
MAIN = lire(BACKEND / "app" / "main.py")

# ── [1] le montage ────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[1] le montage")
check("1.1 classe _WhatsappStatic no-cache", "class _WhatsappStatic" in MAIN
      and "no-cache, must-revalidate" in MAIN[MAIN.find("class _WhatsappStatic"):][:900])
check("1.2 montée AVANT la SPA", 0 <= MAIN.find('app.mount("/whatsapp"') < MAIN.find("_SPAStaticFiles(") if "_SPAStaticFiles(" in MAIN
      else False, (MAIN.find('app.mount("/whatsapp"'), MAIN.find("_SPAStaticFiles(")))
try:
    from fastapi.testclient import TestClient               # noqa: E402
    from app.main import app                                 # noqa: E402
    c = TestClient(app, client=("127.0.0.1", 50000))
    r = c.get("/whatsapp", follow_redirects=False)
    check("1.3 GET /whatsapp -> 307 vers /whatsapp/", r.status_code == 307 and r.headers.get("location") == "/whatsapp/",
          (r.status_code, r.headers.get("location")))
    r = c.get("/whatsapp/")
    check("1.4 GET /whatsapp/ sert index.html", r.status_code == 200 and "data-dz-wa-page" in r.text, r.status_code)
    check("1.5 index.html en no-cache", r.headers.get("cache-control") == "no-cache, must-revalidate", r.headers.get("cache-control"))
    r = c.get("/whatsapp/whatsapp.js")
    check("1.6 whatsapp.js servi en no-cache", r.status_code == 200 and r.headers.get("cache-control") == "no-cache, must-revalidate",
          (r.status_code, r.headers.get("cache-control")))
except Exception as e:                                       # noqa: BLE001
    check("1.3 l'application se charge", False, repr(e))

# ── [2] les fichiers ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[2] les fichiers")
check("2.1 index.html, whatsapp.css et les scripts existent", HTML and CSS and all(JS.values()), [n for n, v in JS.items() if not v])
ordre = ["/shared/dz-i18n-dico.js", "/shared/dz-i18n.js", "/shared/icons/dz-icons.js", "/shared/dz-plafonds.js",
         "/shared/dialogue.js", "whatsapp.js", "onglets-conversations.js", "onglets-gestion.js"]
pos = [HTML.find(f'<script src="{s}"></script>') for s in ordre]
check("2.2 scripts dans l'ordre, une fois chacun", all(p >= 0 for p in pos) and pos == sorted(pos)
      and all(HTML.count(f'src="{s}"') == 1 for s in ordre), list(zip(ordre, pos)))
check("2.3 tokens Deepotus importés en tête de la feuille", CSS.lstrip().startswith("/*") and '@import url("/shared/deepotus.tokens.css");' in CSS[:2000])
check("2.4 feuille d'icônes et racine data-dz-wa-page", '<link rel="stylesheet" href="/shared/icons/dz-icons.css">' in HTML
      and "data-dz-wa-page" in HTML)
check("2.5 aucune couleur en dur hors des jetons (#hex)", not re.findall(r"#[0-9a-fA-F]{3,8}\b", re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)),
      re.findall(r"#[0-9a-fA-F]{3,8}\b", CSS)[:5])

# ── [3] les textes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[3] les textes")
DICO_F = SH / "i18n" / "whatsapp.json"
try:
    DICO = json.loads(lire(DICO_F))
except ValueError:
    DICO = {}
tout_js = "\n".join(JS.values())
employees = set(re.findall(r'\bT\("(whatsapp\.[a-z0-9_.]+)"', tout_js)) | set(re.findall(r'dzT\("(whatsapp\.[a-z0-9_.]+)"', tout_js)) \
    | set(re.findall(r'data-dz-t="(whatsapp\.[a-z0-9_.]+)"', HTML))
# clés composées à l'exécution : "whatsapp.refus." + code, etc. — leurs suffixes sont listés dans le code (tables)
prefixes = set(re.findall(r'"(whatsapp\.[a-z0-9_.]+[._])"\s*\+', tout_js))
check("3.1 le dictionnaire whatsapp.json existe et n'a que des clés whatsapp.*", DICO and all(k.startswith("whatsapp.") for k in DICO), len(DICO))
employees = {k for k in employees if not k.endswith((".", "_"))}      # « whatsapp.refus. » + code : préfixe, vu en 3.4
manque = sorted(k for k in employees if k not in DICO)
check("3.2 chaque clé employée existe", employees and not manque, manque[:10])
check("3.3 FR et EN non vides, mêmes {variables}", all(str(v.get("fr", "")).strip() and str(v.get("en", "")).strip()
      and sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"])) for v in DICO.values()))
for p in sorted(prefixes):
    check(f"3.4 clés composées {p}* présentes", any(k.startswith(p) for k in DICO), p)
for code in ("accord", "stop", "fenetre", "marketing", "plafond", "consentement", "prix", "bsuid_authentification", "occupee"):
    check(f"3.5 refus {code} traduit", f"whatsapp.refus.{code}" in DICO)
for motif in ("sans_cle", "plafond", "stop", "occupee", "sans_entrant", "moteur", "max_tours", "sans_carte", "declencheur", "carte"):
    check(f"3.6 motif {motif} traduit", f"whatsapp.motif.{motif}" in DICO)
try:
    import i18n_assembler as IA                              # noqa: E402
    a = IA.assembler()
    check("3.7 l'assemblé est à jour (deux copies identiques)", a == (SH / "dz-i18n-dico.js").read_bytes()
          == (REPO / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())
except Exception as e:                                       # noqa: BLE001
    check("3.7 l'assembleur se charge", False, repr(e))
MOTS_FR = re.compile(r"\b(le|la|les|des|une|un|du|aucun|aucune|envoyer|modèle|contact|fenêtre|numéro|clé|espace|"
                     r"brouillon|rejeter|enregistrer|ajouter|supprimer|lever|prendre|rendre|grille|marché)\b", re.I)


def litteraux(src):
    s = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    s = re.sub(r'(^|[^:"\'\\])//.*$', r"\1", s, flags=re.M)
    return [a or b for a, b in re.findall(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'', s)]


fr = [x for x in litteraux(tout_js) if not re.fullmatch(r"(?:wa-[\w-]*\s*)+", x)    # classes CSS « wa-… »
      and (re.search(r"[àâçéèêëîïôûùüÿœ]", x, re.I) or (" " in x.strip() and MOTS_FR.search(x)))]
check("3.8 aucun littéral français dans les scripts", not fr, fr[:8])
corps_html = re.sub(r"<!--.*?-->", "", HTML, flags=re.S)
corps_html = re.sub(r"<(script|style|title)[^>]*>.*?</\1>", "", corps_html, flags=re.S)
textes = [t.strip() for t in re.findall(r">([^<>]+)<", corps_html) if t.strip()]
check("3.9 index.html sans texte en dur (tout passe par dzT)", not textes, textes[:6])

# ── [4] les icônes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[4] les icônes")
SUITE = set(re.findall(r'^"(dz-[a-z0-9-]+)":', lire(SH / "icons" / "dz-icons.js"), re.M))
icones = set(re.findall(r'(?:dzIcone|icone)\("(dz-[a-z0-9-]+)"', tout_js))
check("4.1 des icônes de la suite, toutes connues", icones and icones <= SUITE, sorted(icones - SUITE))
emoji = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
check("4.2 aucun emoji", not emoji.search(HTML + tout_js + CSS + lire(DICO_F)))

# ── [5] le banc node ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[5] le banc node")
NODE = shutil.which("node")
if NODE:
    p = subprocess.run([NODE, str(PAGE / "qa" / "whatsapp.test.mjs")], capture_output=True, text=True, encoding="utf-8", timeout=120)
    check("5.1 whatsapp.test.mjs passe", p.returncode == 0 and "whatsapp : ok" in p.stdout, (p.stdout + p.stderr)[-2500:])
else:
    check("5.1 node présent", False, "node absent")

# ── [6] backend et secrets ────────────────────────────────────────────────────────────────────────────────────────────
print("\n[6] backend et secrets")
from app.services import whatsapp_echanges as WE             # noqa: E402
m = WE._modele_plat({"name": "rdv", "language": "fr", "category": "UTILITY", "status": "APPROVED", "components": [
    {"type": "BODY", "text": "Bonjour {{prenom}}, rendez-vous à {{heure}} ({{prenom}})"}]})
check("6.1 noms_parametres : les noms des paramètres nommés, sans doublon, dans l'ordre", m.get("noms_parametres") == ["prenom", "heure"]
      and m["parametres"] == "nommes" and m["n_parametres"] == 2, m)
m = WE._modele_plat({"name": "p", "language": "fr", "category": "MARKETING", "status": "APPROVED", "components": [
    {"type": "BODY", "text": "Promo {{1}} et {{2}}"}]})
check("6.2 positionnels : 1..n", m.get("noms_parametres") == ["1", "2"] and m["parametres"] == "positionnels", m)
check("6.3 la page ne lit ni n'affiche aucune clé ni jeton", not re.search(r"KAPSO_API_KEY|token|download_url|Authorization", tout_js + HTML, re.I))
check("6.4 aucune trace console dans la page", not re.search(r"console\.(log|info|debug|warn)\(", tout_js))

print(f"\n{ok} PASS, {fail} FAIL")
shutil.rmtree(_tmp, ignore_errors=True)
sys.exit(1 if fail else 0)
