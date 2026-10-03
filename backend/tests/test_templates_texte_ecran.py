# -*- coding: utf-8 -*-
"""Plan-templates T4 (tache #74 du suivi, PR D, 03/10/2026) — le TEXTE ADAPTATIF et ses EFFETS dans l'editeur de
gabarit, dans le bundle LIVRE : la section « Texte » et l'apercu sur la toile sont extraits et EXECUTES sous node.
DECISIONS DE L'UTILISATEUR (03/10) : toile en CSS + bouton « Aperçu exact » (une image rendue par le vrai moteur,
locale et gratuite) ; styles prets a l'emploi (Sous-titre reseau, Neon, Bandeau, Titre degrade, Aucun effet).
Temoin positif : le bundle de la base (79bdd3e0) n'a pas l'editeur de texte.
Run (depuis backend/) : & $PY tests/test_templates_texte_ecran.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dztxe_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "79bdd3e0"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a l'editeur de masque mais pas celui du texte", r0.returncode == 0
      and b"DzMaskEditor" in r0.stdout and b"DzTexteEditor" not in r0.stdout)
k_msk = BUN.find('(c.type==="video_slot"||c.type==="image_slot")?r.jsx(DzMaskEditor,{rg:c,upd:function(pt){p(c.id,pt)}}):null,')
k_txt = BUN.find('r.jsx(DzTexteEditor,{rg:c,upd:function(pt){p(c.id,pt)}}),r.jsx("div",{style:{marginTop:10},children:r.jsx("button",{onClick:dzDelReg')
check("T2 la section est posee dans l'inspecteur, apres le masque et juste avant « Delete region » ; la toile passe par l'apercu du texte AUTOUR de celui du masque",
      0 < k_msk < k_txt and k_txt - k_msk < 200 and BUN.count("r.jsx(DzTexteEditor,") == 1
      and BUN.count("children:[dzTexteApercu(j,dzMasqueApercu(j,dzRegionFace(j))),") == 1)


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


VARS = [re.search(r"var " + v + r"=.*?;\s*(?=var |function )", BUN, re.S) for v in ("DZ_TEXTE_TYPES", "DZ_TEXTE_DEFAUTS", "DZ_TEXTE_STYLES")]
NOMS = ("dzRgba", "dzTexteApercu", "DzTexteEditor")
COUCHE = "\n".join(m.group(0) for m in VARS if m) + "\n" + "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a les trois tables et les trois fonctions (une fois chacune)", all(VARS) and all(BUN.count("function " + n + "(") == 1 for n in NOMS))

HARNAIS = r"""
var H=[],hi=0,UPD=[],FETCH=[],REP=null,URLS=[],REVOK=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]},
  cloneElement:function(e,pr,c){var np=Object.assign({},e.props,pr,{children:c});return {t:e.t,p:np,props:np}}};
function el(t,p){p=p||{};return {t:t,p:p,props:p}}var r={jsx:el,jsxs:el,Fragment:"frag"};
var K="K",O="Champ",Ze="Case",re="Liste",Oe="Curseur",le="Saisie",DzColorPicker="Couleur";
var URL={createObjectURL:function(b){URLS.push(b);return "blob:"+URLS.length},revokeObjectURL:function(u){REVOK.push(u)}};
async function fetch(u,o){FETCH.push([u,o&&o.method,o&&o.body&&JSON.parse(o.body)]);var q=REP;await new Promise(function(s){setTimeout(s,5)});
  return {ok:q.ok,status:q.status,json:async function(){return q.json||{}},blob:async function(){return "PNG"}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function ed(rg){hi=0;UPD=[];return DzTexteEditor({rg:rg,upd:function(pt){UPD.push(pt)}})}
function par(T,t,lab){return trouver(T,function(n){return n.t===t&&(lab===undefined||n.p.label===lab)})}
function bouton(T,txt){return par(T,"K").find(function(b){return b.p.children===txt})}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
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


print("[E] la section « Texte »")
R = node("""
R.video=ed({id:"v",type:"video_slot"});R.shape=ed({id:"s",type:"shape"});
var RG={id:"t1",type:"text",text:"Bonjour",size:48};var T=ed(RG);
R.styles=par(T,"K").filter(function(b){return b.p.title&&b.p.title.length>8}).map(function(b){return b.p.children}).slice(0,5);
R.titres=par(T,"K").every(function(b){return typeof b.p.title==="string"&&b.p.title.length>8});
R.cases=par(T,"Case").map(function(c){return c.p.label});R.curseurs0=par(T,"Curseur").length;
bouton(T,"Sous-titre réseau").p.onClick();bouton(T,"Néon").p.onClick();bouton(T,"Aucun effet").p.onClick();R.styleMaj=UPD.slice();
T=ed(RG);bouton(T,"Sous-titre réseau").p.onClick();UPD[0].text_effects.stroke.px=99;T=ed(RG);bouton(T,"Sous-titre réseau").p.onClick();R.copie=UPD[0].text_effects.stroke.px;
T=ed({id:"k",type:"ticker",text:"DEFILE",size:40});R.tk=par(T,"Case").map(function(c){return c.p.label});R.tkNote=texte(T).indexOf("Le ticker défile")>=0;
bouton(T,"Sous-titre réseau").p.onClick();R.tkStyle=UPD.slice();
T=ed(RG);par(T,"Case","Ajuster à la case (couper en lignes, puis réduire)")[0].p.onChange(true);R.fit=UPD.slice();
T=ed(Object.assign({},RG,{text_fit:true}));var m=par(T,"Curseur","Taille minimale")[0];R.mini=[m.p.value,m.p.min,m.p.max];m.p.onChange(20);R.miniMaj=UPD.slice();
T=ed(Object.assign({},RG,{text_fit:true,size:9}));R.miniPetit=par(T,"Curseur","Taille minimale")[0].p.max;
T=ed(RG);par(T,"Case","Contour")[0].p.onChange(true);par(T,"Case","Fond")[0].p.onChange(true);R.on=UPD.slice();
var FX={stroke:{px:6,color:"#000000"},shadow:{dx:3,dy:4,blur:0,color:"#000000",opacity:0.6}};
T=ed(Object.assign({},RG,{text_effects:FX}));R.curseurs=par(T,"Curseur").map(function(c){return [c.p.label,c.p.min,c.p.max]});R.teintes=par(T,"Couleur").length;
par(T,"Curseur","Flou (0 = ombre nette)")[0].p.onChange(12);par(T,"Case","Contour")[0].p.onChange(false);R.majs=UPD.slice();
T=ed(Object.assign({},RG,{text_effects:{stroke:{px:2}}}));par(T,"Case","Contour")[0].p.onChange(false);R.vide=UPD.slice();
T=ed(Object.assign({},RG,{text_effects:{gradient:{c0:"#ffffff",c1:"#00e5ff",direction:"vertical"}}}));
var L=par(T,"Liste")[0];R.sens=L.p.options.map(function(o){return o.value});L.p.onChange("horizontal");R.sensMaj=UPD.slice();
""")
check("E0 sous node : la section s'execute", R is not None)
if R:
    check("E1 rien pour une case video ou une forme ; pour un texte : cinq styles prets (avec title), quatre effets a cocher, l'ajustement ; aucun curseur tant que rien n'est coche",
          R["video"] is None and R["shape"] is None and R["styles"] == ["Aucun effet", "Sous-titre réseau", "Néon", "Bandeau", "Titre dégradé"] and R["titres"]
          and R["cases"] == ["Ajuster à la case (couper en lignes, puis réduire)", "Contour", "Ombre", "Fond", "Dégradé"] and R["curseurs0"] == 0, str(R["cases"]))
    s = R["styleMaj"]
    check("E2 un style remplace TOUS les effets d'un coup (copie, pas la table partagee) ; « Sous-titre réseau » ajuste aussi ; « Aucun effet » les retire",
          s[0] == {"text_effects": {"stroke": {"px": 6, "color": "#000000"}, "shadow": {"dx": 0, "dy": 4, "blur": 0, "color": "#000000", "opacity": 0.6}}, "text_fit": True}
          and s[1] == {"text_effects": {"stroke": {"px": 2, "color": "#00e5ff"}, "shadow": {"dx": 0, "dy": 0, "blur": 18, "color": "#00e5ff", "opacity": 0.9}}}
          and s[2] == {"text_effects": None} and R["copie"] == 6, f"{s} copie={R['copie']}")
    check("E3 le ticker : pas d'ajustement (il defile, c'est dit) ; ses styles n'ajoutent pas text_fit",
          "Ajuster à la case (couper en lignes, puis réduire)" not in R["tk"] and R["tkNote"] and "text_fit" not in R["tkStyle"][0] and R["tkStyle"][0]["text_effects"]["stroke"]["px"] == 6,
          str(R["tk"]) + str(R["tkStyle"]))
    check("E4 ajuster : la case pose text_fit ; la taille minimale n'apparait qu'ajuste (12 par defaut, 6 au plus bas, la taille du texte au plus haut)",
          R["fit"] == [{"text_fit": True}] and R["mini"] == [12, 6, 48] and R["miniMaj"] == [{"text_min_size": 20}] and R["miniPetit"] == 9, f"{R['mini']} {R['miniPetit']}")
    check("E5 cocher un effet pose SES valeurs par defaut, sans perdre les autres reglages",
          R["on"] == [{"text_effects": {"stroke": {"px": 4, "color": "#000000"}}}, {"text_effects": {"box": {"color": "#000000", "opacity": 0.6, "radius": 0, "pad": 12}}}], str(R["on"]))
    check("E6 curseurs du contour et de l'ombre (bornes de la validation serveur) ; regler le flou garde le reste ; decocher retire l'effet ; plus aucun effet -> null",
          R["curseurs"] == [["Épaisseur du contour", 0, 40], ["Décalage horizontal", -50, 50], ["Décalage vertical", -50, 50], ["Flou (0 = ombre nette)", 0, 60], ["Opacité", 0, 1]]
          and R["teintes"] == 2 and R["majs"] == [{"text_effects": {"stroke": {"px": 6, "color": "#000000"}, "shadow": {"dx": 3, "dy": 4, "blur": 12, "color": "#000000", "opacity": 0.6}}},
                                                   {"text_effects": {"shadow": {"dx": 3, "dy": 4, "blur": 0, "color": "#000000", "opacity": 0.6}}}]
          and R["vide"] == [{"text_effects": None}], str(R["majs"]))
    check("E7 le degrade : deux sens, le sens change seul", R["sens"] == ["vertical", "horizontal"]
          and R["sensMaj"] == [{"text_effects": {"gradient": {"c0": "#ffffff", "c1": "#00e5ff", "direction": "horizontal"}}}], str(R["sensMaj"]))

print("\n[X] l'apercu exact")
R = node("""
var RG={id:"t1",type:"badge",text:"LIVE",size:34,text_effects:{box:{radius:8}}};
REP={ok:true,status:200};var T=ed(RG);var b=bouton(T,"Aperçu exact");R.titre=b.p.title;
var p1=b.p.onClick(),p2=b.p.onClick();await p1;await p2;R.fetch=FETCH.slice();
T=ed(RG);var img=trouver(T,function(n){return n.t==="img"})[0];R.img=img&&img.p.src;R.note=texte(T);
T=ed(Object.assign({},RG,{text:"AUTRE"}));R.perime=texte(T);
REP={ok:true,status:200};await bouton(T,"Aperçu exact").p.onClick();R.revok=REVOK.slice();
REP={ok:false,status:400,json:{detail:"Region t1 : text_effects.stroke.px doit être entre 0 et 40."}};await bouton(T,"Aperçu exact").p.onClick();
T=ed(RG);R.erreur=texte(T);
""")
check("X0 sous node : l'apercu s'execute", R is not None)
if R:
    check("X1 le bouton (avec title « gratuit ») demande UNE image au serveur pour CETTE case ; un double clic n'envoie qu'UNE requete",
          "gratuit" in R["titre"] and len(R["fetch"]) == 1 and R["fetch"][0][:2] == ["/api/layout-templates/apercu-texte", "POST"]
          and R["fetch"][0][2] == {"region": {"id": "t1", "type": "badge", "text": "LIVE", "size": 34, "text_effects": {"box": {"radius": 8}}}}, str(R["fetch"]))
    check("X2 l'image recue s'affiche, dite « rendu réel » ; un reglage change ensuite -> l'apercu est dit PERIME",
          R["img"] == "blob:1" and "Rendu réel de la case" in R["note"] and "Réglages changés depuis cet aperçu" in R["perime"], R["perime"][-200:])
    check("X3 un nouvel apercu libere l'ancienne image ; un refus du serveur est AFFICHE tel quel", R["revok"] == ["blob:1"]
          and "stroke.px doit être entre 0 et 40" in R["erreur"], R["erreur"][-200:])

print("\n[C] la toile")
R = node("""
var face=el("div",{style:{color:"#e2e8f0",fontSize:"10cqw"},children:"Titre"});
R.sans=dzTexteApercu({type:"text"},face)===face;R.video=dzTexteApercu({type:"video_slot",text_effects:{stroke:{px:4}}},face)===face;
var A=dzTexteApercu({type:"text",text_effects:{stroke:{px:8,color:"#00ff00"},shadow:{dx:4,dy:-8,blur:12,color:"#ff0000",opacity:0.5}}},face);
R.a={stroke:A.p.style.WebkitTextStroke,ombre:A.p.style.textShadow,taille:A.p.style.fontSize,cls:A.p.className,enfant:A.p.children,orig:face.p.style.WebkitTextStroke===undefined};
var B=dzTexteApercu({type:"badge",text_effects:{box:{color:"#0000ff",opacity:1,radius:20,pad:8},gradient:{c0:"#ffff00",c1:"#ff0000",direction:"horizontal"}}},face);
var fond=B.p.children,deg=fond.p.children;R.b={fondCls:fond.p.className,fond:fond.p.style.background,rayon:fond.p.style.borderRadius,degCls:deg.p.className,img:deg.p.style.backgroundImage,
  clip:deg.p.style.WebkitBackgroundClip,coul:deg.p.style.color,texte:deg.p.children};
var C=dzTexteApercu({type:"ticker",text_effects:{gradient:{}}},el("div",{style:{},children:"X"}));R.c=C.p.children.p.style.backgroundImage;
var D=dzTexteApercu({type:"badge",text_effects:{box:{}}},el("div",{style:{},children:[el("span")]}));R.d=Array.isArray(D.p.children);
""")
check("C0 sous node : l'apercu de la toile s'execute", R is not None)
if R:
    check("C1 sans effet (ou hors texte) la case est dessinee TELLE QUELLE ; contour et ombre en CSS, a l'echelle de la toile (x0,25), la face d'origine intacte",
          R["sans"] and R["video"] and R["a"]["stroke"] == "2px #00ff00" and R["a"]["ombre"] == "1px -2px 3px rgba(255,0,0,0.5)"
          and R["a"]["taille"] == "10cqw" and R["a"]["cls"] == "dz-texte-apercu" and R["a"]["enfant"] == "Titre" and R["a"]["orig"], str(R["a"]))
    check("C2 fond (couleur, opacite, coins) AUTOUR du texte en degrade (texte detoure, sens horizontal) ; degrade vide -> couleurs par defaut ; une face composee n'est pas cassee",
          R["b"] == {"fondCls": "dz-texte-fond", "fond": "rgba(0,0,255,1)", "rayon": 5, "degCls": "dz-texte-degrade", "img": "linear-gradient(90deg,#ffff00,#ff0000)",
                     "clip": "text", "coul": "transparent", "texte": "Titre"} and R["c"] == "linear-gradient(180deg,#ffffff,#00e5ff)" and R["d"], str(R["b"]))

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 178, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 178
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
