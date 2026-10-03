# -*- coding: utf-8 -*-
"""Tache #76 du suivi (03/10/2026) — les transitions des gabarits A L'ECRAN du Studio, dans le bundle LIVRE.
Depuis la conversion (PR #151), un acte de gabarit sequentiel porte sa `transition` (tpl_three_act_sequential : flash
cyan). Le menu « Transition k → k+1 » du noeud Layout affichait pourtant « crossfade » tant qu'on n'y touchait pas, et
ni ce menu ni celui du noeud Concatenate ne proposaient le flash cyan.
DECISION DE L'UTILISATEUR (03/10) : « 1+2 » — le flash blanc reste, le vrai flash cyan s'ajoute.
Le fragment du panneau Layout est extrait du bundle et EXECUTE sous node.
Temoin positif : le bundle de la base (a879ce65) affiche « crossfade » par defaut et n'a pas le flash cyan.
Run (depuis backend/) : & $PY tests/test_templates_transitions_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dztre_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "a879ce65"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base affiche « crossfade » par defaut dans le panneau Layout et n'a pas le flash cyan",
      r0.returncode == 0 and b'value:(trs[ti]&&trs[ti].type)||"crossfade"' in r0.stdout and b"cyan_flash" not in r0.stdout)

DEB = '(i&&i.render_mode==="sequential"?(()=>{'
k = BUN.find(DEB)
fin = BUN.find('})():null)', k)
FRAG = BUN[k:fin + len('})():null)')] if k >= 0 and fin > 0 else ""
check("T2 le fragment du panneau Layout est trouve une fois", BUN.count(DEB) == 1 and FRAG != "")


def fonction(nom):
    k = BUN.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = BUN.find("){", k) + 1, 0, None, False
    while i < len(BUN):
        c_ = BUN[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return BUN[k:i + 1]
        i += 1
    return ""


COUCHE = fonction("dzActeTrans")
check("T3 la couche livree a dzActeTrans (une fois)", BUN.count("function dzActeTrans(") == 1)

HARNAIS = r"""
function el(t,p){return {t:t,p:p||{}}}var r={jsx:el,jsxs:el,Fragment:"frag"};
var O="Champ",Oe="Curseur",re="Menu";
function trouver(n,f,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(z){trouver(z,f,acc)});return acc}
  if(f(n))acc.push(n);var c=n.p&&n.p.children;if(c&&typeof c==="object")trouver(c,f,acc);return acc}
function brut(i,l,e){var t=function(){};return eval(FRAG)}
function panneau(i,l,e){var POSE=[];var t=function(k,v){POSE.push([k,v])};var T=eval(FRAG);
  var menus=trouver(T,function(n){return n.t==="Menu"});return {menus:menus.map(function(m){return {v:m.p.value,o:m.p.options.map(function(z){return z.value})}}),T:T,pose:POSE}}
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\nvar FRAG=" + json.dumps(FRAG) + ";\n" + HARNAIS + "\n(function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R))})()",
                 encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


TROIS = json.loads((RACINE / "backend/app/templates/tpl_three_act_sequential.json").read_text(encoding="utf-8"))
R = node("""
var L=""" + json.dumps(TROIS["regions"]) + """;
R.trois=panneau({render_mode:"sequential"},L,{scenes:3}).menus;
R.choix=panneau({render_mode:"sequential"},L,{scenes:3,transitions:[{type:"dissolve"}]}).menus.map(function(m){return m.v});
var A=[{id:"a",type:"video_slot"},{id:"t",type:"text",transition:{type:"glitch"}},{id:"b",type:"video_slot",transition:{type:"slide"}},{id:"c",type:"video_slot"}];
R.sautes=panneau({render_mode:"sequential"},A,{scenes:3}).menus.map(function(m){return m.v});
var P=panneau({render_mode:"sequential"},L,{scenes:3});P.menus.length;var mn=trouver(P.T,function(n){return n.t==="Menu"})[1];mn.p.onChange("cyan_flash");
R.pose=P.pose;R.spatial=brut({render_mode:"spatial"},L,{})===null&&brut({},L,{})===null&&brut(null,L,{})===null;
R.direct=[dzActeTrans(L,0),dzActeTrans(L,1),dzActeTrans(L,2),dzActeTrans(null,0),dzActeTrans([{type:"video_slot"},{type:"video_slot",transition:{}}],0)];
""")
check("N0 sous node : le panneau Layout s'execute", R is not None)
if R:
    check("N1 tpl_three_act_sequential : les deux menus montrent la transition DU GABARIT (cyan_flash), plus « crossfade » ; le flash cyan est propose, le blanc reste",
          [m["v"] for m in R["trois"]] == ["cyan_flash", "cyan_flash"] and all("cyan_flash" in m["o"] and "flash" in m["o"] for m in R["trois"]), str(R["trois"]))
    check("N2 un choix fait dans le Studio l'emporte sur le gabarit (1er menu), le gabarit garde le 2e", R["choix"] == ["dissolve", "cyan_flash"], str(R["choix"]))
    check("N3 les actes sont les CASES VIDEO dans l'ordre (comme la compilation du Studio) : un texte qui porte une transition ne decale rien ; sans transition, « crossfade »",
          R["sautes"] == ["slide", "crossfade"], str(R["sautes"]))
    check("N4 choisir « cyan_flash » le pose dans les transitions du noeud (meme forme que les autres choix)",
          R["pose"] == [["transitions", [None, {"type": "cyan_flash", "duration_s": 0.5}]]], str(R["pose"]))
    check("N5 dzActeTrans : acte k+1 ; sans gabarit ou sans type -> « crossfade » ; un gabarit spatial n'a pas de menu",
          R["direct"] == ["cyan_flash", "cyan_flash", "crossfade", "crossfade", "crossfade"] and R["spatial"], str(R["direct"]))

check("C1 le noeud Concatenate propose aussi le flash cyan (meme moteur cote serveur), apres le flash blanc",
      BUN.count('options:["crossfade","cut","fadeblack","glitch","slide","flash","cyan_flash"]') == 1
      and 'options:["crossfade","cut","fadeblack","glitch","slide","flash"]' not in BUN)
check("T4 aucun prompt/alert/confirm natif ; la chaine tient (DzTracks 178, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      "window.prompt(" not in COUCHE and "alert(" not in COUCHE and BUN.count("DzTracks") == 178
      and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2 and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
