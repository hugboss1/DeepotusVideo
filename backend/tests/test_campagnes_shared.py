# -*- coding: utf-8 -*-
"""t285 (T8) — le composant partagé de conversation de l'agent Campagnes (frontend/shared/dz-campagnes.js) :
copie dist identique, balise dans la SPA après dz-agent.js, clés FR/EN complètes et employées, aucune chaîne en dur,
aucun mot « publier », banc node du composant.
Run : & $PY tests/test_campagnes_shared.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
SRC = (SHARED / "dz-campagnes.js").read_text(encoding="utf-8")
I18N = json.loads((SHARED / "i18n" / "campagnes.json").read_text(encoding="utf-8"))
GENRES = ("image", "video", "voix")          # campagnes.genre.<genre> : clé construite, pas écrite en toutes lettres


def test_copie_dist_identique():
    assert (SHARED / "dz-campagnes.js").read_bytes() == (DIST / "dz-campagnes.js").read_bytes()


def test_balise_apres_dz_agent():
    html = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    balise = '<script src="/shared/dz-campagnes.js"></script>'
    assert html.count(balise) == 1
    assert html.index('src="/shared/dz-agent.js"') < html.index(balise), "après dz-agent.js"
    assert html.index("/shared/dz-plafonds.js") < html.index(balise), "après la couche des plafonds (window.fetch)"


def test_cles_fr_en():
    assert I18N, "campagnes.json est vide"
    for k, v in I18N.items():
        assert re.fullmatch(r"campagnes\.[a-z_]+\.[a-z_]+", k), f"trois segments : {k}"
        assert isinstance(v.get("fr"), str) and v["fr"].strip(), f"FR manquant : {k}"
        assert isinstance(v.get("en"), str) and v["en"].strip(), f"EN manquant : {k}"
        # les variables {x} sont les mêmes des deux côtés
        assert sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"])), k
    employees = set(re.findall(r'"(campagnes\.[a-z_]+\.[a-z_]+)"', SRC))
    employees |= {f"campagnes.genre.{g}" for g in GENRES}
    # t285 T9 : campagnes.outil.<nom>, clé construite sur la liste OUTILS du composant
    i = SRC.index("var OUTILS = [")
    employees |= {f"campagnes.outil.{o}" for o in re.findall(r'"([a-z_]+)"', SRC[i:SRC.index("];", i)])}
    # t285 T9 : les libellés du mode Agent Campagnes du Planificateur (maillon dzagentplan, source aplatie)
    PLAN = (RACINE / "frontend" / "patches" / "agent-plan.js").read_text(encoding="utf-8")
    employees |= set(re.findall(r'"(campagnes\.[a-z_]+\.[a-z_]+)"', PLAN))
    assert employees, "le composant passe par T(…)"
    assert employees <= set(I18N), "clés employées sans traduction : " + str(sorted(employees - set(I18N)))
    assert set(I18N) <= employees, "clés orphelines : " + str(sorted(set(I18N) - employees))


def test_dictionnaire_assemble():
    dico = (SHARED / "dz-i18n-dico.js").read_text(encoding="utf-8")
    for k in I18N:
        assert f'"{k}"' in dico, k
    assert (SHARED / "dz-i18n-dico.js").read_bytes() == (DIST / "dz-i18n-dico.js").read_bytes()


def test_aucune_chaine_visible_en_dur():
    sans_commentaires = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    sans_commentaires = re.sub(r"(?m)^\s*//.*$", "", sans_commentaires)
    for m in re.finditer(r'texte:\s*"([^"]*)"', sans_commentaires):
        assert not re.search(r"[A-Za-zÀ-ÿ]", m.group(1)), "texte visible en dur : " + m.group(0)
    assert not re.search(r"textContent\s*=\s*\"[A-Za-zÀ-ÿ]", sans_commentaires)


def test_aucun_mot_publier():
    # la porte 2 est le Planificateur : ni dans le code, ni dans un libellé du composant
    sans_commentaires = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    assert not re.search(r"publi(er|sh)|/fire|scheduled", sans_commentaires, re.I)
    for k, v in I18N.items():
        assert not re.search(r"publi(er|sh)", v["fr"] + " " + v["en"], re.I), k


def test_routes_de_generation_fermees():
    # la carte ne peut désigner que ces trois routes
    for r in ("/api/generate", "/api/images/generate", "/api/audio/voiceover"):
        assert f'"{r}"' in SRC


def test_banc_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent")
    r = subprocess.run([node, str(SHARED / "qa" / "campagnes.test.mjs")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "OK" in r.stdout, (r.stdout + r.stderr)[-1500:]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


def test_libelles_des_outils_suivent_le_registre():
    """t285 T9 (relecture) : une ligne d'outil = un libellé traduit par nom ; la liste du composant suit
    agent_outils.OUTILS (aucun outil sans libellé, aucun libellé orphelin)."""
    reg = (RACINE / "backend" / "app" / "services" / "agent_outils.py").read_text(encoding="utf-8")
    bloc = reg[reg.index("OUTILS: dict[str, dict] = {"):]
    outils = set(re.findall(r'^    "([a-z_]+)": \{"nature"', bloc, re.M))
    liste = set(re.findall(r'"([a-z_]+)"', SRC[SRC.index("var OUTILS = ["):SRC.index("];", SRC.index("var OUTILS = ["))]))
    assert outils and liste == outils, (sorted(outils ^ liste))
    assert all(f"campagnes.outil.{o}" in I18N for o in outils) and "campagnes.outil.inconnu" in I18N
    assert "campagnes.fil.outil" not in I18N and '"campagnes.fil.outil"' not in SRC, "plus de résumé serveur affiché"
