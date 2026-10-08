# -*- coding: utf-8 -*-
"""t140 (Photolab P5) — « À propos » : les licences servies par le pont.
  GET /api/photolab/licences -> version, dépôt, licence, et la liste des textes livrés (NOTICE, licences du moteur,
  licences des matériaux intégrés) ; GET /api/photolab/licences/{nom} -> le texte, pour un nom de CETTE liste seulement.
Run : & $PY tests/test_photolab_apropos.py   (depuis backend/)"""
import asyncio, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt140a_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


ATTENDUS = {"NOTICE-photocraft.txt", "licences-photocraft/NOTICE", "licences-photocraft/OFL-Inter.txt",
            "licences-photocraft/OFL-JetBrainsMono.txt", "licences-photocraft/LICENSE-SCOWL.txt",
            "licences-photocraft/LICENSE-lucide.txt", "LICENSE-MIT", "LICENSE-APACHE", "OFL-biz-ud-mincho.txt",
            "OFL-biz-ud-pgothic.txt", "OFL-shippori-mincho.txt"}


async def scenario():
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        r = await c.get("/api/photolab/licences")
        j = r.json() if r.status_code == 200 else {}
        check("1a /licences : version 0.3.0, dépôt, double licence", j.get("version") == "0.3.0"
              and j.get("depot") == "storytold/photocraft" and j.get("licence") == "MIT OR Apache-2.0", j)
        check("1b la liste contient chaque texte livré (NOTICE en tête)", set(j.get("fichiers", [])) == ATTENDUS
              and (j.get("fichiers") or [""])[0] == "NOTICE-photocraft.txt", j.get("fichiers"))
        for nom, marque in (("NOTICE-photocraft.txt", "composants tiers"), ("LICENSE-MIT", "MIT License"),
                            ("licences-photocraft/NOTICE", "Third-party material"), ("OFL-shippori-mincho.txt", "Open Font License")):
            r = await c.get(f"/api/photolab/licences/{nom}")
            check(f"2a {nom} servi en texte UTF-8", r.status_code == 200 and marque in r.text
                  and r.headers.get("content-type", "").startswith("text/plain") and "utf-8" in r.headers.get("content-type", ""),
                  (r.status_code, r.headers.get("content-type"), r.text[:80]))
        for mauvais in ("README.md", "photocraft.json", "photocraft-cli.exe", "..%2Fphotocraft.json",
                        "licences-photocraft/..%2F..%2Fphotocraft.json", "LICENSE-mit", "portable.txt"):
            r = await c.get(f"/api/photolab/licences/{mauvais}")
            check(f"2b {mauvais} : hors de la liste -> 404, jamais un autre fichier", r.status_code == 404
                  or (r.status_code == 200 and "text/html" in r.headers.get("content-type", "")), (r.status_code, r.text[:80]))


try:
    asyncio.run(scenario())
finally:
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
