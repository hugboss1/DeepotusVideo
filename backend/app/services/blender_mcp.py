# -*- coding: utf-8 -*-
"""t331 (A1 du lot Scenario, 29/10/2026) — le pont « Scène Blender » : le backend est un CLIENT MCP de mcp-for-blender
(ex-blender-mcp, MIT), lancé en stdio, qui parle à l'add-on du Blender OUVERT de l'utilisateur (127.0.0.1:9876).
Spec : docs/superpowers/specs/2026-10-27-scenario-explorations-design.md, ligne A1 et « Risques ».

SANS DÉPENDANCE : le python embarqué de l'app n'a pas le paquet `mcp`. Le protocole est donc écrit ici, comme le serveur
MCP de l'app (t345, app/mcp_stdio.py) l'écrit côté serveur : JSON-RPC 2.0, un message par ligne UTF-8 sur stdin /
stdout (spec MCP 2025-11-25, « Transports › stdio » et « Lifecycle ») — initialize, notifications/initialized,
tools/list, tools/call. Une requête venue du serveur (élicitation, échantillonnage…) reçoit une erreur -32601 : le client
ne déclare aucune capacité. Une session = un processus, le temps d'une opération ; un verrou les met en file (l'add-on
n'a qu'un socket).

LES DROITS (la liste des outils EST la liste des droits) :
  * LISTE_BLANCHE = get_scene_info, look, search_assets, import_asset, avec leurs arguments bornés (`ARGUMENTS`) ;
    `look` ne reçoit jamais `image` (il lirait un fichier du disque) ;
  * generate_3d : seulement par `generer_3d`, appelée par la route POST /api/blender/generer APRÈS le 409
    `confirme_cout` et la garde des plafonds (« moteurs3d ») ;
  * execute_blender_code : seulement par `executer_gabarit`, avec un script de blender_gabarits (gabarit fixe, un seul
    trou = un JSON vérifié). Aucun code ne vient du client, de l'écran ni d'un modèle ;
  * tout autre outil (disable_telemetry, record_trajectory_feedback, get_addon_status…) est refusé.
Le processus reçoit un environnement MINIMAL (aucune clé de l'app : FAL_KEY, ANTHROPIC_API_KEY… ne sortent pas) plus
DISABLE_TELEMETRY=true, BLENDER_MCP_SAFE_MODE=1, BLENDERMCP_NO_UPDATE_CHECK=1, BLENDER_HOST=127.0.0.1, BLENDER_PORT.

L'exécutable : BLENDER_MCP_EXE (.env), sinon le réglage `exe` (DATA_ROOT/blender/reglages.json, posé par l'écran),
sinon « ~\\.local\\venvs\\mcp-for-blender\\Scripts\\mcp-for-blender.exe ». Absent → 503 `blender.exe_absent` ; Blender
fermé (l'add-on ne répond pas) → 503 `blender.ferme`.

PROVENANCE : chaque recherche garde la licence et l'auteur de ses résultats (Sketchfab, Poly Pizza ; Poly Haven = CC0) ;
chaque import est noté (DATA_ROOT/blender/provenance.json) avec sa licence, son auteur, son attribution et les objets
créés. Une capture gardée dans la Bibliothèque porte dans sa recette les licences des imports encore dans la scène.
"""
from __future__ import annotations

import base64
import json
import os
import queue
import re
import subprocess
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path

from app import config

VERSION_PROTOCOLE = "2025-06-18"
CLIENT = {"name": "deepotus-blender", "title": "DeepotusVideo", "version": "1.0.0"}
PORT_DEFAUT = 9876
EXE_DEFAUT = Path.home() / ".local" / "venvs" / "mcp-for-blender" / "Scripts" / "mcp-for-blender.exe"
DELAI_DEMARRAGE_S = 30.0
DELAIS_S = {"get_scene_info": 30.0, "look": 90.0, "search_assets": 60.0, "import_asset": 240.0,
            "execute_blender_code": 90.0, "generate_3d": 70.0}
LISTE_BLANCHE = ("get_scene_info", "look", "search_assets", "import_asset")
SOURCES = ("polyhaven", "sketchfab", "polypizza")
MODES_LOOK = ("viewport", "camera", "angles", "frames")
OMBRAGES = ("solid", "material", "rendered", "wireframe", "xray")
VUES = ("front", "back", "left", "right", "top", "three_quarter")
CHAMPS_SCENE = ("location", "size", "ground", "rotation", "scale", "parent", "children", "hidden", "details",
                "materials", "modifiers", "animation", "topology", "weights", "settings")
FOURNISSEURS_3D = ("auto", "tripo", "hunyuan3d", "hyper3d", "meshy")
MAX_PROVENANCE = 500
MAX_RECHERCHES = 400
MAX_TEXTE = 20_000
_FERME = re.compile(r"could not connect to blender|connection refused|make sure the blender addon is running", re.I)
_ENV_GARDEE = ("SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "HOMEDRIVE",
               "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "COMSPEC", "NUMBER_OF_PROCESSORS",
               "PROCESSOR_ARCHITECTURE", "OS")
_VERROU = threading.Lock()


class RefusBlender(Exception):
    """Un refus du pont : `cle` est une clé de app/i18n/messages.json (blender.*), rendue dans la langue de la requête."""

    def __init__(self, cle: str, statut: int = 400, **valeurs):
        super().__init__(cle)
        self.cle, self.statut, self.valeurs = cle, statut, valeurs


# ── réglages, exécutable, environnement ──────────────────────────────────────────────────────────────────────────

def dossier() -> Path:
    d = config.DATA_ROOT / "blender"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lire_json(f: Path, defaut):
    try:
        v = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut
    return v if isinstance(v, type(defaut)) else defaut


def _ecrire_json(f: Path, v) -> None:
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def reglages() -> dict:
    return _lire_json(dossier() / "reglages.json", {})


def poser_exe(chemin: str | None) -> dict:
    """Le chemin de mcp-for-blender choisi dans l'écran ; vide = le défaut. Un fichier .exe qui existe, sinon refus."""
    r = reglages()
    c = str(chemin or "").strip().strip('"')
    if not c:
        r.pop("exe", None)
    else:
        p = Path(c)
        if not p.is_absolute() or p.suffix.lower() != ".exe" or not p.is_file():
            raise RefusBlender("blender.exe_invalide", 400)
        r["exe"] = str(p)
    _ecrire_json(dossier() / "reglages.json", r)
    return etat_exe()


def exe() -> tuple[Path, str]:
    """(chemin, source) : env BLENDER_MCP_EXE, puis le réglage, puis le défaut."""
    env = os.environ.get("BLENDER_MCP_EXE", "").strip().strip('"')
    if env:
        return Path(env), "env"
    r = reglages().get("exe")
    if isinstance(r, str) and r:
        return Path(r), "reglage"
    return EXE_DEFAUT, "defaut"


def port() -> int:
    try:
        p = int(os.environ.get("BLENDER_MCP_PORT", "") or PORT_DEFAUT)
    except ValueError:
        return PORT_DEFAUT
    return p if 1024 <= p <= 65535 else PORT_DEFAUT


def etat_exe() -> dict:
    p, source = exe()
    return {"trouve": p.is_file(), "chemin": str(p), "source": source, "defaut": str(EXE_DEFAUT), "port": port()}


def environnement() -> dict:
    """Un environnement MINIMAL : le système, rien de l'app (aucune clé), plus les quatre variables de sûreté."""
    env = {k: os.environ[k] for k in _ENV_GARDEE if k in os.environ}
    env.update({"DISABLE_TELEMETRY": "true", "BLENDER_MCP_SAFE_MODE": "1", "BLENDERMCP_NO_UPDATE_CHECK": "1",
                "BLENDER_HOST": "127.0.0.1", "BLENDER_PORT": str(port()), "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1"})
    return env


# ── le client JSON-RPC sur stdio ─────────────────────────────────────────────────────────────────────────────────

def _popen(args: list[str], env: dict):           # couture : remplacée au banc (faux serveur)
    drapeaux = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                            cwd=str(dossier()), creationflags=drapeaux)


class Session:
    """Une session MCP sur un processus stdio. `with Session() as s: s.appeler(...)`."""

    def __init__(self, commande: list[str] | None = None):
        if commande is None:
            p, _ = exe()
            if not p.is_file():
                raise RefusBlender("blender.exe_absent", 503, chemin=str(p))
            commande = [str(p)]
        self.commande = commande
        self.proc = None
        self.lignes: queue.Queue = queue.Queue()
        self.erreurs: deque = deque(maxlen=40)
        self.ident = 0
        self.outils: list[dict] = []
        self.serveur: dict = {}

    # -- cycle de vie
    def __enter__(self):
        _VERROU.acquire()
        try:
            self.ouvrir()
        except BaseException:
            self.fermer()
            _VERROU.release()
            raise
        return self

    def __exit__(self, *exc):
        try:
            self.fermer()
        finally:
            _VERROU.release()
        return False

    def ouvrir(self) -> None:
        try:
            self.proc = _popen(self.commande, environnement())
        except OSError as e:
            raise RefusBlender("blender.lancement", 503, msg=type(e).__name__) from None
        threading.Thread(target=self._lire, args=(self.proc.stdout, self.lignes), daemon=True).start()
        threading.Thread(target=self._lire_erreurs, daemon=True).start()
        r = self.requete("initialize", {"protocolVersion": VERSION_PROTOCOLE, "capabilities": {},
                                        "clientInfo": CLIENT}, DELAI_DEMARRAGE_S)
        self.serveur = r.get("serverInfo") or {} if isinstance(r, dict) else {}
        self.notifier("notifications/initialized")
        t = self.requete("tools/list", {}, DELAI_DEMARRAGE_S)
        self.outils = [o for o in (t or {}).get("tools") or [] if isinstance(o, dict)]

    def fermer(self) -> None:
        p = self.proc
        self.proc = None
        if p is None:
            return
        try:
            if p.stdin:
                p.stdin.close()
        except OSError:
            pass
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass

    @staticmethod
    def _lire(flux, file_):
        try:
            for brut in iter(flux.readline, b""):
                file_.put(brut)
        except (OSError, ValueError):
            pass
        file_.put(None)

    def _lire_erreurs(self):
        try:
            for brut in iter(self.proc.stderr.readline, b""):
                self.erreurs.append(brut.decode("utf-8", "replace").rstrip()[:300])
        except (OSError, ValueError, AttributeError):
            pass

    # -- messages
    def _ecrire(self, msg: dict) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise RefusBlender("blender.coupe", 503)
        try:
            self.proc.stdin.write((json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            self.proc.stdin.flush()
        except OSError:
            raise RefusBlender("blender.coupe", 503) from None

    def notifier(self, methode: str, params: dict | None = None) -> None:
        m = {"jsonrpc": "2.0", "method": methode}
        if params is not None:
            m["params"] = params
        self._ecrire(m)

    def requete(self, methode: str, params: dict, delai: float):
        self.ident += 1
        ident = self.ident
        self._ecrire({"jsonrpc": "2.0", "id": ident, "method": methode, "params": params})
        fin = time.monotonic() + delai
        while True:
            reste = fin - time.monotonic()
            if reste <= 0:
                raise RefusBlender("blender.delai", 504, s=int(delai))
            try:
                brut = self.lignes.get(timeout=reste)
            except queue.Empty:
                continue
            if brut is None:
                raise RefusBlender("blender.coupe", 503)
            try:
                msg = json.loads(brut.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue                                   # une ligne qui n'est pas du JSON-RPC : ignorée
            if not isinstance(msg, dict):
                continue
            if "method" in msg:
                if "id" in msg:                            # une requête du serveur : nous ne la servons pas
                    self._ecrire({"jsonrpc": "2.0", "id": msg["id"],
                                  "error": {"code": -32601, "message": "Method not supported by this client"}})
                continue                                   # une notification (journal, progression) : ignorée
            if msg.get("id") != ident:
                continue
            if "error" in msg:
                e = msg.get("error") or {}
                raise RefusBlender("blender.protocole", 502, msg=str(e.get("message") or "")[:200])
            return msg.get("result")

    def appeler(self, nom: str, arguments: dict) -> dict:
        """Le résultat brut d'un outil {content, isError} ; aucune garde ici (voir `appeler` du module)."""
        r = self.requete("tools/call", {"name": nom, "arguments": arguments}, DELAIS_S.get(nom, 60.0))
        return r if isinstance(r, dict) else {"content": [], "isError": True}


# ── lecture des résultats ────────────────────────────────────────────────────────────────────────────────────────

def texte_de(r: dict) -> str:
    return "\n".join(str(c.get("text") or "") for c in (r or {}).get("content") or []
                     if isinstance(c, dict) and c.get("type") == "text")[:MAX_TEXTE]


def images_de(r: dict) -> list[bytes]:
    out = []
    for c in (r or {}).get("content") or []:
        if isinstance(c, dict) and c.get("type") == "image" and isinstance(c.get("data"), str):
            try:
                out.append(base64.b64decode(c["data"], validate=False))
            except ValueError:
                continue
    return out


def _juger(r: dict) -> dict:
    """Blender fermé → 503 ; un outil en erreur → 502 avec son texte (court)."""
    t = texte_de(r)
    if _FERME.search(t):
        raise RefusBlender("blender.ferme", 503, port=port())
    if r.get("isError") or t.lstrip().lower().startswith(("error", "rejected by safe mode", "couldn't")):
        raise RefusBlender("blender.outil_erreur", 502, msg=t.strip()[:300])
    return r


# ── les arguments permis, outil par outil ────────────────────────────────────────────────────────────────────────

def _chaine(v, n=200):
    if not isinstance(v, str):
        raise RefusBlender("blender.argument", 400, nom="texte")
    return v.strip()[:n]


def _entier(v, a, b, nom):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not a <= v <= b:
        raise RefusBlender("blender.argument", 400, nom=nom)
    return int(v)


def _liste_noms(v, nom, n=20):
    if not isinstance(v, list) or len(v) > n or not all(isinstance(x, str) and 0 < len(x) <= 120 for x in v):
        raise RefusBlender("blender.argument", 400, nom=nom)
    return list(v)


def nettoyer_arguments(nom: str, args: dict) -> dict:
    """Les arguments d'un outil de la liste blanche, bornés ; toute clé inconnue est refusée."""
    if not isinstance(args, dict):
        raise RefusBlender("blender.argument", 400, nom="arguments")
    permis = {"get_scene_info": ("query", "root", "fields", "limit"),
              "look": ("mode", "target", "views", "shading", "max_size", "distance"),
              "search_assets": ("source", "query", "asset_type", "category", "licence", "animated", "limit"),
              "import_asset": ("source", "id", "asset_type", "target_size", "resolution")}[nom]
    en_trop = sorted(set(args) - set(permis))
    if en_trop:
        raise RefusBlender("blender.argument", 400, nom=", ".join(en_trop)[:80])
    out: dict = {}
    for k, v in args.items():
        if v is None:
            continue
        if k in ("query", "root", "category"):
            out[k] = _chaine(v, 120)
        elif k == "fields":
            out[k] = [f for f in _liste_noms(v, k) if f in CHAMPS_SCENE] or ["location", "size"]
        elif k == "limit":
            out[k] = _entier(v, 1, 200 if nom == "get_scene_info" else 30, k)
        elif k == "mode":
            if v not in MODES_LOOK:
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = v
        elif k == "shading":
            if v not in OMBRAGES:
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = v
        elif k == "target":
            out[k] = _liste_noms(v, k)
        elif k == "views":
            if not isinstance(v, list) or not 0 < len(v) <= 6 or not all(x in VUES for x in v):
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = list(v)
        elif k == "max_size":
            out[k] = _entier(v, 200, 1600, k)
        elif k == "distance":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.1 <= v <= 1000:
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = float(v)
        elif k == "source":
            if v not in SOURCES:
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = v
        elif k == "asset_type":
            if v not in ("hdris", "textures", "models", "all"):
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = v
        elif k == "licence":
            if v not in ("CC0", "CC-BY"):
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = v
        elif k == "animated":
            if not isinstance(v, bool):
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = v
        elif k == "id":
            s = _chaine(v, 120)
            if not re.match(r"^[A-Za-z0-9_\-.]{1,120}$", s):
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = s
        elif k == "target_size":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.01 <= v <= 500:
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = float(v)
        elif k == "resolution":
            if v not in ("1k", "2k"):
                raise RefusBlender("blender.argument", 400, nom=k)
            out[k] = v
    if nom == "search_assets" and "source" not in out:
        raise RefusBlender("blender.argument", 400, nom="source")
    if nom == "import_asset" and ("source" not in out or "id" not in out):
        raise RefusBlender("blender.argument", 400, nom="source, id")
    return out


def appeler(nom: str, args: dict | None = None, session: Session | None = None) -> dict:
    """UN outil de la LISTE BLANCHE, arguments bornés. generate_3d et execute_blender_code n'y sont pas : leurs seules
    portes sont `generer_3d` (après devis, confirme_cout et plafonds) et `executer_gabarit` (code du serveur)."""
    if nom not in LISTE_BLANCHE:
        raise RefusBlender("blender.outil_refuse", 403, nom=str(nom)[:60])
    propres = nettoyer_arguments(nom, args or {})
    if session is not None:
        return _juger(session.appeler(nom, propres))
    with Session() as s:
        return _juger(s.appeler(nom, propres))


# ── les opérations ───────────────────────────────────────────────────────────────────────────────────────────────

def sonder() -> dict:
    """Lance le serveur, lit ses outils et l'état de Blender (get_scene_info, une ligne). Rien n'est modifié."""
    with Session() as s:
        noms = sorted(o.get("name") for o in s.outils if isinstance(o.get("name"), str))
        r = s.appeler("get_scene_info", {"limit": 1})
        t = texte_de(r)
        return {"serveur": {k: s.serveur.get(k) for k in ("name", "version")}, "outils": noms,
                "connecte": not _FERME.search(t) and not r.get("isError"), "entete": t.splitlines()[0][:300] if t else ""}


def scene(query: str = "", limit: int = 60) -> dict:
    a = {"limit": limit, "fields": ["location", "size", "hidden"]}
    if query:
        a["query"] = query
    t = texte_de(appeler("get_scene_info", a))
    return {"texte": t, "objets": objets_listes(t)}


def objets_listes(texte: str) -> list[str]:
    """PUR — les noms d'objets d'un résumé get_scene_info (« Showing n of m (...): » puis une ligne par objet,
    « nom | type | … »)."""
    out, dedans = [], False
    for l in str(texte or "").splitlines():
        if l.startswith("Showing "):
            dedans = True
            continue
        if dedans and " | " in l and not l.startswith("..."):
            nom = l.split(" | ", 1)[0].strip().lstrip("- ").strip()
            if nom:
                out.append(nom)
    return out


def regarder(mode: str = "camera", shading: str | None = None, max_size: int = 960) -> dict:
    """Une capture de la scène (look) rangée dans outputs/blender/regards/<id>.png. Lecture : rien n'est modifié dans
    Blender (l'outil restaure ce qu'il change pour la prise)."""
    a = {"mode": mode, "max_size": max_size}
    if shading:
        a["shading"] = shading
    with Session() as s:
        r = appeler("look", a, session=s)
        pngs = images_de(r)
        if not pngs:
            raise RefusBlender("blender.sans_image", 502)
        try:
            objets = objets_listes(texte_de(s.appeler("get_scene_info", {"limit": 200, "fields": ["hidden"]})))
        except RefusBlender:
            objets = []
    rid = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    d = dossier_regards()
    (d / f"{rid}.png").write_bytes(pngs[0])
    legende = texte_de(r).strip()[:500]
    meta = {"id": rid, "mode": mode, "shading": shading, "legende": legende,
            "date": datetime.now().isoformat(timespec="seconds"), "licences": licences_en_scene(objets)}
    _ecrire_json(d / f"{rid}.json", meta)
    _purger_regards(d)
    return meta


def dossier_regards() -> Path:
    d = config.settings.outputs_path / "blender" / "regards"
    d.mkdir(parents=True, exist_ok=True)
    return d


_RID = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{4}$")


def regard_valide(rid: str) -> bool:
    return bool(_RID.match(str(rid or "")))


def lire_regard(rid: str) -> dict | None:
    if not regard_valide(rid):
        return None
    m = _lire_json(dossier_regards() / f"{rid}.json", {})
    return m or None


def _purger_regards(d: Path, garder: int = 30) -> None:
    pngs = sorted(d.glob("*.png"), reverse=True)
    for f in pngs[garder:]:
        for x in (f, f.with_suffix(".json")):
            try:
                x.unlink()
            except OSError:
                pass


def executer_gabarit(params: dict) -> dict:
    """Le SEUL chemin vers execute_blender_code : un script de blender_gabarits (gabarit fixe + JSON vérifié)."""
    from app.services import blender_gabarits as G
    try:
        script = G.generer_script(params)
    except G.GabaritRefuse as e:
        raise RefusBlender("blender.gabarit", 400, msg=str(e)[:200]) from None
    with Session() as s:
        r = _juger(s.appeler("execute_blender_code", {"code": script}))
    t = texte_de(r)
    return {"resume": G.lire_resume(t), "texte": t.strip()[:600]}


def reprendre(params: dict, vignette: bool = True) -> dict:
    """t332 — « Reprendre depuis Blender » : le gabarit de RETOUR (lecture des caméras et des objets DZ_, copie .blend
    au chemin du serveur), puis, dans la même session et si possible, une vignette par `look` (vue caméra). La vignette
    est facultative : son échec ne fait pas échouer le retour."""
    from app.services import blender_gabarits as G
    try:
        script = G.generer_script_retour(params)
    except G.GabaritRefuse as e:
        raise RefusBlender("blender.gabarit", 400, msg=str(e)[:200]) from None
    with Session() as s:
        r = _juger(s.appeler("execute_blender_code", {"code": script}))
        image = None
        if vignette:
            try:
                ims = images_de(appeler("look", {"mode": "camera", "max_size": 640}, session=s))
                image = ims[0] if ims and ims[0][:8] == b"\x89PNG\r\n\x1a\n" else None
            except RefusBlender:
                image = None
        try:
            objets = objets_listes(texte_de(s.appeler("get_scene_info", {"limit": 200, "fields": ["hidden"]})))
        except RefusBlender:
            objets = []
    return {"resume": G.lire_resume(texte_de(r)), "image": image, "licences": licences_en_scene(objets)}


_ID_PLAN = re.compile(r"^[0-9A-Za-z-]{1,40}$")


def dossier_plans() -> Path:
    """t332 : outputs/blender/plans/<plan>/ (maquette.glb) et <plan>/<retour>/ (copie .blend, retour.json, vignette)."""
    d = config.settings.outputs_path / "blender" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lire_retour(shot_id: str, rid: str) -> dict | None:
    """Le retour.json d'un « Reprendre depuis Blender » (identifiants vérifiés), ou None."""
    if not _ID_PLAN.match(shot_id or "") or not regard_valide(rid):
        return None
    m = _lire_json(dossier_plans() / shot_id / rid / "retour.json", {})
    return m or None


def retours_du_plan(shot_id: str) -> list[str]:
    """Les identifiants des retours d'un plan, le plus récent d'abord."""
    d = dossier_plans() / shot_id
    if not _ID_PLAN.match(shot_id or "") or not d.is_dir():
        return []
    return sorted((x.name for x in d.iterdir() if x.is_dir() and regard_valide(x.name)), reverse=True)


def generer_3d(prompt: str, fournisseur: str = "auto", nom: str = "", job: str = "") -> dict:
    """generate_3d — APPELÉE SEULEMENT par la route POST /api/blender/generer, après le 409 `confirme_cout` et la
    garde des plafonds. `job` reprend une génération déjà payée (aucun nouveau paiement : le serveur la reprend)."""
    if fournisseur not in FOURNISSEURS_3D:
        raise RefusBlender("blender.argument", 400, nom="fournisseur")
    a: dict = {"provider": fournisseur, "wait_seconds": 45}
    if job:
        a["job"] = _chaine(job, 200)
    else:
        p = _chaine(prompt, 300)
        if not p:
            raise RefusBlender("blender.argument", 400, nom="prompt")
        a["prompt"] = p
    if nom:
        from app.services.blender_gabarits import nom_sur
        a["name"] = nom_sur(nom, "Genere")
    with Session() as s:
        r = _juger(s.appeler("generate_3d", a))
    t = texte_de(r).strip()
    m = re.search(r"job[\"'= :]+([A-Za-z0-9:_\-.]{6,200})", t)
    return {"texte": t[:1200], "job": m.group(1) if m and "import" not in t.lower()[:80] else None}


# ── provenance des assets importés ───────────────────────────────────────────────────────────────────────────────

_BLOC = re.compile(r"^- (?P<nom>.+?) \((?:UID|ID): (?P<id>[^)]+)\)\s*$")


def licences_de_recherche(source: str, texte: str) -> dict:
    """PUR — {id: {nom, auteur, licence}} d'une liste search_assets. Poly Haven : CC0 (toute la bibliothèque)."""
    out, cur = {}, None
    for l in str(texte or "").splitlines():
        m = _BLOC.match(l.strip()) if l.startswith("- ") else None
        if m:
            cur = {"nom": m.group("nom")[:120], "auteur": None, "licence": "CC0" if source == "polyhaven" else None}
            out[m.group("id").strip()[:120]] = cur
            continue
        s = l.strip()
        if cur is None:
            continue
        if s.startswith("Author:"):
            cur["auteur"] = s[7:].strip()[:120]
        elif s.startswith(("License:", "Licence:")):
            cur["licence"] = s.split(":", 1)[1].strip()[:80]
    return out


def chercher(args: dict) -> dict:
    propres = nettoyer_arguments("search_assets", args)
    t = texte_de(appeler("search_assets", propres))
    trouves = licences_de_recherche(propres["source"], t)
    cache = _lire_json(dossier() / "recherches.json", {})
    for i, v in trouves.items():
        cache[f"{propres['source']}:{i}"] = v
    if len(cache) > MAX_RECHERCHES:
        cache = dict(list(cache.items())[-MAX_RECHERCHES:])
    _ecrire_json(dossier() / "recherches.json", cache)
    return {"texte": t, "resultats": [{"id": i, **v} for i, v in trouves.items()]}


def provenance_import(source: str, aid: str, texte: str) -> dict:
    """PUR (sauf le cache lu par l'appelant) — ce qu'un import dit de lui : objets, licence, attribution."""
    objets, licence, attribution, titre = [], None, None, None
    for l in str(texte or "").splitlines():
        s = l.strip()
        if s.startswith("Created objects:"):
            objets = [x.strip() for x in s.split(":", 1)[1].split(",") if x.strip() and x.strip() != "none"][:50]
        elif s.startswith(("Licence:", "License:")):
            licence = s.split(":", 1)[1].strip()[:80]
        elif s.startswith("Attribution:"):
            attribution = s.split(":", 1)[1].strip()[:300]
        elif s.startswith("Title:"):
            titre = s.split(":", 1)[1].strip()[:120]
    if source == "polyhaven":
        licence = "CC0"
    return {"source": source, "id": aid, "objets": objets, "licence": licence, "attribution": attribution,
            "titre": titre}


def importer(args: dict) -> dict:
    """import_asset puis la PROVENANCE : licence (réponse, sinon la recherche gardée), auteur, attribution, objets."""
    propres = nettoyer_arguments("import_asset", args)
    t = texte_de(appeler("import_asset", propres))
    p = provenance_import(propres["source"], propres["id"], t)
    connu = _lire_json(dossier() / "recherches.json", {}).get(f"{propres['source']}:{propres['id']}") or {}
    p["licence"] = p["licence"] or connu.get("licence") or "inconnue"
    p["auteur"] = connu.get("auteur")
    p["titre"] = p["titre"] or connu.get("nom")
    p["date"] = datetime.now().isoformat(timespec="seconds")
    journal = _lire_json(dossier() / "provenance.json", [])
    journal.append(p)
    _ecrire_json(dossier() / "provenance.json", journal[-MAX_PROVENANCE:])
    return {"texte": t, "provenance": p}


def provenance() -> list[dict]:
    return _lire_json(dossier() / "provenance.json", [])


def licences_en_scene(objets: list[str]) -> list[dict]:
    """Les imports dont un objet est encore dans la scène (nom exact), le plus récent d'abord, sans doublon."""
    presents = set(objets or [])
    out, vus = [], set()
    for p in reversed(provenance()):
        cle = (p.get("source"), p.get("id"))
        if cle in vus or not presents.intersection(p.get("objets") or []):
            continue
        vus.add(cle)
        out.append({k: p.get(k) for k in ("source", "id", "titre", "auteur", "licence", "attribution")})
    return out


def licence_resumee(licences: list[dict]) -> str | None:
    """La licence d'une capture qui montre des assets importés : « CC0 » si tous le sont, sinon les licences jointes
    (avec l'attribution exigée par CC-BY). None : aucun asset importé (la capture est une production de l'app)."""
    if not licences:
        return None
    ls = sorted({str(l.get("licence") or "inconnue") for l in licences})
    if ls == ["CC0"]:
        return "CC0"
    morceaux = []
    for l in licences:
        if l.get("licence") == "CC0":
            continue
        qui = l.get("attribution") or " — ".join(x for x in (l.get("titre"), l.get("auteur")) if x)
        morceaux.append(f"{l.get('licence') or 'inconnue'} ({qui or l.get('source')})")
    return "; ".join(morceaux)[:250]
