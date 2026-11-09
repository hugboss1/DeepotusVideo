# -*- coding: utf-8 -*-
"""t436 (lot M3 « Méthodes », 08/11/2026) — l'agent métier RÉALISATEUR, sur la boucle commune (t435a).

[B] boîtes      le Réalisateur voit Chapitres (bible, plans, revue, passes, modèles vidéo), Plateau (previs), Blender
                (lecture), methodes_lire et les briques — et RIEN d'écriture ni de carte, rien de Campagnes ni du
                Monteur ; mcp ne gagne ni plateau ni blender ; registre sain ;
[S] invite      rôle (docs/agent/metiers/realisateur.md), règle « jamais de génération payante », ses méthodes
                (previs-to-picture, the-last-lantern…) et pas celles du Monteur ;
[A] boucle      disponible, catégorie « chapitres » ; un tour scripté appelle modeles_video puis répond : outil exécuté
                (boîte bornée), ligne de dépense « chapitres », conversation rangée ; un outil du Monteur est refusé ;
[H] route       POST /api/agents-metier/realisateur/conversations -> 200 ; le message sans confirmation -> 409.
Run : & $PY tests/test_agent_realisateur.py   (depuis backend/)
"""
import asyncio
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzreal436_")
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


def main():
    from app.services import agent_boites as B
    from app.services import agent_outils as ao
    from app.services import agent_metier as AM

    print("[B] boîtes")
    re_ = set(B.outils_pour("realisateur"))
    attendu = {"lire_revue_plan", "lire_bible", "lire_plans", "lire_passes_plan", "modeles_video", "plateau_previs",
               "blender_scene", "blender_regarder", "blender_retour", "methodes_lire", "modeles_lister", "modele_fiche", "mesurer_sortie",
               "comparer_sorties", "ancres_lire", "ancre_verifier", "registre_lire", "arbitrer_sorties"}
    check("B1 le Réalisateur : Chapitres, Plateau, Blender, méthodes, briques — exactement", re_ == attendu,
          sorted(re_ ^ attendu))
    check("B2 que de la lecture : aucune écriture ni carte", all(ao.OUTILS[o]["nature"] == "lecture" for o in re_))
    check("B3 rien de Campagnes ni du Monteur ; mcp ne gagne ni plateau ni blender",
          not re_ & set(B.outils_pour("campagnes")) and "poser_titre" not in re_ and "deviser_etape_chaine" not in re_
          and "plateau_previs" not in B.outils_pour("mcp") and "blender_scene" not in B.outils_pour("mcp"))
    check("B4 registre sain", B.verifier() == [], B.verifier())

    print("\n[S] invite")
    s = AM.systeme("realisateur", "fr")
    check("S1 rôle, règle de dépense, ses méthodes, pas celles du Monteur",
          "# Le Réalisateur" in s and "JAMAIS une génération payante" in s and "previs-to-picture" in s
          and "the-last-lantern" in s and "auto-edit" not in s)
    check("S2 en anglais : la consigne de langue suit", "Answer in English." in AM.systeme("realisateur", "en"))

    print("\n[A] boucle")
    from app.config import settings
    from app.services import moteurs_texte as MT
    ag = {x["id"]: x for x in AM.agents()}
    check("A1 disponible ; catégorie « chapitres »", ag["realisateur"]["disponible"]
          and AM.ACTIFS["realisateur"]["categorie"] == "chapitres")
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    SCRIPT = [{"blocs": [{"type": "tool_use", "id": "t1", "name": "modeles_video", "input": {}},
                         {"type": "tool_use", "id": "t2", "name": "poser_titre",
                          "input": {"video": "x.mp4", "texte": "x", "debut": 0, "fin": 1}}],
               "arret": "tool_use", "in_tok": 500, "out_tok": 60},
              {"blocs": [{"type": "text", "text": "Seedance 2.5 convient pour ce plan."}], "arret": "end_turn",
               "in_tok": 900, "out_tok": 40}]
    MT.converser = lambda *a, **k: SCRIPT.pop(0)
    conv = AM.creer("realisateur", "", "previs-to-picture")
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(AM.message("realisateur", conv["id"], "Quel modèle pour ce plan ?", max_usd=1))
    loop.close()
    check("A2 modeles_video exécuté, poser_titre (Monteur) refusé hors boîte, réponse rangée",
          [o["nom"] for o in r["outils"]] == ["modeles_video", "poser_titre"] and r["outils"][0]["ok"]
          and not r["outils"][1]["ok"] and "hors de la boîte" in r["outils"][1]["resume"]
          and "Seedance" in r["texte"] and r["arret"] == "fin", r)
    dep = sqlite3.connect(str(pathlib.Path(_tmp, "t.db"))).execute("SELECT DISTINCT categorie FROM depenses").fetchall()
    check("A3 dépenses dans la catégorie « chapitres »", dep == [("chapitres",)], dep)

    print("\n[H] route")
    from fastapi.testclient import TestClient
    from app.main import app
    cl = TestClient(app)
    r = cl.post("/api/agents-metier/realisateur/conversations", json={"methode": "the-last-lantern"})
    cid = r.json().get("id", "")
    check("H1 création", r.status_code == 200 and cid.startswith("am_"), r.text[:200])
    r = cl.post(f"/api/agents-metier/realisateur/conversations/{cid}/message", json={"texte": "Découpe la scène"})
    check("H2 message sans confirmation : 409, devis joint", r.status_code == 409
          and (r.json().get("detail") or {}).get("usd", 0) > 0, r.text[:200])

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
