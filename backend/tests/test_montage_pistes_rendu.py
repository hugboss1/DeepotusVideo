# -*- coding: utf-8 -*-
"""P0 — chaque piste arrive au rendu. Banc-MIROIR : on lit le FICHIER rendu
(ffprobe, PIL, astats), jamais le code qui pretend le produire.
Sources synthetiques : V1 bleu 4 s muet, overlay PNG rouge, musique 200 Hz,
voix 2000 Hz amplifiee x4. Deux chemins : _build_montage_command en direct,
puis la ROUTE POST /api/montage/render (TestClient, tache de fond executee
avant le retour).
Run : & $PY tests/test_montage_pistes_rendu.py   (depuis backend/)

CONSTAT DU 03/09/2026 - le banc est sorti ROUGE au premier tour, sur les trois
chemins a la fois : `*_musique_audible_seule_3s` a -inf dB entre 3,0 et 3,8 s.
Cause racine MESUREE (pas deduite, et rien n'est affirme ici des internes
d'ffmpeg) : `sidechaincompress` rend un flux qui s'arrete a la fin de son
entree la PLUS COURTE. La voix sert de detecteur ; une voix de 2 s coupait
donc la musique bouclee a 2 s. ffprobe sur les trois fichiers rendus : flux
video 4,000 s, flux audio 2,000 s. Isole hors du depot :
    ffmpeg -f lavfi -i sine=d=6 -f lavfi -i sine=d=2 -filter_complex
      "[0:a][1:a]sidechaincompress=threshold=0.05:ratio=6:attack=50:release=400"
      out.wav  ->  2,0 s au lieu de 6 (ffmpeg 8.1.1, celui du PATH ici, le
      seul qui compte : le service emet un « ffmpeg » NU). AUCUNE DECIMALE :
      12 tours de la MEME commande sur le MEME binaire rendent 1,973696 /
      1,996916 / 2,000000 s — le vidage des dernieres trames n'est pas
      deterministe, et cette dispersion a deja ete lue deux fois en revue
      comme un ecart de version, puis de parametres. Elle n'est ni l'un ni
      l'autre : c'est du bruit de quantification de trames.
Correction : la chaine laterale [vsc] est prolongee par apad=whole_dur=total
(montage_service, section ducking). C'est ce que verrouille desormais
`*_audio_aussi_long_que_video_avec_musique`, l'assertion qui NOMME le
mecanisme, doublee de `*_musique_duckee_pendant_la_voix` : rallonger le
detecteur ne doit pas eteindre le ducking qu'il commande.
La musique disparaissait a la derniere syllabe du commentaire - ce qui
correspond au signalement « la piste musique n'est pas rendue ». Les overlays
V2, eux, sont sortis VERTS des le premier tour, sur les trois chemins : cette
moitie du signalement n'est PAS reproduite cote backend.

DEUX HYPOTHESES COTE ECRAN, NON MESUREES ICI, laissees a P1 et P7 (ce banc ne
touche pas au frontend) :
 (a) le bouton M d'une piste ecrit -40 dB dans `proj.mixDb`, autosauvegarde ET
     envoye au rendu (`svmTrackMute`, frontend/patches/son-vfx-montage.js
     ~l. 2943) : une musique « mise en sourdine pour ecouter la voix » repart
     au rendu a -40 dB, donc inaudible sans que rien ne le dise ;
 (b) le lecteur vivant ne joue ni A2 ni A3 (commentaire du vu-metre, meme
     fichier ~l. 2077) : ce que l'utilisateur entend AVANT de rendre n'est pas
     le mix - apercu et rendu peuvent diverger sans qu'il soit alerte.

LA REGLE DES ASSERTIONS NEGATIVES, PASSEE SUR CE BANC LE 05/09/2026. Elle
vient de l'en-tete de test_montage_media.py : un TEMOIN DISTINGUABLE, ou le
repli VIDE d'une garde, SE RETOURNE CONTRE TOUTE NEGATION. `a != b`,
`not (…)`, `x not in y`, `== []`, `== ""`, `is None` sont VRAIS PAR
CONSTRUCTION entre deux temoins comme sur un `{}` ou une `[]` de repli : la
ligne verdit sans avoir rien mesure. LA REGLE : toute assertion negative doit
d'abord exiger que ses operandes SOIENT ce qu'ils pretendent etre, et
seulement ensuite les comparer.

  CE QUE LA MESURE A TROUVE ICI — un `.json()` NU, et rien d'autre.
  (a) SANS FFMPEG le banc s'arrete FRANCHEMENT : `_exe()` imprime
      « SKIP: ffmpeg introuvable » et sort en 0, aucune assertion n'est
      jouee, donc AUCUNE ne peut verdir a vide. Verifie le 05/09/2026 avec
      `PATH=C:/Windows/System32;C:/Windows` ET `LOCALAPPDATA` detourne (sans
      quoi `_exe` retrouve le binaire embarque).
  (b) `j = c.get("/api/jobs/" + r.json()["job_id"]).json()` etait NU. Un
      corps qui n'est pas du JSON fait lever la lecture, et l'exception,
      traversant le bloc `with TestClient(app)`, arrive a une sortie de cycle
      de vie dont on ne revient pas : le banc SE FIGE au lieu de rougir.
      MESURE le 05/09/2026 (`& $PY scratchpad/vide2.py api503 …`, toute
      route `/api/…` en 503) : les trois lignes route_lancee, route_job_done
      et route_fichier_present ROUGISSENT desormais et sont IMPRIMEES.
      DECLARE : sous CE levier le processus ne rend toujours pas la main —
      mesure a part (scratchpad/sonde_sortie.py), un `with TestClient(app)`
      NU, sans un seul banc autour, bloque de la meme facon des que le
      levier est arme. Le blocage appartient au levier, pas aux assertions.
  AUCUNE ASSERTION NEGATIVE A REPARER : les deux seules de ce banc
  (`direct_ffmpeg_ok`, `tf_ffmpeg_ok`) exigent `returncode == 0` ET une
  taille de fichier non nulle.
"""
import json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp0_")
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
    """Une source qui ne se cree pas doit mourir ICI. Sans ce garde-fou, une
    panne de `sine`/`color` ressortait trois ecrans plus loin en erreur PIL ou
    ffprobe, sur une assertion qui n'a rien a voir."""
    r = sh(cmd)
    if r.returncode:
        print(f"  ECHEC fixture {label} : {r.stderr[-400:]}")
        sys.exit(1)

V1, OV, MUS, VOX = (os.path.join(TMP, n) for n in ("v1.mp4", "ov.png", "theme_music.wav", "voice.wav"))
fixture("v1", [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
               "color=c=0x2040a0:s=270x480:r=30:d=4", "-pix_fmt", "yuv420p", V1])
Image.new("RGB", (96, 96), (255, 40, 40)).save(OV)
fixture("musique", [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    "sine=frequency=200:sample_rate=44100:duration=6", MUS])
# Voix a 2000 Hz et 4x plus forte que le sinus nu — DEUX raisons mesurees.
# (a) 200/2000 Hz se separent proprement (deux lowpass a 400 Hz laissent la
#     musique et rejettent la voix) ; a 440/880 la voix fuitait dans la bande
#     musique et noyait la mesure (-50,9 dB de fuite contre -50,4 de musique).
# (b) le sinus de lavfi sort a -21 dBFS RMS ; au bus dialogue -6 dB le
#     detecteur tombe a -27 dBFS, SOUS le seuil 0,05 (-26 dBFS) du
#     sidechaincompress : le ducking ne reduisait que de 0,3 dB — le banc
#     nommait un mecanisme qu'il n'exercait pas. A x4 : detecteur
#     -15 dBFS, et 8,21 dB de ducking mesures au fichier rendu.
fixture("voix", [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                 "sine=frequency=2000:sample_rate=44100:duration=2",
                 "-af", "volume=4", VOX])

def probe(path):
    d = json.loads(sh([FP, "-v", "error", "-show_entries", "stream=codec_type:format=duration",
                       "-of", "json", path]).stdout or "{}")
    return [s["codec_type"] for s in d.get("streams", [])], float(d.get("format", {}).get("duration") or 0)

def stream_dur(path, kind):
    """Duree du PREMIER flux d'un type. C'est la mesure qui NOMME le defaut
    ferme ici : une piste audio plus courte que la video = du mix coupe."""
    d = json.loads(sh([FP, "-v", "error", "-select_streams", kind[0],
                       "-show_entries", "stream=duration", "-of", "json",
                       path]).stdout or "{}")
    ss = d.get("streams", [])
    return float(ss[0].get("duration") or 0) if ss else 0.0

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
    silence — c'est la meme valeur, ce n'est pas le meme fait. `pre` prefixe la
    chaine -af (filtrage de bande avant la mesure)."""
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

def verify(tag, out, cover=True):
    kinds, dur = probe(out)
    check(f"{tag}_une_video_une_audio", kinds.count("video") == 1 and kinds.count("audio") == 1, str(kinds))
    check(f"{tag}_duree_4s", abs(dur - 4.0) < 0.15, f"{dur}")
    # VRAI SOUS CONDITION, et le banc ne joue que des cas qui la remplissent :
    # le flux audio atteint la fin de la video des qu'une piste MUSIQUE existe
    # (entree -stream_loop -1, coupee a `total` par -t). SANS musique, le mix
    # s'arrete au dernier clip a1/a3 : une voix de 2 s dans une video de 4 s
    # laisse encore un flux audio de 2 s — RESIDUEL PRE-EXISTANT, hors de ce
    # correctif et non couvert ici. Ce que cette assertion verrouille, c'est
    # que le DUCKING ne raccourcisse plus le mix.
    da, dv = stream_dur(out, "audio"), stream_dur(out, "video")
    check(f"{tag}_audio_aussi_long_que_video_avec_musique", da >= dv - 0.15,
          f"audio {da}s, video {dv}s")
    b0, b2, b35 = mean_rgb(frame(out, 0.5)), mean_rgb(frame(out, 2.0)), mean_rgb(frame(out, 3.5))
    check(f"{tag}_overlay_absent_avant", b0[2] > b0[0] + 60, f"{b0}")
    if cover:
        check(f"{tag}_overlay_visible_pendant", b2[0] > 180 and b2[0] > b2[2] + 100, f"{b2}")
    else:
        im = frame(out, 2.0); w, h = im.size
        c = mean_rgb(im, (w // 2 - 8, h // 2 - 8, w // 2 + 8, h // 2 + 8))
        k = mean_rgb(im, (0, 0, 16, 16))
        check(f"{tag}_overlay_centre_rouge", c[0] > 180 and c[0] > c[2] + 100, f"{c}")
        check(f"{tag}_overlay_coin_bleu", k[2] > k[0] + 60, f"{k}")
    check(f"{tag}_overlay_absent_apres", b35[2] > b35[0] + 60, f"{b35}")
    m = rms_db(out, 3.0, 3.8); v = rms_db(out, 0.2, 1.8)
    # SEUILS ET LEURS MARGES, mesures sur les trois chemins de ce banc (mp4/AAC,
    # pas un graphe WAV isole) le 03/09/2026, a 0,01 dB pres d'un chemin a
    # l'autre :
    #   musique seule 3,0-3,8 s : -42,10 dB -> seuil -45, MARGE 2,9 dB
    #   voix 0,2-1,8 s          : -18,05 dB -> ecart a la musique 24,05 dB,
    #                                          seuil 6, marge 18,05 dB
    # La voix a donc plus de SIX FOIS la marge de la musique : le seuil -45 est
    # le plus serre du banc, c'est lui qui cassera le premier si l'encodage
    # change. Ne pas le desserrer sans remesurer : -45 laisse encore 2,9 dB.
    check(f"{tag}_musique_audible_seule_3s", m > -45, f"{m} dB")
    check(f"{tag}_voix_plus_forte_que_musique", v > m + 6, f"voix {v} dB, musique {m} dB")
    # Le correctif ALLONGE le detecteur : mal pose, il pourrait eteindre le
    # ducking sans rien casser d'autre. On le mesure dans la bande de la
    # musique (deux lowpass a 400 Hz ; la voix est a 2000 Hz) : duckee pendant
    # la voix, pleine apres. Mesure sur mp4/AAC : -50,84 dB pendant contre
    # -42,63 dB apres, soit 8,21 dB de ducking -> seuil 4, MARGE 4,21 dB.
    # (Le chiffre du graphe WAV isole, 8,2 dB, se retrouve tel quel apres
    # l'encodage AAC : rien a rattraper de ce cote.)
    # VERIFIE PAR MUTATION, sinon cette assertion ne vaudrait rien : en
    # remplacant la branche par `{music_lbl}anull[mduck]` + `[vsc]anullsink`,
    # elle vire au ROUGE sur les trois chemins (pendant -42,60 contre apres
    # -42,63 : 0,04 dB, aucun ducking) et elle SEULE — les 30 autres restent
    # vertes. C'est exactement le trou signale a la revue : avant elle, on
    # pouvait supprimer tout le sidechaincompress sans faire rougir le banc.
    LP = "lowpass=f=400,lowpass=f=400,"
    dpen, dapr = rms_db(out, 0.4, 1.7, LP), rms_db(out, 3.0, 3.8, LP)
    check(f"{tag}_musique_duckee_pendant_la_voix", dapr > dpen + 4,
          f"pendant {dpen} dB, apres {dapr} dB")

print("\n[1] _build_montage_command en direct — overlay cover, voix, musique bouclee")
out1 = os.path.join(TMP, "direct.mp4")
cmd, total = M._build_montage_command(v1_spec(), [ov_spec()], vox_spec(), mus_spec(), w=270, h=480,
                                      fps=30, mix_db={}, ducking=True, duration_master=True,
                                      preview=False, out=out1)
r = sh(cmd); check("direct_ffmpeg_ok", r.returncode == 0 and os.path.getsize(out1) > 0, r.stderr[-300:])
verify("direct", out1)

print("\n[2] overlay TRANSFORME (scale 0,3 au centre) + apercu 480p")
out2 = os.path.join(TMP, "tf.mp4")
cmd, _ = M._build_montage_command(v1_spec(), [ov_spec({"x": .5, "y": .5, "scale": .3, "rotate": 0.0})],
                                  vox_spec(), mus_spec(), w=66, h=120, fps=30, mix_db={},
                                  ducking=True, duration_master=True, preview=True, out=out2)
r = sh(cmd); check("tf_ffmpeg_ok", r.returncode == 0, r.stderr[-300:])
verify("tf", out2, cover=False)

print("\n[3] par la ROUTE — clips v2 / a1 / a2 en {file_path}, tache de fond")
from fastapi.testclient import TestClient               # noqa: E402
from app.main import app                                # noqa: E402
body = {"name": "p0", "ratio": "9:16", "preview": False, "mix": {"dialogue": -6, "musique": -18, "sfx": -12},
        "clips": [{"tr": "v1", "src": {"file_path": V1}, "start": 0, "end": 4, "srcIn": 0, "transition": "cut"},
                  {"tr": "v2", "src": {"file_path": OV}, "start": 1, "end": 3},
                  {"tr": "a1", "src": {"file_path": VOX}, "start": 0, "end": 2},
                  {"tr": "a2", "src": {"file_path": MUS}, "start": 0, "end": 4, "loop": True}]}
with TestClient(app) as c:
    r = c.post("/api/montage/render", json=body)
    # ROUGIR, PAS MOURIR (faute n°6) : `r.json()` sur un corps qui n'est pas
    # du JSON leve, et l'exception traverse le bloc `with TestClient(app)`,
    # dont la sortie attend l'arret des taches de fond — le banc SE FIGE au
    # lieu de mourir. Le job_id est lu UNE fois, garde, et son absence rend
    # une adresse qu'aucune route ne sert (404), jamais une exception.
    _dr = r.json() if r.status_code == 200 else {}
    check("route_lancee", r.status_code == 200 and _dr.get("job_id"), r.text[:200])
    _rj = c.get("/api/jobs/" + str(_dr.get("job_id") or "sans-job"))
    j = _rj.json() if _rj.status_code == 200 else {}
    check("route_job_done", j.get("status") == "done", str(j.get("error") or j.get("status")))
    fp = j.get("final_video_path") or ""
    check("route_fichier_present", fp and os.path.exists(fp), fp)
    if fp and os.path.exists(fp):
        # le rendu reel est 1080x1920 : memes lectures, seuls les seuils sont relatifs
        verify("route", fp)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
