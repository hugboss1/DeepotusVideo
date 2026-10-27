# -*- coding: utf-8 -*-
"""A1 (spec 2026-10-19-agent-aide-design.md) — la connaissance de l'assistant est cohérente :
ancres.json bien formé ; écrans connus ; sections de Réglages connues ; texte d'ancre présent dans l'application
(bundle ou dictionnaire) ; AGENT.md ne cite que des ancres, vues et chapitres qui existent.
Run : & $PY tests/test_agent_connaissance.py   (depuis backend/)"""
import json, pathlib, re, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "backend"))
from app.services import agent_aide as A                                    # noqa: E402

ANCRES = json.loads((RACINE / "docs" / "agent" / "ancres.json").read_text(encoding="utf-8"))["ancres"]
CHAPITRES = {c["id"] for c in json.loads((RACINE / "docs" / "guide" / "src" / "chapitres.json")
                                         .read_text(encoding="utf-8"))["chapitres"]}
_BUNDLES = sorted((RACINE / "frontend" / "dist" / "assets").glob("index-*.js"))
assert len(_BUNDLES) == 1, f"un seul bundle index-*.js attendu dans frontend/dist/assets : {_BUNDLES}"
BUNDLE = _BUNDLES[0].read_text(encoding="utf-8")
DICO = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
LABS = {"/vectorlab/", "/photolab/", "/spritelab/", "/tilelab/"}


def test_forme():
    ids = [a["id"] for a in ANCRES]
    assert len(ids) == len(set(ids)), "identifiants en double"
    for a in ANCRES:
        assert re.fullmatch(r"[a-z0-9]+(\.[a-z0-9_]+)+", a["id"]), a["id"]
        assert a.get("fr") and a.get("en"), a["id"]
        assert a.get("selecteur") or a.get("reglages"), a["id"]


def test_ecrans_et_sections():
    for a in ANCRES:
        assert a.get("ecran") is None or a["ecran"] in A.VUES, a
        assert a.get("reglages") is None or a["reglages"] in A.SECTIONS_REGLAGES, a
        assert a.get("cadre") is None or a["cadre"] in LABS, a


def test_textes_presents_dans_l_application():
    for a in ANCRES:
        t = a.get("texte")
        if not t:
            continue
        for lang in ("fr", "en"):
            v = json.dumps(t[lang], ensure_ascii=False)[1:-1]
            if a.get("cadre"):
                lab = RACINE / "frontend" / a["cadre"].strip("/")
                src = "".join(p.read_text(encoding="utf-8", errors="replace")
                              for p in [lab / "index.html", *sorted((lab / "js").glob("*.js"))] if p.exists())
                assert t[lang] in src or v in src or v in DICO, (a["id"], lang)
            else:
                assert v in BUNDLE or v in DICO, (a["id"], lang)


def test_le_rail_complet():
    rail = {a["ecran"] for a in ANCRES if a["id"].startswith("rail.")}
    assert rail == set(A.VUES), set(A.VUES) - rail


def test_rail_partout_et_libelle():
    rail = [a for a in ANCRES if a["id"].startswith("rail.")]
    assert len(rail) == 15                      # t311 tâche 8 : WhatsApp
    for a in rail:
        assert a.get("partout") is True, a["id"]
    for a in ANCRES:
        if a.get("libelle"):
            assert a["libelle"].lstrip(".") in BUNDLE, a["id"]
    assert all(a.get("libelle") == ".dzNavLbl" for a in rail)


def test_agent_md_ne_cite_que_l_existant():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    ids = {a["id"] for a in ANCRES}
    for typ, cible in re.findall(r"\[(POINT|ALLER|GUIDE):([^\]]+)\]", t):
        if cible.startswith("<"):
            continue                                        # gabarit de la règle (« [POINT:<ancre>] »)
        assert {"POINT": cible in ids, "ALLER": cible in A.VUES, "GUIDE": cible in CHAPITRES}[typ], (typ, cible)


def test_sections_connues_du_bundle():
    """Les sections que l'écran sait ouvrir (dzReglagesEcoute) sont relues DANS le bundle,
    sans dépendre des noms minifiés."""
    listes = [json.loads(m.group(0)) for m in re.finditer(r'\[(?:"[a-z]+",?){10,20}\]', BUNDLE)
              if '"diag"' in m.group(0) and '"pricing"' in m.group(0)]
    assert listes, "liste des sections de Réglages introuvable dans le bundle"
    assert set(A.SECTIONS_REGLAGES) <= set(listes[0]), set(A.SECTIONS_REGLAGES) - set(listes[0])


def test_vues_presentes_dans_le_bundle():
    for v in A.VUES:
        assert f'id:"{v}"' in BUNDLE, v


def test_agent_md_structure():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    for s in ("## Qui tu aides", "## Les écrans", "## Parcours", "## Pièges fréquents", "## Comment répondre",
              "## Tenir ce fichier à jour"):
        assert s in t, s
    for v in A.VUES:
        # chaque écran a son élément de liste (une puce, éventuellement sur plusieurs lignes) dans la carte
        assert any(b.startswith("- ") and f"[ALLER:{v}]" in b for b in re.split(r"\n(?=- |\n|#)", t)), v
    for marqueur in ("5 étapes", "3 balises", "mot de passe"):
        assert marqueur in t, marqueur
    assert len(t) < 24_000, "AGENT.md doit tenir dans un message système raisonnable"


def test_aucune_balise_dans_une_phrase():
    """Le serveur retire chaque balise de la réponse : une balise au milieu d'une phrase laisse un trou. Sur chaque
    ligne, tout ce qui suit la PREMIÈRE balise ne doit donc être que des balises et des espaces."""
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    balise = re.compile(r"\[(POINT|ALLER|GUIDE):[^\]]+\]")
    vues = 0
    for ligne in t.splitlines():
        m = balise.search(ligne)
        if not m or "<" in ligne:                          # les gabarits de règle (<ancre>) sont exemptés
            continue
        vues += 1
        reste = ligne[m.start():]
        assert re.fullmatch(r"(\s*\[(POINT|ALLER|GUIDE):[^\]]+\])+\s*", reste), ligne
    assert vues > 20


def test_agent_md_explique_voir():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    regle = t.split("## Comment répondre", 1)[1].split("## Tenir ce fichier à jour", 1)[0]
    assert "`[VOIR]`" in regle and "aucune ancre" in regle
    assert "[POINT:x,y" not in t, "les coordonnées ne s'écrivent qu'après une capture : la consigne les demande"


def test_agent_md_regles_catalogue():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    assert "Éléments pertinents" in t and "non documenté" in t and "[pointable]" in t


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
