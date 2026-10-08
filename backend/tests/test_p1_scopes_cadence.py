# -*- coding: utf-8 -*-
"""P1 #8 (28/09/2026) — SCOPES SANS VITESSE / STAB / AJUSTEMENT, LECTEUR A 30 I/S FIXE.

Defauts MESURES le 28/09 (couche de ac13ca6 executee sous node) :
  - dzmScwBody (corps de POST /api/montage/scopes) ne portait que dzmGlCadre :
    un plan V1 en retime x2 (blend), stabilise, ou sous un clip J1 actif
    donnait aux scopes le cadre {ratio, t_local, dur} SANS speed / retime /
    fps, stab, adjust / t_global -- alors que l'image etalonnee du lecteur
    (dzmGlBody) les envoyait et que la route /scopes les lit deja
    (_cadre_of -> _cadre_neufs, _cadre_stab, _adjust_graph) : les scopes
    mesuraient l'image BRUTE ;
  - cadre.fps valait DZM_GL_FPS = 30 quel que soit le preset (GIF 12 i/s) ou
    la cadence choisie (60) ;
  - dzmScwVeilleFs n'ecoutait que « fullscreenchange » et la couche lisait
    `document.fullscreenElement` seul.
Decisions : un cadre UNIQUE (dzmGlNeufs) pour les deux corps ; la cadence est
celle que _deliver_resolve donnera au rendu FINAL (dzmGlFps, lue dans les
reglages de livraison de l'hote et dans GET /deliver-presets, dont chaque
integre dit desormais fps et gif) ; les quatre noms prefixes.
Temoin : la couche de la base (git show BASE) sous le meme shim -- elle doit
rougir la ou la nouvelle est verte. Faute n6 : details par _d().
Run : & $PY tests/test_p1_scopes_cadence.py   (depuis backend/)
"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp1sc_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
# t141 (08/10/2026) : la couche appelle dzT AU CHARGEMENT (Bibliotheque traduite) ; _node pose
# AIDE.PRELUDE_DZT (dictionnaire + dzT en francais) APRES le `var window={}` du shim. Sans effet sur la couche de base.
sys.path.insert(0, str(BACKEND / "tests"))
import _i18n_l1_aide as AIDE                             # noqa: E402
from loguru import logger                                 # noqa: E402
logger.remove()
from app.services import montage_service as MS            # noqa: E402

BASE = "ac13ca6"
NODE = shutil.which("node")
SRC = ROOT / "frontend" / "patches" / "montage.js"
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


def _node(src_txt, probe):
    """La couche sous le shim du banc d'edition (strict, window vide) + la sonde ; (code, json|None, stderr)."""
    p = pathlib.Path(TMP) / ("shim_%d.js" % abs(hash(probe + src_txt[:64])))
    p.write_text('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + AIDE.PRELUDE_DZT + src_txt + "\n" + probe, encoding="utf-8")
    r = subprocess.run([NODE, str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return r.returncode, json.loads(r.stdout), r.stderr
    except Exception:
        return r.returncode, None, (r.stderr or "")[-400:] + (r.stdout or "")[:200]


# L'API telle que la route la sert (appel direct de la fonction de route, base de presets maison VIDE puis posee).
API0 = asyncio.run(MS.montage_deliver_presets())
MAISON = [{"id": "m_a", "label": "A", "base": "master_1080", "fps": 25},
          {"id": "m_g", "label": "G", "base": "gif_480", "fps": 60},
          {"id": "m_n", "label": "N", "base": "webm_vp9"},
          {"id": "m_x", "label": "X", "base": "inexistant", "fps": 24}]
API = dict(API0, presets=MAISON)

PROBE = r"""
var T=window.DzTracks,R={},API=__API__,API0=__API0__;
var RT={tr:"v1",id:"r",start:0,end:4,src:{job_id:"j"},srcIn:0,speed:2,retime:"blend"};
var RF={tr:"v1",id:"f",start:0,end:4,src:{job_id:"j"},srcIn:0,speed:.5,retime:"flow",effects:[{type:"negate"}]};
var SB={tr:"v1",id:"s",start:0,end:4,src:{job_id:"j"},srcIn:0,stab:{on:true,smooth:20}};
var VP={tr:"v1",id:"v",start:0,end:4,src:{job_id:"j"},srcIn:0};
var FX={tr:"v1",id:"x",start:2,end:6,src:{job_id:"j"},srcIn:1,effects:[{type:"negate"}]};
var J1={tr:"j1",id:"a",kind:"adjust",start:0,end:4,effects:[{type:"blur"}]};  /* un effet du MOTEUR : un type inconnu est ecarte par la route */
var CL=[VP,J1];
function eq(a,b){return JSON.stringify(a)===JSON.stringify(b)}
R.has=[typeof T.glFps,typeof T.glNeufs,typeof T.scwFsEl,Array.isArray(T.SCW_FS_EV)];
/* [1] le corps des scopes porte LE cadre de l'image etalonnee (memes clips, meme cadence) */
var cas=[[RT,1,[RT]],[RF,1,[RF]],[SB,1,[SB]],[VP,1,CL],[FX,3,[FX]],[VP,1,[VP]]];
R.scw=cas.map(function(q){var s=T.scwBody(q[0],q[1],"9:16",320,1,q[2],60),g=T.glBody(q[0],q[1],"9:16",q[2],60);
  return {s:s,g:g,same:!!s&&!!g&&eq(s.cadre,g.cadre)&&eq(s.src,g.src)&&s.t===g.t}});
/* plan sans rien de neuf : le corps d'hier, octet pour octet (cle de cache du serveur) */
R.plain=[T.scwBody(VP,1,"9:16",320,1,[VP],60),T.scwBody(FX,3,"16:9",500,2),T.scwBody(null,1,"9:16",320,1,[],60)];
/* [2] la cadence */
R.fpsRT=[T.glBody(RT,1,"9:16",[RT],60).cadre.fps,T.glBody(RT,1,"9:16",[RT],12).cadre.fps,T.glBody(RT,1,"9:16",[RT]).cadre.fps,
  T.glBody(RT,1,"9:16",[RT],"x").cadre.fps,T.glBody(RT,1,"9:16",[RT],0).cadre.fps,T.glBody(RT,1,"9:16",[RT],24.5).cadre.fps,
  T.glBody(RT,1,"9:16",[RT],true).cadre.fps];
var ids=[null,"","zzz","m_a","m_g","m_n","m_x"].concat(API.builtins.map(function(b){return b.id})),fpss=[null,24,25,30,60,48,"60","",true,12];
R.croise=[];ids.forEach(function(p){fpss.forEach(function(f){var del={};if(p!==null)del.preset=p;if(f!==null)del.fps=f;
  R.croise.push({del:del,pay:T.deliverPayload({},del),fps:T.glFps(del,API)})})});
R.api0=[T.glFps({},API0),T.glFps({preset:"gif_480"},API0),T.glFps({preset:"gif_480",fps:60},API0),T.glFps({fps:25},API0)];
R.mou=[T.glFps(null,null),T.glFps({fps:60},null),T.glFps({fps:48},null),T.glFps({preset:"x"},{builtins:"x"}),
  T.glFps({},{builtins:[null,{id:"b",fps:"x"}]}),T.glFps({},{builtins:[{id:"g",fps:0,gif:true}]}),T.glFps({},{builtins:[{id:"b",fps:500}]}),
  T.glFps({preset:"zz"},{builtins:[{id:"b",fps:25},{id:"c",fps:60}]}),T.glFps({preset:"m"},{builtins:[{id:"b",fps:25},{id:"g",fps:12,gif:true}],presets:[{id:"m",base:"g",fps:60}]})];
/* [3] le plein ecran prefixe */
var ev=[],rm=[],fn=function(){};var ote=T.scwVeilleFs({addEventListener:function(n,f){ev.push([n,f===fn])},
  removeEventListener:function(n,f){rm.push([n,f===fn])}},fn);ote();R.fs=[ev,rm];
R.fsEl=typeof T.scwFsEl==="function"?[T.scwFsEl({fullscreenElement:"a",webkitFullscreenElement:"b"}),T.scwFsEl({webkitFullscreenElement:"b"}),
  T.scwFsEl({mozFullScreenElement:"c"}),T.scwFsEl({msFullscreenElement:"d"}),T.scwFsEl({}),T.scwFsEl(null)]:null;
process.stdout.write(JSON.stringify(R));
""".replace("__API0__", json.dumps(API0)).replace("__API__", json.dumps(API))

new_src = SRC.read_bytes().decode("utf-8-sig")
old_src = subprocess.run(["git", "show", f"{BASE}:frontend/patches/montage.js"], cwd=ROOT,
                         capture_output=True).stdout.decode("utf-8-sig")

print("\n[0] preconditions et temoin (couche de %s)" % BASE)
check("0.1 node, couche courante, couche de base", bool(NODE) and len(new_src) > 100000 and len(old_src) > 100000,
      _d(NODE, len(new_src), len(old_src)))
rc, N, err = _node(new_src, PROBE)
check("0.2 la sonde s'execute sur la couche courante", rc == 0 and N is not None, _d(err))
rco, O, erro = _node(old_src, PROBE.replace("T.glFps(", "(T.glFps||function(){return null})("))
check("0.3 la sonde s'execute sur la couche de base (temoin)", rco == 0 and O is not None, _d(erro))
N = N or {}
O = O or {}

def _cadres(R):
    return [(q or {}).get("s", {}) and (q.get("s") or {}).get("cadre") for q in (R.get("scw") or [])]

check("0.4 TEMOIN : a la base, les scopes d'un plan en retime / stabilise / sous J1 n'ont ni speed, ni stab, ni adjust",
      [sorted(c or {}) for c in _cadres(O)[:4]] == [["dur", "ratio", "t_local"]] * 4, _d(_cadres(O)[:4]))
check("0.5 TEMOIN : a la base, la cadence vaut 30 quelle que soit celle demandee (60, 12)",
      (O.get("fpsRT") or [])[:2] == [30, 30], _d(O.get("fpsRT")))
check("0.6 TEMOIN : a la base, une seule ecoute (fullscreenchange)",
      [e[0] for e in (O.get("fs") or [[]])[0]] == ["fullscreenchange"], _d(O.get("fs")))

print("\n[1] le corps des scopes porte LE cadre de l'image etalonnee")
check("1.0 exports glFps / glNeufs / scwFsEl / SCW_FS_EV", N.get("has") == ["function", "function", "function", True], _d(N.get("has")))
sc = N.get("scw") or [{}] * 6
check("1.1 retime x2 blend : scopes == image etalonnee, speed 2, retime blend, fps 60",
      sc[0].get("same") and (sc[0].get("s") or {}).get("cadre", {}).get("speed") == 2
      and sc[0]["s"]["cadre"].get("retime") == "blend" and sc[0]["s"]["cadre"].get("fps") == 60, _d(sc[0]))
check("1.2 retime x0,5 flow + effet : scopes == image etalonnee (effets et cadre)",
      sc[1].get("same") and sc[1]["s"]["cadre"].get("retime") == "flow" and sc[1]["s"].get("effects") == [{"type": "negate"}], _d(sc[1]))
check("1.3 stabilise : scopes == image etalonnee, stab normalise (on, smooth 20)",
      sc[2].get("same") and (sc[2]["s"]["cadre"].get("stab") or {}).get("on") is True
      and sc[2]["s"]["cadre"]["stab"].get("smooth") == 20, _d(sc[2]))
check("1.4 sous un J1 actif : scopes == image etalonnee, adjust + t_global",
      sc[3].get("same") and len(sc[3]["s"]["cadre"].get("adjust") or []) == 1 and sc[3]["s"]["cadre"].get("t_global") == 1, _d(sc[3]))
check("1.5 effet seul (tete 3 dans [2,6[) : scopes == image etalonnee, rien de neuf dans le cadre",
      sc[4].get("same") and sorted(sc[4]["s"]["cadre"]) == ["dur", "ratio", "t_local"], _d(sc[4]))
check("1.6 plan brut : l'image etalonnee ne part pas (null), les scopes partent avec le cadre d'hier",
      sc[5].get("g") is None and sorted((sc[5].get("s") or {}).get("cadre") or {}) == ["dur", "ratio", "t_local"], _d(sc[5]))
check("1.7 sans rien de neuf, le corps des scopes est OCTET POUR OCTET celui de la base (cle de cache)",
      N.get("plain") == O.get("plain") and (N.get("plain") or [None])[0] is not None and (N.get("plain") or [0, 0, 1])[2] is None,
      _d(N.get("plain"), O.get("plain")))
# la route lit ce que la couche envoie : _cadre_of garde speed / retime / fps / stab / adjust / t_global
for i, nom in ((0, "retime"), (2, "stab"), (3, "adjust")):
    c_in = ((sc[i].get("s") or {}).get("cadre")) or {}
    try:
        c_out = MS._cadre_of(c_in)
    except Exception as e:                                  # noqa: BLE001
        c_out = {"erreur": str(e)}
    garde = {k: c_out.get(k) for k in ("speed", "retime", "fps", "t_global") if k in c_in}
    check(f"1.8 route : _cadre_of garde les champs neufs envoyes par les scopes ({nom})",
          all(k in c_out for k in c_in if k not in ("reframe", "dz")) and garde == {k: c_in[k] for k in garde}
          and len(c_out.get("adjust") or []) == len(c_in.get("adjust") or [])
          and ("stab" in c_out) == bool((c_in.get("stab") or {}).get("on")),   # normalise : presence = allume
          _d(c_in, c_out))

print("\n[2] la cadence : celle du rendu FINAL (banc croise avec _deliver_resolve)")
check("2.0 la route sert fps et gif pour chaque integre, egaux a _DELIVER",
      all(b.get("fps") == MS._DELIVER[b["id"]]["fps"] and b.get("gif") is bool(MS._DELIVER[b["id"]].get("gif"))
          for b in API0["builtins"]) and len(API0["builtins"]) == len(MS._DELIVER), _d(API0["builtins"]))
cr = N.get("croise") or []
ecarts = []
for q in cr:
    pay = q.get("pay") or {}
    attendu = MS._deliver_resolve(pay.get("preset"), pay.get("fps"), MAISON)["fps"]
    if q.get("fps") != attendu:
        ecarts.append((q.get("del"), pay, q.get("fps"), attendu))
check("2.1 pour %d reglages (presets integres, maison, inconnus x cadences), dzmGlFps == _deliver_resolve(payload)" % len(cr),
      len(cr) >= 150 and not ecarts, _d(len(cr), ecarts[:4]))
check("2.2 la table couvre GIF (12), maison 25, surcharge 60 et le repli master 30",
      {q.get("fps") for q in cr} >= {12, 25, 30, 60}, _d(sorted({q.get("fps") for q in cr})))
check("2.3 base de presets maison vide : master 30, GIF 12 (la surcharge 60 ignoree), cadence 25 choisie",
      N.get("api0") == [30, 12, 12, 25], _d(N.get("api0")))
check("2.4 mous : api absente -> 30 ou la cadence choisie valide ; integre illisible -> 30 ; preset inconnu -> le PREMIER integre (25, pas le repli) ; maison sur base GIF -> 12",
      N.get("mou") == [30, 60, 30, 30, 30, 30, 30, 25, 12], _d(N.get("mou")))
check("2.5 cadre.fps du retime : 60 et 12 demandes passent, absent / illisible / 0 / 24,5 / booleen -> 30",
      N.get("fpsRT") == [60, 12, 30, 30, 30, 30, 30], _d(N.get("fpsRT")))

print("\n[3] le plein ecran prefixe")
EV = ["fullscreenchange", "webkitfullscreenchange", "mozfullscreenchange", "MSFullscreenChange"]
fs = N.get("fs") or [[], []]
check("3.1 les quatre noms sont ecoutes, avec la MEME fonction", [e[0] for e in fs[0]] == EV and all(e[1] for e in fs[0]), _d(fs))
check("3.2 le retrait retire les quatre, avec la meme fonction", [e[0] for e in fs[1]] == EV and all(e[1] for e in fs[1]), _d(fs))
check("3.3 l'element plein ecran lu sous les quatre noms, standard d'abord ; aucun / doc absent -> null",
      N.get("fsEl") == ["a", "b", "c", "d", None, None], _d(N.get("fsEl")))

print("\n[4] la couche et le bundle livre")
check("4.1 la couche ne lit plus `fullscreenElement` qu'a travers dzmScwFsEl (x1 : la table des noms)",
      new_src.count("fullscreenElement") == 1 and new_src.count("dc.fullscreenElement") == 0
      and new_src.count("dzmScwCible(f,dzmScwFsEl(dc))") == 1 and new_src.count("dzmScwCible(hote,dzmScwFsEl(dc))") == 1,
      _d(new_src.count("fullscreenElement")))
check("4.2 les deux composants passent la cadence dzmGlFps(o.dlv,o.dapi) (image etalonnee, scopes avec les plans)",
      new_src.count("dzmGlBody(c,o.head,o.ratio,o.clips,dzmGlFps(o.dlv,o.dapi))") == 1
      and new_src.count("g?g.devicePixelRatio:1,o.clips,dzmGlFps(o.dlv,o.dapi))") == 1, "")
bun = BUNDLE.read_bytes().decode("utf-8")
check("4.3 bundle : l'hote passe dzDel / dzApi aux deux montages (x2), une fois chacun",
      bun.count("vzoom:vzoom,ratio:proj.ratio,dlv:dzDel,dapi:dzApi}") == 1
      and bun.count("r.jsx(DzTracks.Scopes,{clips:clips,head:ph,playing:playing,ratio:proj.ratio,dlv:dzDel,dapi:dzApi})") == 1
      and bun.count("dlv:dzDel,dapi:dzApi") == 2, _d(bun.count("dlv:dzDel,dapi:dzApi")))
check("4.4 bundle : la couche livree est celle du depot (dzmGlNeufs, dzmGlFps, DZM_SCW_FS_EV x1)",
      bun.count("function dzmGlNeufs(") == 1 and bun.count("function dzmGlFps(") == 1 and bun.count("var DZM_SCW_FS_EV=") == 1, "")
i_dd, i_mt = bun.find("var stDzDel="), bun.find("function DzMontage(")
i_fin = bun.find("\nfunction ", i_mt + 10)
check("4.5 bundle : dzDel / dzApi sont declares DANS DzMontage, avant les deux montages",
      0 <= i_mt < i_dd < bun.find("dlv:dzDel,dapi:dzApi") and bun.rfind("dlv:dzDel,dapi:dzApi") < i_fin
      and bun.count("var stDzApi=") == 1, _d(i_mt, i_dd, i_fin))
# MESURE sur 8799 le 28/09 : preset GIF memorise, fps restait 30 -- dzApi n'etait lu qu'a l'ouverture du popover de rendu
check("4.6 bundle : la liste des presets est chargee aussi au MONTAGE de l'hote tant qu'elle manque (temoin : .bak / base)",
      bun.count('x.useEffect(function(){if(pop!=="render"&&dzApi)return;var alive=!0;') == 1
      and bun.count('x.useEffect(function(){if(pop!=="render")return;var alive=!0;') == 0, "")

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
