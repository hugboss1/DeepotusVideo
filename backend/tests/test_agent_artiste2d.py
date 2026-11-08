# -*- coding: utf-8 -*-
"""t440 (lot M7 « Méthodes », 08/11/2026) — l'agent métier ARTISTE 2D DE JEU et ses contrôles (boîte « sprites_qc »).

[P] pixel art   un sprite 16x16 de 4 couleurs agrandi x4 (voisin le plus proche) : bloc 4, grille 16x16, 4 couleurs,
                transparence, grille nette, palette tenue ; un dégradé lisse : bloc 1, trop de couleurs, conseils ;
                un bord adouci : pixels semi-transparents signalés ; refus : vidéo ;
[S] planche     4x2 cases d'un même sujet : stable ; une case qui saute de 3 px logiques : instable (sol) ; une case vide
                comptée ; découpe impossible et planche vide refusées ;
[B] boîtes      contrôles sprites + méthodes + briques — exactement, lecture ; registre sain ;
[A] agent       disponible, catégorie « sprites », rôle (grille exacte par un outil, jamais miroiter un objet tenu),
                ses méthodes ; un tour scripté appelle verifier_planche ; dépense « sprites ».
Run : & $PY tests/test_agent_artiste2d.py   (depuis backend/)
"""
import asyncio
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzart2d440_")
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


def sujet(decalage_y=0):
    """Un petit personnage 16x16 de 4 couleurs sur fond transparent."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([5, 2 + decalage_y, 10, 7 + decalage_y], fill=(240, 200, 160, 255))
    d.rectangle([4, 8 + decalage_y, 11, 12 + decalage_y], fill=(40, 90, 200, 255))
    d.point([(6, 4 + decalage_y), (9, 4 + decalage_y)], fill=(20, 20, 20, 255))
    d.rectangle([5, 13 + decalage_y, 10, 14 + decalage_y], fill=(90, 50, 20, 255))
    return im


def main():
    from PIL import Image
    R = pathlib.Path(_tmp)
    M = R / "medias"
    M.mkdir()
    s = sujet()
    s.resize((64, 64), Image.NEAREST).save(M / "sprite.png")
    deg = Image.new("RGBA", (64, 64))
    deg.putdata([(x * 4, y * 4, 128, 255) for y in range(64) for x in range(64)])
    deg.save(M / "degrade.png")
    doux = s.resize((64, 64), Image.NEAREST)
    doux.putpixel((20, 20), (240, 200, 160, 128))
    doux.save(M / "doux.png")
    planche = Image.new("RGBA", (16 * 4, 16 * 2), (0, 0, 0, 0))
    for k in range(8):
        planche.paste(sujet(), ((k % 4) * 16, (k // 4) * 16))
    planche.resize((256, 128), Image.NEAREST).save(M / "planche.png")
    saute = Image.new("RGBA", (16 * 4, 16 * 2), (0, 0, 0, 0))
    for k in range(7):
        saute.paste(sujet(-3 if k == 2 else 0), ((k % 4) * 16, (k // 4) * 16))
    saute.resize((256, 128), Image.NEAREST).save(M / "saute.png")
    Image.new("RGBA", (64, 32), (0, 0, 0, 0)).save(M / "vide.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=1:duration=1",
                    str(M / "v.mp4")], check=True, capture_output=True)
    from app.services import sprites_qc as SQ

    print("[P] pixel art")
    a = SQ.analyser_pixel_art("medias/sprite.png")
    check("P1 sprite x4 : bloc 4, grille 16x16, 4 couleurs, transparence, grille nette, palette tenue, aucun conseil",
          a["bloc_px"] == 4 and a["grille_logique"] == [16, 16] and a["couleurs"] == 4 and a["transparence"]
          and a["grille_nette"] and a["palette_tenue"] and not a["conseils"], a)
    a = SQ.analyser_pixel_art("medias/degrade.png")
    check("P2 dégradé lisse : bloc 1, trop de couleurs, deux conseils", a["bloc_px"] == 1 and not a["grille_nette"]
          and not a["palette_tenue"] and len(a["conseils"]) == 2, a)
    a = SQ.analyser_pixel_art("medias/doux.png")
    check("P3 un pixel semi-transparent : signalé", a["pixels_semi_transparents"] == 1
          and any("semi-transparents" in c for c in a["conseils"]), a)
    check("P4 une vidéo : refus", refus(SQ.analyser_pixel_art, "medias/v.mp4"))

    print("\n[S] planche")
    p = SQ.verifier_planche("medias/planche.png", 4, 2)
    b1 = Image.new("RGBA", (16 * 2, 16), (0, 0, 0, 0))
    b1.paste(sujet(), (0, 0)); b1.paste(sujet(-1), (16, 0))
    b1.resize((128, 64), Image.NEAREST).save(M / "rebond.png")
    check("P5b un rebond d'1 px logique (marche) reste stable : tolérance de 2 px logiques",
          SQ.verifier_planche("medias/rebond.png", 2, 1)["verdict"] == "stable")
    check("P5 planche régulière 4x2 : stable, case 64x64, bloc 4, aucune case vide",
          p["verdict"] == "stable" and p["case"] == [64, 64] and p["bloc_px"] == 4 and p["vides"] == 0, p["stats"])
    p = SQ.verifier_planche("medias/saute.png", 4, 2)
    check("P6 une case qui saute de 3 px logiques (12 px) et une case vide : instable par le sol, vide comptée",
          p["verdict"] == "instable" and "sol" in p["problemes"] and p["vides"] == 1, (p["problemes"], p["stats"]))
    check("P7 refus : découpe impossible, 0 colonne, planche vide",
          refus(SQ.verifier_planche, "medias/planche.png", 3, 2) and refus(SQ.verifier_planche, "medias/planche.png", 0, 2)
          and refus(SQ.verifier_planche, "medias/vide.png", 2, 1))

    print("\n[B] boîtes")
    from app.services import agent_boites as B
    from app.services import agent_outils as ao
    from app.services import agent_metier as AM
    o = set(B.outils_pour("artiste_2d"))
    attendu = {"analyser_pixel_art", "verifier_planche", "methodes_lire", "mesurer_sortie", "comparer_sorties",
               "ancres_lire", "ancre_verifier", "registre_lire"}
    check("B1 contrôles sprites + méthodes + briques — exactement, lecture", o == attendu
          and all(ao.OUTILS[x]["nature"] == "lecture" for x in o), sorted(o ^ attendu))
    check("B2 registre sain", B.verifier() == [], B.verifier())

    print("\n[A] agent")
    from app.config import settings
    from app.services import moteurs_texte as MT
    s_ = AM.systeme("artiste_2d")
    ag = {x["id"]: x for x in AM.agents()}
    check("A1 disponible, « sprites », rôle (grille exacte par un outil, jamais miroiter), ses méthodes",
          ag["artiste_2d"]["disponible"] and AM.ACTIFS["artiste_2d"]["categorie"] == "sprites"
          and "grille EXACTE" in s_ and "miroités" in s_ and "iso-cycles" in s_ and "wang-tiles" in s_
          and "edit-one-thing" not in s_)
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    SCRIPT = [{"blocs": [{"type": "tool_use", "id": "t1", "name": "verifier_planche",
                          "input": {"chemin": "medias/saute.png", "colonnes": 4, "lignes": 2}}],
               "arret": "tool_use", "in_tok": 300, "out_tok": 30},
              {"blocs": [{"type": "text", "text": "La case 3 saute : recale-la."}], "arret": "end_turn",
               "in_tok": 500, "out_tok": 20}]
    MT.converser = lambda *a, **k: SCRIPT.pop(0)
    conv = AM.creer("artiste_2d", "", "iso-cycles")
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(AM.message("artiste_2d", conv["id"], "Ma planche est-elle propre ?", max_usd=1))
    loop.close()
    check("A2 verifier_planche exécuté (instable), réponse rangée", r["outils"][0]["ok"]
          and "instable" in r["outils"][0]["resume"] and "case 3" in r["texte"], r)
    dep = sqlite3.connect(str(R / "t.db")).execute("SELECT DISTINCT categorie FROM depenses").fetchall()
    check("A3 dépenses dans la catégorie « sprites »", dep == [("sprites",)], dep)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
