# -*- coding: utf-8 -*-
"""Plan-studio T3-T4 (tache #67 du suivi, PR B, 02/10/2026) — les EPINGLES du Studio cote EDITEUR, dans le maillon
montage (decision du 02/10 : pas de maillon studiopin). Les fonctions sont EXTRAITES du bundle livre et executees
sous node (fetch, window et setTimeout simules) : on verifie ce qui part chez l'utilisateur, pas une recopie.
Ce que le plan faisait faux, et que ce banc garde : une empreinte calculee par l'editeur (ici : seul le serveur la
calcule, l'editeur la recoit) ; une recolte qui epinglait le graphe ouvert a la FIN du rendu, quel qu'il soit (ici :
meme nom de graphe, meme noeud, meme type) ; un devis qui sautait des noeuds qu'aucune voie ne substitue (ici : jamais
pour un noeud seul) ; une epingle perimee regeneree en douce (ici : retiree, le tir s'arrete, le cout est recalcule).
Temoin positif : le bundle de la base (1e01cbaa) n'a ni la couche ni les sections.
Run (depuis backend/) : & $PY tests/test_studio_epingles_bundle.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
import _i18n_l1_aide as AIDE                               # noqa: E402  (t142 : textes par dzT, francais par AIDE.fr)
# t143 : la couche montage.js du bundle passe par dzT (traduction L3) ; le banc lit son texte français d'avant la traduction
BUN = AIDE.avant_i18n_l3((RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8"))
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzpinb_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "1e01cbaa"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : le bundle de la base n'a ni la couche d'epingle ni ses sections", r0.returncode == 0 and len(r0.stdout) > 1_000_000
      and b"DzPinPanel" not in r0.stdout and b"dzPinPreparer" not in r0.stdout)


def entre(debut, fin):
    i = BUN.find(debut)
    j = BUN.find(fin, i + 1)
    return BUN[i:j] if i >= 0 and j > i else ""


def node(js):
    f = _TMP / f"p{abs(hash(js)) % 10**9}.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (r.stderr or r.stdout)[-400:])
        return None


COUCHE = entre("function dzPinRendu(", "function DzPinPanel(")
OPS = entre("function dzStudioOps(", "var dzStudioVu=")
WT = ("function Wt(g,id,port){var e=(g.edges||[]).filter(function(x){return x.to===id&&x.toPort===port})[0];"
      "return e?(g.nodes||[]).filter(function(n){return n.id===e.from})[0]:null}\n")
check("T2 la couche est dans le bundle livre (une fois) et dzStudioOps la consulte",
      bool(COUCHE) and BUN.count("function dzPinPreparer(") == 1 and "dzPinReemploi(g,n)" in OPS)

PIN = {"job_id": "j-old", "empreinte": "e" * 32}
COMPO = {"name": "Mon graphe", "nodes": [
    {"id": "img1", "type": "Image", "props": {"filename": "a.png"}}, {"id": "img2", "type": "Image", "props": {"filename": "b.png"}},
    {"id": "p1", "type": "Text", "props": {"value": "vagues"}},
    {"id": "s1", "type": "Seedance", "props": {"durationS": 10, "pin": PIN}},
    {"id": "s2", "type": "Seedance", "props": {"durationS": 5, "model": "seedance-v1-pro"}},
    {"id": "h1", "type": "HeyGenAvatar", "props": {"pin": {"job_id": "j-h", "empreinte": "f" * 32}}},
    {"id": "r", "type": "Render", "props": {}}],
    "edges": [{"from": "img1", "to": "s1", "toPort": "image"}, {"from": "p1", "to": "s1", "toPort": "prompt"},
              {"from": "img2", "to": "s2", "toPort": "image"}]}
SOLO = {"name": "Solo", "nodes": [{"id": "img1", "type": "Image", "props": {"filename": "a.png"}},
                                  {"id": "s1", "type": "Seedance", "props": {"pin": PIN}}],
        "edges": [{"from": "img1", "to": "s1", "toPort": "image"}]}

print("[C] le devis et la voie de rendu")
R = node(WT + COUCHE + OPS + "\nvar C=" + json.dumps(COMPO) + ",S=" + json.dumps(SOLO) + ";"
         "function T(ts,extra){return {nodes:ts.map(function(t,i){return {id:'n'+i,type:t,props:{}}}).concat(extra||[])}}"
         "console.log(JSON.stringify({compo:dzPinRendu(C),solo:dzPinRendu(S),hey:dzPinRendu(T(['HeyGenAvatar'])),"
         "concat:dzPinRendu(T(['Seedance','Concatenate'])),spatial:dzPinRendu(T(['Seedance','SpatialCompose'])),"
         "upload:dzPinRendu(T(['Seedance'],[{id:'u',type:'Upload',props:{jobId:'x'}}])),"
         "re:[dzPinReemploi(C,C.nodes[3]),dzPinReemploi(C,C.nodes[4]),dzPinReemploi(C,C.nodes[5]),dzPinReemploi(S,S.nodes[1])],"
         "nb:[dzPinNb(C),dzPinNb(S)],ops:dzStudioOps(C).map(function(o){return o.kind}),opsSolo:dzStudioOps(S).map(function(o){return o.kind})}))")
check("C1 la voie de RENDU de graphe : Seedance+HeyGen, Concatenate, SpatialCompose, Upload -> oui ; un noeud seul -> non",
      R is not None and R["compo"] and not R["solo"] and not R["hey"] and R["concat"] and R["spatial"] and R["upload"], str(R))
check("C2 un noeud est reemploye s'il porte une epingle COMPLETE ET que sa voie substitue ; jamais un noeud seul",
      R is not None and R["re"] == [True, False, True, False] and R["nb"] == [2, 0], str(R and R["re"]))
check("C3 le « ≈ $ » ne facture pas les deux noeuds epingles (reste : 2 images, 1 video) ; le noeud seul reste facture",
      R is not None and sorted(R["ops"]) == ["image", "image", "video"] and sorted(R["opsSolo"]) == ["image", "video"], str(R and R["ops"]))

print("\n[P] la preparation du tir : annoter, faire verifier, arreter sur une epingle perimee")
SLOTS = {"anim": {"source_kind": "seedance", "seedance": {"image_filename": "a.png", "custom_prompt": "vagues", "duration_s": 10}},
         "anim2": {"source_kind": "seedance", "seedance": {"image_filename": "b.png", "custom_prompt": "x", "video_model": "seedance-v1-pro"}},
         "avatar": {"source_kind": "heygen", "heygen": {"avatar_id": "a", "voice_id": "v", "script": "s"}},
         "titre": {"source_kind": "text", "text": "T"}}
SIM = ("var APPELS=[],MAJ=[];var window={__dzStudioMaj:function(n,p){MAJ.push([n,p])}};"
       "function repondre(rep){globalThis.fetch=async function(u,o){APPELS.push([u,o&&JSON.parse(o.body)]);"
       "if(rep===null)throw new Error('reseau');return {ok:true,json:async function(){return rep}}}}\n")


def preparer(rep, graphe=COMPO, slots=SLOTS):
    return node(WT + COUCHE + "\n" + SIM + "repondre(" + json.dumps(rep) + ");(async function(){var t=" + json.dumps(slots) +
                ";var m=await dzPinPreparer('tpl_x',t,'oracle',null," + json.dumps(graphe) + ");"
                "console.log(JSON.stringify({m:m,t:t,appels:APPELS,maj:MAJ}))})()")


R = preparer({"slots": {"anim": {"valide": True}, "avatar": {"valide": True}}})
t = (R or {}).get("t", {})
corps = ((R or {}).get("appels") or [[None, {}]])[0][1] or {}
check("P1 chaque slot genere porte son NOEUD (par image, prompt et modele : a.png -> s1, b.png -> s2 ; HeyGen -> h1) et son epingle",
      R is not None and t["anim"].get("node_id") == "s1" and t["anim2"].get("node_id") == "s2" and t["avatar"].get("node_id") == "h1"
      and t["anim"].get("pin") == PIN and "pin" not in t["anim2"] and "node_id" not in t["titre"], str(t)[:300])
check("P2 la verification part au serveur avec les slots, le modele de rendu et le mode voix ; toutes valides : rien ne s'arrete",
      R is not None and R["m"] == "" and len(R["appels"]) == 1 and R["appels"][0][0] == "/api/studio/pins/verifier"
      and corps.get("template_id") == "tpl_x" and corps.get("voice_mode") == "oracle" and corps["slot_values"]["anim"]["pin"] == PIN
      and R["maj"] == [], str(R and R["appels"])[:200])
def graphe2(n1, n2, liens):
    return {"name": "G2", "nodes": [{"id": "ia", "type": "Image", "props": {"filename": "a.png"}},
                                    {"id": "ib", "type": "Image", "props": {"filename": "b.png"}},
                                    {"id": "pa", "type": "Text", "props": {"value": "vagues"}}, {"id": "pb", "type": "Text", "props": {"value": "pluie"}},
                                    n1, n2, {"id": "h", "type": "HeyGenAvatar", "props": {}}], "edges": liens}


def deux(slots, g):
    return node(WT + COUCHE + "\n" + SIM + "repondre({slots:{}});(async function(){var t=" + json.dumps(slots) +
                ";await dzPinPreparer('tpl_x',t,null,null," + json.dumps(g) + ");console.log(JSON.stringify(t))})()")


S2 = {"x": {"source_kind": "seedance", "seedance": {"image_filename": "a.png", "custom_prompt": "vagues"}},
      "y": {"source_kind": "seedance", "seedance": {"image_filename": "b.png", "custom_prompt": "vagues"}}}
G_IMG = graphe2({"id": "sb", "type": "Seedance", "props": {}}, {"id": "sa", "type": "Seedance", "props": {}},
                [{"from": "ib", "to": "sb", "toPort": "image"}, {"from": "pa", "to": "sb", "toPort": "prompt"},
                 {"from": "ia", "to": "sa", "toPort": "image"}, {"from": "pa", "to": "sa", "toPort": "prompt"}])
r1 = deux(S2, G_IMG)
S3 = {"x": {"source_kind": "seedance", "seedance": {"image_filename": "a.png", "custom_prompt": "vagues"}},
      "y": {"source_kind": "seedance", "seedance": {"image_filename": "a.png", "custom_prompt": "pluie"}}}
G_PR = graphe2({"id": "sp", "type": "Seedance", "props": {}}, {"id": "sv", "type": "Seedance", "props": {}},
               [{"from": "ia", "to": "sp", "toPort": "image"}, {"from": "pb", "to": "sp", "toPort": "prompt"},
                {"from": "ia", "to": "sv", "toPort": "image"}, {"from": "pa", "to": "sv", "toPort": "prompt"}])
r2 = deux(S3, G_PR)
S4 = {"x": {"source_kind": "seedance", "seedance": {"image_filename": "a.png", "custom_prompt": "vagues"}},
      "y": {"source_kind": "seedance", "seedance": {"image_filename": "a.png", "custom_prompt": "vagues"}}}
G_JUM = graphe2({"id": "j1", "type": "Seedance", "props": {}}, {"id": "j2", "type": "Seedance", "props": {}},
                [{"from": "ia", "to": "j1", "toPort": "image"}, {"from": "pa", "to": "j1", "toPort": "prompt"},
                 {"from": "ia", "to": "j2", "toPort": "image"}, {"from": "pa", "to": "j2", "toPort": "prompt"}])
r3 = deux(S4, G_JUM)
check("P1b le noeud est trouve par son IMAGE (meme prompt, ordre trompeur), par son PROMPT (meme image), et deux jumeaux "
      "recoivent chacun UN slot",
      r1 is not None and r1["x"].get("node_id") == "sa" and r1["y"].get("node_id") == "sb"
      and r2 is not None and r2["x"].get("node_id") == "sv" and r2["y"].get("node_id") == "sp"
      and r3 is not None and {r3["x"].get("node_id"), r3["y"].get("node_id")} == {"j1", "j2"}, f"{r1} {r2} {r3}")
R = preparer({"slots": {"anim": {"valide": True}}})
check("P3b un slot epingle ABSENT de la reponse du serveur ne vaut pas : epingle retiree, tir arrete",
      R is not None and "h1" in R["m"] and "pin" not in R["t"]["avatar"] and R["t"]["anim"].get("pin") == PIN
      and R["maj"] == [["h1", {"pin": None, "pinPerime": "épingle inconnue"}]], str(R)[:300])
R = preparer({"slots": {"anim": {"valide": False, "raison": "la requête a changé"}, "avatar": {"valide": True}}})
check("P3 une epingle PERIMEE : retiree du slot ET du noeud (avec la raison), et le tir S'ARRETE avec un message",
      R is not None and "s1" in R["m"] and "la requête a changé" in R["m"] and "pin" not in R["t"]["anim"] and R["t"]["avatar"].get("pin")
      and R["maj"] == [["s1", {"pin": None, "pinPerime": "la requête a changé"}]], str(R)[:300])
R = preparer(None)
check("P4 verification IMPOSSIBLE : le tir s'arrete, les epingles ne partent pas, celles du graphe restent (une panne n'efface rien)",
      R is not None and "impossible" in R["m"] and all("pin" not in s for s in R["t"].values()) and R["maj"] == [], str(R)[:200])
SANS = json.loads(json.dumps(COMPO))
for n in SANS["nodes"]:
    n["props"].pop("pin", None)
R = preparer({"slots": {}}, graphe=SANS)
check("P5 aucune epingle : AUCUN appel de verification (le tir part comme avant)", R is not None and R["m"] == "" and R["appels"] == [], str(R)[:200])

print("\n[R] la recolte apres un rendu accepte")
PARTS = {"parts": [{"slot": "anim", "node_id": "s2", "kind": "seedance", "job_id": "j-neuf", "empreinte": "a" * 32, "reemploi": False},
                   {"slot": "avatar", "node_id": "h1", "kind": "heygen", "job_id": "j-h", "empreinte": "f" * 32, "reemploi": True},
                   {"slot": "x", "node_id": "s1", "kind": "heygen", "job_id": "j-z", "empreinte": "b" * 32}]}


def recolter(graphe_ouvert):
    return node(WT + COUCHE + "\nvar MAJ=[];var window={__dzStudioMaj:function(n,p){MAJ.push([n,p])},__dzStudioG:" + json.dumps(graphe_ouvert) + "};"
                "globalThis.setTimeout=function(f){f()};"
                "globalThis.fetch=async function(u){return {ok:true,json:async function(){return /parts$/.test(u)?" + json.dumps(PARTS) +
                ":{status:'done'}}}};dzPinRecolter({job_id:'rendu-1'}," + json.dumps(COMPO) + ");"
                "new Promise(function(r){globalThis.setImmediate(r)}).then(function(){return new Promise(function(r){globalThis.setImmediate(r)})})"
                ".then(function(){console.log(JSON.stringify({maj:MAJ}))})")


R = recolter(COMPO)
maj = {m[0]: m[1] for m in (R or {}).get("maj", [])}
check("R1 chaque partie va a SON noeud : s2 recoit sa nouvelle epingle (job, empreinte du serveur), h1 garde la sienne",
      R is not None and maj.get("s2", {}).get("pin", {}).get("job_id") == "j-neuf" and maj["s2"]["pin"]["empreinte"] == "a" * 32
      and maj.get("h1", {}).get("pin", {}).get("reemploi") is True and maj["s2"].get("pinPerime") is None, str(R)[:300])
check("R2 une partie dont le TYPE ne colle pas au noeud (heygen -> Seedance s1) n'est pas posee", R is not None and "s1" not in maj, str(list(maj)))
AUTRE = dict(COMPO, name="Un autre graphe")
R = recolter(AUTRE)
check("R3 le graphe ouvert n'est PLUS celui du rendu (autre nom) : RIEN n'est epingle", R is not None and R["maj"] == [], str(R)[:200])

print("\n[W] le cablage dans le bundle livre")
check("W1 le Studio expose son graphe et son setter (P7pin1), une fois",
      BUN.count("onUpdateNode:(window.__dzStudioG=o,window.__dzStudioMaj=(nid,pp)=>i(") == 1)
check("W2 renderLayoutTemplate prepare et VERIFIE les epingles avant le tir (hors apercu), et s'arrete sur un message",
      BUN.count("window.__dzfxPreview=!1;if(!_pv&&g&&t){var dzPP=await dzPinPreparer(e,t,n,o,g);if(dzPP)return{ok:!1,error:dzPP}}") == 1)
check("W3 un rendu ACCEPTE lance la recolte", BUN.count("if(s.ok){var dzJ=await s.json();dzPinRecolter(dzJ,g);return dzJ}") == 1)
check("W4 le panneau dans l'inspecteur des Seedance et HeyGen ; son bouton « Regenerer » a un title ; le noeud seul est explique",
      BUN.count('(e.type==="Seedance"||e.type==="HeyGenAvatar")&&r.jsx(DzPinPanel,{node:e,graph:t,onUpdate:o})') == 1
      # t142 (09/10) : textes passes par dzT ; epingles par leur cle, le francais verifie par AIDE.fr
      and 'title:dzT("studio.epingle.regenerer_aide")' in BUN and AIDE.fr("studio.epingle.regenerer_aide").startswith("Retirer l'épingle")
      and 'children:__dzGlT("dz-etat-epingle",dzT("studio.epingle.sans_epingle"),"📌")' in BUN     # icônes G1
      and AIDE.fr("studio.epingle.sans_epingle").startswith("📌 Pas d'épingle ici : un Seedance seul (ou un HeyGen seul) part directement par /generate")
      and "onUpdate({pin:null,pinPerime:null})" in BUN)
check("W5 le « ≈ $ » dit les noeuds reemployes", BUN.count('dzPinNb(graph)?dzT("studio.cout.reutilises",{n:dzPinNb(graph)}):""') == 1
      and AIDE.fr("studio.cout.reutilises", n=2) == " · 2 nœud(s) réutilisé(s)")
check("W6 la chaine tient : sondes aval inchangees (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2)",
      BUN.count("DzTracks") == 181 and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
