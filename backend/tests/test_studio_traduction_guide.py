# -*- coding: utf-8 -*-
"""Studio t230 — traduction et guide du lot « Menus : Studio » (17/10/2026).

Relevé (base dbc773f1, t225-t229 livrées) : les 19 paires du maillon `dzstudio` n'écrivent AUCUNE phrase visible.
Leurs littéraux neufs sont des jetons de code (styles, attributs, sélecteurs), l'identifiant de port « brand » (comme
« avatar », « image »…, jamais traduit), et la pastille « ⌘ ». L'infobulle de la pastille relit le texte de l'encart,
qui passe déjà par dzT. Aucune clé neuve n'est donc nécessaire ; ce banc l'empêche de devenir faux. Le chapitre
Studio du guide, lui, ne disait rien des nouveautés visibles : zoom des boutons autour du centre (t229), encart
replié en pastille (t228), texte du Bandeau de marque relié au port brand de la Composition spatiale (t226). Ses
scènes montraient des liens qui s'arrêtaient à côté des ports (avant t225) et des en-têtes serrés (avant t227).

Ce que ce banc garde :
  [K] aucune chaîne en dur dans les paires dzstudio : tout littéral neuf est un jeton de code ou figure dans la
      liste blanche ; chaque dzT d'une paire a sa clé FR ET EN ; l'infobulle de la pastille vient de l'encart ;
  [G] le chapitre Studio (FR et EN, même squelette) dit les nouveautés ; ses scènes avec des nœuds sont
      recapturées sur le Studio d'après t229 (plan t230, images différentes de celles de dbc773f1) ; la nouvelle
      scène studio/vue existe dans les deux langues.
Run (depuis backend/) : & $PY tests/test_studio_traduction_guide.py"""
import json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


import patch_bundle_dzstudio as M                                    # noqa: E402

LIT = re.compile(r'"((?:[^"\\]|\\.)*)"|`([^`]*)`')
PHRASE = re.compile(r"[A-Za-zÀ-ÿ]{2,}\s+[A-Za-zÀ-ÿ]{2,}")       # deux mots de lettres : une phrase lisible
LISTE_BLANCHE = {"brand", "⌘", " · "}         # identifiant de port ; symbole de la pastille ; séparateur « libellé · type »


def litteraux_neufs(a, r):
    la = {x or y for x, y in LIT.findall(a)}
    return [x or y for x, y in LIT.findall(r) if (x or y) not in la]


print("[K] aucune chaîne en dur dans les paires dzstudio")
NEUFS = [(k, s) for k, (a, r) in enumerate(M.PAIRES) for s in litteraux_neufs(a, r)]
check("K1 les paires sont toutes lues (AB + C + F + D + E = 19, puis les familles ajoutées après t230)",
      len(M.PAIRES) == 19 + len(getattr(M, "PAIRES_G", [])), str(len(M.PAIRES)))
phrases = [s for _, s in NEUFS if PHRASE.search(s) and not s.startswith(("var(", "[data-", "radial-gradient"))]
check("K2 aucun littéral neuf n'est une phrase", not phrases, str(phrases[:5]))
non_ascii = sorted({s for _, s in NEUFS if any(ord(c) > 127 for c in s)} - LISTE_BLANCHE)
check("K3 aucun littéral neuf non ASCII hors liste blanche (accents = texte français)", not non_ascii, str(non_ascii))
mots = sorted({s for _, s in NEUFS if re.fullmatch(r"[A-Za-z]+", s)}
              - {"brand", "text", "mark", "function", "span", "none", "flex", "hidden", "nowrap", "ellipsis", "auto",
                 "px", "BrandStrip", "Concatenate"})
check("K4 mots seuls neufs : uniquement des jetons de code connus", not mots, str(mots))
DICO = {}
for f in (RACINE / "frontend/shared/i18n").glob("*.json"):
    DICO.update(json.loads(f.read_text("utf-8")))
cles = sorted({c for _, r in M.PAIRES for c in re.findall(r'dzT\("([^"]+)"\)', r)})
manquantes = [c for c in cles if not (isinstance(DICO.get(c), dict) and DICO[c].get("fr") and DICO[c].get("en"))]
check("K5 chaque dzT des paires a sa clé FR et EN", bool(cles) and not manquantes, f"{cles} manquantes={manquantes}")
D0 = M.PAIRES_D[0][1]
check("K6 l'infobulle de la pastille relit le texte de l'encart (langue active), pas un texte écrit",
      "el.title=hit?Array.prototype.map.call(pl.childNodes," in D0 and 'el.title=hit?"' not in D0)
check("K7 l'étiquette de port tronquée garde son libellé complet en title (pas de texte écrit)",
      any("title:" in r and "ellipsis" in r for _, r in M.PAIRES_AB))

print("[G] chapitre Studio du guide")
SRC = RACINE / "docs" / "guide" / "src"
FR = (SRC / "fr" / "studio.html").read_text("utf-8")
EN = (SRC / "en" / "studio.html").read_text("utf-8")


def squelette(h):
    return re.findall(r"<(h3|ol|li|figure|aside|article|table)\b", h)


check("G1 même squelette FR / EN", squelette(FR) == squelette(EN),
      f"{len(squelette(FR))} / {len(squelette(EN))}")
check("G2 FR : zoom des boutons autour du centre, molette autour du pointeur",
      "autour du centre" in FR and "autour du pointeur" in FR)
check("G3 EN : zoom buttons around the centre, wheel around the pointer",
      "around the centre" in EN and "around the pointer" in EN)
check("G4 FR / EN : l'encart des raccourcis se replie en pastille", "se replie en pastille" in FR
      and "folds into a badge" in EN)
check("G5 FR / EN : le Bandeau de marque relié à l'entrée brand de la Composition spatiale",
      all(k in FR for k in ("Bandeau de marque", "<strong>brand</strong>", "Composition spatiale"))
      and all(k in EN for k in ("Brand strip", "<strong>brand</strong>", "Spatial compose")))
check("G6 la scène studio/vue est citée dans les deux langues",
      'data-scene="studio/vue"' in FR and 'data-scene="studio/vue"' in EN)
PLAN = SRC / "scenes" / "plans" / "t230.json"
plan = json.loads(PLAN.read_text("utf-8")) if PLAN.is_file() else {"scenes": []}
noms = [s["scene"] for s in plan["scenes"]]
check("G7 plan t230 : graphe, composition-fl et vue recapturés", noms == ["studio/graphe", "studio/composition-fl", "studio/vue"],
      str(noms))
SC = SRC / "scenes" / "studio"
vue = json.loads((SC / "vue" / "scene.json").read_text("utf-8")) if (SC / "vue" / "scene.json").is_file() else {}
check("G8 studio/vue : deux captures par langue, présentes", len(vue.get("captures", [])) == 2
      and all((SC / "vue" / c[l]).is_file() for c in vue.get("captures", []) for l in ("fr", "en")))


def blob(rev, chemin):
    r_ = subprocess.run(["git", "rev-parse", f"{rev}:{chemin}"], capture_output=True, text=True, cwd=str(RACINE))
    return r_.stdout.strip() if r_.returncode == 0 else None


def hobj(p):
    return subprocess.run(["git", "hash-object", str(p)], capture_output=True, text=True, cwd=str(RACINE)).stdout.strip()


vieilles = []
for sc in ("graphe", "composition-fl"):
    for p in sorted((SC / sc).glob("*.webp")):
        rel = p.relative_to(RACINE).as_posix()
        if blob("dbc773f1", rel) == hobj(p):
            vieilles.append(rel)
check("G9 les captures de graphe et composition-fl ne sont plus celles d'avant t225 (dbc773f1)", not vieilles,
      str(vieilles))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
