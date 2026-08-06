# -*- coding: utf-8 -*-
# scripts/patch_bundle_version.py
"""Assert-guarded patcher : bump du libellé de version affiché par l'UI.

BASELINE : bundle POST-patch quickvoice (chantier V-a).
Backup dédié : .js.bak_version (état juste avant CE patch).

Le bundle affiche « v<version> » en dur à 4 endroits (topbars, splash,
badge Settings). La source de vérité runtime reste backend/app/config.py
(/api/health) — ce patcher aligne les libellés statiques du bundle.

ATTENTION — le splash de démarrage vit dans frontend/dist/index.html
(<div class="dz-ver">), PAS dans le bundle : ce patcher ne le touche pas.
Il est resté affiché en v2.0.0 pendant tout le cycle 2.1.0 (audit 06/08).
À chaque bump, l'éditer à la main aussi — étape 1 ci-dessous.

Au prochain bump (le patch version doit TOUJOURS être le dernier maillon) :
  1. éditer OLD/NEW ci-dessous, APP_VERSION dans backend/app/config.py,
     MyAppVersion dans installer/deepotus.iss, le titre de README.md ET le
     <div class="dz-ver"> de frontend/dist/index.html ;
  2. archiver .bak_version HORS de frontend/dist/assets (sinon il reste dans
     la chaîne détectée par repatch_all) ;
  3. relancer : python scripts/patch_bundle_version.py — le backup frais
     capture le bundle courant (post-derniers patchs) et le patch s'applique
     en bout de chaîne. NE PAS utiliser repatch_all --from version pour un
     re-bump : il restaurerait le bak HISTORIQUE (libellés de l'ancienne
     version) et l'assert EXPECT échouerait (constat 22/07, chantier V-a).

Run : python scripts/patch_bundle_version.py
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_version")

OLD = "v2.0.0"
NEW = "v2.1.0"
EXPECT = 4  # occurrences exactes du libellé dans le bundle baseline


def guard_downstream(bak):
    """Refuse de tourner si un patcher AVAL est déjà passé — voir repatch_all.py."""
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval détecté : {other.name}. Utiliser : "
                f"python scripts/repatch_all.py --from "
                f"{bak.name.rsplit('.bak_', 1)[1]}")


def main():
    if "--force-unchained" not in sys.argv:
        guard_downstream(BAK)
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
    s = BUNDLE.read_text(encoding="utf-8")
    n = s.count(OLD)
    if n != EXPECT:
        raise SystemExit(f"[version] occurrences {OLD} = {n} (attendu {EXPECT}). Aborting.")
    s = s.replace(OLD, NEW)
    BUNDLE.write_text(s, encoding="utf-8")
    print(f"OK — bundle patched ({OLD} -> {NEW}, {n} libellés). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
