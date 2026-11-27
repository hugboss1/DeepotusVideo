# -*- coding: utf-8 -*-
"""t513 (RV3, 26/11/2026) — banc des références données par un LIEN et de « mes recettes ».

Sections :
  1. pures : reconnaitre (Instagram reel/p, TikTok, YouTube watch/shorts/youtu.be, X, Facebook, LinkedIn, inconnu,
     refus d'un lien non https) ; lire_vtt (balises, répétitions des automatiques) ; texte_horodate ; choisir_piste
     (manuels avant automatiques, langue) ;
  2. routes (réseau remplacé) : YouTube -> oEmbed + sous-titres lus, texte capté, besoin d'une capture ; Instagram ->
     AUCUN appel réseau (jeton Meta, D7), besoin d'une capture ; TikTok -> oEmbed seul ; lien refusé -> 400 ;
     yt-dlp absent -> état « sans_outil » ; jamais de téléchargement (aucune URL de média demandée) ;
  3. mes recettes : liste de l'espace, la plus récente d'abord, sans celles d'un autre espace.
Run (depuis backend/) : & $PY tests/test_inspiration_lien.py"""
import asyncio, json, os, pathlib, shutil, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzinsl_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import inspiration_lien as IL                    # noqa: E402

RESEAU = []
YTDLP = {"absent": False}
VTT = """WEBVTT
Kind: captions
Language: fr

00:00:00.000 --> 00:00:02.500
<c>Tu</c> paies <00:00:01.000><c>chaque mois</c>

00:00:02.500 --> 00:00:05.000
Tu paies chaque mois

00:00:31.000 --> 00:00:33.000
pour un outil inutile
"""


async def faux_json(url):
    RESEAU.append(url)
    if "youtube.com/oembed" in url:
        return {"title": "Pourquoi tu paies trop", "author_name": "Chaîne Test", "thumbnail_url": "https://i.ytimg.com/x.jpg"}
    if "tiktok.com/oembed" in url:
        return {"title": "Astuce", "author_name": "tt", "thumbnail_url": "http://non-https/x.jpg"}
    raise RuntimeError("inattendu")


async def faux_texte(url):
    RESEAU.append(url)
    return VTT


async def faux_ytdlp(url):
    RESEAU.append("ytdlp:" + url)
    if YTDLP["absent"]:
        raise FileNotFoundError("yt-dlp")
    return {"duration": 42, "view_count": 1200, "subtitles": {"de": [{"ext": "vtt", "url": "https://yt/de.vtt"}]},
            "automatic_captions": {"fr": [{"ext": "json3", "url": "https://yt/fr.json3"}, {"ext": "vtt", "url": "https://yt/fr.vtt"}]}}


IL._GET_JSON, IL._GET_TEXTE, IL._YTDLP_INFO = faux_json, faux_texte, faux_ytdlp


def section_pures():
    print("[1] pures")
    cas = {
        "https://www.instagram.com/reel/DfYTnaJFcMP/?igsh=abc": ("instagram", "DfYTnaJFcMP"),
        "https://instagram.com/p/Cx_1-2/": ("instagram", "Cx_1-2"),
        "https://www.tiktok.com/@nom/video/7301234567890": ("tiktok", "7301234567890"),
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s": ("youtube", "dQw4w9WgXcQ"),
        "https://youtube.com/shorts/abcDEF12345": ("youtube", "abcDEF12345"),
        "https://youtu.be/dQw4w9WgXcQ?si=x": ("youtube", "dQw4w9WgXcQ"),
        "https://m.youtube.com/watch?v=zz": ("youtube", "zz"),
        "https://x.com/compte/status/1850000000000000000": ("x", "1850000000000000000"),
        "https://twitter.com/compte/status/42": ("x", "42"),
        "https://www.facebook.com/reel/123": ("facebook", ""),
        "https://www.linkedin.com/posts/abc": ("linkedin", ""),
        "https://exemple.fr/video": ("", ""),
        "https://evilinstagram.com/reel/x": ("", ""),
    }
    for url, (pl, ident) in cas.items():
        r = IL.reconnaitre(url)
        check(f"1 {url[8:40]} -> {pl or 'inconnue'} {ident}", (r["plateforme"], r["id"]) == (pl, ident), r)
    check("1 paramètres de suivi retirés du lien gardé", "igsh" not in IL.reconnaitre("https://www.instagram.com/reel/A/?igsh=abc")["lien"])
    for mauvais in ("javascript:alert(1)", "ftp://x.com/a", "instagram.com/reel/x", "https://" + "a" * 300):
        try:
            IL.reconnaitre(mauvais); check(f"1 refus {mauvais[:20]}", False)
        except Exception as e:  # noqa: BLE001
            check(f"1 refus {mauvais[:20]}", getattr(e, "code", "") == "lien", e)
    b = IL.lire_vtt(VTT)
    check("1v vtt : balises retirées, répétition fusionnée", [x["texte"] for x in b] == ["Tu paies chaque mois", "pour un outil inutile"], b)
    check("1w horodaté par tranche de 30 s", IL.texte_horodate(b) == "[00:00] Tu paies chaque mois\n[00:30] pour un outil inutile",
          IL.texte_horodate(b))
    info = {"subtitles": {"en": [{"ext": "vtt", "url": "https://m/en"}]}, "automatic_captions": {"fr": [{"ext": "vtt", "url": "https://a/fr"}]}}
    check("1x manuels avant automatiques", IL.choisir_piste(info, ("fr", "en")) == ("https://m/en", "en", "manuels"))
    check("1y aucune piste vtt https -> None", IL.choisir_piste({"subtitles": {"fr": [{"ext": "vtt", "url": "http://x"}]}}, ("fr",)) is None)


def section_routes():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import espaces
    with TestClient(app, client=("127.0.0.1", 50000)) as client, TestClient(app, client=("192.168.1.20", 50000)) as dehors:
        EA = espaces.creer({"nom": "Studio Lien"})["id"]
        EB = espaces.creer({"nom": "Autre"})["id"]
        H = {"X-Dz-Espace": EA}
        print("[2] liens")
        r = dehors.post("/api/inspiration/lien", json={"url": "https://youtu.be/x"})
        check("2a hors machine -> 401 ou 403", r.status_code in (401, 403), r.status_code)
        RESEAU.clear()
        r = client.post("/api/inspiration/lien", headers=H, json={"url": "https://www.youtube.com/shorts/abcDEF12345"})
        j = r.json()
        check("2b YouTube : 200, oEmbed lu", r.status_code == 200 and j["source"]["titre"] == "Pourquoi tu paies trop"
              and j["source"]["auteur"] == "Chaîne Test" and j["source"]["vignette"].startswith("https://"), r.text[:300])
        check("2c sous-titres automatiques FR lus, devenus le texte capté", j["lien"]["soustitres"]["etat"] == "lus"
              and j["lien"]["soustitres"]["genre"] == "automatiques" and "Tu paies chaque mois" in j["texte_capte"], j.get("lien"))
        check("2d compteurs relevés mais non vérifiés", j["source"]["compteurs"] == {"view_count": 1200}
              and j["source"]["compteurs_verifies"] is False)
        check("2e besoin d'une capture affiché, matière lien", j["matiere"] == "lien" and j["lien"]["besoin_capture"])
        check("2f jamais de média téléchargé : oEmbed, yt-dlp (métadonnées) et la piste vtt seulement",
              all(("oembed" in u) or u.startswith("ytdlp:") or u.endswith(".vtt") for u in RESEAU), RESEAU)
        RESEAU.clear()
        r = client.post("/api/inspiration/lien", headers=H, json={"url": "https://www.instagram.com/reel/DfYTnaJFcMP/"})
        j = r.json()
        check("2g Instagram : aucun appel réseau (jeton Meta, D7), accès « jeton »", r.status_code == 200 and not RESEAU
              and j["lien"]["acces"] == "jeton" and j["lien"]["besoin_capture"], (RESEAU, r.text[:200]))
        r = client.post("/api/inspiration/lien", headers=H, json={"url": "https://www.tiktok.com/@n/video/1"})
        j = r.json()
        check("2h TikTok : oEmbed seul, vignette http écartée", j["source"]["titre"] == "Astuce" and j["source"]["vignette"] == ""
              and j["lien"]["soustitres"]["etat"] == "non_ouvert", j.get("source"))
        r = client.post("/api/inspiration/lien", headers=H, json={"url": "javascript:alert(1)"})
        check("2i lien refusé -> 400 code lien", r.status_code == 400 and r.json()["detail"]["code"] == "lien", r.text[:200])
        r = client.post("/api/inspiration/lien", headers={**H, "Accept-Language": "en"}, json={"url": "ftp://a"})
        check("2j message traduit", "Link expected" in r.text, r.text[:200])
        YTDLP["absent"] = True
        r = client.post("/api/inspiration/lien", headers=H, json={"url": "https://youtu.be/dQw4w9WgXcQ"})
        check("2k yt-dlp absent : état sans_outil, l'oEmbed reste", r.json()["lien"]["soustitres"]["etat"] == "sans_outil"
              and r.json()["source"]["titre"], r.text[:200])
        iid = r.json()["id"]
        r = client.get(f"/api/inspiration/{iid}/devis-lecture", headers=H)
        check("2l un lien ne se lit pas comme une vidéo (400 matiere)", r.status_code == 400, r.status_code)
        print("[3] mes recettes")
        for nom, eid, quand in (("a" * 32, EA, "2026-11-20T10:00:00+00:00"), ("b" * 32, EA, "2026-11-25T10:00:00+00:00"),
                                ("c" * 32, EB, "2026-11-26T10:00:00+00:00")):
            d = espaces.dossier() / eid / "recettes"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{nom}.json").write_text(json.dumps({"lu_le": quand, "source": {"plateforme": "instagram", "libelle": "Reel"},
                                                       "format": {"duree_s": 42}, "rythme": {"tableaux": 17},
                                                       "structure": [{"role": "accroche"}], "appel": {"type": "lien"}}),
                                           encoding="utf-8")
        (espaces.dossier() / EA / "recettes" / "pas-un-id.json").write_text("{}", encoding="utf-8")
        r = client.get("/api/inspiration/recettes", headers=H)
        ids = [x["id"] for x in r.json().get("recettes", [])]
        check("3a deux recettes de A, la plus récente d'abord, pas celle de B", ids == ["b" * 32, "a" * 32], ids)
        check("3b vue courte : tableaux, briques, appel", r.json()["recettes"][0]["tableaux"] == 17
              and r.json()["recettes"][0]["briques"] == ["accroche"])


def test_inspiration_lien():
    section_pures()
    section_routes()
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    try:
        section_pures()
        section_routes()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
