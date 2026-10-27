# -*- coding: utf-8 -*-
"""t220 (Menus : Réglages, 16/10/2026) — l'ÉCRAN de Réglages › Fournisseurs par défaut (banc serveur à part :
test_reglages_fournisseurs.py).

Défaut relevé sur 7a104ba2 : les rôles proposaient des NOMS DE CLÉS (FAL_KEY, ANTHROPIC_API_KEY…) et le choix restait
dans le localStorage (« Enregistré localement ») ; aucun écran ne réglait ANTHROPIC_MODEL / OPENAI_MODEL ; GEMINI_MODEL
était un champ de clé de Clés d'API.

Ce que ce banc garde (composants du maillon dzreglages rendus sous node, hooks simulés À ÉTAT, faux serveur) :
  [A] lignes Image → vidéo / Avatar / Voix off en LECTURE SEULE : la clé servie et son état, aucun choix ;
  [B] rôles Résumé News / Planificateur : un MOTEUR (liste du serveur, "" = automatique), POST puis relecture ;
      un choix enregistré mais indisponible reste visible et nommé ;
  [C] une ligne de modèle par moteur configuré (ou fautif) : liste du fournisseur + saisie libre liées, Tester (sans
      dépense), Enregistrer ; un modèle fautif n'est JAMAIS montré (champ vide, bord rouge, alerte) et se corrige
      d'un clic ;
  [D] Em : plus de lignes de rôle locales, l'aide ne dit plus « Enregistré localement » ; Diagnostic : l'alerte à
      la place de l'aperçu ; Clés d'API : « Gemini — modèle » renvoie vers Fournisseurs par défaut ;
  [E] i18n : clés reglages.fournisseurs.* FR/EN dans menus.json, une phrase FR = une traduction, catalogue à jour ;
  [F] maillon dzreglages : aller-retour à l'octet, défaut d'origine dans l'avant, aucun chevauchement G1, comptes
      figés, CRLF, aucun .bak.
Run (depuis backend/) : & $PY tests/test_reglages_fournisseurs_ecran.py"""
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
CLE = "AIzaFAUSSECLEDEBANC000000000000000"

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
// ── faux React : hooks à état par instance (chemin + nom + clé), effets joués une fois ──
const STORE=new Map();let CUR="",IDX=0;const EFF=[];
const x={useReducer(fn,init){const k=CUR+"#"+(IDX++);if(!STORE.has(k))STORE.set(k,init);
  return[STORE.get(k),a=>{STORE.set(k,fn(STORE.get(k),a))}]},
 useEffect(f){const k=CUR+"#"+(IDX++);if(!STORE.has(k)){STORE.set(k,1);EFF.push(f)}},
 useState(){throw new Error("useState interdit (compte figé 731)")},useRef(v){return{current:v}}};
const r={jsx:(t,p,key)=>({t,p,key}),jsxs:(t,p,key)=>({t,p,key}),Fragment:"Fragment"};
function re(){}function te(){}function K(){}
function dzT(k,v){return v?k+JSON.stringify(v):k}
const OUVERTS=[];function dzOuvrirReglages(s,a){OUVERTS.push(s)}
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
function ligne(arbre,id){return tous(arbre,n=>n.p&&n.p["data-dzfourn"]===id)[0]}
// ── faux serveur ──
const APPELS=[];let ETAT={roles:{summarizer:{available:["openai","gemini"],active:"openai",preference:""},
 planner:{available:["openai","gemini"],active:"openai",preference:"ollama"}},
 moteurs:[{moteur:"anthropic",nom:"Anthropic",configure:false,cle_modele:"ANTHROPIC_MODEL",modele:"claude-x",fautif:false,alerte:""},
  {moteur:"openai",nom:"OpenAI",configure:true,cle_modele:"OPENAI_MODEL",modele:"gpt-4o-mini",fautif:false,alerte:""},
  {moteur:"gemini",nom:"Google Gemini",configure:true,cle_modele:"GEMINI_MODEL",modele:"",fautif:true,alerte:"contient une clé, pas un nom de modèle"},
  {moteur:"ollama",nom:"Ollama",configure:false,cle_modele:"OLLAMA_MODEL",modele:"",fautif:false,alerte:""}]};
function rep(o,code){return Promise.resolve({ok:(code||200)<400,status:code||200,json:()=>Promise.resolve(o)})}
function fetch(u,o){const m=(o&&o.method)||"GET";APPELS.push([m,u,o&&o.body?JSON.parse(o.body):null]);
 if(u==="/api/settings/provider-defaults"&&m==="GET")return rep(ETAT);
 if(u==="/api/settings/provider-defaults"&&m==="POST")return rep({ok:true});
 if(u.startsWith("/api/settings/provider-defaults/modeles?moteur=openai"))return rep({modeles:["gpt-4o-mini","gpt-4.1"],lisible:true});
 if(u.startsWith("/api/settings/provider-defaults/modeles?moteur=gemini"))return rep({modeles:[],lisible:false});
 if(u==="/api/settings/provider-defaults/tester")return rep({etat:"connu",ok:true});
 return rep({detail:"?"},404)}
async function vider(){for(let i=0;i<6;i++){while(EFF.length)EFF.shift()();await new Promise(z=>setTimeout(z,0))}}
const ENV={r,x,re,te,K,dzT,fetch,dzOuvrirReglages,console};
(async()=>{try{
 const SRC=tranche("function dzFdJson(","function Em(");
 const M=new Function("ENV","with(ENV){"+SRC+";return{DzFournDefauts,DzFournModele,DzCleVersDefauts}}")(ENV);
 const RAC={t:M.DzFournDefauts,p:{cles:["FAL_KEY","OPENAI_API_KEY"]},key:"dzfourn"};
 let A=rendre(RAC,"R");await vider();A=rendre(RAC,"R");await vider();A=rendre(RAC,"R");
 const res={};
 // [A] services
 res.services=["video","avatar","voice"].map(id=>{const l=ligne(A,"service-"+id);return l?{txt:texte(l),
  choix:tous(l,n=>n.t==="re"||n.t==="input").length,ton:(tous(l,n=>n.t==="te")[0]||{p:{}}).p.tone}:null});
 // [B] rôles
 const rs=ligne(A,"role-summarizer"),rp=ligne(A,"role-planner");
 const sel=l=>tous(l,n=>n.t==="re")[0];
 res.sumOpts=sel(rs)&&sel(rs).p.options;res.sumVal=sel(rs)&&sel(rs).p.value;
 res.planOpts=sel(rp)&&sel(rp).p.options;res.planVal=sel(rp)&&sel(rp).p.value;
 APPELS.length=0;sel(rs).p.onChange("gemini");await vider();
 res.roleAppels=APPELS.slice();A=rendre(RAC,"R");res.msg=texte(ligne(A,"msg"));
 // [C] modèles
 res.lignesModele=tous(A,n=>n.p&&/^modele-/.test(n.p["data-dzfourn"]||"")).map(n=>n.p["data-dzfourn"]);
 const lo=()=>ligne(A,"modele-openai"),lg=()=>ligne(A,"modele-gemini");
 const inp=l=>tous(l,n=>n.t==="input")[0],btn=(l,k)=>tous(l,n=>n.t==="K"&&texte(n)===k)[0];
 res.oOpts=sel(lo()).p.options.map(o=>o.value);res.oInput=inp(lo()).p.value;res.oEtat=texte(ligne(lo(),"etat"));
 res.oEnregDesactive=btn(lo(),"reglages.commun.enregistrer").p.disabled;
 sel(lo()).p.onChange("gpt-4.1");A=rendre(RAC,"R");res.oInputApres=inp(lo()).p.value;
 inp(lo()).p.onChange({target:{value:"gpt-4.1-mini"}});A=rendre(RAC,"R");res.oLibre=inp(lo()).p.value;
 res.oOptsLibre=sel(lo()).p.options.map(o=>o.value);
 APPELS.length=0;btn(lo(),"reglages.diag.tester").p.onClick();await vider();A=rendre(RAC,"R");
 res.testAppels=APPELS.slice();res.testEtat=texte(ligne(lo(),"etat"));
 APPELS.length=0;btn(lo(),"reglages.commun.enregistrer").p.onClick();await vider();A=rendre(RAC,"R");
 res.enregAppels=APPELS.slice();
 // gemini fautif
 const g=lg();res.gEtat=texte(ligne(g,"etat"));res.gAlerte=texte(ligne(g,"alerte"));res.gInput=inp(g).p.value;res.gBord=inp(g).p.style.border;
 res.gEnregDesactive=btn(g,"reglages.commun.enregistrer").p.disabled;
 APPELS.length=0;btn(g,"reglages.commun.enregistrer").p.onClick();await vider();res.gAppels=APPELS.slice();
 res.arbre=JSON.stringify(A);
 // Clés d'API → Fournisseurs par défaut
 const V=rendre({t:M.DzCleVersDefauts,p:{k:{k:"GEMINI_MODEL",label:"Gemini — modèle"},c:1},key:"GEMINI_MODEL"},"V");
 res.versTxt=texte(V);tous(V,n=>n.t==="K")[0].p.onClick();res.ouverts=OUVERTS.slice();
 OUT.res=res;
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));})();
"""

print("[A-C] composants sous node")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzfourn_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(BUN_P.read_bytes())
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js")], capture_output=True, text=True, encoding="utf-8",
                    errors="replace")
try:
    OUT = json.loads(rn.stdout or "{}")
except ValueError:
    OUT = {"err": rn.stdout[-300:] + rn.stderr[-300:]}
check("0 composants extraits et rendus", "err" not in OUT, str(OUT.get("err", ""))[:400] + rn.stderr[-200:])
R = OUT.get("res", {})
sv = R.get("services") or [None, None, None]
check("A1 trois lignes de service, aucune liste ni champ (lecture seule)",
      all(s and s["choix"] == 0 for s in sv), repr(sv))
check("A2 la clé servie est nommée", sv[0] and "FAL_KEY" in sv[0]["txt"] and sv[1] and "HEYGEN_API_KEY" in sv[1]["txt"]
      and sv[2] and "ELEVENLABS_API_KEY" in sv[2]["txt"], repr(sv))
check("A3 son état : posée → vert, absente → rouge", sv[0] and sv[0]["ton"] == "green" and sv[1]["ton"] == "red", repr(sv))

print("[B] rôles")
so = R.get("sumOpts") or []
check("B1 Résumé News : Automatique + moteurs du serveur (pas des noms de clés)",
      [o["value"] for o in so] == ["", "openai", "gemini"] and R.get("sumVal") == "", repr(so))
check("B2 libellés : noms des moteurs, l'automatique dit lequel est actif",
      so and so[0]["label"] == 'reglages.fournisseurs.auto{"moteur":"OpenAI"}' and so[2]["label"] == "Google Gemini", repr(so))
po = R.get("planOpts") or []
check("B3 un choix enregistré mais indisponible reste visible et nommé",
      R.get("planVal") == "ollama" and po and po[-1] == {"value": "ollama", "label": "Ollama" + "reglages.defauts.indisponible"},
      repr(po))
ra = R.get("roleAppels") or []
check("B4 choisir un moteur : POST {summarizer:\"gemini\"} puis relecture",
      len(ra) >= 2 and ra[0] == ["POST", "/api/settings/provider-defaults", {"summarizer": "gemini"}]
      and ra[1][:2] == ["GET", "/api/settings/provider-defaults"], repr(ra))
check("B5 confirmation « Enregistré »", R.get("msg") == "commun.etat.enregistre", repr(R.get("msg")))
check("B6 plus aucun localStorage dans les composants", "localStorage" not in
      BUNDLE[BUNDLE.find("function dzFdJson("):BUNDLE.find("function Em(")])

print("[C] modèles")
check("C1 une ligne par moteur configuré ou fautif (ni anthropic ni ollama ici)",
      R.get("lignesModele") == ["modele-openai", "modele-gemini"], repr(R.get("lignesModele")))
check("C2 la liste vient du fournisseur", R.get("oOpts") == ["gpt-4o-mini", "gpt-4.1"], repr(R.get("oOpts")))
check("C3 le modèle courant est dans la saisie, Enregistrer grisé tant que rien ne change",
      R.get("oInput") == "gpt-4o-mini" and R.get("oEnregDesactive") is True, repr((R.get("oInput"), R.get("oEnregDesactive"))))
check("C4 nombre de modèles publiés affiché", R.get("oEtat") == 'reglages.fournisseurs.n_modeles{"n":2}', repr(R.get("oEtat")))
check("C5 choisir dans la liste remplit la saisie", R.get("oInputApres") == "gpt-4.1")
check("C6 saisie libre : gardée, et ajoutée en tête de la liste", R.get("oLibre") == "gpt-4.1-mini"
      and (R.get("oOptsLibre") or [None])[0] == "gpt-4.1-mini", repr(R.get("oOptsLibre")))
ta = R.get("testAppels") or []
check("C7 Tester : POST …/tester {moteur, modele}, rien d'autre",
      ta == [["POST", "/api/settings/provider-defaults/tester", {"moteur": "openai", "modele": "gpt-4.1-mini"}]], repr(ta))
check("C8 résultat du test affiché", R.get("testEtat") == "reglages.fournisseurs.test_connu", repr(R.get("testEtat")))
ea = R.get("enregAppels") or []
check("C9 Enregistrer : POST {modeles:{openai:…}} puis relecture",
      len(ea) >= 2 and ea[0] == ["POST", "/api/settings/provider-defaults", {"modeles": {"openai": "gpt-4.1-mini"}}]
      and ea[1][:2] == ["GET", "/api/settings/provider-defaults"], repr(ea))
check("C10 modèle fautif : alerte « contient une clé »", R.get("gAlerte") == " · reglages.fournisseurs.cle_dans_modele",
      repr(R.get("gAlerte")))
check("C11 modèle fautif : champ vide, bord rouge", R.get("gInput") == "" and "var(--red)" in (R.get("gBord") or ""))
check("C12 se corrige d'un clic : Enregistrer actif, POST {modeles:{gemini:\"\"}}",
      R.get("gEnregDesactive") is False and (R.get("gAppels") or [[None]])[0] == ["POST", "/api/settings/provider-defaults",
                                                                                  {"modeles": {"gemini": ""}}], repr(R.get("gAppels")))
check("C14 liste illisible : dit « illisible », pas « 0 modèle publié »", R.get("gEtat") == "reglages.fournisseurs.liste_illisible", repr(R.get("gEtat")))
check("C13 aucune clé dans l'arbre rendu", "AIza" not in (R.get("arbre") or "AIza"))

print("[D] sites")
i_em = BUNDLE.find("function Em(){")
em = BUNDLE[i_em:BUNDLE.find("function Tm(){", i_em)]
check("D1 Em rend DzFournDefauts à la place des lignes de rôle locales",
      'r.jsx(DzFournDefauts,{cles:t},"dzfourn")' in em and "...s.map(" not in em)
check("D2 l'aide ne dit plus « Enregistré localement »", 'dzT("reglages.fournisseurs.aide")' in em
      and "reglages.defauts.aide_2" not in BUNDLE)
check("D3 Diagnostic : l'alerte à la place de l'aperçu, en rouge",
      "(c.alerte?dzT(\"reglages.fournisseurs.cle_dans_modele\"):(c.apercu||''))" in BUNDLE
      and "(c.alerte?'var(--red)':'var(--ink-muted)')" in BUNDLE)
check("D4 Clés d'API : GEMINI_MODEL rendu par DzCleVersDefauts",
      'h=g[k.k];if(k.k==="GEMINI_MODEL")return r.jsx(DzCleVersDefauts,{k:k,c:c},k.k);' in BUNDLE)   # t221 : DzCleTexte suit
check("D5 DzCleVersDefauts : texte et bouton → rubrique defaults", "reglages.fournisseurs.se_regle_ailleurs" in (R.get("versTxt") or "")
      and R.get("ouverts") == ["defaults"], repr((R.get("versTxt"), R.get("ouverts"))))
check("D6 composants ×1", all(BUNDLE.count(f"function {n}(") == 1 for n in ("DzFournDefauts", "DzFournModele",
                                                                          "DzCleVersDefauts", "dzFdJson")))

print("[E] i18n")
cat = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
utilisees = set(re.findall(r'dzT\("(reglages\.fournisseurs\.[a-z_]+)"[,)]', BUNDLE))
manq = [k for k in sorted(utilisees) if not (cat.get(k) or {}).get("fr") or not (cat.get(k) or {}).get("en")]
check("E1 chaque clé reglages.fournisseurs.* employée est dans menus.json (FR + EN)", not manq and len(utilisees) >= 10,
      repr(manq))
fr_en = {}
for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    try:
        for k, e in json.loads(f.read_text(encoding="utf-8")).items():
            if isinstance(e, dict) and "fr" in e and "en" in e:
                fr_en.setdefault(e["fr"], set()).add(e["en"])
    except ValueError:
        pass
doubles = [k for k in utilisees if k in cat and len(fr_en.get(cat[k]["fr"], set())) > 1]
check("E2 une phrase FR = une traduction", not doubles, repr(doubles))
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("E3 catalogue assemblé à jour", ra.returncode == 0, (ra.stdout + ra.stderr)[-300:])
check("E4 clés réemployées présentes au catalogue",
      all(k in json.loads((RACINE / "frontend/shared/i18n/" / f).read_text(encoding="utf-8"))
          for f, k in (("reglages.json", "reglages.diag.tester"), ("commun.json", "commun.etat.enregistre"),
                       ("commun.json", "commun.action.ouvrir"), ("reglages.json", "reglages.defauts.indisponible"))))

print("[F] maillon dzreglages")
import patch_bundle_dzreglages as DR                                  # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
try:
    # t310 (27/10/2026) : le maillon dzwhatsapp, posé après, touche dzFuNeuves : le livré se lit vu d'avant dzwhatsapp
    avant = DR.defaire(AIDE.avant_dzwhatsapp(BUNDLE))
    rejoue = DR.appliquer(avant)
except (AssertionError, SystemExit) as e:
    avant = rejoue = str(e)
check("F1 aller-retour à l'octet", rejoue == AIDE.avant_dzwhatsapp(BUNDLE) and DR.MARKER not in avant)
check("F2 l'avant a le défaut d'origine (rôles locaux, « Enregistré localement »)",
      "...s.map((a,l)=>{const d=a.options" in avant and 'dzT("reglages.defauts.aide_2")' in avant
      and "DzFournDefauts" not in avant)
check("F3 avant_dzreglages = défaire", AIDE.avant_dzreglages(BUNDLE) == AIDE.avant_dzlogo(avant))  # dzlogo, posé après, défait d'abord
try:
    _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
except (OSError, ValueError, KeyError):
    _g1 = []
check("F4 aucune paire ne chevauche un remplacement G1 (dzglyph)", bool(_g1) and all(BUNDLE.count(x) == avant.count(x)
                                                                                      for x in _g1))
check("F5 comptes figés intacts", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181)
b = BUN_P.read_bytes()
check("F6 CRLF intactes, aucune fin de ligne injectée", b.count(b"\r\n") > 15000 and b.count(b"\n") == b.count(b"\r\n"))
check("F7 aucun .bak_dzreglages", not (BUN_P.parent / (BUN_P.name + ".bak_dzreglages")).exists())
check("F9 aucune clé dzT construite (test_i18n_l1 3b)", 'dzT("reglages.fournisseurs.test_"+' not in BUNDLE)
check("F8 aucun dzT local (règle t212) dans les composants", not re.search(
    r"\bdzT\s*=", BUNDLE[BUNDLE.find("function dzFdJson("):BUNDLE.find("function Em(")]))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
