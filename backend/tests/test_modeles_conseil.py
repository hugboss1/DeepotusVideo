# -*- coding: utf-8 -*-
"""t492 (lot F5 « Fiches modèle », 10/11/2026) — recommander_modele et verifier_prompt, SANS LLM ni réseau.

[1] coût estimé        unités s, min, 1k_car, à l'unité, local gratuit, prix à mesurer ;
[2] filtres durs       durée, image de fin, références, retouche, transparent, SVG, paroles, garder la voix, pose de
                       rig, format d'export, texte vers 3D, balises, clé posée, budget ;
[3] classement         pertinence (fiches, racines FR/EN, puce [CHOIX] qui nomme le membre), alternative chez une autre
                       famille, brouillon (palier, résolution, sans texture, membre moins cher) ;
[4] relecture          format en prose, « no music », négatifs (champ négatif ou positif), prix, paramètre d'un autre
                       outil, crochets, mots-clés, plafond de longueur (musique, effets, voix, h3-max), transparent non
                       servi, balises de voix (retirées, hors palette, consigne lue), prompt propre sans constat ;
[5] outils d'agent     boîte « modeles », lecture, refus nommés.

Lancement (python EMBARQUÉ, depuis backend/) :  PYTHONUTF8=1 python tests/test_modeles_conseil.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import modeles_conseil as K        # noqa: E402
from app.services import agent_outils as ao           # noqa: E402
from app.services import agent_boites as B            # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label}  {str(detail)[:400]}")


def ids(r):
    return [g["id"] for g in r["classement"]]


def ecarte(r, mid):
    return next((e["raison"] for e in r["ecartes"] if e["id"] == mid), None)


print("[1] coût estimé")
check("1.1 à la seconde x durée", K.cout({"usd": 0.1, "unite": "s"}, {"duree": 8}) == 0.8)
check("1.2 à la seconde sans durée : la plus courte du membre",
      K.cout({"usd": 0.1, "unite": "s", "durations": [5, 10]}, {}) == 0.5)
check("1.3 à la minute ENTAMÉE", K.cout({"usd": 0.6, "unite": "min"}, {"duree": 62}) == 1.2)
check("1.4 voix : par 1 000 caractères", K.cout({"usd": 0.24, "unite": "1k_car"}, {"caracteres": 500}) == 0.12)
check("1.5 à l'unité x n", K.cout({"usd": 0.04, "unite": "image"}, {"n": 3}) == 0.12)
check("1.6 local gratuit = 0, prix à mesurer = None",
      K.cout({"usd": 0, "voie": "local", "unite": "gen"}, {}) == 0.0 and K.cout({"usd": 0, "voie": "fal"}, {}) is None)

print("[2] filtres durs")
r = K.recommander("video_i2v", "", {"duree": 15})
check("2.1 durée hors plage d'un membre : écarté avec la plage", ecarte(r, "seedance-v1-pro") and "15" in ecarte(r, "seedance-v1-pro")
      and "kling-v3-pro" in ids(r) + [e["id"] for e in r["ecartes"]], r["ecartes"][:3])
r = K.recommander("video_fl", "", {"image_fin": True})
check("2.2 image de fin exigée : tous les gardés en ont une", all(g["_m"]["end_image"] if "_m" in g else True for g in r["classement"])
      and all(K.ecart(dict(g, natures=["video_fl"], end_image=False), {"image_fin": True}) for g in r["classement"]))
r = K.recommander("image", "", {"refs": 12})
check("2.3 12 références : seuls les membres qui en prennent assez (Nano Pro/2.1, GPT via fal)",
      r["classement"] and all(i in ("nano-banana-pro", "nano-banana-2.1") or i.endswith("-fal") for i in ids(r))
      and "gpt-image-2" in [e["id"] for e in r["ecartes"]], ids(r))
r = K.recommander("image", "", {"transparent": True})
check("2.4 fond transparent : seuls les membres qui le rendent", set(ids(r)) <= {
      "gpt-image-2-fal", "gpt-image-2.5-flare", "gpt-image-2.5-flare-fal", "gpt-image-2.5-sunburst-fal"} and ids(r), ids(r))
r = K.recommander("image", "logo", {"vecteur": True})
check("2.5 vecteur : Recraft seul ; raster : Recraft écarté",
      ids(r) == ["recraft-4.1-vecteur"] and "recraft-4.1-vecteur" in [e["id"] for e in K.recommander("image")["ecartes"]])
r = K.recommander("musique", "", {"paroles": True})
check("2.6 paroles : seuls les membres à paroles", ids(r) and "lyria3" not in ids(r) and ecarte(r, "lyria3") == "pas de paroles")
r = K.recommander("sfx_video", "", {"garder_voix": True})
check("2.7 garder la voix : Sonilo vidéo seul", ids(r) == ["sonilo-video"], ids(r))
r = K.recommander("modele3d", "", {"pose_rig": True})
check("2.8 pose de rig : Rodin, Rodin 2.5, Meshy 7.1", set(ids(r)) == {"rodin", "rodin-2.5", "meshy-7.1"}, ids(r))
r = K.recommander("modele3d", "", {"format_export": "stl", "depuis_texte": True})
check("2.9 export STL depuis un texte : Rodin 2.5", ids(r) == ["rodin-2.5"], ids(r))
r = K.recommander("voix", "", {"balises": True})
check("2.10 balises d'émotion : Eleven v3 seul", ids(r) == ["eleven_v3"], ids(r))
r = K.recommander("video_i2v", "", {"duree": 10, "budget_usd": 0.5})
check("2.11 budget : un membre plus cher écarté, la raison chiffrée",
      any("budget" in e["raison"] for e in r["ecartes"]) and all((g["cout_estime"] or 0) <= 0.5 for g in r["classement"]))
r = K.recommander("voix", "", {"cles_posees": True})
check("2.12 clés posées seulement : un membre sans clé est écarté (Voicebox local gardé)",
      "voicebox" in ids(r) and all(g["dispo"] for g in r["classement"])
      and K.ecart({"dispo": False, "cle": "FAL_KEY", "natures": ["voix"]}, {"cles_posees": True}) == "clé FAL_KEY absente"
      and K.ecart({"dispo": False, "cle": "FAL_KEY", "natures": ["voix"]}, {}) is None)
try:
    K.recommander("inconnue")
    check("2.13 nature inconnue -> KeyError", False)
except KeyError:
    check("2.13 nature inconnue -> KeyError", True)

print("[3] classement")
r = K.recommander("voix", "jeu expressif avec émotions", {"caracteres": 500})
check("3.1 voix expressive -> Eleven v3 (puce [CHOIX] qui le nomme)", r["premier"]["id"] == "eleven_v3"
      and r["premier"]["raisons"] and "Eleven v3" in r["premier"]["raisons"][0], r["premier"])
check("3.2 voix narration posée -> Multilingual v2",
      K.recommander("voix", "narration posée")["premier"]["id"] == "eleven_multilingual_v2")
check("3.3 voix, textes longs en brouillon -> Flash v2.5",
      K.recommander("voix", "textes longs brouillon")["premier"]["id"] == "eleven_flash_v2_5")
check("3.4 détourage fourrure -> BiRefNet v2", K.recommander("detourage_image", "fourrure du chien")["premier"]["id"]
      == "birefnet-v2")
check("3.5 logo vectoriel -> Recraft", K.recommander("image", "logo vectoriel", {"vecteur": True})["premier"]["id"]
      == "recraft-4.1-vecteur")
r = K.recommander("image", "poster with exact headline lettering")
check("3.6 anglais : affiche à titre exact -> Ideogram, alternative d'une AUTRE famille",
      r["premier"]["id"] == "ideogram-4.5" and r["alternative"] and r["alternative"]["famille"] != "ideogram", r["premier"])
check("3.6b la description de la fiche pèse plein (un mot = 1/df), les puces [CHOIX] pour moitié",
      r["premier"]["score"] >= 1.5, r["premier"]["score"])
check("3.6c racines : « typographique » et « typographie », « poses » et « pose » se rejoignent",
      K._mots("typographique") == K._mots("typographie") and K._mots("poses") == K._mots("pose")
      and "v3" in K._mots("Eleven v3"))
_rv = K.recommander("voix", "jeu expressif avec émotions")
check("3.6d alternative : la meilleure d'une AUTRE famille, pas le deuxième du classement",
      _rv["classement"][1]["famille"] == "elevenlabs" and _rv["alternative"]["id"] == "voicebox", _rv["alternative"])
check("3.7 brouillon : palier bas d'Ideogram, moins cher que high",
      r["brouillon"] and r["brouillon"]["reglage"].get("qualite") == "low", r["brouillon"])
from app.services import catalogue_ia as _C   # noqa: E402
_br3 = {e["id"]: e["brouillon"] for e in _C.lister("modele3d")}
_p3 = next(g for g in K.recommander("modele3d", "", {"format_export": "fbx"})["classement"] if _br3[g["id"]])
_b3 = K._brouillon(dict(_p3, _m=dict(_C.lister("modele3d")[[e["id"] for e in _C.lister("modele3d")].index(_p3["id"])],
                                     natures=["modele3d"])), [], {})
check("3.8 3D : brouillon sans texture pour un membre qui le permet", _b3 and _b3["reglage"] == {"texture": False}, _b3)
r = K.recommander("voix", "narration posée", {"caracteres": 1000})
check("3.9 brouillon : membre moins cher de la même famille (Flash v2.5)",
      r["brouillon"] and r["brouillon"]["id"] == "eleven_flash_v2_5", r["brouillon"])
r = K.recommander("video_i2v", "", {"duree": 5})
check("3.10 sans consigne : classé par prix connu croissant (dispo égale)",
      [g["cout_estime"] for g in r["classement"] if g["cout_estime"] is not None and g["dispo"]] ==
      sorted(g["cout_estime"] for g in r["classement"] if g["cout_estime"] is not None and g["dispo"]))
check("3.11 aucune clé privée dans le résultat (« _m » retiré)", all("_m" not in g for g in r["classement"])
      and "_m" not in r["premier"])
check("3.12 une puce « Pas encore dans l'app » n'est jamais une raison", not any(
      "Pas encore" in x for g in K.recommander("video_i2v", "brouillon pas cher extension")["classement"]
      for x in g["raisons"]))

print("[4] relecture")
v = K.verifier_prompt("kling-v3-pro", "A woman walks, 16:9 vertical format, no music, no people, price $19.99 --ar 9:16")
codes = [x["code"] for x in v["constats"]]
check("4.1 format en prose, no music, négatif, prix, paramètre d'un autre outil", codes == [
      "format_en_prose", "sans_son_ecrit", "negatif_en_clair", "prix_ou_mention", "parametre_autre_outil"], codes)
check("4.2 Kling a un champ négatif : le constat le dit ; un prix est une ERREUR, ok faux",
      "champ négatif : y mettre" in v["constats"][2]["message"] and v["ok"] is False
      and v["constats"][3]["extrait"] == "$19.99")
v = K.verifier_prompt("seedance-2", "A dog runs, no people around")
check("4.3 sans champ négatif : formuler en positif", any(x["code"] == "negatif_en_clair"
      and "positif" in x["message"] for x in v["constats"]), v["constats"])
v = K.verifier_prompt("ideogram-4.5", 'Poster, headline "COOL LEAF". No other text, no extra words.')
check("4.4 « no other text » et « no extra words » ne sont pas des négatifs", v["constats"] == [], v["constats"])
v = K.verifier_prompt("flux", "sticker, transparent background")
check("4.5 fond transparent demandé à un membre qui ne le rend pas",
      [x["code"] for x in v["constats"]] == ["transparent_non_servi"], v["constats"])
check("4.6 fond transparent demandé à GPT 2.5 Flare : rien à dire",
      K.verifier_prompt("gpt-image-2.5-flare", "a sticker on a transparent background")["constats"] == [])
v = K.verifier_prompt("flux", "cat, cute, fluffy, 8k, masterpiece, trending, sharp, colorful, detailed")
check("4.7 liste de mots-clés", "mots_cles" in [x["code"] for x in v["constats"]])
v = K.verifier_prompt("flux", "A [character] stands in the rain")
check("4.8 crochet dans un prompt d'image", [x["code"] for x in v["constats"]] == ["crochets"])
v = K.verifier_prompt("lyria3", "x" * 2100)
check("4.9 musique : plafond du registre (prompt_max ou défaut 2000)", v["limite"] == 2000 and v["ok"] is False
      and v["constats"][-1]["code"] == "trop_long")
v = K.verifier_prompt("kling-v2a", "y" * 250)
check("4.10 effets : plafond du registre (Kling vidéo -> son 200)", v["limite"] == 200 and not v["ok"])
v = K.verifier_prompt("h3-max", "z" * 2001)
check("4.11 h3-max : plafond daté 2000", v["limite"] == 2000 and not v["ok"])
v = K.verifier_prompt("eleven_flash_v2_5", "Bonjour [whispers] (angry) salut [Scène 2]")
cs = {x["code"]: x for x in v["constats"]}
check("4.12 voix hors v3 : balise connue retirée, crochet hors palette lu, consigne lue",
      set(cs) == {"balises_retirees", "balise_hors_palette", "consigne_lue"}
      and cs["balises_retirees"]["extrait"] == "[whispers]" and cs["balise_hors_palette"]["extrait"] == "[Scène 2]")
v = K.verifier_prompt("eleven_v3", "Bonjour [whispers] salut.")
check("4.13 v3 et balise connue : rien à dire", v["constats"] == [], v["constats"])
v = K.verifier_prompt("eleven_multilingual_v2", "a" * 10001)
check("4.14 voix au-delà de car_max : découpée (info), pas une erreur", v["ok"] and v["constats"][-1]["code"] == "trop_long"
      and v["constats"][-1]["gravite"] == "info")
v = K.verifier_prompt("kling-v3-pro", "The camera slowly pushes in as she turns her head and smiles.")
check("4.15 prompt propre : aucun constat", v["constats"] == [] and v["ok"], v["constats"])
v = K.verifier_prompt("lyria3", "warm jazz, no vocals, 84 BPM")
check("4.16 « no vocals » en musique : négatif signalé, pas de format", [x["code"] for x in v["constats"]] ==
      ["negatif_en_clair"], v["constats"])
try:
    K.verifier_prompt("inconnu", "x")
    check("4.17 id inconnu -> KeyError", False)
except KeyError:
    check("4.17 id inconnu -> KeyError", True)

print("[5] outils d'agent")
check("5.1 deux outils en lecture dans la boîte « modeles »",
      all(ao.OUTILS[o]["nature"] == "lecture" for o in ("recommander_modele", "verifier_prompt"))
      and {"recommander_modele", "verifier_prompt"} <= set(B.BOITES["modeles"]["outils"])
      and {"recommander_modele", "verifier_prompt"} <= set(B.outils_pour("mcp"))
      and not {"recommander_modele", "verifier_prompt"} & set(B.outils_pour("campagnes")))
check("5.2 schémas : nature requise ; modele et prompt requis",
      ao.OUTILS["recommander_modele"]["schema"]["required"] == ["nature"]
      and ao.OUTILS["verifier_prompt"]["schema"]["required"] == ["modele", "prompt"])
r = asyncio.run(ao.recommander_modele(None, "voix", "jeu expressif", {"caracteres": 500, "inconnue": 1}))
check("5.3 recommander : résumé avec premier choix et prix, contrainte inconnue ignorée",
      r["ok"] and "eleven_v3" in r["resume"] and "inconnue" not in r["donnees"]["contraintes"], r["resume"])
r = asyncio.run(ao.recommander_modele(None, "nope"))
check("5.4 nature inconnue : refus qui liste les natures", not r["ok"] and "video_i2v" in r["resume"])
r = asyncio.run(ao.recommander_modele(None, "sfx_video", "", {"garder_voix": True, "budget_usd": 0.0001, "duree": 8}))
check("5.5 aucun membre : refus qui dit les écartés", not r["ok"] and "écartés" in r["resume"], r["resume"])
r = asyncio.run(ao.verifier_prompt(None, "flux", "sticker, transparent background"))
check("5.6 verifier_prompt : résumé avec le code", r["ok"] and "transparent_non_servi" in r["resume"])
r = asyncio.run(ao.verifier_prompt(None, "nope", "x"))
check("5.7 modèle inconnu : refus", not r["ok"] and "modeles_lister" in r["resume"])

print("[7] correctifs de l'épreuve d'application F5")
r = K.recommander("image", "affiche texte exact, trois brouillons pas chers", {"n": 3})
check("7.1 « brouillons pas chers » : devis au palier le plus bas, hypothèse dite, mots de prix hors pertinence",
      r["contraintes"].get("qualite") == "bas" and "qualite" in r["hypotheses"]
      and all("cher" not in g["mots"] and "brouil" not in g["mots"] for g in r["classement"])
      and next(g for g in r["classement"] if g["id"] == "gpt-image-2.5-sunburst-fal")["cout_estime"] < 0.05, r["hypotheses"])
check("7.2 palier explicite : coût au palier demandé",
      K.cout({"usd": 0.053, "unite": "image", "qualites": {"low": 0.006, "high": 0.053}}, {"qualite": "low"}) == 0.006
      and K.cout({"usd": 0.053, "unite": "image", "qualites": {"low": 0.006, "high": 0.053}}, {"qualite": "bas"}) == 0.006)
r = K.recommander("musique", "", {"duree": 60, "paroles": True})
check("7.3 musique : durée demandée, membre qui la choisit seul -> écarté",
      ecarte(r, "minimax-music-20") == "durée choisie par le modèle (non réglable)" and "minimax-music-3" in ids(r))
r = K.recommander("video_fl", "", {"duree": 6, "ratio": "9:16", "image_fin": True})
check("7.4 durées discontinues : la raison liste les durées permises (PixVerse 5 ou 8 s)",
      ecarte(K.recommander("video_i2v", "", {"duree": 6}), "pixverse-v6") == "durée 6 s non permise (5, 8 s)")
g = {x["id"]: x for x in r["classement"]}
check("7.5 adéquation : un champ format listé + image de fin comptent ; sans champ format, un avertissement",
      g["veo-3.1-fast-fal"]["adequation"] == 1.5 and g["kling-v3-pro"]["adequation"] == 0.75
      and any("cadre suit l'image" in a for a in g["kling-v3-pro"]["avertissements"]))
check("7.5b à consigne vide, l'adéquation départage : le premier tient le format PAR SON CHAMP",
      r["premier"]["adequation"] == max(x["adequation"] for x in r["classement"]) == 1.5, r["premier"])
_r5 = K.recommander("video_i2v", "", {"duree": 5, "ratio": "9:16"})
check("7.5c le moins cher SANS champ format (PixVerse) passe derrière un membre qui tient le format par son champ",
      _r5["premier"]["id"] != "pixverse-v6" and _r5["premier"]["adequation"] == 0.75
      and next(x for x in _r5["classement"] if x["id"] == "pixverse-v6")["adequation"] == 0, _r5["premier"])
check("7.6 tout le classement est rendu (aucun membre ni montré ni écarté)",
      len(r["classement"]) + len(r["ecartes"]) == r["total"])
check("7.7 l'alternative dit son rôle de repli chez un autre fournisseur", "repli" in (r["alternative"] or {}).get("role", ""))
check("7.8 hypothèses : durée et caractères par défaut dites",
      "duree" in K.recommander("video_i2v")["hypotheses"] and K.recommander("voix")["hypotheses"].get("caracteres") == 1000)
r = K.recommander("detourage_image", "personnage aux cheveux bouclés")
check("7.9 cheveux : BiRefNet v2 devant (prix à mesurer averti, pas pénalisé quand la fiche le nomme)",
      r["premier"]["id"] == "birefnet-v2" and any("à mesurer" in a for a in r["premier"]["avertissements"]), r["premier"])
for bad, label in (({"duree": "six"}, "texte"), ({"n": 0}, "zéro"), ({"duree": -3}, "négatif")):
    try:
        K.recommander("voix", "", bad)
        check(f"7.10 contrainte illisible ({label}) -> ValueError nommée", False)
    except ValueError as e:
        check(f"7.10 contrainte illisible ({label}) -> ValueError nommée", "contrainte" in str(e))
r = K.recommander("voix", "", {"bidule": 1, "balises": "oui"})
check("7.11 contrainte inconnue rendue dans « ignorees », booléen texte lu", r["ignorees"] == ["bidule"]
      and r["contraintes"] == {"balises": True})
v = K.verifier_prompt("ideogram-4.5", "Winter sale poster, headline \"SOLDES D'HIVER -30 %\", square format, with no text")
cs = [x["code"] for x in v["constats"]]
check("7.12 « -30 % » est un prix ; « square format » en prose ; « with no text » n'est pas un négatif",
      cs == ["format_en_prose", "prix_ou_mention"], v["constats"])
v = K.verifier_prompt("eleven_v3", "Hi there (say this happily) [Scene 2]")
cs = {x["code"]: x["gravite"] for x in v["constats"]}
check("7.13 v3 : consigne entre parenthèses lue ; crochet hors palette = ERREUR (il sera dit)",
      cs == {"consigne_lue": "avertissement", "balise_hors_palette": "erreur"} and not v["ok"], v["constats"])
check("7.14 sujet nommé exigé (SAM 3) : description vide = erreur ; BiRefNet : description ignorée",
      [x["code"] for x in K.verifier_prompt("sam3-sujet", "")["constats"]] == ["description_requise"]
      and [x["code"] for x in K.verifier_prompt("birefnet-v2", "the dog")["constats"]] == ["description_ignoree"])
v = K.verifier_prompt("kling-v3-pro", "A woman walks, 9:16 frame")
check("7.15 Kling sans champ format : le constat dit de préparer l'image de départ",
      "image de départ" in v["constats"][0]["message"], v["constats"])

print("[6] routes (gratuites, lecture)")
from fastapi import FastAPI                          # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from app.api import modeles_routes as _MR            # noqa: E402
_app = FastAPI()
_app.include_router(_MR.router, prefix="/api/modeles")
with TestClient(_app) as cl:
    r = cl.post("/api/modeles/recommander", json={"nature": "voix", "consigne": "jeu expressif",
                                                  "contraintes": {"caracteres": 500}})
    check("6.1 POST recommander : premier choix", r.status_code == 200 and r.json()["premier"]["id"] == "eleven_v3",
          r.text[:200])
    r = cl.post("/api/modeles/recommander", json={"nature": "x"})
    check("6.2 nature inconnue : 400 nommé", r.status_code == 400 and "nature" in r.text, r.text[:200])
    r = cl.post("/api/modeles/recommander", json={"nature": "voix", "contraintes": {"duree": "six"}})
    check("6.2b contrainte illisible : 400 nommé, jamais 500", r.status_code == 400 and "contrainte" in r.text,
          r.text[:200])
    r = cl.post("/api/modeles/verifier", json={"modele": "flux", "prompt": "sticker, transparent background"})
    check("6.3 POST verifier : constats", r.status_code == 200
          and r.json()["constats"][0]["code"] == "transparent_non_servi", r.text[:200])
    r = cl.post("/api/modeles/verifier", json={"modele": "x", "prompt": "y"})
    check("6.4 modèle inconnu : 404 nommé", r.status_code == 404 and "mod" in r.text, r.text[:200])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
