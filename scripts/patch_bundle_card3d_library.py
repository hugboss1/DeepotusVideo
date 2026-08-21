# -*- coding: utf-8 -*-
# scripts/patch_bundle_card3d_library.py
"""Patcher assert-garde : les cartes 3D de Card Forge dans la Bibliotheque.

BASELINE : bundle POST-patch `version` (dernier maillon en date de la chaine).
Backup dedie : `.js.bak_card3d_library` (etat juste avant CE patch).
Position dans la chaine : EN QUEUE, apres `version` — verifie par
`python scripts/repatch_all.py --list` (doit dire « OK », jamais
« SANS SCRIPT » : ce script deduit le patcher du TAG du backup).
Spec : docs/superpowers/specs/2026-08-19-cardforge-universel-design.md (§5.6
point 7) ; plan 2026-08-20-cardforge-phase2c-canvas.md (tache 6, etape 3).

CE QUE FAIT LE PATCH, ET RIEN DE PLUS : elargir DEUX filtres de provider.
`POST /api/cards/{did}/forge3d/library/{art}` (backend, meme tache) copie
l artefact construit dans `outputs/assets3d/{short}/` -- la disposition EXACTE
que `/api/assets/3d/{short}/{glb,preview,manifest}` lit deja -- et pose un
JobRecord `provider="card3d"`. Tout le reste de la Bibliotheque 3D (viewer,
telechargement, favoris, Optimiser, renommage, suppression) marche alors sans
un octet de plus : il ne manque que la reconnaissance du nouveau provider dans
les deux endroits qui filtrent la file par `provider==="asset3d"`.

`kind` reste « asset3d » cote ecran, expres : c est la categorie de l OBJET
(un modele 3D), pas celle de son fabricant. Le provider, lui, dit d ou viennent
les octets -- et il ne ment pas.

LA DOCTRINE DE CHAINE, UNE SEULE (mesuree le 22/08 ; reapply_inblock_patches.py
pointe ICI plutot que d en raconter une seconde). `repatch_all.py` deduit
l ordre des maillons du MTIME de leur `.bak`, et deux couples sont EX AEQUO a
la microseconde ET au sha1 -- `keepstate`/`sfxstudio` et `subs`/`vfxrack` :

    keepstate  1786444476.444258  1338545 o  sha1 fde613636754
    sfxstudio  1786444476.444258  1338545 o  sha1 fde613636754
    subs       1786444809.741715  1343416 o  sha1 1c0da947d8d1
    vfxrack    1786444809.741715  1343416 o  sha1 1c0da947d8d1

Le tri de `--list` est donc INDECIDABLE sur ces quatre-la (l ordre depend du
parcours de repertoire), d ou :

  * REJOUER DEPUIS UN POINT ANTERIEUR OU EGAL a la derniere egalite
    (`subs`/`vfxrack`) N EST PAS SUR -- ce qui inclut `--from sonvfx`, donc
    inclut `reapply_inblock_patches.py`, qui rafraichit ce bloc en restaurant
    `.bak_sonvfx` (730 Ko, l etat du 6 aout, contre 1 367 Ko aujourd hui) et
    efface au passage TOUS les maillons poses depuis.
  * REJOUER DEPUIS UN POINT STRICTEMENT POSTERIEUR est sur : aucune egalite
    n y subsiste. `python scripts/repatch_all.py --from card3d_library` ne
    rejoue que CE maillon, et c est le seul emploi de `repatch_all` dont ce
    patcher a besoin. Sinon : se lancer SEUL.
  * Relancer un patcher AMONT seul (materialforge, cardforge, version...)
    efface celui-ci sans un mot. La garde de chaine ci-dessous protege le
    SENS INVERSE (ce patcher refuse de tourner si un maillon AVAL existe).
  * Le bundle est en CRLF (11 884 `\\r\\n`, zero `\\n` isole). Tout est lu et
    ecrit avec `newline=""` : aucune traduction de fin de ligne, quelle que
    soit la plateforme. Prouve par comptage d octets avant / apres. Une source
    relue en LF ferait echouer toutes les ancres sans autre symptome qu un
    compte a 0 (piege connu de la chaine, cf. reapply_inblock_patches.py).

Run :
    python scripts/patch_bundle_card3d_library.py              # depot
    python scripts/patch_bundle_card3d_library.py --root <dir> # app installee
    python scripts/patch_bundle_card3d_library.py --check      # n ecrit rien

`--force-unchained` est accepte : son seul effet est de sauter la garde de
chaine aval (comportement copie de patch_bundle_cardforge.py).
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
# LE TAG EST LE NOM DU FICHIER, et ce n'est pas de la cosmetique :
# `repatch_all.py` deduit le script d'un maillon de son `.bak_<tag>`
# (`patch_bundle_<tag>.py`). Un tag « card3dlibrary » devant un fichier
# `patch_bundle_card3d_library.py` sortait « SANS SCRIPT » de
# `--list` — c'est-a-dire une chaine NON REJOUABLE, et un abandon net
# le jour ou quelqu'un rejoue depuis un maillon amont. Mesure faite.
TAG = "card3d_library"

# Marqueur de double application : present <=> le patch est deja pose.
MARKER = '||z.provider==="card3d"'

# Sondes de stabilite verifiees apres coup (doivent rester a 1). Les trois
# premieres sont les filtres de RENDUS VIDEO : ils excluent asset3d et
# sprite2d nommement, et ils ne doivent PAS etre elargis -- une carte 3D n y
# entre pas parce que son JobRecord laisse `final_video_path` VIDE (decision
# backend de la meme tache : un GLB n est pas un rendu video). Si un jour ils
# changent de forme, ce patcher doit le voir.
STABLE_PROBES = [
    ("rendus-bibliotheque", 'C.provider!=="asset3d"&&C.provider!=="sprite2d"'),
    ("rendus-studio", 'l.provider!=="asset3d"&&l.provider!=="sprite2d"'),
    ("rendus-scheduler", 'q.provider!=="asset3d"&&q.provider!=="sprite2d"'),
    ("kind-asset3d", 'kind:"asset3d"'),
    ("filtre-sprites",
     'TS=u.filter(C=>C.provider==="sprite2d"&&C.status==="done"'
     '&&C.final_video_path)'),
]

# Deltas annonces par le plan. Recalcules depuis PATCHES au demarrage : une
# divergence = faute de frappe dans un remplacement -> abandon.
SPEC_CHAR_DELTA = 48
SPEC_BYTE_DELTA = 48

# (nom de section, ancre, remplacement) -- chaque ancre doit etre unique.
PATCHES = [
    # L1 : le hub Game Assets, onglet 3D -- la liste des jobs qu il poll et
    # dont il va chercher le manifeste. Sans ca une carte publiee n apparait
    # pas dans l ecran ou l on FABRIQUE de la 3D.            delta +23
    ("L1-hub-liste-jobs",
     'return z.provider==="asset3d"});setJobs(L)',
     'return z.provider==="asset3d"||z.provider==="card3d"});setJobs(L)'),

    # L2 : la BIBLIOTHEQUE, onglet 3D -- la ligne qui fabrique les vignettes
    # (`url` = /glb, `thumb` = /preview, `short` = job_id.slice(0,8)). C est
    # LE filtre de la demande utilisateur. Parentheses obligatoires : `&&` lie
    # plus fort que `||`, sans elles un job card3d NON termine passerait.
    #                                                        delta +25
    ("L2-bibliotheque-onglet-3d",
     'T3=u.filter(C=>C.provider==="asset3d"&&C.status==="done")',
     'T3=u.filter(C=>(C.provider==="asset3d"||C.provider==="card3d")'
     '&&C.status==="done")'),
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
                f"recent que {bak.name}). {TAG} doit rester le DERNIER "
                "maillon ; ne pas utiliser repatch_all sur cette chaine "
                "(mtimes ex aequo vfxrack/subs).")


def ensure_tail_order(bak):
    """`shutil.copy2` conserve le mtime de la SOURCE : le .bak pourrait ne pas
    sortir en dernier de `repatch_all --list`. On force son mtime au-dela de
    tous les autres .bak."""
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
    """Remplacement assert-garde : l ancre doit exister exactement une fois."""
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
        # Controle a sec : on valide les ancres sur l etat PRE-patch (le .bak
        # s il existe, sinon le bundle courant), sans rien ecrire.
        src = bak if bak.exists() else bundle
        s = read_src(src)
        nm = s.count(MARKER)
        if nm:
            deja = f" (et aucun .bak_{TAG} ici)" if not bak.exists() else ""
            raise SystemExit(
                f"[{TAG}] sanity : marqueur card3d deja present x{nm} dans "
                f"{src.name}{deja} — double application refusee.\n"
                f"[{TAG}] Si cette racine est l'APP INSTALLEE : c'est normal "
                "et c'est voulu. On ne patche pas l'app, on y COPIE le bundle "
                "deja patche du depot.")
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
        # ── TOUT CE QUI PEUT REFUSER, REFUSE AVANT LE PREMIER OCTET ECRIT ──
        # M7 (revue adverse de la T6) : le controle des ancres vivait APRES la
        # copie du backup. Une ancre perimee produisait donc un `.bak` PUIS un
        # abandon — et ce backup-la est un piege differe : l'operateur repare
        # l'ancre a la main, relance, et le patcher prend cette fois la branche
        # « restore <- .bak » qui DETRUIT la reparation, sans un mot. Un
        # backup est un ENGAGEMENT : on ne le pose que si la passe est
        # certaine de pouvoir aller au bout.
        pre = read_src(bundle)
        if MARKER in pre:
            raise SystemExit(
                f"[{TAG}] sanity : marqueur card3d deja present dans le "
                f"bundle alors que {bak.name} n'existe pas (patch pose a la "
                "main, ou backup perdu). Etat ambigu : abandon sans rien "
                "ecrire, aucun backup cree.")
        for tag, anchor, _repl in PATCHES:
            n = pre.count(anchor)
            if n != 1:
                raise SystemExit(
                    f"[{tag}] anchor count={n} (want 1) dans {bundle.name}. "
                    "Aborting sans rien ecrire, aucun backup cree.")
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
            f"[{TAG}] sanity : marqueur card3d deja present apres restore "
            f"depuis {bak.name} (backup empoisonne = pris APRES un patch). "
            "Aborting.")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)

    # ECRITURE ATOMIQUE PAR COPIE TEMPORAIRE : jamais un bundle a moitie
    # patche sur disque. Le fichier temporaire vit A COTE de la cible (meme
    # volume, donc `os.replace` est un rename, pas une copie), et il n est
    # promu qu apres que TOUS les remplacements ont ete faits en memoire.
    tmp = bundle.with_name(bundle.name + ".tmp_" + TAG)
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)
    os.replace(tmp, bundle)

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
        problems.append(f"marqueur card3d x{s.count(MARKER)} (want 1)")
    if s.count('||C.provider==="card3d"') != 1:
        problems.append("second marqueur card3d absent ou duplique")
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

    print("OK - bundle patche (cartes 3D dans la Bibliotheque).")
    print(f"   taille  : {len(before)} -> {len(after)} o (+{db})")
    print(f"   car     : {chars0} -> {len(s)} (lecture newline='', +{dc})")
    print(f"   CRLF    : {crlf0} -> {crlf1} (LF isole {lf1}, CR isole {cr1})")
    print(f"   sondes  : {len(STABLE_PROBES)} a 1, {len(PATCHES)} ancres "
          "consommees, marqueurs x1")
    print("   suite   : scripts/qa/inventory_bundle.py (APRES), puis "
          "python scripts/repatch_all.py --list -> card3dlibrary en DERNIER")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
