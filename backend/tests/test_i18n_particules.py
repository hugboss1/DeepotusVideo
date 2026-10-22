# -*- coding: utf-8 -*-
"""t281 (22/10/2026) — la page Particules de Son & VFX (frontend/patches/sonvfx-particules.js, posée aplatie dans le
bundle par le maillon de queue dzsonvfx), interface en anglais.

Deux sources de données, deux traitements :
  - le catalogue de démarrage (/api/starter/catalog, fabriqué par scripts/build_starter_catalog.py) n'est PAS traduit
    par le serveur : les 18 familles (PARTICLE_FAMILIES) et les 80 textures (« Disques 01 ») restaient en français.
    Les DONNÉES restent françaises ; l'écran les traduit (modèle t280) : catalogue.particules.famille.<id>.nom|desc
    dans frontend/shared/i18n/catalogue.json, une texture = la famille traduite + son numéro, repli sur le texte servi.
  - les presets et les séquences (/api/particles/presets) arrivent DÉJÀ traduits par le serveur (lot L9 :
    backend/app/i18n/catalogues.particules, clés particules.* de messages.json). Aucune clé côté écran (pas de second
    anglais) ; mais la surcouche retraduisait l'« Explosion » servie en « Burst » (photolab.presets.f_burst) : leurs
    boutons et le nom de l'inspecteur portent data-dz-brut.

  [1] le dictionnaire : 36 clés famille (fr = fabricant, en écrit, contexte), aucune clé preset/séquence côté écran,
      le serveur couvre bien chaque preset et chaque séquence, dictionnaire assemblé à jour.
  [2] le catalogue livré : chaque texture commence par le français de sa famille, familles = fabricant.
  [3] la source : plus de F.name / t.name affichés bruts, data-dz-brut sur ce que sert le serveur, et le bundle porte
      aplatir(source) à sa place.
  [4] sous node : « Discs 01 », « Muzzle flash 02 » avec le dictionnaire anglais, texte servi sans dictionnaire.

Run : & $PY tests/test_i18n_particules.py   (depuis backend/)
"""
import importlib.util
import json
import pathlib
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


def module(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


BSC = module("bsc", RACINE / "scripts" / "build_starter_catalog.py")
sys.path.insert(0, str(BACK))
from app.services import particle_service as PS  # noqa: E402
ZS = module("zs", RACINE / "scripts" / "patch_bundle_dzsonvfx.py")

TOUT = {}
for p in sorted((FRONT / "shared" / "i18n").glob("*.json")):
    TOUT.update(json.loads(p.read_text("utf-8")))
CAT = json.loads((FRONT / "shared" / "i18n" / "catalogue.json").read_text("utf-8"))
PART = {k: v for k, v in CAT.items() if k.startswith("catalogue.particules.")}
FAM = "catalogue.particules.famille."
cat = json.loads((BACK / "app" / "assets" / "starter" / "catalog.json").read_text("utf-8"))

print("\n[1] le dictionnaire")
attendu = {}
for fid, (nom, desc) in BSC.PARTICLE_FAMILIES.items():
    attendu[f"{FAM}{fid}.nom"], attendu[f"{FAM}{fid}.desc"] = nom, desc
check(f"1.1 catalogue.particules.* = les {len(attendu)} clés famille (18 × nom, desc), aucune clé preset ni séquence",
      set(PART) == set(attendu) and len(attendu) == 36, sorted(set(PART) ^ set(attendu))[:6])
ko = [k for k, fr in attendu.items() if (PART.get(k) or {}).get("fr") != fr]
check("1.2 le français de chaque clé est celui du fabricant (PARTICLE_FAMILIES)", not ko, ko[:6])
ko = [k for k, v in PART.items() if not v.get("en", "").strip() or v.get("contexte") is not True or v["en"] == v["fr"]]
check("1.3 anglais écrit (non vide, différent du français), clés « contexte » (ignorées par la surcouche)", not ko, ko[:6])
autres = {}
for k, v in TOUT.items():
    if not k.startswith("catalogue.") and isinstance(v, dict):
        autres.setdefault(v.get("fr"), set()).add(v.get("en"))
ko = [(k, v["fr"], v["en"], autres[v["fr"]]) for k, v in PART.items() if v["fr"] in autres and v["en"] not in autres[v["fr"]]]
check("1.4 un français déjà traduit ailleurs garde la même traduction", not ko, ko)
msg = json.loads((BACK / "app" / "i18n" / "messages.json").read_text("utf-8"))
manque = [p["id"] for p in PS.PRESETS if f"particules.{p['id']}.nom" not in msg or f"particules.{p['id']}.desc" not in msg
          or ("boucle" in p["type"] and f"particules.{p['id']}.type" not in msg)]
manque += [a["id"] for a in cat["anims"] if f"particules.anim.{a['id']}.nom" not in msg]
check(f"1.5 le serveur (L9) traduit chacun des {len(PS.PRESETS)} presets et des {len(cat['anims'])} séquences", not manque, manque)
ass = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], cwd=str(RACINE),
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
check("1.6 dz-i18n-dico.js assemblé à jour (les deux copies)", ass.returncode == 0, ass.stdout + ass.stderr)
check("1.7 le dictionnaire assemblé porte les clés famille", f'"{FAM}circle.nom"' in (FRONT / "shared" / "dz-i18n-dico.js").read_text("utf-8"))

print("\n[2] le catalogue livré (données intactes)")
ko = [t["id"] for t in cat["particles"] if not t["name"].startswith(PART.get(f"{FAM}{t['family']}.nom", {}).get("fr", "\0"))]
check(f"2.1 les {len(cat['particles'])} textures commencent par le français de leur famille", not ko and len(cat["particles"]) == 80, ko[:6])
ko = [f["id"] for f in cat["particle_families"]
      if f["name"] != PART.get(f"{FAM}{f['id']}.nom", {}).get("fr") or f["desc"] != PART.get(f"{FAM}{f['id']}.desc", {}).get("fr")]
check(f"2.2 les {len(cat['particle_families'])} familles livrées = le dictionnaire", not ko and len(cat["particle_families"]) == 18, ko)

print("\n[3] la source et le bundle")
SRC = FRONT / "patches" / "sonvfx-particules.js"
src = SRC.read_bytes().decode("utf-8")
i_aides = src.index("function dzSvxCat(k,repli){")
corps = src[:i_aides] + src[src.index("function dzSvxTextes(){"):]
brut = [m for m in ("F.name", "F.desc", "t.name") if m in corps]
check("3.1 plus aucun nom de famille ni de texture affiché brut", not brut, brut)
compte = {f: corps.count(f + "(") for f in ("dzSvxFam", "dzSvxFamD", "dzSvxTex")}
check("3.2 les appels : famille (option + bulle), texture (title + aria-label)",
      compte == {"dzSvxFam": 1, "dzSvxFamD": 1, "dzSvxTex": 2}, compte)
check("3.3 la page fait le même calcul de clés que le banc",
      '"catalogue.particules.famille."+F.id+".nom"' in src and '"catalogue.particules.famille."+t.family+".nom"' in src)
# la surcouche connaît « Explosion » -> « Burst » (clé non contexte) : sans data-dz-brut, le nom servi serait retraduit
check("3.4 le piège existe bien : « Explosion » est retraduit par la surcouche (clé non contexte, en ≠ Explosion)",
      any(v.get("fr") == "Explosion" and v.get("en") != "Explosion" and not v.get("contexte") for v in TOUT.values()))
check("3.5 boutons de preset, de séquence et nom de l'inspecteur : data-dz-brut (texte déjà traduit par le serveur)",
      '"data-preset":P.id,title:P.desc,"data-dz-brut":"1",' in src and '"data-anim":A.id,"data-dz-brut":"1",' in src
      and 'className:"dzsvx-courant","data-dz-brut":"1",children:curP?curP.name:texture' in src)
bundle = (FRONT / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8-sig")
seg = bundle.split("/*__dzsvvoix*/", 1)[1].split("/*__dzsvparticules*/", 1)[0]
check("3.6 le bundle porte aplatir(source) entre /*__dzsvvoix*/ et /*__dzsvparticules*/", seg == ZS.page(SRC))
check("3.7 comptes figés du bundle intacts (useState 731, DzTracks 181)",
      bundle.count("x.useState(") == 731 and bundle.count("DzTracks") == 181)

print("\n[4] fonctionnel sous node")
if not NODE:
    check("4 node disponible", False, "node absent")
else:
    fonctions = src[i_aides:src.index("function dzSvxTextes(){")]
    tex = [{"id": t["id"], "family": t["family"], "name": t["name"]} for t in cat["particles"]] + [
        {"id": "inconnu_04", "family": "inconnu", "name": "Inconnu 04"}]
    fams = cat["particle_families"] + [{"id": "inconnu", "name": "Inconnu", "desc": "d"}]
    entree = json.dumps({"D": PART, "T": tex, "F": fams}, ensure_ascii=False)
    prog = (
        "var window={};var I=JSON.parse(require('fs').readFileSync(0,'utf8'));"
        "function dzT(k){var e=window.DZ_I18N[k];return e?e.en:k}" + fonctions +
        "\nfunction tout(){return {t:I.T.map(dzSvxTex),f:I.F.map(function(f){return [dzSvxFam(f),dzSvxFamD(f)]})}}"
        "var sans=tout();window.DZ_I18N=I.D;var en=tout();console.log(JSON.stringify({sans:sans,en:en}))")
    p = subprocess.run([NODE, "-e", prog], input=entree, capture_output=True, text=True, encoding="utf-8")
    R = json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else {}
    check("4.1 les fonctions de la page se chargent sous node", bool(R), p.stderr[-400:])
    if R:
        S, E = R["sans"], R["en"]
        check("4.2 sans dictionnaire : le texte servi, tel quel",
              S["t"] == [t["name"] for t in tex] and S["f"] == [[f["name"], f["desc"]] for f in fams])
        att = [PART[f"{FAM}{t['family']}.nom"]["en"] + t["name"][len(PART[f"{FAM}{t['family']}.nom"]["fr"]):]
               if f"{FAM}{t['family']}.nom" in PART else t["name"] for t in tex]
        check("4.3 textures : famille anglaise + numéro gardé (« Discs 01 », « Muzzle flash 02 »), inconnue intacte",
              E["t"] == att and "Discs 01" in E["t"] and "Muzzle flash 02" in E["t"] and E["t"][-1] == "Inconnu 04",
              [x for x in zip(E["t"], att) if x[0] != x[1]][:4])
        check("4.4 familles : nom et description anglais, famille inconnue intacte",
              E["f"][:-1] == [[PART[f"{FAM}{f['id']}.nom"]["en"], PART[f"{FAM}{f['id']}.desc"]["en"]] for f in fams[:-1]]
              and E["f"][-1] == ["Inconnu", "d"] and E["f"][0][0] == "Discs", E["f"][:2])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
