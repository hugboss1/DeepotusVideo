# -*- coding: utf-8 -*-
"""Plan mobile T6 (tache #56 du suivi, PR 3/3, 01/10/2026) — la page « Appareils » des Reglages, dans le BUNDLE ECRIT.
Les chaines sont comptees, puis DzAppair est EXECUTE sous node avec un petit moteur de hooks (etats persistants entre
deux rendus, effets, minuteries) et un faux fetch : appairer -> QR affiche -> le telephone reclame -> le QR se ferme ;
revoquer -> dialogue maison qui nomme l'appareil -> POST /revoke seulement si confirme.
Temoin positif : la base (aabc3924) n'a pas DzAppair.
Run (depuis backend/) : & $PY tests/test_appareils_bundle.py"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_RACINE = pathlib.Path(__file__).resolve().parents[2]
_BUNDLE = _RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as AIDE  # noqa: E402  t141 : les libelles passent par dzT (prelude en francais sous node)

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


s = _BUNDLE.read_bytes().decode("utf-8")
r0 = subprocess.run(["git", "show", "aabc3924:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(_RACINE))
s0 = r0.stdout.decode("utf-8") if r0.returncode == 0 else ""
check("T1 temoin : la base n'a pas DzAppair", bool(s0) and "DzAppair" not in s0)


def fonc(nom, src=s):
    i = src.find(f"function {nom}(")
    j = src.find("{", src.find(")", i))
    prof = 0
    for k in range(j, len(src)):
        prof += {"{": 1, "}": -1}.get(src[k], 0)
        if prof == 0:
            return src[i:k + 1]
    return ""


print("\n[A] le bundle ecrit")
check("A1 une page, une entree de barre, une cle dans la liste blanche, un branchement",
      # t141 (08/10/2026) : le libelle de la barre passe par dzT ; la cle est epinglee ET son francais reste « Appareils »
      s.count("function DzAppair(") == 1 and s.count('{k:"appareils",l:dzT("reglages.onglet.appareils")}') == 1
      and AIDE.fr("reglages.onglet.appareils") == "Appareils"
      and s.count('const ym=["diag","coffre","appareils","keys",') == 1 and s.count('s==="appareils"&&r.jsx(DzAppair,{})') == 1)
f = fonc("DzAppair")
check("A2 trois routes : liste, QR, rotation ; revoquer par /devices/<id>/revoke", all(u in f for u in
      ("'/api/devices'", "'/api/pair/start'", "'/api/devices/rotation'", "'/api/devices/'+encodeURIComponent(d.id)+'/revoke'")))
check("A3 le QR n'est PAS redessine : il vient du PNG base64 de la route", "'data:image/png;base64,'+q.qr_png_b64" in f
      and "canvas" not in f.lower())
check("A4 aucun window.confirm/alert/prompt ; chaque bouton K a un title ; liens externes en noreferrer avec title",
      not any(w in f for w in ("window.confirm", "window.alert", "window.prompt", "confirm(\"")) and f.count("r.jsx(K,{") == f.count("title:")
      - f.count("r.jsx('a',{") and "rel:'noreferrer'" in f, str((f.count("r.jsx(K,{"), f.count("title:"))))
import re  # noqa: E402
check("A5 aucun jeton LU ni affiche (la route ne le rend qu'au telephone) : ni .jeton, ni ['jeton'], ni jeton_sha256",
      not re.search(r"\.jeton|\[['\"]jeton['\"]\]|jeton_sha256", f), str(re.findall(r".{20}jeton.{20}", f)[:3]))

node = shutil.which("node")
check("N0 node est present", bool(node))
if node:
    # t141 (08/10/2026) : DzAppair appelle dzT("cle") -> le prelude pose le dictionnaire et dzT (francais) ; le module
    # (.mjs) a donc une variable `window` locale : on y greffe __dzDialogue au lieu de remplacer globalThis.window.
    js = AIDE.PRELUDE_DZT + r"""
// --- moteur de hooks minimal : etats persistants par position, effets apres rendu selon les dependances
var etats=[],deps=[],nettoie=[],i=0,minut=[],toasts=[],appels=[],dlg={rep:true,vu:[]},rendu=null;
var x={useState:function(v){var k=i++;if(!(k in etats))etats[k]=v;return[etats[k],function(n){etats[k]=typeof n==="function"?n(etats[k]):n;planif=true}]},
       useEffect:function(f,d){var k=i++;var change=!(k in deps)||!d||d.some(function(v,j){return v!==deps[k][j]});
         if(change){deps[k]=d;effetsAFaire.push([k,f])}}};
var effetsAFaire=[],planif=false;
function el(t,p){return{t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"F"};
function K(){}function te(){}function jt(){}
globalThis.window=Object.assign(window,{__dzDialogue:{confirmer:function(m,o){dlg.vu.push([m,o]);return Promise.resolve(dlg.rep)}}});
globalThis.__dzToast=function(m){toasts.push(m)};
globalThis.setInterval=function(f,ms){minut.push(f);return minut.length};globalThis.clearInterval=function(id){minut[id-1]=null};
var serveur={appareils:[],max:5,ecoute:"127.0.0.1"};
function rep(st,j){return Promise.resolve({status:st,ok:st>=200&&st<300,json:function(){return Promise.resolve(j)}})}
globalThis.fetch=function(u,o){appels.push([u,(o&&o.method)||"GET"]);
  if(u==="/api/devices")return rep(200,JSON.parse(JSON.stringify(serveur)));
  if(u==="/api/devices/rotation")return rep(200,{consoles:[{cle:"FAL_KEY",nom:"fal.ai",url:"https://fal.ai/dashboard/keys"}]});
  if(u==="/api/pair/start")return rep(200,{url:"dz1://pair?h=10.0.0.2&p=8765&s=ab",qr_png_b64:"QUJD",expire_dans_s:300});
  var m=u.match(/^\/api\/devices\/(.+)\/revoke$/);if(m){var d=serveur.appareils.find(function(z){return z.id===decodeURIComponent(m[1])});
    if(d&&!d.revoque){d.revoque="2026-10-01T20:00:00";return rep(200,{revoque:d.id})}return rep(404,{detail:"inconnu"})}
  return rep(404,{})};
""" + f + r"""
async function tour(){for(var n=0;n<6;n++){planif=false;i=0;rendu=DzAppair();var e=effetsAFaire;effetsAFaire=[];
  e.forEach(function(p){if(nettoie[p[0]])nettoie[p[0]]();nettoie[p[0]]=p[1]()});await new Promise(function(rr){setTimeout(rr,5)});
  if(!planif&&!effetsAFaire.length)break}}
function tout(e,acc){acc=acc||[];if(!e||typeof e!=="object")return acc;if(Array.isArray(e)){e.forEach(function(k){tout(k,acc)});return acc}acc.push(e);var c=e.p&&e.p.children;(Array.isArray(c)?c:[c]).forEach(function(k){tout(k,acc)});return acc}
function bouton(txt){return tout(rendu).find(function(e){return e.t===K&&String(e.p.children)===txt})}
function texte(){return tout(rendu).map(function(e){return typeof e.p.children==="string"?e.p.children:""}).join(" | ")}
(async function(){var out={};try{
 await tour();
 out.vide={t:texte(),btn:!!bouton("Appairer un appareil"),title:(bouton("Appairer un appareil")||{p:{}}).p.title,
   liens:tout(rendu).filter(function(e){return e.t==="a"}).map(function(e){return [e.p.href,e.p.rel,!!e.p.title]})};
 bouton("Appairer un appareil").p.onClick();await tour();
 var img=tout(rendu).find(function(e){return e.t==="img"});
 out.qr={src:img&&img.p.src,url:texte().indexOf("dz1://pair?h=10.0.0.2")>=0,fin:(tout(rendu).find(function(e){return e.p.className==="dza-fin"})||{p:{}}).p.children,
   appairerCache:!bouton("Appairer un appareil"),minuteries:minut.filter(Boolean).length};
 // le telephone reclame pendant que le QR est affiche ; la minuterie relit la liste toutes les 3 s
 serveur.appareils.push({id:"d1",nom:"iPhone de Oli",cree:"2026-10-01T19:00:00",revoque:null});
 for(var k=0;k<3;k++){minut.filter(Boolean).forEach(function(f){f()});await tour()}
 out.reclame={qrFerme:!tout(rendu).some(function(e){return e.t==="img"}),toast:toasts.slice(-1)[0],
   ligne:texte().indexOf("iPhone de Oli")>=0,compte:texte().indexOf("1 / 5 appareils")>=0,minuteries:minut.filter(Boolean).length};
 // revoquer : refuse au dialogue -> aucun appel
 dlg.rep=false;var n0=appels.length;await bouton("Révoquer").p.onClick();await tour();
 out.refus={appels:appels.slice(n0).filter(function(a){return a[1]==="POST"}).length,dialogue:dlg.vu.slice(-1)[0]};
 dlg.rep=true;await bouton("Révoquer").p.onClick();await tour();
 out.revoque={post:appels.filter(function(a){return a[1]==="POST"&&/revoke/.test(a[0])}),toast:toasts.slice(-1)[0],
   etiquette:texte().indexOf("révoqué")>=0,plusDeBouton:!bouton("Révoquer")};
 // cinq actifs : le bouton d'appairage est grise et le dit
 for(var j=2;j<=6;j++)serveur.appareils.push({id:"d"+j,nom:"a"+j,cree:"2026-10-01",revoque:null});
 etats=[];deps=[];nettoie=[];minut=[];await tour();
 var b5=bouton("Appairer un appareil");out.plein={disabled:b5&&b5.p.disabled,title:b5&&b5.p.title};
 // reseau local ouvert : l'etiquette change et le mode d'emploi HOST disparait
 serveur.ecoute="0.0.0.0";etats=[];deps=[];nettoie=[];await tour();out.lan=texte();
 }catch(er){out.erreur=String(er)}finally{console.log(JSON.stringify(out))}})();
"""
    fjs = pathlib.Path(tempfile.mkdtemp(prefix="dzappb_"), "a.mjs"); fjs.write_text(js, encoding="utf-8")
    p = subprocess.run([node, str(fjs)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    v = o.get("vide") or {}
    check("N1 premier rendu : boucle locale DITE avec le mode d'emploi HOST=0.0.0.0, 0/5, « Aucun appareil », bouton avec title",
          "ce PC seulement" in v.get("t", "") and "HOST=0.0.0.0" in v.get("t", "") and "0 / 5 appareils" in v.get("t", "")
          and "Aucun appareil appairé." in v.get("t", "") and v.get("btn") and "5 minutes" in str(v.get("title")), str(v)[:300])
    check("N2 liens de rotation : https, noreferrer, title", v.get("liens") == [["https://fal.ai/dashboard/keys", "noreferrer", True]], str(v.get("liens")))
    q = o.get("qr") or {}
    check("N3 appairer : le QR (PNG base64 de la route), l'URL, le compte a rebours 5:00, le bouton masque, UNE minuterie",
          q.get("src") == "data:image/png;base64,QUJD" and q.get("url") and "5:00" in str(q.get("fin")) and q.get("appairerCache")
          and q.get("minuteries") == 1, str(q))
    rc = o.get("reclame") or {}
    check("N4 le telephone reclame : le QR se FERME seul, toast nomme l'appareil, la ligne apparait, 1/5, minuterie arretee",
          rc.get("qrFerme") and "iPhone de Oli" in str(rc.get("toast")) and rc.get("ligne") and rc.get("compte") and rc.get("minuteries") == 0, str(rc))
    rf = o.get("refus") or {}
    check("N5 revoquer, refuse au dialogue : AUCUN appel ; le dialogue nomme l'appareil et rappelle de regenerer les cles",
          rf.get("appels") == 0 and "« iPhone de Oli »" in str(rf.get("dialogue")) and "régénérez" in str(rf.get("dialogue")), str(rf)[:300])
    rv = o.get("revoque") or {}
    check("N6 confirme : un seul POST /api/devices/d1/revoke, toast, etiquette « revoque », plus de bouton",
          rv.get("post") == [["/api/devices/d1/revoke", "POST"]] and "révoqué" in str(rv.get("toast")) and rv.get("etiquette") and rv.get("plusDeBouton"), str(rv))
    pl = o.get("plein") or {}
    check("N7 cinq appareils actifs : le bouton d'appairage est grise et dit pourquoi", pl.get("disabled") is True and "révoquez" in str(pl.get("title")), str(pl))
    check("N8 reseau local ouvert : etiquette « reseau local ouvert », plus de mode d'emploi HOST", "réseau local ouvert" in str(o.get("lan"))
          and "HOST=0.0.0.0" not in str(o.get("lan")), str(o.get("lan"))[:200])

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
