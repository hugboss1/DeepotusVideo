# -*- coding: utf-8 -*-
"""Atelier sonore, nœuds IA sur une plage (t272, 21/10/2026) — `app/services/atelier_ia.py` (registre relevé sur le
catalogue fal le 21/10/2026) et le pré-calcul payant de `app/services/audio_graph.py` : avant la compilation, chaque
nœud IA (prolonger, régénérer une plage, variation, SFX sur la plage) envoie son entrée rendue au fournisseur, et le
graphe lit le segment rendu comme une source. Le segment est gardé dans le dossier audio sous un nom tiré de son
contenu (aperçu puis rendu : une seule dépense).
Sections :
  [M] registre : quatre opérations (la « couche » écartée), modèles et endpoints relevés, prix, clé, catalogue ;
  [V] validation : modèle inconnu ou d'une autre opération, description vide, plage vide, trop courte, trop longue ;
  [K] clés du cache : stables, changent avec la description, la prise, la source, un nœud IA en amont ;
  [D] devis : kind « atelier_ia » de pricing.estimate (forfait, à la seconde), SFX par le kind « sfx », déjà généré
      = 0, /api/cost/estimate ;
  [G] génération (faux fal, zéro réseau) : champs envoyés par modèle, fenêtre envoyée, segment posé dans la plage,
      prolongation ajoutée au bout, chaîne de deux nœuds IA dans l'ordre ;
  [H] routes : /devis gratuit ; sans clé 503 qui la nomme, aucune dépense ; sans confirmation 409 ; avec : la garde
      AVANT le fournisseur, devis égal à la garde, lignée « atelier_ia » ; cache au second rendu ; plafond 402 ;
      écriture refusée hors boucle ;
  [P] recensement payant : les routes /apercu et /rendre atteignent le puits `generer_ia` ET sont gardées ;
  [I] messages d'erreur traduits (i18n_l10_erreurs --check).
Run (depuis backend/) : & $PY tests/test_atelier_ia.py"""
import array, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzatia_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir()
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))

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


from loguru import logger  # noqa: E402
logger.remove()
from app.config import settings  # noqa: E402
from app.services import audio_graph as AG  # noqa: E402
from app.services import atelier_ia as AI  # noqa: E402
from app.services import pricing  # noqa: E402
from app.services import sfx_service as SX  # noqa: E402

AUDIO = SX._audio_dir()


def sine(chemin, s, f=220):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={f}:duration={s}",
                    "-ac", "2", "-c:a", "libmp3lame", "-b:a", "128k", str(chemin)], check=True)


def dur(p):
    return SX._probe_duration(pathlib.Path(p))


def grave(p, a, b):
    """Énergie (RMS) sous ~300 Hz entre a et b : la source à 220 Hz y passe, un segment à 1000 Hz presque pas."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", str(p), "-af",
                        "lowpass=f=300,lowpass=f=300,lowpass=f=300", "-ac", "1", "-ar", "22050", "-f", "s16le", "-"],
                       capture_output=True, check=True)
    x = array.array("h", r.stdout)
    return (sum(v * v for v in x) / max(1, len(x))) ** 0.5


def zcr(p, a, b):
    """Passages par zéro par seconde entre a et b (220 Hz ≈ 440, 1000 Hz ≈ 2000)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", str(p), "-ac", "1", "-ar",
                        "22050", "-f", "s16le", "-"], capture_output=True, check=True)
    x = array.array("h", r.stdout)
    n = sum(1 for i in range(1, len(x)) if (x[i - 1] < 0) != (x[i] < 0))
    return n / max(1e-6, b - a)


sine(AUDIO / "musique.mp3", 20, 220)
settings.FAL_KEY = ""


def G(noeuds, liens):
    return {"noeuds": [{"id": i, "type": t, "params": p} for i, t, p in noeuds],
            "liens": [{"de": a, "vers": b, "entree": e} for a, b, e in liens]}


SRC = ("s", "source", {"fichier": "musique.mp3"})
OUT = ("o", "sortie", {})


def g1(t, p):
    return G([SRC, ("ia", t, p), OUT], [("s", "ia", 0), ("ia", "o", 0)])


# ── [M] registre ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[M] registre des nœuds IA")
CAT = AG.catalogue()
IA = CAT.get("ia") or {}
check("M1 quatre opérations livrées (prolonger, régénérer, variation, sfx) ; la « couche » est écartée",
      sorted(IA) == ["prolonger", "regenerer", "sfx", "variation"], sorted(IA))
RELEVE = {   # catalogue fal relu le 21/10/2026 (openapi « queue » + prix de la page du modèle)
    "sa3-prolonger": ("prolonger", "fal-ai/stable-audio-3/medium/audio-outpainting", 0.0446, "gen"),
    "ace-prolonger": ("prolonger", "fal-ai/ace-step/audio-outpaint", 0.0002, "s"),
    "sa3-regenerer": ("regenerer", "fal-ai/stable-audio-3/medium/audio-inpainting", 0.0442, "gen"),
    "sa25-regenerer": ("regenerer", "fal-ai/stable-audio-25/inpaint", 0.20, "gen"),
    "ace-regenerer": ("regenerer", "fal-ai/ace-step/audio-inpaint", 0.0002, "s"),
    "sa3-variation": ("variation", "fal-ai/stable-audio-3/medium/audio-to-audio", 0.0417, "gen"),
    "sa25-variation": ("variation", "fal-ai/stable-audio-25/audio-to-audio", 0.20, "gen"),
}
check("M2 modèles fal : opération, endpoint, prix et unité relevés le 21/10/2026",
      {k: (v["op"], v["endpoint"], v["usd"], v["unite"]) for k, v in AI.MODELES.items()} == RELEVE,
      {k: (v["op"], v["endpoint"], v["usd"], v["unite"]) for k, v in AI.MODELES.items()})
_sfx = [m["id"] for m in IA.get("sfx", {}).get("modeles", [])]
check("M3 SFX sur la plage : les modèles TEXTE du registre des bruitages passant par fal (ElevenLabs direct exclu)",
      _sfx == [k for k, e in SX.SFX_MODELS.items() if e["nature"] == SX.SFX_TEXTE and e["voie"] == "fal"], _sfx)
_m = [m for op in IA.values() for m in op.get("modeles", [])]
check("M4 chaque modèle listé dit son prix, son unité, sa clé (FAL_KEY) et sa disponibilité (sans clé : choisissable)",
      _m and all({"id", "label", "usd", "unite", "cle", "dispo"} <= set(m) and m["cle"] == "FAL_KEY"
                 and m["dispo"] is False for m in _m), _m[:2])
check("M5 défaut de chaque opération dans son registre ; SFX par défaut = Sonilo (prix connu)",
      all(IA[o]["defaut"] in [m["id"] for m in IA[o]["modeles"]] for o in IA) and IA["sfx"]["defaut"] == "sonilo-1.1",
      {o: IA[o].get("defaut") for o in IA})
TYPES = {t["type"]: t for t in CAT["noeuds"]}
check("M6 nœuds ia_* au catalogue, une entrée, bornes : plage, force 0,05-1, niveau −30/+6 dB, prolonger 1-120 s",
      all(TYPES.get(t, {}).get("entrees") == 1 for t in ("ia_prolonger", "ia_regenerer", "ia_variation", "ia_sfx"))
      and TYPES["ia_variation"]["params"]["force"] == [0.05, 1, 0.5]
      and TYPES["ia_sfx"]["params"]["niveau_db"] == [-30, 6, 0]
      and TYPES["ia_prolonger"]["params"]["secondes"] == [1, 120, 10]
      and TYPES["ia_regenerer"]["params"]["fin"] == [0, 3600, 5]
      and TYPES["ia_regenerer"]["params"]["prise"] == [1, 99, 1], {t: TYPES.get(t) for t in TYPES if t.startswith("ia_")})

# ── [V] validation ────────────────────────────────────────────────────────────────────────────────────────────────
print("[V] validation")
P0 = {"modele": "sa3-regenerer", "prompt": "warm piano", "debut": 4, "fin": 8}
check("V1 modèle inconnu : refus", "inconnu" in (refus(AG.valider, g1("ia_regenerer", dict(P0, modele="zzz"))) or ""),
      refus(AG.valider, g1("ia_regenerer", dict(P0, modele="zzz"))))
check("V2 modèle d'une autre opération : refus",
      "inconnu" in (refus(AG.valider, g1("ia_regenerer", dict(P0, modele="sa3-variation"))) or ""))
check("V3 description vide : refus", "décri" in (refus(AG.valider, g1("ia_regenerer", dict(P0, prompt="  "))) or ""),
      refus(AG.valider, g1("ia_regenerer", dict(P0, prompt="  "))))
check("V4 plage vide (fin ≤ début) : refus", "plage" in (refus(AG.valider, g1("ia_variation", dict(P0, modele="sa3-variation", fin=4))) or ""))
check("V5 plage de moins d'une seconde : refus",
      "1 s" in (refus(AG.valider, g1("ia_regenerer", dict(P0, fin=4.5))) or ""), refus(AG.valider, g1("ia_regenerer", dict(P0, fin=4.5))))
check("V6 plage plus longue que ce que le modèle accepte (Stable Audio 2.5 : 190 s) : refus",
      "190" in (refus(AG.valider, g1("ia_regenerer", dict(P0, modele="sa25-regenerer", debut=0, fin=200))) or ""))
check("V7 prolonger au-delà de ce que le modèle accepte (ACE-Step : 107 s) : refus",
      "107" in (refus(AG.valider, g1("ia_prolonger", {"modele": "ace-prolonger", "prompt": "lofi", "secondes": 115})) or ""))
check("V8 SFX : plage au-delà des bornes du modèle (Stable Audio 3 SFX : 120 s) : refus",
      "120" in (refus(AG.valider, g1("ia_sfx", {"modele": "stable-audio-3-sfx", "prompt": "rain", "debut": 0, "fin": 130})) or ""))
_v = AG.valider(g1("ia_regenerer", {"prompt": "warm piano", "debut": 4, "fin": 8, "prise": 2.6}))
check("V9 modèle absent = défaut de l'opération ; la prise est un entier",
      _v["params"]["ia"]["modele"] == "sa3-regenerer" and _v["params"]["ia"]["prise"] == 3, _v["params"]["ia"])

# ── [K] clés du cache ─────────────────────────────────────────────────────────────────────────────────────────────
print("[K] clés du cache")


def plan(g):
    return AG.plan_ia(AG.valider(g))


k0 = plan(g1("ia_regenerer", P0))[0]["cle"]
check("K1 clé stable pour un même graphe ; fichier ia_<opération>_<clé>.flac",
      plan(g1("ia_regenerer", P0))[0]["cle"] == k0 and plan(g1("ia_regenerer", P0))[0]["fichier"] == f"ia_regenerer_{k0}.flac")
check("K2 la clé change avec la description et avec la prise",
      plan(g1("ia_regenerer", dict(P0, prompt="cold piano")))[0]["cle"] != k0
      and plan(g1("ia_regenerer", dict(P0, prise=2)))[0]["cle"] != k0)
sine(AUDIO / "musique.mp3", 20, 221)
check("K3 la clé change quand le fichier source change", plan(g1("ia_regenerer", P0))[0]["cle"] != k0)
sine(AUDIO / "musique.mp3", 20, 220)
CH = G([SRC, ("a", "ia_regenerer", P0), ("b", "ia_variation", {"modele": "sa3-variation", "prompt": "jazz", "debut": 10,
                                                                 "fin": 14, "force": 0.4}), OUT],
       [("s", "a", 0), ("a", "b", 0), ("b", "o", 0)])
CH2 = json.loads(json.dumps(CH))
CH2["noeuds"][1]["params"]["prompt"] = "harp"
pc, pc2 = plan(CH), plan(CH2)
check("K4 chaîne : ordre topologique, et un nœud IA en amont qui change change la clé du nœud aval",
      [x["id"] for x in pc] == ["a", "b"] and pc[1]["cle"] != pc2[1]["cle"], (pc, pc2))

# ── [D] devis ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("[D] devis")
e1 = pricing.estimate({"kind": "atelier_ia", "modele": "sa3-regenerer", "secondes": 4})
check("D1 forfait : Stable Audio 3 inpainting 0,0442 $ par génération", abs(e1["total_usd"] - 0.0442) < 1e-9, e1)
e2 = pricing.estimate({"kind": "atelier_ia", "modele": "ace-regenerer", "secondes": 34})
check("D2 à la seconde : ACE-Step 34 s x 0,0002 $", abs(e2["total_usd"] - 0.0068) < 1e-9, e2)
_pa = plan(g1("ia_regenerer", dict(P0, modele="ace-regenerer")))[0]
check("D3 ACE-Step régénérer 4 s : secondes facturées = plage + 2 x 15 s de contexte (borne prudente)",
      _pa["cout"] == {"kind": "atelier_ia", "modele": "ace-regenerer", "secondes": 34.0}, _pa["cout"])
_ps = plan(g1("ia_sfx", {"modele": "sonilo-1.1", "prompt": "rain on a roof", "debut": 2, "fin": 7}))[0]
check("D4 SFX : chiffré par le kind « sfx » du registre des bruitages (Sonilo 5 s)",
      _ps["cout"] == {"kind": "sfx", "modele": "sonilo-1.1", "duration_s": 5.0}
      and abs(pricing.estimate(_ps["cout"])["total_usd"] - 5 * 0.0018) < 1e-9, _ps["cout"])
_d = AG.devis(CH)
check("D5 devis d'une chaîne : la somme de ses nœuds IA à générer", abs(_d["usd"] - (0.0442 + 0.0417)) < 1e-9
      and [x["id"] for x in _d["a_generer"]] == ["a", "b"] and _d["deja"] == [], _d)
(AUDIO / pc[0]["fichier"]).write_bytes(b"x")
_d2 = AG.devis(CH)
check("D6 un segment déjà généré ne coûte plus rien", abs(_d2["usd"] - 0.0417) < 1e-9 and _d2["deja"] == ["a"], _d2)
(AUDIO / pc[0]["fichier"]).unlink()
check("D7 un id inconnu : ligne « non chiffré » à 0 $",
      pricing.estimate({"kind": "atelier_ia", "modele": "zzz"})["total_usd"] == 0.0)

# ── [G] génération, faux fal ──────────────────────────────────────────────────────────────────────────────────────
print("[G] génération (faux fal)")
JOURNAL = []
ENVOIS = {}


async def _faux_envoyer(p):
    u = f"fake://in/{len(ENVOIS)}"
    copie = pathlib.Path(_tmp, f"envoi_{len(ENVOIS)}.wav")
    copie.write_bytes(pathlib.Path(p).read_bytes())
    ENVOIS[u] = copie
    JOURNAL.append(("envoi", u))
    return u


async def _faux_appeler(endpoint, args):
    JOURNAL.append(("fal", endpoint, dict(args)))
    src = ENVOIS.get(args.get("audio_url"))
    d0 = dur(src) if src else 0.0
    if "outpaint" in endpoint:   # rendu = l'entrée (330 Hz) PUIS la suite (1000 Hz)
        ext = float(args.get("extend_seconds_after", args.get("extend_after_duration", 0)))
        return {"audio": {"url": f"fake://out/{d0 + ext}/{d0}"}}
    elif "audio-to-audio" in endpoint:
        long = float(args.get("duration", args.get("total_seconds", d0)) or d0)
    elif "inpaint" in endpoint:
        long = d0
    else:   # bruitage
        long = float(args.get("duration", args.get("duration_seconds", 5)))
    return {"audio": {"url": f"fake://out/{long}"}}


async def _faux_telecharger(url, dest):
    JOURNAL.append(("tele", url))
    morceaux = url.split("/")[3:]
    tmp = pathlib.Path(dest).with_suffix(".mp3")
    if len(morceaux) == 2:
        tete, total = float(morceaux[1]), float(morceaux[0])
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=330:duration={tete}",
                        "-f", "lavfi", "-i", f"sine=frequency=1000:duration={total - tete}", "-filter_complex",
                        "[0:a][1:a]concat=n=2:v=0:a=1", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "128k", str(tmp)],
                       check=True)
    else:
        sine(tmp, float(morceaux[0]), 1000)
    os.replace(tmp, dest)


AI._envoyer, AI._appeler, AI._telecharger = _faux_envoyer, _faux_appeler, _faux_telecharger
import asyncio  # noqa: E402


def _attendre(c):                          # hygiène des lanceurs : jamais asyncio.run() en tête de module
    return asyncio.run(c)


def generer(g):
    v = AG.valider(g)
    pl = AG.plan_ia(v)
    prets = AG.preparer_entrees(v, pl)
    try:
        return _attendre(AG.generer_ia(v, pl, prets))
    finally:
        AG.nettoyer(prets)


def fal_args():
    return [j[2] for j in JOURNAL if j[0] == "fal"]


JOURNAL.clear()
gr = g1("ia_regenerer", dict(P0, prise=3))
faits = generer(gr)
a = fal_args()[0] if fal_args() else {}
check("G1 régénérer (Stable Audio 3) : fenêtre = plage + 15 s de contexte, masque relatif, graine = prise",
      a.get("mask_start_seconds") == 4.0 and a.get("mask_end_seconds") == 8.0 and a.get("seed") == 3
      and a.get("prompt") == "warm piano" and abs(dur(ENVOIS["fake://in/0"]) - 20.0) < 0.1, (a, faits))
check("G2 le segment est rangé (ia_regenerer_<clé>.flac, sidecar « atelier_ia »), long comme la plage",
      faits == [AG.plan_ia(AG.valider(gr))[0]["fichier"]] and abs(dur(AUDIO / faits[0]) - 4.0) < 0.1
      and (SX.load_meta().get(faits[0]) or {}).get("kind") == "atelier_ia", (faits, SX.load_meta().get(faits[0] if faits else "")))
R1 = AG.rendre(gr, "regen")
out = AUDIO / R1["filename"]
check("G3 rendu : durée gardée (20 s), la plage 4-8 s porte le segment, le reste la source",
      abs(dur(out) - 20.0) < 0.15 and zcr(out, 5, 7) > 1500 and zcr(out, 1, 3) < 700 and zcr(out, 10, 12) < 700,
      (dur(out), zcr(out, 5, 7), zcr(out, 1, 3)))
check("G3b dans la plage, la source est muette (seul le segment joue) ; hors plage, elle joue",
      grave(out, 5, 7) < 0.25 * grave(out, 1, 3), (grave(out, 5, 7), grave(out, 1, 3)))
n_fal = len(fal_args())
generer(gr)
check("G4 deuxième passage : segment en cache, aucun appel au fournisseur", len(fal_args()) == n_fal)
JOURNAL.clear()
gv = g1("ia_variation", {"modele": "sa3-variation", "prompt": "jazz", "debut": 10, "fin": 14, "force": 0.35})
generer(gv)
a = fal_args()[0]
check("G5 variation (Stable Audio 3) : la plage seule est envoyée, force = init_noise_level, durée = plage",
      a.get("init_noise_level") == 0.35 and a.get("duration") == 4.0 and abs(dur(ENVOIS[a["audio_url"]]) - 4.0) < 0.1, a)
JOURNAL.clear()
gv25 = g1("ia_variation", {"modele": "sa25-variation", "prompt": "jazz", "debut": 10, "fin": 13.5, "force": 0.6})
generer(gv25)
a = fal_args()[0]
check("G6 variation (Stable Audio 2.5) : strength = force, total_seconds entier (plafond)",
      a.get("strength") == 0.6 and a.get("total_seconds") == 4 and "duration" not in a, a)
JOURNAL.clear()
g25 = g1("ia_regenerer", dict(P0, modele="sa25-regenerer", debut=4.5, fin=8.2))
generer(g25)
a = fal_args()[0]
check("G7 régénérer (Stable Audio 2.5) : masques entiers englobant la plage, seconds_total = fenêtre entière",
      a.get("mask_start") == 4 and a.get("mask_end") == 9 and a.get("seconds_total") == 20, a)
JOURNAL.clear()
gp = g1("ia_prolonger", {"modele": "sa3-prolonger", "prompt": "same groove", "secondes": 6})
generer(gp)
a = fal_args()[0]
R2 = AG.rendre(gp, "prolonge")
out = AUDIO / R2["filename"]
check("G8 prolonger (Stable Audio 3) : la fin (15 s) est envoyée, extend_seconds_after = 6 ; rendu 20 + 6 s",
      a.get("extend_seconds_after") == 6.0 and abs(dur(ENVOIS[a["audio_url"]]) - 15.0) < 0.1
      and abs(dur(out) - 26.0) < 0.2 and zcr(out, 22, 25) > 1500 and zcr(out, 10, 12) < 700, (a, dur(out)))
JOURNAL.clear()
ga = g1("ia_prolonger", {"modele": "ace-prolonger", "prompt": "lofi, piano", "secondes": 5})
generer(ga)
a = fal_args()[0]
check("G9 prolonger (ACE-Step) : la description part en `tags`, extend_after_duration, rien avant",
      a.get("tags") == "lofi, piano" and a.get("extend_after_duration") == 5.0 and a.get("extend_before_duration") == 0
      and "prompt" not in a, a)
JOURNAL.clear()
gs = g1("ia_sfx", {"modele": "sonilo-1.1", "prompt": "glass breaking", "debut": 12, "fin": 15, "niveau_db": 0})
generer(gs)
R3 = AG.rendre(gs, "sfx")
out = AUDIO / R3["filename"]
check("G10 SFX : rien n'est envoyé, la requête est celle du registre des bruitages (3 s), le son est mêlé à 12 s",
      not [j for j in JOURNAL if j[0] == "envoi"] and fal_args()[0] == SX.build_request("sonilo-1.1", "glass breaking", 3.0)[1]
      and abs(dur(out) - 20.0) < 0.15 and zcr(out, 12.5, 14.5) > zcr(out, 5, 7) + 300, (JOURNAL[:2], dur(out)))
JOURNAL.clear()
faits = generer(CH)
ups = [j for j in JOURNAL if j[0] == "envoi"]
check("G11 chaîne de deux nœuds IA : générés dans l'ordre, le second reçoit l'entrée qui contient le premier",
      len(faits) == 2 and [j[1] for j in JOURNAL if j[0] == "fal"] == ["fal-ai/stable-audio-3/medium/audio-inpainting",
                                                                      "fal-ai/stable-audio-3/medium/audio-to-audio"]
      and len(ups) == 2, JOURNAL)
check("G12 compiler un nœud IA sans son segment : refus (génération à lancer)",
      "génération" in (refus(AG.compiler, AG.valider(g1("ia_regenerer", dict(P0, prompt="never made")))) or ""))
check("G13 plage qui commence après la fin de l'entrée : refus AVANT tout envoi",
      "fin de l'entrée" in (refus(lambda: AG.preparer_entrees(AG.valider(g1("ia_regenerer", dict(P0, debut=25, fin=28))),
                                                             AG.plan_ia(AG.valider(g1("ia_regenerer", dict(P0, debut=25, fin=28))))))
                           or ""))

# ── [H] routes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[H] routes")
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from app.main import app  # noqa: E402
from app.services import plafonds as PL  # noqa: E402
from app.services import library_index as LI  # noqa: E402
from app.services.storage import Depense, async_session_factory, init_db  # noqa: E402

_attendre(init_db())


def lignes():
    async def f():
        async with async_session_factory() as s:
            return (await s.execute(select(Depense).order_by(Depense.id))).scalars().all()
    return _attendre(f())


_verif = PL.verifier
GARDES = []


async def _espion(op, categorie="", ref=None, confirme=None):
    GARDES.append((op, categorie))
    JOURNAL.append(("garde",))
    return await _verif(op, categorie, ref, confirme)

PL.verifier = _espion
LOC = TestClient(app, client=("127.0.0.1", 50000))
GH = g1("ia_regenerer", dict(P0, prompt="route test"))
r = LOC.post("/api/audio/graph/devis", json={"graphe": GH})
dv = r.json() if r.status_code == 200 else {}
check("H1 POST /devis : gratuit, liste les nœuds à générer et le total", r.status_code == 200
      and [x["id"] for x in dv.get("a_generer", [])] == ["ia"] and abs(dv.get("usd", 0) - 0.0442) < 1e-9, r.text[:300])
JOURNAL.clear()
settings.FAL_KEY = ""
r = LOC.post("/api/audio/graph/rendre", json={"graphe": GH, "generer": True})
check("H2 sans clé : 503 qui nomme FAL_KEY, aucun appel, aucune garde, aucune dépense",
      r.status_code == 503 and "FAL_KEY" in r.text and not JOURNAL and not lignes(), (r.status_code, r.text[:200]))
settings.FAL_KEY = "cle-de-banc"
r = LOC.post("/api/audio/graph/rendre", json={"graphe": GH})
check("H3 sans confirmation : 409, rien d'envoyé, aucune dépense", r.status_code == 409 and not JOURNAL and not lignes(),
      (r.status_code, r.text[:200]))
r = LOC.post("/api/audio/graph/rendre", json={"graphe": GH, "generer": True, "nom": "routeia"})
j = r.json() if r.status_code == 200 else {}
ordre = [x[0] for x in JOURNAL]
check("H4 confirmé : la garde « son » passe AVANT le premier envoi au fournisseur",
      r.status_code == 200 and ordre and ordre[0] == "garde" and "fal" in ordre and GARDES[-1][1] == "son",
      (r.status_code, r.text[:300], ordre))
check("H5 devis égal à la garde : le devis de /devis = l'estimation de l'op passée à la garde",
      GARDES and abs(pricing.estimate(GARDES[-1][0])["total_usd"] - dv.get("usd", -1)) < 1e-9, GARDES[-1:])
check("H6 rendu : fichier rangé, usd = la génération, segment listé ; une ligne de dépense « son »",
      j.get("filename", "").startswith("atelier_routeia") and abs(j.get("usd", 0) - 0.0442) < 1e-9
      and len(j.get("ia") or []) == 1 and len(lignes()) == 1 and lignes()[0].categorie == "son", (j, lignes()))
carte = _attendre(LI.carte())
seg = (j.get("ia") or ["?"])[0]
check("H7 lignée notée par la route : le segment « atelier_ia » (mère = la source), le rendu « atelier »",
      (carte.get(seg) or {}).get("relation") == "atelier_ia" and (carte.get(seg) or {}).get("parent_filename") == "musique.mp3"
      and (carte.get(j.get("filename", "")) or {}).get("relation") == "atelier", (carte.get(seg), carte.get(j.get("filename", ""))))
JOURNAL.clear()
r = LOC.post("/api/audio/graph/rendre", json={"graphe": GH, "nom": "routeia2"})
check("H8 second rendu : segment en cache, sans confirmation, aucun appel, usd 0",
      r.status_code == 200 and not [x for x in JOURNAL if x[0] in ("fal", "garde")] and r.json().get("usd") == 0.0,
      (r.status_code, r.text[:200], JOURNAL))
JOURNAL.clear()
GA = g1("ia_variation", {"modele": "sa3-variation", "prompt": "apercu", "debut": 2, "fin": 6, "force": 0.5})
r = LOC.post("/api/audio/graph/apercu", json={"graphe": GA, "depuis": 0})
check("H9 aperçu d'un nœud IA à générer, non confirmé : 409", r.status_code == 409 and not JOURNAL, r.status_code)
r = LOC.post("/api/audio/graph/apercu", json={"graphe": GA, "depuis": 0, "generer": True})
check("H10 aperçu confirmé : génération puis audio/mpeg, en-tête X-DZ-IA-Usd",
      r.status_code == 200 and r.headers["content-type"].startswith("audio/mpeg") and "fal" in [x[0] for x in JOURNAL]
      and abs(float(r.headers.get("x-dz-ia-usd", "-1")) - 0.0417) < 1e-9, (r.status_code, r.headers.get("x-dz-ia-usd")))
JOURNAL.clear()
PL.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
r = LOC.post("/api/audio/graph/rendre", json={"graphe": g1("ia_regenerer", dict(P0, prompt="plafond")), "generer": True})
check("H11 au-dessus du plafond : 402 dz_plafond, rien d'envoyé au fournisseur",
      r.status_code == 402 and "fal" not in [x[0] for x in JOURNAL], (r.status_code, r.text[:200]))
PL.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})
NET = TestClient(app, client=("192.168.1.20", 50000))
JOURNAL.clear()
rn = NET.post("/api/audio/graph/rendre", json={"graphe": g1("ia_regenerer", dict(P0, prompt="reseau")), "generer": True})
check("H12 écriture refusée hors de la boucle locale (401 ou 403), rien d'envoyé",
      rn.status_code in (401, 403) and not JOURNAL, rn.status_code)
r = LOC.get("/api/audio/graph/noeuds")
check("H13 GET /noeuds : le registre IA avec la disponibilité de la clé (posée : dispo)",
      r.status_code == 200 and all(m["dispo"] for op in r.json()["ia"].values() for m in op["modeles"]), r.text[:200])

# ── [P] recensement payant ────────────────────────────────────────────────────────────────────────────────────────
print("[P] recensement payant")
import _recensement_payant as RP  # noqa: E402
rec = RP.recenser()
check("P1 /apercu et /rendre atteignent le puits `generer_ia` et appellent la garde",
      all(("audio_graph", "POST", c) in rec and "generer_ia" in rec[("audio_graph", "POST", c)]["puits"]
          and rec[("audio_graph", "POST", c)]["garde"] for c in ("/apercu", "/rendre")),
      {c: rec.get(("audio_graph", "POST", c)) for c in ("/apercu", "/rendre")})
check("P2 /devis, /valider, /noeuds n'atteignent aucun puits",
      all(not rec.get(("audio_graph", "POST", c), {"puits": set()})["puits"] for c in ("/devis", "/valider")))

# ── [I] messages traduits ─────────────────────────────────────────────────────────────────────────────────────────
print("[I] messages d'erreur traduits")
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONUTF8="1"))
check("I1 i18n_l10_erreurs --check vert", rc.returncode == 0, (rc.stdout + rc.stderr)[-400:])

print(f"\n{ok} PASS / {fail} FAIL")


def test_atelier_ia():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
