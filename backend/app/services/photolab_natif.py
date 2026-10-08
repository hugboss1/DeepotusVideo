"""Repli « app native » du Photolab (t140, P5, décision D10) : piloter photocraft.exe par son canal de contrôle.

`photocraft.exe --control <port> --control-token-file <f> --automation-read-root <d> --automation-write-root <d>`
écoute en JSON lignes sur 127.0.0.1 (apps/photocraft/src/control_server.rs, tag v0.3.0). La première ligne de chaque
connexion s'authentifie : {"method":"auth","params":{"token":<64 hex>}} ; ensuite `app.open {path}` / `app.save {path}`
(chemins RELATIFS aux racines, ici le dossier du moteur), `ui.focus`, `app.quit`.

Le jeton est tiré à chaque lancement (secrets) et passé par FICHIER, dans le dossier de données : jamais sur la ligne
de commande, que tout processus de la session peut lire. Le port est tiré libre. Une seule app native à la fois ; elle
reste ouverte entre deux envois (c'est l'app de l'utilisateur), et se ferme avec `fermer()`.
"""
import json
import os
import secrets
import socket
import subprocess
import threading
import time
from pathlib import Path

from app.services import photolab_moteur as PM

RACINE_APP = PM.RACINE_APP
FABRIQUE = None                 # bancs : callable -> argv qui remplace [photocraft.exe] (faux serveur de contrôle)
DELAI_DEMARRAGE = 30.0          # le vrai binaire ouvre une fenêtre et initialise le GPU : quelques secondes
DELAI_APPEL = 60.0              # le serveur répond « timeout » lui-même à 60 s

_verrou = threading.RLock()
_proc = None
_port = None
_jeton = None
dernier = {}                    # le dernier envoi : {"fichier", "base", "origine"} (lu par les routes)


class NatifAbsent(RuntimeError):
    pass


class NatifInjoignable(RuntimeError):
    pass


class NatifErreur(RuntimeError):
    pass


class NatifFerme(RuntimeError):
    pass


def chemin_app() -> Path:
    env = os.environ.get("PHOTOCRAFT_APP")
    if env and Path(env).is_file():
        return Path(env)
    base = Path(RACINE_APP) / "vendor" / f"photocraft-{PM.VERSION}"
    if base.is_dir():
        for c in sorted(base.rglob("photocraft.exe")):
            return c
    raise NatifAbsent(f"App native absente : photocraft.exe {PM.VERSION} introuvable sous {base}.")


def _vivant() -> bool:
    return _proc is not None and _proc.poll() is None


def etat() -> dict:
    try:
        present = FABRIQUE is not None or chemin_app().is_file()
    except NatifAbsent:
        present = False
    return {"present": present, "actif": _vivant(), "fichier": dernier.get("fichier")}


def _port_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _echanger(methode, params, delai):
    """Une connexion : authentification, puis UNE requête. -> result ; lève NatifInjoignable / NatifErreur."""
    try:
        with socket.create_connection(("127.0.0.1", _port), timeout=delai) as so:
            f = so.makefile("rwb")
            f.write((json.dumps({"id": 1, "method": "auth", "params": {"token": _jeton}}) + "\n").encode("utf-8"))
            f.flush()
            a = json.loads(f.readline() or b"{}")
            if not a.get("ok"):
                raise NatifErreur(f"authentification refusée par l'app native : {a.get('error')}")
            f.write((json.dumps({"id": 2, "method": methode, "params": params or {}}) + "\n").encode("utf-8"))
            f.flush()
            ligne = f.readline()
    except (OSError, ValueError) as e:
        raise NatifInjoignable(f"app native injoignable : {e}")
    try:
        r = json.loads(ligne)
    except ValueError:
        raise NatifInjoignable("app native : réponse illisible")
    if not r.get("ok"):
        raise NatifErreur(str(r.get("error") or "erreur inconnue"))
    return r.get("result")


def _lancer():
    global _proc, _port, _jeton
    argv0 = FABRIQUE() if FABRIQUE is not None else [str(chemin_app())]
    d = PM.dossier_travail()
    natif = d / "natif"
    natif.mkdir(parents=True, exist_ok=True)
    fj = natif / ".jeton"
    jeton = secrets.token_hex(32)
    try:
        fj.unlink()
    except FileNotFoundError:
        pass
    fj.write_text(jeton, encoding="ascii")
    port = _port_libre()
    argv = argv0 + ["--control", str(port), "--control-token-file", str(fj),
                    "--automation-read-root", str(d), "--automation-write-root", str(d)]
    drapeaux = subprocess.CREATE_NO_WINDOW if os.name == "nt" and FABRIQUE is not None else 0
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=drapeaux)
    _proc, _port, _jeton = proc, port, jeton
    fin = time.monotonic() + DELAI_DEMARRAGE
    derniere = None
    while time.monotonic() < fin:
        if proc.poll() is not None:
            raise NatifInjoignable(f"l'app native s'est arrêtée au démarrage (code {proc.returncode})")
        try:
            _echanger("ui.focus", {}, 2.0)
            return
        except NatifInjoignable as e:
            derniere = e
            time.sleep(0.2)
    fermer()
    raise NatifInjoignable(f"l'app native ne répond pas après {DELAI_DEMARRAGE:.0f} s ({derniere})")


def appeler(methode, params=None):
    """Une requête à l'app native ouverte (NatifFerme si aucune)."""
    with _verrou:
        if not _vivant():
            raise NatifFerme("aucune app native ouverte")
        return _echanger(methode, params, DELAI_APPEL)


def ouvrir(chemin_rel: str):
    """Lance l'app native si besoin, y ouvre `chemin_rel` (relatif au dossier du moteur), la met au premier plan."""
    with _verrou:
        if not _vivant():
            _lancer()
        r = _echanger("app.open", {"path": chemin_rel}, DELAI_APPEL)
        try:
            _echanger("ui.focus", {}, 5.0)
        except (NatifInjoignable, NatifErreur):
            pass                                   # le premier plan est un confort, pas une condition
        return r


def enregistrer(chemin_rel: str):
    """Fait enregistrer le document actif de l'app native sous `chemin_rel`."""
    return appeler("app.save", {"path": chemin_rel})


def fermer():
    global _proc, _port, _jeton
    with _verrou:
        p = _proc
        if p is not None and p.poll() is None:
            try:
                _echanger("app.quit", {}, 3.0)
            except (NatifInjoignable, NatifErreur):
                pass
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()
        _proc, _port, _jeton = None, None, None
