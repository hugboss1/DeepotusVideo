# -*- coding: utf-8 -*-
"""Diagnostic en un ecran (plan Settings T1, tache #15 du suivi, 29/09/2026) — poids disque par categorie,
journal des alertes, test LEGER de chaque cle. ZERO reseau : le hook `_get` du module et HeyGen sont remplaces.
Adaptations mesurees le 29/09 sur le DATA_ROOT reel : categories des caches de montage, decks, matieres, sprites,
envois, assets 3D ; format de ligne loguru reel (« AAAA-MM-JJ hh:mm:ss.mmm | NIVEAU   | mod:f:l - msg »).
Run : & $PY tests/test_diagnostic.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzdiag_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                          # noqa: E402
logger.remove()
from app.services import diagnostic as D                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


SECRET = "SECRET-ZX81-0042-cle"


def test_poids_disque():
    R = _tmp / "racine"
    (R / "assets" / "images").mkdir(parents=True)
    (R / "assets" / "images" / "a.png").write_bytes(b"x" * 1000)
    (R / "assets" / "outputs" / "montage_cache").mkdir(parents=True)
    (R / "assets" / "outputs" / "montage_cache" / "p.mp4").write_bytes(b"m" * 300)
    (R / "logs").mkdir(); (R / "logs" / "d.log").write_bytes(b"y" * 10)
    (R / "rebut_decks_2026-08-26").mkdir()
    (R / "rebut_decks_2026-08-26" / "z.bin").write_bytes(b"z" * 500)
    (R / "divers.txt").write_bytes(b"d" * 7)
    r = D.poids_disque(R, cache_s=0)
    cats = {c["nom"]: c for c in r["categories"]}
    check("1.1 images = 1000 o, 1 fichier", cats["Images (Bibliothèque)"]["octets"] == 1000 and cats["Images (Bibliothèque)"]["fichiers"] == 1,
          json.dumps(cats.get("Images (Bibliothèque)")))
    check("1.2 cache de montage compte a part (300 o)", cats["Cache du Montage"]["octets"] == 300, json.dumps(cats.get("Cache du Montage")))
    check("1.3 journal = 10 o", cats["Journal"]["octets"] == 10)
    check("1.4 rebut_* compte a part, avec son chemin", cats["Rebuts"]["octets"] == 500 and "rebut_decks_2026-08-26" in cats["Rebuts"]["chemin"])
    check("1.5 le reste tombe dans « Autre » (7 o)", cats["Autre"]["octets"] == 7, json.dumps(cats.get("Autre")))
    check("1.6 total = somme des categories = 1817 o", r["total_octets"] == 1817 == sum(c["octets"] for c in r["categories"]),
          str(r["total_octets"]))
    check("1.7 aucune categorie n'en contient une autre (pas de double compte)",
          not any(a != b and (b["chemin"] + os.sep).startswith(a["chemin"] + os.sep)
                  for a in r["categories"] for b in r["categories"] if a["nom"] not in ("Rebuts", "Autre") and b["nom"] not in ("Rebuts", "Autre")), "")
    check("1.8 espace libre lu", r["libre_octets"] > 0)
    (R / "assets" / "images" / "b.png").write_bytes(b"x" * 5)
    check("1.9 cache 300 s tenu (pas de nouvelle marche)", D.poids_disque(R, cache_s=300)["total_octets"] == 1817)
    check("1.10 cache 0 = relu", D.poids_disque(R, cache_s=0)["total_octets"] == 1822)
    vide = D.poids_disque(_tmp / "absente", cache_s=0)
    check("1.11 racine absente : zeros, aucune exception", vide["total_octets"] == 0 and all(c["octets"] == 0 for c in vide["categories"]), "")


def test_journal():
    L = _tmp / "logs"
    L.mkdir(exist_ok=True)
    (L / "deepotus-2026-09-27.log").write_text(
        "2026-09-27 09:00:00.000 | ERROR    | app.old:f:1 - vieille erreur\n", encoding="utf-8")
    (L / "deepotus-2026-09-28.log").write_text(
        "2026-09-28 10:00:00.000 | INFO     | app.x:f:1 - rien\n"
        "2026-09-28 18:15:10.486 | WARNING  | app.services.marketing:_fetch_x_metrics_sync:612 - x metrics fetch failed: 401 Unauthorized\n"
        "2026-09-28 10:00:02.000 | ERROR    | app.z:h:3 - cassé\n"
        "ligne sans format\n", encoding="utf-8")
    j = D.journal_erreurs(L, n=10)
    check("2.1 INFO et lignes libres filtrees ; ordre des fichiers puis des lignes",
          [l["niveau"] for l in j] == ["ERROR", "WARNING", "ERROR"], json.dumps(j, ensure_ascii=False))
    check("2.2 message, lieu et horodatage lus (format reel loguru)",
          j[1]["message"] == "x metrics fetch failed: 401 Unauthorized" and j[1]["ou"].startswith("app.services.marketing")
          and j[1]["quand"] == "2026-09-28 18:15:10.486", json.dumps(j[1], ensure_ascii=False))
    check("2.3 n borne le nombre (les plus recentes)", [l["message"] for l in D.journal_erreurs(L, n=1)] == ["cassé"], "")
    check("2.4 dossier absent : liste vide", D.journal_erreurs(_tmp / "nulle_part") == [], "")


def _faux_http(reponses):
    async def _get(url, headers=None, timeout=15.0):
        for frag, (code, corps) in reponses.items():
            if frag in url:
                return code, corps
        return 599, {"detail": "url inattendue"}
    return _get


def test_cles():
    async def sc():
        from app.services import heygen_service as HG
        async def _quota(self):
            return {"remaining_quota": 766, "remaining_usd": 30.64, "billing_type": "wallet"}
        HG.HeyGenClient.remaining_quota = _quota
        D._get = _faux_http({"queue.fal.run": (404, {"detail": "Request not found"}),
                             "api.elevenlabs.io": (200, {"character_count": 100, "character_limit": 1000}),
                             "api.meshy.ai": (200, {"balance": 8240}),
                             "api.anthropic.com": (401, {"error": {"message": "invalid x-api-key"}}),
                             "api.openai.com": (200, {"data": [{"id": "gpt-4o-mini"}]}),
                             "generativelanguage": (200, {"models": [{"name": "models/gemini-flash-latest"}]}),
                             "api.figma.com": (200, {"handle": "olivier"}),
                             "api.telegram.org": (200, {"ok": True, "result": {"username": "deepotus_bot"}}),
                             "11434": (200, {"models": [{"name": "qwen2.5:14b"}]})})
        noms = ("FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY", "MESHY_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                "GEMINI_API_KEY", "FIGMA_TOKEN", "TELEGRAM_BOT_TOKEN")
        r = {n: await D.tester_cle(n, SECRET) for n in noms}
        r["OLLAMA_URL"] = await D.tester_cle("OLLAMA_URL", "http://127.0.0.1:11434")
        check("3.1 fal : 404 sur une requete fictive = cle acceptee", r["FAL_KEY"]["ok"] is True and "404" in r["FAL_KEY"]["message"], json.dumps(r["FAL_KEY"]))
        check("3.2 HeyGen : credits et dollars du portefeuille", r["HEYGEN_API_KEY"]["ok"] is True
              and r["HEYGEN_API_KEY"]["details"] == {"credits": 766, "usd": 30.64}, json.dumps(r["HEYGEN_API_KEY"]))
        check("3.3 ElevenLabs : restant = limite - utilise", r["ELEVENLABS_API_KEY"]["ok"] and r["ELEVENLABS_API_KEY"]["details"]["restant"] == 900, "")
        check("3.4 Meshy : solde", r["MESHY_API_KEY"]["details"]["credits"] == 8240, "")
        check("3.5 Anthropic : 401 -> refusee, message du fournisseur", r["ANTHROPIC_API_KEY"]["ok"] is False
              and "invalid x-api-key" in r["ANTHROPIC_API_KEY"]["message"], json.dumps(r["ANTHROPIC_API_KEY"]))
        check("3.6 Telegram : nom du bot ; Ollama : modeles", r["TELEGRAM_BOT_TOKEN"]["details"]["bot"] == "deepotus_bot"
              and r["OLLAMA_URL"]["details"]["modeles"] == ["qwen2.5:14b"], "")
        check("3.7 aucune valeur de cle recopiee dans un resultat", all(SECRET not in json.dumps(v) for v in r.values()), "")
        D._get = _faux_http({})
        r2 = await D.tester_cle("OPENAI_API_KEY", SECRET)
        check("3.8 code inattendu -> indetermine (ok None), pas rouge", r2["ok"] is None and "indéterminé" in r2["message"], json.dumps(r2))
        r3 = await D.tester_cle("X_API_KEY", SECRET)
        check("3.9 X : test de groupe seulement", r3["ok"] is None and "quatre" in r3["message"], json.dumps(r3))
        r4 = await D.tester_cle("FAL_KEY", "  ")
        check("3.10 valeur vide -> « vide », aucun appel", r4 == {"ok": None, "message": "vide", "details": {}}, json.dumps(r4))
        async def _boum(url, headers=None, timeout=15.0):
            raise RuntimeError("reseau coupe " + SECRET)
        D._get = _boum
        r5 = await D.tester_cle("OPENAI_API_KEY", SECRET)
        check("3.11 une exception ne casse pas l'ecran (ok False) et ne recopie pas la cle",
              r5["ok"] is False and SECRET not in json.dumps(r5), json.dumps(r5))
        check("3.12 TESTABLES : les cles a secret, pas les reglages (modeles, voix, chat id)",
              D.testable("FAL_KEY") and D.testable("X_API_SECRET") and not D.testable("OPENAI_MODEL")
              and not D.testable("TELEGRAM_CHAT_ID") and not D.testable("ELEVENLABS_VOICE_ID_FR"), "")
    asyncio.run(sc())


test_poids_disque(); test_journal(); test_cles()
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
