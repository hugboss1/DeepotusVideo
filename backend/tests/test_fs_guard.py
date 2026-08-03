# -*- coding: utf-8 -*-
"""Test de non-régression du garde MSIX (fs_guard) — script autonome.

Lancer avec le python embarqué de l'app installée :
  C:\\Users\\olivi\\AppData\\Local\\DeepotusVideoGen\\runtime\\python\\python.exe
      backend\\tests\\test_fs_guard.py

Vérifie :
  1. probe_write_visibility → True dans un environnement normal (les
     écritures apparaissent dans l'énumération) et ne laisse aucun canari.
  2. startup_check mémorise le résultat et is_virtualized() le reflète.
  3. Un dossier dont l'énumération « ment » (simulation d'overlay MSIX par
     monkeypatch de iterdir) est bien détecté virtualisé.
  4. Un échec d'écriture (dossier fichier) est traité « visible » (pas de
     faux positif MSIX sur simple erreur disque).
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import fs_guard  # noqa: E402

FAILURES = []


def check(name, cond):
    tag = "OK " if cond else "FAIL"
    print(f"[{tag}] {name}")
    if not cond:
        FAILURES.append(name)


with tempfile.TemporaryDirectory() as td:
    d = Path(td) / "images"

    # 1. Environnement normal : visible, et pas de canari résiduel.
    check("probe normale -> visible", fs_guard.probe_write_visibility(d) is True)
    leftovers = list(d.glob(".dz_fsguard_*"))
    check("aucun canari résiduel", leftovers == [])

    # 2. startup_check + is_virtualized cohérents.
    virt = fs_guard.startup_check(d)
    check("startup_check normal -> non virtualisé", virt is False)
    check("is_virtualized() == False", fs_guard.is_virtualized() is False)

    # 3. Simulation d'overlay : l'énumération ne montre pas le canari.
    real_iterdir = Path.iterdir

    def lying_iterdir(self):
        return iter([p for p in real_iterdir(self)
                     if ".dz_fsguard_" not in p.name])

    Path.iterdir = lying_iterdir
    try:
        check("probe overlay simulé -> invisible",
              fs_guard.probe_write_visibility(d) is False)
        check("startup_check overlay -> virtualisé",
              fs_guard.startup_check(d) is True)
        check("is_virtualized() == True", fs_guard.is_virtualized() is True)
    finally:
        Path.iterdir = real_iterdir

    # 4. Écriture impossible (le « dossier » est un fichier) -> visible.
    f = Path(td) / "notadir"
    f.write_text("x", encoding="utf-8")
    check("échec d'écriture -> traité visible",
          fs_guard.probe_write_visibility(f) is True)

print()
if FAILURES:
    print(f"ÉCHECS: {len(FAILURES)} -> {FAILURES}")
    sys.exit(1)
print("test_fs_guard: 8/8 OK")
