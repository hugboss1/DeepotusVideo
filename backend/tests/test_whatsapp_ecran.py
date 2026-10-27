# -*- coding: utf-8 -*-
"""t310 tâche 7 (27/10/2026) — WhatsApp à l'écran : panneau de liaison, filtres de cibles et clé Kapso dans Réglages.

Plan docs/superpowers/plans/2026-10-27-t310-whatsapp-kapso.md (tâche 7), spec 2026-10-25-boite-a-outils-design.md §5.3
et §6.1 « Liaison d'un numéro dans l'assistant ». WhatsApp est un canal de conversation d'espace, JAMAIS une cible de
publication.
[1] le maillon      scripts/patch_bundle_dzwhatsapp.py : marqueur x1, aucun .bak_dzwhatsapp, octets, --check « déjà
                    appliqué », ancres uniques (vue d'avant), hors couche, aller-retour exact, base rendue à l'octet,
                    épingles intouchées, node --check ;
[2] réversible      avant_dzwhatsapp == defaire, appelé EN TÊTE de avant_dzgardeclient ;
[3] les paires      P1 dzFuNeuves porte la ligne KAPSO_API_KEY (texte exact) ; P2 DzPostComptes écarte whatsapp (sous node,
                    fonction LIVRÉE) ; whatsapp absent de la table des canaux `_t` du Planificateur ;
[4] le panneau      sous node (faux DOM, faux fetch) : sans clé Kapso, le message seul ; espace gouverné par un client
                    (client, ou produit d'un client) : moyen et date du consentement, « Créer le lien » grisé sans eux ;
                    facturation customer_managed cochée par défaut, celle déjà posée imposée ; le clic envoie POST
                    …/whatsapp/lien puis montre l'URL en lecture seule, « Copier » et l'expiration ; « Vérifier » relit la
                    liaison (GET …/liaison après /verifier) ; codes de liaison traduits ; refus structuré lisible ;
                    aucun <input> pour un champ whatsapp ni pour KAPSO_API_KEY ;
[5] les canaux      la boîte des canaux d'un projet (dz-projet-canaux.js) ne propose aucun compte whatsapp ;
[6] textes          chaque clé employée existe en FR et en EN, mêmes {variables} ; l'assemblé est à jour ; copies dist.
Run : & $PY tests/test_whatsapp_ecran.py   (depuis backend/)
"""
import hashlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import _i18n_l1_aide as AIDE  # noqa: E402
F = AIDE.fr

NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


ASSETS = REPO / "frontend" / "dist" / "assets"
BUNDLE = ASSETS / "index-BEOJX8L5.js"
RAW = BUNDLE.read_bytes()
B = RAW.decode("utf-8")
SH = REPO / "frontend" / "shared"
DI = REPO / "frontend" / "dist" / "shared"
ASSISTANT = SH / "dz-espace-assistant.js"
CANAUX = SH / "dz-projet-canaux.js"
MARKER = "/*dzwhatsapp*/"
CONFIRMER = "await window.__dzDialogue.confirmer("
# empreinte du bundle d'avant le maillon (base 676b9116, CRLF du poste)
BASE_SHA256 = "6b3ebb0296a7c5df4480ec3c28883a573e397f27e1ebb63ff0fa2bbb4b11642a"
LIGNE_KAPSO = '{k:"KAPSO_API_KEY",label:dzT("reglages.cles.kapso"),why:dzT("reglages.cles.kapso_why")}'
CHAMPS_WA = ("KAPSO_CUSTOMER_ID", "WHATSAPP_PHONE_ID", "WHATSAPP_NUMERO", "WHATSAPP_WABA_ID", "WHATSAPP_FACTURATION_META",
             "KAPSO_API_KEY")


def blocs(s):
    return [(m.start(), s.index("/*__DZ_%s_END__*/" % m.group(1)))
            for m in re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", s)]


def tranche(s, debut, fin):
    i = s.find(debut)
    j = s.find(fin, i)
    return s[i:j] if 0 <= i < j else ""


def node(code):
    with tempfile.TemporaryDirectory() as _d:
        f = pathlib.Path(_d) / "h.js"
        f.write_text(code, "utf-8")
        p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except ValueError:
        return {"erreur": (p.stdout + p.stderr)[-800:]}


# le faux DOM et le faux React du banc de l'assistant (t308), repris tels quels
_SRC_ASSISTANT = (BACKEND / "tests" / "test_espace_assistant_ecran.py").read_text("utf-8")
FAUX_DOM = re.search(r'FAUX_DOM = r"""(.*?)"""', _SRC_ASSISTANT, re.S).group(1)
FAUX_REACT = re.search(r'FAUX_REACT = r"""(.*?)"""', _SRC_ASSISTANT, re.S).group(1)

# ── [1] le maillon ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[1] le maillon")
try:
    import patch_bundle_dzwhatsapp as PM                 # noqa: E402
except Exception as e:                                   # noqa: BLE001
    PM = None
    check("1.0 le maillon patch_bundle_dzwhatsapp existe", False, repr(e))
check("1.1 le marqueur une fois dans le bundle", B.count(MARKER) == 1, str(B.count(MARKER)))
check("1.2 aucun .bak_dzwhatsapp laissé", not list(ASSETS.glob("*.bak_dzwhatsapp")))
avant = ""
if PM:
    src = (REPO / "scripts" / "patch_bundle_dzwhatsapp.py").read_text("utf-8")
    check("1.3 lecture et écriture en OCTETS", "read_text(" not in src and "write_text(" not in src
          and "read_bytes(" in src and "write_bytes(" in src)
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzwhatsapp.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("1.4 --check : « déjà appliqué », bundle inchangé", r.returncode == 0 and "déjà appliqué" in r.stdout
          and BUNDLE.read_bytes() == RAW, r.stdout + r.stderr)
    check("1.5 sondes amont : marqueur de dzgardeclient et épingles",
          ("dzgardeclient", "/*dzgardeclient*/", 1) in PM.SONDE_AMONT and ("useState", "x.useState(", 731) in PM.SONDE_AMONT
          and ("version", "v2.8.0", 4) in PM.SONDE_AMONT and ("montage", "DzTracks", 181) in PM.SONDE_AMONT
          and ("dialogue", CONFIRMER, 30) in PM.SONDE_AMONT)
    try:
        avant = PM.defaire(B) if MARKER in B else ""
    except AssertionError:
        avant = ""
    check("1.6 cinq paires (P1, P2, P3a-c) ; chaque ancre une fois dans le bundle d'avant, chaque remplacement une fois dans le livré",
          lambda: len(PM.PAIRES) == 5 and bool(avant) and all(avant.count(a) == 1 and B.count(z) == 1 for a, z in PM.PAIRES))
    check("1.7 les paires n'ont aucune fin de ligne, n'ajoutent ni x.useState( ni confirmation",
          all("\n" not in a + z and "x.useState(" not in z and CONFIRMER not in z for a, z in PM.PAIRES))
    check("1.8 chaque ancre (vue d'avant) et chaque remplacement (livré) HORS de tout bloc de couche __DZ_*_BEGIN__",
          lambda: all(not (s0 <= B.index(z) <= e0) for _a, z in PM.PAIRES for s0, e0 in blocs(B))
          and all(not (s0 <= avant.index(a) <= e0) for a, _z in PM.PAIRES for s0, e0 in blocs(avant)))
    check("1.9 aller-retour exact : appliquer(defaire(B)) == B, defaire(B) sans marqueur",
          lambda: PM.appliquer(PM.defaire(B)) == B and MARKER not in PM.defaire(B))
    check("1.10 la base est rendue À L'OCTET (empreinte du bundle d'avant le maillon, CRLF compris)",
          lambda: hashlib.sha256(PM.defaire(B).encode("utf-8")).hexdigest() == BASE_SHA256)
for jeton, n in {"x.useState(": 731, "v2.8.0": 4, "DzTracks": 181, CONFIRMER: 30, "/*dzgardeclient*/": 1,
                 "function DzPostComptes(": 1, "function dzFuNeuves(": 1}.items():
    check(f"1.11 compte {jeton!r} = {n}", B.count(jeton) == n, str(B.count(jeton)))
check("1.12 CRLF partout (en octets)", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
if NODE:
    with tempfile.TemporaryDirectory() as _d:
        t = pathlib.Path(_d) / "b.mjs"
        t.write_bytes(RAW)
        rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("1.13 node --check : le bundle PARSE", rc.returncode == 0, rc.stderr[-300:])

# ── [2] réversible ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[2] la chaîne inverse")
check("2.1 avant_dzwhatsapp existe et rend defaire(B)",
      lambda: PM is not None and AIDE.avant_dzwhatsapp(B) == PM.defaire(B))
check("2.2 avant_dzwhatsapp sans marqueur : rendu tel quel",
      lambda: AIDE.avant_dzwhatsapp(PM.defaire(B)) == PM.defaire(B))
check("2.3 avant_dzgardeclient défait dzwhatsapp D'ABORD, puis dzgardeclient",
      lambda: MARKER not in AIDE.avant_dzgardeclient(B) and "/*dzgardeclient*/" not in AIDE.avant_dzgardeclient(B)
      and AIDE.avant_dzgardeclient(B) == AIDE.avant_dzgardeclient(AIDE.avant_dzwhatsapp(B)))
check("2.4 l'appel est en TÊTE de avant_dzgardeclient (avant le test du marqueur)",
      lambda: (lambda s: 0 <= s.find("avant_dzwhatsapp(bundle)") < s.find("_m.MARKER not in bundle"))(
          (BACKEND / "tests" / "_i18n_l1_aide.py").read_text("utf-8").split("def avant_dzgardeclient(", 1)[1].split("\ndef ", 1)[0]))
check("2.5 la chaîne reste complète (avant_dzassistant retire aussi dzwhatsapp)",
      lambda: MARKER not in AIDE.avant_dzassistant(B) and "/*__dzassistant*/" not in AIDE.avant_dzassistant(B))

# ── [3] les paires ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[3] les paires P1 et P2")
FU = tranche(B, "function dzFuNeuves(", "function dzRgCle(")
check("3.1 P1 : dzFuNeuves() porte la ligne de la clé Kapso, texte exact, une fois",
      FU.count(LIGNE_KAPSO) == 1 and B.count('k:"KAPSO_API_KEY"') == 1, FU[-300:])
check("3.2 P1 : la ligne est rendue par Réglages › Clés d'API (Fu.concat(dzFuNeuves()))", "Fu.concat(dzFuNeuves())" in B)
PC = tranche(B, "function DzPostComptes(", "return r.jsxs(")
check("3.3 P2 : DzPostComptes écarte plateforme==='whatsapp' de la liste rangée",
      'filter(function(c){return c.plateforme!=="whatsapp"})' in PC, PC[:400])
TABLE = tranche(B, "const _t={", "Bu=")
check("3.4 whatsapp n'est PAS une cible du Planificateur (table des canaux _t)", bool(TABLE) and "whatsapp" not in TABLE)

ECRANS = tranche(B, "function dzEspEnvoyer(", "function dzEspSignal(") + "\n" + tranche(B, "function DzComptesEspace(", "var DZ_ONB_ETAPES=")
SONDE_POST = r"""
function cpt(id,p){return{id:id,espace_id:"esp_c",plateforme:p,libelle:"Compte "+id,handle:"",historique:false,oauth:false,disponible:true,verification:null,canal_id:null,champs:[]}}
globalThis.fetch=function(u){
  if(u.indexOf("/api/comptes?espace=")===0)return Promise.resolve({ok:true,status:200,json:function(){return Promise.resolve({espace:"esp_c",
    comptes:[cpt("c_tg","telegram"),cpt("c_wa","whatsapp"),cpt("c_x","x")],plateformes:{telegram:{libelle:"Telegram"},whatsapp:{libelle:"WhatsApp"},x:{libelle:"X"}}})}});
  return Promise.resolve({ok:false,status:404,json:function(){return Promise.resolve({})}})};
__SCRIPT__
__ECRANS__
var R={};
(async function(){
 /* P3 : Réglages › Espaces (DzComptesEspace livrée) */
 monter(DzComptesEspace,{espace:"esp_c",nom:"Client C"});await attendre();
 var sel=chercher(function(n){return n.t==="select"})[0];
 R.options=sel?kids(sel).map(function(o){return o.p.value}):null;
 function boutons(id){var b=avec("data-dz-compte",id)[0];return b?chercher(function(n){return n.t==="button"},b).map(texte):null}
 R.bt_wa=boutons("c_wa");R.bt_tg=boutons("c_tg");
 R.indice_wa=texte(avec("data-dz-compte-whatsapp","c_wa")[0]||null);R.indice_tg=avec("data-dz-compte-whatsapp","c_tg").length;
 R.inputs_wa=(function(){var b=avec("data-dz-compte","c_wa")[0];return b?chercher(function(n){return n.t==="input"},b).length:-1})();
 var changes=[];
 monter(DzPostComptes,{post:{id:"p1",espaceId:"esp_c",comptes:[]},onChange:function(v){changes.push(v)}});await attendre();
 R.proposes=avec("data-dz-post-compte").map(function(n){return n.p["data-dz-post-compte"]});
 R.texte=texte(arbre);
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
P3 = {}
if NODE and ECRANS.strip():
    P3 = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + FAUX_REACT
              + SONDE_POST.replace("__SCRIPT__", ASSISTANT.read_text("utf-8")).replace("__ECRANS__", ECRANS))
check("3.5 la fonction livrée DzPostComptes s'exécute sous node", bool(P3) and "erreur" not in P3, str(P3.get("erreur", ""))[:800])
if P3 and "erreur" not in P3:
    check("3.6 P2 : l'éditeur de post propose telegram et x, jamais le compte whatsapp",
          sorted(P3["proposes"]) == ["c_tg", "c_x"] and "c_wa" not in P3["texte"], str(P3["proposes"]))
    check("3.7 P3a : Réglages › Espaces, « Ajouter un compte » ne propose pas whatsapp",
          P3["options"] is not None and "whatsapp" not in P3["options"] and {"telegram", "x"} <= set(P3["options"]), str(P3["options"]))
    check("3.8 P3b : un compte whatsapp n'a ni « Identifiants » ni « Tester », aucun champ, mais « Vérifier » et « Supprimer » ; telegram garde tout",
          P3["bt_wa"] is not None and F("espaces.comptes.identifiants") not in P3["bt_wa"]
          and F("espaces.comptes.tester") not in P3["bt_wa"] and P3["inputs_wa"] == 0
          and F("espaces.comptes.verifier") in P3["bt_wa"] and F("espaces.comptes.supprimer") in P3["bt_wa"]
          and F("espaces.comptes.identifiants") in P3["bt_tg"] and F("espaces.comptes.tester") in P3["bt_tg"],
          str([P3["bt_wa"], P3["bt_tg"], P3["inputs_wa"]]))
    check("3.9 P3c : à la place, la ligne en lecture seule « relié par l'assistant d'espace » (whatsapp seulement)",
          P3["indice_wa"] == F("espaces.comptes.whatsapp_assistant") and P3["indice_tg"] == 0, str(P3["indice_wa"]))

# ── [4] le panneau de liaison ───────────────────────────────────────────────────────────────────────────────────────
print("\n[4] le panneau de liaison, sous node")
HARNAIS = r"""
var appels=[],ESP_ID="esp_new";
var PLATS={telegram:{libelle:"Telegram",champs:[{nom:"TELEGRAM_BOT_TOKEN",secret:true},{nom:"TELEGRAM_CHAT_ID",secret:false}],requis:["TELEGRAM_BOT_TOKEN"],oauth:false},
  whatsapp:{libelle:"WhatsApp",champs:[{nom:"KAPSO_CUSTOMER_ID",secret:false},{nom:"WHATSAPP_PHONE_ID",secret:false},{nom:"WHATSAPP_NUMERO",secret:false},
    {nom:"WHATSAPP_WABA_ID",secret:false},{nom:"WHATSAPP_FACTURATION_META",secret:false}],requis:["WHATSAPP_PHONE_ID"],oauth:false}};
function cptWa(posee,fact){return{id:"cwa000001",espace_id:ESP_ID,plateforme:"whatsapp",libelle:"WhatsApp",handle:"",historique:false,oauth:false,disponible:false,verification:null,canal_id:null,
  cle_plate:{nom:"KAPSO_API_KEY",posee:posee},
  champs:[{nom:"KAPSO_CUSTOMER_ID",secret:false,pose:false,valeur:""},{nom:"WHATSAPP_PHONE_ID",secret:false,pose:false,valeur:""},{nom:"WHATSAPP_NUMERO",secret:false,pose:false,valeur:""},
    {nom:"WHATSAPP_WABA_ID",secret:false,pose:false,valeur:""},{nom:"WHATSAPP_FACTURATION_META",secret:false,pose:!!fact,valeur:fact||""}]}}
var COMPTES=[],POSEE=true,FACT="",LIAISON={etat:"aucune",erreur:null,numero:null},LIEN_REP=null,VERIF_LIAISON=null;
function rep(st,d){return Promise.resolve({ok:st<300,status:st,json:function(){return Promise.resolve(d)}})}
globalThis.fetch=function(u,o){var m=(o&&o.method)||"GET",b=o&&o.body?JSON.parse(o.body):null;appels.push({u:u,m:m,b:b});
  if(u==="/api/espaces"&&m==="GET")return rep(200,{espaces:[{id:"esp_m",nom:"Marque M",type:"marque"},{id:"esp_c",nom:"Client C",type:"client"}],actif:"deepotus"});
  if(u==="/api/brand-kits")return rep(200,{kits:[]});
  if(u==="/api/espaces"&&m==="POST")return rep(200,{espace:Object.assign({id:ESP_ID},b)});
  if(u==="/api/espaces/"+ESP_ID&&m==="POST")return rep(200,{espace:Object.assign({id:ESP_ID},b)});
  if(u==="/api/espaces/"+ESP_ID+"/client"&&m==="PUT")return rep(200,Object.assign({version:1},b));
  if(u.indexOf("/api/comptes?espace=")===0)return rep(200,{espace:ESP_ID,comptes:COMPTES,plateformes:platsAvecCle()});
  if(u==="/api/comptes"&&m==="POST")return rep(200,{compte:cptWa(POSEE,FACT)});
  if(u==="/api/comptes/cwa000001/whatsapp/lien"&&m==="POST")return LIEN_REP?rep(LIEN_REP[0],LIEN_REP[1]):rep(200,{url:"https://app.kapso.ai/setup/abc",expire_le:"2026-11-26T10:00:00Z",facturation:b.facturation});
  if(u==="/api/comptes/cwa000001/whatsapp/liaison"&&m==="GET")return rep(200,LIAISON);
  if(u==="/api/comptes/cwa000001/verifier"&&m==="POST"){if(VERIF_LIAISON)LIAISON=VERIF_LIAISON;return rep(200,{compte:Object.assign(cptWa(POSEE,FACT),{verification:{etat:"orange",code:"liaison_en_cours",raison:"en cours",date:"2026-10-27T10:00:00"}})})}
  return rep(404,{detail:"route inconnue du faux serveur : "+m+" "+u})};
function platsAvecCle(){var p=JSON.parse(JSON.stringify(PLATS));p.whatsapp.cle_plate={nom:"KAPSO_API_KEY",posee:POSEE};return p}
var COPIES=[];
Object.defineProperty(globalThis,"navigator",{value:{clipboard:{writeText:function(t){COPIES.push(t);return Promise.resolve()}}},configurable:true});
__SCRIPT__
function attendre(){return new Promise(function(ok){setTimeout(ok,25)})}
function voile(){return tous(body,function(n){return n.getAttribute("data-dz-assistant")!==null})[0]||null}
function etape(){var v=voile();return v?v.getAttribute("data-etape"):null}
function par(attr,val){var v=voile();return v?tous(v,function(n){return n.getAttribute(attr)!==null&&(val===undefined||n.getAttribute(attr)===val)}):[]}
function un(attr,val){return par(attr,val)[0]||null}
function saisir(cle,val){var n=un("data-dz-assistant-champ",cle);n.value=val;n.declencher(n.tagName==="SELECT"?"change":"input")}
function compte(m,u){return appels.filter(function(a){return a.m===m&&a.u===u}).length}
var INPUTS=[];
function relever(){var v=voile();if(!v)return;tous(v,function(n){return n.tagName==="INPUT"||n.tagName==="SELECT"||n.tagName==="TEXTAREA"}).forEach(function(n){
  INPUTS.push([n.getAttribute("name")||n.name||"",n.getAttribute("aria-label")||"",n.getAttribute("data-dz-assistant-cle")||"",n.getAttribute("data-dz-assistant-champ")||""])})}
async function jusquaCanaux(type,parent){var p=window.__dzEspaceAssistant.ouvrir();await attendre();saisir("nom","Espace WA");saisir("type",type);await attendre();
  if(parent){saisir("parent",parent);}
  un("data-dz-assistant-suivant").declencher("click");await attendre();
  if(etape()==="2"){un("data-dz-assistant-suivant").declencher("click");await attendre();}
  return {p:p}}
function fermer(){var a=un("data-dz-assistant-annuler");if(a)a.declencher("click");var pan=un("data-dz-assistant-annuler-cree");if(pan)tous(pan,function(n){return n.tagName==="BUTTON"})[0].declencher("click")}
var R={};
(async function(){
 /* A : une marque, compte whatsapp existant, clé Kapso ABSENTE : le message seul */
 COMPTES=[cptWa(false,"")];POSEE=false;
 var pA=await jusquaCanaux("marque");R.a_etape=etape();
 var msg=un("data-dz-assistant-whatsapp-cle");R.a_msg=msg&&msg.textContent;
 R.a_creer=!!un("data-dz-assistant-whatsapp-creer");R.a_fact=par("data-dz-assistant-whatsapp-facturation").length;
 R.a_cons=!!un("data-dz-assistant-whatsapp-moyen");R.a_liaison=compte("GET","/api/comptes/cwa000001/whatsapp/liaison");
 R.a_champs=par("data-dz-assistant-cle").length;relever();fermer();await pA.p;
 /* B : un CLIENT, clé posée, AUCUN compte : cocher ne crée RIEN (la clé se lit sur plateformes), le consentement est exigé ;
    « Créer le lien » crée alors le compte (une fois) puis le lien */
 appels=[];COMPTES=[];POSEE=true;FACT="";LIAISON={etat:"aucune",erreur:null,numero:null};
 var pB=await jusquaCanaux("client");R.b_etape=etape();
 R.b_avant=!!un("data-dz-assistant-whatsapp");
 var caseW=un("data-dz-assistant-case","whatsapp");caseW.checked=true;caseW.declencher("change");await attendre();await attendre();
 R.b_posts_coche=compte("POST","/api/comptes");R.b_case_libre=!(un("data-dz-assistant-case","whatsapp")||{}).disabled;
 R.b_liaison=compte("GET","/api/comptes/cwa000001/whatsapp/liaison");
 R.b_champs=par("data-dz-assistant-cle").length;
 var fact=par("data-dz-assistant-whatsapp-facturation");R.b_fact=fact.map(function(n){return [n.getAttribute("data-dz-assistant-whatsapp-facturation"),n.type,!!n.checked,!!n.disabled]});
 R.b_fact_aide=(un("data-dz-assistant-whatsapp-facturation-aide")||{}).textContent;
 var cr=un("data-dz-assistant-whatsapp-creer");R.b_creer_grise=!!(cr&&cr.disabled);R.b_creer_txt=cr&&cr.textContent;
 cr.declencher("click");await attendre();R.b_lien_sans_cons=compte("POST","/api/comptes/cwa000001/whatsapp/lien");
 var mo=un("data-dz-assistant-whatsapp-moyen"),da=un("data-dz-assistant-whatsapp-date");
 R.b_moyens=mo?tous(mo,function(n){return n.tagName==="OPTION"}).map(function(n){return n.value}):null;R.b_date_type=da&&da.type;
 mo.value="whatsapp";mo.declencher("change");R.b_grise_moitie=!!un("data-dz-assistant-whatsapp-creer").disabled;
 da=un("data-dz-assistant-whatsapp-date");da.value="2026-10-27";da.declencher("input");
 cr=un("data-dz-assistant-whatsapp-creer");R.b_creer_libre=!cr.disabled;relever();
 cr.declencher("click");cr.declencher("click");await attendre();await attendre();
 var li=appels.filter(function(a){return a.m==="POST"&&a.u==="/api/comptes/cwa000001/whatsapp/lien"});R.b_liens=li.length;R.b_corps=(li[0]||{}).b;
 var url=un("data-dz-assistant-whatsapp-url");R.b_url=url&&[url.tagName,url.value,!!url.readOnly];
 R.b_expire=(un("data-dz-assistant-whatsapp-expire")||{}).textContent;
 R.b_creer_apres=!!un("data-dz-assistant-whatsapp-creer");
 R.b_cree=(appels.filter(function(a){return a.m==="POST"&&a.u==="/api/comptes"})[0]||{}).b;R.b_posts=compte("POST","/api/comptes");
 var iC=-1,iLi=-1;appels.forEach(function(a,i){if(a.m==="POST"&&a.u==="/api/comptes"&&iC<0)iC=i;if(a.u==="/api/comptes/cwa000001/whatsapp/lien"&&iLi<0)iLi=i});R.b_ordre_cree=[iC,iLi];
 R.b_case_apres=!!(un("data-dz-assistant-case","whatsapp")||{}).disabled;
 var cp=un("data-dz-assistant-whatsapp-copier");R.b_copier=cp&&cp.textContent;cp.declencher("click");await attendre();R.b_copies=COPIES.slice();
 relever();
 /* « Vérifier » : /verifier PUIS GET …/liaison ; la liaison terminée montre le numéro */
 VERIF_LIAISON={etat:"terminee",erreur:null,numero:{phone_number_id:"pn_1",display_phone_number:"+33 6 12 34 56 78",business_account_id:"waba_1"}};
 var nGet=compte("GET","/api/comptes/cwa000001/whatsapp/liaison");
 un("data-dz-assistant-verifier","whatsapp").declencher("click");await attendre();await attendre();
 var iV=-1,iL=-1;appels.forEach(function(a,i){if(a.u==="/api/comptes/cwa000001/verifier")iV=i;if(a.u==="/api/comptes/cwa000001/whatsapp/liaison"&&a.m==="GET")iL=i});
 R.b_ordre=[iV,iL];R.b_relues=compte("GET","/api/comptes/cwa000001/whatsapp/liaison")-nGet;
 var et=un("data-dz-assistant-whatsapp-etat");R.b_etat=et&&[et.getAttribute("data-etat"),et.textContent];
 R.b_creer_fini=!!un("data-dz-assistant-whatsapp-creer");
 relever();fermer();await pB.p;
 /* C : une marque, clé posée, facturation DÉJÀ posée (partner_managed) : aucun consentement, la facturation imposée */
 appels=[];COMPTES=[cptWa(true,"partner_managed")];POSEE=true;FACT="partner_managed";VERIF_LIAISON=null;
 LIAISON={etat:"expiree",erreur:"lien d'installation expiré",numero:null,code:"expire"};
 var pC=await jusquaCanaux("marque");await attendre();
 R.c_cons=!!un("data-dz-assistant-whatsapp-moyen");
 R.c_fact=par("data-dz-assistant-whatsapp-facturation").map(function(n){return [n.getAttribute("data-dz-assistant-whatsapp-facturation"),!!n.checked,!!n.disabled]});
 var etC=un("data-dz-assistant-whatsapp-etat");R.c_etat=etC&&[etC.getAttribute("data-etat"),etC.textContent];
 var crC=un("data-dz-assistant-whatsapp-creer");R.c_libre=!!crC&&!crC.disabled;
 crC.declencher("click");await attendre();
 R.c_corps=(appels.filter(function(a){return a.m==="POST"&&a.u==="/api/comptes/cwa000001/whatsapp/lien"})[0]||{}).b;
 relever();fermer();await pC.p;
 /* D : codes de liaison et refus structuré (502 {message, code}) lisible */
 appels=[];COMPTES=[cptWa(true,"")];FACT="";
 LIAISON={etat:"echouee",erreur:"ce numéro est déjà relié à l'espace Client Z",numero:null,code:"numero_deja_relie",espace:"Client Z"};
 var pD=await jusquaCanaux("marque");await attendre();
 var etD=un("data-dz-assistant-whatsapp-etat");R.d_deja=etD&&etD.textContent;fermer();await pD.p;
 LIAISON={etat:"echouee",erreur:"Meta refused the WABA",numero:null,code:"fournisseur"};
 var pD2=await jusquaCanaux("marque");await attendre();
 var etD2=un("data-dz-assistant-whatsapp-etat");R.d_fourn=etD2&&etD2.textContent;
 var brut=un("data-dz-assistant-whatsapp-erreur");R.d_brut=brut&&[brut.textContent,brut.getAttribute("data-dz-brut")];
 LIEN_REP=[502,{detail:{message:"insufficient_credits: top up",code:"insufficient_credits"}}];
 un("data-dz-assistant-whatsapp-creer").declencher("click");await attendre();await attendre();
 R.d_refus=(un("data-dz-assistant-whatsapp-msg")||{}).textContent;R.d_creer_rendu=!!un("data-dz-assistant-whatsapp-creer")&&!un("data-dz-assistant-whatsapp-creer").disabled;
 LIEN_REP=null;relever();fermer();await pD2.p;
 /* E : un PRODUIT dont le parent est un client est gouverné par lui : le consentement est demandé */
 /* F : une marque, clé ABSENTE, aucun compte : le message seul (lu sur plateformes) ; cocher puis décocher avant toute
    action ne laisse rien ; « Suivant » n'écrit aucun compte whatsapp */
 appels=[];COMPTES=[];POSEE=false;
 var pF=await jusquaCanaux("marque");var cF=un("data-dz-assistant-case","whatsapp");cF.checked=true;cF.declencher("change");await attendre();
 R.f_msg=(un("data-dz-assistant-whatsapp-cle")||{}).textContent;R.f_creer=!!un("data-dz-assistant-whatsapp-creer");
 cF=un("data-dz-assistant-case","whatsapp");cF.checked=false;cF.declencher("change");await attendre();
 R.f_panneau=!!un("data-dz-assistant-whatsapp");
 un("data-dz-assistant-suivant").declencher("click");await attendre();await attendre();
 R.f_etape=etape();R.f_posts=compte("POST","/api/comptes");relever();fermer();await pF.p;POSEE=true;
 appels=[];COMPTES=[cptWa(true,"")];LIAISON={etat:"aucune",erreur:null,numero:null};
 var pE=await jusquaCanaux("produit","esp_c");await attendre();R.e_etape=etape();
 R.e_cons=!!un("data-dz-assistant-whatsapp-moyen")&&!!un("data-dz-assistant-whatsapp-date");
 R.e_grise=!!(un("data-dz-assistant-whatsapp-creer")||{}).disabled;relever();fermer();await pE.p;
 R.inputs=INPUTS;
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
R = {}
if NODE and ASSISTANT.is_file():
    R = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + HARNAIS.replace("__SCRIPT__", ASSISTANT.read_text("utf-8")))
check("4.0 le script s'exécute sous node", bool(R) and "erreur" not in R, str(R.get("erreur", ""))[:800])
F = AIDE.fr
if R and "erreur" not in R:
    check("4.1 sans clé Kapso : le message « clé Kapso à saisir dans Réglages › Clés d'API », et rien d'autre",
          R["a_etape"] == "3" and R["a_msg"] == F("espaces.assistant.whatsapp_cle_absente") and not R["a_creer"]
          and R["a_fact"] == 0 and not R["a_cons"] and R["a_liaison"] == 0 and R["a_champs"] == 0,
          str([R["a_msg"], R["a_creer"], R["a_fact"], R["a_cons"], R["a_liaison"]]))
    check("4.2 cocher WhatsApp ne crée RIEN (aucun POST /api/comptes, aucune relecture), la case reste décochable",
          not R["b_avant"] and R["b_posts_coche"] == 0 and R["b_liaison"] == 0 and R["b_case_libre"],
          str([R["b_posts_coche"], R["b_liaison"], R["b_case_libre"]]))
    check("4.2b « Créer le lien » crée le compte SANS valeur (une fois) PUIS le lien ; la case se fige ensuite",
          R["b_cree"] == {"espace_id": "esp_new", "plateforme": "whatsapp"} and R["b_posts"] == 1
          and 0 <= R["b_ordre_cree"][0] < R["b_ordre_cree"][1] and R["b_case_apres"],
          str([R["b_cree"], R["b_posts"], R["b_ordre_cree"], R["b_case_apres"]]))
    check("4.17 sans compte et sans clé (plateformes.whatsapp.cle_plate) : le message seul ; décocher avant toute action ne laisse rien",
          R["f_msg"] == F("espaces.assistant.whatsapp_cle_absente") and not R["f_creer"] and not R["f_panneau"]
          and R["f_etape"] == "4" and R["f_posts"] == 0, str([R["f_msg"], R["f_creer"], R["f_panneau"], R["f_etape"], R["f_posts"]]))
    check("4.3 aucun champ générique pour whatsapp (panneauWhatsapp remplace champsDe)", R["b_champs"] == 0, str(R["b_champs"]))
    check("4.4 facturation Meta : deux radios, customer_managed cochée par défaut ; l'aide dit que le choix est définitif",
          R["b_fact"] == [["customer_managed", "radio", True, False], ["partner_managed", "radio", False, False]]
          and R["b_fact_aide"] == F("espaces.assistant.whatsapp_facturation_aide"), str([R["b_fact"], R["b_fact_aide"]]))
    check("4.5 espace client sans consentement : « Créer le lien » grisé, un clic n'envoie rien",
          R["b_creer_grise"] and R["b_creer_txt"] == F("espaces.assistant.whatsapp_creer") and R["b_lien_sans_cons"] == 0,
          str([R["b_creer_grise"], R["b_lien_sans_cons"]]))
    check("4.6 le consentement : moyen (écrit, WhatsApp, au doigt) et date ; le bouton reste grisé tant qu'il manque l'un des deux",
          R["b_moyens"] == ["", "ecrit", "whatsapp", "doigt"] and R["b_date_type"] == "date" and R["b_grise_moitie"]
          and R["b_creer_libre"], str([R["b_moyens"], R["b_date_type"], R["b_grise_moitie"], R["b_creer_libre"]]))
    check("4.7 le clic envoie POST …/whatsapp/lien UNE fois (double clic) avec la facturation cochée et le consentement daté",
          R["b_liens"] == 1 and R["b_corps"] == {"facturation": "customer_managed",
                                                  "consentement": {"moyen": "whatsapp", "date": "2026-10-27"}}, str([R["b_liens"], R["b_corps"]]))
    check("4.8 puis l'URL en lecture seule, « Copier » (presse-papiers) et l'expiration ; plus de second lien proposé",
          R["b_url"] == ["INPUT", "https://app.kapso.ai/setup/abc", True] and R["b_copier"] == F("espaces.assistant.whatsapp_copier")
          and R["b_copies"] == ["https://app.kapso.ai/setup/abc"]
          and R["b_expire"] == F("espaces.assistant.whatsapp_expire_le", date="2026-11-26 10:00") and not R["b_creer_apres"],
          str([R["b_url"], R["b_copier"], R["b_copies"], R["b_expire"], R["b_creer_apres"]]))
    check("4.9 « Vérifier » appelle /verifier PUIS relit la liaison (GET …/liaison) ; terminée : le numéro, plus de lien",
          0 <= R["b_ordre"][0] < R["b_ordre"][1] and R["b_relues"] == 1
          and R["b_etat"] == ["terminee", F("espaces.assistant.whatsapp_liaison_terminee", numero="+33 6 12 34 56 78")]
          and not R["b_creer_fini"], str([R["b_ordre"], R["b_relues"], R["b_etat"]]))
    check("4.10 une marque : aucun consentement ; la facturation déjà posée est imposée (l'autre grisée)",
          not R["c_cons"] and R["c_fact"] == [["customer_managed", False, True], ["partner_managed", True, False]],
          str([R["c_cons"], R["c_fact"]]))
    check("4.11 lien expiré : le code traduit, un nouveau lien possible, sans consentement dans le corps",
          R["c_etat"] == ["expiree", F("espaces.assistant.liaison_expire")] and R["c_libre"]
          and R["c_corps"] == {"facturation": "partner_managed"}, str([R["c_etat"], R["c_corps"]]))
    check("4.12 numéro déjà relié : le code traduit avec le nom de l'espace",
          R["d_deja"] == F("espaces.assistant.liaison_numero_deja_relie", espace="Client Z"), str(R["d_deja"]))
    check("4.13 échec chez le fournisseur : le code traduit, le texte brut (nettoyé par le serveur) marqué data-dz-brut",
          (R["d_fourn"] or "").startswith(F("espaces.assistant.liaison_fournisseur"))
          and R["d_brut"] == ["Meta refused the WABA", "1"], str([R["d_fourn"], R["d_brut"]]))
    check("4.14 un refus structuré (502 {message, code}) se lit en clair, jamais « [object Object] » ; le bouton revient",
          "insufficient_credits: top up" in (R["d_refus"] or "") and "[object Object]" not in (R["d_refus"] or "")
          and R["d_creer_rendu"], str(R["d_refus"]))
    check("4.15 un PRODUIT d'un client est gouverné par lui : moyen et date demandés, bouton grisé",
          R["e_etape"] == "3" and R["e_cons"] and R["e_grise"], str([R["e_etape"], R["e_cons"], R["e_grise"]]))
    mauvais = [i for i in R["inputs"] if any(c in v for v in i for c in CHAMPS_WA)]
    check("4.16 aucun <input>/<select> n'a pour nom (name, aria-label, data-dz-assistant-cle) un champ whatsapp ni KAPSO_API_KEY",
          len(R["inputs"]) > 5 and not mauvais, str(mauvais[:3]))

# ── [5] la boîte des canaux d'un projet ─────────────────────────────────────────────────────────────────────────────
print("\n[5] la boîte des canaux d'un projet")
SONDE_CANAUX = r"""
globalThis.fetch=function(u){return Promise.resolve({ok:true,status:200,json:function(){return Promise.resolve({espace:"esp_a",
  comptes:[{id:"c_tg",espace_id:"esp_a",plateforme:"telegram"},{id:"c_wa",espace_id:"esp_a",plateforme:"whatsapp"},{id:"c_b",espace_id:"esp_b",plateforme:"x"}]})}})};
globalThis.MutationObserver=function(){this.observe=function(){};this.disconnect=function(){}};
__SCRIPT__
(async function(){var l=await window.__dzProjetCanaux.comptes("esp_a");
 process.stdout.write(JSON.stringify({ids:l.map(function(c){return c.id}),connus:(window.__dzProjetCanaux.connus("esp_a")||[]).map(function(c){return c.id})}))
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
P5 = {}
if NODE and CANAUX.is_file():
    P5 = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + SONDE_CANAUX.replace("__SCRIPT__", CANAUX.read_text("utf-8")))
check("5.0 dz-projet-canaux.js s'exécute sous node", bool(P5) and "erreur" not in P5, str(P5.get("erreur", ""))[:800])
if P5 and "erreur" not in P5:
    check("5.1 comptes(espace) exclut plateforme === 'whatsapp' (et garde le filtre d'espace)",
          P5["ids"] == ["c_tg"] and P5["connus"] == ["c_tg"], str(P5))

# ── [6] textes ──────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[6] textes et copies")
TXT = ASSISTANT.read_text("utf-8")
cles = set(re.findall(r'"((?:espaces|commun|reglages|projets)\.[a-z_]+\.[a-z_.]+)"', TXT))
cles = {k for k in cles if not k.endswith((".", "_"))} | {"reglages.cles.kapso", "reglages.cles.kapso_why",
                                                         "espaces.comptes.whatsapp_assistant"}
NEUVES = ("espaces.assistant.whatsapp_cle_absente", "espaces.assistant.whatsapp_creer", "espaces.assistant.whatsapp_copier",
          "espaces.assistant.whatsapp_expire_le", "espaces.assistant.whatsapp_facturation_aide",
          "espaces.assistant.whatsapp_liaison_terminee", "espaces.assistant.liaison_numero_deja_relie",
          "espaces.assistant.liaison_fournisseur", "espaces.assistant.liaison_expire")


def vars_(t):
    return sorted(re.findall(r"\{(\w+)\}", t or ""))


manque = [k for k in cles | set(NEUVES) if not (AIDE.DICO.get(k, {}).get("fr", "").strip() and AIDE.DICO.get(k, {}).get("en", "").strip()
                                               and vars_(AIDE.DICO[k]["fr"]) == vars_(AIDE.DICO[k]["en"]))]
check("6.1 chaque clé dzT employée (assistant + ligne de clé) existe en FR et en EN, mêmes {variables}", not manque, str(manque))
check("6.2 les variables attendues : {espace} pour le numéro déjà relié, {date} pour l'expiration, {numero} une fois relié",
      vars_(AIDE.DICO.get("espaces.assistant.liaison_numero_deja_relie", {}).get("fr")) == ["espace"]
      and vars_(AIDE.DICO.get("espaces.assistant.whatsapp_expire_le", {}).get("fr")) == ["date"]
      and vars_(AIDE.DICO.get("espaces.assistant.whatsapp_liaison_terminee", {}).get("fr")) == ["numero"])
# reglages.json est réécrit par scripts/i18n_l1_generer.py : les lignes neuves de Réglages vivent dans menus.json (t221)
check("6.2b le texte « fournisseur » sans deux-points pendant ; la facturation partenaire dit qu'elle s'active chez Kapso",
      not AIDE.DICO.get("espaces.assistant.liaison_fournisseur", {}).get("fr", ":").rstrip().endswith(":")
      and not AIDE.DICO.get("espaces.assistant.liaison_fournisseur", {}).get("en", ":").rstrip().endswith(":")
      and "chez Kapso" in AIDE.DICO.get("espaces.assistant.whatsapp_facturation_kapso", {}).get("fr", "")
      and "at Kapso" in AIDE.DICO.get("espaces.assistant.whatsapp_facturation_kapso", {}).get("en", ""))
check("6.3 les clés de la ligne Kapso vivent dans menus.json, à côté de reglages.cles.decart (jamais dans reglages.json, généré)",
      lambda: {"reglages.cles.kapso", "reglages.cles.kapso_why", "reglages.cles.decart"}
      <= set(json.loads((SH / "i18n" / "menus.json").read_text("utf-8")))
      and not {"reglages.cles.kapso", "reglages.cles.kapso_why"} & set(json.loads((SH / "i18n" / "reglages.json").read_text("utf-8"))))
check("6.4 l'assemblé dz-i18n-dico.js est à jour", lambda: subprocess.run(
    [sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True).returncode == 0)
check("6.5 copies dist OCTET POUR OCTET (assistant, boîte des canaux)",
      lambda: all((SH / n).read_bytes() == (DI / n).read_bytes() for n in ("dz-espace-assistant.js", "dz-projet-canaux.js")))
check("6.6 aucun emoji, aucun innerHTML d'une donnée dans le panneau",
      lambda: not re.search("[\U0001F300-\U0001FAFF☀-➿✓✗]", TXT)
      and all("icone(" in l or "innerHTML = \"\"" in l for l in TXT.splitlines() if "innerHTML" in l
              and not l.strip().startswith(("/*", "*"))))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
