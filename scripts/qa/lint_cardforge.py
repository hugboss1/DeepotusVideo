# -*- coding: utf-8 -*-
# scripts/qa/lint_cardforge.py
"""Fait respecter MECANIQUEMENT les regles de cloisonnement de Card Forge.

Spec : docs/superpowers/specs/2026-08-11-cardforge-design.md (§2.2, LES 10
REGLES). Neuf builders travaillent en parallele sur un meme document et un
meme canevas : sans controle automatique, deux modules ecrivent le meme
sous-arbre ou la meme couche et le dernier gagne EN SILENCE (risque 1 de la
spec). Ce script est le garde-fou. Sortie non nulle = build rejete.

Regles verifiees ici :
  R4  Tout selecteur de css/mod-<id>.css contient `.cf-<id>`.
      Aucune regle sur `body`, `:root`, `*`, ni sur un element nu.
  R5  Tout `id=` DOM cree par un module commence par `cf-<id>-`.
  R7  Painters seulement aux z alloues (TABLE Z gelee).
  R8  backend/app/services/cards/<id>.py declare `router = APIRouter()`,
      chemins RELATIFS, et aucun module n'importe le router d'un autre.
  R11 Tout js/mod-<id>.js commence par "use strict".
      CE N'EST PAS UN DETAIL DE STYLE. `CF.doc()` rend un clone deep-frozen,
      mais en mode bâclé une mutation ne leve PAS : c'est un no-op MUET, le
      module croit avoir ecrit, relit l'ancienne valeur et cherche ailleurs
      pendant une heure. La garantie « mutation = TypeError » de la spec 2.2
      est ENTIEREMENT portee par cette directive, dans des <script>
      classiques ou le mode bâclé est le DEFAUT. Aucun test dynamique ne peut
      la remplacer : sur V8 moderne, `Object.getOwnPropertyNames` d'une
      fonction rend la meme chose stricte ou non (mesure). Il ne reste que la
      source — ici au build, et `auditStrict()` au demarrage du lab, qui
      REFUSE de lancer un module non conforme.
  R12 Aucun mutateur GLOBAL dans un module : `CF.patch`, `CF.setFormat`,
      `CF.setCards`, `CF.emit`, `CF.api`, `CF.slot`, `CF.aside`,
      `CF.invalidate` n'existent plus. L'ecriture passe par le JETON rendu
      par `CF.register` (`const M = CF.register({…}); M.patch({…})`) : c'est
      lui qui porte l'identite, la pile d'appel ne la portait pas (un
      `//# sourceURL` suffisait a la contrefaire).
  R13 « Octets sains » (barre de fluidite §9.6-5, amendement du 20/08) :
      aucun octet NUL brut dans les sources du labo (grep et consorts
      traitent le fichier comme du binaire des le premier — un litteral
      `"\x00"` s'ECRIT echappe), et aucun retour chariot CRLF dans le BLOB
      COMMIS (HEAD). Le controle NUL porte sur les octets d'ARBRE DE TRAVAIL
      (c'est ce que lit tout outil, maintenant) ; le controle CRLF porte sur
      le blob HEAD et non l'arbre de travail, expres : mesure sur les
      machines de ce chantier, `core.autocrlf` y convertit la plupart des
      fichiers texte en CRLF AU CHECKOUT alors que le depot les stocke en LF
      (filtre "clean" a l'ecriture) — un controle CRLF sur l'arbre de travail
      serait donc FAUX POSITIF en permanence sur la quasi-totalite du labo,
      sur CE genre de poste. Le blob HEAD, lui, est ce que quiconque clone le
      depot relira reellement : c'est la qu'une regression CRLF (attribut
      gitattributes mal pose, autocrlf desactive au moment d'un commit,
      renormalisation ratee) compte. Si HEAD est indisponible (pas un depot
      git, fichier neuf non suivi, `git` absent du PATH) le controle CRLF est
      SAUTE pour ce fichier ; le controle NUL, lui, reste actif dans tous les
      cas, seul a ne pas dependre de l'historique. Voir check_r13().

Ce que le script ne peut PAS voir (le contrat runtime de core.js reste
l'autorite) : un painter enregistre dynamiquement, un id DOM construit par
concatenation, une route montee par reflexion. Le lint est un filet statique,
pas une preuve.

Comportement sur arborescence vide : les 9 modules sont declares mais aucun
fichier n'existe encore -> tout est signale « absent », rien n'est en faute,
code de retour 0. C'est voulu : le lint doit tourner des le jour 1.

Run :
    python scripts/qa/lint_cardforge.py
    python scripts/qa/lint_cardforge.py --root <dir>
    python scripts/qa/lint_cardforge.py --json
    python scripts/qa/lint_cardforge.py --module face
Codes : 0 = conforme, 1 = violation(s), 2 = erreur d'usage.
"""
import json
import pathlib
import re
import subprocess
import sys

# --- TABLE Z GELEE (spec §2.2) ------------------------------------------
# data, solid, print, gltf, forge3d n'ont AUCUN painter : ils ne dessinent pas la carte.
Z_TABLE = {
    "texture": {10, 30},
    "face": {20},
    "frame": {40, 70},
    "type": {60},
    "data": set(),
    "solid": set(),
    "print": set(),
    "gltf": set(),
    "forge3d": set(),
}
MODULES = ["face", "frame", "type", "data", "solid", "texture", "print",
           "gltf", "forge3d"]  # ordre = rang dans le rail (= numero de piece)
Z_CORE = 90                 # reperes fond perdu / coupe / zone sure

FRONT_DIR = pathlib.Path("frontend/cardforge")
BACK_DIR = pathlib.Path("backend/app/services/cards")
TEST_DIR = pathlib.Path("backend/tests")

# Fichiers .py SUPPLEMENTAIRES par module, au-dela du {mid}.py canonique --
# forge3d_scene.py est le sidecar geometrie de forge3d (couture legs 6, revue
# 2a) : soumis a R8 comme le py canonique, sinon il reste un angle mort
# JUSTE avant que ~1000 lignes de GLB/materiaux (2b) n'y atterrissent. Ne
# compte PAS pour la regle 1 (1 JS + 1 CSS + 1 py + 1 test) : ce n'est pas
# LE py du module, un fichier interne en plus.
EXTRA_PY = {"forge3d": ["forge3d_scene.py"]}

# Harnais QA en .mjs : UN SEUL fichier, simple (pas de sous-arbre a explorer)
# -- R13 le lit comme les sources des 10 modules, meme regle d'octets sains.
QA_MJS = FRONT_DIR / "qa" / "test_core_contract.mjs"

# At-rules dont le contenu porte de vrais selecteurs : on descend dedans.
COND_AT = {"media", "supports", "layer", "container", "scope", "document"}
BARE_ELEMENT = re.compile(r"^[a-z][a-z0-9]*$")
FORBIDDEN_BARE = {"body", "html", "*", ":root", "::backdrop"}


# =========================================================================
# Analyse CSS : un scanner a accolades, pas une regex naive
# =========================================================================
def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _skip_block(css, i):
    """css[i] == '{' -> index juste apres l'accolade fermante appariee."""
    depth, n = 0, len(css)
    while i < n:
        ch = css[i]
        if ch in "\"'":
            q, i = ch, i + 1
            while i < n and css[i] != q:
                i += 2 if css[i] == "\\" else 1
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def iter_selectors(css):
    """Rend (selecteur, ligne) pour chaque bloc de regle reel.

    Descend dans @media / @supports / @layer / @container ; saute entierement
    le corps de @keyframes / @font-face / @page (leurs « selecteurs » sont
    des pourcentages ou rien du tout).
    """
    css = strip_comments(css)
    i, n, buf, line, start = 0, len(css), [], 1, 1
    while i < n:
        ch = css[i]
        if ch == "\n":
            line += 1
            i += 1
            if not "".join(buf).strip():
                start = line
            buf.append(ch)
            continue
        if ch in "\"'":
            j, q = i + 1, ch
            while j < n and css[j] != q:
                j += 2 if css[j] == "\\" else 1
            buf.append(css[i:j + 1])
            line += css.count("\n", i, j + 1)
            i = j + 1
            continue
        if ch == ";":
            buf, start, i = [], line, i + 1
            continue
        if ch == "{":
            prelude = "".join(buf).strip()
            buf = []
            if prelude.startswith("@"):
                m = re.match(r"@([\w-]+)", prelude)
                at = (m.group(1).lower() if m else "")
                if at in COND_AT:      # on descend dans le groupe
                    i += 1
                    start = line
                    continue
                j = _skip_block(css, i)   # keyframes/font-face/page : ignore
                line += css.count("\n", i, j)
                i, start = j, line
                continue
            if prelude:
                yield prelude, start
            j = _skip_block(css, i)
            line += css.count("\n", i, j)
            i, start = j, line
            continue
        if ch == "}":
            buf, start, i = [], line, i + 1
            continue
        buf.append(ch)
        i += 1


def split_selector_list(sel):
    """Coupe sur les virgules de premier niveau (pas celles de :is(a,b))."""
    out, depth, cur = [], 0, []
    for ch in sel:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


# =========================================================================
# Regles
# =========================================================================
def check_r4(mid, path, text, add):
    need = f".cf-{mid}"
    for sel, line in iter_selectors(text):
        for one in split_selector_list(sel):
            flat = " ".join(one.split())
            if need in flat:
                continue
            if flat in FORBIDDEN_BARE or BARE_ELEMENT.match(flat):
                add("R4", path, line,
                    f"selecteur global interdit : {flat!r} "
                    f"(toute regle doit porter {need})")
            else:
                add("R4", path, line,
                    f"selecteur sans {need} : {flat!r}")


ID_PATTERNS = [
    # attribut HTML dans une chaine de gabarit : <div id="cf-face-x">
    (re.compile(r"""(?<![\w$?&#-])id\s*=\s*["']([^"'{}$]+)["']"""), "id="),
    # affectation de propriete : el.id = "cf-face-x"
    (re.compile(r"""\.id\s*=\s*["']([^"'{}$]+)["']"""), ".id="),
    # setAttribute("id", "cf-face-x")
    (re.compile(r"""setAttribute\(\s*["']id["']\s*,\s*["']([^"'{}$]+)["']"""),
     "setAttribute"),
]


def check_r5(mid, path, text, add):
    pref = f"cf-{mid}-"
    seen = set()
    for rx, kind in ID_PATTERNS:
        for m in rx.finditer(text):
            val = m.group(1).strip()
            key = (m.start(1), val)
            if key in seen or not val:
                continue
            seen.add(key)
            if not val.startswith(pref):
                add("R5", path, text.count("\n", 0, m.start()) + 1,
                    f"id DOM {val!r} ({kind}) ne commence pas par {pref!r}")


PAINTERS_RE = re.compile(r"painters\s*:\s*\[")
Z_IN_PAINTERS = re.compile(r"(?<![\w$.-])z\s*:\s*(-?\d+)")


def _array_after(text, i):
    """i = index du '[' ; renvoie le contenu jusqu'au ']' apparie."""
    depth, n, j = 0, len(text), i
    while j < n:
        c = text[j]
        if c in "\"'`":
            q, j = c, j + 1
            while j < n and text[j] != q:
                j += 2 if text[j] == "\\" else 1
        elif c in "[({":
            depth += 1
        elif c in "])}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
        j += 1
    return text[i:]


def check_r7(mid, path, text, add):
    allowed = Z_TABLE[mid]
    found = False
    for m in PAINTERS_RE.finditer(text):
        found = True
        arr = _array_after(text, text.index("[", m.start()))
        line0 = text.count("\n", 0, m.start()) + 1
        zs = [int(z) for z in Z_IN_PAINTERS.findall(arr)]
        if not zs and "".join(arr.split()) != "[]":
            # `painters: []` = zero couche, parfaitement legal (data, solid,
            # print, gltf ne dessinent pas). Un tableau NON vide sans `z:`
            # litteral, lui, est un z calcule : illisible, donc interdit.
            add("R7", path, line0,
                "painters: [...] non vide sans aucun z: litteral (z calcule "
                "-> interdit, la table Z est gelee et doit se lire a l'oeil)")
        for z in zs:
            if z in allowed:
                continue
            if z == Z_CORE:
                add("R7", path, line0,
                    f"z={z} appartient a CORE (reperes fond perdu / coupe / "
                    "zone sure), jamais a un module")
            else:
                owner = next((k for k, v in Z_TABLE.items() if z in v), None)
                who = f" (alloue a {owner!r})" if owner else " (non alloue)"
                add("R7", path, line0,
                    f"z={z} interdit pour {mid!r}{who} ; autorises : "
                    f"{sorted(allowed) or 'aucun'}")
    if not found and allowed:
        add("R7", path, 0,
            f"aucun `painters:` trouve alors que {mid!r} possede les couches "
            f"{sorted(allowed)} (couche non dessinee ?)", warn=True)


# R11 — la directive doit etre la PREMIERE instruction du fichier, commentaires
# et blancs mis a part. `"use strict";` enfoui dans une fonction ne rend pas le
# reste du fichier strict.
DIRECTIVE = re.compile(
    r"""\A(?:\s|/\*.*?\*/|//[^\n]*\n)*["']use strict["']\s*;""", re.S)


def check_r11(mid, path, text, add):
    if DIRECTIVE.match(text):
        return
    add("R11", path, 1,
        'le fichier ne commence pas par "use strict" — en mode bâclé, une '
        "mutation de CF.doc() est un no-op MUET (aucune exception) et la "
        "garantie d'ecriture exclusive tombe")


# R12 — les mutateurs qui vivaient sur le global. `CF.<nom>` suivi d'un `(` ou
# d'un `.` : on ne veut ni l'appel, ni `CF.api.get`.
GLOBAL_MUTATORS = ("patch", "setFormat", "setCards", "emit", "api", "slot",
                   "aside", "invalidate")
R12_RE = re.compile(
    r"(?<![\w$.])CF\s*\.\s*(" + "|".join(GLOBAL_MUTATORS) + r")\s*[.(]")


def check_r12(mid, path, text, add):
    for m in R12_RE.finditer(text):
        add("R12", path, text.count("\n", 0, m.start()) + 1,
            f"CF.{m.group(1)} n'existe plus (il lisait l'identite dans la pile "
            "d'appel, qui se contrefait) : passer par le jeton — "
            "const M = CF.register({...}) puis M." +
            ("setCards" if m.group(1) == "setCards" else
             "setFormat" if m.group(1) == "setFormat" else m.group(1)) + "(...)")


ROUTER_OK = re.compile(r"^\s*router\s*=\s*APIRouter\(\s*\)\s*$", re.M)
ROUTER_ANY = re.compile(r"APIRouter\s*\(")
ROUTE_DEC = re.compile(
    r"@router\.(get|post|put|patch|delete|head|options)\(\s*([\"'])(.*?)\2")


def check_r8(mid, path, text, add, require_router=True):
    # require_router=False : sidecar (EXTRA_PY) — un fichier interne au
    # module qui n'est PAS le py canonique n'a pas a declarer SON router (il
    # n'en a pas, par construction : forge3d_scene.py est PURES, zero
    # dependance HTTP). Le reste de R8 (aucun import du router d'une AUTRE
    # piece, aucune route a chemin absolu, aucun include_router) s'applique
    # quand meme, inchange.
    if require_router and not ROUTER_OK.search(text):
        if ROUTER_ANY.search(text):
            add("R8", path, text.count(
                "\n", 0, ROUTER_ANY.search(text).start()) + 1,
                "signature imposee : `router = APIRouter()` sans argument "
                "(le prefixe est pose par cards/__init__.py)")
        else:
            add("R8", path, 0, "aucun `router = APIRouter()` declare")
    for m in ROUTE_DEC.finditer(text):
        p, line = m.group(3), text.count("\n", 0, m.start()) + 1
        if p.startswith("/api"):
            add("R8", path, line,
                f"chemin absolu {p!r} : les chemins sont RELATIFS au "
                "sous-prefixe /api/cards/<did>/<id>")
        elif "/cards" in p:
            add("R8", path, line,
                f"chemin {p!r} re-declare /cards (deja dans le prefixe)")
        elif "{did}" in p:
            add("R8", path, line,
                f"chemin {p!r} re-declare {{did}} (deja dans le prefixe)")
    for other in MODULES:
        if other == mid:
            continue
        pats = [
            (rf"from\s+app\.services\.cards\.{other}\s+import\s+[^\n]*router",
             f"import du router de {other!r}"),
            (rf"from\s+\.{other}\s+import\s+[^\n]*router",
             f"import du router de {other!r}"),
            (rf"(?<![\w.]){other}\.router\b",
             f"acces a {other}.router"),
        ]
        for rx, why in pats:
            for m in re.finditer(rx, text):
                add("R8", path, text.count("\n", 0, m.start()) + 1,
                    f"{why} : regle 8, aucun module n'importe le router d'un "
                    "autre")
    for m in re.finditer(r"include_router\s*\(", text):
        add("R8", path, text.count("\n", 0, m.start()) + 1,
            "include_router() n'appartient qu'a cards/__init__.py")


def _git_blob_bytes(root, relpath):
    """Octets du blob HEAD pour <relpath>, ou None si indisponible.

    Aucune exception ne remonte : pas un depot git, fichier neuf jamais
    commis, `git` absent du PATH, ou tout simplement un `root` qui n'est pas
    la racine du depot (le tantot-Export sans .git mentionne au-dessus) sont
    tous des cas legitimes ou R13 doit se taire sur le controle CRLF plutot
    que de faire echouer tout le lint pour une raison qui lui est etrangere.
    """
    try:
        r = subprocess.run(
            ["git", "show", f"HEAD:{relpath}"],
            cwd=str(root), capture_output=True, timeout=5)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def check_r13(path, add, root):
    """R13 « octets sains » (spec 9.6-5) : ni NUL brut, ni CRLF.

    NUL : controle sur les octets d'ARBRE DE TRAVAIL — c'est ce que lit tout
    outil (grep, l'IDE, ce lint) MAINTENANT, quel que soit l'historique. Un
    octet NUL brut fait passer le fichier pour du binaire aux yeux d'outils
    textuels (grep s'y est deja arrete une fois sur mod-frame.js) ; ecrit
    besoin, la sequence ECHAPPEE `\\x00` dit la meme chose sans ce cout.

    CRLF : controle sur le BLOB GIT (HEAD:<chemin>), PAS sur l'arbre de
    travail — choix deliberatif, documente ici (cf. R13 dans l'entete du
    fichier) : mesure sur les machines de ce chantier, `core.autocrlf` y
    convertit la plupart des fichiers texte du labo en CRLF AU CHECKOUT alors
    que le depot les STOCKE en LF (filtre "clean" a l'ecriture) — un controle
    CRLF sur l'arbre de travail serait donc FAUX POSITIF en permanence sur la
    quasi-totalite du labo, tout le temps, sur ce genre de poste : le lint
    n'y serait alors plus jamais vert, pour une raison qui ne regarde aucun
    changement reel. Le blob HEAD, lui, EST ce que quiconque clone le depot
    relira reellement — c'est la qu'une regression CRLF (gitattributes mal
    pose, autocrlf desactive au moment precis d'un commit, renormalisation
    ratee) compte. Si HEAD est indisponible pour ce fichier (pas un depot
    git, fichier neuf non suivi, `git` absent du PATH) le controle CRLF est
    SAUTE pour lui — le controle NUL, seul a ne pas dependre de l'historique,
    reste actif dans tous les cas.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return
    if b"\x00" in raw:
        line = raw.count(b"\n", 0, raw.index(b"\x00")) + 1
        add("R13", path, line,
            "octet NUL brut (le fichier passe pour du binaire aux outils "
            "textuels) -- ecrire la sequence ECHAPPEE \\x00")
    try:
        relpath = path.relative_to(root).as_posix()
    except ValueError:
        relpath = path.as_posix()
    blob = _git_blob_bytes(root, relpath)
    if blob is None:
        return
    if b"\r" in blob:
        line = blob.count(b"\n", 0, blob.index(b"\r")) + 1
        add("R13", path, line,
            "retour chariot (CRLF) dans le blob commis (HEAD) -- le depot "
            "attend du LF ; verifier .gitattributes / core.autocrlf au "
            "moment du commit")


# =========================================================================
# Pilote
# =========================================================================
def run(root, only=None):
    findings, present = [], {}

    def add(rule, path, line, msg, warn=False):
        findings.append({"rule": rule, "file": str(path), "line": line,
                         "msg": msg, "warn": bool(warn)})

    for mid in MODULES:
        if only and mid != only:
            continue
        files = {
            "js": root / FRONT_DIR / "js" / f"mod-{mid}.js",
            "css": root / FRONT_DIR / "css" / f"mod-{mid}.css",
            "py": root / BACK_DIR / f"{mid}.py",
            "test": root / TEST_DIR / f"test_cards_{mid}.py",
        }
        present[mid] = {k: v.is_file() for k, v in files.items()}
        if files["css"].is_file():
            check_r4(mid, files["css"], files["css"].read_text(
                encoding="utf-8", errors="replace"), add)
            check_r13(files["css"], add, root)
        if files["js"].is_file():
            t = files["js"].read_text(encoding="utf-8", errors="replace")
            check_r5(mid, files["js"], t, add)
            check_r7(mid, files["js"], t, add)
            check_r11(mid, files["js"], t, add)
            check_r12(mid, files["js"], t, add)
            check_r13(files["js"], add, root)
        if files["py"].is_file():
            check_r8(mid, files["py"], files["py"].read_text(
                encoding="utf-8", errors="replace"), add)
            check_r13(files["py"], add, root)
        if files["test"].is_file():
            check_r13(files["test"], add, root)
        # sidecar geometrie de forge3d (couture legs 6, revue 2a) : soumis a
        # R8 comme le py canonique -- require_router=False, c'est un fichier
        # PURES (zero dependance HTTP) par construction, pas une deuxieme
        # route pour le module.
        for extra in EXTRA_PY.get(mid, []):
            p = root / BACK_DIR / extra
            if p.is_file():
                check_r8(mid, p, p.read_text(
                    encoding="utf-8", errors="replace"), add,
                    require_router=False)
                check_r13(p, add, root)
    # harnais QA .mjs (UN SEUL fichier, simple) : meme regle d'octets sains,
    # hors boucle par module puisqu'il n'appartient a aucun d'eux.
    qa_mjs = root / QA_MJS
    if (not only) and qa_mjs.is_file():
        check_r13(qa_mjs, add, root)
    return findings, present


def main():
    args = sys.argv[1:]
    if "--root" in args:
        root = pathlib.Path(args[args.index("--root") + 1]).resolve()
    else:
        here = pathlib.Path(".").resolve()
        root = here if (here / BACK_DIR.parent).is_dir() else \
            pathlib.Path(__file__).resolve().parent.parent.parent
    only = args[args.index("--module") + 1] if "--module" in args else None
    if only and only not in MODULES:
        print(f"module inconnu {only!r} ; connus : {MODULES}", file=sys.stderr)
        return 2

    findings, present = run(root, only)
    errs = [f for f in findings if not f["warn"]]
    warns = [f for f in findings if f["warn"]]

    if "--json" in args:
        print(json.dumps({"root": str(root), "present": present,
                          "findings": findings, "errors": len(errs),
                          "warnings": len(warns)},
                         indent=2, ensure_ascii=True))
        return 1 if errs else 0

    print(f"racine : {root}")
    print("=== PRESENCE DES FICHIERS (regle 1 : 1 JS + 1 CSS + 1 py + 1 test)")
    nfull = 0
    for mid in MODULES:
        if mid not in present:
            continue
        p = present[mid]
        got = sum(p.values())
        nfull += 1 if got == 4 else 0
        state = "COMPLET" if got == 4 else ("ABSENT " if got == 0 else "PARTIEL")
        marks = " ".join(k if p[k] else f"-{k}" for k in ("js", "css", "py",
                                                          "test"))
        print(f"  {mid:8s} {state}  {marks}")
    print(f"  -> {nfull}/{len(present)} module(s) complet(s)")
    print("=== VIOLATIONS (R4 css · R5 ids DOM · R7 couches z · R8 routeur · R11 use strict · "
          "R12 jeton · R13 octets sains)")
    if not findings:
        print("  aucune")
    for f in findings:
        where = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        print(f"  [{'WARN' if f['warn'] else f['rule']}] {where}\n"
              f"        {f['msg']}")
    print(f"=== BILAN : {len(errs)} violation(s), {len(warns)} avertissement(s)")
    if errs:
        print("KO - build rejete.")
        return 1
    print("OK - conforme.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(main())
