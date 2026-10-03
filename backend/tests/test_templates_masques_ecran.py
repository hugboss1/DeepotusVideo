# -*- coding: utf-8 -*-
"""Plan-templates T3 (tache #74 du suivi, PR B, 03/10/2026) — les MASQUES dans l'editeur de gabarit, dans le bundle
LIVRE : la section « Masque », l'editeur de points et l'apercu sur la toile sont extraits et EXECUTES sous node.
DECISIONS DE L'UTILISATEUR (03/10) : arrondi, ellipse, polygone et fenetres ; cases video et image ; adoucissement +
liseré ; section dans l'inspecteur + apercu sur la toile ; fenetres et points en FRACTIONS de la case.
Temoin positif : le bundle de la base (f45b67db) n'a pas l'editeur de masque.
Run (depuis backend/) : & $PY tests/test_templates_masques_ecran.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzmske_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "f45b67db"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a l'inspecteur de region mais pas l'editeur de masque", r0.returncode == 0
      and b"onClick:dzDelReg" in r0.stdout and b"DzMaskEditor" not in r0.stdout)
k_del = BUN.find('r.jsx("div",{style:{marginTop:10},children:r.jsx("button",{onClick:dzDelReg')
k_ed = BUN.find('(c.type==="video_slot"||c.type==="image_slot")?r.jsx(DzMaskEditor,{rg:c,upd:function(pt){p(c.id,pt)}}):null,')
check("T2 la section est posee dans l'inspecteur, juste avant « Delete region », pour les cases video et image seulement ; la toile passe par l'apercu du masque",
      0 < k_ed < k_del and k_del - k_ed < 200 and BUN.count("r.jsx(DzMaskEditor,") == 1 and BUN.count("dzMasqueApercu(j,dzRegionFace(j))") == 1)   # #74 PR D : l'apercu du texte l'enveloppe (children:[dzTexteApercu(j,...))


def fonction(nom):
    k = BUN.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = BUN.find("){", k) + 1, 0, None, False
    while i < len(BUN):
        c_ = BUN[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return BUN[k - 6 if BUN[k - 6:k] == "async " else k:i + 1]
        i += 1
    return ""


m_var = re.search(r"var DZ_MASQUE_MODELES=\{.*?\]\]\};", BUN, re.S)
COUCHE = (m_var.group(0) if m_var else "") + "\n" + "\n".join(fonction(n) for n in ("dzMasqueSvg", "dzMasqueUrl", "dzMasqueApercu", "DzPointsEditeur", "DzMaskEditor"))
check("T3 la couche livree a les modeles et les cinq fonctions (une fois chacune)", m_var is not None and all(BUN.count("function " + n + "(") == 1
      for n in ("dzMasqueSvg", "dzMasqueUrl", "dzMasqueApercu", "DzPointsEditeur", "DzMaskEditor")))

HARNAIS = r"""
var H=[],hi=0,UPD=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};
var K="K",O="Champ",Ze="Case",re="Liste",Oe="Curseur",le="Saisie",DzColorPicker="Couleur";
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function ed(rg){hi=0;UPD=[];return DzMaskEditor({rg:rg,upd:function(pt){UPD.push(pt)}})}
function par(T,t,lab){return trouver(T,function(n){return n.t===t&&(lab===undefined||n.p.label===lab)})}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    try:
        p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    except subprocess.TimeoutExpired:
        print("   (node) suspendu plus de 60 s")
        return None
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


print("[S] le dessin SVG et l'apercu sur la toile")
R = node("""
R.rond=dzMasqueSvg({shape:"rounded",radius:500},300,200,false);
R.ell=dzMasqueSvg({shape:"ellipse",holes:[{shape:"ellipse",x:0.1,y:0.2,width:0.2,height:0.4}]},300,200,false);
R.poly=dzMasqueSvg({shape:"polygon",points:[[0.5,0],[1,1],[0,1]],holes:[{shape:"rect",x:0.5,y:0.5,width:0.25,height:0.25,radius:9}]},200,100,false);
R.trait=dzMasqueSvg({shape:"rounded",radius:10,border_px:6,border_color:"#00ff00",holes:[{x:0,y:0,width:0.5,height:0.5}]},100,100,true);
var face={t:"face"};R.sans=dzMasqueApercu({type:"video_slot",width:10,height:10},face)===face;R.badge=dzMasqueApercu({type:"badge",mask:{shape:"ellipse"}},face)===face;
var A=dzMasqueApercu({type:"image_slot",width:300,height:200,mask:{shape:"ellipse",border_px:3,border_color:"#ff0000"}},face);
R.ap={t:A.t,n:A.p.children.length,masque:A.p.children[0].p.style.maskImage.slice(0,40),face:A.p.children[0].p.children===face,lis:!!A.p.children[1],
  lisCls:A.p.children[1]&&A.p.children[1].p.className,taille:A.p.children[0].p.style.maskSize};
var B=dzMasqueApercu({type:"video_slot",width:300,height:200,mask:{shape:"rounded",radius:20}},face);R.sansLis=B.p.children[1];
""")
check("S0 sous node : le dessin s'execute", R is not None)
if R:
    check("S1 coins arrondis : rayon BORNE a la moitie du petit cote ; ellipse : centree ; polygone : points a l'echelle de la case",
          'rx="100"' in R["rond"] and 'width="300" height="200"' in R["rond"] and '<ellipse cx="150" cy="100" rx="150" ry="100" fill="white"/>' in R["ell"]
          and 'points="100,0 200,100 0,100"' in R["poly"], R["poly"])
    check("S2 les fenetres sont NOIRES (elles percent le masque), en fractions de la case, rayon borne", '<ellipse cx="60" cy="80" rx="30" ry="40" fill="black"/>' in R["ell"]
          and '<rect x="100" y="50" width="50" height="25" rx="9" fill="black"/>' in R["poly"], R["ell"])
    check("S3 le liseré : trace (sans remplissage) de la couleur et de l'epaisseur demandees, fenetres comprises",
          R["trait"].count('stroke="#00ff00" stroke-width="6"') == 2 and "fill=\"white\"" not in R["trait"] and 'fill="none"' in R["trait"], R["trait"])
    check("S4 la toile : sans masque (ou hors video/image) la case est dessinee TELLE QUELLE ; avec masque, son contenu est masque (SVG en masque CSS, etire a la case) et le liseré pose par-dessus ; sans epaisseur, pas de liseré",
          R["sans"] and R["badge"] and R["ap"]["t"] == "frag" and R["ap"]["face"] and R["ap"]["masque"].startswith('url("data:image/svg+xml,')
          and R["ap"]["taille"] == "100% 100%" and R["ap"]["lisCls"] == "dz-masque-lisere" and R["sansLis"] is None, str(R["ap"]))

print("\n[E] la section « Masque »")
R = node("""
var RG={id:"r1",type:"video_slot",width:300,height:200};
var T=ed(RG);R.off=[par(T,"Case")[0].p.label,par(T,"Liste").length];par(T,"Case")[0].p.onChange(true);R.on=UPD.slice();
T=ed(Object.assign({},RG,{mask:{shape:"rounded",radius:40,feather_px:4,border_px:0}}));par(T,"Case")[0].p.onChange(false);R.coupe=UPD.slice();
T=ed({id:"p",type:"image_slot",width:60,height:50});par(T,"Case")[0].p.onChange(true);R.petit=UPD.slice();
T=ed(Object.assign({},RG,{mask:{shape:"rounded",radius:40,feather_px:4}}));
R.curseurs=par(T,"Curseur").map(function(c){return [c.p.label,c.p.max]});R.couleur=par(T,"Couleur").length;
par(T,"Curseur","Rayon des coins")[0].p.onChange(55);par(T,"Curseur","Liseré")[0].p.onChange(5);R.majs=UPD.slice();
T=ed(Object.assign({},RG,{mask:{shape:"rounded",radius:40,border_px:3}}));R.couleur2=par(T,"Couleur").length;
var L=par(T,"Liste").find(function(l){return l.p.options&&l.p.options.length===3});R.formes=L.p.options.map(function(o){return o.value});
L.p.onChange("polygon");R.poly=UPD.slice();
T=ed(Object.assign({},RG,{mask:{shape:"polygon",points:[[0,0],[1,0],[1,1]]}}));R.ratio=trouver(T,function(n){return n.t===DzPointsEditeur})[0].p.ratio;R.poly3=par(T,"K").map(function(b){return [b.p.children,b.p.title]});
par(T,"K").find(function(b){return b.p.children==="Losange"}).p.onClick();R.modele=UPD.slice();
T=ed(Object.assign({},RG,{mask:{shape:"rounded",radius:10}}));par(T,"K").find(function(b){return b.p.children==="+ Fenêtre"}).p.onClick();R.ajout=UPD.slice();
T=ed(Object.assign({},RG,{mask:{shape:"rounded",radius:10,holes:[{shape:"rect",x:0.35,y:0.35,width:0.3,height:0.3}]}}));
var ligne=trouver(T,function(n){return n.p&&n.p.className==="dz-trou"})[0];var sx=trouver(ligne,function(n){return n.t==="Saisie"});
R.vals=sx.map(function(s){return s.p.value});sx[0].p.onChange("50");sx[2].p.onChange("abc");sx[3].p.onChange("150");
trouver(ligne,function(n){return n.t==="Liste"})[0].p.onChange("ellipse");var x_=trouver(ligne,function(n){return n.t==="button"})[0];R.xTitre=x_.p.title;x_.p.onClick();R.trous=UPD.slice();
var seize=[];for(var i=0;i<16;i++)seize.push({x:0,y:0,width:0.1,height:0.1});T=ed(Object.assign({},RG,{mask:{shape:"rounded",holes:seize}}));
R.plein=par(T,"K").filter(function(b){return b.p.children==="+ Fenêtre"}).length;
""")
check("E0 sous node : la section s'execute", R is not None)
if R:
    check("E1 sans masque : une case a cocher ; cochee -> un masque arrondi (rayon 40, borne a la case) ; decochee -> masque retire",
          R["off"] == ["Masque (forme de la case)", 0] and R["on"] == [{"mask": {"shape": "rounded", "radius": 40}}] and R["coupe"] == [{"mask": None}]
          and R["petit"] == [{"mask": {"shape": "rounded", "radius": 25}}], f"{R['on']} {R['coupe']} {R['petit']}")
    check("E2 curseurs : rayon (max = moitie du petit cote), bord adouci, liseré ; la COULEUR du liseré n'apparait que s'il a une epaisseur",
          R["curseurs"] == [["Rayon des coins", 100], ["Bord adouci", 100], ["Liseré", 40]] and R["couleur"] == 0 and R["couleur2"] == 1, str(R["curseurs"]))
    check("E3 chaque reglage envoie le masque COMPLET (les autres champs gardes)", R["majs"] == [{"mask": {"shape": "rounded", "radius": 55, "feather_px": 4}},
          {"mask": {"shape": "rounded", "radius": 40, "feather_px": 4, "border_px": 5}}], str(R["majs"]))
    check("E4 trois formes ; passer en polygone SANS points pose l'hexagone ; les modeles (avec title) remplacent les points",
          R["formes"] == ["rounded", "ellipse", "polygon"] and R["poly"][0]["mask"]["shape"] == "polygon" and len(R["poly"][0]["mask"]["points"]) == 6
          and [b[0] for b in R["poly3"]][:4] == ["Triangle", "Losange", "Hexagone", "Étoile"] and all("modèle" in b[1] for b in R["poly3"][:4])
          and R["modele"][0]["mask"]["points"] == [[0.5, 0], [1, 0.5], [0.5, 1], [0, 0.5]] and R["ratio"] == 1.5, str(R["poly"]) + str(R.get("ratio")))
    check("E5 « + Fenêtre » ajoute un rectangle de 30 % au centre ; les champs sont en % de la case (35 -> 0.35)",
          R["ajout"] == [{"mask": {"shape": "rounded", "radius": 10, "holes": [{"shape": "rect", "x": 0.35, "y": 0.35, "width": 0.3, "height": 0.3}]}}]
          and R["vals"] == ["35", "35", "30", "30"], f"{R['ajout']} {R['vals']}")
    t = [u["mask"]["holes"] for u in R["trous"]]
    check("E6 une saisie de % est bornee a 0..100 (illisible -> 0) ; la forme de la fenetre se change ; ✕ (avec title) la retire ; 16 fenetres au plus",
          t[0][0]["x"] == 0.5 and t[1][0]["width"] == 0 and t[2][0]["height"] == 1 and t[3][0]["shape"] == "ellipse" and t[4] == []
          and R["xTitre"] == "Retirer cette fenêtre" and R["plein"] == 0, str(t))

print("\n[P] l'editeur de points")
R = node("""
var PTS=[[0.5,0],[1,1],[0,1]],OUT=[];function pe(pts){hi=0;var S=DzPointsEditeur({pts:pts,ratio:2,onChange:function(q){OUT.push(q)}});
  H[0].current={getBoundingClientRect:function(){return {left:10,top:20,width:200,height:100}}};return S}
var S=pe(PTS);R.taille=[S.p.width,S.p.height];
S.p.onClick({target:H[0].current,clientX:110,clientY:70});R.ajout=OUT.slice();OUT=[];
var c=trouver(S,function(n){return n.t==="circle"});R.n=c.length;c[1].p.onPointerDown({stopPropagation:function(){}});S=pe(PTS);
S.p.onPointerMove({clientX:500,clientY:-50});R.glisse=OUT.slice();OUT=[];S.p.onPointerUp();S=pe(PTS);S.p.onPointerMove({clientX:60,clientY:60});R.apresLacher=OUT.length;
c=trouver(S,function(n){return n.t==="circle"});c[0].p.onDoubleClick({stopPropagation:function(){}});R.retire3=OUT.length;
var S4=pe([[0,0],[1,0],[1,1],[0,1]]);trouver(S4,function(n){return n.t==="circle"})[2].p.onDoubleClick({stopPropagation:function(){}});R.retire4=OUT.slice();OUT=[];
S.p.onClick({target:{autre:1},clientX:60,clientY:60});R.surPoint=OUT.length;
var plein=[];for(var i=0;i<64;i++)plein.push([0,0]);var S64=pe(plein);S64.p.onClick({target:H[0].current,clientX:60,clientY:60});R.max=OUT.length;
""")
check("P0 sous node : l'editeur de points s'execute", R is not None)
if R:
    check("P1 le cadre suit les proportions de la case (2:1 -> 200x100) ; un clic dans le cadre AJOUTE un point, en fraction",
          R["taille"] == [200, 100] and R["ajout"] == [[[0.5, 0], [1, 1], [0, 1], [0.5, 0.5]]] and R["n"] == 3, f"{R['taille']} {R['ajout']}")
    check("P2 glisser un point le deplace (borne au cadre) ; apres le lacher, plus rien ne bouge",
          R["glisse"] == [[[0.5, 0], [1, 0], [0, 1]]] and R["apresLacher"] == 0, str(R["glisse"]))
    check("P3 double-clic : retire un point (pas en dessous de 3) ; un clic sur un point n'en ajoute pas ; 64 points au plus",
          R["retire3"] == 0 and R["retire4"] == [[[0, 0], [1, 0], [0, 1]]] and R["surPoint"] == 0 and R["max"] == 0, f"{R['retire3']} {R['retire4']}")

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 178, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 178
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
