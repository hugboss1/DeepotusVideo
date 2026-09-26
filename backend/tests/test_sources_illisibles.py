# -*- coding: utf-8 -*-
"""Correctif du 26/09/2026 — sources VIDES ou ILLISIBLES.

CONSTAT (mesure du 25/09/2026) : un upload de juillet
`assets/outputs/uploads/demo complete videogen brute.mp4` faisait 0 OCTET ;
`POST /api/videos/upload` l'avait accepte et avait cree un job « done »
(`provider ugc`, `duration_s` None). Pose sur la timeline, il faisait echouer
un rendu Montage avec la tranche brute de stderr ffmpeg (« moov atom not
found »). Le pre-vol P8 de `/render` ne jugeait que l'EXTENSION.

Ce banc tient :
  [1] l'UPLOAD video : 0 octet -> 415, tronque -> 415, fichier supprime,
      aucun job ; temoins : mp4 valide -> 200 + job, son seul -> 200 (la
      route l'acceptait avant : garde) ;
  [2] l'UPLOAD audio : meme refus, et un fichier existant du meme nom n'est
      PAS ecrase par un envoi illisible ;
  [3] le PRE-VOL de `/render` : une source resolue vide ou illisible est
      NOMMEE (libelle, piste, temps, fichier, raison), sur V1 comme sur A1,
      AUCUN job cree ; temoin deux clips valides -> 200 ; source disparue ->
      chemin d'avant (200) ;
  [4] le CACHE de la sonde : deux rendus = UNE sonde ; source modifiee
      (mtime) -> nouvelle sonde.

En-tete recopie de test_montage_l6_voix.py (env, check, J, TestClient `with`,
nettoyage final) : dossier de donnees NEUF par execution, toute lecture gardee
(faute n6 : le DETAIL est evalue AVANT le court-circuit de la condition, il
ne doit donc jamais lever). `_run_ffmpeg` est remplace par un talon : ce banc
mesure le pre-vol, pas l'encodage. Aucune depense.
Run : & $PY tests/test_sources_illisibles.py   (depuis backend/)
"""
import os, sys, tempfile, subprocess, pathlib, shutil, sqlite3
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzsrcill_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def J(resp):
    """Corps JSON, ou {} — le banc doit ROUGIR, pas mourir sur un .json() nu."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {"_liste": v}


class _Temoin:
    status_code = -1
    text = ""
    def json(self):
        return {}


c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

from app.services import montage_service as MS           # noqa: E402
from app.services.effects_preview import ffmpeg_bin      # noqa: E402
from app.config import settings                          # noqa: E402

FF = ffmpeg_bin()
SRC = pathlib.Path(TMP) / "sources"
SRC.mkdir(parents=True, exist_ok=True)
UP = settings.outputs_path / "uploads"
ADIR = settings.images_path.parent / "audio"
DB = pathlib.Path(TMP) / "t.db"


def FAB(nom, args):
    """Fabrique une source par ffmpeg ; rend le chemin ou None (jamais d'exception)."""
    p = SRC / nom
    try:
        subprocess.run([FF, "-y", "-loglevel", "error", *args, str(p)],
                       capture_output=True, timeout=60, check=False)
    except Exception as e:                               # noqa: BLE001
        print("  (ffmpeg injoignable : %s)" % e)
        return None
    return p if p.is_file() and p.stat().st_size > 0 else None


def POST(path, **kw):
    try:
        return c.post(path, **kw)
    except Exception as e:                               # noqa: BLE001
        print("  (POST %s a leve : %r)" % (path, e))
        return _Temoin()


def UPLOAD(nom, octets, route="/api/videos/upload", mime="video/mp4"):
    return POST(route, files={"file": (nom, octets, mime)})


def N_JOBS(provider=None):
    """Compte des lignes `jobs` (toutes, ou d'un provider) ; -1 si illisible."""
    try:
        con = sqlite3.connect(str(DB))
        try:
            if provider:
                r = con.execute("select count(*) from jobs where provider=?",
                                (provider,)).fetchone()
            else:
                r = con.execute("select count(*) from jobs").fetchone()
            return int(r[0])
        finally:
            con.close()
    except Exception as e:                               # noqa: BLE001
        print("  (lecture de la base : %s)" % e)
        return -1


def UPS():
    try:
        return sorted(p.name for p in UP.iterdir()) if UP.is_dir() else []
    except Exception:                                    # noqa: BLE001
        return ["<illisible>"]


def LIRE(p):
    try:
        return pathlib.Path(p).read_bytes()
    except Exception:                                    # noqa: BLE001
        return b""


MP4 = FAB("valide.mp4", ["-f", "lavfi", "-i", "testsrc2=s=64x64:r=10:d=2",
                         "-f", "lavfi", "-i", "sine=f=440:d=2",
                         "-c:v", "libx264", "-pix_fmt", "yuv420p",
                         "-c:a", "aac", "-shortest"])
WAV = FAB("son.wav", ["-f", "lavfi", "-i", "sine=f=330:d=1"])
MP4B = LIRE(MP4) if MP4 else b""
WAVB = LIRE(WAV) if WAV else b""
check("fixture_mp4_valide_fabrique_et_plus_long_que_2000_octets",
      len(MP4B) > 4000, f"{len(MP4B)} o")
check("fixture_wav_fabrique", len(WAVB) > 1000, f"{len(WAVB)} o")
TRONQUE = MP4B[:2000]


print("\n[1] UPLOAD video — vide ou illisible refuse, valide inchange.")
av_jobs, av_ups = N_JOBS(), UPS()
r0 = UPLOAD("vide total.mp4", b"")
d0 = str(J(r0).get("detail") or "")
check("upload_0_octet_415", r0.status_code == 415, f"{r0.status_code} {r0.text[:200]}")
check("upload_0_octet_message_nomme_et_dit_0_octet",
      d0.startswith("Fichier vide ou illisible : ") and "vide total.mp4" in d0
      and "0 octet" in d0, d0[:200])
check("upload_0_octet_aucun_job_aucun_fichier",
      N_JOBS() == av_jobs and UPS() == av_ups, f"{av_jobs}->{N_JOBS()} {UPS()}")

r1 = UPLOAD("coupe.mp4", TRONQUE)
d1 = str(J(r1).get("detail") or "")
check("upload_tronque_415", r1.status_code == 415, f"{r1.status_code} {r1.text[:200]}")
check("upload_tronque_message_nomme_et_dit_illisible",
      d1.startswith("Fichier vide ou illisible : ") and "coupe.mp4" in d1
      and "illisible" in d1.split("coupe.mp4", 1)[-1] and "0 octet" not in d1,
      d1[:200])
# La raison est COURTE : pas la tranche brute de stderr (ni chemin absolu, ni
# banniere).
check("upload_tronque_raison_courte_sans_chemin",
      0 < len(d1) <= 220 and TMP not in d1 and "configuration:" not in d1,
      f"{len(d1)} car. : {d1[:220]}")
check("upload_tronque_aucun_job_aucun_fichier",
      N_JOBS() == av_jobs and UPS() == av_ups, f"{av_jobs}->{N_JOBS()} {UPS()}")

r2 = UPLOAD("temoin.mp4", MP4B)
d2 = J(r2)
JID_OK = str(d2.get("job_id") or "")
check("upload_temoin_mp4_valide_200_job_cree",
      r2.status_code == 200 and bool(JID_OK) and N_JOBS() == av_jobs + 1,
      f"{r2.status_code} {r2.text[:200]} jobs {av_jobs}->{N_JOBS()}")
check("upload_temoin_duree_inchangee",
      1.5 <= float(d2.get("duration_s") or 0) <= 2.6
      and (UP / "temoin.mp4").is_file(), str(d2)[:200])
# MESURE avant correctif : la route force `.mp4` au nom et accepte un contenu
# audio seul (ffprobe lit le contenu, pas l'extension). Garde.
r3 = UPLOAD("rien_que_du_son.wav", WAVB, mime="audio/wav")
check("upload_temoin_son_seul_toujours_accepte",
      r3.status_code == 200 and bool(J(r3).get("job_id")),
      f"{r3.status_code} {r3.text[:200]}")


print("\n[2] UPLOAD audio — meme refus, rien d'ecrase.")
av_a = LIRE(ADIR / "garde.wav")
r4 = UPLOAD("garde.wav", WAVB, route="/api/audio/upload", mime="audio/wav")
check("audio_temoin_valide_200",
      r4.status_code == 200 and LIRE(ADIR / "garde.wav") == WAVB,
      f"{r4.status_code} {r4.text[:200]}")
r5 = UPLOAD("garde.wav", b"", route="/api/audio/upload", mime="audio/wav")
d5 = str(J(r5).get("detail") or "")
check("audio_0_octet_415_nomme",
      r5.status_code == 415 and "garde.wav" in d5 and "0 octet" in d5,
      f"{r5.status_code} {d5[:200]}")
check("audio_0_octet_n_ecrase_pas_l_existant",
      LIRE(ADIR / "garde.wav") == WAVB, f"{len(LIRE(ADIR / 'garde.wav'))} o")
r6 = UPLOAD("garde.wav", b"RIFF\x00\x00\x00\x00pas du tout un wav" * 3,
            route="/api/audio/upload", mime="audio/wav")
d6 = str(J(r6).get("detail") or "")
check("audio_illisible_415_nomme",
      r6.status_code == 415 and "garde.wav" in d6 and "illisible" in d6,
      f"{r6.status_code} {d6[:200]}")
check("audio_illisible_n_ecrase_pas_et_ne_laisse_rien",
      LIRE(ADIR / "garde.wav") == WAVB
      and sorted(p.name for p in ADIR.iterdir() if p.is_file()
                 and not p.name.endswith(".json")) == ["garde.wav"],
      str(sorted(p.name for p in ADIR.iterdir())) if ADIR.is_dir() else "-")
r7 = UPLOAD("neuf_vide.mp3", b"", route="/api/audio/upload", mime="audio/mpeg")
check("audio_0_octet_nom_neuf_rien_ecrit",
      r7.status_code == 415 and not (ADIR / "neuf_vide.mp3").exists(),
      f"{r7.status_code}")


print("\n[3] PRE-VOL de POST /render — sources vides ou illisibles nommees.")
_vrai_run_ffmpeg = MS._run_ffmpeg


def _talon(cmd, out, *a, **k):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"talon")
    return out


MS._run_ffmpeg = _talon

# L'espion : chaque appel de la sonde de lisibilite, par chemin ; il note
# aussi si l'appel tourne HORS de la boucle asyncio (m-1 : dans un thread,
# `get_running_loop()` leve RuntimeError), ce que liste le dossier audio a
# cet instant (m-3), et peut lever une fois (I-1 : « pas pu juger »).
import asyncio                                           # noqa: E402
SONDES, HORS_BOUCLE, AUDIO_PENDANT = [], [], []
LEVER = []            # chemins (suffixes) pour lesquels lever UNE fois
_vraie_sonde = getattr(MS, "_sonde_flux", None)


def _espion(p, *a, **k):
    SONDES.append(str(p))
    try:
        asyncio.get_running_loop()
        HORS_BOUCLE.append((str(p), False))
    except RuntimeError:
        HORS_BOUCLE.append((str(p), True))
    try:
        AUDIO_PENDANT.append(sorted(q.name for q in ADIR.iterdir()))
    except Exception:                                    # noqa: BLE001
        AUDIO_PENDANT.append(["<illisible>"])
    for s in list(LEVER):
        if str(p).endswith(s):
            LEVER.remove(s)
            raise FileNotFoundError("ffprobe (simule)")
    return _vraie_sonde(p, *a, **k)


if _vraie_sonde is not None:
    MS._sonde_flux = _espion
check("sonde_de_lisibilite_exposee", _vraie_sonde is not None, "MS._sonde_flux absent")


def JOB_UP(nom, octets):
    d = J(UPLOAD(nom, octets))
    jid = str(d.get("job_id") or "")
    return jid, UP / str(d.get("filename") or "?")


JID_VIDE, P_VIDE = JOB_UP("demo complete videogen brute.mp4", MP4B)
JID_TR, P_TR = JOB_UP("rush coupe.mp4", MP4B)
JID_V2, P_V2 = JOB_UP("second.mp4", MP4B)
check("fixtures_jobs_poses", bool(JID_VIDE and JID_TR and JID_V2 and JID_OK),
      f"{JID_VIDE!r} {JID_TR!r} {JID_V2!r} {JID_OK!r}")
try:
    P_VIDE.write_bytes(b"")          # vide sur disque APRES l'upload (juillet)
    P_TR.write_bytes(TRONQUE)        # tronque sur disque
except Exception as e:                                   # noqa: BLE001
    print("  (preparation des fautifs : %s)" % e)

BASE = {"name": "illisibles", "ratio": "9:16", "preview": True,
        "mix": {"dialogue": -6, "musique": -18, "sfx": -12}}


def V1(cid, label, jid, start, end):
    return {"tr": "v1", "id": cid, "label": label, "start": start, "end": end,
            "src": {"job_id": jid}, "srcIn": 0, "transition": "cut"}


def RENDER(clips):
    return POST("/api/montage/render", json=dict(BASE, clips=clips))


PLAN_OK = V1("c1", "plan valide", JID_OK, 0, 2)
av = N_JOBS("montage")
rv = RENDER([PLAN_OK, V1("c2", "demo brute", JID_VIDE, 62, 64)])
dv = str(J(rv).get("detail") or "")
check("render_source_0_octet_400", rv.status_code == 400, f"{rv.status_code} {rv.text[:200]}")
check("render_0_octet_message_complet",
      dv.startswith("Rendu impossible : 1 source(s) illisible(s)")
      and "« demo brute »" in dv and "V1" in dv and "à 1:02" in dv
      and "demo complete videogen brute.mp4" in dv and "(0 octet)" in dv
      and dv.endswith("Remplace ou retire ces plans."), dv[:300])
check("render_0_octet_ne_nomme_pas_le_clip_valide",
      bool(dv) and "plan valide" not in dv and "temoin.mp4" not in dv, dv[:300])
check("render_0_octet_aucun_job", N_JOBS("montage") == av, f"{av}->{N_JOBS('montage')}")

rt = RENDER([PLAN_OK, V1("c3", "rush tronque", JID_TR, 2, 4)])
dt = str(J(rt).get("detail") or "")
check("render_source_tronquee_400", rt.status_code == 400, f"{rt.status_code} {rt.text[:200]}")
check("render_tronque_message_dit_illisible_et_nomme",
      "« rush tronque »" in dt and "à 0:02" in dt and "rush coupe.mp4" in dt
      and "(illisible : " in dt and "0 octet" not in dt and TMP not in dt,
      dt[:300])
check("render_tronque_aucun_job", N_JOBS("montage") == av, f"{av}->{N_JOBS('montage')}")

ra = RENDER([PLAN_OK, {"tr": "a1", "id": "c4", "label": "son vide", "start": 5,
                        "end": 7, "src": {"job_id": JID_VIDE}}])
da = str(J(ra).get("detail") or "")
check("render_a1_source_vide_400_nomme_piste_a1",
      ra.status_code == 400 and "« son vide »" in da and "A1" in da
      and "à 0:05" in da and "(0 octet)" in da, f"{ra.status_code} {da[:300]}")
check("render_a1_aucun_job", N_JOBS("montage") == av, f"{av}->{N_JOBS('montage')}")

# Les deux fautifs ensemble : le compte annonce est le vrai.
r2f = RENDER([PLAN_OK, V1("c2", "demo brute", JID_VIDE, 2, 4),
              V1("c3", "rush tronque", JID_TR, 4, 6)])
d2f = str(J(r2f).get("detail") or "")
check("render_deux_fautifs_comptes_et_nommes",
      r2f.status_code == 400 and "2 source(s) illisible(s)" in d2f
      and "demo brute" in d2f and "rush tronque" in d2f, d2f[:300])

# Bornes alignees sur P8 : libelle [:60], huit fautifs cites, vrai compte.
rl = RENDER([PLAN_OK, V1("c9", "L" * 5000, JID_VIDE, 2, 4)])
dl = str(J(rl).get("detail") or "")
check("render_borne_libelle_60",
      rl.status_code == 400 and ("L" * 60) in dl and ("L" * 61) not in dl,
      f"{rl.status_code} {len(dl)} o")
r12 = RENDER([PLAN_OK] + [V1("d%02d" % i, "fautif%02d" % i, JID_VIDE,
                              2 + 2 * i, 4 + 2 * i) for i in range(12)])
d12 = str(J(r12).get("detail") or "")
cites = [i for i in range(12) if ("fautif%02d" % i) in d12]
check("render_borne_huit_cites_vrai_compte",
      r12.status_code == 400 and len(cites) == 8 and "12 source(s)" in d12,
      f"{r12.status_code} cites={cites} {d12[:120]}")

# TEMOIN : deux clips valides -> 200 et un job.
av = N_JOBS("montage")
rok = RENDER([PLAN_OK, V1("c5", "second plan", JID_V2, 2, 4)])
check("render_temoin_deux_valides_200",
      rok.status_code == 200 and bool(J(rok).get("job_id"))
      and N_JOBS("montage") == av + 1,
      f"{rok.status_code} {rok.text[:200]} {av}->{N_JOBS('montage')}")

# ETAT VIDE / chemin d'avant : une source DISPARUE n'est pas l'affaire du
# pre-vol (et n'est jamais sondee).
P_GONE = UP / "second.mp4"
n_av = len(SONDES)
try:
    P_GONE.unlink()
except Exception as e:                                   # noqa: BLE001
    print("  (effacement : %s)" % e)
av = N_JOBS("montage")
rg = RENDER([PLAN_OK, V1("c6", "efface", JID_V2, 2, 4)])
check("render_source_disparue_chemin_d_avant_200",
      rg.status_code == 200 and N_JOBS("montage") == av + 1,
      f"{rg.status_code} {rg.text[:200]}")
check("render_source_disparue_jamais_sondee",
      not any(s.endswith("second.mp4") for s in SONDES[n_av:]), str(SONDES[n_av:]))


print("\n[4] CACHE de la sonde — (chemin, taille, mtime).")
JID_C, P_C = JOB_UP("cache.mp4", MP4B)
n0 = len(SONDES)
def _sur_c():
    return sum(1 for s in SONDES[n0:] if s.endswith("cache.mp4"))
rc1 = RENDER([V1("k1", "cache", JID_C, 0, 2)])
rc2 = RENDER([V1("k1", "cache", JID_C, 0, 2)])
check("cache_deux_rendus_une_seule_sonde",
      rc1.status_code == 200 and rc2.status_code == 200 and _sur_c() == 1,
      f"{rc1.status_code}/{rc2.status_code} sondes={_sur_c()}")
try:
    _st = P_C.stat()
    os.utime(P_C, ns=(_st.st_atime_ns, _st.st_mtime_ns + 5_000_000_000))
except Exception as e:                                   # noqa: BLE001
    print("  (utime : %s)" % e)
rc3 = RENDER([V1("k1", "cache", JID_C, 0, 2)])
check("cache_mtime_change_nouvelle_sonde",
      rc3.status_code == 200 and _sur_c() == 2, f"{rc3.status_code} sondes={_sur_c()}")
try:
    P_C.write_bytes(TRONQUE)
except Exception as e:                                   # noqa: BLE001
    print("  (troncature : %s)" % e)
rc4 = RENDER([V1("k1", "cache", JID_C, 0, 2)])
check("cache_taille_change_nouvelle_sonde_et_refus",
      rc4.status_code == 400 and _sur_c() == 3, f"{rc4.status_code} sondes={_sur_c()}")

print("\n[5] REVUE du 26/09 — nom du plan, indecis non cache, hors boucle, bornes.")
# A — le client envoie le NOM du plan dans `title` (sans `label`).
rA = RENDER([PLAN_OK, {"tr": "v1", "id": "v1", "title": "plan B", "start": 6,
                       "end": 8, "src": {"job_id": JID_VIDE}, "srcIn": 0,
                       "transition": "cut"}])
dA = str(J(rA).get("detail") or "")
check("titre_du_plan_nomme_au_prevol_illisible",
      rA.status_code == 400 and "« plan B » (V1, à 0:06)" in dA, f"{rA.status_code} {dA[:200]}")
GLB = SRC / "maillage.glb"
try:
    GLB.write_bytes(b"glTF\x02\x00\x00\x00faux")
except Exception as e:                                   # noqa: BLE001
    print("  (glb : %s)" % e)
rA2 = RENDER([PLAN_OK, {"tr": "v2", "id": "v2", "title": "maillage B", "start": 0,
                        "end": 2, "src": {"file_path": str(GLB)}}])
dA2 = str(J(rA2).get("detail") or "")
check("titre_du_plan_nomme_au_prevol_p8",
      rA2.status_code == 400 and "« maillage B »" in dA2, f"{rA2.status_code} {dA2[:200]}")

# I-1 — « pas pu juger » passe SANS cache : le rendu suivant re-sonde et refuse.
JID_I, P_I = JOB_UP("indecis.mp4", MP4B)
try:
    P_I.write_bytes(TRONQUE)
except Exception as e:                                   # noqa: BLE001
    print("  (troncature : %s)" % e)
LEVER.append("indecis.mp4")
rI1 = RENDER([V1("i1", "indecis", JID_I, 0, 2)])
rI2 = RENDER([V1("i1", "indecis", JID_I, 0, 2)])
check("indecis_passe_puis_refus_au_rendu_suivant",
      rI1.status_code == 200 and rI2.status_code == 400
      and "indecis.mp4 (illisible : " in str(J(rI2).get("detail") or ""),
      f"{rI1.status_code}/{rI2.status_code} {rI2.text[:200]}")
check("indecis_l_espion_a_bien_leve", not LEVER, str(LEVER))

# m-1 — la sonde tourne hors de la boucle : pre-vol ET /audio/upload.
_pv = [h for (s, h) in HORS_BOUCLE if s.endswith("indecis.mp4")]
check("sonde_hors_boucle_prevol", len(_pv) >= 2 and all(_pv), str(_pv))
n_hb, n_ap = len(HORS_BOUCLE), len(AUDIO_PENDANT)
rU = UPLOAD("pendant.wav", WAVB, route="/api/audio/upload", mime="audio/wav")
_au = [h for (s, h) in HORS_BOUCLE[n_hb:]]
check("sonde_hors_boucle_audio_upload",
      rU.status_code == 200 and len(_au) == 1 and all(_au), f"{rU.status_code} {_au}")
# m-3 — le temporaire de sonde n'est jamais dans le dossier audio liste.
_pend = AUDIO_PENDANT[n_ap:]
_liste = [str(x.get("name")) for x in (J(c.get("/api/audio")).get("audio") or [])]
check("audio_temporaire_de_sonde_hors_du_dossier_liste",
      len(_pend) == 1 and not any("sonde" in n for n in _pend[0])
      and "pendant.wav" not in _pend[0]
      and "pendant.wav" in _liste and not any("sonde" in n for n in _liste),
      f"pendant={_pend} apres={_liste}")

# m-2 — un `start` non fini ne fait pas de 500.
rS = RENDER([PLAN_OK, V1("s1", "infini", JID_VIDE, "1e999", 4)])
dS = str(J(rS).get("detail") or "")
check("start_non_fini_400_pas_500",
      rS.status_code == 400 and "« infini » (V1, à 0:00)" in dS, f"{rS.status_code} {dS[:200]}")

if _vraie_sonde is not None:
    MS._sonde_flux = _vraie_sonde
MS._run_ffmpeg = _vrai_run_ffmpeg

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
# Nettoyage : le journal loguru et le pool sqlite tiennent encore des handles
# apres le lifespan — on les ferme d'abord, puis on efface sans jamais rougir.
try:
    from loguru import logger as _lg
    _lg.remove()
    import asyncio as _aio
    from app.services import storage as _st
    _aio.run(_st._engine.dispose())
except Exception as _e:
    print("  (fermeture des handles : %s)" % _e)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
