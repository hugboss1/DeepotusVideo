# -*- coding: utf-8 -*-
"""Studio — l'aperçu de composition montre le VRAI bandeau de marque (suite de t227, 17/10/2026).

Relevé (base 55893568) : l'aperçu de l'inspecteur de Composition spatiale (`dzPreviewModel` → `dzPvCell`, item
kind "brand") dessinait un bandeau EN DUR, « 🐙 DEEPOTUS » à gauche et « $DEEP » à droite, quels que soient le modèle
et le Bandeau de marque relié. Le rendu réel (backend, template_service) pose le logo PNG du modèle (item `mark`) et
le 1er item texte de la région brand_strip ; depuis t226 (paire B3), `dzCompose` remplace ce texte par celui du
Bandeau de marque relié au port `brand` (ou le texte du catalogue, l'espace actif), et laisse la région intacte si le
texte est vide, identique, ou si un autre type de nœud est relié.

Ce que ce banc garde (sous node, fonctions réelles du bundle) :
  [M] `dzPreviewModel` : l'item brand porte le texte effectif (même règle que B3), sa couleur, et la présence du logo ;
  [R] `dzPvCell` : le texte affiché est ce texte (avec `title`), le pictogramme du logo seulement si le modèle a un
      `mark`, plus aucun « $DEEP » en dur ;
  [C] cohérence : texte de l'aperçu == texte que `dzCompose` envoie au rendu, pour chaque cas ;
  [D] maillon de queue `dzstudio`, famille F* : sans les F* = livré t227 (55893568) octet pour octet, comptes figés,
      aucun texte visible neuf, aucun useState.
Run (depuis backend/) : & $PY tests/test_studio_apercu_bandeau.py"""
import json, os, pathlib, subprocess, sys, tempfile
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
TD = RACINE / "backend" / "app" / "templates"
TPLS = {n: json.loads((TD / f"{n}.json").read_text(encoding="utf-8"))
        for n in ("tpl_news_reel", "tpl_oracle_full_with_lower_third", "tpl_alpha_reel_60_30_10")}
# modèle sans logo : la région brand_strip de news_reel privée de son item mark
_sans = json.loads(json.dumps(TPLS["tpl_news_reel"]))
_sans["id"] = "tpl_sans_logo"
for _r in _sans["regions"]:
    if _r["type"] == "brand_strip":
        _r["items"] = [it for it in _r["items"] if it.get("type") != "mark"]
TPLS["tpl_sans_logo"] = _sans


def tranche(s, a, b):
    i = s.find(a)
    if i < 0:
        return ""
    j = s.find(b, i)
    return s[i:j] if j > 0 else ""


HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const TPLS=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
const sp=new Function(tranche("function dzSpatialSlots(","function dzNodeInPorts(")+";return dzSpatialSlots")();
const Wt=(g,id,p)=>{const ed=g.edges.find(x=>x.to===id&&x.toPort===p);return ed?g.nodes.find(n=>n.id===ed.from)||null:null};
const Me={BrandStrip:{props:{get mark(){return "🐙"},get text(){return "ESPACEACTIF"}}}};
const r={jsx(t,p,k){return{t,p,k}},jsxs(t,p,k){return{t,p,k}}};
const BASE={dzT:(k,v)=>k+(v?JSON.stringify(v):""),Wt,dzSpatialSlots:sp,Me,r,dzIsImgNode:()=>false,dzReach:()=>false,
 dzFinVide:()=>false,dzFinImg:()=>null,dzSSML:x=>x,dzMq:k=>k,D:{imageUrl:x=>x,jobVideoUrl:x=>x,listHeygenAvatars:async()=>({}),listHeygenVoices:async()=>({})}};
function texts(el){const o=[];(function w(n){if(n==null||n===false)return;if(typeof n==="string"){o.push(n);return}
 if(Array.isArray(n)){n.forEach(w);return}if(n.p)w(n.p.children)})(el);return o}
function graphe(tplId,brand){
 const nodes=[{id:"n1",type:"Upload",props:{filename:"clip.mp4"}},{id:"n6",type:"SpatialCompose",props:{templateId:tplId}},{id:"n8",type:"Render",props:{}}];
 const edges=[{id:"e1",from:"n1",fromPort:"out",to:"n6",toPort:"reel"},{id:"e2",from:"n6",fromPort:"out",to:"n8",toPort:"in"}];
 if(brand){nodes.push(Object.assign({id:"n5"},brand));edges.push({id:"e7",from:"n5",fromPort:"out",to:"n6",toPort:"brand"})}
 return{nodes,edges};
}
async function apercu(g,tplId){
 const ENV=Object.assign({},BASE,{__dzTplCache:{},fetch:async()=>({ok:true,json:async()=>JSON.parse(JSON.stringify(TPLS[tplId]))})});
 const f=new Function("ENV","with(ENV){return "+tranche("async function dzPreviewModel(","function dzPvCell(")+"}")(ENV);
 const m=await f(g);
 const br=(m.items||[]).filter(x=>x.kind==="brand");
 const PV=new Function("ENV","with(ENV){"+(()=>{const i=S.indexOf("function dzPvCell(");const j=S.indexOf("\nfunction ",i+10);return S.slice(i,j)})()+";return dzPvCell}")(ENV);
 return{ok:m.ok,brand:br.map(b=>{const el=PV(b,1080,0,null);return{item:b,texts:texts(el),
  titles:(function t(n,o){if(!n||typeof n!=="object")return o;if(Array.isArray(n)){n.forEach(x=>t(x,o));return o}
   if(n.p){if(n.p.title)o.push(n.p.title);t(n.p.children,o)}return o})(el,[])}})};
}
async function compose(g,tplId){
 const appels=[];
 const ENV=Object.assign({},BASE,{fetch:async()=>({ok:true,json:async()=>JSON.parse(JSON.stringify(TPLS[tplId]))}),
  D:Object.assign({},BASE.D,{renderLayoutTemplate:(...a)=>{appels.push(a);return{ok:true}}})});
 const f=new Function("ENV","with(ENV){return "+tranche("async function dzCompose(","function DzOpenGraph(")+"}")(ENV);
 await f(g,g.nodes.find(n=>n.id==="n8"),g.nodes.find(n=>n.id==="n6"),"9:16",{});
 const a=appels[0]||[];const def=a[3]||TPLS[tplId];
 return (def.regions||[]).filter(x=>x.type==="brand_strip").map(x=>{const t=(x.items||[]).find(i=>i.type==="text");return t?t.text:""});
}
(async()=>{
 const CAS=[["relie","tpl_news_reel",{type:"BrandStrip",props:{text:"MAMARQUE",mark:"🐙"}}],
  ["defaut","tpl_news_reel",{type:"BrandStrip",props:{}}],["sans","tpl_news_reel",null],
  ["vide","tpl_news_reel",{type:"BrandStrip",props:{text:"  "}}],["meme","tpl_news_reel",{type:"BrandStrip",props:{text:"$DEEPOTUS"}}],
  ["autre","tpl_news_reel",{type:"Image",props:{filename:"x.png"}}],
  ["oracle","tpl_oracle_full_with_lower_third",null],["oracle_relie","tpl_oracle_full_with_lower_third",{type:"BrandStrip",props:{text:"MAMARQUE"}}],
  ["alpha","tpl_alpha_reel_60_30_10",null],["alpha_relie","tpl_alpha_reel_60_30_10",{type:"BrandStrip",props:{text:"ALPHA"}}],
  ["sans_logo","tpl_sans_logo",{type:"BrandStrip",props:{text:"NUE"}}]];
 for(const [k,tpl,b] of CAS){
  try{const g=graphe(tpl,b);OUT[k]={ap:await apercu(g,tpl),rendu:await compose(g,tpl)}}
  catch(e){OUT[k]={err:String(e&&e.stack||e).slice(0,500)}}
 }
 process.stdout.write(JSON.stringify(OUT));
})();
"""

d = pathlib.Path(tempfile.mkdtemp(prefix="dzapercu_node_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(RAW)
(d / "t.json").write_text(json.dumps(TPLS), encoding="utf-8")
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js"), str(d / "t.json")], capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
try:
    OUT = json.loads(rn.stdout or "{}")
except ValueError:
    OUT = {"err": rn.stdout[-300:] + rn.stderr[-300:]}


def cas(k):
    v = OUT.get(k) or {}
    return v if "err" not in v else {}


def br(k):
    b = (cas(k).get("ap") or {}).get("brand") or []
    return b[0] if b else {}


check("0 harnais node : dzPreviewModel, dzPvCell et dzCompose exécutés sur chaque cas",
      "err" not in OUT and all(cas(k) for k in ("relie", "defaut", "sans", "oracle", "alpha", "sans_logo")),
      str({k: v.get("err", "")[:200] for k, v in OUT.items() if isinstance(v, dict) and "err" in v} or OUT.get("err", ""))[:400])

print("[M] modèle d'aperçu : l'item brand porte le texte effectif")
check("M1 Bandeau relié : texte du nœud", br("relie").get("item", {}).get("text") == "MAMARQUE", str(br("relie").get("item")))
check("M2 Bandeau relié sans texte propre : texte du catalogue (espace actif)",
      br("defaut").get("item", {}).get("text") == "ESPACEACTIF", str(br("defaut").get("item")))
for k, lab in (("sans", "M3 sans lien"), ("vide", "M4 texte vide"), ("meme", "M5 même texte"),
               ("autre", "M6 autre type de nœud sur brand (Image)")):
    check(f"{lab} : texte du modèle ($DEEPOTUS)", br(k).get("item", {}).get("text") == "$DEEPOTUS", str(br(k).get("item")))
check("M7 couleur = celle de l'item texte du modèle (#00e5ff)", br("relie").get("item", {}).get("color") == "#00e5ff",
      str(br("relie").get("item")))
check("M8 logo : présent si le modèle a un item mark", br("relie").get("item", {}).get("mark") is True
      and br("oracle").get("item", {}).get("mark") is True and br("sans_logo").get("item", {}).get("mark") is False,
      str([br(k).get("item", {}).get("mark") for k in ("relie", "oracle", "sans_logo")]))
check("M9 modèle sans item texte (oracle) : aucun texte, même relié (le rendu n'en pose pas)",
      not br("oracle").get("item", {}).get("text") and not br("oracle_relie").get("item", {}).get("text"),
      str((br("oracle").get("item"), br("oracle_relie").get("item"))))
check("M10 autre modèle (alpha) : son texte, et celui du Bandeau relié", br("alpha").get("item", {}).get("text") == "$DEEPOTUS"
      and br("alpha_relie").get("item", {}).get("text") == "ALPHA", str((br("alpha").get("item"), br("alpha_relie").get("item"))))

print("[R] rendu de la cellule d'aperçu")
check("R1 relié : la cellule affiche le texte du Bandeau", "MAMARQUE" in br("relie").get("texts", []), str(br("relie").get("texts")))
check("R2 plus aucun « $DEEP » en dur : sans lien, le texte du modèle", br("sans").get("texts", [])[-1:] == ["$DEEPOTUS"]
      and all("$DEEP" != t for k in OUT for t in br(k).get("texts", [])), str(br("sans").get("texts")))
check("R3 pictogramme du logo seulement si le modèle a un mark",
      "🐙 DEEPOTUS" in br("relie").get("texts", []) and "🐙 DEEPOTUS" in br("oracle").get("texts", [])
      and "🐙 DEEPOTUS" not in br("sans_logo").get("texts", []), str([br(k).get("texts") for k in ("relie", "oracle", "sans_logo")]))
check("R4 oracle (logo seul) : rien d'autre que le logo", br("oracle").get("texts") == ["🐙 DEEPOTUS"], str(br("oracle").get("texts")))
check("R5 le texte a un title (libellé complet si l'ellipse le coupe)", "MAMARQUE" in br("relie").get("titles", []),
      str(br("relie").get("titles")))
PV = BUNDLE[BUNDLE.find("function dzPvCell("):BUNDLE.find("\nfunction ", BUNDLE.find("function dzPvCell(") + 10)]
check("R6 dzPvCell : plus de littéral « $DEEP »", '"$DEEP"' not in PV and "it.text" in PV)

print("[C] cohérence aperçu ↔ rendu (dzCompose)")
for k in ("relie", "defaut", "sans", "vide", "meme", "autre", "oracle", "oracle_relie", "alpha", "alpha_relie", "sans_logo"):
    ap = br(k).get("item", {}).get("text") or ""
    rd = (cas(k).get("rendu") or [None])[0]
    check(f"C {k} : aperçu == rendu ({ap!r})", cas(k) and ap == (rd or ""), f"aperçu {ap!r} / rendu {rd!r}")

print("[D] maillon de queue dzstudio, famille F*")
import patch_bundle_dzstudio as M                                    # noqa: E402
import _i18n_l1_aide as AIDE                                         # noqa: E402


def git_bundle(rev):
    r_ = subprocess.run(["git", "show", f"{rev}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
    if r_.returncode != 0:
        return None
    b_ = r_.stdout                                  # blob normalisé LF (autocrlf) → les CRLF du fichier extrait
    return b_ if b"\r\n" in b_ else b_.replace(b"\n", b"\r\n")


PF = list(getattr(M, "PAIRES_F", []))
_AVF = len(M.PAIRES_AB) + len(M.PAIRES_C)                       # t228 : d'autres familles suivent les F* (D*)
check("D1 famille F* déclarée (PAIRES_F), juste après PAIRES_AB + PAIRES_C", len(PF) >= 2
      and M.PAIRES[:_AVF] == M.PAIRES_AB + M.PAIRES_C and M.PAIRES[_AVF:_AVF + len(PF)] == PF, str(len(PF)))
try:
    avant = M.defaire(BUNDLE)
except AssertionError as e:
    avant = None
    check("D2 toutes les paires sont dans le livré", False, str(e)[:160])
base_t227 = git_bundle("55893568")
base_t224 = git_bundle("02f8162c")
check("D3 inverse = 02f8162c octet pour octet", avant is not None and base_t224 is not None
      and AIDE.avant_dzstudio(BUNDLE).encode("utf-8") == base_t224)


def sans_f(s):
    for a_, r_ in M.PAIRES_AB + M.PAIRES_C:                      # borné à ses familles (t228 ajoute les D* après)
        s = s.replace(a_, r_, 1)
    return s


check("D4 sans les F* = 55893568 (t227) octet pour octet", avant is not None and base_t227 is not None and bool(PF)
      and sans_f(avant).encode("utf-8") == base_t227)
check("D5 aller-retour exact", avant is not None and M.appliquer(avant) == BUNDLE)
check("D6 comptes figés (useState 731, v2.8.0 ×4, DzTracks 181)",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
check("D7 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("D8 aucun .bak_dzstudio laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzstudio")).exists())
check("D9 aucun texte visible neuf (pas de dzT ajouté), aucun useState dans les F*",
      bool(PF) and all(r_.count("dzT(") == a_.count("dzT(") and "useState" not in r_ for a_, r_ in PF))
check("D10 garde : un bundle t227 (sans les F*) est « partiellement appliqué »",
      avant is not None and bool(PF) and M.partiel(sans_f(avant)) and not M.partiel(BUNDLE))
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzstudio.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("D11 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
