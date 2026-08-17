# -*- coding: utf-8 -*-
# scripts/patch_bundle_cardforge.py
"""Patcher assert-garde : sous-onglet « Cartes » (Card Forge) du hub Game Assets.

BASELINE : bundle POST-patch `subs` (dernier maillon en date de la chaine).
Backup dedie : `.js.bak_cardforge` (etat juste avant CE patch).
Position dans la chaine : EN QUEUE, apres `subs`.
Spec : docs/superpowers/specs/2026-08-11-cardforge-design.md (§2.6).

Le hub `DzGameAssetsHub` (3D | 3D Studio | Sprites 2D | Tuiles | Matieres)
gagne un onglet de plus : « Cartes » = iframe `/cardforge/`, page standalone
hors bundle. Le relais `deepotus:navigate` -> `deepotus:assets-subtab` accepte
deja n'importe quel `detail.subtab` : on etend seulement l'etat accepte par le
hub (au montage via `window.__dzSubtab`, et par l'ecouteur de l'evenement).

Mecanique identique a patch_bundle_materialforge.py : restauration du .bak
dedie puis re-application, chaque ancre devant apparaitre EXACTEMENT une fois,
sinon abandon sans rien ecrire. Plus la garde de chaine aval de
patch_bundle_geminimodel.py (lignes 32-42) et la sanity de double application.

DANGERS (chacun a deja coute une regression dans ce depot) :
  * NE JAMAIS lancer `repatch_all.py --from ...` sur cette chaine :
    `.bak_subs` et `.bak_vfxrack` ont le meme mtime a la microseconde ET le
    meme sha1, `--list` les sort dans l'ordre inverse du reel. Ce patcher se
    lance SEUL.
  * Relancer `patch_bundle_materialforge.py` seul efface cardforge sans un mot
    (ce patcher-la n'a aucune garde de chaine amont).
  * Le bundle est en CRLF (11 884 `\\r\\n`, zero `\\n` isole). Tout est lu et
    ecrit avec `newline=""` : aucune traduction de fin de ligne, quelle que
    soit la plateforme. Prouve par comptage d'octets avant / apres.
  * Ne jamais `print` une ancre : la console Windows est en cp1252 et les
    libelles d'onglet contiennent des emoji (ecrits ici en echappement).

Run :
    python scripts/patch_bundle_cardforge.py              # depot
    python scripts/patch_bundle_cardforge.py --root <dir> # app installee
    python scripts/patch_bundle_cardforge.py --check      # n'ecrit rien

`--force-unchained` est accepte : son seul effet est de sauter la garde de
chaine aval (comportement copie de patch_bundle_geminimodel.py). Comme
`cardforge` est le maillon de queue, cette garde ne se declenche jamais en
pratique : le drapeau est donc inerte, mais present pour repatch_all.py.
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "cardforge"

# Marqueur de double application : present <=> le patch est deja pose.
MARKER = 'src:"/cardforge/"'

# Sondes de stabilite verifiees apres coup (doivent rester a 1).
STABLE_PROBES = [
    ("screen-switch", 's==="assets3d"&&r.jsx(DzGameAssetsHub,{variant:e})'),
    ("key-p3d", '},"p3d")'),
    ("key-p2d", '},"p2d")'),
    ("key-ptl", '},"ptl")'),
    ("key-pmf", '},"pmf")'),
    ("key-ps3", '},"ps3")'),
]

# Deltas annonces par la spec §2.6. Recalcules depuis PATCHES au demarrage :
# une divergence = faute de frappe dans un remplacement -> abandon.
SPEC_CHAR_DELTA = 251
SPEC_BYTE_DELTA = 254

# (nom de section, ancre, remplacement) — chaque ancre doit etre unique.
PATCHES = [
    # K1 : etat initial du hub — « cards » est un sous-onglet valide
    # (chemin window.__dzSubtab, pose par deepotus:navigate).      delta +13
    ("K1-init-state",
     'return t==="sprites"||t==="tiles"||t==="studio3d"||t==="materials"'
     '?t:"3d"}',
     'return t==="sprites"||t==="tiles"||t==="studio3d"||t==="materials"'
     '||t==="cards"?t:"3d"}'),

    # K2 : evenement relais deepotus:assets-subtab — bascule aussi vers
    # « cards » quand le hub est deja monte.                       delta +20
    ("K2-relay-event",
     'if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles"'
     '||d.subtab==="studio3d"||d.subtab==="materials")setTab(d.subtab)',
     'if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles"'
     '||d.subtab==="studio3d"||d.subtab==="materials"||d.subtab==="cards")'
     'setTab(d.subtab)'),

    # K3 : la rangee d'onglets gagne « Cartes », en DERNIERE position.
    # U+1F0CF = dos de carte a jouer.                 delta +23 car / +26 o
    ("K3-tab-btn",
     'tb("materials","✨ Matières")]},"tabs")',
     'tb("materials","✨ Matières"),'
     'tb("cards","\U0001f0cf Cartes")]},"tabs")'),

    # K4 : le panneau — nouvelle branche AVANT la branche par defaut
    # (3D Studio), pour ne pas deplacer le fallback existant. L'ancre est
    # ancree sur la cle "pmf" pour ne pouvoir tomber qu'apres Matieres.
    # Style d'iframe impose par la chaine (identique aux 4 autres). delta +187
    ("K4-cards-pane",
     '}},"pmf"):r.jsx("iframe",{src:"/studio3d/",title:"3D Studio",',
     '}},"pmf"):tab==="cards"?r.jsx("iframe",{src:"/cardforge/",'
     'title:"Card Forge",style:{flex:1,width:"100%",'
     'minHeight:"calc(100vh - 110px)",border:"0",marginTop:10,'
     'background:"var(--bg-base)"}},"pcf")'
     ':r.jsx("iframe",{src:"/studio3d/",title:"3D Studio",'),

    # K5 : description de l'entree de navigation du rail.           delta +8
    ("K5-nav-desc",
     'desc:"3D studio, sprites, tuiles & matières"',
     'desc:"3D studio, sprites, tuiles, matières & cartes"'),
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
                f"recent que {bak.name}). cardforge doit rester le DERNIER "
                "maillon ; ne pas utiliser repatch_all sur cette chaine "
                "(mtimes ex aequo vfxrack/subs).")


def ensure_tail_order(bak):
    """`shutil.copy2` conserve le mtime de la SOURCE (piege 3 de la spec) :
    le .bak_cardforge pourrait ne pas sortir en dernier de `repatch_all
    --list`. On force son mtime au-dela de tous les autres .bak."""
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
    # Le shell ne demarre pas forcement dans le depot : repli sur scripts/..
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
        # Controle a sec : on valide les ancres sur l'etat PRE-patch
        # (le .bak s'il existe, sinon le bundle courant), sans rien ecrire.
        src = bak if bak.exists() else bundle
        s = read_src(src)
        nm = s.count(MARKER)
        if nm:
            deja = " (et aucun .bak_cardforge ici)" if not bak.exists() else ""
            raise SystemExit(
                f"[{TAG}] sanity : marqueur cardforge deja present x{nm} dans "
                f"{src.name}{deja} — double application refusee.\n"
                f"[{TAG}] Si cette racine est l'APP INSTALLEE : c'est normal et "
                "c'est voulu. On ne patche pas l'app, on y COPIE le bundle "
                "deja patche du depot (les .bak_* de l'app sont ceux de la "
                "construction precedente). Patcher ici a nouveau appliquerait "
                "le patch deux fois.")
        for tag, anchor, _repl in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(
                    f"[{tag}] anchor count={n} (want 1) dans {src.name}. "
                    "Aborting.")
        raw = src.read_bytes()
        crlf, lf, cr = eol_stats(raw)
        univ = len(s) - crlf  # lecture newline=None : CRLF compte pour 1
        print(f"[{TAG}] applicable sur {src}")
        print(f"[{TAG}] {len(PATCHES)} ancres OK (1 occurrence chacune), "
              f"marqueur absent")
        print(f"[{TAG}] fins de ligne : CRLF={crlf} LF-isole={lf} "
              f"CR-isole={cr}")
        print(f"[{TAG}] taille avant : {len(raw)} o / {len(s)} car (newline='')"
              f" / {univ} car (universel)")
        print(f"[{TAG}] delta attendu : +{dc} car / +{db} o")
        print(f"[{TAG}] taille apres  : {len(raw) + db} o / {len(s) + dc} car "
              f"(newline='') / {univ + dc} car (universel)")
        return

    if not bak.exists():
        # Sanity AVANT le backup : sinon un bundle deja patche empoisonnerait
        # le .bak_cardforge (qui deviendrait un point de chaine post-patch).
        if MARKER in read_src(bundle):
            raise SystemExit(
                f"[{TAG}] sanity : marqueur cardforge deja present dans le "
                f"bundle alors que {bak.name} n'existe pas (patch pose a la "
                "main, ou backup perdu). Etat ambigu : abandon sans rien "
                "ecrire, aucun backup cree.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine (piege copy2)")
        print("backup ->", bak)
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
            f"[{TAG}] sanity : marqueur cardforge deja present apres restore "
            f"depuis {bak.name} (backup empoisonne = pris APRES un patch). "
            "Aborting.")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)

    # newline='' a l'ecriture : aucune traduction, le CRLF traverse intact.
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
            f"taille {len(after)} o, attendu {len(before) + db} o "
            f"({len(before)} + {db})")
    if len(s) != chars0 + dc:
        problems.append(
            f"caracteres {len(s)}, attendu {chars0 + dc} ({chars0} + {dc})")
    if s.count(MARKER) != 1:
        problems.append(f"marqueur cardforge x{s.count(MARKER)} (want 1)")
    for tag, anchor, _r in PATCHES:
        if s.count(anchor) != 0:
            problems.append(f"{tag} : ancre encore presente")
    for name, probe in STABLE_PROBES:
        if s.count(probe) != 1:
            problems.append(f"sonde {name} x{s.count(probe)} (want 1)")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))

    print("OK - bundle patche (hub 3D|3D Studio|Sprites|Tuiles|Matieres|"
          "Cartes).")
    print(f"   taille  : {len(before)} -> {len(after)} o (+{db})")
    print(f"   car     : {chars0} -> {len(s)} (lecture newline='', +{dc})")
    print(f"   CRLF    : {crlf0} -> {crlf1} (LF isole {lf1}, CR isole {cr1})")
    print(f"   sondes  : {len(STABLE_PROBES)} a 1, {len(PATCHES)} ancres "
          "consommees, marqueur x1")
    print("   suite   : scripts/qa/inventory_bundle.py (APRES), puis "
          "python scripts/repatch_all.py --list -> cardforge en DERNIER")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
