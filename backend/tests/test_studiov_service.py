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
     couture : aucun logiciel n'est lancé par ce banc.
Données jetables (DEEPOTUS_DATA_DIR temporaire), aucun réseau.
Run (depuis backend/) : & $PY tests/test_studiov_service.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzstudiov_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")                 # les matières de la Forge (section 8) : jetables
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
check("5.4 le catalogue servi : familles, motifs, lumières, mouvements, usages, polices, styles d'enseigne, types à mot et lumineux",
      set(S.catalogue()) == {"familles", "motifs", "lumieres", "mouvements", "usages", "polices", "styles_enseigne", "types_texte", "types_lumineux"})
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
      and set(r.json()) == {"textures", "familles_texture", "finitions", "ambiances", "styles", "catalogue"} and len(r.json()["textures"]) >= 72
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

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
