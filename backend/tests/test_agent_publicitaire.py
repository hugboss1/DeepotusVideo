# -*- coding: utf-8 -*-
"""t439 (lot M6 « Méthodes », 08/11/2026) — l'agent métier PUBLICITAIRE et le contrôle des formats par réseau.

[F] formats     une vidéo verticale 1080x1920 de 15 s avec son : conforme TikTok, Reels, Shorts, Stories, pas YouTube
                ni le fil Meta (ratio) ; un carré 720x720 : fil Meta et Shorts ; un 16:9 de 3 s : refusé partout
                (durée YouTube < 6 s, ratio ailleurs) ; une vidéo sans son : conseil, pas d'écart ; un petit vertical
                540x960 : « petit côté » ; refus : image, réseau inconnu ; date du relevé et avertissement rendus ;
[B] boîtes      le Publicitaire voit ses formats, les gestes du Monteur (coupes, titres, chaîne), méthodes et briques ;
                rien de Campagnes ; registre sain ;
[A] agent       disponible, catégorie « marketing », rôle (accroche, carton de fin, un fichier par réseau), ses
                méthodes ; un tour scripté appelle verifier_format_pub ; dépense « marketing ».
Run : & $PY tests/test_agent_publicitaire.py   (depuis backend/)
"""
import asyncio
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzpub439_")
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


def video(nom, taille, duree, son=True):
    args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x334455:s={taille}:r=24:d={duree}"]
    if son:
        args += ["-f", "lavfi", "-i", f"sine=frequency=330:duration={duree}", "-shortest", "-c:a", "aac"]
    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(pathlib.Path(_tmp, "medias", nom))]
    subprocess.run(args, check=True, capture_output=True, timeout=120)


def main():
    R = pathlib.Path(_tmp)
    (R / "medias").mkdir()
    video("vertical.mp4", "1080x1920", 15)
    video("carre.mp4", "720x720", 20)
    video("paysage.mp4", "1280x720", 3)
    video("muet.mp4", "1080x1920", 10, son=False)
    video("petit.mp4", "540x960", 10)
    from PIL import Image
    Image.new("RGB", (8, 8)).save(R / "medias" / "i.png")
    from app.services import formats_pub as FP

    print("[F] formats")
    v = FP.verifier("medias/vertical.mp4")
    ok_ = {k for k, x in v["reseaux"].items() if x["ok"]}
    check("F1 vertical 1080x1920, 15 s, son : TikTok, Reels, Shorts, Stories ; pas YouTube ni fil Meta",
          ok_ == {"tiktok", "reels", "shorts", "stories"}
          and any("ratio" in e for e in v["reseaux"]["youtube"]["ecarts"]), {k: x["ecarts"] for k, x in v["reseaux"].items()})
    v = FP.verifier("medias/carre.mp4", ["meta_feed", "shorts", "tiktok"])
    check("F2 carré 720x720 : fil Meta et Shorts oui, TikTok non (ratio)", v["reseaux"]["meta_feed"]["ok"]
          and v["reseaux"]["shorts"]["ok"] and not v["reseaux"]["tiktok"]["ok"] and list(v["reseaux"]) ==
          ["meta_feed", "shorts", "tiktok"], v["reseaux"])
    v = FP.verifier("medias/paysage.mp4")
    check("F3 16:9 de 3 s : refusé partout ; YouTube pour la durée", not any(x["ok"] for x in v["reseaux"].values())
          and any("durée" in e for e in v["reseaux"]["youtube"]["ecarts"]), v["reseaux"]["youtube"])
    v = FP.verifier("medias/muet.mp4", ["tiktok"])
    check("F4 sans son : conforme, avec un conseil", v["reseaux"]["tiktok"]["ok"] and v["reseaux"]["tiktok"]["conseils"]
          and v["infos"]["son"] is False, v)
    v = FP.verifier("medias/petit.mp4", ["reels"])
    check("F5 540x960 : écart « petit côté »", not v["reseaux"]["reels"]["ok"]
          and any("petit côté" in e for e in v["reseaux"]["reels"]["ecarts"]), v)
    check("F6 refus : image, réseau inconnu", refus(FP.verifier, "medias/i.png")
          and refus(FP.verifier, "medias/vertical.mp4", ["myspace"]))
    check("F7 relevé daté et avertissement", v["releve"] == "2026-11-08" and "vérifie les règles" in v["avertissement"])

    print("\n[B] boîtes")
    from app.services import agent_boites as B
    from app.services import agent_metier as AM
    o = set(B.outils_pour("publicitaire"))
    attendu = {"verifier_format_pub", "temps_forts_musique", "caler_coupes", "poser_titre", "chaines_lire",
               "deviser_etape_chaine", "methodes_lire", "modeles_lister", "modele_fiche", "recommander_modele", "verifier_prompt", "mesurer_sortie", "comparer_sorties", "ancres_lire",
               "ancre_verifier", "registre_lire", "arbitrer_sorties"}
    check("B1 formats + gestes du Monteur + méthodes + briques — exactement", o == attendu, sorted(o ^ attendu))
    check("B2 rien de Campagnes ; registre sain", not o & set(B.outils_pour("campagnes")) and B.verifier() == [],
          B.verifier())

    print("\n[A] agent")
    from app.config import settings
    from app.services import moteurs_texte as MT
    s = AM.systeme("publicitaire")
    ag = {x["id"]: x for x in AM.agents()}
    check("A1 disponible, catégorie « marketing », rôle et méthodes (game-ua-ads, the-showroom), pas celles des autres",
          ag["publicitaire"]["disponible"] and AM.ACTIFS["publicitaire"]["categorie"] == "marketing"
          and "# Le Publicitaire" in s and "game-ua-ads" in s and "the-showroom" in s and "edit-one-thing" not in s)
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    SCRIPT = [{"blocs": [{"type": "tool_use", "id": "t1", "name": "verifier_format_pub",
                          "input": {"chemin": "medias/vertical.mp4", "reseaux": ["tiktok", "youtube"]}}],
               "arret": "tool_use", "in_tok": 300, "out_tok": 30},
              {"blocs": [{"type": "text", "text": "Bon pour TikTok, il faut une version 16:9 pour YouTube."}],
               "arret": "end_turn", "in_tok": 500, "out_tok": 20}]
    MT.converser = lambda *a, **k: SCRIPT.pop(0)
    conv = AM.creer("publicitaire", "", "game-ua-ads")
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(AM.message("publicitaire", conv["id"], "Ma pub passe-t-elle ?", max_usd=1))
    loop.close()
    check("A2 verifier_format_pub exécuté (1/2 réseaux), réponse rangée", r["outils"][0]["ok"]
          and "1/2" in r["outils"][0]["resume"] and "TikTok" in r["texte"], r)
    dep = sqlite3.connect(str(R / "t.db")).execute("SELECT DISTINCT categorie FROM depenses").fetchall()
    check("A3 dépenses dans la catégorie « marketing »", dep == [("marketing",)], dep)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
