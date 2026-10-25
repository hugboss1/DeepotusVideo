# -*- coding: utf-8 -*-
"""Studio — le port « brand » de Composition spatiale (t226, 16/10/2026).

Défaut relevé (docs/superpowers/specs/2026-10-16-releve-menus-studio.md, cause 4 « Port fantôme brand ») :
`dzSpatialSlots` ne crée de port image que pour les régions `image_slot` ; la région `r_brand` de `tpl_news_reel` est
un `brand_strip` → aucun port `brand` affiché, alors que le graphe de départ « Post reel News » relie Bandeau de marque
→ `brand`. `qi` ne trouvait pas l'index et rendait {x:0,y:0} : le lien atterrissait au coin haut-gauche du nœud.
Relevé t226 : `dzCompose` sautait la région brand_strip (seuls video_slot / image_slot sont lus) et le backend la
dessine d'après les `items` du modèle — le nœud relié n'était lu par personne. Décision de l'utilisateur (16/10) :
(a) port `brand` exposé + le TEXTE du Bandeau de marque relié remplace celui du bandeau (le logo PNG du modèle reste,
l'emoji du nœud est ignoré) ; sans lien, rendu identique.

Ce que ce banc garde :
  [P] `dzSpatialSlots` (extrait, sous node) : tpl_news_reel expose `brand` (type image, slot = id de la région, libellé
      sans texte neuf) APRÈS les ports existants ; pas de doublon si une image_slot a déjà pris `brand` ; rien sans
      brand_strip ;
  [Q] `qi` d'un port introuvable ne rend plus jamais {x:0,y:0} (bord du nœud, ligne sous le dernier port) ; le port
      `brand` de Composition spatiale tombe sur la 3e ligne du nœud ;
  [K] `dzCompose` (extrait, sous node, gabarit réel) : la région brand_strip est mappée au port `brand` ; le texte
      du nœud relié remplace le 1er item texte ; logo et autres régions intacts ; sans lien ou même texte → aucun
      gabarit modifié envoyé (rendu identique) ;
  [R] test_studio_r8 intact (`var sp=dzSpatialSlots(tpl,hit.sc.props||{})` ×1) ;
  [D] maillon de queue dzstudio : paires B* au maillon EXISTANT (pas dans spatialports), inverse = 02f8162c octet pour
      octet, sans les B* = 0b62e7c4 (t225), comptes figés.
Run (depuis backend/) : & $PY tests/test_studio_ports_spatial.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")
TPL = json.loads((RACINE / "backend" / "app" / "templates" / "tpl_news_reel.json").read_text(encoding="utf-8"))

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const TPL=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
function garde(k,f){try{OUT[k]=f()}catch(e){OUT[k]={err:String(e&&e.stack||e).slice(0,400)}}}
const K=/bi=(\d+),Ru=(\d+),Mu=(\d+)/.exec(S);const bi=+K[1],Ru=+K[2],Mu=+K[3];OUT.bi=bi;OUT.Ru=Ru;OUT.Mu=Mu;
const SLOTS=tranche("function dzSpatialSlots(","function dzNodeInPorts(");
const sp=new Function(SLOTS+";return dzSpatialSlots")();
garde("news",()=>sp(TPL,{}).ports);
garde("double",()=>sp({regions:[{type:"video_slot",slot_name:"v"},{type:"image_slot",slot_name:"logo",slot_label:"Logo"},
 {id:"r_b",type:"brand_strip"}]},{}).ports);
garde("sans",()=>sp({regions:[{type:"video_slot",slot_name:"v"},{type:"separator"}]},{}).ports);
garde("deux_bandeaux",()=>sp({regions:[{type:"video_slot",slot_name:"v"},{id:"b1",type:"brand_strip"},{id:"b2",type:"brand_strip"}]},{}).ports);
garde("seq",()=>sp(Object.assign({},TPL,{render_mode:"sequential"}),{scenes:2}).ports);
// qi : géométrie + port introuvable
garde("qi",()=>{
 const i0=S.indexOf("var dzPortGeo=");const SRC=(i0>=0?tranche("var dzPortGeo=","function qi("):"")+tranche("function qi(","function Th(");
 const P=n=>Array.from({length:n},(_,i)=>({id:"p"+i,type:"av"}));
 const Me={T:{inPorts:P(3),outPorts:P(2)},SpatialCompose:{inPorts:[{id:"reel"},{id:"avatar"},{id:"s3"},{id:"s4"},{id:"s5"},{id:"s6"},{id:"brand"},{id:"bg"}],outPorts:[{id:"out"}]}};
 const dzNodeInPorts=nd=>nd&&nd.type==="SpatialCompose"?sp(TPL,nd.props||{}).ports:null;
 const qi=new Function("ENV","with(ENV){"+SRC+";return qi}")({Me,bi,Ru,Mu,dzNodeInPorts});
 const nd={id:"n6",type:"SpatialCompose",props:{templateId:"tpl_news_reel"}};
 return{in_absent:qi("T","in","zz",null),out_absent:qi("T","out","zz",null),in2:qi("T","in","p2",null),out1:qi("T","out","p1",null),
  brand:qi("SpatialCompose","in","brand",nd),avatar:qi("SpatialCompose","in","avatar",nd),fantome:qi("SpatialCompose","in","s9",nd)};
});
// dzCompose : gabarit réel, Upload sur reel, BrandStrip (ou rien) sur brand
async function compose(graphe,lProps){
 const SRC=tranche("async function dzCompose(","function DzOpenGraph(");
 const appels=[];
 const ENV={
  dzT:(k,v)=>k+(v?JSON.stringify(v):""),fetch:async()=>({ok:true,json:async()=>JSON.parse(JSON.stringify(TPL))}),
  Wt:(g,id,p)=>{const ed=g.edges.find(x=>x.to===id&&x.toPort===p);return ed?g.nodes.find(n=>n.id===ed.from)||null:null},
  dzSpatialSlots:sp,dzFinVide:()=>false,dzFinImg:()=>null,dzIsImgNode:()=>false,dzSSML:x=>x,dzMq:k=>k,dzReach:()=>false,
  Me:{BrandStrip:{props:{get mark(){return "🐙"},get text(){return "ESPACEACTIF"}}}},
  D:{renderLayoutTemplate:(...a)=>{appels.push(a);return{ok:true}},listHeygenAvatars:async()=>({}),listHeygenVoices:async()=>({})}};
 const f=new Function("ENV","with(ENV){return "+SRC+"}")(ENV);
 const l=graphe.nodes.find(n=>n.id==="n6"),t=graphe.nodes.find(n=>n.id==="n8");
 const res=await f(graphe,t,l,"9:16",{});
 return{res,appels:appels.map(a=>({tplId:a[0],slots:a[1],def:a[3]}))};
}
function graphe(brand){
 const nodes=[{id:"n1",type:"Upload",props:{filename:"clip.mp4"}},{id:"n6",type:"SpatialCompose",props:{templateId:"tpl_news_reel"}},
  {id:"n8",type:"Render",props:{}}];const edges=[{id:"e1",from:"n1",fromPort:"out",to:"n6",toPort:"reel"},{id:"e2",from:"n6",fromPort:"out",to:"n8",toPort:"in"}];
 if(brand){nodes.push(Object.assign({id:"n5",type:"BrandStrip"},brand));edges.push({id:"e7",from:"n5",fromPort:"out",to:"n6",toPort:"brand"})}
 return{nodes,edges};
}
(async()=>{
 for(const [k,g] of [["relie",graphe({props:{text:"MAMARQUE",mark:"🐙"}})],["defaut",graphe({props:{}})],["meme",graphe({props:{text:"$DEEPOTUS"}})],
  ["vide",graphe({props:{text:"  "}})],["sans",graphe(null)],["autre",{nodes:graphe(null).nodes.concat([{id:"n5",type:"Image",props:{filename:"x.png"}}]),
  edges:graphe(null).edges.concat([{id:"e7",from:"n5",fromPort:"out",to:"n6",toPort:"brand"}])}]]){
  try{OUT["c_"+k]=await compose(g)}catch(e){OUT["c_"+k]={err:String(e&&e.stack||e).slice(0,400)}}
 }
 process.stdout.write(JSON.stringify(OUT));
})();
"""

d = pathlib.Path(tempfile.mkdtemp(prefix="dzports_node_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(RAW)
(d / "t.json").write_text(json.dumps(TPL), encoding="utf-8")
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js"), str(d / "t.json")], capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
try:
    OUT = json.loads(rn.stdout or "{}")
except ValueError:
    OUT = {"err": rn.stdout[-300:] + rn.stderr[-300:]}
check("0 harnais node exécuté", "err" not in OUT and OUT.get("news") is not None, str(OUT.get("err", rn.stderr[-300:]))[:300])


def ports(k):
    v = OUT.get(k)
    return v if isinstance(v, list) else []


print("[P] dzSpatialSlots expose le port brand du bandeau")
news = ports("news")
ids = [p.get("id") for p in news]
br = next((p for p in news if p.get("id") == "brand"), {})
check("P1 tpl_news_reel : un port « brand »", ids.count("brand") == 1, str(ids))
check("P2 brand : type image (comme le port du catalogue), slot = id de la région r_brand",
      br.get("type") == "image" and br.get("slot") == "r_brand", str(br))
check("P3 libellé sans texte neuf (aucun slot_label sur la région → « brand »)", br.get("label") == "brand", str(br))
check("P4 ports existants inchangés et en tête (reel, avatar), brand APRÈS", ids[:2] == ["reel", "avatar"] and ids[-1:] == ["brand"],
      str(ids))
check("P5 image_slot déjà sur « brand » : pas de doublon",
      [p.get("id") for p in ports("double")].count("brand") == 1
      and next((p for p in ports("double") if p.get("id") == "brand"), {}).get("slot") == "logo", str(ports("double")))
check("P6 sans brand_strip : aucun port brand", "brand" not in [p.get("id") for p in ports("sans")], str(ports("sans")))
check("P7 deux bandeaux : seul le PREMIER a le port", [(p.get("id"), p.get("slot")) for p in ports("deux_bandeaux")
                                                     if p.get("id") == "brand"] == [("brand", "b1")], str(ports("deux_bandeaux")))
check("P8 mode séquentiel : brand toujours exposé", "brand" in [p.get("id") for p in ports("seq")], str(ports("seq")))

print("[Q] qi : plus jamais {x:0,y:0}")
Q = OUT.get("qi") or {}
bi, Ru, Mu = OUT.get("bi"), OUT.get("Ru"), OUT.get("Mu")
_oy = re.search(r"var dzPortGeo=\{b:1,oy:(\d+),", BUNDLE)          # t227 : oy 10 → 8 (lu, plus en dur)
OY = int(_oy.group(1)) if _oy else None
def ligne(i):
    return 1 + Ru + OY + i * Mu + 8 if Ru is not None and OY is not None else None
check("Q0 qi extrait", isinstance(Q, dict) and "err" not in Q, str(Q)[:300])
check("Q1 port introuvable (entrée) ≠ {0,0} : bord gauche, ligne sous le dernier port",
      Q.get("in_absent") == {"x": 1, "y": ligne(3)}, str(Q.get("in_absent")))
check("Q2 port introuvable (sortie) ≠ {0,0} : bord droit, ligne sous le dernier port",
      Q.get("out_absent") == {"x": bi - 1, "y": ligne(2)} if bi else False, str(Q.get("out_absent")))
check("Q3 ports trouvés inchangés (t225)", Q.get("in2") == {"x": 1, "y": ligne(2)} and Q.get("out1") == {"x": bi - 1, "y": ligne(1)}
      if bi else False, str((Q.get("in2"), Q.get("out1"))))
check("Q4 Composition spatiale : « brand » sur la 3e ligne (reel, avatar, brand)",
      Q.get("brand") == {"x": 1, "y": ligne(2)}, str(Q.get("brand")))
check("Q5 avatar toujours 2e ligne", Q.get("avatar") == {"x": 1, "y": ligne(1)}, str(Q.get("avatar")))
check("Q6 port fantôme de Composition spatiale ≠ {0,0}", isinstance(Q.get("fantome"), dict) and Q.get("fantome") != {"x": 0, "y": 0}
      and Q["fantome"].get("x") == 1, str(Q.get("fantome")))

print("[K] dzCompose mappe la région brand_strip au port brand")
def appel(k):
    c = OUT.get("c_" + k) or {}
    a = c.get("appels") or []
    return c, (a[0] if a else {})
def region(df, rid):
    return next((r for r in ((df or {}).get("regions") or []) if r.get("id") == rid), None)
tpl_brand = next(r for r in TPL["regions"] if r["id"] == "r_brand")
c, a = appel("relie")
rb = region(a.get("def"), "r_brand")
check("K0 compose exécuté, renderLayoutTemplate appelé une fois", "err" not in c and len(c.get("appels") or []) == 1,
      str(c)[:300])
check("K1 nœud relié : gabarit modifié envoyé, texte du bandeau = texte du nœud",
      rb is not None and [it.get("text") for it in rb.get("items", []) if it.get("type") == "text"] == ["MAMARQUE"], str(rb))
check("K2 logo PNG du modèle intact (l'emoji du nœud est ignoré)",
      rb is not None and [it for it in rb.get("items", []) if it.get("type") == "mark"] ==
      [it for it in tpl_brand["items"] if it.get("type") == "mark"], str(rb))
check("K3 le reste de la région intact (position, fond, police, taille, couleur)",
      rb is not None and {k: v for k, v in rb.items() if k != "items"} == {k: v for k, v in tpl_brand.items() if k != "items"}
      and [{k: v for k, v in it.items() if k != "text"} for it in rb["items"]] ==
      [{k: v for k, v in it.items() if k != "text"} for it in tpl_brand["items"]], str(rb))
check("K4 autres régions et slots inchangés",
      a.get("def") is not None and [r for r in a["def"]["regions"] if r.get("id") != "r_brand"] ==
      [r for r in TPL["regions"] if r["id"] != "r_brand"] and a.get("slots") == {"reel": {"source_kind": "upload",
                                                                                         "upload_filename": "clip.mp4"}},
      str(a.get("slots")))
c, a = appel("defaut")
rb = region(a.get("def"), "r_brand")
check("K5 nœud sans texte propre : le texte par défaut du catalogue (espace actif)",
      rb is not None and [it.get("text") for it in rb["items"] if it.get("type") == "text"] == ["ESPACEACTIF"], str(rb))
for k, lab in (("sans", "K6 sans lien : aucun gabarit modifié (rendu identique)"),
               ("meme", "K7 même texte que le modèle : aucun gabarit modifié"),
               ("vide", "K8 texte vide : le modèle garde le sien"),
               ("autre", "K9 autre type de nœud sur brand (Image) : bandeau du modèle")):
    c, a = appel(k)
    check(lab, "err" not in c and len(c.get("appels") or []) == 1 and a.get("def") is None, str(c)[:300])
K = BUNDLE[BUNDLE.find("async function dzCompose("):BUNDLE.find("function DzOpenGraph(")]
check("K10 le mappage passe par la carte région → port de dzSpatialSlots", "__regionPort[" in K and 'rg5.type==="brand_strip"' in K)
check("K11 le gabarit modifié part quand le bandeau change (hasMods)", "||__trMod||__brMod;" in K)

print("[R] test_studio_r8 intact")
check("R1 `var sp=dzSpatialSlots(tpl,hit.sc.props||{})` ×1", BUNDLE.count("var sp=dzSpatialSlots(tpl,hit.sc.props||{})") == 1)
check("R2 le format HeyGen ne regarde que les video_slot",
      'rg=pt&&tpl.regions.find(function(z){return z.type==="video_slot"&&z.slot_name===pt.slot})' in BUNDLE)

print("[D] maillon de queue dzstudio, famille B*")
import patch_bundle_dzstudio as M                                    # noqa: E402
import _i18n_l1_aide as AIDE                                         # noqa: E402


# t280 : la couche sonvfx a été retouchée après ces bases (consignée L4 + G1, réinjectée par refresh_layer) — le bloc
# SONVFX attendu est celui du livré ; ce banc vérifie ses maillons HORS de ce bloc
def git_bundle(rev):
    b_ = _git_bundle_brut(rev)
    return None if b_ is None else __import__("_i18n_l1_aide").base_avec_couches_livrees(
        b_, (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes())


def _git_bundle_brut(rev):
    r = subprocess.run(["git", "show", f"{rev}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
    if r.returncode != 0:
        return None
    b = r.stdout                                    # blob normalisé LF (autocrlf) → les CRLF du fichier extrait
    return b if b"\r\n" in b else b.replace(b"\n", b"\r\n")


src_m = (RACINE / "scripts" / "patch_bundle_dzstudio.py").read_text(encoding="utf-8")
PB = [p for p in M.PAIRES if p[1].find("dzPortGeo={") < 0 and ("dzBs" in p[1] or "__brMod" in p[1] or "_lst.length" in p[1])]
check("D1 paires B* présentes dans le maillon dzstudio (≥ 3)", len(PB) >= 3 and src_m.count("# B") >= 3, str(len(PB)))
sp_src = (RACINE / "scripts" / "patch_bundle_spatialports.py")
check("D2 spatialports non réécrit (couche amont)", not sp_src.exists() or "dzBs" not in sp_src.read_text(encoding="utf-8")
      and subprocess.run(["git", "diff", "--quiet", "0b62e7c4", "--", "scripts/patch_bundle_spatialports.py"],
                         cwd=str(RACINE)).returncode == 0)
try:
    avant = M.defaire(AIDE.avant_dzmotion(BUNDLE))       # t235 : le maillon dzmotion, posé APRÈS, défait d'abord
except AssertionError as e:
    avant = None
    check("D3 toutes les paires sont dans le livré", False, str(e)[:160])
base_t224 = git_bundle("02f8162c")
base_t225 = git_bundle("0b62e7c4")
check("D4 inverse = 02f8162c octet pour octet", avant is not None and base_t224 is not None
      and AIDE.avant_dzstudio(BUNDLE).encode("utf-8") == base_t224)
def sans_b(s):
    for a_, r_ in M.PAIRES:
        if (a_, r_) not in PB and (a_, r_) in getattr(M, "PAIRES_AB", M.PAIRES):   # t227 : C*, F*… viennent après
            s = s.replace(a_, r_, 1)
    return s
check("D5 sans les B* = 0b62e7c4 (t225) octet pour octet", avant is not None and base_t225 is not None
      and sans_b(avant).encode("utf-8") == base_t225)
check("D6 aller-retour exact", avant is not None and M.appliquer(avant) == AIDE.avant_dzmotion(BUNDLE))
check("D7 marqueur ×1", BUNDLE.count(M.MARKER) == 1)
check("D8 comptes figés (useState 731, v2.8.0 ×4, DzTracks 181)",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
check("D9 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("D10 aucun .bak_dzstudio laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzstudio")).exists())
check("D11 aucun texte visible neuf dans les B* (pas de dzT ajouté)", all(r_.count("dzT(") == a_.count("dzT(") for a_, r_ in PB))
check("D12 aucun useState dans les B*", all("useState" not in r_ for _a, r_ in PB))
try:
    _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
except (OSError, ValueError, KeyError):
    _g1 = []
check("D13 remplacements G1 intacts", bool(_g1) and avant is not None and all(BUNDLE.count(x) == avant.count(x) for x in _g1))
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzstudio.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("D14 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
