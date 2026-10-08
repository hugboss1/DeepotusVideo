# -*- coding: utf-8 -*-
"""t137 (Photolab P2, tâche C4, 08/10/2026) — les textes de l'écran Photolab passent tous par le dictionnaire.

  [1] le relevé du skill traduction-deepotus (copie vendue scripts/releve_chaines.py, --fr-seulement --hors-dico photolab.json
      commun.json) ne trouve AUCUNE chaîne française hors dictionnaire dans frontend/photolab (page et modules). Le
      relevé est une estimation par expressions régulières : une fausse alerte se met dans AUTORISEES avec sa raison,
      jamais en relâchant le compte. Témoin : sans --hors-dico, le relevé voit bien les phrases de l'accueil (sinon un
      relevé vide passerait pour un succès).
  [2] chaque clé « photolab.* » / « commun.* » écrite en toutes lettres dans js/*.js existe au dictionnaire (fr et en).
Run : & $PY tests/test_photolab_textes.py   (depuis backend/)
"""
import json, pathlib, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
LAB = ROOT / "frontend" / "photolab"
I18N = ROOT / "frontend" / "shared" / "i18n"
RELEVE = ROOT / "scripts" / "releve_chaines.py"          # copie vendue du script du skill traduction-deepotus

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:900]}")


# Fausses alertes connues du relevé : (fichier relatif à frontend/photolab, texte exact) -> raison. Vide à ce jour :
# une ligne de code qui piégeait l'expression (deux littéraux sur une ligne) a été réécrite plutôt qu'autorisée.
AUTORISEES = {}


def relever(*args):
    r = subprocess.run([sys.executable, "-X", "utf8", str(RELEVE), *args], capture_output=True, text=True,
                       encoding="utf-8", cwd=str(ROOT))
    lignes = []
    for l in r.stdout.splitlines():
        parts = l.split("\t")
        if len(parts) >= 4 and ":" in parts[0]:
            fichier = parts[0].rsplit(":", 1)[0].replace("\\", "/")
            lignes.append((fichier, parts[1], parts[2], "\t".join(parts[3:])))
    return r, lignes


print("[1] relevé des chaînes françaises hors dictionnaire")
check("1.1 le script de relevé (copie vendue dans scripts/) est présent", RELEVE.is_file(), RELEVE)
if RELEVE.is_file():
    r, brut = relever("frontend/photolab")
    check("1.2 le relevé tourne", r.returncode == 0, r.stderr[-400:])
    check("1.3 témoin : sans dictionnaire, il voit la phrase de l'accueil",
          any(t == "Crée un document ou ouvre une image." for _, _, _, t in brut), brut[:5])
    r, lignes = relever("frontend/photolab", "--fr-seulement", "--hors-dico",
                        str(I18N / "photolab.json"), str(I18N / "commun.json"))
    # qa/ : les bancs node (libellés de check en français, par convention du dépôt) ne s'affichent jamais à l'écran.
    vues = [x for x in lignes if "/photolab/qa/" not in x[0] and not x[0].startswith("frontend/photolab/qa/")]
    restes = [x for x in vues if (x[0].split("frontend/photolab/", 1)[-1], x[3]) not in AUTORISEES]
    check("1.4 aucune chaîne française hors dictionnaire dans la page et les modules", not restes,
          "\n" + "\n".join(f"{f} [{g}] {t}" for f, g, _, t in restes[:20]))
    check("1.5 chaque autorisation sert encore (pas de liste morte)",
          all(any(x[0].endswith(f) and x[3] == t for x in vues) for f, t in AUTORISEES), list(AUTORISEES))

print("\n[2] clés du dictionnaire citées par les modules")
dico = {}
for f in sorted(I18N.glob("*.json")):
    dico.update(json.loads(f.read_text("utf-8")))
manquantes = []
for js in sorted((LAB / "js").glob("*.js")):
    for cle in re.findall(r'"((?:photolab|commun)\.[a-z0-9_.]+)"', js.read_text("utf-8")):
        if cle.endswith("."):
            continue                                       # préfixe complété à l'exécution (outils, options…) : banc node
        v = dico.get(cle)
        if not (isinstance(v, dict) and v.get("fr") and v.get("en")):
            manquantes.append(f"{js.name}: {cle}")
check("2.1 chaque clé écrite en toutes lettres existe (fr et en)", not manquantes, manquantes[:20])
check("2.2 le relevé des clés a bien lu des modules", len(list((LAB / "js").glob("mod-*.js"))) >= 10)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
