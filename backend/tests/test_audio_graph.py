# -*- coding: utf-8 -*-
"""Atelier sonore, moteur de graphe audio (t270, 21/10/2026) — `app/services/audio_graph.py` et ses routes
(`app/api/audio_graph_routes.py`, sous /api/audio/graph) : un graphe de nœuds (source, effet, gain, panoramique, tempo,
hauteur, plage, décalage, mix, ducking, sortie) validé puis compilé en UN filter_complex ffmpeg, rendu en aperçu
(10 s, gratuit, jamais rangé) ou en fichier de la Bibliothèque (relation « atelier »).
Sections :
  [N] catalogue des nœuds (GET /noeuds) : types, entrées, bornes des paramètres, effets = vocabulaire FX partagé ;
  [V] validation : chaque refus avec son message (cycle, sortie absente ou double, port libre ou hors bornes, lien
      vers un nœud inconnu, source introuvable ou hors dossier, type inconnu, id mal formé, trop de nœuds, plage
      bouclée ou fondue sans fin) ; bornes ramenées dans le contrat ; nœuds sans chemin vers la sortie ignorés ;
  [C] compilation FIGÉE sur six graphes types (chaîne exacte) ;
  [R] rendu RÉEL par ffmpeg sur des sons de synthèse : durées, aperçu borné, fichier rangé avec son sidecar ;
  [H] routes : 400 avec le message, aperçu audio/mpeg non rangé, rendu rangé + lignée, écriture refusée hors boucle ;
  [I] messages d'erreur traduits (i18n_l10_erreurs --check).
Run (depuis backend/) : & $PY tests/test_audio_graph.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzgraphe_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir()
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


def refus(fn, *a):
    try:
        fn(*a)
    except ValueError as e:
        return str(e)
    return None


from app.services import audio_graph as AG  # noqa: E402
from app.services import sfx_service as SX  # noqa: E402

AUDIO = SX._audio_dir()
FMT = "aresample=44100,aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"


def sine(nom, s, f=440):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={f}:duration={s}",
                    "-ac", "2", "-c:a", "libmp3lame", "-b:a", "96k", str(AUDIO / nom)], check=True)


sine("musique.mp3", 3, 220)
sine("voix.mp3", 2, 880)
sine("long.mp3", 14, 330)


def G(noeuds, liens):
    return {"noeuds": [{"id": i, "type": t, "params": p} for i, t, p in noeuds],
            "liens": [{"de": a, "vers": b, "entree": e} for a, b, e in liens]}


# ── [N] catalogue ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[N] catalogue des nœuds")
CAT = AG.catalogue()
TYPES = {t["type"]: t for t in CAT["noeuds"]}
check("N1 onze types de nœuds", sorted(TYPES) == sorted(["source", "effet", "gain", "pan", "tempo", "hauteur", "plage",
                                                          "decalage", "mix", "duck", "sortie"]), sorted(TYPES))
check("N2 entrées : source 0, sortie 1, mix 2 à 8 (réglable), ducking 2 (principal, déclencheur)",
      TYPES["source"]["entrees"] == 0 and TYPES["sortie"]["entrees"] == 1 and TYPES["duck"]["entrees"] == 2
      and TYPES["mix"]["entrees"] == 2 and TYPES["mix"]["params"]["entrees"] == [2, 8, 2], TYPES.get("mix"))
check("N3 les effets sont le vocabulaire FX partagé (mêmes bornes que le Montage)",
      sorted(CAT["effets"]) == sorted(SX._FX_PARAMS)
      and all(CAT["effets"][k] == {p: list(b) for p, b in SX._FX_PARAMS[k].items()} for k in SX._FX_PARAMS), CAT["effets"].keys())
check("N4 bornes : gain −40/+12 dB, tempo 0,5-2, hauteur ±12 demi-tons, boucles 1-16",
      TYPES["gain"]["params"]["db"] == [-40, 12, 0] and TYPES["tempo"]["params"]["facteur"] == [0.5, 2, 1]
      and TYPES["hauteur"]["params"]["demi_tons"] == [-12, 12, 0] and TYPES["plage"]["params"]["boucles"] == [1, 16, 1],
      TYPES.get("plage"))

# ── [V] validation ────────────────────────────────────────────────────────────────────────────────────────────────
print("[V] validation")
SRC = ("s", "source", {"fichier": "musique.mp3"})
OUT = ("o", "sortie", {})
check("V1 cycle refusé", "cycle" in (refus(AG.valider, G([SRC, ("a", "gain", {}), ("b", "gain", {}), ("m", "mix", {}), OUT],
                                                             [("s", "m", 0), ("b", "m", 1), ("m", "a", 0), ("a", "b", 0), ("m", "o", 0)])) or ""))
check("V2 sans sortie", (refus(AG.valider, G([SRC], [])) or "").startswith("graphe : une sortie"))
check("V3 deux sorties", (refus(AG.valider, G([SRC, OUT, ("o2", "sortie", {})], [("s", "o", 0), ("s", "o2", 0)])) or "")
      .startswith("graphe : une sortie"))
check("V4 port d'entrée laissé libre", "entrée 1 libre" in (refus(AG.valider, G([SRC, ("m", "mix", {}), OUT],
                                                                               [("s", "m", 0), ("m", "o", 0)])) or ""))
check("V5 port hors bornes", "entrée 3" in (refus(AG.valider, G([SRC, ("g", "gain", {}), OUT],
                                                                [("s", "g", 3), ("g", "o", 0)])) or ""))
check("V6 deux liens sur la même entrée", "déjà reliée" in (refus(AG.valider, G([SRC, ("s2", "source", {"fichier": "voix.mp3"}), OUT],
                                                                               [("s", "o", 0), ("s2", "o", 0)])) or ""))
check("V7 lien vers un nœud inconnu", "inconnu" in (refus(AG.valider, G([SRC, OUT], [("s", "zz", 0), ("s", "o", 0)])) or ""))
check("V8 source introuvable", "introuvable" in (refus(AG.valider, G([("s", "source", {"fichier": "absent.mp3"}), OUT],
                                                                     [("s", "o", 0)])) or ""))
check("V9 source hors du dossier audio : le nom seul est gardé (../ retiré) puis cherché",
      "introuvable" in (refus(AG.valider, G([("s", "source", {"fichier": "../t.db"}), OUT], [("s", "o", 0)])) or ""))
check("V10 type inconnu", "type inconnu" in (refus(AG.valider, G([SRC, ("x", "flanger3000", {}), OUT],
                                                                 [("s", "x", 0), ("x", "o", 0)])) or ""))
check("V11 effet inconnu", "effet inconnu" in (refus(AG.valider, G([SRC, ("x", "effet", {"fx": "laser"}), OUT],
                                                                   [("s", "x", 0), ("x", "o", 0)])) or ""))
check("V12 id mal formé ou en double", "id" in (refus(AG.valider, G([SRC, ("s", "gain", {}), OUT], [("s", "o", 0)])) or "")
      and "id" in (refus(AG.valider, G([("a b", "source", {"fichier": "musique.mp3"}), OUT], [("a b", "o", 0)])) or ""))
check("V13 64 nœuds au plus", "64" in (refus(AG.valider, G([SRC, OUT] + [(f"g{i}", "gain", {}) for i in range(63)],
                                                           [("s", "o", 0)])) or ""))
check("V14 plage bouclée ou fondue en sortie sans fin : refus",
      "fin" in (refus(AG.valider, G([SRC, ("p", "plage", {"boucles": 3}), OUT], [("s", "p", 0), ("p", "o", 0)])) or "")
      and "fin" in (refus(AG.valider, G([SRC, ("p", "plage", {"fondu_sortie": 1}), OUT], [("s", "p", 0), ("p", "o", 0)])) or ""))
V = AG.valider(G([SRC, ("g", "gain", {"db": 99}), ("t", "tempo", {"facteur": "x"}), ("orph", "gain", {}), OUT],
                 [("s", "g", 0), ("g", "t", 0), ("t", "o", 0)]))
check("V15 bornes ramenées dans le contrat, valeur illisible = défaut ; nœud sans chemin vers la sortie ignoré",
      V["params"]["g"]["db"] == 12 and V["params"]["t"]["facteur"] == 1 and V["ignores"] == ["orph"]
      and V["sources"] == ["musique.mp3"], V)
check("V16 graphe non objet refusé", (refus(AG.valider, [1, 2]) or "").startswith("graphe :"))

# ── [C] compilation figée ─────────────────────────────────────────────────────────────────────────────────────────
print("[C] compilation figée")


def comp(g):
    c = AG.compiler(AG.valider(g))
    return c["filtre"], [p.name for p in c["entrees"]]


f1 = comp(G([SRC, OUT], [("s", "o", 0)]))
check("C1 source → sortie", f1 == (f"[0:a]{FMT}[n0];[n0]anull[sortie]", ["musique.mp3"]), f1)
f2 = comp(G([SRC, ("r", "effet", {"fx": "reverb", "mix": 40, "decay_s": 2}), OUT], [("s", "r", 0), ("r", "o", 0)]))
check("C2 effet : le fragment du vocabulaire FX partagé",
      f2[0] == f"[0:a]{FMT}[n0];[n0]{SX._fx_reverb({'mix': 40.0, 'decay_s': 2.0})}[n1];[n1]anull[sortie]", f2)
f3 = comp(G([SRC, ("g", "gain", {"db": -6}), ("t", "tempo", {"facteur": 1.5}), ("h", "hauteur", {"demi_tons": 12}), OUT],
            [("s", "g", 0), ("g", "t", 0), ("t", "h", 0), ("h", "o", 0)]))
check("C3 gain → tempo → hauteur (une octave : asetrate ×2, atempo ½)",
      f3[0] == f"[0:a]{FMT}[n0];[n0]volume=-6dB[n1];[n1]atempo=1.5[n2];"
               "[n2]asetrate=88200,aresample=44100,atempo=0.5[n3];[n3]anull[sortie]", f3)
f4 = comp(G([SRC, ("v", "source", {"fichier": "voix.mp3"}), ("m", "mix", {}), OUT],
            [("s", "m", 0), ("v", "m", 1), ("m", "o", 0)]))
check("C4 deux sources → mix : amix sans normalisation, durée la plus longue",
      f4 == (f"[0:a]{FMT}[n0];[1:a]{FMT}[n1];[n0][n1]amix=inputs=2:duration=longest:normalize=0[n2];[n2]anull[sortie]",
             ["musique.mp3", "voix.mp3"]), f4)
f5 = comp(G([SRC, ("v", "source", {"fichier": "voix.mp3"}), ("d", "duck", {"ratio": 8}), ("m", "mix", {}), OUT],
            [("s", "d", 0), ("v", "d", 1), ("d", "m", 0), ("v", "m", 1), ("m", "o", 0)]))
check("C5 ducking : la voix pilote (prolongée par apad) ET se mêle (lue deux fois → asplit), chaîne partagée",
      f5[0] == f"[0:a]{FMT}[n0];[1:a]{FMT},asplit=2[n1_0][n1_1];[n1_0]apad[n2_sc];"
               f"[n0][n2_sc]{SX.ducking_filter(SX.parse_ducking({'ratio': 8}))}[n2];"
               "[n2][n1_1]amix=inputs=2:duration=longest:normalize=0[n3];[n3]anull[sortie]", f5)
f6 = comp(G([SRC, ("p", "plage", {"debut": 0.5, "fin": 1.5, "boucles": 3, "fondu_entree": 0.2, "fondu_sortie": 0.4}),
             ("d", "decalage", {"secondes": 1.25}), ("q", "pan", {"pan": -50}), OUT],
            [("s", "p", 0), ("p", "d", 0), ("d", "q", 0), ("q", "o", 0)]))
gl, gr = SX.pan_gains(-0.5)
check("C6 plage (bornes, 3 boucles, fondus) → décalage → panoramique",
      f6[0] == f"[0:a]{FMT}[n0];[n0]atrim=start=0.5:end=1.5,asetpts=PTS-STARTPTS,aloop=loop=2:size=44100,"
               "asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.2,afade=t=out:st=2.6:d=0.4[n1];"
               "[n1]adelay=1250:all=1[n2];"
               f"[n2]pan=stereo|c0={SX._g(gl)}*c0|c1={SX._g(gr)}*c1[n3];[n3]anull[sortie]", f6)
f7 = comp(G([SRC, ("g", "gain", {"db": 0}), ("t", "tempo", {}), ("h", "hauteur", {}), ("d", "decalage", {}),
             ("e", "effet", {"fx": "echo", "mix": 0}), OUT],
            [("s", "g", 0), ("g", "t", 0), ("t", "h", 0), ("h", "d", 0), ("d", "e", 0), ("e", "o", 0)]))
check("C7 nœuds neutres : anull (jamais un fragment vide dans la chaîne)",
      f7[0] == f"[0:a]{FMT}[n0];" + "".join(f"[n{i}]anull[n{i + 1}];" for i in range(5)) + "[n5]anull[sortie]", f7)

# ── [R] rendu réel ────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] rendu réel (ffmpeg)")
dur = SX._probe_duration
GT = G([SRC, ("t", "tempo", {"facteur": 1.5}), OUT], [("s", "t", 0), ("t", "o", 0)])
R1 = AG.rendre(GT, nom="essai tempo")
check("R1 tempo ×1,5 : 3 s → 2 s, fichier rangé atelier_*.mp3 avec son sidecar",
      R1["filename"].startswith("atelier_essai_tempo") and abs(dur(AUDIO / R1["filename"]) - 2.0) < 0.15
      and SX.load_meta()[R1["filename"]]["kind"] == "atelier"
      and SX.load_meta()[R1["filename"]]["parents"] == ["musique.mp3"]
      and SX.load_meta()[R1["filename"]]["graphe"] == AG.valider(GT)["graphe"], R1)
R2 = AG.rendre(G([SRC, ("v", "source", {"fichier": "voix.mp3"}), ("d", "duck", {}), ("m", "mix", {}), OUT],
                 [("s", "d", 0), ("v", "d", 1), ("d", "m", 0), ("v", "m", 1), ("m", "o", 0)]))
check("R2 ducking + mix : durée de la plus longue (3 s), nom par défaut", R2["filename"].startswith("atelier_")
      and abs(dur(AUDIO / R2["filename"]) - 3.0) < 0.15, R2)
R3 = AG.rendre(G([SRC, ("p", "plage", {"debut": 0, "fin": 1, "boucles": 4}), OUT], [("s", "p", 0), ("p", "o", 0)]))
check("R3 plage bouclée 4 fois : 4 s", abs(dur(AUDIO / R3["filename"]) - 4.0) < 0.15, R3)
AP = AG.apercu(G([("s", "source", {"fichier": "long.mp3"}), OUT], [("s", "o", 0)]), depuis=2)
check("R4 aperçu : 10 s au plus depuis la position demandée, fichier temporaire hors Bibliothèque",
      abs(dur(AP) - 10.0) < 0.2 and AP.parent != AUDIO and AP.name not in SX.load_meta(), AP)
AP.unlink(missing_ok=True)
R5 = AG.rendre(GT, nom="essai tempo")
check("R5 deux rendus du même nom : jamais d'écrasement", R5["filename"] != R1["filename"]
      and (AUDIO / R1["filename"]).is_file(), (R1, R5))

# ── [H] routes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[H] routes")
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

from app.services.storage import init_db  # noqa: E402
import asyncio  # noqa: E402


def _attendre(c):                          # hygiène des lanceurs : jamais asyncio.run() en tête de module
    return asyncio.run(c)


_attendre(init_db())
LOC = TestClient(app, client=("127.0.0.1", 50000))
r = LOC.get("/api/audio/graph/noeuds")
check("H1 GET /noeuds : le catalogue", r.status_code == 200 and r.json() == json.loads(json.dumps(CAT)), r.text[:200])
r = LOC.post("/api/audio/graph/valider", json=G([SRC, OUT], [("s", "o", 0)]))
check("H2 POST /valider : ok, sources, ignorés", r.status_code == 200 and r.json().get("ok") is True
      and r.json().get("sources") == ["musique.mp3"], r.text[:300])
r = LOC.post("/api/audio/graph/valider", json=G([SRC], []))
check("H3 POST /valider refusé : 400 avec le message", r.status_code == 400 and "sortie" in str(r.json().get("detail")),
      r.text[:300])
avant = sorted(p.name for p in AUDIO.iterdir())
r = LOC.post("/api/audio/graph/apercu", json={"graphe": GT, "depuis": 0})
check("H4 POST /apercu : audio/mpeg, rien de rangé dans la Bibliothèque",
      r.status_code == 200 and r.headers["content-type"].startswith("audio/mpeg") and len(r.content) > 1000
      and sorted(p.name for p in AUDIO.iterdir()) == avant, (r.status_code, r.headers.get("content-type")))
r = LOC.post("/api/audio/graph/rendre", json={"graphe": GT, "nom": "route"})
j = r.json() if r.status_code == 200 else {}
check("H5 POST /rendre : fichier rangé, relation atelier, mère = la première source, gratuit",
      r.status_code == 200 and j.get("filename", "").startswith("atelier_route") and j.get("relation") == "atelier"
      and j.get("parent") == "musique.mp3" and j.get("usd") == 0.0, r.text[:300])
from app.services import library_index as LI  # noqa: E402
import asyncio  # noqa: E402
carte = _attendre(LI.carte())
check("H6 lignée Bibliothèque notée par la route", (carte.get(j.get("filename", "")) or {}).get("parent_filename") == "musique.mp3"
      and (carte.get(j.get("filename", "")) or {}).get("relation") == "atelier",
      carte.get(j.get("filename", "")))
NET = TestClient(app, client=("192.168.1.20", 50000))
avant = sorted(p.name for p in AUDIO.iterdir())
rn = NET.post("/api/audio/graph/rendre", json={"graphe": GT, "nom": "reseau"})
check("H7 écriture refusée hors de la boucle locale (jeton 401 ou garde 403), rien d'écrit",
      rn.status_code in (401, 403) and sorted(p.name for p in AUDIO.iterdir()) == avant, rn.status_code)

# ── [I] messages traduits ─────────────────────────────────────────────────────────────────────────────────────────
print("[I] messages d'erreur traduits")
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONUTF8="1"))
check("I1 i18n_l10_erreurs --check vert", rc.returncode == 0, (rc.stdout + rc.stderr)[-400:])

print(f"\n{ok} PASS / {fail} FAIL")


def test_audio_graph():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
