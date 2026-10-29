# -*- coding: utf-8 -*-
"""Jetons communs de la charte (t370, 29/10/2026) — `frontend/shared/dz-charte.css`, UNE feuille chargée par la
coque ET par chaque lab. Relevé et règles : docs/superpowers/specs/2026-10-29-charte-jetons-releve.md.
Sections :
  [J] la feuille : jetons attendus, uniquement des propriétés personnalisées sur :root, tout passe par des
      variables (t382/t383 redéfinissent les jetons de base), --radius:0 et rayons hérités rebranchés ;
  [C] copie identique dans frontend/dist/shared ;
  [L] chargée PARTOUT : la coque (lien APRÈS la feuille du bundle) et chaque page de lab, par lien ou par une
      chaîne d'@import valide (un @import après une règle est ignoré par le navigateur) ;
  [R] angles vifs : aucun rayon littéral > 0 dans les feuilles partagées hors exceptions LISTÉES, aucune
      redéfinition de --r-sm/--r/--r-lg autre que var(--radius), et CLIQUET par zone (le compte de rayons
      littéraux ne peut que baisser ; t374 l'amène à 0).
Run (depuis backend/) : & $PY tests/test_charte_jetons.py"""
import json, pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(RACINE / "scripts"))

import charte_releve  # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


FRONT = RACINE / "frontend"
CHARTE = FRONT / "shared" / "dz-charte.css"
COPIE = FRONT / "dist" / "shared" / "dz-charte.css"
TOKENS = FRONT / "shared" / "deepotus.tokens.css"
PLAFOND = RACINE / "scripts" / "charte_rayons_plafond.json"
URL = "/shared/dz-charte.css"


def _sans_commentaires(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _lire(p):
    return p.read_text(encoding="utf-8") if p.is_file() else ""


SRC = _lire(CHARTE)
NUE = _sans_commentaires(SRC)
DECL = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", NUE))

# ── [J] la feuille ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[J] la feuille de jetons")
ATTENDUS = (["--fg-1", "--fg-2", "--fg-3", "--fg-4", "--fg-accent", "--fg-on-accent",
             "--font-ui", "--font-mono", "--font-display", "--fs-1", "--fs-2", "--fs-3", "--fs-4", "--fs-5",
             "--fw-1", "--fw-2", "--fw-3", "--pad-1", "--pad-2", "--pad-3", "--pad-4", "--radius",
             "--r-sm", "--r", "--r-lg"])
check("J1 la feuille existe", CHARTE.is_file())
check("J2 tous les jetons attendus sont déclarés", all(k in DECL for k in ATTENDUS),
      [k for k in ATTENDUS if k not in DECL])
blocs = re.findall(r"([^{}]+)\{([^{}]*)\}", NUE)
check("J3 un seul bloc, sur :root (aucun sélecteur d'élément : la charger ne casse rien)",
      len(blocs) == 1 and blocs[0][0].strip() == ":root", [b[0].strip() for b in blocs])
check("J4 le bloc ne contient QUE des propriétés personnalisées",
      bool(blocs) and all(d.strip().startswith("--") for d in blocs[0][1].split(";") if d.strip()),
      [d.strip()[:40] for d in (blocs[0][1].split(";") if blocs else []) if d.strip() and not d.strip().startswith("--")])
check("J5 couleurs et polices passent par une variable de base (t382/t383 les redéfinissent)",
      all(DECL.get(k, "").strip().startswith("var(--") for k in
          ["--fg-1", "--fg-2", "--fg-3", "--fg-4", "--fg-accent", "--fg-on-accent",
           "--font-ui", "--font-mono", "--font-display"]),
      {k: DECL.get(k) for k in ["--fg-1", "--fg-2", "--fg-3", "--fg-4", "--font-ui"]})
check("J6 --fg-1..4 suivent les quatre encres relevées, dans l'ordre",
      [re.match(r"var\((--[\w-]+)", DECL.get(f"--fg-{i}", "") or "x") and
       re.match(r"var\((--[\w-]+)", DECL[f"--fg-{i}"]).group(1) for i in range(1, 5)]
      == ["--ink-strong", "--ink", "--ink-soft", "--ink-muted"])
check("J7 --radius vaut 0", DECL.get("--radius", "").strip() in ("0", "0px"), DECL.get("--radius"))
check("J8 --r-sm, --r, --r-lg rebranchés sur var(--radius)",
      all(DECL.get(k, "").strip() == "var(--radius)" for k in ("--r-sm", "--r", "--r-lg")))
check("J9 --r-pill n'est pas touché (pastilles rondes)", "--r-pill" not in DECL)
check("J10 espacements en base 4, croissants",
      [DECL.get(f"--pad-{i}", "").strip() for i in range(1, 5)] == ["4px", "8px", "12px", "16px"])
_tailles = [float(re.sub(r"px$", "", DECL.get(f"--fs-{i}", "0").strip()) or 0) for i in range(1, 6)]
check("J11 cinq tailles strictement croissantes, en px", _tailles == sorted(set(_tailles)) and _tailles[0] > 0, _tailles)

# ── [C] copie ───────────────────────────────────────────────────────────────────────────────────────────────────────
print("[C] copie servie")
check("C1 frontend/dist/shared/dz-charte.css est identique à la source",
      COPIE.is_file() and COPIE.read_bytes() == CHARTE.read_bytes())

# ── [L] chargée partout ─────────────────────────────────────────────────────────────────────────────────────────────
print("[L] chargée par la coque et par chaque lab")
_REGLE = re.compile(r"@import\s+(?:url\()?\s*[\"']?([^\"')\s;]+)[\"']?\s*\)?\s*;")


def _resoudre(url, depuis):
    """Chemin disque d'une URL de feuille vue depuis le fichier `depuis` (servie : /shared → frontend/shared)."""
    if url.startswith("http"):
        return None
    if url.startswith("/"):
        p = FRONT / url.lstrip("/")
        return p if p.is_file() else (FRONT / "dist" / url.lstrip("/"))
    return (depuis.parent / url).resolve()


def _imports_valides(p):
    """@import pris en compte par le navigateur : seulement ceux qui précèdent toute autre règle."""
    css = _sans_commentaires(_lire(p))
    res, pos = [], 0
    while True:
        m = re.compile(r"\s*(@charset[^;]*;|@layer[^;{]*;)?\s*").match(css, pos)
        pos = m.end()
        m = _REGLE.match(css, pos)
        if not m:
            return res
        res.append(m.group(1))
        pos = m.end()


def charge_charte(css, vus=None):
    vus = vus or set()
    if css is None or css in vus or not css.is_file():
        return False
    vus.add(css)
    if css.name == "dz-charte.css":
        return True
    return any(u.endswith("dz-charte.css") or charge_charte(_resoudre(u, css), vus) for u in _imports_valides(css))


def feuilles_de_page(html):
    src = _lire(html)
    liens = re.findall(r"<link\b[^>]*rel=[\"']stylesheet[\"'][^>]*>", src)
    return [re.search(r"href=[\"']([^\"']+)", l).group(1) for l in liens if re.search(r"href=[\"']([^\"']+)", l)]


PAGES = sorted(p for p in FRONT.rglob("*.html")
               if not re.search(r"/(qa|aide|node_modules|src)/", p.as_posix())
               and p.parent != FRONT and "/dist/" not in p.as_posix())
check("L0 pages de labs trouvées (au moins 14)", len(PAGES) >= 14, [p.relative_to(FRONT).as_posix() for p in PAGES])
for page in PAGES:
    ok_page = any(h.endswith("dz-charte.css") or charge_charte(_resoudre(h, page)) for h in feuilles_de_page(page))
    check(f"L1 {page.relative_to(FRONT).as_posix()} charge la charte", ok_page, feuilles_de_page(page))

COQUE = FRONT / "dist" / "index.html"
_feuilles = feuilles_de_page(COQUE)
_i_bundle = next((i for i, h in enumerate(_feuilles) if re.search(r"/assets/index-.*\.css$", h)), -1)
_i_charte = next((i for i, h in enumerate(_feuilles) if h == URL), -1)
check("L2 la coque lie la charte une fois", _feuilles.count(URL) == 1, _feuilles)
check("L3 … APRÈS la feuille du bundle (sinon --r-sm:6px du bundle l'emporte)", _i_charte > _i_bundle >= 0,
      (_i_bundle, _i_charte))
check("L4 deepotus.tokens.css l'importe en tête", URL in _imports_valides(TOKENS), _imports_valides(TOKENS))

# ── [R] angles vifs ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] angles vifs")
# Exceptions LISTÉES (spec t370 §Exceptions) : sélecteur → raison.
EXCEPTIONS = {".dt-dot": "pastille d'état ronde (ok / off / idle)"}


def rayons_litteraux(css):
    """(sélecteur, valeur) des border-radius STRICTEMENT > 0 (même ronds) hors sélecteurs d'EXCEPTIONS."""
    res = []
    for sel, corps in re.findall(r"([^{}]+)\{([^{}]*)\}", _sans_commentaires(css)):
        if sel.strip() in EXCEPTIONS:
            continue
        for val in re.findall(r"border(?:-\w+-\w+)?-radius\s*:\s*([^;]+)", corps):
            v = val.replace("!important", "").strip()
            if not re.fullmatch(r"(0(px)?\s*)+|var\(--(radius|r|r-sm|r-lg)\)", v):
                res.append((sel.strip()[:40], v))
    return res


check("R1 la charte ne déclare aucun border-radius", "border-radius" not in NUE)
check("R2 deepotus.tokens.css : aucun rayon littéral hors exceptions listées",
      not rayons_litteraux(_lire(TOKENS)), rayons_litteraux(_lire(TOKENS)))
_redef = []
for f in list(FRONT.rglob("*.css")):
    pf = f.as_posix()
    if re.search(r"/(node_modules|src|qa)/", pf) or re.search(r"/dist/assets/", pf):
        continue  # src/ n'est pas servi ; la feuille du bundle prébâti est surchargée par la charte (L3)
    for k, v in re.findall(r"(--r(?:-sm|-lg)?)\s*:\s*([^;}]+)", _sans_commentaires(_lire(f))):
        if v.strip() != "var(--radius)":
            _redef.append(f"{f.relative_to(FRONT).as_posix()} {k}:{v.strip()}")
check("R3 aucune feuille servie ne redéfinit --r-sm/--r/--r-lg autrement que par var(--radius)", not _redef, _redef)

PLAF = json.loads(_lire(PLAFOND) or "{}")
MESURE = charte_releve.rayons_par_zone()
check("R4 le cliquet couvre la coque et chaque lab", set(PLAF) == set(MESURE), sorted(set(PLAF) ^ set(MESURE)))
for zone, n in sorted(MESURE.items()):
    check(f"R5 {zone} : {n} rayon(s) littéral(aux) ≤ plafond {PLAF.get(zone)}",
          PLAF.get(zone) is not None and n <= PLAF[zone])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
