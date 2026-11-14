# -*- coding: utf-8 -*-
"""SVO (15/11/2026) — la BIBLIOTHÈQUE D'OBJETS IMPORTÉS du studio virtuel : les modèles 3D (GLB) que l'utilisateur fait
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
le moteur ne sait pas ouvrir, poids en triangles. Aucun réseau, aucune dépense."""
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
           "blender", "creation")
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
COMPRESSIONS = ("KHR_draco_mesh_compression", "EXT_meshopt_compression", "KHR_texture_basisu")
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
    """{triangles, dims: [l, h, p] (m, approché : sans les transformations des nœuds), maillages, images}."""
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
        raise RefusObjet("Ce modèle est compressé (Draco, Meshopt ou Basis) : exportez-le en GLB sans compression.", 415)
    for x in list(j.get("buffers") or []) + list(j.get("images") or []):
        uri = x.get("uri") if isinstance(x, dict) else None
        if isinstance(uri, str) and not uri.startswith("data:"):
            raise RefusObjet("Ce GLB renvoie à des fichiers voisins : exportez un GLB autonome (tout dans un seul fichier).", 415)
    acc = j.get("accessors") or []
    nombre = lambda i: acc[i].get("count", 0) if isinstance(i, int) and 0 <= i < len(acc) and isinstance(acc[i], dict) else 0   # noqa: E731
    triangles, lo, hi = 0, [None] * 3, [None] * 3
    for m in j.get("meshes") or []:
        for p in (m.get("primitives") or []) if isinstance(m, dict) else []:
            if not isinstance(p, dict) or p.get("mode", 4) != 4:
                continue
            pos = (p.get("attributes") or {}).get("POSITION")
            triangles += nombre(p["indices"] if "indices" in p else pos) // 3
            a = acc[pos] if isinstance(pos, int) and 0 <= pos < len(acc) and isinstance(acc[pos], dict) else {}
            mn, mx = a.get("min"), a.get("max")
            if isinstance(mn, list) and isinstance(mx, list) and len(mn) == 3 and len(mx) == 3:
                for k in range(3):
                    try:
                        lo[k] = float(mn[k]) if lo[k] is None else min(lo[k], float(mn[k]))
                        hi[k] = float(mx[k]) if hi[k] is None else max(hi[k], float(mx[k]))
                    except (TypeError, ValueError):
                        pass
    if triangles <= 0:
        raise RefusObjet("Ce modèle ne contient aucune surface à afficher.", 415)
    if triangles > MAX_TRIANGLES:
        raise RefusObjet(f"Modèle trop lourd pour un décor en direct : {triangles} triangles (plafond : {MAX_TRIANGLES}).", 413)
    dims = [round(max(0.0, (hi[k] or 0.0) - (lo[k] or 0.0)), 3) for k in range(3)]
    return {"triangles": triangles, "dims": dims, "maillages": len(j.get("meshes") or []), "images": len(j.get("images") or [])}


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
    if source == "creation":
        return "CREATION"
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
            "cree": d.get("cree") or "", "droits": droits(lic), "modele": f"/api/studiov/objets/{oid}/modele.glb"}


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


def importer(octets: bytes, meta: dict | None = None) -> dict:
    """Garde un GLB dans la bibliothèque. `meta` = {nom, source, auteur, licence, url} déclarés à l'import."""
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
                     "octets": len(octets), "cree": S.K._maintenant(), **mesure}
            S.K._ecrire_json(d / "fiche.json", fiche)
        except OSError:
            shutil.rmtree(d, ignore_errors=True)
            raise RefusObjet("L'objet n'a pas pu être enregistré.", 500) from None
    return lire(oid)


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
               "creation": "", "fichier": ""}
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
        lignes.append({"ref": ref, "nom": v["nom"], "auteur": v["auteur"], "licence": v["licence"], "source": v["source"],
                       "url": v["url"], "obligatoire": bool(v["droits"]["credit"]), "a_verifier": v["droits"]["video"] is None,
                       "export": bool(v["droits"]["export"]), "partage": bool(v["droits"]["partage"])})
    lignes.sort(key=lambda x: (not x["obligatoire"], x["nom"].lower()))

    def phrase(x, en):
        par = f" {'by' if en else 'par'} {x['auteur']}" if x["auteur"] else ""
        lic = f" ({NOMS_LICENCE[x['licence']]})" if NOMS_LICENCE.get(x["licence"]) else ""
        via = f" {'via' if en else 'via'} {NOMS_SOURCE[x['source']]}" if NOMS_SOURCE.get(x["source"]) else ""
        return f"« {x['nom']} »{par}{lic}{via}{' — ' + x['url'] if x['url'] else ''}" if not en else \
               f"\"{x['nom']}\"{par}{lic}{via}{' — ' + x['url'] if x['url'] else ''}"
    dus = [x for x in lignes if x["obligatoire"]]
    return {"lignes": lignes, "absents": absents,
            "texte_fr": ("Modèles 3D du décor :\n" + "\n".join("- " + phrase(x, False) for x in dus)) if dus else "",
            "texte_en": ("3D models in the set:\n" + "\n".join("- " + phrase(x, True) for x in dus)) if dus else "",
            "export": all(x["export"] for x in lignes), "partage": all(x["partage"] for x in lignes),
            "a_verifier": [x["nom"] for x in lignes if x["a_verifier"]]}
