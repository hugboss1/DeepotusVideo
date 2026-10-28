# -*- coding: utf-8 -*-
"""t313 (28/10/2026) (C3 Inspiration, tâches 5 et 6) — banc de l'écran : le module partagé dz-inspiration.js, ses
textes, sa balise dans la SPA et le maillon de queue `dzinspiration` (bouton « Depuis une inspiration » du Planificateur).
Sections :
  1. module : copie dist identique OCTET POUR OCTET, balise classique après dz-whatsapp-espace.js dans
     frontend/dist/index.html, aucun innerHTML ni confirm()/alert() natif, confirmations par __dzDialogue ;
  2. textes : clés inspiration.* FR et EN non vides, dictionnaire assemblé à jour (i18n_assembler --check) ;
  3. maillon : marqueur ×1, bouton posé juste après « Nouveau post » et hors de tout bloc de couche, aller-retour exact
     (`defaire`), comptes figés, CRLF intact, `--check` dit « déjà appliqué », l'inverse `avant_dzinspiration` en tête
     de `avant_whatsapppage` ;
  4. la boîte jouée sous node (frontend/shared/qa/inspiration.test.mjs) : verte.
Run (depuis backend/) : & $PY tests/test_inspiration_ecran.py"""
import json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
REPO = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(REPO / "scripts"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


PY = sys.executable
SRC = REPO / "frontend" / "shared" / "dz-inspiration.js"
DIST = REPO / "frontend" / "dist" / "shared" / "dz-inspiration.js"
INDEX = REPO / "frontend" / "dist" / "index.html"
BUNDLE = REPO / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"

print("[1] module")
check("1a copie dist identique octet pour octet", SRC.is_file() and DIST.is_file() and SRC.read_bytes() == DIST.read_bytes())
html = INDEX.read_text(encoding="utf-8")
balise = '<script src="/shared/dz-inspiration.js"></script>'
check("1b balise classique (pas module) une fois", html.count(balise) == 1)
check("1c après dz-whatsapp-espace.js, avant </head>", html.find('/shared/dz-whatsapp-espace.js') < html.find(balise) < html.find("</head>"))
code = SRC.read_text(encoding="utf-8")
check("1d aucun innerHTML, confirm( ou alert( natifs", not re.search(r"\.innerHTML\b|[^.\w]confirm\(|[^.\w]alert\(", code))
check("1e confirmations par window.__dzDialogue.confirmer", "window.__dzDialogue" in code and "d.confirmer(" in code)
check("1e' (preuve à l'écran) éléments masqués vraiment invisibles : règle [data-dz-insp][hidden] posée, et tout ce qui "
      "est masqué porte data-dz-insp", "[data-dz-insp][hidden]{display:none!important}" in code
      and '"data-dz-insp": "ligne-image"' in code)
check("1f seule route d'image permise : /api/images/generate", 'ROUTE_IMAGE = "/api/images/generate"' in code
      and "img.route !== ROUTE_IMAGE" in code)

print("[2] textes")
dico = json.loads((REPO / "frontend" / "shared" / "i18n" / "inspiration.json").read_text(encoding="utf-8"))
check("2a au moins 60 clés inspiration.*, FR et EN non vides", len(dico) >= 60 and all(k.startswith("inspiration.") and v.get("fr") and v.get("en")
                                                                                     for k, v in dico.items()), len(dico))
cles = set(re.findall(r'T\("(inspiration\.[a-z_.]+[a-z_])"', code)) | {"inspiration.planif.bouton", "inspiration.planif.aide"}
check("2b chaque clé employée existe", cles <= set(dico), sorted(cles - set(dico)))
r = subprocess.run([PY, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True, text=True, encoding="utf-8")
check("2c dictionnaire assemblé à jour", r.returncode == 0, r.stdout + r.stderr)
check("2d mêmes variables FR/EN", all(set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])) for v in dico.values()))

print("[3] maillon dzinspiration")
import patch_bundle_dzinspiration as M          # noqa: E402
import _i18n_l1_aide as AIDE                    # noqa: E402
octets = BUNDLE.read_bytes()
B = octets.decode("utf-8-sig")
check("3a marqueur ×1", B.count(M.MARKER) == 1, B.count(M.MARKER))
check("3b bouton juste après « Nouveau post »", M._NOUVEAU + M.MARKER + M.BOUTON in B)
check("3c bouton hors de tout bloc de couche", M.hors_couche(B, M.MARKER + M.BOUTON))
check("3d le bouton appelle window.__dzInspiration.ouvrir, libellé et aide par dzT, icône Glyph existante",
      'dzT("inspiration.planif.bouton")' in M.BOUTON and 'dzT("inspiration.planif.aide")' in M.BOUTON and M.OUVRIR in M.BOUTON
      and 'icon:"dz-media-image"' in M.BOUTON)
avant = M.defaire(B)
check("3e aller-retour exact", M.appliquer(avant) == B and M.MARKER not in avant)
check("3f comptes figés", all(B.count(j) == n for j, n in (("x.useState(", 731), ("v2.8.0", 4), ("DzTracks", 181),
                                                            (M.CONFIRMER, 30))))
check("3g CRLF intact (octets)", octets.count(b"\n") == octets.count(b"\r\n"))
r = subprocess.run([PY, str(REPO / "scripts" / "patch_bundle_dzinspiration.py"), "--check"], capture_output=True, text=True,
                   encoding="utf-8")
check("3h --check : déjà appliqué", r.returncode == 0 and "déjà appliqué" in r.stdout, r.stdout + r.stderr)
check("3i aucun .bak laissé", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzinspiration")).exists())
# fusion t320 : dzdiffusion (t328) est rejoué APRÈS dzinspiration ; avant_dzinspiration le défait d'abord
_sans_diff = AIDE.avant_dzdiffusion(B) if hasattr(AIDE, "avant_dzdiffusion") else B
check("3j inverse : avant_dzinspiration défait le maillon (après la queue)", AIDE.avant_dzinspiration(B) == M.defaire(_sans_diff))
check("3k inverse en tête de avant_whatsapppage", M.MARKER not in AIDE.avant_whatsapppage(B)
      and "/*whatsapppage*/" not in AIDE.avant_whatsapppage(B))
src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
# fusion t320 : dzinspiration est rejoué APRÈS dzcapture (t315) ; son inverse ouvre donc avant_dzcapture
fw = src_aide[src_aide.find("def avant_dzcapture("):]
check("3l l'appel est la première instruction de avant_dzcapture",
      0 <= fw.find("avant_dzinspiration(bundle)") < fw.find("_m.MARKER"))

print("[4] la boîte sous node")
r = subprocess.run(["node", str(REPO / "frontend" / "shared" / "qa" / "inspiration.test.mjs")], capture_output=True, text=True,
                   encoding="utf-8")
check("4a inspiration.test.mjs vert", r.returncode == 0 and " 0 failed" in r.stdout, (r.stdout + r.stderr)[-600:])

print(f"\n=== {ok} passed, {fail} failed ===")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
