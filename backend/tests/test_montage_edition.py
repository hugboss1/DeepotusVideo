# -*- coding: utf-8 -*-
"""L1 — LES MODES D'EDITION (D-2) : le coeur JS est EXECUTE sous node
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
    try:
        D = json.loads(derniere) if derniere else {}
    except Exception as e:
        D = {}; check("js_shim_json_illisible", False, temoin(e))
    else:
        check("js_shim_rend_un_objet_json", isinstance(D, dict) and bool(D), repr(derniere)[:160])

check("modes_les_six", D.get("modes") == ["ecraser","inserer","fin","dessus","ripple_ecraser","remplir"],
      D.get("modes"))
check("ecraser_rogne_et_fend", D.get("ecraser") == [["p1",0,2,None],["x",2,5,0],["p2",5,8,1]], D.get("ecraser"))
check("ecraser_ne_touche_pas_les_autres_pistes", D.get("ecraser_autres") == 1)
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

print("\n[2] etat vide (garde des assertions negatives)")
# Copie du banc pointee sur un fichier VIDE : si le shim meurt ou `D` reste
# `{}`, AUCUNE ligne au-dessus de celle-ci ne doit verdir sauf via un `in D`
# explicite (il n'y en a qu'une, `entrees_molles`, et elle EXIGE "mou" in D,
# donc elle rougit aussi). Prouve ici sur une COPIE dans un dossier temporaire.
vide_dir = tempfile.mkdtemp(prefix="dzl1_vide_")
try:
    vide_src = os.path.join(vide_dir, "montage_vide.js")
    with open(vide_src, "w", encoding="utf-8") as fh: fh.write("")
    vide_shim = os.path.join(vide_dir, "shim.js")
    with open(vide_shim, "w", encoding="utf-8") as fh:
        fh.write('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + "" + "\n" + PROBE)
    rv = sh([NODE, vide_shim]) if NODE else None
    vide_ok = 0
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
    vide_cles = ["modes","ecraser","inserer","fin","dessus_piste","ripple","remplir","jumeau"]
    vide_absent = all(k not in vide_dv for k in vide_cles)
    print(f"  (etat vide : returncode={'n/a' if rv is None else rv.returncode}, "
          f"D={vide_dv!r}, cles_absentes={vide_absent})")
finally:
    shutil.rmtree(vide_dir, ignore_errors=True)

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
