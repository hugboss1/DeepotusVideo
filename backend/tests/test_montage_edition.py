# -*- coding: utf-8 -*-
"""L1 — LES MODES D'EDITION (D-2), LES TRIMS ROLL/SLIP/SLIDE (D-3) ET LES MARQUEURS (D-5) : le coeur JS est EXECUTE sous node
(frontend/patches/montage.js, celui que le patcher injecte), jamais lu.
Shim par FICHIER, jamais `node -e`.
Run : & $PY tests\test_montage_edition.py   (depuis backend/)"""
import json, os, re, shutil, subprocess, sys, tempfile
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
/* `fade` EST DANS LES DEUX SOURCES, ET AVEC DEUX LIBELLES DIFFERENTS --
   c'est la seule facon que `tl_label_catalogue_prime` ait de mesurer
   VRAIMENT la priorite. Mesure du 22/09/2026 (campagne
   mutations_montage_l2.py, n°4) : avec « fondu » des deux cotes, la
   ligne restait VERTE alors que `dzmTransLabel` avait cesse de lire le
   catalogue -- elle ne separait pas les deux autorites, elle les
   confondait. */
var LEG=[["cut","coupe sèche"],["fade","fondu simple"],["glitch","pixélisé"]];
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
/* --- [5b] D-12 : LE VOILE DES FONDUS EN DIRECT ---------------------------
   `VC` est une timeline de quatre plans de 4 s : la jonction a mesurer est
   celle de `b` (fadeblack, 1 s), et les deux autres transitions sont la
   pour dire ce que la fonction REFUSE (pixelize : pas jouable en direct) et
   ce qu'elle accepte en blanc (fadewhite, 0,4 s). */
var VC=[{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
        {tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"fadeblack",transition_s:1},
        {tr:"v1",id:"c",start:8,end:12,src:{job_id:"j"},transition:"pixelize",transition_s:.5},
        {tr:"v1",id:"d",start:12,end:16,src:{job_id:"j"},transition:"fadewhite",transition_s:.4}];
out.vl_loin=T.veil(VC,2);
out.vl_milieu=T.veil(VC,4);
out.vl_avant=T.veil(VC,3.75);
out.vl_apres=T.veil(VC,4.25);
out.vl_pixel=T.veil(VC,8);
out.vl_blanc=T.veil(VC,12).color;
out.vl_fade=T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"fade",transition_s:.4}],4);
out.vl_premier=T.veil([{tr:"v1",id:"b",start:0,end:8,src:{job_id:"j"},transition:"fadeblack",transition_s:1}],0);
out.vl_mou=[T.veil(null,1).alpha,T.veil(VC,NaN).alpha];
/* LE NOM COMPOSE : le bundle stocke « <nom> <duree> » depuis toujours
   (svmTransBase garde le premier mot) ; la couche doit le lire pareil. */
out.vl_nom_compose=T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"fadeblack 0.4"}],4);
/* DEUX JONCTIONS DANS LA MEME FENETRE : `b` dure 0,6 s, les triangles de
   `b` (4 +- 0,5) et de `c` (4,6 +- 0,5) se recouvrent a 4,4. Le MAX gagne,
   donc `c` (0,6) et non `b` (0,2) -- la couleur le prouve. */
out.vl_deux_jonctions=T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:4.6,src:{job_id:"j"},transition:"fadeblack",transition_s:1},
  {tr:"v1",id:"c",start:4.6,end:8,src:{job_id:"j"},transition:"fadewhite",transition_s:1}],4.4);
/* A EGALITE D'ALPHA, LE PREMIER DU TABLEAU GARDE LA MAIN : a 4,3 les
   deux triangles valent 0,4 (4,3 est a 0,3 de 4 ET a 0,3 de 4,6). C'est la
   COULEUR qui le dit -- l'alpha, lui, serait le meme des deux cotes. */
out.vl_egalite=T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:4.6,src:{job_id:"j"},transition:"fadeblack",transition_s:1},
  {tr:"v1",id:"c",start:4.6,end:8,src:{job_id:"j"},transition:"fadewhite",transition_s:1}],4.3);
/* LE BORD EXACT DE LA FENETRE : a 4,5 (jonction 4, duree 1) l'alpha vaut
   ZERO. Pas de couleur pour un voile qui ne se voit pas. */
out.vl_bord=T.veil(VC,4.5);
/* UN TROU > 0,1 s N'EST PAS UNE JONCTION : `dzmVoisins` ne rend rien a
   gauche, et ffmpeg ne jouerait pas de xfade non plus. */
out.vl_trou=T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4.5,end:8,src:{job_id:"j"},transition:"fadeblack",transition_s:1}],4.5);
/* L'HERITAGE DU PROTOTYPE : `DZM_VEIL["constructor"]` est une FONCTION,
   donc vraie. Sans `hasOwnProperty`, le voile aurait pris `Object` pour
   une couleur et l'ecran se serait assombri sur un nom quelconque. */
out.vl_heritage=[T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"constructor"}],4),
  T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"toString"}],4)];
/* LES AUTRES PISTES ET LES CLIPS SANS SOURCE SONT HORS SUJET : le lecteur
   vivant ne montre que V1, et un clip sans `src` (un TITRE, D-21) n'a
   aucune image a fondre. */
out.vl_hors_v1=[T.veil([{tr:"v2",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v2",id:"b",start:4,end:8,src:{job_id:"j"},transition:"fadeblack",transition_s:1}],4).alpha,
  T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:8,transition:"fadeblack",transition_s:1}],4).alpha];
/* LES BORNES DE `svmTransS` (0,1 - 1 s) SONT CELLES DU BUNDLE : une duree
   de 9 s est ramenee a 1 (fenetre +-0,5), une de 0,01 a 0,1 (+-0,05). */
out.vl_bornes=[T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"fadeblack",transition_s:9}],4.6).alpha,
  T.veil([{tr:"v1",id:"a",start:0,end:4,src:{job_id:"j"}},
  {tr:"v1",id:"b",start:4,end:8,src:{job_id:"j"},transition:"fadeblack",transition_s:.01}],4.04).alpha];
/* LA TABLE EST GELEE, comme TRANS_FAM et MARKER_COLORS. Elle est PLATE
   (trois chaines) : un seul `Object.freeze` suffit, et les deux dernieres
   valeurs relisent le contenu -- la levee ne dit pas que rien n'a change. */
out.vl_gel=(function(){var a=[];
  try{T.VEIL.zzz="#f0f";a.push("no")}catch(e){a.push(e.constructor.name)}
  try{T.VEIL.fade="#f0f";a.push("no")}catch(e){a.push(e.constructor.name)}
  a.push(T.VEIL.fade,Object.keys(T.VEIL).length);return a})();
/* PURETE : la timeline d'entree n'est pas touchee. */
out.vl_pur=VC.length===4&&VC[1].transition==="fadeblack"&&VC[1].transition_s===1;
/* --- [6] D-21 : LE GENRE `title`, LA PISTE t1 ET LE CARTON --------------
   Un titre est un clip SANS `src` sur t1. Les quatre fonctions sont PURES
   et ne recopient AUCUN des huit gabarits : le nom du gabarit traverse, le
   backend decide. */
out.tt_defaut=T.DEFAULTS.some(function(t){return t.id==="t1"&&t.kind==="title"});
/* t1 EST LA PREMIERE LIGNE de la table, pas seulement presente : au-dessus
   de v2, donc tout en haut de la timeline. */
out.tt_defaut_tete=T.DEFAULTS[0]&&T.DEFAULTS[0].id;
out.tt_ensure=T.titleTrack([{id:"v1",kind:"video"},{id:"a1",kind:"audio"}]).map(function(t){return t.id});
out.tt_ensure_deja=T.titleTrack([{id:"t1",kind:"title"},{id:"v1",kind:"video"}]).length;
/* DEJA LA = LE MEME TABLEAU, pas une copie : l'appelant compare l'identite
   pour savoir s'il doit payer un `pushHistory`. Et une piste t1 SANS `kind`
   (vieille sauvegarde) compte deja comme une piste de titres. */
out.tt_ensure_identite=(function(){var ts=[{id:"t1",kind:"title"},{id:"v1",kind:"video"}];
  return T.titleTrack(ts)===ts})();
out.tt_ensure_sans_kind=T.titleTrack([{id:"t1"},{id:"v1"}]).length;
/* L'HABILLAGE DE LA PISTE POSEE vient de la table : sans hauteur, la bande
   ferait 0 px et porterait pourtant ses cartons. */
out.tt_ensure_habillage=(function(){var t=T.titleTrack([{id:"v1",kind:"video"}])[0];
  return [t.id,t.kind,t.name,t.h>0]})();
out.tt_group=[T.group({id:"t1",kind:"title"}),T.group({id:"v1",kind:"video"}),T.group({id:"s1",kind:"subs"})];
out.tt_pick=T.pickTrack([{id:"v1",kind:"video"},{id:"t1",kind:"title"}],"title");
/* LE GENRE SE DEDUIT DE L'INITIALE, comme `trackKind` du bundle (TT1) : une
   piste t1 sans `kind` est une piste de titres pour `pickTrack` aussi. */
out.tt_pick_sans_kind=T.pickTrack([{id:"v1"},{id:"t1"}],"title");
out.tt_pick_absente=T.pickTrack([{id:"v1",kind:"video"}],"title");
/* `from` (restauration) GARDE le genre title : mesure qui dit si TT3 a
   besoin d'un repli sur le genre, ou seulement sur la piste manquante. */
out.tt_from=T.from([{id:"t1",kind:"title"},{id:"v1",kind:"video"}])
  .map(function(t){return [t.id,t.kind,t.h]});
var TN=T.titleNew({template:"cta",text:"Abonnez-vous"},4,[],"t1");
out.tt_new=[TN.tr,TN.kind,TN.start,TN.end,TN.title.template,TN.title.text,"src" in TN];
/* LE LIBELLE DE LA BANDE est le texte tronque a 24 : la timeline dessine
   `c.label`, et un carton sans libelle n'aurait montre que son identifiant. */
out.tt_new_label=T.titleNew({text:"Abonnez-vous a la chaine du Deepotus"},0,[],"t1").label;
out.tt_new_sans_texte=T.titleNew({template:"cta",text:"  "},4,[],"t1");
/* NI TITRE MOU, NI TEXTE NON-CHAINE : `null`, jamais une levee ni un carton
   muet. Meme regle que `title_spec` du backend (`isinstance(str)`). */
out.tt_new_mous=[T.titleNew(null,4,[],"t1"),T.titleNew({text:42},4,[],"t1"),
  T.titleNew({text:"a"},NaN,[],"t1").start,T.titleNew({text:"a"},-3,[],"t1").start];
out.tt_new_id_unique=T.titleNew({text:"a"},0,[{id:"t1u1"}],"t1").id!=="t1u1";
/* LES CLES QUE L'APPELANT NE DIT PAS SONT ABSENTES, elles ne valent pas ""
   ni 0 : les defauts des huit gabarits vivent dans `titles.TEMPLATES`, et
   un `size:0` parti d'ici aurait donne 24 px au lieu des 64 du gabarit. */
out.tt_new_cles=Object.keys(T.titleNew({text:"a"},0,[],"t1").title);
out.tt_new_cles_pleines=Object.keys(T.titleNew({template:"legende",text:"a",
  sub:"b",color:"or",font:"Inter",size:80},0,[],"t1").title).sort();
out.tt_at=[!!T.titleAt([{tr:"t1",kind:"title",start:1,end:3,title:{text:"x"}},{tr:"v1",start:0,end:9,src:{a:1}}],2),
  !!T.titleAt([{tr:"t1",kind:"title",start:1,end:3,title:{text:"x"}}],5)];
/* FIN EXCLUE, DEBUT INCLUS, et le DERNIER DEPART gagne : les trois regles
   de `svmActiveV1`. Le clip rendu est NOMME -- une ligne sur « non nul »
   aurait ete verte sur le mauvais carton. */
var TA=[{tr:"t1",kind:"title",id:"a",start:0,end:4,title:{text:"a"}},
        {tr:"t1",kind:"title",id:"b",start:2,end:6,title:{text:"b"}}];
out.tt_at_recouvrement=[(T.titleAt(TA,0)||{}).id,(T.titleAt(TA,3)||{}).id,
  (T.titleAt(TA,4)||{}).id,T.titleAt(TA,6)];
out.tt_at_mous=[T.titleAt(null,1),T.titleAt(TA,NaN),
  T.titleAt([{tr:"v1",id:"z",start:0,end:9,src:{a:1}}],1)];
out.tt_html=T.titleHtml({tr:"t1",kind:"title",start:0,end:4,title:{template:"tiers_inferieur",text:"<b>Ab",sub:"ep"}},1);
/* LES CINQ CARACTERES : &, <, >, le guillemet et l'APOSTROPHE (ajoutee le
   22/09/2026 : l'echappeur etait juste a moitie). L'esperluette PASSE EN
   PREMIER, sinon `&lt;` serait devenu `&amp;lt;`. */
out.tt_html_esc=T.titleHtml({kind:"title",start:0,end:4,
  title:{text:'a&b<c>d"e'+String.fromCharCode(39)+"f"}},1);
/* HORS DE LA PLAGE, RIEN : l'appelant ecrit la chaine telle quelle dans
   `innerHTML`, et « vide » y vaut « efface ». */
out.tt_html_hors=[T.titleHtml({kind:"title",start:2,end:4,title:{text:"x"}},5),
  T.titleHtml({kind:"title",start:2,end:4,title:{text:"x"}},2),
  T.titleHtml({kind:"title",start:2,end:4,title:{text:"x"}},4)];
out.tt_html_mous=[T.titleHtml(null,1),T.titleHtml({kind:"title",title:{text:" "}},1),
  T.titleHtml({tr:"v1",start:0,end:4,src:{a:1}},1)];
/* UN GABARIT INCONNU NE REND QUE `dzm-tt` : la regle de base l'affiche au
   lieu de le faire disparaitre, et AUCUNE seconde table de huit noms n'est
   ecrite ici. Un nom hostile est assaini aux caracteres d'un identifiant --
   la classe ne peut pas sortir de l'attribut. */
out.tt_html_gabarit=[T.titleHtml({kind:"title",start:0,end:4,title:{text:"x"}},1),
  T.titleHtml({kind:"title",start:0,end:4,title:{template:'a"><img src=x ',text:"x"}},1)];
out.tt_remove=T.remove([{id:"t1",kind:"title"},{id:"v1",kind:"video"}],"t1").length;
/* PURETE : ni la liste de pistes ni celle des clips n'est touchee. */
out.tt_pur=(function(){var ts=[{id:"v1",kind:"video"}],cs=[{id:"z"}];
  T.titleTrack(ts);T.titleNew({text:"a"},0,cs,"t1");T.titleAt(cs,1);
  return ts.length===1&&cs.length===1})();
/* --- [6b] D-21 (tache 7) : REGLER UN CARTON ------------------------------
   `titleUpdate(clips,id,patch)` est PURE. L'IDENTITE du tableau rendu est le
   signal « rien n'a bouge » : c'est elle qui empeche l'hote de payer un
   pushHistory pour un blur qui n'a rien touche. */
var TU=[{tr:"t1",kind:"title",id:"t1u1",label:"Ab",start:0,end:4,
         title:{template:"cta",text:"Ab"}},
        {tr:"v1",id:"z",start:0,end:9,src:{a:1}}];
out.tu_texte=(function(){var q=T.titleUpdate(TU,"t1u1",{text:"Abonnez-vous"});
  return [q!==TU,q[0].title.text,q[0].label,q[1]===TU[1],TU[0].title.text]})();
/* SEPT REFUS, UN PAR REGLE -- et chacun rend LE MEME tableau. Sans cette
   ligne, une fonction qui recopierait toujours passerait `tu_texte`. */
out.tu_inchange=[T.titleUpdate(TU,"t1u1",{text:"Ab"})===TU,
  T.titleUpdate(TU,"t1u1",{text:"   "})===TU,
  T.titleUpdate(TU,"t1u1",{template:"!!!"})===TU,
  T.titleUpdate(TU,"t1u1",{})===TU,
  T.titleUpdate(TU,"zzz",{text:"x"})===TU,
  T.titleUpdate(TU,"z",{text:"x"})===TU,
  T.titleUpdate(TU,"t1u1",null)===TU];
/* LE TEXTE EST TRONQUE A 120 et le LIBELLE DE LA BANDE suit a 24 : la
   timeline dessine `c.label`, un carton renomme aurait garde son premier
   jet. */
out.tu_tronque=T.titleUpdate(TU,"t1u1",{text:new Array(200).join("x")})[0].title.text.length;
out.tu_label=T.titleUpdate(TU,"t1u1",{text:new Array(60).join("y")})[0].label.length;
/* LE GABARIT PASSE EN MINUSCULES AVANT d'etre assaini (sans quoi « CTA »
   devenait "" et « Plein_Cadre » devenait « lein_adre »), et un nom hostile
   ne sort pas de l'attribut. */
out.tu_gabarit=[T.titleUpdate(TU,"t1u1",{template:"Plein_Cadre"})[0].title.template,
  T.titleUpdate(TU,"t1u1",{template:'a"><img '})[0].title.template];
/* LA CHAINE VIDE EFFACE LA CLE -- c'est le choix « (du gabarit) » de
   l'inspecteur, qui doit RETIRER le reglage et non ecrire un `color:""`.
   ET LA COUCHE NE JUGE NI LA COULEUR NI LA POLICE : elle n'a aucune copie
   de BRAND ni de FONT_FILES, le backend assainit (`color not in BRAND`). */
out.tu_vide=(function(){
  var a=T.titleUpdate(TU,"t1u1",{color:"or",font:"Anton",sub:"s"});
  var b=T.titleUpdate(a,"t1u1",{color:""});
  var q=T.titleUpdate(a,"t1u1",{sub:"  "});
  return [Object.keys(a[0].title).sort(),"color" in b[0].title,
    "sub" in q[0].title,T.titleUpdate(TU,"t1u1",{color:"mauve"})[0].title.color]})();
out.tu_taille=[T.titleUpdate(TU,"t1u1",{size:"88"})[0].title.size,
  T.titleUpdate(TU,"t1u1",{size:"abc"})===TU,
  T.titleUpdate(TU,"t1u1",{size:0})===TU];
/* PURETE : ni le tableau, ni le clip, ni son objet `title` ne bougent. */
out.tu_pur=(function(){var av=JSON.stringify(TU);
  T.titleUpdate(TU,"t1u1",{text:"zz",size:99,color:"cyan"});
  return [JSON.stringify(TU)===av,TU.length===2]})();
out.tu_mou=[T.titleUpdate(null,"a",{text:"x"}).length,
  T.titleUpdate("x","a",{text:"x"}).length];
/* LE SOUS-TEXTE EST TRONQUE A 160, comme `MAX_SUB` du backend -- et c'est
   une borne DIFFERENTE de celle du texte : les deux sont mesurees, sinon
   « 120 partout » passerait. */
out.tu_sub_tronque=T.titleUpdate(TU,"t1u1",{sub:new Array(300).join("z")})[0].title.sub.length;
/* LE LIBELLE EST RECALCULE DEPUIS LE TEXTE, y compris quand c'est une AUTRE
   cle qui bouge : le carton porte `label:"Ab"` et un changement de couleur
   ne doit pas le figer sur un premier jet -- ici le texte n'a pas change,
   donc le libelle ne change pas non plus, et c'est ce qu'on mesure. */
out.tu_label_suit=(function(){
  var a=T.titleUpdate(TU,"t1u1",{text:"Abonnez-vous"});
  var b=T.titleUpdate(a,"t1u1",{color:"or"});
  return [a[0].label,b[0].label,TU[0].label]})();
/* LES CLES INCONNUES SONT IGNOREES : un patch qui ne porte que `zzz` ne
   change rien (meme tableau), et un patch mixte n'emporte QUE les cles
   connues -- `zzz` ne se retrouve pas dans le `title` sauvegarde. */
out.tu_cles_inconnues=(function(){
  var a=T.titleUpdate(TU,"t1u1",{zzz:1,id:"autre",start:99})===TU;
  var b=T.titleUpdate(TU,"t1u1",{zzz:1,text:"Neuf"});
  return [a,Object.keys(b[0].title).sort(),b[0].start]})();
/* LA TAILLE EST BORNEE 24..200 ICI AUSSI : `titleUpdate` est PUBLIQUE, et un
   appel venu d'ailleurs aurait ecrit un `size:5000` que la sauvegarde aurait
   garde et que seul le rendu aurait ramene a 200, sans le dire. */
out.tu_taille_bornee=[T.titleUpdate(TU,"t1u1",{size:5000})[0].title.size,
  T.titleUpdate(TU,"t1u1",{size:1})[0].title.size];
/* [12] E-1 : montage neuf */
out.pn_neuf=T.projetNeuf(" Pub été ");
out.pn_neuf_vide=T.projetNeuf("");
out.pn_snap=[T.instantaneNom("",new Date(2026,8,22,14,5)),T.instantaneNom("montage",new Date(2026,8,22,14,5)),T.instantaneNom("Pub",new Date(2026,8,22,14,5))];
/* espaces seuls = pas de nom ; une date INVALIDE (instanceof Date, mais NaN)
   retombe sur maintenant, jamais « NaN/NaN » */
out.pn_snap_mou=[T.instantaneNom("   ",new Date(2026,8,22,14,5)),T.instantaneNom("",new Date(NaN))];
/* les pistes du corps sont des COPIES : muter le corps ne touche pas DEFAULTS */
out.pn_defaults_pur=(function(){var c=T.projetNeuf("x");c.tracks[0].id="zz";c.tracks.push({id:"q"});
  return JSON.stringify(T.DEFAULTS.map(function(t){return t.id}))==='["t1","v2","v1","a1","a2","a3","s1"]'})();
/* [13] E-4 : publier */
var NOW=new Date(2026,8,22,14,7,30);
out.pb_def=T.publishDefaults("Pub été",NOW,null);
out.pb_def_mem=T.publishDefaults("",NOW,["youtube","zzz","x"]);
out.pb_norm=[T.channelsNorm(["zzz"]),T.channelsNorm(null),T.channelsNorm(["instagram","x","x"])];
out.pb_local=T.publishLocal(NOW);
out.pb_iso=typeof T.publishIso("2026-09-22T16:15")==="string"&&/Z$/.test(T.publishIso("2026-09-22T16:15"))&&T.publishIso("")===""&&T.publishIso("zzz")==="";
/* l'arrondi monte au QUART D'HEURE SUIVANT meme quand +2 h tombe pile :
   14:00:00 -> 16:00 (rien a monter) ; 14:00:01 -> 16:15 */
out.pb_local_pile=[T.publishLocal(new Date(2026,8,22,14,0,0)),T.publishLocal(new Date(2026,8,22,14,0,1))];
/* [14] D-13 : le zoom dynamique, cote client */
var DZ1={x0:0,y0:0,w0:1,x1:.2,y1:.2,w1:.6};
out.dz_norm=T.dzNorm(DZ1);
out.dz_norm_clamp=T.dzNorm({x0:.9,y0:-1,w0:.02,x1:5,y1:5,w1:3});
out.dz_norm_vide=[T.dzNorm(null),T.dzNorm({x0:0,y0:0,w0:1,x1:0,y1:0,w1:1}),T.dzNorm({x0:"a"})];
out.dz_at=[T.dzAt(DZ1,0),T.dzAt(DZ1,1),T.dzAt(Object.assign({ease:"lin"},DZ1),.5)];
out.dz_at_doux=T.dzAt(DZ1,.5);
out.dz_preset=[T.dzPreset("in"),T.dzPreset("out"),T.dzPreset("zzz")];
out.dz_move=[T.dzMove(DZ1,1,.5,.5),T.dzMove(DZ1,0,.1,.1)];
out.dz_scale=[T.dzScale(DZ1,1,.3),T.dzScale(DZ1,1,-.9)];
out.dz_css=[T.dzCss(DZ1,0),T.dzCss(DZ1,1),T.dzCss(null,.5)];
out.dz_of=[T.dzOf({dz:DZ1}),T.dzOf({dz:{x0:0,y0:0,w0:1,x1:0,y1:0,w1:1}}),T.dzOf({})];
out.dz_pur=JSON.stringify(DZ1)==='{"x0":0,"y0":0,"w0":1,"x1":0.2,"y1":0.2,"w1":0.6}';
/* les deux composants EXISTENT et rendent null sans clip / sans zoom (r n'est
   pas lu) ; PlanProps avec un clip touche `r` -> le shim strict leve */
out.dz_comp=[typeof T.PlanProps,typeof T.DzRects,T.PlanProps({clip:null}),T.DzRects({dz:null}),
  (function(){try{T.PlanProps({clip:{id:"c",tr:"v1"}});return "rendu"}catch(e){return "leve"}})()];
/* [15] D-15 : interpolation et rampe de vitesse (client) */
out.rt_of=[T.retimeOf({retime:"flow"}),T.retimeOf({retime:"blend"}),T.retimeOf({retime:"nearest"}),T.retimeOf({}),T.retimeOf({retime:9})];
var RC=[{id:"p1",tr:"v1",start:0,end:4,srcIn:1,speed:2,src:{job_id:"j"},transition:"fade",transition_s:.5},{id:"p2",tr:"v1",start:4,end:6,src:{job_id:"j"}}];
var RR=T.rampe(RC,"p1",2,1,4);
out.rt_rampe=RR&&RR.clips.map(function(c){return [c.id===RR.left?"L":c.id===RR.right?"R":c.id,c.start,c.end,c.srcIn,c.speed||1]});
/* la partie droite ne reprend PAS la transition d'entree (elle est au milieu du plan) ; la gauche la garde */
out.rt_rampe_trans=RR&&RR.clips.map(function(c){return c.transition||null});
/* ECART MESURE CONTRE LE PLAN : le plan sondait p2 a t=5, qui est DANS p2 [4,6[ (aucun refus) -- t=7 est hors */
out.rt_rampe_refus=[T.rampe(RC,"p1",0.1,1,2).refus,T.rampe(RC,"p1",3.9,1,2).refus,T.rampe(RC,"zz",2,1,2).refus,T.rampe(RC,"p2",7,1,2).refus];
out.rt_rampe_pur=JSON.stringify(RC[0])==='{"id":"p1","tr":"v1","start":0,"end":4,"srcIn":1,"speed":2,"src":{"job_id":"j"},"transition":"fade","transition_s":0.5}';
/* revue : la vitesse n'est PAS arrondie (« remplir » pose 1,333) -- la gauche garde 1.333, R.srcIn = 1 + 2*1.333 */
var RF=T.rampe([{id:"f1",tr:"v1",start:0,end:4,srcIn:1,speed:1.333,src:{job_id:"j"}}],"f1",2,1.333,2);
out.rt_rampe_fine=RF&&[RF.clips[0].speed,RF.clips[1].srcIn];
/* revue : continuite du zoom au raccord -- la fenetre a t ferme la gauche et ouvre la droite ; sans dz, aucune cle dz */
var RZ=T.rampe([{id:"z1",tr:"v1",start:0,end:4,srcIn:0,dz:{x0:0,y0:0,w0:1,x1:.2,y1:.2,w1:.6,ease:"lin"},src:{job_id:"j"}}],"z1",2,1,2);
out.rt_rampe_dz=RZ&&[RZ.clips[0].dz.w1===RZ.clips[1].dz.w0&&RZ.clips[0].dz.x1===RZ.clips[1].dz.x0,RZ.clips[0].dz.w1,RZ.clips[1].dz.w1,RZ.clips[0].dz.w0,"dz" in RR.clips[0]||"dz" in RR.clips[1]];
/* [16] D-16 : stabilisation, cote client (memes bornes que _v1_stab) */
out.sb_norm=[T.stabNorm({on:true}),T.stabNorm({on:true,smooth:999,crop:"black",zoom:-80}),T.stabNorm({on:false}),T.stabNorm(null),T.stabNorm({on:true,smooth:"x",crop:1,zoom:"7"})];
out.sb_of=[T.stabOf({stab:{on:true,smooth:30}}),T.stabOf({}),T.stabOf({stab:{on:false,smooth:30}})];
out.sb_state=[T.stabState(null),T.stabState({status:"running",progress:40}),T.stabState({status:"done"}),T.stabState({status:"failed",error:"x"}),T.stabState({status:"failed"}),T.stabState({status:"running",progress:"zz"})];
/* purete : l'entree n'est pas mutee ; un entier est rendu (12.6 -> 13) */
var SBI={on:true,smooth:12.6,crop:"black",zoom:3.4};var SBN=T.stabNorm(SBI);
out.sb_pur=[JSON.stringify(SBI)==='{"on":true,"smooth":12.6,"crop":"black","zoom":3.4}',SBN&&SBN.smooth,SBN&&SBN.zoom];
/* [17] D-14 : keyframes d'echelle et d'opacite (client) -- mpLerp2 : lerp sur le SOUS-ENSEMBLE porteur, constante hors bornes, defaut sans porteur */
var KP=[{t:0,x:.5,y:.5,scale:.5},{t:1,x:.6,y:.5},{t:2,x:.7,y:.5,scale:1.5,opacity:.2}];
out.kf_lerp=[T.mpLerp2(KP,1,"scale",1),T.mpLerp2(KP,.5,"scale",1),Math.round(T.mpLerp2(KP,1.5,"x",0)*1000)/1000];
out.kf_lerp_hors=[T.mpLerp2(KP,-3,"scale",1),T.mpLerp2(KP,9,"scale",1),T.mpLerp2(KP,0,"opacity",1),T.mpLerp2(KP,5,"opacity",1)];
out.kf_lerp_defaut=[T.mpLerp2(KP,1,"zz",7),T.mpLerp2([],1,"scale",.3),T.mpLerp2(null,1,"scale",null),T.mpLerp2([{t:0,x:0,y:0,scale:"abc"}],0,"scale",2)];
/* points NON tries et t manquant (0) : meme resultat que tries */
out.kf_lerp_desordre=[T.mpLerp2([{t:2,scale:1.5},{t:0,scale:.5}],1,"scale",1),T.mpLerp2([{scale:.5},{t:2,scale:1.5}],.5,"scale",1)];
/* mpKeep : le patch gagne, sinon le point ecrase, bornes .05..3 / 0..1, arrondi 0,001 / 0,01 ; sans source, aucune cle */
var NP={t:1,x:.5,y:.5,rotate:0},VP={t:1,x:.5,y:.5,rotate:0,scale:9,opacity:.123456},PV={t:1,x:.1,y:.1,scale:.7,opacity:.4};
var K1=T.mpKeep(NP,VP,PV);
out.kf_keep=[K1===NP,K1.scale,K1.opacity,T.mpKeep({t:1},{t:1,x:0},PV).scale,T.mpKeep({t:1},{t:1,x:0},PV).opacity,T.mpKeep({t:1},{scale:-4,opacity:-1},null).scale,T.mpKeep({t:1},{scale:-4,opacity:-1},null).opacity];
var K2=T.mpKeep({t:1,x:.5,y:.5,rotate:0},{t:1,x:.5,y:.5,rotate:0},null),K3=T.mpKeep({t:1},{scale:"zz",opacity:null},{opacity:"x"});
out.kf_keep_absent=["scale" in K2,"opacity" in K2,"scale" in K3,"opacity" in K3,Object.keys(K2).length];
out.kf_pur=[JSON.stringify(KP)==='[{"t":0,"x":0.5,"y":0.5,"scale":0.5},{"t":1,"x":0.6,"y":0.5},{"t":2,"x":0.7,"y":0.5,"scale":1.5,"opacity":0.2}]',JSON.stringify(VP)==='{"t":1,"x":0.5,"y":0.5,"rotate":0,"scale":9,"opacity":0.123456}',JSON.stringify(PV)==='{"t":1,"x":0.1,"y":0.1,"scale":0.7,"opacity":0.4}'];
/* [18] D-9 : la piste d'ajustement (client) -- « j » = cinquieme genre ; `group` prend un OBJET (mesure : dzmGroup(t) lit t.kind/t.id, le plan ecrivait group("j1","adjust") a tort) */
out.aj_kind=[T.kindOf("j1"),T.kindOf("j2","adjust"),T.kindOf("a1"),T.kindOf("t1"),T.kindOf("v1")];
var AJS=T.skin("j1","adjust");
out.aj_skin=[AJS.kind,AJS.type,AJS.id,typeof AJS.h];
var TS0=T.DEFAULTS.map(function(t){return t.id});
var TS1=T.adjustTrack(T.DEFAULTS);
out.aj_track=[TS1.map(function(t){return t.id}),T.adjustTrack(TS1)===TS1,T.adjustTrack([]).map(function(t){return t.id}),T.adjustTrack([{id:"j1"}]).length];
var AJC=[{id:"p",tr:"v1",start:0,end:10}];
out.aj_new=T.adjustNew(2.5,AJC,"j1");
out.aj_new_dur=[T.adjustNew(9,AJC,"j1").end,T.adjustNew(-1,AJC,"j1"),T.adjustNew(1,[],"j1"),T.adjustNew(0,[{id:"j1u1",tr:"j1",kind:"adjust",start:0,end:3}].concat(AJC),"j1").id];
out.aj_group=[T.group({id:"j1",kind:"adjust"}),T.group({id:"t1",kind:"title"}),T.group({id:"v2",kind:"video"}),T.group({id:"a1",kind:"audio"})];
out.aj_pur=[TS0.join()===T.DEFAULTS.map(function(t){return t.id}).join(),TS1.length===T.DEFAULTS.length+1,AJC.length===1&&AJC[0].end===10];
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
                 "tl_grille_existe","tl_global_ne_leve_pas","tl_doublons",
                 # D-12 (revue 21/09) : la section [5b] n'etait couverte par
                 # AUCUNE de ces cles -- la garde de l'etat vide s'arretait
                 # a [5]. Les DIX-HUIT que la sonde ecrit y sont desormais.
                 "vl_loin","vl_milieu","vl_avant","vl_apres","vl_pixel",
                 "vl_blanc","vl_fade","vl_premier","vl_mou","vl_nom_compose",
                 "vl_deux_jonctions","vl_egalite","vl_trou","vl_heritage",
                 "vl_hors_v1","vl_bornes","vl_bord","vl_gel","vl_pur",
                 # D-21 (tache 6) : les VINGT-NEUF cles de la section [6].
                 # Sans elles, la garde de l'etat vide s'arreterait a [5b]
                 # et une section [6] entierement creuse passerait.
                 "tt_defaut","tt_defaut_tete","tt_ensure","tt_ensure_deja",
                 "tt_ensure_identite","tt_ensure_sans_kind","tt_ensure_habillage",
                 "tt_group","tt_pick","tt_pick_sans_kind","tt_pick_absente",
                 "tt_from","tt_new","tt_new_label","tt_new_sans_texte",
                 "tt_new_mous","tt_new_id_unique","tt_new_cles",
                 "tt_new_cles_pleines","tt_at","tt_at_recouvrement","tt_at_mous",
                 "tt_html","tt_html_esc","tt_html_hors","tt_html_mous",
                 "tt_html_gabarit","tt_remove","tt_pur",
                 # D-21 (tache 7) : les NEUF cles de la section [6b].
                 "tu_texte","tu_inchange","tu_tronque","tu_label",
                 "tu_gabarit","tu_vide","tu_taille","tu_pur","tu_mou",
                 "tu_sub_tronque","tu_label_suit","tu_cles_inconnues",
                 "tu_taille_bornee",
                 # D-13 (L3, tache 2) : les DOUZE cles de la section [14].
                 "dz_norm","dz_norm_clamp","dz_norm_vide","dz_at","dz_at_doux",
                 "dz_preset","dz_move","dz_scale","dz_css","dz_of","dz_pur","dz_comp",
                 # D-15 (L3, tache 4) : les CINQ cles de la section [15].
                 "rt_of","rt_rampe","rt_rampe_trans","rt_rampe_refus","rt_rampe_pur",
                 "rt_rampe_fine","rt_rampe_dz",
                 # D-16 (L3, tache 6) : les QUATRE cles de la section [16].
                 "sb_norm","sb_of","sb_state","sb_pur",
                 # D-14 (L3, tache 7) : les SEPT cles de la section [17].
                 "kf_lerp","kf_lerp_hors","kf_lerp_defaut","kf_lerp_desordre",
                 "kf_keep","kf_keep_absent","kf_pur",
                 # D-9 (L3, tache 9) : les SEPT cles de la section [18].
                 "aj_kind","aj_skin","aj_track","aj_new","aj_new_dur","aj_group","aj_pur"]
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

print("\n[5b] D-12 le voile des fondus en direct")
# LOIN DE TOUTE JONCTION : AUCUNE couleur, alpha nul. C'est l'etat VIDE de
# cette section -- sans lui, une fonction qui rendrait toujours `{#000,1}`
# passerait les lignes qui suivent.
check("vl_loin_d_une_jonction_il_n_y_a_pas_de_voile",
      D.get("vl_loin") == {"color": None, "alpha": 0}, D.get("vl_loin"))
# AU RACCORD, LE VOILE EST PLEIN, et il est NOIR parce que la transition du
# clip de DROITE est `fadeblack` -- c'est le clip de droite qui la porte,
# ici comme au rendu ffmpeg.
check("vl_au_raccord_le_voile_noir_est_plein",
      D.get("vl_milieu") == {"color": "#000", "alpha": 1}, D.get("vl_milieu"))
# LA MONTEE ET LA DESCENTE SONT SYMETRIQUES : a une demi-fenetre de part et
# d'autre, la meme moitie. Les deux, pas une : une fonction qui ne
# regarderait que `v >= t0` serait verte sur la seule descente.
check("vl_la_montee_et_la_descente_valent_une_moitie_chacune",
      "vl_avant" in D and "vl_apres" in D
      and D["vl_avant"].get("alpha") == 0.5 and D["vl_apres"].get("alpha") == 0.5,
      f'{D.get("vl_avant")} {D.get("vl_apres")}')
# LES 55 AUTRES NE SE JOUENT PAS EN DIRECT, et la CLE existe quand meme :
# c'est ce qui distingue « mesure faite, zero » de « rien mesure ».
check("vl_une_transition_hors_direct_ne_pose_aucun_voile",
      "vl_pixel" in D and isinstance(D["vl_pixel"], dict)
      and D["vl_pixel"].get("alpha") == 0 and D["vl_pixel"].get("color") is None,
      D.get("vl_pixel"))
check("vl_le_fondu_blanc_pose_un_voile_blanc", D.get("vl_blanc") == "#fff",
      D.get("vl_blanc"))
# LE FONDU SIMPLE N'EST PAS UNE COULEUR : « dim » nomme un MECANISME (baisser
# l'image) que l'appelant traduit ; la fonction ne choisit aucun style.
check("vl_le_fondu_simple_est_un_mecanisme_pas_une_couleur",
      D.get("vl_fade") == {"color": "dim", "alpha": 1}, D.get("vl_fade"))
# LE PREMIER CLIP N'A PAS DE JONCTION : sans voisin gauche EN CONTACT, rien.
# C'est la ligne que la mutation « retirer la garde du voisin gauche » fait
# rougir -- mesuree le 21/09/2026.
check("vl_le_premier_clip_n_a_aucune_jonction_a_fondre",
      "vl_premier" in D and D["vl_premier"].get("alpha") == 0, D.get("vl_premier"))
# A EGALITE, LE PREMIER DU TABLEAU : `>` et non `>=`. La couleur est la
# seule chose qui distingue les deux candidats -- une ligne sur l'alpha
# seul aurait ete vraie des deux cotes.
check("vl_a_egalite_d_alpha_le_premier_du_tableau_garde_la_main",
      D.get("vl_egalite") == {"color": "#000", "alpha": 0.4}, D.get("vl_egalite"))
# LE BORD EXACT : alpha nul, et AUCUNE couleur. Avant la revue, la fonction
# rendait `{"color": "#000", "alpha": 0}` -- un voile noir invisible que
# l'appelant devait demeler. La cle existe : mesure faite, zero.
check("vl_au_bord_exact_de_la_fenetre_il_n_y_a_plus_de_voile",
      D.get("vl_bord") == {"color": None, "alpha": 0}, D.get("vl_bord"))
check("vl_un_trou_de_plus_d_un_dixieme_n_est_pas_une_jonction",
      "vl_trou" in D and D["vl_trou"].get("alpha") == 0, D.get("vl_trou"))
check("vl_les_entrees_molles_rendent_zero_sans_lever",
      D.get("vl_mou") == [0, 0], D.get("vl_mou"))
# LE NOM COMPOSE « <nom> <duree> » est celui que le bundle ecrit depuis
# toujours ; `svmTransBase` garde le premier mot, la couche aussi.
check("vl_un_nom_compose_a_l_ancienne_est_lu_sur_son_premier_mot",
      D.get("vl_nom_compose") == {"color": "#000", "alpha": 1},
      D.get("vl_nom_compose"))
# DEUX JONCTIONS DANS LA MEME FENETRE : le MAXIMUM l'emporte. La couleur le
# prouve -- `#fff` vient de `c` (0,6) et non de `b` (0,2).
check("vl_de_deux_jonctions_proches_la_plus_forte_l_emporte",
      D.get("vl_deux_jonctions") == {"color": "#fff", "alpha": 0.6},
      D.get("vl_deux_jonctions"))
# L'HERITAGE DU PROTOTYPE : sans `hasOwnProperty`, « constructor » rendait
# une FONCTION en guise de couleur.
check("vl_un_nom_herite_du_prototype_ne_pose_aucun_voile",
      D.get("vl_heritage") == [{"color": None, "alpha": 0},
                               {"color": None, "alpha": 0}], D.get("vl_heritage"))
# HORS V1 ET SANS SOURCE : le lecteur vivant ne montre que V1, et un clip
# sans `src` (un TITRE) n'a aucune image a fondre.
check("vl_les_autres_pistes_et_les_clips_sans_source_sont_ignores",
      D.get("vl_hors_v1") == [0, 0], D.get("vl_hors_v1"))
# LES BORNES DE `svmTransS` SONT REPRISES TELLES QUELLES : 9 s ramene a 1
# (a 4,6 la demi-fenetre vaut 0,5 et l'ecart 0,6 : DEHORS, donc zero) et
# 0,01 ramene a 0,1 (a 4,04 il reste 1 - 0,04/0,05 = 0,2).
check("vl_la_duree_est_bornee_comme_dans_le_bundle",
      D.get("vl_bornes") == [0, 0.2], D.get("vl_bornes"))
check("vl_la_table_des_trois_fondus_est_gelee",
      D.get("vl_gel") == ["TypeError", "TypeError", "dim", 3], D.get("vl_gel"))
check("vl_pur", D.get("vl_pur") is True, D.get("vl_pur"))

print("\n[6] D-21 le genre title, la piste t1 et le carton")
# LA PISTE EXISTE, ET ELLE EST EN TETE. Les deux faces : le genre `title`
# (quatrieme genre, ni video ni audio ni subs) et le RANG -- un carton se
# lit par-dessus tout, la bande doit etre la premiere.
check("tt_la_piste_des_titres_est_dans_la_table_des_defauts",
      D.get("tt_defaut") is True and D.get("tt_defaut_tete") == "t1",
      f'defaut={D.get("tt_defaut")!r} tete={D.get("tt_defaut_tete")!r}')
check("tt_la_piste_manquante_est_posee_en_tete",
      D.get("tt_ensure") == ["t1", "v1", "a1"], D.get("tt_ensure"))
# DEJA LA = RIEN DE POSE, et le MEME tableau : l'appelant compare
# l'identite pour ne pas payer un instantane d'historique pour rien.
check("tt_une_piste_deja_la_rend_le_meme_tableau",
      D.get("tt_ensure_deja") == 2 and D.get("tt_ensure_identite") is True
      and D.get("tt_ensure_sans_kind") == 2,
      f'len={D.get("tt_ensure_deja")!r} identite={D.get("tt_ensure_identite")!r} '
      f'sans_kind={D.get("tt_ensure_sans_kind")!r}')
# L'HABILLAGE, SINON UNE BANDE DE 0 PX portant pourtant ses cartons.
check("tt_la_piste_posee_porte_son_habillage",
      D.get("tt_ensure_habillage") == ["t1", "title", "T1", True],
      D.get("tt_ensure_habillage"))
# LE GROUPE DU HAUT : un carton ne peut pas descendre sous V1 par les fleches.
check("tt_le_titre_est_dans_le_groupe_du_haut",
      D.get("tt_group") == [0, 1, 3], D.get("tt_group"))
check("tt_la_piste_se_choisit_par_son_genre",
      D.get("tt_pick") == "t1" and D.get("tt_pick_sans_kind") == "t1"
      and D.get("tt_pick_absente") == "",
      f'pick={D.get("tt_pick")!r} sans_kind={D.get("tt_pick_sans_kind")!r} '
      f'absente={D.get("tt_pick_absente")!r}')
# LA RESTAURATION GARDE LE GENRE, mesure du 21/09/2026 : `svmTracksFrom` ne
# rabat PAS un `kind` inconnu sur « video » -- TT3 n'a donc a replier que la
# piste MANQUANTE, pas le genre.
check("tt_la_restauration_garde_le_genre_title_et_l_habillage",
      D.get("tt_from") == [["t1", "title", 40], ["v1", "video", 54]],
      D.get("tt_from"))
# LE CARTON : piste, genre, bornes (4 s, la duree d'une IMAGE), gabarit,
# texte -- et PAS DE `src`, la cle qui distingue un titre d'un plan.
check("tt_le_carton_neuf_est_un_clip_sans_source",
      D.get("tt_new") == ["t1", "title", 4, 8, "cta", "Abonnez-vous", False],
      D.get("tt_new"))
check("tt_le_libelle_de_la_bande_est_le_texte_tronque",
      D.get("tt_new_label") == "Abonnez-vous a la chaine", D.get("tt_new_label"))
# SANS TEXTE, PAS DE CARTON -- et la cle EXISTE (mesure faite, `null`) :
# c'est ce qui distingue « refus » de « rien mesure ». Meme regle que
# `titles.title_spec` du backend.
check("tt_un_carton_sans_texte_n_est_pas_pose",
      "tt_new_sans_texte" in D and D.get("tt_new_sans_texte") is None,
      D.get("tt_new_sans_texte"))
check("tt_les_entrees_molles_ne_levent_pas",
      D.get("tt_new_mous") == [None, None, 0, 0], D.get("tt_new_mous"))
check("tt_l_identifiant_du_carton_est_unique",
      D.get("tt_new_id_unique") is True, D.get("tt_new_id_unique"))
# AUCUNE SECONDE AUTORITE SUR LES DEFAUTS : ce que l'appelant ne dit pas est
# ABSENT, et c'est `titles.TEMPLATES` qui tranche. Un `size:0` parti d'ici
# aurait donne 24 px (le plancher de `title_spec`) au lieu des 64 du gabarit.
check("tt_les_cles_non_dites_sont_absentes_du_titre",
      D.get("tt_new_cles") == ["text"]
      and D.get("tt_new_cles_pleines") == ["color", "font", "size", "sub",
                                           "template", "text"],
      f'nues={D.get("tt_new_cles")!r} pleines={D.get("tt_new_cles_pleines")!r}')
check("tt_le_carton_sous_la_tete_se_trouve_ou_manque",
      D.get("tt_at") == [True, False], D.get("tt_at"))
# FIN EXCLUE, DEBUT INCLUS, DERNIER DEPART GAGNANT : le carton est NOMME.
check("tt_de_deux_cartons_qui_se_recouvrent_le_dernier_parti_gagne",
      D.get("tt_at_recouvrement") == ["a", "b", "b", None],
      D.get("tt_at_recouvrement"))
check("tt_sans_carton_ni_tete_lisible_il_n_y_a_rien_sous_la_tete",
      D.get("tt_at_mous") == [None, None, None], D.get("tt_at_mous"))
# L'APERCU : la classe porte le gabarit, le texte est ECHAPPE, le sous-texte
# est HORS du bloc du texte.
check("tt_l_apercu_porte_le_gabarit_et_echappe_le_texte",
      isinstance(D.get("tt_html"), str)
      and "&lt;b&gt;Ab" in D["tt_html"]
      and "dzm-tt dzm-tt-tiers_inferieur" in D["tt_html"]
      and "<i>ep</i>" in D["tt_html"]
      and "<b>&lt;b&gt;Ab</b>" in D["tt_html"],
      D.get("tt_html"))
check("tt_les_cinq_caracteres_sont_echappes_l_esperluette_en_premier",
      isinstance(D.get("tt_html_esc"), str)
      and "a&amp;b&lt;c&gt;d&quot;e&#39;f" in D["tt_html_esc"]
      and "&amp;lt;" not in D["tt_html_esc"]
      # l'apostroPHE BRUTE a disparu du corps rendu : la moitie negative,
      # sans quoi la ligne serait verte d'un echappeur qui AJOUTERAIT
      # l'entite sans retirer le caractere.
      and chr(39) not in D["tt_html_esc"], D.get("tt_html_esc"))
# HORS PLAGE : chaine VIDE, que l'appelant ecrit telle quelle. Debut INCLUS,
# fin EXCLUE : la cle du milieu est la seule non vide.
check("tt_hors_de_sa_plage_l_apercu_est_vide",
      isinstance(D.get("tt_html_hors"), list) and len(D.get("tt_html_hors")) == 3
      and D["tt_html_hors"][0] == "" and D["tt_html_hors"][1] != ""
      and D["tt_html_hors"][2] == "", D.get("tt_html_hors"))
check("tt_sans_carton_ni_texte_l_apercu_est_vide",
      D.get("tt_html_mous") == ["", "", ""], D.get("tt_html_mous"))
# UN GABARIT INCONNU N'EST PAS UN GABARIT PAR DEFAUT ECRIT ICI : la classe
# de base seule. Et un nom hostile ne sort pas de l'attribut.
check("tt_un_gabarit_inconnu_ne_rend_que_la_classe_de_base",
      isinstance(D.get("tt_html_gabarit"), list)
      and len(D.get("tt_html_gabarit")) == 2
      and 'class="dzm-tt">' in D["tt_html_gabarit"][0]
      and "dzm-tt-" not in D["tt_html_gabarit"][0]
      and 'class="dzm-tt dzm-tt-aimgsrcx">' in D["tt_html_gabarit"][1]
      and "<img" not in D["tt_html_gabarit"][1], D.get("tt_html_gabarit"))
# t1 SE RETIRE, contrairement a s1 : un montage sans carton n'a pas besoin de
# la bande, et `titleNew` la fait recreer par `titleTrack` au prochain titre.
check("tt_la_piste_des_titres_se_retire_contrairement_a_s1",
      D.get("tt_remove") == 1, D.get("tt_remove"))
check("tt_pur", D.get("tt_pur") is True, D.get("tt_pur"))

print("\n[6b] D-21 regler un carton : titleUpdate")
# LE TABLEAU EST NEUF, le texte et le LIBELLE suivent, le clip voisin est le
# MEME objet (rien n'est recopie pour rien), et l'entree n'a pas bouge.
check("tu_le_texte_change_le_libelle_suit_et_le_voisin_ne_bouge_pas",
      D.get("tu_texte") == [True, "Abonnez-vous", "Abonnez-vous", True, "Ab"],
      D.get("tu_texte"))
# LES SEPT REFUS RENDENT LE MEME TABLEAU : c'est l'IDENTITE qui dit a l'hote
# de ne pas payer de pushHistory. Sans cette ligne, une fonction qui
# recopierait TOUJOURS passerait la precedente.
check("tu_sept_patchs_refuses_rendent_le_meme_tableau",
      D.get("tu_inchange") == [True] * 7, D.get("tu_inchange"))
check("tu_le_texte_est_tronque_a_cent_vingt_et_le_libelle_a_vingt_quatre",
      D.get("tu_tronque") == 120 and D.get("tu_label") == 24,
      f'texte={D.get("tu_tronque")} libelle={D.get("tu_label")}')
# MINUSCULES AVANT L'ASSAINISSEMENT : sans `toLowerCase()`, « Plein_Cadre »
# devenait « lein_adre » — un gabarit qui n'existe pas, remplace en silence
# par le defaut du backend.
check("tu_le_gabarit_passe_en_minuscules_avant_d_etre_assaini",
      D.get("tu_gabarit") == ["plein_cadre", "aimg"],
      D.get("tu_gabarit"))
# LA CHAINE VIDE EFFACE, une valeur pose, et la couche n'est juge de rien :
# « mauve » traverse, c'est `title_spec` qui le remplacera.
check("tu_la_chaine_vide_efface_la_cle_et_la_couche_ne_juge_pas_la_charte",
      D.get("tu_vide") == [["color", "font", "sub", "template", "text"],
                           False, False, "mauve"],
      D.get("tu_vide"))
check("tu_la_taille_est_un_entier_et_refuse_ce_qui_n_en_est_pas_un",
      D.get("tu_taille") == [88, True, True], D.get("tu_taille"))
check("tu_pur", D.get("tu_pur") == [True, True], D.get("tu_pur"))
check("tu_les_entrees_molles_ne_levent_pas",
      D.get("tu_mou") == [0, 0], D.get("tu_mou"))
# M-6 (revue du 22/09/2026) : les trois lignes qui manquaient.
check("tu_le_sous_texte_est_tronque_a_cent_soixante",
      D.get("tu_sub_tronque") == 160, D.get("tu_sub_tronque"))
# LE LIBELLE SUIT LE TEXTE ET RIEN D'AUTRE : il change quand le texte change
# et reste stable quand c'est la couleur qui bouge. Le troisieme element est
# la purete — l'entree garde le sien.
check("tu_le_libelle_suit_le_texte_et_seulement_lui",
      D.get("tu_label_suit") == ["Abonnez-vous", "Abonnez-vous", "Ab"],
      D.get("tu_label_suit"))
# LES CLES INCONNUES SONT IGNOREES : un patch qui n'en porte QUE rend le
# meme tableau, et un patch mixte n'emporte que les cles connues — `zzz`
# n'entre pas dans le `title` sauvegarde, `start` ne bouge pas.
check("tu_les_cles_inconnues_sont_ignorees",
      D.get("tu_cles_inconnues") == [True, ["template", "text"], 0],
      D.get("tu_cles_inconnues"))
# M-1 : les memes bornes que la reglette et que `title_spec`.
check("tu_la_taille_est_bornee_vingt_quatre_deux_cents",
      D.get("tu_taille_bornee") == [200, 24], D.get("tu_taille_bornee"))

print("\n[12] E-1 montage neuf (client)")
check("pn_neuf_porte_nom_vide_et_les_pistes_par_defaut",
      "pn_neuf" in D and D["pn_neuf"].get("name") == "Pub été" and D["pn_neuf"].get("vide") is True
      and [t["id"] for t in D["pn_neuf"].get("tracks", []) if isinstance(t, dict) and "id" in t]
      == ["t1", "v2", "v1", "a1", "a2", "a3", "s1"], D.get("pn_neuf"))
check("pn_neuf_sans_nom_s_appelle_montage_neuf",
      (D.get("pn_neuf_vide") or {}).get("name") == "montage neuf", D.get("pn_neuf_vide"))
# « montage » est le nom par DEFAUT de l'ecran (`nm` de DzmProjects) : il
# n'est pas un nom, la copie de surete est datee comme le vide.
check("pn_instantane_nomme_le_non_nomme_et_garde_un_vrai_nom",
      D.get("pn_snap") == ["(non nommé) 22/09 14:05", "(non nommé) 22/09 14:05", "Pub"], D.get("pn_snap"))
_SNAP = re.compile(r"^\(non nomm\u00e9\) \d\d/\d\d \d\d:\d\d$")
check("pn_instantane_espaces_seuls_et_date_invalide",
      isinstance(D.get("pn_snap_mou"), list) and len(D["pn_snap_mou"]) == 2
      and D["pn_snap_mou"][0] == "(non nomm\u00e9) 22/09 14:05"
      and isinstance(D["pn_snap_mou"][1], str) and _SNAP.match(D["pn_snap_mou"][1]) is not None
      and "NaN" not in D["pn_snap_mou"][1], D.get("pn_snap_mou"))
# DEFAULTS reste intact APRES qu'un corps de projet neuf a ete mute : le
# corps porte des copies, jamais les objets de la constante.
check("pn_defaults_pur_apres_mutation_du_corps", D.get("pn_defaults_pur") is True, D.get("pn_defaults_pur"))

print("\n[13] E-4 publier (client)")
check("pb_defaults_plus_deux_heures_au_quart_d_heure_x_par_defaut_legende_nom",
      D.get("pb_def") == {"channels": ["x"], "run_at": "2026-09-22T16:15", "caption": "Pub été"}, D.get("pb_def"))
check("pb_defaults_reprend_les_canaux_memorises_filtres", (D.get("pb_def_mem") or {}).get("channels") == ["youtube", "x"] and (D.get("pb_def_mem") or {}).get("caption") == "Montage", D.get("pb_def_mem"))
check("pb_norm_liste_blanche_sans_doublon_x_a_defaut", D.get("pb_norm") == [["x"], ["x"], ["instagram", "x"]], D.get("pb_norm"))
check("pb_local_est_la_forme_datetime_local", D.get("pb_local") == "2026-09-22T16:15", D.get("pb_local"))
check("pb_local_pile_ne_monte_pas_une_seconde_monte", D.get("pb_local_pile") == ["2026-09-22T16:00", "2026-09-22T16:15"], D.get("pb_local_pile"))
check("pb_iso_convertit_l_heure_locale_en_utc_z_et_vide_sur_invalide", D.get("pb_iso") is True)

print("\n[14] D-13 zoom dynamique (client)")
check("dz_norm_clampe_et_pose_ease_doux",
      D.get("dz_norm") == {"x0": 0, "y0": 0, "w0": 1, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"}, D.get("dz_norm"))
check("dz_norm_tient_les_memes_bornes_que_le_backend",
      D.get("dz_norm_clamp") == {"x0": 0.9, "y0": 0, "w0": 0.1, "x1": 0, "y1": 0, "w1": 1, "ease": "doux"}, D.get("dz_norm_clamp"))
check("dz_norm_rend_null_pour_vide_plein_cadre_et_invalide",
      "dz_norm_vide" in D and D["dz_norm_vide"] == [None, None, None], D.get("dz_norm_vide"))
check("dz_at_rend_le_rectangle_debut_fin_et_le_milieu_lineaire",
      D.get("dz_at") == [{"x": 0, "y": 0, "w": 1}, {"x": 0.2, "y": 0.2, "w": 0.6}, {"x": 0.1, "y": 0.1, "w": 0.8}], D.get("dz_at"))
check("dz_at_doux_est_la_smoothstep_a_mi_course_egale_au_lineaire",
      D.get("dz_at_doux") == {"x": 0.1, "y": 0.1, "w": 0.8}, D.get("dz_at_doux"))
check("dz_preset_in_zoome_au_centre_out_l_inverse_inconnu_null",
      D.get("dz_preset") == [{"x0": 0, "y0": 0, "w0": 1, "x1": 0.2, "y1": 0.2, "w1": 0.6, "ease": "doux"},
                             {"x0": 0.2, "y0": 0.2, "w0": 0.6, "x1": 0, "y1": 0, "w1": 1, "ease": "doux"}, None], D.get("dz_preset"))
check("dz_move_deplace_un_rectangle_en_restant_dans_le_cadre",
      D.get("dz_move") == [dict(D["dz_norm"], x1=0.4, y1=0.4), D["dz_norm"]] if isinstance(D.get("dz_norm"), dict) else False, D.get("dz_move"))
# faute n6 : `at` ne descend que des listes -- un dict au bout se lit avec un repli
_dzs = lambda i, k: (at("dz_scale", i) if isinstance(at("dz_scale", i), dict) else {}).get(k, -1)
check("dz_scale_change_la_largeur_autour_du_centre_borne_0_1",
      "dz_scale" in D and _dzs(0, "w1") == 0.9 and abs(_dzs(0, "x1") - 0.05) < 1e-9
      and _dzs(1, "w1") == 0.1 and abs(_dzs(1, "x1") - 0.45) < 1e-9, D.get("dz_scale"))
# ECART MESURE (22/09/2026) : le plan attendait `-33.3333%` ET `scale(1.66667)`
# avec UN arrondi a 1e5 -- incoherent (-33.33333 a 1e5). Un seul arrondi, 1e4.
check("dz_css_est_une_translation_puis_une_echelle_origine_0_0",
      D.get("dz_css") == ["translate(0%, 0%) scale(1)", "translate(-33.3333%, -33.3333%) scale(1.6667)", ""], D.get("dz_css"))
check("dz_of_lit_le_clip_et_rend_null_hors_zoom",
      "dz_of" in D and at("dz_of", 0) == D.get("dz_norm") and at("dz_of", 1) is None and at("dz_of", 2) is None, D.get("dz_of"))
check("dz_pur", D.get("dz_pur") is True)
check("dz_composants_existent_et_rendent_null_sans_clip_ni_zoom",
      D.get("dz_comp") == ["function", "function", None, None, "leve"], D.get("dz_comp"))
print("\n[15] D-15 interpolation et rampe (client)")
check("rt_of_ne_rend_que_blend_ou_flow_sinon_null",
      D.get("rt_of") == ["flow", "blend", None, None, None], D.get("rt_of"))
# srcIn de la partie droite = srcIn + (t - start) * ancienne vitesse = 1 + 2*2 = 5 :
# la REGLE DE dzmCarve (`si+(b-s)*sp`), mesuree identique a celle du plan.
check("rt_rampe_fend_a_t_et_pose_les_deux_vitesses_srcin_propage_a_l_ancienne_vitesse",
      D.get("rt_rampe") == [["L", 0, 2, 1, 1], ["R", 2, 4, 5, 4], ["p2", 4, 6, None, 1]], D.get("rt_rampe"))
check("rt_rampe_la_droite_perd_la_transition_la_gauche_la_garde",
      D.get("rt_rampe_trans") == ["fade", None, None], D.get("rt_rampe_trans"))
check("rt_rampe_refuse_les_bords_a_moins_de_0_3_s_l_inconnu_et_le_hors_clip",
      "rt_rampe_refus" in D and D["rt_rampe_refus"] == ["bord", "bord", "clip", "hors"], D.get("rt_rampe_refus"))
check("rt_rampe_pur", D.get("rt_rampe_pur") is True)
# revue : SANS arrondi au centieme -- 1.333 reste 1.333 et srcIn = dzmR3(1 + 2*1.333) = 3.666
check("rt_rampe_ne_rond_pas_la_vitesse_et_srcin_suit_la_vitesse_fine",
      D.get("rt_rampe_fine") == [1.333, 3.666], D.get("rt_rampe_fine"))
# revue : la fenetre a t (lin, u=.5 -> w=.8) ferme la gauche et ouvre la droite ; sans dz, aucune cle dz
check("rt_rampe_garde_le_zoom_continu_au_raccord_et_sans_dz_n_en_pose_pas",
      D.get("rt_rampe_dz") == [True, 0.8, 0.6, 1, False], D.get("rt_rampe_dz"))

print("\n[16] D-16 stabilisation (client)")
check("sb_norm_tient_les_bornes_du_backend_et_rend_null_hors_on",
      D.get("sb_norm") == [{"on": True, "smooth": 15, "crop": "keep", "zoom": 0},
                           {"on": True, "smooth": 100, "crop": "black", "zoom": -30},
                           None, None, {"on": True, "smooth": 15, "crop": "keep", "zoom": 7}], D.get("sb_norm"))
check("sb_of_lit_le_clip",
      "sb_of" in D and D["sb_of"] == [{"on": True, "smooth": 30, "crop": "keep", "zoom": 0}, None, None], D.get("sb_of"))
# un echec sans message dit « ? » ; un progres non numerique dit 0 %
check("sb_state_phrase_les_quatre_etats",
      D.get("sb_state") == ["à analyser", "analyse 40 %", "analysée", "échec : x", "échec : ?", "analyse 0 %"], D.get("sb_state"))
check("sb_norm_pur_et_entier", D.get("sb_pur") == [True, 13, 3], D.get("sb_pur"))

print("\n[17] D-14 keyframes d'echelle et d'opacite (client)")
# le sous-ensemble porteur seul : a t=1 le point sans scale ne pese pas (0.5 -> 1.5 sur [0,2] = 1 a t=1, .75 a t=.5) ; x se lit sur les trois (arrondi : .6+.1*.5 = .6499999 en flottant, comme svmMpLerp)
check("kf_lerp2_interpole_sur_le_sous_ensemble_porteur",
      D.get("kf_lerp") == [1, 0.75, 0.65], D.get("kf_lerp"))
check("kf_lerp2_constante_hors_bornes_du_sous_ensemble",
      D.get("kf_lerp_hors") == [0.5, 1.5, 0.2, 0.2], D.get("kf_lerp_hors"))
check("kf_lerp2_rend_le_defaut_sans_point_porteur_mous_compris",
      "kf_lerp_defaut" in D and D["kf_lerp_defaut"] == [7, 0.3, None, 2], D.get("kf_lerp_defaut"))
check("kf_lerp2_ne_suppose_pas_les_points_tries",
      D.get("kf_lerp_desordre") == [1, 0.75], D.get("kf_lerp_desordre"))
# mpKeep : 9 -> 3 (borne), .123456 -> .12 ; sans patch le point ecrase donne .7/.4 ; -4 -> .05, -1 -> 0
check("kf_keep_reporte_le_patch_sinon_le_point_ecrase_avec_les_bornes_du_backend",
      D.get("kf_keep") == [True, 3, 0.12, 0.7, 0.4, 0.05, 0], D.get("kf_keep"))
check("kf_keep_ne_pose_aucune_cle_sans_source_finie",
      D.get("kf_keep_absent") == [False, False, False, False, 4], D.get("kf_keep_absent"))
check("kf_pur", D.get("kf_pur") == [True, True, True], D.get("kf_pur"))

print("\n[18] D-9 piste d'ajustement (client)")
check("aj_kind_j_est_le_cinquieme_genre",
      D.get("aj_kind") == ["adjust", "adjust", "audio", "title", "video"], D.get("aj_kind"))
check("aj_skin_habille_la_piste",
      "aj_skin" in D and D["aj_skin"] == ["adjust", "ajustement", "j1", "number"], D.get("aj_skin"))
# j1 sous t1 (le haut du groupe des incrustations, dzmTitresAt), idempotent, ["j1"] sur liste vide,
# et une liste restauree qui ne porte que l'id (kindOf lit la lettre) ne recoit pas une seconde j1
check("aj_track_pose_j1_sous_t1_au_dessus_de_v2_idempotent",
      "aj_track" in D and D["aj_track"] == [["t1", "j1", "v2", "v1", "a1", "a2", "a3", "s1"], True, ["j1"], 1], D.get("aj_track"))
check("aj_new_est_un_clip_sans_src_de_3_s_a_la_tete",
      "aj_new" in D and isinstance(D["aj_new"], dict) and D["aj_new"]["tr"] == "j1" and D["aj_new"]["start"] == 2.5
      and D["aj_new"]["end"] == 5.5 and "src" not in D["aj_new"] and D["aj_new"]["kind"] == "adjust"
      and D["aj_new"]["effects"] == [] and D["aj_new"]["label"] == "Ajustement" and D["aj_new"]["id"] == "j1u1", D.get("aj_new"))
# borne par max(end) des clips ; null si t<0 ; null sur une liste vide ; le second clip se nomme j1u2
check("aj_new_est_borne_par_la_fin_de_la_timeline_et_refuse_le_negatif_et_le_vide",
      "aj_new_dur" in D and D["aj_new_dur"] == [10, None, None, "j1u2"], D.get("aj_new_dur"))
check("aj_group_range_l_ajustement_avec_les_titres_et_les_incrustations",
      D.get("aj_group") == [0, 0, 0, 2], D.get("aj_group"))
check("aj_pur", D.get("aj_pur") == [True, True, True], D.get("aj_pur"))
# CE QUE LA NOTE DE RETRAIT PROMET DOIT EXISTER (revue 23/09/2026) : le corps
# de `del()` de l'en-tete de piste promet Maj+J pour j1, comme Maj+T pour t1
# (temoin positif : `title_add` dans le MEME corps). Lu dans la SOURCE.
_SRCd = globals().get("SRC") or ""   # SRC n'existe pas sans node : rougir, pas mourir
_iDel = _SRCd.find("  function del(){")
_iDelF = _SRCd.find("  return r.jsxs(\"div\",{className:\"dzm-hb\",", _iDel) if _iDel >= 0 else -1
_DEL = _SRCd[_iDel:_iDelF] if 0 <= _iDel < _iDelF else ""
check("aj_la_note_de_retrait_de_j1_promet_Maj_J_comme_t1_promet_Maj_T",
      len(_DEL) > 200 and _DEL.count('dzmCombo("title_add","Maj+T")') == 1
      and _DEL.count('dzmCombo("adjust_add","Maj+J")') == 1
      and _DEL.count('kd==="adjust"') == 1 and _DEL.count('kd==="title"') == 1,
      f"corps={len(_DEL)} o title={_DEL.count('title_add')} adjust={_DEL.count('adjust_add')}")
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
