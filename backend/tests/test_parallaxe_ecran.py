"""t341 (lot Scenario, B5) — l'écran « Décor en parallaxe » du Tile Lab (frontend/tilelab/parallaxe.js), sans navigateur.

  - la page charge le module APRÈS tilelab.js (il s'appuie sur window.__tl et l'évènement « tl-mode ») ;
  - tilelab.js n'est pas touché (il est généré par la traduction L9) ;
  - chaque clé dzT du module est au dictionnaire parallaxe.json, fr et en, mêmes variables ; les clés composées
    (voie.<modèle>, calque.<id>) couvrent le registre du serveur ; aucune clé du dictionnaire sans usage ;
  - aucun texte français en dur dans les chaînes du module (hors commentaires) ;
  - la voie IA : le devis s'affiche AVANT, `confirme_cout` ne part qu'APRÈS __dzDialogue.confirmer ;
  - node --check du module.
Run: & $PY tests/test_parallaxe_ecran.py   (depuis backend/)
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI.parent))
MOD = (RACINE / "frontend" / "tilelab" / "parallaxe.js").read_bytes().decode("utf-8")
PAGE = (RACINE / "frontend" / "tilelab" / "index.html").read_bytes().decode("utf-8")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "parallaxe.json").read_text("utf-8"))


def _sans_commentaires(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return "\n".join(re.sub(r"(^|[^:\"'])//.*$", r"\1", ligne) for ligne in s.splitlines())


def test_la_page_charge_le_module_apres_tilelab():
    i_tl, i_px = PAGE.find('<script src="tilelab.js">'), PAGE.find('<script type="module" src="parallaxe.js">')
    assert 0 <= i_tl < i_px, (i_tl, i_px)
    assert "parallaxe" not in (RACINE / "frontend" / "tilelab" / "tilelab.js").read_bytes().decode("utf-8")


def test_cles_du_module_au_dictionnaire_et_sans_orpheline():
    from app.services import parallaxe as PX
    fixes = set(re.findall(r'"(parallaxe\.[a-z0-9_]+\.[a-z0-9_]+)"', MOD))
    composees = {f"parallaxe.voie.{m.replace('-', '_')}" for m in PX.MODELES}
    composees |= {f"parallaxe.voie.{m.replace('-', '_')}_aide" for m in PX.MODELES}
    composees |= {f"parallaxe.calque.{c}" for c in PX.NOMS_5}
    utilisees = fixes | composees
    assert not sorted(utilisees - set(DICO)), sorted(utilisees - set(DICO))
    assert not sorted(set(DICO) - utilisees), sorted(set(DICO) - utilisees)
    for k, v in DICO.items():
        assert v.get("fr") and v.get("en"), k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k


def test_aucun_texte_francais_en_dur():
    code = _sans_commentaires(MOD)
    litteraux = re.findall(r'"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`', code)
    fautifs = []
    for a, b in litteraux:
        t = re.sub(r"\$\{[^}]*\}", "", a or b)
        t = re.sub(r"<[^>]+>", " ", t)
        if re.search(r"[àâçéèêëîïôûùüÿœÉÈ]", t):
            fautifs.append(t.strip()[:60])
    assert not fautifs, fautifs


def test_devis_avant_puis_confirmation_avant_confirme_cout():
    lancer = MOD[MOD.index("async function lancer()"):MOD.index("/* ── le résultat")]
    assert lancer.index("__dzDialogue.confirmer(") < lancer.index("corps.confirme_cout = true") \
        < lancer.index('api("POST", "/parallaxe/decouper"')
    assert "if (!ok) return;" in lancer
    assert "/parallaxe/modeles?w=" in MOD and "#plxCout" in MOD                     # le coût affiché avant le clic


def test_syntaxe_du_module():
    node = shutil.which("node")
    if not node:
        pytest.skip("node introuvable")
    with tempfile.TemporaryDirectory() as t:
        f = pathlib.Path(t) / "parallaxe.mjs"
        f.write_text(MOD, encoding="utf-8")
        r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
