# -*- coding: utf-8 -*-
"""L4 — LIVRAISON cote backend. En-tete recopie de test_montage_l3.py (env,
check, J, A, V1SPEC/FLAT/BUILD) : dossier de donnees NEUF par execution,
TestClient sans port ouvert, toute lecture gardee — un banc qui meurt sur un
acces nu ne dit pas quelles assertions manquent.
Run : & $PY tests/test_montage_l4.py   (depuis backend/)

[1] D-35 PRESETS DE SORTIE. `_DELIVER` porte dix presets {label, side, fps,
vcodec|vcodec_alt, pix_fmt, acodec, ext, flags | audio_only | gif} ;
`_deliver_dims(ratio, side)` = `_CANVAS[ratio]` mis a l'echelle sur le PETIT
cote (ECART DATE 23/09/2026 : le plan ecrit « grand cote » mais ses propres
checks — dims("16:9",720)==(1280,720), dims("9:16",2160)==(2160,3840) —
imposent le petit, c'est-a-dire la classe usuelle 720p/1080p/2160p), arrondi
pair, ratio inconnu → 9:16 ; `_encoder_ok(name)` SONDE par un encodage reel
d'une image (cache par processus) — mesure le 23/09/2026 : hevc_amf est liste
par `ffmpeg -encoders` mais ECHOUE (rc 171), hevc_nvenc rend 127 dans ce shell,
la liste ne prouve rien ; `_build_montage_command(…, preset=)` accepte un dict
RESOLU ou un id integre (maison NON resolu ici → master) et remplace le
dernier maillon `format=yuv420p[outv]` + la queue historique par
`_deliver_tail` : format={pix_fmt}, vcodec (sonde pour vcodec_alt), -pix_fmt,
-r, acodec, flags, extension du preset ; audio seul → `-vn`, `-map` audio
seul, video dans `nullsink` ; GIF → fps=12,split/palettegen/paletteuse, `-an`,
mix dans `anullsink`. `master_1080` == commande historique OCTET POUR OCTET ;
l'apercu IGNORE le preset (480p/x264 veryfast/crf 30). fps hors 24/25/30/60
avec un preset → ValueError.
ETAT VIDE : `A("_DELIVER")` rend None, `A("_deliver_dims")` etc. rendent
"ABSENT" ; `BUILD(preset=…)` sur une signature qui ne connait pas `preset`
rend "TypeError: …" (temoin nomme) → les checks rougissent, ne meurent pas.
Regle des assertions negatives : chaque « pas de X » est precede dans la
MEME expression du temoin positif qui prouve que la mesure a eu lieu.
[2] PRESETS MAISON. `GET /api/montage/deliver-presets` → {builtins:[{id,
label}], fps:[24,25,30,60], presets:[]} sur base vide (le client n'a AUCUNE
liste en dur) ; `PUT` {presets:[{id,label,base,fps?,crf?}]} → 200, fichier
`deliver_presets.json` a cote de `montage_saved.json`, atomique (aucun .tmp),
relu par GET ; base inconnue / id non slug / id integre / fps hors liste /
crf hors 0..51 / > 50 / non-liste → 400 et le fichier N'EST PAS touche ;
`_deliver_resolve(pid, fps, maison)` pure : maison → base + surcharges (fps,
crf remplace la valeur apres -crf ET -cq), inconnu → master, fps du payload
prime, GIF garde 12.
[M] MESURE ffmpeg REELLE (SKIP si absent) : prores422 → .mov, gif_480 → .gif,
audio_mp3 → .mp3, non vides, rc 0.
[6] ESPION /render : {preset:"web_4k", fps:60} → `preset` recu est un dict
side 2160, w 2160, fps 60, out .mp4 ; {preset:"audio_wav"} → out .wav ;
{fps:48} → 400 ; apercu + prores → w 270 (1080/4), fps 30, out _preview.mp4.
[3] D-24 LOUDNESS NORMEE EN DEUX PASSES. `_LOUD_TARGETS = (-14, -16, -23)` ;
`_loudnorm_parse(stderr)` pure : DERNIER bloc JSON de loudnorm (input_i,
input_tp, input_lra, input_thresh, target_offset) → {I, TP, LRA, thresh,
offset} floats, None sans JSON ; `_loudnorm_pass1_cmd(v1, v2, a_clips, music,
*, loudness, **kw)` = EXACTEMENT le chemin audio_only=True de
`_build_montage_command` (memes entrees, meme graphe audio) dont le maillon
`ebur128…[emeas]` est remplace par `loudnorm=I=T:TP=-1.5:LRA=11:
print_format=json[emeas]` → `-f null -` ; cmd None sans audio (anullsrc) ;
`_loudnorm_pass1(…)` l'execute (timeout 180) et parse. `_build_montage_command(
…, loudness=, loud_measured=)` : loudness ∈ cibles sinon ValueError ; final +
audio reel → `loud_measured` OBLIGATOIRE (ValueError sinon) et
`[outa]loudnorm=I=T:TP=-1.5:LRA=11:measured_I=…:measured_TP=…:measured_LRA=…:
measured_thresh=…:offset=…:linear=true:print_format=summary,aresample=48000
[outn]` mappe A LA PLACE de [outa] (les deux formes : aresample seul, amix) ;
anullsrc → aucun loudnorm (temoin anullsrc) ; apercu → commande historique.
ECART DATE (23/09/2026) : la passe 1 mesure la PLAGE rendue quand `range_out`
est pose (-ss/-t sur la sortie de mesure aussi) — le gain lineaire est
calcule sur ce que le fichier contiendra, pas sur tout le montage.
[4] D-38 RENDU PARTIEL DE LA PLAGE I/O. `range_out=(a, b)` valide (a ≥ 0,
b > a, a < total) → `-ss a` JUSTE AVANT `-t round(min(b,total)-a, 3)` a la place
de `-t total`, dans les quatre queues (historique/apercu, preset video, audio
seul, GIF) et dans la mesure audio_only ; invalide → ValueError « plage » ;
None → historique.
[6] (suite) ESPION : {loudness:-14} → `_loudnorm_pass1` espionne appele AVANT
la commande finale, `loud_measured` transmis ; {range:[2,5]} → range_out ==
(2.0, 5.0) ; {range:[5,2]} / [4,6] (a ≥ total) → 400 « plage invalide » ;
{loudness:-19} → 400 « loudness invalide » ; apercu + loudness → passe 1 NON
appelee ; le titre du job final porte le libelle du preset (pas master).
[5] D-36 FILE LOCALE EN SERIE. `queue:true` → le job nait `queued`/0/
« En file » (statut EXISTANT de `JobStatus`, aucun schema touche), la reponse
porte {queued:true, position:n} (n = rang dans la file EN COMPTANT le job
en cours : 1 = prochain/en cours — ECART DATE 23/09/2026 : `q.qsize()` du
plan exclut l'element deja pris par le worker et rendrait 1 au deuxieme
POST), un worker asyncio unique execute `_run` en serie (start[k+1] >=
end[k]) ; sans `queue` → immediat, chevauchement autorise (temoin) ; un
job en file qui leve → failed, la file continue ; `queue` + `preview` →
400 ; `GET /api/jobs?providers=montage` liste les `queued`.
"""
import json, os, sys, tempfile, subprocess, pathlib, shutil, time
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl4_")
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


c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

from app.services import montage_service as MS           # noqa: E402


def A(nom, defaut):
    """`getattr` module — un attribut ABSENT (avant l'implementation) doit
    faire ROUGIR les checks qui le lisent, jamais TUER le banc."""
    return getattr(MS, nom, defaut)


V1F = str(pathlib.Path(TMP) / "v1.mp4")
pathlib.Path(V1F).write_bytes(b"x")


def V1SPEC(**kw):
    d = {"path": V1F, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}
    d.update(kw)
    return d


def FLAT(cmd):
    return " ".join(cmd) if isinstance(cmd, list) else str(cmd)


def ASPEC(**kw):
    """Forme d'un clip AUDIO pour `_build_montage_command`, RECOPIEE de
    `/render` (:3703) : `tr` a1|a3, gain, fades, fx_chain, speed."""
    d = {"tr": "a1", "path": V1F, "src_dur": 4.0, "src_in": 0.0, "start": 0.0,
         "end": 4.0, "gain": 1.0, "fade_in": 0.0, "fade_out": 0.0,
         "fade_in_curve": None, "fade_out_curve": None, "fx_chain": "",
         "speed": 0.0, "volume_points": None}
    d.update(kw)
    return d


def TL(name="l4", n=1, dur=4, src=None):
    """Timeline minimale pour /render — recopiee de tests/test_montage_l3.py."""
    return {"name": name, "ratio": "9:16", "duration": dur, "mix": {},
            "clips": [{"tr": "v1", "id": "v%d" % i, "start": 0, "end": 4,
                       "src": {"file_path": src or V1F}} for i in range(n)]}


def BUILD(**kw):
    """`_build_montage_command` avec les constantes de CE banc : FINAL
    (preview=False, sinon le preset serait ignore par construction) a 30 i/s
    (la cadence du master). `preset`, `fps`, `preview`, `out`… sont des
    mots-cles de SIGNATURE ; `dz`/`speed`/… iraient au clip. Toute exception
    du service rend un temoin nomme (« TypeError: … » = l'ETAT VIDE quand
    `preset` est inconnu de la signature) — rougir, pas mourir."""
    clip = {k: kw.pop(k) for k in ("dz", "speed", "retime", "stab", "src_in", "end", "src_dur") if k in kw}
    a = {"w": 64, "h": 64, "fps": 30, "mix_db": {}, "ducking": False,
         "duration_master": False, "preview": False,
         "out": os.path.join(TMP, "o.mp4")}
    a.update(kw)
    # `_audio` : False/0 → anullsrc ; True/1 → une source (aresample seul) ;
    # 2 → deux sources (forme amix). Les trois formes du mix final.
    ac = [ASPEC() for _ in range(int(a.pop("_audio", 0) or 0))]
    try:
        cmd, _ = MS._build_montage_command([V1SPEC(**clip)], [], ac, None, **a)
    except Exception as e:                 # faute n°6 : rougir, pas mourir
        return "%s: %s" % (type(e).__name__, e)
    return FLAT(cmd)


def _t(cmd, n=260):
    return cmd[-n:] if isinstance(cmd, str) else cmd


print("\n[1] D-35 presets de sortie : table, dimensions, encodeur sonde, queue de commande")
_c0 = BUILD()
check("d35_sans_preset_la_commande_est_l_historique",
      _c0.startswith("ffmpeg") and BUILD(preset=None) == _c0 and BUILD(preset="master_1080") == _c0,
      (_t(_c0, 120), _t(BUILD(preset="master_1080"), 120)))
# La queue historique, PINNEE : c'est elle que master_1080 doit reproduire.
_QUEUE_HIST = ("-c:v libx264 -profile:v high -level 4.0 -preset medium -crf 20 "
               "-pix_fmt yuv420p -r 30 -c:a aac -b:a 192k -movflags +faststart ")
check("d35_la_queue_historique_est_pinnee_octet_pour_octet",
      _QUEUE_HIST in _c0 and "format=yuv420p[outv]" in _c0 and _c0.rstrip().endswith("o.mp4"),
      _t(_c0))
D = A("_DELIVER", None)
_DIX = {"master_1080", "web_4k", "social_720", "prores422", "hevc", "webm_vp9",
        "audio_aac", "audio_mp3", "audio_wav", "gif_480"}
check("d35_table_porte_les_dix_presets",
      isinstance(D, dict) and set(D) >= _DIX
      and all(isinstance(v, dict) and "label" in v and "ext" in v and "side" in v and "fps" in v
              for v in D.values()),
      D and sorted(D))
check("d35_chaque_preset_video_porte_un_vcodec_ou_des_candidats_et_les_extensions_sont_distinctes",
      isinstance(D, dict) and all(
          ("vcodec" in v) != ("vcodec_alt" in v) for k, v in D.items()
          if not v.get("audio_only") and not v.get("gif"))
      and {v.get("ext") for v in D.values()} >= {".mp4", ".mov", ".webm", ".m4a", ".mp3", ".wav", ".gif"},
      D and {k: sorted(v) for k, v in D.items()})
check("d35_la_liste_des_cadences_est_24_25_30_60",
      tuple(A("_DELIVER_FPS", ())) == (24, 25, 30, 60), A("_DELIVER_FPS", None))
dims = A("_deliver_dims", None)
check("d35_dims_petit_cote_et_pair",
      callable(dims) and dims("9:16", 2160) == (2160, 3840) and dims("16:9", 720) == (1280, 720)
      and dims("4:5", 1080) == (1080, 1350) and dims("1:1", 2160) == (2160, 2160)
      and dims("zz", 1080) == (1080, 1920),
      callable(dims) and [dims("9:16", 2160), dims("16:9", 720), dims("4:5", 1080), dims("zz", 1080)])
check("d35_dims_master_reproduit_le_canvas_et_l_arrondi_est_pair",
      callable(dims) and all(dims(r, 1080) == MS._CANVAS[r] for r in MS._CANVAS)
      and dims("4:5", 720) == (720, 900) and dims("9:16", 481)[0] % 2 == 0 and dims("9:16", 481)[1] % 2 == 0,
      callable(dims) and [dims("4:5", 720), dims("9:16", 481)])
_c4k = BUILD(preset="web_4k")
check("d35_web_4k_crf_18_libx264_niveau_5_1",
      "-c:v libx264" in _c4k and "-crf 18" in _c4k and "-level 5.1" in _c4k and _c0 != _c4k
      and "-crf 20" not in _c4k, _t(_c4k, 200))
_c7 = BUILD(preset="social_720")
check("d35_social_720_crf_23_mp4",
      "-c:v libx264" in _c7 and "-crf 23" in _c7 and _c7.rstrip().endswith(".mp4") and _c7 != _c0,
      _t(_c7, 200))
_cp = BUILD(preset="prores422")
check("d35_prores_ks_profil_2_yuv422p10le_mov_pcm",
      "-c:v prores_ks" in _cp and "-profile:v 2" in _cp and "format=yuv422p10le[outv]" in _cp
      and "-pix_fmt yuv422p10le" in _cp and "-c:a pcm_s16le" in _cp
      and _cp.rstrip().endswith(".mov") and "format=yuv420p[outv]" not in _cp
      and "libx264" not in _cp, _t(_cp))
_cw = BUILD(preset="webm_vp9")
check("d35_vp9_libopus_webm",
      "-c:v libvpx-vp9" in _cw and "-b:v 0" in _cw and "-row-mt 1" in _cw and "-c:a libopus" in _cw
      and _cw.rstrip().endswith(".webm") and "-movflags" not in _cw, _t(_cw, 200))
_ca = BUILD(preset="audio_mp3")
check("d35_audio_seul_vn_sans_map_outv_mp3",
      "ffmpeg" in _ca and "-vn" in _ca and "-map [outv]" not in _ca and "-map 1:a" in _ca
      and "anullsrc" in _ca and "-c:a libmp3lame" in _ca and "-q:a 2" in _ca
      and _ca.rstrip().endswith(".mp3") and "-c:v" not in _ca and "]nullsink" in _ca
      and "[outv]" not in _ca, _t(_ca, 300))
_caa = BUILD(preset="audio_mp3", _audio=True)
check("d35_audio_seul_avec_mix_mappe_outa_et_jette_la_video",
      "[outa]" in _caa and "-map [outa]" in _caa and "-vn" in _caa and "anullsrc" not in _caa
      and "]nullsink" in _caa and "-map [outv]" not in _caa, _t(_caa, 300))
_cwav = BUILD(preset="audio_wav"); _cm4a = BUILD(preset="audio_aac")
check("d35_audio_wav_pcm_et_m4a_aac",
      "-vn" in _cwav and "-c:a pcm_s16le" in _cwav and _cwav.rstrip().endswith(".wav")
      and "-vn" in _cm4a and "-c:a aac" in _cm4a and _cm4a.rstrip().endswith(".m4a"),
      (_t(_cwav, 120), _t(_cm4a, 120)))
_cg = BUILD(preset="gif_480")
check("d35_gif_palettegen_paletteuse_12fps_sans_audio",
      "palettegen[pal]" in _cg and "[pal]paletteuse[outv]" in _cg and "fps=12,split[g0][g1]" in _cg
      and "-r 12" in _cg and "-an" in _cg and _cg.rstrip().endswith(".gif")
      and "anullsrc" in _cg and "-map 1:a" not in _cg and "-c:v" not in _cg
      and "-c:a" not in _cg, _t(_cg, 320))
_cga = BUILD(preset="gif_480", _audio=True)
check("d35_gif_avec_mix_jette_le_mix_dans_anullsink_sans_le_mapper",
      "[outa]" in _cga and "[outa]anullsink" in _cga and "-map [outa]" not in _cga
      and "-an" in _cga and "[pal]paletteuse[outv]" in _cga, _t(_cga, 320))
_ch = BUILD(preset="hevc")
check("d35_hevc_prend_nvenc_si_sonde_ok_sinon_libx265",
      "ffmpeg" in _ch and ("-c:v hevc_nvenc" in _ch) != ("-c:v libx265" in _ch)
      and "-tag:v hvc1" in _ch and _ch.rstrip().endswith(".mp4"), _t(_ch, 200))
eok = A("_encoder_ok", None)
check("d35_encoder_ok_sonde_reellement_et_cache",
      callable(eok) and eok("libx264") is True and eok("zz_pas_un_encodeur") is False
      and eok("hevc_amf") in (True, False) and eok("a b; rm") is False
      and isinstance(A("_ENCODER_CACHE", None), dict)
      and A("_ENCODER_CACHE", {}).get("libx264") is True
      and A("_ENCODER_CACHE", {}).get("zz_pas_un_encodeur") is False,
      (callable(eok) and eok("libx264"), A("_ENCODER_CACHE", None)))
check("d35_la_sonde_hevc_decide_la_branche",
      callable(eok) and (("-c:v hevc_nvenc" in _ch) == eok("hevc_nvenc"))
      and (("-c:v libx265" in _ch) == (not eok("hevc_nvenc"))),
      (callable(eok) and eok("hevc_nvenc"), _t(_ch, 120)))
_c60 = BUILD(preset="master_1080", fps=60)
check("d35_fps_60_ecrit_r_60",
      "-r 60" in _c60 and "-r 30" in _c0 and "-r 60" not in _c0 and "-r 30" not in _c60,
      (_t(_c60, 120)))
_c48 = BUILD(preset="master_1080", fps=48)
check("d35_fps_hors_liste_refuse",
      _c48.startswith("ValueError") and "48" in _c48 and "-r 48" not in _c48, _c48[:120])
check("d35_sans_preset_la_cadence_historique_25_passe_encore",
      "-r 25" in BUILD(fps=25) and "-r 25" in BUILD(fps=25, preview=True),
      _t(BUILD(fps=25), 120))
check("d35_preset_inconnu_retombe_sur_master",
      BUILD(preset="zzz") == _c0 and BUILD(preset="maison_a") == _c0 and BUILD(preset="") == _c0,
      _t(BUILD(preset="zzz"), 120))
_cpv = BUILD(preview=True)
check("d35_apercu_ignore_le_preset",
      BUILD(preset="prores422", preview=True) == _cpv and BUILD(preset="gif_480", preview=True) == _cpv
      and "-crf 30" in _cpv and "-preset veryfast" in _cpv and _cpv.rstrip().endswith("o.mp4")
      and "prores" not in _cpv, _t(_cpv, 200))
# Un dict RESOLU est accepte tel quel (c'est ce que /render envoie).
_res = A("_deliver_resolve", None)
_dres = _res("prores422", None) if callable(_res) else None
check("d35_un_dict_resolu_est_accepte_par_la_commande",
      isinstance(_dres, dict) and BUILD(preset=_dres) == _cp and _dres.get("id") == "prores422",
      (_dres and sorted(_dres), _t(BUILD(preset=_dres), 80)))
# Le maillon final suit `cur` : avec des sous-titres, la gravure precede format=.
_ASS = pathlib.Path(TMP) / "s.ass"; _ASS.write_text("[Script Info]\n", encoding="utf-8")
_cs = BUILD(preset="prores422", subs_ass=str(_ASS))
check("d35_avec_sous_titres_la_gravure_precede_le_format_du_preset",
      "subtitles=" in _cs and ",format=yuv422p10le[outv]" in _cs
      and _cs.index("subtitles=") < _cs.index("format=yuv422p10le[outv]"), _t(_cs, 300))

print("\n[2] presets maison : GET/PUT /api/montage/deliver-presets, fichier atomique, resolution pure")
_PF = pathlib.Path(TMP) / "deliver_presets.json"
try:
    _PF.unlink()
except OSError:
    pass
r = c.get("/api/montage/deliver-presets"); d = J(r)
check("maison_get_sur_base_vide_rend_builtins_fps_et_presets_vides",
      r.status_code == 200 and d.get("presets") == [] and d.get("fps") == [24, 25, 30, 60]
      and isinstance(d.get("builtins"), list) and len(d["builtins"]) == len(D or {})
      and all(set(b) == {"id", "label"} for b in d["builtins"])
      and [b["id"] for b in d["builtins"]] == list(D or {})
      and not _PF.exists(), (r.status_code, str(d)[:200]))
_M = [{"id": "maison_a", "label": "Mon 4K 60", "base": "web_4k", "fps": 60, "crf": 16},
      {"id": "maison_b", "label": "GIF maison", "base": "gif_480"}]
r = c.put("/api/montage/deliver-presets", json={"presets": _M}); d = J(r)
check("maison_put_valide_rend_200_et_la_liste_canonique",
      r.status_code == 200 and d.get("ok") is True and isinstance(d.get("presets"), list)
      and len(d["presets"]) == 2 and d["presets"][0] == _M[0]
      and d["presets"][1] == {"id": "maison_b", "label": "GIF maison", "base": "gif_480", "fps": None, "crf": None},
      (r.status_code, str(d)[:300]))
_disk = None
try:
    _disk = json.loads(_PF.read_text(encoding="utf-8")) if _PF.is_file() else None
except ValueError:
    _disk = "corrompu"
check("maison_le_fichier_est_a_cote_de_montage_saved_sans_fragment_tmp",
      isinstance(_disk, dict) and len(_disk.get("presets") or []) == 2
      and _PF.parent == MS._saved_path().parent
      and not [p for p in _PF.parent.iterdir() if p.name.endswith(".tmp")],
      (_PF, _disk))
r = c.get("/api/montage/deliver-presets"); d = J(r)
check("maison_get_relit_ce_que_put_a_ecrit",
      r.status_code == 200 and [p.get("id") for p in (d.get("presets") or [])] == ["maison_a", "maison_b"]
      and (d.get("presets") or [{}])[0].get("crf") == 16, str(d)[:300])
_sha_avant = _PF.read_bytes() if _PF.is_file() else b""
_refus = {
    "base_inconnue": [{"id": "x1", "label": "X", "base": "h266"}],
    "id_non_slug": [{"id": "Maison A", "label": "X", "base": "web_4k"}],
    "id_integre": [{"id": "web_4k", "label": "X", "base": "web_4k"}],
    "id_doublon": [{"id": "d", "label": "X", "base": "web_4k"}, {"id": "d", "label": "Y", "base": "hevc"}],
    "fps_hors_liste": [{"id": "f", "label": "X", "base": "web_4k", "fps": 48}],
    "crf_hors_bornes": [{"id": "q", "label": "X", "base": "web_4k", "crf": 99}],
    "label_vide": [{"id": "l", "label": "  ", "base": "web_4k"}],
    "pas_une_liste": {"id": "z"},
    "trop_de_presets": [{"id": "p%d" % i, "label": "P", "base": "web_4k"} for i in range(51)],
    "id_hostile": [{"id": "../x", "label": "X", "base": "web_4k"}],
}
_codes = {}
for k, v in _refus.items():
    rr = c.put("/api/montage/deliver-presets", json={"presets": v} if k != "pas_une_liste" else v)
    _codes[k] = (rr.status_code, (J(rr).get("detail") or "")[:60])
check("maison_put_refuse_chaque_forme_invalide_en_400",
      all(v[0] == 400 for v in _codes.values()) and len(_codes) == 10, _codes)
check("maison_un_put_refuse_ne_touche_pas_le_fichier",
      _sha_avant and _PF.is_file() and _PF.read_bytes() == _sha_avant
      and not [p for p in _PF.parent.iterdir() if p.name.endswith(".tmp")],
      (len(_sha_avant), _PF.is_file()))
r = c.put("/api/montage/deliver-presets", json=[{"id": "nu", "label": "Liste nue", "base": "hevc"}]); d = J(r)
check("maison_put_accepte_une_liste_nue_et_remplace_tout",
      r.status_code == 200 and [p.get("id") for p in (d.get("presets") or [])] == ["nu"]
      and [p.get("id") for p in (J(c.get("/api/montage/deliver-presets")).get("presets") or [])] == ["nu"],
      (r.status_code, str(d)[:200]))
r = c.put("/api/montage/deliver-presets", json={"presets": []}); d = J(r)
check("maison_put_vide_efface_la_liste",
      r.status_code == 200 and d.get("presets") == []
      and J(c.get("/api/montage/deliver-presets")).get("presets") == [], (r.status_code, d))
# Fichier corrompu sur le disque : GET rend [] et le rendu ne meurt pas.
_PF.write_text("{pas du json", encoding="utf-8")
r = c.get("/api/montage/deliver-presets"); d = J(r)
_ld = A("_load_deliver_presets", lambda: "ABSENT")
check("maison_fichier_corrompu_rend_une_liste_vide_sans_mourir",
      r.status_code == 200 and d.get("presets") == [] and _ld() == [] and _PF.is_file(), (r.status_code, d))
_PF.unlink()
# Resolution PURE.
_mais = [{"id": "maison_a", "label": "Mon 4K 60", "base": "web_4k", "fps": 60, "crf": 16},
         {"id": "maison_h", "label": "H", "base": "hevc", "fps": None, "crf": 30},
         {"id": "maison_g", "label": "G", "base": "gif_480", "fps": 60, "crf": None}]
_ra = _res("maison_a", None, _mais) if callable(_res) else None
_rh = _res("maison_h", 25, _mais) if callable(_res) else None
_rg = _res("maison_g", 24, _mais) if callable(_res) else None
_rz = _res("zzz", None, _mais) if callable(_res) else None
_rn = _res(None, None, None) if callable(_res) else None
_rf = _res("web_4k", 60, None) if callable(_res) else None
_rx = _res("web_4k", 48, None) if callable(_res) else None
check("maison_resolve_maison_est_base_plus_surcharges",
      isinstance(_ra, dict) and _ra.get("id") == "web_4k" and _ra.get("side") == 2160 and _ra.get("fps") == 60
      and "-crf" in (_ra.get("vcodec") or []) and _ra["vcodec"][_ra["vcodec"].index("-crf") + 1] == "16"
      and _ra.get("ext") == ".mp4", _ra)
check("maison_resolve_crf_remplace_aussi_cq_des_candidats_hevc_et_le_fps_du_payload_prime",
      isinstance(_rh, dict) and _rh.get("fps") == 25
      and [a[a.index("-cq" if "-cq" in a else "-crf") + 1] for a in (_rh.get("vcodec_alt") or [])] == ["30", "30"],
      _rh)
check("maison_resolve_gif_garde_sa_cadence_12",
      isinstance(_rg, dict) and _rg.get("gif") is True and _rg.get("fps") == 12, _rg)
check("maison_resolve_inconnu_et_none_retombent_sur_master",
      isinstance(_rz, dict) and _rz.get("id") == "master_1080" and _rz == _rn
      and _rz.get("side") == 1080 and _rz.get("fps") == 30, (_rz and _rz.get("id"), _rn and _rn.get("id")))
check("maison_resolve_fps_payload_valide_prime_et_hors_liste_ignore",
      isinstance(_rf, dict) and _rf.get("fps") == 60 and isinstance(_rx, dict) and _rx.get("fps") == 30, (_rf, _rx))
check("maison_resolve_est_pure_la_table_n_est_pas_mutee",
      isinstance(_ra, dict) and (D or {}).get("web_4k", {}).get("fps") == 30
      and "-crf 18" in " ".join((D or {}).get("web_4k", {}).get("vcodec") or [])
      and (D or {}).get("hevc", {}).get("vcodec_alt", [[]])[0][-1] == "24", (D or {}).get("web_4k"))
_pv = A("_valider_presets", None)
try:
    _pv_bad = _pv([{"id": "a", "label": "A", "base": "web_4k", "fps": True}]) if callable(_pv) else "ABSENT"
except ValueError as e:
    _pv_bad = "ValueError: %s" % e
check("maison_valider_refuse_un_booleen_pour_fps",
      isinstance(_pv_bad, str) and _pv_bad.startswith("ValueError") and "fps" in _pv_bad, _pv_bad)
# T2 : le preset maison CONSERVE son libelle (le titre du job le portera).
check("maison_resolve_conserve_le_libelle_maison_et_l_integre_garde_le_sien",
      isinstance(_ra, dict) and _ra.get("label") == "Mon 4K 60"
      and isinstance(_rf, dict) and _rf.get("label") == (D or {}).get("web_4k", {}).get("label")
      and _ra.get("label") != _rf.get("label"), (_ra and _ra.get("label"), _rf and _rf.get("label")))

print("\n[3] D-24 loudness normee en deux passes : chaine passe 2, passe 1 obligatoire, parse, apercu, anullsrc")
_LT = A("_LOUD_TARGETS", None)
check("d24_les_cibles_sont_14_16_23", tuple(_LT or ()) == (-14, -16, -23), _LT)
_MEAS = {"I": -20.1, "TP": -3.2, "LRA": 7.5, "thresh": -30.4, "offset": 0.2}
_CH14 = ("[outa]loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=-20.1:measured_TP=-3.2:measured_LRA=7.5:"
         "measured_thresh=-30.4:offset=0.2:linear=true:print_format=summary,aresample=48000[outn]")
_cl1 = BUILD(loudness=-14, loud_measured=_MEAS, _audio=1)
check("d24_chaine_passe_2_exacte_apres_outa_forme_aresample_seule_et_outn_mappe_a_la_place_de_outa",
      _CH14 in _cl1 and "aresample=async=1[outa]" in _cl1 and "-map [outn]" in _cl1
      and "-map [outa]" not in _cl1 and "amix=" not in _cl1 and _cl1.rstrip().endswith("o.mp4"),
      _t(_cl1, 420))
_cl2 = BUILD(loudness=-14, loud_measured=_MEAS, _audio=2)
check("d24_chaine_passe_2_sur_la_forme_amix_aussi",
      _CH14 in _cl2 and "amix=inputs=2" in _cl2 and "-map [outn]" in _cl2 and "-map [outa]" not in _cl2
      and _cl2.index("amix=inputs=2") < _cl2.index("[outa]loudnorm="), _t(_cl2, 420))
check("d24_la_chaine_vient_apres_outa_et_avant_la_video_finale_dans_le_graphe",
      "[outa]loudnorm=" in _cl1 and "aresample=async=1[outa];[outa]loudnorm=" in _cl1, _t(_cl1, 420))
_cl16 = BUILD(loudness=-16, loud_measured=_MEAS, _audio=1); _cl23 = BUILD(loudness=-23, loud_measured=_MEAS, _audio=1)
check("d24_cibles_16_et_23_ecrivent_I_16_et_I_23",
      "[outa]loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=-20.1" in _cl16 and "I=-14" not in _cl16
      and "[outa]loudnorm=I=-23:TP=-1.5:LRA=11:measured_I=-20.1" in _cl23 and "I=-14" not in _cl23,
      (_t(_cl16, 200), _t(_cl23, 200)))
_clf = BUILD(loudness=-14, loud_measured={"I": -20.13, "TP": -3, "LRA": 7.5, "thresh": -30.4, "offset": 0.0}, _audio=1)
check("d24_les_valeurs_mesurees_sont_ecrites_en_decimal_court_sans_zeros_ni_notation_scientifique",
      "measured_I=-20.13:measured_TP=-3:measured_LRA=7.5:measured_thresh=-30.4:offset=0:linear=true" in _clf
      and "e-" not in _clf.split("loudnorm=")[-1].split("[outn]")[0], _t(_clf, 420))
_cln = BUILD(loudness=-14, _audio=1)
check("d24_loudness_sans_passe_1_est_une_faute_nommee",
      _cln.startswith("ValueError") and "passe 1" in _cln and "loudnorm=" not in _cln, _cln[:160])
_clm = BUILD(loudness=-14, loud_measured={"I": -20.1, "TP": -3.2}, _audio=1)
check("d24_une_mesure_incomplete_est_refusee",
      _clm.startswith("ValueError") and "loudnorm=" not in _clm, _clm[:160])
_cpv1 = BUILD(preview=True, _audio=1)
_cpvl = BUILD(loudness=-14, loud_measured=_MEAS, preview=True, _audio=1)
check("d24_apercu_ignore_la_loudness_commande_historique",
      _cpvl == _cpv1 and "[outa]" in _cpvl and "-map [outa]" in _cpvl and "loudnorm" not in _cpvl
      and BUILD(loudness=-14, preview=True, _audio=1) == _cpv1, _t(_cpvl, 200))
_c19 = BUILD(loudness=-19, loud_measured=_MEAS, _audio=1)
_cbool = BUILD(loudness=True, loud_measured=_MEAS, _audio=1)
_cstr = BUILD(loudness="-14", loud_measured=_MEAS, _audio=1)
check("d24_cible_hors_liste_refusee_19_booleen_chaine",
      _c19.startswith("ValueError") and "-19" in _c19 and "loudnorm=" not in _c19
      and _cbool.startswith("ValueError") and _cstr.startswith("ValueError"), (_c19[:120], _cbool[:80], _cstr[:80]))
_ca0 = BUILD(loudness=-14)
check("d24_sans_audio_anullsrc_aucun_loudnorm_et_aucune_passe_1_exigee",
      _ca0.startswith("ffmpeg") and "anullsrc" in _ca0 and "-map 1:a" in _ca0 and "loudnorm" not in _ca0
      and "[outn]" not in _ca0 and _ca0 == _c0, _t(_ca0, 200))
_clg = BUILD(loudness=-14, loud_measured=_MEAS, _audio=1, preset="gif_480")
_cla = BUILD(loudness=-14, loud_measured=_MEAS, _audio=1, preset="audio_mp3")
check("d24_avec_preset_gif_le_mix_normalise_part_dans_anullsink_et_audio_seul_mappe_outn",
      _CH14 in _clg and "[outn]anullsink" in _clg and "-map [outn]" not in _clg and "-an" in _clg
      and _CH14 in _cla and "-map [outn]" in _cla and "-vn" in _cla and _cla.rstrip().endswith(".mp3"),
      (_t(_clg, 300), _t(_cla, 200)))
_lp = A("_loudnorm_parse", None)
_STDERR = ("ffmpeg version 8.1.1\n[Parsed_loudnorm_0 @ 0000] \n{\n\t\"input_i\" : \"-20.10\",\n"
           "\t\"input_tp\" : \"-3.20\",\n\t\"input_lra\" : \"7.50\",\n\t\"input_thresh\" : \"-30.40\",\n"
           "\t\"output_i\" : \"-14.02\",\n\t\"output_tp\" : \"-1.50\",\n\t\"output_lra\" : \"6.90\",\n"
           "\t\"output_thresh\" : \"-24.30\",\n\t\"normalization_type\" : \"dynamic\",\n"
           "\t\"target_offset\" : \"0.20\"\n}\n")
_STDERR2 = _STDERR + _STDERR.replace("-20.10", "-25.00").replace("\"0.20\"", "\"0.55\"")
_p1 = _lp(_STDERR) if callable(_lp) else "ABSENT"
_p2 = _lp(_STDERR2) if callable(_lp) else "ABSENT"
_p0 = _lp("ffmpeg version 8.1.1\nrien\n") if callable(_lp) else "ABSENT"
_pe = _lp("") if callable(_lp) else "ABSENT"
_pj = _lp("{ \"input_i\" : \"nan\" }") if callable(_lp) else "ABSENT"
check("d24_parse_extrait_le_bloc_json_de_loudnorm_en_floats",
      _p1 == {"I": -20.1, "TP": -3.2, "LRA": 7.5, "thresh": -30.4, "offset": 0.2}
      and all(isinstance(v, float) for v in (_p1 or {}).values()), _p1)
check("d24_parse_prend_le_dernier_bloc",
      isinstance(_p2, dict) and _p2.get("I") == -25.0 and _p2.get("offset") == 0.55
      and isinstance(_p1, dict) and _p1.get("I") == -20.1, _p2)
check("d24_parse_sans_json_ou_incomplet_rend_none",
      _p0 is None and _pe is None and _pj is None, (_p0, _pe, _pj))
_p1c = A("_loudnorm_pass1_cmd", None)
_ARGS = {"w": 64, "h": 64, "fps": 30, "mix_db": {}, "ducking": False, "duration_master": False}
try:
    _pc1 = _p1c([V1SPEC()], [], [ASPEC()], None, loudness=-14, **_ARGS) if callable(_p1c) else ("ABSENT", None)
except Exception as e:
    _pc1 = ("%s: %s" % (type(e).__name__, e), None)
_pc1s = FLAT(_pc1[0]) if isinstance(_pc1, tuple) and isinstance(_pc1[0], list) else str(_pc1)
try:
    _mes = MS._build_montage_command([V1SPEC()], [], [ASPEC()], None, preview=False, out=None,
                                     audio_only=True, **_ARGS)
    _mess = FLAT(_mes[0])
except Exception as e:
    _mess = "%s: %s" % (type(e).__name__, e)
check("d24_passe_1_est_la_mesure_audio_seule_avec_loudnorm_json_a_la_place_d_ebur128",
      "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json[emeas]" in _pc1s and "-map [emeas]" in _pc1s
      and "-f null -" in _pc1s and "ebur128" not in _pc1s and "-c:v" not in _pc1s and "o.mp4" not in _pc1s
      and "ebur128=peak=true:framelog=verbose[emeas]" in _mess
      and _pc1s == _mess.replace("ebur128=peak=true:framelog=verbose", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json")
      and isinstance(_pc1, tuple) and _pc1[1] == _mes[1], (_pc1s[-300:], _mess[-200:]))
try:
    _pc0 = _p1c([V1SPEC()], [], [], None, loudness=-14, **_ARGS) if callable(_p1c) else "ABSENT"
except Exception as e:
    _pc0 = "%s: %s" % (type(e).__name__, e)
check("d24_passe_1_sans_audio_ne_construit_rien",
      isinstance(_pc0, tuple) and _pc0[0] is None and _pc0[1] == 4.0, _pc0)
try:
    _pc19 = _p1c([V1SPEC()], [], [ASPEC()], None, loudness=-19, **_ARGS) if callable(_p1c) else "ABSENT"
except Exception as e:
    _pc19 = "%s: %s" % (type(e).__name__, e)
check("d24_passe_1_refuse_une_cible_hors_liste",
      isinstance(_pc19, str) and _pc19.startswith("ValueError") and "-19" in _pc19, str(_pc19)[:120])
check("d24_passe_1_executrice_existe", callable(A("_loudnorm_pass1", None)))

print("\n[4] D-38 rendu partiel de la plage I/O : -ss avant -t recalcule, validation, historique")
_c8 = BUILD(end=8.0, src_dur=8.0)
_cr = BUILD(end=8.0, src_dur=8.0, range_out=(2.0, 5.0))
# Le `-t 8.0` d'ENTREE (coupe du clip V1 avant son decodage) reste : seule la
# coupe de SORTIE (`-map … -t`) change de forme.
check("d38_range_2_5_ecrit_ss_2_0_juste_avant_t_3_0_a_la_place_de_t_8",
      "-map 1:a -t 8.0 -c:v" in _c8 and "-ss" not in _c8 and "-map 1:a -ss 2.0 -t 3.0 -c:v" in _cr
      and "-map 1:a -t 8.0" not in _cr and _cr.count("-ss") == 1
      and _cr.replace("-map 1:a -ss 2.0 -t 3.0 -c:v", "-map 1:a -t 8.0 -c:v") == _c8,
      (_t(_c8, 160), _t(_cr, 160)))
_cr0 = BUILD(end=8.0, src_dur=8.0, range_out=(0, 3))
check("d38_range_0_3_ecrit_ss_0_0_t_3_0",
      "-map 1:a -ss 0.0 -t 3.0 -c:v" in _cr0 and "-map 1:a -t 8.0" not in _cr0, _t(_cr0, 160))
_crc = BUILD(range_out=(2.0, 99.0))
check("d38_la_fin_est_bornee_au_total",
      "-t 4.0" in _c0 and "-ss 2.0 -t 2.0" in _crc and "-t 97" not in _crc, _t(_crc, 160))
_crf = BUILD(range_out=(1.25, 3.75))
check("d38_les_bornes_decimales_passent_arrondies_a_3",
      "-ss 1.25 -t 2.5" in _crf, _t(_crf, 160))
_bad = {"a_negatif": (-1, 3), "vide": (3, 3), "inversee": (5, 2), "hors_total": (9e9, 9e9),
        "a_egal_total": (4.0, 6.0), "pas_un_couple": (1,), "non_numerique": ("a", "b")}
_bads = {k: BUILD(range_out=v) for k, v in _bad.items()}
check("d38_plages_invalides_sont_des_fautes_nommees",
      all(v.startswith("ValueError") and "plage" in v.lower() for v in _bads.values()) and len(_bads) == 7
      and all("-ss" not in v for v in _bads.values()), {k: v[:70] for k, v in _bads.items()})
check("d38_none_est_l_historique", BUILD(range_out=None) == _c0 and "-ss" not in _c0)
_crp = BUILD(range_out=(1.0, 2.0), preview=True)
check("d38_l_apercu_rend_aussi_la_plage",
      "-ss 1.0 -t 1.0" in _crp and "-preset veryfast" in _crp, _t(_crp, 160))
_crg = BUILD(range_out=(1.0, 3.0), preset="gif_480"); _cra = BUILD(range_out=(1.0, 3.0), preset="audio_wav")
_crpr = BUILD(range_out=(1.0, 3.0), preset="prores422")
check("d38_les_queues_gif_audio_seul_et_preset_video_portent_aussi_ss_t",
      "-an -ss 1.0 -t 2.0 -r 12" in _crg and "-map 1:a -ss 1.0 -t 2.0 -c:a pcm_s16le" in _cra
      and "-ss 1.0 -t 2.0 -c:v prores_ks" in _crpr, (_t(_crg, 160), _t(_cra, 160), _t(_crpr, 160)))
try:
    _mr = MS._build_montage_command([V1SPEC()], [], [ASPEC()], None, preview=False, out=None,
                                    audio_only=True, range_out=(1.0, 3.0), **_ARGS)
    _mrs = FLAT(_mr[0])
except Exception as e:
    _mrs = "%s: %s" % (type(e).__name__, e)
check("d38_la_mesure_audio_seule_porte_aussi_la_plage",
      "-map [emeas] -ss 1.0 -t 2.0 -f null -" in _mrs and "-map [emeas] -t 4.0" not in _mrs
      and "-map [emeas] -t 4.0 -f null -" in _mess, (_mrs[-160:], _mess[-80:]))
_crl = BUILD(range_out=(1.0, 3.0), loudness=-14, loud_measured=_MEAS, _audio=1)
check("d38_plage_et_loudness_se_composent",
      _CH14 in _crl and "-map [outn] -ss 1.0 -t 2.0" in _crl, _t(_crl, 200))

print("\n[M] mesure ffmpeg reelle : prores422 → .mov, gif_480 → .gif, audio_mp3 → .mp3")
_FB = None
try:
    from app.services.effects_preview import ffmpeg_bin as _fb
    _FB = _fb()
    _SRC = str(pathlib.Path(TMP) / "src.mp4")
    _gen = subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                           "testsrc2=s=64x64:r=25:d=2", "-f", "lavfi", "-i",
                           "sine=frequency=440:duration=2", "-c:v", "libx264",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", _SRC],
                          check=False, capture_output=True, timeout=60)
    if _gen.returncode != 0 or not os.path.isfile(_SRC):
        _FB = None
        print("  (ffmpeg present mais testsrc2 a echoue : %r)" % _gen.stderr[-300:])
except Exception as _e:
    _FB = None
    print("  (ffmpeg injoignable : %s)" % _e)
if _FB is None:
    check("d35_rendu_reel_SKIP_sans_ffmpeg", True)
else:
    _spec = V1SPEC(path=_SRC, src_dur=2.0, start=0.0, end=2.0)
    _acl = [ASPEC(path=_SRC, src_dur=2.0, end=2.0)]
    for _pid, _ext in (("prores422", ".mov"), ("gif_480", ".gif"), ("audio_mp3", ".mp3")):
        _out = os.path.join(TMP, "reel_%s.mp4" % _pid)
        try:
            _cmd, _tot = MS._build_montage_command(
                [_spec], [], _acl, None, w=64, h=64, fps=30, mix_db={}, ducking=False,
                duration_master=False, preview=False, out=_out, preset=_pid)
        except Exception as e:
            _cmd, _tot = None, "%s: %s" % (type(e).__name__, e)
        _rc, _err, _size = None, "", -1
        if isinstance(_cmd, list):
            _cmd[0] = _FB
            try:
                _r = subprocess.run(_cmd, capture_output=True, timeout=120)
                _rc, _err = _r.returncode, (_r.stderr or b"")[-400:]
            except Exception as e:
                _err = str(e)
            _fin = pathlib.Path(_out).with_suffix(_ext)
            _size = _fin.stat().st_size if _fin.is_file() else -1
        check("d35_rendu_reel_%s_rc_0_et_fichier_%s_non_vide" % (_pid, _ext[1:]),
              _rc == 0 and _size > 0 and isinstance(_cmd, list) and _cmd[-1].endswith(_ext),
              (_rc, _size, _tot, _err))
    # T2 — D-24 : source 3 s testsrc2 + sine (mesure le 23/09/2026 : -21,8 LUFS
    # une fois passe par le gain dialogue du mix), cible -14 → passe 1 REELLE
    # puis rendu final, puis ebur128 sur la sortie : I ∈ [-15, -13]. La source
    # doit etre a plus de 2 dB de la cible, sinon la mesure ne prouverait rien.
    _SRC3 = str(pathlib.Path(TMP) / "src3.mp4")
    _gen3 = subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "testsrc2=s=64x64:r=25:d=3", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=3", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", _SRC3],
                           check=False, capture_output=True, timeout=60)
    _spec3 = V1SPEC(path=_SRC3, src_dur=3.0, start=0.0, end=3.0)
    _acl3 = [ASPEC(path=_SRC3, src_dur=3.0, end=3.0)]
    _p1f = A("_loudnorm_pass1", None)
    _m1, _m1e = None, ""
    try:
        _m1 = _p1f([_spec3], [], _acl3, None, loudness=-14, w=64, h=64, fps=30, mix_db={},
                   ducking=False, duration_master=False) if callable(_p1f) else None
    except Exception as e:
        _m1e = "%s: %s" % (type(e).__name__, e)
    check("d24_passe_1_reelle_mesure_une_source_a_plus_de_2_db_de_la_cible",
          _gen3.returncode == 0 and isinstance(_m1, dict) and set(_m1) == {"I", "TP", "LRA", "thresh", "offset"}
          and -40 < _m1["I"] < 0 and abs(_m1["I"] + 14) > 2 and _m1["TP"] < 0
          and all(isinstance(v, float) for v in _m1.values()), (_gen3.returncode, _m1, _m1e))
    _out3 = os.path.join(TMP, "reel_loud.mp4")
    _rc3, _err3, _I3 = None, "", None
    try:
        _cmd3, _tot3 = MS._build_montage_command(
            [_spec3], [], _acl3, None, w=64, h=64, fps=30, mix_db={}, ducking=False,
            duration_master=False, preview=False, out=_out3, loudness=-14, loud_measured=_m1)
        _cmd3[0] = _FB
        _r3 = subprocess.run(_cmd3, capture_output=True, timeout=120)
        _rc3, _err3 = _r3.returncode, (_r3.stderr or b"")[-300:]
        _e3 = subprocess.run([_FB, "-hide_banner", "-nostats", "-i", _out3, "-filter_complex",
                              "[0:a]ebur128=peak=true:framelog=verbose[e]", "-map", "[e]", "-f", "null", "-"],
                             capture_output=True, text=True, timeout=60)
        from app.services import sfx_service as _sfx
        _I3 = _sfx.parse_ebur128(_e3.stderr).get("lufs_i")
    except Exception as e:
        _err3 = "%s: %s" % (type(e).__name__, e)
    check("d24_rendu_reel_normalise_a_14_lufs_mesure_par_ebur128_sur_la_sortie",
          _rc3 == 0 and isinstance(_I3, float) and -15.0 <= _I3 <= -13.0
          and isinstance(_m1, dict) and abs(_m1["I"] + 14) > 2, (_rc3, _I3, _m1, _err3))
    # Revue (23/09/2026) — mix REEL mais MUET (anullsrc encode en AAC) : la passe
    # 1 rend input_i "-inf" / target_offset "inf" (rc 0) ; la passe 1 doit rendre
    # None (rien a normaliser), la commande finale ne porte pas de loudnorm et
    # le rendu aboutit — et non un job failed « out of range » de ffmpeg.
    _SRCS = str(pathlib.Path(TMP) / "srcs.mp4")
    _gens = subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "testsrc2=s=64x64:r=25:d=3", "-f", "lavfi", "-i",
                            "anullsrc=channel_layout=stereo:sample_rate=44100", "-t", "3",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", _SRCS],
                           check=False, capture_output=True, timeout=60)
    _specs = V1SPEC(path=_SRCS, src_dur=3.0, start=0.0, end=3.0)
    _acls = [ASPEC(path=_SRCS, src_dur=3.0, end=3.0)]
    _ms, _mse = "NON_APPELE", ""
    try:
        _ms = _p1f([_specs], [], _acls, None, loudness=-14, w=64, h=64, fps=30, mix_db={},
                   ducking=False, duration_master=False) if callable(_p1f) else "ABSENT"
    except Exception as e:
        _mse = "%s: %s" % (type(e).__name__, e)
    # Temoin : la passe 1 BRUTE de cette source rend bien un JSON en -inf.
    _rawc, _ = _p1c([_specs], [], _acls, None, loudness=-14, **_ARGS) if callable(_p1c) else (None, None)
    _rawi = None
    if isinstance(_rawc, list):
        _rawc[0] = _FB
        _rawr = subprocess.run(_rawc, capture_output=True, text=True, timeout=60)
        _rawi = (_lp(_rawr.stderr) or {}).get("I") if callable(_lp) else None
    check("d24_passe_1_reelle_sur_un_mix_muet_rend_none_temoin_json_moins_inf",
          _gens.returncode == 0 and _rawi is not None and _rawi == float("-inf") and _ms is None,
          (_gens.returncode, _rawi, _ms, _mse))
    _outs = os.path.join(TMP, "reel_muet.mp4")
    _rcs, _errs, _cmds = None, "", ""
    try:
        _cs, _ = MS._build_montage_command(
            [_specs], [], _acls, None, w=64, h=64, fps=30, mix_db={}, ducking=False,
            duration_master=False, preview=False, out=_outs,
            loudness=(-14 if _ms is not None else None), loud_measured=_ms)
        _cmds = FLAT(_cs); _cs[0] = _FB
        _rs = subprocess.run(_cs, capture_output=True, timeout=120)
        _rcs, _errs = _rs.returncode, (_rs.stderr or b"")[-300:]
    except Exception as e:
        _errs = "%s: %s" % (type(e).__name__, e)
    check("d24_rendu_reel_du_mix_muet_aboutit_sans_loudnorm",
          _ms is None and _rcs == 0 and "[outa]" in _cmds and "loudnorm" not in _cmds
          and os.path.isfile(_outs) and os.path.getsize(_outs) > 0, (_ms, _rcs, _errs, _cmds[-200:]))
    # D-38 : plage [1, 2] → fichier d'environ 1,0 s (ffprobe).
    _outr = os.path.join(TMP, "reel_range.mp4")
    _rcr, _errr, _durr = None, "", None
    try:
        _cmdr, _ = MS._build_montage_command(
            [_spec3], [], _acl3, None, w=64, h=64, fps=30, mix_db={}, ducking=False,
            duration_master=False, preview=False, out=_outr, range_out=(1.0, 2.0))
        _cmdr[0] = _FB
        _rr_ = subprocess.run(_cmdr, capture_output=True, timeout=120)
        _rcr, _errr = _rr_.returncode, (_rr_.stderr or b"")[-300:]
        _pr = subprocess.run([str(pathlib.Path(_FB).with_name("ffprobe" + pathlib.Path(_FB).suffix)),
                              "-v", "error", "-show_entries", "format=duration", "-of",
                              "default=nw=1:nk=1", _outr], capture_output=True, text=True, timeout=60)
        _durr = float(_pr.stdout.strip())
    except Exception as e:
        _errr = "%s: %s" % (type(e).__name__, e)
    check("d38_rendu_reel_de_la_plage_1_2_dure_environ_1_s",
          _rcr == 0 and isinstance(_durr, float) and 0.85 <= _durr <= 1.2, (_rcr, _durr, _errr))

print("\n[6] espion /render : preset, fps, dimensions, extension")
_cap = {}
_vrai_build, _vrai_run = MS._build_montage_command, MS._run_ffmpeg


def _espion(*a, **k):
    _cap["preset"] = k.get("preset"); _cap["w"] = k.get("w"); _cap["h"] = k.get("h")
    _cap["fps"] = k.get("fps"); _cap["out"] = str(k.get("out"))
    _cap["loudness"] = k.get("loudness"); _cap["loud_measured"] = k.get("loud_measured")
    _cap["range_out"] = k.get("range_out"); _cap["n_build"] = _cap.get("n_build", 0) + 1
    _cmd = _vrai_build(*a, **k)
    _cap["cmd"] = FLAT(_cmd[0] if isinstance(_cmd, tuple) else _cmd)
    return _cmd


_MEAS_SPY = {"I": -21.5, "TP": -4.0, "LRA": 6.0, "thresh": -31.0, "offset": 0.1}
_vrai_p1 = A("_loudnorm_pass1", None)


def _espion_p1(*a, **k):
    """Passe 1 espionnee : note l'ordre (AVANT la commande finale) et la cible."""
    _cap["p1_calls"] = _cap.get("p1_calls", 0) + 1
    _cap["p1_loudness"] = k.get("loudness")
    _cap["p1_avant_build"] = _cap.get("n_build", 0) == 0
    return dict(_MEAS_SPY)


def _rendu(payload):
    _cap.clear()
    MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
    if callable(_vrai_p1):
        MS._loudnorm_pass1 = _espion_p1
    try:
        return c.post("/api/montage/render", json=payload)
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run
        if callable(_vrai_p1):
            MS._loudnorm_pass1 = _vrai_p1


def _titre(resp):
    jid = J(resp).get("job_id")
    return J(c.get("/api/jobs/%s" % jid)).get("title") if jid else None


_REAL = str(pathlib.Path(TMP) / "reel.mp4")
if _FB:
    shutil.copy(_SRC, _REAL)
else:
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc2=s=64x64:r=10:d=1", "-c:v", "libx264", "-pix_fmt",
                        "yuv420p", _REAL], check=False, capture_output=True, timeout=60)
    except Exception as _e:
        print("  (ffmpeg injoignable pour la source reelle : %s)" % _e)
_tl = TL("rendu", src=_REAL); _tl["preset"] = "web_4k"; _tl["fps"] = 60
_rr = _rendu(_tl); _pc = _cap.get("preset")
check("d35_render_web_4k_60_passe_un_preset_resolu_side_2160_w_2160_fps_60_mp4",
      _rr.status_code == 200 and isinstance(_pc, dict) and _pc.get("side") == 2160 and _pc.get("id") == "web_4k"
      and _cap.get("w") == 2160 and _cap.get("h") == 3840 and _cap.get("fps") == 60
      and _cap.get("out", "").endswith(".mp4") and "-r 60" in (_cap.get("cmd") or "")
      and "-crf 18" in (_cap.get("cmd") or "") and "_preview" not in _cap.get("out", "x"),
      (_rr.status_code, J(_rr).get("detail"), _pc and _pc.get("side"), _cap.get("w"), _cap.get("fps"), _cap.get("out")))
_tl = TL("rendu", src=_REAL); _tl["preset"] = "audio_wav"
_rr = _rendu(_tl)
check("d35_render_audio_wav_nomme_le_fichier_wav_et_vn",
      _rr.status_code == 200 and _cap.get("out", "").endswith(".wav") and "-vn" in (_cap.get("cmd") or "")
      and pathlib.Path(_cap.get("out", "")).name.startswith("montage_"),
      (_rr.status_code, _cap.get("out"), (_cap.get("cmd") or "")[-120:]))
_tl = TL("rendu", src=_REAL); _tl["ratio"] = "16:9"; _tl["preset"] = "social_720"
_rr = _rendu(_tl)
check("d35_render_social_720_en_16_9_donne_1280x720",
      _rr.status_code == 200 and (_cap.get("w"), _cap.get("h")) == (1280, 720) and _cap.get("fps") == 30,
      (_rr.status_code, _cap.get("w"), _cap.get("h")))
_tl = TL("rendu", src=_REAL); _tl["fps"] = 48
_rr = _rendu(_tl)
check("d35_render_fps_48_rend_400_sans_construire",
      _rr.status_code == 400 and "48" in str(J(_rr).get("detail")) and _cap.get("cmd") is None,
      (_rr.status_code, J(_rr).get("detail")))
_tl = TL("rendu", src=_REAL); _tl["preview"] = True; _tl["preset"] = "prores422"; _tl["fps"] = 60
_rr = _rendu(_tl)
check("d35_render_apercu_ignore_preset_et_fps_270x480_30_preview_mp4",
      _rr.status_code == 200 and (_cap.get("w"), _cap.get("h")) == (270, 480) and _cap.get("fps") == 30
      and _cap.get("out", "").endswith("_preview.mp4") and "prores" not in (_cap.get("cmd") or "x")
      and "-crf 30" in (_cap.get("cmd") or ""),
      (_rr.status_code, _cap.get("w"), _cap.get("h"), _cap.get("fps"), _cap.get("out")))
# Un preset MAISON traverse /render : base + surcharges.
c.put("/api/montage/deliver-presets", json={"presets": [
    {"id": "maison_r", "label": "R", "base": "social_720", "fps": 24, "crf": 28}]})
_tl = TL("rendu", src=_REAL); _tl["preset"] = "maison_r"
_rr = _rendu(_tl); _pc = _cap.get("preset")
check("d35_render_preset_maison_resolu_base_720_fps_24_crf_28",
      _rr.status_code == 200 and isinstance(_pc, dict) and _pc.get("id") == "social_720"
      and _cap.get("fps") == 24 and "-crf 28" in (_cap.get("cmd") or "") and "-r 24" in (_cap.get("cmd") or "")
      and (_cap.get("w"), _cap.get("h")) == (720, 1280),
      (_rr.status_code, _pc and _pc.get("id"), _cap.get("fps"), (_cap.get("cmd") or "")[-160:]))
_tl = TL("rendu", src=_REAL)
_rr = _rendu(_tl); _pc = _cap.get("preset")
check("d35_render_sans_preset_est_le_master_1080x1920_30_mp4",
      _rr.status_code == 200 and isinstance(_pc, dict) and _pc.get("id") == "master_1080"
      and (_cap.get("w"), _cap.get("h")) == (1080, 1920) and _cap.get("fps") == 30
      and _cap.get("out", "").endswith(".mp4") and _QUEUE_HIST in (_cap.get("cmd") or ""),
      (_rr.status_code, _pc and _pc.get("id"), _cap.get("w"), _cap.get("fps")))
_t_master = _titre(_rr)
_tl = TL("rendu", src=_REAL); _tl["preset"] = "web_4k"
_rr = _rendu(_tl); _t_4k = _titre(_rr)
check("t2_le_titre_du_job_final_porte_le_libelle_du_preset_sauf_master",
      _rr.status_code == 200 and _t_4k == "rendu (Web 4K (H.264))" and _t_master == "rendu"
      and "(" not in (_t_master or "("), (_t_master, _t_4k))
_tl = TL("rendu", src=_REAL); _tl["preset"] = "maison_r"
_rr = _rendu(_tl); _t_m = _titre(_rr)
check("t2_le_titre_porte_le_libelle_du_preset_maison",
      _rr.status_code == 200 and _t_m == "rendu (R)", _t_m)
_tl = TL("rendu", src=_REAL); _tl["preview"] = True; _tl["preset"] = "web_4k"
_rr = _rendu(_tl); _t_p = _titre(_rr)
check("t2_l_apercu_ne_porte_pas_le_libelle_du_preset",
      _rr.status_code == 200 and _t_p == "rendu (aperçu 480p)", _t_p)
# --- D-24 : passe 1 espionnee, appelee AVANT la commande, mesure transmise.
# Le mix vient des pistes AUDIO (a1…), pas du son du clip V1 : sans clip
# audio le mix est anullsrc et il n'y a RIEN a normaliser (temoin plus bas).
def TLA(**kw):
    t = TL("rendu", src=_REAL)
    t["clips"].append({"tr": "a1", "id": "a1", "start": 0, "end": 4, "src": {"file_path": _REAL}})
    t.update(kw)
    return t
_tl = TLA(loudness=-14)
_rr = _rendu(_tl)
check("d24_render_loudness_14_appelle_la_passe_1_avant_la_commande_et_transmet_la_mesure",
      _rr.status_code == 200 and _cap.get("p1_calls") == 1 and _cap.get("p1_loudness") == -14
      and _cap.get("p1_avant_build") is True and _cap.get("loudness") == -14
      and _cap.get("loud_measured") == _MEAS_SPY
      and "measured_I=-21.5:measured_TP=-4:measured_LRA=6:measured_thresh=-31:offset=0.1:linear=true" in (_cap.get("cmd") or "")
      and "-map [outn]" in (_cap.get("cmd") or ""),
      (_rr.status_code, J(_rr).get("detail"), {k: v for k, v in _cap.items() if k != "cmd"}, (_cap.get("cmd") or "")[-260:]))
_tl = TL("rendu", src=_REAL); _tl["loudness"] = -14          # AUCUNE piste audio
_rr = _rendu(_tl)
check("d24_render_loudness_sans_piste_audio_anullsrc_temoin_aucune_chaine",
      _rr.status_code == 200 and "anullsrc" in (_cap.get("cmd") or "") and "loudnorm" not in (_cap.get("cmd") or "x")
      and "-map 1:a" in (_cap.get("cmd") or ""), (_rr.status_code, (_cap.get("cmd") or "")[-200:]))
# Revue (23/09/2026) : passe 1 qui rend None (mix vide OU muet) → la commande
# finale part SANS loudness (meme sort qu'anullsrc), pas en ValueError.
def _p1_none(*a, **k):
    _cap["p1_calls"] = _cap.get("p1_calls", 0) + 1
    return None
_tl = TLA(loudness=-14)
_cap.clear()
MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
if callable(_vrai_p1):
    MS._loudnorm_pass1 = _p1_none
try:
    _rr = c.post("/api/montage/render", json=_tl)
finally:
    MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run
    if callable(_vrai_p1):
        MS._loudnorm_pass1 = _vrai_p1
_jn = J(c.get("/api/jobs/%s" % J(_rr).get("job_id")))
check("d24_render_passe_1_none_mix_muet_rend_sans_loudness_et_le_job_aboutit",
      _rr.status_code == 200 and _cap.get("p1_calls") == 1 and _cap.get("cmd") is not None
      and "[outa]" in _cap["cmd"] and "loudnorm" not in _cap["cmd"] and "loudness" in _cap
      and _cap.get("loudness") is None and _jn.get("status") == "done",
      (_rr.status_code, _cap.get("p1_calls"), _cap.get("loudness"), _jn.get("status"), _jn.get("error")))
# M1 : le GIF jette le mix (anullsink) → pas de passe 1 ; l'audio seul la garde.
# Trouve par ce banc (23/09/2026) : /render passait fps = 12 au GIF et la garde
# de cadence le refusait (« cadence 12 hors de… ») — bug T1, le GIF est exempte.
_rr = _rendu(TLA(preset="gif_480"))
_jg = J(c.get("/api/jobs/%s" % J(_rr).get("job_id")))
check("d35_render_gif_480_aboutit_a_12_i_s_sans_passe_1",
      _rr.status_code == 200 and _cap.get("cmd") is not None and "paletteuse" in _cap["cmd"]
      and _cap.get("fps") == 12 and "-r 12" in _cap["cmd"] and _cap.get("out", "").endswith(".gif")
      and _jg.get("status") == "done" and _cap.get("p1_calls") is None,
      (_rr.status_code, _cap.get("fps"), _jg.get("status"), _jg.get("error")))
_rr = _rendu(TLA(loudness=-14, preset="gif_480"))
_jg = J(c.get("/api/jobs/%s" % J(_rr).get("job_id")))
check("d24_render_gif_avec_loudness_n_appelle_pas_la_passe_1",
      _rr.status_code == 200 and _cap.get("cmd") is not None and "paletteuse" in _cap["cmd"]
      and "[outa]anullsink" in _cap["cmd"] and _cap.get("p1_calls") is None
      and "loudnorm" not in _cap["cmd"] and _jg.get("status") == "done",
      (_rr.status_code, _cap.get("p1_calls"), _jg.get("status"), _jg.get("error"), (_cap.get("cmd") or "")[-160:]))
_rr = _rendu(TLA(loudness=-14, preset="audio_wav"))
check("d24_render_audio_seul_avec_loudness_garde_la_passe_1",
      _rr.status_code == 200 and _cap.get("p1_calls") == 1 and "-vn" in (_cap.get("cmd") or "")
      and "-map [outn]" in (_cap.get("cmd") or ""), (_rr.status_code, _cap.get("p1_calls")))
_tl = TL("rendu", src=_REAL); _tl["loudness"] = -19
_rr = _rendu(_tl)
check("d24_render_loudness_19_rend_400_sans_passe_1_ni_commande",
      _rr.status_code == 400 and "loudness" in str(J(_rr).get("detail")).lower()
      and _cap.get("p1_calls") is None and _cap.get("cmd") is None, (_rr.status_code, J(_rr).get("detail")))
_tl = TL("rendu", src=_REAL); _tl["loudness"] = "-14"
_rr = _rendu(_tl)
check("d24_render_loudness_chaine_rend_400",
      _rr.status_code == 400 and _cap.get("cmd") is None, (_rr.status_code, J(_rr).get("detail")))
_tl = TL("rendu", src=_REAL); _tl["loudness"] = -14; _tl["preview"] = True
_rr = _rendu(_tl)
check("d24_render_apercu_avec_loudness_n_appelle_pas_la_passe_1",
      _rr.status_code == 200 and _cap.get("p1_calls") is None and _cap.get("cmd") is not None
      and "loudnorm" not in (_cap.get("cmd") or "x"), (_rr.status_code, _cap.get("p1_calls")))
_tl = TL("rendu", src=_REAL)
_rr = _rendu(_tl)
# Revue (23/09/2026) : les negations exigent le TEMOIN de capture — `cmd` pose
# et cle `loudness` presente — sinon un `_run` jamais lance passerait a vide.
check("d24_render_sans_loudness_n_appelle_pas_la_passe_1_et_loudness_est_none",
      _rr.status_code == 200 and _cap.get("cmd") is not None and "ffmpeg" in _cap["cmd"]
      and "loudness" in _cap and "loud_measured" in _cap
      and _cap.get("p1_calls") is None and _cap.get("loudness") is None
      and _cap.get("loud_measured") is None and "loudnorm" not in _cap["cmd"],
      (_cap.get("p1_calls"), sorted(_cap)))
# Passe 1 qui ECHOUE → job failed avec le message, pas de commande finale.
def _p1_echec(*a, **k):
    _cap["p1_calls"] = _cap.get("p1_calls", 0) + 1
    raise RuntimeError("passe 1 cassee pour le banc")
_tl = TL("rendu", src=_REAL); _tl["loudness"] = -16
_cap.clear()
MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
if callable(_vrai_p1):
    MS._loudnorm_pass1 = _p1_echec
try:
    _rr = c.post("/api/montage/render", json=_tl)
finally:
    MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run
    if callable(_vrai_p1):
        MS._loudnorm_pass1 = _vrai_p1
_jf = J(c.get("/api/jobs/%s" % J(_rr).get("job_id")))
check("d24_render_passe_1_en_echec_met_le_job_en_failed_avec_le_message_sans_commande_finale",
      _rr.status_code == 200 and _cap.get("p1_calls") == 1 and _cap.get("cmd") is None
      and _jf.get("status") == "failed" and "passe 1 cassee" in str(_jf.get("error")),
      (_rr.status_code, _cap.get("p1_calls"), _jf.get("status"), _jf.get("error")))
# --- D-38 : plage validee contre le total estime (max(end) des clips = 4).
# La source reelle dure 2 s (la timeline dit 4) : [1,5] passe l'estimation
# (max(end) = 4) ET la commande (total reel 2) → -ss 1.0 -t 1.0.
_tl = TL("rendu", src=_REAL); _tl["range"] = [1, 5]
_rr = _rendu(_tl)
check("d38_render_range_1_5_transmet_range_out_1_0_5_0_et_la_commande_porte_ss_1_t_1",
      _rr.status_code == 200 and _cap.get("range_out") == (1.0, 5.0)
      and isinstance(_cap.get("range_out"), tuple) and "-ss 1.0 -t 1.0 " in (_cap.get("cmd") or ""),
      (_rr.status_code, J(_rr).get("detail"), _cap.get("range_out"), (_cap.get("cmd") or "")[-160:]))
_codes_r = {}
for _k, _v in {"inversee": [5, 2], "a_egal_total": [4, 6], "negatif": [-1, 2], "vide": [1, 1],
               "pas_un_couple": [1], "non_numerique": ["a", "b"], "objet": {"in": 1, "out": 2}}.items():
    _tl = TL("rendu", src=_REAL); _tl["range"] = _v
    _rr = _rendu(_tl)
    _codes_r[_k] = (_rr.status_code, str(J(_rr).get("detail"))[:40], _cap.get("cmd") is None)
check("d38_render_plages_invalides_rendent_400_plage_invalide_sans_commande",
      len(_codes_r) == 7 and all(v[0] == 400 and "plage" in v[1].lower() and v[2] for v in _codes_r.values()),
      _codes_r)
_tl = TL("rendu", src=_REAL)
_rr = _rendu(_tl)
# Observation datee (23/09/2026) : /render accepte range:["1","5"] (float()
# des bornes) mais refuse loudness:"-14" (nombre exige) — asymetrie tolerée,
# pas une exigence.
check("d38_render_sans_range_transmet_none",
      _rr.status_code == 200 and _cap.get("cmd") is not None and "ffmpeg" in _cap["cmd"]
      and "range_out" in _cap and _cap.get("range_out") is None and "-ss" not in _cap["cmd"],
      (_cap.get("range_out"), sorted(_cap)))
_tl = TL("rendu", src=_REAL); _tl["range"] = None
_rr = _rendu(_tl)
check("d38_render_range_null_est_l_historique",
      _rr.status_code == 200 and _cap.get("range_out") is None, (_rr.status_code, _cap.get("range_out")))

print("\n[5] D-36 file locale de rendus executee en serie (un worker asyncio)")
# Espion `_run_ffmpeg` : dort 0,3 s dans le thread (asyncio.to_thread), ecrit
# le fichier, note (debut, fin) par nom de sortie ; `_q_boom` fait LEVER le
# prochain appel (job en echec dans la file). ETAT VIDE MESURE (23/09/2026,
# 109/7) : le TestClient execute `background_tasks` AVANT le retour de
# `post()`, donc sans implementation les trois rendus tournent DEJA en serie
# et le check « serie » reste VERT — il vise la mutation T5 « worker
# parallele » (un `create_task` par element), pas l'etat vide. Ce qui rougit
# a l'etat vide : reponse sans `queued`/`position`, 3e job lu `done` au lieu
# de `queued`, liste sans `queued`, temoin de chevauchement de l'immediat,
# apercu en file rendu 200 au lieu de 400, positions None.
_q_times = {}
_q_boom = {"on": False}


def _espion_dort(cmd, out):
    t0 = time.time()
    time.sleep(0.3)
    if _q_boom["on"]:
        _q_boom["on"] = False
        _q_times[pathlib.Path(str(out)).name] = (t0, time.time())
        raise RuntimeError("ffmpeg casse pour la file")
    pathlib.Path(str(out)).write_bytes(b"x")
    _q_times[pathlib.Path(str(out)).name] = (t0, time.time())
    return out


def _attend(jids, attente=3.0):
    """Poll GET /api/jobs/{id} jusqu'a done/failed pour tous ; rend {id: job}."""
    t0 = time.time()
    res = {}
    while time.time() - t0 < attente:
        res = {j: J(c.get("/api/jobs/%s" % j)) for j in jids}
        if all(v.get("status") in ("done", "failed") for v in res.values()):
            break
        time.sleep(0.05)
    return res


def _fen(j):
    """(debut, fin) de l'espion pour un job, via son nom de fichier."""
    return _q_times.get(str(j.get("image_filename") or ""), (None, None))


MS._run_ffmpeg = _espion_dort
try:
    _rq = []
    for _i in range(3):
        _tl = TL("file%d" % _i, src=_REAL); _tl["queue"] = True
        _rq.append(c.post("/api/montage/render", json=_tl))
    _tli = TL("immediat", src=_REAL)
    _ri = c.post("/api/montage/render", json=_tli)
    _ids = [J(r).get("job_id") for r in _rq]
    _j2_0 = J(c.get("/api/jobs/%s" % _ids[2]))
    _liste0 = J(c.get("/api/jobs?providers=montage")).get("_liste") or []
    _tlp = TL("apercu", src=_REAL); _tlp["queue"] = True; _tlp["preview"] = True
    _rp = c.post("/api/montage/render", json=_tlp)
    _jobs = _attend(_ids + [J(_ri).get("job_id")])
finally:
    MS._run_ffmpeg = _vrai_run

check("d36_trois_post_queue_true_rendent_trois_job_id_distincts_et_position_1_2_3",
      all(r.status_code == 200 for r in _rq) and len(set(_ids)) == 3 and all(_ids)
      and [J(r).get("position") for r in _rq] == [1, 2, 3]
      and all(J(r).get("queued") is True for r in _rq),
      ([r.status_code for r in _rq], [J(r).get("position") for r in _rq], [str(J(r).get("detail"))[:60] for r in _rq]))
check("d36_le_troisieme_job_nait_queued_progress_0_en_file_lu_par_get_jobs_id",
      _j2_0.get("status") == "queued" and _j2_0.get("progress") == 0
      and "file" in str(_j2_0.get("current_step") or "").lower(),
      (_j2_0.get("status"), _j2_0.get("progress"), _j2_0.get("current_step")))
check("d36_get_api_jobs_providers_montage_montre_au_moins_un_queued_pendant_l_attente",
      len(_liste0) >= 4 and any(j.get("status") == "queued" for j in _liste0)
      and any(j.get("job_id") == _ids[2] for j in _liste0),
      (len(_liste0), [j.get("status") for j in _liste0][:8]))
_jq3 = [_jobs.get(j, {}) for j in _ids]
_fq = [_fen(j) for j in _jq3]
check("d36_les_trois_jobs_en_file_sont_done_avec_un_fichier_et_une_fenetre_mesuree",
      all(j.get("status") == "done" for j in _jq3) and all(f[0] is not None for f in _fq)
      and all(j.get("final_video_path") and os.path.isfile(j["final_video_path"]) for j in _jq3),
      ([j.get("status") for j in _jq3], [j.get("error") for j in _jq3], _fq))
check("d36_les_trois_jobs_en_file_s_executent_en_serie_start_k1_superieur_ou_egal_a_end_k",
      all(f[0] is not None for f in _fq) and _fq[1][0] >= _fq[0][1] and _fq[2][0] >= _fq[1][1]
      and _fq[0][1] - _fq[0][0] >= 0.25,
      _fq)
_ji = _jobs.get(J(_ri).get("job_id"), {})
_fi = _fen(_ji)
check("d36_un_post_sans_queue_pendant_la_file_demarre_immediatement_temoin_chevauchement",
      _ri.status_code == 200 and "queued" not in J(_ri) and _ji.get("status") == "done"
      and _fi[0] is not None and _fq[0][1] is not None and _fi[0] < _fq[0][1]
      and _fi[0] < _fq[2][0],
      (_ri.status_code, _ji.get("status"), _fi, _fq[0], _fq[2]))
check("d36_queue_true_et_preview_true_rend_400_la_file_est_reservee_aux_rendus_finaux",
      _rp.status_code == 400 and "file" in str(J(_rp).get("detail")).lower()
      and J(_rp).get("job_id") is None,
      (_rp.status_code, str(J(_rp).get("detail"))[:100]))

# Un job en file dont `_run_ffmpeg` LEVE → failed avec le message, et le
# suivant s'execute quand meme (la file continue, apres lui).
MS._run_ffmpeg = _espion_dort
try:
    _q_boom["on"] = True
    _tl = TL("casse", src=_REAL); _tl["queue"] = True
    _rf = c.post("/api/montage/render", json=_tl)
    _tl = TL("apres", src=_REAL); _tl["queue"] = True
    _rs = c.post("/api/montage/render", json=_tl)
    _jobs2 = _attend([J(_rf).get("job_id"), J(_rs).get("job_id")])
finally:
    MS._run_ffmpeg = _vrai_run
    _q_boom["on"] = False
_jf2 = _jobs2.get(J(_rf).get("job_id"), {}); _js2 = _jobs2.get(J(_rs).get("job_id"), {})
_ff, _fs = _fen(_jf2), _fen(_js2)
check("d36_un_job_en_file_qui_leve_passe_failed_avec_le_message_et_le_suivant_s_execute_apres_lui",
      _rf.status_code == 200 and _rs.status_code == 200
      and _jf2.get("status") == "failed" and "ffmpeg casse" in str(_jf2.get("error"))
      and _js2.get("status") == "done" and _ff[1] is not None and _fs[0] is not None
      and _fs[0] >= _ff[1],
      (_jf2.get("status"), str(_jf2.get("error"))[:80], _js2.get("status"), _ff, _fs))
check("d36_les_positions_repartent_a_1_quand_la_file_est_vide",
      J(_rf).get("position") == 1 and J(_rs).get("position") == 2,
      (J(_rf).get("position"), J(_rs).get("position")))

print("\n[6] (suite) espion /render : queue:true → reponse {queued, position}, sans → non")
def _rendu_q(payload, attente=3.0):
    """POST /render avec `_run_ffmpeg` REMPLACE pour toute la vie du job (un
    job en file s'execute APRES la reponse : `_rendu` qui restaure dans son
    `finally` laisserait le vrai ffmpeg tourner). Attend la fin du job."""
    _cap.clear()
    MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
    try:
        r = c.post("/api/montage/render", json=payload)
        _cap["queued"] = J(r).get("queued"); _cap["position"] = J(r).get("position")
        jid = J(r).get("job_id"); _cap["st0"] = None
        if jid:
            _cap["st0"] = J(c.get("/api/jobs/%s" % jid)).get("status")
            t0 = time.time()
            while time.time() - t0 < attente:
                st = J(c.get("/api/jobs/%s" % jid)).get("status")
                if st in ("done", "failed"):
                    break
                time.sleep(0.05)
        return r
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run


_tl = TL("rendu", src=_REAL); _tl["queue"] = True
_rr = _rendu_q(_tl)
_jq = J(c.get("/api/jobs/%s" % J(_rr).get("job_id")))
check("d36_espion_queue_true_la_reponse_porte_queued_et_position_et_le_job_aboutit",
      _rr.status_code == 200 and "queued" in _cap and _cap.get("queued") is True
      and isinstance(_cap.get("position"), int) and _cap.get("position") >= 1
      and _cap.get("cmd") is not None and _jq.get("status") == "done",
      (_rr.status_code, J(_rr).get("detail"), _cap.get("queued"), _cap.get("position"), _jq.get("status"), _jq.get("error")))
_tl = TL("rendu", src=_REAL)
_rr = _rendu_q(_tl)
check("d36_espion_sans_queue_la_reponse_ne_porte_ni_queued_ni_position_temoin_job_id",
      _rr.status_code == 200 and J(_rr).get("job_id") and "queued" in _cap and _cap.get("queued") is None
      and _cap.get("position") is None and _cap.get("st0") in ("generating_video", "done"),
      (_rr.status_code, sorted(J(_rr)), _cap.get("st0")))

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
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
