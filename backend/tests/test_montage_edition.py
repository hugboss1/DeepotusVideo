# -*- coding: utf-8 -*-
"""L1 — LES MODES D'EDITION (D-2), LES TRIMS ROLL/SLIP/SLIDE (D-3) ET LES MARQUEURS (D-5) : le coeur JS est EXECUTE sous node
(frontend/patches/montage.js, celui que le patcher injecte), jamais lu.
Shim par FICHIER, jamais `node -e`.
Run : & $PY tests\test_montage_edition.py   (depuis backend/)"""
import json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_PATH = os.path.join(ROOT, "frontend", "patches", "montage.js")
NODE = shutil.which("node")
TMP = tempfile.mkdtemp(prefix="dzl1_")
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def temoin(e): return f"{type(e).__name__}: {e}"
def sh(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")

PROBE = r"""
var T=window.DzTracks,out={};
var C=[{tr:"v1",id:"p1",start:0,end:4,src:{a:1}},{tr:"v1",id:"p2",start:4,end:8,src:{a:1}},
       {tr:"v2",id:"o1",start:1,end:3,src:{a:1}},{tr:"a1",id:"n1",start:0,end:8,src:{a:1}}];
var TS=[{id:"v3",kind:"video"},{id:"v2",kind:"video"},{id:"v1",kind:"video"},{id:"a1",kind:"audio"}];
var N={tr:"v1",id:"x",start:2,end:5,src:{b:1},srcIn:0};
function sv(res,tr){return (res.clips||[]).filter(function(c){return c.tr===tr})
  .sort(function(a,b){return a.start-b.start}).map(function(c){return [c.id,c.start,c.end,c.srcIn==null?null:c.srcIn]})}
out.modes=T.MODES.map(function(m){return m[0]});
/* écraser : ce qui est sous [2,5[ est rogné ou fendu */
var e=T.insere(C,N,"ecraser",{tracks:TS});
out.ecraser=sv(e,"v1"); out.ecraser_autres=sv(e,"a1").length;
/* insérer : tout ce qui commence à ≥ 2 sur v1 recule de 3, p1 est fendu */
var i=T.insere(C,N,"inserer",{tracks:TS});
out.inserer=sv(i,"v1");
/* fin : après le dernier clip de la piste, la tête ignorée */
var f=T.insere(C,N,"fin",{tracks:TS});
out.fin=sv(f,"v1");
/* dessus : sur la piste vidéo LIBRE la plus proche au-dessus de v1 → v3 (v2 est occupée en [1,3[) */
var d=T.insere(C,N,"dessus",{tracks:TS});
out.dessus_piste=d.track; out.dessus=sv(d,"v3");
var d2=T.insere(C,Object.assign({},N,{start:5,end:7}),"dessus",{tracks:TS});
out.dessus_v2_libre=d2.track;
/* ripple_ecraser : remplace le clip sous la tête (p1, [0,4[) par x (3 s),
   x prend la place DE p1 depuis SON DEBUT (pas depuis la tête) ; la suite avance */
var r=T.insere(C,N,"ripple_ecraser",{tracks:TS,head:2});
out.ripple=sv(r,"v1");
/* remplir : la plage I/O fixe les bornes et la vitesse (source 6 s dans 3 s → ×2) */
var m=T.insere(C,Object.assign({},N,{srcDur:6}),"remplir",{tracks:TS,range:{in:2,out:5}});
out.remplir=sv(m,"v1"); out.remplir_speed=(m.clips.filter(function(c){return c.id==="x"})[0]||{}).speed;
out.remplir_sans_plage=T.insere(C,N,"remplir",{tracks:TS}).mode;
/* jumeau : le clip A1 posé en même temps suit le même mode (inserer ripple aussi a1) */
var j=T.insere(C,N,"inserer",{tracks:TS,twin:{tr:"a1",id:"xa",start:2,end:5,src:{b:1}}});
out.jumeau=sv(j,"a1");
/* mous */
out.mou=[T.insere(null,N,"ecraser",{}).clips.length,T.insere(C,null,"ecraser",{}).clips.length,
         T.insere(C,N,"zzz",{}).mode,T.insere(C,N,"ecraser",{locked:{v1:1}}).refus];
out.pur=C.length===4&&C[0].end===4;
/* ── revue du 21/09/2026 : verrous, jumeau synchrone, ids, jetons ───────── */
var FULL=C.concat([{tr:"v3",id:"t1",start:0,end:8,src:{a:1}}]);
var TW={tr:"a1",id:"xa",start:2,end:5,src:{b:1}};
/* C1 : le repli de « dessus » repasse par la garde de verrou */
var rv=T.insere(FULL,N,"dessus",{tracks:TS,locked:{v1:1}});
out.dessus_repli_verrou=[rv.refus,rv.track,sv(rv,"v1")];
/* C2 : piste jumelle verrouillée → la vidéo est posée, le son non */
var jv=T.insere(C,N,"ecraser",{tracks:TS,twin:TW,locked:{a1:1}});
out.jumeau_verrou=[jv.refus,sv(jv,"a1"),sv(jv,"v1").length,jv.note!==""];
/* C3 : un clip AUDIO en « dessus » ne monte pas sur une piste vidéo */
var da=T.insere(C,{tr:"a1",id:"xs",start:2,end:5,src:{b:1}},"dessus",{tracks:TS});
out.dessus_audio=[da.track,da.refus,da.mode];
/* I1 : jumeau synchrone en ripple (tête 2, clip [6,9[) */
var jr=T.insere(C,Object.assign({},N,{start:6,end:9}),"ripple_ecraser",{tracks:TS,head:2,twin:TW});
out.jumeau_ripple=[sv(jr,"v1").filter(function(q){return q[0]==="x"})[0],
                   sv(jr,"a1").filter(function(q){return q[0]==="xa"})[0]];
/* I2 : jumeau en « fin » aux bornes RÉELLES du clip vidéo posé (a1 finit à 20) */
var CF=C.concat([{tr:"a1",id:"n2",start:12,end:20,src:{a:1}}]);
var jf=T.insere(CF,N,"fin",{tracks:TS,twin:TW});
out.jumeau_fin=[sv(jf,"v1").filter(function(q){return q[0]==="x"})[0],
                sv(jf,"a1").filter(function(q){return q[0]==="xa"})[0]];
/* I3 : jumeau en « remplir » reprend la vitesse du clip vidéo posé */
var jm=T.insere(C,Object.assign({},N,{srcDur:6}),"remplir",{tracks:TS,range:{in:2,out:5},twin:TW});
out.jumeau_remplir=[(jm.clips.filter(function(c){return c.id==="xa"})[0]||{}).speed,
                    sv(jm,"a1").filter(function(q){return q[0]==="xa"})[0]];
/* I4 : le jumeau survit au repli « dessus » */
var jd=T.insere(FULL,N,"dessus",{tracks:TS,twin:TW});
out.jumeau_repli=[jd.refus,sv(jd,"a1").filter(function(q){return q[0]==="xa"})[0]];
/* I6 : identifiant déjà pris sur le montage */
var ic=T.insere(C,Object.assign({},N,{id:"p2"}),"ecraser",{tracks:TS});
out.id_collision=[sv(ic,"v1").map(function(q){return q[0]}),ic.id];
/* longueur nulle : repli sur la durée vidéo par défaut */
out.len0=sv(T.insere(C,Object.assign({},N,{start:2,end:2}),"ecraser",{tracks:TS}),"v1")
  .filter(function(q){return q[0]==="x"})[0];
/* fente d'un clip à vitesse : la fenêtre de source avance de (b−s)×speed */
var CV=[{tr:"v1",id:"p1",start:0,end:4,src:{a:1},srcIn:10,speed:2}];
out.fend_vitesse=sv(T.insere(CV,N,"inserer",{tracks:TS}),"v1");
/* ripple, tête dans un TROU : aucun clip dessous → repli « ecraser » */
var CH=[{tr:"v1",id:"p1",start:0,end:1,src:{a:1}},{tr:"v1",id:"p2",start:6,end:9,src:{a:1}}];
var rh=T.insere(CH,Object.assign({},N,{start:3,end:6}),"ripple_ecraser",{tracks:TS,head:3});
out.ripple_trou=[rh.mode,sv(rh,"v1")];
/* doctrine `dzmRippleCut` : pas de source, pas de fenêtre de source */
var TT=[{tr:"v1",id:"tt",start:0,end:10,text:"t"}];
out.titre_carve=T.carve(TT,"v1",2,5).map(function(c){return [c.id,c.start,c.end,("srcIn" in c)]});
var tp=T.insere([],{tr:"v1",id:"tx",start:0,end:3,text:"t"},"ecraser",{tracks:TS});
out.titre_pose=("srcIn" in tp.clips[0]);
/* M1 : la vitesse écrêtée est DITE */
var ec=T.insere(C,Object.assign({},N,{srcDur:100}),"remplir",{tracks:TS,range:{in:2,out:5}});
out.ecrete=[(ec.clips.filter(function(c){return c.id==="x"})[0]||{}).speed,ec.note];
/* I7 : tous les refus rencontrés sont des JETONS */
out.refus_lus=[e.refus,i.refus,f.refus,d.refus,r.refus,m.refus,j.refus,rv.refus,jv.refus,
               da.refus,jd.refus,T.insere(C,N,"ecraser",{locked:{v1:1}}).refus,
               T.insere(null,N,"ecraser",{}).refus,T.insere(C,null,"ecraser",{}).refus]
  .filter(function(x){return x!==""});
out.refus_table=T.REFUS?T.REFUS.slice():null;
/* M3 : MODES exporté GELÉ (tableau ET paires) */
var mp="";try{T.MODES.push(["z","z"])}catch(err){mp=err.name}
var mw="";try{T.MODES[0][0]="zz"}catch(err){mw=err.name}
out.modes_gel=[T.MODES.length,mp,T.MODES[0][0],mw];
/* ── D-3 : roll, slip, slide ── (cles suffixees 3 : `mou` et `pur` sont
   DEJA pris par le bloc D-2 ci-dessus, une collision les aurait ecrases) */
var K3=[{tr:"v1",id:"p1",start:0,end:4,srcIn:0,src:{a:1}},
        {tr:"v1",id:"p2",start:4,end:8,srcIn:2,src:{a:1}},
        {tr:"v1",id:"p3",start:8,end:10,srcIn:0,src:{a:1}}];
function tri3(cs){return cs.filter(function(c){return c.tr==="v1"})
  .sort(function(a,b){return a.start-b.start})
  .map(function(c){return [c.id,c.start,c.end,c.srcIn]})}
out.slip=tri3(T.slip(K3,"p2",1,{srcDur:10}));
out.slip_borne_bas=tri3(T.slip(K3,"p2",5,{srcDur:10}));
out.slip_borne_haut=tri3(T.slip(K3,"p2",-9,{srcDur:10}));
out.slip_vitesse=tri3(T.slip(K3.map(function(c){
  return c.id==="p2"?Object.assign({},c,{speed:2}):c}),"p2",1,{srcDur:20}));
/* doctrine : un titre (ni srcIn ni src) ne gagne pas de fenetre de source */
out.slip_titre=(function(){var TT=[{tr:"v1",id:"tt",start:0,end:4,text:"t"}];
  return ("srcIn" in T.slip(TT,"tt",1,{srcDur:10})[0])})();
/* I1 (revue du 21/09/2026) : reculer p2 recule le srcIn de p3, et p3 part
   de srcIn 0 -- sur K3 NU, tout recul est donc borne a zero. Les lignes qui
   veulent voir un recul travaillent sur des variantes ou p3 porte de la
   source devant lui : K3N (p3 srcIn 2) et K3D (p3 srcIn 9). */
var K3N=K3.map(function(c){return c.id==="p3"?Object.assign({},c,{srcIn:2}):c});
var K3D=K3.map(function(c){return c.id==="p3"?Object.assign({},c,{srcIn:9}):c});
var K3G=K3.map(function(c){return c.id==="p2"?Object.assign({},c,{srcIn:9}):c});
var K3V=K3.map(function(c){return c.id==="p3"?Object.assign({},c,{srcIn:1,speed:2}):c});
out.slide=tri3(T.slide(K3,"p2",1));
out.slide_neg=tri3(T.slide(K3N,"p2",-1));
out.slide_borne=tri3(T.slide(K3,"p2",5));
out.slide_borne_gauche=tri3(T.slide(K3D,"p2",-9));
out.slide_borne_source_droite=tri3(T.slide(K3,"p2",-9));
out.slide_sans_voisin=tri3(T.slide(K3,"p3",1));
out.slide_sans_gauche=(function(){
  var G=[{tr:"v1",id:"c",start:2,end:6,srcIn:0,src:{a:1}},
         {tr:"v1",id:"d",start:6,end:12,srcIn:5,src:{a:1}}];
  return tri3(T.slide(G,"c",-5))})();
out.slide_vitesse=tri3(T.slide(K3V,"p2",1));
out.roll=tri3(T.roll(K3,"p1","p2",-1));
out.roll_avant=tri3(T.roll(K3,"p1","p2",1));
out.roll_borne=tri3(T.roll(K3G,"p1","p2",-9));
out.roll_borne_source=tri3(T.roll(K3,"p1","p2",-9));
out.roll_borne_haut=tri3(T.roll(K3,"p1","p2",9));
out.roll_non_contigu=tri3(T.roll(K3,"p1","p3",1));
out.roll_vitesse=tri3(T.roll(K3V,"p2","p3",1));
/* I2 : la garde de jonction a DEUX moities. Le clip audio n'est pas filtre
   par `tri3`, donc la sonde rend la liste ENTIERE avec sa piste. */
out.roll_pistes_diff=(function(){
  var X=[{tr:"v1",id:"a",start:0,end:4,srcIn:0,src:{a:1}},
         {tr:"a1",id:"b",start:4,end:8,srcIn:0,src:{a:1}}];
  return T.roll(X,"a","b",1)
    .map(function(c){return [c.id,c.tr,c.start,c.end,c.srcIn]})})();
/* I1 : la borne de tete de source se compte EN SOURCE, donc divisee par la
   vitesse. p3 va a x2 avec srcIn 1 : il ne reste qu'une DEMI-seconde de
   timeline devant sa tete, pas une seconde. */
out.slide_tete_source_vitesse=tri3(T.slide(K3V,"p2",-9));
out.roll_tete_source_vitesse=tri3(T.roll(K3V,"p2","p3",-9));
out.slip_borne_haut_vitesse=tri3(T.slip(K3.map(function(c){
  return c.id==="p2"?Object.assign({},c,{speed:2}):c}),"p2",-100,{srcDur:20}));
/* dzmVoisins : le contact se mesure a 0,1 s pres, sur la MEME piste */
out.voisins=(function(){var v=T.voisins(K3,K3[1]);
  return [v.g?v.g.id:null,v.d?v.d.id:null]})();
out.voisins_autre_piste=(function(){
  var X=[{tr:"v1",id:"a",start:0,end:4},{tr:"v2",id:"b",start:4,end:8}];
  var v=T.voisins(X,X[0]);return [v.g?v.g.id:null,v.d?v.d.id:null]})();
/* M2 : 4 - 3,9 vaut 0,10000000000000009 en flottant -- un contact d'un
   dixieme EXACT tombait dehors avec `<= .1` nu. */
out.voisins_dixieme_exact=(function(){
  var X=[{tr:"v1",id:"a",start:0,end:3.9},{tr:"v1",id:"b",start:4,end:8}];
  var v=T.voisins(X,X[1]);return v.g?v.g.id:null})();
out.mou3=[T.slip(null,"p2",1,{}).length,T.slide(K3,"zz",1).length,
          T.roll(K3,"p1","zz",1).length,tri3(T.roll(K3,"p1","p2",NaN))[0][2]];
out.pur3=K3[1].srcIn===2&&K3[0].end===4&&K3[2].start===8;
/* ── D-5 : MARQUEURS ET INDEX ───────────────────────────────────────────── */
var M=[];
M=T.markerAdd(M,2.004,{title:"intro"}); M=T.markerAdd(M,7,{color:"rouge",title:"b"}); M=T.markerAdd(M,4,{});
out.mk_liste=M.map(function(m){return [m.t,m.color,m.title]});
out.mk_ids_uniques=new Set(M.map(function(m){return m.id})).size===3;
out.mk_toggle=T.markerAdd(M,2.1,{}).length;             /* <= 0,15 s : retire, pas double */
out.mk_force=T.markerAdd(M,2.1,{force:!0}).length;      /* force : AJOUTE */
out.mk_remove=T.markerRemove(M,M[1].id).length;
out.mk_remove_inconnu=T.markerRemove(M,"zz").length;
out.mk_next=[T.markerNext(M,2,1),T.markerNext(M,2,-1),T.markerNext(M,9,1),T.markerNext(M,0,-1)];
out.mk_next_vrai=[T.markerNext(M,0,1),T.markerNext(M,9,-1),T.markerNext(M,4,1),T.markerNext(M,4,-1)];
out.mk_from=T.markersFrom([{t:"3",color:"zz",title:5},{t:-1},"x",{t:1.5,color:"bleu",title:"ok",note:"n"}]).map(function(m){return [m.t,m.color,m.title,m.note]});
out.mk_from_ids=(function(){var l=T.markersFrom([{t:3},{t:1},{t:2}]);
  return [l.map(function(m){return m.id}),new Set(l.map(function(m){return m.id})).size]})();
out.mk_colors=T.MARKER_COLORS.map(function(c){return c[0]});
out.mk_pur=M.length===3;
/* t negatif / NaN : ignores, la liste ne bouge pas (et la cle EXISTE) */
out.mk_mous=[T.markerAdd(M,-1,{}).length,T.markerAdd(M,NaN,{}).length,
             T.markerAdd(null,1,{}).length,T.markersFrom("x").length,
             T.markerRemove(null,"m1").length];
/* markersFrom tronque a 200, comme le backend */
out.mk_from_plafond=T.markersFrom((function(){var a=[],i;
  for(i=0;i<250;i++)a.push({t:i});return a})()).length;
/* markerUpdate : couleur assainie, titre/note en chaine, id inconnu inchange */
out.mk_update=(function(){var l=T.markerUpdate(M,M[0].id,{color:"zz",title:7,note:null});
  return [l[0].color,l[0].title,l[0].note,l.length]})();
out.mk_update_couleur=T.markerUpdate(M,M[0].id,{color:"cyan"})[0].color;
out.mk_update_partiel=(function(){var l=T.markerUpdate(M,M[0].id,{color:"vert"});
  return [l[0].color,l[0].title]})();
out.mk_update_inconnu=T.markerUpdate(M,"zz",{color:"vert"}).map(function(m){return [m.t,m.color]});
out.mk_update_pur=M[0].color==="or"&&M[0].title==="intro";
/* MARKER_COLORS gelee comme MODES : six paires, ecriture refusee en strict */
out.mk_gel=(function(){var a=[T.MARKER_COLORS.length];
  try{T.MARKER_COLORS.push(["x","#000"]);a.push("no")}catch(e){a.push(e.constructor.name)}
  a.push(T.MARKER_COLORS[0][0]);
  try{T.MARKER_COLORS[0][0]="x";a.push("no")}catch(e){a.push(e.constructor.name)}
  return a})();
/* les deux composants EXISTENT et ne lisent PAS svmTcFF au chargement */
out.mk_composants=[typeof T.Markers,typeof T.MarkerIndex];
/* I-1 : la BASCULE retire le PLUS PROCHE. A a 1,00 et B a 1,10 encadrent une
   tete a 1,09 : les deux sont dans la tolerance, c est B qui doit tomber. */
out.mk_toggle_le_plus_proche=(function(){
  var L=[{id:"a",t:1,color:"or",title:"A",note:""},
         {id:"b",t:1.1,color:"or",title:"B",note:""}];
  return T.markerAdd(L,1.09,{}).map(function(m){return m.title})})();
out.mk_toggle_le_plus_proche_bas=(function(){
  var L=[{id:"a",t:1,color:"or",title:"A",note:""},
         {id:"b",t:1.1,color:"or",title:"B",note:""}];
  return T.markerAdd(L,1.01,{}).map(function(m){return m.title})})();
/* I-2 : l invariant d espacement est tenu par la RESTAURATION aussi. Sans
   lui, 1,12 apres 1,00 etait injoignable par markerNext. Le doublon exact
   tombe par la meme regle (distance nulle). */
out.mk_from_espacement=T.markersFrom([{t:1},{t:1.12},{t:5}])
  .map(function(m){return [m.id,m.t]});
out.mk_from_doublon=T.markersFrom([{t:2},{t:2}]).length;
/* R-1 : EXACTEMENT UN EPS est TROP PROCHE. Un filtre strict laissait
   passer le couple (0 ; 0,150), que markerNext ne peut atteindre ni en
   avant (il exige t > v+EPS) ni en arriere (t < v-EPS). Le conjoint
   positif : un cheveu de plus (0,151) passe, lui. */
out.mk_from_eps_exact=[T.markersFrom([{t:0},{t:.15}]).map(function(m){return m.t}),
                       T.markersFrom([{t:0},{t:.151}]).map(function(m){return m.t})];
out.mk_eps_injoignable=[T.markerNext([{id:"a",t:0},{id:"b",t:.15}],0,1),
                        T.markerNext([{id:"a",t:0},{id:"b",t:.15}],.15,-1)];
out.mk_from_espacement_trie=T.markersFrom([{t:5},{t:1.12},{t:1}])
  .map(function(m){return m.t});
/* t:"" -- `Number("")` vaut ZERO en JS et `float("")` LEVE en Python :
   le client acceptait a 0 s ce que le serveur jetait. Aligne. */
out.mk_t_vide=[T.markersFrom([{t:""},{t:"  "},{t:null},{t:3}])
                 .map(function(m){return m.t}),
               T.markerAdd([],"",{}).length,
               T.markerAdd([],null,{}).length,
               T.markerAdd([],"4",{}).length];
/* R-3 : LE TYPE EST REFUSE AVANT LA VALEUR. `Number(true)` vaut 1 et
   `Number([])` vaut 0 : un booleen devenait un marqueur a 1 s, un tableau
   vide un marqueur a 0 s. Seuls un NOMBRE et une CHAINE sont des temps. */
out.mk_t_types=[T.markersFrom([{t:!0},{t:[]},{t:{}},{t:2}])
                  .map(function(m){return m.t}),
                T.markerAdd([],!0,{}).length,
                T.markerAdd([],[],{}).length,
                T.markerAdd([],2,{}).length];
/* --- [5] D-20 : LA GALERIE DES TRANSITIONS ------------------------------
   `CAT` est un catalogue MINUSCULE (deux familles, trois transitions) et
   c'est délibéré : il ne ressemble pas à celui du serveur, ce qui rend
   visible ce que chaque fonction lui demande VRAIMENT. `transFamily` rend
   "volets" pour `wipetl` alors que CAT n'a pas cette famille -- la table des
   familles est CLIENTE (DZM_TRANS_FAM, une table de STYLE : elle choisit
   l'animation de la micro-scène dès le premier rendu, avant que le réseau
   ait répondu) et le catalogue ne sert qu'aux libellés et au drapeau `live`.
   Le repli sur le catalogue est mesuré à part (tl_fam_du_catalogue). */
var CAT={familles:[{id:"fondus",label:"fondus",items:[{id:"fade",label:"fondu",live:!0},{id:"fadeblack",label:"fondu noir",live:!0}]},
  {id:"pixels",label:"pixels",items:[{id:"pixelize",label:"pixélisé",live:!1}]}]};
var LEG=[["cut","coupe sèche"],["fade","fondu"],["glitch","pixélisé"]];
out.tl_liste=T.transList(LEG,CAT).map(function(f){return [f.id,f.items.map(function(i){return i.id})]});
out.tl_cut_en_tete=T.transList(LEG,CAT)[0].items[0].id;
out.tl_sans_catalogue=T.transList(LEG,null).map(function(f){return [f.id,f.items.length]});
out.tl_label=[T.transLabel("fadeblack",LEG,CAT),T.transLabel("cut",LEG,CAT),T.transLabel("zzz",LEG,CAT)];
out.tl_fam=[T.transFamily("wipetl",CAT),T.transFamily("cut",CAT),T.transFamily("zzz",CAT)];
out.tl_live=[T.transLive("fade",CAT),T.transLive("pixelize",CAT),T.transLive("cut",CAT),T.transLive("zzz",CAT)];
out.tl_pur=CAT.familles.length===2&&LEG.length===3;
/* le REPLI : une famille que la table cliente ne connait pas est LUE dans le
   catalogue. Sans cette moitié, ajouter une famille au serveur donnerait des
   tuiles sans `data-fam` du tout. */
out.tl_fam_du_catalogue=T.transFamily("zz1",{familles:[{id:"neuve",label:"n",items:[{id:"zz1",label:"z"}]}]});
/* les libellés du CATALOGUE priment sur ceux des sept historiques : `fade`
   est dans les deux, et c'est le serveur qui parle. */
out.tl_label_catalogue_prime=T.transLabel("fade",LEG,CAT);
/* la DIRECTION : quatre sens, et le vide pour ce qui n'en a pas. `hlslice`
   va à DROITE (la moitié gauche part, l'entrant vient de la droite). */
out.tl_dir=[T.transDir("slideleft"),T.transDir("wipeup"),T.transDir("hlslice"),
            T.transDir("fade"),T.transDir("zzz")];
/* la table cliente COUVRE les 58 : chaque nom y est UNE SEULE FOIS. Le banc
   croisé avec le backend vit dans test_montage_l2.py ; ici on mesure la
   cohérence interne de la copie. */
out.tl_fam_58=(function(){var a=[],k,i;
  for(k in T.TRANS_FAM)for(i=0;i<T.TRANS_FAM[k].length;i++)a.push(T.TRANS_FAM[k][i]);
  var u={},dbl=0,j;for(j=0;j<a.length;j++){if(u[a[j]])dbl++;u[a[j]]=1}
  return [a.length,Object.keys(u).length,dbl,Object.keys(T.TRANS_FAM)]})();
/* les tables sont GELEES EN PROFONDEUR, comme MODES et MARKER_COLORS : le
   shim est en mode strict, une ecriture y leve. `Object.freeze` est
   SUPERFICIEL -- les deux dernieres lignes visent les TABLEAUX portes par
   les objets, qui restaient modifiables quand seul l objet etait scelle
   (mesure : `TRANS_FAM.fondus.push("zzz")` passait en silence). */
out.tl_gel=(function(){var a=[];
  try{T.TRANS_FAM.zzz=["x"];a.push("no")}catch(e){a.push(e.constructor.name)}
  try{T.TRANS_DIR.zzz=["x"];a.push("no")}catch(e){a.push(e.constructor.name)}
  try{T.TRANS_FAM.fondus.push("zzz");a.push("no")}catch(e){a.push(e.constructor.name)}
  try{T.TRANS_DIR.left[0]="zzz";a.push("no")}catch(e){a.push(e.constructor.name)}
  a.push(T.TRANS_FAM.fondus.length,T.TRANS_DIR.left[0]);
  return a})();
/* MOUS : aucune de ces entrees ne doit lever, et la CLE existe toujours. */
out.tl_mous=[T.transList(null,null).length,T.transList("x","y").length,
             T.transList(LEG,{familles:"x"}).length,
             T.transList(LEG,{familles:[null,{id:"f",items:[null,{id:"a"}]}]})
               .map(function(f){return [f.id,f.items.length]}),
             T.transLabel(null,null,null),T.transFamily(null,null),
             T.transLive(null,null),T.transDir(null)];
/* LA COMPOSANTE : elle EXISTE et ne touche a `r` qu'a l'appel (le shim de ce
   banc n'a pas de stub JSX -- son RENDU est mesure par test_montage_bundle). */
/* M2 : `SVM_TRANS` est une liste de PAIRES -- rien n y interdit deux
   entrees de meme nom. Sans dedoublonnage, la galerie rendait deux tuiles
   de meme cle React. Le PREMIER gagne, libelle compris. */
out.tl_doublons=T.transList([["cut","c"],["glitch","un"],["glitch","deux"],["slide","s"]],null)
  .map(function(f){return [f.id,f.items.map(function(i){return [i.id,i.label]})]});
out.tl_grille_existe=typeof T.TransGrid;
/* `window.__dzTransCat` : X4 lit ce global au niveau MODULE. Sous node, en
   "use strict" avec `var window={}`, la lecture d'une propriete ABSENTE rend
   `undefined` et ne leve pas -- c'est la mesure qui autorise la forme
   `window.__dzTransCat||null` ecrite dans le patcher. */
out.tl_global_ne_leve_pas=(function(){
  try{return [window.__dzTransCat||null,"pas de levee"]}
  catch(e){return ["LEVEE",e.constructor.name]}})();
console.log(JSON.stringify(out));
"""
print("\n[1] dzmInsere sous node")
D = {}
if not NODE or not os.path.isfile(SRC_PATH):
    check("js_shim_execute", False, f"node={NODE} src={os.path.isfile(SRC_PATH)}")
else:
    shim = os.path.join(TMP, "shim.js")
    with open(SRC_PATH, "rb") as fh: SRC = fh.read().decode("utf-8-sig")
    with open(shim, "w", encoding="utf-8") as fh:
        fh.write('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + SRC + "\n" + PROBE)
    r = sh([NODE, shim])
    check("js_shim_execute", r.returncode == 0, (r.stderr or "")[-600:])
    lignes = (r.stdout or "").strip().splitlines()
    derniere = lignes[-1] if lignes else ""
    # M7 (revue 21/09) : l'ancien label `js_shim_json_illisible` n'EXISTAIT
    # qu'en echec -- un banc vert ne disait donc rien de la lisibilite du
    # JSON. Label renomme `js_shim_json_lisible` et TOUJOURS evalue, comme
    # `js_shim_rend_un_objet_json`, qui sort du `else` pour la meme raison.
    lisible, temoin_json = True, ""
    try:
        D = json.loads(derniere) if derniere else {}
    except Exception as e:
        D = {}; lisible = False; temoin_json = temoin(e)
    check("js_shim_json_lisible", lisible, temoin_json)
    check("js_shim_rend_un_objet_json", isinstance(D, dict) and bool(D), repr(derniere)[:160])

check("modes_les_six", D.get("modes") == ["ecraser","inserer","fin","dessus","ripple_ecraser","remplir"],
      D.get("modes"))
check("ecraser_rogne_et_fend", D.get("ecraser") == [["p1",0,2,None],["x",2,5,0],["p2",5,8,1]], D.get("ecraser"))
check("ecraser_ne_touche_pas_les_autres_pistes", D.get("ecraser_autres") == 1,
      D.get("ecraser_autres"))
check("inserer_fend_et_pousse", D.get("inserer") == [["p1",0,2,None],["x",2,5,0],["p1_r",5,7,2],["p2",7,11,None]],
      D.get("inserer"))
check("fin_apres_le_dernier", D.get("fin") == [["p1",0,4,None],["p2",4,8,None],["x",8,11,0]], D.get("fin"))
check("dessus_prend_la_piste_libre_la_plus_proche",
      D.get("dessus_piste") == "v3" and D.get("dessus") == [["x",2,5,0]], D.get("dessus_piste"))
check("dessus_v2_quand_libre", D.get("dessus_v2_libre") == "v2")
# ECART MESURE CONTRE LE PLAN (21/09/2026), et la mesure gagne : le plan
# attendait x pose SOUS LA TETE ([2,5[, p2 recale a [5,9[). Rejoue a la
# main sur le coeur livre : `under`=p1 [0,4[ (le clip SOUS la tete a t=2),
# s0=0 (le DEBUT de p1, pas la tete), d=len-(under.end-s0)=3-4=-1 -> x
# prend la place de p1 depuis SON DEBUT : [0,3[, et p2 (qui commencait a
# under.end=4) recale de d=-1 -> [3,7[. C'est le sens Resolve d'un ripple
# overwrite : on REMPLACE le clip entier sous la tete, pas seulement le
# morceau apres la tete.
check("ripple_ecraser_remplace_depuis_le_debut_du_clip_sous_la_tete",
      D.get("ripple") == [["x",0,3,0],["p2",3,7,None]], D.get("ripple"))
check("remplir_fixe_bornes_et_vitesse",
      D.get("remplir") == [["p1",0,2,None],["x",2,5,0],["p2",5,8,1]] and D.get("remplir_speed") == 2,
      D.get("remplir_speed"))
check("remplir_sans_plage_retombe_en_ecraser", D.get("remplir_sans_plage") == "ecraser")
# ECART MESURE (21/09/2026) : le plan attendait `["xa",2,5,None]`. Rejoue a
# la main sur `dzmPose` : le clip jumeau (`twin`) ne porte pas `srcIn`, et
# `dzmPose` force `k.srcIn=0` quand la cle est absente ou nulle (meme regle
# que pour `x`, qui porte `srcIn:0` explicitement mais rendrait pareil sans).
# Le clip jumeau doit donc rendre `srcIn:0`, pas `None` -- sinon la ligne
# demande a `dzmPose` de traiter le jumeau autrement que tout le reste de
# la couche, ce que rien d'autre ne justifie.
check("jumeau_suit_sur_sa_piste",
      D.get("jumeau") == [["n1",0,2,None],["xa",2,5,0],["n1_r",5,11,2]], D.get("jumeau"))
# REGLE DES ASSERTIONS NEGATIVES : "entrees molles" mele des zeros et une
# chaine attendue -- aucune n'est une negation creuse (0 est etabli par un
# calcul mesure, pas par l'absence de mesure), mais la cle "mou" doit
# d'abord ETRE LA pour que la comparaison ne verdisse pas sur un shim muet.
check("entrees_molles", "mou" in D and D.get("mou") == [0, 4, "ecraser", "verrou"],
      f'"mou" in D={"mou" in D} v={D.get("mou")!r}')
check("insere_est_pur", D.get("pur") is True)

# ── revue du 21/09/2026 : les quinze lignes du second tour ────────────────
# REGLE DES ASSERTIONS NEGATIVES : chaque ligne qui nie quelque chose
# (« v1 inchangee », « pas de srcIn », « le son n'a pas ete pose ») etablit
# D'ABORD que la cle mesuree EST LA -- sinon un shim muet la ferait verdir.
check("dessus_repli_respecte_le_verrou",
      "dessus_repli_verrou" in D and
      D.get("dessus_repli_verrou") == ["verrou", "v1", [["p1",0,4,None],["p2",4,8,None]]],
      f'{"dessus_repli_verrou" in D} {D.get("dessus_repli_verrou")!r}')
check("jumeau_refuse_sur_piste_verrouillee",
      "jumeau_verrou" in D and
      D.get("jumeau_verrou") == ["verrou_jumeau", [["n1",0,8,None]], 3, True],
      f'{"jumeau_verrou" in D} {D.get("jumeau_verrou")!r}')
check("dessus_refuse_un_clip_audio",
      D.get("dessus_audio") == ["a1", "aucune_piste", "ecraser"], D.get("dessus_audio"))
check("jumeau_reste_synchrone_en_ripple",
      "jumeau_ripple" in D and D.get("jumeau_ripple") == [["x",0,3,0],["xa",0,3,0]],
      f'{"jumeau_ripple" in D} {D.get("jumeau_ripple")!r}')
check("jumeau_reste_synchrone_en_fin",
      "jumeau_fin" in D and D.get("jumeau_fin") == [["x",8,11,0],["xa",8,11,0]],
      f'{"jumeau_fin" in D} {D.get("jumeau_fin")!r}')
check("jumeau_reprend_la_vitesse_en_remplir",
      D.get("jumeau_remplir") == [2, ["xa",2,5,0]], D.get("jumeau_remplir"))
check("jumeau_pose_meme_en_repli_dessus",
      D.get("jumeau_repli") == ["aucune_piste", ["xa",2,5,0]], D.get("jumeau_repli"))
# ECART MESURE CONTRE LA REVUE (21/09/2026), et la mesure gagne : la revue
# annoncait des identifiants v1 en ["p1","p2","p2_r"]. Rejoue sous node sur
# le coeur corrige : `sv` TRIE PAR `start`, et le clip pose occupe [2,5[
# tandis que le `p2` survivant est rogne a [5,8[ -- l'ordre CHRONOLOGIQUE
# est donc ["p1","p2_r","p2"]. Le fond est celui que la revue demandait :
# c'est le clip POSE qui est renomme (`p2_r`), l'existant garde son `p2`.
check("id_en_collision_renomme",
      D.get("id_collision") == [["p1","p2_r","p2"], "p2_r"], D.get("id_collision"))
check("longueur_nulle_repli_six_secondes", D.get("len0") == ["x",2,8,0], D.get("len0"))
check("fend_avec_vitesse",
      D.get("fend_vitesse") == [["p1",0,2,10],["x",2,5,0],["p1_r",5,7,14]], D.get("fend_vitesse"))
check("ripple_tete_dans_un_trou",
      D.get("ripple_trou") == ["ecraser", [["p1",0,1,None],["x",3,6,0],["p2",6,9,None]]],
      D.get("ripple_trou"))
check("titre_sans_source_ne_gagne_pas_de_srcIn",
      "titre_carve" in D and "titre_pose" in D and
      D.get("titre_carve") == [["tt",0,2,False],["tt_r",5,10,False]] and
      D.get("titre_pose") is False,
      f'carve={D.get("titre_carve")!r} pose={D.get("titre_pose")!r}')
check("vitesse_ecretee_est_dite",
      isinstance(D.get("ecrete"), list) and D.get("ecrete")[:1] == [4]
      and isinstance(D.get("ecrete")[1], str) and "×4" in D.get("ecrete")[1],
      D.get("ecrete"))
JETONS = ["clips", "clip", "verrou", "verrou_jumeau", "aucune_piste"]
check("refus_sont_des_jetons",
      isinstance(D.get("refus_lus"), list) and len(D.get("refus_lus")) >= 5
      and all(x in JETONS for x in D.get("refus_lus"))
      and D.get("refus_table") == JETONS,
      f'lus={D.get("refus_lus")!r} table={D.get("refus_table")!r}')
check("modes_exportes_immuables",
      D.get("modes_gel") == [6, "TypeError", "ecraser", "TypeError"], D.get("modes_gel"))

print("\n[2] etat vide (garde des assertions negatives)")
# Copie du banc pointee sur un fichier VIDE : si le shim meurt ou `D` reste
# `{}`, AUCUNE ligne au-dessus de celle-ci ne doit verdir sauf via un `in D`
# explicite (il n'y en a qu'une, `entrees_molles`, et elle EXIGE "mou" in D,
# donc elle rougit aussi). Prouve ici sur une COPIE dans un dossier temporaire.
vide_dir = tempfile.mkdtemp(prefix="dzl1_vide_")
try:
    vide_shim = os.path.join(vide_dir, "shim.js")
    with open(vide_shim, "w", encoding="utf-8") as fh:
        fh.write('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + "" + "\n" + PROBE)
    rv = sh([NODE, vide_shim]) if NODE else None
    if rv is not None and rv.returncode != 0:
        vide_dv = {}
    else:
        lignes_v = (rv.stdout or "").strip().splitlines() if rv else []
        derniere_v = lignes_v[-1] if lignes_v else ""
        try:
            vide_dv = json.loads(derniere_v) if derniere_v else {}
        except Exception:
            vide_dv = {}
    # aucune des cles utilisees par les `check` positifs plus haut ne doit
    # apparaitre dans D quand la source est vide (T.MODES etc n'existent pas)
    vide_cles = ["modes","ecraser","inserer","fin","dessus_piste","ripple","remplir","jumeau",
                 "slip","slide","roll","voisins","mou3","pur3",
                 "slide_borne_gauche","slide_sans_gauche",
                 "roll_borne_source","roll_non_contigu",
                 "voisins_dixieme_exact","roll_pistes_diff",
                 "slide_tete_source_vitesse","roll_tete_source_vitesse",
                 "mk_liste","mk_next","mk_from","mk_colors","mk_gel",
                 "mk_update","mk_composants","mk_from_plafond",
                 "mk_from_espacement","mk_t_vide","mk_toggle_le_plus_proche",
                 "mk_from_eps_exact","mk_t_types",
                 "tl_liste","tl_sans_catalogue","tl_label","tl_fam",
                 "tl_live","tl_dir","tl_fam_58","tl_gel","tl_mous",
                 "tl_grille_existe","tl_global_ne_leve_pas","tl_doublons"]
    vide_absent = all(k not in vide_dv for k in vide_cles)
    # I8 (revue 21/09) : cette preuve n'etait qu'un `print` -- elle ne
    # POUVAIT pas rougir. Elle est maintenant une ASSERTION, et la source
    # vide est ecrite EN LIGNE dans le shim (le fichier `montage_vide.js`
    # d'avant n'etait jamais relu : code mort, retire).
    check("etat_vide_aucune_cle_positive",
          isinstance(vide_dv, dict) and vide_absent,
          f"returncode={'n/a' if rv is None else rv.returncode} D={vide_dv!r}")
finally:
    shutil.rmtree(vide_dir, ignore_errors=True)

print("\n[3] D-3 : roll, slip, slide sous node")
# Faute n6 : chaque lecture indexee passe par `at()`, qui rend un TEMOIN
# distinguable (et jamais egal a une attente) quand la cle manque ou que la
# liste est trop courte -- une lecture nue `D.get("slip_borne_bas")[1]`
# mourrait sur l'etat vide au lieu de rougir.
def at(k, *ix):
    v = D.get(k)
    for i in ix:
        if not isinstance(v, list) or len(v) <= i:
            return f"<absent:{k}{list(ix)}>"
        v = v[i]
    return v

check("slip_deplace_la_source_sans_bouger_le_clip",
      D.get("slip") == [["p1",0,4,0],["p2",4,8,1],["p3",8,10,0]], D.get("slip"))
check("slip_borne_bas", at("slip_borne_bas",1) == ["p2",4,8,0], at("slip_borne_bas",1))
check("slip_borne_haut", at("slip_borne_haut",1) == ["p2",4,8,6], at("slip_borne_haut",1))
check("slip_suit_la_vitesse", at("slip_vitesse",1) == ["p2",4,8,0], at("slip_vitesse",1))
# La borne HAUTE aussi compte en source : longueur consommee = 4 x 2 = 8,
# donc srcIn plafonne a 20 - 8 = 12 et non a 20 - 4 = 16.
check("slip_borne_haut_suit_la_vitesse",
      at("slip_borne_haut_vitesse",1) == ["p2",4,8,12], at("slip_borne_haut_vitesse",1))
check("slip_titre_ne_gagne_pas_de_srcIn",
      "slip_titre" in D and D.get("slip_titre") is False, D.get("slip_titre"))
check("slide_les_voisins_compensent",
      D.get("slide") == [["p1",0,5,0],["p2",5,9,2],["p3",9,10,1]], D.get("slide"))
# I1 : sur K3 NU, p3 part de srcIn 0 et tout recul est borne a zero. La
# ligne travaille donc sur K3N (p3 srcIn 2), et le srcIn de p3 RECULE de 1.
check("slide_negatif",
      D.get("slide_neg") == [["p1",0,3,0],["p2",3,7,2],["p3",7,10,1]], D.get("slide_neg"))
# M4 : attente CHIFFREE EXACTE, et non deux inegalites -- la forme d'avant
# etait vraie de toute une famille de resultats.
check("slide_borne_par_le_voisin_droit",
      D.get("slide_borne") == [["p1",0,5.7,0],["p2",5.7,9.7,2],["p3",9.7,10,1.7]],
      D.get("slide_borne"))
# LA BORNE GAUCHE, vue pour de bon : p3 porte 9 s de source devant lui, donc
# la tete de source ne borne plus rien et c'est p1 (4 s, min 0,3) qui arrete
# le recul a -3,7.
check("slide_borne_par_le_voisin_gauche",
      D.get("slide_borne_gauche") == [["p1",0,0.3,0],["p2",0.3,4.3,2],["p3",4.3,10,5.3]],
      D.get("slide_borne_gauche"))
# I1 : la MEME demande sur K3 nu ne bouge RIEN -- p3 n'a pas de source avant
# sa tete. C'est la ligne qui aurait rougi avant le correctif : le slide
# reculait p3 jusqu'a 4,3 avec un srcIn ecrete a 0, soit 4,3 s inventees.
check("slide_borne_par_la_tete_de_source_du_voisin_droit",
      D.get("slide_borne_source_droite") == [["p1",0,4,0],["p2",4,8,2],["p3",8,10,0]],
      D.get("slide_borne_source_droite"))
# SANS VOISIN GAUCHE, la borne est le zero de la timeline -- et la tete de
# source du droit (5 s) est plus large, donc c'est bien zero qui arrete.
check("slide_sans_voisin_gauche_s_arrete_a_zero",
      D.get("slide_sans_gauche") == [["c",0,4,0],["d",4,12,3]], D.get("slide_sans_gauche"))
check("slide_la_source_du_voisin_droit_suit_la_vitesse",
      at("slide_vitesse",2) == ["p3",9,10,3], at("slide_vitesse",2))
check("slide_sans_voisin_droit_ne_bouge_pas",
      D.get("slide_sans_voisin") == [["p1",0,4,0],["p2",4,8,2],["p3",8,10,0]],
      D.get("slide_sans_voisin"))
check("roll_recule",
      D.get("roll") == [["p1",0,3,0],["p2",3,8,1],["p3",8,10,0]], D.get("roll"))
check("roll_avance",
      D.get("roll_avant") == [["p1",0,5,0],["p2",5,8,3],["p3",8,10,0]], D.get("roll_avant"))
# I1 : sur K3 nu, la borne de TETE DE SOURCE de p2 (-2) est plus serree que
# celle des 0,3 s (-3,7) -- la ligne ne verrait donc plus la borne qu'elle
# nomme. Elle joue sur K3G (p2 srcIn 9), ou la source ne borne plus rien.
check("roll_borne_a_0_3_s", at("roll_borne",0,2) == 0.3, at("roll_borne",0,2))
check("roll_borne_haut_a_0_3_s",
      D.get("roll_borne_haut") == [["p1",0,7.7,0],["p2",7.7,8,5.7],["p3",8,10,0]],
      D.get("roll_borne_haut"))
# I1 : la jonction ne recule pas au-dela de la tete de source du clip DROIT.
# Avant le correctif, p2 partait a 0,3 avec un srcIn ecrete a 0 : 1,7 s de
# media INVENTE devant sa source.
check("roll_ne_depasse_pas_la_tete_de_source_du_droit",
      D.get("roll_borne_source") == [["p1",0,2,0],["p2",2,8,0],["p3",8,10,0]],
      D.get("roll_borne_source"))
# I2 : p1 et p3 ne se touchent pas -- ce n'est pas une jonction, rien ne
# bouge. La cle doit EXISTER : sans ce conjoint, la ligne serait vraie d'un
# banc ou la sonde n'a jamais tourne.
check("roll_refuse_deux_clips_non_contigus",
      "roll_non_contigu" in D
      and D.get("roll_non_contigu") == [["p1",0,4,0],["p2",4,8,2],["p3",8,10,0]],
      D.get("roll_non_contigu"))
check("roll_la_source_du_droit_suit_la_vitesse",
      at("roll_vitesse",2) == ["p3",9,10,3], at("roll_vitesse",2))
# I2, SECONDE MOITIE DE LA GARDE : `a` (V1) et `b` (A1) sont CONTIGUS en
# temps -- seule la piste les separe. Sans cette ligne, retirer `L.tr!==R.tr`
# ne faisait rougir personne : le mutant survivait.
check("roll_refuse_deux_pistes_differentes",
      "roll_pistes_diff" in D
      and D.get("roll_pistes_diff") == [["a","v1",0,4,0],["b","a1",4,8,0]],
      D.get("roll_pistes_diff"))
# I1, LA DIVISION PAR LA VITESSE : p3 va a x2 avec srcIn 1, donc il ne reste
# qu'une DEMI-seconde de timeline devant sa tete de source. Sans le
# `/dzmSpeedNum(...)`, la borne vaudrait -1 et p3 partirait a 7 : le mutant
# survivait aux lignes a vitesse 1, ou diviser par 1 ne se voit pas.
check("slide_la_tete_de_source_se_compte_en_source",
      D.get("slide_tete_source_vitesse")
      == [["p1",0,3.5,0],["p2",3.5,7.5,2],["p3",7.5,10,0]],
      D.get("slide_tete_source_vitesse"))
check("roll_la_tete_de_source_se_compte_en_source",
      D.get("roll_tete_source_vitesse")
      == [["p1",0,4,0],["p2",4,7.5,2],["p3",7.5,10,0]],
      D.get("roll_tete_source_vitesse"))
check("voisins_de_contact", D.get("voisins") == ["p1","p3"], D.get("voisins"))
check("voisins_ignorent_les_autres_pistes",
      "voisins_autre_piste" in D and D.get("voisins_autre_piste") == [None, None],
      D.get("voisins_autre_piste"))
check("voisins_le_contact_a_un_dixieme_exact",
      "voisins_dixieme_exact" in D and D.get("voisins_dixieme_exact") == "a",
      D.get("voisins_dixieme_exact"))
check("trims_entrees_molles", "mou3" in D and D.get("mou3") == [0, 3, 3, 4], D.get("mou3"))
check("trims_purs", D.get("pur3") is True, D.get("pur3"))

print("\n[4] D-5 : marqueurs et index sous node")
# Faute n6 : toute lecture indexee passe par `at()` (defini en [3]).
check("mk_liste_triee_par_t_couleur_par_defaut_or",
      D.get("mk_liste") == [[2.004,"or","intro"],[4,"or",""],[7,"rouge","b"]],
      D.get("mk_liste"))
check("mk_les_identifiants_sont_uniques",
      "mk_ids_uniques" in D and D.get("mk_ids_uniques") is True,
      f'{"mk_ids_uniques" in D} {D.get("mk_ids_uniques")!r}')
# LA BASCULE : reposer a moins de 0,15 s d'un marqueur le RETIRE au lieu de
# le doubler (geste de Resolve, une seule touche). `{force:true}` passe
# outre -- l'index doit pouvoir doubler un repere si on le lui demande.
check("mk_reposer_sous_l_eps_retire_au_lieu_de_doubler", D.get("mk_toggle") == 2,
      D.get("mk_toggle"))
check("mk_force_ajoute_meme_pres_d_un_existant", D.get("mk_force") == 4,
      D.get("mk_force"))
check("mk_retirer_par_id", D.get("mk_remove") == 2, D.get("mk_remove"))
# NEGATION GARDEE : « un id inconnu ne retire rien » serait vraie d'un banc
# muet -- la cle doit d'abord ETRE LA, et la longueur vaut celle de depart.
check("mk_retirer_un_id_inconnu_ne_retire_rien",
      "mk_remove_inconnu" in D and D.get("mk_remove_inconnu") == 3,
      f'{"mk_remove_inconnu" in D} {D.get("mk_remove_inconnu")!r}')
# ECART MESURE CONTRE LE PLAN, ET LE PLAN AVAIT RAISON POUR UNE AUTRE
# RAISON QUE LA SIENNE. Le plan attendait `markerNext(M,2,1) == 4` en
# annoncant un `>v+1e-6` : avec ce seuil-la, le premier t superieur a 2 est
# 2,004 et la ligne aurait rougi. Le seuil est donc DZM_MARKER_EPS (0,15),
# pas 1e-6, et c'est le bon sens pour Ctrl+Bas : « aller au SUIVANT » depuis
# un marqueur doit quitter celui sous la tete, pas y rester. Les trois
# `null` du plan tiennent avec l'un comme avec l'autre -- seule la premiere
# valeur distingue les deux seuils, et c'est elle qui tranche.
check("mk_suivant_ignore_le_marqueur_sous_la_tete",
      D.get("mk_next") == [4, None, None, None], D.get("mk_next"))
# LE CONJOINT POSITIF des trois `null` ci-dessus : dans les quatre memes
# directions, depuis des tetes qui ONT un voisin, la fonction le trouve.
# Sans cette ligne, un `markerNext` qui rendrait TOUJOURS `null` passerait.
check("mk_suivant_et_precedent_trouvent_vraiment",
      D.get("mk_next_vrai") == [2.004, 7, 7, 2.004], D.get("mk_next_vrai"))
check("mk_restauration_assainit_et_trie",
      D.get("mk_from") == [[1.5,"bleu","ok","n"],[3,"or","5",""]], D.get("mk_from"))
# LES IDS SONT REGENERES m1..mN, DANS L'ORDRE CHRONOLOGIQUE. Revue du
# 21/09/2026 : ils etaient attribues dans l'ordre d'ARRIVEE, puis la liste
# etait triee -- d'ou des ids dans le desordre (m2, m3, m1). L'ordre du
# filtre d'espacement (I-2) impose de trier AVANT, et la numerotation suit
# donc la chronologie. C'est aussi ce que l'index affiche.
check("mk_restauration_regenere_des_ids_uniques",
      at("mk_from_ids", 0) == ["m1","m2","m3"] and at("mk_from_ids", 1) == 3,
      f'{at("mk_from_ids",0)!r} {at("mk_from_ids",1)!r}')
check("mk_restauration_tronque_a_deux_cents", D.get("mk_from_plafond") == 200,
      D.get("mk_from_plafond"))
check("mk_les_six_couleurs",
      D.get("mk_colors") == ["or","rouge","vert","bleu","violet","cyan"],
      D.get("mk_colors"))
check("mk_couleurs_exportees_immuables",
      D.get("mk_gel") == [6, "TypeError", "or", "TypeError"], D.get("mk_gel"))
# ENTREES MOLLES, cle exigee d'abord : t negatif et NaN sont IGNORES (la
# liste rendue garde ses trois marqueurs), une liste nulle ou une chaine
# rendent une liste vide, et `markerRemove(null, ...)` ne meurt pas.
check("mk_entrees_molles",
      "mk_mous" in D and D.get("mk_mous") == [3, 3, 1, 0, 0],
      f'{"mk_mous" in D} {D.get("mk_mous")!r}')
check("mk_update_assainit_couleur_et_chaines",
      D.get("mk_update") == ["or", "7", "", 3], D.get("mk_update"))
check("mk_update_accepte_une_couleur_connue",
      D.get("mk_update_couleur") == "cyan", D.get("mk_update_couleur"))
# PATCH PARTIEL : une cle ABSENTE du patch ne doit pas ecraser la valeur.
# Sans ce conjoint, un `markerUpdate` qui reconstruirait l'entree entiere
# (titre remis a "") passerait les deux lignes du dessus.
check("mk_update_ne_touche_pas_les_cles_absentes_du_patch",
      D.get("mk_update_partiel") == ["vert", "intro"], D.get("mk_update_partiel"))
check("mk_update_d_un_id_inconnu_ne_change_rien",
      "mk_update_inconnu" in D
      and D.get("mk_update_inconnu") == [[2.004,"or"],[4,"or"],[7,"rouge"]],
      f'{"mk_update_inconnu" in D} {D.get("mk_update_inconnu")!r}')
check("mk_les_fonctions_sont_pures",
      D.get("mk_pur") is True and D.get("mk_update_pur") is True,
      f'add={D.get("mk_pur")!r} update={D.get("mk_update_pur")!r}')
# LES DEUX COMPOSANTS EXISTENT SOUS NODE, ou `svmTcFF` n'est PAS defini :
# c'est la preuve que la couche ne le lit pas AU CHARGEMENT. La resolution a
# l'appel (`typeof svmTcFF==="function"?svmTcFF:dzmSecs`) est tenue par le
# banc du bundle, qui RENDS les composants avec un stub JSX.
check("mk_les_deux_composants_sont_exportes",
      D.get("mk_composants") == ["function", "function"], D.get("mk_composants"))
# I-1 (revue du 21/09/2026) : LA BASCULE RETIRE LE PLUS PROCHE, PAS LE
# PREMIER DE LA LISTE. Mesure d'avant le correctif : A a 1,00, B a 1,10,
# tete a 1,09 -> A tombait, parce que `filter(...)[0]` rend le premier de la
# liste TRIEE et non le plus proche. Les DEUX sens sont joues -- une tete a
# 1,01 doit, elle, retirer A : sans le second cas, un `[l.length-1]` nu
# (« le dernier ») passerait la premiere ligne.
check("mk_la_bascule_retire_le_marqueur_le_plus_proche",
      D.get("mk_toggle_le_plus_proche") == ["A"]
      and D.get("mk_toggle_le_plus_proche_bas") == ["B"],
      f'1.09={D.get("mk_toggle_le_plus_proche")!r} '
      f'1.01={D.get("mk_toggle_le_plus_proche_bas")!r}')
# I-2 : L'INVARIANT D'ESPACEMENT EST TENU PAR `markersFrom` AUSSI. Avant le
# correctif, `markerAdd` en etait la SEULE gardienne : un fichier (ou un
# autre client) pouvait poser 1,00 et 1,12, et le second etait INJOIGNABLE
# par Ctrl+haut / Ctrl+bas, qui sautent tout ce qui est a moins d'un EPS de
# la tete. Les ids sont REGENERES apres le filtre : m1, m2, jamais un trou.
check("mk_restauration_tient_l_ecart_minimal",
      D.get("mk_from_espacement") == [["m1", 1], ["m2", 5]],
      D.get("mk_from_espacement"))
# LE DOUBLON EXACT TOMBE PAR LA MEME REGLE -- distance nulle, donc < EPS.
# Sans ce conjoint, un filtre ecrit `0 < d < EPS` passerait la ligne du
# dessus en laissant deux marqueurs au MEME temps.
check("mk_restauration_fusionne_les_doublons_exacts",
      "mk_from_doublon" in D and D.get("mk_from_doublon") == 1,
      f'{"mk_from_doublon" in D} {D.get("mk_from_doublon")!r}')
# LE TRI PRECEDE LE FILTRE : donne en desordre, c'est toujours le PREMIER
# CHRONOLOGIQUE de deux voisins qui reste. Un filtre applique avant le tri
# aurait garde 5 et 1,12 et jete 1.
check("mk_restauration_trie_avant_de_filtrer",
      D.get("mk_from_espacement_trie") == [1, 5],
      D.get("mk_from_espacement_trie"))
# `t:""` -- `Number("")` vaut ZERO en JavaScript quand `float("")` LEVE en
# Python : le client acceptait a 0 s un marqueur que le serveur jetait, et
# il disparaissait au rechargement sans un mot. `dzmMarkerT` dit desormais
# la meme chose que le backend. Le dernier terme est le conjoint positif :
# une chaine qui EST un nombre reste acceptee.
check("mk_un_temps_vide_est_refuse_comme_au_backend",
      D.get("mk_t_vide") == [[3], 0, 0, 1], D.get("mk_t_vide"))
# R-3 (seconde revue du 21/09/2026) : UN BOOLEEN N'EST PAS UN TEMPS.
# `Number(true)` vaut 1 et `Number([])` vaut 0 -- le premier devenait un
# marqueur a 1 s, le second un marqueur a 0 s, quand `_save_record` les
# refuse (test `isinstance(t, bool)`, et `float([])` leve). Le dernier
# terme de chaque moitie est le conjoint positif : un vrai nombre passe.
check("mk_un_temps_qui_n_est_ni_nombre_ni_chaine_est_refuse",
      D.get("mk_t_types") == [[2], 0, 0, 1], D.get("mk_t_types"))
# R-1 (seconde revue) : EXACTEMENT UN EPS EST TROP PROCHE. Le filtre etait
# STRICT quand `markerNext` exige `t > v + EPS` strict lui aussi : un
# couple a 0,150 s pile passait le filtre et restait INJOIGNABLE dans les
# DEUX sens (mesure : 697 couples au millieme entre 0 et 10 s). La seconde
# moitie est le conjoint positif -- un cheveu de plus, et les deux restent.
check("mk_un_ecart_d_exactement_un_eps_est_trop_proche",
      at("mk_from_eps_exact", 0) == [0] and at("mk_from_eps_exact", 1) == [0, 0.151],
      f'{at("mk_from_eps_exact",0)!r} {at("mk_from_eps_exact",1)!r}')
# ET LA RAISON, MESUREE PLUTOT QUE DITE : depuis 0, le marqueur a 0,150 est
# introuvable en avant ; depuis 0,150, celui de 0 est introuvable en
# arriere. C'est ce couple-la que le filtre large empeche d'exister.
check("mk_un_ecart_d_exactement_un_eps_serait_injoignable",
      "mk_eps_injoignable" in D and D.get("mk_eps_injoignable") == [None, None],
      f'{"mk_eps_injoignable" in D} {D.get("mk_eps_injoignable")!r}')

print("\n[5] D-20 galerie des transitions")
# LA LISTE : « coupe » d'abord, puis les historiques du bundle QUE LE
# CATALOGUE N'A PAS, puis les familles servies. Le plan attendait ici
# [coupe, fondus, pixels] et il avait TORT : `glitch` est dans LEG et n'est
# dans aucune famille de CAT -- il DOIT former le groupe « historiques »,
# sinon la transition d'un vieux montage disparaîtrait de la galerie. C'est
# exactement ce que `tl_sans_catalogue` (que le plan écrit juste) dit de
# l'autre côté : sans catalogue, les deux historiques restent.
check("tl_la_liste_commence_par_les_coupes_puis_les_familles",
      D.get("tl_liste") == [["coupe", ["cut"]], ["historiques", ["glitch"]],
                            ["fondus", ["fade", "fadeblack"]], ["pixels", ["pixelize"]]],
      D.get("tl_liste"))
check("tl_cut_reste_en_tete", D.get("tl_cut_en_tete") == "cut", D.get("tl_cut_en_tete"))
check("tl_sans_catalogue_les_historiques_restent",
      D.get("tl_sans_catalogue") == [["coupe", 1], ["historiques", 2]], D.get("tl_sans_catalogue"))
check("tl_le_libelle_vient_du_catalogue_puis_de_l_historique_puis_du_nom",
      D.get("tl_label") == ["fondu noir", "coupe sèche", "zzz"], D.get("tl_label"))
# ET LE CATALOGUE PRIME, mesuré sur un nom qui est DANS LES DEUX : sans cette
# ligne, `tl_label` serait vraie d'une fonction qui regarde d'abord LEG.
check("tl_le_catalogue_prime_sur_l_historique_pour_un_nom_commun",
      D.get("tl_label_catalogue_prime") == "fondu", D.get("tl_label_catalogue_prime"))
check("tl_la_famille_est_connue_ou_vide", D.get("tl_fam") == ["volets", "coupe", ""], D.get("tl_fam"))
# LE REPLI SUR LE CATALOGUE : une famille que la copie cliente ignore est
# quand même nommée. C'est la moitié que `tl_fam` ne voit pas.
check("tl_une_famille_inconnue_de_la_copie_est_lue_dans_le_catalogue",
      D.get("tl_fam_du_catalogue") == "neuve", D.get("tl_fam_du_catalogue"))
check("tl_le_direct_est_dit_par_le_catalogue",
      "tl_live" in D and D["tl_live"] == [True, False, True, False], D.get("tl_live"))
check("tl_la_direction_a_quatre_sens_et_un_vide",
      D.get("tl_dir") == ["left", "up", "right", "", ""], D.get("tl_dir"))
# LA COPIE CLIENTE COUVRE LES 58 SANS DOUBLON, et ses six familles portent
# les noms du serveur. Le banc CROISÉ avec `_XFADE_FAMILIES` vit dans
# test_montage_l2.py ; ici, la cohérence interne.
check("tl_la_copie_cliente_porte_58_noms_distincts_en_six_familles",
      D.get("tl_fam_58") == [58, 58, 0,
                             ["fondus", "glissements", "volets", "formes", "zooms", "pixels"]],
      D.get("tl_fam_58"))
# LE GEL EST PROFOND, ET LES DEUX DERNIERES VALEURS LE PROUVENT : la
# levee ne suffit pas a dire que RIEN n'a change (un `push` peut lever
# APRES avoir ecrit, selon le moteur). Les deux conjoints positifs
# relisent la longueur et le premier element.
check("tl_les_deux_tables_sont_gelees_en_profondeur",
      D.get("tl_gel") == ["TypeError", "TypeError", "TypeError", "TypeError",
                          8, "slideleft"], D.get("tl_gel"))
# MOUS : rien ne lève, et chaque repli est CHIFFRÉ. Le 4e élément mesure
# qu'une famille nulle et une entrée nulle sont écartées sans emporter la
# famille qui les entoure.
check("tl_les_entrees_molles_ne_levent_pas",
      "tl_mous" in D and D.get("tl_mous") == [1, 1, 2,
                                              [["coupe", 1], ["historiques", 2], ["f", 1]],
                                              "null", "", False, ""],
      D.get("tl_mous"))
check("tl_un_historique_en_double_ne_donne_qu_une_tuile",
      D.get("tl_doublons") == [["coupe", [["cut", "c"]]],
                               ["historiques", [["glitch", "un"], ["slide", "s"]]]],
      D.get("tl_doublons"))
check("tl_la_grille_est_une_fonction", D.get("tl_grille_existe") == "function",
      D.get("tl_grille_existe"))
# LA MESURE QUI AUTORISE `window.__dzTransCat||null` DANS X4 : sous node, en
# "use strict" et avec `var window={}`, lire une propriété ABSENTE rend
# `undefined` -- ce n'est pas une variable non déclarée, donc aucune
# ReferenceError. La forme du patcher tient.
check("tl_le_global_du_catalogue_ne_leve_pas_en_strict",
      D.get("tl_global_ne_leve_pas") == [None, "pas de levee"],
      D.get("tl_global_ne_leve_pas"))
check("tl_pur", D.get("tl_pur") is True, D.get("tl_pur"))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
