# -*- coding: utf-8 -*-
"""t315 (28/10/2026) (D1, tâche 1) — banc du service des sessions de capture (app/services/capture.py).
Plan docs/superpowers/plans/2026-10-28-t315-capture.md, spec boîte à outils §8.1-8.3.
Sections :
  1. créer : dossier et session.json (en_cours), options relues (mode, drapeaux, forme) ;
  2. morceaux : dans l'ordre seulement (409 hors ordre, rien d'écrit), MIME par piste (415), poids (413), piste
     inconnue (400), format changé (409), session close (409), identifiant hors motif (400, jamais sur le disque) ;
  3. piste des clics : liste blanche (champ `value` et type « touche » retirés), textes bornés, chemins et noms de
     fichier vidés, caractères de contrôle ôtés, coordonnées bornées, zone secrète sans libellé, tri par t, borne
     de 20 000 ;
  4. identité : un libellé du catalogue de « Demander » donne sa fiche (écran du clic), un inconnu donne None ;
  5. clôture : <id>.dzclics.json écrit, générations fusionnées dans l'ordre, état terminee, seconde clôture 409 ;
     abandon : pistes effacées ; copie de la scène (409 sans image).
Données jetables (DEEPOTUS_DATA_DIR temporaire), aucun réseau.
Run (depuis backend/) : & $PY tests/test_capture_service.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcap_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


def refus(f, statut):
    try:
        f()
    except C.RefusCapture as e:
        return e.statut == statut
    return False


from app.services import capture as C                               # noqa: E402
from app.services import agent_aide                                  # noqa: E402

print("[1] créer")
s = C.creer({"mode": "onglet", "camera": True, "forme": "vif", "inconnu": 1, "voix": "oui"})
d = C.racine() / s["id"]
check("1.1 id de 16 hexadécimaux, dossier sous DATA_ROOT/captures", C.ID.match(s["id"]) and d.is_dir()
      and str(d).startswith(str(_tmp)))
check("1.2 session.json en_cours, sans piste", json.loads((d / "session.json").read_text("utf-8"))["etat"] == "en_cours"
      and s["pistes"] == {})
check("1.3 options relues : mode, forme, booléens stricts, clé inconnue ignorée",
      s["options"]["mode"] == "onglet" and s["options"]["forme"] == "vif" and s["options"]["camera"] is True
      and s["options"]["voix"] is True and "inconnu" not in s["options"], s["options"])
check("1.4 options illisibles -> défauts prudents (app, caméra éteinte)",
      C.options_lues("x") == C.options_lues({}) and C.options_lues({})["mode"] == "app"
      and C.options_lues({})["camera"] is False)

print("[2] morceaux")
cid = s["id"]
r0 = C.ajouter_morceau(cid, "scene", 0, b"AAAA", "video/webm;codecs=vp9,opus")
check("2.1 morceau 0 accepté", r0 == {"piste": "scene", "recu": 0, "octets": 4}, r0)
check("2.2 morceau hors ordre (2 au lieu de 1) : 409, rien d'écrit",
      refus(lambda: C.ajouter_morceau(cid, "scene", 2, b"ZZ", "video/webm"), 409)
      and (d / "scene.webm").read_bytes() == b"AAAA")
check("2.3 rejouer le morceau 0 : 409", refus(lambda: C.ajouter_morceau(cid, "scene", 0, b"AAAA", "video/webm"), 409))
C.ajouter_morceau(cid, "scene", 1, b"BB", "video/webm")
check("2.4 les morceaux se suivent dans l'ordre", (d / "scene.webm").read_bytes() == b"AAAABB")
check("2.5 format changé en cours : 409", refus(lambda: C.ajouter_morceau(cid, "scene", 2, b"C", "video/mp4"), 409))
check("2.6 voix en vidéo : 415", refus(lambda: C.ajouter_morceau(cid, "voix", 0, b"C", "video/webm"), 415))
check("2.7 écran en audio : 415", refus(lambda: C.ajouter_morceau(cid, "ecran", 0, b"C", "audio/webm"), 415))
check("2.8 MIME inconnu : 415", refus(lambda: C.ajouter_morceau(cid, "ecran", 0, b"C", "text/html"), 415))
check("2.9 piste inconnue : 400", refus(lambda: C.ajouter_morceau(cid, "clavier", 0, b"C", "video/webm"), 400))
check("2.10 morceau trop lourd : 413", refus(lambda: C.ajouter_morceau(cid, "ecran", 0, b"x" * (C.MAX_MORCEAU + 1),
                                                                         "video/webm"), 413))
check("2.11 identifiant hors motif : 400, jamais un chemin", refus(lambda: C.ajouter_morceau("../../x", "scene", 0, b"",
                                                                                          "video/webm"), 400)
      and refus(lambda: C.lire("ABCDEF0123456789"), 400))
check("2.12 capture inconnue : 404", refus(lambda: C.lire("0123456789abcdef"), 404))
C.ajouter_morceau(cid, "voix", 0, b"V", "audio/webm;codecs=opus")
check("2.13 piste voix en audio/webm -> voix.webm", (d / "voix.webm").read_bytes() == b"V"
      and C.chemin_piste(cid, "voix") == d / "voix.webm")
check("2.14 piste absente -> None", C.chemin_piste(cid, "camera") is None)
ancien, C.MAX_PISTE = C.MAX_PISTE, 7
check("2.15 piste trop longue : 413", refus(lambda: C.ajouter_morceau(cid, "scene", 2, b"CC", "video/webm"), 413))
C.MAX_PISTE = ancien

print("[3] piste des clics")
fiche = agent_aide.catalogue()["reglages.coffre.poser"]          # « Poser le coffre » / « Set up vault », écran settings
doc = {"evenements": [
    {"type": "clic", "t": 900, "x": 0.5, "y": 1.7, "bouton": 0, "ecran": "settings", "value": "motdepasse",
     "cible": {"balise": "BUTTON", "role": "", "t": "Set up vault", "i": "", "value": "secret"}},
    {"type": "touche", "t": 100, "cle": "a"},
    {"type": "clic", "t": 50, "x": -3, "y": 0.2, "bouton": 7, "ecran": "../etc",
     "cible": {"balise": "a b", "t": "C:\\Users\\olivi\\cle.txt", "i": "rapport.pdf"}},
    {"type": "clic", "t": 300, "x": 0.1, "y": 0.1, "secret": True, "ecran": "settings",
     "cible": {"balise": "input", "t": "sk-ant-xxx", "i": "Coller la clé"}},
    {"type": "ecran", "t": 10, "ecran": "settings"},
    {"type": "clic", "t": "x", "x": 0.1, "y": 0.1},
    {"type": "clic", "t": 20, "x": 0.1, "y": 0.1, "cible": {"t": "a\u202eb\u0000c" + "z" * 80, "i": "  libre   texte "}},
    "pas un objet",
]}
ev = C.nettoyer_clics(doc, 1000)
check("3.1 types gardés : clic et ecran seulement (touche retirée), t illisible retiré",
      [e["type"] for e in ev] == ["ecran", "clic", "clic", "clic", "clic"], ev)
check("3.2 triés par t", [e["t"] for e in ev] == sorted(e["t"] for e in ev))
tout = json.dumps(ev, ensure_ascii=False)
check("3.3 aucune valeur saisie, aucune touche, aucun chemin, aucun nom de fichier",
      all(m not in tout for m in ("motdepasse", "\"value\"", "cle.txt", "rapport.pdf", "Users", "touche", "sk-ant")), tout)
c900 = next(e for e in ev if e["t"] == 900)
check("3.4 champs du clic en liste blanche, y borné à 1, balise en minuscules",
      set(c900) == {"type", "t", "x", "y", "bouton", "ecran", "cible"} and c900["y"] == 1.0
      and c900["cible"] == {"balise": "button", "role": "", "t": "Set up vault", "i": ""}, c900)
c50 = next(e for e in ev if e["t"] == 50)
check("3.5 x borné à 0, bouton inconnu -> 0, écran hors motif vidé, balise invalide vidée",
      c50["x"] == 0.0 and c50["bouton"] == 0 and c50["ecran"] == "" and c50["cible"]["balise"] == "", c50)
c300 = next(e for e in ev if e["t"] == 300)
check("3.6 zone secrète : secret true, ni libellé ni infobulle", c300.get("secret") is True
      and c300["cible"]["t"] == "" and c300["cible"]["i"] == "", c300)
c20 = next(e for e in ev if e["t"] == 20)
check("3.7 contrôle/format Unicode ôtés, libellé ≤ 40, infobulle aux espaces réduits",
      c20["cible"]["t"].startswith("abc") and len(c20["cible"]["t"]) == 40 and c20["cible"]["i"] == "libre texte", c20)
check("3.8 t au-delà de la durée + 5 s borné", C.nettoyer_clics({"evenements": [{"type": "ecran", "t": 10 ** 9,
                                                                                    "ecran": "quick"}]}, 1000)[0]["t"] == 6000)
check("3.9 borne de 20 000 événements", len(C.nettoyer_clics({"evenements": [{"type": "ecran", "t": 1, "ecran": "q"}]
                                                                    * 25000}, 10)) == C.MAX_EVENEMENTS)
check("3.10 document illisible -> liste vide", C.nettoyer_clics("x", 0) == [] and C.nettoyer_clics({"evenements": 3}, 0) == [])

print("[4] identité par le catalogue")
idf = C.identifier([dict(c900)])
check("4.1 « Set up vault » (anglais) cliqué sur Réglages -> la fiche reglages.coffre.poser", idf[0]["fiche"] == fiche["id"], (idf, fiche["id"]))
check("4.2 libellé inconnu -> None ; zone secrète -> None",
      C.identifier([{"type": "clic", "ecran": "quick", "cible": {"t": "zzz inconnu qqq", "i": ""}}])[0]["fiche"] is None
      and C.identifier([dict(c300)])[0]["fiche"] is None)

print("[5] clôture, abandon, scène")
gens = [{"type": "generation_debut", "t": 400, "job_id": "j1", "provider": "fal"}]
r = C.clore(cid, doc, 1000, {"largeur": 1280.7, "hauteur": "x"}, gens)
f = d / f"{cid}.dzclics.json"
lu = json.loads(f.read_text("utf-8")) if f.is_file() else {}
check("5.1 <id>.dzclics.json écrit (version 1, id, cadre, mode)", lu.get("version") == 1 and lu.get("id") == cid
      and lu.get("cadre") == {"largeur": 1280, "hauteur": 0, "mode": "onglet"} and lu.get("duree_ms") == 1000, lu)
check("5.2 générations fusionnées dans l'ordre de t", [e["t"] for e in lu["evenements"]] == sorted(e["t"] for e in lu["evenements"])
      and any(e["type"] == "generation_debut" for e in lu["evenements"]))
check("5.3 fiche posée sur chaque clic", all("fiche" in e for e in lu["evenements"] if e["type"] == "clic"))
check("5.4 état terminee, seconde clôture 409, morceau après clôture 409",
      C.lire(cid)["session"]["etat"] == "terminee" and refus(lambda: C.clore(cid, doc, 1, {}), 409)
      and refus(lambda: C.ajouter_morceau(cid, "scene", 2, b"C", "video/webm"), 409))
dest = C.copier_scene(cid, _tmp / "sortie")
check("5.5 scène copiée : capture_<date>_<id>.webm, mêmes octets", dest.name.startswith("capture_") and dest.name.endswith(
    f"_{cid}.webm") and dest.read_bytes() == b"AAAABB", dest)
s2 = C.creer({})
check("5.6 scène vide : 409", refus(lambda: C.copier_scene(s2["id"], _tmp / "sortie"), 409))
C.ajouter_morceau(s2["id"], "ecran", 0, b"E", "video/webm")
a = C.abandonner(s2["id"])
check("5.7 abandon : état abandonnee, pistes effacées, session.json gardé",
      a["etat"] == "abandonnee" and sorted(p.name for p in (C.racine() / s2["id"]).iterdir()) == ["session.json"])
check("5.8 abandon d'une session close : 409", refus(lambda: C.abandonner(cid), 409))

print("[6] revue finale (I1) : clôture réservée")
s3 = C.creer({})
C.ajouter_morceau(s3["id"], "scene", 0, b"S", "video/webm")
C.reserver(s3["id"])
check("6.1 seconde réservation concurrente : 409", refus(lambda: C.reserver(s3["id"]), 409))
check("6.2 aucun morceau pendant la clôture : 409", refus(lambda: C.ajouter_morceau(s3["id"], "scene", 1, b"S", "video/webm"), 409))
check("6.3 abandon pendant la clôture : 409", refus(lambda: C.abandonner(s3["id"]), 409))
C.liberer(s3["id"])
check("6.4 libérer rend en_cours", C.lire(s3["id"])["session"]["etat"] == "en_cours")
C.reserver(s3["id"])
check("6.5 clore une session réservée", C.clore(s3["id"], {}, 10)["session"]["etat"] == "terminee")
C.liberer(s3["id"])
check("6.6 libérer une session close ne la rouvre pas", C.lire(s3["id"])["session"]["etat"] == "terminee")

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
