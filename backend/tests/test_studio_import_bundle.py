# -*- coding: utf-8 -*-
"""Plan-studio T7 (tache #69 du suivi, 02/10/2026) — le bouton « Importer » du Studio, dans le bundle LIVRE. Le
composant (couche du maillon montage) est extrait du bundle et EXECUTE sous node, React, le dialogue maison et fetch
remplaces par des doublures qui notent tout.
DECISIONS DE L'UTILISATEUR (02/10) : bouton dans le maillon montage ; graphe ouvert + dialogue qui LISTE les sources
manquantes et les aretes jetees ; remplacement CONFIRME si le graphe ouvert a des noeuds ; rien n'est enregistre.
Temoin positif : le bundle de la base (bdb70ceb) n'a pas le bouton.
Run (depuis backend/) : & $PY tests/test_studio_import_bundle.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
BUN = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzimpb_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "bdb70ceb"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : le bundle de la base a le selecteur de graphes mais pas l'import", r0.returncode == 0
      and b"function DzOpenGraph(" in r0.stdout and b"DzImportGraph" not in r0.stdout and b"studio-graphs/import" not in r0.stdout)


def fonction(nom):
    """Le texte d'une declaration `function nom(` du bundle, accolades appariees (chaines sautees)."""
    k = BUN.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = BUN.find("){", k) + 1, 0, None, False      # le CORPS (la signature peut destructurer)
    while i < len(BUN):
        c = BUN[i]
        if ch:
            if c == "\\": i += 2; continue
            if c == ch: ch = None
        elif c in "\"'`": ch = c
        elif c == "{": prof += 1; vu = True
        elif c == "}":
            prof -= 1
            if vu and prof == 0: return BUN[k:i + 1]
        i += 1
    return ""


LISTE, COMP = fonction("dzImpListe"), fonction("DzImportGraph")
check("T2 la couche livree a le composant et sa liste (une fois chacun)", BUN.count("function DzImportGraph(") == 1
      and BUN.count("function dzImpListe(") == 1 and bool(LISTE) and bool(COMP))

APPEL = ('r.jsx(DzImportGraph,{graph:o,onOpen:function(G){i(ts(G));d({});f({});a(null);k(null);'
         'p("Graphe importé (non enregistré) : "+G.name)}}),r.jsx(DzOpenGraph,{onPick:async id=>{')
check("T3 pose une fois, juste a gauche de « Ouvrir un graphe » : ts() fusionne les defauts, etats/selection/rendu remis a zero",
      BUN.count(APPEL) == 1 and BUN.count("r.jsx(DzImportGraph,") == 1)
j = BUN.find("function Lh(")
check("T4 dans le Studio (Lh), ou o/i sont le graphe et son setter, d/f/a/k les etats, p le message",
      0 <= j < BUN.find(APPEL) and "[o,i]=x.useState(" in BUN[j:BUN.find(APPEL)] and "[c,p]=x.useState(" in BUN[j:BUN.find(APPEL)])

HARNAIS = r"""
var JOURNAL=[],ARBRE=null,OUVERT=[],REP=null,CONF=true;
var x={useRef:function(v){return {current:{click:function(){JOURNAL.push(["click"])}}}}};
function el(t,p){return {t:t,p:p||{}}}
var r={jsx:el,jsxs:el,Fragment:"frag"};var K="K";
var window={__dzDialogue:{
  informer:async function(m,o){JOURNAL.push(["informer",m,o&&o.titre])},
  confirmer:async function(m,o){JOURNAL.push(["confirmer",m,o&&o.ok]);return CONF}}};
globalThis.fetch=async function(u,o){JOURNAL.push(["fetch",u,o.method,JSON.parse(o.body)]);
  if(REP==="panne")throw new Error("hors ligne");
  return {ok:REP.ok,status:REP.status||200,json:async function(){return REP.d}}};
function fichier(nom,texte,taille){return {name:nom,size:taille==null?texte.length:taille,text:async function(){return texte}}}
function trouver(n,f){if(!n||typeof n!=="object")return null;if(f(n))return n;var c=n.p&&n.p.children;
  if(Array.isArray(c)){for(var i=0;i<c.length;i++){var z=trouver(c[i],f);if(z)return z}}else if(c&&typeof c==="object")return trouver(c,f);return null}
async function scenario(graphe,f){JOURNAL=[];OUVERT=[];
  var T=DzImportGraph({graph:graphe,onOpen:function(G){OUVERT.push(G)}});ARBRE=T;
  var inp=trouver(T,function(n){return n.t==="input"});
  var ev={target:{files:[f],value:"x"}};inp.p.onChange(ev);
  for(var i=0;i<20;i++)await new Promise(function(r){setImmediate(r)});
  return {j:JOURNAL,o:OUVERT,vide:ev.target.value}}
"""
GRAPHE_OUVERT = {"name": "Mon graphe", "nodes": [{"id": "a"}, {"id": "b"}], "edges": []}
REP_OK = {"ok": True, "d": {"graph": {"name": "Importé", "nodes": [{"id": "im"}, {"id": "er"}, {"id": "rn"}], "edges": []},
                             "warnings": ["Port d'entrée « fantome » inconnu sur Seedance (sd) : arête jetée."],
                             "missing": [{"node_id": "im", "type": "Image", "champ": "filename", "valeur": "trone.png", "magasin": "images"},
                                         {"node_id": "er", "type": "ExistingRender", "champ": "jobId", "valeur": "job_x", "magasin": "jobs"}]}}
REP_PROPRE = {"ok": True, "d": {"graph": {"name": "Net", "nodes": [{"id": "n"}], "edges": []}, "warnings": [], "missing": []}}


def node(corps):
    f = _TMP / f"i{abs(hash(corps)) % 10**9}.js"
    f.write_text(LISTE + "\n" + COMP + "\n" + HARNAIS + "\n(async function(){var R={};" + corps
                 + "\nconsole.log(JSON.stringify(R))})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-500:])
        return None


print("[F] le parcours")
R = node(f"""
REP={json.dumps(REP_OK)};CONF=true;R.ok=await scenario({json.dumps(GRAPHE_OUVERT)},fichier("g.json",'{{"nodes":[{{"id":"im","type":"Image"}}]}}'));
CONF=false;R.non=await scenario({json.dumps(GRAPHE_OUVERT)},fichier("g.json","{{}}"));
REP={json.dumps(REP_PROPRE)};R.vide=await scenario({{name:"",nodes:[],edges:[]}},fichier("g.json","{{}}"));
R.nul=await scenario(null,fichier("g.json","{{}}"));
R.json=await scenario({json.dumps(GRAPHE_OUVERT)},fichier("casse.json","{{pas du json"));
R.gros=await scenario({json.dumps(GRAPHE_OUVERT)},fichier("g.json","{{}}",6e6));
REP={{ok:false,status:400,d:{{detail:"Type de nœud inconnu : Sora (nœud sd). Le registre de cette version en compte 34."}}}};
R.refus=await scenario({json.dumps(GRAPHE_OUVERT)},fichier("g.json","{{}}"));
REP={{ok:false,status:500,d:null}};R.refus2=await scenario({json.dumps(GRAPHE_OUVERT)},fichier("g.json","{{}}"));
REP="panne";R.panne=await scenario({json.dumps(GRAPHE_OUVERT)},fichier("g.json","{{}}"));
R.liste=dzImpListe({json.dumps(REP_OK["d"])});R.liste0=dzImpListe({{warnings:[],missing:[]}});R.listeNul=dzImpListe(null);
""")
check("F0 le parcours s'execute sous node (aucune exception non rattrapee)", R is not None)
if R:
    j = R["ok"]["j"]
    check("F1 le fichier part tel quel au serveur (POST /api/studio-graphs/import, {graph: …})",
          j[0] == ["fetch", "/api/studio-graphs/import", "POST", {"graph": {"nodes": [{"id": "im", "type": "Image"}]}}], str(j[:1]))
    check("F2 graphe ouvert NON vide : remplacement CONFIRME, avec les deux noms et les deux tailles, bouton « Remplacer »",
          len(j) > 1 and j[1][0] == "confirmer" and "« Importé » (3 nœuds)" in j[1][1] and "« Mon graphe » (2 nœuds)" in j[1][1]
          and "perdu" in j[1][1] and j[1][2] == "Remplacer", str(j[1:2]))
    check("F3 confirme : le graphe RENDU PAR LE SERVEUR s'ouvre (pas le fichier brut)", R["ok"]["o"] == [REP_OK["d"]["graph"]], str(R["ok"]["o"]))
    check("F4 puis un dialogue LISTE chaque source manquante et chaque arete jetee, et dit que rien n'est enregistre",
          len(j) == 3 and j[2][0] == "informer" and "• Image im — image trone.png" in j[2][1] and "• ExistingRender er — rendu job_x" in j[2][1]
          and "fantome" in j[2][1] and "« Save » le garde" in j[2][1] and j[2][2] == "Graphe importé — à reprendre", str(j[2:]))
    check("F5 refus de remplacer : rien ne s'ouvre, rien d'autre n'est dit", R["non"]["o"] == [] and [x[0] for x in R["non"]["j"]] == ["fetch", "confirmer"])
    check("F6 graphe ouvert VIDE (ou absent) : pas de confirmation ; import propre : aucun dialogue",
          R["vide"]["o"] == [REP_PROPRE["d"]["graph"]] and [x[0] for x in R["vide"]["j"]] == ["fetch"]
          and R["nul"]["o"] == [REP_PROPRE["d"]["graph"]] and [x[0] for x in R["nul"]["j"]] == ["fetch"], f"{R['vide']} {R['nul']}")
    check("F7 JSON illisible : dit avec le nom du fichier AVANT tout appel reseau, rien ne s'ouvre",
          R["json"]["o"] == [] and len(R["json"]["j"]) == 1 and R["json"]["j"][0][0] == "informer"
          and "« casse.json » n’est pas du JSON valide" in R["json"]["j"][0][1], str(R["json"]))
    check("F8 fichier trop gros (> 5 Mo) : dit, sans le lire ni l'envoyer", R["gros"]["o"] == [] and len(R["gros"]["j"]) == 1
          and "trop gros" in R["gros"]["j"][0][1], str(R["gros"]))
    check("F9 refus du serveur : SA phrase, titre « Import refusé », rien ne s'ouvre et pas de confirmation",
          R["refus"]["o"] == [] and [x[0] for x in R["refus"]["j"]] == ["fetch", "informer"]
          and R["refus"]["j"][1][1].startswith("Type de nœud inconnu : Sora") and R["refus"]["j"][1][2] == "Import refusé", str(R["refus"]))
    check("F10 refus sans phrase (500 sans corps) : le statut est dit ; serveur injoignable : dit", R["refus2"]["o"] == []
          and "500" in R["refus2"]["j"][-1][1] and R["panne"]["o"] == [] and "ne répond pas" in R["panne"]["j"][-1][1], f"{R['refus2']} {R['panne']}")
    check("F11 le champ fichier est VIDE apres chaque choix (re-choisir le meme fichier relance l'import)", R["ok"]["vide"] == "" and R["json"]["vide"] == "")
    check("F12 la liste : vide quand rien ne manque (pas de dialogue), sure sur une reponse nulle", R["liste0"] == "" and R["listeNul"] == ""
          and R["liste"].count("\n• ") == 3, repr(R["liste"]))

print("\n[U] le bouton")
R = node("var T=DzImportGraph({graph:null,onOpen:function(){}});var b=trouver(T,function(n){return n.t===K}),i=trouver(T,function(n){return n.t==='input'});"
         "JOURNAL=[];b.p.onClick();R.b={title:b.p.title,icon:b.p.icon,ch:b.p.children,aria:b.p['aria-label'],v:b.p.variant};"
         "R.i={type:i.p.type,accept:i.p.accept,disp:i.p.style.display};R.clic=JOURNAL;")
check("U1 « Importer » : bouton du Studio (K, contour, icone upload) AVEC title, et libelle accessible",
      R is not None and R["b"]["ch"] == "Importer" and R["b"]["icon"] == "upload" and R["b"]["v"] == "outline"
      and "validé par le serveur" in (R["b"]["title"] or "") and "sans être enregistré" in R["b"]["title"] and R["b"]["aria"] == "Importer un graphe", str(R))
check("U2 il ouvre un champ fichier CACHE, limite au JSON", R is not None and R["clic"] == [["click"]]
      and R["i"] == {"type": "file", "accept": "application/json,.json", "disp": "none"}, str(R))
check("U3 aucun prompt/alert/confirm natif dans le composant", "window.confirm(" not in COMP and "alert(" not in COMP.replace("__dzDialogue", "")
      and "prompt(" not in COMP)
check("U4 la chaine tient : sondes aval inchangees (DzTracks 181, __dzCoutBlanc 7, __dzSrcLbl x2, dzRunMaxTake() x3)",
      BUN.count("DzTracks") == 181 and BUN.count("__dzCoutBlanc") == 7 and BUN.count("Object.assign(__dzSrcLbl,") == 2
      and BUN.count("dzRunMaxTake()") == 3)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
