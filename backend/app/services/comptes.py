# -*- coding: utf-8 -*-
"""t203 (Espaces de marque E3, 13/10/2026) — PLUSIEURS comptes de diffusion par plateforme, rattachés à un espace.

Un compte = une plateforme (x, telegram, youtube, instagram, tiktok), un libellé, un handle, et ses identifiants :
  - les champs SECRETS (jetons, clés) vivent là où vivent déjà les clés — coffre ouvert, sinon .env — par
    `coffre.enregistrer_cle`, sous un nom propre au compte : `DZC_<ID>_<CHAMP>` (ex. DZC_C1A2B3C4D_X_ACCESS_TOKEN) ;
    un coffre posé mais FERMÉ refuse (CoffreVerrouille) : le secret ne serait gardé qu'en mémoire ;
  - les champs PUBLICS (chat Telegram, chaîne YouTube, compte IG, client TikTok, audit) vivent dans
    `DATA_ROOT/espaces/comptes.json`, avec le libellé et le handle. Aucun secret n'y est jamais écrit.
Les comptes HISTORIQUES : chaque plateforme déjà réglée par les clés plates d'avant (X_ACCESS_TOKEN…) apparaît comme
le compte virtuel `historique-<plateforme>` de l'espace Deepotus ; il LIT ces mêmes clés (rien n'est migré, rien ne
peut casser) et se règle toujours dans Réglages › Connected accounts.

Lecture : `cred.X_ACCESS_TOKEN` / `cred.has_x` remplacent `settings.…` dans les adaptateurs ; sous `sous_compte(id)`
ils lisent le compte, sinon les clés plates (comportement d'avant, à l'octet).
"""
from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.config import DATA_ROOT, settings

# plateforme -> (libellé, [(champ, secret)], champs requis pour publier, OAuth)
PLATEFORMES: dict = {
    "x": ("X", [("X_API_KEY", True), ("X_API_SECRET", True), ("X_ACCESS_TOKEN", True), ("X_ACCESS_SECRET", True)],
          ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"), False),
    "telegram": ("Telegram", [("TELEGRAM_BOT_TOKEN", True), ("TELEGRAM_CHAT_ID", False)],
                 ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"), False),
    "youtube": ("YouTube", [("YOUTUBE_CLIENT_ID", True), ("YOUTUBE_CLIENT_SECRET", True),
                            ("YOUTUBE_REFRESH_TOKEN", True), ("YOUTUBE_CHANNEL_ID", False)],
                ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"), True),
    "instagram": ("Instagram", [("IG_ACCESS_TOKEN", True), ("IG_BUSINESS_ID", False)],
                  ("IG_ACCESS_TOKEN", "IG_BUSINESS_ID"), False),
    "tiktok": ("TikTok", [("TIKTOK_CLIENT_KEY", False), ("TIKTOK_CLIENT_SECRET", True),
                          ("TIKTOK_REFRESH_TOKEN", True), ("TIKTOK_AUDITED", False)],
               ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"), True),
}
_CHAMP_PLAT = {c: p for p, (_l, champs, _r, _o) in PLATEFORMES.items() for c, _s in champs}
_SECRET = {c: s for _p, (_l, champs, _r, _o) in PLATEFORMES.items() for c, s in champs}
_ID = re.compile(r"^c[0-9a-f]{8}$")
HISTO = "historique-"
MAX_COMPTES = 200
MAX = 80
_COMPTE: ContextVar = ContextVar("dz_compte_courant", default=None)


class CompteHistorique(ValueError):
    """Un compte historique se règle dans Réglages › Connected accounts (clés plates)."""


def _fichier() -> Path:
    p = DATA_ROOT / "espaces"
    p.mkdir(parents=True, exist_ok=True)
    return p / "comptes.json"


def _lire() -> dict:
    f = _fichier()
    if f.is_file():
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and isinstance(doc.get("comptes"), dict) and all(_ID.match(k) for k in doc["comptes"]):
                return doc
        except (OSError, ValueError):
            pass
        cote = f.with_name(f"comptes.json.illisible-{datetime.now():%Y%m%d-%H%M%S}")
        f.replace(cote)
        logger.warning(f"comptes.json illisible : mis de côté ({cote.name})")
    return {"comptes": {}}


def _ecrire(doc: dict) -> None:
    f = _fichier()
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def nom_secret(cid: str, champ: str) -> str:
    """Le nom de clé (coffre / .env) d'un champ secret d'un compte : DZC_<ID>_<CHAMP>."""
    if not _ID.match(cid or "") or champ not in _SECRET:
        raise ValueError(f"compte ou champ invalide : {cid}/{champ}")
    return f"DZC_{cid.upper()}_{champ}"


def _valeur_secrete(nom: str) -> str:
    from app.services import coffre
    return (os.environ.get(nom) or coffre.valeur(nom) or "").strip()


# ---- le compte courant ------------------------------------------------------------------------------------------------

def courant():
    return _COMPTE.get()


@contextmanager
def sous_compte(cid):
    """Les adaptateurs lisent les identifiants de `cid` dans ce bloc (None ou historique : les clés plates)."""
    if cid and not cid.startswith(HISTO) and not _ID.match(cid):
        raise KeyError(cid)
    if cid and _ID.match(cid) and cid not in _lire()["comptes"]:
        raise KeyError(cid)
    j = _COMPTE.set(cid if cid and not cid.startswith(HISTO) else None)
    try:
        yield
    finally:
        _COMPTE.reset(j)


def cle(champ: str):
    """La valeur d'un champ pour le compte courant (clé plate sans compte courant)."""
    cid = courant()
    if not cid:
        return getattr(settings, champ)
    e = _lire()["comptes"].get(cid) or {}
    if _SECRET.get(champ):
        return _valeur_secrete(nom_secret(cid, champ))
    v = (e.get("publics") or {}).get(champ)
    if champ == "TIKTOK_AUDITED":
        return bool(v)
    return str(v or "")


def disponible(plateforme: str) -> bool:
    cid = courant()
    if not cid:
        return bool(getattr(settings, f"has_{plateforme}"))
    e = _lire()["comptes"].get(cid) or {}
    if e.get("plateforme") != plateforme:
        return False
    return all(str(cle(c) or "").strip() for c in PLATEFORMES[plateforme][2])


class _Cred:
    """`cred.X_ACCESS_TOKEN`, `cred.has_x` : comme `settings`, mais pour le compte courant s'il y en a un."""

    def __getattr__(self, nom: str):
        if nom.startswith("has_") and nom[4:] in PLATEFORMES:
            return disponible(nom[4:])
        if nom in _CHAMP_PLAT:
            return cle(nom)
        return getattr(settings, nom)


cred = _Cred()


# ---- la liste --------------------------------------------------------------------------------------------------------

def _historiques() -> list:
    out = []
    for p, (lib, champs, _req, oauth) in PLATEFORMES.items():
        if not any(str(getattr(settings, c) or "").strip() for c, _s in champs if c != "TIKTOK_AUDITED"):
            continue
        out.append({"id": HISTO + p, "espace_id": "deepotus", "plateforme": p, "libelle": f"{lib} (historique)",
                    "handle": "", "historique": True, "oauth": oauth, "disponible": bool(getattr(settings, f"has_{p}")),
                    "champs": [{"nom": c, "secret": s, "pose": bool(str(getattr(settings, c) or "").strip()),
                                **({} if s else {"valeur": getattr(settings, c)})} for c, s in champs]})
    return out


def _vue(cid: str, e: dict) -> dict:
    p = e.get("plateforme")
    lib, champs, _req, oauth = PLATEFORMES[p]
    pub = e.get("publics") or {}
    with sous_compte(cid):
        dispo = disponible(p)
        poses = {c: bool(str(cle(c) or "").strip()) for c, s in champs if s}
    return {"id": cid, "espace_id": e.get("espace_id"), "plateforme": p, "libelle": e.get("libelle") or lib,
            "handle": e.get("handle") or "", "historique": False, "oauth": oauth, "disponible": dispo,
            "created_at": e.get("created_at"),
            "champs": [{"nom": c, "secret": s, "pose": poses[c] if s else bool(pub.get(c)),
                        **({} if s else {"valeur": pub.get(c, False if c == "TIKTOK_AUDITED" else "")})}
                       for c, s in champs]}


def lister(espace_id: str | None = None) -> list:
    """Les comptes d'un espace (tous sinon), historiques compris (espace Deepotus). Jamais de valeur secrète."""
    doc = _lire()
    out = [_vue(k, v) for k, v in doc["comptes"].items() if espace_id in (None, v.get("espace_id"))]
    if espace_id in (None, "deepotus"):
        out = _historiques() + out
    return sorted(out, key=lambda v: (not v["historique"], v["plateforme"], v["libelle"].lower()))


def obtenir(cid: str) -> dict:
    for v in lister():
        if v["id"] == cid:
            return v
    raise KeyError(cid)


def _texte(v, n=MAX) -> str:
    return v.strip()[:n] if isinstance(v, str) else ""


def creer(champs: dict) -> dict:
    from app.services import espaces
    eid = champs.get("espace_id") or espaces.lire()["actif"]
    if eid not in espaces.lire()["espaces"]:
        raise KeyError(eid)
    p = champs.get("plateforme")
    if p not in PLATEFORMES:
        raise ValueError(f"plateforme inconnue : {p} — connues : {', '.join(PLATEFORMES)}")
    doc = _lire()
    if len(doc["comptes"]) >= MAX_COMPTES:
        raise ValueError(f"{MAX_COMPTES} comptes au plus")
    cid = "c" + uuid.uuid4().hex[:8]
    doc["comptes"][cid] = {"espace_id": eid, "plateforme": p, "libelle": _texte(champs.get("libelle")) or PLATEFORMES[p][0],
                           "handle": _texte(champs.get("handle")), "publics": {},
                           "created_at": datetime.now().isoformat(timespec="seconds")}
    _ecrire(doc)
    if isinstance(champs.get("valeurs"), dict) and champs["valeurs"]:
        poser(cid, champs["valeurs"])
    return obtenir(cid)


def _propre(cid: str) -> dict:
    if (cid or "").startswith(HISTO):
        raise CompteHistorique("compte historique : il se règle dans Réglages › Connected accounts")
    doc = _lire()
    if cid not in doc["comptes"]:
        raise KeyError(cid)
    return doc


def modifier(cid: str, champs: dict) -> dict:
    doc = _propre(cid)
    e = doc["comptes"][cid]
    if "libelle" in champs:
        e["libelle"] = _texte(champs.get("libelle")) or PLATEFORMES[e["plateforme"]][0]
    if "handle" in champs:
        e["handle"] = _texte(champs.get("handle"))
    _ecrire(doc)
    if isinstance(champs.get("valeurs"), dict) and champs["valeurs"]:
        poser(cid, champs["valeurs"])
    return obtenir(cid)


def poser(cid: str, valeurs: dict) -> list:
    """Écrit des champs du compte (valeur vide = effacer). Secrets : coffre ouvert, sinon .env ; coffre posé mais fermé
    -> CoffreVerrouille AVANT toute écriture. Rend les champs écrits. ValueError = champ étranger à la plateforme."""
    from app.services import coffre
    doc = _propre(cid)
    e = doc["comptes"][cid]
    autorises = dict(PLATEFORMES[e["plateforme"]][1])
    for c in valeurs:
        if c not in autorises:
            raise ValueError(f"{c} n'est pas un champ d'un compte {PLATEFORMES[e['plateforme']][0]}")
    if any(autorises[c] for c in valeurs) and coffre.verrouille():
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le avant d'enregistrer un secret")
    for c, v in valeurs.items():
        if autorises[c]:
            _secret_ecrire(nom_secret(cid, c), str(v or "").strip())
        elif c == "TIKTOK_AUDITED":
            e.setdefault("publics", {})[c] = bool(v) and str(v).strip().lower() not in ("0", "false", "non", "no")
        else:
            e.setdefault("publics", {})[c] = _texte(v, 200)
    _ecrire(doc)
    return list(valeurs)


def _secret_ecrire(nom: str, valeur_: str) -> str:
    from app.services import coffre
    if valeur_:
        return coffre.enregistrer_cle(nom, valeur_)
    if coffre.ouvert() and coffre.lire_cle(nom) is not None:
        coffre.ecrire_cle(nom, "")
    if nom in coffre.lire_env():         # écrit au .env avant que le coffre soit posé ou ouvert : effacé là aussi
        coffre._ecrire_env({}, {nom})
    os.environ.pop(nom, None)
    return "efface"


def garder_secret(champ: str, valeur_: str) -> str:
    """Un ADAPTATEUR reçoit un secret neuf (refresh token tournant de TikTok, jeton OAuth) : rangé dans le compte
    courant, sinon dans la clé plate d'avant. Rend l'endroit (coffre | env | memoire)."""
    from app.services import coffre
    cid = courant()
    if not cid:
        return coffre.enregistrer_cle(champ, valeur_)
    return coffre.enregistrer_cle(nom_secret(cid, champ), valeur_)


def supprimer(cid: str) -> None:
    """Retire le compte ET efface ses secrets (coffre posé mais fermé : refus avant tout)."""
    from app.services import coffre
    doc = _propre(cid)
    e = doc["comptes"][cid]
    secrets_ = [c for c, s in PLATEFORMES[e["plateforme"]][1] if s]
    if coffre.verrouille() and any(_valeur_secrete(nom_secret(cid, c)) for c in secrets_):
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le pour effacer les secrets de ce compte")
    for c in secrets_:
        _secret_ecrire(nom_secret(cid, c), "")
    doc["comptes"].pop(cid)
    _ecrire(doc)


def de_l_espace(cid: str, espace_id: str) -> bool:
    """Le compte appartient-il à l'espace ? (la garde de t204 : jamais un post client sur un compte Deepotus)."""
    if (cid or "").startswith(HISTO):
        return espace_id == "deepotus"
    return (_lire()["comptes"].get(cid) or {}).get("espace_id") == espace_id


# ---- t204 (Espaces de marque E4) : les comptes CIBLES d'un post du Planificateur ---------------------------------------

def espace_du_post(espace_id) -> str:
    """Un post d'avant les espaces (espace_id vide) appartient à Deepotus."""
    return espace_id or "deepotus"


def verifier_cibles(espace_id, ids) -> list:
    """Les vues des comptes cibles d'un post, dans l'ordre, sans doublon. KeyError = compte inconnu ; PermissionError =
    compte d'un AUTRE espace (jamais un post client sur un compte Deepotus, ni l'inverse)."""
    if ids is None:
        return []
    if not isinstance(ids, list):
        raise ValueError("comptes doit être une liste d'identifiants")
    eid, out, vus = espace_du_post(espace_id), [], set()
    for cid in ids:
        if not isinstance(cid, str) or cid in vus:
            continue
        v = obtenir(cid)
        if not de_l_espace(cid, eid):
            raise PermissionError(f"le compte {v['libelle']} ({cid}) n'appartient pas à l'espace de ce post")
        out.append(v)
        vus.add(cid)
    return out


def cle_distante(vue: dict) -> str:
    """La clé de remote_ids d'une cible : le nom du canal pour un compte historique (comme avant), sinon
    « canal:id » — deux comptes X d'un même post ne se marchent jamais dessus."""
    return vue["plateforme"] if vue.get("historique") else f"{vue['plateforme']}:{vue['id']}"


def cle_quota(canal: str, cid) -> str:
    """Le compteur de quota d'une publication : par COMPTE (« x@c1a2b3c4d ») ; sans compte ou historique, le canal."""
    return f"{canal}@{cid}" if cid and _ID.match(cid) else canal
