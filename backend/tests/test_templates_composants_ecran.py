# -*- coding: utf-8 -*-
"""Plan-templates T8 / D1 (tache #76 du suivi, PR F, 03/10/2026) — les COMPOSANTS dans l'editeur de gabarit, dans le
bundle LIVRE : la barre (« + Composant », « Enregistrer comme composant »), le dessin sur la toile et l'inspecteur
d'une instance sont extraits et EXECUTES sous node.
DECISIONS DE L'UTILISATEUR (03/10) : une instance ne change que ses TEXTES et COULEURS ; « Enregistrer comme
composant » par une LISTE A COCHER (l'editeur ne selectionne qu'une region), la selectionnee deja cochee, option de
remplacer les regions par une instance ; pas d'imbrication. Les types d'un composant sont ceux du serveur (parite).
Temoin positif : le bundle de la base (9d5f9761) n'a pas la barre des composants.
Run (depuis backend/) : & $PY tests/test_templates_composants_ecran.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzcpe_"))
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE                               # noqa: E402  (t142 : PRELUDE_DZT)

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "9d5f9761"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a l'editeur (rangee Add) mais pas la barre des composants", r0.returncode == 0
      and b'children:"+ "+z[1]},z[0])})' in r0.stdout and b"DzComposantBar" not in r0.stdout)
check("T2 la barre suit la rangee « Add: » (toile g x v, cases d / u, selection m / f) ; l'inspecteur suit la section Animation ; la toile dessine le composant AU CENTRE de la chaine d'apercus",
      BUN.count('children:z[2]?["+ "].concat(__dzGlT(z[2],z[1],z[3])):"+ "+z[1]},z[0])}),r.jsx(DzComposantBar,{W:g,H:v,regs:d,setRegs:u,select:m,sel:f})') == 1
      and BUN.count('r.jsx(DzAnimEditor,{rg:c,upd:function(pt){p(c.id,pt)}}),r.jsx(DzComposantEditor,{rg:c,upd:function(pt){p(c.id,pt)}}),') == 1
      and BUN.count("children:[dzAnimApercu(j,dzTexteApercu(j,dzMasqueApercu(j,dzComposantFace(j,dzRegionFace(j))))),") == 1)


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


VARS = [re.search(r"var " + v + r"=.*?;\s*(?=var |async function |function )", BUN, re.S) for v in ("DZ_CMP_TYPES", "__dzCmp")]
NOMS = ("dzCmpCharger", "dzCmpTrouve", "dzComposantFace", "DzComposantEditor", "DzComposantBar")
COUCHE = "\n".join(m.group(0) for m in VARS if m) + "\n" + "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a les deux tables et les cinq fonctions (une fois chacune)", all(VARS) and all(BUN.count("function " + n + "(") == 1 for n in NOMS))

HARNAIS = r"""
var H=[],hi=0,FETCH=[],REP={},EVT=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=typeof n==="function"?n(H[i]):n}]},
  useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]},useEffect:function(f){f()}};
function el(t,p,k){p=p||{};return {t:t,p:p,props:p,key:k}}var r={jsx:el,jsxs:el,Fragment:"frag"};
var K="K",O="Champ",Ze="Case",re="Liste",Oe="Curseur",le="Saisie",DzColorPicker="Couleur";
var window={addEventListener:function(n){EVT.push(n)},removeEventListener:function(){},dispatchEvent:function(){}};function CustomEvent(n){this.type=n}
async function fetch(u,o){FETCH.push([u,o&&o.method,o&&o.body&&JSON.parse(o.body)]);var q=REP[(o&&o.method||"GET")+" "+u]||{ok:!0,status:200,json:{}};await new Promise(function(s){setTimeout(s,3)});
  return {ok:q.ok,status:q.status,json:async function(){return q.json}}}
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function par(T,t,lab){return trouver(T,function(n){return n.t===t&&(lab===undefined||n.p.label===lab)})}
function texte(T){var s=[];trouver(T,function(n){if(typeof n.p.children==="string")s.push(n.p.children);return false});return s.join(" | ")}
var CMP={id:"cmp_b",name:"Bandeau",width:1000,height:200,builtin:true,regions:[{id:"fond",type:"separator",x:0,y:0,width:1000,height:200,color:"#02060d"},
  {id:"titre",type:"text",x:40,y:20,width:900,height:100,text:"Titre",size:60,color:"#ffffff"},{id:"bd",type:"badge",x:40,y:130,width:200,height:50,text:"LIVE",color:"#ffffff",background_color:"#ff0000"},
  {id:"st",type:"sticker",x:900,y:120,width:80,height:80}]};
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    # t142 (09/10) : les libelles passent par dzT (globale) ; le prelude la pose en FRANCAIS, APRES le harnais (qui pose
    # son propre `var window`, sinon le dictionnaire serait ecrase) — les attentes en francais restent vraies
    f.write_text(COUCHE + "\n" + HARNAIS + "\n" + AIDE.PRELUDE_DZT + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
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


print("[P] la parite avec le serveur")
from app.services import template_components as TC                 # noqa: E402
R = node("R.t=DZ_CMP_TYPES;")
check("P1 les types qu'on peut mettre dans un composant sont EXACTEMENT ceux du serveur", R is not None and tuple(R["t"]) == TC.SOUS_TYPES, str(R))

print("\n[C] le chargement et la toile")
R = node("""
REP["GET /api/template-components"]={ok:true,status:200,json:{components:[CMP]}};
var l=await dzCmpCharger();var l2=await dzCmpCharger();R.n=[l.length,FETCH.length];await dzCmpCharger(true);R.force=FETCH.length;
var face={t:"face"};R.autre=dzComposantFace({type:"text"},face)===face;
var I={type:"component",component:"cmp_b",overrides:{titre:{text:"LE POULPE"},bd:{background_color:"#00ff00"}}};
var F=dzComposantFace(I,face);var subs=F.p.children;R.n2=subs.length;R.titre=subs[1].p.children;R.fondTitre=subs[1].p.style.background;
R.bd=[subs[2].p.style.background,subs[2].p.children];R.sep=[subs[0].p.style.background,subs[0].p.children];R.pos=[subs[1].p.style.left,subs[1].p.style.top,subs[1].p.style.width];
R.stk=subs[3].p.style.border;R.absent=texte(dzComposantFace({type:"component",component:"cmp_x"},face));
""")
check("C0 sous node : le chargement et le dessin s'executent", R is not None)
if R:
    check("C1 la liste est chargee UNE fois (cache) ; « force » la recharge (apres un enregistrement)", R["n"] == [1, 1] and R["force"] == 2, str(R["n"]))
    check("C2 la toile dessine CHAQUE sous-region en % de la boite, avec les SURCHARGES (texte, fond) ; separateur plein ; sticker en pointilles ; ailleurs, la face d'origine",
          R["autre"] and R["n2"] == 4 and R["titre"] == "LE POULPE" and R["bd"] == ["#00ff00", "LIVE"] and R["sep"] == ["#02060d", None]
          and R["pos"] == ["4%", "10%", "90%"] and "dashed" in R["stk"] and R["fondTitre"] == "transparent", str(R))
    check("C3 un composant introuvable est dit sur la toile", "cmp_x" in R["absent"], R["absent"])

print("\n[E] l'inspecteur d'une instance")
R = node("""
__dzCmp.liste=[CMP];__dzCmp.charge=true;var UPD=[];
function ed(rg){hi=0;UPD=[];return DzComposantEditor({rg:rg,upd:function(pt){UPD.push(pt)}})}
R.texte=ed({type:"text"})===null;var I={id:"i1",type:"component",component:"cmp_b",overrides:{bd:{text:"ON AIR"}}};var T=ed(I);
R.sous=trouver(T,function(n){return n.p&&n.p.className==="dz-cmp-sous"}).map(function(b){return b.key});
var champs=par(T,"Saisie");R.valeurs=champs.map(function(s){return s.p.value});R.couleurs=par(T,"Couleur").length;
champs[0].p.onChange("NOUVEAU");par(T,"Couleur")[0].p.onChange("#123456");
var ret=par(T,"K");R.ret=ret.map(function(b){return [b.p.children,!!b.p.title]});ret[0].p.onClick();R.majs=UPD.slice();
T=ed({id:"i2",type:"component",component:"cmp_absent"});R.absent=texte(T);
""")
check("E0 sous node : l'inspecteur s'execute", R is not None)
if R:
    check("E1 rien hors instance ; une ligne par sous-region qui a un texte ou une couleur (pas le sticker) ; les valeurs montrees sont les SURCHARGES sinon celles du composant",
          R["texte"] and R["sous"] == ["fond", "titre", "bd"] and R["valeurs"] == ["Titre", "ON AIR"] and R["couleurs"] == 4, str(R))
    check("E2 changer un texte ou une couleur ecrit overrides[sous-region][champ] sans toucher le reste ; « ↺ Rétablir » (avec title) rend la sous-region au composant",
          R["majs"][0] == {"overrides": {"bd": {"text": "ON AIR"}, "titre": {"text": "NOUVEAU"}}} and R["majs"][1] == {"overrides": {"bd": {"text": "ON AIR"}, "fond": {"color": "#123456"}}}
          and R["ret"] == [["⟦dz-action-reinitialiser⟧ Rétablir", True]] and R["majs"][2] == {"overrides": {}}, str(R["majs"]))
    check("E3 un composant introuvable est signale dans l'inspecteur", "introuvable" in R["absent"], R["absent"])

print("\n[B] la barre : poser, enregistrer")
R = node("""
__dzCmp.liste=[CMP];__dzCmp.charge=true;var REGS=[{id:"a",type:"text",x:100,y:100,width:300,height:80,z_index:2,_disp:"x",text:"Salut"},{id:"b",type:"separator",x:100,y:200,width:500,height:10,z_index:3},
  {id:"c",type:"video_slot",x:0,y:0,width:1080,height:900,slot_name:"v",z_index:1}];
var ETAT=REGS.slice(),SEL=[];function setRegs(f){ETAT=f(ETAT)}
function bar(sel){hi=0;return DzComposantBar({W:1080,H:1920,regs:ETAT,setRegs:setRegs,select:function(i){SEL.push(i)},sel:sel})}
var T=bar("a");R.btn=trouver(T,function(n){return n.t==="button"}).map(function(b){return [b.p.children,!!b.p.title]});
trouver(T,function(n){return n.t==="button"&&n.p.children==="+ Composant"})[0].p.onClick();T=bar("a");
var it=trouver(T,function(n){return n.t==="button"&&String(n.p.children).indexOf("Bandeau")===0});R.item=[it.length,it[0].p.children];it[0].p.onClick();
var pose=ETAT[ETAT.length-1];R.pose=[pose.type,pose.component,pose.x,pose.y,pose.width,pose.height,pose.z_index,JSON.stringify(pose.overrides),SEL[0]===pose.id];
ETAT=REGS.slice();SEL=[];T=bar("a");trouver(T,function(n){return n.t==="button"&&String(n.p.children).indexOf("Enregistrer comme")>=0})[0].p.onClick();T=bar("a");
R.cases=par(T,"Case").map(function(c){return [c.p.label,c.p.checked]});
await par(T,"K").find(function(b){return b.p.children==="Enregistrer"}).p.onClick();T=bar("a");R.sansNom=texte(T).indexOf("Donnez un nom")>=0;
par(T,"Saisie")[0].p.onChange("Mon titre");T=bar("a");par(T,"Case","b · separator")[0].p.onChange(true);T=bar("a");
REP["POST /api/template-components"]={ok:true,status:200,json:{id:"cmp_mon_titre"}};REP["GET /api/template-components"]={ok:true,status:200,json:{components:[CMP]}};
FETCH=[];await par(T,"K").find(function(b){return b.p.children==="Enregistrer"}).p.onClick();
var post=FETCH.find(function(f){return f[1]==="POST"});R.post=post&&post[2];R.recharge=FETCH.filter(function(f){return f[1]===undefined}).length;
R.apres=ETAT.map(function(q){return q.type==="component"?[q.type,q.component,q.x,q.y,q.width,q.height,q.z_index]:q.id});R.sel=SEL;R.ferme=H[1]===null;
ETAT=REGS.slice();T=bar("a");trouver(T,function(n){return n.t==="button"&&String(n.p.children).indexOf("Enregistrer comme")>=0})[0].p.onClick();T=bar("a");
par(T,"Saisie")[0].p.onChange("Sans remplacer");T=bar("a");par(T,"Case","Remplacer ces régions par une instance du composant")[0].p.onChange(false);T=bar("a");
REP["POST /api/template-components"]={ok:true,status:200,json:{id:"cmp_sans"}};FETCH=[];await par(T,"K").find(function(b){return b.p.children==="Enregistrer"}).p.onClick();
R.sansRemp=[FETCH.filter(function(f){return f[1]==="POST"}).length,ETAT.map(function(q){return q.id})];
ETAT=REGS.slice();T=bar("a");trouver(T,function(n){return n.t==="button"&&String(n.p.children).indexOf("Enregistrer comme")>=0})[0].p.onClick();T=bar("a");
par(T,"Saisie")[0].p.onChange("X");T=bar("a");par(T,"Case","Remplacer ces régions par une instance du composant")[0].p.onChange(false);T=bar("a");
REP["POST /api/template-components"]={ok:false,status:400,json:{detail:"Composant : la région a est un video_slot"}};await par(T,"K").find(function(b){return b.p.children==="Enregistrer"}).p.onClick();
T=bar("a");R.refus=texte(T);R.intact=ETAT.length===3;
""")
check("B0 sous node : la barre s'execute", R is not None)
if R:
    check("B1 deux boutons (avec title) ; la liste montre les composants ; poser en met une instance AU CENTRE, a 70 % de haut, au premier plan, a l'echelle de la toile, et la selectionne",
          R["btn"][:2] == [["+ Composant", True], ["⧉ Enregistrer comme composant", True]] and R["item"] == [1, "Bandeau · livré"]
          and R["pose"] == ["component", "cmp_b", 54, 1344, 972, 194, 4, "{}", True], str(R["pose"]))
    check("B2 la fenetre liste les regions VISUELLES seulement (pas la case video), la SELECTIONNEE deja cochee, et « remplacer » coche par defaut ; sans nom : refuse",
          R["cases"] == [["a · text", True], ["b · separator", False], ["Remplacer ces régions par une instance du composant", True]] and R["sansNom"], str(R["cases"]))
    check("B3 enregistrer envoie la boite qui ENGLOBE les cochees et leurs regions RELATIVES (sans _disp) ; la liste est rechargee ; les regions sont REMPLACEES par une instance a leur place, selectionnee",
          R["post"] == {"name": "Mon titre", "width": 500, "height": 110, "regions": [{"id": "a", "type": "text", "x": 0, "y": 0, "width": 300, "height": 80, "z_index": 2, "text": "Salut"},
                                                                                       {"id": "b", "type": "separator", "x": 0, "y": 100, "width": 500, "height": 10, "z_index": 3}]}
          and R["recharge"] >= 1 and R["apres"] == ["c", ["component", "cmp_mon_titre", 100, 100, 500, 110, 3]] and len(R["sel"]) == 1 and R["ferme"], f"{R['post']} {R['apres']}")
    check("B4 sans « remplacer », le composant est ENREGISTRE et le gabarit garde ses regions ; un refus du serveur est AFFICHE dans la fenetre",
          R["sansRemp"] == [1, ["a", "b", "c"]] and "video_slot" in R["refus"] and R["intact"], f"{R['sansRemp']} {R['refus'][-200:]}")

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3, __dzLibPicker x11)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 181
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3 and BUN.count("__dzLibPicker") == 11)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
