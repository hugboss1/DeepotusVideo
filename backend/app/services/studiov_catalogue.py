# -*- coding: utf-8 -*-
"""SVC (15/11/2026) — le CATALOGUE DE PRODUITS RÉELS du studio virtuel : les 7 953 modèles 3D d'Amazon Berkeley
Objects (meubles, luminaires, tapis, art mural… de vrais produits, à leur taille réelle), dans leur édition allégée
pour le web « codepawl/abo-glb » (Hugging Face). Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md
(§ 10).

Licence : CC BY 4.0 (vérifiée à la source, amazon-berkeley-objects.s3.amazonaws.com) — usage commercial permis, crédit
à Amazon.com obligatoire, changements à signaler. Les noms de produits et de marques restent à leurs propriétaires.

RIEN de ce catalogue n'est livré avec l'application. Ce module est le SEUL du studio à ouvrir le réseau, et seulement
sur un geste de l'utilisateur :
  - « Charger le catalogue » télécharge la liste des produits (9 Mo) et en garde un index compact ;
  - une vignette n'est demandée que pour un produit affiché, puis gardée ;
  - « Poser » télécharge UN modèle (1,2 Mo en médiane) et le range dans la bibliothèque d'objets de l'utilisateur
    (studiov_objets, source `abo`), avec sa licence, son auteur, sa façon de se poser (sol, mur, plafond) et, pour
    un luminaire, le fait qu'il éclaire.
Aucune adresse ne vient de l'écran ni de la recette : tout chemin est bâti ici, depuis un identifiant de produit
vérifié, vers une RÉVISION FIGÉE du dépôt. Aucune dépense.

- `DATA_ROOT/studiov/catalogue/index.json`      l'index compact (refait si la révision change)
- `DATA_ROOT/studiov/catalogue/vignettes/<id>.webp`"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from app.services import studiov as S
from app.services import studiov_objets as OB

DEPOT = "codepawl/abo-glb"
REVISION = "806eef9d41c8854eecf53462978079f90ebc67ca"               # figée : les fichiers ne changent pas sous l'application
BASE = f"https://huggingface.co/datasets/{DEPOT}/resolve/{REVISION}/"
PAGE = f"https://huggingface.co/datasets/{DEPOT}"
ID_PRODUIT = re.compile(r"^[A-Z0-9]{10}$")
MAX_LISTE = 40 * 1024 * 1024
MAX_VIGNETTE = 600 * 1024
MAX_VIGNETTES = 2000                       # vignettes gardées sur le disque (les plus anciennes partent)
PAR_PAGE = 24
MIN_PRODUITS = 100                         # en dessous, la liste reçue n'est pas le catalogue
_VERROU = threading.RLock()
_memoire: dict = {}


class RefusCatalogue(ValueError):
    """Une demande refusée : `statut` = le code HTTP. Message littéral (traduit par L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


# les familles du décorateur, dans l'ordre où elles sont proposées : id -> (nom, nom en anglais)
FAMILLES = {
    "sieges": ("Chaises et fauteuils", "Chairs and armchairs"), "canapes": ("Canapés", "Sofas"),
    "tables": ("Tables et bureaux", "Tables and desks"), "rangements": ("Rangements", "Storage"),
    "luminaires": ("Luminaires", "Lighting"), "tapis": ("Tapis", "Rugs"), "mural": ("Art mural et miroirs", "Wall art and mirrors"),
    "plantes": ("Jardinières et vases", "Planters and vases"), "textiles": ("Coussins et textiles", "Pillows and textiles"),
    "chambre": ("Chambre", "Bedroom"), "bureau": ("Bureau et tech", "Office and tech"), "divers": ("Autres", "Other"),
}
# le type de produit d'Amazon -> (famille, nom, nom en anglais)
TYPES = {
    "chair": ("sieges", "Chaise", "Chair"), "stool seating": ("sieges", "Tabouret", "Stool"), "ottoman": ("sieges", "Pouf", "Ottoman"),
    "bench": ("sieges", "Banc", "Bench"), "bean bag chair": ("sieges", "Pouf poire", "Bean bag"),
    "sofa": ("canapes", "Canapé", "Sofa"),
    "table": ("tables", "Table", "Table"), "desk": ("tables", "Bureau", "Desk"),
    "cabinet": ("rangements", "Meuble de rangement", "Cabinet"), "shelf": ("rangements", "Étagère", "Shelf"),
    "dresser": ("rangements", "Commode", "Dresser"), "storage box": ("rangements", "Boîte de rangement", "Storage box"),
    "storage rack": ("rangements", "Casier", "Storage rack"), "storage drawer": ("rangements", "Tiroir", "Storage drawer"),
    "clothes rack": ("rangements", "Portant", "Clothes rack"), "bottle rack": ("rangements", "Casier à bouteilles", "Bottle rack"),
    "storage hook": ("rangements", "Patère", "Hook"), "laundry hamper": ("rangements", "Panier à linge", "Laundry hamper"),
    "basket": ("rangements", "Panier", "Basket"), "jewelry storage": ("rangements", "Boîte à bijoux", "Jewellery box"),
    "lamp": ("luminaires", "Lampe", "Lamp"), "light fixture": ("luminaires", "Luminaire", "Light fixture"),
    "home lighting and lamps": ("luminaires", "Luminaire", "Light fixture"), "candle holder": ("luminaires", "Bougeoir", "Candle holder"),
    "rug": ("tapis", "Tapis", "Rug"), "exercise mat": ("tapis", "Tapis de sport", "Exercise mat"),
    "wall art": ("mural", "Art mural", "Wall art"), "home mirror": ("mural", "Miroir", "Mirror"),
    "picture frame": ("mural", "Cadre", "Picture frame"), "clock": ("mural", "Horloge", "Clock"),
    "writing board": ("mural", "Tableau d'écriture", "Writing board"), "pinboard": ("mural", "Tableau d'affichage", "Pinboard"),
    "planter": ("plantes", "Jardinière", "Planter"), "vase": ("plantes", "Vase", "Vase"),
    "artificial plant": ("plantes", "Plante artificielle", "Artificial plant"),
    "pillow": ("textiles", "Coussin", "Pillow"), "curtain": ("textiles", "Rideau", "Curtain"), "blanket": ("textiles", "Plaid", "Blanket"),
    "furniture cover": ("textiles", "Housse", "Furniture cover"),
    "bed": ("chambre", "Lit", "Bed"), "headboard": ("chambre", "Tête de lit", "Headboard"), "bed frame": ("chambre", "Cadre de lit", "Bed frame"),
    "mattress": ("chambre", "Matelas", "Mattress"),
    "office products": ("bureau", "Fourniture de bureau", "Office supply"), "multiport hub": ("bureau", "Hub", "Hub"),
    "flat screen display mount": ("bureau", "Support d'écran", "Screen mount"),
    "portable electronic device stand": ("bureau", "Support d'appareil", "Device stand"),
    "portable electronic device mount": ("bureau", "Support d'appareil", "Device mount"),
    "portable electronic device cover": ("bureau", "Housse d'appareil", "Device cover"),
    "computer add on": ("bureau", "Accessoire d'ordinateur", "Computer accessory"), "computer": ("bureau", "Ordinateur", "Computer"),
    "electronic cable": ("bureau", "Câble", "Cable"), "sound and recording equipment": ("bureau", "Matériel audio", "Audio gear"),
    "mouse pad": ("bureau", "Tapis de souris", "Mouse pad"), "electric fan": ("divers", "Ventilateur", "Fan"),
    "sporting goods": ("divers", "Article de sport", "Sporting goods"),
}
# un type trop vague chez Amazon (« home », « home furniture and decor »…) est rangé d'après le NOM du produit
_MOTS = (
    ("canapes", ("sofa", "loveseat", "sectional", "couch", "chaise lounge", "futon")),
    ("chambre", ("headboard", "mattress", "bed frame", "platform bed", "nightstand", "bedside")),
    ("sieges", ("chair", "stool", "ottoman", "bench", "recliner", "glider", "pouf")),
    ("tables", ("table", "desk")),
    ("rangements", ("cabinet", "shelf", "shelv", "bookcase", "dresser", "sideboard", "tv ", "storage", "drawer", "wardrobe", "console", "rack")),
    ("luminaires", ("lamp", "light", "pendant", "chandelier", "sconce", "lantern")),
    ("tapis", ("rug", "runner", "doormat")),
    ("mural", ("mirror", "wall art", "print", "canvas", "frame", "clock")),
    ("plantes", ("planter", "vase", "flower pot", "plant")),
    ("textiles", ("pillow", "curtain", "throw", "blanket", "cushion")),
)
# ceux qui, centrés sur leur point de pose, ne sont PAS des objets de mur (un coussin se pose)
_JAMAIS_MUR = ("pillow", "home bed and bath", "chair", "blanket")
_ORDRE = list(FAMILLES)
_SANS_LUMIERE = ("candle holder",)         # de la famille des luminaires, mais sans ampoule…
_MOTS_LUMIERE = ("lamp", "light", "pendant", "chandelier", "sconce", "lantern")     # … sauf si le nom dit le contraire


def _lumineux(p: dict) -> bool:
    """Un luminaire éclaire. Amazon range parfois une suspension parmi les bougeoirs : le nom du produit tranche."""
    if p["famille"] != "luminaires":
        return False
    return p["type"] not in _SANS_LUMIERE or any(m in p["nom"].lower() for m in _MOTS_LUMIERE)


def racine() -> Path:
    return S.racine() / "catalogue"


# ── le réseau : UNE fonction, vers la révision figée (remplacée par une couture dans les bancs) ──

def _telecharger(chemin: str, maximum: int) -> bytes:
    """Les octets d'un fichier de la révision figée (`chemin` est bâti par ce module), `maximum` octets au plus."""
    import httpx
    from app.config import SSL_VERIFY
    try:
        with httpx.Client(verify=SSL_VERIFY, follow_redirects=True, timeout=httpx.Timeout(20.0, read=60.0)) as c:
            with c.stream("GET", BASE + chemin) as r:
                if r.url.scheme != "https":
                    raise RefusCatalogue("Le catalogue en ligne ne répond pas : réessayez plus tard.", 502)
                if r.status_code == 404:
                    raise RefusCatalogue("Ce fichier n'est plus dans le catalogue en ligne.", 404)
                if r.status_code != 200:
                    raise RefusCatalogue("Le catalogue en ligne ne répond pas : réessayez plus tard.", 502)
                octets = bytearray()
                for bout in r.iter_bytes(65536):
                    octets += bout
                    if len(octets) > maximum:
                        raise RefusCatalogue("Fichier du catalogue plus lourd qu'attendu : téléchargement arrêté.", 502)
    except httpx.HTTPError:
        raise RefusCatalogue("Catalogue en ligne injoignable : vérifiez la connexion à Internet.", 503) from None
    return bytes(octets)


# ── l'index ──

def _famille(type_abo: str, nom: str) -> str:
    connu = TYPES.get(type_abo)
    if connu:
        return connu[0]
    bas = f" {nom.lower()} "
    for fam, mots in _MOTS:
        if any(m in bas for m in mots):
            return fam
    return "divers"


def _pose(type_abo: str, mini: list, dims: list) -> str:
    """Comment le produit se pose, d'après son origine dans le fichier : au sol (sa base à y = 0), au mur (centré sur
    son point, le dos à z = 0), au plafond (il pend sous y = 0)."""
    if mini[1] >= -0.005:
        return "sol"
    if abs(mini[1] + dims[1] / 2) < 0.02 * max(1.0, dims[1]):
        return "sol" if type_abo in _JAMAIS_MUR else "mur"
    return "plafond" if mini[1] + dims[1] <= 0.02 else "sol"


def _nombres(v, n=3):
    if not isinstance(v, list) or len(v) != n:
        return None
    try:
        out = [float(x) for x in v]
    except (TypeError, ValueError):
        return None
    return out if all(x == x and abs(x) < 1e4 for x in out) else None


def _produit(brut) -> dict | None:
    """Une ligne de la liste d'Amazon -> une entrée de l'index, ou None si elle est inutilisable ou trop lourde."""
    if not isinstance(brut, dict):
        return None
    pid, nom = brut.get("id"), S.K._texte(brut.get("name"), "", 200)
    dims, mini = _nombres(brut.get("size_metres")), _nombres(brut.get("bounds_min"))
    tri, octets = brut.get("triangles"), brut.get("pack_bytes")
    if not (isinstance(pid, str) and ID_PRODUIT.match(pid) and nom and dims and mini):
        return None
    if isinstance(tri, bool) or isinstance(octets, bool) or not isinstance(tri, int) or not isinstance(octets, int):
        return None
    if not (0 < tri <= OB.MAX_TRIANGLES and 0 < octets <= OB.MAX_OCTETS) or min(dims) < 0:
        return None
    if brut.get("file") != f"objects/{pid}/{pid}.glb":
        return None
    type_abo = S.K._texte(brut.get("product_type"), "", 60).lower()
    return {"id": pid, "nom": nom, "type": type_abo, "famille": _famille(type_abo, nom),
            "marque": S.K._texte(brut.get("brand"), "", 60), "couleur": S.K._texte(brut.get("color"), "", 60),
            "matiere": S.K._texte(brut.get("material"), "", 80), "style": S.K._texte(brut.get("style"), "", 60),
            "dims": [round(x, 3) for x in dims], "triangles": tri, "octets": octets, "pose": _pose(type_abo, mini, dims)}


def construire(octets: bytes) -> list:
    """La liste des produits (JSON Lines) -> les entrées de l'index, rangées par famille puis par type et par nom."""
    produits, vus = [], set()
    for ligne in octets.split(b"\n"):
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            p = _produit(json.loads(ligne.decode("utf-8")))
        except (ValueError, UnicodeDecodeError):
            continue
        if p and p["id"] not in vus:
            vus.add(p["id"])
            produits.append(p)
    if len(produits) < MIN_PRODUITS:
        raise RefusCatalogue("La liste reçue n'est pas le catalogue attendu : réessayez plus tard.", 502)
    produits.sort(key=lambda p: (_ORDRE.index(p["famille"]), p["type"], p["nom"].lower(), p["id"]))
    return produits


def _index() -> list | None:
    """Les produits de l'index gardé sur le disque, ou None tant qu'il n'a pas été chargé (ou s'il est d'une autre
    révision)."""
    with _VERROU:
        if "produits" in _memoire:
            return _memoire["produits"]
        try:
            d = json.loads((racine() / "index.json").read_text("utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(d, dict) or d.get("revision") != REVISION or not isinstance(d.get("produits"), list):
            return None
        produits = [p for p in d["produits"] if isinstance(p, dict) and isinstance(p.get("id"), str) and ID_PRODUIT.match(p["id"])]
        _ranger(produits)
        return produits


def _ranger(produits: list) -> None:
    _memoire["produits"] = produits
    _memoire["par_id"] = {p["id"]: p for p in produits}
    _memoire["texte"] = {p["id"]: _texte_de(p) for p in produits}


def _texte_de(p: dict) -> str:
    connu = TYPES.get(p["type"])
    fam = FAMILLES.get(p["famille"], ("", ""))
    return " ".join([p["nom"], p["type"], connu[1] if connu else "", fam[0], fam[1], p["marque"], p["couleur"], p["matiere"], p["style"], p["id"]]).lower()


def charger() -> dict:
    """Télécharge la liste des produits et en fait l'index (geste « Charger le catalogue »)."""
    produits = construire(_telecharger("metadata.jsonl", MAX_LISTE))
    with _VERROU:
        try:
            S.K._ecrire_json(racine() / "index.json", {"revision": REVISION, "cree": S.K._maintenant(), "produits": produits})
        except OSError:
            raise RefusCatalogue("Le catalogue n'a pas pu être enregistré.", 500) from None
        _ranger(produits)
    return etat()


def etat() -> dict:
    produits = _index()
    compte = {}
    for p in produits or []:
        compte[p["famille"]] = compte.get(p["famille"], 0) + 1
    return {"pret": produits is not None, "total": len(produits or []),
            "familles": [{"id": f, "nom": FAMILLES[f][0], "nom_en": FAMILLES[f][1], "n": compte[f]} for f in _ORDRE if compte.get(f)],
            "source": {"nom": "Amazon Berkeley Objects", "auteur": "Amazon.com", "licence": "CC BY 4.0", "url": PAGE,
                       "depot": DEPOT, "revision": REVISION}}


def _vue(p: dict, deja: dict) -> dict:
    connu = TYPES.get(p["type"])
    fam = FAMILLES.get(p["famille"], FAMILLES["divers"])
    return {**p, "libelle": connu[1] if connu else fam[0], "libelle_en": connu[2] if connu else fam[1],
            "lourd": p["triangles"] > OB.TRIANGLES_LEGER, "lumineux": _lumineux(p), "vignette": f"/api/studiov/catalogue/vignette/{p['id']}.webp",
            "deja": deja.get(f"abo:{p['id']}")}


def chercher(q=None, famille=None, page=1) -> dict:
    """{total, page, pages, resultats} : les produits dont le texte contient TOUS les mots de `q`, d'une famille."""
    produits = _index()
    if produits is None:
        raise RefusCatalogue("Le catalogue n'est pas encore chargé.", 409)
    mots = [m for m in S.K._texte(q, "", 80).lower().split(" ") if m][:6]
    fam = famille if famille in FAMILLES else None
    texte = _memoire["texte"]
    retenus = [p for p in produits if (not fam or p["famille"] == fam) and all(m in texte[p["id"]] for m in mots)]
    pages = max(1, -(-len(retenus) // PAR_PAGE))
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    page = min(max(1, page), pages)
    deja = OB.par_origine("abo:")
    return {"total": len(retenus), "page": page, "pages": pages,
            "resultats": [_vue(p, deja) for p in retenus[(page - 1) * PAR_PAGE:page * PAR_PAGE]]}


def _entree(pid) -> dict:
    if not isinstance(pid, str) or not ID_PRODUIT.match(pid):
        raise RefusCatalogue("Produit inconnu du catalogue.", 400)
    if _index() is None:
        raise RefusCatalogue("Le catalogue n'est pas encore chargé.", 409)
    p = _memoire["par_id"].get(pid)
    if p is None:
        raise RefusCatalogue("Produit inconnu du catalogue.", 404)
    return p


# ── les vignettes ──

def _est_webp(octets: bytes) -> bool:
    return len(octets) > 16 and octets[:4] == b"RIFF" and octets[8:12] == b"WEBP"


def vignette(pid) -> bytes:
    """La vignette (WebP, 512 px) d'un produit de l'index : téléchargée une fois, puis gardée."""
    p = _entree(pid)
    f = racine() / "vignettes" / f"{p['id']}.webp"
    try:
        octets = f.read_bytes()
        if _est_webp(octets):
            return octets
    except OSError:
        pass
    octets = _telecharger(f"thumbs/{p['id']}.webp", MAX_VIGNETTE)
    if not _est_webp(octets):
        raise RefusCatalogue("Vignette illisible.", 502)
    with _VERROU:
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(octets)
            _elaguer(f.parent)
        except OSError:
            pass                                        # disque plein ou fermé : la vignette est servie sans être gardée
    return octets


def _elaguer(dossier: Path) -> None:
    fichiers = [x for x in dossier.glob("*.webp") if x.is_file()]
    if len(fichiers) <= MAX_VIGNETTES:
        return
    fichiers.sort(key=lambda x: x.stat().st_mtime)
    for x in fichiers[:len(fichiers) - MAX_VIGNETTES + 200]:
        try:
            x.unlink()
        except OSError:
            pass


# ── poser un produit : le télécharger, le ranger dans les objets de l'utilisateur ──

def _nom_court(nom: str) -> str:
    """Le nom du produit sans la mention de marque d'Amazon, coupé à un mot entier."""
    nom = re.sub(r"^Amazon Brand\s*[–—-]\s*", "", nom).strip()
    if len(nom) <= OB.MAX_NOM:
        return nom
    court = nom[:OB.MAX_NOM - 1]
    return (court[:court.rfind(" ")] if " " in court[20:] else court).rstrip(" ,;:-–") + "…"


def poser(pid) -> dict:
    """La fiche (studiov_objets) du produit, téléchargé s'il n'est pas déjà dans les objets de l'utilisateur."""
    p = _entree(pid)
    origine = f"abo:{p['id']}"
    ref = OB.par_origine("abo:").get(origine)
    if ref:
        return OB.lire(ref[4:])
    octets = _telecharger(f"objects/{p['id']}/{p['id']}.glb", OB.MAX_OCTETS)        # hors verrou : la recherche reste libre
    if len(octets) != p["octets"]:                      # la révision est figée : une autre taille n'est pas le fichier attendu
        raise RefusCatalogue("Le modèle reçu n'est pas celui du catalogue : téléchargement abandonné.", 502)
    with _VERROU:
        ref = OB.par_origine("abo:").get(origine)       # deux demandes du même produit : la seconde reprend la première
        if ref:
            return OB.lire(ref[4:])
        return OB.importer(octets, {"nom": _nom_court(p["nom"]), "titre": p["nom"], "source": "abo", "auteur": "Amazon.com",
                                    "licence": "CC-BY", "url": PAGE, "origine": origine, "pose": p["pose"],
                                    "lumineux": _lumineux(p)})
