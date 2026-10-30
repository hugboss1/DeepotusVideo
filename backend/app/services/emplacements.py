# -*- coding: utf-8 -*-
"""t378 (30/10/2026, lot « Réglages : chemins & apparence », plan
docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md, décisions D2 et D3 du 29/10) —
les EMPLACEMENTS de Réglages › Chemins : des dossiers en plus des deux dossiers de l'application, pour la
sauvegarde, un NAS ou un serveur distant.

Un emplacement = un nom, un TYPE (D2) et des RÔLES cochables (D3) :
  - `dossier` : un chemin absolu local, un lecteur réseau (`Z:\\…`) ou un chemin UNC (`\\\\NAS\\partage\\…`) ; Windows
    s'identifie avec la session de l'utilisateur, rien n'est gardé ici ;
  - `sftp` : hôte, port, utilisateur, dossier distant ; mot de passe facultatif (sinon la clé SSH de l'utilisateur,
    son agent ou le fichier de clé indiqué). Le transfert passe par le client OpenSSH de Windows (`sftp.exe`, livré
    avec Windows 10/11) : aucune roue neuve dans le Python embarqué. S3 compatible viendra plus tard (D2).
Rôles (D3), câblés par t379 : `sauvegarde` (copie planifiée des données), `miroir` (chaque rendu fini copié),
`bibliotheque` (source de la Bibliothèque, LECTURE SEULE : le test n'y écrit rien).

La description vit dans `DATA_ROOT/emplacements.json`, SANS secret. Le mot de passe SFTP va au coffre (ou au .env tant
qu'aucun coffre n'est posé : la règle de toutes les clés, `comptes._secret_ecrire`) sous `DZC_<ID>_SECRET`, n'est
jamais relu vers l'écran (la vue dit `secret_pose`) et passe à `sftp.exe` par SSH_ASKPASS (une variable
d'environnement du seul processus enfant), jamais par la ligne de commande ni un fichier.

« Tester » écrit un fichier témoin, le relit, le compare, l'efface, et lit l'espace libre ; `verifier` (le
Diagnostic) ne fait que joindre et lister. Aucun chemin renseigné = rien ne change (t379 s'y appuie).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path, PureWindowsPath

from loguru import logger

from app.config import DATA_ROOT, settings

TYPES = ("dossier", "sftp")
ROLES = ("sauvegarde", "miroir", "bibliotheque")
MAX_EMPLACEMENTS = 20
MAX_NOM = 60
DELAI_S = 20                                    # un NAS éteint ne bloque pas l'écran plus longtemps
_ID = re.compile(r"^[a-z][a-z0-9]{0,23}$")
_HOTE = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$|^\[[0-9A-Fa-f:.]+\]$")
_UTILISATEUR = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,63}$")
# Un dossier distant : chemin POSIX absolu, sans guillemet ni barre oblique inverse, retour à la ligne ni caractère de contrôle (il est écrit
# dans le lot de commandes de sftp.exe : un retour à la ligne y ajouterait une commande).
_DISTANT = re.compile(r"^/[^\"\\\x00-\x1f\x7f]{0,400}$")


class EmplacementInconnu(Exception):
    """L'identifiant ne désigne aucun emplacement enregistré."""


# ── le fichier ──────────────────────────────────────────────────────────────────────────────────────────────────────

def _fichier() -> Path:
    return DATA_ROOT / "emplacements.json"


def _lire() -> dict:
    f = _fichier()
    if f.is_file():
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and isinstance(doc.get("emplacements"), dict) \
                    and all(_ID.match(k) for k in doc["emplacements"]):
                return doc
        except (OSError, ValueError):
            pass
        cote = f.with_name(f"emplacements.json.illisible-{datetime.now():%Y%m%d-%H%M%S}")
        f.replace(cote)
        logger.warning(f"emplacements.json illisible : mis de côté ({cote.name})")
    return {"emplacements": {}}


def _ecrire(doc: dict) -> None:
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


# ── le secret (SFTP seulement, facultatif) ──────────────────────────────────────────────────────────────────────────

def nom_secret(eid: str) -> str:
    """Le nom du secret (coffre / .env) d'un emplacement : DZC_<ID>_SECRET."""
    if not _ID.match(eid or ""):
        raise ValueError(f"identifiant d'emplacement invalide : {eid}")
    return f"DZC_{eid.upper()}_SECRET"


def _secret(eid: str) -> str:
    from app.services import coffre
    n = nom_secret(eid)
    return (os.environ.get(n) or coffre.valeur(n) or "").strip()


def _poser_secret(eid: str, valeur_: str) -> str:
    from app.services import comptes
    return comptes._secret_ecrire(nom_secret(eid), (valeur_ or "").strip())


def _coffre_libre(avec_secret: bool) -> None:
    from app.services import coffre
    if avec_secret and coffre.verrouille():
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le avant d'enregistrer un mot de passe")


# ── la validation ───────────────────────────────────────────────────────────────────────────────────────────────────

def _texte(v, n=MAX_NOM) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _dans(enfant: Path, parent: Path) -> bool:
    try:
        enfant.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def verifier_dossier(v) -> str:
    """Un chemin ABSOLU (lettre de lecteur ou UNC), hors des dossiers de l'application et de ses données : une
    sauvegarde rangée dans ce qu'elle sauvegarde se recopierait elle-même."""
    s = str(v or "").strip().strip('"')
    if not s:
        raise ValueError("dossier : chemin requis")
    if any(ord(c) < 32 for c in s) or len(s) > 400:
        raise ValueError("dossier : chemin invalide")
    p = PureWindowsPath(s)
    if not (p.is_absolute() and (p.drive.startswith("\\\\") or re.match(r"^[A-Za-z]:$", p.drive))):
        raise ValueError("dossier : chemin absolu requis (C:\\…, Z:\\… ou \\\\NAS\\partage\\…)")
    if p.drive.startswith("\\\\") and not re.match(r"^\\\\[^\\/]+\\[^\\/]+$", p.drive):
        raise ValueError("dossier : chemin UNC incomplet (\\\\serveur\\partage\\…)")
    for interdit in (DATA_ROOT, settings.images_path, settings.outputs_path):
        if _dans(Path(s), Path(interdit)) or _dans(Path(interdit), Path(s)):
            raise ValueError("dossier : pas dans les dossiers de l'application ni au-dessus")
    return str(p)


def _sftp_champs(c: dict, avant: dict | None = None) -> dict:
    a = avant or {}
    hote = str(c.get("hote", a.get("hote")) or "").strip()
    if not _HOTE.match(hote):
        raise ValueError("sftp : hôte invalide")
    try:
        port = c.get("port", a.get("port"))
        port = 22 if port in (None, "") else int(port)
    except (TypeError, ValueError):
        raise ValueError("sftp : port invalide")
    if not 1 <= port <= 65535:
        raise ValueError("sftp : port invalide")
    util = str(c.get("utilisateur", a.get("utilisateur")) or "").strip()
    if not _UTILISATEUR.match(util):
        raise ValueError("sftp : utilisateur invalide")
    distant = str(c.get("dossier_distant", a.get("dossier_distant")) or "/").strip()
    if not _DISTANT.match(distant):
        raise ValueError("sftp : dossier distant invalide (chemin absolu /…)")
    cle_ssh = str(c.get("cle_ssh", a.get("cle_ssh")) or "").strip()
    if cle_ssh and (any(ord(ch) < 32 for ch in cle_ssh) or not PureWindowsPath(cle_ssh).is_absolute()):
        raise ValueError("sftp : fichier de clé SSH invalide (chemin absolu)")
    return {"hote": hote, "port": port, "utilisateur": util, "dossier_distant": distant.rstrip("/") or "/",
            "cle_ssh": cle_ssh}


def _roles(v) -> list[str]:
    if v is None:
        return []
    if not isinstance(v, (list, tuple)) or any(r not in ROLES for r in v):
        raise ValueError("rôles : sauvegarde, miroir ou bibliotheque")
    return [r for r in ROLES if r in v]


def _decrire(c: dict, avant: dict | None = None) -> dict:
    """Les champs d'un emplacement, vérifiés ; rien n'est écrit ici."""
    a = avant or {}
    type_ = str(c.get("type", a.get("type")) or "dossier").strip().lower()
    if type_ not in TYPES:
        raise ValueError("type : dossier ou sftp")
    e = {"type": type_, "roles": _roles(c["roles"]) if "roles" in c else list(a.get("roles") or [])}
    if type_ == "dossier":
        e["chemin"] = verifier_dossier(c.get("chemin", a.get("chemin")))
    else:
        e.update(_sftp_champs(c, a))
    return e


def _adresse(e: dict) -> str:
    if e.get("type") == "sftp":
        port = "" if int(e.get("port") or 22) == 22 else f":{e['port']}"
        return f"sftp://{e.get('utilisateur')}@{e.get('hote')}{port}{e.get('dossier_distant')}"
    return str(e.get("chemin") or "")


def _id_neuf(nom: str, pris) -> str:
    sans_accent = unicodedata.normalize("NFKD", nom.lower()).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]", "", sans_accent) or "e"
    base = ("e" + base if not base[0].isalpha() else base)[:20]
    sid, i = base, 2
    while sid in pris:
        sid, i = f"{base[:20]}{i}", i + 1
    return sid


def _vue(eid: str, e: dict) -> dict:
    v = {"id": eid, "nom": e.get("nom") or eid, "type": e.get("type"), "roles": list(e.get("roles") or []),
         "adresse": _adresse(e), "cree": e.get("cree", ""), "dernier_test": e.get("dernier_test")}
    if e.get("type") == "sftp":
        v.update({k: e.get(k) for k in ("hote", "port", "utilisateur", "dossier_distant", "cle_ssh")})
        v["secret_pose"] = bool(_secret(eid))
    else:
        v["chemin"] = e.get("chemin")
    return v


# ── l'API du service ────────────────────────────────────────────────────────────────────────────────────────────────

def lister() -> list[dict]:
    return [_vue(k, e) for k, e in _lire()["emplacements"].items()]


def obtenir(eid: str) -> dict:
    e = _lire()["emplacements"].get(eid)
    if e is None:
        raise EmplacementInconnu(eid)
    return _vue(eid, e)


def avec_role(role: str) -> list[dict]:
    """Pour t379 : les emplacements qui portent ce rôle (vide = rien à faire)."""
    return [v for v in lister() if role in v["roles"]]


def creer(champs: dict) -> dict:
    """{nom, type, roles, chemin | hote, port, utilisateur, dossier_distant, cle_ssh, secret?} -> la vue."""
    c = champs if isinstance(champs, dict) else {}
    e = _decrire(c)
    nom = _texte(c.get("nom")) or _adresse(e)[:MAX_NOM]
    secret = str(c.get("secret") or "").strip()
    if secret and e["type"] != "sftp":
        raise ValueError("mot de passe : seulement pour un emplacement SFTP")
    doc = _lire()
    if len(doc["emplacements"]) >= MAX_EMPLACEMENTS:
        raise ValueError(f"{MAX_EMPLACEMENTS} emplacements au plus")
    _coffre_libre(bool(secret))
    eid = _id_neuf(nom, doc["emplacements"])
    doc["emplacements"][eid] = {"nom": nom, **e, "cree": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    if secret:
        _poser_secret(eid, secret)
    _ecrire(doc)
    return _vue(eid, doc["emplacements"][eid])


def modifier(eid: str, champs: dict) -> dict:
    """Le type ne change pas ; `secret` vide = garder, `effacer_secret` pour le retirer."""
    c = dict(champs) if isinstance(champs, dict) else {}
    doc = _lire()
    a = doc["emplacements"].get(eid)
    if a is None:
        raise EmplacementInconnu(eid)
    c["type"] = a.get("type")
    neuf = {**a, **_decrire(c, a)}
    if "nom" in c:
        neuf["nom"] = _texte(c.get("nom")) or a.get("nom")
    if any(neuf.get(k) != a.get(k) for k in ("chemin", "hote", "port", "utilisateur", "dossier_distant")):
        neuf.pop("dernier_test", None)                  # l'adresse a changé : l'ancien test ne dit plus rien
    secret = str(c.get("secret") or "").strip()
    effacer = c.get("effacer_secret") is True
    if secret and neuf["type"] != "sftp":
        raise ValueError("mot de passe : seulement pour un emplacement SFTP")
    _coffre_libre(bool(secret) or effacer)
    if secret:
        _poser_secret(eid, secret)
    elif effacer:
        _poser_secret(eid, "")
    doc["emplacements"][eid] = neuf
    _ecrire(doc)
    return _vue(eid, neuf)


def supprimer(eid: str) -> None:
    """Retire l'emplacement ET efface son secret (coffre posé mais fermé : refus avant tout). Les fichiers déjà
    copiés là-bas restent : on ne touche jamais au contenu d'un emplacement."""
    from app.services import coffre
    doc = _lire()
    if eid not in doc["emplacements"]:
        raise EmplacementInconnu(eid)
    if coffre.verrouille() and _secret(eid):
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le pour effacer le mot de passe de cet emplacement")
    _poser_secret(eid, "")
    doc["emplacements"].pop(eid)
    _ecrire(doc)


# ── le test (fichier témoin) et la vérification (Diagnostic) ───────────────────────────────────────────────────────

# Chaque résultat porte un CODE stable (l'écran le traduit : clés chemins.etat.<code>) et un message français
# (journal, assistant) ; `detail` garde la cause brute quand aucun code ne la dit.
ETATS = {
    "ecrit_lu": "écriture et lecture réussies", "joignable": "joignable",
    "introuvable": "dossier introuvable ou injoignable", "acces_refuse": "accès refusé",
    "injoignable": "injoignable", "temoin_different": "fichier témoin relu différent",
    "cle_hote": "clé d'hôte changée", "hote_introuvable": "hôte introuvable", "connexion_refusee": "connexion refusée",
    "delai": "délai dépassé", "distant_introuvable": "dossier distant introuvable",
    "client_absent": "client SFTP introuvable : installez le client OpenSSH de Windows", "echec": "échec",
}


def _resultat(ok: bool, code: str, libre=None, detail: str = "") -> dict:
    return {"ok": ok, "code": code, "message": ETATS[code] + (f" : {detail}" if detail else ""),
            "detail": detail, "libre_octets": libre, "quand": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}


def _lecture_seule(e: dict) -> bool:
    roles = e.get("roles") or []
    return bool(roles) and set(roles) == {"bibliotheque"}


def _tester_dossier(e: dict, leger: bool) -> dict:
    p = Path(e["chemin"])
    try:
        if not p.is_dir():
            return _resultat(False, "introuvable")
        next(iter(os.scandir(p)), None)                 # se liste-t-il ?
        libre = shutil.disk_usage(p).free
        if leger or _lecture_seule(e):
            return _resultat(True, "joignable", libre)
        nom = f".deepotus-temoin-{secrets.token_hex(6)}.txt"
        contenu = f"DeepotusVideo — fichier témoin ({datetime.now():%Y-%m-%d %H:%M:%S})\n".encode("utf-8")
        f = p / nom
        try:
            f.write_bytes(contenu)
            relu = f.read_bytes()
        finally:
            f.unlink(missing_ok=True)
        if relu != contenu:
            return _resultat(False, "temoin_different", libre)
        return _resultat(True, "ecrit_lu", libre)
    except PermissionError:
        return _resultat(False, "acces_refuse")
    except OSError as ex:
        return _resultat(False, "injoignable", detail=ex.strerror or ex.__class__.__name__)


def sftp_exe() -> str | None:
    """Le client OpenSSH : `DZ_SFTP_EXE` (bancs, installation atypique), sinon celui de Windows, sinon le PATH."""
    v = os.environ.get("DZ_SFTP_EXE", "").strip()
    if v:
        return v if Path(v).is_file() else None
    sys_ = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "OpenSSH" / "sftp.exe"
    if sys_.is_file():
        return str(sys_)
    return shutil.which("sftp")


def _known_hosts() -> Path:
    d = DATA_ROOT / "ssh"
    d.mkdir(parents=True, exist_ok=True)
    return d / "known_hosts"


def _askpass(dossier: Path) -> Path:
    """Le petit programme que ssh appelle pour lire le mot de passe : il le RECOPIE depuis une variable
    d'environnement du seul processus sftp ; le mot de passe n'est jamais écrit dans un fichier."""
    f = dossier / "askpass.cmd"
    f.write_text("@echo off\r\nsetlocal EnableDelayedExpansion\r\necho(!DZC_ASKPASS!\r\n", encoding="ascii")
    return f


def lancer_sftp(eid: str | None, e: dict, commandes: list[str], *, secret: str | None = None,
                delai: float = DELAI_S) -> tuple[bool, str]:
    """Joue un lot de commandes sftp (une par ligne, chemins entre guillemets) ; rend (réussi, sortie)."""
    exe = sftp_exe()
    if not exe:
        raise FileNotFoundError(ETATS["client_absent"])
    mdp = secret if secret is not None else (_secret(eid) if eid else "")
    with tempfile.TemporaryDirectory(prefix="dzsftp_") as td:
        lot = Path(td) / "lot.txt"
        lot.write_text("\n".join(commandes) + "\n", encoding="utf-8")
        args = [exe]
        from app.services import coffre
        env = {k: v for k, v in os.environ.items()          # sftp.exe ne reçoit aucune clé de l'application
               if not k.startswith(("DZC_", "DZL_", "DZF_")) and k not in coffre.SECRETES}
        if mdp:
            # avant -b : sftp ajoute « BatchMode yes » à -b, et ssh garde la PREMIÈRE valeur reçue
            args += ["-o", "BatchMode=no", "-o", "PreferredAuthentications=publickey,password,keyboard-interactive"]
            env.update({"SSH_ASKPASS": str(_askpass(Path(td))), "SSH_ASKPASS_REQUIRE": "force",
                        "DZC_ASKPASS": mdp, "DISPLAY": "dz:0"})
        args += ["-b", str(lot), "-P", str(int(e.get("port") or 22)),
                 "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={_known_hosts()}",
                 "-o", f"ConnectTimeout={int(max(3, min(delai, 30)))}"]
        if e.get("cle_ssh"):
            args += ["-i", e["cle_ssh"]]
        args += ["--", f"{e['utilisateur']}@{e['hote']}"]
        try:
            r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env=env, timeout=delai, stdin=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            return False, "timed out"
        sortie = (r.stdout or "") + (r.stderr or "")
        if mdp:
            sortie = sortie.replace(mdp, "•••")
        return r.returncode == 0, sortie


def _echec_sftp(sortie: str) -> dict:
    s = sortie.lower()
    for motif, code in (("permission denied", "acces_refuse"), ("host key verification failed", "cle_hote"),
                        ("could not resolve", "hote_introuvable"), ("connection refused", "connexion_refusee"),
                        ("timed out", "delai"), ("can't change directory", "distant_introuvable"),
                        ("no such file", "distant_introuvable")):
        if motif in s:
            return _resultat(False, code)
    lignes = [l.strip() for l in sortie.splitlines() if l.strip() and not l.startswith("sftp>")]
    return _resultat(False, "echec", detail=(lignes[-1] if lignes else "")[:160])


def _libre_sftp(sortie: str):
    """`df .` : Size Used Avail (Kio) ; None si le serveur ne le sait pas."""
    m = re.search(r"^\s*\d+\s+\d+\s+(\d+)\s+\d+\s+\d+%", sortie, re.M)
    return int(m.group(1)) * 1024 if m else None


def _tester_sftp(eid: str | None, e: dict, leger: bool, secret: str | None) -> dict:
    d = e["dossier_distant"]
    if leger or _lecture_seule(e):
        reussi, sortie = lancer_sftp(eid, e, [f'cd "{d}"', "ls", "-df ."], secret=secret)
        return _resultat(True, "joignable", _libre_sftp(sortie)) if reussi else _echec_sftp(sortie)
    nom = f".deepotus-temoin-{secrets.token_hex(6)}.txt"
    contenu = f"DeepotusVideo — fichier témoin ({datetime.now():%Y-%m-%d %H:%M:%S})\n".encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="dztemoin_") as td:
        envoi, retour = Path(td) / "envoi.txt", Path(td) / "retour.txt"
        envoi.write_bytes(contenu)
        reussi, sortie = lancer_sftp(eid, e, [f'cd "{d}"', f'put "{envoi.as_posix()}" "{nom}"',
                                              f'get "{nom}" "{retour.as_posix()}"',
                                              f'rm "{nom}"', "-df ."], secret=secret)
        if not reussi:
            return _echec_sftp(sortie)
        if not retour.is_file() or retour.read_bytes() != contenu:
            return _resultat(False, "temoin_different")
        return _resultat(True, "ecrit_lu", _libre_sftp(sortie))


def _essayer(eid: str | None, e: dict, leger: bool, secret: str | None = None) -> dict:
    try:
        if e["type"] == "sftp":
            return _tester_sftp(eid, e, leger, secret)
        return _tester_dossier(e, leger)
    except FileNotFoundError:
        return _resultat(False, "client_absent")


def tester(eid: str) -> dict:
    """« Tester » un emplacement enregistré : le résultat est gardé (`dernier_test`)."""
    doc = _lire()
    e = doc["emplacements"].get(eid)
    if e is None:
        raise EmplacementInconnu(eid)
    r = _essayer(eid, e, leger=False)
    doc = _lire()                                       # relu : un autre geste a pu écrire pendant le test
    if eid in doc["emplacements"]:
        doc["emplacements"][eid]["dernier_test"] = r
        _ecrire(doc)
    return r


def tester_brouillon(champs: dict) -> dict:
    """« Tester » avant d'enregistrer : rien n'est gardé, le mot de passe éventuel non plus."""
    c = champs if isinstance(champs, dict) else {}
    e = _decrire(c)
    secret = str(c.get("secret") or "").strip()
    if secret and e["type"] != "sftp":
        raise ValueError("mot de passe : seulement pour un emplacement SFTP")
    return _essayer(None, e, leger=False, secret=secret)


def verifier() -> list[dict]:
    """Le Diagnostic : chaque emplacement est-il joignable ? (aucune écriture là-bas)."""
    return [{"id": k, "nom": e.get("nom") or k, "type": e.get("type"), "adresse": _adresse(e),
             **_essayer(k, e, leger=True)} for k, e in _lire()["emplacements"].items()]
