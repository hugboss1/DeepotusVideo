# -*- coding: utf-8 -*-
"""t134 (traduction, lot 0, 07/10/2026) — la langue de l'interface : français (langue de référence) ou anglais, choisie
à l'installation, basculée dans les Réglages.

  [1] le runtime /shared/dz-i18n.js (source frontend/shared, copie dist octet pour octet), EXÉCUTÉ sous node : ordre de
      résolution (bascule localStorage dz_lang > choix de l'installation > fr), dzT et ses variables, clé absente,
      surcouche FR→EN par correspondance EXACTE (espaces gardés, rien de partiel), en-tête Accept-Language sur /api/.
  [2] le dictionnaire : frontend/shared/i18n/*.json (clés zone.objet.role, fr et en non vides, mêmes {variables}),
      assemblé par scripts/i18n_assembler.py dans /shared/dz-i18n-dico.js (assemblage rejoué = octets identiques).
  [3] les neuf pages chargent le dictionnaire puis le runtime, AVANT le bundle et les modules des labs.
  [4] le backend : UI_LANG (défaut fr), /api/health.ui_lang, GET/POST /api/reglages/langue (borné fr|en, écrit le .env
      sans toucher au reste, appliqué tout de suite, localhost seulement), msg() et la langue d'une requête.
  [5] l'installeur : la section [Code] écrit UI_LANG dans le .env du dossier de données sans remplacer un choix existant —
      compilée par ISCC et EXÉCUTÉE en silence dans un dossier jetable (FR puis EN, puis réinstallation).
  [6] l'écran : la rangée DzLangueUI dans les Réglages (paire native T134_NATIF hors de PATCHES), aucun useState de plus.
Run : & $PY tests/test_i18n_l0.py   (depuis backend/)
"""
import asyncio, json, os, pathlib, re, shutil, subprocess, sys, tempfile

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt134_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.pop("UI_LANG", None)
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "scripts"))
NODE = shutil.which("node")
SRC = ROOT / "frontend" / "shared"
DIST = ROOT / "frontend" / "dist" / "shared"
PAGES = ["frontend/dist/index.html", "frontend/atelier/index.html", "frontend/cardforge/index.html",
         "frontend/etabli/index.html", "frontend/materialforge/index.html", "frontend/spritelab/index.html",
         "frontend/studio3d/index.html", "frontend/tilelab/index.html", "frontend/vectorlab/index.html"]
B_DICO = '<script src="/shared/dz-i18n-dico.js"></script>'
B_RUN = '<script src="/shared/dz-i18n.js"></script>'
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:600]}")


print("\n[1] le runtime sous node")
run_src = SRC / "dz-i18n.js"
dico_dist = DIST / "dz-i18n-dico.js"
for nom in ("dz-i18n.js", "dz-i18n-dico.js"):
    a, b = SRC / nom, DIST / nom
    check(f"1.0 {nom} : deux copies identiques à l'octet, CRLF", a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()
          and a.read_bytes().count(b"\n") == a.read_bytes().count(b"\r\n") > 0)
if NODE and run_src.is_file() and dico_dist.is_file():
    HARNAIS = r"""
const fs = require("fs");
const [runSrc, dicoSrc, scen] = process.argv.slice(1);
function monde(ls, install) {
  const magasin = Object.assign({}, ls), entetes = [], recharge = [];
  const window = { location: { reload: () => recharge.push(1) } };
  window.localStorage = { getItem: k => (k in magasin ? magasin[k] : null), setItem: (k, v) => { magasin[k] = String(v); } };
  window.fetch = (url, init) => { entetes.push([String(url), init && init.headers ? JSON.parse(JSON.stringify(init.headers)) : null]);
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ ui_lang: install }) }); };
  const document = { documentElement: { lang: "en" }, readyState: "loading", addEventListener() {} };
  const f = new Function("window", "document", "localStorage", "MutationObserver", "Node",
    dicoSrc + "\n" + runSrc + "\n;return window;");
  const w = f(window, document, window.localStorage, undefined, { TEXT_NODE: 3, ELEMENT_NODE: 1 });
  return { w, document, magasin, entetes, recharge };
}
const R = {};
let m = monde({}, "fr");
R.defaut = [m.w.dzLang(), m.document.documentElement.lang];
m = monde({ dz_lang_install: "en" }, "en"); R.install = m.w.dzLang();
m = monde({ dz_lang_install: "en", dz_lang: "fr" }, "en"); R.bascule = m.w.dzLang();
m = monde({ dz_lang: "de" }, "fr"); R.borne = m.w.dzLang();
m = monde({ dz_lang: "en" }, "en");
R.t_en = m.w.dzT("commun.action.annuler");
R.t_vars = m.w.dzT("commun.plan.compteur", { i: 2, n: 5 });
R.t_absente = m.w.dzT("zz.absente.cle");
R.lang_en = m.document.documentElement.lang;
const I = m.w.__dzI18n;
R.surc_exact = I.traduire("Annuler");
R.surc_espaces = I.traduire("  Annuler\n");
R.surc_partiel = I.traduire("Annuler tout");
R.surc_inconnu = I.traduire("Bonjour le monde");
m.w.fetch("/api/health"); m.w.fetch("https://exemple.org/x"); m.w.fetch("/api/x", { headers: { "Accept-Language": "fr" } });
R.entetes = m.entetes;
m = monde({ dz_lang: "fr" }, "fr");
R.t_fr = m.w.dzT("commun.action.annuler");
R.surc_fr = m.w.__dzI18n.traduire("Annuler");
m.w.dzSetLang("en"); R.set = [m.magasin.dz_lang, m.recharge.length];
m.w.dzSetLang("xx"); R.set_borne = m.magasin.dz_lang;
// premier lancement d'une installation anglaise : rien en mémoire -> /api/health dit en -> mémorisé, UNE recharge
m = monde({}, "en");
setTimeout(() => { R.premier = [m.magasin.dz_lang_install, m.recharge.length];
  const m2 = monde({ dz_lang_install: "en" }, "en");
  setTimeout(() => { R.second = m2.recharge.length; process.stdout.write(JSON.stringify(R)); }, 20); }, 20);
"""
    r = subprocess.run([NODE, "-e", HARNAIS, run_src.read_text("utf-8"), dico_dist.read_text("utf-8"), ""],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        check("1.1 le runtime s'exécute sous node", False, r.stderr[-800:])
    else:
        R = json.loads(r.stdout)
        check("1.1 défaut : fr, <html lang> posé", R["defaut"] == ["fr", "fr"], R["defaut"])
        check("1.2 le choix de l'installation est suivi", R["install"] == "en", R["install"])
        check("1.3 la bascule des Réglages l'emporte sur l'installation", R["bascule"] == "fr", R["bascule"])
        check("1.4 une langue inconnue vaut fr", R["borne"] == "fr", R["borne"])
        check("1.5 dzT en anglais, variables remplacées", R["t_en"] == "Cancel" and R["t_vars"] == "Shot 2/5", [R["t_en"], R["t_vars"]])
        check("1.6 clé absente : la clé elle-même, visible", R["t_absente"] == "zz.absente.cle", R["t_absente"])
        check("1.7 <html lang> suit la langue (dictée vocale, guide)", R["lang_en"] == "en", R["lang_en"])
        check("1.8 surcouche : correspondance exacte, espaces autour gardés",
              R["surc_exact"] == "Cancel" and R["surc_espaces"] == "  Cancel\n", [R["surc_exact"], R["surc_espaces"]])
        check("1.9 surcouche : jamais une phrase traduite à moitié, inconnu intact",
              R["surc_partiel"] is None and R["surc_inconnu"] is None, [R["surc_partiel"], R["surc_inconnu"]])
        check("1.10 en français : dzT rend le français, la surcouche ne fait rien", R["t_fr"] == "Annuler" and R["surc_fr"] is None,
              [R["t_fr"], R["surc_fr"]])
        e = {u: h for u, h in R["entetes"]}
        check("1.11 Accept-Language ajouté aux seules requêtes /api/, jamais imposé par-dessus un en-tête posé",
              (e.get("/api/health") or {}).get("Accept-Language") == "en" and not (e.get("https://exemple.org/x") or {}).get("Accept-Language")
              and (e.get("/api/x") or {}).get("Accept-Language") == "fr", R["entetes"])
        check("1.12 dzSetLang mémorise et recharge ; borné", R["set"] == ["en", 1] and R["set_borne"] == "en", [R["set"], R["set_borne"]])
        check("1.13 premier lancement d'une installation anglaise : mémorisé puis UNE recharge, pas de boucle",
              R["premier"] == ["en", 1] and R["second"] == 0, [R["premier"], R["second"]])
else:
    check("1.1 le runtime existe", False, "node ou fichiers absents")

print("\n[2] le dictionnaire")
dicos = sorted((SRC / "i18n").glob("*.json")) if (SRC / "i18n").is_dir() else []
check("2.1 au moins un dictionnaire (commun)", any(d.name == "commun.json" for d in dicos), [d.name for d in dicos])
mauvais, vars_ko, toutes = [], [], {}
for d in dicos:
    for k, v in json.loads(d.read_text("utf-8")).items():
        toutes[k] = v
        if not re.fullmatch(r"[a-z0-9]+(\.[a-z0-9_]+){2,}", k) or not isinstance(v, dict) or not str(v.get("fr", "")).strip() \
                or not str(v.get("en", "")).strip():
            mauvais.append(k)
        elif sorted(re.findall(r"\{(\w+)\}", v["fr"])) != sorted(re.findall(r"\{(\w+)\}", v["en"])):
            vars_ko.append(k)
check("2.2 clés zone.objet.role, fr et en non vides", toutes and not mauvais, mauvais[:10])
check("2.3 mêmes {variables} des deux côtés", not vars_ko, vars_ko)
fr_dup = {}
for k, v in toutes.items():
    fr_dup.setdefault(v.get("fr"), set()).add(v.get("en"))
check("2.4 un même texte français a UNE seule traduction (sinon la surcouche serait ambiguë)",
      all(len(s) == 1 for s in fr_dup.values()), [f for f, s in fr_dup.items() if len(s) > 1][:5])
try:
    import i18n_assembler as IA
    rejoue = IA.assembler(SRC / "i18n")
    check("2.5 l'assemblé est à jour (assemblage rejoué = octets identiques)", dico_dist.is_file() and rejoue == (SRC / "dz-i18n-dico.js").read_bytes())
except Exception as e:
    check("2.5 l'assembleur se charge", False, repr(e))

print("\n[3] les neuf pages")
for p in PAGES:
    t = (ROOT / p).read_text(encoding="utf-8")
    i, j = t.find(B_DICO), t.find(B_RUN)
    premier = min([k for k in (t.find('<script type="module"'), t.find('<script src="js/'), t.find("<script src=\"./js/")) if k >= 0] or [len(t)])
    check(f"3 {p} : dictionnaire puis runtime, une fois, avant le bundle et les modules",
          t.count(B_DICO) == 1 and t.count(B_RUN) == 1 and 0 <= i < j < premier, (i, j, premier))

print("\n[4] le backend")
from app.config import settings                            # noqa: E402
check("4.1 UI_LANG vaut fr par défaut", getattr(settings, "UI_LANG", None) == "fr", getattr(settings, "UI_LANG", None))
try:
    from app import i18n as I18N                            # noqa: E402
    check("4.2 msg() : fr par défaut, en sur demande, variables, clé absente -> clé",
          I18N.msg("i18n.langue.inconnue", lang="fr", lang_demandee="de").startswith("Langue inconnue")
          and I18N.msg("i18n.langue.inconnue", lang="en", lang_demandee="de").startswith("Unknown language")
          and "de" in I18N.msg("i18n.langue.inconnue", lang="en", lang_demandee="de")
          and I18N.msg("zz.absente.cle", lang="en") == "zz.absente.cle")
    check("4.3 langue d'une requête : Accept-Language, sinon UI_LANG",
          I18N.langue_entete("en-US,en;q=0.9") == "en" and I18N.langue_entete("fr-FR") == "fr"
          and I18N.langue_entete("de-DE,de") is None and I18N.langue_entete("") is None)
except Exception as e:
    check("4.2 app.i18n se charge", False, repr(e))


async def _back():
    import httpx
    from app.main import app
    env = _tmp / ".env"
    env.write_text("FAL_KEY=abc\n# commentaire\nOLLAMA_URL=http://x\n", encoding="utf-8")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        h = (await c.get("/api/health")).json()
        check("4.4 /api/health dit ui_lang", h.get("ui_lang") == "fr", h.get("ui_lang"))
        g = (await c.get("/api/reglages/langue")).json()
        check("4.5 GET /api/reglages/langue : la langue et les deux choix",
              g.get("lang") == "fr" and [x.get("id") for x in g.get("langues", [])] == ["fr", "en"], g)
        r = await c.post("/api/reglages/langue", json={"lang": "de"}, headers={"Accept-Language": "en"})
        check("4.6 langue hors fr|en -> 400 dit dans la langue de la requête", r.status_code == 400 and "Unknown language" in r.text, (r.status_code, r.text))
        r = await c.post("/api/reglages/langue", json={"lang": "en"})
        lignes = env.read_text("utf-8").splitlines()
        check("4.7 POST en : écrit UI_LANG=en, garde le reste du .env intact", r.status_code == 200 and lignes ==
              ["FAL_KEY=abc", "# commentaire", "OLLAMA_URL=http://x", "UI_LANG=en"], (r.status_code, lignes))
        h = (await c.get("/api/health")).json()
        check("4.8 appliqué tout de suite (sans relance)", h.get("ui_lang") == "en" and settings.UI_LANG == "en", h.get("ui_lang"))
        r = await c.post("/api/reglages/langue", json={"lang": "fr"})
        check("4.9 réécrire remplace la ligne, n'en ajoute pas", env.read_text("utf-8").splitlines().count("UI_LANG=fr") == 1
              and "UI_LANG=en" not in env.read_text("utf-8"), env.read_text("utf-8"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("192.168.1.20", 5000)), base_url="http://t") as c:
        r = await c.post("/api/reglages/langue", json={"lang": "en"})
        check("4.10 hors de la machine : refusé (garde d'appairage 401 ou garde locale 403)", r.status_code in (401, 403) and settings.UI_LANG == "fr", r.status_code)

asyncio.run(_back())

print("\n[5] l'installeur")
iss = (ROOT / "installer" / "deepotus.iss").read_text("utf-8")
check("5.1 [Code] : CurStepChanged(ssPostInstall) écrit UI_LANG depuis ActiveLanguage",
      "[Code]" in iss and "ssPostInstall" in iss and "ActiveLanguage" in iss and "UI_LANG=" in iss)
ISCC = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"
_i = iss.find("\n[Code]")
code = iss[_i + 1:] if _i >= 0 else ""
if ISCC.is_file() and code:
    w = _tmp / "iss"
    w.mkdir()
    (w / "vide.txt").write_text("x", encoding="utf-8")
    donnees = _tmp / "donnees"
    mini = "\n".join([
        f'#define DataDir "{donnees}"',
        "[Setup]", "AppId={{0B1D4C2A-7E1F-4A11-9B5D-13401340T134}", "AppName=dzt134", "AppVersion=1",
        f"DefaultDirName={w / 'app'}", "DisableDirPage=yes", "PrivilegesRequired=lowest", "Uninstallable=no",
        "CreateUninstallRegKey=no", f"OutputDir={w}", "OutputBaseFilename=mini", "DisableProgramGroupPage=yes",
        "[Languages]", 'Name: "fr"; MessagesFile: "compiler:Languages\\French.isl"', 'Name: "en"; MessagesFile: "compiler:Default.isl"',
        "[Files]", f'Source: "{w / "vide.txt"}"; DestDir: "{{app}}"',
        code])
    (w / "mini.iss").write_text(mini, encoding="utf-8-sig")
    r = subprocess.run([str(ISCC), "/Q", str(w / "mini.iss")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("5.2 la section [Code] compile (ISCC)", r.returncode == 0 and (w / "mini.exe").is_file(), (r.stdout + r.stderr)[-800:])
    if r.returncode == 0:
        def poser(lang):
            subprocess.run([str(w / "mini.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/LANG={lang}"], timeout=120)
            p = donnees / ".env"
            return p.read_text("utf-8") if p.is_file() else None
        t1 = poser("en")
        check("5.3 installation en anglais -> UI_LANG=en dans le .env du dossier de données (créé)", t1 is not None
              and [l for l in t1.splitlines() if l.startswith("UI_LANG=")] == ["UI_LANG=en"], t1)
        t2 = poser("fr")
        check("5.4 réinstallation en français : le choix existant n'est PAS remplacé", t2 is not None
              and [l for l in t2.splitlines() if l.startswith("UI_LANG=")] == ["UI_LANG=en"], t2)
        (donnees / ".env").write_bytes(b"FAL_KEY=abc")              # sans fin de ligne
        t3 = poser("fr")
        check("5.5 .env existant sans UI_LANG : ajouté sur sa propre ligne, le reste intact", t3 is not None
              and t3.splitlines() == ["FAL_KEY=abc", "UI_LANG=fr"], t3)
else:
    check("5.2 ISCC disponible et [Code] présent", False, (ISCC, bool(code)))

print("\n[6] l'écran des Réglages")
BUN = (ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
COUCHE = (ROOT / "frontend" / "patches" / "montage.js").read_text("utf-8")
try:
    import patch_bundle_montage as PM
    paires = PM.T134_NATIF
except Exception as e:
    paires = None
check("6.1 paire consignée hors de PATCHES, une fois au bundle", paires is not None and len(paires) == 1
      and all(BUN.count(r) == 1 for _n, _a, r in paires) and not any(n.startswith("T134") for n, _a, _r in PM.PATCHES))
check("6.2 la rangée suit les modèles par défaut", BUN.count('r.jsx(DzModelDefaults,{},"modeldefaults"),r.jsx(DzLangueUI,{},"langueui"),') == 1)
check("6.3 DzLangueUI dans la couche montage, passe par dzSetLang et /reglages/langue",
      COUCHE.count("function DzLangueUI(") == 1 and "dzSetLang(" in COUCHE and "/reglages/langue" in COUCHE)
check("6.3b la couche est rafraîchie dans le bundle (DzLangueUI y est défini, une fois)",
      BUN.count("function DzLangueUI(") == 1 and BUN.count('dzT("reglages.langue.titre")') == 1)
# preuve 8799 : en anglais, la surcouche traduisait l'option « Français » du sélecteur en « French » — les noms de
# langue restent dans leur propre langue : le sélecteur est soustrait à la surcouche
check("6.3c le sélecteur de langue est marqué data-dz-brut (Français reste Français)",
      BUN.count('r.jsx("div",{"data-dz-brut":"1",children:r.jsx(re,{value:l,onChange:choisir,') == 1)
check("6.4 aucun x.useState de plus (731)", BUN.count("x.useState(") == 731, BUN.count("x.useState("))
r = subprocess.run([NODE, "--check", str(ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js")], capture_output=True, text=True)
check("6.5 bundle node --check", r.returncode == 0, r.stderr[-300:])

shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
