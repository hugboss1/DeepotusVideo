# scripts/patch_bundle_asset3d_h31.py
"""Assert-guarded patcher : Tripo H3.1 dans Game Assets 3D (29/08/2026).

BASELINE : bundle POST-patch libsend (dernier patch en date).
Backup dédié : .js.bak_asset3dh31 (état juste avant CE patch).

Pourquoi un patch et pas une liste dynamique : l'écran Game Assets 3D câble
ses moteurs en dur (`var ENG=[...]`) et leur tarif en dur (`var RATES={...}`),
contrairement aux sélecteurs vidéo/image qui lisent /api/video-models et
/api/image-models. Rendre CETTE liste dynamique demande de réécrire l'état
d'un composant React minifié — chantier à part, à faire avec l'app sous les
yeux. Ici on AJOUTE une entrée aux deux littéraux : deux ancres uniques,
aucune logique touchée, vérifiable par chaîne.

Le nom : la spec Magnific parle de « Tripo v3.1 ». Cet endpoint n'existe pas
sur fal (tripo3d/tripo/v3.1 → 404) ; la génération correspondante y est
publiée sous h3.1. Le registre backend (asset3d_service.ENGINES) reste la
seule vérité des capacités — ce patch ne fait qu'offrir le choix à l'écran.

Tarif affiché : 0,20 $ sans texture / 0,30 $ avec (page fal du 29/08/2026).
L'écran n'a pas de champ « qualité », il reste donc en texture standard ;
le palier HD (0,40 $) et les suppléments (géométrie détaillée +0,20 $,
quad +0,05 $) passent par l'API, jamais d'office.

Run: python scripts/patch_bundle_asset3d_h31.py
"""
import pathlib
import shutil
import sys

# Sortie UTF-8 forcée : lu en sous-processus, stdout retombe sinon sur cp1252
# sous Windows et un simple « → » fait échouer le patch APRÈS l'écriture du
# backup — leçon des outils qa/ du dépôt.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_asset3dh31")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ── 1. le sélecteur de moteur ────────────────────────────────────────────────
# Ancre volontairement COURTE et sans tiret typographique : les libellés
# voisins mélangent — et – , qu'un copier-coller abîme silencieusement.
ANCRE_ENG = '{value:"hunyuan",label:'
ENTREE_H31 = (
    '{value:"tripo-h3.1",label:"Tripo H3.1 — face budget + quad topology '
    '(~$0.30)"},'
)

# ── 2. la pastille de coût ───────────────────────────────────────────────────
ANCRE_RATES = 'var RATES={tripo:p.textures?.3:.2,'
RATES_H31 = 'var RATES={tripo:p.textures?.3:.2,"tripo-h3.1":p.textures?.3:.2,'


def main():
    if not BUNDLE.is_file():
        raise SystemExit(f"bundle introuvable : {BUNDLE}")
    src = BUNDLE.read_text(encoding="utf-8")

    if '"tripo-h3.1"' in src:
        print("déjà appliqué (tripo-h3.1 présent) — rien à faire.")
        return

    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print(f"backup → {BAK.name}")

    out = apply(src, ANCRE_ENG, ENTREE_H31 + ANCRE_ENG, "ENG")
    out = apply(out, ANCRE_RATES, RATES_H31, "RATES")

    # vérifications de sortie : ce que le patch PROMET doit être vrai
    assert out.count('{value:"tripo-h3.1"') == 1, "entrée ENG absente"
    assert out.count('"tripo-h3.1":p.textures') == 1, "tarif absent"
    assert len(out) > len(src), "le bundle n'a pas grandi"

    BUNDLE.write_text(out, encoding="utf-8")
    print(f"OK — Tripo H3.1 ajouté au sélecteur et au tarif "
          f"(+{len(out) - len(src)} octets)")


if __name__ == "__main__":
    main()
