# -*- coding: utf-8 -*-
"""Studio : Animation, t236 (18/10/2026) — rubrique « Bibliothèque motion » de l'inspecteur de Direction motion
(plan docs/superpowers/plans/2026-10-17-studio-animation.md § t236 ; spec 2026-10-17 § B3 pour la licence, spec
2026-10-18 § 3 pour l'aperçu du bloc de précisions), dans le maillon de queue `dzmotion`
(scripts/patch_bundle_dzmotion.py, constante BIBLIO posée dans M5, devant DzMotionDirection).

Ce que ce banc garde, sous node avec les VRAIES fonctions extraites du livré (catalogue `Me`, `Wt`, bloc du maillon ;
React et le réseau simulés ; les données de personnalisation = le VRAI fichier du dépôt) :
  [N] rien ne part sur le réseau sans un clic : afficher la rubrique, saisir, cocher un thème, filtrer, taper un dépôt
      → aucune requête ; « Lire la licence » éteint tant que le dépôt est vide ;
  [I] importer un prompt : titre / texte / URL / auteur / thèmes, attribution affichée en direct (amber sans URL),
      aperçu du bloc de précisions (titre, règle « mes précisions priment », les 5 précisions), bouton éteint sans
      titre, texte ou URL ; le clic envoie UN POST /api/motion/biblio, relit la liste (dzMoCharger(true)), vide le
      formulaire, et le prompt apparaît dans la liste Source du nœud ; un refus du serveur est montré, la saisie gardée ;
  [S] installer un skill : « Lire la licence » → POST /api/motion/skills/apercu ; la licence (identifiant, fichier, texte)
      est montrée AVANT, sans aucune installation ; « Installer sous licence X » → POST /skills/installer {source,
      licence} puis relecture : le skill est dans la Source ; un dépôt sans licence est refusé à l'aperçu (message, pas
      de bouton d'installation) ; retaper le dépôt ou « Ne pas installer » efface l'aperçu sans requête ;
  [L] liste filtrée par thème, attribution (lien _blank noopener vers la fiche / le dépôt, auteur, licence), « Utiliser »
      pose la source ; suppression : confirmation (refus → aucune requête), DELETE puis relecture, la source du nœud
      est vidée si c'était elle ;
  [D] chaîne : sans la famille t236 = le bundle de 52efd328 octet pour octet ; inverse ; paires des ports intouchées ;
      comptes chiffrés : dzMoUS 2 (le bandeau garde sa saisie dans le magasin module `dzMoBib` et se redessine par
      l'état de rafraîchissement existant : aucun hook neuf), dzMoUE 3, x.useState( 731, confirmations 24 → 25 (la
      suppression), v2.8.0 ×4, DzTracks 181, Fu ; CRLF ; node --check ;
  [K] chaque clé studio.motion.bib_* a son FR et son EN, mêmes {variables}, toutes employées par le livré.
Run (depuis backend/) : & $PY tests/test_studio_motion_biblio.py"""
import importlib.util, json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(_ICI))

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


BASE = "52efd328"                # origin/main : t231-t235 et t239-t241 fusionnées et installées
BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")
PERSO_P = RACINE / "backend" / "app" / "motion" / "personnalisation.json"
PERSO = json.loads(PERSO_P.read_bytes().decode("utf-8"))

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const PERSO=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
function objet(debut){const i=S.indexOf(debut);if(i<0)throw new Error("introuvable : "+debut);let k=i+debut.indexOf("{"),n=0,q=null;
 for(let j=k;j<S.length;j++){const c=S[j];if(q){if(c==="\\"){j++;continue}if(c===q)q=null;continue}
  if(c==='"'||c==="'"||c==="`"){q=c;continue}if(c==="{")n++;else if(c==="}"){n--;if(!n)return S.slice(k,j+1)}}
 throw new Error("objet non fermé")}
let LANG="fr",H=[],hi=0,EFF=[],CALLS=[],SETS=[],ROUTES={},CONFIRME=true,CONF=[];
const x={useState(init){const i=hi++;if(!(i in H))H[i]=typeof init==="function"?init():init;
  return [H[i],function(v){H[i]=typeof v==="function"?v(H[i]):v}]},useEffect(f){EFF.push(f)},useRef(){return{current:null}}};
const r={jsx(t,p){return{t,p:p||{}}},jsxs(t,p){return{t,p:p||{}}}};
const window={dzLang(){return LANG},addEventListener(){},removeEventListener(){},
 __dzDialogue:{confirmer:async function(m,o){CONF.push([m,o]);return CONFIRME},saisir:async function(){return null}}};
async function fetch(u,o){const m=(o&&o.method)||"GET",ch=u.split("?")[0];CALLS.push({u,m,b:o&&o.body?JSON.parse(o.body):null});
 const f=ROUTES[m+" "+ch]||ROUTES[m+" *"];const v=f?f(u,o):{status:404,j:{detail:"x"}};
 return{ok:(v.status||200)<400,status:v.status||200,json:async function(){return v.j}}}
const dzT=function(k,v){return k+(v?JSON.stringify(v):"")},dzMq=function(k){return"MQ:"+k};
const STUB={x,r,window,fetch,dzT,dzMq,localStorage:{getItem(){return null},setItem(){}},DZ_FONTS:["Anton","Inter"],
 ie:"ie",O:"O",le:"le",re:"re",Ze:"Ze",DzColorPicker:"DzColorPicker",__dzGl(n){return"gl:"+n},__dzGlT(n,t){return t}};
const ENV=new Proxy(STUB,{has(t,k){return typeof k==="string"},get(t,k){if(k===Symbol.unscopables)return undefined;
 if(k in t)return t[k];if(k in globalThis)return globalThis[k];return function(){return null}}});
function arbre(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>arbre(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)arbre(n.p.children,f,acc);return acc}
function par(t,nom){return arbre(t,n=>n.p&&n.p["data-dz-motion"]===nom)[0]||null}
function champ(t,label){return arbre(t,n=>n.t==="O"&&n.p.label===label)[0]||null}
function texte(n){if(n==null||n===false)return"";if(typeof n!=="object")return String(n);if(Array.isArray(n))return n.map(texte).join("");
 return texte(n.p&&n.p.children)}
async function vider(){for(let k=0;k<6;k++){const e=EFF;EFF=[];e.forEach(f=>f());await new Promise(s=>setTimeout(s,0))}}
function poseur(nd){return function(k,v){nd.props=Object.assign({},nd.props,{[k]:v});SETS.push([k,v])}}
function rendre(C,nd,g){hi=0;EFF=[];return C({node:nd,graph:g,set:poseur(nd)})}
function n0(){return CALLS.length}
const STY=[{id:"style-charts",nature:"style",themes:["charts"],titre:{fr:"Graphiques",en:"Charts"}},
 {id:"style-kinetic-type",nature:"style",themes:["kinetic-type"],titre:{fr:"Typographie cinétique",en:"Kinetic type"}}];
let ENT=[{id:"prompt-a1",nature:"prompt",titre:"Nos barres qui montent",texte:"T",url:"https://exemple.org/fiche/1",auteur:"Équipe Deepotus",themes:["charts"]},
 {id:"skill-demo-mit",nature:"skill",titre:"demo-rebond",licence:"MIT",themes:[],source:{depot:"banc-demo/rebond",url:"https://github.com/banc-demo/rebond/tree/HEAD"}}];
const MIT="MIT License\n\nPermission is hereby granted, free of charge...";
(async function(){try{
 const SRC="var Me="+objet("Me={Image:")+";"+tranche("function Wt(","function dzFinImg(")+";"
  +tranche("var dzMoUS=","function DzAnimation(")
  +";return{Me,Wt,dzMoCache,dzMoBib,dzMotionBiblio,DzMotionDirection}";
 const M=new Function("ENV","with(ENV){"+SRC+"}")(ENV);
 ROUTES["GET /api/motion/biblio"]=()=>({j:{entrees:STY.concat(ENT)}});
 ROUTES["GET /api/motion/moteurs"]=()=>({j:{moteurs:[]}});
 ROUTES["GET /api/motion/personnalisation"]=()=>({j:{neutre:PERSO.neutre,curseurs:PERSO.curseurs,precisions:PERSO.precisions,tempo:PERSO.tempo}});
 ROUTES["GET *"]=(u)=>({j:{id:decodeURIComponent(u.split("/").pop())}});
 const nd={id:"d",type:"MotionDirection",props:{style:"style-kinetic-type",source:"",consigne:"",moteur:"",modele:""}},g={nodes:[nd],edges:[]};
 let t=rendre(M.DzMotionDirection,nd,g);await vider();t=rendre(M.DzMotionDirection,nd,g);
 const sources=tr=>((champ(tr,"studio.motion.source")||{p:{children:{p:{options:[]}}}}).p.children.p.options||[]).map(o=>o.value);
 const rub=arbre(t,n=>n.t==="ie"&&n.p.label==="studio.motion.bib_titre")[0];
 OUT.rub={la:!!rub,ouvert:rub&&rub.p.defaultOpen,dedans:!!(rub&&par(rub,"bib-titre")&&par(rub,"bib-skill")&&par(rub,"bib-liste"))};
 OUT.ordre=arbre(t,n=>n.t==="ie").map(n=>n.p.label);
 // ── [N] rien sans clic ──
 const c0=n0();
 par(t,"bib-titre").p.onChange("Nos chiffres qui dansent");t=rendre(M.DzMotionDirection,nd,g);
 OUT.pretTitre=par(t,"bib-importer").p.disabled;
 par(t,"bib-texte").p.onChange({target:{value:"Fais monter chaque barre sur le temps fort."}});t=rendre(M.DzMotionDirection,nd,g);
 OUT.attrVide={txt:texte(par(t,"bib-attribution")),col:par(t,"bib-attribution").p.style.color,dis:par(t,"bib-importer").p.disabled,
  title:par(t,"bib-importer").p.title};
 par(t,"bib-url").p.onChange("  https://exemple.org/nos-fiches/42  ");t=rendre(M.DzMotionDirection,nd,g);
 OUT.attrUrl=texte(par(t,"bib-attribution"));
 par(t,"bib-auteur").p.onChange("Équipe Deepotus");t=rendre(M.DzMotionDirection,nd,g);
 OUT.attr={txt:texte(par(t,"bib-attribution")),col:par(t,"bib-attribution").p.style.color};
 par(t,"bib-theme-charts").p.onClick();t=rendre(M.DzMotionDirection,nd,g);par(t,"bib-theme-kinetic-type").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 par(t,"bib-theme-kinetic-type").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 OUT.themes={charts:par(t,"bib-theme-charts").p["aria-pressed"],kin:par(t,"bib-theme-kinetic-type").p["aria-pressed"],
  lib:texte(par(t,"bib-theme-charts")),etat:M.dzMoBib.d.th.slice()};
 OUT.lireVide=par(t,"bib-lire").p.disabled;
 par(t,"bib-skill").p.onChange("banc-demo/rebond");t=rendre(M.DzMotionDirection,nd,g);OUT.lirePret=par(t,"bib-lire").p.disabled;
 champ(t,"studio.motion.bib_filtre").p.children.p.onChange("charts");t=rendre(M.DzMotionDirection,nd,g);
 champ(t,"studio.motion.bib_filtre").p.children.p.onChange("");t=rendre(M.DzMotionDirection,nd,g);
 OUT.sansClic=CALLS.slice(c0);
 OUT.apercu=texte(par(t,"bib-apercu"));OUT.pret=par(t,"bib-importer").p.disabled;
 // ── [I] importer ──
 let recu=null;ROUTES["POST /api/motion/biblio"]=(u,o)=>{recu=JSON.parse(o.body);const e={id:"prompt-neuf1",nature:"prompt",titre:recu.titre.trim(),
  texte:recu.texte,url:recu.url,auteur:recu.auteur,themes:recu.themes};ENT=[e].concat(ENT);return{j:e}};
 OUT.srcAvant=sources(t);
 let c1=n0();await par(t,"bib-importer").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 OUT.imp={appels:CALLS.slice(c1).map(c=>c.m+" "+c.u),corps:recu,msg:texte(par(t,"bib-message")),err:M.dzMoBib.d.err,
  vide:[par(t,"bib-titre").p.value,par(t,"bib-texte").p.value,par(t,"bib-url").p.value,par(t,"bib-auteur").p.value,M.dzMoBib.d.th.length],
  src:sources(t),liste:!!par(t,"bib-prompt-neuf1")};
 // refus du serveur : la saisie reste
 ROUTES["POST /api/motion/biblio"]=()=>({status:400,j:{detail:"L'URL d'attribution est obligatoire."}});
 M.dzMoBib.d.ti="X";M.dzMoBib.d.tx="Y";M.dzMoBib.d.u="https://exemple.org/z";t=rendre(M.DzMotionDirection,nd,g);
 c1=n0();await par(t,"bib-importer").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 OUT.impRefus={msg:texte(par(t,"bib-message")),col:par(t,"bib-message").p.style.color,garde:par(t,"bib-titre").p.value,
  appels:CALLS.slice(c1).map(c=>c.m+" "+c.u)};
 M.dzMoBib.d.ti="";M.dzMoBib.d.tx="";M.dzMoBib.d.u="";t=rendre(M.DzMotionDirection,nd,g);
 // ── [S] skill ──
 ROUTES["POST /api/motion/skills/apercu"]=(u,o)=>{const s=JSON.parse(o.body).source;return s==="banc-demo/sans"?
  {status:400,j:{detail:"Aucune licence dans banc-demo/sans : installation refusée (MIT, Apache-2.0, BSD ou ISC requise)."}}:
  {j:{id:"skill-banc-demo-rebond",titre:"demo-rebond",description:"Un skill de démo écrit par nous.",source:{depot:"banc-demo/rebond",
   url:"https://github.com/banc-demo/rebond/tree/HEAD"},licence:"MIT",fichier_licence:"LICENSE",licence_texte:MIT,notice:false}}};
 let inst=null;ROUTES["POST /api/motion/skills/installer"]=(u,o)=>{inst=JSON.parse(o.body);const e={id:"skill-banc-demo-rebond",nature:"skill",
  titre:"demo-rebond",licence:"MIT",themes:[],source:{depot:"banc-demo/rebond",url:"https://github.com/banc-demo/rebond/tree/HEAD"}};
  ENT=ENT.concat([e]);return{j:e}};
 c1=n0();await par(t,"bib-lire").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 OUT.ap={appels:CALLS.slice(c1).map(c=>c.m+" "+c.u),corps:CALLS.slice(c1)[0]&&CALLS.slice(c1)[0].b,
  id:texte(par(t,"bib-licence-id")),texte:par(t,"bib-licence-texte")&&par(t,"bib-licence-texte").p.value,
  ro:par(t,"bib-licence-texte")&&par(t,"bib-licence-texte").p.readOnly,bouton:texte(par(t,"bib-installer")),
  de:texte(par(t,"bib-licence")),inst:inst,lire:!!par(t,"bib-lire")};
 // annuler, puis retaper : l'aperçu s'efface sans requête
 c1=n0();par(t,"bib-annuler").p.onClick();t=rendre(M.DzMotionDirection,nd,g);OUT.annule={pan:!!par(t,"bib-licence"),lire:!!par(t,"bib-lire")};
 await par(t,"bib-lire").p.onClick();t=rendre(M.DzMotionDirection,nd,g);const c2=n0();
 par(t,"bib-skill").p.onChange("banc-demo/rebond2");t=rendre(M.DzMotionDirection,nd,g);OUT.retape={pan:!!par(t,"bib-licence"),appels:CALLS.length-c2};
 par(t,"bib-skill").p.onChange("banc-demo/rebond");t=rendre(M.DzMotionDirection,nd,g);await par(t,"bib-lire").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 c1=n0();await par(t,"bib-installer").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 OUT.inst={appels:CALLS.slice(c1).map(c=>c.m+" "+c.u),corps:inst,msg:texte(par(t,"bib-message")),pan:!!par(t,"bib-licence"),
  skill:par(t,"bib-skill").p.value,src:sources(t)};
 // refus : dépôt sans licence
 par(t,"bib-skill").p.onChange("banc-demo/sans");t=rendre(M.DzMotionDirection,nd,g);inst=null;
 c1=n0();await par(t,"bib-lire").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 OUT.refus={appels:CALLS.slice(c1).map(c=>c.m+" "+c.u),msg:texte(par(t,"bib-message")),col:par(t,"bib-message").p.style.color,
  pan:!!par(t,"bib-licence"),btn:!!par(t,"bib-installer"),inst:inst};
 // ── [L] liste, filtre, attribution, utiliser, supprimer ──
 const ids=tr=>arbre(tr,n=>n.p&&typeof n.p["data-dz-motion"]==="string"&&/^bib-(prompt|skill)-/.test(n.p["data-dz-motion"])).map(n=>n.p["data-dz-motion"]);
 OUT.tous=ids(t);
 champ(t,"studio.motion.bib_filtre").p.children.p.onChange("charts");t=rendre(M.DzMotionDirection,nd,g);OUT.charts=ids(t);
 OUT.filtreOpts=champ(t,"studio.motion.bib_filtre").p.children.p.options;
 champ(t,"studio.motion.bib_filtre").p.children.p.onChange("kinetic-type");t=rendre(M.DzMotionDirection,nd,g);
 OUT.kin={ids:ids(t),vide:texte(par(t,"bib-vide"))};
 champ(t,"studio.motion.bib_filtre").p.children.p.onChange("");t=rendre(M.DzMotionDirection,nd,g);
 const it=par(t,"bib-prompt-a1"),is=par(t,"bib-skill-demo-mit");
 const lien=n=>{const a=par(n,"bib-lien");return a&&{href:a.p.href,target:a.p.target,rel:a.p.rel,txt:texte(a)}};
 OUT.item={p:{info:texte(par(it,"bib-info")),lien:lien(it)},s:{info:texte(par(is,"bib-info")),lien:lien(is)}};
 SETS=[];par(it,"bib-utiliser").p.onClick();OUT.utiliser=SETS.slice();t=rendre(M.DzMotionDirection,nd,g);
 OUT.utilisee={dis:par(par(t,"bib-prompt-a1"),"bib-utiliser").p.disabled,txt:texte(par(par(t,"bib-prompt-a1"),"bib-utiliser"))};
 let del=[];ROUTES["DELETE *"]=(u)=>{const id=decodeURIComponent(u.split("/").pop());del.push(id);ENT=ENT.filter(e=>e.id!==id);return{j:{ok:true,id}}};
 CONFIRME=false;CONF=[];c1=n0();await par(par(t,"bib-prompt-a1"),"bib-supprimer").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 OUT.supNon={conf:CONF.slice(),appels:CALLS.length-c1,reste:!!par(t,"bib-prompt-a1")};
 CONFIRME=true;CONF=[];SETS=[];c1=n0();await par(par(t,"bib-prompt-a1"),"bib-supprimer").p.onClick();t=rendre(M.DzMotionDirection,nd,g);
 OUT.supOui={conf:CONF.length,appels:CALLS.slice(c1).map(c=>c.m+" "+c.u),del:del.slice(),sets:SETS.slice(),reste:!!par(t,"bib-prompt-a1"),
  src:sources(t),msg:texte(par(t,"bib-message"))};
 // une autre entrée que la source : la source du nœud n'est pas touchée
 SETS=[];await par(par(t,"bib-skill-demo-mit"),"bib-supprimer").p.onClick();OUT.supAutre=SETS.slice();
 // ── EN : noms des thèmes et précisions dans la langue ──
 LANG="en";t=rendre(M.DzMotionDirection,nd,g);OUT.en={theme:texte(par(t,"bib-theme-charts")),apercu:texte(par(t,"bib-apercu"))};LANG="fr";
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));})();
"""

print("[N/I/S/L] sous node, vraies fonctions du livré")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzmotion_biblio_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(RAW)
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js"), str(PERSO_P)], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=120)
try:
    F = json.loads(rn.stdout or "{}")
except ValueError:
    F = {"err": (rn.stdout or "")[-300:] + (rn.stderr or "")[-300:]}
check("B0 bloc du maillon extrait et exécuté (dzMotionBiblio, magasin dzMoBib)", "err" not in F, str(F.get("err", ""))[:400])
rb = F.get("rub") or {}
check("B1 rubrique « Bibliothèque motion » repliée par défaut, avec import, skill et liste",
      rb.get("la") is True and rb.get("ouvert") is False and rb.get("dedans") is True, str(rb))
check("B2 placée après la Source et avant « Personnaliser »",
      (F.get("ordre") or [])[:3] == ["studio.motion.titre", "studio.motion.bib_titre", "studio.motion.personnaliser"], str(F.get("ordre")))

check("N1 saisir, cocher des thèmes, taper un dépôt, filtrer : AUCUNE requête", F.get("sansClic") == [], str(F.get("sansClic")))
check("N2 « Lire la licence » éteint tant que le dépôt est vide, allumé ensuite", F.get("lireVide") is True and F.get("lirePret") is False)
check("N3 « Importer » éteint sans URL (titre + texte seuls), avec l'aide « obligatoires »",
      F.get("pretTitre") is True and (F.get("attrVide") or {}).get("dis") is True
      and (F.get("attrVide") or {}).get("title") == "studio.motion.bib_import_manque" and F.get("pret") is False, str(F.get("attrVide")))

av = F.get("attrVide") or {}
check("I1 attribution en direct : sans URL → rappel en ambre", av.get("txt") == "studio.motion.bib_attribution_vide"
      and av.get("col") == "var(--amber)", str(av))
check("I2 avec l'URL seule → « Attribution : <url> » (espaces retirés)",
      F.get("attrUrl") == 'studio.motion.bib_attribution_url{"url":"https://exemple.org/nos-fiches/42"}', str(F.get("attrUrl")))
check("I3 avec l'auteur → « Attribution : <auteur> — <url> »", (F.get("attr") or {}).get("txt") ==
      'studio.motion.bib_attribution{"auteur":"Équipe Deepotus","url":"https://exemple.org/nos-fiches/42"}'
      and (F.get("attr") or {}).get("col") == "var(--ink-soft)", str(F.get("attr")))
th = F.get("themes") or {}
check("I4 thèmes : bascule par clic, nom lu sur la fiche maison du thème", th.get("charts") is True and th.get("kin") is False
      and th.get("lib") == "Graphiques" and th.get("etat") == ["charts"], str(th))
pr = PERSO["precisions"]
check("I5 aperçu du bloc de précisions : aide, règle « mes précisions priment » (titre + règle des données), les 5 précisions",
      "studio.motion.bib_apercu_aide" in F.get("apercu", "")
      and f'studio.motion.apercu_regle{json.dumps({"titre": pr["titre"]["fr"], "regle": pr["regle"]["fr"]}, ensure_ascii=False, separators=(",", ":"))}' in F.get("apercu", "")
      and all(f'studio.motion.bib_apercu_champ{{"libelle":{json.dumps(c["libelle"]["fr"], ensure_ascii=False)}}}' in F.get("apercu", "")
              for c in pr["champs"]) and len(pr["champs"]) == 5, F.get("apercu", "")[:300])
im = F.get("imp") or {}
check("I6 le clic envoie UN POST /api/motion/biblio puis relit la liste (dzMoCharger(true))",
      im.get("appels") == ["POST /api/motion/biblio", "GET /api/motion/biblio"], str(im.get("appels")))
check("I7 corps : titre, texte, URL (nettoyée), auteur, thèmes", im.get("corps") == {"titre": "Nos chiffres qui dansent",
      "texte": "Fais monter chaque barre sur le temps fort.", "url": "https://exemple.org/nos-fiches/42", "auteur": "Équipe Deepotus",
      "themes": ["charts"]}, str(im.get("corps")))
check("I8 après l'import : message, formulaire vidé, le prompt est dans la liste ET dans la Source du nœud",
      im.get("msg") == 'studio.motion.bib_import_fait{"titre":"Nos chiffres qui dansent"}' and im.get("err") is False
      and im.get("vide") == ["", "", "", "", 0] and "prompt-neuf1" in (im.get("src") or [])
      and "prompt-neuf1" not in (F.get("srcAvant") or []) and im.get("liste") is True, str(im)[:300])
ir = F.get("impRefus") or {}
check("I9 refus du serveur : son message (rouge), la saisie est gardée, aucune relecture",
      ir.get("msg") == "L'URL d'attribution est obligatoire." and ir.get("col") == "var(--red)" and ir.get("garde") == "X"
      and ir.get("appels") == ["POST /api/motion/biblio"], str(ir))

ap = F.get("ap") or {}
check("S1 « Lire la licence » : UN POST /api/motion/skills/apercu {source}, AUCUNE installation",
      ap.get("appels") == ["POST /api/motion/skills/apercu"] and ap.get("corps") == {"source": "banc-demo/rebond"}
      and ap.get("inst") is None, str(ap.get("appels")))
check("S2 la licence est montrée AVANT : identifiant + fichier, texte complet en lecture seule, nom et dépôt",
      ap.get("id") == 'studio.motion.bib_skill_licence{"licence":"MIT","fichier":"LICENSE"}' and ap.get("ro") is True
      and ap.get("texte", "").startswith("MIT License") and 'studio.motion.bib_skill_de{"titre":"demo-rebond","depot":"banc-demo/rebond"}' in ap.get("de", ""),
      str(ap)[:300])
check("S3 le bouton dit la licence : « Installer sous licence MIT » ; « Lire la licence » remplacé",
      ap.get("bouton") == 'studio.motion.bib_skill_installer{"licence":"MIT"}' and ap.get("lire") is False, str(ap.get("bouton")))
check("S4 « Ne pas installer » efface l'aperçu ; retaper le dépôt aussi, sans requête",
      F.get("annule") == {"pan": False, "lire": True} and F.get("retape") == {"pan": False, "appels": 0}, str(F.get("retape")))
ins = F.get("inst") or {}
check("S5 « Installer » : POST /skills/installer {source, licence montrée} puis relecture de la liste",
      ins.get("appels") == ["POST /api/motion/skills/installer", "GET /api/motion/biblio"]
      and ins.get("corps") == {"source": "banc-demo/rebond", "licence": "MIT"}, str(ins.get("appels")) + str(ins.get("corps")))
check("S6 après l'installation : message, aperçu fermé, dépôt vidé, le skill est dans la Source",
      ins.get("msg") == 'studio.motion.bib_skill_fait{"titre":"demo-rebond","licence":"MIT"}' and ins.get("pan") is False
      and ins.get("skill") == "" and "skill-banc-demo-rebond" in (ins.get("src") or []), str(ins)[:300])
rf = F.get("refus") or {}
check("S7 dépôt sans licence : refus du serveur montré (rouge), aucun aperçu, aucun bouton d'installation, aucune installation",
      rf.get("appels") == ["POST /api/motion/skills/apercu"] and "Aucune licence dans banc-demo/sans" in rf.get("msg", "")
      and rf.get("col") == "var(--red)" and rf.get("pan") is False and rf.get("btn") is False and rf.get("inst") is None, str(rf))

check("L1 la liste : prompts et skills (pas les fiches maison)", sorted(F.get("tous") or []) ==
      ["bib-prompt-a1", "bib-prompt-neuf1", "bib-skill-banc-demo-rebond", "bib-skill-demo-mit"], str(F.get("tous")))
check("L2 filtre par thème : « charts » → les deux prompts du thème", sorted(F.get("charts") or []) == ["bib-prompt-a1", "bib-prompt-neuf1"],
      str(F.get("charts")))
check("L3 options du filtre : « Tous les thèmes » puis les thèmes des fiches maison",
      F.get("filtreOpts") == [{"value": "", "label": "studio.motion.bib_filtre_tous"}, {"value": "charts", "label": "Graphiques"},
                              {"value": "kinetic-type", "label": "Typographie cinétique"}], str(F.get("filtreOpts")))
check("L4 thème sans entrée → message vide", (F.get("kin") or {}).get("ids") == [] and (F.get("kin") or {}).get("vide") == "studio.motion.bib_vide")
itp, its = (F.get("item") or {}).get("p") or {}, (F.get("item") or {}).get("s") or {}
check("L5 attribution d'un prompt : nature, auteur, thème ; lien _blank noopener vers SA fiche",
      itp.get("info") == 'studio.motion.bib_nature_prompt · studio.motion.bib_par{"auteur":"Équipe Deepotus"} · Graphiques'
      and itp.get("lien") == {"href": "https://exemple.org/fiche/1", "target": "_blank", "rel": "noopener noreferrer",
                              "txt": "studio.motion.bib_fiche"}, str(itp))
check("L6 un skill : licence et dépôt ; lien vers le dépôt GitHub",
      its.get("info") == 'studio.motion.bib_nature_skill{"licence":"MIT"} · banc-demo/rebond'
      and (its.get("lien") or {}).get("href") == "https://github.com/banc-demo/rebond/tree/HEAD", str(its))
check("L7 « Utiliser » pose la source du nœud (consigne remise à zéro) ; le bouton dit alors « Source du nœud », éteint",
      F.get("utiliser") == [["source", "prompt-a1"], ["consigne", ""]]
      and F.get("utilisee") == {"dis": True, "txt": "studio.motion.bib_utilisee"}, str(F.get("utiliser")))
sn = F.get("supNon") or {}
check("L8 suppression : confirmation demandée (titre cité) ; refusée → aucune requête, l'entrée reste",
      len(sn.get("conf") or []) == 1 and sn["conf"][0][0] == 'studio.motion.bib_supprimer_q{"titre":"Nos barres qui montent"}'
      and sn["conf"][0][1] == {"titre": "studio.motion.bib_titre", "ok": "studio.motion.bib_supprimer"}
      and sn.get("appels") == 0 and sn.get("reste") is True, str(sn))
so = F.get("supOui") or {}
check("L9 confirmée → DELETE /api/motion/biblio/<id> puis relecture ; l'entrée et la Source la perdent",
      so.get("conf") == 1 and so.get("appels") == ["DELETE /api/motion/biblio/prompt-a1", "GET /api/motion/biblio"]
      and so.get("del") == ["prompt-a1"] and so.get("reste") is False and "prompt-a1" not in (so.get("src") or [])
      and so.get("msg") == 'studio.motion.bib_supprime{"titre":"Nos barres qui montent"}', str(so)[:300])
check("L10 la source du nœud était elle → vidée ; une autre entrée supprimée → la source n'est pas touchée",
      so.get("sets") == [["source", ""], ["consigne", ""]] and F.get("supAutre") == [], str(so.get("sets")) + str(F.get("supAutre")))
en = F.get("en") or {}
check("E1 EN : noms des thèmes et précisions de l'aperçu dans la langue", en.get("theme") == "Charts"
      and all(c["libelle"]["en"] in en.get("apercu", "") for c in pr["champs"]) and pr["regle"]["en"] in en.get("apercu", ""), str(en)[:200])

# ── [D] chaîne ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[D] maillon dzmotion : famille t236")


def git(rev, chemin):
    r_ = subprocess.run(["git", "show", f"{rev}:{chemin}"], capture_output=True, cwd=str(RACINE))
    return r_.stdout if r_.returncode == 0 else None


def crlf(b_):
    return b_ if b"\r\n" in b_ else b_.replace(b"\n", b"\r\n")


import patch_bundle_dzmotion as M                                    # noqa: E402
import _i18n_l1_aide as AIDE                                         # noqa: E402
base = git(BASE, "frontend/dist/assets/index-BEOJX8L5.js")
src_b = git(BASE, "scripts/patch_bundle_dzmotion.py")
MB = None
if src_b:
    p_ = pathlib.Path(tempfile.mkdtemp(prefix="dzmo_base_")) / "patch_base.py"
    p_.write_bytes(src_b)
    sp_ = importlib.util.spec_from_file_location("patch_dzmotion_base", p_)
    MB = importlib.util.module_from_spec(sp_)
    sp_.loader.exec_module(MB)
avant = M.defaire(AIDE.avant_dzdock(BUNDLE))       # 19/10 : le maillon dzdock, posé APRÈS dzmotion, défait d'abord
BIBS = getattr(M, "BIBLIO", "")              # la famille t236 (absente sur la base : ROUGE)
check("D1 sans la famille t236 = le bundle de 52efd328 octet pour octet (défaire le neuf, appliquer le maillon de 52efd328)",
      base is not None and MB is not None and MB.appliquer(avant).encode("utf-8") == crlf(base))
check("D2 inverse : avant_dzmotion(livré) = défaire ; aller-retour exact",
      AIDE.avant_dzmotion(BUNDLE) == avant and M.appliquer(avant) == AIDE.avant_dzdock(BUNDLE))
# t238 (19/10) : la famille C (nœud MotionCode) élargit M1-M5 et ajoute M8-M10 ; les ANCRES de M0-M7 ne bougent pas.
check("D3 ancres M0-M7 identiques à 52efd328, paires M0 / M6 / M7 identiques : ancrage inchangé (t238 : + M8-M10)",
      MB is not None and len(MB.PAIRES) == 8 and len(M.PAIRES) == 11
      and all(M.PAIRES[i][0] == MB.PAIRES[i][0] for i in range(8))
      and all(M.PAIRES[i] == MB.PAIRES[i] for i in (0, 6, 7)))
check("D4 M5 = celui de 52efd328 + le magasin dzMoBib + BIBLIO devant DzMotionDirection + l'appel dans l'inspecteur",
      MB is not None and bool(BIBS) and M.FONCTIONS.replace("dzMoBib={},", "", 1).replace(BIBS, "", 1)
      .replace("dzMotionBiblio(e,o,P,f),", "", 1)
      # 19/10 (PR #390, délais) : deux raisons de repli et la clé d'échec choisie par l'appelant
      .replace('c==="delai"?dzT("studio.motion.raison_delai"):c==="erreur_moteur"?dzT("studio.motion.raison_erreur_moteur"):',
               "", 1)
      .replace("function dzMotionErreur(j,k){", "function dzMotionErreur(j){", 1)
      .replace('dzT(k||"studio.motion.echec")', 'dzT("studio.motion.echec")', 1) == MB.FONCTIONS)
check("D5 hooks : dzMoUS 3 (= HOOKS ; t236 aucun neuf : la saisie vit dans dzMoBib ; t238 : l'état de DzMotionCode), "
      "dzMoUE 3 ; x.useState( 731",
      BUNDLE.count("dzMoUS(") == 3 == M.HOOKS and BUNDLE.count("dzMoUE(") == 3 and BUNDLE.count("x.useState(") == 731
      and bool(BIBS) and "dzMoUS(" not in BIBS and "useState" not in BIBS)
hors_b = base.decode("utf-8").count("await window.__dzDialogue.confirmer(") if base else -1
check("D6 confirmations 24 → 25 : la seule neuve est la suppression du bandeau",
      hors_b == 24 and BUNDLE.count("await window.__dzDialogue.confirmer(") == 25
      and BIBS.count("await window.__dzDialogue.confirmer(") == 1, str(hors_b))
check("D7 v2.8.0 ×4, DzTracks 181, littéral Fu inchangé", BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181
      and base is not None and BUNDLE.count("Fu") == base.decode("utf-8").count("Fu"))
check("D8 octets : CRLF préservés, aucun LF nu ; aucun .bak_dzmotion", RAW.count(b"\r\n") > 15000
      and RAW.count(b"\n") == RAW.count(b"\r\n") and not (BUN_P.parent / (BUN_P.name + ".bak_dzmotion")).exists())
r_ = subprocess.run(["node", "--check", str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
check("D9 node --check du livré", r_.returncode == 0, (r_.stderr or "")[-300:])
check("D10 routes du bandeau : t233 (biblio, installer) + l'aperçu neuf ; aucune autre adresse",
      sorted(set(re.findall(r'"(/api/[a-z/]+)"', BIBS))) == ["/api/motion/biblio", "/api/motion/biblio/",
                                                               "/api/motion/skills/apercu", "/api/motion/skills/installer"],
      str(sorted(set(re.findall(r'"(/api/[a-z/]+)"', BIBS)))))
check("D11 aucune requête à l'affichage : le bandeau ne contient ni useEffect ni chargement hors des gestes",
      "dzMoUE(" not in BIBS and BIBS.count("dzMoEnvoyer(\"") == 4 and BIBS.count("dzMoCharger(!0)") == 3)

# ── [K] textes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] textes")
MO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "motion.json").read_bytes().decode("utf-8"))
BIB = sorted(k for k in MO if k.startswith("studio.motion.bib_"))
cles_b = sorted(set(re.findall(r'dzT\("(studio\.motion\.[a-z0-9_]+)"', BIBS)))
check("K1 43 clés studio.motion.bib_*, FR ET EN", len(BIB) == 43 and all(MO[k]["fr"].strip() and MO[k]["en"].strip() for k in BIB),
      str(len(BIB)))
check("K2 mêmes {variables} en FR et en EN", all(sorted(re.findall(r"\{(\w+)\}", MO[k]["fr"])) == sorted(re.findall(r"\{(\w+)\}", MO[k]["en"]))
                                                 for k in BIB))
check("K3 le bandeau emploie exactement ces clés (+ en_cours et apercu_regle déjà là), toutes dans le livré",
      sorted(set(cles_b) - {"studio.motion.en_cours", "studio.motion.apercu_regle"}) == BIB
      and all(f'dzT("{k}"' in BUNDLE for k in BIB), str(sorted(set(cles_b) ^ set(BIB))[:6]))
check("K4 aucune phrase en dur dans le bandeau (littéraux : jetons, CSS, adresses)",
      not [s for s in re.findall(r'"((?:[^"\\]|\\.)*)"', BIBS) if re.search(r"[A-Za-zÀ-ÿ]{2,}\s+[A-Za-zÀ-ÿ]{2,}", s)
           and not s.startswith(("1px solid", "1px dashed", "noopener noreferrer", "0 0 8px", "6px 8px", "2px 0 4px", "4px 0"))])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
