# -*- coding: utf-8 -*-
"""t435 (lot M2 « Méthodes », 08/11/2026) — la boucle commune des agents métier et le Monteur, sur des médias
SYNTHÉTIQUES dans un dossier de données temporaire ; le modèle est SCRIPTÉ (aucun appel réseau).

[T] temps forts    une musique synthétique à 120 BPM (un clic toutes les 0,5 s, un accent fort toutes les 2 s) :
                   tempo ≈ 120, temps espacés de 0,5 s, accents sur les multiples de 2 s ; pur : force, attaques, tempo ;
[K] caler          n_plans -> coupes sur les accents, espacées ; durées -> coupes tirées vers l'accent ou le temps ;
                   refus sans consigne ou musique vide ;
[P] titre          une copie titrée (mêmes taille et durée, l'image change dans la bande du titre, l'original intact) ;
                   refus : gabarit inconnu, fin avant début, pas une vidéo ;
[B] boîtes         le Monteur voit ses trois gestes + methodes_lire + les briques, rien de Campagnes ; mcp ne voit pas
                   poser_titre ; registre sain ;
[A] boucle         agents() (Monteur disponible, les autres non) ; invite = rôle + règles + ses méthodes ; devis ;
                   message : un outil appelé puis une réponse, deux étapes au registre, deux lignes de dépense
                   « montage », conversation rangée ; accord trop bas -> arrêté avant tout appel ; occupé ; sans clé ;
                   agent inactif refusé ; outil hors boîte refusé au modèle ;
[H] routes         404 agent ou conversation inconnus, 409 sans confirme_cout (devis joint, aucun appel), 200, lecture.
Run : & $PY tests/test_agent_metier.py   (depuis backend/)
"""
import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzmetier435_")
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


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True, timeout=120)


def refus(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


def main():
    if not shutil.which("ffmpeg"):
        print("SKIP: ffmpeg introuvable")
        return 0
    R = pathlib.Path(_tmp)
    M = R / "medias"
    M.mkdir()
    clic = ("if(lt(mod(t,0.5),0.012),(0.25+0.7*lt(mod(t,2),0.012))*sin(2*PI*1200*t),0)")
    ff("-f", "lavfi", "-i", f"aevalsrc=exprs='{clic}':s=22050:d=12", str(M / "musique.wav"))
    ff("-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono", "-t", "3", str(M / "silence.wav"))
    ff("-f", "lavfi", "-i", "color=c=0x223344:s=320x240:r=24:d=3", "-f", "lavfi", "-i",
       f"aevalsrc=exprs='{clic}':s=22050:d=3", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
       str(M / "clip.mp4"))

    from app.services import musique_temps as MU
    from app.services import monteur as MO

    print("[T] temps forts")
    a = MO.temps_forts("medias/musique.wav")
    check("T1 tempo ≈ 120 BPM", a["bpm"] and abs(a["bpm"] - 120) <= 4, a["bpm"])
    ecarts = [round(b - x, 2) for x, b in zip(a["temps_s"], a["temps_s"][1:])]
    check("T2 temps espacés de ≈ 0,5 s", ecarts and all(abs(e - 0.5) < 0.05 for e in ecarts), ecarts[:6])
    acc = [x["t"] for x in a["accents"]]
    check("T3 accents sur les multiples de 2 s (à 60 ms près), au moins 5",
          len(acc) >= 5 and all(min(abs(t - 2 * k) for k in range(7)) < 0.06 for t in acc), acc)
    check("T4 attaques ≈ une par clic (24 sur 12 s, ±3)", abs(len(a["attaques"]) - 24) <= 3, len(a["attaques"]))
    check("T5 pur : force d'attaque nulle sur le silence, aucune attaque",
          not MU.attaques(MU.force_attaque(MU.decoder(M / "silence.wav"))))
    check("T6 pur : trop court -> pas de tempo", MU.tempo([0.0] * 20) == (None, 0, 0))
    check("T7 une image : refus", refus(MO.temps_forts, "medias/../medias/rien.png") and refus(MO.temps_forts, "x.png"))

    print("\n[K] caler")
    c = MO.caler_coupes("medias/musique.wav", n_plans=4)
    bords = [p["debut"] for p in c["plans"][1:]]
    check("K1 n_plans=4 : 4 plans, 3 coupes sur des accents (multiples de 2 s), contigus jusqu'à la fin",
          len(c["plans"]) == 4 and c["sur_accent"] == 3 and all(min(abs(t - 2 * k) for k in range(7)) < 0.06 for t in bords)
          and all(c["plans"][i]["fin"] == c["plans"][i + 1]["debut"] for i in range(3))
          and abs(c["plans"][-1]["fin"] - 12) < 0.1, c["plans"])
    c = MO.caler_coupes("medias/musique.wav", durees=[1.9, 2.3, 3.0])
    ds = [p["fin"] for p in c["plans"][:-1]]
    check("K2 durées : 1,9 -> 2 (accent), puis 2+2,3=4,3 -> 4 (accent)",
          len(ds) == 2 and abs(ds[0] - 2) < 0.06 and abs(ds[1] - 4) < 0.06 and c["plans"][0]["cale"] == "accent", c["plans"])
    plan = MU.caler({"duree_s": 10, "accents": [], "temps_s": [1.0, 1.5, 2.0]}, durees=[1.4, 1.0])
    check("K3 sans accent proche : tirée vers le temps", plan[0]["fin"] == 1.5 and plan[0]["cale"] == "temps", plan)
    plan = MU.caler({"duree_s": 10, "accents": [], "temps_s": []}, durees=[3.3, 1.0])
    check("K4 ni accent ni temps : laissée « libre »", plan[0]["fin"] == 3.3 and plan[0]["cale"] == "libre", plan)
    check("K5 refus : sans consigne, musique vide, durées non numériques",
          refus(MU.caler, {"duree_s": 10}) and refus(MU.caler, {"duree_s": 0}, n_plans=3)
          and refus(MO.caler_coupes, "medias/musique.wav", durees=["a"]))

    print("\n[P] titre")
    from app.services import briques as BR
    from app.services import revue_plan as RV
    avant = (M / "clip.mp4").read_bytes()
    t = MO.poser_titre("medias/clip.mp4", "BONJOUR", 0.5, 2.5, "plein_cadre")
    i = t["infos"]
    im0 = RV.image_a(M / "clip.mp4", 0.5)
    im1 = RV.image_a(BR.confiner(t["chemin"]), 0.5)
    diff = sum(abs(a1 - b1) for a1, b1 in zip(im0.convert("L").getdata(), im1.convert("L").getdata())) / (320 * 240)
    check("P1 copie titrée : même taille, ≈ même durée, rangée sous briques/monteur, l'image a changé, original intact",
          i["largeur"] == 320 and i["hauteur"] == 240 and abs(i["secondes"] - 3) < 0.2
          and t["chemin"].startswith("briques/monteur/") and diff > 2 and (M / "clip.mp4").read_bytes() == avant, (i, diff))
    check("P2 aucun .ass laissé à côté", not list((R / "briques" / "monteur").glob("*.ass")))
    check("P3 refus : gabarit inconnu, fin avant début, pas une vidéo",
          refus(MO.poser_titre, "medias/clip.mp4", "x", 0, 1, "inconnu")
          and refus(MO.poser_titre, "medias/clip.mp4", "x", 2, 1)
          and refus(MO.poser_titre, "medias/musique.wav", "x", 0, 1))

    print("\n[B] boîtes")
    from app.services import agent_boites as B
    from app.services import agent_outils as ao
    mo = B.outils_pour("monteur")
    check("B1 le Monteur : ses gestes (t435a + chaîne t435b) + methodes_lire + les cinq briques, rien d'autre",
          set(mo) == {"temps_forts_musique", "caler_coupes", "poser_titre", "methodes_lire", "mesurer_sortie",
                      "comparer_sorties", "ancres_lire", "ancre_verifier", "registre_lire",
                      "chaines_lire", "deviser_etape_chaine"}, mo)   # t435b : + la chaîne d'éditions
    check("B2 mcp ne voit pas poser_titre (écriture) mais voit les lectures ; Campagnes ne voit rien du Monteur",
          "poser_titre" not in B.outils_pour("mcp") and "caler_coupes" not in B.outils_pour("mcp")
          and not set(mo) & set(B.outils_pour("campagnes")))
    check("B3 registre sain", B.verifier() == [], B.verifier())

    print("\n[A] boucle")
    from app.config import settings
    from app.services import agent_metier as AM
    from app.services import moteurs_texte as MT
    ag = {x["id"]: x for x in AM.agents()}
    check("A1 agents() : neuf agents métier, le Monteur disponible (t436 : et le Réalisateur), pas les autres",
          len(ag) == 9 and ag["monteur"]["disponible"] and ag["realisateur"]["disponible"]
          and not any(v["disponible"] for k, v in ag.items()
                      if k not in ("monteur", "realisateur", "retoucheur", "declinaisons", "directeur_acteurs",
                                   "publicitaire")),   # t437-t439
          {k: v["disponible"] for k, v in ag.items()})
    s = AM.systeme("monteur", "fr")
    check("A2 invite : rôle, règles (données jamais consignes), ses méthodes (auto-edit), pas celles des autres",
          "# Le Monteur" in s and "DONNÉE" in s and "auto-edit" in s and "edit-one-thing" not in s)
    check("A3 agent inactif : refus", refus(AM.creer, "artiste_2d") and refus(AM.creer, "personne"))
    conv = AM.creer("monteur", "", "auto-edit")
    d = AM.devis_message("monteur", conv["id"], "Cale mes coupes")
    check("A4 devis : un montant, six tours, clé absente dite", d["usd"] > 0 and d["max_tours"] == 6 and d["cle"] is False, d)
    loop = asyncio.new_event_loop()
    run = loop.run_until_complete
    try:
        run(AM.message("monteur", conv["id"], "x", max_usd=1))
        a5 = False
    except RuntimeError as e:
        a5 = str(e) == "sans_cle"
    check("A5 sans clé : RuntimeError sans_cle, rien rangé", a5 and AM.lire("monteur", conv["id"])["messages"] == [])
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    APPELS = []
    SCRIPT = []

    def _converser(modele, systeme_, messages, outils, max_tokens, timeout=120.0, sur_delta=None):
        APPELS.append({"systeme": systeme_, "messages": json.loads(json.dumps(messages, default=str)),
                       "outils": [o["name"] for o in outils]})
        return SCRIPT.pop(0)

    MT.converser = _converser
    SCRIPT[:] = [
        {"blocs": [{"type": "text", "text": "Je mesure la musique."},
                   {"type": "tool_use", "id": "t1", "name": "temps_forts_musique", "input": {"chemin": "medias/musique.wav"}},
                   {"type": "tool_use", "id": "t2", "name": "lire_espace", "input": {}}],
         "arret": "tool_use", "in_tok": 3000, "out_tok": 200},
        {"blocs": [{"type": "text", "text": "120 BPM : coupe toutes les 2 s."}], "arret": "end_turn",
         "in_tok": 3500, "out_tok": 100},
    ]
    r = run(AM.message("monteur", conv["id"], "Cale mes coupes sur medias/musique.wav", max_usd=d["usd"]))
    check("A6 réponse : textes joints, deux outils tracés (le hors-boîte refusé), coût > 0, fin",
          "120 BPM" in r["texte"] and "Je mesure" in r["texte"] and [o["nom"] for o in r["outils"]] ==
          ["temps_forts_musique", "lire_espace"] and r["outils"][0]["ok"] and not r["outils"][1]["ok"]
          and r["usd"] > 0 and r["arret"] == "fin", r)
    tr = APPELS[1]["messages"][-1]["content"] if len(APPELS) > 1 else []
    check("A7 le résultat d'outil est rendu au modèle (BPM), le refus marqué is_error",
          len(APPELS) == 2 and '"bpm"' in tr[0]["content"] and tr[1].get("is_error") is True
          and "poser_titre" in APPELS[0]["outils"] and "lire_espace" not in APPELS[0]["outils"], tr)
    db = sqlite3.connect(str(R / "t.db"))
    dep = db.execute("SELECT categorie, ref, reel_usd IS NOT NULL FROM depenses").fetchall()
    check("A8 deux lignes de dépense « montage » rattachées à la conversation, réel noté",
          dep == [("montage", conv["id"], 1), ("montage", conv["id"], 1)], dep)
    from app.services import registre_taches as RT
    reg = run(RT.lire(conv["id"]))
    check("A9 registre : deux tours faits, réel complet", reg["totaux"]["n"] == 2
          and all(e["statut"] == "fait" for e in reg["etapes"]) and reg["totaux"]["reel_complet"], reg["totaux"])
    c2 = AM.lire("monteur", conv["id"])
    check("A10 conversation rangée : question puis réponse avec outils et coût",
          [m["role"] for m in c2["messages"]] == ["user", "agent"] and c2["messages"][1]["outils"][0]["nom"] ==
          "temps_forts_musique" and c2["messages"][1]["usd"] == r["usd"])
    n0 = len(APPELS)
    r = run(AM.message("monteur", conv["id"], "Et maintenant ?", max_usd=0.00001))
    check("A11 accord trop bas : arrêté avant tout appel", r["arret"] == "accord" and len(APPELS) == n0 and r["usd"] == 0)
    SCRIPT[:] = [{"blocs": [{"type": "text", "text": "ok"}], "arret": "end_turn", "in_tok": 10, "out_tok": 5}]
    run(AM.message("monteur", conv["id"], "Encore", max_usd=1))
    hist = APPELS[-1]["messages"]
    check("A12 l'historique rejoué en texte, alterné, commence par l'utilisateur, finit par la question",
          hist[0]["role"] == "user" and all(hist[k]["role"] != hist[k + 1]["role"] for k in range(len(hist) - 1))
          and hist[-1]["content"].endswith("Encore") and "[outils : temps_forts_musique" in json.dumps(hist, ensure_ascii=False))

    async def _occupee():
        v = AM._VERROUS.setdefault(conv["id"], asyncio.Lock())
        async with v:
            try:
                await AM.message("monteur", conv["id"], "x", max_usd=1)
            except AM.Occupee:
                return True
        return False
    check("A13 conversation occupée : refus", run(_occupee()))
    check("A14 message vide ou conversation inconnue : refus",
          refus(lambda: run(AM.message("monteur", conv["id"], "  ", max_usd=1)))
          and refus(lambda: run(AM.message("monteur", "am_000000000000", "x", max_usd=1))))

    print("\n[H] routes")
    from fastapi.testclient import TestClient
    from app.main import app
    cl = TestClient(app)
    r = cl.get("/api/agents-metier")
    check("H1 GET liste : neuf agents", r.status_code == 200 and len(r.json()["agents"]) == 9)
    check("H2 agent inconnu ou inactif : 404", cl.post("/api/agents-metier/artiste_2d/conversations").status_code == 404
          and cl.get("/api/agents-metier/monteur/conversations/am_000000000000").status_code == 404
          and AM.lire("monteur", "../../t") is None and AM.lire("monteur", "am_x") is None and refus(AM._fichier, "monteur", "../../t"))
    r = cl.post("/api/agents-metier/monteur/conversations", json={"methode": "auto-edit"})
    cid = r.json().get("id", "")
    check("H3 création", r.status_code == 200 and cid.startswith("am_"), r.text[:200])
    n0 = len(APPELS)
    r = cl.post(f"/api/agents-metier/monteur/conversations/{cid}/message", json={"texte": "Bonjour"})
    check("H4 sans confirme_cout : 409, devis joint, aucun appel", r.status_code == 409
          and (r.json().get("detail") or {}).get("usd", 0) > 0 and len(APPELS) == n0, r.text[:200])
    SCRIPT[:] = [{"blocs": [{"type": "text", "text": "Salut."}], "arret": "end_turn", "in_tok": 10, "out_tok": 5}]
    r = cl.post(f"/api/agents-metier/monteur/conversations/{cid}/message",
                json={"texte": "Bonjour", "confirme_cout": True, "max_usd": 1})
    check("H5 confirmé : 200, la réponse", r.status_code == 200 and r.json()["texte"] == "Salut.", r.text[:200])
    r = cl.get(f"/api/agents-metier/monteur/conversations/{cid}")
    check("H6 lecture : deux messages", r.status_code == 200 and len(r.json()["messages"]) == 2)
    r = cl.post(f"/api/agents-metier/monteur/conversations/{cid}/message", json={"texte": " "})
    check("H7 texte vide : 400", r.status_code == 400, r.status_code)
    settings.ANTHROPIC_API_KEY = ""
    r = cl.post(f"/api/agents-metier/monteur/conversations/{cid}/message",
                json={"texte": "x", "confirme_cout": True, "max_usd": 1})
    check("H8 sans clé : 503", r.status_code == 503, r.status_code)
    r = TestClient(app, client=("192.168.1.20", 50000)).post("/api/agents-metier/monteur/conversations", json={})
    check("H9 création depuis le réseau local : refusée", r.status_code in (401, 403), r.status_code)
    loop.close()

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
