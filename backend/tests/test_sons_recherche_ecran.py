# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T13, D3c) — le tiroir Sons cherche par DESCRIPTION et montre les VOISINS, dans le bundle
LIVRÉ : le bloc SFXSTUDIO est exécuté sous node avec le harnais du banc T101 (repris tel quel de
test_sons_tiroir_ecran.py : moteur de hooks, fetch / Audio / minuteries en doublures). Vérifié :
  · service ABSENT : ✧ désactivé, l'infobulle donne la RAISON du backend ; aucun « ≈ » tant que rien n'est indexé ;
  · service PRÊT : ✧ actif avec le compte indexé ; le mode « décrire » change le champ, montre « indexer » et
    « tout réindexer » (force) ; Entrée LANCE la recherche (et ne saute pas à la première rangée) ; les rangées
    du résultat sont les rangées de la liste PLUS le score ; un son indexé mais effacé est DIT, pas fantôme ;
    « retour à la liste » restaure ;
  · « ≈ » sur une rangée : GET /audio/similar/<nom>, panneau « Proches de » ; vide -> la raison.
Témoin positif : le bundle de la base (d7eaf665) n'a ni ✧ ni « ≈ ».
Run (depuis backend/) : & $PY tests/test_sons_recherche_ecran.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzsonsrech_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "d7eaf665"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T0 témoin : la base a le tiroir mais ni la recherche par description ni les voisins",
      r0.returncode == 0 and b"const SvxDrawer=" in r0.stdout and b"svx-sembtn" not in r0.stdout
      and b"/api/audio/similar/" not in r0.stdout)
DEB, FIN = "/*__DZ_SFXSTUDIO_BEGIN__*/", "/*__DZ_SFXSTUDIO_END__*/"
check("T1 un seul bloc SFXSTUDIO", BUN.count(DEB) == 1 and BUN.count(FIN) == 1)
BLOC = BUN.split(DEB, 1)[1].split(FIN, 1)[0].replace("\r\n", "\n")
src101 = (_ICI / "test_sons_tiroir_ecran.py").read_text(encoding="utf-8")
m = re.search(r'HARNAIS = r"""(.*?)"""', src101, re.S)
check("T2 le harnais du banc T101 est repris tel quel", m is not None)
HARNAIS = m.group(1) if m else ""

MOTEUR = r"""
var PROPS={open:true};
function render(){hi=0;PEND=[];var t=window.DzSfx.Drawer(PROPS);
  PEND.forEach(function(pe){var o=H[pe[0]];if(o.c)o.c();var c=pe[1]();o.c=typeof c==="function"?c:null});return t}
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
function txt(n){if(n==null||n===false||n===true)return "";if(typeof n!=="object")return String(n);return kids(n).map(txt).join("")}
function cls(t,c){return tout(t).filter(function(n){return typeof n.p.className==="string"&&(" "+n.p.className+" ").indexOf(" "+c+" ")>=0})}
function rangees(t){return tout(t).filter(function(n){return n.p["data-svx-item"]})}
function rangee(t,nom){return rangees(t).filter(function(n){return n.p["data-svx-item"]===nom})[0]}
function btn(t,label){return tout(t).filter(function(n){return n.t==="button"&&txt(n).trim()===label})[0]}
function stop(){return {stopPropagation:function(){},preventDefault:function(){},defaultPrevented:false}}
async function tick(){for(var i=0;i<12;i++)await new Promise(function(res){setImmediate(res)})}
async function stable(){var t;for(var i=0;i<4;i++){t=render();await tick()}return render()}
function lance(){return CALLS.filter(function(c){return c.u.indexOf("/api/audio/search")===0||c.u.indexOf("/api/audio/similar")===0})
  .map(function(c){return c.m+" "+c.u+(c.b?" "+JSON.stringify(c.b):"")})}
var OUT={};
(async function(){
  REP["GET /api/audio"]={st:200,js:{audio:[
    {name:"porte.mp3",url:"/api/audio/porte.mp3",size_kb:50,mtime:300},
    {name:"pluie.mp3",url:"/api/audio/pluie.mp3",size_kb:80,mtime:200},
    {name:"boom.mp3",url:"/api/audio/boom.mp3",size_kb:40,mtime:100}]}};
  REP["GET /api/audio/meta"]={st:200,js:{meta:{"porte.mp3":{kind:"sfx"},"pluie.mp3":{kind:"sfx"},"boom.mp3":{kind:"sfx"}}}};
  [["porte.mp3",1],["pluie.mp3",4],["boom.mp3",1]].forEach(function(p){SVM_WAVES.set("a:"+p[0],{st:"ok",dur:p[1],peaks:[0.5]})});
  // ── 1. service ABSENT ──
  REP["GET /api/audio/search/status"]={st:200,js:{ready:false,indexed:0,provider:"",hint:"Recherche par description indisponible : lance Clapbox"}};
  var t=await stable();
  var sb=cls(t,"svx-sembtn")[0];
  OUT.absent={disabled:sb&&sb.p.disabled,title:sb&&sb.p.title,proches:tout(t).filter(function(n){return n.p.title&&/proches/.test(n.p.title)}).length,
    indexer:!!btn(t,"indexer")};
  // ── 2. service PRÊT ──
  REP["GET /api/audio/search/status"]={st:200,js:{ready:true,indexed:3,provider:"clapbox",hint:""}};
  H=[];t=await stable();
  sb=cls(t,"svx-sembtn")[0];
  OUT.pret={disabled:sb.p.disabled,title:sb.p.title,proches:rangees(t).map(function(rg){return tout(rg).filter(function(n){return txt(n)==="≈"}).length})};
  sb.p.onClick();t=render();
  var champ=tout(t).filter(function(n){return n.p.className==="svx-searchin"})[0];
  OUT.mode={placeholder:champ.p.placeholder,indexer:!!btn(t,"indexer"),tout:!!btn(t,"tout réindexer")};
  champ.p.onChange({target:{value:"une porte qui grince"}});t=render();
  REP["GET /api/audio/search"]={st:200,js:{query:"x",items:[
    {name:"porte.mp3",url:"/api/audio/porte.mp3",score:0.9312,kind:"sfx",tags:[]},
    {name:"efface.mp3",url:"/api/audio/efface.mp3",score:0.5,kind:"sfx",tags:[]},
    {name:"boom.mp3",url:"/api/audio/boom.mp3",score:0.2101,kind:"sfx",tags:[]}]}};
  champ=tout(t).filter(function(n){return n.p.className==="svx-searchin"})[0];
  champ.p.ref.current=champ;champ.tagName="INPUT";
  CALLS.length=0;
  var foc=0;var vrai=t.p.onKeyDown;
  t.p.onKeyDown({key:"Enter",target:champ,preventDefault:function(){},stopPropagation:function(){}});await tick();t=await stable();
  OUT.recherche={appels:lance(),tete:txt(cls(t,"svx-semhead")[0]),scores:cls(t,"svx-semscore").map(txt),
    rangees:cls(t,"svx-semrow").map(function(rw){var it=rangees(rw)[0];return it&&it.p["data-svx-item"]}),
    efface:txt(t).indexOf("« efface.mp3 » n'est plus dans la bibliothèque")>=0};
  btn(t,"retour à la liste").p.onClick();t=render();
  OUT.retour={panneau:cls(t,"svx-sem").length,liste:rangees(t).map(function(n){return n.p["data-svx-item"]})};
  // indexer / tout réindexer
  REP["POST /api/audio/search/index"]={st:200,js:{indexed:1,skipped:2,dropped:["vieux.mp3"],total:3}};
  CALLS.length=0;btn(t,"indexer").p.onClick();await tick();t=await stable();
  btn(t,"tout réindexer").p.onClick();await tick();t=await stable();
  OUT.index={appels:lance(),note:txt(cls(t,"svx-note")[cls(t,"svx-note").length-1])};
  // ≈ : voisins
  REP["GET /api/audio/similar/pluie.mp3"]={st:200,js:{name:"pluie.mp3",items:[{name:"boom.mp3",url:"/api/audio/boom.mp3",score:0.7,kind:"sfx",tags:[]}]}};
  CALLS.length=0;
  var pr=tout(rangee(t,"pluie.mp3")).filter(function(n){return txt(n)==="≈"})[0];
  pr.p.onClick(stop());await tick();t=await stable();
  OUT.voisins={appels:lance(),tete:txt(cls(t,"svx-semhead")[0]),rangees:cls(t,"svx-semrow").map(function(rw){var it=rangees(rw)[0];return it&&it.p["data-svx-item"]})};
  REP["GET /api/audio/similar/boom.mp3"]={st:200,js:{name:"boom.mp3",items:[]}};
  btn(t,"retour à la liste").p.onClick();t=render();
  tout(rangee(t,"boom.mp3")).filter(function(n){return txt(n)==="≈"})[0].p.onClick(stop());await tick();t=await stable();
  OUT.voisinsVide=txt(t).indexOf("Aucun voisin")>=0;
  // hors mode « décrire » : Entrée garde son rôle (aller à la 1re rangée), aucune recherche
  btn(t,"retour à la liste").p.onClick();t=render();
  cls(t,"svx-sembtn")[0].p.onClick();t=render();
  champ=tout(t).filter(function(n){return n.p.className==="svx-searchin"})[0];champ.p.ref.current=champ;champ.tagName="INPUT";
  CALLS.length=0;
  t.p.onKeyDown({key:"Enter",target:champ,preventDefault:function(){},stopPropagation:function(){}});await tick();
  OUT.horsMode={appels:lance(),placeholder:champ.p.placeholder};
  console.log(JSON.stringify(OUT));
})().catch(function(e){console.log(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""

js = _TMP / "tiroir_rech.js"
js.write_text(HARNAIS + BLOC + MOTEUR, encoding="utf-8")
p = subprocess.run(["node", str(js)], capture_output=True, text=True, encoding="utf-8", timeout=60)
ligne = (p.stdout.strip().splitlines() or ["{}"])[-1]
try:
    OUT = json.loads(ligne)
except Exception:
    OUT = {"erreur": p.stdout[-400:] + p.stderr[-800:]}
check("T3 le tiroir livré s'exécute", "erreur" not in OUT, str(OUT.get("erreur", ""))[:800])

if "erreur" not in OUT:
    a = OUT["absent"]
    check("A1 service absent : ✧ désactivé, l'infobulle porte la RAISON du backend",
          a["disabled"] is True and "Clapbox" in (a["title"] or ""), str(a))
    check("A2 rien d'indexé : aucun « ≈ », pas d'« indexer »", a["proches"] == 0 and a["indexer"] is False, str(a))
    pr = OUT["pret"]
    check("P1 service prêt : ✧ actif, compte indexé dans l'infobulle", pr["disabled"] is False and "3 sons indexés" in pr["title"], str(pr))
    check("P2 un « ≈ » par rangée dès qu'il y a un index", pr["proches"] == [1, 1, 1], str(pr["proches"]))
    md = OUT["mode"]
    check("P3 le mode « décrire » change le champ et montre indexer / tout réindexer",
          md["placeholder"].startswith("Décrire le son cherché") and md["indexer"] and md["tout"], str(md))
    rc = OUT["recherche"]
    check("P4 Entrée LANCE la recherche par description (k=24, texte encodé)",
          rc["appels"] == ["GET /api/audio/search?k=24&q=une%20porte%20qui%20grince"], str(rc["appels"]))
    check("P5 les rangées du résultat = rangées de la liste + score, dans l'ordre du serveur",
          rc["rangees"] == ["porte.mp3", "boom.mp3"] and rc["scores"] == ["0.93", "0.21"]
          and rc["tete"].startswith("Décrit : « une porte qui grince »"), str(rc))
    check("P6 un son indexé mais effacé est DIT, pas une rangée fantôme", rc["efface"])
    check("P7 « retour à la liste » restaure la liste", OUT["retour"]["panneau"] == 0
          and OUT["retour"]["liste"] == ["porte.mp3", "pluie.mp3", "boom.mp3"], str(OUT["retour"]))
    ix = OUT["index"]
    check("P8 indexer = POST {} ; tout réindexer = POST {force:true}",
          ix["appels"] == ['POST /api/audio/search/index {}', 'POST /api/audio/search/index {"force":true}'], str(ix["appels"]))
    check("P9 le compte rendu est dit (indexés, inchangés, retirés)", "1 son(s) indexé(s), 2 inchangé(s), 1 retiré(s)" in ix["note"], ix["note"])
    v = OUT["voisins"]
    check("V1 « ≈ » : GET /audio/similar/<nom>?k=8, panneau « Proches de »",
          v["appels"] == ["GET /api/audio/similar/pluie.mp3?k=8"] and v["tete"].startswith("Proches de « pluie.mp3 »")
          and v["rangees"] == ["boom.mp3"], str(v))
    check("V2 aucun voisin : la raison est dite", OUT["voisinsVide"])
    hm = OUT["horsMode"]
    check("H1 hors mode « décrire » : Entrée ne lance AUCUNE recherche, le champ reprend son texte d'origine",
          hm["appels"] == [] and hm["placeholder"].startswith("Rechercher"), str(hm))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
