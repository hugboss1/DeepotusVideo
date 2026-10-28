# -*- coding: utf-8 -*-
"""t353 (27/10/2026) — l'écran « Prospects » (frontend/shared/dz-prospects.js, 4e onglet du tiroir F1) : copie dist
identique, balise dans la SPA après dz-veille.js, listes (statuts, transitions, sources, bases, offres, canaux, moyens)
alignées sur le serveur, clés FR/EN complètes et employées, aucune chaîne en dur, aucun envoi ni publication, banc node.
Run : & $PY tests/test_prospects_ecran.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
SRC = (SHARED / "dz-prospects.js").read_text(encoding="utf-8")
I18N = json.loads((SHARED / "i18n" / "prospects.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(RACINE / "backend"))


def _liste(nom: str) -> list[str]:
    i = SRC.index(f"var {nom} = [")
    return re.findall(r'"([a-z_0-9]+)"', SRC[i:SRC.index("];", i)])


def _transitions() -> dict:
    i = SRC.index("var TRANSITIONS = {")
    bloc = SRC[i:SRC.index("};", i)]
    return {k: tuple(re.findall(r'"([a-z_]+)"', v)) for k, v in re.findall(r"(\w+): \[([^\]]*)\]", bloc)}


def test_copie_dist_identique():
    for f in ("dz-prospects.js", "dz-agent.js", "dz-agent-logique.js", "dz-i18n-dico.js"):
        assert (SHARED / f).read_bytes() == (DIST / f).read_bytes(), f


def test_balise_apres_dz_veille():
    html = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    balise = '<script src="/shared/dz-prospects.js"></script>'
    assert html.count(balise) == 1
    assert html.index('src="/shared/dz-veille.js"') < html.index(balise)
    assert html.index("/shared/dz-i18n-dico.js") < html.index(balise), "après le dictionnaire"


def test_listes_suivent_le_serveur():
    from app.services import prospects as P
    assert tuple(_liste("STATUTS")) == P.STATUTS
    assert _transitions() == {k: tuple(v) for k, v in P.TRANSITIONS.items()}
    assert tuple(_liste("SOURCES")) == P.SOURCES
    assert tuple(_liste("BASES")) == P.BASES
    assert tuple(_liste("OFFRES")) == P.OFFRES
    assert tuple(_liste("CANAUX")) == P.CANAUX
    assert tuple(_liste("MOYENS")) == P.MOYENS


def test_cles_fr_en():
    for k, v in I18N.items():
        assert re.fullmatch(r"prospects\.[a-z_]+\.[a-z_0-9]+", k), f"trois segments : {k}"
        assert isinstance(v.get("fr"), str) and v["fr"].strip(), f"FR manquant : {k}"
        assert isinstance(v.get("en"), str) and v["en"].strip(), f"EN manquant : {k}"
        assert sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"])), k
    employees = set(re.findall(r'"(prospects\.[a-z_]+\.[a-z_0-9]+)"', SRC))
    for nom, prefixe in (("STATUTS", "statut"), ("SOURCES", "source"), ("BASES", "base"), ("OFFRES", "offre"),
                         ("CANAUX", "canal"), ("MOYENS", "moyen"), ("NOTES", "note"), ("HISTO", "histo"),
                         ("CRITERES", "critere"), ("FOURNISSEURS", "recherche"),   # t354
                         ("SEQ_STATUTS", "seqstatut"), ("ETAPE_STATUTS", "etapestatut"), ("SEQ_MOTIFS", "seqmotif")):   # t355
        employees |= {f"prospects.{prefixe}.{x}" for x in _liste(nom)}         # clés construites sur les listes
    assert employees <= set(I18N), "clés employées sans traduction : " + str(sorted(employees - set(I18N)))
    assert set(I18N) <= employees, "clés orphelines : " + str(sorted(set(I18N) - employees))


def test_notes_suivent_le_serveur():
    src = (RACINE / "backend" / "app" / "services" / "prospects.py").read_text(encoding="utf-8")
    serveur = set(re.findall(r'"(demo_[a-z]+|plafond_espaces)"', src))
    assert serveur == set(_liste("NOTES")), serveur


def test_dictionnaire_assemble():
    dico = (SHARED / "dz-i18n-dico.js").read_text(encoding="utf-8")
    for k in list(I18N) + ["agent.onglet.prospects", "agent.prospects.espace", "agent.prospects.indisponible"]:
        assert f'"{k}"' in dico, k


def test_aucune_chaine_visible_en_dur():
    sans = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    sans = re.sub(r"(?m)^\s*//.*$", "", sans)
    for m in re.finditer(r'texte:\s*"([^"]*)"', sans):
        assert not re.search(r"[A-Za-zÀ-ÿ]", m.group(1)), "texte visible en dur : " + m.group(0)
    assert not re.search(r"textContent\s*=\s*\"[A-Za-zÀ-ÿ]", sans)
    assert "innerHTML" not in sans


def test_aucun_envoi_ni_publication():
    sans = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    assert not re.search(r"publi(er|sh)|/fire|scheduled|/whatsapp|/envoyer|/send", sans, re.I)


def test_banc_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent")
    for banc in ("prospects.test.mjs", "agent-onglets.test.mjs"):
        r = subprocess.run([node, str(SHARED / "qa" / banc)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0 and "OK" in r.stdout, (banc + " : " + r.stdout + r.stderr)[-1500:]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
