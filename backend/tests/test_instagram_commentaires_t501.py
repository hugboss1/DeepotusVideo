# -*- coding: utf-8 -*-
"""t501 (G11, 26/11/2026) — Instagram : commentaires d'un post, mot-clé d'appel, brouillons de réponse PUBLIQUE.

Codé SANS RIEN CONNECTER (décision D7 « pas maintenant ») : aucun appel réel à Meta, aucun appel réel à Claude. Chaque
appel Graph passe par un faux client HTTP qui les relève ; Claude par un faux `tirer_garde`.
Décision de l'utilisateur (26/11) : réponse PUBLIQUE SEULEMENT, jamais de message privé (ni en masse, ni à l'unité).

[1] aucun message privé : ni route, ni fonction, ni adresse /messages, ni permission de messagerie
[2] rien sans jeton : 409 clair, aucun appel ; rien pour un post non publié ou sans mot-clé
[3] relevé : pages, champs sans pseudo, masqués ignorés, casse et accents, mot entier, compteur dans le brief du post
[4] hôte : graph.instagram.com pour un jeton IG…, graph.facebook.com pour EAA…
[5] brouillons par gabarit : gratuits, aucun appel ; mots interdits de l'espace refusés
[6] brouillons par Claude : devis, accord plafonné, coût changé refusé AVANT l'appel, catégorie « campagnes »,
    commentaires encadrés, mots interdits relevés
[7] porte humaine : aucun envoi sans validation UN PAR UN, confirmation, texte validé = texte envoyé, une seule fois,
    garde-fou du jour ; extrait effacé après décision ; aucun envoi automatique (aucune boucle ne l'appelle)
[8] refus de Meta expliqué, jeton jamais rendu
[9] recensement des routes payantes (test_plafonds_garde, _recensement_payant)
[10] écran : module partagé, copie dist, balise, monté par l'écran Croissance, textes FR/EN, aucun innerHTML
[11] AGENTS.md
Run (depuis backend/) : & $PY tests/test_instagram_commentaires_t501.py"""
import asyncio, json, os, pathlib, re, shutil, subprocess, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt501_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("IG_ACCESS_TOKEN", "IG_BUSINESS_ID", "ANTHROPIC_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()
JOURNAL: list = []
logger.add(lambda m: JOURNAL.append(str(m)), level="DEBUG")

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:400]}")


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.config import settings                                      # noqa: E402
from app.services.storage import init_db, ScheduledPost, async_session_factory  # noqa: E402
from app.services import instagram_commentaires as IC                # noqa: E402

TOK_IG = "IGAAjeton-SECRET-501"
TOK_EAA = "EAAjeton-SECRET-501"
IG_ID = "17841400000000501"
MEDIA = "18000000000000501"

APPELS: list = []
REPONSES: dict = {}


class _R:
    def __init__(self, code, corps):
        self.status_code, self._c = code, corps
        self.text = json.dumps(corps)

    def json(self):
        return self._c


class _Faux:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False

    async def _rep(self, meth, url, **k):
        APPELS.append((meth, url, k))
        for motif, f in REPONSES.items():
            if re.search(motif, url):
                return f(meth, url, k)
        return _R(599, {"error": {"message": "url inattendue"}})

    async def get(self, url, **k): return await self._rep("GET", url, **k)
    async def post(self, url, **k): return await self._rep("POST", url, **k)


IC._client = lambda *a, **k: _Faux()
TIRS: list = []
INTERDITS = ["gratuit"]


async def faux_tirer_garde(moteur, modele, prompt, systeme, max_tokens=4000, json=False, *, categorie="", **k):
    TIRS.append({"moteur": moteur, "prompt": prompt, "systeme": systeme, "categorie": categorie})
    ids = re.findall(r'"id": "([0-9a-f]{12})"', prompt)
    rep = [{"id": i, "texte": "Merci ! Le guide est dans la bio."} for i in ids]
    if rep:
        rep[-1]["texte"] = "C'est gratuit, regarde la bio."          # un mot interdit : relevé, jamais envoyé tel quel
    import json as _j
    return _j.dumps({"reponses": rep})


async def faux_interdits(eid):
    return list(INTERDITS)


IC._tirer_garde = faux_tirer_garde
IC._interdits = faux_interdits
IC._persona = lambda eid: '{"ton": "chaleureux"}'
IC._claude_pret = lambda: ""
IC._estimer_usd = lambda prompt, systeme: 0.0123

c = TestClient(app, client=("127.0.0.1", 50000))
NOW = datetime.utcnow()


async def _preparer():
    await init_db()
    async with async_session_factory() as s:
        s.add(ScheduledPost(id="p-publie", title="Le guide", channels="instagram", run_at=NOW, status="posted",
                            posted_at=NOW - timedelta(days=1), espace_id="deepotus",
                            remote_ids=json.dumps({"instagram": MEDIA}),
                            brief=json.dumps({"mot_cle": "GUIDE", "cta": "Commente GUIDE"})))
        s.add(ScheduledPost(id="p-sans-mot", title="Sans mot", channels="instagram", run_at=NOW, status="posted",
                            posted_at=NOW, espace_id="deepotus", remote_ids=json.dumps({"instagram": "18000000000000999"})))
        s.add(ScheduledPost(id="p-brouillon", title="Brouillon", channels="instagram", run_at=NOW, status="draft",
                            espace_id="deepotus", brief=json.dumps({"mot_cle": "GUIDE"})))
        await s.commit()


asyncio.run(_preparer())


def _src(p):
    return (RACINE / p).read_text(encoding="utf-8")


SRC_S = _src("backend/app/services/instagram_commentaires.py")
SRC_R = _src("backend/app/api/instagram_commentaires_routes.py")
SRC_J = _src("frontend/shared/dz-ig-commentaires.js")
from app.api.instagram_commentaires_routes import router as _ROUTEUR    # noqa: E402
ROUTES = sorted((sorted(r.methods)[0], "/api/instagram/commentaires" + r.path) for r in _ROUTEUR.routes)

print("[1] aucun message privé")
for nom, src in (("service", SRC_S), ("routes", SRC_R), ("écran", SRC_J)):
    sans_doc = re.sub(r'"""[\s\S]*?"""', "", src) if nom != "écran" else re.sub(r"/\*[\s\S]*?\*/", "", src)
    check(f"1.1 {nom} : aucune adresse /messages, aucune réponse privée, aucune permission de messagerie",
          not re.search(r"/messages|private_repl|instagram_(business_)?manage_messages|recipient", sans_doc, re.I))
check("1.2 aucune route privée, aucune route d'envoi en masse (11 routes)", len(ROUTES) == 11 and
      not [p for _m, p in ROUTES if re.search(r"prive|private|message|dm\b|masse|tous|lot", p, re.I)], ROUTES)
check("1.3 aucune fonction du service nommée pour un message privé ou un envoi en masse",
      not re.search(r"def \w*(prive|private|dm|masse|tous|lot)\w*\(", SRC_S, re.I))
check("1.4 la seule écriture vers Meta est /{comment}/replies (réponse publique en fil)",
      re.findall(r'c\.post\(f"\{g\}/\{([a-z_]+)\}/(\w+)"', SRC_S) == [("comment_id", "replies")],
      re.findall(r"c\.post\([^\n]+", SRC_S))
check("1.5 l'envoi ne prend qu'UN brouillon (un identifiant dans le chemin)",
      ("POST", "/api/instagram/commentaires/posts/{post_id}/brouillons/{bid}/envoyer") in ROUTES, ROUTES)
check("1.6 la permission documentée est instagram_business_manage_comments", IC.SCOPE == "instagram_business_manage_comments")

print("[2] rien sans jeton")
e = c.get("/api/instagram/commentaires/etat").json()
check("2.1 état : indisponible sans jeton, permission nommée, réponse privée False",
      e.get("disponible") is False and e.get("scope") == IC.SCOPE and e.get("reponse_privee") is False, e)
r = c.post("/api/instagram/commentaires/posts/p-publie/relever")
check("2.2 relever sans jeton : 409 sans_jeton, aucun appel", r.status_code == 409 and not APPELS
      and r.json()["detail"]["code"] == "sans_jeton" and "instagram_business_manage_comments" in r.json()["detail"]["message"],
      (r.status_code, r.text[:300]))
r = c.post("/api/instagram/commentaires/posts/p-publie/relever", headers={"Accept-Language": "en"})
check("2.3 refus en anglais", r.status_code == 409 and "token" in r.json()["detail"]["message"].lower(), r.text[:300])
settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID = TOK_IG, IG_ID
r = c.post("/api/instagram/commentaires/posts/p-brouillon/relever")
check("2.4 post non publié : 409 pas_publie, aucun appel", r.status_code == 409 and r.json()["detail"]["code"] == "pas_publie"
      and not APPELS, r.text[:300])
r = c.post("/api/instagram/commentaires/posts/p-sans-mot/relever")
check("2.5 post sans mot-clé : 409 sans_mot_cle, aucun appel", r.status_code == 409
      and r.json()["detail"]["code"] == "sans_mot_cle" and not APPELS, r.text[:300])
r = c.post("/api/instagram/commentaires/posts/inconnu/relever")
check("2.6 post inconnu : 404", r.status_code == 404, r.status_code)
r2 =TestClient(app, client=("10.0.0.9", 50000)).get("/api/instagram/commentaires/etat")
check("2.7 boucle locale seulement (refus depuis une autre adresse)", r2.status_code in (401, 403), r2.status_code)
APPELS.clear()

print("[3] relevé")
PAGE1 = {"data": [
    {"id": "c1", "text": "GUIDE stp", "timestamp": "2026-11-26T10:00:00+0000", "hidden": False},
    {"id": "c2", "text": "je veux le guide !", "timestamp": "2026-11-26T10:01:00+0000", "hidden": False},
    {"id": "c3", "text": "super vidéo", "timestamp": "2026-11-26T10:02:00+0000", "hidden": False},
    {"id": "c4", "text": "guidebook ?", "timestamp": "2026-11-26T10:03:00+0000", "hidden": False}],
    "paging": {"cursors": {"after": "CUR1"}, "next": "https://graph.instagram.com/v25.0/" + MEDIA + "/comments?after=CUR1"}}
PAGE2 = {"data": [
    {"id": "c5", "text": "Guidé ?", "timestamp": "2026-11-26T10:04:00+0000", "hidden": False},
    {"id": "c6", "text": "GUIDE (masqué)", "timestamp": "2026-11-26T10:05:00+0000", "hidden": True},
    {"id": "c7", "text": "Guide guide GUIDE", "timestamp": "2026-11-26T10:06:00+0000", "hidden": False}]}
REPONSES[r"/comments"] = lambda m, u, k: _R(200, PAGE2 if (k.get("params") or {}).get("after") == "CUR1" else PAGE1)
r = c.post("/api/instagram/commentaires/posts/p-publie/relever")
d = r.json()
check("3.1 relevé : 200, 7 commentaires lus sur deux pages", r.status_code == 200 and d.get("lus") == 7
      and len([a for a in APPELS if a[1].endswith("/comments")]) == 2, (r.status_code, r.text[:300]))
p1 = APPELS[0][2].get("params") or {}
check("3.2 champs demandés SANS pseudo (ni username, ni from), 50 par page",
      set(p1.get("fields", "").split(",")) == {"id", "text", "timestamp", "hidden"} and str(p1.get("limit")) == "50", p1)
check("3.3 au mot-clé : c1, c2, c5, c7 (casse, accents, mot entier ; masqué et « guidebook » exclus)",
      d.get("au_mot_cle") == 4 and sorted(b["comment_id"] for b in d["brouillons"]) == ["c1", "c2", "c5", "c7"], d)
check("3.4 chaque commentaire au mot-clé attend un brouillon (a_rediger), aucun texte de réponse encore",
      all(b["statut"] == "a_rediger" and b["texte"] == "" for b in d["brouillons"]), d["brouillons"])
fichier = _tmp / "scheduler" / "ig_commentaires" / "p-publie.json"
brut = fichier.read_text("utf-8") if fichier.is_file() else ""
check("3.5 état gardé sans pseudo ni jeton", brut and "username" not in brut and TOK_IG not in brut, brut[:300])


async def _brief(pid):
    async with async_session_factory() as s:
        p = await s.get(ScheduledPost, pid)
        return json.loads(p.brief or "{}")
b = asyncio.run(_brief("p-publie"))
cm = b.get("commentaires_mot_cle") or {}
check("3.6 compteur rangé dans les mesures du post (brief.commentaires_mot_cle), le reste du brief intact",
      cm.get("mot") == "GUIDE" and cm.get("n") == 4 and cm.get("lus") == 7 and cm.get("releve_le") and b.get("cta") == "Commente GUIDE", b)
APPELS.clear()
r = c.post("/api/instagram/commentaires/posts/p-publie/relever")
check("3.7 relevé rejoué : aucun doublon de brouillon", r.status_code == 200 and len(r.json()["brouillons"]) == 4, r.text[:300])
check("3.8 contient_mot : mot entier, sans accents, sans casse",
      IC.contient_mot("Je VEUX le Guidé", "guide") and not IC.contient_mot("guidebook", "guide")
      and IC.contient_mot("mot clé svp", "MOT-CLÉ") is False and IC.contient_mot("le mot-clé svp", "MOT-CLÉ"))
r = c.put("/api/instagram/commentaires/posts/p-sans-mot/mot-cle", json={"mot_cle": "  Recette  "})
check("3.9 poser le mot-clé d'un post : brief.mot_cle", r.status_code == 200 and asyncio.run(_brief("p-sans-mot")).get("mot_cle") == "Recette",
      r.text[:200])
r = c.put("/api/instagram/commentaires/posts/p-sans-mot/mot-cle", json={"mot_cle": "<script>"})
check("3.10 mot-clé invalide refusé (400)", r.status_code == 400, r.status_code)
check("3.11 mot_cle_du_post lit brief.mot_cle", IC.mot_cle_du_post({"mot_cle": "GUIDE"}) == "GUIDE"
      and IC.mot_cle_du_post({}) == "" and IC.mot_cle_du_post(None) == "")

print("[4] hôte")
check("4.1 jeton IG… -> graph.instagram.com", APPELS and all("graph.instagram.com" in a[1] for a in APPELS), APPELS[:1])
APPELS.clear()
settings.IG_ACCESS_TOKEN = TOK_EAA
c.post("/api/instagram/commentaires/posts/p-publie/relever")
check("4.2 jeton EAA… -> graph.facebook.com", APPELS and all("graph.facebook.com" in a[1] for a in APPELS), APPELS[:1])
settings.IG_ACCESS_TOKEN = TOK_IG
APPELS.clear()

print("[5] brouillons par gabarit")
r = c.post("/api/instagram/commentaires/posts/p-publie/brouillons/gabarit", json={"langue": "fr", "gabarit": "Regarde, c'est gratuit !"})
check("5.1 gabarit avec un mot interdit : 409 interdits, aucun brouillon écrit", r.status_code == 409
      and r.json()["detail"]["code"] == "interdits" and all(x["statut"] == "a_rediger" for x in IC.lire("p-publie")["brouillons"]),
      r.text[:300])
r = c.post("/api/instagram/commentaires/posts/p-publie/brouillons/gabarit", json={"langue": "fr"})
d = r.json()
brs = d.get("brouillons") or []
check("5.2 gabarit par défaut : 4 brouillons a_valider, source gabarit, aucun appel ni Claude",
      r.status_code == 200 and len([x for x in brs if x["statut"] == "a_valider" and x["source"] == "gabarit" and x["texte"]]) == 4
      and not APPELS and not TIRS, r.text[:300])

print("[6] brouillons par Claude")
# on remet deux brouillons en attente de rédaction pour Claude
st = IC.lire("p-publie")
for x in st["brouillons"][2:]:
    x["statut"], x["texte"], x["source"] = "a_rediger", "", ""
IC._ecrire("p-publie", st)
r = c.get("/api/instagram/commentaires/posts/p-publie/brouillons/devis?langue=fr")
check("6.1 devis gratuit : usd, 2 commentaires, aucun tir", r.status_code == 200 and r.json().get("usd") == 0.0123
      and r.json().get("n") == 2 and not TIRS, r.text[:200])
r = c.post("/api/instagram/commentaires/posts/p-publie/brouillons/claude", json={"langue": "fr"})
check("6.2 sans accord (max_usd) : 400, aucun tir", r.status_code == 400 and not TIRS, (r.status_code, r.text[:200]))
r = c.post("/api/instagram/commentaires/posts/p-publie/brouillons/claude", json={"langue": "fr", "max_usd": 0.001})
check("6.3 coût au-delà de l'accord : 409 cout AVANT tout tir", r.status_code == 409 and r.json()["detail"]["code"] == "cout"
      and not TIRS, r.text[:300])
r = c.post("/api/instagram/commentaires/posts/p-publie/brouillons/claude", json={"langue": "fr", "max_usd": 0.05})
d = r.json()
check("6.4 un seul tir Claude, catégorie « campagnes », moteur anthropic", r.status_code == 200 and len(TIRS) == 1
      and TIRS[0]["categorie"] == "campagnes" and TIRS[0]["moteur"] == "anthropic", (r.status_code, r.text[:300], TIRS))
check("6.5 commentaires encadrés PREUVE, persona de l'espace et mots interdits dans le prompt, aucun pseudo",
      "<<<PREUVE" in TIRS[0]["prompt"] and "chaleureux" in TIRS[0]["prompt"] and "gratuit" in TIRS[0]["prompt"]
      and "username" not in TIRS[0]["prompt"], TIRS[0]["prompt"][:500])
cl = [x for x in d["brouillons"] if x["source"] == "claude"]
check("6.6 deux brouillons Claude a_valider ; le mot interdit est relevé dans `fautifs`",
      len(cl) == 2 and all(x["statut"] == "a_valider" for x in cl) and any(x.get("fautifs") == ["gratuit"] for x in cl), cl)
check("6.7 la consigne dit : réponse publique, jamais de message privé", "publique" in TIRS[0]["systeme"].lower()
      and "privé" in TIRS[0]["systeme"].lower())
check("6.8 aucun appel à Meta pendant la rédaction", not APPELS, APPELS)
r = c.post("/api/instagram/commentaires/posts/p-publie/brouillons/claude", json={"langue": "fr", "max_usd": 0.05})
check("6.9 rien à rédiger : 409 rien_a_rediger, aucun tir de plus", r.status_code == 409 and len(TIRS) == 1, r.text[:200])

print("[7] porte humaine")
brs = IC.lire("p-publie")["brouillons"]
b0 = brs[0]
fautif = next(x for x in brs if x.get("fautifs"))
REPONSES[r"/replies"] = lambda m, u, k: _R(200, {"id": "rep-" + u.split("/")[-2]})
base = "/api/instagram/commentaires/posts/p-publie/brouillons/"
r = c.post(base + b0["id"] + "/envoyer", json={"texte": b0["texte"], "confirme": True})
check("7.1 envoyer un brouillon NON validé : 409 non_valide, aucun appel", r.status_code == 409
      and r.json()["detail"]["code"] == "non_valide" and not APPELS, r.text[:300])
r = c.post(base + fautif["id"] + "/valider", json={"texte": fautif["texte"]})
check("7.2 valider un texte avec un mot interdit : 409 interdits", r.status_code == 409 and r.json()["detail"]["code"] == "interdits", r.text[:200])
r = c.post(base + b0["id"] + "/valider", json={"texte": "Merci ! Le guide est dans la bio."})
check("7.3 valider UN brouillon : valide, les autres restent a_valider", r.status_code == 200
      and [x["statut"] for x in IC.lire("p-publie")["brouillons"]].count("valide") == 1, r.text[:300])
r = c.post(base + b0["id"] + "/envoyer", json={"texte": "Merci ! Le guide est dans la bio."})
check("7.4 sans confirmation explicite : 400, aucun appel", r.status_code == 400 and not APPELS, r.text[:200])
r = c.post(base + b0["id"] + "/envoyer", json={"texte": "Autre texte", "confirme": True})
check("7.5 texte différent du texte validé : 409 texte_change, aucun appel", r.status_code == 409
      and r.json()["detail"]["code"] == "texte_change" and not APPELS, r.text[:200])
settings.IG_ACCESS_TOKEN = ""
r = c.post(base + b0["id"] + "/envoyer", json={"texte": "Merci ! Le guide est dans la bio.", "confirme": True})
check("7.6 envoi sans jeton : 409 sans_jeton, aucun appel", r.status_code == 409 and r.json()["detail"]["code"] == "sans_jeton"
      and not APPELS, r.text[:200])
settings.IG_ACCESS_TOKEN = TOK_IG
r = c.post(base + b0["id"] + "/envoyer", json={"texte": "Merci ! Le guide est dans la bio.", "confirme": True})
x0 = next(x for x in IC.lire("p-publie")["brouillons"] if x["id"] == b0["id"])
check("7.7 envoi validé : UN POST /{comment}/replies, message = texte validé", r.status_code == 200 and len(APPELS) == 1
      and APPELS[0][0] == "POST" and APPELS[0][1].endswith("/" + b0["comment_id"] + "/replies")
      and (APPELS[0][2].get("data") or {}).get("message") == "Merci ! Le guide est dans la bio.", (r.text[:300], APPELS))
check("7.8 brouillon envoye, id de la réponse gardé, extrait du commentaire effacé",
      x0["statut"] == "envoye" and x0.get("reponse_id") == "rep-" + b0["comment_id"] and not x0.get("extrait"), x0)
APPELS.clear()
r = c.post(base + b0["id"] + "/envoyer", json={"texte": "Merci ! Le guide est dans la bio.", "confirme": True})
check("7.9 deuxième envoi : 409 deja_envoye, aucun appel", r.status_code == 409 and r.json()["detail"]["code"] == "deja_envoye"
      and not APPELS, r.text[:200])
b1 = IC.lire("p-publie")["brouillons"][1]
r = c.post(base + b1["id"] + "/rejeter")
x1 = next(x for x in IC.lire("p-publie")["brouillons"] if x["id"] == b1["id"])
check("7.10 rejeter : rejete, extrait effacé, aucun appel", r.status_code == 200 and x1["statut"] == "rejete"
      and not x1.get("extrait") and not APPELS, x1)
r = c.post(base + b1["id"] + "/valider", json={"texte": "ok"})
check("7.11 un brouillon rejeté ne se valide plus", r.status_code == 409, r.status_code)
b2 = next(x for x in IC.lire("p-publie")["brouillons"] if x["statut"] == "a_valider" and not x.get("fautifs"))
c.post(base + b2["id"] + "/valider", json={"texte": "Merci, regarde la bio."})
IC._compter_envoi(IC.REPONSES_JOUR)                               # le garde-fou du jour est plein
r = c.post(base + b2["id"] + "/envoyer", json={"texte": "Merci, regarde la bio.", "confirme": True})
check("7.12 garde-fou du jour plein : 409 quota, aucun appel", r.status_code == 409 and r.json()["detail"]["code"] == "quota"
      and not APPELS, r.text[:200])
check("7.13 aucune boucle, aucun tick, aucun planificateur n'appelle l'envoi",
      not [f.name for f in (RACINE / "backend" / "app").rglob("*.py")
           if f.name not in ("instagram_commentaires.py", "instagram_commentaires_routes.py")
           and "instagram_commentaires" in f.read_text(encoding="utf-8", errors="replace")
           and f.name != "main.py"])
sans_doc = re.sub(r'"""[\s\S]*?"""', "", SRC_S)
check("7.14 envoyer exige le statut valide ET le texte validé avant le POST",
      0 < sans_doc.find("async def envoyer(") < sans_doc.find('"non_valide"', sans_doc.find("async def envoyer("))
      < sans_doc.find('"texte_change"', sans_doc.find("async def envoyer(")) < sans_doc.find("c.post("))
check("7.15 l'état d'un post donne le compteur et la file", c.get("/api/instagram/commentaires/posts/p-publie").json().get("au_mot_cle") == 4)
f = c.get("/api/instagram/commentaires/file?espace_id=deepotus").json()
check("7.16 la file liste les posts Instagram publiés (avec ou sans mot-clé), jamais un brouillon de post",
      sorted(p["post_id"] for p in f.get("posts", [])) == ["p-publie", "p-sans-mot"], f)

print("[8] refus de Meta")
IC._vider_envois()
REPONSES[r"/replies"] = lambda m, u, k: _R(400, {"error": {"message": "Invalid OAuth access token " + TOK_IG, "code": 190}})
r = c.post(base + b2["id"] + "/envoyer", json={"texte": "Merci, regarde la bio.", "confirme": True})
check("8.1 jeton refusé par Meta : 502, explication, jeton absent", r.status_code == 502 and TOK_IG not in r.text
      and r.json()["detail"]["code"] == "meta", r.text[:300])
x2 = next(x for x in IC.lire("p-publie")["brouillons"] if x["id"] == b2["id"])
check("8.2 l'échec laisse le brouillon valide (rien n'est parti)", x2["statut"] == "valide", x2)
check("8.3 jeton jamais dans le journal", not any(TOK_IG in j or TOK_EAA in j for j in JOURNAL))

print("[9] recensement des routes payantes")
import _recensement_payant as RP                                    # noqa: E402
rec = RP.recenser()
for chemin in ("/posts/{post_id}/brouillons/claude", "/posts/{post_id}/brouillons/{bid}/envoyer"):
    cle = ("instagram_commentaires", "POST", chemin)
    check(f"9.1 {chemin} recensée, puits atteint, gardée", cle in rec and rec[cle]["puits"] and rec[cle]["garde"], rec.get(cle))
gratuites = [k for k, v in rec.items() if k[0] == "instagram_commentaires" and v["puits"]
             and k[2] not in ("/posts/{post_id}/brouillons/claude", "/posts/{post_id}/brouillons/{bid}/envoyer")]
check("9.2 aucune autre route du module n'atteint un puits", not gratuites, gratuites)
pg = _src("backend/tests/test_plafonds_garde.py")
check("9.3 les deux routes dans PAYANTES de test_plafonds_garde",
      '("instagram_commentaires", "POST", "/posts/{post_id}/brouillons/claude")' in pg
      and '("instagram_commentaires", "POST", "/posts/{post_id}/brouillons/{bid}/envoyer")' in pg)
check("9.4 rédaction : coût hors accord refusé AVANT _tirer_garde", 0 < SRC_S.find("async def rediger_claude(")
      < SRC_S.find('"cout"', SRC_S.find("async def rediger_claude(")) < SRC_S.find("await _tirer_garde(", SRC_S.find("async def rediger_claude(")))

print("[10] écran")
check("10.1 copie dist identique", (RACINE / "frontend/shared/dz-ig-commentaires.js").read_bytes()
      == (RACINE / "frontend/dist/shared/dz-ig-commentaires.js").read_bytes())
html = _src("frontend/dist/index.html")
check("10.2 balise une fois, avant dz-croissance.js", html.count('<script src="/shared/dz-ig-commentaires.js"></script>') == 1
      and html.index("/shared/dz-ig-commentaires.js") < html.index("/shared/dz-croissance.js"))
cro = _src("frontend/shared/dz-croissance.js")
check("10.3 monté par l'écran Croissance (section commentaires)", "window.DzIgCommentaires" in cro
      and "croissance.section.commentaires" in cro and cro == _src("frontend/dist/shared/dz-croissance.js"))
I18N = json.loads(_src("frontend/shared/i18n/igcommentaires.json"))
employees = set(re.findall(r'"(igcomm\.[a-z_]+\.[a-z0-9_]+)"', SRC_J))
check("10.4 clés FR/EN complètes, employées, sans orpheline",
      employees and employees == set(I18N) and all(v.get("fr") and v.get("en") for v in I18N.values()),
      sorted(employees ^ set(I18N)))
dico = _src("frontend/shared/dz-i18n-dico.js")
check("10.5 dictionnaire assemblé", all(f'"{k}"' in dico for k in I18N) and '"croissance.section.commentaires"' in dico)
sj = re.sub(r"/\*[\s\S]*?\*/", "", SRC_J)
check("10.6 aucun innerHTML, aucun texte visible en dur", "innerHTML" not in sj
      and not re.search(r'texte:\s*"[A-Za-zÀ-ÿ]', sj) and not re.search(r'textContent\s*=\s*"[A-Za-zÀ-ÿ]', sj))
check("10.7 l'envoi passe par une confirmation et ne vise qu'un brouillon",
      "confirme: true" in sj and "/envoyer" in sj and "__dzDialogue" in sj and not re.search(r"forEach[^\n]*envoyer", sj))
node = shutil.which("node")
if node:
    rr = subprocess.run([node, "--check", str(RACINE / "frontend/shared/dz-ig-commentaires.js")], capture_output=True, text=True)
    check("10.8 syntaxe JS valide (node --check)", rr.returncode == 0, rr.stderr[-300:])
    rr = subprocess.run([node, str(RACINE / "frontend/shared/qa/ig-commentaires.test.mjs")], capture_output=True, text=True,
                        encoding="utf-8")
    check("10.9 banc node du composant (DOM simulé : envoi sans dialogue ou refusé = rien ne part)",
          rr.returncode == 0 and "OK" in rr.stdout, (rr.stdout + rr.stderr)[-600:])

print("[11] AGENTS.md")
ag = _src("AGENTS.md")
i = ag.find("backend/app/services/instagram_commentaires.py")
check("11.1 une ligne t501 juste avant la ligne du coffre", 0 < i < ag.find("| `backend/app/services/coffre.py` | Coffre à clés chiffré |")
      and "t501" in ag[i:ag.find("\n", i)])

print(f"\n{ok} PASS, {fail} FAIL")
shutil.rmtree(_tmp, ignore_errors=True)
sys.exit(1 if fail else 0)
