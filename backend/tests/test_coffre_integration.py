# -*- coding: utf-8 -*-
"""Le coffre branché (plan Settings T16 — tâche #20, 29/09/2026) : .env vidé de ses secrets, écran des clés et
Diagnostic qui disent la vérité, écriture au coffre, refus coffre fermé, archive portable, ouverture au lancement,
transfert entre machines qui n'emporte jamais le coffre.
Banc-miroir : après chaque geste, le banc RELIT le .env sur le disque, le fichier coffre.dzk en octets, l'état du
processus (settings) et les réponses JSON. Exige `cryptography`. Zéro réseau (les tests de clé sont remplacés).
Run : & $PY tests/test_coffre_integration.py   (depuis backend/)"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcoffi_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
(_tmp / ".env").write_text("# mes réglages\nFAL_KEY=fal-secret-123\nGEMINI_MODEL=gemini-flash-latest\n"
                           "TELEGRAM_BOT_TOKEN=111:AAA\nTELEGRAM_CHAT_ID=-100999\n", encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import APP_VERSION, settings                        # noqa: E402
from app.services import coffre as C, diagnostic as D, transfert as TR  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


async def _faux_test(nom, valeur):
    return {"ok": True, "message": f"accepté ({nom}, {len(valeur)} car.)"}
D.tester_cle = _faux_test
env = lambda: (_tmp / ".env").read_text(encoding="utf-8")         # noqa: E731
MDP = "un-mot-de-passe-maitre-long"


def cle(liste, nom, champ="key"):
    return next(k for k in liste if k[champ] == nom)


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("\n[0] sans coffre : rien ne change")
    j = c.get("/api/settings/keys").json()
    check("0.1 sans coffre, toute clé vient du .env", cle(j["keys"], "FAL_KEY") == {"key": "FAL_KEY", "set": True,
          "preview": cle(j["keys"], "FAL_KEY")["preview"], "source": "env"} and j["coffre"] == {"pose": False, "ouvert": False}, json.dumps(j["coffre"]))
    r = c.post("/api/settings/keys", json={"name": "GEMINI_MODEL", "value": "gemini-x"}).json()
    check("0.2 set_key sans coffre : .env, « ou: env », comme avant", r["ou"] == "env" and "GEMINI_MODEL=gemini-x" in env(), json.dumps(r))
    c.post("/api/settings/keys", json={"name": "GEMINI_MODEL", "value": "gemini-flash-latest"})

    _vrai = C._aesgcm

    def _sans_roue():
        raise C.CoffreIndisponible("chiffrement indisponible : la bibliothèque « cryptography » manque")
    C._aesgcm = _sans_roue
    r = c.post("/api/reglages/coffre/poser", json={"mot_de_passe": MDP})
    check("0.3 sans la roue cryptography : 503 qui le dit, aucun coffre posé, .env intact",
          r.status_code == 503 and "cryptography" in r.json()["detail"] and not (_tmp / "coffre.dzk").exists()
          and "fal-secret-123" in env(), r.text[:160])
    C._aesgcm = _vrai

    print("\n[1] poser absorbe le .env")
    check("1.1 mot de passe trop court : 400", c.post("/api/reglages/coffre/poser", json={"mot_de_passe": "court"}).status_code == 400)
    r = c.post("/api/reglages/coffre/poser", json={"mot_de_passe": MDP})
    check("1.2 200, seules les clés SECRÈTES sont absorbées", r.status_code == 200 and r.json()["absorbees"] == ["FAL_KEY", "TELEGRAM_BOT_TOKEN"], r.text[:200])
    check("1.3 les secrets ont QUITTÉ le .env en clair", "fal-secret-123" not in env() and "111:AAA" not in env())
    check("1.4 réglages et commentaires restent", "GEMINI_MODEL=gemini-flash-latest" in env() and "TELEGRAM_CHAT_ID=-100999" in env() and "# mes réglages" in env())
    check("1.5 rien de lisible dans le coffre", b"fal-secret-123" not in (_tmp / "coffre.dzk").read_bytes())
    check("1.6 le coffre posé est ouvert et ses clés sont actives", C.ouvert() and settings.FAL_KEY == "fal-secret-123")
    check("1.7 reposer : 409 (écraserait le contenu)", c.post("/api/reglages/coffre/poser", json={"mot_de_passe": MDP}).status_code == 409)

    print("\n[2] l'écran des clés et le Diagnostic disent la vérité")
    k = c.get("/api/settings/keys").json()["keys"]
    check("2.1 coffre ouvert : la clé est définie, source « coffre », aperçu masqué", cle(k, "FAL_KEY")["set"] is True
          and cle(k, "FAL_KEY")["source"] == "coffre" and cle(k, "FAL_KEY")["preview"] and "fal-secret-123" not in json.dumps(k))
    check("2.2 un réglage non secret vient toujours du .env", cle(k, "GEMINI_MODEL")["source"] == "env")
    d = c.get("/api/reglages/diagnostic").json()["cles"]
    check("2.3 le Diagnostic voit la clé du coffre ouvert", cle(d, "FAL_KEY", "cle")["definie"] is True and cle(d, "FAL_KEY", "cle")["source"] == "coffre")
    t = c.post("/api/reglages/diagnostic/cle", json={"nom": "FAL_KEY"}).json()
    check("2.4 « Tester » relit la valeur DANS le coffre", t.get("ok") is True and "14 car." in t.get("message", ""), json.dumps(t))
    c.post("/api/reglages/coffre/fermer")
    k = c.get("/api/settings/keys").json()["keys"]
    check("2.5 coffre fermé : « verrouillé », set None, aucun aperçu", cle(k, "FAL_KEY") == {"key": "FAL_KEY", "set": None, "preview": "", "source": "coffre-verrouille"})
    check("2.6 une clé secrète JAMAIS posée est aussi « verrouillée » (on ne sait pas)", cle(k, "OPENAI_API_KEY")["set"] is None)
    check("2.7 fermé : la clé n'est plus active dans le processus", settings.FAL_KEY == "")
    dd = cle(c.get("/api/reglages/diagnostic").json()["cles"], "FAL_KEY", "cle")
    check("2.8 le Diagnostic dit « verrouillé », pas « absente »", dd["definie"] is None and dd["source"] == "coffre-verrouille")
    check("2.9 tester une clé du coffre fermé : 409 dit", c.post("/api/reglages/diagnostic/cle", json={"nom": "FAL_KEY"}).status_code == 409)

    print("\n[3] écrire")
    r = c.post("/api/settings/keys", json={"name": "MESHY_API_KEY", "value": "msh-42"})
    check("3.1 coffre FERMÉ : un secret est refusé (409), rien n'est écrit en clair", r.status_code == 409 and "msh-42" not in env(), r.text[:160])
    r = c.post("/api/settings/keys", json={"name": "GEMINI_MODEL", "value": "gemini-3"})
    check("3.2 coffre fermé : un réglage non secret s'écrit toujours", r.status_code == 200 and "GEMINI_MODEL=gemini-3" in env())
    check("3.3 mauvais mot de passe : 401", c.post("/api/reglages/coffre/ouvrir", json={"mot_de_passe": "faux"}).status_code == 401)
    r = c.post("/api/reglages/coffre/ouvrir", json={"mot_de_passe": MDP}).json()
    check("3.4 ouvert : 2 clés, réappliquées", r == {"ok": True, "cles": 2} and settings.FAL_KEY == "fal-secret-123", json.dumps(r))
    r = c.post("/api/settings/keys", json={"name": "MESHY_API_KEY", "value": "msh-42", "tester": True}).json()
    check("3.5 coffre ouvert : le secret va AU COFFRE, testé, jamais au .env", r["ou"] == "coffre" and "msh-42" not in env()
          and C.lire_cle("MESHY_API_KEY") == "msh-42" and settings.MESHY_API_KEY == "msh-42" and r["tests"]["MESHY_API_KEY"]["ok"], json.dumps(r))
    r = c.post("/api/settings/keys", json={"entries": [{"name": "OPENAI_API_KEY", "value": "sk-1"}, {"name": "OPENAI_MODEL", "value": "gpt-x"}]}).json()
    check("3.6 mixte : le secret au coffre, le réglage au .env, et c'est dit", r["ou"] == "mixte" and r["au_coffre"] == ["OPENAI_API_KEY"]
          and "sk-1" not in env() and "OPENAI_MODEL=gpt-x" in env(), json.dumps(r))

    print("\n[4] archive portable")
    check("4.1 mot de passe d'archive trop court : 400", c.post("/api/reglages/coffre/archive", json={"mot_de_passe": "x"}).status_code == 400)
    r = c.post("/api/reglages/coffre/archive", json={"mot_de_passe": "phrase-du-telephone"})
    blob = r.content
    check("4.2 octets bruts DZKV1, nom de fichier proposé, jamais en cache", r.status_code == 200 and r.headers["content-type"] == "application/octet-stream"
          and "DeepotusVideoGen-" in r.headers.get("content-disposition", "") and r.headers.get("cache-control") == "no-store" and blob[:6] == b"DZKV1\n")
    check("4.3 rien en clair dans l'archive", b"fal-secret-123" not in blob and b"FAL_KEY" not in blob)
    a = C.dechiffrer(blob, "phrase-du-telephone")
    check("4.4 coffre ET .env : tout ce qu'il faut au second poste", a["genre"] == "archive" and a["cles"]["FAL_KEY"] == "fal-secret-123"
          and a["cles"]["MESHY_API_KEY"] == "msh-42" and a["cles"]["GEMINI_MODEL"] == "gemini-3" and a["cles"]["TELEGRAM_CHAT_ID"] == "-100999", json.dumps(sorted(a["cles"])))
    check("4.5 plafonds, grille, provenance datée et nommée", "plafonds" in a and "pricing" in a and a["app_version"] == APP_VERSION and a["machine"])
    imp = lambda mdp: c.post("/api/reglages/coffre/archive/importer", files={"fichier": ("a.dzk", blob, "application/octet-stream")}, data={"mot_de_passe": mdp})  # noqa: E731
    check("4.6 import : mauvais mot de passe 401", imp("pas-la-bonne").status_code == 401)
    c.post("/api/reglages/coffre/fermer")
    check("4.7 import coffre FERMÉ : 409 (les secrets iraient en clair)", imp("phrase-du-telephone").status_code == 409 and "fal-secret-123" not in env())
    c.post("/api/reglages/coffre/ouvrir", json={"mot_de_passe": MDP})
    C.ecrire_cle("MESHY_API_KEY", "")
    r = imp("phrase-du-telephone").json()
    check("4.8 import coffre ouvert : secrets au coffre, réglages au .env, et c'est dit", "MESHY_API_KEY" in r["au_coffre"] and C.lire_cle("MESHY_API_KEY") == "msh-42"
          and "GEMINI_MODEL" in r["au_env"] and "FAL_KEY" not in r["au_env"] and "msh-42" not in env(), json.dumps(r))
    check("4.9 une archive trop lourde : 413", c.post("/api/reglages/coffre/archive/importer", files={"fichier": ("g.dzk", b"0" * 4_000_001, "application/octet-stream")},
                                                     data={"mot_de_passe": "x"}).status_code == 413)
    check("4.10 un fichier coffre n'est pas une archive : 401", c.post("/api/reglages/coffre/archive/importer",
          files={"fichier": ("c.dzk", (_tmp / "coffre.dzk").read_bytes(), "application/octet-stream")}, data={"mot_de_passe": MDP}).status_code == 401)

    print("\n[5] retenir, lancement, mot de passe")
    check("5.1 retenir : sceau écrit", c.post("/api/reglages/coffre/retenir").status_code == 200 and (_tmp / "coffre.pc").is_file())
    C.fermer()
    check("5.2 au lancement, le coffre s'ouvre seul", C.ouvrir_par_dpapi() is True)
    e = c.get("/api/reglages/coffre/etat").json()
    check("5.3 l'état dit les faits (posé, ouvert, retenu, clés par NOM)", e["pose"] and e["ouvert"] and e["retenu"] and "FAL_KEY" in e["cles"]
          and "fal-secret-123" not in json.dumps(e), json.dumps(e))
    C.fermer()
    with TestClient(app, client=("127.0.0.1", 50001)) as c_boot:          # un VRAI démarrage (lifespan)
        check("5.3b un démarrage de l'application rouvre le coffre retenu, et ses clés sont actives",
              c_boot.get("/api/reglages/coffre/etat").json()["ouvert"] is True and settings.FAL_KEY == "fal-secret-123")
    check("5.4 changer : ancien faux -> 401", c.post("/api/reglages/coffre/mot-de-passe", json={"ancien": "x", "nouveau": "nouveau-long-1"}).status_code == 401)
    r = c.post("/api/reglages/coffre/mot-de-passe", json={"ancien": MDP, "nouveau": "nouveau-long-1"})
    check("5.5 changé : le sceau est désarmé", r.status_code == 200 and not (_tmp / "coffre.pc").exists())
    c.post("/api/reglages/coffre/oublier")

    print("\n[6] le transfert n'emporte JAMAIS le coffre (décision du 29/09)")
    check("6.1 coffre.dzk et coffre.pc sont des secrets pour le transfert", TR.exclu("coffre.dzk")[0] and TR.exclu("coffre.pc")[0]
          and TR.exclu("coffre.dzk.tmp")[0] and TR.exclu("coffre.dzk", {"journaux": True, "rebuts": True})[0])
    rels = [r for r, _t in TR.inventaire()[0]]
    check("6.2 l'inventaire du transfert ne les liste pas", not any(r.startswith("coffre.") for r in rels), str([r for r in rels if "coffre" in r]))

import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E401,E702
import _jeton_appareil as _JA  # noqa: E402 — tache #56 : le reseau local exige un jeton d'appareil (garde exterieure)
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    check("7.1 hors boucle locale : état, ouverture et archive refusés", c2.get("/api/reglages/coffre/etat").status_code == 403
          and c2.post("/api/reglages/coffre/ouvrir", json={"mot_de_passe": MDP}).status_code == 403
          and c2.post("/api/reglages/coffre/archive", json={"mot_de_passe": "phrase-du-telephone"}).status_code == 403)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
