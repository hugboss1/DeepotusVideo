# -*- coding: utf-8 -*-
"""t442 (lot M9 « Méthodes », 08/11/2026) — l'ARBITRE (B6, outil commun) et l'agent métier ÉDITEUR ILLUSTRÉ.

[R] arbitre     trois sorties d'une même consigne (fidèle, dérivée, illisible) contre une référence : tableau COMPLET
                (rien d'écarté, l'illisible reste une ligne), rangé par note, la fidèle première ; à note égale le
                moins cher puis le plus rapide ; note pure (identité, vidéo, rien) ; refus : vide, doublon de modèle,
                modèle sans nom, trop de sorties ;
[T] texte       FR / EN / DE dans une boîte de 300 px sur 2 lignes en Inter 32 : le court tient, le long non ; la taille
                commune fait tout tenir (vérifiée) ; un mot plus long que la boîte est signalé ; refus : fonte
                inconnue, texte vide, bornes ;
[B] boîtes      l'Arbitre chez les neuf agents métier, pas chez mcp ni Campagnes ; l'Éditeur voit edition + arbitre +
                méthodes + briques — exactement, lecture ; registre sain ;
[A] agent       disponible, « cartes », rôle (mots composés par l'app, fiches de personnages), ses méthodes ; un tour
                scripté appelle ajuster_texte ; dépense « cartes ».
Run : & $PY tests/test_agent_editeur.py   (depuis backend/)
"""
import asyncio
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzediteur442_")
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


def refus(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


def main():
    from PIL import Image, ImageDraw
    R = pathlib.Path(_tmp)
    M = R / "medias"
    M.mkdir()
    ref = Image.new("RGB", (200, 200), (120, 120, 120))
    ImageDraw.Draw(ref).ellipse([40, 40, 160, 160], fill=(220, 40, 40))
    ref.save(M / "ref.png")
    ref.copy().save(M / "fidele.png")
    der = Image.new("RGB", (200, 200), (20, 30, 80))
    ImageDraw.Draw(der).rectangle([0, 0, 90, 200], fill=(30, 200, 60))
    der.save(M / "derive.png")
    ref.copy().save(M / "fidele2.png")
    from app.services import arbitre as AR

    print("[R] arbitre")
    t = AR.tableau([{"modele": "B", "chemin": "medias/derive.png", "usd": 0.01, "secondes": 3},
                    {"modele": "C", "chemin": "medias/absent.png", "usd": 0.02},
                    {"modele": "A", "chemin": "medias/fidele.png", "usd": 0.05, "secondes": 9}], "medias/ref.png")
    ls = t["lignes"]
    check("R1 tableau complet : trois lignes, rien d'écarté, la fidèle première, l'illisible dernière",
          t["n"] == 3 and t["complet"] and [x["modele"] for x in ls] == ["A", "B", "C"] and ls[0]["note"] == 100.0
          and ls[2]["verdict"] == "illisible" and ls[2]["note"] is None and "erreur" in ls[2] and t["meilleur"] == "A",
          [(x["modele"], x.get("note"), x.get("verdict")) for x in ls])
    t = AR.tableau([{"modele": "cher", "chemin": "medias/fidele.png", "usd": 0.5, "secondes": 1},
                    {"modele": "lent", "chemin": "medias/fidele2.png", "usd": 0.1, "secondes": 40},
                    {"modele": "vite", "chemin": "medias/fidele2.png", "usd": 0.1, "secondes": 5}], "medias/ref.png")
    check("R2 à note égale : le moins cher, puis le plus rapide", [x["modele"] for x in t["lignes"]] == ["vite", "lent", "cher"],
          [x["modele"] for x in t["lignes"]])
    check("R3 note pure : identité, vidéo, rien", AR.note({"identite": {"ecart_couleur": 0, "ecart_silhouette": 0}}) == 100.0
          and AR.note({"temporel": {"moyenne": 0.82}}) == 82.0 and AR.note({}) is None)
    check("R4 refus : vide, doublon de modèle, modèle sans nom, trop de sorties",
          refus(AR.tableau, []) and refus(AR.tableau, [{"modele": "A", "chemin": "x"}, {"modele": "A", "chemin": "y"}])
          and refus(AR.tableau, [{"chemin": "x"}])
          and refus(AR.tableau, [{"modele": str(i), "chemin": "x"} for i in range(25)]))

    print("\n[T] texte")
    from app.services import mise_en_texte as MT_
    textes = {"fr": "Le petit renard court dans la neige.", "en": "The little fox runs.",
              "de": "Der kleine Fuchs läuft durch den tiefen, kalten, glitzernden Winterschnee des Waldes."}
    r = MT_.ajuster(textes, "Inter", 32, 300, 2)
    check("T1 en tient, de ne tient pas (Inter 32, 300 px, 2 lignes)", r["langues"]["en"]["tient"]
          and not r["langues"]["de"]["tient"] and not r["tout_tient"], {k: v["n_lignes"] for k, v in r["langues"].items()})
    s = r["taille_commune"]
    r2 = MT_.ajuster(textes, "Inter", s, 300, 2) if s else {}
    check("T2 la taille commune (< 32) fait tout tenir, et la taille au-dessus non", s and s < 32 and r2["tout_tient"]
          and not MT_.ajuster(textes, "Inter", s + 1, 300, 2)["tout_tient"], s)
    r = MT_.ajuster({"fr": "Anticonstitutionnellement"}, "Inter", 40, 120, 3)
    check("T3 un mot plus long que la boîte : ne tient pas", not r["langues"]["fr"]["tient"])
    check("T4 refus : fonte inconnue, texte vide, bornes", refus(MT_.ajuster, {"fr": "x"}, "Comic Sans")
          and refus(MT_.ajuster, {"fr": "  "}) and refus(MT_.ajuster, {"fr": "x"}, "Inter", 2)
          and refus(MT_.ajuster, {}))

    print("\n[B] boîtes")
    from app.services import agent_boites as B
    from app.services import agent_outils as ao
    from app.services import agent_metier as AM
    metiers = [a["id"] for a in AM.agents()]
    check("B1 l'Arbitre chez les neuf agents métier, pas chez mcp ni Campagnes",
          len(metiers) == 9 and all("arbitrer_sorties" in B.outils_pour(a) for a in metiers)
          and "arbitrer_sorties" not in B.outils_pour("mcp") and "arbitrer_sorties" not in B.outils_pour("campagnes"))
    o = set(B.outils_pour("editeur_illustre"))
    attendu = {"ajuster_texte", "arbitrer_sorties", "methodes_lire", "modeles_lister", "modele_fiche", "recommander_modele", "verifier_prompt", "mesurer_sortie", "comparer_sorties",
               "ancres_lire", "ancre_verifier", "registre_lire"}
    check("B2 l'Éditeur : edition + arbitre + méthodes + briques — exactement, lecture ; registre sain",
          o == attendu and all(ao.OUTILS[x]["nature"] == "lecture" for x in o) and B.verifier() == [],
          (sorted(o ^ attendu), B.verifier()))

    print("\n[A] agent")
    from app.config import settings
    from app.services import moteurs_texte as MT
    s_ = AM.systeme("editeur_illustre")
    ag = {x["id"]: x for x in AM.agents()}
    check("A1 tous les agents métier disponibles ; l'Éditeur en « cartes », rôle et méthodes (the-picture-book)",
          all(v["disponible"] for v in ag.values()) and AM.ACTIFS["editeur_illustre"]["categorie"] == "cartes"
          and "composés par l'app" in s_ and "the-picture-book" in s_ and "inside-a-heartbeat" in s_
          and "nine-models-one-brief" not in s_)
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    SCRIPT = [{"blocs": [{"type": "tool_use", "id": "t1", "name": "ajuster_texte",
                          "input": {"textes": textes, "police": "Inter", "taille": 32, "largeur_px": 300,
                                    "lignes_max": 2}}], "arret": "tool_use", "in_tok": 300, "out_tok": 30},
              {"blocs": [{"type": "text", "text": "L'allemand ne tient pas : réduis la taille."}], "arret": "end_turn",
               "in_tok": 500, "out_tok": 20}]
    MT.converser = lambda *a, **k: SCRIPT.pop(0)
    conv = AM.creer("editeur_illustre", "", "the-picture-book")
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(AM.message("editeur_illustre", conv["id"], "Mes textes tiennent-ils ?", max_usd=1))
    loop.close()
    check("A2 ajuster_texte exécuté (de ne tient pas), réponse rangée", r["outils"][0]["ok"]
          and "ne tient pas : de" in r["outils"][0]["resume"] and "allemand" in r["texte"], r)
    dep = sqlite3.connect(str(R / "t.db")).execute("SELECT DISTINCT categorie FROM depenses").fetchall()
    check("A3 dépenses dans la catégorie « cartes »", dep == [("cartes",)], dep)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
