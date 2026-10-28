# -*- coding: utf-8 -*-
# Backend de PREUVE du guide pour les collectes Apify (28/10/2026, chapitre « prospection ») : code de ce dépôt, python
# embarqué, dossier de données jetable, port 8819 (jamais le 8765), AUCUNE dépense :
#   - clé Apify FACTICE au .env de démonstration (la ligne Apify des Clés d'API est « posée », rien n'est appelé) ;
#   - `apify.devis` et `apify.lancer` remplacés : devis fixe, run SIMULÉ qui rend des studios de démonstration ;
#   - espace « Marque Démo », une conversation Campagnes à id fixe (CID) avec sa carte « collecte » Google Maps,
#     une veille de démonstration et le volet « Ce que font les concurrents » (pubs, page prix changée, positions).
# Les noms, sites et textes sont INVENTÉS pour la démonstration (domaines en .example).
import asyncio
import os
import pathlib
import sys
import tempfile

PORT = int(os.environ.get("PORT", "8819"))
CID = "a0a0a0a0-0000-4000-8000-000000000365"
WT = pathlib.Path(__file__).resolve().parents[2] / "backend"
d = pathlib.Path(tempfile.mkdtemp(prefix="dzguide_apify_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(d)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(d / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(d / "images")
os.environ["OUTPUTS_FOLDER"] = str(d / "outputs")
for k in ("FAL_KEY", "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MESHY_API_KEY",
          "GEMINI_API_KEY", "FIGMA_TOKEN", "TELEGRAM_BOT_TOKEN", "APIFY_TOKEN"):
    os.environ.pop(k, None)
(d / "images").mkdir(parents=True, exist_ok=True)
(d / ".env").write_text("APIFY_TOKEN=apify_api_DEMOguide000000000000000000000\n", encoding="utf-8")
sys.path.insert(0, str(WT))
os.chdir(WT)
print("donnees de preuve :", d, flush=True)

from app.services import apify as AP, agent_format as fmt, agent_store as st, espaces as E  # noqa: E402
from app.services import veille as V, veille_collecte as VC, veille_concurrents as VK      # noqa: E402

LIEUX = [
    {"title": "Studio Lumière Croix-Rousse", "website": "https://studio-lumiere.example/", "totalScore": 4.8,
     "categoryName": "Studio de production vidéo", "city": "Lyon"},
    {"title": "Atelier Saône Films", "website": "https://saone-films.example/", "totalScore": 4.6,
     "categoryName": "Société de production", "city": "Lyon"},
    {"title": "Quai 9 Vidéo", "website": "https://quai9.example/", "totalScore": 4.4,
     "categoryName": "Studio de production vidéo", "city": "Villeurbanne"},
    {"title": "Motion Rhône", "totalScore": 4.1, "categoryName": "Agence de motion design", "city": "Lyon"},
]


async def faux_devis(cle, n, entree=None):
    return round(0.004 * AP.volume(cle, entree, n) + 0.00005, 4)


async def faux_lancer(cle, entree, n, plafond=None):
    await asyncio.sleep(1.2)
    return {"items": LIEUX, "cout_usd": 0.017, "statut": "SUCCEEDED", "partiel": False, "run_id": "DEMO",
            "devis_usd": await faux_devis(cle, n, entree)}


AP.devis = faux_devis
AP.lancer = faux_lancer
AP._GET = None          # garde-fou : aucun appel réel possible
AP._POST = None

eid = E.creer({"nom": "Marque Démo"})["id"]


CID_EN = "a0a0a0a0-0000-4000-8000-000000000366"     # la scène anglaise décide SA carte (une carte ne se décide qu'une fois)
TEXTES = {CID: ("Trouve des studios vidéo à Lyon sur Google Maps, 50 au plus.",
                "Je propose une collecte Google Maps : 50 lieux au plus, payante, plafonnée à 1 $. Rien ne part avant "
                "votre accord."),
          CID_EN: ("Find video studios in Lyon on Google Maps, 50 at most.",
                   "I suggest a Google Maps collection: 50 places at most, paid, capped at $1. Nothing runs before you "
                   "agree.")}


async def semer():
    from app.services.storage import init_db
    await init_db()
    for cid, (question, reponse) in TEXTES.items():
        await st.creer("campagnes", eid, "Studios vidéo à Lyon", id=cid)
        carte = await AP.carte_collecte("google_maps", {"searchStringsArray": ["studio vidéo"], "locationQuery": "Lyon",
                                                        "language": "fr"}, 50, but="leads")
        await st.ajouter(cid, [fmt.nouveau_message("utilisateur", [{"type": "texte", "texte": question}]),
                               fmt.nouveau_message("agent", [{"type": "texte", "texte": reponse}, carte])])


asyncio.run(semer())

p = V.perimetre(eid)
for c in p["concurrents"]:
    c["domaine"] = {"runway": "runwayml.example", "capcut": "capcut.example", "kling": "kling.example"}.get(c["id"], "")
p["mots_cles"] = ["générateur vidéo ia", "vidéo produit ia"]
V.poser_perimetre(eid, p)
J = "2026-10-20"
V.ajouter_brut(eid, "reddit", "runway", [
    VC._ligne("runway", "reddit", f"https://reddit.example/r/vfx/{i}", J, f"demo{i}", t, 3, "runway")
    for i, t in enumerate(["Runway credits burn too fast for client work, looking for an alternative",
                           "Gen-4 motion is great but the price per second is too high",
                           "Support never answered my refund request", "Love the new camera controls"])])
VK.noter_pubs(eid, "runway", [
    {"snapshot": {"body": {"text": "Gen-4 : vos images prennent vie. Essai gratuit."}}, "startDateFormatted": "2026-10-12",
     "publisherPlatform": ["FACEBOOK", "INSTAGRAM"], "isActive": True, "url": "https://ads.example/runway/1"},
    {"snapshot": {"body": {"text": "Studios : un forfait équipe à prix fixe."}}, "startDateFormatted": "2026-10-20",
     "publisherPlatform": ["INSTAGRAM"], "isActive": True, "url": "https://ads.example/runway/2"}])
VK.noter_serp(eid, [{"searchQuery": {"term": "générateur vidéo ia"}, "organicResults": [
    {"position": 1, "url": "https://capcut.example/ia"}, {"position": 4, "url": "https://runwayml.example/gen4"}]},
    {"searchQuery": {"term": "vidéo produit ia"}, "organicResults": [{"position": 2, "url": "https://blog.example/x"}]}])
VK._ecrire(VK._dossier(eid) / "pages.json", {"le": "2026-10-28T10:00:00+00:00", "pages": [
    {"concurrent": "runway", "url": "https://runwayml.example/pricing", "change": True,
     "diff": "--- avant\n+++ maintenant\n-Standard 12 $ / mois\n+Standard 15 $ / mois\n Pro 28 $ / mois"}]})
print("espace de démonstration :", eid, "conversation :", CID, flush=True)

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, log_level="warning")
