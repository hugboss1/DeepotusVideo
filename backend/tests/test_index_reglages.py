# -*- coding: utf-8 -*-
"""Recherche dans les réglages (plan Settings T19 — tâche #22, 29/09/2026).
Banc-miroir : les sections, leurs libellés et la place de chaque clé sont LUS dans le bundle livré (la barre latérale
de `xm`, la liste `Fu` et le panneau Ollama de l'écran des clés, les champs de « Connected accounts »), jamais recopiés
ici — un index qui envoie une clé vers une section qui ne l'affiche pas, ou qui oublie une section, rougit.
La fonction de recherche est la VRAIE (`dzChercheReglage`, extraite du bundle et exécutée par node sur l'index servi).
Témoin : la base 1e3d9f0 n'a ni route ni champ.
Run : & $PY tests/test_index_reglages.py   (depuis backend/)"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzidx_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
_B = racine / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
s = _B.read_text(encoding="utf-8")
def base(p):
    return subprocess.run(["git", "show", "1e3d9f0:" + p], cwd=racine, capture_output=True).stdout.decode("utf-8")

print("\n[0] témoin : la base 1e3d9f0")
vr, vb = base("backend/app/api/settings_routes.py"), base("frontend/dist/assets/index-BEOJX8L5.js")
check("0.1 TÉMOIN : pas de route /index", vr and '@router.get("/index")' not in vr)
check("0.2 TÉMOIN : pas de champ de recherche", vb and "function DzSettingsSearch(" not in vb)

# ── ce que l'écran AFFICHE, lu dans le bundle ──
m = re.search(r'children:"Settings"\}\),(?:r\.jsx\(DzSettingsSearch,\{aller:a\}\),)?\[(\{k:"diag".*?)\]\.map\(u=>', s)
barre = dict(re.findall(r'\{k:"([a-z]+)",l:"([^"]+)"\}', m.group(1))) if m else {}
fu = re.search(r'Fu=\[(.*?)\];function bm\(', s)
cles_keys = set(re.findall(r'\{k:"([A-Z_]+)",label:', fu.group(1))) if fu else set()
_iw = s.find("function wm({serverKeys:e,onSaved:t})")
wm = s[_iw:_iw + 6000] if _iw >= 0 else ""
cles_ollama = set(re.findall(r"e==null\?void 0:e\.([A-Z_]+)", wm))
tm = s[s.find("function Tm("):s.find("function Tm(") + 9000]
cles_comptes = set(re.findall(r'k:"([A-Z][A-Z_]+)"', tm))
print(f"\n  (lu dans le bundle : {len(barre)} sections, {len(cles_keys)} + {sorted(cles_ollama)} clés à l'écran API keys, "
      f"{len(cles_comptes)} dans Connected accounts)")

from app.api.routes import _ALLOWED_ENV_KEYS                       # noqa: E402
from app.config import ENV_FILE                                     # noqa: E402
from app.services import guides_fournisseurs as G                  # noqa: E402
SECRET = "sk-DZSECRET-ne-doit-jamais-sortir-4242"
ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
ENV_FILE.write_text(f"FAL_KEY={SECRET}\nTELEGRAM_BOT_TOKEN={SECRET}\n", encoding="utf-8")

from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    rep = c.get("/api/reglages/index")
    brut = rep.text
    try:
        e = rep.json().get("entrees", [])
    except ValueError:                                              # la base : le fourre-tout SPA rend du HTML
        e = []
with TestClient(app, client=("192.168.1.20", 50000)) as c2:
    code_distant = c2.get("/api/reglages/index").status_code

print("\n[1] les sections")
check("1.0 le miroir a bien lu le bundle (13 sections, 9 clés, Ollama, 16 comptes dont TikTok depuis #31)", len(barre) == 13 and len(cles_keys) == 9
      and cles_ollama == {"OLLAMA_URL", "OLLAMA_MODEL"} and len(cles_comptes) == 16, f"{barre} {cles_keys} {cles_ollama} {cles_comptes}")
vues = {x["section"] for x in e}
check("1.1 CHAQUE section de la barre a au moins une entrée, et aucune entrée ne vise une section qui n'existe pas",
      vues == set(barre), f"manquent {set(barre) - vues}, en trop {vues - set(barre)}")
check("1.2 chaque entrée porte le libellé de sa rubrique tel que la barre l'affiche",
      e and all(x.get("rubrique") == barre.get(x["section"]) for x in e),
      str([x for x in e if x.get("rubrique") != barre.get(x["section"])][:2]))
check("1.3 chaque entrée a un libellé et des mots (chaînes non vides)",
      e and all(isinstance(x.get("libelle"), str) and x["libelle"] and isinstance(x.get("mots"), str) and x["mots"] for x in e))

print("\n[2] les clés : là où l'écran les montre, et nulle part ailleurs")
par_cle = {}
for x in e:
    if x.get("cle"):
        par_cle.setdefault(x["cle"], []).append(x["section"])
attendu = {k: ["keys"] for k in cles_keys | cles_ollama}
attendu.update({k: ["accounts"] for k in cles_comptes})
check("2.1 chaque clé affichée a UNE entrée, dans la section qui l'affiche", par_cle == attendu,
      f"écart : {[(k, par_cle.get(k), attendu.get(k)) for k in set(par_cle) | set(attendu) if par_cle.get(k) != attendu.get(k)]}")
cachees = _ALLOWED_ENV_KEYS - set(attendu)
check("2.2 une clé autorisée mais affichée NULLE PART n'est pas indexée (la recherche mènerait dans le vide)",
      cachees and not (cachees & set(par_cle)), f"cachées {sorted(cachees)}")
check("2.3 aucune clé hors de la liste autorisée", set(par_cle) <= _ALLOWED_ENV_KEYS)
fal = [x for x in e if x.get("cle") == "FAL_KEY"]
gf = G.guide("FAL_KEY")
check("2.4 les mots d'une clé viennent de SON guide fournisseur (nom + début du texte), pas d'une liste doublée",
      len(fal) == 1 and gf["nom"].lower() in fal[0]["mots"].lower() and "dashboard" in fal[0]["mots"].lower()
      and fal[0]["libelle"] == gf["nom"], json.dumps(fal, ensure_ascii=False)[:300])
tg = [x for x in e if x.get("cle") == "TELEGRAM_BOT_TOKEN"]
check("2.5 une clé sans guide garde un libellé lisible (son nom) et ses mots", len(tg) == 1 and tg[0]["libelle"]
      and "telegram" in tg[0]["mots"].lower(), json.dumps(tg, ensure_ascii=False))

print("\n[3] rien de secret")
check("3.1 la valeur d'une clé posée n'apparaît NULLE PART dans la réponse", rep.status_code == 200 and SECRET not in brut
      and SECRET[:8] not in brut and "•" not in brut)
check("3.2 ni valeur ni aperçu : les seuls champs sont section, rubrique, libelle, cle, mots",
      e and all(set(x) == {"section", "rubrique", "libelle", "cle", "mots"} for x in e), str({tuple(sorted(x)) for x in e}))
check("3.3 hors boucle locale : refusé", code_distant == 403, str(code_distant))

print("\n[4] la VRAIE recherche du bundle, sur l'index servi")
i0 = s.find("function dzChercheReglage(")
i1 = s.find("function DzSettingsSearch(")
fn = s[i0:i1] if 0 <= i0 < i1 else ""
_n = shutil.which("node")
def cherche(q):
    if not (fn and _n):
        return None
    js = fn + ";const ix=" + json.dumps(e) + ";process.stdout.write(JSON.stringify(dzChercheReglage(ix," + json.dumps(q) + ")))"
    p = subprocess.run([_n, "-e", js], capture_output=True, text=True, encoding="utf-8")
    return json.loads(p.stdout) if p.returncode == 0 and p.stdout else None
r1 = cherche("plafond")
check("4.1 « plafond » : le premier résultat est « Plafonds de dépense », section pricing",
      r1 and r1[0]["section"] == "pricing" and r1[0]["libelle"].startswith("Plafonds"), str(r1)[:300])
r2 = cherche("meshy")
check("4.2 « meshy » : la clé Meshy d'abord, qui ouvre API keys", r2 and r2[0].get("cle") == "MESHY_API_KEY" and r2[0]["section"] == "keys", str(r2)[:300])
r3 = cherche("zzz")
check("4.3 « zzz » : rien", r3 == [], str(r3))
r4 = cherche("MOT DE PASSE maitre")
check("4.4 sans accents, en capitales, plusieurs mots : « MOT DE PASSE maitre » trouve le coffre (tous les mots requis)",
      r4 and r4[0]["section"] == "coffre", str(r4)[:300])
r5 = cherche("clé telegram")
check("4.5 « clé telegram » : les accents de la requête ne gênent pas, la clé Telegram ouvre Connected accounts",
      r5 and r5[0].get("cle", "").startswith("TELEGRAM") and r5[0]["section"] == "accounts", str(r5)[:300])
r6 = cherche("a")
check("4.6 huit résultats au plus", r6 is not None and 0 < len(r6) <= 8, str(len(r6 or [])))
r7 = cherche("   ")
check("4.7 requête vide : rien (pas toute la liste)", r7 == [], str(r7))
r8 = cherche("pricing")
check("4.8 le nom affiché de la rubrique (anglais) est cherchable : « pricing »", r8 and all(x["section"] == "pricing" for x in r8), str(r8)[:300])
r9 = cherche("plafond zzz")
check("4.9 TOUS les mots sont requis : « plafond zzz » ne rend rien", r9 == [], str(r9)[:300])
r10 = cherche("clé")
_nz = lambda v: __import__("unicodedata").normalize("NFD", v).encode("ascii", "ignore").decode().lower()
check("4.10 le rang : un libellé qui porte le mot passe avant une entrée qui ne l'a que dans ses mots (« clé »)",
      r10 and "cle" in _nz(r10[0]["libelle"]) and any("cle" not in _nz(x["libelle"]) for x in e[:1]), str(r10)[:300])

print("\n[5] l'écran (bundle livré)")
dz = s[i1:s.find("function xm(")]
check("5.1 DzSettingsSearch x1, monté UNE fois dans la barre, avec le setter de section de xm",
      s.count("function DzSettingsSearch(") == 1 and s.count("r.jsx(DzSettingsSearch,{aller:a})") == 1
      and s.count('children:"Settings"}),r.jsx(DzSettingsSearch,{aller:a}),[{k:"diag"') == 1)
check("5.2 il lit /api/reglages/index une fois, et cherche avec dzChercheReglage", dz.count("fetch(") == 1
      and "fetch('/api/reglages/index')" in dz and "dzChercheReglage(ix,q)" in dz)
check("5.3 un clic OUVRE la section et vide le champ", "onClick:()=>ouvrir(e)" in dz and "aller(e.section);setQ('')" in dz)
check("5.4 clavier : Entrée ouvre le premier résultat, Échap vide le champ",
      "ev.key==='Enter'&&res.length" in dz and "ouvrir(res[0])" in dz and "ev.key==='Escape'" in dz)
check("5.5 rien trouvé : c'est dit", "'Aucun réglage ne correspond.'" in dz)
check("5.6 chaque résultat dit OÙ il mène (la rubrique affichée)", "e.rubrique" in dz)
_nc = subprocess.run([_n, "--check", str(_B)], capture_output=True, text=True) if _n else None
check("5.7 node --check du bundle entier", _nc is not None and _nc.returncode == 0, (_nc.stderr[-200:] if _nc else ""))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
