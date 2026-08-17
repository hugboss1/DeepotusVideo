# -*- coding: utf-8 -*-
# scripts/qa/inventory_bundle.py
"""Inventaire mecanique du bundle compile — la preuve de non-regression.

Pourquoi : le bundle de PROD est un artefact minifie de 1,3 Mo sur 11 885
lignes dont une seule (la 147) porte tout le hub Game Assets. Constater « a
l'oeil » qu'un patch n'a rien casse est impossible. Ce script produit un
instantane chiffre, comparable octet pour octet avant / apres un patch :

  * taille, sha1, fins de ligne (CRLF / LF isole / CR isole) ;
  * inventaire des fonctions : nombre de declarations, nombre de noms
    distincts, sha1 de la liste triee des noms — un patcher qui n'ajoute
    aucune fonction DOIT laisser ces trois valeurs identiques ;
  * hub Game Assets : ids d'onglets dans l'ordre, etats acceptes au montage
    et par le relais d'evenement, branches du panneau, iframes dans l'ordre,
    cles React ;
  * comptes d'ancres nommees (les 5 du patcher cardforge + marqueurs).

Aucune ancre n'est jamais imprimee (console Windows cp1252, libelles a
emoji) : seuls son NOM et son COMPTE sortent.

Recette du sha1 des fonctions, gelee ici :
    regex   r"function\\s+([A-Za-z_$][\\w$]*)\\s*\\("
    donnee  "\\n".join(sorted(set(noms)))   encodee en utf-8
Elle est stable, pas canonique : c'est la comparaison AVANT / APRES qui fait
foi, pas la valeur absolue.

Run :
    python scripts/qa/inventory_bundle.py
    python scripts/qa/inventory_bundle.py --root <dir>
    python scripts/qa/inventory_bundle.py --json
    python scripts/qa/inventory_bundle.py --out avant.json
    python scripts/qa/inventory_bundle.py --diff avant.json   # rc=1 si regression
"""
import hashlib
import json
import pathlib
import re
import sys

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")

FUNC_RE = re.compile(r"function\s+([A-Za-z_$][\w$]*)\s*\(")

# Ancres nommees : NOM -> texte. Jamais imprimees, seulement comptees.
ANCHORS = {
    # les 5 ancres du patcher cardforge, etat PRE-patch (attendu : 1)
    "K1-init-state":
        'return t==="sprites"||t==="tiles"||t==="studio3d"||t==="materials"'
        '?t:"3d"}',
    "K2-relay-event":
        'if(d.subtab==="sprites"||d.subtab==="3d"||d.subtab==="tiles"'
        '||d.subtab==="studio3d"||d.subtab==="materials")setTab(d.subtab)',
    "K3-tab-btn": 'tb("materials","✨ Matières")]},"tabs")',
    "K4-cards-pane":
        '}},"pmf"):r.jsx("iframe",{src:"/studio3d/",title:"3D Studio",',
    "K5-nav-desc": 'desc:"3D studio, sprites, tuiles & matières"',
    # marqueurs POST-patch (attendu : 0 avant, 1 apres)
    "MARK-cardforge-src": 'src:"/cardforge/"',
    "MARK-cards-tab": 'tb("cards"',
    "MARK-key-pcf": '},"pcf")',
    # sondes de stabilite (attendu : 1 avant ET apres)
    "STABLE-screen-switch": 's==="assets3d"&&r.jsx(DzGameAssetsHub,{variant:e})',
    "STABLE-key-p3d": '},"p3d")',
    "STABLE-key-p2d": '},"p2d")',
    "STABLE-key-ptl": '},"ptl")',
    "STABLE-key-pmf": '},"pmf")',
    "STABLE-key-ps3": '},"ps3")',
    "STABLE-mf-iframe": 'src:"/materialforge/"',
}

# Champs dont un changement = REGRESSION (utilises par --diff).
INVARIANTS = [
    ("functions", "declarations"),
    ("functions", "distinct"),
    ("functions", "sha1_names"),
    ("anchors", "STABLE-screen-switch"),
    ("anchors", "STABLE-key-p3d"),
    ("anchors", "STABLE-key-p2d"),
    ("anchors", "STABLE-key-ptl"),
    ("anchors", "STABLE-key-pmf"),
    ("anchors", "STABLE-key-ps3"),
    ("anchors", "STABLE-mf-iframe"),
    ("eol", "lf_isole"),
    ("eol", "cr_isole"),
]

HUB_START = "function DzGameAssetsHub"


def resolve_bundle(args):
    if "--bundle" in args:
        return pathlib.Path(args[args.index("--bundle") + 1]).resolve()
    if "--root" in args:
        root = pathlib.Path(args[args.index("--root") + 1]).resolve()
    else:
        here = pathlib.Path(".").resolve()
        root = here if (here / REL_BUNDLE).is_file() else \
            pathlib.Path(__file__).resolve().parent.parent.parent
    return root / REL_BUNDLE


def _match(s, i, opener, closer):
    """s[i] == opener -> index de la fermeture appariee. Ignore le contenu
    des chaines ' " ` (le hub minifie n'a pas de litteral regex)."""
    depth, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "\"'`":
            q, i = c, i + 1
            while i < n and s[i] != q:
                i += 2 if s[i] == "\\" else 1
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n - 1


def hub_region(s):
    """Le corps complet de DzGameAssetsHub, par appariement d'accolades.

    Borner a « la fonction suivante » ne marche PAS : le composant contient
    des fonctions imbriquees (postSrc, h, tb) et la region serait tronquee
    avant la rangee d'onglets. On saute d'abord la liste de parametres
    destructures `({variant:e})`, dont les accolades ne sont pas le corps.
    """
    i = s.find(HUB_START)
    if i < 0:
        return ""
    par = s.index("(", i)
    body = s.index("{", _match(s, par, "(", ")") + 1)
    return s[i:_match(s, body, "{", "}") + 1]


def inventory(bundle):
    raw = bundle.read_bytes()
    s = bundle.read_text(encoding="utf-8", newline="")
    crlf = raw.count(b"\r\n")
    names = FUNC_RE.findall(s)
    uniq = sorted(set(names))
    hub = hub_region(s)

    return {
        "file": {
            "path": str(bundle),
            "bytes": len(raw),
            "sha1": hashlib.sha1(raw).hexdigest(),
            "chars_raw": len(s),
            "chars_universal": len(s) - crlf,
            "lines": len(s.split("\r\n")) if crlf else len(s.split("\n")),
        },
        "eol": {
            "crlf": crlf,
            "lf_isole": raw.count(b"\n") - crlf,
            "cr_isole": raw.count(b"\r") - crlf,
        },
        "functions": {
            "regex": FUNC_RE.pattern,
            "declarations": len(names),
            "distinct": len(uniq),
            "sha1_names": hashlib.sha1(
                "\n".join(uniq).encode("utf-8")).hexdigest(),
            "sha1_recipe": "sha1('\\n'.join(sorted(set(names))).utf-8)",
        },
        "hub": {
            "region_chars": len(hub),
            "tabs": re.findall(r'tb\("([A-Za-z0-9_]+)"', hub),
            "init_states": re.findall(r't==="([A-Za-z0-9_]+)"', hub),
            "relay_states": sorted(set(
                re.findall(r'd\.subtab==="([A-Za-z0-9_]+)"', hub))),
            "pane_branches": re.findall(r'tab==="([A-Za-z0-9_]+)"\?', hub),
            "iframes": re.findall(r'"iframe",\{src:"([^"]+)"', hub),
            "react_keys": re.findall(r'\},"(p[a-z0-9]{2})"\)', hub),
        },
        "iframes_bundle": re.findall(r'"iframe",\{src:"([^"]+)"', s),
        "anchors": {k: s.count(v) for k, v in ANCHORS.items()},
    }


def render(inv):
    f, e, fn, h = inv["file"], inv["eol"], inv["functions"], inv["hub"]
    out = []
    out.append("=== FICHIER =========================================")
    out.append(f"  path            {f['path']}")
    out.append(f"  octets          {f['bytes']}")
    out.append(f"  sha1            {f['sha1']}")
    out.append(f"  caracteres      {f['chars_raw']} (newline='') / "
               f"{f['chars_universal']} (universel)")
    out.append(f"  lignes          {f['lines']}")
    out.append("=== FINS DE LIGNE ===================================")
    out.append(f"  CRLF            {e['crlf']}")
    out.append(f"  LF isole        {e['lf_isole']}   (doit rester 0)")
    out.append(f"  CR isole        {e['cr_isole']}   (doit rester 0)")
    out.append("=== FONCTIONS =======================================")
    out.append(f"  declarations    {fn['declarations']}")
    out.append(f"  noms distincts  {fn['distinct']}")
    out.append(f"  sha1 des noms   {fn['sha1_names']}")
    out.append(f"  recette         {fn['sha1_recipe']}")
    out.append("=== HUB GAME ASSETS =================================")
    out.append(f"  onglets         {h['tabs']}")
    out.append(f"  etats montage   {h['init_states']}")
    out.append(f"  etats relais    {h['relay_states']}")
    out.append(f"  branches        {h['pane_branches']}")
    out.append(f"  iframes (hub)   {h['iframes']}")
    out.append(f"  cles React      {h['react_keys']}")
    out.append(f"  iframes bundle  {inv['iframes_bundle']}")
    out.append("=== ANCRES (comptes, texte jamais imprime) ==========")
    for k in ANCHORS:
        out.append(f"  {k:24s} {inv['anchors'][k]}")
    return "\n".join(out)


def diff(prev, cur):
    """Renvoie (regressions, changements) — deux listes de lignes."""
    regs, chg = [], []
    for sec, key in INVARIANTS:
        a, b = prev.get(sec, {}).get(key), cur.get(sec, {}).get(key)
        if a != b:
            regs.append(f"  REGRESSION {sec}.{key} : {a} -> {b}")
    for sec in ("file", "eol", "functions", "hub", "anchors"):
        pa, cb = prev.get(sec, {}), cur.get(sec, {})
        for key in sorted(set(pa) | set(cb)):
            if (sec, key) in INVARIANTS or key in ("path", "sha1_recipe",
                                                   "regex"):
                continue
            if pa.get(key) != cb.get(key):
                chg.append(f"  {sec}.{key} : {pa.get(key)} -> {cb.get(key)}")
    if prev.get("iframes_bundle") != cur.get("iframes_bundle"):
        chg.append(f"  iframes_bundle : {prev.get('iframes_bundle')} -> "
                   f"{cur.get('iframes_bundle')}")
    return regs, chg


def main():
    args = sys.argv[1:]
    bundle = resolve_bundle(args)
    if not bundle.is_file():
        print(f"bundle introuvable : {bundle}", file=sys.stderr)
        return 2
    inv = inventory(bundle)

    if "--out" in args:
        p = pathlib.Path(args[args.index("--out") + 1]).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(inv, indent=2, ensure_ascii=True),
                     encoding="utf-8")
        print(f"instantane ecrit -> {p}")

    if "--diff" in args:
        p = pathlib.Path(args[args.index("--diff") + 1]).resolve()
        prev = json.loads(p.read_text(encoding="utf-8"))
        regs, chg = diff(prev, inv)
        print(f"=== DIFF vs {p.name} ===")
        for line in chg or ["  (aucun changement hors invariants)"]:
            print(line)
        if regs:
            print("--- INVARIANTS ROMPUS ---")
            for line in regs:
                print(line)
            print(f"KO : {len(regs)} regression(s).")
            return 1
        print("OK : tous les invariants tiennent.")
        return 0

    if "--json" in args:
        print(json.dumps(inv, indent=2, ensure_ascii=True))
    else:
        print(render(inv))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(main())
