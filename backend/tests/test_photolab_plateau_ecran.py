# -*- coding: utf-8 -*-
"""Plateau hexagonal, lot 1 (tâche 6) : Photolab › Image › Découper en hexagones…

  1. les chaînes : photolab.menu.decouper_hex (FR/EN) et photolab.plateau.erreur_enregistrement, dictionnaire assemblé à jour ;
  2. le câblage : core.js initialise le module, mod-fichier expose enregistrer(), le menu et ses ensembles déclarent l'id,
     le module importe le dialogue PARTAGÉ par un chemin relatif servi aussi sous /shared/ ;
  3. aucune chaîne en dur dans mod-plateau.js ;
  4. le banc node (photolab/qa/plateau.test.mjs) et les bancs de menus voisins, verts.

Run (depuis backend/) : & $PY tests/test_photolab_plateau_ecran.py
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
PL = RACINE / "frontend" / "photolab"
NODE = shutil.which("node")


def _lire(p: pathlib.Path) -> str:
    return p.read_bytes().decode("utf-8")


MODULE = _lire(PL / "js" / "mod-plateau.js")
DICO = json.loads(_lire(RACINE / "frontend" / "shared" / "i18n" / "photolab.json"))


def test_les_cles_sont_en_francais_et_en_anglais():
    assert DICO["photolab.menu.decouper_hex"] == {"fr": "Découper en hexagones…", "en": "Cut into hexagons…"}
    e = DICO["photolab.plateau.erreur_enregistrement"]
    assert e["fr"].strip() and e["en"].strip() and e["fr"] != e["en"]


def test_le_dictionnaire_assemble_est_a_jour_et_copie_dans_dist():
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    assert p.returncode == 0, (p.stdout + p.stderr)[-400:]
    for dossier in (RACINE / "frontend" / "shared", RACINE / "frontend" / "dist" / "shared"):
        assemble = _lire(dossier / "dz-i18n-dico.js")
        for cle in ("photolab.menu.decouper_hex", "photolab.plateau.erreur_enregistrement"):
            assert json.dumps(cle) + ": " in assemble, (dossier, cle)


def test_cablage_du_module():
    core = _lire(PL / "js" / "core.js")
    assert 'import { initPlateau } from "./mod-plateau.js";' in core and "initPlateau(PL);" in core
    assert core.index("initFichier(PL);") < core.index("initPlateau(PL);")
    assert "PL.enregistrerBibliotheque = enregistrer;" in _lire(PL / "js" / "mod-fichier.js")
    menus = _lire(PL / "js" / "mod-menus.js")
    assert menus.count('"pl.plateau.decouper"') >= 3          # insertion + TRAITES_PAR_ECRAN + NECESSITE_DOC
    assert "...INSERTIONS_PLATEAU]" in menus
    # le dialogue partagé, par un chemin relatif (le Photolab est servi sous /photolab/js/, /shared/ est un frère)
    assert 'from "../../shared/dz-decoupe-hex.js"' in MODULE
    assert (PL / "js" / ".." / ".." / "shared" / "dz-decoupe-hex.js").resolve().is_file()
    # une seule route : celle du moteur (rendu) ; la création passe par le dialogue
    assert re.findall(r'PL\.post\("([^"]+)"', MODULE) == ["/rendu"]


def test_aucune_chaine_en_dur():
    code = re.sub(r"/\*.*?\*/", "", MODULE, flags=re.S)
    code = re.sub(r"(?m)(^|\s)//.*$", "", code)
    lits = [a or b for a, b in re.findall(r'"((?:[^"\\n]|\.)*)"|\'((?:[^\'\\n]|\.)*)\'', code)]
    durs = [t for t in lits if t.startswith("photolab.") is False and (re.search(r"[À-ÖØ-öø-ÿ«»’…—]", t) or re.search(r"[a-z]{3,} [a-z]{3,}", t))]
    assert not durs, durs
    assert "innerHTML" not in code


@pytest.mark.skipif(NODE is None, reason="node absent")
@pytest.mark.parametrize("banc", ["plateau", "menus", "defauts-menus", "exports-m8", "envoi", "natif", "cadres-n7"])
def test_bancs_node(banc):
    p = subprocess.run([NODE, str(PL / "qa" / f"{banc}.test.mjs")], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(RACINE))
    assert p.returncode == 0, (p.stdout + p.stderr)[-800:]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
