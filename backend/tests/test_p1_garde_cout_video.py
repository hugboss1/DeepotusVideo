# -*- coding: utf-8 -*-
"""P1 #9 (28/09/2026) — GARDE DE COUT VIDEO INCOMPLETE COTE CLIENT.

Defauts MESURES le 28/09 (bundle et backend de 399c118) :
  - le Studio n'envoyait JAMAIS `max_usd` (POST /generate, rendus de layout) :
    seul le plafond serveur de 10 $ protegeait ;
  - le « ≈ $ » du graphe (DzStudioEst) chiffrait la duree BRUTE du noeud (op
    `seedance`) : 15 s affichees pour 10 facturees, 5 s pour Veo qui en
    facture 6 ; HeyGen a 1 minute forfaitaire quel que soit le script ;
  - la vignette du noeud (dzVmCost) lisait une table figee (dzVmRates), bornee
    a 10 s EN DUR, sans bornage natif, sans `video_max_gen_s`, sans tarifs
    surcharges ;
  - l'ecran Tarifs ne reglait ni `video_max_usd_per_request` ni
    `video_max_gen_s`, et son enregistrement REMPLACAIT pricing.json (toute
    valeur posee a la main disparaissait).
Decisions (validees par l'utilisateur le 28/09) : op `video` de l'estimation =
la garde (`_devis_video`) ; le Studio envoie le « ≈ $ » affiche comme
`max_usd` (estimation perimee -> lancement refuse) ; vignette = miroir de la
garde sur GET /video-models (+ max_gen_s, legacy_usd_per_s) ; deux champs dans
Tarifs ; save FUSIONNE.
Temoin : pricing.py et le bundle de BASE (git show). Faute n6 : details par _d().
Run : & $PY tests/test_p1_garde_cout_video.py   (depuis backend/)
"""
import asyncio, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp1gc_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                 # noqa: E402
logger.remove()
from app.services import pricing as PR                    # noqa: E402
from app.api import routes as RT                          # noqa: E402
from app.services.fal_service import VIDEO_MODELS         # noqa: E402

BASE = "399c118"
NODE = shutil.which("node")
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:600]
    except Exception as e:                                  # pragma: no cover
        return f"(detail illisible : {e})"


def _git(path):
    return subprocess.run(["git", "show", f"{BASE}:{path}"], cwd=ROOT, capture_output=True).stdout


def _entre(txt, debut, fin):
    i = txt.find(debut)
    j = txt.find(fin, i)
    return txt[i:j] if i >= 0 and j > i else ""


def _node(js):
    p = pathlib.Path(TMP) / ("n%d.js" % abs(hash(js)))
    p.write_text(js, encoding="utf-8")
    r = subprocess.run([NODE, str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return r.returncode, json.loads(r.stdout), r.stderr
    except Exception:
        return r.returncode, None, (r.stderr or "")[-500:] + (r.stdout or "")[:200]


PF = PR._PRICING_FILE
def _pose(d):
    PF.parent.mkdir(parents=True, exist_ok=True)
    if d is None:
        PF.unlink(missing_ok=True)
    else:
        PF.write_text(json.dumps(d), encoding="utf-8")


def _garde(model, dur, res="1080p", n=1):
    """Le total que la GARDE calcule (routes._devis_video -> estimate campaign), sans le refus 402."""
    ns = types.SimpleNamespace(video_model=model, duration_s=dur, resolution=res)
    return PR.estimate({"kind": "campaign", "ops": [RT._devis_video(ns, n=n)]})["total_usd"]


# temoin : pricing.py de la base, importe dans un module a part
OLDPR = None
try:
    _p = pathlib.Path(TMP) / "pricing_base.py"
    _p.write_bytes(_git("backend/app/services/pricing.py"))
    _sp = importlib.util.spec_from_file_location("app.services._pricing_base_gc", str(_p))
    OLDPR = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(OLDPR)
    OLDPR._PRICING_FILE = PF
except Exception as e:                                      # noqa: BLE001
    print("  (temoin pricing indisponible :", e, ")")
bun = BUNDLE.read_bytes().decode("utf-8")
old_bun = _git("frontend/dist/assets/index-BEOJX8L5.js").decode("utf-8")

print("\n[0] preconditions et temoins (base %s)" % BASE)
check("0.1 node, bundle, bundle de base, pricing de base", bool(NODE) and len(bun) > 10**6 and len(old_bun) > 10**6 and OLDPR is not None, "")
_pose({"video_max_gen_s": 6, "video_usd_per_s": {"seedance-2.5": {"720p": 0.5}}})
if OLDPR is not None:
    OLDPR.save({"flux_image_usd": 0.01})
    _lu = json.loads(PF.read_text(encoding="utf-8"))
else:
    _lu = {}
check("0.2 TEMOIN : a la base, enregistrer les Tarifs EFFACE video_max_gen_s et la table video posees a la main",
      _lu == {"flux_image_usd": 0.01}, _d(_lu))
_pose(None)
_o15 = PR.estimate({"kind": "campaign", "ops": [{"kind": "seedance", "duration_s": 15, "model": "seedance-2.5"}]})["total_usd"]
check("0.3 TEMOIN : l'op `seedance` du ≈ $ d'hier chiffre 15 s la ou la garde en facture 10 (seedance-2.5)",
      _o15 != _garde("seedance-2.5", 15) and abs(_o15 - 15 * 0.473) < 1e-6 and abs(_garde("seedance-2.5", 15) - 10 * 0.473) < 1e-6,
      _d(_o15, _garde("seedance-2.5", 15)))
check("0.4 TEMOIN : a la base, le Studio n'envoie pas max_usd (/generate du compilateur, rendu de layout)",
      old_bun.count("source_graph:e,max_usd:") == 0 and old_bun.count("preview:_pv,max_usd:") == 0
      and old_bun.count("voiceover_enabled:!1,voiceover:dzGraphVoiceover(e)||void 0,source_graph:e})") == 1, "")
check("0.5 TEMOIN : a la base, l'ecran Tarifs n'a aucun des deux plafonds",
      old_bun.count('k:"video_max_usd_per_request"') == 0 and old_bun.count('k:"video_max_gen_s"') == 0, "")
check("0.6 TEMOIN : a la base, la vignette borne a 10 s EN DUR sans bornage natif (Veo 5 s -> 5 s ; la garde en facture 6)",
      old_bun.count("d2=Math.min(Number(p2.durationS)||10,en[1],10)") == 1
      and abs(_garde("veo-3.1-fast-fal", 5) - 6 * PR.video_rate("veo-3.1-fast-fal", "1080p")) < 1e-9, _d(_garde("veo-3.1-fast-fal", 5)))

print("\n[1] backend : l'op `video` EST la garde ; les Tarifs fusionnent ; /video-models sert les plafonds")
ecarts = []
nb = 0
for mid in list(VIDEO_MODELS) + ["", None]:
    for dur in (None, 1, 3, 4.9, 5, 7, 8, 10, 12, 15, 30, -2, "x"):
        for res in (None, "720p", "1080p"):
            for n in (1, 3):
                nb += 1
                try:
                    g = _garde(mid, dur if dur != "x" else None, res or "1080p", n)
                except Exception as e:                      # noqa: BLE001
                    g = "exc " + str(e)[:40]
                v = PR.estimate({"kind": "campaign", "ops": [{"kind": "video", "model": mid, "duration_s": dur,
                                                             "resolution": res or "1080p", "n": n}]})["total_usd"]
                if not isinstance(g, float) or abs(v - g) > 1e-9:
                    ecarts.append((mid, dur, res, n, v, g))
check("1.1 pour %d requetes (modeles x durees x resolutions x n), estimate(video) == la garde (_devis_video)" % nb,
      nb > 800 and not ecarts, _d(ecarts[:4]))
try:
    _inc = PR.estimate({"kind": "video", "model": "inconnu", "duration_s": 7})
except Exception as e:                                      # noqa: BLE001
    _inc = {"erreur": str(e)}
check("1.2 modele inconnu : aucune exception, une ligne chiffree (repli)", len(_inc.get("breakdown") or []) == 1, _d(_inc))
_pose({"video_max_gen_s": 6, "video_usd_per_s": {"seedance-2.5": {"720p": 0.5}}, "zzz_inconnu": 1})
PR.save({"flux_image_usd": 0.01, "video_max_usd_per_request": 3})
_lu = json.loads(PF.read_text(encoding="utf-8"))
check("1.3 les Tarifs FUSIONNENT : les valeurs posees a la main restent, les champs envoyes remplacent",
      _lu.get("video_max_gen_s") == 6 and _lu.get("video_usd_per_s") == {"seedance-2.5": {"720p": 0.5}}
      and _lu.get("flux_image_usd") == 0.01 and _lu.get("video_max_usd_per_request") == 3, _d(_lu))
PF.write_text("{pas du json", encoding="utf-8")
_r = PR.save({"video_max_gen_s": 8})
check("1.4 pricing.json illisible : l'enregistrement repart de vide, sans exception",
      json.loads(PF.read_text(encoding="utf-8")) == {"video_max_gen_s": 8} and _r.get("video_max_gen_s") == 8, _d(PF.read_text(encoding="utf-8")))
_mg = []
for d in (None, {"video_max_gen_s": 6}, {"video_max_gen_s": 0}, {"video_max_gen_s": -1}, {"video_max_gen_s": "x"}):
    _pose(d)
    c = asyncio.run(RT.list_video_models())
    _mg.append([c.get("max_gen_s"), c.get("legacy_usd_per_s")])
check("1.5 /video-models sert max_gen_s EFFECTIF (defaut 10, 6, 0 = aucun, illisible -> 10) et le forfait historique",
      _mg == [[10.0, 0.04], [6.0, 0.04], [0.0, 0.04], [10.0, 0.04], [10.0, 0.04]], _d(_mg))
_pose(None)

print("\n[2] la vignette du noeud : miroir de la garde (banc croise)")
PURE = _entre(bun, "var dzVmCatV=null,", "function DzVmCostTag(")
FALLB = _entre(bun, "var dzVmRates=", "function DzVideoModelSel(")
check("2.0 les aides pures sont dans le bundle, avant DzVmCostTag", len(PURE) > 800 and "dzVmCostOf" in PURE and len(FALLB) > 200, _d(len(PURE), len(FALLB)))
DURS = [None, "", 1, 3, 4, 5, 5.9, 6, 7, 8, 9, 10, 11, 12, 15, 20, 30, -4, "x"]
CAS = []
for reg in (None, {"video_max_gen_s": 6}, {"video_max_gen_s": 0}, {"video_max_gen_s": 4},
            {"video_usd_per_s": {"seedance-2.5": {"720p": 0.5}, "kling-v3-pro": {"*": 0.2, "720p": 0.9}}},  # « * » != max : separe les deux replis
            {"video_usd_per_s": {"seedance-2": {"720p": 0.3, "1080p": 0.7}}, "seedance_usd_per_s": 0.05}):
    _pose(reg)
    cat = asyncio.run(RT.list_video_models())
    CAS.append({"reg": reg, "cat": cat})
_pose(None)
probe = (FALLB + PURE + "\nvar CAS=" + json.dumps(CAS) + ",DURS=" + json.dumps(DURS) + ",out=[];"
         "CAS.forEach(function(c,ic){c.cat.models.map(function(m){return m.id}).concat([\"\"]).forEach(function(mid){"
         "DURS.forEach(function(d){var nd={type:\"Seedance\",props:{model:mid,durationS:d}};"
         "out.push({ic:ic,mid:mid,d:d,sent:Number(d)||10,v:dzVmCostOf(nd,c.cat),f:dzVmCost(nd)})})})});"
         "out.push({mou:[dzVmCostOf({props:{model:\"inconnu\"}},CAS[0].cat),dzVmCostOf({props:{}},null),"
         "dzVmCostOf({props:{}},{models:\"x\"}),dzVmGen([],5,10),dzVmGen([4,6,8],5,0),dzVmGen([4,6,8],5,5),dzVmGen([4,6,8],9,null),"
         "dzVmGen([3,4,5,6,7,8,9,10],2,10),dzVmRate({},\"1080p\"),dzVmRate({\"720p\":.3},\"1080p\"),dzVmRate({\"*\":.1,\"1080p\":.2},\"1080p\"),dzVmRate({\"*\":.1,\"720p\":.3},\"1080p\")]});"
         "process.stdout.write(JSON.stringify(out))")
rc, OUT, err = _node(probe)
check("2.1 la sonde s'execute", rc == 0 and OUT is not None, _d(err))
OUT = OUT or [{}]
mou = OUT[-1].get("mou") if OUT and isinstance(OUT[-1], dict) else None
ecarts = []
nb = 0
for q in OUT[:-1]:
    nb += 1
    reg = CAS[q["ic"]]["reg"]
    _pose(reg)
    attendu = "$%.2f" % _garde(q["mid"] or None, q["sent"])
    if q.get("v") != attendu:
        ecarts.append((reg, q["mid"], q["d"], q.get("v"), attendu))
_pose(None)
check("2.2 pour %d cas (6 reglages x modeles x durees), vignette == la garde, au cent" % nb,
      nb >= 6 * 12 * 19 and not ecarts, _d(len(ecarts), ecarts[:4]))
_diff = [q for q in OUT[:-1] if q["ic"] == 0 and q.get("f") != q.get("v")]
check("2.3 TEMOIN : l'ancienne table (repli) s'ecarte de la garde sur des cas reels (Veo 5 s, 2.5 a 15 s sous plafond 10…)",
      len(_diff) >= 5, _d(len(_diff), _diff[:2]))
check("2.4 mous : modele inconnu / catalogue absent -> null (repli sur l'ancienne table) ; bornage natif et plafond ; taux",
      mou == [None, None, None, None, 6, 4, 8, 3, None, 0.3, 0.2, 0.1], _d(mou))

print("\n[3] le ≈ $ du graphe, la memoire de l'estimation affichee et le plafond du run")
PURE3 = _entre(bun, "function dzStudioOps(", "function DzVideoModelSel(")   # dzStudioOps .. dzRunWith, sans hook
# tache #67 : dzStudioOps consulte dzPinReemploi (un noeud epingle n'est pas facture) -- extrait du bundle livre, pas recopie
PIN3 = _entre(bun, "function dzPinRendu(", "function dzPinNb(") if "function dzPinRendu(" in bun else ""
G = {"nodes": [{"id": "i", "type": "Image", "props": {}}, {"id": "s", "type": "Seedance", "props": {"durationS": 15, "model": "seedance-2.5"}},
               {"id": "t", "type": "Text", "props": {"value": "  Un script de quarante caracteres pile.  "}},
               {"id": "h", "type": "HeyGenAvatar", "props": {}}, {"id": "h2", "type": "HeyGenAvatar", "props": {}},
               {"id": "a", "type": "AvatarMaster", "props": {}}, {"id": "r", "type": "Render", "props": {}}],
     "edges": [{"from": "t", "to": "h", "toPort": "script"}]}
probe3 = ("function Wt(g,id,port){var e=(g.edges||[]).filter(function(x){return x.to===id&&x.toPort===port})[0];"
          "return e?(g.nodes||[]).filter(function(n){return n.id===e.from})[0]:null}\n" + PIN3 + "\n" + PURE3 +
          "\nvar G=" + json.dumps(G) + ",R={};(async function(){R.ops=dzStudioOps(G);var sg=JSON.stringify(R.ops);"
          "R.m0=dzStudioMaxFor(G);dzStudioVuSet(sg,7.4);R.m1=dzStudioMaxFor(G);"
          "var G2=JSON.parse(JSON.stringify(G));G2.nodes[1].props.durationS=8;R.m2=dzStudioMaxFor(G2);"
          "dzStudioVuSet(sg,NaN);R.m3=dzStudioMaxFor(G);dzStudioVuSet(sg,-1);R.m4=dzStudioMaxFor(G);dzStudioVuSet(sg,0);R.m5=dzStudioMaxFor(G);"
          "R.vide=dzStudioOps({nodes:[]});R.mou=[dzStudioOps(null),dzStudioOps({nodes:\"x\"})];"
          "R.run=await dzRunWith(5,async function(){return [dzRunMaxTake(),dzRunMaxTake()]});R.apres=dzRunMaxTake();"
          "try{await dzRunWith(6,async function(){throw new Error(\"x\")})}catch(e){R.err=e.message}R.apres2=dzRunMaxTake();"
          "R.nul=await dzRunWith(null,async function(){return dzRunMaxTake()});"
          "process.stdout.write(JSON.stringify(R))})()")
rc, R3, err = _node(probe3)
check("3.1 la sonde s'execute", rc == 0 and R3 is not None, _d(err))
R3 = R3 or {}
ops = R3.get("ops") or []
_scr = "Un script de quarante caracteres pile."
check("3.2 ops du graphe : image, video (duree du noeud, modele), heygen compte le script CONNECTE (rogne), le texte par defaut sinon, AvatarMaster 1 min",
      ops == [{"kind": "image"}, {"kind": "video", "duration_s": 15, "model": "seedance-2.5"},
              {"kind": "heygen", "chars": len(_scr)}, {"kind": "heygen", "chars": len("From the deep, the prophecy ascends.")},
              {"kind": "heygen", "minutes": 1}], _d(ops))
_tot = PR.estimate({"kind": "campaign", "ops": ops})["total_usd"] if ops else -1
_gen = _garde("seedance-2.5", 15)
_comp = PR.estimate({"kind": "campaign", "ops": [RT._devis_video(types.SimpleNamespace(video_model="seedance-2.5", duration_s=15, resolution="1080p")),
                                                 RT._devis_heygen(types.SimpleNamespace(script="  " + _scr + "  "))]})["total_usd"]
check("3.3 le ≈ $ couvre la garde de CHAQUE voie du run : /generate (video seule) et composition (video + HeyGen du script)",
      _tot >= _gen - 1e-9 and _tot >= _comp - 1e-9 and PR.cost_guard(_gen, _tot) is None and PR.cost_guard(_comp, _tot) is None,
      _d(_tot, _gen, _comp))
check("3.4 memoire : rien d'affiche -> null ; affiche pour CE graphe -> son total ; graphe change / NaN / negatif -> null ; 0 garde 0",
      [R3.get(k) for k in ("m0", "m1", "m2", "m3", "m4", "m5")] == [None, 7.4, None, None, None, 0], _d(R3))
check("3.5 graphe vide ou illisible : aucune op", R3.get("vide") == [] and R3.get("mou") == [[], []], _d(R3.get("vide"), R3.get("mou")))
check("3.6 le plafond du run se prend UNE fois, et plus apres le run (meme sur exception) ; null -> rien",
      R3.get("run") == [5, None] and R3.get("apres") is None and R3.get("err") == "x" and R3.get("apres2") is None and R3.get("nul") is None,
      _d(R3.get("run"), R3.get("apres"), R3.get("apres2"), R3.get("nul")))

print("\n[4] le bundle livre : cablage")
for jet, n in (("function Qh(e){return e.type===\"Seedance\"?r.jsx(DzVmCostTag,{node:e}):", 1),
               ("const ops0=dzStudioOps(graph),sig=JSON.stringify(ops0);", 1),
               ("if(on&&d){setE(d);dzStudioVuSet(sig,d.total_usd)}", 1),
               ("setE({total_usd:0});dzStudioVuSet(sig,0);", 1),
               ("var dzMx=dzStudioMaxFor(o);if(dzMx===null&&!window.__dzfxPreview){", 1),
               ("J=await dzRunWith(dzMx,R.run);", 1),
               ("source_graph:e,max_usd:dzRunMaxTake()})", 1),
               ("preview:_pv,max_usd:dzRunMaxTake()??null})", 1),
               ('{k:"video_max_usd_per_request",l:"Plafond vidéo par requête",u:"$ — 0 = aucun",step:"0.5"}', 1),
               ('{k:"video_max_gen_s",l:"Secondes générées max par clip",u:"s — 0 = durée native",step:"1"}];', 1),
               ("J=await R.run();", 0), ('ops.push({kind:"seedance",duration_s:Number(n.props&&n.props.durationS)||10', 0)):
    check(f"4.x bundle x{n} : {jet[:70]}", bun.count(jet) == n, _d(bun.count(jet)))
check("4.y dzRunMaxTake : trois mentions de code (definition, /generate, layout) ; __dzfxPreview garde son motif",
      bun.count("dzRunMaxTake()") == 3 and bun.count("var _pv=!!window.__dzfxPreview;window.__dzfxPreview=!1;") == 1, _d(bun.count("dzRunMaxTake()")))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
