# -*- coding: utf-8 -*-
"""t233 (lot « Studio : Animation », 17/10/2026) — la bibliothèque motion : styles maison, imports, skills.

Décision de l'utilisateur (Q3 = a) : nos PROPRES fiches de style dans le dépôt, les imports de l'utilisateur dans ses
données (attribution obligatoire), les skills sous licence permissive installés À LA DEMANDE. prompt-motion.com n'a
aucune licence : « les vidéos et les prompts appartiennent à leurs créateurs » — rien de ce site n'entre dans le dépôt.

Zéro réseau : le transport httpx de `motion_biblio` est un FAUX MIROIR GITHUB en mémoire (raw.githubusercontent.com),
chaque requête est enregistrée. Ce que ce banc garde :
  [F] les 11 fiches maison : un fichier par thème, champs complets FR + EN, presets = ceux du nœud Animation, easings =
      ceux de son éditeur d'images clés, formats connus, durées cohérentes ; lecture seule (PATCH / DELETE → 403) ;
  [I] l'import d'un prompt : titre + texte + URL d'attribution OBLIGATOIRE (http(s), sans identifiants) + auteur +
      thèmes connus ; rangé dans DEEPOTUS_DATA_DIR/motion, JAMAIS dans le dépôt ; modifier, supprimer ;
  [S] l'installation d'un skill `owner/repo[:chemin]` ou d'une URL github.com : SKILL.md + LICENSE (+ NOTICE Apache)
      seulement, depuis raw.githubusercontent.com seulement ; licence MIT / Apache-2.0 / BSD / ISC exigée ; chemin hors
      dossier, hôte tiers, redirection, fichier trop gros REFUSÉS avant toute écriture ; aucun processus lancé ;
      copie éditable `consigne`, « revenir à l'original » ; doublon refusé ; suppression = dossier retiré ;
  [M] le miroir de preuve (DZ_MOTION_MIROIR_GITHUB) n'est suivi que sur une instance isolée ET en boucle locale ;
  [X] lecture et écriture refusées depuis un autre appareil ;
  [G] GARDE ANTI-CONTENU TIERS : aucun titre, pseudo ni extrait de prompt de prompt-motion.com dans les fichiers suivis
      du dépôt. Le banc ne garde que des EMPREINTES (motion_garde_empreintes.json), jamais le texte ;
  [E] chaque message d'erreur neuf est traduit (scripts/i18n_l10_traductions.json, --check vert).
Run (depuis backend/) : & $PY tests/test_motion_biblio.py
Régénérer les empreintes (fichiers HORS dépôt) : & $PY tests/test_motion_biblio.py --regenerer META.json PHRASES.txt"""
import hashlib, json, os, pathlib, re, subprocess, sys, tempfile, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
EMPREINTES = ICI / "motion_garde_empreintes.json"


# ── empreintes de la garde [G] ────────────────────────────────────────────────────────────────────────────────────
def _jetons(texte: str) -> list:
    t = unicodedata.normalize("NFKD", texte)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return re.findall(r"[a-z0-9_]+", t)


def _h_phrase(jetons) -> str:
    return hashlib.sha256(("dzmotion|" + " ".join(jetons)).encode("utf-8")).hexdigest()[:20]


def _h_tete(jeton: str) -> str:
    return hashlib.sha256(("dzmotion1|" + jeton).encode("utf-8")).hexdigest()[:12]


TEMOIN_ENVERS = ["dz", "motion", "garde", "temoin"]                  # lu à l'envers (voir G4)


def regenerer(meta: str, phrases: str) -> None:
    """Titres + pseudos du relevé (meta.json) et phrases en plus (une par ligne ; « !nom » = exempter ce pseudo, ex.
    le propriétaire d'un dépôt de skill sous licence, dont le nom de dépôt est cité légitimement)."""
    entrees = json.loads(pathlib.Path(meta).read_text(encoding="utf-8"))
    textes, exempts = [" ".join(reversed(TEMOIN_ENVERS))], set()
    for ligne in pathlib.Path(phrases).read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        if ligne.startswith("!"):
            exempts.add(" ".join(_jetons(ligne[1:].split("(")[0])))
        else:
            textes.append(ligne)
    for e in entrees:
        textes.append(e.get("title") or "")
        textes.append(e.get("handle") or "")
    vus = {}
    for t in textes:
        j = _jetons(t)
        if not j or " ".join(j) in exempts:
            continue
        vus[_h_phrase(j)] = [len(j), _h_tete(j[0]), _h_phrase(j)]
    note = ("t233 : empreintes des titres, pseudos et extraits de prompt-motion.com (sha256 tronqué, jamais le texte) "
            "— voir test_motion_biblio.py [G]")
    lignes = ",\n".join(json.dumps(v) for v in sorted(vus.values(), key=lambda v: v[2]))
    EMPREINTES.write_text(f'{{"note": {json.dumps(note, ensure_ascii=False)},\n"empreintes": [\n{lignes}\n]}}\n',
                          encoding="utf-8")
    print(f"{len(vus)} empreintes écrites dans {EMPREINTES.name}")


if len(sys.argv) == 4 and sys.argv[1] == "--regenerer":
    regenerer(sys.argv[2], sys.argv[3])
    sys.exit(0)

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmb_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.pop("DZ_MOTION_MIROIR_GITHUB", None)
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import motion_biblio as MB                        # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


THEMES = ["kinetic-type", "product-ui", "charts", "diagrams", "shapes", "particles", "characters", "photos", "phone",
          "code", "music"]
# Lus dans le bundle (composant DzAnimation, base 39241c15) : PRESETS et EAS. Recopiés ici À LA MAIN : si le nœud
# change, ce banc doit être relu, pas suivre en silence.
PRESETS_NOEUD = {"fade-in", "slide-up", "slide-down", "slide-left", "slide-right", "pop", "zoom-in", "ken-burns"}
EASINGS_NOEUD = {"linear", "easeIn", "easeOut", "easeInOut", "easeOutBack", "easeOutBounce", "smooth",
                 "easeInOutSine", "anticipate", "overshoot"}
FORMATS = {"16:9", "9:16", "1:1", "4:5"}
STYLES = RACINE / "backend" / "app" / "motion" / "styles"
DONNEES = _tmp / "motion"


def suivis() -> dict:
    """Les fichiers du dépôt sous backend/app/motion (pour vérifier qu'un import n'y écrit rien)."""
    base = RACINE / "backend" / "app" / "motion"
    return {p.relative_to(base).as_posix(): p.stat().st_mtime_ns for p in base.rglob("*") if p.is_file()} \
        if base.is_dir() else {}


c = TestClient(app)
cd = TestClient(app, client=("192.168.1.50", 5000))

# ── [F] fiches maison ─────────────────────────────────────────────────────────────────────────────────────────────
print("[F] fiches de style maison")
fichiers = sorted(STYLES.glob("*.json")) if STYLES.is_dir() else []
check("F1 11 fichiers, un par thème", sorted(p.stem for p in fichiers) == sorted(THEMES), [p.stem for p in fichiers])
for p in fichiers:
    try:
        f = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:                                          # noqa: BLE001
        check(f"F2 {p.name} : JSON lisible", False, e); continue
    defauts = []
    if f.get("theme") != p.stem:
        defauts.append("theme")
    for k in ("titre", "consigne", "rythme"):
        v = f.get(k) or {}
        if not (isinstance(v, dict) and str(v.get("fr", "")).strip() and str(v.get("en", "")).strip()):
            defauts.append(k)
    if len((f.get("consigne") or {}).get("fr", "")) < 200 or len((f.get("consigne") or {}).get("en", "")) < 200:
        defauts.append("consigne trop courte")
    pr = f.get("presets") or []
    if not pr or not set(pr) <= PRESETS_NOEUD or len(set(pr)) != len(pr):
        defauts.append(f"presets {pr}")
    ea = f.get("easings") or []
    if not ea or not set(ea) <= EASINGS_NOEUD:
        defauts.append(f"easings {ea}")
    fo = f.get("formats") or []
    if not fo or not set(fo) <= FORMATS:
        defauts.append(f"formats {fo}")
    d = f.get("duree_s") or {}
    if not (isinstance(d, dict) and 0 < d.get("min", 0) <= d.get("type", 0) <= d.get("max", 0) <= 180):
        defauts.append(f"duree_s {d}")
    ca = f.get("cadence_s") or []
    if not (isinstance(ca, list) and len(ca) == 2 and 0 < ca[0] <= ca[1] <= 10):
        defauts.append(f"cadence_s {ca}")
    check(f"F2 {p.stem} : complète et dans le vocabulaire du nœud", not defauts, defauts)

r = c.get("/api/motion/biblio")
ents = r.json().get("entrees", []) if r.status_code == 200 else []
styles = [e for e in ents if e.get("nature") == "style"]
check("F3 GET /api/motion/biblio → les 11 styles, lecture seule", r.status_code == 200 and len(styles) == 11
      and all(e.get("lecture_seule") is True and e["id"] == "style-" + e["theme"] for e in styles), r.status_code)
r = c.get("/api/motion/biblio", params={"nature": "style", "theme": "charts"})
check("F4 filtre nature + thème", r.status_code == 200 and [e["id"] for e in r.json()["entrees"]] == ["style-charts"],
      r.text[:200])
r = c.get("/api/motion/biblio/style-music")
check("F5 GET d'une fiche", r.status_code == 200 and r.json().get("theme") == "music", r.status_code)
r = c.patch("/api/motion/biblio/style-music", json={"titre": "x"})
r2 = c.delete("/api/motion/biblio/style-music")
check("F6 une fiche maison ne se modifie ni ne se supprime (403)", r.status_code == 403 and r2.status_code == 403
      and (STYLES / "music.json").is_file(), (r.status_code, r2.status_code))

# ── [I] imports de prompts ────────────────────────────────────────────────────────────────────────────────────────
print("[I] imports de l'utilisateur")
avant = suivis()
BON = {"titre": "Ma direction néon", "texte": "Un texte de prompt collé par l'utilisateur, avec sa mise en forme.\n"
       "Deuxième ligne.", "url": "https://exemple.test/fiche/42", "auteur": "Créatrice Exemple",
       "themes": ["kinetic-type", "music"]}
r = c.post("/api/motion/biblio", json=BON)
imp = r.json() if r.status_code == 200 else {}
check("I1 import avec attribution → 200, nature prompt", r.status_code == 200 and imp.get("nature") == "prompt"
      and imp.get("url") == BON["url"] and imp.get("auteur") == BON["auteur"] and imp.get("texte") == BON["texte"],
      r.text[:200])
iid = imp.get("id", "")
check("I2 id sûr (prompt-…)", re.fullmatch(r"prompt-[a-z0-9-]+", iid or "") is not None, iid)
check("I3 rangé dans DEEPOTUS_DATA_DIR/motion", any(DONNEES.rglob(f"{iid}.json")) if iid else False,
      list(DONNEES.rglob("*")) if DONNEES.exists() else "absent")
check("I4 rien d'écrit dans le dépôt", suivis() == avant)
for label, champ, val in (("URL absente", "url", None), ("URL vide", "url", "  "), ("URL javascript:", "url",
                          "javascript:alert(1)"), ("URL ftp", "url", "ftp://exemple.test/x"),
                          ("URL avec identifiants", "url", "https://moi:secret@exemple.test/x"),
                          ("URL sans hôte", "url", "https:///x"), ("titre vide", "titre", " "),
                          ("texte vide", "texte", ""), ("thème inconnu", "themes", ["kinetic-type", "inconnu"]),
                          ("texte trop long", "texte", "x" * 20001)):
    corps = dict(BON)
    if val is None:
        corps.pop(champ)
    else:
        corps[champ] = val
    r = c.post("/api/motion/biblio", json=corps)
    check(f"I5 {label} → 400", r.status_code == 400, (r.status_code, r.text[:160]))
r = c.post("/api/motion/biblio", json={k: v for k, v in BON.items() if k != "url"})
r2 = c.post("/api/motion/biblio", json=dict(BON, url="   "))
check("I6 le refus dit que l'attribution est obligatoire (absente ou vide)", all("attribution est obligatoire" in x.text for x in (r, r2)),
      (r.text[:200], r2.text[:200]))
n_imports = len([e for e in c.get("/api/motion/biblio").json()["entrees"] if e["nature"] == "prompt"])
check("I7 un seul import enregistré malgré les refus", n_imports == 1, n_imports)
r = c.patch(f"/api/motion/biblio/{iid}", json={"titre": "Direction néon v2", "themes": ["shapes"]})
check("I8 PATCH titre + thèmes", r.status_code == 200 and r.json().get("titre") == "Direction néon v2"
      and r.json().get("themes") == ["shapes"], r.text[:200])
r = c.patch(f"/api/motion/biblio/{iid}", json={"url": ""})
check("I9 PATCH qui efface l'attribution → 400", r.status_code == 400
      and c.get(f"/api/motion/biblio/{iid}").json().get("url") == BON["url"], r.status_code)
r = c.patch(f"/api/motion/biblio/{iid}", json={"id": "prompt-autre"})
check("I10 champ non modifiable → 400", r.status_code == 400, r.status_code)
r = c.post(f"/api/motion/biblio/{iid}/revenir")
check("I11 « revenir à l'original » refusé pour un prompt", r.status_code == 400, r.status_code)
for mauvais in ("prompt-..", "prompt-a.b", "style-../../x", "PROMPT-A"):
    r = c.get(f"/api/motion/biblio/{mauvais}")
    check(f"I12 id {mauvais!r} → 404", r.status_code == 404, r.status_code)
_fuites = []
for mauvais in ("prompt-../../x", "skill-../../../x", "prompt-a/b", "prompt-a\\b", "prompt-x.json", ""):
    try:
        MB._fichier_entree(mauvais); _fuites.append(mauvais)
    except LookupError:
        pass
check("I14 un id hors du dossier ne donne jamais de chemin", not _fuites, _fuites)
r = c.delete(f"/api/motion/biblio/{iid}")
check("I13 DELETE → l'import disparaît", r.status_code == 200 and c.get(f"/api/motion/biblio/{iid}").status_code
      == 404 and not any(DONNEES.rglob(f"{iid}.json")), r.status_code)

# ── [S] skills : le faux miroir GitHub ────────────────────────────────────────────────────────────────────────────
print("[S] skills installés à la demande")
MIT = ("MIT License\n\nCopyright (c) 2026 Banc Exemple\n\nPermission is hereby granted, free of charge, to any person "
       "obtaining a copy\nof this software and associated documentation files (the \"Software\"), to deal\nin the "
       "Software without restriction, including without limitation the rights\nto use, copy, modify, merge, publish, "
       "distribute, sublicense, and/or sell\ncopies of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT "
       "WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED.\n")
APACHE = ("                                 Apache License\n                           Version 2.0, January 2004\n"
          "                        http://www.apache.org/licenses/\n\n   TERMS AND CONDITIONS FOR USE, REPRODUCTION, "
          "AND DISTRIBUTION\n")
ISC = ("ISC License\n\nCopyright (c) 2026 Banc\n\nPermission to use, copy, modify, and/or distribute this software for "
       "any\npurpose with or without fee is hereby granted, provided that the above\ncopyright notice and this "
       "permission notice appear in all copies.\n")
BSD3 = ("BSD 3-Clause License\n\nRedistribution and use in source and binary forms, with or without\nmodification, "
        "are permitted provided that the following conditions are met:\n3. Neither the name of the copyright holder "
        "nor the names of its\n   contributors may be used to endorse or promote products.\n")
GPL = ("                    GNU GENERAL PUBLIC LICENSE\n                       Version 3, 29 June 2007\n\n Everyone is "
       "permitted to copy and distribute verbatim copies\n")
SKILL = ("---\nname: banc-demo\ndescription: Un skill de démonstration pour le banc t233.\n---\n\n# Banc démo\n\n"
         "Animez chaque mot sur le temps fort, sans jamais dépasser trois mots à l'écran.\n")
R = "https://raw.githubusercontent.com"
MIROIR = {
    f"{R}/banc-mit/skills-demo/HEAD/skills/demo/SKILL.md": (200, SKILL),
    f"{R}/banc-mit/skills-demo/HEAD/LICENSE": (200, MIT),
    f"{R}/banc-mit/skills-demo/HEAD/skills/demo/run.sh": (200, "#!/bin/sh\necho NE-JAMAIS-LIRE\n"),
    f"{R}/banc-mit/skills-demo/main/skills/autre/SKILL.md": (200, SKILL.replace("banc-demo", "banc-autre")),
    f"{R}/banc-mit/skills-demo/main/LICENSE": (200, MIT),
    f"{R}/banc-apache/hf/HEAD/SKILL.md": (200, SKILL.replace("banc-demo", "banc-apache")),
    f"{R}/banc-apache/hf/HEAD/LICENSE": (200, APACHE),
    f"{R}/banc-apache/hf/HEAD/NOTICE": (200, "Banc Apache\nCopyright 2026 Banc.\n"),
    f"{R}/banc-isc/s/HEAD/x/SKILL.md": (200, SKILL.replace("banc-demo", "banc-isc")),
    f"{R}/banc-isc/s/HEAD/x/LICENSE.md": (200, ISC),
    f"{R}/banc-bsd/s/HEAD/SKILL.md": (200, SKILL.replace("banc-demo", "banc-bsd")),
    f"{R}/banc-bsd/s/HEAD/LICENSE.txt": (200, BSD3),
    f"{R}/banc-sanslicence/s/HEAD/SKILL.md": (200, SKILL),
    f"{R}/banc-gpl/s/HEAD/SKILL.md": (200, SKILL),
    f"{R}/banc-gpl/s/HEAD/LICENSE": (200, GPL),
    f"{R}/banc-redir/s/HEAD/SKILL.md": (302, ""),
    f"{R}/banc-gros/s/HEAD/SKILL.md": (200, "x" * (256 * 1024 + 1)),
    f"{R}/banc-gros/s/HEAD/LICENSE": (200, MIT),
    f"{R}/banc-proprio/s/HEAD/SKILL.md": (200, SKILL),
    f"{R}/banc-proprio/s/HEAD/LICENSE": (200, "Copyright (c) 2026 Banc. All rights reserved.\n"),
    f"{R}/banc-mixte/s/HEAD/SKILL.md": (200, SKILL),
    f"{R}/banc-mixte/s/HEAD/LICENSE": (200, MIT + "\nThe scripts/ folder is licensed under the GNU General Public "
                                       "License v3.\n"),
    f"{R}/banc-binaire/s/HEAD/SKILL.md": (200, b"\x89PNG\r\n\x1a\n\x00\x00"),
    f"{R}/banc-binaire/s/HEAD/LICENSE": (200, MIT),
    f"{R}/banc-nul/s/HEAD/SKILL.md": (200, "# titre\n\x00 caché\n"),
    f"{R}/banc-nul/s/HEAD/LICENSE": (200, MIT),
}
REQ = []


def _miroir(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    REQ.append(u)
    st, corps = MIROIR.get(u, (404, "Not Found"))
    corps = corps if isinstance(corps, bytes) else corps.encode("utf-8")
    h = {"location": "https://evil.example/SKILL.md"} if st == 302 else {}
    return httpx.Response(st, content=corps, headers=h)


MB._transport = httpx.MockTransport(_miroir)
_lances = []
_vrai_popen, _vrai_system = subprocess.Popen, os.system


class _Interdit:
    def __init__(self, *a, **k):
        _lances.append(a)
        raise AssertionError("un processus a été lancé pendant une installation de skill")


def installer(source):
    REQ.clear()
    subprocess.Popen, os.system = _Interdit, lambda *a: _lances.append(a) or 1
    try:
        return c.post("/api/motion/skills/installer", json={"source": source})
    finally:
        subprocess.Popen, os.system = _vrai_popen, _vrai_system


def dossiers_skills():
    d = DONNEES / "skills"
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


r = installer("banc-mit/skills-demo:skills/demo")
sk = r.json() if r.status_code == 200 else {}
check("S1 skill MIT accepté", r.status_code == 200 and sk.get("nature") == "skill" and sk.get("licence") == "MIT",
      r.text[:300])
sid = sk.get("id", "")
check("S2 titre et description lus dans l'en-tête de SKILL.md", sk.get("titre") == "banc-demo"
      and "démonstration" in (sk.get("description") or ""), sk)
check("S3 SKILL.md + LICENSE seulement, depuis raw.githubusercontent.com",
      sorted(REQ) == sorted([f"{R}/banc-mit/skills-demo/HEAD/skills/demo/SKILL.md",
                             f"{R}/banc-mit/skills-demo/HEAD/skills/demo/LICENSE",
                             f"{R}/banc-mit/skills-demo/HEAD/skills/demo/LICENSE.md",
                             f"{R}/banc-mit/skills-demo/HEAD/skills/demo/LICENSE.txt",
                             f"{R}/banc-mit/skills-demo/HEAD/LICENSE"]), REQ)
dsk = DONNEES / "skills" / sid
check("S4 dossier du skill : SKILL.md + LICENSE, octets d'origine",
      dsk.is_dir() and sorted(p.name for p in dsk.iterdir()) == ["LICENSE", "SKILL.md"]
      and (dsk / "SKILL.md").read_bytes() == SKILL.encode() and (dsk / "LICENSE").read_bytes() == MIT.encode(),
      sorted(p.name for p in dsk.iterdir()) if dsk.is_dir() else "absent")
check("S5 aucun processus lancé, aucun script lu", not _lances and not any(u.endswith(".sh") for u in REQ), _lances)
check("S6 consigne = copie du texte d'origine, non modifiée", sk.get("consigne") == SKILL and sk.get("modifie") is False)
full = c.get(f"/api/motion/biblio/{sid}").json()
check("S7 GET du skill : original + texte de licence affichés", full.get("original") == SKILL
      and full.get("licence_texte") == MIT and full.get("source", {}).get("depot") == "banc-mit/skills-demo"
      and full.get("source", {}).get("url", "").startswith("https://github.com/banc-mit/skills-demo"), full.get("source"))
liste = [e for e in c.get("/api/motion/biblio", params={"nature": "skill"}).json()["entrees"]]
check("S8 la liste ne transporte pas l'original", len(liste) == 1 and "original" not in liste[0], liste)
r = c.patch(f"/api/motion/biblio/{sid}", json={"consigne": "Ma version : deux mots à l'écran au plus."})
check("S9 PATCH consigne → modifiée, original intact", r.status_code == 200 and r.json().get("modifie") is True
      and (dsk / "SKILL.md").read_bytes() == SKILL.encode()
      and c.get(f"/api/motion/biblio/{sid}").json().get("original") == SKILL, r.text[:200])
r = c.patch(f"/api/motion/biblio/{sid}", json={"original": "piraté"})
check("S10 l'original ne se modifie pas (400)", r.status_code == 400 and (dsk / "SKILL.md").read_bytes()
      == SKILL.encode(), r.status_code)
r = c.patch(f"/api/motion/biblio/{sid}", json={"consigne": "  "})
check("S11 consigne vide → 400", r.status_code == 400, r.status_code)
r = c.post(f"/api/motion/biblio/{sid}/revenir")
check("S12 « revenir à l'original »", r.status_code == 200 and r.json().get("consigne") == SKILL
      and r.json().get("modifie") is False, r.text[:200])
r = installer("banc-mit/skills-demo:skills/demo")
check("S13 doublon refusé (400), rien de plus", r.status_code == 400 and dossiers_skills() == [sid], r.status_code)

r = installer("https://github.com/banc-mit/skills-demo/tree/main/skills/autre")
check("S14 URL github.com/tree/<ref>/<chemin> acceptée (ref suivie)", r.status_code == 200
      and REQ[0] == f"{R}/banc-mit/skills-demo/main/skills/autre/SKILL.md", (r.status_code, REQ[:1], r.text[:200]))
check("S15 hôtes interrogés : raw.githubusercontent.com SEULEMENT",
      REQ and all(httpx.URL(u).host == "raw.githubusercontent.com" for u in REQ), REQ)
r = installer("banc-apache/hf")
ap = r.json() if r.status_code == 200 else {}
check("S16 Apache-2.0 : accepté, NOTICE gardé", r.status_code == 200 and ap.get("licence") == "Apache-2.0"
      and (DONNEES / "skills" / ap.get("id", "?") / "NOTICE").is_file(), r.text[:200])
r = installer("banc-isc/s:x")
check("S17 ISC (LICENSE.md du dossier) accepté", r.status_code == 200 and r.json().get("licence") == "ISC", r.text[:200])
r = installer("https://raw.githubusercontent.com/banc-bsd/s/HEAD/SKILL.md")
check("S18 BSD-3-Clause (LICENSE.txt), URL raw acceptée", r.status_code == 200
      and r.json().get("licence") == "BSD-3-Clause", r.text[:200])

n0 = dossiers_skills()
r = installer("banc-sanslicence/s")
check("S19 dépôt SANS licence refusé", r.status_code == 400 and "licence" in r.text.lower()
      and dossiers_skills() == n0, (r.status_code, r.text[:200]))
r = installer("banc-proprio/s")
check("S20b licence propriétaire (« All rights reserved ») refusée", r.status_code == 400
      and dossiers_skills() == n0, (r.status_code, r.text[:200]))
r = installer("banc-mixte/s")
check("S20c MIT + une part GPL dans la même licence → refusée", r.status_code == 400
      and dossiers_skills() == n0, (r.status_code, r.text[:200]))
r = installer("banc-gpl/s")
check("S20 licence GPL refusée", r.status_code == 400 and dossiers_skills() == n0, (r.status_code, r.text[:200]))
for mauvais in ("banc-mit/skills-demo:../x", "banc-mit/skills-demo:skills/../../x", "banc-mit/skills-demo:/etc",
                "banc-mit/skills-demo:skills\\demo", "banc-mit/skills-demo:.git", "banc-mit/skills-demo:%2e%2e/x",
                "https://github.com/banc-mit/skills-demo/tree/main/../../x", "../skills-demo", "banc-mit/..",
                "https://github.com/banc-mit/skills-demo/tree/../skills", "https://github.com/a/b/tree/.x/skills",
                "https://raw.githubusercontent.com/banc-mit/skills-demo/a..b/SKILL.md",
                "banc mit/skills", "banc-mit/skills-demo:a/b/c/d/e/f/g/h/i/j/k"):
    r = installer(mauvais)
    check(f"S21 chemin hors dossier {mauvais!r} → 400, aucune requête", r.status_code == 400 and not REQ
          and dossiers_skills() == n0, (r.status_code, REQ))
for mauvais in ("https://evil.example/banc-mit/skills-demo", "http://github.com/banc-mit/skills-demo",
                "https://github.com.evil.example/banc-mit/skills-demo", "https://api.github.com/repos/a/b",
                "https://github.com:8443/banc-mit/skills-demo", "https://x@github.com/banc-mit/skills-demo",
                "file:///C:/Windows/win.ini"):
    r = installer(mauvais)
    check(f"S22 hôte refusé {mauvais!r} → 400, aucune requête", r.status_code == 400 and not REQ, (r.status_code, REQ))
r = installer("banc-redir/s")
check("S23 redirection NON suivie → refus", r.status_code >= 400 and len(REQ) == 1 and dossiers_skills() == n0,
      (r.status_code, REQ))
r = installer("banc-gros/s")
check("S24 SKILL.md trop gros → 400", r.status_code == 400 and dossiers_skills() == n0, (r.status_code, r.text[:160]))
r = installer("banc-binaire/s")
check("S25 SKILL.md binaire → 400", r.status_code == 400 and dossiers_skills() == n0, (r.status_code, r.text[:160]))
r = installer("banc-nul/s")
check("S25b SKILL.md UTF-8 avec octet NUL → 400", r.status_code == 400 and dossiers_skills() == n0,
      (r.status_code, r.text[:160]))
r = installer("banc-absent/s")
check("S26 SKILL.md introuvable → 404", r.status_code == 404 and dossiers_skills() == n0, r.status_code)
r = c.post("/api/motion/skills/installer", json={})
check("S27 source absente → 400", r.status_code == 400, r.status_code)
check("S28 aucun processus lancé sur toute la série", not _lances, _lances)
r = c.delete(f"/api/motion/biblio/{sid}")
check("S29 DELETE d'un skill : entrée + dossier retirés", r.status_code == 200 and not dsk.exists()
      and c.get(f"/api/motion/biblio/{sid}").status_code == 404, r.status_code)

# ── [M] le miroir de preuve ───────────────────────────────────────────────────────────────────────────────────────
print("[M] miroir de preuve")
os.environ["DZ_MOTION_MIROIR_GITHUB"] = "http://127.0.0.1:8798"
check("M1 instance isolée + boucle locale → miroir suivi",
      MB._base_raw() == "http://127.0.0.1:8798/raw.githubusercontent.com", MB._base_raw())
os.environ["DZ_MOTION_MIROIR_GITHUB"] = "https://evil.example"
check("M2 miroir hors boucle locale → ignoré", MB._base_raw() == R, MB._base_raw())
os.environ["DZ_MOTION_MIROIR_GITHUB"] = "http://127.0.0.1:8798"
_dd = os.environ.pop("DEEPOTUS_DATA_DIR")
check("M3 instance NON isolée → miroir ignoré", MB._base_raw() == R, MB._base_raw())
os.environ["DEEPOTUS_DATA_DIR"] = _dd
os.environ.pop("DZ_MOTION_MIROIR_GITHUB")

# ── [X] autre appareil ────────────────────────────────────────────────────────────────────────────────────────────
print("[X] autre appareil")
for meth, url, corps in (("get", "/api/motion/biblio", None), ("get", "/api/motion/biblio/style-music", None),
                         ("post", "/api/motion/biblio", BON), ("post", "/api/motion/skills/installer",
                                                                {"source": "banc-mit/skills-demo:skills/demo"})):
    r = getattr(cd, meth)(url, **({"json": corps} if corps else {}))
    check(f"X1 {meth.upper()} {url} depuis le réseau → refusé", r.status_code in (401, 403), r.status_code)
from app.api import motion_biblio_routes as MR                      # noqa: E402
import inspect                                                      # noqa: E402
_src_routes = inspect.getsource(MR)
n_routes = len(re.findall(r"@router\.(get|post|patch|delete)\(", _src_routes))
n_gardes = len(re.findall(r"_local\(request\)", _src_routes))
check("X2 chaque route appelle la garde locale", n_routes >= 7 and n_gardes >= n_routes, (n_routes, n_gardes))

class _Client:
    host = "192.168.1.50"


class _Req:
    client = _Client()


try:
    MR._local(_Req()); _l = None
except Exception as e:                                              # noqa: BLE001
    _l = getattr(e, "status_code", None)
check("X3 la garde _local refuse elle-même un client du réseau (403)", _l == 403, _l)

# ── [G] garde anti-contenu tiers ──────────────────────────────────────────────────────────────────────────────────
print("[G] aucun contenu de prompt-motion.com dans le dépôt")
emp = json.loads(EMPREINTES.read_text(encoding="utf-8"))["empreintes"] if EMPREINTES.is_file() else []
check("G1 empreintes présentes (titres + pseudos + extraits)", len(emp) >= 400, len(emp))
check("G2 le fichier d'empreintes ne contient que des empreintes",
      EMPREINTES.is_file() and all(isinstance(n, int) and re.fullmatch(r"[0-9a-f]{12}", t) and
                                   re.fullmatch(r"[0-9a-f]{20}", h) for n, t, h in emp))
TETES = {}
for n, t, h in emp:
    TETES.setdefault(t, []).append((n, h))
_memo = {}
trouves = []
fichiers_suivis = subprocess.run(["git", "ls-files", "-z"], cwd=RACINE, capture_output=True).stdout.split(b"\0")
for rel in fichiers_suivis:
    if not rel:
        continue
    p = RACINE / rel.decode("utf-8", "replace")
    if not p.is_file() or p == EMPREINTES:
        continue
    b = p.read_bytes()
    if b"\0" in b[:8192]:
        continue
    jj = _jetons(b.decode("utf-8", "ignore"))
    for i, j in enumerate(jj):
        t = _memo.get(j)
        if t is None:
            t = _memo[j] = _h_tete(j)
        for n, h in TETES.get(t, ()):
            if _h_phrase(jj[i:i + n]) == h:
                trouves.append((rel.decode("utf-8", "replace"), h))
check(f"G3 {len(fichiers_suivis) - 1} fichiers suivis : aucun titre, pseudo ni extrait tiers", not trouves,
      sorted(set(trouves))[:20])
# Auto-contrôle : le générateur ajoute une phrase TÉMOIN ; écrite ici à l'envers pour que ce banc (relu par G3) ne
# la contienne pas dans l'ordre. Un texte d'essai qui la cite au milieu d'une phrase est attrapé.
_temoin = " ".join(reversed(TEMOIN_ENVERS))
_essai = _jetons(f"Début d'un fichier d'essai. {_temoin.upper()} ! Fin.")
check("G4 la garde attrape une phrase empreinte au milieu d'un texte (témoin)",
      any(_h_phrase(_essai[i:i + n]) == h for i, j in enumerate(_essai) for n, h in TETES.get(_h_tete(j), ())))
# ce banc lui-même ne cite aucun texte tiers : la même garde le relit (il est suivi, donc déjà dans G3)

# ── [E] messages d'erreur traduits ────────────────────────────────────────────────────────────────────────────────
print("[E] traductions L10")
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], cwd=RACINE,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
check("E1 i18n_l10_erreurs.py --check vert", r.returncode == 0, (r.stdout + r.stderr)[-600:])
tr = json.loads((RACINE / "scripts" / "i18n_l10_traductions.json").read_text(encoding="utf-8"))
import ast                                                          # noqa: E402
msgs = set()
for src in (inspect.getsource(MB), _src_routes):
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Raise) and isinstance(nd.exc, ast.Call) and getattr(nd.exc.func, "id", "") in \
                ("ValueError", "RuntimeError", "LookupError", "PermissionError", "HTTPException") and nd.exc.args:
            a = nd.exc.args[-1] if getattr(nd.exc.func, "id", "") == "HTTPException" else nd.exc.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                msgs.add(a.value)
manque = sorted(m for m in msgs if m not in tr)
check(f"E2 les {len(msgs)} messages fixes sont traduits", msgs and not manque, manque)
r = c.post("/api/motion/biblio", json={k: v for k, v in BON.items() if k != "url"},
           headers={"Accept-Language": "en"})
check("E3 le refus d'attribution sort en anglais avec Accept-Language: en", r.status_code == 400
      and "attribution" in r.text.lower() and "obligatoire" not in r.text.lower(), r.text[:200])

print(f"\n{ok} ok, {fail} échec(s)")
sys.exit(1 if fail else 0)
