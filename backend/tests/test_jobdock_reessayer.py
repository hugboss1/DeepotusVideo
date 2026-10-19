# -*- coding: utf-8 -*-
"""Job Dock, « Réessayer » (19/10/2026, option (a) validée par l'utilisateur) — le bouton d'un job en échec n'avait AUCUN
onClick dans le livré. Il est branché là où une relance est possible, masqué ailleurs :
  - le serveur dit comment relancer (`relance` de _job_to_dict, seulement pour un job en échec) :
      « direct » = un rendu motion code (provider animation, sortie mcode_*) dont le graphe Studio est gardé : local et
      gratuit, on rappelle POST /api/motion/code/rendre avec la même page ;
      « quick »  = une recette Quick existe : Quick rouvre prérempli, rien ne part avant « Générer » (estimation, plafond) ;
      « studio » = un graphe Studio existe : le Studio rouvre le graphe, rien ne part avant le rendu ;
      absent     = rien de quoi relancer : le bouton est masqué ;
  - le maillon de queue `dzdock` (scripts/patch_bundle_dzdock.py, APRÈS dzmotion) pose `__dzRelancer` et branche le bouton.
Sections :
  [B] serveur : _relance_de sur les cas ci-dessus, et le champ dans _job_to_dict ;
  [A] câblage dans le livré : plus de bouton inerte, la ligne du Dock porte relance / aspect / titre ;
  [F] sous node, avec les VRAIES fonctions extraites du livré (`__dzRelancer`, `Wt`, `dzMoProps`) : corps de la relance
      directe, repli sur le Studio, Quick, Studio, échec du serveur, rien sans relance ;
  [D] chaîne : sans le maillon = la base octet pour octet ; aller-retour ; comptes figés ; octets / CRLF ;
  [K] textes : clés FR ET EN dans relance.json (coque.json est écrit par i18n_l1_generer), mêmes variables,
      dictionnaire assemblé.
Run (depuis backend/) : & $PY tests/test_jobdock_reessayer.py"""
import json, pathlib, re, subprocess, sys, tempfile
from types import SimpleNamespace
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")
BASE = "bb533b9a"            # origin/main (#390 fusionnée), dzmotion en queue
INERTE = 'u&&r.jsx(K,{variant:"outline",size:"sm",icon:"dz-action-reessayer",children:dzT("commun.action.reessayer")})'

# ── [B] serveur ───────────────────────────────────────────────────────────────────────────────────────────────────
print("[B] serveur : comment relancer")


def _cas_serveur():
    from app.config import settings
    from app.api import routes as R
    from app.services import quick_recipe
    ancien = settings.OUTPUTS_FOLDER
    with tempfile.TemporaryDirectory() as d:
        settings.OUTPUTS_FOLDER = d
        try:
            (pathlib.Path(d) / "_graphs").mkdir()
            def job(i, statut="failed", provider="animation", img="mcode_abcd1234.mp4", graphe=False, recette=False):
                if graphe:
                    (pathlib.Path(d) / "_graphs" / f"{i}.json").write_text('{"nodes":[],"edges":[]}', encoding="utf-8")
                if recette:
                    quick_recipe.save(i, {"tab": "seedance"})
                return SimpleNamespace(id=i, status=statut, provider=provider, image_filename=img)
            res = {
                "mcode_graphe": R._relance_de(job("a1", graphe=True)),
                "mcode_sans_graphe": R._relance_de(job("a2")),
                "anim_graphe": R._relance_de(job("a3", img="anim_abcd1234.mp4", graphe=True)),
                "quick": R._relance_de(job("q1", provider="seedance", img="x.png", recette=True)),
                "quick_et_graphe": R._relance_de(job("q2", provider="seedance", img="x.png", recette=True, graphe=True)),
                "studio": R._relance_de(job("s1", provider="template", img="", graphe=True)),
                "rien": R._relance_de(job("n1", provider="asset3d", img="asset3d_x")),
                "termine": R._relance_de(job("t1", statut="done", graphe=True)),
                "en_cours": R._relance_de(job("t2", statut="generating_video", provider="seedance", recette=True)),
                # un graphe posé HORS de _graphs (outputs/evade.json) : « ../evade » ne doit pas le lire
                "chemin": (pathlib.Path(d, "evade.json").write_text("{}", encoding="utf-8"),
                           R._relance_de(job("../evade", graphe=False)))[1],
            }
            j = SimpleNamespace(**{k: None for k in (
                "id status progress title current_step image_filename image_filename_end final_prompt negative_prompt "
                "video_path audio_path final_video_path caption_text caption_path seed duration_s aspect_ratio style "
                "template_id voiceover_language voice_mode video_model provider composition_id composition_layout "
                "layer_index error batch_id batch_index batch_size created_at completed_at rating fav").split()})
            j.id, j.status, j.provider, j.image_filename = "a1", "failed", "animation", "mcode_abcd1234.mp4"
            res["dict"] = R._job_to_dict(j).get("relance", "ABSENT")
            j.status = "done"
            res["dict_done"] = R._job_to_dict(j).get("relance", "ABSENT")
            return res
        finally:
            settings.OUTPUTS_FOLDER = ancien


try:
    SRV = _cas_serveur()
except Exception as e:  # noqa: BLE001
    SRV = {"erreur": f"{type(e).__name__}: {e}"}
check("B1 motion code en échec avec graphe → direct", SRV.get("mcode_graphe") == "direct", SRV)
check("B2 motion code sans graphe → rien (masqué)", SRV.get("mcode_sans_graphe") is None, SRV)
check("B3 Animation (anim_*) avec graphe → studio", SRV.get("anim_graphe") == "studio", SRV)
check("B4 recette Quick → quick", SRV.get("quick") == "quick", SRV)
check("B5 recette Quick ET graphe → quick (la recette est le formulaire exact)", SRV.get("quick_et_graphe") == "quick", SRV)
check("B6 graphe seul → studio", SRV.get("studio") == "studio", SRV)
check("B7 ni recette ni graphe → rien", SRV.get("rien") is None, SRV)
check("B8 job terminé ou en cours → rien", SRV.get("termine") is None and SRV.get("en_cours") is None, SRV)
check("B9 un id hors du dossier ne lit rien d'autre", SRV.get("chemin") is None, SRV)
check("B10 _job_to_dict porte `relance` (direct en échec, None sinon)",
      SRV.get("dict") == "direct" and SRV.get("dict_done") is None, SRV)

# ── [A] câblage ───────────────────────────────────────────────────────────────────────────────────────────────────
print("[A] câblage dans le livré")
check("A1 plus de bouton « Réessayer » sans onClick", INERTE not in BUNDLE)
check("A2 le bouton n'existe que si le serveur dit comment relancer, et appelle __dzRelancer",
      'u&&e.relance&&r.jsx(K,{title:e.relance==="quick"?' in BUNDLE
      and 'onClick:function(ev){__dzRelancer(e,ev)},variant:"outline",size:"sm",icon:"dz-action-reessayer",children:' in BUNDLE)
check("A3 libellés : Réessayer / Réessayer dans Quick / Réessayer dans le Studio, tous en clés littérales",
      'children:e.relance==="quick"?dzT("coque.file.reessayer_quick"):e.relance==="studio"?'
      'dzT("coque.file.reessayer_studio"):dzT("commun.action.reessayer")' in BUNDLE)
check("A4 la ligne du Dock reçoit relance, aspect et titre du job",
      'error:c.error,relance:c.relance||null,aspect:c.aspect_ratio||"",titre:c.title||"",img:c.image_' in BUNDLE)
check("A6 avec le bouton, les actions passent à la ligne dans 112 px (le badge « échoué » n'est plus recouvert)",
      'justifySelf:"end",flexWrap:"wrap",justifyContent:"flex-end",rowGap:6,maxWidth:u&&e.relance?112:void 0}' in BUNDLE)
check("A5 __dzRelancer posé une fois, juste devant __dzReopenStudio",
      BUNDLE.count("function __dzRelancer(") == 1
      and BUNDLE.find("function __dzRelancer(") < BUNDLE.find("function __dzReopenStudio(id){")
      and "__dzReopenStudio(id){" in BUNDLE[BUNDLE.find("function __dzRelancer("):][:4000])

# ── [F] sous node ─────────────────────────────────────────────────────────────────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
const SRC=tranche("function Wt(","function dzFinImg(")+tranche("function dzMoProps(","function dzMoNature(")
 +tranche("function __dzRelancer(","function __dzReopenStudio(id){");
let APPELS=[],TOASTS=[],ROUTES={};
const Me={MotionCode:{props:{script:"",durationS:8,fps:30,pageId:""}}};
function dzT(k,v){return k+(v?JSON.stringify(v):"")}
function __dzToast(m){TOASTS.push(m)}
function __dzReopenQuick(id){APPELS.push(["quick",id])}
function __dzReopenStudio(id){APPELS.push(["studio",id])}
function fetch(u,o){APPELS.push(["fetch",u,o&&o.method||"GET",o&&o.body?JSON.parse(o.body):null]);
 const r=ROUTES[u]||{s:404,j:null};return Promise.resolve({ok:r.s<300,status:r.s,json:()=>Promise.resolve(r.j)})}
eval(SRC);
function bouton(){const b={disabled:false};return {b,ev:{currentTarget:b,stopPropagation(){b.stop=true}}}}
const G={nodes:[{id:"m",type:"MotionCode",props:{pageId:"mc_abc",fps:24,durationS:12}},{id:"r",type:"Render",props:{}}],
 edges:[{from:"m",fromPort:"out",to:"r",toPort:"in"}]};
const J={id:"j1",relance:"direct",aspect:"9:16",titre:"animaytion test"};
async function cas(nom,job,routes){APPELS=[];TOASTS=[];ROUTES=routes||{};const {b,ev}=bouton();
 const p=__dzRelancer(job,ev);const pendant=b.disabled;await p;await new Promise(r=>setTimeout(r,0));
 return {nom,appels:APPELS,toasts:TOASTS,pendant,apres:b.disabled,stop:!!b.stop}}
(async()=>{const R=[];
 R.push(await cas("direct",J,{"/api/jobs/j1/graph":{s:200,j:G},"/api/motion/code/rendre":{s:200,j:{job_id:"j2"}}}));
 R.push(await cas("direct_sans_mc",J,{"/api/jobs/j1/graph":{s:200,j:{nodes:[{id:"r",type:"Render"}],edges:[]}}}));
 R.push(await cas("direct_sans_page",J,{"/api/jobs/j1/graph":{s:200,j:{nodes:[{id:"m",type:"MotionCode",props:{}},{id:"r",type:"Render"}],edges:G.edges}}}));
 R.push(await cas("direct_graphe_404",J,{})); R.push(await cas("direct_deux_mc",J,{"/api/jobs/j1/graph":{s:200,j:{nodes:G.nodes.concat([{id:"m2",type:"MotionCode",props:{pageId:"mc_z"}},{id:"r2",type:"Render"}]),edges:G.edges.concat([{from:"m2",fromPort:"out",to:"r2",toPort:"in"}])}}}));
 R.push(await cas("direct_502",J,{"/api/jobs/j1/graph":{s:200,j:G},"/api/motion/code/rendre":{s:502,j:{detail:"bac à sable arrêté"}}}));
 R.push(await cas("quick",{id:"q1",relance:"quick"}));
 R.push(await cas("studio",{id:"s1",relance:"studio"}));
 R.push(await cas("rien",{id:"n1",relance:null}));
 process.stdout.write(JSON.stringify(R));})().catch(e=>{process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""


def _node():
    with tempfile.TemporaryDirectory() as d:
        h = pathlib.Path(d) / "h.js"
        h.write_text(HARNAIS, encoding="utf-8")
        p = subprocess.run(["node", str(h), str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return {"erreur": (p.stdout + p.stderr)[:800]}


print("[F] sous node (vraies fonctions du livré)")
NR = _node()
C = {c["nom"]: c for c in NR} if isinstance(NR, list) else {}
check("F0 harnais exécuté", bool(C), NR)
d = C.get("direct", {})
post = [a for a in d.get("appels", []) if a[0] == "fetch" and a[2] == "POST"]
check("F1 direct : relit le graphe puis UN POST /api/motion/code/rendre avec la même page, cadence, durée, format, titre",
      len(post) == 1 and post[0][1] == "/api/motion/code/rendre" and post[0][3].get("page_id") == "mc_abc"
      and post[0][3].get("fps") == 24 and post[0][3].get("duree_s") == 12 and post[0][3].get("aspect") == "9:16"
      and post[0][3].get("title") == "animaytion test" and post[0][3].get("source_graph", {}).get("nodes")
      and d["appels"][0][1] == "/api/jobs/j1/graph", d)
check("F2 direct : bouton grisé pendant l'envoi, clic non propagé, message « relancé »",
      d.get("pendant") is True and d.get("stop") is True
      and any(t.startswith("coque.file.reessayer_lance") and "animaytion test" in t for t in d.get("toasts", [])), d)
for nom in ("direct_sans_mc", "direct_sans_page", "direct_graphe_404", "direct_deux_mc"):
    c = C.get(nom, {})
    check(f"F3 {nom} : aucun POST, repli sur le Studio, bouton rendu",
          not [a for a in c.get("appels", []) if a[0] == "fetch" and a[2] == "POST"]
          and ["studio", "j1"] in c.get("appels", []) and c.get("apres") is False, c)
c = C.get("direct_502", {})
check("F4 échec du serveur : son message, bouton rendu, pas de repli",
      any(t.startswith("coque.file.reessayer_echec") and "bac à sable arrêté" in t for t in c.get("toasts", []))
      and c.get("apres") is False and ["studio", "j1"] not in c.get("appels", []), c)
c = C.get("quick", {})
check("F5 quick : Quick rouvert prérempli, aucun appel réseau ici", c.get("appels") == [["quick", "q1"]], c)
c = C.get("studio", {})
check("F6 studio : Studio rouvert, aucun appel réseau ici", c.get("appels") == [["studio", "s1"]], c)
c = C.get("rien", {})
check("F7 sans relance : rien", c.get("appels") == [] and c.get("toasts") == [], c)

# ── [D] chaîne ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[D] chaîne dzdock")
try:
    import patch_bundle_dzdock as PD
except Exception as e:  # noqa: BLE001
    PD = None
    print(f"  (maillon introuvable : {e})")


def _base_bytes():
    r_ = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True,
                        cwd=str(RACINE))
    return r_.stdout.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")     # le dépôt garde le bundle en LF


check("D1 maillon présent", PD is not None)
check("D2 sans le maillon (avant_dzdock) = la base octet pour octet",
      lambda: __import__("_i18n_l1_aide").avant_dzdock(BUNDLE).encode("utf-8") == _base_bytes())
check("D3 avant_dzmotion défait dzdock d'abord",
      lambda: "__dzRelancer" not in __import__("_i18n_l1_aide").avant_dzmotion(BUNDLE))
check("D4 aller-retour exact", lambda: PD.appliquer(PD.defaire(BUNDLE)) == BUNDLE)
check("D5 comptes figés : x.useState( 731, DzTracks 181, v2.8.0 ×4, dz-action-reessayer ×1, aucun hook neuf",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("DzTracks") == 181 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("dz-action-reessayer") == 1 and BUNDLE.count("dzMoUS(") == 3)
check("D5b le remplacement G1 de dzglyph reste contigu (title / onClick avant variant)",
      BUNDLE.count('m",icon:"dz-action-reessayer",childre') == 1)
check("D6 octets : CRLF partout", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("D7 le maillon lit en octets", lambda: "read_text(" not in (RACINE / "scripts" / "patch_bundle_dzdock.py")
      .read_text(encoding="utf-8") and "write_text(" not in (RACINE / "scripts" / "patch_bundle_dzdock.py")
      .read_text(encoding="utf-8"))
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzdock.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                    env=dict(__import__("os").environ, PYTHONIOENCODING="utf-8"))
check("D8 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)
check("D9 pas de .bak_dzdock laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzdock")).exists())

# ── [K] textes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] textes FR / EN")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "relance.json").read_text(encoding="utf-8"))
CLES = ["coque.file.reessayer_quick", "coque.file.reessayer_studio", "coque.file.reessayer_direct_aide",
        "coque.file.reessayer_quick_aide", "coque.file.reessayer_studio_aide", "coque.file.reessayer_lance",
        "coque.file.reessayer_echec"]
for k in CLES:
    v = DICO.get(k) or {}
    check(f"K1 {k} : FR et EN, mêmes variables",
          v.get("fr") and v.get("en") and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
          and f'"{k}"' in BUNDLE, v)
src_dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("K2 dictionnaire assemblé (source = copie de dist)",
      all(k.encode() in src_dico for k in CLES)
      and src_dico == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS / {fail} FAIL")


def test_jobdock_reessayer():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
