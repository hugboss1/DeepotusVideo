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
  [b1] bundle, maillon de queue scripts/patch_bundle_encartsia.py : aides
       dzImgLbl/dzImgOpts posées une fois ; DzImgModelSel et DzImageModel lisent
       `tous` raster rangé par voie (plus `models` seul) ; DzVideoModelSel et
       DzVoModelSel disent « clé X à ajouter dans Réglages » (plus « clé
       manquante ») ; compteurs figés (useState 731, DzTracks 181), CRLF
       homogène, aucun .bak_encartsia ; node exécute dzImgOpts : vectoriel
       écarté, fal d'abord, libellé = celui que la pastille rejoue ;
  [b2] inverse avant_encartsia : aller-retour exact à l'octet, défait EN TÊTE
       d'avant_dzguide, double application refusée.
  [r]  relecture : UNE règle de prix et UN ordre des voies — le corps de
       prixUsd et ORDRE de dz-modeles-ia.js (la source) sont ceux de
       dz-champ-ia.js et du maillon ; sous node, le CODE RÉEL du bundle
       (dzImgOpts) et le chargeur RÉEL de la pastille (CHARGEURS.image, couche
       chargée avec un faux fetch) rendent, sur un même jeu (usd 0.145 / 0 /
       null / absent, dispo vrai / faux / absent, un svg, une voie inconnue),
       les mêmes entrées dans le même ordre, libellé du select == `vue` ; les
       aides sont au niveau du MODULE (vues par DzGameAssets).
  [c0] chaque page de lab qui génère charge /shared/dz-modeles-ia.js (Atelier,
       Material Forge, Spritelab, Photolab ; le Vectorlab en G8 : sa page est
       figée par la table L6) ;
  [c1] Card Forge : l'option d'un modèle sans clé porte la mention (face,
       cadre), le lot ne désactive plus rien et ne refuse plus côté écran (le
       serveur dit 503), « aucune clé » se lit sur cle_absente ; le repli de
       core.js lit `tous` ; tables L7 et L8 à jour (--check) ;
  [c2] Atelier : #daProvider lit `tous` (DzModelesIA), l'image de production
       prend son prix au catalogue (/ia/catalogue), plus à la grille.
  [d1] Material Forge : plus de MODEL_COST littéral (crédit = usd du
       catalogue), #model par DzModelesIA sur `tous` ;
  [d2] bundle : plus de `var ENG=[{value:"tripo"` ni de table RATES ; les
       moteurs 3D viennent de /api/assets3d/engines (dzEngOpts exécuté sous
       node : prix « ~$ », mention de clé, service local à démarrer) ;
  [d3] son-vfx-montage.js : SVM_GENS sans « gratuit », sans « ~$0.10 » ni
       « $0.08 » ; le bloc sonvfx du bundle est la couche à l'octet ;
  [d4] Spritelab : #pmModel rempli par DzModelesIA, le modèle part dans
       /images/generate ; tables L4 et L9 à jour (--check) ;
  [d5] i18n : ia.modele.choisir et ia.local.a_demarrer en fr et en.

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
      'T("ia.cle.a_ajouter"' in mi and 'T("ia.prix.a_mesurer")' in mi and sans_commentaires(mi).count("gratuit") == 1 and '"ia.voie.local": "local, gratuit"' in mi)   # seule la voie locale l'est
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
for nom in ("generate", "generate_batch", "generate_composition", "render_layout_template", "render_episode"):
    m = re.search(r"\nasync def " + nom + r"\(.*?(?=\n@router\.)", rt, re.S)
    corps = m.group(0) if m else ""
    i, j = corps.find("_cle_video_ou_503("), corps.find("await _plafond(")
    k = corps.find("_garde_cout(")
    check(f"{nom} : _cle_video_ou_503 avant _garde_cout et _plafond", 0 <= i < j and (k < 0 or i < k), f"{i} {k} {j}")

# ── [b1] bundle : maillon encartsia ──────────────────────────────────────────
print("[b1] bundle : sélecteurs de modèle sur le catalogue")
import json                                                       # noqa: E402
sys.path.insert(0, str(R / "scripts"))
sys.path.insert(0, str(R / "backend" / "tests"))
import patch_bundle_encartsia as ENC                              # noqa: E402
BUN = R / "frontend/dist/assets/index-BEOJX8L5.js"
braw = BUN.read_bytes()
B = braw.decode("utf-8")
check("marqueur dzImgOpts posé une fois", B.count(ENC.MARKER) == 1 and B.count("function dzImgLbl(") == 1)
i = B.find("function DzImgModelSel(")
sel = B[i:B.find("}function DzImgPrev(", i)]
check("DzImgModelSel lit dzImgOpts(mm) (plus `models` seul)",
      ".concat(dzImgOpts(mm))" in sel and "(mm.models||[]).map(" not in sel, sel[-200:])
i = B.find("function DzImageModel(")
dim = B[i:B.find("function DzPromptAI(", i)]
check("DzImageModel lit dzImgOpts(d)", "setModels(dzImgOpts(d)" in dim and "setModels(d.models||[])" not in dim, dim[:300])
check("vidéo et voix : « clé X à ajouter » (plus « clé manquante ») dans les sélecteurs",
      'dzT("reglages.modeles.cle_manquante")' not in B
      and B.count('dzT("ia.cle.a_ajouter",{cle:m2.provider==="google"?"GEMINI_API_KEY":"FAL_KEY"})') == 1
      and B.count('dzT("ia.cle.a_ajouter",{cle:"ELEVENLABS_API_KEY"})') == 1)
check("compteurs figés : useState 731, DzTracks 181", B.count("x.useState(") == 731 and B.count("DzTracks") == 181,
      f"{B.count('x.useState(')} {B.count('DzTracks')}")
check("CRLF homogène (lecture en octets)", braw.count(b"\r\n") > 15000 and braw.count(b"\n") == braw.count(b"\r\n")
      and "read_text(" not in (R / "scripts/patch_bundle_encartsia.py").read_text(encoding="utf-8"))
check("aucun .bak_encartsia laissé", not BUN.with_name(BUN.name + ".bak_encartsia").exists())
DICO = {"ia.cle.a_ajouter": "clé {cle} à ajouter dans Réglages", "ia.prix.a_mesurer": "prix à mesurer"}
a0 = B.find("function dzPrixUsd(")
code = B[a0:B.find("var dzEngCat=", a0)]
sonde = ("var window={};var DICO=" + json.dumps(DICO, ensure_ascii=False) + ";function dzT(k,v){var t=DICO[k]||k;"
         "for(var x in (v||{}))t=t.split('{'+x+'}').join(v[x]);return t}" + code
         + ";var T=[{id:'gpt-image-2',label:'GPT Image 2',voie:'openai',usd:0.12,dispo:false,cle:'OPENAI_API_KEY',sortie:'raster'},"
         "{id:'recraft',label:'Recraft',voie:'fal',usd:0.08,dispo:true,cle:'FAL_KEY',sortie:'svg'},"
         "{id:'flux',label:'FLUX schnell',voie:'fal',usd:0.003,dispo:true,cle:'FAL_KEY',sortie:'raster'},"
         "{id:'qwen',label:'Qwen',voie:'fal',usd:0,dispo:true,cle:'FAL_KEY',sortie:'raster'}];"
         "console.log(JSON.stringify([dzImgOpts({tous:T,models:[]}),dzImgOpts({models:[{id:'flux',label:'FLUX schnell',usd:0.003}]})]))")
if node:
    pr = subprocess.run([node, "-e", sonde], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        O, O2 = json.loads(pr.stdout)
    except ValueError:
        O, O2 = None, None
    check("dzImgOpts : vectoriel écarté, fal d'abord (ordre stable), libellé · prix · mention, prix inconnu « à mesurer »",
          O == [{"value": "flux", "label": "FLUX schnell · $0.003/image"},
                {"value": "qwen", "label": "Qwen · prix à mesurer"},
                {"value": "gpt-image-2", "label": "GPT Image 2 · $0.12/image · clé OPENAI_API_KEY à ajouter dans Réglages"}],
          (pr.stdout + pr.stderr)[:600])
    check("dzImgOpts : serveur d'avant t182 (sans `tous`) → `models`",
          O2 == [{"value": "flux", "label": "FLUX schnell · $0.003/image"}], str(O2))

# ── [r] relecture : une règle de prix, un ordre des voies, un même rendu ──────
print("[r] une règle de prix, un ordre des voies, bundle == pastille")
mi_src = lire("frontend/shared/dz-modeles-ia.js")
ch_src = lire("frontend/shared/dz-champ-ia.js")


def corps_prix(txt, nom):
    i = txt.find("function " + nom + "(usd, unite) ")
    return txt[i + len("function " + nom + "(usd, unite) "):txt.find("\n", i)].strip() if i >= 0 else None


cp_mi, cp_ch, cp_b = corps_prix(mi_src, "prixUsd"), corps_prix(ch_src, "prixUsd"), corps_prix(B, "dzPrixUsd")
cp_b = cp_b.split("var dzVoiesOrdre=")[0] if cp_b else None
check("prixUsd : MÊME corps dans dz-modeles-ia.js (source), dz-champ-ia.js et le maillon du bundle",
      bool(cp_mi) and cp_mi == cp_ch == cp_b, f"{cp_mi!r}\n{cp_ch!r}\n{cp_b!r}")
o_mi = re.search(r"var ORDRE = (\[[^\]]*\]);", mi_src)
o_ch = re.search(r"var ORDRE_VOIES = (\[[^\]]*\]);", ch_src)
o_b = re.search(r"var dzVoiesOrdre=(\[[^\]]*\]);", B)
check("ordre des voies : MÊME tableau dans DzModelesIA.ORDRE, ORDRE_VOIES (pastille) et dzVoiesOrdre (bundle)",
      bool(o_mi and o_ch and o_b) and json.loads(o_mi.group(1)) == json.loads(o_ch.group(1)) == json.loads(o_b.group(1)),
      str([x and x.group(1) for x in (o_mi, o_ch, o_b)]))
if node:
    pr = subprocess.run([node, str(R / "frontend/shared/qa/modeles_ia.test.mjs")], capture_output=True, text=True, encoding="utf-8")
    FIX = [
        {"id": "p1", "label": "P un", "voie": "openai", "usd": 0.145, "dispo": False, "cle": "OPENAI_API_KEY", "sortie": "raster"},
        {"id": "p2", "label": "P deux", "voie": "fal", "usd": 0, "dispo": True, "cle": "FAL_KEY", "sortie": "raster"},
        {"id": "p3", "label": "P trois", "voie": "fal", "usd": None, "cle": "FAL_KEY"},
        {"id": "p4", "voie": "gemini", "dispo": False, "cle": "GEMINI_API_KEY"},
        {"id": "svg1", "label": "Vect", "voie": "fal", "usd": 0.08, "dispo": True, "sortie": "svg"},
        {"id": "p5", "label": "P cinq", "voie": "nouvelle-voie", "usd": 0.22, "dispo": True},
        {"id": "p6", "label": "P six", "voie": "fal", "usd": 0.04, "dispo": True, "cle": "FAL_KEY"},
    ]
    harnais = r"""
const fs = require("fs");
const FIX = JSON.parse(process.argv[2]), AIDES = fs.readFileSync(process.argv[3], "utf8"), COUCHE = fs.readFileSync(process.argv[4], "utf8");
const FR = { "ia.prix.a_mesurer": "prix à mesurer", "ia.cle.a_ajouter": "clé {cle} à ajouter dans Réglages" };
function dzT(k, v) { let t = FR[k] || k; for (const x in (v || {})) t = t.split("{" + x + "}").join(v[x]); return t; }
const B = new Function("dzT", "window", AIDES + ";return { dzImgOpts: dzImgOpts };")(dzT, {});
const ob = B.dzImgOpts({ default: "p2", tous: FIX });
const document = { addEventListener() {}, body: null, documentElement: {} };
const window = { document, addEventListener() {}, setTimeout, localStorage: { getItem() { return null; } },
  fetch: (u) => Promise.resolve({ ok: true, json: () => Promise.resolve({ default: "p2", models: [], tous: FIX }) }) };
global.window = window; global.document = document;
eval(COUCHE);
window.DzChampIA.modeles.charger("image", true).then((o) => {
  console.log(JSON.stringify({ bundle: ob, pastille: o.modeles.map((m) => ({ value: m.id, label: m.vue, dispo: m.dispo, sansCle: m.sansCle })) }));
});
"""
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="encia_"))
    (tmp / "h.js").write_text(harnais, encoding="utf-8")
    (tmp / "aides.js").write_text(code, encoding="utf-8")
    pr = subprocess.run([node, str(tmp / "h.js"), json.dumps(FIX), str(tmp / "aides.js"), str(R / "frontend/shared/dz-champ-ia.js")],
                        capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        RR = json.loads(pr.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        RR = {}
    ob, op = RR.get("bundle") or [], RR.get("pastille") or []
    ATT = [("p2", "P deux · prix à mesurer"), ("p3", "P trois · prix à mesurer"), ("p6", "P six · $0.04/image"),
           ("p1", "P un · $0.145/image · clé OPENAI_API_KEY à ajouter dans Réglages"),
           ("p4", "p4 · prix à mesurer · clé GEMINI_API_KEY à ajouter dans Réglages"), ("p5", "P cinq · $0.22/image")]
    check("bundle (dzImgOpts réel) : ordre des voies, svg écarté, voie inconnue en dernier, prix et mention à la règle",
          [(o["value"], o["label"]) for o in ob] == ATT, str(ob) + (pr.stderr or "")[:300])
    check("pastille (CHARGEURS.image réel) : MÊMES entrées, MÊME ordre, `vue` == libellé du select du bundle",
          [(o["value"], o["label"]) for o in op] == [(o["value"], o["label"]) for o in ob] and len(op) == 6, str(op))
    check("dispo absent = disponible, dispo faux = sans clé (choisissable), des deux côtés",
          {o["value"]: (o["dispo"], o["sansCle"]) for o in op} == {"p1": (False, True), "p2": (True, False), "p3": (True, False),
                                                                    "p4": (False, True), "p5": (True, False), "p6": (True, False)}, str(op))
    probe = ("console.log(JSON.stringify([typeof DzGameAssets,typeof dzEngOpts,typeof dzImgOpts,typeof dzPrixUsd]));"
             "process.exit(0);\n")
    (tmp / "b.js").write_bytes(probe.encode("utf-8") + braw)
    pr = subprocess.run([node, str(tmp / "b.js")], capture_output=True, text=True, encoding="utf-8", timeout=120)
    check("les aides du maillon sont au niveau du MODULE (hissées, vues par DzGameAssets et les selects)",
          pr.stdout.strip() == '["function","function","function","function"]', (pr.stdout + pr.stderr)[:300])

# ── [b2] l'inverse ───────────────────────────────────────────────────────────
print("[b2] inverse avant_encartsia")
import _i18n_l1_aide as AIDE                                     # noqa: E402
try:
    sans = AIDE.avant_encartsia(B)
    erreur_inv = ""
except AssertionError as e:            # une paire introuvable : le bundle a dérivé du maillon (dit, sans arrêter le banc)
    sans, erreur_inv = None, str(e)
check("avant_encartsia défait les paires : plus de marqueur, `models` revient",
      sans is not None and ENC.MARKER not in sans and "(mm.models||[]).map(function(m){return{value:m.id,label:m.label}})" in sans,
      erreur_inv[:200])
check("aller-retour exact à l'octet", sans is not None and ENC.appliquer(sans) == B)
try:
    _sans_g = AIDE.avant_dzguide(B)
except AssertionError:
    _sans_g = B
check("avant_dzguide défait D'ABORD encartsia (posé après lui)", ENC.MARKER not in _sans_g)
check("un bundle sans le maillon passe tel quel", sans is not None and AIDE.avant_encartsia(sans) == sans)
r = subprocess.run([sys.executable, str(R / "scripts/patch_bundle_encartsia.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(R))
check("double application refusée", r.returncode != 0 and "double application" in (r.stdout + r.stderr), r.stdout + r.stderr)

# ── [c0] pages des labs ──────────────────────────────────────────────────────
print("[c0] pages des labs")
for lab in ("atelier", "materialforge", "spritelab"):   # relecture : le Photolab (G9) ne le charge pas encore
    html = (R / f"frontend/{lab}/index.html").read_text(encoding="utf-8")
    check(f"{lab} charge dz-modeles-ia.js (une fois)", html.count('<script src="/shared/dz-modeles-ia.js"></script>') == 1)
check("NÉGATIF : le Photolab ne charge pas dz-modeles-ia.js (rien ne l'y utilise avant G9)",
      "dz-modeles-ia.js" not in (R / "frontend/photolab/index.html").read_text(encoding="utf-8"))

# ── [c1] Card Forge ─────────────────────────────────────────────────────────
print("[c1] Card Forge")
cf = {n: lire(f"frontend/cardforge/js/{n}") for n in ("mod-face.js", "mod-frame.js", "mod-data.js", "core.js")}
check("face : mention sur l'option sans clé ; « aucune clé » via cle_absente, dit selon la règle",
      'm.dispo === false && m.cle ? " — " + esc(dzT("cartes.face.cle_a_ajouter", { cle: m.cle }))' in cf["mod-face.js"]
      and "if (MODELS.length && AI_META.cle_absente) {" in cf["mod-face.js"] and 'dzT("cartes.face.aucune_cle")' in cf["mod-face.js"])
check("cadre : mention sur l'option sans clé ; « aucune clé » via cle_absente",
      'm.dispo === false && m.cle ? " — " + esc(dzT("cartes.frame2.cle_a_ajouter", { cle: m.cle }))' in cf["mod-frame.js"]
      and "if (AI_MODELS.length && AI_META.cle_absente) {" in cf["mod-frame.js"] and 'dzT("cartes.frame2.aucune_cle")' in cf["mod-frame.js"])
mo = lire("frontend/patches/montage.js")
check("Duel : le challenger est nommé d'après `tous` (sans-clé compris)",
      "function dzDuelLabel(mm,id){var m=((mm&&mm.tous)||[]).find(" in mo)
check("lot : plus d'option désactivée ni de refus côté écran, la clé nommée",
      "LOT.model, !m.cle)" not in cf["mod-data.js"] and "if (m && !m.cle)" not in cf["mod-data.js"]
      and 'dzT("cartes.data2.cle_a_ajouter", { cle: m.cle_nom' in cf["mod-data.js"])
check("core : le repli CF.images.models() lit `tous` raster",
      "d.tous" in cf["core.js"] and 'e.sortie !== "svg"' in cf["core.js"])
for gen in ("i18n_l7_generer.py", "i18n_l8_generer.py"):
    r = subprocess.run([sys.executable, str(R / "scripts" / gen), "--check"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(R))
    check(f"table {gen} à jour (--check)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

# ── [c2] Atelier ────────────────────────────────────────────────────────────
print("[c2] Atelier")
at = lire("frontend/atelier/atelier.js")
check("#daProvider : `tous` (sans-clé compris) par DzModelesIA, la note des seeds lit la même liste",
      "const tous = (pv.tous && pv.tous.length)" in at and "window.DzModelesIA.remplir($(\"#daProvider\"), tous" in at
      and 'const sel = tous.find(p => p.id === $("#daProvider").value);' in at and "pv.providers.find(" not in at)
check("image de production : prix lu au catalogue (/ia/catalogue), plus à la grille de tarifs",
      'api.get("/ia/catalogue?nature=image")' in at and 'api.get("/cost/pricing")' not in at)

# ── [d1] Material Forge ─────────────────────────────────────────────────────
print("[d1] Material Forge")
mf = lire("frontend/materialforge/materialforge.js")
check("plus de MODEL_COST littéral (crédit = usd du catalogue)", not re.search(r"MODEL_COST\s*=\s*\{", mf)
      and "MODEL_COST" not in sans_commentaires(mf) and "Math.round(Number(ent.usd) * 100)" in mf)
check("#model : `tous` par DzModelesIA, sans-clé jamais désactivés",
      'window.DzModelesIA.remplir($("#model"), models' in mf and "d.tous" in mf
      and "disabled" not in mf[mf.index("async function loadModels("):mf.index("async function loadLibrary(")])

# ── [d2] bundle : moteurs 3D ────────────────────────────────────────────────
print("[d2] bundle : moteurs 3D lus au serveur")
B = BUN.read_bytes().decode("utf-8")
check("plus de liste de moteurs ni de table de tarifs écrites en dur",
      'var ENG=[{value:"tripo"' not in B and "var RATES={tripo:" not in B and "var ENG=dzEngOpts(p.engine);" in B
      and "dzEngCharger(function(){setPP(" in B and "var dzE=dzEngTrouve(p.engine);" in B)
check("compteurs figés après E6-E8 : useState 731, DzTracks 181",
      B.count("x.useState(") == 731 and B.count("DzTracks") == 181)
a0 = B.find("function dzPrixUsd(")
code = B[a0:B.find("function DzImgModelSel(", a0)]
e7 = B[B.find("var dzE=dzEngTrouve(p.engine);"):B.find("var meshyNoKey=", B.find("var dzE=dzEngTrouve(p.engine);"))]
check("E7 : un moteur LOCAL coûte 0 (jamais le repli 0,30)", "var cost=dzE&&dzE.local?0:" in e7, e7[:200])
DICO3 = {"ia.cle.a_ajouter": "clé {cle} à ajouter dans Réglages", "ia.local.a_demarrer": "service local à démarrer",
         "ia.prix.a_mesurer": "prix à mesurer", "ia.voie.local": "local, gratuit", "ia.etat.chargement": "chargement…"}
TETE = ("var DICO=" + json.dumps(DICO3, ensure_ascii=False)
        + ";function dzT(k,v){var t=DICO[k]||k;for(var x in (v||{}))t=t.split('{'+x+'}').join(v[x]);return t}"
        "var window={};var NF=0;")
MOTEURS = ("var REP={engines:[{id:'tripo',label:'Tripo v2.5',available:false,usd_texture:0.3,usd_brouillon:0.2},"
           "{id:'hunyuan-local',label:'Hunyuan3D 2.1 (local)',local:true,available:false,usd_texture:0,usd_brouillon:0},"
           "{id:'rodin',label:'Hyper3D Rodin',available:true,usd_texture:0.4,usd_brouillon:0.4}]};")
COUT = "function cout(p){var dzE=dzEngTrouve(p.engine);" + e7.split("\r\n")[1] + "return cost}"
# le cycle du panneau, tel que React le joue : un RENDU (dzEngOpts), puis l'EFFET passif (dzEngCharger(redessin)) ;
# le redessin rejoue un rendu. `delai` = latence de la réponse du registre (0 : elle arrive AVANT l'effet).
CYCLE = ("var RENDUS=[];function rendre(){RENDUS.push(dzEngOpts('tripo'))}"
         "function effet(){dzEngCharger(function(){rendre()})}")
def sonde_cycle(reponse, delai, avant_effet):
    return (TETE + MOTEURS + "var fetch=function(u){NF++;return new Promise(function(ok){setTimeout(function(){ok(" + reponse
            + ")}," + str(delai) + ")})};" + code + ";" + CYCLE
            + "rendre();" + ("setTimeout(effet,40);" if avant_effet else "effet();")
            + "setTimeout(function(){console.log(JSON.stringify([RENDUS,NF,dzEngCat?dzEngCat.length:null]))},120);")
OK200 = "{ok:true,json:function(){return Promise.resolve(REP)}}"
KO500 = "{ok:false,status:500,json:function(){return Promise.resolve({})}}"
sonde_ok = (TETE + MOTEURS + "var fetch=function(u){NF++;return Promise.resolve({ok:true,json:function(){return Promise.resolve(REP)}})};"
            + code + ";" + COUT + ";var avant=dzEngOpts('tripo');"
            "dzEngCharger(function(){console.log(JSON.stringify([avant,dzEngOpts('tripo'),"
            "[cout({engine:'hunyuan-local',textures:true,multiview:false}),cout({engine:'tripo',textures:true}),"
            "cout({engine:'tripo',textures:false}),cout({engine:'inconnu',textures:true})],NF]))});")
sonde_ko = (TETE + "var fetch=function(u){NF++;return Promise.resolve({ok:false,status:500,json:function(){return Promise.resolve({})}})};"
            + code + ";var a=dzEngOpts('rodin');"
            "setTimeout(function(){var b=dzEngOpts('rodin');var n1=NF;dzEngEssai=0;var c=dzEngOpts('rodin');"
            "setTimeout(function(){console.log(JSON.stringify([a,b,n1,NF,dzEngCat]))},20)},20);")
ATTENDU_REG = [{"value": "tripo", "label": "Tripo v2.5 · ~$0.30 · clé FAL_KEY à ajouter dans Réglages"},
               {"value": "hunyuan-local", "label": "Hunyuan3D 2.1 (local) · local, gratuit · service local à démarrer"},
               {"value": "rodin", "label": "Hyper3D Rodin · ~$0.40"}]
ATTENTE = [{"value": "tripo", "label": "chargement…"}]
if node:
    SECOURS = ["tripo", "tripo-h3.1", "hunyuan", "trellis", "rodin", "triposr", "hunyuan-local"]
    pr = subprocess.run([node, "-e", sonde_ok], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        E0, E1, C, NF = json.loads(pr.stdout)
    except ValueError:
        E0, E1, C, NF = None, None, None, None
    check("dzEngOpts EN ATTENTE du registre : la valeur courante, « chargement… » — jamais « prix à mesurer » ni la liste de secours",
          E0 == ATTENTE, (pr.stdout + pr.stderr)[:400])
    check("dzEngOpts : registre servi, prix « ~$ » à la règle, fal sans clé choisissable avec la mention, LOCAL « local, gratuit »",
          E1 == ATTENDU_REG and NF == 1, str(E1) + f" NF={NF}")
    check("coût du panneau : local 0, tripo texturé 0,30 / brouillon 0,20, inconnu 0,30 (le repli d'avant)",
          C == [0, 0.3, 0.2, 0.3], str(C))
    for nom, rep_, delai, avant_effet in (("réponse RAPIDE, arrivée avant l'effet du panneau (le défaut vu à l'écran)", OK200, 0, True),
                                          ("réponse LENTE, arrivée après l'effet", OK200, 30, False)):
        pr = subprocess.run([node, "-e", sonde_cycle(rep_, delai, avant_effet)], capture_output=True, text=True,
                            encoding="utf-8", timeout=60)
        try:
            RENDUS, NFc, NCAT = json.loads(pr.stdout)
        except ValueError:
            RENDUS, NFc, NCAT = None, None, None
        check(f"cycle du panneau, {nom} : 1er rendu « chargement… », puis REDESSIN sans geste de l'utilisateur sur le registre",
              bool(RENDUS) and RENDUS[0] == ATTENTE and RENDUS[-1] == ATTENDU_REG and len(RENDUS) == 2 and NFc == 1,
              (pr.stdout + pr.stderr)[:500])
    pr = subprocess.run([node, "-e", sonde_cycle(KO500, 10, False)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        RENDUS, NFc, NCAT = json.loads(pr.stdout)
    except ValueError:
        RENDUS, NFc, NCAT = None, None, None
    check("cycle du panneau, registre en ÉCHEC : 1er rendu « chargement… », puis redessin sur la liste de SECOURS, rien en cache",
          bool(RENDUS) and RENDUS[0] == ATTENTE and RENDUS[-1] == [{"value": i, "label": i + " · prix à mesurer"} for i in SECOURS]
          and NCAT is None and NFc == 1, (pr.stdout + pr.stderr)[:500])
    pr = subprocess.run([node, "-e", sonde_ko], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        K0, K1, N1, N2, CAT = json.loads(pr.stdout)
    except ValueError:
        K0 = K1 = N1 = N2 = CAT = None
    check("registre en échec (HTTP 500) : en attente « chargement… », après l'échec la liste de SECOURS, rien en cache",
          K0 == [{"value": "rodin", "label": "chargement…"}]
          and K1 == [{"value": i, "label": i + " · prix à mesurer"} for i in SECOURS] and CAT is None, (pr.stdout + pr.stderr)[:400])
    check("registre en échec : pas de rafale (un seul essai tant que 4 s ne sont pas passées), un nouvel essai ensuite",
          N1 == 1 and N2 == 2, f"{N1} {N2}")
    ch3 = lire("frontend/shared/dz-champ-ia.js")
    check("la pastille Game Assets lit toujours le select (libellés « ~$ »)", "/~\\$/" in ch3)

# ── [d3] Son & VFX ──────────────────────────────────────────────────────────
print("[d3] Son & VFX")
svm = lire("frontend/patches/son-vfx-montage.js")
i = svm.index("var SVM_GENS=[")
bloc = svm[i:svm.index("];", i)]
check("SVM_GENS sans « gratuit »", "gratuit" not in bloc, bloc[:300])
check("SVM_GENS sans prix écrit en dur (~$0.10, $0.08)", "~$0.10" not in bloc and "$0.08" not in bloc
      and 'price:dzT("son.gen.prix_sfx")' in bloc)
CR = chr(13)
bb = B.find("var SVM_GENS=[")
check("le bundle porte le même rail (couche sonvfx rafraîchie)",
      bb >= 0 and B[bb:B.index("];", bb)].replace(CR, "") == bloc.replace(CR, ""))

# (refresh_layer --check mesure la dérive contre la source COMMISE : il n'est probant qu'après le commit — la
# comparaison du rail ci-dessus porte sur la source du poste)

# ── [d4] Spritelab ──────────────────────────────────────────────────────────
print("[d4] Spritelab")
sp = lire("frontend/spritelab/spritelab.js")
sph = lire("frontend/spritelab/index.html")
check("#pmModel posé dans le panneau Prompt, rempli par DzModelesIA (catalogue image)",
      sph.count('<select id="pmModel"') == 1 and 'window.DzModelesIA.select(pmSel, "image"' in sp)
check("le modèle choisi part dans /images/generate", "imageModel ? { model: imageModel } : {}" in sp)
for gen in ("i18n_l4_generer.py", "i18n_l9_generer.py"):
    r = subprocess.run([sys.executable, str(R / "scripts" / gen), "--check"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(R))
    check(f"table {gen} à jour (--check)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

# ── [d5] i18n ───────────────────────────────────────────────────────────────
print("[d5] i18n")
com = json.loads(lire("frontend/shared/i18n/commun.json"))
check("ia.modele.choisir, ia.local.a_demarrer et ia.etat.chargement en fr et en",
      com.get("ia.modele.choisir") == {"fr": "Modèle", "en": "Model"}
      and (com.get("ia.local.a_demarrer") or {}).get("fr") and (com.get("ia.local.a_demarrer") or {}).get("en")
      and com.get("ia.etat.chargement") == {"fr": "chargement…", "en": "loading…"})
r = subprocess.run([sys.executable, str(R / "scripts/i18n_assembler.py"), "--check"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=str(R))
check("dictionnaire assemblé à jour", r.returncode == 0, r.stdout + r.stderr)

print(f"\n{OK} ok, {KO} fail")
sys.exit(1 if KO else 0)
