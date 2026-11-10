# -*- coding: utf-8 -*-
"""t437 (lot M4 « Méthodes », 08/11/2026) — les agents métier RETOUCHEUR et DÉCLINAISONS PRODUIT, et la carte des
différences (boîte « retouche »), sur des images synthétiques dans un dossier de données temporaire.

[D] carte       identique -> 0 % et pas de zone ; un carré changé en bas à droite -> part ≈ 1/16, zone exacte, le quart
                bas-droit seul ; tailles différentes ramenées ; la carte PNG rangée sous briques/differences ; refus :
                vidéo, hors données ;
[B] boîtes      chacun voit methodes_lire, les briques et carte_differences, rien de Campagnes, du Monteur ni du
                Réalisateur ; mcp ne voit pas carte_differences ; registre sain ;
[S] invites     rôles (une chose à changer + ce qui reste ; master en ancre, étiquette posée par l'app), leurs méthodes ;
[A] boucle      disponibles, catégorie « studio » ; un tour scripté appelle carte_differences ; dépense « studio ».
Run : & $PY tests/test_agent_retouche.py   (depuis backend/)
"""
import asyncio
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzretouche437_")
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
    from PIL import Image, ImageDraw
    R = pathlib.Path(_tmp)
    M = R / "medias"
    M.mkdir()
    base = Image.new("RGB", (400, 400), (90, 110, 130))
    ImageDraw.Draw(base).ellipse([60, 60, 180, 180], fill=(200, 200, 60))
    base.save(M / "avant.png")
    base.copy().save(M / "pareil.png")
    ap = base.copy()
    ImageDraw.Draw(ap).rectangle([300, 300, 399, 399], fill=(240, 20, 20))
    ap.save(M / "apres.png")
    ap.resize((800, 800)).save(M / "apres_grand.png")
    dehors = pathlib.Path(tempfile.mkdtemp(prefix="dzdehors_")) / "x.png"
    base.save(dehors)

    from app.services import briques as BR

    print("[D] carte des différences")
    c = BR.carte_differences("medias/avant.png", "medias/pareil.png")
    check("D1 identiques : 0 %, pas de zone", c["part_changee"] == 0 and c["boite"] is None, c)
    c = BR.carte_differences("medias/avant.png", "medias/apres.png")
    q = c["par_quart"]
    check("D2 un carré 100x100 en bas à droite : part 1/16, zone exacte, le quart bas-droit seul",
          abs(c["part_changee"] - 0.0625) < 0.002 and c["boite"] == [300, 300, 400, 400]
          and q["bas_droit"] > 0.2 and q["haut_gauche"] == q["haut_droit"] == q["bas_gauche"] == 0, c)
    check("D3 la carte PNG est rangée sous briques/differences, à la taille de l'avant",
          c["carte"].startswith("briques/differences/") and Image.open(R / c["carte"]).size == (400, 400))
    c2 = BR.carte_differences("medias/avant.png", "medias/apres_grand.png")
    check("D4 tailles différentes : l'après est ramené, même verdict", abs(c2["part_changee"] - 0.0625) < 0.01, c2)
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=1:duration=1",
                    str(M / "v.mp4")], check=True, capture_output=True)
    check("D5 refus : une vidéo, un fichier hors données",
          refus(BR.carte_differences, "medias/avant.png", "medias/v.mp4")
          and refus(BR.carte_differences, "medias/avant.png", str(dehors)))

    print("\n[B] boîtes")
    from app.services import agent_boites as B
    from app.services import agent_outils as ao
    from app.services import agent_metier as AM
    attendu = {"methodes_lire", "modeles_lister", "modele_fiche", "recommander_modele", "verifier_prompt", "mesurer_sortie", "comparer_sorties", "ancres_lire", "ancre_verifier", "registre_lire",
               "carte_differences", "arbitrer_sorties"}
    for a in ("retoucheur", "declinaisons"):
        check(f"B1 {a} : méthodes, briques, carte des différences — exactement", set(B.outils_pour(a)) == attendu,
              sorted(set(B.outils_pour(a)) ^ attendu))
    check("B2 mcp ne voit pas carte_differences (elle écrit une image) ; registre sain",
          "carte_differences" not in B.outils_pour("mcp") and ao.OUTILS["carte_differences"]["nature"] == "ecriture"
          and B.verifier() == [], B.verifier())

    print("\n[S] invites")
    s1, s2 = AM.systeme("retoucheur"), AM.systeme("declinaisons")
    check("S1 Retoucheur : une chose à changer + ce qui reste, ses méthodes (edit-one-thing), pas celles des autres",
          "# Le Retoucheur" in s1 and "la seule chose à changer" in s1 and "edit-one-thing" in s1
          and "give-each-picture-a-job" in s1 and "auto-edit" not in s1 and "same-product-every-variation" not in s1)
    check("S2 Déclinaisons : master en ancre, étiquette posée par l'app, ses méthodes",
          "Déclinaisons produit" in s2 and "ancre" in s2 and "étiquette" in s2
          and "same-product-every-variation" in s2 and "edit-one-thing" not in s2)

    print("\n[A] boucle")
    from app.config import settings
    from app.services import moteurs_texte as MT
    ag = {x["id"]: x for x in AM.agents()}
    check("A1 disponibles, catégorie « studio »", ag["retoucheur"]["disponible"] and ag["declinaisons"]["disponible"]
          and AM.ACTIFS["retoucheur"]["categorie"] == AM.ACTIFS["declinaisons"]["categorie"] == "studio")
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    SCRIPT = [{"blocs": [{"type": "tool_use", "id": "t1", "name": "carte_differences",
                          "input": {"avant": "medias/avant.png", "apres": "medias/apres.png"}}],
               "arret": "tool_use", "in_tok": 400, "out_tok": 40},
              {"blocs": [{"type": "text", "text": "Seul le coin bas droit a changé."}], "arret": "end_turn",
               "in_tok": 700, "out_tok": 30}]
    MT.converser = lambda *a, **k: SCRIPT.pop(0)
    conv = AM.creer("retoucheur", "", "edit-one-thing")
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(AM.message("retoucheur", conv["id"], "Ai-je changé autre chose ?", max_usd=1))
    loop.close()
    check("A2 carte_differences exécutée (6,2 %), réponse rangée", r["outils"][0]["nom"] == "carte_differences"
          and r["outils"][0]["ok"] and "6.2 %" in r["outils"][0]["resume"] and "bas droit" in r["texte"], r)
    dep = sqlite3.connect(str(R / "t.db")).execute("SELECT DISTINCT categorie FROM depenses").fetchall()
    check("A3 dépenses dans la catégorie « studio »", dep == [("studio",)], dep)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
