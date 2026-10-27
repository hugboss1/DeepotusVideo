# -*- coding: utf-8 -*-
"""t352 (27/10/2026) — l'écran « Veille » (frontend/shared/dz-veille.js, 3e onglet du tiroir F1) : copie dist identique,
balise dans la SPA après dz-campagnes.js, clés FR/EN complètes et employées, aucune chaîne en dur, aucun mot « publier »,
thèmes alignés sur la grille du serveur, banc node du composant.
Run : & $PY tests/test_veille_ecran.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
SRC = (SHARED / "dz-veille.js").read_text(encoding="utf-8")
I18N = json.loads((SHARED / "i18n" / "veille.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(RACINE / "backend"))


def _liste(nom: str) -> list[str]:
    i = SRC.index(f"var {nom} = [")
    return re.findall(r'"([a-z_]+)"', SRC[i:SRC.index("];", i)])


def test_copie_dist_identique():
    assert (SHARED / "dz-veille.js").read_bytes() == (DIST / "dz-veille.js").read_bytes()


def test_balise_apres_dz_campagnes():
    html = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    balise = '<script src="/shared/dz-veille.js"></script>'
    assert html.count(balise) == 1
    assert html.index('src="/shared/dz-campagnes.js"') < html.index(balise)
    assert html.index("/shared/dz-i18n-dico.js") < html.index(balise), "après le dictionnaire"


def test_themes_suivent_la_grille():
    from app.services import veille_grille as G
    assert tuple(_liste("THEMES")) == G.THEMES
    assert set(_liste("CHEZ_NOUS")) == {"regle", "partiel", "absent", "inconnu"}


def test_cles_fr_en():
    for k, v in I18N.items():
        assert re.fullmatch(r"veille\.[a-z_]+\.[a-z_]+", k), f"trois segments : {k}"
        assert isinstance(v.get("fr"), str) and v["fr"].strip(), f"FR manquant : {k}"
        assert isinstance(v.get("en"), str) and v["en"].strip(), f"EN manquant : {k}"
        assert sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"])), k
    employees = set(re.findall(r'"(veille\.[a-z_]+\.[a-z_]+)"', SRC))
    employees |= {f"veille.theme.{t}" for t in _liste("THEMES")}           # clés construites sur les listes
    employees |= {f"veille.etat.{e}" for e in _liste("ETATS")}
    employees |= {f"veille.chez_nous.{c}" for c in _liste("CHEZ_NOUS")}
    assert employees <= set(I18N), "clés employées sans traduction : " + str(sorted(employees - set(I18N)))
    assert set(I18N) <= employees, "clés orphelines : " + str(sorted(set(I18N) - employees))


def test_dictionnaire_assemble():
    dico = (SHARED / "dz-i18n-dico.js").read_text(encoding="utf-8")
    for k in I18N:
        assert f'"{k}"' in dico, k
    assert (SHARED / "dz-i18n-dico.js").read_bytes() == (DIST / "dz-i18n-dico.js").read_bytes()


def test_aucune_chaine_visible_en_dur():
    sans = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    sans = re.sub(r"(?m)^\s*//.*$", "", sans)
    for m in re.finditer(r'texte:\s*"([^"]*)"', sans):
        assert not re.search(r"[A-Za-zÀ-ÿ]", m.group(1)), "texte visible en dur : " + m.group(0)
    assert not re.search(r"textContent\s*=\s*\"[A-Za-zÀ-ÿ]", sans)
    assert "innerHTML" not in sans, "les citations collectées ne passent jamais par innerHTML"


def test_aucun_mot_publier():
    sans = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    assert not re.search(r"publi(er|sh)|/fire|scheduled", sans, re.I)
    for k, v in I18N.items():
        assert not re.search(r"publi(er|sh)", v["fr"] + " " + v["en"], re.I), k


def test_banc_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent")
    r = subprocess.run([node, str(SHARED / "qa" / "veille.test.mjs")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "OK" in r.stdout, (r.stdout + r.stderr)[-1500:]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
