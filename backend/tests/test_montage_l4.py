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
Sections [3] D-24, [4] D-38, [5] D-36 : taches 2 et 3 du plan L4.
"""
import json, os, sys, tempfile, subprocess, pathlib, shutil
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
    clip = {k: kw.pop(k) for k in ("dz", "speed", "retime", "stab", "src_in") if k in kw}
    a = {"w": 64, "h": 64, "fps": 30, "mix_db": {}, "ducking": False,
         "duration_master": False, "preview": False,
         "out": os.path.join(TMP, "o.mp4")}
    a.update(kw)
    ac = [ASPEC()] if a.pop("_audio", False) else []
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

print("\n[6] espion /render : preset, fps, dimensions, extension")
_cap = {}
_vrai_build, _vrai_run = MS._build_montage_command, MS._run_ffmpeg


def _espion(*a, **k):
    _cap["preset"] = k.get("preset"); _cap["w"] = k.get("w"); _cap["h"] = k.get("h")
    _cap["fps"] = k.get("fps"); _cap["out"] = str(k.get("out"))
    _cmd = _vrai_build(*a, **k)
    _cap["cmd"] = FLAT(_cmd[0] if isinstance(_cmd, tuple) else _cmd)
    return _cmd


def _rendu(payload):
    _cap.clear()
    MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
    try:
        return c.post("/api/montage/render", json=payload)
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run


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
