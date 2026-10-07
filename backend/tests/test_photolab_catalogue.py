# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — le catalogue des menus de photocraft 0.3.0 exporté pour l'écran (P2) : forme, comptes du relevé
(inventaire B §1), libellés FR, attribution.
Run : & $PY tests/test_photolab_catalogue.py   (depuis backend/)"""
import json, pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


C = json.loads((RACINE / "frontend" / "photolab" / "donnees" / "menus.json").read_text("utf-8"))
E = C.get("entrees", [])
check("1 attribution : source, version, licence", C.get("source") == "storytold/photocraft v0.3.0 crates/ui-egui/src/menu_catalog.rs"
      and C.get("licence") == "MIT OR Apache-2.0", {k: C.get(k) for k in ("source", "licence")})
check("2 les 765 lignes du catalogue, dans l'ordre", len(E) == 765, len(E))
# 9 menus : le catalogue de photocraft s'arrête à Window ; Help (7 entrées) vient de UI_COMMANDS dans son shell
# (menus.rs), l'écran (P2) l'ajoute — le plan de P1 en comptait 10 à tort.
check("3 9 menus de premier niveau dans l'ordre de photocraft (Help vient du shell, ajouté en P2)",
      list(dict.fromkeys(e["chemin"][0] for e in E)) == ["File", "Edit", "Image", "Layer", "Type", "Select", "Filter",
                                                          "View", "Window"],
      list(dict.fromkeys(e["chemin"][0] for e in E)))
sep = [e for e in E if e.get("separateur")]
ent = [e for e in E if not e.get("separateur")]
check("4 séparateurs sans id ni libellé", sep and all(set(e) == {"chemin", "separateur"} for e in sep))
check("5 chaque entrée : id, libelle_en, libelle_fr non vides, raccourci ou null",
      all(re.fullmatch(r"[a-z][A-Za-z0-9]*(\.[A-Za-z0-9]+)+", e["id"]) and e["libelle_en"] and e["libelle_fr"]
          and (e["raccourci"] is None or isinstance(e["raccourci"], str)) for e in ent),
      [e for e in ent if not e.get("libelle_fr")][:3])
nouv = next((e for e in ent if e["id"] == "file.new"), None)
check("6 File › New… = Nouveau…, Cmd+N", nouv == {"chemin": ["File"], "id": "file.new", "libelle_en": "New…",
                                                  "libelle_fr": "Nouveau…", "raccourci": "Cmd+N"}, nouv)
check("7 les noms des menus et sous-menus ont leur traduction", C.get("menus_fr", {}).get("File") == "Fichier"
      and C.get("menus_fr", {}).get("Blur") == "Flou", {k: C.get("menus_fr", {}).get(k) for k in ("File", "Blur")})
check("8 aucun « Photoshop » dans les libellés montrés (D8)",
      not [e for e in ent if "Photoshop" in e["libelle_fr"] or "Photoshop" in e["libelle_en"]],
      [e["libelle_en"] for e in ent if "Photoshop" in e["libelle_en"]][:5])
check("9 source_fr nomme le commit 3d23a708c2 et le blob 453fa2ad",
      "3d23a708c2" in C.get("source_fr", "") and "453fa2ad" in C.get("source_fr", ""), C.get("source_fr"))
# Refus d'un fr.tsv d'une autre empreinte : le français est épinglé, jamais « celui qui traîne ».
import subprocess, tempfile
SCRIPT = RACINE / "scripts" / "photocraft_catalogue.py"
# Autonome : un fr.tsv quelconque (pas celui de l'amont, qui ne vit que dans un dossier temporaire) suffit à prouver
# le refus — le script vérifie l'empreinte AVANT de lire le catalogue ou d'écrire.
with tempfile.TemporaryDirectory() as t:
    faux = pathlib.Path(t) / "fr.tsv"
    faux.write_bytes(b"\tFile\tFichier\n#modifie\n")
    sortie = pathlib.Path(t) / "menus.json"
    r = subprocess.run([sys.executable, str(SCRIPT), t, "--fr-tsv", str(faux), "--sortie", str(sortie)],
                       capture_output=True, text=True, encoding="utf-8")
    check("10 le script refuse un fr.tsv d'une autre empreinte, sans rien écrire",
          r.returncode == 1 and "Refus" in r.stdout and not sortie.exists(), (r.returncode, r.stdout, r.stderr))
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
