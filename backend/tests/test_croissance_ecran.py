# -*- coding: utf-8 -*-
"""t492 (09/11/2026) — l'écran « Croissance » (frontend/shared/dz-croissance.js, 5e onglet du tiroir F1) : copie dist
identique, balise dans la SPA après dz-prospects.js, clés FR/EN complètes et employées, aucune chaîne en dur, aucun mot
« publier », listes alignées sur le serveur, banc node du composant et du tiroir.
t495 (26/11/2026) : la section « Gagnants de ma niche » — grille alignée sur le serveur, seules écritures permises
(niche, enregistrer, devis gratuit, analyse sur accord), aucun POST d'analyse sans max_usd.
t498 (26/11/2026) : « Recycler ce gagnant » — ses éléments et raisons suivent recyclage.py, ses seules écritures sont
les routes /api/recyclage/{id}/redaction et /brouillons (en plus du relevé).
Run : & $PY tests/test_croissance_ecran.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
SRC = (SHARED / "dz-croissance.js").read_text(encoding="utf-8")
I18N = json.loads((SHARED / "i18n" / "croissance.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(RACINE / "backend"))


def _liste(nom: str) -> list[str]:
    i = SRC.index(f"var {nom} = [")
    return re.findall(r'"([a-z0-9_]+)"', SRC[i:SRC.index("];", i)])


def test_copies_dist_identiques():
    for f in ("dz-croissance.js", "dz-agent.js", "dz-agent-logique.js", "dz-i18n-dico.js"):
        assert (SHARED / f).read_bytes() == (DIST / f).read_bytes(), f


def test_balise_apres_dz_prospects():
    html = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    balise = '<script src="/shared/dz-croissance.js"></script>'
    assert html.count(balise) == 1
    assert html.index('src="/shared/dz-prospects.js"') < html.index(balise)
    assert html.index("/shared/dz-i18n-dico.js") < html.index(balise), "après le dictionnaire"


def test_listes_suivent_le_serveur():
    from app.services import croissance as CR, metrics_service as MS
    assert _liste("JALONS") == [f"j{j}" for j in CR.JALONS]
    assert set(_liste("JALONS")) == set(MS._SANS["jalons"])
    src_ms = (RACINE / "backend" / "app" / "services" / "metrics_service.py").read_text(encoding="utf-8")
    assert set(_liste("RAISONS")) == set(re.findall(r'raison=(?:None if m is not None else )?"([a-z_]+)"', src_ms)), "les raisons rendues par le serveur"
    src_ig = (RACINE / "backend" / "app" / "services" / "instagram_publisher.py").read_text(encoding="utf-8")
    cles = set(re.findall(r'"([a-z_]+)": None', src_ig[src_ig.index("async def fetch_compte"):]))
    assert set(_liste("TUILES_COMPTE")) <= cles, "tuiles hors du contrat de fetch_compte"
    assert set(_liste("TUILES_POSTS")) <= {"posts", *MS._CLES}
    from app.services import croissance_gagnants as CG
    assert tuple(_liste("GRILLE")) == CG.GRILLE, "la grille fixe de l'analyse"
    src_cg = (RACINE / "backend" / "app" / "services" / "croissance_gagnants.py").read_text(encoding="utf-8")
    assert set(_liste("MESURES")) == set(re.findall(r'"(vues|interactions)" if _nombre', src_cg)), "les mesures du serveur"
    from app.services import recyclage as RC                      # t498
    assert _liste("ELEMENTS_RECYCLAGE") == list(RC.ELEMENTS)
    src_rc = (RACINE / "backend" / "app" / "services" / "recyclage.py").read_text(encoding="utf-8")
    assert set(_liste("RAISONS_RECYCLAGE")) == {"cle", *re.findall(r'\("(sans_[a-z]+)" if el (?:==|in)', src_rc)}, "raisons des cartes"


def test_cles_fr_en():
    for k, v in I18N.items():
        assert re.fullmatch(r"croissance\.[a-z_]+\.[a-z0-9_]+", k), f"trois segments : {k}"
        assert isinstance(v.get("fr"), str) and v["fr"].strip(), f"FR manquant : {k}"
        assert isinstance(v.get("en"), str) and v["en"].strip(), f"EN manquant : {k}"
        assert sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"])), k
    employees = set(re.findall(r'"(croissance\.[a-z_]+\.[a-z0-9_]+)"', SRC))
    employees |= {f"croissance.compte.{t}" for t in _liste("TUILES_COMPTE")}     # clés construites sur les listes
    employees |= {f"croissance.posts.{t}" for t in _liste("TUILES_POSTS")}
    employees |= {f"croissance.jalon.{j}" for j in _liste("JALONS")}
    employees |= {f"croissance.raison.{r}" for r in _liste("RAISONS")}
    employees |= {f"croissance.grille.{g}" for g in _liste("GRILLE")}                       # t495
    employees |= {f"croissance.niche.{p}_{m}" for p in ("habituel", "valeur") for m in _liste("MESURES")}
    employees |= {f"croissance.recyclage.{e}" for e in _liste("ELEMENTS_RECYCLAGE")}           # t498
    employees |= {f"croissance.raison_recyclage.{r}" for r in _liste("RAISONS_RECYCLAGE")}
    assert employees <= set(I18N), "clés employées sans traduction : " + str(sorted(employees - set(I18N)))
    assert set(I18N) <= employees, "clés orphelines : " + str(sorted(set(I18N) - employees))


def test_onglet_du_tiroir():
    agent = json.loads((SHARED / "i18n" / "agent.json").read_text(encoding="utf-8"))
    assert agent["agent.onglet.croissance"] == {"fr": "Croissance", "en": "Growth"}
    assert "agent.croissance.indisponible" in agent
    logique = (SHARED / "dz-agent-logique.js").read_text(encoding="utf-8")
    assert '["demander", "campagnes", "veille", "prospects", "croissance"]' in logique
    tiroir = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert "window.DzCroissance" in tiroir and 'ongletBouton("croissance", "agent.onglet.croissance")' in tiroir


def test_dictionnaire_assemble():
    dico = (SHARED / "dz-i18n-dico.js").read_text(encoding="utf-8")
    for k in list(I18N) + ["agent.onglet.croissance", "agent.croissance.indisponible"]:
        assert f'"{k}"' in dico, k


def test_aucune_chaine_visible_en_dur():
    sans = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    sans = re.sub(r"(?m)^\s*//.*$", "", sans)
    for m in re.finditer(r'texte:\s*"([^"]*)"', sans):
        assert not re.search(r"[A-Za-zÀ-ÿ]", m.group(1)), "texte visible en dur : " + m.group(0)
    assert not re.search(r"textContent\s*=\s*\"[A-Za-zÀ-ÿ]", sans)
    assert "innerHTML" not in sans, "les titres des posts ne passent jamais par innerHTML"


def test_lecture_seule():
    sans = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    assert not re.search(r"publi(er|sh)|/fire|/schedule/validate", sans, re.I)
    ecritures = re.findall(r'fetch\(([^,]+),\s*\{\s*method:\s*"POST"', sans)
    # t498 : le relevé, puis la rédaction d'UNE carte acceptée et les brouillons du recyclage (adresse sous `base`)
    assert ecritures == ['"/api/schedule/analytics/refresh"', 'base + "/redaction"', 'base + "/brouillons"'], ecritures
    assert 'var base = "/api/recyclage/" + encodeURIComponent(String(p.id));' in sans
    assert "max_usd: usd" in sans, "la rédaction part au montant de la carte affichée"
    # t495 : les autres écritures passent par envoyer(url, méthode, corps) — la niche, l'enregistrement (métadonnées),
    # le devis GRATUIT et l'analyse, celle-ci avec max_usd = le montant du devis affiché sur le bouton
    envois = re.findall(r'envoyer\(("[^"]+"(?:\s*\+[^,]+)?),\s*"([A-Z]+)"', sans)
    assert sorted((u.split('"')[1] + u.split('"')[-2] if u.count('"') > 2 else u.split('"')[1], m) for u, m in envois) == sorted([
        ("/api/croissance/niche", "PUT"), ("/api/croissance/enregistres", "POST"),
        ("/api/croissance/gagnants//devis", "POST"), ("/api/croissance/gagnants//analyse", "POST"),
        ("/api/croissance/x/releve", "POST"), ("/api/croissance/x/accord", "PUT"),   # t500 : relevé X sur accord, accord
        ("/api/schedule/croissance/alertes", "PUT")]), envois   # t504 (G12) : l'accord du bilan et de l'alerte WhatsApp
    # t504 : l'accord part au prix du devis affiché, seulement case cochée ; le retrait est un DELETE
    assert "usd_accepte: devisA.usd_par_message" in sans and "if (!devisA || !caseAccord.checked) return;" in sans
    assert sans.count('{ method: "DELETE" }') == 1
    assert sans.count('"/analyse", "POST", { max_usd: devisUsd') == 1, "l'analyse n'est envoyée qu'avec l'accord du devis"
    for k, v in I18N.items():
        assert not re.search(r"publi(er|sh)", v["fr"] + " " + v["en"], re.I), k


def test_charte():
    assert not re.search(r"border-radius:\s*\d", SRC), "angles : le jeton var(--r) seulement"
    assert "var(--accent" in SRC and "var(--stroke" in SRC


@pytest.mark.parametrize("banc", ["croissance.test.mjs", "agent-onglets.test.mjs"])
def test_banc_node(banc):
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent")
    r = subprocess.run([node, str(SHARED / "qa" / banc)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "OK" in r.stdout, (r.stdout + r.stderr)[-1500:]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
