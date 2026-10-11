"""t183 / G1 — encarts alignés sur le catalogue : plus aucune liste de modèles codée en dur.

Décision de l'utilisateur (11/10/2026) : un modèle sans clé reste VISIBLE ET
CHOISISSABLE dans tout sélecteur (prix + mention « clé X à ajouter dans
Réglages »), jamais `disabled` ; seul un modèle vectoriel (sortie "svg") est
écarté des sélecteurs raster. Banc STATIQUE (lit les sources et le bundle) :

  [a1] frontend/shared/dz-modeles-ia.js : lit /api/ia/catalogue, groupe par
       voie (<optgroup>), n'écrit jamais `disabled = true`, mention
       ia.cle.a_ajouter, filtre « svg » ; son test node passe ;
  [a2] dz-champ-ia.js : plus de miroir CATALOGUE_IMAGE ni d'estimation POST,
       lit `tous` (le catalogue) et rend des en-têtes de voie ; la vidéo
       marque ses modèles sans clé choisissables (sansCle) ; le cas grisé dit
       « clé X à ajouter dans Réglages — absent du sélecteur de la vue » ;
  [a3] copies dist octet pour octet (dz-modeles-ia.js, dz-champ-ia.js) ;
  [a4] /generate : la clé du modèle vidéo est vérifiée par
       _cle_video_ou_503 AVANT _garde_cout et _plafond (ordre dans la source).

Run: & $PY tests/test_encarts_ia.py   (depuis backend/)
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parents[2]
OK = KO = 0


def check(label, cond, detail=""):
    global OK, KO
    if cond:
        OK += 1
        print("  ok  ", label)
    else:
        KO += 1
        print("  FAIL", label, detail)


def sans_commentaires(js):
    """le code sans ses commentaires /* … */ et // … (un commentaire peut citer « gratuit »)"""
    return re.sub(r"(?m)^\s*//.*$", "", re.sub(r"/\*.*?\*/", "", js, flags=re.S))


def lire(rel):
    return (R / rel).read_text(encoding="utf-8")


# ── [a1] composant partagé ───────────────────────────────────────────────────
print("[a1] dz-modeles-ia.js")
mi = lire("frontend/shared/dz-modeles-ia.js")
check("lit /api/ia/catalogue?nature=", '"/api/ia/catalogue?nature="' in mi)
check("un <optgroup> par voie", 'createElement("optgroup")' in mi and "ORDRE" in mi)
check("NÉGATIF : aucune option désactivée en dur (desactive: false, jamais disabled = true)",
      "desactive: false" in mi and not re.search(r"disabled\s*=\s*true", mi) and "desactive: true" not in mi
      and not re.search(r"desactive:\s*!", mi))
check("mention ia.cle.a_ajouter, prix inconnu = ia.prix.a_mesurer (jamais « gratuit »)",
      'T("ia.cle.a_ajouter"' in mi and 'T("ia.prix.a_mesurer")' in mi and "gratuit" not in sans_commentaires(mi))
check("filtre raster : un modèle « svg » écarté sauf option vectoriel",
      'm.sortie !== "svg"' in mi and "opts.vectoriel" in mi)
node = shutil.which("node")
if node:
    pr = subprocess.run([node, str(R / "frontend/shared/qa/modeles_ia.test.mjs")], capture_output=True, text=True,
                        encoding="utf-8", timeout=60)
    check("test node frontend/shared/qa/modeles_ia.test.mjs", pr.returncode == 0 and "modeles_ia ok" in pr.stdout,
          (pr.stdout + pr.stderr)[-600:])
else:
    check("node présent", False)

# ── [a2] couche des champs IA ────────────────────────────────────────────────
print("[a2] dz-champ-ia.js")
ch = lire("frontend/shared/dz-champ-ia.js")
check("plus de miroir CATALOGUE_IMAGE ni d'estimation POST du prix d'image",
      "CATALOGUE_IMAGE" not in ch and "/api/cost/estimate" not in ch)
check("lit le catalogue unique (`tous` de /api/image-models), sans les modèles vectoriels",
      "d.tous" in ch and 'e.sortie !== "svg"' in ch)
check("rend des en-têtes de voie (dzia-ogrp, ia.voie.*)", "dzia-ogrp" in ch and '"ia.voie."' in ch)
check("vidéo : un modèle sans clé est choisissable (sansCle: !m.available)", "sansCle: !m.available" in ch)
check("cas grisé : « clé X à ajouter dans Réglages — absent du sélecteur de la vue »",
      re.search(r"x\.sansCle \? CLE_A_AJOUTER : CLE_ABSENTE\)\(x\.cle\) \+ \" — \"\)\s*\+ \"absent du sélecteur de la vue\"",
                ch) is not None)

# ── [a3] copies dist ─────────────────────────────────────────────────────────
print("[a3] copies dist")
for f in ("dz-modeles-ia.js", "dz-champ-ia.js"):
    a, b = R / "frontend/shared" / f, R / "frontend/dist/shared" / f
    check(f"dist {f} identique à l'octet", a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes())

# ── [a4] ordre des gardes de /generate ───────────────────────────────────────
print("[a4] /generate : clé vérifiée avant la dépense")
rt = lire("backend/app/api/routes.py")
for nom in ("generate", "generate_batch", "generate_composition"):
    m = re.search(r"\nasync def " + nom + r"\(.*?(?=\n@router\.)", rt, re.S)
    corps = m.group(0) if m else ""
    i, j = corps.find("_cle_video_ou_503("), corps.find("await _plafond(")
    k = corps.find("_garde_cout(")
    check(f"{nom} : _cle_video_ou_503 avant _garde_cout et _plafond", 0 <= i < j and (k < 0 or i < k), f"{i} {k} {j}")

print(f"\n{OK} ok, {KO} fail")
sys.exit(1 if KO else 0)
