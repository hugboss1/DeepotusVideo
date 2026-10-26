# -*- coding: utf-8 -*-
"""t308 tâche 4 (26/10/2026) — l'ASSISTANT de création d'espace en quatre temps, à l'écran.

Plan docs/superpowers/plans/2026-10-26-t308-assistant-espace.md (tâche 4), spec 2026-10-25-boite-a-outils-design.md §5.3.
L'assistant vit dans frontend/shared/dz-espace-assistant.js (window.__dzEspaceAssistant) ; le maillon de QUEUE
scripts/patch_bundle_dzassistant.py fait seulement que « Créer l'espace » de Réglages › Espaces (DzEspaces, sortie du
maillon dzespace, HORS de tout bloc de couche) ouvre l'assistant. Son inverse `avant_dzassistant`
(backend/tests/_i18n_l1_aide.py) est appelé EN TÊTE de `avant_dzagentplan`.
[1] le maillon      marqueur x1, aucun .bak_dzassistant, --check « déjà appliqué », chaque ancre unique (vue d'avant) ;
[2] réversible      defaire(B) puis appliquer == B, avant_dzassistant == defaire, avant_dzagentplan le défait d'abord ;
[3] comptes figés   x.useState( 731, v2.8.0 ×4, DzTracks 181, confirmations ×30, CRLF en octets, node --check ;
[4] le script       copie dist identique, balise dans la SPA après dz-projet-canaux.js, ni emoji ni alert/confirm ;
[5] sous node       (faux DOM, faux fetch) : l'étape 2 sautée pour une marque ; « Suivant » crée l'espace UNE fois (deux
                    clics → un POST ; au retour, il modifie) ; la fiche d'un client par PUT …/client ; un secret jamais
                    prérempli depuis une réponse ; « Vérifier » appelle /verifier et montre l'état traduit (la raison brute
                    au survol seulement) ; le récapitulatif dit le consentement manquant ; « Terminer » active, émet
                    dz-espace-cree et ferme ;
[6] textes          clés espaces.assistant.* FR et EN, toutes employées, aucune orpheline, assemblées ;
[7] la paire        le formulaire de DzEspaces (data-dz-espace-nouveau, lu par la scène du guide t211) ouvre l'assistant.
t308 tâche 5 (26/10/2026) — l'état de vérification dans Réglages › Espaces et au Planificateur :
[8] la pastille     window.__dzEspaceAssistant.pastille(vue) pour les quatre états (glyphe, couleur, texte traduit, survol
                    « vérifié le … : raison » ou « non vérifié ») ; verifier(id) n'envoie qu'UN appel à la fois par compte
                    (enCours), libéré aussi sur échec ;
[9] les écrans      sous node (faux React, faux fetch), les fonctions LIVRÉES du bundle : DzComptesEspace montre la pastille
                    et « Vérifier » (route appelée une fois malgré le double clic, bouton grisé, libéré sur échec, liste
                    relue) ; DzPostComptes dit « non vérifié » (ou l'état) d'un compte COCHÉ pas vert, rien pour un vert, et
                    ne bloque rien (signal seulement : les règles client sont t309) ; cibles hors couche.
Run : & $PY tests/test_espace_assistant_ecran.py   (depuis backend/)
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import _i18n_l1_aide as AIDE  # noqa: E402

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
SHARED = REPO / "frontend" / "shared" / "dz-espace-assistant.js"
DIST = REPO / "frontend" / "dist" / "shared" / "dz-espace-assistant.js"
DICO_P = REPO / "frontend" / "shared" / "i18n" / "espaces.json"
MARKER = "/*__dzassistant*/"
CONFIRMER = "await window.__dzDialogue.confirmer("

print("\n[1] le maillon")
try:
    import patch_bundle_dzassistant as PM               # noqa: E402
except Exception as e:                                  # noqa: BLE001
    PM = None
    check("1.0 le maillon patch_bundle_dzassistant existe", False, repr(e))
check("1.1 le marqueur une fois dans le bundle", B.count(MARKER) == 1, str(B.count(MARKER)))
check("1.2 aucun .bak_dzassistant laissé", not list(ASSETS.glob("*.bak_dzassistant")))
if PM:
    src = (REPO / "scripts" / "patch_bundle_dzassistant.py").read_text("utf-8")
    check("1.3 lecture et écriture en OCTETS", "read_text(" not in src and "write_text(" not in src)
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzassistant.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("1.4 --check : « déjà appliqué », bundle inchangé", r.returncode == 0 and "déjà appliqué" in r.stdout
          and BUNDLE.read_bytes() == RAW, r.stdout + r.stderr)
    avant = PM.defaire(B) if MARKER in B else ""
    check("1.5 chaque ancre une fois dans le bundle d'avant le maillon, chaque remplacement une fois dans le livré",
          lambda: all(avant.count(a) == 1 and B.count(z) == 1 for a, z in PM.PAIRES), "")
    check("1.6 les paires n'ont aucune fin de ligne ; P1 garde le formulaire rapide entier derrière le crochet (repli)",
          all("\n" not in a + z for a, z in PM.PAIRES)
          and PM.PAIRES[0][0].split("{ev.preventDefault();")[1] in PM.PAIRES[0][1])
    check("1.7 la cible (DzEspaces) est HORS de tout bloc de couche __DZ_*_BEGIN__",
          lambda: all(not (s0 <= B.index(MARKER) <= e0) for s0, e0 in
                      [(m.start(), B.index("/*__DZ_%s_END__*/" % m.group(1))) for m in
                       re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", B)]))

print("\n[2] réversible")
if PM and MARKER in B:
    check("2.1 appliquer(defaire(B)) == B", lambda: PM.appliquer(PM.defaire(B)) == B)
    check("2.2 avant_dzassistant existe et rend defaire(B)", lambda: AIDE.avant_dzassistant(B) == PM.defaire(B))
    check("2.3 avant_dzagentplan défait dzassistant d'abord",
          lambda: MARKER not in AIDE.avant_dzagentplan(B) and "/*__dzagentplan*/" not in AIDE.avant_dzagentplan(B))
    check("2.4 avant_dzassistant sans marqueur : rendu tel quel",
          lambda: AIDE.avant_dzassistant(PM.defaire(B)) == PM.defaire(B))
    check("2.5 la chaîne d'inverses reste complète (avant_dzespace retire l'écran des espaces)",
          lambda: "function DzEspaceSel(" not in AIDE.avant_dzespace(B))
    check("2.6 CRLF préservé par l'aller-retour (en octets)",
          lambda: PM.defaire(B).encode("utf-8").count(b"\n") == PM.defaire(B).encode("utf-8").count(b"\r\n"))

print("\n[3] comptes figés")
for jeton, n in {"x.useState(": 731, "v2.8.0": 4, "DzTracks": 181, CONFIRMER: 30, "/*__dzagentplan*/": 1,
                 "function DzEspaces(": 1, "function DzComptesEspace(": 1, "function DzPostComptes(": 1}.items():
    check(f"3 compte {jeton!r} = {n}", B.count(jeton) == n, str(B.count(jeton)))
check("3.x CRLF partout (en octets)", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
if NODE:
    with tempfile.TemporaryDirectory() as _d:                     # fix 1 (Minor 5) : copie du bundle supprimée
        t = pathlib.Path(_d) / "b.mjs"
        t.write_bytes(RAW)
        rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("3.n node --check : le bundle PARSE", rc.returncode == 0, rc.stderr[-300:])

print("\n[4] le script partagé")
check("4.1 copie dist OCTET POUR OCTET", lambda: SHARED.read_bytes() == DIST.read_bytes())
HTML = (REPO / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
BALISE = '<script src="/shared/dz-espace-assistant.js"></script>'
check("4.2 balise dans la SPA, une fois, après dz-i18n.js, dz-icons.js et dz-projet-canaux.js",
      lambda: HTML.count(BALISE) == 1 and HTML.index("/shared/dz-i18n.js") < HTML.index(BALISE)
      and HTML.index("/shared/icons/dz-icons.js") < HTML.index(BALISE)
      and HTML.index("/shared/dz-projet-canaux.js") < HTML.index(BALISE))
check("4.3 aucun emoji ni window.alert/confirm/prompt, aucun innerHTML d'une donnée",
      lambda: not re.search("[\U0001F300-\U0001FAFF☀-➿✓✗]", SHARED.read_text("utf-8"))
      and not re.search(r"window\.(alert|confirm|prompt)\(", SHARED.read_text("utf-8"))
      and all("icone(" in l or "innerHTML = \"\"" in l for l in SHARED.read_text("utf-8").splitlines() if "innerHTML" in l
              and not l.strip().startswith(("/*", "*"))))

FAUX_DOM = r"""
function Noeud(tag){this.tagName=String(tag).toUpperCase();this.enfants=[];this.attrs={};this.ecoutes={};this._t="";this.parent=null;
  this.type="";this.checked=false;this.disabled=false;this.className="";this.innerHTML="";this.value="";this.placeholder="";this.title="";}
Object.defineProperty(Noeud.prototype,"textContent",{get:function(){return this._t+this.enfants.map(function(e){return e.textContent}).join("")},
  set:function(v){this._t=String(v);this.enfants=[]}});
Noeud.prototype.setAttribute=function(k,v){this.attrs[k]=String(v)};
Noeud.prototype.getAttribute=function(k){return k in this.attrs?this.attrs[k]:null};
Noeud.prototype.removeAttribute=function(k){delete this.attrs[k]};
Noeud.prototype.appendChild=function(e){e.parent=this;this.enfants.push(e);return e};
Noeud.prototype.addEventListener=function(t,f){(this.ecoutes[t]=this.ecoutes[t]||[]).push(f)};
Noeud.prototype.remove=function(){if(this.parent){var p=this.parent;p.enfants=p.enfants.filter(function(x){return x!==this},this);this.parent=null}};
Noeud.prototype.focus=function(){};
Noeud.prototype.declencher=function(t,ev){ev=ev||{};ev.target=ev.target||this;ev.preventDefault=function(){};(this.ecoutes[t]||[]).forEach(function(f){f(ev)})};
function tous(n,pred,out){out=out||[];if(pred(n))out.push(n);n.enfants.forEach(function(e){tous(e,pred,out)});return out}
var body=new Noeud("body"),docEcoutes={};
globalThis.document={body:body,createElement:function(t){return new Noeud(t)},
  addEventListener:function(t,f){(docEcoutes[t]=docEcoutes[t]||[]).push(f)},
  removeEventListener:function(t,f){docEcoutes[t]=(docEcoutes[t]||[]).filter(function(g){return g!==f})}};
var evenements=[];window.dzT=dzT;
window.dispatchEvent=function(e){evenements.push(e)};
window.open=function(){return null};
globalThis.CustomEvent=function(t,o){this.type=t;this.detail=o&&o.detail};
globalThis.Event=function(t){this.type=t};
window.dzIcone=function(cle){return "<svg data-cle=\""+cle+"\"></svg>"};
"""
HARNAIS = r"""
var appels=[],ESP_ID="esp_new";
var PLATS={telegram:{libelle:"Telegram",champs:[{nom:"TELEGRAM_BOT_TOKEN",secret:true},{nom:"TELEGRAM_CHAT_ID",secret:false}],requis:["TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID"],oauth:false},
  youtube:{libelle:"YouTube",champs:[{nom:"YOUTUBE_CLIENT_ID",secret:true},{nom:"YOUTUBE_CHANNEL_ID",secret:false}],requis:["YOUTUBE_CLIENT_ID"],oauth:true}};
/* une réponse FAUTIVE : le compte existant porte une « valeur » sur son champ secret — l'écran ne doit jamais la reprendre */
var CPT_TG={id:"c0000aaaa",espace_id:"esp_new",plateforme:"telegram",libelle:"Telegram",handle:"",oauth:false,disponible:true,verification:null,canal_id:null,
  champs:[{nom:"TELEGRAM_BOT_TOKEN",secret:true,pose:true,valeur:"FUITE-SECRET-1"},{nom:"TELEGRAM_CHAT_ID",secret:false,pose:true,valeur:"-100123"}]};
var COMPTES=[];
function rep(st,d){return Promise.resolve({ok:st<300,status:st,json:function(){return Promise.resolve(d)}})}
globalThis.fetch=function(u,o){var m=(o&&o.method)||"GET",b=o&&o.body?JSON.parse(o.body):null;appels.push({u:u,m:m,b:b});
  if(u==="/api/espaces"&&m==="GET")return rep(200,{espaces:[{id:"esp_m",nom:"Marque M",type:"marque"},{id:"esp_c",nom:"Client C",type:"client"},{id:"esp_p",nom:"Produit P",type:"produit"}],actif:"deepotus"});
  if(u==="/api/brand-kits")return rep(200,{kits:[{id:"k1",name:"Kit Un"}]});
  if(u==="/api/espaces"&&m==="POST")return new Promise(function(ok){setTimeout(function(){ok({ok:true,status:200,json:function(){return Promise.resolve({espace:Object.assign({id:ESP_ID},b)})}})},5)});
  if(u==="/api/espaces/"+ESP_ID&&m==="POST")return rep(200,{espace:Object.assign({id:ESP_ID},b)});
  if(u==="/api/espaces/"+ESP_ID+"/client"&&m==="PUT")return rep(200,Object.assign({version:1},b));
  if(u.indexOf("/api/comptes?espace=")===0)return rep(200,{espace:ESP_ID,comptes:COMPTES,plateformes:PLATS});
  if(u==="/api/comptes"&&m==="POST"){var c={id:"c1111bbbb",espace_id:ESP_ID,plateforme:b.plateforme,libelle:"YouTube",champs:[{nom:"YOUTUBE_CLIENT_ID",secret:true,pose:true,valeur:"FUITE-SECRET-2"},{nom:"YOUTUBE_CHANNEL_ID",secret:false,pose:false,valeur:""}],verification:null};return rep(200,{compte:c})}
  if(u==="/api/comptes/c0000aaaa"&&m==="POST")return rep(200,{compte:Object.assign({},CPT_TG,{champs:[{nom:"TELEGRAM_BOT_TOKEN",secret:true,pose:true,valeur:"FUITE-SECRET-3"},{nom:"TELEGRAM_CHAT_ID",secret:false,pose:true,valeur:"-100123"}]})});
  if(u==="/api/comptes/c1111bbbb/verifier")return rep(200,{compte:{id:"c1111bbbb",espace_id:ESP_ID,plateforme:"youtube",libelle:"YouTube",champs:[],verification:{etat:"orange",code:"incomplet",raison:"identifiants incomplets : YOUTUBE_CLIENT_ID",date:"2026-10-26T10:06:00"},canal_id:null}});
  if(u==="/api/comptes/c0000aaaa/verifier")return rep(200,{compte:Object.assign({},CPT_TG,{verification:{etat:"rouge",code:"refuse",raison:"jeton refusé (401) : Unauthorized",date:"2026-10-26T10:05:09",id_distant:null,nom_distant:null},canal_id:null})});
  if(u==="/api/espaces/"+ESP_ID+"/recapitulatif")return rep(200,{espace_id:ESP_ID,type:"client",client_responsable:ESP_ID,mode_publication:"valide_par_client",
     canaux:[{compte:"c0000aaaa",plateforme:"telegram",libelle:"Telegram",etat:"non_verifie",verifie_le:null,canal_id:null,consentement:"manquant"}],manques:{non_verifies:1,consentements:1}});
  if(u==="/api/espaces/"+ESP_ID+"/activate")return rep(200,{actif:ESP_ID});
  return rep(404,{detail:"route inconnue du faux serveur : "+m+" "+u})};
__SCRIPT__
function attendre(){return new Promise(function(ok){setTimeout(ok,25)})}
function voile(){return tous(body,function(n){return n.getAttribute("data-dz-assistant")!==null})[0]||null}
function etape(){var v=voile();return v?v.getAttribute("data-etape"):null}
function par(attr,val){var v=voile();return v?tous(v,function(n){return n.getAttribute(attr)!==null&&(val===undefined||n.getAttribute(attr)===val)}):[]}
function un(attr,val){return par(attr,val)[0]||null}
function saisir(cle,val){var n=un("data-dz-assistant-champ",cle);n.value=val;n.declencher(n.tagName==="SELECT"?"change":"input")}
function compte(m,u){return appels.filter(function(a){return a.m===m&&a.u===u}).length}
var R={};
(async function(){
 var A=window.__dzEspaceAssistant;R.api=typeof (A&&A.ouvrir);
 /* A : une MARQUE — l'étape 2 sautée ; deux clics sur « Suivant » = un seul POST ; au retour il modifie */
 var pA=A.ouvrir();await attendre();
 R.a_etape0=etape();R.a_fil=par("data-dz-assistant-fil").map(function(n){return n.textContent});
 R.a_parent_cache=!un("data-dz-assistant-champ","parent");
 saisir("nom","Marque A");saisir("type","marque");
 un("data-dz-assistant-suivant").declencher("click");un("data-dz-assistant-suivant").declencher("click");await attendre();
 R.a_posts=compte("POST","/api/espaces");R.a_corps=(appels.filter(function(a){return a.m==="POST"&&a.u==="/api/espaces"})[0]||{}).b;
 R.a_etape1=etape();
 un("data-dz-assistant-precedent").declencher("click");await attendre();R.a_retour=etape();
 saisir("nom","Marque A2");un("data-dz-assistant-suivant").declencher("click");await attendre();
 R.a_posts2=compte("POST","/api/espaces");R.a_modif=compte("POST","/api/espaces/esp_new");R.a_etape2=etape();
 un("data-dz-assistant-annuler").declencher("click");R.a_resolu=await pA;R.a_ferme=!voile();R.a_evts=evenements.length;
 /* B : un CLIENT — fiche, canaux, vérification, récapitulatif, Terminer */
 appels=[];COMPTES=[CPT_TG];
 var pB=A.ouvrir();await attendre();
 saisir("nom","Oracle Club");saisir("type","produit");await attendre();
 R.b_parents=par("data-dz-assistant-parent-option").map(function(n){return n.value});
 saisir("type","client");await attendre();R.b_parent_cache=!un("data-dz-assistant-champ","parent");
 un("data-dz-assistant-suivant").declencher("click");await attendre();
 R.b_etape_fiche=etape();
 saisir("societe","Oracle Club SAS");saisir("contact_nom","Ada");saisir("pays","fr");saisir("mode","publie_en_son_nom");
 un("data-dz-assistant-suivant").declencher("click");await attendre();
 var put=appels.filter(function(a){return a.m==="PUT"})[0]||{};R.b_put=[put.u,put.b];
 R.b_etape_canaux=etape();
 R.b_plats=par("data-dz-assistant-plateforme").map(function(n){return n.getAttribute("data-dz-assistant-plateforme")});
 R.b_glyphes=par("data-dz-glyphe").map(function(n){return n.getAttribute("data-dz-glyphe")});
 var cTg=un("data-dz-assistant-case","telegram");R.b_coche_existant=cTg&&cTg.checked;
 var sec=un("data-dz-assistant-cle","TELEGRAM_BOT_TOKEN"),pub=un("data-dz-assistant-cle","TELEGRAM_CHAT_ID");
 R.b_secret=[sec&&sec.type,sec&&sec.value,sec&&sec.placeholder];R.b_public=pub&&pub.value;
 sec.value="FAUX-JETON";sec.declencher("input");
 un("data-dz-assistant-verifier","telegram").declencher("click");await attendre();
 R.b_ecrit=(appels.filter(function(a){return a.m==="POST"&&a.u==="/api/comptes/c0000aaaa"})[0]||{}).b;
 R.b_verif=compte("POST","/api/comptes/c0000aaaa/verifier");
 var pas=un("data-dz-assistant-pastille","telegram");R.b_pastille=pas&&[pas.getAttribute("data-etat"),pas.textContent,pas.getAttribute("title")];
 var det=un("data-dz-assistant-detail","telegram");R.b_detail=det&&det.textContent;
 var sec2=un("data-dz-assistant-cle","TELEGRAM_BOT_TOKEN");R.b_secret_apres=sec2&&sec2.value;
 R.b_voile_txt=voile().textContent;
 /* YouTube coché sans rien saisir : « Suivant » crée le compte (non vérifié) ; son secret n'est pas relu non plus */
 var cYt=un("data-dz-assistant-case","youtube");cYt.checked=true;cYt.declencher("change");await attendre();
 var secYt=un("data-dz-assistant-cle","YOUTUBE_CLIENT_ID");R.b_yt_secret=secYt&&secYt.value;
 R.b_connecter_yt=!!un("data-dz-assistant-connecter","youtube")&&!un("data-dz-assistant-connecter","telegram");
 /* t308 fix 1 : clics CONCURRENTS sur une plateforme sans compte (Vérifier ×2, Connecter, Suivant, sans attendre) : un seul POST /api/comptes, un seul /verifier, boutons grisés pendant l'envoi */
 un("data-dz-assistant-verifier","youtube").declencher("click");R.b_ve_grise=!!(un("data-dz-assistant-verifier","youtube")||{}).disabled&&!!(un("data-dz-assistant-connecter","youtube")||{}).disabled;
 un("data-dz-assistant-verifier","youtube").declencher("click");un("data-dz-assistant-connecter","youtube").declencher("click");
 un("data-dz-assistant-suivant").declencher("click");await attendre();await attendre();
 R.b_posts_comptes=compte("POST","/api/comptes");R.b_verif_yt=compte("POST","/api/comptes/c1111bbbb/verifier");
 R.b_cree_yt=(appels.filter(function(a){return a.m==="POST"&&a.u==="/api/comptes"})[0]||{}).b;
 R.b_etape_recap=etape();
 R.b_recap=par("data-dz-assistant-recap-canal").map(function(n){return n.getAttribute("data-dz-assistant-recap-canal")});
 var cons=un("data-dz-assistant-consentement","c0000aaaa");R.b_cons=cons&&cons.textContent;
 var pr=un("data-dz-assistant-pastille","c0000aaaa");R.b_recap_pastille=pr&&[pr.getAttribute("data-etat"),pr.textContent];
 R.b_mode=(un("data-dz-assistant-mode")||{textContent:null}).textContent;
 R.b_manques=(un("data-dz-assistant-manques")||{textContent:null}).textContent;
 R.b_terminer_avant=evenements.length;
 un("data-dz-assistant-terminer").declencher("click");await attendre();
 R.b_activate=compte("POST","/api/espaces/esp_new/activate");
 R.b_evts=evenements.map(function(e){return [e.type,e.detail===undefined?null:e.detail]});
 R.b_ferme=!voile();R.b_resolu=await pB;
 R.secret_nulle_part=JSON.stringify(R).indexOf("FUITE-SECRET")<0;
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""


def node(code):
    with tempfile.TemporaryDirectory() as _d:
        f = pathlib.Path(_d) / "h.js"
        f.write_text(code, "utf-8")
        p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except ValueError:
        return {"erreur": (p.stdout + p.stderr)[-800:]}


print("\n[5] l'assistant, sous node")
R = {}
if NODE and SHARED.is_file():
    R = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + HARNAIS.replace("__SCRIPT__", SHARED.read_text("utf-8")))
check("5.0 le script s'exécute sous node", bool(R) and "erreur" not in R, str(R.get("erreur", ""))[:800])
F = AIDE.fr
if R and "erreur" not in R:
    check("5.1 l'API ouvrir", R["api"] == "function")
    check("5.2 la boîte s'ouvre à l'étape 1, fil des quatre étapes traduit",
          R["a_etape0"] == "1" and R["a_fil"] == [F("espaces.assistant.etape_identite"), F("espaces.assistant.etape_fiche"),
                                                   F("espaces.assistant.etape_canaux"), F("espaces.assistant.etape_recap")],
          str(R["a_fil"]))
    check("5.3 deux clics sur « Suivant » à l'étape 1 = UN seul POST /api/espaces (nom, couleur, type)",
          R["a_posts"] == 1 and (R["a_corps"] or {}).get("nom") == "Marque A" and R["a_corps"].get("type") == "marque"
          and re.fullmatch(r"#[0-9a-fA-F]{6}", R["a_corps"].get("couleur", "")), str(R["a_corps"]))
    check("5.4 une MARQUE saute l'étape 2 (fiche), à l'aller comme au retour",
          R["a_etape1"] == "3" and R["a_retour"] == "1", f'{R["a_etape1"]} {R["a_retour"]}')
    check("5.5 au retour, « Suivant » MODIFIE l'espace créé (POST /api/espaces/{id}), jamais un second espace",
          R["a_posts2"] == 1 and R["a_modif"] == 1 and R["a_etape2"] == "3", str([R["a_posts2"], R["a_modif"]]))
    check("5.6 Annuler après création : la boîte se ferme, rend l'id (la liste se relit), aucun évènement de fin",
          R["a_ferme"] and R["a_resolu"] == "esp_new" and R["a_evts"] == 0, str(R["a_resolu"]))
    check("5.7 le parent n'existe que pour un produit : marques et clients proposés, jamais un produit",
          R["a_parent_cache"] and R["b_parent_cache"] and R["b_parents"] == ["", "esp_m", "esp_c"], str(R["b_parents"]))
    check("5.8 un CLIENT passe par la fiche, écrite par PUT …/client",
          R["b_etape_fiche"] == "2" and R["b_put"][0] == "/api/espaces/esp_new/client"
          and R["b_put"][1].get("societe") == "Oracle Club SAS" and R["b_put"][1].get("contact", {}).get("nom") == "Ada"
          and R["b_put"][1].get("pays") == "FR" and R["b_put"][1].get("mode_publication") == "publie_en_son_nom"
          and R["b_etape_canaux"] == "3", str(R["b_put"]))
    check("5.9 une case par plateforme, glyphe Deepotus (dz-reseau-*) ; le compte existant de l'espace est coché",
          R["b_plats"] == ["telegram", "youtube"] and "dz-reseau-telegram" in R["b_glyphes"]
          and "dz-reseau-youtube" in R["b_glyphes"] and R["b_coche_existant"], str(R["b_glyphes"]))
    check("5.10 un champ SECRET n'est jamais prérempli depuis une réponse (type mot de passe, vide, « posé ») ; un champ public l'est",
          R["b_secret"] == ["password", "", F("espaces.comptes.pose")] and R["b_public"] == "-100123", str(R["b_secret"]))
    check("5.11 OAuth : « Connecter » pour YouTube cochée (et pas pour Telegram, à clés)", R["b_connecter_yt"])
    check("5.12 « Vérifier » écrit la saisie (seulement ce qui est saisi) puis appelle /verifier une fois",
          R["b_ecrit"] == {"valeurs": {"TELEGRAM_BOT_TOKEN": "FAUX-JETON"}} and R["b_verif"] == 1, str(R["b_ecrit"]))
    check("5.13 la pastille dit l'état traduit ; la raison BRUTE n'est qu'au survol",
          R["b_pastille"] and R["b_pastille"][0] == "rouge" and F("espaces.assistant.etat_rouge") in R["b_pastille"][1]
          and "jeton refusé (401)" in (R["b_pastille"][2] or "") and "jeton refusé" not in R["b_voile_txt"], str(R["b_pastille"]))
    check("5.14 le détail : la traduction du CODE et la date", R["b_detail"] and F("espaces.assistant.code_refuse") in R["b_detail"]
          and "2026-10-26 10:05" in R["b_detail"], str(R["b_detail"]))
    check("5.15 après écriture, le secret n'est pas relu (champ vide) ; idem pour un compte créé par l'assistant",
          R["b_secret_apres"] == "" and R["b_yt_secret"] == "", str([R["b_secret_apres"], R["b_yt_secret"]]))
    check("5.21 clics concurrents (Vérifier ×2, Connecter, Suivant) : UN seul POST /api/comptes, UN seul /verifier ; Vérifier et Connecter grisés pendant l'envoi",
          R["b_posts_comptes"] == 1 and R["b_verif_yt"] == 1 and R["b_ve_grise"], str([R["b_posts_comptes"], R["b_verif_yt"], R["b_ve_grise"]]))
    check("5.16 une plateforme cochée sans vérification : « Suivant » crée son compte dans l'espace (marqué non vérifié)",
          R["b_cree_yt"] == {"espace_id": "esp_new", "plateforme": "youtube"} and R["b_etape_recap"] == "4", str(R["b_cree_yt"]))
    check("5.17 le récapitulatif : le canal, « non vérifié », le consentement MANQUANT dit en clair",
          R["b_recap"] == ["c0000aaaa"] and R["b_recap_pastille"] == ["non_verifie", F("espaces.assistant.etat_non_verifie")]
          and R["b_cons"] == F("espaces.assistant.consentement_manquant"), str([R["b_recap_pastille"], R["b_cons"]]))
    check("5.18 le récapitulatif dit le mode de publication et les manques",
          F("espaces.assistant.mode_valide_par_client") in (R["b_mode"] or "")
          and F("espaces.assistant.manques", non_verifies=1, consentements=1) == R["b_manques"], str([R["b_mode"], R["b_manques"]]))
    check("5.19 « Terminer » active l'espace, émet deepotus:espace-refresh puis dz-espace-cree (detail = id), ferme et rend l'id",
          R["b_terminer_avant"] == 0 and R["b_activate"] == 1 and ["dz-espace-cree", "esp_new"] in R["b_evts"]
          and ["deepotus:espace-refresh", None] in R["b_evts"] and R["b_ferme"] and R["b_resolu"] == "esp_new", str(R["b_evts"]))
    check("5.20 aucune valeur secrète d'une réponse ne paraît nulle part à l'écran", R["secret_nulle_part"])

print("\n[6] textes")
DICO = json.loads(DICO_P.read_text("utf-8"))
NEUVES = {k: v for k, v in DICO.items() if k.startswith("espaces.assistant.")}
check("6.1 clés espaces.assistant.* à trois segments, FR et EN non vides, mêmes {variables}",
      bool(NEUVES) and all(re.fullmatch(r"espaces\.assistant\.[a-z_]+", k) and v.get("fr", "").strip() and v.get("en", "").strip()
                           and sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"]))
                           for k, v in NEUVES.items()))
CODES = ("ok", "incomplet", "refuse", "refuse_palier", "quota", "reseau", "indetermine", "non_audite", "chat_introuvable",
         "telephone_verifie", "telephone_jamais", "plateforme_inconnue")
import app.services.verif_canaux as VC  # noqa: E402
check("6.2 un texte par code de vérification (verif_canaux.CODES)", tuple(VC.CODES) == CODES
      and all(f"espaces.assistant.code_{c}" in NEUVES for c in CODES))
TXT = SHARED.read_text("utf-8") if SHARED.is_file() else ""
emp = {k for k in re.findall(r'"(espaces\.assistant\.[a-z_]+)"', TXT) if not k.endswith("_")}   # un préfixe composé n'est pas une clé
emp |= {f"espaces.assistant.{p}{x}" for p, xs in (("code_", CODES), ("etat_", ("vert", "orange", "rouge", "non_verifie")),
                                                   ("type_", ("marque", "produit", "client")),
                                                   ("mode_", ("valide_par_client", "publie_en_son_nom")))
        for x in xs if f'"espaces.assistant.{p}"' in TXT}
check("6.3 toutes les clés employées existent, aucune orpheline", bool(emp) and emp == set(NEUVES),
      f"sans traduction {sorted(emp - set(NEUVES))} orphelines {sorted(set(NEUVES) - emp)}")
check("6.4 les autres clés employées existent (espaces.*, commun.action.*)",
      all(k in AIDE.DICO for k in re.findall(r'"((?:espaces|commun)\.[a-z_]+\.[a-z_.]+)"', TXT) if not k.endswith((".", "_"))))
check("6.5 l'assemblé dz-i18n-dico.js est à jour", lambda: subprocess.run(
    [sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True).returncode == 0)

print("\n[7] la paire : « Créer l'espace » ouvre l'assistant")
check("7.1 le formulaire data-dz-espace-nouveau est toujours là, une fois (scène du guide t211)",
      B.count('"data-dz-espace-nouveau":"1"') == 1)
check("7.2 sa soumission ouvre window.__dzEspaceAssistant.ouvrir (nom et couleur saisis), relit la liste au retour",
      B.count("window.__dzEspaceAssistant.ouvrir({nom:st.nom.trim(),couleur:st.couleur})") == 1
      and B.count(MARKER + "window.__dzEspaceAssistant") == 1)
check("7.3 sans le script partagé, l'ancien formulaire rapide reste le repli (POST /api/espaces)",
      B.count('agir(dzEspEnvoyer("/api/espaces","POST",{nom:st.nom.trim(),couleur:st.couleur}))') == 1)

# ── t308 tâche 5 (26/10/2026) : l'état de vérification dans Réglages › Espaces et au Planificateur ─────────────────────
print("\n[8] la pastille partagée et la vérification à un seul appel")
SONDE_PASTILLE = r"""
var appels=[],REPONSES={};
function rep(st,d){return Promise.resolve({ok:st<300,status:st,json:function(){return Promise.resolve(d)}})}
globalThis.fetch=function(u,o){var m=(o&&o.method)||"GET";appels.push({u:u,m:m});
  var r=REPONSES[u];if(!r)return rep(404,{detail:"inconnu"});
  return new Promise(function(ok){setTimeout(function(){ok({ok:r[0]<300,status:r[0],json:function(){return Promise.resolve(r[1])}})},10)})};
__SCRIPT__
var R={},A=window.__dzEspaceAssistant;
function lire(n){var g=n.enfants[0];return {tag:n.tagName,etat:n.getAttribute("data-etat"),texte:n.textContent,titre:n.getAttribute("title"),
  glyphe:g&&g.innerHTML,style:n.getAttribute("style")}}
(async function(){
 R.api=[typeof A.pastille,typeof A.verifier,typeof A.enCours];
 R.vert=lire(A.pastille({verification:{etat:"vert",code:"ok",raison:"identité lue : @oracle",date:"2026-10-26T10:00:00"}}));
 R.orange=lire(A.pastille({verification:{etat:"orange",code:"incomplet",raison:"identifiants incomplets",date:"2026-10-26T10:01:00"}}));
 R.rouge=lire(A.pastille({verification:{etat:"rouge",code:"refuse",raison:"jeton refusé (401)",date:"2026-10-26T10:02:00"}}));
 R.aucun=lire(A.pastille({id:"c9",verification:null}));
 R.recap=lire(A.pastille({etat:"vert",verifie_le:"2026-10-26T10:03:00"}));
 /* verifier : deux appels pour le même compte pendant le vol = UN fetch ; libéré à la réponse ; libéré aussi sur échec */
 REPONSES["/api/comptes/c1/verifier"]=[200,{compte:{id:"c1",verification:{etat:"vert",code:"ok",raison:"ok",date:"2026-10-26T10:04:00"}}}];
 REPONSES["/api/comptes/c2/verifier"]=[500,{detail:"panne du faux serveur"}];
 var p1=A.verifier("c1"),p2=A.verifier("c1");R.en_vol=A.enCours("c1");R.autre_libre=!A.enCours("c2");
 var v1=await p1;await p2;R.un_appel=appels.filter(function(a){return a.u==="/api/comptes/c1/verifier"&&a.m==="POST"}).length;
 R.libre_apres=!A.enCours("c1");R.rendu=v1&&v1.compte&&v1.compte.verification&&v1.compte.verification.etat;
 var e2=null;try{await A.verifier("c2")}catch(e){e2=String(e&&e.message||e)}
 R.echec=e2;R.libre_echec=!A.enCours("c2");
 A.verifier("c1");await new Promise(function(ok){setTimeout(ok,30)});
 R.rejouable=appels.filter(function(a){return a.u==="/api/comptes/c1/verifier"}).length;
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
P8 = {}
if NODE and SHARED.is_file():
    P8 = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + SONDE_PASTILLE.replace("__SCRIPT__", SHARED.read_text("utf-8")))
check("8.0 la sonde s'exécute sous node", bool(P8) and "erreur" not in P8, str(P8.get("erreur", ""))[:800])
if P8 and "erreur" not in P8:
    check("8.1 l'API expose pastille, verifier et enCours", P8["api"] == ["function"] * 3, str(P8["api"]))
    DATES = {"vert": "2026-10-26 10:00", "orange": "2026-10-26 10:01", "rouge": "2026-10-26 10:02"}
    RAISONS = {"vert": "identité lue : @oracle", "orange": "identifiants incomplets", "rouge": "jeton refusé (401)"}
    for et, glyphe, cle in (("vert", "dz-etat-succes", "etat_vert"), ("orange", "dz-etat-avertissement", "etat_orange"),
                            ("rouge", "dz-etat-erreur", "etat_rouge")):
        v = P8[et]
        check(f"8.2 {et} : un élément, glyphe {glyphe}, texte traduit, survol « vérifié le … : raison »",
              v["tag"] == "SPAN" and v["etat"] == et and glyphe in (v["glyphe"] or "") and v["texte"] == F(f"espaces.assistant.{cle}")
              and v["titre"] == F("espaces.assistant.survol", date=DATES[et], raison=RAISONS[et]), str(v))
    check("8.3 couleurs distinctes pour les quatre états (vert, ambre, rouge, atténué)",
          len({re.search(r"color:([^;]+)$", P8[k]["style"]).group(1) for k in ("vert", "orange", "rouge", "aucun")}) == 4)
    check("8.4 sans vérification : « non vérifié », glyphe dz-etat-inconnu, survol « non vérifié »",
          P8["aucun"]["etat"] == "non_verifie" and P8["aucun"]["texte"] == F("espaces.assistant.etat_non_verifie")
          and P8["aucun"]["titre"] == F("espaces.assistant.etat_non_verifie") and "dz-etat-inconnu" in P8["aucun"]["glyphe"], str(P8["aucun"]))
    check("8.5 la même aide lit un canal du récapitulatif (etat, verifie_le)", P8["recap"]["etat"] == "vert"
          and "2026-10-26 10:03" in P8["recap"]["titre"], str(P8["recap"]))
    check("8.6 verifier : deux appels pendant le vol = UN POST /api/comptes/{id}/verifier, enCours vrai pendant, faux après",
          P8["en_vol"] and P8["autre_libre"] and P8["un_appel"] == 1 and P8["libre_apres"] and P8["rendu"] == "vert",
          str([P8["en_vol"], P8["un_appel"], P8["libre_apres"]]))
    check("8.7 verifier : un échec rejette (détail du serveur) ET libère le compte ; un appel suivant repart",
          P8["echec"] == "panne du faux serveur" and P8["libre_echec"] and P8["rejouable"] == 2, str([P8["echec"], P8["rejouable"]]))
check("8.8 l'assistant réemploie la MÊME aide (une seule fonction de pastille dans le script, exportée telle quelle)",
      TXT.count("function pastille(") == 1 and re.search(r"pastille:\s*pastille", TXT) is not None)

print("\n[9] les écrans : Réglages › Espaces et l'éditeur de post du Planificateur (fonctions LIVRÉES du bundle)")


def _tranche(debut, fin):
    i = B.find(debut)
    j = B.find(fin, i)
    return B[i:j] if 0 <= i < j else ""


ECRANS = _tranche("function dzEspEnvoyer(", "function dzEspSignal(") + "\n" + _tranche("function DzComptesEspace(", "var DZ_ONB_ETAPES=")
FAUX_REACT = r"""
var hooks=[],hi=0,arbre=null,effets=[],COMP=null,PROPS=null,plan=false;
var x={useReducer:function(red,init){var i=hi++;if(!(i in hooks))hooks[i]=init;return[hooks[i],function(a){hooks[i]=red(hooks[i],a);planifier()}]},
  useEffect:function(f,deps){var i=hi++,old=hooks[i];if(!old||!deps||deps.some(function(d,k){return d!==old[k]})){hooks[i]=deps||[];effets.push(f)}}};
var r={jsx:function(t,p){return{t:t,p:p||{}}},jsxs:function(t,p){return{t:t,p:p||{}}}};
function aplat(c,out){out=out||[];if(c==null||c===false||c===true||c==="")return out;if(Array.isArray(c)){c.forEach(function(e){aplat(e,out)});return out}out.push(c);return out}
function kids(n){return n&&typeof n==="object"&&n.p?aplat(n.p.children):[]}
function refs(n){if(!n||typeof n!=="object")return;if(typeof n.p.ref==="function"){var d=document.createElement(n.t);n.p.ref(d);n.dom=d}kids(n).forEach(refs)}
function monter(C,p){COMP=C;PROPS=p;hooks=[];rendre()}
function rendre(){hi=0;effets=[];arbre=COMP(PROPS);refs(arbre);var e=effets;e.forEach(function(f){f()})}
function planifier(){if(plan)return;plan=true;Promise.resolve().then(function(){plan=false;rendre()})}
function chercher(pred,n,out){out=out||[];n=n===undefined?arbre:n;if(!n||typeof n!=="object")return out;if(pred(n))out.push(n);kids(n).forEach(function(e){chercher(pred,e,out)});return out}
function avec(attr,val){return chercher(function(n){return n.p&&n.p[attr]!==undefined&&(val===undefined||n.p[attr]===val)})}
function texte(n){if(n==null||n===false)return"";if(typeof n!=="object")return String(n);if(n.dom)return n.dom.textContent;return kids(n).map(texte).join("")}
function pastilleDe(n){var d=n&&n.dom;var s=d&&d.enfants[0];return s?[s.getAttribute("data-etat"),s.textContent,s.getAttribute("title")]:null}
function attendre(ms){return new Promise(function(ok){setTimeout(ok,ms||30)})}
"""
SONDE_ECRANS = r"""
var appels=[],VERIFS={c_a:null,c_b:{etat:"vert",code:"ok",raison:"identité lue",date:"2026-10-26T09:00:00"},
  c_r:{etat:"rouge",code:"refuse",raison:"jeton refusé (401)",date:"2026-10-26T09:01:00"},c_o:{etat:"orange",code:"incomplet",raison:"incomplet",date:"2026-10-26T09:02:00"}};
function cpt(id,p){return{id:id,espace_id:"esp_c",plateforme:p,libelle:"Compte "+id,handle:"",historique:false,oauth:false,disponible:true,
  verification:VERIFS[id],canal_id:null,champs:[]}}
function liste(){return[cpt("c_a","telegram"),cpt("c_b","youtube"),cpt("c_r","x"),cpt("c_o","tiktok")]}
function rep(st,d,ms){return new Promise(function(ok){setTimeout(function(){ok({ok:st<300,status:st,json:function(){return Promise.resolve(d)}})},ms||0)})}
globalThis.fetch=function(u,o){var m=(o&&o.method)||"GET";appels.push({u:u,m:m});
  if(u.indexOf("/api/comptes?espace=")===0)return rep(200,{espace:"esp_c",comptes:liste(),plateformes:{telegram:{libelle:"Telegram"},youtube:{libelle:"YouTube"},x:{libelle:"X"},tiktok:{libelle:"TikTok"}}});
  if(u==="/api/comptes/c_a/verifier"&&m==="POST"){VERIFS.c_a={etat:"orange",code:"incomplet",raison:"identifiants incomplets : TELEGRAM_CHAT_ID",date:"2026-10-26T11:00:00"};return rep(200,{compte:cpt("c_a","telegram")},40)}
  if(u==="/api/comptes/c_r/verifier"&&m==="POST")return rep(500,{detail:"panne du faux serveur"},20);
  return rep(404,{detail:"route inconnue du faux serveur : "+m+" "+u})};
__SCRIPT__
__ECRANS__
function compte(m,u){return appels.filter(function(a){return a.m===m&&a.u===u}).length}
var R={};
(async function(){
 /* Réglages › Espaces */
 monter(DzComptesEspace,{espace:"esp_c",nom:"Client C"});await attendre();
 R.pastilles={};avec("data-dz-compte-etat").forEach(function(n){R.pastilles[n.p["data-dz-compte-etat"]]=pastilleDe(n)});
 var bt=function(id){return avec("data-dz-compte-verifier",id)[0]||null};
 R.boutons=avec("data-dz-compte-verifier").map(function(n){return [n.p["data-dz-compte-verifier"],texte(n),!!n.p.disabled,n.t]});
 var gets0=compte("GET","/api/comptes?espace=esp_c");
 bt("c_a").p.onClick();bt("c_a").p.onClick();await attendre(5);
 R.grise_pendant=!!(bt("c_a")&&bt("c_a").p.disabled);R.autre_libre=!(bt("c_b")&&bt("c_b").p.disabled);
 bt("c_a").p.onClick();
 await attendre(120);
 R.verifs_a=compte("POST","/api/comptes/c_a/verifier");R.relue=compte("GET","/api/comptes?espace=esp_c")-gets0;
 R.libre_apres=!(bt("c_a")&&bt("c_a").p.disabled);R.pastille_a_apres=pastilleDe(avec("data-dz-compte-etat","c_a")[0]);
 var gets1=compte("GET","/api/comptes?espace=esp_c");
 bt("c_r").p.onClick();await attendre(5);R.grise_r=!!bt("c_r").p.disabled;await attendre(100);
 R.libre_echec=!bt("c_r").p.disabled;R.relue_echec=compte("GET","/api/comptes?espace=esp_c")-gets1;
 R.msg_echec=texte(avec("data-dz-compte-msg","c_r")[0]||null);
 R.rouge_garde=pastilleDe(avec("data-dz-compte-etat","c_r")[0]);
 /* le Planificateur : c_a (orange maintenant), c_b (vert), c_r (rouge) cochés ; c_o (orange) PAS coché ; un 5e compte jamais vérifié coché */
 VERIFS.c_a=null;
 var changes=[];
 monter(DzPostComptes,{post:{id:"p1",espaceId:"esp_c",comptes:["c_a","c_b","c_r"]},onChange:function(v){changes.push(v)}});await attendre();
 R.post_etats={};avec("data-dz-post-compte-etat").forEach(function(n){R.post_etats[n.p["data-dz-post-compte-etat"]]=pastilleDe(n)});
 var lab=avec("data-dz-post-compte","c_o")[0];var caseO=chercher(function(n){return n.t==="input"},lab)[0];caseO.p.onChange();
 R.change=changes[0]||null;
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
P9 = {}
if NODE and SHARED.is_file() and ECRANS.strip():
    P9 = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + FAUX_REACT
              + SONDE_ECRANS.replace("__SCRIPT__", SHARED.read_text("utf-8")).replace("__ECRANS__", ECRANS))
check("9.0 les fonctions livrées s'exécutent sous node", bool(P9) and "erreur" not in P9, str(P9.get("erreur", ""))[:800])
if P9 and "erreur" not in P9:
    pa = P9["pastilles"]
    check("9.1 Réglages : une pastille par compte, l'état de SA vérification (rouge, vert, orange, non vérifié)",
          set(pa) == {"c_a", "c_b", "c_r", "c_o"} and (pa["c_b"] or [None])[0] == "vert" and (pa["c_r"] or [None])[0] == "rouge"
          and (pa["c_o"] or [None])[0] == "orange" and (pa["c_a"] or [None])[0] == "non_verifie", str(pa))
    check("9.2 Réglages : un bouton « Vérifier » par compte, libellé traduit", len(P9["boutons"]) == 4
          and all(b[1] == F("espaces.comptes.verifier") and b[3] == "button" and not b[2] for b in P9["boutons"]), str(P9["boutons"]))
    check("9.3 « Vérifier » : double clic = UN seul appel à la route ; bouton grisé pendant l'appel (les autres comptes libres)",
          P9["verifs_a"] == 1 and P9["grise_pendant"] and P9["autre_libre"], str([P9["verifs_a"], P9["grise_pendant"]]))
    check("9.4 après la réponse : la liste est relue UNE fois (un clic de plus pendant le vol ne relance rien), le bouton libéré, la pastille dit le nouvel état",
          P9["relue"] == 1 and P9["libre_apres"] and (P9["pastille_a_apres"] or [None])[0] == "orange"
          and "2026-10-26 11:00" in (P9["pastille_a_apres"] or ["", "", ""])[2], str([P9["relue"], P9["pastille_a_apres"]]))
    check("9.5 sur ÉCHEC : grisé pendant, libéré après, liste relue, l'erreur dite dans la ligne",
          P9["grise_r"] and P9["libre_echec"] and P9["relue_echec"] == 1 and "panne du faux serveur" in P9["msg_echec"],
          str([P9["grise_r"], P9["libre_echec"], P9["relue_echec"], P9["msg_echec"]]))
    pe = P9["post_etats"]
    check("9.6 Planificateur : un compte coché SANS vérification dit « non vérifié »",
          (pe.get("c_a") or [None, None])[:2] == ["non_verifie", F("espaces.assistant.etat_non_verifie")], str(pe))
    check("9.7 Planificateur : rien pour un compte coché VERT ni pour un compte non coché ; l'état d'un coché rouge est dit",
          "c_b" not in pe and "c_o" not in pe and (pe.get("c_r") or [None])[0] == "rouge", str(pe))
    check("9.8 Planificateur : SIGNALE sans bloquer — cocher un compte non vérifié passe (comptes et canaux posés)",
          P9["change"] == {"comptes": ["c_a", "c_b", "c_r", "c_o"], "channels": ["telegram", "youtube", "x", "tiktok"]}, str(P9["change"]))
if PM:
    _cibles = [z for _a, z in PM.PAIRES[2:]]
    _couches = [(m.start(), B.index("/*__DZ_%s_END__*/" % m.group(1))) for m in re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", B)]
    check("9.9 les paires de la tâche 5 visent DzComptesEspace et DzPostComptes, HORS de tout bloc de couche",
          lambda: len(_cibles) >= 3 and all(B.count(z) == 1 and not any(s0 <= B.index(z) <= e0 for s0, e0 in _couches)
                                            and B.index("function DzComptesEspace(") < B.index(z) < B.index("var DZ_ONB_ETAPES=")
                                            for z in _cibles))
check("9.10 une seule aide de pastille : le bundle l'appelle par window.__dzEspaceAssistant.pastille (Réglages et Planificateur)",
      B.count("window.__dzEspaceAssistant.pastille(c)") == 2 and B.count("var A=window.__dzEspaceAssistant;if(!A||A.enCours(c.id))return;var pv=A.verifier(c.id);") == 1)
check("9.11 la clé du bouton existe en FR et EN (« Vérifier » / « Verify », contexte : même texte FR ailleurs)",
      DICO.get("espaces.comptes.verifier", {}).get("fr") == "Vérifier" and DICO["espaces.comptes.verifier"].get("en") == "Verify"
      and DICO["espaces.comptes.verifier"].get("contexte") is True and 'dzT("espaces.comptes.verifier")' in B)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
