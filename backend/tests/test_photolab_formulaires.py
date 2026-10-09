# -*- coding: utf-8 -*-
"""t138 (Photolab P3, tâche B1, relecture) — de bout en bout : le formulaire de l'écran ne produit QUE des commandes
que le pont admet.

  [1] node lance frontend/photolab/qa/outils/formulaires.mjs sur le registre structuré de la fixture
      (tests/photocraft_commandes_0.3.0.json) : pour chaque commande du périmètre P3 (filter., image.adjustments.,
      layer.layerStyle., layer.newAdjustmentLayer.), valeurInitiale puis parametres de mod-champs.js avec des saisies
      hostiles (défaut, "zorg", ±1e9, NaN, "3,7", [300,-5,2], "#ABC", "") ; Teinte/Saturation aussi colorisation allumée.
  [2] chaque jeu de paramètres passe PM.commande_autorisee (liste blanche, registre de la fixture) : 0 refus attendu,
      hors commandes « bientôt » (sansEcran) que l'écran n'envoie jamais.
  [3] témoins : le banc refuse bien quand on lui donne une valeur hors bornes (sinon un 0 refus ne prouverait rien).
  [4]-[6] Courbes/Niveaux, calques de réglage, exposition ; [7] Style de calque (etapesStyles de mod-styles.js) : 0 refus.
  [8] VRAI moteur (t138 B6) : ombre portée appliquée puis désactivée sur un calque rempli, « tout coché » = 10 effets ;
      rouge si le binaire manque. Sections [1]-[7] hors ligne ; node requis. Le registre passe par FICHIER temporaire (ligne de commande ≤ 32 767 car.).
Run : & $PY -X utf8 tests/test_photolab_formulaires.py   (depuis backend/)"""
import asyncio, collections, json, os, pathlib, shutil, subprocess, sys, tempfile
# t138 B6 : la section [8] (VRAI moteur) passe par l'application : dossier de données temporaire AVANT tout import de app.
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt138b6_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.setdefault("FAL_KEY", "test-key")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_registre as PR             # noqa: E402
from app.services import photolab_moteur as PM               # noqa: E402

OUTIL = ROOT / "frontend" / "photolab" / "qa" / "outils" / "formulaires.mjs"
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:1500]}")


COMMANDES = json.loads((BACKEND / "tests" / "photocraft_commandes_0.3.0.json").read_text(encoding="utf-8"))
REG = PR.structurer(COMMANDES)

print("[1] formulaires remplis par mod-champs.js (node)")
node = shutil.which("node")
check("1.1 node présent", node is not None)
check("1.2 l'outil existe", OUTIL.is_file(), OUTIL)
sortie = []
if node and OUTIL.is_file():
    with tempfile.TemporaryDirectory() as d:
        entree, res = pathlib.Path(d) / "registre.json", pathlib.Path(d) / "formulaires.json"
        entree.write_text(json.dumps({k: {"champs": v["champs"]} for k, v in REG.items()}), encoding="utf-8")
        r = subprocess.run([node, str(OUTIL), str(entree), str(res)], capture_output=True, text=True, encoding="utf-8")
        check("1.3 l'outil tourne", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            sortie = json.loads(res.read_text(encoding="utf-8"))
ids = {o["id"] for o in sortie}
check("1.4 tout le périmètre est rempli (≥ 150 commandes)", len(ids) >= 150, len(ids))
check("1.5 neuf saisies par commande (+ colorisation pour Teinte/Saturation)",
      len(sortie) == 9 * len(ids) + 9 * 2, (len(sortie), len(ids)))
check("1.6 scénario « défaut » : des paramètres pour la plupart des filtres",
      sum(1 for o in sortie if o["scen"] == "defaut" and o["id"].startswith("filter.") and o["params"]) >= 50)

print("\n[2] chaque formulaire passe la liste blanche du pont")
refus = collections.defaultdict(list)
vus = 0
for o in sortie:
    if o["sans"]:
        continue                                              # « bientôt » : l'écran ne l'envoie jamais
    if o["aig"] == "galerie":
        continue                                              # t157 : éditeur sur mesure (mod-galerie), banc test_photolab_masques
    vus += 1
    try:
        PM.commande_autorisee(o["id"], o["params"], REG)
    except ValueError as e:
        refus[o["scen"]].append(f"{o['id']} {json.dumps(o['params'])[:160]} -> {e}")
check("2.1 des formulaires ont été vérifiés", vus > 1000, vus)
for scen in ("defaut", "zorg", "grand", "negatif", "nan", "virgule", "tableau", "hex3", "vide"):
    l = refus.get(scen, []) + refus.get(scen + "+colorize", [])
    check(f"2.2 « {scen} » : 0 refus", not l, "\n    " + "\n    ".join(sorted(set(l))[:12]))
bientot = sorted({o["id"] for o in sortie if o["sans"]})
# SANS_EDITEUR (mod-champs.js) : Personnalisé (kernel int[25] requis, non éditable). t157 : Convertir pour les filtres
# dynamiques en est sorti (le panneau Calques les montre) et la Galerie a son éditeur (aiguillage « galerie »).
# edit.puppetWarp (D9) est hors du périmètre de ce banc (préfixe edit.).
check("2.3 « bientôt » du périmètre = D9 + SANS_EDITEUR + Déplacement + Correspondance + Flamme (8)", bientot == sorted([
    "filter.adaptiveWideAngle", "filter.cameraRaw", "filter.distort.displace",
    "filter.liquify", "filter.other.custom", "filter.render.flame", "filter.vanishingPoint",
    "image.adjustments.matchColor"]), bientot)
check("2.3b Galerie : aiguillée vers son éditeur (t157)", {o["aig"] for o in sortie if o["id"] == "filter.filterGallery"} == {"galerie"})
ts = [o for o in sortie if o["id"] == "image.adjustments.hueSaturation" and o["scen"] == "grand+colorize"]
check("2.4 colorisation : hue 1e9 -> 360, saturation -> 100", ts and ts[0]["params"].get("hue") == 360 and ts[0]["params"].get("saturation") == 100,
      ts and ts[0]["params"])
fu = [o for o in sortie if o["id"] == "layer.layerStyle.dropShadow" and o["scen"] == "zorg"]
check("2.5 blend « zorg » -> défaut du registre (multiply)", fu and fu[0]["params"].get("blend") == "multiply", fu and fu[0]["params"])

print("\n[3] témoins : le pont refuse ce que l'écran ne doit pas produire")
for cid, p in (("filter.blur.gaussianBlur", {"radius": 5000}), ("layer.layerStyle.dropShadow", {"blend": "zorg"}),
               ("image.adjustments.hueSaturation", {"hue": 300}), ("filter.noise.addNoise", {"seed": "3"})):
    try:
        PM.commande_autorisee(cid, p, REG); refuse = False
    except ValueError:
        refuse = True
    check(f"3 {cid} {p} refusé", refuse)

# t138 B4 : les éditeurs Courbes / Niveaux (mod-courbes.js) fabriquent leurs paramètres eux-mêmes (points, canaux,
# niveaux) : leurs éditions types passent elles aussi la liste blanche, destructives et calque de réglage.
print("\n[4] Courbes et Niveaux sur mesure (qa/outils/courbes.mjs)")
OUTIL_COURBES = ROOT / "frontend" / "photolab" / "qa" / "outils" / "courbes.mjs"
editions = []
if node and OUTIL_COURBES.is_file():
    with tempfile.TemporaryDirectory() as d:
        res = pathlib.Path(d) / "courbes.json"
        r = subprocess.run([node, str(OUTIL_COURBES), str(res)], capture_output=True, text=True, encoding="utf-8")
        check("4.1 l'outil tourne", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            editions = json.loads(res.read_text(encoding="utf-8"))
else:
    check("4.1 l'outil existe", False, OUTIL_COURBES)
check("4.2 éditions types produites (≥ 16)", len(editions) >= 16, len(editions))
refus_c = []
for o in editions:
    try:
        PM.commande_autorisee(o["command"], o["params"], REG)
    except ValueError as e:
        refus_c.append(f"{o['nom']} {o['command']} {json.dumps(o['params'])[:200]} -> {e}")
check("4.3 0 refus de la liste blanche", not refus_c, "\n    " + "\n    ".join(refus_c[:12]))
noms = {o["nom"]: o["params"] for o in editions}
s5 = noms.get("courbe à 5 points", {})
check("4.4 courbe à 5 points : clé points seule, 5 points", list(s5) == ["points"] and len(s5["points"]) == 5, s5)
check("4.5 canal bleu seul : clé blue seule", list(noms.get("canal bleu seul", {})) == ["blue"], noms.get("canal bleu seul"))
check("4.6 19 points envoyés tels quels", len(noms.get("19 points sur les 4 canaux", {}).get("red", [])) == 19)
for cid, p in (("image.adjustments.curves", {"points": [[0, 0], [255, 255], [128, 128]]}),
               ("image.adjustments.curves", {"blue": [[0, 0], [128, 300], [255, 255]]}),
               ("image.adjustments.levels", {"inBlack": 254})):
    try:
        PM.commande_autorisee(cid, p, REG); refuse = False
    except ValueError:
        refuse = True
    check(f"4.7 témoin refusé : {cid} {json.dumps(p)}", refuse)

# t138 B5 : l'éditeur d'un calque de réglage (mod-reglages.js) part de depuisInspect(doc.inspect) et envoie
# layer.setAdjustment {layer, ...difference}. Les 21 états relevés sur le VRAI moteur (fixture reglages-inspect.json),
# relus puis édités contrôle par contrôle, passent la liste blanche avec le kind et l'état du calque visé — comme la
# route /executer les lit dans doc.inspect.
print("\n[5] calques de réglage : depuisInspect et éditions (qa/outils/reglages.mjs)")
OUTIL_REGLAGES = ROOT / "frontend" / "photolab" / "qa" / "outils" / "reglages.mjs"
FIXTURE_REGLAGES = ROOT / "frontend" / "photolab" / "qa" / "fixtures" / "reglages-inspect.json"
reglages = []
if node and OUTIL_REGLAGES.is_file():
    with tempfile.TemporaryDirectory() as d:
        entree, res = pathlib.Path(d) / "registre.json", pathlib.Path(d) / "reglages.json"
        entree.write_text(json.dumps({k: {"champs": v["champs"]} for k, v in REG.items()
                                      if k.startswith("layer.newAdjustmentLayer.")}), encoding="utf-8")
        r = subprocess.run([node, str(OUTIL_REGLAGES), str(entree), str(res)], capture_output=True, text=True, encoding="utf-8")
        check("5.1 l'outil tourne", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            reglages = json.loads(res.read_text(encoding="utf-8"))
else:
    check("5.1 l'outil existe", False, OUTIL_REGLAGES)
fixture_r = json.loads(FIXTURE_REGLAGES.read_text(encoding="utf-8"))
etats = [o for o in reglages if o["nom"].endswith(" état relu")]
check("5.2 les 21 états de la fixture sont relus", len(etats) == len(fixture_r) == 21, (len(etats), len(fixture_r)))
check("5.3 éditions produites pour les 16 kinds (≥ 400 jeux)",
      len(reglages) >= 400 and {o["kind"] for o in reglages} == set(PR.KINDS.values()), len(reglages))
refus_r = []
for o in reglages:
    try:
        PM.commande_autorisee("layer.setAdjustment", {"layer": 1, **o["params"]}, REG, o["kind"], etat=o["etat"])
    except ValueError as e:
        refus_r.append(f"{o['nom']} {json.dumps(o['params'])[:200]} -> {e}")
check("5.4 0 refus de la liste blanche (setAdjustment, kind et état du calque visé)", not refus_r,
      "\n    " + "\n    ".join(refus_r[:12]))
# témoins : le même chemin refuse bien une forme fausse (sinon 0 refus ne prouverait rien)
for kind, p in (("colorBalance", {"midtones": [150, 0, 0]}), ("channelMixer", {"red": [100, 0, 0]}),
                ("hueSaturation", {"reds": {"hue": 10, "zorg": 1}}), ("gradientMap", {"stops": [[0, [1, 2, 3]], [1, "#ffffff"]]}),
                ("levels", {"points": [[0, 0], [255, 255]]})):
    try:
        PM.commande_autorisee("layer.setAdjustment", {"layer": 1, **p}, REG, kind, etat=None); refuse = False
    except ValueError:
        refuse = True
    check(f"5.5 témoin refusé : {kind} {json.dumps(p)}", refuse)

# t138 B5 (relecture) : l'exposition est corrigée À LA SOURCE (photolab_registre.CORRECTIONS_CHAMPS) : le dialogue
# générique (mod-champs.parametres, mod-dialogue-reglage.depuisCurseur) envoie 0.5 EV, plus 1, et le pont l'admet.
print("\n[6] exposition en EV décimale dans le dialogue générique")
JS = ROOT / "frontend" / "photolab" / "js"
for cid in ("image.adjustments.exposure", "layer.newAdjustmentLayer.exposure"):
    champs = REG[cid]["champs"]
    code = ("const C = await import(process.argv[1]); const D = await import(process.argv[2]); const ch = JSON.parse(process.argv[3]);"
            "const e = ch.find((c) => c.cle === 'exposure');"
            "console.log(JSON.stringify({p: C.parametres(ch, {exposure: 0.5}), s: C.parametres(ch, {exposure: '0,5'}),"
            " pas: C.pasDe(e, {}), curseur: D.depuisCurseur(e, 0.5, {})}));")
    r = subprocess.run([node, "--input-type=module", "-e", code, (JS / "mod-champs.js").as_uri(),
                        (JS / "mod-dialogue-reglage.js").as_uri(), json.dumps(champs)],
                       capture_output=True, text=True, encoding="utf-8") if node else None
    res = json.loads(r.stdout) if r and r.returncode == 0 else {}
    check(f"6.1 {cid} : 0.5 et « 0,5 » partent à 0.5, pas 0,01, curseur 0.5",
          res.get("p", {}).get("exposure") == 0.5 and res.get("s", {}).get("exposure") == 0.5 and res.get("pas") == 0.01
          and res.get("curseur") == 0.5, (res, r.stderr[-400:] if r else "node absent"))
    try:
        PM.commande_autorisee(cid, {"exposure": 0.5}, REG); admis = True
    except ValueError:
        admis = False
    check(f"6.2 {cid} : le pont admet 0.5", admis)

# t138 B6 : le dialogue Style de calque (mod-styles.js) n'envoie que des étapes etapesStyles : chaque style coché,
# chaque champ à sa borne, saisies hostiles, désactivation (enabled:false + tous les paramètres), options de fusion
# (les 28 modes, passThrough compris) passent la liste blanche du pont.
print("\n[7] Style de calque : étapes de etapesStyles (qa/outils/styles.mjs)")
OUTIL_STYLES = ROOT / "frontend" / "photolab" / "qa" / "outils" / "styles.mjs"
styles = []
if node and OUTIL_STYLES.is_file():
    with tempfile.TemporaryDirectory() as d:
        res = pathlib.Path(d) / "styles.json"
        r = subprocess.run([node, str(OUTIL_STYLES), str(res)], capture_output=True, text=True, encoding="utf-8")
        check("7.1 l'outil tourne", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            styles = json.loads(res.read_text(encoding="utf-8"))
else:
    check("7.1 l'outil existe", False, OUTIL_STYLES)
KINDS_STYLES = {"dropShadow", "innerShadow", "outerGlow", "innerGlow", "stroke", "colorOverlay", "gradientOverlay",
                "patternOverlay", "bevelEmboss", "satin"}
check("7.2 les 10 styles et les options de fusion sont couverts (≥ 150 étapes)",
      {o["kind"] for o in styles} == KINDS_STYLES | {"blendingOptions"} and len(styles) >= 150,
      (len(styles), sorted({o["kind"] for o in styles})))
refus_s = []
for o in styles:
    try:
        PM.commande_autorisee(o["command"], o["params"], REG)
    except ValueError as e:
        refus_s.append(f"{o['nom']} {json.dumps(o['params'])[:200]} -> {e}")
check("7.3 0 refus de la liste blanche", not refus_s, "\n    " + "\n    ".join(refus_s[:12]))
desact = [o for o in styles if o["nom"].endswith(" désactivé")]
check("7.4 désactivation : enabled:false + tous les paramètres, pour les 10",
      len(desact) == 10 and all(o["params"].get("enabled") is False and len(o["params"]) >= 4 for o in desact), desact[:2])
blends = {o["params"]["blend"] for o in styles if "blend" in o["params"]}
check("7.5 toute clé blend envoyée est un des 28 ids (PR.FUSIONS), passThrough compris", blends <= set(PR.FUSIONS)
      and "passThrough" in blends and len(blends) == 28, sorted(blends))
check("7.6 le contour ne part jamais avec from/to (le moteur le passerait en dégradé)",
      not any(o["kind"] == "stroke" and ("from" in o["params"] or "to" in o["params"]) for o in styles))
for cid, p in (("layer.layerStyle.blendingOptions", {"layer": 1, "blend": "zorg"}),
               ("layer.layerStyle.dropShadow", {"layer": 1, "opacity": 150}),
               ("layer.layerStyle.stroke", {"layer": 1, "color": "rouge"})):
    try:
        PM.commande_autorisee(cid, p, REG); refuse = False
    except ValueError:
        refuse = True
    check(f"7.7 témoin refusé : {cid} {json.dumps(p)}", refuse)


# VRAI moteur : les étapes du dialogue appliquées par la route /executer sur un calque rempli ; doc.inspect montre
# l'effet puis, après la désactivation, enabled:false ; « tout coché » pose les 10 effets ; /apercu les accepte.
async def styles_reel():
    import httpx
    from app.main import app
    print("\n[8] VRAI moteur : Style de calque appliqué puis désactivé")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("8.1 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
        if not cli.is_file():
            return
    except PM.MoteurAbsent as e:
        check("8.1 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t",
                                 timeout=120) as c:
        async def ex(cmd, p):
            r = await c.post("/api/photolab/executer", json={"command": cmd, "params": p})
            return r.status_code, r.text

        async def calque_haut():
            i = (await c.get("/api/photolab/inspecter")).json()
            return next((L for L in i.get("layers", []) if L.get("name") == "haut"), None)

        r = await c.post("/api/photolab/nouveau", json={"width": 200, "height": 150, "background": "white"})
        check("8.2 document créé", r.status_code == 200, r.text[:300])
        for cmd, p in (("layer.new.layer", {"name": "haut"}),
                       ("select.rect", {"x": 50, "y": 40, "width": 100, "height": 70, "mode": "replace"}),
                       ("edit.fill", {"color": "#3366cc"}), ("select.deselect", {})):
            await ex(cmd, p)
        haut = await calque_haut()
        check("8.3 calque « haut » rempli, sans effet", haut is not None and not haut.get("effects"), haut)
        if haut is None:
            return
        lid = haut["id"]
        avec_id = lambda o: {**o["params"], "layer": lid} if "layer" in o["params"] else o["params"]
        ajout = next(o for o in styles if o["nom"] == "dropShadow coché aux défauts")
        r = await c.post("/api/photolab/apercu", json={"etapes": [{"command": ajout["command"], "params": avec_id(ajout)}], "maxSide": 256})
        check("8.4 /apercu accepte l'étape de l'ombre portée", r.status_code == 200 and "url" in r.json(), r.text[:300])
        code, txt = await ex(ajout["command"], avec_id(ajout))
        check("8.5 /executer applique l'ombre portée", code == 200, txt[:300])
        fx = ((await calque_haut()) or {}).get("effects") or {}
        check("8.6 inspect : un item Drop Shadow allumé",
              fx.get("items") == [{"enabled": True, "kind": "Drop Shadow"}], fx)
        desact = next(o for o in styles if o["nom"] == "dropShadow désactivé")
        code, txt = await ex(desact["command"], avec_id(desact))
        check("8.7 /executer applique la désactivation", code == 200, txt[:300])
        fx = ((await calque_haut()) or {}).get("effects") or {}
        check("8.8 inspect : le même item, enabled:false",
              fx.get("items") == [{"enabled": False, "kind": "Drop Shadow"}], fx)
        tout = [o for o in styles if o["nom"] == "tout coché"]
        r = await c.post("/api/photolab/apercu", json={"etapes": [{"command": o["command"], "params": avec_id(o)} for o in tout],
                                                       "maxSide": 256})
        check("8.9 /apercu accepte les 11 étapes de « tout coché »", len(tout) == 11 and r.status_code == 200, (len(tout), r.text[:300]))
        codes = [(await ex(o["command"], avec_id(o)))[0] for o in tout]
        haut = await calque_haut() or {}
        kinds = sorted(it["kind"] for it in (haut.get("effects") or {}).get("items", []))
        check("8.10 « tout coché » : 10 effets allumés au moteur, fond 60 %",
              codes == [200] * 11 and len(kinds) == 10 and all(it["enabled"] for it in haut["effects"]["items"])
              and abs((haut.get("fill") or 0) - 0.6) < 0.01, (codes, kinds, haut.get("fill")))
    PM.fermer()


try:
    asyncio.run(styles_reel())
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
