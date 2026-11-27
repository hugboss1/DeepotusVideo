# -*- coding: utf-8 -*-
"""26/11/2026 (avant le nouvel installateur) — le relevé WhatsApp reprend l'arriéré après une coupure (cahier des charges
§6.2 : les messages reçus PC éteint sont « relus dans l'ordre »). Aucun réseau : `whatsapp_echanges.lire` est simulé.
  P1  compte jamais relevé : seuls les entrants des 10 dernières minutes sont neufs ; le marqueur est RANGÉ (whatsapp.json)
  P2  redémarrage (marqueur en mémoire perdu) : l'arriéré depuis le marqueur rangé est relu, dans l'ordre, sans doublon
  P3  coupure de plus de 7 jours : la reprise est bornée à 7 jours
  P4  même seconde que le marqueur : un entrant déjà vu n'est jamais rendu deux fois
  P5  l'agent ne rédige que pour un contact dont le dernier entrant a moins de 24 h ; le crochet de validation voit tout
Run (depuis backend/) : & $PY tests/test_whatsapp_releve_reprise.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwarep_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["KAPSO_API_KEY"] = ""
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from datetime import datetime, timedelta, timezone                  # noqa: E402
from app.services import comptes as CP, espaces as E, whatsapp as WA, whatsapp_echanges as WE  # noqa: E402
from app.services import whatsapp_releve as WR                      # noqa: E402

E.lire()
eid = E.creer({"nom": "Boulangerie Lune"})["id"]
cid = CP.creer({"espace_id": eid, "plateforme": "whatsapp"})["id"]
CP.poser_publics_serveur(cid, {"WHATSAPP_PHONE_ID": "PN-1", "WHATSAPP_WABA_ID": "WABA-1"})
NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
MSGS: list = []
DEPUIS: list = []


async def faux_lire(c, depuis=None, apres=None):
    DEPUIS.append(depuis)
    d = datetime.fromisoformat(depuis) if depuis else None
    return {"messages": [m for m in MSGS if d is None or datetime.fromisoformat(m["quand"]) >= d], "suivant": None}
WE.lire = faux_lire


def entrant(i, quand, qui="tel:33600000001"):
    return {"id": f"wamid.{i}", "identite": qui, "sens": "entrant", "type": "text", "texte": "x",
            "quand": quand.isoformat(timespec="seconds")}


def lire(marqueur, now):
    return [m["id"] for m in asyncio.run(WR._lire_neufs(cid, marqueur, now, eid))]


print("[P] reprise")
MSGS[:] = [entrant(1, NOW - timedelta(hours=2)), entrant(2, NOW - timedelta(minutes=5))]
check("P1a jamais relevé : seuls les 10 dernières minutes", lire({}, NOW) == ["wamid.2"])
r = WA._lire_doc(eid).get(WR.CLE_RELEVE, {}).get(cid) or {}
check("P1b marqueur rangé dans whatsapp.json", r.get("quand") == (NOW - timedelta(minutes=5)).isoformat(timespec="seconds")
      and "wamid.2" in r.get("vus", []), str(r))

PLUS_TARD = NOW + timedelta(hours=8)                                 # le PC a été éteint 8 h
MSGS += [entrant(3, NOW + timedelta(hours=1)), entrant(4, NOW + timedelta(hours=3), "tel:33600000002"),
         entrant(5, NOW + timedelta(hours=7))]
check("P2 redémarrage : l'arriéré relu dans l'ordre depuis le marqueur rangé, sans le déjà-vu",
      lire({}, PLUS_TARD) == ["wamid.3", "wamid.4", "wamid.5"])
check("P2b tour suivant (mémoire) : rien de neuf", lire({cid: (NOW + timedelta(hours=7)).isoformat(timespec="seconds"),
                                                         WR._VUS: {cid: ["wamid.5"]}}, PLUS_TARD) == [])

TRES_TARD = NOW + timedelta(days=20)
MSGS += [entrant(6, NOW + timedelta(days=10)), entrant(7, NOW + timedelta(days=19))]
DEPUIS.clear()
ids = lire({}, TRES_TARD)
check("P3 coupure de 20 jours : reprise bornée à 7 jours", ids == ["wamid.7"]
      and DEPUIS[0] == (TRES_TARD - WR.RATTRAPAGE).isoformat(timespec="seconds"), f"{ids} {DEPUIS[:1]}")

MSGS[:] = [entrant(8, TRES_TARD), entrant(9, TRES_TARD)]
premier = lire({}, TRES_TARD + timedelta(minutes=1))
second = lire({}, TRES_TARD + timedelta(minutes=2))                  # nouveau redémarrage, même seconde de marqueur
check("P4 même seconde : jamais rendu deux fois", premier == ["wamid.8", "wamid.9"] and second == [], f"{premier} {second}")

print("\n[A] agent et arriéré")
traites = []


async def faux_traiter(c, e, p, agent, cle, groupe, ms, now, haut=None):
    traites.append(cle)
    return False
WR._traiter_contact = faux_traiter
vieux = entrant(10, PLUS_TARD - timedelta(hours=30), "tel:33600000003")
recent = entrant(11, PLUS_TARD - timedelta(hours=2), "tel:33600000004")
rapport = {"comptes": 0, "neufs": 0, "envoyes": 0, "erreurs": 0}
asyncio.run(WR._agent_compte(cid, eid, "PN-1", WA.reglages(eid)["agent"], [vieux, recent], PLUS_TARD, rapport))
check("P5 l'agent ne rédige que pour le contact récent (< 24 h)", len(traites) == 1 and "33600000004" in traites[0], str(traites))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
