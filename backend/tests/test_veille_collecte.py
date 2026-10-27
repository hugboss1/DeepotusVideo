# -*- coding: utf-8 -*-
"""t352 (27/10/2026) : la collecte de veille niveau 1 (HN, YouTube, App Store), portée du skill veille-concurrents.
Lecture seule, plafonds, auteurs hachés, doublon = lien + texte. Aucun réseau réel : coutures _GET_JSON et _YTDLP.
Run : & $PY tests/test_veille_collecte.py   (depuis backend/, PYTHONUTF8=1)."""
import asyncio, json, os, sys, tempfile, pathlib, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzt352_collecte_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(TMP)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (str(TMP) + "/t.db").replace("\\", "/")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from app.services import veille_collecte as VC             # noqa: E402

URLS: list = []


def hn_page(q, page, n, nb_pages):
    return {"nbPages": nb_pages, "hits": [{"objectID": f"{q}-{page}-{i}", "comment_text": f"<p>runway credits burn {q} {page}-{i}</p>",
                                           "author": "PseudoSecret", "created_at": "2026-06-01T00:00:00Z", "points": 1}
                                          for i in range(n)]}


def avis(n, meme_texte=False):
    return {"feed": {"entry": [{"im:rating": {"label": "1"}, "title": {"label": "Bad"},
                                "content": {"label": "same" if meme_texte else f"avis {i}"},
                                "author": {"name": {"label": "PseudoSecret"}}, "updated": {"label": "2026-07-01"},
                                "link": {"attributes": {"href": "https://apps.apple.com/app/id1"}}} for i in range(n)]}}


def faux_web(pages_hn=3, lever_page=None, appstore=None, n=40):
    async def _get(url):
        URLS.append(url)
        if "algolia" in url:
            page = int(url.split("page=")[1].split("&")[0])
            if lever_page is not None and page == lever_page:
                raise OSError("réseau coupé")
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["query"][0]
            return hn_page(q, page, n, pages_hn)
        if "itunes.apple.com" in url:
            page = int(url.split("page=")[1].split("/")[0])
            return appstore(page) if appstore else {"feed": {}}
        raise AssertionError(url)
    return _get


async def faux_ytdlp(video, maxi):
    return {"title": "Review", "comments": [{"id": f"c{i}", "text": f"commentaire {i}", "author": "@PseudoSecret",
                                             "timestamp": 1780000000, "like_count": 3} for i in range(maxi + 20)]}


def perim(**k):
    c = {"id": "runway", "famille": "video", "hn": [], "youtube": [], "appstore": [], "pays": ["us"]}
    c.update(k)
    return VC.valider_perimetre({"concurrents": [c]})


def collecte(p, brut, duree=60.0):
    j = []
    r = asyncio.run(VC.collecter(p, brut, VC._horloge() + duree, j.append))
    return r, j


def lignes(brut):
    return [json.loads(l) for f in sorted(brut.glob("*.jsonl")) for l in f.read_text(encoding="utf-8").splitlines() if l]


print("[1] périmètre")
check("test_perimetre_defaut : 13 concurrents valides", len(VC.valider_perimetre(VC.PERIMETRE_DEFAUT)["concurrents"]) == 13)
for mauvais in ({"id": "../x"}, {"id": "runway", "youtube": ["pas une vidéo"]}, {"id": "runway", "appstore": ["abc"]},
                {"id": "runway", "pays": ["usa"]}):
    def _refuse(m=mauvais):
        try:
            VC.valider_perimetre({"concurrents": [m]})
        except ValueError:
            return True
        return False
    check(f"test_perimetre_invalide : {mauvais}", _refuse)
check("test_perimetre_invalide : trop de concurrents bornés",
      len(VC.valider_perimetre({"concurrents": [{"id": f"c{i}"} for i in range(40)]})["concurrents"]) == VC.MAX_CONCURRENTS)
check("test_perimetre_invalide : vidéos bornées",
      len(perim(youtube=["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc", "ddddddddddd"])["concurrents"][0]["youtube"])
      == VC.MAX_VIDEOS_PAR_CONCURRENT)

print("\n[2] Hacker News")
VC._GET_JSON = faux_web(pages_hn=5)
brut = TMP / "a" / "brut"
r, j = collecte(perim(hn=["runway gen"]), brut)
ls = lignes(brut)
check("test_hn_pagination_et_plafond : MAX_PAR_REQUETE", len(ls) == VC.MAX_PAR_REQUETE, len(ls))
check("test_hn_pagination_et_plafond : texte sans html", ls[0]["texte"].startswith("runway credits"), ls[0]["texte"])
check("test_hn_pagination_et_plafond : forme de ligne",
      set(ls[0]) == {"concurrent", "source", "url", "date", "auteur_hash", "texte", "score", "collecte_le", "requete"})
check("test_hn : ajoutés comptés", r["ajoutes"].get("hn") == VC.MAX_PAR_REQUETE, r)

print("\n[3] relance, doublons, auteurs")
r2, _ = collecte(perim(hn=["runway gen"]), brut)
check("test_relance_sans_doublon : rien de neuf", r2["ajoutes"].get("hn", 0) == 0 and len(lignes(brut)) == len(ls), r2)
check("test_auteur_jamais_en_clair", all(b"PseudoSecret" not in f.read_bytes() for f in brut.glob("*")))
check("test_auteur_jamais_en_clair : empreinte", ls[0]["auteur_hash"] == VC.empreinte("PseudoSecret") and len(ls[0]["auteur_hash"]) == 10)

print("\n[4] App Store : doublon = lien + texte")
VC._GET_JSON = faux_web(appstore=lambda page: avis(5) if page == 1 else {"feed": {"entry": []}})
brut = TMP / "b" / "brut"
collecte(perim(appstore=["1665024375"]), brut)
check("test_appstore_doublon_lien_texte : même lien, textes différents gardés", len(lignes(brut)) == 5, len(lignes(brut)))
VC._GET_JSON = faux_web(appstore=lambda page: avis(5, meme_texte=True) if page == 1 else {"feed": {"entry": []}})
brut = TMP / "c" / "brut"
collecte(perim(appstore=["1665024375"]), brut)
check("test_appstore_doublon_lien_texte : même lien et même texte = 1", len(lignes(brut)) == 1, len(lignes(brut)))
check("test_appstore : source par pays", lignes(brut)[0]["source"] == "appstore-us")

print("\n[5] YouTube")
VC._YTDLP = faux_ytdlp
brut = TMP / "d" / "brut"
collecte(perim(youtube=["DrGuh-eJXDw"]), brut)
ls = lignes(brut)
check("test_youtube : plafond par vidéo", len(ls) == VC.MAX_PAR_VIDEO, len(ls))
check("test_youtube : lien vers le commentaire", ls[0]["url"] == "https://www.youtube.com/watch?v=DrGuh-eJXDw&lc=c0", ls[0]["url"])
VC._YTDLP = VC._ytdlp_defaut
VC._ytdlp_commande = lambda: None
r, _ = collecte(perim(youtube=["DrGuh-eJXDw"]), TMP / "e" / "brut")
check("test_youtube_sans_ytdlp_limite", any("yt-dlp" in l for l in r["limites"]) and not r["ajoutes"].get("youtube"), r)

print("\n[6] pannes et échéance")
URLS.clear()
VC._GET_JSON = faux_web(pages_hn=5, lever_page=1)
brut = TMP / "f" / "brut"
r, _ = collecte(perim(hn=["runway gen", "runwayml"]), brut)
check("test_collecte_reseau_partiel : acquis gardés (2 requêtes × 1 page)", len(lignes(brut)) == 80, len(lignes(brut)))
check("test_collecte_reseau_partiel : limite notée", any("réseau coupé" in l for l in r["limites"]), r["limites"])
VC._GET_JSON = faux_web(pages_hn=5)
r, _ = collecte(perim(hn=["a", "b", "c"]), TMP / "g" / "brut", duree=-1)
check("test_echeance : arrêt et limite", any("durée maximale" in l for l in r["limites"]) and not r["ajoutes"].get("hn"), r)
VC.MAX_BRUT, _mb = 150, VC.MAX_BRUT
r, _ = collecte(perim(hn=["x1", "x2", "x3"]), TMP / "h" / "brut")
check("test_max_brut : plafond global", sum(r["ajoutes"].values()) <= 150 and any("plafond" in l for l in r["limites"]), r)
VC.MAX_BRUT = _mb
check("test_lecture_seule : seulement des GET connus",
      all(u.startswith(("https://hn.algolia.com/api/v1/search?", "https://itunes.apple.com/")) for u in URLS))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
