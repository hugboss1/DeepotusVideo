# -*- coding: utf-8 -*-
"""Plateau hexagonal, lot 1 (tâche 5) à l'écran : le dialogue partagé « Découper en hexagones »
(frontend/shared/dz-decoupe-hex.js, .css, i18n/decoupehex.json).

  1. les textes : chaque clé decoupehex.* utilisée est écrite en FR et en EN, mêmes variables, aucune orpheline ;
     le dictionnaire assemblé est à jour et visible des deux labs (Photolab, Vectorlab chargent dz-i18n-dico.js) ;
  2. aucune chaîne en dur dans le module, aucun innerHTML ;
  3. le réseau : la seule route est POST /api/cards/decks/plateau ; le Card Forge s'ouvre par /cardforge/?deck= et
     son core lit bien ce paramètre ;
  4. la charte : aucun rayon, aucune couleur littérale, sélecteurs sous .dz-dh ;
  5. les copies dist/shared sont identiques à la source ;
  6. le banc node (shared/qa/decoupe_hex_dialogue.test.mjs), vert.

Run (depuis backend/) : & $PY tests/test_decoupe_hex_ecran.py
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
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
JS = (SHARED / "dz-decoupe-hex.js").read_bytes().decode("utf-8")
CSS = (SHARED / "dz-decoupe-hex.css").read_bytes().decode("utf-8")
LOGIQUE = (SHARED / "dz-decoupe-hex-logique.js").read_bytes().decode("utf-8")
DICO = json.loads((SHARED / "i18n" / "decoupehex.json").read_bytes().decode("utf-8"))
NODE = shutil.which("node")


def _sans_commentaires(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"(?m)(^|\s)//.*$", "", s)


CODE = _sans_commentaires(JS)
FORMATS = re.findall(r"^\s+(hex_[pf]\d+):", LOGIQUE, flags=re.M)


def _cles_utilisees() -> set:
    cles = {c for c in re.findall(r'"(decoupehex\.[a-z0-9_.]+)"', CODE) if not c.endswith(".")}
    if '"decoupehex.format." + id' in CODE:               # une clé par format, composée à la volée
        cles |= {"decoupehex.format." + f for f in FORMATS}
    return cles


# ── 1. les textes ──────────────────────────────────────────────────────────────────────────────────────────────────
def test_les_huit_formats_sont_lus_dans_la_logique():
    assert len(FORMATS) == 8, FORMATS


def test_chaque_cle_est_en_francais_et_en_anglais_memes_variables():
    cles = _cles_utilisees()
    assert len(cles) >= 25, len(cles)
    absentes = sorted(c for c in cles if c not in DICO)
    assert not absentes, absentes
    for c in cles:
        v = DICO[c]
        assert v.get("fr", "").strip() and v.get("en", "").strip(), c
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), c


def test_aucune_cle_orpheline():
    orphelines = sorted(k for k in DICO if k not in _cles_utilisees())
    assert not orphelines, orphelines
    assert all(k.startswith("decoupehex.") for k in DICO)


def test_les_phrases_a_variables_sont_appelees_avec_leurs_variables():
    # les clés de refus de la grille sont passées par `verifier` avec leurs variables
    for cle, variables in {"decoupehex.grille.borne": {"max"}, "decoupehex.grille.tuiles_max": {"n", "max"},
                           "decoupehex.grille.pixels_max": {"mpx", "max"}, "decoupehex.cadrage.ppp": {"ppp"},
                           "decoupehex.cadrage.ppp_faible": {"min"}, "decoupehex.erreur.http": {"code"},
                           "decoupehex.grille.tuiles": {"n"}, "decoupehex.jeu.nom_defaut": {"nom"}}.items():
        assert set(re.findall(r"\{(\w+)\}", DICO[cle]["fr"])) == variables, cle


def test_dictionnaire_assemble_a_jour():
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    assert p.returncode == 0, (p.stdout + p.stderr)[-400:]
    assemble = (SHARED / "dz-i18n-dico.js").read_bytes().decode("utf-8")
    for cle in DICO:
        assert json.dumps(cle, ensure_ascii=False) + ": " in assemble, cle


def test_les_deux_labs_chargent_le_dictionnaire_assemble():
    # Task 6 (Photolab) et 7 (Vectorlab) : leur T est dzT, qui lit window.DZ_I18N (dz-i18n-dico.js)
    for lab in ("photolab", "vectorlab"):
        html = (RACINE / "frontend" / lab / "index.html").read_bytes().decode("utf-8")
        assert html.count('src="/shared/dz-i18n-dico.js"') == 1, lab
        assert html.index("dz-i18n-dico.js") < html.index("dz-i18n.js"), lab


# ── 2. aucune chaîne en dur ────────────────────────────────────────────────────────────────────────────────────────
def test_aucune_chaine_en_dur_dans_le_module():
    code = re.sub(r"console\.\w+\([^;]*\);", "", CODE)
    lits = re.findall(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`', code)
    lits = [a or b or c for a, b, c in lits]
    valeurs = {"Escape", "Tab", "Content-Type", "application/json", "POST"}        # comparées ou protocolaires, jamais affichées
    durs = [t for t in lits if not t.startswith(("decoupehex.", "commun.")) and t not in valeurs
            and (re.search(r"[À-ÖØ-öø-ÿ«»’…—]", t) or re.search(r"\b[A-Z][a-z]{2,}", t)
                 or re.search(r"[a-z]{3,} [a-z]{3,} [a-z]{3,}", t))]
    assert not durs, durs
    assert "innerHTML" not in code
    # seul le « × » de la croix est un signe, pas un mot : il est posé en dur (une glyphe), tout le reste passe par T
    assert code.count('croix.textContent = "×"') == 1
    assert not re.search(r"\.(textContent|title|placeholder|label)\s*=\s*[\"'`][^\"'`]", code.replace('croix.textContent = "×"', ""))
    assert not re.search(r'setAttribute\("(aria-label|placeholder|title)",\s*["\'`]', code)


# ── 3. le réseau et le Card Forge ──────────────────────────────────────────────────────────────────────────────────
def test_une_seule_route_et_le_fetch_est_injecte():
    assert re.findall(r'"/api/[^"]*"', CODE) == ['"/api/cards/decks/plateau"']
    assert "XMLHttpRequest" not in CODE
    assert CODE.count("window.fetch") == 1                          # le seul : la valeur par défaut du paramètre
    assert 'import { FORMATS_HEX, COTE_MAX, TUILES_MAX, PIXELS_MAX, grille, cadrageCouvrant, pppEffectif } from "./dz-decoupe-hex-logique.js";' in CODE


def test_le_card_forge_s_ouvre_par_son_chemin_reel():
    assert 'window.open(adresse)' in CODE and '"/cardforge/?deck=" + encodeURIComponent(j.deck.id)' in CODE
    main = (RACINE / "backend" / "app" / "main.py").read_bytes().decode("utf-8")
    assert 'app.mount("/cardforge"' in main
    html = RACINE / "frontend" / "cardforge" / "index.html"
    assert html.is_file()
    core = (RACINE / "frontend" / "cardforge" / "js" / "core.js").read_bytes().decode("utf-8")
    assert 'searchParams.get("deck")' in core or "get('deck')" in core or 'u.searchParams.set("deck", did)' in core


# ── 4. la charte ───────────────────────────────────────────────────────────────────────────────────────────────────
def test_angles_vifs_selecteurs_et_jetons():
    corps = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    assert "radius" not in corps, "angles vifs : aucun rayon"
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", corps), "couleur littérale : passer par les jetons"
    corps_sans_media = re.sub(r"@media[^{]*\{", "", corps)
    selecteurs = [s.strip() for bloc in re.findall(r"([^{}]+)\{", corps_sans_media) for s in bloc.split(",")]
    assert selecteurs and all(s.startswith(".dz-dh") for s in selecteurs), [s for s in selecteurs if not s.startswith(".dz-dh")]
    # toutes les classes posées par le module ont leur règle (ou sont des pures marques)
    posees = {c for m in re.findall(r'(?:el\("\w+", |className = )"([^"]+)"', CODE) for c in m.split()}
    assert len(posees) >= 15, posees
    for c in sorted(posees):
        assert "." + c in corps, c


def test_le_curseur_de_zoom_garde_le_style_fader_de_l_app():
    """M-2 : le curseur n'est pas une case (fond, bordure, hauteur de .dz-dh-in) ni une seconde peau (accent-color) :
    il reste sous la règle commune input[type=range] de dz-curseur.css (t373)."""
    corps = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    assert "accent-color" not in corps
    m = re.search(r'inZoom = marque\(el\("input"(?:, "([^"]*)")?\), "zoom"\)', CODE)
    assert m, "le curseur de zoom doit être créé par marque(el(\"input\"), \"zoom\")"
    assert "dz-dh-in" not in (m.group(1) or "")
    assert 'inZoom.type = "range"' in CODE
    for sel, decl in re.findall(r"([^{}]+)\{([^}]*)\}", corps):
        if "range" in sel:           # une règle qui vise le curseur ne peint ni fond, ni bordure, ni hauteur
            assert not re.search(r"background|border|height|appearance|padding", decl), (sel, decl)


def test_la_feuille_est_posee_par_le_module():
    assert 'new URL("./dz-decoupe-hex.css", import.meta.url).href' in CODE
    assert 'document.getElementById("dz-dh-css")' in CODE


# ── 5. les copies ──────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("nom", ["dz-decoupe-hex.js", "dz-decoupe-hex.css", "dz-decoupe-hex-logique.js", "dz-i18n-dico.js"])
def test_copie_dist_identique(nom):
    src, copie = SHARED / nom, DIST / nom
    assert copie.is_file(), nom
    assert copie.read_bytes() == src.read_bytes(), nom


# ── 6. le banc node ────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.skipif(not NODE, reason="node introuvable")
def test_le_banc_node_joue_le_dialogue():
    r = subprocess.run([NODE, str(SHARED / "qa" / "decoupe_hex_dialogue.test.mjs")], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(RACINE), timeout=120)
    assert r.returncode == 0 and r.stdout.strip().endswith("OK"), (r.stdout + r.stderr)[-800:]
    m = re.search(r"(\d+)/(\d+) vérifications", r.stdout)
    assert m and m.group(1) == m.group(2) and int(m.group(2)) >= 60, r.stdout[-300:]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
