# -*- coding: utf-8 -*-
"""L7-B — les services backend du lot (24/09/2026). En-tete recopie de
test_montage_l7.py (env, check, A) : dossier de donnees NEUF par execution,
toute lecture gardee — un banc qui meurt sur un acces nu ne dit pas quelles
assertions manquent.
Run : & $PY tests/test_montage_l7b.py   (depuis backend/)

[1] D-37 EXPORT EDL (CMX 3600) + FCPXML. Service PUR `app.services.edl_export`
(`src_key`, `to_edl(rec, resolve, fps, meta)`, `to_fcpxml(rec, resolve, fps,
size, meta)`) et route `GET /api/montage/export?format=edl|fcpxml`.
Projet de test (30 i/s) : deux plans V1 de sources testsrc2 generees en TMP
(plan1 srcIn 1,0 de 0 a 1,5 s en coupe ; plan2 srcIn 0 de 1,5 a 2,5 s en
`fade` 0,4 s et vitesse x2), une voix A1 (0,5 → 2,0 s, srcIn 0,2), un
titre t1. TIMECODES CALCULES A LA MAIN (30 i/s, non-drop) :
  plan1 : rec 0 → 45 images = 00:00:00:00 → 00:00:01:15 ;
          src 30 → 75       = 00:00:01:00 → 00:00:02:15 ;
  plan2 : rec 45 → 75       = 00:00:01:15 → 00:00:02:15 ;
          src 0 → 0 + 30×2  = 00:00:00:00 → 00:00:02:00 (vitesse x2) ;
          fondu 0,4 s       = 12 images → evenement « D 012 » precede de la
          ligne sortante de plan1 a longueur nulle (src 00:00:02:15) ;
          M2 : 30 × 2 = « 060.0 » ;
  voix  : rec 15 → 60       = 00:00:00:15 → 00:00:02:00 ;
          src 6 → 51        = 00:00:00:06 → 00:00:01:21.
FCPXML parse par xml.etree : version, format 1/30s 1080x1920 (9:16), une
ressource `asset` par source avec `media-rep` `file:///`, toute reference
`ref`/`format` resolue, toute duree `^\\d+/30s$|^0s$`, spine = plan1 puis
plan2 (timeMap 0→0, 45/30s→90/30s), voix ANCREE sous plan1 en lane -1 a
offset 30 + 15 = 45/30s (temps local du parent).
Route : espion `_load_saved` ; 200 + Content-Disposition ; 400 sans
timeline, timeline vide, format inconnu.
Regle des assertions negatives : chaque « pas de X » est precede dans la
MEME expression du temoin positif qui prouve que la mesure a eu lieu.
"""
import os, sys, re, tempfile, subprocess, pathlib, shutil, asyncio
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl7b_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.services import montage_service as MS           # noqa: E402
try:
    from app.services import edl_export as EX             # noqa: E402
except Exception as _e:                                    # faute n°6 : rougir, pas mourir
    print("  (edl_export introuvable : %s)" % _e)
    EX = None

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def A(nom, defaut):
    return getattr(MS, nom, defaut)


def X(nom):
    """Une fonction du service, ou un temoin qui rend une chaine d'erreur."""
    f = getattr(EX, nom, None) if EX is not None else None
    if f is None:
        return lambda *a, **k: "ABSENT: %s" % nom
    def g(*a, **k):
        try:
            return f(*a, **k)
        except Exception as e:
            return "%s: %s" % (type(e).__name__, e)
    return g


# ── sources : testsrc2 + sine generees (repli : un octet — la route resout
# encore un file_path qui existe, seule la sonde de duree rend 0)
_FB = None
S1 = str(pathlib.Path(TMP) / "plan1.mp4")
S2 = str(pathlib.Path(TMP) / "plan2.mp4")
VX = str(pathlib.Path(TMP) / "voix.wav")
try:
    from app.services.effects_preview import ffmpeg_bin as _fb
    _FB = _fb()
    # ffprobe voisin de ffmpeg : les sondes de montage_service l'appellent par son nom
    os.environ["PATH"] = os.path.dirname(_FB) + os.pathsep + os.environ.get("PATH", "")
    for _dst, _args in ((S1, ["-f", "lavfi", "-i", "testsrc2=s=64x64:r=30:d=3", "-f", "lavfi", "-i",
                              "sine=frequency=440:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                              "-c:a", "aac", "-shortest"]),
                        (S2, ["-f", "lavfi", "-i", "testsrc2=s=64x64:r=30:d=3", "-c:v", "libx264",
                              "-pix_fmt", "yuv420p"]),
                        (VX, ["-f", "lavfi", "-i", "sine=frequency=220:duration=2"])):
        _g = subprocess.run([_FB, "-y", "-loglevel", "error"] + _args + [_dst],
                            check=False, capture_output=True, timeout=60)
        if _g.returncode != 0 or not os.path.isfile(_dst):
            _FB = None
            print("  (generation ffmpeg en echec : %r)" % _g.stderr[-300:])
            break
except Exception as _e:
    _FB = None
    print("  (ffmpeg injoignable : %s)" % _e)
for _p in (S1, S2, VX):
    if not os.path.isfile(_p):
        pathlib.Path(_p).write_bytes(b"x")


def REC():
    return {"name": "Essai export", "ratio": "9:16", "duration": 2.5, "mix": {},
            "tracks": [{"id": "v1", "kind": "video"}, {"id": "t1", "kind": "title"},
                       {"id": "a1", "kind": "audio", "bus": "dialogue"}],
            "clips": [
                {"tr": "v1", "id": "p1", "label": "plan1", "src": {"file_path": S1},
                 "srcIn": 1.0, "start": 0.0, "end": 1.5, "transition": "cut", "transition_s": 0},
                {"tr": "v1", "id": "p2", "label": "plan2", "src": {"file_path": S2},
                 "srcIn": 0.0, "start": 1.5, "end": 2.5, "transition": "fade", "transition_s": 0.4,
                 "speed": 2},
                {"tr": "t1", "id": "t1a", "label": "Titre", "text": "Bonjour", "start": 0.0, "end": 1.0},
                {"tr": "a1", "id": "vx", "label": "voix", "src": {"file_path": VX},
                 "srcIn": 0.2, "start": 0.5, "end": 2.0}]}


def RES():
    k = X("src_key")
    return {k({"file_path": S1}): {"path": S1, "dur": 3.0, "audio": True, "video": True},
            k({"file_path": S2}): {"path": S2, "dur": 3.0, "audio": False, "video": True},
            k({"file_path": VX}): {"path": VX, "dur": 2.0, "audio": True, "video": False}}


def META(rec):
    try:
        return MS._tracks_meta(rec.get("tracks"))
    except Exception:
        return None


print("\n[1] D-37 export EDL (CMX 3600) et FCPXML")
check("d37_le_service_edl_export_existe_avec_src_key_to_edl_to_fcpxml",
      EX is not None and all(callable(getattr(EX, n, None)) for n in ("src_key", "to_edl", "to_fcpxml")),
      "EX=%r" % (EX,))

_rec = REC()
_edl = X("to_edl")(_rec, RES(), fps=30, meta=META(_rec))
_edl = _edl if isinstance(_edl, str) else "NON-STR: %r" % (_edl,)
_lines = [l for l in _edl.splitlines() if l.strip()]
_ATT = [
    "TITLE: Essai export",
    "FCM: NON-DROP FRAME",
    "001  AX       V     C        00:00:01:00 00:00:02:15 00:00:00:00 00:00:01:15",
    "* FROM CLIP NAME: plan1",
    "* SOURCE FILE: " + S1,
    "002  AX       V     C        00:00:02:15 00:00:02:15 00:00:01:15 00:00:01:15",
    "002  AX       V     D    012 00:00:00:00 00:00:02:00 00:00:01:15 00:00:02:15",
    "M2   AX       060.0                00:00:00:00",
    "* FROM CLIP NAME: plan1",
    "* TO CLIP NAME: plan2",
    "* SPEED: 2",
    "* SOURCE FILE: " + S2,
    "003  AX       A     C        00:00:00:06 00:00:01:21 00:00:00:15 00:00:02:00",
    "* FROM CLIP NAME: voix",
    "* SOURCE FILE: " + VX,
    "* SKIPPED: title Titre",
]
check("d37_edl_lignes_exactes_timecodes_calcules_a_la_main",
      _lines == _ATT,
      "\n".join("  %s %r" % ("==" if i < len(_ATT) and l == _ATT[i] else "!=", l) for i, l in enumerate(_lines))
      + "\n  attendu=%d obtenu=%d" % (len(_ATT), len(_lines)))
check("d37_edl_crlf_et_ligne_vide_apres_l_entete",
      "\r\n" in _edl and _edl.startswith("TITLE: Essai export\r\nFCM: NON-DROP FRAME\r\n\r\n001  "),
      repr(_edl[:80]))
# chaque ligne d'evenement a la meme gabarit : 3 chiffres, bobine 8, piste 5, transition 4, duree 3, quatre TC
_ev = [l for l in _lines if re.match(r"^\d{3}  ", l)]
check("d37_edl_quatre_lignes_d_evenement_au_gabarit_cmx",
      len(_ev) == 4 and all(re.match(r"^\d{3}  .{8} .{5} .{4} .{3} (\d\d:\d\d:\d\d:\d\d ){3}\d\d:\d\d:\d\d:\d\d$", l) for l in _ev),
      _ev)

# variantes : trou avant un fondu -> BL ; transition non exportee ; sources introuvables, overlay, sous-titres
_r2 = {"name": "v", "ratio": "16:9", "tracks": [{"id": "v2", "kind": "video"}, {"id": "v1", "kind": "video"},
                                                {"id": "s1", "kind": "subs"}, {"id": "j1", "kind": "adjust"}],
       "clips": [
           {"tr": "v1", "id": "a", "label": "A", "src": {"file_path": S1}, "srcIn": 0, "start": 0, "end": 1,
            "transition": "cut"},
           {"tr": "v1", "id": "b", "label": "B", "src": {"file_path": S2}, "srcIn": 0, "start": 2, "end": 3,
            "transition": "dissolve", "transition_s": 0.5},
           {"tr": "v1", "id": "c", "label": "C", "src": {"file_path": S1}, "srcIn": 0, "start": 3, "end": 4,
            "transition": "slideleft", "transition_s": 0.4},
           {"tr": "v1", "id": "d", "label": "D", "src": {"file_path": "Z:/absent.mp4"}, "srcIn": 0,
            "start": 4, "end": 5},
           {"tr": "v2", "id": "o", "label": "logo", "src": {"image": "logo.png"}, "start": 0, "end": 2},
           {"tr": "s1", "id": "s_1", "text": "un", "start": 0, "end": 1},
           {"tr": "s1", "id": "s_2", "text": "deux", "start": 1, "end": 2},
           {"tr": "j1", "id": "aj", "label": "Ajust", "start": 0, "end": 1, "effects": []}]}
_e2 = X("to_edl")(_r2, RES(), fps=30, meta=META(_r2))
_e2 = _e2 if isinstance(_e2, str) else ""
_l2 = [l for l in _e2.splitlines() if l.strip()]
check("d37_edl_fondu_apres_un_trou_part_du_noir_BL_duree_15_images",
      "002  BL       V     C        00:00:00:00 00:00:00:00 00:00:02:00 00:00:02:00" in _l2
      and "002  AX       V     D    015 00:00:00:00 00:00:01:00 00:00:02:00 00:00:03:00" in _l2
      and "* TO CLIP NAME: B" in _l2, _l2)
check("d37_edl_transition_non_exportee_dite_en_commentaire_et_coupe_C",
      "003  AX       V     C        00:00:00:00 00:00:01:00 00:00:03:00 00:00:04:00" in _l2
      and "* TRANSITION: slideleft (non exportée)" in _l2
      # temoin : la coupe franche de A n'a PAS de commentaire de transition
      and "001  AX       V     C        00:00:00:00 00:00:01:00 00:00:00:00 00:00:01:00" in _l2
      and sum(1 for l in _l2 if l.startswith("* TRANSITION:")) == 1, _l2)
check("d37_edl_source_introuvable_overlay_sous_titres_ajustement_SKIPPED",
      "* SKIPPED: source introuvable D" in _l2 and "* SKIPPED: overlay logo" in _l2
      and "* SKIPPED: subs s1 (2 segments)" in _l2 and "* SKIPPED: adjust Ajust" in _l2
      # temoin : trois evenements seulement (A, B, C) — D n'en a pas
      and len([l for l in _l2 if re.match(r"^\d{3}  AX       V     [CD] ", l)]) == 3
      and not any(l.startswith("004") for l in _l2), _l2)
check("d37_edl_sans_timeline_rend_l_entete_seule",
      X("to_edl")({"name": "x", "clips": []}, {}, fps=30) == "TITLE: x\r\nFCM: NON-DROP FRAME\r\n\r\n",
      repr(X("to_edl")({"name": "x", "clips": []}, {}, fps=30)))

# ── FCPXML
_fx = X("to_fcpxml")(_rec, RES(), fps=30, size=(1080, 1920), meta=META(_rec))
_fx = _fx if isinstance(_fx, str) else "NON-STR: %r" % (_fx,)
try:
    _root = ET.fromstring(_fx.encode("utf-8"))
except Exception as _e:
    print("  (FCPXML illisible : %s)" % _e)
    _root = ET.Element("illisible")
_res = _root.find("resources")
_ids = {e.get("id") for e in (_res if _res is not None else [])}
_fmt = _res.find("format") if _res is not None else None
_assets = _res.findall("asset") if _res is not None else []
check("d37_fcpxml_version_1_9_entete_doctype_format_1_30s_1080x1920",
      _root.tag == "fcpxml" and _root.get("version") == "1.9"
      and _fx.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.9">')
      and _fmt is not None and _fmt.get("frameDuration") == "1/30s"
      and _fmt.get("width") == "1080" and _fmt.get("height") == "1920",
      (_root.tag, _root.get("version"), _fx[:120]))
_mr = [a.find("media-rep") for a in _assets]
check("d37_fcpxml_trois_assets_media_rep_original_file_uri_uid",
      len(_assets) == 3 and all(m is not None and m.get("kind") == "original-media"
                                and (m.get("src") or "").startswith("file:///") for m in _mr)
      and sorted(m.get("src") for m in _mr) == sorted(pathlib.Path(p).resolve().as_uri() for p in (S1, S2, VX))
      and all(a.get("uid") and a.get("id") and a.get("start") == "0s" for a in _assets)
      and [a.get("hasVideo") for a in _assets].count("1") == 2 and [a.get("hasAudio") for a in _assets].count("1") == 2,
      [(a.attrib, m.attrib if m is not None else None) for a, m in zip(_assets, _mr)])
_refs = [e.get(k) for e in _root.iter() for k in ("ref", "format") if e.get(k) is not None]
check("d37_fcpxml_toute_reference_ref_format_est_resolue",
      # 4 references : le format de la sequence + deux plans + la voix ; r1..r4 declares
      sorted(_refs) == ["r1", "r2", "r3", "r4"] and all(r in _ids for r in _refs) and len(_ids) == 4, (_refs, _ids))
_TIME = re.compile(r"^\d+/30s$|^0s$")
_tv = [(e.tag, k, e.get(k)) for e in _root.iter() for k in ("offset", "start", "duration", "time", "value", "tcStart")
       if e.get(k) is not None]
check("d37_fcpxml_toute_duree_en_n_30s_ou_0s",
      len(_tv) >= 15 and all(_TIME.match(v) for _t, _k, v in _tv),
      [t for t in _tv if not _TIME.match(t[2])])
_seq = _root.find("library/event/project/sequence")
_spine = _seq.find("spine") if _seq is not None else None
_sp = list(_spine) if _spine is not None else []
_sp_clips = [e for e in _sp if e.tag == "asset-clip"]
check("d37_fcpxml_sequence_75_images_spine_plan1_puis_plan2",
      _seq is not None and _seq.get("duration") == "75/30s" and _seq.get("format") in _ids
      and _root.find("library/event/project").get("name") == "Essai export"
      and [(e.get("name"), e.get("offset"), e.get("start"), e.get("duration")) for e in _sp_clips]
      == [("plan1", "0s", "30/30s", "45/30s"), ("plan2", "45/30s", "0s", "30/30s")]
      and _sp_clips[0].get("srcEnable") == "video",
      [(e.tag, e.attrib) for e in _sp])
_tm = _sp_clips[1].find("timeMap") if len(_sp_clips) > 1 else None
_tp = [(p.get("time"), p.get("value")) for p in (_tm.findall("timept") if _tm is not None else [])]
check("d37_fcpxml_vitesse_x2_par_timeMap_0_0_puis_45_90",
      _tp == [("0s", "0s"), ("45/30s", "90/30s")]
      # temoin : plan1 (vitesse 1) n'a PAS de timeMap
      and _sp_clips[0].find("timeMap") is None, _tp)
_anc = _sp_clips[0].findall("asset-clip") if _sp_clips else []
check("d37_fcpxml_voix_ancree_sous_plan1_lane_moins_1_offset_local_45",
      len(_anc) == 1 and _anc[0].get("lane") == "-1" and _anc[0].get("offset") == "45/30s"
      and _anc[0].get("start") == "6/30s" and _anc[0].get("duration") == "45/30s"
      and _anc[0].get("audioRole") == "dialogue" and _anc[0].get("srcEnable") is None
      and (_sp_clips[1].findall("asset-clip") == []), [a.attrib for a in _anc])
check("d37_fcpxml_titre_saute_dit_en_commentaire",
      "<!-- SKIPPED: title Titre -->" in _fx and _fx.count("SKIPPED:") == 1, _fx[-400:])
_fx2 = X("to_fcpxml")(_r2, RES(), fps=30, size=(1920, 1080), meta=META(_r2))
_fx2 = _fx2 if isinstance(_fx2, str) else ""
try:
    _root2 = ET.fromstring(_fx2.encode("utf-8"))
except Exception:
    _root2 = ET.Element("illisible")
_spn2 = _root2.find("library/event/project/sequence/spine")
_sp2 = list(_spn2) if _spn2 is not None else []
check("d37_fcpxml_trou_rendu_par_un_gap_et_transitions_dites_non_exportees",
      [(e.tag, e.get("offset"), e.get("duration")) for e in _sp2]
      == [("asset-clip", "0s", "30/30s"), ("gap", "30/30s", "30/30s"),
          ("asset-clip", "60/30s", "30/30s"), ("asset-clip", "90/30s", "30/30s")]
      and "TRANSITION: dissolve 0.5 s (non exportée en FCPXML)" in _fx2
      and "TRANSITION: slideleft 0.4 s (non exportée en FCPXML)" in _fx2
      and "SKIPPED: source introuvable D" in _fx2,
      [(e.tag, e.attrib) for e in _sp2])

# ── la route
_espion = {"n": 0, "rend": None}
_ls0 = A("_load_saved", None)
def _faux_load():
    _espion["n"] += 1
    return _espion["rend"]
MS._load_saved = _faux_load


def ROUTE(fmt):
    f = A("montage_export", None)
    if f is None:
        return ("ABSENT", None, None)
    try:
        r = asyncio.run(f(format=fmt))
        return (r.status_code, r.body, dict(r.headers))
    except Exception as e:
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)), None)


_espion["rend"] = REC()
_e_st, _e_body, _e_h = ROUTE("edl")
_e_txt = _e_body.decode("utf-8") if isinstance(_e_body, bytes) else ""
check("d37_route_edl_200_piece_jointe_Essai_export_edl_et_corps_du_service",
      _e_st == 200 and (_e_h or {}).get("content-disposition") == 'attachment; filename="Essai_export.edl"'
      and _e_txt.startswith("TITLE: Essai export\r\n") and "* SOURCE FILE: " + str(pathlib.Path(S1)) in _e_txt
      and "003  AX       A     C        00:00:00:06 00:00:01:21 00:00:00:15 00:00:02:00" in _e_txt
      and _espion["n"] == 1, (_e_st, _e_h, _e_txt[:200], _espion))
_f_st, _f_body, _f_h = ROUTE("FCPXML")
_f_txt = _f_body.decode("utf-8") if isinstance(_f_body, bytes) else ""
try:
    _froot = ET.fromstring(_f_body) if isinstance(_f_body, bytes) else ET.Element("x")
except Exception:
    _froot = ET.Element("x")
_fasset = {pathlib.Path(a.find("media-rep").get("src")).name if a.find("media-rep") is not None else "?": a
           for a in _froot.iter("asset")}
check("d37_route_fcpxml_200_piece_jointe_xml_parsable_duree_sondee",
      _f_st == 200 and (_f_h or {}).get("content-disposition") == 'attachment; filename="Essai_export.fcpxml"'
      and "xml" in ((_f_h or {}).get("content-type") or "") and _froot.tag == "fcpxml"
      and len(_fasset) == 3 and _espion["n"] == 2
      # la duree sondee (3 s = 90/30s) si ffmpeg a genere les sources ; sinon le repli (consomme)
      and (_FB is None or (_fasset.get("plan2.mp4") is not None and _fasset["plan2.mp4"].get("duration") == "90/30s"
                           and _fasset["plan2.mp4"].get("hasAudio") is None
                           and _fasset["plan1.mp4"].get("hasAudio") == "1")),
      (_f_st, _f_h, {k: v.attrib for k, v in _fasset.items()}))
_espion["rend"] = None
_n_st, _n_det, _ = ROUTE("edl")
_espion["rend"] = {"name": "x", "clips": []}
_v_st, _v_det, _ = ROUTE("edl")
_espion["rend"] = REC()
_n0 = _espion["n"]
_u_st, _u_det, _ = ROUTE("xml")
check("d37_route_400_sans_timeline_timeline_vide_et_format_inconnu_avant_toute_lecture",
      _n_st == 400 and _v_st == 400 and _u_st == 400 and "timeline" in str(_n_det).lower()
      and "format" in str(_u_det).lower() and _espion["n"] == _n0
      # temoin : les deux premiers ont bien lu la sauvegarde
      and _n0 == 4, (_n_st, _n_det, _v_st, _v_det, _u_st, _u_det, _espion))
MS._load_saved = _ls0

print(f"\n=== {ok} passed, {fail} failed ===")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
