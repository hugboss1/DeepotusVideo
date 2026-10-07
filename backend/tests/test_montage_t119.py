# -*- coding: utf-8 -*-
"""t119 (07/10/2026) — les deux écarts datés du lot E-A (spec
docs/superpowers/specs/2026-09-22-montage-vs-resolve-app-design.md) :

  E-1 — le panneau Projets devient une GRILLE DE CARTES : vignette (une
        image — celle du milieu, mesuré à l'écran — de la source du premier
        plan vidéo de V1, par `/strip?n=1`), nom,
        date ; « nouveau / dupliquer / ouvrir / supprimer » gardés.
  E-3 — « Ouvrir dans le Montage » d'un épisode de Chapitres : UN CLIP PAR
        SCÈNE et un marqueur par scène. L'écart venait de ce que le job
        `episode` ne stockait aucune durée de scène : le rendu les mesure
        désormais (durée de chaque morceau AVANT la concaténation, c'est elle
        que le démultiplexeur concat ajoute) et les range dans `cost_meta`.
        « Un seul plan » reste à un « Annuler » : la pose et la découpe sont
        deux pas d'historique.

Sections :
  [1] E-3 serveur : `bornes_scenes` (pur), MESURE ffmpeg réelle (trois
      scènes de couleurs distinctes, dont deux avec un son, concaténées par
      `concat_clips` : la couleur lue juste avant / juste après chaque borne
      est celle de la bonne scène), câblage dans `run_episode`, route
      `GET /api/montage/episode-scenes/{job_id}`.
  [2] E-1 serveur : `_project_meta` rend la source vignette du premier plan
      vidéo de V1 (et rien quand il n'y en a pas).
  [3] couche sous node : `dzmScenesPose` (découpe le plan ET son jumeau son,
      marqueurs), `dzmProjVignette` (URL de la vignette).
  [4] écran : la boîte aux lettres demande les scènes, la grille est montée
      — dans la SOURCE de la couche ET dans le bundle servi.

Règle des assertions négatives : chaque « n'est pas » est précédé dans la
MÊME expression du témoin positif qui établit que la mesure a eu lieu.
Run : & $PY tests/test_montage_t119.py   (depuis backend/)
"""
import asyncio
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzt119_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
NODE = shutil.which("node")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def lire(rel):
    p = os.path.join(ROOT, *rel.split("/"))
    try:
        return open(p, "rb").read().decode("utf-8-sig").replace("\r\n", "\n")
    except OSError:
        return ""


def node_json(nom, script):
    if not NODE:
        return {}, "node absent du PATH"
    p = os.path.join(TMP, nom)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(script)
    try:
        r = subprocess.run([NODE, p], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {}, repr(e)
    if r.returncode != 0:
        return {}, "rc=%d %s" % (r.returncode, (r.stderr or "")[-400:])
    lignes = (r.stdout or "").strip().splitlines()
    try:
        d = json.loads(lignes[-1]) if lignes else None
    except ValueError:
        d = None
    return (d if isinstance(d, dict) else {}), ("" if isinstance(d, dict) else repr((r.stdout or "")[-200:]))


async def appel(f, *a):
    try:
        return (200, await f(*a))
    except Exception as e:
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)))


try:
    from app.services import episode_video as ev
    from app.services import montage_service as ms
    from app.services import pipeline as pl
    from app.services.ffmpeg_service import FFmpegMerger as FF
    from app.services.storage import JobRecord, async_session_factory, init_db
except Exception as e:                       # le banc rougit, ne meurt pas
    ev = ms = pl = FF = JobRecord = async_session_factory = init_db = None
    print(f"  (import impossible : {e!r})")
check("x0_services_importes", all(m is not None for m in (ev, ms, pl, FF, JobRecord)))

# ══ [1] E-3 serveur ═══════════════════════════════════════════════════════
print("\n[1] E-3 — les bornes des scènes d'un épisode")
B = getattr(ev, "bornes_scenes", None)
check("1a_bornes_scenes_existe", callable(B))
if callable(B):
    b = B([1.3, 0.9, 2.1], ["Un", "Deux", "x" * 200])
    check("1b_bornes_cumulees_au_millieme",
          [(s["start"], s["end"]) for s in b] == [(0.0, 1.3), (1.3, 2.2), (2.2, 4.3)], b)
    check("1c_texte_court_garde_et_long_tronque_a_80",
          b[0]["texte"] == "Un" and len(b[2]["texte"]) == 80, [s["texte"] for s in b])
    b2 = B([1.0, None, "abc", float("nan"), -2, 0.5], None)
    check("1d_duree_illisible_ou_negative_vaut_zero_et_ne_casse_pas_la_suite",
          len(b2) == 6 and b2[-1]["end"] == 1.5 and all(s["texte"] == "" for s in b2), b2)

FFMPEG = shutil.which("ffmpeg")
check("1e_ffmpeg_sur_le_PATH", bool(FFMPEG), FFMPEG)


def couleur(p, t):
    """La couleur moyenne (r, g, b) de l'image à `t` s, ou None."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", str(p),
                        "-frames:v", "1", "-s", "8x8", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, timeout=60)
    d = r.stdout
    if r.returncode != 0 or len(d) < 192:
        return None
    return tuple(sum(d[i::3]) // 64 for i in range(3))


def proche(c, ref, tol=40):
    return c is not None and all(abs(a - b) <= tol for a, b in zip(c, ref))


if FFMPEG and FF is not None and callable(B):
    W = Path(TMP) / "ep"
    W.mkdir(parents=True, exist_ok=True)
    son = W / "a.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=0.9",
                    str(son)], check=True, timeout=60)
    plans = [("ff0000", 1.3, None), ("00ff00", 0.9, son), ("0000ff", 2.1, son)]
    morceaux, durs = [], []
    for i, (bg, d, a) in enumerate(plans):
        o = W / f"c{i}.mp4"
        FF.scene_clip(None, a, o, dur=d, w=64, h=112, bg=bg)
        morceaux.append(o)
        durs.append(FF.probe_dur(o))
    final = W / "final.mp4"
    FF.concat_clips(morceaux, final)
    bs = B(durs, ["r", "v", "b"])
    refs = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    lu = []
    for i, s in enumerate(bs):
        lu.append((couleur(final, s["start"] + 0.05), couleur(final, s["end"] - 0.05)))
    check("1f_chaque_scene_a_sa_couleur_juste_apres_son_debut_et_juste_avant_sa_fin",
          all(proche(a, refs[i]) and proche(z, refs[i]) for i, (a, z) in enumerate(lu)),
          (durs, bs, lu))
    total = FF.probe_dur(final)
    check("1g_la_derniere_borne_est_la_duree_de_l_episode_a_une_image_pres",
          total > 0 and abs(bs[-1]["end"] - total) <= 1 / 30 + 1e-3, (bs[-1]["end"], total))
    # témoin : des bornes prises sur les durées DEMANDÉES (et non mesurées)
    # tomberaient-elles aussi juste ? La mesure doit au moins valoir celles-ci.
    check("1h_temoin_les_durees_mesurees_sont_celles_des_morceaux",
          all(abs(m - d) < 0.1 for m, (_, d, _) in zip(durs, plans)), durs)

SRC = lire("backend/app/services/pipeline.py")
i0 = SRC.find("async def run_episode")
corps = SRC[i0:SRC.find("async def _episode_video", i0)] if i0 >= 0 else ""
check("1i_run_episode_mesure_chaque_morceau_et_range_les_bornes_dans_cost_meta",
      len(corps) > 1000 and corps.count("self.merger.probe_dur(c) for c in clips") == 1
      and "bornes_scenes(" in corps and '"scenes": ' in corps, len(corps))

R = getattr(ms, "montage_episode_scenes", None)
check("1j_route_episode_scenes_existe", callable(R))
if callable(R) and init_db is not None:
    asyncio.run(init_db())
    sc = [{"start": 0.0, "end": 1.3, "texte": "Un"}, {"start": 1.3, "end": 2.2, "texte": "Deux"}]

    async def _jobs():
        async with async_session_factory() as s:
            s.add(JobRecord(id="ep_ok", provider="episode", status="done", title="Ep",
                            image_filename="x", cost_meta=json.dumps({"chars": 3, "scenes": sc})))
            s.add(JobRecord(id="ep_vieux", provider="episode", status="done", title="Ep",
                            image_filename="x", cost_meta=json.dumps({"chars": 3})))
            s.add(JobRecord(id="ep_casse", provider="episode", status="done", title="Ep",
                            image_filename="x", cost_meta="{pas du json"))
            s.add(JobRecord(id="ep_faux", provider="episode", status="done", title="Ep",
                            image_filename="x", cost_meta=json.dumps(
                                {"scenes": [{"start": 0, "end": 1}, "x", {"start": "a", "end": 2},
                                            {"start": 2, "end": 1}]})))
            s.add(JobRecord(id="studio1", provider="kling", status="done", title="S",
                            image_filename="x", cost_meta=json.dumps({"scenes": sc})))
            await s.commit()
    asyncio.run(_jobs())
    rc = {k: asyncio.run(appel(R, k)) for k in ("ep_ok", "ep_vieux", "ep_casse", "ep_faux",
                                                  "studio1", "inconnu")}
    check("1k_episode_mesure_rend_ses_scenes",
          rc["ep_ok"][0] == 200 and rc["ep_ok"][1].get("scenes") == sc, rc["ep_ok"])
    check("1l_episode_d_avant_ou_meta_illisible_rend_une_liste_vide_pas_une_erreur",
          rc["ep_ok"][0] == 200 and rc["ep_vieux"] == (200, {"ok": True, "job_id": "ep_vieux", "scenes": []})
          and rc["ep_casse"][0] == 200 and rc["ep_casse"][1]["scenes"] == [], rc)
    check("1m_scenes_malformees_ecartees_une_par_une",
          rc["ep_faux"][0] == 200 and rc["ep_faux"][1]["scenes"] == [{"start": 0.0, "end": 1.0, "texte": ""}],
          rc["ep_faux"])
    check("1n_un_rendu_qui_n_est_pas_un_episode_n_a_pas_de_scenes",
          rc["ep_ok"][1].get("scenes") and rc["studio1"] == (200, {"ok": True, "job_id": "studio1", "scenes": []}),
          rc["studio1"])
    check("1o_job_inconnu_404", rc["inconnu"][0] == 404, rc["inconnu"])

# ══ [2] E-1 serveur ═══════════════════════════════════════════════════════
print("\n[2] E-1 — la vignette d'une carte de projet")
PM = getattr(ms, "_project_meta", None)
if callable(PM):
    d = {"id": "m_1", "name": "a", "clips": [
        {"tr": "v2", "start": 0, "end": 2, "src": {"job_id": "haut"}},
        {"tr": "a1", "start": 0, "end": 2, "src": {"job_id": "son"}},
        {"tr": "v1", "start": 5, "end": 7, "src": {"job_id": "tard"}},
        {"tr": "v1", "start": 1, "end": 2, "src": {"image": "i.png"}},
        {"tr": "v1", "start": 2, "end": 5, "src": {"job_id": "tot"}, "srcIn": 3}]}
    m = PM(d)
    check("2a_vignette_du_premier_plan_video_de_v1",
          m.get("thumb") == {"job_id": "tot"} and m.get("clips") == 5, m)
    m2 = PM({"id": "m_2", "clips": [{"tr": "v1", "start": 0, "end": 1, "src": {"image": "i.png"}},
                                    {"tr": "v2", "start": 0, "end": 1, "src": {"job_id": "h"}}]})
    check("2b_sans_plan_video_sur_v1_pas_de_cle_thumb",
          m.get("thumb") and "thumb" not in m2 and m2.get("clips") == 2, m2)
    m3 = PM({"id": "m_3", "clips": [None, "x", {"tr": "v1", "start": "?", "src": {"job_id": 7}},
                                    {"tr": "v1", "start": 4, "src": {"job_id": "j"}}]})
    check("2c_clips_illisibles_ignores", m3.get("thumb") == {"job_id": "j"}, m3)
else:
    check("2a_project_meta_existe", False)

# ══ [3] couche sous node ══════════════════════════════════════════════════
print("\n[3] couche — dzmScenesPose, dzmProjVignette")
JS = lire("frontend/patches/montage.js")
PROBE = r"""
var T=window.DzTracks,out={};
var SC=[{start:0,end:1.3,texte:"Un"},{start:1.3,end:2.2,texte:"Deux"},{start:2.2,end:4.3,texte:"Trois"}];
function base(){return [
  {tr:"v1",id:"v1u1_40",label:"Ep",start:4,end:8.3,src:{job_id:"E"},srcIn:0,transition:"fade",transition_s:.5},
  {tr:"a1",id:"a1u1_40",label:"Ep · son du plan",start:4,end:8.3,src:{job_id:"E"},srcIn:0},
  {tr:"v1",id:"autre",start:0,end:4,src:{job_id:"Z"},srcIn:0},
  {tr:"a2",id:"musique",start:0,end:9,src:{audio:"m.mp3"},srcIn:0}]}
var c0=base(),gel=JSON.stringify(c0);
var r=T.scenesPose(c0,"v1u1_40",SC,[],{});
out.n=r.n;out.refus=r.refus;out.note=r.note;out.intact=JSON.stringify(c0)===gel;
out.v1=r.clips.filter(function(k){return k.tr==="v1"&&k.src.job_id==="E"}).map(function(k){return [k.start,k.end,k.srcIn,k.transition||""]});
out.a1=r.clips.filter(function(k){return k.tr==="a1"}).map(function(k){return [k.start,k.end,k.srcIn]});
out.autres=r.clips.filter(function(k){return k.id==="autre"||k.id==="musique"}).length;
out.ids=r.clips.map(function(k){return k.id});
out.mk=r.markers.map(function(m){return [m.t,m.title,m.note]});
var rt=T.scenesPose([Object.assign({},base()[0],{end:6}),Object.assign({},base()[1],{end:6})],"v1u1_40",SC,[],{});
out.rogne=[rt.n,rt.clips.filter(function(k){return k.tr==="v1"}).map(function(k){return [k.start,k.end]}),rt.markers.map(function(m){return m.t})];
var rs=T.scenesPose([Object.assign({},base()[0],{srcIn:1,speed:2})],"v1u1_40",SC,[],{});
out.vitesse=rs.clips.map(function(k){return [k.start,k.end,k.srcIn]});
var r1=T.scenesPose(base(),"v1u1_40",[SC[0]],[],{});out.une=[r1.n,r1.refus,r1.clips.length,r1.markers.length];
var r0=T.scenesPose(base(),"absent",SC,[],{});out.absent=[r0.n,r0.refus,r0.clips.length];
var rv=T.scenesPose(base(),"v1u1_40",SC,[],{locked:{v1:true}});out.verrou=[rv.n,rv.refus,rv.clips.length,rv.markers.length];
var ra=T.scenesPose(base(),"v1u1_40",SC,[],{locked:{a1:true}});out.verrou_son=[ra.n,ra.clips.filter(function(k){return k.tr==="a1"}).length,ra.clips.filter(function(k){return k.tr==="v1"}).length,ra.note];
var mk0=[{id:"m1",t:9,color:"rouge",title:"x",note:""}];
var rm=T.scenesPose(base(),"v1u1_40",SC,mk0,{});out.mk_garde=[rm.markers.length,rm.markers.some(function(m){return m.id==="m1"})];
out.vign=T.projVignette({thumb:{job_id:"a"},ratio:"9:16"});
out.vign_169=T.projVignette({thumb:{job_id:"a"},ratio:"16:9"});
out.vign_vide=[T.projVignette({}),T.projVignette(null),T.projVignette({thumb:"x"})];
console.log(JSON.stringify(out));
"""
D, why = node_json("t119_couche.js", '"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + JS + "\n" + PROBE)
check("3a_la_couche_s_execute_sous_node", bool(D) and "n" in D, why)
if D:
    check("3b_trois_scenes_deux_coupes_sur_le_plan_ET_son_jumeau",
          D["n"] == 2 and D["v1"] == [[4, 5.3, 0, "fade"], [5.3, 6.2, 1.3, "cut"], [6.2, 8.3, 2.2, "cut"]]
          and D["a1"] == [[4, 5.3, 0], [5.3, 6.2, 1.3], [6.2, 8.3, 2.2]], (D["v1"], D["a1"]))
    check("3c_entree_intacte_autres_clips_gardes_ids_uniques",
          D["n"] == 2 and D["intact"] and D["autres"] == 2 and len(set(D["ids"])) == len(D["ids"]) == 8, D["ids"])
    check("3d_un_marqueur_par_scene_titre_et_texte",
          D["mk"] == [[4, "Scène 1", "Un"], [5.3, "Scène 2", "Deux"], [6.2, "Scène 3", "Trois"]], D["mk"])
    check("3e_note_dit_le_nombre_de_plans_et_annuler",
          D["n"] == 2 and "3 plans" in D["note"] and "Annuler" in D["note"], D["note"])
    check("3f_plan_rogne_coupe_et_marque_seulement_dans_ses_bornes",
          D["rogne"] == [1, [[4, 5.3], [5.3, 6]], [4, 5.3]], D["rogne"])
    check("3g_vitesse_et_srcin_suivent_la_loi_de_la_lame",
          D["vitesse"] == [[4, 4.15, 1], [4.15, 4.6, 1.3], [4.6, 8.3, 2.2]], D["vitesse"])
    check("3h_une_seule_scene_ou_clip_absent_rien_ne_bouge",
          D["une"] == [0, "une_scene", 4, 0] and D["absent"] == [0, "clip", 4], (D["une"], D["absent"]))
    check("3i_piste_video_verrouillee_refus_entier",
          D["verrou"] == [0, "verrou", 4, 0], D["verrou"])
    check("3j_piste_du_son_verrouillee_le_plan_est_coupe_le_son_non_et_c_est_dit",
          D["verrou_son"][0] == 2 and D["verrou_son"][1] == 1 and D["verrou_son"][2] == 4
          and "verrouill" in D["verrou_son"][3], D["verrou_son"])
    check("3k_marqueurs_existants_gardes", D["mk_garde"] == [4, True], D["mk_garde"])
    check("3l_vignette_url_strip_une_image_au_format_du_projet",
          D["vign"] == "/api/montage/strip?src=%7B%22job_id%22%3A%22a%22%7D&n=1&w=54&h=96"
          and D["vign_169"] == "/api/montage/strip?src=%7B%22job_id%22%3A%22a%22%7D&n=1&w=160&h=90"
          and D["vign_vide"] == ["", "", ""], (D["vign"], D["vign_169"], D["vign_vide"]))

# ══ [4] écran ═════════════════════════════════════════════════════════════
print("\n[4] écran — boîte aux lettres et grille, source ET bundle")
SV = lire("frontend/patches/son-vfx-montage.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
CSS = lire("frontend/dist/shared/montage.css")
for nom, t in (("source", SV), ("bundle", BUN)):
    check(f"4a_{nom}_la_boite_aux_lettres_demande_les_scenes_de_l_episode",
          len(t) > 100_000 and t.count('"/api/montage/episode-scenes/"+encodeURIComponent(') == 1
          and t.count("DzTracks.scenesPose(") == 1, len(t))
for nom, t in (("source", JS), ("bundle", BUN)):
    check(f"4b_{nom}_la_liste_des_projets_est_une_grille_de_cartes_a_vignette",
          len(t) > 100_000 and t.count('className:"dzm-projgrid"') == 1
          and t.count('className:"dzm-projcard"') == 1 and t.count("var vg=dzmProjVignette(p);") == 1, len(t))
check("4c_feuille_grille_et_vignette",
      ".dzsvm .dzm-projgrid{" in CSS and ".dzsvm .dzm-projthumb{" in CSS, len(CSS))

print(f"\n=== {ok} passed, {fail} failed ===")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
