# -*- coding: utf-8 -*-
"""t309 tâche 5 (26/10/2026) — le bandeau « pour qui » et la FICHE CLIENT, hors du bundle.
Plan docs/superpowers/plans/2026-10-26-t309-securites-client.md (tâche 5, décision 7), spec
2026-10-25-boite-a-outils-design.md §5.5. Tout vit dans frontend/shared/dz-pour-qui.js (window.__dzPourQui) : AUCUN
maillon, aucun octet du bundle touché.
[P1] le bandeau  inséré APRÈS `main > header` (frère, jamais dans un enfant React) sur quick, studio, scheduler, library ;
                 retiré ailleurs (settings) ; relu à chaque mutation de #root et à deepotus:navigate ; un `main` recréé
                 reçoit le bandeau, jamais deux ; pastille, nom de l'espace, « Projet : <nom> » si un projet est actif ;
[P2] le client   liseré gauche 3 px de la couleur de l'espace, « Client : <nom> » (société de la fiche, sinon nom de
                 l'espace client) et « Fiche client » SEULEMENT pour un espace client ou un produit sous un client ;
[P3] Révoquer    confirmation par window.__dzDialogue.confirmer (non : rien n'est envoyé) ; oui : la route, puis le nombre
                 `en_pause` rendu par la route dit dans la boîte ;
[P4] Ajouter     canaux = les canal_id des récapitulatifs des espaces gouvernés ; envoie {canal_id, permis:["publier"], moyen} ;
[P5] À valider   les posts « a_valider » des espaces gouvernés seulement, libellé de __dzGardeClient.etiquette ;
                 « Validé par le client » / « À corriger » -> validation-client {reponse, moyen} puis deepotus:schedule-recharger ;
[P6] journal     plus récent d'abord, au plus 50 lignes ;
[P7] anglais     aucun texte français dans le bandeau ni la boîte (textes, survols, options) ;
[P9] revue finale t309 (26/10/2026) : I1/D1 le bandeau ne pose plus `data-espace` (data-dz-pq-espace) et l'observateur
                 de dz-projet-canaux.js (chargé AVANT, faux MutationObserver qui livre les attributs) ne le vide plus au
                 changement d'espace, ses hôtes restent remplis ; role=region + aria-label ; D3 heures UTC en heure locale
                 (TZ Asia/Tokyo) ; M2 les posts programmés non validés (en pause) listés en valide_par_client ;
[P10] t311 tâche 6 : « Envoyer au client par WhatsApp » (data-dz-pour-qui-wa-valider) pour un post a_valider quand la
                 fiche a un contact WhatsApp -> POST /api/schedule/{id}/validation-whatsapp, message ; note de correction
                 et état « envoyé » lus dans GET /api/schedule/{id}/client (validation_whatsapp) ;
[P8] livraison   shared == dist, index.html charge le script une fois après dz-garde-client.js ; textes espaces.pourqui.*
                 FR/EN, mêmes variables, tous employés, assemblés ; ni emoji, ni alert/confirm/prompt, ni arrondi de châssis.
Aucun réseau (faux fetch). Run (depuis backend/) : & $PY tests/test_pour_qui_ecran.py"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import _i18n_l1_aide as AIDE                                        # noqa: E402

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
        fail += 1; print(f"  FAIL  {label} {str(detail)[:700]}")


SHARED = REPO / "frontend" / "shared" / "dz-pour-qui.js"
DIST = REPO / "frontend" / "dist" / "shared" / "dz-pour-qui.js"
DICO_P = REPO / "frontend" / "shared" / "i18n" / "espaces.json"
BUNDLE = REPO / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
TXT = SHARED.read_text("utf-8") if SHARED.is_file() else ""
PC = REPO / "frontend" / "shared" / "dz-projet-canaux.js"
PC_TXT = PC.read_text("utf-8") if PC.is_file() else ""


def F(cle, **v):
    return AIDE.fr(cle, **v) if cle in AIDE.DICO else "<clé absente> " + cle    # le banc rougit sans planter


def EN(cle, **v):
    if cle not in AIDE.DICO:
        return "<clé absente> " + cle
    s = AIDE.DICO[cle]["en"]
    for k, x in v.items():
        s = s.replace("{" + k + "}", str(x))
    return s


# ── faux DOM : de quoi poser un bandeau à côté de `main > header` et jouer une boîte ──
FAUX_DOM = r"""
function Noeud(tag){this.tagName=String(tag).toUpperCase();this.enfants=[];this.attrs={};this.ecoutes={};this._t="";this.parent=null;
  this.type="";this.checked=false;this.disabled=false;this.className="";this.innerHTML="";this.value="";this.id="";}
Object.defineProperty(Noeud.prototype,"textContent",{get:function(){return this._t+this.enfants.map(function(e){return e.textContent}).join("")},
  set:function(v){this._t=String(v);this.enfants.forEach(function(e){e.parent=null});this.enfants=[]}});
Object.defineProperty(Noeud.prototype,"parentNode",{get:function(){return this.parent}});
Object.defineProperty(Noeud.prototype,"nextSibling",{get:function(){if(!this.parent)return null;var l=this.parent.enfants,i=l.indexOf(this);return l[i+1]||null}});
Object.defineProperty(Noeud.prototype,"isConnected",{get:function(){var n=this;while(n.parent)n=n.parent;return n===body}});
process.env.TZ="Asia/Tokyo";   /* D3 : UTC+9 sans heure d'été */
Noeud.prototype.setAttribute=function(k,v){this.attrs[k]=String(v);if(k==="id")this.id=String(v);notifier(this,k)};
/* revue finale I1 : comme un vrai MutationObserver (attributes + attributeFilter + subtree), livré en microtâche */
function notifier(n,k){(typeof observateurs==="undefined"?[]:observateurs).forEach(function(o){var op=o.opts||{};
  if(!o.cible||!op.attributes||(op.attributeFilter&&op.attributeFilter.indexOf(k)<0))return;
  var x=n;while(x&&x!==o.cible)x=x.parent;if(!x)return;
  Promise.resolve().then(function(){o.cb([{type:"attributes",target:n,attributeName:k}])})})}
Noeud.prototype.getAttribute=function(k){return k in this.attrs?this.attrs[k]:null};
Noeud.prototype.removeAttribute=function(k){delete this.attrs[k]};
Noeud.prototype.appendChild=function(e){if(e.parent)e.remove();e.parent=this;this.enfants.push(e);return e};
Noeud.prototype.insertBefore=function(e,ref){if(e.parent)e.remove();if(!ref)return this.appendChild(e);var i=this.enfants.indexOf(ref);
  if(i<0)throw new Error("insertBefore : ref absent");e.parent=this;this.enfants.splice(i,0,e);return e};
Noeud.prototype.addEventListener=function(t,f){(this.ecoutes[t]=this.ecoutes[t]||[]).push(f)};
Noeud.prototype.removeEventListener=function(t,f){this.ecoutes[t]=(this.ecoutes[t]||[]).filter(function(g){return g!==f})};
Noeud.prototype.remove=function(){if(this.parent){var p=this.parent,me=this;p.enfants=p.enfants.filter(function(x){return x!==me});this.parent=null}};
Noeud.prototype.focus=function(){document.activeElement=this};
Object.defineProperty(Noeud.prototype,"offsetParent",{get:function(){return /display:\s*none/.test(this.attrs.style||"")||this._cache?null:(this.parent||body)}});
function correspond(n,p){
  if(p==="main > header")return n.tagName==="HEADER"&&!!n.parent&&n.parent.tagName==="MAIN";
  var m=/^([a-z]*)(?:\[([\w-]+)\])?$/.exec(p);
  return !!m&&!!(m[1]||m[2])&&(!m[1]||n.tagName.toLowerCase()===m[1])&&(!m[2]||n.getAttribute(m[2])!==null)}
Noeud.prototype.querySelectorAll=function(sel){var me=this,ps=sel.split(",").map(function(s){return s.trim()});
  return tous(this,function(n){return n!==me&&ps.some(function(p){return correspond(n,p)})})};
Noeud.prototype.querySelector=function(sel){return this.querySelectorAll(sel)[0]||null};
Noeud.prototype.declencher=function(t,ev){ev=ev||{};ev.target=ev.target||this;ev.preventDefault=function(){};ev.stopPropagation=function(){};(this.ecoutes[t]||[]).forEach(function(f){f(ev)})};
function tous(n,pred,out){out=out||[];if(pred(n))out.push(n);n.enfants.forEach(function(e){tous(e,pred,out)});return out}
var body=new Noeud("body"),head=new Noeud("head"),docEcoutes={};
globalThis.document={body:body,head:head,activeElement:null,readyState:"complete",createElement:function(t){return new Noeud(t)},
  getElementById:function(i){return tous(body,function(n){return n.id===i})[0]||null},
  querySelector:function(s){return body.querySelector(s)},querySelectorAll:function(s){return body.querySelectorAll(s)},
  addEventListener:function(t,f){(docEcoutes[t]=docEcoutes[t]||[]).push(f)},
  removeEventListener:function(t,f){docEcoutes[t]=(docEcoutes[t]||[]).filter(function(g){return g!==f})}};
var evenements=[],winEcoutes={};
window.dzT=dzT;
window.addEventListener=function(t,f){(winEcoutes[t]=winEcoutes[t]||[]).push(f)};
window.removeEventListener=function(t,f){winEcoutes[t]=(winEcoutes[t]||[]).filter(function(g){return g!==f})};
window.dispatchEvent=function(e){evenements.push(e.type);(winEcoutes[e.type]||[]).slice().forEach(function(f){f(e)});return true};
globalThis.CustomEvent=function(t,o){this.type=t;this.detail=o&&o.detail};
globalThis.Event=function(t){this.type=t};
window.dzIcone=function(cle){return "<svg data-cle=\""+cle+"\"></svg>"};
var STOCK={dz_view:"scheduler"};
window.localStorage={getItem:function(k){return k in STOCK?STOCK[k]:null},setItem:function(k,v){STOCK[k]=String(v)}};
var observateurs=[];
globalThis.MutationObserver=function(cb){this.cb=cb;this.cible=null;observateurs.push(this)};
MutationObserver.prototype.observe=function(c,o){this.cible=c;this.opts=o||{}};MutationObserver.prototype.disconnect=function(){this.cible=null};
function muter(){observateurs.forEach(function(o){if(o.cible)o.cb([{type:"childList",addedNodes:[]}])})}
/* la coque : #root > div > main > [header, section] */
var root=new Noeud("div");root.setAttribute("id","root");body.appendChild(root);
var coque=new Noeud("div");root.appendChild(coque);
function poserMain(){var m=new Noeud("main"),h=new Noeud("header"),s=new Noeud("section");h.textContent="HEADER";m.appendChild(h);m.appendChild(s);coque.appendChild(m);return m}
var MAIN=poserMain();
"""

HARNAIS = r"""
var CONTACT="",VALW={},MODE="valide_par_client",appels=[],dial=[],REPONSE=false,ACTIF="cli_a",PROJET={id:"proj_1",nom:"Spring launch"},SOCIETE="Acme Corp";
var ESPACES=[{id:"deepotus",nom:"Deepotus",couleur:"#ef4444",type:"marque",parent:null},
  {id:"cli_a",nom:"Acme space",couleur:"#aa3311",type:"client",parent:null},
  {id:"prod_b",nom:"Acme widget",couleur:"#22aa55",type:"produit",parent:"cli_a"},
  {id:"marque_c",nom:"Brand C",couleur:"#3355ff",type:"marque",parent:null},
  {id:"prod_d",nom:"Brand C gadget",couleur:"#777777",type:"produit",parent:"marque_c"}];
var JOURNAL=[];for(var i=0;i<60;i++){var j=(i*37)%60;JOURNAL.push({quand:"2026-10-"+(10+Math.floor(j/10))+"T0"+(j%10)+":00:00",quoi:["consentement","validation","publication","revocation","mode","import"][i%6],canal_id:i%2?"x:111":"",qui:["utilisateur","client","telephone"][i%3]})}
function fiche(revoque){return {version:1,societe:SOCIETE,mode_publication:MODE,contact:{nom:"",email:"",whatsapp:CONTACT},
  consentements:[{canal_id:"x:111",permis:["publier"],date:"2026-10-20T10:00:00",moyen:"ecrit",revoque_le:revoque?"2026-10-26T08:00:00":null},
                 {canal_id:"telegram:acme",permis:["publier"],date:"2026-10-18T10:00:00",moyen:"whatsapp",revoque_le:"2026-10-21T09:00:00"}],
  journal:JOURNAL}}
var POSTS=[{id:"p1",title:"Teaser",status:"a_valider",espace_id:"cli_a",run_at:"2026-11-02T09:00:00Z"},
  {id:"p2",title:"Live",status:"scheduled",espace_id:"cli_a",run_at:"2026-11-03T09:00:00Z"},
  {id:"p3",title:"Widget post",status:"a_valider",espace_id:"prod_b",run_at:null},
  {id:"p4",title:"Other brand",status:"a_valider",espace_id:"marque_c",run_at:null},
  {id:"p5",title:"Validated",status:"scheduled",espace_id:"cli_a",run_at:"2026-11-04T09:00:00Z",valide_client_le:"2026-10-25T10:00:00Z"},
  {id:"p6",title:"Widget ready",status:"ready",espace_id:"prod_b",run_at:"2026-11-05T23:30:00Z",valide_client_le:null}];
var RECAP={cli_a:{canaux:[{compte:"cpt1",plateforme:"x",libelle:"Acme X",canal_id:"x:111"},
                         {compte:"cpt2",plateforme:"youtube",libelle:"Acme YT",canal_id:"youtube:UC9"},
                         {compte:"cpt3",plateforme:"tiktok",libelle:"Acme TT",canal_id:null}]},
           prod_b:{canaux:[{compte:"cpt4",plateforme:"instagram",libelle:"Widget IG",canal_id:"instagram:b1"}]}};
globalThis.fetch=function(u,o){var m=(o&&o.method)||"GET";appels.push({u:u,m:m,b:o&&o.body?JSON.parse(o.body):null});
  var st=200,d={};
  if(/^\/api\/espaces(\?|$)/.test(u))d={espaces:ESPACES,actif:ACTIF};
  else if(u==="/api/library/projets/actif")d=PROJET;
  else if(/^\/api\/espaces\/cli_a\/client$/.test(u))d=fiche(false);
  else if(/^\/api\/schedule\/[^/]+\/client$/.test(u))d={exigences:null,validation_whatsapp:VALW[u.split("/")[3]]||null};
  else if(/\/validation-whatsapp$/.test(u))d={envoi:"boutons",id:"wamid.X"};
  else if(/\/client$/.test(u)){st=400;d={detail:"pas un client"}}
  else if(/\/client\/consentements\/revoquer$/.test(u)){d=fiche(true);d.en_pause=2}
  else if(/\/client\/consentements$/.test(u))d=fiche(false);
  else if(/\/recapitulatif$/.test(u)){var e=u.split("/")[3];d=RECAP[e]||{canaux:[]}}
  else if(u.indexOf("/api/schedule?espace=")===0)d=POSTS;
  else if(/\/validation-client$/.test(u))d={ok:true};
  else {st=404;d={detail:"?"}}
  return Promise.resolve({ok:st<300,status:st,json:function(){return Promise.resolve(d)}})};
window.__dzDialogue={confirmer:function(msg,o){dial.push([msg,o]);return Promise.resolve(REPONSE)}};
window.__dzGardeClient={etiquette:function(s){return s==="a_valider"?window.dzT("scheduler.etat.a_valider"):null}};
__PC__
__SCRIPT__
function attendre(ms){return new Promise(function(ok){setTimeout(ok,ms||90)})}
function bandeaux(){return tous(body,function(n){return n.getAttribute("data-dz-pour-qui")!==null})}
function bandeau(){return bandeaux()[0]||null}
function voile(){return tous(body,function(n){return n.getAttribute("data-dz-pq-boite")!==null})[0]||null}
function dans(r,attr,val){return r?tous(r,function(n){return n.getAttribute(attr)!==null&&(val===undefined||n.getAttribute(attr)===val)}):[]}
function txt(n,brut){if(!n)return "";if(!brut&&n.getAttribute("data-dz-brut")!==null)return "";return n._t+n.enfants.map(function(e){return txt(e,brut)}).join("")}
function attrsTxt(n){var o=[];tous(n,function(x){return x.getAttribute("data-dz-brut")===null}).forEach(function(x){["title","aria-label"].forEach(function(a){if(x.getAttribute(a))o.push(x.getAttribute(a))})});return o.join(" | ")}
function etat(){var b=bandeau();var h=b&&b.parentNode?b.parentNode.enfants:[];
  return {n:bandeaux().length,frere:!!b&&!!b.parentNode&&b.parentNode.tagName==="MAIN"&&h.indexOf(b)===1&&h[0].tagName==="HEADER",
    texte:txt(b,true),style:b?b.getAttribute("style")||"":"",cache:!!b&&/display:\s*none/.test(b.getAttribute("style")||""),
    attr:b?[b.getAttribute("data-espace"),b.getAttribute("data-dz-pq-espace"),b.getAttribute("role"),b.getAttribute("aria-label")]:null,fiche:dans(b,"data-dz-pq-fiche").length,
    client:dans(b,"data-dz-pq-client").length,projet:dans(b,"data-dz-pq-projet").length,
    pastille:(dans(b,"data-dz-pq-pastille")[0]||{getAttribute:function(){return ""}}).getAttribute("style")||""}}
var R={};
(async function(){
 var P=window.__dzPourQui;R.api=[typeof P.rafraichir,typeof P.ouvrirFiche];
 await attendre();
 /* P1 */
 R.p1_sched=etat();
 STOCK.dz_view="settings";muter();await attendre();R.p1_settings=etat();
 STOCK.dz_view="library";window.dispatchEvent(new CustomEvent("deepotus:navigate",{detail:{view:"library"}}));await attendre();R.p1_lib=etat();
 STOCK.dz_view="quick";muter();await attendre();R.p1_quick=etat().n;
 STOCK.dz_view="studio";muter();await attendre();R.p1_studio=etat().n;
 STOCK.dz_view="montage";muter();await attendre();R.p1_montage=etat().n;
 STOCK.dz_view="scheduler";muter();await attendre();
 MAIN.remove();MAIN=poserMain();muter();await attendre();R.p1_recree=etat();
 muter();muter();await attendre();R.p1_stable=etat().n;
 /* P2 */
 ACTIF="marque_c";window.dispatchEvent(new Event("deepotus:espace-refresh"));await attendre();R.p2_marque=etat();
 ACTIF="prod_b";window.dispatchEvent(new Event("deepotus:espace-refresh"));await attendre();R.p2_produit=etat();
 ACTIF="prod_d";window.dispatchEvent(new Event("deepotus:espace-refresh"));await attendre();R.p2_produit_marque=etat();
 SOCIETE="";ACTIF="cli_a";window.dispatchEvent(new Event("deepotus:espace-refresh"));await attendre();R.p2_sans_societe=etat();
 SOCIETE="Acme Corp";PROJET={id:""};window.dispatchEvent(new Event("dz-projets"));await attendre();R.p2_sans_projet=etat();
 PROJET={id:"proj_1",nom:"Spring launch"};await P.rafraichir();R.p2_client=etat();
 /* P9 I1 : un hôte de dz-projet-canaux posé dans main est toujours rempli par l'observateur */
 var hote=new Noeud("span");hote.setAttribute("data-dz-projet-canaux","proj_1");hote.setAttribute("data-espace","cli_a");MAIN.appendChild(hote);
 hote.setAttribute("data-canaux","cpt_x");await attendre();R.p9_hote=[hote.innerHTML.indexOf("data-dz-canal")>=0,hote.getAttribute("style")||""];
 hote.remove();
 ACTIF="prod_b";window.dispatchEvent(new Event("deepotus:espace-refresh"));await attendre();R.p9_change=etat();
 ACTIF="cli_a";window.dispatchEvent(new Event("deepotus:espace-refresh"));await attendre();R.p9_retour=etat();
 R.p2_aucun=await P.ouvrirFiche("marque_c");R.p2_aucun_boite=!!voile();
 /* le bouton du bandeau ouvre la fiche */
 appels=[];dans(bandeau(),"data-dz-pq-fiche")[0].declencher("click");await attendre();
 var v=voile();R.boite=!!v&&v.getAttribute("data-dz-pq-boite");R.boite_titre=v&&v.getAttribute("aria-label");
 R.boite_get=appels.filter(function(a){return a.m==="GET"}).map(function(a){return a.u}).sort();
 /* P3 */
 R.p3_lignes=dans(v,"data-dz-pq-consentement").map(function(n){return [n.getAttribute("data-dz-pq-consentement"),dans(n,"data-dz-pq-revoquer").length]});
 appels=[];REPONSE=false;dans(v,"data-dz-pq-revoquer","x:111")[0].declencher("click");await attendre();
 R.p3_non=[dial.length,appels.filter(function(a){return a.m==="POST"}).length];
 R.p3_dial=dial[0];
 REPONSE=true;dans(voile(),"data-dz-pq-revoquer","x:111")[0].declencher("click");await attendre();
 R.p3_post=appels.filter(function(a){return a.m==="POST"}).map(function(a){return [a.u,JSON.stringify(a.b)]});
 R.p3_msg=(dans(voile(),"data-dz-pq-msg")[0]||{textContent:""}).textContent;
 R.p3_apres=dans(voile(),"data-dz-pq-revoquer").length;
 /* P4 */
 v=voile();var sc=dans(v,"data-dz-pq-ajout-canal")[0],sm=dans(v,"data-dz-pq-ajout-moyen")[0];
 R.p4_canaux=sc?tous(sc,function(n){return n.tagName==="OPTION"}).map(function(n){return n.value}):null;
 R.p4_moyens=sm?tous(sm,function(n){return n.tagName==="OPTION"}).map(function(n){return n.value}):null;
 sc.value="youtube:UC9";sc.declencher("change");sm.value="whatsapp";sm.declencher("change");
 appels=[];dans(v,"data-dz-pq-ajouter")[0].declencher("click");await attendre();
 R.p4_post=appels.filter(function(a){return a.m==="POST"}).map(function(a){return [a.u,JSON.stringify(a.b)]});
 /* P5 */
 v=voile();R.p5_posts=dans(v,"data-dz-pq-post").map(function(n){return [n.getAttribute("data-dz-pq-post"),txt(n,true)]});
 var pm=dans(dans(v,"data-dz-pq-post","p1")[0],"data-dz-pq-post-moyen")[0];pm.value="doigt";pm.declencher("change");
 appels=[];evenements=[];dans(v,"data-dz-pq-valide","p1")[0].declencher("click");await attendre();
 R.p5_valide=appels.filter(function(a){return a.m==="POST"}).map(function(a){return [a.u,JSON.stringify(a.b)]});
 R.p5_evts=evenements.slice();
 appels=[];evenements=[];dans(voile(),"data-dz-pq-corriger","p3")[0].declencher("click");await attendre();
 R.p5_corriger=appels.filter(function(a){return a.m==="POST"}).map(function(a){return [a.u,JSON.stringify(a.b)]});
 R.p5_evts2=evenements.slice();
 /* P6 */
 R.p6=dans(voile(),"data-dz-pq-journal").map(function(n){return n.getAttribute("data-dz-pq-journal")});
 R.p6_texte=(dans(voile(),"data-dz-pq-journal")[0]||{textContent:""}).textContent;
 /* t326 : Tab piégé, Échap ferme */
 v=voile();var foc=v.querySelectorAll("button, input, select, textarea, a[href], [tabindex]").filter(function(n){return !n.disabled&&n.offsetParent!==null});
 function touche(k,shift){var ev={key:k,shiftKey:!!shift,defaultPrevented:false,preventDefault:function(){ev.defaultPrevented=true},stopPropagation:function(){}};
   (docEcoutes.keydown||[]).forEach(function(f){f(ev)});return ev}
 foc[foc.length-1].focus();var t1=touche("Tab");R.tab=[foc.indexOf(document.activeElement),t1.defaultPrevented,foc.length>3];
 foc[0].focus();touche("Tab",true);R.tab_haut=foc.indexOf(document.activeElement)===foc.length-1;
 touche("Escape");await attendre();R.echap=!voile();
 /* P9 M2 : en publie_en_son_nom, un post programmé sans validation n'est pas en pause : pas listé */
 MODE="publie_en_son_nom";var pm2=P.ouvrirFiche("cli_a");await attendre();
 R.p9_mode=dans(voile(),"data-dz-pq-post").map(function(n){return n.getAttribute("data-dz-pq-post")});
 dans(voile(),"data-dz-pq-fermer")[0].declencher("click");await pm2;MODE="valide_par_client";
 /* P10 t311 tâche 6 : « Envoyer au client par WhatsApp », état et note de correction */
 CONTACT="06 12 34 56 78";VALW={p3:{etat:"corrige",note:"Logo plus grand"},p1:{etat:"envoye"}};
 var pw=P.ouvrirFiche("cli_a");await attendre();v=voile();
 R.p10_btn=dans(v,"data-dz-pour-qui-wa-valider").map(function(n){return n.getAttribute("data-dz-pour-qui-wa-valider")});
 R.p10_note=(dans(v,"data-dz-pq-wa-note","p3")[0]||{textContent:""}).textContent;
 R.p10_etat=dans(v,"data-dz-pq-wa-etat").map(function(n){return [n.getAttribute("data-dz-pq-wa-etat"),n.textContent]});
 R.p10_get=appels.filter(function(a){return a.m==="GET"&&/^\/api\/schedule\/[^/]+\/client$/.test(a.u)}).map(function(a){return a.u}).sort();
 appels=[];dans(v,"data-dz-pour-qui-wa-valider","p1")[0].declencher("click");await attendre();
 R.p10_post=appels.filter(function(a){return a.m==="POST"}).map(function(a){return a.u});
 R.p10_msg=(dans(voile(),"data-dz-pq-msg")[0]||{textContent:""}).textContent;
 dans(voile(),"data-dz-pq-fermer")[0].declencher("click");await pw;
 CONTACT="";var pw2=P.ouvrirFiche("cli_a");await attendre();
 R.p10_sans=dans(voile(),"data-dz-pour-qui-wa-valider").length;
 dans(voile(),"data-dz-pq-fermer")[0].declencher("click");await pw2;CONTACT="06 12 34 56 78";
 /* P7 : en anglais */
 window.dzT=function(k,v){var e=(window.DZ_I18N||{})[k];var s=e?(e.en||e.fr):k;if(v)s=s.replace(/\{(\w+)\}/g,function(m,n){return v[n]!=null?String(v[n]):m});return s};
 window.dzLang=function(){return "en"};
 await P.rafraichir();R.en_bandeau=[txt(bandeau()),attrsTxt(bandeau())].join(" || ");
 var pf=P.ouvrirFiche("cli_a");await attendre();v=voile();
 R.en_boite=[txt(v),attrsTxt(v)].join(" || ");
 REPONSE=true;dans(v,"data-dz-pq-revoquer","x:111")[0].declencher("click");await attendre();
 R.en_dial=dial[dial.length-1];R.en_msg=(dans(voile(),"data-dz-pq-msg")[0]||{textContent:""}).textContent;
 R.en_boite2=[txt(voile()),attrsTxt(voile())].join(" || ");
 dans(voile(),"data-dz-pq-fermer")[0].declencher("click");R.en_ferme=await pf;R.en_ferme_boite=!!voile();
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""


def node(code):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "h.js"
        f.write_text(code, "utf-8")
        p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    try:
        return json.loads(p.stdout or "{}")
    except ValueError:
        return {"erreur": (p.stdout + p.stderr)[-900:]}


print("\n[P0] le script sous node")
R = {}
if NODE and SHARED.is_file():
    R = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + HARNAIS.replace("__PC__", PC_TXT).replace("__SCRIPT__", TXT))
check("P0.1 le script existe et s'exécute sous node (faux DOM, faux fetch)", bool(R) and "erreur" not in R,
      str(R.get("erreur", "script absent" if not SHARED.is_file() else "")))
G = R.get
check("P0.2 window.__dzPourQui = {rafraichir, ouvrirFiche}", G("api") == ["function", "function"], str(G("api")))

print("\n[P1] le bandeau")
s = G("p1_sched") or {}
check("P1.1 scheduler : UN bandeau, frère juste après `main > header` (jamais dans un enfant React)",
      s.get("n") == 1 and s.get("frere"), str(s))
check("P1.2 pastille de la couleur de l'espace, nom de l'espace, « Projet : <nom> »",
      "#aa3311" in s.get("pastille", "") and "Acme space" in s.get("texte", "")
      and F("espaces.pourqui.projet", nom="Spring launch") in s.get("texte", "") and s.get("projet") == 1, str(s))
check("P1.3 settings : le bandeau est retiré", (G("p1_settings") or {}).get("n") == 0, str(G("p1_settings")))
check("P1.4 deepotus:navigate vers library : le bandeau revient, à sa place",
      (G("p1_lib") or {}).get("n") == 1 and (G("p1_lib") or {}).get("frere"), str(G("p1_lib")))
check("P1.5 quick et studio : présent ; montage : absent",
      G("p1_quick") == 1 and G("p1_studio") == 1 and G("p1_montage") == 0,
      str([G("p1_quick"), G("p1_studio"), G("p1_montage")]))
check("P1.6 `main` recréé : le bandeau suit le nouvel entête, un seul ; des mutations répétées n'en ajoutent pas",
      (G("p1_recree") or {}).get("n") == 1 and (G("p1_recree") or {}).get("frere") and G("p1_stable") == 1,
      str([G("p1_recree"), G("p1_stable")]))

print("\n[P2] l'espace gouverné par un client")
c = G("p2_client") or {}
LISERE = "border-left:3px solid #aa3311"
check("P2.1 espace client : liseré 3 px de sa couleur, « Client : <société> », bouton « Fiche client »",
      LISERE in c.get("style", "")
      and F("espaces.pourqui.client", nom="Acme Corp") in c.get("texte", "") and c.get("fiche") == 1
      and F("espaces.pourqui.fiche") in c.get("texte", ""), str(c))
m_ = G("p2_marque") or {}
check("P2.2 marque : ni liseré, ni « Client », ni bouton",
      m_.get("n") == 1 and "border-left:3px" not in m_.get("style", "") and m_.get("fiche") == 0 and m_.get("client") == 0, str(m_))
p_ = G("p2_produit") or {}
check("P2.3 produit sous un client : liseré de SA couleur, le client nommé, le bouton",
      "border-left:3px solid #22aa55" in p_.get("style", "") and F("espaces.pourqui.client", nom="Acme Corp") in p_.get("texte", "")
      and p_.get("fiche") == 1 and "Acme widget" in p_.get("texte", ""), str(p_))
pm_ = G("p2_produit_marque") or {}
check("P2.4 produit sous une marque : rien du client", pm_.get("fiche") == 0 and pm_.get("client") == 0
      and "border-left:3px" not in pm_.get("style", ""), str(pm_))
check("P2.5 société vide : le client est nommé par son espace",
      F("espaces.pourqui.client", nom="Acme space") in (G("p2_sans_societe") or {}).get("texte", ""), str(G("p2_sans_societe")))
check("P2.6 aucun projet actif (dz-projets relu) : pas de « Projet »", (G("p2_sans_projet") or {}).get("projet") == 0
      and "Spring launch" not in (G("p2_sans_projet") or {}).get("texte", ""), str(G("p2_sans_projet")))
check("P2.7 ouvrirFiche d'un espace sans client : null, aucune boîte", G("p2_aucun") is None and G("p2_aucun_boite") is False)
check("P2.8 « Fiche client » ouvre la boîte du client, titre qui le nomme ; lit fiche, récapitulatifs des espaces gouvernés, posts",
      G("boite") == "cli_a" and G("boite_titre") == F("espaces.pourqui.titre", nom="Acme Corp")
      and "/api/espaces/cli_a/client" in (G("boite_get") or []) and "/api/espaces/cli_a/recapitulatif" in (G("boite_get") or [])
      and "/api/espaces/prod_b/recapitulatif" in (G("boite_get") or []) and "/api/schedule?espace=*" in (G("boite_get") or []),
      str([G("boite"), G("boite_titre"), G("boite_get")]))

print("\n[P3] Révoquer")
check("P3.1 une ligne par consentement ; « Révoquer » seulement pour celui en cours",
      G("p3_lignes") == [["x:111", 1], ["telegram:acme", 0]], str(G("p3_lignes")))
d0 = G("p3_dial") or ["", {}]
check("P3.2 confirmation par __dzDialogue.confirmer (danger, nomme le canal) ; non : RIEN n'est envoyé",
      G("p3_non") == [1, 0] and "x:111" in d0[0] and (d0[1] or {}).get("danger") is True
      and (d0[1] or {}).get("ok") == F("espaces.pourqui.revoquer"), str([G("p3_non"), d0]))
check("P3.3 oui : POST …/consentements/revoquer {canal_id}",
      G("p3_post") == [["/api/espaces/cli_a/client/consentements/revoquer", '{"canal_id":"x:111"}']], str(G("p3_post")))
check("P3.4 le nombre de posts mis en pause RENDU par la route est dit dans la boîte ; plus de « Révoquer »",
      G("p3_msg") == F("espaces.pourqui.en_pause", n=2) and G("p3_apres") == 0, str([G("p3_msg"), G("p3_apres")]))

print("\n[P4] Ajouter un consentement")
check("P4.1 canaux proposés = les canal_id des récapitulatifs des espaces gouvernés (jamais un canal_id vide)",
      sorted(G("p4_canaux") or []) == ["instagram:b1", "x:111", "youtube:UC9"], str(G("p4_canaux")))
check("P4.2 moyens = écrit, WhatsApp, doigt", G("p4_moyens") == ["ecrit", "whatsapp", "doigt"], str(G("p4_moyens")))
check("P4.3 « Ajouter » envoie {canal_id, permis:[\"publier\"], moyen}",
      G("p4_post") == [["/api/espaces/cli_a/client/consentements",
                        '{"canal_id":"youtube:UC9","permis":["publier"],"moyen":"whatsapp"}']], str(G("p4_post")))

print("\n[P5] posts à valider")
pp = G("p5_posts") or []
check("P5.1 les posts « a_valider » des espaces gouvernés (client et produit), libellé de __dzGardeClient.etiquette ; "
      "M2 : aussi les programmés/prêts sans validation (« en pause : à valider »), jamais un post validé",
      [x[0] for x in pp] == ["p1", "p2", "p3", "p6"]
      and all(F("scheduler.etat.a_valider") in x[1] for x in pp if x[0] in ("p1", "p3"))
      and all(F("espaces.pourqui.en_pause_a_valider") in x[1] for x in pp if x[0] in ("p2", "p6"))
      and "Teaser" in pp[0][1], str(pp))
check("P9.D3 heure UTC du post en heure LOCALE (Asia/Tokyo, UTC+9), changement de jour compris",
      "2026-11-02 18:00" in pp[0][1] and "2026-11-02 09:00" not in pp[0][1]
      and len(pp) > 3 and "2026-11-06 08:30" in pp[3][1], str(pp))
check("P5.2 « Validé par le client » -> validation-client {reponse:valide, moyen choisi}, puis deepotus:schedule-recharger",
      G("p5_valide") == [["/api/schedule/p1/validation-client", '{"reponse":"valide","moyen":"doigt"}']]
      and "deepotus:schedule-recharger" in (G("p5_evts") or []), str([G("p5_valide"), G("p5_evts")]))
check("P5.3 « À corriger » -> {reponse:corriger, moyen}, puis deepotus:schedule-recharger",
      G("p5_corriger") == [["/api/schedule/p3/validation-client", '{"reponse":"corriger","moyen":"ecrit"}']]
      and "deepotus:schedule-recharger" in (G("p5_evts2") or []), str([G("p5_corriger"), G("p5_evts2")]))

print("\n[P6] journal")
j = G("p6") or []
check("P6.1 au plus 50 lignes, plus récente d'abord", len(j) == 50 and j == sorted(j, reverse=True)
      and j[0] == "2026-10-15T09:00:00", str(j[:3]) + str(len(j)))
check("P6.2 une ligne dit quoi et qui, traduits", F("espaces.pourqui.qui_utilisateur") in (G("p6_texte") or "")
      or F("espaces.pourqui.qui_client") in (G("p6_texte") or "") or F("espaces.pourqui.qui_telephone") in (G("p6_texte") or ""),
      str(G("p6_texte")))

print("\n[T] clavier")
check("T.1 Tab piégé (dernier -> premier, Maj+Tab premier -> dernier), Échap ferme",
      (G("tab") or [None])[:3] == [0, True, True] and G("tab_haut") and G("echap"), str([G("tab"), G("tab_haut"), G("echap")]))

print("\n[P10] t311 tâche 6 : validation par WhatsApp")
check("P10.1 « Envoyer au client par WhatsApp » seulement pour les posts a_valider (pas les programmés en pause)",
      G("p10_btn") == ["p1", "p3"], str(G("p10_btn")))
check("P10.2 fiche sans contact WhatsApp : aucun bouton", G("p10_sans") == 0, str(G("p10_sans")))
check("P10.3 clic : POST /api/schedule/p1/validation-whatsapp, puis le message de résultat",
      G("p10_post") == ["/api/schedule/p1/validation-whatsapp"] and G("p10_msg") == F("espaces.pourqui.wa_envoye"),
      str([G("p10_post"), G("p10_msg")]))
check("P10.4 note de correction affichée (validation_whatsapp.note de GET /api/schedule/{id}/client) ; état envoyé dit",
      F("espaces.pourqui.wa_note") in (G("p10_note") or "") and "Logo plus grand" in (G("p10_note") or "")
      and G("p10_etat") == [["p1", F("espaces.pourqui.wa_attente")]]
      and "/api/schedule/p1/client" in (G("p10_get") or []) and "/api/schedule/p3/client" in (G("p10_get") or []),
      str([G("p10_note"), G("p10_etat"), G("p10_get")]))

print("\n[P7] en anglais")
ACCENTS = re.compile("[éèêëàâçùûôîïœÉÈÀÇ«»]")
DICO = json.loads(DICO_P.read_text("utf-8"))
POURQUI = {k: v for k, v in DICO.items() if k.startswith("espaces.pourqui.")}
frags = set()
for k, v in POURQUI.items():
    for f in re.split(r"\{\w+\}", v["fr"]):
        f = f.strip(" :·—()?.,")
        if len(f) >= 4 and f not in v["en"]:
            frags.add(f)


def sans_fr(t):
    return bool(t) and not ACCENTS.search(t) and not [f for f in frags if f in t]


for nom_, cle in (("bandeau", "en_bandeau"), ("boîte", "en_boite"), ("boîte après révocation", "en_boite2")):
    t = G(cle) or ""
    check(f"P7 {nom_} : aucun texte français", sans_fr(t),
          f"{ACCENTS.findall(t)} {[f for f in frags if f in t]} :: {t[:400]}")
check("P7 bandeau EN : « Client: », « Project: », « Client sheet »",
      EN("espaces.pourqui.client", nom="Acme Corp") in (G("en_bandeau") or "")
      and EN("espaces.pourqui.projet", nom="Spring launch") in (G("en_bandeau") or "")
      and EN("espaces.pourqui.fiche") in (G("en_bandeau") or ""), str(G("en_bandeau"))[:300])
ed = G("en_dial") or ["", {}]
check("P7 la confirmation et le nombre en pause en anglais",
      sans_fr(ed[0]) and sans_fr((ed[1] or {}).get("titre", "")) and G("en_msg") == EN("espaces.pourqui.en_pause", n=2),
      str([ed, G("en_msg")]))
check("P7 « Close » ferme la boîte, la promesse rend null", G("en_ferme") is None and G("en_ferme_boite") is False)

print("\n[P9] revue finale t309 : bandeau au changement d'espace (I1), a11y, posts en pause (M2), heure locale (D3)")
for k in ("p2_marque", "p2_produit", "p2_client", "p9_change", "p9_retour"):
    e_ = G(k) or {}
    check(f"P9.I1 {k} : le bandeau redessiné sur place reste visible et rempli (l'observateur de dz-projet-canaux.js ne le vide plus)",
          e_.get("n") == 1 and not e_.get("cache") and len(e_.get("texte", "")) > 3, str(e_))
check("P9.I1 le changement d'espace redessine le bon espace (produit puis client)",
      "Acme widget" in (G("p9_change") or {}).get("texte", "") and "Acme space" in (G("p9_retour") or {}).get("texte", "")
      and (G("p9_change") or {}).get("fiche") == 1, str([G("p9_change"), G("p9_retour")]))
check("P9.I1 le bandeau porte data-dz-pq-espace, jamais data-espace (attribut observé par dz-projet-canaux.js)",
      ((G("p9_retour") or {}).get("attr") or [0, 0])[:2] == [None, "cli_a"], str((G("p9_retour") or {}).get("attr")))
check("P9.I1 un hôte de dz-projet-canaux.js est toujours rempli par l'observateur (glyphes, visible)",
      (G("p9_hote") or [False])[0] is True and "display:none" not in (G("p9_hote") or [0, "display:none"])[1], str(G("p9_hote")))
check("P9.a11y role=region et aria-label traduit (plus de role=status annoncé à chaque redessin)",
      ((G("p2_client") or {}).get("attr") or [0, 0, 0, 0])[2:] == ["region", F("espaces.pourqui.bandeau")],
      str((G("p2_client") or {}).get("attr")))
check("P9.M2 en publie_en_son_nom : seuls les posts a_valider (aucun programmé n'est en pause pour validation)",
      G("p9_mode") == ["p1", "p3"], str(G("p9_mode")))
check("P9.D3 dates de la fiche (locales, sans fuseau) telles quelles", "2026-10-15 09:00" in (G("p6_texte") or ""),
      str(G("p6_texte")))
check("P9.EN « Active space » sur le bandeau anglais", EN("espaces.pourqui.bandeau") in (G("en_bandeau") or ""),
      str(G("en_bandeau"))[:300])

print("\n[P8] livraison")
check("P8.1 copie dist OCTET POUR OCTET", lambda: SHARED.read_bytes() == DIST.read_bytes())
HTML = (REPO / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
BALISE = '<script src="/shared/dz-pour-qui.js"></script>'
check("P8.2 index.html charge le script UNE fois, après dz-garde-client.js",
      lambda: HTML.count(BALISE) == 1 and HTML.count("dz-pour-qui.js") == 1
      and HTML.index('<script src="/shared/dz-garde-client.js"></script>') < HTML.index(BALISE))
check("P8.3 aucun emoji, ni window.alert/confirm/prompt, ni arrondi de châssis",
      bool(TXT) and not re.search("[\U0001F300-\U0001FAFF☀-➿]", TXT)
      and not re.search(r"window\.(alert|confirm|prompt)\(", TXT)
      and not re.search(r"border-radius:\s*(?!0[;\"'])", TXT))
check("P8.4 le bundle ne connaît pas ce script (aucun maillon)", "__dzPourQui" not in BUNDLE.read_text("utf-8", errors="replace"))
check("P8.5 clés espaces.pourqui.* à trois segments, FR et EN non vides, mêmes {variables}",
      bool(POURQUI) and all(re.fullmatch(r"espaces\.pourqui\.[a-z_]+", k) and v.get("fr", "").strip() and v.get("en", "").strip()
                            and sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"]))
                            for k, v in POURQUI.items()))
emp = {k for k in re.findall(r'"(espaces\.pourqui\.[a-z_]+)"', TXT) if not k.endswith("_")}
for p_, xs in (("moyen_", ("ecrit", "whatsapp", "doigt")),
               ("quoi_", ("mode", "consentement", "revocation", "publication", "validation", "import")),
               ("qui_", ("utilisateur", "client", "telephone"))):
    if f'"espaces.pourqui.{p_}"' in TXT:
        emp |= {f"espaces.pourqui.{p_}{x}" for x in xs}
check("P8.6 toutes les clés employées existent, aucune orpheline", bool(emp) and emp == set(POURQUI),
      f"sans traduction {sorted(emp - set(POURQUI))} orphelines {sorted(set(POURQUI) - emp)}")
check("P8.7 les autres clés employées existent (commun.*, scheduler.*)",
      all(k in AIDE.DICO for k in re.findall(r'"((?:commun|scheduler)\.[a-z_]+\.[a-z_.]+)"', TXT)))
check("P8.8 l'assemblé dz-i18n-dico.js est à jour, shared == dist", lambda: subprocess.run(
    [sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True).returncode == 0
    and (REPO / "frontend/shared/dz-i18n-dico.js").read_bytes() == (REPO / "frontend/dist/shared/dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
