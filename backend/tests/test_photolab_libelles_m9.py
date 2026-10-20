# -*- coding: utf-8 -*-
"""t258 (Photolab M9, 20/10/2026) — libellés FR/EN des commandes neuves ; fr.tsv de photocraft v0.10.0 en REPLI.

  [1] menus.json : français de l'amont pris au tag v0.10.0 (blob 4a819b0e), attribution ; l'arbre et nos libellés
      INCHANGÉS (empreinte figée des 627 entrées et des noms de menus, relevée avant M9) ; aucun écart amont gardé
      sans être consigné.
  [2] `repli` : exactement les commandes du moteur épinglé hors de l'arbre (moins celles qui nomment Photoshop),
      libellé anglais du moteur, français du fr.tsv seulement.
  [3] le script : nos libellés gagnent sur l'amont (garder), l'écart est consigné ; repli() écarte l'arbre et D8.
  [4] les 79 commandes ouvertes par M3-M8 (0.10 - 0.3.0 - photolab_neuves) ont TOUTES leur clé dans
      LIBELLES_COMMANDES (mod-libelles.js), et seulement elles ; chaque clé a fr et en, dans les deux dicos assemblés.
  [5] un texte FR = une traduction : nos clés neuves photolab.commande.* ne contredisent aucune clé du dictionnaire.
Hors ligne ; aucun moteur. Run : & $PY -X utf8 tests/test_photolab_libelles_m9.py   (depuis backend/)"""
import hashlib, json, pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))
import photocraft_version as PV                            # noqa: E402
import photocraft_catalogue as PC                          # noqa: E402
from app.services.photolab_neuves import COMMANDES_NEUVES_FERMEES   # noqa: E402

MENUS = json.loads((ROOT / "frontend" / "photolab" / "donnees" / "menus.json").read_text("utf-8"))
MOD = (ROOT / "frontend" / "photolab" / "js" / "mod-libelles.js").read_text("utf-8")
I18N = ROOT / "frontend" / "shared" / "i18n"
DICO = json.loads((I18N / "photolab.json").read_text("utf-8"))
ASSEMBLES = [ROOT / "frontend" / "shared" / "dz-i18n-dico.js", ROOT / "frontend" / "dist" / "shared" / "dz-i18n-dico.js"]
# Relevé avant M9 sur main 2b483b42 (menus.json du commit 3d23a708c2) : sha256 de json.dumps([[id, fr, en, raccourci]…])
# des entrées (séparateurs compris, comme [chemin]) puis des noms de menus triés.
EMPREINTE_ARBRE = "96f3904185894be127bc892010fd57c32dc20fe96bba7413bc812bb06aa0dccb"
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:1200]}")


def empreinte_arbre(m):
    lignes = [[e["chemin"]] if e.get("separateur") else [e["id"], e["libelle_fr"], e["libelle_en"], e["raccourci"], e["chemin"]]
              for e in m.get("entrees", [])]
    lignes.append(sorted((m.get("menus_fr") or {}).items()))
    return hashlib.sha256(json.dumps(lignes, ensure_ascii=False).encode("utf-8")).hexdigest()


print("[1] menus.json : source, attribution, arbre inchangé")
src = MENUS.get("source_fr", "")
check("1.1 français de l'amont : tag v0.10.0, blob 4a819b0e, repli seulement", "v0.10.0" in src and "4a819b0e" in src
      and "repli" in src and "3d23a708c2" not in src, src)
check("1.2 licence et source de l'arbre (v0.3.0) inchangées", MENUS.get("licence") == "MIT OR Apache-2.0"
      and MENUS.get("source") == "storytold/photocraft v0.3.0 crates/ui-egui/src/menu_catalog.rs")
check("1.3 l'arbre et nos libellés : empreinte d'avant M9", empreinte_arbre(MENUS) == EMPREINTE_ARBRE, empreinte_arbre(MENUS))
check("1.4 765 lignes, aucun écart amont (le fr.tsv v0.10.0 ne contredit aucun de nos libellés)",
      len(MENUS.get("entrees", [])) == 765 and MENUS.get("ecarts_amont") == [], MENUS.get("ecarts_amont"))
attr = (ROOT / "frontend" / "photolab" / "ATTRIBUTION.md").read_text("utf-8")
check("1.5 ATTRIBUTION.md cite la traduction française de l'amont (fr.tsv, v0.10.0)", "fr.tsv" in attr and "v0.10.0" in attr)

print("[2] repli : commandes du moteur hors de l'arbre")
CMD = PV.commandes()
arbre = {e["id"] for e in MENUS["entrees"] if e.get("id")}
attendus = {c["id"]: c["label"].strip() for c in CMD if c["id"] not in arbre and c.get("label") and "Photoshop" not in c["label"]}
rep = MENUS.get("repli", {})
check("2.1 exactement les commandes hors arbre (moins D8)", set(rep) == set(attendus),
      (sorted(set(attendus) - set(rep))[:5], sorted(set(rep) - set(attendus))[:5]))
check("2.2 libellé anglais = celui du moteur", all(rep[i]["libelle_en"] == attendus[i] for i in rep if i in attendus))
check("2.3 forme : libelle_en, libelle_fr facultatif, rien d'autre ; 118 traduits par le fr.tsv",
      all(set(v) <= {"libelle_en", "libelle_fr"} and v.get("libelle_fr", "x").strip() for v in rep.values())
      and sum(1 for v in rep.values() if "libelle_fr" in v) == 118, sum(1 for v in rep.values() if "libelle_fr" in v))
check("2.4 aucun « Photoshop » dans le repli (D8)", "Photoshop" not in json.dumps(rep, ensure_ascii=False))

print("[3] script : nos libellés d'abord")
ent = [{"chemin": ["F"], "id": "a.b", "libelle_en": "A", "libelle_fr": "Amont", "raccourci": None},
       {"chemin": ["F"], "id": "c.d", "libelle_en": "C", "libelle_fr": "Pareil", "raccourci": None}]
menus = {"F": "Fichier amont"}
ecarts = PC.garder(ent, menus, {"entrees": [{"id": "a.b", "libelle_fr": "Nôtre"}, {"id": "c.d", "libelle_fr": "Pareil"}],
                                "menus_fr": {"F": "Fichier"}})
check("3.1 garder : notre français l'emporte, l'écart est consigné (entrée et menu)",
      ent[0]["libelle_fr"] == "Nôtre" and menus["F"] == "Fichier"
      and ecarts == [{"id": "a.b", "garde": "Nôtre", "amont": "Amont"}, {"menu": "F", "garde": "Fichier", "amont": "Fichier amont"}], ecarts)
check("3.2 garder sans menus.json en place : l'amont tel quel", PC.garder([dict(ent[1])], {}, {}) == [])
r = PC.repli([{"id": "a.b", "label": "A"}, {"id": "x.y", "label": "Patch"}, {"id": "p.s", "label": "Photoshop Step"},
              {"id": "z.z", "label": "Zed"}, {"id": "i.d", "label": "Id"}], {"a.b"}, {"Patch": "Pièce"}, {"i.d": "Par id"})
check("3.3 repli : hors arbre, sans Photoshop, @id d'abord, trié", r == {"i.d": {"libelle_en": "Id", "libelle_fr": "Par id"},
      "x.y": {"libelle_en": "Patch", "libelle_fr": "Pièce"}, "z.z": {"libelle_en": "Zed"}}, r)
check("3.4 épinglage : blob du fr.tsv de v0.10.0", PC.BLOB_FR == "4a819b0e1b15b2ed7f6fc2625895be1d02e46cf4" and PC.TAG_FR == "v0.10.0")

print("[4] les commandes ouvertes par M3-M8 ont nos libellés")
C3 = {c["id"] for c in PV.commandes("0.3.0")}
ouvertes = {c["id"] for c in CMD} - C3 - set(COMMANDES_NEUVES_FERMEES)
table = dict(re.findall(r'^\s*"([a-zA-Z.]+)": "(photolab\.[A-Za-z0-9_.]+)",', MOD, re.M))
check("4.1 79 commandes ouvertes (142 neuves - fermées)", len(ouvertes) == 79, len(ouvertes))
check("4.2 LIBELLES_COMMANDES = exactement les commandes ouvertes", set(table) == ouvertes,
      (sorted(ouvertes - set(table)), sorted(set(table) - ouvertes)))
manq = [c for c in table.values() if not (DICO.get(c) and DICO[c]["fr"].strip() and DICO[c]["en"].strip())]
check("4.3 chaque clé : fr et en non vides au dictionnaire du Photolab", not manq, manq)
for f in ASSEMBLES:
    txt = f.read_text("utf-8")
    check(f"4.4 {f.parent.parent.name}/{f.parent.name}/dz-i18n-dico.js porte nos clés", all(json.dumps(c) in txt for c in table.values()))
morts = sorted(k for k in DICO if k.startswith("photolab.commande.") and k not in table.values())
check("4.5 aucune clé photolab.commande.* orpheline", not morts, morts)

print("[5] un texte FR = une traduction")
tout = {}
for f in I18N.glob("*.json"):
    tout.update(json.loads(f.read_text("utf-8")))
par_fr = {}
for k, v in tout.items():
    if not v.get("contexte"):
        par_fr.setdefault(v["fr"], set()).add(v["en"])
conflits = [(k, DICO[k]["fr"], sorted(par_fr[DICO[k]["fr"]])) for k in DICO if k.startswith("photolab.commande.")
            and len(par_fr.get(DICO[k]["fr"], ())) > 1]
check("5.1 nos clés neuves ne donnent pas deux anglais au même français", not conflits, conflits)
check("5.2 34 clés neuves photolab.commande.*", sum(1 for k in DICO if k.startswith("photolab.commande.")) == 34)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
