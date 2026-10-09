# -*- coding: utf-8 -*-
"""t117 — PLUSIEURS SÉQUENCES, l'écran. Banc-miroir de texte (le patron du dépôt pour un front vanilla, voir
test_etabli_canevas) : il épingle que chaque porte « V1 seulement » est LEVÉE pour toute piste vidéo — plein cadre et
incrustation, décision de l'utilisateur du 06/10 — dans la SOURCE de la couche (frontend/patches/son-vfx-montage.js,
montage.js) ET dans le bundle servi (les couches y sont réinjectées par scripts/refresh_layer.py : le bloc du bundle
doit être la source à l'octet), et que les titres disent la vérité. Ce qu'il ne prouve pas — que la page se rend —
a été vu à l'écran le 06/10 (preuve du commit : losange sur V2, vitesse 200 %, fondu dans l'aperçu rendu, fondu J1).
Témoin positif : la base (fc052852) a les portes fermées.
Run (depuis backend/) : & $PY tests/test_montage_sequences_ecran.py"""
import pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
BASE = "fc052852"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def lire(rel):
    return (RACINE / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")


def base(rel):
    return subprocess.run(["git", "show", f"{BASE}:{rel}"], capture_output=True, cwd=str(RACINE)).stdout.decode(
        "utf-8").replace("\r\n", "\n")


SV, MJ = "frontend/patches/son-vfx-montage.js", "frontend/patches/montage.js"
# t144 : la couche passe par dzT (traduction L4) ; le banc exécute/lit son texte français d'avant la traduction
# (test_i18n_l4 garantit qu'elle se défait exactement)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as AIDE  # noqa: E402
sv, mj, sv0, mj0 = AIDE.couche_avant_i18n_l4(lire(SV), "sonvfx"), lire(MJ), base(SV), base(MJ)
bundle = AIDE.avant_i18n_l4(lire("frontend/dist/assets/index-BEOJX8L5.js"))

# chaque porte : (nom, ancienne forme — présente dans la base, nouvelle forme — présente dans la source)
PORTES = [
    ("jonctions par piste", 'function svmV1Junctions(cs){\n  var vs=cs.filter(function(c){return c.tr==="v1"})',
     'function svmV1Junctions(cs,tid){\n  tid=tid||"v1";\n  var vs=cs.filter(function(c){return c.tr===tid})'),
    ("voisin de gauche sur la même piste", 'if(k.tr!=="v1"||k.id===c.id||k.start>=c.start)return;',
     'if(k.tr!==c.tr||k.id===c.id||k.start>=c.start)return;'),
    ("losanges dans toute piste vidéo", 'tr.id==="v1"?svmV1Junctions(clips).map(',
     'trackKind(tr.id)==="video"?svmV1Junctions(clips,tr.id).map('),
    ("inspecteur de transition", 'if(!sel||sel.tr!=="v1")return null;\n    var left=svmLeftNeighbor(clips,sel);',
     'if(!sel||trackKind(sel.tr)!=="video")return null;'),
    ("Alt+T", 'k.id===selRef.current&&k.tr==="v1"})[0];if(!dzTc)',
     'k.id===selRef.current&&trackKind(k.tr)==="video"})[0];if(!dzTc)'),
    ("vitesse : le setter", 'if(!c||c.tr!=="v1"||!c.src||!c.src.job_id)return;',
     'if(!c||trackKind(c.tr)!=="video"||!c.src||!c.src.job_id)return;'),
    ("vitesse : le verrou de SA piste", 'if(trackStRef.current.v1&&trackStRef.current.v1.l){\n      fireNote("Piste V1 verrouillée — vitesse bloquée.")',
     'if(trackStRef.current[c.tr]&&trackStRef.current[c.tr].l){\n      fireNote("Piste "+String(c.tr).toUpperCase()+" verrouillée — vitesse bloquée.")'),
    ("vitesse : l'inspecteur", 'var v1spd=!!(sel&&sel.tr==="v1"&&sel.src&&sel.src.job_id);',
     'var v1spd=!!(sel&&trackKind(sel.tr)==="video"&&sel.src&&sel.src.job_id);'),
    ("vitesse : le menu de clip", 'off:!v1||!c.src||!c.src.job_id,run:function(){svmSetV1Speed(id,v)}',
     'off:!vid||!c.src||!c.src.job_id,run:function(){svmSetV1Speed(id,v)}'),
    ("vitesse : la charge utile", 'if(c.tr==="v1"&&c.src&&c.src.job_id&&typeof c.speed==="number"&&c.speed>0&&\n           Math.abs(c.speed-1)>1e-6)o.speed=',
     'if(trackKind(c.tr)==="video"&&c.src&&c.src.job_id&&typeof c.speed==="number"&&c.speed>0&&\n           Math.abs(c.speed-1)>1e-6)o.speed='),
    ("vitesse : la puce de désynchro du jumeau", 'if(c.tr==="v1"&&c.src&&c.src.job_id&&typeof c.speed==="number"&&\n       c.speed>0&&Math.abs(c.speed-1)>1e-6)\n      v1SpeedJobs[',
     'if(trackKind(c.tr)==="video"&&c.src&&c.src.job_id&&typeof c.speed==="number"&&\n       c.speed>0&&Math.abs(c.speed-1)>1e-6)\n      v1SpeedJobs['),
    ("vitesse : l'aperçu en direct d'un plan haut", 'var wt2=(k.srcIn||0)+(t-k.start);\n        if(run){\n          if(el.playbackRate!==s)el.playbackRate=s;',
     'var wt2=(k.srcIn||0)+(t-k.start)*kSpd;\n        if(run){\n          if(el.playbackRate!==s*kSpd)el.playbackRate=s*kSpd;'),
    ("restauration : la transition gardée", 'if(c.tr==="v1"){nk.transition=c.transition||"cut";',
     'if(String(c.tr||"").charAt(0)==="v"){nk.transition=c.transition||"cut";'),
]
for nom, ancien, neuf in PORTES:
    check(f"P_{nom} — fermée dans la base, levée dans la source, servie par le bundle",
          sv0.count(ancien) == 1 and sv.count(ancien) == 0 and sv.count(neuf) == 1 and bundle.count(neuf) == 1,
          (sv0.count(ancien), sv.count(ancien), sv.count(neuf), bundle.count(neuf)))

# J1 : les fondus du clip d'ajustement — champs, setter, charge utile
check("J1_la_charge_utile_joint_les_fondus_d_un_clip_d_ajustement_seulement_s_ils_existent",
      'if(c.kind==="adjust"){if(c.fade_in)o.fade_in=c.fade_in;if(c.fade_out)o.fade_out=c.fade_out}' in sv
      and sv0.count('if(c.kind==="adjust"){if(c.fade_in)') == 0)
check("J1_l_inspecteur_d_ajustement_porte_les_deux_champs",
      'sel.kind==="adjust"?dzAjFadeRow(sel):null,' in sv and 'champ("in","Fondu d\'entrée"),champ("out","Fondu de sortie")' in sv)
_fn = sv[sv.find("  function dzAjFade(which,v){"):sv.find("  function dzAjFadeRow(c){")]
check("J1_le_setter_borne_a_la_moitie_du_clip_retire_le_champ_a_zero_et_pousse_l_historique",
      "var half=Math.max(0,(c.end-c.start)/2);" in _fn and "Math.min(half,Math.max(0,Number(v)||0))" in _fn
      and "if(v>0)nk[key]=v;else delete nk[key];" in _fn and "pushHistory();" in _fn and "setDirty(!0)" in _fn
      and 'if(!c||c.kind!=="adjust")return;' in _fn, _fn[:120])
check("J1_aucun_hook_ajoute_aucun_dialogue_natif",
      # t119 (07/10/2026) : + 2 hooks hors t117 — `dzScenesRef` et l'effet qui découpe un épisode posé
      len(re.findall(r"x\.use(State|Ref|Effect|Memo|Callback)\(", sv)) == len(re.findall(r"x\.use(State|Ref|Effect|Memo|Callback)\(", sv0)) + 2
      and sv.count("var dzScenesRef=x.useRef(null);") == 1
      and not re.search(r"\b(alert|confirm|prompt)\(", _fn + sv[sv.find("  function dzAjFadeRow(c){"):sv.find("  function vfxLegacySection(){")]))

# les titres disent la vérité : l'écart est levé, et l'avertissement faux sur les effets des pistes hautes est retiré
check("T_le_titre_de_piste_video_ne_declare_plus_l_ecart",
      "V1 reste la séquence maîtresse (durée, \"+\n      \"transitions, vitesse, effets)." in mj0
      and "ses plans ont leurs transitions, leur vitesse et \"+" in mj and "transitions, vitesse, effets)." not in mj
      # la NOTE d'ajout de piste (dzmAddDit) répétait l'écart : elle suit aussi
      and "leurs effets, comme V1 ; V1 reste la séquence maîtresse (durée)." in mj
      and "opacité), muette ; ses plans ont aussi transitions, vitesse et effets." in mj)
check("T_l_avertissement_faux_sur_les_effets_des_pistes_hautes_est_retire",
      "ATTENTION — mesuré : le rendu n'emporte pas les " in mj0 and "ATTENTION — mesuré" not in mj
      and 'var hors="";' in mj)

# la couche servie EST la source (refresh_layer) — mêmes marqueurs que l'outil
for tag, rel, src in (("SONVFX", SV, sv), ("MONTAGE", MJ, mj)):
    a, b = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    blk = bundle[bundle.find(a) + len(a):bundle.find(b)] if a in bundle and b in bundle else ""
    check(f"C_{tag}_le_bloc_du_bundle_est_la_source", blk and blk.strip() == src.strip(), (len(blk), len(src)))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
