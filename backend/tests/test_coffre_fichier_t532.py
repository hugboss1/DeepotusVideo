"""t532 (20/11/2026) — couche hébergée, pièce ③ : « retenir » le coffre sans DPAPI, par un fichier de clé.

Plan docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md. Sur le VPS (Linux), DPAPI n'existe pas. Quand
DEEPOTUS_COFFRE_CLE_FICHIER est posé, « retenir » tire une clé aléatoire de 32 octets dans CE fichier (créé 0600, hors
du volume sauvegardé) et range dans coffre.pc un sceau AES-256-GCM du mot de passe (magie DZRF1). Aucun des deux
fichiers ne livre seul le mot de passe. Le coffre DZKV1 lui-même n'est pas touché. Sous Windows, DPAPI reste la voie.

Sous Windows, ce banc SIMULE l'absence de DPAPI ; le cas des permissions POSIX ne tourne que sous Linux (job
bancs-linux de .github/workflows/image-vps.yml).
Run (depuis backend/) : & $PY tests/test_coffre_fichier_t532.py
"""
import os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcoffref_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp / "data")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.pop("DEEPOTUS_COFFRE_CLE_FICHIER", None)
for _k in ("FAL_KEY", "MESHY_API_KEY", "HEYGEN_API_KEY"):
    os.environ.pop(_k, None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from loguru import logger  # noqa: E402
logger.remove()
from app.services import coffre as C  # noqa: E402

MDP = "phrase du coffre assez longue"
CLE = _tmp / "secrets" / "coffre.cle"


@pytest.fixture(autouse=True)
def _propre(monkeypatch):
    """Chaque cas : pas de DPAPI, un coffre posé et OUVERT, aucun sceau, pas de fichier de clé."""
    monkeypatch.setattr(C, "_dpapi_disponible", lambda: False)
    monkeypatch.setenv("DEEPOTUS_COFFRE_CLE_FICHIER", str(CLE))
    C.fermer()
    for f in (C.FICHIER, C.SCEAU_PC, CLE):
        f.unlink(missing_ok=True)
    CLE.parent.mkdir(parents=True, exist_ok=True)
    C.poser(MDP, {"FAL_KEY": "fal-secret"})
    C.ouvrir(MDP)
    yield
    C.fermer()


def test_voie_choisie():
    assert C.voie_retenir() == "fichier"


def test_voie_absente_sans_variable(monkeypatch):
    monkeypatch.delenv("DEEPOTUS_COFFRE_CLE_FICHIER")
    assert C.voie_retenir() is None
    with pytest.raises(C.RetenirIndisponible):
        C.retenir()
    assert not C.SCEAU_PC.exists()


def test_voie_dpapi_prioritaire(monkeypatch):
    monkeypatch.setattr(C, "_dpapi_disponible", lambda: True)
    assert C.voie_retenir() == "dpapi"


def test_aller_retour_sans_rien_demander():
    avant = C.FICHIER.read_bytes()
    C.retenir()
    assert C.retenu()
    assert CLE.is_file() and len(CLE.read_bytes()) == 32
    sceau = C.SCEAU_PC.read_bytes()
    assert sceau.startswith(b"DZRF1\n")
    assert MDP.encode() not in sceau and MDP.encode() not in CLE.read_bytes()
    assert C.FICHIER.read_bytes() == avant, "le coffre DZKV1 n'est pas réécrit"
    C.fermer()
    assert not C.ouvert()
    assert C.ouvrir_par_dpapi() is True
    assert C.ouvert() and C.lire_cle("FAL_KEY") == "fal-secret"


def test_retenir_garde_une_cle_existante():
    C.retenir()
    cle = CLE.read_bytes()
    C.retenir()
    assert CLE.read_bytes() == cle


def test_fichier_de_cle_absent_coffre_verrouille_sans_exception():
    C.retenir()
    C.fermer()
    CLE.unlink()
    assert C.ouvrir_par_dpapi() is False
    assert C.verrouille()


def test_mauvaise_cle_refus_et_sceau_efface():
    C.retenir()
    C.fermer()
    CLE.write_bytes(os.urandom(32))
    assert C.ouvrir_par_dpapi() is False
    assert C.verrouille()


def test_sceau_trafique():
    C.retenir()
    C.fermer()
    s = bytearray(C.SCEAU_PC.read_bytes())
    s[-1] ^= 1
    C.SCEAU_PC.write_bytes(bytes(s))
    assert C.ouvrir_par_dpapi() is False


def test_oublier_efface_sceau_et_cle():
    C.retenir()
    C.oublier()
    assert not C.SCEAU_PC.exists() and not CLE.exists()
    assert not C.retenu()


def test_changer_mot_de_passe_desarme():
    C.retenir()
    C.changer_mot_de_passe(MDP, "nouvelle phrase du coffre")
    assert not C.retenu() and not CLE.exists()


@pytest.mark.skipif(os.name != "posix", reason="permissions POSIX : job bancs-linux")
def test_permissions_posix():
    C.retenir()
    assert (CLE.stat().st_mode & 0o777) == 0o600
    C.fermer()
    os.chmod(CLE, 0o644)
    assert C.ouvrir_par_dpapi() is False, "une clé lisible par d'autres n'ouvre pas le coffre"
    C.ouvrir(MDP)
    with pytest.raises(C.CleFichierExposee):
        C.retenir()


def test_routes_etat_et_refus_traduit(monkeypatch):
    from app.main import app
    c = TestClient(app)
    e = c.get("/api/reglages/coffre/etat").json()
    assert e["retenir_possible"] is True
    monkeypatch.delenv("DEEPOTUS_COFFRE_CLE_FICHIER")
    assert c.get("/api/reglages/coffre/etat").json()["retenir_possible"] is False
    fr = c.post("/api/reglages/coffre/retenir", headers={"Accept-Language": "fr"})
    en = c.post("/api/reglages/coffre/retenir", headers={"Accept-Language": "en"})
    assert fr.status_code == 501 and en.status_code == 501
    assert "DEEPOTUS_COFFRE_CLE_FICHIER" in fr.json()["detail"] and "DEEPOTUS_COFFRE_CLE_FICHIER" in en.json()["detail"]
    assert fr.json()["detail"] != en.json()["detail"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
