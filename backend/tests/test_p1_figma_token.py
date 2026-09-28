# -*- coding: utf-8 -*-
"""P1 #2 (28/09/2026) — FIGMA_TOKEN REFUSE A L'ENREGISTREMENT.

Defaut mesure : l'import Figma (`POST /images/import-figma`) lit
`settings.FIGMA_TOKEN` et renvoie 409 sans lui, mais la cle n'etait pas dans
`_ALLOWED_ENV_KEYS` : `POST /settings/keys` repondait 400 « Key not allowed »,
et l'ecran Reglages → API keys (catalogue `Fu` du bundle) ne proposait meme
pas le champ. Seule voie : editer le .env a la main.

Correctif : la cle entre dans la liste blanche, `/health` expose
`figma_configured`, le 409 renvoie aux Reglages, et le groupe P1 du maillon
montage (section P1fg1) ajoute la rangee « Figma » au catalogue.

INVARIANT BANCE (la classe du defaut, pas seulement l'occurrence) : toute cle
du catalogue des Reglages est dans la liste blanche du serveur, et toute cle
`health` du catalogue existe dans la reponse de /health. Temoins : l'ancienne
liste blanche (lue par `git show 00f621e:`) REFUSE FIGMA_TOKEN, et le nouveau
catalogue confronte a l'ancienne liste la VIOLE — l'invariant sait donc
rougir. Faute n6 : details par _d().
Run : & $PY tests/test_p1_figma_token.py   (depuis backend/)
"""
import ast, asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp1fg_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ.setdefault("FAL_KEY", "test-key")
os.environ.pop("FIGMA_TOKEN", None)
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "scripts"))
from loguru import logger                                  # noqa: E402
logger.remove()
import patch_bundle_montage as P                           # noqa: E402

BASE = "00f621e"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:400]
    except Exception as e:                                   # pragma: no cover
        return f"(detail illisible : {e})"


def _allowlist(src):
    """Le litteral `_ALLOWED_ENV_KEYS = {...}` d'une source routes.py."""
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_ALLOWED_ENV_KEYS" for t in n.targets):
            return set(ast.literal_eval(n.value))
    return None


BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
s = BUNDLE.read_bytes().decode("utf-8")
bak = BAK.read_bytes().decode("utf-8") if BAK.is_file() else ""
NODE = shutil.which("node")
_g = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], cwd=ROOT,
                    capture_output=True, text=True, encoding="utf-8")
OLD = _allowlist(_g.stdout) if _g.returncode == 0 else None

print("\n[0] preconditions")
check("0.1 .bak_montage present (temoin)", bool(bak), _d(str(BAK)))
check("0.2 node present", bool(NODE), _d(NODE))
check("0.3 ancienne liste blanche lue a la base (temoin)", bool(OLD) and "FAL_KEY" in OLD, _d(_g.stderr[-200:]))

print("\n[1] serveur : la liste blanche et les routes")
from app.api import routes as R                            # noqa: E402
from app.config import settings                            # noqa: E402
from app.main import app                                   # noqa: E402
check("1.1 temoin : l'ancienne liste blanche REFUSAIT FIGMA_TOKEN", OLD is not None and "FIGMA_TOKEN" not in OLD, "")
check("1.2 FIGMA_TOKEN dans _ALLOWED_ENV_KEYS", "FIGMA_TOKEN" in R._ALLOWED_ENV_KEYS, "")
check("1.3 rien d'autre n'entre ni ne sort de la liste blanche",
      OLD is not None and R._ALLOWED_ENV_KEYS - OLD == {"FIGMA_TOKEN"} and not (OLD - R._ALLOWED_ENV_KEYS),
      _d(sorted((R._ALLOWED_ENV_KEYS ^ OLD) if OLD else [])))


async def _http():
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1/api") as c:
        refus = await c.post("settings/keys", json={"name": "PAS_UNE_CLE", "value": "x"})
        pose = await c.post("settings/keys", json={"name": "FIGMA_TOKEN", "value": "figd_banc_1234567890"})
        liste = await c.get("settings/keys")
        settings.FIGMA_TOKEN = ""
        sante0 = await c.get("health")
        imp = await c.post("images/import-figma", json={"url": "https://www.figma.com/design/abc/x?node-id=1-2"})
        settings.FIGMA_TOKEN = "figd_banc_1234567890"
        sante1 = await c.get("health")
        settings.FIGMA_TOKEN = ""
        return refus, pose, liste, sante0, imp, sante1

refus, pose, liste, sante0, imp, sante1 = asyncio.run(_http())
envtxt = (pathlib.Path(TMP) / ".env").read_text(encoding="utf-8") if (pathlib.Path(TMP) / ".env").is_file() else ""
check("1.4 temoin : une cle hors liste reste refusee 400", refus.status_code == 400, _d(refus.status_code, refus.text[:120]))
check("1.5 POST /settings/keys FIGMA_TOKEN -> 200 et ecrit dans le .env des donnees",
      pose.status_code == 200 and "FIGMA_TOKEN=figd_banc_1234567890" in envtxt.splitlines(),
      _d(pose.status_code, pose.text[:160], envtxt[-120:]))
_k = {e["key"]: e for e in (liste.json().get("keys", []) if liste.status_code == 200 else [])}
check("1.6 GET /settings/keys : FIGMA_TOKEN pose, apercu MASQUE (jamais la valeur en clair)",
      _k.get("FIGMA_TOKEN", {}).get("set") is True and "figd_banc_1234567890" not in liste.text
      and _k["FIGMA_TOKEN"]["preview"].startswith("figd") and "•" in _k["FIGMA_TOKEN"]["preview"],
      _d(_k.get("FIGMA_TOKEN")))
check("1.7 /health : figma_configured suit le jeton (False puis True)",
      sante0.json().get("figma_configured") is False and sante1.json().get("figma_configured") is True,
      _d(sante0.json().get("figma_configured"), sante1.json().get("figma_configured")))
check("1.8 import sans jeton : 409 qui renvoie aux Reglages (et nomme toujours FIGMA_TOKEN)",
      imp.status_code == 409 and "FIGMA_TOKEN" in imp.text and "Réglages" in imp.text,
      _d(imp.status_code, imp.text[:240]))

print("\n[2] bundle : la rangee Figma du catalogue des Reglages (groupe P1)")
P1 = list(getattr(P, "P1", []))
check("2.1 groupe P1 en QUEUE de PATCHES, apres R8", bool(P1) and P.PATCHES[-len(P1):] == P1
      and P.PATCHES[-len(P1) - len(P.R8):-len(P1)] == P.R8, _d([t[0] for t in P.PATCHES[-3:]]))
_A = 'health:"has_meshy"}];function bm(){'
check("2.2 temoin : l'ancre du catalogue x1 dans le .bak, sans FIGMA_TOKEN",
      bak.count(_A) == 1 and '"FIGMA_TOKEN"' not in bak, _d(bak.count(_A)))
check("2.3 bundle : la rangee FIGMA_TOKEN x1, l'ancre consommee", s.count('{k:"FIGMA_TOKEN",') == 1 and s.count(_A) == 0,
      _d(s.count('{k:"FIGMA_TOKEN",'), s.count(_A)))


def _catalogue(txt):
    """Le tableau `const Fu=[...]` evalue par node -> liste de {k, health}."""
    i = txt.find('const Fu=[{k:"FAL_KEY"')
    j = txt.find('];function bm(){', i)
    if i < 0 or j < 0 or not NODE:
        return None
    lit = txt[i + len("const Fu="):j + 1]
    r = subprocess.run([NODE, "-e", "process.stdout.write(JSON.stringify(" + lit + "))"],
                       capture_output=True, text=True, encoding="utf-8")
    return json.loads(r.stdout) if r.returncode == 0 else None


NEW_CAT, OLD_CAT = _catalogue(s), _catalogue(bak)
_keys = lambda cat: [e["k"] for e in cat or []]
check("2.4 le catalogue s'evalue dans les deux etats", bool(NEW_CAT) and bool(OLD_CAT), "")
check("2.5 rangee Figma en DERNIER, le reste du catalogue intact",
      _keys(NEW_CAT) == _keys(OLD_CAT) + ["FIGMA_TOKEN"], _d(_keys(NEW_CAT)[-3:]))
check("2.6 INVARIANT : toute cle du catalogue est dans la liste blanche du serveur",
      bool(NEW_CAT) and set(_keys(NEW_CAT)) <= R._ALLOWED_ENV_KEYS, _d(sorted(set(_keys(NEW_CAT)) - R._ALLOWED_ENV_KEYS)))
check("2.7 temoin : le nouveau catalogue confronte a l'ANCIENNE liste blanche viole l'invariant",
      OLD is not None and bool(NEW_CAT) and set(_keys(NEW_CAT)) - OLD == {"FIGMA_TOKEN"}, "")
check("2.8 INVARIANT : toute cle health du catalogue existe dans /health",
      bool(NEW_CAT) and all(e.get("health") in sante1.json() for e in NEW_CAT),
      _d([e.get("health") for e in NEW_CAT or [] if e.get("health") not in sante1.json()]))
_fg = next((e for e in NEW_CAT or [] if e["k"] == "FIGMA_TOKEN"), {})
check("2.9 la rangee dit ou creer le jeton (figma.com → Settings → Security)",
      "Settings → Security" in (_fg.get("why") or "") and "Figma" in (_fg.get("label") or ""), _d(_fg))
_nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("2.10 le bundle ENTIER passe node --check", _nc is not None and _nc.returncode == 0,
      _d(_nc.stderr[-300:] if _nc else "node absent"))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
