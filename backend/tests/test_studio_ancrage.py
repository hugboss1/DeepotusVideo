# -*- coding: utf-8 -*-
"""Studio — chaque lien atterrit au MILIEU du rond du port, à l'entrée comme à la sortie (t225, 16/10/2026).

Défaut relevé sur 02f8162c (docs/superpowers/specs/2026-10-16-releve-menus-studio.md) : `qi` (la géométrie des liens)
plaçait le port à x = 0 / bi et y = Ru+12+i·Mu (48+22i) alors que le rond est rendu par `ud` à x+1 / x+bi−1 (bordure
du nœud) et y = 1 (bordure) + Ru + 10 (top de ligne) + 8 (demi-rond) = 55+22i ; un libellé long passait sur deux
lignes (ligne `alignItems:center`, `width:130`) et le rond descendait encore de 7 (−14 sur Composition spatiale).

Ce que ce banc garde :
  [A] une seule géométrie `dzPortGeo` (bordure b, origine oy, pas p = Mu, hauteur de ligne lh, rond r) lue À LA FOIS par
      `qi` et par `ud` ; plus aucun `Ru+12+a*Mu` ni `8+n*Mu+2` en dur ;
  [B] sous node : `qi` (extrait avec `dzPortGeo`) rend, pour i = 0..5, le CENTRE du rond tel que `ud` le dessine
      (bordure du nœud + Ru + top de la ligne + demi-rond ; x = bordure + left + demi-rond) : in.x = 1,
      out.x = bi − 1 ;
  [C] la ligne de port : rond ancré en haut de ligne (`alignItems:"flex-start"`, hauteur de ligne fixe = lh), étiquette
      sur UNE ligne (nowrap, overflow hidden, ellipsis, minWidth 0) avec `title` = libellé complet → la hauteur ne
      dépend plus de la longueur du libellé ni de la langue ;
  [D] maillon de queue `dzstudio` : sonde amont (dzlogo…), octets, inverse exact, `avant_dzstudio` en tête
      d'`avant_dzlogo`, comptes figés (useState 731, v2.8.0 ×4, DzTracks 181), remplacements G1 intacts, aucun .bak.
Run (depuis backend/) : & $PY tests/test_studio_ancrage.py"""
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


def eq(a, b):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) < 1e-9


def tranche(s, a, b):
    i = s.find(a)
    if i < 0:
        return ""
    j = s.find(b, i)
    return s[i:j] if j > 0 else ""


QI = tranche(BUNDLE, "function qi(", "function Th(")
UD = tranche(BUNDLE, "function ud(", "var __dzG=")
TH = tranche(BUNDLE, "function Th(", "var __dzTplList=")

print("[A] une seule géométrie des ports")
check("A1 dzPortGeo défini une fois", BUNDLE.count("var dzPortGeo={") == 1)
m = re.search(r"var dzPortGeo=\{([^}]*)\};", BUNDLE)
GEO = dict(kv.split(":", 1) for kv in m.group(1).split(",")) if m else {}
check("A2 dzPortGeo : bordure 1, pas = Mu, rond 16, ligne 16, origine numérique",
      GEO.get("b") == "1" and GEO.get("p") == "Mu" and GEO.get("r") == "16" and GEO.get("lh") == "16"
      and GEO.get("oy", "").isdigit(), str(GEO))
check("A3 qi lit dzPortGeo (bordure, origine, pas, rond)",
      all(k in QI for k in ("dzPortGeo.b", "dzPortGeo.oy", "dzPortGeo.p", "dzPortGeo.r")), QI[:200])
check("A4 ud lit dzPortGeo (origine, pas, ligne, rond)",
      all(k in UD for k in ("dzPortGeo.oy", "dzPortGeo.p", "dzPortGeo.lh", "dzPortGeo.r")), UD[:200])
check("A5 plus de géométrie en dur (Ru+12+a*Mu, 8+n*Mu+2)",
      "Ru+12+a*Mu" not in BUNDLE and "8+n*Mu+2" not in BUNDLE)
check("A6 dzPortGeo posé devant qi, après les constantes", "Eh=30;var dzPortGeo={" in BUNDLE
      and BUNDLE.find("var dzPortGeo={") < BUNDLE.find("function qi("))

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
try{
 const K=/bi=(\d+),Ru=(\d+),Mu=(\d+)/.exec(S);const bi=+K[1],Ru=+K[2],Mu=+K[3];
 const i0=S.indexOf("var dzPortGeo=");const SRC=(i0>=0?tranche("var dzPortGeo=","function Th("):tranche("function qi(","function Th("))
  +";"+tranche("function ud(","var __dzG=");
 const P=n=>Array.from({length:n},(_,i)=>({id:"p"+i,type:"av",label:"Port "+i}));
 const Me={T:{inPorts:P(6),outPorts:P(6)}};
 const r={jsx(t,p){return{t,p}},jsxs(t,p){return{t,p}}};
 const Ur={av:{color:"#9aa6b4"}};
 const ENV={Me,r,Ur,bi,Ru,Mu};
 const M=new Function("ENV","with(ENV){"+SRC+";return{qi,ud}}")(ENV);
 const BORD=/border:`(\d+)px solid \$\{y\}`/.exec(S);const b=BORD?+BORD[1]:NaN;
 const L=[];
 for(let i=0;i<6;i++)for(const side of ["in","out"]){
  const q=M.qi("T",side,"p"+i,null);
  const row=M.ud({side,port:{id:"p"+i,type:"av",label:"Une étiquette vraiment très longue pour deux lignes"},index:i,onPress(){},onRelease(){}});
  const rs=row.p.style,dot=row.p.children[0].p.style,lab=row.p.children[1].p;
  const lh=typeof rs.height==="number"?rs.height:null;
  const cy=b+Ru+rs.top+(rs.alignItems==="flex-start"?dot.height/2:(lh!=null?lh/2:NaN));
  const off=side==="in"?rs.left:rs.right;
  const cx=side==="in"?b+off+dot.width/2:bi-b-off-dot.width/2;
  L.push({i,side,qx:q.x,qy:q.y,cx,cy,align:rs.alignItems,h:lh,dw:dot.width,dh:dot.height,
   lab:{ws:lab.style.whiteSpace,ov:lab.style.overflow,to:lab.style.textOverflow,mw:lab.style.minWidth,lh:lab.style.lineHeight,title:lab.title}});
 }
 OUT.L=L;OUT.b=b;OUT.bi=bi;OUT.Ru=Ru;OUT.Mu=Mu;
 OUT.absent=M.qi("T","in","zz",null);
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));
"""

print("[B] qi = centre du rond rendu par ud (sous node)")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzstudio_node_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(RAW)
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js")], capture_output=True, text=True, encoding="utf-8",
                    errors="replace")
try:
    OUT = json.loads(rn.stdout or "{}")
except ValueError:
    OUT = {"err": rn.stdout[-300:] + rn.stderr[-300:]}
check("B0 qi et ud extraits et exécutés", "err" not in OUT, str(OUT.get("err", ""))[:300])
L = OUT.get("L", [])
bi, Ru, Mu = OUT.get("bi"), OUT.get("Ru"), OUT.get("Mu")
check("B1 bordure du nœud lue dans Th = 1", OUT.get("b") == 1, str(OUT.get("b")))
check("B2 six ports par côté mesurés", len(L) == 12, str(len(L)))
check("B3 entrée : qi.x = 1 (bordure comptée)", L and all(p["qx"] == 1 for p in L if p["side"] == "in"),
      [p["qx"] for p in L if p["side"] == "in"])
check("B4 sortie : qi.x = bi − 1", L and all(p["qx"] == bi - 1 for p in L if p["side"] == "out"),
      [p["qx"] for p in L if p["side"] == "out"])
check("B5 qi.x = centre x du rond rendu (in et out)", L and all(eq(p["qx"], p["cx"]) for p in L),
      [(p["side"], p["qx"], p["cx"]) for p in L][:4])
check("B6 qi.y = centre y du rond rendu, i = 0..5", L and all(eq(p["qy"], p["cy"]) for p in L),
      [(p["i"], p["qy"], p["cy"]) for p in L if p["side"] == "in"])
check("B7 pas entre deux ports = Mu", L and all(eq(L[k + 2]["qy"] - L[k]["qy"], Mu) for k in range(len(L) - 2)))
OY = int(GEO.get("oy", "0") or 0)
check("B8 1er rond à bordure + Ru + oy + 8 : 55 au relevé (oy 10), 53 depuis t227 (oy 8, maquette validée)",
      L and OY == 8 and L[0]["qy"] == 1 + Ru + OY + 8 == 53, str(L[0]["qy"] if L else None))
check("B9 port introuvable (t226) : bord du nœud, ligne sous le dernier port, jamais (0,0)",
      OUT.get("absent") == {"x": 1, "y": 1 + Ru + OY + 6 * Mu + 8} if Ru is not None else False, str(OUT.get("absent")))

print("[C] ligne de port : rond en haut, étiquette sur une ligne")
check("C1 rond ancré en haut de ligne (alignItems flex-start)", L and all(p.get("align") == "flex-start" for p in L),
      str({p.get("align") for p in L}))
check("C2 hauteur de ligne fixe = lh = rond", L and all(p.get("h") == 16 and p.get("dw") == 16 and p.get("dh") == 16 for p in L),
      str({(p.get("h"), p.get("dw"), p.get("dh")) for p in L}))
lab = [p["lab"] for p in L]
check("C3 étiquette sur une ligne : nowrap, overflow hidden, ellipsis, minWidth 0",
      lab and all(x.get("ws") == "nowrap" and x.get("ov") == "hidden" and x.get("to") == "ellipsis" and x.get("mw") == 0 for x in lab),
      str(lab[:1]))
check("C4 interligne de l'étiquette = lh (16 px)", lab and all(x.get("lh") == "16px" for x in lab), str({x.get("lh") for x in lab}))
check("C5 title = libellé complet · type",
      lab and all(x.get("title") == "Une étiquette vraiment très longue pour deux lignes · av" for x in lab), str(lab[:1]))
check("C6 l'étiquette visible reste « libellé · type » (couleur du type)",
      'children:[t.label||t.id,r.jsxs("span",{style:{color:s,opacity:.6},children:[" · ",t.type]})]' in UD)
check("C7 les données des ports (data-port-side/id) et les gestes restent sur le rond",
      '"data-port-side":e,"data-port-id":t.id,onMouseDown:a=>{a.stopPropagation(),o(a)},onMouseUp:a=>{a.stopPropagation(),i(a)}' in UD)
check("C8 corps des ports à hauteur explicite et encart sans marge haute (t227, banc test_studio_entetes)",
      'r.jsxs("div",{style:{position:"relative",height:dzPortBodyH(dzVisInPorts(e,u).length,u.outPorts.length)},children:[' in TH
      and 'm&&r.jsx("div",{style:{height:zh,margin:"0 10px",' in TH and 'minHeight:16,padding:"8px 0"' not in TH)

print("[D] maillon de queue dzstudio")
try:
    import patch_bundle_dzstudio as M                                # noqa: E402
except ImportError as e:
    M = None
    check("D0 scripts/patch_bundle_dzstudio.py existe", False, str(e))
if M:
    import _i18n_l1_aide as AIDE                                     # noqa: E402
    try:
        avant = M.defaire(AIDE.avant_dzmotion(BUNDLE))       # t235 : le maillon dzmotion, posé APRÈS, défait d'abord
    except AssertionError as e:                                      # une paire absente du livré
        check("D0 les paires du maillon sont toutes dans le livré", False, str(e)[:160])
        print(f"\n{ok} passed, {fail} failed")
        sys.exit(1)
    check("D1 marqueur ×1 dans le livré, absent avant", BUNDLE.count(M.MARKER) == 1 and M.MARKER not in avant)
    check("D2 aller-retour exact", M.appliquer(avant) == AIDE.avant_dzmotion(BUNDLE))
    check("D3 l'avant = la géométrie d'origine (Ru+12+a*Mu, 8+n*Mu+2, alignItems center)",
          "d=Ru+12+a*Mu" in avant and "top:8+n*Mu+2" in avant and "dzPortGeo" not in avant)
    check("D4 sonde amont : dzlogo et version", any(t == "dzlogo" for t, _j, _n in M.SONDE_AMONT)
          and any(t == "version" for t, _j, _n in M.SONDE_AMONT))
    check("D5 la sonde amont tient sur l'avant", all(avant.count(j) == n for _t, j, n in M.SONDE_AMONT))
    check("D6 comptes figés intacts (useState 731, v2.8.0 ×4, DzTracks 181)",
          BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
    check("D7 avant_dzstudio = défaire", AIDE.avant_dzstudio(BUNDLE) == avant)
    check("D8 avant_dzstudio sans marqueur : rendu tel quel", AIDE.avant_dzstudio(avant) == avant)
    src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
    j = src_aide.find("def avant_dzlogo(")
    check("D9 avant_dzstudio appelé EN TÊTE d'avant_dzlogo",
          j > 0 and "bundle = avant_dzstudio(bundle)" in src_aide[j:src_aide.find("import patch_bundle_dzlogo", j)])
    check("D10 avant_dzlogo(livré) == avant_dzlogo(avant)", AIDE.avant_dzlogo(BUNDLE) == AIDE.avant_dzlogo(avant))
    try:
        _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
    except (OSError, ValueError, KeyError):
        _g1 = []
    check("D11 aucun remplacement G1 du maillon dzglyph ne bouge", bool(_g1) and all(BUNDLE.count(x) == avant.count(x) for x in _g1),
          [x[:60] for x in _g1 if BUNDLE.count(x) != avant.count(x)][:3])
    check("D12 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
    check("D13 aucun .bak_dzstudio laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzstudio")).exists())
    src_m = (RACINE / "scripts" / "patch_bundle_dzstudio.py").read_text(encoding="utf-8")
    check("D14 le maillon lit et écrit en octets", "read_bytes" in src_m and "write_bytes" in src_m and "read_text" not in src_m)
    def _uniques(s):                                                 # t227 : C1 réécrit la sortie de A0 → ancre
        for a_, r_ in M.PAIRES:                                      # unique AU MOMENT où la paire s'applique
            if s.count(a_) != 1:
                return False
            s = s.replace(a_, r_, 1)
        return True
    check("D15 chaque paire a une ancre unique au moment où elle s'applique", _uniques(avant))
    rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzstudio.py"), "--check"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    check("D16 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
