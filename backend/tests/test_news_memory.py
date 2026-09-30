# -*- coding: utf-8 -*-
"""La memoire des sujets deja couverts (plan 2026-09-03 T7, tache #34 du suivi, 30/09/2026).

Banc-miroir : il relit `news/couverture.json` sur le disque apres chaque note. Aucun reseau, aucun LLM. Data-dir
temporaire : la vraie memoire de l'utilisateur n'est jamais touchee.
Run (depuis backend/) : & $PY tests/test_news_memory.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dznewsm_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "outputs").mkdir(exist_ok=True)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.services import news_memory as M                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def rase():
    p = M.chemin_couverture()
    if p.is_file():
        p.unlink()


def _it(titre, source="CoinDesk", sid="s1"):
    return {"id": titre[:10], "title": titre, "source_name": source, "source_id": sid, "link": "https://x/1",
            "published": "2026-09-03T11:00:00+00:00"}


SOL = "Solana network hits record daily transactions"
check("T0 temoin : la memoire vit dans le data-dir temporaire, a cote de cache.json", str(M.chemin_couverture()).startswith(str(_tmp))
      and M.chemin_couverture().parent.name == "news", str(M.chemin_couverture()))

print("\n[A] noter")
rase()
n = M.noter_couverture([_it(SOL), _it("")], post_id="p1", quand="2026-09-03T12:00:00+00:00")
ecrit = json.loads(M.chemin_couverture().read_text("utf-8"))
s0 = ecrit["sujets"][0] if ecrit["sujets"] else {}
check("A1 une note arrive sur le disque, un titre vide est ignore", n == 1 and len(ecrit["sujets"]) == 1, str(ecrit)[:200])
check("A2 le sujet porte post, source, jetons, titre et date", s0.get("post_id") == "p1" and s0.get("source_id") == "s1"
      and "solana" in s0.get("jetons", []) and s0.get("titre", "").startswith("Solana") and s0.get("quand", "").startswith("2026-09-03T12"))
rase()
check("A3 rien a noter : aucun fichier ecrit", M.noter_couverture([_it("")], post_id="x") == 0 and not M.chemin_couverture().is_file())

print("\n[B] marquer")
rase()
M.noter_couverture([_it(SOL)], post_id="p1", quand="2026-09-03T12:00:00+00:00")
m = M.marquer([_it("Solana network hits a record in daily transactions", sid="s2"),
               _it("Storm Bernard floods southern Spain", sid="s3")], maintenant="2026-09-04T09:00:00+00:00")
check("B1 un article proche d'un sujet couvert porte son titre", (m[0].get("deja_couvert") or "").startswith("Solana network hits record"), str(m[0]))
check("B2 un sujet different ne porte rien (None, pas absent)", "deja_couvert" in m[1] and m[1]["deja_couvert"] is None)
m = M.marquer([_it("Solana network hits a record in daily transactions")], maintenant="2026-10-10T09:00:00+00:00")
check("B3 au-dela de 30 jours, plus de marque", m[0]["deja_couvert"] is None)
m = M.marquer([_it("Solana network hits a record in daily transactions")], maintenant="2026-09-01T09:00:00+00:00")
check("B4 un sujet note APRES le moment de reference ne marque pas", m[0]["deja_couvert"] is None)
rase()
M.noter_couverture([_it("Bitcoin rally halts trading floor")], post_id="p2", quand="2026-09-03T12:00:00+00:00")
m = M.marquer([_it("Bitcona rallx haltz tradinq floov")], maintenant="2026-09-04T09:00:00+00:00")
check("B6 la conjonction du dedoublonnage est exigee : ratio 0,839 mais Jaccard 0 -> pas de marque", m[0]["deja_couvert"] is None)
it = _it(SOL)
M.marquer([it], maintenant="2026-09-04T09:00:00+00:00")
check("B5 marquer ne mute pas les articles d'entree", "deja_couvert" not in it)

print("\n[C] malus de source")
rase()
for k in range(4):
    M.noter_couverture([_it(f"Sujet CoinDesk numero {k}")], post_id=f"p{k}", quand=f"2026-09-0{k + 1}T12:00:00+00:00")
M.noter_couverture([_it("Un seul sujet BBC", source="BBC", sid="s2")], post_id="p9", quand="2026-09-02T12:00:00+00:00")
mal = M.penalites_de_source(maintenant="2026-09-04T09:00:00+00:00")
check("C1 4 contre 1 : la source sur-representee perd, l'autre rien", mal.get("s1", 0) > 0 and mal.get("s2") == 0, str(mal))
check("C2 la note du 04/09 12 h est APRES la reference (04/09 9 h) : 3 contre 1, 25 * (0,75 - 0,5) / 0,5 = 12,5 -> 12",
      mal.get("s1") == 12, str(mal))
check("C3 borne MALUS_MAX", all(0 <= v <= M.MALUS_MAX for v in mal.values()))
check("C4 hors fenetre de 14 jours : plus de malus", M.penalites_de_source(maintenant="2026-10-01T00:00:00+00:00") == {})
rase()
M.noter_couverture([_it("Seul", sid="s1")], post_id="p", quand="2026-09-03T12:00:00+00:00")
check("C5 une seule source : aucun malus", M.penalites_de_source(maintenant="2026-09-04T00:00:00+00:00") == {})

print("\n[D] bornes et robustesse")
rase()
for k in range(M.SUJETS_MAX + 15):
    M.noter_couverture([_it(f"Sujet parfaitement distinct numero {k}")], post_id=f"p{k}",
                       quand=(f"2026-09-03T12:00:00+00:00" if k else "2026-01-01T00:00:00+00:00"))
ecrit = json.loads(M.chemin_couverture().read_text("utf-8"))
check("D1 la memoire est bornee a SUJETS_MAX", len(ecrit["sujets"]) == M.SUJETS_MAX, str(len(ecrit["sujets"])))
check("D2 le plus vieux part en premier", all(s["post_id"] != "p0" for s in ecrit["sujets"]))
M.chemin_couverture().write_text("]]pas du json[[", encoding="utf-8")
check("D3 fichier corrompu : lecture vide, marque None, pas d'exception", M.sujets_couverts() == []
      and M.marquer([_it(SOL)], maintenant="2026-09-04T09:00:00+00:00")[0]["deja_couvert"] is None)
M.chemin_couverture().write_text(json.dumps({"sujets": ["pas un dict", {"titre": SOL, "quand": "2026-09-03T12:00:00+00:00"}]}), encoding="utf-8")
check("D4 une entree non-dict est ignoree", len(M.sujets_couverts()) == 1)
check("D5 une note apres corruption repart proprement", M.noter_couverture([_it("Neuf")], post_id="n") == 1)
check("D6 l'ecriture passe par un .tmp qui ne reste pas", not M.chemin_couverture().with_name("couverture.json.tmp").exists())

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
