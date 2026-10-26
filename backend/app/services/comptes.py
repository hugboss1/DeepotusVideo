# -*- coding: utf-8 -*-
"""t203 (Espaces de marque E3, 13/10/2026) — PLUSIEURS comptes de diffusion par plateforme, rattachés à un espace.

Un compte = une plateforme (x, telegram, youtube, instagram, tiktok ; whatsapp depuis t310), un libellé, un handle, et ses identifiants :
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

t308 (26/10/2026) — la VÉRIFICATION d'un compte (services/verif_canaux.py) est rangée à part, datée, dans la clé de premier
niveau `verifications` de comptes.json (`{compte: {etat, raison, date, id_distant, nom_distant}}`) : jamais de secret. Réécrire
un champ du compte (`poser`) ou le supprimer l'efface : la vue redevient « non vérifié ». Le `canal_id` (`<plateforme>:<id
distant>`, expression de t306) vient de là. Un compte peut aussi être PORTÉ PAR LE TÉLÉPHONE (`porte_par`) : la vérification
ne lit alors ni secret ni réseau, elle reprend la déclaration de l'appareil.

t310 (27/10/2026) — WhatsApp par Kapso (spec §6.1). La plateforme `whatsapp` garde la forme à 4 positions, mais elle n'a
AUCUN secret par compte : la clé Kapso est PLATE et partagée par tous les espaces (`CLE_PLATE`, lue par `cle_kapso`), et
ses champs publics (client Kapso, numéro…) sont posés par la liaison (`poser_publics_serveur`), jamais saisis. Elle n'a
pas de compte historique (`SANS_HISTORIQUE`) et n'est jamais une cible de publication (`NON_PUBLIABLES`).
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
    # t310 (27/10/2026) : aucun champ secret — la clé Kapso est plate (CLE_PLATE) ; tous ces champs sont posés par la liaison
    "whatsapp": ("WhatsApp", [("KAPSO_CUSTOMER_ID", False), ("WHATSAPP_PHONE_ID", False), ("WHATSAPP_NUMERO", False),
                              ("WHATSAPP_WABA_ID", False), ("WHATSAPP_FACTURATION_META", False)],
                 ("WHATSAPP_PHONE_ID",), False),
}
# t310 (27/10/2026) : les particularités d'une plateforme vivent à part (PLATEFORMES garde 4 positions, décompressées partout)
CLE_PLATE = {"whatsapp": "KAPSO_API_KEY"}         # plateforme -> clé plate partagée par tous les espaces (jamais par compte)
SANS_HISTORIQUE = frozenset({"whatsapp"})         # pas de compte virtuel `historique-<p>` (la clé plate n'est pas un compte)
NON_PUBLIABLES = frozenset({"whatsapp"})          # jamais la cible d'un post du Planificateur
_LIES_PAR_SERVEUR = frozenset({"whatsapp"})       # champs publics posés par la liaison, jamais saisis
_CHAMP_PLAT = {c: p for p, (_l, champs, _r, _o) in PLATEFORMES.items() for c, _s in champs}
_SECRET = {c: s for _p, (_l, champs, _r, _o) in PLATEFORMES.items() for c, s in champs}
_ID = re.compile(r"^c[0-9a-f]{8}$")
_NOM_COMPTE = re.compile(r"^DZC_(C[0-9A-F]{8})_")      # t326 revue finale : DZC_<ID>_<CHAMP> (voir nom_secret)
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
                if "verifications" in doc and not isinstance(doc["verifications"], dict):
                    doc.pop("verifications")          # t308 : tolérée absente ou abîmée (« non vérifié »)
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


def _cle_plate(plateforme: str) -> str:
    """t310 (27/10/2026) : la clé PLATE partagée d'une plateforme (`CLE_PLATE`) : `settings`, puis le coffre (.env ou coffre
    ouvert), "" si absente. Ne lève jamais, même coffre posé et fermé."""
    nom = CLE_PLATE.get(plateforme)
    if not nom:
        return ""
    try:
        v = str(getattr(settings, nom, "") or "").strip()
        if v:
            return v
        from app.services import coffre
        return str(coffre.valeur(nom) or "").strip()
    except Exception:  # noqa: BLE001 — une lecture de clé ne casse jamais la liste des comptes
        return ""


def cle_kapso() -> str:
    """t310 (27/10/2026) : la clé Kapso plate (KAPSO_API_KEY), partagée par tous les espaces ; "" si absente. Ne lève jamais."""
    return _cle_plate("whatsapp")


def champs_poses_par_serveur(plateforme: str) -> tuple:
    """t310 (27/10/2026) : les champs d'une plateforme posés par la liaison (service), jamais saisis par l'utilisateur."""
    if plateforme not in _LIES_PAR_SERVEUR:
        return ()
    return tuple(c for c, s in PLATEFORMES[plateforme][1] if not s)


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
        if _CHAMP_PLAT.get(champ) in SANS_HISTORIQUE:      # t310 : aucun champ plat (pas de compte historique)
            return ""
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
        if plateforme in SANS_HISTORIQUE:                 # t310 : rien ne se publie « sans compte » sur whatsapp
            return False
        return bool(getattr(settings, f"has_{plateforme}"))
    e = _lire()["comptes"].get(cid) or {}
    if e.get("plateforme") != plateforme:
        return False
    if plateforme in CLE_PLATE and not _cle_plate(plateforme):     # t310 : la clé Kapso plate ET les requis du compte
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

def _historiques(verifs: dict | None = None) -> list:
    verifs = (_lire().get("verifications") or {}) if verifs is None else verifs
    out = []
    for p, (lib, champs, _req, oauth) in PLATEFORMES.items():
        if p in SANS_HISTORIQUE:      # t310 : une clé plate partagée (Kapso) n'est pas un compte, ses champs pas dans Settings
            continue
        if not any(str(getattr(settings, c) or "").strip() for c, _s in champs if c != "TIKTOK_AUDITED"):
            continue
        out.append({"id": HISTO + p, "espace_id": "deepotus", "plateforme": p, "libelle": f"{lib} (historique)",
                    "handle": "", "historique": True, "oauth": oauth, "disponible": bool(getattr(settings, f"has_{p}")),
                    **_verif_vue(p, verifs.get(HISTO + p)),
                    "champs": [{"nom": c, "secret": s, "pose": bool(str(getattr(settings, c) or "").strip()),
                                **({} if s else {"valeur": getattr(settings, c)})} for c, s in champs]})
    return out


def _verif_vue(p: str, verif) -> dict:
    """Les clés de vue d'une vérification : `verification` (dict ou None) et `canal_id` (str ou None)."""
    verif = verif if isinstance(verif, dict) else None
    return {"verification": verif, "canal_id": canal_id({"plateforme": p, "verification": verif})}


def canal_id(vue: dict):
    """t308 : `<plateforme>:<id distant>` si la vérification du compte porte un id distant qui passe l'expression de t306
    (`fiche_client.CANAL_ID`), sinon None (canal jamais vérifié : le consentement du client est alors « manquant »)."""
    from app.services import fiche_client
    vue = vue or {}
    verif = vue.get("verification")
    idd = verif.get("id_distant") if isinstance(verif, dict) else None
    if not isinstance(idd, str) or not idd or not isinstance(vue.get("plateforme"), str):
        return None
    c = f"{vue['plateforme']}:{idd}"
    return c if fiche_client.CANAL_ID.match(c) else None


def _vue(cid: str, e: dict, verifs: dict | None = None) -> dict:
    verifs = (_lire().get("verifications") or {}) if verifs is None else verifs
    p = e.get("plateforme")
    lib, champs, _req, oauth = PLATEFORMES[p]
    pub = e.get("publics") or {}
    if isinstance(e.get("porte_par"), dict):
        # t308 : canal PORTÉ PAR LE TÉLÉPHONE — le PC ne lit jamais ses secrets (même s'il en existe au même nom)
        dispo, poses = False, {c: False for c, s in champs if s}
    else:
        with sous_compte(cid):
            dispo = disponible(p)
            poses = {c: bool(str(cle(c) or "").strip()) for c, s in champs if s}
    return {"id": cid, "espace_id": e.get("espace_id"), "plateforme": p, "libelle": e.get("libelle") or lib,
            "handle": e.get("handle") or "", "historique": False, "oauth": oauth, "disponible": dispo,
            "created_at": e.get("created_at"),
            **_verif_vue(p, verifs.get(cid)),
            **({"porte_par": _porte_par_vue(e["porte_par"])} if isinstance(e.get("porte_par"), dict) else {}),
            # t310 : la clé plate partagée (Kapso) — son NOM et si elle est posée, jamais sa valeur
            **({"cle_plate": {"nom": CLE_PLATE[p], "posee": bool(_cle_plate(p))}} if p in CLE_PLATE else {}),
            "champs": [{"nom": c, "secret": s, "pose": poses[c] if s else bool(pub.get(c)),
                        **({} if s else {"valeur": pub.get(c, False if c == "TIKTOK_AUDITED" else "")})}
                       for c, s in champs]}


def lister(espace_id: str | None = None) -> list:
    """Les comptes d'un espace (tous sinon), historiques compris (espace Deepotus). Jamais de valeur secrète."""
    doc = _lire()
    verifs = doc.get("verifications") or {}
    out = [_vue(k, v, verifs) for k, v in doc["comptes"].items() if espace_id in (None, v.get("espace_id"))]
    if espace_id in (None, "deepotus"):
        out = _historiques(verifs) + out
    return sorted(out, key=lambda v: (not v["historique"], v["plateforme"], v["libelle"].lower()))


def obtenir(cid: str) -> dict:
    """La vue d'UN compte (sans calculer celle des autres : une vérification ne lit que les secrets du compte visé)."""
    if (cid or "").startswith(HISTO):
        for v in _historiques():
            if v["id"] == cid:
                return v
        raise KeyError(cid)
    doc = _lire()
    if cid not in doc["comptes"]:
        raise KeyError(cid)
    return _vue(cid, doc["comptes"][cid], doc.get("verifications") or {})


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
    if isinstance(champs.get("valeurs"), dict):
        _verifier_valeurs(p, champs["valeurs"])          # t310 : refus AVANT de créer le compte (rien d'écrit)
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


def _verifier_valeurs(p: str, valeurs: dict) -> None:
    """Les champs saisis : chacun doit être un champ de la plateforme, et aucun ne doit être posé par la liaison (t310 :
    les champs whatsapp ; la clé Kapso plate n'est le champ d'aucun compte). ValueError sinon, avant toute écriture."""
    autorises = dict(PLATEFORMES[p][1])
    poses = champs_poses_par_serveur(p)
    for c in valeurs:
        if c not in autorises:
            raise ValueError(f"{c} n'est pas un champ d'un compte {PLATEFORMES[p][0]}")
        if c in poses:
            raise ValueError(f"{c} est posé par la liaison du compte, jamais saisi")


def modifier(cid: str, champs: dict) -> dict:
    doc = _propre(cid)
    e = doc["comptes"][cid]
    if isinstance(champs.get("valeurs"), dict):
        _verifier_valeurs(e["plateforme"], champs["valeurs"])    # t310 : refus AVANT d'écrire libellé et handle
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
    _verifier_valeurs(e["plateforme"], valeurs)
    if any(autorises[c] for c in valeurs) and coffre.verrouille():
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le avant d'enregistrer un secret")
    if valeurs:
        # t308 (26/10/2026) : le compte change -> « non vérifié », et sa révision change (une vérification en vol qui finit
        # après ce poser ne range rien). Écrit AVANT les secrets : un échec n'en laisse pas de périmée.
        _perimer(doc, cid)
        _ecrire(doc)
    for c, v in valeurs.items():
        if autorises[c]:
            _secret_ecrire(nom_secret(cid, c), str(v or "").strip())
        elif c == "TIKTOK_AUDITED":
            e.setdefault("publics", {})[c] = bool(v) and str(v).strip().lower() not in ("0", "false", "non", "no")
        else:
            e.setdefault("publics", {})[c] = _texte(v, 200)
    _ecrire(doc)
    return list(valeurs)


def poser_publics_serveur(cid: str, valeurs: dict) -> list:
    """t310 (27/10/2026) : le SERVICE de liaison (whatsapp) écrit les champs publics qu'il a relevés chez le fournisseur
    (`champs_poses_par_serveur`). Comme `poser` : la révision change et la vérification est retirée. Rend les champs
    écrits. ValueError = champ hors de ceux posés par la liaison (jamais un secret, jamais la clé plate)."""
    doc = _propre(cid)
    e = doc["comptes"][cid]
    permis = champs_poses_par_serveur(e["plateforme"])
    for c in valeurs:
        if c not in permis:
            raise ValueError(f"{c} n'est pas un champ d'un compte {PLATEFORMES[e['plateforme']][0]}")
    if not valeurs:
        return []
    _perimer(doc, cid)
    for c, v in valeurs.items():
        e.setdefault("publics", {})[c] = _texte("" if v is None else str(v), 200)
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
    (doc.get("verifications") or {}).pop(cid, None)
    _ecrire(doc)


# ---- t308 (26/10/2026) : la vérification enregistrée et le canal porté par le téléphone -----------------------------------------------
# Un compte HISTORIQUE reste lié aux clés plates (Réglages › Connected accounts) : t326 (26/10/2026) : sa vérification est
# désormais retirée (et sa révision change, dans `rev_historiques`) quand ces clés sont réécrites : `perimer_historiques`.

ETATS = ("vert", "orange", "rouge")
_PORTE_CLES = ("appareil_id", "appareil_nom", "verifie_le", "etat", "id_distant")


def revision(cid: str):
    """La révision du compte (changée par `poser` et `porter_par_telephone` ; "" avant la première). t326 (26/10/2026) : un
    compte historique a aussi sa révision (`rev_historiques`, changée par `perimer_historiques`). KeyError = compte inconnu."""
    if (cid or "").startswith(HISTO):
        p = cid[len(HISTO):]
        if p not in PLATEFORMES:
            raise KeyError(cid)
        return str((_lire().get("rev_historiques") or {}).get(p) or "")
    e = _lire()["comptes"].get(cid)
    if e is None:
        raise KeyError(cid)
    return str(e.get("rev") or "")


def _perimer(doc: dict, cid: str) -> None:
    """Le compte a changé : sa vérification est retirée et, pour un compte non historique, sa révision change (une
    vérification en vol relevée avant ne range rien). N'écrit pas : l'appelant écrit `doc`."""
    (doc.get("verifications") or {}).pop(cid, None)
    if cid in doc["comptes"]:
        doc["comptes"][cid]["rev"] = uuid.uuid4().hex[:8]
    elif cid.startswith(HISTO) and cid[len(HISTO):] in PLATEFORMES:
        doc.setdefault("rev_historiques", {})[cid[len(HISTO):]] = uuid.uuid4().hex[:8]     # t326 (26/10/2026)


def perimer_historiques(noms: list) -> list:
    """t326 (26/10/2026) : des clés plates ont été réécrites (Réglages › Connected accounts). Pour chaque plateforme dont un
    des `noms` est un champ, la vérification de `historique-<p>` est retirée et sa révision change. Une seule écriture, et
    aucune s'il n'y a rien à périmer. Rend les ids périmés (triés). Ne lève pas pour un nom inconnu."""
    plats = sorted({_CHAMP_PLAT[n] for n in (noms or []) if n in _CHAMP_PLAT})
    if not plats:
        return []
    doc = _lire()
    ids = [HISTO + p for p in plats]
    for cid in ids:
        _perimer(doc, cid)
    _ecrire(doc)
    return sorted(ids)


def perimer_apres_restauration(noms: list) -> list:
    """t326 revue finale (26/10/2026) : une archive du coffre vient de réécrire des clés (plates et `DZC_<ID>_<CHAMP>`).
    Les historiques dont une clé plate est dans `noms` sont périmés (`perimer_historiques`) ; chaque compte d'espace dont
    une clé `DZC_<ID>_*` est dans `noms` perd sa vérification (`oublier_verification`). Un id inconnu est ignoré.
    Rend les ids périmés (triés). À appeler après une restauration réussie seulement."""
    ids = set(perimer_historiques(noms))
    for n in noms or []:
        m = _NOM_COMPTE.match(str(n))
        if not m:
            continue
        cid = m.group(1).lower()
        try:
            oublier_verification(cid)
            ids.add(cid)
        except KeyError:
            pass
    return sorted(ids)


def oublier_verification(cid: str) -> None:
    """t308 relecture finale (26/10/2026) : l'identité distante du compte a pu changer sans qu'un champ soit réécrit par
    `poser` (reconnexion OAuth : autre chaîne, autre compte TikTok). Retire sa vérification et change sa révision, comme
    `poser`. Pas appelée par `garder_secret` : TikTok y fait tourner son refresh token PENDANT une vérification.
    KeyError = compte inconnu."""
    doc = _lire()
    if (cid or "").startswith(HISTO):
        if cid[len(HISTO):] not in PLATEFORMES:
            raise KeyError(cid)
    elif cid not in doc["comptes"]:
        raise KeyError(cid)
    _perimer(doc, cid)
    _ecrire(doc)


def _date_res(d) -> str:
    """t326 (26/10/2026) : la date d'un résultat si c'est une chaîne ISO lisible (date de l'appareil pour un canal porté par le
    téléphone), sinon maintenant."""
    if isinstance(d, str):
        try:
            return datetime.fromisoformat(d).isoformat(timespec="seconds")
        except ValueError:
            pass
    return datetime.now().isoformat(timespec="seconds")


def noter_verification(cid: str, res: dict, rev=None):
    """Range la vérification d'un compte (aussi `historique-<p>`) : {etat, raison, code, date, id_distant, nom_distant}. Rend
    la vérification rangée. KeyError = compte inconnu. Aucun secret : `res` vient de verif_canaux (déjà nettoyé).
    `rev` (relevée AVANT l'appel réseau) : si le compte a changé depuis, rien n'est rangé et la fonction rend None."""
    doc = _lire()
    if (cid or "").startswith(HISTO):
        if cid[len(HISTO):] not in PLATEFORMES:
            raise KeyError(cid)
    elif cid not in doc["comptes"]:
        raise KeyError(cid)
    if rev is not None:
        actuelle = ((doc.get("rev_historiques") or {}).get(cid[len(HISTO):]) if cid.startswith(HISTO)
                    else doc["comptes"][cid].get("rev"))
        if str(actuelle or "") != rev:
            return None
    res = res if isinstance(res, dict) else {}

    def _t(v, n):
        return None if v is None else str(v)[:n]
    verif = {"etat": res.get("etat") if res.get("etat") in ETATS else "orange", "raison": _t(res.get("raison"), 200) or "",
             "code": _t(res.get("code"), 40), "date": _date_res(res.get("date")), "id_distant": _t(res.get("id_distant"), 200),
             "nom_distant": _t(res.get("nom_distant"), 200)}
    # t308 relecture finale (26/10/2026) : un résultat SANS identité (réseau, 5xx, 429, quota, refus) ne l'efface pas. La
    # vérification d'avant existe encore, donc le compte n'a pas été réécrit depuis (poser, porter_par_telephone,
    # oublier_verification et supprimer la retirent) : son identité ne peut pas avoir changé. État, raison et code sont neufs.
    avant = (doc.get("verifications") or {}).get(cid)
    if verif["id_distant"] is None and isinstance(avant, dict) and avant.get("id_distant"):
        verif["id_distant"], verif["nom_distant"] = avant.get("id_distant"), avant.get("nom_distant")
    doc.setdefault("verifications", {})[cid] = verif
    _ecrire(doc)
    return verif


def _porte_par_vue(pp: dict) -> dict:
    return {k: pp.get(k) for k in _PORTE_CLES}


def porter_par_telephone(cid: str, declaration: dict) -> dict:
    """Marque le canal d'un compte comme PORTÉ PAR LE TÉLÉPHONE (service seulement : l'écriture du téléphone viendra en
    L4.2, aucune route). `declaration` = {appareil_id, appareil_nom, verifie_le (ISO|None), etat (vert|orange|rouge|None),
    id_distant (str|None)}. Efface la vérification d'avant (la déclaration la remplace). Rend la vue. ValueError = forme
    refusée, CompteHistorique = compte d'avant les espaces, KeyError = compte inconnu."""
    from app.services import fiche_client
    doc = _propre(cid)
    if not isinstance(declaration, dict):
        raise ValueError("déclaration du téléphone : un objet est attendu")
    for k in declaration:
        if k not in _PORTE_CLES:
            raise ValueError("déclaration du téléphone : champ inconnu")
    out = {}
    for k in ("appareil_id", "appareil_nom"):
        v = declaration.get(k)
        if not isinstance(v, str) or not v.strip():
            raise ValueError("déclaration du téléphone : identifiant et nom de l'appareil requis")
        out[k] = v.strip()[:80]
    vl = declaration.get("verifie_le")
    if vl is not None:
        try:
            if not isinstance(vl, str):
                raise ValueError(vl)
            vl = datetime.fromisoformat(vl).isoformat(timespec="seconds")
        except ValueError:
            raise ValueError("déclaration du téléphone : date de vérification illisible (ISO attendu)") from None
    out["verifie_le"] = vl
    et = declaration.get("etat")
    if et is not None and et not in ETATS:
        raise ValueError("déclaration du téléphone : état inconnu (vert, orange ou rouge)")
    out["etat"] = et
    idd = declaration.get("id_distant") or None
    if idd is not None and (not isinstance(idd, str)
                            or not fiche_client.CANAL_ID.match(f"{doc['comptes'][cid]['plateforme']}:{idd}")):
        raise ValueError("déclaration du téléphone : identifiant distant invalide")
    out["id_distant"] = idd
    doc["comptes"][cid]["porte_par"] = out
    _perimer(doc, cid)
    _ecrire(doc)
    return obtenir(cid)


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
        if v["plateforme"] in NON_PUBLIABLES:      # t310 (27/10/2026) : WhatsApp est un canal de messages, pas de posts
            raise ValueError("un compte WhatsApp n'est pas une cible de publication")
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
