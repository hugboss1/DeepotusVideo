# -*- coding: utf-8 -*-
"""T101 (plan-son-vfx T4, P3) — l'API du tiroir Sons : mtime dans /audio (tri par date), tags éditables
(PUT /audio/meta/{fn}) FUSIONNÉS dans le sidecar sans rien perdre de l'entrée (prompt, starter_id, parent),
garde-fous (inconnu, traversée, corps invalide).
Run: python tests/test_sons_drawer_api.py (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzdrawer_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from loguru import logger
logger.remove()
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services import sfx_service as S
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

print("\n[1] sanitize_tags")
check("trim, espaces internes réduits, dédoublonnés sans casse, ≤ 24 car.",
      S.sanitize_tags([" Impact ", "impact", "x" * 40, "grave  sourd", "", 7, None]) == ["Impact", "x" * 24, "grave sourd"])
check("≤ 12 tags", len(S.sanitize_tags([f"t{i}" for i in range(20)])) == 12)
check("dédoublonnage SANS casse dans les deux sens : la première graphie gagne",
      S.sanitize_tags(["impact", "Impact", "IMPACT"]) == ["impact"], str(S.sanitize_tags(["impact", "Impact", "IMPACT"])))
check("non-liste → []", S.sanitize_tags("impact") == [] and S.sanitize_tags(None) == [])

audio = S._audio_dir()
(audio / "a.mp3").write_bytes(b"ID3a"); (audio / "b.mp3").write_bytes(b"ID3b"); (audio / "cat.mp3").write_bytes(b"ID3c")
os.utime(audio / "a.mp3", (1_700_000_000, 1_700_000_000))
os.utime(audio / "cat.mp3", (1_600_000_000, 1_600_000_000))
S.record_meta("cat.mp3", {"kind": "sfx", "prompt": "porte qui grince", "starter_id": "kenney-door", "tags": ["porte"]})
(audio / "_sfx_meta.json.bak").write_bytes(b"x")

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        print("\n[2] GET /audio")
        d = (await c.get("/api/audio")).json()["audio"]
        check("tri décroissant par date, mtime servi en secondes entières", [x["name"] for x in d] == ["b.mp3", "a.mp3", "cat.mp3"]
              and d[1]["mtime"] == 1_700_000_000 and d[2]["mtime"] == 1_600_000_000 and isinstance(d[0]["mtime"], int), str(d))
        print("\n[3] PUT /audio/meta/{fn}")
        r = await c.put("/api/audio/meta/a.mp3", json={"tags": [" Impact ", "impact", "x" * 40, "grave", "", 7] + [f"t{i}" for i in range(20)]})
        check("tags nettoyés : trim, dédoublonnés, ≤ 24 car., ≤ 12", r.status_code == 200 and r.json()["meta"]["tags"][:3] == ["Impact", "x" * 24, "grave"]
              and len(r.json()["meta"]["tags"]) == 12, r.text[:200])
        check("sidecar écrit", S.load_meta()["a.mp3"]["tags"][0] == "Impact")
        check("kind déduit pour un fichier sans entrée (import)", S.load_meta()["a.mp3"].get("kind") == "import")
        r = await c.put("/api/audio/meta/cat.mp3", json={"tags": ["porte", "bois"]})
        m = S.load_meta()["cat.mp3"]
        check("FUSION : prompt, starter_id et kind gardés", r.status_code == 200 and m["tags"] == ["porte", "bois"]
              and m["prompt"] == "porte qui grince" and m["starter_id"] == "kenney-door" and m["kind"] == "sfx", str(m))
        r = await c.put("/api/audio/meta/cat.mp3", json={"tags": []})
        check("tags vidés : liste vide, le reste intact", r.status_code == 200 and S.load_meta()["cat.mp3"]["tags"] == []
              and S.load_meta()["cat.mp3"]["starter_id"] == "kenney-door")
        r = await c.put("/api/audio/meta/zzz.mp3", json={"tags": ["a"]})
        check("inconnu : 404", r.status_code == 404, str(r.status_code))
        r = await c.put("/api/audio/meta/..%2F..%2Ft.db", json={"tags": ["a"]})
        check("traversée : refusée (404, ou 405 quand le %2F décodé ne correspond plus à la route), sidecar intact", r.status_code in (404, 405) and "t.db" not in S.load_meta(), str(r.status_code))
        r = await c.put("/api/audio/meta/_sfx_meta.json.bak", json={"tags": ["a"]})
        check("un fichier qui n'est pas un son : 404", r.status_code == 404, str(r.status_code))
        r = await c.put("/api/audio/meta/a.mp3", content=b"pas du json", headers={"Content-Type": "application/json"})
        check("corps invalide : 400, tags inchangés", r.status_code == 400 and S.load_meta()["a.mp3"]["tags"][0] == "Impact", str(r.status_code))
        r = await c.put("/api/audio/meta/a.mp3", json={"tags": "impact"})
        check("tags non-liste : 400", r.status_code == 400, str(r.status_code))
        print("\n[4] GET /audio/meta")
        m = (await c.get("/api/audio/meta")).json()["meta"]
        check("GET /audio/meta rend les tags", m["a.mp3"]["tags"][0] == "Impact" and m["cat.mp3"]["starter_id"] == "kenney-door")
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
