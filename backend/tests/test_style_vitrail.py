"""Option vitrail Młoda Polska — la copie épinglée et le moteur de prompts.

Le skill user-level `vitrail-mloda-polska` est la SOURCE ; le backend embarque
des copies datées et vérifiées par empreinte (patron walkuski, tests B de
test_cards_face.py) : `app/services/style_vitrail.py` (compositeur, stdlib
pur) et `app/services/style_vitrail.json` (grammaire machine). La déclaration
de provenance `VITRAIL_COPIE` vit dans le consommateur `manuscript_agent.py`.

Run: pytest tests/test_style_vitrail.py -q
"""
import hashlib
import json
import os
import pathlib
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SERVICES = pathlib.Path(__file__).resolve().parent.parent / "app" / "services"
REPO = pathlib.Path(__file__).resolve().parent.parent.parent


def _sha_norme(p: pathlib.Path) -> str:
    """Empreinte avec fins de ligne normalisées (dépôt LF, copies de travail
    parfois CRLF : l'empreinte doit dire le contenu, pas la machine)."""
    return hashlib.sha256(
        p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# ── A. les copies vivent en dépôt, datées, avec leur provenance ──────────────

def test_les_copies_vivent_en_depot_avec_leur_provenance():
    """La campagne tournera sur un backend déployé où ~/.claude/skills/
    n'existe pas : le compositeur et la fiche sont COPIÉS, et une copie DATE
    SA SOURCE avec son empreinte — une retouche silencieuse rougit ici."""
    moteur = SERVICES / "style_vitrail.py"
    fiche = SERVICES / "style_vitrail.json"
    assert moteur.is_file() and fiche.is_file()
    from app.services import manuscript_agent as MA
    decl = MA.VITRAIL_COPIE
    assert "vitrail-mloda-polska" in decl["origine"], decl
    assert decl["copie_le"] == "2026-08-27"
    assert decl["sha256"]["style_vitrail.py"] == _sha_norme(moteur)
    assert decl["sha256"]["style_vitrail.json"] == _sha_norme(fiche)
    f = json.loads(fiche.read_text("utf-8"))
    assert len(f["familles"]) == 8 and "vitrail" in f["familles"]
    # la provenance est honnête : bornes déclarées, PAS mesurées sur corpus
    assert "DECLARES" in f["provenance"].upper()


def test_la_copie_est_fraiche_face_au_skill():
    """Si le skill est là (poste de dev), les copies sont IDENTIQUES au
    skill ; sinon le contrôle se SAUTE en le disant."""
    src = pathlib.Path.home() / ".claude" / "skills" / "vitrail-mloda-polska"
    if not src.is_dir():
        pytest.skip("skill vitrail-mloda-polska absent de cette machine : "
                    "la fraîcheur ne peut pas se mesurer ici")
    paires = [(src / "scripts" / "vitrail_prompt.py",
               SERVICES / "style_vitrail.py"),
              (src / "fiche_style.json", SERVICES / "style_vitrail.json")]
    for amont, aval in paires:
        assert amont.is_file(), amont.name
        assert _sha_norme(amont) == _sha_norme(aval), (
            f"{aval.name} a divergé de {amont.name} : recopiez-le et "
            f"remettez la date + l'empreinte dans MA.VITRAIL_COPIE")


# ── B. le moteur exécute la formule du guide ─────────────────────────────────

def test_le_moteur_compose_selon_la_formule():
    from app.services import style_vitrail as SV
    r = SV.construire_prompt("une gardienne de phare dans une ville lacustre",
                             famille="vitrail", intensite=4)
    p = r["prompt"]
    # palette ancrée en hex (échec baseline n°2 : « jewel-toned » sans dose)
    assert "#0047AB" in p and "#9B111E" in p
    # garde-fous DANS le prompt principal (échec baseline n°3)
    assert "entirely original artwork" in p
    assert "no text" in p and "no signature" in p
    # les codes de la famille et la lumière transmise
    assert "leadlines" in p and "light transmitted from within" in p
    # la variante diffère (autre dosage d'ornement / autre heure)
    assert r["variante"] != p
    assert r["negatif"] and "no text" in r["negatif"]
    assert r["codes_mobilises"] and r["note"]


def test_aucun_nom_d_artiste_ne_sort_jamais():
    """Échec baseline n°1 : « in the style of Stanisław Wyspiański ». Le nom
    ne sort d'AUCUN compositeur, et la garde lève sur un prompt empoisonné."""
    from app.services import style_vitrail as SV
    fiche = SV.charger_fiche()
    for fid in fiche["familles"]:
        r = SV.construire_prompt("un sujet neutre", famille=fid, intensite=3)
        tout = (r["prompt"] + r["variante"] + r["negatif"]).lower()
        for nom in ("wyspia", "mehoffer", "malczewski", "boznańska",
                    "boznanska", "ruszczyc", "matejko", "axentowicz"):
            assert nom not in tout, (fid, nom)
    with pytest.raises(ValueError):
        SV.garde_noms("a window after Wyspianski")
    with pytest.raises(ValueError):
        SV.appliquer("in the style of Mehoffer, a garden")
    # l'épuration retire les noms d'un texte utilisateur sans le vider
    net = SV.epurer_noms("after Wyspianski, a tall tower by Mehoffer")
    assert "wyspia" not in net.lower() and "mehoffer" not in net.lower()
    assert "tall tower" in net
    assert SV.appliquer(SV.epurer_noms("by Wyspianski: a tower"))


def test_appliquer_stylise_un_prompt_libre():
    """La voie de l'option d'app : le prompt de l'appelant garde son sujet et
    gagne le bloc de la famille + les garde-fous."""
    from app.services import style_vitrail as SV
    out = SV.appliquer("a lighthouse keeper over a lake city")
    assert out.startswith("a lighthouse keeper over a lake city")
    assert "#046307" in out and "no text" in out
    with pytest.raises(ValueError):
        SV.appliquer("   ")
    with pytest.raises(KeyError):
        SV.appliquer("x", famille="gothico")


def test_les_huit_familles_sont_completes():
    from app.services import style_vitrail as SV
    fiche = SV.charger_fiche()
    assert set(fiche["familles"]) == {
        "vitrail", "symbolisme", "portrait", "folklore", "paysage",
        "impressionnisme", "synthetisme", "decoratif"}
    for fid, fam in fiche["familles"].items():
        assert fam["label"] and fam["label_en"], fid
        assert len(fam["codes"]) >= 5, fid
        ancres = fam["palette"]["ancres"]
        assert ancres, fid
        for nom, hexa in ancres.items():
            assert len(hexa) == 7 and hexa[0] == "#", (fid, nom, hexa)
        # le bloc prêt-générateur porte au moins une ancre hex de sa palette
        assert any(h in fam["bloc_en"] for h in ancres.values()), fid
        assert fam["negatif_en"].startswith("no "), fid
        assert fam["referents_pedagogiques"], fid


# ── C. le preset DA et le miroir atelier ne dérivent pas de la fiche ─────────

def test_le_preset_et_le_canon_collent_a_la_fiche():
    from app.services import manuscript_agent as MA
    from app.services import style_vitrail as SV
    preset = next(p for p in MA.STYLE_PRESETS if p["id"] == "vitrail")
    assert preset["label"] == "Vitrail Młoda Polska"
    assert preset["canon"] == "vitrail"
    # verrou anti-dérive : le preset EST le bloc de la fiche épinglée
    assert preset["style_prompt"] == SV.bloc_style("vitrail")
    canon = MA.PROPORTION_CANONS["vitrail"]
    # l'espace du vitrail est aplati : pas de perspective linéaire profonde
    assert "flat" in canon["decor"].lower(), canon["decor"]
    assert "vitrail" in canon["kw"] and "stained glass" in canon["kw"]
    assert MA.resolve_canon("stained glass vitrail art nouveau") == "vitrail"
    # le choix explicite du réglage DA prime toujours
    assert MA.resolve_canon("anything", explicit="vitrail") == "vitrail"


def test_le_miroir_atelier_porte_le_preset_et_le_canon():
    from app.services import style_vitrail as SV
    js = (REPO / "frontend" / "atelier" / "atelier.js").read_text("utf-8")
    assert "Vitrail Młoda Polska" in js
    # le chip du miroir embarque exactement le bloc épinglé (zéro dérive)
    assert SV.bloc_style("vitrail") in js
    assert 'id: "vitrail"' in js
