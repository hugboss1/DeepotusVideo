# -*- coding: utf-8 -*-
"""Bibliotheque, tache #78 PR B (plan-library T4, 03/10/2026) — l'ECRAN des projets : barre « Projet » (voir un projet
dans tous les onglets, le rendre actif, l'epingler sur le telephone, le renommer, le supprimer, en creer un) et
« Envoyer vers → Projet de la Bibliotheque… » (ranger, retirer, creer et ranger).
DECISIONS DE L'UTILISATEUR (03/10) : un seul projet (epingle sur le telephone = case du projet) ; le projet actif range
TOUT (serveur, PR A #144) — l'ecran dit lequel est actif, meme quand on en regarde un autre.
Ce que le plan faisait faux, et que ce banc garde : un maillon `libproj` en queue (le depot range l'ecran dans la couche
montage) ; un window.prompt pour choisir le projet (retire du bundle le 27/09) ; un onglet « Projets » de plus alors
que le projet doit filtrer TOUS les onglets ; une nouvelle section ancree sur un texte qu'ecrit deja une section
(P9lib2, P9lib4) — ici REPLIEE dans ces sections.
Banc-miroir : il lit le BUNDLE LIVRE et execute sous node la couche qui y est injectee (faux fetch, faux dialogue).
Temoin positif : le bundle de la base (84c6db39) n'a ni la barre ni la cible.
Run (depuis backend/) : & $PY tests/test_library_projets_ecran.py"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
PATCHER = RACINE / "scripts" / "patch_bundle_montage.py"
NODE = shutil.which("node")

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "84c6db39"
sb = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True,
                    cwd=str(RACINE)).stdout.decode("utf-8", "replace")
check("T0 temoin : le bundle de la base n'a ni la barre des projets ni la cible du menu",
      len(sb) > 1_000_000 and "DzProjetsBar" not in sb and "dzProjMenu" not in sb and "/api/library/projets" not in sb)

braw = BUNDLE.read_bytes()
s = braw.decode("utf-8")
DEBUT, FIN = "/* ── Bibliothèque #78 PR B", "/* ── fin Bibliothèque #78 */"

print("[B] le bundle livre")
check("B1 la couche est injectee UNE fois", s.count(DEBUT) == 1 and s.count(FIN) == 1)
check("B2 l'etat du projet regarde est REPLIE dans P9lib2 (meme ancre, meme section)",
      s.count('[dzSF,dzSFs]=x.useState(""),[dzEta,dzEtas]=x.useState([]),[dzMF,dzMFs]=x.useState({tag:"",note:0}),'
              '[dzPF,dzPFs]=x.useState(null),') == 1)
check("B3 le filtre du projet entre DANS Lfs, replie dans P9lib4 : il vaut pour TOUS les onglets (et le repli de demo)",
      s.count('const Lfs=(L)=>{L=(o==="Images"||o==="Favoris")?dzMetaFiltre(L,dzMF):L;L=dzProjFiltre(L,dzPF);') == 1)
check("B4 la barre « Projet » ouvre le contenu de la Bibliotheque, avant les chips de provenance",
      s.count('children:[r.jsx(DzProjetsBar,{f:dzPF,setF:dzPFs}),r.jsx(DzOutilsBiblio,{}),__dzSrcChips(o,T,dzSF,dzSFs)') == 1)   # #81 PR C : la barre Corbeille / Nettoyage suit
check("B5 « Envoyer vers » propose le projet pour TOUT asset (avant le « aucune cible »)",
      s.count('items.push({lbl:"📁 Projet de la Bibliothèque…",fn:function(){dzProjMenu(m)}});'
              'if(!items.length){__dzToast("Aucune cible pour cet asset");return}') == 1)
check("B6 aucun window.prompt ni window.alert dans la couche (le dialogue maison)", "window.prompt" not in s[s.find(DEBUT):s.find(FIN)]
      and "window.alert" not in s[s.find(DEBUT):s.find(FIN)] and "__dzDialogue.saisir" in s[s.find(DEBUT):s.find(FIN)])
check("B7 aucun onglet « Projets » de plus (le projet filtre les onglets existants)", "Projets:[]" not in s and "Projets:" not in
      s[s.find("Favoris:H.filter"):s.find("Favoris:H.filter") + 900])
check("B8 fins de ligne : CRLF homogene", braw.count(b"\r\n") > 15000 and braw.count(b"\n") == braw.count(b"\r\n"))
if NODE:
    t = pathlib.Path(tempfile.mkdtemp()) / "b.mjs"
    t.write_bytes(braw)
    rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("B9 node --check : le bundle PARSE", rc.returncode == 0, rc.stderr[-300:])
pt = PATCHER.read_text("utf-8")
check("B10 deux sections neuves seulement (P9lib11 barre, P9lib12 cible) ; aucun maillon libproj",
      pt.count('("P9lib11') == 1 and pt.count('("P9lib12') == 1 and pt.count('("P9lib13') == 0
      and not (RACINE / "scripts" / "patch_bundle_libproj.py").exists())

print("\n[N] la couche, executee sous node")
i0, i1 = s.find(DEBUT), s.find(FIN)
# la couche #78 s'appuie sur celle de #77 (dzToastSur) : on charge les DEUX blocs, comme le bundle les porte
j0, j1 = s.find("/* ── Bibliothèque #77 PR B"), s.find("/* ── fin Bibliothèque #77 */")
couche = (s[j0:j1] + "\n" + s[i0:i1]).replace("\r\n", "\n") if i0 >= 0 and i1 > i0 and j0 >= 0 and j1 > j0 else ""
HARNAIS = r"""
var appels=[],toasts=[],menus=[],signaux=0,saisie=null;
var BASE={projets:[{id:"proj_a",nom:"Abysses",couleur:null,epingle:false,n:2},{id:"proj_b",nom:"Oracle",couleur:null,epingle:true,n:0}]};
var routes=function(u,o){var m=(o&&o.method)||"GET";
  if(u==="/api/library/projets"&&m==="GET")return BASE;
  if(u.indexOf("/api/library/projets?ref=")===0)return{projets:[BASE.projets[0]]};
  if(u==="/api/library/projets"&&m==="POST")return{id:"proj_n",nom:JSON.parse(o.body).nom,epingle:false};
  if(u==="/api/library/projets/proj_a")return{id:"proj_a",nom:"Abysses",epingle:false,items:[{ref:"gen_a.png",kind:"image"},{ref:"job-1",kind:"render"}]};
  if(/\/items$/.test(u))return m==="POST"?{ajoutes:1}:{retires:1};
  return{}};
globalThis.fetch=function(u,o){appels.push({u:u,m:(o&&o.method)||"GET",b:o&&o.body?JSON.parse(o.body):null});
  var d=routes(u,o);return Promise.resolve({ok:!d.__err,status:d.__err||200,json:function(){return Promise.resolve(d)}})};
globalThis.window=globalThis;window.dispatchEvent=function(e){if(e&&e.type==="dz-projets")signaux++};
globalThis.CustomEvent=function(t){this.type=t};
window.__dzDialogue={saisir:function(m,o){return Promise.resolve(saisie)},confirmer:function(){return Promise.resolve(true)}};
globalThis.__dzToast=function(m){toasts.push(m)};
globalThis.__dzSendMenu=function(items,titre){menus.push({items:items,titre:titre})};
var r={jsx:function(t,p){return{t:t,p:p}},jsxs:function(t,p){return{t:t,p:p}}};
var x={useState:function(v){return[v,function(){}]},useEffect:function(){},useRef:function(v){return{current:v}}};
var K="K";
__COUCHE__
function attendre(){return new Promise(function(ok){setTimeout(ok,10)})}
var R={};
(async function(){
 R.cle=[dzProjCle({name:"a.png"}),dzProjCle({name:"Rendu 1",jobId:"job-1"}),dzProjCle(null)];
 R.kind=[dzProjKind({kind:"image",name:"a.png"}),dzProjKind({kind:"render",jobId:"j"}),dzProjKind({kind:"asset3d",jobId:"j"}),
         dzProjKind({kind:"sprite2d",jobId:"j"}),dzProjKind({kind:"audio",name:"v.mp3",audioFile:"v.mp3"})];
 var L=[{name:"gen_a.png"},{name:"gen_b.png"},{name:"Rendu",jobId:"job-1"},{name:"Rendu 2",jobId:"job-2"}];
 R.filtre=[dzProjFiltre(L,null).length,dzProjFiltre(L,{id:"proj_a",refs:{"gen_a.png":1,"job-1":1}}).map(dzProjCle),dzProjFiltre(null,{id:"x",refs:{}}).length];
 var ch=await dzProjCharger("proj_a");R.charge=[ch.id,ch.nom,Object.keys(ch.refs).sort(),ch.n];R.charge_vide=await dzProjCharger("");
 appels=[];await dzProjMenu({kind:"image",name:"gen_a.png"});await attendre();
 var mn=menus[0];R.menu=[mn&&mn.titre,mn&&mn.items.map(function(i){return i.lbl})];
 appels=[];signaux=0;toasts=[];mn.items[1].fn();await attendre();R.ranger=[appels[0],signaux,toasts[0]||""];
 appels=[];toasts=[];mn.items[0].fn();await attendre();R.retirer=[appels[0],toasts[0]||""];
 saisie="  Nuit bleue ";appels=[];toasts=[];mn.items[2].fn();await attendre();await attendre();
 R.nouveau=[appels.map(function(a){return a.m+" "+a.u+" "+JSON.stringify(a.b)}),toasts[0]||""];
 saisie=null;appels=[];mn.items[2].fn();await attendre();R.annule=appels.length;
 menus=[];await dzProjMenu({kind:"render",name:"Rendu",jobId:"job-9"});await attendre();menus[0].items[1].fn();await attendre();
 R.render=appels.filter(function(a){return a.m==="POST"}).map(function(a){return JSON.stringify(a.b)});
 var b0=DzProjetsBar({f:null,setF:function(){}});R.barre0=JSON.stringify(b0);
 var b1=DzProjetsBar({f:{id:"proj_a",nom:"Abysses",epingle:false,refs:{},n:2},setF:function(){}});R.barre1=JSON.stringify(b1);
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
R = {}
if NODE and couche:
    f = pathlib.Path(tempfile.mkdtemp()) / "h.js"
    f.write_text(HARNAIS.replace("__COUCHE__", couche), "utf-8")
    p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        R = json.loads(p.stdout or "{}")
    except ValueError:
        R = {"erreur": (p.stdout + p.stderr)[-600:]}
check("N0 la couche s'execute sous node sans erreur", bool(couche) and bool(R) and "erreur" not in R, str(R.get("erreur", ""))[:600])
if R and "erreur" not in R:
    check("N1 la cle d'un asset : son job_id s'il en a un, sinon son nom de fichier", R["cle"] == ["a.png", "job-1", ""], str(R["cle"]))
    check("N2 le kind range : celui de l'ecran (image, render, asset3d, sprite2d, audio)",
          R["kind"] == ["image", "render", "asset3d", "sprite2d", "audio"], str(R["kind"]))
    check("N3 le filtre : aucun projet = tout ; un projet = ses seuls assets (fichiers ET rendus) ; liste nulle = []",
          R["filtre"] == [4, ["gen_a.png", "job-1"], 0], str(R["filtre"]))
    check("N4 charger un projet donne ses refs (ensemble) et son nombre ; aucun id = null",
          R["charge"] == ["proj_a", "Abysses", ["gen_a.png", "job-1"], 2] and R["charge_vide"] is None, str(R["charge"]))
    m = R["menu"]
    check("N5 le menu : coche les projets qui CONTIENNENT deja l'asset (retirer), propose les autres et un nouveau projet",
          m[0] == "Ranger « gen_a.png » dans un projet…" and m[1] == ["✓ Abysses — retirer", "📁 Oracle", "＋ Nouveau projet…"], str(m))
    check("N6 ranger : POST /items {ref, kind}, l'ecran est prevenu (signal) et l'utilisateur aussi",
          R["ranger"][0] == {"u": "/api/library/projets/proj_b/items", "m": "POST", "b": {"items": [{"ref": "gen_a.png", "kind": "image"}]}}
          and R["ranger"][1] == 1 and "Oracle" in R["ranger"][2], str(R["ranger"]))
    check("N7 retirer : DELETE /items {refs}", R["retirer"][0] == {"u": "/api/library/projets/proj_a/items", "m": "DELETE",
                                                                    "b": {"refs": ["gen_a.png"]}} and "Retiré" in R["retirer"][1], str(R["retirer"]))
    check("N8 nouveau projet par le DIALOGUE maison : creer puis ranger, dans cet ordre ; annuler ne fait rien",
          R["nouveau"][0] == ['POST /api/library/projets {"nom":"  Nuit bleue "}',
                              'POST /api/library/projets/proj_n/items {"items":[{"ref":"gen_a.png","kind":"image"}]}']
          and R["annule"] == 0, str(R["nouveau"]))
    check("N9 un rendu se range par son job_id, kind render", R["render"] == ['{"items":[{"ref":"job-9","kind":"render"}]}'], str(R["render"]))
    b0, b1 = R["barre0"], R["barre1"]
    check("N10 la barre sans projet regarde : « Toute la Bibliotheque », la liste, « Nouveau projet » ; pas de boutons de projet",
          "Toute la Bibliothèque" in b0 and "Nouveau projet" in b0 and "Épingler" not in b0 and "Supprimer" not in b0, b0[:400])
    check("N11 la barre d'un projet regarde : rendre actif, epingler sur le telephone, renommer, supprimer",
          "Ranger ici automatiquement" in b1 and "Épingler sur le téléphone" in b1 and "Renommer" in b1 and "Supprimer" in b1, b1[:600])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
