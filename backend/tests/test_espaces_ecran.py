# -*- coding: utf-8 -*-
"""t202 (Espaces de marque E2, 13/10/2026) — les espaces à l'ÉCRAN, maillon de queue patch_bundle_dzespace.
Ce que ce banc garde :
  - le maillon est EXACTEMENT réversible : avant_dzespace(bundle livré) == le bundle de la base (e0d1ceff), octet pour
    octet ; il est idempotent ; il ne touche ni au compte de x.useState( (731), ni à « v2.8.0 » (4), ni aux CRLF ;
  - toute clé dzT("espaces.…") du bundle existe en français ET en anglais (espaces.json) et dans le dictionnaire assemblé ;
  - sous node, avec un faux fetch : activer un espace POSTe …/activate, relit /api/espaces et émet
    deepotus:espace-refresh PUIS deepotus:brand-refresh ; un refus du serveur rend son `detail` ; enregistrer le persona
    de l'écran PUTte le persona v2 de l'espace ACTIF avec `ecran` et garde ses autres champs ;
  - sous node, la logique du shell : au démarrage, Deepotus sans `ecran` garde le préréglage « deepotus » ; un espace
    avec `ecran` l'active ; un espace neuf reçoit un persona vierge À SON NOM ; savePersona et le choix d'un persona
    (dzJ) écrivent dans l'espace ; le changement d'espace relit le persona.
Rien de payé, aucun serveur : la preuve à l'écran est faite à part sur 8799.
Run (depuis backend/) : & $PY tests/test_espaces_ecran.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))
import _i18n_l1_aide as AIDE                                        # noqa: E402
import patch_bundle_dzespace as M                                   # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):                       # un contrôle qui LÈVE (aller-retour cassé) rougit, sans arrêter le banc
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{type(e).__name__}: {e}"[:200]
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "e0d1ceff"
BUNDLE = RACINE / "frontend/dist/assets/index-BEOJX8L5.js"
octets = BUNDLE.read_bytes()
s = octets.decode("utf-8")
base = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE)).stdout

print("[0] témoin et réversibilité")
check("0.1 TÉMOIN : la base n'a ni le sélecteur ni l'onglet", base and b"function DzEspaceSel(" not in base and b'"/api/espaces' not in base)
check("0.2 le bundle livré porte le maillon (marqueur x1)", s.count(M.MARKER) == 1)
CRLF, LF = chr(13) + chr(10), chr(10)
# le blob git est en LF (core.autocrlf extrait le bundle en CRLF) : on compare au blob en ramenant les CRLF
check("0.3 avant_dzespace(livré) == la base, OCTET POUR OCTET (aux CRLF d'extraction près)",
      lambda: AIDE.avant_dzespace(s).replace(CRLF, LF).encode("utf-8") == base)
check("0.4 avant_encartsia défait dzespace d'abord (la chaîne d'inverses reste complète)",
      lambda: "function DzEspaceSel(" not in AIDE.avant_encartsia(s) and "function dzImgOpts(" not in AIDE.avant_encartsia(s))
check("0.5 appliquer(base) == livré (le maillon rejoué sur la base redonne le livré)", lambda: M.appliquer(base.decode("utf-8").replace(LF, CRLF)) == s)
check("0.6 comptes figés intacts : x.useState( 731, v2.8.0 x4, DzTracks 181",
      s.count("x.useState(") == 731 and s.count("v2.8.0") == 4 and s.count("DzTracks") == 181)
check("0.7 CRLF homogènes (octets)", octets.count(b"\r\n") > 15000 and octets.count(b"\n") == octets.count(b"\r\n"))
src = (RACINE / "scripts/patch_bundle_dzespace.py").read_text(encoding="utf-8")
check("0.8 le maillon lit et écrit en OCTETS", "read_text(" not in src and "write_text(" not in src)
check("0.9 aucun .bak_dzespace laissé", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzespace")).exists())
r = subprocess.run([sys.executable, "scripts/patch_bundle_dzespace.py"], capture_output=True, cwd=str(RACINE))
check("0.10 relancer : « déjà appliqué », bundle inchangé", r.returncode == 0 and BUNDLE.read_bytes() == octets, r.stdout + r.stderr)
r = subprocess.run(["node", "--check", str(BUNDLE)], capture_output=True, text=True)
check("0.11 node --check du bundle", r.returncode == 0, r.stderr[:300])

print("\n[1] le dictionnaire")
ZONE = json.loads((RACINE / "frontend/shared/i18n/espaces.json").read_text(encoding="utf-8"))
cles = set(re.findall(r'"(espaces\.[a-z_.]+)"', s))          # dzT("…") et le ternaire archiver/desarchiver
check("1.1 au moins 18 clés espaces.* lues dans le bundle", len(cles) >= 18, str(sorted(cles)))
manq = [k for k in cles if not (ZONE.get(k, {}).get("fr") and ZONE.get(k, {}).get("en"))]
check("1.2 chacune a son français ET son anglais", not manq, str(manq))
check("1.3 aucune clé morte dans espaces.json", set(ZONE) <= cles, str(set(ZONE) - cles))
dico = (RACINE / "frontend/shared/dz-i18n-dico.js").read_text(encoding="utf-8")
check("1.4 le dictionnaire assemblé les porte (et sa copie dist est identique)",
      all(json.dumps(k) in dico for k in cles)
      and (RACINE / "frontend/dist/shared/dz-i18n-dico.js").read_bytes() == (RACINE / "frontend/shared/dz-i18n-dico.js").read_bytes())
r = subprocess.run([sys.executable, "scripts/i18n_assembler.py", "--check"], capture_output=True, cwd=str(RACINE))
check("1.5 i18n_assembler --check", r.returncode == 0, (r.stdout + r.stderr)[-200:])

print("\n[2] sous node : les aides (faux fetch)")
i = s.find("function rs(){")
RS = s[i:s.index("}}", i) + 2]
HARNAIS = r"""
var journal=[], evts=[], serveur={actif:"deepotus", espaces:{deepotus:{id:"deepotus",nom:"Deepotus"},esp_r:{id:"esp_r",nom:"Rippled"}},
  persona:{deepotus:{persona_id:"deepotus",display_name:"Deepotus",templates:[1,2]}, esp_r:{persona_id:"esp_r",display_name:"Rippled"}}};
function rep(code,j){return Promise.resolve({ok:code<400,status:code,json:function(){return Promise.resolve(j)}})}
global.fetch=function(u,o){o=o||{};journal.push((o.method||"GET")+" "+u+(o.body?" "+o.body:""));
  var m;
  if(u==="/api/espaces")return rep(200,{actif:serveur.actif,espaces:Object.values(serveur.espaces)});
  if(u==="/api/espaces/actif")return rep(200,serveur.espaces[serveur.actif]);
  if((m=u.match(/^\/api\/espaces\/([^/]+)\/activate$/))){if(m[1]==="esp_x")return rep(404,{detail:"espace inconnu : esp_x"});serveur.actif=m[1];return rep(200,{actif:m[1]})}
  if((m=u.match(/^\/api\/espaces\/([^/]+)\/persona$/))){if(o.method==="PUT"){serveur.persona[m[1]]=JSON.parse(o.body);return rep(200,serveur.persona[m[1]])}return rep(200,serveur.persona[m[1]])}
  return rep(404,{detail:"?"})};
global.window={dispatchEvent:function(e){evts.push(e.type)},addEventListener:function(t,f){(ecout[t]=ecout[t]||[]).push(f)},removeEventListener:function(){}};
var ecout={};
global.Event=function(t){this.type=t};
function Ji(){try{window.dispatchEvent(new Event("deepotus:brand-refresh"))}catch{}}
function dzT(k){return k}
var x={useReducer:function(){return[{},function(){}]},useEffect:function(f){f()}}, r={jsx:function(){},jsxs:function(){}};
var attendre=function(){return new Promise(function(f){setTimeout(f,20)})};
"""
AIDES_JS = M.AIDES
SCENARIO = r"""
(async function(){
  var out={};
  await dzEspActiver("esp_r"); await attendre();
  out.activer=journal.slice(); out.evts=evts.slice(); out.cache=dzEspCache&&dzEspCache.actif;
  journal.length=0; evts.length=0;
  try{await dzEspActiver("esp_x");out.refus="aucun"}catch(e){out.refus=e.message}
  out.evtsRefus=evts.slice();
  journal.length=0;
  dzEspPersonaEcrire({id:"rip",name:"Rip"}); await attendre();
  out.ecrit=JSON.parse(JSON.stringify(serveur.persona.esp_r)); out.ecritJ=journal.slice();
  // la logique du shell
  var etat={z:[{id:"deepotus",name:"Deepotus",handle:"@deepotus_official",tone:["slow"]},{id:"oracle",name:"Oracle"}],P:"deepotus"};
  function shell(){var z=etat.z;
    var _us=0;var x2={useState:function(i){_us++;var k=_us===1?"z":"P";if(!(k in etat))etat[k]=typeof i==="function"?i():i;
      return[etat[k],function(v){etat[k]=typeof v==="function"?v(etat[k]):v}]},useEffect:function(f){f()}};
    var x=x2, rm=etat.z;
    __SHELL__
    return{E:E,dzJ:dzJ}}
  serveur.actif="deepotus"; var h=shell(); await attendre();
  out.demarrageDeep=etat.P;out.presetDeep=JSON.stringify(etat.z[0]);
  serveur.persona.deepotus.ecran={id:"oracle",name:"Oracle"};
  ecout["deepotus:espace-refresh"].forEach(function(f){f()}); await attendre();
  out.ecranDeep=etat.P;
  serveur.actif="esp_r"; delete serveur.persona.esp_r.ecran;
  ecout["deepotus:espace-refresh"].forEach(function(f){f()}); await attendre();
  out.neuf=etat.P; out.neufNom=(etat.z.find(function(p){return p.id==="esp_r"})||{}).name;
  out.neufForme=Object.keys(etat.z.find(function(p){return p.id==="esp_r"})||{}).sort().join(",");
  h.E({id:"rip2",name:"Rip 2"}); await attendre();
  out.save=(serveur.persona.esp_r.ecran||{}).id; out.saveP=etat.P;
  h=shell(); h.dzJ("oracle"); await attendre();
  out.choix=(serveur.persona.esp_r.ecran||{}).id;
  console.log(JSON.stringify(out));
})();
"""
shell_js = M.SHELL_APRES.replace("const[z,N]=x.useState(()=>(rm||[]).slice()),[P,j]=x.useState(\"deepotus\");",
                                 "var _s1=x.useState(()=>(rm||[]).slice()),z=_s1[0],N=_s1[1],_s2=x.useState(\"deepotus\"),P=_s2[0],j=_s2[1];")
js = HARNAIS + RS + AIDES_JS + SCENARIO.replace("__SHELL__", shell_js)
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(js)
r = subprocess.run(["node", f.name], capture_output=True, text=True, encoding="utf-8")
try:
    o = json.loads(r.stdout.strip().splitlines()[-1])
except Exception:
    o = {}
    print(r.stdout[-800:], r.stderr[-1500:])
check("2.1 activer : POST …/activate puis GET /api/espaces", o.get("activer", [])[:2] == ["POST /api/espaces/esp_r/activate {}", "GET /api/espaces"], str(o.get("activer")))
check("2.2 ... puis deepotus:espace-refresh ET deepotus:brand-refresh (la carte de marque relit le kit)",
      o.get("evts") == ["deepotus:espace-refresh", "deepotus:brand-refresh"] and o.get("cache") == "esp_r", str(o.get("evts")))
check("2.3 un refus rend le `detail` du serveur, sans événement", o.get("refus") == "espace inconnu : esp_x" and o.get("evtsRefus") == [], str(o.get("refus")))
check("2.4 enregistrer le persona de l'écran : PUT dans l'espace ACTIF, `ecran` posé, les autres champs gardés",
      (o.get("ecrit") or {}).get("ecran") == {"id": "rip", "name": "Rip"} and (o.get("ecrit") or {}).get("display_name") == "Rippled"
      and any(l.startswith("PUT /api/espaces/esp_r/persona") for l in o.get("ecritJ", [])), str(o.get("ecrit")))

print("\n[3] sous node : la logique du shell")
check("3.1 démarrage sur Deepotus sans `ecran` : le préréglage « deepotus » reste actif ET intact (jamais écrasé par un vierge)",
      o.get("demarrageDeep") == "deepotus"
      and o.get("presetDeep") == '{"id":"deepotus","name":"Deepotus","handle":"@deepotus_official","tone":["slow"]}', str(o.get("presetDeep")))
check("3.2 Deepotus avec `ecran` (oracle) : relu au changement d'espace, oracle actif", o.get("ecranDeep") == "oracle", str(o))
check("3.3 espace neuf sans `ecran` : un persona vierge À SON NOM devient actif", o.get("neuf") == "esp_r" and o.get("neufNom") == "Rippled", str(o))
check("3.4 ... de la forme d'un persona d'écran (champs de rs())",
      o.get("neufForme") == "banned,catchphrase,emojiPolicy,formality,handle,id,languages,name,preferred,role,tone,voiceMode", str(o.get("neufForme")))
check("3.5 savePersona écrit aussi dans l'espace actif", o.get("save") == "rip2" and o.get("saveP") == "rip2", str(o))
check("3.6 choisir un persona (dzJ, passé aux Réglages et à l'Onboarding) l'écrit dans l'espace", o.get("choix") == "oracle", str(o))
check("3.7 les deux passages de setActivePersonaId sont branchés sur dzJ", s.count("setActivePersonaId:dzJ,savePersona:E") == 2
      and "setActivePersonaId:j," not in s)

print("\n[4] les Réglages")
check("4.1 « espaces » est dans la liste blanche ?section= (ym)", 'const ym=["diag","coffre","appareils","keys","accounts","personas","espaces",' in s)
check("4.2 l'onglet, son rendu et sa rubrique de recherche (une fois chacun)",
      s.count('{k:"espaces",l:dzT("espaces.reglages.onglet")}') == 1 and s.count('s==="espaces"&&r.jsx(DzEspaces,{})') == 1
      and s.count('espaces:dzT("espaces.reglages.onglet")};return(e&&dzRubriques') == 1)
check("4.3 le sélecteur du rail est sous la tagline, avant la version", s.count('r.jsx(DzEspaceSel,{setView:t}),r.jsxs("div",{style:{marginTop:10,') == 1)
check("4.4 les noms d'espaces et de kits ne sont pas traduits par la surcouche (data-dz-brut)",
      M.AIDES.count('"data-dz-brut":"1",children:e.nom') == 1 and M.AIDES.count('"data-dz-brut":"1",style:{fontSize:13') == 2   # nom d'espace + libellé de compte (t203)
      and '"data-dz-brut":"1",children:k.name' in M.AIDES)

print("\n[5] t203 : les comptes de diffusion de l'espace actif")
_i = M.AIDES.find("function DzComptesEspace(")
CPT = M.AIDES[_i:]
check("5.1 DzComptesEspace posé une fois, rendu une fois sous la liste des espaces (clé = l'espace actif)",
      s.count("function DzComptesEspace(") == 1 and s.count("r.jsx(DzComptesEspace,{espace:st.actif,") == 1)
check("5.2 aucun secret relu : un champ secret part VIDE (« posé » en indication), jamais f.valeur",
      'value:val!=null?val:f.secret?"":f.valeur||""' in CPT and 'placeholder:f.secret&&f.pose?dzT("espaces.comptes.pose")' in CPT)
check("5.3 une saisie vide ne change rien (seules les valeurs saisies partent)", 'if(x2!==""&&x2!=null)v[k]=x2' in CPT)
check("5.4 OAuth PAR compte (?compte=), onglet ouvert AVANT l'appel, erreur dite dans la ligne",
      '"/api/oauth/"+c.plateforme+"/start"+(c.historique?"":"?compte="+encodeURIComponent(c.id))' in CPT
      and CPT.index('w=window.open("","_blank")') < CPT.index('fetch(u,{redirect:"manual"})'))
check("5.5 tester passe le compte (sauf historique) ; supprimer en deux clics, sans window.confirm ni __dzDialogue",
      'compte:c.historique?void 0:c.id' in CPT and '"data-dz-compte-suppr":c.id' in CPT
      and "window.confirm" not in CPT and "__dzDialogue" not in CPT)
check("5.6 un compte historique n'offre ni identifiants ni suppression ici (renvoi vers Comptes connectés)",
      '!c.historique&&r.jsx("button"' in CPT and '!c.historique&&(st.suppr===c.id' in CPT and 'dzT("espaces.comptes.historique")' in CPT)
check("5.7 toujours aucun useState (731)", "x.useState(" not in M.AIDES and s.count("x.useState(") == 731)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
