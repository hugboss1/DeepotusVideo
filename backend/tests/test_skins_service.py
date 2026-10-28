# -*- coding: utf-8 -*-
"""t316 (28/10/2026) (D2, tâche 1) — banc du service des skins de capture (app/services/skins.py).
Plan docs/superpowers/plans/2026-10-28-t316-skins.md, spec boîte à outils §8.5.
Sections :
  1. format : champ inconnu ignoré, bornes, couleurs (rôle, #hex, null = kit pour principale/accent seulement), textes
     (contrôle ôté, borné), choix fermés (forme, styles, coin, fond), place tenue dans le cadre, type faux -> défaut ;
  2. livrés : cinq (deepotus, sobre, neon, presse, jeu), lecture seule (409 à l'écriture, à la suppression, aux
     images), « Fait avec DeepotusVideo » actif sur Deepotus seulement ;
  3. skins de l'espace : créer (copie d'un livré, d'un skin avec ses images), nom libre « (2) », enregistrer (l'espace ne
     change jamais), lister par espace, identifiants hostiles (400, jamais sur le disque), introuvable (404) ;
  4. choix : défaut livre-deepotus, "" = sans habillage, skin d'un autre espace refusé (409), suppression qui libère ;
  5. images : Pillow (pas une image -> 415, trop lourde -> 413), réduite à 2 048 px, source du logo / type du fond ;
  6. export/import : aller-retour (images comprises, espace courant, nom libre), liste blanche (../, entrée inconnue
     ignorée et dite, jamais écrite), format ou version faux, skin.json manquant, bombe (décompressé trop lourd),
     image piégée -> rien d'écrit ;
  7. contexte : espace, kit de l'espace, polices de l'identité, logo de l'ESPACE (jamais celui de l'application).
Données jetables (DEEPOTUS_DATA_DIR temporaire), aucun réseau.
Run (depuis backend/) : & $PY tests/test_skins_service.py"""
import io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzskins_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
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


from app.services import skins as K                                  # noqa: E402
from PIL import Image                                                 # noqa: E402


def refus(f, statut):
    try:
        f()
    except K.RefusSkin as e:
        return e.statut == statut
    return False


def png(l=40, h=20, couleur=(200, 30, 30, 255), fmt="PNG"):
    b = io.BytesIO(); Image.new("RGBA" if fmt == "PNG" else "RGB", (l, h), couleur[:4] if fmt == "PNG" else couleur[:3]).save(b, fmt)
    return b.getvalue()


def fichiers():
    return sorted(str(p.relative_to(K.racine())).replace("\\", "/") for p in K.racine().rglob("*") if p.is_file()) if K.racine().is_dir() else []


print("[1] format")
n = K.normaliser({"inconnu": 1, "cadre": {"marge": 5, "bord": -1, "couleur": "rose", "fond": {"type": "video", "c1": "#ABCDEF", "c2": "accent"}},
                  "couleurs": {"principale": None, "accent": "#00FF00", "texte": None, "fond": "noir"},
                  "polices": {"titre": "Georgia", "texte": "x;}<script>"},
                  "logo": {"actif": "oui", "x": 0.99, "l": 0.2, "opacite": 0},
                  "bandeau": {"titre": "  Bonjour\x07\n  le   monde  " + "x" * 200, "style": "neon", "debut_s": float("nan")},
                  "encart": {"forme": "triangle", "y": 0.9, "h": 0.3, "l": 0.01},
                  "zoom": {"niveau": 9, "duree_ms": 1234.6}, "curseur": {"style": "aucun", "taille": True},
                  "signature": {"coin": "milieu"}, "intro": "pas un objet"})
check("1.1 champ inconnu ignoré, sections complètes", "inconnu" not in n and set(n) == set(K.DEFAUT), sorted(n))
check("1.2 bornes (marge 0,12 ; bord 0 ; opacité 0,2 ; zoom 2,5 ; durée entière)", n["cadre"]["marge"] == 0.12 and n["cadre"]["bord"] == 0
      and n["logo"]["opacite"] == 0.2 and n["zoom"]["niveau"] == 2.5 and n["zoom"]["duree_ms"] == 1235, (n["cadre"], n["zoom"]))
check("1.3 couleurs : rôle ou #hex (minuscules), inconnue -> défaut ; null permis pour principale/accent seulement",
      n["cadre"]["couleur"] == "principale" and n["cadre"]["fond"] == {"type": "degrade", "c1": "#abcdef", "c2": "accent"}
      and n["couleurs"] == {"principale": None, "accent": "#00ff00", "texte": "#ffffff", "fond": "#0b0f14"}, (n["cadre"], n["couleurs"]))
check("1.4 polices : un nom de famille sûr gardé, le reste -> null (identité)", n["polices"] == {"titre": "Georgia", "texte": None})
check("1.5 textes : contrôle ôté, espaces repliés, 80 au plus ; NaN -> défaut",
      n["bandeau"]["titre"].startswith("Bonjour le monde x") and len(n["bandeau"]["titre"]) == 80 and n["bandeau"]["debut_s"] == 2.0,
      n["bandeau"])
check("1.6 choix fermés -> défaut (style, forme, coin), booléen faux type -> défaut, section non objet -> défaut",
      n["bandeau"]["style"] == "bande" and n["encart"]["forme"] == "cercle" and n["signature"]["coin"] == "bas-droite"
      and n["logo"]["actif"] is True and n["curseur"]["taille"] == 1.0 and n["curseur"]["style"] == "aucun"
      and n["intro"] == K.DEFAUT["intro"])
check("1.7 place tenue dans le cadre (x + l ≤ 1 ; y + h ≤ 1 pour l'encart ; l borné)",
      n["logo"]["x"] == 0.8 and n["encart"]["l"] == 0.08 and n["encart"]["y"] == 0.7, (n["logo"], n["encart"]))
check("1.8 un document qui n'est pas un objet est refusé (400)", refus(lambda: K.normaliser([1]), 400))

print("[2] livrés")
L = {v["id"]: v for v in K.livres()}
check("2.1 cinq livrés : deepotus, sobre, neon, presse, jeu", sorted(L) == ["livre-deepotus", "livre-jeu", "livre-neon", "livre-presse", "livre-sobre"], sorted(L))
check("2.2 « Fait avec DeepotusVideo » actif sur Deepotus seulement", L["livre-deepotus"]["signature"]["actif"] is True
      and not any(v["signature"]["actif"] for k, v in L.items() if k != "livre-deepotus"))
check("2.3 livrés en lecture seule : écrire, supprimer, poser une image -> 409",
      refus(lambda: K.enregistrer("livre-sobre", {}), 409) and refus(lambda: K.supprimer("livre-neon"), 409)
      and refus(lambda: K.poser_image("livre-jeu", "logo", png()), 409) and refus(lambda: K.enregistrer("livre-inexistant", {}), 409))
check("2.4 un livré suit le kit (principale/accent null) ou porte sa palette (néon)",
      L["livre-deepotus"]["couleurs"]["principale"] is None and L["livre-neon"]["couleurs"]["principale"] == "#ff2bd6")
check("2.5 lire un livré inconnu -> 404", refus(lambda: K.lire("livre-zzz"), 404))

print("[3] skins de l'espace")
a = K.creer("livre-neon", None, "deepotus")
check("3.1 copie d'un livré : neuf, de l'espace, base notée, nom repris", K.ID.match(a["id"]) and a["espace_id"] == "deepotus"
      and a["base"] == "livre-neon" and a["nom"] == "Néon" and a["livre"] is False and a["cadre"]["marge"] == 0.04, a)
b = K.creer("livre-neon", None, "deepotus")
check("3.2 nom libre : « Néon (2) »", b["nom"] == "Néon (2)", b["nom"])
e = K.enregistrer(a["id"], {"nom": "Mon néon", "espace_id": "autre", "bandeau": {"titre": "Épisode 1"}, "id": "x"})
check("3.3 enregistrer : nom changé, l'espace et l'id ne changent jamais", e["nom"] == "Mon néon" and e["espace_id"] == "deepotus"
      and e["id"] == a["id"] and e["bandeau"]["titre"] == "Épisode 1" and e["cadre"]["marge"] == 0.0, e)
c = K.creer(None, "Client", "client-a")
check("3.4 lister par espace", [v["id"] for v in K.lister("client-a")] == [c["id"]]
      and {v["id"] for v in K.lister("deepotus")} == {a["id"], b["id"]})
avant = fichiers()
check("3.5 identifiants hostiles -> 400 (lire, enregistrer, supprimer, image), rien sur le disque",
      all(refus(lambda x=x: K.lire(x), 400) for x in ("../x", "ABCDEF0123456789", "a" * 17, "", None))
      and refus(lambda: K.enregistrer("../../x", {}), 400) and refus(lambda: K.supprimer("..\\x"), 400)
      and refus(lambda: K.chemin_image("../x", "logo"), 400) and fichiers() == avant)
check("3.6 introuvable -> 404", refus(lambda: K.lire("0123456789abcdef"), 404) and refus(lambda: K.supprimer("0123456789abcdef"), 404))
check("3.7 copier depuis une base introuvable -> 404, rien d'écrit", refus(lambda: K.creer("0123456789abcdef", None, "deepotus"), 404) and fichiers() == avant)

print("[4] choix de l'espace")
check("4.1 sans choix : livre-deepotus", K.choisi("deepotus") == "livre-deepotus" and K.actif("x")["id"] == "livre-deepotus")
K.choisir("deepotus", a["id"])
check("4.2 choisir un skin de l'espace", K.choisi("deepotus") == a["id"] and K.actif("deepotus")["nom"] == "Mon néon")
check("4.3 un skin d'un autre espace est refusé (409), un introuvable (404)",
      refus(lambda: K.choisir("deepotus", c["id"]), 409) and refus(lambda: K.choisir("deepotus", "0123456789abcdef"), 404))
K.choisir("client-a", "")
check("4.4 \"\" = sans habillage", K.choisi("client-a") == "" and K.actif("client-a") is None)
K.choisir("client-a", "livre-presse")
check("4.5 un livré se choisit pour tout espace", K.choisi("client-a") == "livre-presse")
K.supprimer(a["id"])
check("4.6 supprimer le skin choisi libère le choix (retour au défaut)", K.choisi("deepotus") == "livre-deepotus"
      and a["id"] not in json.loads((K.racine() / "choix.json").read_text("utf-8")).values())

print("[5] images")
g = K.poser_image(b["id"], "logo", png(4000, 1000))
with Image.open(K.chemin_image(b["id"], "logo")) as im:
    im.load()
check("5.1 logo posé : PNG réduit à 2 048 px, source « image »", im.format == "PNG" and max(im.size) == 2048
      and g["logo"]["source"] == "image" and g["images"] == ["logo"], (im.size, g["logo"]))
g = K.poser_image(b["id"], "fond", png(30, 30, fmt="JPEG"))
check("5.2 fond JPEG relu en PNG, fond de type image", g["cadre"]["fond"]["type"] == "image" and sorted(g["images"]) == ["fond", "logo"])
avant = fichiers()
check("5.3 pas une image -> 415 ; trop lourde -> 413 ; nom inconnu -> 400 ; rien d'écrit",
      refus(lambda: K.poser_image(b["id"], "logo", b"%PDF-1.4 pas une image"), 415)
      and refus(lambda: K.poser_image(b["id"], "logo", b"\x89PNG" + b"0" * (K.MAX_IMAGE + 1)), 413)
      and refus(lambda: K.poser_image(b["id"], "../etc", png()), 400) and fichiers() == avant)
check("5.3b format hors liste (BMP, EPS…) -> 415 : Pillow n'ouvre que PNG, JPEG, WebP",
      refus(lambda: K.poser_image(b["id"], "logo", png(fmt="BMP")), 415)
      and refus(lambda: K.poser_image(b["id"], "logo", b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 10 10\n"), 415) and fichiers() == avant)
d = K.creer(b["id"], None, "client-a")
check("5.4 la copie d'un skin emporte ses images", sorted(d["images"]) == ["fond", "logo"] and d["espace_id"] == "client-a")
g = K.retirer_image(b["id"], "logo")
check("5.5 retirer le logo : logo de l'espace de nouveau", g["logo"]["source"] == "espace" and g["images"] == ["fond"]
      and refus(lambda: K.chemin_image(b["id"], "logo"), 404))

print("[6] export / import")
nom, z = K.exporter(d["id"])
with zipfile.ZipFile(io.BytesIO(z)) as zz:
    noms = sorted(zz.namelist()); sj = json.loads(zz.read("skin.json"))
check("6.1 export : skin.json + images, sans id ni espace", noms == ["images/fond.png", "images/logo.png", "skin.json"]
      and sj["format"] == "deepotus-skin" and sj["version"] == 1 and "id" not in sj and "espace_id" not in sj
      and nom == "skin-neon-2.zip", (noms, nom))
r = K.importer(z, "deepotus")
check("6.2 import : skin NEUF de l'espace courant, images comprises, rien d'ignoré", r["id"] != d["id"] and r["espace_id"] == "deepotus"
      and sorted(r["images"]) == ["fond", "logo"] and r["ignores"] == [] and r["cadre"] == d["cadre"], r)
r2 = K.importer(z, "deepotus")
check("6.3 import du même paquet : nom libre (« (n) » ajouté, jamais un doublon dans l'espace)",
      r["nom"] == d["nom"] + " (2)" and r2["nom"] == d["nom"] + " (3)", (d["nom"], r["nom"], r2["nom"]))


def zip_de(entrees):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as zz:
        for k, v in entrees.items():
            zz.writestr(k, v)
    return b.getvalue()


SJ = json.dumps({"format": "deepotus-skin", "version": 1, "nom": "Piégé"})
r3 = K.importer(zip_de({"skin.json": SJ, "../../evil.txt": "x", "images/autre.png": png(), "notes.md": "y"}), "deepotus")
check("6.4 liste blanche : ../, image hors liste, fichier inconnu ignorés ET dits, jamais écrits",
      sorted(r3["ignores"]) == ["../../evil.txt", "images/autre.png", "notes.md"] and r3["images"] == []
      and not any("evil" in f or "autre" in f or "notes" in f for f in fichiers()) and not (_tmp / "evil.txt").exists(), r3["ignores"])
avant = fichiers()
check("6.5 format faux, version fausse, skin.json manquant ou illisible, pas un zip -> 400, rien d'écrit",
      refus(lambda: K.importer(zip_de({"skin.json": json.dumps({"format": "autre", "version": 1})}), "deepotus"), 400)
      and refus(lambda: K.importer(zip_de({"skin.json": json.dumps({"format": "deepotus-skin", "version": 2})}), "deepotus"), 400)
      and refus(lambda: K.importer(zip_de({"images/logo.png": png()}), "deepotus"), 400)
      and refus(lambda: K.importer(zip_de({"skin.json": "{pas du json"}), "deepotus"), 400)
      and refus(lambda: K.importer(b"PK\x03\x04 casse", "deepotus"), 400) and fichiers() == avant)
bombe = zip_de({"skin.json": SJ, "images/fond.png": b"\0" * (K.MAX_ZIP + 10)})
check("6.6 bombe (décompressé > 12 Mo) -> 413 ; paquet trop lourd -> 413 ; trop d'entrées -> 400 ; rien d'écrit",
      len(bombe) < 200_000 and refus(lambda: K.importer(bombe, "deepotus"), 413)
      and refus(lambda: K.importer(b"0" * (K.MAX_ZIP + 1), "deepotus"), 413)
      and refus(lambda: K.importer(zip_de({f"x{i}": "y" for i in range(9)} | {"skin.json": SJ}), "deepotus"), 400)
      and fichiers() == avant)
check("6.7 image piégée dans le paquet -> 415, rien d'écrit",
      refus(lambda: K.importer(zip_de({"skin.json": SJ, "images/logo.png": b"<svg onload=alert(1)>"}), "deepotus"), 415) and fichiers() == avant)
r4 = K.importer(zip_de({"skin.json": json.dumps({"format": "deepotus-skin", "version": 1, "nom": "Sans image",
                                                 "logo": {"source": "image"}, "cadre": {"fond": {"type": "image"}}})}), "deepotus")
check("6.8 un skin qui réclame des images absentes retombe sur le logo de l'espace et le dégradé",
      r4["logo"]["source"] == "espace" and r4["cadre"]["fond"]["type"] == "degrade")
nom_l, zl = K.exporter("livre-presse")
check("6.9 un livré s'exporte (et se réimporte comme skin de l'espace)", K.importer(zl, "client-a")["base"] is None and "presse" in nom_l)

zc = bytearray(zip_de({"skin.json": SJ, "images/logo.png": png(200, 200, (1, 2, 3, 255))}))
i = zc.find(b"images/logo.png") + len("images/logo.png") + 20
zc[i] ^= 0xFF; zc[i + 1] ^= 0xFF                                     # données compressées abîmées (CRC faux)
avant = fichiers()
check("6.10 entrée abîmée (CRC faux, flux illisible) -> 400, jamais 500, rien d'écrit",
      refus(lambda: K.importer(bytes(zc), "deepotus"), 400) and fichiers() == avant)
check("6.11 du_meme_espace : livré ou skin de l'espace lu ; skin d'un autre espace -> 409",
      K.du_meme_espace("livre-jeu", "x")["id"] == "livre-jeu" and K.du_meme_espace(d["id"], "client-a")["id"] == d["id"]
      and refus(lambda: K.du_meme_espace(d["id"], "deepotus"), 409))

print("[7] contexte")
from app.services import espaces, identite                          # noqa: E402
espaces.lire()
eid = espaces.lire()["actif"]
try:
    identite.ecrire(eid, {"typographies": [{"nom": "Playfair Display", "usage": "titres"}, {"nom": "Inter", "usage": "texte"}]})
    typos_ok = True
except Exception as x:                                               # noqa: BLE001
    typos_ok = repr(x)
cx = K.contexte(eid)
check("7.1 contexte : espace, kit (couleurs, slogans), polices de l'identité, logo de l'ESPACE",
      typos_ok is True and cx["espace"]["id"] == eid and cx["kit"]["brand_color"].startswith("#")
      and cx["polices"] == {"titre": "Playfair Display", "texte": "Inter"} and cx["logo_espace"] == f"/api/espaces/{eid}/logo", (typos_ok, cx))
check("7.2 le logo de l'application n'est jamais servi par un skin", "branding" not in json.dumps(cx) and "deepotus-logo" not in json.dumps(cx))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
