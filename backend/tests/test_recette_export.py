# -*- coding: utf-8 -*-
"""t346 (29/10/2026, D2 du lot Scenario) — EXPORTER la recette : un ZIP « skill » (SKILL.md au format des skills
Claude + fabrication.pdf illustré + recette.json + images réduites), pour un RENDU (job), un PLAN (agrège ses jobs,
previs comprise) ou un ASSET de la Bibliothèque (remonte sa lignée). Gratuit, local, sans aucune clé dans l'archive.

[A] rendu : ZIP, SKILL.md (frontmatter name/description, prompt exact, modèle + endpoint, graine, paramètres, coûts
    réel contre estimé, essais rejetés du même lot, provenance), PDF multi-pages, images d'entrée réduites.
[B] plan : croquis, image de production, previs (endpoint, conform, dérive), raté (erreur), coûts agrégés.
[C] asset : la lignée remontée, racine d'abord (mère → fille), recettes de la Bibliothèque.
[D] AUCUN secret : clé du coffre/des réglages, champ api_key, jeton d'URL, en-tête Bearer, chemin local.
[E] refus : 400 type inconnu, 404 introuvable ; anglais ; aperçu JSON ; aucune ligne de dépense écrite.
[F] agent interne : outil `lire_recette` (lecture, sans dépense) dans une boîte de l'agent Campagnes.
[G] écran : bouton « Exporter la recette » (fiche Bibliothèque, boîte Previs → plan), textes FR/EN.
Run : & $PY tests/test_recette_export.py   (depuis backend/)
"""
import asyncio, io, json, os, re, sys, tempfile, pathlib, zipfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzt346_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ.pop(k, None)
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


from datetime import datetime, timedelta                    # noqa: E402
from PIL import Image                                       # noqa: E402
from fastapi.testclient import TestClient                   # noqa: E402
from app.main import app                                    # noqa: E402
from app.config import settings                             # noqa: E402
from app.services.storage import (JobRecord, Shot, Chapter, LibraryAsset, Depense,   # noqa: E402
                                  async_session_factory)

SECRET = "fal-7f3c2a91-secret-0b8d4e6f1a2c3d4e5f60718293a4b5c6"
JETON = "tok3nS3cr3tQuiNeDoitPasSortir"
BEARER = "Bearer abcdefghijklmnopqrstuvwxyz0123456789"
PROMPT = ("The giant bioluminescent jellyfish pulses and glides upward, city lights flicker below, slow epic camera "
          "rise, cinematic")
PROMPT_PREVIS = "@Video1 gives the motion and timing; @Image1 gives the look. A red car drifts at sunset."
D = datetime(2026, 10, 28, 10, 0, 0)


def img(nom, couleur=(200, 80, 40), taille=(1200, 2000)):
    p = settings.images_path / nom
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", taille, couleur).save(p)
    return p


async def semer():
    async with async_session_factory() as s:
        # [A] un rendu Seedance, son essai rejeté du même lot, deux lignes de dépense (une réelle)
        s.add(JobRecord(id="job-ok", status="done", progress=100, title="Méduse géante", image_filename="gen_dep.png",
                        final_prompt=PROMPT, negative_prompt="no morphing", seed=482831877, duration_s=5,
                        aspect_ratio="9:16", style="cinematic", provider="seedance", video_model="seedance-2.5",
                        batch_id="lot-1", batch_index=0, batch_size=2, created_at=D,
                        cost_meta=json.dumps({"usd": 0.61, "authorization": BEARER})))
        s.add(JobRecord(id="job-ok-b", status="failed", progress=40, title="Méduse géante (essai 2)",
                        image_filename="gen_dep.png", final_prompt=PROMPT, seed=11, duration_s=5, provider="seedance",
                        video_model="seedance-2.5", batch_id="lot-1", batch_index=1, batch_size=2,
                        error=f"fal 500 : upstream timeout ({BEARER})", created_at=D + timedelta(seconds=5)))
        s.add(Depense(quand=D, mois="2026-10", moteur="fal", categorie="quick", op="video", estime_usd=0.61,
                      reel_usd=0.55, ref="job-ok"))
        # [B] un plan : croquis, image de production, previs réussie (rattachée) + previs ratée
        s.add(Chapter(id="chap-1", title="La poursuite"))
        s.add(Shot(id="shot-1", chapter_id="chap-1", idx=3, action="Une voiture rouge dérape au couchant",
                   sketch_image="croquis.png", sketch_seed=7, image="prod.png", prompt="Shot: wide, red car, sunset",
                   motion_prompt="the car drifts left", keyframe_image="plateau_debut.png", video="job-previs",
                   duration_s=4.0))
        s.add(JobRecord(id="job-previs", status="done", progress=100, title="Previs → plan · Une voiture rouge",
                        image_filename="prod.png", final_prompt=PROMPT_PREVIS, video_model="seedance-2.5-v2v",
                        provider="previs", seed=99, duration_s=4, aspect_ratio="9:16", created_at=D + timedelta(hours=1),
                        final_video_path=str(pathlib.Path(TMP) / "outputs" / "previs_out.mp4"),
                        cost_meta=json.dumps({"usd": 1.2, "kind": "video_refs", "modele": "seedance-2.5-v2v",
                                              "plan": "shot-1",
                                              "conform": {"mode": "etirer", "facteur": 1.33},
                                              "recalage": {"derive_images": 1, "fiable": True, "images": 96,
                                                           "fps": 24, "score": 0.91,
                                                           "phrase": "dérive d'une image"}})))
        s.add(JobRecord(id="job-previs-rate", status="failed", progress=5, title="Previs → plan · Une voiture rouge",
                        image_filename="prod.png", final_prompt=PROMPT_PREVIS, video_model="seedance-2.5-v2v",
                        provider="previs", created_at=D + timedelta(minutes=30),
                        error="fal : 422 clip trop court",
                        cost_meta=json.dumps({"usd": 1.2, "kind": "video_refs", "plan": "shot-1"})))
        s.add(Depense(quand=D, mois="2026-10", moteur="fal", categorie="chapitres", op="video_refs", estime_usd=1.2,
                      reel_usd=1.1, ref="shot-1"))
        s.add(Depense(quand=D, mois="2026-10", moteur="fal", categorie="chapitres", op="video_refs", estime_usd=1.2,
                      ref="shot-1"))
        s.add(LibraryAsset(filename="previs_out.mp4", source="atelier", kind="video", job_id="job-previs",
                           parent_filename="clip.mp4", relation="previs",
                           recette=json.dumps({"modele": "seedance-2.5-v2v",
                                               "endpoint": "bytedance/seedance-2.5/reference-to-video",
                                               "prompt": PROMPT_PREVIS, "tache": "editing", "resolution": "720p",
                                               "clip": "clip.mp4", "style_frames": ["prod.png"], "plan": "shot-1",
                                               "arguments": {"prompt": PROMPT_PREVIS, "api_key": SECRET,
                                                             "video_url": f"https://v3.fal.media/files/c.mp4?token={JETON}"},
                                               "notes": [f"chemin C:\\Users\\olivi\\AppData\\Local\\x\\clip.mp4", f"envoyé avec {SECRET}"],
                                               "usd": 1.2, "seed": 99})))
        s.add(LibraryAsset(filename="prod.png", source="atelier", kind="image"))
        # [C] une lignée : mere.png (générateur, recette) → fille.png (upscale)
        s.add(LibraryAsset(filename="mere.png", source="generation", kind="image",
                           recette=json.dumps({"prompt": "a lighthouse in a storm, oil painting", "model": "flux",
                                               "seed": 42, "size": "portrait_16_9", "token": JETON})))
        s.add(LibraryAsset(filename="fille.png", source="retouche", kind="image", parent_filename="mere.png",
                           relation="upscale"))
        await s.commit()


async def nb_depenses():
    from sqlalchemy import select, func
    async with async_session_factory() as s:
        return (await s.execute(select(func.count()).select_from(Depense))).scalar()


def zip_de(r):
    try:
        return zipfile.ZipFile(io.BytesIO(r.content))
    except zipfile.BadZipFile:
        return None


def fichier(z, fin):
    if z is None:
        return None
    for n in z.namelist():
        if n.endswith(fin):
            return z.read(n)
    return None


def texte_pdf(octets):
    from pypdf import PdfReader
    rd = PdfReader(io.BytesIO(octets))
    return len(rd.pages), "\n".join((p.extract_text() or "") for p in rd.pages)


def tout_texte(z):
    """Tout le texte de l'archive : SKILL.md, recette.json, le texte du PDF et ses octets bruts."""
    out = []
    for n in z.namelist():
        b = z.read(n)
        if n.endswith(".pdf"):
            out.append(texte_pdf(b)[1])
            out.append(b.decode("latin-1"))
        elif n.endswith((".md", ".json", ".txt")):
            out.append(b.decode("utf-8"))
    return "\n".join(out)


with TestClient(app) as c:
    asyncio.run(semer())
    for n in ("gen_dep.png", "croquis.png", "prod.png", "plateau_debut.png", "mere.png", "fille.png"):
        img(n)
    settings.FAL_KEY = SECRET                                 # une clé RÉELLEMENT posée : elle ne doit pas sortir
    avant = asyncio.run(nb_depenses())

    print("\n[A] rendu (job)")
    r = c.get("/api/recettes/export", params={"type": "job", "id": "job-ok"})
    check("A1 200 + application/zip + pièce jointe .zip", r.status_code == 200
          and r.headers.get("content-type", "").startswith("application/zip")
          and ".zip" in r.headers.get("content-disposition", ""), f"{r.status_code} {r.text[:200]}")
    z = zip_de(r) if r.status_code == 200 else None
    noms = z.namelist() if z else []
    racines = {n.split("/")[0] for n in noms}
    check("A2 un seul dossier racine (le nom du skill)", len(racines) == 1, noms[:6])
    skill = (fichier(z, "/SKILL.md") or b"").decode("utf-8") if z else ""
    check("A3 SKILL.md, fabrication.pdf, recette.json présents", z and fichier(z, "/SKILL.md")
          and fichier(z, "/fabrication.pdf") and fichier(z, "/recette.json"), noms)
    fm = re.match(r"^---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---\n", skill)
    check("A4 frontmatter des skills Claude (name puis description)", bool(fm), skill[:200])
    if fm:
        check("A5 name : minuscules, chiffres, tirets, ≤ 64, = dossier racine",
              re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm.group(1)) and len(fm.group(1)) <= 64
              and fm.group(1) in racines, fm.group(1))
        check("A6 description : 1 à 1024 caractères, dit quand l'utiliser", 0 < len(fm.group(2)) <= 1024
              and "seedance-2.5" in fm.group(2).lower(), fm.group(2))
    check("A7 le prompt EXACT, dans un bloc", "```text\n" + PROMPT + "\n```" in skill)
    check("A8 modèle + endpoint fal", "seedance-2.5" in skill and "bytedance/seedance-2.5/image-to-video" in skill)
    check("A9 graine et paramètres (durée, format, négatif)", "482831877" in skill and "9:16" in skill
          and "no morphing" in skill and "5 s" in skill)
    check("A10 coûts : réel 0,55 $ contre estimé 0,61 $", "0.55" in skill and "0.61" in skill)
    check("A11 essai rejeté du même lot, avec son erreur", "job-ok-b" in skill and "upstream timeout" in skill)
    check("A12 provenance de l'image d'entrée", "gen_dep.png" in skill)
    img_zip = [n for n in noms if "/images/" in n]
    check("A13 l'image d'entrée réduite (JPEG ≤ 1024 px)", img_zip and all(
        max(Image.open(io.BytesIO(z.read(n))).size) <= 1024 for n in img_zip), img_zip)
    pdf = fichier(z, "/fabrication.pdf") if z else None
    if pdf:
        n_pages, txt = texte_pdf(pdf)
        check("A14 PDF multi-pages, illustré (une image au moins)", pdf[:5] == b"%PDF-" and n_pages >= 2
              and b"/DCTDecode" in pdf, n_pages)
        check("A15 PDF : chronologie et coûts", "482831877" in txt and "0.55" in txt and "seedance-2.5" in txt, txt[:300])
    rj = json.loads((fichier(z, "/recette.json") or b"{}").decode("utf-8")) if z else {}
    check("A16 recette.json : type job, étapes, coûts", rj.get("type") == "job" and rj.get("etapes")
          and rj.get("couts", {}).get("etat") == "reel", str(rj)[:300])

    print("\n[B] plan")
    r = c.get("/api/recettes/export", params={"type": "plan", "id": "shot-1"})
    check("B1 200", r.status_code == 200, r.text[:200])
    zb = zip_de(r) if r.status_code == 200 else None
    sb = (fichier(zb, "/SKILL.md") or b"").decode("utf-8") if zb else ""
    rb = json.loads((fichier(zb, "/recette.json") or b"{}").decode("utf-8")) if zb else {}
    check("B2 titre : chapitre + plan", "La poursuite" in sb and "Une voiture rouge" in sb)
    check("B3 étapes croquis → image de production → previs (ordre)", [e.get("genre") for e in rb.get("etapes", [])][:3]
          == ["croquis", "image", "previs"], [e.get("genre") for e in rb.get("etapes", [])])
    check("B4 previs : endpoint, prompt exact, tâche, résolution, graine",
          "bytedance/seedance-2.5/reference-to-video" in sb and PROMPT_PREVIS in sb and "editing" in sb
          and "720p" in sb and "99" in sb)
    check("B5 conform et dérive mesurée", "etirer" in sb and "1.33" in sb and "dérive" in sb.lower())
    check("B6 le raté : job-previs-rate et son erreur", "job-previs-rate" in sb and "clip trop court" in sb
          and any(x.get("job_id") == "job-previs-rate" for x in rb.get("rates", [])), rb.get("rates"))
    cb = rb.get("couts", {})
    check("B7 coûts agrégés : estimé 2,4 $, réel 1,1 $, réel partiel", abs((cb.get("estime_usd") or 0) - 2.4) < 1e-6
          and abs((cb.get("reel_usd") or 0) - 1.1) < 1e-6 and cb.get("etat") == "reel-partiel", cb)
    check("B8 entrées : croquis (graine 7), borne du Plateau, style frame", "croquis.png" in sb
          and "plateau_debut.png" in sb and "prod.png" in sb)

    print("\n[C] asset (lignée)")
    r = c.get("/api/recettes/export", params={"type": "asset", "id": "fille.png"})
    check("C1 200", r.status_code == 200, r.text[:200])
    zc = zip_de(r) if r.status_code == 200 else None
    sc = (fichier(zc, "/SKILL.md") or b"").decode("utf-8") if zc else ""
    rc = json.loads((fichier(zc, "/recette.json") or b"{}").decode("utf-8")) if zc else {}
    fic = [e.get("fichier") for e in rc.get("etapes", [])]
    check("C2 racine d'abord : mere.png puis fille.png", fic == ["mere.png", "fille.png"], fic)
    check("C3 recette de la mère : prompt, modèle, graine", "a lighthouse in a storm, oil painting" in sc
          and "flux" in sc and "42" in sc)
    check("C4 relation de la fille (upscale)", "upscale" in sc)
    r = c.get("/api/recettes/export", params={"type": "asset", "id": "previs_out.mp4"})
    check("C5 asset vidéo de la Bibliothèque : remonte à son job (previs)", r.status_code == 200
          and PROMPT_PREVIS in (fichier(zip_de(r), "/SKILL.md") or b"").decode("utf-8"), r.text[:200])

    print("\n[D] aucun secret dans l'archive")
    for nom, zz in (("job", z), ("plan", zb), ("asset", zc)):
        t = tout_texte(zz) if zz else ""
        check(f"D1 {nom} : la clé posée dans les réglages n'y est pas", t and SECRET not in t)
        check(f"D2 {nom} : ni jeton d'URL ni en-tête Bearer", t and JETON not in t and BEARER not in t
              and "abcdefghijklmnopqrstuvwxyz0123456789" not in t)
        check(f"D3 {nom} : aucun champ api_key / token / authorization",
              t and not re.search(r'"(api_key|token|authorization)"', t))
        check(f"D4 {nom} : aucun chemin local (dossier de l'utilisateur)", t and "C:\\Users" not in t
              and "olivi" not in t and TMP not in t)

    print("\n[E] refus, anglais, aperçu, gratuité")
    check("E1 type inconnu : 400", c.get("/api/recettes/export", params={"type": "x", "id": "a"}).status_code == 400)
    for t_, i_ in (("job", "nope"), ("plan", "nope"), ("asset", "nope.png")):
        check(f"E2 {t_} introuvable : 404", c.get("/api/recettes/export", params={"type": t_, "id": i_}).status_code == 404)
    check("E3 nom d'asset hors du magasin refusé", c.get("/api/recettes/export",
          params={"type": "asset", "id": "../t.db"}).status_code in (400, 404))
    r = c.get("/api/recettes/export", params={"type": "job", "id": "job-ok", "lang": "en"})
    se = (fichier(zip_de(r), "/SKILL.md") or b"").decode("utf-8") if r.status_code == 200 else ""
    check("E4 anglais : titres de sections en anglais", "## Steps" in se and "## Costs" in se and "## Étapes" not in se,
          se[:300])
    r = c.get("/api/recettes/apercu", params={"type": "plan", "id": "shot-1"})
    ja = r.json() if r.status_code == 200 else {}
    check("E5 aperçu JSON : nom, étapes, coûts, texte du SKILL.md", ja.get("nom") and ja.get("etapes")
          and ja.get("couts") and "---\nname:" in (ja.get("skill_md") or ""), str(ja)[:200])
    check("E6 aperçu : aucun secret", SECRET not in r.text and JETON not in r.text)
    check("E7 gratuit : aucune ligne de dépense écrite", asyncio.run(nb_depenses()) == avant)

    print("\n[F] agent interne : lire_recette")
    from app.services import agent_outils as AO, agent_boites as AB
    o = AO.OUTILS.get("lire_recette")
    check("F1 outil lire_recette, nature lecture", o and o.get("nature") == "lecture")
    check("F2 registre des boîtes sain", AB.verifier() == [], AB.verifier())
    check("F3 visible de l'agent Campagnes", "lire_recette" in AB.outils_pour("campagnes"))
    ctx = AO.Ctx(cid="c1", agent="campagnes")
    if ctx is not None:
        res = asyncio.run(AO.executer("lire_recette", {"type": "plan", "id": "shot-1"}, ctx))
        check("F4 lecture : ok, étapes et coûts, lien d'export", res.get("ok") and "previs" in json.dumps(res, ensure_ascii=False)
              and "/api/recettes/export" in json.dumps(res), str(res)[:300])
        check("F5 aucun secret rendu au modèle", SECRET not in AO.pour_modele(res) and JETON not in AO.pour_modele(res))
        res = asyncio.run(AO.executer("lire_recette", {"type": "job", "id": "inconnu"}, ctx))
        check("F6 introuvable : refus lisible", res.get("ok") is False and res.get("resume"), str(res)[:200])
    check("F7 aucune ligne de dépense écrite par l'outil", asyncio.run(nb_depenses()) == avant)

print("\n[G] écran")
SRC = (REPO / "frontend" / "patches" / "recette.js").read_text(encoding="utf-8")
B = (REPO / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
check("G1 la source porte DzRecetteExport (lien /api/recettes/export, langue de l'écran)",
      "function DzRecetteExport(" in SRC and "/api/recettes/export?type=" in SRC and "dzLang" in SRC)
check("G2 aucun x.useState( direct dans la source", "x.useState(" not in SRC)
check("G3 le bundle monte le bouton dans la fiche, après le panneau de recette",
      "r.jsx(DzRecetteRendu,{m:m,fermer:()=>y(null)}),r.jsx(DzRecetteExport,{m:m})," in B)
check("G4 bundle : comptes figés (x.useState( 731, confirmations ×30)",
      B.count("x.useState(") == 731 and B.count("await window.__dzDialogue.confirmer(") == 30)
import patch_bundle_dzrecette as PR                         # noqa: E402
check("G5 maillon dzrecette : aller-retour exact", lambda: PR.appliquer(PR.defaire(B)) == B)
PV = (REPO / "frontend" / "shared" / "dz-previs-plan.js").read_bytes()
check("G6 boîte Previs → plan : lien « Exporter la recette du plan »", b"/api/recettes/export?type=plan" in PV
      and b"previs.export" in PV)
check("G7 copie dist/shared identique", PV == (REPO / "frontend" / "dist" / "shared" / "dz-previs-plan.js").read_bytes())
DICO = {}
for f in ("recette.json", "previs.json"):
    DICO.update(json.loads((REPO / "frontend" / "shared" / "i18n" / f).read_text(encoding="utf-8")))
cles = set(re.findall(r'"(recette\.export\.[a-z0-9_]+)"', SRC)) | set(
    re.findall(r'"(previs\.export\.[a-z0-9_]+)"', PV.decode("utf-8")))
check("G8 clés neuves traduites FR et EN (trois segments)", cles and all(
    k.count(".") == 2 and DICO.get(k, {}).get("fr") and DICO.get(k, {}).get("en") for k in cles),
    sorted(k for k in cles if k not in DICO))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
