# -*- coding: utf-8 -*-
"""Avatar live t168b (10/10/2026) — les nœuds Studio « Recast » et « Voix → voix » : maillon de queue
scripts/patch_bundle_avnoeuds.py, posé sur le bundle versionné. Vérifié DANS le bundle livré (catalogue, palette,
inspecteur, compilation avant les autres branches, devis du graphe, fournisseurs, tarif de carte), l'inverse
`avant_avnoeuds` à l'octet, le refus d'une double application ; puis le COMPORTEMENT des fonctions posées, rejouées
sous node avec un graphe : la route appelée et son corps, la voix comptée une fois, la durée de source ; enfin le
devis serveur de ces opérations et les clés de traduction.
Run (depuis backend/) : & $PY tests/test_avatar_noeuds.py"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzavnoeuds_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI)); sys.path.insert(0, str(RACINE / "scripts"))
from loguru import logger                                           # noqa: E402
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


import patch_bundle_avnoeuds as M                                   # noqa: E402
import _i18n_l1_aide as A                                           # noqa: E402
CHEMIN = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
B = CHEMIN.read_bytes().decode("utf-8")

print("\n[B] le bundle livré")
check("B1 le marqueur une seule fois", B.count(M.MARKER) == 1, str(B.count(M.MARKER)))
check("B2 les huit paires en place (chaque remplacement présent une fois)",
      all(B.count(b) == 1 for _a, b in M.paires(B)), [k for k, (_a, b) in enumerate(M.paires(B)) if B.count(b) != 1])
check("B3 catalogue : Recast (gen) et VoixVoix (audio), entrée et sortie vidéo",
      'Recast:{cat:"gen",title:dzT("avatar.noeud.recast_titre")' in B and 'VoixVoix:{cat:"audio",title:dzT("avatar.noeud.voix_titre")' in B)
check("B4 palette : Recast après Variations, VoixVoix après Loudness",
      '"Variations","Recast"]' in B and '"Loudness","VoixVoix"]' in B)
check("B5 la compilation essaie les nœuds Avatar AVANT la branche UGC (sinon un Upload part en composition)",
      B.find("const __av=dzAvCompile(e)") < B.find('d=e.nodes.find(h=>{var b;return h.type==="Upload"') and B.count("const __av=dzAvCompile(e)") == 1)
check("B6 le compte de « x.useState( » ne bouge pas (731, sondé par d'autres bancs) : hooks par l'alias dzAvUS",
      B.count("x.useState(") == 731 and "var dzAvUS=x.useState," in B)
check("B7 aucun .bak_avnoeuds laissé", not (CHEMIN.parent / (CHEMIN.name + ".bak_avnoeuds")).exists())
r = subprocess.run(["node", "--check", str(CHEMIN)], capture_output=True)
check("B8 le bundle reste du JavaScript valide (node --check)", r.returncode == 0, r.stderr.decode("utf-8", "replace")[-200:])
check("B9 fournisseurs (fal.ai, ElevenLabs) et tarif sur la carte",
      'else if(t==="Recast")add("fal.ai");else if(t==="VoixVoix")add("ElevenLabs");' in B
      and 'e.type==="Recast"||e.type==="VoixVoix"?r.jsx(DzAvCostTag,{node:e}):' in B)

print("\n[I] l'inverse")
sans = A.avant_avnoeuds(B)
check("I1 avant_avnoeuds défait le maillon : plus de marqueur ni de nœud Recast au catalogue",
      M.MARKER not in sans and 'Recast:{cat:"gen"' not in sans)
# dzbiblio, posé APRÈS avnoeuds, est défait par avant_avnoeuds : la référence est le bundle sans dzbiblio
check("I2 l'aller-retour est exact à l'octet (bundle sans dzbiblio ni i18nfix)", M.appliquer(sans) == A.avant_dzbiblio(B))
check("I3 avant_avatar défait D'ABORD les nœuds (posés après lui)", M.MARKER not in A.avant_avatar(B) and '{id:"avatarlive",' not in A.avant_avatar(B))
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_avnoeuds.py"), "--check"], capture_output=True,
                   text=True, cwd=str(RACINE))
check("I4 double application refusée (--check sur le bundle livré)", r.returncode != 0 and "double application" in (r.stdout + r.stderr))

print("\n[N] le comportement, rejoué sous node")
HARNAIS = r"""
const defs = require("fs").readFileSync(process.argv[1], "utf8");
const Me = { Recast: { props: { modele: "remplacer", personnage: "", prereglage: "", consigne: "", resolution: "" } }, VoixVoix: { props: { personnage: "" } } };
const appels = [];
const D = { postJson: (u, b) => { appels.push([u, b]); return Promise.resolve({ ok: true, job_id: "j" }); } };
const dzT = (k) => k, x = { useState: () => [null, () => {}], useEffect: () => {} }, r = {}, O = 0, re = 0, le = 0;
function Wt(g, id, port) { const e = g.edges.find((e) => e.to === id && e.toPort === port); return e ? g.nodes.find((n) => n.id === e.from) : null; }
eval(defs);
const N = (id, type, props) => ({ id, type, props: props || {} }), E = (a, b) => ({ from: a, fromPort: "out", to: b, toPort: "in" });
const R = {};
const g1 = { nodes: [N("s", "ExistingRender", { jobId: "job1", durationS: 18.4 }), N("r", "Recast", { personnage: "p1", modele: "remplacer", resolution: "720p", sourceDur: { job: "job1", s: 6 } }), N("v", "VoixVoix"), N("o", "Render")], edges: [E("s", "r"), E("r", "v"), E("v", "o")] };
let c = dzAvCompile(g1); c.run(); R.recast_voix = appels.pop(); R.ops1 = dzStudioLike(g1);
const g2 = { nodes: [N("s", "Upload", { jobId: "job2", durationS: 12 }), N("v", "VoixVoix", { personnage: "p1" }), N("o", "Render")], edges: [E("s", "v"), E("v", "o")] };
c = dzAvCompile(g2); c.run(); R.voix = appels.pop(); R.ops2 = dzStudioLike(g2);
const g3 = { nodes: [N("r", "Recast"), N("o", "Render")], edges: [] };
R.sans_source = dzAvCompile(g3);
const g4 = { nodes: [N("s", "ExistingRender", { jobId: "job1" }), N("v", "VoixVoix"), N("o", "Render")], edges: [E("s", "v")] };
R.sans_perso = dzAvCompile(g4);
const g5 = { nodes: [N("s", "ExistingRender", { jobId: "job9", durationS: 18.4 }), N("r", "Recast", { sourceDur: { job: "autre", s: 6 } })], edges: [E("s", "r")] };
R.ops5 = dzStudioLike(g5);
R.rien = dzAvCompile({ nodes: [N("o", "Render")], edges: [] });
function dzStudioLike(g) { const ops = []; g.nodes.forEach((n) => { if (n.type === "Recast" || n.type === "VoixVoix") ops.push.apply(ops, dzAvOps(g, n)); }); return ops; }
process.stdout.write(JSON.stringify(R));
"""
debut = B.index("var dzAvUS=x.useState,")
fin = B.index(M._DEF_A, debut)
t = pathlib.Path(tempfile.mkdtemp(prefix="dzavn_"))
(t / "defs.js").write_text(B[debut:fin], encoding="utf-8")
r = subprocess.run(["node", "-e", HARNAIS, str(t / "defs.js")], capture_output=True, text=True, encoding="utf-8")
shutil.rmtree(t, ignore_errors=True)
R = json.loads(r.stdout) if r.returncode == 0 and r.stdout else {}
check("N0 le harnais tourne", bool(R), r.stderr[-300:])
if R:
    u, b = R["recast_voix"]
    check("N1 Rendu existant -> Recast -> Voix -> Rendu : UNE route, /avatar-live/recast, voix:true, le Personnage, la source par job",
          u == "/avatar-live/recast" and b.get("voix") is True and b.get("personnage_id") == "p1" and b.get("source") == {"job_id": "job1"}
          and b.get("modele") == "remplacer" and b.get("resolution") == "720p", str(R["recast_voix"]))
    check("N2 devis : recast sur la durée RÉELLE lue (6 s, pas les 18,4 s par défaut du nœud) + la voix UNE fois",
          R["ops1"] == [{"kind": "recast", "modele": "remplacer", "resolution": "720p", "seconds": 6}, {"kind": "voix_sts", "duration_s": 6}], str(R["ops1"]))
    u, b = R["voix"]
    check("N3 Vidéo UGC -> Voix -> Rendu : /avatar-live/voix avec le Personnage", u == "/avatar-live/voix" and b == {"source": {"job_id": "job2"}, "personnage_id": "p1"}, str(R["voix"]))
    check("N4 devis de la voix seule : la durée de la vidéo UGC (12 s)", R["ops2"] == [{"kind": "voix_sts", "duration_s": 12}], str(R["ops2"]))
    check("N5 Recast sans source : refus clair, rien n'est appelé", R["sans_source"] == {"ok": False, "error": "avatar.noeud.source_manquante"}, str(R["sans_source"]))
    check("N6 Voix sans Personnage : refus clair", R["sans_perso"] == {"ok": False, "error": "avatar.noeud.personnage_manquant"}, str(R["sans_perso"]))
    check("N7 durée inconnue (lue pour un AUTRE job) : 30 s, le maximum du Recast — jamais les 18,4 s factices",
          R["ops5"] == [{"kind": "recast", "modele": "remplacer", "seconds": 30}], str(R["ops5"]))
    check("N8 un graphe sans ces nœuds n'est pas touché (null : les autres branches compilent)", R["rien"] is None)

print("\n[S] le devis serveur des opérations du graphe")
from app.services import pricing  # noqa: E402
e = pricing.estimate({"kind": "campaign", "ops": [{"kind": "recast", "modele": "remplacer", "resolution": "720p", "seconds": 6},
                                                  {"kind": "voix_sts", "duration_s": 6}]})
check("S1 recast 6 s en 720p + voix 6 s = 0,48 $ + 0,024 $ (la dépense réelle relevée sur le backend de preuve)",
      abs(e["total_usd"] - 0.504) < 1e-6, str(e["total_usd"]))

print("\n[T] traduction")
AV = json.loads((RACINE / "frontend" / "shared" / "i18n" / "avatar.json").read_text(encoding="utf-8"))
cles = set(re.findall(r'dzT\("(avatar\.[a-z_.]+)"', B[debut:fin] + "".join(b for _a, b in M.paires(B))))
cles |= {"avatar.noeud.resume_recast", "avatar.noeud.resume_recast_voix"}
check(f"T1 les {len(cles)} clés employées par le maillon sont au dictionnaire, FR et EN", all(k in AV and AV[k].get("en") for k in cles),
      sorted(k for k in cles if k not in AV))
dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
check("T2 le dictionnaire assemblé porte les nœuds", '"avatar.noeud.voix_titre": {"fr": "Voix → voix", "en": "Voice → voice"}' in dico)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
