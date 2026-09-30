"""Coffre à mot de passe maître + archive portable (plan Settings T15-T16 — tâche #20 du suivi, 29/09/2026).

Décisions de l'utilisateur (29/09) : la roue `cryptography` est ajoutée (la stdlib embarquée n'a pas d'AES) ; DPAPI ne
sert qu'à « retenir sur ce PC » ; le coffre et son sceau ne partent JAMAIS par le transfert entre machines (ils sont
dans les secrets de `transfert.py`) — les clés voyagent par l'ARCHIVE chiffrée, avec son propre mot de passe.

FORMAT `DZKV1`, figé ici et LU par le futur compagnon mobile (il ne l'écrit pas) :

    octets  0..5   b"DZKV1\\n"              magie + version de format
    octets  6..21  sel                      16 o aléatoires
    octets 22..25  itérations PBKDF2        uint32 gros-boutiste
    octets 26..37  nonce AES-GCM            12 o aléatoires
    octets 38..    AES-256-GCM(clair)||tag  tag de 16 o collé à la fin
    AAD   = les 38 premiers octets
    clé   = PBKDF2-HMAC-SHA256(mot de passe UTF-8, sel, itérations, dklen=32)
    clair = un objet JSON encodé en UTF-8, séparateurs compacts

L'AAD couvre l'en-tête : trafiquer le nombre d'itérations fait ÉCHOUER le déchiffrement au lieu de dériver en
silence une autre clé. Un sel ET un nonce neufs à chaque écriture (un seul chemin d'écriture : `_reecrire`).

Le coffre OUVERT ne vit qu'en mémoire du processus ; rien de déchiffré ne retouche le disque. Ouvrir APPLIQUE les clés
à chaud (`cles_a_chaud.appliquer`, tâche #17 : client fal renouvelé, client HeyGen oublié) ; fermer les RETIRE du
processus — sinon « coffre fermé » serait un mensonge.
"""
import hashlib
import json
import os
import struct

from loguru import logger

from app.config import APP_VERSION, DATA_ROOT

MAGIE = b"DZKV1\n"
SEL_N = 16
NONCE_N = 12
ENTETE_N = len(MAGIE) + SEL_N + 4 + NONCE_N          # 38
ITERATIONS = 600_000
FICHIER = DATA_ROOT / "coffre.dzk"
SCEAU_PC = DATA_ROOT / "coffre.pc"
ENTROPIE_DPAPI = b"DeepotusVideoGen/coffre/v1"
MDP_MIN = 8

# Ce qui est un SECRET, et ce qui n'est qu'un réglage : un modèle par défaut ou l'identifiant d'un salon Telegram n'a
# rien à faire derrière un mot de passe ; un jeton en clair sur le disque, si.
SECRETES = {
    "FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY", "MESHY_API_KEY",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "FIGMA_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
    "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
    "IG_ACCESS_TOKEN",
    # plan scheduler T6 (tâche #28, 30/09/2026) : le secret du client TikTok et son refresh token (renouvelé par TikTok,
    # regardé par coffre.enregistrer_cle) ; l'identifiant public du client et le drapeau d'audit restent au .env
    "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN",
}

_ouvert: dict | None = None
_mdp_courant: str | None = None


class MotDePasseInvalide(Exception):
    """Mot de passe faux, fichier trafiqué ou format inconnu — la réponse est la même, et l'on ne dit pas laquelle."""


class CoffreVerrouille(Exception):
    """Le coffre existe mais il est fermé : écrire un secret en clair à sa place annulerait son existence."""


class CoffreIndisponible(Exception):
    """La roue `cryptography` manque à ce runtime (installation incomplète) : on le DIT plutôt qu'un 500 muet."""


def _aesgcm():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:
        raise CoffreIndisponible("chiffrement indisponible : la bibliothèque « cryptography » manque à cette "
                                 f"installation ({e}) — réinstaller l'application") from e
    return AESGCM


# ── le format ──────────────────────────────────────────────────────────────────────────────────────────────────────

def deriver(mot_de_passe: str, sel: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", (mot_de_passe or "").encode("utf-8"), sel, iterations, dklen=32)


def chiffrer(objet: dict, mot_de_passe: str, iterations: int = ITERATIONS) -> bytes:
    sel = os.urandom(SEL_N)
    nonce = os.urandom(NONCE_N)
    entete = MAGIE + sel + struct.pack(">I", iterations) + nonce
    clair = json.dumps(objet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return entete + _aesgcm()(deriver(mot_de_passe, sel, iterations)).encrypt(nonce, clair, entete)


def dechiffrer(blob: bytes, mot_de_passe: str) -> dict:
    if len(blob) < ENTETE_N + 16 or blob[:len(MAGIE)] != MAGIE:
        raise MotDePasseInvalide("fichier illisible : ce n'est pas une archive DZKV1")
    sel, nonce, entete = blob[6:22], blob[26:38], blob[:ENTETE_N]
    iterations = struct.unpack(">I", blob[22:26])[0]
    if not (1 <= iterations <= 10_000_000):
        raise MotDePasseInvalide("fichier illisible : nombre d'itérations aberrant")
    try:
        clair = _aesgcm()(deriver(mot_de_passe, sel, iterations)).decrypt(nonce, blob[ENTETE_N:], entete)
    except Exception:  # noqa: BLE001 — InvalidTag et compagnie
        raise MotDePasseInvalide("mot de passe incorrect, ou archive altérée")
    try:
        objet = json.loads(clair.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise MotDePasseInvalide("archive déchiffrée mais illisible")
    if not isinstance(objet, dict):
        raise MotDePasseInvalide("archive déchiffrée mais illisible")
    return objet


# ── le .env (lu et réécrit ligne à ligne : commentaires et réglages conservés) ─────────────────────────────────────

def _env_path():
    from app.config import ENV_FILE
    return ENV_FILE


def lire_env() -> dict:
    p = _env_path()
    out: dict = {}
    if p.exists():
        for ligne in p.read_text(encoding="utf-8").splitlines():
            s = ligne.strip()
            if s and not s.startswith("#") and "=" in s:
                k, _, v = s.partition("=")
                out[k.strip()] = v.strip()
    return out


def _ecrire_env(poser_: dict, retirer: set) -> None:
    """Pose/remplace `poser_`, retire les lignes des clés de `retirer` ; tout le reste est gardé tel quel."""
    p = _env_path()
    lignes = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    vus, sortie = set(), []
    for ligne in lignes:
        s = ligne.strip()
        k = s.partition("=")[0].strip() if (s and not s.startswith("#") and "=" in s) else None
        if k in retirer:
            continue
        if k in poser_:
            sortie.append(f"{k}={poser_[k]}")
            vus.add(k)
            continue
        sortie.append(ligne)
    sortie += [f"{k}={v}" for k, v in poser_.items() if k not in vus]
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text("\n".join(sortie) + "\n", encoding="utf-8")
    tmp.replace(p)


# ── le coffre local ────────────────────────────────────────────────────────────────────────────────────────────────

def est_pose() -> bool:
    return FICHIER.is_file()


def ouvert() -> bool:
    return _ouvert is not None


def verrouille() -> bool:
    return est_pose() and not ouvert()


def retenu() -> bool:
    return SCEAU_PC.is_file()


def cles_posees() -> set:
    return set(((_ouvert or {}).get("cles") or {}).keys())


def lire_cle(nom: str):
    return ((_ouvert or {}).get("cles") or {}).get(nom)


def valeur(nom: str) -> str:
    """La valeur d'une clé, d'où qu'elle vienne : le .env, sinon le coffre ouvert ('' sinon)."""
    return lire_env().get(nom, "") or (lire_cle(nom) or "")


def _reecrire(contenu: dict, mot_de_passe: str) -> None:
    tmp = FICHIER.with_name(FICHIER.name + ".tmp")
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(chiffrer(contenu, mot_de_passe))
    tmp.replace(FICHIER)


def _appliquer(cles: dict) -> None:
    from app.services import cles_a_chaud
    cles_a_chaud.appliquer(cles)


def poser(mot_de_passe: str, cles: dict) -> None:
    """Crée le coffre. Ne l'ouvre pas : poser et ouvrir sont deux gestes différents."""
    if len(mot_de_passe or "") < MDP_MIN:
        raise ValueError(f"mot de passe trop court ({MDP_MIN} caractères au moins)")
    _reecrire({"format": 1, "cles": dict(cles or {})}, mot_de_passe)
    logger.info(f"coffre posé : {len(cles or {})} clé(s)")


def ouvrir(mot_de_passe: str) -> dict:
    global _ouvert, _mdp_courant
    if not est_pose():
        raise MotDePasseInvalide("aucun coffre sur cette machine")
    contenu = dechiffrer(FICHIER.read_bytes(), mot_de_passe)
    contenu.setdefault("cles", {})
    _ouvert, _mdp_courant = contenu, mot_de_passe
    _appliquer(contenu["cles"])
    logger.info(f"coffre ouvert : {len(contenu['cles'])} clé(s) appliquée(s)")
    return dict(contenu["cles"])


def fermer() -> None:
    """Oublie le contenu ET retire ses clés du processus (sauf celles qu'un .env fournit encore)."""
    global _ouvert, _mdp_courant
    cles = dict((_ouvert or {}).get("cles") or {})
    _ouvert, _mdp_courant = None, None
    env = lire_env()
    a_retirer = {k: "" for k in cles if not env.get(k)}
    if a_retirer:
        _appliquer(a_retirer)


def ecrire_cle(nom: str, valeur_: str) -> None:
    """Écrit (ou efface, valeur vide) une clé dans le coffre OUVERT, rechiffre, applique."""
    if _ouvert is None or _mdp_courant is None:
        raise CoffreVerrouille("le coffre est fermé")
    if valeur_:
        _ouvert.setdefault("cles", {})[nom] = valeur_
    else:
        _ouvert.setdefault("cles", {}).pop(nom, None)
    _reecrire(_ouvert, _mdp_courant)
    _appliquer({nom: valeur_ or ""})


def enregistrer_cle(nom: str, valeur_: str) -> str:
    """Tâche #27 (29/09/2026) : un SERVICE reçoit une clé neuve (TikTok renouvelle son refresh token) et doit la garder
    là où vivent les clés : coffre ouvert → coffre ; pas de coffre → .env ; coffre posé mais FERMÉ → appliquée en
    mémoire seulement (écrire le secret en clair annulerait le coffre) et c'est journalisé. Rend l'endroit."""
    if ouvert():
        ecrire_cle(nom, valeur_)
        return "coffre"
    if est_pose():
        _appliquer({nom: valeur_})
        logger.warning(f"coffre fermé : {nom} renouvelée appliquée en mémoire, NON enregistrée")
        return "memoire"
    _ecrire_env({nom: valeur_}, set())
    _appliquer({nom: valeur_})
    return "env"


def changer_mot_de_passe(ancien: str, nouveau: str) -> None:
    global _mdp_courant
    if len(nouveau or "") < MDP_MIN:
        raise ValueError(f"mot de passe trop court ({MDP_MIN} caractères au moins)")
    contenu = dechiffrer(FICHIER.read_bytes(), ancien)
    _reecrire(contenu, nouveau)
    if _ouvert is not None:
        _mdp_courant = nouveau
    oublier()          # le sceau DPAPI portait l'ancien mot de passe : il ne vaut plus
    logger.info("coffre : mot de passe changé, sceau DPAPI effacé")


# ── « retenir sur ce PC » : DPAPI scelle le MOT DE PASSE, pour cette session Windows ─────────────────────────────────

def retenir() -> None:
    if _mdp_courant is None:
        raise CoffreVerrouille("le coffre est fermé")
    from app.services import dpapi
    tmp = SCEAU_PC.with_name(SCEAU_PC.name + ".tmp")
    tmp.write_bytes(dpapi.sceller(_mdp_courant.encode("utf-8"), ENTROPIE_DPAPI))
    tmp.replace(SCEAU_PC)
    logger.info("coffre : ouverture automatique armée pour cette session Windows")


def oublier() -> None:
    try:
        SCEAU_PC.unlink(missing_ok=True)
    except OSError:
        pass


def ouvrir_par_dpapi() -> bool:
    """Ouverture au lancement, sans rien demander. False (jamais d'exception) si le sceau manque, vient d'un autre
    compte, ou n'ouvre plus le coffre (mot de passe changé ailleurs : le sceau périmé est alors effacé)."""
    if not (retenu() and est_pose()):
        return False
    from app.services import dpapi
    brut = dpapi.desceller(SCEAU_PC.read_bytes(), ENTROPIE_DPAPI)
    if not brut:
        return False
    try:
        ouvrir(brut.decode("utf-8"))
        return True
    except (MotDePasseInvalide, UnicodeDecodeError):
        logger.info("coffre : sceau DPAPI périmé — effacé")
        oublier()
        return False


# ── le .env vidé de ses secrets ────────────────────────────────────────────────────────────────────────────────────

def absorber_env() -> list:
    """DÉPLACE les secrets du .env vers le coffre OUVERT et les efface du .env (une copie en clair viderait le coffre de
    son sens). Réglages et commentaires restent. Rend les noms absorbés."""
    if _ouvert is None or _mdp_courant is None:
        raise CoffreVerrouille("le coffre est fermé")
    pris = {k: v for k, v in lire_env().items() if k in SECRETES and v}
    if pris:
        _ouvert.setdefault("cles", {}).update(pris)
        _reecrire(_ouvert, _mdp_courant)          # d'abord le coffre : jamais une clé perdue entre les deux
        _ecrire_env({}, set(pris))
    logger.info(f"coffre : {len(pris)} secret(s) absorbé(s) depuis le .env")
    return sorted(pris)


# ── l'archive portable ─────────────────────────────────────────────────────────────────────────────────────────────

def archiver(mot_de_passe: str) -> bytes:
    """L'archive portable : les clés (coffre ET .env — un modèle par défaut sert autant qu'un jeton), les plafonds et
    la grille de prix. Son mot de passe est demandé À PART de celui du coffre."""
    import socket
    import time as _t
    from app.services import plafonds as _plaf, pricing as _pricing
    if len(mot_de_passe or "") < MDP_MIN:
        raise ValueError(f"mot de passe trop court ({MDP_MIN} caractères au moins)")
    if verrouille():
        raise CoffreVerrouille("le coffre est fermé : ouvrez-le pour que l'archive porte ses clés")
    cles = {k: v for k, v in lire_env().items() if v}
    cles.update((_ouvert or {}).get("cles") or {})
    objet = {"format": 1, "genre": "archive", "cree_le": _t.strftime("%Y-%m-%dT%H:%M:%S"),
             "app_version": APP_VERSION, "machine": socket.gethostname(), "cles": cles,
             "plafonds": _plaf.charger(), "pricing": _pricing.load()}
    return chiffrer(objet, mot_de_passe)


def restaurer(blob: bytes, mot_de_passe: str) -> dict:
    """Relit une archive et repose son contenu SUR CETTE MACHINE : les secrets au coffre s'il est ouvert, au .env s'il
    n'y a pas de coffre — et l'on DIT où. Coffre posé mais fermé : refus (un secret en clair à sa place serait une fuite)."""
    from app.services import plafonds as _plaf, pricing as _pricing
    a = dechiffrer(blob, mot_de_passe)
    if a.get("genre") != "archive":
        raise MotDePasseInvalide("ce fichier est un coffre, pas une archive")
    cles = {str(k): str(v) for k, v in (a.get("cles") or {}).items() if v}
    secrets = {k: v for k, v in cles.items() if k in SECRETES}
    if secrets and verrouille():
        raise CoffreVerrouille("le coffre est fermé : ouvrez-le avant d'importer une archive qui porte des clés")
    au_coffre = []
    if secrets and ouvert():
        _ouvert.setdefault("cles", {}).update(secrets)
        _reecrire(_ouvert, _mdp_courant)
        au_coffre = sorted(secrets)
    reste = {k: v for k, v in cles.items() if k not in au_coffre}
    if reste:
        _ecrire_env(reste, set())
    if isinstance(a.get("plafonds"), dict):
        _plaf.enregistrer(a["plafonds"])
    if isinstance(a.get("pricing"), dict):
        _pricing.save(a["pricing"])
    _appliquer(cles)
    logger.info(f"archive restaurée : {len(au_coffre)} au coffre, {len(reste)} au .env")
    return {"cles": len(cles), "au_coffre": au_coffre, "au_env": sorted(reste),
            "venue_de": a.get("machine", ""), "creee_le": a.get("cree_le", "")}
