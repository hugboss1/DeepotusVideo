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
REVUE du 24/09/2026 : `FROM/TO CLIP NAME` = nom du FICHIER, libelle dans
`* CLIP LABEL:` ; poignee insuffisante dite (`* HANDLES:`) ; fondu borne
comme le rendu ; arret a 999 evenements ; commentaires XML surs (`x--y-`) ;
chevauchement V1 en FCPXML ; nom hostile dans Content-Disposition.
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
    "* FROM CLIP NAME: plan1.mp4",
    "* CLIP LABEL: plan1",
    "* SOURCE FILE: " + S1,
    "002  AX       V     C        00:00:02:15 00:00:02:15 00:00:01:15 00:00:01:15",
    "002  AX       V     D    012 00:00:00:00 00:00:02:00 00:00:01:15 00:00:02:15",
    "M2   AX       060.0                00:00:00:00",
    "* FROM CLIP NAME: plan1.mp4",
    "* TO CLIP NAME: plan2.mp4",
    "* CLIP LABEL: plan2",
    "* SPEED: 2",
    "* SOURCE FILE: " + S2,
    "003  AX       A     C        00:00:00:06 00:00:01:21 00:00:00:15 00:00:02:00",
    "* FROM CLIP NAME: voix.wav",
    "* CLIP LABEL: voix",
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
      and "* TO CLIP NAME: plan2.mp4" in _l2 and "* CLIP LABEL: B" in _l2
      # temoin : partir du noir ne demande AUCUNE poignee
      and not any(l.startswith("* HANDLES:") for l in _l2), _l2)
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

# ── revue du 24/09/2026 : poignees, borne du fondu, 999 evenements, commentaires XML surs, chevauchement
def _res_d(d1):
    k = X("src_key")
    r = RES()
    r[k({"file_path": S1})] = dict(r[k({"file_path": S1})], dur=d1)
    return r
# A : S1 srcIn 2,0 de 0 a 0,9 s -> src 60..87 ; S1 dure 3 s = 90 images -> 3 images de poignee.
# B : 0,9 -> 1,2 s (9 images), fondu 0,4 demande -> borne a min(0,4 ; 0,3-0,1 ; 0,9-0,1) = 0,2 s = 6 images > 3.
_r3 = {"name": "h", "tracks": [{"id": "v1", "kind": "video"}], "clips": [
    {"tr": "v1", "id": "a", "label": "A", "src": {"file_path": S1}, "srcIn": 2.0, "start": 0, "end": 0.9},
    {"tr": "v1", "id": "b", "label": "B", "src": {"file_path": S2}, "srcIn": 0, "start": 0.9, "end": 1.2,
     "transition": "fade", "transition_s": 0.4}]}
_e3 = X("to_edl")(_r3, _res_d(3.0), fps=30, meta=META(_r3)); _e3 = _e3 if isinstance(_e3, str) else ""
_l3 = [l for l in _e3.splitlines() if l.strip()]
_e3b = X("to_edl")(_r3, _res_d(None), fps=30, meta=META(_r3)); _e3b = _e3b if isinstance(_e3b, str) else ""
_e3c = X("to_edl")(_r3, _res_d(4.0), fps=30, meta=META(_r3)); _e3c = _e3c if isinstance(_e3c, str) else ""
check("d37_revue_fondu_borne_comme_le_rendu_6_images_et_poignee_insuffisante_dite_3_images",
      "002  AX       V     C        00:00:02:27 00:00:02:27 00:00:00:27 00:00:00:27" in _l3
      and "002  AX       V     D    006 00:00:00:00 00:00:00:09 00:00:00:27 00:00:01:06" in _l3
      and "* HANDLES: insuffisantes (3 images)" in _l3
      and _l3.index("* HANDLES: insuffisantes (3 images)") > _l3.index("* CLIP LABEL: B")
      # temoins : duree inconnue -> rien ; source de 4 s (33 images de poignee) -> rien, le fondu est la
      and "D    006" in _e3b and "HANDLES" not in _e3b and "D    006" in _e3c and "HANDLES" not in _e3c, _l3)
_r4 = {"name": "n", "tracks": [{"id": "v1", "kind": "video"}], "clips": [
    {"tr": "v1", "id": "c%d" % i, "label": "c%d" % i, "src": {"file_path": S1}, "srcIn": 0,
     "start": i / 10, "end": (i + 1) / 10} for i in range(1001)]}
_e4 = X("to_edl")(_r4, RES(), fps=30, meta=META(_r4)); _e4 = _e4 if isinstance(_e4, str) else ""
_l4 = [l for l in _e4.splitlines() if l.strip()]
check("d37_revue_plus_de_999_evenements_arret_et_TRUNCATED",
      sum(1 for l in _l4 if re.match(r"^\d{3}  AX", l)) == 999 and any(l.startswith("999  AX") for l in _l4)
      and not any(l.startswith("1000") for l in _l4)
      and _l4[-1] == "* TRUNCATED: plus de 999 événements — la suite n'est pas exportée", _l4[-3:])
_r5 = {"name": "c", "tracks": [{"id": "v1", "kind": "video"}, {"id": "t1", "kind": "title"}], "clips": [
    {"tr": "v1", "id": "a", "label": "A", "src": {"file_path": S1}, "srcIn": 0, "start": 0, "end": 1},
    {"tr": "v1", "id": "b", "label": "B", "src": {"file_path": S2}, "srcIn": 1.0, "start": 0.8, "end": 2,
     "transition": "wipe--x-", "transition_s": 0.4},
    {"tr": "t1", "id": "t", "label": "x--y-", "start": 0, "end": 1}]}
_f5 = X("to_fcpxml")(_r5, RES(), fps=30, size=(1080, 1920), meta=META(_r5)); _f5 = _f5 if isinstance(_f5, str) else ""
try:
    _root5 = ET.fromstring(_f5.encode("utf-8"))
except Exception as _e:
    print("  (FCPXML _r5 illisible : %s)" % _e)
    _root5 = ET.Element("illisible")
check("d37_revue_libelle_x__y_tiret_final_le_FCPXML_reste_lisible_commentaires_neutralises",
      _root5.tag == "fcpxml" and "<!-- SKIPPED: title x- -y- -->" in _f5
      and "<!-- TRANSITION: wipe- -x- 0.4 s (non exportée en FCPXML) -->" in _f5
      and _f5.count("<!--") == 2 and all("--" not in c[4:-3] for c in re.findall(r"<!--.*?-->", _f5)), _f5[-700:])
_spn5 = _root5.find("library/event/project/sequence/spine")
_sp5 = [(e.get("name"), e.get("offset"), e.get("start"), e.get("duration"))
        for e in (list(_spn5) if _spn5 is not None else []) if e.tag == "asset-clip"]
# B commence a 0,8 s (24) mais A finit a 30 : B part a 30 et sa source AVANCE de 6 images (srcIn 30 + 6 = 36)
check("d37_revue_chevauchement_V1_start_avance_avec_le_debut_36_30s",
      _sp5 == [("A", "0s", "0s", "30/30s"), ("B", "30/30s", "36/30s", "30/30s")], _sp5)

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
_fasset = {pathlib.Path(a.find("media-rep").get("src") or "").name if a.find("media-rep") is not None else "?": a
           for a in _froot.iter("asset")}
if _FB is None:
    print("  (ffmpeg absent : la duree sondee et hasAudio de la route FCPXML ne sont PAS verifies)")
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
_espion["rend"] = dict(REC(), name='a"b\r\nc/../d')
_h_st, _h_body, _h_h = ROUTE("edl")
_h_cd = (_h_h or {}).get("content-disposition") or ""
check("d37_revue_nom_hostile_guillemet_crlf_chemin_neutralise_dans_Content_Disposition",
      _h_st == 200 and _h_cd == 'attachment; filename="a_b_c_.._d.edl"'
      and _h_cd.count('"') == 2 and "\r" not in _h_cd and "\n" not in _h_cd and "/" not in _h_cd, (_h_st, _h_cd))
# revue du 24/09/2026 : la ROUTE sonde la duree des sources aussi pour l'EDL -> la poignee
# insuffisante sort dans un export REEL. plan1.mp4 dure 3 s (90 images) : A lu de 60 a 87 laisse
# 3 images ; le fondu de B est borne a 6 images -> « insuffisantes (3 images) ». Temoin : A lu de
# 0 a 27 laisse 63 images -> le meme fondu D 006, aucune mention.
def _r_h(src_in_a):
    return {"name": "poignees", "ratio": "9:16", "tracks": [{"id": "v1", "kind": "video"}], "clips": [
        {"tr": "v1", "id": "a", "label": "A", "src": {"file_path": S1}, "srcIn": src_in_a, "start": 0, "end": 0.9},
        {"tr": "v1", "id": "b", "label": "B", "src": {"file_path": S2}, "srcIn": 0, "start": 0.9, "end": 1.2,
         "transition": "fade", "transition_s": 0.4}]}
if _FB is None:
    print("  (ffmpeg absent : la poignee sondee par la route EDL n'est PAS verifiee)")
    check("d37_revue_route_edl_poignee_sondee_SKIP_sans_ffmpeg", True)
else:
    _espion["rend"] = _r_h(2.0)
    _p_st, _p_body, _ = ROUTE("edl")
    _p_txt = _p_body.decode("utf-8") if isinstance(_p_body, bytes) else ""
    _espion["rend"] = _r_h(0.0)
    _q_st, _q_body, _ = ROUTE("edl")
    _q_txt = _q_body.decode("utf-8") if isinstance(_q_body, bytes) else ""
    check("d37_revue_route_edl_sonde_la_duree_poignee_insuffisante_dite_temoin_sans_mention",
          _p_st == 200 and "D    006" in _p_txt and "* HANDLES: insuffisantes (3 images)\r\n" in _p_txt
          and _q_st == 200 and "D    006" in _q_txt and "HANDLES" not in _q_txt,
          (_p_st, _p_txt[-400:], _q_st))
MS._load_saved = _ls0

# ══ [2] D-42 DECOUPER AUX CHANGEMENTS DE PLAN ═══════════════════════════════
# Service PUR `app.services.scenes` : `parse(texte)`, `detect(path, src_in,
# dur, threshold=10.0)`, `timeout_de(dur)` ; route `POST /api/montage/scenes`.
# CE QUE ffmpeg 8.1.1 IMPRIME REELLEMENT (mesure du 24/09/2026, scdet +
# metadata=mode=print:key=lavfi.scd.time:file=-) : UNE paire de lignes par
# image COUPEE et rien d'autre —
#   frame:60   pts:30720   pts_time:2
#   lavfi.scd.time=2
# (sans `key=`, chaque image sort avec lavfi.scd.mafd / lavfi.scd.score, et
# lavfi.scd.time n'apparait que sur la coupe). Source de test : testsrc2 2 s
# puis testsrc 2 s concatenes (coupe a 2,0 s, score 31,05) ; une source grise
# uniforme de 3 s (score 0 partout).
print("\n[2] D-42 decouper aux changements de plan (scdet)")
try:
    from app.services import scenes as SC                  # noqa: E402
except Exception as _e:                                    # faute n°6 : rougir, pas mourir
    print("  (scenes introuvable : %s)" % _e)
    SC = None


def Y(nom):
    f = getattr(SC, nom, None) if SC is not None else None
    if f is None:
        return lambda *a, **k: "ABSENT: %s" % nom
    def g(*a, **k):
        try:
            return f(*a, **k)
        except Exception as e:
            return "%s: %s" % (type(e).__name__, e)
    return g


CC = str(pathlib.Path(TMP) / "deux_plans.mp4")
UNI = str(pathlib.Path(TMP) / "uniforme.mp4")
if _FB is not None:
    subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=64x64:r=30:d=2",
                    "-f", "lavfi", "-i", "testsrc=s=64x64:r=30:d=2", "-filter_complex",
                    "[0][1]concat=n=2:v=1:a=0", "-c:v", "libx264", "-pix_fmt", "yuv420p", CC],
                   check=False, capture_output=True, timeout=60)
    subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=64x64:r=30:d=3",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", UNI], check=False, capture_output=True, timeout=60)
_gen_ok = os.path.isfile(CC) and os.path.getsize(CC) > 1000 and os.path.isfile(UNI) and os.path.getsize(UNI) > 100
check("d42_sources_de_test_generees_deux_plans_et_uniforme", _gen_ok, (_FB, os.path.isfile(CC), os.path.isfile(UNI)))
check("d42_le_service_scenes_existe_avec_parse_detect_timeout_de",
      SC is not None and all(callable(getattr(SC, n, None)) for n in ("parse", "detect", "timeout_de")), "SC=%r" % (SC,))

# parse : la sortie MESUREE, telle quelle (espaces compris) ; tri, dedoublonnage a 1/30 s, plafond 200
_OUT_MESURE = "frame:60   pts:30720   pts_time:2\nlavfi.scd.time=2\n"
_OUT_DEUX = ("frame:45   pts:23040   pts_time:1.5\r\nlavfi.scd.time=1.5\r\n"
             "frame:22   pts:11264   pts_time:0.733333\r\nlavfi.scd.time=0.733333\r\n"
             "frame:23   pts:11776   pts_time:0.766667\r\nlavfi.scd.time=0.766667\r\n")
_OUT_BAVARD = ("frame:0    pts:0       pts_time:0\nlavfi.scd.mafd=0.000\nlavfi.scd.score=0.000\n"
               "frame:45   pts:23040   pts_time:1.5\nlavfi.scd.mafd=32.220\nlavfi.scd.score=31.050\nlavfi.scd.time=1.5\n"
               "frame:46   pts:23552   pts_time:1.533333\nlavfi.scd.mafd=0.126\nlavfi.scd.score=0.126\n")
_OUT_300 = "".join("frame:%d pts:0 pts_time:%s\nlavfi.scd.time=%s\n" % (i, i * 0.5, i * 0.5) for i in range(300))
check("d42_parse_la_sortie_mesuree_rend_2",
      Y("parse")(_OUT_MESURE) == [2.0], Y("parse")(_OUT_MESURE))
check("d42_parse_trie_dedoublonne_a_une_image_crlf_tolere",
      # 0.733333 et 0.766667 sont a 1/30 s l'un de l'autre : UNE coupe (la premiere)
      Y("parse")(_OUT_DEUX) == [0.733, 1.5], Y("parse")(_OUT_DEUX))
check("d42_parse_la_sortie_bavarde_sans_key_ne_prend_que_lavfi_scd_time",
      Y("parse")(_OUT_BAVARD) == [1.5]
      # temoin : la sortie vide rend une liste vide, pas une erreur
      and Y("parse")("") == [], (Y("parse")(_OUT_BAVARD), Y("parse")("")))
_p300 = Y("parse")(_OUT_300)
check("d42_parse_plafonne_a_200_coupes_et_ignore_t_nul",
      isinstance(_p300, list) and len(_p300) == 200 and _p300[0] == 0.5 and _p300[-1] == 100.0,
      (type(_p300), len(_p300) if isinstance(_p300, list) else _p300))
check("d42_timeout_proportionnel_plancher_120_deux_fois_la_duree_plus_60",
      [Y("timeout_de")(v) for v in (0, 3, 30, 3600, "x")] == [120, 120, 120, 7260, 120],
      [Y("timeout_de")(v) for v in (0, 3, 30, 3600, "x")])

# detect : ESPION sur le lanceur ffmpeg du service (compte les appels, garde la commande)
_sp = {"n": 0, "cmd": None, "timeout": None}
_lanceur0 = getattr(SC, "_ffmpeg", None) if SC is not None else None
if _lanceur0 is not None:
    def _espion_ff(cmd, timeout):
        _sp["n"] += 1; _sp["cmd"] = list(cmd); _sp["timeout"] = timeout
        return _lanceur0(cmd, timeout)
    SC._ffmpeg = _espion_ff
_d0 = Y("detect")(CC, 0.0, 4.0)
_n_apres_1 = _sp["n"]
check("d42_detect_deux_plans_coupe_a_2_a_une_image_pres",
      isinstance(_d0, list) and len(_d0) == 1 and abs(_d0[0] - 2.0) <= 1 / 30 + 1e-9 and _n_apres_1 == 1,
      (_d0, _sp["n"]))
_cmd = _sp["cmd"] or []
_vf = _cmd[_cmd.index("-vf") + 1] if "-vf" in _cmd else ""
check("d42_detect_commande_ss_t_avant_i_scdet_seuil_et_impression_par_cle",
      _cmd[:1] == ["ffmpeg"] and "-ss" in _cmd and "-t" in _cmd and "-i" in _cmd
      and _cmd.index("-ss") < _cmd.index("-i") and _cmd.index("-t") < _cmd.index("-i")
      and _vf == "setpts=PTS-STARTPTS,scdet=threshold=10,metadata=mode=print:key=lavfi.scd.time:file=-"
      and "-an" in _cmd and _sp["timeout"] == 120, (_cmd, _sp["timeout"]))
_d05 = Y("detect")(CC, 0.5, 3.0)
check("d42_detect_srcIn_0_5_rend_une_coupe_relative_a_1_5",
      isinstance(_d05, list) and len(_d05) == 1 and abs(_d05[0] - 1.5) <= 1 / 30 + 1e-9 and _sp["n"] == 2,
      (_d05, _sp["n"]))
_dcourt = Y("detect")(CC, 0.0, 1.5)
check("d42_detect_une_fenetre_avant_la_coupe_rend_vide_apres_avoir_lance_ffmpeg",
      _dcourt == [] and _sp["n"] == 3, (_dcourt, _sp["n"]))
_duni = Y("detect")(UNI, 0.0, 3.0)
check("d42_detect_source_uniforme_rend_vide_apres_avoir_lance_ffmpeg",
      _duni == [] and _sp["n"] == 4, (_duni, _sp["n"]))
_d40 = Y("detect")(CC, 0.0, 4.0, threshold=40)
check("d42_detect_seuil_40_au_dessus_du_score_31_rend_vide_et_c_est_une_autre_cle_de_cache",
      _d40 == [] and _sp["n"] == 5, (_d40, _sp["n"]))
# le cache : meme (chemin, mtime, srcIn, dur, T) -> ffmpeg n'est PAS relance, meme reponse
_d0b = Y("detect")(CC, 0.0, 4.0)
_d05b = Y("detect")(CC, 0.5, 3.0)
_cache_dir = pathlib.Path(TMP) / "outputs" / "montage_cache"
_caches = sorted(p.name for p in _cache_dir.glob("*_scenes.json")) if _cache_dir.is_dir() else []
check("d42_cache_deuxieme_appel_sans_ffmpeg_meme_reponse_fichiers_json_dans_montage_cache",
      _d0b == _d0 and _d05b == _d05 and _sp["n"] == 5 and len(_caches) == 5
      and not any(".tmp" in n for n in _caches), (_d0b, _d05b, _sp["n"], _caches))
# une source MODIFIEE (mtime) invalide la cle
try:
    _st = os.stat(CC); os.utime(CC, ns=(_st.st_atime_ns, _st.st_mtime_ns + 10_000_000_000))
except Exception as _e:
    print("  (utime : %s)" % _e)
_d0c = Y("detect")(CC, 0.0, 4.0)
check("d42_cache_une_source_modifiee_relance_ffmpeg", _d0c == _d0 and _sp["n"] == 6, (_d0c, _sp["n"]))
_dabs = Y("detect")(str(pathlib.Path(TMP) / "absent.mp4"), 0.0, 3.0)
_n_abs = _sp["n"]
_dwav = Y("detect")(VX, 0.0, 2.0)
check("d42_detect_source_absente_leve_MediaError_nommee_sans_ffmpeg",
      isinstance(_dabs, str) and _dabs.startswith("MediaError") and "absent.mp4" in _dabs and _n_abs == 6,
      (_dabs, _n_abs))
check("d42_detect_ffmpeg_en_echec_leve_MediaError_et_rien_n_est_mis_en_cache",
      # un .wav n'a pas de flux video : ffmpeg sort en erreur (rc != 0) -> MediaError ; temoin : ffmpeg a tourne
      isinstance(_dwav, str) and _dwav.startswith("MediaError") and _sp["n"] == 7
      and len(list(_cache_dir.glob("*_scenes.json"))) == 6, (_dwav, _sp["n"]))
if _lanceur0 is not None:
    SC._ffmpeg = _lanceur0


# la route : une vraie Request starlette (client 127.0.0.1), sans serveur
def REQ(body):
    from starlette.requests import Request as _R
    import json as _j
    raw = _j.dumps(body).encode("utf-8")
    async def rcv():
        return {"type": "http.request", "body": raw, "more_body": False}
    return _R({"type": "http", "method": "POST", "path": "/api/montage/scenes", "query_string": b"",
               "headers": [(b"content-type", b"application/json")], "client": ("127.0.0.1", 5000)}, rcv)


def SCN(body):
    f = A("montage_scenes", None)
    if f is None:
        return ("ABSENT", None)
    try:
        return (200, asyncio.run(f(REQ(body))))
    except Exception as e:
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)))


_sp2 = {"n": 0, "args": None}
_det0 = getattr(SC, "detect", None) if SC is not None else None
if _det0 is not None:
    def _espion_det(*a, **k):
        _sp2["n"] += 1; _sp2["args"] = (a, k)
        return _det0(*a, **k)
    SC.detect = _espion_det
_r_ok = SCN({"src": {"file_path": CC}, "srcIn": 0.5, "dur": 3.0})
check("d42_route_200_ok_times_relatifs_au_srcIn",
      _r_ok[0] == 200 and isinstance(_r_ok[1], dict) and _r_ok[1].get("ok") is True
      and isinstance(_r_ok[1].get("times"), list) and len(_r_ok[1]["times"]) == 1
      and abs(_r_ok[1]["times"][0] - 1.5) <= 1 / 30 + 1e-9 and _sp2["n"] == 1
      and _sp2["args"] is not None and _sp2["args"][1].get("threshold") == 10.0, (_r_ok, _sp2))
_r_t = SCN({"src": {"file_path": CC}, "srcIn": 0, "dur": 4, "threshold": 40})
check("d42_route_seuil_transmis",
      _r_t[0] == 200 and isinstance(_r_t[1], dict) and _r_t[1].get("times") == [] and _sp2["n"] == 2
      and _sp2["args"][1].get("threshold") == 40.0, (_r_t, _sp2))
_r_404 = SCN({"src": {"file_path": str(pathlib.Path(TMP) / "absent.mp4")}, "srcIn": 0, "dur": 2})
_r_415 = SCN({"src": {"file_path": VX}, "srcIn": 0, "dur": 2})
check("d42_route_404_source_inconnue_415_source_non_video_sans_analyse",
      _r_404[0] == 404 and _r_415[0] == 415 and _sp2["n"] == 2, (_r_404, _r_415, _sp2["n"]))
_bad = [SCN({"src": {"file_path": CC}, "srcIn": 0}),
        SCN({"src": {"file_path": CC}, "srcIn": 0, "dur": 0}),
        SCN({"src": {"file_path": CC}, "srcIn": -1, "dur": 2}),
        SCN({"src": {"file_path": CC}, "srcIn": "abc", "dur": 2}),
        SCN({"src": {"file_path": CC}, "srcIn": 0, "dur": "nan"}),
        SCN({"src": {"file_path": CC}, "srcIn": 0, "dur": 2, "threshold": 0}),
        SCN({"src": {"file_path": CC}, "srcIn": 0, "dur": 2, "threshold": 101}),
        SCN({"src": {"file_path": CC}, "srcIn": 0, "dur": 100000})]
check("d42_route_400_parametres_illisibles_ou_hors_bornes_avant_toute_analyse",
      [b[0] for b in _bad] == [400] * 8 and _sp2["n"] == 2
      # temoin : la meme requete aux bornes permises passe (seuil 100, dur 4 h)
      and SCN({"src": {"file_path": CC}, "srcIn": 0, "dur": 14400, "threshold": 100})[0] == 200 and _sp2["n"] == 3,
      ([b for b in _bad], _sp2["n"]))
if _det0 is not None:
    SC.detect = _det0

# ══ [3] D-40 RECADRAGE PAR ENERGIE DE MOUVEMENT (backend) ═══════════════════
# Service PUR `app.services.reframe` : `barycentre(a, b, noise)`, `suivre(images,
# fps, noise)`, `motion_track(path, src_in, dur, fps=4, width=96, noise=12)`,
# `simplifier(pairs, tol)` ; `MS._reframe_of(c)`, `MS._reframe_crop(rf, w, h)`,
# chaine cover V1 de `_build_montage_command`, route `POST /api/montage/reframe`.
# MESURE DE L'ETAPE 1 (24/09/2026, ffmpeg 8.1.1) : un `x` ANIME de crop passe
# (le `w` anime echoue −22, temoin D-13) et `t` y vaut le temps LOCAL du flux
# lu (-ss avant -i ; voie D-16 trim+setpts idem) ; le crop precede
# setpts=PTS/speed : a xN, `t` est le temps de SOURCE depuis srcIn — l'unite
# des points (voir le docstring de reframe.py).
# Source de test : fond noir 480x270 a 30 i/s, carre blanc de 60 px (y 105..165)
# dont le centre vaut 70 + 95 T (T absolu) ; source statique : le carre fixe.
print("\n[3] D-40 recadrage par energie de mouvement (backend)")
try:
    from app.services import reframe as RF                 # noqa: E402
except Exception as _e:                                    # faute n°6 : rougir, pas mourir
    print("  (reframe introuvable : %s)" % _e)
    RF = None


def Z(nom):
    f = getattr(RF, nom, None) if RF is not None else None
    if f is None:
        return lambda *a, **k: "ABSENT: %s" % nom
    def g(*a, **k):
        try:
            return f(*a, **k)
        except Exception as e:
            return "%s: %s" % (type(e).__name__, e)
    return g


MOV = str(pathlib.Path(TMP) / "carre_mobile.mp4")
FIX = str(pathlib.Path(TMP) / "carre_fixe.mp4")
if _FB is not None:
    for _dst, _xe in ((MOV, "40+t*95"), (FIX, "210")):
        subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=480x270:r=30:d=4",
                        "-f", "lavfi", "-i", "color=c=white:s=60x60:r=30:d=4", "-filter_complex",
                        "[0][1]overlay=x='%s':y=105:shortest=1" % _xe, "-c:v", "libx264", "-pix_fmt", "yuv420p", _dst],
                       check=False, capture_output=True, timeout=60)
_gen3 = os.path.isfile(MOV) and os.path.getsize(MOV) > 1000 and os.path.isfile(FIX) and os.path.getsize(FIX) > 500
check("d40_sources_de_test_generees_carre_mobile_et_fixe", _gen3, (_FB, os.path.isfile(MOV), os.path.isfile(FIX)))
check("d40_le_service_reframe_existe",
      RF is not None and all(callable(getattr(RF, n, None))
                             for n in ("barycentre", "suivre", "motion_track", "simplifier")), "RF=%r" % (RF,))


def _vrai(t, src_in=0.0):
    return (70 + 95 * (t + src_in)) / 480


def _err_max(res, src_in=0.0, lo=0.5, hi=3.5):
    pts = [p for p in (res.get("points") or []) if lo <= p.get("t", -1) <= hi] if isinstance(res, dict) else []
    return (max(abs(p["x"] - _vrai(p["t"], src_in)) for p in pts) if pts else 9.0), len(pts)


# espion sur le lanceur ffmpeg du service
_sr = {"n": 0, "cmd": None, "timeout": None}
_rl0 = getattr(RF, "_ffmpeg", None) if RF is not None else None
if _rl0 is not None:
    def _espion_rf(cmd, timeout):
        _sr["n"] += 1; _sr["cmd"] = list(cmd); _sr["timeout"] = timeout
        return _rl0(cmd, timeout)
    RF._ffmpeg = _espion_rf
_t0 = Z("motion_track")(MOV, 0.0, 4.0)
_e0, _n0 = _err_max(_t0)
print("  (suivi mesure : erreur max %.4f de la largeur sur %d points de [0,5 ; 3,5])" % (_e0, _n0))
check("d40_tracker_carre_qui_traverse_mode_suivi_erreur_leq_8_pourcent_sur_0_5_3_5",
      isinstance(_t0, dict) and _t0.get("mode") == "suivi" and _n0 >= 8 and _e0 <= 0.08
      and _t0.get("fps") == 4 and _sr["n"] == 1, (_t0 if not isinstance(_t0, dict) else (_t0.get("mode"), _e0, _n0), _sr["n"]))
_cmd3 = _sr["cmd"] or []
_vf3 = _cmd3[_cmd3.index("-vf") + 1] if "-vf" in _cmd3 else ""
check("d40_tracker_commande_ss_t_avant_i_png_gris_4_ips_96_de_large_delai_proportionnel",
      _cmd3[:1] == ["ffmpeg"] and "-ss" in _cmd3 and "-i" in _cmd3 and _cmd3.index("-ss") < _cmd3.index("-i")
      and _cmd3.index("-t") < _cmd3.index("-i") and _vf3 == "setpts=PTS-STARTPTS,fps=4,scale=96:-2,format=gray"
      and _cmd3[-1].endswith("f_%05d.png") and _sr["timeout"] == 120, (_cmd3, _sr["timeout"]))
_pts0 = _t0.get("points") if isinstance(_t0, dict) else None
check("d40_tracker_points_t_croissants_dans_0_dur_x_dans_0_1_au_plus_240",
      isinstance(_pts0, list) and 8 <= len(_pts0) <= 240
      and all(0 <= p["t"] <= 4.0 and 0 <= p["x"] <= 1 for p in _pts0)
      and all(a["t"] < b["t"] for a, b in zip(_pts0, _pts0[1:])), _pts0)
_t1 = Z("motion_track")(MOV, 1.0, 2.0)
_e1, _n1 = _err_max(_t1, 1.0, 0.25, 1.75)
check("d40_tracker_srcIn_1_temps_relatifs_au_debut_lu",
      isinstance(_t1, dict) and _t1.get("mode") == "suivi" and _n1 >= 4 and _e1 <= 0.08
      # temoin : lus en temps ABSOLU, les memes points seraient faux de 95/480 ~ 0,2
      and _err_max(_t1, 0.0, 0.25, 1.75)[0] > 0.15 and _sr["n"] == 2, (_t1, _e1, _sr["n"]))
_tf = Z("motion_track")(FIX, 0.0, 4.0)
check("d40_tracker_source_statique_mode_centre_x_0_5_apres_avoir_lance_ffmpeg",
      isinstance(_tf, dict) and _tf.get("mode") == "centre" and _tf.get("x") == 0.5
      and _tf.get("points") == [] and _tf.get("motion") == 0 and _sr["n"] == 3, (_tf, _sr["n"]))
_t0b = Z("motion_track")(MOV, 0.0, 4.0)
_tfb = Z("motion_track")(FIX, 0.0, 4.0)
_caches3 = sorted(p.name for p in _cache_dir.glob("*_reframe.json")) if _cache_dir.is_dir() else []
check("d40_cache_deuxieme_appel_sans_ffmpeg_meme_reponse_json_dans_montage_cache",
      _t0b == _t0 and _tfb == _tf and _sr["n"] == 3 and len(_caches3) == 3
      and not any(".tmp" in n for n in _caches3), (_sr["n"], _caches3))
_t0f = Z("motion_track")(MOV, 0.0, 4.0, fps=2)
check("d40_cache_une_autre_cadence_est_une_autre_cle",
      isinstance(_t0f, dict) and _t0f.get("fps") == 2 and _sr["n"] == 4, (_t0f, _sr["n"]))
try:
    _st3 = os.stat(MOV); os.utime(MOV, ns=(_st3.st_atime_ns, _st3.st_mtime_ns + 10_000_000_000))
except Exception as _e:
    print("  (utime : %s)" % _e)
_t0c = Z("motion_track")(MOV, 0.0, 4.0)
check("d40_cache_une_source_modifiee_relance_ffmpeg", _t0c == _t0 and _sr["n"] == 5, (_sr["n"],))
_rabs = Z("motion_track")(str(pathlib.Path(TMP) / "absent.mp4"), 0.0, 3.0)
_nabs3 = _sr["n"]
_rwav = Z("motion_track")(VX, 0.0, 2.0)
check("d40_source_absente_MediaError_nommee_sans_ffmpeg",
      isinstance(_rabs, str) and _rabs.startswith("MediaError") and "absent.mp4" in _rabs and _nabs3 == 5,
      (_rabs, _nabs3))
check("d40_ffmpeg_en_echec_MediaError_et_rien_n_est_mis_en_cache",
      isinstance(_rwav, str) and _rwav.startswith("MediaError") and _sr["n"] == 6
      and len(list(_cache_dir.glob("*_reframe.json"))) == 5, (_rwav, _sr["n"]))
if _rl0 is not None:
    RF._ffmpeg = _rl0

# le coeur pur sur des images synthetiques (PIL seul)
try:
    from PIL import Image as _Im
    def _barre(x, w=96, h=10):
        im = _Im.new("L", (w, h), 0)
        for xx in range(max(0, x), min(w, x + 4)):
            for yy in range(h):
                im.putpixel((xx, yy), 255)
        return im
    _mob = [_barre(i % 90) for i in range(301)]
    _mob_trous = [_barre(10 + 3 * (i // 2)) for i in range(20)]   # une paire sur deux identique
    _plats = [_Im.new("L", (96, 10), 40) for _ in range(10)]
except Exception as _e:
    print("  (PIL : %s)" % _e)
    _mob = _mob_trous = _plats = []
_s300 = Z("suivre")(_mob, 4, 12)
check("d40_suivre_300_paires_en_mouvement_plafonne_a_240_points",
      isinstance(_s300, dict) and _s300.get("mode") == "suivi" and len(_s300.get("points") or []) == 240
      and _s300["points"][0]["t"] == 0.125 and _s300["points"][-1]["t"] == 74.875,
      (_s300.get("mode"), len(_s300.get("points") or [])) if isinstance(_s300, dict) else _s300)
_strous = Z("suivre")(_mob_trous, 4, 12)
_splat = Z("suivre")(_plats, 4, 12)
_sun = Z("suivre")(_plats[:1], 4, 12)
check("d40_suivre_plus_de_20_pourcent_de_paires_sans_mouvement_centre_temoin_suivi",
      isinstance(_strous, dict) and _strous.get("mode") == "centre" and 0.4 < _strous.get("motion", 0) < 0.6
      and isinstance(_splat, dict) and _splat.get("mode") == "centre" and _splat.get("motion") == 0
      and isinstance(_sun, dict) and _sun.get("mode") == "centre"
      # temoin : les memes barres SANS paire immobile suivent
      and isinstance(Z("suivre")(_mob[:20], 4, 12), dict) and Z("suivre")(_mob[:20], 4, 12).get("mode") == "suivi",
      (_strous, _splat, _sun))
_b = Z("barycentre")(_barre(20), _barre(24), 12) if _mob else None
check("d40_barycentre_milieu_des_deux_positions_et_None_sans_mouvement",
      isinstance(_b, float) and abs(_b * 96 - 24.0) < 0.6
      and Z("barycentre")(_barre(20), _barre(20), 12) is None, (_b,))
# EMA 0,5 : deux paires de barycentres bruts b0, b1 -> points b0 puis (b0 + b1) / 2, dates (i + 1/2) / fps
_tri = [_barre(10), _barre(14), _barre(60)] if _mob else []
_b0 = Z("barycentre")(_tri[0], _tri[1], 12) if _tri else None
_b1 = Z("barycentre")(_tri[1], _tri[2], 12) if _tri else None
_sema = Z("suivre")(_tri, 4, 12) if _tri else None
check("d40_ema_0_5_lisse_le_barycentre_et_date_au_milieu_de_la_paire",
      isinstance(_b0, float) and isinstance(_b1, float) and isinstance(_sema, dict)
      and [p["t"] for p in _sema.get("points", [])] == [0.125, 0.375]
      and [p["x"] for p in _sema.get("points", [])] == [round(_b0, 4), round(0.5 * _b1 + 0.5 * _b0, 4)]
      and abs(_b1 - _b0) > 0.2, (_b0, _b1, _sema))
_simp = Z("simplifier")([(0, 0.1), (1, 0.2), (2, 0.3), (3, 0.9), (4, 0.9)], 0.004)
check("d40_simplifier_garde_les_extremites_et_les_ruptures_retire_les_points_alignes",
      _simp == [(0, 0.1), (2, 0.3), (3, 0.9), (4, 0.9)]
      and Z("simplifier")([(0, 0.5)], 0.004) == [(0, 0.5)], _simp)

# _reframe_of : bornes, modes, warning
_rfo = A("_reframe_of", None)


class _J3:
    def __init__(self): self.msgs = []
    def warning(self, m, *a, **k): self.msgs.append(str(m))
    def __getattr__(self, k): return lambda *a, **k2: None


def RFO(c):
    """(resultat, warnings) de MS._reframe_of(c) sous journal capte."""
    if _rfo is None:
        return ("ABSENT", [])
    j, l0 = _J3(), MS.logger
    MS.logger = j
    try:
        return (_rfo(c), j.msgs)
    except Exception as e:
        return ("%s: %s" % (type(e).__name__, e), j.msgs)
    finally:
        MS.logger = l0


def CL(rf, **kw):
    d = {"tr": "v1", "label": "p", "start": 1.0, "end": 3.0}
    if rf is not ...:
        d["reframe"] = rf
    d.update(kw)
    return d


check("d40_reframe_of_absent_None_sans_warning_temoin_manuel_rend_un_dict",
      RFO(CL(...)) == (None, []) and RFO(CL({"mode": "manuel", "x": 0.3}))[0] == {"mode": "manuel", "x": 0.3},
      (RFO(CL(...)), RFO(CL({"mode": "manuel", "x": 0.3}))))
check("d40_reframe_of_centre_None_meme_avec_x_sans_warning",
      RFO(CL({"mode": "centre"})) == (None, []) and RFO(CL({"mode": "centre", "x": 0.2})) == (None, []),
      (RFO(CL({"mode": "centre"})), RFO(CL({"mode": "centre", "x": 0.2}))))
_inv = [RFO(CL(v)) for v in ("x", 3, {"mode": "zoom"}, {"x": 0.3}, {"mode": "manuel"},
                                {"mode": "manuel", "x": "abc"}, {"mode": "manuel", "x": float("nan")},
                                {"mode": "manuel", "x": True}, {"mode": "suivi"}, {"mode": "suivi", "points": []},
                                {"mode": "suivi", "points": [{"t": "a", "x": 0.2}, {"x": 0.3}, "z"]})]
check("d40_reframe_of_invalide_None_avec_warning",
      all(r[0] is None and len(r[1]) >= 1 and "reframe" in r[1][0] for r in _inv), _inv)
check("d40_reframe_of_manuel_x_borne_0_1",
      RFO(CL({"mode": "manuel", "x": 1.7}))[0] == {"mode": "manuel", "x": 1.0}
      and RFO(CL({"mode": "manuel", "x": -2}))[0] == {"mode": "manuel", "x": 0.0}
      and RFO(CL({"mode": "manuel", "x": "0.25"}))[0] == {"mode": "manuel", "x": 0.25},
      (RFO(CL({"mode": "manuel", "x": 1.7})), RFO(CL({"mode": "manuel", "x": -2}))))
_su = RFO(CL({"mode": "suivi", "points": [{"t": 1.5, "x": 0.8}, {"t": -1, "x": 0.1}, {"t": 9, "x": 2},
                                           {"t": 0.5, "x": "bad"}, {"t": 1.0, "x": 0.5}]}))
check("d40_reframe_of_suivi_trie_t_borne_0_duree_du_clip_x_borne_point_invalide_ignore_avec_warning",
      _su[0] == {"mode": "suivi", "points": [(0.0, 0.1), (1.0, 0.5), (1.5, 0.8), (2.0, 1.0)]}
      and len(_su[1]) == 1, _su)
_su2 = RFO(CL({"mode": "suivi", "points": [{"t": 3.5, "x": 0.4}, {"t": 9, "x": 0.6}]}, speed=2))
check("d40_reframe_of_suivi_a_vitesse_2_borne_t_a_la_duree_de_SOURCE_consommee",
      _su2[0] == {"mode": "suivi", "points": [(3.5, 0.4), (4.0, 0.6)]} and _su2[1] == [], _su2)
_su300 = RFO(CL({"mode": "suivi", "points": [{"t": i * 0.001 * 6, "x": 0.5} for i in range(300)]}, end=4.0))
check("d40_reframe_of_suivi_plafonne_a_240_points_avec_warning",
      isinstance(_su300[0], dict) and len(_su300[0]["points"]) == 240 and len(_su300[1]) == 1
      and "240" in _su300[1][0], (len(_su300[0]["points"]) if isinstance(_su300[0], dict) else _su300,))

# formes de commande : sans champ octet pour octet ; manuel x constant ; suivi expression
_crop_of = A("_reframe_crop", None)
V1R = str(pathlib.Path(TMP) / "v1r.mp4")
pathlib.Path(V1R).write_bytes(b"x")


def V1D(**kw):
    d = {"path": V1R, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}
    d.update(kw)
    return d


def CMD(v1s, v2=None, w=152, h=270):
    try:
        c, _ = MS._build_montage_command(v1s, v2 or [], [], None, w=w, h=h, fps=30, mix_db={},
                                         ducking=False, duration_master=False, preview=True,
                                         out=os.path.join(TMP, "r.mp4"))
        return " ".join(c)
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)


_OV = {"path": V1R, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 1.0, "end": 3.0,
       "opacity": None, "tf": None, "mp": None, "layer": 0}
_variantes = [dict(), dict(speed=2.0), dict(dz={"x0": 0, "y0": 0, "w0": 1, "x1": .2, "y1": .2, "w1": .6, "ease": "lin"}),
              dict(speed=0.5, dz={"x0": 0, "y0": 0, "w0": 1, "x1": .2, "y1": .2, "w1": .6, "ease": "doux"})]
_ref = [CMD([V1D(**v)], [dict(_OV)]) for v in _variantes]
_nul = [CMD([V1D(reframe=None, **v)], [dict(_OV)]) for v in _variantes]
check("d40_commande_sans_champ_octet_pour_octet_temoin_crop_cover_historique",
      _nul == _ref and all("crop=152:270,setsar=1" in r and "ABSENT" not in r and "crop=152:270:x=" not in r for r in _ref),
      [r[:200] for r in _ref])
_man = [CMD([V1D(reframe={"mode": "manuel", "x": 0.3}, **v)], [dict(_OV)]) for v in _variantes]
_CM = "crop=152:270:x='clip(iw*0.3-76,0,iw-152)':y=(ih-270)/2,setsar=1"
check("d40_commande_manuel_x_constant_seule_la_fenetre_du_crop_change_les_4_variantes_et_l_overlay_intacts",
      all(_CM in m and m.replace(_CM, "crop=152:270,setsar=1") == r for m, r in zip(_man, _ref))
      and all(m != r for m, r in zip(_man, _ref)), [m[:300] for m in _man])
_PTS = [(0.5, 0.2), (1.5, 0.6), (2.5, 0.8)]   # non alignes : la simplification les garde tous
_sui = CMD([V1D(reframe={"mode": "suivi", "points": _PTS})], [dict(_OV)])
_EX = MS._mp_lerp_expr(_PTS) if hasattr(MS, "_mp_lerp_expr") else "?"
_CS = "crop=152:270:x='clip(iw*(%s)-76,0,iw-152)':y=(ih-270)/2,setsar=1" % _EX
check("d40_commande_suivi_expression_interpolee_en_t_local_seule_la_fenetre_change",
      _CS in _sui and _sui.replace(_CS, "crop=152:270,setsar=1") == _ref[0] and "if(lt(t,0.5),0.2," in _sui,
      _sui[:400])
_sui1 = CMD([V1D(reframe={"mode": "suivi", "points": [(0.0, 0.7)]})])
check("d40_commande_suivi_un_seul_point_x_constant",
      "crop=152:270:x='clip(iw*(0.7)-76,0,iw-152)':y=(ih-270)/2,setsar=1" in _sui1, _sui1[:300])
_long = [(i * 0.25, 0.5 + 0.3 * ((-1) ** i) * (i % 7) / 7) for i in range(240)]
_lin = [(i * 0.25, 0.1 + 0.8 * i / 239) for i in range(240)]
_cl = CMD([V1D(end=60.0, src_dur=60.0, reframe={"mode": "suivi", "points": _long})])
_cli = CMD([V1D(end=60.0, src_dur=60.0, reframe={"mode": "suivi", "points": _lin})])
check("d40_commande_suivi_simplifie_une_droite_de_240_points_devient_2_points_temoin_zigzag_garde",
      _cli.count("if(lt(t,") == 2 and 100 < _cl.count("if(lt(t,") <= 240, (_cli.count("if(lt(t,"), _cl.count("if(lt(t,")))
_stab_ref = CMD([V1D(stab={"smooth": 15, "crop": "keep", "zoom": 0, "trf": V1R})])
_stab_man = CMD([V1D(stab={"smooth": 15, "crop": "keep", "zoom": 0, "trf": V1R}, reframe={"mode": "manuel", "x": 0.3})])
check("d40_commande_voie_stabilisee_trim_setpts_puis_crop_anime",
      "vidstabtransform=" in _stab_ref and _stab_man.replace(_CM, "crop=152:270,setsar=1") == _stab_ref
      and _CM in _stab_man and _stab_man.index("setpts=PTS-STARTPTS,scale=") < _stab_man.index(_CM), _stab_man[:400])

# rendu REEL 9:16 d'une source 16:9 : le carre reste dans le cadre (pixels mesures)
def _ligne(out, t, y=135, w=152):
    try:
        r = subprocess.run([_FB, "-loglevel", "error", "-ss", "%.3f" % t, "-i", out, "-frames:v", "1",
                            "-vf", "format=gray,crop=%d:1:0:%d" % (w, y), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                           check=False, capture_output=True, timeout=60)
        return list(r.stdout[:w]) if len(r.stdout) >= w else None
    except Exception:
        return None


def _rendu(rf, nom):
    out = os.path.join(TMP, nom)
    kw = {} if rf is ... else {"reframe": rf}
    try:
        c, _ = MS._build_montage_command([V1D(path=MOV, **kw)], [], [], None, w=152, h=270, fps=30,
                                         mix_db={}, ducking=False, duration_master=False, preview=True, out=out)
        c = [_FB] + list(c[1:])
        r = subprocess.run(c, check=False, capture_output=True, text=True, timeout=180)
        return r.returncode, (r.stderr or "")[-300:], out
    except Exception as e:
        return -1, "%s: %s" % (type(e).__name__, e), out


if _FB is None:
    check("d40_rendu_reel_SKIP_sans_ffmpeg", True)
else:
    _trk = _t0 if isinstance(_t0, dict) else {}
    _rf_s = MS._reframe_of({"start": 0, "end": 4, "reframe": _trk}) if _rfo is not None else None
    _rc_s, _er_s, _o_s = _rendu(_rf_s, "d40_suivi.mp4")
    _rc_c, _er_c, _o_c = _rendu(..., "d40_centre.mp4")
    _blanc_s = [sum(1 for v in (_ligne(_o_s, t) or []) if v > 128) for t in (0.8, 2.0, 3.2)]
    _blanc_c = [sum(1 for v in (_ligne(_o_c, t) or []) if v > 128) for t in (0.8, 2.0, 3.2)]
    print("  (rendu reel : colonnes blanches a y=135, suivi %s, centre %s)" % (_blanc_s, _blanc_c))
    check("d40_rendu_reel_9_16_suivi_le_carre_reste_dans_le_cadre_aux_trois_instants",
          _rc_s == 0 and isinstance(_rf_s, dict) and _rf_s.get("mode") == "suivi"
          and all(n >= 50 for n in _blanc_s), (_rc_s, _er_s, _blanc_s))
    check("d40_rendu_reel_temoin_centre_le_carre_sort_du_cadre_a_au_moins_un_instant",
          _rc_c == 0 and min(_blanc_c) < 20 and max(_blanc_c) >= 50, (_rc_c, _er_c, _blanc_c))

# la route : espion de motion_track
def RQR(body):
    from starlette.requests import Request as _R
    import json as _j
    raw = _j.dumps(body).encode("utf-8")
    async def rcv():
        return {"type": "http.request", "body": raw, "more_body": False}
    return _R({"type": "http", "method": "POST", "path": "/api/montage/reframe", "query_string": b"",
               "headers": [(b"content-type", b"application/json")], "client": ("127.0.0.1", 5000)}, rcv)


def RFR(body):
    f = A("montage_reframe", None)
    if f is None:
        return ("ABSENT", None)
    try:
        return (200, asyncio.run(f(RQR(body))))
    except Exception as e:
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)))


_sm = {"n": 0, "args": None}
_mt0 = getattr(RF, "motion_track", None) if RF is not None else None
if _mt0 is not None:
    def _espion_mt(*a, **k):
        _sm["n"] += 1; _sm["args"] = (a, k)
        return _mt0(*a, **k)
    RF.motion_track = _espion_mt
_ro = RFR({"src": {"file_path": MOV}, "srcIn": 1.0, "dur": 2.0})
check("d40_route_200_rend_le_resultat_du_tracker_avec_srcIn_et_dur",
      _ro[0] == 200 and isinstance(_ro[1], dict) and _ro[1].get("ok") is True and _ro[1].get("mode") == "suivi"
      and isinstance(_ro[1].get("points"), list) and _sm["n"] == 1
      and _sm["args"] is not None and _sm["args"][0][1:3] == (1.0, 2.0), (_ro, _sm))
_r404 = RFR({"src": {"file_path": str(pathlib.Path(TMP) / "absent.mp4")}, "srcIn": 0, "dur": 2})
_r415 = RFR({"src": {"file_path": VX}, "srcIn": 0, "dur": 2})
check("d40_route_404_source_inconnue_415_non_video_sans_analyse",
      _r404[0] == 404 and _r415[0] == 415 and _sm["n"] == 1, (_r404, _r415, _sm["n"]))
_bad3 = [RFR({"src": {"file_path": MOV}, "srcIn": 0}),
         RFR({"src": {"file_path": MOV}, "srcIn": 0, "dur": 0}),
         RFR({"src": {"file_path": MOV}, "srcIn": -1, "dur": 2}),
         RFR({"src": {"file_path": MOV}, "srcIn": "abc", "dur": 2}),
         RFR({"src": {"file_path": MOV}, "srcIn": 0, "dur": "nan"}),
         RFR({"src": {"file_path": MOV}, "srcIn": 0, "dur": 100000}),
         RFR({"src": None, "srcIn": 0, "dur": "x"})]
check("d40_route_400_parametres_avant_toute_resolution_temoin_bornes_permises",
      [b[0] for b in _bad3] == [400] * 7 and _sm["n"] == 1
      and RFR({"src": {"file_path": MOV}, "srcIn": 0, "dur": 14400})[0] == 200 and _sm["n"] == 2,
      (_bad3, _sm["n"]))
if _mt0 is not None:
    RF.motion_track = _mt0
import inspect as _insp
try:
    _src_render = _insp.getsource(MS.montage_render)
except Exception as _e:
    _src_render = ""
check("d40_render_transmet_reframe_nettoye_dans_la_normalisation_v1_comme_dz",
      '"dz": _dz_spec(c)' in _src_render and '"reframe": _reframe_of(c)' in _src_render
      and _src_render.index('"dz": _dz_spec(c)') < _src_render.index('"reframe": _reframe_of(c)')
      < _src_render.index("v2 = []"), len(_src_render))

print(f"\n=== {ok} passed, {fail} failed ===")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
