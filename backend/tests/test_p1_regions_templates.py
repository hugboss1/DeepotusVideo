# -*- coding: utf-8 -*-
"""P1 #4 (28/09/2026) — RECOPIE FILTRANTE DES REGIONS D'UN TEMPLATE.

L'editeur de templates (hm) recopiait les regions champ par champ :
  - au CHARGEMENT `const H=(E.regions||[]).map(F=>({id:F.id,…}))` : `fit`,
    `audio_volume`, `act`, `transition`, `length_s`, `effects`… (mesure sur
    les neuf gabarits livres) n'entraient jamais dans l'etat de l'editeur ;
  - a l'ENREGISTREMENT `Object.assign({},O0,{…}, E.effect!=null?{effect}:{}…)` :
    seuls les champs listes et NON NULS de l'etat partaient ; la region
    d'origine O0 revenait pour tout le reste.
Mesure qui compte : l'aller-retour d'un gabarit INTACT etait deja fidele
(O0 le sauve — controle 1.x, temoin compris) ; la perte est celle d'une
EDITION : decocher « Pulse » d'un badge pose effect:null, que l'ancien
enregistrement ignorait -> O0.effect="pulse" revenait (defaut VISIBLE) ; et
tout champ hors liste edite dans l'etat (masque, text_fit… du plan
templates T7) disparaissait au Save.
Correctif (groupe P1 du maillon montage, P1rg1 et P1rg2, dessin P1-P3 du plan
2026-09-03-plan-templates) : chargement par Object.assign({},F,{…}) ;
enregistrement de tout champ de l'etat sauf `_disp` et les undefined (les
null PASSENT) avant les champs listes d'origine.
METHODE : les deux expressions (chargement, enregistrement) sont EXTRAITES
du bundle livre et du .bak_montage (temoin) et EXECUTEES sous node sur les
gabarits de backend/app/templates. Faute n6 : details par _d().
Run : & $PY tests/test_p1_regions_templates.py   (depuis backend/)
"""
import glob, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
import patch_bundle_montage as P                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:400]
    except Exception as e:                                   # pragma: no cover
        return f"(detail illisible : {e})"


BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
s = BUNDLE.read_bytes().decode("utf-8")
bak = BAK.read_bytes().decode("utf-8") if BAK.is_file() else ""
NODE = shutil.which("node")
TPLS = {pathlib.Path(f).stem: json.load(open(f, encoding="utf-8"))
        for f in sorted(glob.glob(str(BACKEND / "app" / "templates" / "*.json")))}


def _exprs(txt):
    """(chargement, enregistrement) extraits du composant hm."""
    h = txt.find("function hm({pickedT:e,onSaved:t}){")
    i = txt.find("const H=", h)
    j = txt.find(";u(H)", i)
    k = txt.find("regions:d.map(", h)
    m = txt.find(')};try{const E=await fetch("/api/layout-templates"', k)
    if min(h, i, j, k, m) < 0:
        return None, None
    return txt[i + len("const H="):j], txt[k + len("regions:d.map("):m]


def _run(txt, scenario_js):
    ch, en = _exprs(txt)
    if not ch or not NODE:
        return None, "expressions introuvables"
    js = ("function load(E){return " + ch + "}\nfunction save(a,d){return d.map(" + en + ")}\n"
          "function canon(v){if(Array.isArray(v))return v.map(canon);if(v&&typeof v==='object'){var o={};"
          "Object.keys(v).sort().forEach(function(k){o[k]=canon(v[k])});return o}return v}\n"
          "var TPLS=" + json.dumps(TPLS) + ";\n" + scenario_js)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
    try:
        r = subprocess.run([NODE, f.name], capture_output=True, text=True, encoding="utf-8")
    finally:
        os.unlink(f.name)
    try:
        return json.loads(r.stdout), r.stderr
    except Exception:
        return None, r.stderr[-400:] + r.stdout[:200]


SCEN = r"""
var out={};
// 1. aller-retour d'un gabarit INTACT : chaque champ d'origine garde sa valeur ; l'enregistrement complet est rendu
//    pour comparer ANCIEN et NOUVEAU (les defauts des champs listes -- slot_name=id, geometrie 0/0/200/200 -- sont
//    un comportement anterieur, mesure le 28/09, hors perimetre)
out.intact={};out.sauve={};Object.keys(TPLS).forEach(function(k){var a=TPLS[k],sv=save(a,load(a));
  out.intact[k]=a.regions.every(function(r,i){return Object.keys(r).every(function(f){
    return JSON.stringify(canon(r[f]))===JSON.stringify(canon(sv[i][f]))})});
  out.sauve[k]=JSON.stringify(canon(sv))});
// 2. chargement : les champs hors liste entrent dans l'etat de l'editeur
var nr=TPLS.tpl_news_reel,dl=load(nr),r0=nr.regions.filter(function(r){return r.fit!==undefined})[0];
out.charge=r0?{fit:dl.filter(function(r){return r.id===r0.id})[0].fit,attendu:r0.fit,
  audio:dl.filter(function(r){return r.id===r0.id})[0].audio_volume}:null;
// 3. decocher Pulse d'un badge (effect:null) puis Save : doit rester decoche
var ab={id:"t",name:"t",canvas:{width:1080,height:1920},regions:[{id:"b1",type:"badge",x:10,y:10,width:200,height:60,
  badge_kind:"live",text:"LIVE",effect:"pulse",effect_speed:1.2,z_index:3}]};
var db=load(ab).map(function(r){return r.id==="b1"?Object.assign({},r,{effect:null}):r});
var sb=save(ab,db)[0];out.pulse={effect:sb.effect,speed:sb.effect_speed};
// 4. un champ hors liste EDITE dans l'etat (masque du plan T7) part au Save
var dm=load(ab).map(function(r){return Object.assign({},r,{mask:{shape:"circle"},text_fit:"shrink"})});
var sm=save(ab,dm)[0];out.edite={mask:sm.mask||null,text_fit:sm.text_fit||null};
// 5. jamais la cle privee _disp ; pas de cle undefined ajoutee
var s5=save(ab,load(ab))[0];out.prive={disp:("_disp" in s5),undef:Object.keys(s5).filter(function(k){return s5[k]===undefined})};
// 6. une region AJOUTEE dans l'editeur (sans O0) garde ses champs, sans _disp
var dn=load(ab).concat([{id:"tx_1",type:"text",x:5.4,y:6.6,width:100,height:40,text:"Hi",color:"#fff",size:30,
  font:"Space Grotesk",align:"center",text_fit:"wrap",_disp:"var(--ink-strong)",z_index:4}]);
var sn=save(ab,dn)[1];out.neuve={x:sn.x,y:sn.y,fit:sn.text_fit||null,disp:("_disp" in sn)};
process.stdout.write(JSON.stringify(out));
"""

print("\n[0] preconditions")
check("0.1 .bak_montage present, node present, neuf gabarits livres", bool(bak) and bool(NODE) and len(TPLS) == 9, _d(len(TPLS)))
_ch0, _en0 = _exprs(bak)
check("0.2 temoin : le .bak recopie champ par champ (litteral au chargement, champs listes non nuls a l'enregistrement)",
      bool(_ch0) and _ch0.startswith("(E.regions||[]).map(F=>({id:F.id,") and "E.effect!=null?{effect:E.effect}:{}" in (_en0 or ""), "")

OLD, e0 = _run(bak, SCEN)
NEW, e1 = _run(s, SCEN)
check("0.3 les deux etats s'executent", OLD is not None and NEW is not None, _d(e0, e1))
OLD, NEW = OLD or {}, NEW or {}

print("\n[1] aller-retour d'un gabarit intact (non-regression)")
check("1.1 temoin mesure : l'ANCIEN aller-retour gardait deja chaque champ d'origine (O0 le sauvait)",
      len(OLD.get("intact", {})) == 9 and all(OLD["intact"].values()), _d(OLD.get("intact")))
check("1.2 le NOUVEL aller-retour garde chaque champ d'origine sur les neuf gabarits",
      len(NEW.get("intact", {})) == 9 and all(NEW["intact"].values()), _d(NEW.get("intact")))
check("1.3 gabarit intact : le NOUVEL enregistrement est IDENTIQUE a l'ancien sur les neuf (aucune regression)",
      len(NEW.get("sauve", {})) == 9 and NEW.get("sauve") == OLD.get("sauve"),
      _d([k for k in NEW.get("sauve", {}) if NEW["sauve"][k] != OLD.get("sauve", {}).get(k)]))

print("\n[2] chargement transparent")
check("2.1 temoin : l'ancien chargement perdait fit / audio_volume", (OLD.get("charge") or {}).get("fit") is None
      and (OLD.get("charge") or {}).get("attendu") is not None, _d(OLD.get("charge")))
check("2.2 le chargement garde fit et audio_volume dans l'etat de l'editeur",
      (NEW.get("charge") or {}).get("fit") == (NEW.get("charge") or {}).get("attendu") is not None
      and (NEW.get("charge") or {}).get("audio") is not None, _d(NEW.get("charge")))

print("\n[3] enregistrement transparent (le defaut visible)")
check("3.1 temoin : decocher Pulse ne tenait pas (l'ancien Save rendait effect='pulse')",
      (OLD.get("pulse") or {}).get("effect") == "pulse", _d(OLD.get("pulse")))
check("3.2 decocher Pulse tient : effect null enregistre, effect_speed d'origine garde",
      "pulse" in NEW and NEW["pulse"].get("effect") is None and NEW["pulse"].get("speed") == 1.2, _d(NEW.get("pulse")))
check("3.3 temoin : un champ hors liste edite (mask, text_fit) disparaissait au Save",
      OLD.get("edite") == {"mask": None, "text_fit": None}, _d(OLD.get("edite")))
check("3.4 un champ hors liste edite part au Save", NEW.get("edite") == {"mask": {"shape": "circle"}, "text_fit": "shrink"},
      _d(NEW.get("edite")))
check("3.5 jamais _disp, aucune cle undefined", NEW.get("prive") == {"disp": False, "undef": []}, _d(NEW.get("prive")))
check("3.6 region ajoutee : x/y arrondis, champ neuf garde, sans _disp",
      NEW.get("neuve") == {"x": 5, "y": 7, "fit": "wrap", "disp": False}, _d(NEW.get("neuve")))

print("\n[4] groupe P1 du maillon et syntaxe")
_P1 = [t for t, _a, _r in getattr(P, "P1", [])]
check("4.1 P1rg1, P1rg2 dans le groupe P1 (apres P1tp4), groupe en QUEUE de PATCHES", _P1[9:11] == ["P1rg1-chargement-des-regions-transparent",
      "P1rg2-enregistrement-des-regions-transparent"]
      and [t for t, _a, _r in P.PATCHES[-len(_P1):]] == _P1, _d(_P1[-4:]))
_nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("4.2 le bundle ENTIER passe node --check", _nc is not None and _nc.returncode == 0, _d(_nc.stderr[-300:] if _nc else ""))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
