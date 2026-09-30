# -*- coding: utf-8 -*-
"""Le score de pertinence News (plan 2026-09-03 T4, tache #33 du suivi, 30/09/2026).

Decision de l'utilisateur : score DETERMINISTE par defaut, LLM seulement sur demande (`llm=True`). Aucun reseau :
`summarizer._chat_dispatch` est remplace par un espion qui COMPTE ses appels — l'assertion negative « sans llm=True,
zero appel » a son temoin positif (le meme espion compte 1 appel avec llm=True).
Run (depuis backend/) : & $PY tests/test_news_rank.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrank_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.services import news_rank as R, summarizer                # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


appels = []
def espion(reponse, fournisseur="anthropic"):
    def f(p, s, m):
        appels.append((p, s, m))
        if isinstance(reponse, Exception):
            raise reponse
        return reponse, (fournisseur if reponse else "")
    summarizer._chat_dispatch = f


def _it(titre, source="CoinDesk", sid="s1", resume="", pub="2026-09-03T11:00:00+00:00", doublons=None):
    return {"id": titre[:10], "title": titre, "source_name": source, "source_id": sid, "summary": resume,
            "link": "https://x/1", "published": pub, "doublons": doublons or []}


SOL = _it("Solana network hits record daily transactions")
BAK = _it("Local bakery wins regional prize", source="NPR", sid="s9")
LLM_OK = json.dumps([{"id": "Solana net", "score": 93, "pourquoi": "sujet coeur de la communaute"},
                     {"id": "Local bake", "score": 4, "pourquoi": "hors sujet"}])

print("\n[A] par defaut : deterministe, AUCUN appel")
espion(LLM_OK)
appels.clear()
c = R.classer([BAK, SOL], brief="crypto Solana deepotus")
check("A1 sans llm=True : zero appel au fournisseur, meme quand il repondrait", appels == [], str(len(appels)))
check("A2 origine deterministe, scores bornes", all(i["score_origine"] == "deterministe" and 0 <= i["score"] <= 100
                                                     for i in c), str(c))
check("A3 le sujet du brief passe devant, son motif le dit", c[0]["title"].startswith("Solana")
      and "solana" in c[0]["score_pourquoi"], c[0]["score_pourquoi"])
check("A4 bareme : socle 10 + un mot du brief 18 = 28 ; hors brief = 10", c[0]["score"] == 28 and c[1]["score"] == 10,
      f'{c[0]["score"]} {c[1]["score"]}')
a = [i["score"] for i in R.classer([SOL, _it("AI Act delayed once more", sid="s2")], brief="crypto")]
b = [i["score"] for i in R.classer([SOL, _it("AI Act delayed once more", sid="s2")], brief="crypto")]
check("A5 le meme flux rend deux fois les memes scores", a == b, f"{a} {b}")
rep = _it("Bitcoin ETF outflows", doublons=[{"source_name": "X"}, {"source_name": "Y"}, {"source_name": "Z"}])
check("A6 reprises : +12 par media, plafond 24", R.score_deterministe(rep, [])[0] == 34, str(R.score_deterministe(rep, [])))
long_ = _it("Bitcoin", resume=" ".join(f"mot{n}x" for n in range(45)))
check("A7 corps lisible (>= 40 jetons distincts) : +12", R.score_deterministe(long_, [])[0] == 22
      and "article lisible" in R.score_deterministe(long_, [])[1], str(R.score_deterministe(long_, [])))
mots = ["solana", "network", "record", "daily", "transact"]
check("A8 mots du brief : 18 chacun, plafond 54", R.score_deterministe(SOL, mots)[0] == 64, str(R.score_deterministe(SOL, mots)))
check("A9 un mot repete dans le brief ne compte qu'une fois", R.classer([SOL], brief="solana solana solana")[0]["score"] == 28)
check("A10 accents ignores (brief « Sólana »)", R.classer([SOL], brief="Sólana")[0]["score"] == 28)

print("\n[B] sur demande : le LLM")
appels.clear()
c = R.classer([BAK, SOL], brief="crypto Solana deepotus", llm=True)
check("B1 temoin positif : avec llm=True, UN appel pour tout le lot", len(appels) == 1, str(len(appels)))
check("B2 le score et le motif du LLM, son origine", c[0]["score"] == 93 and c[0]["score_origine"] == "anthropic"
      and c[0]["score_pourquoi"] == "sujet coeur de la communaute" and c[1]["score"] == 4, str(c))
check("B3 le prompt porte le brief et les identifiants", "crypto Solana deepotus" in appels[0][0]
      and "id=Solana net" in appels[0][0] and "id=Local bake" in appels[0][0], appels[0][0][:300])
check("B4 max_tokens = sortie chiffree par jetons_llm", appels[0][2] == R.jetons_llm(2)[1], str(appels[0][2]))
cl = "`" * 3
espion("Voici :\n" + cl + 'json\n[{"id": "Solana net", "score": 70, "pourquoi": "ok"}]\n' + cl + "\nVoila.", "openai")
c = R.classer([SOL], brief="crypto", llm=True)
check("B5 un LLM bavard autour du JSON est lu", c[0]["score"] == 70 and c[0]["score_origine"] == "openai", str(c))
espion("je ne sais pas faire", "gemini")
check("B6 JSON illisible : repli deterministe", R.classer([SOL], brief="crypto Solana", llm=True)[0]["score_origine"] == "deterministe")
espion(RuntimeError("socket ferme"))
check("B7 un fournisseur qui leve : repli deterministe, pas d'exception",
      R.classer([SOL], brief="crypto Solana", llm=True)[0]["score_origine"] == "deterministe")
espion(None)
check("B8 aucune cle (None) : repli deterministe", R.classer([SOL], brief="crypto", llm=True)[0]["score_origine"] == "deterministe")
espion(json.dumps([{"id": "fantome", "score": 99, "pourquoi": "invente"}]))
c = R.classer([SOL], brief="crypto", llm=True)
check("B9 un id inconnu est ignore", c[0]["score_origine"] == "deterministe" and c[0]["score"] != 99, str(c))
espion(json.dumps([{"id": "Solana net", "score": 4000, "pourquoi": "trop"}]))
check("B10 un score hors bornes est ramene a 100", R.classer([SOL], brief="crypto", llm=True)[0]["score"] == 100)
espion(json.dumps([{"id": "Solana net", "score": 4000, "pourquoi": "trop"}]))
check("B10b borne AVANT le malus : 4000 puis -15 = 85", R.classer([SOL], brief="c", llm=True, penalites={"s1": 15})[0]["score"] == 85)
espion(json.dumps([{"id": "Solana net", "score": "1e999", "pourquoi": "infini"}]))
check("B11 un score infini ne leve pas (repli)", R.classer([SOL], brief="crypto", llm=True)[0]["score_origine"] == "deterministe")
appels.clear()
espion(LLM_OK)
beaucoup = [_it(f"{n:02d} sujet, numero {n} de la journee", sid=f"s{n}") for n in range(R.LOT_MAX + 7)]
check("B12a temoin de fixture : identifiants distincts", len({i["id"] for i in beaucoup}) == len(beaucoup))
R.classer(beaucoup, brief="x", llm=True)
check(f"B12 un seul appel, LOT_MAX={R.LOT_MAX} titres au plus", len(appels) == 1
      and appels[0][0].count("- id=") == R.LOT_MAX and "numero 39" in appels[0][0] and "numero 40" not in appels[0][0],
      str(appels[0][0].count("- id=")))

hors = beaucoup[R.LOT_MAX + 3]
espion(json.dumps([{"id": hors["id"], "score": 99, "pourquoi": "jamais envoye"}]))
c = {i["id"]: i for i in R.classer(beaucoup, brief="x", llm=True)}
check("B13 un id hors du lot envoye (au-dela de LOT_MAX) n'est pas note par le LLM",
      c[hors["id"]]["score_origine"] == "deterministe" and c[hors["id"]]["score"] != 99, str(c[hors["id"]]))

print("\n[C] tete, malus, bords")
espion(None)
c = R.classer([_it(f"Solana sujet numero {n} de la journee", sid=f"s{n}") for n in range(9)], brief="crypto Solana")
tete = [i for i in c if i["en_tete"]]
check("C1 EN_TETE_MAX = 5 et les cinq premiers sont en tete", R.EN_TETE_MAX == 5 and len(tete) == 5 and c[:5] == tete)
vieux = _it("Solana older", pub="2026-09-01T00:00:00+00:00")
neuf = _it("Solana newer", pub="2026-09-03T00:00:00+00:00")
check("C2 a score egal, le plus recent d'abord", [i["title"] for i in R.classer([vieux, neuf], brief="solana")]
      == ["Solana newer", "Solana older"])
c = R.classer([SOL], brief="solana", penalites={"s1": 15})
check("C3 malus de source retranche et dit", c[0]["score"] == 13 and "-15 source" in c[0]["score_pourquoi"], str(c))
check("C4 une liste vide ne leve pas", R.classer([], brief="crypto", llm=True) == [])
orig = dict(SOL)
R.classer([SOL], brief="solana")
check("C5 les articles d'entree ne sont pas mutes", SOL == orig)

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
