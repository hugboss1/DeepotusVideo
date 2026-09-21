# -*- coding: utf-8 -*-
"""L0 — HISTORIQUE COMPLET (D-0), PLAGE I/O (D-11), ECHANGE (D-4) : le cœur
JS est EXECUTE sous node (frontend/patches/montage.js, celui que le patcher
injecte), jamais lu. Shim par FICHIER, jamais `node -e`.
Run : & $PY tests\test_montage_historique.py   (depuis backend/)"""
import json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_PATH = os.path.join(ROOT, "frontend", "patches", "montage.js")
NODE = shutil.which("node")
TMP = tempfile.mkdtemp(prefix="dzl0_")
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
var P={clips:[{tr:"v1",id:"a",start:0,end:4},{tr:"a1",id:"b",start:0,end:2}],
       mixDb:{dialogue:-6},proj:{tracks:[{id:"v1",kind:"video"}],dur:10,
       subsStyle:{wordAnim:"glow"},range:{in:1,out:3},markers:[{t:2,color:"or"}],demo:!1}};
var s=T.histSnap(P);
out.snap_cles=Object.keys(s).sort();
out.snap_copie=s.clips===P.clips&&s.tracks===P.proj.tracks;   /* refs conservees, pas de copie */
out.snap_vide=T.histSnap(null);
out.snap_sans_proj=Object.keys(T.histSnap({clips:[],mixDb:{}})).sort();
out.snap_hors_proj=Object.keys(T.histSnap({clips:[],mixDb:{},dur:7,tracks:[{id:"z"}]})).sort();
var p1={tracks:[{id:"v1"}],dur:99,subsStyle:{wordAnim:"couleur"},range:null,markers:[],mixDb:{dialogue:0},name:"x"};
var a=T.histApply(p1,s);
out.apply_dur=a.dur; out.apply_tracks=a.tracks.length; out.apply_anim=a.subsStyle.wordAnim;
out.apply_range=a.range; out.apply_markers=a.markers.length; out.apply_nom=a.name;
out.apply_pur=p1.dur===99;
/* un instantane PARTIEL (l'ancien {clips,mixDb}) ne touche pas au reste */
var b=T.histApply(p1,{clips:[],mixDb:{dialogue:-3}});
out.partiel_dur=b.dur; out.partiel_mix=b.mixDb.dialogue; out.partiel_tracks=b.tracks.length;
out.apply_nul=T.histApply(p1,null)===p1;
out.apply_mou=T.histApply(null,s).dur;
/* ABSENT EST UN ÉTAT (correctif du 21/09/2026, vu à l'écran sur le projet de
   démonstration : pas de clé `proj.tracks`, donc l'instantané ne la portait
   pas et « Annuler » laissait la piste ajoutée). Le projet d'avant n'a QUE
   `dur` : l'instantané doit porter les cinq clés quand même, `tracks` à
   `undefined`, et `histApply` doit réécrire cette absence par-dessus un
   projet qui, lui, a des pistes. */
var s2=T.histSnap({clips:[],mixDb:{},proj:{dur:5}});
out.absent_porte_la_cle="tracks" in s2&&s2.tracks===void 0;
var a2=T.histApply({tracks:[{id:"v9"}],dur:1},s2);
out.absent_restaure="tracks" in a2&&a2.tracks===void 0&&a2.dur===5;
/* [2] plage I/O */
out.r_in=T.rangeSet(null,"in",3.2,10);
out.r_out=T.rangeSet({in:3.2,out:null},"out",7,10);
out.r_inverse=T.rangeSet({in:6,out:8},"in",9,10);       /* in > out : out suit */
out.r_borne=T.rangeSet(null,"out",99,10);
out.r_neg=T.rangeSet(null,"in",-4,10);
out.r_clear=T.rangeSet({in:1,out:2},"clear",0,10);
out.r_from=[T.rangeFrom({in:"1.5",out:4}),T.rangeFrom({in:5,out:2}),T.rangeFrom("x"),T.rangeFrom({in:1})];
out.r_len=[T.rangeLen({in:1,out:4.5}),T.rangeLen(null),T.rangeLen({in:2,out:null})];
console.log(JSON.stringify(out));
"""
print("\n[1] histSnap / histApply sous node")
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
check("hist_snap_porte_les_sept_cles",
      D.get("snap_cles") == ["clips", "dur", "markers", "mixDb", "range", "subsStyle", "tracks"],
      D.get("snap_cles"))
check("hist_snap_garde_les_references", D.get("snap_copie") is True)
check("hist_snap_nul_rend_objet_vide", D.get("snap_vide") == {})
check("hist_snap_sans_proj_ne_porte_que_clips_et_mix", D.get("snap_sans_proj") == ["clips", "mixDb"])
check("hist_snap_ne_lit_les_cinq_cles_que_dans_proj", D.get("snap_hors_proj") == ["clips", "mixDb"], D.get("snap_hors_proj"))
check("hist_apply_restaure_duree_pistes_style_plage_marqueurs",
      D.get("apply_dur") == 10 and D.get("apply_tracks") == 1 and D.get("apply_anim") == "glow"
      and D.get("apply_range") == {"in": 1, "out": 3} and D.get("apply_markers") == 1,
      {k: D.get(k) for k in ("apply_dur", "apply_tracks", "apply_anim", "apply_range", "apply_markers")})
check("hist_apply_ne_touche_pas_aux_autres_cles", D.get("apply_nom") == "x")
check("hist_apply_est_pur", D.get("apply_pur") is True)
check("hist_apply_partiel_ne_touche_que_ce_qu_il_porte",
      D.get("partiel_dur") == 99 and D.get("partiel_mix") == -3 and D.get("partiel_tracks") == 1,
      {k: D.get(k) for k in ("partiel_dur", "partiel_mix", "partiel_tracks")})
check("hist_apply_instantane_nul_rend_le_projet_tel_quel", D.get("apply_nul") is True)
check("hist_apply_projet_nul_ne_meurt_pas", D.get("apply_mou") == 10)
check("hist_snap_porte_une_cle_absente_comme_absente",
      D.get("absent_porte_la_cle") is True,
      f'absent_porte_la_cle={D.get("absent_porte_la_cle")}')
check("hist_apply_restaure_l_absence",
      D.get("absent_restaure") is True,
      f'absent_restaure={D.get("absent_restaure")}')
print("\n[2] plage I/O")
check("range_in_pose_l_entree", D.get("r_in") == {"in": 3.2, "out": None}, D.get("r_in"))
check("range_out_pose_la_sortie", D.get("r_out") == {"in": 3.2, "out": 7}, D.get("r_out"))
check("range_entree_apres_la_sortie_pousse_la_sortie", D.get("r_inverse") == {"in": 9, "out": 10},
      D.get("r_inverse"))
check("range_borne_a_la_duree", D.get("r_borne") == {"in": None, "out": 10}, D.get("r_borne"))
check("range_jamais_negative", D.get("r_neg") == {"in": 0, "out": None}, D.get("r_neg"))
# REGLE DES ASSERTIONS NEGATIVES. Le plan ecrivait `D.get("r_clear") is None` :
# a VIDE (shim muet, cle absente) cette ligne VERDIT toute seule -- mesure du
# 21/09/2026, banc rouge avant implementation, 1 passed / 22 failed, et le seul
# passed etait celui-la. La cle doit d'abord ETRE LA, et valoir null ensuite.
check("range_clear_rend_null", "r_clear" in D and D["r_clear"] is None,
      f'"r_clear" in D={"r_clear" in D} v={D.get("r_clear")!r}')
check("range_from_assainit",
      D.get("r_from") == [{"in": 1.5, "out": 4}, None, None, None], D.get("r_from"))
check("range_len", D.get("r_len") == [3.5, 0, 0], D.get("r_len"))
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
