# -*- coding: utf-8 -*-
"""Tendances locales et signal X borne (plan 2026-09-03 T14, tache #35 du suivi, 30/09/2026).

Aucun reseau : `_lire_x` est remplace par un espion ; le budget du jour ET le quota `x_lecture` sont relus SUR LE
DISQUE du data-dir temporaire. Decision de l'utilisateur : X seulement sur demande, 3 par jour, dans le quota
x_lecture, jamais sans cle. Mesure : un appel lit jusqu'a 10 posts, chacun compte.
Run (depuis backend/) : & $PY tests/test_news_trends.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dznewst_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "outputs").mkdir(exist_ok=True)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.config import settings                                     # noqa: E402
from app.services import news_trends as T, quota                    # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _it(titre, sid, jour="03", doublons=None):
    return {"id": titre[:10] + sid, "title": titre, "source_id": sid, "source_name": f"Media {sid}",
            "published": f"2026-09-{jour}T11:00:00+00:00", "doublons": doublons or []}


A, B, C = ("Solana network hits record daily transactions", "Solana network hits a record in daily transactions",
           "Solana network hits new record in daily transactions")
check("T0 temoin : les trois titres sont presque identiques deux a deux, et le budget vit dans le data-dir",
      all(T.titres_presque_identiques(x, y) for x, y in ((A, B), (A, C))) and str(T.chemin_budget()).startswith(str(_tmp))
      and str(quota._FILE).startswith(str(_tmp)))

print("\n[A] tendances locales")
m = T.marquer_tendances([_it(A, "s1"), _it(B, "s2"), _it(C, "s3"), _it("Storm Bernard floods southern Spain", "s4")])
check("A1 trois medias le meme jour : tendance, 3 sources ; l'autre sujet non", [i["tendance"] for i in m] == [True, True, True, False]
      and all(i["tendance_sources"] == 3 for i in m[:3]) and m[3]["tendance_sources"] == 0, str([(i["tendance"], i["tendance_sources"]) for i in m]))
check("A2 deux medias ne suffisent pas", not any(i["tendance"] for i in T.marquer_tendances([_it(A, "s1"), _it(B, "s2")])))
check("A3 trois articles du MEME media ne font pas une tendance", not any(i["tendance"] for i in T.marquer_tendances([_it(A, "s1"), _it(B, "s1"), _it(C, "s1")])))
check("A4 trois jours differents : un feuilleton, pas une tendance",
      not any(i["tendance"] for i in T.marquer_tendances([_it(A, "s1", "01"), _it(B, "s2", "02"), _it(C, "s3", "03")])))
fondu = _it(A, "s1", doublons=[{"source_name": "Decrypt"}, {"source_name": "The Block"}])
m = T.marquer_tendances([fondu])
check("A5 LE CAS REEL : un article fondu (sa source + 2 doublons) est une tendance a lui seul", m[0]["tendance"] and m[0]["tendance_sources"] == 3, str(m[0]))
fondu2 = _it(A, "s1", doublons=[{"source_name": "media s1"}, {"source_name": "Decrypt"}])
check("A6 un doublon du meme media (casse ignoree) ne compte pas deux fois", T.marquer_tendances([fondu2])[0]["tendance"] is False)
it = _it(A, "s1")
T.marquer_tendances([it])
check("A7 marquer ne mute pas l'entree", "tendance" not in it)
check("A8 liste vide", T.marquer_tendances([]) == [])

print("\n[B] signal X")
lus = []
def espion(n=10, boum=None):
    def f(q):
        lus.append(q)
        if boum:
            raise RuntimeError(boum)
        return {"posts": n}
    T._lire_x = f
cles = (settings.X_API_KEY, settings.X_API_SECRET, settings.X_ACCESS_TOKEN, settings.X_ACCESS_SECRET)
settings.X_API_KEY = settings.X_API_SECRET = settings.X_ACCESS_TOKEN = settings.X_ACCESS_SECRET = ""
from datetime import datetime
SEPT = datetime(2026, 9, 3, 12)
espion()
r = T.signal_x("solana", quand="2026-09-03T12:00:00+00:00")
check("B1 sans cle X : refus lisible, AUCUNE lecture, rien de decompte", r["posts"] is None and "cle X" in r["motif"] and lus == []
      and not T.chemin_budget().is_file() and quota.used("x_lecture", SEPT) == 0, str(r))
settings.X_API_KEY = settings.X_API_SECRET = settings.X_ACCESS_TOKEN = settings.X_ACCESS_SECRET = "k"
r = T.signal_x("solana", quand="2026-09-03T12:00:00+00:00")
budget = json.loads(T.chemin_budget().read_text("utf-8"))
check("B2 un appel : posts lus, jour decompte SUR LE DISQUE, posts comptes dans x_lecture", r["posts"] == 10 and r["restant_jour"] == 2
      and budget == {"2026-09-03": 1} and quota.used("x_lecture", SEPT) == 10 and r["quota"] == "10/100", str(r))
espion(n=0)
T.signal_x("solana", quand="2026-09-03T12:00:00+00:00")
check("B3 zero post rendu : rien de plus au quota, mais l'appel du jour compte", quota.used("x_lecture", SEPT) == 10
      and json.loads(T.chemin_budget().read_text("utf-8"))["2026-09-03"] == 2)
espion(boum="tweepy absent")
r = T.signal_x("solana", quand="2026-09-03T12:00:00+00:00")
check("B4 un lecteur qui leve : refus lisible, l'appel du jour est compte (pas de repetition silencieuse)",
      r["posts"] is None and "tweepy absent" in r["motif"] and r["restant_jour"] == 0, str(r))
espion()
n0 = len(lus)
r = T.signal_x("solana", quand="2026-09-03T12:00:00+00:00")
check("B5 au-dela de 3 appels par jour : refus, aucune lecture", r["posts"] is None and "3 lectures" in r["motif"] and len(lus) == n0, str(r))
r = T.signal_x("solana", quand="2026-09-04T09:00:00+00:00")
check("B6 le lendemain, le jour repart (et seule la journee courante est gardee)", r["posts"] == 10 and r["restant_jour"] == 2
      and list(json.loads(T.chemin_budget().read_text("utf-8"))) == ["2026-09-04"], str(r))
quota.count("x_lecture", SEPT, n=100 - quota.used("x_lecture", SEPT) - 5)        # il reste 5 lectures ce mois
n0 = len(lus)
r = T.signal_x("solana", quand="2026-09-05T09:00:00+00:00")
check("B7 moins de 10 lectures devant soi ce mois : refus nommant x_lecture, aucune lecture",
      r["posts"] is None and "x_lecture" in r["motif"] and "95/100" in r["motif"] and len(lus) == n0, str(r))
check("B8 3 appels x 31 jours depassent les 100 du mois : le quota mensuel est bien la borne qui tient", T.APPELS_PAR_JOUR * 31 * T.POSTS_PAR_APPEL > 100)
settings.X_API_KEY, settings.X_API_SECRET, settings.X_ACCESS_TOKEN, settings.X_ACCESS_SECRET = cles
T.chemin_budget().write_text("{pas du json", encoding="utf-8")
check("B9 budget corrompu : relu vide, pas d'exception", T._lire_budget() == {})

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
