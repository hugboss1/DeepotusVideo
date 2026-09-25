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
/* [19] E-2 (lot E-B, tache 2) : provenance des rendus, chips derivees, filtre du tiroir Medias */
out.prov=[T.provGroupe("seedance"),T.provGroupe("episode"),T.provGroupe("ugc"),T.provGroupe(null),T.provGroupe("zzz")];
out.chips=T.provChips([{provider:"seedance"},{provider:"heygen"},{provider:"episode"},{provider:null},{provider:"zzz"}]);
var MJ=[{title:"Alpha",provider:"seedance"},{title:"Beta",provider:"episode"},{title:"alphabet",provider:"news"}];
out.filtre=T.mediaFiltre(MJ,{groupe:"Studio",q:""}).map(function(j){return j.title});
out.filtre_q=T.mediaFiltre([{title:"Alpha",provider:"seedance"},{title:"Beta",provider:"episode"}],{groupe:"Tout",q:"ALP"}).map(function(j){return j.title});
out.filtre_vide=T.mediaFiltre([],{groupe:"Tout",q:""}).length;
/* bornes : sans filtre -> tout ; q sur le job_id quand le titre manque ; entree non mutee ; chips sans job -> ["Tout"] */
out.filtre_bornes=[T.mediaFiltre(MJ,null).length,T.mediaFiltre([{job_id:"abc123",provider:"news"}],{q:"BC1"}).length,
  T.mediaFiltre([null,{title:"x",provider:"news"}],{groupe:"News"}).length,JSON.stringify(MJ)==='[{"title":"Alpha","provider":"seedance"},{"title":"Beta","provider":"episode"},{"title":"alphabet","provider":"news"}]',
  T.provChips([]),T.provChips(null)];
/* le composant EXISTE et touche `x` (hooks) des l'appel, ferme comme ouvert : la regle des hooks
   de React interdit un `return null` AVANT les useState (le tiroir est monte en permanence par
   l'hote, `open` bascule) -- le shim strict leve donc dans les trois cas, et c'est le temoin
   que ce n'est PAS une fonction pure */
out.drawer_pure=typeof T.MediaDrawer;
out.drawer_touche_x=[!1,null,!0].map(function(o){try{T.MediaDrawer(o===null?null:{open:o});return "rendu"}catch(e){return e instanceof ReferenceError?"leve":"autre:"+e}});
/* E-5 (lot E-B, tache 4) : le dernier rendu FINAL par projet -- store pur {pid:{job_id,name,at}}.
   MESURE 23/09 : `out.fin` est DEJA la cle du mode « fin » de la section [1] (fin_apres_le_dernier) -> prefixe finst */
out.finst=T.finStore({},"p1",{job_id:"j",name:"n",at:1});
out.finst_of=T.finOf(out.finst,"p1");
out.finst_rm=T.finStore(out.finst,"p1",null);
out.finst_none=T.finOf({},"zz");
/* bornes : pid vide -> cle "_" ; store non-objet -> {} ; objet NEUF (l'entree n'est pas mutee) ; finOf lit "_" pour pid vide ;
   store null -> null ; entree sans job_id -> null ; les cles voisines survivent au retrait */
var FS0={p1:{job_id:"j",name:"n",at:1}};
out.finst_bornes=[Object.keys(T.finStore({},"",{job_id:"k",name:"m",at:2})),T.finStore("zut",null,{job_id:"k",name:"m",at:2})["_"].job_id,
  T.finStore(FS0,"p2",{job_id:"z",name:"z",at:3})!==FS0&&Object.keys(FS0).length===1,T.finOf({_:{job_id:"u",name:"",at:0}},""),
  T.finOf(null,"p1"),T.finOf({p1:{}},"p1"),Object.keys(T.finStore({a:{job_id:"1"},b:{job_id:"2"}},"a",null))];
/* E-8 (lot E-B, tache 6) : la largeur de l'inspecteur, bornee 260..480, defaut 300 ; le clamp pur dessous.
   null / "" / undefined / non numerique -> defaut (pas 0 puis borne basse) ; hors bornes -> la borne ; 261 reste 261 */
out.insp=[T.inspW("999"),T.inspW("abc"),T.inspW(261),T.inspW(null),T.inspW(""),T.inspW(void 0),T.inspW(-5),T.inspW(480.4),T.inspW(" 300 ")];
out.clamp=[T.clamp(5,0,10,7),T.clamp(-1,0,10,7),T.clamp(11,0,10,7),T.clamp(NaN,0,10,7),T.clamp(Infinity,0,10,7),T.clamp(-Infinity,0,10,7),
  T.clamp("3",0,10,7),T.clamp(null,0,10,7),T.clamp({},0,10,7),T.clamp(0,0,10,7),T.clamp(10,0,10,7)];
/* E-9 (lot E-B, tache 7, 23/09/2026) : la hauteur de la timeline bornee 30..70 % du total, null sans choix
   (= plafond historique) ; la duree sur le label du clip par le formateur svmRuler DU BUNDLE, que le banc
   EXTRAIT de .bak_montage (jamais recopie) et joue ici -- sans lui, durLbl(...,true) leve et le temoin le dit */
/*E9_RULER*/
out.tlh=[T.tlH("50",1000),T.tlH("900",1000),T.tlH("",1000),T.tlH("500",0),T.tlH(500,1000),T.tlH("650.4",1000)];
out.tlh_bornes=[T.tlH(null,1000),T.tlH(void 0,1000),T.tlH("abc",1000),T.tlH(NaN,1000),T.tlH(Infinity,1000),T.tlH(!0,1000),
  T.tlH("500",-1),T.tlH("500",null),T.tlH("500","abc"),T.tlH("500",Infinity),T.tlH(300,1000),T.tlH(700,1000)];
out.durlbl=(function(){try{return [T.durLbl("a",0,6,true),T.durLbl("a",0,6,false),T.durLbl("a",6,6,true)]}catch(e){return "leve:"+e}})();
out.durlbl_bornes=(function(){try{return [T.durLbl("a",4,2,true),T.durLbl("a",0,65,true),T.durLbl("a",0,6.4,true),T.durLbl("a",0,125,!0),
  T.durLbl("a","0","6",true),T.durLbl("a",0,NaN,true),T.durLbl("a",null,null,true),T.durLbl("",0,6,true)]}catch(e){return "leve:"+e}})();
/* D-7 (lot E-B, tache 8, 23/09/2026) : la mini-carte -- rectangles en FRACTIONS de la duree, une ligne par piste
   dans l'ordre recu, clips hors [0,dur] / a duree nulle / sans piste connue ignores ; le champ piste d'un clip
   est `tr` (mesure : 58 `c.tr` dans .bak_montage, 0 `c.track`) ; le genre par dzmKindOf (id, kind) */
out.mm=T.minimap([{id:"c1",tr:"v1",start:2,end:6},{id:"c2",tr:"a1",start:0,end:20},{id:"c3",tr:"v1",start:25,end:30}],
  [{id:"v1"},{id:"a1",kind:"audio"}],20);
out.mm_vide=[T.minimap([],[],20),T.minimap([{id:"c",tr:"v1",start:0,end:5}],[{id:"v1"}],0),T.minimap([{id:"c",tr:"v1",start:0,end:5}],[{id:"v1"}],-3),
  T.minimap([{id:"c",tr:"v1",start:0,end:5}],[{id:"v1"}],NaN),T.minimap([{id:"c",tr:"v1",start:0,end:5}],[{id:"v1"}],Infinity),
  T.minimap(null,[{id:"v1"}],20),T.minimap([{id:"c",tr:"v1",start:0,end:5}],"v1",20)];
/* bornes : depasse a droite -> x1 borne a 1 ; commence avant 0 -> x0 borne a 0 ; end <= start ignore ; piste inconnue
   ignoree ; clip null ignore ; piste dupliquee = une ligne ; genre par la lettre (a1 -> audio) ; entrees NON mutees */
var _mmC=[{id:"c1",tr:"v1",start:15,end:30},{id:"c2",tr:"v1",start:-5,end:5},{id:"c3",tr:"v1",start:6,end:6},{id:"c4",tr:"zz",start:1,end:2},null,
  {id:"c5",tr:"a1",start:"4","end":"8"}],_mmT=[{id:"v1"},{id:"a1"},{id:"v1"}],_mmJ=JSON.stringify(_mmC)+JSON.stringify(_mmT);
var _mmB=T.minimap(_mmC,_mmT,20);
out.mm_bornes=[_mmB.rows.length,_mmB.rects.map(function(q){return [q.tr,q.row,q.x0,q.x1,q.kind]}),JSON.stringify(_mmC)+JSON.stringify(_mmT)===_mmJ,
  _mmB.rows.map(function(w){return w.kind})];
out.mm_comp=typeof T.Minimap;
/* MESURE 23/09 : `r` est ICI le resultat de la section [1] (`var r=T.insere(...)`, un objet sans jsx) :
   le composant le lit a l'appel et leve un TypeError sur r.jsx -- pas un ReferenceError comme le tiroir (x) */
out.mm_comp_leve=[null,{},{clips:[],tracks:[],dur:0}].map(function(o){try{T.Minimap(o);return "rendu"}catch(e){return e instanceof TypeError&&String(e).indexOf("r.jsx")>=0?"r.jsx":"autre:"+e}});
/* [20] E-6 (lot E-C, tache 1, 23/09/2026) : combo -> touche, modele de menu, DzmCtxMenu */
out.combo=[T.comboToKey("Alt+C"),T.comboToKey("Ctrl+Maj+X"),T.comboToKey("Suppr"),T.comboToKey("Maj+M"),T.comboToKey(""),T.comboToKey("Ctrl+←")];
/* bornes : null / nombre -> null ; Echap, Espace, Entree, Home, End, ? ; Cmd inconnu -> null (revue 23/09 : svmComboCanon ne le
   serialise jamais) ; « Ctrl+ » sans touche finale -> null ; espaces toleres ; = tel quel */
out.combo_bornes=[T.comboToKey(null),T.comboToKey(42),T.comboToKey("Échap"),T.comboToKey("Espace"),T.comboToKey("Entrée"),T.comboToKey("Home"),T.comboToKey("End"),
  T.comboToKey("?"),T.comboToKey("Cmd+K"),T.comboToKey("Ctrl+"),T.comboToKey(" Maj + Z "),T.comboToKey("Ctrl+=")].map(function(k){return k===null?null:[k.key,k.ctrlKey,k.shiftKey,k.altKey,k.metaKey]});
/* TOUTES les combos de la table SVM_ACTIONS du bundle PATCHE, extraites par regex GARDEE (jamais recopiees) : aucune ne rend null,
   chaque resultat porte exactement les cinq cles d'un KeyboardEventInit */
var _ecL=/*EC_COMBOS*/;
out.combo_bundle=[_ecL.length,_ecL.filter(function(c){return T.comboToKey(c)===null}),
  _ecL.filter(function(c){var k=T.comboToKey(c);return !k||Object.keys(k).sort().join()!=="altKey,ctrlKey,key,metaKey,shiftKey"}).length];
out.menu=T.menuModel([{id:"blade",sec:"Montage",lbl:"lame",combo:"Alt+C"},{id:"undo",sec:"Montage",lbl:"annuler",combo:"Ctrl+Z"},{id:"marker_toggle",sec:"Montage",lbl:"marqueur",combo:"Maj+M"},
  {id:"zoom_in",sec:"Affichage",lbl:"zoom",combo:"Ctrl+="},{id:"gain_up",sec:"Audio",lbl:"gain",combo:"Alt+↑"}],
  function(id){return id==="blade"?"Alt+C*":null}).map(function(g){return [g.rub,g.items.map(function(i){return i.id+":"+(i.combo||"")})]});
out.menu_vide=T.menuModel([],null).length;
/* sec inconnue -> Timeline ; ids INCONNUS de la table : sec Audio -> Edition, sec Affichage -> Affichage (les replis de dzmMenuRub,
   revue 23/09) ; entrees non-objets ignorees ; keyLabel qui rend "" (svmKeyLabel du bundle) -> combo de la table ;
   keys_panel -> Aide, fullscreen -> Affichage par la table ; sans lbl ni combo -> chaines vides */
out.menu_inconnu=T.menuModel([{id:"zzz",sec:"Zzz",lbl:"z",combo:"Q"},null,"x",7,{id:"keys_panel",sec:"Affichage",lbl:"k",combo:"?"},{id:"mute",sec:"Audio",lbl:"m",combo:"M"},
  {id:"fullscreen",sec:"Lecture",lbl:"f",combo:"F"},{id:"nolbl",sec:"Montage"},{id:"zza",sec:"Audio",lbl:"za",combo:"1"},
  {id:"zzf",sec:"Affichage",lbl:"zf",combo:"2"}],function(){return ""}).map(function(g){return [g.rub,g.items.map(function(i){return i.id+":"+i.lbl+":"+i.combo})]});
/* actions null / non-tableau -> [] ; sans keyLabel -> combo de la table ; le modele ne MUTE pas l'entree */
var _ecA=[{id:"undo",sec:"Montage",lbl:"a",combo:"Ctrl+Z"}],_ecJ=JSON.stringify(_ecA);
out.menu_bornes=[T.menuModel(null,null).length,T.menuModel("x").length,T.menuModel(_ecA).map(function(g){return g.rub+"/"+g.items[0].combo}),JSON.stringify(_ecA)===_ecJ];
out.ctx_pure=typeof T.CtxMenu;
/* revue 23/09 : le clic ferme TOUJOURS -- `r` (objet de la section [1]) est remplace le temps de l'appel par un jsx factice qui
   rend {t,p} ; le bouton dont run leve appelle quand meme onClose (et releve), le bouton sain appelle run puis onClose */
out.ctx_onclose=(function(){var r0=r,log=[];try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.CtxMenu({items:[{lbl:"boom",run:function(){throw new Error("boom")}},{lbl:"ok",run:function(){log.push("run")}}],onClose:function(){log.push("close")}});
  var btns=m.p.children[0].p.children[1].filter(function(b){return b&&b.t==="button"});
  try{btns[0].p.onClick()}catch(e){log.push("leve:"+e.message)}
  btns[1].p.onClick();return [btns.length,m.t,m.p.className,log]}catch(e){return "autre:"+e}finally{r=r0}})();
/* MESURE : `r` est ici l'objet de la section [1] -> le composant leve sur r.jsx a l'appel, props null / vides / items / rubs */
out.ctx_leve=[null,{},{items:[{lbl:"a",run:function(){}},{sep:!0},{lbl:"b",off:!0}]},{rubs:[{rub:"Projet",items:[{lbl:"b"}]}],x:5,y:5}].map(function(o){try{T.CtxMenu(o);return "rendu"}catch(e){return (e instanceof TypeError||e instanceof ReferenceError)&&String(e).indexOf("r.jsx")>=0?"r.jsx":"autre:"+e}});
/* [22] E-10 (lot E-C, tache 4, 23/09/2026) : la barre ANCREE -- la prop `docked` pose `data-docked:""` sur .dzm-tbar ;
   sans la prop, ou avec une valeur non strictement `true` (motif de `open`/`anim`/`drag`), l'attribut vaut undefined (React ne
   le pose pas). `data-off` reste pose et GARDE SON SENS (l'onglet replie la barre ancree a zero largeur, par la feuille) ;
   l'onglet, lui, ne recoit rien -- il fait la meme chose ancre ou non. Rendu par le jsx factice {t,p}. */
out.tbd=(function(){var r0=r;try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var a=T.ToolBar({open:!0,docked:!0}),b=T.ToolBar({open:!0}),c=T.ToolBar({open:!1,docked:!0}),d=T.ToolBar({open:!0,docked:"1"});
  var ta=T.ToolTab({open:!0,docked:!0});
  return [a.p["data-docked"],b.p["data-docked"],c.p["data-docked"],c.p["data-off"],d.p["data-docked"],"data-docked" in ta.p,
    a.t,a.p.className,a.p.id,b.p["data-off"],ta.p.className,ta.p["aria-expanded"]]}catch(e){return "autre:"+e}finally{r=r0}})();
/* [23] E-13 / E-14 (lot E-C, tache 5, 23/09/2026) : la tete dans l'inspecteur (teteTxt) et le trou selectionne (trou,
   trouRipple). Le formateur est PASSE (l'hote donne svmTcFF) : ici `F` prefixe la valeur brute, la sonde lit le texte.
   Cinq clips : v1 a [0,4[ · c [8,10[ · b [6,8[ (c AVANT b : l'ordre d'entree n'est pas trie), a1 n [0,10[, v2 o [5,9[ */
var _F=function(v){return "F"+v};
var _g=[{tr:"v1",id:"a",start:0,end:4,src:{k:1}},{tr:"v1",id:"c",start:8,end:10,src:{k:3}},{tr:"v1",id:"b",start:6,end:8,src:{k:2}},
  {tr:"a1",id:"n",start:0,end:10,src:{k:4}},{tr:"v2",id:"o",start:5,end:9,src:{k:5}}],_gJ=JSON.stringify(_g);
/* dans le plan (+2), hors (5 > end), a la borne end (4 : hors, l'intervalle est ferme-ouvert), sans sel, au debut (+0) */
out.tete=[T.teteTxt(2,{start:0,end:4},_F),T.teteTxt(5,{start:0,end:4},_F),T.teteTxt(4,{start:0,end:4},_F),T.teteTxt(5,null,_F),T.teteTxt(0,{start:0,end:4},_F)];
/* bornes : ph NaN / undefined / chaine / Infinity -> "" ; fmt absent -> nombre arrondi au centieme ; sel sans bornes numeriques -> comme sans sel */
out.tete_bornes=[T.teteTxt(NaN,null,_F),T.teteTxt(void 0,{start:0,end:4},_F),T.teteTxt("x",null,_F),T.teteTxt(2.456,null),T.teteTxt(2,{start:"a",end:4},_F),T.teteTxt(Infinity,null,_F)];
/* entre a et b (5) ; a la borne end de a (4 : a est ferme-ouvert, 4 est DANS le trou) ; en tete de piste (a=0) ; dans a (2) ;
   en queue (11 : pas de suivant -> null) ; v2 : le trou [0,5[ ignore les clips de v1 ; a1 : dans n ; trou de 0,03 s -> null ; 5.99 */
out.trou=[T.trou(_g,"v1",5),T.trou(_g,"v1",4),T.trou([{tr:"v1",id:"b",start:6,end:8}],"v1",2),T.trou(_g,"v1",2),T.trou(_g,"v1",11),
  T.trou(_g,"v2",2),T.trou(_g,"a1",5),T.trou([{tr:"v1",start:0,end:4},{tr:"v1",start:4.03,end:6}],"v1",4.01),T.trou(_g,"v1",5.99)];
/* bornes : clips null / chaine, t NaN, piste null / inconnue -> null ; entrees non-objets ignorees (le trou reste trouve) */
out.trou_bornes=[T.trou(null,"v1",1),T.trou("x","v1",1),T.trou(_g,"v1",NaN),T.trou(_g,null,5),T.trou(_g,"v9",5),
  T.trou([null,7,{tr:"v1",start:0,end:4},{tr:"v1",start:6,end:8}],"v1",5)];
/* ripple du trou [4,6[ sur v1 : b et c reculent de 2, a reste, n (a1) et o (v2) intacts ; ordre d'entree conserve */
var _rp=T.trouRipple(_g,"v1",4,6);
out.rip=_rp.map(function(c){return [c.id,c.tr,c.start,c.end]});
/* nouveau tableau, entree non mutee, `src` du clip decale conserve par reference (les autres champs sont intacts), le clip
   non decale est LE MEME objet ; bornes b<a, a NaN, b==a -> copie identique (nouvelle reference) ; clips null -> [] */
out.rip_bornes=[_rp!==_g,JSON.stringify(_g)===_gJ,_rp[2].src===_g[2].src&&_rp[2].id==="b",_rp[0]===_g[0],
  JSON.stringify(T.trouRipple(_g,"v1",6,4))===_gJ&&T.trouRipple(_g,"v1",6,4)!==_g,JSON.stringify(T.trouRipple(_g,"v1",NaN,6))===_gJ,
  JSON.stringify(T.trouRipple(_g,"v1",4,4))===_gJ,T.trouRipple(null,"v1",4,6).length];
/* revue T7 (cloture, 23/09/2026) : une AUTRE piste dont un clip commence APRES le trou ne bouge pas (v2 [7,9[ reste) -- dans _g,
   les clips des autres pistes commencent tous AVANT b=6 : une mutation qui retire `c.tr!==tr` du ripple SURVIVAIT sur le comportement */
out.rip_autre=T.trouRipple([{tr:"v1",id:"a",start:0,end:4},{tr:"v2",id:"z",start:7,end:9}],"v1",4,6).map(function(c){return [c.id,c.tr,c.start,c.end]});
/* [21] E-7 (lot E-C, tache 3, 23/09/2026) : le tri des rendus (par TITRE, aucun project_id en base) et la vue Livraison.
   Cinq jobs : deux finals du projet (a, e), un apercu du projet (b), un final d'un AUTRE projet (c), un job non-montage
   au meme titre (d) ; `a` porte une duree (1:05 par svmRuler du bundle, E-9) */
var _jt=[{provider:"montage",title:"preuve e3",job_id:"a",created_at:"2026-09-23T10:00:00",duration_s:65},
  {provider:"montage",title:"preuve e3 (aperçu 480p)",job_id:"b"},
  {provider:"montage",title:"autre projet",job_id:"c"},
  {provider:"seedance",title:"preuve e3",job_id:"d"},
  {provider:"montage",title:"preuve e3",job_id:"e"}];
var _jtJ=JSON.stringify(_jt);
var _t1=T.jobsTri(_jt,"preuve e3");
out.jt=[_t1.finals.map(function(j){return j.job_id}),_t1.previews.map(function(j){return j.job_id})];
var _t2=T.jobsTri(_jt,"");
out.jt_tous=[_t2.finals.map(function(j){return j.job_id}),_t2.previews.map(function(j){return j.job_id})];
out.jt_vide=[T.jobsTri([],"x").finals.length,T.jobsTri([],"x").previews.length];
/* bornes : null / chaine -> vides ; entrees non-objets ignorees (un seul objet montage garde) ; nom null -> tous (3 finals) ;
   le prefixe : « preuve » prend les deux « preuve e3 » (un nom plus court attrape les titres qui le prolongent -- ecart date 23/09,
   l'historique est par titre) et « preuve e3x » ne prend rien */
out.jt_bornes=[T.jobsTri(null,"x").finals.length,T.jobsTri("zz","x").previews.length,
  T.jobsTri([null,"s",7,{provider:"montage",title:"x1"}],"x").finals.length,T.jobsTri(_jt,null).finals.length,
  T.jobsTri(_jt,"preuve").finals.length,T.jobsTri(_jt,"preuve e3x").finals.length];
out.jt_pur=JSON.stringify(_jt)===_jtJ;
out.del_pure=typeof T.Deliver;
/* le composant lit `r` a l'appel (l'objet de la section [1] : TypeError r.jsx), props null / vides / pleines */
out.del_leve=[null,{},{nom:"preuve e3",jobs:_jt,lastFin:{name:"preuve e3",at:1}}].map(function(o){try{T.Deliver(o);return "rendu"}catch(e){return (e instanceof TypeError||e instanceof ReferenceError)&&String(e).indexOf("r.jsx")>=0?"r.jsx":"autre:"+e}});
/* rendu par un jsx factice {t,p} : racine, titre, trois boutons (classe, title present, disabled), ligne « dernier rendu »,
   rangees (finals PUIS apercus, badge, duree du bundle), bouton Bibliotheque ; les clics : Publier grise NE PUBLIE PAS */
out.del_rendu=(function(){var r0=r,log=[];try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.Deliver({nom:"preuve e3",jobs:_jt,publishOn:!1,lastFin:null,onPreview:function(){log.push("preview")},onRender:function(){log.push("render")},onPublish:function(){log.push("publish")},onOpenLib:function(){log.push("lib")}});
  var ch=m.p.children,btns=ch[1].p.children,rows=ch[3].p.children;
  btns[0].p.onClick();btns[1].p.onClick();btns[2].p.onClick();ch[4].p.onClick();
  return [m.t,m.p.className,ch[0].p.children,btns.map(function(b){return [b.p.className,!!b.p.title,!!b.p.disabled]}),ch[2].p.children,
    rows.map(function(w){return [w.p.className,w.p["data-kind"],w.p.children[3].p.children,w.p.children[2].p.children]}),ch[4].p.children,log]}catch(e){return "autre:"+e}finally{r=r0}})();
/* liste vide (aucun job de ce nom) -> svm-delempty ; publishOn -> Publier actif et le clic publie ; dernier rendu nomme (at 0 : sans date) */
out.del_vide_liste=(function(){var r0=r,log=[];try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.Deliver({nom:"zzz",jobs:_jt,publishOn:!0,lastFin:{name:"preuve e3",at:0},onPublish:function(){log.push("publish")}});
  m.p.children[1].p.children[2].p.onClick();
  return [m.p.children[3].p.children.p.className,m.p.children[1].p.children[2].p.disabled,m.p.children[2].p.children,log]}catch(e){return "autre:"+e}finally{r=r0}})();
/* ── [24] L4 (23/09/2026) : reglages de livraison — pastille, options, payload, statut, composant ── */
out.lp=[T.loudPastille(-14,-14),T.loudPastille(-15,-14),T.loudPastille(-15.01,-14),T.loudPastille(-17,-14),T.loudPastille(-17.01,-14),
  T.loudPastille(-13,-14),T.loudPastille(-11,-14),T.loudPastille(-16,null),T.loudPastille(NaN,-14),T.loudPastille(null,-14),T.loudPastille(-16,"x"),T.loudPastille(-16,void 0)];
var _api={builtins:[{id:"master_1080",label:"Master"},{id:"web_4k",label:"4K"}],fps:[24,25,30,60],
  presets:[{id:"maison_a",label:"Mon 4K",base:"web_4k"},{id:"web_4k",label:"doublon"},null,"s",{label:"sans id"},{id:"m2"}]},_apiJ=JSON.stringify(_api);
out.opts=T.deliverOpts(_api).map(function(p){return [p.id,p.label,p.groupe]});
out.opts_bornes=[T.deliverOpts(null).length,T.deliverOpts("x").length,T.deliverOpts({}).length,
  T.deliverOpts({builtins:"zz",presets:[{id:"q"}]}).map(function(p){return p.groupe})];
out.opts_pur=JSON.stringify(_api)===_apiJ;
var _b={name:"n",preview:!1,clips:[]},_bJ=JSON.stringify(_b);
out.pl=T.deliverPayload(_b,{preset:"web_4k",fps:60,loudness:-14,rangeOnly:!0,range:{in:2,out:5},queue:!0});
out.pl_absent=Object.keys(T.deliverPayload(_b,{})).sort();
out.pl_bornes=[T.deliverPayload(_b,{fps:48}).fps,T.deliverPayload(_b,{fps:"60"}).fps,T.deliverPayload(_b,{loudness:"-14"}).loudness,T.deliverPayload(_b,{loudness:-19}).loudness,
  T.deliverPayload(_b,{rangeOnly:!0,range:{in:5,out:2}}).range,T.deliverPayload(_b,{rangeOnly:!1,range:{in:2,out:5}}).range,T.deliverPayload(_b,{preset:""}).preset,
  T.deliverPayload(_b,{queue:!1}).queue,Object.keys(T.deliverPayload(null,null)).length,T.deliverPayload(_b,{fps:null}).fps,T.deliverPayload(_b,{fps:""}).fps];
out.pl_pur=JSON.stringify(_b)===_bJ&&T.deliverPayload(_b,{preset:"x"})!==_b;
out.st=[T.delStatut({status:"queued"}),T.delStatut({status:"generating_video",progress:42.4}),T.delStatut({status:"done"}),T.delStatut({status:"failed"}),
  T.delStatut({status:"zz"}),T.delStatut(null),T.delStatut({status:"generating_video",progress:"x"}),T.delStatut({status:"generating_video",progress:250})];
out.dr_pure=typeof T.DeliverRow;
out.dr_leve=[null,{},{opts:{preset:"web_4k"},api:_api,lufs:{i:-16.2},hasRange:!0}].map(function(o){try{T.DeliverRow(o);return "rendu"}catch(e){return (e instanceof TypeError||e instanceof ReferenceError)&&String(e).indexOf("r.jsx")>=0?"r.jsx":"autre:"+e}});
/* rendu par un jsx factice : la grille, les trois selects (groupes, valeurs, options), la pastille (jaune : |-16,2+14| = 2,2), la case (hasRange), le bouton ; les gestes remontent des PATCHS */
out.dr_rendu=(function(){var r0=r,log=[];try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.DeliverRow({opts:{preset:"maison_a",fps:60,loudness:-14,rangeOnly:!0},api:_api,lufs:{i:-16.2},hasRange:!0,onChange:function(p){log.push(p)},onSavePreset:function(){log.push("save")}});
  var ch=m.p.children,sel=ch[1],fps=ch[3],ld=ch[5].p.children[0],pill=ch[5].p.children[1],rg=ch[6],btn=ch[7];
  sel.p.onChange({target:{value:"web_4k"}});fps.p.onChange({target:{value:""}});ld.p.onChange({target:{value:"-23"}});rg.p.children[0].p.onChange({target:{checked:!1}});btn.p.onClick();
  return [m.t,m.p.className,ch.length,sel.t,sel.p.value,!!sel.p.title,sel.p.children.map(function(g){return g?[g.p.label,g.p.children.map(function(q){return q.p.value})]:null}),
    fps.p.value,fps.p.children.map(function(q){return q.p.children}),ld.p.value,ld.p.children.map(function(q){return q.p.value}),
    pill.p.className,pill.p["data-etat"],pill.p.title,rg.t,rg.p.children[0].p.type,rg.p.children[0].p.checked,!!rg.p.children[0].p.title,btn.p.className,btn.p.children,!!btn.p.title,log]}catch(e){return "autre:"+e}finally{r=r0}})();
/* etat vide : aucun api, aucune mesure, pas de plage -> select preset vide (deux groupes null), pastille grise « mesurez d'abord », pas de case */
out.dr_vide=(function(){var r0=r;try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.DeliverRow({opts:{},api:null,lufs:null,hasRange:!1});var ch=m.p.children,pill=ch[5].p.children[1];
  return [ch[1].p.value,ch[1].p.children,ch[3].p.value,ch[5].p.children[0].p.value,pill.p["data-etat"],pill.p.title,ch[6],ch[7].p.children]}catch(e){return "autre:"+e}finally{r=r0}})();
/* revue T4 : un preset persiste absent des options (maison supprime / api en panne) -> option « (absent) » en tete, valeur gardee */
out.dr_absent=(function(){var r0=r;try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.DeliverRow({opts:{preset:"zz_parti"},api:_api}),s2=m.p.children[1];var m2=T.DeliverRow({opts:{preset:"zz_parti"},api:null}).p.children[1];
  return [s2.p.value,s2.p.children[0].t,s2.p.children[0].p.value,s2.p.children[0].p.children,s2.p.children.length,m2.p.value,m2.p.children[0].p.children,m2.p.children[1]]}catch(e){return "autre:"+e}finally{r=r0}})();
/* le badge de statut de la vue Livraison (DzmDeliver) : cinquieme enfant de la rangee, data-st = statut brut, texte par delStatut */
out.del_st=(function(){var r0=r;try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var js=[{provider:"montage",title:"q",job_id:"a",status:"queued"},{provider:"montage",title:"q",job_id:"b",status:"generating_video",progress:40},
    {provider:"montage",title:"q",job_id:"c",status:"done"},{provider:"montage",title:"q",job_id:"d",status:"failed"},{provider:"montage",title:"q",job_id:"e",status:"zz"}];
  var m=T.Deliver({nom:"q",jobs:js});
  return m.p.children[3].p.children.map(function(w){var b=w.p.children[4];return [w.p.children.length,b.p.className,b.p["data-st"],b.p.children]})}catch(e){return "autre:"+e}finally{r=r0}})();
/* ── [25] L7 D-10 (24/09/2026) : preset Resolve, export/import du mappage ── */
out.kp_resolve=T.kmPreset("resolve");
out.kp_inconnu=[T.kmPreset("avid"),T.kmPreset(null),T.kmPreset(""),T.kmPreset("constructor")];
out.kp_pur=(function(){var a=T.kmPreset("resolve");a.blade="Q";return T.kmPreset("resolve").blade})();
out.kx=T.kmExport({blade:"Ctrl+B"});
out.kx_bornes=[T.kmExport(null),T.kmExport(void 0),T.kmExport("x"),T.kmExport([1])];
var _kA=[{id:"blade",combo:"Alt+C"},{id:"undo",combo:"Ctrl+Z"},{id:"redo",combo:"Ctrl+Y"}],_kC=function(s){return s==="Q"?"":s},_kR=function(s){return s==="Espace"?"raccourci":""};
out.ki_ok=T.kmImport('{"version":1,"keymap":{"blade":"Ctrl+B","zzz":"Q","undo":"Espace","redo":"Ctrl+Y"}}',_kA,_kC,_kR);
out.ki_combo=T.kmImport('{"version":1,"keymap":{"blade":"Q","undo":7}}',_kA,_kC,_kR);
out.ki_casse=T.kmImport("{pas du json",_kA,_kC,_kR);
out.ki_v2=[T.kmImport('{"version":2,"keymap":{}}',_kA,_kC,_kR),T.kmImport('{"keymap":{}}',_kA,_kC,_kR),T.kmImport('{"version":1}',_kA,_kC,_kR),
  T.kmImport('{"version":1,"keymap":[1]}',_kA,_kC,_kR),T.kmImport('null',_kA,_kC,_kR),T.kmImport('"s"',_kA,_kC,_kR)];
out.ki_vide=T.kmImport('{"version":1,"keymap":{}}',null,_kC,_kR);
out.ki_aller_retour=T.kmImport(T.kmExport({blade:"Ctrl+B"}),_kA,_kC,_kR);
/* revue I1 : les collisions -- vol du defaut d'une action NON remappee (range_out:"O" vole toolbar), deux lignes
   sur une meme touche (redo perd contre undo, ordre de TABLE comme svmKmMerge), temoins : blade Ctrl+B libre passe,
   et le preset Resolve (toolbar remappee explicitement) passe sans collision */
var _kT=[{id:"blade",combo:"Alt+C"},{id:"undo",combo:"Ctrl+Z"},{id:"redo",combo:"Ctrl+Y"},{id:"range_out",combo:"U"},{id:"toolbar",combo:"O"},{id:"mute",combo:"M"},{id:"solo",combo:"S"}];
out.ki_vol=T.kmImport('{"version":1,"keymap":{"range_out":"O","undo":"Alt+Q","redo":"Alt+Q","blade":"Ctrl+B"}}',_kT,_kC,_kR);
out.ki_vol_preset=T.kmImport(T.kmExport(T.kmPreset("resolve")),_kT,_kC,_kR);
out.ki_vol_echange=T.kmImport('{"version":1,"keymap":{"mute":"Alt+M","solo":"M"}}',_kT,_kC,_kR);
/* ── [26] L7 D-6 (24/09/2026) : presse-papiers de clips entre projets ── */
var _cc0={id:"v1c4",tr:"v1",label:"x",start:2,end:5,srcIn:1,srcOut:4,src:{job_id:"j"},transition:"fade",transition_s:.4,src_history:[1],gain:-3,effects:[{n:"a"}],hidden:void 0};
out.cc=T.clipCopy(_cc0);
out.cc_pur=(function(){var a=T.clipCopy(_cc0);a.src.job_id="Z";a.effects[0].n="Z";return [_cc0.src.job_id,_cc0.effects[0].n,_cc0.id,_cc0.transition]})();
out.cc_bornes=[T.clipCopy(null),T.clipCopy(void 0),T.clipCopy("x"),T.clipCopy(7),T.clipCopy([1])];
/* les pistes du banc sont dans l'ORDRE DE L'ECRAN (v3 en haut, a1 en bas), comme DZM_DEFAULT_TRACKS */
var _cp=function(cs,pl,o){var r=T.clipPaste(cs,pl,o);return {id:r.id,track:r.track,mode:r.mode,refus:r.refus,note:r.note,start:r.start,v1:sv(r,"v1"),n:(r.clips||[]).length,
  pose:(r.clips||[]).filter(function(k){return k&&r.id!=null&&k.id===r.id})[0]||null}};
out.cp_meme_piste=_cp(C,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"inserer",seq:7});
out.cp_inserer_fend=_cp(C,{v:1,clip:out.cc},{head:2,tracks:TS,mode:"inserer",seq:8});
out.cp_ecraser=_cp(C,{v:1,clip:out.cc},{head:2,tracks:TS,mode:"ecraser",seq:9});
out.cp_piste_absente=_cp(C,{v:1,clip:Object.assign({},out.cc,{tr:"v9"})},{head:10,tracks:TS,mode:"inserer",seq:7});
out.cp_kind_prime=_cp(C,{v:1,clip:Object.assign({},out.cc,{tr:"a1"})},{head:10,tracks:[{id:"x9",kind:"audio"},{id:"v1",kind:"video"}],mode:"inserer",seq:7});
out.cp_genre_absent=_cp(C,{v:1,clip:Object.assign({},out.cc,{tr:"a1"})},{head:10,tracks:[{id:"v2",kind:"video"},{id:"v1",kind:"video"}],mode:"inserer",seq:7});
out.cp_vide=[_cp(C,null,{}),_cp(C,void 0,{}),_cp(C,{v:1},{}),_cp(C,{v:1,clip:null},{}),_cp(C,{v:1,clip:"x"},{}),_cp(C,"x",{})].map(function(r){return [r.refus,r.id,r.n,r.track]});
out.cp_v0=[_cp(C,{v:2,clip:out.cc},{}),_cp(C,{clip:out.cc},{}),_cp(C,{v:"1",clip:out.cc},{})].map(function(r){return [r.refus,r.id,r.n]});
out.cp_verrou=_cp(C,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"inserer",seq:7,locked:{v1:!0}});
out.cp_mou=_cp(null,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"inserer",seq:7});
out.cp_sans_pistes=_cp(C,{v:1,clip:out.cc},{head:10});
out.cp_head=[_cp(C,{v:1,clip:out.cc},{head:-3,tracks:TS,mode:"inserer",seq:1}),_cp(C,{v:1,clip:out.cc},{head:"zz",tracks:TS,mode:"inserer",seq:1}),
  _cp(C,{v:1,clip:out.cc},{head:10.12345,tracks:TS,mode:"inserer",seq:1})].map(function(r){return [r.id,r.v1.filter(function(k){return k[0]===r.id})[0]||null]});
out.cp_len0=_cp(C,{v:1,clip:Object.assign({},out.cc,{start:5,end:5})},{head:10,tracks:TS,mode:"inserer",seq:2});
out.cp_id_pris=_cp(C.concat([{tr:"v1",id:"v1u7_100",start:20,end:21,src:{a:1}}]),{v:1,clip:out.cc},{head:10,tracks:TS,mode:"inserer",seq:7});
out.cp_remplir=_cp(C,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"remplir",seq:3,range:{in:2,out:5}});
out.cp_remplir_srcdur=_cp(C,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"remplir",seq:3,range:{in:2,out:5},srcDur:6});
/* revue : I-2 clip sans source refuse (temoin : un carton title sans src passe), M-2 piste homonyme d'un autre genre
   ignoree (temoin : v2 video la prend), M-1 start = position REELLE (fin -> 8, ripple -> 4, remplir -> 2, inserer -> 10) */
out.cp_sans_source=[_cp(C,{v:1,clip:{tr:"v1",label:"d",start:0,end:3}},{head:10,tracks:TS,mode:"inserer",seq:1}),
  _cp(C,{v:1,clip:{tr:"t1",kind:"title",text:"Bonjour",start:0,end:3}},{head:10,tracks:TS.concat([{id:"t1",kind:"title"}]),mode:"inserer",seq:1}),
  _cp(C,{v:1,clip:{tr:"j1",kind:"adjust",start:0,end:3}},{head:10,tracks:TS.concat([{id:"j1",kind:"adjust"}]),mode:"inserer",seq:1})]
  .map(function(r){return [r.refus,r.id,r.track,r.n,r.note]});
out.cp_homonyme=[_cp(C,{v:1,clip:out.cc},{head:10,tracks:[{id:"v1",kind:"audio"},{id:"v2",kind:"video"}],mode:"inserer",seq:1}),
  _cp(C,{v:1,clip:out.cc},{head:10,tracks:[{id:"v1",kind:"audio"}],mode:"inserer",seq:1})].map(function(r){return [r.refus,r.track,r.id]});
out.cp_start=[_cp(C,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"fin",seq:1}),_cp(C,{v:1,clip:out.cc},{head:5,tracks:TS,mode:"ripple_ecraser",seq:1}),
  _cp(C,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"remplir",seq:1,range:{in:2,out:5}}),_cp(C,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"inserer",seq:1})]
  .map(function(r){return [r.mode,r.start,r.id]});
out.cp_start_refus=[_cp(C,null,{}),_cp(C,{v:1,clip:out.cc},{head:10,tracks:TS,mode:"inserer",seq:7,locked:{v1:!0}})].map(function(r){return r.start});
out.cp_pur=[C.length,C.map(function(c){return c.id}).join(","),out.cc.tr,out.cc.start,out.cc.id];
out.cp_menu=T.menuModel([{id:"copy",sec:"Montage",lbl:"c",combo:"Ctrl+C"},{id:"paste",sec:"Montage",lbl:"p",combo:"Ctrl+V"},{id:"blade",sec:"Montage",lbl:"b",combo:"Alt+C"}],null)
  .map(function(g){return [g.rub,g.items.map(function(i){return i.id}).join(",")]});
/* ── [27] L7 D-8 (24/09/2026) : boring detector — plans trop longs et jump cuts sur V1 ── */
var CLB=[{id:"a",tr:"v1",start:0,end:10,srcIn:0,src:{job_id:"j1"}},{id:"b",tr:"v1",start:10,end:12,srcIn:10.2,src:{job_id:"j1"}},
  {id:"c",tr:"v1",start:12,end:15,srcIn:0,src:{job_id:"j2"}},{id:"d",tr:"a1",start:0,end:30,src:{audio:"x"}}];
var _clb0=JSON.stringify(CLB);
var _bj=function(a,b){return [{id:"a",tr:"v1",start:0,end:2,srcIn:0,src:{job_id:"j"}},Object.assign({id:"b",tr:"v1",start:2,end:4,srcIn:2,src:{job_id:"j"}},a,b||{})]};
out.bo=T.boring(CLB,{maxS:8,minFrames:12,fps:30});
out.bo_defaut=T.boring(CLB);
out.bo_def=T.boringDef;
out.bo_def_pur=(function(){var d=T.boringDef,m=Object.assign({},d);m.maxS=1;var r=T.boring(CLB,m);return [r.a||null,r.b||null,r.c||null,d.maxS,T.boring(CLB).c||null]})();
out.bo_loin=T.boring(CLB,{maxS:8,minFrames:3});
out.bo_vide=[T.boring([]),T.boring(null),T.boring(void 0),T.boring("x"),T.boring([null,7,"x"]),T.boring([{tr:"v1",start:0,end:99}])];
out.bo_long_et_jump=T.boring([{id:"a",tr:"v1",start:0,end:10,srcIn:0,src:{job_id:"j1"}},{id:"b",tr:"v1",start:10,end:20,srcIn:10,src:{job_id:"j1"}}]);
out.bo_egal=T.boring([{id:"a",tr:"v1",start:0,end:8,src:{job_id:"j1"}},{id:"b",tr:"v1",start:8,end:16.001,src:{job_id:"j2"}}]);
/* seuil : 12 images à 30 i/s = 0,4 s — 2.4 est AU seuil (pas un jump, flottant compris), 2.3 est dessous */
out.bo_seuil=[T.boring(_bj({srcIn:2.4})),T.boring(_bj({srcIn:2.3})),T.boring(_bj({srcIn:1.7})),T.boring(_bj({srcIn:1.6}))];
/* contact : la tolérance de dzmVoisins (0,1 s) — 2.1 touche, 2.5 non ; un chevauchement n'est pas un contact */
out.bo_contact=[T.boring(_bj({start:2.1})),T.boring(_bj({start:2.5})),T.boring(_bj({start:1.5,srcIn:1.5}))];
/* sources : deux images identiques en contact = jump (une image n'a pas de position de source), deux images
   différentes non, sans source rien, job et image homonymes ne se confondent pas, audio hors V1 */
out.bo_sources=[T.boring(_bj({src:{image:"i"},srcIn:0},{})).b||null,
  T.boring([{id:"a",tr:"v1",start:0,end:2,src:{image:"i"}},{id:"b",tr:"v1",start:2,end:4,src:{image:"i"}}]),
  T.boring([{id:"a",tr:"v1",start:0,end:2,src:{image:"i"}},{id:"b",tr:"v1",start:2,end:4,src:{image:"k"}}]),
  T.boring([{id:"a",tr:"v1",start:0,end:2},{id:"b",tr:"v1",start:2,end:4}]),
  T.boring([{id:"a",tr:"v1",start:0,end:2,src:{job_id:"j"}},{id:"b",tr:"v1",start:2,end:4,srcIn:2,src:{image:"j"}}]),
  T.boring([{id:"a",tr:"v1",start:0,end:2,src:{}},{id:"b",tr:"v1",start:2,end:4,src:{}}])];
out.bo_v2=[T.boring([{id:"a",tr:"v2",start:0,end:20,srcIn:0,src:{job_id:"j"}},{id:"b",tr:"v2",start:20,end:22,srcIn:20,src:{job_id:"j"}}]),
  T.boring([{id:"a",tr:"v1",start:0,end:2,srcIn:0,src:{job_id:"j"}},{id:"b",tr:"v2",start:2,end:4,srcIn:2,src:{job_id:"j"}}])];
/* vitesse : à ×2, 5 s de timeline consomment 10 s de source — le plan suivant repris à 10 est un jump ; à ×1 non */
out.bo_vitesse=[T.boring([{id:"a",tr:"v1",start:0,end:5,srcIn:0,speed:2,src:{job_id:"j"}},{id:"b",tr:"v1",start:5,end:7,srcIn:10,src:{job_id:"j"}}]),
  T.boring([{id:"a",tr:"v1",start:0,end:5,srcIn:0,src:{job_id:"j"}},{id:"b",tr:"v1",start:5,end:7,srcIn:10,src:{job_id:"j"}}]),
  T.boring([{id:"a",tr:"v1",start:0,end:5,srcIn:0,speed:"zz",src:{job_id:"j"}},{id:"b",tr:"v1",start:5,end:7,srcIn:5,src:{job_id:"j"}}])];
out.bo_desordre=T.boring(CLB.slice().reverse());
out.bo_pur=[JSON.stringify(CLB)===_clb0,CLB.map(function(c){return c.id}).join(",")];
/* options : illisibles, nulles ou négatives → défaut ; maxS 20 ne laisse que le jump ; fps 60 resserre le seuil (12/60 = 0,2 : 10.2 est AU seuil) */
out.bo_opts=[T.boring(CLB,{maxS:"zz"}),T.boring(CLB,{maxS:0}),T.boring(CLB,{maxS:-3,minFrames:null}),T.boring(CLB,{maxS:20}),
  T.boring(CLB,{fps:0}),T.boring(CLB,{minFrames:-1}),T.boring(CLB,{fps:60}),T.boring(CLB,"zz"),T.boring(CLB,7)];
/* ── [28] L7 D-39 (24/09/2026) : comparaison de deux projets — dzmDiff pur + DzmDiffView ── */
var DA=[{id:"1",tr:"v1",start:0,end:5,srcIn:0},{id:"2",tr:"v1",start:5,end:8,srcIn:0,gain:0},{id:"3",tr:"a1",start:0,end:8}];
var DB=[{id:"1",tr:"v1",start:2,end:7,srcIn:0},{id:"2",tr:"v1",start:5,end:9,srcIn:0,gain:-3},{id:"4",tr:"v1",start:9,end:12}];
var _da0=JSON.stringify(DA),_db0=JSON.stringify(DB);
out.df=T.diff(DA,DB);
out.df_id=T.diff(DA,DA);
out.df_vide=[T.diff([],[]),T.diff(null,void 0),T.diff("x",7),T.diff([null,3,{tr:"v1",start:0,end:1}],[{id:"z",tr:"v1",start:0,end:1}])];
/* un slip (srcIn seul) est un rognage de la fenêtre de source, pas un déplacement ; un même clip décalé d'une piste
   à l'autre à durée égale est déplacé ET modifié (tr) ; un clip déplacé sur sa piste n'est pas « modifié » */
out.df_slip=T.diff([{id:"1",tr:"v1",start:0,end:5,srcIn:0}],[{id:"1",tr:"v1",start:0,end:5,srcIn:2}]);
out.df_piste=T.diff([{id:"1",tr:"v1",start:0,end:5}],[{id:"1",tr:"v2",start:3,end:8}]);
out.df_rogne_et_bouge=T.diff([{id:"1",tr:"v1",start:0,end:5,srcIn:0}],[{id:"1",tr:"v1",start:3,end:5,srcIn:3}]);
/* noms : le libellé de B prime, sinon celui de A ; un clip sans libellé n'a pas d'entrée */
out.df_noms=T.diff([{id:"1",tr:"v1",start:0,end:5,label:"Ancien"},{id:"2",tr:"v1",start:5,end:6},{id:"5",tr:"v1",start:6,end:7,label:"Parti"}],
  [{id:"1",tr:"v1",start:0,end:5,label:"Neuf"},{id:"3",tr:"v1",start:5,end:6,label:"Tiers"}]);
/* clés : absent, null et undefined se valent ; 0 n'est pas absent ; effects/dz comparés en profondeur ; une clé hors liste (kind) ne compte pas */
out.df_cles=[T.diff([{id:"1",tr:"v1",start:0,end:5}],[{id:"1",tr:"v1",start:0,end:5,gain:null,effects:void 0}]).changed,
  T.diff([{id:"1",tr:"v1",start:0,end:5}],[{id:"1",tr:"v1",start:0,end:5,gain:0}]).changed,
  T.diff([{id:"1",tr:"v1",start:0,end:5,effects:[{k:"a"}],dz:{p:1}}],[{id:"1",tr:"v1",start:0,end:5,effects:[{k:"b"}],dz:{p:1}}]).changed,
  T.diff([{id:"1",tr:"v1",start:0,end:5,kind:"a"}],[{id:"1",tr:"v1",start:0,end:5,kind:"b"}]).changed,
  T.diff([{id:"1",tr:"v1",start:0,end:5,text:"a",transition:"fade",transition_s:.4,opacity:1}],[{id:"1",tr:"v1",start:0,end:5,text:"b",transition:"wipe",transition_s:.5,opacity:.5}]).changed];
/* revue 24/09 : start/srcIn à la tolérance 1e-6 — un ripple flottant n'est ni déplacé ni rogné ; 1 ms l'est (témoin) */
out.df_tolerance=[T.diff([{id:"1",tr:"v1",start:5,end:8,srcIn:1}],[{id:"1",tr:"v1",start:5+1e-9,end:8+1e-9,srcIn:1+1e-9}]),
  T.diff([{id:"1",tr:"v1",start:5,end:8,srcIn:1}],[{id:"1",tr:"v1",start:5.001,end:8.001,srcIn:1}]),
  T.diff([{id:"1",tr:"v1",start:5,end:8,srcIn:1}],[{id:"1",tr:"v1",start:5,end:8,srcIn:1.001}])];
out.df_pur=[JSON.stringify(DA)===_da0,JSON.stringify(DB)===_db0,DA.length,DB.length];
out.df_temps=[T.diffTemps(0),T.diffTemps(65),T.diffTemps(5.3),T.diffTemps(59.96),T.diffTemps("x"),T.diffTemps(-2)];
/* rendu par un jsx factice {t,p} : racine svm-pop dzm-diff, titre, résumé, cinq rubriques (data-rub, tête, lignes), « Fermer » titré ; le clic ferme */
out.df_vue=(function(){var r0=r,log=[];try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.DiffView({diff:out.df,nomA:"a",nomB:"b",onClose:function(){log.push("close")}});
  var ch=m.p.children,rubs=ch.slice(2,7),btn=ch[7].p.children;btn.p.onClick();
  return [m.t,m.p.className,ch[0].p.children,ch[1].p.children,
    rubs.map(function(w){return [w.t,w.p["data-rub"],w.p.children[0].p.children,w.p.children[1].p.children.map(function(li){return li.p.children})]}),
    [btn.t,btn.p.className,btn.p.title,btn.p.children],log,typeof m.p.onClick]}catch(e){return "autre:"+e}finally{r=r0}})();
/* noms et pluriels : deux ajoutés portent leur libellé, les rubriques vides montrent « — » ; sans props, rien ne lève */
out.df_vue_noms=(function(){var r0=r;try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.DiffView({diff:T.diff([],[{id:"1",tr:"v1",start:0,end:5,label:"Un"},{id:"2",tr:"v1",start:5,end:6}]),nomA:"",nomB:""}),ch=m.p.children;
  var m0=T.DiffView(),ch0=m0.p.children;
  return [ch[1].p.children,ch[2].p.children[1].p.children.map(function(li){return li.p.children}),ch[3].p.children[1].p.children.map(function(li){return li.p.children}),
    ch[0].p.children,m0.p.className,ch0[1].p.children,ch0.length]}catch(e){return "autre:"+e}finally{r=r0}})();
/* ── [29] L7 D-3b (24/09/2026) : les deux secondes de source A/B d'une jonction — dzmAbSecs pur ── */
var AG={id:"g",tr:"v1",start:0,end:3,srcIn:2,src:{job_id:"j1"}},AD={id:"d",tr:"v1",start:3,end:5,srcIn:1,src:{job_id:"j2"}};
var _ag0=JSON.stringify(AG),_ad0=JSON.stringify(AD);
out.ab=T.abSecs(AG,AD);
/* la vitesse du plan GAUCHE étire sa fenêtre de source (2 + 3×2 − 1/30) ; une vitesse illisible ou nulle vaut 1 ; celle du plan droit ne compte pas */
out.ab_vitesse=[T.abSecs(Object.assign({},AG,{speed:2}),AD),T.abSecs(Object.assign({},AG,{speed:"zz"}),AD),T.abSecs(Object.assign({},AG,{speed:0}),AD),
  T.abSecs(AG,Object.assign({},AD,{speed:2}))];
/* sans srcIn : A = durée − 1/30, B = 0 ; un srcIn en chaîne est lu */
out.ab_sans_srcin=[T.abSecs({id:"g",tr:"v1",start:0,end:3,src:{job_id:"j1"}},{id:"d",tr:"v1",start:3,end:5,src:{job_id:"j2"}}),
  T.abSecs(Object.assign({},AG,{srcIn:"2"}),Object.assign({},AD,{srcIn:"1"}))];
/* refus (null) : un des deux absent, image ou audio à gauche ou à droite, sans source, pistes différentes, pas en contact, plan gauche sans durée */
out.ab_refus=[T.abSecs(null,AD),T.abSecs(AG,void 0),T.abSecs(Object.assign({},AG,{src:{image:"x.png"}}),AD),T.abSecs(AG,Object.assign({},AD,{src:{audio:"y.mp3"}})),
  T.abSecs(Object.assign({},AG,{src:null}),AD),T.abSecs(AG,Object.assign({},AD,{tr:"v2"})),T.abSecs(AG,Object.assign({},AD,{start:3.5,end:5})),
  T.abSecs(Object.assign({},AG,{end:0}),AD),T.abSecs("g","d")];
/* contact à la tolérance du roll (0,1 s) : 3.1 passe, 3.11 refuse (témoin) ; un plan droit AVANT le gauche n'est pas une jonction */
out.ab_contact=[T.abSecs(AG,Object.assign({},AD,{start:3.1})),T.abSecs(AG,Object.assign({},AD,{start:3.11})),T.abSecs(AD,AG)];
/* bornes : A ne descend pas sous 0 (plan de 0,02 s), B non plus (srcIn négatif) ; les deux sont arrondies à l'image (1/30) puis au millième */
out.ab_zero=[T.abSecs({id:"g",tr:"v1",start:0,end:.02,srcIn:0,src:{job_id:"j"}},{id:"d",tr:"v1",start:.02,end:2,srcIn:-1,src:{job_id:"j"}}),
  T.abSecs(Object.assign({},AG,{srcIn:2.0104}),Object.assign({},AD,{srcIn:1.0499}))];
out.ab_pur=[JSON.stringify(AG)===_ag0,JSON.stringify(AD)===_ad0];
/* revue 24/09 : ce que le roll a fait — total (k = n), partiel (k < n, dit), nul (refus), signé, entrées molles, 0,5 ms = rien */
out.abd=[T.abRollDit(3,3+10/30,10),T.abRollDit(3,3+4/30,10),T.abRollDit(3,3,10),T.abRollDit(3,3-1/30,-1),T.abRollDit(3,3-1/30,-10),
  T.abRollDit("x",null,3),T.abRollDit(3,3.0005,1),T.abRollDit(3.001,3.334,10)];
/* ── [30] L7 D-19 (24/09/2026) : coins arrondis et ombre d'un overlay — dzmOvExtra pur ── */
var OVX={id:"o",tr:"v2",radius:40,shadow:1,x:.5},_ovx0=JSON.stringify(OVX);
out.ox=T.ovExtra(OVX);
/* bornes : 999 → 200, −1 → 0, 12.6 → 13 (entier), "abc" → 0, chaîne "40" lue, absent → 0 */
out.ox_rayon=[T.ovExtra({radius:999}).radius,T.ovExtra({radius:-1}).radius,T.ovExtra({radius:12.6}).radius,
  T.ovExtra({radius:"abc"}).radius,T.ovExtra({radius:"40"}).radius,T.ovExtra({}).radius];
/* ombre : true / "1" / 2 / .5 → 1 ; 0 / null / .49 / "x" / absent → 0 (la règle du backend : numérique ≥ 0,5) */
out.ox_ombre=[T.ovExtra({shadow:!0}).shadow,T.ovExtra({shadow:"1"}).shadow,T.ovExtra({shadow:2}).shadow,T.ovExtra({shadow:.5}).shadow,
  T.ovExtra({shadow:0}).shadow,T.ovExtra({shadow:null}).shadow,T.ovExtra({shadow:.49}).shadow,T.ovExtra({shadow:"x"}).shadow,T.ovExtra({}).shadow];
/* entrées molles : null, chaîne, nombre → {0,0} ; toujours les deux clés et rien d'autre */
out.ox_mou=[T.ovExtra(null),T.ovExtra("a"),T.ovExtra(7),Object.keys(T.ovExtra(OVX))];
out.ox_pur=JSON.stringify(OVX)===_ovx0;
/* ── [31] L7 D-22 (24/09/2026) : pistes de sous-titres par langue, une seule gravée — subsTracks/subsNew/subsBurn/subsBurnId/subsCopy purs ── */
var TRS=[{id:"v1",kind:"video"},{id:"s1",kind:"subs"},{id:"a1",kind:"audio"}],_trs0=JSON.stringify(TRS);
var CLS=[{id:"v1u1",tr:"v1",start:0,end:5},{id:"s1c1",tr:"s1",start:0,end:1,text:"Salut",label:"Salut"},
  {id:"s1c2",tr:"s1",start:1,end:2.5,text:"Bonjour à tous",label:"Bonjour à tous",hidden:!0,words:[{t:1}]}],_cls0=JSON.stringify(CLS);
out.sst=T.subsTracks(TRS);
/* genre déduit de l'initiale sans kind, kind explicite gagne (x1 subs, s1 vidéo exclue) ; entrées molles */
out.sst_bornes=[T.subsTracks([{id:"s9"},{id:"x1",kind:"subs"},{id:"v1"}]),T.subsTracks(null),T.subsTracks([null,{},{id:"s1",kind:"video"}])];
out.sn=T.subsNew(TRS,"en");
out.sn2=T.subsNew(out.sn.tracks,"de").id;
/* la piste neuve suit la DERNIÈRE piste subs ; sans subs → s1 en fin ; trou d'identifiant : max+1 (s5 → s6) ;
   langue blanche → ni lang ni suffixe ; liste molle → s1 seule */
out.sn_place=[T.subsNew([{id:"v1"},{id:"s1"},{id:"a1"}],"en").tracks.map(function(t){return t.id}),T.subsNew([{id:"v1"}],"en").id,
  T.subsNew([{id:"v1"},{id:"s5",kind:"subs"}],"en").id,T.subsNew(TRS," ").tracks[2],T.subsNew(null,"en").tracks.map(function(t){return t.id})];
out.sb=T.subsBurn(out.sn.tracks,"s2");
/* s1 par défaut : id absent, inconnu, ou d'une piste qui n'est pas de sous-titres */
out.sb_defaut=[T.subsBurn(TRS,null),T.subsBurn(out.sn.tracks,"zz"),T.subsBurn(out.sn.tracks,"v1")].map(function(ts){return ts.map(function(t){return t.id+":"+(t.burn===void 0?"-":t.burn)})});
/* tableau NEUF, pistes hors subs = les MÊMES objets, pistes subs = objets neufs ; la bascule retour ne laisse qu'une gravée */
out.sb_neuf=(function(){var r2=T.subsBurn(out.sn.tracks,"s2");return [r2!==out.sn.tracks,r2[0]===out.sn.tracks[0],r2[1]!==out.sn.tracks[1],r2[3]===out.sn.tracks[3]]})();
out.sb_bascule=T.subsBurn(out.sb,"s1").map(function(t){return t.id+":"+(t.burn===void 0?"-":t.burn)});
/* la piste qui part au rendu : la marquée, sinon s1 (même sans marque, même sans aucune piste subs, même liste molle), sinon la première subs */
out.bid=[T.subsBurnId(out.sb),T.subsBurnId(TRS),T.subsBurnId(out.sn.tracks),T.subsBurnId([{id:"v1"}]),T.subsBurnId(null),
  T.subsBurnId([{id:"v1"},{id:"s3",kind:"subs"}]),T.subsBurnId([{id:"s1",burn:!0},{id:"s2",burn:!0}])];
out.sc=T.subsCopy(CLS,"s1","s2",[{start:0,end:1,text:"Hi"},{start:1,end:2.5,text:"Hello everyone",hidden:!0}]);
/* sans segments : copie des clips de s1 (hidden et words gardés, label gardé), ids s2c1/s2c2 ; les autres clips sont les MÊMES objets */
out.sc_clips=T.subsCopy(CLS,"s1","s2");
out.sc_memes=[out.sc[0]===CLS[0],out.sc[1]===CLS[1],out.sc[2]===CLS[2],out.sc_clips[0]===CLS[0]];
/* ids uniques contre les clips déjà présents (s2c1 pris → s2c1_2) */
out.sc_ids=T.subsCopy(CLS.concat([{id:"s2c1",tr:"s2",start:0,end:1,text:"x"}]),"s1","s2",[{start:0,end:1,text:"Hi"}]).map(function(c){return c.id});
/* bornes : start illisible → ignoré, end ≤ start → start+0,1, null → ignoré, texte absent → "" et label « (vide) », label long tronqué (46) ;
   clips mous → seulement les neufs ; piste cible vide → rien de neuf ; segments [] → rien de neuf ; deTr absente → rien de neuf */
out.sc_bornes=[T.subsCopy(CLS,"s1","s2",[{start:"a",end:1,text:"x"},{start:2,end:1.5,text:"y"},null,{start:3,end:4},
    {start:5,end:6,text:"aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeee"}]).slice(3),
  T.subsCopy(null,"s1","s2",[{start:0,end:1,text:"z"}]),T.subsCopy(CLS,"s1","",[{start:0,end:1,text:"z"}]).length,
  T.subsCopy(CLS,"s1","s2",[]).length,T.subsCopy(CLS,"s7","s2").length];
out.sc_pur=[JSON.stringify(TRS)===_trs0,JSON.stringify(CLS)===_cls0,JSON.stringify(out.sn.tracks.slice(0,2).concat([out.sn.tracks[3]]))===_trs0];
/* retrait : s2 se retire, s1 jamais (même liste rendue) ; le payload porte lang, burn et le nom d'une piste de langue, pas burn:false */
out.rm=T.remove(out.sn.tracks,"s2").map(function(t){return t.id});
out.rm_s1=T.remove(TRS,"s1")===TRS;
out.tp=T.payload({tracks:out.sb});
/* ── [32] L7-B D-42 (24/09/2026) : découper un clip aux changements de plan — dzmCutAt pur ── */
var CA=[{tr:"v1",id:"p",start:2,end:12,srcIn:1,src:{job_id:"j"},transition:"fade",transition_s:.5,label:"P"},
  {tr:"a1",id:"n",start:0,end:12,src:{a:1}}],_ca0=JSON.stringify(CA);
function ca(res){return (res&&res.clips||[]).map(function(c){return [c.id,c.tr,c.start,c.end,c.srcIn==null?null:c.srcIn,c.transition,c.transition_s]})}
var ca3=T.cutAt(CA,"p",[3,6,8],{});
out.ca=[ca(ca3),ca3.n,ca3.refus,ca3.note];
/* vitesse ×2 : t (secondes de SOURCE depuis srcIn) → timeline start + t/2 ; srcIn = srcIn + t */
var ca2=T.cutAt([Object.assign({},CA[0],{speed:2})],"p",[4,8],{});
out.ca_vitesse=[ca(ca2),ca2.n];
/* deux coupes à moins de 0,1 s (4,96 et 5,04 : écart 0,08 ≥ 0,05) : même base d'identifiant (p_b50), ids uniques quand même */
out.ca_ids=ca(T.cutAt(CA,"p",[2.96,3.04],{})).map(function(q){return q[0]});
/* revue 24/09 : écart minimal 0,05 s entre candidates successives (chaîne) — 7 ; 7,001 ; 7,04 ; 7,06 → UNE coupe ; témoin 7 ; 7,1 → deux */
out.ca_ecart=[T.cutAt(CA,"p",[5,5.001,5.04,5.06],{}).n,ca(T.cutAt(CA,"p",[5.06,5,5.04,5.001],{})).map(function(q){return q[3]}),
  T.cutAt(CA,"p",[5,5.1],{}).n,ca(T.cutAt(CA,"p",[5,5.1],{})).map(function(q){return q[3]})];
out.ca_ids_pris=ca(T.cutAt(CA.concat([{tr:"v2",id:"p_b50",start:0,end:1}]),"p",[3],{})).map(function(q){return q[0]});
/* bords : à moins de 0,05 s du début ou de la fin → ignorées ; doublon, négatif, illisible, au-delà → ignorés ; non trié → trié */
var cab=T.cutAt(CA,"p",[.02,9.97,5,5,-1,"x",null,20,1],{});
out.ca_bords=[ca(cab).map(function(q){return [q[0],q[2],q[3]]}),cab.n];
/* refus : clip absent, piste verrouillée (celle du clip ; une autre piste verrouillée ne gêne pas), aucune coupe utilisable, times illisible */
var r1=T.cutAt(CA,"zz",[3],{}),r2=T.cutAt(CA,"p",[3],{locked:{v1:!0}}),r3=T.cutAt(CA,"p",[3],{locked:{a1:!0}}),
  r4=T.cutAt(CA,"p",[.01,9.99],{}),r5=T.cutAt(CA,"p",null,null),r6=T.cutAt(null,"p",[3],{});
out.ca_refus=[[r1.refus,r1.n,ca(r1).length,r1.note],[r2.refus,r2.n,ca(r2).length,r2.note],[r3.refus,r3.n,ca(r3).length],
  [r4.refus,r4.n,r4.note],[r5.refus,r5.n],[r6.refus,r6.n,ca(r6).length]];
/* une seule coupe : « 1 coupe » (singulier) ; le clip sans srcIn (mais avec src) démarre à 0 ; un clip SANS src ne gagne pas de srcIn */
var c1=T.cutAt([{tr:"v1",id:"q",start:0,end:4,src:{job_id:"k"}}],"q",[2],{});
out.ca_un=[ca(c1),c1.note];
out.ca_sans_src=ca(T.cutAt([{tr:"v1",id:"q",start:0,end:4}],"q",[2],{}));
/* la moitié droite garde les autres champs du clip (label, src, fx) — comme la lame */
out.ca_champs=(function(){var o=T.cutAt([Object.assign({},CA[0],{fx:["x"]})],"p",[3],{}).clips[1];return [o.label,o.src,o.fx]})();
out.ca_pur=[JSON.stringify(CA)===_ca0,T.cutAt(CA,"p",[3],{}).clips!==CA,T.cutAt(CA,"p",[3],{}).clips[2]===CA[1]];
/* ── [33] L7-B D-34 (24/09/2026) : la note étoile d'un rendu — dzmRatingNorm / dzmRatingNext purs ── */
out.rn=[T.ratingNorm(0),T.ratingNorm(3),T.ratingNorm(5),T.ratingNorm(6),T.ratingNorm(-1),T.ratingNorm("3"),T.ratingNorm(3.5),
  T.ratingNorm(!0),T.ratingNorm(null),T.ratingNorm(void 0),T.ratingNorm(NaN),T.ratingNorm(3.0)];
/* l'étoile cliquée devient la note ; l'étoile COURANTE la retire (0) ; une note serveur illisible est lue 0 */
out.rx=[T.ratingNext(0,3),T.ratingNext(3,3),T.ratingNext(3,5),T.ratingNext(5,1),T.ratingNext(1,1),T.ratingNext(null,4),T.ratingNext("3",3)];
/* clic illisible (0, 6, "2", null) : la note courante, normalisée (9 → 0) */
out.rx_bornes=[T.ratingNext(3,0),T.ratingNext(3,6),T.ratingNext(3,"2"),T.ratingNext(3,null),T.ratingNext(9,9),T.ratingNext(9,2)];
/* une suite de clics sur la même ligne : 0 -3→ 3 -3→ 0 -5→ 5 -2→ 2 -2→ 0 */
out.rx_suite=(function(){var v=0,s=[];[3,3,5,2,2].forEach(function(c){v=T.ratingNext(v,c);s.push(v)});return s})();
/* les chips du tiroir : deux seuils, 3 puis 5, chacune avec un titre */
out.rchips=typeof DZM_NOTE_CHIPS==="undefined"?null:DZM_NOTE_CHIPS.map(function(n){return [n[0],n[1],typeof n[2]==="string"&&n[2].length>10]});
/* ── [34] L7-B D-40 (24/09/2026) : le cadrage d'un clip V1 — dzmReframeOf / At / K / Pos / Css purs ── */
var RB={tr:"v1",id:"r",start:2,end:6,srcIn:1};
function rof(rf,extra){return T.reframeOf(Object.assign({},RB,extra||{},{reframe:rf}))}
function rfR6(v){return typeof v==="number"?Math.round(v*1e6)/1e6:v}
/* centre, inconnu, illisible -> null ; manuel borné, chaîne numérique lue, booléen / vide / base 16 / absent -> null */
out.rf_modes=[rof({mode:"centre"}),rof({mode:"zzz"}),rof(null),rof("suivi"),rof([1,2]),rof({mode:"manuel",x:.3}),
  rof({mode:"manuel",x:1.7}),rof({mode:"manuel",x:-2}),rof({mode:"manuel",x:" 0.25 "}),rof({mode:"manuel",x:!0}),
  rof({mode:"manuel"}),rof({mode:"manuel",x:"0x1"}),rof({mode:"manuel",x:""}),rof({mode:"manuel",x:NaN}),
  T.reframeOf({tr:"v1"}),T.reframeOf(null)];
/* suivi : t borné à [0, (end−start)×vitesse = 4], x à [0,1], illisibles ignorés, tri stable, doublons à 5 ms (le dernier gagne) */
out.rf_suivi=rof({mode:"suivi",points:[{t:5,x:.9},{t:-1,x:.2},[2,1.5],{t:"x",x:.5},{t:1,x:null},{t:1.0001,x:.4},
  {t:1.003,x:.45},[1,2,3],{t:9,x:.7},"z",null]});
/* vitesse (la lecture de _v1_speed, e09552b) : ×2 -> dur 8 ; 10 -> bornée 4 (dur 16) ; 0 -> ×1 (dur 4) ; "2" lue ; sans start -> t borné à 0 seulement ;
   0,1 -> 0,25 (dur 1) ; "inf" et Infinity -> 4 ; vrai -> 1 ; "nan", base 16, négatif -> 1 */
out.rf_vitesse=[{speed:2},{speed:10},{speed:0},{speed:"2"},{start:null},{speed:.1},{speed:"inf"},{speed:Infinity},{speed:!0},{speed:"nan"},{speed:"0x2"},{speed:-3}].map(function(e){
  var q=rof({mode:"suivi",points:[{t:7,x:.5}]},e);return q&&q.points[0].t});
/* au plus 240 points, sous-échantillonnés régulièrement (500 -> 240 : premier, dernier, index 2 au second) */
out.rf_cap=(function(){var m=[],i;for(i=0;i<500;i++)m.push({t:i/100,x:(i%10)/10});
  var q=T.reframeOf({tr:"v1",start:0,end:10,reframe:{mode:"suivi",points:m}});return [q.points.length,q.points[0].t,q.points[239].t,q.points[1].t]})();
/* l'arrondi du millième est celui de round(t, 3) du backend : valeur exacte du flottant, demi exact au pair */
out.rf_r3=[.0045,.0625,.1875,.0055,1.0005,2.0625,.3125].map(function(v){return rof({mode:"suivi",points:[{t:v,x:.5}]},{srcIn:0}).points[0].t});
/* revue finale du lot (24/09/2026) : points ABSOLUS de source, srcIn COURANT soustrait — les QUATRE gestes qui
   avancent srcIn en copiant le champ gardent le bon cadrage sur le morceau droit. Plan [0,10] srcIn 0 suivi
   0,2 -> 0,8 ; la découpe aux plans (cutAt, couche) et la coupe ripple (rippleCut, couche) EXÉCUTÉES ; la
   lame et le rognage de tête vivent dans le bundle (banc bundle, sous node). */
var RG={tr:"v1",id:"g",start:0,end:10,srcIn:0,src:{job_id:"j"},reframe:{mode:"suivi",points:[{t:0,x:.2},{t:10,x:.8}]}};
function rfPts(c){var q=T.reframeOf(c);return q&&q.points.map(function(z){return [z.t,rfR6(z.x)]})}
out.rf_gestes=(function(){var ca=T.cutAt([RG],"g",[5],{}),rc=T.rippleCut([RG],2,3,{});
  var d1=ca.clips.filter(function(k){return k.start===5})[0],d2=rc.clips.filter(function(k){return k.start===2})[0];
  return [ca.n,rfPts(ca.clips[0]),d1&&d1.srcIn,d1&&rfPts(d1),d2&&d2.srcIn,d2&&rfPts(d2)]})();
/* la fenêtre : points de BORD interpolés, tout avant / tout après, sans fin lisible (bornée à gauche seulement) */
out.rf_fenetre=[rfPts({start:0,end:2,srcIn:5,reframe:{mode:"suivi",points:[{t:4,x:.2},{t:6,x:.4},{t:8,x:.8}]}}),
  rfPts({start:0,end:2,srcIn:5,reframe:{mode:"suivi",points:[{t:5,x:.2},{t:7,x:.8}]}}),
  rfPts({start:0,end:2,srcIn:5,reframe:{mode:"suivi",points:[{t:1,x:.2},{t:2,x:.9}]}}),
  rfPts({start:0,end:2,srcIn:5,reframe:{mode:"suivi",points:[{t:10,x:.2},{t:12,x:.9}]}}),
  rfPts({start:0,srcIn:5,reframe:{mode:"suivi",points:[{t:4,x:.2},{t:9,x:.7}]}})];
/* le payload : points ABSOLUS lisibles du champ en suivi, {mode, x} en manuel, rien au centre */
out.rf_payload=[T.reframePayload({start:0,end:2,srcIn:5,reframe:{mode:"suivi",points:[{t:4,x:1.4},"z",[6,.4]]}}),
  T.reframePayload({start:0,end:2,reframe:{mode:"manuel",x:.3,points:[{t:0,x:.1}]}}),
  T.reframePayload({start:0,end:2,reframe:{mode:"centre",points:[{t:0,x:.1}]}}),
  T.reframePayload({start:0,end:2,reframe:{mode:"suivi",points:["z"]}})];
out.rf_vide=[rof({mode:"suivi",points:[]}),rof({mode:"suivi",points:[{t:"a",x:1}]}),rof({mode:"suivi"}),rof({mode:"suivi",points:{t:1,x:.5}})];
/* x à l'instant t (secondes de source) : constante avant/après, lerp entre ; manuel ; sans cadrage 0,5 */
var RA={mode:"suivi",points:[{t:1,x:.2},{t:3,x:.6}]};
out.rf_at=[0,1,2,2.5,3,9].map(function(t){return rfR6(T.reframeAt(RA,t))}).concat([T.reframeAt({mode:"manuel",x:.7},5),
  T.reframeAt(null,2),rfR6(T.reframeAt(RA,NaN)),T.reframeAt({mode:"suivi",points:[]},1)]);
/* largeur relative de la source : 16:9 dans 9:16, 9:16 dans 16:9, même ratio, mesures manquantes */
out.rf_k=[T.reframeK(1920,1080,9/16),T.reframeK(1080,1920,16/9),T.reframeK(1920,1080,16/9),T.reframeK(0,1080,1),
  T.reframeK(1920,1080,0),T.reframeK(null,1,1)].map(function(v){return v===null?null:Math.round(v*1e4)/1e4});
/* position de l'aperçu : (k·x − ½)/(k − 1) bornée ; k ≤ 1,001 (un pixel sur 1080, _reframe_utile) ou inconnu -> null ; 1,005 agit déjà */
out.rf_pos=[[.5,3],[0,3],[1,3],[.3,3],[.5,1],[.5,1.0005],[.5,null],[.9,2],["x",3],[.9,1.005]].map(function(a){return rfR6(T.reframePos(a[0],a[1]))});
/* la chaîne de l'aperçu vivant : manuel 0,3 sur 16:9 -> 9:16 ; sans cadrage, portrait sur paysage, cadre ou source non mesurés -> "" */
var RCM=Object.assign({},RB,{reframe:{mode:"manuel",x:.3}});
out.rf_css=[T.reframeCss(RCM,1,1920,1080,540,960),T.reframeCss(RB,1,1920,1080,540,960),T.reframeCss(RCM,1,1080,1920,960,540),
  T.reframeCss(RCM,1,1920,1080,0,0),T.reframeCss(RCM,1,0,0,540,960),
  T.reframeCss(Object.assign({},RB,{reframe:{mode:"suivi",points:[{t:0,x:0},{t:4,x:1}]}}),2,1920,1080,540,960),
  T.reframeCss(Object.assign({},RB,{reframe:{mode:"centre",points:[{t:0,x:0}]}}),2,1920,1080,540,960)];
/* pur : l'entrée n'est pas touchée, les points rendus sont des objets neufs */
/* revue 24/09 : « Remplacer la source » retire les points du suivi (ils décrivent l'ANCIENNE source), garde
   centré / manuel (x), un suivi redevient centré ; la note le dit — témoin : sans points, clip et note inchangés */
out.rf_remplace=(function(){var S={job_id:"n"},base={tr:"v1",id:"r",start:0,end:4,srcIn:0,src:{job_id:"o"},label:"A"},P2=[{t:0,x:.2},{t:4,x:.6}];
  function go(rf){var q=T.replaceSrc(Object.assign({},base,rf===void 0?{}:{reframe:rf}),S,"B",20,1);
    return [q.clip.reframe===void 0?null:q.clip.reframe,q.note.indexOf("suivi du mouvement de l'ancienne source est retiré")>0,q.note.indexOf("(cadrage centré)")>0]}
  return [go({mode:"suivi",points:P2}),go({mode:"manuel",x:.3,points:P2}),go({mode:"centre",points:P2}),go({mode:"manuel",x:.3}),go(void 0)]})();
out.rf_pur=(function(){var P0={mode:"suivi",points:[{t:5,x:.9},{t:1,x:2}]},C0=Object.assign({},RB,{reframe:P0}),j=JSON.stringify(C0);
  var q=T.reframeOf(C0);return [JSON.stringify(C0)===j,q.points!==P0.points,q.points[0]!==P0.points[1],q.points[1].t]})();
/* ── [35] L7-B D-41 (24/09/2026) : les auto-clips d'un rendu — dzmAcPayload et ses formateurs purs ── */
var AS={job_id:"j1"},AK=T.acCle(AS),EOK={ok:!0,usd:.05,eta_s:40,provider:"elevenlabs",label:"ElevenLabs",pour:AK};
/* la clé d'une source : chaîne telle quelle, objet en JSON (ordre des clés gardé), vide pour rien */
out.ac_cle=[T.acCle(AS),T.acCle("p/x.mp4"),T.acCle(null),T.acCle(""),T.acCle({b:1,a:2})];
/* n : entier 1..8 arrondi, 4 pour l'illisible (vide, texte, booléen, null, NaN, infini) */
out.ac_n=[T.acNum(3),T.acNum("5"),T.acNum(" 2 "),T.acNum(0),T.acNum(9),T.acNum(3.6),T.acNum(""),T.acNum("abc"),T.acNum(!0),
  T.acNum(null),T.acNum(NaN),T.acNum(Infinity),T.acNum(-4)];
/* sans rien : n 4, llm vrai, pas de texte, pas de persona, JAMAIS confirm */
out.ac_base=T.acPayload({src:AS});
/* llm : seul false l'éteint (0, absent -> vrai) */
out.ac_llm=[T.acPayload({src:AS,llm:!1}).llm,T.acPayload({src:AS,llm:0}).llm,T.acPayload({src:AS,llm:void 0}).llm];
out.ac_text=[T.acPayload({src:AS,text:"  bonjour  "}).text,"text" in T.acPayload({src:AS,text:"   "}),"text" in T.acPayload({src:AS,text:5})];
out.ac_persona=[T.acPayload({src:AS,persona:" gamer "}).persona,T.acPayload({src:AS,persona:new Array(80).join("a")}).persona.length,
  "persona" in T.acPayload({src:AS,persona:""})];
/* LA RÈGLE DE LA DÉPENSE (revue T6) : confirm seulement si la coche porte sur l'estimation AFFICHÉE (même objet),
   ok, pour CETTE source, coût lisible ≥ 0, et sans texte ; un booléen ou une copie de l'estimation ne suffisent plus */
function acf(e){var q=T.acPayload(Object.assign({src:AS},e));return q.confirm===void 0?0:q.confirm}
function acv(d){var v=Object.assign({},EOK,d);return {payer:v,vu:v}}
out.ac_confirm=[acf({payer:EOK,vu:EOK}),acf({payer:!0,vu:EOK}),acf({payer:Object.assign({},EOK),vu:EOK}),acf({payer:null,vu:EOK}),
  acf({payer:EOK}),acf(acv({ok:!1})),acf(acv({ok:"true"})),acf(acv({pour:'{"job_id":"autre"}'})),acf(acv({pour:void 0})),
  acf(acv({usd:"0.05"})),acf(acv({usd:-1})),acf(acv({usd:NaN})),acf({payer:EOK,vu:EOK,text:"le texte"}),acf({payer:EOK,vu:EOK,text:"   "})];
/* le plafond : max_usd = le coût de l'estimation cochée, et seulement avec confirm */
out.ac_max=[T.acPayload({src:AS,payer:EOK,vu:EOK}).max_usd,"max_usd" in T.acPayload({src:AS,payer:!0,vu:EOK}),
  T.acPayload(Object.assign({src:AS},acv({usd:0}))).max_usd];
/* la langue : fr, en, es, de, it ; tout le reste (majuscules, absent, inconnu) -> fr */
out.ac_lang=["en","it","de","es","xx","EN",null,void 0,5].map(function(l){return T.acPayload({src:AS,lang:l}).lang});
out.ac_src=[T.acPayload({}),T.acPayload(null),T.acPayload({src:[1]}),T.acPayload({src:5}),T.acPayload({src:""}),T.acPayload({src:"p.mp4"}).src];
out.ac_pur=(function(){var E0={src:AS,text:" t ",n:"3",persona:" p ",llm:!1,lang:"de",payer:EOK,vu:EOK},j=JSON.stringify(E0),q=T.acPayload(E0);
  return [JSON.stringify(E0)===j,q.src===AS,q!==E0,Object.keys(q).sort(),q.n]})();
out.ac_usd=[T.acUsd(.05),T.acUsd(.0067),T.acUsd(0),T.acUsd(1.234),T.acUsd(-1),T.acUsd("1"),T.acUsd(NaN)];
out.ac_est=[T.acEstTxt(EOK),T.acEstTxt({ok:!0,usd:.4,eta_s:300,provider:"openai"}),T.acEstTxt({ok:!1,reason:"Aucune clé"}),
  T.acEstTxt({ok:!1}),T.acEstTxt(null),T.acEstTxt({ok:!0,usd:.01,eta_s:0})];
out.ac_tr=[T.acTrTxt("align"),T.acTrTxt("chapitre"),T.acTrTxt("stt:elevenlabs:cache"),T.acTrTxt("stt:openai"),T.acTrTxt(null),
  T.acTrTxt("toString"),T.acTrTxt("zz")];
out.ac_clip=[T.acClipTxt({start:12,end:44.46,origine:"llm"}),T.acClipTxt({start:0,end:15,origine:"heuristique"}),T.acClipTxt({}),T.acClipTxt(null)];
/* clôture T8 (24/09/2026) : le 409 « coût dépassé » porte la NOUVELLE estimation ; acEstRefus la marque pour la
   source (objet neuf) ou rend null ; la coche de l'ANCIENNE ne la couvre pas (règle de la coche intacte), témoin :
   cocher la nouvelle couvre la nouvelle */
var E409={detail:"Coût estimé 0.4000 $",estimate:{ok:!0,usd:.4,provider:"elevenlabs"}},N409=T.acEstRefus(E409,AK);
out.ac_409=[N409,N409!==E409.estimate,T.acEstRefus({detail:"x"},AK),T.acEstRefus(null,AK),T.acEstRefus({estimate:"x"},AK),
  T.acEstRefus({estimate:[1]},AK),acf({payer:EOK,vu:N409}),acf({payer:N409,vu:N409}),T.acPayload({src:AS,payer:N409,vu:N409}).max_usd];
/* clôture T8 : D-39 compare aussi le cadrage — un A/B qui ne diffère que par `reframe` n'est plus « identique » ; témoin : même cadrage */
out.df_reframe=[T.diff([{id:"1",tr:"v1",start:0,end:5}],[{id:"1",tr:"v1",start:0,end:5,reframe:{mode:"manuel",x:.3}}]).changed,
  T.diff([{id:"1",tr:"v1",start:0,end:5,reframe:{mode:"manuel",x:.3}}],[{id:"1",tr:"v1",start:0,end:5,reframe:{mode:"manuel",x:.3}}]).changed,
  T.diff([{id:"1",tr:"v1",start:0,end:5,reframe:{mode:"manuel",x:.3}}],[{id:"1",tr:"v1",start:0,end:5,reframe:{mode:"manuel",x:.7}}]).changed];
/* ── [36] L5 D-27 D-29 D-30 D-32 (24/09/2026) : le cœur pur de la couleur — roues, courbes, masque, grade, temps de source ── */
out.co_types=[T.colorTypes.slice(),Object.isFrozen(T.colorTypes)];
/* roue neutre -> identité EXACTE (lift 0, gamma 1, gain 1) */
out.co_neutre=[T.wheelToRgb("lift",0,0,0),T.wheelToRgb("gamma",0,0,0),T.wheelToRgb("gain",0,0,0)];
/* valeurs : R à 90°, G à 210°, B à 330° ; bornes ; disque borné à 1 ; illisible -> neutre ; genre inconnu (y compris hérité) -> null */
out.co_val=[T.wheelToRgb("gain",0,1,0),T.wheelToRgb("lift",1,0,0),T.wheelToRgb("gamma",0,0,1),T.wheelToRgb("gamma",0,0,5),
  T.wheelToRgb("lift",0,0,1),T.wheelToRgb("gain",0,0,-3),T.wheelToRgb("gain",0,3,0),T.wheelToRgb("gain","a",null,void 0),
  T.wheelToRgb("zz",0,0,0),T.wheelToRgb("toString",0,0,0)];
/* aller-retour sur 20 points du disque par genre (maître choisi hors saturation) */
out.co_rt=(function(){var M={lift:.05,gamma:.2,gain:-.1},err=0,n=0;
  ["lift","gamma","gain"].forEach(function(k){for(var i=0;i<20;i++){var r=.15+.45*(i%4)/3,a=i*18*Math.PI/180,x=r*Math.cos(a),y=r*Math.sin(a);
    var q=T.wheelFromRgb(k,T.wheelToRgb(k,x,y,M[k]));n++;
    err=Math.max(err,Math.abs(q.x-x),Math.abs(q.y-y),Math.abs(q.m-M[k]))}});
  return [n,Math.round(err*1e4)/1e4]})();
out.co_from=[T.wheelFromRgb("gain",{r:1.5,g:.75,b:.75}),T.wheelFromRgb("gamma",{r:2,g:2,b:2}),T.wheelFromRgb("lift",{}),
  T.wheelFromRgb("lift",null),T.wheelFromRgb("zz",{r:1})];
var WE={type:"wheels",lift_r:.1,t0:1};
out.co_set=[T.wheelsSet(null,"gain",0,1,0),T.wheelsSet(WE,"gamma",0,0,1),T.wheelsSet({type:"grade_basic",exposure:3},"lift",0,0,0),
  T.wheelsSet(WE,"zz",0,0,0),JSON.stringify(WE)==='{"type":"wheels","lift_r":0.1,"t0":1}',T.wheelsSet(WE,"zz",0,0,0)!==WE];
/* courbes : les cas de T1 §Étape 1 du plan, puis les bords */
out.co_clean=["0.5/0.6","0/0 0.5/0.7 1/1","1/1 0/0 0.5/0.7","0/0 0.5/0.2 0.5/0.7 1/1","abc","","0/0 0.5/1.4 1/1",
  null,5,"0.2/0.3 0.8/0.9","0.12345/0.5","0.1/0.2 zz","-0.5/0.2 1.5/0.8","  0/0\t1/1  ","0.5/0.6/0.7","0.0005/0.2 1/1"].map(function(s){return T.curveClean(s)});
var C20=[];for(var ci=0;ci<20;ci++)C20.push((ci/19)+"/"+(ci/19));
var C20c=T.curveClean(C20.join(" ")),C20p=C20c.split(" ");
out.co_c20=[C20p.length,C20p[0].split("/")[0],C20p[15].split("/")[0],T.curveClean(C20c)===C20c,C20p[1]];
out.co_parse=[T.curveParse("0.5/0.6"),T.curveParse(null)];
out.co_str=[T.curveStr([[0.5,0.7],[0,0],[1,1]]),T.curveStr(null),T.curveStr([]),T.curveStr([[0.5,NaN]]),T.curveStr([[.25,.3]])];
/* pchip : monotone sur des points monotones, dans [0,1], passe par les points, plateau tenu, pas de dépassement ;
   mesure du plan (ffmpeg interp=pchip) : '0/0 0.5/0.6 1/1' fait 64 -> 83 (81 en natural) */
out.co_eval=(function(){var P=[[0,0],[.25,.1],[.5,.7],[1,1]],mono=!0,prev=-1,dans=!0,i,v;
  for(i=0;i<=200;i++){v=T.curveEval(P,i/200);if(v<prev-1e-12)mono=!1;prev=v;if(v<0||v>1)dans=!1}
  var passe=P.every(function(p){return Math.abs(T.curveEval(P,p[0])-p[1])<1e-9});
  var plat=[.4,.5,.6].map(function(x){return Math.round(T.curveEval([[0,0],[.4,.5],[.6,.5],[1,1]],x)*1e6)/1e6});
  var bosse=0;for(i=0;i<=200;i++)bosse=Math.max(bosse,T.curveEval([[0,0],[.5,1],[1,0]],i/200));
  return [mono,dans,passe,plat,Math.round(bosse*1e6)/1e6,Math.round(T.curveEval([[0,0],[1,1]],.3)*1e6)/1e6,
    T.curveEval([[0,.2],[1,.8]],-1),T.curveEval([[0,.2],[1,.8]],2),
    Math.round(T.curveEval([[0,0],[.5,.6],[1,1]],64/255)*2550)/10,Math.round(T.curveEval("0/0 0.5/0.6 1/1",64/255)*2550)/10]})();
/* masque : bornes, forme inconnue / non objet / trop petit -> null, arrondi 1e-4, objet neuf */
var MV={shape:"ellipse",x:.25,y:.25,w:.5,h:.5,soft:.1,inv:!0};
out.co_mask=[T.maskOf(MV),T.maskOf({shape:"rect",x:-1,y:.8,w:2,h:.5,soft:.9}),T.maskOf({shape:"star",x:0,y:0,w:.5,h:.5}),
  T.maskOf({}),T.maskOf(null),T.maskOf("rect"),T.maskOf([1]),T.maskOf({shape:"rect",x:0,y:0,w:.005,h:.5}),
  T.maskOf({shape:"rect",x:.995,y:0,w:.5,h:.5}),T.maskOf({shape:"rect",x:.123456,y:" 0.5 ",w:.5,h:.25,inv:"true"}),
  T.maskOf({shape:"rect",y:0,w:.5,h:.5}),T.maskOf({shape:"ellipse",x:0,y:0,w:1,h:1,soft:"abc",inv:1}),
  T.maskOf(MV)!==MV];
/* grade : prise sans bornes de temps ni `off`, types couleur seulement ; pose à la place du premier effet couleur */
var GK={tr:"v1",id:"k",effects:[{type:"grain",amount:3},{type:"grade_basic",exposure:10,t0:1,t1:2,fade_in:.5,off:!0},
  {type:"wheels",gain_r:1.2,ease_out:.3},{type:"vignette"}],mask:{shape:"rect",x:0,y:0,w:.5,h:.5}},GKj=JSON.stringify(GK),GT=T.gradeTake(GK);
out.co_take=[GT,T.gradeTake(null),T.gradeTake({effects:[{type:"grain"}]}),T.gradeTake({mask:{shape:"ellipse",x:0,y:0,w:.5,h:.5}}),
  T.gradeTake({effects:[{type:"lut",lut:"a"}],mask:{shape:"zz"}}),T.gradeTake({effects:"x"}),
  JSON.stringify(GK)===GKj,GT.effects[0]!==GK.effects[2]];
var PT={tr:"v1",id:"t",effects:[{type:"grain",amount:1},{type:"grade_basic",exposure:-5},{type:"blur"},{type:"lut",lut:"x"}],mask:{shape:"ellipse",x:0,y:0,w:.3,h:.3}},PTj=JSON.stringify(PT);
var PG={effects:[{type:"wheels",gain_r:1.2,t0:3},{type:"grain"}],mask:null},PR=T.gradePaste(PT,PG);
var PR2=T.gradePaste({id:"u",effects:[{type:"grain"}]},{effects:[{type:"curves",pts_m:"0/0 1/1"}],mask:{shape:"ellipse",x:.1,y:.1,w:.2,h:.2}});
out.co_paste=[PR.effects,"mask" in PR,PR.id,PR2.effects,PR2.mask,T.gradePaste(PT,null)===PT,T.gradePaste(PT,{effects:[]}).effects,
  T.gradePaste(PT,GT).effects.map(function(e){return e.type}),JSON.stringify(PT)===PTj,PR.effects[1]!==PG.effects[0],PR.effects[0]===PT.effects[0]];
var CM={type:"colormatch",y_gain:1.5},CMin=[{type:"grain"},{type:"colormatch",y_gain:1},{type:"blur"},{type:"colormatch",y_gain:2}];
out.co_cm=[T.colorMatchPut(CMin,CM),T.colorMatchPut([{type:"grain"}],CM),T.colorMatchPut(null,{y_gain:2}),
  T.colorMatchPut(CMin,CM).filter(function(e){return e.type==="colormatch"}).length,CMin.length,T.colorMatchPut(CMin,CM)[1]!==CM];
/* temps de source sous la tête : srcIn + (tête − début)·vitesse, vitesse lue comme le cadrage (0,25..4) ; hors plan -> milieu */
var SK={tr:"v1",start:2,end:6,srcIn:1,speed:2};
out.co_src=[T.srcTimeAt(SK,3),T.srcTimeAt(SK,2),T.srcTimeAt(SK,7),T.srcTimeAt(SK,1),T.srcTimeAt(SK,6),T.srcTimeAt(SK,NaN),
  T.srcTimeAt({start:2,end:6,srcIn:1},4),T.srcTimeAt({start:0,end:4},1),T.srcTimeAt(null,1),T.srcTimeAt({tr:"v1",start:2,end:6,srcIn:1,speed:10},3),
  T.srcTimeAt({start:0,end:3,srcIn:.5},1/3)];
/* revue T4 (24/09) : un effet couleur ÉTEINT (off vrai) ne fait pas partie du grade — ni emporté, ni réactivé à la pose ;
   témoins : un effet actif (off absent ou faux) passe, `off` retiré de la copie */
out.co_paste_off=[T.gradePaste(PT,{effects:[{type:"lut",lut:"z",off:!0},{type:"wheels",gain_r:1.1}],mask:null}).effects,
  T.gradePaste(PT,{effects:[{type:"lut",lut:"z"}]}).effects,T.gradeTake({effects:[{type:"wheels",gain_r:2,off:!0}]}),
  T.gradeTake({effects:[{type:"wheels",gain_r:1,off:!1},{type:"curves",off:1}]})];
/* revue T4 (24/09) : la règle UNIQUE des courbes rejouée sur les vecteurs partagés (tests/l5_courbes_vecteurs.json,
   lus par le banc et posés ici — la couche ne lit aucun fichier) ; [index, entrée, attendu, obtenu] par divergence */
out.co_vec=(function(){var V=/*L5_VEC*/,dv=[];
  V.forEach(function(v,i){var js=T.curveClean(v["in"]);if(js!==v.out)dv.push([i,v["in"],v.out,js])});
  return [V.length,dv]})();
/* revue T4 (24/09) : 30 masques rejoués contre mask_region.mask_of (appelé par le banc) */
out.co_maskx=(/*L5_MASKS*/).map(function(m){return T.maskOf(m)});
/* revue T4 (24/09, T4-1) : la pchip ÉPINGLÉE au 1e-6 (moyenne harmonique pondérée, borne 3·m0, remise à 0 au changement
   de signe : chacune change au moins une valeur) ; « sans dépassement » : la première courbe reste dans [0, 0,5], monotone */
out.co_eval_exact=(function(){var R=function(v){return Math.round(v*1e6)/1e6},mx=-1,mn=2,mono=!0,pv=-1,i,v;
  for(i=0;i<=1000;i++){v=T.curveEval("0/0 0.1/0.45 1/0.5",i/1000);mx=Math.max(mx,v);mn=Math.min(mn,v);if(v<pv-1e-12)mono=!1;pv=v}
  return [R(T.curveEval("0/0 0.1/0.45 1/0.5",.3)),R(T.curveEval("0/0.5 0.5/0.6 1/0.2",.1)),R(T.curveEval("0/0 0.1/0.45 1/0.5",.55)),
    R(mx),R(mn),mono]})();
/* T4-6 : dzmCurveEval ne lève JAMAIS (x lu par dzmRfNum, illisible -> 0) ; la fabrique = l'évaluation ; témoin « 0.3 » lu */
out.co_eval_sur=(function(){var f=T.curveFn("0/0.2 0.1/0.45 1/0.5"),res=[];
  [Symbol("s"),{valueOf:function(){throw new Error("x")}},null,void 0,"abc","0.3",.3].forEach(function(x){
    try{res.push(Math.round(T.curveEval("0/0.2 0.1/0.45 1/0.5",x)*1e6)/1e6)}catch(e){res.push("leve")}});
  return [res,f(.3)===T.curveEval("0/0.2 0.1/0.45 1/0.5",.3),f(.55)===T.curveEval("0/0.2 0.1/0.45 1/0.5",.55)]})();
/* T4-5 : Math.hypot — un point énorme est ramené sur le cercle (x·x déborderait à l'infini et annulerait le point) */
out.co_hypot=[T.wheelToRgb("gain",1e200,1e200,0),T.wheelToRgb("gain",Math.SQRT1_2,Math.SQRT1_2,0)];
/* T4-7 : la vitesse ne compte que sur V1 (le rendu ne la lit que là, _v1_speed) ; témoin : V1 à vitesse 2 */
out.co_src_v1=[T.srcTimeAt({tr:"v2",start:2,end:6,srcIn:1,speed:2},3),T.srcTimeAt({start:2,end:6,srcIn:1,speed:2},3),
  T.srcTimeAt({tr:"v1",start:2,end:6,srcIn:1,speed:2},3),T.srcTimeAt({tr:"v1",start:2,end:6,srcIn:1,speed:"x"},3)];
/* ── [37] L5 D-27 D-29 D-30 D-28 (24/09/2026, tâche 5) : le panneau Étalonnage — aides pures, puis le composant sous shim ── */
/* la pile : le premier effet d'un type ; poser à la place du PREMIER de son type (les suivants gardés), sinon en queue */
out.gp_fx=[T.fxOf([{type:"grain"},{type:"wheels",a:1},{type:"wheels",a:2}],"wheels"),T.fxOf(null,"wheels"),T.fxOf([{type:"grain"}],"curves"),
  T.fxPut([{type:"grain"},{type:"wheels",a:1},{type:"blur"},{type:"wheels",a:2}],{type:"wheels",a:9}),T.fxPut([{type:"grain"}],{type:"curves"}),
  T.fxPut(null,{type:"x"}),(function(){var L=[{type:"a"}],j=JSON.stringify(L),n=T.fxPut(L,{type:"a",v:1});return [JSON.stringify(L)===j,n!==L,n[0].v]})()];
/* l'édition des points d'une courbe : toucher, déplacer (x entre les voisins, extrémités fixes en x), ajouter (16 au plus), retirer, milieu */
var CP=[[0,0],[.5,.6],[1,1]],CPj=JSON.stringify(CP);
out.gp_hit=[T.curveHit(CP,.51,.62,.04),T.curveHit(CP,.3,.3,.04),T.curveHit(CP,0,.01,.04),T.curveHit(null,0,0,.04),T.curveHit(CP,.98,.99,.04)];
out.gp_move=[T.curveMove(CP,1,.7,.9),T.curveMove(CP,1,1.5,-1),T.curveMove(CP,1,-3,2),T.curveMove(CP,0,.3,.2),T.curveMove(CP,2,.2,.5),
  T.curveMove(CP,5,.3,.3),T.curveMove(CP,1,.3333333,.66666),T.curveMove(CP,1,NaN,"x")];
var C16=[];for(var gi=0;gi<16;gi++)C16.push([gi/15,gi/15]);
out.gp_add=[T.curveAdd(CP,.25,.4),T.curveAdd(CP,.5,.9),T.curveAdd(CP,1.2,.3),T.curveAdd(C16,.01,.5),T.curveAdd(CP,NaN,.5),T.curveAdd(null,.2,.2),
  T.curveAdd(C16.slice(0,15),.01,1.7).i,JSON.stringify(CP)===CPj];
out.gp_del=[T.curveDel(CP,1),T.curveDel(CP,0),T.curveDel(CP,2),T.curveDel(null,1),T.curveDel(CP,1)!==CP];
out.gp_mid=(function(){var m=T.curveMid(CP),m2=T.curveMid([[0,0],[.2,.1],[1,1]]);
  return [m.x,m.y===Math.round(T.curveEval(CP,m.x)*1000)/1000,T.curveMid([[0,0],[1,1]]),m2.x,T.curveMid(null)]})();
/* le plan précédent de V1 : voisin gauche en contact, sinon le plus proche qui finit avant ; plans sans source écartés */
var GV=[{tr:"v1",id:"a",start:0,end:4,src:{job_id:"A"}},{tr:"v1",id:"b",start:4,end:8,src:{job_id:"B"}},{tr:"v1",id:"c",start:10,end:12,src:{job_id:"C"}},
  {tr:"v2",id:"o",start:0,end:10,src:{job_id:"O"}},{tr:"v1",id:"t",start:12,end:13},{tr:"v1",id:"d",start:13,end:15,src:{job_id:"D"}}];
out.gp_prev=["b","c","a","d","o"].map(function(k){var p=T.gradePrev(GV,GV.filter(function(q){return q.id===k})[0]);return p?p.id:null})
  .concat([T.gradePrev(null,GV[1]),T.gradePrev(GV,null)]);
/* le corps de POST /api/montage/color-match : cible = instant de source sous la tête ; référence = milieu du précédent ; auto sans référence */
var MC={tr:"v1",id:"b",start:4,end:8,srcIn:1,speed:2,src:{job_id:"B"}};
out.gp_match=[T.matchBody(MC,5,GV[0],!1),T.matchBody(MC,5,null,!0),T.matchBody(MC,5,null,!1),T.matchBody(MC,5,{id:"z"},!1),
  T.matchBody(null,1,GV[0],!0),T.matchBody(MC,5,GV[0],!0)];
/* le corps de POST /api/montage/grade-frame : effets actifs (pas les `off`), masque seulement avec des effets, largeur paire 96..640 */
var FC={tr:"v1",id:"f",start:0,end:4,srcIn:0,src:{job_id:"F"},effects:[{type:"wheels",gain_r:1.2},{type:"blur",off:!0}],mask:{shape:"rect",x:0,y:0,w:.5,h:.5}};
out.gp_frame=[T.frameBody(FC,1,320),T.frameBody(Object.assign({},FC,{effects:[]}),1,320),T.frameBody(FC,1,7),T.frameBody(FC,1,999),
  T.frameBody(FC,1,"x"),T.frameBody(null,1,320),T.frameBody(Object.assign({},FC,{effects:[{type:"blur",off:!0}]}),9,241)];
/* l'empreinte d'obsolescence : source + fenêtre de source + géométrie (les effets n'y entrent pas) */
out.gp_sig=[T.gpSig(MC)===T.gpSig(Object.assign({},MC,{effects:[1]})),T.gpSig(MC)!==T.gpSig(Object.assign({},MC,{srcIn:2})),
  T.gpSig(MC)!==T.gpSig(Object.assign({},MC,{src:{job_id:"Z"}})),T.gpSig(MC)!==T.gpSig(Object.assign({},MC,{speed:1})),T.gpSig(null)];
/* LE COMPOSANT : `r` et `x` lus à l'appel ; shim = jsx factice {t,p}, hooks factices posés sur l'objet global le temps de l'appel
   (un `var x` du banc casserait drawer_touche_x), magasin factice (un objet par appel) posé là où dzmTbStore le lit :
   `window` du shim (le cœur E-5..D-7 ne nomme pas le stockage, eb_croise x5 — la couche passe par dzmTbStore) */
function gpShim(fn,store){var r0=r,G=globalThis,hx=Object.prototype.hasOwnProperty.call(G,"x"),x0=G.x,
  hl=Object.prototype.hasOwnProperty.call(window,"localStorage"),l0=window.localStorage,log={st:0,eff:[],ref:0},S=store||{};
  try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
    G.x={useState:function(v){log.st++;return [v,function(){}]},useRef:function(v){log.ref++;return {current:v}},
      useEffect:function(f,d){log.eff.push(Array.isArray(d)?d.length:-1)}};
    window.localStorage={getItem:function(k){return Object.prototype.hasOwnProperty.call(S,k)?S[k]:null},setItem:function(k,v){S[k]=String(v)}};
    return fn(log,S)}catch(e){return "autre:"+e}finally{r=r0;if(hx)G.x=x0;else delete G.x;if(hl)window.localStorage=l0;else delete window.localStorage}}
function gpTous(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;
  if(Array.isArray(n)){n.forEach(function(k){gpTous(k,acc)});return acc}
  if(n.t!==void 0&&n.p){acc.push(n);gpTous(n.p.children,acc)}return acc}
function gpTxt(n){var c=n&&n.p&&n.p.children;if(typeof c==="string")return c;
  if(Array.isArray(c))return c.filter(function(k){return typeof k==="string"}).join("");return ""}
function gpBtns(m){return gpTous(m).filter(function(n){return n.t==="button"})}
function gpBtn(m,lbl){return gpBtns(m).filter(function(b){return gpTxt(b)===lbl})[0]}
var GC={tr:"v1",id:"g",start:4,end:8,srcIn:0,src:{job_id:"G"},effects:[{type:"wheels",gain_r:1.5,gain_g:.75,gain_b:.75},{type:"curves",pts_m:"0/0 0.5/0.7 1/1"}],
  mask:{shape:"ellipse",x:.25,y:.25,w:.5,h:.5}};
out.gp_pure=[typeof T.GradePanel,typeof T.MaskBox];
/* sans clip : null SANS toucher x (la garde précède les hooks) ; boîte du masque : null sans masque lisible ou sans effet actif */
out.gp_null=(function(){var r0=r;try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  return [T.GradePanel(null),T.GradePanel({}),T.MaskBox(null),T.MaskBox({clip:{effects:[{type:"blur"}]}}),
    T.MaskBox({clip:{mask:{shape:"rect",x:0,y:0,w:.5,h:.5}}}),T.MaskBox({clip:{mask:{shape:"rect",x:0,y:0,w:.5,h:.5},effects:[{type:"blur",off:!0}]}}),
    T.MaskBox({clip:{mask:{shape:"zz",x:0,y:0,w:.5,h:.5},effects:[{type:"blur"}]}})]}catch(e){return "autre:"+e}finally{r=r0}})();
out.gp_box=(function(){var r0=r;try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  var m=T.MaskBox({clip:{mask:{shape:"ellipse",x:.1,y:.2,w:.3,h:.4,inv:!0},effects:[{type:"blur"}]}}),m2=T.MaskBox({clip:{mask:{shape:"rect",x:0,y:0,w:1,h:1},effects:[{type:"blur"}]}});
  return [m.t,m.p.className,m.p["data-shape"],m.p["data-inv"],m.p.style,m2.p["data-shape"],m2.p["data-inv"]]}catch(e){return "autre:"+e}finally{r=r0}})();
/* le rendu : racine, titre, rangées, 13 boutons TITRÉS dans l'ordre, 4 canvas, 8 curseurs + 1 case, valeurs lues, 4 useState + 2 useEffect */
out.gp_rendu=gpShim(function(log){var m=T.GradePanel({clip:GC,clips:[GV[0],GC],head:5,onChange:function(){},onNote:function(){}}),all=gpTous(m);
  var rng=all.filter(function(n){return n.t==="input"&&n.p.type==="range"}),cv=all.filter(function(n){return n.t==="canvas"});
  return [m.t,m.p.className,m.p.children[0].p.children,all.filter(function(n){return /dzm-plan-row/.test(n.p.className||"")}).map(function(n){return n.p.children[0].p.children}),
    gpBtns(m).map(function(b){return [gpTxt(b),typeof b.p.title==="string"&&b.p.title.length>3,!!b.p.disabled]}),
    cv.map(function(n){return [n.p["data-kind"],n.p.width,n.p.height,typeof n.p.onPointerDown,typeof n.p.ref,!!n.p.title]}),
    rng.map(function(n){return [n.p.value,!!n.p.disabled,!!n.p.title]}),
    all.filter(function(n){return n.t==="input"&&n.p.type==="checkbox"}).map(function(n){return [n.p.checked,!!n.p.disabled,!!n.p.title]}),
    log.st,log.eff,gpBtn(m,"M").p["aria-pressed"],gpBtn(m,"Ellipse").p["aria-pressed"]]});
/* verrou de V1 : toute écriture grisée et dite (titre « verrouillée »), les onglets et « Copier » restent (lecture seule) ;
   un grade EST copié (sinon « Coller » serait grisé pour une autre raison : mutation survivante du 24/09, corrigée) */
out.gp_verrou=gpShim(function(){var m=T.GradePanel({clip:GC,clips:[GV[0],GC],head:5,locked:!0});
  return gpBtns(m).map(function(b){return [gpTxt(b),!!b.p.disabled,/verrouillée/.test(b.p.title||"")]}).concat([
    gpTous(m).filter(function(n){return n.t==="input"}).every(function(n){return n.p.disabled===!0&&/verrouillée/.test(n.p.title||"")})])},
  {dz_montage_grade:JSON.stringify({effects:[{type:"wheels",gain_r:1.1}],mask:null})});
/* état vide : ni effet, ni masque, ni voisin — masque grisé et dit (« ajoutez-en un »), accord grisé et dit, rien à copier */
out.gp_vide=gpShim(function(){var m=T.GradePanel({clip:{tr:"v1",id:"v",start:0,end:4,src:{job_id:"V"}},clips:[],head:1});
  return gpBtns(m).map(function(b){return [gpTxt(b),!!b.p.disabled,b.p.title]}).concat([
    gpTous(m).filter(function(n){return n.t==="input"}).map(function(n){return !!n.p.disabled})])});
/* les gestes qui n'ont pas besoin de la fenêtre : double-clic d'une roue (remise à zéro, léger), maître (léger), onglets, masque
   (forme = lourd, curseur = léger, « Aucun » retire la clé), « À plat » (le canal courant revient à l'identité), « + Point » */
out.gp_geste=gpShim(function(){var L=[],on=function(p,h){L.push([JSON.parse(JSON.stringify(p)),Object.keys(p),h])};
  var m=T.GradePanel({clip:GC,clips:[GV[0],GC],head:5,onChange:on});
  var cv=gpTous(m).filter(function(n){return n.t==="canvas"}),rng=gpTous(m).filter(function(n){return n.t==="input"&&n.p.type==="range"});
  cv[2].p.onDoubleClick({});rng[2].p.onChange({target:{value:"20"}});
  gpBtn(m,"Rectangle").p.onClick();gpBtn(m,"Aucun").p.onClick();rng[3].p.onChange({target:{value:"40"}});rng[7].p.onChange({target:{value:"30"}});
  gpTous(m).filter(function(n){return n.t==="input"&&n.p.type==="checkbox"})[0].p.onChange({target:{checked:!0}});
  gpBtn(m,"À plat").p.onClick();gpBtn(m,"+ Point").p.onClick();
  return L});
/* copier / coller le grade par le stockage `dz_montage_grade` (objet factice) : copier écrit gradeTake, coller remplace les effets couleur */
out.gp_grade=gpShim(function(log,S){var N=[],on=[];
  var m=T.GradePanel({clip:GC,clips:[],head:5,onNote:function(t){N.push(t)},onChange:function(p,h){on.push([p,h])}});
  gpBtn(m,"Copier le grade").p.onClick();
  var cible={tr:"v1",id:"h",start:0,end:4,src:{job_id:"H"},effects:[{type:"grain"},{type:"grade_basic",exposure:3}]};
  var m2=T.GradePanel({clip:cible,clips:[],head:1,onNote:function(t){N.push(t)},onChange:function(p,h){on.push([p,h])}}),cb=gpBtn(m2,"Coller le grade");
  cb.p.onClick();
  var brut=S.dz_montage_grade;S.dz_montage_grade="{pas du json";var m3=T.GradePanel({clip:cible,clips:[],head:1});
  return [typeof brut==="string"&&JSON.parse(brut),N,!!cb.p.disabled,on.map(function(q){return [q[0].effects,"mask" in q[0],q[0].mask,q[1]]}),
    !!gpBtn(m3,"Coller le grade").p.disabled]});
/* ── [38] L5 D-31 D-32 (24/09/2026, tâche 6) : scopes sous le lecteur, lightbox des plans, copier / coller du grade (gestes partagés) ── */
var SC=[{tr:"v2",id:"o",start:0,end:10,src:{job_id:"O"}},
  {tr:"v1",id:"a",start:0,end:4,src:{job_id:"A"},effects:[{type:"wheels",gain_r:1.2},{type:"blur",off:!0}],mask:{shape:"rect",x:0,y:0,w:.5,h:.5}},
  {tr:"v1",id:"b",start:4,end:8,srcIn:2,speed:2,src:{job_id:"B"}},{tr:"v1",id:"d",start:9,end:11}];
/* le plan V1 sous la tête : [début, fin[, V2 ignoré, tête illisible -> null */
out.sc_at=[4,3.999,0,8,8.5,9.5,-1,"x",null,"4.5"].map(function(h){var c=T.scopesAt(SC,h);return c?c.id:null})
  .concat([T.scopesAt(null,1),T.scopesAt([null,5],1)]);
/* le corps de POST /api/montage/scopes : celui de grade-frame SANS largeur (effets actifs, masque avec effets) ; sans source -> null */
out.sc_body=[T.scopesBody(SC[1],1),T.scopesBody(SC[2],5),T.scopesBody(SC[3],10),T.scopesBody(null,1)];
/* la mémoire de la bascule : clé dz_montage_scopes, « 1 » / « 0 », éteinte par défaut, magasin en panne -> éteinte, rend ce qu'elle a posé */
function scSt(S){return {getItem:function(k){return Object.prototype.hasOwnProperty.call(S,k)?S[k]:null},setItem:function(k,v){S[k]=String(v)}}}
var SCBAD={getItem:function(){throw new Error("refus")},setItem:function(){throw new Error("refus")}};
out.sc_store=(function(){var S={},st=scSt(S),a=T.scopesGet(st),b=T.scopesSet(!0,st),c=T.scopesGet(st),d=S.dz_montage_scopes,
  e=T.scopesSet(!1,st),f=S.dz_montage_scopes;
  return [a,b,c,d,e,f,T.scopesGet(st),T.scopesGet(SCBAD),T.scopesSet(!0,SCBAD),T.SC_CLE]})();
/* la lightbox : les plans de V1 dans l'ordre du début (bornes lisibles), l'entrée intacte */
out.lb_plans=(function(){var L=SC.concat([{tr:"v1",id:"z",start:-2,end:0},{tr:"v1",id:"n",start:"x",end:3},null]),j=JSON.stringify(L);
  return [T.lbPlans(L).map(function(c){return c.id}),JSON.stringify(L)===j,T.lbPlans(null),T.lbPlans([])]})();
/* la file des vignettes : au plus trois en vol, les premières en attente dans l'ordre, max illisible -> 3, borné à 3 */
out.lb_next=[T.lbNext(["a","b","c","d","e"],{},3),T.lbNext(["a","b","c","d","e"],{a:"run",b:"ok",c:"run"},3),
  T.lbNext(["a","b","c","d"],{a:"run",b:"run",c:"run"},3),T.lbNext(["a","b"],{a:"ok",b:"err"},3),T.lbNext(null,{},3),
  T.lbNext(["a","b"],null,0),T.lbNext(["a","b","c","d"],{},"x"),T.lbNext(["a","b","c","d","e"],{},5),T.lbNext(["a","b","c"],{z:"run",y:"run"},3),T.LB_MAX];
/* copier / coller : LES gestes partagés du panneau, du clavier et des menus (même stockage dz_montage_grade, même phrase) */
out.gc=(function(){var S={},st=scSt(S);
  var src={tr:"v1",id:"s",effects:[{type:"grain"},{type:"wheels",gain_r:1.2,t0:1},{type:"curves",pts_m:"0/0 1/1",off:!0}],mask:{shape:"ellipse",x:.1,y:.1,w:.5,h:.5}};
  var c1=T.gradeCopyDo(src,st),stored=JSON.parse(S.dz_montage_grade||"null");
  var c2=T.gradeCopyDo({effects:[{type:"grain"}]},st),c3=T.gradeCopyDo(src,SCBAD),c4=T.gradeCopyDo(null,st);
  var cible={tr:"v2",id:"t",effects:[{type:"blur"},{type:"huesat",hue:10},{type:"grain"}],mask:{shape:"rect",x:0,y:0,w:1,h:1}},cj=JSON.stringify(cible);
  var p1=T.gradePasteDo(cible,st),p2=T.gradePasteDo(cible,scSt({})),p3=T.gradePasteDo(cible,SCBAD);
  var p4=T.gradePasteDo(cible,scSt({dz_montage_grade:JSON.stringify({effects:[{type:"lut",file:"a.cube"},{type:"grade",x:1}],mask:null})}));
  return [c1,stored,c2,c3,c4,p1,p2,p3,p4,"mask" in p4.clip,JSON.stringify(cible)===cj,JSON.stringify(stored)===S.dz_montage_grade]})();
/* LES COMPOSANTS sous shim (gpShim : jsx factice, hooks factices, magasin factice là où dzmTbStore le lit) */
/* scShim = gpShim dont useState JOUE l'initialiseur paresseux (la bascule et les plans sont lus UNE fois, au montage) */
function scShim(fn,store){var G=globalThis;
  return gpShim(function(log,S){var x1=G.x;G.x=Object.assign({},x1,{useState:function(v){return x1.useState(typeof v==="function"?v():v)}});
    try{return fn(log,S)}finally{G.x=x1}},store)}
function scMsg(m){return gpTous(m).filter(function(n){return /dzm-scmsg/.test(n.p.className||"")}).map(gpTxt)}
out.sc_null=(function(){var r0=r;try{r={jsx:function(t,p){return {t:t,p:p}},jsxs:function(t,p){return {t:t,p:p}}};
  return [T.Scopes(null),T.Lightbox(null)]}catch(e){return "autre:"+e}finally{r=r0}})();
out.sc_rendu=scShim(function(log,S){
  var off=T.Scopes({clips:SC,head:1,playing:!1}),b0=gpBtns(off);
  S.dz_montage_scopes="1";
  var on=T.Scopes({clips:SC,head:1,playing:!1}),lec=T.Scopes({clips:SC,head:1,playing:!0}),
    vide=T.Scopes({clips:SC,head:8.5,playing:!1}),ss=T.Scopes({clips:SC,head:10,playing:!1});
  return [off.t,off.p.className,b0.map(function(b){return [gpTxt(b),b.p.title,b.p["aria-pressed"],b.p["data-on"]]}),scMsg(off),
    gpBtns(on).map(function(b){return [gpTxt(b),b.p.title,b.p["aria-pressed"],b.p["data-on"]]}),scMsg(on),scMsg(lec),scMsg(vide),scMsg(ss),
    log.st,log.eff.slice(0,2),log.eff.length,
    [off,on,lec].map(function(m){return gpTous(m).filter(function(n){return /dzm-scpop/.test(n.p.className||"")}).length})]});
out.lb_rendu=scShim(function(log){var P=[],C=[];
  var m=T.Lightbox({clips:SC,onPick:function(c){P.push(c.id)},onClose:function(){C.push(1)}});
  var all=gpTous(m),tiles=all.filter(function(n){return /dzm-lbtile/.test(n.p.className||"")});
  tiles[1].p.onClick();
  m.p.onClick({target:1,currentTarget:2});m.p.onClick({target:m,currentTarget:m});
  gpBtns(m).filter(function(b){return gpTxt(b)==="Fermer"})[0].p.onClick();
  var vide=T.Lightbox({clips:[{tr:"v2",id:"o",start:0,end:1}],onPick:function(){},onClose:function(){}});
  return [m.t,m.p.className,tiles.map(function(b){return [b.t,b.p["data-id"],typeof b.p.title==="string"&&b.p.title.length>5]}),P,C.length,
    gpBtns(m).every(function(b){return typeof b.p.title==="string"&&b.p.title.length>3}),gpBtns(m).length,
    gpTous(vide).filter(function(n){return /dzm-lbmsg/.test(n.p.className||"")}).map(gpTxt),log.st,log.eff.slice(0,1)]});
/* ── [39] L6 D-25 D-26 (25/09/2026, tâche 4) : le cœur pur audio — plage de bruit en temps de source, débruiteur appris, prises, type d'enregistrement ── */
function auR(o){return o&&o.refus?o.refus:o}
var AK={tr:"a1",id:"k",start:10,end:20,srcIn:5,src:{audio:"a.wav"}};
out.au_lr=[T.learnRange(AK,{"in":12,out:13},0),T.learnRange(Object.assign({},AK,{speed:2}),{"in":12,out:13},0),
  T.learnRange(AK,{"in":8,out:9},0),auR(T.learnRange(AK,{"in":2,out:3},0)),auR(T.learnRange(AK,null,0)),
  auR(T.learnRange(AK,{"in":null,out:3},0)),auR(T.learnRange(AK,{"in":12,out:12.1},0)),auR(T.learnRange(AK,{"in":12,out:13},7.5)),
  T.learnRange(AK,{"in":12,out:13},8),auR(T.learnRange(AK,{"in":12,out:43},0)),T.learnRange(AK,{"in":12,out:42},0),
  auR(T.learnRange(null,{"in":12,out:13},0)),auR(T.learnRange(AK,{"in":13,out:12},0)),
  T.learnRange(Object.assign({},AK,{speed:1.0004}),{"in":12,out:13},0),T.learnRange(Object.assign({},AK,{speed:9}),{"in":12,out:13},0),
  T.learnRange(Object.assign({},AK,{srcIn:null}),{"in":12,out:13},0),T.learnRange(AK,{"in":"12",out:"13"},0),
  T.learnRange(AK,{"in":12,out:12.2},0),auR(T.learnRange(AK,{"in":6,out:6.2},0)),auR(T.learnRange(AK,{"in":6,out:6.199},0)),
  auR(T.learnRange({tr:"a1",id:"k",end:20,srcIn:5,src:{audio:"a.wav"}},{"in":12,out:13},0)),
  auR(T.learnRange(Object.assign({},AK,{start:"x"}),{"in":12,out:13},0)),
  T.learnRange(Object.assign({},AK,{srcIn:-3}),{"in":10.5,out:11.5},0)];
/* chaque refus porte une phrase */
out.au_lr_note=[T.learnRange(AK,null,0),T.learnRange(AK,{"in":2,out:3},0),T.learnRange(AK,{"in":12,out:12.1},0),
  T.learnRange(AK,{"in":12,out:43},0),T.learnRange(null,{"in":1,out:2},0),
  T.learnRange(Object.assign({},AK,{start:"x"}),{"in":12,out:13},0)].map(function(o){return typeof o.note==="string"&&o.note.length>10});
var DQ=[{type:"eq3",params:{bass_db:2}},{type:"denoise",params:{amount:30}}],DQj=JSON.stringify(DQ),DL=T.denoiseLearn(DQ,7,8,-31);
var DF=[{type:"denoise",amount:30,enabled:!0}],DFj=JSON.stringify(DF),DFL=T.denoiseLearn(DF,1,2,-40);
out.au_dl=[T.denoiseLearn([],7,8,-31),DL,DL[0]===DQ[0],DL!==DQ,DL[1]!==DQ[1],JSON.stringify(DQ)===DQj,
  DFL,JSON.stringify(DF)===DFj,T.denoiseLearn(null,7,8,-31),T.denoiseLearn(DQ,7,8,"x")[1],T.denoiseLearn(DQ,"a",8,-31),
  T.denoiseLearn(DQ,8,7,-31),T.denoiseLearn([{type:"denoise",params:{amount:30}},{type:"denoise",params:{amount:50}}],1,2,-30),
  T.denoiseLearn([{type:"denoise",params:[1]}],1,2,-30),T.denoiseLearn([],1,2,-95)[0].params.nf,T.denoiseLearn([],1,2,5)[0].params.nf];
/* revue T5 (25/09) : un debruiteur COUPE est reactive par l'apprentissage ; temoin : l'eq3 coupe reste coupe, entree intacte */
var DX=[{type:"eq3",enabled:!1,params:{bass_db:2}},{type:"denoise",enabled:!1,params:{amount:30}},{type:"deesser",enabled:!1,amount:3}],
  DXj=JSON.stringify(DX),DXL=T.denoiseLearn(DX,1,2,-30);
out.au_dx=[DXL,DXL[0]===DX[0],DXL[2]===DX[2],JSON.stringify(DX)===DXj,
  T.denoiseLearn([{type:"denoise",enabled:!1,amount:30}],1,2,-30),T.denoiseLearn([{type:"denoise",enabled:!0,amount:30}],1,2,-30)];
var FG=[{type:"eq3",params:{bass_db:2}},{type:"denoise",params:{amount:30,nf:-31,learn_in:7,learn_out:8}},{type:"denoise",nf:-2,learn_in:1,learn_out:2,amount:9}],
  FGj=JSON.stringify(FG),FGo=T.denoiseForget(FG);
out.au_df=[FGo,FGo[0]===FG[0],JSON.stringify(FG)===FGj,T.denoiseForget(null),T.denoiseForget([{type:"eq3"}]),
  T.denoiseForget(T.denoiseLearn(DQ,7,8,-31)),T.denoiseForget([{type:"denoise",params:{amount:30}}])[0]];
out.au_vo=[T.voCount([{src:{audio:"voix-off-20260925-101010.wav"}},{src:{audio:"voix-off-20260925-101011-2.wav"}},{src:{audio:"musique.mp3"}},
  {src:{job_id:"voix-off-x"}},null,{src:null},{src:{audio:"ma-voix-off-1.wav"}}]),T.voCount([]),T.voCount(null),T.voLabel(3),T.voLabel(1),T.voLabel(0),T.voLabel("x"),T.voLabel(2.7)];
out.au_rm=[T.recMime(function(t){return t==="audio/ogg;codecs=opus"}),T.recMime(function(){return !1}),T.recMime(function(){return !0}),
  T.recMime(null),T.recMime(function(t){if(t!=="audio/mp4")throw new Error("x");return !0}),T.VO_MIMES.slice(),Object.isFrozen(T.VO_MIMES)];
console.log(JSON.stringify(out));
"""
# E-9 : svmRuler / svmPad2 sont des fonctions DU BUNDLE (meme portee module que
# la couche) : le shim les recoit EXTRAITES de .bak_montage, comme le banc du
# bundle (P10) les lit -- une copie ici divergerait au premier changement.
_E9_BAK = os.path.join(ROOT, "frontend", "dist", "assets", "index-BEOJX8L5.js.bak_montage")
_E9_RULER = ""
if os.path.isfile(_E9_BAK):
    with open(_E9_BAK, "rb") as _fh: _bk = _fh.read().decode("utf-8", "replace")
    _mp = re.search(r"function svmPad2\([^)]*\)\{[^}]*\}", _bk); _mr = re.search(r"function svmRuler\([^)]*\)\{[^}]*\}", _bk)
    if _mp and _mr: _E9_RULER = _mp.group(0) + "\n" + _mr.group(0)
PROBE = PROBE.replace("/*E9_RULER*/", _E9_RULER)
# E-6 (lot E-C, tache 1) : les combos de SVM_ACTIONS sont lues dans le bundle PATCHE
# (R_R1 y ajoute 11 actions absentes du .bak : 34 -> 45 combos mesurees le 23/09/2026),
# entre `var SVM_ACTIONS=[` et son `];` -- jamais recopiees. Regex gardee par le temoin de compte.
_EC_BUNDLE = os.path.join(ROOT, "frontend", "dist", "assets", "index-BEOJX8L5.js")
_EC_COMBOS, _EC_IDS = [], []
if os.path.isfile(_EC_BUNDLE):
    with open(_EC_BUNDLE, "rb") as _fh: _bd = _fh.read().decode("utf-8", "replace")
    _i0 = _bd.find("var SVM_ACTIONS=["); _i1 = _bd.find("];", _i0) if _i0 >= 0 else -1
    if 0 <= _i0 < _i1:
        _EC_COMBOS = re.findall(r'combo:"([^"]*)"', _bd[_i0:_i1])
        _EC_IDS = re.findall(r'\{id:"([a-z0-9_]+)",sec:"', _bd[_i0:_i1])
PROBE = PROBE.replace("/*EC_COMBOS*/", json.dumps(_EC_COMBOS, ensure_ascii=False))
# revue T4 (24/09) : les vecteurs PARTAGES des courbes (produits par le script de reference Python, font foi) et
# trente masques rejoues contre mask_region.mask_of. JSON ASCII (\u001c, NaN et Infinity sont du JS valide).
_L5_VEC_PATH = os.path.join(ROOT, "backend", "tests", "l5_courbes_vecteurs.json")
_L5_VEC = []
if os.path.isfile(_L5_VEC_PATH):
    with open(_L5_VEC_PATH, "rb") as _fh: _L5_VEC = json.loads(_fh.read().decode("utf-8"))
PROBE = PROBE.replace("/*L5_VEC*/", json.dumps(_L5_VEC))
_L5_MASKS = [
    {"shape": "rect", "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4},
    {"shape": "ellipse", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0.2, "inv": True},
    {"shape": "rect", "x": False, "y": 0, "w": 0.5, "h": 0.5},
    {"shape": "rect", "x": 0, "y": 0, "w": True, "h": 0.5},
    {"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": 0.5, "soft": True},
    {"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": 0.5, "inv": 1},
    {"shape": "rect", "x": -0.5, "y": 0, "w": 0.5, "h": 0.5},
    {"shape": "rect", "x": 1.2, "y": 0, "w": 0.5, "h": 0.5},
    {"shape": "rect", "x": 0.99004, "y": 0, "w": 0.5, "h": 0.5},
    {"shape": "rect", "x": 0.12345, "y": 0.00005, "w": 1, "h": 1},
    {"shape": "rect", "x": 0, "y": " 0.5 ", "w": 0.5, "h": 0.25},
    {"shape": "rect", "x": "abc", "y": 0, "w": 0.5, "h": 0.5},
    {"shape": "rect", "x": None, "y": 0, "w": 0.5, "h": 0.5},
    {"shape": "rect", "x": 0, "y": 0, "w": 0.5},
    {"shape": "star", "x": 0, "y": 0, "w": 0.5, "h": 0.5},
    [1, 2],
    "rect",
    None,
    {"shape": "rect", "x": 0, "y": 0, "w": 0.009, "h": 0.5},
    {"shape": "rect", "x": 0, "y": 0, "w": 0.01, "h": 0.01},
    {"shape": "ellipse", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "soft": 0.9},
    {"shape": "ellipse", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "soft": -1},
    {"shape": "ellipse", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "soft": "abc"},
    {"shape": "rect", "x": float("inf"), "y": 0, "w": 0.5, "h": 0.5},
    {"shape": "rect", "x": float("nan"), "y": 0, "w": 0.5, "h": 0.5},
    {"shape": "rect", "x": 0.5, "y": 0.5, "w": "1e3", "h": 0.2},
    {"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": "0x1"},
    {"shape": "rect", "x": 0.33333333, "y": 0.66666666, "w": 0.33333334, "h": 0.33333334, "soft": 0.123456},
    {"shape": "rect", "x": 0.00005, "y": 0.99, "w": 0.5, "h": 0.5},
    {"shape": "ellipse", "x": 0.5, "y": 0.5, "w": 0.5, "h": 0.5, "soft": 0.25, "inv": "true"},
    # revue T4 (24/09, T4-4) : float() de Python lisait « 1_0 » (10) et les chiffres Unicode ; Number() de JS non
    {"shape": "rect", "x": 0, "y": 0, "w": "1_0", "h": 0.5},
    {"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": "٠.٥", "soft": "1_0"},
    # re-revue T6 (24/09) : Number() de JS ote U+FEFF (un blanc pour ECMAScript) ; str.strip() de Python non
    {"shape": "rect", "x": 0, "y": 0, "w": "﻿0.5", "h": 0.5},
]
PROBE = PROBE.replace("/*L5_MASKS*/", json.dumps(_L5_MASKS))
try:
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    from app.services.mask_region import mask_of as _py_mask_of
    _py_mask_err = ""
except Exception as _e:
    _py_mask_of, _py_mask_err = None, temoin(_e)
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
                 # D-15 (L3, tache 4) : les SEPT cles de la section [15]
                 # (cinq de la tache, deux de sa revue -- compte corrige 23/09/2026).
                 "rt_of","rt_rampe","rt_rampe_trans","rt_rampe_refus","rt_rampe_pur",
                 "rt_rampe_fine","rt_rampe_dz",
                 # D-16 (L3, tache 6) : les QUATRE cles de la section [16].
                 "sb_norm","sb_of","sb_state","sb_pur",
                 # D-14 (L3, tache 7) : les SEPT cles de la section [17].
                 "kf_lerp","kf_lerp_hors","kf_lerp_defaut","kf_lerp_desordre",
                 "kf_keep","kf_keep_absent","kf_pur",
                 # D-9 (L3, tache 9) : les SEPT cles de la section [18].
                 "aj_kind","aj_skin","aj_track","aj_new","aj_new_dur","aj_group","aj_pur",
                 # E-2 (lot E-B, tache 2) : les HUIT cles de la section [19].
                 "prov","chips","filtre","filtre_q","filtre_vide","filtre_bornes",
                 "drawer_pure","drawer_touche_x",
                 # E-5 (lot E-B, tache 4) : les CINQ cles du store du dernier rendu.
                 "finst","finst_of","finst_rm","finst_none","finst_bornes",
                 # E-8 (lot E-B, tache 6) : les DEUX cles de la largeur de l'inspecteur.
                 "insp","clamp",
                 # E-9 (lot E-B, tache 7) : les QUATRE cles de la hauteur de la timeline et du label de duree.
                 "tlh","tlh_bornes","durlbl","durlbl_bornes",
                 # D-7 (lot E-B, tache 8) : les CINQ cles de la mini-carte.
                 "mm","mm_vide","mm_bornes","mm_comp","mm_comp_leve",
                 # E-6 (lot E-C, tache 1) : les DIX cles de la section [20].
                 "combo","combo_bornes","combo_bundle","menu","menu_vide","menu_inconnu",
                 "menu_bornes","ctx_pure","ctx_leve","ctx_onclose",
                 # E-7 (lot E-C, tache 3) : les NEUF cles de la section [21].
                 "jt","jt_tous","jt_vide","jt_bornes","jt_pur","del_pure","del_leve","del_rendu","del_vide_liste",
                 # E-10 (lot E-C, tache 4) : la cle de la section [22].
                 "tbd",
                 # E-13 / E-14 (lot E-C, tache 5) : les SIX cles de la section [23].
                 "tete","tete_bornes","trou","trou_bornes","rip","rip_bornes","rip_autre",
                 # L4 (tache 4) : les QUINZE cles de la section [24].
                 "lp","opts","opts_bornes","opts_pur","pl","pl_absent","pl_bornes","pl_pur","st",
                 "dr_pure","dr_leve","dr_rendu","dr_vide","dr_absent","del_st",
                 # L7 D-10 (tache 1) : les QUATORZE cles de la section [25].
                 "kp_resolve","kp_inconnu","kp_pur","kx","kx_bornes","ki_ok","ki_combo","ki_casse","ki_v2","ki_vide","ki_aller_retour",
                 "ki_vol","ki_vol_preset","ki_vol_echange",
                 # L7 D-6 (tache 2) : les VINGT-ET-UNE cles de la section [26].
                 "cc","cc_pur","cc_bornes","cp_meme_piste","cp_inserer_fend","cp_ecraser","cp_piste_absente","cp_kind_prime",
                 "cp_genre_absent","cp_vide","cp_v0","cp_verrou","cp_mou","cp_sans_pistes","cp_head","cp_len0","cp_id_pris",
                 "cp_remplir","cp_remplir_srcdur","cp_pur","cp_menu",
                 # revue 24/09 : I-2, M-2, M-1
                 "cp_sans_source","cp_homonyme","cp_start","cp_start_refus",
                 # L7 D-8 (tache 3) : les SEIZE cles de la section [27].
                 "bo","bo_defaut","bo_def","bo_def_pur","bo_loin","bo_vide","bo_long_et_jump","bo_egal","bo_seuil",
                 "bo_contact","bo_sources","bo_v2","bo_vitesse","bo_desordre","bo_pur","bo_opts",
                 # L7 D-39 (tache 4) : les DOUZE cles de la section [28].
                 "df","df_id","df_vide","df_slip","df_piste","df_rogne_et_bouge","df_noms","df_cles","df_pur","df_temps",
                 "df_vue","df_vue_noms","df_tolerance",
                 # L7 D-3b (tache 4-bis) : les SEPT cles de la section [29].
                 "ab","ab_vitesse","ab_sans_srcin","ab_refus","ab_contact","ab_zero","ab_pur","abd",
                 # L7 D-19 (tache 5, client) : les CINQ cles de la section [30].
                 "ox","ox_rayon","ox_ombre","ox_mou","ox_pur",
                 # L7 D-22 (tache 6) : les DIX-NEUF cles de la section [31].
                 "sst","sst_bornes","sn","sn2","sn_place","sb","sb_defaut","sb_neuf","sb_bascule","bid",
                 "sc","sc_clips","sc_memes","sc_ids","sc_bornes","sc_pur","rm","rm_s1","tp",
                 # L7-B D-42 (tache 2) : les ONZE cles de la section [32] (ca_ecart : revue du 24/09).
                 "ca","ca_vitesse","ca_ids","ca_ids_pris","ca_bords","ca_refus","ca_un","ca_sans_src","ca_champs","ca_pur","ca_ecart",
                 # L7-B D-34 (tache 7) : les CINQ cles de la section [33].
                 "rn","rx","rx_bornes","rx_suite","rchips",
                 # L7-B D-40 (tache 4) : les QUINZE cles de la section [34] (rf_remplace : revue du 24/09 ; rf_gestes, rf_fenetre, rf_payload : revue finale).
                 "rf_modes","rf_suivi","rf_vitesse","rf_cap","rf_r3","rf_vide","rf_remplace","rf_gestes","rf_fenetre","rf_payload","rf_at","rf_k","rf_pos","rf_css","rf_pur",
                 # L7-B D-41 (tache 6) : les TREIZE cles de la section [35].
                 "ac_cle","ac_n","ac_base","ac_llm","ac_text","ac_persona","ac_confirm","ac_src","ac_pur","ac_usd","ac_est","ac_tr","ac_clip",
                 # revue T6 (24/09) : le plafond et la langue
                 "ac_max","ac_lang",
                 # cloture T8 (24/09) : l'estimation du 409 et le cadrage compare par D-39
                 "ac_409","df_reframe",
                 # L5 D-27 D-29 D-30 D-32 (tache 4, 24/09) : les SEIZE cles de la section [36].
                 "co_types","co_neutre","co_val","co_rt","co_from","co_set","co_clean","co_c20","co_parse","co_str",
                 "co_eval","co_mask","co_take","co_paste","co_cm","co_src",
                 # revue T4 (24/09) : grade sans effet eteint, vecteurs partages des courbes, masques croises
                 "co_paste_off","co_vec","co_maskx",
                 # L5 D-27 D-29 D-30 D-28 (tache 5, 24/09) : les DIX-HUIT cles de la section [37].
                 "gp_fx","gp_hit","gp_move","gp_add","gp_del","gp_mid","gp_prev","gp_match","gp_frame","gp_sig",
                 "gp_pure","gp_null","gp_box","gp_rendu","gp_verrou","gp_vide","gp_geste","gp_grade",
                 # L5 D-31 D-32 (tache 6, 24/09) : les NEUF cles de la section [38] (les gardes en execution ont leur shim a part).
                 "sc_at","sc_body","sc_store","lb_plans","lb_next","gc","sc_null","sc_rendu","lb_rendu",
                 # L6 D-25 D-26 (tache 4, 25/09) : les SIX cles de la section [39] ; + au_dx (revue T5, 25/09).
                 "au_lr","au_lr_note","au_dl","au_df","au_vo","au_rm","au_dx"]
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
print("\n[19] E-2 provenance, filtre et tiroir Medias (client)")
# la table DZM_PROV_LBL : seedance -> Studio, episode -> Chapitres, ugc -> Importes, null (lu seedance) -> Studio,
# un provider inconnu s'affiche tel quel (pas de « Autres » qui cacherait un nom)
check("prov_groupe_derive_du_provider_null_vaut_seedance_inconnu_tel_quel",
      D.get("prov") == ["Studio", "Chapitres", "Importés", "Studio", "zzz"], D.get("prov"))
# derivees des jobs recus, uniques (seedance+heygen+null = un seul Studio), « Tout » en tete, ordre d'apparition
check("prov_chips_derivees_uniques_tout_en_tete_ordre_d_apparition",
      D.get("chips") == ["Tout", "Studio", "Chapitres", "zzz"], D.get("chips"))
check("media_filtre_par_groupe", D.get("filtre") == ["Alpha"], D.get("filtre"))
check("media_filtre_q_insensible_a_la_casse", D.get("filtre_q") == ["Alpha"], D.get("filtre_q"))
check("media_filtre_liste_vide_rend_zero", "filtre_vide" in D and D["filtre_vide"] == 0, D.get("filtre_vide"))
# sans filtre -> 3 ; q lit le job_id quand le titre manque -> 1 ; un job null est ignore -> 1 ; l'entree n'est pas mutee ; chips sans job -> ["Tout"] x2
check("media_filtre_bornes_sans_filtre_job_id_null_ignore_pur_et_chips_vides",
      D.get("filtre_bornes") == [3, 1, 1, True, ["Tout"], ["Tout"]], D.get("filtre_bornes"))
check("media_drawer_est_une_fonction", D.get("drawer_pure") == "function", D.get("drawer_pure"))
check("media_drawer_touche_les_hooks_ferme_comme_ouvert_regle_des_hooks",
      D.get("drawer_touche_x") == ["leve", "leve", "leve"], D.get("drawer_touche_x"))
# LE COEUR RESTE PUR : le corps des trois fonctions pures ne contient ni `r.jsx` ni `x.use`.
# Lu dans la SOURCE en octets ; regex gardee par un temoin de longueur (un corps vide verdirait
# une negation creuse). Le composant, lui, DOIT porter les deux (temoin inverse).
_SRCb = globals().get("SRC") or ""
def _corps(nom):
    i = _SRCb.find("function " + nom + "(")
    if i < 0: return ""
    j = _SRCb.find("\nfunction ", i + 1); k = _SRCb.find("\nvar ", i + 1)
    fin = min([v for v in (j, k) if v >= 0] or [len(_SRCb)])
    return _SRCb[i:fin]
_PURS = {n: _corps(n) for n in ("dzmProvGroupe", "dzmProvChips", "dzmMediaFiltre")}
check("media_coeur_pur_les_trois_fonctions_ne_touchent_ni_r_ni_x",
      all(len(c) > 100 and not re.search(r"\br\.jsx|\bx\.use", c) for c in _PURS.values()),
      {n: len(c) for n, c in _PURS.items()})
_DRW = _corps("DzmMediaDrawer")
check("media_drawer_porte_hooks_jsx_fetch_jobs_video_strip_drag_et_le_formateur_de_duree_existant",
      len(_DRW) > 400 and _DRW.count("x.useState(") >= 4 and "r.jsx" in _DRW
      and '"/api/jobs?limit=' in _DRW and "video=1" in _DRW and "/api/montage/strip?src=" in _DRW
      and "dzmDurTxt(" in _DRW and "dragPayload(" in _DRW and 'className:"svm-medrow"' in _DRW
      and "dzmProvChips(" in _DRW and "dzmMediaFiltre(" in _DRW
      and _DRW.count("function dzmDur") == 0 and _DRW.count("function dzmTc") == 0,
      f"corps={len(_DRW)} o useState={_DRW.count('x.useState(')}")
# la regle des hooks : le `return null` du tiroir ferme vient APRES le premier useState
_iUS = _DRW.find("x.useState("); _iNul = _DRW.find("return null")
check("media_drawer_le_return_null_ferme_vient_apres_les_hooks",
      0 <= _iUS < _iNul, (_iUS, _iNul))
# les quatre exports sont en queue de DzTracks (T3 les lit sous ces noms)
# revue 23/09 : la couche juge TOUJOURS le statut (dzmIsVideoJob hors de toute condition sur o.exts) --
# le serveur `video=1` ne juge que l'extension ; un job en cours a video_path pose n'entre pas
check("media_drawer_applique_toujours_le_juge_de_statut_exts_facultatif",
      len(_DRW) > 400 and _DRW.count("dzmIsVideoJob(") == 1
      and "var vus=jobs.filter(function(j){return dzmIsVideoJob(j,o.exts)});" in _DRW
      and "o.exts&&o.exts.length?jobs.filter" not in _DRW,
      f"corps={len(_DRW)} o isVideoJob={_DRW.count('dzmIsVideoJob(')}")
_iDT = _SRCb.find("var DzTracks={")
_iFin = _SRCb.find("window.DzTracks=DzTracks;", _iDT) if _iDT >= 0 else -1
_DT = _SRCb[_iDT:_iFin] if 0 <= _iDT < _iFin else ""
check("media_exports_provGroupe_provChips_mediaFiltre_MediaDrawer_dans_DzTracks",
      _iFin > _iDT >= 0 and len(_DT) > 1000 and all(_DT.count(e) == 1 for e in
          ("provGroupe:dzmProvGroupe", "provChips:dzmProvChips", "mediaFiltre:dzmMediaFiltre", "MediaDrawer:DzmMediaDrawer")),
      len(_DT))
# ── E-5 (lot E-B, tache 4, 23/09/2026) : LE DERNIER RENDU FINAL PAR PROJET ──
# Aucun JobRecord ne porte de project_id (mesure routes.py:3330) : la memoire
# est cote client, un store {pid:{job_id,name,at}} que l'hote lit/ecrit dans
# localStorage["dz_montage_lastfin"]. Ici DEUX fonctions PURES : finStore rend
# un objet NEUF (pose ou retrait), finOf lit l'entree ou null.
check("fin_store_pose_l_entree_du_projet",
      D.get("finst") == {"p1": {"job_id": "j", "name": "n", "at": 1}}, D.get("finst"))
check("fin_of_rend_l_entree_du_projet",
      D.get("finst_of") == {"job_id": "j", "name": "n", "at": 1}, D.get("finst_of"))
check("fin_store_null_retire_la_cle", "finst_rm" in D and D["finst_rm"] == {}, D.get("finst_rm"))
check("fin_of_rend_null_sans_entree", "finst_none" in D and D["finst_none"] is None, D.get("finst_none"))
# pid vide -> "_" ; store non-objet -> {} puis pose ; objet neuf sans muter l'entree ; finOf("")
# lit "_" ; store null -> null ; entree sans job_id -> null ; le retrait garde les voisines
check("fin_store_bornes_pid_vide_store_non_objet_objet_neuf_et_voisines",
      D.get("finst_bornes") == [["_"], "k", True, {"job_id": "u", "name": "", "at": 0}, None, None, ["b"]],
      D.get("finst_bornes"))
# LE COEUR RESTE PUR : ni r.jsx, ni x.use, ni localStorage dans les deux corps (temoin de longueur).
_FINS = {n: _corps(n) for n in ("dzmFinStore", "dzmFinOf")}
check("fin_coeur_pur_ni_r_ni_x_ni_localStorage",
      all(len(c) > 100 and not re.search(r"\br\.jsx|\bx\.use|localStorage", c) for c in _FINS.values()),
      {n: len(c) for n, c in _FINS.items()})
check("fin_exports_finStore_finOf_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("finStore:dzmFinStore") == 1 and _DT.count("finOf:dzmFinOf") == 1,
      len(_DT))
# ── E-11 (lot E-B, tache 5, 23/09/2026) : LE BANDEAU ARRETE LE CLIC ─────
# Le voile (.svm-modescrim, bundle EB5a) se ferme au clic ; la racine du
# bandeau .svm-pop dzm-fin porte le meme stopPropagation que le popover du
# bundle (EB5b) et que kbPanel. Temoin : corps > 400 o, UN seul stopPropagation.
_FBB = _corps("DzmFinBandeau")
check("fin_bandeau_arrete_le_clic_sur_sa_racine_svm_pop",
      len(_FBB) > 400 and _FBB.count('className:"svm-pop dzm-fin",onClick:function(e){e.stopPropagation()},children:[') == 1
      and _FBB.count("stopPropagation") == 1 and _FBB.count("svm-modescrim") == 0,
      f"corps={len(_FBB)} o stop={_FBB.count('stopPropagation')}")
# ── E-8 (lot E-B, tache 6, 23/09/2026) : LA LARGEUR DE L'INSPECTEUR ──────
# L'hote (EB6b) lit localStorage["dz_svm_insp"].w et la poignee (EB6a) pose
# startW+(startX-clientX) : les deux passent par inspW, qui borne 260..480 et
# rend 300 sur tout ce qui n'est pas un nombre fini (JSON corrompu, cle
# absente). Le clamp est la fonction generale (NaN / non fini / vide -> def).
check("insp_w_borne_260_480_defaut_300_sur_null_vide_et_non_numerique",
      D.get("insp") == [480, 300, 261, 300, 300, 300, 260, 480, 300], D.get("insp"))
# le clamp : dans les bornes tel quel, hors bornes la borne, NaN / ±Infinity / vide / objet -> def,
# une chaine numerique est lue, les bornes elles-memes sont dedans
check("clamp_bornes_nan_infini_vide_objet_rendent_le_defaut",
      D.get("clamp") == [5, 0, 10, 7, 7, 7, 3, 7, 7, 0, 10], D.get("clamp"))
# LE COEUR RESTE PUR : ni r.jsx, ni x.use, ni localStorage, ni window dans les deux corps (temoin de longueur) ;
# inspW APPELLE clamp (une seule ecriture des bornes) et porte les trois nombres 260 / 480 / 300.
_INS = {n: _corps(n) for n in ("dzmClamp", "dzmInspW")}
check("insp_coeur_pur_et_inspW_passe_par_clamp_avec_260_480_300",
      all(len(c) > 60 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b", c) for c in _INS.values())
      and _INS["dzmInspW"].count("dzmClamp(") == 1 and all(k in _INS["dzmInspW"] for k in ("260", "480", "300"))
      and _INS["dzmClamp"].count("dzmClamp(") == 1,  # sa declaration seule : pas de recursion
      {n: len(c) for n, c in _INS.items()})
check("insp_exports_clamp_inspW_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("clamp:dzmClamp,inspW:dzmInspW,") == 1, len(_DT))
# ── E-9 (lot E-B, tache 7, 23/09/2026) : LA HAUTEUR DE LA TIMELINE ET LA DUREE SUR LES CLIPS ──
# L'hote (EB7a, repli R_EB6B) lit localStorage["dz_svm_tlh"] au montage et la
# poignee (EB7b) pose startH+(startY-clientY) : les deux passent par tlH, qui
# borne 30..70 % du total (.dzsvm.clientHeight) et rend null -- « aucun choix »,
# le plafond historique max-height:48vh reste -- sur tout ce qui n'est pas un
# nombre fini ou quand le total est inconnu (<= 0, non fini).
check("tlh_borne_30_70_pour_cent_du_total_arrondi_null_sans_choix_ou_sans_total",
      D.get("tlh") == [300, 700, None, None, 500, 650], D.get("tlh"))
check("tlh_bornes_null_undefined_nan_infini_booleen_total_negatif_null_ou_non_fini_et_les_bornes_elles_memes",
      D.get("tlh_bornes") == [None, None, None, None, None, None, None, None, None, None, 300, 700], D.get("tlh_bornes"))
# le label : « a · 0:06 » par svmRuler (format m:ss du bundle, extrait ici), le label seul
# quand la chip est eteinte ou que la duree est nulle (end <= start)
check("durlbl_ajoute_la_duree_m_ss_quand_la_chip_est_allumee_label_seul_sinon_ou_sans_duree",
      D.get("durlbl") == ["a · 0:06", "a", "a"], D.get("durlbl"))
# end < start -> label ; 65 s -> 1:05 ; 6,4 s -> 0:06 (arrondi du formateur) ; 125 -> 2:05 ; chaines lues ;
# NaN / null -> label ; label vide -> la duree seule (pas « · 0:06 » orphelin)
check("durlbl_bornes_end_avant_start_minutes_arrondi_chaines_nan_null_et_label_vide",
      D.get("durlbl_bornes") == ["a", "a · 1:05", "a · 0:06", "a · 2:05", "a · 0:06", "a", "a", "0:06"], D.get("durlbl_bornes"))
# LE COEUR RESTE PUR : ni r.jsx, ni x.use, ni localStorage, ni window, ni document dans les deux corps
# (temoin de longueur) ; tlH APPELLE clamp (une seule ecriture des bornes) et porte .3 / .7 ; durLbl
# APPELLE dzmDurTxt (le formateur EXISTANT, qui appelle svmRuler du bundle) -- AUCUN second formateur :
# la source ne declare qu'UN `function dzmDurTxt(` (temoin) et aucun `function dzmTc` / `dzmRuler` / `dzmMmss`.
_TLH = {n: _corps(n) for n in ("dzmTlH", "dzmDurLbl")}
check("tlh_durlbl_coeur_pur_tlH_passe_par_clamp_durLbl_par_dzmDurTxt_aucun_second_formateur",
      all(len(c) > 60 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b", c) for c in _TLH.values())
      and _TLH["dzmTlH"].count("dzmClamp(") == 1 and ".3*" in _TLH["dzmTlH"] and ".7*" in _TLH["dzmTlH"]
      and _TLH["dzmDurLbl"].count("dzmDurTxt(") == 1 and "svmRuler" not in _TLH["dzmDurLbl"]
      and _SRCb.count("function dzmDurTxt(") == 1 and _SRCb.count("svmRuler(") >= 1
      and all(_SRCb.count(k) == 0 for k in ("function dzmTc", "function dzmRuler", "function dzmMmss", "function dzmPad")),
      {n: len(c) for n, c in _TLH.items()})
check("tlh_durlbl_exports_tlH_durLbl_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("tlH:dzmTlH,durLbl:dzmDurLbl,") == 1, len(_DT))
# le formateur du bundle a bien ete EXTRAIT (sinon durLbl(...,true) aurait leve et le pin d'au-dessus l'aurait dit)
check("tlh_le_shim_joue_svmRuler_et_svmPad2_extraits_du_bak_montage",
      _E9_RULER.count("function svmRuler(") == 1 and _E9_RULER.count("function svmPad2(") == 1
      and _E9_RULER in PROBE and "/*E9_RULER*/" not in PROBE, len(_E9_RULER))
# ── D-7 (lot E-B, tache 8, 23/09/2026) : LA MINI-CARTE DE LA TIMELINE ──
# dzmMinimap(clips, tracks, dur) est PURE : lignes = pistes dans l'ordre recu
# (id, genre par dzmKindOf), rectangles en FRACTIONS [0,1] de la duree (start/dur,
# end/dur bornes) ; le troisieme clip (25..30 sur 20 s) est HORS duree -> exclu.
# Le clic-centrer vit dans l'hote (seul detenteur de tlScrollRef), pas ici.
check("mm_deux_pistes_trois_clips_rendent_deux_lignes_et_deux_rects_en_fractions_exactes_le_troisieme_hors_duree_exclu",
      D.get("mm") == {"rows": [{"id": "v1", "kind": "video"}, {"id": "a1", "kind": "audio"}],
                      "rects": [{"tr": "v1", "row": 0, "x0": 0.1, "x1": 0.3, "kind": "video"},
                                {"tr": "a1", "row": 1, "x0": 0.0, "x1": 1.0, "kind": "audio"}]},
      D.get("mm"))
# etat vide : listes vides, dur 0 / negatif / NaN / Infinity, clips non-tableau, pistes non-tableau -> {rows:[],rects:[]} x7
check("mm_etat_vide_dur_nul_negatif_nan_infini_ou_entrees_non_tableaux_rendent_rows_et_rects_vides",
      isinstance(D.get("mm_vide"), list) and len(D["mm_vide"]) == 7
      and all(v == {"rows": [], "rects": []} for v in D["mm_vide"]), D.get("mm_vide"))
# bornes : x1 borne a 1 (15..30 sur 20), x0 borne a 0 (-5..5), end == start ignore, piste inconnue ignoree, clip null
# ignore, piste dupliquee = UNE ligne (2 lignes pour 3 entrees), chaines lues ("4"/"8" -> .2/.4), genre a1 -> audio, entrees non mutees
check("mm_bornes_x1_a_1_x0_a_0_duree_nulle_piste_inconnue_clip_null_ignores_piste_dupliquee_une_ligne_chaines_lues_pur",
      D.get("mm_bornes") == [2, [["v1", 0, 0.75, 1, "video"], ["v1", 0, 0, 0.25, "video"], ["a1", 1, 0.2, 0.4, "audio"]], True, ["video", "audio"]],
      D.get("mm_bornes"))
check("mm_composant_est_une_fonction_qui_touche_r_a_l_appel_props_null_vides_ou_pleines",
      D.get("mm_comp") == "function" and D.get("mm_comp_leve") == ["r.jsx", "r.jsx", "r.jsx"],
      (D.get("mm_comp"), D.get("mm_comp_leve")))
# LE COEUR RESTE PUR : ni r.jsx, ni x.use, ni localStorage/window/document dans dzmMinimap (temoin de longueur) ;
# il lit le genre par dzmKindOf (la table EXISTANTE, une fois) et le champ `tr` ; le composant, lui, porte r.jsx,
# svm-minimap / svm-mmrow / svm-mmrect / svm-mmview, data-kind, pointer-events par la feuille (pas de onClick sur
# la fenetre), onSeek borne 0..1 par getBoundingClientRect, et APPELLE dzmMinimap (une seule geometrie).
_MM = {n: _corps(n) for n in ("dzmMinimap", "DzmMinimap")}
check("mm_coeur_pur_par_kindOf_et_tr_le_composant_appelle_minimap_et_porte_les_quatre_classes_et_onSeek_borne",
      all(len(c) > 200 for c in _MM.values())
      and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b", _MM["dzmMinimap"])
      and _MM["dzmMinimap"].count("dzmKindOf(") == 1 and "c.tr" in _MM["dzmMinimap"] and "c.track" not in _MM["dzmMinimap"]
      and _MM["DzmMinimap"].count("dzmMinimap(") == 1 and "r.jsx" in _MM["DzmMinimap"] and "x.use" not in _MM["DzmMinimap"]
      and all(_MM["DzmMinimap"].count('className:"' + k + '"') == 1 for k in ("svm-minimap", "svm-mmrow", "svm-mmrect", "svm-mmview"))
      and _MM["DzmMinimap"].count('"data-kind":') == 1 and _MM["DzmMinimap"].count("getBoundingClientRect()") == 1
      and _MM["DzmMinimap"].count("Math.max(0,Math.min(1,") >= 1 and "onSeek" in _MM["DzmMinimap"]
      and _MM["DzmMinimap"].count("Mini-carte") == 1,
      {n: len(c) for n, c in _MM.items()})
check("mm_exports_minimap_Minimap_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("minimap:dzmMinimap,Minimap:DzmMinimap,") == 1, len(_DT))
print("\n[20] E-6 combo -> touche, modele de menu, DzmCtxMenu (lot E-C, tache 1)")
# ── E-6 (lot E-C, tache 1, 23/09/2026) : LE MENU ─────────────────────────
# Decision 1 du plan : pas de dispatch(id) -- l'hote REJOUE la combo d'une
# action par un KeyboardEvent synthetique ; dzmComboToKey traduit la combo de
# SVM_ACTIONS en KeyboardEventInit {key,ctrlKey,shiftKey,altKey,metaKey} :
# lettre -> minuscule, Maj -> shiftKey, Suppr -> "Delete", fleche -> "Arrow*",
# vide -> null (une entree sans raccourci ne rejoue rien).
_F, _T = False, True
check("combo_six_cas_lettre_minuscule_maj_shift_suppr_delete_vide_null_fleche_arrow",
      D.get("combo") == [{"key": "c", "ctrlKey": _F, "shiftKey": _F, "altKey": _T, "metaKey": _F},
                         {"key": "x", "ctrlKey": _T, "shiftKey": _T, "altKey": _F, "metaKey": _F},
                         {"key": "Delete", "ctrlKey": _F, "shiftKey": _F, "altKey": _F, "metaKey": _F},
                         {"key": "m", "ctrlKey": _F, "shiftKey": _T, "altKey": _F, "metaKey": _F},
                         None,
                         {"key": "ArrowLeft", "ctrlKey": _T, "shiftKey": _F, "altKey": _F, "metaKey": _F}],
      D.get("combo"))
# null / nombre -> null ; Echap / Espace / Entree / Home / End / ? ; Cmd -> meta ; « Ctrl+ » sans touche -> null ; espaces ; =
check("combo_bornes_null_nombre_echap_espace_entree_home_end_point_d_interrogation_cmd_inconnu_null_modificateur_seul_null_espaces_egal",
      D.get("combo_bornes") == [None, None, ["Escape", _F, _F, _F, _F], [" ", _F, _F, _F, _F], ["Enter", _F, _F, _F, _F],
                                ["Home", _F, _F, _F, _F], ["End", _F, _F, _F, _F], ["?", _F, _F, _F, _F],
                                None, None, ["z", _F, _T, _F, _F], ["=", _T, _F, _F, _F]],
      D.get("combo_bornes"))
# TOUTES les combos reelles du bundle patche sont parsables : liste extraite (temoin >= 20, placeholder consomme,
# 47 mesurees le 23/09), aucune ne rend null, chaque resultat porte les cinq cles
_cb = D.get("combo_bundle")
check("combo_toutes_les_combos_du_bundle_patche_sont_parsables_temoin_au_moins_20_extraites_par_regex_gardee",
      len(_EC_COMBOS) >= 20 and all(c for c in _EC_COMBOS) and "/*EC_COMBOS*/" not in PROBE
      and json.dumps(_EC_COMBOS, ensure_ascii=False) in PROBE
      and isinstance(_cb, list) and len(_cb) == 3 and _cb[0] == len(_EC_COMBOS) and _cb[1] == [] and _cb[2] == 0,
      (len(_EC_COMBOS), _cb))
# Decision 2 : six rubriques (Projet, Edition, Timeline, Marqueurs, Affichage, Aide) != les quatre `sec` :
# table DZM_MENU_RUB pour les ids connus, repli sur sec (Audio -> Edition, Affichage -> Affichage, sinon Timeline),
# ordre fixe, vides omises ; le libelle de combo vient de keyLabel(id) quand il rend non vide, sinon de la table
check("menu_cinq_actions_quatre_rubriques_dans_l_ordre_fixe_vides_omises_keyLabel_prioritaire",
      D.get("menu") == [["Édition", ["undo:Ctrl+Z", "gain_up:Alt+↑"]], ["Timeline", ["blade:Alt+C*"]],
                        ["Marqueurs", ["marker_toggle:Maj+M"]], ["Affichage", ["zoom_in:Ctrl+="]]],
      D.get("menu"))
check("menu_vide_rend_zero_rubrique", "menu_vide" in D and D["menu_vide"] == 0, D.get("menu_vide"))
# revue 23/09 : zza / zzf sont ABSENTS de la table -> seuls les replis Audio -> Edition et Affichage -> Affichage les placent
check("menu_sec_inconnue_timeline_ids_inconnus_audio_edition_affichage_affichage_non_objets_ignores_keyLabel_vide_repli_table",
      D.get("menu_inconnu") == [["Édition", ["mute:m:M", "zza:za:1"]], ["Timeline", ["zzz:z:Q", "nolbl::"]],
                                ["Affichage", ["fullscreen:f:F", "zzf:zf:2"]], ["Aide", ["keys_panel:k:?"]]],
      D.get("menu_inconnu"))
check("menu_bornes_null_et_non_tableau_rendent_vide_sans_keyLabel_la_table_entree_non_mutee",
      D.get("menu_bornes") == [0, 0, ["Édition/Ctrl+Z"], True], D.get("menu_bornes"))
# Decision 3 : UN composant DzmCtxMenu sert le menu principal et les deux menus contextuels ;
# il lit r a l'appel (TypeError r.jsx dans ce shim, comme la mini-carte) sur props null / vides / items / rubs
check("ctx_composant_est_une_fonction_qui_touche_r_a_l_appel_props_null_vides_items_ou_rubs",
      D.get("ctx_pure") == "function" and D.get("ctx_leve") == ["r.jsx", "r.jsx", "r.jsx", "r.jsx"],
      (D.get("ctx_pure"), D.get("ctx_leve")))
# revue 23/09 : run qui leve -> onClose appele quand meme (finally) puis l'erreur remonte ; run sain -> run puis onClose
check("ctx_le_clic_appelle_onClose_meme_quand_run_leve_puis_relance_l_erreur",
      D.get("ctx_onclose") == [2, "div", "svm-pop svm-menu", ["close", "leve:boom", "run", "close"]], D.get("ctx_onclose"))
# LE COEUR RESTE PUR : ni r.jsx, ni x.use, ni window/document/localStorage dans les trois corps purs (temoin de longueur) ;
# comboToKey ne lit la table des jetons qu'une fois et connait Delete/Escape/Arrow* ; menuModel lit DZM_MENU_ORDRE et
# dzmMenuRub (une seule ecriture du repli) ; la table porte les quatre marqueurs, keys_panel -> Aide, undo -> Edition
_EC = {n: _corps(n) for n in ("dzmComboToKey", "dzmMenuRub", "dzmMenuModel")}
_iRub = _SRCb.find("var DZM_MENU_RUB={"); _iRubF = _SRCb.find("};", _iRub) if _iRub >= 0 else -1
_RUB = _SRCb[_iRub:_iRubF] if 0 <= _iRub < _iRubF else ""
_RUB_IDS = re.findall(r"(\w+):\"", _RUB)
check("ec_coeur_pur_les_trois_fonctions_ne_touchent_ni_r_ni_x_ni_window_et_la_table_est_ecrite_une_fois",
      all(len(c) > 80 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b", c) for c in _EC.values())
      and _EC["dzmComboToKey"].count("DZM_KEY_TOK[") == 1 and all('"' + k + '"' in _SRCb[_SRCb.find("var DZM_KEY_TOK="):_iRub]
          for k in ("Delete", "Escape", "Enter", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"))
      and _EC["dzmMenuModel"].count("dzmMenuRub(") == 1 and _EC["dzmMenuModel"].count("DZM_MENU_ORDRE") == 1
      and _EC["dzmMenuRub"].count("DZM_MENU_RUB[") == 1 and _EC["dzmMenuRub"].count('"Timeline"') == 1
      and _SRCb.count('var DZM_MENU_ORDRE=["Projet","Édition","Timeline","Marqueurs","Affichage","Aide"];') == 1
      and len(_RUB_IDS) >= 20 and all(_RUB.count(k + ':"Marqueurs"') == 1 for k in ("marker_toggle", "marker_prev", "marker_next", "marker_index"))
      and _RUB.count('keys_panel:"Aide"') == 1 and _RUB.count('undo:"Édition"') == 1 and _RUB.count('zoom_in:"Affichage"') == 1
      and _RUB.count('"Projet"') == 0,
      ({n: len(c) for n, c in _EC.items()}, len(_RUB_IDS)))
# banc croise : chaque id de DZM_MENU_RUB EXISTE dans la table SVM_ACTIONS du bundle patche (temoin >= 20 ids lus)
check("ec_chaque_id_de_la_table_des_rubriques_existe_dans_SVM_ACTIONS_du_bundle_patche",
      len(_EC_IDS) >= 20 and len(_RUB_IDS) >= 20 and all(i in _EC_IDS for i in _RUB_IDS),
      (len(_EC_IDS), [i for i in _RUB_IDS if i not in _EC_IDS]))
# le composant : div.svm-pop.svm-menu role menu, racine stopPropagation (UN seul), en-tete svm-menurub, separateur
# svm-menusep, button.svm-menuitem role menuitem disabled:!!it.off title:it.lbl, span svm-menukey, clic -> run puis onClose,
# position bornee a la fenetre LUE A L'APPEL (typeof window, repli) : aucun hook, aucun useState
_CTX = _corps("DzmCtxMenu")
check("ctx_porte_svm_pop_svm_menu_role_menu_stop_unique_rub_sep_item_disabled_title_key_run_puis_onClose_fenetre_a_l_appel_sans_hook",
      len(_CTX) > 500 and "r.jsx" in _CTX and "x.use" not in _CTX
      and _CTX.count('className:"svm-pop svm-menu",role:"menu",onClick:function(e){e.stopPropagation()}') == 1
      and _CTX.count("stopPropagation") == 1
      and all(_CTX.count('className:"' + k + '"') == 1 for k in ("svm-menurub", "svm-menusep", "svm-menuitem", "svm-menukey"))
      and _CTX.count('role:"menuitem",disabled:!!it.off,title:it.lbl') == 1
      and _CTX.count("onClick:function(){try{it.run&&it.run()}finally{o.onClose&&o.onClose()}}") == 1
      and _CTX.count("typeof window") == 2 and _CTX.count("innerWidth") == 1 and _CTX.count("innerHeight") == 1
      and _CTX.count("-270") == 1 and _CTX.count("40*n") == 1 and "Math.max(0,Math.min(" in _CTX
      and "o.rubs" in _CTX and "o.items" in _CTX,
      f"corps={len(_CTX)} o stop={_CTX.count('stopPropagation')}")
check("ec_exports_comboToKey_menuModel_CtxMenu_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("comboToKey:dzmComboToKey,menuModel:dzmMenuModel,CtxMenu:DzmCtxMenu,") == 1, len(_DT))
print("\n[21] E-7 tri des rendus par titre et vue Livraison (lot E-C, tache 3)")
# ── E-7 (lot E-C, tache 3, 23/09/2026) : LA VUE LIVRAISON ─────────────────
# Decision 4 du plan : l'historique d'un projet est lu de GET /api/jobs?providers=montage&q=<nom>
# et trie PAR TITRE (aucun project_id en base) : finals / apercus separes par le suffixe
# « (aperçu 480p) » que montage_service pose ; ordre recu conserve.
check("jt_deux_finals_un_apercu_l_autre_projet_et_le_job_non_montage_exclus_ordre_recu",
      D.get("jt") == [["a", "e"], ["b"]], D.get("jt"))
check("jt_nom_vide_prend_tous_les_jobs_montage_finals_puis_apercus",
      D.get("jt_tous") == [["a", "c", "e"], ["b"]], D.get("jt_tous"))
check("jt_etat_vide_deux_listes_vides", D.get("jt_vide") == [0, 0], D.get("jt_vide"))
check("jt_bornes_null_chaine_non_objets_ignores_nom_null_tous_prefixe_court_prolonge_prefixe_faux_rien",
      D.get("jt_bornes") == [0, 0, 1, 3, 2, 0], D.get("jt_bornes"))
check("jt_ne_mute_pas_l_entree", D.get("jt_pur") is True, D.get("jt_pur"))
check("del_composant_fonction_qui_touche_r_a_l_appel_props_null_vides_pleines",
      D.get("del_pure") == "function" and D.get("del_leve") == ["r.jsx", "r.jsx", "r.jsx"],
      (D.get("del_pure"), D.get("del_leve")))
# rendu factice : finals PUIS apercus, badge final/apercu, duree 1:05 par svmRuler du bundle, Publier grise ne publie pas
check("del_rendu_racine_titre_trois_boutons_titres_dernier_aucun_rangees_finals_puis_apercus_badge_duree_bibliotheque_clics",
      D.get("del_rendu") == ["div", "svm-deliver", "Livraison",
                             [["svm-secbtn", True, False], ["svm-goldbtn", True, False], ["svm-secbtn", True, True]],
                             "Dernier rendu final : aucun",
                             [["svm-delrow", "final", "final", "1:05"], ["svm-delrow", "final", "final", ""],
                              ["svm-delrow", "preview", "aperçu", ""]],
                             "Voir dans la Bibliothèque", ["preview", "render", "lib"]],
      D.get("del_rendu"))
check("del_liste_vide_svm_delempty_publier_actif_publie_dernier_rendu_nomme",
      D.get("del_vide_liste") == ["svm-delempty", False, "Dernier rendu final : preuve e3 · ", ["publish"]],
      D.get("del_vide_liste"))
# LE COEUR RESTE PUR (jobsTri sans r/x/window), le composant SANS hook (pas de x.use : le fetch est dans l'hote),
# une seule ecriture du suffixe, IDENTIQUE a celui de montage_service (jamais recopie a la main), duree par dzmDurTxt
_E7 = {n: _corps(n) for n in ("dzmJobsTri", "DzmDeliver")}
_MSV = ""
try:
    with open(os.path.join(ROOT, "backend", "app", "services", "montage_service.py"), "rb") as _fh: _MSV = _fh.read().decode("utf-8", "replace")
except OSError: pass
check("e7_jobsTri_pur_Deliver_sans_hook_suffixe_unique_egal_a_montage_service_duree_par_dzmDurTxt",
      len(_E7["dzmJobsTri"]) > 150 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b", _E7["dzmJobsTri"])
      and _E7["dzmJobsTri"].count("DZM_DEL_APERCU") == 1 and _E7["dzmJobsTri"].count('j.provider!=="montage"') == 1
      and len(_E7["DzmDeliver"]) > 800 and "r.jsx" in _E7["DzmDeliver"] and "x.use" not in _E7["DzmDeliver"] and "fetch(" not in _E7["DzmDeliver"]
      and all(_E7["DzmDeliver"].count('className:"' + k + '"') == 1 for k in ("svm-deliver", "svm-delrow", "svm-delbadge", "svm-dellast", "svm-delempty"))
      and _E7["DzmDeliver"].count("dzmDurTxt(") == 1 and _E7["DzmDeliver"].count('className:"svm-goldbtn"') == 1 and _E7["DzmDeliver"].count('className:"svm-secbtn"') == 3
      and _E7["DzmDeliver"].count("title:") == 4 and _E7["DzmDeliver"].count("if(o.publishOn&&o.onPublish)o.onPublish()") == 1
      and _SRCb.count('var DZM_DEL_APERCU="(aperçu 480p)";') == 1 and len(_MSV) > 1000 and _MSV.count('" (aperçu 480p)"') == 1,
      ({n: len(c) for n, c in _E7.items()}, _MSV.count('" (aperçu 480p)"')))
check("e7_exports_jobsTri_Deliver_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("jobsTri:dzmJobsTri,Deliver:DzmDeliver,") == 1, len(_DT))
print("\n[22] E-10 la barre d'outils ancree : prop docked -> data-docked (lot E-C, tache 4)")
# ── E-10 (lot E-C, tache 4, 23/09/2026) : LA BARRE ANCREE ───────────────────
# Decision 5 du plan : `docked` = une PROP du Dock (l'etat vit dans l'hote, cle
# dz_svm_tb_dock), posee en `data-docked:""` sur .dzm-tbar ; la feuille fait le
# reste (position:static, en flux dans .svm-trans). DECISION mesuree 23/09 (le
# plan laissait le choix) : `data-off` GARDE SON SENS ancree -- l'onglet OUTILS
# replie la barre ancree a zero largeur (feuille), le pin §4.2 du banc bundle
# interdisant de masquer un noeud de la barre ; l'onglet ne recoit donc AUCUNE
# prop neuve (temoin : `docked` passe a l'onglet n'y pose rien).
check("tbd_docked_true_pose_data_docked_vide_sur_la_barre_sans_la_prop_ou_non_booleen_undefined_data_off_intact_onglet_intouche",
      D.get("tbd") == ["", None, "", "", None, False, "div", "dzm-tbar", "dzm-toolbar", None, "dzm-tbtab", "true"],
      D.get("tbd"))
_E10 = {n: _corps(n) for n in ("DzmToolBar", "DzmToolTab", "DzmToolDock")}
check("e10_data_docked_ecrit_une_fois_dans_la_barre_strict_true_jamais_dans_l_onglet_et_le_dock_passe_docked_a_la_barre_seule",
      len(_E10["DzmToolBar"]) > 800 and _E10["DzmToolBar"].count('"data-docked":o.docked===!0?"":void 0') == 1
      and len(_E10["DzmToolTab"]) > 300 and "docked" not in _E10["DzmToolTab"]
      and len(_E10["DzmToolDock"]) > 2000 and _E10["DzmToolDock"].count("docked:o.docked") == 1
      and _E10["DzmToolDock"].count("DzmToolTab({open:open,onToggle:bascule,") == 1
      and _E10["DzmToolDock"].count("DzmToolBar({open:open,docked:o.docked,") == 1
      and _SRCb.count('"data-docked"') == 1 and _SRCb.count("docked:o.docked") == 1
      # revue 23/09 : ANCREE, la poignee est inerte -- saisir (pointeur) ET clavier (fleches) sortent en tete ; x2 dans le Dock
      and _E10["DzmToolDock"].count("if(o.docked===!0)return;") == 2 and _SRCb.count("if(o.docked===!0)return;") == 2
      and re.search(r"function saisir\(e\)\{[^}]{0,400}if\(o\.docked===!0\)return;", _E10["DzmToolDock"], re.S) is not None
      and re.search(r"function clavier\(e\)\{\r?\n\s*if\(o\.docked===!0\)return;", _E10["DzmToolDock"]) is not None  # la couche est en CRLF
      and _E10["DzmToolDock"].count("onGrab:saisir") == 1 and _E10["DzmToolDock"].count("onGripKey:clavier") == 1
      # temoin : les trois attributs d'etat de la barre restent poses a cote, une fois chacun
      and _E10["DzmToolBar"].count('"data-off":open?void 0:""') == 1 and _E10["DzmToolBar"].count('"data-drag":o.drag===!0?"":void 0') == 1,
      ({n: len(c) for n, c in _E10.items()}, _SRCb.count('"data-docked"')))

print("\n[23] E-13 la tete dans l'inspecteur et E-14 le trou selectionne (lot E-C, tache 5)")
# ── E-13 / E-14 (lot E-C, tache 5, 23/09/2026) ─────────────────────────────
# Decisions 7 et 8 du plan : teteTxt REUTILISE le formateur de l'hote (svmTcFF,
# HH:MM:SS:FF a 30 i/s -- pas de « ·ii ») ; l'intervalle du plan est FERME-OUVERT
# (ph == end : « hors du plan ») ; la queue de piste N'EST PAS un trou (aucun
# clip suivant -> null), un trou < 0,05 s non plus ; le ripple ne touche QUE la
# piste du trou (ecart date : le jumeau A1 ne suit pas, comme D-4).
check("tete_dans_le_plan_hors_a_la_borne_end_sans_sel_au_debut",
      D.get("tete") == ["tête à F2 · +F2 dans le plan", "tête à F5 · hors du plan", "tête à F4 · hors du plan",
                        "tête à F5", "tête à F0 · +F0 dans le plan"], D.get("tete"))
check("tete_bornes_ph_non_fini_vide_fmt_absent_arrondi_centieme_sel_non_numerique_ignore",
      D.get("tete_bornes") == ["", "", "", "tête à 2.46", "tête à F2", ""], D.get("tete_bornes"))
check("trou_entre_deux_clips_a_la_borne_en_tete_dans_un_clip_en_queue_autre_piste_ignoree_moins_de_5_centiemes",
      D.get("trou") == [{"a": 4, "b": 6}, {"a": 4, "b": 6}, {"a": 0, "b": 6}, None, None, {"a": 0, "b": 5}, None, None, {"a": 4, "b": 6}],
      D.get("trou"))
check("trou_bornes_clips_null_chaine_t_nan_piste_null_inconnue_null_entrees_non_objets_ignorees",
      D.get("trou_bornes") == [None, None, None, None, None, {"a": 4, "b": 6}], D.get("trou_bornes"))
check("ripple_decale_les_clips_de_la_piste_apres_le_trou_seulement_ordre_conserve_autres_pistes_intactes",
      D.get("rip") == [["a", "v1", 0, 4], ["c", "v1", 6, 8], ["b", "v1", 4, 6], ["n", "a1", 0, 10], ["o", "v2", 5, 9]],
      D.get("rip"))
check("ripple_nouveau_tableau_entree_non_mutee_src_conserve_clip_immobile_identique_bornes_copie_identique_null_vide",
      D.get("rip_bornes") == [True, True, True, True, True, True, True, 0], D.get("rip_bornes"))
# revue T7 (cloture) : le clip d'une AUTRE piste qui commence apres le trou reste en place -- le seul cas qui distingue
# « la piste du trou seule » de « toutes les pistes » (dans _g, aucun clip d'une autre piste ne commence apres b)
check("ripple_revue_t7_une_autre_piste_dont_le_clip_commence_apres_le_trou_ne_bouge_pas",
      D.get("rip_autre") == [["a", "v1", 0, 4], ["z", "v2", 7, 9]], D.get("rip_autre"))
# LE COEUR RESTE PUR : ni r.jsx, ni x.use, ni window/document/localStorage ; le formateur n'est JAMAIS recopie
# (aucun « 30 » ni « svmTcFF » dans teteTxt : il vient de l'hote) ; exports x1 chacun dans DzTracks.
_E13 = {n: _corps(n) for n in ("dzmTeteTxt", "dzmTrou", "dzmTrouRipple")}
check("e13_e14_coeur_pur_formateur_passe_et_non_recopie_intervalle_ferme_ouvert_seuil_5_centiemes_exports_x1",
      all(len(c) > 120 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b", c) for c in _E13.values())
      and "svmTcFF" not in _E13["dzmTeteTxt"] and "30" not in _E13["dzmTeteTxt"]
      and _E13["dzmTeteTxt"].count(" dans le plan") == 1 and _E13["dzmTeteTxt"].count(" · hors du plan") == 1
      and _E13["dzmTrou"].count("if(s0<=p&&p<e0)return null;") == 1 and _E13["dzmTrou"].count("b-a<.05") == 1
      and _E13["dzmTrouRipple"].count("c.tr!==tr") == 1
      and len(_DT) > 1000 and _DT.count("teteTxt:dzmTeteTxt,trou:dzmTrou,trouRipple:dzmTrouRipple,") == 1,
      ({n: len(c) for n, c in _E13.items()}, _DT.count("teteTxt:dzmTeteTxt")))
print("\n[24] L4 : reglages de livraison — pastille loudness, options, payload, badge de statut, DeliverRow (tache 4)")
# ── L4 (23/09/2026, tache 4) : decisions 5-8 du plan. La pastille compare la mesure
# (ebur128, /measure) a la cible choisie : vert |d| <= 1 dB, jaune <= 3, rouge ; gris sans
# cible ou sans mesure finie. Les options viennent de GET /deliver-presets (builtins puis
# maison, ids uniques, le premier gagne) ; le payload ne pose QUE les champs valides
# (fps hors liste, loudness en chaine, plage invalide ou case decochee -> OMIS) ; le
# statut du badge suit `status` brut de _job_to_dict.
check("lp_bornes_exactes_1_et_3_dB_vert_jaune_rouge_gris_sans_cible_nan_null_cible_non_numerique",
      D.get("lp") == ["vert", "vert", "jaune", "jaune", "rouge", "vert", "jaune", "gris", "gris", "gris", "gris", "gris"], D.get("lp"))
check("opts_builtins_puis_maison_doublon_ignore_non_objets_et_sans_id_ignores_label_absent_prend_l_id",
      D.get("opts") == [["master_1080", "Master", "Standard"], ["web_4k", "4K", "Standard"], ["maison_a", "Mon 4K", "Maison"], ["m2", "m2", "Maison"]],
      D.get("opts"))
check("opts_bornes_api_null_chaine_vide_builtins_non_tableau_ignore_maison_seule",
      D.get("opts_bornes") == [0, 0, 0, ["Maison"]], D.get("opts_bornes"))
check("opts_ne_mute_pas_l_api", D.get("opts_pur") is True, D.get("opts_pur"))
check("pl_tous_les_champs_poses_preset_fps_loudness_range_in_out_queue_true",
      D.get("pl") == {"name": "n", "preview": False, "clips": [], "preset": "web_4k", "fps": 60, "loudness": -14, "range": [2, 5], "queue": True},
      D.get("pl"))
check("pl_champs_absents_non_poses_la_base_seule", D.get("pl_absent") == ["clips", "name", "preview"], D.get("pl_absent"))
# fps 48 omis ; "60" (valeur d'un <select>) accepte ; loudness "-14" CHAINE omise (le backend refuse les chaines) ; -19 omis ;
# plage inversee omise ; case decochee -> plage omise ; preset vide omis ; queue false omis ; base null -> {} ; fps null / "" omis
check("pl_bornes_fps_48_omis_60_chaine_pris_loudness_chaine_omise_hors_liste_omise_plage_inversee_ou_decochee_omise_preset_vide_queue_false_base_null_fps_null_vide",
      D.get("pl_bornes") == [None, 60, None, None, None, None, None, None, 0, None, None], D.get("pl_bornes"))
check("pl_copie_la_base_sans_la_muter", D.get("pl_pur") is True, D.get("pl_pur"))
check("st_queued_en_file_generating_en_cours_n_pour_cent_done_termine_failed_echec_autre_vide_null_vide_progress_borne_0_100",
      D.get("st") == [{"st": "queued", "txt": "en file"}, {"st": "generating_video", "txt": "en cours 42 %"}, {"st": "done", "txt": "terminé"},
                      {"st": "failed", "txt": "échec"}, {"st": "zz", "txt": ""}, {"st": "", "txt": ""}, {"st": "generating_video", "txt": "en cours 0 %"},
                      {"st": "generating_video", "txt": "en cours 100 %"}], D.get("st"))
check("dr_composant_fonction_qui_touche_r_a_l_appel_props_null_vides_pleines",
      D.get("dr_pure") == "function" and D.get("dr_leve") == ["r.jsx", "r.jsx", "r.jsx"], (D.get("dr_pure"), D.get("dr_leve")))
check("dr_rendu_grille_huit_enfants_selects_groupes_valeurs_options_pastille_jaune_titree_case_cochee_bouton_titre_et_les_patchs_remontent",
      D.get("dr_rendu") == ["div", "svm-delopts", 8, "select", "maison_a", True,
                            [None, ["Standard", ["master_1080", "web_4k"]], ["Maison", ["maison_a", "m2"]]],
                            "60", ["projet (30)", "24", "25", "30", "60"], "-14", ["", "-14", "-16", "-23"],
                            "svm-loudpill", "jaune", "mesure −16,2 LUFS · cible −14", "label", "checkbox", True, True,
                            "svm-secbtn svm-delsave", "Enregistrer ce réglage…", True,
                            [{"preset": "web_4k"}, {"fps": None}, {"loudness": -23}, {"rangeOnly": False}, "save"]],
      D.get("dr_rendu"))
check("dr_etat_vide_sans_api_ni_mesure_ni_plage_select_vide_groupes_null_pastille_grise_mesurez_d_abord_pas_de_case",
      D.get("dr_vide") == ["", [None, None, None], "", "", "gris", "mesurez d'abord (bouton « mesurer » du bandeau Son)", None, "Enregistrer ce réglage…"],
      D.get("dr_vide"))
check("dr_revue_preset_persiste_absent_option_absent_en_tete_valeur_gardee_meme_sans_api",
      D.get("dr_absent") == ["zz_parti", "option", "zz_parti", "zz_parti (absent)", 3, "zz_parti", "zz_parti (absent)", None], D.get("dr_absent"))
check("del_badge_de_statut_cinquieme_enfant_data_st_brut_texte_par_delStatut_autre_statut_texte_vide",
      D.get("del_st") == [[5, "svm-delbadge svm-delst", "queued", "en file"], [5, "svm-delbadge svm-delst", "generating_video", "en cours 40 %"],
                          [5, "svm-delbadge svm-delst", "done", "terminé"], [5, "svm-delbadge svm-delst", "failed", "échec"],
                          [5, "svm-delbadge svm-delst", "zz", ""]], D.get("del_st"))
# LE COEUR RESTE PUR (quatre fonctions sans r/x/window/localStorage/fetch) ; le composant SANS hook ni fetch ; la plage
# passe par dzmRangeFrom EXISTANT (jamais recopie) ; AUCUN id de preset en dur dans la couche (banc croise T5 : temoin
# master_1080 x0 hors du banc) ; les listes fps/loudness ecrites UNE fois ; sept `title:` dans la rangee (3 selects,
# pastille, label, case, bouton) ; le badge de statut dans DzmDeliver x1 ; exports x1.
_L4 = {n: _corps(n) for n in ("dzmLoudPastille", "dzmDeliverOpts", "dzmDeliverPayload", "dzmDelStatut")}
_DRW4 = _corps("DzmDeliverRow"); _DEL4 = _corps("DzmDeliver")
check("l4_coeur_pur_x4_composant_sans_hook_ni_fetch_rangeFrom_reutilise_listes_uniques_aucun_id_de_preset_en_dur_sept_titres_badge_x1",
      all(len(c) > 80 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(", c) for c in _L4.values())
      and len(_DRW4) > 1500 and "r.jsx" in _DRW4 and "x.use" not in _DRW4 and "fetch(" not in _DRW4 and "localStorage" not in _DRW4
      and _L4["dzmDeliverPayload"].count("dzmRangeFrom(") == 1 and _L4["dzmDeliverPayload"].count("function dzmRange") == 0
      # revue T4 : la condition morte `o.fps!=null&&o.fps!==""` est retiree (Number(null|"") = 0, hors liste)
      and _L4["dzmDeliverPayload"].count("var f=Number(o.fps);if(DZM_DEL_FPS.indexOf(f)>=0)out.fps=f;") == 1 and "o.fps!=null" not in _L4["dzmDeliverPayload"]
      and _DRW4.count('pv+" (absent)"') == 1 and _DRW4.count("children:[absent,grp(") == 1
      and _SRCb.count("var DZM_DEL_FPS=[24,25,30,60];") == 1 and _SRCb.count("var DZM_DEL_LOUD=[[-14,") == 1
      and _SRCb.count("master_1080") == 0 and _SRCb.count("web_4k") == 0
      and _DRW4.count("title:") == 7 and _DRW4.count('className:"svm-secbtn svm-delsave"') == 1 and _DRW4.count('className:"svm-loudpill"') == 1
      and _DRW4.count("o.hasRange?") == 1 and _DRW4.count("dzmLoudPastille(") == 1 and _DRW4.count("dzmDeliverOpts(") == 1
      and len(_DEL4) > 800 and _DEL4.count("dzmDelStatut(") == 1 and _DEL4.count('className:"svm-delbadge svm-delst"') == 1
      and _DEL4.count('className:"svm-delbadge"') == 1,
      ({n: len(c) for n, c in _L4.items()}, len(_DRW4), _DRW4.count("title:"), _SRCb.count("master_1080")))
check("l4_exports_loudPastille_deliverOpts_deliverPayload_delStatut_DeliverRow_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("loudPastille:dzmLoudPastille,deliverOpts:dzmDeliverOpts,deliverPayload:dzmDeliverPayload,delStatut:dzmDelStatut,DeliverRow:DzmDeliverRow,") == 1,
      len(_DT))

print("\n[25] L7 D-10 : preset clavier Resolve, export / import du mappage (tache 1, 24/09/2026)")
# ── L7 D-10 (24/09/2026, tache 1). Le preset est un dictionnaire d'OVERRIDES applique par
# setKmOv (meme chemin que le panneau). MESURES sur le bundle (.bak_montage) qui CONTREDISENT
# le plan : « Ctrl+T » ET « Ctrl+Maj+T » sont dans SVM_COMBO_RESERVED (B:1641) -> l'action
# neuve trans_add a pour defaut « Alt+T » (libre, non reservee) et n'a rien a faire dans le
# preset ; « Backspace » n'est pas canonisable (SVM_COMBO_WORDS) et la touche est DEJA
# « Suppr » (SVM_EV_NAMES) -> delete retire du preset ; « O » est le defaut de toolbar, et
# svmKmMerge ignore un override qui vole la touche d'une action non remappee -> le preset
# deplace toolbar sur « Alt+O » (libre). JKL et I sont deja les defauts. TROIS cles, exactes.
check("kp_resolve_exactement_range_out_O_toolbar_Alt_O_blade_Ctrl_B",
      D.get("kp_resolve") == {"range_out": "O", "toolbar": "Alt+O", "blade": "Ctrl+B"}, D.get("kp_resolve"))
check("kp_inconnu_avid_null_vide_et_constructor_rendent_null", D.get("kp_inconnu") == [None, None, None, None], D.get("kp_inconnu"))
check("kp_rend_une_copie_neuve_a_chaque_appel", D.get("kp_pur") == "Ctrl+B", D.get("kp_pur"))
_kx = D.get("kx")
try: _kxj = json.loads(_kx) if isinstance(_kx, str) else None
except Exception as _e: _kxj = temoin(_e)
check("kx_chaine_json_version_1_keymap_copie", isinstance(_kx, str) and _kxj == {"version": 1, "keymap": {"blade": "Ctrl+B"}}, (_kx, _kxj))
_kxb = D.get("kx_bornes")
try: _kxbj = [json.loads(v) for v in _kxb] if isinstance(_kxb, list) and all(isinstance(v, str) for v in _kxb) else None
except Exception as _e: _kxbj = temoin(_e)
check("kx_bornes_null_undefined_chaine_tableau_donnent_un_keymap_objet_vide",
      _kxbj == [{"version": 1, "keymap": {}}] * 4, (_kxb, _kxbj))
# l'ordre des ignores suit l'ordre du fichier ; redo == defaut -> ni garde ni ignore
check("ki_ok_garde_blade_ignore_zzz_inconnu_et_undo_reservee_dans_l_ordre_du_fichier_defaut_tu",
      D.get("ki_ok") == {"ok": True, "keymap": {"blade": "Ctrl+B"}, "ignores": [{"id": "zzz", "raison": "inconnu"}, {"id": "undo", "raison": "reservee"}]},
      D.get("ki_ok"))
check("ki_combo_non_canonisable_et_valeur_non_chaine_ignorees_raison_combo",
      D.get("ki_combo") == {"ok": True, "keymap": {}, "ignores": [{"id": "blade", "raison": "combo"}, {"id": "undo", "raison": "combo"}]}, D.get("ki_combo"))
check("ki_casse_json_illisible", D.get("ki_casse") == {"ok": False, "raison": "json"}, D.get("ki_casse"))
check("ki_v2_version_2_absente_keymap_absent_tableau_null_chaine_refus_version",
      D.get("ki_v2") == [{"ok": False, "raison": "version"}] * 6, D.get("ki_v2"))
check("ki_actions_null_keymap_vide_ok_sans_rien", D.get("ki_vide") == {"ok": True, "keymap": {}, "ignores": []}, D.get("ki_vide"))
check("ki_aller_retour_export_puis_import_rend_le_meme_mappage",
      D.get("ki_aller_retour") == {"ok": True, "keymap": {"blade": "Ctrl+B"}, "ignores": []}, D.get("ki_aller_retour"))
# revue I1 : les collisions sont DITES, jugees comme svmKmMerge (defauts des actions sans override, puis overrides en
# ordre de table) -- range_out:"O" vole toolbar (non remappee) ; redo perd Alt+Q contre undo (avant dans la table) ;
# temoin positif : blade Ctrl+B passe. Le preset (toolbar remappee) passe entier ; l'echange mute/solo passe (M liberee).
check("ki_vol_vol_du_defaut_et_doublon_dits_collision_avec_l_id_qui_garde_la_touche_temoin_blade_passe",
      D.get("ki_vol") == {"ok": True, "keymap": {"blade": "Ctrl+B", "undo": "Alt+Q"},
                          "ignores": [{"id": "redo", "raison": "collision", "avec": "undo"}, {"id": "range_out", "raison": "collision", "avec": "toolbar"}]},
      D.get("ki_vol"))
check("ki_vol_le_preset_resolve_passe_sans_collision_toolbar_deplacee",
      D.get("ki_vol_preset") == {"ok": True, "keymap": {"blade": "Ctrl+B", "range_out": "O", "toolbar": "Alt+O"}, "ignores": []}, D.get("ki_vol_preset"))
check("ki_vol_l_echange_mute_solo_passe_la_touche_liberee_n_est_pas_une_collision",
      D.get("ki_vol_echange") == {"ok": True, "keymap": {"mute": "Alt+M", "solo": "M"}, "ignores": []}, D.get("ki_vol_echange"))
# LE COEUR RESTE PUR (trois fonctions sans r/x/window/localStorage/fetch) ; le preset n'est ecrit qu'UNE fois
# (DZM_KM_PRESETS) ; kmPreset lit par hasOwnProperty (« constructor » ne rend pas Object.prototype.constructor) ;
# aucun « Ctrl+T » ni « Backspace » dans la couche (les deux ecarts mesures) ; exports x1 dans DzTracks.
_L7A = {n: _corps(n) for n in ("dzmKmPreset", "dzmKmExport", "dzmKmImport")}
check("l7a_coeur_pur_x3_preset_ecrit_une_fois_hasOwnProperty_ni_Ctrl_T_ni_Backspace_dans_la_couche",
      all(len(c) > 60 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(", c) for c in _L7A.values())
      and _SRCb.count('var DZM_KM_PRESETS={resolve:{range_out:"O",toolbar:"Alt+O",blade:"Ctrl+B"}};') == 1
      and _L7A["dzmKmPreset"].count("hasOwnProperty") == 1 and _L7A["dzmKmImport"].count('raison:"inconnu"') == 1
      and _L7A["dzmKmImport"].count('raison:"combo"') == 1 and _L7A["dzmKmImport"].count('raison:"reservee"') == 1
      and _L7A["dzmKmImport"].count('raison:"json"') == 1 and _L7A["dzmKmImport"].count('raison:"version"') == 1
      and _L7A["dzmKmImport"].count('raison:"collision",avec:used[c]') == 1
      and _SRCb.count('"Ctrl+T"') == 0 and _SRCb.count("Backspace") == 0 and _SRCb.count("DZM_KM_PRESETS") == 3,
      ({n: len(c) for n, c in _L7A.items()}, _SRCb.count("DZM_KM_PRESETS")))
check("l7a_exports_kmPreset_kmExport_kmImport_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("kmPreset:dzmKmPreset,kmExport:dzmKmExport,kmImport:dzmKmImport,") == 1, len(_DT))

print("\n[26] L7 D-6 : presse-papiers de clips entre projets (tache 2, 24/09/2026)")
# ── L7 D-6 (24/09/2026, tache 2). UN clip (la selection est simple : selId, B:1707 -- ecart date, pas de
# multi-copie). clipCopy = copie PROFONDE sans id / transition / transition_s / src_history (srcOut garde :
# la fenetre de source suit le clip), clipPaste = choix de la piste + id + dzmInsere en mode courant.
# MESURES qui precisent le plan : (1) les pistes arrivent dans l'ORDRE DE L'ECRAN (DZM_DEFAULT_TRACKS :
# t1, v3, v2, v1, a1...) -> « la premiere piste du genre » serait V3 pour une video ; la cible est la piste
# du genre au PLUS PETIT rang (v1, a1) -- ce que le plan attendait (« -> piste v1 ») ; (2) dzmInsere rend
# refus:"" et note:"" quand tout va bien -> normalises a null ; (3) srcDur n'est lu que par « remplir »
# (dzmInsereUn) et le presse-papiers ne connait pas la duree de la source (addAsset la tient de /duration,
# B:4395 srcDurOr / askDur) -> colle sans srcDur, vitesse x1 en « remplir » sauf si l'appelant la passe.
check("cc_copie_sans_id_transition_transition_s_src_history_avec_srcOut_et_gain_undefined_ignore",
      D.get("cc") == {"tr": "v1", "label": "x", "start": 2, "end": 5, "srcIn": 1, "srcOut": 4, "src": {"job_id": "j"},
                      "gain": -3, "effects": [{"n": "a"}]}, D.get("cc"))
check("cc_copie_profonde_muter_la_copie_ne_touche_pas_l_original", D.get("cc_pur") == ["j", "a", "v1c4", "fade"], D.get("cc_pur"))
check("cc_bornes_null_undefined_chaine_nombre_tableau_rendent_null", D.get("cc_bornes") == [None] * 5, D.get("cc_bornes"))
_cpm = D.get("cp_meme_piste") or {}
check("cp_meme_piste_v1_existe_id_v1u7_100_inserer_clip_de_3_s_a_10_13_srcIn_garde_refus_et_note_null",
      _cpm.get("id") == "v1u7_100" and _cpm.get("track") == "v1" and _cpm.get("mode") == "inserer"
      and _cpm.get("refus") is None and _cpm.get("note") is None and _cpm.get("n") == 5
      and _cpm.get("v1") == [["p1", 0, 4, None], ["p2", 4, 8, None], ["v1u7_100", 10, 13, 1]]
      and isinstance(_cpm.get("pose"), dict) and _cpm["pose"].get("srcOut") == 4 and "srcDur" not in _cpm["pose"]
      and "transition" not in _cpm["pose"] and "src_history" not in _cpm["pose"], _cpm)
check("cp_inserer_a_2_fend_p1_et_decale_le_reste_de_3_s_le_collage_passe_par_dzmInsere",
      (D.get("cp_inserer_fend") or {}).get("v1") == [["p1", 0, 2, None], ["v1u8_20", 2, 5, 1], ["p1_r", 5, 7, 2], ["p2", 7, 11, None]]
      and (D.get("cp_inserer_fend") or {}).get("n") == 6, D.get("cp_inserer_fend"))
check("cp_ecraser_a_2_rogne_p1_et_p2_mode_rendu_ecraser",
      (D.get("cp_ecraser") or {}).get("v1") == [["p1", 0, 2, None], ["v1u9_20", 2, 5, 1], ["p2", 5, 8, 1]]
      and (D.get("cp_ecraser") or {}).get("mode") == "ecraser", D.get("cp_ecraser"))
_cpa = D.get("cp_piste_absente") or {}
check("cp_piste_absente_v9_va_sur_v1_le_plus_petit_rang_du_genre_pas_v3_la_premiere_de_la_liste",
      _cpa.get("track") == "v1" and _cpa.get("id") == "v1u7_100" and _cpa.get("refus") is None
      and _cpa.get("v1") == [["p1", 0, 4, None], ["p2", 4, 8, None], ["v1u7_100", 10, 13, 1]], _cpa)
_cpk = D.get("cp_kind_prime") or {}
check("cp_kind_de_la_piste_prime_sur_son_initiale_a1_absente_va_sur_x9_kind_audio",
      _cpk.get("track") == "x9" and _cpk.get("id") == "x9u7_100" and _cpk.get("refus") is None and _cpk.get("n") == 5
      and _cpk.get("v1") == [["p1", 0, 4, None], ["p2", 4, 8, None]] and (_cpk.get("pose") or {}).get("tr") == "x9", _cpk)
_cpg = D.get("cp_genre_absent") or {}
check("cp_genre_absent_refus_piste_note_dite_rien_pose_track_null",
      _cpg.get("refus") == "piste" and _cpg.get("note") == "Aucune piste audio pour coller" and _cpg.get("id") is None
      and _cpg.get("track") is None and _cpg.get("n") == 4 and _cpg.get("pose") is None, _cpg)
check("cp_vide_null_undefined_sans_clip_clip_null_clip_chaine_payload_chaine_refus_vide_rien_pose",
      D.get("cp_vide") == [["vide", None, 4, None]] * 6, D.get("cp_vide"))
check("cp_v0_version_2_absente_ou_chaine_refus_version_rien_pose", D.get("cp_v0") == [["version", None, 4]] * 3, D.get("cp_v0"))
_cpv = D.get("cp_verrou") or {}
check("cp_verrou_de_dzmInsere_relaye_tel_quel_note_dite_rien_pose",
      _cpv.get("refus") == "verrou" and _cpv.get("id") is None and _cpv.get("n") == 4 and _cpv.get("track") == "v1"
      and _cpv.get("note") == "Piste V1 verrouillée — rien n'a été collé", _cpv)
_cpo = D.get("cp_mou") or {}
check("cp_clips_mous_refus_clips_de_dzmInsere_relaye_note_generique",
      _cpo.get("refus") == "clips" and _cpo.get("id") is None and _cpo.get("n") == 0 and _cpo.get("note") == "Rien n'a été collé", _cpo)
check("cp_sans_pistes_refus_piste_video", (D.get("cp_sans_pistes") or {}).get("refus") == "piste"
      and (D.get("cp_sans_pistes") or {}).get("note") == "Aucune piste video pour coller", D.get("cp_sans_pistes"))
check("cp_head_negatif_ou_illisible_vaut_0_et_la_tete_est_arrondie_au_millieme_id_au_dixieme",
      D.get("cp_head") == [["v1u1_0", ["v1u1_0", 0, 3, 1]], ["v1u1_0", ["v1u1_0", 0, 3, 1]], ["v1u1_101", ["v1u1_101", 10.123, 13.123, 1]]], D.get("cp_head"))
check("cp_clip_sans_duree_prend_la_duree_video_par_defaut_6_s",
      (D.get("cp_len0") or {}).get("id") == "v1u2_100" and ((D.get("cp_len0") or {}).get("pose") or {}).get("end") == 16
      and ((D.get("cp_len0") or {}).get("pose") or {}).get("start") == 10, D.get("cp_len0"))
_cpi = D.get("cp_id_pris") or {}
check("cp_id_deja_pris_renomme_v1u7_100_2_l_ancien_est_decale_par_l_insertion",
      _cpi.get("id") == "v1u7_100_2" and _cpi.get("v1") == [["p1", 0, 4, None], ["p2", 4, 8, None], ["v1u7_100_2", 10, 13, 1], ["v1u7_100", 23, 24, None]], _cpi)
_cpr = D.get("cp_remplir") or {}; _cprs = D.get("cp_remplir_srcdur") or {}
check("cp_remplir_sans_srcDur_vitesse_x1_pose_sur_la_plage_avec_srcDur_6_vitesse_x2_srcOut_garde",
      _cpr.get("mode") == "remplir" and _cpr.get("refus") is None and _cpr.get("note") is None
      and _cpr.get("v1") == [["p1", 0, 2, None], ["v1u3_100", 2, 5, 0], ["p2", 5, 8, 1]]
      and (_cpr.get("pose") or {}).get("speed") == 1 and "srcDur" not in (_cpr.get("pose") or {"srcDur": 1})
      and (_cprs.get("pose") or {}).get("speed") == 2 and (_cprs.get("pose") or {}).get("srcOut") == 4 and _cprs.get("id") == "v1u3_100",
      (_cpr, _cprs))
check("cp_revue_I2_clip_sans_source_refus_source_note_dite_temoins_title_et_adjust_sans_src_passent",
      D.get("cp_sans_source") == [["source", None, None, 4, "Ce clip n'a pas de source (copié depuis la démo ?) — rien n'a été collé"],
                                  [None, "t1u1_100", "t1", 5, None], [None, "j1u1_100", "j1", 5, None]], D.get("cp_sans_source"))
check("cp_revue_M2_piste_homonyme_d_un_autre_genre_ignoree_v2_video_la_prend_sinon_refus_piste",
      D.get("cp_homonyme") == [[None, "v2", "v2u1_100"], ["piste", None, None]], D.get("cp_homonyme"))
check("cp_revue_M1_start_est_la_position_reelle_fin_8_ripple_4_remplir_2_inserer_10_null_sur_refus",
      D.get("cp_start") == [["fin", 8, "v1u1_100"], ["ripple_ecraser", 4, "v1u1_50"], ["remplir", 2, "v1u1_100"], ["inserer", 10, "v1u1_100"]]
      and D.get("cp_start_refus") == [None, None], (D.get("cp_start"), D.get("cp_start_refus")))
check("cp_pur_ni_les_clips_ni_le_presse_papiers_ne_sont_mutes", D.get("cp_pur") == [4, "p1,p2,o1,n1", "v1", 2, None], D.get("cp_pur"))
_cpmenu = dict(D.get("cp_menu") or []) if isinstance(D.get("cp_menu"), list) and all(isinstance(g, list) and len(g) == 2 for g in D.get("cp_menu")) else {}
check("cp_menu_copy_et_paste_ranges_en_Edition_par_DZM_MENU_RUB_blade_reste_Timeline_temoin",
      _cpmenu.get("Édition") == "copy,paste" and _cpmenu.get("Timeline") == "blade" and len(_cpmenu) == 2, D.get("cp_menu"))
# LE COEUR RESTE PUR (trois fonctions sans r/x/window/localStorage/fetch) ; la liste des cles non copiees est ecrite
# UNE fois ; clipPaste passe par dzmInsere (x1) et dzmUniqueId (x1) -- jamais recopies ; exports x1 dans DzTracks.
_L7B = {n: _corps(n) for n in ("dzmClipCopy", "dzmClipPisteCible", "dzmClipPaste")}
check("l7b_coeur_pur_x3_nocopy_ecrit_une_fois_paste_par_dzmInsere_et_dzmUniqueId_x1",
      all(len(c) > 60 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(", c) for c in _L7B.values())
      and _SRCb.count('var DZM_CLIP_NOCOPY=["id","transition","transition_s","src_history"];') == 1 and _SRCb.count("DZM_CLIP_NOCOPY") == 2
      and _L7B["dzmClipPaste"].count("dzmInsere(") == 1 and _L7B["dzmClipPaste"].count("dzmUniqueId(") == 1
      and _L7B["dzmClipPaste"].count("dzmClipPisteCible(") == 1 and _L7B["dzmClipPaste"].count("dzmClipCopy(") == 1
      and _L7B["dzmClipPaste"].count('refus:"vide"') == 1 and _L7B["dzmClipPaste"].count('refus:"version"') == 1 and _L7B["dzmClipPaste"].count('refus:"piste"') == 1
      and _L7B["dzmClipPaste"].count('refus:"source"') == 1 and _L7B["dzmClipPaste"].count("start:null") == 4 and _L7B["dzmClipPaste"].count("start:pose?Number(pose.start):null") == 1
      and _L7B["dzmClipPisteCible"].count("dzmKindOf(") == 3 and _SRCb.count('copy:"Édition",paste:"Édition"') == 1,
      ({n: len(c) for n, c in _L7B.items()}, _SRCb.count("DZM_CLIP_NOCOPY")))
check("l7b_exports_clipCopy_clipPaste_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("clipCopy:dzmClipCopy,clipPaste:dzmClipPaste,") == 1, len(_DT))

print("\n[27] L7 D-8 : boring detector, plans trop longs et jump cuts sur V1 (tache 3, 24/09/2026)")
# ── L7 D-8 (24/09/2026, tache 3). dzmBoring(clips, opts) pur -> {id: "long"|"jump"} sur V1 SEULEMENT :
# `long` = duree > maxS (strict : 8 s n'est pas long) ; `jump` = deux clips V1 en CONTACT (la tolerance de
# dzmVoisins, 0,1 s, REUTILISEE : pas de seconde regle de contact), meme source, et la reprise de source
# a moins de minFrames images : |srcIn_droit - (srcIn_gauche + len_gauche x vitesse)| x fps < minFrames.
# Le jump PRIME sur le long (un seul attribut par clip, le defaut visible d'abord). MESURES qui precisent le
# plan : (1) la comparaison se fait EN IMAGES avec un epsilon (2.4 - 2 vaut 0.3999... en flottant : au seuil,
# pas un jump) ; (2) la vitesse du plan gauche compte (a x2, 5 s consomment 10 s de source) ; (3) une IMAGE
# n'a pas de position de source : deux images identiques en contact sont un jump quel que soit srcIn ;
# (4) les options illisibles, nulles ou negatives retombent sur le defaut, et DZM_BORING_DEF n'est jamais
# mute (copie) ; (5) l'ordre d'arrivee des clips est indifferent, et ils ne sont pas mutes.
_BO_AB = {"a": "long", "b": "jump"}
check("bo_a_long_10_s_b_jump_meme_source_reprise_a_0_2_s_c_change_de_source_d_hors_V1",
      D.get("bo") == _BO_AB and D.get("bo_defaut") == _BO_AB, (D.get("bo"), D.get("bo_defaut")))
check("bo_def_exporte_maxS_8_minFrames_12_fps_30_et_jamais_mute_par_les_options",
      D.get("bo_def") == {"maxS": 8, "minFrames": 12, "fps": 30} and D.get("bo_def_pur") == ["long", "jump", "long", 8, None],
      (D.get("bo_def"), D.get("bo_def_pur")))
check("bo_loin_3_images_0_1_s_l_ecart_de_0_2_s_n_est_plus_un_jump_a_reste_long", D.get("bo_loin") == {"a": "long"}, D.get("bo_loin"))
check("bo_vide_tableau_vide_null_undefined_chaine_entrees_mortes_et_clip_sans_id_rendent_un_objet_vide",
      D.get("bo_vide") == [{}] * 6, D.get("bo_vide"))
check("bo_long_et_jump_le_jump_prime_sur_le_long", D.get("bo_long_et_jump") == _BO_AB, D.get("bo_long_et_jump"))
check("bo_egal_8_s_exactement_n_est_pas_long_8_001_l_est", D.get("bo_egal") == {"b": "long"}, D.get("bo_egal"))
check("bo_seuil_12_images_a_30_i_s_2_4_au_seuil_non_2_3_oui_symetrique_1_7_oui_1_6_non",
      D.get("bo_seuil") == [{}, {"b": "jump"}, {"b": "jump"}, {}], D.get("bo_seuil"))
check("bo_contact_tolerance_de_dzmVoisins_2_1_touche_2_5_non_un_chevauchement_n_est_pas_un_contact",
      D.get("bo_contact") == [{"b": "jump"}, {}, {}], D.get("bo_contact"))
check("bo_sources_job_vs_image_differents_deux_images_identiques_jump_differentes_non_sans_source_rien_src_vide_rien",
      D.get("bo_sources") == [None, {"b": "jump"}, {}, {}, {}, {}], D.get("bo_sources"))
check("bo_v2_les_pistes_autres_que_V1_ne_sont_jamais_jugees_ni_entre_elles_ni_contre_V1", D.get("bo_v2") == [{}, {}], D.get("bo_v2"))
check("bo_vitesse_x2_consomme_le_double_de_source_reprise_a_10_est_un_jump_x1_non_vitesse_illisible_vaut_1",
      D.get("bo_vitesse") == [{"b": "jump"}, {}, {"b": "jump"}], D.get("bo_vitesse"))
check("bo_desordre_l_ordre_d_arrivee_est_indifferent_et_les_clips_ne_sont_pas_mutes",
      D.get("bo_desordre") == _BO_AB and D.get("bo_pur") == [True, "a,b,c,d"], (D.get("bo_desordre"), D.get("bo_pur")))
check("bo_opts_illisibles_nulles_negatives_defaut_maxS_20_ne_laisse_que_le_jump_fps_60_resserre_le_seuil",
      D.get("bo_opts") == [_BO_AB, _BO_AB, _BO_AB, {"b": "jump"}, _BO_AB, _BO_AB, {"a": "long"}, _BO_AB, _BO_AB], D.get("bo_opts"))
# LE COEUR RESTE PUR : quatre fonctions sans r/x/stockage/fenetre/document/fetch ; le defaut est ecrit UNE fois ;
# le contact vient de dzmVoisins (x1, jamais recopie) ; "long" x1, "jump" x2 (image, puis seuil) ; exports x1.
# MESURE contre le plan : `dzmSrcKey` EXISTAIT (couche :2886, la cle JSON canonique de `src`, exportee `srcKey`,
# le juge du jumeau) -- pas de seconde definition (node --check refusait le doublon) : dzmBoringKey l'appelle x1.
_L7C = {n: _corps(n) for n in ("dzmBoringOpts", "dzmBoringKey", "dzmBoring")}
check("l7c_coeur_pur_x3_defaut_ecrit_une_fois_contact_par_dzmVoisins_x1_source_par_dzmSrcKey_x1_long_x1_jump_x2_seuil_en_images_avec_epsilon",
      all(len(c) > 60 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(", c) for c in _L7C.values())
      # x5 : la definition, deux lectures dans dzmBoringOpts (copie, puis les cles), l'export, le commentaire du bloc
      and _SRCb.count("var DZM_BORING_DEF={maxS:8,minFrames:12,fps:30};") == 1 and _SRCb.count("DZM_BORING_DEF") == 5
      and _SRCb.count("function dzmSrcKey(") == 1 and _SRCb.count("srcKey:dzmSrcKey,") == 1
      and _L7C["dzmBoring"].count("dzmVoisins(") == 1 and _L7C["dzmBoring"].count("dzmBoringKey(") == 2 and _L7C["dzmBoring"].count("dzmBoringOpts(") == 1
      and _L7C["dzmBoring"].count('"long"') == 1 and _L7C["dzmBoring"].count('"jump"') == 2 and _L7C["dzmBoring"].count('c.tr==="v1"') == 1
      and _L7C["dzmBoring"].count(">o.maxS)") == 1 and _L7C["dzmBoring"].count("*o.fps<o.minFrames-1e-6)") == 1
      and _L7C["dzmBoring"].count("c.src.image&&!c.src.job_id") == 1
      and _L7C["dzmBoringOpts"].count("isFinite(v)&&v>0") == 1 and _L7C["dzmBoringKey"].count("dzmSrcKey(") == 1 and _L7C["dzmBoringKey"].count("Object.keys(") == 1,
      ({n: len(c) for n, c in _L7C.items()}, _SRCb.count("DZM_BORING_DEF")))
check("l7c_exports_boring_boringDef_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("boring:dzmBoring,boringDef:DZM_BORING_DEF,") == 1, len(_DT))

print("\n[28] L7 D-39 : comparaison de deux projets (tache 4, 24/09/2026)")
# ── L7 D-39 (24/09/2026, tache 4). dzmDiff(a, b) pur sur deux tableaux de clips -> {added, removed, moved, trimmed,
# changed, noms} ; identite = `id` (les ids sont des chaines). `moved` = meme duree ET meme srcIn, start different ;
# `trimmed` = duree OU srcIn differents (un slip est un rognage de la fenetre de source : `src:[inA,inB]` s'ajoute
# quand srcIn a bouge — MESURE contre le plan, dont la lettre laissait le slip sans rubrique) ; `changed` = cles de
# DZM_DIFF_CLES differentes par JSON.stringify (absent, null et undefined se valent ; 0 n'est pas absent), un clip
# peut etre rogne ET modifie, un clip deplace d'une piste est deplace ET modifie (tr), moved exclut trimmed.
# `noms` = {id: label} (B prime, sinon A, jamais d'entree sans libelle) : la vue n'a pas les clips sous la main —
# ECART mesure : le plan ne prevoyait que cinq rubriques, la sixieme cle porte les libelles.
_DF_VIDE = {"added": [], "removed": [], "moved": [], "trimmed": [], "changed": [], "noms": {}}
check("df_ajoute_4_supprime_3_deplace_1_rogne_2_modifie_2_gain_un_clip_rogne_et_modifie",
      D.get("df") == {"added": ["4"], "removed": ["3"], "moved": [{"id": "1", "de": 0, "en": 2}],
                      "trimmed": [{"id": "2", "de": [5, 8], "en": [5, 9]}], "changed": [{"id": "2", "cles": ["gain"]}], "noms": {}},
      D.get("df"))
check("df_id_un_projet_contre_lui_meme_rend_les_six_cles_vides", D.get("df_id") == _DF_VIDE, D.get("df_id"))
check("df_vide_tableaux_vides_null_chaines_entrees_mortes_et_clip_sans_id_ignores",
      D.get("df_vide") == [_DF_VIDE, _DF_VIDE, _DF_VIDE, dict(_DF_VIDE, added=["z"])], D.get("df_vide"))
check("df_slip_srcIn_seul_est_un_rognage_de_source_pas_un_deplacement",
      D.get("df_slip") == dict(_DF_VIDE, trimmed=[{"id": "1", "de": [0, 5], "en": [0, 5], "src": [0, 2]}]), D.get("df_slip"))
check("df_piste_meme_duree_autre_piste_et_autre_start_deplace_et_modifie_tr",
      D.get("df_piste") == dict(_DF_VIDE, moved=[{"id": "1", "de": 0, "en": 3}], changed=[{"id": "1", "cles": ["tr"]}]), D.get("df_piste"))
check("df_rogne_et_bouge_tete_coupee_duree_et_srcIn_changes_rogne_seulement_jamais_deplace",
      D.get("df_rogne_et_bouge") == dict(_DF_VIDE, trimmed=[{"id": "1", "de": [0, 5], "en": [3, 5], "src": [0, 3]}]), D.get("df_rogne_et_bouge"))
check("df_noms_B_prime_sinon_A_jamais_d_entree_sans_libelle_supprimes_dans_l_ordre_de_A",
      # `label` est dans DZM_DIFF_CLES : Ancien -> Neuf est aussi un `changed`
      D.get("df_noms") == dict(_DF_VIDE, added=["3"], removed=["2", "5"], changed=[{"id": "1", "cles": ["label"]}],
                               noms={"1": "Neuf", "3": "Tiers", "5": "Parti"}), D.get("df_noms"))
check("df_cles_absent_null_undefined_se_valent_0_compte_effects_en_profondeur_kind_hors_liste_ordre_de_la_liste",
      D.get("df_cles") == [[], [{"id": "1", "cles": ["gain"]}], [{"id": "1", "cles": ["effects"]}], [],
                           [{"id": "1", "cles": ["opacity", "text", "transition", "transition_s"]}]], D.get("df_cles"))
check("df_reframe_cloture_T8_un_cadrage_different_est_modifie_reframe_temoin_meme_cadrage_rien",
      D.get("df_reframe") == [[{"id": "1", "cles": ["reframe"]}], [], [{"id": "1", "cles": ["reframe"]}]], D.get("df_reframe"))
check("df_tolerance_1e_9_n_est_ni_deplace_ni_rogne_1_ms_deplace_1_ms_de_srcIn_rogne_temoin",
      D.get("df_tolerance") == [_DF_VIDE, dict(_DF_VIDE, moved=[{"id": "1", "de": 5, "en": 5.001}]),
                                dict(_DF_VIDE, trimmed=[{"id": "1", "de": [5, 8], "en": [5, 8], "src": [1, 1.001]}])], D.get("df_tolerance"))
check("df_pur_les_deux_tableaux_ne_sont_pas_mutes", D.get("df_pur") == [True, True, 3, 3], D.get("df_pur"))
check("df_temps_m_ss_du_bundle_dixieme_a_la_virgule_arrondi_qui_porte_illisible_et_negatif_a_zero",
      D.get("df_temps") == ["0:00", "1:05", "0:05,3", "1:00", "0:00", "0:00"], D.get("df_temps"))
check("df_vue_racine_svm_pop_dzm_diff_titre_resume_cinq_rubriques_lignes_temps_Fermer_titre_clic_ferme_clic_racine_arrete",
      D.get("df_vue") == ["div", "svm-pop dzm-diff", "Comparer : « a » → « b »", "1 ajouté · 1 supprimé · 1 déplacé · 1 rogné · 1 modifié",
                          [["div", "added", "Ajoutés (1)", ["4"]], ["div", "removed", "Supprimés (1)", ["3"]],
                           ["div", "moved", "Déplacés (1)", ["1 : 0:00 → 0:02"]],
                           ["div", "trimmed", "Rognés (1)", ["2 : 0:05–0:08 → 0:05–0:09"]],
                           ["div", "changed", "Modifiés (1)", ["2 : gain"]]],
                          ["button", "svm-secbtn", "Fermer la comparaison (Échap)", "Fermer"], ["close"], "function"],
      D.get("df_vue"))
check("df_vue_noms_pluriel_libelle_ou_id_rubrique_vide_tiret_noms_par_defaut_sans_props_rien_ne_leve",
      D.get("df_vue_noms") == ["2 ajoutés · 0 supprimé · 0 déplacé · 0 rogné · 0 modifié", ["Un", "2"], ["—"],
                               "Comparer : « montage courant » → « autre projet »", "svm-pop dzm-diff",
                               "0 ajouté · 0 supprimé · 0 déplacé · 0 rogné · 0 modifié", 8],
      D.get("df_vue_noms"))
# LE COEUR RESTE PUR : la liste des cles ecrite UNE fois ; dzmDiffIndex, dzmDiff et dzmDiffTemps sans r/x/stockage/
# fenetre/document/fetch ; la vue lit `r` a l'appel (dans son corps, jamais au chargement) ; exports x1.
_L7D = {n: _corps(n) for n in ("dzmDiffIndex", "dzmDiff", "dzmDiffTemps")}
_L7DV = _corps("DzmDiffView")
check("l7d_coeur_pur_x3_cles_ecrites_une_fois_index_par_id_stringify_x2_vue_lit_r_a_l_appel_et_reutilise_svmRuler",
      all(len(c) > 60 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(", c) for c in _L7D.values())
      # cloture T8 (24/09/2026) : `reframe` (D-40) rejoint la liste en queue -- dix-neuf cles
      and _SRCb.count('var DZM_DIFF_CLES=["gain","opacity","x","y","scale","rotate","effects","dz","speed","retime","stab","text",'
                      '"transition","transition_s","fade_in","fade_out","label","tr","reframe"];') == 1
      # x3 : la definition, le filtre de dzmDiff, le commentaire du bloc
      and _SRCb.count("DZM_DIFF_CLES") == 3 and _L7D["dzmDiff"].count("dzmDiffIndex(") == 2 and _L7D["dzmDiff"].count("JSON.stringify(") == 1
      and _L7D["dzmDiff"].count("out.moved.push(") == 1 and _L7D["dzmDiff"].count("out.trimmed.push(") == 1
      and _L7D["dzmDiffTemps"].count("svmRuler(") == 1 and _SRCb.count("function svmRuler(") == 0
      and len(_L7DV) > 400 and _L7DV.count("r.jsx") >= 6 and _L7DV.count("x.use") == 0 and _L7DV.count("dzmDiffTemps(") >= 2
      and _L7DV.count('className:"svm-pop dzm-diff"') == 1 and _L7DV.count("title:") == 1 and _L7DV.count("localStorage") == 0,
      ({n: len(c) for n, c in _L7D.items()}, len(_L7DV), _SRCb.count("DZM_DIFF_CLES")))
check("l7d_exports_diff_DiffView_diffTemps_dans_DzTracks",
      len(_DT) > 1000 and _DT.count("diff:dzmDiff,DiffView:DzmDiffView,diffTemps:dzmDiffTemps,") == 1, len(_DT))
# la ligne d'un projet : « ⇄ » TOUJOURS rendu (grise sur le courant, comme « ouvrir » : la regle E-12 des boutons
# conditionnels), appelle props.onDiff(p) x1 ; le bouton n'existe pas dans le .bak (couche seule)
_L7DP = _SRCb[_SRCb.find("  function row(p){"):_SRCb.find("  var rows=list||[];")]
check("l7d_projets_bouton_compare_toujours_rendu_disabled_mine_title_onDiff_x1_entre_dupliquer_et_ouvrir",
      0 < len(_L7DP) < 6000 and _L7DP.count('className:"svm-tbtn dzm-projbtn dzm-projdiff",disabled:mine||off,"aria-disabled":mine||off,') == 1
      and _L7DP.count("onClick:function(){if(props&&props.onDiff)props.onDiff(p)},children:\"⇄\"},\"df\")") == 1
      # x2 : la garde et l'appel, sur la meme ligne
      and _SRCb.count("props.onDiff") == 2 and _SRCb.count("dzm-projdiff") == 1
      and _L7DP.find('children:"dupliquer"},"dp")') < _L7DP.find("dzm-projdiff") < _L7DP.find('children:oArm?"remplacer ?":"ouvrir"},"op")')
      and re.search(r'(\?null:|\?|&&)\s*r\.jsxs?\("button",\{className:"svm-tbtn dzm-projbtn dzm-projdiff"', _L7DP) is None,
      (len(_L7DP), _SRCb.count("props.onDiff"), _SRCb.count("dzm-projdiff")))

print("\n[29] L7 D-3b : les deux secondes de source A/B d'une jonction (tache 4-bis, 24/09/2026)")
# ── L7 D-3b (24/09/2026, tache 4-bis). dzmAbSecs(g, d) pur -> {a, b} ou null : A = derniere image du plan GAUCHE
# (srcIn + duree x vitesse − 1/30 : la vitesse etire la fenetre de source, meme mesure que dzmBoring et que le srcIn
# du roll), B = premiere image du plan DROIT (son srcIn, la vitesse n'y change rien). Les deux plans doivent etre
# des VIDEOS (src.job_id) sur la meme piste, en contact a la tolerance du roll (0,1 s), le gauche AVANT le droit
# et d'une duree > 0 ; sinon null (l'hote grise la rangee, il ne la retire pas — E-12). Les secondes sont bornees
# a 0 et arrondies a l'image (1/30) puis au millieme : la cle « source@seconde » des vignettes ne bouge que
# lorsque l'image change.
check("ab_A_derniere_image_du_gauche_srcIn_plus_duree_moins_une_image_B_srcIn_du_droit",
      D.get("ab") == {"a": 4.967, "b": 1}, D.get("ab"))
check("ab_vitesse_du_gauche_etire_la_fenetre_x2_illisible_ou_nulle_vaut_1_celle_du_droit_ne_compte_pas",
      D.get("ab_vitesse") == [{"a": 7.967, "b": 1}, {"a": 4.967, "b": 1}, {"a": 4.967, "b": 1}, {"a": 4.967, "b": 1}], D.get("ab_vitesse"))
check("ab_sans_srcIn_A_duree_moins_une_image_B_zero_srcIn_en_chaine_lu",
      D.get("ab_sans_srcin") == [{"a": 2.967, "b": 0}, {"a": 4.967, "b": 1}], D.get("ab_sans_srcin"))
check("ab_refus_null_x9_absent_image_audio_sans_source_autre_piste_trou_duree_nulle_chaines",
      isinstance(D.get("ab_refus"), list) and len(D.get("ab_refus")) == 9 and all(v is None for v in D.get("ab_refus")), D.get("ab_refus"))
check("ab_contact_tolerance_du_roll_3_1_passe_3_11_refuse_temoin_droit_avant_gauche_refuse",
      D.get("ab_contact") == [{"a": 4.967, "b": 1}, None, None], D.get("ab_contact"))
check("ab_zero_bornes_a_0_et_arrondi_a_l_image_puis_au_millieme",
      D.get("ab_zero") == [{"a": 0, "b": 0}, {"a": 4.967, "b": 1.033}], D.get("ab_zero"))
check("ab_pur_les_deux_clips_ne_sont_pas_mutes", D.get("ab_pur") == [True, True], D.get("ab_pur"))
# revue 24/09 : dzmAbRollDit(avant, apres, n) -> {k, partiel} -- total (k = n, rien a dire), partiel (dzmRoll a borne : k
# images seulement, a DIRE apres l'ecriture), nul (refus, rien a ecrire) ; signe ; tolerance 1 ms (un start arrondi au
# millieme par dzmR3 reste « total » : 3.001 -> 3.334 pour dix images, temoin)
check("abd_total_partiel_nul_signe_entrees_molles_demi_ms_rien_millieme_arrondi_total",
      D.get("abd") == [{"k": 10, "partiel": False}, {"k": 4, "partiel": True}, {"k": 0, "partiel": False}, {"k": -1, "partiel": False},
                       {"k": -1, "partiel": True}, {"k": 0, "partiel": False}, {"k": 0, "partiel": False}, {"k": 10, "partiel": False}], D.get("abd"))
_L7G = _corps("dzmAbSecs"); _L7GD = _corps("dzmAbRollDit")
check("l7g_coeur_pur_x2_reutilise_dzmSpeedNum_et_dzmR3_constante_DZM_AB_IMG_x4_exports_abSecs_abRollDit_x1",
      len(_L7G) > 120 and len(_L7GD) > 80
      and all(not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(", c) for c in (_L7G, _L7GD))
      and _L7G.count("dzmSpeedNum(") == 1 and _L7G.count("dzmR3(") == 2 and _L7G.count("DZM_AB_IMG") == 1 and _L7GD.count("DZM_AB_IMG") == 2
      # x4 : la definition, abSecs, abRollDit x2 -- 1/30 n'est ecrit qu'UNE fois dans le bloc
      and _SRCb.count("var DZM_AB_IMG=1/30;") == 1 and _SRCb.count("DZM_AB_IMG") == 4 and _L7GD.count("1e-3") == 2
      and len(_DT) > 1000 and _DT.count("abSecs:dzmAbSecs,abRollDit:dzmAbRollDit,") == 1,
      (len(_L7G), len(_L7GD), _SRCb.count("DZM_AB_IMG"), _DT.count("abSecs:dzmAbSecs,")))

print("\n[30] L7 D-19 : coins arrondis et ombre d'un overlay — dzmOvExtra pur (tache 5, client, 24/09/2026)")
# ── L7 D-19 (24/09/2026, tache 5, moitie client). dzmOvExtra(c) pur -> {radius, shadow} : le rayon des coins en px
# du canvas (entier 0..200, arrondi) et l'ombre portee (0|1 : numerique >= 0,5, la regle meme de _ov_transform cote
# backend), TOUJOURS les deux cles, defauts 0 ; entree molle -> {0,0}. Une seule mesure pour svmOvTfOf, donc pour
# l'apercu, l'inspecteur et le payload (L7e2) ; jamais dans les keyframes (D-14 : statiques, date).
check("ox_rayon_et_ombre_lus_sur_le_clip", D.get("ox") == {"radius": 40, "shadow": 1}, D.get("ox"))
check("ox_rayon_borne_0_200_entier_chaine_lue_illisible_ou_absent_0",
      D.get("ox_rayon") == [200, 0, 13, 0, 40, 0], D.get("ox_rayon"))
check("ox_ombre_vrai_1_2_et_demi_valent_1_zero_nul_049_x_absent_valent_0",
      D.get("ox_ombre") == [1, 1, 1, 1, 0, 0, 0, 0, 0], D.get("ox_ombre"))
check("ox_entrees_molles_0_0_x3_et_deux_cles_seulement",
      D.get("ox_mou") == [{"radius": 0, "shadow": 0}] * 3 + [["radius", "shadow"]], D.get("ox_mou"))
check("ox_pur_le_clip_n_est_pas_mute", D.get("ox_pur") is True, D.get("ox_pur"))
_L7E = _corps("dzmOvExtra")
check("l7e_coeur_pur_constante_DZM_OV_RADIUS_MAX_x2_export_ovExtra_x1",
      len(_L7E) > 80
      and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(", _L7E)
      # x2 : la definition et la borne du corps -- 200 n'est ecrit qu'UNE fois dans le bloc
      and _L7E.count("DZM_OV_RADIUS_MAX") == 1 and _SRCb.count("var DZM_OV_RADIUS_MAX=200;") == 1
      and _SRCb.count("DZM_OV_RADIUS_MAX") == 2 and _L7E.count("200") == 0
      and len(_DT) > 1000 and _DT.count("ovExtra:dzmOvExtra,") == 1 and _SRCb.count("ovExtra:") == 1,
      (len(_L7E), _SRCb.count("DZM_OV_RADIUS_MAX"), _DT.count("ovExtra:dzmOvExtra,")))

print("\n[31] L7 D-22 : pistes de sous-titres par langue, une seule gravee — subsTracks/subsNew/subsBurn/subsBurnId/subsCopy purs (tache 6, 24/09/2026)")
# ── L7 D-22 (24/09/2026, tache 6). Perimetre MINIMAL et date (decision n°7) : une piste S2… est une copie (traduite ou
# vide) de S1 ; l'editeur reste sur S1 ; la piste subs marquee `burn:true` (UNE seule ; s1 sans marque par defaut) est
# celle que subsPayload() envoie (subsBurnId). Le genre est lu par dzmKindOf (initiale ou kind explicite), jamais par
# une egalite avec "s1". Toutes les fonctions rendent des tableaux NEUFS et ne mutent rien.
_S2 = {"id": "s2", "name": "S2 en", "type": "sous-titres", "h": 44, "c": "--c-text", "mix": 11, "kind": "subs", "lang": "en"}
check("sst_pistes_de_sous_titres_s1_seule", D.get("sst") == ["s1"], D.get("sst"))
check("sst_bornes_initiale_ou_kind_explicite_s1_declaree_video_exclue_entrees_molles_vides",
      D.get("sst_bornes") == [["s9", "x1"], [], []], D.get("sst_bornes"))
check("sn_s2_habillee_par_dzmSkin_nommee_S2_en_avec_lang_id_rendu",
      isinstance(D.get("sn"), dict) and D["sn"].get("id") == "s2" and isinstance(D["sn"].get("tracks"), list)
      and len(D["sn"]["tracks"]) == 4 and D["sn"]["tracks"][2] == _S2, D.get("sn"))
check("sn2_puis_s3", D.get("sn2") == "s3", D.get("sn2"))
check("sn_place_apres_la_derniere_subs_s1_sans_subs_s6_apres_s5_langue_blanche_sans_lang_liste_molle_s1",
      D.get("sn_place") == [["v1", "s1", "s2", "a1"], "s1", "s6",
                            {"id": "s2", "name": "S2", "type": "sous-titres", "h": 44, "c": "--c-text", "mix": 11, "kind": "subs"}, ["s1"]],
      D.get("sn_place"))
check("sb_s2_gravee_s1_burn_false_les_autres_sans_cle",
      isinstance(D.get("sb"), list) and [(t.get("id"), t.get("burn", "-")) for t in D["sb"]] == [("v1", "-"), ("s1", False), ("s2", True), ("a1", "-")],
      D.get("sb"))
check("sb_defaut_s1_gravee_pour_id_absent_inconnu_ou_hors_genre",
      D.get("sb_defaut") == [["v1:-", "s1:true", "a1:-"], ["v1:-", "s1:true", "s2:false", "a1:-"], ["v1:-", "s1:true", "s2:false", "a1:-"]],
      D.get("sb_defaut"))
check("sb_neuf_tableau_neuf_pistes_hors_subs_memes_objets_pistes_subs_objets_neufs",
      D.get("sb_neuf") == [True, True, True, True], D.get("sb_neuf"))
check("sb_bascule_retour_une_seule_gravee", D.get("sb_bascule") == ["v1:-", "s1:true", "s2:false", "a1:-"], D.get("sb_bascule"))
check("bid_la_marquee_sinon_s1_meme_sans_marque_sans_subs_ou_liste_molle_sinon_la_premiere_subs_deux_marquees_la_premiere",
      D.get("bid") == ["s2", "s1", "s1", "s1", "s1", "s3", "s1"], D.get("bid"))
check("sc_segments_donnes_deux_clips_neufs_s2c1_s2c2_label_egal_texte_hidden_garde",
      isinstance(D.get("sc"), list) and len(D["sc"]) == 5
      and D["sc"][3] == {"id": "s2c1", "tr": "s2", "start": 0, "end": 1, "text": "Hi", "label": "Hi"}
      and D["sc"][4] == {"id": "s2c2", "tr": "s2", "start": 1, "end": 2.5, "text": "Hello everyone", "label": "Hello everyone", "hidden": True},
      D.get("sc"))
check("sc_clips_sans_segments_copie_des_clips_de_s1_hidden_words_label_gardes",
      isinstance(D.get("sc_clips"), list) and len(D["sc_clips"]) == 5
      and D["sc_clips"][3] == {"id": "s2c1", "tr": "s2", "start": 0, "end": 1, "text": "Salut", "label": "Salut"}
      and D["sc_clips"][4] == {"id": "s2c2", "tr": "s2", "start": 1, "end": 2.5, "text": "Bonjour à tous", "label": "Bonjour à tous", "hidden": True, "words": [{"t": 1}]},
      D.get("sc_clips"))
check("sc_memes_les_autres_clips_sont_les_memes_objets", D.get("sc_memes") == [True] * 4, D.get("sc_memes"))
check("sc_ids_uniques_contre_les_clips_presents_s2c1_pris_s2c1_2",
      D.get("sc_ids") == ["v1u1", "s1c1", "s1c2", "s2c1", "s2c1_2"], D.get("sc_ids"))
check("sc_bornes_start_illisible_ignore_end_borne_null_ignore_texte_absent_vide_label_tronque_clips_mous_cible_vide_segments_vides_deTr_absente",
      D.get("sc_bornes") == [[{"id": "s2c1", "tr": "s2", "start": 2, "end": 2.1, "text": "y", "label": "y"},
                             {"id": "s2c2", "tr": "s2", "start": 3, "end": 4, "text": "", "label": "(vide)"},
                             {"id": "s2c3", "tr": "s2", "start": 5, "end": 6, "text": "aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeee",
                              "label": "aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeee…"}],
                            [{"id": "s2c1", "tr": "s2", "start": 0, "end": 1, "text": "z", "label": "z"}], 3, 3, 3],
      D.get("sc_bornes"))
check("sc_pur_ni_pistes_ni_clips_mutes_et_les_pistes_d_avant_intactes_dans_le_neuf", D.get("sc_pur") == [True, True, True], D.get("sc_pur"))
check("rm_s2_se_retire_s1_jamais", D.get("rm") == ["v1", "s1", "a1"] and D.get("rm_s1") is True, (D.get("rm"), D.get("rm_s1")))
check("tp_payload_porte_lang_burn_et_nom_de_la_piste_de_langue_jamais_burn_false",
      D.get("tp") == [{"id": "v1", "kind": "video"}, {"id": "s1", "kind": "subs"},
                      {"id": "s2", "kind": "subs", "lang": "en", "burn": True, "name": "S2 en"}, {"id": "a1", "kind": "audio"}],
      D.get("tp"))
_L7F = {n: _corps(n) for n in ("dzmSubsTracks", "dzmSubsNew", "dzmSubsBurn", "dzmSubsBurnId", "dzmSubsCopy")}
check("l7f_coeur_pur_cinq_fonctions_genre_par_dzmKindOf_x0_egalite_s1_exports_x1_dzmRemove_intact",
      all(len(c) > 80 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(", c) for c in _L7F.values())
      and all("dzmKindOf(" in _L7F[n] for n in ("dzmSubsTracks", "dzmSubsNew", "dzmSubsBurn", "dzmSubsBurnId"))
      # aucune egalite avec "s1" dans les cinq corps : le repli de subsBurnId est la SEULE mention, en litteral de retour
      and sum(c.count('"s1"') for c in _L7F.values()) == 1 and _L7F["dzmSubsBurnId"].count('"s1"') == 1
      and _L7F["dzmSubsCopy"].count("dzmUniqueId(") == 1 and _L7F["dzmSubsNew"].count("dzmSkin(") == 1
      and len(_DT) > 1000 and _DT.count("subsTracks:dzmSubsTracks,subsNew:dzmSubsNew,subsBurn:dzmSubsBurn,subsBurnId:dzmSubsBurnId,subsCopy:dzmSubsCopy,") == 1
      and _SRCb.count("subsBurn:") == 1 and _SRCb.count('return (id==="v1"||id==="s1")?ts:ts.filter(function(t){return t.id!==id})}') == 1
      and _SRCb.count('if(t.kind==="subs"){if(t.lang)o.lang=String(t.lang);if(t.burn)o.burn=!0;if(t.lang&&t.name)o.name=String(t.name)}') == 1,
      ({n: len(c) for n, c in _L7F.items()}, _DT.count("subsBurn:dzmSubsBurn,"), sum(c.count('"s1"') for c in _L7F.values())))

print("\n[32] L7-B D-42 : decouper un clip aux changements de plan — dzmCutAt pur (tache 2, 24/09/2026)")
# ── L7-B D-42 (24/09/2026, tache 2, decision n°2 du plan). dzmCutAt(clips, id, times, opts) PUR -> {clips, n, refus, note} :
# `times` = secondes de SOURCE depuis le srcIn du clip (ce que rend POST /api/montage/scenes), converties en timeline
# `start + t/speed` ; coupes a moins de 0,05 s d'un bord ignorees (la tolerance de la lame) ; piste verrouillee -> refus ;
# moities droites `transition:"cut", transition_s:0` et `srcIn` recale (srcIn + (p - start) x speed) ; ids par
# dzmUniqueId sur la base de la lame (id + "_b" + round(p x 10)) -- uniques meme a < 0,1 s d'ecart (la lame, elle, ne
# l'est pas : fait mesure du plan). Le clip est remplace EN PLACE par ses morceaux (la lame, elle, ajoute en queue).
_CA_N = ["n", "a1", 0, 12, None, None, None]
check("ca_trois_coupes_quatre_morceaux_en_place_srcIn_recales_moities_droites_en_cut_note_n_coupes",
      D.get("ca") == [[["p", "v1", 2, 5, 1, "fade", 0.5], ["p_b50", "v1", 5, 8, 4, "cut", 0], ["p_b80", "v1", 8, 10, 7, "cut", 0],
                       ["p_b100", "v1", 10, 12, 9, "cut", 0], _CA_N], 3, "", "3 coupes aux changements de plan"],
      D.get("ca"))
check("ca_vitesse_x2_timeline_start_plus_t_sur_2_srcIn_plus_t",
      D.get("ca_vitesse") == [[["p", "v1", 2, 4, 1, "fade", 0.5], ["p_b40", "v1", 4, 6, 5, "cut", 0], ["p_b60", "v1", 6, 12, 9, "cut", 0]], 2],
      D.get("ca_vitesse"))
check("ca_ids_uniques_a_moins_de_0_1_s_meme_base_p_b50_et_contre_un_id_deja_pris",
      D.get("ca_ids") == ["p", "p_b50", "p_b50_2", "n"] and D.get("ca_ids_pris") == ["p", "p_b50_2", "n", "p_b50"],
      (D.get("ca_ids"), D.get("ca_ids_pris")))
check("ca_bords_0_05_ignores_doublon_negatif_illisible_nul_au_dela_ignores_tri",
      D.get("ca_bords") == [[["p", 2, 3], ["p_b30", 3, 7], ["p_b70", 7, 12], ["n", 0, 12]], 2], D.get("ca_bords"))
check("ca_refus_clip_absent_verrou_de_sa_piste_aucune_coupe_times_ou_clips_illisibles_autre_piste_verrouillee_passe",
      D.get("ca_refus") == [["clip", 0, 2, "Clip introuvable — rien à découper."],
                            ["verrou", 0, 2, "Piste V1 verrouillée — déverrouillez-la pour découper ce plan."],
                            ["", 1, 3],
                            ["aucune_coupe", 0, "Aucun changement de plan à découper dans ce clip."],
                            ["aucune_coupe", 0], ["clip", 0, 0]],
      D.get("ca_refus"))
check("ca_une_coupe_au_singulier_clip_sans_srcIn_part_de_0",
      D.get("ca_un") == [[["q", "v1", 0, 2, None, None, None], ["q_b20", "v1", 2, 4, 2, "cut", 0]], "1 coupe aux changements de plan"],
      D.get("ca_un"))
check("ca_clip_sans_source_ne_gagne_pas_de_srcIn",
      # temoin : la meme coupe AVEC source pose srcIn 2 (ligne precedente)
      D.get("ca_sans_src") == [["q", "v1", 0, 2, None, None, None], ["q_b20", "v1", 2, 4, None, "cut", 0]]
      # faute n°6 (revue 24/09) : chaque niveau garde sa longueur avant l'index
      and isinstance(D.get("ca_un"), list) and len(D["ca_un"]) > 0 and isinstance(D["ca_un"][0], list)
      and len(D["ca_un"][0]) > 1 and isinstance(D["ca_un"][0][1], list) and len(D["ca_un"][0][1]) > 4
      and D["ca_un"][0][1][4] == 2, D.get("ca_sans_src"))
# revue 24/09 : ECART MINIMAL entre coupes (chaine de candidates, DZM_CUT_BORD) -- la rafale 7 ; 7,001 ; 7,04 ; 7,06
# (dans le desordre aussi) garde la seule premiere ; temoin : 7 ; 7,1 en garde deux
check("ca_ecart_minimal_0_05_entre_candidates_une_rafale_fait_une_coupe_temoin_deux_coupes_a_0_1",
      D.get("ca_ecart") == [1, [7, 12, 12], 2, [7, 7.1, 12, 12]], D.get("ca_ecart"))
check("ca_moitie_droite_garde_label_src_fx_comme_la_lame", D.get("ca_champs") == ["P", {"job_id": "j"}, ["x"]], D.get("ca_champs"))
check("ca_pur_entree_intacte_tableau_neuf_autres_clips_memes_objets", D.get("ca_pur") == [True, True, True], D.get("ca_pur"))
_L7BC = _corps("dzmCutAt")
check("l7b_ca_coeur_pur_dzmUniqueId_x1_bord_par_constante_export_cutAt_x1",
      len(_L7BC) > 300
      and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(|setClips|pushHistory", _L7BC)
      and _L7BC.count("dzmUniqueId(") == 1 and _L7BC.count("DZM_CUT_BORD") == 3 and _L7BC.count(".05") == 0
      and _SRCb.count("var DZM_CUT_BORD=.05;") == 1
      and len(_DT) > 1000 and _DT.count("cutAt:dzmCutAt,") == 1 and _SRCb.count("cutAt:") == 1,
      (len(_L7BC), _L7BC.count("dzmUniqueId("), _L7BC.count("DZM_CUT_BORD"), _DT.count("cutAt:dzmCutAt,")))

print("\n[33] L7-B D-34 : la note etoile d'un rendu — dzmRatingNorm / dzmRatingNext purs, etoiles et chips du tiroir (tache 7, 24/09/2026)")
# ── L7-B D-34 (24/09/2026, tache 7, decision n°5 du plan). La note vit EN BASE (jobs.rating, PUT /api/jobs/{id}/rating,
# GET /api/jobs?min_rating= : banc backend test_montage_l7b_notes.py). Ici le coeur PUR du client : ratingNorm lit ce que
# le serveur rend (entier 0..5, tout le reste -> 0, MEME juge que la route qui refuse "3", 3.5, true) ; ratingNext : l'etoile
# cliquee devient la note, l'etoile COURANTE la retire (0), un clic illisible rend la note courante.
check("rn_norm_entier_0_5_sinon_0_chaine_flottant_bool_null_nan_hors_bornes",
      D.get("rn") == [0, 3, 5, 0, 0, 0, 0, 0, 0, 0, 0, 3], D.get("rn"))
check("rx_etoile_cliquee_devient_la_note_etoile_courante_la_retire",
      D.get("rx") == [3, 0, 5, 1, 0, 4, 3], D.get("rx"))
check("rx_bornes_clic_illisible_rend_la_note_courante_normalisee",
      D.get("rx_bornes") == [3, 3, 3, 3, 0, 2], D.get("rx_bornes"))
check("rx_suite_de_clics_3_3_5_2_2", D.get("rx_suite") == [3, 0, 5, 2, 0], D.get("rx_suite"))
check("rchips_deux_seuils_3_puis_5_avec_titre",
      D.get("rchips") == [[3, "★ 3+", True], [5, "★ 5", True]], D.get("rchips"))
_L7N = {n: _corps(n) for n in ("dzmRatingNorm", "dzmRatingNext")}
check("l7b_rn_coeur_pur_ni_r_ni_x_ni_reseau_export_x1",
      all(len(c) > 60 for c in _L7N.values())
      and not any(re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(|setJobs", c) for c in _L7N.values())
      and len(_DT) > 1000 and _DT.count("ratingNorm:dzmRatingNorm,ratingNext:dzmRatingNext,") == 1
      and _SRCb.count("ratingNext:") == 1 and _SRCb.count("ratingNorm:") == 1,
      ({n: len(c) for n, c in _L7N.items()}, _DT.count("ratingNext:dzmRatingNext")))
# le TIROIR : cinq etoiles par ligne (clic qui n'atteint pas la ligne, glisser annule sur les etoiles), PUT optimiste avec
# retour arriere garde par un compteur par rendu, chips qui passent min_rating au serveur et rechargent depuis la page 0.
_DRW = _corps("DzmMediaDrawer")
check("l7b_tiroir_etoiles_clic_arrete_a_l_etoile_et_glisser_annule_sur_les_etoiles",
      len(_DRW) > 400 and _DRW.count('className:"svm-medstars",draggable:!0,') == 1
      # L7-B D-41 (tache 6) : le bouton « ✂ auto-clips » de la ligne annule AUSSI son glisser -> 2
      and _DRW.count("onDragStart:function(e){e.preventDefault();e.stopPropagation()}") == 2
      and _DRW.count("onClick:function(e){e.stopPropagation();e.preventDefault();noter(j,i)}") == 1
      and _DRW.count("[1,2,3,4,5].map(") == 1 and _DRW.count('className:"svm-medstar",') == 1
      and _DRW.count('var ti=i===cur?"Retirer la note ("+i+" ★)":"Noter "+i+" ★"') == 1
      # revue 24/09 : une etoile n'est pas une bascule -- aria-label = l'infobulle, plus d'aria-pressed
      and _DRW.count('title:ti,"aria-label":ti,') == 1 and _DRW.count('"aria-pressed":i<=cur') == 0,
      f"corps={len(_DRW)}")
check("l7b_tiroir_note_optimiste_put_puis_retour_arriere_garde_par_compteur",
      len(_DRW) > 400 and _DRW.count('fetch("/api/jobs/"+encodeURIComponent(jid)+"/rating",{method:"PUT",') == 1
      and _DRW.count("apres=dzmRatingNext(avant,clic)") == 1 and _DRW.count("avant=dzmRatingNorm(j.rating)") == 1
      and _DRW.find("pose(apres);") < _DRW.find('fetch("/api/jobs/"+encodeURIComponent(jid)')
      # revue 24/09 : le refus remet la derniere note CONFIRMEE par le serveur (et non la note d'avant le clic)
      and _DRW.count("noteSeq.current[jid]!==k)return;pose(noteConf.current[jid]);") == 1
      and _DRW.count("pose(avant)") == 0
      and _DRW.count('setNoteMsg("Note refusée : "') == 1,
      (_DRW.find("pose(apres);"), _DRW.find('fetch("/api/jobs/"+encodeURIComponent(jid)')))
check("l7b_tiroir_chips_passent_min_rating_au_serveur_et_rechargent_page_0",
      len(_DRW) > 400 and _DRW.count('+(minNote>0?"&min_rating="+minNote:"")') == 1
      and _DRW.count("},[o.open?1:0,qServ,minNote]);") == 1 and _DRW.count("charge(0,qServ,!0)") == 1
      and _DRW.count("DZM_NOTE_CHIPS.map(") == 1 and _DRW.count("setMinNote(minNote===n[0]?0:n[0])") == 1
      # temoin : la requete de base garde limit/offset/video=1
      and _DRW.count('"/api/jobs?limit="+DZM_MED_PAGE+"&offset="+off+"&video=1"') == 1,
      f"corps={len(_DRW)}")
# regle des hooks : les deux useState neufs et le useRef du compteur viennent AVANT le `return null` du tiroir ferme
_iN7 = _DRW.find("x.useState(0),minNote="); _iN8 = _DRW.find('x.useState(""),noteMsg=');
_iNr = _DRW.find("noteSeq=x.useRef({}),noteConf=x.useRef({}),noteFile=x.useRef({}),vague=x.useRef(0);"); _iNul2 = _DRW.find("return null")
check("l7b_tiroir_hooks_de_la_note_avant_le_return_null",
      0 <= _iN7 < _iNul2 and 0 <= _iN8 < _iNul2 and 0 <= _iNr < _iNul2, (_iN7, _iN8, _iNr, _iNul2))
# revue 24/09 (2) : les PUT d'un meme rendu partent EN FILE -- chaque envoi s'enchaine a la promesse du precedent
check("l7b_tiroir_put_en_file_par_rendu",
      len(_DRW) > 400 and _DRW.count("var envoi=(noteFile.current[jid]||Promise.resolve()).then(function(){") == 1
      and _DRW.count("noteFile.current[jid]=envoi}") == 1
      and _DRW.find("var envoi=(noteFile.current[jid]") < _DRW.find('fetch("/api/jobs/"+encodeURIComponent(jid)') < _DRW.find("noteFile.current[jid]=envoi}"),
      f"corps={len(_DRW)}")
# revue 24/09 (1) : sous filtre, l'offset suit la note CONFIRMEE (seuil franchi -> -1 / +1), jamais sur un refus ni apres rechargement
check("l7b_tiroir_offset_suit_le_seuil_au_succes_et_la_vague_de_chargement",
      len(_DRW) > 400 and _DRW.count("var dl=(apres>=seuil?1:0)-(c0>=seuil?1:0);") == 1
      and _DRW.count("if(dl)setOffset(function(o2){return Math.max(0,o2+dl)})") == 1
      and _DRW.count("if(vivant.current&&seuil>0&&vague.current===v0)") == 1
      and _DRW.count("if(remplace)vague.current++;") == 1 and _DRW.count("var seuil=minNote,v0=vague.current;") == 1
      and _DRW.find("var dl=") < _DRW.find(".catch(function(e){if(!vivant.current||noteSeq"),
      f"corps={len(_DRW)}")
# restes de T7 (fermes en T6, 24/09/2026) : la recharge depuis la page 0 attend TOUTES les files de PUT avant son GET,
# et vide ensuite les trois memoires des rendus dont la file est celle qu'on a attendue ; « Plus » n'attend pas
check("l7b_tiroir_recharge_page0_attend_les_notes_en_vol_puis_vide_les_memoires",
      len(_DRW) > 400 and _DRW.count("var att=remplace?Object.assign({},noteFile.current):null,fini={};") == 1
      # revue T6 : l'attente est bornee (DZM_MED_ATT = 15 s), le minuteur est retire des que les PUT sont retombes
      and _DRW.count("var enVol=att?new Promise(function(z){var h=setTimeout(z,DZM_MED_ATT);") == 1
      # cloture T8 (24/09/2026, reste c) : chaque file attendue marque sa FIN (`fini`) ; apres le plafond de 15 s, un
      # rendu dont le PUT est ENCORE en cours garde ses trois memoires (temoin : un rendu sans file est vide)
      and _DRW.count("Promise.all(Object.keys(att).map(function(k2){return att[k2].then(function(){fini[k2]=1})})).then(function(){clearTimeout(h);z()})}):Promise.resolve();") == 1
      and _SRCb.count("var DZM_MED_ATT=15000;") == 1
      and _DRW.find("var enVol=") < _DRW.find("return enVol.then(function(){") < _DRW.find("return fetch(u).then(")
      and _DRW.count("if(noteFile.current[k2]!==att[k2]||(att[k2]&&!fini[k2]))return;") == 1
      and _DRW.count("delete noteSeq.current[k2];delete noteConf.current[k2];delete noteFile.current[k2]") == 1
      and _DRW.count("fetch(u)") == 1,
      f"corps={len(_DRW)}")

print("\n[34] L7-B D-40 : le cadrage d'un clip V1 — dzmReframeOf / At / K / Pos / Css purs (tache 4, 24/09/2026)")
# ── L7-B D-40 (24/09/2026, tache 4, decision n°3 du plan). dzmReframeOf est la regle MEME de _reframe_of du backend
# (d70989c) : centre / illisible -> null (rien ne part), manuel x borne, suivi t borne a (end-start) x vitesse (vitesse
# bornee 0,25..4), x borne, tri stable, doublons a 5 ms (le dernier gagne), <= 240. t en secondes de SOURCE depuis srcIn.
_M = {"mode": "manuel"}
check("rf_modes_centre_inconnu_illisible_null_manuel_borne_chaine_lue_bool_vide_base16_nan_null",
      D.get("rf_modes") == [None, None, None, None, None, dict(_M, x=0.3), dict(_M, x=1), dict(_M, x=0), dict(_M, x=0.25),
                            None, None, None, None, None, None, None], D.get("rf_modes"))
# revue finale (24/09/2026) : RB lit la source depuis srcIn 1 -> fenetre [1, 5] en temps ABSOLU. Le point de bord
# gauche (t 0) est remplace par 1,0001 -> 0 puis 1,003 -> 0,003 (doublons a 5 ms, le dernier gagne) ; 9 -> 0,7 tombe
# a droite, 5 -> 0,9 est PILE sur le bord (aucun point de bord ajoute)
check("rf_suivi_fenetre_srcIn_duree_x_0_1_illisibles_ignores_tri_stable_doublon_5ms_le_dernier_gagne",
      D.get("rf_suivi") == {"mode": "suivi", "points": [{"t": 0.003, "x": 0.45}, {"t": 1, "x": 1}, {"t": 4, "x": 0.9}]},
      D.get("rf_suivi"))
# un point a t 7 absolu, srcIn 1 -> t 6 relatif ; vitesse 0 (x1) : fenetre [1,5], le point tombe, bord droit a 4 ;
# 0,1 -> 0,25 : fenetre [1, 2], bord a 1 ; sans start : pas de borne droite
check("rf_vitesse_duree_de_source_x2_bornee_4_nulle_1_chaine_sans_start_non_borne_0_1_vaut_0_25",
      D.get("rf_vitesse") == [6, 6, 4, 6, 6, 1, 6, 6, 4, 4, 4, 4], D.get("rf_vitesse"))
check("rf_gestes_decoupe_et_coupe_ripple_le_morceau_droit_cadre_0_5_0_8_le_gauche_0_2_0_5",
      D.get("rf_gestes") == [1, [[0, 0.2], [5, 0.5]], 5, [[0, 0.5], [5, 0.8]], 3, [[0, 0.38], [7, 0.8]]], D.get("rf_gestes"))
check("rf_fenetre_bords_interpoles_pile_sur_les_bords_tout_avant_tout_apres_sans_fin",
      D.get("rf_fenetre") == [[[0, 0.3], [1, 0.4], [2, 0.6]], [[0, 0.2], [2, 0.8]], [[0, 0.9]], [[2, 0.2]],
                              [[0, 0.3], [4, 0.7]]], D.get("rf_fenetre"))
check("rf_payload_points_absolus_lisibles_en_suivi_x_en_manuel_rien_au_centre_ni_sans_point",
      D.get("rf_payload") == [{"mode": "suivi", "points": [{"t": 4, "x": 1}, {"t": 6, "x": 0.4}]}, {"mode": "manuel", "x": 0.3},
                              None, None], D.get("rf_payload"))
check("rf_cap_240_points_sous_echantillonnes_premier_dernier_second",
      D.get("rf_cap") == [240, 0, 4.99, 0.02], D.get("rf_cap"))
check("rf_r3_arrondi_du_millieme_comme_round_python_valeur_exacte_demi_au_pair",
      D.get("rf_r3") == [0.004, 0.062, 0.188, 0.005, 1, 2.062, 0.312], D.get("rf_r3"))
check("rf_vide_suivi_sans_point_valable_null", D.get("rf_vide") == [None, None, None, None], D.get("rf_vide"))
check("rf_at_constante_avant_apres_lerp_entre_manuel_x_sans_cadrage_0_5",
      D.get("rf_at") == [0.2, 0.2, 0.4, 0.5, 0.6, 0.6, 0.7, 0.5, 0.2, 0.5], D.get("rf_at"))
check("rf_k_largeur_relative_paysage_dans_portrait_portrait_dans_paysage_meme_ratio_manquants_null",
      D.get("rf_k") == [3.1605, 0.3164, 1, None, None, None], D.get("rf_k"))
check("rf_pos_formule_du_crop_bornee_k_inutile_ou_inconnu_null",
      D.get("rf_pos") == [0.5, 0, 1, 0.2, None, None, None, 1, 0.5, 1], D.get("rf_pos"))
check("rf_css_apercu_manuel_et_suivi_vide_sans_cadrage_portrait_cadre_ou_source_non_mesures_centre_garde",
      # revue finale : le suivi (0,0) -> (4,1) ABSOLU lu depuis srcIn 1 -> bord gauche (0 ; 0,25), (3 ; 1) : a t 2, x 0,75
      D.get("rf_css") == ["20.74% 50%", "", "", "", "", "86.57% 50%", ""], D.get("rf_css"))
check("rf_remplace_la_source_retire_les_points_garde_centre_manuel_suivi_devient_centre_note_dite_temoin_sans_points",
      D.get("rf_remplace") == [[None, True, True], [{"mode": "manuel", "x": 0.3}, True, False], [None, True, False],
                               [{"mode": "manuel", "x": 0.3}, False, False], [None, False, False]], D.get("rf_remplace"))
check("rf_pur_entree_intacte_points_neufs", D.get("rf_pur") == [True, True, True, 4], D.get("rf_pur"))
_L7RF = {n: _corps(n) for n in ("dzmRfNum", "dzmRfR3", "dzmRfSpeed", "dzmRfLerp", "dzmRfPoints", "dzmReframeOf", "dzmReframeAt",
                                 "dzmReframePayload", "dzmReframeK", "dzmReframePos", "dzmReframeCss")}
check("l7b_rf_coeur_pur_ni_r_ni_x_ni_reseau_ni_dom_constantes_uniques_exports_x1",
      all(len(c) > 80 for c in _L7RF.values())
      and not any(re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(|setClips|style\.", c) for c in _L7RF.values())
      and _SRCb.count("var DZM_RF_MAX=240,DZM_RF_UTILE=1.001;") == 1
      and _L7RF["dzmReframeOf"].count("DZM_RF_MAX") == 3 and _L7RF["dzmReframeOf"].count("240") == 0
      and _L7RF["dzmReframeOf"].count("dzmRfR3(q.t-a)") == 1 and _L7RF["dzmReframeOf"].count("dzmRfLerp(pts,") == 2 and _L7RF["dzmReframeOf"].count("dzmR3(") == 0 and _L7RF["dzmReframeOf"].count("<.005") == 1
      and len(_DT) > 1000
      and _DT.count("reframeOf:dzmReframeOf,reframePayload:dzmReframePayload,reframeAt:dzmReframeAt,reframeK:dzmReframeK,reframePos:dzmReframePos,reframeCss:dzmReframeCss,") == 1
      and all(_SRCb.count(k + ":dzmReframe") == 1 for k in ("reframeOf", "reframePayload", "reframeAt", "reframeK", "reframePos", "reframeCss")),
      ({n: len(c) for n, c in _L7RF.items()}, _DT.count("reframeOf:dzmReframeOf")))
# LA SECTION « Cadrage » de l'inspecteur de plan (DzmPlanProps, couche) : trois modes, curseur du manuel (leger, rafale),
# « Analyser le mouvement » (o.onReframe), grise-jamais-masque (E-12), le second useState APRES la garde.
_PP = _SRCb[_SRCb.find("function DzmPlanProps(o){"):_SRCb.find("function DzmDzRects(o){")]
check("l7b_rf_section_cadrage_trois_modes_curseur_leger_analyse_grisee_hooks_apres_garde",
      len(_PP) > 3000 and _PP.count('row("Cadrage",') == 1 and _PP.count('row("Position",') == 1 and _PP.count('row("Mouvement",') == 1
      and _PP.count('rfBtn("centre","Centré",') == 1 and _PP.count('rfBtn("suivi","Suivre",') == 1 and _PP.count('rfBtn("manuel","Manuel",') == 1
      and _PP.count('children:"Analyser le mouvement"') == 1 and _PP.count("disabled:rfSans||rfBusy,") == 2  # l analyse et (revue 24/09) le curseur gele
      and _PP.count("rfBusy?rfGel:") == 5
      and _PP.count("rfSans||rfBusy,function(){if(rfPts)") == 1 and _PP.count("rfNon") >= 5
      and _PP.count("x:Math.max(0,Math.min(100,v))/100})},!1)") == 1  # le curseur : leger (rafale 600 ms)
      and _PP.count('on({reframe:rfPts?{mode:"centre",points:rfPts}:void 0},!0)') == 1
      and _PP.count("Promise.resolve(o.onReframe()).then(fin,fin)") == 1
      and 0 <= _PP.find("if(!c)return null;") < _PP.find("x.useState(2)") < _PP.find("x.useState({})") < _PP.find('row("Cadrage",')
      and _PP.count("x.useState(") == 2 and _PP.count("DzTracks") == 0,
      f"hote={len(_PP)} useState={_PP.count('x.useState(')}")
print("\n[35] L7-B D-41 : les auto-clips d'un rendu — dzmAcPayload et ses formateurs purs, popover et tiroir (tache 6, 24/09/2026)")
# ── L7-B D-41 (24/09/2026, tache 6, decision n°4 du plan). Le corps de POST /api/montage/autoclips (T5 : 9c55f40, 031dd6a)
# est construit par UN coeur pur. LA REGLE DE LA DEPENSE : `confirm:true` part SEULEMENT si la case « Payer » est cochee
# (true strict) ET qu'une estimation ok a ete vue POUR CETTE SOURCE ET sans texte connu ; tout le reste n'envoie rien.
check("ac_cle_chaine_telle_quelle_objet_en_json_vide_pour_rien",
      D.get("ac_cle") == ['{"job_id":"j1"}', "p/x.mp4", "", "", '{"b":1,"a":2}'], D.get("ac_cle"))
check("ac_n_entier_1_8_arrondi_4_pour_l_illisible",
      D.get("ac_n") == [3, 5, 2, 1, 8, 4, 4, 4, 4, 4, 4, 4, 1], D.get("ac_n"))
check("ac_base_n4_llm_vrai_lang_fr_sans_texte_ni_persona_ni_confirm",
      D.get("ac_base") == {"src": {"job_id": "j1"}, "n": 4, "llm": True, "lang": "fr"}, D.get("ac_base"))
check("ac_llm_seul_false_l_eteint", D.get("ac_llm") == [False, True, True], D.get("ac_llm"))
check("ac_texte_rogne_blanc_ou_non_chaine_absent", D.get("ac_text") == ["bonjour", False, False], D.get("ac_text"))
check("ac_persona_rognee_60_car_vide_absente", D.get("ac_persona") == ["gamer", 60, False], D.get("ac_persona"))
check("ac_confirm_seulement_coche_de_l_estimation_affichee_ok_cette_source_cout_lisible_et_sans_texte",
      # temoins positifs en tete et en queue ; douze negations entre (dont la coche BOOLEENNE et la COPIE : revue T6)
      D.get("ac_confirm") == [True, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, True], D.get("ac_confirm"))
check("ac_max_usd_le_cout_coche_seulement_avec_confirm",
      D.get("ac_max") == [0.05, False, 0], D.get("ac_max"))
check("ac_lang_cinq_langues_sinon_fr",
      D.get("ac_lang") == ["en", "it", "de", "es", "fr", "fr", "fr", "fr", "fr"], D.get("ac_lang"))
check("ac_source_illisible_null_chaine_gardee",
      D.get("ac_src") == [None, None, None, None, None, "p.mp4"], D.get("ac_src"))
check("ac_pur_entree_intacte_objet_neuf_cles_exactes",
      D.get("ac_pur") == [True, True, True, ["lang", "llm", "n", "persona", "src", "text"], 3], D.get("ac_pur"))
check("ac_usd_virgule_deux_decimales_moins_d_un_centime_illisible",
      D.get("ac_usd") == ["0,05 $", "< 0,01 $", "0,00 $", "1,23 $", "? $", "? $", "? $"], D.get("ac_usd"))
check("ac_est_cout_duree_fournisseur_refus_dit_sa_raison",
      D.get("ac_est") == ["Transcription payante : ≈ 0,05 $ · ~40 s · ElevenLabs",
                          "Transcription payante : ≈ 0,40 $ · ~5 min · openai",
                          "Pas de transcription payante possible — Aucune clé",
                          "Pas de transcription payante possible", "",
                          "Transcription payante : ≈ 0,01 $ · ~1 s · fournisseur inconnu"], D.get("ac_est"))
check("ac_tr_cache_dit_deja_payee_reutilisee_chapitre_non_appele_dit_par_son_nom",
      D.get("ac_tr") == ["texte connu calé sur le son (gratuit)", "texte : chapitre",
                         "transcription déjà payée, réutilisée (elevenlabs)", "transcription payée (openai)",
                         "texte : ?", "texte : toString", "texte : zz"], D.get("ac_tr"))
check("ac_clip_bornes_duree_origine",
      D.get("ac_clip") == ["12,0 → 44,5 s · 32,5 s · IA", "0,0 → 15,0 s · 15,0 s · heuristique",
                           "? → ? s · ? s · heuristique", "? → ? s · ? s · heuristique"], D.get("ac_clip"))
# cloture T8 (24/09/2026, reste b) : l'estimation du 409 « cout depasse » -> vue NON cochee, pour la source ; la
# coche de l'ancienne ne couvre pas la nouvelle (0) ; cocher la nouvelle la couvre (temoin : True, max_usd 0,4)
check("ac_409_estimation_du_corps_marquee_pour_la_source_objet_neuf_null_sinon_coche_ancienne_ne_couvre_pas",
      D.get("ac_409") == [{"ok": True, "usd": 0.4, "provider": "elevenlabs", "pour": '{"job_id":"j1"}'}, True,
                          None, None, None, None, 0, True, 0.4], D.get("ac_409"))
_L7AC = {n: _corps(n) for n in ("dzmAcCle", "dzmAcNum", "dzmAcPayload", "dzmAcDec", "dzmAcUsd", "dzmAcEstTxt", "dzmAcTrTxt", "dzmAcClipTxt", "dzmAcEstRefus")}
check("l7b_ac_coeur_pur_ni_r_ni_x_ni_reseau_ni_dom_exports_x1",
      all(len(c) > 60 for c in _L7AC.values())
      and not any(re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|fetch\(|setClips|pushHistory", c) for c in _L7AC.values())
      and _L7AC["dzmAcPayload"].count("{b.confirm=!0;b.max_usd=v.usd}") == 1 and _L7AC["dzmAcPayload"].count("confirm") == 1
      and _L7AC["dzmAcPayload"].count("e.payer===v") == 1 and _L7AC["dzmAcPayload"].count("e.payer===!0") == 0
      and len(_DT) > 1000
      and _DT.count("acCle:dzmAcCle,acNum:dzmAcNum,acPayload:dzmAcPayload,acUsd:dzmAcUsd,acEstTxt:dzmAcEstTxt,acTrTxt:dzmAcTrTxt,acClipTxt:dzmAcClipTxt,Autoclips:DzmAutoclips,") == 1
      and _SRCb.count("acPayload:") == 1 and _SRCb.count("Autoclips:") == 1
      and _DT.count("acEstRefus:dzmAcEstRefus,") == 1 and _SRCb.count("acEstRefus:") == 1,
      ({n: len(c) for n, c in _L7AC.items()}, _DT.count("acPayload:dzmAcPayload")))
# LE POPOVER : ses dix useState sans garde avant (aucun `return null`), le corps passe TOUJOURS par le coeur (aucun
# `confirm` litteral), la case « payer » se decoche des l'envoi confirme, quatre gardes d'obsolescence (numero de
# requete + cle de la source + vivant), l'ouverture passe par o.onOpenProject, « Creer » est arme, AUCUNE ecriture de
# la timeline (temoin de longueur).
_AC = _SRCb[_SRCb.find("function DzmAutoclips(o){"):_SRCb.find("/* E-5 (lot E-B, tache 4, 23/09/2026) ")]  # borne : le docstring E-5 qui suit (il cite localStorage)
check("l7b_ac_popover_hooks_coeur_obsolescence_armement_aucune_ecriture_de_timeline",
      len(_AC) > 3000 and _AC.count("x.useState(") == 11 and _AC.count("return null") == 0
      and _AC.count('className:"svm-pop dzm-autoclips"') == 1
      and _AC.count("var b=dzmAcPayload({src:o.src,text:text,n:n,persona:persona,llm:llm,lang:lang,payer:payer,vu:vu});") == 1
      and _AC.count("confirm:") == 0 and _AC.count("paye=b.confirm===!0") == 1 and _AC.count("if(paye)setPayer(null);") == 1
      # revue T6 : la coche retombe a CHAQUE estimation (poseVu, seul chemin vers setVu hors remise a zero), au texte, au
      # nombre, a la langue ; la case lit `payer===est` ; un second envoi confirme en vol ne part pas (useRef)
      and _AC.count("var poseVu=function(v){setVu(v);setPayer(null)};") == 1 and _AC.count("setVu(") == 2
      # cloture T8 (24/09/2026) : poseVu x3 -- l'estimation du 409 passe AUSSI par poseVu (donc decochee)
      and _AC.count("poseVu(") == 3 and _AC.count(";setPayer(null)}") == 4
      and _AC.count("var ne=dzmAcEstRefus(e&&e.corps,k0);if(ne)poseVu(ne);") == 1
      and _AC.count("var er=new Error(") == 1 and _AC.count("er.corps=d;throw er") == 1
      and _AC.count("onChange:function(e){setPayer(e.target.checked?est:null)}") == 1 and _AC.count("coche=!!est&&payer===est") == 1
      and _AC.count("if(paye){if(enVolPaye.current)return;enVolPaye.current=!0}") == 1 and _AC.count("libere();if(!frais(q,k0))return;") == 2
      and _AC.count("var frais=function(q,k0){return vivant.current&&q===seq.current&&cle.current===k0};") == 1
      and _AC.count("if(!frais(q,k0))return;") == 4
      and _AC.count('x.useEffect(function(){seq.current++;setVu(null);setPayer(null);setRes(null);setMsg("");setBusy(0);setArm(-1)},[k]);') == 1
      and _AC.count('fetch("/api/montage/autoclips",{method:"POST",') == 1 and _AC.count('fetch("/api/montage/autoclips/create",{method:"POST",') == 1
      and _AC.count("o.onOpenProject({id:String(pid),name:nm})") == 1 and _AC.count("if(arm!==i){setArm(i);return}") == 1
      and _AC.count('className:"svm-goldbtn dzm-acgo",disabled:!!busy,') == 1
      and not re.search(r"setClips|pushHistory|addAsset|svmApplyProject|localStorage|DzTracks", _AC),
      f"corps={len(_AC)} useState={_AC.count('x.useState(')}")
# LE TIROIR : la ligne ouverte (un useState de plus, avant la garde), « ✂ auto-clips » dont le clic n'atteint pas la
# ligne, le popover monte avec la cle du job et o.onOpenProject relaye ; refermer le tiroir ferme le popover.
_iAc = _DRW.find("var s9=x.useState(null),ac=s9[0],setAc=s9[1];")
check("l7b_ac_tiroir_bouton_de_ligne_popover_cle_du_job_relai_d_ouverture",
      len(_DRW) > 400 and 0 <= _iAc < _DRW.find("return null")
      and _DRW.count("onClick:function(e){e.stopPropagation();e.preventDefault();setAc(j)}") == 1
      and _DRW.count('className:"svm-medac",draggable:!0,') == 1
      and _DRW.count("ac?r.jsx(DzmAutoclips,{src:{job_id:String(ac.job_id)},") == 1
      and _DRW.count("onOpenProject:o.onOpenProject},String(ac.job_id)):null") == 1
      and _DRW.count("x.useEffect(function(){if(!o.open)setAc(null)},[o.open?1:0]);") == 1,
      (_iAc, len(_DRW)))
# LA LISTE DES PROJETS : `openProj` (compteur) ouvre par le chemin MEME de « ouvrir » (surete puis ouvrir), refus dit
# quand la liste est occupee ; `n<=0` garde le montage (rien au premier rendu)
_PJ = _SRCb[_SRCb.find("var DzmProjects=function(props){"):_SRCb.find("  function saveAs(){")]
check("l7b_ac_projets_openProj_compteur_chemin_de_ouvrir",
      len(_PJ) > 2000 and _PJ.count("var oproj=props&&props.openProj,opn=Number(oproj&&oproj.n)||0;") == 1
      and _PJ.count("if(opn<=0||!oproj||!oproj.id)return;") == 1
      and _PJ.count("surete().then(function(s){if(s)ouvrir(p,s.nom)})},[opn]);") == 1
      and _PJ.count('if(busy){note("Liste des projets occupée') == 1,
      f"hote={len(_PJ)}")
print("\n[36] L5 D-27 D-29 D-30 D-32 : le coeur pur de la couleur — roues, courbes, masque, grade, temps de source (tache 4, 24/09/2026)")
# ── L5 (24/09/2026, tache 4, decisions 1, 2, 4, 8 du plan). Roue : disque (x, y) + maitre m -> trois canaux, angles
# R 90, G 210, B 330 ; courbes : MEMES regles que curves_clean (T1, backend) ; masque : MEMES bornes que mask_of (T2) ;
# grade = effets des types couleur sans bornes de temps ni `off` + masque. Temoins positifs dans chaque liste.
_CO_TYPES = ["grade", "lut", "grade_basic", "wheels", "curves", "colormatch", "huesat", "monochrome"]
check("co_types_les_huit_types_couleur_du_plan_gele", D.get("co_types") == [_CO_TYPES, True], D.get("co_types"))
check("co_neutre_roue_au_centre_identite_exacte_lift_0_gamma_1_gain_1",
      D.get("co_neutre") == [{"r": 0, "g": 0, "b": 0}, {"r": 1, "g": 1, "b": 1}, {"r": 1, "g": 1, "b": 1}], D.get("co_neutre"))
check("co_val_angles_r90_g210_b330_bornes_disque_borne_illisible_neutre_genre_inconnu_null",
      D.get("co_val") == [{"r": 1.5, "g": 0.75, "b": 0.75}, {"r": 0, "g": -0.217, "b": 0.217}, {"r": 2, "g": 2, "b": 2},
                          {"r": 4, "g": 4, "b": 4}, {"r": 0.5, "g": 0.5, "b": 0.5}, {"r": 0, "g": 0, "b": 0},
                          {"r": 1.5, "g": 0.75, "b": 0.75}, {"r": 1, "g": 1, "b": 1}, None, None], D.get("co_val"))
_rt = D.get("co_rt") if isinstance(D.get("co_rt"), list) and len(D.get("co_rt")) == 2 else [0, 9]
check("co_rt_aller_retour_60_points_a_1e_2", _rt[0] == 60 and isinstance(_rt[1], (int, float)) and _rt[1] <= 0.01, D.get("co_rt"))
check("co_from_moindres_carres_defauts_neutres_genre_inconnu_null",
      D.get("co_from") == [{"x": 0, "y": 1, "m": 0}, {"x": 0, "y": 0, "m": 1}, {"x": 0, "y": 0, "m": 0},
                           {"x": 0, "y": 0, "m": 0}, None], D.get("co_from"))
check("co_set_effet_neuf_cree_ou_complete_autres_cles_gardees_grade_basic_intact_entree_intacte",
      D.get("co_set") == [{"type": "wheels", "gain_r": 1.5, "gain_g": 0.75, "gain_b": 0.75},
                          {"type": "wheels", "lift_r": 0.1, "t0": 1, "gamma_r": 2, "gamma_g": 2, "gamma_b": 2},
                          {"type": "wheels", "lift_r": 0, "lift_g": 0, "lift_b": 0},
                          {"type": "wheels", "lift_r": 0.1, "t0": 1}, True, True], D.get("co_set"))
check("co_clean_regles_de_curves_clean_extremites_prolongees_tri_dernier_gagne_bornes_arrondi_python_jeton_invalide_saute",
      D.get("co_clean") == ["0/0.6 0.5/0.6 1/0.6", "0/0 0.5/0.7 1/1", "0/0 0.5/0.7 1/1", "0/0 0.5/0.7 1/1", "0/0 1/1", "0/0 1/1",
                            "0/0 0.5/1 1/1", "0/0 1/1", "0/0 1/1", "0/0.3 0.2/0.3 0.8/0.9 1/0.9", "0/0.5 0.123/0.5 1/0.5",
                            "0/0.2 0.1/0.2 1/0.2", "0/0.2 1/0.8", "0/0 1/1", "0/0 1/1", f"0/0.2 {round(0.0005, 3):g}/0.2 1/1"],
      D.get("co_clean"))
# 20 points i/19 -> 16 sous-echantillonnes (index round(k*19/15) : le second est l'index 1 = 1/19 arrondi), extremites gardees, idempotent
check("co_c20_seize_points_extremites_gardees_idempotent",
      D.get("co_c20") == [16, "0", "1", True, f"{round(1 / 19, 3):g}/{round(1 / 19, 3):g}"], D.get("co_c20"))
check("co_parse_str_chaine_canonique_et_points",
      D.get("co_parse") == [[[0, 0.6], [0.5, 0.6], [1, 0.6]], [[0, 0], [1, 1]]]
      and D.get("co_str") == ["0/0 0.5/0.7 1/1", "0/0 1/1", "0/0 1/1", "0/0 1/1", "0/0.3 0.25/0.3 1/0.3"],
      (D.get("co_parse"), D.get("co_str")))
_ev = D.get("co_eval") if isinstance(D.get("co_eval"), list) and len(D.get("co_eval")) == 10 else [None] * 10
check("co_eval_pchip_monotone_dans_0_1_passe_par_les_points_plateau_sans_depassement_lineaire_a_deux_points",
      _ev[:8] == [True, True, True, [0.5, 0.5, 0.5], 1, 0.3, 0.2, 0.8], _ev)
# la mesure du plan : 64 -> 83 en pchip, 81 en natural (spline naturelle : 81,6) -- la valeur calculee tombe dans la
# fenetre pchip et HORS de la naturelle ; chaine et points donnent la meme valeur
check("co_eval_pchip_comme_ffmpeg_64_vers_83_pas_la_spline_naturelle",
      isinstance(_ev[8], (int, float)) and 82.5 <= _ev[8] <= 84.5 and _ev[8] == _ev[9], _ev[8:])
check("co_mask_bornes_de_mask_of_forme_inconnue_non_objet_trop_petit_null_arrondi_1e_4_objet_neuf",
      D.get("co_mask") == [{"shape": "ellipse", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0.1, "inv": True},
                           {"shape": "rect", "x": 0, "y": 0.8, "w": 1, "h": 0.2, "soft": 0.5, "inv": False},
                           None, None, None, None, None, None, None,
                           {"shape": "rect", "x": 0.1235, "y": 0.5, "w": 0.5, "h": 0.25, "soft": 0, "inv": False},
                           None, {"shape": "ellipse", "x": 0, "y": 0, "w": 1, "h": 1, "soft": 0, "inv": False}, True],
      D.get("co_mask"))
_MK = {"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}
check("co_take_sans_t0_ni_off_ni_grain_ni_effet_eteint_wheels_actif_emporte_masque_normalise_rien_a_prendre_null_entree_intacte",
      D.get("co_take") == [{"effects": [{"type": "wheels", "gain_r": 1.2}], "mask": _MK},
                           None, None, {"effects": [], "mask": dict(_MK, shape="ellipse")},
                           {"effects": [{"type": "lut", "lut": "a"}], "mask": None}, None, True, True], D.get("co_take"))
check("co_paste_grain_a_sa_place_grade_basic_remplace_par_wheels_masque_pose_ou_retire_entree_intacte_copies",
      D.get("co_paste") == [[{"type": "grain", "amount": 1}, {"type": "wheels", "gain_r": 1.2}, {"type": "blur"}], False, "t",
                            [{"type": "grain"}, {"type": "curves", "pts_m": "0/0 1/1"}],
                            {"shape": "ellipse", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "soft": 0, "inv": False},
                            True, [{"type": "grain", "amount": 1}, {"type": "blur"}],
                            ["grain", "wheels", "blur"], True, True, True], D.get("co_paste"))
check("co_cm_un_seul_colormatch_a_la_place_du_premier_sinon_en_queue",
      D.get("co_cm") == [[{"type": "grain"}, {"type": "colormatch", "y_gain": 1.5}, {"type": "blur"}],
                         [{"type": "grain"}, {"type": "colormatch", "y_gain": 1.5}], [{"type": "colormatch", "y_gain": 2}],
                         1, 4, True], D.get("co_cm"))
check("co_src_srcin_plus_ecart_fois_vitesse_hors_plan_milieu_vitesse_bornee",
      D.get("co_src") == [3, 1, 5, 5, 5, 5, 3, 1, 0, 5, 0.833], D.get("co_src"))
# ── revue T4 (24/09/2026). (1) un effet couleur eteint n'est ni emporte ni reactive ; temoins : actif emporte, `off` retire.
check("co_paste_off_effet_eteint_ni_emporte_ni_reactive_a_la_pose_effet_actif_garde_off_retire",
      D.get("co_paste_off") == [[{"type": "grain", "amount": 1}, {"type": "wheels", "gain_r": 1.1}, {"type": "blur"}],
                                [{"type": "grain", "amount": 1}, {"type": "lut", "lut": "z"}, {"type": "blur"}], None,
                                {"effects": [{"type": "wheels", "gain_r": 1}], "mask": None}], D.get("co_paste_off"))
# (2) la regle UNIQUE des courbes : les 60 vecteurs partages rejoues sous node, 0 divergence (detail calcule AVANT).
_cv = D.get("co_vec") if isinstance(D.get("co_vec"), list) and len(D.get("co_vec")) == 2 else [0, ["co_vec absent"]]
_cv_dv = _cv[1] if isinstance(_cv[1], list) else ["co_vec illisible"]
# revue T4 (24/09, T4-2) : 60 -> 61 vecteurs -- le DEMI EXACT au pair (0,0625 -> 0,062 ; 0,1875 -> 0,188, sortie de
# curves_clean Python mesuree) : la mutation `(f%2?f+1:f)` -> `f+1` de dzmCoR rougit ici (pin realigne, pas affaibli)
check("co_vec_regle_unique_des_courbes_les_61_vecteurs_partages_rejoues_zero_divergence_demi_exact_au_pair_present",
      len(_L5_VEC) == 61 and _cv[0] == 61 and _cv_dv == []
      and {"in": "0.0625/0.1875", "out": "0/0.188 0.062/0.188 1/0.188"} in _L5_VEC, (len(_L5_VEC), _cv[0], _cv_dv))
# (3) trente masques croises avec mask_region.mask_of ; temoins : au moins dix valides ET dix refuses cote Python.
_mx_js = D.get("co_maskx") if isinstance(D.get("co_maskx"), list) else []
_mx_py = [_py_mask_of(m) for m in _L5_MASKS] if _py_mask_of else []
_mx_dv = [(i, m, p, j) for i, (m, p, j) in enumerate(zip(_L5_MASKS, _mx_py, _mx_js)) if p != j]
check("co_maskx_trente_masques_croises_avec_mask_of_python_zero_divergence_valides_et_refuses",
      # revue T4 (24/09) : 30 -> 32 masques (« 1_0 », chiffres Unicode : refuses des deux cotes -- pin realigne) ;
      # re-revue T6 (24/09) : 32 -> 33 (« ﻿0.5 » : LU des deux cotes -- pin realigne)
      _py_mask_of is not None and len(_L5_MASKS) == 33 and len(_mx_py) == 33 and len(_mx_js) == 33 and _mx_dv == []
      and sum(p is not None for p in _mx_py) >= 10 and sum(p is None for p in _mx_py) >= 10,
      (_py_mask_err, len(_mx_js), _mx_dv))
# ── revue T4 (24/09/2026, second passage). T4-1 : la pchip EPINGLEE au 1e-6 -- moyenne arithmetique, retrait de la borne
# 3*m0, retrait de la remise a 0 au changement de signe rougissent chacun (mutations rejouees) ; sans depassement.
check("co_eval_exact_pchip_epinglee_au_1e_6_trois_valeurs_sans_depassement_monotone",
      D.get("co_eval_exact") == [0.474259, 0.5488, 0.49169, 0.5, 0, True], D.get("co_eval_exact"))
# T4-6 : jamais d'exception (Symbol, valueOf qui leve, null, absent, texte -> x = 0 -> 0,2) ; temoins « 0.3 » et 0,3 lus
_ces = D.get("co_eval_sur") if isinstance(D.get("co_eval_sur"), list) and len(D.get("co_eval_sur")) == 3 else [None, None, None]
check("co_eval_sur_ne_leve_jamais_illisible_vaut_zero_texte_decimal_lu_fabrique_egale_a_l_evaluation",
      _ces[0] == [0.2, 0.2, 0.2, 0.2, 0.2, 0.473964, 0.473964] and _ces[1] is True and _ces[2] is True, _ces)
# T4-5 : Math.hypot -- un point enorme ramene sur le cercle (egal au point unitaire a 45 degres)
_chy = D.get("co_hypot") if isinstance(D.get("co_hypot"), list) and len(D.get("co_hypot")) == 2 else [None, None]
check("co_hypot_point_enorme_ramene_sur_le_cercle_comme_le_point_unitaire",
      isinstance(_chy[1], dict) and _chy[1] != {"r": 1, "g": 1, "b": 1} and _chy[0] == _chy[1], _chy)
# T4-7 : la vitesse sur V1 seulement ; temoins : V1 vitesse 2 -> 3, V1 vitesse illisible -> 1
check("co_src_v1_vitesse_lue_sur_v1_seulement_v2_et_sans_piste_a_vitesse_1",
      D.get("co_src_v1") == [2, 2, 3, 2], D.get("co_src_v1"))
_L5CO = {n: _corps(n) for n in ("dzmCoR", "dzmWheelToRgb", "dzmWheelFromRgb", "dzmWheelsSet", "dzmCurveTok", "dzmCurveClean",
                                 "dzmCurveParse", "dzmCurveStr", "dzmCurveFn", "dzmCurveEval", "dzmMaskOf", "dzmGradeEffCopy",
                                 "dzmIsColorEff", "dzmIsGradeEff", "dzmGradeTake", "dzmGradePaste", "dzmColorMatchPut",
                                 "dzmSrcTimeAt")}
_CO_EXP = ("colorTypes:DZM_COLOR_TYPES,wheelToRgb:dzmWheelToRgb,wheelFromRgb:dzmWheelFromRgb,wheelsSet:dzmWheelsSet,"
           "curveClean:dzmCurveClean,curveParse:dzmCurveParse,curveStr:dzmCurveStr,curveEval:dzmCurveEval,maskOf:dzmMaskOf,"
           "gradeTake:dzmGradeTake,gradePaste:dzmGradePaste,colorMatchPut:dzmColorMatchPut,srcTimeAt:dzmSrcTimeAt,")
check("l5_co_coeur_pur_ni_r_ni_x_ni_reseau_ni_dom_ni_stockage_constantes_uniques_bornes_de_temps_reutilisees_exports_x1",
      all(len(c) > 40 for c in _L5CO.values())
      # revue T4 (24/09) : dzmIsGradeEff et dzmCurveFn entrent dans la garde ; les noms d'API du navigateur s'ajoutent
      and not any(re.search(r"\br\.jsx|\bx\.use|localStorage|sessionStorage|\bwindow\b|\bdocument\b|\bnavigator\b|fetch\(|setClips|pushHistory|style\."
                            r"|requestAnimationFrame|addEventListener|getContext|AbortController|\bURL\.", c)
                  for c in _L5CO.values())
      and _L5CO["dzmCurveEval"].count("dzmCurveFn(pts)(x)") == 1 and _L5CO["dzmCurveFn"].count("dzmRfNum(x)") == 1
      and _L5CO["dzmIsGradeEff"].count("dzmIsColorEff(e)&&!e.off") == 1
      and all(_L5CO[n].count("Math.hypot(x,y)") == 1 and _L5CO[n].count("Math.sqrt") == 0 for n in ("dzmWheelToRgb", "dzmWheelFromRgb"))
      and _L5CO["dzmSrcTimeAt"].count('clip.tr==="v1"?dzmRfSpeed(clip.speed):1') == 1
      and _DT.count("curveFn:dzmCurveFn,") == 1
      and _SRCb.count('var DZM_COLOR_TYPES=Object.freeze(["grade","lut","grade_basic","wheels","curves","colormatch","huesat","monochrome"]);') == 1
      # les bornes de temps : la liste de dzmGradeCopy lue a l'APPEL (une dependance au chargement cassait le shim
      # node du banc bundle, L7_revue_I1, qui execute tout le code entre dzmKmImport et l'objet du contrat -- mesure 24/09)
      and _L5CO["dzmGradeEffCopy"].count('k!=="off"&&DZM_GRADE_TIMING.indexOf(k)<0') == 1 and _SRCb.count("DZM_GRADE_SANS") == 0
      and _L5CO["dzmCurveClean"].count("DZM_CURVE_MAX") >= 2 and _L5CO["dzmMaskOf"].count("dzmRfNum(") == 5
      and _L5CO["dzmSrcTimeAt"].count("dzmRfSpeed(") == 1
      and len(_DT) > 1000 and _DT.count(_CO_EXP) == 1
      and all(_SRCb.count(k) == 1 for k in _CO_EXP.split(",") if k),
      ({n: len(c) for n, c in _L5CO.items()}, _DT.count(_CO_EXP)))
print("\n[37] L5 D-27 D-29 D-30 D-28 : le panneau Etalonnage — aides pures et composant sous shim (tache 5, 24/09/2026)")
# ── L5 (24/09/2026, tache 5). Les aides PURES du panneau (pile, points de courbe, plan precedent, corps des deux routes
# de T3, empreinte d'obsolescence), puis DzmGradePanel et DzmMaskBox EXECUTES sous un jsx factice {t,p} et des hooks
# factices poses sur l'objet global le temps de l'appel. Faute n6 : chaque lecture passe par D.get / at().
check("gp_fx_premier_du_type_pose_a_la_place_du_premier_sinon_en_queue_entree_intacte",
      D.get("gp_fx") == [{"type": "wheels", "a": 1}, None, None,
                         [{"type": "grain"}, {"type": "wheels", "a": 9}, {"type": "blur"}, {"type": "wheels", "a": 2}],
                         [{"type": "grain"}, {"type": "curves"}], [{"type": "x"}], [True, True, 1]], D.get("gp_fx"))
check("gp_hit_point_le_plus_proche_a_la_tolerance_sinon_moins_un",
      D.get("gp_hit") == [1, -1, 0, -1, 2], D.get("gp_hit"))
check("gp_move_x_entre_les_voisins_extremites_fixes_en_x_y_borne_arrondi_hors_liste_copie_illisible_garde",
      D.get("gp_move") == [[[0, 0], [0.7, 0.9], [1, 1]], [[0, 0], [0.999, 0], [1, 1]], [[0, 0], [0.001, 1], [1, 1]],
                           [[0, 0.2], [0.5, 0.6], [1, 1]], [[0, 0], [0.5, 0.6], [1, 0.5]], [[0, 0], [0.5, 0.6], [1, 1]],
                           [[0, 0], [0.333, 0.667], [1, 1]], [[0, 0], [0.5, 0.6], [1, 1]]], D.get("gp_move"))
check("gp_add_insere_trie_refuse_x_existant_16_points_illisible_entree_intacte",
      D.get("gp_add") == [{"pts": [[0, 0], [0.25, 0.4], [0.5, 0.6], [1, 1]], "i": 1}, None, None, None, None, None, 1, True],
      D.get("gp_add"))
check("gp_del_retire_un_point_interieur_jamais_une_extremite_copie_neuve",
      D.get("gp_del") == [[[0, 0], [1, 1]], [[0, 0], [0.5, 0.6], [1, 1]], [[0, 0], [0.5, 0.6], [1, 1]], [], True], D.get("gp_del"))
check("gp_mid_milieu_du_plus_grand_ecart_sur_la_courbe",
      D.get("gp_mid") == [0.25, True, {"x": 0.5, "y": 0.5}, 0.6, None], D.get("gp_mid"))
check("gp_prev_voisin_gauche_en_contact_sinon_le_plus_proche_avant_sans_source_ecarte_autre_piste_rien",
      D.get("gp_prev") == ["a", "b", None, "c", None, None, None], D.get("gp_prev"))
_GT, _GA = {"src": {"job_id": "B"}, "t": 3}, {"src": {"job_id": "A"}, "t": 2}
check("gp_match_cible_temps_de_source_sous_la_tete_reference_milieu_du_precedent_auto_sans_reference",
      D.get("gp_match") == [{"target": _GT, "ref": _GA}, {"target": _GT, "auto": True}, None, None, None, {"target": _GT, "auto": True}],
      D.get("gp_match"))
_GF = {"src": {"job_id": "F"}, "t": 1, "w": 320}
check("gp_frame_effets_actifs_masque_avec_effets_seulement_largeur_paire_96_640",
      D.get("gp_frame") == [dict(_GF, effects=[{"type": "wheels", "gain_r": 1.2}],
                                 mask={"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}),
                            _GF, dict(_GF, w=96, effects=[{"type": "wheels", "gain_r": 1.2}],
                                      mask={"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}),
                            dict(_GF, w=640, effects=[{"type": "wheels", "gain_r": 1.2}],
                                 mask={"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}),
                            dict(_GF, w=240, effects=[{"type": "wheels", "gain_r": 1.2}],
                                 mask={"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}),
                            None, {"src": {"job_id": "F"}, "t": 2, "w": 242}], D.get("gp_frame"))
check("gp_sig_source_fenetre_geometrie_sans_les_effets", D.get("gp_sig") == [True, True, True, True, ""], D.get("gp_sig"))
check("gp_composants_exportes", D.get("gp_pure") == ["function", "function"], D.get("gp_pure"))
check("gp_null_sans_clip_sans_toucher_x_boite_sans_masque_lisible_ou_sans_effet_actif",
      "gp_null" in D and D.get("gp_null") == [None] * 7, D.get("gp_null"))
check("gp_box_boite_du_masque_en_pour_cent_du_cadre_forme_et_inversion",
      D.get("gp_box") == ["div", "dzm-maskbox", "ellipse", "1", {"left": "10%", "top": "20%", "width": "30%", "height": "40%"}, "rect", ""],
      D.get("gp_box"))
_GB = ["M", "R", "G", "B", "+ Point", "À plat", "Aucun", "Rectangle", "Ellipse", "Accorder sur le plan précédent", "Auto",
       "Copier le grade", "Coller le grade"]
_GR = D.get("gp_rendu") if isinstance(D.get("gp_rendu"), list) and len(D.get("gp_rendu")) == 12 else [None] * 12
check("gp_rendu_racine_titre_six_rangees",
      _GR[:4] == ["div", "dzm-plan dzm-gp", "Étalonnage", ["Roues", "Courbes", "Masque", "Accord", "Grade", "Aperçu"]], _GR[:4])
check("gp_rendu_treize_boutons_tous_titres_dans_l_ordre_seul_coller_grise_sans_grade_copie",
      _GR[4] == [[b, True, b == "Coller le grade"] for b in _GB], _GR[4])
# revue T5 (24/09, I-3) : le ref d'un canvas est un OBJET stable (x.useRef) -- une fonction recreee a chaque rendu
# faisait redessiner les quatre canvas par React a chaque image ; le dessin vit dans des effets (pin realigne)
check("gp_rendu_quatre_canvas_trois_roues_96_une_courbe_200_geste_et_ref_objet_stable_titres",
      _GR[5] == [[k, 96, 96, "function", "object", True] for k in ("lift", "gamma", "gain")] + [["curve", 200, 200, "function", "object", True]],
      _GR[5])
check("gp_rendu_huit_curseurs_trois_maitres_cinq_du_masque_valeurs_lues_une_case_inverser",
      _GR[6] == [[0, False, True], [0, False, True], [0, False, True], [25, False, True], [25, False, True], [50, False, True],
                 [50, False, True], [0, False, True]] and _GR[7] == [[False, False, True]], (_GR[6], _GR[7]))
# revue T5 (24/09) : 4 -> 5 useState (le compteur de relecture du grade, evenement storage) ; 2 -> 4 useEffect
# (montage, apercu [sig, id], roues [6 primitives], courbe [chaine, onglet]) -- pin realigne
check("gp_rendu_cinq_useState_quatre_useEffect_a_dependances_primitives_onglet_M_et_ellipse_presses",
      _GR[8:12] == [5, [0, 2, 6, 2], True, True], _GR[8:12])
_GV = D.get("gp_verrou") if isinstance(D.get("gp_verrou"), list) and len(D.get("gp_verrou")) == 14 else [None] * 14
check("gp_verrou_toute_ecriture_grisee_et_dite_onglets_et_copier_restent_tous_les_champs_grises",
      _GV == [[b, b not in ("M", "R", "G", "B", "Copier le grade"), b not in ("M", "R", "G", "B", "Copier le grade")] for b in _GB] + [True],
      _GV)
_MT = "Le masque limite les effets du plan : ajoutez-en un"
check("gp_vide_masque_grise_et_dit_accord_grise_rien_a_copier_ni_a_coller_curseurs_du_masque_grises",
      D.get("gp_vide") == [["M", False, "Courbe maître : les trois canaux ensemble"], ["R", False, "Courbe du canal rouge"],
                           ["G", False, "Courbe du canal vert"], ["B", False, "Courbe du canal bleu"],
                           ["+ Point", False, "Ajouter un point au milieu du plus grand écart (16 au plus) — ou cliquer dans la courbe"],
                           ["À plat", True, "Courbe déjà à plat sur ce canal"], ["Aucun", True, "Aucun masque posé"],
                           ["Rectangle", True, _MT], ["Ellipse", True, _MT],
                           ["Accorder sur le plan précédent", True, "Aucun plan précédent sur V1 : rien à accorder"],
                           ["Auto", False, "Accord automatique : neutralise la dominante et étire le contraste (pose ou remplace l'effet « Accord couleur »)"],
                           ["Copier le grade", True, "Rien à copier : ni effet couleur ni masque sur ce plan"],
                           ["Coller le grade", True, "Aucun grade copié (Copier le grade d'abord)"],
                           [False, False, False, True, True, True, True, True, True]], D.get("gp_vide"))
_W0 = {"type": "wheels", "gain_r": 1.5, "gain_g": 0.75, "gain_b": 0.75}
_CU = {"type": "curves", "pts_m": "0/0 0.5/0.7 1/1"}
_ME = {"shape": "ellipse", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}
_GG = D.get("gp_geste") if isinstance(D.get("gp_geste"), list) and len(D.get("gp_geste")) == 9 else [None] * 9
check("gp_geste_roue_double_clic_neutre_leger_maitre_leger_forme_lourde_aucun_retire_curseurs_legers_inverser_lourd_a_plat_lourd",
      _GG[:8] == [[{"effects": [{"type": "wheels", "gain_r": 1, "gain_g": 1, "gain_b": 1}, _CU]}, ["effects"], False],
                  [{"effects": [{"type": "wheels", "gain_r": 1.7, "gain_g": 0.95, "gain_b": 0.95}, _CU]}, ["effects"], False],
                  [{"mask": dict(_ME, shape="rect")}, ["mask"], True], [{}, ["mask"], True],
                  [{"mask": dict(_ME, x=0.4)}, ["mask"], False], [{"mask": dict(_ME, soft=0.3)}, ["mask"], False],
                  [{"mask": dict(_ME, inv=True)}, ["mask"], True],
                  [{"effects": [_W0, {"type": "curves", "pts_m": "0/0 1/1"}]}, ["effects"], True]], _GG[:8])
_GP = _GG[8] if isinstance(_GG[8], list) and len(_GG[8]) == 3 and isinstance(_GG[8][0], dict) else [{}, [], None]
_GPe = _GP[0].get("effects") if isinstance(_GP[0].get("effects"), list) and len(_GP[0].get("effects")) == 2 else [{}, {}]
check("gp_geste_plus_point_quatre_points_au_quart_sur_la_courbe_lourd",
      _GPe[0] == _W0 and str(_GPe[1].get("pts_m", "")).startswith("0/0 0.25/") and str(_GPe[1].get("pts_m", "")).endswith(" 0.5/0.7 1/1")
      and len(str(_GPe[1].get("pts_m", "")).split(" ")) == 4 and _GP[2] is True, _GP)
_GD = D.get("gp_grade") if isinstance(D.get("gp_grade"), list) and len(D.get("gp_grade")) == 5 else [None] * 5
_GTK = {"effects": [_W0, _CU], "mask": _ME}
check("gp_grade_copier_ecrit_gradeTake_coller_remplace_les_effets_couleur_masque_pose_lourd_json_illisible_grise",
      _GD == [_GTK, ["Grade copié (2 effets)", "Grade collé (2 effets)"], False,
              [[[{"type": "grain"}, _W0, _CU], True, _ME, True]], True], _GD)
# LE SOURCE : aides pures sans r / x / reseau / DOM / stockage ; composant : garde AVANT les hooks, gestes sur la fenetre sans
# capture, stockage en try/catch, deux routes appelees UNE fois chacune, URL de blob revoquee, anti-rebond 400 ms
_L5GP = {n: _corps(n) for n in ("dzmFxOf", "dzmFxPut", "dzmCurveHit", "dzmCurveMove", "dzmCurveAdd", "dzmCurveDel", "dzmCurveMid",
                                 "dzmGradePrev", "dzmMatchBody", "dzmFrameBody", "dzmGpSig")}
check("l5_gp_aides_pures_ni_r_ni_x_ni_reseau_ni_dom_ni_stockage",
      all(len(c) > 40 for c in _L5GP.values())
      and not any(re.search(r"\br\.jsx|\bx\.use|localStorage|sessionStorage|\bwindow\b|\bdocument\b|\bnavigator\b|fetch\(|setClips|pushHistory|style\.|URL\.", c)
                  for c in _L5GP.values())
      and _L5GP["dzmCurveAdd"].count("DZM_CURVE_MAX") == 1 and _L5GP["dzmGradePrev"].count("dzmVoisins(") == 1
      and _L5GP["dzmMatchBody"].count("dzmSrcTimeAt(") == 2 and _L5GP["dzmFrameBody"].count("dzmMaskOf(") == 1,
      {n: len(c) for n, c in _L5GP.items()})
_GPC = _SRCb[_SRCb.find("function DzmGradePanel(o){"):_SRCb.find("function DzmMaskBox(o){")]
check("l5_gp_composant_garde_avant_hooks_gestes_fenetre_sans_capture_stockage_protege_routes_x1_blob_revoque_400ms",
      len(_GPC) > 3000 and 0 <= _GPC.find("if(!c)return null;") < _GPC.find("x.useState(")
      # revue T5 (24/09) : 4 -> 5 useState, 2 -> 4 useEffect (pins realignes : rien par image, dessin dans des effets) ;
      # le geste passe par UNE aide qui garde le retrait (dzmGpDrag x2 : roue et courbe l'appellent par elle) ; le
      # dessin n'est plus dans un ref-fonction ; la lecture n'est plus dans le rendu (grade copie lu au cache)
      and _GPC.count("x.useState(") == 5 and _GPC.count("x.useEffect(") == 4
      and _GPC.count("ref:function") == 0 and _GPC.count("retrait.current=dzmGpDrag(e,") == 1 and _GPC.count("dzmGpDrag(") == 1
      and _GPC.count("jouant?null:dzmFrameBody(") == 1 and _GPC.count("if(!sig)return;") == 1
      and _GPC.count("dzmGpRead()") == 1 and _GPC.count("gsR.current.v!==DZM_GP_VER.n") == 1
      and _corps("dzmGpWrite").count("DZM_GP_VER.n++") == 1 and _corps("dzmGpDrawCurve").count("dzmCurveFn(pts)") == 1
      and _corps("dzmGpDrawCurve").count("dzmCurveEval(") == 0 and _corps("dzmGpDrag").count("return stop}") == 1
      and _GPC.count("setPointerCapture") == 0 and _SRCb.count("setPointerCapture") == 1
      # tache 6 (24/09/2026) : grade-frame 1 -> 2, la lightbox (DzmLightbox) appelle la meme route -- ecart date, pin realigne
      and _SRCb.count('dzmGpFetch("/api/montage/grade-frame",') == 2 and _SRCb.count('dzmGpFetch("/api/montage/color-match",') == 1
      and _GPC.count("URL.revokeObjectURL(") == 2 and _GPC.count("},400);") == 1 and _GPC.count("DzTracks") == 0
      and _SRCb.count('var DZM_GP_CLE="dz_montage_grade"') == 1
      and _corps("dzmGpRead").count("try{") == 1 and _corps("dzmGpWrite").count("try{") == 1
      and _corps("dzmGpRead").count("st||dzmTbStore()") == 1 and _corps("dzmGpWrite").count("st||dzmTbStore()") == 1
      and _corps("dzmGpDrag").count('w.addEventListener("pointermove",mv)') == 1 and _corps("dzmGpDrag").count("requestAnimationFrame(") == 1
      and len(_DT) > 1000
      and _DT.count("fxOf:dzmFxOf,fxPut:dzmFxPut,curveHit:dzmCurveHit,curveMove:dzmCurveMove,curveAdd:dzmCurveAdd,curveDel:dzmCurveDel,"
                    "curveMid:dzmCurveMid,gradePrev:dzmGradePrev,matchBody:dzmMatchBody,frameBody:dzmFrameBody,gpSig:dzmGpSig,"
                    "GradePanel:DzmGradePanel,MaskBox:DzmMaskBox,") == 1,
      f"corps={len(_GPC)} useState={_GPC.count('x.useState(')}")

print("\n[38] L5 D-31 D-32 : scopes sous le lecteur, lightbox des plans, gestes partages du grade (tache 6, 24/09/2026)")
# ── L5 (24/09/2026, tache 6). Les aides PURES (plan sous la tete, corps de /scopes, plans de la lightbox, file des
# vignettes, memoire de la bascule), les GESTES PARTAGES du grade (panneau, clavier, menu de clip : un stockage, une
# phrase), puis les deux composants : rendu sous shim, et leurs GARDES DE COURSE ET DE FUITE jouees en EXECUTION sous un
# mini-React (etats et effets persistants, minuteurs, fetch, URL et AbortController factices) -- une mutation qui retire
# une garde doit rougir ici, pas seulement un pin de texte. Faute n6 : chaque lecture passe par D.get / DX.get / at().
check("sc_at_plan_v1_sous_la_tete_debut_inclus_fin_exclue_v2_ignore_tete_illisible_rien",
      D.get("sc_at") == ["b", "a", "a", None, None, "d", None, None, None, "b", None, None], D.get("sc_at"))
_SCM = {"shape": "rect", "x": 0, "y": 0, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}
check("sc_body_corps_de_grade_frame_sans_largeur_effets_actifs_masque_avec_effets_sans_source_rien",
      D.get("sc_body") == [{"src": {"job_id": "A"}, "t": 1, "effects": [{"type": "wheels", "gain_r": 1.2}], "mask": _SCM},
                           {"src": {"job_id": "B"}, "t": 4}, None, None], D.get("sc_body"))
check("sc_store_cle_dz_montage_scopes_eteinte_par_defaut_1_0_magasin_en_panne_eteinte_rend_ce_qu_elle_pose",
      D.get("sc_store") == [False, True, True, "1", False, "0", False, False, True, "dz_montage_scopes"], D.get("sc_store"))
check("lb_plans_v1_dans_l_ordre_du_debut_bornes_lisibles_entree_intacte",
      D.get("lb_plans") == [["z", "a", "b", "d"], True, [], []], D.get("lb_plans"))
check("lb_next_au_plus_trois_en_vol_premieres_en_attente_max_illisible_trois_borne_a_trois",
      D.get("lb_next") == [["a", "b", "c"], ["d"], [], [], [], ["a", "b"], ["a", "b", "c"], ["a", "b", "c"], ["a", "b", "c"], 3],
      D.get("lb_next"))
_GCM = {"shape": "ellipse", "x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}
_GCs = {"effects": [{"type": "wheels", "gain_r": 1.2}], "mask": _GCM}
_GCn = "Aucun grade copié (Copier le grade d'abord)"
check("gc_copier_ecrit_le_grade_sans_bornes_ni_effet_eteint_rien_a_copier_stockage_en_panne_dit",
      at("gc", 0) == {"ok": True, "note": "Grade copié (1 effet)"} and at("gc", 1) == _GCs
      and at("gc", 2) == {"ok": False, "note": "Rien à copier : ni effet couleur ni masque sur ce plan"}
      and at("gc", 3) == {"ok": False, "note": "Copie refusée : stockage du navigateur indisponible."}
      and at("gc", 4) == {"ok": False, "note": "Rien à copier : ni effet couleur ni masque sur ce plan"} and at("gc", 11) is True,
      D.get("gc"))
check("gc_coller_rend_le_nouveau_clip_couleur_remplacee_a_sa_place_masque_pose_ou_retire_sans_grade_dit_entree_intacte",
      at("gc", 5) == {"clip": {"tr": "v2", "id": "t", "effects": [{"type": "blur"}, {"type": "wheels", "gain_r": 1.2}, {"type": "grain"}],
                               "mask": _GCM}, "note": "Grade collé (1 effet)"}
      and at("gc", 6) == {"clip": None, "note": _GCn} and at("gc", 7) == {"clip": None, "note": _GCn}
      and at("gc", 8) == {"clip": {"tr": "v2", "id": "t", "effects": [{"type": "blur"}, {"type": "lut", "file": "a.cube"}, {"type": "grade", "x": 1},
                                                                 {"type": "grain"}]}, "note": "Grade collé (2 effets)"}
      and at("gc", 9) is False and at("gc", 10) is True, D.get("gc"))
check("sc_null_sans_props_rien_sans_toucher_x", "sc_null" in D and D.get("sc_null") == [None, None], D.get("sc_null"))
_SCR = D.get("sc_rendu") if isinstance(D.get("sc_rendu"), list) and len(D.get("sc_rendu")) == 13 else [None] * 13
_SCt0 = ("Afficher les scopes du plan V1 sous la tête (forme d'onde, vecteurscope, histogramme de l'image étalonnée) "
         "— rafraîchis à l'arrêt, jamais pendant la lecture")
check("sc_rendu_eteint_un_bouton_titre_non_presse_aucun_message",
      _SCR[:4] == ["div", "dzm-scopes", [["Scopes", _SCt0, False, None]], []], _SCR[:4])
check("sc_rendu_allume_presse_mesure_en_cours_lecture_dite_aucun_plan_dit_plan_sans_source_dit",
      _SCR[4:9] == [[["Scopes", "Masquer les scopes", True, ""]], ["Mesure en cours…"],
                    ["Lecture : les scopes se rafraîchissent à l'arrêt"], ["Aucun plan sous la tête"], ["Plan sans source : rien à mesurer"]],
      _SCR[4:9])
# Correctif preuve ecran (24/09) : la puce vit dans la barre du lecteur, l'ENCART (dzm-scpop : image + ligne d'etat) est
# porte dans le cadre de lecture -- un quatrieme useState (le cadre hote) et un troisieme useEffect (le chercher, deps
# [on]) : 15 -> 20 et 10 -> 15, pins realignes ; l'encart n'existe qu'allume (eteint : 0 ; allume, arret ou lecture : 1).
check("sc_rendu_quatre_useState_trois_useEffect_par_rendu_encart_seulement_allume",
      _SCR[9:13] == [20, [0, 1], 15, [0, 1, 1]], _SCR[9:13])
_SCB = _corps("DzmScopes")
check("sc_encart_porte_dans_le_cadre_du_lecteur_cherche_a_l_allumage_repli_sans_portail",
      len(_SCB) > 200 and _SCB.count("Pu.createPortal(") == 1 and _SCB.count('typeof Pu!=="undefined"') == 1
      and _SCB.count('closest(".svm-playerzone")') == 1 and _SCB.count('querySelector(".svm-frame")') == 1
      and _SCB.count("isConnected") == 1 and _SCB.count("},[on]);") == 1 and _SCB.count('className:"dzm-scpop"') == 1,
      [_SCB.count(k) for k in ("Pu.createPortal(", 'closest(".svm-playerzone")', 'querySelector(".svm-frame")', "},[on]);")])
_LBR = D.get("lb_rendu") if isinstance(D.get("lb_rendu"), list) and len(D.get("lb_rendu")) == 10 else [None] * 10
check("lb_rendu_voile_trois_tuiles_v1_dans_l_ordre_titrees_clic_choisit_le_plan_voile_et_fermer_ferment_tout_bouton_titre",
      _LBR[:7] == ["div", "dzm-lbscrim", [["button", "a", True], ["button", "b", True], ["button", "d", True]], ["b"], 2, True, 4], _LBR[:7])
check("lb_rendu_sans_plan_v1_le_dit_deux_useState_un_useEffect_au_montage",
      _LBR[7:] == [["Aucun plan sur V1"], 4, [0]], _LBR[7:])
# LE SOURCE : aides pures sans r / x / reseau / DOM / stockage ; exports au contrat ; la route /scopes appelee UNE fois
_L5SC = {n: _corps(n) for n in ("dzmScopesAt", "dzmScopesBody", "dzmLbPlans", "dzmLbNext")}
check("l5_sc_aides_pures_ni_r_ni_x_ni_reseau_ni_dom_ni_stockage",
      all(len(c) > 40 for c in _L5SC.values())
      and not any(re.search(r"\br\.jsx|\bx\.use|localStorage|sessionStorage|\bwindow\b|\bdocument\b|\bnavigator\b|fetch\(|setClips|pushHistory|style\.|URL\.", c)
                  for c in _L5SC.values())
      and _L5SC["dzmScopesBody"].count("dzmFrameBody(") == 1 and _L5SC["dzmLbNext"].count("DZM_LB_MAX") == 2,
      {n: len(c) for n, c in _L5SC.items()})
check("l5_sc_exports_au_contrat_route_scopes_x1_grade_frame_x2_panneau_et_lightbox_gestes_partages_dans_le_panneau",
      _DT.count("scopesAt:dzmScopesAt,scopesBody:dzmScopesBody,scopesGet:dzmScopesGet,scopesSet:dzmScopesSet,SC_CLE:DZM_SC_CLE,"
                "lbPlans:dzmLbPlans,lbNext:dzmLbNext,LB_MAX:DZM_LB_MAX,gradeCopyDo:dzmGradeCopyDo,gradePasteDo:dzmGradePasteDo,gradeRead:dzmGpRead,"
                "Scopes:DzmScopes,Lightbox:DzmLightbox,") == 1
      and _SRCb.count('dzmGpFetch("/api/montage/scopes",') == 1 and _SRCb.count('dzmGpFetch("/api/montage/grade-frame",') == 2
      and _SRCb.count('var DZM_SC_CLE="dz_montage_scopes"') == 1
      and _GPC.count("dzmGradeCopyDo(c)") == 1 and _GPC.count("dzmGradePasteDo(cur.current)") == 1 and _GPC.count("dzmGpWrite(") == 0,
      [_SRCb.count('dzmGpFetch("/api/montage/scopes",'), _SRCb.count('dzmGpFetch("/api/montage/grade-frame",')])

# ── LES GARDES EN EXECUTION : un second shim (asynchrone), un mini-React ─────────────────────────────────────────────
PROBE_L5X = r"""
var T=window.DzTracks,out={},G=globalThis,r=null; /* `r` : le runtime jsx que la couche lit a l'appel (pose par mini) */
/* revue T5 (24/09) : `att(n)` facultatif = le montage des refs OBJETS (comme React, AVANT les effets) : chaque noeud dont
   p.ref est un objet encore vide reçoit att(n) -- le panneau dessine ses canvas depuis des effets, via des refs stables */
function mini(Comp,att){var H={s:[],f:[],e:[],p:null,out:null,dirty:!1};
  function render(p){if(p!==void 0)H.p=p;var r0=r,hx=Object.prototype.hasOwnProperty.call(G,"x"),x0=G.x,i=0,j=0,k=0,run=[];
    r={jsx:function(t,q){return {t:t,p:q}},jsxs:function(t,q){return {t:t,p:q}}};
    G.x={useState:function(v){var a=i++;if(!(a in H.s))H.s[a]=typeof v==="function"?v():v;
        return [H.s[a],function(nv){H.s[a]=typeof nv==="function"?nv(H.s[a]):nv;H.dirty=!0}]},
      useRef:function(v){var a=j++;if(!(a in H.f))H.f[a]={current:v};return H.f[a]},
      useEffect:function(fn,d){var a=k++,o=H.e[a];
        if(!o||!d||!o.d||d.length!==o.d.length||d.some(function(v,q){return v!==o.d[q]}))run.push([a,fn,d])}};
    try{H.out=Comp(H.p)}finally{r=r0;if(hx)G.x=x0;else delete G.x}
    if(att)tous(H.out).forEach(function(n){if(n.p.ref&&typeof n.p.ref==="object"&&!n.p.ref.current)n.p.ref.current=att(n)});
    run.forEach(function(q){var o=H.e[q[0]];if(o&&typeof o.c==="function")o.c();H.e[q[0]]={d:q[2],c:q[1]()}});
    return H.out}
  function flush(){var g=0;while(H.dirty&&g++<20){H.dirty=!1;render()}return H.out}
  function unmount(){H.e.forEach(function(o){if(o&&typeof o.c==="function")o.c()});H.e=[]}
  return {render:render,flush:flush,unmount:unmount,H:H}}
function tous(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;
  if(Array.isArray(n)){n.forEach(function(k){tous(k,acc)});return acc}
  if(n.t!==void 0&&n.p){acc.push(n);tous(n.p.children,acc)}return acc}
function txt(n){var c=n&&n.p&&n.p.children;return typeof c==="string"?c:Array.isArray(c)?c.filter(function(k){return typeof k==="string"}).join(""):""}
function msg(m){return tous(m).filter(function(n){return /dzm-scmsg/.test(n.p.className||"")}).map(txt)}
function imgs(m){return tous(m).filter(function(n){return n.t==="img"}).map(function(n){return n.p.src})}
function btn(m,l){return tous(m).filter(function(n){return n.t==="button"&&txt(n)===l})[0]}
var TM=[],TID=0;G.setTimeout=function(f,ms){var id=++TID;TM.push({id:id,f:f,ms:ms});return id};
G.clearTimeout=function(id){TM=TM.filter(function(t){return t.id!==id})};
function tick(){var l=TM;TM=[];l.forEach(function(t){t.f()});return l.length}
var FQ=[];G.fetch=function(u,op){var d={},p=new Promise(function(a,b){d.a=a;d.b=b});
  FQ.push({u:u,body:JSON.parse(op.body),sig:op.signal||null,d:d});return p};
function rep(i,tag){FQ[i].d.a({ok:!0,status:200,blob:function(){return Promise.resolve({blob:tag})}})}
var UR={made:[],rev:[]};G.URL={createObjectURL:function(b){var u="blob:"+b.blob;UR.made.push(u);return u},revokeObjectURL:function(u){UR.rev.push(u)}};
function settle(){var p=Promise.resolve();for(var i=0;i<12;i++)p=p.then(function(){return new Promise(function(a){setImmediate(a)})});return p}
var S={dz_montage_scopes:"1"};window.localStorage={getItem:function(k){return Object.prototype.hasOwnProperty.call(S,k)?S[k]:null},setItem:function(k,v){S[k]=String(v)}};
var SC=[{tr:"v1",id:"a",start:0,end:4,src:{job_id:"A"},effects:[{type:"wheels",gain_r:1.2}]},{tr:"v1",id:"b",start:4,end:8,src:{job_id:"B"}}];
var M=mini(T.Scopes),R={};
(async function(){
  /* 1 : en lecture, AUCUN minuteur, AUCUNE requête (l'état de lecture est lu, pas seulement l'anti-rebond) */
  M.render({clips:SC,head:1,playing:!0});R.lecture=[TM.length,FQ.length,msg(M.H.out)];
  /* 2 : à l'arrêt, UN minuteur de 300 ms et rien avant ; 3 : la tête bouge avant 300 ms -> l'ancien minuteur annulé */
  M.render({clips:SC,head:1,playing:!1});R.arret=[TM.map(function(t){return t.ms}),FQ.length];
  M.render({clips:SC,head:1.5,playing:!1});R.rebond=[TM.length,FQ.length];
  tick();R.req=[FQ.length,FQ[0]&&FQ[0].u,FQ[0]&&FQ[0].body];
  /* 4 : nouvel instant avant la réponse -> la 1re requête ABANDONNÉE ; elle répond APRÈS la 2e : JETÉE (numéro de requête) */
  M.render({clips:SC,head:2,playing:!1});R.abort1=!!(FQ[0]&&FQ[0].sig&&FQ[0].sig.aborted);tick();
  rep(1,"B");await settle();M.flush();rep(0,"A");await settle();M.flush();
  R.perimee=[imgs(M.H.out),UR.made.slice(),msg(M.H.out)];
  /* 5 : changement de plan -> l'image de l'autre plan n'est plus montrée ; la nouvelle REMPLACE et révoque l'ancienne */
  M.render({clips:SC,head:5,playing:!1});R.plan=[imgs(M.H.out),msg(M.H.out)];
  tick();rep(2,"C");await settle();M.flush();R.remplace=[imgs(M.H.out),UR.rev.slice()];
  /* 6 : la lecture repart pendant une requête en vol -> abandon, minuteur annulé, la réponse tardive est jetée */
  M.render({clips:SC,head:5.5,playing:!1});tick();M.render({clips:SC,head:5.6,playing:!0});
  R.lecture_abort=[!!(FQ[3]&&FQ[3].sig&&FQ[3].sig.aborted),TM.length];rep(3,"D");await settle();M.flush();R.lecture_jette=UR.made.slice();
  /* 7 : aller-retour de la tête (6 -> 6,5 -> 6) : les DEUX requêtes abandonnées refusent APRÈS le retour — elles se taisent
     (même quand leur empreinte redevient la courante) ; le refus de la requête COURANTE se dit, avec le détail du serveur */
  M.render({clips:SC,head:6,playing:!1});tick();M.render({clips:SC,head:6.5,playing:!1});tick();M.render({clips:SC,head:6,playing:!1});tick();
  FQ[5].d.a({ok:!1,status:500,json:function(){return Promise.resolve({detail:"périmé"})}});await settle();M.flush();
  FQ[4].d.b(new Error("abandon"));await settle();M.flush();R.refus_abandon=msg(M.H.out);
  FQ[6].d.a({ok:!1,status:500,json:function(){return Promise.resolve({detail:"ffmpeg a refusé"})}});await settle();M.flush();R.refus=msg(M.H.out);
  /* 8 : éteindre -> URL révoquée, mémoire « 0 », plus aucune requête */
  var n0=UR.rev.length;btn(M.H.out,"Scopes").p.onClick();M.flush();tick();
  R.eteint=[UR.rev.slice(n0),S.dz_montage_scopes,FQ.length,imgs(M.H.out)];
  /* 9 : rallumer, une image, une requête en vol, DÉMONTER -> abandon + URL révoquée, la réponse tardive ne crée rien */
  btn(M.H.out,"Scopes").p.onClick();M.flush();tick();rep(7,"E");await settle();M.flush();
  M.render({clips:SC,head:7,playing:!1});tick();var n1=UR.rev.length,nm=UR.made.length;M.unmount();
  rep(8,"F");await settle();R.demonte=[!!(FQ[8]&&FQ[8].sig&&FQ[8].sig.aborted),UR.rev.slice(n1),UR.made.length-nm,TM.length];
  /* LA LIGHTBOX : six plans rendus + un sans source ; au plus trois en vol ; la file suit ; fermer abandonne et révoque */
  FQ=[];UR.made=[];UR.rev=[];TM=[];
  var PL=[];for(var i=0;i<6;i++)PL.push({tr:"v1",id:"p"+i,start:i*2,end:i*2+2,srcIn:i,src:{job_id:"J"+i}});
  PL.splice(2,0,{tr:"v1",id:"t",start:3.5,end:4});PL.push({tr:"v2",id:"o",start:0,end:9,src:{job_id:"O"}});
  var L=mini(T.Lightbox),PK=[],CL=0;L.render({clips:PL,onPick:function(c){PK.push(c.id)},onClose:function(){CL++}});
  R.lb_vol=[FQ.length,FQ.map(function(q){return [q.u,q.body.src.job_id,q.body.t,q.body.w]})];
  rep(0,"L0");await settle();L.flush();R.lb_suite=[FQ.length,FQ[3]&&FQ[3].body.src.job_id,imgs(L.H.out)];
  FQ[1].d.b(new Error("x"));await settle();L.flush();
  R.lb_err=[FQ.length,tous(L.H.out).filter(function(n){return /dzm-lbph/.test(n.p.className||"")}).map(txt)];
  L.unmount();rep(2,"tard");await settle();
  R.lb_ferme=[FQ.slice(2).map(function(q){return !!(q.sig&&q.sig.aborted)}),UR.rev.slice(),UR.made.slice(),FQ.length];
  /* ── revue T5 (24/09/2026) : LE PANNEAU ÉTALONNAGE EN EXÉCUTION. Fenêtre factice qui COMPTE ses écouteurs, faux
     rAF / cAF, canvas factices montés sur les refs objets (mini, att), magasin et JSON.stringify comptés, timeline
     en Proxy qui compte ses lectures. Chaque garde de course ou de fuite a son cas ; une mutation qui la retire rougit. */
  FQ=[];UR.made=[];UR.rev=[];TM=[];
  var LS={},WL={add:[],rem:[]},NOREM=!1;
  window.addEventListener=function(t,f){WL.add.push(t);(LS[t]=LS[t]||[]).push(f)};
  window.removeEventListener=function(t,f){WL.rem.push(t);if(NOREM&&t!=="storage")return;LS[t]=(LS[t]||[]).filter(function(g){return g!==f})};
  function fire(t,e){(LS[t]||[]).slice().forEach(function(f){f(e)})}
  var RQ=[],RID=0,CAF=0;G.requestAnimationFrame=function(f){var id=++RID;RQ.push({id:id,f:f});return id};
  G.cancelAnimationFrame=function(id){CAF++;RQ=RQ.filter(function(q){return q.id!==id})};
  function frame(){var l=RQ;RQ=[];l.forEach(function(q){q.f()});return l.length}
  var DRW={},CTX={};["clearRect","beginPath","arc","fill","stroke","moveTo","lineTo","fillRect"].forEach(function(k){CTX[k]=function(){}});
  function fcv(n){var k=n.p["data-kind"];return {width:n.p.width,height:n.p.height,getContext:function(){DRW[k]=(DRW[k]||0)+1;return CTX}}}
  function drw(){return JSON.parse(JSON.stringify(DRW))}
  var GI=0,g0=window.localStorage.getItem;window.localStorage.getItem=function(k){GI++;return g0(k)};
  var JS0=JSON.stringify,NS=0;
  var GPa={tr:"v1",id:"a",start:0,end:4,src:{job_id:"A"}},
    GPg={tr:"v1",id:"g",start:4,end:8,srcIn:0,src:{job_id:"G"},effects:[{type:"wheels",gain_r:1.5,gain_g:.75,gain_b:.75},{type:"curves",pts_m:"0/0 0.5/0.7 1/1"}],
      mask:{shape:"ellipse",x:.25,y:.25,w:.5,h:.5}},
    GPh={tr:"v1",id:"h",start:8,end:12,srcIn:0,src:{job_id:"H"},effects:[{type:"wheels",gain_r:1.2}]};
  var CG=0,CLp=new Proxy([GPa,GPg,GPh],{get:function(t,k,rc){CG++;return Reflect.get(t,k,rc)}});
  var ON=[],NT=[],onC=function(p,h){ON.push([JSON.parse(JS0(p)),h])},onN=function(t){NT.push(t)};
  function gpP(o){return Object.assign({clips:CLp,head:5,playing:!1,onChange:onC,onNote:onN,clip:GPg},o)}
  function cvs(m,k){return tous(m).filter(function(n){return n.t==="canvas"&&n.p["data-kind"]===k})[0]}
  function bx(w){return {getBoundingClientRect:function(){return {left:0,top:0,width:w,height:w}}}}
  function pdn(id,cx,cy,w){return {button:0,pointerId:id,clientX:cx,clientY:cy,currentTarget:bx(w),preventDefault:function(){}}}
  function pmsg(m){return tous(m).filter(function(n){return /dzm-gp-pmsg/.test(n.p.className||"")}).map(txt)}
  var P=mini(T.GradePanel,fcv);
  /* 1 : le montage -- les trois roues et la courbe dessinées UNE fois, l'écouteur « storage », UN minuteur de 400 ms */
  P.render(gpP());R.gp_mount=[drw(),WL.add.slice(),TM.map(function(t){return t.ms}),FQ.length];
  /* 2 (I-3) : 60 re-rendus EN LECTURE, la tête bouge à chaque image -- 0 dessin, 0 lecture du magasin, 0 JSON.stringify,
     0 lecture de la timeline (plan précédent mis en cache sur l'identité), plus aucun minuteur (M-f), aucune requête */
  var d0=JS0(DRW),gi0=GI,cg0=CG;JSON.stringify=function(){NS++;return JS0.apply(JSON,arguments)};
  for(var fi=0;fi<60;fi++)P.render(gpP({head:5+fi*.033,playing:!0}));
  JSON.stringify=JS0;
  R.gp_lecture=[JS0(DRW)===d0,GI-gi0,NS,CG-cg0,TM.length,FQ.length,pmsg(P.H.out)];
  /* témoin : 60 re-rendus à l'arrêt SANS changement de valeur -- 0 dessin non plus */
  P.render(gpP());var d1=JS0(DRW);for(fi=0;fi<60;fi++)P.render(gpP());R.gp_arret=[JS0(DRW)===d1,TM.length];
  /* 3 (numéro de requête, M-b) : la tête bouge -- la 1re requête ABANDONNÉE ; elle répond APRÈS la 2e : JETÉE */
  tick();P.render(gpP({head:5.5}));R.gp_ab=[FQ.length,!!(FQ[0]&&FQ[0].sig&&FQ[0].sig.aborted)];tick();
  rep(1,"P1");await settle();P.flush();rep(0,"P0");await settle();P.flush();
  R.gp_perimee=[imgs(P.H.out),UR.made.slice(),pmsg(P.H.out)];
  /* re-revue T6 (24/09) : EN LECTURE avec une image déjà montrée, la ligne dit la lecture (comme les scopes : `jouant`
     testé AVANT `voit`) ; aucune requête ne part (sig vide) */
  var fqL=FQ.length;P.render(gpP({head:5.5,playing:!0}));R.gp_lec_img=[imgs(P.H.out),pmsg(P.H.out),FQ.length-fqL];
  /* 4 (M-a) : un AUTRE plan -- l'image du précédent n'est plus montrée ; son refus ne se dit que sur lui ; retour : l'image de g */
  P.render(gpP({clip:GPh}));var mh=[imgs(P.H.out),pmsg(P.H.out)];tick();
  FQ[2].d.a({ok:!1,status:500,json:function(){return Promise.resolve({detail:"ffmpeg a refusé"})}});await settle();P.flush();
  mh.push(pmsg(P.H.out));P.render(gpP());R.gp_plan=mh.concat([imgs(P.H.out),pmsg(P.H.out)]);
  /* 5 (dzmGpDrag, exporté) : pointerId filtré, rAF coalescé, dernier point rejoué au relâcher, pointercancel, retrait idempotent */
  var DG=[],dcb=function(a,b){DG.push([a,b])},a0=WL.add.length,r0=WL.rem.length,c0=CAF;
  var st1=T.gpDrag({pointerId:1},dcb);fire("pointermove",{pointerId:2,clientX:1,clientY:1});frame();
  fire("pointermove",{pointerId:1,clientX:10,clientY:20});var avant=DG.length;frame();
  fire("pointermove",{pointerId:1,clientX:30,clientY:40});fire("pointerup",{pointerId:1});var rel=DG.slice();frame();
  var st2=T.gpDrag({pointerId:5},dcb);fire("pointercancel",{pointerId:5});fire("pointermove",{pointerId:5,clientX:7,clientY:7});frame();
  var st3=T.gpDrag({pointerId:7},dcb);fire("pointermove",{pointerId:7,clientX:8,clientY:8});var r3=WL.rem.length;st3();var r3b=WL.rem.length;st3();frame();
  R.gp_drag=[WL.add.slice(a0,a0+3),avant,rel,DG,WL.rem.length-r0,CAF-c0,typeof st1,r3b-r3,WL.rem.length-r3b,RQ.length,(LS.pointermove||[]).length];
  /* 6 (I-2) : un geste écrit dans le plan SAISI -- la sélection change pendant le geste : plus rien n'est écrit ;
     témoin : sur le même plan, le déplacement écrit */
  ON=[];P.render(gpP());var wl=cvs(P.H.out,"lift");wl.p.onPointerDown(pdn(3,48,20,96));
  fire("pointermove",{pointerId:3,clientX:60,clientY:20});frame();var nsame=ON.length;
  P.render(gpP({clip:GPh}));fire("pointermove",{pointerId:3,clientX:70,clientY:30});frame();fire("pointerup",{pointerId:3});
  R.gp_saisi=[nsame,ON.length,(LS.pointermove||[]).length];
  /* 7 (I-1, accord) : empreinte -- le plan a changé (srcIn) pendant le calcul : refus dit, 0 écriture ; « busy » : deux clics
     SANS re-rendu = une requête ; succès : l'effet posé (lourd) ; démontage pendant le calcul : rien n'est écrit ni dit */
  ON=[];NT=[];P.render(gpP());var fq0=FQ.length;btn(P.H.out,"Accorder sur le plan précédent").p.onClick();
  P.render(gpP({clip:Object.assign({},GPg,{srcIn:2})}));
  FQ[fq0].d.a({ok:!0,status:200,json:function(){return Promise.resolve({effect:{type:"colormatch",y_gain:1.2}})}});await settle();P.flush();
  R.gp_acc_sig=[FQ[fq0].u,FQ[fq0].body,ON.length,NT.slice(-1)];
  P.render(gpP());var fq1=FQ.length,bA=btn(P.H.out,"Auto");bA.p.onClick();bA.p.onClick();var nreq=FQ.length-fq1;
  FQ[fq1].d.a({ok:!0,status:200,json:function(){return Promise.resolve({effect:{type:"colormatch",y_gain:1.1}})}});await settle();P.flush();
  R.gp_acc=[nreq,ON.slice(),NT.slice(-1),!!btn(P.H.out,"Auto").p.disabled];
  ON=[];NT=[];var fq2=FQ.length;btn(P.H.out,"Auto").p.onClick();var nr0=UR.rev.length,wr0=WL.rem.slice();
  /* 8 : démontage -- requête d'aperçu en vol abandonnée, sa réponse tardive ne crée rien ; URL révoquée ; écouteurs ôtés */
  P.render(gpP({head:6}));tick();var fqp=FQ.length-1;var nm=UR.made.length;P.unmount();
  FQ[fq2].d.a({ok:!0,status:200,json:function(){return Promise.resolve({effect:{type:"colormatch",y_gain:1.3}})}});rep(fqp,"TARD");await settle();
  R.gp_demonte=[ON.length,NT.length,FQ[fqp].u,!!(FQ[fqp].sig&&FQ[fqp].sig.aborted),UR.made.length-nm,UR.rev.length-nr0,
    WL.rem.slice(wr0.length),TM.length,(LS.storage||[]).length];
  /* 9 (I-2, défense) : une fenêtre qui NE retire PAS les écouteurs du geste -- après démontage, rien n'est écrit (vivant) ;
     et le démontage en plein geste retire les trois écouteurs et annule le rAF (fenêtre normale) */
  ON=[];var P2=mini(T.GradePanel,fcv);P2.render(gpP());cvs(P2.H.out,"gain").p.onPointerDown(pdn(9,48,48,96));
  fire("pointermove",{pointerId:9,clientX:60,clientY:40});var c9=CAF,rm9=WL.rem.length;P2.unmount();frame();
  var dem=[ON.length,CAF-c9,WL.rem.slice(rm9),(LS.pointermove||[]).length];
  NOREM=!0;ON=[];var P3=mini(T.GradePanel,fcv);P3.render(gpP());cvs(P3.H.out,"gamma").p.onPointerDown(pdn(11,48,48,96));var n11=ON.length;
  P3.unmount();fire("pointermove",{pointerId:11,clientX:70,clientY:20});frame();NOREM=!1;LS.pointermove=[];LS.pointerup=[];LS.pointercancel=[];
  R.gp_vivant=dem.concat([n11,ON.length]);
  /* 10 (M-c) : X et Y du masque bornés à 1 − w | 1 − h, la largeur GARDÉE ; (M-d) double-clic dans le vide de la courbe :
     le point créé par son premier clic reste (une écriture AVEC effet, pas « ajouter puis retirer ») ; témoin : un
     double-clic volontaire plus tard retire le point */
  ON=[];var P4=mini(T.GradePanel,fcv),GI0=Object.assign({},GPg,{effects:[{type:"curves",pts_m:"0/0 1/1"}]});P4.render(gpP({clip:GI0}));
  var rgs=tous(P4.H.out).filter(function(n){return n.t==="input"&&n.p.type==="range"});
  rgs[3].p.onChange({target:{value:"70"}});rgs[4].p.onChange({target:{value:"90"}});var mc=ON.slice();ON=[];
  var cc=cvs(P4.H.out,"curve");cc.p.onPointerDown(pdn(21,60,40,200));fire("pointerup",{pointerId:21});
  var GI1=Object.assign({},GI0,{effects:ON[0]&&ON[0][0].effects});P4.render(gpP({clip:GI1}));cc=cvs(P4.H.out,"curve");
  cc.p.onPointerDown(pdn(22,60,40,200));fire("pointerup",{pointerId:22});cc.p.onDoubleClick(pdn(0,60,40,200));var md=ON.map(function(q){return q[0].effects[0].pts_m});
  cc.p.onPointerDown(pdn(23,60,40,200));fire("pointerup",{pointerId:23});cc.p.onPointerDown(pdn(24,60,40,200));fire("pointerup",{pointerId:24});
  cc.p.onDoubleClick(pdn(0,60,40,200));R.gp_mask_curve=[mc,md,ON.length,ON.length>1?ON[ON.length-1][0].effects[0].pts_m:null];P4.unmount();
  /* 11 : le grade copié n'est relu que quand il a changé -- « Copier » de CE panneau (DZM_GP_VER) rallume « Coller » ;
     l'événement « storage » d'un autre onglet (grade effacé) l'éteint ; chaque fois UNE lecture, aucune entre deux */
  delete S.dz_montage_grade;var P5=mini(T.GradePanel,fcv);P5.render(gpP());var cz=!!btn(P5.H.out,"Coller le grade").p.disabled,gi5=GI;
  for(fi=0;fi<5;fi++)P5.render(gpP());var gi6=GI;
  btn(P5.H.out,"Copier le grade").p.onClick();P5.flush();var cp=[!!btn(P5.H.out,"Coller le grade").p.disabled,GI-gi6],gi7=GI;
  delete S.dz_montage_grade;fire("storage",{key:"dz_montage_grade"});P5.flush();
  R.gp_storage=[cz,gi6-gi5].concat(cp,[!!btn(P5.H.out,"Coller le grade").p.disabled,GI-gi7]);P5.unmount();
  /* ── revue T6 (24/09/2026). M1 : une erreur PÉRIMÉE ne s'affiche plus -- refus à l'empreinte S (t=1), succès à S'
     (t=2), retour à S : « Mesure en cours… » puis l'image fraîche SANS l'ancien refus ; la ligne d'état est aria-live */
  FQ=[];UR.made=[];UR.rev=[];TM=[];S.dz_montage_scopes="1";
  var M6=mini(T.Scopes);M6.render({clips:SC,head:1,playing:!1});tick();
  FQ[0].d.a({ok:!1,status:500,json:function(){return Promise.resolve({detail:"backend en relance"})}});await settle();M6.flush();
  var e1=[msg(M6.H.out),tous(M6.H.out).filter(function(n){return /dzm-scmsg/.test(n.p.className||"")}).map(function(n){return n.p["aria-live"]})];
  M6.render({clips:SC,head:2,playing:!1});tick();rep(1,"X");await settle();M6.flush();
  M6.render({clips:SC,head:1,playing:!1});var pend=[msg(M6.H.out),imgs(M6.H.out)];tick();rep(2,"OK");await settle();M6.flush();
  R.t6_err=[e1,pend,[msg(M6.H.out),imgs(M6.H.out)]];M6.unmount();
  /* M4 : la lightbox est un dialogue MODAL (aria-modal) ; à l'ouverture le focus va sur « Fermer », à la fermeture il
     revient là où il était (document factice : activeElement) */
  FQ=[];var FOC=[],AV={focus:function(){FOC.push("avant")}};G.document={activeElement:AV};
  var L6=mini(T.Lightbox,function(n){return {focus:function(){FOC.push("focus:"+txt(n))}}});
  L6.render({clips:[{tr:"v1",id:"q",start:0,end:2,src:{job_id:"Q"}}],onPick:function(){},onClose:function(){}});
  var f0=FOC.slice(),dlg=tous(L6.H.out).filter(function(n){return n.p.role==="dialog"})[0];L6.unmount();
  R.t6_lb=[f0,FOC.slice(),dlg&&dlg.p["aria-modal"]];delete G.document;
  /* ── re-revue 4bda880 (24/09/2026) : LE PORTAIL DE L'ENCART, en exécution. Pu factice (createPortal rend un nœud
     « portail » qui garde sa cible) ; la ref du mini est montée sur un faux nœud dont closest(".svm-playerzone") rend une
     fausse zone dont querySelector(".svm-frame") rend un faux cadre -- les recherches sont COMPTÉES. Cadre connecté :
     l'encart part dans le portail (et nulle part en ligne) ; cinq re-rendus, la tête bouge : AUCUNE nouvelle recherche
     (deps [on]) ; cadre détaché (isConnected faux) : l'encart retombe en ligne, hors portail. */
  FQ=[];UR.made=[];UR.rev=[];TM=[];S.dz_montage_scopes="1";
  var NQ={cl:0,qs:0},FR={isConnected:!0},ZN={querySelector:function(s){NQ.qs++;return s===".svm-frame"?FR:null}};
  G.Pu={createPortal:function(el,c){return {t:"portail",p:{children:[el],cible:c}}}};
  var estPop=function(n){return /dzm-scpop/.test(n.p.className||"")};
  function ou(m){var k=m&&m.p&&Array.isArray(m.p.children)?m.p.children[1]:null,dp=k&&k.t==="portail";
    return [k?k.t:null,dp?k.p.cible===FR:null,tous(m).filter(estPop).length,dp?tous(k.p.children).filter(estPop).length:0]}
  var M7=mini(T.Scopes,function(){return {closest:function(s){NQ.cl++;return s===".svm-playerzone"?ZN:null}}});
  M7.render({clips:SC,head:1,playing:!1});M7.flush();var pc=ou(M7.H.out);
  for(var hi=1;hi<=5;hi++)M7.render({clips:SC,head:1+hi*.2,playing:!1});M7.flush();var pr=[ou(M7.H.out),NQ.cl,NQ.qs];
  FR.isConnected=!1;M7.render({clips:SC,head:2.4,playing:!1});M7.flush();var pd=ou(M7.H.out);
  R.pt_portail=[pc,pr,pd,[NQ.cl,NQ.qs]];M7.unmount();delete G.Pu;
  out.R=R;
})().catch(function(e){out.err=String(e&&e.stack||e)}).then(function(){console.log(JSON.stringify(out))});
"""
DX = {}
if NODE and os.path.isfile(SRC_PATH) and globals().get("SRC"):
    _shx = os.path.join(TMP, "shim_l5x.js")
    with open(_shx, "w", encoding="utf-8") as fh:
        fh.write('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + SRC + "\n" + PROBE_L5X)
    _rx = sh([NODE, _shx])
    _lx = (_rx.stdout or "").strip().splitlines()
    try:
        DX = json.loads(_lx[-1]) if _lx else {}
    except Exception as _e:
        DX = {"err": temoin(_e)}
    check("l5x_shim_execute_sans_erreur", _rx.returncode == 0 and "err" not in DX and isinstance(DX.get("R"), dict),
          (DX.get("err"), (_rx.stderr or "")[-400:]))
else:
    check("l5x_shim_execute_sans_erreur", False, "node ou source absents")
_RX = DX.get("R") if isinstance(DX.get("R"), dict) else {}
check("l5x_scopes_en_lecture_aucun_minuteur_aucune_requete_la_lecture_dite",
      _RX.get("lecture") == [0, 0, ["Lecture : les scopes se rafraîchissent à l'arrêt"]], _RX.get("lecture"))
check("l5x_scopes_a_l_arret_un_minuteur_300_ms_puis_une_requete_anti_rebond_annule_l_ancien",
      _RX.get("arret") == [[300], 0] and _RX.get("rebond") == [1, 0]
      and _RX.get("req") == [1, "/api/montage/scopes", {"src": {"job_id": "A"}, "t": 1.5, "effects": [{"type": "wheels", "gain_r": 1.2}]}],
      [_RX.get("arret"), _RX.get("rebond"), _RX.get("req")])
check("l5x_scopes_requete_remplacee_abandonnee_et_reponse_perimee_jetee",
      _RX.get("abort1") is True and _RX.get("perimee") == [["blob:B"], ["blob:B"], []], [_RX.get("abort1"), _RX.get("perimee")])
check("l5x_scopes_changement_de_plan_l_ancienne_image_cachee_puis_remplacee_et_revoquee",
      _RX.get("plan") == [[], ["Mesure en cours…"]] and _RX.get("remplace") == [["blob:C"], ["blob:B"]],
      [_RX.get("plan"), _RX.get("remplace")])
check("l5x_scopes_la_lecture_repart_requete_abandonnee_minuteur_annule_reponse_tardive_jetee",
      _RX.get("lecture_abort") == [True, 0] and _RX.get("lecture_jette") == ["blob:B", "blob:C"],
      [_RX.get("lecture_abort"), _RX.get("lecture_jette")])
check("l5x_scopes_aller_retour_les_refus_des_requetes_abandonnees_se_taisent_refus_courant_dit_avec_le_detail",
      _RX.get("refus_abandon") == ["Mesure en cours…"] and _RX.get("refus") == ["Scopes indisponibles : ffmpeg a refusé"],
      [_RX.get("refus_abandon"), _RX.get("refus")])
check("l5x_scopes_eteindre_revoque_memorise_0_et_ne_demande_plus_rien",
      _RX.get("eteint") == [["blob:C"], "0", 7, []], _RX.get("eteint"))
check("l5x_scopes_demontage_abandonne_la_requete_revoque_l_url_la_reponse_tardive_ne_cree_rien",
      _RX.get("demonte") == [True, ["blob:E"], 0, 0], _RX.get("demonte"))
check("l5x_lightbox_trois_requetes_en_vol_au_plus_vignette_240_au_milieu_du_plan_dans_l_ordre",
      _RX.get("lb_vol") == [3, [["/api/montage/grade-frame", "J0", 1, 240], ["/api/montage/grade-frame", "J1", 2, 240],
                                ["/api/montage/grade-frame", "J2", 3, 240]]], _RX.get("lb_vol"))
check("l5x_lightbox_une_reponse_libere_une_place_la_file_suit_l_image_montree",
      _RX.get("lb_suite") == [4, "J3", ["blob:L0"]], _RX.get("lb_suite"))
check("l5x_lightbox_un_refus_libere_aussi_une_place_et_se_dit_sur_la_tuile_sans_source_dit",
      _RX.get("lb_err") == [5, ["image indisponible", "sans source", "calcul…", "calcul…", "calcul…", "calcul…"]], _RX.get("lb_err"))
check("l5x_lightbox_fermer_abandonne_les_trois_en_vol_revoque_les_urls_rien_ne_part_ni_ne_se_cree_apres",
      _RX.get("lb_ferme") == [[True, True, True], ["blob:L0"], ["blob:L0"], 5], _RX.get("lb_ferme"))
# ── revue T5 (24/09/2026) : le panneau Etalonnage EN EXECUTION (mini-React, fenetre factice qui compte, faux rAF, canvas
# factices). Les neuf gardes de la revue (I-1) ont chacune un cas qui rougit sans elle (mutations rejouees) ; I-2 : un
# geste n'ecrit que dans le plan saisi ; I-3 : rien par image pendant la lecture (MESURE : 0 dessin, 0 lecture du magasin,
# 0 JSON.stringify, 0 lecture de la timeline sur 60 re-rendus) ; M-a M-b M-c M-d M-f.
_GPW = {"type": "wheels", "gain_r": 1.5, "gain_g": 0.75, "gain_b": 0.75}
_GPCU = {"type": "curves", "pts_m": "0/0 0.5/0.7 1/1"}
check("l5x_gp_montage_trois_roues_et_la_courbe_dessinees_une_fois_ecouteur_storage_un_minuteur_400",
      _RX.get("gp_mount") == [{"lift": 1, "gamma": 1, "gain": 1, "curve": 1}, ["storage"], [400], 0], _RX.get("gp_mount"))
check("l5x_gp_I3_soixante_re_rendus_en_lecture_zero_dessin_zero_magasin_zero_stringify_zero_timeline_zero_minuteur_lecture_dite",
      _RX.get("gp_lecture") == [True, 0, 0, 0, 0, 0, ["Lecture : l'aperçu se rafraîchit à l'arrêt"]], _RX.get("gp_lecture"))
check("l5x_gp_I3_temoin_soixante_re_rendus_a_l_arret_sans_changement_zero_dessin_un_minuteur",
      _RX.get("gp_arret") == [True, 1], _RX.get("gp_arret"))
check("l5x_gp_Mb_requete_remplacee_abandonnee_I1_reponse_perimee_jetee",
      _RX.get("gp_ab") == [1, True] and _RX.get("gp_perimee") == [["blob:P1"], ["blob:P1"], [""]],
      [_RX.get("gp_ab"), _RX.get("gp_perimee")])
check("l5x_gp_lecture_avec_image_montree_la_ligne_dit_la_lecture_aucune_requete",
      _RX.get("gp_lec_img") == [["blob:P1"], ["Lecture : l'aperçu se rafraîchit à l'arrêt"], 0], _RX.get("gp_lec_img"))
check("l5x_gp_Ma_autre_plan_image_du_precedent_cachee_son_refus_dit_sur_lui_seul_retour_image_rendue",
      _RX.get("gp_plan") == [[], ["calcul de l'aperçu…"], ["Aperçu étalonné indisponible : ffmpeg a refusé"], ["blob:P1"], [""]],
      _RX.get("gp_plan"))
check("l5x_gp_drag_pointerId_filtre_raf_coalesce_dernier_point_rejoue_pointercancel_retrait_idempotent",
      _RX.get("gp_drag") == [["pointermove", "pointerup", "pointercancel"], 0, [[10, 20], [30, 40]], [[10, 20], [30, 40]],
                             9, 2, "function", 3, 0, 0, 0], _RX.get("gp_drag"))
check("l5x_gp_I2_geste_ecrit_dans_le_plan_saisi_selection_changee_plus_rien_temoin_meme_plan_ecrit",
      _RX.get("gp_saisi") == [2, 2, 0], _RX.get("gp_saisi"))
_GPB = {"target": {"src": {"job_id": "G"}, "t": 1}, "ref": {"src": {"job_id": "A"}, "t": 2}}
check("l5x_gp_I1_accord_plan_change_pendant_le_calcul_refus_dit_zero_ecriture",
      _RX.get("gp_acc_sig") == ["/api/montage/color-match", _GPB, 0, ["Accord refusé : le plan a changé pendant le calcul — relancez."]],
      _RX.get("gp_acc_sig"))
check("l5x_gp_I1_accord_deux_clics_sans_re_rendu_une_requete_succes_pose_l_effet_lourd",
      _RX.get("gp_acc") == [1, [[{"effects": [_GPW, _GPCU, {"type": "colormatch", "y_gain": 1.1}]}, True]],
                            ["Accord automatique posé (effet « Accord couleur »)."], False], _RX.get("gp_acc"))
check("l5x_gp_I1_demontage_accord_ni_ecrit_ni_dit_apercu_abandonne_reponse_tardive_ne_cree_rien_url_revoquee_ecouteur_ote",
      _RX.get("gp_demonte") == [0, 1, "/api/montage/grade-frame", True, 0, 1, ["storage"], 0, 0], _RX.get("gp_demonte"))
check("l5x_gp_I2_demontage_en_plein_geste_retire_les_ecouteurs_annule_le_raf_defense_vivant_si_un_ecouteur_survit",
      _RX.get("gp_vivant") == [1, 1, ["storage", "pointermove", "pointerup", "pointercancel"], 0, 1, 1], _RX.get("gp_vivant"))
_GPMK = {"shape": "ellipse", "x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5, "soft": 0, "inv": False}
check("l5x_gp_Mc_x_et_y_du_masque_bornes_largeur_gardee_Md_double_clic_dans_le_vide_garde_le_point_temoin_retrait_volontaire",
      _RX.get("gp_mask_curve") == [[[{"mask": dict(_GPMK, x=0.5)}, False], [{"mask": dict(_GPMK, y=0.5)}, False]],
                                   ["0/0 0.3/0.8 1/1"], 2, "0/0 1/1"], _RX.get("gp_mask_curve"))
check("l5x_gp_grade_copie_relu_une_fois_par_changement_copier_rallume_coller_storage_d_un_autre_onglet_l_eteint",
      _RX.get("gp_storage") == [True, 0, False, 1, True, 1], _RX.get("gp_storage"))
# ── revue T6 (24/09/2026). M1 : erreur perimee effacee au succes (et l'image testee AVANT l'erreur) ; M4 : aria-live sur
# la ligne d'etat des scopes, lightbox aria-modal, focus sur « Fermer » a l'ouverture, rendu au point de depart a la fermeture.
check("l5x_t6_M1_refus_dit_puis_succes_ailleurs_retour_mesure_en_cours_puis_image_fraiche_sans_l_ancien_refus_aria_live",
      _RX.get("t6_err") == [[["Scopes indisponibles : backend en relance"], ["polite"]], [["Mesure en cours…"], []], [[], ["blob:OK"]]],
      _RX.get("t6_err"))
check("l5x_t6_M4_lightbox_modale_focus_sur_fermer_a_l_ouverture_rendu_au_depart_a_la_fermeture",
      _RX.get("t6_lb") == [["focus:Fermer"], ["focus:Fermer", "avant"], "true"], _RX.get("t6_lb"))
# ── re-revue 4bda880 (24/09/2026) : le portail de l'encart EXECUTE (le compte de texte sc_encart_... ne suffisait pas).
# Mutations qui rougissent ici : portail retire (en ligne des le cadre connecte), test isConnected retire (cadre detache
# encore porte), deps [on] -> aucune (une recherche par rendu : 7 au lieu de 1).
check("l5x_pt_encart_porte_dans_le_cadre_connecte_une_recherche_par_allumage_retombe_en_ligne_cadre_detache",
      _RX.get("pt_portail") == [["portail", True, 1, 1], [["portail", True, 1, 1], 1, 1], ["div", None, 1, 0], [1, 1]],
      _RX.get("pt_portail"))

print("\n[39] L6 D-25 D-26 : le coeur pur audio — plage de bruit en temps de source, debruiteur appris, prises, type d'enregistrement (tache 4, 25/09/2026)")
# ── L6 (25/09/2026, tache 4). La plage I/O (temps de TIMELINE) devient une plage de SOURCE du clip selectionne
# (a = srcIn + (in - start)·v ; v = la vitesse audio lue comme sfx_service.clamp_speed : 0,5..2, ~1 -> 1) ; elle peut
# sortir du clip mais pas de la source ; la garde 0,2 s porte la MEME tolerance que learn_of du backend
# (b - a < LEARN_MIN - 1e-9 refuse ; revue T4 25/09 L6 : l'ancienne garde nue `< .2` refusait 1,0-1,2 (0,19999…) et
# acceptait 7,0-7,2 -- le verdict dependait de la POSITION de la plage). Temoins : 1,0-1,2 ACCEPTEE comme 7,0-7,2,
# 1,0-1,199 refusee (courte). Clip sans debut lisible -> clip (pas plage) ; srcIn negatif borne a 0.
# Faute n6 : chaque lecture passe par D.get / at().
check("au_lr_plage_de_source_vitesse_hors_clip_hors_source_plage_absente_courte_longue_clip_absent_ordre_inverse",
      D.get("au_lr") == [{"a": 7, "b": 8}, {"a": 9, "b": 11}, {"a": 3, "b": 4}, "hors_source", "plage", "plage", "courte",
                         "hors_source", {"a": 7, "b": 8}, "longue", {"a": 7, "b": 37}, "clip", "plage",
                         {"a": 7, "b": 8}, {"a": 9, "b": 11}, {"a": 2, "b": 3}, {"a": 7, "b": 8}, {"a": 7, "b": 7.2},
                         {"a": 1, "b": 1.2}, "courte", "clip", "clip", {"a": 0.5, "b": 1.5}],
      D.get("au_lr"))
check("au_lr_chaque_refus_porte_une_phrase", D.get("au_lr_note") == [True] * 6, D.get("au_lr_note"))
_AUL = {"type": "denoise", "params": {"amount": 30, "nf": -31, "learn_in": 7, "learn_out": 8}}
_AUQ = [{"type": "eq3", "params": {"bass_db": 2}}, {"type": "denoise", "params": {"amount": 30}}]
check("au_dl_debruiteur_cree_amount_24_ou_garde_forme_params_ou_a_plat_autres_modules_meme_reference_entree_intacte",
      at("au_dl", 0) == [{"type": "denoise", "params": {"amount": 24, "nf": -31, "learn_in": 7, "learn_out": 8}}]
      and at("au_dl", 1) == [_AUQ[0], _AUL] and at("au_dl", 2) is True and at("au_dl", 3) is True and at("au_dl", 4) is True
      and at("au_dl", 5) is True
      and at("au_dl", 6) == [{"type": "denoise", "amount": 30, "enabled": True, "nf": -40, "learn_in": 1, "learn_out": 2}]
      and at("au_dl", 7) is True
      and at("au_dl", 8) == [{"type": "denoise", "params": {"amount": 24, "nf": -31, "learn_in": 7, "learn_out": 8}}],
      D.get("au_dl"))
check("au_dl_plancher_illisible_auto_0_borne_moins_80_0_plage_illisible_ou_courte_liste_inchangee_premier_denoise_seul_params_non_objet_a_plat",
      at("au_dl", 9) == {"type": "denoise", "params": {"amount": 30, "nf": 0, "learn_in": 7, "learn_out": 8}}
      and at("au_dl", 10) == _AUQ and at("au_dl", 11) == _AUQ
      and at("au_dl", 12) == [{"type": "denoise", "params": {"amount": 30, "nf": -30, "learn_in": 1, "learn_out": 2}},
                              {"type": "denoise", "params": {"amount": 50}}]
      and at("au_dl", 13) == [{"type": "denoise", "params": [1], "nf": -30, "learn_in": 1, "learn_out": 2}]
      and at("au_dl", 14) == -80 and at("au_dl", 15) == 0,
      D.get("au_dl"))
# revue T5 (25/09) : un denoise enabled:false (saute par sanitize_fx au rendu) recevait l'apprentissage SANS effet ; il est
# REACTIVE (cle retiree, forme gardee), l'eq3 et le deesser coupes gardent leur reference ; enabled:true garde tel quel.
check("au_dx_apprendre_reactive_le_debruiteur_coupe_autres_modules_coupes_intacts_entree_intacte",
      at("au_dx", 0) == [{"type": "eq3", "enabled": False, "params": {"bass_db": 2}},
                         {"type": "denoise", "params": {"amount": 30, "nf": -30, "learn_in": 1, "learn_out": 2}},
                         {"type": "deesser", "enabled": False, "amount": 3}]
      and at("au_dx", 1) is True and at("au_dx", 2) is True and at("au_dx", 3) is True
      and at("au_dx", 4) == [{"type": "denoise", "amount": 30, "nf": -30, "learn_in": 1, "learn_out": 2}]
      and at("au_dx", 5) == [{"type": "denoise", "enabled": True, "amount": 30, "nf": -30, "learn_in": 1, "learn_out": 2}],
      D.get("au_dx"))
check("au_df_oublier_retire_nf_et_apprentissage_de_chaque_denoise_module_garde_autres_meme_reference_entree_intacte",
      D.get("au_df") == [[{"type": "eq3", "params": {"bass_db": 2}}, {"type": "denoise", "params": {"amount": 30}},
                          {"type": "denoise", "amount": 9}], True, True, [], [{"type": "eq3"}], _AUQ,
                         {"type": "denoise", "params": {"amount": 30}}],
      D.get("au_df"))
# Temoin « ma-voix-off-1.wav » (revue T4) : la sous-chaine SANS prefixe n'est pas une prise (indexOf >= 0 -> 4, rouge).
check("au_vo_prises_comptees_par_le_prefixe_voix_off_du_fichier_son_libelle_numero_lisible_au_moins_1",
      D.get("au_vo") == [3, 1, 1, "Voix off 3", "Voix off 1", "Voix off 1", "Voix off 1", "Voix off 2"], D.get("au_vo"))
check("au_rm_premier_type_accepte_dans_l_ordre_aucun_rien_juge_absent_rien_juge_qui_leve_saute_liste_gelee",
      D.get("au_rm") == ["audio/ogg;codecs=opus", "", "audio/webm;codecs=opus", "", "audio/mp4",
                         ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm", "audio/mp4"], True],
      D.get("au_rm"))
# LE SOURCE : les six fonctions sont PURES (ni r / x, ni reseau, ni DOM, ni stockage, ni API du navigateur -- le juge du type
# d'enregistrement est INJECTE) ; regex gardee par un temoin de longueur ; exports au contrat ; hors de la zone _L5Z.
_L6A = {n: _corps(n) for n in ("dzmLearnRange", "dzmDenoiseLearn", "dzmDenoiseForget", "dzmVoCount", "dzmVoLabel", "dzmRecMime")}
check("l6_au_six_fonctions_pures_ni_r_ni_x_ni_reseau_ni_dom_ni_stockage_ni_api_navigateur",
      all(len(c) > 40 for c in _L6A.values())
      and not any(re.search(r"\br\.jsx|\bx\.use|localStorage|sessionStorage|\bwindow\b|\bdocument\b|\bnavigator\b|MediaRecorder|"
                            r"getUserMedia|isTypeSupported|fetch\(|setClips|pushHistory|style\.|URL\.", c) for c in _L6A.values())
      and _L6A["dzmRecMime"].count("ok(DZM_VO_MIMES[i])") == 1 and _L6A["dzmLearnRange"].count("dzmCoR(") == 2,
      {n: len(c) for n, c in _L6A.items()})
check("l6_au_exports_au_contrat_une_fois_mimes_declares_une_fois_avant_la_zone_des_composants_l5",
      _DT.count("learnRange:dzmLearnRange,denoiseLearn:dzmDenoiseLearn,denoiseForget:dzmDenoiseForget,"
                "voCount:dzmVoCount,voLabel:dzmVoLabel,recMime:dzmRecMime,VO_MIMES:DZM_VO_MIMES,") == 1
      and _SRCb.count("var DZM_VO_MIMES=") == 1
      and 0 <= _SRCb.find("function dzmRecMime(") < _SRCb.find("function DzmScopes(o){")
      and 0 <= _SRCb.find("function dzmLearnRange(") < _SRCb.find("function DzmScopes(o){"),
      [_DT.count("learnRange:dzmLearnRange,"), _SRCb.count("var DZM_VO_MIMES=")])

print("\n[40] L6 D-25 : « Apprendre le bruit » sous le rack — le composant joue sous le mini-React (tache 5, 25/09/2026)")
# ── L6 (25/09/2026, tache 5). DzmNoiseLearn sous le mini-React de PROBE_L5X (harnais REPRIS par tranche, pas recopie :
# de son debut a la memoire des scopes ; temoin de longueur) ; le reseau est un faux `fetch` en file. Faute n6 : chaque
# lecture passe par .get / une liste de longueur verifiee, detail calcule avant.
_L6H = PROBE_L5X[:PROBE_L5X.find("var S={dz_montage_scopes")] if "var S={dz_montage_scopes" in PROBE_L5X else ""
PROBE_L6 = _L6H + r"""
function jrep(i,ok,st,j){FQ[i].d.a({ok:ok,status:st,json:function(){return Promise.resolve(j)}})}
function bts(m){return tous(m).filter(function(n){return n.t==="button"})}
function etat(m){return bts(m).map(function(b){return [txt(b),!!b.p.disabled,typeof b.p.title==="string"?b.p.title:null]})}
function st(m){return tous(m).filter(function(n){return /dzm-nlst/.test(n.p.className||"")}).map(txt)}
var AK={tr:"a1",id:"k",start:10,end:20,srcIn:5,src:{audio:"a.wav"},fx:[{type:"eq3",params:{bass_db:2}}]};
var R={},NT=[],FX=[];
function props(extra){return Object.assign({clip:AK,range:{"in":12,out:13},demo:!1,music:!1,
  onNote:function(m){NT.push(m)},onFx:function(id,f){FX.push([id,f])}},extra||{})}
(async function(){
  /* 1 : sans plage I/O -> les DEUX boutons rendus, grisés, titrés ; aucune requête ; état « aucun bruit appris » */
  var M=mini(T.NoiseLearn);M.render(props({range:null}));R.sans=[etat(M.H.out),st(M.H.out),FQ.length];
  M.bts=bts(M.H.out);M.bts[0].p.onClick();R.sans_clic=[FQ.length,NT.length];M.unmount();
  /* 2 : démo -> grisé et dit ; 3 : plage 12–13 sur un clip calé à 10 (srcIn 5) -> source 7–8, UNE requête, libellé « Mesure… » */
  M=mini(T.NoiseLearn);M.render(props({demo:!0}));R.demo=etat(M.H.out)[0];M.unmount();
  M=mini(T.NoiseLearn);M.render(props());R.pret=etat(M.H.out);bts(M.H.out)[0].p.onClick();M.flush();
  R.req=[FQ.length,FQ[0]&&FQ[0].u,FQ[0]&&FQ[0].body,etat(M.H.out)[0]];
  bts(M.H.out)[0].p.onClick();R.pas_deux=FQ.length;
  /* 4 : réponse ok -> onFx(id du clip, f) UNE fois, f applique dzmDenoiseLearn à la liste COURANTE ; la note dit la plage */
  jrep(0,!0,200,{ok:!0,rms_db:-40.2,nf_db:-30,t0:7,t1:8});await settle();M.flush();
  var f0=FX.length===1?FX[0][1]:null;
  R.ok=[FX.length,FX[0]&&FX[0][0],f0?f0([{type:"eq3",params:{bass_db:2}}]):null,NT.slice(-1),etat(M.H.out)[0][0]];
  /* 5 : réponse ok:false -> « Plage muette », rien d'écrit ; 6 : 404 -> la note porte le détail ; rien d'écrit */
  bts(M.H.out)[0].p.onClick();jrep(1,!0,200,{ok:!1,reason:"muet"});await settle();M.flush();R.muet=[FX.length,NT.slice(-1)];
  bts(M.H.out)[0].p.onClick();jrep(2,!1,404,{detail:"Not Found"});await settle();M.flush();R.err=[FX.length,NT.slice(-1),etat(M.H.out)[0][1]];
  M.unmount();
  /* 7 : plage trop courte -> bouton ACTIF, le clic DIT le refus, rien ne part ; 8 : durée de source EN CACHE (7,5 s) -> hors source */
  var n0=FQ.length;M=mini(T.NoiseLearn);M.render(props({range:{"in":12,out:12.1}}));R.courte_actif=!etat(M.H.out)[0][1];
  bts(M.H.out)[0].p.onClick();R.courte=[FQ.length-n0,NT.slice(-1)];M.unmount();
  var SK={tr:"a1",id:"q",start:10,end:20,srcIn:5,src:{audio:"court.wav"}};T.audioSet(SK.src,{has_audio:!0,dur:7.5,pourquoi:"mesure"});
  M=mini(T.NoiseLearn);M.render(props({clip:SK}));bts(M.H.out)[0].p.onClick();R.cache=[FQ.length-n0,NT.slice(-1)];M.unmount();
  /* 9 : clip appris -> « Oublier » actif, l'état le dit ; clic -> onFx(id, f) où f retire la plage apprise */
  var AP=Object.assign({},AK,{fx:[{type:"denoise",params:{amount:30,nf:-31,learn_in:7,learn_out:8}}]}),nf=FX.length;
  M=mini(T.NoiseLearn);M.render(props({clip:AP}));R.appris=[etat(M.H.out)[1][1],st(M.H.out)];bts(M.H.out)[1].p.onClick();
  R.oublie=[FX.length-nf,FX[nf]&&FX[nf][0],FX[nf]?FX[nf][1](AP.fx):null,NT.slice(-1)];M.unmount();
  /* 10 : démonté PENDANT la mesure -> la réponse tardive ne note ni n'écrit rien */
  M=mini(T.NoiseLearn);M.render(props());bts(M.H.out)[0].p.onClick();var q=FQ.length-1,nn=NT.length,nx=FX.length;M.unmount();
  jrep(q,!0,200,{ok:!0,nf_db:-33});await settle();R.demonte=[NT.length-nn,FX.length-nx];
  /* 11 : musique bouclée -> le title le dit ; nlAppris pur (forme à plat, garde 0,2 s, nf illisible -> 0) */
  M=mini(T.NoiseLearn);M.render(props({music:!0}));R.musique=/seul le plancher/.test(etat(M.H.out)[0][2]||"");M.unmount();
  R.nla=[T.nlAppris([{type:"denoise",learn_in:1,learn_out:2,nf:"x"}]),T.nlAppris([{type:"denoise",params:{learn_in:1,learn_out:1.1}}]),
    T.nlAppris(null),T.nlAppris([{type:"eq3"},{type:"denoise",params:{amount:3}},{type:"denoise",params:{learn_in:1,learn_out:2}}])];
  R.nul=T.NoiseLearn(null);
  out.R=R;
})().catch(function(e){out.err=String(e&&e.stack||e)}).then(function(){console.log(JSON.stringify(out))});
"""
D6 = {}
if NODE and os.path.isfile(SRC_PATH) and globals().get("SRC") and len(_L6H) > 2000 and "function mini(" in _L6H:
    _sh6 = os.path.join(TMP, "shim_l6.js")
    with open(_sh6, "w", encoding="utf-8") as fh:
        fh.write('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + SRC + "\n" + PROBE_L6)
    _r6 = sh([NODE, _sh6])
    _l6x = (_r6.stdout or "").strip().splitlines()
    try:
        D6 = json.loads(_l6x[-1]) if _l6x else {}
    except Exception as _e:
        D6 = {"err": temoin(_e)}
    check("l6x_shim_execute_sans_erreur", _r6.returncode == 0 and "err" not in D6 and isinstance(D6.get("R"), dict),
          (D6.get("err"), (_r6.stderr or "")[-400:]))
else:
    check("l6x_shim_execute_sans_erreur", False, ("node, source ou harnais absents", len(_L6H)))
_R6 = D6.get("R") if isinstance(D6.get("R"), dict) else {}
_S6 = _R6.get("sans") if isinstance(_R6.get("sans"), list) and len(_R6.get("sans")) == 3 else [None] * 3
check("l6x_sans_plage_deux_boutons_rendus_grises_titres_aucune_requete_le_clic_ne_fait_rien",
      isinstance(_S6[0], list) and [b[:2] for b in _S6[0]] == [["Apprendre le bruit", True], ["Oublier", True]]
      and all(isinstance(b[2], str) and len(b[2]) > 10 for b in _S6[0]) and "plage I/O" in (_S6[0][0][2] or "")
      and _S6[1] == ["aucun bruit appris"] and _S6[2] == 0 and _R6.get("sans_clic") == [0, 0],
      [_S6, _R6.get("sans_clic")])
_D6d = _R6.get("demo") if isinstance(_R6.get("demo"), list) else [None] * 3
check("l6x_demo_grise_et_dit", _D6d[:2] == ["Apprendre le bruit", True] and "démonstration" in (_D6d[2] or ""), _D6d)
_RQ = _R6.get("req") if isinstance(_R6.get("req"), list) and len(_R6.get("req")) == 4 else [None] * 4
check("l6x_plage_12_13_devient_7_8_de_source_une_requete_noise_profile_libelle_mesure_grise_pas_de_seconde_requete",
      isinstance(_R6.get("pret"), list) and _R6["pret"][0][:2] == ["Apprendre le bruit", False] and "7–8 s de source" in (_R6["pret"][0][2] or "")
      and _RQ[:3] == [1, "/api/montage/noise-profile", {"src": {"audio": "a.wav"}, "t0": 7, "t1": 8, "fx": [{"type": "eq3", "params": {"bass_db": 2}}]}]
      and isinstance(_RQ[3], list) and _RQ[3][:2] == ["Mesure…", True] and _R6.get("pas_deux") == 1,
      [_R6.get("pret"), _RQ, _R6.get("pas_deux")])
check("l6x_reponse_ok_onFx_une_fois_pour_le_clip_vise_f_ecrit_le_debruiteur_appris_la_note_dit_la_plage",
      _R6.get("ok") == [1, "k", [{"type": "eq3", "params": {"bass_db": 2}},
                                 {"type": "denoise", "params": {"amount": 24, "nf": -30, "learn_in": 7, "learn_out": 8}}],
                        ["Bruit appris sur 7–8 s (source) : plancher -30 dB"], "Apprendre le bruit"],
      _R6.get("ok"))
check("l6x_plage_muette_et_refus_du_serveur_dits_rien_d_ecrit_bouton_rendu_actif",
      _R6.get("muet") == [1, ["Plage muette : rien à apprendre"]]
      and isinstance(_R6.get("err"), list) and _R6["err"][0] == 1 and _R6["err"][2] is False
      and isinstance(_R6["err"][1], list) and len(_R6["err"][1]) == 1 and _R6["err"][1][0].startswith("Apprentissage impossible : Not Found"),
      [_R6.get("muet"), _R6.get("err")])
check("l6x_plage_courte_bouton_actif_le_clic_dit_le_refus_rien_ne_part_duree_de_source_lue_dans_le_cache",
      _R6.get("courte_actif") is True
      and _R6.get("courte") == [0, ["Plage trop courte : il faut au moins 0,2 s de bruit seul (dans la source)"]]
      and _R6.get("cache") == [0, ["La plage sort de la source de ce clip : posez-la sur un passage que la source contient"]],
      [_R6.get("courte_actif"), _R6.get("courte"), _R6.get("cache")])
check("l6x_clip_appris_oublier_actif_etat_dit_clic_retire_la_plage_module_garde",
      _R6.get("appris") == [False, ["appris 7–8 s · -31 dB"]]
      and _R6.get("oublie") == [1, "k", [{"type": "denoise", "params": {"amount": 30}}],
                                ["Bruit appris oublié : le débruiteur reste, plancher automatique"]],
      [_R6.get("appris"), _R6.get("oublie")])
check("l6x_demonte_pendant_la_mesure_la_reponse_tardive_ne_note_ni_n_ecrit_rien_musique_dite",
      _R6.get("demonte") == [0, 0] and _R6.get("musique") is True, [_R6.get("demonte"), _R6.get("musique")])
check("l6x_nlAppris_pur_forme_a_plat_garde_0_2_premier_denoise_seul_null_sans_clip",
      _R6.get("nla") == [{"a": 1, "b": 2, "nf": 0}, None, None, None] and "nul" in _R6 and _R6.get("nul") is None, _R6.get("nla"))
_NLA = _corps("dzmNlAppris")
check("l6x_nlAppris_pur_ni_r_ni_x_ni_reseau_ni_dom_exporte_une_fois_composant_avant_la_zone_l5",
      len(_NLA) > 200 and not re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|\bnavigator\b|fetch\(|setClips|pushHistory", _NLA)
      and _DT.count("nlAppris:dzmNlAppris,NoiseLearn:DzmNoiseLearn,") == 1
      and 0 <= _SRCb.find("var DZM_VO_MIMES=") < _SRCb.find("function DzmNoiseLearn(o){") < _SRCb.find("function DzmScopes(o){")
      and _SRCb.count('dzmGpFetch("/api/montage/noise-profile",') == 1,
      [len(_NLA), _DT.count("NoiseLearn:DzmNoiseLearn,")])

print("\n[41] L6 D-26 : l'enregistreur de voix off — le composant joue sous le mini-React, faux micro injecte (tache 6, 25/09/2026)")
# ── L6 (25/09/2026, tache 6). DzmVoiceRec sous le MEME harnais que [40] (tranche _L6H de PROBE_L5X) ; le micro et
# l'enregistreur sont INJECTES (o.rec = {media, Rec, juge}) ; le reseau est un faux `fetch` propre a cette section (le
# corps est un FormData, que le faux de [40] ne sait pas lire). Aucune route payante : l'URL appelee est RELEVEE et
# comparee (jamais /api/audio/voiceover). Faute n6 : chaque lecture passe par .get / une liste de longueur verifiee.
PROBE_L6V = _L6H + r"""
var FV=[];G.fetch=function(u,op){var d={},p=new Promise(function(a,b){d.a=a;d.b=b});
  var f=op&&op.body&&typeof op.body.get==="function"?op.body.get("file"):null;
  FV.push({u:u,m:op&&op.method,champs:op&&op.body&&typeof op.body.keys==="function"?Array.from(op.body.keys()):null,
    nom:f&&f.name,type:f&&f.type,taille:f&&f.size,d:d});return p};
function vrep(i,ok,st,j){FV[i].d.a({ok:ok,status:st,json:function(){return Promise.resolve(j)}})}
function bts(m){return tous(m).filter(function(n){return n.t==="button"})}
function etat(m){return bts(m).map(function(b){return [txt(b),!!b.p.disabled,typeof b.p.title==="string"?b.p.title:null,b.p["data-rec"]||""]})}
var RC=[],CN=[],PISTES=[],RecCrash=null;
function flux(){var f={pistes:[{n:0,stop:function(){this.n++}}],getTracks:function(){return this.pistes}};PISTES.push(f);return f}
function FauxRec(fl,opt){this.fl=fl;this.opt=opt===void 0?null:opt;this.state="inactive";this.mimeType=(opt&&opt.mimeType)||"";this.starts=[];this.stops=0;RC.push(this)}
FauxRec.prototype.start=function(ts){this.state="recording";this.starts.push(ts)};
FauxRec.prototype.stop=function(){this.stops++;if(this.state==="inactive")return;this.state="inactive";var s=this;
  Promise.resolve().then(function(){if(s.ondataavailable)s.ondataavailable({data:s.vide?new Blob([]):new Blob(["prise"],{type:"audio/ogg"})});
    if(s.onstop)s.onstop()})};
function RecVide(fl,opt){FauxRec.call(this,fl,opt);this.vide=!0}RecVide.prototype=FauxRec.prototype;
var OGG=function(t){return t==="audio/ogg;codecs=opus"};
function inj(extra){return Object.assign({media:function(c){CN.push(c);return Promise.resolve(flux())},Rec:FauxRec,juge:OGG},extra||{})}
var R={},NT=[],ST=[],SP=[],DN=[];
function props(extra){var ctl={current:null};return Object.assign({demo:!1,ctl:ctl,rec:inj(),
  onNote:function(m){NT.push(m)},onStart:function(){ST.push(1);return 12.5},onStop:function(){SP.push(1)},
  onDone:function(f,d,t0){DN.push([f,d,t0])}},extra||{})}
(async function(){
  /* 1 : démo -> UN bouton, grisé, titré ; la bascule du clavier (ctl) DIT le refus et n'ouvre pas le micro */
  var P=props({demo:!0}),M=mini(T.VoiceRec);M.render(P);R.demo=[etat(M.H.out),typeof P.ctl.current];
  P.ctl.current();await settle();R.demo_ctl=[CN.length,NT.slice(-1),ST.length];M.unmount();
  /* 2 : sans injection (node n'a ni micro ni enregistreur) -> « Micro indisponible », rien ne démarre, le bouton reste actif */
  P=props({rec:null});M=mini(T.VoiceRec);M.render(P);bts(M.H.out)[0].p.onClick();await settle();M.flush();
  R.absent=[NT.slice(-1),ST.length,etat(M.H.out)[0].slice(0,2)];M.unmount();
  /* 3 : micro refusé -> la raison est dite, retour au repos */
  P=props({rec:inj({media:function(){return Promise.reject({name:"NotAllowedError",message:"Permission denied"})}})});
  M=mini(T.VoiceRec);M.render(P);bts(M.H.out)[0].p.onClick();M.flush();R.refus_attente=etat(M.H.out)[0].slice(0,2);
  await settle();M.flush();R.refus=[NT.slice(-1),ST.length,etat(M.H.out)[0].slice(0,2)];M.unmount();
  /* 4 : LE CYCLE. clic -> micro demandé (audio), enregistreur au type choisi par le juge, onStart UNE fois (t0 = 12,5),
     bouton « ■ … » titré ; second clic -> onStop UNE fois, pistes coupées, « envoi… » grisé ; la prise part UNE fois
     à /api/audio/recording (POST, champ file, prise.ogg) ; réponse -> onDone UNE fois avec (filename, dur, t0) */
  var n0=NT.length;P=props();M=mini(T.VoiceRec);M.render(P);R.repos=etat(M.H.out);
  bts(M.H.out)[0].p.onClick();bts(M.H.out)[0].p.onClick();M.flush();R.attente=[etat(M.H.out)[0].slice(0,2),CN.length];
  await settle();M.flush();var rc=RC[RC.length-1];
  R.prise=[CN.slice(-1),rc&&rc.opt,rc&&rc.state,rc&&rc.starts.length,ST.length,etat(M.H.out)[0],typeof P.ctl.current];
  bts(M.H.out)[0].p.onClick();M.flush();var fl=PISTES[PISTES.length-1];
  R.arret=[SP.length,fl&&fl.pistes[0].n,etat(M.H.out)[0].slice(0,2),rc&&rc.stops];
  await settle();M.flush();
  R.envoi=[FV.length,FV[0]&&FV[0].u,FV[0]&&FV[0].m,FV[0]&&FV[0].champs,FV[0]&&FV[0].nom,FV[0]&&FV[0].taille>0];
  /* les rappels sont lus sur les DERNIERES props : un rendu de l'hote pendant l'envoi remplace onDone */
  P=Object.assign({},P,{onDone:function(f,d,t0){DN.push(["neuf",f,d,t0])}});M.render(P);
  vrep(0,!0,200,{ok:!0,filename:"voix-off-20260925-101010.wav",url:"/audio/voix-off-20260925-101010.wav",dur:3.25,size_kb:305});
  await settle();M.flush();R.pose=[DN.slice(),etat(M.H.out)[0].slice(0,2),NT.slice(n0)];
  /* 5 : LA BASCULE DU CLAVIER (ctl) fait le même cycle ; l'envoi échoue (415) -> « prise non enregistrée », rien de posé */
  P.ctl.current();await settle();M.flush();P.ctl.current();await settle();M.flush();
  R.ctl=[ST.length,SP.length,FV.length];vrep(1,!1,415,{detail:"Enregistrement illisible"});await settle();M.flush();
  R.echec=[DN.length,NT.slice(-1),etat(M.H.out)[0].slice(0,2)];
  /* 6 : réponse sans durée lisible -> dite, rien de posé (addAsset partirait mesurer la durée hors du mode forcé) */
  bts(M.H.out)[0].p.onClick();await settle();M.flush();bts(M.H.out)[0].p.onClick();await settle();M.flush();
  vrep(2,!0,200,{ok:!0,filename:"voix-off-x.wav",dur:0});await settle();M.flush();R.sans_duree=[DN.length,NT.slice(-1)];
  M.unmount();
  /* 7 : DÉMONTAGE PENDANT UNE PRISE -> enregistreur arrêté, flux coupé, rien d'envoyé, rien de dit, rien de posé */
  var nf=FV.length,nn=NT.length;P=props();M=mini(T.VoiceRec);M.render(P);bts(M.H.out)[0].p.onClick();await settle();M.flush();
  rc=RC[RC.length-1];fl=PISTES[PISTES.length-1];M.unmount();await settle();
  R.demonte=[rc&&rc.state,rc&&rc.stops,fl&&fl.pistes[0].n,FV.length-nf,NT.length-nn,P.ctl.current];
  /* 8 : démontage PENDANT l'accord du micro -> le flux arrivé en retard est coupé aussitôt, aucun enregistreur */
  var dly={},nr=RC.length;P=props({rec:inj({media:function(){return new Promise(function(a){dly.a=a})}})});
  M=mini(T.VoiceRec);M.render(P);bts(M.H.out)[0].p.onClick();M.unmount();var tard=flux();dly.a(tard);await settle();
  R.tard=[tard.pistes[0].n,RC.length-nr];
  /* 9 : prise vide -> dite, rien d'envoyé ; 10 : sans type accepté par le juge -> enregistreur SANS option */
  nf=FV.length;P=props({rec:inj({Rec:RecVide})});M=mini(T.VoiceRec);M.render(P);bts(M.H.out)[0].p.onClick();await settle();M.flush();
  bts(M.H.out)[0].p.onClick();await settle();M.flush();R.vide=[FV.length-nf,NT.slice(-1)];M.unmount();
  P=props({rec:inj({juge:function(){return !1}})});M=mini(T.VoiceRec);M.render(P);bts(M.H.out)[0].p.onClick();await settle();M.flush();
  R.sans_type=[RC[RC.length-1].opt];M.unmount();
  /* 11 : aides pures */
  R.pur=[T.voExt("audio/ogg;codecs=opus"),T.voExt("audio/mp4"),T.voExt("audio/webm;codecs=opus"),T.voExt(""),T.voExt(null),
    T.voChrono(0),T.voChrono(3.9),T.voChrono(65),T.voChrono(-2),T.voChrono("x"),
    T.voErr({name:"NotAllowedError"}),T.voErr({name:"NotFoundError"}),T.voErr(new Error("boum")),T.voErr(null)];
  R.nul=T.VoiceRec(null);
  /* revue T6 — 13 : ARRÊT SPONTANÉ (erreur de l'enregistreur puis arrêt, sans passer par la puce) -> la raison est dite,
     les pistes coupées, la lecture arrêtée, « envoi… » ; le clavier pendant l'envoi dit l'attente ; la prise part quand
     même, et onDone reçoit l'identité du projet rendue par onStart ({t0, pj}) */
  RecCrash=function(fl,opt){FauxRec.call(this,fl,opt)};RecCrash.prototype=Object.create(FauxRec.prototype);
  RecCrash.prototype.crash=function(){this.state="inactive";var s=this;Promise.resolve().then(function(){
    if(s.onerror)s.onerror({error:{name:"NotReadableError"}});
    if(s.ondataavailable)s.ondataavailable({data:new Blob(["x"],{type:"audio/ogg"})});if(s.onstop)s.onstop()})};
  var D4=[],sp0=SP.length,nf0=FV.length;
  P=props({rec:inj({Rec:RecCrash}),onStart:function(){return {t0:4,pj:"P1"}},onDone:function(f,d,t0,pj){D4.push([f,d,t0,pj])}});
  M=mini(T.VoiceRec);M.render(P);bts(M.H.out)[0].p.onClick();await settle();M.flush();
  rc=RC[RC.length-1];fl=PISTES[PISTES.length-1];var nn0=NT.length;rc.crash();await settle();M.flush();
  R.crash=[fl.pistes[0].n,SP.length-sp0,etat(M.H.out)[0].slice(0,2),FV.length-nf0,NT.slice(nn0),rc.stops];
  P.ctl.current();R.crash_ctl=NT.slice(-1);
  vrep(FV.length-1,!0,200,{ok:!0,filename:"voix-off-c.wav",dur:1.5});await settle();M.flush();
  R.crash_pose=[D4.slice(),etat(M.H.out)[0].slice(0,2)];
  /* 14 : un refus 422 dont le détail est une LISTE -> détail sérialisé, jamais « [object Object] » */
  bts(M.H.out)[0].p.onClick();await settle();M.flush();RC[RC.length-1].crash();await settle();M.flush();
  vrep(FV.length-1,!1,422,{detail:[{loc:["body","file"],msg:"field required"}]});await settle();M.flush();R.d422=NT.slice(-1);M.unmount();
  /* 15 (reste de la tâche 5) : le plancher AFFICHÉ par « Apprendre le bruit » est celui du RENDU (dzmNfEffectif) */
  R.nfe=[T.nfEffectif(-5),T.nfEffectif(-0.3),T.nfEffectif(-0.5),T.nfEffectif(-90),T.nfEffectif(-31),T.nfEffectif("x"),T.nfEffectif(0),T.nfEffectif(null)];
  function nlst(nf){var AP={tr:"a1",id:"k",start:10,end:20,srcIn:5,src:{audio:"a.wav"},fx:[{type:"denoise",params:{amount:30,nf:nf,learn_in:7,learn_out:8}}]};
    var K=mini(T.NoiseLearn);K.render({clip:AP,range:null,demo:!1,music:!1,onNote:function(){},onFx:function(){}});
    var sn=tous(K.H.out).filter(function(n){return /dzm-nlst/.test(n.p.className||"")}).map(txt),
      ob=bts(K.H.out).filter(function(n){return txt(n)==="Oublier"}).map(function(n){return n.p.title});K.unmount();return [sn,ob]}
  R.nlst=[nlst(-5),nlst(-0.3),nlst(-31)];
  /* 12 : POURQUOI L'HÔTE FORCE « écraser » : en « insérer », la prise pousserait le clip suivant de la même piste */
  var CL=[{tr:"a1",id:"q",start:14,end:18,src:{audio:"z.wav"},srcIn:0}],NV={tr:"a1",id:"vo",start:12.5,end:15.75,src:{audio:"voix-off-1.wav"},srcIn:0};
  var ins=T.insere(CL,NV,"inserer",{tracks:T.DEFAULTS,head:12.5}),ecr=T.insere(CL,NV,"ecraser",{tracks:T.DEFAULTS,head:12.5});
  function q(res){var k=(res.clips||[]).filter(function(c){return c.id==="q"})[0];return k?[k.start,k.end]:null}
  R.mode=[q(ins),q(ecr)];
  out.R=R;
})().catch(function(e){out.err=String(e&&e.stack||e)}).then(function(){console.log(JSON.stringify(out))});
"""
D7 = {}
if NODE and os.path.isfile(SRC_PATH) and globals().get("SRC") and len(_L6H) > 2000 and "function mini(" in _L6H:
    _sh7 = os.path.join(TMP, "shim_l6v.js")
    with open(_sh7, "w", encoding="utf-8") as fh:
        fh.write('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + SRC + "\n" + PROBE_L6V)
    _r7 = sh([NODE, _sh7])
    _l7x = (_r7.stdout or "").strip().splitlines()
    try:
        D7 = json.loads(_l7x[-1]) if _l7x else {}
    except Exception as _e:
        D7 = {"err": temoin(_e)}
    check("l6v_shim_execute_sans_erreur", _r7.returncode == 0 and "err" not in D7 and isinstance(D7.get("R"), dict),
          (D7.get("err"), (_r7.stderr or "")[-400:]))
else:
    check("l6v_shim_execute_sans_erreur", False, ("node, source ou harnais absents", len(_L6H)))
_R7 = D7.get("R") if isinstance(D7.get("R"), dict) else {}
def _l7(k, n):
    v = _R7.get(k)
    return v if isinstance(v, list) and len(v) == n else [None] * n
_V1 = _l7("demo", 2)
_V1b = _l7("demo_ctl", 3)
check("l6v_demo_un_bouton_grise_titre_la_bascule_clavier_dit_le_refus_sans_ouvrir_le_micro",
      isinstance(_V1[0], list) and len(_V1[0]) == 1 and _V1[0][0][:2] == ["● voix off", True]
      and "démonstration" in (_V1[0][0][2] or "") and _V1[1] == "function"
      and _V1b[0] == 0 and _V1b[2] == 0 and isinstance(_V1b[1], list) and len(_V1b[1]) == 1 and "démo" in _V1b[1][0],
      [_V1, _V1b])
_V2 = _l7("absent", 3)
check("l6v_sans_micro_ni_enregistreur_micro_indisponible_dit_rien_ne_demarre_bouton_actif",
      isinstance(_V2[0], list) and len(_V2[0]) == 1 and _V2[0][0].startswith("Micro indisponible : ")
      and _V2[1] == 0 and _V2[2] == ["● voix off", False], _V2)
_V3 = _l7("refus", 3)
check("l6v_micro_refuse_la_raison_est_dite_attente_grisee_retour_au_repos",
      _R7.get("refus_attente") == ["micro…", True]
      and _V3[0] == ["Micro indisponible : accès au micro refusé"] and _V3[1] == 0 and _V3[2] == ["● voix off", False],
      [_R7.get("refus_attente"), _V3])
_V4r = _R7.get("repos") if isinstance(_R7.get("repos"), list) else []
_V4a = _l7("attente", 2)
_V4 = _l7("prise", 7)
check("l6v_cycle_prise_micro_audio_type_du_juge_onStart_une_fois_bouton_a_deux_etats_titre_une_demande_malgre_deux_clics",
      len(_V4r) == 1 and _V4r[0][:2] == ["● voix off", False] and len(_V4r[0][2] or "") > 20 and "()" not in (_V4r[0][2] or "")
      and _V4a == [["micro…", True], 1]
      and _V4[0] == [{"audio": True}] and _V4[1] == {"mimeType": "audio/ogg;codecs=opus"} and _V4[2] == "recording"
      and _V4[3] == 1 and _V4[4] == 1 and isinstance(_V4[5], list) and str(_V4[5][0]).startswith("■ 0:0")
      and _V4[5][1] is False and "Arrêter" in (_V4[5][2] or "") and _V4[5][3] == "1" and _V4[6] == "function"
      and _V4r[0][2] != _V4[5][2],
      [_V4r, _V4a, _V4])
_V5 = _l7("arret", 4)
_V6 = _l7("envoi", 6)
check("l6v_second_clic_onStop_une_fois_pistes_coupees_envoi_grise_une_requete_audio_recording_multipart_file_prise_ogg",
      _V5 == [1, 1, ["envoi…", True], 1]
      and _V6 == [1, "/api/audio/recording", "POST", ["file"], "prise.ogg", True],
      [_V5, _V6])
_V7 = _l7("pose", 3)
check("l6v_reponse_onDone_des_dernieres_props_une_fois_avec_filename_dur_et_t0_de_la_tete_au_debut_retour_au_repos_rien_de_dit",
      # revue T6 : le second clic pendant « micro… » (bouton grise ; le clavier, lui, y arrive) DIT l'attente
      _V7 == [[["neuf", "voix-off-20260925-101010.wav", 3.25, 12.5]], ["● voix off", False], ["Voix off : accès au micro en cours…"]], _V7)
_V8 = _l7("ctl", 3)
_V8b = _l7("echec", 3)
check("l6v_bascule_clavier_meme_cycle_envoi_en_echec_dit_prise_non_enregistree_rien_de_pose",
      _V8 == [2, 2, 2] and _V8b[0] == 1
      and _V8b[1] == ["Envoi de la prise impossible : Enregistrement illisible — prise non enregistrée"]
      and _V8b[2] == ["● voix off", False],
      [_V8, _V8b])
_V9 = _l7("sans_duree", 2)
check("l6v_reponse_sans_duree_lisible_dite_rien_de_pose",
      _V9[0] == 1 and isinstance(_V9[1], list) and len(_V9[1]) == 1 and "prise non enregistrée" not in _V9[1][0]
      and "illisible" in _V9[1][0], _V9)
_V10 = _l7("demonte", 6)
check("l6v_demontage_pendant_la_prise_enregistreur_arrete_flux_coupe_rien_envoye_rien_dit_bascule_retiree",
      _V10 == ["inactive", 1, 1, 0, 0, None], _V10)
check("l6v_demontage_pendant_l_accord_le_flux_tardif_est_coupe_aucun_enregistreur",
      _R7.get("tard") == [1, 0], _R7.get("tard"))
_V11 = _l7("vide", 2)
check("l6v_prise_vide_dite_rien_envoye_sans_type_accepte_enregistreur_sans_option",
      _V11 == [0, ["Prise vide : rien n'a été capté — prise non enregistrée"]] and _R7.get("sans_type") == [None],
      [_V11, _R7.get("sans_type")])
check("l6v_aides_pures_extension_chrono_raison",
      _R7.get("pur") == ["ogg", "m4a", "webm", "webm", "webm", "0:00", "0:03", "1:05", "0:00", "0:00",
                         "accès au micro refusé", "aucun micro détecté", "boum", "erreur inconnue"]
      and "nul" in _R7 and _R7.get("nul") is None, _R7.get("pur"))
_V12 = _l7("mode", 2)
check("l6v_pourquoi_ecraser_force_inserer_pousserait_le_clip_suivant_ecraser_le_rogne_sans_rien_decaler",
      isinstance(_V12[0], list) and _V12[0][0] > 14 and _V12[1] == [15.75, 18], _V12)
_V13 = _l7("crash", 6)
check("l6v_arret_spontane_raison_dite_pistes_coupees_lecture_arretee_passage_par_envoi_la_prise_part_une_fois",
      _V13 == [1, 1, ["envoi…", True], 1, ["Enregistreur arrêté : micro occupé par une autre application"], 0]
      and _R7.get("crash_ctl") == ["Voix off : prise en cours d'envoi…"], [_V13, _R7.get("crash_ctl")])
check("l6v_arret_spontane_onDone_recoit_l_identite_du_projet_rendue_par_onStart",
      _R7.get("crash_pose") == [[["voix-off-c.wav", 1.5, 4, "P1"]], ["● voix off", False]], _R7.get("crash_pose"))
check("l6v_refus_422_detail_liste_serialise_jamais_object_Object",
      _R7.get("d422") == ['Envoi de la prise impossible : [{"loc":["body","file"],"msg":"field required"}] — prise non enregistrée'],
      _R7.get("d422"))
check("l6v_nfEffectif_regle_du_rendu_auto_au_dessus_de_moins_0_5_sinon_borne_80_20",
      _R7.get("nfe") == [-20, None, -20, -80, -31, None, None, None], _R7.get("nfe"))
_NLS = _R7.get("nlst") if isinstance(_R7.get("nlst"), list) and len(_R7.get("nlst")) == 3 else [[None, None]] * 3
check("l6v_statut_et_title_d_oublier_montrent_le_plancher_du_rendu_moins_5_devient_moins_20_moins_0_3_auto_temoin_moins_31",
      _NLS[0][0] == ["appris 7–8 s · -20 dB"] and isinstance(_NLS[0][1], list) and len(_NLS[0][1]) == 1 and "plancher -20 dB" in _NLS[0][1][0]
      and _NLS[1][0] == ["appris 7–8 s · auto"] and "plancher automatique" in (_NLS[1][1] or [""])[0]
      and _NLS[2][0] == ["appris 7–8 s · -31 dB"], _NLS)
_VRC = _corps("DzmVoiceRec")
_VPU = {n: _corps(n) for n in ("dzmVoExt", "dzmVoChrono", "dzmVoErr")}
check("l6v_aides_pures_ni_r_ni_x_ni_api_navigateur_composant_lit_micro_et_enregistreur_a_l_appel_route_unique",
      all(len(c) > 40 for c in _VPU.values())
      and not any(re.search(r"\br\.jsx|\bx\.use|localStorage|\bwindow\b|\bdocument\b|\bnavigator\b|MediaRecorder|"
                            r"getUserMedia|isTypeSupported|fetch\(|setClips|pushHistory|URL\.", c) for c in _VPU.values())
      and len(_VRC) > 2500 and _VRC.count('fetch("/api/audio/recording",{method:"POST",body:fd})') == 1
      and _VRC.count("/api/audio/voiceover") == 0 and _SRCb.count("/api/audio/voiceover") == 0
      and _VRC.count("getTracks()") == 1 and _VRC.count("typeof MediaRecorder") == 1 and _VRC.count('typeof navigator!=="undefined"?navigator:null') == 1 and _VRC.count("N.mediaDevices.getUserMedia(c)") == 1
      and _VRC.count('r.jsx("button",') == 1 and _VRC.count("x.useState(") == 2
      and _DT.count("voExt:dzmVoExt,voChrono:dzmVoChrono,voErr:dzmVoErr,VoiceRec:DzmVoiceRec,") == 1
      and 0 < _SRCb.find("function DzmNoiseLearn(o){") < _SRCb.find("function DzmVoiceRec(o){") < _SRCb.find("function DzmScopes(o){"),
      [len(_VRC), {n: len(c) for n, c in _VPU.items()}])
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
