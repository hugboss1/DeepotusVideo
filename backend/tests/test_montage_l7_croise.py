# -*- coding: utf-8 -*-
"""L7-A — BANC CROISE couche / bundle / service : ce que le lot L7-A ecrit
EN DUR d'un cote du reseau doit etre CE QUE l'autre cote lit, ou etre DATE
comme un ecart. Fichier SEPARE de test_montage_l7.py (un processus, un code
de sortie) : il ne monte NI TestClient NI l'app -- il lit la couche, le
bundle et le service en OCTETS, importe le service seul, et JOUE sous node
(a) les juges du BUNDLE (svmComboCanon, svmComboReserved, svmKmMerge,
SVM_ACTIONS -- extraits du fichier livre, jamais recopies, meme mecanique
que le controle « revue I1 » du banc bundle [L7] D-10) contre le preset de
la couche, (b) la couche ENTIERE (shim du banc edition) pour ovExtra,
boringDef et le payload des pistes. Modeles : test_montage_l4_croise.py
(regex gardees, deux mesures par borne : le LITERAL et le COMPORTEMENT),
test_montage_ec_croise.py (etat vide).
Run : & $PY tests/test_montage_l7_croise.py   (depuis backend/)

CE QUI EST COMPARE, ET COMMENT. Chaque literal est extrait par une regex
GARDEE : le temoin positif (la regex trouve EXACTEMENT UNE fois) est une
assertion a part entiere, avant toute lecture du groupe -- faute n°6 : aucune
lecture nue, une regex qui ne trouve rien fait ROUGIR le banc, pas mourir ;
un sous-processus node absent ou mort rend un dict VIDE, et chaque ligne
qui le lit exige d'abord la cle (etat vide construit).

  [1] D-10 : les ids du preset Resolve (couche, literal) ⊂ ids de
      SVM_ACTIONS (bundle, literal) ; sous node, chaque combo du preset est
      CANONISABLE par svmComboCanon (canon(c) === c), NON reservee par
      svmComboReserved, et svmKmMerge(preset).byId la RETIENT toutes (aucune
      collision) ; temoin d'etat non vide : « ctrl+t » se canonise en
      « Ctrl+T » ET est reservee (le juge voit bien une reservee), « Alt+T »
      est le defaut de trans_add -- ECART DATE 24/09/2026 : Ctrl+T et
      Ctrl+Maj+T sont au navigateur, le preset n'a PAS de transition ;
  [2] D-39 : DZM_DIFF_CLES (couche, literal JSON) ⊂ cles reellement EMISES
      par renderPayload (bundle : les cles du litteral `var o={…}` et les
      `o.<cle>=`) ∪ cles CLIENT connues -- MESURE 24/09/2026 : les orphelines
      sont EXACTEMENT ["label","text"] (« label » n'est jamais rendu, le
      « text » d'une replique voyage dans subsPayload().segments, celui d'un
      carton dans `title`) ; temoin : les autres cles sont emises (seize,
      dix-sept depuis l'ajout de `reframe` le 24/09/2026, cloture L7-B) ;
  [3] D-19 : les cles `radius`/`shadow` que renderPayload emet (`o.radius`,
      `o.shadow`) == les cles lues par `_ov_transform` (`spec`, regex) ;
      bornes IDENTIQUES des deux cotes : couche DZM_OV_RADIUS_MAX=200 et
      `s>=.5?1:0`, service `(0, 200, 0)` et `1 if f >= 0.5 else 0` ;
      comportement : pour huit entrees (999, -1, 40.4, "abc", .5, .49, True,
      2) `dzmOvExtra` sous node et `_ov_transform` en python rendent le MEME
      couple (radius, shadow) -- SAUF la demi, ECART DATE 24/09/2026 :
      `Math.round(.5)` vaut 1 sous node, `int(round(0.5))` vaut 0 en python
      (demi vers le pair) ; sans effet sur le fil, la couche emet un entier ;
  [4] D-22 : `svmTracksPayload` (couche, sous node) emet `lang`, `burn` et
      `name` d'une piste subs marquee, PAS burn:false sur s1 ; `_save_record`
      CONSERVE `tracks` tel quel (dict rendu), `_write_saved` + `_load_saved`
      les RELISENT sur TMP a l'identique, et `_tracks_meta` les IGNORE sans
      erreur (s2 : {kind subs, bus sfx, loop False, layer 0}, aucune des
      trois cles) ; temoin de forme : la ligne de la couche x1 dans le
      fichier ET dans le bundle, le corps de `_tracks_meta` ne cite ni lang
      ni burn ni name (temoin : il cite loop et bus) ;
  [5] D-8 : `DZM_BORING_DEF.fps` (couche, literal) == 30 == la cadence de
      l'apercu (`fps = 30`, regex) == la cadence de NEUF des dix presets de
      sortie `_DELIVER` (import) -- MESURE 24/09/2026 : le GIF (gif_480)
      est a 12, « tous a 30 » etait faux ; 30 ∈ _DELIVER_FPS ; sous node,
      boring() sans option == boring() avec {fps:30} sur une fixture au
      seuil (0,39 s = 11,7 images : jump ; 0,42 s = 12,6 : non), et diverge
      a {fps:60} (temoin que la cadence compte) -- ECART DATE 24/09/2026 :
      30 i/s est EN DUR dans la couche (DZM_AB_IMG=1/30, nudge du bundle
      `Math.round(ns*3000)/3000` x1) alors que 24/25/60 existent ; le juge
      des jump cuts compte en images a 30, pas a la cadence du preset.

Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif qui etablit que la mesure a eu lieu.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl7x_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
NODE = shutil.which("node")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def lire(rel):
    """Le fichier en OCTETS, decode, LF -- ou "" (le banc rougit, ne meurt pas)."""
    p = os.path.join(ROOT, *rel.split("/"))
    try:
        return open(p, "rb").read().decode("utf-8-sig").replace("\r\n", "\n")
    except OSError:
        return ""


def un(motif, texte, flags=0):
    """LA regex gardee : rend le match si le motif est trouve EXACTEMENT une
    fois, None sinon. Le compte est rendu a part pour le detail des lignes."""
    ms_ = list(re.finditer(motif, texte, flags))
    return (ms_[0] if len(ms_) == 1 else None), len(ms_)


def node_json(nom, script):
    """Ecrit le script, le joue sous node, rend le DERNIER objet JSON de sa
    sortie -- ou {} avec la raison (node absent, rc ≠ 0, sortie illisible) :
    l'etat VIDE, que chaque lecteur doit demasquer par la presence de sa cle."""
    if not NODE:
        return {}, "node absent du PATH"
    p = os.path.join(TMP, nom)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(script)
    try:
        r = subprocess.run([NODE, p], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {}, repr(e)
    if r.returncode != 0:
        return {}, "rc=%d %s" % (r.returncode, (r.stderr or "")[-400:])
    lignes = (r.stdout or "").strip().splitlines()
    try:
        d = json.loads(lignes[-1]) if lignes else None
    except ValueError:
        d = None
    return (d if isinstance(d, dict) else {}), ("" if isinstance(d, dict) else "sortie illisible : " + repr((r.stdout or "")[-200:]))


JS = lire("frontend/patches/montage.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
MSV = lire("backend/app/services/montage_service.py")
check("x0_couche_bundle_et_service_sont_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(BUN) > 1_000_000 and len(MSV) > 100_000, (len(JS), len(BUN), len(MSV)))
check("x0_node_est_sur_le_PATH_le_banc_joue_les_juges_du_bundle_et_la_couche", bool(NODE), NODE)

try:
    from app.services import montage_service as ms
except Exception as e:                       # le banc rougit, ne meurt pas
    ms = None
    print(f"  (import du service impossible : {e!r})")
check("x0_le_service_est_importe_et_porte_les_symboles_L7",
      ms is not None and all(hasattr(ms, k) for k in ("_ov_transform", "_save_record", "_write_saved", "_load_saved", "_tracks_meta", "_DELIVER", "_DELIVER_FPS")),
      ms is not None and [k for k in ("_ov_transform", "_save_record", "_write_saved", "_load_saved", "_tracks_meta", "_DELIVER", "_DELIVER_FPS") if not hasattr(ms, k)])

# -- la couche entiere sous node (shim du banc edition) -----------------------
_PROBE_JS = r"""
var T=DzTracks,out={};
out.ovx=[999,-1,40.4,"abc",.5,.49,true,2].map(function(v){var e=T.ovExtra({radius:v,shadow:v});return [e.radius,e.shadow]});
out.boringDef=T.boringDef;
var CLB=[{id:"a",tr:"v1",start:0,end:5,srcIn:0,src:{job_id:"j1"}},{id:"b",tr:"v1",start:5,end:8,srcIn:5.39,src:{job_id:"j1"}},
  {id:"c",tr:"v1",start:8,end:9,srcIn:8.81,src:{job_id:"j1"}}];
out.bo_defaut=T.boring(CLB);out.bo_30=T.boring(CLB,{fps:30});out.bo_60=T.boring(CLB,{fps:60});
out.tp=T.payload({tracks:[{id:"v1",kind:"video"},{id:"s1",kind:"subs"},{id:"s2",kind:"subs",lang:"en",burn:true,name:"S2 en"},{id:"a1",kind:"audio"}]});
out.kp=T.kmPreset("resolve");
console.log(JSON.stringify(out));
"""
_shim = '"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JS + "\n" + _PROBE_JS
D, _dwhy = node_json("l7x_couche.js", _shim)
check("x0_la_couche_s_execute_sous_node_et_rend_un_objet_json_avec_les_six_cles_de_la_sonde",
      bool(D) and all(k in D for k in ("ovx", "boringDef", "bo_defaut", "bo_30", "bo_60", "tp", "kp")), _dwhy or sorted(D))

# -- [1] D-10 : le preset Resolve contre les juges du bundle -------------------
print("\n[1] D-10 : preset Resolve (couche) vs SVM_ACTIONS / svmComboCanon / svmComboReserved / svmKmMerge (bundle, sous node)")
mP, nP = un(r'^var DZM_KM_PRESETS=(\{resolve:\{[^}]*\}\});$', JS, re.M)
PRESET = {}
if mP:
    # {resolve:{range_out:"O",toolbar:"Alt+O",blade:"Ctrl+B"}} -> JSON en citant les cles
    try:
        PRESET = json.loads(re.sub(r'([{,])([a-z_]+):', r'\1"\2":', mP.group(1)))["resolve"]
    except (ValueError, KeyError, TypeError):
        PRESET = {}
check("x1_le_preset_resolve_est_lu_une_fois_dans_la_couche_et_porte_trois_overrides_range_out_toolbar_blade",
      nP == 1 and mP is not None and PRESET == {"range_out": "O", "toolbar": "Alt+O", "blade": "Ctrl+B"}
      and isinstance(D.get("kp"), dict) and D.get("kp") == PRESET, (nP, PRESET, D.get("kp")))
_iA0 = BUN.find("var SVM_ACTIONS=[")
_iA1 = BUN.find("];", _iA0) if _iA0 >= 0 else -1
IDS_ACT = re.findall(r'\{id:"([a-z0-9_]+)",sec:"', BUN[_iA0:_iA1]) if 0 <= _iA0 < _iA1 else []
COMBOS_ACT = dict(re.findall(r'\{id:"([a-z0-9_]+)",sec:"[^"]*",lbl:"[^"]*",combo:"([^"]*)"\}', BUN[_iA0:_iA1])) if 0 <= _iA0 < _iA1 else {}
# L5 D-32 (24/09/2026, tache 6) : 48 -> 50 -- grade_copy (« Ctrl+Alt+C ») et grade_paste (« Ctrl+Alt+V »), repli R_R1 ; les
# libelles des checks gardent « 48 » (identifiants stables), les VALEURS sont realignees
check("x1_SVM_ACTIONS_du_bundle_x1_48_actions_ids_uniques_et_les_ids_du_preset_en_font_partie",
      BUN.count("var SVM_ACTIONS=[") == 1 and len(IDS_ACT) == 50 and len(set(IDS_ACT)) == 50 and len(COMBOS_ACT) == 50
      and COMBOS_ACT.get("grade_copy") == "Ctrl+Alt+C" and COMBOS_ACT.get("grade_paste") == "Ctrl+Alt+V"
      and len(PRESET) == 3 and all(i in IDS_ACT for i in PRESET), (len(IDS_ACT), [i for i in PRESET if i not in IDS_ACT]))
# ETAT VIDE : le meme compteur ne trouve pas un id invente
check("x1_etat_vide_le_meme_compteur_ne_trouve_pas_un_id_invente_temoin_blade_trouve",
      len(IDS_ACT) == 50 and "blade" in IDS_ACT and "zzz_pas_une_action" not in IDS_ACT and COMBOS_ACT.get("blade") == "Alt+C", COMBOS_ACT.get("blade"))
# ecart date : trans_add a pour defaut Alt+T, Ctrl+T et Ctrl+Maj+T sont dans la table des reservees du bundle
check("x1_ecart_date_24_09_2026_trans_add_par_defaut_Alt_T_et_Ctrl_T_Ctrl_Maj_T_reservees_par_le_bundle_le_preset_n_a_pas_de_transition",
      COMBOS_ACT.get("trans_add") == "Alt+T" and BUN.count('"Ctrl+T":1') == 1 and BUN.count('"Ctrl+Maj+T":1') == 1
      and len(PRESET) == 3 and "trans_add" not in PRESET and "delete" not in PRESET and COMBOS_ACT.get("delete") == "Suppr",
      (COMBOS_ACT.get("trans_add"), COMBOS_ACT.get("delete"), BUN.count('"Ctrl+T":1')))
# sous node : les juges EXTRAITS du bundle (meme decoupe que le banc bundle [L7] D-10, revue I1)
_iN1 = BUN.find("function svmNorm(s){"); _iN1f = BUN.find("\n", BUN.find("  return s}", _iN1)) if _iN1 >= 0 else -1
_iN2 = BUN.find("var SVM_ACTIONS=["); _iN2f = BUN.find("function svmKmSave(ov){") if _iN2 >= 0 else -1
_iN3 = BUN.find("function svmKmMerge(ov){"); _iN3f = BUN.find("var SVM_KMNOW_CACHE=") if _iN3 >= 0 else -1
check("x1_les_trois_decoupes_du_bundle_svmNorm_table_et_juges_fusion_sont_trouvees_dans_l_ordre",
      all(0 <= a < b for a, b in ((_iN1, _iN1f), (_iN2, _iN2f), (_iN3, _iN3f))) and _iN1 < _iN2 < _iN3, (_iN1, _iN1f, _iN2, _iN2f, _iN3, _iN3f))
K = {}
_kwhy = "decoupe absente"
if all(0 <= a < b for a, b in ((_iN1, _iN1f), (_iN2, _iN2f), (_iN3, _iN3f))):
    _kshim = ("var window={};var localStorage={getItem:function(){return null}};\n" + BUN[_iN1:_iN1f] + "\n" + BUN[_iN2:_iN2f] + "\n" + BUN[_iN3:_iN3f]
              + "\nvar P=" + json.dumps(PRESET) + ",out={canon:{},reserved:{},merge:{},temoin:{}};\n"
              + "Object.keys(P).forEach(function(id){out.canon[id]=svmComboCanon(P[id]);out.reserved[id]=svmComboReserved(P[id])});\n"
              + "var m=svmKmMerge(P).byId;Object.keys(P).forEach(function(id){out.merge[id]=m[id]});\n"
              + "out.temoin={ctrl_t:svmComboCanon(\"ctrl+t\"),ctrl_t_res:svmComboReserved(\"Ctrl+T\"),zzz:svmComboCanon(\"Zork+Q\"),alt_t:svmComboReserved(\"Alt+T\"),n:SVM_ACTIONS.length};\n"
              + "console.log(JSON.stringify(out));\n")
    K, _kwhy = node_json("l7x_keymap.js", _kshim)
check("x1_sous_node_chaque_combo_du_preset_est_canonisable_a_l_identique_et_non_reservee",
      len(PRESET) == 3 and isinstance(K.get("canon"), dict) and all(K["canon"].get(i) == c for i, c in PRESET.items())
      and isinstance(K.get("reserved"), dict) and all(K["reserved"].get(i) == "" for i in PRESET), _kwhy or (K.get("canon"), K.get("reserved")))
check("x1_sous_node_svmKmMerge_retient_les_trois_overrides_du_preset_aucune_collision",
      len(PRESET) == 3 and isinstance(K.get("merge"), dict) and all(K["merge"].get(i) == c for i, c in PRESET.items()), _kwhy or K.get("merge"))
# temoin d'etat non vide : le juge VOIT une reservee et une combo illisible
check("x1_temoin_les_juges_du_bundle_canonisent_ctrl_t_en_Ctrl_T_la_disent_reservee_refusent_Zork_Q_et_laissent_Alt_T_48_actions",
      isinstance(K.get("temoin"), dict) and K["temoin"].get("ctrl_t") == "Ctrl+T" and K["temoin"].get("ctrl_t_res") == "raccourci du navigateur"
      and K["temoin"].get("zzz") == "" and K["temoin"].get("alt_t") == "" and K["temoin"].get("n") == 50 == len(IDS_ACT), _kwhy or K.get("temoin"))

# -- [2] D-39 : DZM_DIFF_CLES vs les cles emises par renderPayload ------------
print("\n[2] D-39 : DZM_DIFF_CLES (couche) ⊂ cles emises par renderPayload (bundle) ∪ cles client -- orphelines datees")
mC, nC = un(r'^var DZM_DIFF_CLES=(\[[^\]]*\]);$', JS, re.M)
CLES = []
if mC:
    try:
        CLES = json.loads(mC.group(1))
    except ValueError:
        CLES = []
# REALIGNE le 24/09/2026 (cloture L7-B, T8) : `reframe` (D-40) rejoint DZM_DIFF_CLES -- dix-neuf cles, et renderPayload
# l'emet (`o.reframe=`) : les orphelines restent label et text, les emises passent de seize a dix-sept
check("x2_DZM_DIFF_CLES_lu_une_fois_dix_neuf_cles_uniques_dont_reframe", nC == 1 and len(CLES) == 19 and len(set(CLES)) == 19
      and "reframe" in CLES, (nC, CLES))
_iR0 = BUN.find("  function renderPayload(preview,queue){")
_iR1 = BUN.find("  function launchRender(", _iR0) if _iR0 >= 0 else -1
RP = BUN[_iR0:_iR1] if 0 <= _iR0 < _iR1 else ""
_iO0 = RP.find("var o={"); _iO1 = RP.find("opacity:c.opacity};", _iO0) if _iO0 >= 0 else -1
# le terminateur `opacity:c.opacity` FAIT PARTIE du litteral (mesure 24/09/2026 : sans lui, opacity passait pour orpheline)
LIT = re.findall(r'(?:\{|,|\n\s*)([a-zA-Z_]+):(?=[^:])', RP[_iO0:_iO1 + len("opacity:c.opacity")]) if 0 <= _iO0 < _iO1 else []
DOT = re.findall(r'\bo\.([a-zA-Z_]+)=', RP)
EMIS = sorted(set(LIT) | set(DOT))
check("x2_renderPayload_x1_le_litteral_var_o_et_les_o_cle_sont_lus_au_moins_vingt_cles_emises_dont_tr_src_start_end",
      BUN.count("  function renderPayload(preview,queue){") == 1 and 0 < _iR0 < _iR1 and 0 <= _iO0 < _iO1 and len(EMIS) >= 20
      and all(k in EMIS for k in ("tr", "src", "start", "end", "srcIn", "kind", "title", "transition", "transition_s", "effects", "opacity")), (len(EMIS), EMIS))
ORPH = sorted(k for k in CLES if k not in EMIS)
check("x2_date_24_09_2026_les_orphelines_de_DZM_DIFF_CLES_sont_exactement_label_et_text_les_dix_sept_autres_sont_emises",
      len(CLES) == 19 and len(EMIS) >= 20 and ORPH == ["label", "text"] and sum(1 for k in CLES if k in EMIS) == 17
      and "reframe" in EMIS, (ORPH, EMIS))
# le « text » d'une replique voyage dans subsPayload().segments (`text:` dans le corps de subsPayload), jamais dans clips ; « label » jamais
_iS0 = BUN.find("  function subsPayload(){"); _iS1 = BUN.find("  function subs", _iS0 + 10) if _iS0 >= 0 else -1
SP = BUN[_iS0:_iS1] if 0 <= _iS0 < _iS1 else ""
check("x2_text_voyage_dans_les_segments_de_subsPayload_x1_et_label_n_est_emis_ni_par_renderPayload_ni_par_subsPayload_temoin_start_end",
      len(SP) > 200 and SP.count("text:") == 1 and SP.count("start:") == 1 and SP.count("end:") == 1 and SP.count("label:") == 0
      and len(RP) > 2000 and RP.count("label:") == 0 and RP.count("o.label=") == 0 and RP.count("o.text=") == 0, (len(SP), SP.count("text:"), RP.count("label:")))
# ETAT VIDE : le meme extracteur voit une cle inventee absente, et voit `o.radius=` (D-19) presente
check("x2_etat_vide_l_extracteur_voit_radius_et_shadow_emis_et_ne_voit_pas_une_cle_inventee",
      len(EMIS) >= 20 and "radius" in DOT and "shadow" in DOT and "zzz_cle_inventee" not in EMIS, DOT)

# -- [3] D-19 : radius / shadow, cles et bornes des deux cotes ---------------
print("\n[3] D-19 : cles radius/shadow du payload client == spec de _ov_transform, bornes identiques, comportement egal")
mS, nS = un(r'"radius": \((\d+), (\d+), (\d+)\), "shadow": \((\d+), (\d+), (\d+)\)\}', MSV)
mR, nR = un(r'^var DZM_OV_RADIUS_MAX=(\d+);$', JS, re.M)
check("x3_spec_du_service_x1_radius_0_200_0_shadow_0_1_0_et_DZM_OV_RADIUS_MAX_x1_200",
      nS == 1 and nR == 1 and mS is not None and mR is not None and tuple(map(int, mS.groups())) == (0, 200, 0, 0, 1, 0) and int(mR.group(1)) == 200
      and int(mS.group(2)) == int(mR.group(1)), (nS, nR, mS and mS.groups(), mR and mR.group(1)))
check("x3_le_seuil_de_l_ombre_est_0_5_des_deux_cotes_couche_s_ge_point_5_service_f_ge_0_5",
      JS.count("shadow:isFinite(s)&&s>=.5?1:0}") == 1 and MSV.count("out[key] = 1 if f >= 0.5 else 0") == 1
      and BUN.count("shadow:isFinite(s)&&s>=.5?1:0}") == 1, (JS.count("s>=.5?1:0"), MSV.count("f >= 0.5")))
check("x3_renderPayload_emet_o_radius_si_gt_0_et_o_shadow_1_x1_et_le_service_lit_c_get_radius_et_shadow_dans_spec",
      len(RP) > 2000 and RP.count("if(tf.radius>0)o.radius=tf.radius;if(tf.shadow)o.shadow=1") == 1 and nS == 1
      and MSV.count('key not in ("radius", "shadow")') == 1, RP.count("o.radius="))
_ovt = []
if ms is not None:
    for v in (999, -1, 40.4, "abc", .5, .49, True, 2):
        try:
            t = ms._ov_transform({"radius": v, "shadow": v})
            _ovt.append([t["radius"], t["shadow"]] if t else [0, 0])
        except Exception as e:
            _ovt.append(repr(e))
# MESURE 24/09/2026 : sept des huit entrees rendent le MEME couple ; la HUITIEME (.5) diverge sur le rayon SEUL --
# JS `Math.round(.5)` = 1 (demi vers le haut), python `int(round(0.5))` = 0 (demi vers le pair) ; l'ombre est 1 des deux
# cotes (seuil >= 0,5). ECART DATE, sans effet sur le fil : renderPayload emet `tf.radius` DEJA arrondi par la couche
# (svmOvTfOf -> dzmOvExtra), le service recoit un entier ; et l'inspecteur avance par pas de 5.
check("x3_comportement_sept_entrees_sur_huit_dzmOvExtra_sous_node_et_ov_transform_rendent_le_meme_couple_radius_shadow",
      isinstance(D.get("ovx"), list) and len(D["ovx"]) == 8 and len(_ovt) == 8
      and [x for i, x in enumerate(D["ovx"]) if i != 4] == [x for i, x in enumerate(_ovt) if i != 4]
      and D["ovx"][0] == [200, 1] and D["ovx"][1] == [0, 0] and D["ovx"][2] == [40, 1] and D["ovx"][3] == [0, 0] and D["ovx"][5] == [0, 0] and D["ovx"][7] == [2, 1],
      (D.get("ovx"), _ovt))
check("x3_ecart_date_24_09_2026_la_demi_arrondit_a_1_sous_node_et_a_0_en_python_ombre_1_des_deux_cotes_temoin_1_5_vaut_2_en_python",
      isinstance(D.get("ovx"), list) and len(D["ovx"]) == 8 and len(_ovt) == 8 and D["ovx"][4] == [1, 1] and _ovt[4] == [0, 1]
      and ms is not None and ms._ov_transform({"radius": 1.5})["radius"] == 2 and RP.count("o.radius=tf.radius") == 1,
      (D.get("ovx") and D["ovx"][4], _ovt and _ovt[4]))

# -- [4] D-22 : lang / burn / name des pistes subs, du client au disque ------
print("\n[4] D-22 : svmTracksPayload emet lang/burn/name ; _save_record les garde, _load_saved les relit, _tracks_meta les ignore")
_LIGNE = 'if(t.kind==="subs"){if(t.lang)o.lang=String(t.lang);if(t.burn)o.burn=!0;if(t.lang&&t.name)o.name=String(t.name)}'
check("x4_la_ligne_de_svmTracksPayload_x1_dans_la_couche_et_x1_dans_le_bundle",
      JS.count(_LIGNE) == 1 and BUN.count(_LIGNE) == 1 and JS.count("function svmTracksPayload(proj){") == 1, (JS.count(_LIGNE), BUN.count(_LIGNE)))
TP = D.get("tp")
_s2 = next((t for t in TP if t.get("id") == "s2"), None) if isinstance(TP, list) else None
_s1 = next((t for t in TP if t.get("id") == "s1"), None) if isinstance(TP, list) else None
check("x4_sous_node_le_payload_porte_s2_lang_en_burn_true_name_S2_en_et_s1_sans_burn_ni_lang_ni_name",
      isinstance(TP, list) and len(TP) == 4 and _s2 == {"id": "s2", "kind": "subs", "lang": "en", "burn": True, "name": "S2 en"}
      and _s1 == {"id": "s1", "kind": "subs"}, TP)
REC = LOADED = META = None
_e4 = ""
if ms is not None and isinstance(TP, list):
    try:
        REC = ms._save_record({"name": "l7x", "ratio": "9:16", "duration": 3, "mix": {}, "clips": [], "tracks": TP})
        ms._write_saved(REC)
        LOADED = ms._load_saved()
        META = ms._tracks_meta(TP)
    except Exception as e:
        _e4 = repr(e)
check("x4_save_record_conserve_tracks_a_l_identique_et_load_saved_les_relit_sur_TMP",
      isinstance(REC, dict) and REC.get("tracks") == TP and isinstance(LOADED, dict) and LOADED.get("tracks") == TP and LOADED.get("name") == "l7x"
      and os.path.isfile(os.path.join(TMP, "montage_saved.json")), _e4 or (REC and REC.get("tracks"), LOADED and LOADED.get("tracks")))
check("x4_tracks_meta_ignore_lang_burn_name_sans_erreur_s2_kind_subs_bus_sfx_loop_False_layer_0_temoin_v1_video",
      isinstance(META, dict) and META.get("s2") == {"kind": "subs", "bus": "sfx", "loop": False, "layer": 0}
      and META.get("s1") == {"kind": "subs", "bus": "sfx", "loop": False, "layer": 0} and META.get("v1", {}).get("kind") == "video"
      and not ({"lang", "burn", "name"} & set(META.get("s2", {}))), _e4 or META)
_iM0 = MSV.find("def _tracks_meta(raw) -> dict:"); _iM1 = MSV.find("\ndef ", _iM0 + 10) if _iM0 >= 0 else -1
TMB = MSV[_iM0:_iM1] if 0 <= _iM0 < _iM1 else ""
check("x4_le_corps_de_tracks_meta_ne_cite_ni_lang_ni_burn_ni_name_temoin_loop_et_bus_cites",
      len(TMB) > 1000 and re.search(r'\bloop\b', TMB) is not None and re.search(r'\bbus\b', TMB) is not None
      and re.search(r'"lang"|\blang\b', TMB) is None and re.search(r'"burn"|\bburn\b', TMB) is None and re.search(r'"name"', TMB) is None, len(TMB))

# -- [5] D-8 : la cadence du boring detector vs celle du backend --------------
print("\n[5] D-8 : DZM_BORING_DEF.fps == 30 == cadence de l'apercu == cadence de chaque preset _DELIVER -- 30 i/s en dur, date")
mB, nB = un(r'^var DZM_BORING_DEF=\{maxS:(\d+),minFrames:(\d+),fps:(\d+)\};$', JS, re.M)
mA, nA = un(r'^        fps = 30\n    else:\n', MSV, re.M)
DELF = sorted({int(v.get("fps") or 0) for v in (getattr(ms, "_DELIVER", {}) or {}).values()}) if ms is not None else []
check("x5_DZM_BORING_DEF_lu_une_fois_8_12_30_et_sous_node_boringDef_le_rend",
      nB == 1 and mB is not None and tuple(map(int, mB.groups())) == (8, 12, 30) and D.get("boringDef") == {"maxS": 8, "minFrames": 12, "fps": 30}, (nB, D.get("boringDef")))
# MESURE 24/09/2026 : DIX presets, NEUF a 30 et le GIF (gif_480) a 12 -- « tous a 30 » etait faux ; c'est dit
_DEL = getattr(ms, "_DELIVER", {}) or {}
check("x5_la_cadence_de_l_apercu_est_30_x1_neuf_presets_de_sortie_a_30_et_le_gif_480_a_12_30_dans_DELIVER_FPS",
      nA == 1 and mA is not None and DELF == [12, 30] and len(_DEL) == 10 and sum(1 for v in _DEL.values() if v.get("fps") == 30) == 9
      and _DEL.get("gif_480", {}).get("fps") == 12 and 30 in tuple(getattr(ms, "_DELIVER_FPS", ()) or ()),
      (nA, DELF, getattr(ms, "_DELIVER_FPS", None)))
# comportement : au seuil (11,7 images a 30 = 0,39 s) le defaut et {fps:30} disent la meme chose ; a 60 (23,4 images) ils divergent -> temoin que fps compte
check("x5_sous_node_boring_sans_option_egal_boring_fps_30_b_jump_c_non_et_diverge_a_fps_60_temoin",
      D.get("bo_defaut") == {"b": "jump"} and D.get("bo_30") == {"b": "jump"} and D.get("bo_60") == {} and D.get("bo_defaut") == D.get("bo_30"),
      (D.get("bo_defaut"), D.get("bo_30"), D.get("bo_60")))
# MESURE 24/09/2026 : le nudge du bundle (`Math.round(ns*3000)/3000`, B:3917) est x1 -- le plan disait deux branches, une seule ligne les sert
check("x5_ecart_date_24_09_2026_30_i_s_en_dur_dans_la_couche_DZM_AB_IMG_1_30_x1_et_nudge_3000_du_bundle_x1_alors_que_24_25_60_existent",
      JS.count("var DZM_AB_IMG=1/30;") == 1 and BUN.count("*3000)/3000") == 1 and BUN.count("ns=Math.round(ns*3000)/3000;") == 1
      and tuple(getattr(ms, "_DELIVER_FPS", ()) or ()) == (24, 25, 30, 60),
      (JS.count("var DZM_AB_IMG=1/30;"), BUN.count("*3000)/3000"), getattr(ms, "_DELIVER_FPS", None)))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
