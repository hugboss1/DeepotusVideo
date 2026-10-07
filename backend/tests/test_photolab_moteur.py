# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — le pont vers photocraft-cli, sans le vrai binaire.
  [1] chemins : binaire épinglé, dossier de travail unique, chemins relatifs sûrs (même règle que le moteur).
  [2] la session : protocole JSON lignes avec un FAUX moteur (tests/faux_photocraft.py).
  [3] les commandes refusées : rien qui écrive ou lise hors du dossier de travail.
Run : & $PY tests/test_photolab_moteur.py   (depuis backend/)"""
import os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt136_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.pop("PHOTOCRAFT_CLI", None)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


print("\n[1] chemins")
d = PM.dossier_travail()
check("1a dossier de travail = <données>/photolab, sous-dossiers entrees, rendus, exports",
      d == _tmp / "photolab" and all((d / s).is_dir() for s in ("entrees", "rendus", "exports")), d)
for bon in ("entrees/a.png", "rendus/apercu.png", "exports/Mon-fichier_2.psd"):
    check(f"1b relatif accepte {bon}", PM.relatif(bon) == bon)
for mauvais in ("../x.png", "entrees/../../x", "C:/x.png", "/etc/x", "entrees\\a.png", "", "entrees//a.png", "./a.png",
                "a b.png", None, "rendus/CON.png", "entrees/nul", "rendus/a.", "entrées/a.png", "a" * 201,
                "exports/COM1", "rendus/lpt9.txt"):
    try:
        PM.relatif(mauvais)
        passe = True
    except ValueError:
        passe = False
    check(f"1c relatif refuse {mauvais!r}", not passe)
faux = _tmp / "outil" / "photocraft-cli.exe"
faux.parent.mkdir()
faux.write_bytes(b"MZ")
os.environ["PHOTOCRAFT_CLI"] = str(faux)
check("1d PHOTOCRAFT_CLI désigne le binaire (bancs, installations particulières)", PM.chemin_cli() == faux, PM.chemin_cli())
os.environ["PHOTOCRAFT_CLI"] = str(_tmp / "absent.exe")
racine_vide = _tmp / "racine_vide"
racine_vide.mkdir()
RACINE_APP_0 = PM.RACINE_APP                              # restaurée en fin de section : l'état du module ne fuit pas
PM.RACINE_APP = racine_vide
try:
    PM.chemin_cli()
    absent_dit = False
except PM.MoteurAbsent as e:
    absent_dit = "vendor_photocraft.py" in str(e)
check("1e binaire introuvable : MoteurAbsent qui dit comment le fournir", absent_dit)
os.environ.pop("PHOTOCRAFT_CLI")
vend = racine_vide / "vendor" / "photocraft-0.3.0" / "photocraft-0.3.0-windows-x64"
vend.mkdir(parents=True)
(vend / "photocraft-cli.exe").write_bytes(b"MZ")
check("1f sinon : vendor/photocraft-0.3.0/** sous la racine de l'application", PM.chemin_cli() == vend / "photocraft-cli.exe",
      PM.chemin_cli())
PM.RACINE_APP = RACINE_APP_0

print("\n[2] la session (faux moteur)")
import json as _json, time as _time                        # noqa: E402
FAUX = [sys.executable, str(BACKEND / "tests" / "faux_photocraft.py"), "serve",
        "--automation-read-root", str(d), "--automation-write-root", str(d)]
s = PM.SessionMoteur(FAUX, delai_s=2.0)
r = s.appeler("doc.new", {"width": 64, "height": 32})
check("2a démarrage à la première demande, réponse rendue", r == {"document": 0} and s.vivant(), r)
check("2b generation = 1 après le premier démarrage", s.generation == 1, s.generation)
check("2c une ligne non JSON est ignorée", s.appeler("engine.execute", {"command": "dz.bruit"}) == {"ok": True})
check("2d une réponse à un autre id est ignorée, la bonne est rendue",
      s.appeler("engine.execute", {"command": "dz.desordre"}) == {"bon": True})
try:
    s.appeler("engine.execute", {"command": "dz.erreur"})
    err = None
except PM.MoteurErreur as e:
    err = str(e)
check("2e ok:false -> MoteurErreur avec le message du moteur, la session reste vivante",
      err == "no active layer" and s.vivant(), err)
pid1 = s.appeler("engine.execute", {"command": "dz.pid"})["pid"]
t0 = _time.monotonic()
try:
    s.appeler("engine.execute", {"command": "dz.dormir"}, delai_s=0.5)
    delai = False
except PM.MoteurDelai:
    delai = True
check("2f pas de réponse dans le délai -> MoteurDelai, moteur arrêté, sans attendre ses 30 s",
      delai and not s.vivant() and _time.monotonic() - t0 < 2.5, _time.monotonic() - t0)
pid2 = s.appeler("engine.execute", {"command": "dz.pid"})["pid"]
check("2g la demande suivante relance un NOUVEAU moteur (generation 2)", pid2 != pid1 and s.generation == 2, (pid1, pid2))
try:
    s.appeler("engine.execute", {"command": "dz.mourir"})
    mort = False
except PM.MoteurErreur:
    mort = True
check("2h moteur qui meurt pendant une demande -> MoteurErreur, relancé ensuite",
      mort and s.appeler("doc.inspect") == {"documents": []} and s.generation == 3, s.generation)
s.fermer()
check("2i fermer() arrête le moteur", not s.vivant())
PM.FABRIQUE = lambda: PM.SessionMoteur(FAUX, delai_s=2.0)
PM._SESSION = None
check("2j session() rend UNE session (la même à chaque appel)", PM.session() is PM.session())
_vieille = PM.session()
_vieille.appeler("doc.inspect")
check("2k0 etat_session() dit génération et vie de la session courante",
      PM.etat_session() == {"generation": 1, "vivant": True}, PM.etat_session())
PM.fermer()
check("2k fermer() du module arrête et oublie la session", PM._SESSION is None)
check("2k1 etat_session() sans session : génération 0, pas vivante",
      PM.etat_session() == {"generation": 0, "vivant": False}, PM.etat_session())
# Une route encore en vol qui tient l'ancienne session ne doit PAS relancer le moteur après l'arrêt du backend.
try:
    _vieille.appeler("doc.inspect")
    _relance = True
except PM.MoteurAbsent:
    _relance = False
check("2k2 session fermée pour de bon : MoteurAbsent, aucun redémarrage", not _relance and not _vieille.vivant()
      and _vieille.generation == 1, (_relance, _vieille.generation))
PM.FABRIQUE = None                                        # l'état du module ne fuit pas vers les autres sections
PM._SESSION = None

import threading as _th                                    # noqa: E402
s2 = PM.SessionMoteur(FAUX, delai_s=3.0)
res = {}


def _long():
    try:
        s2.appeler("engine.execute", {"command": "dz.dormir"})
    except Exception as e:                                 # noqa: BLE001
        res["t1"] = type(e).__name__


t1 = _th.Thread(target=_long)
t1.start()
_time.sleep(0.4)                                           # t1 tient le verrou et attend la réponse qui ne vient pas
t0 = _time.monotonic()
try:
    s2.appeler("doc.inspect", delai_s=0.5)
    occupe = False
except PM.MoteurOccupe:
    occupe = True
check("2l verrou occupé : MoteurOccupe dans le délai, sans attendre l'autre demande",
      occupe and _time.monotonic() - t0 < 1.5, _time.monotonic() - t0)
t1.join()
check("2m la demande longue finit en MoteurDelai", res.get("t1") == "MoteurDelai", res)
try:
    s2.appeler("engine.execute", {"command": "dz.mourir"})
except PM.MoteurErreur:
    pass
g0 = s2.generation
r, g = s2.appeler_g("doc.inspect")
check("2n appeler_g rend la génération qui a RÉPONDU (relance comprise) = précédente + 1",
      r == {"documents": []} and g == g0 + 1 == s2.generation, (g0, g))
check("2o appeler() = résultat seul", s2.appeler("doc.inspect") == {"documents": []})
s2.fermer()
sa = PM.SessionMoteur([str(_tmp / "absent.exe")])
try:
    sa.appeler("doc.inspect")
    absent = None
except PM.MoteurAbsent as e:
    absent = str(e)
except Exception as e:                                     # noqa: BLE001
    absent = "autre:" + type(e).__name__
check("2p binaire introuvable au lancement -> MoteurAbsent (vendor_photocraft.py), génération inchangée",
      absent is not None and "vendor_photocraft.py" in absent and sa.generation == 0 and not sa.vivant(), (absent, sa.generation))
# Réponse {"id":null,"ok":false} (ligne illisible) : une seule requête à la fois, donc elle est la nôtre -> MoteurErreur
# tout de suite plutôt que d'attendre le délai. Non testée : notre propre écriture est toujours du JSON valide.

print("\n[3] les commandes refusées")
for bon in ("filter.blur.gaussianBlur", "image.adjustments.levels", "layer.new.layer", "edit.fill", "select.all"):
    check(f"3a commande acceptée {bon}", PM.commande_autorisee(bon, {"radius": 3}) == bon)
for mauvais, params in (("file.saveAs", {}), ("file.open", {}), ("file.place.embedded", {}), ("file.scripts.browse", {}),
                        ("automate.droplet", {}), ("plugin.install", {}), ("app.quit", {}), ("FILTER.blur", {}),
                        ("filter..blur", {}), ("filter.blur.gaussianBlur", {"path": "C:/x.png"}),
                        ("image.adjustments.colorLookup", {"lut": {"file": "../x.cube"}}),
                        ("layer.new.layer", {"steps": [{"folder": "x"}]})):
    try:
        PM.commande_autorisee(mauvais, params)
        passe = True
    except ValueError:
        passe = False
    check(f"3b refusée {mauvais} {params}", not passe)
for mauvais, params in (("image.adjustments.colorLookup", {"lut": "../x.cube"}), ("edit.fill", {"Path": "C:/x"}),
                        ("edit.fill", {"filePath": "a"}), ("edit.fill", {"outputPath": "a"}),
                        ("edit.fill", {"src": "/etc/x"}), ("edit.fill", "C:/x.png"), ("edit.fill", ["C:/x.png"]),
                        ("fiLe.open", {}), ("filE.saveAs", {}), ("edit.fill", {"a": {"b": ["x/y.png"]}}),
                        ("edit.fill", {"a": "x\\y"}), ("edit.fill", {"a": "C:x"}), ("edit.fill", {"a": "MOI.PSD"}),
                        ("edit.fill", {"a": "t.cube"}), ("edit.fill", {"out": "a"}), ("edit.fill", {"profile": 1}),
                        ("edit.fill", {"Preset": 1}), ("edit.fill", {"dir": "a"}),
                        # mutation t136 : une clé « path » à valeur anodine doit tomber par la CLÉ seule
                        ("edit.fill", {"path": "abc"})):
    try:
        PM.commande_autorisee(mauvais, params)
        passe = True
    except ValueError:
        passe = False
    check(f"3c refusée (contournement) {mauvais} {params!r}", not passe)
for bon, params in (("filter.blur.gaussianBlur", {"radius": 3}), ("image.adjustments.levels", {"lightness": {"outBlack": 60}}),
                    ("edit.fill", {"color": "#336699"}), ("image.crop", {"ratio": "16:9"}), ("select.all", None),
                    ("image.resize", {"resolution": 72, "direction": "h", "mode": "normal"})):
    check(f"3d acceptée {bon} {params!r}", PM.commande_autorisee(bon, params) == bon)

if __name__ == "__main__":
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1 if fail else 0)
