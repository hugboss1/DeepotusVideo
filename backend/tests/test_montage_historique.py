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
/* la sortie posee AVANT l entree : `in` retombe a 0, jamais de plage inversee */
out.r_out_avant_in=T.rangeSet({in:6,out:8},"out",4,10);
/* la plage degeneree : `in` colle a la duree, puis `out` ne peut plus suivre */
out.r_in_a_dur=T.rangeSet(null,"in",10,10);
out.r_from_degenere=T.rangeFrom({in:10,out:10});
/* le projet de DEPART du bundle n a pas de cle `range` : `undefined`, pas
   `null`. rangeSet doit rendre `null` dans les deux cas, sinon la sortie tot
   de R2 compare `null` a `undefined` et laisse passer. */
out.r_undef_clear=T.rangeSet(undefined,"clear",0,10);
out.r_undef_tete_illisible=T.rangeSet(void 0,"in",NaN,10);
/* MEME playhead, MEME bout : un objet NEUF, egal en valeurs. */
out.r_meme_valeur=T.rangeSet({in:3.2,out:null},"in",3.2,10);
/* [2b] cutOpts : les options de coupe, partagees par R2 et le tiroir Texte */
/* pistes CHOISIES hors table par defaut (« v9 » n y est pas) : sans cela la
   ligne verdirait sur les defauts, ou A2 est DEJA en boucle. */
out.co=T.cutOpts({tracks:[{id:"v1",kind:"video"},{id:"v9",kind:"video",loop:!0}]},{v1:{l:1},v9:{}});
out.co_vide=T.cutOpts(null,null);
/* [3] swap : ECHANGER deux plans voisins (D-4) */
var K=[{tr:"v1",id:"p1",start:0,end:4,srcIn:0,src:{a:1}},
       {tr:"v1",id:"p2",start:4,end:8,srcIn:2,src:{a:1}},
       {tr:"v1",id:"p3",start:8,end:10,srcIn:0,src:{a:1}}];
var KJ=JSON.stringify(K);
function parKId(cs,id){return cs.filter(function(k){return k.id===id})[0]}
function brefs(cs){return cs.map(function(k){return{id:k.id,start:k.start,end:k.end}})}
var sw1=T.swap(K,"p2",-1);
out.sw1_p2=parKId(sw1,"p2");out.sw1_p1=parKId(sw1,"p1");out.sw1_p3=parKId(sw1,"p3");
out.sw1_order=sw1.map(function(k){return k.id});
out.sw_pure=JSON.stringify(K)===KJ;
out.sw_p1_left=brefs(T.swap(K,"p1",-1));
out.sw_p3_right=brefs(T.swap(K,"p3",1));
out.sw_zz=brefs(T.swap(K,"zz",1));
var KGap=[{tr:"v1",id:"g1",start:0,end:4},{tr:"v1",id:"g2",start:4.2,end:8}];
out.sw_gap=brefs(T.swap(KGap,"g2",-1));
out.sw_null=T.swap(null,"p1",1);
var sw2=T.swap(K,"p2",1);
out.sw2_p2=parKId(sw2,"p2");out.sw2_p3=parKId(sw2,"p3");out.sw2_p1=parKId(sw2,"p1");
var KOther=[{tr:"v1",id:"o1",start:0,end:4},{tr:"v1",id:"o2",start:4,end:8},
            {tr:"a1",id:"oa",start:0,end:8}];
out.sw_other_piste=parKId(T.swap(KOther,"o2",-1),"oa");
var KTitre=[{tr:"v1",id:"t1",start:0,end:3},{tr:"v1",id:"t2",start:3,end:6}];
out.sw_titre=T.swap(KTitre,"t2",-1);
out.sw_dir0=brefs(T.swap(K,"p2",0));
out.sw_dirNaN=brefs(T.swap(K,"p2",NaN));
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
# LA SORTIE POSEE AVANT L ENTREE. Symetrique de `range_entree_apres_la_sortie`
# (qui pousse `out` a `dur`) : ici c est `in` qui retombe a 0. Les deux
# branches sont tenues, sinon une plage INVERSEE atteindrait `rippleCut`, qui
# la retournerait en silence -- la regle montrerait une chose, la coupe en
# ferait une autre.
check("range_sortie_avant_l_entree_ramene_l_entree_a_zero",
      D.get("r_out_avant_in") == {"in": 0, "out": 4}, D.get("r_out_avant_in"))
# LA TETE EN BOUT DE TIMELINE est une entree VALIDE : `dzmRangeNum` borne a
# `dur`, il ne refuse pas. C est la plage DEGENEREE qui suit (in == out) que
# `dzmRangeFrom` doit refuser -- et c est lui, pas `rangeSet`, qui garde
# `DzmRangeBar` et « Maj+X ».
check("range_entree_a_la_duree_est_gardee",
      D.get("r_in_a_dur") == {"in": 10, "out": None}, D.get("r_in_a_dur"))
# ASSERTION NEGATIVE GARDEE : la cle doit d abord ETRE LA. Sans le `in D`, un
# shim muet suffirait a verdir la ligne.
check("range_degeneree_n_est_pas_une_plage",
      "r_from_degenere" in D and D["r_from_degenere"] is None,
      f'"r_from_degenere" in D={"r_from_degenere" in D} '
      f'v={D.get("r_from_degenere")!r}')
# `undefined` N EST PAS `null`, ET LA FENETRE ETAIT REELLE : le projet de
# DEPART du bundle est `useState({demo:!0,...})`, SANS cle `range` (mesure du
# 21/09/2026). Si `rangeSet` rendait `undefined` ici, la sortie tot de R2
# comparerait `undefined` a `null` -- faux -- et X sur une plage vide au
# demarrage pousserait l historique. ASSERTIONS NEGATIVES GARDEES, et le `in D`
# porte VRAIMENT : `JSON.stringify` OMET une cle dont la valeur est
# `undefined`, donc la cle absente est exactement le mode de panne vise.
check("range_clear_sur_un_projet_sans_plage_rend_null",
      "r_undef_clear" in D and D["r_undef_clear"] is None,
      f'"r_undef_clear" in D={"r_undef_clear" in D} '
      f'v={D.get("r_undef_clear")!r}')
check("range_tete_illisible_sur_un_projet_sans_plage_rend_null",
      "r_undef_tete_illisible" in D and D["r_undef_tete_illisible"] is None,
      f'"r_undef_tete_illisible" in D={"r_undef_tete_illisible" in D} '
      f'v={D.get("r_undef_tete_illisible")!r}')
# I PUIS I AU MEME PLAYHEAD : `rangeSet` construit un objet NEUF a chaque
# "in" / "out", meme quand la tete n a pas bouge d un pouce. C est la mesure
# qui JUSTIFIE le second terme de la sortie tot de R2 (egalite de VALEURS) :
# l identite de reference seule ne pouvait pas voir ce cas. Le banc epingle
# ici l egalite des valeurs ; la forme du test, elle, est tenue par
# `D11_une_plage_inchangee_...` du banc bundle.
check("range_meme_bout_au_meme_playhead_rend_une_plage_egale",
      D.get("r_meme_valeur") == {"in": 3.2, "out": None},
      D.get("r_meme_valeur"))

print("\n[2b] cutOpts : les options de coupe, ecrites une seule fois")
# I-2 : la paire {loopTracks, locked} etait rebatie a l identique dans R_M12
# et dans R_R2. Elle est PURE et vit dans la couche ; ces deux lignes jouent
# ce que le pin de forme du banc bundle ne peut pas jouer -- le comportement.
# `l` (verrouillee) devient une CLE de `locked` ; `loop` devient un ID dans
# `loopTracks` ; une piste ni l un ni l autre n apparait nulle part.
check("cut_opts_separe_le_verrou_de_la_boucle",
      D.get("co") == {"loopTracks": ["v9"], "locked": {"v1": True}}, D.get("co"))
# ECART MESURE CONTRE LA CONSIGNE DE REVUE (21/09/2026), et la mesure gagne :
# la revue attendait `{loopTracks: [], locked: {}}` pour `cutOpts(null,null)`.
# FAUX -- `svmTracksOf(null)` passe par `dzmTsOr`, qui rend la table PAR
# DEFAUT, et A2 (musique) y porte `loop:!0` (montage.js l. 170). Un projet nul
# EST la timeline par defaut partout ailleurs dans la couche ; rendre une
# liste vide ici ferait ripper une piste que l ecran montre en boucle. Ce que
# la ligne tient : aucun verrou (l etat est nul) et la boucle PAR DEFAUT,
# nommee -- la cle est etablie presente avant la comparaison.
check("cut_opts_sans_projet_ni_etat_ne_verrouille_rien",
      "co_vide" in D and D["co_vide"] == {"loopTracks": ["a2"], "locked": {}},
      f'"co_vide" in D={"co_vide" in D} v={D.get("co_vide")!r}')

print("\n[3] swap : ECHANGER deux plans voisins (D-4)")
check("swap_p2_gauche_p2_prend_la_place_de_p1",
      D.get("sw1_p2") == {"tr": "v1", "id": "p2", "start": 0, "end": 4, "srcIn": 2, "src": {"a": 1}},
      D.get("sw1_p2"))
check("swap_p2_gauche_p1_prend_la_place_de_p2",
      D.get("sw1_p1") == {"tr": "v1", "id": "p1", "start": 4, "end": 8, "srcIn": 0, "src": {"a": 1}},
      D.get("sw1_p1"))
check("swap_p2_gauche_p3_ne_bouge_pas",
      D.get("sw1_p3") == {"tr": "v1", "id": "p3", "start": 8, "end": 10, "srcIn": 0, "src": {"a": 1}},
      D.get("sw1_p3"))
check("swap_ordre_du_tableau_rendu_inchange",
      D.get("sw1_order") == ["p1", "p2", "p3"], D.get("sw1_order"))
check("swap_est_pur_K_non_mute", D.get("sw_pure") is True)
check("swap_p1_sans_voisin_gauche_inchange",
      D.get("sw_p1_left") == [{"id": "p1", "start": 0, "end": 4},
                               {"id": "p2", "start": 4, "end": 8},
                               {"id": "p3", "start": 8, "end": 10}],
      D.get("sw_p1_left"))
check("swap_p3_sans_voisin_droit_inchange",
      D.get("sw_p3_right") == [{"id": "p1", "start": 0, "end": 4},
                                {"id": "p2", "start": 4, "end": 8},
                                {"id": "p3", "start": 8, "end": 10}],
      D.get("sw_p3_right"))
check("swap_id_inconnu_inchange",
      D.get("sw_zz") == [{"id": "p1", "start": 0, "end": 4},
                          {"id": "p2", "start": 4, "end": 8},
                          {"id": "p3", "start": 8, "end": 10}],
      D.get("sw_zz"))
check("swap_voisin_hors_tolerance_de_contact_inchange",
      D.get("sw_gap") == [{"id": "g1", "start": 0, "end": 4}, {"id": "g2", "start": 4.2, "end": 8}],
      D.get("sw_gap"))
check("swap_projet_nul_rend_tableau_vide", D.get("sw_null") == [], D.get("sw_null"))
check("swap_p2_droite_p3_prend_la_place_de_p2",
      D.get("sw2_p3") == {"tr": "v1", "id": "p3", "start": 4, "end": 6, "srcIn": 0, "src": {"a": 1}},
      D.get("sw2_p3"))
check("swap_p2_droite_p2_prend_la_place_de_p3",
      D.get("sw2_p2") == {"tr": "v1", "id": "p2", "start": 6, "end": 10, "srcIn": 2, "src": {"a": 1}},
      D.get("sw2_p2"))
check("swap_p2_droite_p1_ne_bouge_pas",
      D.get("sw2_p1") == {"tr": "v1", "id": "p1", "start": 0, "end": 4, "srcIn": 0, "src": {"a": 1}},
      D.get("sw2_p1"))
check("swap_les_autres_pistes_ne_bougent_pas",
      D.get("sw_other_piste") == {"tr": "a1", "id": "oa", "start": 0, "end": 8}, D.get("sw_other_piste"))
# ASSERTION NEGATIVE GARDEE : un clip de titre sans `src` n'a pas de `srcIn` --
# JSON.stringify OMET une cle a `undefined`, donc l'absence de la cle EST le
# mode de panne vise (un `srcIn:null` invente passerait un `== None` nu).
_sw_titre = D.get("sw_titre") or [{}, {}]
check("swap_clip_de_titre_sans_src_pas_de_srcIn_invente",
      len(_sw_titre) == 2
      and {"tr": "v1", "id": "t1", "start": 3, "end": 6} == _sw_titre[0]
      and {"tr": "v1", "id": "t2", "start": 0, "end": 3} == _sw_titre[1]
      and "srcIn" not in _sw_titre[0] and "srcIn" not in _sw_titre[1],
      _sw_titre)
check("swap_dir_zero_inchange",
      D.get("sw_dir0") == [{"id": "p1", "start": 0, "end": 4},
                            {"id": "p2", "start": 4, "end": 8},
                            {"id": "p3", "start": 8, "end": 10}],
      D.get("sw_dir0"))
check("swap_dir_nan_inchange",
      D.get("sw_dirNaN") == [{"id": "p1", "start": 0, "end": 4},
                              {"id": "p2", "start": 4, "end": 8},
                              {"id": "p3", "start": 8, "end": 10}],
      D.get("sw_dirNaN"))
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
