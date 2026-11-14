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
  6. routes : boucle locale, liste, actif, choix, création, lecture, écriture d'un livré refusée, fabrique absente 404.
Données jetables (DEEPOTUS_DATA_DIR temporaire), aucun réseau.
Run (depuis backend/) : & $PY tests/test_studiov_service.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzstudiov_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
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
check("5.4 le catalogue servi : familles, motifs, lumières, mouvements", set(S.catalogue()) == {"familles", "motifs", "lumieres", "mouvements"})

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

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
