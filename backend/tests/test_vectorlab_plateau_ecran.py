# -*- coding: utf-8 -*-
"""Plateau hexagonal, lot 1 (tâche 7) : Vectorlab › Exporter › Découper en hexagones…

  1. les chaînes : vectorlab.export.plateau / plateau_titre (FR/EN), dictionnaire assemblé à jour ;
  2. le câblage : bouton #expPlateau dans le menu Export, clic gardé, exporterPNG lit l'option `opaque` (jamais la case
     transparente pour ce bouton), le module importe le dialogue PARTAGÉ par un chemin relatif servi aussi sous /shared/ ;
  3. aucune chaîne en dur dans mod-decoupehex.js ;
  4. le banc node (vectorlab/qa/decoupehex.test.mjs) et les bancs d'export voisins, verts.

Run (depuis backend/) : & $PY tests/test_vectorlab_plateau_ecran.py
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
VL = RACINE / "frontend" / "vectorlab"
NODE = shutil.which("node")


def _lire(p: pathlib.Path) -> str:
    return p.read_bytes().decode("utf-8")


MODULE = _lire(VL / "js" / "mod-decoupehex.js")
EXPORT = _lire(VL / "js" / "mod-export.js")
DICO = json.loads(_lire(RACINE / "frontend" / "shared" / "i18n" / "vectorlab.json"))
CLES = ("vectorlab.export.plateau", "vectorlab.export.plateau_titre")


def test_les_cles_sont_en_francais_et_en_anglais():
    assert DICO[CLES[0]] == {"fr": "Découper en hexagones…", "en": "Cut into hexagons…"}
    t = DICO[CLES[1]]
    assert t["fr"].strip() and t["en"].strip() and t["fr"] != t["en"]


def test_le_dictionnaire_assemble_est_a_jour_et_copie_dans_dist():
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    assert p.returncode == 0, (p.stdout + p.stderr)[-400:]
    for dossier in (RACINE / "frontend" / "shared", RACINE / "frontend" / "dist" / "shared"):
        assemble = _lire(dossier / "dz-i18n-dico.js")
        for cle in CLES:
            assert json.dumps(cle) + ": " in assemble, (dossier, cle)


def test_cablage():
    html = _lire(VL / "index.html")
    assert "expPlateau" not in html          # convention L6 : index.html n'est pas modifié, le bouton est créé en JS
    assert 'btnPlateau.id = "expPlateau";' in EXPORT and '$("#expPng4").after(btnPlateau);' in EXPORT
    assert 'btnPlateau.addEventListener("click", garde(() => decouperHex(VL, T)));' in EXPORT
    assert 'T("vectorlab.export.plateau")' in EXPORT and 'T("vectorlab.export.plateau_titre")' in EXPORT
    assert 'transparentExport(opts, $("#expTransparent").checked)' in EXPORT
    assert "k: Math.round(k * 100) / 100" in EXPORT          # le toast affiche le k arrondi
    # les boutons existants n'ont pas changé de comportement
    for k in ("1", "2", "4"):
        assert f'garde(() => exporterPNG({k}))' in EXPORT
    # le dialogue partagé, par un chemin relatif (le Vectorlab est servi sous /vectorlab/js/, /shared/ est un frère)
    assert 'from "../../shared/dz-decoupe-hex.js"' in MODULE
    assert (VL / "js" / ".." / ".." / "shared" / "dz-decoupe-hex.js").resolve().is_file()
    # la lignée remonte au document par le nom vector_<docId>_…, sans route nouvelle
    assert 'suffixe: "_plateau"' in MODULE and "opaque: true" in MODULE
    assert not re.search(r"fetch\(|/api/", MODULE)


def test_aucune_chaine_en_dur():
    code = re.sub(r"/\*.*?\*/", "", MODULE, flags=re.S)
    code = re.sub(r"(?m)(^|\s)//.*$", "", code)
    lits = [a or b for a, b in re.findall(r'"((?:[^"\\n]|\.)*)"|\'((?:[^\'\\n]|\.)*)\'', code)]
    durs = [t for t in lits if re.search(r"[À-ÖØ-öø-ÿ«»’…—]", t) or re.search(r"[a-z]{3,} [a-z]{3,}", t)]
    assert not durs, durs
    assert "innerHTML" not in code


@pytest.mark.skipif(NODE is None, reason="node absent")
@pytest.mark.parametrize("banc", ["decoupehex", "exportplus_ui", "noms_bruts", "dxf"])
def test_bancs_node(banc):
    p = subprocess.run([NODE, str(VL / "qa" / f"{banc}.test.mjs")], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(RACINE))
    assert p.returncode == 0, (p.stdout + p.stderr)[-600:]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
