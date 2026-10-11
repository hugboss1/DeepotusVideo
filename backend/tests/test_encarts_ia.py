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
  [c0] chaque page de lab qui génère charge /shared/dz-modeles-ia.js (Atelier,
       Material Forge, Spritelab, Photolab ; le Vectorlab en G8 : sa page est
       figée par la table L6) ;
  [c1] Card Forge : l'option d'un modèle sans clé porte la mention (face,
       cadre), le lot ne désactive plus rien et ne refuse plus côté écran (le
       serveur dit 503), « aucune clé » se lit sur cle_absente ; le repli de
       core.js lit `tous` ; tables L7 et L8 à jour (--check) ;
  [c2] Atelier : #daProvider lit `tous` (DzModelesIA), l'image de production
       prend son prix au catalogue (/ia/catalogue), plus à la grille.

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
a0 = B.find("function dzImgLbl(")
code = B[a0:B.find("function DzImgModelSel(", a0)]
sonde = ("var DICO=" + json.dumps(DICO, ensure_ascii=False) + ";function dzT(k,v){var t=DICO[k]||k;"
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
    ch2 = (R / "frontend/shared/dz-champ-ia.js").read_text(encoding="utf-8")
    check("la pastille rejoue CE libellé (vue = nom · prix · mention, comme dzImgLbl)",
          'vue: (e.label || e.id) + " · " + px + (!e.dispo && e.cle ? " · " + CLE_A_AJOUTER(e.cle) : "")' in ch2)

# ── [b2] l'inverse ───────────────────────────────────────────────────────────
print("[b2] inverse avant_encartsia")
import _i18n_l1_aide as AIDE                                     # noqa: E402
sans = AIDE.avant_encartsia(B)
check("avant_encartsia défait les paires : plus de marqueur, `models` revient",
      ENC.MARKER not in sans and "(mm.models||[]).map(function(m){return{value:m.id,label:m.label}})" in sans)
check("aller-retour exact à l'octet", ENC.appliquer(sans) == B)
check("avant_dzguide défait D'ABORD encartsia (posé après lui)", ENC.MARKER not in AIDE.avant_dzguide(B))
check("un bundle sans le maillon passe tel quel", AIDE.avant_encartsia(sans) == sans)
r = subprocess.run([sys.executable, str(R / "scripts/patch_bundle_encartsia.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(R))
check("double application refusée", r.returncode != 0 and "double application" in (r.stdout + r.stderr), r.stdout + r.stderr)

# ── [c0] pages des labs ──────────────────────────────────────────────────────
print("[c0] pages des labs")
for lab in ("atelier", "materialforge", "spritelab", "photolab"):
    html = (R / f"frontend/{lab}/index.html").read_text(encoding="utf-8")
    check(f"{lab} charge dz-modeles-ia.js (une fois)", html.count('<script src="/shared/dz-modeles-ia.js"></script>') == 1)

# ── [c1] Card Forge ─────────────────────────────────────────────────────────
print("[c1] Card Forge")
cf = {n: lire(f"frontend/cardforge/js/{n}") for n in ("mod-face.js", "mod-frame.js", "mod-data.js", "core.js")}
check("face : mention sur l'option sans clé ; « aucune clé » via cle_absente",
      'm.dispo === false && m.cle ? " — " + esc(dzT("cartes.face.cle_a_ajouter", { cle: m.cle }))' in cf["mod-face.js"]
      and "if (!MODELS.length || AI_META.cle_absente) {" in cf["mod-face.js"])
check("cadre : mention sur l'option sans clé ; « aucune clé » via cle_absente",
      'm.dispo === false && m.cle ? " — " + esc(dzT("cartes.frame2.cle_a_ajouter", { cle: m.cle }))' in cf["mod-frame.js"]
      and "if (!AI_MODELS.length || AI_META.cle_absente) {" in cf["mod-frame.js"])
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

print(f"\n{OK} ok, {KO} fail")
sys.exit(1 if KO else 0)
