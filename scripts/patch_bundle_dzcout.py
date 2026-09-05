# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzcout.py
"""Assert-guarded patcher : la pastille de coût DIT ce qu'elle ne sait pas.

BASELINE : bundle POST-patch libpicker/montage (queue de chaîne au 05/09/2026).
Backup dédié : .js.bak_dzcout (état juste avant CE patch).
JAMAIS de repatch_all sur cette chaîne — la garde aval ci-dessous le rappelle.

POURQUOI. `GET /api/cost/usage` rend `{total_usd, by_provider}`. Depuis la
tâche 8b, un provider que `_job_to_cost` ne sait pas tarifer rend 0 sous la
clé `non-tarifé:<provider>` — « pour que le blanc porte un nom ». MESURÉ à ce
moment-là : la chaîne `by_provider` n'apparaissait NULLE PART dans le bundle.
La pastille n'affichait que `total_usd`, donc le blanc mourait avant l'écran
et un total INCOMPLET se présentait comme un total.

CE QUE CE PATCH CHANGE, ET RIEN D'AUTRE :
  L1  préambule `__dzCoutBlanc(u)` en tête de fichier — une fonction PURE de
      la carte `by_provider` : elle rend `{n, noms, puce, titre}`. Aucune
      lecture du DOM, aucun appel réseau : c'est ce qui la rend exécutable
      telle quelle sous node par `backend/tests/test_cout_pastille.py`, qui
      l'EXTRAIT du bundle livré plutôt que de la recopier.
  L2  l'infobulle de la pastille, jusqu'ici une phrase fixe en anglais,
      devient la liste de `by_provider` ligne à ligne, montant compris — et
      une ligne non tarifée y est nommée comme telle.
  L3  le total passe de « $x » à « ≥ $x » dès qu'un blanc existe, et une
      pastille ambre « · N non tarifé(s) » s'ajoute à côté.

LE NOM DU FOURNISSEUR EST AFFICHÉ SANS SON PRÉFIXE TECHNIQUE : `non-tarifé:`
est une convention de clé, pas un mot que l'utilisateur doit lire. Le préfixe
que ce fichier découpe et celui que `_job_to_cost` écrit sont deux littéraux
dans deux langages ; c'est le banc qui les fait mesurer l'un par l'autre.

CE QUE CE PATCH NE FAIT PAS : il ne rafraîchit pas la pastille (elle lit
`cost/usage` au montage du Shell, inchangé), il n'ajoute aucun compte de JOBS
(la carte ne le porte pas), et il ne touche à aucun autre octet.

Run :
    python scripts/patch_bundle_dzcout.py              # dépôt
    python scripts/patch_bundle_dzcout.py --check      # n'écrit rien
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "dzcout"
MARKER = "__dzCoutBlanc"
MARKER_ATTENDU = 7      # définition + window x2 + infobulle + total + puce x2

# Sondes des maillons AMONT : si l'un de ces comptes bouge, c'est qu'un
# patcher amont a été rejoué seul et a effacé ce qui le suivait.
STABLE_PROBES = [
    ("libpicker", "__dzLibPicker", 10),
    ("print3d", "__dzPrint3d", 3),
    ("navrail", "dz_nav_collapsed", 2),
    ("dzdesign", "__dzCatBar", 2),
    ("montage", "DzTracks", 25),
]

# ── L1 — le préambule, fonction PURE de la carte ────────────────────────────
# Le libellé « fournisseurs » n'apparaît QUE dans la branche plurielle : la
# ligne `deux_blancs_accordent_le_pluriel` du banc serait sinon verte au
# singulier aussi, sans rien mesurer.
PREAMBULE = (
    "function __dzCoutBlanc(u){"
    'var P="non-tarifé:",b=(u&&u.by_provider)||{},k=Object.keys(b).sort(),'
    "nt=[],ls=[],i,x;"
    "for(i=0;i<k.length;i++){x=k[i];"
    "if(x.indexOf(P)===0){nt.push(x.slice(P.length));"
    'ls.push("  ? "+x.slice(P.length)'
    '+" — NON TARIFÉ : coût inconnu, absent de ce total")}'
    'else{ls.push("  · "+x+" — $"+b[x]'
    '+(x==="local"?" (opérations locales, sans dépense)":""))}}'
    'var t=k.length?"Dépense estimée sur cette app, par fournisseur :\\n"'
    '+ls.join("\\n"):"Aucune dépense estimée pour l\'instant.";'
    'if(nt.length){t+="\\n\\n⚠ Ce total est un MINORANT : "+nt.length'
    '+" fournisseur"+(nt.length>1?"s":"")+" sans tarif ("+nt.join(", ")'
    '+"). "+(nt.length>1?"Leur":"Son")+" coût réel n\'est PAS compté."}'
    'return{n:nt.length,noms:nt,puce:"· "+nt.length+" non tarifé"'
    '+(nt.length>1?"s":""),titre:t+"\\n\\nClic → Réglages."}}'
    "window.__dzCoutBlanc=__dzCoutBlanc;"
)

_A1 = '(function(){const t=document.createElement("link").relList;'
_A2 = ('title:"Estimated spend on this app + live provider balances. '
       'Click for Settings."')
_A3 = 'children:["$",Cu&&Cu.total_usd!=null?Cu.total_usd:"—"]}),'

_R3 = (
    'children:[__dzCoutBlanc(Cu).n?"≥ $":"$",'
    'Cu&&Cu.total_usd!=null?Cu.total_usd:"—"]}),'
    '__dzCoutBlanc(Cu).n?r.jsx("span",{style:{color:"var(--amber)"},'
    'children:__dzCoutBlanc(Cu).puce},"dzcoutblanc"):null,'
)

PATCHES = [
    ("L1-preambule", _A1, PREAMBULE + _A1),
    ("L2-infobulle", _A2, "title:__dzCoutBlanc(Cu).titre"),
    ("L3-total-et-puce", _A3, _R3),
]


def deltas():
    dc = sum(len(r) - len(a) for _t, a, r in PATCHES)
    db = sum(len(r.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, r in PATCHES)
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
    check = "--check" in args
    dc, db = deltas()
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
                f"{src.name} — double application refusee. Une racine d'app "
                "installee se met a jour par COPIE du bundle du depot.")
        for tag, anchor, _r in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(f"[{tag}] anchor count={n} (want 1). "
                                 "Aborting.")
        # L1 s'insere EN TETE : l'ancre doit etre le debut du fichier, sinon
        # la fonction atterrirait dans une portee quelconque.
        if not s.startswith(_A1):
            raise SystemExit(f"[L1] l'ancre n'est pas en tete du fichier. "
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
    if not s.startswith(_A1):
        raise SystemExit(f"[L1] l'ancre n'est pas en tete du fichier. "
                         "Aborting.")
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
    if not s.startswith(PREAMBULE):
        problems.append("le preambule n'est pas en tete du fichier")
    for tag, _anchor, repl in PATCHES:
        if s.count(repl) != 1:
            problems.append(f"{tag} : remplacement x{s.count(repl)} (want 1)")
    if s.count(_A2) or s.count(_A3):
        problems.append("une ancre consommee est encore presente")
    for name, probe, want in STABLE_PROBES:
        if s.count(probe) != want:
            problems.append(f"sonde {name} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print("OK - bundle patche (la pastille de cout dit son blanc).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : & $PY tests/test_cout_pastille.py, puis DEPLOYER")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
