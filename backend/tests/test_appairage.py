# -*- coding: utf-8 -*-
"""Plan mobile T2 (tache #56 du suivi, P1, 01/10/2026) — appairage d'un appareil : table `devices`, secret a usage
unique valable 5 minutes, jeton dont SEUL le sha256 est stocke, cinq appareils au plus, revocation immediate.
Banc-miroir : il lit la BASE (PRAGMA, lignes) et pas le code qui pretend l'ecrire. Data-dir isole (aucune cle reelle).
Temoin positif : la base (eef08cd7) n'a ni la table ni le service.
Run (depuis backend/) : & $PY tests/test_appairage.py"""
import asyncio, hashlib, os, pathlib, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzappair_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "eef08cd7"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/storage.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/appairage.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni la table devices ni le service d'appairage",
      r0.returncode == 0 and b'"devices"' not in r0.stdout and r1.returncode != 0)

from sqlalchemy import text                                         # noqa: E402
from app.services.storage import _engine, init_db                   # noqa: E402
from app.services import appairage as AP                            # noqa: E402

BOUCLE = asyncio.new_event_loop()                                   # une seule boucle (lecon #30)
def run(co):
    return BOUCLE.run_until_complete(co)


run(init_db())


async def _sql(q, **k):
    async with _engine.begin() as conn:
        r = await conn.execute(text(q), k)
        return r.fetchall()


print("\n[B] la table, lue dans la BASE")
cols = {row[1] for row in run(_sql("PRAGMA table_info(devices)"))}
check("B1 la table devices existe avec ses six colonnes", {"id", "nom", "jeton_sha256", "cree", "revoque", "vu_le"} <= cols, str(cols))

print("\n[S] le secret")
s = AP.creer_secret()
check("S1 32 caracteres hexadecimaux, valable 5 minutes", len(s.secret) == 32 and all(c in "0123456789abcdef" for c in s.secret)
      and 299 <= (s.expire_a - s.cree_a) <= 301, str(s))
jeton, app1 = run(AP.reclamer(s.secret, "  iPhone de Oli  "))
check("S2 reclamer : jeton de 64 hex, fiche nommee (nom rogne)", len(jeton) == 64 and all(c in "0123456789abcdef" for c in jeton)
      and app1["nom"] == "iPhone de Oli" and app1["id"], str(app1))
try:
    run(AP.reclamer(s.secret, "second essai")); e = None
except AP.SecretRefuse as x:
    e = str(x)
check("S3 USAGE UNIQUE : la seconde reclamation est refusee, en le disant", e is not None and "consomm" in e, str(e))
s2 = AP.creer_secret()
AP._SECRETS[s2.secret]["expire_a"] -= 400
try:
    run(AP.reclamer(s2.secret, "trop tard")); e = None
except AP.SecretRefuse as x:
    e = str(x)
check("S4 secret expire : refuse en le disant, et oublie", e is not None and "expir" in e and s2.secret not in AP._SECRETS, str(e))
try:
    run(AP.reclamer("0" * 32, "inconnu")); e = None
except AP.SecretRefuse as x:
    e = str(x)
check("S5 secret inconnu : refuse", e is not None and "inconnu" in e, str(e))
n0 = len(AP._SECRETS)
for _ in range(3):
    AP.creer_secret()
for k in list(AP._SECRETS):
    AP._SECRETS[k]["expire_a"] = time.time() - 1
AP.creer_secret()
check("S6 les secrets expires sont purges a la creation suivante (pas d'accumulation)", len(AP._SECRETS) == 1, str(len(AP._SECRETS)))

print("\n[J] le jeton")
ligne = run(_sql("SELECT jeton_sha256, nom FROM devices WHERE id = :i", i=app1["id"]))
check("J1 la LIGNE porte le sha256, JAMAIS le jeton en clair", ligne and ligne[0][0] == hashlib.sha256(jeton.encode()).hexdigest()
      and ligne[0][0] != jeton, str(ligne))
tout = " ".join(str(c) for r in run(_sql("SELECT * FROM devices")) for c in r)
check("J2 le jeton en clair n'apparait nulle part dans la table", jeton not in tout)
check("J3 jeton valide ; jeton faux, vide ou mal forme : refuses",
      run(AP.jeton_valide(jeton)) is True and run(AP.jeton_valide("f" * 64)) is False and run(AP.jeton_valide("")) is False
      and run(AP.jeton_valide(jeton[:63])) is False and run(AP.jeton_valide(None)) is False)

print("\n[R] revocation et quota")
check("R1 revoquer : immediat pour la garde (cache invalide, pas de TTL a attendre)",
      run(AP.revoquer(app1["id"])) is True and run(AP.jeton_valide(jeton)) is False)
check("R2 revoquer deux fois, ou un inconnu : False", run(AP.revoquer(app1["id"])) is False and run(AP.revoquer("nope")) is False)
lst = run(AP.lister())
check("R3 lister : l'appareil revoque reste visible, date de revocation posee, aucun jeton ni empreinte rendus",
      len(lst) == 1 and lst[0]["revoque"] and "jeton_sha256" not in lst[0] and "jeton" not in lst[0], str(lst))
run(AP.revoquer_tout())
jetons = [run(AP.reclamer(AP.creer_secret().secret, f"appareil {i}"))[0] for i in range(5)]
try:
    run(AP.reclamer(AP.creer_secret().secret, "le sixieme")); e = None
except AP.SecretRefuse as x:
    e = str(x)
check("R4 cinq appareils actifs au plus : le sixieme est refuse en le disant", e is not None and "cinq" in e, str(e))
check("R5 revoquer_tout : rend le nombre, plus aucun jeton ne passe", run(AP.revoquer_tout()) == 5
      and not any(run(AP.jeton_valide(j)) for j in jetons))
j6, _a6 = run(AP.reclamer(AP.creer_secret().secret, "apres revocation"))
check("R6 apres revocation, une place se libere (les revoques ne comptent pas)", run(AP.jeton_valide(j6)) is True)

print("\n[C] consoles a rappeler apres une revocation")
noms = {c["cle"] for c in AP.CONSOLES}
manque = {"FAL_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY", "ELEVENLABS_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
          "GEMINI_API_KEY", "FIGMA_TOKEN", "X_API_KEY", "TELEGRAM_BOT_TOKEN", "YOUTUBE_CLIENT_SECRET", "IG_ACCESS_TOKEN",
          "TIKTOK_CLIENT_SECRET"} - noms
check("C1 chaque fournisseur qui depense ou publie a sa console (Scheduler compris)", not manque, str(manque))
src = (_ICI.parent / "app" / "api" / "routes.py").read_text("utf-8")
i_k = src.find("_ALLOWED_ENV_KEYS = {"); bloc = src[i_k:src.find("}", i_k)]
check("C2 chaque cle citee existe dans la liste blanche des Reglages", all(f'"{k}"' in bloc for k in noms), str([k for k in noms if f'"{k}"' not in bloc]))
check("C3 chaque console est en https", all(c["url"].startswith("https://") for c in AP.CONSOLES))

print(f"\n{ok} ok, {fail} fail")
BOUCLE.run_until_complete(_engine.dispose())
sys.exit(1 if fail else 0)
