# -*- coding: utf-8 -*-
"""Avatar live G0 (t161, 10/10/2026) — le socle du Direct : clé Decart, Personnage avec consentement, session
gardée par le plafond mensuel et bornée CHEZ Decart (maxSessionDuration), jeton client éphémère, coût réel noté à
la fin. Spec : docs/superpowers/specs/2026-10-10-higgsfield-genjutsu-inventaire.md.

Trois faits relevés le 10/10 dans le SDK @decartai/sdk 0.2.8 et la doc Decart, qui commandent ce fichier :
  - POST https://api.decart.ai/v1/client/tokens, en-tête X-API-KEY, corps {expiresIn, allowedModels,
    constraints.realtime.maxSessionDuration (min 10)}, réponse {apiKey, expiresAt} ;
  - un jeton EXPIRÉ n'arrête PAS une session déjà ouverte : seul maxSessionDuration la borne — c'est donc lui qui
    porte le plafond, jamais le TTL ;
  - Lucy 2.5 se facture 0,02 $/s (0,04 $/s en mode rapide), à la seconde de génération active.

Aucun réseau : le poste HTTP vers Decart est remplacé (avatar_live._poster). Data-dir isolé, aucune clé réelle.
Run (depuis backend/) : & $PY tests/test_avatar_live_socle.py"""
import base64, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzavlive_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("DECART_API_KEY", "FAL_KEY"):
    os.environ.pop(k, None)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def png(w=600, h=600, couleur=(200, 80, 40)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), couleur).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import avatar_live as AL, pricing, plafonds, coffre, appairage   # noqa: E402

APPELS = []


async def faux_poster(url, entetes, corps):
    APPELS.append({"url": url, "entetes": dict(entetes), "corps": json.loads(json.dumps(corps))})
    return 200, {"apiKey": "ek_court_" + "x" * 20, "expiresAt": "2026-10-10T12:00:00Z"}

AL._poster = faux_poster

print("\n[K] la clé Decart est une clé comme les autres")
from app.api import routes as R                                     # noqa: E402
check("K1 DECART_API_KEY dans les réglages, la liste des clés modifiables, le coffre et les consoles de rotation",
      hasattr(settings, "DECART_API_KEY") and "DECART_API_KEY" in R._ALLOWED_ENV_KEYS
      and "DECART_API_KEY" in coffre.SECRETES and any(c["cle"] == "DECART_API_KEY" for c in appairage.CONSOLES))

print("\n[P] le prix du direct")
d = pricing.estimate({"kind": "direct", "seconds": 300})
check("P1 300 s de Lucy 2.5 = 6,00 $ chez decart, à la seconde",
      abs(d["total_usd"] - 6.0) < 1e-6 and d["breakdown"][0]["provider"] == "decart"
      and d["breakdown"][0]["unit"] == "s", str(d))
d = pricing.estimate({"kind": "direct", "seconds": 60, "rapide": True})
check("P2 le mode rapide coûte le double (60 s = 2,40 $)", abs(d["total_usd"] - 2.4) < 1e-6, str(d))
for bad in ({"kind": "direct"}, {"kind": "direct", "seconds": -5}, {"kind": "direct", "seconds": "abc"},
            {"kind": "direct", "seconds": float("nan")}):
    d = pricing.estimate(bad)
    check(f"P3 durée illisible {bad.get('seconds')!r} : devis de la durée PAR DÉFAUT, jamais 0 ni une erreur",
          abs(d["total_usd"] - AL.DUREE_DEFAUT_S * 0.02) < 1e-6, str(d))
check("P4 « direct » est une catégorie de dépense", "direct" in plafonds.CATEGORIES)

LAN = ("192.168.1.42", 50000)
LOC = ("127.0.0.1", 50000)

with TestClient(app, client=LOC, raise_server_exceptions=False) as loc, \
        TestClient(app, client=LAN, raise_server_exceptions=False) as lan:

    print("\n[E] l'état du direct")
    e = loc.get("/api/avatar-live/etat").json()
    check("E1 sans clé : cle=false, modèle lucy-2.5, prix 0,02 $/s, bornes de durée, texte du consentement",
          e.get("cle") is False and e.get("modele") == "lucy-2.5" and e.get("prix_usd_s") == 0.02
          and e.get("duree") == {"min": 10, "max": 1800, "defaut": 300} and "droit" in e.get("consentement", ""), str(e))

    print("\n[C] le Personnage exige le consentement")
    r = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png()]})
    check("C1 sans consentement : 400 qui le dit, rien d'écrit",
          r.status_code == 400 and "consentement" in r.text.lower()
          and loc.get("/api/avatar-live/personnages").json().get("personnages") == [], r.text[:200])
    r = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [], "consentement": True})
    check("C2 aucune image : 400", r.status_code == 400, r.text[:200])
    r = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png()] * 9, "consentement": True})
    check("C3 neuf images : 400 (huit au plus)", r.status_code == 400 and "8" in r.text, r.text[:200])
    r = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [base64.b64encode(b"pas une image").decode()],
                                                       "consentement": True})
    check("C4 des octets qui ne sont pas une image : 415, Pillow décide", r.status_code == 415, r.text[:200])
    r = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png(200, 200)], "consentement": True})
    check("C5 image sous 256 px : 400 qui dit la taille minimale", r.status_code == 400 and "256" in r.text, r.text[:200])
    r = loc.post("/api/avatar-live/personnages", json={
        "nom": "  Oli le clone  ", "images": [png(), png(512, 900, (10, 10, 10))], "consentement": True,
        "voix": {"fournisseur": "elevenlabs", "voice_id": "abc123"}})
    pj = r.json() if r.status_code == 200 else {}
    pid = pj.get("id", "")
    check("C6 créé : id, nom nettoyé, deux images, voix, consentement daté avec son texte et son origine",
          r.status_code == 200 and pid and pj.get("nom") == "Oli le clone" and pj.get("images") == 2
          and pj.get("voix", {}).get("voice_id") == "abc123"
          and pj.get("consentement", {}).get("texte") == AL.TEXTE_CONSENTEMENT
          and pj.get("consentement", {}).get("origine") == "pc" and pj["consentement"].get("le"), r.text[:300])
    fiche = _tmp / "personnages" / pid / "fiche.json"
    check("C7 la fiche vit dans le data-dir, images ré-encodées en PNG à côté",
          fiche.is_file() and (_tmp / "personnages" / pid / "ref_0.png").is_file()
          and (_tmp / "personnages" / pid / "ref_1.png").is_file())
    im = loc.get(f"/api/avatar-live/personnages/{pid}/image/1")
    check("C8 l'image de référence se relit (PNG)", im.status_code == 200 and im.content[:8] == b"\x89PNG\r\n\x1a\n")
    # ..%2F n'atteint pas la route : le routeur la rend au catch-all de l'app (la page, 200 HTML) — relevé le 10/10,
    # comme partout ailleurs (Vectorlab) ; ce qui compte : aucun octet du data-dir ne sort
    piege = loc.get("/api/avatar-live/personnages/..%2F..%2Ft.db/image/0")
    check("C9 index hors bornes ou id piégé : 404, jamais un fichier voisin",
          loc.get(f"/api/avatar-live/personnages/{pid}/image/7").status_code == 404
          and (piege.status_code == 404 or piege.headers.get("content-type", "").startswith("text/html"))
          and b"SQLite format" not in piege.content and piege.content[:8] != b"\x89PNG\r\n\x1a\n"
          and loc.get("/api/avatar-live/personnages/..%5Ct.db").status_code == 404
          and loc.get("/api/avatar-live/personnages/..%5C..%5Ct.db/image/0").status_code == 404)
    check("C10 créer un Personnage depuis le réseau local, même appairé : écriture refusée (403)",
          lan.post("/api/avatar-live/personnages", json={"nom": "x", "images": [png()], "consentement": True},
                   headers={"Authorization": "Bearer " + "0" * 64}).status_code in (401, 403))

    print("\n[S] la session : clé, garde, borne chez Decart")
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 120})
    check("S1 sans clé Decart : 409 qui dit où la poser, aucun appel, aucune dépense",
          r.status_code == 409 and "DECART_API_KEY" in r.text and not APPELS, r.text[:200])
    settings.DECART_API_KEY = "dct_permanente_secrete"
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": "inconnu", "duree_s": 120})
    check("S2 Personnage inconnu : 404, aucun appel", r.status_code == 404 and not APPELS, r.text[:200])
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 120})
    sj = r.json() if r.status_code == 200 else {}
    a = APPELS[-1] if APPELS else {}
    check("S3 ouverte : jeton court rendu, JAMAIS la clé permanente",
          r.status_code == 200 and sj.get("jeton", "").startswith("ek_court_")
          and "dct_permanente_secrete" not in r.text, r.text[:300])
    check("S4 l'appel Decart : bonne URL, X-API-KEY, TTL 60 s, limité à lucy-2.5, maxSessionDuration = durée",
          a.get("url") == "https://api.decart.ai/v1/client/tokens"
          and a.get("entetes", {}).get("X-API-KEY") == "dct_permanente_secrete"
          and a.get("corps", {}).get("expiresIn") == 60 and a.get("corps", {}).get("allowedModels") == ["lucy-2.5"]
          and a.get("corps", {}).get("constraints") == {"realtime": {"maxSessionDuration": 120}}, str(a))
    check("S5 la réponse dit la durée maximale, le prix, le devis, le modèle et l'image du Personnage",
          sj.get("duree_max_s") == 120 and sj.get("prix_usd_s") == 0.02 and abs(sj.get("devis_usd", 0) - 2.4) < 1e-6
          and sj.get("modele") == "lucy-2.5" and sj.get("image_url") == f"/api/avatar-live/personnages/{pid}/image/0",
          str(sj))
    import asyncio                                                   # noqa: E402
    et = asyncio.run(plafonds.tableau())
    lg = [l for l in et["lignes"] if l["moteur"] == "decart"]
    check("S6 le devis ENTIER est réservé au registre, catégorie « direct »",
          len(lg) == 1 and lg[0]["categorie"] == "direct" and abs(lg[0]["estime_usd"] - 2.4) < 1e-6, str(et["lignes"]))
    for duree, attendu in ((5, 10), (99999, 1800), ("x", 300)):
        n = len(APPELS)
        r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": duree})
        check(f"S7 durée {duree!r} bornée à {attendu} s chez Decart",
              r.status_code == 200 and len(APPELS) == n + 1
              and APPELS[-1]["corps"]["constraints"]["realtime"]["maxSessionDuration"] == attendu, r.text[:200])
        loc.post("/api/avatar-live/sessions/fin", json={"session_id": r.json().get("session_id"), "secondes": 0})

    print("\n[F] la fin : le réel remplace le devis")
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": sj.get("session_id"), "secondes": 45})
    check("F1 fin à 45 s : réel 0,90 $", r.status_code == 200 and abs(r.json().get("reel_usd", 0) - 0.9) < 1e-6, r.text[:200])
    et = asyncio.run(plafonds.tableau())
    lg = [l for l in et["lignes"] if l["moteur"] == "decart"][0]
    check("F2 le registre : effectif = réel là où il est connu", abs(lg["reel_usd"] - 0.9) < 1e-6, str(lg))
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": sj.get("session_id"), "secondes": 45})
    check("F3 une seconde fin : 404 (pas de double compte)", r.status_code == 404, r.text[:200])
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60})
    s2 = r.json()
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": s2["session_id"], "secondes": 9999})
    check("F4 des secondes au-delà de la borne : comptées à la borne (60 s = 1,20 $)",
          r.status_code == 200 and abs(r.json().get("reel_usd", 0) - 1.2) < 1e-6, r.text[:200])

    print("\n[G] le plafond mord AVANT Decart")
    plafonds.enregistrer({"par_moteur": {"decart": 5.0}})
    n = len(APPELS)
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 600})
    check("G1 12 $ demandés sous un plafond decart de 5 $ : 402 dz_plafond, AUCUN jeton frappé",
          r.status_code == 402 and "dz_plafond" in r.text and len(APPELS) == n, r.text[:200])
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 600},
                 headers={"X-DZ-Plafond": "confirme"})
    check("G2 rejoué avec la confirmation : ouvert", r.status_code == 200 and len(APPELS) == n + 1, r.text[:200])
    loc.post("/api/avatar-live/sessions/fin", json={"session_id": r.json().get("session_id"), "secondes": 0})
    plafonds.enregistrer({"par_moteur": {}})

    async def poster_en_panne(url, entetes, corps):
        return 401, {"error": "Invalid or expired API key"}   # la forme RELEVÉE sur le vrai Decart le 10/10
    AL._poster = poster_en_panne
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 30})
    et = asyncio.run(plafonds.tableau())
    tot = [l for l in et["lignes"] if l["moteur"] == "decart"][0]
    check("G3 Decart refuse la clé : 502 qui le dit, et la réservation est remise à 0 $ réel (rien consommé)",
          r.status_code == 502 and "decart" in r.text.lower() and "Invalid or expired" in r.text and tot["rapproches"] == tot["tirs"], r.text[:200] + str(tot))
    AL._poster = faux_poster

    print("\n[M] le téléphone appairé")
    jeton, _ = asyncio.run(appairage.reclamer(appairage.creer_secret().secret, "Pixel"))
    H = {"Authorization": "Bearer " + jeton}
    check("M1 sans jeton depuis le Wi-Fi : 401", lan.post("/api/avatar-live/sessions", json={"personnage_id": pid}).status_code == 401)
    check("M2 lecture de l'état et des Personnages avec jeton : 200",
          lan.get("/api/avatar-live/etat", headers=H).status_code == 200
          and len(lan.get("/api/avatar-live/personnages", headers=H).json().get("personnages", [])) == 1)
    r = lan.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60}, headers=H)
    sm = r.json() if r.status_code == 200 else {}
    check("M3 le téléphone ouvre une session (écriture ouverte, garde du plafond la même)",
          r.status_code == 200 and sm.get("jeton", "").startswith("ek_court_"), r.text[:200])
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": sm.get("session_id"), "secondes": 10})
    check("M4 le PC peut clore la session d'un téléphone", r.status_code == 200, r.text[:200])
    r = lan.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60}, headers=H)
    sm = r.json()
    jeton2, _ = asyncio.run(appairage.reclamer(appairage.creer_secret().secret, "Autre"))
    r = lan.post("/api/avatar-live/sessions/fin", json={"session_id": sm["session_id"], "secondes": 10},
                 headers={"Authorization": "Bearer " + jeton2})
    check("M5 un AUTRE appareil ne clôt pas la session d'un téléphone : 404", r.status_code == 404, r.text[:200])
    r = lan.post("/api/avatar-live/sessions/fin", json={"session_id": sm["session_id"], "secondes": 10}, headers=H)
    check("M6 son téléphone la clôt", r.status_code == 200, r.text[:200])

    print("\n[D] suppression")
    check("D1 supprimer depuis le Wi-Fi : refusé", lan.delete(f"/api/avatar-live/personnages/{pid}", headers=H).status_code == 403)
    r = loc.delete(f"/api/avatar-live/personnages/{pid}")
    check("D2 supprimé du PC : dossier parti, liste vide",
          r.status_code == 200 and not (_tmp / "personnages" / pid).exists()
          and loc.get("/api/avatar-live/personnages").json().get("personnages") == [], r.text[:200])

print("\n[R] recensement des routes payantes")
import _recensement_payant as RP                                    # noqa: E402
check("R1 le recensement couvre le module du Direct et y voit la garde", "avatar_live" in RP.MODULES)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
