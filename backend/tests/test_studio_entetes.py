# -*- coding: utf-8 -*-
"""Studio — en-têtes de ports : de l'air au-dessus de l'encart, même mise en page partout (t227, 16/10/2026).

Défaut 2 du relevé (docs/superpowers/specs/2026-10-16-releve-menus-studio.md) : le corps des ports avait une hauteur
FIXE (`minHeight:16` + `padding:"8px 0"`, 16 au total) et l'encart se posait 4 plus bas (`margin:"4px 10px 0"`) ; les
lignes de ports sont en absolu : la 1re débordait de 6 dans l'encart, les suivantes s'imprimaient dessus (News script,
Rendu, Composition spatiale). Décision de l'utilisateur sur maquette (variante B, t227-maquette.png) : oy 8, lh 16,
Mu 22, air 10 MESURÉ sous le bas de la dernière ligne → corps = oy + (n − 1)·Mu + lh + air, n = max(nIn, nOut).

Ce que ce banc garde (rendu RÉEL de `Th` + `ud` + `qi` sous node, pour chaque type du catalogue `Me`) :
  [A] le corps des ports a une hauteur explicite (`dzPortBodyH`) = oy + (n − 1)·Mu + lh + air, plus de minHeight:16 ;
      nIn = ports d'entrée VISIBLES (`dzVisInPorts`) : Concatenate tronqué (sourceCount, 2..6), Composition spatiale
      par `dzNodeInPorts` (port `brand` de t226 compris) ;
  [B] l'encart (variante reef) et le pied (variante classique) se posent juste sous le corps : écart « haut de
      l'encart (ou du pied) − bas de la dernière ligne » = air pour TOUS les types, dans les deux variantes ;
  [C] `qi` et le rendu restent alignés : centre du rond = qi pour chaque port visible, tous les ronds dans le corps ;
  [D] maillon de queue `dzstudio`, famille C* : sans les C* = livré t226 (0b883708) octet pour octet, inverse exact,
      comptes figés, aperçu de composition (dzPvCell) non touché, aucun texte visible neuf.
Run (depuis backend/) : & $PY tests/test_studio_entetes.py"""
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
OY, LH, MU, AIR = 8, 16, 22, 10                     # valeurs validées sur maquette (variante B)


def tranche(s, a, b):
    i = s.find(a)
    if i < 0:
        return ""
    j = s.find(b, i)
    return s[i:j] if j > 0 else ""


TH = tranche(BUNDLE, "function Th(", "var __dzTplList=")
m = re.search(r"var dzPortGeo=\{([^}]*)\};", BUNDLE)
GEO = dict(kv.split(":", 1) for kv in m.group(1).split(",")) if m else {}

print("[A] hauteur explicite du corps des ports")
check("A1 dzPortGeo : oy 8, lh 16, pas Mu, air 10", GEO.get("oy") == str(OY) and GEO.get("lh") == str(LH)
      and GEO.get("p") == "Mu" and GEO.get("air") == str(AIR), str(GEO))
check("A2 Mu = 22", re.search(r"bi=220,Ru=36,Mu=22,", BUNDLE) is not None)
check("A3 plus de corps à hauteur fixe (minHeight:16, padding 8px 0)", 'minHeight:16,padding:"8px 0"' not in TH, TH[:0])
check("A4 le corps lit dzPortBodyH(ports d'entrée visibles, ports de sortie)",
      'style:{position:"relative",height:dzPortBodyH(dzVisInPorts(e,u).length,u.outPorts.length)}' in TH)
check("A5 les lignes d'entrée rendues = dzVisInPorts (une seule source pour la hauteur et les lignes)",
      "children:[dzVisInPorts(e,u).map(" in TH and 'e.type==="Concatenate"?u.inPorts.slice(' not in TH)
check("A6 dzPortBodyH et dzVisInPorts définis une fois, devant qi",
      BUNDLE.count("function dzPortBodyH(") == 1 and BUNDLE.count("function dzVisInPorts(") == 1
      and BUNDLE.find("var dzPortGeo={") < BUNDLE.find("function dzPortBodyH(") < BUNDLE.find("function qi(")
      and BUNDLE.find("function dzVisInPorts(") < BUNDLE.find("function qi("))

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const TPL=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const OUT={rows:[]};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
try{
 const K=/bi=(\d+),Ru=(\d+),Mu=(\d+),zh=(\d+),Eh=(\d+)/.exec(S);const bi=+K[1],Ru=+K[2],Mu=+K[3],zh=+K[4],Eh=+K[5];
 // catalogue Me réel : ports de chaque type
 const Me={};const RX=/([A-Z][A-Za-z0-9]*):\{cat:"([a-z]+)",title:[^]*?inPorts:(\[[^\]]*\]),outPorts:(\[[^\]]*\])/g;
 const i0=S.indexOf("Me={"),seg=S.slice(i0,S.indexOf("bi=220,Ru=36",i0));let mm;
 while((mm=RX.exec(seg))){Me[mm[1]]={cat:mm[2],title:mm[1],inPorts:new Function("return "+mm[3])(),outPorts:new Function("return "+mm[4])()}}
 OUT.types=Object.keys(Me);
 const SLOTS=tranche("function dzSpatialSlots(","function dzNodeInPorts(");
 const sp=new Function(SLOTS+";return dzSpatialSlots")();
 const dzNodeInPorts=nd=>{if(!nd||nd.type!=="SpatialCompose")return null;const ps=sp(TPL,nd.props||{}).ports;return ps.length?ps:null};
 const r={jsx(t,p){return{t,p}},jsxs(t,p){return{t,p}}};
 const Ur=new Proxy({},{get:()=>({color:"#9aa6b4"})});
 const Qr=new Proxy({},{get:()=>({color:"#00e5ff",icon:"x"})});
 const STUB=()=>null;
 const ENV={Me,r,Ur,Qr,bi,Ru,Mu,zh,Eh,dzNodeInPorts,dzT:k=>k,X:STUB,te:STUB,Ih:STUB,Nh:()=>"~0 s",Rh:()=>"0 $"};
 const i1=S.indexOf("var dzPortGeo=");
 const SRC=(i1>=0?tranche("var dzPortGeo=","function Th("):tranche("function qi(","function Th("))
  +";"+tranche("function Th(","var __dzTplList=")+";"+tranche("function ud(","var __dzG=");
 const M=new Function("ENV","with(ENV){"+SRC+";return{qi,Th,ud,geo:typeof dzPortGeo!=='undefined'?dzPortGeo:null}}")(ENV);
 OUT.geo=M.geo;OUT.Ru=Ru;OUT.Mu=Mu;OUT.zh=zh;OUT.Eh=Eh;OUT.bi=bi;
 const BORD=/border:`(\d+)px solid \$\{y\}`/.exec(S);const b=BORD?+BORD[1]:NaN;OUT.b=b;
 function flat(c){return Array.isArray(c)?c.flat(Infinity):[c]}
 function mesure(node,variant){
  const el=M.Th({node,variant,selected:false,status:null,onMouseDown(){},onPortPress(){},onPortRelease(){},onClick(){},onDelete:null});
  const kids=flat(el.p.children).filter(Boolean);
  const k=kids.findIndex(c=>c&&c.p&&c.p.style&&c.p.style.position==="relative");
  if(k<0)throw new Error("corps des ports introuvable");
  const body=kids[k],bs=body.p.style,next=kids.slice(k+1).filter(Boolean)[0];
  const rows=flat(body.p.children).filter(Boolean).map(c=>{const ro=M.ud(c.p);return{side:c.p.side,id:c.p.port.id,top:ro.p.style.top,
   h:ro.p.style.height,dot:ro.p.children[0].p.style}});
  const ins=rows.filter(x=>x.side==="in"),outs=rows.filter(x=>x.side==="out");
  const lastBottom=rows.length?Math.max(...rows.map(x=>x.top+x.h)):0;
  const ns=next&&next.p&&next.p.style||{};
  // marge haute de l'élément suivant (encart reef : margin ; pied classique : padding-top)
  const mt=s=>{const v=(s.margin!==undefined?String(s.margin):"0").split(/\s+/)[0];return parseFloat(v)||0};
  const pt=s=>{const v=(s.padding!==undefined?String(s.padding):"0").split(/\s+/)[0];return parseFloat(v)||0};
  const nextIsReef=ns.height===zh;
  const gap=(typeof bs.height==="number"?bs.height:NaN)-lastBottom+(nextIsReef?mt(ns):pt(ns));
  const qi=ins.map(x=>({id:x.id,q:M.qi(node.type,"in",x.id,node),cy:b+Ru+x.top+x.dot.height/2,cx:b-(x.dot.width/2)+x.dot.width/2}))
   .concat(outs.map(x=>({id:x.id,q:M.qi(node.type,"out",x.id,node),cy:b+Ru+x.top+x.dot.height/2,cx:bi-b})));
  return{type:node.type,variant,props:node.props||{},h:bs.height,minH:bs.minHeight,pad:bs.padding,nIn:ins.length,nOut:outs.length,
   ins:ins.map(x=>x.id),lastBottom,gap,nextIsReef,nextMargin:ns.margin,nextPadding:ns.padding,
   qi,maxRowBottom:lastBottom};
 }
 const NODES=[];
 for(const t of OUT.types)NODES.push({id:"n_"+t,type:t,props:{}});
 for(const sc of [2,3,6,9])NODES.push({id:"cc"+sc,type:"Concatenate",props:{sourceCount:sc}});
 for(const n of [2,5])NODES.push({id:"sc"+n,type:"SpatialCompose",props:{templateId:"tpl_news_reel",scenes:n}});
 for(const nd of NODES)for(const v of ["reef","abyssal"]){
  try{OUT.rows.push(mesure(nd,v))}catch(e){OUT.rows.push({type:nd.type,variant:v,err:String(e&&e.stack||e).slice(0,300)})}
 }
 OUT.spPorts={2:dzNodeInPorts({type:"SpatialCompose",props:{templateId:"tpl_news_reel",scenes:2}}).map(p=>p.id),
  5:dzNodeInPorts({type:"SpatialCompose",props:{templateId:"tpl_news_reel",scenes:5}}).map(p=>p.id)};
 OUT.bodyH=S.includes("function dzPortBodyH(")?[0,1,2,3,4,5,6].map(n=>new Function("ENV","with(ENV){"+tranche("var dzPortGeo=","function qi(")+";return dzPortBodyH("+n+",0)}")(ENV)):null;
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));
"""

d = pathlib.Path(tempfile.mkdtemp(prefix="dzentetes_node_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(RAW)
(d / "t.json").write_text(json.dumps(TPL), encoding="utf-8")
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js"), str(d / "t.json")], capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
try:
    OUT = json.loads(rn.stdout or "{}")
except ValueError:
    OUT = {"err": rn.stdout[-300:] + rn.stderr[-300:]}
check("A7 Th, ud, qi extraits et rendus sous node", "err" not in OUT, str(OUT.get("err", ""))[:300])
ROWS = [x for x in OUT.get("rows", []) if "err" not in x]
ERRS = [x for x in OUT.get("rows", []) if "err" in x]
TYPES = OUT.get("types", [])
check("A8 catalogue réel lu (≥ 30 types, dont News, HeyGen, Composition spatiale, Rendu, Bandeau)",
      len(TYPES) >= 30 and all(t in TYPES for t in ("NewsItem", "NewsScript", "HeyGenAvatar", "SpatialCompose", "Render",
                                                       "BrandStrip", "AvatarMaster", "Concatenate")), str(TYPES))
check("A9 chaque type rendu dans les deux variantes sans erreur", not ERRS and len(ROWS) == 2 * (len(TYPES) + 6),
      str(ERRS[:2]))
check("A10 dzPortBodyH(n) = oy + (n − 1)·Mu + lh + air, n = 1..6",
      (OUT.get("bodyH") or [None])[1:] == [OY + (n - 1) * MU + LH + AIR for n in range(1, 7)], str(OUT.get("bodyH")))
check("A11 dzPortBodyH(0) = oy + air (aucun port : jamais négatif)", (OUT.get("bodyH") or [None])[0] == OY + AIR,
      str(OUT.get("bodyH")))
check("A12 hauteur du corps = dzPortBodyH(max(nIn visibles, nOut)) pour chaque type et variante",
      ROWS and all((x.get("h") or 0) == OY + (max(x["nIn"], x["nOut"]) - 1) * MU + LH + AIR for x in ROWS if max(x["nIn"], x["nOut"])),
      [(x["type"], (x.get("h") or 0), x["nIn"], x["nOut"]) for x in ROWS if (x.get("h") or 0) != OY + (max(x["nIn"], x["nOut"]) - 1) * MU + LH + AIR][:4])
check("A13 corps sans minHeight ni padding", ROWS and all(x.get("minH") is None and x.get("pad") is None for x in ROWS),
      str({(x.get("minH"), x.get("pad")) for x in ROWS}))
cc = {x["props"].get("sourceCount"): x for x in ROWS if x["type"] == "Concatenate" and x["variant"] == "reef"}
check("A14 Concatenate tronqué : sourceCount 2/3/6/9 → 2/3/6/6 lignes et corps à leur mesure",
      [cc.get(k, {}).get("nIn") for k in (2, 3, 6, 9)] == [2, 3, 6, 6]
      and [cc.get(k, {}).get("h") for k in (2, 3, 6, 9)] == [OY + (n - 1) * MU + LH + AIR for n in (2, 3, 6, 6)],
      str([(k, v.get("nIn"), v.get("h")) for k, v in cc.items()]))
cat = next((x for x in ROWS if x["type"] == "Concatenate" and x["variant"] == "reef" and not x["props"]), {})
check("A15 Concatenate du catalogue (sourceCount absent) : 3 lignes, pas 6", cat.get("nIn") == 3, str(cat.get("nIn")))
spc = {x["props"].get("scenes"): x for x in ROWS if x["type"] == "SpatialCompose" and x["variant"] == "reef"}
sp_ports = OUT.get("spPorts", {})
check("A16 Composition spatiale : lignes = dzNodeInPorts (port brand de t226 compris), 2 et 5 scènes",
      all(spc.get(n, {}).get("ins") == sp_ports.get(str(n)) and "brand" in (sp_ports.get(str(n)) or []) for n in (2, 5)),
      str({n: (spc.get(n, {}).get("ins"), sp_ports.get(str(n))) for n in (2, 5)}))
check("A17 Composition spatiale : corps à la mesure des ports visibles (pas des 8 ports du catalogue)",
      all(spc.get(n, {}).get("h") == OY + (len(sp_ports.get(str(n)) or [0]) - 1) * MU + LH + AIR for n in (2, 5)),
      str({n: spc.get(n, {}).get("h") for n in (2, 5)}))

print("[B] encart et pied posés à « air » sous la dernière ligne, pour tous les types")
reef = [x for x in ROWS if x["variant"] == "reef"]
cl = [x for x in ROWS if x["variant"] == "abyssal"]
check("B1 reef : l'élément sous le corps est l'encart (hauteur zh)", reef and all(x["nextIsReef"] for x in reef))
check("B2 reef : encart sans marge haute (margin 0 10px)", reef and all(str(x["nextMargin"]) == "0 10px" for x in reef),
      str({x["nextMargin"] for x in reef}))
check("B3 reef : encart − bas de la dernière ligne = air, chaque type",
      reef and all(x.get("gap") == AIR for x in reef), [(x["type"], x.get("gap")) for x in reef if x.get("gap") != AIR][:6])
check("B4 classique : le pied suit le corps, sans encart", cl and all(not x["nextIsReef"] for x in cl))
check("B5 classique : pied − bas de la dernière ligne = air, chaque type",
      cl and all(x.get("gap") == AIR for x in cl), [(x["type"], x.get("gap")) for x in cl if x.get("gap") != AIR][:6])
check("B6 même mise en page partout : une seule valeur d'écart sur tous les nœuds",
      len({x.get("gap") for x in ROWS}) == 1 and None not in {x.get("gap") for x in ROWS}, str(sorted({x.get("gap") for x in ROWS})))
check("B7 1 port : encart à oy + lh + air = 34 sous l'en-tête (au lieu de 20, plus de chevauchement)",
      any(x["type"] == "NewsItem" and (x.get("h") or 0) == OY + LH + AIR == 34 for x in reef))

print("[C] qi et rendu alignés")
check("C1 qi = centre du rond rendu (x et y), chaque port visible, chaque type",
      ROWS and all(abs(p["q"]["y"] - p["cy"]) < 1e-9 and abs(p["q"]["x"] - p["cx"]) < 1e-9 for x in ROWS for p in x["qi"]),
      [(x["type"], p["id"], p["q"], p["cy"]) for x in ROWS for p in x["qi"]
       if abs(p["q"]["y"] - p["cy"]) >= 1e-9 or abs(p["q"]["x"] - p["cx"]) >= 1e-9][:4])
b, Ru = OUT.get("b"), OUT.get("Ru")
check("C2 tous les ronds dans le corps (qi.y + r/2 ≤ bordure + Ru + hauteur − air)",
      ROWS and all(p["q"]["y"] + 8 <= b + Ru + (x.get("h") or 0) - AIR + 1e-9 for x in ROWS for p in x["qi"]))
check("C3 1er rond : bordure + Ru + oy + r/2 = 53", any(p["q"]["y"] == 1 + 36 + OY + 8 == 53 for x in ROWS for p in x["qi"]))
check("C4 la géométrie des liens et des lignes vient de dzPortGeo (qi et ud lisent oy et lh)",
      "dzPortGeo.oy" in tranche(BUNDLE, "function qi(", "function Th(") and "dzPortGeo.lh" in tranche(BUNDLE, "function ud(", "var __dzG="))

print("[D] maillon de queue dzstudio, famille C*")
import patch_bundle_dzstudio as M                                    # noqa: E402
import _i18n_l1_aide as AIDE                                         # noqa: E402


# t280 : la couche sonvfx a été retouchée après ces bases (consignée L4 + G1, réinjectée par refresh_layer) — le bloc
# SONVFX attendu est celui du livré ; ce banc vérifie ses maillons HORS de ce bloc
def git_bundle(rev):
    b_ = _git_bundle_brut(rev)
    return None if b_ is None else __import__("_i18n_l1_aide").base_avec_sonvfx_livre(
        b_, (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes())


def _git_bundle_brut(rev):
    r = subprocess.run(["git", "show", f"{rev}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
    if r.returncode != 0:
        return None
    b_ = r.stdout                                   # blob normalisé LF (autocrlf) → les CRLF du fichier extrait
    return b_ if b"\r\n" in b_ else b_.replace(b"\n", b"\r\n")


PC = list(getattr(M, "PAIRES_C", []))
_nab = len(getattr(M, "PAIRES_AB", []))                             # les familles suivantes (F*…) viennent après
check("D1 famille C* déclarée (PAIRES_C), juste après A*+B* dans PAIRES", len(PC) >= 3 and _nab
      and M.PAIRES[_nab:_nab + len(PC)] == PC, str(len(PC)))
try:
    avant = M.defaire(AIDE.avant_dzmotion(BUNDLE))       # t235 : le maillon dzmotion, posé APRÈS, défait d'abord
except AssertionError as e:
    avant = None
    check("D2 toutes les paires sont dans le livré", False, str(e)[:160])
base_t226 = git_bundle("0b883708")
base_t224 = git_bundle("02f8162c")
check("D3 inverse = 02f8162c octet pour octet", avant is not None and base_t224 is not None
      and AIDE.avant_dzstudio(BUNDLE).encode("utf-8") == base_t224)


def sans_c(s):
    for a_, r_ in M.PAIRES[:_nab]:
        s = s.replace(a_, r_, 1)
    return s


check("D4 sans les C* = 0b883708 (t226) octet pour octet", avant is not None and base_t226 is not None and PC
      and sans_c(avant).encode("utf-8") == base_t226)
check("D5 aller-retour exact", avant is not None and M.appliquer(avant) == AIDE.avant_dzmotion(BUNDLE))
check("D6 comptes figés (useState 731, v2.8.0 ×4, DzTracks 181)",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
check("D7 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("D8 aucun .bak_dzstudio laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzstudio")).exists())
check("D9 aucun texte visible neuf dans les C* (pas de dzT, pas de useState)",
      PC and all(r_.count("dzT(") == a_.count("dzT(") and "useState" not in r_ for a_, r_ in PC))
check("D10 aperçu de composition (dzPvCell, bandeau en dur) non touché par les C*",
      PC and all("dzPv" not in a_ and "DEEPOTUS" not in a_ for a_, _r in PC) and base_t226 is not None
      and tranche(BUNDLE, "function dzPvCell(", "function ") == tranche(base_t226.decode("utf-8"), "function dzPvCell(", "function "))
try:
    _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
except (OSError, ValueError, KeyError):
    _g1 = []
check("D11 remplacements G1 intacts", bool(_g1) and avant is not None and all(BUNDLE.count(x) == avant.count(x) for x in _g1))
partiel = getattr(M, "partiel", None)
check("D12 garde « partiellement appliqué » : A*+B* sans les C* refusé, livré complet accepté",
      callable(partiel) and avant is not None and bool(PC) and partiel(sans_c(avant)) and not partiel(BUNDLE)
      and not partiel(avant))
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzstudio.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("D13 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
