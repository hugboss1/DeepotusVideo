# -*- coding: utf-8 -*-
"""Correctifs de traduction du Planificateur et de News (10/10/2026), relevés en capturant le guide v3 (t175) :

  [B] le maillon de queue scripts/patch_bundle_i18nfix.py dans le bundle livré : pastilles de mode et d'état de
      l'inspecteur, « assisted » de la liste des canaux, `&lang=` de l'aperçu final, exemple du Brief et langue par
      défaut de « Générer un plan marketing » ; inverse `avant_i18nfix` exact à l'octet ; double application refusée ;
  [D] le dictionnaire : clés du maillon en fr et en, « Réglages → Comptes connectés » dans l'aide des Comptes ;
  [S] le serveur : quotas (/schedule/quotas), formes (/news/forms), motifs du filtre, du score, des tendances et de la
      voix, aperçu PNG — en anglais avec Accept-Language: en (ou `lang=en` pour l'aperçu), en français accentué sinon ;
      messages.json à jour (scripts/i18n_planif_news_serveur.py --check).
Run (depuis backend/) : & $PY tests/test_i18n_planif_news.py"""
import io, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzi18npn_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "UI_LANG"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI)); sys.path.insert(0, str(RACINE / "scripts"))
from loguru import logger                                           # noqa: E402
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


import patch_bundle_i18nfix as M                                    # noqa: E402
import _i18n_l1_aide as A                                           # noqa: E402
BUN = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
B = BUN.read_bytes().decode("utf-8")

print("\n[B] le bundle livré")
check("B1 le marqueur du maillon une seule fois, chaque remplacement une seule fois, plus aucune ancre",
      B.count(M.MARKER) == 1 and all(B.count(r) == 1 and B.count(a) == 0 for a, r in M.PAIRES))
check("B2 pastille de mode par dzT (publication auto / assisté), plus « auto-publish » ni « assisted » en dur",
      'children:e.mode==="auto"?dzT("scheduler.mode.auto"):dzT("scheduler.mode.assiste")' in B
      and '"auto-publish"' not in B and '?"auto":"assisted"})]}' not in B)
check("B3 pastille d'état : la valeur stockée passe par dzT(scheduler.etat.*), un état inconnu s'affiche tel quel",
      'draft:dzT("scheduler.etat.draft")' in B and 'scheduled:dzT("scheduler.etat.scheduled")' in B
      and '})[e.status]||e.status})' in B)
check("B4 les valeurs ENREGISTRÉES ne changent pas (status draft/scheduled, mode assisted)",
      'onChange:j=>s({status:j?"scheduled":"draft"})' in B and 'onChange:j=>s({mode:j?"auto":"assisted"})' in B)
check("B5 l'aperçu final demande sa langue au serveur (&lang=dzLang())",
      '/preview.png?channel=${ch}&lang=${dzLang()}&caption=' in B)
check("B6 l'exemple du Brief par dzT, plus en dur", 'placeholder:dzT("scheduler.plan.brief_exemple")' in B
      and "e.g. Week around the $DEEPOTUS" not in B)
check("B7 la langue des posts part de la langue de l'interface (toujours modifiable, valeurs EN/FR inchangées)",
      '[v,g]=x.useState(()=>dzLang()==="fr"?"FR":"EN")' in B and '{value:"EN",label:dzT("scheduler.plan.anglais")}' in B)
check("B8 compteurs figés : x.useState( 731, DzTracks 181", B.count("x.useState(") == 731 and B.count("DzTracks") == 181,
      (B.count("x.useState("), B.count("DzTracks")))
check("B9 aucun .bak_i18nfix laissé", not BUN.with_name(BUN.name + ".bak_i18nfix").exists())
r = subprocess.run(["node", "--check", str(BUN)], capture_output=True)
check("B10 node --check", r.returncode == 0, r.stderr.decode("utf-8", "replace")[-200:])

print("\n[I] l'inverse")
sans = A.avant_i18nfix(B)
check("I1 avant_i18nfix défait les paires : plus de marqueur", M.MARKER not in sans and '"assisted"})' in sans)
check("I2 l'aller-retour est exact à l'octet", M.appliquer(sans) == B)
check("I3 avant_avnoeuds défait D'ABORD i18nfix (posé après lui)", M.MARKER not in A.avant_avnoeuds(B))
check("I4 un bundle sans le maillon passe tel quel", A.avant_i18nfix(sans) == sans)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_i18nfix.py"), "--check"], capture_output=True,
                   text=True, cwd=str(RACINE))
check("I5 double application refusée", r.returncode != 0 and "double application" in (r.stdout + r.stderr), r.stdout + r.stderr)

print("\n[D] le dictionnaire")
DICO = {}
for f in (RACINE / "frontend" / "shared" / "i18n").glob("*.json"):
    DICO.update(json.loads(f.read_text("utf-8")))
utilisees = sorted(set(__import__("re").findall(r'dzT\("(scheduler\.(?:mode|etat|plan\.brief_exemple)[\w.]*)"\)',
                                                "".join(r for _a, r in M.PAIRES))))
check("D1 chaque clé posée par le maillon existe, fr et en non vides",
      len(utilisees) >= 10 and all(DICO.get(k, {}).get("fr") and DICO.get(k, {}).get("en") for k in utilisees),
      [k for k in utilisees if k not in DICO])
check("D2 états et modes en français dans fr (brouillon, programmé, assisté, publication auto)",
      DICO["scheduler.etat.draft"]["fr"] == "brouillon" and DICO["scheduler.etat.scheduled"]["fr"] == "programmé"
      and DICO["scheduler.mode.assiste"] == {"fr": "assisté", "en": "assisted"}
      and DICO["scheduler.mode.auto"]["en"] == "auto-publish")
check("D3 l'aide des Comptes dit « Réglages → Comptes connectés » en français, « Connected accounts » en anglais",
      "Réglages → Comptes connectés" in DICO["scheduler.comptes.aide"]["fr"]
      and "Connected accounts" not in DICO["scheduler.comptes.aide"]["fr"]
      and "Settings → Connected accounts" in DICO["scheduler.comptes.aide"]["en"])
check("D4 l'exemple du Brief en français dans fr, l'exemple d'origine dans en",
      DICO["scheduler.plan.brief_exemple"]["fr"].startswith("ex. Semaine autour du lancement")
      and DICO["scheduler.plan.brief_exemple"]["en"].startswith("e.g. Week around the $DEEPOTUS"))
dico_js = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text("utf-8")
check("D5 le dictionnaire assemblé porte les clés (assembleur rejoué)", all(f'"{k}"' in dico_js for k in utilisees))

print("\n[S] le serveur")
PY = sys.executable
r = subprocess.run([PY, str(RACINE / "scripts" / "i18n_planif_news_serveur.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
check("S1 i18n_planif_news_serveur --check : messages.json à jour, fr = texte des sources", r.returncode == 0,
      r.stdout + r.stderr)
r = subprocess.run([PY, str(RACINE / "scripts" / "i18n_l4_serveur.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
check("S2 … et i18n_l4_serveur --check reste vrai (les deux générateurs se rejouent l'un après l'autre)",
      r.returncode == 0, r.stdout + r.stderr)

from app.i18n import planif_news as PN                             # noqa: E402
from app.services import news_filter, news_rank, news_trends, news_voice, post_preview, quota  # noqa: E402
_n, motif = news_rank.score_deterministe({"title": "storm whale", "doublons": [1, 2]}, ["storm"])
check("S3 motif du score accentué en français", motif == "brief : storm ; 2 média(s) sur le même sujet", motif)
check("S4 … et traduit bout par bout en anglais (malus compris)",
      PN.motif(motif + " ; -6 source sur-représentée", "en")
      == "brief: storm ; 2 outlet(s) on the same story ; -6 over-represented source")
check("S5 « aucun signal, socle seulement » / « hors brief : moitié des points »",
      PN.motif("aucun signal, socle seulement", "en") == "no signal, base points only"
      and PN.motif("article lisible ; hors brief : moitié des points", "en") == "readable article ; off-brief: half the points")
check("S6 une raison inconnue (rendue par un modèle) reste telle quelle ; fr et langue inconnue = texte d'origine",
      PN.motif("coeur du brief", "en") == "coeur du brief" and PN.motif(motif, "fr") is motif and PN.motif(motif, "de") is motif)
check("S7 motifs du filtre accentués et traduits",
      PN.texte("hors fenêtre de fraîcheur", "en") == "outside the freshness window"
      and PN.texte("hors mots-clés", "en") == "no keyword match"
      and "hors mots-clés" in (RACINE / "backend" / "app" / "services" / "news_filter.py").read_text("utf-8"))
check("S8 tendances : « Réglages → Comptes connectés », et en anglais « Settings → Connected accounts »",
      news_trends.MOTIF_CLE == "aucune clé X configurée (Réglages → Comptes connectés)"
      and PN.texte(news_trends.MOTIF_CLE, "en") == "no X key configured (Settings → Connected accounts)")
q = "quota x_lecture : 98/100 ce mois, un appel peut lire 10 posts (" + quota.LIMITS["x_lecture"][2] + ")"
check("S9 un motif qui cite la source d'un quota : la source est traduite aussi",
      PN.texte(q, "en") == "x_lecture quota: 98/100 this month, one call can read 10 posts "
                           "(X free tier: 100 reads/month (docs.x.com, 09/03/2026))", PN.texte(q, "en"))
check("S10 voix : « mode par défaut » et « mots du sujet : … »",
      PN.texte("aucun mot du sujet ne tranche, mode par défaut", "en") == "no topic word decides, default mode"
      and PN.texte("mots du sujet : pump, whale", "en") == "topic words: pump, whale")

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
EN = {"Accept-Language": "en-US,en;q=0.9"}
FR = {"Accept-Language": "fr-FR,fr;q=0.9"}
with TestClient(app, client=("127.0.0.1", 5)) as c:
    qfr, qen, q0 = c.get("/api/schedule/quotas", headers=FR).json(), c.get("/api/schedule/quotas", headers=EN).json(), \
        c.get("/api/schedule/quotas").json()
    check("S11 /schedule/quotas : la source en français sans en-tête et en français",
          q0["x"]["source"] == qfr["x"]["source"] == "palier gratuit X : 500 posts/mois (docs.x.com, 03/09/2026)")
    check("S12 … en anglais avec Accept-Language: en, chiffres et canaux inchangés",
          qen["x"]["source"] == "X free tier: 500 posts/month (docs.x.com, 09/03/2026)"
          and {k: (v["used"], v["limit"], v["period"]) for k, v in qen.items()}
          == {k: (v["used"], v["limit"], v["period"]) for k, v in qfr.items()}
          and all(not v["source"].startswith(("palier", "Instagram : ")) for v in qen.values()), qen)
    ffr, fen = c.get("/api/news/forms", headers=FR).json()["forms"], c.get("/api/news/forms", headers=EN).json()["forms"]
    check("S13 /news/forms : noms accentués en français (Cartes animées, Plans vidéo, Avatar présentateur)",
          [f["label"] for f in ffr][:4] == ["Cartes animées (gratuit)", "Illustration IA par titre", "Plans vidéo par sujet",
                                            "Avatar présentateur"], [f["label"] for f in ffr])
    check("S14 … en anglais (nom et description), ids et disponibilité inchangés",
          [f["label"] for f in fen][0] == "Animated cards (free)" and fen[2]["description"].startswith("one shot generated")
          and [(f["id"], f["disponible"], f["payant"]) for f in fen] == [(f["id"], f["disponible"], f["payant"]) for f in ffr])
    tr = c.get("/api/news/trends", params={"x_query": "deepotus"}, headers=EN).json()
    check("S15 /news/trends sans clé X : motif en anglais", (tr.get("x") or {}).get("motif")
          == "no X key configured (Settings → Connected accounts)", tr)
    tr = c.get("/api/news/trends", params={"x_query": "deepotus"}, headers=FR).json()
    check("S16 … et en français accentué", (tr.get("x") or {}).get("motif") == news_trends.MOTIF_CLE, tr)
    p = c.post("/api/schedule", json={"title": "t", "caption": "Bonjour", "channels": ["instagram"],
                                      "run_at": "2030-01-01T10:00:00Z", "status": "draft", "mode": "assisted"}).json()
    pid = (p or {}).get("id")
    imgs = {lg: c.get(f"/api/schedule/{pid}/preview.png", params={"channel": "instagram", "lang": lg}) for lg in ("fr", "en")}
    sans_lang = c.get(f"/api/schedule/{pid}/preview.png", params={"channel": "instagram"})
    check("S17 aperçu PNG : rendu dans les deux langues, et différent (le bandeau et le visuel absent sont dessinés)",
          bool(pid) and all(r.status_code == 200 and r.headers["content-type"] == "image/png" for r in imgs.values())
          and imgs["fr"].content != imgs["en"].content, str(p)[:200])
    check("S18 sans `lang` : la langue d'installation (UI_LANG, fr par défaut)", sans_lang.content == imgs["fr"].content)

from PIL import Image                                               # noqa: E402
from app.i18n import msg                                            # noqa: E402
check("S19 gabarits de l'aperçu : « zones indicatives · N car. » / « approximate safe zones · N chars »",
      msg("apercu.zones", "fr", reseau="Reels", n=5) == "Reels · zones indicatives · 5 car."
      and msg("apercu.zones", "en", reseau="Reels", n=5) == "Reels · approximate safe zones · 5 chars")
im = Image.open(io.BytesIO(post_preview.render_preview(channel="x", caption="x", hero_path=None, lang="en")))
check("S20 render_preview accepte lang pour X et Telegram", im.size[0] == 680 and Image.open(io.BytesIO(
    post_preview.render_preview(channel="telegram", caption="x", hero_path=None, lang="en"))).size[0] == 680)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
