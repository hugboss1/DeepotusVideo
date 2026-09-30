# -*- coding: utf-8 -*-
"""Arrêt propre et isolation des bancs (30/09/2026).
Constat : à la fermeture de `TestClient(app)`, le préchargement HeyGen du démarrage restait en vol (tâche protégée par
`asyncio.shield`, que l'annulation de `warm_task` ne touche pas) et le processus ne se terminait jamais ; et il était
lancé parce que les bancs voyaient une VRAIE clé HeyGen — héritée d'une variable d'environnement Windows (portée
Utilisateur), qu'un data-dir temporaire sans .env laissait passer.
Banc-miroir : chaque scénario tourne dans un PROCESSUS ENFANT à l'environnement construit ici (clés factices posées
comme le fait Windows, LOCALAPPDATA temporaire) ; le réseau HeyGen est remplacé par des faux qui comptent les appels.
[A] instance isolée (DEEPOTUS_DATA_DIR) : les secrets hérités sont ignorés, ceux du .env du data-dir comptent ;
    instance par défaut (sans DEEPOTUS_DATA_DIR) : inchangée, l'héritage compte.
[B] session courte : le préchargement n'a pas démarré, le processus se termine vite même si le faux bloque un thread.
[C] session longue : le préchargement a démarré ; à l'arrêt, la récupération en vol est ANNULÉE et oubliée.
Run : & $PY tests/test_arret_isole.py   (depuis backend/)"""
import json, os, pathlib, subprocess, sys, tempfile, textwrap, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parents[1]

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


SECRETS_HERITES = {"HEYGEN_API_KEY": "herite-heygen", "ANTHROPIC_API_KEY": "herite-anthropic",
                   "GEMINI_API_KEY": "herite-gemini", "FAL_KEY": "herite-fal"}


def enfant(code, *, data_dir=True, env_file="", extra=None, timeout=90):
    """Lance `code` dans un python neuf ; rend (json de la dernière ligne, durée s, sortie)."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzarret_"))
    env = {k: v for k, v in os.environ.items() if k not in ("DEEPOTUS_DATA_DIR", "DATABASE_URL")}
    env.update(SECRETS_HERITES)
    env["LOCALAPPDATA"] = str(tmp / "local")          # jamais le vrai %LOCALAPPDATA%
    (tmp / "local").mkdir()
    racine = tmp / "data" if data_dir else tmp / "local" / "DeepotusVideoGenData"
    racine.mkdir(parents=True)
    if data_dir:
        env["DEEPOTUS_DATA_DIR"] = str(racine)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{(racine / 't.db').as_posix()}"
    if env_file:
        (racine / ".env").write_text(env_file, encoding="utf-8")
    env.update(extra or {})
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.monotonic()
    try:
        p = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=BACKEND, env=env,
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, time.monotonic() - t0, "TIMEOUT"
    dt = time.monotonic() - t0
    out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    lignes = [l for l in p.stdout.decode("utf-8", "replace").splitlines() if l.startswith("{")]
    return (json.loads(lignes[-1]) if lignes else None), dt, out


LIRE_CLES = """
    import json, sys
    sys.path.insert(0, ".")
    from app.config import settings
    print(json.dumps({k: getattr(settings, k) for k in %r}))
""" % sorted(SECRETS_HERITES)

print("\n[A] d'où viennent les clés")
r, _, out = enfant(LIRE_CLES)
check("A.1 instance isolée, data-dir sans .env : AUCUN secret hérité n'est vu",
      r is not None and all(v == "" for v in r.values()), f"{r} {out[-400:]}")
r, _, out = enfant(LIRE_CLES, env_file="HEYGEN_API_KEY=du-data-dir\n")
check("A.2 instance isolée : la clé du .env du data-dir compte, les autres héritées restent muettes",
      r is not None and r["HEYGEN_API_KEY"] == "du-data-dir" and r["FAL_KEY"] == "" and r["GEMINI_API_KEY"] == "",
      f"{r} {out[-400:]}")
r, _, out = enfant(LIRE_CLES, data_dir=False)
check("A.3 instance par défaut (sans DEEPOTUS_DATA_DIR) : l'héritage compte comme avant",
      r is not None and r == SECRETS_HERITES, f"{r} {out[-400:]}")
r, _, out = enfant(LIRE_CLES + """
    import os
    print(json.dumps({"env": os.environ.get("HEYGEN_API_KEY"), "db": os.environ.get("DATABASE_URL", "")[:9]}))
""")
check("A.4 instance isolée : le secret hérité est retiré de os.environ (sous-processus compris), le reste est gardé",
      r is not None and r["env"] is None and r["db"] == "sqlite+ai", f"{r} {out[-400:]}")
r, _, out = enfant(LIRE_CLES.replace("print(json.dumps({k:", "import os\n    print(json.dumps({'env': os.environ.get('HEYGEN_API_KEY'), **{k:"
                                     ).replace("for k in %r}))" % sorted(SECRETS_HERITES), "for k in %r}}))" % sorted(SECRETS_HERITES)),
                   env_file="HEYGEN_API_KEY=herite-heygen\n")
check("A.6 instance isolée : une clé que le .env du data-dir pose LUI-MÊME reste, même identique à l'héritée "
      "(dans settings ET dans os.environ, que les sous-processus reçoivent)",
      r is not None and r["HEYGEN_API_KEY"] == "herite-heygen" and r["env"] == "herite-heygen"
      and r["GEMINI_API_KEY"] == "", f"{r} {out[-400:]}")
# ~90 bancs posent leurs clés FACTICES par os.environ avant d'importer l'app : elles ne sont pas héritées, on les garde.
r, _, out = enfant("""
    import os
    os.environ["FAL_KEY"] = "factice-du-banc"
    os.environ.setdefault("MESHY_API_KEY", "factice-meshy")
    os.environ["GEMINI_API_KEY"] = "factice-gemini"
""" + LIRE_CLES.replace('print(json.dumps({k: getattr(settings, k) for k in %r}))' % sorted(SECRETS_HERITES),
                        'print(json.dumps({k: getattr(settings, k) for k in ("FAL_KEY", "MESHY_API_KEY", '
                        '"GEMINI_API_KEY", "HEYGEN_API_KEY")}))'))
check("A.5 instance isolée : les clés FACTICES posées par le banc lui-même restent, même par-dessus une héritée",
      r == {"FAL_KEY": "factice-du-banc", "MESHY_API_KEY": "factice-meshy", "GEMINI_API_KEY": "factice-gemini",
            "HEYGEN_API_KEY": ""}, f"{r} {out[-400:]}")

# Les faux HeyGen : aucun réseau. `bloque_thread` imite le contexte TLS qui ne rend jamais la main (magasin de
# certificats Windows) : un thread de l'exécuteur par défaut qu'on ne peut pas interrompre.
SESSION = """
    import asyncio, json, sys, time
    sys.path.insert(0, ".")
    from loguru import logger; logger.remove()
    from app.services import heygen_service as H
    appels = []
    async def faux_paginate(self, path, params, **kw):
        appels.append(path)
        if MODE == "thread":
            await asyncio.to_thread(time.sleep, 25)
        else:
            await asyncio.sleep(3600)
        return []
    H.HeyGenClient._paginate = faux_paginate
    import app.main as M
    from fastapi.testclient import TestClient
    en_vol = []
    with TestClient(M.app, client=("127.0.0.1", 50000)) as c:
        sante = c.get("/api/health").json()
        time.sleep(ATTENTE)
        en_vol = [t for t in H._INFLIGHT.values()]
    print(json.dumps({"heygen": sante.get("heygen_enabled"), "appels": appels,
                      "en_vol_apres": len(H._INFLIGHT),
                      "annulees": all(t.cancelled() for t in en_vol), "vues": len(en_vol)}))
"""
CLE = "HEYGEN_API_KEY=cle-factice-du-banc\n"

print("\n[B] session courte, le faux bloque un thread")
r, dt, out = enfant("MODE, ATTENTE = 'thread', 0.2\n" + textwrap.dedent(SESSION), env_file=CLE)
check("B.1 la clé factice du data-dir active HeyGen (le scénario teste bien le préchargement)",
      r is not None and r["heygen"] is True, f"{r} {out[-600:]}")
check("B.2 le préchargement n'a PAS démarré pendant une session courte", r is not None and r["appels"] == [],
      f"{r}")
check("B.3 le processus se termine vite (< 15 s) malgré un thread qui bloquerait 25 s", dt < 15, f"{dt:.1f} s")

print("\n[C] session longue, préchargement en vol à l'arrêt")
r, dt, out = enfant("MODE, ATTENTE = 'attente', 1.5\n" + textwrap.dedent(SESSION), env_file=CLE,
                    extra={"DEEPOTUS_HEYGEN_WARM_DELAY_S": "0.1"})
check("C.1 le délai est réglable et le préchargement a bien démarré", r is not None and len(r["appels"]) >= 1,
      f"{r} {out[-600:]}")
check("C.2 à l'arrêt, la récupération en vol est annulée", r is not None and r["vues"] >= 1 and r["annulees"],
      f"{r}")
check("C.3 et oubliée (_INFLIGHT vide : un TestClient suivant n'hérite pas d'une tâche d'une boucle morte)",
      r is not None and r["en_vol_apres"] == 0, f"{r}")
check("C.4 le processus se termine vite (< 15 s)", dt < 15, f"{dt:.1f} s")

print("\n[E] le préchargement dépasse sa borne")
r, dt, out = enfant("""
    import asyncio, json, sys, time
    sys.path.insert(0, ".")
    from loguru import logger; logger.remove()
    from app.services import heygen_service as H
    marques = {}
    async def faux_paginate(self, path, params, **kw):
        marques["debut"] = time.monotonic()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            marques["annulee"] = time.monotonic()
            raise
        return []
    H.HeyGenClient._paginate = faux_paginate
    import app.main as M
    M._HEYGEN_WARM_TIMEOUT_S = 0.5
    from fastapi.testclient import TestClient
    with TestClient(M.app, client=("127.0.0.1", 50000)) as c:
        c.get("/api/health")
        time.sleep(2.0)
        marques["fermeture"] = time.monotonic()
        marques["en_vol"] = len(H._INFLIGHT)
    print(json.dumps(marques))
""", env_file=CLE, extra={"DEEPOTUS_HEYGEN_WARM_DELAY_S": "0"})
check("E.1 la borne dépassée annule la récupération ELLE-MÊME (derrière asyncio.shield), AVANT l'arrêt de l'app",
      r is not None and "annulee" in r and r["annulee"] < r["fermeture"] and r["en_vol"] == 0, f"{r} {out[-600:]}")

# Mesuré le 30/09 (test_index_reglages figé) : à l'arrêt, l'annulation tombe sur schedule_loop pendant que SQLAlchemy
# ferme une connexion aiosqlite ; le pool ATTRAPE le CancelledError (« Exception terminating connection ») et la boucle
# repart dormir 60 s — asyncio.runners n'annule qu'UNE fois, l'arrêt attend pour toujours. Le faux ci-dessous avale
# DEUX annulations (celle du lifespan puis celle d'asyncio.runners), comme le pool l'a fait le 30/09.
print("\n[F] une tâche de fond avale son annulation")
AVALE = """
    import asyncio, json, sys, time
    sys.path.insert(0, ".")
    from loguru import logger; logger.remove()
    import app.main as M
    async def boucle_qui_avale():
        avalees = 0
        while True:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                avalees += 1              # comme sqlalchemy.pool._close_connection
                if avalees >= 2:
                    await asyncio.sleep(60)
    M.schedule_loop = boucle_qui_avale
    from fastapi.testclient import TestClient
    with TestClient(M.app, client=("127.0.0.1", 50000)) as c:
        c.get("/api/health")
    print(json.dumps({"fini": True}))
"""
r, dt, out = enfant(AVALE, timeout=40)
check("F.1 l'arrêt de l'app ré-annule une tâche qui a avalé son annulation : le processus se termine (< 15 s)",
      r is not None and r.get("fini") and dt < 15, f"{dt:.1f} s {out[-300:]}")

print("\n[G] schedule_loop elle-même")
r, dt, out = enfant("""
    import asyncio, json, sys, time
    sys.path.insert(0, ".")
    from loguru import logger; logger.remove()
    from app.services import marketing as MK
    async def refresh_qui_avale(max_posts=10):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        return 0
    MK.refresh_x_metrics = refresh_qui_avale
    async def sc():
        t = asyncio.create_task(MK.schedule_loop())
        await asyncio.sleep(0.2)
        t.cancel()
        done, _ = await asyncio.wait([t], timeout=3)
        return bool(done)
    print(json.dumps({"sortie": asyncio.run(asyncio.wait_for(sc(), 10))}))
""", timeout=40)
check("G.1 schedule_loop annulée pendant un tick qui avale l'annulation sort quand même (pas de sommeil de 60 s)",
      r is not None and r["sortie"] is True, f"{r} {out[-400:]}")

print("\n[D] un seul contexte TLS par processus pour HeyGen")
r, _, out = enfant("""
    import json, ssl, sys
    sys.path.insert(0, ".")
    import app.main
    from app.services import heygen_service as H
    n = [0]; orig = ssl.create_default_context
    def compte(*a, **k):
        n[0] += 1; return orig(*a, **k)
    ssl.create_default_context = compte
    import httpx
    clients = [httpx.AsyncClient(verify=H._verify()) for _ in range(3)]
    print(json.dumps({"n": n[0], "meme": H._verify() is H._verify()}))
""")
check("D.1 trois clients HeyGen = UNE construction de contexte TLS, réutilisée",
      r is not None and r["n"] == 1 and r["meme"] is True, f"{r} {out[-400:]}")
src = (BACKEND / "app" / "services" / "heygen_service.py").read_text(encoding="utf-8")
check("D.2 aucun client HeyGen ne reconstruit son contexte (plus de verify=SSL_VERIFY)",
      "verify=SSL_VERIFY" not in src and src.count("verify=_verify()") == 4, "")

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
