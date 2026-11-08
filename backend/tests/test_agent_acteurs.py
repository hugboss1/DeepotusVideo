# -*- coding: utf-8 -*-
"""t438 (lot M5 « Méthodes », 08/11/2026) — l'agent métier DIRECTEUR D'ACTEURS et ses contrôles locaux.

[R] réplique    identique (ponctuation, casse, accents ignorés) -> exact ; un mot manquant, un ajouté, un remplacé
                trouvés à leur place ; WER = erreurs / mots attendus ; verdicts proche / ecart ; texte attendu vide refusé ;
[V] voix        une « voix » synthétique (3 phrases de tonalité séparées par 0,6 s et 1,0 s de silence) : 3 passages aux
                bons instants, parole ≈ 3,4 s, pause max ≈ 1 s, débit = mots / minute de parole ; refus : image ;
[B] boîtes      méthodes, briques et « acteurs » — exactement ; rien d'écriture ; registre sain ;
[A] agent       disponible, catégorie « son », rôle (une voix, un portrait, un texte ; réplique dite contre voulue),
                ses méthodes ; un tour scripté appelle controler_replique ; dépense « son ».
Run : & $PY tests/test_agent_acteurs.py   (depuis backend/)
"""
import asyncio
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzacteurs438_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[_k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def refus(fn, *a):
    try:
        fn(*a)
    except ValueError:
        return True
    return False


def main():
    from app.services import acteurs as AC

    print("[R] réplique")
    r = AC.controler_replique("Bonjour, je suis Mira !", "bonjour je suis mira")
    check("R1 identique (ponctuation, casse) : exact, WER 0", r["verdict"] == "exact" and r["wer"] == 0, r)
    check("R2 accents ignorés", AC.controler_replique("Élise était là", "elise etait la")["wer"] == 0)
    r = AC.controler_replique("le chat dort sur le tapis rouge", "le chat dort sur tapis bleu ce soir")
    check("R3 manquant « le », remplacé rouge→bleu, ajoutés « ce soir » ; WER = 4/7",
          r["manquants"] == ["le"] and r["remplaces"] == [["rouge", "bleu"]] and r["ajoutes"] == ["ce", "soir"]
          and r["wer"] == round(4 / 7, 4) and r["verdict"] == "ecart", r)
    r = AC.controler_replique(" ".join(["mot"] * 20), " ".join(["mot"] * 19))
    check("R4 un mot de moins sur 20 : WER 5 %, proche", r["wer"] == 0.05 and r["verdict"] == "proche", r)
    check("R5 texte attendu vide : refus", refus(AC.controler_replique, " ,. ", "x"))

    print("\n[V] voix")
    R = pathlib.Path(_tmp)
    M = R / "medias"
    M.mkdir()
    phrase = "sine=frequency=220:duration={d}"
    morceaux = [("p1", 1.2), ("s1", 0.6), ("p2", 1.0), ("s2", 1.0), ("p3", 1.2)]
    fichiers = []
    for nom, d in morceaux:
        f = M / f"{nom}.wav"
        src = phrase.format(d=d) if nom.startswith("p") else f"anullsrc=r=44100:cl=mono:d={d}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-ar", "44100", "-ac", "1",
                        "-t", str(d), str(f)], check=True, capture_output=True)
        fichiers.append(f)
    liste = M / "l.txt"
    liste.write_text("".join(f"file '{f.as_posix()}'\n" for f in fichiers), "utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(liste), str(M / "voix.wav")],
                   check=True, capture_output=True)
    v = AC.segments_voix("medias/voix.wav", "un deux trois quatre cinq six sept huit neuf dix onze douze treize")
    seg = v["segments"]
    check("V1 trois passages parlés aux bons instants (±0,15 s)", len(seg) == 3
          and all(abs(a - b) < 0.15 for a, b in zip([x for s in seg for x in s], [0, 1.2, 1.8, 2.8, 3.8, 5.0])), seg)
    check("V2 parole ≈ 3,4 s, pause max ≈ 1 s", abs(v["parole_s"] - 3.4) < 0.3 and abs(v["pause_max_s"] - 1.0) < 0.15, v)
    check("V3 débit = 13 mots / minute de parole", v["mots_par_minute"] and
          abs(v["mots_par_minute"] - 13 / (v["parole_s"] / 60)) < 0.2, v)
    from PIL import Image
    Image.new("RGB", (8, 8)).save(M / "i.png")
    check("V4 une image : refus", refus(AC.segments_voix, "medias/i.png"))

    print("\n[B] boîtes")
    from app.services import agent_boites as B
    from app.services import agent_outils as ao
    from app.services import agent_metier as AM
    attendu = {"methodes_lire", "mesurer_sortie", "comparer_sorties", "ancres_lire", "ancre_verifier", "registre_lire",
               "controler_replique", "segments_voix", "arbitrer_sorties"}
    o = set(B.outils_pour("directeur_acteurs"))
    check("B1 méthodes, briques, acteurs — exactement ; que de la lecture", o == attendu
          and all(ao.OUTILS[x]["nature"] == "lecture" for x in o), sorted(o ^ attendu))
    check("B2 registre sain", B.verifier() == [], B.verifier())

    print("\n[A] agent")
    from app.config import settings
    from app.services import moteurs_texte as MT
    ag = {x["id"]: x for x in AM.agents()}
    s = AM.systeme("directeur_acteurs")
    check("A1 disponible, catégorie « son » ; rôle et méthodes (one-more-take, babel-tavern), pas celles des autres",
          ag["directeur_acteurs"]["disponible"] and AM.ACTIFS["directeur_acteurs"]["categorie"] == "son"
          and "# Le Directeur d'acteurs" in s and "one-more-take" in s and "babel-tavern" in s and "auto-edit" not in s)
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    SCRIPT = [{"blocs": [{"type": "tool_use", "id": "t1", "name": "controler_replique",
                          "input": {"attendu": "Je reviendrai demain", "obtenu": "je reviendrai"}}],
               "arret": "tool_use", "in_tok": 300, "out_tok": 30},
              {"blocs": [{"type": "text", "text": "Il manque « demain »."}], "arret": "end_turn", "in_tok": 500,
               "out_tok": 20}]
    MT.converser = lambda *a, **k: SCRIPT.pop(0)
    conv = AM.creer("directeur_acteurs", "", "one-more-take")
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(AM.message("directeur_acteurs", conv["id"], "La prise est-elle juste ?", max_usd=1))
    loop.close()
    check("A2 controler_replique exécuté (1 manquant), réponse rangée", r["outils"][0]["ok"]
          and "1 manquant" in r["outils"][0]["resume"] and "demain" in r["texte"], r)
    dep = sqlite3.connect(str(R / "t.db")).execute("SELECT DISTINCT categorie FROM depenses").fetchall()
    check("A3 dépenses dans la catégorie « son »", dep == [("son",)], dep)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
