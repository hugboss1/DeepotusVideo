# -*- coding: utf-8 -*-
"""Plan-templates T9 / D2 (tache #76 du suivi, PR B, 03/10/2026) — les ANIMATIONS dans l'editeur de gabarit, dans le
bundle LIVRE : la section « Animation » et l'apercu rejoue sur la toile sont extraits et EXECUTES sous node.
DECISIONS DE L'UTILISATEUR (03/10) : fondu, glissement, pop + courbes ; toutes les regions visibles. Les types et les
courbes de l'ecran sont ceux que le serveur accepte (parite verifiee contre template_anim).
Temoin positif : le bundle de la base (da3255b1) n'a pas l'editeur d'animation.
Run (depuis backend/) : & $PY tests/test_templates_anim_ecran.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzane_"))
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE                               # noqa: E402  (t142 : PRELUDE_DZT)

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "da3255b1"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base a l'inspecteur (echantillon) mais pas l'editeur d'animation", r0.returncode == 0
      and b"DzEchantillon" in r0.stdout and b"DzAnimEditor" not in r0.stdout)
check("T2 la section suit l'echantillon, juste avant « Delete region » (toute region : le composant filtre) ; la toile passe par l'apercu d'animation AUTOUR des autres",
      BUN.count('r.jsx(DzEchantillon,{rg:c,tpl:a,setTpl:l}),r.jsx(DzAnimEditor,{rg:c,upd:function(pt){p(c.id,pt)}}),r.jsx(DzComposantEditor,') == 1
      and BUN.count("r.jsx(DzAnimEditor,") == 1 and BUN.count("children:[dzAnimApercu(j,dzTexteApercu(j,dzMasqueApercu(j,dzComposantFace(j,dzRegionFace(j))))),") == 1)   # #76 PR F : + le dessin d'un composant au centre


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


VARS = [re.search(r"var " + v + r"=.*?;\s*(?=var |function )", BUN, re.S) for v in ("DZ_ANIM_TYPES", "DZ_ANIM_COURBES", "DZ_ANIM_VISIBLES", "DZ_ANIM_CSS", "__dzAnimJeu")]
NOMS = ("dzAnimStyle", "dzAnimCss", "dzAnimApercu", "DzAnimEditor")
COUCHE = "\n".join(m.group(0) for m in VARS if m) + "\n" + "\n".join(fonction(n) for n in NOMS)
check("T3 la couche livree a les cinq tables et les quatre fonctions (une fois chacune)", all(VARS) and all(BUN.count("function " + n + "(") == 1 for n in NOMS))

HARNAIS = r"""
var H=[],hi=0,UPD=[];
var x={useState:function(v){var i=hi++;if(!(i in H))H[i]=v;return [H[i],function(n){H[i]=n}]},useRef:function(v){var i=hi++;if(!(i in H))H[i]={current:v};return H[i]}};
function el(t,p,k){p=p||{};return {t:t,p:p,props:p,key:k}}var r={jsx:el,jsxs:el,Fragment:"frag"};
var K="K",O="Champ",Ze="Case",re="Liste",Oe="Curseur",le="Saisie";
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function par(T,t,lab){return trouver(T,function(n){return n.t===t&&(lab===undefined||n.p.label===lab)})}
function ed(rg){hi=0;UPD=[];return DzAnimEditor({rg:rg,upd:function(pt){UPD.push(pt)}})}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    # t142 (09/10) : les tables DZ_ANIM_TYPES / DZ_ANIM_COURBES et les libelles passent par dzT (globale) des le
    # chargement ; le prelude la pose en FRANCAIS avant la couche (les attentes en francais restent vraies)
    f.write_text(AIDE.PRELUDE_DZT + COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
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
from app.services import template_anim as TA                        # noqa: E402
R = node("R.types=DZ_ANIM_TYPES.map(function(z){return z[0]});R.courbes=DZ_ANIM_COURBES.map(function(z){return z[0]});R.vis=DZ_ANIM_VISIBLES;")
check("P1 les types (hors « Aucune »), les courbes et les regions animables de l'ecran sont EXACTEMENT ceux du serveur",
      R is not None and R["types"][0] == "" and tuple(R["types"][1:]) == TA.TYPES and set(R["courbes"]) == set(TA.COURBES) and tuple(R["vis"]) == TA.VISIBLES, str(R))

print("\n[E] la section « Animation »")
R = node("""
R.son=ed({id:"s",type:"audio_slot"})===null;R.forme=ed({id:"f",type:"shape"})===null;
var RG={id:"t1",type:"text",text:"x"};var T=ed(RG);R.listes=par(T,"Liste").map(function(l){return [l.p.value,l.p.options.length]});R.champs=par(T,"Champ").map(function(c){return c.p.label}).filter(Boolean);
R.rejouer0=par(T,"K").length;
par(T,"Liste")[0].p.onChange("pop");R.pop=UPD.slice();
var A={in:{type:"pop",duration:0.8,delay:0.3,easing:"back"},out:{type:"fade",duration:0.5,delay:0}};
T=ed(Object.assign({},RG,{animation:A}));R.curseurs=par(T,"Curseur").map(function(c){return [c.p.label,c.p.min,c.p.max,c.p.value]});
R.courbes=par(T,"Liste").map(function(l){return l.p.options.map(function(o){return o.value})});R.btn=par(T,"K").map(function(b){return [b.p.children,!!b.p.title]});
par(T,"Curseur","Durée")[0].p.onChange(1.5);par(T,"Liste")[0].p.onChange("");R.majs=UPD.slice();
T=ed(Object.assign({},RG,{animation:{in:{type:"fade"}}}));par(T,"Liste")[0].p.onChange("");R.vide=UPD.slice();
T=ed(Object.assign({},RG,{animation:A}));var j0=__dzAnimJeu.n;par(T,"K")[0].p.onClick();R.jeu=[__dzAnimJeu.id,__dzAnimJeu.n-j0,UPD.slice()];
""")
check("E0 sous node : la section s'execute", R is not None)
if R:
    check("E1 rien pour une piste son ou une forme ; pour un texte : Entree et Sortie (7 choix, « Aucune » par defaut), pas de bouton tant que rien n'anime",
          R["son"] and R["forme"] and R["listes"] == [["", 7], ["", 7]] and R["champs"] == ["Entrée", "Sortie"] and R["rejouer0"] == 0, str(R["listes"]))
    check("E2 choisir « Pop » pose une entree COMPLETE (0,6 s, sans delai, courbe douce)",
          R["pop"] == [{"animation": {"in": {"type": "pop", "duration": 0.6, "delay": 0, "easing": "ease_out"}}}], str(R["pop"]))
    check("E3 curseurs dans les bornes du serveur (duree 0,1..5 s, delai 0..10 s ; la sortie dit « avance sur la fin ») ; la courbe n'existe pas pour un fondu",
          R["curseurs"] == [["Durée", 0.1, 5, 0.8], ["Délai après le début", 0, 10, 0.3], ["Durée", 0.1, 5, 0.5], ["Avance sur la fin", 0, 10, 0]]
          and len(R["courbes"]) == 3 and R["courbes"][1] == ["ease_out", "linear", "back"], str(R["curseurs"]) + str(R["courbes"]))
    check("E4 regler garde le reste ; « Aucune » retire l'entree en gardant la sortie ; plus rien -> animation null",
          R["majs"] == [{"animation": {"in": {"type": "pop", "duration": 1.5, "delay": 0.3, "easing": "back"}, "out": {"type": "fade", "duration": 0.5, "delay": 0}}},
                        {"animation": {"out": {"type": "fade", "duration": 0.5, "delay": 0}}}] and R["vide"] == [{"animation": None}], str(R["majs"]))
    check("E5 « Rejouer sur la toile » (avec title) designe CETTE region, relance le compteur et redessine",
          R["btn"] == [["▶ Rejouer sur la toile", True]] and R["jeu"][0] == "t1" and R["jeu"][1] == 1 and R["jeu"][2] == [{}], str(R["jeu"]))

print("\n[C] l'apercu sur la toile")
R = node("""
R.css1=dzAnimCss({in:{type:"pop",duration:0.8,delay:0.3,easing:"back"},out:{type:"fade",duration:0.5}});
R.css2=dzAnimCss({in:{type:"slide_left"}});R.css3=dzAnimCss({out:{type:"slide_up",duration:1,easing:"linear"}});R.css4=dzAnimCss({});
var face={t:"face"};__dzAnimJeu={id:"t1",n:4};
R.autre=dzAnimApercu({id:"t2",animation:{in:{type:"fade"}}},face)===face;R.sans=dzAnimApercu({id:"t1"},face)===face;
var A=dzAnimApercu({id:"t1",animation:{in:{type:"fade",duration:1}}},face);R.a={cls:A.p.className,anim:A.p.style.animation,pos:A.p.style.position,face:A.p.children===face,key:A.key};
__dzAnimJeu={id:"t1",n:5};R.k2=dzAnimApercu({id:"t1",animation:{in:{type:"fade"}}},face).key;
""")
check("C0 sous node : l'apercu s'execute", R is not None)
if R:
    check("C1 la courbe « rebond » est un cubic-bezier qui DEPASSE ; le fondu reste lineaire ; la sortie part APRES l'entree (+0,8 s de pose) ; rien a jouer -> vide",
          R["css1"] == "dzIn_pop 0.8s cubic-bezier(0.34,1.56,0.64,1) 0.3s both,dzOut_fade 0.5s linear 1.9s forwards"
          and R["css2"] == "dzIn_slide_left 0.6s cubic-bezier(0.33,1,0.68,1) 0s both" and R["css3"] == "dzOut_slide_up 1s linear 0.8s forwards" and R["css4"] == "", str(R))
    check("C2 seule la region rejouee est enveloppee (absolue, sur toute la case) ; chaque « Rejouer » change la cle (l'animation repart)",
          R["autre"] and R["sans"] and R["a"] == {"cls": "dz-anim-apercu", "anim": "dzIn_fade 1s linear 0s both", "pos": "absolute", "face": True, "key": "dzan4"}
          and R["k2"] == "dzan5", str(R["a"]))

check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3, __dzLibPicker x11)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and "window.confirm(" not in COUCHE and BUN.count("DzTracks") == 181
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3 and BUN.count("__dzLibPicker") == 11)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
