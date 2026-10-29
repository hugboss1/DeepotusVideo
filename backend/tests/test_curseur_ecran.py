# -*- coding: utf-8 -*-
"""t373 (29/10/2026, lot A « Finitions esthétiques », décision D1) — banc des CURSEURS façon table de mixage
(frontend/shared/dz-curseur.css, maillon scripts/patch_bundle_dzcurseur.py, plan
docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md).
  1. la feuille commune : copie octet pour octet, règles sous :where() (spécificité nulle : les mises en page locales
     gardent la main), rainure 2-3 px encastrée, bouton rectangulaire strié, rempli --cat sinon --amber discret (60 %),
     focus clavier visible, graduations optionnelles, variante verticale ; aucun rayon littéral, aucune couleur en dur ;
  2. les branchements : la coque (après dz-charte) et chaque lab (par deepotus.tokens.css, atelier.css, spritelab.css) ;
     tout lab qui pose un curseur charge la feuille ;
  3. UN SEUL STYLE : aucune autre feuille, aucun maillon, aucune couche ni le bundle ne dessine plus de pouce ou de
     piste de curseur (le lecteur t372 s'aligne sur la règle commune) ;
  4. le curseur de base de la coque (`Oe`, 37 usages : Studio, Quick, Modèles, News, Réglages) : plus de pastille ronde
     ni de dégradé cyan → violet, un vrai input visible à la charte (maillon de queue dzcurseur, inverse avant_dzcurseur) ;
  5. le Montage : rails MIXAGE et faders d'en-tête au style fader, masque (X/Y/W/H/Doux) et gain = la règle commune ;
  6. Son & VFX › Pistes : la console des pistes en faders VERTICAUX gradués.
Run (depuis backend/) : & $PY tests/test_curseur_ecran.py"""
import pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
REPO = _ICI.parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(_ICI))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


FRONT = REPO / "frontend"
SRC = FRONT / "shared" / "dz-curseur.css"
DIST = FRONT / "dist" / "shared" / "dz-curseur.css"
css = SRC.read_text(encoding="utf-8") if SRC.exists() else ""
css_net = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

def regle(selecteur_re):
    """Le corps de la première règle dont le sélecteur correspond."""
    m = re.search(r"(?:^|})\s*([^{}]*" + selecteur_re + r"[^{}]*)\{([^}]*)\}", css_net)
    return m.group(2) if m else ""

print("[1] la feuille commune")
check("1.1 la feuille existe et sa copie dans frontend/dist/shared est identique",
      SRC.exists() and DIST.exists() and DIST.read_bytes() == SRC.read_bytes())
selecteurs = re.findall(r"(?:^|})\s*([^{}@]+)\{", css_net)
_nus = [s.strip() for s in selecteurs if "input[type=range]" in s and ":where(" not in s]
check("1.2 toute règle générale de curseur passe par :where() (spécificité nulle)", selecteurs and not _nus, _nus)
base = regle(r":where\(input\[type=range\]\)")
check("1.3 apparence native retirée, fond transparent, débordement coupé (rempli dessiné par le bouton)",
      "appearance:none" in base and "-webkit-appearance:none" in base and "overflow:hidden" in base
      and "background:transparent" in base)
_piste = re.search(r"--dz-curseur-piste:\s*(\d+)px", css_net)
check("1.4 rainure fine de 2 à 3 px", _piste and 2 <= int(_piste.group(1)) <= 3, _piste and _piste.group(0))
track = regle(r"::-webkit-slider-runnable-track")
check("1.5 rainure encastrée : fond --dz-curseur-rainure (--bg-base), ombre intérieure, filet --stroke",
      "height:var(--dz-curseur-piste)" in track and "background:var(--dz-curseur-rainure)" in track
      and "inset" in track and "var(--stroke)" in track and "--dz-curseur-rainure:var(--bg-base)" in css_net)
thumb = regle(r"::-webkit-slider-thumb")
check("1.6 bouton rectangulaire strié, centré sur la rainure",
      "width:var(--dz-curseur-bouton-l)" in thumb and "height:var(--dz-curseur-bouton-h)" in thumb
      and "repeating-linear-gradient(var(--dz-curseur-stries,to bottom)" in thumb and "border-radius:var(--radius)" in thumb
      and "margin-top:calc((var(--dz-curseur-piste) - var(--dz-curseur-bouton-h)) / 2)" in thumb)
check("1.7 rempli discret : teinte de catégorie (--cat) sinon --amber, à 60 %, dessiné jusqu'au bouton sans script",
      "--dz-curseur-rempli:color-mix(in srgb,var(--cat,var(--amber)) 60%,transparent)" in css_net
      and "border-image:linear-gradient(90deg,var(--dz-curseur-rempli) 50%,transparent 0)" in thumb)
check("1.8 Firefox : même rainure, rempli natif (-moz-range-progress), même bouton",
      "::-moz-range-track" in css_net and "::-moz-range-progress" in css_net and "::-moz-range-thumb" in css_net)
focus = regle(r":focus-visible")
check("1.9 focus clavier visible : contour --amber", "outline:1px solid var(--amber)" in focus, focus)
check("1.10 désactivé : estompé, curseur par défaut", re.search(r":disabled\)?\s*\{[^}]*opacity:", css_net) is not None)
gradue = regle(r"\.dz-gradue")
check("1.11 graduations optionnelles (.dz-gradue, pas réglable par --dz-graduations)",
      "repeat-x" in gradue and "var(--dz-graduations,10)" in gradue)
vert = regle(r"\.dz-curseur-vertical")
check("1.12 variante verticale (.dz-curseur-vertical) : même dessin tourné, place réservée en hauteur",
      "rotate(-90deg)" in vert and "var(--dz-curseur-longueur)" in vert and "--dz-curseur-stries:to right" in vert)
_rayons = re.findall(r"border-radius:\s*([^;}]*)", css_net)
check("1.13 chaque rayon vaut var(--radius)", _rayons and all(r.strip() == "var(--radius)" for r in _rayons), _rayons)
check("1.14 aucune couleur en dur (#hex, rgb, hsl, nom de couleur)",
      not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|(?<![\w-])(white|black|red|gray|grey)(?![\w-])", css_net))
_vars = set(re.findall(r"var\(--([a-z0-9-]+)", css_net))
_hors = sorted(v for v in _vars if not re.match(r"(fg-[1-4]|pad-[1-4]|fs-[1-5]|radius|amber|cat|bg-[a-z0-9-]+|stroke(-strong)?|dz-curseur-[a-z-]+|dz-graduations|mod)$", v))
check("1.15 seulement des jetons de la charte (--fg-*, --fs-*, --pad-*, --radius) et de base (--amber, --cat, --bg-*, --stroke)", not _hors, _hors)

print("\n[2] les branchements")
LIEN = '<link rel="stylesheet" href="/shared/dz-curseur.css">'
coque = (FRONT / "dist" / "index.html").read_text(encoding="utf-8")
check("2.1 la coque charge la feuille une fois, après la feuille du bundle et dz-charte",
      coque.count(LIEN) == 1 and coque.index('href="/shared/dz-charte.css"') < coque.index(LIEN)
      and coque.index("/assets/index-") < coque.index(LIEN))
IMPORT = '@import url("/shared/dz-curseur.css");'
for f in (FRONT / "shared" / "deepotus.tokens.css", FRONT / "dist" / "shared" / "deepotus.tokens.css",
          FRONT / "atelier" / "atelier.css", FRONT / "spritelab" / "spritelab.css"):
    t = re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)   # un @import en commentaire ne charge rien
    tete = t.split("{", 1)[0]
    check(f"2.2 {f.relative_to(REPO).as_posix()} : @import en tête, après dz-charte",
          t.count(IMPORT) == 1 and IMPORT in tete and tete.index("dz-charte.css") < tete.index(IMPORT))
RANGE = re.compile(r"""type\s*[=:]\s*["']?range\b|input\[type=["']?range|\.type\s*=\s*["']range""")
EXCLUS = ("vendor", "qa", "node_modules", "lib3d")
def porte_la_feuille(page: pathlib.Path) -> bool:
    vus, a_lire = set(), [m for m in re.findall(r'href="([^"]+\.css)"', page.read_text(encoding="utf-8"))]
    while a_lire:
        h = a_lire.pop()
        f = (FRONT / h.lstrip("/")) if h.startswith("/") else (page.parent / h)
        if h.endswith("dz-curseur.css"):
            return True
        if f in vus or not f.exists():
            continue
        vus.add(f)
        a_lire += re.findall(r'@import url\("([^"]+)"\)', re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S))
    return False
labs = {}
for lab in sorted(p for p in FRONT.iterdir() if p.is_dir() and p.name not in ("dist", "shared", "src", "patches", "node_modules")):
    if not (lab / "index.html").exists():
        continue
    for f in lab.rglob("*"):
        if f.suffix in (".js", ".html", ".css") and not any(x in f.parts for x in EXCLUS) and ".min." not in f.name \
                and RANGE.search(f.read_text(encoding="utf-8", errors="replace")):
            labs.setdefault(lab.name, []).append(f.name)
check("2.3 relevé : au moins 8 labs posent des curseurs", len(labs) >= 8, sorted(labs))
_sans = [l for l in labs if not porte_la_feuille(FRONT / l / "index.html")]
check("2.4 chaque lab qui pose un curseur charge la feuille commune", not _sans, _sans)

print("\n[3] un seul style")
PSEUDO = re.compile(r"::?-(webkit-slider-thumb|webkit-slider-runnable-track|moz-range-thumb|moz-range-track|moz-range-progress)")
autres = []
for f in list(FRONT.rglob("*.css")) + list(FRONT.rglob("*.js")) + list(FRONT.rglob("*.html")) + list((REPO / "scripts").glob("patch_bundle_*.py")):
    if any(x in f.parts for x in EXCLUS) or f.name == "dz-curseur.css" or ".min." in f.name or f.name.endswith(".bak"):
        continue
    if PSEUDO.search(f.read_text(encoding="utf-8", errors="replace")):
        autres.append(f.relative_to(REPO).as_posix())
check("3.1 aucune autre feuille, aucun module, aucun maillon ni le bundle ne dessine de pouce ou de piste", not autres, autres)
lecteur = (FRONT / "shared" / "dz-lecteur.js").read_text(encoding="utf-8")
check("3.2 le lecteur t372 s'aligne : plus de rempli scripté (--dz-lecteur-pos), ses curseurs suivent la règle commune",
      "--dz-lecteur-pos" not in lecteur and "slider" not in lecteur)
photolab = (FRONT / "photolab" / "photolab.css").read_text(encoding="utf-8")
vector = (FRONT / "vectorlab" / "vectorlab.css").read_text(encoding="utf-8")
mforge = (FRONT / "materialforge" / "materialforge.css").read_text(encoding="utf-8")
check("3.3 Vectorlab : les pistes colorées du vitrail gardent leur fond par les variables de la règle commune",
      re.search(r"\.vit-tsv\s*\{[^}]*--dz-curseur-rainure:\s*transparent", vector) is not None and "#nuH {" not in vector)
_poignee = re.search(r"\.vl-curseur-poignee\s*\{([^}]*)\}", vector)
_piste = re.search(r"\.vl-curseur-piste::before\s*\{([^}]*)\}", vector)
check("3.5 Vectorlab : <vl-curseur> (curseur maison) prend le dessin du fader : rainure 3 px encastrée, bouton strié",
      _poignee and "border-radius: var(--radius)" in _poignee.group(1) and "repeating-linear-gradient(to bottom" in _poignee.group(1)
      and _piste and "height: 3px" in _piste.group(1) and "inset" in _piste.group(1)
      and "vl-curseur:focus-visible { outline: 1px solid var(--amber)" in vector)
check("3.4 Material Forge : le repère du défaut reste, aligné sur le bouton de 8 px ; « modifié » teinte les stries",
      ".rng::after" in mforge and "calc(4px + (100% - 8px) * var(--dp, 0))" in mforge
      and re.search(r"\.prop\.mod \.rng input\[type=range\]\s*\{\s*--dz-curseur-strie:\s*var\(--mod\)", mforge) is not None)

print("\n[4] le curseur de base de la coque (Oe)")
B = next((FRONT / "dist" / "assets").glob("index-*.js"))
bundle = B.read_bytes().decode("utf-8")
i = bundle.find("function Oe({value:e")
oe = bundle[i:bundle.find("function jt(", i)] if i >= 0 else ""
check("4.1 le composant est trouvé", len(oe) > 200, len(oe))
check("4.2 plus de pastille ronde ni de dégradé cyan → violet ni d'input invisible",
      "var(--cyan), var(--violet)" not in oe and "borderRadius:999" not in oe and "opacity:0" not in oe)
check("4.3 un vrai input visible, à la charte (classe dz-curseur), nommé par son libellé",
      'r.jsx("input",{type:"range",className:"dz-curseur"' in oe and '"aria-label":a' in oe)
check("4.4 37 usages du composant intouchés", bundle.count("(Oe,{") == 37, bundle.count("(Oe,{"))
r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzcurseur.py"), "--check"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
check("4.5 le maillon est appliqué (--check)", r.returncode == 0 and "déjà appliqué" in r.stdout, (r.stdout + r.stderr)[-300:])
import patch_bundle_dzcurseur as M
import _i18n_l1_aide as AIDE
avant = AIDE.avant_dzcurseur(bundle)
check("4.6 l'inverse avant_dzcurseur défait le maillon, et le rejouer redonne le bundle à l'octet",
      M.MARKER not in avant and M.appliquer(avant) == AIDE.avant_dzecartes(bundle))   # t375 : dzecartes suit dzcurseur
src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
_mcp = src_aide[src_aide.index("def avant_dzmcp("):]
_mcp = _mcp[:_mcp.index("\ndef ", 5)]
check("4.7 avant_dzmcp défait d'abord dzcurseur (maillon posé après lui)", "bundle = avant_dzcurseur(bundle)" in _mcp)
check("4.8 aucune paire dans une couche __DZ_*_BEGIN__", all(M.hors_couche(bundle, z) for _a, z in M.PAIRES))

print("\n[5] le Montage : mixage, masque, gain")
rail = regle(r"\.svm-mixrail\s*$|\.svm-mixrail,") or regle(r"\.svm-mixrail")
check("5.1 rails MIXAGE : rainure encastrée aux variables du curseur, angles vifs",
      "height:var(--dz-curseur-piste" in rail and "border-radius:var(--radius)" in rail and "inset" in rail, rail)
bouton = regle(r"\.svm-mixfill::after")
check("5.2 rails MIXAGE et faders d'en-tête : bouton rectangulaire strié au bout du rempli",
      "repeating-linear-gradient(to bottom" in bouton and "border-radius:var(--radius)" in bouton
      and ".svm-thmixfill::after" in css_net)
check("5.3 rempli des rails à angles vifs (plus de pilule)", re.search(r"\.svm-mixfill[^{]*\{[^}]*border-radius:var\(--radius\)", css_net) is not None)
mcss = (FRONT / "dist" / "shared" / "montage.css").read_text(encoding="utf-8")
check("5.4 masque (X/Y/W/H/Doux) : aucun style local de pouce, la règle commune s'applique",
      re.search(r"dzm-gp-mr input\[type=range\]\{[^}]*(appearance|accent)", mcss) is None)
svm = (FRONT / "dist" / "shared" / "son-vfx-montage.css").read_text(encoding="utf-8")
check("5.5 gain et réglages du Montage (.svm-range) : la règle commune s'applique (aucun pouce local)",
      ".svm-range{" in svm and not PSEUDO.search(svm))

print("\n[6] Son & VFX › Pistes : console verticale")
vol = regle(r"\.dzsvp-stems \.dzsvp-vol")
check("6.1 les volumes des pistes sont des faders verticaux gradués",
      "rotate(-90deg)" in vol and "repeat-x" in vol and "--dz-curseur-stries:to right" in vol, vol)
check("6.2 chaque piste est une tranche de console (grille : M/S, fader, envoyer/télécharger, nom)",
      "grid-template-areas" in regle(r"\.dzsvp-stems > \.dzsvp-stem")
      and "flex-direction:row" in regle(r"div\.dzsvp-stems"))

print("\n[7] cliquet des rayons de la charte")
r = subprocess.run([sys.executable, str(_ICI / "test_charte_jetons.py")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=str(REPO / "backend"))
check("7.1 test_charte_jetons reste vert", r.returncode == 0, (r.stdout + r.stderr)[-600:])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
