"""scripts/restaurer_bak_montage.py — le .bak_montage (gitignoré, perdu partout) reconstitué depuis l'histoire.

Ce qu'on vérifie, par les OCTETS et non par le message du script :
  - le fichier est écrit à côté du bundle d'une racine donnée, avec l'empreinte que le patcher déclare, et AUCUN
    autre fichier `.bak_*` (la garde de chaîne et repatch_all prennent tout `.bak_*` pour un maillon) ;
  - c'est le bon : les témoins que les bancs ont relevés sur le vrai .bak (482 useState + l'état `lots` de #19,
    le corps du payload SANS garde `c.src&&c.src.job_id`, aucun bloc montage) ;
  - le patcher montage ACTUEL y trouve chacune de ses ancres exactement une fois ;
  - rejouer montage (version du commit source) sur le fichier redonne le bundle de ce commit octet pour octet ;
  - sa date de modification est celle du commit source (la garde de chaîne des patchers ordonne par mtime) ;
  - il refuse d'écraser un .bak_montage qui n'est PAS une reconstruction ;
  - sur la reconstruction, patch_bundle_montage.py REFUSE d'appliquer et de retirer (il restaurerait l'état du 04/10 et
    effacerait sans un mot ce que refresh_layer et les maillons aval ont écrit depuis) ; --check reste permis.

Run: python tests/test_restaurer_bak_montage.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT = RACINE / "scripts" / "restaurer_bak_montage.py"
PATCHER = RACINE / "scripts" / "patch_bundle_montage.py"
REL = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
PY = sys.executable
_ETAT = {}


def _lancer(*args, cwd=None):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([PY, *map(str, args)], cwd=str(cwd or RACINE), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=600)


def _racine_temp():
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzbakm_"))
    (d / REL.parent).mkdir(parents=True)
    shutil.copy2(RACINE / REL, d / REL)
    shutil.copy2(RACINE / "frontend/dist/index.html", d / "frontend/dist/index.html")
    return d


def _restaure():
    if "d" not in _ETAT:
        d = _racine_temp()
        r = _lancer(SCRIPT, "--root", d, "--repo", RACINE)
        _ETAT.update(d=d, r=r)
    return _ETAT["d"], _ETAT["r"]


def test_le_fichier_est_ecrit_avec_l_empreinte_declaree_et_seul():
    import hashlib
    import importlib.util
    d, r = _restaure()
    assert r.returncode == 0, r.stdout + r.stderr
    bak = d / (str(REL) + ".bak_montage")
    assert bak.is_file() and bak.stat().st_size > 1_000_000
    spec = importlib.util.spec_from_file_location("pm_sha", PATCHER)
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    assert hashlib.sha256(bak.read_bytes()).hexdigest() == pm.BAK_RECONSTRUIT_SHA256
    assert sorted(p.name for p in (d / REL.parent).glob(REL.name + ".bak_*")) == [REL.name + ".bak_montage"]


def test_les_temoins_du_vrai_bak_sont_la():
    d, _ = _restaure()
    s = (d / (str(REL) + ".bak_montage")).read_bytes().decode("utf-8-sig")
    assert s.count("x.useState({ journaux: false, rebuts: false })") == 1      # l'état `lots` de #19
    assert s.count("x.useState(") == 483                                       # 482 + lots (test_montage_bundle L7d0)
    assert "/*__DZ_MONTAGE_BEGIN__*/" not in s                                 # aucun bloc montage
    i = s.find("clips.filter(function(c){return c.src})")
    j = s.find("return o})", i)
    corps = s[i:j]
    assert len(corps) > 1500 and corps.count("c.src.job_id") == 1 and corps.count("c.src&&c.src.job_id") == 0


def test_le_patcher_actuel_trouve_chaque_ancre_une_fois():
    import importlib.util
    d, _ = _restaure()
    spec = importlib.util.spec_from_file_location("pm_actuel", PATCHER)
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    s = (d / (str(REL) + ".bak_montage")).read_bytes().decode("utf-8-sig")
    crlf = "\r\n" in s
    assert s.count(pm.ANCHOR_INJECT) == 1
    hors = [t for t, a, _r in pm.PATCHES if s.count(pm.nl(a, crlf)) != 1]
    assert hors == [] and len(pm.PATCHES) > 300


def test_l_aller_redonne_le_bundle_du_commit_et_la_date_est_la_sienne():
    d, r = _restaure()
    assert "aller == bundle du commit : True" in r.stdout, r.stdout
    commit = r.stdout.split("commit source : ", 1)[1].split()[0]
    ts = int(subprocess.run(["git", "-C", str(RACINE), "log", "-1", "--format=%ct", commit],
                            capture_output=True, text=True, check=True).stdout.strip())
    assert int((d / (str(REL) + ".bak_montage")).stat().st_mtime) == ts


def test_un_vrai_bak_n_est_jamais_ecrase():
    d = _racine_temp()
    vrai = d / (str(REL) + ".bak_montage")
    vrai.write_bytes(b"un vrai .bak, pas une reconstruction")
    r = _lancer(SCRIPT, "--root", d, "--repo", RACINE)
    assert r.returncode != 0 and "reconstruction" in (r.stdout + r.stderr)
    assert vrai.read_bytes() == b"un vrai .bak, pas une reconstruction"
    # …et sur un AUTRE .bak, la garde du patcher se tait : elle ne vise que la reconstruction
    r = _lancer(PATCHER, "--root", d, "--force-unchained")
    assert "reconstruction" not in (r.stdout + r.stderr), r.stdout + r.stderr


def test_un_commit_trop_recent_est_refuse_par_les_temoins():
    """fd6cfe8a (#214, T101) : refresh_layer a déjà réécrit le bloc SONVFX dans le bundle (+5 useState) — l'inverse
    y laisse 488 useState au lieu de 483. Le script doit le DIRE et ne rien écrire."""
    d = _racine_temp()
    r = _lancer(SCRIPT, "--root", d, "--repo", RACINE, "--commit", "fd6cfe8a")
    assert r.returncode != 0 and "témoins" in (r.stdout + r.stderr) and "useState 488" in (r.stdout + r.stderr), \
        r.stdout + r.stderr
    assert not (d / (str(REL) + ".bak_montage")).exists()


def test_chaque_temoin_refuse_seul():
    import importlib.util
    d, _ = _restaure()
    spec = importlib.util.spec_from_file_location("rbm", SCRIPT)
    rbm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rbm)
    s = (d / (str(REL) + ".bak_montage")).read_bytes().decode("utf-8-sig")
    assert rbm.temoins(s) == []
    assert any("lots" in e for e in rbm.temoins(s.replace(rbm.LOTS, "x.useState({})")))
    assert any("useState" in e for e in rbm.temoins(s + "x.useState("))
    assert any("bloc montage" in e for e in rbm.temoins(s + "/*__DZ_MONTAGE_BEGIN__*/"))
    i = s.find(rbm.PAYLOAD_B)
    garde = s[:i] + s[i:].replace("c.src.job_id", "c.src&&c.src.job_id", 1)
    assert any("payload" in e for e in rbm.temoins(garde))


def _scripts_alteres(alteration):
    """Copie le script et le patcher montage dans une racine temporaire, le patcher ALTÉRÉ ; rend (racine, résultat)."""
    d = _racine_temp()
    (d / "scripts").mkdir()
    shutil.copy2(SCRIPT, d / "scripts" / SCRIPT.name)
    (d / "scripts" / PATCHER.name).write_text(alteration(PATCHER.read_text("utf-8")), encoding="utf-8")
    r = _lancer(d / "scripts" / SCRIPT.name, "--root", d, "--repo", RACINE)
    return d, r


def test_une_empreinte_declaree_fausse_bloque_l_ecriture():
    """Si la reconstruction n'a pas l'empreinte que le patcher reconnaît, sa garde ne la verrait pas : rien n'est écrit."""
    d, r = _scripts_alteres(lambda t: t.replace('BAK_RECONSTRUIT_SHA256 = "', 'BAK_RECONSTRUIT_SHA256 = "0', 1))
    assert r.returncode != 0 and "empreinte" in (r.stdout + r.stderr), r.stdout + r.stderr
    assert not (d / (str(REL) + ".bak_montage")).exists()


def test_une_ancre_du_patcher_actuel_absente_bloque_l_ecriture():
    d, r = _scripts_alteres(lambda t: t + '\nPATCHES = PATCHES + [("ZZ-ancre-absente", "ancre qui n existe nulle part", "x")]\n')
    assert r.returncode != 0 and "ZZ-ancre-absente" in (r.stdout + r.stderr), r.stdout + r.stderr
    assert not (d / (str(REL) + ".bak_montage")).exists()


def test_une_reconstruction_se_refait_sans_force():
    d, _ = _restaure()
    r = _lancer(SCRIPT, "--root", d, "--repo", RACINE)
    assert r.returncode == 0, r.stdout + r.stderr


def test_sur_la_reconstruction_le_patcher_montage_refuse_d_appliquer_et_de_retirer():
    d, _ = _restaure()
    avant = (d / REL).read_bytes()
    for args in ((), ("--force-unchained",), ("--strip",)):
        r = _lancer(PATCHER, "--root", d, *args)
        assert r.returncode != 0, (args, r.stdout)
        assert "reconstruction" in (r.stdout + r.stderr), (args, r.stdout + r.stderr)
    assert (d / REL).read_bytes() == avant                                   # le bundle n'a pas bougé
    r = _lancer(PATCHER, "--root", d, "--check")
    assert r.returncode == 0 and "applicable" in r.stdout, r.stdout + r.stderr


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
