# -*- coding: utf-8 -*-
"""t222 (Menus : Réglages, 16/10/2026) — l'ÉCRAN : Clés d'API › « Fournisseurs libres (compatibles OpenAI) » (banc
serveur à part : test_reglages_fournisseurs_libres.py).

Défaut relevé sur 1ad154a5 : Clés d'API n'avait qu'un encart « LLM local » ; aucun moyen d'ajouter DeepSeek,
OpenRouter, Mistral, Groq… ni de voir leurs modèles dans l'application.

Ce que ce banc garde (DzFournLibres du maillon dzreglages rendu sous node, hooks simulés À ÉTAT, faux serveur) :
  [A] chargement : GET /api/reglages/fournisseurs-libres ; liste vide dite ; « + Ajouter un fournisseur » ;
  [B] le formulaire : préréglage → nom + URL ; « Lire la liste » grisé sans URL ou sans clé, puis POST lire-modeles
      {base, cle} → modèles (saisie libre) remplis, défaut = le premier, choix parmi la liste lue ;
  [C] Enregistrer : POST {nom, base, cle, modeles, defaut} ; le formulaire se ferme et OUBLIE la clé ; relecture ;
      la ligne dit nom, base, moteur fl:<id>, nom de la clé, « posée », « prix à mesurer » — jamais la clé ;
  [D] refus du serveur : son message en rouge, formulaire gardé ouvert (rien perdu) ;
  [E] par ligne : Tester (ok / sans_cle), Lire la liste (lire puis enregistrer), défaut changé, Remplacer la clé
      (grisé à vide, champ vidé après succès seulement) ;
  [F] Supprimer en DEUX clics : le premier arme (« Confirmer la suppression », rouge), le second DELETE ;
  [G] sites : l'encart se pose juste avant « LLM local » de Clés d'API ; champs de clé en `password` ;
  [H] i18n : clés FR/EN dans menus.json, une phrase FR = une traduction, catalogue assemblé, clés réemployées ;
  [I] maillon dzreglages : aller-retour à l'octet, défaut d'origine dans l'avant, aucun chevauchement G1, comptes
      figés (aucun useState), CRLF, aucun .bak, aucune clé dzT construite, aucun dzT local, style compté intact.
Run (depuis backend/) : & $PY tests/test_reglages_fournisseurs_libres_ecran.py"""
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
CLE = "sk-faussecle-ecran-t222-000000"

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
// le faux serveur : l'état des fournisseurs, jamais une clé en sortie
const APPELS=[];let LISTE=[];let REFUS={};
const PRE=[{id:"deepseek",nom:"DeepSeek",base:"https://api.deepseek.com/v1"},{id:"groq",nom:"Groq",base:"https://api.groq.com/openai/v1"}];
function rep(o,code){return Promise.resolve({ok:(code||200)<400,status:code||200,json:()=>Promise.resolve(o)})}
function vue(e){return Object.assign({moteur:"fl:"+e.id,cle:"DZF_"+e.id.toUpperCase()+"_API_KEY"},e)}
function fetch(u,o){const m=(o&&o.method)||"GET",b=o&&o.body?JSON.parse(o.body):null;APPELS.push([m,u,b]);
 const R="/api/reglages/fournisseurs-libres";
 if(REFUS[m+" "+u])return rep({detail:REFUS[m+" "+u]},400);
 if(u===R&&m==="GET")return rep({fournisseurs:LISTE.map(vue),prereglages:PRE});
 if(u===R&&m==="POST"){const id=b.nom.toLowerCase().replace(/[^a-z0-9]/g,"");const mods=String(b.modeles||"").split(/[,\n]/).map(s=>s.trim()).filter(Boolean);
  LISTE.push({id,nom:b.nom,base:b.base,modeles:mods,defaut:b.defaut||mods[0]||"",cle_posee:!!b.cle});return rep({fournisseur:vue(LISTE[LISTE.length-1])})}
 if(u===R+"/lire-modeles")return rep({modeles:["deepseek-chat","deepseek-reasoner"]});
 const mm=u.match(/^\/api\/reglages\/fournisseurs-libres\/([a-z0-9]+)(\/tester)?$/);
 if(mm){const e=LISTE.find(f=>f.id===mm[1]);if(!e)return rep({detail:"inconnu"},404);
  if(mm[2])return rep(e.cle_posee?{id:e.id,ok:true,etat:"ok",n:2}:{id:e.id,ok:false,etat:"sans_cle",n:0});
  if(m==="DELETE"){LISTE=LISTE.filter(f=>f!==e);return rep({deleted:e.id})}
  if(b.cle)e.cle_posee=true;if(b.modeles)e.modeles=b.modeles;if(b.defaut)e.defaut=b.defaut;return rep({fournisseur:vue(e)})}
 return rep({detail:"?"},404)}
async function vider(){for(let i=0;i<8;i++){while(EFF.length)EFF.shift()();await new Promise(z=>setTimeout(z,0))}}
const ENV={r,x,K,jt,te,re,dzT,fetch,console};
(async()=>{try{
 const SRC=tranche("function dzFdJson(","function dzFdPoster(")+tranche("var dzFlVide=","function wm(");
 const M=new Function("ENV","with(ENV){"+SRC+";return{DzFournLibres}}")(ENV);
 const res={};let SAUVE=0;
 const RL={t:M.DzFournLibres,p:{onSaved:()=>{SAUVE++}},key:"fl"};
 let V=rendre(RL,"L");const av=a=>tous(V,n=>n.p&&n.p["data-dzfl"]===a)[0];const re_=()=>{V=rendre(RL,"L")};
 // [A]
 res.aCharge=texte(V).includes("reglages.commun.chargement");await vider();re_();
 res.aAppels=APPELS.slice();res.aVide=!!av("vide");res.aAjouter=texte(av("ajouter"));res.aForm=!!av("form");
 res.aTitre=texte(V).includes("reglages.libres.titre")&&texte(V).includes("reglages.libres.aide");
 // [B]
 av("ajouter").p.onClick();re_();res.bForm=!!av("form");res.bAjouterApres=!!av("ajouter");
 const sel=tous(av("form"),n=>n.t==="re")[0];res.bPre=sel.p.options.map(o=>o.value);
 sel.p.onChange("deepseek");re_();res.bNom=av("nom").p.value;res.bBase=av("base").p.value;
 res.bLireSansCle=av("lire-form").p.disabled;res.bCleType=av("cle").p.type;res.bCreerPret=av("creer").p.disabled;
 av("cle").p.onChange({target:{value:CLE}});re_();res.bLireAvecCle=av("lire-form").p.disabled;
 APPELS.length=0;av("lire-form").p.onClick();await vider();re_();
 res.bAppels=APPELS.slice();res.bModeles=av("modeles").p.value;
 const selD=tous(av("form"),n=>n.t==="re");res.bDefautSel=selD.length===2?selD[1].p.value:null;
 res.bDefautOpts=selD.length===2?selD[1].p.options.map(o=>o.value):null;res.bMsg=texte(av("msg"));
 selD[1].p.onChange("deepseek-reasoner");re_();
 av("modeles").p.onChange({target:{value:"deepseek-chat, deepseek-reasoner, mon-modele"}});re_();
 // [D] refus d'abord
 REFUS["POST /api/reglages/fournisseurs-libres"]="URL de base : https:// obligatoire";
 APPELS.length=0;av("creer").p.onClick();await vider();re_();
 res.dMsg=texte(av("msg"));res.dCouleur=av("msg").p.style.color;res.dForm=!!av("form");res.dCleGardee=av("cle").p.value;
 REFUS={};
 // [C] enregistrer
 APPELS.length=0;av("creer").p.onClick();await vider();re_();
 res.cAppels=APPELS.slice();res.cForm=!!av("form");res.cSauve=SAUVE;
 const ln=av("ligne-deepseek");res.cLigne=texte(ln);res.cBadge=(tous(ln,n=>n.t==="te")[0]||{p:{}}).p.tone;
 res.cArbre=JSON.stringify(V).includes(CLE);res.cStore=JSON.stringify(Array.from(STORE.values())).includes(CLE);
 res.cMsg=texte(av("msg"));
 // [E] tester / lire / défaut / remplacer
 APPELS.length=0;av("tester-deepseek").p.onClick();await vider();re_();
 res.eTest=[APPELS.slice(),texte(av("msg-deepseek")),av("msg-deepseek").p.style.color];
 APPELS.length=0;av("lire-deepseek").p.onClick();await vider();re_();res.eLire=[APPELS.slice(),texte(av("msg-deepseek"))];
 APPELS.length=0;tous(av("defaut-deepseek"),n=>n.t==="re")[0].p.onChange("deepseek-chat");await vider();re_();res.eDefaut=APPELS.slice();
 res.eRempVide=av("remplacer-deepseek").p.disabled;res.eCleType=av("cle-deepseek").p.type;
 REFUS["POST /api/reglages/fournisseurs-libres/deepseek"]="Coffre verrouillé : le coffre est fermé";
 av("cle-deepseek").p.onChange({target:{value:"sk-neuve-0000000000"}});re_();res.eRempPlein=av("remplacer-deepseek").p.disabled;
 APPELS.length=0;av("remplacer-deepseek").p.onClick();await vider();re_();
 res.eRempErr=[APPELS.slice(),texte(av("msg-deepseek")),av("msg-deepseek").p.style.color,av("cle-deepseek").p.value];
 REFUS={};APPELS.length=0;av("remplacer-deepseek").p.onClick();await vider();re_();
 res.eRempOk=[APPELS.slice(),av("cle-deepseek").p.value,texte(av("msg-deepseek"))];
 // sans clé : Tester dit « clé manquante », Lire la liste grisé
 LISTE.push({id:"groq",nom:"Groq",base:"https://api.groq.com/openai/v1",modeles:[],defaut:"",cle_posee:false});
 av("ajouter").p.onClick();re_();av("annuler")||0;
 const ann=tous(av("form"),n=>n.t==="K"&&texte(n)==="commun.action.annuler")[0];ann.p.onClick();re_();
 STORE.forEach((v,k)=>{});res.ePresqueForm=!!av("form");
 // relecture forcée : un clic Tester sur deepseek relit pas la liste ; on remonte le composant
 STORE.clear();re_();await vider();re_();
 APPELS.length=0;av("tester-groq").p.onClick();await vider();re_();
 res.eSansCle=[texte(av("msg-groq")),av("lire-groq").p.disabled,(tous(av("ligne-groq"),n=>n.t==="te")[0]||{p:{}}).p.tone];
 // [F] supprimer en deux clics
 APPELS.length=0;av("suppr-deepseek").p.onClick();re_();
 res.f1=[APPELS.slice(),texte(av("suppr-deepseek")),av("suppr-deepseek").p.variant];
 av("suppr-deepseek").p.onClick();await vider();re_();
 res.f2=[APPELS.slice(),!!av("ligne-deepseek"),texte(av("msg"))];
 OUT.res=res;
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));})();
"""

print("[A-F] DzFournLibres sous node")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzfl222_"))
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
RT = "/api/reglages/fournisseurs-libres"

print("[A] chargement")
check("A1 « chargement » avant la réponse, puis un seul GET de la liste", R.get("aCharge") is True
      and R.get("aAppels") == [["GET", RT, None]], repr(R.get("aAppels")))
check("A2 liste vide dite, « + Ajouter un fournisseur », pas de formulaire, titre et aide",
      R.get("aVide") is True and R.get("aAjouter") == "reglages.libres.ajouter" and R.get("aForm") is False
      and R.get("aTitre") is True)

print("[B] formulaire")
check("B1 « Ajouter » ouvre le formulaire (et se retire)", R.get("bForm") is True and R.get("bAjouterApres") is False)
check("B2 préréglages : « Autre » puis ceux du serveur", R.get("bPre") == ["", "deepseek", "groq"], repr(R.get("bPre")))
check("B3 préréglage DeepSeek → nom et URL de base remplis", R.get("bNom") == "DeepSeek"
      and R.get("bBase") == "https://api.deepseek.com/v1", repr((R.get("bNom"), R.get("bBase"))))
check("B4 « Lire la liste » grisé sans clé, actif avec ; la clé se saisit en password ; Enregistrer actif (nom + URL)",
      R.get("bLireSansCle") is True and R.get("bLireAvecCle") is False and R.get("bCleType") == "password"
      and R.get("bCreerPret") is False)
check("B5 « Lire la liste » : POST lire-modeles {base, cle} (le serveur lit, pas le navigateur)",
      R.get("bAppels") == [["POST", RT + "/lire-modeles", {"base": "https://api.deepseek.com/v1", "cle": CLE}]], repr(R.get("bAppels")))
check("B6 modèles remplis (saisie libre), défaut = le premier, choisi parmi la liste lue ; « n modèles lus »",
      R.get("bModeles") == "deepseek-chat, deepseek-reasoner" and R.get("bDefautSel") == "deepseek-chat"
      and R.get("bDefautOpts") == ["deepseek-chat", "deepseek-reasoner"]
      and R.get("bMsg") == 'reglages.libres.n_lus{"n":2}', repr((R.get("bModeles"), R.get("bDefautSel"), R.get("bMsg"))))

print("[D] refus")
check("D1 refus du serveur : son message, en rouge ; formulaire ouvert, clé gardée pour corriger",
      R.get("dMsg") == "URL de base : https:// obligatoire" and R.get("dCouleur") == "var(--red)" and R.get("dForm") is True
      and R.get("dCleGardee") == CLE, repr((R.get("dMsg"), R.get("dForm"))))

print("[C] enregistrer")
check("C1 POST {nom, base, cle, modeles (texte brut), defaut} puis relecture",
      (R.get("cAppels") or [None])[0] == ["POST", RT, {"nom": "DeepSeek", "base": "https://api.deepseek.com/v1", "cle": CLE,
                                                       "modeles": "deepseek-chat, deepseek-reasoner, mon-modele",
                                                       "defaut": "deepseek-reasoner"}]
      and ["GET", RT, None] in (R.get("cAppels") or []), repr(R.get("cAppels")))
check("C2 formulaire fermé, Clés d'API prévenue (onSaved), « Enregistré »", R.get("cForm") is False and R.get("cSauve") == 1
      and R.get("cMsg") == "commun.etat.enregistre")
lg = R.get("cLigne") or ""
check("C3 la ligne : nom, base, moteur fl:deepseek, nom de la clé, « posée », n modèles, « prix à mesurer »",
      "DeepSeek" in lg and "https://api.deepseek.com/v1" in lg and "fl:deepseek · DZF_DEEPSEEK_API_KEY" in lg
      and "reglages.cles.posee" in lg and 'reglages.libres.n_modeles{"n":3}' in lg and "ia.prix.a_mesurer" in lg
      and R.get("cBadge") == "green", lg[:300])
check("C4 après enregistrement, la clé n'est NULLE PART : ni dans l'écran, ni dans l'état du composant",
      R.get("cArbre") is False and R.get("cStore") is False)

print("[E] par ligne")
t = R.get("eTest") or [[], "", ""]
check("E1 Tester : POST …/deepseek/tester (rien d'autre), « Clé acceptée : 2 modèles » en vert",
      t[0] == [["POST", RT + "/deepseek/tester", {}]] and t[1] == 'reglages.libres.test_ok{"n":2}' and t[2] == "var(--green)", repr(t))
li = R.get("eLire") or [[], ""]
check("E2 Lire la liste : POST lire-modeles {id} puis POST …/deepseek {modeles}, relecture, « n modèles lus »",
      li[0][:2] == [["POST", RT + "/lire-modeles", {"id": "deepseek"}],
                    ["POST", RT + "/deepseek", {"modeles": ["deepseek-chat", "deepseek-reasoner"]}]]
      and li[1] == 'reglages.libres.n_lus{"n":2}', repr(li))
check("E3 changer le défaut : POST …/deepseek {defaut}", (R.get("eDefaut") or [None])[0] == ["POST", RT + "/deepseek",
                                                                                          {"defaut": "deepseek-chat"}], repr(R.get("eDefaut")))
check("E4 Remplacer la clé : grisé à vide, actif rempli, champ password", R.get("eRempVide") is True
      and R.get("eRempPlein") is False and R.get("eCleType") == "password")
e = R.get("eRempErr") or [[], "", "", ""]
check("E5 refus (coffre fermé) : message rouge, la saisie reste", e[0] == [["POST", RT + "/deepseek", {"cle": "sk-neuve-0000000000"}]]
      and e[1].startswith("Coffre verrouillé") and e[2] == "var(--red)" and e[3] == "sk-neuve-0000000000", repr(e))
e = R.get("eRempOk") or [[], "x", ""]
check("E6 succès : champ vidé, « Enregistré »", e[0][:1] == [["POST", RT + "/deepseek", {"cle": "sk-neuve-0000000000"}]]
      and e[1] == "" and e[2] == "commun.etat.enregistre", repr(e))
check("E7 Annuler ferme le formulaire", R.get("ePresqueForm") is False)
e = R.get("eSansCle") or ["", None, ""]
check("E8 fournisseur sans clé : Tester dit « clé manquante », Lire la liste grisé, badge rouge",
      e[0] == "reglages.libres.sans_cle" and e[1] is True and e[2] == "red", repr(e))

print("[F] supprimer en deux clics")
f1 = R.get("f1") or [[1], "", ""]
check("F1 premier clic : AUCUN appel, le bouton devient « Confirmer la suppression » (rouge)",
      f1[0] == [] and f1[1] == "espaces.comptes.confirmer" and f1[2] == "danger", repr(f1))
f2 = R.get("f2") or [[], True, ""]
check("F2 second clic : DELETE …/deepseek, relecture, ligne partie, « Fournisseur supprimé »",
      (f2[0] or [None])[0] == ["DELETE", RT + "/deepseek", None] and f2[1] is False and f2[2] == "reglages.libres.supprime", repr(f2))

print("[G] sites")
check("G1 l'encart se pose dans Clés d'API juste avant « LLM local » (wm), relecture des clés et de la santé",
      BUNDLE.count("r.jsx(DzFournLibres,{onSaved:()=>{m(),No()}}),r.jsx(wm,{serverKeys:g,onSaved:()=>{m(),No()}})") == 1)
src = BUNDLE[BUNDLE.find("var dzFlVide="):BUNDLE.find("function wm(")]
check("G2 composant ×1, posé devant wm", BUNDLE.count("function DzFournLibres(") == 1 and src.count("function DzFournLibres(") == 1)
check("G3 les champs de clé sont en password ; aucun listKeys ni lecture de clé", src.count('"password")') == 2
      and "listKeys" not in src and "preview" not in src)
check("G4 toutes les écritures passent par /api/reglages/fournisseurs-libres", set(re.findall(r'"(/api/[^"]+)"', src))
      == {"/api/reglages/fournisseurs-libres"}, re.findall(r'"(/api/[^"]+)"', src))

print("[H] i18n")
cat = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
NEUVES = sorted(k for k in cat if k.startswith("reglages.libres."))
manq = [k for k in NEUVES if not cat[k].get("fr") or not cat[k].get("en") or f'dzT("{k}"' not in BUNDLE]
check(f"H1 les {len(NEUVES)} clés reglages.libres.* : FR + EN, toutes employées", len(NEUVES) == 17 and not manq, repr(manq))
utilisees = set(re.findall(r'dzT\("(reglages\.libres\.[a-z_]+)"', src))
check("H1b aucune clé employée absente du catalogue", utilisees <= set(NEUVES), sorted(utilisees - set(NEUVES)))
fr_en, ou = {}, {}
for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    try:
        for k, e in json.loads(f.read_text(encoding="utf-8")).items():
            if isinstance(e, dict) and "fr" in e and "en" in e:
                fr_en.setdefault(e["fr"], set()).add(e["en"])
                ou.setdefault(k, []).append(f.name)
    except ValueError:
        pass
check("H2 une phrase FR = une traduction", all(len(fr_en.get(cat[k]["fr"], set())) == 1 for k in NEUVES))
frs = {}
for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    for kk, e in json.loads(f.read_text(encoding="utf-8")).items():
        if isinstance(e, dict) and "fr" in e:
            frs.setdefault(e["fr"], []).append(kk)
check("H2b aucune phrase FR neuve n'existe déjà sous une autre clé", all(frs.get(cat[k]["fr"]) == [k] for k in NEUVES),
      {k: frs.get(cat[k]["fr"]) for k in NEUVES if frs.get(cat[k]["fr"]) != [k]})
check("H3 aucune clé neuve en double dans un autre catalogue", all(ou.get(k) == ["menus.json"] for k in NEUVES))
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("H4 catalogue assemblé à jour", ra.returncode == 0, (ra.stdout + ra.stderr)[-300:])
reemployees = set(re.findall(r'dzT\("([a-z0-9_.]+)"', src)) - set(NEUVES)
tout = {}
for f in (RACINE / "frontend" / "shared" / "i18n").glob("*.json"):
    tout.update(json.loads(f.read_text(encoding="utf-8")))
check(f"H5 les {len(reemployees)} clés réemployées existent (Supprimer, Annuler, Confirmer la suppression, posée…)",
      reemployees and all(k in tout for k in reemployees), sorted(k for k in reemployees if k not in tout))

print("[I] maillon dzreglages")
import patch_bundle_dzreglages as DR                                  # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
try:
    avant = DR.defaire(BUNDLE)
    rejoue = DR.appliquer(avant)
except (AssertionError, SystemExit) as e:
    avant = rejoue = str(e)
check("I1 aller-retour à l'octet", rejoue == BUNDLE and DR.MARKER not in avant)
check("I2 l'avant a le défaut d'origine (aucun encart de fournisseurs libres)", "DzFournLibres" not in avant
      and "dzFlVide" not in avant and "r.jsx(wm,{serverKeys:g,onSaved:()=>{m(),No()}})" in avant)
check("I3 avant_dzreglages = défaire", AIDE.avant_dzreglages(BUNDLE) == AIDE.avant_dzlogo(avant))  # dzlogo, posé après, défait d'abord
try:
    _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
except (OSError, ValueError, KeyError):
    _g1 = []
check("I4 aucune paire ne chevauche ni ne recopie un remplacement G1 (dzglyph)",
      bool(_g1) and all(BUNDLE.count(x) == avant.count(x) for x in _g1))
check("I5 comptes figés intacts (aucun useState ajouté)", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181 and "useState" not in src)
b = BUN_P.read_bytes()
check("I6 CRLF intactes, aucune fin de ligne injectée", b.count(b"\r\n") > 15000 and b.count(b"\n") == b.count(b"\r\n"))
check("I7 aucun .bak_dzreglages", not (BUN_P.parent / (BUN_P.name + ".bak_dzreglages")).exists())
check("I8 aucune clé dzT construite (test_i18n_l1 3b)", not re.search(r'dzT\("[a-z_.]+"\+', src))
check("I9 aucun dzT local (règle t212)", not re.search(r"\bdzT\s*=", src))
check("I10 le style compté par test_p2_cles_ecran 2.2 reste ×1",
      BUNDLE.count('style:{width:"100%",minWidth:0,boxSizing:"border-box",background:"var(--bg-base)",') == 1)
check("I11 les paires de t222 (L0-L1) sont les 18e et 19e (t223 ajoute S0-S1 après elles)",
      len(DR.PAIRES) >= 19 and DR.PAIRES[17][0] == DR.WM and DR.PAIRES[18][0] == DR.WM_APPEL, len(DR.PAIRES))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
