# -*- coding: utf-8 -*-
"""t211 (Espaces de marque E11, 15/10/2026) — traduction des écrans du lot et chapitre du guide « Travailler pour
plusieurs marques ». Ce que ce banc garde :
  - K : plus aucun texte visible en dur dans les paires des maillons dzespace et dzquick (la pastille « All » de la
    galerie des modèles Quick passe par dzT) ; l'aide de Réglages › Espaces ne promet plus des comptes « bientôt » ;
  - B : les catégories, titres et résumés des modèles Quick sont des DONNÉES de l'espace : data-dz-brut (sinon le
    runtime traduisait « Produit » en « Multiply ») ;
  - C : dzCtSeq — deux changements d'espace rapprochés : la réponse dépassée n'écrase pas la plus récente (simulé
    dans node avec un faux serveur aux réponses dans le désordre ; la base d'avant donnait l'espace dépassé) ;
  - G : le chapitre `marques` (famille Démarrer, v3, après Réglages), FR et EN, ses trois scènes capturées en FR et
    EN ; le chapitre Quick décrit les onglets en icônes, le menu persona, le zoom et l'orbe ; les scènes Quick et le
    tour de la coque sont refaits sur les écrans du 15/10 (plan t211, jamais le 8765).
Run (depuis backend/) : & $PY tests/test_espaces_guide.py"""
import importlib.util, json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def module(nom, src=None):
    spec = importlib.util.spec_from_file_location(nom, RACINE / "scripts" / f"{nom}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


BUNDLE = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(encoding="utf-8-sig")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "espaces.json").read_text(encoding="utf-8"))
DZE, DZQ = module("patch_bundle_dzespace"), module("patch_bundle_dzquick")

print("[K] clés")
EXEMPTS = {"×", "v2.8.0"}
durs = []
for m in (DZE, DZQ):
    for _a, n in m.PAIRES:
        for x in re.findall(r'(?:children|placeholder|title|"aria-label"|alt):"([^"]*[A-Za-zÀ-ÿ][^"]*)"', n):
            if x not in EXEMPTS and not x.startswith("e.g. "):        # S11 : l'exemple part au modèle, en anglais (L2)
                durs.append(x)
check("K1 aucun texte visible en dur dans les paires dzespace / dzquick", not durs, str(durs))
check("K2 la pastille « Toutes » de la galerie passe par dzT (plus de « All » en dur)",
      'children:dzT("espaces.ct.filtre_toutes")' in BUNDLE and 'onClick:()=>n("all"),children:"All"' not in BUNDLE
      and DICO["espaces.ct.filtre_toutes"] == {"fr": "Toutes", "en": "All"})
check("K3 « Toutes les catégories » (le menu du dialogue des modèles) intact",
      DICO["espaces.ct.toutes"] == {"fr": "Toutes les catégories", "en": "All categories"})
aide = DICO["espaces.reglages.aide"]
check("K4 l'aide des espaces ne promet plus les comptes « bientôt »", "bientôt" not in aide["fr"] and "soon" not in aide["en"]
      and "comptes de diffusion" in aide["fr"] and "publishing accounts" in aide["en"])
# une phrase FR = une traduction (règle L0-L7) pour les textes neufs
tout = {}
for f in (RACINE / "frontend" / "shared" / "i18n").glob("*.json"):
    for k, v in json.loads(f.read_text(encoding="utf-8")).items():
        if isinstance(v, dict) and isinstance(v.get("fr"), str):
            tout.setdefault(v["fr"], set()).add(v.get("en"))
check("K5 « Toutes » a une seule traduction dans toute l'interface", tout.get("Toutes") == {"All"}, str(tout.get("Toutes")))

print("[B] données de l'espace jamais traduites")
check("B1 les catégories de modèles portent data-dz-brut",
      'children:r.jsx("span",{"data-dz-brut":"1",children:i.label})},i.id))]})' in BUNDLE)
check("B2 titres et résumés des modèles portent data-dz-brut",
      'r.jsx("div",{"data-dz-brut":"1",style:{fontSize:12,color:"var(--ink-strong)",fontWeight:500},children:i.title})' in BUNDLE
      and 'r.jsx("div",{"data-dz-brut":"1",style:{fontSize:10.5,color:"var(--ink-soft)",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"},children:i.short})' in BUNDLE)
try:
    avant = DZQ.defaire(BUNDLE)
    avant = DZE.defaire(avant)
except AssertionError as e:
    avant = "ERREUR " + str(e)
check("B3 l'inverse des maillons retire T1-T2, dzCtSeq et la pastille traduite ; aller-retour exact",
      "dzCtSeq" not in avant and "espaces.ct.filtre_toutes" not in avant and 'children:i.label},i.id))]})' in avant
      and DZQ.appliquer(DZE.appliquer(avant)) == BUNDLE, avant[:120])

print("[C] course des contenus")
def simuler(bundle):
    i = bundle.index("var dzEspCt=null,dzCtAbonnes=[]")
    j = bundle.index('try{window.addEventListener("deepotus:espace-refresh"', i)
    aides = bundle[i:j]
    js = ("var window={addEventListener:function(){}};var actif='deepotus',FILE=[];"
          "function rep(o){return Promise.resolve({ok:true,json:function(){return Promise.resolve(o)}})}"
          # GET /espaces/actif répond tout de suite ; GET /contenus attend qu'on le libère (dans le désordre)
          "function fetch(u){if(/\\/espaces\\/actif$/.test(u))return rep({id:actif,nom:actif});"
          "var id=decodeURIComponent(u.split('/')[3]);return new Promise(function(r){FILE.push(function(){r({ok:true,json:function(){"
          "return Promise.resolve({prompt_templates:[{title:id}]})}})})})}"
          + aides +
          ";dzCtCharger(true);actif='rippled';setTimeout(function(){dzCtCharger(true);setTimeout(function(){"
          "FILE[1]();setTimeout(function(){FILE[0]();setTimeout(function(){console.log(dzEspCt&&dzEspCt.id)},20)},20)},20)},20)")
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8")
    return (r.stdout + r.stderr).strip()
base = subprocess.run(["git", "show", "cdb34331:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("C0 témoin : sur la base (cdb34331), la réponse dépassée (Deepotus) écrase la plus récente",
      base.returncode == 0 and simuler(base.stdout.decode("utf-8-sig")) == "deepotus", simuler(base.stdout.decode("utf-8-sig"))[:200] if base.returncode == 0 else "git show")
check("C1 avec dzCtSeq, l'espace le plus récent (Rippled) reste affiché", simuler(BUNDLE) == "rippled", simuler(BUNDLE)[:200])

print("[G] guide")
GUIDE = RACINE / "docs" / "guide"
som = json.loads((GUIDE / "src" / "chapitres.json").read_text(encoding="utf-8"))
ids = [c["id"] for c in som["chapitres"]]
ch = next((c for c in som["chapitres"] if c["id"] == "marques"), {})
check("G1 chapitre « marques » : Démarrer, v3, juste après Réglages, titres FR/EN",
      ch.get("famille") == "demarrer" and ch.get("etat") == "v3" and ids.index("marques") == ids.index("reglages") + 1
      and ch.get("fr") == "Travailler pour plusieurs marques" and ch.get("en") == "Work for several brands", str(ch))
frag = {l: (GUIDE / "src" / l / "marques.html").read_text(encoding="utf-8") for l in ("fr", "en")}
scenes = {l: re.findall(r'data-scene="([^"]+)"', frag[l]) for l in frag}
check("G2 les deux langues montrent les mêmes trois scènes", scenes["fr"] == scenes["en"] == ["marques/creer", "marques/quick", "marques/exporter"], str(scenes))
for s in scenes["fr"]:
    d = GUIDE / "src" / "scenes" / s
    sj = json.loads((d / "scene.json").read_text(encoding="utf-8"))
    imgs = [c[l] for c in sj["captures"] for l in ("fr", "en")]
    check(f"G3 {s} : capturée en FR et EN ({len(sj['captures'])} captures, {len(sj['temps'])} temps), servie dans img/",
          all((d / f).is_file() and (GUIDE / "img" / "scenes" / s / f).is_file() for f in imgs) and 2 <= len(sj["temps"]) <= 3, str(imgs))
for mot in ("Exporter", "Importer un espace…", "Archiver", "Définir le persona", "Relevé du mois (CSV)", "+ Nouveau persona…"):
    check(f"G4 le chapitre FR cite « {mot} » comme à l'écran", f'<b class="ui">{mot}</b>' in frag["fr"])
check("G5 le chapitre dit qu'aucun secret n'est exporté et que le logo de l'app ne suit pas l'espace",
      "Aucun secret" in frag["fr"] and "No secret" in frag["en"] and "logo et le nom de l'application ne changent jamais" in frag["fr"])
q = {l: (GUIDE / "src" / l / "quick.html").read_text(encoding="utf-8") for l in ("fr", "en")}
check("G6 Quick : onglets en icônes, menu persona (lien #marques), zoom et orbe, en FR et EN",
      all('href="#marques"' in q[l] and "dz-action-zoom-avant" in q[l] and "dz-media-forme-onde" in q[l] for l in q)
      and "en icônes" in q["fr"] and "as icons" in q["en"] and '<b class="ui">Compositing</b>' in q["en"])
plan = json.loads((GUIDE / "src" / "scenes" / "plans" / "t211.json").read_text(encoding="utf-8"))
refaites = {"quick/seedance", "quick/camera", "tour/coque"}
check("G7 le plan t211 refait les scènes Quick et la coque, sur un backend de preuve (jamais le 8765)",
      refaites <= {s["scene"] for s in plan["scenes"]} and ":8765" not in json.dumps(plan))
sd = json.loads((GUIDE / "src" / "scenes" / "quick" / "seedance" / "scene.json").read_text(encoding="utf-8"))
check("G8 la scène Seedance montre la barre d'onglets en icônes (bulle « le nom au survol »)",
      sd["temps"][0]["bulle"]["fr"] == "Les onglets en icônes : le nom au survol" and len(sd["temps"]) == 3)
html = {l: (GUIDE / f"{l}.html").read_text(encoding="utf-8") for l in ("fr", "en")}
check("G9 le guide construit contient le chapitre dans les deux langues",
      'id="marques"' in html["fr"] and 'id="marques"' in html["en"] and "Travailler pour plusieurs marques" in html["fr"]
      and "Work for several brands" in html["en"])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
