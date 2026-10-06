# -*- coding: utf-8 -*-
"""Écran /materialforge/ — bancs-miroirs de texte (T4 et T8 du plan
2026-09-03-plan-matieres).

Patron de test_etabli_canevas.py : le frontend est du vanilla servi en
statique, donc on le LIT comme du texte et on y épingle des marqueurs. Les
assertions NÉGATIVES portent sur le fichier PRIVÉ DE SES COMMENTAIRES — ce
dépôt commente en expliquant ce qu'il écarte, et un `assert "x" not in js`
posé sur le fichier entier serait satisfait par la phrase même qui jure de
ne pas s'en servir.

LA MOITIÉ QUI COMPTE : les clés du contrat HTTP sont épinglées DES DEUX
CÔTÉS — dans `routes.py` et dans `materialforge.js`. Renommer une clé d'un
seul côté fait rougir ce banc, ce qu'aucune lecture d'un seul fichier ne
saurait faire.

Run (depuis backend/) : python tests/test_materialforge_ecran.py
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend" / "materialforge"
ROUTES = RACINE / "backend" / "app" / "api" / "routes.py"

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def lire(nom):
    return (FRONT / nom).read_text(encoding="utf-8")


def code(nom):
    """Le fichier SANS ses blocs /* … */ — réservé aux assertions négatives."""
    return re.sub(r"/\*.*?\*/", "", lire(nom), flags=re.S)


HTML = lire("index.html")
JS = lire("materialforge.js")
JS_CODE = code("materialforge.js")
CSS = lire("materialforge.css")
PY = ROUTES.read_text(encoding="utf-8")

# ══ 1 · le panneau Photo existe et porte ses commandes ══════════════════════
for ident in ("grpPhoto", "phCanvas", "phDelight", "phStrength", "phPreview",
              "phReset", "phOut", "phMeasure"):
    assert f'id="{ident}"' in HTML, ident
assert HTML.count('id="grpPhoto"') == 1
assert '<div class="grp-body">' in HTML.split('id="grpPhoto"', 1)[1].split("</details>", 1)[0]
ok("index.html : panneau Photo — canevas des quatre coins, délighter, "
   "intensité, aperçu, remise à zéro, image de sortie, mesure")

# ══ 2 · le contrat HTTP est épinglé DES DEUX CÔTÉS ══════════════════════════
assert '"/materials/prep/preview"' in PY, "la route a changé de chemin"
assert "/materials/prep/preview" in JS_CODE, "l'écran n'appelle plus la route"
for cle in ("lowfreq_sd_before", "lowfreq_sd_after", "baisse_pct"):
    assert cle in PY, cle
    assert cle in JS_CODE, f"{cle} absent du JS — contrat rompu d'un côté"
ok("contrat d'aperçu épinglé des deux côtés : chemin + trois clés de mesure")

# ══ 3 · la génération EMPORTE la préparation ════════════════════════════════
corps = JS_CODE.split("async function generate()", 1)[1].split("\n}\n", 1)[0]
assert re.search(r"if \(state\.ref\) \{\s*body\.filename = state\.ref;\s*body\.prep = photoPrep\(\);",
                 corps), corps[:900]
ok("generate() envoie le bloc prep AVEC la référence, et seulement avec elle")

# ══ 3b · state.ref est une CHAÎNE, et un refus n'est pas une API absente ════
pv = JS_CODE.split("async function photoPreview()", 1)[1].split("\n}\n", 1)[0]
assert "const fn = state.ref;" in pv and "state.ref.filename" not in JS_CODE, pv[:300]
assert "if (e.missing) apiFail(" in pv and "toast(" in pv, pv
ok("photoPreview lit le nom de la référence tel quel ; un 400 se dit en toast, "
   "apiFail reste aux routes absentes")

# ══ 4 · quatre coins, pas trois ni cinq ═════════════════════════════════════
assert re.search(r"quad\.length\s*[<>=!]{1,3}\s*4", JS_CODE), \
    "aucune garde sur le nombre de coins"
assert "phCanvas" in JS_CODE and "getBoundingClientRect" in JS_CODE
# la regex ci-dessus est satisfaite par photoPrep() seule : on épingle aussi le
# geste lui-même — un CINQUIÈME clic recommence la saisie, il ne l'allonge pas
clic = JS_CODE.split("function photoClick(ev)", 1)[1].split("\n}\n", 1)[0]
assert "if (photo.quad.length >= 4) photo.quad = [];" in clic, clic
# la conversion affichage -> image se fait DANS photoClick (getBoundingClientRect
# existe ailleurs dans le fichier : le chercher partout laissait un mutant vert)
assert '$("#phCanvas").getBoundingClientRect()' in clic and "/ photo.fit.s" in clic, clic
# et une NOUVELLE référence oublie les coins de l'ancienne
ref = JS_CODE.split("function setRef(fn)", 1)[1].split("\n}\n", 1)[0]
assert "photo.quad = [];" in ref and '$("#phMeasure").textContent = "—";' in ref, ref
ok("le canevas borne la saisie à quatre coins et convertit les clics en "
   "coordonnées d'image")

# ══ 5 · le style existe ════════════════════════════════════════════════════
for regle in ("#phCanvas", "#phOut"):
    assert regle in CSS, regle
ok("materialforge.css : le canevas et l'aperçu ont leur règle")

print(f"\nOK — {PASS} assertions groupées vertes (écran Material Forge, "
      f"panneau Photo)")
