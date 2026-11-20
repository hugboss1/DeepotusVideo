"""t533 (20/11/2026) — couche hébergée, pièce ④ : Réglages › Chemins sous Linux.

Plan docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md. Sur le VPS, le dépôt SFTP du PC est monté en
/depot (lecture seule) et déclaré source de bibliothèque : le type « dossier » accepte un chemin POSIX absolu hors
Windows (les règles Windows — lettre de lecteur ou UNC — restent celles de Windows). Le fichier de clé SSH suit la
même règle. Avec un mot de passe, ssh lit le secret par un askpass en script shell 0700 au lieu du askpass.cmd.

Sous Windows, ce banc SIMULE Linux (`_chemins_posix`) ; l'exécution réelle du script askpass ne tourne que sous
Linux (job bancs-linux de .github/workflows/image-vps.yml).
Run (depuis backend/) : & $PY tests/test_emplacements_linux_t533.py
"""
import os, pathlib, subprocess, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzempl533_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp / "data")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest  # noqa: E402
from loguru import logger  # noqa: E402
logger.remove()
from app.services import emplacements as E  # noqa: E402


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(E, "_chemins_posix", lambda: True)


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(E, "_chemins_posix", lambda: False)


@pytest.mark.parametrize("brut,attendu", [("/depot", "/depot"), ("/srv/deepotus/depot/", "/srv/deepotus/depot"),
                                          (' "/mnt/nas/rendus" ', "/mnt/nas/rendus"), ("/a//b/./c", "/a/b/c")])
def test_dossier_posix_accepte(linux, brut, attendu):
    assert E.verifier_dossier(brut) == attendu


@pytest.mark.parametrize("brut", ["depot", "./depot", "C:\\Rendus", "\\\\NAS\\partage", "/a/../etc", "/a\\b", "",
                                  "/" + "x" * 401, "/a\nb"])
def test_dossier_posix_refuse(linux, brut):
    with pytest.raises(ValueError):
        E.verifier_dossier(brut)


@pytest.mark.parametrize("brut", ["/srv/deepotus/data", "/srv/deepotus/data/images", "/srv/deepotus", "/"])
def test_dossier_posix_hors_des_donnees(linux, monkeypatch, brut):
    monkeypatch.setattr(E, "DATA_ROOT", pathlib.Path("/srv/deepotus/data"))
    with pytest.raises(ValueError):
        E.verifier_dossier(brut)


def test_windows_inchange(windows):
    assert E.verifier_dossier("Z:\\Rendus") == "Z:\\Rendus"
    with pytest.raises(ValueError):
        E.verifier_dossier("/depot")


def test_cle_ssh_posix(linux):
    c = {"hote": "studio.deepotus.tech", "port": 2222, "utilisateur": "depot", "dossier_distant": "/upload"}
    assert E._sftp_champs({**c, "cle_ssh": "/home/deepotus/.ssh/id_ed25519"})["cle_ssh"] == "/home/deepotus/.ssh/id_ed25519"
    with pytest.raises(ValueError):
        E._sftp_champs({**c, "cle_ssh": "id_ed25519"})


def test_cle_ssh_windows_inchangee(windows):
    c = {"hote": "studio.deepotus.tech", "port": 2222, "utilisateur": "depot", "dossier_distant": "/upload"}
    assert E._sftp_champs({**c, "cle_ssh": "C:\\Users\\o\\.ssh\\depot"})["cle_ssh"] == "C:\\Users\\o\\.ssh\\depot"
    with pytest.raises(ValueError):
        E._sftp_champs({**c, "cle_ssh": "/home/o/.ssh/depot"})


def test_creer_un_emplacement_depot(linux):
    v = E.creer({"nom": "Dépôt du PC", "type": "dossier", "chemin": "/depot", "roles": ["bibliotheque"]})
    assert v["type"] == "dossier" and v["roles"] == ["bibliotheque"]
    assert E.obtenir(v["id"])["chemin"] == "/depot"
    E.supprimer(v["id"])


def test_askpass_shell_hors_windows(linux, tmp_path):
    f = E._askpass(tmp_path)
    assert f.name == "askpass.sh"
    txt = f.read_text(encoding="ascii")
    assert txt.startswith("#!/bin/sh\n") and "\r" not in txt
    assert "DZC_ASKPASS" in txt and "secret" not in txt
    if os.name == "posix":
        assert (f.stat().st_mode & 0o777) == 0o700
        r = subprocess.run([str(f)], env={"DZC_ASKPASS": "mot de passe $(pas évalué) ; `non`"}, capture_output=True,
                           text=True)
        assert r.stdout == "mot de passe $(pas évalué) ; `non`\n"


def test_askpass_cmd_sous_windows(windows, tmp_path):
    assert E._askpass(tmp_path).name == "askpass.cmd"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
