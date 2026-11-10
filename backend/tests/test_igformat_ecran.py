# -*- coding: utf-8 -*-
"""t494 (09/11/2026) — le format Instagram dans l'éditeur de post : module partagé frontend/shared/dz-ig-format.js,
maillon de queue scripts/patch_bundle_dzigformat.py, son inverse, dictionnaire FR/EN, banc node.
Run : & $PY tests/test_igformat_ecran.py   (depuis backend/)"""
import importlib, json, pathlib, re, shutil, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
SRC = (SHARED / "dz-ig-format.js").read_text(encoding="utf-8")
I18N = json.loads((SHARED / "i18n" / "igformat.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(RACINE / "backend"))
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
M = importlib.import_module("patch_bundle_dzigformat")
BUNDLE = M.BUNDLE.read_bytes().decode("utf-8-sig")


def _liste(nom: str) -> list[str]:
    i = SRC.index(f"var {nom} = [")
    return re.findall(r'"([A-Za-z_]+)"', SRC[i:SRC.index("];", i)])


def test_copies_dist_identiques():
    for f in ("dz-ig-format.js", "dz-i18n-dico.js"):
        assert (SHARED / f).read_bytes() == (DIST / f).read_bytes(), f


def test_balise_dans_la_spa():
    html = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    balise = '<script src="/shared/dz-ig-format.js"></script>'
    assert html.count(balise) == 1
    assert html.index("/shared/dz-i18n-dico.js") < html.index(balise), "après le dictionnaire"


def test_listes_suivent_le_serveur():
    from app.services import instagram_publisher as ig
    assert tuple(_liste("FORMES")) == ig.FORMES
    assert tuple(_liste("GRADUATIONS")) == ig.GRADUATIONS


def test_cles_fr_en():
    for k, v in I18N.items():
        assert re.fullmatch(r"igformat\.[a-z_]+\.[a-z_]+", k), f"trois segments : {k}"
        assert isinstance(v.get("fr"), str) and v["fr"].strip() and isinstance(v.get("en"), str) and v["en"].strip(), k
        assert sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"])), k
    employees = set(re.findall(r'"(igformat\.[a-z_]+\.[a-z_]+)"', SRC))
    employees |= {f"igformat.forme.{f}" for f in _liste("FORMES")} | {f"igformat.aide.{f}" for f in _liste("FORMES")}
    employees |= {f"igformat.graduation.{g.lower()}" for g in _liste("GRADUATIONS")}
    assert employees <= set(I18N), "clés employées sans traduction : " + str(sorted(employees - set(I18N)))
    assert set(I18N) <= employees, "clés orphelines : " + str(sorted(set(I18N) - employees))
    dico = (SHARED / "dz-i18n-dico.js").read_text(encoding="utf-8")
    assert all(f'"{k}"' in dico for k in I18N)


def test_module_sur():
    sans = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
    assert "innerHTML" not in sans
    for m in re.finditer(r'texte:\s*"([^"]*)"', sans):
        assert not re.search(r"[A-Za-zÀ-ÿ]", m.group(1)), "texte visible en dur : " + m.group(0)
    assert not re.search(r"/fire|media_publish|fal\.run|fal\.ai", sans), "le module ne publie ni ne dépose rien lui-même"
    ecrit = set(re.findall(r'fetch\(("[^"]+"(?: \+ [^,]+)?), \{ method: "PUT"', sans))
    assert len(ecrit) == 2 and all("instagram" in e for e in ecrit), ecrit
    assert not re.search(r"border-radius:\s*\d", SRC)


def test_accord_jamais_precoche():
    """La case du dépôt ne se coche que par la valeur lue du serveur ; le serveur est à False par défaut."""
    assert "caseAccord.checked = !!E.depot;" in SRC and "depot: false" in SRC
    from app.services import instagram_publisher as ig
    src_ig = pathlib.Path(ig.__file__).read_text(encoding="utf-8")
    assert 'return {"depot_fal": d.get("depot_fal") is True}' in src_ig


def test_maillon_applique_et_reversible():
    assert BUNDLE.count(M.MARKER) == 1 and not M.partiel(BUNDLE)
    avant = M.defaire(BUNDLE)
    assert M.MARKER not in avant and "__dzIgFormat" not in avant
    assert M.appliquer(avant) == BUNDLE, "aller-retour à l'octet"
    assert len(M.PAIRES) == 1 and all("\n" not in a + z for a, z in M.PAIRES)


def test_maillon_ne_mord_aucun_voisin():
    """Les maillons dont le texte borde l'ancre se disent toujours « déjà appliqué »."""
    for nom in ("dzmethodes", "dzdiffusion", "dzespace", "dzassistant", "dzcreer3d"):
        r = subprocess.run([sys.executable, str(RACINE / "scripts" / f"patch_bundle_{nom}.py"), "--check"],
                           capture_output=True, cwd=RACINE)     # dzespace lit le bundle par un chemin relatif
        sortie = (r.stdout + r.stderr).decode("utf-8", "replace")     # la console Windows n'écrit pas en UTF-8
        assert r.returncode == 0 and f"[{nom}]" in sortie and "appliqu" in sortie and "partiel" not in sortie, nom + " : " + sortie[-300:]


def test_epingles():
    assert BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181
    assert BUNDLE.count(M.CONFIRMER) == 30
    assert BUNDLE.count("\n") == BUNDLE.count("\r\n")
    assert all(M.hors_couche(BUNDLE, z) for _a, z in M.PAIRES)


def test_montage_conditionnel():
    z = M.PAIRES[0][1]
    assert 'e.channels.includes("instagram")&&' in z, "seulement si le post vise instagram"
    assert '"dzigf:"+e.id' in z and "{statut:e.status}" in z
    i = BUNDLE.index(M.MARKER)
    assert BUNDLE.rindex('dzT("scheduler.post.canaux")', 0, i) > 0 and BUNDLE.index('dzT("scheduler.routage.legende")', i) - i < 400


def test_inverse_inscrit_en_tete():
    AIDE = importlib.import_module("_i18n_l1_aide")
    assert AIDE.avant_dzigformat(BUNDLE) == M.defaire(AIDE.avant_dzplanifaff(BUNDLE)), "dzplanifaff (aval) défait d'abord"
    assert AIDE.avant_dzigformat(M.defaire(BUNDLE)) == AIDE.avant_dzplanifaff(M.defaire(BUNDLE)), "sans marqueur : seul l'aval est défait"
    corps = pathlib.Path(AIDE.__file__).read_text(encoding="utf-8")
    c = corps[corps.index("def avant_dzmethodes("):corps.index("def avant_dzcreer3d(")]
    assert "bundle = avant_dzigformat(bundle)" in c and c.index("avant_dzigformat(") < c.index("if _m.MARKER not in bundle")


def test_bundle_syntaxe_et_banc_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent")
    r = subprocess.run([node, "--check", str(M.BUNDLE)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-400:]
    r = subprocess.run([node, str(SHARED / "qa" / "ig-format.test.mjs")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "OK" in r.stdout, (r.stdout + r.stderr)[-1500:]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
