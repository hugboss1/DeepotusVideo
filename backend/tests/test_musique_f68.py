"""t486 (F6.8, lot « Fiches modèle ») — musique : tempo, instrumental par le négatif, prix relevés.

Schémas et prix fal relus le 09/11/2026 :
- aucun modèle de musique n'a de champ tempo : `bpm` (40-220) s'écrit dans le prompt, sous une forme (« 92 BPM »),
  et remplace un tempo déjà écrit (celui d'une ambiance) ;
- Lyria 3 et Lyria 3.5 n'ont pas d'interrupteur mais un `negative_prompt` : l'instrumental DEMANDÉ y passe ;
- prix : Lyria 3 0,04 $, MiniMax 2.6 0,15 $, Lyria 3.5 0,10 $, MiniMax Music 3 0,002 $/s, Stable Audio 3 0,0376 $.

Run: <python embarqué> backend/tests/test_musique_f68.py
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8")

from app.services import music_service as MS, pricing as P  # noqa: E402

ok = fail = 0


def check(nom, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {nom}")
    else:
        fail += 1
        print(f"  FAIL  {nom} {detail}")


def refus(fn):
    try:
        fn()
    except MS.MusicError as e:
        return e
    return None


print("\n[1] tempo")
check("1.1 sans bpm : prompt inchangé", MS.build_prompt("synthwave nocturne") == "synthwave nocturne")
check("1.2 bpm ajouté en fin, une forme", MS.build_prompt("synthwave nocturne", bpm=92) == "synthwave nocturne, 92 BPM")
p = MS.build_prompt("", "cinematic", bpm=120)
check("1.3 le bpm remplace le tempo de l'ambiance (un seul tempo)", p.endswith(", 120 BPM") and p.count("BPM") == 1
      and "70 BPM" not in p, p)
p = MS.build_prompt("lofi, 80 bpm, rain", bpm=72)
check("1.4 un tempo écrit à la main est remplacé aussi (casse ignorée)", p == "lofi, rain, 72 BPM", p)
check("1.5 bpm en chaîne accepté", MS.build_prompt("jazz", bpm="100") == "jazz, 100 BPM")
for b in (39, 221, "vite"):
    e = refus(lambda: MS.build_prompt("jazz", bpm=b))
    check(f"1.6 bpm {b!r} refusé (400)", e is not None and e.status == 400, e)
check("1.7 bornes 40 et 220 acceptées", MS.build_prompt("x", bpm=40).endswith("40 BPM")
      and MS.build_prompt("x", bpm=220).endswith("220 BPM"))
prep = MS.preparer({"model": "stable-audio-25", "prompt": "nappe", "bpm": 60})
check("1.8 preparer passe le bpm au prompt envoyé", prep["prompt"] == "nappe, 60 BPM" and prep["args"]["prompt"]
      == "nappe, 60 BPM", prep["args"])
msg = json.loads((HERE.parent / "app/i18n/messages.json").read_text(encoding="utf-8")).get("musique.bpm_bornes")
check("1.9 refus traduit FR/EN", msg and "{lo}" in msg["fr"] and "{lo}" in msg["en"], msg)

print("\n[2] instrumental par le négatif (Lyria)")
for mid in ("lyria3", "lyria-3.5"):
    a = MS.preparer({"model": mid, "prompt": "épique", "instrumental": True})["args"]
    check(f"2.1 {mid} instrumental demandé : négatif posé", a.get("negative_prompt") == MS.INSTRUMENTAL_NEGATIF, a)
    a = MS.preparer({"model": mid, "prompt": "épique", "instrumental": True, "negative_prompt": "drums"})["args"]
    check(f"2.2 {mid} : le négatif de l'utilisateur est gardé, après", a.get("negative_prompt")
          == MS.INSTRUMENTAL_NEGATIF + ", drums", a)
    a = MS.preparer({"model": mid, "prompt": "épique", "instrumental": False})["args"]
    check(f"2.3 {mid} chanté : aucun négatif", "negative_prompt" not in a, a)
    a = MS.preparer({"model": mid, "prompt": "épique"})["args"]
    check(f"2.4 {mid} sans avis (appelant d'API) : rien ajouté", "negative_prompt" not in a, a)
    a = MS.preparer({"model": mid, "prompt": "épique", "instrumental": True})["args"]
    check(f"2.5 {mid} : la description ne reçoit jamais « instrumental »", "instrumental" not in a["prompt"].lower(), a)
cat = {m["id"]: m for m in MS.catalog()["models"]}
check("2.6 l'écran voit l'interrupteur sur Lyria 3 et 3.5", cat["lyria3"]["instrumental"] and cat["lyria-3.5"]["instrumental"])
a = MS.preparer({"model": "elevenlabs-music-2.5", "prompt": "x", "instrumental": True})["args"]
check("2.7 ElevenLabs garde son interrupteur, sans négatif", a.get("force_instrumental") is True
      and "negative_prompt" not in a, a)
n = MS.preparer({"model": "lyria3", "prompt": "x", "duration_s": 60, "seed": 3})["notes"]
check("2.8 Lyria 3 : la note dit toujours sa durée (30 s)", any("30" in str(x) for x in n), [str(x) for x in n])

print("\n[3] prix relevés le 09/11/2026")
attendus = {"lyria3": (0.04, "gen"), "minimax-music-26": (0.15, "gen"), "lyria-3.5": (0.10, "gen"),
            "minimax-music-3": (0.002, "s"), "stable-audio-3": (0.0376, "gen")}
for mid, (usd, unite) in attendus.items():
    m = MS.MUSIC_MODELS[mid]
    check(f"3.1 {mid} : {usd} $ / {unite}", m["usd"] == usd and m.get("usd_unit", "gen") == unite, (m["usd"], m.get("usd_unit")))
check("3.2 MiniMax Music 3 : chiffré sur la durée envoyée (60 s = 0,12 $)",
      abs(P.estimate({"kind": "music", "model": "minimax-music-3", "duration_s": 60})["total_usd"] - 0.12) < 1e-9)
check("3.3 aucun modèle de musique à 0 $", all(m["usd"] > 0 for m in MS.MUSIC_MODELS.values()))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
