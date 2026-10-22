# -*- coding: utf-8 -*-
"""t280 (22/10/2026) — deux restes français relevés pendant la preuve anglaise de t279 (clôture Son & VFX).

  [1] la dictée des champs IA (frontend/shared/dz-champ-ia.js, partagé par tous les écrans) : le title et l'aria-label
      du micro passent par TP("ia.dictee.<état>", repli) — plus aucun titre en dur, chaque clé existe (commun.json),
      son français est le repli au caractère près, et la copie frontend/dist/shared/ est identique à l'octet.
  [2] le catalogue de démarrage de la rubrique SFX (backend/app/assets/starter/catalog.json, fabriqué par
      scripts/build_starter_catalog.py) : les DONNÉES restent françaises (recherche, import en Bibliothèque) ; l'écran
      (couche son-vfx-montage.js) traduit par motif — une clé par radical Kenney (catalogue.sfx.son.<radical>, 123
      clés pour 606 sons) suivie du numéro du fichier, et deux clés par famille (catalogue.sfx.famille.<id>.nom|desc),
      dans frontend/shared/i18n/catalogue.json. Le français de chaque clé EST celui du fabricant (STEM_FR,
      SFX_FAMILIES) ; chaque nom du catalogue commence par le français de sa clé. La couche est sous les tables L4 et
      G1 (positions) : les remplacements gardent la longueur (it.name -> svN(it), f.name -> svF(f), f.desc -> svD(f),
      recherche -> svH(it)), les fonctions sont en fin de couche, la retouche est consignée dans la saisie L4 ET dans
      RETOUCHES de G1 (les deux générateurs --check à jour), et le bundle sert la couche.
  [3] sous node, les fonctions de la couche rendent l'anglais avec un dictionnaire anglais (radical + numéro) et le
      nom du catalogue sans dictionnaire ; leur calcul de clé est celui du banc, sur les 123 radicaux.

Run : & $PY tests/test_i18n_dictee_catalogue.py   (depuis backend/)
"""
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
BACK = HERE.parent
RACINE = BACK.parent
FRONT = RACINE / "frontend"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


def dico(nom):
    return json.loads((FRONT / "shared" / "i18n" / f"{nom}.json").read_text("utf-8"))


TOUT = {}
for p in sorted((FRONT / "shared" / "i18n").glob("*.json")):
    TOUT.update(json.loads(p.read_text("utf-8")))

print("\n[1] la dictée des champs IA")
src = (FRONT / "shared" / "dz-champ-ia.js").read_bytes()
check("1.1 frontend/dist/shared/dz-champ-ia.js identique à la source", (FRONT / "dist" / "shared" / "dz-champ-ia.js").read_bytes() == src)
js = src.decode("utf-8")
dictee = js[js.index("T10 (27/09) : DICTÉE"):js.index("function rafraichirMicros()")]
check("1.2 plus de titre de dictée en dur (TITRE_V1/V2/STOP sont des fonctions)",
      not re.search(r"var TITRE_(V1|V2|STOP)\s*=", dictee) and "titre = TITRE_V1;" not in dictee, "")
appels = re.findall(r'TP\("(ia\.dictee\.[a-z0-9_]+)", "((?:[^"\\]|\\.)*)"', dictee)
cles = {k for k, _ in appels}
ATTENDUES = {"ia.dictee." + c for c in ("v1", "v2", "arreter", "micro", "estime", "accord", "envoi", "fin",
                                         "indispo", "v1_ko", "aucune")}
check("1.3 les onze états du micro passent par TP(ia.dictee.*)", cles == ATTENDUES, sorted(cles ^ ATTENDUES))
com = dico("commun")
ko = [k for k, fr in appels if k not in com or com[k].get("fr") != fr or not com[k].get("en", "").strip()]
check("1.4 chaque clé est dans commun.json, son français = le repli du code, anglais non vide", not ko, ko)
check("1.5 le title de la voie 1 se dit en anglais",
      com.get("ia.dictee.v1", {}).get("en", "").startswith("Dictate — browser speech recognition"), com.get("ia.dictee.v1"))
lit = [s for s in ("Dicter — reconnaissance", "Arrêter la dictée", "Transcription en cours")
       if re.search(r'(titre|"title")\s*[=,]\s*"' + re.escape(s), dictee)]
check("1.6 aucun title posé avec un littéral français", not lit, lit)

print("\n[2] le catalogue de démarrage (rubrique SFX)")
spec = importlib.util.spec_from_file_location("bsc", RACINE / "scripts" / "build_starter_catalog.py")
BSC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BSC)


def cle_radical(stem):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stem).lower()
    return "catalogue.sfx.son." + re.sub(r"[^a-z0-9]+", "_", s).strip("_")


CAT = dico("catalogue")
ko = [s for s, fr in BSC.STEM_FR.items()
      if cle_radical(s) not in CAT or CAT[cle_radical(s)].get("fr") != fr or not CAT[cle_radical(s)].get("en", "").strip()
      or CAT[cle_radical(s)].get("contexte") is not True]
check(f"2.1 les {len(BSC.STEM_FR)} radicaux ont leur clé (fr = STEM_FR, en non vide, contexte)", not ko, ko[:10])
ko = []
for f in BSC.SFX_FAMILIES:
    for champ, fr in (("nom", f["name"]), ("desc", f["desc"])):
        e = CAT.get(f"catalogue.sfx.famille.{f['id']}.{champ}") or {}
        if e.get("fr") != fr or not e.get("en", "").strip() or e.get("contexte") is not True:
            ko.append((f["id"], champ))
check(f"2.2 les {len(BSC.SFX_FAMILIES)} familles ont nom et description (fr = SFX_FAMILIES)", not ko, ko)
attendues = {cle_radical(s) for s in BSC.STEM_FR} | {f"catalogue.sfx.famille.{f['id']}.{c}" for f in BSC.SFX_FAMILIES
                                                      for c in ("nom", "desc")}
check("2.3 catalogue.json ne porte que ces clés (aucune orpheline)", set(CAT) == attendues, sorted(set(CAT) ^ attendues)[:5])
cat = json.loads((BACK / "app" / "assets" / "starter" / "catalog.json").read_text("utf-8"))
ko = [it["id"] for it in cat["sfx"] if not it["name"].startswith(CAT.get(cle_radical(it["stem"]), {}).get("fr", "\0"))]
check(f"2.4 les {len(cat['sfx'])} sons du catalogue livré commencent par le français de leur radical", not ko and cat["sfx"], ko[:10])
fam_cat = {f["id"]: f for f in cat["sfx_families"]}
check("2.5 les familles du catalogue livré sont celles du fabricant",
      all(fam_cat.get(f["id"], {}).get("name") == f["name"] and fam_cat[f["id"]].get("desc") == f["desc"] for f in BSC.SFX_FAMILIES))
# 2.6 : un français déjà traduit ailleurs garde CETTE traduction (Verre/Glass, Sélection/Selection, Interface,
#       Tissu/Fabric) ; seuls les homonymes à sens différent ont la leur (Pas : Spacing ailleurs, Retour : Release)
HOMONYMES = {"Pas", "Retour"}
autres = {}
for k, v in TOUT.items():
    if not k.startswith("catalogue.") and isinstance(v, dict):
        autres.setdefault(v.get("fr"), set()).add(v.get("en"))
ko = [(k, v["fr"], v["en"], autres[v["fr"]]) for k, v in CAT.items()
      if v["fr"] in autres and v["en"] not in autres[v["fr"]] and v["fr"] not in HOMONYMES]
check("2.6 un français déjà traduit ailleurs garde la même traduction (homonymes motivés à part)", not ko, ko)

couche = (FRONT / "patches" / "son-vfx-montage.js").read_text("utf-8")
i_nav = couche.index("function SvmSfxBrowser(props){")
nav = couche[i_nav:couche.index("\nfunction ", i_nav + 10)]
check("2.7 le navigateur SFX n'affiche plus it.name brut (nom, deux aria-label, note d'import : svN)",
      "nom:it.name}" not in nav and "children:it.name}" not in nav and nav.count("svN(it)") == 4, nav.count("svN(it)"))
rail = couche[couche.index("function SvmRailFamilies(props){"):i_nav]
check("2.8 le rail des familles passe par svF / svD (nom, description, bulle)",
      rail.count("svF(f)") == 1 and rail.count("svD(f)") == 2 and "f.name" not in rail and "f.desc" not in rail)
check("2.9 la recherche locale cherche le nom du catalogue ET le nom affiché (svH)", "svmNorm([svH(it),it.stem," in couche)
i_aides = couche.index("t280 : le catalogue de démarrage dans la langue")
check("2.10 les fonctions sont en FIN de couche (après la dernière édition G1)",
      couche.index("function svCle(stem){") > i_aides > couche.index("function SvmVfxIa(props){"))
gens = {}
for g in ("scripts/i18n_l4_generer.py", "scripts/icones/g1_generer.py"):
    r = subprocess.run([sys.executable, str(RACINE / g), "--check"], cwd=str(RACINE), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONUTF8="1"))
    gens[g] = (r.returncode, (r.stdout + r.stderr).strip()[-200:])
check("2.11 retouche consignée : générateurs L4 et G1 --check à jour", all(c == 0 for c, _ in gens.values()), gens)
saisie = (RACINE / "scripts" / "i18n_l4" / "son_a.py").read_text("utf-8")
g1 = (RACINE / "scripts" / "icones" / "g1_generer.py").read_text("utf-8")
check("2.12 la saisie L4 et RETOUCHES de G1 portent la retouche t280",
      "# t280" in saisie and saisie.count("svN(it)") >= 4 and "# t280" in g1 and "function svN(it)" in g1)
bundle = (FRONT / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes()
bloc = bundle.split(b"/*__DZ_SONVFX_BEGIN__*/", 1)[1].split(b"/*__DZ_SONVFX_END__*/", 1)[0]
check("2.13 le bundle sert la couche à jour, à l'octet",
      bloc.strip(b"\r\n") == couche.encode("utf-8").replace(b"\r\n", b"\n").replace(b"\n", b"\r\n").strip(b"\r\n")
      or bloc.strip(b"\r\n") == (FRONT / "patches" / "son-vfx-montage.js").read_bytes().strip(b"\r\n"))

print("\n[3] fonctionnel sous node")
if not NODE:
    check("3 node disponible", False, "node absent")
else:
    fonctions = couche[couche.index("function svCle(stem){"):]
    un_par_radical = {}
    for it in cat["sfx"]:
        un_par_radical.setdefault(it["stem"], it)          # un son par radical : les 123 clés calculées par la couche
    sondes = [{"name": it["name"], "stem": it["stem"]} for it in un_par_radical.values()] + [{"name": "Autre 003", "stem": "inconnuX"}]
    fams = [{"id": f["id"], "name": f["name"], "desc": f["desc"]} for f in BSC.SFX_FAMILIES] + [{"id": "circle", "name": "Disques", "desc": "d"}]
    prog = (
        "var window={};var D=JSON.parse(process.argv[1]),S=JSON.parse(process.argv[2]),F=JSON.parse(process.argv[3]);"
        "function dzT(k){var e=window.DZ_I18N[k];return e?e.en:k}" + fonctions +
        "\nvar out={cles:S.map(function(s){return svCle(s.stem)}),sans:S.map(svN),famSans:F.map(svF),hay:svH(S[0])};"
        "window.DZ_I18N=D;out.en=S.map(svN);out.famEn=F.map(function(f){return [svF(f),svD(f)]});out.hayEn=svH(S[0]);"
        "console.log(JSON.stringify(out))")
    p = subprocess.run([NODE, "-e", prog, json.dumps(CAT, ensure_ascii=False), json.dumps(sondes, ensure_ascii=False),
                        json.dumps(fams, ensure_ascii=False)], capture_output=True, text=True, encoding="utf-8")
    R = json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else {}
    check("3.1 les fonctions de la couche se chargent sous node", bool(R), p.stderr[-400:])
    if R:
        check(f"3.2 svCle (JS) = cle_radical (banc) sur les {len(un_par_radical)} radicaux",
              R["cles"] == [cle_radical(s["stem"]) for s in sondes] and len(un_par_radical) == len(BSC.STEM_FR),
              [(a, b) for a, b in zip(R["cles"], [cle_radical(s["stem"]) for s in sondes]) if a != b][:5])
        check("3.3 sans dictionnaire : le nom du catalogue, tel quel", R["sans"] == [s["name"] for s in sondes], R["sans"][:3])
        attendu = []
        for s in sondes:
            e = CAT.get(cle_radical(s["stem"]))
            attendu.append(e["en"] + s["name"][len(e["fr"]):] if e else s["name"])
        check("3.4 avec le dictionnaire anglais : radical traduit + numéro gardé (« Generic impact, light 000 »)",
              R["en"] == attendu and "Generic impact, light 000" in R["en"], list(zip(R["en"], attendu))[:4])
        check("3.5 familles : anglais avec dictionnaire, nom du catalogue sans ; famille inconnue (particules) intacte",
              R["famSans"] == [f["name"] for f in fams]
              and R["famEn"][:-1] == [[CAT[f"catalogue.sfx.famille.{f['id']}.nom"]["en"], CAT[f"catalogue.sfx.famille.{f['id']}.desc"]["en"]]
                                      for f in BSC.SFX_FAMILIES]
              and R["famEn"][-1] == ["Disques", "d"], R.get("famEn", [])[:2])
        check("3.6 la recherche porte le nom du catalogue et le nom anglais",
              R["hayEn"].startswith(sondes[0]["name"] + " ") and R["hayEn"].endswith(R["en"][0]) and R["en"][0] != sondes[0]["name"],
              (R.get("hay"), R.get("hayEn")))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
