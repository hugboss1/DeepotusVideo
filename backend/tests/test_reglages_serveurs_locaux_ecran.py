# -*- coding: utf-8 -*-
"""t223 (Menus : Réglages, 16/10/2026) — l'ÉCRAN : Clés d'API › LLM local, « Serveurs locaux » (banc serveur à part :
test_reglages_serveurs_locaux.py).

Défaut relevé sur e544888a : l'encart « LLM local (Ollama) » (`wm`) ne réglait qu'UN couple OLLAMA_URL / OLLAMA_MODEL,
en API Ollama native ; impossible d'ajouter LM Studio, llama.cpp, vLLM ou un second Ollama.

Ce que ce banc garde (DzServeursLocaux du maillon dzreglages rendu sous node, hooks simulés À ÉTAT, faux serveur) :
  [A] chargement : GET /api/reglages/serveurs-locaux ; la première ligne (Ollama intégré) montre OLLAMA_URL et
      OLLAMA_MODEL tels quels, « intégré », Lire les modèles et Tester, PAS de Supprimer ; puis les serveurs ajoutés ;
  [B] le formulaire : préréglage → nom, URL, type ; la clé (password) n'existe que pour un serveur compatible OpenAI et
      s'oublie si l'on repasse en Ollama ; « Lire les modèles » grisé sans URL, puis POST lire-modeles {url, type, cle} ;
  [C] Enregistrer : POST {nom, url, type, cle, modeles, defaut} ; formulaire fermé, clé oubliée ; la ligne dit
      local:<id> · type, « n modèles · gratuit », prêt ;
  [D] refus du serveur : son message en rouge, formulaire gardé ;
  [E] par ligne : Tester (la première ligne aussi), Lire les modèles (première ligne : montrés, rien d'écrit ; ajoutée :
      enregistrés), défaut changé, Remplacer la clé (OpenAI seulement) ;
  [F] Supprimer en DEUX clics ; jamais sur la première ligne ;
  [G] sites : la liste se pose juste APRÈS `wm`, resté intact ; champs de clé en password ; une seule racine d'API ;
  [H] i18n : clés reglages.locaux.* FR/EN (menus.json), une phrase FR = une traduction, catalogue assemblé ;
  [I] maillon dzreglages : aller-retour à l'octet, défaut d'origine dans l'avant, aucun chevauchement G1, comptes figés,
      CRLF, aucun .bak, aucune clé dzT construite, aucun dzT local, style compté intact, 21 paires.
Run (depuis backend/) : & $PY tests/test_reglages_serveurs_locaux_ecran.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
CLE = "sk-faussecle-ecran-t223-000000"

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const CLE=process.argv[3];const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
const STORE=new Map();let CUR="",IDX=0;const EFF=[];
const x={useReducer(fn,init){const k=CUR+"#"+(IDX++);if(!STORE.has(k))STORE.set(k,init);
  return[STORE.get(k),a=>{STORE.set(k,fn(STORE.get(k),a))}]},
 useEffect(f){const k=CUR+"#"+(IDX++);if(!STORE.has(k)){STORE.set(k,1);EFF.push(f)}},
 useState(){throw new Error("useState interdit (compte figé 731)")},useRef(v){return{current:v}}};
const r={jsx:(t,p,key)=>({t,p,key}),jsxs:(t,p,key)=>({t,p,key}),Fragment:"Fragment"};
function K(){}function jt(){}function te(){}function re(){}
function dzT(k,v){return v?k+JSON.stringify(v):k}
function rendre(el,ch){if(Array.isArray(el))return el.map((e,i)=>rendre(e,ch+"/"+i));
 if(!el||typeof el!=="object")return el;
 if(typeof el.t==="function"&&/^Dz/.test(el.t.name)){const sv=[CUR,IDX];CUR=ch+":"+el.t.name+":"+(el.key||"");IDX=0;
  const out=el.t(el.p);const moi=CUR;CUR=sv[0];IDX=sv[1];return rendre(out,moi)}
 const p=Object.assign({},el.p);if(p.children!==undefined)p.children=rendre(p.children,ch+"/c");
 return{t:typeof el.t==="function"?el.t.name:el.t,p,key:el.key}}
function tous(n,pred,acc){acc=acc||[];if(Array.isArray(n)){n.forEach(e=>tous(e,pred,acc));return acc}
 if(!n||typeof n!=="object")return acc;if(pred(n))acc.push(n);tous(n.p&&n.p.children,pred,acc);return acc}
function texte(n){if(Array.isArray(n))return n.map(texte).join("");if(n==null||n===false)return"";if(typeof n!=="object")return String(n);
 return texte(n.p&&n.p.children)}
// le faux serveur : la première ligne (Ollama intégré) puis les serveurs ajoutés ; jamais une clé en sortie
const APPELS=[];let REFUS={};
const PREMIERE={id:"ollama",moteur:"ollama",nom:"Ollama",type:"ollama",url:"http://127.0.0.1:11434",modeles:["qwen2.5:14b-instruct"],
 defaut:"qwen2.5:14b-instruct",cle:"",cle_posee:false,integre:true};
let LISTE=[{id:"ollama2",nom:"Ollama (PC du salon)",type:"ollama",url:"http://192.168.1.30:11434",modeles:["llama3.2:3b"],defaut:"llama3.2:3b",cle_posee:false}];
const PRE=[{id:"ollama",nom:"Ollama",type:"ollama",url:"http://127.0.0.1:11434"},{id:"lmstudio",nom:"LM Studio",type:"openai",url:"http://127.0.0.1:1234/v1"}];
function rep(o,code){return Promise.resolve({ok:(code||200)<400,status:code||200,json:()=>Promise.resolve(o)})}
function vue(e){return Object.assign({moteur:"local:"+e.id,cle:e.type==="openai"?"DZL_"+e.id.toUpperCase()+"_API_KEY":"",integre:false},e)}
function fetch(u,o){const m=(o&&o.method)||"GET",b=o&&o.body?JSON.parse(o.body):null;APPELS.push([m,u,b]);
 const R="/api/reglages/serveurs-locaux";
 if(REFUS[m+" "+u])return rep({detail:REFUS[m+" "+u]},400);
 if(u===R&&m==="GET")return rep({serveurs:[PREMIERE].concat(LISTE.map(vue)),prereglages:PRE});
 if(u===R&&m==="POST"){const id=b.nom.toLowerCase().replace(/[^a-z0-9]/g,"");const mods=String(b.modeles||"").split(/[,\n]/).map(s=>s.trim()).filter(Boolean);
  LISTE.push({id,nom:b.nom,type:b.type,url:b.url,modeles:mods,defaut:b.defaut||mods[0]||"",cle_posee:!!b.cle});return rep({serveur:vue(LISTE[LISTE.length-1])})}
 if(u===R+"/lire-modeles")return rep({modeles:b.id==="ollama"?["llama3.2:3b","qwen2.5:14b-instruct"]:["qwen2.5-7b-instruct","llama-3.2-3b"]});
 const mm=u.match(/^\/api\/reglages\/serveurs-locaux\/([a-z0-9]+)(\/tester)?$/);
 if(mm){if(mm[2])return rep({id:mm[1],ok:true,etat:"ok",n:2,defaut_publie:true});
  const e=LISTE.find(f=>f.id===mm[1]);if(!e)return rep({detail:"inconnu"},mm[1]==="ollama"?400:404);
  if(m==="DELETE"){LISTE=LISTE.filter(f=>f!==e);return rep({deleted:e.id})}
  if(b.cle)e.cle_posee=true;if(b.modeles)e.modeles=b.modeles;if(b.defaut)e.defaut=b.defaut;return rep({serveur:vue(e)})}
 return rep({detail:"?"},404)}
async function vider(){for(let i=0;i<8;i++){while(EFF.length)EFF.shift()();await new Promise(z=>setTimeout(z,0))}}
const ENV={r,x,K,jt,te,re,dzT,fetch,console};
(async()=>{try{
 const SRC=tranche("function dzFdJson(","function dzFdPoster(")+tranche("var dzSlVide=","var dzFlVide=")
  +tranche("function dzFlAppel(","function dzFlSaisie(");
 const M=new Function("ENV","with(ENV){"+SRC+";return{DzServeursLocaux}}")(ENV);
 const res={};let SAUVE=0;
 const RL={t:M.DzServeursLocaux,p:{cles:{},onSaved:()=>{SAUVE++}},key:"sl"};
 let V=rendre(RL,"L");const av=a=>tous(V,n=>n.p&&n.p["data-dzsl"]===a)[0];const re_=()=>{V=rendre(RL,"L")};
 // [A]
 res.aCharge=texte(V).includes("reglages.commun.chargement");await vider();re_();
 res.aAppels=APPELS.slice();res.aTitre=texte(V).includes("reglages.locaux.titre")&&texte(V).includes("reglages.locaux.aide");
 const l0=av("ligne-ollama");res.aL0=texte(l0);res.aL0Suppr=!!av("suppr-ollama");res.aL0Lire=!!av("lire-ollama");
 res.aL0Tester=!!av("tester-ollama");res.aL0Cle=!!av("cle-ollama");res.aL0Defaut=texte(av("defaut-ollama"));
 res.aL0Badge=(tous(l0,n=>n.t==="te")[0]||{p:{}}).p.tone;
 res.aOrdre=tous(V,n=>n.p&&/^ligne-/.test(n.p["data-dzsl"]||"")).map(n=>n.p["data-dzsl"]);
 res.aL1=texte(av("ligne-ollama2"));res.aL1Suppr=!!av("suppr-ollama2");res.aL1Cle=!!av("cle-ollama2");
 res.aAjouter=texte(av("ajouter"));res.aForm=!!av("form");
 // [B]
 av("ajouter").p.onClick();re_();res.bForm=!!av("form");res.bAjouterApres=!!av("ajouter");
 const sels=()=>tous(av("form"),n=>n.t==="re");
 res.bPre=sels()[0].p.options.map(o=>o.value);res.bTypes=sels()[1].p.options.map(o=>o.value);
 res.bTypeInit=sels()[1].p.value;res.bCleOllama=!!av("cle");res.bLireVide=av("lire-form").p.disabled;res.bCreerVide=av("creer").p.disabled;
 sels()[0].p.onChange("lmstudio");re_();res.bNom=av("nom").p.value;res.bUrl=av("url").p.value;res.bType=sels()[1].p.value;
 res.bCleType=av("cle")?av("cle").p.type:null;res.bLirePret=av("lire-form").p.disabled;
 av("cle").p.onChange({target:{value:CLE}});re_();
 sels()[1].p.onChange("ollama");re_();res.bCleApresOllama=!!av("cle");
 sels()[1].p.onChange("openai");re_();res.bCleOubliee=av("cle").p.value;
 av("cle").p.onChange({target:{value:CLE}});re_();
 APPELS.length=0;av("lire-form").p.onClick();await vider();re_();
 res.bAppels=APPELS.slice();res.bModeles=av("modeles").p.value;
 res.bDefautSel=sels().length===3?sels()[2].p.value:null;res.bDefautOpts=sels().length===3?sels()[2].p.options.map(o=>o.value):null;
 res.bMsg=texte(av("msg"));
 sels()[2].p.onChange("llama-3.2-3b");re_();
 // [D] refus d'abord
 REFUS["POST /api/reglages/serveurs-locaux"]="URL du serveur : adresse publique refusée ici";
 APPELS.length=0;av("creer").p.onClick();await vider();re_();
 res.dMsg=texte(av("msg"));res.dCouleur=av("msg").p.style.color;res.dForm=!!av("form");res.dCleGardee=av("cle").p.value;
 REFUS={};
 // [C] enregistrer
 APPELS.length=0;av("creer").p.onClick();await vider();re_();
 res.cAppels=APPELS.slice();res.cForm=!!av("form");res.cSauve=SAUVE;res.cMsg=texte(av("msg"));
 const ln=av("ligne-lmstudio");res.cLigne=texte(ln);res.cBadge=(tous(ln,n=>n.t==="te")[0]||{p:{}}).p.tone;
 res.cArbre=JSON.stringify(V).includes(CLE);res.cStore=JSON.stringify(Array.from(STORE.values())).includes(CLE);
 // [E] la première ligne : Tester / Lire (montrés, rien d'écrit)
 APPELS.length=0;av("tester-ollama").p.onClick();await vider();re_();
 res.eTest0=[APPELS.slice(),texte(av("msg-ollama")),av("msg-ollama").p.style.color];
 APPELS.length=0;av("lire-ollama").p.onClick();await vider();re_();res.eLire0=[APPELS.slice(),texte(av("msg-ollama"))];
 // une ligne ajoutée : Lire (enregistrés), défaut, clé
 APPELS.length=0;av("lire-lmstudio").p.onClick();await vider();re_();res.eLire1=[APPELS.slice(),texte(av("msg-lmstudio"))];
 APPELS.length=0;tous(av("defaut-lmstudio"),n=>n.t==="re")[0].p.onChange("qwen2.5-7b-instruct");await vider();re_();
 res.eDefaut=APPELS.slice();
 res.eRempVide=av("remplacer-lmstudio").p.disabled;res.eCleType=av("cle-lmstudio").p.type;
 av("cle-lmstudio").p.onChange({target:{value:"sk-neuve-0000000000"}});re_();res.eRempPlein=av("remplacer-lmstudio").p.disabled;
 APPELS.length=0;av("remplacer-lmstudio").p.onClick();await vider();re_();
 res.eRemp=[APPELS.slice(),av("cle-lmstudio").p.value,texte(av("msg-lmstudio"))];
 res.eAnnuler=(()=>{av("ajouter").p.onClick();re_();const a=!!av("form");av("annuler").p.onClick();re_();return[a,!!av("form")]})();
 // [F] supprimer en deux clics
 APPELS.length=0;av("suppr-ollama2").p.onClick();re_();
 res.f1=[APPELS.slice(),texte(av("suppr-ollama2")),av("suppr-ollama2").p.variant];
 av("suppr-ollama2").p.onClick();await vider();re_();
 res.f2=[APPELS.slice(),!!av("ligne-ollama2"),texte(av("msg")),!!av("ligne-ollama")];
 OUT.res=res;
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));})();
"""

print("[A-F] DzServeursLocaux sous node")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzsl223_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(BUN_P.read_bytes())
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js"), CLE], capture_output=True, text=True, encoding="utf-8",
                    errors="replace")
try:
    OUT = json.loads(rn.stdout or "{}")
except ValueError:
    OUT = {"err": rn.stdout[-300:] + rn.stderr[-300:]}
check("0 composant extrait et rendu", "err" not in OUT, str(OUT.get("err", ""))[:500] + rn.stderr[-200:])
R = OUT.get("res", {})
RT = "/api/reglages/serveurs-locaux"

print("[A] chargement")
check("A1 « chargement » avant la réponse, puis un seul GET de la liste", R.get("aCharge") is True
      and R.get("aAppels") == [["GET", RT, None]], repr(R.get("aAppels")))
l0 = R.get("aL0") or ""
check("A2 première ligne = Ollama intégré : OLLAMA_URL et OLLAMA_MODEL tels quels, moteur ollama, « intégré », gratuit",
      "http://127.0.0.1:11434" in l0 and R.get("aL0Defaut") == "qwen2.5:14b-instruct"
      and "ollama · reglages.locaux.type_ollama" in l0 and "reglages.locaux.integre" in l0 and "son.commun.gratuit" in l0
      and R.get("aL0Badge") == "green", l0[:300])
check("A3 première ligne : Lire les modèles et Tester, PAS de Supprimer ni de champ de clé",
      R.get("aL0Lire") is True and R.get("aL0Tester") is True and R.get("aL0Suppr") is False and R.get("aL0Cle") is False)
check("A4 ordre : la première ligne, puis les serveurs ajoutés", R.get("aOrdre") == ["ligne-ollama", "ligne-ollama2"], R.get("aOrdre"))
check("A5 serveur Ollama ajouté : local:ollama2 · Ollama natif, « 1 modèles · gratuit », Supprimer, pas de clé",
      "local:ollama2 · reglages.locaux.type_ollama" in (R.get("aL1") or "") and 'reglages.libres.n_modeles{"n":1} · son.commun.gratuit'
      in (R.get("aL1") or "") and R.get("aL1Suppr") is True and R.get("aL1Cle") is False, (R.get("aL1") or "")[:300])
check("A6 titre, aide, « + Ajouter un serveur », pas de formulaire", R.get("aTitre") is True
      and R.get("aAjouter") == "reglages.locaux.ajouter" and R.get("aForm") is False)

print("[B] formulaire")
check("B1 « Ajouter » ouvre le formulaire (et se retire)", R.get("bForm") is True and R.get("bAjouterApres") is False)
check("B2 préréglages « Autre » puis ceux du serveur ; types Ollama natif / compatible OpenAI, Ollama d'abord",
      R.get("bPre") == ["", "ollama", "lmstudio"] and R.get("bTypes") == ["ollama", "openai"] and R.get("bTypeInit") == "ollama",
      repr((R.get("bPre"), R.get("bTypes"))))
check("B3 à vide : pas de champ de clé (Ollama), Lire et Enregistrer grisés", R.get("bCleOllama") is False
      and R.get("bLireVide") is True and R.get("bCreerVide") is True)
check("B4 préréglage LM Studio → nom, URL, type compatible OpenAI ; clé en password ; Lire actif",
      R.get("bNom") == "LM Studio" and R.get("bUrl") == "http://127.0.0.1:1234/v1" and R.get("bType") == "openai"
      and R.get("bCleType") == "password" and R.get("bLirePret") is False, repr((R.get("bNom"), R.get("bUrl"), R.get("bType"))))
check("B5 repasser en Ollama retire le champ de clé et OUBLIE la clé saisie", R.get("bCleApresOllama") is False
      and R.get("bCleOubliee") == "")
check("B6 « Lire les modèles » : POST lire-modeles {url, type, cle} (le serveur lit, pas le navigateur)",
      R.get("bAppels") == [["POST", RT + "/lire-modeles", {"url": "http://127.0.0.1:1234/v1", "type": "openai", "cle": CLE}]],
      repr(R.get("bAppels")))
check("B7 modèles remplis, défaut = le premier, choisi parmi la liste lue, « n modèles lus »",
      R.get("bModeles") == "qwen2.5-7b-instruct, llama-3.2-3b" and R.get("bDefautSel") == "qwen2.5-7b-instruct"
      and R.get("bDefautOpts") == ["qwen2.5-7b-instruct", "llama-3.2-3b"] and R.get("bMsg") == 'reglages.locaux.n_lus{"n":2}',
      repr((R.get("bModeles"), R.get("bDefautSel"), R.get("bMsg"))))

print("[D] refus")
check("D1 refus du serveur : son message, en rouge ; formulaire ouvert, clé gardée",
      R.get("dMsg") == "URL du serveur : adresse publique refusée ici" and R.get("dCouleur") == "var(--red)"
      and R.get("dForm") is True and R.get("dCleGardee") == CLE, repr((R.get("dMsg"), R.get("dForm"))))

print("[C] enregistrer")
check("C1 POST {nom, url, type, cle, modeles, defaut} puis relecture",
      (R.get("cAppels") or [None])[0] == ["POST", RT, {"nom": "LM Studio", "url": "http://127.0.0.1:1234/v1", "type": "openai",
                                                       "cle": CLE, "modeles": "qwen2.5-7b-instruct, llama-3.2-3b",
                                                       "defaut": "llama-3.2-3b"}]
      and ["GET", RT, None] in (R.get("cAppels") or []), repr(R.get("cAppels")))
check("C2 formulaire fermé, Clés d'API prévenue (onSaved), « Enregistré »", R.get("cForm") is False and R.get("cSauve") == 1
      and R.get("cMsg") == "commun.etat.enregistre")
lg = R.get("cLigne") or ""
check("C3 la ligne : nom, URL, local:lmstudio · compatible OpenAI · clé posée, « 2 modèles · gratuit », prêt",
      "LM Studio" in lg and "http://127.0.0.1:1234/v1" in lg
      and "local:lmstudio · reglages.locaux.type_openai · reglages.cles.posee" in lg
      and 'reglages.libres.n_modeles{"n":2} · son.commun.gratuit' in lg and R.get("cBadge") == "green", lg[:300])
check("C4 après enregistrement, la clé n'est NULLE PART (écran, état)", R.get("cArbre") is False and R.get("cStore") is False)

print("[E] par ligne")
t = R.get("eTest0") or [[], "", ""]
check("E1 Tester la première ligne : POST …/ollama/tester (rien d'autre), « Serveur joignable : 2 modèles » en vert",
      t[0] == [["POST", RT + "/ollama/tester", {}]] and t[1] == 'reglages.locaux.test_ok{"n":2}' and t[2] == "var(--green)", repr(t))
li = R.get("eLire0") or [[], ""]
check("E2 Lire les modèles de la première ligne : un POST lire-modeles {id: ollama}, liste MONTRÉE, rien d'écrit",
      li[0] == [["POST", RT + "/lire-modeles", {"id": "ollama"}]]
      and li[1] == 'reglages.locaux.n_lus{"n":2} : llama3.2:3b, qwen2.5:14b-instruct', repr(li))
li = R.get("eLire1") or [[], ""]
check("E3 Lire les modèles d'un serveur ajouté : lire puis POST …/lmstudio {modeles}, « n modèles lus »",
      li[0][:2] == [["POST", RT + "/lire-modeles", {"id": "lmstudio"}],
                    ["POST", RT + "/lmstudio", {"modeles": ["qwen2.5-7b-instruct", "llama-3.2-3b"]}]]
      and li[1] == 'reglages.locaux.n_lus{"n":2}', repr(li))
check("E4 changer le défaut : POST …/lmstudio {defaut}", (R.get("eDefaut") or [None])[0]
      == ["POST", RT + "/lmstudio", {"defaut": "qwen2.5-7b-instruct"}], repr(R.get("eDefaut")))
check("E5 Remplacer la clé (OpenAI) : grisé à vide, actif rempli, password", R.get("eRempVide") is True
      and R.get("eRempPlein") is False and R.get("eCleType") == "password")
e = R.get("eRemp") or [[], "x", ""]
check("E6 Remplacer : POST {cle}, champ vidé, « Enregistré »", e[0][:1] == [["POST", RT + "/lmstudio", {"cle": "sk-neuve-0000000000"}]]
      and e[1] == "" and e[2] == "commun.etat.enregistre", repr(e))
check("E7 Annuler ferme le formulaire", R.get("eAnnuler") == [True, False], R.get("eAnnuler"))

print("[F] supprimer en deux clics")
f1 = R.get("f1") or [[1], "", ""]
check("F1 premier clic : AUCUN appel, « Confirmer la suppression » (rouge)",
      f1[0] == [] and f1[1] == "espaces.comptes.confirmer" and f1[2] == "danger", repr(f1))
f2 = R.get("f2") or [[], True, "", False]
check("F2 second clic : DELETE …/ollama2, relecture, ligne partie, « Serveur supprimé », la première ligne reste",
      (f2[0] or [None])[0] == ["DELETE", RT + "/ollama2", None] and f2[1] is False and f2[2] == "reglages.locaux.supprime"
      and f2[3] is True, repr(f2))

print("[G] sites")
import patch_bundle_dzreglages as DR                                  # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
try:
    avant = DR.defaire(BUNDLE)
    rejoue = DR.appliquer(avant)
except (AssertionError, SystemExit) as e:
    avant = rejoue = str(e)
check("G1 la liste se pose juste APRÈS « LLM local » (wm), relue avec les clés (cles:g)",
      BUNDLE.count("r.jsx(wm,{serverKeys:g,onSaved:()=>{m(),No()}}),r.jsx(DzServeursLocaux,{cles:g,onSaved:()=>{m(),No()}})") == 1
      and BUNDLE.count("r.jsx(DzFournLibres,{onSaved:()=>{m(),No()}}),r.jsx(wm,") == 1)
src = BUNDLE[BUNDLE.find("var dzSlVide="):BUNDLE.find("var dzFlVide=")]
check("G2 composant ×1, posé devant les fournisseurs libres (hors des tranches du banc t222)",
      BUNDLE.count("function DzServeursLocaux(") == 1 and src.count("function DzServeursLocaux(") == 1
      and BUNDLE.find("var dzSlVide=") < BUNDLE.find("var dzFlVide="))
_wm = lambda s: s[s.find("function wm("):s.find("function Sm(){")]
check("G3 `wm` (OLLAMA_URL / OLLAMA_MODEL, ses 4 useState) est resté intact à l'octet", _wm(BUNDLE) == _wm(avant)
      and _wm(BUNDLE).count("x.useState(") == 4 and 'name:"OLLAMA_URL"' in _wm(BUNDLE))
check("G4 champs de clé en password (ligne + formulaire) ; aucun listKeys ni preview", src.count('"password")') == 2
      and "listKeys" not in src and "preview" not in src)
check("G5 une seule racine d'API : /api/reglages/serveurs-locaux", set(re.findall(r'"(/api/[^"]+)"', src))
      == {"/api/reglages/serveurs-locaux"}, re.findall(r'"(/api/[^"]+)"', src))

print("[H] i18n")
cat = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
NEUVES = sorted(k for k in cat if k.startswith("reglages.locaux."))
manq = [k for k in NEUVES if not cat[k].get("fr") or not cat[k].get("en") or f'dzT("{k}"' not in BUNDLE]
check(f"H1 les {len(NEUVES)} clés reglages.locaux.* : FR + EN, toutes employées", len(NEUVES) == 15 and not manq, repr(manq))
utilisees = set(re.findall(r'dzT\("(reglages\.locaux\.[a-z_]+)"', src))
check("H1b aucune clé employée absente du catalogue", utilisees <= set(NEUVES), sorted(utilisees - set(NEUVES)))
frs, ou, tout = {}, {}, {}
for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        continue
    tout.update(doc)
    for kk, e in doc.items():
        if isinstance(e, dict) and "fr" in e and "en" in e:
            frs.setdefault(e["fr"], []).append(kk)
            ou.setdefault(kk, []).append(f.name)
check("H2 une phrase FR = une traduction : aucune phrase FR neuve n'existe sous une autre clé",
      all(frs.get(cat[k]["fr"]) == [k] for k in NEUVES), {k: frs.get(cat[k]["fr"]) for k in NEUVES if frs.get(cat[k]["fr"]) != [k]})
check("H3 aucune clé neuve en double dans un autre catalogue", all(ou.get(k) == ["menus.json"] for k in NEUVES))
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("H4 catalogue assemblé à jour", ra.returncode == 0, (ra.stdout + ra.stderr)[-300:])
reemployees = set(re.findall(r'dzT\("([a-z0-9_.]+)"', src)) - set(NEUVES)
check(f"H5 les {len(reemployees)} clés réemployées existent (URL du serveur, Nom, Type, gratuit, prêt, Supprimer…)",
      reemployees and all(k in tout for k in reemployees), sorted(k for k in reemployees if k not in tout))

print("[I] maillon dzreglages")
check("I1 aller-retour à l'octet", rejoue == BUNDLE and DR.MARKER not in avant)
check("I2 l'avant a le défaut d'origine (aucune liste de serveurs, wm seul)", "DzServeursLocaux" not in avant
      and "dzSlVide" not in avant and "r.jsx(wm,{serverKeys:g,onSaved:()=>{m(),No()}})" in avant)
check("I3 avant_dzreglages = défaire", AIDE.avant_dzreglages(BUNDLE) == avant)
try:
    _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
except (OSError, ValueError, KeyError):
    _g1 = []
check("I4 aucune paire ne chevauche ni ne recopie un remplacement G1 (dzglyph)",
      bool(_g1) and all(BUNDLE.count(x) == avant.count(x) for x in _g1))
check("I5 comptes figés intacts (aucun useState ajouté)", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181 and "useState" not in src)
b = BUN_P.read_bytes()
check("I6 CRLF intactes", b.count(b"\r\n") > 15000 and b.count(b"\n") == b.count(b"\r\n"))
check("I7 aucun .bak_dzreglages", not (BUN_P.parent / (BUN_P.name + ".bak_dzreglages")).exists())
check("I8 aucune clé dzT construite (test_i18n_l1 3b)", not re.search(r'dzT\("[a-z_.]+"\+', src))
check("I9 aucun dzT local (règle t212)", not re.search(r"\bdzT\s*=", src))
check("I10 le style compté par test_p2_cles_ecran 2.2 reste ×1",
      BUNDLE.count('style:{width:"100%",minWidth:0,boxSizing:"border-box",background:"var(--bg-base)",') == 1)
check("I11 21 paires (… L0-L1, S0-S1) ; S0-S1 en dernier", len(DR.PAIRES) == 21
      and DR.PAIRES[19][0] == DR.FL_VIDE and DR.PAIRES[20][0] == DR.WM_APPEL, len(DR.PAIRES))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
