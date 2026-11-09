# -*- coding: utf-8 -*-
"""t494 (lot G4 « boucle de croissance », 09/11/2026) — les formes d'un post Instagram : Reel (inchangé), reel d'essai,
image, carrousel, Story ; dépôt temporaire chez fal, jamais par défaut.

[A] pur        format_post (normalisation, noms d'images confinés), exige_depot, reglage / regler
[B] refus      AVANT tout appel : dépôt non activé, clé fal absente, pièces manquantes, carrousel hors bornes, image hors rapport
[C] envois     la suite exacte des appels de chaque forme ; le jeton et l'adresse du dépôt ; la Story vidéo reste locale
[D] routes     réglage, format d'un post (422, 409, 404), image du post transmise par marketing
Data-dir temporaire, aucun réseau, aucun dépôt réel.
Run : & $PY tests/test_instagram_formes.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzigf_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID, settings.FAL_KEY = "EAAbancjeton", "42", ""
from app.services import instagram_publisher as ig                  # noqa: E402
from PIL import Image                                               # noqa: E402

print("\n[A] le format d'un post")
check("A1 rien ou n'importe quoi : Reel, graduation manuelle, aucune image",
      ig.format_post(None) == {"forme": "reel", "graduation": "MANUAL", "images": []} == ig.format_post({"forme": "vlog", "graduation": 3, "images": "x"}))
check("A2 formes connues gardées", [ig.format_post({"forme": f})["forme"] for f in ig.FORMES] == list(ig.FORMES)
      and ig.FORMES == ("reel", "essai", "image", "carrousel", "story"))
check("A3 graduation selon performance gardée", ig.format_post({"forme": "essai", "graduation": "SS_PERFORMANCE"})["graduation"] == "SS_PERFORMANCE")
check("A4 images : noms simples seulement (ni chemin, ni remontée, ni autre extension)",
      ig.format_post({"images": ["a.png", "../b.png", "c:/d.jpg", "sous/e.jpg", "f.exe", 7, "g h.webp", ".cache.png"]})["images"] == ["a.png", "g h.webp"])
check("A5 images bornées à 20", len(ig.format_post({"images": [f"i{k}.jpg" for k in range(30)]})["images"]) == 20)
check("A6 exige_depot : essai, image, carrousel toujours ; story seulement sans vidéo ; reel jamais",
      [ig.exige_depot(f, True) for f in ig.FORMES] == [False, True, True, True, False]
      and ig.exige_depot("story", False) is True and ig.exige_depot("reel", False) is False)
check("A7 réglage absent : dépôt désactivé", ig.reglage() == {"depot_fal": False})
check("A8 regler(True) puis (False)", ig.regler(True) == {"depot_fal": True} and ig.reglage()["depot_fal"] is True
      and ig.regler(False) == {"depot_fal": False})
ig._FICHIER_REGLAGE.write_text('{"depot_fal": "oui"}', "utf-8")
check("A9 une valeur qui n'est pas « vrai » ne vaut pas accord", ig.reglage() == {"depot_fal": False})
ig._FICHIER_REGLAGE.write_text("pas du json", "utf-8")
check("A10 fichier illisible : désactivé", ig.reglage() == {"depot_fal": False})

settings.images_path.mkdir(parents=True, exist_ok=True)
def image(nom, l, h, mode="RGB"):
    p = settings.images_path / nom
    Image.new(mode, (l, h), (200, 60, 20) if mode == "RGB" else (200, 60, 20, 128)).save(p)
    return str(p)
CARRE, PORTRAIT, LARGE, TROP_LARGE, PETITE, VERT = (image("carre.png", 1080, 1080), image("portrait.png", 1080, 1350, "RGBA"),
    image("large.jpg", 3000, 2000), image("bandeau.png", 2400, 600), image("petite.png", 200, 200), image("vertical.png", 1080, 1920))
vid = _tmp / "clip.mp4"
vid.write_bytes(b"\x00" * 2048)


class _Rep:
    def __init__(self, code, data): self.status_code, self._d, self.text = code, data, json.dumps(data)
    def json(self): return self._d


class _Faux:
    """Répond selon l'appel ; `casse` = un préfixe d'étape à faire échouer (« media », « publish », « statut »)."""
    appels: list = []
    casse = None
    plein = False
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def get(self, url, params=None):
        _Faux.appels.append(("GET", url, dict(params or {}), {}))
        if url.endswith("/content_publishing_limit"):
            return _Rep(200, {"data": [{"quota_usage": 100 if _Faux.plein else 3, "config": {"quota_total": 100}}]})
        return _Rep(200, {"status_code": "ERROR", "status": "format"} if _Faux.casse == "statut" else {"status_code": "FINISHED"})
    async def post(self, url, data=None, content=None, headers=None):
        _Faux.appels.append(("POST", url, dict(data or {}), dict(headers or {})))
        if "rupload" in url:
            async for _ in content:
                pass
            return _Rep(200, {"success": True})
        if url.endswith("/media_publish"):
            return _Rep(403, {"error": {"message": "refus EAAbancjeton"}}) if _Faux.casse == "publish" else _Rep(200, {"id": "media77"})
        if _Faux.casse == "media":
            return _Rep(400, {"error": {"message": "mauvais EAAbancjeton"}})
        n = sum(1 for a in _Faux.appels if a[0] == "POST" and a[1].endswith("/media"))
        return _Rep(200, {"id": f"c{n}", "uri": f"https://rupload.facebook.com/ig-api-upload/v25.0/c{n}"})


DEPOTS = []
class _Depot:
    def __init__(self, path, infos): self.path, self.infos, self.name = pathlib.Path(path), infos, pathlib.Path(path).name
    def exists(self): return self.path.exists()
async def _depot(path):
    with Image.open(path) as im:
        DEPOTS.append(_Depot(path, (im.format, im.mode, im.size)))
    return f"https://depot.example/{pathlib.Path(path).name}"
async def _depot_video(path):
    DEPOTS.append(_Depot(path, None))
    return f"https://depot.example/{pathlib.Path(path).name}"

ig._client = lambda timeout=60.0: _Faux()
ig.POLL_DELAIS = (0,)
ig.POLL_IMAGE = (0,)
B = lambda **k: {"brief": {"instagram": k}}
etapes = lambda: [(m, u.split("/")[-1] if "rupload" not in u else "rupload") for m, u, _d, _h in _Faux.appels]
def raz(): _Faux.appels.clear(); DEPOTS.clear(); _Faux.casse = None; _Faux.plein = False


async def main():
    print("\n[B] refus avant tout appel")
    ig.regler(False)
    for forme, v, im, extra in (("essai", str(vid), None, {}), ("image", None, CARRE, {}), ("story", None, VERT, {}),
                                ("carrousel", None, None, {"images": ["carre.png", "portrait.png"]})):
        raz()
        r = await ig.publish("légende", v, im, B(forme=forme, **extra))
        check(f"B1 {forme} sans le réglage : refusé, le refus dit quoi activer, aucun appel, aucun dépôt",
              not r.ok and "dépôt" in r.detail and forme in r.detail and not _Faux.appels and not DEPOTS, r.detail)
    ig.regler(True)
    raz()
    r = await ig.publish("l", None, CARRE, B(forme="image"))
    check("B2 réglage activé mais pas de clé fal : refusé, dit, aucun appel", not r.ok and "clé fal" in r.detail and not _Faux.appels and not DEPOTS, r.detail)
    settings.FAL_KEY = "fal-banc"
    ig._deposer = _depot
    for libelle, v, im, meta, mot in (
            ("essai sans vidéo", None, CARRE, B(forme="essai"), "exige une vidéo"),
            ("reel sans vidéo (comme avant)", None, CARRE, {}, "exige une vidéo"),
            ("image sans image", str(vid), None, B(forme="image"), "exige une image"),
            ("story sans rien", None, None, B(forme="story"), "exige une image ou une vidéo"),
            ("carrousel d'une image", None, None, B(forme="carrousel", images=["carre.png"]), "2 à 20"),
            ("carrousel sans image", None, None, B(forme="carrousel"), "2 à 20"),
            ("carrousel, image absente", None, None, B(forme="carrousel", images=["carre.png", "fantome.png"]), "fantome.png"),
            ("image hors rapport (4:1)", None, TROP_LARGE, B(forme="image"), "recadrez"),
            ("image trop petite", None, PETITE, B(forme="image"), "au moins 320"),
            ("carrousel avec une image hors rapport", None, None, B(forme="carrousel", images=["carre.png", "bandeau.png"]), "recadrez")):
        raz()
        r = await ig.publish("l", v, im, meta)
        check(f"B3 {libelle} : refusé « {mot} », aucun appel, aucun dépôt", not r.ok and mot in r.detail and not _Faux.appels and not DEPOTS, r.detail)
    raz(); _Faux.plein = True
    r = await ig.publish("l", None, CARRE, B(forme="image"))
    check("B4 compteur plein : refus après le compteur seul, AUCUN dépôt chez fal", not r.ok and "100/100" in r.detail
          and etapes() == [("GET", "content_publishing_limit")] and not DEPOTS, r.detail)

    print("\n[C] les envois")
    raz()
    r = await ig.publish("Ma légende", None, CARRE, B(forme="image"))
    check("C1 image : compteur, conteneur, statut, publication", r.ok and r.remote_id == "media77" and r.detail == "instagram: image media77"
          and etapes() == [("GET", "content_publishing_limit"), ("POST", "media"), ("GET", "c1"), ("POST", "media_publish")], str(etapes()))
    d = _Faux.appels[1][2]
    check("C2 image : image_url du dépôt, légende, ni media_type ni envoi résumable", d.get("image_url") == "https://depot.example/carre.jpg"
          and d.get("caption") == "Ma légende" and "media_type" not in d and "upload_type" not in d, str(d))
    check("C3 le fichier déposé est un JPEG RVB (un PNG ne part jamais tel quel)", len(DEPOTS) == 1 and DEPOTS[0].infos == ("JPEG", "RGB", (1080, 1080)), str(DEPOTS[0].infos))
    raz()
    await ig.publish("l", None, LARGE, B(forme="image"))
    check("C4 image de 3000 px : ramenée à 1440 de large, rapport gardé", DEPOTS[0].infos == ("JPEG", "RGB", (1440, 960)), str(DEPOTS[0].infos))
    raz()
    await ig.publish("l", None, CARRE, B(forme="image"))
    check("C5 la copie JPEG temporaire est effacée après l'envoi", not DEPOTS[0].exists())
    raz()
    r = await ig.publish("L", None, None, B(forme="carrousel", images=["carre.png", "portrait.png", "large.jpg"]))
    check("C6 carrousel : trois enfants puis le parent, attendu, publié — UN post", r.ok and r.detail == "instagram: carrousel media77"
          and etapes() == [("GET", "content_publishing_limit"), ("POST", "media"), ("POST", "media"), ("POST", "media"), ("POST", "media"),
                           ("GET", "c4"), ("POST", "media_publish")], str(etapes()))
    enf, par = [a[2] for a in _Faux.appels[1:4]], _Faux.appels[4][2]
    check("C7 enfants : is_carousel_item, dans l'ordre choisi, sans légende", [e.get("image_url").split("/")[-1] for e in enf] == ["carre.jpg", "portrait.jpg", "large.jpg"]
          and all(e.get("is_carousel_item") == "true" and "caption" not in e for e in enf), str(enf))
    check("C8 parent : CAROUSEL, children dans l'ordre, légende", par.get("media_type") == "CAROUSEL" and par.get("children") == "c1,c2,c3" and par.get("caption") == "L", str(par))
    raz()
    ig._deposer = _depot_video
    r = await ig.publish("Essai", str(vid), None, B(forme="essai", graduation="SS_PERFORMANCE"))
    d = _Faux.appels[1][2]
    check("C9 reel d'essai : par video_url (jamais l'envoi résumable), trial_params en JSON", r.ok and r.detail == "instagram: reel d'essai media77"
          and d.get("media_type") == "REELS" and d.get("video_url") == "https://depot.example/clip.mp4" and "upload_type" not in d
          and json.loads(d.get("trial_params")) == {"graduation_strategy": "SS_PERFORMANCE"}
          and not any(e == ("POST", "rupload") for e in etapes()), str(d))
    check("C10 reel d'essai : pas de share_to_feed (non documenté avec l'essai)", "share_to_feed" not in d)
    raz()
    r = await ig.publish("ignorée", str(vid), VERT, B(forme="story"))
    d = _Faux.appels[1][2]
    check("C11 Story vidéo : envoi résumable LOCAL, aucun dépôt, pas de légende", r.ok and r.detail == "instagram: story media77" and not DEPOTS
          and d.get("media_type") == "STORIES" and d.get("upload_type") == "resumable" and "caption" not in d and "share_to_feed" not in d
          and ("POST", "rupload") in etapes(), str(d))
    ig.regler(False)
    raz()
    r = await ig.publish("l", str(vid), None, B(forme="story"))
    check("C12 Story vidéo : part même SANS le réglage du dépôt", r.ok and not DEPOTS)
    r0 = await ig.publish("Reel", str(vid), None, {})
    check("C13 Reel : inchangé et sans dépôt, réglage désactivé", r0.ok and r0.detail == "instagram: reel media77" and not DEPOTS
          and _Faux.appels[-4][2].get("share_to_feed") == "true")
    ig.regler(True)
    ig._deposer = _depot
    raz()
    r = await ig.publish("l", None, VERT, B(forme="story"))
    d = _Faux.appels[1][2]
    check("C14 Story image : par le dépôt, 9:16 accepté (pas de borne de rapport), pas de légende", r.ok and d.get("media_type") == "STORIES"
          and d.get("image_url") == "https://depot.example/vertical.jpg" and "caption" not in d, str(d))
    raz()
    r = await ig.publish("l", str(vid), None, dict(B(forme="image"), image=PORTRAIT))
    check("C15 image du post transmise par meta.image quand une vidéo est attachée", r.ok and DEPOTS[0].name == "portrait.jpg")
    for casse, mot in (("media", "instagram container 400"), ("statut", "instagram container ERROR"), ("publish", "instagram publish 403")):
        raz(); _Faux.casse = casse
        r = await ig.publish("l", None, CARRE, B(forme="image"))
        check(f"C16 échec à l'étape « {casse} » : dit, jeton masqué", not r.ok and r.detail.startswith(mot) and "EAAbancjeton" not in r.detail, r.detail)
    raz(); _Faux.casse = "media"
    r = await ig.publish("l", None, None, B(forme="carrousel", images=["carre.png", "portrait.png"]))
    check("C17 carrousel : un enfant refusé arrête tout, rien n'est publié", not r.ok and not any(e == ("POST", "media_publish") for e in etapes())
          and sum(1 for e in etapes() if e == ("POST", "media")) == 1, str(etapes()))
    async def _panne(path): raise RuntimeError("fal muet EAAbancjeton")
    ig._deposer = _panne
    raz()
    r = await ig.publish("l", None, CARRE, B(forme="image"))
    check("C18 le dépôt échoue : refus dit, jeton masqué, aucun conteneur créé", not r.ok and "fal muet" in r.detail and "EAAbancjeton" not in r.detail
          and ("POST", "media") not in etapes(), r.detail)
    check("C19 le jeton n'est dans aucune URL", all("EAAbancjeton" not in a[1] for a in _Faux.appels))
    ig._deposer = _depot

    print("\n[D] les routes")
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import init_db, ScheduledPost, async_session_factory
    await init_db()
    async with async_session_factory() as s:
        s.add(ScheduledPost(id="p1", title="Post", channels="instagram", run_at=datetime.utcnow(), status="draft",
                            brief=json.dumps({"objective": "garder"})))
        s.add(ScheduledPost(id="p2", title="Parti", channels="instagram", run_at=datetime.utcnow(), status="posted"))
        s.add(ScheduledPost(id="p3", title="Avec rendu", channels="instagram", run_at=datetime.utcnow(), status="draft", job_id="j1"))
        await s.commit()
    ig.regler(False)
    with TestClient(app) as c:
        j = c.get("/api/schedule/instagram/reglage").json()
        check("D1 réglage : désactivé par défaut, clé fal dite, formes et bornes", j["depot_fal"] is False and j["fal_pret"] is True
              and j["formes"] == list(ig.FORMES) and j["graduations"] == list(ig.GRADUATIONS) and j["carrousel"] == [2, 20], str(j))
        check("D2 activer : 200, relu", c.put("/api/schedule/instagram/reglage", json={"depot_fal": True}).json() == {"depot_fal": True}
              and c.get("/api/schedule/instagram/reglage").json()["depot_fal"] is True)
        check("D3 autre chose qu'un booléen : 422, rien ne change", c.put("/api/schedule/instagram/reglage", json={"depot_fal": "oui"}).status_code == 422
              and ig.reglage()["depot_fal"] is True)
        j = c.get("/api/schedule/p1/instagram").json()
        check("D4 post sans format : Reel, pas de dépôt requis", j["forme"] == "reel" and j["exige_depot"] is False and j["a_video"] is False and j["statut"] == "draft", str(j))
        r = c.put("/api/schedule/p1/instagram", json={"forme": "carrousel", "images": ["carre.png", "portrait.png"]})
        check("D5 carrousel posé : 200, dépôt requis", r.status_code == 200 and r.json()["forme"] == "carrousel" and r.json()["exige_depot"] is True
              and r.json()["images"] == ["carre.png", "portrait.png"], r.text[:200])
        async with async_session_factory() as s:
            b = json.loads((await s.get(ScheduledPost, "p1")).brief)
        check("D6 le reste du brief est gardé", b.get("objective") == "garder" and b["instagram"]["forme"] == "carrousel", str(b))
        check("D7 forme inconnue : 422", c.put("/api/schedule/p1/instagram", json={"forme": "vlog"}).status_code == 422)
        check("D8 graduation inconnue : 422", c.put("/api/schedule/p1/instagram", json={"forme": "essai", "graduation": "VITE"}).status_code == 422)
        check("D9 image hors Bibliothèque ou chemin : 422", c.put("/api/schedule/p1/instagram", json={"forme": "carrousel", "images": ["carre.png", "../x.png"]}).status_code == 422
              and c.put("/api/schedule/p1/instagram", json={"forme": "carrousel", "images": ["carre.png", "fantome.png"]}).status_code == 422)
        check("D10 plus de 20 images : 422", c.put("/api/schedule/p1/instagram", json={"forme": "carrousel", "images": ["carre.png"] * 21}).status_code == 422)
        check("D11 post déjà publié : 409", c.put("/api/schedule/p2/instagram", json={"forme": "story"}).status_code == 409)
        check("D12 post inconnu : 404", c.get("/api/schedule/nulle/instagram").status_code == 404
              and c.put("/api/schedule/nulle/instagram", json={"forme": "story"}).status_code == 404)
        r = c.put("/api/schedule/p3/instagram", json={"forme": "story"})
        check("D13 Story sur un post avec rendu : pas de dépôt requis", r.status_code == 200 and r.json()["exige_depot"] is False and r.json()["a_video"] is True)
    src = (pathlib.Path(__file__).resolve().parents[1] / "app" / "services" / "marketing.py").read_text(encoding="utf-8")
    check("D14 marketing transmet l'image du post même avec une vidéo", 'meta["image"] = image or await _resolve_post_image(post)' in src)


asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
