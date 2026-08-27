# -*- coding: utf-8 -*-
# scripts/patch_bundle_vectorlab.py
"""Patcher assert-garde : categorie « Vectorlab » au rail de navigation.

BASELINE : bundle POST-patch episodes_style (dernier maillon en date).
Backup dedie : `.js.bak_vectorlab` (etat juste avant CE patch).
Position dans la chaine : EN QUEUE, apres tout le reste.
Spec : docs/superpowers/plans/2026-08-27-vectorlab-menu-general-pont-cartes.md
(decisions D1/D2/D7) ; l'icone est documentee en DESIGN.md §15-bis.

Trois sections chirurgicales :
  V1  l'icone `vectorpen` (courbe de Bezier + ancres 45° + poignees, style
      §15-2 : masses pleines currentColor, sujet 1 / support .32) inseree
      dans la carte d'icones devant `gamegrid:` — le meme geste que
      patch_bundle_dzdesign.py pour gamegrid.
  V2  l'entree de navigation `vectorlab` dans le tableau Uu, AVANT
      Settings (libelle « Vectorlab », badge new).
  V3  la branche de vue : `s==="vectorlab"` rend une iframe `/vectorlab/`
      absolue qui remplit le conteneur des vues — la surface servie par
      main.py (bibliotheque sans ?doc).

Mecanique identique a patch_bundle_cardforge.py : restauration du .bak
dedie puis re-application, chaque ancre devant apparaitre EXACTEMENT une
fois, sinon abandon sans rien ecrire ; garde de chaine aval ; sanity de
double application ; parite de deltas ; sondes de stabilite a comptes
ATTENDUS (les patchs amont restent intacts) ; verification post-ecriture
sinon restauration.

DANGERS (chacun a deja coute une regression dans ce depot) :
  * NE JAMAIS lancer `repatch_all.py --from ...` sur cette chaine :
    `.bak_subs` et `.bak_vfxrack` ont le meme mtime a la microseconde ET le
    meme sha1, `--list` les sort dans l'ordre inverse du reel. Ce patcher se
    lance SEUL.
  * Le bundle est en CRLF. Tout est lu et ecrit avec `newline=""` : aucune
    traduction de fin de ligne, quelle que soit la plateforme.
  * Ne jamais `print` une ancre : la console Windows est en cp1252 et le
    bundle porte des caracteres hors page de code.

Run :
    python scripts/patch_bundle_vectorlab.py              # depot
    python scripts/patch_bundle_vectorlab.py --root <dir> # app installee
    python scripts/patch_bundle_vectorlab.py --check      # n'ecrit rien

`--force-unchained` est accepte : il saute la garde de chaine aval
(comportement copie de cardforge). Comme `vectorlab` est le maillon de
queue, cette garde ne se declenche jamais en pratique.
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "vectorlab"

# Marqueur de double application : present <=> le patch est deja pose.
MARKER = 'src:"/vectorlab/"'

# Sondes de stabilite verifiees apres coup : (nom, sonde, compte attendu).
# navrail pose dz_nav_collapsed deux fois (init + persist), dzdesign pose
# __dzCatBar deux fois (getElementById + st.id) — des comptes MESURES.
STABLE_PROBES = [
    ("screen-switch", 's==="assets3d"&&r.jsx(DzGameAssetsHub,{variant:e})', 1),
    ("cardforge-pane", 'src:"/cardforge/"', 1),
    ("navrail", "dz_nav_collapsed", 2),
    ("dzdesign", "__dzCatBar", 2),
    ("gamegrid-icon", 'gamegrid:r.jsxs("g",{fill:"currentColor",children:[', 1),
]

# Deltas annonces par la spec (expansion D7). Recalcules depuis PATCHES au
# demarrage : une divergence = faute de frappe dans un remplacement -> abort.
SPEC_CHAR_DELTA = 819
SPEC_BYTE_DELTA = 820

# L'icone D2 — grille 24, masses pleines currentColor, sujet 1 / support .32,
# props React camelCase, le glyphe porte sa couleur (patron ICONS dzdesign).
VECTORPEN = (
    'vectorpen:r.jsxs("g",{fill:"currentColor",children:['
    'r.jsx("rect",{x:"1.7",y:"7.8",width:"14",height:"1.7",rx:".85",'
    'transform:"rotate(-45 8.7 8.7)",opacity:".32"}),'
    'r.jsx("circle",{cx:"13.6",cy:"3.7",r:"2",opacity:".32"}),'
    'r.jsx("circle",{cx:"3.7",cy:"13.6",r:"2",opacity:".32"}),'
    'r.jsx("path",{d:"M4.1 18.6 C4.1 9 9 4.1 18.6 4.1 L18.6 6.7 '
    'C10.4 6.7 6.7 10.4 6.7 18.6 z"}),'
    'r.jsx("rect",{x:"3.4",y:"16.6",width:"4",height:"4",'
    'transform:"rotate(45 5.4 18.6)"}),'
    'r.jsx("rect",{x:"16.6",y:"3.4",width:"4",height:"4",'
    'transform:"rotate(45 18.6 5.4)"})]}),'
)

NAV_ENTRY = (
    '{id:"vectorlab",label:"Vectorlab",icon:"vectorpen",'
    'desc:"Éditeur vectoriel & vitrail",new:!0},'
)

VIEW_BRANCH = (
    's==="vectorlab"&&r.jsx("iframe",{src:"/vectorlab/",title:"Vectorlab",'
    'style:{position:"absolute",inset:0,width:"100%",height:"100%",'
    'border:"0",background:"var(--bg-base)"}},"pvlab"),'
)

_A_ICON = 'gamegrid:r.jsxs("g",{fill:"currentColor",children:['
_A_NAV = '{id:"settings",label:"Settings",icon:"cog",desc:"Keys, paths, persona"}'
_A_VIEW = 's==="assets3d"&&r.jsx(DzGameAssetsHub,{variant:e}),'

# (nom de section, ancre, remplacement) — chaque ancre doit etre unique.
PATCHES = [
    ("V1-icone", _A_ICON, VECTORPEN + _A_ICON),
    ("V2-nav", _A_NAV, NAV_ENTRY + _A_NAV),
    ("V3-vue", _A_VIEW, _A_VIEW + VIEW_BRANCH),
]


def deltas():
    """(delta caracteres, delta octets) recalcules depuis PATCHES."""
    dc = sum(len(r) - len(a) for _t, a, r in PATCHES)
    db = sum(len(r.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, r in PATCHES)
    return dc, db


def check_spec_parity():
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(
            f"[{TAG}] parite spec rompue : delta calcule {dc} car / {db} o, "
            f"spec {SPEC_CHAR_DELTA} car / {SPEC_BYTE_DELTA} o. "
            "Un remplacement a change. Aborting.")
    return dc, db


def guard_downstream(bak):
    """Refuse de tourner si un patcher AVAL est deja passe (cf. repatch_all)."""
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name} (plus "
                f"recent que {bak.name}). vectorlab doit rester le DERNIER "
                "maillon ; ne pas utiliser repatch_all sur cette chaine "
                "(mtimes ex aequo vfxrack/subs).")


def ensure_tail_order(bak):
    """`shutil.copy2` conserve le mtime de la SOURCE : le .bak_vectorlab
    pourrait ne pas sortir en dernier de `repatch_all --list`. On force son
    mtime au-dela de tous les autres .bak."""
    stem = bak.name.rsplit(".bak_", 1)[0]
    others = [p.stat().st_mtime for p in bak.parent.glob(stem + ".bak_*")
              if p != bak]
    if not others:
        return False
    top = max(others)
    if bak.stat().st_mtime > top:
        return False
    t = max(time.time(), top + 1.0)
    os.utime(bak, (t, t))
    return True


def apply(s, anchor, replacement, tag):
    """Remplacement assert-garde : l'ancre doit exister exactement une fois."""
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_src(p):
    """Lecture fidele : newline='' -> aucune traduction de fin de ligne."""
    return p.read_text(encoding="utf-8", newline="")


def eol_stats(data):
    """(crlf, lf isole, cr isole) sur des octets."""
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


def resolve_root(args):
    if "--root" in args:
        return pathlib.Path(args[args.index("--root") + 1]).resolve()
    here = pathlib.Path(".").resolve()
    if (here / REL_BUNDLE).is_file():
        return here
    return pathlib.Path(__file__).resolve().parent.parent


def main():
    args = sys.argv[1:]
    check = "--check" in args
    dc, db = check_spec_parity()

    root = resolve_root(args)
    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)

    if "--force-unchained" not in args:
        guard_downstream(bak)

    if check:
        src = bak if bak.exists() else bundle
        s = read_src(src)
        nm = s.count(MARKER)
        if nm:
            deja = " (et aucun .bak_vectorlab ici)" if not bak.exists() else ""
            raise SystemExit(
                f"[{TAG}] sanity : marqueur vectorlab deja present x{nm} dans "
                f"{src.name}{deja} — double application refusee.\n"
                f"[{TAG}] Si cette racine est l'APP INSTALLEE : c'est normal "
                "et c'est voulu. On ne patche pas l'app, on y COPIE le bundle "
                "deja patche du depot. Patcher ici a nouveau appliquerait le "
                "patch deux fois.")
        for tag, anchor, _repl in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(
                    f"[{tag}] anchor count={n} (want 1) dans {src.name}. "
                    "Aborting.")
        for name, probe, want in STABLE_PROBES:
            n = s.count(probe)
            if n != want:
                raise SystemExit(
                    f"[sonde {name}] count={n} (want {want}) dans {src.name}. "
                    "Aborting.")
        raw = src.read_bytes()
        crlf, lf, cr = eol_stats(raw)
        print(f"[{TAG}] applicable sur {src}")
        print(f"[{TAG}] {len(PATCHES)} ancres OK (1 occurrence chacune), "
              f"marqueur absent, {len(STABLE_PROBES)} sondes aux comptes")
        print(f"[{TAG}] fins de ligne : CRLF={crlf} LF-isole={lf} "
              f"CR-isole={cr}")
        print(f"[{TAG}] delta attendu : +{dc} car / +{db} o")
        return

    if not bak.exists():
        # Sanity AVANT le backup : un bundle deja patche empoisonnerait le
        # .bak_vectorlab (qui deviendrait un point de chaine post-patch).
        if MARKER in read_src(bundle):
            raise SystemExit(
                f"[{TAG}] sanity : marqueur vectorlab deja present dans le "
                f"bundle alors que {bak.name} n'existe pas (patch pose a la "
                "main, ou backup perdu). Etat ambigu : abandon sans rien "
                "ecrire, aucun backup cree.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine (piege copy2)")
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)

    before = bundle.read_bytes()
    crlf0, lf0, cr0 = eol_stats(before)
    if lf0 or cr0:
        raise SystemExit(
            f"[{TAG}] fins de ligne non homogenes AVANT patch "
            f"(CRLF={crlf0} LF-isole={lf0} CR-isole={cr0}). Aborting.")

    s = read_src(bundle)
    chars0 = len(s)
    if MARKER in s:
        raise SystemExit(
            f"[{TAG}] sanity : marqueur vectorlab deja present apres restore "
            f"depuis {bak.name} (backup empoisonne = pris APRES un patch). "
            "Aborting.")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)

    with open(bundle, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)

    # --- verification post-ecriture, sinon on restaure ---------------------
    after = bundle.read_bytes()
    crlf1, lf1, cr1 = eol_stats(after)
    problems = []
    if (crlf1, lf1, cr1) != (crlf0, 0, 0):
        problems.append(
            f"fins de ligne changees : CRLF {crlf0}->{crlf1}, "
            f"LF-isole {lf0}->{lf1}, CR-isole {cr0}->{cr1}")
    if len(after) != len(before) + db:
        problems.append(
            f"taille {len(after)} o, attendu {len(before) + db} o")
    if len(s) != chars0 + dc:
        problems.append(
            f"caracteres {len(s)}, attendu {chars0 + dc}")
    if s.count(MARKER) != 1:
        problems.append(f"marqueur vectorlab x{s.count(MARKER)} (want 1)")
    for tag, anchor, _r in PATCHES:
        if s.count(anchor) != 0 and anchor not in (_A_ICON, _A_NAV, _A_VIEW):
            problems.append(f"{tag} : ancre encore presente")
    # les remplacements CONSERVENT les ancres (insertion avant/apres) :
    # chacune doit rester a exactement 1
    for tag, anchor in (("V1", _A_ICON), ("V2", _A_NAV), ("V3", _A_VIEW)):
        if s.count(anchor) != 1:
            problems.append(f"{tag} : ancre x{s.count(anchor)} (want 1)")
    if s.count("vectorpen:r.jsxs") != 1:
        problems.append("icone vectorpen absente ou dupliquee")
    if s.count('id:"vectorlab"') != 1:
        problems.append("entree nav vectorlab absente ou dupliquee")
    for name, probe, want in STABLE_PROBES:
        if s.count(probe) != want:
            problems.append(f"sonde {name} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))

    print("OK - bundle patche (categorie Vectorlab au rail : icone vectorpen, "
          "entree nav, vue iframe /vectorlab/).")
    print(f"   taille  : {len(before)} -> {len(after)} o (+{db})")
    print(f"   car     : {chars0} -> {len(s)} (newline='', +{dc})")
    print(f"   CRLF    : {crlf0} -> {crlf1} (LF isole {lf1}, CR isole {cr1})")
    print(f"   sondes  : {len(STABLE_PROBES)} aux comptes, "
          f"{len(PATCHES)} sections posees, marqueur x1")
    print("   suite   : copie .mjs + node --check, puis deployer bundle ET "
          "theme-v2.css ET dist/shared/deepotus.tokens.css")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
