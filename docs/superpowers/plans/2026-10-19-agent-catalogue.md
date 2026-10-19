# Catalogue des éléments de l'assistant — plan d'implémentation (lots C1, C3, C4)

> **Pour les agents qui exécutent :** SOUS-SKILL OBLIGATOIRE : superpowers:subagent-driven-development (recommandé)
> ou superpowers:executing-plans, tâche par tâche. Étapes en cases `- [ ]`.

**But :** l'assistant « Demander à Deepotus » connaît chaque élément de l'interface : un catalogue généré depuis le
code (C1), une recherche lexicale qui met les bonnes fiches dans le message à chaque question (C3), et le relevé de
l'écran ouvert envoyé avec la question (C4).

**Architecture :** `scripts/agent/catalogue_sources.py` extrait les éléments bruts du code (bundle, labs, Réglages,
fiches) ; `scripts/agent/catalogue.py` les fusionne dans `docs/agent/catalogue/<ecran>.json` sans écraser ce que le
skill `connaissance-agent` a rédigé, et son `--check` refuse un catalogue pas à jour. Côté serveur,
`agent_aide.py` charge le catalogue, construit un index lexical et ajoute deux sections EN FIN de message système
(après « ## Contexte », pour garder le préfixe stable). Côté écran, le tiroir et le répondeur des labs relèvent les
éléments visibles et les envoient avec la question.

**Pile :** Python embarqué (scripts autonomes + bancs pytest avec lanceur), modules ES vanilla, bancs node.

**Spec :** `docs/superpowers/specs/2026-10-19-agent-catalogue-design.md`. **Skill :** `~/.claude/skills/connaissance-agent`
(C5, évalué après C1). **C2** (rédaction initiale écran par écran) se fait ensuite avec le skill.

**Suivi des chantiers :** t245 (C1), t246 (C3), t247 (C4) — passer la tâche `en_cours` au démarrage, `fait` + note à
la fin (ArtifactData, `if_version`).

---

## Conventions (aucun contexte supposé)

- Worktree `C:\Users\olivi\DeepotusVideo-catalogue`, branche `chantier/agent-catalogue` (rebasée sur origin/main bb533b9a).
- `$PY` = `C:\Users\olivi\AppData\Local\DeepotusVideoGen\runtime\python\python.exe` (ignore PYTHONPATH ; chaque banc
  fait son `sys.path.insert`). Bancs depuis `backend/` : `& $PY tests/<banc>.py` ; chaque banc pytest finit par
  `if __name__ == "__main__": sys.exit(pytest.main([__file__, "-q"]))`.
- Bancs node : `node frontend/shared/qa/<nom>.test.mjs`.
- `frontend/shared/x.js` a une copie octet pour octet `frontend/dist/shared/x.js` (`cp`).
- Aucun message d'erreur backend neuf dans ce plan (les entrées invalides sont ignorées) : rien à ajouter à
  `scripts/i18n_l10_traductions.json`. Si un message apparaît quand même : l'y ajouter SANS retrier le fichier puis
  `& $PY scripts/i18n_l10_erreurs.py`.
- Commits : `git add` des fichiers neufs, `git commit --only <fichiers>`, message en français, terminé par
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Pas d'amend, pas de push sans accord.
- Écrans valides (`agent_aide.VUES`) : quick, studio, episodes, sonvfx, montage, scheduler, templates, news, library,
  assets3d, vectorlab, photolab, avatarlive, settings — plus `commun` pour la coque et les dialogues.

## Carte des fichiers

| Fichier | Rôle |
|---|---|
| `scripts/agent/catalogue_sources.py` (créé) | extraction brute depuis le code |
| `scripts/agent/catalogue.py` (créé) | empreinte, fusion, écriture, `--check`, `--rapport` |
| `docs/agent/catalogue/<ecran>.json` (générés) | les fiches, une par ligne |
| `docs/agent/catalogue/_couverture.json` (créé) | `{"ecrans": []}` — écrans dont la rédaction est faite |
| `backend/tests/test_agent_catalogue.py` (créé) | banc C1 |
| `backend/app/services/agent_aide.py` (modifié) | `catalogue()`, index, `chercher`, `rapprocher`, sections, `[POINT:id]` |
| `backend/tests/test_agent_recherche.py` (créé) | banc C3/C4 côté serveur |
| `docs/agent/AGENT.md` (modifié) | règles 7-8 |
| `frontend/shared/dz-agent-logique.js` (modifié) | `releverVisibles` |
| `frontend/shared/dz-agent.js`, `dz-agent-cadre.js` (modifiés) + copies dist | relevé, `visibles` dans les requêtes |
| `frontend/shared/qa/agent_logique.test.mjs`, `backend/tests/test_agent_ecran.py` (modifiés) | bancs C4 |

---

## LOT C1 — le catalogue

### Tâche 1 : sources « i18n » et « bundle »

**Fichiers :** créer `scripts/agent/catalogue_sources.py`, `backend/tests/test_agent_catalogue.py`.

- [ ] **Étape 1 : banc (rouge)** — `backend/tests/test_agent_catalogue.py` :

```python
# -*- coding: utf-8 -*-
"""C1 (spec 2026-10-19-agent-catalogue-design.md) — le catalogue des éléments de l'assistant : extraction depuis le
code (dépôt factice en tmp_path), fusion sans écraser le rédigé, --check, et l'intégrité du vrai catalogue.
Run : & $PY tests/test_agent_catalogue.py   (depuis backend/)"""
import json, pathlib, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "agent"))
sys.path.insert(0, str(RACINE / "backend"))
import catalogue_sources as S                                              # noqa: E402

BUNDLE = ('r.jsx("button",{className:"x",title:dzT("montage.outils.lame_titre"),icon:"dz-action-couper",'
          'children:dzT("montage.outils.lame")});r.jsx(K,{title:dzT("coque.rail.replier")});'
          'r.jsx("button",{onClick:f,title:"Lecture (Espace)"});r.jsx("button",{children:dzT("montage.outils.vide")})')


def _ecrire(p: pathlib.Path, txt: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


@pytest.fixture
def depot(tmp_path):
    i18n = tmp_path / "frontend" / "shared" / "i18n"
    _ecrire(i18n / "montage.json", json.dumps({
        "montage.outils.lame": {"fr": "lame", "en": "blade"},
        "montage.outils.lame_titre": {"fr": "couper le clip", "en": "split the clip"},
        "montage.outils.vide": {"fr": "rien", "en": "nothing"}}, ensure_ascii=False))
    _ecrire(i18n / "coque.json", json.dumps({"coque.rail.replier": {"fr": "Replier", "en": "Collapse"},
                                             "commun.lit.lecture": {"fr": "Lecture (Espace)", "en": "Play (Space)"}}))
    _ecrire(i18n / "vectorlab.json", json.dumps({"vectorlab.core.grille_titre": {"fr": "Grille", "en": "Grid"}}))
    _ecrire(i18n / "photolab.json", json.dumps({"photolab.outil.pinceau": {"fr": "Pinceau", "en": "Brush"}}))
    _ecrire(tmp_path / "frontend" / "dist" / "assets" / "index-TEST.js", BUNDLE)
    _ecrire(tmp_path / "frontend" / "vectorlab" / "js" / "core.js", 'b.title = T("vectorlab.core.grille_titre");')
    _ecrire(tmp_path / "frontend" / "vectorlab" / "index.html", "<html></html>")
    _ecrire(tmp_path / "frontend" / "photolab" / "index.html", "<html></html>")
    _ecrire(tmp_path / "frontend" / "vectorlab" / "aide" / "index.json", json.dumps(
        [{"id": "plume", "titre": "Plume", "phrase": "Trace des courbes.", "titre_en": "Pen", "phrase_en": "Draws curves."}]))
    _ecrire(tmp_path / "backend" / "app" / "api" / "settings_routes.py",
            '_INDEX_FIXE = [\n    ("keys", "Clés API", "clé api jeton"),\n]\n')
    return tmp_path


def test_bundle_bouton_complet(depot):
    e = S.extraire(depot)
    x = e["montage.outils.lame"]
    assert x["type"] == "bouton" and x["ecran"] == "montage" and x["cadre"] is None
    assert x["libelle"] == {"fr": "lame", "en": "blade"}
    assert x["infobulle"] == {"fr": "couper le clip", "en": "split the clip"}
    assert x["icone"] == "dz-action-couper"
    assert set(x["sources"]) == {"i18n:montage.outils.lame", "i18n:montage.outils.lame_titre"}


def test_bundle_infobulle_seule_et_litteral(depot):
    e = S.extraire(depot)
    r = e["coque.rail.replier"]
    assert r["ecran"] == "commun" and r["libelle"] == {"fr": "", "en": ""} and r["infobulle"]["en"] == "Collapse"
    lit = [x for x in e.values() if x["id"].startswith("lit.")]
    assert len(lit) == 1 and lit[0]["infobulle"] == {"fr": "Lecture (Espace)", "en": "Play (Space)"}
    assert lit[0]["ecran"] == "commun"


def test_messages_ecartes(depot):
    assert "montage.outils.vide" not in S.extraire(depot)      # rôle « vide » = un message, pas un élément
```

(La suite du banc arrive aux tâches 2 à 5 ; lanceur ajouté à la tâche 5.)

- [ ] **Étape 2 : lancer** — `& $PY -m pytest tests/test_agent_catalogue.py -q` → `ModuleNotFoundError: catalogue_sources`.

- [ ] **Étape 3 : implémenter** `scripts/agent/catalogue_sources.py` :

```python
# -*- coding: utf-8 -*-
"""Catalogue de l'assistant (spec docs/superpowers/specs/2026-10-19-agent-catalogue-design.md § 2) — les SOURCES.

Lit le CODE du dépôt (jamais l'application en marche) et rend des éléments bruts :
{id, ecran, cadre, type, libelle{fr,en}, infobulle{fr,en}|None, icone, sources[], (reglages, fiche)}.
Aucune rédaction ici : le rôle et les synonymes viennent du skill connaissance-agent (fusion : catalogue.py).
Lancé avec le python embarqué, sans importer l'application.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re

# zone d'une clé i18n (1er segment) → écran de l'app (agent_aide.VUES) ; tout le reste : « commun »
ECRAN_DE_ZONE = {
    "quick": "quick", "studio": "studio", "motion": "studio", "episodes": "episodes", "atelier": "episodes",
    "son": "sonvfx", "sfx": "sonvfx", "vfx": "sonvfx", "montage": "montage", "montage_svm": "montage",
    "subs": "montage", "scheduler": "scheduler", "planif_news": "scheduler", "templates": "templates",
    "news": "news", "biblio": "library", "lib3d": "assets3d", "sprites": "assets3d", "tuiles": "assets3d",
    "cartes": "assets3d", "matiere": "assets3d", "studio3d": "assets3d", "etabli": "assets3d",
    "plateau": "assets3d", "avatar": "avatarlive", "vectorlab": "vectorlab", "photolab": "photolab",
    "reglages": "settings", "espaces": "settings", "transfert": "settings",
}
# zone → lab affiché dans un cadre intégré (les iframes que monte la SPA)
CADRE_DE_ZONE = {"vectorlab": "/vectorlab/", "photolab": "/photolab/", "sprites": "/spritelab/",
                 "tuiles": "/tilelab/", "cartes": "/cardforge/", "matiere": "/materialforge/",
                 "studio3d": "/studio3d/"}
# dernier segment d'une clé qui désigne un MESSAGE (état, erreur), pas un élément cliquable
ROLES_MESSAGES = {"echec", "erreur", "err", "vide", "aucun", "aucune", "chargement", "en_cours", "illisible",
                  "refuse", "fait", "enregistre", "pose", "plusieurs", "un"}
LABS = {"vectorlab": "/vectorlab/", "photolab": "/photolab/"}
LAB_DE_DOSSIER = {"vectorlab": ("vectorlab", "/vectorlab/"), "photolab": ("photolab", "/photolab/"),
                  "spritelab": ("assets3d", "/spritelab/"), "tilelab": ("assets3d", "/tilelab/")}

FENETRE = 600
RE_BOUTON = re.compile(r'"button",\{')
RE_DZT = re.compile(r'(title|children|"aria-label"|label)\s*:\s*dzT\("([a-z0-9_.]+)"\)')
RE_TITRE_LIT = re.compile(r'title:"([^"\\]{3,80})"')
RE_ICONE = re.compile(r'icone?:"(dz-[a-z0-9-]+)"')
RE_T_LAB = re.compile(r'(title|titre|"aria-label"|tip)\s*[:=]\s*(?:T|dzT|t)\("([a-z0-9_.]+)"\)')
VIDE = {"fr": "", "en": ""}


def dictionnaire(racine: pathlib.Path) -> dict:
    d = {}
    for f in sorted((racine / "frontend" / "shared" / "i18n").glob("*.json")):
        d.update(json.loads(f.read_text(encoding="utf-8")))
    return d


def inverse(dico: dict) -> dict:
    """texte FR → texte EN (le bundle garde des libellés FR en clair, traduits par recouvrement exact)."""
    return {v["fr"]: v["en"] for v in dico.values() if isinstance(v, dict) and v.get("fr") and v.get("en")}


def zone(cle: str) -> str:
    return cle.split(".", 1)[0]


def message(cle: str) -> bool:
    return cle.rsplit(".", 1)[-1] in ROLES_MESSAGES


def _texte(dico: dict, cle: str) -> dict:
    v = dico.get(cle) or {}
    return {"fr": v.get("fr", ""), "en": v.get("en", "")}


def _base(cle: str, typ: str, dico: dict) -> dict:
    z = zone(cle)
    return {"id": cle, "ecran": ECRAN_DE_ZONE.get(z, "commun"), "cadre": CADRE_DE_ZONE.get(z), "type": typ,
            "libelle": _texte(dico, cle), "infobulle": None, "icone": None, "sources": [f"i18n:{cle}"]}


def _sha8(t: str) -> str:
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:8]


def _bundle(racine: pathlib.Path) -> str:
    fichiers = sorted((racine / "frontend" / "dist" / "assets").glob("index-*.js"))
    return fichiers[0].read_text(encoding="utf-8") if fichiers else ""


def depuis_bundle(racine: pathlib.Path, dico: dict, inv: dict) -> dict:
    b, out, titres_vus = _bundle(racine), {}, set()
    for m in RE_BOUTON.finditer(b):
        f = b[m.end(): m.end() + FENETRE]
        n = f.find('"button",{')
        f = f if n < 0 else f[:n]
        cles = RE_DZT.findall(f)
        lib = next((k for a, k in cles if a in ("children", "label") and k in dico and not message(k)), None)
        tip = next((k for a, k in cles if a in ("title", '"aria-label"') and k in dico and not message(k)), None)
        ic = RE_ICONE.search(f)
        if lib or tip:
            e = out.setdefault(lib or tip, _base(lib or tip, "bouton", dico))
            e["libelle"] = _texte(dico, lib) if lib else dict(VIDE)
            if tip:
                e["infobulle"] = _texte(dico, tip)
                titres_vus.add(tip)
            if ic:
                e["icone"] = ic.group(1)
            e["sources"] = sorted({f"i18n:{k}" for k in (lib, tip) if k})
            continue
        lit = RE_TITRE_LIT.search(f)
        if lit and re.search(r"[A-Za-zÀ-ÿ]", lit.group(1)):
            fr = lit.group(1)
            i = f"lit.{_sha8(fr)}"
            out[i] = {"id": i, "ecran": "commun", "cadre": None, "type": "bouton", "libelle": dict(VIDE),
                      "infobulle": {"fr": fr, "en": inv.get(fr, fr)}, "icone": ic.group(1) if ic else None,
                      "sources": ["bundle:title"]}
    for a, k in RE_DZT.findall(b):                      # infobulles hors d'un bouton natif (composants à icône)
        if a in ("title", '"aria-label"') and k in dico and not message(k) and k not in titres_vus and k not in out:
            e = _base(k, "bouton", dico)
            e["libelle"], e["infobulle"] = dict(VIDE), _texte(dico, k)
            out[k] = e
    return out


def extraire(racine) -> dict:
    """Tous les éléments bruts du dépôt, par id."""
    racine = pathlib.Path(racine)
    dico = dictionnaire(racine)
    inv = inverse(dico)
    out = {}
    out.update(depuis_bundle(racine, dico, inv))
    return out
```

- [ ] **Étape 4 : lancer** → `3 passed`.
- [ ] **Étape 5 : commit** — `git add scripts/agent/catalogue_sources.py backend/tests/test_agent_catalogue.py` ;
  message « agent : catalogue C1, sources i18n et bundle ».

### Tâche 2 : sources « labs », « Réglages », « fiches »

**Fichiers :** `scripts/agent/catalogue_sources.py`, `backend/tests/test_agent_catalogue.py`.

- [ ] **Étape 1 : tests (rouges)** à ajouter :

```python
def test_labs(depot):
    e = S.extraire(depot)
    g = e["vectorlab.core.grille_titre"]
    assert g["ecran"] == "vectorlab" and g["cadre"] == "/vectorlab/" and g["infobulle"]["en"] == "Grid"
    assert "frontend/vectorlab/js/core.js" in g["sources"]
    p = e["photolab.outil.pinceau"]
    assert p["type"] == "outil" and p["cadre"] == "/photolab/" and p["libelle"]["en"] == "Brush"


def test_reglages_et_fiches(depot):
    e = S.extraire(depot)
    r = e["reglages.keys.cles-api"]
    assert r["type"] == "reglage" and r["ecran"] == "settings" and r["reglages"] == "keys"
    assert r["libelle"]["fr"] == "Clés API"
    f = e["vectorlab.fiche.plume"]
    assert f["fiche"] == "plume" and f["cadre"] == "/vectorlab/" and f["infobulle"]["en"] == "Draws curves."
```

- [ ] **Étape 2 : lancer** → 2 échecs (KeyError).
- [ ] **Étape 3 : implémenter** — ajouter avant `extraire` :

```python
def _slug(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or _sha8(t)


def depuis_labs(racine: pathlib.Path, dico: dict) -> dict:
    out = {}
    for lab, cadre in LABS.items():
        dossier = racine / "frontend" / lab
        fichiers = [dossier / "index.html", *sorted((dossier / "js").glob("*.js"))]
        for f in fichiers:
            if not f.exists():
                continue
            rel = f.relative_to(racine).as_posix()
            for _a, k in RE_T_LAB.findall(f.read_text(encoding="utf-8", errors="replace")):
                if k in dico and not message(k):
                    e = out.get(k) or {**_base(k, "bouton", dico), "ecran": lab, "cadre": cadre,
                                       "libelle": dict(VIDE), "infobulle": _texte(dico, k), "sources": []}
                    e["sources"] = sorted(set(e["sources"]) | {rel})
                    out[k] = e
    for k in dico:                                      # registre des outils du Photolab : photolab.outil.<id>
        if k.startswith("photolab.outil.") and not message(k):
            out[k] = {**_base(k, "outil", dico), "ecran": "photolab", "cadre": "/photolab/"}
    return out


def depuis_reglages(racine: pathlib.Path, inv: dict) -> dict:
    f = racine / "backend" / "app" / "api" / "settings_routes.py"
    if not f.exists():
        return {}
    valeur = []
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "_INDEX_FIXE" for t in n.targets):
            valeur = ast.literal_eval(n.value)
    out = {}
    for section, libelle, _mots in valeur:
        i = f"reglages.{section}.{_slug(libelle)}"
        out[i] = {"id": i, "ecran": "settings", "cadre": None, "type": "reglage",
                  "libelle": {"fr": libelle, "en": inv.get(libelle, libelle)}, "infobulle": None, "icone": None,
                  "sources": ["backend/app/api/settings_routes.py#_INDEX_FIXE"], "reglages": section}
    return out


def depuis_fiches(racine: pathlib.Path) -> dict:
    out = {}
    for f in sorted((racine / "frontend").glob("*/aide/index.json")):
        dossier = f.parent.parent.name
        ecran, cadre = LAB_DE_DOSSIER.get(dossier, ("commun", None))
        for x in json.loads(f.read_text(encoding="utf-8")):
            i = f"{dossier}.fiche.{x['id']}"
            out[i] = {"id": i, "ecran": ecran, "cadre": cadre, "type": "outil",
                      "libelle": {"fr": x["titre"], "en": x.get("titre_en") or x["titre"]},
                      "infobulle": {"fr": x["phrase"], "en": x.get("phrase_en") or x["phrase"]}, "icone": None,
                      "sources": [f.relative_to(racine).as_posix()], "fiche": x["id"]}
    return out
```

et compléter `extraire` :

```python
    out.update(depuis_labs(racine, dico))
    out.update(depuis_reglages(racine, inv))
    out.update(depuis_fiches(racine))
    return out
```

- [ ] **Étape 4 : lancer** → `5 passed`. **Étape 5 : commit** « agent : catalogue C1, sources labs, Réglages et fiches ».

### Tâche 3 : empreinte, fusion, écriture

**Fichiers :** créer `scripts/agent/catalogue.py` ; banc.

- [ ] **Étape 1 : tests (rouges)** :

```python
import catalogue as C                                                       # noqa: E402


def _fiche(i="a.b.c", lib="x", etat=None, role=""):
    f = {"id": i, "ecran": "montage", "cadre": None, "type": "bouton", "libelle": {"fr": lib, "en": lib},
         "infobulle": None, "icone": None, "sources": ["i18n:" + i]}
    if etat:
        f.update(etat=etat, role={"fr": role, "en": role}, synonymes={"fr": ["s"], "en": ["s"]},
                 localisateur={"selecteur": "button", "texte": {"fr": lib, "en": lib}}, guide="montage",
                 empreinte=C.empreinte(f))
    return f


def test_fusion_neuve_et_preservee():
    neuf = C.fusionner({}, {"a.b.c": _fiche()})["a.b.c"]
    assert neuf["etat"] == "extrait" and neuf["role"] == {"fr": "", "en": ""} and neuf["localisateur"] is None
    ancien = _fiche(etat="redige", role="Coupe.")
    f = C.fusionner({"a.b.c": ancien}, {"a.b.c": _fiche()})["a.b.c"]
    assert f["etat"] == "redige" and f["role"]["fr"] == "Coupe." and f["synonymes"]["fr"] == ["s"]
    assert f["localisateur"]["selecteur"] == "button" and f["guide"] == "montage"


def test_fusion_perime_retire_revient():
    ancien = _fiche(etat="redige", role="Coupe.")
    f = C.fusionner({"a.b.c": ancien}, {"a.b.c": _fiche(lib="autre")})["a.b.c"]
    assert f["etat"] == "perime" and f["role"]["fr"] == "Coupe."
    assert C.fusionner({"a.b.c": f}, {"a.b.c": _fiche(lib="autre")})["a.b.c"]["etat"] == "perime"   # reste à relire
    r = C.fusionner({"a.b.c": ancien}, {})["a.b.c"]
    assert r["etat"] == "retire"
    assert C.fusionner({"a.b.c": r}, {"a.b.c": _fiche()})["a.b.c"]["etat"] == "redige"


def test_ecran_fixe_preserve():
    ancien = {**_fiche(etat="redige", role="R"), "ecran": "quick", "ecran_fixe": True}
    assert C.fusionner({"a.b.c": ancien}, {"a.b.c": _fiche()})["a.b.c"]["ecran"] == "quick"


def test_ecriture_stable(tmp_path):
    fiches = C.fusionner({}, {"z.y.x": _fiche("z.y.x"), "a.b.c": _fiche()})
    C.ecrire(tmp_path, fiches)
    txt = (tmp_path / "montage.json").read_text(encoding="utf-8")
    assert txt.index('"a.b.c"') < txt.index('"z.y.x"') and txt.count("\n") == 7
    assert C.charger(tmp_path) == fiches
    C.ecrire(tmp_path, fiches)
    assert (tmp_path / "montage.json").read_text(encoding="utf-8") == txt
```

- [ ] **Étape 2 : lancer** → `ModuleNotFoundError: catalogue`.
- [ ] **Étape 3 : implémenter** `scripts/agent/catalogue.py` :

```python
# -*- coding: utf-8 -*-
"""Catalogue des éléments de l'assistant « Demander » (spec 2026-10-19-agent-catalogue-design.md § 1-2).

  python scripts/agent/catalogue.py              met docs/agent/catalogue/ à jour depuis le code
  python scripts/agent/catalogue.py --check      code 1 si le catalogue n'est pas à jour, ou si un écran couvert
                                                 (_couverture.json) garde des fiches extrait/perime/retire
  python scripts/agent/catalogue.py --rapport    par écran : nombre de fiches par état

Fusion SANS écraser : role, synonymes, localisateur, guide, notes (et l'écran si ecran_fixe) viennent du skill
connaissance-agent et sont toujours gardés. Une fiche neuve est « extrait » ; une fiche rédigée dont la source change
devient « perime » ; une fiche dont la source disparaît devient « retire » (le skill la supprime).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import catalogue_sources as S                                               # noqa: E402

RACINE = ICI.parents[1]
DOSSIER = RACINE / "docs" / "agent" / "catalogue"
ETATS = ("extrait", "redige", "perime", "retire")
GARDES = ("role", "synonymes", "localisateur", "guide", "notes")
ORDRE = ("id", "ecran", "ecran_fixe", "cadre", "type", "libelle", "infobulle", "icone", "reglages", "fiche", "role",
         "synonymes", "guide", "localisateur", "notes", "sources", "empreinte", "etat")


def empreinte(e: dict) -> str:
    vu = {k: e.get(k) for k in ("type", "libelle", "infobulle", "icone")}
    return hashlib.sha1(json.dumps(vu, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def fusionner(existants: dict, extraits: dict) -> dict:
    out = {}
    for i, brut in extraits.items():
        e = dict(brut)
        e["empreinte"] = empreinte(e)
        a = existants.get(i)
        if a is None:
            e.update(role={"fr": "", "en": ""}, synonymes={"fr": [], "en": []}, localisateur=None, guide=None,
                     etat="extrait")
        else:
            for k in GARDES:
                if k in a:
                    e[k] = a[k]
            e.setdefault("role", {"fr": "", "en": ""})
            e.setdefault("synonymes", {"fr": [], "en": []})
            e.setdefault("localisateur", None)
            e.setdefault("guide", None)
            if a.get("ecran_fixe"):
                e["ecran"], e["ecran_fixe"] = a["ecran"], True
            if a.get("etat") == "retire":
                e["etat"] = "redige" if (a.get("role") or {}).get("fr") else "extrait"
            elif a.get("etat") == "redige" and a.get("empreinte") != e["empreinte"]:
                e["etat"] = "perime"
            else:
                e["etat"] = a.get("etat", "extrait")
        out[i] = e
    for i, a in existants.items():
        if i not in out:
            out[i] = {**a, "etat": "retire"}
    return out


def _ligne(f: dict) -> str:
    rang = {k: n for n, k in enumerate(ORDRE)}
    return json.dumps({k: f[k] for k in sorted(f, key=lambda k: rang.get(k, 99))}, ensure_ascii=False)


def texte_fichier(ecran: str, fiches: list) -> str:
    lignes = ",\n".join("    " + _ligne(f) for f in sorted(fiches, key=lambda f: f["id"]))
    return '{\n  "ecran": ' + json.dumps(ecran) + ',\n  "fiches": [\n' + lignes + "\n  ]\n}\n"


def par_ecran(fiches: dict) -> dict:
    g = {}
    for f in fiches.values():
        g.setdefault(f.get("ecran") or "commun", []).append(f)
    return g


def charger(dossier=DOSSIER) -> dict:
    out = {}
    for f in sorted(pathlib.Path(dossier).glob("*.json")):
        if not f.name.startswith("_"):
            for x in json.loads(f.read_text(encoding="utf-8"))["fiches"]:
                out[x["id"]] = x
    return out


def ecrire(dossier, fiches: dict) -> None:
    dossier = pathlib.Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    groupes = par_ecran(fiches)
    for f in dossier.glob("*.json"):
        if not f.name.startswith("_") and f.stem not in groupes:
            f.unlink()
    for ecran, liste in groupes.items():
        (dossier / f"{ecran}.json").write_text(texte_fichier(ecran, liste), encoding="utf-8", newline="\n")
```

- [ ] **Étape 4 : lancer** → `9 passed`. **Étape 5 : commit** « agent : catalogue C1, fusion sans écraser et écriture stable ».

### Tâche 4 : `--check` et `--rapport`

- [ ] **Étape 1 : tests (rouges)** :

```python
def test_check(depot):
    d = depot / "docs" / "agent" / "catalogue"
    assert C.main(["--racine", str(depot)]) == 0
    _ecrire(d / "_couverture.json", '{"ecrans": []}')
    assert C.main(["--racine", str(depot), "--check"]) == 0
    i18n = depot / "frontend" / "shared" / "i18n" / "montage.json"
    i18n.write_text(i18n.read_text(encoding="utf-8").replace("couper le clip", "scinder le clip"), encoding="utf-8")
    assert C.main(["--racine", str(depot), "--check"]) == 1                 # pas à jour : il faut relancer
    assert C.main(["--racine", str(depot)]) == 0
    assert C.main(["--racine", str(depot), "--check"]) == 0
    _ecrire(d / "_couverture.json", '{"ecrans": ["montage"]}')
    assert C.main(["--racine", str(depot), "--check"]) == 1                 # écran couvert avec du « extrait »


def test_rapport(depot, capsys):
    C.main(["--racine", str(depot)])
    assert C.main(["--racine", str(depot), "--rapport"]) == 0
    sortie = capsys.readouterr().out
    assert "montage" in sortie and "extrait" in sortie
```

- [ ] **Étape 2 : lancer** → AttributeError `main`.
- [ ] **Étape 3 : implémenter** — à la fin de `catalogue.py` :

```python
def calculer(racine: pathlib.Path) -> tuple[pathlib.Path, dict, dict]:
    dossier = racine / "docs" / "agent" / "catalogue"
    existants = charger(dossier) if dossier.is_dir() else {}
    return dossier, existants, fusionner(existants, S.extraire(racine))


def couverture(dossier: pathlib.Path) -> list:
    f = dossier / "_couverture.json"
    return json.loads(f.read_text(encoding="utf-8")).get("ecrans", []) if f.exists() else []


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    racine = pathlib.Path(argv[argv.index("--racine") + 1]) if "--racine" in argv else RACINE
    dossier, existants, fiches = calculer(racine)
    if "--check" in argv:
        attendu = {e: texte_fichier(e, l) for e, l in par_ecran(fiches).items()}
        present = {f.stem: f.read_text(encoding="utf-8") for f in dossier.glob("*.json")
                   if not f.name.startswith("_")} if dossier.is_dir() else {}
        if attendu != present:
            print("catalogue PAS à jour : lance python scripts/agent/catalogue.py puis le skill connaissance-agent")
            return 1
        couverts = set(couverture(dossier))
        reste = sorted(f["id"] for f in fiches.values() if f.get("ecran") in couverts and f["etat"] != "redige")
        if reste:
            print(f"{len(reste)} fiche(s) à rédiger sur des écrans couverts : {', '.join(reste[:20])}")
            return 1
        print(f"catalogue à jour : {len(fiches)} fiches")
        return 0
    if "--rapport" in argv:
        for ecran, liste in sorted(par_ecran(fiches).items()):
            n = {e: sum(1 for f in liste if f["etat"] == e) for e in ETATS}
            print(f"{ecran:12} " + "  ".join(f"{e}={n[e]}" for e in ETATS))
        return 0
    ecrire(dossier, fiches)
    print(f"{len(fiches)} fiches écrites dans {dossier}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
```

- [ ] **Étape 4 : lancer** → `11 passed`. **Étape 5 : commit** « agent : catalogue C1, --check et --rapport ».

### Tâche 5 : générer le vrai catalogue + banc d'intégrité

- [ ] **Étape 1 : générer** — depuis la racine : `& $PY scripts/agent/catalogue.py` puis `--rapport`. Créer
  `docs/agent/catalogue/_couverture.json` = `{"ecrans": []}`. Lire le rapport : chaque écran doit avoir des fiches ;
  si un écran attendu est vide (ex. `library`), vérifier la zone dans `ECRAN_DE_ZONE` (banc d'abord, puis correctif).
- [ ] **Étape 2 : tests d'intégrité (sur le vrai dépôt)** + lanceur :

```python
VUES = ("quick", "studio", "episodes", "sonvfx", "montage", "scheduler", "templates", "news", "library", "assets3d",
        "vectorlab", "photolab", "avatarlive", "settings", "commun")
CADRES = {None, "/vectorlab/", "/photolab/", "/spritelab/", "/tilelab/", "/cardforge/", "/materialforge/", "/studio3d/"}


def test_vrai_catalogue_a_jour():
    assert C.main(["--check"]) == 0


def test_vrai_catalogue_integre():
    fiches = C.charger()
    assert len(fiches) >= 300, len(fiches)
    chapitres = {c["id"] for c in json.loads((RACINE / "docs/guide/src/chapitres.json")
                                             .read_text(encoding="utf-8"))["chapitres"]}
    for f in fiches.values():
        assert f["ecran"] in VUES and f.get("cadre") in CADRES and f["etat"] in C.ETATS, f["id"]
        assert f.get("guide") in (None, *chapitres), f["id"]
        if f["etat"] == "redige":
            for l in ("fr", "en"):
                assert 0 < len(f["role"][l]) <= 300, (f["id"], l)
                assert isinstance(f["synonymes"][l], list), (f["id"], l)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

- [ ] **Étape 3 : lancer** → `13 passed` ; `& $PY tests/test_hygiene_lanceurs.py` vert.
- [ ] **Étape 4 : commit** — `git add docs/agent/catalogue` ; message « agent : catalogue C1, catalogue généré
  (N fiches) et banc d'intégrité » (N = nombre réel).
- [ ] **Étape 5 : suivi** — t245 → `fait` (note : commit, N fiches, rapport par écran) ; t244 (skill) : noter
  « prêt à évaluer ».

---

## LOT C3 — la recherche dans « demander »

### Tâche 6 : charger le catalogue, index lexical, `chercher`

**Fichiers :** `backend/app/services/agent_aide.py` ; créer `backend/tests/test_agent_recherche.py`.

- [ ] **Étape 1 : banc (rouge)** :

```python
# -*- coding: utf-8 -*-
"""C3/C4 (spec 2026-10-19-agent-catalogue-design.md § 4) — la recherche dans le catalogue, les sections du message
système, [POINT:id] sur une fiche, le relevé de l'écran ouvert côté serveur.
Run : & $PY tests/test_agent_recherche.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrech_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import agent_aide as A                                    # noqa: E402

LOC = {"selecteur": "button", "texte": {"fr": "lame · Alt+C", "en": "blade · Alt+C"}}
FAUX = {
    "montage.lame": {"id": "montage.lame", "ecran": "montage", "cadre": None, "type": "bouton",
                     "libelle": {"fr": "lame · Alt+C", "en": "blade · Alt+C"},
                     "infobulle": {"fr": "couper le clip à la tête", "en": "split the clip at the playhead"},
                     "role": {"fr": "Coupe le clip sélectionné à la tête de lecture.", "en": "Splits the clip."},
                     "synonymes": {"fr": ["scinder", "rasoir"], "en": ["cut", "razor"]},
                     "localisateur": LOC, "etat": "redige"},
    "vectorlab.creer": {"id": "vectorlab.creer", "ecran": "vectorlab", "cadre": "/vectorlab/", "type": "bouton",
                        "libelle": {"fr": "Créer", "en": "Create"}, "infobulle": None,
                        "role": {"fr": "", "en": ""}, "synonymes": {"fr": [], "en": []},
                        "localisateur": None, "etat": "extrait"},
    "photolab.couper": {"id": "photolab.couper", "ecran": "photolab", "cadre": "/photolab/", "type": "outil",
                        "libelle": {"fr": "Recadrage", "en": "Crop"}, "infobulle": None,
                        "role": {"fr": "Coupe les bords de l'image.", "en": "Crops the image."},
                        "synonymes": {"fr": ["couper"], "en": []}, "localisateur": None, "etat": "redige"},
}


@pytest.fixture
def faux(monkeypatch):
    monkeypatch.setattr(A, "catalogue", lambda: FAUX)
    A._index.cache_clear()
    A._par_texte.cache_clear()
    yield
    A._index.cache_clear()
    A._par_texte.cache_clear()


def test_synonymes_et_accents(faux):
    assert [x["id"] for x in A.chercher("scinder une séquence")][:1] == ["montage.lame"]
    assert A.chercher("creer")[0]["id"] == "vectorlab.creer"                 # accents ignorés
    assert A.chercher("") == [] and A.chercher("le la de") == []


def test_bonus_ecran_et_visible(faux):
    ids = [x["id"] for x in A.chercher("couper", "photolab")]
    assert ids[0] == "photolab.couper"
    ids = [x["id"] for x in A.chercher("couper", "photolab", visibles=["montage.lame"])]
    assert ids[0] == "montage.lame"
    assert len(A.chercher("couper", n=1)) == 1


def test_vrai_catalogue_charge():
    A.catalogue.cache_clear()
    A._index.cache_clear()
    assert len(A.catalogue()) >= 300
    assert all(f["etat"] != "retire" for f in A.catalogue().values())
```

- [ ] **Étape 2 : lancer** → `AttributeError: catalogue`.
- [ ] **Étape 3 : implémenter** dans `agent_aide.py` (imports `math`, `collections.Counter` en tête) :

```python
CATALOGUE = DOSSIER / "catalogue"
MAX_PERTINENTS = 15
POIDS = (("libelle", 3.0), ("synonymes", 3.0), ("infobulle", 2.0), ("role", 1.0))
MOTS_VIDES = {"le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "en", "au", "aux", "je", "tu", "il",
              "on", "ce", "ca", "est", "pour", "par", "sur", "dans", "avec", "comment", "quoi", "que", "qui", "mon",
              "ma", "mes", "the", "a", "an", "of", "to", "in", "on", "is", "how", "do", "i", "my", "what", "where"}


@lru_cache(maxsize=1)
def catalogue() -> dict:
    """Les fiches non retirées de docs/agent/catalogue/*.json (lues une fois par processus)."""
    fiches = {}
    if CATALOGUE.is_dir():
        for f in sorted(CATALOGUE.glob("*.json")):
            if f.name.startswith("_"):
                continue
            for x in json.loads(f.read_text(encoding="utf-8"))["fiches"]:
                if x.get("etat") != "retire":
                    fiches[x["id"]] = x
    return fiches


def _mots(t) -> list:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return [m for m in re.findall(r"[a-z0-9]+", t) if len(m) >= 2 and m not in MOTS_VIDES]


def _racine(m: str) -> str:
    return m[:5] if len(m) > 5 else m           # « coupe », « couper », « coupez » se rejoignent


@lru_cache(maxsize=1)
def _index() -> tuple:
    docs, df = {}, Counter()
    for i, x in catalogue().items():
        poids = {}
        for champ, w in POIDS:
            v = x.get(champ) or {}
            for lang in ("fr", "en"):
                t = v.get(lang) if isinstance(v, dict) else None
                t = " ".join(t) if isinstance(t, list) else (t or "")
                for m in _mots(t):
                    r = _racine(m)
                    poids[r] = max(poids.get(r, 0.0), w)
        docs[i] = poids
        df.update(poids.keys())
    n = max(1, len(docs))
    return docs, {r: math.log(1 + n / c) for r, c in df.items()}


def chercher(question, ecran: str = "", visibles=(), n: int = MAX_PERTINENTS) -> list:
    """Les fiches les plus proches de la question : mots communs pondérés par champ et par rareté, ×1,5 sur l'écran
    ouvert, +3 pour un élément visible maintenant. [] si la question n'a aucun mot utile."""
    q = {_racine(m) for m in _mots(question)}
    if not q:
        return []
    docs, idf = _index()
    fiches, vis, res = catalogue(), set(visibles or ()), []
    for i, poids in docs.items():
        s = sum(poids[r] * idf.get(r, 0.0) for r in q if r in poids)
        if not s:
            continue
        if ecran and fiches[i].get("ecran") == ecran:
            s *= 1.5
        if i in vis:
            s += 3.0
        res.append((-s, i))
    return [fiches[i] for _, i in sorted(res)[:n]]
```

(`_par_texte` est créé à la tâche 9 ; d'ici là, retirer ses deux lignes de la fixture ou créer tout de suite
`@lru_cache(maxsize=1) def _par_texte() -> dict: return {}` pour que la fixture passe — on le remplit en tâche 9.)

- [ ] **Étape 4 : lancer** → `3 passed`. **Étape 5 : commit** « agent : C3, catalogue chargé et recherche lexicale ».

### Tâche 7 : sections du message système et `[POINT:id]` sur une fiche

- [ ] **Étape 1 : tests (rouges)** :

```python
def test_sections_apres_contexte(faux):
    s = A.systeme("montage", "fr", "", pertinents=A.chercher("scinder"),
                  visibles={"reconnus": [FAUX["vectorlab.creer"]], "inconnus": [{"t": "Bidule", "i": "fait un truc"}]})
    tete, fin = s.split("## Contexte")
    assert "## Éléments pertinents" not in tete and "## Éléments pertinents" in fin
    assert "montage.lame (montage) « lame · Alt+C » [pointable] : Coupe le clip" in fin
    assert "## À l'écran maintenant" in fin and "vectorlab.creer « Créer »" in fin
    assert "« Bidule » (fait un truc) — non documenté" in fin
    assert A.systeme("quick", "fr", "").split("## Contexte")[0] == tete      # préfixe stable


def test_fiche_non_redigee_signalee(faux):
    s = A.systeme("vectorlab", "en", "", pertinents=[FAUX["vectorlab.creer"]])
    assert "vectorlab.creer (vectorlab) « Create » : — not written yet: describe only what is visible" in s


def test_point_sur_fiche(faux):
    _, actions, rejets = A.analyser("[POINT:montage.lame] [POINT:vectorlab.creer]")
    assert rejets == 1 and len(actions) == 1
    a = actions[0]
    assert a["type"] == "point" and a["selecteur"] == "button" and a["texte"] == LOC["texte"]
    assert a["ecran"] == "montage" and a["fr"] == "lame · Alt+C" and a["partout"] is False
```

- [ ] **Étape 2 : lancer** → TypeError (argument `pertinents`).
- [ ] **Étape 3 : implémenter** — remplacer `systeme` et compléter `_action` :

```python
NON_REDIGE = {"fr": "— pas encore rédigé : décris seulement ce qui est visible",
              "en": "— not written yet: describe only what is visible"}
NON_DOCUMENTE = {"fr": "non documenté", "en": "not documented"}


def _fiche_ligne(x: dict, cle: str, avec_role: bool = True) -> str:
    lib = ((x.get("libelle") or {}).get(cle) or (x.get("infobulle") or {}).get(cle) or x["id"])
    pt = " [pointable]" if x.get("localisateur") else ""
    ou = x.get("ecran") or "partout"
    if not avec_role:
        return f"- {x['id']} « {lib} »{pt}"
    role = (x.get("role") or {}).get(cle) or ""
    return f"- {x['id']} ({ou}) « {lib} »{pt} : {role or NON_REDIGE[cle]}"


def systeme(ecran: str, lang: str, espace: str = "", pertinents=(), visibles=None) -> str:
    """AGENT.md + chapitres + « Je veux… » + ancres + vues, puis « ## Contexte » ; les sections qui changent à chaque
    question (éléments pertinents, écran relevé) viennent APRÈS, pour garder le préfixe identique (cache)."""
    ecran, espace = _ligne(ecran, 30), _ligne(espace)
    k = connaissance()
    en = lang == "en"
    cle = "en" if en else "fr"
    chap = "\n".join(f"- {c['id']} : {c[cle]}" for c in k["chapitres"].values())
    jv = "\n".join(f"- {e[cle]} → {e['cible']}" for e in k["jeveux"])
    anc = "\n".join(f"- {a['id']} ({'partout' if a.get('partout') or not a.get('ecran') else a['ecran']}) : {a[cle]}"
                    for a in k["ancres"].values())
    s = (f"{k['agent']}\n\n## Chapitres (id : titre)\n{chap}\n\n## Je veux…\n{jv}\n\n"
         f"## Ancres (id (écran) : libellé)\n{anc}\n\n## Vues\n{', '.join(VUES)}\n\n"
         f"## Contexte\n- écran ouvert : {ecran or 'inconnu'}\n- espace de marque actif : {espace or 'inconnu'}\n"
         f"- langue : {'English' if en else 'français'}\n")
    if pertinents:
        s += "\n## Éléments pertinents (id (écran) « libellé » : rôle)\n" + "\n".join(
            _fiche_ligne(x, cle) for x in pertinents) + "\n"
    if visibles and (visibles.get("reconnus") or visibles.get("inconnus")):
        lignes = [_fiche_ligne(x, cle, avec_role=False) for x in visibles.get("reconnus", [])]
        lignes += [f"- « {v['t'] or v['i']} »" + (f" ({v['i']})" if v["t"] and v["i"] else "")
                   + f" — {NON_DOCUMENTE[cle]}" for v in visibles.get("inconnus", [])]
        s += "\n## À l'écran maintenant\n" + "\n".join(lignes) + "\n"
    return s
```

Dans `_action`, juste APRÈS le bloc des ancres (`if typ == "POINT" and cible in k["ancres"]: …`) :

```python
    if typ == "POINT" and cible in catalogue() and catalogue()[cible].get("localisateur"):
        x = catalogue()[cible]
        loc = x["localisateur"]
        lib = x.get("libelle") or {}
        tip = x.get("infobulle") or {}
        return {"type": "point", "cible": cible, "ecran": None if x.get("ecran") == "commun" else x.get("ecran"),
                "selecteur": loc.get("selecteur"), "texte": loc.get("texte"), "cadre": x.get("cadre") or loc.get("cadre"),
                "reglages": loc.get("reglages"), "partout": bool(loc.get("partout") or x.get("ecran") == "commun"),
                "libelle": loc.get("libelle"), "fr": lib.get("fr") or tip.get("fr") or cible,
                "en": lib.get("en") or tip.get("en") or cible}
```

- [ ] **Étape 4 : lancer** → `6 passed` ; `& $PY tests/test_agent_aide.py` et `tests/test_agent_connaissance.py` verts
  (le préfixe et l'ancien contrat de `systeme(ecran, lang, espace)` ne changent pas).
- [ ] **Étape 5 : commit** « agent : C3, sections pertinentes en fin de message, POINT sur une fiche ».

### Tâche 8 : brancher dans `demander` / `estimer_vue`, règles d'AGENT.md

- [ ] **Étape 1 : tests (rouges)** — dans `test_agent_recherche.py` :

```python
from app.services import moteurs_texte as MT                                # noqa: E402


def test_demander_envoie_les_pertinents(faux, monkeypatch):
    vu = {}

    async def faux_tirer(moteur, modele, prompt, systeme, max_tokens=4000, json=False, **kw):
        vu["systeme"] = systeme
        return "Utilise la lame.\n[POINT:montage.lame]"

    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "anthropic")
    monkeypatch.setattr(MT, "tirer_garde", faux_tirer)
    monkeypatch.setattr(A, "_espace", lambda: "")
    r = asyncio.run(A.demander({"question": "comment scinder un clip ?", "ecran": "montage", "lang": "fr"}))
    assert "## Éléments pertinents" in vu["systeme"] and "montage.lame" in vu["systeme"]
    assert r["actions"][0]["cible"] == "montage.lame"
```

et dans `backend/tests/test_agent_connaissance.py` :

```python
def test_agent_md_regles_catalogue():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    assert "Éléments pertinents" in t and "non documenté" in t and "[pointable]" in t
```

- [ ] **Étape 2 : lancer** → échecs (section absente, règles absentes).
- [ ] **Étape 3 : implémenter** — dans `agent_aide.py`, un seul point qui construit le message de la question :

```python
def _systeme_question(p: dict) -> str:
    vis = rapprocher(p.get("visibles") or [], p["lang"]) if p.get("visibles") else None
    ids = [x["id"] for x in (vis or {}).get("reconnus", [])]
    return systeme(p["ecran"], p["lang"], _espace(), pertinents=chercher(p["q"], p["ecran"], ids), visibles=vis)
```

(`rapprocher` arrive en tâche 9 : d'ici là, `p.get("visibles")` est toujours vide et la ligne ne s'exécute pas.)
Remplacer `systeme(p["ecran"], lang, _espace())` dans `demander` et
`systeme(p["ecran"], p["lang"], _espace())` dans `estimer_vue` par `_systeme_question(p)` (le devis et l'envoi
gardent le même texte).

Dans `docs/agent/AGENT.md`, section « Comment répondre », ajouter après la dernière règle numérotée (adapter les
numéros) :

```markdown
7. Pour décrire un bouton, une icône, un outil ou un réglage, appuie-toi sur sa fiche (« Éléments pertinents »,
   « À l'écran maintenant ») ; une fiche « pas encore rédigé » ou un élément « non documenté » se décrit seulement
   par son libellé et son infobulle, et tu dis que tu n'as pas sa description détaillée.
8. `[POINT:<id>]` marche pour une ancre de la liste « Ancres » ou pour une fiche marquée [pointable].
```

- [ ] **Étape 4 : lancer** — `test_agent_recherche.py` (7 passed), `test_agent_connaissance.py`, `test_agent_aide.py`
  verts.
- [ ] **Étape 5 : commit** « agent : C3, recherche branchée dans demander et estimer, règles d'AGENT.md » ;
  suivi t246 → `fait`.

---

## LOT C4 — le relevé de l'écran ouvert

### Tâche 9 : côté serveur — `visibles` bornés et `rapprocher`

- [ ] **Étape 1 : tests (rouges)** — `test_agent_recherche.py` :

```python
def test_visibles_bornes():
    v = A._visibles([{"t": "x" * 200, "i": "a\u202eb"}, "pas un objet", {"t": 3}, {"t": "", "i": ""}]
                    + [{"t": f"b{n}", "i": ""} for n in range(200)])
    assert v[0] == {"t": "x" * 80, "i": "ab"} and len(v) == A.MAX_VISIBLES
    assert A._visibles(None) == [] and A._visibles("x") == []


def test_rapprocher(faux):
    r = A.rapprocher([{"t": "lame · Alt+C", "i": ""}, {"t": "", "i": "Create"}, {"t": "Truc", "i": "inconnu"}], "fr")
    assert [x["id"] for x in r["reconnus"]] == ["montage.lame", "vectorlab.creer"]
    assert r["inconnus"] == [{"t": "Truc", "i": "inconnu"}]


def test_demander_avec_visibles(faux, monkeypatch):
    vu = {}

    async def faux_tirer(moteur, modele, prompt, systeme, max_tokens=4000, json=False, **kw):
        vu["systeme"] = systeme
        return "ok"

    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "anthropic")
    monkeypatch.setattr(MT, "tirer_garde", faux_tirer)
    monkeypatch.setattr(A, "_espace", lambda: "")
    asyncio.run(A.demander({"question": "à quoi sert ce bouton ?", "ecran": "montage", "lang": "fr",
                            "visibles": [{"t": "lame · Alt+C", "i": ""}, {"t": "Zorg", "i": ""}]}))
    assert "## À l'écran maintenant" in vu["systeme"] and "« Zorg » — non documenté" in vu["systeme"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

- [ ] **Étape 2 : lancer** → AttributeError `_visibles`.
- [ ] **Étape 3 : implémenter** dans `agent_aide.py` :

```python
MAX_VISIBLES = 120
MAX_TEXTE_VISIBLE = 80
MAX_RECONNUS = 40
MAX_INCONNUS = 30


def _visibles(v) -> list:
    """Le relevé de l'écran envoyé par le tiroir, borné et nettoyé ; une entrée illisible est ignorée (pas d'erreur :
    le relevé n'est qu'un contexte)."""
    if not isinstance(v, list):
        return []
    out = []
    for x in v:
        if len(out) >= MAX_VISIBLES:
            break
        if not isinstance(x, dict):
            continue
        t = x.get("t") if isinstance(x.get("t"), str) else ""
        i = x.get("i") if isinstance(x.get("i"), str) else ""
        t, i = _ligne(_sans_controle(t), MAX_TEXTE_VISIBLE), _ligne(_sans_controle(i), MAX_TEXTE_VISIBLE)
        if t or i:
            out.append({"t": t, "i": i})
    return out


def _cle_texte(t) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


@lru_cache(maxsize=1)
def _par_texte() -> dict:
    """texte normalisé (libellé ou infobulle, FR et EN) → id de fiche (le premier par ordre d'id)."""
    out = {}
    for i in sorted(catalogue()):
        x = catalogue()[i]
        for champ in ("libelle", "infobulle"):
            for lang in ("fr", "en"):
                c = _cle_texte((x.get(champ) or {}).get(lang))
                if c:
                    out.setdefault(c, i)
    return out


def rapprocher(visibles: list, lang: str = "fr") -> dict:
    """{reconnus: [fiches], inconnus: [{t, i}]} — un élément visible est reconnu par son texte, sinon son infobulle."""
    idx, fiches, rec, inc, vus = _par_texte(), catalogue(), [], [], set()
    for v in visibles:
        i = idx.get(_cle_texte(v["t"])) or idx.get(_cle_texte(v["i"]))
        if i and i not in vus:
            vus.add(i)
            if len(rec) < MAX_RECONNUS:
                rec.append(fiches[i])
        elif not i and len(inc) < MAX_INCONNUS:
            inc.append(v)
    return {"reconnus": rec, "inconnus": inc}
```

(si la tâche 6 a créé un `_par_texte` vide provisoire, le remplacer par celui-ci) et dans `_preparer`, ajouter à
l'objet rendu : `"visibles": _visibles(corps.get("visibles")),`.

- [ ] **Étape 4 : lancer** → `test_agent_recherche.py` 10 passed ; `test_agent_aide.py` vert.
- [ ] **Étape 5 : commit** « agent : C4, relevé de l'écran borné et rapproché du catalogue (serveur) ».

### Tâche 10 : côté écran — `releverVisibles` (logique pure)

**Fichiers :** `frontend/shared/dz-agent-logique.js`, `frontend/shared/qa/agent_logique.test.mjs`.

- [ ] **Étape 1 : tests (rouges)** — ajouter au banc node, avant le contrôle « aucun objet du navigateur » :

```js
// C4 — relevé des éléments visibles (faux document)
const faux = (els) => ({ querySelectorAll: () => els });
const n = (t, title, w = 10, vis = true) => ({
  textContent: t, getAttribute: (a) => (a === "title" ? title : null),
  getBoundingClientRect: () => ({ width: vis ? w : 0, height: vis ? 10 : 0 }),
});
const rel = L.releverVisibles(faux([n("Rendre", "Rendu final"), n("Rendre", "Rendu final"), n("caché", "", 10, false),
  n("  a\n b  ", ""), n("", ""), n("x".repeat(200), "")]));
assert.deepEqual(rel.slice(0, 2), [{ t: "Rendre", i: "Rendu final" }, { t: "a b", i: "" }]);
assert.equal(rel.length, 3, "doublon, invisible et vide écartés");
assert.equal(rel[2].t.length, 80);
assert.equal(L.releverVisibles(faux(Array.from({ length: 300 }, (_, k) => n("b" + k, "")))).length, L.MAX_VISIBLES);
assert.deepEqual(L.releverVisibles(faux([n("moi", "")]), () => true), [], "exclure() écarte le tiroir");
assert.deepEqual(L.releverVisibles({ querySelectorAll: () => { throw new Error("x"); } }), []);
```

- [ ] **Étape 2 : lancer** `node frontend/shared/qa/agent_logique.test.mjs` → TypeError `releverVisibles`.
- [ ] **Étape 3 : implémenter** dans `dz-agent-logique.js` :

```js
// C4 (spec 2026-10-19-agent-catalogue-design.md § 4) : les éléments visibles de l'écran ouvert, envoyés avec la
// question ; texte + infobulle seulement (jamais le contenu des documents), bornés.
export const MAX_VISIBLES = 120;
const MAX_TEXTE = 80;
const SEL_VISIBLES = 'button, [role="tab"], [role="menuitem"], a[href], [title], [aria-label]';
const court = (s) => String(s || "").replace(/\s+/g, " ").trim().slice(0, MAX_TEXTE);

export function releverVisibles(doc, exclure = () => false, max = MAX_VISIBLES) {
  let noeuds = [];
  try { noeuds = Array.from(doc.querySelectorAll(SEL_VISIBLES)); } catch (e) { return []; }
  const out = [], vus = new Set();
  for (const x of noeuds) {
    if (out.length >= max) break;
    if (exclure(x)) continue;
    const r = x.getBoundingClientRect();
    if (!(r.width > 0 && r.height > 0)) continue;
    const t = court(x.textContent), i = court(x.getAttribute("title") || x.getAttribute("aria-label") || "");
    if (!t && !i) continue;
    const k = t + "\u0001" + i;
    if (vus.has(k)) continue;
    vus.add(k);
    out.push({ t, i });
  }
  return out;
}
```

- [ ] **Étape 4 : lancer** → `agent_logique : OK`. `cp frontend/shared/dz-agent-logique.js frontend/dist/shared/`.
- [ ] **Étape 5 : commit** « agent : C4, relevé des éléments visibles (logique) ».

### Tâche 11 : le tiroir et le répondeur des labs envoient le relevé

**Fichiers :** `frontend/shared/dz-agent.js`, `frontend/shared/dz-agent-cadre.js` (+ copies dist),
`backend/tests/test_agent_ecran.py`.

- [ ] **Étape 1 : tests (rouges)** — `test_agent_ecran.py` :

```python
def test_releve_envoye():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert src.count("visibles: await releve()") == 2, "question texte ET question avec capture"
    assert "releverVisibles(document" in src and 'dzAgent: "releve"' in src
    cadre = (SHARED / "dz-agent-cadre.js").read_text(encoding="utf-8")
    assert 'd.dzAgent === "releve"' in cadre and 'dzAgent: "visibles"' in cadre
    assert cadre.count("ev.origin !== location.origin") == 1   # une seule garde, en tête, pour les deux messages
```

- [ ] **Étape 2 : lancer** → FAIL.
- [ ] **Étape 3 : implémenter.**

`dz-agent-cadre.js` — remplacer la condition de type en tête du gestionnaire et ajouter la branche « releve »
(importer `releverVisibles`) :

```js
import { choisir, candidats, releverVisibles } from "./dz-agent-logique.js";
// …
    const d = ev.data;
    if (d && d.dzAgent === "releve") {
      ev.source.postMessage({ dzAgent: "visibles", id: d.id, items: releverVisibles(document) }, location.origin);
      return;
    }
    if (!d || d.dzAgent !== "trouve" || typeof d.selecteur !== "string") return;
```

`dz-agent.js` — importer `releverVisibles, MAX_VISIBLES` ; ajouter, près de `demanderAuCadre` :

```js
  // C4 : le relevé de l'écran ouvert — la page (hors tiroir et bouton) + le lab visible, s'il y en a un
  const LABS_CADRES = /^\/(vectorlab|photolab|spritelab|tilelab|cardforge|materialforge|studio3d)\//;
  function cadreVisible() {
    return Array.from(document.querySelectorAll("iframe")).find((f) => {
      const r = f.getBoundingClientRect();
      let chemin = "";
      try { chemin = new URL(f.getAttribute("src") || "", location.href).pathname; } catch (e) { chemin = ""; }
      return r.width > 0 && r.height > 0 && LABS_CADRES.test(chemin) && f.contentWindow;
    }) || null;
  }
  function releveDuCadre(cadre) {
    const id = ++numero;
    return new Promise((ok) => {
      const fini = setTimeout(() => { window.removeEventListener("message", h); ok([]); }, 400);
      function h(ev) {
        if (ev.origin !== location.origin || ev.source !== cadre.contentWindow || !ev.data
          || ev.data.dzAgent !== "visibles" || ev.data.id !== id) return;
        clearTimeout(fini);
        window.removeEventListener("message", h);
        ok(Array.isArray(ev.data.items) ? ev.data.items : []);
      }
      window.addEventListener("message", h);
      try { cadre.contentWindow.postMessage({ dzAgent: "releve", id }, location.origin); }
      catch (e) { clearTimeout(fini); window.removeEventListener("message", h); ok([]); }
    });
  }
  async function releve() {
    const ici = releverVisibles(document, (x) => tiroir.contains(x) || bouton.contains(x));
    const cadre = cadreVisible();
    const lab = cadre ? await releveDuCadre(cadre) : [];
    return [...lab, ...ici].slice(0, MAX_VISIBLES);
  }
```

(`numero` est le compteur d'ids déjà utilisé par `demanderAuCadre` ; s'il porte un autre nom, réutiliser le sien.)
Puis ajouter `visibles: await releve()` dans les DEUX corps de requête : celui de `envoyer`
(`JSON.stringify({ question: q, historique: avant, ecran: vue(), lang: lang(), moteur: …, visibles: await releve() })`)
et l'objet `corps` de la question avec capture (`{ question: msg.question, …, lang: lang(), visibles: await releve() }`
— rendre la fonction englobante `async` si elle ne l'est pas).

Copies : `cp` des deux fichiers vers `frontend/dist/shared/`.

- [ ] **Étape 4 : lancer** — `tests/test_agent_ecran.py` (tout vert), node logique OK, `node --check` des deux
  fichiers, `cmp` des copies.
- [ ] **Étape 5 : commit** « agent : C4, le tiroir et les labs envoient le relevé de l'écran ».

### Tâche 12 : preuve, suite, suivi

- [ ] **Étape 1 : preuve à l'écran** — `preview_start` sur la configuration « preuve-agent » adaptée au worktree
  catalogue (ou `& $PY scripts/guide/serve_guide.py`, port 8809). Dans la console de la page :
  1. ouvrir le Montage, puis `await (async () => { const r = await fetch("/api/agent/demander", …) })()` n'est pas
     possible sans moteur : vérifier plutôt ce que le tiroir ENVOIE — intercepter `fetch` dans la console
     (`const f0 = window.fetch; window.fetch = (u, o) => { if (String(u).includes("/api/agent/")) console.log(o.body); return f0(u, o); }`),
     poser une question au tiroir, lire le corps : `visibles` contient « Rendre », « Preview »… (≤ 120) ;
  2. même chose dans le Vectorlab : `visibles` contient les entrées du lab (« Fichier », « Créer »…) ;
  3. côté serveur, `& $PY -c "…A.rapprocher(A._visibles(<corps relevé>), 'fr')"` reconnaît des fiches du vrai
     catalogue.
- [ ] **Étape 2 : suite** — `test_agent_catalogue`, `test_agent_recherche`, `test_agent_aide`, `test_agent_ecran`,
  `test_agent_connaissance`, `test_plafonds_garde`, `test_i18n_l0`, `test_i18n_l10`, `test_hygiene_lanceurs`, node ;
  puis la suite complète en arrière-plan, comparée à un worktree d'`origin/main` (≈ 45 rouges préexistantes).
- [ ] **Étape 3 : suivi** — t247 → `fait` (note : commits, preuve) ; demander à l'utilisateur avant push/PR.
- [ ] **Étape 4 : évaluer le skill (C5, t244)** — maintenant que l'extracteur existe : méthode skill-creator, deux ou
  trois cas réels (« j'ai ajouté un bouton Dupliquer au Montage, apprends-le à l'agent »), avec et sans skill.
