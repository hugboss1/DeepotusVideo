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
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
