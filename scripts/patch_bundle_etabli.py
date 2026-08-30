# -*- coding: utf-8 -*-
# scripts/patch_bundle_etabli.py
"""Patcher assert-garde : onglet « Etabli » de la Bibliotheque.

BASELINE : bundle POST-patch libsend (dernier maillon en date).
Backup dedie : `.js.bak_etabli`. Position : EN QUEUE, apres libsend.
Moitie serveur (deja livree) : GET /api/etabli/productions, cf.
`backend/tests/test_etabli_canevas.py` section K.

« Il convient aussi de rajouter les dossiers generes dans une categorie
specifique de la librairie pour pouvoir facilement la retrouver. » —
la categorie prend la forme d'un SEPTIEME onglet, a cote d'Images /
Renders / 3D / Sprites / Audio / Favoris.

CE QUE LE PATCH NE FAIT PAS, ET C'EST LE POINT
  Aucun markup, aucune CSS, aucun composant. La rangee d'onglets du
  bundle est `Object.keys(vo).map(...)` : ajouter une cle a l'objet de
  demonstration `vo` SUFFIT a obtenir un bouton rigoureusement identique
  a ses voisins (meme composant, meme typographie, memes jetons, meme
  pastille de compte). La liste, elle, vient de `T["Etabli"]`, et la
  carte est celle de l'onglet 3D — la route serveur epouse sa forme
  expres. Six greffes, toutes additives sauf E6.

LES TROIS CORRECTIONS QUE LA ROUTE LEGUE (mesurees par la tache serveur)
  1. `thumb` peut valoir `null` (job adopte sans preview.png et sans
     silhouette). La carte fait `<img src={C.thumb} onError={… shot/0}>`
     — React OMET l'attribut quand la valeur est `null`, donc aucune
     requete, aucun evenement `error`, et le repli `shot/0` ne joue
     JAMAIS. On le pose donc nous-memes a la lecture.
  2. `date` porte l'ISO brut la ou T3 envoie une date deja passee par
     `mo()`. Sans quoi la carte afficherait `2026-08-30T20:39:30+00:00`.
  3. `imprimable` vaut faux des qu'il y a une version ecrite :
     `print3d_from_assets3d` lit `model.glb` et jamais `model.v<n>.glb`,
     donc « Envoyer vers -> Impression 3D » enverrait le BROUILLON au
     slicer — un objet faux, imprime, en silence. E6 masque cette entree
     de menu. On NE repare PAS la route d'impression : c'est un autre
     chantier, et le menu ne sait de toute facon pas transmettre un
     numero de version. Le mapping force un booleen STRICT (`===!0`) :
     si le champ disparaissait de la route, le menu se fermerait au lieu
     de s'ouvrir sur un mensonge.

DANGERS : jamais `repatch_all.py --from` sur cette chaine, lancement
SEUL, newline='' partout (CRLF), jamais d'ancre imprimee (cp1252).
Validation finale : copie .mjs + `node --check`.

Run :
    python scripts/patch_bundle_etabli.py              # depot
    python scripts/patch_bundle_etabli.py --check      # n'ecrit rien
    python scripts/patch_bundle_etabli.py --deltas     # affiche les deltas
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "etabli"
MARKER = "__dzEtabli"
MARKER_ATTENDU = 2      # la definition + l'appel dans le sondage de vm

STABLE_PROBES = [
    ("libpicker", "__dzLibPicker", 10),
    ("libprov", "__dzSrcChips", 2),
    ("libsend", "__dzSendTo", 2),
    ("print3d", "__dzPrint3d", 3),
    ("spritelab", "__dzToSpriteLab", 5),
    ("navrail", "dz_nav_collapsed", 2),
    ("dzdesign", "__dzCatBar", 2),
    ("rangee-onglets", "Object.keys(vo)", 1),
]

# comptes attendus APRES application (verification post-ecriture)
POST_COUNTS = [
    ("__dzEtabli", 2),
    ("/api/etabli/productions", 1),
    ("Établi", 2),              # la cle de `vo` + la cle de `T`
    ("Object.keys(vo)", 1),     # toujours UNE rangee d'onglets
    ("/shot/0", 4),             # les 3 d'avant + le repli du thumb nul
    ("__dzLibPicker", 10),
    ("__dzSrcChips", 2),
    ("__dzSendTo", 2),
    ("__dzPrint3d", 3),
    ("__dzToSpriteLab", 5),
    ("__dzQuickStart", 3),
    ("__dzMontageAdd", 4),
    ("deepotus:select-post", 6),
]

SPEC_CHAR_DELTA = 524
SPEC_BYTE_DELTA = 526

# ── E1 : le seul code neuf, un lecteur de route (module, avant vm) ───────────
# `mo` est declaree au meme niveau que `vm` (le bundle est un module unique)
# et `vm` s'en sert deja : elle est donc dans la portee de ce helper-ci.
# `.catch(function(){})` GARDE la derniere liste connue au lieu de la vider :
# un hoquet reseau ne doit pas faire clignoter la categorie.
HELPER = (
    "function __dzEtabli(cb){try{"
    'fetch("/api/etabli/productions").then(function(rp){'
    'if(!rp.ok)throw new Error("HTTP "+rp.status);return rp.json()})'
    ".then(function(dd){cb(((dd&&dd.items)||[]).map(function(z){"
    'var sh=String((z&&z.short)||"");'
    "return Object.assign({},z,{"
    'date:mo(z&&z.date)||"",'
    'thumb:(z&&z.thumb)||("/api/assets/3d/"+sh+"/shot/0"),'
    "imprimable:(z&&z.imprimable)===!0})}))})"
    ".catch(function(){})}catch(e){}}"
)

# ── ancres (mesurees au bundle post-libsend) ─────────────────────────────────
_E1 = "function vm({variant:e,uploads:t=[],setUploads:n=()=>{}}){"
_E2 = '[dzSF,dzSFs]=x.useState(""),'
_E3 = "d(W),f(R||[]),"
_E4 = "__dzFavImgHas(z.name)))},Y=T[o]||[],"
_E5 = ',"3D":[],Sprites:[],Audio:[],Favoris:[]};function __dzFavGet(){'
_E6 = 'if(m.kind==="asset3d"&&m.short){'

PATCHES = [
    # le code neuf, pose juste avant l'ecran Library
    ("E1-lecteur", _E1, HELPER + _E1),
    # l'etat de la categorie, a la suite de celui de libprov
    ("E2-etat", _E2, _E2 + "[dzEta,dzEtas]=x.useState([]),"),
    # E3 : AUCUN cycle de vie neuf. On se greffe sur le sondage EXISTANT
    # (`Promise.all([listImages, listJobs, listAudio])`, intervalle 8 s,
    # drapeau de montage `C`, `clearInterval` au demontage) — c'est le
    # chemin que T3 emprunte deja pour ses jobs.
    ("E3-charge", _E3, _E3 + "__dzEtabli(function(L){if(C)dzEtas(L)}),"),
    # la categorie dans la table des listes
    ("E4-liste", _E4, '__dzFavImgHas(z.name))),"Établi":dzEta},Y=T[o]||[],'),
    # E5 : LA RANGEE D'ONGLETS. Elle iterera `Object.keys(vo)` — le bouton
    # sort du meme `map` que ses voisins. Le tableau VIDE compte aussi : le
    # bundle se replie sur `vo[o]` quand la liste reelle est vide
    # (`Y.length>0?Y:vo[o]`), et une categorie neuve ne doit pas se
    # remplir d'items de demonstration.
    ("E5-onglet", _E5,
     ',"3D":[],Sprites:[],Audio:[],Favoris:[],"Établi":[]};'
     "function __dzFavGet(){"),
    # E6 : la SEULE greffe non additive. `undefined!==!1` reste vrai, donc
    # les cartes de l'onglet 3D gardent leur entree d'impression intacte ;
    # seules les productions de l'Etabli portent le champ.
    ("E6-garde-impression", _E6,
     'if(m.kind==="asset3d"&&m.short&&m.imprimable!==!1){'),
]


def deltas():
    dc = sum(len(rp) - len(a) for _t, a, rp in PATCHES)
    db = sum(len(rp.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, rp in PATCHES)
    return dc, db


def check_spec_parity():
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(
            f"[{TAG}] parite spec rompue : delta calcule {dc} car / {db} o, "
            f"spec {SPEC_CHAR_DELTA} car / {SPEC_BYTE_DELTA} o. Aborting.")
    return dc, db


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. "
                f"{TAG} doit rester le DERNIER maillon ; jamais de "
                "repatch_all sur cette chaine.")


def ensure_tail_order(bak):
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
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_src(p):
    return p.read_text(encoding="utf-8", newline="")


def eol_stats(data):
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
    if "--deltas" in args:
        dc, db = deltas()
        print(f"[{TAG}] delta +{dc} car / +{db} o")
        return
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
        if s.count(MARKER):
            raise SystemExit(
                f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans "
                f"{src.name} : double application refusee. Une racine d'app "
                "installee se met a jour par COPIE du bundle du depot.")
        for tag, anchor, _r in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(f"[{tag}] anchor count={n} (want 1). "
                                 "Aborting.")
        for name, probe, want in STABLE_PROBES:
            if s.count(probe) != want:
                raise SystemExit(f"[sonde {name}] count={s.count(probe)} "
                                 f"(want {want}). Aborting.")
        raw = src.read_bytes()
        crlf, lf, cr = eol_stats(raw)
        print(f"[{TAG}] applicable sur {src}")
        print(f"[{TAG}] {len(PATCHES)} ancres OK, marqueur absent, "
              f"{len(STABLE_PROBES)} sondes aux comptes")
        print(f"[{TAG}] CRLF={crlf} LF-isole={lf} CR-isole={cr} ; "
              f"delta +{dc} car / +{db} o")
        return

    if not bak.exists():
        if MARKER in read_src(bundle):
            raise SystemExit(
                f"[{TAG}] marqueur present sans {bak.name} : etat ambigu, "
                "abandon sans rien ecrire.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine")
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)

    before = bundle.read_bytes()
    crlf0, lf0, cr0 = eol_stats(before)
    if lf0 or cr0:
        raise SystemExit(f"[{TAG}] fins de ligne non homogenes. Aborting.")
    s = read_src(bundle)
    chars0 = len(s)
    if MARKER in s:
        raise SystemExit(f"[{TAG}] backup empoisonne (marqueur present "
                         "apres restore). Aborting.")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)
    with open(bundle, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)

    after = bundle.read_bytes()
    crlf1, lf1, cr1 = eol_stats(after)
    problems = []
    if (crlf1, lf1, cr1) != (crlf0, 0, 0):
        problems.append("fins de ligne changees")
    if len(after) != len(before) + db:
        problems.append(f"taille {len(after)} o, attendu {len(before) + db}")
    if len(s) != chars0 + dc:
        problems.append(f"caracteres {len(s)}, attendu {chars0 + dc}")
    if s.count(MARKER) != MARKER_ATTENDU:
        problems.append(f"marqueur x{s.count(MARKER)} "
                        f"(want {MARKER_ATTENDU})")
    for probe, want in POST_COUNTS:
        if s.count(probe) != want:
            problems.append(f"post {probe!a} x{s.count(probe)} "
                            f"(want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print("OK - bundle patche (onglet Etabli : cle de vo, liste de T, "
          "lecteur de route, garde d'impression).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : copie .mjs + node --check, puis DEPLOYER le bundle")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
