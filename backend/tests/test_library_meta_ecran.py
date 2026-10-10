# -*- coding: utf-8 -*-
"""Bibliotheque, tache #77 PR B (plan-library T2, 03/10/2026) — l'ECRAN : favori, note et tags lus et ecrits EN BASE.
DECISIONS DE L'UTILISATEUR (03/10) : favori (oui/non) et note (0..5) sont DEUX notions ; les favoris des rendus aussi en
base ; les listes du navigateur (dz_fav_images / dz_fav_renders) sont reprises UNE fois puis gardees telles quelles.
Ce que le plan faisait faux, et que ce banc garde : il ajoutait un patcher `libmeta` en queue de chaine (le pattern du
depot est desormais une section de la couche montage) ; son etoile de vignette posait la note 5 ET le favori (couplage) ;
il laissait le renommage basculer deux fois le favori — avec un serveur qui EMPORTE le favori au renommage, cette double
bascule l'aurait ETEINT.
Banc-miroir : il lit le BUNDLE LIVRE et execute sous node la couche qui y est injectee (faux fetch, faux localStorage).
Temoin positif : le bundle de la base (6c5b31cc) n'a rien de tout cela et lit les favoris dans localStorage.
Run (depuis backend/) : & $PY tests/test_library_meta_ecran.py"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE  # t141 : dzT (prelude node)
RACINE = _ICI.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
COUCHE = RACINE / "frontend" / "patches" / "montage.js"
PATCHER = RACINE / "scripts" / "patch_bundle_montage.py"
NODE = shutil.which("node")

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "6c5b31cc"
sb = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True,
                    cwd=str(RACINE)).stdout.decode("utf-8", "replace")
check("T0 temoin : le bundle de la base lit les favoris dans localStorage et n'a ni la couche ni ses sections",
      len(sb) > 1_000_000 and sb.count('localStorage.getItem("dz_fav_renders")') == 1 and "DZ_FAV" not in sb
      and "DzMetaEditor" not in sb)

braw = BUNDLE.read_bytes()
s = braw.decode("utf-8")
DEBUT, FIN = "/* ── Bibliothèque #77 PR B", "/* ── fin Bibliothèque #77 */"

print("[B] le bundle livre")
check("B1 la couche est injectee UNE fois (debut et fin de bloc)", s.count(DEBUT) == 1 and s.count(FIN) == 1)
check("B2 les helpers du bundle gardent leurs NOMS (appelants intacts) mais DELEGUENT au cache serveur",
      s.count("function __dzFavHas(id){return dzFavHas(\"r\",id)}") == 1
      and s.count("function __dzFavImgHas(nm){return dzFavHas(\"i\",nm)}") == 1
      and s.count("function __dzFavToggle(id){dzFavToggle(\"r\",id)}") == 1
      and s.count("function __dzFavImgToggle(nm){dzFavToggle(\"i\",nm)}") == 1)
check("B3 plus AUCUNE lecture ni ecriture de favori dans localStorage hors de la reprise unique (dzFavLocaux)",
      s.count('localStorage.setItem("dz_fav_renders"') == 0 and s.count('localStorage.setItem("dz_fav_images"') == 0
      and s.count('"dz_fav_renders"') == 1 and s.count('"dz_fav_images"') == 1
      and s.index('"dz_fav_images"') > s.index(DEBUT), str((s.count('"dz_fav_renders"'), s.count('"dz_fav_images"'))))
check("B4 la liste des images porte tags, note, favori ; le cache est seme par les listes deja chargees (images, jobs)",
      # tache #81 PR C (03/10/2026) : la couleur dominante voyage aussi (teinte, couleur)
      # tache #82 PR B (04/10/2026) : + le brut des tris et de la liste (octets, date, dimensions, licence)
      s.count('srcOrigin:S.source_origin||"",tags:S.tags||[],note:S.note||0,fav:!!S.fav,teinte:S.teinte||"",couleur:S.couleur||"",octets:S.size_kb!=null?S.size_kb*1024:null,mtime:S.mtime||0,larg:S.width||null,haut:S.height||null,licence:S.licence||""}));'
              'dzFavSemer("i",ne&&ne.images,"filename"),dzFavSemer("r",R,"job_id"),dzFavMigrer(),d(W),f(R||[]),') == 1)
check("B5 un etat de filtre dans la Bibliotheque, applique DANS Lfs (donc aussi au repli de demo)",
      s.count('[dzSF,dzSFs]=x.useState(""),[dzEta,dzEtas]=x.useState([]),[dzMF,dzMFs]=x.useState({tag:"",note:0}),') == 1
      and s.count('const Lfs=(L)=>{L=(o==="Images"||o==="Favoris")?dzMetaFiltre(L,dzMF):L;') == 1)
check("B6 la recherche lit AUSSI les tags (Bibliotheque et selecteur)",
      s.count('((((I&&I.name||"")+" "+((I&&I.tags)||[]).join(" "))+"").toLowerCase().includes(z))') == 1
      and s.count('(!q||(im.filename+" "+(im.tags||[]).join(" ")).toLowerCase().indexOf(q)>=0)') == 1
      and s.count('placeholder="rechercher une image ou un tag…"') == 1)
check("B7 la rangee de chips, la vignette et l'editeur de la fiche sont poses",
      s.count('r.jsx(DzMetaChips,{o:o,T:T,f:dzMF,setF:dzMFs}),o==="Audio"&&') == 1
      and s.count('children:C.provider}),dzCarteMeta(C,function(){dzMFs(function(v){return Object.assign({},v)})})') == 1
      and s.count('r.jsx(se,{name:"dz-action-fermer",onClick:()=>y(null)})]}),r.jsx(DzMetaEditor,{m:m,maj:') == 1)
check("B8 le renommage ne bascule PLUS le favori (le serveur l'emporte) : il deplace le cache",
      s.count("dzFavRenomme(m.name,j.new)") == 1 and "__dzFavImgToggle(j.new)" not in s)
check("B9 fins de ligne : le bundle reste en CRLF homogene", braw.count(b"\r\n") > 15000
      and braw.count(b"\n") == braw.count(b"\r\n"), str((braw.count(b"\r\n"), braw.count(b"\n"))))
if NODE:
    t = pathlib.Path(tempfile.mkdtemp()) / "b.mjs"
    t.write_bytes(braw)
    rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("B10 node --check : le bundle est un module qui PARSE", rc.returncode == 0, rc.stderr[-300:])
pt = PATCHER.read_text("utf-8")
check("B11 le patcher porte les sections P9lib (une liste de P1, pas un maillon neuf) et la couche est la source",
      pt.count('("P9lib') == 13   # 11 de #77 + 2 de #78 PR B (P9lib11, P9lib12) and "patch_bundle_libmeta" not in pt and COUCHE.read_text("utf-8").count(DEBUT) == 1
      and not (RACINE / "scripts" / "patch_bundle_libmeta.py").exists())

print("\n[N] la couche, executee sous node")
i0, i1 = s.find(DEBUT), s.find(FIN)
couche = s[i0:i1].replace("\r\n", "\n") if i0 >= 0 and i1 > i0 else ""
HARNAIS = r"""
var appels=[],toasts=[],LS={},repondre=function(u,o){return{ok:!0,status:200,json:function(){return Promise.resolve({})}}};
globalThis.localStorage={getItem:function(k){return k in LS?LS[k]:null},setItem:function(k,v){LS[k]=String(v)},removeItem:function(k){delete LS[k]}};
globalThis.fetch=function(u,o){appels.push({u:u,m:(o&&o.method)||"GET",b:o&&o.body?JSON.parse(o.body):null});return Promise.resolve(repondre(u,o))};
globalThis.__dzToast=function(m){toasts.push(m)};
var r={jsx:function(t,p){return{t:t,p:p}},jsxs:function(t,p){return{t:t,p:p}}};
var x={useState:function(v){return[v,function(){}]},useRef:function(v){return{current:v}}};
var K="K";
__COUCHE__
var R={};function attendre(){return new Promise(function(ok){setTimeout(ok,5)})}
(async function(){
 R.filtre=[dzMetaFiltre([{tags:["a","b"],note:4},{tags:["b"],note:1},{tags:[],note:5}],{tag:"b",note:0}).length,
           dzMetaFiltre([{tags:["a"],note:4},{tags:["b"],note:2},{note:5}],{tag:"",note:3}).length,
           dzMetaFiltre([{},{}],{tag:"",note:0}).length, dzMetaFiltre(null,{tag:"a"}).length];
 R.comptes=dzMetaComptes([{tags:["b","a"],note:3},{tags:["b"],note:5},{tags:["c"],note:2},{}]);
 R.tagsDe=dzTagsDe(" Vitrail , deep sea,,  ");
 dzFavSemer("i",[{filename:"a.png",fav:true},{filename:"b.png",fav:false}],"filename");
 dzFavSemer("r",[{job_id:"j1",fav:true}],"job_id");
 R.semes=[dzFavHas("i","a.png"),dzFavHas("i","b.png"),dzFavHas("r","j1"),dzFavHas("r","zz"),dzFavHas("i","")];
 R.helpers=[typeof __dzFavHas];
 appels=[];var p=dzFavToggle("i","b.png");R.optimiste=dzFavHas("i","b.png");
 DZ_FAV.t["i:b.png"]=0;  // une requete de plus de 10 s : seule la garde EN VOL protege encore
 dzFavSemer("i",[{filename:"b.png",fav:false}],"filename");R.seme_pendant_vol=dzFavHas("i","b.png");
 await p;R.appel_i=appels[0];
 appels=[];await dzFavToggle("r","j1");R.appel_r=appels[0];R.apres_r=dzFavHas("r","j1");
 dzFavSemer("i",[{filename:"b.png",fav:false}],"filename");R.seme_juste_apres=dzFavHas("i","b.png");
 repondre=function(){return{ok:!1,status:500,json:function(){return Promise.resolve({detail:"base verrouillee"})}}};
 toasts=[];await dzFavToggle("i","a.png");R.revert=dzFavHas("i","a.png");R.toast=toasts[0]||"";
 repondre=function(u,o){return{ok:!0,status:200,json:function(){return Promise.resolve(JSON.parse(o.body).images?{images:{repris:1,ignores:["absent.png"]},renders:{repris:1,ignores:[]}}:{})}}};
 LS={"dz_fav_images":JSON.stringify(["m1.png","absent.png"]),"dz_fav_renders":JSON.stringify(["jm"])};
 appels=[];toasts=[];await dzFavMigrer();
 R.migre=[appels.length,appels[0]&&appels[0].u,appels[0]&&appels[0].m,JSON.stringify(appels[0]&&appels[0].b),LS["dz_fav_migre"],
          dzFavHas("i","m1.png"),dzFavHas("i","absent.png"),dzFavHas("r","jm"),LS["dz_fav_images"],toasts[0]||""];
 appels=[];await dzFavMigrer();R.migre_deux=appels.length;
 DZ_FAV.migre=!1;appels=[];await dzFavMigrer();R.migre_drapeau=appels.length;
 dzFavRenomme("m1.png","m2.png");R.renomme=[dzFavHas("i","m1.png"),dzFavHas("i","m2.png")];
 R.carte_audio=dzCarteMeta({kind:"audio",name:"x.mp3",audioFile:"x.mp3"},null);
 var c=dzCarteMeta({kind:"image",name:"m2.png",note:3,tags:["vitrail"]},null);
 R.carte=JSON.stringify(c);
 var c2=dzCarteMeta({kind:"render",name:"r.mp4",jobId:"j9"},null);R.carte_r=JSON.stringify(c2);
 var stop=0,raf=0;repondre=function(){return{ok:!0,status:200,json:function(){return Promise.resolve({})}}};appels=[];
 var cc=dzCarteMeta({kind:"image",name:"z.png"},function(){raf++});cc.p.children[0].p.onClick({stopPropagation:function(){stop++}});
 await attendre();R.clic_carte=[stop,appels.length&&appels[0].u,appels.length&&JSON.stringify(appels[0].b),raf>=1,dzFavHas("i","z.png")];
 R.chips_vide=DzMetaChips({o:"Images",T:{Images:[{tags:[],note:0}]},f:{tag:"",note:0},setF:function(){}});
 R.chips_renders=DzMetaChips({o:"Renders",T:{Renders:[{tags:["a"],note:5}]},f:{tag:"",note:0},setF:function(){}});
 R.chips=JSON.stringify(DzMetaChips({o:"Images",T:{Images:[{tags:["vitrail"],note:4},{tags:["vitrail","mer"],note:1}]},f:{tag:"vitrail",note:0},setF:function(){}}));
 R.editeur_rendu=DzMetaEditor({m:{kind:"render",name:"r.mp4",jobId:"j9"},maj:function(){}});
 R.editeur=JSON.stringify(DzMetaEditor({m:{kind:"image",name:"m2.png",note:2,tags:["vitrail"]},maj:function(){}}));
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
R = {}
if NODE and couche:
    # t141 (08/10) : la couche passe ses textes par dzT -> le prelude (dictionnaire + dzT en francais) AVANT
    js = AIDE.PRELUDE_DZT + "\n" + HARNAIS.replace("__COUCHE__", couche) + "\nfunction __dzFavHas(id){return dzFavHas(\"r\",id)}\n"
    f = pathlib.Path(tempfile.mkdtemp()) / "h.js"
    f.write_text(js, "utf-8")
    p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        R = json.loads(p.stdout or "{}")
    except ValueError:
        R = {"erreur": (p.stdout + p.stderr)[-600:]}
check("N0 la couche s'execute sous node sans erreur", couche and "erreur" not in R and R, str(R.get("erreur", ""))[:600])
if R and "erreur" not in R:
    check("N1 dzMetaFiltre : par tag, par note minimale, aucun filtre = tout, liste nulle = []",
          R["filtre"] == [2, 2, 2, 0], str(R["filtre"]))
    check("N2 dzMetaComptes : tags comptes et tries par nombre puis nom ; « 3+ » compte les notes >= 3",
          R["comptes"] == {"tags": [{"t": "b", "n": 2}, {"t": "a", "n": 1}, {"t": "c", "n": 1}], "note3": 2, "teintes": []}, str(R["comptes"]))   # #81 : + teintes
    check("N3 dzTagsDe : une saisie « a, b » donne des tags nets (la normalisation finale est au serveur)",
          R["tagsDe"] == ["Vitrail", "deep sea"], str(R["tagsDe"]))
    check("N4 le cache est SEME par les listes servies (images par filename, rendus par job_id)",
          R["semes"] == [True, False, True, False, False], str(R["semes"]))
    check("N5 bascule OPTIMISTE, et une liste rechargee PENDANT l'envoi ne l'ecrase pas",
          R["optimiste"] is True and R["seme_pendant_vol"] is True, str((R["optimiste"], R["seme_pendant_vol"])))
    check("N6 image : PATCH /api/library/asset/{f} {fav} ; rendu : PUT /api/jobs/{id}/fav {fav} — jamais la note",
          R["appel_i"] == {"u": "/api/library/asset/b.png", "m": "PATCH", "b": {"fav": True}}
          and R["appel_r"] == {"u": "/api/jobs/j1/fav", "m": "PUT", "b": {"fav": False}} and R["apres_r"] is False,
          f"{R['appel_i']} {R['appel_r']}")
    check("N7 une liste perimee arrivee JUSTE apres l'envoi ne rallume/eteint pas l'etoile (garde de 10 s)",
          R["seme_juste_apres"] is True)
    check("N8 un refus du serveur REMET l'etoile et le dit (toast avec le detail)",
          R["revert"] is True and "base verrouillee" in R["toast"], str((R["revert"], R["toast"])))
    m = R["migre"]
    check("N9 reprise UNE fois : POST /api/library/favoris/import {images, renders}, drapeau pose, cache allume sauf ignores, "
          "listes du navigateur GARDEES, l'utilisateur est prevenu",
          m[0] == 1 and m[1] == "/api/library/favoris/import" and m[2] == "POST"
          and json.loads(m[3]) == {"images": ["m1.png", "absent.png"], "renders": ["jm"]} and m[4] == "1"
          and m[5] is True and m[6] is False and m[7] is True and json.loads(m[8]) == ["m1.png", "absent.png"]
          and "2 favoris" in m[9], str(m))
    check("N10 ... et jamais deux fois : ni dans la meme page, ni apres rechargement (drapeau en localStorage)",
          R["migre_deux"] == 0 and R["migre_drapeau"] == 0, str((R["migre_deux"], R["migre_drapeau"])))
    check("N11 le renommage DEPLACE le favori du cache (aucun appel serveur : il l'emporte deja)",
          R["renomme"] == [False, True], str(R["renomme"]))
    c = R["carte"]
    check("N12 la vignette : l'etoile du FAVORI (★ allume), la note en points (3), les tags ; rien pour un son",
          R["carte_audio"] is None and '"children":"⟦dz-action-favori⟧"' in c and c.count("⟦dz-etat-note⟧") == 3 and "#vitrail" in c
          and "Retirer des favoris" in c, c[:300])
    check("N13 la vignette d'un rendu porte l'etoile (eteinte) et ni note ni tags inventes",
          '"children":"⟦dz-action-favori⟧"' in R["carte_r"] and "dz-etat-note" not in R["carte_r"] and "#" not in R["carte_r"], R["carte_r"][:300])
    check("N14 la rangee de chips : rien si rien a filtrer ou hors Images/Favoris ; sinon tags comptes, filtre actif marque, "
          "« 3+ » compte, et un bouton pour effacer",
          R["chips_vide"] is None and R["chips_renders"] is None and "#vitrail (2)" in R["chips"] and "#mer (1)" in R["chips"]
          and "⟦dz-etat-note⟧ 3+ (1)" in R["chips"] and "Effacer" in R["chips"] and '"aria-pressed":true' in R["chips"], R["chips"][:400])
    check("N16 l'etoile d'une vignette ne laisse PAS le clic ouvrir la fiche (stopPropagation), envoie le favori et rafraichit",
          R["clic_carte"] == [1, "/api/library/asset/z.png", '{"fav":true}', True, True], str(R["clic_carte"]))
    e = R["editeur"]
    check("N15 l'editeur de fiche : seulement pour une IMAGE ; cinq points de note et les tags editables (retirer, ajouter)",
          R["editeur_rendu"] is None and e.count("Note ") >= 5 and "#vitrail" in e and "Ajouter" in e and "Retirer le tag" in e,
          e[:400])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
