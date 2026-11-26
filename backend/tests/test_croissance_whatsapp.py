# -*- coding: utf-8 -*-
"""t502 (G12, 26/11/2026) — banc de WhatsApp dans la boucle de croissance (`whatsapp_suivi`).

Sections :
  1. note dans la validation : bloc_note FR/EN (note, trois remarques, temps mm:ss), sans note -> None, brief illisible ;
  2. lien suivi : code stable de 8 caractères, wa.me avec le texte et la référence, code rangé dans l'espace, numéro
     invalide refusé (message traduit), route POST /api/schedule/{id}/lien-whatsapp (locale, 404 post inconnu) ;
  3. entrant : un message qui porte le code note l'ORIGINE (code + date, jamais le texte) ; un STOP ne la note pas ;
     prospects_sources.whatsapp_entrants rend origine_post ;
  4. textes du bilan et de l'alerte (purs, FR/EN) ; aucun envoi n'est branché.
Run (depuis backend/) : & $PY tests/test_croissance_whatsapp.py"""
import json, os, pathlib, sys, tempfile, uuid
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzg12_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import whatsapp_suivi as WS, espaces as E, whatsapp as WA, prospects_sources as PS   # noqa: E402
from urllib.parse import unquote                                    # noqa: E402

NOTE = {"note_rendu": {"note": 72, "libelle": "estimation", "remarques": [
    {"code": "plan_long", "t": 65.0, "secondes": 6.2}, {"code": "debit_lent", "t": 0, "mpm": 120},
    {"code": "sans_soustitres", "t": 0}, {"code": "long", "t": 0, "secondes": 70}]}}


def run():
    print("[1] note dans la validation")
    b = WS.bloc_note(json.dumps(NOTE), "fr")
    check("1a FR : note et trois remarques, temps mm:ss", b.splitlines()[0] == "Note avant publication (estimation) : 72/100"
          and "- image figée 6.2 s à 1:05" in b and len(b.splitlines()) == 4, b)
    check("1b EN", WS.bloc_note(NOTE, "en").startswith("Pre-publish score (estimate): 72/100"))
    check("1c sans note -> None ; brief illisible -> None", WS.bloc_note("{}") is None and WS.bloc_note("{pas json") is None
          and WS.bloc_note(None) is None)
    print("[2] lien suivi")
    A = E.creer({"nom": "Studio G12"})["id"]
    pid = str(uuid.uuid4())
    c = WS.code_post(pid)
    check("2a code stable de 8 caractères", c == WS.code_post(pid) and len(c) == 8 and c.isalnum() and c.upper() == c)
    l = WS.lien(A, "+33 6 12 34 56 78", pid, "Je veux la démo", "fr")
    check("2b wa.me, numéro en chiffres, texte et référence", l["lien"].startswith("https://wa.me/33612345678?text=")
          and unquote(l["lien"].split("text=")[1]) == f"Je veux la démo réf. #P{c}", l)
    check("2c code rangé dans l'espace -> post", WS.post_du_code(A, c) == pid and WS.post_du_code(A, "ZZZZZZZZ") is None)
    try:
        WS.lien(A, "12", pid); check("2d numéro invalide refusé", False)
    except ValueError as e:
        check("2d numéro invalide refusé", "invalide" in str(e))
    check("2e extraire_code : casse indifférente, absent -> None", WS.extraire_code(f"bonjour réf. #p{c.lower()} !") == c
          and WS.extraire_code("bonjour") is None)
    print("[3] entrant")
    etat = {"accords": {}, "stops": {}, "desinscrits_marketing": {}, "compteur": {}, "alias": {}, "journal": []}
    sauve = (WA._noter, WA._PROSPECT_ENTRANT, WA._stop_au_registre)
    WA._noter = lambda cid, geste: geste(etat)
    WA._PROSPECT_ENTRANT = lambda cid, groupe: None
    WA._stop_au_registre = lambda cid, i: None
    try:
        ident = WA.noter_entrant("cpt", {"from": "33611111111", "type": "text", "text": {"body": f"Salut réf. #P{c}"}, "id": "m1"})
        o = etat.get("origines", {}).get(ident)
        check("3a origine notée : code et date, jamais le texte", o and o["code"] == c and "Salut" not in json.dumps(etat), etat.get("origines"))
        WA.noter_entrant("cpt", {"from": "33622222222", "type": "text", "text": {"body": "STOP"}, "id": "m2"})
        check("3b un STOP ne note pas d'origine (et reste un STOP)", "tel:33622222222" not in etat["origines"]
              and "tel:33622222222" in etat["stops"], etat["origines"])
        WA.noter_entrant("cpt", {"from": "33611111111", "type": "text", "text": {"body": "#PAAAAAAAA"}, "id": "m3"})
        check("3c la première origine est gardée", etat["origines"][ident]["code"] == c)
    finally:
        WA._noter, WA._PROSPECT_ENTRANT, WA._stop_au_registre = sauve
    E.chemin(A, "whatsapp.json").write_text(json.dumps({"etat": {"cpt": etat}}), encoding="utf-8")
    r = PS.whatsapp_entrants(A)
    check("3d prospects : origine_post rendue", [x.get("origine_post") for x in r if x["identite"] == ident] == [pid], r)
    print("[4] bilan et alerte")
    t = {"totaux": {"posts": 5, "views": 1200, "engagement": 80}, "gagnants": [{}, {}]}
    check("4a bilan FR", WS.texte_bilan(t) == "Bilan de la semaine : 5 post(s), 1200 vues, 80 interactions ; 2 gagnant(s).", WS.texte_bilan(t))
    check("4b alerte EN", WS.texte_alerte("Pay once", 3.0, "en") == "Winner spotted: “Pay once” is at 3× your usual. Worth recycling?")
    import inspect
    check("4c aucun envoi branché dans le module (attente de la décision)", "envoyer(" not in inspect.getsource(WS))
    print("[2f] route")
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import ScheduledPost, async_session_factory
    from datetime import datetime

    async def poser():
        async with async_session_factory() as s:
            s.add(ScheduledPost(id=pid, title="t", run_at=datetime.utcnow(), espace_id=A))
            await s.commit()
    with TestClient(app, client=("127.0.0.1", 50000)) as client, TestClient(app, client=("192.168.1.20", 50000)) as dehors:
        client.portal.call(poser)
        r = client.post(f"/api/schedule/{pid}/lien-whatsapp", json={"numero": "33612345678", "texte": "Démo"})
        check("2f route : 200, lien et code", r.status_code == 200 and r.json()["code"] == c, r.text[:200])
        r = client.post("/api/schedule/inconnu/lien-whatsapp", json={"numero": "33612345678"})
        check("2g post inconnu -> 404", r.status_code == 404, r.status_code)
        r = client.post(f"/api/schedule/{pid}/lien-whatsapp", json={"numero": "1"}, headers={"Accept-Language": "en"})
        check("2h numéro invalide -> 400 traduit", r.status_code == 400 and "Invalid WhatsApp number" in r.text, r.text[:200])
        r = dehors.post(f"/api/schedule/{pid}/lien-whatsapp", json={"numero": "33612345678"})
        check("2i hors machine -> 401 ou 403", r.status_code in (401, 403), r.status_code)


def test_croissance_whatsapp():
    run()
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    run()
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
