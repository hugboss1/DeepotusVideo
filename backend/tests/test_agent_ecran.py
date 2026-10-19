# -*- coding: utf-8 -*-
"""A3/A4 (spec 2026-10-19-agent-aide-design.md) — l'écran de l'assistant : libellés FR/EN complets et employés,
copies dist identiques, balises dans la SPA et dans les labs, banc node de la logique pure.
Run : & $PY tests/test_agent_ecran.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
I18N = json.loads((SHARED / "i18n" / "agent.json").read_text(encoding="utf-8"))


def test_libelles_complets():
    assert len(I18N) >= 14
    for k, v in I18N.items():
        assert k.startswith("agent."), k
        assert v.get("fr") and v.get("en"), k


def test_dictionnaire_assemble():
    dico = (SHARED / "dz-i18n-dico.js").read_text(encoding="utf-8")
    for k in I18N:
        assert f'"{k}"' in dico, k


FICHIERS = ["dz-agent.js", "dz-agent-logique.js", "dz-agent-pointeur.js"]
BALISE_SPA = '<script type="module" src="/shared/dz-agent.js"></script>'


def test_copies_dist_identiques():
    for f in FICHIERS:
        assert (SHARED / f).read_bytes() == (DIST / f).read_bytes(), f


def test_balise_dans_la_spa():
    html = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    assert html.count(BALISE_SPA) == 1
    assert html.index("/shared/dz-plafonds.js") < html.index(BALISE_SPA), "après la couche des plafonds"


def test_cles_employees_existent():
    src = "".join((SHARED / f).read_text(encoding="utf-8") for f in ("dz-agent.js", "dz-agent-pointeur.js"))
    employees = set(re.findall(r'"(agent\.[a-z_]+\.[a-z_.]+)"', src))
    assert employees, "le tiroir passe par T(…)"
    assert employees <= set(I18N), employees - set(I18N)
    assert not re.search(r">[A-ZÀ-Ý][a-zà-ÿ]{3,}[^<]*<", src), "aucun texte visible en dur dans le HTML généré"


def test_banc_node_logique():
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent")
    r = subprocess.run([node, str(SHARED / "qa" / "agent_logique.test.mjs")], capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0 and "OK" in r.stdout, r.stderr[-800:]


def test_pointeur_present():
    src = (SHARED / "dz-agent-pointeur.js").read_text(encoding="utf-8")
    assert 'import { creerPointeur } from "./dz-agent-pointeur.js";' in (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert "courbe(" in src and "dzAgentCurseur" in src and "dzAgentHalo" in src
    assert 'matchMedia("(prefers-reduced-motion' in src, "le mouvement réduit est lu en JS"
    assert "if (reduit()) return finir();" in src, "le mouvement réduit saute l'animation"


LABS = ["vectorlab", "photolab", "spritelab", "tilelab"]
BALISE_LAB = '<script type="module" src="/shared/dz-agent-cadre.js"></script>'


def test_cadre_copie_et_balises():
    assert (SHARED / "dz-agent-cadre.js").read_bytes() == (DIST / "dz-agent-cadre.js").read_bytes()
    for lab in LABS:
        html = (RACINE / "frontend" / lab / "index.html").read_text(encoding="utf-8")
        assert html.count(BALISE_LAB) == 1, lab
        assert html.index("/shared/dz-plafonds.js") < html.index(BALISE_LAB), lab


def test_cadre_verifie_l_origine():
    src = (SHARED / "dz-agent-cadre.js").read_text(encoding="utf-8")
    assert "ev.origin !== location.origin" in src and "postMessage(" in src
    assert "ev.source !== window.parent" in src, "le cadre ne répond qu'à la SPA qui l'héberge"
    assert "d.libelle" in src, "répond à la source, lit le sous-élément libellé comme le tiroir"
    agent = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert "ev.origin !== location.origin" in agent, "le tiroir ne lit que les réponses de même origine"
    assert "ev.source !== cadre.contentWindow" in agent, "la réponse vient du cadre interrogé"
    assert "b.width > 0 && b.height > 0 ? composer(b, t.interne) : null" in agent, "cadre démonté ou masqué : rect nul"
    pointeur = (SHARED / "dz-agent-pointeur.js").read_text(encoding="utf-8")
    assert "if (!r) { effacerPointeur(); return false; }" in pointeur, "rect nul : le pointeur s'efface"
    assert "candidats(document, d.selecteur" in src, "le cadre lit les candidats comme le tiroir (logique partagée)"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
