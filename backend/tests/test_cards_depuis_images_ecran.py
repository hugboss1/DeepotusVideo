# -*- coding: utf-8 -*-
"""Card Forge — t421 (cartes hexagonales, 07/11/2026, tâche 5) à l'écran : le dialogue « Nouveau jeu depuis des
images ».

  1. l'entrée de la galerie : section et bouton #galImages dans le squelette de core.js, câblés à galImages, qui ouvre
     window.CFDepuisImages ; témoin : le core d'avant la tâche (1b7d9772) n'a pas l'entrée ;
  2. l'API publique du CORE : CF.bibliotheque (images, projets, projet, importer, url) et CF.deckDepuisImages, qui
     crée par POST /api/cards/decks/depuis-images puis ouvre par ?deck= (galGo) — aucun fetch dans le dialogue ;
  3. la coquille : la feuille et les deux scripts chargés après core.js et les dix pièces, la logique avant le dialogue ;
  4. les textes : chaque clé cartes.depuis.* écrite en FR et en EN, mêmes variables, aucune orpheline, dictionnaire
     assemblé à jour, saisie L7 rejouée (i18n_l7_generer --check) ; aucune chaîne en dur dans depuis-images.js ;
  5. la charte : angles vifs (aucun rayon littéral), sélecteurs sous .cf-di ;
  6. le banc node (qa/depuis_images.test.mjs) : logique ET dialogue joués, vert.

Ce banc lit la source TRADUITE (sans `_cartes_avant_l7`).
Run (depuis backend/) : & $PY tests/test_cards_depuis_images_ecran.py
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RACINE / "backend"))
CF_DIR = RACINE / "frontend" / "cardforge"
CORE = (CF_DIR / "js" / "core.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
DIAL = (CF_DIR / "js" / "depuis-images.js").read_bytes().decode("utf-8")
LOGI = (CF_DIR / "js" / "depuis-images-logique.js").read_bytes().decode("utf-8")
CSS = (CF_DIR / "css" / "depuis-images.css").read_bytes().decode("utf-8")
HTML = (CF_DIR / "index.html").read_bytes().decode("utf-8")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "cartes.json").read_bytes().decode("utf-8"))
TEMOIN = "1b7d9772"          # la tâche 4 : la route, sans l'écran
NODE = shutil.which("node")


def _sans_commentaires(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", s)


def _fonction(src: str, nom: str) -> str:
    k = src.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof = src.find("{", k), 0
    for j in range(i, len(src)):
        prof += {"{": 1, "}": -1}.get(src[j], 0)
        if prof == 0:
            return src[k:j + 1]
    return ""


# ── 1. l'entrée de la galerie ──────────────────────────────────────────────────────────────────────────────────────
def test_temoin_le_core_d_avant_n_a_pas_l_entree():
    r = subprocess.run(["git", "show", f"{TEMOIN}:frontend/cardforge/js/core.js"], cwd=str(RACINE), capture_output=True)
    assert r.returncode == 0 and b"function galOpenDeck(" in r.stdout
    assert b"galImages" not in r.stdout and b"deckDepuisImages" not in r.stdout


def test_l_entree_est_dans_la_galerie_et_cablee():
    sq = CORE[CORE.find("const GAL_SKELETON"):CORE.find("function galEnsure(")]
    assert 'id="galImages"' in sq and 'dzT("cartes.depuis.gal_titre")' in sq and 'dzT("cartes.depuis.gal_bouton")' in sq
    # la section ouvre le corps de la galerie, avant « Nouveau jeu depuis un modèle »
    assert sq.find('class="cf-gal-body"') < sq.find('id="galImages"') < sq.find("cartes.core.gal_nouveau")
    ens = _fonction(CORE, "galEnsure")
    assert 'const gi = el("#galImages"); if (gi) gi.addEventListener("click", galImages);' in ens
    gi = _fonction(CORE, "galImages")
    assert "window.CFDepuisImages" in gi and "closeGallery();" in gi and "D.ouvrir();" in gi
    assert 'toast(dzT("cartes.depuis.absent"), true)' in gi


# ── 2. l'API publique du CORE ──────────────────────────────────────────────────────────────────────────────────────
def test_le_core_tient_la_bibliotheque_et_la_creation():
    cf = CORE[CORE.find("const CF = {"):CORE.find("Object.freeze(CF);")]
    assert "bibliotheque: bibliotheque, deckDepuisImages: deckDepuisImages, libelleFormat: libelleFormat," in cf
    bib = CORE[CORE.find("const bibliotheque = Object.freeze({"):CORE.find("async function deckDepuisImages(")]
    for m in ("async images()", "async projets()", "async projet(id)", "async importer(file)", "url(nom)"):
        assert m in bib, m
    assert 'jsonNamed("GET", "/images")' in bib and 'jsonNamed("GET", "/library/projets")' in bib
    assert 'jsonNamed("POST", "/images/upload", fd)' in bib and 'fd.append("file", file' in bib
    assert '"/api/images/" + encodeURIComponent(' in bib
    dk = _fonction(CORE, "deckDepuisImages")
    assert 'jsonNamed("POST", "/cards/decks/depuis-images"' in dk
    assert dk.index("await galFlush();") < dk.index("jsonNamed(") < dk.index("galGo(did);")


def test_le_dialogue_ne_formule_aucune_requete():
    code = _sans_commentaires(DIAL) + _sans_commentaires(LOGI)
    assert "fetch(" not in code and "XMLHttpRequest" not in code and "/api/" not in code
    for appel in ("CF.bibliotheque.images()", "CF.bibliotheque.projets()", "CF.bibliotheque.projet(id)",
                  "CF.bibliotheque.importer(", "CF.bibliotheque.url(", "await CF.deckDepuisImages(P.corps)"):
        assert appel in DIAL, appel


# ── 3. la coquille ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_la_coquille_charge_la_feuille_et_les_scripts_dans_l_ordre():
    assert HTML.count('href="css/depuis-images.css"') == 1
    assert HTML.index('href="cardforge.css"') < HTML.index('href="css/depuis-images.css"')
    i_core, i_ed = HTML.index('src="js/core.js"'), HTML.index('src="js/mod-edition.js"')
    i_l, i_d = HTML.index('src="js/depuis-images-logique.js"'), HTML.index('src="js/depuis-images.js"')
    assert i_core < i_ed < i_l < i_d


# ── 4. les textes ──────────────────────────────────────────────────────────────────────────────────────────────────
def _cles(src):
    return set(re.findall(r'\bdzT\("(cartes\.depuis\.[a-z0-9_]+)"', src))


def test_chaque_cle_est_en_francais_et_en_anglais():
    cles = _cles(DIAL) | _cles(CORE)
    assert len(cles) >= 50, len(cles)
    absentes = sorted(c for c in cles if c not in DICO)
    assert not absentes, absentes
    for c in cles:
        v = DICO[c]
        assert v.get("fr") and v.get("en"), c
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), c
    orphelines = sorted(k for k in DICO if k.startswith("cartes.depuis.") and k not in cles)
    assert not orphelines, orphelines
    # le dialogue réutilise « Fermer (Échap) » du CORE
    assert 'dzT("cartes.core.fermer_echap")' in DIAL and "cartes.core.fermer_echap" in DICO


def test_dictionnaire_assemble_et_saisie_l7_a_jour():
    for script in ("i18n_l7_generer.py", "i18n_assembler.py"):
        p = subprocess.run([sys.executable, str(RACINE / "scripts" / script), "--check"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                           env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        assert p.returncode == 0, (script, (p.stdout + p.stderr)[-400:])
    saisie = (RACINE / "scripts" / "i18n_l7" / "t421_depuis.py").read_text("utf-8")
    assert "cartes.depuis." in saisie and 'H("cartes.depuis." + k, fr, en)' in saisie


def test_aucune_chaine_en_dur_dans_le_dialogue():
    code = _sans_commentaires(DIAL)
    code = re.sub(r"console\.\w+\([^;]*\);", "", code)              # messages de console : gardés (consigne L7)
    lits = re.findall(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`', code)
    lits = [a or b or c for a, b, c in lits]
    compares = {"Escape"}                                            # valeur comparée (ev.key), pas affichée
    durs = [t for t in lits if not t.startswith("cartes.") and t not in compares
            and (re.search(r"[À-ÖØ-öø-ÿ«»’…]", t) or re.search(r"\b[A-Z][a-z]{2,}", t)
                 or re.search(r"[a-z]{3,} [a-z]{3,} [a-z]{3,}", t))]
    assert not durs, durs
    assert "innerHTML" not in code
    # aucun texte posé en dur dans un attribut affiché
    assert not re.search(r"\.(textContent|title|placeholder|label)\s*=\s*[\"'`]", code)
    assert not re.search(r'setAttribute\("aria-label",\s*["\'`]', code)


# ── 5. la charte ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_angles_vifs_et_selecteurs_du_dialogue():
    rayons = re.findall(r"border-radius:\s*([^;]+);", CSS)
    assert rayons and all(r.strip() == "var(--r)" for r in rayons), rayons
    corps = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    selecteurs = [s.strip() for bloc in re.findall(r"([^{}]+)\{", corps) for s in bloc.split(",")]
    assert selecteurs and all(s.startswith(".cf-di") for s in selecteurs), [s for s in selecteurs if not s.startswith(".cf-di")]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", corps), "couleur littérale : passer par les jetons"


# ── 6. le banc node ────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.skipif(not NODE, reason="node introuvable")
def test_le_banc_node_joue_la_logique_et_le_dialogue():
    r = subprocess.run([NODE, str(CF_DIR / "qa" / "depuis_images.test.mjs")], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(RACINE))
    assert r.returncode == 0 and r.stdout.strip().endswith("OK"), (r.stdout + r.stderr)[-800:]
    m = re.search(r"(\d+)/(\d+) vérifications", r.stdout)
    assert m and m.group(1) == m.group(2) and int(m.group(2)) >= 50, r.stdout[-300:]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
