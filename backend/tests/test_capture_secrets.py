# -*- coding: utf-8 -*-
"""t315 (28/10/2026) (D1, tâche 5) — le MASQUAGE de la capture couvre chaque secret (spec boîte à outils §8.2 : « le
banc vérifie que chaque champ type=password et chaque écran du coffre porte cette marque »).
Plan docs/superpowers/plans/2026-10-28-t315-capture.md.
[M] maillon dzcapture : marqueur une fois, aller-retour exact (défaire puis réappliquer = le livré), inverse
    `avant_dzcapture` en tête de `avant_whatsapppage`, hors de tout bloc de couche, épingles intactes, sections
    SECRETS figées et toutes présentes dans la navigation de Réglages ;
[C] couverture : chaque champ mot de passe des sources servies (bundle, frontend/shared, pages des labs) est un
    `input` de type password, donc couvert par SELECTEURS_SECRETS sans marque à poser ; les écrans de Réglages qui
    montrent une clé, un aperçu de clé, un identifiant OAuth, le coffre, l'appairage, les appareils ou un mot de
    passe d'archive portent data-dz-secret="ecran" ; aucune autre section ne le porte ;
[F] feuille et scène : CSS_MASQUE floute data-dz-secret ET type=password sous html[data-dz-capture], rend l'écran
    inerte ; l'enregistreur pose l'attribut et la feuille dans la page ET les cadres de même origine AVANT la
    première image ; le caviardage est posé par la scène elle-même.
Run (depuis backend/) : & $PY tests/test_capture_secrets.py"""
import pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import _i18n_l1_aide as AIDE                                        # noqa: E402
import patch_bundle_dzcapture as M                                  # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:600]}")


B = M.BUNDLE.read_bytes().decode("utf-8")
SH = REPO / "frontend" / "shared"
LOG = (SH / "dz-capture-logique.js").read_text("utf-8")
CAP = (SH / "dz-capture.js").read_text("utf-8")
SCN = (SH / "dz-capture-scene.js").read_text("utf-8")

print("[M] maillon dzcapture")
check("M1 marqueur une fois", B.count(M.MARKER) == 1)
avant = M.defaire(B) if M.MARKER in B else ""
check("M2 aller-retour exact : défaire puis réappliquer rend le livré", avant and M.appliquer(avant) == B)
check("M3 avant_dzcapture = défaire ; avant_whatsapppage passe d'abord par lui",
      AIDE.avant_dzcapture(B) == avant and M.MARKER not in AIDE.avant_whatsapppage(B))
check("M4 hors de tout bloc de couche, sans fin de ligne", all(M.hors_couche(B, z) and "\n" not in z for _a, z in M.PAIRES))
check("M5 épingles intactes (useState 731, v2.8.0 x4, DzTracks 181, confirmations 30)",
      (B.count("x.useState("), B.count("v2.8.0"), B.count("DzTracks"), B.count(M.CONFIRMER)) == (731, 4, 181, 30))
check("M6 la sonde amont est le marqueur de whatsapppage, une fois", B.count("/*whatsapppage*/") == 1
      and M.SONDE_AMONT[0] == ("whatsapppage", "/*whatsapppage*/", 1))
NAV = set(re.findall(r'\{k:"(\w+)",l:dzT\("(?:reglages\.onglet|espaces\.reglages)', B))
check("M7 sections secrètes figées, toutes dans la navigation de Réglages",
      M.SECRETS == ("coffre", "appareils", "keys", "accounts", "transfert") and set(M.SECRETS) <= NAV, NAV)

print("[C] couverture des secrets")
mots = []
for f in [M.BUNDLE] + sorted(SH.glob("*.js")) + sorted((REPO / "frontend").glob("*/*.html")) + sorted((REPO / "frontend").glob("*/js/*.js")):
    if any(x in f.as_posix() for x in ("/vendor/", "/node_modules/", "/src/", "dz-i18n-dico")):
        continue
    t = f.read_text("utf-8", errors="replace")
    for m in re.finditer(r'password', t):
        mots.append((f.name, t[max(0, m.start() - 90):m.end() + 30]))
# chaque occurrence est un champ mot de passe (type d'un input), un test de type ou une aide d'écran : jamais un
# autre élément qui montrerait un secret sans être un input[type=password]
champ = re.compile(r'''type:\s*["']password["']|type="password"|type\s*=\s*f\.secret\s*\?\s*"password"'''
                   r'|type:f\.secret\?"password"|,"password"\)|type===?"password"|\[type=\\?"?password'
                   r"|'(?:new|current)-password'"        # autocomplete passé à champ() du coffre : input type password
                   r'|,password:!0,')                     # la table interne de React des types d'input
inexpliques = [(n, c) for n, c in mots if not champ.search(c) and "autocomplete" not in c.lower()]
check("C1 chaque « password » des sources servies est un champ input de type password (couvert par le sélecteur)",
      len(mots) >= 7 and not inexpliques, inexpliques[:4])
check("C2 SELECTEURS_SECRETS couvre data-dz-secret ET input[type=\"password\"]",
      "export const SELECTEURS_SECRETS = '[data-dz-secret], input[type=\"password\"]';" in LOG)
for sec in M.SECRETS:
    check(f"C3 la section « {sec} » de Réglages porte data-dz-secret=\"ecran\" (le panneau qui l'affiche)",
          f'"{sec}"' in M.ATTR and f's==="{sec}"&&' in B[B.index(M.MARKER):B.index(M.MARKER) + 900])
check("C4 aucune autre section n'est marquée (personas, espaces, marque… restent filmables)",
      set(re.findall(r'"(\w+)"', M.ATTR.split("]")[0])) - {"data-dz-secret"} == set(M.SECRETS))
check("C5 le marquage dépend de la section affichée (s), pas d'une constante", '.indexOf(s)>=0?"ecran":void 0' in M.ATTR)

print("[F] feuille et scène")
check("F1 CSS_MASQUE floute data-dz-secret et type=password sous html[data-dz-capture]",
      'html[data-dz-capture] [data-dz-secret], html[data-dz-capture] input[type="password"]{filter:blur(16px)!important}' in LOG)
check("F2 l'écran secret est inerte et grisé pendant la capture",
      'html[data-dz-capture] [data-dz-secret="ecran"]{filter:blur(22px) grayscale(1)!important;pointer-events:none!important' in LOG)
i_masque, i_scene = CAP.index("    ecouter();\n") if "    ecouter();\n" in CAP else CAP.index("    ecouter();\r\n"), CAP.index("scene.demarrer();")
check("F3 masque (attribut + feuille, page et cadres) posé AVANT que la scène ne démarre",
      "doc.documentElement.setAttribute(ATTR_CAPTURE" in CAP and "st.textContent = CSS_MASQUE" in CAP and i_masque < i_scene)
check("F4 la mesure des secrets passe par SELECTEURS_SECRETS, page et cadres", "doc.querySelectorAll(SELECTEURS_SECRETS)" in CAP
      and "creerScene({ largeur: W * k, hauteur: H * k, fps: 30, secrets: () => mesurerSecrets() })" in CAP
      and "try { const m = mesure(s); etat.secrets = Array.isArray(m) ? m : null; }" in SCN)
check("F5 le caviardage est posé par creerScene (aucun appelant ne peut l'oublier)",
      "scene.ajouterCalque(calqueCaviardage());\r\n  return scene;" in SCN or "scene.ajouterCalque(calqueCaviardage());\n  return scene;" in SCN)
check("F6 le masque est retiré à l'arrêt (page et cadres)", "nePlusEcouter();" in CAP and "removeAttribute(ATTR_CAPTURE)" in CAP)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
