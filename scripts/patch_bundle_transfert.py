# -*- coding: utf-8 -*-
# scripts/patch_bundle_transfert.py
"""Patcher assert-gardé : « Transfert entre machines » dans les Réglages.

BASELINE : bundle POST-patch version (queue de chaîne au 07/09/2026).
Backup dédié : .js.bak_transfert (état juste avant CE patch).

Demande de l'utilisateur (07/09/2026) : un bouton du menu principal qui
lance l'export de tout ce que l'application a créé vers une autre machine,
un autre qui l'importe, « sur la même catégorie », avec un modal
d'avancement conforme aux design.md. « La même catégorie » a été mesurée :
les Réglages portent une liste de catégories `[{k,l}, …]` et un rendu
conditionnel `s==="<k>" && r.jsx(<Composant>,{})` — c'est là que la
fonctionnalité appartient, et c'est le motif qu'emploie déjà `DzPricing`.

TROIS sections :
  T1  injection de la couche `frontend/patches/transfert.js` (le composant
      `DzTransfert`, une déclaration de fonction : la remontée de portée la
      rend visible du rendu des Réglages, qui vit plus haut dans le module) ;
  T2  la catégorie `{k:"transfert",l:"Transfert entre machines"}`, ajoutée
      APRÈS `Pricing & budget` — la dernière de la liste ;
  T3  le rendu conditionnel de la section, à la suite de celui de
      `DzPricing`.

La couche ne cite AUCUNE ancre de ce patcher : le banc le vérifie.

Run : python scripts/patch_bundle_transfert.py [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
COUCHE = pathlib.Path("frontend/patches/transfert.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_transfert")
TAG = "transfert"

BEGIN = "/*__DZ_TRANSFERT_BEGIN__*/"
END = "/*__DZ_TRANSFERT_END__*/"

# T1 — la couche s'injecte juste après le bloc Montage : `x` (React) et `r`
# (le runtime JSX) y sont en portée, et le bloc est en fin de module.
ANCHOR_INJECT = "/*__DZ_MONTAGE_END__*/"

# T2 — la liste des catégories des Réglages. Mesuré : une seule occurrence.
A_T2 = '{k:"appearance",l:"Appearance"},{k:"pricing",l:"Pricing & budget"}]'
R_T2 = ('{k:"appearance",l:"Appearance"},{k:"pricing",l:"Pricing & budget"},'
        '{k:"transfert",l:"Transfert entre machines"}]')

# T3 — le rendu conditionnel, à la suite de celui de la tarification.
A_T3 = 's==="pricing"&&r.jsx(DzPricing,{})]'
R_T3 = ('s==="pricing"&&r.jsx(DzPricing,{}),'
        's==="transfert"&&r.jsx(DzTransfert,{})]')

PATCHES = [
    ("T2-categorie", A_T2, R_T2),
    ("T3-section", A_T3, R_T3),
]


def lire(p):
    """Le mode texte MENT sur les fins de ligne : `read_text` replie tout
    CRLF en LF (universal newlines), et le test `crlf` rendait alors False
    sur un bundle pourtant en CRLF — la reecriture aplatissait 17 204 CRLF
    en LF et cassait les bancs qui decoupent le bundle sur une ligne vide
    (mesure du 07/09/2026). On lit et on ecrit en OCTETS."""
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def nl(text, crlf):
    """Le bundle mêle du minifié (sans saut de ligne) et des blocs injectés
    en CRLF : une ancre multi-ligne doit être convertie, sinon elle ne
    matche jamais. Ici les ancres tiennent sur une ligne, mais la couche
    injectée, elle, en porte des centaines."""
    return text.replace("\n", "\r\n") if crlf else text


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def guard_downstream(bak):
    """Refuse de tourner si un maillon AVAL est déjà passé : le relancer
    seul remettrait le bundle à l'état d'avant lui et EFFACERAIT en silence
    ce que les suivants ont écrit (mémoire du dépôt, 05/09/2026)."""
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in sorted(bak.parent.glob(stem + ".bak_*")):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name} (plus "
                f"recent que {bak.name}). Le relancer seul effacerait ce que "
                f"les maillons suivants ont ecrit. Utilise "
                f"`python scripts/repatch_all.py --from {TAG}`.")


def main():
    args = sys.argv[1:]
    if "--force-unchained" not in args:
        guard_downstream(BAK)
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)
    crlf = "\r\n" in s
    # la couche est ramenee en LF puis reconvertie par `nl` : elle doit
    # epouser les fins de ligne du bundle, pas celles de son fichier.
    couche = COUCHE.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")

    if "--check" in args:
        for tag, a, _ in PATCHES:
            n = s.count(nl(a, crlf))
            if n != 1:
                raise SystemExit(f"[{tag}] anchor count={n} (want 1) dans "
                                 f"{src.name}. Aborting.")
        if s.count(nl(ANCHOR_INJECT, crlf)) != 1:
            raise SystemExit("[T1] ancre d'injection absente ou multiple.")
        print(f"[{TAG}] applicable sur {src.name} "
              f"({len(PATCHES) + 1} ancres OK)")
        return

    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK.name)
    else:
        shutil.copy2(BAK, BUNDLE)
        s, bom = lire(BUNDLE)
        crlf = "\r\n" in s

    injection = nl("\n" + couche.strip() + "\n", crlf)
    s = apply(s, nl(ANCHOR_INJECT, crlf),
              nl(ANCHOR_INJECT, crlf) + injection, "T1-inject")
    for tag, a, rp in PATCHES:
        s = apply(s, nl(a, crlf), nl(rp, crlf), tag)
    ecrire(BUNDLE, s, bom)
    print(f"OK — {TAG} applique ({BUNDLE.stat().st_size} o).")


if __name__ == "__main__":
    main()
