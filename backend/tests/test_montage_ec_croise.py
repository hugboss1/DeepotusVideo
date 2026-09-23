# -*- coding: utf-8 -*-
"""E-C — BANC CROISE couche / bundle / feuille / backend / banc d'audit : les
LITERAUX que la couche `montage.js` ecrit en dur (la table des rubriques du
menu, les jetons de combo, le suffixe des apercus) doivent etre CEUX du bundle
livre et du service, et les listes que les bancs pinnent (les contextuels
toleres de l'audit E-12) doivent etre celles que le bundle porte VRAIMENT.
Fichier SEPARE de test_montage_edition.py / test_montage_bundle.py (un
processus, un code de sortie) : il ne monte NI TestClient NI l'app -- il lit
la couche, le bundle, la feuille, le service et le banc d'audit en OCTETS, et
joue sous node (shim par FICHIER, jamais `node -e`) les deux fonctions de
l'aller-retour. Modele : test_montage_eb_croise.py.
Run : & $PY tests/test_montage_ec_croise.py   (depuis backend/)

CE QUI EST COMPARE, ET COMMENT. Chaque literal est extrait par une regex
GARDEE : le temoin positif (la regex trouve EXACTEMENT UNE fois) est une
assertion a part entiere, avant toute lecture du groupe -- faute n°6 : aucune
lecture nue, une regex qui ne trouve rien fait ROUGIR le banc, pas mourir.

  [1] E-6 : chaque id de `DZM_MENU_RUB` (couche) EXISTE dans `SVM_ACTIONS`
      du bundle patche (45 entrees apres R_R1, 46 depuis L7 D-10, 48 depuis L7 D-6) ; les ids de SVM_ACTIONS qui
      n'y sont PAS sont exactement les treize gestes de tete (Lecture sans
      fullscreen/safezones, blade, title_add, adjust_add) que le repli
      `dzmMenuRub` envoie en Timeline -- liste pinnee, mesuree le 23/09/2026 ;
  [2] E-6 : chaque combo de `SVM_ACTIONS` est parsable par `dzmComboToKey`
      (non null) ET fait l'ALLER-RETOUR avec `svmComboOfEvent` du bundle
      (combo -> KeyboardEventInit -> combo identique), sous node, pour >= 40
      combos (45 mesurees) ; `svmKeyLabel` rend "" sans surcharge (le modele
      retombe sur la combo de la table) ; aucune combo ne porte « Cmd » ;
  [3] E-7 : `DZM_DEL_APERCU` (couche) == le suffixe que montage_service pose
      sur le titre d'un apercu (regex gardee des deux cotes) ;
  [4] E-10 : la cle `dz_svm_tb_dock` est LUE x1 et ECRITE x1 dans le bundle
      (x2 en tout), jamais dans la couche ;
  [5] E-10 : les SIX regles `[data-docked]` de la feuille, une fois chacune,
      et la PREMIERE regle `.dzsvm .dzm-tbar{` INTACTE (texte pinne : celle
      que les pins D-1 du banc bundle lisent) ;
  [6] E-12 : la liste TOLERES + BASCULES du banc d'audit
      (test_montage_ergonomie.py, lue par regex gardee et literal_eval) ==
      les conditionnels REELLEMENT presents dans les deux zones du bundle,
      forme par forme et compte par compte, avec le MEME scanner (RX_COND
      relu dans la source du banc) -- total 11, mesure le 23/09/2026.

Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif qui etablit que la mesure a eu lieu.
"""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
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
    ms = list(re.finditer(motif, texte, flags))
    return (ms[0] if len(ms) == 1 else None), len(ms)


JS = lire("frontend/patches/montage.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
CSS = lire("frontend/dist/shared/montage.css")
MSV = lire("backend/app/services/montage_service.py")
ERGO = lire("backend/tests/test_montage_ergonomie.py")
check("x0_couche_bundle_feuille_service_et_banc_d_audit_sont_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(BUN) > 1_000_000 and len(CSS) > 10_000 and len(MSV) > 100_000 and len(ERGO) > 5_000,
      (len(JS), len(BUN), len(CSS), len(MSV), len(ERGO)))

# ── [1] E-6 : DZM_MENU_RUB vs SVM_ACTIONS du bundle ─────────────────────
print("\n[1] E-6 : la table des rubriques vs la table des actions du bundle")
mR, nR = un(r'var DZM_MENU_RUB=\{(.*?)\};\nfunction dzmMenuRub\(a\)\{', JS, re.S)
check("x1_DZM_MENU_RUB_est_lue_une_fois_dans_la_couche_jusqu_a_dzmMenuRub", nR == 1 and mR is not None, nR)
_corpsR = re.sub(r"/\*.*?\*/", "", mR.group(1), flags=re.S) if mR else ""
RUB = dict(re.findall(r'(\w+):"([^"]+)"', _corpsR))
check("x1_la_table_porte_trente_quatre_ids_et_six_rubriques_moins_Projet_et_Timeline",
      len(RUB) == 34 and set(RUB.values()) == {"Édition", "Marqueurs", "Affichage", "Aide"}, (len(RUB), sorted(set(RUB.values()))))
_i0 = BUN.find("var SVM_ACTIONS=[")
_i1 = BUN.find("];", _i0) if _i0 >= 0 else -1
_TAB = BUN[_i0:_i1] if 0 <= _i0 < _i1 else ""
check("x1_SVM_ACTIONS_est_lue_une_fois_dans_le_bundle_jusqu_a_sa_fermeture",
      BUN.count("var SVM_ACTIONS=[") == 1 and len(_TAB) > 2000 and _TAB.count("{id:") >= 40, (BUN.count("var SVM_ACTIONS=["), len(_TAB)))
ACT = re.findall(r'^ \{id:"([a-z0-9_]+)",sec:"([^"]+)",lbl:"[^"]*",combo:"([^"]*)"\}', _TAB, re.M)
IDS = [a[0] for a in ACT]
SEC = {a[0]: a[1] for a in ACT}
COMBOS = [a[2] for a in ACT]
# 45 -> 46 le 24/09/2026 (L7 D-10, tache 1) : `trans_add` (sec Montage, « Alt+T »
# -- « Ctrl+T » et « Ctrl+Maj+T » sont reservees au navigateur, mesure), repli
# dans R_R1 ; hors DZM_MENU_RUB comme title_add / adjust_add -> Timeline.
# 46 -> 48 le 24/09/2026 (L7 D-6, tache 2) : `copy` (« Ctrl+C ») et `paste`
# (« Ctrl+V »), sec Montage, repli dans R_R1 ; ranges en Édition par DZM_MENU_RUB
# (32 -> 34 ids dans la table des rubriques).
NACT = 48
check("x1_le_bundle_patche_porte_quarante_huit_actions_ids_uniques_quatre_sections",
      len(ACT) == NACT and len(set(IDS)) == NACT and set(SEC.values()) == {"Lecture", "Montage", "Affichage", "Audio"},
      (len(ACT), sorted(set(SEC.values()))))
check("x1_chaque_id_de_la_table_des_rubriques_existe_dans_SVM_ACTIONS",
      len(RUB) == 34 and len(IDS) == NACT and set(RUB) <= set(IDS), sorted(set(RUB) - set(IDS)))
# les ids SANS rubrique tombent par `sec` : Lecture / Montage -> Timeline -- ce
# sont les QUATORZE gestes de tete (pinnes) ; aucun id Audio / Affichage n'est
# hors table (sinon le repli Audio -> Edition / Affichage parlerait a sa place)
HORS = set(IDS) - set(RUB)
TETE = {"play", "jog_back", "jog_pause", "jog_fwd", "step_back", "step_fwd", "cut_prev", "cut_next",
        "home", "end", "blade", "title_add", "adjust_add", "trans_add"}
check("x1_les_quatorze_ids_hors_table_sont_les_gestes_de_tete_Lecture_ou_Montage_vers_Timeline",
      len(RUB) == 34 and len(IDS) == NACT and HORS == TETE and all(SEC[i] in ("Lecture", "Montage") for i in HORS),
      sorted(HORS ^ TETE))
mRub, nRub = un(r'function dzmMenuRub\(a\)\{\n  var s=a&&DZM_MENU_RUB\[a\.id\];if\(s\)return s;\n  return a\.sec==="Audio"\?"Édition":a\.sec==="Affichage"\?"Affichage":"Timeline"\}', JS)
check("x1_le_repli_de_rubrique_est_ecrit_une_fois_Audio_Edition_Affichage_Affichage_sinon_Timeline", nRub == 1 and mRub is not None, nRub)
check("x1_les_quatre_marqueurs_vont_en_Marqueurs_keys_panel_en_Aide_undo_en_Edition",
      len(RUB) == 34 and all(RUB.get(k) == "Marqueurs" for k in ("marker_toggle", "marker_prev", "marker_next", "marker_index"))
      and RUB.get("keys_panel") == "Aide" and RUB.get("undo") == "Édition" and RUB.get("snap") == "Édition", RUB)

# ── [2] E-6 : chaque combo parsable et aller-retour sous node ──────────
print("\n[2] E-6 : combo -> touche -> combo, sous node")
mTok, nTok = un(r'^var DZM_KEY_TOK=\{[^\n]*\n[^\n]*\};$', JS, re.M)
mFn, nFn = un(r'^function dzmComboToKey\(combo\)\{\n(?:.*\n)*?  return k\.key\?k:null\}$', JS, re.M)
mEv, nEv = un(r'^var SVM_EV_NAMES=\{[^;]*\};$', BUN, re.M)
mEvs, nEvs = un(r'^var SVM_EV_NAMED_SET=\{[^;]*\};$', BUN, re.M)
mCoe, nCoe = un(r'^function svmComboOfEvent\(e\)\{\n(?:.*\n)*?         \(e\.shiftKey&&keepMaj\?"Maj\+":""\)\+name\}$', BUN, re.M)
check("x2_les_cinq_morceaux_sont_extraits_une_fois_chacun_couche_x2_bundle_x3",
      (nTok, nFn, nEv, nEvs, nCoe) == (1, 1, 1, 1, 1) and None not in (mTok, mFn, mEv, mEvs, mCoe),
      (nTok, nFn, nEv, nEvs, nCoe))
check("x2_aucune_combo_ne_porte_Cmd_et_tous_les_jetons_sont_connus",
      len(COMBOS) == NACT and all(c for c in COMBOS) and not any("Cmd" in c for c in COMBOS)
      and all(all(t in ("Ctrl", "Maj", "Alt", "Suppr", "Espace", "Home", "End", "←", "→", "↑", "↓") or len(t) == 1
                  for t in c.split("+")) for c in COMBOS),
      [c for c in COMBOS if "Cmd" in c or not all(t in ("Ctrl", "Maj", "Alt", "Suppr", "Espace", "Home", "End", "←", "→", "↑", "↓") or len(t) == 1 for t in c.split("+"))])
RT = None
if NODE and None not in (mTok, mFn, mEv, mEvs, mCoe) and len(COMBOS) >= 40:
    _probe = "\n".join([mTok.group(0), mFn.group(0), mEv.group(0), mEvs.group(0), mCoe.group(0), """
var L=%s,out=[];
L.forEach(function(c){var k=dzmComboToKey(c);if(!k){out.push([c,null,null]);return}
  /* l'evenement que le navigateur produirait pour cette touche : `code` d'une lettre = KeyX, d'un espace = Space */
  var code=k.key===" "?"Space":(/^[a-z]$/.test(k.key)?"Key"+k.key.toUpperCase():"");
  out.push([c,Object.keys(k).sort().join(),svmComboOfEvent({key:k.key,code:code,ctrlKey:k.ctrlKey,shiftKey:k.shiftKey,altKey:k.altKey,metaKey:k.metaKey})])});
console.log(JSON.stringify(out));""" % json.dumps(COMBOS, ensure_ascii=False)])
    _d = tempfile.mkdtemp(prefix="dzecx_")
    _p = os.path.join(_d, "rt.js")
    with open(_p, "w", encoding="utf-8") as _fh:
        _fh.write(_probe)
    try:
        _r = subprocess.run([NODE, _p], capture_output=True, timeout=120)
        RT = json.loads(_r.stdout.decode("utf-8")) if _r.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        RT = None
    finally:
        shutil.rmtree(_d, ignore_errors=True)
check("x2_le_shim_node_a_tourne_et_rend_une_ligne_par_combo",
      NODE is not None and isinstance(RT, list) and len(RT) == len(COMBOS) == NACT, (NODE, None if RT is None else len(RT)))
_nuls = [x[0] for x in (RT or []) if x[1] is None]
_mauv = [x for x in (RT or []) if x[1] is not None and x[2] != x[0]]
check("x2_chaque_combo_est_parsable_par_dzmComboToKey_et_porte_les_cinq_cles_d_un_KeyboardEventInit",
      isinstance(RT, list) and len(RT) == NACT and _nuls == []
      and all(x[1] == "altKey,ctrlKey,key,metaKey,shiftKey" for x in RT), (_nuls, [x for x in (RT or []) if x[1] != "altKey,ctrlKey,key,metaKey,shiftKey"][:3]))
check("x2_aller_retour_svmComboOfEvent_rend_la_combo_de_depart_pour_les_48",
      isinstance(RT, list) and len(RT) == NACT and _mauv == [] and sum(1 for x in RT if x[2] == x[0]) == NACT, _mauv)
# svmKeyLabel rend "" sans surcharge (le modele retombe alors sur a.combo) ; le
# repli est ecrit UNE fois dans le bundle ET dans le modele de la couche
mKL, nKL = un(r'  function svmKeyLabel\(id\)\{\n    return km\.byId\[id\]\|\|\(SVM_ACTION_BY_ID\[id\]\?SVM_ACTION_BY_ID\[id\]\.combo:""\)\}', BUN)
check("x2_svmKeyLabel_rend_la_combo_de_la_table_ou_vide_et_le_modele_retombe_sur_a_combo",
      nKL == 1 and mKL is not None and JS.count('cb=(typeof keyLabel==="function"&&keyLabel(a.id))||a.combo||"";') == 1
      and BUN.count("DzTracks.menuModel(SVM_ACTIONS,svmKeyLabel)") == 1, (nKL, JS.count("||a.combo||")))

# ── [3] E-7 : le suffixe des apercus ───────────────────────────────────
print("\n[3] E-7 : le suffixe « aperçu » de la couche vs montage_service")
mSufJ, nSufJ = un(r'^var DZM_DEL_APERCU="([^"]+)";$', JS, re.M)
mSufS, nSufS = un(r'\+ \(" ([^"]+)" if preview else ""\)\)', MSV)
check("x3_le_suffixe_est_ecrit_une_fois_dans_la_couche_et_une_fois_dans_le_service", nSufJ == 1 and nSufS == 1 and mSufJ is not None and mSufS is not None, (nSufJ, nSufS))
check("x3_le_suffixe_de_la_couche_est_celui_du_service_apercu_480p",
      mSufJ is not None and mSufS is not None and mSufJ.group(1) == mSufS.group(1) == "(aperçu 480p)"
      and JS.count("DZM_DEL_APERCU") == 2, (mSufJ and mSufJ.group(1), mSufS and mSufS.group(1)))
# le service pose le suffixe sur name[:60] : un titre long garde le suffixe, la couche le cherche par indexOf
check("x3_le_service_tronque_a_60_puis_suffixe_et_la_couche_cherche_par_indexOf",
      mSufS is not None and MSV.count('or "montage")[:60]') == 1 and JS.count("t.indexOf(DZM_DEL_APERCU)>=0") == 1, MSV.count('or "montage")[:60]'))

# ── [4] E-10 : la cle dz_svm_tb_dock ───────────────────────────────────
print("\n[4] E-10 : la cle localStorage de l'ancrage")
_g = BUN.count('localStorage.getItem("dz_svm_tb_dock")')
_s = BUN.count('localStorage.setItem("dz_svm_tb_dock"')
check("x4_dz_svm_tb_dock_est_lue_x1_et_ecrite_x1_dans_le_bundle_x2_en_tout_jamais_dans_la_couche",
      _g == 1 and _s == 1 and BUN.count("dz_svm_tb_dock") == 2 and BUN.count("localStorage") >= 10 and JS.count("dz_svm_tb_dock") == 0,
      (_g, _s, BUN.count("dz_svm_tb_dock")))

# ── [5] E-10 : la feuille ──────────────────────────────────────────────
print("\n[5] E-10 : les six regles [data-docked] et la premiere regle intacte")
_DOCK = (
    ".dzsvm .dzm-tbar[data-docked]{position:static; bottom:auto; left:auto; transform:none; translate:none; margin-right:8px; flex:none; --lbl:none; box-shadow:none}",
    ".dzsvm .dzm-tbar[data-docked][data-off]{transform:none; width:0; margin:0; padding:0; border-width:0; overflow:hidden}",
    ".dzsvm .dzm-tbar[data-docked] .dzm-tbzone{padding:2px}",
    ".dzsvm .dzm-tbar[data-docked] .dzm-tbgrp{padding:0 3px}",
    ".dzsvm .dzm-tbar[data-docked] .dzm-tbhead{padding:0 2px 2px; font-size:7px; letter-spacing:.08em}",
    ".dzsvm .dzm-tbar[data-docked] .dzm-tbb, .dzsvm .dzm-tbar[data-docked] .dzm-tbb.dzm-solo{width:32px; padding:2px 0}")
check("x5_les_six_regles_data_docked_sont_presentes_une_fois_chacune_et_aucune_autre",
      all(CSS.count(r) == 1 for r in _DOCK) and len(re.findall(r"^\.dzsvm \.dzm-tbar\[data-docked\]", CSS, re.M)) == 6,
      ([CSS.count(r) for r in _DOCK], len(re.findall(r"^\.dzsvm \.dzm-tbar\[data-docked\]", CSS, re.M))))
mTb, nTb = un(r"^\.dzsvm \.dzm-tbar\{([^\n]*)$", CSS, re.M)
_TB_MESUREE = ("position:absolute; left:14px; top:auto; bottom:calc(100% + 8px);")
check("x5_la_premiere_regle_dzm_tbar_est_lue_une_fois_et_commence_comme_D_1_l_a_ecrite",
      nTb == 1 and mTb is not None and mTb.group(1).startswith(_TB_MESUREE) and "static" not in mTb.group(1) and "docked" not in mTb.group(1)
      and CSS.find(".dzsvm .dzm-tbar{") < CSS.find(".dzsvm .dzm-tbar[data-docked]{"),
      (nTb, mTb and mTb.group(1)[:80]))

# ── [6] E-12 : la liste des toleres du banc d'audit == le bundle ───────
print("\n[6] E-12 : TOLERES + BASCULES du banc d'audit vs les conditionnels du bundle")


def bloc(nom):
    """Le literal `NOM = [...]` du banc d'audit, evalue -- regex gardee."""
    m, n = un(r"^" + nom + r" = \[.*?^\]$", ERGO, re.M | re.S)
    if n != 1 or m is None:
        return None, n
    try:
        v = ast.literal_eval(m.group(0)[len(nom) + 3:])
    except (ValueError, SyntaxError):
        return None, n
    return v, n


BASC, nB = bloc("BASCULES")
TOL, nT = bloc("TOLERES")
mP, nP = un(r"^_PROPS = (r'[^\n]*')$", ERGO, re.M)
mC, nC = un(r"^RX_COND = re\.compile\((r'[^\n]*') \+ _PROPS\)$", ERGO, re.M)
_Z = {}
for k in ("Z1_DEB", "Z1_FIN", "Z2_DEB", "Z2_FIN"):
    mz, nz = un(r'^' + k + r' = "([^"\n]*)"$', ERGO, re.M)
    _Z[k] = mz.group(1) if nz == 1 and mz else None
check("x6_les_deux_listes_le_scanner_et_les_quatre_bornes_sont_lus_une_fois_dans_le_banc_d_audit",
      nB == 1 and nT == 1 and isinstance(BASC, list) and isinstance(TOL, list) and len(BASC) == 2 and len(TOL) == 9
      and nP == 1 and nC == 1 and mP is not None and mC is not None and all(_Z.values()),
      (nB, nT, nP, nC, _Z))
RX = None
if mP is not None and mC is not None:
    try:
        RX = re.compile(ast.literal_eval(mC.group(1)) + ast.literal_eval(mP.group(1)))
    except (ValueError, SyntaxError, re.error):
        RX = None
ZS = None
if all(_Z.values()) and all(BUN.count(v) == 1 for v in _Z.values()):
    ZS = [(BUN.find(_Z["Z1_DEB"]), BUN.find(_Z["Z1_FIN"])), (BUN.find(_Z["Z2_DEB"]), BUN.find(_Z["Z2_FIN"]))]
    if not (ZS[0][0] < ZS[0][1] < ZS[1][0] < ZS[1][1]):
        ZS = None
check("x6_les_deux_zones_du_bundle_sont_mesurees_1_1_et_ordonnees", ZS is not None and RX is not None, (ZS, RX is not None))
conds = []
if ZS is not None and RX is not None:
    for a, b in ZS:
        z = BUN[a:b]
        for m in RX.finditer(z):
            conds.append(re.sub(r"\s+", " ", z[max(0, m.start() - 80):m.end()]))
FORMES = {f: n for f, _, n in (BASC or []) + (TOL or [])} if isinstance(BASC, list) and isinstance(TOL, list) else {}
vus = {f: sum(1 for c in conds if f in c) for f in FORMES}
orphelins = [c for c in conds if sum(1 for f in FORMES if f in c) != 1]
check("x6_chaque_forme_datee_du_banc_d_audit_est_trouvee_dans_le_bundle_au_compte_dit",
      len(FORMES) == 11 and len(conds) >= 11 and all(vus[f] == n for f, n in FORMES.items()),
      {f[:40]: (vus.get(f), n) for f, n in FORMES.items() if vus.get(f) != n})
check("x6_aucun_conditionnel_du_bundle_n_est_orphelin_total_onze",
      len(FORMES) == 11 and len(conds) == sum(FORMES.values()) == 11 and orphelins == [], (len(conds), orphelins))
# ETAT VIDE : le meme scanner sur l'entree du patcher (.bak_montage, zone
# DzMontage seule) voit le `proj.demo?null:` du bouton or que le lot a retire
# -- sans ce temoin, « orphelins == [] » ne prouverait rien. MESURE (23/09) :
# le .bak porte DEUX `proj.demo?null:` mais le scanner n'en voit qu'UN devant
# un bouton (l'autre precede `libArm?`, dont la premiere branche est un span).
BAK = lire("frontend/dist/assets/index-BEOJX8L5.js.bak_montage")
_ck, _zk = [], ""
if RX is not None and _Z.get("Z1_DEB") and BAK.count(_Z["Z1_DEB"]) == 1 and BAK.count(_Z["Z1_FIN"]) == 1:
    _zk = BAK[BAK.find(_Z["Z1_DEB"]):BAK.find(_Z["Z1_FIN"])]
    for m in RX.finditer(_zk):
        _ck.append(re.sub(r"\s+", " ", _zk[max(0, m.start() - 80):m.end()]))
check("x6_etat_vide_le_bak_porte_deux_proj_demo_null_dont_un_devant_un_bouton_que_le_livre_n_a_plus",
      len(BAK) > 1_000_000 and len(_ck) >= 7 and _zk.count("proj.demo?null:") == 2
      and sum(1 for c in _ck if "proj.demo?null:" in c) == 1 and any("svm-goldbtn" in c and "proj.demo?null:" in c for c in _ck)
      and len(conds) >= 11 and sum(1 for c in conds if "proj.demo?null:" in c) == 0
      and BUN[ZS[0][0]:ZS[0][1]].count("proj.demo?null:") == 0,
      (len(BAK), len(_ck), _zk.count("proj.demo?null:"), sum(1 for c in _ck if "proj.demo?null:" in c)))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
