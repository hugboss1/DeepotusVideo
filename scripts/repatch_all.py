# -*- coding: utf-8 -*-
# scripts/repatch_all.py
"""Rejoue la chaîne des patchers bundle dans l'ordre, à partir d'un tag donné.

Pourquoi : chaque patch_bundle_<tag>.py restaure SON .bak_<tag> puis applique
ses sections. Les .bak forment une chaîne d'états figés (l'ordre = leur mtime,
copy2 préservant le mtime du bundle au moment du backup). Relancer un patcher
AMONT seul écrase donc silencieusement tous les patchs postérieurs (constat
CR chantier 11) — d'où la garde-chaîne dans les patchers, et CE script pour
rejouer proprement.

Mécanique de rechaînage, pour chaque étape à partir de --from <tag> :
  1. étape de départ : son .bak_<tag> historique est conservé (on rejoue la
     nouvelle version du patcher depuis le même état d'avant) ;
  2. étapes AVAL : leur .bak_<tag> est REMPLACÉ par le bundle courant (nouveau
     point de chaîne), puis le patcher est relancé (il restaure ce bak frais
     et ré-applique) — avec --force-unchained pour passer la garde.
Un tag aval sans script patch_bundle_<tag>.py correspondant = abort (chaîne
non rejouable) ; les tags AMONT sans script sont ignorés (leur état vit déjà
dans les .bak suivants).

Usage :
  python scripts/repatch_all.py --from toolbars      # rejoue toolbars puis shellaudit
  python scripts/repatch_all.py --list               # affiche la chaîne détectée
"""
import pathlib
import shutil
import subprocess
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
SCRIPTS = pathlib.Path("scripts")


def chain():
    baks = [p for p in BUNDLE.parent.glob(BUNDLE.name + ".bak_*")]
    baks.sort(key=lambda p: p.stat().st_mtime)
    return [(p.name.rsplit(".bak_", 1)[1], p) for p in baks]


def main():
    steps = chain()
    if "--list" in sys.argv:
        for tag, bak in steps:
            script = SCRIPTS / f"patch_bundle_{tag}.py"
            print(f"{tag:16s} {'OK ' if script.exists() else 'SANS SCRIPT '}"
                  f"(bak {bak.stat().st_size} o)")
        return
    if "--from" not in sys.argv:
        raise SystemExit("Usage: python scripts/repatch_all.py --from <tag> | --list")
    start = sys.argv[sys.argv.index("--from") + 1]
    tags = [t for t, _ in steps]
    if start not in tags:
        raise SystemExit(f"tag inconnu '{start}' — chaîne détectée : {', '.join(tags)}")
    todo = steps[tags.index(start):]
    missing = [t for t, _ in todo if not (SCRIPTS / f"patch_bundle_{t}.py").exists()]
    if missing:
        raise SystemExit(f"chaîne non rejouable, script(s) manquant(s) : {missing}")
    for i, (tag, bak) in enumerate(todo):
        if i > 0:
            shutil.copy2(BUNDLE, bak)
            print(f"[chaîne] {bak.name} := bundle courant ({BUNDLE.stat().st_size} o)")
        script = SCRIPTS / f"patch_bundle_{tag}.py"
        print(f"[chaîne] run {script.name}")
        rc = subprocess.run([sys.executable, str(script), "--force-unchained"]).returncode
        if rc != 0:
            raise SystemExit(f"{script.name} a échoué (rc={rc}) — chaîne interrompue à '{tag}'.")
    print(f"OK — chaîne rejouée depuis '{start}' ({len(todo)} étape(s)).")


if __name__ == "__main__":
    main()
