# -*- coding: utf-8 -*-
"""RETOURS 26/09 (plan du 27/09, tache 4) -- LE GROUPE R7 DU MAILLON `montage`.

Deux retours, portes par des sections EN QUEUE du patcher montage (groupe R7,
pose apres R6), mesures sur le bundle LIVRE et sur .bak_montage (l'entree du
patcher), jamais sur la seule source du patcher :

  D   R7up1 -- `uploadVideo` lit le `detail` du serveur quand l'upload est
      refuse (415 « Fichier vide ou illisible : … » depuis la PR #31) au lieu
      de ne dire que « HTTP 415 ». Deux appelants : le noeud UGC du Studio et
      la Library -- ils affichent deja `.error`.
  F5  R7vm1..R7vm3 -- Seedance 2.5 devient le defaut du Studio cote client :
      la prop par defaut du noeud Seedance, le repli de `dzVmCost` quand le
      noeud n'a pas de modele (tarif 2.5 a 720p, 0,473 $/s, le meme que le
      backend de la tache 5) et le libelle « Défaut (… » du selecteur quand
      /api/video-models ne dit pas son defaut. Un graphe DEJA ENREGISTRE avec
      `model:"seedance-v1-pro"` le GARDE : le defaut n'entre que dans les props
      ABSENTES (fusion `ts` du bundle, jouee sous node).

Chaque fonction est EXTRAITE mot pour mot du bundle livre et jouee sous node
(faux fetch, faux React) ; le TEMOIN est la meme extraction faite dans
.bak_montage, qui doit rendre l'ancien comportement. AUCUN reseau, AUCUN
serveur.

Run : & $PY tests/test_retours_bundle_r7.py   (depuis backend/)
"""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
PATCHER = ROOT / "scripts" / "patch_bundle_montage.py"
NODE = shutil.which("node")
TMP = tempfile.mkdtemp(prefix="dzr7_")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def lire(p):
    try:
        return p.read_bytes().decode("utf-8-sig")
    except OSError:
        return ""


def node_json(nom, script):
    """Joue le script sous node (par FICHIER) et rend le DERNIER objet JSON de
    sa sortie -- ou {} et la raison (l'etat VIDE se voit a l'absence des cles)."""
    if not NODE:
        return {}, "node absent du PATH"
    p = os.path.join(TMP, nom)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(script)
    try:
        r = subprocess.run([NODE, p], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {}, repr(e)
    if r.returncode != 0:
        return {}, "rc=%d %s" % (r.returncode, (r.stderr or "")[-400:])
    lignes = (r.stdout or "").strip().splitlines()
    try:
        d = json.loads(lignes[-1]) if lignes else None
    except ValueError:
        d = None
    return (d if isinstance(d, dict) else {}), ("" if isinstance(d, dict) else "sortie illisible")


def entre(s, debut, fin):
    """Le texte de `debut` (inclus) a `fin` (exclu), ou "" si l'un manque."""
    i = s.find(debut)
    j = s.find(fin, i + len(debut)) if i >= 0 else -1
    return s[i:j] if i >= 0 and j > i else ""


S = lire(BUNDLE)
B = lire(BAK)
check("x0_bundle_et_bak_montage_lus_en_octets_et_non_vides",
      len(S) > 1_000_000 and len(B) > 1_000_000, (len(S), len(B)))
check("x0_node_est_sur_le_PATH", bool(NODE), NODE)
try:
    _spec = importlib.util.spec_from_file_location("patch_bundle_montage_r7", PATCHER)
    P = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(P)
except BaseException as _e:          # SystemExit compris
    print(f"  FAIL  patcher_importable {_e!r}")
    print("\n=== %d passed, %d failed ===" % (ok, fail + 1))
    sys.exit(1)
crlf = "\r\n" in S


def nl(t):
    t = t.replace("\r\n", "\n")
    return t.replace("\n", "\r\n") if crlf else t


# ── [1] le groupe R7, en queue apres R6 ──────────────────────────────────────
print("\n[1] le groupe R7 du patcher montage, en queue apres R6")
R7 = list(getattr(P, "R7", []))
_TAGS = [t for t, _a, _r in R7]
check("r7_quatre_sections_nommees",
      [t.split("-")[0] for t in _TAGS] == ["R7up1", "R7vm1", "R7vm2", "R7vm3"], _TAGS)
_R6 = list(getattr(P, "R6", []))
check("r7_en_queue_de_PATCHES_juste_apres_R6",
      len(R7) == 4 and len(_R6) == 7 and P.PATCHES[-4:] == R7 and P.PATCHES[-5] == _R6[-1],
      [t[0] for t in P.PATCHES[-6:]])

# Les ancres, ECRITES ICI (pas relues du patcher) : une ancre deplacee dans le
# patcher rougit ce banc au lieu de se valider elle-meme.
A_UP1 = ('uploadVideo:async e=>{try{const t=new FormData;t.append("file",e);const n=await fetch(`${Te}/videos/upload`,'
         '{method:"POST",body:t});return n.ok?await n.json():{ok:!1,error:`HTTP ${n.status}`}}')
R_UP1 = ('uploadVideo:async e=>{try{const t=new FormData;t.append("file",e);const n=await fetch(`${Te}/videos/upload`,'
         '{method:"POST",body:t});if(n.ok)return await n.json();let d="";try{const j=await n.json();'
         'd=typeof(j&&j.detail)=="string"?j.detail:""}catch(x){}return{ok:!1,error:d||`HTTP ${n.status}`}}')
A_VM1 = 'props:{model:"seedance-v1-pro",style:"cinematic",durationS:10'
A_VM2 = 'en=dzVmRates[p2.model||"seedance-v1-pro"]||[.04,60]'
A_VM3 = 'label:"Défaut ("+(mm.default||"seedance-v1-pro")+")"'
_ATT = {"R7up1": (A_UP1, R_UP1),
        "R7vm1": (A_VM1, A_VM1.replace("seedance-v1-pro", "seedance-2.5")),
        "R7vm2": (A_VM2, A_VM2.replace("seedance-v1-pro", "seedance-2.5")),
        "R7vm3": (A_VM3, A_VM3.replace("seedance-v1-pro", "seedance-2.5"))}
for _t, _a, _r in R7:
    _k = _t.split("-")[0]
    _ea, _er = _ATT.get(_k, ("", ""))
    check(f"{_k}_ancre_et_remplacement_du_patcher_sont_ceux_du_plan", _a == _ea and _r == _er, (_a[:60], _r[:60]))
    # 1/0/1 : x1 dans .bak_montage, consommee dans le bundle livre, remplacement x1
    check(f"{_k}_ancre_x1_dans_bak_x0_livre_remplacement_x1_livre",
          B.count(_a) == 1 and S.count(nl(_a)) == 0 and S.count(nl(_r)) == 1,
          (B.count(_a), S.count(nl(_a)), S.count(nl(_r))))
    # aucune autre section ne touche l'ancre (elle serait comptee deux fois)
    check(f"{_k}_ancre_touchee_par_aucune_autre_section",
          sum(1 for t2, a2, r2 in P.PATCHES if t2 != _t and (_a in a2 or a2 in _a)) == 0)

# le motif COURT de l'erreur vaut 2 dans le .bak : l'AUTRE appelant garde le sien
_COURT = 'return n.ok?await n.json():{ok:!1,error:`HTTP ${n.status}`}'
check("up1_motif_court_2_dans_bak_1_livre_l_autre_fonction_intacte",
      B.count(_COURT) == 2 and S.count(_COURT) == 1, (B.count(_COURT), S.count(_COURT)))
# plus AUCUN defaut client a seedance-v1-pro : seule la cle du tableau des tarifs reste
check("vm_seedance_v1_pro_ne_reste_que_comme_cle_de_tarif",
      B.count("seedance-v1-pro") == 4 and S.count("seedance-v1-pro") == 1
      and S.count('"seedance-v1-pro":[.124,10]') == 1, (B.count("seedance-v1-pro"), S.count("seedance-v1-pro")))

# ── [2] uploadVideo sous node ────────────────────────────────────────────────
print("\n[2] uploadVideo, extraite du bundle livre et jouee sous node (faux fetch)")
_UP_NEUF = entre(S, "uploadVideo:async", ",getCaptionPack:")
_UP_VIEUX = entre(B, "uploadVideo:async", ",getCaptionPack:")
check("up_fonction_extraite_du_livre_et_du_bak", len(_UP_NEUF) > 200 and len(_UP_VIEUX) > 200,
      (len(_UP_NEUF), len(_UP_VIEUX)))
_JS_UP = r"""
const Te="/api";
class FormData{append(){}}
var REP=null;
async function fetch(u,o){ if(REP==="reseau") throw new Error("hors ligne"); return REP; }
function rep(status, corps){ return {ok: status>=200&&status<300, status,
  json: async()=>{ if(corps===undefined) throw new SyntaxError("pas du JSON"); return corps; }}; }
const api={__FN__};
(async()=>{
  const out={};
  REP=rep(415,{detail:"Fichier vide ou illisible : a.mp4 (vide)"}); out.r415=await api.uploadVideo({name:"a.mp4"});
  REP=rep(500); out.r500=await api.uploadVideo({});
  REP=rep(200,{ok:!0,id:"v1",filename:"a.mp4"}); out.r200=await api.uploadVideo({});
  REP=rep(422,{detail:[{loc:["body","file"],msg:"field required"}]}); out.r422=await api.uploadVideo({});
  REP=rep(413,{detail:""}); out.r413=await api.uploadVideo({});
  REP="reseau"; out.rres=await api.uploadVideo({});
  console.log(JSON.stringify(out));
})().catch(e=>{console.log(JSON.stringify({erreur:String(e)}))});
"""
_d, _why = node_json("up_neuf.js", _JS_UP.replace("__FN__", _UP_NEUF))
check("up_415_rend_le_detail_du_serveur",
      (_d.get("r415") or {}) == {"ok": False, "error": "Fichier vide ou illisible : a.mp4 (vide)"}, (_d, _why))
check("up_500_sans_json_rend_HTTP_500", (_d.get("r500") or {}) == {"ok": False, "error": "HTTP 500"}, _d.get("r500"))
check("up_200_rend_le_json", (_d.get("r200") or {}) == {"ok": True, "id": "v1", "filename": "a.mp4"}, _d.get("r200"))
# detail non-chaine (liste pydantic) ou vide : on retombe sur le code, jamais « [object Object] »
check("up_422_detail_liste_retombe_sur_HTTP_422", (_d.get("r422") or {}) == {"ok": False, "error": "HTTP 422"}, _d.get("r422"))
check("up_413_detail_vide_retombe_sur_HTTP_413", (_d.get("r413") or {}) == {"ok": False, "error": "HTTP 413"}, _d.get("r413"))
check("up_erreur_reseau_inchangee", (_d.get("rres") or {}) == {"ok": False, "error": "hors ligne"}, _d.get("rres"))
_v, _whyv = node_json("up_vieux.js", _JS_UP.replace("__FN__", _UP_VIEUX))
check("temoin_up_l_ancienne_fonction_du_bak_ne_disait_que_HTTP_415",
      (_v.get("r415") or {}) == {"ok": False, "error": "HTTP 415"} and (_v.get("r200") or {}).get("id") == "v1",
      (_v, _whyv))

# ── [3] Seedance 2.5 par defaut : noeud, fusion des graphes, cout, libelle ──
print("\n[3] Seedance 2.5 par defaut dans le Studio, sous node ; les graphes enregistres gardent leur modele")


def props_seedance(s):
    """Le litteral des props par defaut du noeud Seedance (registre `Me`)."""
    blk = entre(s, 'Seedance:{cat:"gen"', "HeyGenAvatar:{")
    return entre(blk, "props:{", "}}") + "}" if blk else ""


_TS = entre(S, "function ts(e){", "function Lh(")
_TS_B = entre(B, "function ts(e){", "function Lh(")
_PR_N, _PR_V = props_seedance(S), props_seedance(B)
check("vm_fusion_ts_et_props_du_noeud_extraites",
      _TS != "" and _TS == _TS_B and _PR_N.startswith("props:{model:") and _PR_V.startswith("props:{model:"),
      (_TS[:40], _PR_N, _PR_V))
_JS_VM = r"""
__TS__
const Me={Seedance:{__PROPS__}};
const g={nodes:[
  {id:"a",type:"Seedance",props:{model:"seedance-v1-pro",durationS:5}},
  {id:"b",type:"Seedance",props:{durationS:8}},
  {id:"c",type:"Seedance",props:{model:""}},
  {id:"d",type:"Seedance"}]};
const f=ts(g);
const L=Me.Seedance;
const neuf={props:{...L.props||{}}};
console.log(JSON.stringify({a:f.nodes[0].props.model,a_d:f.nodes[0].props.durationS,b:f.nodes[1].props.model,
  b_d:f.nodes[1].props.durationS,c:f.nodes[2].props.model,d:f.nodes[3].props.model,neuf:neuf.props.model,
  entree_intacte:g.nodes[0].props.model+"|"+("model" in g.nodes[1].props)}));
"""
_d, _why = node_json("vm_neuf.js", _JS_VM.replace("__TS__", _TS).replace("__PROPS__", _PR_N))
check("vm_graphe_enregistre_en_v1_pro_garde_v1_pro", _d.get("a") == "seedance-v1-pro" and _d.get("a_d") == 5, (_d, _why))
check("vm_prop_absente_prend_le_defaut_2_5", _d.get("b") == "seedance-2.5" and _d.get("b_d") == 8
      and _d.get("d") == "seedance-2.5", _d)
check("vm_modele_vide_enregistre_reste_vide_donc_le_defaut_serveur", _d.get("c") == "", _d.get("c"))
check("vm_noeud_neuf_pose_seedance_2_5", _d.get("neuf") == "seedance-2.5", _d.get("neuf"))
check("vm_la_fusion_ne_modifie_pas_le_graphe_d_entree", _d.get("entree_intacte") == "seedance-v1-pro|false",
      _d.get("entree_intacte"))
_v, _whyv = node_json("vm_vieux.js", _JS_VM.replace("__TS__", _TS_B).replace("__PROPS__", _PR_V))
check("temoin_vm_le_bak_posait_v1_pro_sur_les_props_absentes_et_les_noeuds_neufs",
      _v.get("b") == "seedance-v1-pro" and _v.get("neuf") == "seedance-v1-pro" and _v.get("a") == "seedance-v1-pro", (_v, _whyv))

# dzVmCost : le repli d'un noeud sans modele = tarif 2.5 a 720p (0,473 $/s) -- meme valeur que le backend (T5)
_COST = entre(S, "var dzVmRates=", "function DzVideoModelSel(")
_COST_B = entre(B, "var dzVmRates=", "function DzVideoModelSel(")
_JS_COST = r"""
__C__
console.log(JSON.stringify({vide:dzVmCost({props:{}}),vide_str:dzVmCost({props:{model:""}}),sans_props:dzVmCost({}),
  v1:dzVmCost({props:{model:"seedance-v1-pro",durationS:10}}),s25_5:dzVmCost({props:{model:"seedance-2.5",durationS:5}}),
  inconnu:dzVmCost({props:{model:"modele-inconnu",durationS:10}}),taux25:dzVmRates["seedance-2.5"]}));
"""
_d, _why = node_json("cost_neuf.js", _JS_COST.replace("__C__", _COST))
check("vm_cout_sans_modele_au_tarif_2_5_720p_4_73_pour_10_s",
      _d.get("vide") == "$4.73" and _d.get("vide_str") == "$4.73" and _d.get("sans_props") == "$4.73"
      and _d.get("taux25") == [0.473, 30], (_d, _why))
check("vm_cout_d_un_modele_choisi_inchange", _d.get("v1") == "$1.24" and _d.get("s25_5") == "$2.36", _d)
# un id INCONNU du tableau garde son repli forfaitaire, comme le backend (pricing : modele inconnu -> forfait)
check("vm_cout_modele_inconnu_garde_son_repli_forfaitaire", _d.get("inconnu") == "$0.40", _d.get("inconnu"))
_v, _whyv = node_json("cost_vieux.js", _JS_COST.replace("__C__", _COST_B))
check("temoin_vm_le_bak_chiffrait_un_noeud_sans_modele_au_tarif_v1_pro", _v.get("vide") == "$1.24", (_v, _whyv))

# le libelle « Défaut (… » du selecteur, quand /api/video-models ne dit pas son defaut
_SEL = entre(S, "function DzVideoModelSel(", "var dzVoMult=")
_SEL_B = entre(B, "function DzVideoModelSel(", "var dzVoMult=")
_JS_SEL = r"""
var MM=null;
const x={useState:function(){return [MM,function(){}]},useEffect:function(){}};
const r={jsx:function(t,p){return {t:t,p:p}}};
const re="SELECT";
__SEL__
function lab(mm){MM=mm;var o=DzVideoModelSel({value:"",onChange:null});return o&&o.p.children.p.options[0].label}
console.log(JSON.stringify({sans:lab({models:[]}),avec:lab({models:[],default:"kling-v3-pro"}),attente:lab(null)}));
"""
_d, _why = node_json("sel_neuf.js", _JS_SEL.replace("__SEL__", _SEL))
check("vm_libelle_defaut_sans_reponse_du_serveur_dit_seedance_2_5", _d.get("sans") == "Défaut (seedance-2.5)", (_d, _why))
check("vm_libelle_defaut_suit_le_serveur_quand_il_le_dit", _d.get("avec") == "Défaut (kling-v3-pro)"
      and _d.get("attente") is None and "attente" in _d, _d)
_v, _whyv = node_json("sel_vieux.js", _JS_SEL.replace("__SEL__", _SEL_B))
check("temoin_vm_le_bak_disait_defaut_seedance_v1_pro", _v.get("sans") == "Défaut (seedance-v1-pro)", (_v, _whyv))

print(f"\n=== {ok} passed, {fail} failed ===")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
