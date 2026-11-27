# -*- coding: utf-8 -*-
"""SV1 (14/11/2026) — banc du service du STUDIO VIRTUEL 3D (app/services/studiov.py) et de ses routes.
Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md.
Sections :
  1. format : champ inconnu ignoré, nombres bornés (NaN, bool, hors borne), choix fermés, listes bornées, objet hors
     catalogue RETIRÉ (jamais un chemin ni une URL), matière inconnue -> défaut, couleur = rôle ou #hex, au moins une
     caméra, normaliser idempotent ;
  2. livrés : onze, lecture seule (409), chacun avec écran, caméras (dont « Écran »), clé + appoint + contre, objets
     tous au catalogue et DANS la pièce ; le fichier livré = la sortie du compositeur (--check) ;
  3. décors de l'espace : créer (copie d'un livré), nom libre « (2) », enregistrer (l'espace ne change pas), lister par
     espace, identifiants hostiles (400), introuvable (404), autre espace (409), supprimer libère le choix ;
  4. choix : défaut "" (PAS de studio : il s'ajoute aux skins), livré, décor d'un autre espace refusé ;
  5. catalogue : les types du serveur = ceux de la logique JS = ceux que le moteur sait bâtir ;
  6. routes : boucle locale, liste, actif, choix, création, lecture, écriture d'un livré refusée, fabrique absente 404 ;
  7. habillage (lot SVH) : une texture n'est qu'une RÉFÉRENCE (stu:, cat:, mat:) — chemin, URL ou préfixe inconnu -> "" ;
     teinte, usage, mur du fond, matière secondaire, mot et police des seuls objets à mot ; le pack d'intérieur livré
     concorde avec son catalogue (--check) ; styles, ambiances et finitions cohérents (références livrées, couleurs
     valides) ; les décors livrés n'emploient que des textures de l'installeur ; routes : catalogue, carte du pack
     (confinée), vignette de la Forge, hors boucle locale refusé ;
  8. depuis Blender (lot SVH) : chemin vide (400), fichier absent ou d'une autre extension (404) ; Blender lancé sans
     fenêtre et SANS exécuter les scripts du fichier ; les cartes cuites deviennent une matière ordinaire de la Forge
     (référence `mat:`), proposée aussitôt au décorateur ; un dossier de sortie hostile est ignoré, une sortie sans
     marque est un refus (502) ; le script de cuisson est livré dans l'application. Blender est remplacé par une
     couture : aucun logiciel n'est lancé par ce banc ;
  9. objets importés et atelier (lots SVO, SVA) : un GLB est LU avant d'être gardé (format, version, compression,
     fichiers voisins, poids) ; la licence retenue dit les droits (vidéo, export, partage, crédit) et les licences
     NC, ND, SA sont refusées ; bibliothèque (import, liste, identifiant hostile, suppression refusée tant qu'un
     décor l'emploie) ; la recette garde un objet `modele` par sa RÉFÉRENCE seulement, et une matière par pan de
     mur ; crédits d'un décor ; routes (dont le chargeur three.js réécrit, liste fermée) ; export depuis Blender ;
 10. depuis la Bibliothèque de l'application (lot SVB) : une image (illustration, logo) est RECOPIÉE dans le studio,
     désignée par son nom de fichier seul, ramenée à 2 048 px, sa transparence gardée, copiée une seule fois ; la
     recette la porte par référence (tableau, logo mural, kakémono, écran du décor, enseigne) ; un modèle 3D généré
     entre dans les objets du studio (version allégée d'abord) ; suppression refusée tant qu'un décor l'emploie ;
     crédits : une image sous licence à citer ou à vérifier est signalée ;
 11. catalogue de produits réels (lot SVC, Amazon Berkeley Objects) : rien sans le geste « Charger » (409) ; la liste
     reçue devient un index (lignes hostiles, trop lourdes ou en double écartées ; trop peu de produits = refus) ;
     famille d'après le type, sinon d'après le nom ; pose d'après l'origine du fichier (sol, mur, plafond) ; recherche
     en français ou en anglais, par famille, paginée ; vignette téléchargée une fois ; « poser » ne télécharge QUE
     objects/<id>/<id>.glb de la révision figée, vérifie sa taille, range l'objet avec sa licence CC BY, son auteur,
     sa pose et son titre, une seule fois ; un luminaire est rangé « lumineux », un bougeoir ou un siège non ; Meshopt accepté, dimensions mesurées avec les nœuds ; crédits groupés ;
     la source `abo` n'est pas déclarable à l'import d'un fichier ; le réseau du studio tient en UNE fonction.
     Le réseau est remplacé par une couture : ce banc ne sort jamais.
 12. régie de l'écran (lot SVR) : la recette garde la suite des médias de l'écran — type fermé, image ou vidéo par
     RÉFÉRENCE seulement, 12 au plus ; une vidéo de la Bibliothèque est LIÉE (jamais copiée) : seulement un fichier
     vidéo rangé sous le dossier des sorties, revérifié à chaque lecture, une fois par job ; vignette tirée par
     ffmpeg (remplacé par une couture) ; suppression refusée tant qu'une régie l'emploie ; routes (lecture par
     morceaux, identifiant hostile, hors boucle locale).
Données jetables (DEEPOTUS_DATA_DIR temporaire), aucun réseau.
Run (depuis backend/) : & $PY tests/test_studiov_service.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzstudiov_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")                 # les matières de la Forge (section 8) : jetables
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")                   # la Bibliothèque d'images (section 10) : jetable
_ICI = pathlib.Path(__file__).resolve().parent
REPO = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


def _refus_h(f, *a):
    try:
        f(*a)
    except H.RefusHabillage as e:
        return e.statut
    return None


def refus(f, *a):
    try:
        f(*a)
    except S.RefusStudio as e:
        return e.statut
    return None


from app.services import studiov as S                                # noqa: E402

print("1. format")
n = S.normaliser({"piece": {"l": 99, "p": float("nan"), "h": True, "sol": "inconnue", "pirate": 1},
                  "matieres": {"bois": {"couleur": "principale", "motif": "bois", "rugosite": 7}, "../x": {}, "m2": {"motif": "lave", "couleur": "rouge"}},
                  "objets": [{"type": "bureau", "x": 500, "matiere": "bois"}, {"type": "C:/x.glb"}, {"type": "http://x/y.glb"}, "bureau",
                             {"type": "plante", "matiere": "absente", "couleur": "#AABBCC"}],
                  "lumieres": [{"type": "laser", "intensite": 999, "vers": [1, 2]}],
                  "ecrans": [{"source": "fichier", "l": 100}], "cameras": [], "enseigne": {"style": "hologramme", "texte": "A\x00B" + "x" * 90},
                  "presentateur": {"mode": "clone", "h": 9}, "ambiance": {"fond": "bleu", "brouillard": 4}, "mode": "cinema", "secret": "x"})
check("1.1 pièce bornée, NaN et booléen -> défaut, matière inconnue -> « sol »",
      n["piece"]["l"] == 16.0 and n["piece"]["p"] == 5.0 and n["piece"]["h"] == 2.8 and n["piece"]["sol"] == "sol" and "pirate" not in n["piece"], n["piece"])
check("1.2 matières : clé hostile écartée, motif inconnu -> uni, rôle gardé, rugosité bornée, sol/mur/plafond toujours là",
      set(n["matieres"]) == {"bois", "m2", "sol", "mur", "plafond"} and n["matieres"]["bois"]["couleur"] == "principale"
      and n["matieres"]["bois"]["rugosite"] == 1.0 and n["matieres"]["m2"]["motif"] == "uni" and n["matieres"]["m2"]["couleur"] == "#808890", n["matieres"])
check("1.3 objets : hors catalogue retirés (chemin, URL, non-objet), place bornée, matière absente -> None, #hex en minuscules",
      [o["type"] for o in n["objets"]] == ["bureau", "plante"] and n["objets"][0]["x"] == 12 and n["objets"][0]["matiere"] == "bois"
      and n["objets"][1]["matiere"] is None and n["objets"][1]["couleur"] == "#aabbcc", n["objets"])
check("1.4 lumière : type inconnu -> appoint, intensité bornée, visée fausse -> défaut",
      n["lumieres"][0]["type"] == "appoint" and n["lumieres"][0]["intensite"] == 20 and n["lumieres"][0]["vers"] == [0.0, 1.2, 0.0], n["lumieres"])
check("1.5 écran : source inconnue -> ecran, largeur bornée", n["ecrans"][0]["source"] == "ecran" and n["ecrans"][0]["l"] == 8.0)
check("1.6 enseigne : style inconnu -> neon, texte sans contrôle et borné",
      n["enseigne"]["style"] == "neon" and "\x00" not in n["enseigne"]["texte"] and len(n["enseigne"]["texte"]) == S.MAX_TEXTE)
check("1.7 au moins une caméra ; présentateur et mode ramenés aux choix fermés ; champ inconnu ignoré",
      len(n["cameras"]) == 1 and n["presentateur"]["mode"] == "detoure" and n["presentateur"]["h"] == 2.4 and n["mode"] == "plateau"
      and "secret" not in n and n["ambiance"]["fond"] == "#0b0f14" and n["ambiance"]["brouillard"] == 0.3)
check("1.8 normaliser est idempotent", S.normaliser(n) == n)
check("1.9 listes bornées", len(S.normaliser({"objets": [{"type": "de"}] * 500, "lumieres": [{}] * 50, "cameras": [{}] * 50,
                                             "ecrans": [{}] * 50})["objets"]) == S.MAX_OBJETS
      and len(S.normaliser({"cameras": [{}] * 50})["cameras"]) == S.MAX_CAMERAS)
check("1.10 un document qui n'est pas un objet rend le décor de référence", S.normaliser("x")["piece"]["l"] == 6.0)

print("2. livrés")
L = S.livres()
ATTENDUS = ["tech", "podcast", "loft", "actualite", "gaming", "atelier3d", "jeux", "scifi", "cartoon", "foot", "usa"]
check("2.1 onze décors livrés, dans l'ordre", [d["id"] for d in L] == ["livre-" + x for x in ATTENDUS], [d["id"] for d in L])
check("2.2 lecture seule : enregistrer et supprimer -> 409", refus(S.enregistrer, "livre-tech", {}) == 409 and refus(S.supprimer, "livre-tech") == 409)
for d in L:
    types = {l["type"] for l in d["lumieres"]}
    P = d["piece"]
    dedans = all(abs(o["x"]) <= P["l"] / 2 + 0.01 and -P["p"] / 2 - 0.01 <= o["z"] <= P["p"] / 2 + 2 and 0 <= o["y"] <= P["h"] + 0.5 for o in d["objets"])
    check(f"2.3 {d['id']} : écran partagé, 4 caméras ou plus dont « Écran », clé + appoint + contre, objets au catalogue et dans la pièce",
          any(e["source"] == "ecran" for e in d["ecrans"]) and len(d["cameras"]) >= 4 and "Écran" in [c["nom"] for c in d["cameras"]]
          and {"cle", "appoint", "contre"} <= types and len(d["objets"]) >= 8 and all(o["type"] in S.TYPES_OBJET for o in d["objets"])
          and dedans and d["livre"] and d["espace_id"] is None and d["famille"], (types, dedans, len(d["objets"])))
check("2.4 un livré inconnu -> 404", refus(S.lire, "livre-absent") == 404)
r = subprocess.run([sys.executable, str(REPO / "scripts" / "studiov" / "composer_livres.py"), "--check"], capture_output=True)
check("2.5 livres.json = la sortie du compositeur (scripts/studiov/composer_livres.py --check)", r.returncode == 0, r.stderr[-300:])

print("3. décors de l'espace")
a = S.creer("livre-loft", None, "esp-a")
b = S.creer("livre-loft", None, "esp-a")
check("3.1 créer copie le livré ; nom libre « (2) »", a["nom"] == "Loft chaleureux" and b["nom"] == "Loft chaleureux (2)" and a["base"] == "livre-loft"
      and not a["livre"] and a["espace_id"] == "esp-a" and len(a["objets"]) == len(S.lire("livre-loft")["objets"]) and S.ID.match(a["id"]))
doc = dict(a, nom="Mon loft", espace_id="esp-pirate"); doc["piece"] = dict(a["piece"], l=7.5)
e = S.enregistrer(a["id"], doc)
check("3.2 enregistrer : nom et recette changent, l'espace jamais", e["nom"] == "Mon loft" and e["piece"]["l"] == 7.5 and e["espace_id"] == "esp-a")
check("3.3 lister par espace", {d["id"] for d in S.lister("esp-a")} == {a["id"], b["id"]} and S.lister("esp-b") == [])
check("3.4 identifiants hostiles -> 400, jamais sur le disque", all(refus(S.lire, x) == 400 for x in ["../x", "a" * 15, "ABCDEF0123456789", "", None, 12]))
check("3.5 introuvable -> 404", refus(S.lire, "0" * 16) == 404 and refus(S.supprimer, "0" * 16) == 404)
check("3.6 décor d'un autre espace : copie refusée, lecture « du même espace » refusée (409)",
      refus(S.creer, a["id"], None, "esp-b") == 409 and refus(S.du_meme_espace, a["id"], "esp-b") == 409)
check("3.7 corps qui n'est pas un objet -> 400", refus(S.enregistrer, a["id"], [1]) == 400)

print("4. choix")
check("4.1 défaut : PAS de studio", S.choisi("esp-a") == "" and S.choisi("esp-neuf") == "")
check("4.2 choisir un livré, puis un décor de l'espace", S.choisir("esp-a", "livre-scifi") == "livre-scifi" and S.choisi("esp-a") == "livre-scifi"
      and S.choisir("esp-a", a["id"]) == a["id"] and S.choisi("esp-a") == a["id"])
check("4.3 décor d'un autre espace refusé (409), inconnu (404)", refus(S.choisir, "esp-b", a["id"]) == 409 and refus(S.choisir, "esp-b", "livre-absent") == 404)
S.supprimer(a["id"])
check("4.4 supprimer libère le choix", S.choisi("esp-a") == "" and refus(S.lire, a["id"]) == 404)
check("4.5 \"\" = sans studio", S.choisir("esp-a", "") == "" and S.choisir("esp-a", None) == "")

print("5. catalogue")
js = (REPO / "frontend" / "shared" / "dz-studiov-logique.js").read_text("utf-8")
types_js = re.findall(r'"([a-z0-9_]+)"', js.split("export const TYPES = [", 1)[1].split("];", 1)[0])
moteur = (REPO / "frontend" / "shared" / "dz-studiov-moteur.js").read_text("utf-8")
bloc = moteur.split("const B = {", 1)[1].split("\n  };", 1)[0]
types_moteur = re.findall(r"^    ([a-z0-9_]+)\(g", bloc, re.M)
check("5.1 types du serveur = types de la logique JS (même ordre)", list(S.TYPES_OBJET) == types_js, set(S.TYPES_OBJET) ^ set(types_js))
check("5.2 chaque type a son constructeur dans le moteur, et rien de plus", sorted(types_moteur) == sorted(S.TYPES_OBJET), set(S.TYPES_OBJET) ^ set(types_moteur))
check("5.3 aucun type en double", len(set(S.TYPES_OBJET)) == len(S.TYPES_OBJET))
check("5.4 le catalogue servi : familles, motifs, lumières, mouvements, usages, polices, styles d'enseigne, types à mot, lumineux et à image",
      set(S.catalogue()) == {"familles", "motifs", "lumieres", "mouvements", "usages", "polices", "styles_enseigne", "types_texte", "types_lumineux", "types_image", "types_media"})
check("5.5 les types à mot et les types lumineux sont au catalogue ; chaque police proposée est embarquée (frontend/dist/fonts)",
      set(S.TYPES_TEXTE) <= set(S.TYPES_OBJET) and set(S.TYPES_LUMINEUX) <= set(S.TYPES_OBJET)
      and all((REPO / "frontend" / "dist" / "fonts" / f"{p}.ttf").is_file() for p in S.POLICES))

print("6. routes")
from fastapi import FastAPI                                          # noqa: E402
from fastapi.testclient import TestClient                            # noqa: E402
from app.api.studiov_routes import router                            # noqa: E402
app = FastAPI(); app.include_router(router, prefix="/api/studiov")
local = TestClient(app, client=("127.0.0.1", 50000))
loin = TestClient(app, client=("192.168.1.50", 50000))
check("6.1 hors boucle locale : refusé", loin.get("/api/studiov").status_code in (401, 403))
r = local.get("/api/studiov")
check("6.2 liste : onze livrés, choisi \"\", catalogue", r.status_code == 200 and len(r.json()["livres"]) == 11 and r.json()["choisi"] == ""
      and "familles" in r.json()["catalogue"], r.text[:200])
check("6.3 actif : aucun décor par défaut, contexte présent", local.get("/api/studiov/actif").json()["decor"] is None
      and "logo_espace" in local.get("/api/studiov/actif").json()["contexte"])
check("6.4 choix d'un livré puis actif", local.put("/api/studiov/choix", json={"decor_id": "livre-tech"}).json() == {"choisi": "livre-tech"}
      and local.get("/api/studiov/actif").json()["decor"]["id"] == "livre-tech")
c = local.post("/api/studiov", json={"base": "livre-podcast", "nom": "Mon podcast"})
cid = c.json().get("id", "")
check("6.5 création, lecture, écriture", c.status_code == 200 and local.get(f"/api/studiov/{cid}").json()["decor"]["nom"] == "Mon podcast"
      and local.put(f"/api/studiov/{cid}", json={"nom": "Podcast B", "mode": "incruste"}).json()["mode"] == "incruste")
check("6.6 livré : écriture et suppression 409 ; id hostile 400 ; corps illisible 400",
      local.put("/api/studiov/livre-tech", json={}).status_code == 409 and local.delete("/api/studiov/livre-tech").status_code == 409
      and local.get("/api/studiov/ZZZ").status_code == 400 and local.put(f"/api/studiov/{cid}", content=b"{").status_code == 400)
check("6.7 fabrique absente -> 404 ; suppression", local.get(f"/api/studiov/{cid}/fabrique").status_code == 404
      and local.delete(f"/api/studiov/{cid}").json() == {"supprime": cid})

print("7. habillage")
from app.services import studiov_habillage as H                      # noqa: E402
h = S.normaliser({"piece": {"fond": "brique", "mur": "mur"},
                  "matieres": {"brique": {"texture": "cat:brick_wall_001", "usage": "mur"}, "a": {"texture": "stu:oak_veneer_01", "teinte": True, "usage": "bois"},
                               "b": {"texture": "mat:0123abcd"}, "c": {"texture": "C:/x/y.jpg"}, "d": {"texture": "http://x/y.jpg"}, "e": {"texture": "zzz:oak"},
                               "f": {"texture": "stu:../../etc", "teinte": "oui", "usage": "marbre"}, "g": {"texture": ["stu:oak"]}},
                  "objets": [{"type": "neon_texte", "texte": "ON\x00 AIR" + "x" * 40, "police": "Comic", "matiere2": "a"},
                             {"type": "bureau", "texte": "pirate", "police": "Monoton", "matiere2": "absente"},
                             {"type": "lettres_retro", "police": "Monoton"}],
                  "enseigne": {"style": "retro", "police": "Pacifico"}})
M = h["matieres"]
check("7.1 texture : références stu:, cat: et mat: gardées ; chemin, URL, préfixe inconnu, remontée et non-texte -> \"\"",
      [M[k]["texture"] for k in "abcdefg"] == ["stu:oak_veneer_01", "mat:0123abcd", "", "", "", "", ""] and M["brique"]["texture"] == "cat:brick_wall_001", M)
check("7.2 teinte : un vrai booléen seulement ; usage : choix fermé", M["a"]["teinte"] is True and M["f"]["teinte"] is False and M["f"]["usage"] == "autre"
      and M["a"]["usage"] == "bois" and M["sol"]["texture"] == "" and M["sol"]["usage"] == "autre")
check("7.3 mur du fond : une matière de la recette, sinon celle des murs", h["piece"]["fond"] == "brique" and S.normaliser({})["piece"]["fond"] == "mur"
      and S.normaliser({"piece": {"fond": "absente"}})["piece"]["fond"] == "mur")
O7 = h["objets"]
check("7.4 mot et police : aux seuls objets à mot, mot borné sans caractère de contrôle, police hors liste -> Inter",
      O7[0]["texte"] == ("ON AIR" + "x" * 40)[:S.MAX_MOT] and O7[0]["police"] == "Inter" and "texte" not in O7[1] and "police" not in O7[1]
      and O7[2]["texte"] == "" and O7[2]["police"] == "Monoton", O7)
check("7.5 matière secondaire : une clé de la recette, sinon rien", O7[0]["matiere2"] == "a" and O7[1]["matiere2"] is None)
check("7.6 enseigne : styles rétroéclairé et caisson, police embarquée", h["enseigne"]["style"] == "retro" and h["enseigne"]["police"] == "Pacifico"
      and S.normaliser({"enseigne": {"style": "caisson", "police": "x"}})["enseigne"] == dict(S.normaliser({})["enseigne"], style="caisson"))
check("7.7 normaliser reste idempotent avec l'habillage", S.normaliser(h) == h)
r = subprocess.run([sys.executable, str(REPO / "scripts" / "studiov" / "composer_textures.py"), "--check"], capture_output=True)
check("7.8 le pack d'intérieur livré concorde avec son catalogue (scripts/studiov/composer_textures.py --check)", r.returncode == 0, r.stdout[-300:])
T7 = H.textures()
refs = H.refs_livrees()
check("7.9 catalogue : 42 matières du studio + 30 de la Forge, chacune avec ses trois cartes, une taille et une référence valide",
      sum(t["source"] == "studio" for t in T7) == 42 and sum(t["source"] == "forge" for t in T7) == 30 and len(refs) == 72
      and all(S.REF_TEXTURE.match(t["ref"]) and set(t["cartes"]) >= {"basecolor"} and 0.05 <= t["taille_m"] <= 50 and t["nom"] and t["nom_en"] for t in T7)
      and all(set(t["cartes"]) == {"basecolor", "normal", "roughness"} and re.match(r"^#[0-9a-f]{6}$", t["moyenne"] or "") for t in T7 if t["source"] != "utilisateur"))
check("7.10 chaque carte du pack du studio existe sur le disque, vignette comprise", all(H.chemin_carte(t["ref"][4:], c).is_file()
      for t in T7 if t["source"] == "studio" for c in ("basecolor", "normal", "roughness", "vignette")))
coul = lambda v: v in ("principale", "accent", "texte", "fond") or bool(re.match(r"^#[0-9a-f]{6}$", v or ""))     # noqa: E731
amb = {a["id"] for a in H.AMBIANCES}
check("7.11 ambiances : couleurs valides, deux néons ou plus, identifiants uniques", len(amb) == len(H.AMBIANCES) >= 12
      and all(coul(a["cle"]) and coul(a["appoint"]) and coul(a["contre"]) and coul(a["ambiance"]) and len(a["neons"]) >= 2 and all(map(coul, a["neons"])) for a in H.AMBIANCES))
check("7.12 styles : une matière pour le sol, les murs, le plafond, le bois, le tissu, le cuir et le métal ; textures LIVRÉES ; ambiance connue",
      len({s["id"] for s in H.STYLES}) == len(H.STYLES) >= 12 and all(s["ambiance"] in amb and set(s["matieres"]) == {"sol", "mur", "plafond", "bois", "tissu", "cuir", "metal"}
      and all((not m["texture"] or m["texture"] in refs) and (m["texture"] or coul(m.get("couleur"))) and (not m["teinte"] or coul(m.get("couleur"))) for m in s["matieres"].values()) for s in H.STYLES))
check("7.13 finitions : couleur valide, rugosité et métal bornés, motif connu", all(coul(f["couleur"]) and 0 < f["rugosite"] <= 1 and 0 <= f["metal"] <= 1
      and f["motif"] in S.MOTIFS and set(f["usages"]) <= set(S.USAGES) for f in H.FINITIONS))
check("7.14 décors livrés : au moins une vraie texture chacun, toutes dans l'installeur, avec un repli (couleur) ; mots de 24 caractères au plus",
      all(any(m["texture"] for m in d["matieres"].values()) and all(not m["texture"] or m["texture"] in refs for m in d["matieres"].values())
          and all(len(o.get("texte", "")) <= S.MAX_MOT for o in d["objets"]) for d in L))
check("7.15 carte du pack : slug ou carte inconnus, remontée de dossier -> 404", all(_refus_h(H.chemin_carte, *a) == 404 for a in
      [("absente", "basecolor"), ("oak_veneer_01", "secret"), ("../textures", "basecolor"), ("oak_veneer_01/..", "basecolor"), (None, "basecolor")]))
check("7.16 vignette de la Forge : catalogue rendu en JPEG ; inconnue, source hostile -> 404", H.vignette("cat", "brick_wall_001")[:2] == b"\xff\xd8"
      and all(_refus_h(H.vignette, *a) == 404 for a in [("cat", "absente"), ("cat", "../x"), ("mat", "zzzzzzzz"), ("mat", "00000000"), ("disque", "brick_wall_001")]))
r = local.get("/api/studiov/habillage")
check("7.17 route du catalogue : textures, familles, finitions, ambiances, styles, catalogue ; hors boucle locale refusée", r.status_code == 200
      and set(r.json()) == {"textures", "familles_texture", "finitions", "ambiances", "styles", "catalogue", "objets", "images", "videos"} and len(r.json()["textures"]) >= 72
      and loin.get("/api/studiov/habillage").status_code in (401, 403))
check("7.18 route d'une carte : JPEG du pack ; carte inconnue 404 ; vignette de la Forge ; carte de la Forge par cette route 404 ; hors boucle refusé",
      local.get("/api/studiov/textures/stu/oak_veneer_01/normal.jpg").headers.get("content-type") == "image/jpeg"
      and local.get("/api/studiov/textures/stu/oak_veneer_01/secret.jpg").status_code == 404
      and local.get("/api/studiov/textures/stu/absente/basecolor.jpg").status_code == 404
      and local.get("/api/studiov/textures/cat/brick_wall_001/vignette.jpg").status_code == 200
      and local.get("/api/studiov/textures/cat/brick_wall_001/basecolor.jpg").status_code == 404
      and loin.get("/api/studiov/textures/stu/oak_veneer_01/normal.jpg").status_code in (401, 403))
c7 = local.post("/api/studiov", json={"base": "livre-tech"}).json()
doc7 = dict(c7); doc7["matieres"] = dict(c7["matieres"], sol=dict(c7["matieres"]["sol"], texture="cat:brushed_concrete", teinte=True, couleur="accent"))
e7 = local.put(f"/api/studiov/{c7['id']}", json=doc7).json()
check("7.19 un décor de l'espace garde l'habillage posé (texture, teinte, couleur du kit) et celui du livré copié",
      e7["matieres"]["sol"]["texture"] == "cat:brushed_concrete" and e7["matieres"]["sol"]["teinte"] is True and e7["matieres"]["sol"]["couleur"] == "accent"
      and e7["matieres"]["bois"]["texture"] == "stu:oak_veneer_01" and e7["piece"]["fond"] == "fond")

print("8. depuis Blender")
from PIL import Image                                                # noqa: E402
from app.services import material_store as MS                        # noqa: E402
blend = _tmp / "essai.blend"; blend.write_bytes(b"BLENDER-essai")
(_tmp / "note.txt").write_text("x", "utf-8")
check("8.1 chemin vide ou non-texte -> 400 ; fichier absent, autre extension -> 404", _refus_h(H.matieres_blender, "") == 400 and _refus_h(H.cuire_blender, None) == 400
      and _refus_h(H.matieres_blender, str(_tmp / "absent.blend")) == 404 and _refus_h(H.cuire_blender, str(_tmp / "note.txt")) == 404)
vrai_blender, vrai_lancer, appels = H._blender, H._lancer_blender, []
H._blender = lambda: "blender-de-banc"
argv_vus = []
_run = subprocess.run
def _faux_run(argv, **k):                                            # ce que _lancer_blender passe VRAIMENT à Blender
    argv_vus.append(list(argv))
    class R: stdout = 'MATIERES ["A", "B"]\n'
    return R()
H.subprocess.run = _faux_run
check("8.2 lister : Blender sans fenêtre, scripts du fichier coupés, le script de cuisson de l'application, puis --liste",
      H.matieres_blender(str(blend)) == ["A", "B"] and argv_vus[0][:4] == ["blender-de-banc", "--background", "--disable-autoexec", str(blend)]
      and argv_vus[0][4:] == ["--python", str(H.SCRIPT_CUISSON), "--", "--liste"], argv_vus)
H.subprocess.run = _run
def _fausse_cuisson(fichier, arguments):
    appels.append(list(arguments))
    sortie = pathlib.Path(arguments[arguments.index("--sortie") + 1])
    for nom in ("brique", "or"):
        (sortie / nom).mkdir(parents=True)
        Image.new("RGB", (512, 512), (150, 60, 40)).save(sortie / nom / "basecolor.png")
        Image.new("RGB", (512, 512), (128, 128, 255)).save(sortie / nom / "normal.png")
        Image.new("L", (512, 512), 200).save(sortie / nom / "roughness.png")
    Image.new("L", (512, 512), 255).save(sortie / "or" / "metallic.png")
    return 'bruit\nCUISSON_OK ' + json.dumps([{"nom": "Brique d'essai", "dossier": "brique"}, {"nom": "Or", "dossier": "or"},
                                               {"nom": "Pirate", "dossier": "../../ailleurs"}]) + "\n"
H._lancer_blender = _fausse_cuisson
faits = H.cuire_blender(str(blend), "Brique d'essai", 2)
check("8.3 cuire : deux matières rangées dans la Forge, le dossier hostile ignoré ; arguments : sortie jetable, taille, mètres bornés, matière",
      [x["nom"] for x in faits] == ["Brique d'essai", "Or"] and all(S.REF_TEXTURE.match(x["ref"]) and x["ref"] == "mat:" + x["id"][4:] for x in faits)
      and appels[0][2:] == ["--taille", "1024", "--metres", "2.0", "--matiere", "Brique d'essai"] and not pathlib.Path(appels[0][1]).exists(), (faits, appels))
m8 = MS.read_material(faits[1]["id"])
check("8.4 la matière de la Forge porte les cartes cuites (couleur, normale, rugosité, métal) et les dérivées ; sa source dit Blender",
      {"basecolor", "normal", "roughness", "metallic", "ao", "height"} <= set(m8["maps"]) and m8["source"]["kind"] == "upload"
      and m8["source"]["filename"] == "blender:essai.blend" and Image.open(MS.map_path(faits[1]["id"], "metallic")).convert("L").getpixel((5, 5)) == 255, m8.get("maps"))
t8 = {t["ref"]: t for t in H.textures()}
check("8.5 le décorateur la propose aussitôt : famille « Mes matières », trois cartes par les routes de la Forge, vignette",
      all(x["ref"] in t8 and t8[x["ref"]]["famille"] == "forge" and t8[x["ref"]]["source"] == "utilisateur" for x in faits)
      and t8[faits[0]["ref"]]["cartes"]["normal"] == f"/api/materials/{faits[0]['id']}/map/normal.png?res=1024"
      and H.vignette("mat", faits[0]["id"][4:])[:2] == b"\xff\xd8" and faits[0]["ref"] not in H.refs_livrees())
H._lancer_blender = lambda f, a: "Blender quit\n"
check("8.6 sortie sans marque -> 502 ; rien que des dossiers hostiles -> 502", _refus_h(H.cuire_blender, str(blend)) == 502)
H._lancer_blender = lambda f, a: 'CUISSON_OK [{"nom": "x", "dossier": "../x"}]\n'
check("8.7 dossier hors de la sortie : jamais lu", _refus_h(H.cuire_blender, str(blend)) == 502)
H._lancer_blender = _fausse_cuisson
r = local.post("/api/studiov/blender/cuire", json={"blend": str(blend), "matiere": "Or"})
check("8.8 routes : cuire -> {materials}, lister ; fichier absent 404 ; hors boucle locale refusé", r.status_code == 200 and len(r.json()["materials"]) == 2
      and local.post("/api/studiov/blender/matieres", json={"blend": str(_tmp / "absent.blend")}).status_code == 404
      and loin.post("/api/studiov/blender/cuire", json={"blend": str(blend)}).status_code in (401, 403), r.text[:200])
H._blender, H._lancer_blender = vrai_blender, vrai_lancer
src8 = H.SCRIPT_CUISSON.read_text("utf-8")
check("8.9 le script de cuisson est livré dans l'application, se compile, travaille sur une COPIE et n'enregistre jamais le fichier ouvert",
      H.SCRIPT_CUISSON.is_file() and compile(src8, "cuisson", "exec") is not None and "source.copy()" in src8 and "save_as_mainfile" not in src8
      and "save_mainfile" not in src8)

print("9. objets importés et atelier")
import struct                                                        # noqa: E402
from app.services import studiov_objets as OB                        # noqa: E402


def _refus_o(f, *a):
    try:
        f(*a)
    except OB.RefusObjet as e:
        return e.statut
    return None


def _glb(j, version=2):
    corps = json.dumps(j).encode("utf-8")
    corps += b" " * (-len(corps) % 4)
    return b"glTF" + struct.pack("<II", version, 20 + len(corps)) + struct.pack("<II", len(corps), 0x4E4F534A) + corps


CUBE = {"asset": {"version": "2.0"}, "accessors": [{"count": 36}, {"count": 24, "min": [-0.5, 0, -0.25], "max": [0.5, 2, 0.25]}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]}]}
check("9.1 un GLB sain est mesuré : triangles et dimensions", OB.analyser_glb(_glb(CUBE)) == {"triangles": 12, "dims": [1.0, 2.0, 0.5], "maillages": 1, "images": 0})
check("9.2 refusés avant toute écriture : pas un GLB, version 1, JSON cassé (415) ; trop gros (413)",
      [_refus_o(OB.analyser_glb, x) for x in (b"PK\x03\x04" + b"x" * 40, _glb(CUBE, 1), b"glTF" + struct.pack("<IIII", 2, 28, 8, 0x4E4F534A) + b"{pas du ", None)] == [415, 415, 415, 415]
      and _refus_o(OB.analyser_glb, b"glTF" + b"\0" * (OB.MAX_OCTETS + 8)) == 413)
check("9.3 refusés : compression que le moteur n'ouvre pas, fichier voisin (tampon ou image), aucune surface, trop de triangles",
      _refus_o(OB.analyser_glb, _glb(dict(CUBE, extensionsRequired=["KHR_draco_mesh_compression"]))) == 415
      and _refus_o(OB.analyser_glb, _glb(dict(CUBE, buffers=[{"uri": "scene.bin"}]))) == 415
      and _refus_o(OB.analyser_glb, _glb(dict(CUBE, images=[{"uri": "http://ailleurs/t.png"}]))) == 415
      and OB.analyser_glb(_glb(dict(CUBE, images=[{"uri": "data:image/png;base64,AAAA"}])))["images"] == 1
      and _refus_o(OB.analyser_glb, _glb({"asset": {}, "meshes": []})) == 415
      and _refus_o(OB.analyser_glb, _glb(dict(CUBE, accessors=[{"count": 3 * (OB.MAX_TRIANGLES + 1)}, CUBE["accessors"][1]]))) == 413)
check("9.4 licence retenue : CC0 et CC BY sous toutes leurs écritures ; BlenderKit = Royalty Free sauf CC0 ; création ; inconnue = à vérifier",
      [OB.licence_propre(*x) for x in (("cc0 1.0", "polypizza"), ("CC-BY-4.0", "sketchfab"), ("CC BY 3.0", "polypizza"), ("Royalty Free", "blenderkit"),
                                        ("CC0", "blenderkit"), ("n'importe", "creation"), ("", "fichier"), ("GPL", "fichier"))]
      == ["CC0", "CC-BY", "CC-BY", "BLENDERKIT-RF", "CC0", "CREATION", "A-VERIFIER", "A-VERIFIER"])
check("9.5 licences refusées (409) : usage commercial interdit, modification interdite, partage à l'identique, fichier non extractible",
      all(_refus_o(OB.licence_propre, x, "sketchfab") == 409 for x in ("CC BY-NC 4.0", "cc-by-nd", "CC-BY-SA-4.0", "CC-BY-NC-SA", "Standard")))
check("9.6 droits : CC0 tout ; CC BY tout + crédit ; BlenderKit ni export ni partage ; à vérifier : vidéo non affirmée",
      OB.droits("CC0") == {"video": True, "export": True, "partage": True, "credit": False} and OB.droits("CC-BY")["credit"] is True
      and OB.droits("BLENDERKIT-RF") == {"video": True, "export": False, "partage": False, "credit": False}
      and OB.droits("A-VERIFIER")["video"] is None and OB.droits("inconnue") == OB.droits("A-VERIFIER"))
o1 = OB.importer(_glb(CUBE), {"nom": "Lampe  de\x00 studio", "source": "polypizza", "licence": "CC-BY 3.0", "auteur": "Jeanne Martin", "url": "https://poly.pizza/m/abc"})
o2 = OB.importer(_glb(CUBE), {"nom": "Fauteuil", "source": "blenderkit", "licence": "Royalty Free", "url": "javascript:alert(1)"})
o3 = OB.importer(_glb(CUBE), {"source": "disque C:", "licence": "?"})
check("9.7 importer : fiche propre (nom sans contrôle, source fermée, adresse http(s) seulement), référence obj:, droits, GLB sur le disque",
      o1["nom"] == "Lampe de studio" and o1["ref"] == "obj:" + o1["id"] and S.REF_OBJET.match(o1["ref"]) and o1["licence"] == "CC-BY" and o1["droits"]["credit"]
      and o1["url"] == "https://poly.pizza/m/abc" and o2["url"] == "" and o2["licence"] == "BLENDERKIT-RF" and o3["source"] == "fichier" and o3["licence"] == "A-VERIFIER"
      and o3["nom"] == "Objet importé" and OB.chemin(o1["id"]).read_bytes()[:4] == b"glTF" and o1["triangles"] == 12 and o1["lourd"] is False, (o1, o2, o3))
check("9.8 une licence refusée ou un fichier illisible ne laissent rien sur le disque", _refus_o(OB.importer, _glb(CUBE), {"licence": "CC-BY-NC"}) == 409
      and _refus_o(OB.importer, b"pas un glb", {"licence": "CC0"}) == 415 and len(OB.lister()) == 3 and len(list(OB.racine().iterdir())) == 3)
check("9.9 bibliothèque : liste, index par référence ; identifiant hostile 400, inconnu 404", set(OB.index()) == {o1["ref"], o2["ref"], o3["ref"]}
      and all(_refus_o(OB.lire, x) == 400 for x in ("../x", "ABC", "", None, "0" * 15)) and _refus_o(OB.lire, "0" * 16) == 404 and _refus_o(OB.chemin, "0" * 16) == 404)
r9 = S.normaliser({"piece": {"gauche": "brique", "droite": "absente"}, "matieres": {"brique": {}},
                   "objets": [{"type": "modele", "ref": o1["ref"], "x": 1}, {"type": "modele", "ref": "C:/x.glb"}, {"type": "modele", "ref": "obj:../../x"},
                              {"type": "modele"}, {"type": "bureau", "ref": o1["ref"]}]})
check("9.10 recette : un objet « modele » est gardé par sa référence seule ; sans référence valide il n'est rien ; un autre type n'en porte pas",
      [(o["type"], o.get("ref")) for o in r9["objets"]] == [("modele", o1["ref"]), ("bureau", None)] and S.normaliser(r9) == r9)
check("9.11 recette : chaque pan de mur a sa matière (défaut : celle des murs) ; 48 matières au plus", r9["piece"]["gauche"] == "brique" and r9["piece"]["droite"] == "mur"
      and S.normaliser({})["piece"]["gauche"] == "mur" and S.MAX_MATIERES == 48
      and len(S.normaliser({"matieres": {f"m{i}": {} for i in range(90)}})["matieres"]) <= 51)
dc = S.creer(None, "Décor aux objets", "esp-o")
dc = S.enregistrer(dc["id"], dict(dc, objets=[{"type": "modele", "ref": o1["ref"]}, {"type": "modele", "ref": o1["ref"], "x": 1}, {"type": "modele", "ref": o2["ref"]},
                                             {"type": "modele", "ref": o3["ref"]}, {"type": "modele", "ref": "obj:" + "f" * 16}, {"type": "bureau"}]))
cr = OB.credits(dc)
check("9.12 crédits : un modèle cité une fois, les obligatoires d'abord, le texte FR et EN prêts ; l'objet disparu est compté",
      [x["nom"] for x in cr["lignes"]][0] == "Lampe de studio" and len(cr["lignes"]) == 3 and cr["absents"] == 1
      and cr["texte_fr"] == "Crédits du décor :\n- « Lampe de studio » par Jeanne Martin (CC BY) via Poly Pizza — https://poly.pizza/m/abc\n- « Objet importé »"
      and cr["texte_en"].startswith("Set credits:\n- \"Lampe de studio\" by Jeanne Martin (CC BY) via Poly Pizza"), cr)
check("9.13 droits du décor entier : un objet BlenderKit interdit l'export et le partage ; la licence à vérifier est signalée",
      cr["export"] is False and cr["partage"] is False and cr["a_verifier"] == ["Objet importé"] and OB.credits(dict(dc, objets=[]))["export"] is True
      and OB.credits(dict(dc, objets=[]))["texte_fr"] == "")
check("9.14 supprimer : refusé tant qu'un décor l'emploie (409), permis ensuite ; inconnu 404", _refus_o(OB.supprimer, o2["id"]) == 409
      and _refus_o(OB.supprimer, "0" * 16) == 404)
S.enregistrer(dc["id"], dict(dc, objets=[{"type": "modele", "ref": o1["ref"]}]))
OB.supprimer(o2["id"])
check("9.15 … l'objet retiré du décor se supprime ; les autres restent", _refus_o(OB.lire, o2["id"]) == 404 and len(OB.lister()) == 2)
r = local.get("/api/studiov/objets")
check("9.16 routes : la bibliothèque, ses sources, ses licences et leurs droits ; hors boucle locale refusée", r.status_code == 200 and len(r.json()["objets"]) == 2
      and r.json()["licences"]["CC-BY"]["credit"] is True and "polypizza" in r.json()["sources"] and loin.get("/api/studiov/objets").status_code in (401, 403))
r = local.post("/api/studiov/objets", files={"fichier": ("Vase bleu.glb", _glb(CUBE), "model/gltf-binary")}, data={"source": "sketchfab", "licence": "CC0", "auteur": "A"})
oid = r.json().get("id", "")
check("9.17 routes : import d'un fichier (le nom vient du fichier), lecture du GLB, refus d'une licence (409) et d'un faux GLB (415)",
      r.status_code == 200 and r.json()["nom"] == "Vase bleu" and r.json()["licence"] == "CC0"
      and local.get(f"/api/studiov/objets/{oid}/modele.glb").content[:4] == b"glTF"
      and local.post("/api/studiov/objets", files={"fichier": ("x.glb", _glb(CUBE))}, data={"licence": "CC-BY-NC"}).status_code == 409
      and local.post("/api/studiov/objets", files={"fichier": ("x.glb", b"zip")}, data={"licence": "CC0"}).status_code == 415
      and local.get("/api/studiov/objets/ZZZ/modele.glb").status_code == 400, r.text[:200])
check("9.18 routes : crédits d'un décor ; suppression (409 s'il est posé, puis 200)", local.get(f"/api/studiov/{dc['id']}/credits").status_code in (200, 409)
      and local.delete(f"/api/studiov/objets/{oid}").json() == {"supprime": oid} and local.delete(f"/api/studiov/objets/{oid}").status_code == 404)
m = local.get("/api/studiov/three/GLTFLoader.js")
check("9.19 chargeur three.js : servi avec ses imports réécrits vers les fichiers de l'application ; liste FERMÉE (remontée de dossier, autre module : 404)",
      m.status_code == 200 and "javascript" in m.headers["content-type"] and "from '/assets/three/three.module.min.js'" in m.text and "from 'three'" not in m.text
      and "'/api/studiov/three/BufferGeometryUtils.js'" in m.text and "from 'three'" not in local.get("/api/studiov/three/SkeletonUtils.js").text
      and local.get("/api/studiov/three/OrbitControls.js").status_code == 404 and local.get("/api/studiov/three/..%2f..%2fx.js").status_code == 404
      and loin.get("/api/studiov/three/GLTFLoader.js").status_code in (401, 403))
appels9 = []
def _faux_export(fichier, arguments, script=None):
    appels9.append((list(arguments), script))
    if "--liste" in arguments:
        return 'OBJETS [{"nom": "Fauteuil club", "faces": 1200}, {"nom": "Lampe", "faces": 90}, "pirate"]\n'
    sortie = pathlib.Path(arguments[arguments.index("--sortie") + 1])
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "fauteuil_club.glb").write_bytes(_glb(CUBE))
    return 'EXPORT_OK {"nom": "Fauteuil club", "fichier": "fauteuil_club.glb"}\n'
H._blender, H._lancer_blender = (lambda: "blender-de-banc"), _faux_export
check("9.20 depuis Blender : lister les objets d'un fichier (script d'export de l'application)", H.objets_blender(str(blend)) == [{"nom": "Fauteuil club", "faces": 1200}, {"nom": "Lampe", "faces": 90}]
      and appels9[0] == (["--liste"], H.SCRIPT_EXPORT))
ex = H.exporter_blender(str(blend), "Fauteuil club", {"source": "blenderkit", "licence": "Royalty Free", "auteur": "B"})
check("9.21 depuis Blender : l'objet sorti entre dans la bibliothèque avec ses droits (un asset BlenderKit : ni export ni partage) ; le dossier de travail est ôté",
      ex["nom"] == "Fauteuil club" and ex["source"] == "blenderkit" and ex["licence"] == "BLENDERKIT-RF" and ex["droits"]["export"] is False
      and appels9[1][0][2:] == ["--objet", "Fauteuil club"] and not pathlib.Path(appels9[1][0][1]).exists() and OB.chemin(ex["id"]).is_file(), ex)
H._lancer_blender = lambda f, a, s=None: 'EXPORT_OK {"nom": "x", "fichier": "../../ailleurs.glb"}\n'
check("9.22 fichier hors du dossier de travail, objet non choisi, fichier absent : refusés", _refus_h(H.exporter_blender, str(blend), "x") == 502
      and _refus_h(H.exporter_blender, str(blend), "") == 400 and _refus_h(H.objets_blender, str(_tmp / "absent.blend")) == 404)
H._blender, H._lancer_blender = vrai_blender, vrai_lancer
src9 = H.SCRIPT_EXPORT.read_text("utf-8")
check("9.23 le script d'export est livré dans l'application, se compile, n'enregistre jamais le fichier ouvert et coupe la compression",
      H.SCRIPT_EXPORT.is_file() and compile(src9, "export", "exec") is not None and "save_as_mainfile" not in src9 and "save_mainfile" not in src9
      and "export_draco_mesh_compression_enable" in src9)

print("10. depuis la Bibliothèque de l'application")
from app.config import settings as _reglages                         # noqa: E402
from app.services import studiov_images as SI                        # noqa: E402


def _refus_i(f, *a):
    try:
        f(*a)
    except SI.RefusImage as e:
        return e.statut
    return None


BIB = _reglages.images_path
BIB.mkdir(parents=True, exist_ok=True)
Image.new("RGB", (3000, 1500), (30, 90, 160)).save(BIB / "gen_illustration.png")
logo = Image.new("RGBA", (600, 600), (0, 0, 0, 0)); logo.paste((240, 180, 41, 255), (150, 150, 450, 450)); logo.save(BIB / "gen_logo.png")
Image.new("RGBA", (400, 300), (200, 30, 50, 255)).save(BIB / "opaque.png")
(BIB / "note.txt").write_text("x", "utf-8"); (BIB / "faux.png").write_bytes(b"pas une image")
check("10.1 une image est désignée par son NOM seul : chemin, remontée, autre extension, absente, non-texte -> refus",
      [_refus_i(SI.fichier_bibliotheque, x) for x in ("../gen_logo.png", str(BIB / "gen_logo.png"), "note.txt", "absente.png", "", None, 12)] == [400, 400, 404, 404, 400, 400, 400])
i1 = SI.depuis_bibliotheque("gen_illustration.png", {"licence": "propriétaire", "auteur": ""})
i2 = SI.depuis_bibliotheque("gen_logo.png", {"licence": "CC BY 4.0", "auteur": "Studio Martin"})
i3 = SI.depuis_bibliotheque("opaque.png", {"licence": "inconnue"})
check("10.2 copie : ramenée à 2 048 px (JPEG), le logo garde sa transparence (PNG), une couche alpha toute opaque n'en est pas une",
      (i1["l"], i1["h"], i1["alpha"]) == (2048, 1024, False) and SI.chemin(i1["id"]).name == "image.jpg" and (i2["l"], i2["alpha"]) == (600, True)
      and SI.chemin(i2["id"]).name == "image.png" and Image.open(SI.chemin(i2["id"])).mode == "RGBA" and i3["alpha"] is False and S.REF_IMAGE.match(i1["ref"]), (i1, i2, i3))
check("10.3 la même image, inchangée, n'est copiée qu'une fois ; la fiche garde l'origine, la licence et l'auteur de la Bibliothèque",
      SI.depuis_bibliotheque("gen_logo.png")["id"] == i2["id"] and len(SI.lister()) == 3 and i2["origine"] == "gen_logo.png" and i2["licence"] == "CC BY 4.0"
      and i2["auteur"] == "Studio Martin" and i1["nom"] == "gen_illustration")
check("10.4 fichier illisible -> 415, rien n'est écrit ; identifiant hostile 400, inconnu 404", _refus_i(SI.depuis_bibliotheque, "faux.png") == 415 and len(SI.lister()) == 3
      and all(_refus_i(SI.lire, x) == 400 for x in ("../x", "", None)) and _refus_i(SI.lire, "0" * 16) == 404 and _refus_i(SI.chemin, "0" * 16) == 404)
check("10.5 vignette d'une image de la Bibliothèque : JPEG ; fichier hostile ou illisible refusé", SI.vignette_bibliotheque("gen_logo.png")[:2] == b"\xff\xd8"
      and _refus_i(SI.vignette_bibliotheque, "../x.png") == 400 and _refus_i(SI.vignette_bibliotheque, "faux.png") == 415)
r10 = S.normaliser({"objets": [{"type": "tableau", "image": i1["ref"]}, {"type": "logo_mural", "image": i2["ref"], "couleur": "accent"}, {"type": "kakemono", "image": i3["ref"]},
                               {"type": "tableau"}, {"type": "tableau", "image": "C:/x.png"}, {"type": "logo_mural", "image": "http://x/y.png"}, {"type": "bureau", "image": i1["ref"]}],
                    "ecrans": [{"source": "image", "image": i1["ref"]}, {"source": "image", "image": "../x"}, {}],
                    "enseigne": {"source": "image", "image": i2["ref"]}})
check("10.6 recette : tableau, logo mural et kakémono gardés par leur référence ; sans image valide ils ne sont rien ; un autre type n'en porte pas",
      [(o["type"], o.get("image")) for o in r10["objets"]] == [("tableau", i1["ref"]), ("logo_mural", i2["ref"]), ("kakemono", i3["ref"]), ("bureau", None)] and S.normaliser(r10) == r10)
check("10.7 recette : image d'un écran du décor et de l'enseigne par référence ; « image » sans image = le logo de l'espace",
      [e["image"] for e in r10["ecrans"]] == [i1["ref"], "", ""] and r10["enseigne"]["source"] == "image" and r10["enseigne"]["image"] == i2["ref"]
      and S.normaliser({"enseigne": {"source": "image"}})["enseigne"]["source"] == "espace" and S.normaliser({"enseigne": {"source": "image", "image": "x"}})["enseigne"]["source"] == "espace")
di = S.creer(None, "Décor aux images", "esp-i")
di = S.enregistrer(di["id"], dict(di, objets=[{"type": "tableau", "image": i1["ref"]}, {"type": "logo_mural", "image": i2["ref"]}], ecrans=[{"source": "image", "image": i3["ref"]}]))
ci = OB.credits(di)
check("10.8 crédits : l'image à l'utilisateur n'est pas citée ; la CC BY l'est avec son auteur ; la licence inconnue est à vérifier",
      [x["nom"] for x in ci["lignes"]] == ["gen_logo", "opaque"] and ci["texte_fr"] == "Crédits du décor :\n- « gen_logo » par Studio Martin (CC BY)"
      and ci["a_verifier"] == ["opaque"] and ci["export"] is True, ci)
check("10.9 supprimer une image : refusé tant qu'un décor l'emploie (objet, écran), permis ensuite", _refus_i(SI.supprimer, i1["id"]) == 409 and _refus_i(SI.supprimer, i3["id"]) == 409
      and SI.emplois(di) == {i1["ref"], i2["ref"], i3["ref"]})
S.enregistrer(di["id"], dict(di, objets=[], ecrans=[]))
SI.supprimer(i3["id"])
check("10.10 … l'image retirée du décor se supprime", _refus_i(SI.lire, i3["id"]) == 404 and len(SI.lister()) == 2)
J = _reglages.outputs_path / "assets3d"
(J / "job1").mkdir(parents=True); (J / "job1" / "model.glb").write_bytes(_glb(CUBE)); (J / "job1" / "model.v2.glb").write_bytes(_glb(CUBE) + b"    ")
(J / "job1" / "asset.json").write_text(json.dumps({"name": "Robot généré", "engine": "meshy"}), "utf-8")
(J / "job2").mkdir(); (J / "job2" / "model.glb").write_bytes(_glb(dict(CUBE, accessors=[{"count": 3 * (OB.MAX_TRIANGLES + 1)}, CUBE["accessors"][1]])))
(J / "job2" / "model.opt.glb").write_bytes(_glb(CUBE)); (J / "_banc").mkdir()
m1 = OB.depuis_bibliotheque("job1")
check("10.11 modèle 3D généré : copié dans les objets du studio, à l'utilisateur (tous droits, rien à citer), la DERNIÈRE version, une seule fois",
      m1["nom"] == "Robot généré" and m1["source"] == "bibliotheque" and m1["licence"] == "CREATION" and m1["droits"] == OB.droits("CREATION")
      and OB._fiche(m1["id"])["origine"].startswith("assets3d:job1:model.v2.glb:") and OB.depuis_bibliotheque("job1")["id"] == m1["id"])
m2 = OB.depuis_bibliotheque("job2")
check("10.12 la version allégée passe d'abord (le modèle plein dépasserait le plafond de triangles) ; une version nommée se demande ; trop lourde : 413",
      OB._fiche(m2["id"])["origine"].startswith("assets3d:job2:model.opt.glb:") and _refus_o(OB.depuis_bibliotheque, "job2", "model.glb") == 413
      and OB._fiche(OB.depuis_bibliotheque("job1", "model.glb")["id"])["origine"].startswith("assets3d:job1:model.glb:"))
check("10.13 job hostile, réservé, absent, fichier hors convention -> 404", all(_refus_o(OB.depuis_bibliotheque, *x) == 404 for x in
      (("../job1",), ("_banc",), ("absent",), ("",), (None,), ("job1", "../asset.json"), ("job1", "asset.json"), ("job1", "model.v9.glb"))))
r = local.post("/api/studiov/bibliotheque/image", json={"filename": "gen_illustration.png"})
check("10.14 routes : copie d'une image (déjà copiée : la même), son fichier, sa vignette ; nom hostile 400 ; hors boucle locale refusé",
      r.status_code == 200 and r.json()["id"] == i1["id"] and local.get(f"/api/studiov/images/{i1['id']}/fichier").headers["content-type"] == "image/jpeg"
      and local.get(f"/api/studiov/images/{i2['id']}/fichier").headers["content-type"] == "image/png"
      and local.get("/api/studiov/bibliotheque/vignette", params={"f": "gen_logo.png"}).content[:2] == b"\xff\xd8"
      and local.post("/api/studiov/bibliotheque/image", json={"filename": "../x.png"}).status_code == 400
      and local.get("/api/studiov/bibliotheque/vignette", params={"f": "absente.png"}).status_code == 404
      and loin.post("/api/studiov/bibliotheque/image", json={"filename": "gen_logo.png"}).status_code in (401, 403), r.text[:200])
check("10.15 routes : copie d'un modèle 3D généré ; job absent 404 ; suppression d'une image posée 409 ; le catalogue liste images et objets",
      local.post("/api/studiov/bibliotheque/modele", json={"job": "job1"}).json()["id"] == m1["id"]
      and local.post("/api/studiov/bibliotheque/modele", json={"job": "absent"}).status_code == 404
      and local.delete(f"/api/studiov/images/{i1['id']}").status_code in (200, 409)
      and {x["ref"] for x in local.get("/api/studiov/habillage").json()["objets"]} >= {m1["ref"], m2["ref"]}
      and i2["ref"] in {x["ref"] for x in local.get("/api/studiov/habillage").json()["images"]})

print("11. catalogue de produits réels")
from app.services import studiov_catalogue as CA                     # noqa: E402


def _refus_c(f, *a):
    try:
        f(*a)
    except CA.RefusCatalogue as e:
        return e.statut
    return None


def _ligne(pid, nom, typ, tri=1200, octets=None, mini=(-0.5, 0, -0.4), dims=(1.0, 0.9, 0.8), **k):
    return dict({"id": pid, "file": f"objects/{pid}/{pid}.glb", "name": nom, "product_type": typ, "brand": "Rivet", "color": "Denim",
                 "material": "Wood", "style": None, "size_metres": list(dims), "bounds_min": list(mini), "triangles": tri,
                 "pack_bytes": octets if octets is not None else 1000}, **k)


# un produit comme ceux du catalogue : compressé en Meshopt, quantifié (ses mètres ne viennent que de son nœud)
PRODUIT = {"asset": {"version": "2.0"}, "extensionsUsed": ["EXT_meshopt_compression", "EXT_texture_webp", "KHR_mesh_quantization"],
           "extensionsRequired": ["EXT_meshopt_compression", "EXT_texture_webp", "KHR_mesh_quantization"],
           "buffers": [{"byteLength": 8}, {"byteLength": 8, "extensions": {"EXT_meshopt_compression": {"fallback": True}}}],
           "accessors": [{"count": 36}, {"count": 24, "min": [0, 0, 0], "max": [1000, 2000, 500]}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]}],
           "nodes": [{"children": [1], "translation": [0, 0.1, 0]}, {"mesh": 0, "scale": [0.001, 0.001, 0.001], "translation": [-0.5, 0, -0.25]}],
           "scenes": [{"nodes": [0]}], "scene": 0}
GLB_PRODUIT = _glb(PRODUIT)
WEBP = b"RIFF" + struct.pack("<I", 20) + b"WEBPVP8 " + b"\0" * 12
lignes = [_ligne("B000000001", "Amazon Brand – Rivet North End Wood Accent Living Room Arm Chair with Tufted Back and Brass Legs, 38\"W, Denim", "chair", octets=len(GLB_PRODUIT)),
          _ligne("B000000002", "Stone & Beam Westport Modern Nailhead Upholstered Sofa", "home furniture and decor"),
          _ligne("B000000003", "Watercolor Green Leaf Print Wall Art", "wall art", mini=(-0.15, -0.15, 0), dims=(0.3, 0.3, 0.04), octets=len(GLB_PRODUIT)),
          _ligne("B000000004", "Glass Globe Pendant", "light fixture", mini=(-0.2, -1.7, -0.2), dims=(0.4, 1.7, 0.4)),
          _ligne("B000000005", "Velvet Throw Pillow", "pillow", mini=(-0.2, -0.2, 0), dims=(0.4, 0.4, 0.15)),
          _ligne("B000000006", "Widget 3000", "biss"), _ligne("B000000013", "Brass Candle Holder", "candle holder"),
          _ligne("B000000007", "Trop de triangles", "chair", tri=OB.MAX_TRIANGLES + 1), _ligne("B000000008", "Trop lourd", "chair", octets=OB.MAX_OCTETS + 1),
          _ligne("B000000009", "Fichier ailleurs", "chair", file="objects/../x.glb"), _ligne("../../x", "Identifiant hostile", "chair"),
          _ligne("B000000001", "Doublon", "sofa"), _ligne("B000000010", "", "chair"), _ligne("B000000011", "Sans taille", "chair", size_metres="grand"),
          _ligne("B000000012", "Triangles en texte", "chair", tri="12")]
lignes += [_ligne(f"B1{i:08d}", f"Dining Chair {i:03d}", "chair") for i in range(60)] + [_ligne(f"B2{i:08d}", f"Table Lamp {i:03d}", "lamp") for i in range(50)]
LISTE = b"\n".join(json.dumps(x).encode("utf-8") for x in lignes) + b"\n{pas du json\n\n[1, 2]\n"
reseau, sorties = {"metadata.jsonl": LISTE, "thumbs/B000000001.webp": WEBP, "thumbs/B000000002.webp": b"<html>pas une image</html>",
                   "objects/B000000001/B000000001.glb": GLB_PRODUIT, "objects/B000000003/B000000003.glb": GLB_PRODUIT,
                   "objects/B000000002/B000000002.glb": GLB_PRODUIT, "objects/B200000000/B200000000.glb": b"x" * 1000,
                   "objects/B000000013/B000000013.glb": b"x" * 1000}, []
def _faux_reseau(chemin, maximum):
    sorties.append(chemin)
    if chemin not in reseau:
        raise CA.RefusCatalogue("Ce fichier n'est plus dans le catalogue en ligne.", 404)
    return reseau[chemin]
vrai_reseau, CA._telecharger = CA._telecharger, _faux_reseau
check("11.1 rien sans le geste « Charger » : état vide, recherche, vignette et pose refusées (409) ; identifiant hostile 400 ; aucune sortie",
      CA.etat()["pret"] is False and CA.etat()["total"] == 0 and _refus_c(CA.chercher, "chaise") == 409 and _refus_c(CA.vignette, "B000000001") == 409
      and _refus_c(CA.poser, "B000000001") == 409 and all(_refus_c(CA.poser, x) == 400 for x in ("../x", "b000000001", "B0000", None, 12, "B000000001/..")) and sorties == [])
check("11.2 un modèle compressé en Meshopt est accepté, et mesuré en mètres avec les transformations de ses nœuds ; Draco et Basis restent refusés",
      OB.analyser_glb(GLB_PRODUIT) == {"triangles": 12, "dims": [1.0, 2.0, 0.5], "maillages": 1, "images": 0}
      and _refus_o(OB.analyser_glb, _glb(dict(CUBE, extensionsRequired=["KHR_texture_basisu"]))) == 415
      and OB.analyser_glb(_glb(dict(CUBE, nodes=[{"mesh": 0, "matrix": [2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 5, 0, 0, 1]}], scenes=[{"nodes": [0]}])))["dims"] == [2.0, 2.0, 0.5]
      and OB.analyser_glb(_glb(dict(CUBE, nodes=[{"mesh": 0, "children": [0], "scale": "x"}], scenes=[{"nodes": [0]}])))["dims"] == [1.0, 2.0, 0.5]
      # des entiers « normalisés » (16 bits signés) : la valeur est l'entier / 32 767, puis l'échelle du nœud
      and OB.analyser_glb(_glb(dict(CUBE, accessors=[{"count": 36}, {"count": 24, "componentType": 5122, "normalized": True, "min": [-32767, -32767, -16384], "max": [32767, 32767, 16383]}],
                                    nodes=[{"mesh": 0, "scale": [0.8, 0.5, 0.4], "translation": [0, 0.5, 0]}], scenes=[{"nodes": [0]}])))["dims"] == [1.6, 1.0, 0.4])
e11 = CA.charger()
ind = json.loads((CA.racine() / "index.json").read_text("utf-8"))
check("11.3 charger : la liste devient l'index (117 produits ; hostiles, trop lourds, en double, sans nom ni taille écartés), gardé avec sa révision",
      e11["pret"] is True and e11["total"] == 117 and sorties == ["metadata.jsonl"] and ind["revision"] == CA.REVISION and len(ind["produits"]) == 117
      and not {"B000000007", "B000000008", "B000000009", "B000000010", "B000000011", "B000000012"} & {p["id"] for p in ind["produits"]}
      and [p["nom"] for p in ind["produits"] if p["id"] == "B000000001"][0].startswith("Amazon Brand"), e11)
par = {p["id"]: p for p in ind["produits"]}
check("11.4 famille : d'après le type d'Amazon ; un type vague est rangé d'après le nom du produit ; sinon « Autres » ; les familles servies ont leur nom FR et EN",
      par["B000000001"]["famille"] == "sieges" and par["B000000002"]["famille"] == "canapes" and par["B000000006"]["famille"] == "divers"
      and [(x["id"], x["n"]) for x in e11["familles"]] == [("sieges", 61), ("canapes", 1), ("luminaires", 52), ("mural", 1), ("textiles", 1), ("divers", 1)]
      and all(x["nom"] and x["nom_en"] for x in e11["familles"]) and all(t[0] in CA.FAMILLES for t in CA.TYPES.values()), e11["familles"])
check("11.5 pose d'après l'origine du fichier : base à y = 0 -> sol ; centré -> mur ; pendu -> plafond ; un coussin centré se pose au sol",
      [par[k]["pose"] for k in ("B000000001", "B000000003", "B000000004", "B000000005")] == ["sol", "mur", "plafond", "sol"])
r11 = CA.chercher("chaise", None, 1)
check("11.6 recherche : en français (« chaise ») comme en anglais, tous les mots exigés, par famille, 24 par page, page bornée, famille hostile ignorée",
      r11["total"] == 61 and r11["pages"] == 3 and len(r11["resultats"]) == 24 and CA.chercher("CHAIR dining 007")["total"] == 1
      and CA.chercher("lampe", "sieges")["total"] == 0 and CA.chercher("", "luminaires")["total"] == 52 and CA.chercher("", "../x")["total"] == 117
      and CA.chercher("", None, 99)["page"] == 5 and CA.chercher("", None, "x")["page"] == 1 and CA.chercher("zzz")["resultats"] == []
      and r11["resultats"][0]["libelle"] == "Chaise" and r11["resultats"][0]["libelle_en"] == "Chair" and r11["resultats"][0]["deja"] is None
      and r11["resultats"][0]["vignette"].startswith("/api/studiov/catalogue/vignette/"))
sorties.clear()
check("11.7 vignette : téléchargée une fois puis gardée ; une réponse qui n'est pas une image WebP est refusée (502) ; produit inconnu 404, absent en ligne 404",
      CA.vignette("B000000001") == WEBP and CA.vignette("B000000001") == WEBP and sorties == ["thumbs/B000000001.webp"]
      and _refus_c(CA.vignette, "B000000002") == 502 and not (CA.racine() / "vignettes" / "B000000002.webp").exists()
      and _refus_c(CA.vignette, "B999999999") == 404 and _refus_c(CA.vignette, "B000000004") == 404)
sorties.clear()
avant11 = len(OB.lister())
p1 = CA.poser("B000000001")
check("11.8 poser : UN fichier demandé (objects/<id>/<id>.glb), rangé dans les objets avec sa licence CC BY, son auteur, sa pose, son titre entier et un nom court",
      sorties == ["objects/B000000001/B000000001.glb"] and p1["source"] == "abo" and p1["licence"] == "CC-BY" and p1["droits"] == {"video": True, "export": True, "partage": True, "credit": True}
      and p1["auteur"] == "Amazon.com" and p1["pose"] == "sol" and p1["titre"].startswith("Amazon Brand – Rivet North End") and p1["titre"].endswith("Denim")
      and len(p1["nom"]) <= OB.MAX_NOM and p1["nom"].startswith("Rivet North End") and p1["nom"].endswith("…") and p1["url"] == CA.PAGE
      and S.REF_OBJET.match(p1["ref"]) and OB.chemin(p1["id"]).read_bytes() == GLB_PRODUIT and p1["dims"] == [1.0, 2.0, 0.5], p1)
p3 = CA.poser("B000000003")
check("11.9 le même produit n'entre qu'une fois (aucun second téléchargement) ; un produit de mur garde sa pose ; la recherche dit ce qui est déjà là",
      CA.poser("B000000001")["id"] == p1["id"] and sorties.count("objects/B000000001/B000000001.glb") == 1 and len(OB.lister()) == avant11 + 2
      and p3["pose"] == "mur" and CA.chercher("B000000001")["resultats"][0]["deja"] == p1["ref"] and OB.par_origine("abo:") == {"abo:B000000001": p1["ref"], "abo:B000000003": p3["ref"]})
check("11.10 un fichier d'une autre taille que celle de l'index n'est pas gardé (502) ; un produit absent en ligne : 404 ; rien n'est écrit",
      _refus_c(CA.poser, "B000000002") == 502 and _refus_c(CA.poser, "B000000004") == 404 and len(OB.lister()) == avant11 + 2)
check("11.10b un luminaire du catalogue est lumineux (la recherche et la fiche le disent) ; un bougeoir, un siège, un fichier importé à la main ne le sont pas",
      [x["lumineux"] for x in CA.chercher("table lamp 007")["resultats"]] == [True] and CA.chercher("candle")["resultats"][0]["lumineux"] is False
      and CA._lumineux({"famille": "luminaires", "type": "candle holder", "nom": "Raffia Ceiling Hanging Pendant"}) is True
      and CA._lumineux({"famille": "tables", "type": "table", "nom": "Lamp Table"}) is False
      and p1["lumineux"] is False and o1["lumineux"] is False and OB.importer(_glb(CUBE), {"source": "abo", "lumineux": True, "origine": "abo:BLAMPE0001"})["lumineux"] is True
      and OB.importer(_glb(CUBE), {"lumineux": "oui"})["lumineux"] is False)
dc11 = S.creer(None, "Décor du catalogue", "esp-c")
dc11 = S.enregistrer(dc11["id"], dict(dc11, objets=[{"type": "modele", "ref": p1["ref"]}, {"type": "modele", "ref": p3["ref"]}, {"type": "modele", "ref": o1["ref"]}]))
cr11 = OB.credits(dc11)
check("11.11 crédits : les produits du catalogue tiennent en UNE ligne (titres, Amazon.com, CC BY 4.0 et son adresse, fichiers modifiés, adresse du dépôt), en FR et en EN",
      cr11["texte_fr"].count("\n") == 2 and "- « Lampe de studio » par Jeanne Martin (CC BY) via Poly Pizza" in cr11["texte_fr"]
      and cr11["texte_fr"].splitlines()[-1].startswith("- Modèles 3D « ") and "Watercolor Green Leaf Print Wall Art" in cr11["texte_fr"]
      and "par Amazon.com (Amazon Berkeley Objects, CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/), fichiers recompressés par CodePawl — https://huggingface.co/datasets/codepawl/abo-glb" in cr11["texte_fr"]
      and cr11["texte_en"].splitlines()[-1].startswith('- 3D models "') and "files recompressed by CodePawl" in cr11["texte_en"]
      and cr11["export"] is True and cr11["partage"] is True and len(cr11["lignes"]) == 3 and all(x["obligatoire"] for x in cr11["lignes"]), cr11)
check("11.12 nom court : la mention « Amazon Brand » ôtée, coupé à un mot entier ; un nom court reste entier",
      CA._nom_court("Amazon Brand - Rivet Lamp") == "Rivet Lamp" and CA._nom_court("Vase") == "Vase" and len(CA._nom_court("mot " * 40)) <= OB.MAX_NOM
      and not CA._nom_court("Amazon Brand – " + "Stone Beam Sofa " * 8).endswith(" …"))
(CA.racine() / "index.json").write_text(json.dumps(dict(ind, revision="0" * 40)), "utf-8"); CA._memoire.clear()
check("11.13 un index d'une autre révision n'est pas employé : le catalogue redevient « à charger »", CA.etat()["pret"] is False and _refus_c(CA.chercher, "") == 409)
reseau["metadata.jsonl"] = b"\n".join(json.dumps(x).encode("utf-8") for x in lignes[:20])
check("11.14 une liste trop courte n'est pas le catalogue (502) : l'index n'est pas remplacé", _refus_c(CA.charger) == 502 and CA.etat()["pret"] is False)
reseau["metadata.jsonl"] = LISTE
r = local.get("/api/studiov/catalogue")
check("11.15 routes : état (à charger), chargement, recherche, vignette (image/webp), pose ; produit inconnu 404, identifiant hostile 400 ; hors boucle locale refusé",
      r.status_code == 200 and r.json()["pret"] is False and r.json()["source"]["licence"] == "CC BY 4.0" and local.get("/api/studiov/catalogue/recherche").status_code == 409
      and local.post("/api/studiov/catalogue/index").json()["total"] == 117
      and local.get("/api/studiov/catalogue/recherche", params={"q": "wall art", "famille": "mural"}).json()["resultats"][0]["deja"] == p3["ref"]
      and local.get("/api/studiov/catalogue/vignette/B000000001.webp").headers["content-type"] == "image/webp"
      and local.post("/api/studiov/catalogue/poser", json={"id": "B000000001"}).json()["id"] == p1["id"]
      and local.post("/api/studiov/catalogue/poser", json={"id": "B999999999"}).status_code == 404
      and local.post("/api/studiov/catalogue/poser", json={"id": "../x"}).status_code == 400
      and local.get("/api/studiov/catalogue/vignette/..%2f..%2fx.webp").status_code in (400, 404)
      and all(x.status_code in (401, 403) for x in (loin.get("/api/studiov/catalogue"), loin.post("/api/studiov/catalogue/index"), loin.post("/api/studiov/catalogue/poser", json={"id": "B000000001"}))), r.text[:200])
r = local.post("/api/studiov/objets", files={"fichier": ("x.glb", _glb(CUBE))}, data={"source": "abo", "licence": ""})
check("11.16 la source du catalogue n'est pas déclarable à l'import d'un fichier : elle ne donne pas sa licence à un fichier quelconque",
      r.status_code == 200 and r.json()["source"] == "fichier" and r.json()["licence"] == "A-VERIFIER", r.text[:200])
CA._telecharger = vrai_reseau
src11 = pathlib.Path(CA.__file__).read_text("utf-8")
autres11 = "".join(pathlib.Path(m.__file__).read_text("utf-8") for m in (S, H, OB, SI))
check("11.17 le réseau du studio tient en UNE fonction, vers une révision FIGÉE en https ; les autres modules du studio n'ouvrent aucun réseau",
      src11.count("import httpx") == 1 and src11.count("BASE + chemin") == 1 and re.match(r"^[0-9a-f]{40}$", CA.REVISION) and CA.BASE.startswith("https://huggingface.co/datasets/codepawl/abo-glb/resolve/" + CA.REVISION + "/")
      and not re.search(r"httpx|urllib|requests|socket", autres11) and "follow_redirects=True" in src11 and 'r.url.scheme != "https"' in src11)

print("12. régie de l'écran")
from app.services import studiov_videos as SV                        # noqa: E402


def _refus_v(f, *a):
    try:
        f(*a)
    except SV.RefusVideo as e:
        return e.statut
    return None


SORTIES = _reglages.outputs_path
(SORTIES / "captures").mkdir(parents=True, exist_ok=True)
(SORTIES / "captures" / "prise.mp4").write_bytes(b"\0" * 4096)
(SORTIES / "captures" / "note.txt").write_text("x", "utf-8")
(_tmp / "ailleurs.mp4").write_bytes(b"\0" * 64)
r12 = S.normaliser({"regie": {"medias": [{"type": "partage", "ref": "C:/x"}, {"type": "image", "ref": i1["ref"]}, {"type": "image", "ref": "vid:" + "0" * 16},
                                         {"type": "video", "ref": "vid:" + "a" * 16}, {"type": "video", "ref": "../x.mp4"}, {"type": "video"},
                                         {"type": "eteint"}, {"type": "youtube", "ref": "https://x"}, "pirate"] + [{"type": "eteint"}] * 20}})
check("12.1 recette : la régie garde un type fermé et, pour une image ou une vidéo, une RÉFÉRENCE valide ; 12 médias au plus ; sans régie : liste vide ; idempotent",
      [(m["type"], m["ref"]) for m in r12["regie"]["medias"][:4]] == [("partage", ""), ("image", i1["ref"]), ("video", "vid:" + "a" * 16), ("eteint", "")]
      and len(r12["regie"]["medias"]) == 8 and len(S.normaliser({"regie": {"medias": [{"type": "eteint"}] * 30}})["regie"]["medias"]) == S.MAX_MEDIAS == 12
      and S.normaliser({})["regie"] == {"medias": []} and S.normaliser({"regie": "x"})["regie"] == {"medias": []}
      and S.normaliser(r12) == r12 and all(v["regie"] == {"medias": []} for v in S.livres()) and S.catalogue()["types_media"] == ["partage", "eteint", "image", "video"])
v1 = SV.lier("job-1", str(SORTIES / "captures" / "prise.mp4"), "Ma  prise\x00 du jour", 24)
check("12.2 lier une vidéo de la Bibliothèque : une fiche (référence vid:), jamais une copie ; le même job n'est lié qu'une fois",
      S.REF_VIDEO.match(v1["ref"]) and v1["nom"] == "Ma prise du jour" and v1["duree"] == 24.0 and v1["present"] is True and v1["job"] == "job-1"
      and SV.lier("job-1", str(SORTIES / "captures" / "prise.mp4"))["id"] == v1["id"] and len(SV.lister()) == 1
      and sorted(x.name for x in (SV.racine() / v1["id"]).iterdir()) == ["fiche.json"] and SV.chemin(v1["id"]) == (SORTIES / "captures" / "prise.mp4").resolve(), v1)
check("12.3 refusés (404) : fichier hors du dossier des sorties, remontée de dossier, autre extension, fichier absent, job hostile ; rien n'est écrit",
      [_refus_v(SV.lier, *x) for x in (("job-2", str(_tmp / "ailleurs.mp4")), ("job-2", str(SORTIES / "captures" / ".." / ".." / "ailleurs.mp4")),
                                       ("job-2", str(SORTIES / "captures" / "note.txt")), ("job-2", str(SORTIES / "captures" / "absente.mp4")),
                                       ("../job", str(SORTIES / "captures" / "prise.mp4")), (None, str(SORTIES / "captures" / "prise.mp4")), ("job-2", None))] == [404] * 7
      and len(SV.lister()) == 1)
appels12 = []
def _faux_ffmpeg(argv, **k):
    appels12.append(list(argv))
    pathlib.Path(argv[-1]).write_bytes(b"\xff\xd8\xff\xe0vignette")
vrai_run12, SV.subprocess.run = SV.subprocess.run, _faux_ffmpeg
check("12.4 vignette : tirée une fois par ffmpeg (sans fenêtre de saisie : une liste d'arguments), puis gardée avec la fiche ; identifiant hostile 400, inconnu 404",
      SV.vignette(v1["id"])[:2] == b"\xff\xd8" and SV.vignette(v1["id"])[:2] == b"\xff\xd8" and len(appels12) == 1 and str(SORTIES / "captures" / "prise.mp4") in " ".join(appels12[0])
      and all(_refus_v(SV.lire, x) == 400 for x in ("../x", "ABC", "", None)) and _refus_v(SV.vignette, "0" * 16) == 404)
SV.subprocess.run = vrai_run12
dc12 = S.creer(None, "Décor en régie", "esp-r")
dc12 = S.enregistrer(dc12["id"], dict(dc12, regie={"medias": [{"type": "partage"}, {"type": "image", "ref": i2["ref"]}, {"type": "video", "ref": v1["ref"]}]}))
check("12.5 une vidéo et une image de la régie sont EMPLOYÉES : suppression refusée (409) tant que le décor les garde",
      SV.emplois(dc12) == {v1["ref"]} and i2["ref"] in SI.emplois(dc12) and _refus_v(SV.supprimer, v1["id"]) == 409 and _refus_i(SI.supprimer, i2["id"]) == 409)
r = local.get(f"/api/studiov/videos/{v1['id']}/fichier", headers={"Range": "bytes=0-99"})
check("12.6 routes : liste, fichier servi par morceaux (206), vignette, identifiant hostile 400, job hostile ou inconnu 404, hors boucle locale refusée ; le catalogue du décorateur liste les vidéos",
      local.get("/api/studiov/videos").json()["videos"][0]["id"] == v1["id"] and r.status_code == 206 and len(r.content) == 100 and r.headers["content-type"] == "video/mp4"
      and local.get(f"/api/studiov/videos/{v1['id']}/vignette.jpg").headers["content-type"] == "image/jpeg"
      and local.get("/api/studiov/videos/ZZZ/fichier").status_code == 400 and local.post("/api/studiov/bibliotheque/video", json={"job": "../x"}).status_code == 404
      and local.post("/api/studiov/bibliotheque/video", json={}).status_code == 404 and local.delete(f"/api/studiov/videos/{v1['id']}").status_code == 409
      and loin.get("/api/studiov/videos").status_code in (401, 403) and loin.post("/api/studiov/bibliotheque/video", json={"job": "job-1"}).status_code in (401, 403)
      and local.get("/api/studiov/habillage").json()["videos"][0]["ref"] == v1["ref"], r.status_code)
(SORTIES / "captures" / "prise.mp4").unlink()
check("12.7 la vidéo a quitté la Bibliothèque : la fiche le dit, le fichier n'est plus servi (404), la recette garde sa référence",
      SV.lire(v1["id"])["present"] is False and _refus_v(SV.chemin, v1["id"]) == 404 and local.get(f"/api/studiov/videos/{v1['id']}/fichier").status_code == 404
      and S.lire(dc12["id"])["regie"]["medias"][2]["ref"] == v1["ref"])
S.enregistrer(dc12["id"], dict(dc12, regie={"medias": []}))
SV.supprimer(v1["id"])
check("12.8 … retirée de la régie, la fiche s'oublie ; inconnue 404", SV.lister() == [] and _refus_v(SV.supprimer, v1["id"]) == 404)
src12 = pathlib.Path(SV.__file__).read_text("utf-8")
check("12.9 le module ne copie jamais la vidéo, n'ouvre aucun réseau et ne passe ffmpeg que par une liste d'arguments",
      "copyfile" not in src12 and "shutil.copy" not in src12 and not re.search(r"httpx|urllib|requests|socket", src12) and "shell=True" not in src12)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
