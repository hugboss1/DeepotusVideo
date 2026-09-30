# -*- coding: utf-8 -*-
"""Sources en legende (T9), voix selon le sujet (T10), memoire notee au lancement d'un reel (T7) — plan News 2026-09-03,
tache #34 du suivi, 30/09/2026.

Aucun reseau, aucun LLM : `summarizer.available` est faux, `rewrite_script` et `_chat_dispatch` sont des espions qui
comptent leurs appels, `pipeline.run_news_illustration` est remplace. Data-dir temporaire.
Temoin positif : la persona de la base (a57cbae) n'a PAS de bloc voice_modes (les quatre modes ne pilotaient rien).
Run (depuis backend/) : & $PY tests/test_news_legende_voix.py"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dznewslv_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import summarizer, news_caption as C, news_voice as V, news_memory as M, plafonds as P  # noqa: E402
from app.api.routes import pipeline                                 # noqa: E402
from app.services.storage import init_db                            # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


appels, reecrits = [], []
reponse_llm = [None]
summarizer.available = lambda: False
summarizer.rewrite_script = lambda *a, **k: (reecrits.append(1), (None, ""))[1]
def _espion(p, s, m):
    appels.append(p)
    return reponse_llm[0], ("anthropic" if reponse_llm[0] else "")
summarizer._chat_dispatch = _espion
summarizer.active_provider = lambda: "anthropic"

ITEM = {"title": "Solana network hits record daily transactions", "summary": "Records everywhere.",
        "source_name": "CoinDesk", "source_id": "s1", "id": "a1",
        "link": "https://www.coindesk.com/markets/2026/09/03/solana-record", "published": "2026-09-03T11:00:00+00:00"}

print("\n[T] temoin")
r0 = subprocess.run(["git", "show", "a57cbae:backend/app/personas/deepotus.json"], capture_output=True, cwd=str(_ICI.parent))
check("T1 la persona de la base n'a pas de voice_modes", r0.returncode == 0 and "voice_modes" not in json.loads(r0.stdout.decode("utf-8")))

print("\n[A] la ligne de sources (T9)")
L = C.bloc_sources([ITEM], langue="EN")
check("A1 media, date et domaine, sans www.", L == "Sources: CoinDesk, 2026-09-03, coindesk.com", L)
check("A2 en francais", C.bloc_sources([ITEM], langue="FR").startswith("Sources : CoinDesk"))
it = dict(ITEM, doublons=[{"source_name": "Decrypt", "link": "https://decrypt.co/a"},
                          {"source_name": "coindesk", "link": "https://coindesk.com/b"}, "pas un dict"])
L = C.bloc_sources([it], langue="EN")
check("A3 les medias fondus sont cites, sans doublon (casse ignoree), un doublon non-dict ignore",
      L.lower().count("coindesk,") == 1 and "Decrypt, 2026-09-03, decrypt.co" in L, L)
check("A4 un article sans lien ni date garde son media", C.bloc_sources([dict(ITEM, link="", published="")]) == "Sources: CoinDesk")
check("A5 aucun media : chaine vide", C.bloc_sources([]) == "" and C.bloc_sources([{"title": "x"}]) == "")
L = C.bloc_sources([dict(ITEM, source_name=f"Media {n}", link=f"https://m{n}.com/a") for n in range(9)])
check("A6 bornee a quatre medias, plus le compte", L.count(" | ") == C.MEDIAS_MAX - 1 and L.endswith(" +5"), L)
check("A7 un lien avec identifiants et port ne fuit que le domaine", C._domaine("https://u:p@www.Ex.com:8443/a") == "ex.com")

print("\n[B] la voix (T10)")
modes = pipeline.engine.persona.get("voice_modes") or {}
check("B1 la persona porte ses quatre modes complets", set(modes) == set(V.MODES) and all(
    m.get("description") and m.get("style_hints") and m.get("example_caption_en") and m.get("example_caption_fr")
    and isinstance(m.get("sujets"), list) and m["sujets"] for m in modes.values()), str(sorted(modes)))
check("B2 oracle garde la queue de legende d'avant (« From the deep. »)",
      modes.get("oracle", {}).get("example_caption_en", "").split("\n")[-1].startswith("From the deep."))
from app.services.prompt_engine import _voice_mode_block
check("B3 le bloc de mode est resolu par le moteur", _voice_mode_block(pipeline.engine.persona, "memer") is not None
      and _voice_mode_block(pipeline.engine.persona, "inconnu") is None)
appels.clear()
cas = [("Bitcoin crashes 20% after liquidation cascade", "alpha"), ("A dog meme coin overtakes a bank in market cap", "memer"),
       ("Central bank keeps its rate unchanged, guidance steady", "zen"), ("Un sujet parfaitement quelconque", "oracle")]
res = [(V.choisir_mode([{"title": t}])[0], m) for t, m in cas]
check("B4 sans demande, les mots du sujet decident (alpha, memer, zen, oracle par defaut)", all(a == b for a, b in res), str(res))
check("B5 ... et AUCUN appel au fournisseur", appels == [], str(len(appels)))
m, pq = V.choisir_mode([{"title": cas[0][0]}])
check("B6 le motif nomme les mots", "crash" in pq and "liquidation" in pq, pq)
check("B7 un mot compose (central bank) exige ses deux mots : « Bank crash » reste alpha",
      V.choisir_mode([{"title": "Bank crash hits markets"}])[0] == "alpha", str(V.choisir_mode([{"title": "Bank crash hits markets"}])))
reponse_llm[0] = json.dumps({"mode": "memer", "pourquoi": "le sujet est absurde"})
check("B8 temoin : llm=True, le LLM choisit, un appel", V.choisir_mode([{"title": cas[2][0]}], llm=True) == ("memer", "le sujet est absurde")
      and len(appels) == 1)
reponse_llm[0] = json.dumps({"mode": "pirate", "pourquoi": "arr"})
check("B9 un mode invente est refuse (repli deterministe)", V.choisir_mode([{"title": cas[0][0]}], llm=True)[0] == "alpha")
reponse_llm[0] = "[1,2]"
check("B10 une reponse sans objet JSON ne leve pas (repli)", V.choisir_mode([{"title": cas[0][0]}], llm=True)[0] == "alpha")
reponse_llm[0] = json.dumps({"mode": "memer", "pourquoi": "x"})
check("B11 le mode force gagne toujours", V.choisir_mode([{"title": "Bitcoin crashes"}], force="zen", llm=True)
      == ("zen", "mode force par l'utilisateur"))
reponse_llm[0] = None

print("\n[C] la route /news/script")
corps = {"items": [dict(ITEM, title=cas[0][0])], "language": "EN", "max_words": 60, "read_articles": False}
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    appels.clear()
    r = c.post("/api/news/script", json=corps)
    j = r.json() if r.status_code == 200 else {}
    check("C1 200, ligne de sources en fin de legende", r.status_code == 200 and j.get("sources_line", "").startswith("Sources: CoinDesk")
          and j.get("suggested_caption", "").rstrip().endswith(j.get("sources_line", "--")), f"{r.status_code} {str(j)[:300]}")
    check("C2 sans voice_mode : mode deduit du sujet et applique, avec son motif",
          j.get("voice_mode_auto") == "alpha" and j.get("voice_mode_applied") == "alpha" and "crash" in j.get("voice_mode_reason", ""), str(j)[:300])
    check("C3 aucun appel LLM sans demande", appels == [], str(len(appels)))
    r = c.post("/api/news/script", json=dict(corps, voice_mode="zen"))
    j = r.json()
    check("C4 un mode envoye par l'ecran reste prioritaire", j.get("voice_mode_applied") == "zen" and j.get("voice_mode_auto") == "zen")
    c.post("/api/news/script", json=dict(corps, voice_mode="oracle", language="FR"))
    check("C5 la legende en francais", c.post("/api/news/script", json=dict(corps, language="FR")).json().get("sources_line", "").startswith("Sources : "))
    # T10 sur demande : la garde des plafonds chiffre l'appel ; au-dessus du plafond, 402 et aucun appel
    P.enregistrer({"global_usd": 0.000001, "par_moteur": {}, "alerte_pct": 80})
    r = c.post("/api/news/script", json=dict(corps, voice_mode_llm=True))
    d = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else {}
    devis_avec = ((d or {}).get("dz_plafond") or {}).get("devis_usd", 0) if isinstance(d, dict) else 0
    r2 = c.post("/api/news/script", json=corps)
    d2 = r2.json().get("detail") if r2.headers.get("content-type", "").startswith("application/json") else {}
    devis_sans = ((d2 or {}).get("dz_plafond") or {}).get("devis_usd", 0) if isinstance(d2, dict) else 0
    check("C6 voice_mode_llm : la garde chiffre UN appel de plus (devis plus haut), 402 sans appel",
          r.status_code == 402 and r2.status_code == 402 and devis_avec > devis_sans > 0 and appels == [], f"{r.status_code} {devis_avec} {devis_sans}")
    reponse_llm[0] = json.dumps({"mode": "memer", "pourquoi": "absurde"})
    r = c.post("/api/news/script", json=dict(corps, voice_mode_llm=True), headers={"X-DZ-Plafond": "confirme"})
    check("C7 confirme : le LLM choisit (un appel)", r.status_code == 200 and r.json().get("voice_mode_auto") == "memer" and len(appels) == 1,
          f"{r.status_code} {r.text[:200]}")
    appels.clear()
    r = c.post("/api/news/script", json=dict(corps, voice_mode="zen", voice_mode_llm=True), headers={"X-DZ-Plafond": "confirme"})
    check("C8 mode force + voice_mode_llm : aucun appel (le force gagne)", r.status_code == 200 and appels == [] and r.json().get("voice_mode_auto") == "zen")
    reponse_llm[0] = None
    P.enregistrer({"global_usd": 0, "par_moteur": {}})

    print("\n[D] /news/illustration note la couverture (T7)")
    lances = []
    async def _faux_run(items, **k):
        lances.append(items)
        if items and items[0].get("title") == "ECHEC":
            raise RuntimeError("rendu en echec")
        return k.get("job_id")
    pipeline.run_news_illustration = _faux_run
    if M.chemin_couverture().is_file():
        M.chemin_couverture().unlink()
    r = c.post("/api/news/illustration", json={"items": [ITEM], "per_card_s": 3.5, "engine": "ffmpeg"})
    job = r.json().get("job_id")
    s = M.sujets_couverts()
    check("D1 un reel lance note ses sujets (post_id = job, source_id garde)", r.status_code == 200 and len(s) == 1
          and s[0]["post_id"] == job and s[0]["source_id"] == "s1", f"{r.status_code} {s}")
    r = c.post("/api/news/illustration", json={"items": [dict(ITEM, title="ECHEC")], "per_card_s": 3.5, "engine": "ffmpeg"})
    check("D2 un reel en echec ne note rien", len(lances) == 2 and len(M.sujets_couverts()) == 1, str(len(M.sujets_couverts())))

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
