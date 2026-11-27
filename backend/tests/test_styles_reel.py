# -*- coding: utf-8 -*-
"""t503 (lot G13 « Styles de reel », 26/11/2026) — la BIBLIOTHÈQUE DE STYLES DE REEL NOMMÉS.

Un style = une RECETTE au-dessus de briques qui existent déjà : un gabarit Templates intégré, une ou plusieurs pages
motion code (fiches de style maison de la bibliothèque motion), une voix (synthèse ou avatar), une humeur de musique,
un préréglage de sous-titres, un rythme. Données versionnées : backend/app/styles_reel/<id>.json, FR et EN.
Service : app.services.styles_reel ; routes : GET /api/styles-reel… (lecture et devis GRATUIT, rien de payant).

  [D] données     6 à 10 styles, un fichier par style, verifier() == [] sur le dépôt, familles génériques ;
  [G] garde       aucun nom de style ni de marque de la référence étudiée (empreintes seulement, jamais le texte) ;
  [R] rouge       sur des copies d'essai dans un dossier temporaire, chaque écart est signalé : gabarit absent,
                  emplacement inconnu ou oublié, page motion absente, style motion absent, champ inconnu, valeur hors
                  liste, nombre hors bornes, champ texte, curseur, voix, balise, humeur, modèle de musique,
                  préréglage de sous-titres, durée hors bornes du motion code, parité FR/EN, id ≠ fichier ;
  [S] service     lister_styles / style : langue, repli, inconnu -> None, chemin refusé ;
  [Q] devis       devis_style : lignes voix / avatar / musique / motion code / rendus locaux, total = la somme
                  chiffrée par pricing.estimate, durée bornée au style, moteur local gratuit, AUCUN appel au moteur ;
  [H] routes      GET seulement, locales seulement, 404, langue de la requête ;
  [A] agent       outil `styles_reel_lire` dans la boîte « styles_reel » de l'agent « mcp » SEULEMENT ; l'agent
                  Campagnes inchangé à l'octet (fixture agent_definitions_campagnes.json) ;
  [E] erreurs     messages levés traduits (scripts/i18n_l10_traductions.json, --check vert) ; AGENTS.md.
Données isolées (DEEPOTUS_DATA_DIR temporaire), clés vidées, rien de payé.
Run (depuis backend/) : & $PY tests/test_styles_reel.py"""
import asyncio
import copy
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzstyles_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _d in ("images", "outputs"):
    (_tmp / _d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
           "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY"):
    os.environ[_k] = ""
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def main() -> int:
    from app.services import styles_reel as SR                          # noqa: E402
    from app.services import pricing                                    # noqa: E402
    from app.services import moteurs_texte as MT                        # noqa: E402
    from app.services.template_service import TemplateEngine            # noqa: E402

    DOSSIER = RACINE / "backend" / "app" / "styles_reel"

    # ── [D] données ───────────────────────────────────────────────────────────────────────────────────────────────────
    print("[D] données du dépôt")
    fichiers = sorted(DOSSIER.glob("*.json")) if DOSSIER.is_dir() else []
    check("D1 entre 6 et 10 styles, un fichier par style", 6 <= len(fichiers) <= 10, len(fichiers))
    bruts = [json.loads(p.read_text(encoding="utf-8")) for p in fichiers]
    check("D2 verifier() == [] sur le dépôt", SR.verifier() == [], SR.verifier()[:8])
    check("D3 chaque id = nom du fichier", all(b.get("id") == p.stem for b, p in zip(bruts, fichiers)))
    familles = {b.get("famille") for b in bruts}
    check("D4 au moins 5 familles distinctes, toutes connues", len(familles) >= 5 and familles <= set(SR.FAMILLES),
          familles)
    check("D5 chaque famille a un libellé FR et EN", all(SR.FAMILLES[f].get("fr") and SR.FAMILLES[f].get("en")
                                                         for f in SR.FAMILLES))
    check("D6 un style avec avatar, un sans visage, un à plusieurs pages motion",
          any(b.get("voix", {}).get("moteur") == "avatar" for b in bruts)
          and any(b.get("voix", {}).get("moteur") == "tts" for b in bruts)
          and any(len(b.get("motion") or {}) >= 2 for b in bruts))
    tpl = TemplateEngine()
    check("D7 chaque gabarit cité est un gabarit INTÉGRÉ de Templates",
          all(tpl.is_builtin(b["gabarit"]["id"]) for b in bruts if b.get("gabarit")))

    # ── [G] garde anti-copie ──────────────────────────────────────────────────────────────────────────────────────────
    print("[G] aucun nom de la référence")


    def _norm(t: str) -> list:
        t = unicodedata.normalize("NFKD", t)
        t = "".join(c for c in t if not unicodedata.combining(c)).lower()
        return re.findall(r"[a-z0-9]+", t)


    def _h(jetons) -> str:
        return hashlib.sha256(("dzstyles|" + " ".join(jetons)).encode()).hexdigest()[:16]


    # empreintes (sha256 tronqué) des 18 noms de styles relevés, de la marque et de ses slogans — jamais le texte
    EMPREINTES = {'4a85894fc3f17a3e', 'd9172578e1b8f56b', '20ced89ad39e465a', 'eea62f7a3fa9fd0e', 'e866390c475618b2',
                  '3e24bfefb0857dbb', 'f1790e189a621bd8', '07d2980f53feda37', 'd7ed1eaa417a59dc', '50ecbf4e0d4525c9',
                  '89218f4276a84514', 'c2d91ce6db9db6b1', 'cfa25365b66a166b', 'a4a108c7de8b6d4d', '078b6350f1e05fbd',
                  'a687a8567145781e', '9194832a8f973884', 'a607e98fb5363352', '4e0a31595ab7bc0f', 'c0a2db9f9f47dc45',
                  '55eaf0f0a8e6679d', 'fb91d11720053937'}


    def _touches(texte: str) -> list:
        j = _norm(texte)
        return [" ".join(j[i:i + n]) for n in (1, 2, 3) for i in range(len(j) - n + 1) if _h(j[i:i + n]) in EMPREINTES]


    for p in fichiers + [RACINE / "backend" / "app" / "services" / "styles_reel.py"]:
        check(f"G1 {p.name} ne cite aucun nom de la référence", not _touches(p.read_text(encoding="utf-8")),
              len(_touches(p.read_text(encoding="utf-8"))))
    check("G2 la garde attrape un témoin (empreinte connue)", bool(_touches("un style " + "tier" + " " + "list" + " ici")))

    # ── [R] règles, sur des copies d'essai ────────────────────────────────────────────────────────────────────────────
    print("[R] chaque écart est signalé")
    modele = next(b for b in bruts if b.get("gabarit") and b.get("voix", {}).get("moteur") == "tts"
                  and any(c for pg in (b.get("motion") or {}).values() for c in (pg.get("champs") or {})))


    def essai(mut) -> list:
        d = pathlib.Path(tempfile.mkdtemp(prefix="dzstyles_essai_", dir=_tmp))
        b = copy.deepcopy(modele)
        nom = mut(b) or b.get("id")
        (d / f"{nom}.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
        return SR.verifier(d)


    check("R0 la copie intacte passe", essai(lambda b: None) == [], essai(lambda b: None))
    _page = next(iter(modele["motion"]))
    _slot = next(iter(modele["gabarit"]["emplacements"]))
    _champ = next(iter(modele["motion"][_page].get("champs") or {}))


    def _m(f):
        def g(b):
            f(b)
        return g


    CAS = [
        ("id ≠ nom du fichier", lambda b: "autre-nom"),
        ("famille inconnue", _m(lambda b: b.update(famille="inconnue"))),
        ("titre EN manquant", _m(lambda b: b["titre"].pop("en"))),
        ("résumé FR vide", _m(lambda b: b["resume"].update(fr=""))),
        ("à fournir vide", _m(lambda b: b.update(a_fournir=[]))),
        ("gabarit absent", _m(lambda b: b["gabarit"].update(id="tpl_qui_n_existe_pas"))),
        ("emplacement inconnu", _m(lambda b: b["gabarit"]["emplacements"].update(inconnu={"source": "fournir"}))),
        ("emplacement oublié", _m(lambda b: b["gabarit"]["emplacements"].pop(_slot))),
        ("source inconnue", _m(lambda b: b["gabarit"]["emplacements"][_slot].update(source="magie"))),
        ("page motion absente", _m(lambda b: [e.update(page="nulle") for e in b["gabarit"]["emplacements"].values()
                                              if e.get("source") == "motion"])),
        ("style motion absent", _m(lambda b: b["motion"][_page].update(style="style-inexistant"))),
        ("champ motion inconnu", _m(lambda b: b["motion"][_page].setdefault("champs", {}).update(zzz=1))),
        ("curseur inconnu", _m(lambda b: b["motion"][_page].update(curseurs={"vitesse": 2}))),
        ("curseur hors bornes", _m(lambda b: b["motion"][_page].update(curseurs={"rythme": 9}))),
        ("modèle de voix inconnu", _m(lambda b: b["voix"].update(modele="voix_inventee"))),
        ("balise de voix inconnue", _m(lambda b: b["voix"].update(balises=["[danse]"]))),
        ("stabilité hors des trois valeurs", _m(lambda b: b["voix"].update(stabilite=0.3))),
        ("moteur de voix inconnu", _m(lambda b: b["voix"].update(moteur="telepathie"))),
        ("avatar sans voix d'avatar", _m(lambda b: b["gabarit"]["emplacements"][_slot].update(source="avatar"))),
        ("humeur de musique inconnue", _m(lambda b: b.update(musique={"humeur": "polka", "modele": "lyria3"}))),
        ("modèle de musique inconnu", _m(lambda b: b.update(musique={"humeur": "hype", "modele": "orchestre-x"}))),
        ("préréglage de sous-titres inconnu", _m(lambda b: b.update(sous_titres={"prereglage": "arc-en-ciel"}))),
        ("durée au-delà du motion code", _m(lambda b: b["rythme"]["duree_s"].update(max=500))),
        ("durée min > type", _m(lambda b: b["rythme"]["duree_s"].update(min=b["rythme"]["duree_s"]["type"] + 1))),
        ("plan_s illisible", _m(lambda b: b["rythme"].update(plan_s=[3, 1]))),
    ]
    for nom, mut in CAS:
        r = essai(mut)
        check(f"R1 signalé : {nom}", bool(r), r)


    def _valeur_hors(b):
        from app.services import motion_biblio as MB
        pg = b["motion"][_page]
        f = MB.lire(pg["style"])
        c = next(c for c in f["champs"] if c["type"] == "liste")
        pg.setdefault("champs", {})[c["id"]] = "valeur-hors-liste"


    def _nombre_hors(b):
        from app.services import motion_biblio as MB
        for pg in b["motion"].values():
            for c in MB.lire(pg["style"])["champs"]:
                if c["type"] == "nombre":
                    pg.setdefault("champs", {})[c["id"]] = int(c["max"]) + 50
                    return
        b["motion"][_page]["champs"] = {"zzz": 1}                       # pas de champ nombre : un autre écart


    def _champ_texte(b):
        from app.services import motion_biblio as MB
        pg = b["motion"][_page]
        c = next(c for c in MB.lire(pg["style"])["champs"] if c["type"] == "texte")
        pg.setdefault("champs", {})[c["id"]] = "un texte imposé"


    for nom, mut in (("valeur hors liste", _valeur_hors), ("nombre hors bornes", _nombre_hors),
                     ("champ texte imposé (c'est à l'utilisateur)", _champ_texte)):
        r = essai(mut)
        check(f"R2 signalé : {nom}", bool(r), r)
    d2 = pathlib.Path(tempfile.mkdtemp(prefix="dzstyles_double_", dir=_tmp))
    for n in ("a-un", "a-deux"):
        b = copy.deepcopy(modele); b["id"] = "a-un"
        (d2 / f"{n}.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    check("R3 id en double signalé", any("a-un" in x for x in SR.verifier(d2)), SR.verifier(d2))
    d3 = pathlib.Path(tempfile.mkdtemp(prefix="dzstyles_illisible_", dir=_tmp))
    (d3 / "casse.json").write_text("{pas du json", encoding="utf-8")
    check("R4 fichier illisible signalé", bool(SR.verifier(d3)))

    # ── [S] service ───────────────────────────────────────────────────────────────────────────────────────────────────
    print("[S] lecture")
    ls = SR.lister_styles("fr")
    check("S1 lister_styles rend tous les styles, triés par id", [s["id"] for s in ls] == sorted(p.stem for p in fichiers))
    check("S2 un résumé par style : titre, famille, durée, briques", all(
        s.get("titre") and s.get("famille_libelle") and s.get("duree_s") and "gabarit" in s and "voix" in s for s in ls))
    en = SR.lister_styles("en")
    check("S3 en anglais : titres anglais (au moins un diffère)", any(a["titre"] != b["titre"] for a, b in zip(ls, en)))
    check("S4 langue inconnue -> français", SR.lister_styles("de") == ls)
    sid = modele["id"]
    st = SR.style(sid, "fr")
    check("S5 style(id) : parties, à fournir localisés, emplacements nommés",
          st and st["titre"] == modele["titre"]["fr"] and isinstance(st["a_fournir"], list)
          and all(isinstance(x, str) for x in st["a_fournir"]) and st.get("gabarit", {}).get("emplacements"))
    check("S6 les champs texte du style motion sont rendus à fournir",
          st and any(c.get("type") == "texte" for pg in st.get("motion", {}).values() for c in pg.get("a_remplir", [])))
    check("S7 style inconnu -> None", SR.style("pas-un-style") is None)
    check("S8 chemin refusé -> None", SR.style("../motion/styles/charts") is None and SR.style("") is None)
    check("S9 lecture seule : aucune fonction d'écriture exposée",
          not [n for n in dir(SR) if re.match(r"^(ecrire|enregistrer|modifier|supprimer|creer)", n)])

    # ── [Q] devis ─────────────────────────────────────────────────────────────────────────────────────────────────────
    print("[Q] devis gratuit")
    _appels = []


    async def _interdit(*a, **k):
        _appels.append(a)
        raise AssertionError("aucun appel au moteur dans un devis")
    MT.tirer = MT.tirer_garde = _interdit


    def _dev(s, d=None, **k):
        return SR.devis_style(s, d, **k)


    for b in bruts:
        dv = _dev(b["id"], b["rythme"]["duree_s"]["type"])
        somme = round(sum(l["usd"] for l in dv["breakdown"]), 4)
        check(f"Q1 {b['id']} : total = somme des lignes, rien de lancé", abs(dv["total_usd"] - somme) < 1e-6
              and dv["lance"] is False and dv["total_usd"] >= 0, dv.get("total_usd"))
    check("Q2 aucun appel au moteur de texte pendant les devis", _appels == [])
    p = pricing.load()
    for b in bruts:
        dv = _dev(b["id"], b["rythme"]["duree_s"]["type"])
        prov = [l["provider"] for l in dv["breakdown"]]
        v = b["voix"]["moteur"]
        if v == "tts":
            check(f"Q3 {b['id']} : une ligne de voix de synthèse", "elevenlabs" in prov, prov)
        if v == "avatar":
            n_av = sum(1 for e in b["gabarit"]["emplacements"].values() if e["source"] == "avatar")
            check(f"Q4 {b['id']} : une ligne d'avatar par emplacement", prov.count("heygen") == n_av, prov)
        if b.get("musique"):
            check(f"Q5 {b['id']} : une ligne de musique", any(l["unit"] in ("piste", "s", "min") and l["provider"] == "fal"
                                                            for l in dv["breakdown"]), prov)
        pages = len(b.get("motion") or {})
        check(f"Q6 {b['id']} : une ligne de moteur de texte par page motion", prov.count("anthropic") == pages, prov)
        check(f"Q7 {b['id']} : les rendus locaux sont dits (0 $)", any(l["provider"] == "local" and l["usd"] == 0
                                                                     for l in dv["breakdown"]), prov)
    # cohérence avec pricing.estimate : la voix et la musique d'un style chiffrées à la main
    bt = next(b for b in bruts if b["voix"]["moteur"] == "tts" and b.get("musique"))
    dv = _dev(bt["id"], 20)
    chars = dv["caracteres"]
    check("Q8 caractères = durée × débit de parole de la grille",
          chars == round(20 * float(p["heygen_chars_per_min"]) / 60), chars)
    v_ref = pricing.estimate({"kind": "elevenlabs", "chars": chars, "model": bt["voix"]["modele"]})["total_usd"]
    m_ref = pricing.estimate({"kind": "music", "model": bt["musique"]["modele"], "duration_s": 20})["total_usd"]
    check("Q9 voix et musique = pricing.estimate", abs(sum(l["usd"] for l in dv["breakdown"] if l["provider"] == "elevenlabs")
                                                       - v_ref) < 1e-6
          and abs(sum(l["usd"] for l in dv["breakdown"] if l["provider"] == "fal") - m_ref) < 1e-6)
    mn = bt["rythme"]["duree_s"]["min"]; mx = bt["rythme"]["duree_s"]["max"]
    check("Q10 durée bornée au style (trop court, trop long, absente)",
          _dev(bt["id"], 1)["duree_s"] == mn and _dev(bt["id"], 999)["duree_s"] == mx
          and _dev(bt["id"], None)["duree_s"] == bt["rythme"]["duree_s"]["type"] and _dev(bt["id"], 1)["duree_bornee"])
    check("Q11 moteur local (ollama) : la page motion ne coûte rien",
          all(l["usd"] == 0 for l in _dev(bt["id"], 20, moteur="ollama")["breakdown"] if l["provider"] == "ollama"
              or l["provider"] == "local")
          and not [l for l in _dev(bt["id"], 20, moteur="ollama")["breakdown"] if l["provider"] == "anthropic"])
    check("Q12 sans moteur : le repli déterministe, gratuit et dit",
          not [l for l in _dev(bt["id"], 20, moteur="")["breakdown"] if l["provider"] in ("anthropic", "openai")])
    lab_en = [l["label"] for l in _dev(bt["id"], 20, langue="en")["breakdown"]]
    check("Q13 libellés en anglais avec langue=en, tous des str", all(type(x) is str for x in lab_en)
          and lab_en != [l["label"] for l in _dev(bt["id"], 20)["breakdown"]], lab_en)
    try:
        _dev("pas-un-style", 20); _r = False
    except LookupError:
        _r = True
    check("Q14 style inconnu -> LookupError", _r)
    bd = next((b for b in bruts if sum(1 for e in (b.get("gabarit") or {}).get("emplacements", {}).values()
                                       if e["source"] == "avatar") >= 2), None)
    if bd:
        dvb = _dev(bd["id"], bd["rythme"]["duree_s"]["type"])
        ch = sum(l["units"] for l in dvb["breakdown"] if l["provider"] == "heygen")
        check("Q15 deux avatars se partagent le texte (crédits = un seul texte)",
              abs(ch - pricing.estimate({"kind": "heygen", "chars": dvb["caracteres"]})["breakdown"][0]["units"]) < 0.05,
              ch)

    # ── [H] routes ────────────────────────────────────────────────────────────────────────────────────────────────────
    print("[H] routes locales en lecture")
    from fastapi.testclient import TestClient                          # noqa: E402
    from app.main import app                                            # noqa: E402
    from app.api import styles_reel_routes as RR                        # noqa: E402
    c = TestClient(app)
    loin = TestClient(app, client=("192.168.1.50", 5000))
    r = c.get("/api/styles-reel")
    check("H1 GET /api/styles-reel : la liste et les familles", r.status_code == 200
          and len(r.json()["styles"]) == len(fichiers) and r.json().get("familles"), r.text[:200])
    r = c.get(f"/api/styles-reel/{sid}")
    check("H2 GET /api/styles-reel/{id}", r.status_code == 200 and r.json()["id"] == sid, r.text[:200])
    r = c.get("/api/styles-reel/pas-un-style")
    check("H3 style inconnu -> 404", r.status_code == 404, r.status_code)
    r = c.get(f"/api/styles-reel/{sid}/devis", params={"duree_s": 20})
    check("H4 devis gratuit par GET", r.status_code == 200 and r.json()["lance"] is False
          and r.json()["total_usd"] == _dev(sid, 20)["total_usd"], r.text[:200])
    r = c.get("/api/styles-reel/pas-un-style/devis")
    check("H5 devis d'un style inconnu -> 404", r.status_code == 404, r.status_code)
    r = c.get(f"/api/styles-reel/{sid}", headers={"Accept-Language": "en"})
    check("H6 Accept-Language: en -> titre anglais", r.status_code == 200 and r.json()["titre"] == modele["titre"]["en"])
    check("H7 depuis un autre appareil sans jeton -> refusé (401 de la garde d'appareil)",
          loin.get("/api/styles-reel").status_code in (401, 403)
          and loin.get(f"/api/styles-reel/{sid}/devis").status_code in (401, 403))

    class _Faux:                                                    # un appareil APPAIRÉ passe la garde de jeton
        client = type("C", (), {"host": "192.168.1.50"})()
    try:
        RR._local(_Faux()); _code = None
    except Exception as e:                                          # noqa: BLE001
        _code = getattr(e, "status_code", None)
    check("H8 même appairé, un autre appareil est refusé par la route (403)", _code == 403, _code)
    check("H9 le routeur n'a que des GET (aucune route payante ni d'écriture)",
          {m for rt in RR.router.routes for m in getattr(rt, "methods", set())} <= {"GET", "HEAD"})
    check("H10 aucun appel à plafonds.verifier dans le routeur (rien à payer)",
          "plafonds" not in (RACINE / "backend" / "app" / "api" / "styles_reel_routes.py").read_text(encoding="utf-8"))

    # ── [A] agent ─────────────────────────────────────────────────────────────────────────────────────────────────────
    print("[A] outil d'agent en lecture, pour « mcp » seulement")
    from app.services import agent_boites as B, agent_outils as ao     # noqa: E402
    fige = json.loads((ICI / "agent_definitions_campagnes.json").read_text(encoding="utf-8"))
    check("A1 Campagnes inchangé à l'octet (fixture)", ao.definitions() == fige)
    check("A2 boîte styles_reel : un outil, agent mcp seul, pas sur le téléphone",
          B.BOITES.get("styles_reel") == {"libelle": "agent.boites.styles_reel", "outils": ["styles_reel_lire"],
                                          "agents": ["mcp"], "mobile": False}, B.BOITES.get("styles_reel"))
    check("A3 outil en lecture", ao.OUTILS["styles_reel_lire"]["nature"] == "lecture")
    check("A4 Campagnes ne le voit pas", "styles_reel_lire" not in B.outils_pour("campagnes"))
    check("A5 mcp le voit", "styles_reel_lire" in B.outils_pour("mcp"))
    _ctx = ao.Ctx(cid="banc", agent="mcp")
    if _ctx is not None:
        r = asyncio.run(ao.executer("styles_reel_lire", {}, _ctx))
        check("A6 sans id : la liste", r["ok"] and len(r["donnees"]["styles"]) == len(fichiers), r.get("resume"))
        r = asyncio.run(ao.executer("styles_reel_lire", {"id": sid, "duree_s": 20}, _ctx))
        check("A7 avec id et durée : le style et son devis", r["ok"] and r["donnees"]["style"]["id"] == sid
              and r["donnees"]["devis"]["lance"] is False, r.get("resume"))
        r = asyncio.run(ao.executer("styles_reel_lire", {"id": "pas-un-style"}, _ctx))
        check("A8 style inconnu : refus lisible", r["ok"] is False)
        _cc = ao.Ctx(cid="banc", agent="campagnes")
        r = asyncio.run(ao.executer("styles_reel_lire", {}, _cc))
        check("A9 refusé à Campagnes (hors boîte)", r["ok"] is False)
    else:
        check("A6 Ctx a un champ agent", False)
    dico = json.loads((RACINE / "frontend" / "shared" / "i18n" / "agent.json").read_text(encoding="utf-8"))
    check("A10 libellé de la boîte FR/EN", dico.get("agent.boites.styles_reel", {}).get("en"))
    check("A11 dictionnaire assemblé à jour (source et copie dist)", all(
        "agent.boites.styles_reel" in (RACINE / "frontend" / x / "dz-i18n-dico.js").read_text(encoding="utf-8")
        for x in ("shared", "dist/shared")))

    # ── [E] erreurs traduites, AGENTS.md ──────────────────────────────────────────────────────────────────────────────
    print("[E] traductions et AGENTS.md")
    # --check est rouge sur main pour des messages d'autres lots (routes.py, moteurs3d_neufs.py) : ce banc ne garde que
    # les siens — rendus dans erreurs.json (le produit de i18n_l10_erreurs.py) et sans traduction orpheline
    r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], cwd=RACINE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("E1 i18n_l10_erreurs.py : aucune traduction orpheline ni fautive",
          " 0 fautif(s), 0 traduction(s) orpheline(s)" in r.stdout, (r.stdout + r.stderr)[-600:])
    produits = {v["fr"] for v in json.loads((RACINE / "backend" / "app" / "i18n" / "erreurs.json")
                                            .read_text(encoding="utf-8")).values()}
    import ast                                                          # noqa: E402
    tr = json.loads((RACINE / "scripts" / "i18n_l10_traductions.json").read_text(encoding="utf-8"))
    msgs = set()
    for src in (RACINE / "backend" / "app" / "services" / "styles_reel.py",
                RACINE / "backend" / "app" / "api" / "styles_reel_routes.py"):
        for nd in ast.walk(ast.parse(src.read_text(encoding="utf-8"))):
            if isinstance(nd, ast.Raise) and isinstance(nd.exc, ast.Call) and nd.exc.args:
                fn = getattr(nd.exc.func, "id", "")
                a = nd.exc.args[-1] if fn == "HTTPException" else nd.exc.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    msgs.add(a.value)
    manque = sorted(m for m in msgs if m not in tr)
    check(f"E2 les {len(msgs)} messages fixes sont traduits", msgs and not manque, manque)
    check("E2b et rendus dans erreurs.json (réassemblé)", msgs and msgs <= produits, sorted(msgs - produits))
    ag = (RACINE / "AGENTS.md").read_text(encoding="utf-8")
    i_s, i_c = ag.find("`backend/app/services/styles_reel.py`"), ag.find("| `backend/app/services/coffre.py` |")
    check("E3 AGENTS.md : la ligne des styles de reel, juste avant le coffre", 0 < i_s < i_c
          and ag[i_s:i_c].count("\n") == 1, (i_s, i_c))

    print(f"\n{ok} ok, {fail} échec(s)")
    shutil.rmtree(_tmp, ignore_errors=True)
    return fail


def test_styles_reel():
    """Lanceur pytest."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
