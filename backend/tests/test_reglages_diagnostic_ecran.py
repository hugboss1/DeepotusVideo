# -*- coding: utf-8 -*-
"""t221 (Menus : Réglages, 16/10/2026) — l'ÉCRAN : Diagnostic « Régler », champs des clés orphelines (banc serveur à
part : test_reglages_diagnostic.py).

Défaut relevé sur c784c6e8 : chaque ligne du Diagnostic disait « définie / absente » sans dire où régler la clé ;
DECART_API_KEY, ELEVENLABS_VOICE_ID_FR / _EN et ARTICLE_READER_FALLBACK ne se réglaient nulle part dans Réglages.

Ce que ce banc garde (composants du maillon dzreglages rendus sous node, hooks simulés À ÉTAT, faux serveur) :
  [A] DzDiagRegler : « Régler » ouvre la rubrique de la ligne par dzOuvrirReglages(rubrique) SANS `aller` (Réglages
      est déjà ouvert) ; une ligne sans rubrique n'a pas de bouton ;
  [B] DzCleTexte (voix ElevenLabs) : champ CLAIR (pas un champ de clé), aperçu actuel, Enregistrer grisé à vide,
      POST /api/settings/keys {name, value} puis relecture ; l'erreur du serveur est dite en rouge ;
  [C] DzNewsLecteur : l'état lu sur /api/health, la bascule écrit "false"/"true", l'erreur est dite ;
  [D] sites : la ligne du Diagnostic a sa colonne et son bouton ; Clés d'API a la ligne Decart (secret, santé
      decart_configured) et les deux voix (`texte`) ; Réglages › News monte la bascule ;
  [E] i18n : clés FR/EN dans menus.json, une phrase FR = une traduction, catalogue assemblé à jour ;
  [F] maillon dzreglages : aller-retour à l'octet, défaut d'origine dans l'avant, aucun chevauchement G1, comptes
      figés, CRLF, aucun .bak, aucune clé dzT construite, aucun dzT local.
Run (depuis backend/) : & $PY tests/test_reglages_diagnostic_ecran.py"""
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

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
const STORE=new Map();let CUR="",IDX=0;const EFF=[];
const x={useReducer(fn,init){const k=CUR+"#"+(IDX++);if(!STORE.has(k))STORE.set(k,init);
  return[STORE.get(k),a=>{STORE.set(k,fn(STORE.get(k),a))}]},
 useEffect(f){const k=CUR+"#"+(IDX++);if(!STORE.has(k)){STORE.set(k,1);EFF.push(f)}},
 useState(){throw new Error("useState interdit (compte figé 731)")},useRef(v){return{current:v}}};
const r={jsx:(t,p,key)=>({t,p,key}),jsxs:(t,p,key)=>({t,p,key}),Fragment:"Fragment"};
function K(){}function jt(){}function Ze(){}
function dzT(k,v){return v?k+JSON.stringify(v):k}
const OUVERTS=[];function dzOuvrirReglages(){OUVERTS.push(Array.from(arguments))}
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
const APPELS=[];let SANTE={article_reader_fallback:true};let REFUS=null;
function rep(o,code){return Promise.resolve({ok:(code||200)<400,status:code||200,json:()=>Promise.resolve(o)})}
function fetch(u,o){const m=(o&&o.method)||"GET";APPELS.push([m,u,o&&o.body?JSON.parse(o.body):null]);
 if(u==="/api/health")return rep(SANTE);
 if(u==="/api/settings/keys"&&m==="POST")return REFUS?rep({detail:REFUS},400):rep({ok:true,written:[JSON.parse(o.body).name]});
 return rep({detail:"?"},404)}
async function vider(){for(let i=0;i<6;i++){while(EFF.length)EFF.shift()();await new Promise(z=>setTimeout(z,0))}}
const ENV={r,x,K,jt,Ze,dzT,fetch,dzOuvrirReglages,console};
(async()=>{try{
 const SRC=tranche("function dzRgCle(","function DzDiag(");
 const M=new Function("ENV","with(ENV){"+SRC+";return{DzDiagRegler,DzCleTexte,DzNewsLecteur,dzRgCle}}")(ENV);
 const res={};
 // [A] Régler
 const A1=rendre({t:M.DzDiagRegler,p:{c:{cle:"PLANNER_PROVIDER",rubrique:"defaults"}}},"A");
 res.aType=A1.t;res.aTxt=texte(A1);res.aData=A1.p["data-dzdiag-regler"];res.aTitre=A1.p.title;A1.p.onClick();
 const A2=rendre({t:M.DzDiagRegler,p:{c:{cle:"X",rubrique:""}}},"A2");res.a2Type=A2.t;
 res.ouverts=OUVERTS.slice();
 // [B] voix
 let RELU=0;const RB={t:M.DzCleTexte,p:{k:{k:"ELEVENLABS_VOICE_ID_FR",label:"voix FR",why:"pourquoi",texte:true},c:1,
  h:{set:true,preview:"nPcz••••zQrb"},relire:()=>{RELU++}},key:"ELEVENLABS_VOICE_ID_FR"};
 let B=rendre(RB,"B");const inp=()=>tous(B,n=>n.t==="input")[0],btn=()=>tous(B,n=>n.t==="K")[0];
 res.bType=inp().p.type;res.bPlace=inp().p.placeholder;res.bTxt=texte(B);res.bData=B.p["data-dzcle-texte"];
 res.bVide=btn().p.disabled;
 inp().p.onChange({target:{value:"  JBFqnCBsd6RMkjVDRZzb "}});B=rendre(RB,"B");res.bPlein=btn().p.disabled;
 APPELS.length=0;btn().p.onClick();await vider();B=rendre(RB,"B");
 res.bAppels=APPELS.slice();res.bRelu=RELU;res.bMsg=texte(tous(B,n=>n.p&&n.p["data-dzcle-msg"])[0]);res.bApres=inp().p.value;
 res.bMsgType=(tous(B,n=>n.p&&n.p["data-dzcle-msg"])[0]||{p:{}}).p["data-dzcle-msg"];
 REFUS="Key not allowed: X";inp().p.onChange({target:{value:"abc"}});B=rendre(RB,"B");btn().p.onClick();await vider();B=rendre(RB,"B");
 const em=tous(B,n=>n.p&&n.p["data-dzcle-msg"])[0]||{p:{}};res.bErr=texte(em);res.bErrType=em.p["data-dzcle-msg"];
 res.bErrCouleur=em.p.style&&em.p.style.color;REFUS=null;res.bRelu2=RELU;
 // [C] lecteur
 const RC={t:M.DzNewsLecteur,p:{},key:"lect"};
 let C=rendre(RC,"C");res.cInconnu=C.p["data-dzlecteur"];await vider();C=rendre(RC,"C");
 res.cEtat=C.p["data-dzlecteur"];const ze=()=>tous(C,n=>n.t==="Ze")[0];res.cChecked=ze().p.checked;res.cTxt=texte(C);
 APPELS.length=0;ze().p.onChange(false);await vider();C=rendre(RC,"C");
 res.cAppels=APPELS.slice();res.cApres=C.p["data-dzlecteur"];res.cMsg=texte(tous(C,n=>n.p&&n.p["data-dzlecteur-msg"])[0]);
 APPELS.length=0;ze().p.onChange(true);await vider();C=rendre(RC,"C");res.cAppels2=APPELS.slice();res.cApres2=C.p["data-dzlecteur"];
 REFUS="refus banc";ze().p.onChange(false);await vider();C=rendre(RC,"C");
 const cm=tous(C,n=>n.p&&n.p["data-dzlecteur-msg"])[0]||{p:{}};res.cErr=texte(cm);res.cErrType=cm.p["data-dzlecteur-msg"];
 res.cApres3=C.p["data-dzlecteur"];REFUS=null;
 // ancien serveur (sans le champ) : état inconnu, aucune bascule montrée
 STORE.clear();SANTE={};let C2=rendre(RC,"C2");await vider();C2=rendre(RC,"C2");
 res.c2Etat=C2.p["data-dzlecteur"];res.c2Ze=tous(C2,n=>n.t==="Ze").length;
 OUT.res=res;
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));})();
"""

print("[A-C] composants sous node")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzdiag221_"))
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

print("[A] Régler")
check("A1 un bouton « Régler » (K), sa bulle dit où il mène", R.get("aType") == "K" and R.get("aTxt") == "reglages.diag.regler"
      and R.get("aTitre") == "reglages.diag.regler_aide" and R.get("aData") == "defaults", repr(R)[:300])
check("A2 clic : dzOuvrirReglages(\"defaults\") SANS second argument (Réglages déjà ouvert)",
      R.get("ouverts") == [["defaults"]], repr(R.get("ouverts")))
check("A3 ligne sans rubrique : aucun bouton (cellule vide)", R.get("a2Type") == "div", repr(R.get("a2Type")))

print("[B] voix ElevenLabs (réglage texte)")
check("B1 champ CLAIR, pas un champ de clé (type text)", R.get("bType") == "text", repr(R.get("bType")))
check("B2 libellé, nom du réglage, aperçu actuel, invite « Identifiant de voix »",
      "voix FR" in (R.get("bTxt") or "") and "ELEVENLABS_VOICE_ID_FR" in R.get("bTxt", "") and "nPcz••••zQrb" in R.get("bTxt", "")
      and R.get("bPlace") == "avatar.perso.voix_id" and R.get("bData") == "ELEVENLABS_VOICE_ID_FR", repr(R.get("bTxt")))
check("B3 Enregistrer grisé à vide, actif une fois rempli", R.get("bVide") is True and R.get("bPlein") is False)
check("B4 Enregistrer : POST /api/settings/keys {name, value rognée}, rien d'autre",
      R.get("bAppels") == [["POST", "/api/settings/keys", {"name": "ELEVENLABS_VOICE_ID_FR", "value": "JBFqnCBsd6RMkjVDRZzb"}]],
      repr(R.get("bAppels")))
check("B5 puis relecture des clés, champ vidé, « Enregistré » en vert",
      R.get("bRelu") == 1 and R.get("bApres") == "" and R.get("bMsg") == "commun.etat.enregistre" and R.get("bMsgType") == "ok")
check("B6 refus du serveur : son message, en rouge, sans relecture",
      R.get("bErr") == "Key not allowed: X" and R.get("bErrType") == "erreur" and R.get("bErrCouleur") == "var(--red)"
      and R.get("bRelu2") == 1, repr((R.get("bErr"), R.get("bErrType"), R.get("bRelu2"))))

print("[C] lecteur public de News")
check("C1 avant la réponse de /api/health : état inconnu", R.get("cInconnu") == "inconnu", repr(R.get("cInconnu")))
check("C2 l'état est lu sur /api/health (actif), la bascule est cochée, le réglage est nommé",
      R.get("cEtat") == "actif" and R.get("cChecked") is True and "ARTICLE_READER_FALLBACK" in (R.get("cTxt") or "")
      and "reglages.news.lecteur_aide" in R.get("cTxt", ""), repr(R.get("cTxt")))
check("C3 couper : POST {name:ARTICLE_READER_FALLBACK, value:\"false\"}, état « coupé », « Enregistré »",
      R.get("cAppels") == [["POST", "/api/settings/keys", {"name": "ARTICLE_READER_FALLBACK", "value": "false"}]]
      and R.get("cApres") == "coupe" and R.get("cMsg") == "commun.etat.enregistre", repr(R.get("cAppels")))
check("C4 rétablir : value \"true\"", R.get("cAppels2") == [["POST", "/api/settings/keys",
                                                            {"name": "ARTICLE_READER_FALLBACK", "value": "true"}]]
      and R.get("cApres2") == "actif")
check("C5 refus : message rouge, l'état ne change pas", R.get("cErr") == "refus banc" and R.get("cErrType") == "erreur"
      and R.get("cApres3") == "actif", repr((R.get("cErr"), R.get("cApres3"))))
check("C6 serveur sans le champ : état inconnu, aucune bascule montrée (pas de faux « coupé »)",
      R.get("c2Etat") == "inconnu" and R.get("c2Ze") == 0, repr((R.get("c2Etat"), R.get("c2Ze"))))

print("[D] sites")
check("D1 la ligne du Diagnostic : une colonne de plus et DzDiagRegler",
      "'data-dzdiag-cle':c.cle,style:{display:'grid',gridTemplateColumns:'210px 90px 1fr auto auto',gap:10," in BUNDLE
      and "r.jsx('div',{}),r.jsx(DzDiagRegler,{c:c})]},c.cle)" in BUNDLE)
fu = BUNDLE[BUNDLE.find("function dzFuNeuves("):BUNDLE.find("function dzRgCle(")]
check("D2a les lignes neuves sont AJOUTÉES au rendu (Fu.concat), le littéral Fu reste tel quel (Figma en dernier)",
      BUNDLE.count("children:Fu.concat(dzFuNeuves()).map((k,c)=>{") == 1 and BUNDLE.count('health:"figma_configured"}];function bm(){') == 1
      and "DECART_API_KEY" not in BUNDLE[BUNDLE.find("const Fu=["):BUNDLE.find("function bm(")])
check("D2 Clés d'API : Decart, ligne de secret ordinaire (santé decart_configured, pas `texte`)",
      '{k:"DECART_API_KEY",label:dzT("reglages.cles.decart"),why:dzT("reglages.cles.decart_pourquoi"),health:"decart_configured"}'
      in fu)
check("D3 Clés d'API : voix FR et EN en `texte:!0`", fu.count("texte:!0") == 2 and '{k:"ELEVENLABS_VOICE_ID_FR"' in fu
      and '{k:"ELEVENLABS_VOICE_ID_EN"' in fu)
check("D4 une ligne `texte` est rendue par DzCleTexte, avec la relecture de bm (m) et de la santé (No)",
      'if(k.texte)return r.jsx(DzCleTexte,{k:k,c:c,h:h,relire:function(){m(),No()}},k.k);' in BUNDLE)
check("D5 Réglages › News monte DzNewsLecteur sous son aide", 'children:dzT("reglages.news.aide")}),r.jsx(DzNewsLecteur,{}),'
      in BUNDLE)
check("D6 composants ×1", all(BUNDLE.count(f"function {n}(") == 1 for n in ("dzFuNeuves", "dzRgCle", "DzDiagRegler", "DzCleTexte",
                                                                          "DzNewsLecteur")))
src_d = BUNDLE[BUNDLE.find("function dzRgCle("):BUNDLE.find("function DzDiag(")]
check("D7 « Régler » n'appelle jamais aller : dzOuvrirReglages(c.rubrique) seul", "dzOuvrirReglages(c.rubrique)}" in src_d
      and "dzOuvrirReglages(c.rubrique," not in src_d)
check("D8 aucune valeur de clé lue ni rendue (aucun listKeys, aucun champ password)", "listKeys" not in src_d
      and "password" not in src_d)

print("[E] i18n")
cat = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
NEUVES = ("reglages.diag.regler", "reglages.diag.regler_aide", "reglages.cles.decart", "reglages.cles.decart_pourquoi",
          "reglages.cles.voix_fr", "reglages.cles.voix_en", "reglages.cles.voix_pourquoi", "reglages.news.lecteur",
          "reglages.news.lecteur_aide")
manq = [k for k in NEUVES if not (cat.get(k) or {}).get("fr") or not (cat.get(k) or {}).get("en")
        or f'dzT("{k}")' not in BUNDLE]
check("E1 chaque clé neuve est dans menus.json (FR + EN) et employée par le bundle", not manq, repr(manq))
fr_en, ou = {}, {}
for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    try:
        for k, e in json.loads(f.read_text(encoding="utf-8")).items():
            if isinstance(e, dict) and "fr" in e and "en" in e:
                fr_en.setdefault(e["fr"], set()).add(e["en"])
                ou.setdefault(k, []).append(f.name)
    except ValueError:
        pass
check("E2 une phrase FR = une traduction", all(len(fr_en.get(cat[k]["fr"], set())) == 1 for k in NEUVES if k in cat))
check("E3 aucune clé neuve en double dans un autre catalogue", all(ou.get(k) == ["menus.json"] for k in NEUVES), repr(
    {k: ou.get(k) for k in NEUVES if ou.get(k) != ["menus.json"]}))
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("E4 catalogue assemblé à jour", ra.returncode == 0, (ra.stdout + ra.stderr)[-300:])
check("E5 clés réemployées présentes au catalogue",
      all(k in json.loads((RACINE / "frontend/shared/i18n/" / f).read_text(encoding="utf-8"))
          for f, k in (("avatar.json", "avatar.perso.voix_id"), ("commun.json", "commun.etat.enregistre"),
                       ("reglages.json", "reglages.cles.actuelle"), ("reglages.json", "reglages.commun.enregistrer"))))

print("[F] maillon dzreglages")
import patch_bundle_dzreglages as DR                                  # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
try:
    avant = DR.defaire(BUNDLE)
    rejoue = DR.appliquer(avant)
except (AssertionError, SystemExit) as e:
    avant = rejoue = str(e)
check("F1 aller-retour à l'octet", rejoue == BUNDLE and DR.MARKER not in avant)
check("F2 l'avant a le défaut d'origine (ligne sans bouton, aucune ligne Decart ni voix, News sans bascule)",
      "gridTemplateColumns:'210px 90px 1fr auto',gap:10" in avant and "DzDiagRegler" not in avant
      and "DECART_API_KEY" not in avant and "DzNewsLecteur" not in avant)
check("F3 avant_dzreglages = défaire", AIDE.avant_dzreglages(BUNDLE) == avant)
try:
    _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
except (OSError, ValueError, KeyError):
    _g1 = []
check("F4 aucune paire ne chevauche ni ne recopie un remplacement G1 (dzglyph)",
      bool(_g1) and all(BUNDLE.count(x) == avant.count(x) for x in _g1))
check("F5 comptes figés intacts", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181)
b = BUN_P.read_bytes()
check("F6 CRLF intactes, aucune fin de ligne injectée", b.count(b"\r\n") > 15000 and b.count(b"\n") == b.count(b"\r\n"))
check("F7 aucun .bak_dzreglages", not (BUN_P.parent / (BUN_P.name + ".bak_dzreglages")).exists())
check("F8 aucune clé dzT construite (test_i18n_l1 3b)", not re.search(r'dzT\("[a-z_.]+"\+', src_d))
check("F9 aucun dzT local (règle t212) dans les composants", not re.search(r"\bdzT\s*=", src_d))
check("F10 lecture/écriture du patcher en octets", "read_text(" not in (RACINE / "scripts" / "patch_bundle_dzreglages.py")
      .read_text(encoding="utf-8"))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
