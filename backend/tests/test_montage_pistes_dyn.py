# -*- coding: utf-8 -*-
"""P1 — PISTES DYNAMIQUES : c'est l'ORDRE des pistes qui decide de la
composition, pas une table figee dans le code. Meme banc-MIROIR que
test_montage_pistes_rendu.py : on lit le FICHIER rendu (ffprobe, PIL, astats),
jamais le code qui pretend le produire. En-tete recopie tel quel de ce banc.
Run : & $PY tests/test_montage_pistes_dyn.py   (depuis backend/)

CE QUI EST FERME ICI
  [1] `_tracks_meta(raw)` : `tracks` absent => la table historique (v2 au-dessus
      de v1, a1 dialogue, a2 musique bouclee, a3 sfx) ; present => l'ordre du
      payload, du HAUT vers le BAS de la timeline, fixe `layer` (rang de
      composition des overlays, 0 = juste au-dessus de V1) et le bus.
  [2] non-regression : un overlay SANS `layer` et le meme avec `layer:0`
      rendent la MEME commande, argument pour argument.
  [3] MIROIR, en direct : deux overlays au meme instant, l'un rouge large,
      l'autre vert etroit, tous deux centres. Celle du HAUT couvre celle du
      bas — on lit la couleur au CENTRE de la trame rendue. Sans `layer` le
      tri se faisait sur `start` seul : a start egal l'ordre d'insertion
      gagnait toujours, donc UNE des deux orientations sortait fausse.
  [4] MIROIR, par la ROUTE POST /api/montage/render : c'est la seule section
      qui exerce le CABLAGE de `_tracks_meta` dans `montage_render._run()`.
      Le payload declare une piste `v3` (inconnue de la table historique) et
      une piste audio `a5`. Avant le cablage, la boucle overlays testait
      `c.get("tr") != "v2"` et la boucle audio `c.get("tr") not in
      ("a1","a2","a3")` : le clip v3 et le clip a5 etaient purement JETES.
      MUTATION VERIFIEE (03/09/2026) : en remettant ces deux tests d'egalite
      a la place de `meta`, `route_v3_au_dessus_centre_vert` et
      `route_voix_a5_audible` virent au ROUGE et elles seules.

CE QUE CE BANC N'AFFIRME PAS. Un SECOND clip du bus `musique` reste range
dans les BRUITAGES (`"tr": "a1" if bus == "dialogue" else "a3"`) : P1 lui
rend son GAIN musique, mais il n'est ni boucle (`-stream_loop -1` n'est pose
que sur l'entree `music`) ni ducke (seule `music` alimente le
sidechaincompress). Un seul clip devient `music` : le PREMIER du bus musique
porteur de `loop`. C'est un reste assume, pas un point ferme."""
import json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp1_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _exe(name):
    p = shutil.which(name)
    if p:
        return p
    cand = os.path.expandvars(rf"%LOCALAPPDATA%\DeepotusVideoGen\bin\{name}.exe")
    if os.path.isfile(cand):
        os.environ["PATH"] = os.path.dirname(cand) + os.pathsep + os.environ["PATH"]
        return cand   # la commande sous test lance un "ffmpeg" NU : il faut le PATH
    print(f"SKIP: {name} introuvable — le banc-miroir ne peut rien mesurer")
    sys.exit(0)


FF, FP = _exe("ffmpeg"), _exe("ffprobe")
from PIL import Image                                   # noqa: E402
from app.services import montage_service as M           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def sh(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")

def fixture(label, cmd):
    """Une source qui ne se cree pas doit mourir ICI (meme garde-fou que P0)."""
    r = sh(cmd)
    if r.returncode:
        print(f"  ECHEC fixture {label} : {r.stderr[-400:]}")
        sys.exit(1)

V1, OV, MUS, VOX = (os.path.join(TMP, n) for n in ("v1.mp4", "ov.png", "theme_music.wav", "voice.wav"))
GV = os.path.join(TMP, "green.png")
fixture("v1", [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
               "color=c=0x2040a0:s=270x480:r=30:d=4", "-pix_fmt", "yuv420p", V1])
Image.new("RGB", (96, 96), (255, 40, 40)).save(OV)
Image.new("RGB", (40, 40), (40, 220, 60)).save(GV)
fixture("musique", [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    "sine=frequency=200:sample_rate=44100:duration=6", MUS])
# Memes raisons qu'en P0 : 200 Hz / 2000 Hz se separent proprement au filtre,
# et x4 met le detecteur du ducking au-dessus de son seuil.
fixture("voix", [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                 "sine=frequency=2000:sample_rate=44100:duration=2",
                 "-af", "volume=4", VOX])

def probe(path):
    d = json.loads(sh([FP, "-v", "error", "-show_entries", "stream=codec_type:format=duration",
                       "-of", "json", path]).stdout or "{}")
    return [s["codec_type"] for s in d.get("streams", [])], float(d.get("format", {}).get("duration") or 0)

def frame(path, t):
    png = os.path.join(TMP, f"f_{os.path.basename(path)}_{t}.png")
    sh([FF, "-y", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", png])
    return Image.open(png).convert("RGB")

def mean_rgb(im, box=None):
    if box: im = im.crop(box)
    px = list(im.getdata()); n = float(len(px))
    return tuple(round(sum(p[i] for p in px) / n, 1) for i in range(3))

def rms_db(path, t0, t1, pre=""):
    """-999.0 = silence MESURE (astats a rendu -inf). Un ECHEC de mesure leve :
    un banc qui ne mesure pas ne doit pas ressembler a un banc qui mesure du
    silence. `pre` prefixe la chaine -af (filtrage de bande avant la mesure)."""
    r = sh([FF, "-hide_banner", "-ss", str(t0), "-t", str(t1 - t0), "-i", path, "-vn",
            "-af", pre + "astats=measure_overall=RMS_level:measure_perchannel=none",
            "-f", "null", "-"])
    for ln in r.stderr.splitlines():
        if "RMS level dB" in ln:
            v = ln.split(":")[-1].strip()
            return -999.0 if v == "-inf" else float(v)
    raise RuntimeError(f"astats muet sur {path} [{t0};{t1}] :\n{r.stderr[-400:]}")

def v1_spec():
    return [{"path": V1, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
             "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}]
def ov_spec(tf=None):
    return {"path": OV, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 1.0,
            "end": 3.0, "opacity": None, "tf": tf, "mp": None}
AUD = {"fade_in": 0, "fade_out": 0, "fade_in_curve": None, "fade_out_curve": None,
       "fx_chain": "", "speed": 0.0, "volume_points": None}
def vox_spec():
    return [dict(AUD, tr="a1", path=VOX, src_dur=2.0, src_in=0.0, start=0.0, end=2.0,
                 gain=M._db_to_gain(-6))]
def mus_spec():
    return dict(AUD, path=MUS, gain=M._db_to_gain(-18))


print("\n[1] _tracks_meta : absent = table historique, sinon ordre haut→bas")
m = M._tracks_meta(None)
check("meta_legacy_v2_layer0", m["v2"]["layer"] == 0 and m["v2"]["kind"] == "video",
      str(m.get("v2")))
check("meta_legacy_a2_musique_loop", m["a2"]["bus"] == "musique" and m["a2"]["loop"] is True,
      str(m.get("a2")))
check("meta_legacy_a3_sfx", m["a3"]["bus"] == "sfx" and m["a3"]["loop"] is False,
      str(m.get("a3")))
m = M._tracks_meta([{"id": "v3", "kind": "video"}, {"id": "v2", "kind": "video"},
                    {"id": "v1", "kind": "video"},
                    {"id": "a1", "kind": "audio", "bus": "dialogue"},
                    {"id": "a4", "kind": "audio", "bus": "musique", "loop": True},
                    {"id": "a2", "kind": "audio", "bus": "musique", "loop": False}])
check("meta_v3_au_dessus_de_v2", m["v3"]["layer"] == 1 and m["v2"]["layer"] == 0,
      f'v3 {m["v3"]["layer"]}, v2 {m["v2"]["layer"]}')
check("meta_a4_boucle_a2_non",
      m["a4"]["loop"] is True and m["a2"]["loop"] is False and m["a2"]["bus"] == "musique",
      f'a4 {m["a4"]}, a2 {m["a2"]}')
check("meta_bus_inconnu_retombe_sfx",
      M._tracks_meta([{"id": "a9", "kind": "audio", "bus": "x"}])["a9"]["bus"] == "sfx")

print("\n[2] non-régression : sans `layer`, la commande ne bouge pas d'un octet")
ref, _ = M._build_montage_command(v1_spec(), [ov_spec()], vox_spec(), mus_spec(), w=270, h=480, fps=30,
                                  mix_db={}, ducking=True, duration_master=True, preview=False, out="o.mp4")
got, _ = M._build_montage_command(v1_spec(), [dict(ov_spec(), layer=0)], vox_spec(), mus_spec(), w=270, h=480,
                                  fps=30, mix_db={}, ducking=True, duration_master=True, preview=False, out="o.mp4")
check("cmd_identique_layer0", got == ref,
      f"{len(ref)} vs {len(got)} args")

print("\n[3] miroir : deux pistes d'overlay — celle du HAUT couvre celle du bas")
def two(top_green):
    red = dict(ov_spec({"x": .5, "y": .5, "scale": .6, "rotate": 0.0}), layer=0 if top_green else 1)
    grn = dict(ov_spec({"x": .5, "y": .5, "scale": .3, "rotate": 0.0}), path=GV, layer=1 if top_green else 0)
    out = os.path.join(TMP, f"two_{int(top_green)}.mp4")
    cmd, _ = M._build_montage_command(v1_spec(), [red, grn], [], None, w=270, h=480, fps=30, mix_db={},
                                      ducking=False, duration_master=False, preview=False, out=out)
    r = sh(cmd)
    if r.returncode:
        print(f"  ECHEC rendu two_{int(top_green)} : {r.stderr[-400:]}")
        sys.exit(1)
    im = frame(out, 2.0); w, h = im.size
    return mean_rgb(im, (w // 2 - 6, h // 2 - 6, w // 2 + 6, h // 2 + 6))
c = two(True);  check("vert_au_dessus_centre_vert", c[1] > 150 and c[1] > c[0] + 60, f"{c}")
c = two(False); check("rouge_au_dessus_centre_rouge", c[0] > 150 and c[0] > c[1] + 60, f"{c}")

print("\n[4] par la ROUTE — `tracks` du payload : v3 (piste neuve) au-dessus de v2,")
print("    voix sur a5 (piste neuve, bus dialogue). Aperçu 480p.")
from fastapi.testclient import TestClient               # noqa: E402
from app.main import app                                # noqa: E402
CTR = {"x": 0.5, "y": 0.5, "rotate": 0}
body = {"name": "p1", "ratio": "9:16", "preview": True, "duration_master": False,
        "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
        # ordre HAUT → BAS : v3 est listée au-dessus de v2, elle doit couvrir.
        "tracks": [{"id": "v3", "kind": "video"}, {"id": "v2", "kind": "video"},
                   {"id": "v1", "kind": "video"},
                   {"id": "a5", "kind": "audio", "bus": "dialogue"},
                   {"id": "a2", "kind": "audio", "bus": "musique", "loop": True}],
        "clips": [{"tr": "v1", "src": {"file_path": V1}, "start": 0, "end": 4, "srcIn": 0,
                   "transition": "cut"},
                  {"tr": "v2", "src": {"file_path": OV}, "start": 1, "end": 3, "scale": 0.6, **CTR},
                  {"tr": "v3", "src": {"file_path": GV}, "start": 1, "end": 3, "scale": 0.3, **CTR},
                  {"tr": "a5", "src": {"file_path": VOX}, "start": 0, "end": 2},
                  {"tr": "a2", "src": {"file_path": MUS}, "start": 0, "end": 4, "loop": True}]}
with TestClient(app) as cli:
    r = cli.post("/api/montage/render", json=body)
    check("route_lancee", r.status_code == 200 and r.json().get("job_id"), r.text[:200])
    j = cli.get("/api/jobs/" + r.json()["job_id"]).json()
    check("route_job_done", j.get("status") == "done", str(j.get("error") or j.get("status")))
    fp = j.get("final_video_path") or ""
    check("route_fichier_present", bool(fp) and os.path.exists(fp), fp)
    if fp and os.path.exists(fp):
        kinds, _dur = probe(fp)
        check("route_une_video_une_audio",
              kinds.count("video") == 1 and kinds.count("audio") == 1, str(kinds))
        im = frame(fp, 2.0); w, h = im.size
        c = mean_rgb(im, (w // 2 - 6, h // 2 - 6, w // 2 + 6, h // 2 + 6))
        k = mean_rgb(im, (0, 0, 16, 16))
        # v3 (vert, étroit) est listée AU-DESSUS de v2 (rouge, large) : au
        # centre on doit lire le VERT. Sans le câblage de _tracks_meta la
        # boucle overlays jetait v3 (tr != "v2") et le centre sortait ROUGE.
        check("route_v3_au_dessus_centre_vert", c[1] > 150 and c[1] > c[0] + 60, f"{c}")
        check("route_v2_visible_coin_bleu", k[2] > k[0] + 60, f"{k}")
        # a5 (bus dialogue) doit atteindre le mix. La voix est à 2000 Hz, la
        # musique à 200 Hz : deux highpass à 1000 Hz ne laissent passer que la
        # voix. Sans le câblage, a5 était jeté et cette bande retombait au
        # plancher de l'encodage AAC.
        HP = "highpass=f=1000,highpass=f=1000,"
        vpen, vapr = rms_db(fp, 0.3, 1.7, HP), rms_db(fp, 3.0, 3.8, HP)
        check("route_voix_a5_audible", vpen > vapr + 12,
              f"pendant {vpen} dB, apres {vapr} dB")

print("\n[5] aller-retour POST /save → GET /project : l'ordre des pistes")
print("    survit au rechargement (sans quoi les clips d'une piste ajoutée")
print("    retomberaient sur une piste inconnue, donc hors du rendu).")
TRACKS = [{"id": "v3", "kind": "video"}, {"id": "v2", "kind": "video"},
          {"id": "v1", "kind": "video"},
          {"id": "a1", "kind": "audio", "bus": "dialogue"},
          {"id": "a4", "kind": "audio", "bus": "musique", "loop": True},
          {"id": "s1", "kind": "subs"}]
with TestClient(app) as cli:
    r = cli.post("/api/montage/save", json={
        "name": "p1", "ratio": "9:16", "duration": 4.0,
        "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
        "tracks": TRACKS,
        "clips": [{"tr": "v1", "id": "c1", "label": "v1", "start": 0, "end": 4,
                   "src": {"file_path": V1}, "srcIn": 0, "transition": "cut"},
                  {"tr": "v3", "id": "c2", "label": "ov", "start": 1, "end": 3,
                   "src": {"file_path": GV}, "srcIn": 0}]})
    check("save_acceptee", r.status_code == 200 and r.json().get("ok"), r.text[:200])
    d = cli.get("/api/montage/project").json()
    check("project_saved", d.get("saved") is True, str(d.get("saved")))
    check("project_rend_les_pistes", d.get("tracks") == TRACKS, str(d.get("tracks")))
    # et la loi de classement les relit à l'identique : v3 au-dessus de v2,
    # a4 devenue la piste bouclée à la place d'a2 (absente du projet).
    # `.get` partout : si la clé `tracks` n'est pas revenue, cette assertion
    # doit sortir ROUGE et le banc finir sa ligne — pas mourir sur un KeyError
    # trois lignes avant le total (constaté en mutant POST /save).
    mm = M._tracks_meta(d.get("tracks"))
    g = lambda t, k: (mm.get(t) or {}).get(k)
    check("project_pistes_relues_par_meta",
          g("v3", "layer") == 1 and g("v2", "layer") == 0
          and g("a4", "loop") is True and g("s1", "kind") == "subs",
          str({k: mm.get(k) for k in ("v3", "v2", "a4", "s1")}))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
