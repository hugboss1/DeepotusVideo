# -*- coding: utf-8 -*-
"""SVO (14/11/2026) — la BIBLIOTHÈQUE D'OBJETS IMPORTÉS du studio virtuel : les modèles 3D (GLB) que l'utilisateur fait
entrer LUI-MÊME — téléchargés chez Poly Pizza ou Sketchfab, sortis de son Blender (BlenderKit compris), ou de sa
création — et qu'il pose dans un décor comme un objet du catalogue (type `modele`, référence `obj:<id>`).
Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md (§ 7).

Rien de ce module n'est LIVRÉ avec l'application : l'utilisateur importe sous son compte et sous sa licence. Chaque
modèle garde donc sa PROVENANCE — source, auteur, licence, adresse — et la licence dit ce qu'on a le droit d'en faire :

  video    le montrer dans une vidéo (le décor filmé)
  export   le sortir de l'application (décor exporté vers Unreal, Unity, Blender)
  partage  le transmettre à un autre utilisateur (décor partagé)
  credit   l'auteur doit être cité (description de la vidéo)

Une licence qui interdit l'usage commercial, la modification, ou qui impose le partage à l'identique est REFUSÉE à
l'import : une chaîne monétisée est un usage commercial, habiller un modèle est une modification.

- `DATA_ROOT/studiov/objets/<id>/modele.glb` + `fiche.json` (id = 16 hex) ; la bibliothèque est celle de l'utilisateur
  (tous ses espaces), comme ses matières de la Forge.
Le GLB est LU avant d'être gardé : format, version, autonomie (aucun fichier voisin, aucune adresse), compression que
le moteur ne sait pas ouvrir, poids en triangles. Aucun réseau, aucune dépense.

SVC (15/11/2026) : la compression Meshopt est ACCEPTÉE (son décodeur est embarqué avec three.js, et Blender la lit) ;
Draco et Basis restent refusés. Un objet garde sa POSE (sol, mur, plafond) et, s'il vient du catalogue de produits
réels (studiov_catalogue, source `abo`), son titre complet pour les crédits."""
from __future__ import annotations

import json
import re
import secrets
import shutil
import struct
import threading
from pathlib import Path

from app.services import studiov as S

ID_OBJET = re.compile(r"^[a-f0-9]{16}$")
MAX_OCTETS = 30 * 1024 * 1024
MAX_TRIANGLES = 300_000
TRIANGLES_LEGER = 60_000                   # au-delà : le modèle pèse sur une carte intégrée (la fiche le dit)
MAX_BIBLIOTHEQUE = 300
MAX_NOM, MAX_AUTEUR, MAX_URL = 60, 80, 300

SOURCES = ("fichier", "polypizza", "sketchfab", "blenderkit", "polyhaven", "ambientcg", "kenney", "quaternius",
           "blender", "creation", "bibliotheque", "abo")
POSES = ("sol", "mur", "plafond")          # la base à y = 0 ; centré sur son point, le dos au mur ; pendu sous son point
MAX_TITRE = 200
# ce que chaque licence ACCEPTÉE permet (None = à vérifier par l'utilisateur : l'application ne l'affirme pas)
LICENCES = {
    "CC0": {"video": True, "export": True, "partage": True, "credit": False},
    "CC-BY": {"video": True, "export": True, "partage": True, "credit": True},
    "BLENDERKIT-RF": {"video": True, "export": False, "partage": False, "credit": False},
    "CREATION": {"video": True, "export": True, "partage": True, "credit": False},
    "A-VERIFIER": {"video": None, "export": False, "partage": False, "credit": True},
}
# les licences courantes qu'on REFUSE, avec la raison dite à l'utilisateur
REFUSEES = {"CC-BY-NC": "commercial", "CC-BY-NC-SA": "commercial", "CC-BY-NC-ND": "commercial", "CC-BY-ND": "modification",
            "CC-BY-SA": "identique", "STANDARD": "extraction"}
COMPRESSIONS = ("KHR_draco_mesh_compression", "KHR_texture_basisu")
_VERROU = threading.RLock()


class RefusObjet(ValueError):
    """Une demande refusée : `statut` = le code HTTP. Message littéral (traduit par L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


def racine() -> Path:
    return S.racine() / "objets"


# ── lire un GLB sans le charger en 3D ──

def analyser_glb(octets: bytes) -> dict:
    """{triangles, dims: [l, h, p] (m : la boîte de la scène, transformations des nœuds comprises ; sans scène lisible,
    celle des maillages bruts), maillages, images}."""
    if not isinstance(octets, (bytes, bytearray)) or len(octets) < 20 or bytes(octets[:4]) != b"glTF":
        raise RefusObjet("Ce fichier n'est pas un modèle GLB.", 415)
    if len(octets) > MAX_OCTETS:
        raise RefusObjet("Modèle trop lourd : 30 Mo au plus.", 413)
    version, total = struct.unpack_from("<II", octets, 4)
    longueur, genre = struct.unpack_from("<II", octets, 12)
    if version != 2 or genre != 0x4E4F534A or 20 + longueur > len(octets) or total > len(octets):
        raise RefusObjet("Modèle GLB illisible (version 2 attendue).", 415)
    try:
        j = json.loads(bytes(octets[20:20 + longueur]).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise RefusObjet("Modèle GLB illisible (version 2 attendue).", 415) from None
    if not isinstance(j, dict):
        raise RefusObjet("Modèle GLB illisible (version 2 attendue).", 415)
    if set(j.get("extensionsRequired") or []) & set(COMPRESSIONS):
        raise RefusObjet("Ce modèle est compressé (Draco ou Basis) : exportez-le en GLB sans cette compression.", 415)
    for x in list(j.get("buffers") or []) + list(j.get("images") or []):
        uri = x.get("uri") if isinstance(x, dict) else None
        if isinstance(uri, str) and not uri.startswith("data:"):
            raise RefusObjet("Ce GLB renvoie à des fichiers voisins : exportez un GLB autonome (tout dans un seul fichier).", 415)
    acc = j.get("accessors") or []
    nombre = lambda i: acc[i].get("count", 0) if isinstance(i, int) and 0 <= i < len(acc) and isinstance(acc[i], dict) else 0   # noqa: E731
    triangles, lo, hi, boites = 0, [None] * 3, [None] * 3, []
    for m in j.get("meshes") or []:
        propres = []
        for p in (m.get("primitives") or []) if isinstance(m, dict) else []:
            if not isinstance(p, dict) or p.get("mode", 4) != 4:
                continue
            pos = (p.get("attributes") or {}).get("POSITION")
            triangles += nombre(p["indices"] if "indices" in p else pos) // 3
            a = acc[pos] if isinstance(pos, int) and 0 <= pos < len(acc) and isinstance(acc[pos], dict) else {}
            mn, mx = a.get("min"), a.get("max")
            if isinstance(mn, list) and isinstance(mx, list) and len(mn) == 3 and len(mx) == 3:
                try:
                    # un accesseur « normalisé » (modèle quantifié) range des entiers : sa valeur est l'entier / son maximum
                    k0 = _NORMES.get(a.get("componentType"), 1.0) if a.get("normalized") is True else 1.0
                    mn, mx = [max(float(v) / k0, -1.0) if k0 != 1.0 else float(v) for v in mn], [float(v) / k0 for v in mx]
                except (TypeError, ValueError):
                    continue
                propres.append((mn, mx))
                for k in range(3):
                    lo[k] = mn[k] if lo[k] is None else min(lo[k], mn[k])
                    hi[k] = mx[k] if hi[k] is None else max(hi[k], mx[k])
        boites.append(propres)
    if triangles <= 0:
        raise RefusObjet("Ce modèle ne contient aucune surface à afficher.", 415)
    if triangles > MAX_TRIANGLES:
        raise RefusObjet(f"Modèle trop lourd pour un décor en direct : {triangles} triangles (plafond : {MAX_TRIANGLES}).", 413)
    scene = _boite_scene(j, boites)
    if scene:
        lo, hi = scene
    dims = [round(max(0.0, (hi[k] or 0.0) - (lo[k] or 0.0)), 3) for k in range(3)]
    return {"triangles": triangles, "dims": dims, "maillages": len(j.get("meshes") or []), "images": len(j.get("images") or [])}


_NORMES = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}      # le maximum d'un entier normalisé, par type glTF


def _matrice(n: dict) -> list:
    """La transformation d'un nœud glTF, en 3 lignes de 4 (matrice donnée, sinon translation, rotation, échelle)."""
    m = n.get("matrix")
    if isinstance(m, list) and len(m) == 16:
        return [[float(m[c * 4 + r]) for c in range(4)] for r in range(3)]
    t = [float(v) for v in (n.get("translation") or [0, 0, 0])]
    x, y, z, w = [float(v) for v in (n.get("rotation") or [0, 0, 0, 1])]
    e = [float(v) for v in (n.get("scale") or [1, 1, 1])]
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[r[i][0] * e[0], r[i][1] * e[1], r[i][2] * e[2], t[i]] for i in range(3)]


def _boite_scene(j: dict, boites: list):
    """(lo, hi) de la scène, transformations des nœuds comprises, ou None si la scène n'est pas lisible."""
    noeuds, scenes = j.get("nodes"), j.get("scenes")
    if not isinstance(noeuds, list) or not isinstance(scenes, list) or not scenes:
        return None
    i = j.get("scene") if isinstance(j.get("scene"), int) and 0 <= j["scene"] < len(scenes) else 0
    racines = scenes[i].get("nodes") if isinstance(scenes[i], dict) else None
    if not isinstance(racines, list):
        return None
    lo, hi, vus = [None] * 3, [None] * 3, set()
    pile = [(r, [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]) for r in racines]
    try:
        while pile:
            k, parent = pile.pop()
            if not isinstance(k, int) or not 0 <= k < len(noeuds) or k in vus or not isinstance(noeuds[k], dict):
                continue
            vus.add(k)
            n, loc = noeuds[k], _matrice(noeuds[k])
            m = [[sum(parent[a][c] * loc[c][b] for c in range(3)) + (parent[a][3] if b == 3 else 0) for b in range(4)] for a in range(3)]
            mesh = n.get("mesh")
            for mn, mx in (boites[mesh] if isinstance(mesh, int) and 0 <= mesh < len(boites) else []):
                for coin in range(8):
                    p = [mx[a] if coin >> a & 1 else mn[a] for a in range(3)]
                    for a in range(3):
                        v = m[a][0] * p[0] + m[a][1] * p[1] + m[a][2] * p[2] + m[a][3]
                        lo[a] = v if lo[a] is None else min(lo[a], v)
                        hi[a] = v if hi[a] is None else max(hi[a], v)
            pile.extend((c, m) for c in (n.get("children") or []) if isinstance(n.get("children"), list))
    except (TypeError, ValueError, IndexError):
        return None
    return (lo, hi) if None not in lo else None


# ── les droits ──

def licence_propre(licence, source) -> str:
    """La licence RETENUE pour un import, ou un refus qui dit pourquoi."""
    brute = str(licence or "").strip().upper().replace(" ", "-").replace("_", "-")
    brute = re.sub(r"-?[0-9]\.[0-9]$", "", brute)                      # CC-BY-4.0 -> CC-BY
    if brute in ("CC0-1.0", "CC-0", "PUBLIC-DOMAIN", "CC0-1"):
        brute = "CC0"
    raison = REFUSEES.get(brute)
    if raison == "commercial":
        raise RefusObjet("Licence refusée : elle interdit l'usage commercial, donc une vidéo publiée sur une chaîne.", 409)
    if raison == "modification":
        raise RefusObjet("Licence refusée : elle interdit de modifier le modèle, donc de l'habiller.", 409)
    if raison == "identique":
        raise RefusObjet("Licence refusée : elle impose de publier la vidéo sous la même licence.", 409)
    if raison == "extraction":
        raise RefusObjet("Licence refusée : elle interdit de sortir le fichier du service d'origine.", 409)
    if source == "blenderkit" and brute != "CC0":
        return "BLENDERKIT-RF"                                         # tout ce qui n'est pas CC0 chez eux est « Royalty Free »
    if source in ("creation", "bibliotheque"):       # ce que l'utilisateur a fait ou généré dans l'application est à lui
        return "CREATION"
    if source == "abo":                              # le catalogue de produits réels : CC BY 4.0, vérifiée à la source
        return "CC-BY"
    return brute if brute in LICENCES else "A-VERIFIER"


def droits(licence: str) -> dict:
    return dict(LICENCES.get(licence, LICENCES["A-VERIFIER"]))


# ── la bibliothèque ──

def _dossier(oid: str) -> Path:
    if not isinstance(oid, str) or not ID_OBJET.match(oid):
        raise RefusObjet("Identifiant d'objet invalide.", 400)
    return racine() / oid


def _fiche(oid: str) -> dict:
    dossier = _dossier(oid)                    # (hors du try : un refus est un ValueError, il ne doit pas devenir « illisible »)
    try:
        d = json.loads((dossier / "fiche.json").read_text("utf-8"))
    except OSError:
        raise RefusObjet("Objet introuvable.", 404) from None
    except ValueError:
        raise RefusObjet("Objet illisible.", 404) from None
    if not isinstance(d, dict):
        raise RefusObjet("Objet illisible.", 404)
    return d


def _vue(oid: str, d: dict) -> dict:
    lic = d.get("licence") if d.get("licence") in LICENCES else "A-VERIFIER"
    tri = int(d.get("triangles") or 0)
    return {"id": oid, "ref": f"obj:{oid}", "nom": S.K._texte(d.get("nom"), oid, MAX_NOM) or oid,
            "source": d.get("source") if d.get("source") in SOURCES else "fichier",
            "auteur": S.K._texte(d.get("auteur"), "", MAX_AUTEUR), "licence": lic, "url": _url(d.get("url")),
            "triangles": tri, "lourd": tri > TRIANGLES_LEGER, "octets": int(d.get("octets") or 0),
            "dims": d.get("dims") if isinstance(d.get("dims"), list) and len(d["dims"]) == 3 else [0, 0, 0],
            "cree": d.get("cree") or "", "droits": droits(lic), "modele": f"/api/studiov/objets/{oid}/modele.glb",
            "pose": d.get("pose") if d.get("pose") in POSES else "sol", "titre": S.K._texte(d.get("titre"), "", MAX_TITRE)}


def _url(v) -> str:
    """Une adresse http(s) de la page du modèle (jamais suivie par l'application : elle ne sert qu'aux crédits)."""
    v = S.K._texte(v, "", MAX_URL)
    return v if re.match(r"^https?://[^\s<>\"']+$", v) else ""


def lire(oid: str) -> dict:
    return _vue(oid, _fiche(oid))


def chemin(oid: str) -> Path:
    f = _dossier(oid) / "modele.glb"
    if not f.is_file():
        raise RefusObjet("Objet introuvable.", 404)
    return f


def lister() -> list:
    out = []
    if racine().is_dir():
        for d in racine().iterdir():
            if d.is_dir() and ID_OBJET.match(d.name) and (d / "modele.glb").is_file():
                try:
                    out.append(lire(d.name))
                except RefusObjet:
                    continue
    return sorted(out, key=lambda v: v["cree"], reverse=True)


def index() -> dict:
    """{ref: fiche} : ce que le moteur de l'écran reçoit (il ne fabrique aucune adresse depuis la recette)."""
    return {v["ref"]: v for v in lister()}


def par_origine(prefixe: str) -> dict:
    """{origine: ref} des objets dont l'origine commence par `prefixe` (un produit du catalogue n'entre qu'une fois)."""
    out = {}
    for v in lister():
        try:
            o = _fiche(v["id"]).get("origine")
        except RefusObjet:
            continue
        if isinstance(o, str) and o.startswith(prefixe):
            out[o] = v["ref"]
    return out


def importer(octets: bytes, meta: dict | None = None) -> dict:
    """Garde un GLB dans la bibliothèque. `meta` = {nom, source, auteur, licence, url} déclarés à l'import, et pour
    les appelants de l'application {origine, pose, titre}."""
    m = meta if isinstance(meta, dict) else {}
    source = m.get("source") if m.get("source") in SOURCES else "fichier"
    licence = licence_propre(m.get("licence"), source)                 # un refus de licence passe AVANT toute écriture
    mesure = analyser_glb(octets)
    with _VERROU:
        if len(lister()) >= MAX_BIBLIOTHEQUE:
            raise RefusObjet("Bibliothèque d'objets pleine : supprimez-en un d'abord.", 409)
        oid = secrets.token_hex(8)
        d = _dossier(oid)
        d.mkdir(parents=True, exist_ok=False)
        try:
            (d / "modele.glb").write_bytes(bytes(octets))
            fiche = {"nom": S.K._texte(m.get("nom"), "", MAX_NOM) or "Objet importé", "source": source,
                     "auteur": S.K._texte(m.get("auteur"), "", MAX_AUTEUR), "licence": licence, "url": _url(m.get("url")),
                     "octets": len(octets), "cree": S.K._maintenant(), "origine": S.K._texte(m.get("origine"), "", 200),
                     "pose": m.get("pose") if m.get("pose") in POSES else "sol", "titre": S.K._texte(m.get("titre"), "", MAX_TITRE), **mesure}
            S.K._ecrire_json(d / "fiche.json", fiche)
        except OSError:
            shutil.rmtree(d, ignore_errors=True)
            raise RefusObjet("L'objet n'a pas pu être enregistré.", 500) from None
    return lire(oid)


MODELE_BIB = re.compile(r"^model(\.v[0-9]{1,3}|\.opt)?\.glb$")


def depuis_bibliotheque(job, fichier=None) -> dict:
    """Recopie un modèle 3D GÉNÉRÉ dans l'application (Game Assets 3D, Établi : outputs/assets3d/<job>) dans la
    bibliothèque d'objets du studio. Sans `fichier` : la version décimée si elle existe (elle est faite pour le temps
    réel), sinon la dernière version. Le même fichier, inchangé, n'est copié qu'une fois."""
    from app.config import settings
    nom_job = job if isinstance(job, str) and job and Path(job).name == job else ""      # un NOM de dossier, jamais un chemin
    d = settings.outputs_path / "assets3d" / nom_job
    if not nom_job or nom_job.startswith(("_", ".")) or not d.is_dir():
        raise RefusObjet("Modèle 3D introuvable dans la Bibliothèque.", 404)
    if fichier is not None:
        if not isinstance(fichier, str) or not MODELE_BIB.match(fichier) or not (d / fichier).is_file():
            raise RefusObjet("Modèle 3D introuvable dans la Bibliothèque.", 404)
        f = d / fichier
    else:
        versions = sorted((x for x in d.glob("model*.glb") if MODELE_BIB.match(x.name) and x.name != "model.opt.glb"),
                          key=lambda x: int(re.sub(r"[^0-9]", "", x.name) or 1))
        f = d / "model.opt.glb" if (d / "model.opt.glb").is_file() else (versions[-1] if versions else None)
        if f is None:
            raise RefusObjet("Modèle 3D introuvable dans la Bibliothèque.", 404)
    st = f.stat()
    cle = f"assets3d:{nom_job}:{f.name}:{st.st_size}:{st.st_mtime_ns}"
    for v in lister():
        if _fiche(v["id"]).get("origine") == cle:
            return v
    nom = nom_job
    try:
        manifeste = json.loads((d / "asset.json").read_text("utf-8"))
        nom = (manifeste.get("name") if isinstance(manifeste, dict) else None) or nom_job
    except (OSError, ValueError):
        pass
    return importer(f.read_bytes(), {"nom": nom, "source": "bibliotheque", "licence": "CREATION", "origine": cle})


def decors_qui_emploient(oid: str) -> list:
    ref = f"obj:{oid}"
    return [v["nom"] for v in S._tous() if any(o.get("ref") == ref for o in v["objets"])]


def supprimer(oid: str) -> None:
    with _VERROU:
        d = _dossier(oid)
        if not d.is_dir():
            raise RefusObjet("Objet introuvable.", 404)
        emploi = decors_qui_emploient(oid)
        if emploi:
            raise RefusObjet(f"Cet objet est posé dans {len(emploi)} décor(s) : retirez-le d'abord de « {emploi[0]} ».", 409)
        shutil.rmtree(d, ignore_errors=True)


# ── les crédits et les droits d'un décor ──

NOMS_SOURCE = {"polypizza": "Poly Pizza", "sketchfab": "Sketchfab", "blenderkit": "BlenderKit", "polyhaven": "Poly Haven",
               "ambientcg": "ambientCG", "kenney": "Kenney", "quaternius": "Quaternius", "blender": "Blender",
               "creation": "", "fichier": "", "bibliotheque": "", "abo": "Amazon Berkeley Objects"}
# une source dont TOUS les objets se citent d'une seule ligne : (ce que c'est, la mention, l'adresse), en FR puis en EN.
# CC BY 4.0 demande l'auteur, la licence et son adresse, et de dire que le fichier a été modifié.
GROUPES = {"abo": (("Modèles 3D", "par Amazon.com (Amazon Berkeley Objects, CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/), "
                    "fichiers recompressés par CodePawl — https://huggingface.co/datasets/codepawl/abo-glb"),
                   ("3D models", "by Amazon.com (Amazon Berkeley Objects, CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/), "
                    "files recompressed by CodePawl — https://huggingface.co/datasets/codepawl/abo-glb"))}
NOMS_LICENCE = {"CC0": "CC0", "CC-BY": "CC BY", "BLENDERKIT-RF": "BlenderKit Royalty Free", "CREATION": "", "A-VERIFIER": ""}


def credits(decor: dict) -> dict:
    """Ce qu'un décor doit à ses objets importés : les lignes de crédit (obligatoires d'abord), le texte prêt à coller
    dans la description d'une vidéo, et ce que les licences permettent pour le décor ENTIER (export, partage)."""
    vus, lignes, absents = set(), [], 0
    for o in decor.get("objets", []):
        ref = o.get("ref")
        if o.get("type") != "modele" or not isinstance(ref, str) or ref in vus:
            continue
        vus.add(ref)
        try:
            v = lire(ref[4:])
        except RefusObjet:
            absents += 1
            continue
        lignes.append({"ref": ref, "nom": v["titre"] or v["nom"], "auteur": v["auteur"], "licence": v["licence"], "source": v["source"],
                       "url": v["url"], "obligatoire": bool(v["droits"]["credit"]), "a_verifier": v["droits"]["video"] is None,
                       "export": bool(v["droits"]["export"]), "partage": bool(v["droits"]["partage"])})
    # les images venues de la Bibliothèque : celles dont la licence demande un crédit, ou reste à vérifier
    from app.services import studiov_images as SI
    for ref in sorted(SI.emplois(decor)):
        try:
            im = SI.lire(ref[4:])
        except SI.RefusImage:
            absents += 1
            continue
        lic = im["licence"].strip()
        norme = lic.upper().replace(" ", "-")
        if not lic or lic.lower() in ("propriétaire", "proprietaire") or norme.startswith("CC0"):
            continue                                   # à l'utilisateur, ou libre : rien à citer
        du = norme.startswith("CC-BY") and not any(x in norme for x in ("-NC", "-ND", "-SA"))
        lignes.append({"ref": ref, "nom": im["nom"], "auteur": im["auteur"], "licence": "CC-BY" if du else "A-VERIFIER", "source": "bibliotheque",
                       "url": "", "obligatoire": du, "a_verifier": not du, "export": True, "partage": True})
    lignes.sort(key=lambda x: (not x["obligatoire"], x["nom"].lower()))

    def phrase(x, en):
        par = f" {'by' if en else 'par'} {x['auteur']}" if x["auteur"] else ""
        lic = f" ({NOMS_LICENCE[x['licence']]})" if NOMS_LICENCE.get(x["licence"]) else ""
        via = f" {'via' if en else 'via'} {NOMS_SOURCE[x['source']]}" if NOMS_SOURCE.get(x["source"]) else ""
        return f"« {x['nom']} »{par}{lic}{via}{' — ' + x['url'] if x['url'] else ''}" if not en else \
               f"\"{x['nom']}\"{par}{lic}{via}{' — ' + x['url'] if x['url'] else ''}"
    dus = [x for x in lignes if x["obligatoire"]]

    def texte(en):
        seuls = ["- " + phrase(x, en) for x in dus if x["source"] not in GROUPES]
        for source, mentions in GROUPES.items():                   # les objets d'un catalogue : une seule ligne pour tous
            noms = [x["nom"] for x in dus if x["source"] == source]
            if noms:
                quoi, mention = mentions[1 if en else 0]
                seuls.append(f"- {quoi} " + ", ".join(f'"{n}"' if en else f"« {n} »" for n in noms) + f" {mention}")
        return (("Set credits:\n" if en else "Crédits du décor :\n") + "\n".join(seuls)) if seuls else ""
    return {"lignes": lignes, "absents": absents, "texte_fr": texte(False), "texte_en": texte(True),
            "export": all(x["export"] for x in lignes), "partage": all(x["partage"] for x in lignes),
            "a_verifier": [x["nom"] for x in lignes if x["a_verifier"]]}
