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


FICHIERS = ["dz-agent.js", "dz-agent-logique.js", "dz-agent-pointeur.js", "dz-agent-vision.js"]
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
    assert "requestAnimationFrame(poser)" in pointeur, "écouteurs du lab posés après le défilement de mise en vue"
    assert "candidats(document, d.selecteur" in src, "le cadre lit les candidats comme le tiroir (logique partagée)"


def test_langue_lue_comme_fonction():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert 'typeof window.dzLang === "function"' in src, "dzLang est une fonction dans la SPA"
    assert 'window.dzLang === "en"' not in src


def test_tiroir_exclu_des_candidats():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert "!tiroir.contains(" in src, "le tiroir ne se vise pas lui-même"
    assert "!bouton.contains(" in src, "ni le bouton « Demander »"


def test_capture_de_l_onglet():
    src = (SHARED / "dz-agent-vision.js").read_text(encoding="utf-8")
    assert "getDisplayMedia(" in src and "preferCurrentTab: true" in src
    assert 'displaySurface !== "browser"' in src and "memeOnglet(" in src, "seul CET onglet est accepté"
    assert "reduire(" in src and 'toDataURL("image/jpeg", 0.8)' in src
    assert src.count(".stop()") >= 1 and "finally" in src, "les pistes sont coupées quoi qu'il arrive"
    assert "avant()" in src and "apres()" in src, "le tiroir est masqué pendant la prise"
    assert "window.isSecureContext" in src


def test_vision_dans_le_tiroir():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert 'from "./dz-agent-vision.js"' in src
    r = src[src.index("async function regarder("):]
    assert r.index("captureDisponible()") < r.index("accord(") < r.index("capturer(") < r.index("envoyerVue("), \
        "disponibilité, accord (devis), capture, envoi : dans cet ordre"
    assert "/api/agent/estimer" in src and "max_usd" in src
    assert ".filter((m) => m.vision)" in src, "l'accord ne propose que les moteurs qui voient"
    assert 'e.faire === "voir"' in src and 'e.faire === "pointer_xy"' in src
    assert "versEcran(" in src and "cliquable(" in src and "document.elementsFromPoint(" in src
    assert "occupe || enVue" in src, "une seule demande à la fois"


def test_libelles_vision():
    for k in ("agent.vision.voir", "agent.vision.accord", "agent.vision.accord_gratuit", "agent.vision.envoyer",
              "agent.vision.annuler", "agent.vision.moteur", "agent.vision.indisponible", "agent.vision.aucun_moteur",
              "agent.vision.refusee", "agent.vision.onglet", "agent.vision.ici", "agent.vision.devis"):
        assert k in I18N, k
    assert "${usd}" in I18N["agent.vision.accord"]["en"] and "{usd} $" in I18N["agent.vision.accord"]["fr"]


def test_corrections_de_revue_du_tiroir():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    d = src[src.index("function dessiner("):src.index("// un seul envoi")]
    assert "boiteAccord" in d, "dessiner() remet la boîte d'accord au bas du fil"
    assert "boiteAccord = null" in src and "boiteAccord = boite" in src
    r = src[src.index("async function regarder("):src.index("async function envoyerVue(")]
    assert r.index("enVue = true") < r.index("captureDisponible()") < r.index("moteursConnus()"), "verrou dès l'entrée"
    assert "btnEnvoyer.disabled = true" in r and "btnEnvoyer.disabled = false" in r
    assert "let chargement = null" in src and "chargement = null; chargerMoteurs()" in src
    assert "dataset.charge" not in src
    p = src[src.index("async function pointerXY("):]
    assert "tiroir.getBoundingClientRect()" in p and "basculer(false)" in p and "document.elementsFromPoint(" in p
    assert p.index("attendre(60)") < p.index("moi !== tourPointeur", p.index("attendre(60)")) < p.index("elementsFromPoint(")
    assert "window.innerHeight - v.h" in p, "décalage du bandeau de partage"
    assert "agent.vision.accord_inconnu" in src and 'j.cout === "a_mesurer"' in src
    assert 'x.type !== "voir"' in src, "pas de nouvelle capture en réponse à une capture"
    e = src[src.index("async function envoyerVue("):src.index("async function pointerXY(")]
    assert "!j.texte.trim()" in e and "oui.focus()" in src


def test_capture_meme_image_pour_vue_et_taille():
    src = (SHARED / "dz-agent-vision.js").read_text(encoding="utf-8")
    assert "requestVideoFrameCallback((_, meta)" in src and "meta.width" in src
    assert src.count("window.innerHeight") == 1, "la vue n'est mesurée qu'une fois, avec l'image"
    assert "agent.vision.accord_inconnu" in I18N


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
