# -*- coding: utf-8 -*-
"""P8 — SEULE DE LA VIDEO SUR V1, ET UNE ERREUR DE RENDU LISIBLE.

Run : & $PY tests/test_montage_sources.py   (depuis backend/)

LE DEFAUT, MESURE AVANT D'ETRE CORRIGE (journal du 04/09/2026, job de
montage a32009c4 a 15:57:44, base deepotus.db interrogee sur une COPIE) :
les quatre « plans » de la piste V1 de l'utilisateur n'etaient pas des
videos. `sprite2d` range sa planche PNG et `asset3d` son maillage GLB dans
la MEME colonne `final_video_path` qu'un rendu `seedance` ; GET
/api/montage/project retenait les jobs `done` les plus RECENTS dont ce
chemin existe, sans jamais regarder ce que le fichier est. Les 35 rendus
seedance de la base, plus anciens, n'ont jamais ete atteints. Le rendu
mourait ensuite sur `model.glb` — « Invalid data found when processing
input » — et l'utilisateur lisait une tranche de 1200 CARACTERES de
stderr, coupee au milieu de la banniere de compilation de ffmpeg.

CE QUI EST FERME ICI
  [1] CONSTRUCTION AUTOMATIQUE : la boucle de `montage_project` n'accepte en
      V1 qu'une extension de `_VIDEO_EXTS`. Le banc pose en base les QUATRE
      cas reels — un seedance `.mp4`, un sprite2d `.png`, un asset3d `.glb`,
      un quatrieme dont le fichier a disparu — le mp4 etant le PLUS ANCIEN
      des quatre, comme dans la base de l'utilisateur. La liste des job_id
      retenus en V1 est comparee a un LITTERAL d'un seul element.
  [2] la base ne portant QUE des planches et un maillage : `has_assets` est
      FAUX et `clips` est vide — l'ecran garde sa demo au lieu d'ouvrir sur
      quatre cartons de 4 s.
  [3] NON-REGRESSION, l'autre cote de la frontiere : une image POSEE A LA
      MAIN reste valide. `_resolve_src({image})` la resout, et le pre-vol
      l'accepte AUSSI BIEN sur V1 (carton fixe) que sur V2 (incrustation).
      MESURE (04/09/2026) qui fonde ce choix : `ovPicker()` du bundle
      (frontend/patches/son-vfx-montage.js, ~l.3630) propose la rubrique
      « Images (Bibliotheque) » sur TOUTE piste video — le filtre y est
      `trackKind(tr)==="audio"`, pas `tr==="v2"`. Refuser une image sur V1
      casserait un geste que l'interface offre. La regle « seule de la
      video » ne vaut donc QUE pour la construction automatique.
  [4] PRE-VOL de POST /render : les sources sont resolues AVANT la creation
      du JobRecord, et celles qu'aucun demultiplexeur n'ouvrira sont
      refusees en 400 en nommant le libelle du clip ET le fichier. Le banc
      verifie qu'AUCUN job `montage` n'a ete cree par un refus.
  [5] `_run_ffmpeg` : la ligne qui DECIDE passe en tete du message, la
      tranche brute de 1200 caracteres restant derriere. Sans motif trouve,
      le message est identique CARACTERE POUR CARACTERE a l'historique —
      c'est une assertion a part entiere (`erreur_sans_motif_inchangee`),
      sans quoi la mise en tete serait verte a vide.

HUIT MUTATIONS JOUEES le 04/09/2026 (protocole : le service est reecrit sur
disque, le banc relance en processus neuf, le fichier restaure ; script
scratchpad/mut_p8.py). Ligne verte de reference : 30/0.
  M1 `_VIDEO_EXTS` + ".png"  => 23/7, dont `sprite_exclu` ROUGE et
     `glb_exclu` VERTE — les deux discriminent bien.
  M2 `_VIDEO_EXTS` + ".glb"  => 18/12, dont `glb_exclu` ROUGE et
     `sprite_exclu` VERTE. (Les six `prevol_*` rougissent aussi : le pre-vol
     lit la meme table.)
  M3 filtre `_is_video_artifact` retire de `montage_project` => 23/7, les
     sept lignes de la construction automatique ; aucune ligne de rendu.
  M4 pre-vol retire de `montage_render` => 24/6, EXACTEMENT les six lignes
     du refus ; les deux `prevol_accepte_*` et
     `prevol_laisse_passer_une_source_disparue` restent vertes.
  M5 `_ffmpeg_lignes_utiles` rendant toujours [] => 26/4, les quatre lignes
     de position ; `erreur_sans_motif_inchangee` VERTE (autre branche).
  M6 mise en tete INCONDITIONNELLE (motif ou pas) => 29/1,
     `erreur_sans_motif_inchangee` SEULE rouge.
  M7 `v1_non_video` jamais rempli => 29/1,
     `sauvegarde_signale_le_clip_non_video` SEULE rouge.
  M8 pre-vol REFUSANT aussi les images (le zele que la decision 3 interdit)
     => 28/2, `prevol_accepte_image_v1_et_v2_et_audio` et
     `prevol_accepte_a_bien_mis_en_file` rouges. C'est l'autre cote de la
     frontiere, et il est mesure.

CE QUE CE BANC N'AFFIRME PAS
  * Aucun octet n'est encode : `_run_ffmpeg` est REMPLACE par un talon pour
    les deux rendus acceptes. Ce banc mesure le PRE-VOL et le MESSAGE, pas
    la sortie video — c'est test_montage_pistes_rendu.py et
    test_montage_pistes_dyn.py qui rendent pour de vrai, et ils restent la
    garde contre un pre-vol trop zele.
  * La liste blanche est une liste d'EXTENSIONS. Un `.mp4` de zero octet ou
    un `.webm` tronque la passent. MESURE du 04/09/2026 (mediane de 12
    appels, ffprobe 7.x de %LOCALAPPDATA%\\DeepotusVideoGen\\bin) : une sonde
    `ffprobe -select_streams v -show_entries stream=codec_type` coute 52 ms
    par asset ET REND « video » SUR UN PNG — elle n'aurait ecarte aucune des
    trois planches de sprites, seulement le GLB, que l'extension ecarte pour
    0 ms. La sonde n'est donc PAS ajoutee ; le trou restant (fichier video
    corrompu) tombe desormais sur le message lisible de [5], ou
    « Invalid data found » est l'un des cinq motifs remontes en tete.
  * COUT du pre-vol, mesure le 04/09/2026 (scratchpad/cout_prevol.py, base
    sqlite neuve de 24 JobRecord, 15 tours apres chauffe) : 53,2 ms de
    mediane pour 24 clips, soit 2,22 ms par clip — une session sqlite par
    `job_id`. Les MEMES 24 clips sondes par ffprobe : 1345 ms, vingt-cinq
    fois plus, pour un verdict qui n'aurait pas ecarte les planches. Le
    pre-vol n'est pas gratuit : sur une timeline de cent clips il ajoute
    ~0,2 s au clic. Ce n'est PAS optimise (pas de resolution groupee).
  * VERIFICATION sur la base REELLE (une COPIE de deepotus.db + -wal + -shm,
    04/09/2026 18:10, l'application tournant ; DEEPOTUS_DATA_DIR temporaire
    donc sans sauvegarde) : 13 jobs `sprite2d`/`asset3d` sont desormais
    ecartes au journal, et la construction automatique rend QUATRE VRAIES
    videos — 10,04 + 15,97 + 21,63 + 21,23 s, total 68,881 s — la ou elle
    rendait quatre cartons de 4 s (16,0 s exactes de la capture).
  * La SAUVEGARDE de l'utilisateur n'est PAS elaguee de ses clips V1
    non-video ; elle est seulement SIGNALEE (cle `v1_non_video` + warning au
    journal). MESURE sur le fichier reel
    (%LOCALAPPDATA%\\DeepotusVideoGenData\\assets\\montage_saved.json,
    5980 o, 04/09/2026 17:51) : il porte 17 clips — 4 V1 fautifs, mais aussi
    9 segments de sous-titres mot a mot, 1 voix avec fondus et fx, 1 musique
    avec fx, 2 incrustations V2 et un `subs_style`. Elaguer les 4 viderait
    la piste V1, et la garde deja en place (`any(c["tr"] == "v1")`) ferait
    alors repartir la construction depuis la Bibliotheque : 13 clips de
    travail detruits pour en retirer 4, sans retour. Le pre-vol les nomme,
    l'utilisateur les remplace.
  * DETTE NAVIGATEUR, non corrigee ici (cette tache est backend pure) : le
    selecteur d'assets du bundle (`openPicker`, son-vfx-montage.js ~l.3168)
    filtre `/api/jobs` sur `status==="done" && (video_path ||
    final_video_path)` — la MEME faute. Les planches de sprites et le
    maillage restent donc proposes sous « Rendus video » tant que le bundle
    n'est pas patche."""
import asyncio
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp8_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from httpx import AsyncClient, ASGITransport                # noqa: E402
from app.main import app                                    # noqa: E402
from app.services import montage_service as M               # noqa: E402
from app.services.storage import (JobRecord, async_session_factory,  # noqa: E402
                                  init_db)
from app.models.schemas import JobStatus                    # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


_illisibles = 0


def J(resp):
    """Corps JSON, ou un temoin NUMEROTE — ce banc doit ROUGIR, pas mourir
    (faute n°6 du chantier). Le temoin est numerote pour que deux lectures
    ratees ne se valent jamais : un `a == b` entre deux echecs passerait au
    vert."""
    global _illisibles
    try:
        v = resp.json()
    except Exception as e:
        _illisibles += 1
        return {"_illisible": "#%d %s" % (_illisibles, e)}
    return v if isinstance(v, dict) else {"_liste": v}


def api(method, path, **kw):
    async def go():
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=180.0) as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


ROOT = pathlib.Path(TMP)
LIB = ROOT / "lib"
LIB.mkdir(parents=True, exist_ok=True)
(ROOT / "images").mkdir(parents=True, exist_ok=True)
(ROOT / "audio").mkdir(parents=True, exist_ok=True)

# Les fixtures ne sont PAS des medias valides : rien ici n'est decode. Ce que
# le code sous test lit, c'est l'EXTENSION du chemin range en base.
F_MP4 = LIB / "plan_seedance.mp4"
F_PNG = LIB / "sheet.png"
F_GLB = LIB / "model.glb"
F_ABSENT = LIB / "efface.mp4"          # jamais cree : la source disparue
F_MP4.write_bytes(b"\x00faux mp4")
F_PNG.write_bytes(b"\x89PNG\r\n\x1a\nfaux")
F_GLB.write_bytes(b"glTF\x02\x00\x00\x00faux")
CARTON = ROOT / "images" / "carton.png"
CARTON.write_bytes(b"\x89PNG\r\n\x1a\ncarton")
VOIX = ROOT / "audio" / "voix.wav"
VOIX.write_bytes(b"RIFFfauxWAVE")

ID_MP4 = "aaaaaaaa-0000-0000-0000-000000000001"
ID_PNG = "bbbbbbbb-0000-0000-0000-000000000002"
ID_GLB = "cccccccc-0000-0000-0000-000000000003"
ID_GONE = "dddddddd-0000-0000-0000-000000000004"

asyncio.run(init_db())


def pose(jid, provider, path, dur, quand):
    async def go():
        async with async_session_factory() as s:
            s.add(JobRecord(id=jid, provider=provider,
                            status=JobStatus.DONE.value, progress=100,
                            title=provider + " " + jid[:4],
                            image_filename=jid[:8] + ".png",
                            final_video_path=str(path), video_path=str(path),
                            duration_s=dur, completed_at=quand))
            await s.commit()
    asyncio.run(go())


def retire(*jids):
    async def go():
        async with async_session_factory() as s:
            for jid in jids:
                v = await s.get(JobRecord, jid)
                if v is not None:
                    await s.delete(v)
            await s.commit()
    asyncio.run(go())


def n_montage():
    """Combien de JobRecord `montage` la base porte — la file d'attente."""
    async def go():
        from sqlalchemy import select, func
        async with async_session_factory() as s:
            r = await s.execute(select(func.count()).select_from(JobRecord)
                                .where(JobRecord.provider == "montage"))
            return int(r.scalar() or 0)
    return asyncio.run(go())


T0 = datetime(2026, 9, 4, 12, 0, 0)
# L'ORDRE EST LE POINT : le seul vrai plan video est le PLUS ANCIEN des
# quatre, exactement comme dans la base de l'utilisateur (35 seedance jamais
# atteints, les quatre plus recents etant trois planches et un maillage).
pose(ID_MP4, "seedance", F_MP4, 5, T0 - timedelta(hours=3))
pose(ID_PNG, "sprite2d", F_PNG, None, T0 - timedelta(hours=2))
pose(ID_GLB, "asset3d", F_GLB, None, T0 - timedelta(hours=1))
pose(ID_GONE, "template", F_ABSENT, 6, T0)


print("\n[1] construction AUTOMATIQUE — GET /project sans sauvegarde :")
print("    seule de la video atterrit sur V1.")
d = J(api("GET", "/api/montage/project"))
v1_ids = [c.get("src", {}).get("job_id")
          for c in (d.get("clips") or []) if c.get("tr") == "v1"]
check("project_repond", d.get("ok") is True and d.get("saved") is False,
      str(d)[:200])
check("v1_ne_prend_que_la_video", v1_ids == [ID_MP4], str(v1_ids))
# Trois lignes SEPAREES et DISCRIMINANTES : une seule ligne agregee resterait
# verte si l'un des trois repassait. `ID_MP4 in v1_ids` interdit la version
# vacante (un filtre qui jetterait TOUT rendrait ces lignes vertes a vide) ;
# `len(v1_ids) == 1` n'est PAS utilise ici, sinon rouvrir la porte au sprite
# ferait aussi rougir `glb_exclu` et les deux cesseraient de discriminer
# (MESURE : c'etait le cas d'une premiere version, mutations M1/M2 du
# 04/09/2026).
check("sprite_exclu", ID_MP4 in v1_ids and ID_PNG not in v1_ids, str(v1_ids))
check("glb_exclu", ID_MP4 in v1_ids and ID_GLB not in v1_ids, str(v1_ids))
check("chemin_disparu_exclu", ID_MP4 in v1_ids and ID_GONE not in v1_ids,
      str(v1_ids))
# La duree du clip retenu vient du plan video (duration_s=5), pas du repli
# `or 4.0` qui donnait les quatre cartons de 4 s (16,0 s exactes) de la
# capture de l'utilisateur.
v1c = [c for c in (d.get("clips") or []) if c.get("tr") == "v1"]
check("duree_du_plan_video",
      len(v1c) == 1 and round(v1c[0]["end"] - v1c[0]["start"], 3) == 5.0,
      str(v1c)[:200])
check("duree_totale_du_seul_plan", d.get("duration") == 5.0,
      str(d.get("duration")))


print("\n[2] la base ne porte QUE des planches et un maillage :")
print("    has_assets FAUX — l'ecran garde sa demo.")
retire(ID_MP4, ID_GONE)
d2 = J(api("GET", "/api/montage/project"))
check("aucune_video_has_assets_faux",
      d2.get("ok") is True and d2.get("has_assets") is False
      and d2.get("clips") == [], str(d2)[:200])
# Et la Bibliotheque a bien ete LUE : deux jobs `done` y sont, tous deux
# ecartes. Sans cette ligne, un GET qui echouerait avant la boucle rendrait
# la meme chose.
check("sources_comptees_a_zero",
      (d2.get("sources") or {}).get("videos") == 0,
      str(d2.get("sources")))
pose(ID_MP4, "seedance", F_MP4, 5, T0 - timedelta(hours=3))


print("\n[3] NON-REGRESSION — une image posee A LA MAIN reste valide.")
p_img = asyncio.run(M._resolve_src({"image": "carton.png"}))
check("image_posee_a_la_main_reste_valide",
      p_img is not None and pathlib.Path(p_img).name == "carton.png",
      str(p_img))
p_glb = asyncio.run(M._resolve_src({"job_id": ID_GLB}))
check("resolve_src_resout_aussi_le_glb",
      p_glb is not None and pathlib.Path(p_glb).suffix == ".glb", str(p_glb))
# `_resolve_src` ne juge PAS : c'est le pre-vol qui juge. Les deux cotes de
# la frontiere sont donc mesures separement.


# Le talon : ce banc mesure le PRE-VOL, pas l'encodage. Sans lui, chaque
# rendu accepte lancerait un vrai ffmpeg.
_vrai_run_ffmpeg = M._run_ffmpeg


def _talon(cmd, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"talon")
    return out


M._run_ffmpeg = _talon

print("\n[4] PRE-VOL de POST /render.")
BASE = {"name": "p8", "ratio": "9:16", "preview": True,
        "mix": {"dialogue": -6, "musique": -18, "sfx": -12}}
avant = n_montage()
r_ok = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c1", "label": "plan", "start": 0, "end": 4,
     "src": {"job_id": ID_MP4}, "srcIn": 0, "transition": "cut"},
    {"tr": "v1", "id": "c2", "label": "carton fixe", "start": 4, "end": 6,
     "src": {"image": "carton.png"}, "srcIn": 0, "transition": "cut"},
    {"tr": "v2", "id": "c3", "label": "incrustation", "start": 0, "end": 3,
     "src": {"image": "carton.png"}},
    {"tr": "a1", "id": "c4", "label": "voix", "start": 0, "end": 3,
     "src": {"audio": "voix.wav"}}]))
j_ok = J(r_ok)
check("prevol_accepte_image_v1_et_v2_et_audio",
      r_ok.status_code == 200 and bool(j_ok.get("job_id")),
      f"{r_ok.status_code} {r_ok.text[:200]}")
check("prevol_accepte_a_bien_mis_en_file", n_montage() == avant + 1,
      f"{avant} -> {n_montage()}")

avant = n_montage()
r_ko = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c1", "label": "plan", "start": 0, "end": 4,
     "src": {"job_id": ID_MP4}, "srcIn": 0, "transition": "cut"},
    {"tr": "v1", "id": "c2", "label": "3D · tripo", "start": 4, "end": 8,
     "src": {"job_id": ID_GLB}, "srcIn": 0, "transition": "cut"}]))
det = str(J(r_ko).get("detail") or "")
check("prevol_refuse_le_maillage", r_ko.status_code == 400,
      f"{r_ko.status_code} {r_ko.text[:200]}")
check("prevol_nomme_le_clip", "3D · tripo" in det, det[:250])
check("prevol_nomme_le_fichier", "model.glb" in det, det[:250])
# TEMOIN : le message ne deballe pas la timeline entiere — le clip VALIDE
# n'a rien a faire dans un refus. Sans cette ligne, un `detail` qui listerait
# tout passerait les deux precedentes.
check("prevol_ne_nomme_pas_le_clip_valide",
      bool(det) and "plan_seedance.mp4" not in det, det[:250])
check("prevol_aucun_job_cree", n_montage() == avant, f"{avant} -> {n_montage()}")

# Le pre-vol vaut pour TOUTE piste media, pas seulement V1 : un maillage en
# incrustation etait jusqu'ici jete en silence (warning au journal), donc
# invisible pour l'utilisateur.
r_ov = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c1", "label": "plan", "start": 0, "end": 4,
     "src": {"job_id": ID_MP4}, "srcIn": 0, "transition": "cut"},
    {"tr": "v2", "id": "c9", "label": "maillage en overlay", "start": 0,
     "end": 3, "src": {"job_id": ID_GLB}}]))
check("prevol_refuse_le_maillage_en_overlay", r_ov.status_code == 400,
      f"{r_ov.status_code} {r_ov.text[:200]}")

# Une source DISPARUE n'est PAS l'affaire du pre-vol : ce chemin reste celui
# d'avant (echec nomme dans _run), sinon le pre-vol changerait deux choses a
# la fois.
avant = n_montage()
r_gone = api("POST", "/api/montage/render", json=dict(BASE, clips=[
    {"tr": "v1", "id": "c1", "label": "efface", "start": 0, "end": 4,
     "src": {"job_id": ID_GONE}, "srcIn": 0, "transition": "cut"}]))
check("prevol_laisse_passer_une_source_disparue",
      r_gone.status_code == 200 and n_montage() == avant + 1,
      f"{r_gone.status_code} {avant} -> {n_montage()}")

M._run_ffmpeg = _vrai_run_ffmpeg


print("\n[5] _run_ffmpeg — la ligne qui DECIDE passe devant la tranche brute.")
BANNIERE = ("  configuration: --prefix=/ffbuild/prefix --enable-libtheora "
            "--enable-libvo-amrwbenc --enable-libvorbis --enable-libvpx "
            "--enable-libwebp --enable-libx264 --enable-libx265 "
            "--enable-libxml2 --enable-libxvid --enable-libzimg "
            "--enable-libzvbi --enable-lv2 --enable-libmysofa "
            "--enable-openal --enable-opencl --enable-opengl\n") * 6
STDERR_ERR = (
    "ffmpeg version 7.1 Copyright (c) 2000-2024 the FFmpeg developers\n"
    + BANNIERE
    + "[in#2 @ 000001d0] Error opening input: Invalid data found when "
      "processing input\n"
      "Error opening input file C:\\\\assets3d\\\\b6cec0f5\\\\model.glb.\n"
      "Error opening input files: Invalid data found when processing input\n"
      "MARQUEUR_DE_QUEUE_UNIQUE\n")
STDERR_MUET = ("ffmpeg version 7.1\n" + BANNIERE
               + "frame=  120 fps=0.0 q=-1.0 Lsize=  512kB\n")
SEP = "--- journal ffmpeg (fin) ---"


def _faux_subprocess(rc, err):
    def run(cmd, **kw):
        return types.SimpleNamespace(returncode=rc, stdout="", stderr=err)
    return types.SimpleNamespace(run=run,
                                 TimeoutExpired=subprocess.TimeoutExpired)


def _msg(rc, err):
    vrai = M.subprocess
    M.subprocess = _faux_subprocess(rc, err)
    try:
        M._run_ffmpeg(["ffmpeg"], pathlib.Path(TMP) / "jamais_ecrit.mp4")
        return "<AUCUNE EXCEPTION>"
    except RuntimeError as e:
        return str(e)
    finally:
        M.subprocess = vrai


msg = _msg(1, STDERR_ERR)
# Assertions de POSITION, pas de sous-chaine : avant le correctif la ligne
# « Error opening input file » ETAIT dans le message — a l'offset 960, apres
# neuf cents caracteres de drapeaux de compilation. Une simple recherche de
# sous-chaine passait donc au VERT sur le defaut lui-meme (constate en
# jouant ce banc AVANT l'implementation : `erreur_motif_en_tete` et
# `erreur_deux_motifs` etaient vertes). Ce qui se mesure ici, c'est OU.
i_motif = msg.find("Error opening input file")
check("erreur_motif_en_tete", 0 <= i_motif < 200, f"offset {i_motif}")
i_ban = msg.find("--enable-libtheora")
check("erreur_deux_motifs",
      0 <= msg.find("Invalid data found") < i_ban
      and 0 <= msg.find("model.glb") < i_ban,
      f"invalid {msg.find('Invalid data found')}, glb "
      f"{msg.find('model.glb')}, banniere {i_ban}")
# La banniere de compilation n'a rien a faire DEVANT le diagnostic : c'est
# elle qui occupait les neuf cents premiers caracteres de l'ancien message.
check("erreur_banniere_pas_en_tete", i_ban > i_motif >= 0,
      f"banniere {i_ban}, motif {i_motif}")
# ... et la tranche brute est TOUJOURS la, DERRIERE le diagnostic.
i_queue = msg.find("MARQUEUR_DE_QUEUE_UNIQUE")
check("erreur_tranche_conservee_apres_motif",
      i_queue > i_motif >= 0 and "--enable-libtheora" in msg
      and SEP in msg, f"motif {i_motif}, queue {i_queue}")
check("erreur_code_de_retour_cite", msg.startswith("ffmpeg a échoué (1) :"),
      msg[:80])

# L'AUTRE BRANCHE, litteralement : sans motif, le message est celui d'avant,
# caractere pour caractere. Sans cette ligne, une mise en tete
# INCONDITIONNELLE serait verte.
msg2 = _msg(7, STDERR_MUET)
check("erreur_sans_motif_inchangee",
      msg2 == "ffmpeg a échoué (7) : " + STDERR_MUET[-1200:],
      msg2[:120] + " … len=" + str(len(msg2)))


print("\n[6] la SAUVEGARDE n'est pas elaguee — elle est SIGNALEE.")
r_save = api("POST", "/api/montage/save", json={
    "name": "sauvegarde de l'utilisateur", "ratio": "9:16", "duration": 16.0,
    "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
    "clips": [
        {"tr": "v1", "id": "v1_plan", "label": "plan", "start": 0, "end": 4,
         "src": {"job_id": ID_MP4}, "srcIn": 0},
        {"tr": "v1", "id": "v1_sheet", "label": "Particules · Aura magique",
         "start": 4, "end": 8, "src": {"job_id": ID_PNG}, "srcIn": 0},
        {"tr": "a1", "id": "a1_vo", "label": "voix", "start": 0, "end": 3,
         "src": {"audio": "voix.wav"}}]})
check("save_acceptee", r_save.status_code == 200 and J(r_save).get("ok") is True,
      r_save.text[:200])
d3 = J(api("GET", "/api/montage/project"))
ids3 = [c.get("id") for c in (d3.get("clips") or [])]
check("sauvegarde_servie", d3.get("saved") is True, str(d3)[:200])
check("sauvegarde_pas_elaguee", ids3 == ["v1_plan", "v1_sheet", "a1_vo"],
      str(ids3))
check("sauvegarde_signale_le_clip_non_video",
      d3.get("v1_non_video") == ["v1_sheet"], str(d3.get("v1_non_video")))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
