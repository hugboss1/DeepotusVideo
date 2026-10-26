# -*- coding: utf-8 -*-
"""t307 tâche 4 (25/10/2026) — l'ÉCRAN des canaux d'un projet de la Bibliothèque, par la COUCHE montage.

La barre « Projet » vit dans frontend/patches/montage.js (bloc #78) : le bloc MONTAGE du bundle EST cette source
(scripts/refresh_layer.py). Les retouches t307 passent par la saisie L3 (scripts/i18n_l3/montage_i.py ->
i18n_l3_generer.py -> refresh_layer) avec leur miroir G1 (scripts/icones/g1_generer.py RETOUCHES) : aides dzPcEc et
dzPcB, dzProjCharger qui garde espace_id et canaux, appels de la barre à longueur égale. AUCUN maillon de queue.
Le reste est dans frontend/shared/dz-projet-canaux.js (window.__dzProjetCanaux : boîte, hôte des glyphes).
[1] la couche     pas de patch_bundle_dzcanaux.py ; les retouches dans montage.js ET dans le bloc du bundle, une fois ;
                  le bloc = la source (refresh_layer --check) ; L3 et G1 --check à jour ;
[2] réversible    la couche d'avant L3 n'a plus les retouches (couche_avant_i18n_l3), la table L3 les porte (montage_i) ;
[3] comptes figés x.useState( 731, v2.8.0 ×4, DzTracks 181, confirmations ×30, CRLF en octets ;
[4] le script partagé copie dist identique, balise dans la SPA après dz-plafonds.js et dz-campagnes.js ;
[5] la boîte sous node (faux DOM, faux fetch) : seuls les comptes de l'espace du projet, le PUT porte la bonne liste,
    l'évènement dz-projet-canaux porte la vue relue ; 409 et 404 traduits DANS la boîte ; l'hôte rempli de glyphes ;
[6] la barre sous node : hôte + bouton « Canaux » qui appelle ouvrir(f), écoute de « dz-projet-canaux » ;
[7] textes : clés projets.canaux.* FR et EN, toutes employées, aucune orpheline.
Run : & $PY tests/test_projets_canaux_ecran.py   (depuis backend/)
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
RAW = (ASSETS / "index-BEOJX8L5.js").read_bytes()
B = RAW.decode("utf-8")
SHARED = REPO / "frontend" / "shared" / "dz-projet-canaux.js"
DIST = REPO / "frontend" / "dist" / "shared" / "dz-projet-canaux.js"
COUCHE_P = REPO / "frontend" / "patches" / "montage.js"
COUCHE = COUCHE_P.read_bytes().decode("utf-8")
DICO_P = REPO / "frontend" / "shared" / "i18n" / "projets.json"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
DEB, FIN_M = "/*__DZ_MONTAGE_BEGIN__*/", "/*__DZ_MONTAGE_END__*/"
BLOC = B.split(DEB, 1)[1].split(FIN_M, 1)[0] if B.count(DEB) == 1 else ""
RETOUCHES = ["function dzPcEc(h,on){", "function dzPcB(ch,f){", "espace_id:d.espace_id,canaux:d.canaux,",
             "dzPcEc(h,1);", "dzPcEc(h,0)", "if(dzPcB(ch,f)){", 'dzT("projets.canaux.bouton")', 'className:"dzpc-btn"',
             '"data-dz-projet-canaux":f.id']


def n_(t):
    return t.replace(chr(13) + chr(10), chr(10)).lstrip(chr(0xfeff)).strip(chr(10))


def outil(*args):
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=str(REPO))
    return p.returncode, (p.stdout + p.stderr)


print("\n[1] la couche")
check("1.1 aucun maillon de queue : ni patch_bundle_dzcanaux.py, ni frontend/patches/projet-canaux.js, ni marqueur",
      not (REPO / "scripts" / "patch_bundle_dzcanaux.py").exists()
      and not (REPO / "frontend" / "patches" / "projet-canaux.js").exists() and "/*__dzcanaux*/" not in B)
check("1.2 chaque retouche une fois dans montage.js", all(COUCHE.count(t) == 1 for t in RETOUCHES),
      str([(t, COUCHE.count(t)) for t in RETOUCHES if COUCHE.count(t) != 1]))
check("1.3 chaque retouche une fois dans le bloc MONTAGE du bundle, et nulle part ailleurs",
      all(BLOC.count(t) == 1 and B.count(t) == 1 for t in RETOUCHES))
check("1.4 le bloc MONTAGE du bundle EST la source montage.js (rafraîchi par refresh_layer --layer montage)",
      lambda: n_(BLOC) == n_(COUCHE))
check("1.5 saisie L3 à jour (i18n_l3_generer --check)", lambda: outil("scripts/i18n_l3_generer.py", "--check")[0] == 0)
check("1.6 table G1 à jour (g1_generer --check)", lambda: outil("scripts/icones/g1_generer.py", "--check")[0] == 0)
check("1.7 la barre appelle les aides à longueur égale (commentaires datés, ch.push indenté), l'en-tête du bloc #78 compensé",
      "dzPcEc(h,1);/*t307 (25/10/2026) G1*/" in COUCHE and "dzPcEc(h,0)/* t307 (25/10/2026), G1" in COUCHE
      and chr(10) + "    ch.push(bouton(ici?" in COUCHE.replace(chr(13), "") and "Un seul projet épinglé" in COUCHE
      and not any(l != l.rstrip(" ") for l in COUCHE.replace(chr(13), "").split(chr(10)) if "dzPc" in l))

print("\n[2] réversible")
check("2.1 la couche d'avant L3 n'a plus aucune retouche t307",
      lambda: not any(t in AIDE.couche_avant_i18n_l3(COUCHE) for t in RETOUCHES[:6]))
TABLE = json.loads((REPO / "scripts" / "i18n_l3_paires.json").read_bytes().decode("utf-8"))
check("2.2 la table L3 porte les six retouches (groupe montage_i)",
      sum(1 for e in TABLE["couches"]["montage"] if e["groupe"] == "montage_i" and ("dzPc" in e["apres"]
          or "canaux:d.canaux" in e["apres"] or "Un seul projet épinglé" in e["apres"])) == 6)

print("\n[3] comptes figés")
COMPTES = {"x.useState(": 731, "v2.8.0": 4, "DzTracks": 181, "await window.__dzDialogue.confirmer(": 30,
           "/*__dzagentplan*/": 1, "/*__dzrecette*/": 1, "function DzProjetsBar(": 1,
           "r.jsx(DzProjetsBar,{f:dzPF,setF:dzPFs})": 1}
for jeton, n in COMPTES.items():
    check(f"3 compte {jeton!r} = {n}", B.count(jeton) == n, str(B.count(jeton)))
check("3.x CRLF partout (en octets)", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
if NODE:
    t = pathlib.Path(tempfile.mkdtemp()) / "b.mjs"
    t.write_bytes(RAW)
    rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("3.n node --check : le bundle PARSE", rc.returncode == 0, rc.stderr[-300:])

print("\n[4] le script partagé")
check("4.1 copie dist OCTET POUR OCTET", lambda: SHARED.read_bytes() == DIST.read_bytes())
HTML = (REPO / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
BALISE = '<script src="/shared/dz-projet-canaux.js"></script>'
check("4.2 balise dans la SPA, une fois, après dz-plafonds.js et dz-campagnes.js",
      lambda: HTML.count(BALISE) == 1 and HTML.index("/shared/dz-plafonds.js") < HTML.index(BALISE)
      and HTML.index("/shared/dz-campagnes.js") < HTML.index(BALISE))
check("4.3 aucun emoji ni window.alert/confirm/prompt dans le script",
      lambda: not re.search("[\U0001F300-\U0001FAFF☀-➿]", SHARED.read_text("utf-8"))
      and not re.search(r"window\.(alert|confirm|prompt)\(", SHARED.read_text("utf-8")))

# ── [5] la boîte, sous node : un faux DOM minimal (createElement, setAttribute, appendChild, textContent, events)
FAUX_DOM = r"""
function Noeud(tag){this.tagName=String(tag).toUpperCase();this.enfants=[];this.attrs={};this.ecoutes={};this._t="";this.parent=null;
  this.type="";this.checked=false;this.disabled=false;this.className="";this.innerHTML="";}
Object.defineProperty(Noeud.prototype,"textContent",{get:function(){return this._t+this.enfants.map(function(e){return e.textContent}).join("")},
  set:function(v){this._t=String(v);this.enfants=[]}});
Noeud.prototype.setAttribute=function(k,v){this.attrs[k]=String(v)};
Noeud.prototype.getAttribute=function(k){return k in this.attrs?this.attrs[k]:null};
Noeud.prototype.appendChild=function(e){e.parent=this;this.enfants.push(e);return e};
Noeud.prototype.addEventListener=function(t,f){(this.ecoutes[t]=this.ecoutes[t]||[]).push(f)};
Noeud.prototype.remove=function(){if(this.parent){var p=this.parent;p.enfants=p.enfants.filter(function(x){return x!==this},this);this.parent=null}};
Noeud.prototype.focus=function(){document.activeElement=this};
/* t326 : de quoi piéger Tab — querySelectorAll (tag, tag[attr], [attr], séparés par des virgules) et offsetParent (null si caché) */
Object.defineProperty(Noeud.prototype,"offsetParent",{get:function(){return /display:\s*none/.test(this.attrs.style||"")||this._cache?null:(this.parent||body)}});
Noeud.prototype.querySelectorAll=function(sel){var me=this,ps=sel.split(",").map(function(s){return s.trim()});
  return tous(this,function(n){return n!==me&&ps.some(function(p){var m=/^([a-z]*)(?:\[(\w+)\])?$/.exec(p);
    return !!m&&(m[1]||m[2])&&(!m[1]||n.tagName.toLowerCase()===m[1])&&(!m[2]||n.getAttribute(m[2])!==null)})})};
Noeud.prototype.removeAttribute=function(k){delete this.attrs[k]};
Noeud.prototype.declencher=function(t,ev){ev=ev||{};ev.target=ev.target||this;ev.preventDefault=function(){};(this.ecoutes[t]||[]).forEach(function(f){f(ev)})};
function tous(n,pred,out){out=out||[];if(pred(n))out.push(n);n.enfants.forEach(function(e){tous(e,pred,out)});return out}
var body=new Noeud("body"),docEcoutes={};
globalThis.document={body:body,activeElement:null,createElement:function(t){return new Noeud(t)},
  addEventListener:function(t,f){(docEcoutes[t]=docEcoutes[t]||[]).push(f)},
  removeEventListener:function(t,f){docEcoutes[t]=(docEcoutes[t]||[]).filter(function(g){return g!==f})}};
var evenements=[];window.dzT=dzT;   /* le prélude pose « var window » et dzT : le script lit window.dzT */
window.dispatchEvent=function(e){evenements.push(e)};
globalThis.CustomEvent=function(t,o){this.type=t;this.detail=o&&o.detail};
window.dzIcone=function(cle){return "<svg data-cle=\""+cle+"\"></svg>"};
"""
HARNAIS_BOITE = r"""
var appels=[],reponsePut=null;
var COMPTES={espace:"esp_a",comptes:[
  {id:"cpt_a",espace_id:"esp_a",plateforme:"x",libelle:"Compte A",handle:"@a",disponible:true},
  {id:"cpt_a2",espace_id:"esp_a",plateforme:"youtube",libelle:"Chaîne A",handle:"",disponible:false},
  {id:"cpt_b",espace_id:"esp_b",plateforme:"tiktok",libelle:"Compte B",handle:"@b",disponible:true}]};
globalThis.fetch=function(u,o){var m=(o&&o.method)||"GET";appels.push({u:u,m:m,b:o&&o.body?JSON.parse(o.body):null});
  var st=200,d={};
  if(u.indexOf("/api/comptes?espace=")===0)d=COMPTES;
  else if(/\/canaux$/.test(u)&&m==="PUT"){var rp=reponsePut||{st:200,d:{id:"proj_a",nom:"Abysses",espace_id:"esp_a",canaux:JSON.parse(o.body).canaux}};st=rp.st;d=rp.d}
  return Promise.resolve({ok:st<300,status:st,json:function(){return Promise.resolve(d)}})};
__SCRIPT__
function attendre(){return new Promise(function(ok){setTimeout(ok,15)})}
function boite(){return tous(body,function(n){return n.getAttribute("data-dz-projet-canaux-boite")!==null})[0]||null}
function lignes(){var b=boite();return b?tous(b,function(n){return n.getAttribute("data-dz-projet-canal")!==null}):[]}
function caseDe(id){var l=lignes().filter(function(n){return n.getAttribute("data-dz-projet-canal")===id})[0];return l?tous(l,function(n){return n.tagName==="INPUT"})[0]:null}
function bouton(){var b=boite();return b?tous(b,function(n){return n.getAttribute("data-dz-projet-canaux-enregistrer")!==null})[0]:null}
function erreur(){var b=boite();var e=b?tous(b,function(n){return n.getAttribute("data-dz-projet-canaux-erreur")!==null})[0]:null;return e?e.textContent:null}
var R={};
(async function(){
 var P=window.__dzProjetCanaux;R.api=[typeof P.ouvrir,typeof P.comptes,typeof P.connus,typeof P.glyphe];
 R.glyphes=["x","telegram","youtube","instagram","tiktok","inconnue"].map(P.glyphe);
 var projet={id:"proj_a",nom:"Abysses",espace_id:"esp_a",canaux:["cpt_a2"]};
 var prom=P.ouvrir(projet);await attendre();
 R.url=appels.filter(function(a){return a.m==="GET"}).map(function(a){return a.u});
 R.titre=boite()&&boite().getAttribute("aria-label");
 R.lignes=lignes().map(function(n){return n.getAttribute("data-dz-projet-canal")});
 R.glyphes_lignes=lignes().map(function(n){return tous(n,function(x){return x.getAttribute("data-dz-glyphe")!==null})[0].getAttribute("data-dz-glyphe")});
 R.coches=lignes().map(function(n){return tous(n,function(x){return x.tagName==="INPUT"})[0].checked});
 R.connus=(P.connus("esp_a")||[]).map(function(c){return c.id});
 var c=caseDe("cpt_a");c.checked=true;c.declencher("change");
 var c2=caseDe("cpt_a2");c2.checked=false;c2.declencher("change");
 reponsePut={st:409,d:{detail:"le compte Compte B (cpt_b) n'appartient pas à l'espace de ce post"}};
 appels=[];bouton().declencher("click");await attendre();
 R.put409=appels.filter(function(a){return a.m==="PUT"}).map(function(a){return [a.u,JSON.stringify(a.b)]});
 R.erreur409=erreur();R.ouverte409=!!boite();R.evt409=evenements.length;
 reponsePut={st:404,d:{detail:"compte inconnu : cpt_x"}};
 bouton().declencher("click");await attendre();R.erreur404=erreur();R.ouverte404=!!boite();
 reponsePut=null;appels=[];bouton().declencher("click");await attendre();
 R.put=appels.filter(function(a){return a.m==="PUT"}).map(function(a){return [a.u,JSON.stringify(a.b)]});
 R.fermee=!boite();R.evts=evenements.map(function(e){return [e.type,e.detail&&e.detail.canaux]});
 R.resolu=await prom;
 /* t326 A5 : Tab piégé dans la boîte (case A, case A2, Annuler, Enregistrer) */
 var pT=P.ouvrir({id:"proj_a",nom:"Abysses",espace_id:"esp_a",canaux:[]});await attendre();
 var cA=caseDe("cpt_a"),cA2=caseDe("cpt_a2"),bts=tous(boite(),function(n){return n.tagName==="BUTTON"}),bAnn=bts[0],bOk=bouton();
 var ordre=[cA,cA2,bAnn,bOk];
 function foc(){return ordre.indexOf(document.activeElement)}
 function touche(shift){var ev={key:"Tab",shiftKey:!!shift,defaultPrevented:false,preventDefault:function(){ev.defaultPrevented=true},stopPropagation:function(){}};
   (docEcoutes.keydown||[]).forEach(function(f){f(ev)});return ev}
 bOk.focus();var t1=touche(false);R.t_bas=[foc(),t1.defaultPrevented];
 cA.focus();var t2=touche(true);R.t_haut=[foc(),t2.defaultPrevented];
 cA.focus();touche(false);R.t_milieu=foc();
 document.activeElement=body;touche(false);R.t_dehors=foc();
 bOk.disabled=true;cA.focus();touche(true);R.t_desactive=foc();bOk.disabled=false;
 cA2._cache=true;cA.focus();touche(false);R.t_cache=foc();cA2._cache=false;
 bAnn.declencher("click");await pT;
 var p2=P.ouvrir({id:"proj_v",nom:"Vide",espace_id:"esp_z",canaux:[]});
 COMPTES={espace:"esp_z",comptes:[]};await attendre();
 R.vide=boite()?boite().textContent:"";
 tous(boite(),function(n){return n.tagName==="BUTTON"})[0].declencher("click");R.annule=await p2;R.annule_fermee=!boite();
 var hote=new Noeud("span");hote.setAttribute("data-dz-projet-canaux","proj_a");hote.setAttribute("data-canaux","cpt_a,cpt_q");hote.setAttribute("data-espace","esp_a");P.remplir(hote);await attendre();R.hote=[hote.innerHTML,hote.getAttribute("title")];
 var vide=new Noeud("span");vide.setAttribute("data-canaux","");vide.setAttribute("data-espace","esp_a");P.remplir(vide);R.hote_vide=[vide.innerHTML,vide.getAttribute("title"),vide.getAttribute("style")];
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""


def node(code):
    f = pathlib.Path(tempfile.mkdtemp()) / "h.js"
    f.write_text(code, "utf-8")
    p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except ValueError:
        return {"erreur": (p.stdout + p.stderr)[-800:]}


print("\n[5] la boîte, sous node")
R = {}
if NODE and SHARED.is_file():
    R = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + HARNAIS_BOITE.replace("__SCRIPT__", SHARED.read_text("utf-8")))
check("5.0 le script s'exécute sous node", bool(R) and "erreur" not in R, str(R.get("erreur", ""))[:800])
if R and "erreur" not in R:
    check("5.1 l'API : ouvrir, comptes, connus, glyphe", R["api"] == ["function"] * 4, str(R["api"]))
    check("5.2 glyphes Deepotus des plateformes (repli dz-action-publier)",
          R["glyphes"] == ["dz-reseau-x", "dz-reseau-telegram", "dz-reseau-youtube", "dz-reseau-instagram",
                           "dz-reseau-tiktok", "dz-action-publier"], str(R["glyphes"]))
    check("5.3 la liste demandée est celle de l'espace DU PROJET", R["url"] == ["/api/comptes?espace=esp_a"], str(R["url"]))
    check("5.4 seuls les comptes de l'espace du projet (le compte de l'autre espace n'est pas proposé)",
          R["lignes"] == ["cpt_a", "cpt_a2"] and R["connus"] == ["cpt_a", "cpt_a2"], str(R["lignes"]))
    check("5.5 une case par compte, cochée pour les canaux déjà posés ; glyphe par plateforme",
          R["coches"] == [False, True] and R["glyphes_lignes"] == ["dz-reseau-x", "dz-reseau-youtube"], str(R))
    check("5.6 le titre traduit nomme le projet", R["titre"] == "Canaux du projet Abysses", str(R["titre"]))
    check("5.7 le PUT porte la liste cochée", R["put409"] == [["/api/library/projets/proj_a/canaux", '{"canaux":["cpt_a"]}']]
          and R["put"] == [["/api/library/projets/proj_a/canaux", '{"canaux":["cpt_a"]}']], str(R["put409"]))
    check("5.8 409 : le message TRADUIT dans la boîte, qui reste ouverte, aucun évènement",
          R["erreur409"] == AIDE.fr("projets.canaux.erreur_espace") and R["ouverte409"] and R["evt409"] == 0, str(R["erreur409"]))
    check("5.9 404 : le message traduit dans la boîte, qui reste ouverte",
          R["erreur404"] == AIDE.fr("projets.canaux.erreur_inconnu") and R["ouverte404"], str(R["erreur404"]))
    check("5.10 succès : la boîte se ferme, « dz-projet-canaux » porte la vue relue, la promesse la rend",
          R["fermee"] and R["evts"] == [["dz-projet-canaux", ["cpt_a"]]] and (R["resolu"] or {}).get("canaux") == ["cpt_a"], str(R["evts"]))
    check("5.12 l'hôte de la barre : un glyphe par canal (Deepotus Glyph), titre qui nomme les comptes ; compte inconnu = son identifiant ; aucun canal = hôte vide et masqué",
          "dz-reseau-x" in R["hote"][0] and R["hote"][0].count("data-dz-canal") == 2
          and R["hote"][1] == "Canaux : Compte A @a, cpt_q" and R["hote_vide"][0] == "" and R["hote_vide"][1] is None
          and "display:none" in R["hote_vide"][2], str(R.get("hote")))
    check("A5 Tab piégé dans la boîte des canaux : dernier -> premier, Maj+Tab premier -> dernier, focus hors boîte -> premier ; ni désactivé ni caché choisi",
          R.get("t_bas") == [0, True] and R.get("t_haut") == [3, True] and R.get("t_milieu") == 1 and R.get("t_dehors") == 0
          and R.get("t_desactive") == 2 and R.get("t_cache") == 2,
          str([R.get(k) for k in ("t_bas", "t_haut", "t_milieu", "t_dehors", "t_desactive", "t_cache")]))
    check("5.11 un espace sans compte : le message traduit ; Annuler rend null et ferme",
          AIDE.fr("projets.canaux.aucun_compte") in R["vide"] and R["annule"] is None and R["annule_fermee"], R["vide"][:200])

print("\n[6] la barre des projets, sous node (le bloc #78 du bundle livré)")
DEBUT, FIN = "/* ── Bibliothèque #78 PR B", "/* ── fin Bibliothèque #78 */"
i0, i1 = B.find(DEBUT), B.find(FIN)
j0, j1 = B.find("/* ── Bibliothèque #77 PR B"), B.find("/* ── fin Bibliothèque #77 */")
couche = (B[j0:j1] + "\n" + B[i0:i1]).replace("\r\n", "\n") if min(i0, i1, j0, j1) >= 0 else ""
check("6.0 les aides dzPcB / dzPcEc sont DANS le bloc #78 (le banc de la barre l'exécute)",
      lambda: "function dzPcB(" in couche and "function dzPcEc(" in couche)
HARNAIS_BARRE = r"""
var ouverts=[],ecoutes=[],retraits=[];
globalThis.window=globalThis;window.addEventListener=function(t){ecoutes.push(t)};window.removeEventListener=function(t){retraits.push(t)};
window.dispatchEvent=function(){};globalThis.CustomEvent=function(t){this.type=t};
globalThis.fetch=function(u){var d=u==="/api/library/projets/proj_a"?{id:"proj_a",nom:"Abysses",epingle:false,espace_id:"esp_a",canaux:["cpt_a","cpt_b"],items:[]}:{};
  return Promise.resolve({ok:true,status:200,json:function(){return Promise.resolve(d)}})};
window.__dzDialogue={saisir:function(){return Promise.resolve(null)},confirmer:function(){return Promise.resolve(false)}};
globalThis.__dzToast=function(){};globalThis.__dzSendMenu=function(){};
window.__dzProjetCanaux={ouvrir:function(p){ouverts.push(p.id)},glyphe:function(p){return p?"dz-reseau-"+p:"dz-action-publier"}};
var r={jsx:function(t,p,k){return{t:typeof t==="function"?t.name:t,p:p}},jsxs:function(t,p){return{t:typeof t==="function"?t.name:t,p:p}}};
var effets=[];var x={useState:function(v){return[v,function(){}]},useEffect:function(f){effets.push(f())},useRef:function(v){return{current:v}}};
var X="X";
__COUCHE__
function cherche(n,pred,out){out=out||[];if(n&&typeof n==="object"){if(pred(n))out.push(n);Object.keys(n).forEach(function(k){cherche(n[k],pred,out)})}return out}
var R={};
(async function(){
 var f={id:"proj_a",nom:"Abysses",epingle:false,espace_id:"esp_a",canaux:["cpt_a","cpt_b"],refs:{},n:0};
 var b=DzProjetsBar({f:f,setF:function(){}});
 R.ecoutes=ecoutes.slice();effets.forEach(function(d){if(typeof d==="function")d()});R.retraits=retraits.slice();
 var h=cherche(b,function(n){return n.t==="span"&&n.p&&n.p["data-dz-projet-canaux"]!==undefined});
 R.hote=h.length;R.hote_p=h[0]&&[h[0].p["data-dz-projet-canaux"],h[0].p["data-canaux"],h[0].p["data-espace"]];
 var bt=cherche(b,function(n){return n.t==="button"&&n.p&&n.p.title===dzT("projets.canaux.aide")});R.bouton=bt.length;
 R.bouton_txt=JSON.stringify(bt[0]&&bt[0].p.children);R.classe=bt[0]&&bt[0].p.className;
 if(bt[0])bt[0].p.onClick();R.ouverts=ouverts;
 R.n11=JSON.stringify(b).indexOf("Renommer")>=0;
 var b0=DzProjetsBar({f:null,setF:function(){}});
 R.sans=cherche(b0,function(n){return n.t==="span"&&n.p&&n.p["data-dz-projet-canaux"]!==undefined}).length+
        cherche(b0,function(n){return n.t==="button"&&n.p&&n.p.title===dzT("projets.canaux.aide")}).length;
 var ch=await dzProjCharger("proj_a");R.charge=[ch.espace_id,ch.canaux];
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
R2 = {}
if NODE and couche:
    R2 = node(AIDE.PRELUDE_DZT + "\n" + HARNAIS_BARRE.replace("__COUCHE__", couche))
check("6.1 la barre s'exécute sous node", bool(R2) and "erreur" not in R2, str(R2.get("erreur", ""))[:800])
if R2 and "erreur" not in R2:
    check("6.2 la barre écoute « dz-projets » ET « dz-projet-canaux », et retire les deux au démontage",
          sorted(R2["ecoutes"]) == ["dz-projet-canaux", "dz-projets"]
          and sorted(R2["retraits"]) == ["dz-projet-canaux", "dz-projets"], str(R2["ecoutes"]) + str(R2["retraits"]))
    check("6.3 l'hôte des glyphes, une fois : id du projet, ses canaux, son espace",
          R2["hote"] == 1 and R2["hote_p"] == ["proj_a", "cpt_a,cpt_b", "esp_a"], str(R2.get("hote_p")))
    check("6.4 le bouton « Canaux » : glyphe + libellé traduit, classe dzpc-btn ; il appelle __dzProjetCanaux.ouvrir(f)",
          R2["bouton"] == 1 and "Canaux" in R2["bouton_txt"] and "dz-action-publier" in R2["bouton_txt"]
          and R2["classe"] == "dzpc-btn" and R2["ouverts"] == ["proj_a"], str(R2.get("bouton_txt")))
    check("6.5 les autres boutons du projet sont toujours là", R2["n11"])
    check("6.7 toute la Bibliothèque (aucun projet regardé) : ni hôte ni bouton", R2["sans"] == 0)
    check("6.8 le projet chargé garde son espace et ses canaux", R2["charge"] == ["esp_a", ["cpt_a", "cpt_b"]], str(R2["charge"]))

print("\n[7] textes")
DICO = json.loads(DICO_P.read_text("utf-8")) if DICO_P.is_file() else {}
check("7.1 clés projets.canaux.* à trois segments, FR et EN non vides, mêmes {variables}",
      bool(DICO) and all(re.fullmatch(r"projets\.canaux\.[a-z_]+", k) and v.get("fr", "").strip() and v.get("en", "").strip()
                         and sorted(re.findall(r"\{(\w+)\}", v["fr"])) == sorted(re.findall(r"\{(\w+)\}", v["en"]))
                         for k, v in DICO.items()))
ATTENDUES = {"projets.canaux.bouton": ("Canaux", "Channels"), "projets.canaux.titre": ("Canaux du projet {nom}", "Channels of project {nom}"),
             "projets.canaux.enregistrer": ("Enregistrer", "Save")}
check("7.2 bouton, titre, enregistrer : les textes du brief", all(DICO.get(k, {}).get("fr") == fr and DICO.get(k, {}).get("en") == en
                                                              for k, (fr, en) in ATTENDUES.items()))
check("7.3 aucun_compte, erreur_espace existent", "projets.canaux.aucun_compte" in DICO and "projets.canaux.erreur_espace" in DICO)
emp = set()
for f_ in (SHARED, COUCHE_P):
    if f_.is_file():
        emp |= set(re.findall(r'"(projets\.canaux\.[a-z_]+)"', f_.read_text("utf-8")))
emp |= set(re.findall(r'dzT\(\\?"(projets\.canaux\.[a-z_]+)', B))
check("7.4 toutes les clés employées existent, aucune orpheline", bool(emp) and emp == set(DICO),
      f"sans traduction {sorted(emp - set(DICO))} orphelines {sorted(set(DICO) - emp)}")
check("7.5 l'assemblé dz-i18n-dico.js porte les clés", lambda: all(
    k in (REPO / "frontend" / "shared" / "dz-i18n-dico.js").read_text("utf-8") for k in DICO))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
