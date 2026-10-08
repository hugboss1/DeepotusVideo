"""Le moteur du Photolab : photocraft-cli 0.3.0 piloté en JSON lignes (t136, Photolab P1, 07/10/2026).

Décision D1 (validée par l'utilisateur le 07/10) : le CALCUL est celui de photocraft, pour que le Photolab produise
exactement ce que photocraft produit ; notre écran (P2) ne fait que le piloter. Un processus `photocraft-cli serve`
par backend, démarré à la première demande, arrêté avec le backend (fin de stdin = fin du serveur).

Le moteur ne voit qu'un dossier : <données>/photolab/, sa racine de lecture ET d'écriture. Il refuse lui-même les
chemins absolus, `..` et les préfixes Windows (crates/automation/src/workspace.rs) ; `relatif` applique la même règle
AVANT l'envoi, pour qu'un refus soit dit ici, en français, et jamais tenté.
"""
import itertools
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

VERSION = "0.3.0"
RACINE_APP = Path(__file__).resolve().parents[3]          # le dépôt, ou %LOCALAPPDATA%\DeepotusVideoGen installé
SOUS_DOSSIERS = ("entrees", "rendus", "exports")
_REL = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._-]*(/[A-Za-z0-9_-][A-Za-z0-9._-]*)*")
# Noms de périphériques Windows : « CON.png » désigne le périphérique, pas un fichier, même avec une extension.
_PERIPH = re.compile(r"(con|prn|aux|nul|com[0-9]|lpt[0-9])", re.IGNORECASE)
_SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class MoteurAbsent(RuntimeError):
    """Le binaire photocraft-cli n'est pas là (pas encore fourni, ou installation incomplète)."""


class MoteurErreur(RuntimeError):
    """Le moteur a répondu ok:false (le message est le sien) ou s'est arrêté."""


class MoteurDelai(RuntimeError):
    """Pas de réponse dans le délai : le moteur a été arrêté et sera relancé à la demande suivante."""


class MoteurOccupe(RuntimeError):
    """Une autre opération tient la session : on n'attend pas plus que le délai de la demande pour le verrou."""


def chemin_cli() -> Path:
    env = os.environ.get("PHOTOCRAFT_CLI")
    if env and Path(env).is_file():
        return Path(env)
    base = RACINE_APP / "vendor" / f"photocraft-{VERSION}"
    if base.is_dir():
        for c in sorted(base.rglob("photocraft-cli.exe")):
            return c
    raise MoteurAbsent(f"Moteur du Photolab absent : photocraft-cli {VERSION} introuvable sous {base} — "
                       "lance `python scripts/vendor_photocraft.py`.")


def dossier_travail() -> Path:
    from app.config import DATA_ROOT
    d = Path(DATA_ROOT) / "photolab"
    for s in SOUS_DOSSIERS:
        (d / s).mkdir(parents=True, exist_ok=True)
    return d


def relatif(p) -> str:
    """Un chemin relatif sûr (barres obliques, ni `..`, ni `.`, ni absolu, ni espace) — sinon ValueError.
    Refusés aussi, parce que Windows les traite à part : un nom de périphérique (CON, NUL, COM1…) même avec une
    extension, un segment qui finit par « . » (Windows le retire en silence : `a.` devient `a`), et plus de 200
    caractères (marge sous les 260 de MAX_PATH une fois le dossier de travail ajouté)."""
    if not isinstance(p, str) or len(p) > 200 or not _REL.fullmatch(p):
        raise ValueError(f"chemin refusé : {p!r}")
    for seg in p.split("/"):
        if seg in (".", "..") or seg.endswith(".") or _PERIPH.fullmatch(seg.split(".")[0]):
            raise ValueError(f"chemin refusé : {p!r}")
    return p


_ID_COMMANDE = re.compile(r"[a-z][A-Za-z0-9]*(\.[a-z][A-Za-z0-9]*)+")
PREFIXES_REFUSES = ("file.", "app.", "automate.", "plugin.", "script", "window.", "help.", "edit.preferences",
                    "edit.presets", "edit.keyboardshortcuts", "edit.menus")      # comparés sur cid.lower()
# Clés qui désignent un fichier. Les noms COURTS (out, lut, src, dir…) ne sont refusés qu'en entier : en sous-chaîne
# ils attraperaient des paramètres de réglage légitimes (`outBlack` des niveaux, `resolution`, `direction`).
CLES_FICHIER_PARTIE = ("path", "file", "folder", "url", "uri", "source", "dest", "output", "profile", "preset")
CLES_FICHIER_ENTIERES = {"dir", "directory", "src", "out", "lut", "paths"}
_EXT_FICHIER = (".png", ".jpg", ".jpeg", ".psd", ".psb", ".pcraft", ".tif", ".tiff", ".webp", ".gif", ".bmp", ".tga",
                ".exr", ".hdr", ".cube", ".3dl", ".look", ".icc", ".icm", ".abr", ".grd", ".pat", ".json", ".exe",
                ".dll", ".wasm", ".txt", ".csv", ".pdf", ".ai")
_LECTEUR = re.compile(r"^[A-Za-z]:")


def _cle_fichier(k) -> bool:
    k = str(k).lower()
    return k in CLES_FICHIER_ENTIERES or any(m in k for m in CLES_FICHIER_PARTIE)


def _valeur_fichier(v: str) -> bool:
    """Une chaîne qui ressemble à une référence de fichier : séparateur de chemin, lecteur, extension connue.
    « 16:9 », « #336699 », « normal » passent."""
    return "/" in v or "\\" in v or bool(_LECTEUR.match(v)) or v.lower().endswith(_EXT_FICHIER)


def _suspect(v):
    """Une clé ou une valeur de fichier n'importe où dans les paramètres (dicts et listes imbriqués) — son nom ou None."""
    if isinstance(v, dict):
        for k, w in v.items():
            if _cle_fichier(k):
                return f"clé {k!r}"
            r = _suspect(w)
            if r:
                return r
    elif isinstance(v, list):
        for w in v:
            r = _suspect(w)
            if r:
                return r
    elif isinstance(v, str) and _valeur_fichier(v):
        return f"valeur {v!r}"
    return None


def commande_autorisee(cid, params) -> str:
    """L'id d'une commande moteur que l'écran peut lancer — sinon ValueError. Refusées : tout ce qui touche des
    fichiers, l'application ou du code (préfixes ci-dessus, casse ignorée), et toute commande dont les paramètres
    nomment OU contiennent un fichier : les fichiers passent par les routes du Photolab, jamais par une commande.
    Défense en profondeur derrière les racines de lecture/écriture que le moteur impose lui-même."""
    if not isinstance(cid, str) or not _ID_COMMANDE.fullmatch(cid):
        raise ValueError(f"commande illisible : {cid!r}")
    if cid.lower().startswith(PREFIXES_REFUSES):
        raise ValueError(f"commande réservée aux routes du Photolab : {cid}")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError(f"{cid} : les paramètres doivent être un objet")
    r = _suspect(params)
    if r:
        raise ValueError(f"{cid} : {r} désigne un fichier — passe par les routes du Photolab")
    return cid


class SessionMoteur:
    """Une session `photocraft-cli serve` : une requête à la fois (verrou), réponse appariée par id, délai par
    requête. Un délai dépassé ou un moteur mort arrêtent le processus ; la demande suivante en relance un neuf
    (`generation` +1) — ses documents ouverts sont alors PERDUS, l'écran (P2) relit `generation` pour le dire."""

    def __init__(self, commande: list, delai_s: float = 60.0):
        self.commande = list(commande)
        self.delai_s = delai_s
        self.generation = 0
        self.ferme = False                                # fermé pour de bon : plus aucun redémarrage
        self._proc = None
        self._lignes = None
        self._ids = itertools.count(1)
        self._verrou = threading.Lock()

    def vivant(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _demarrer(self):
        try:
            proc = subprocess.Popen(self.commande, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, creationflags=_SANS_FENETRE)
        except FileNotFoundError:
            raise MoteurAbsent(f"Moteur du Photolab absent : {self.commande[0]} introuvable — "
                               "lance `python scripts/vendor_photocraft.py`.")
        except OSError as e:
            raise MoteurErreur(f"le moteur n'a pas pu démarrer : {e}")
        self._proc = proc
        self._lignes = queue.Queue()
        threading.Thread(target=self._lire, args=(proc, self._lignes), daemon=True).start()
        self.generation += 1                              # seulement après un lancement réussi

    @staticmethod
    def _lire(proc, q):
        try:
            for brut in proc.stdout:
                q.put(brut)
        except (OSError, ValueError):
            pass                                          # tube fermé sous nos pieds par fermer()
        q.put(None)                                       # fin de flux : le moteur s'est arrêté

    def fermer(self, brutal: bool = False, definitif: bool = False):
        """Arrête le moteur. `definitif` : arrêt du backend — une demande encore en vol qui tient cette session ne doit
        pas relancer un processus que plus personne n'arrêterait. `brutal` : kill tout de suite, sans les 2 s de grâce après la fermeture de stdin — pour
        un délai dépassé, où le moteur ne répond de toute façon plus."""
        if definitif:
            self.ferme = True
        p, self._proc = self._proc, None
        if p is None:
            return
        try:
            if p.poll() is None:
                if not brutal:
                    try:
                        p.stdin.close()                   # fin de stdin = fin propre du serveur
                        p.wait(timeout=2)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                if p.poll() is None:
                    p.kill()
                p.wait()
        finally:
            for f in (p.stdin, p.stdout):                 # même si le processus était déjà mort : pas de fuite de tube
                try:
                    f.close()
                except (OSError, ValueError):
                    pass

    def appeler(self, methode: str, params: dict | None = None, delai_s: float | None = None):
        return self.appeler_g(methode, params, delai_s)[0]

    def appeler_g(self, methode: str, params: dict | None = None, delai_s: float | None = None):
        """(résultat, génération qui a répondu) — la génération est lue DANS le verrou, après un éventuel
        redémarrage : l'écran sait ainsi que ses documents ouverts ont disparu."""
        delai = self.delai_s if delai_s is None else delai_s
        if not self._verrou.acquire(timeout=delai):
            raise MoteurOccupe("moteur occupé : une opération est en cours")
        try:
            gen = self._preparer()
            return self._echange(self._proc, self._lignes, methode, params, delai), gen
        finally:
            self._verrou.release()

    def _preparer(self) -> int:
        """SOUS le verrou : le moteur est vivant (relancé au besoin) ; rend la génération qui va répondre."""
        if self.ferme:                                    # relu sous le verrou : l'arrêt a pu tomber pendant l'attente
            raise MoteurAbsent("Photolab arrêté")
        if not self.vivant():
            self._demarrer()
        return self.generation

    def _echange(self, proc, lignes, methode, params, delai):
        """UNE requête sur CE processus, SOUS le verrou. `proc`/`lignes` sont des locaux : un fermer() concurrent ne
        nous casse pas. Ne relance jamais rien (le redémarrage est l'affaire de `_preparer`)."""
        rid = next(self._ids)
        try:
            proc.stdin.write((json.dumps({"id": rid, "method": methode, "params": params or {}}) + "\n")
                             .encode("utf-8"))
            proc.stdin.flush()
        except (OSError, ValueError):
            self.fermer()
            raise MoteurErreur(f"{methode} : le moteur s'est arrêté")
        fin = time.monotonic() + delai
        while True:
            reste = fin - time.monotonic()
            if reste <= 0:
                self.fermer(brutal=True)
                raise MoteurDelai(f"{methode} : pas de réponse en {delai:g} s — moteur arrêté, relancé à la "
                                  "demande suivante")
            try:
                brut = lignes.get(timeout=reste)
            except queue.Empty:
                continue
            if brut is None:
                self.fermer()
                raise MoteurErreur(f"{methode} : le moteur s'est arrêté")
            try:
                rep = json.loads(brut.decode("utf-8"))
            except ValueError:
                continue                                  # une ligne qui n'est pas une réponse (journal, bruit)
            if not isinstance(rep, dict):
                continue
            if rep.get("id") is None and not rep.get("ok"):
                # `{"id":null,"ok":false}` = le moteur n'a pas pu lire NOTRE ligne ; une seule requête à la fois,
                # donc c'est la nôtre : inutile d'attendre le délai.
                raise MoteurErreur(str(rep.get("error") or "requête illisible pour le moteur"))
            if rep.get("id") != rid:
                continue
            if rep.get("ok"):
                return rep.get("result")
            raise MoteurErreur(str(rep.get("error") or "erreur du moteur"))

    def sequence(self, fn, delai_s: float | None = None):
        """(résultat de fn, génération) — plusieurs étapes du moteur tenues d'un seul tenant (t137, vignettes et
        historique). Le verrou est pris UNE fois (attente bornée -> MoteurOccupe) et `fn(appel, gen)` reçoit un
        `appel(methode, params=None, delai_etape=None)` qui parle au moteur SANS reprendre le verrou : aucun autre appel
        ne peut s'intercaler entre deux étapes (sinon une demande étrangère verrait, ou agirait sur, le document
        COPIE que les vignettes ouvrent un instant).
        Redémarrage : le moteur est (re)lancé UNE fois, avant la première étape, et `gen` est sa génération. Si le
        processus meurt ou dépasse son délai en cours de route, les étapes suivantes lèvent MoteurErreur : jamais
        elles ne se rejouent sur un moteur neuf et vide, dont les documents ne sont plus ceux de la séquence."""
        delai = self.delai_s if delai_s is None else delai_s
        if not self._verrou.acquire(timeout=delai):
            raise MoteurOccupe("moteur occupé : une opération est en cours")
        try:
            gen = self._preparer()
            proc, lignes = self._proc, self._lignes

            def appel(methode, params=None, delai_etape=None):
                if self._proc is not proc or proc.poll() is not None:
                    raise MoteurErreur(f"{methode} : le moteur s'est arrêté pendant la séquence")
                return self._echange(proc, lignes, methode, params, delai if delai_etape is None else delai_etape)
            return fn(appel, gen), gen
        finally:
            self._verrou.release()


FABRIQUE = None                                           # bancs : une fabrique de fausse session
_SESSION = None
_VERROU_SESSION = threading.Lock()


def session() -> SessionMoteur:
    global _SESSION
    with _VERROU_SESSION:
        if _SESSION is None:
            if FABRIQUE is not None:
                _SESSION = FABRIQUE()
            else:
                d = dossier_travail()
                _SESSION = SessionMoteur([str(chemin_cli()), "serve", "--automation-read-root", str(d),
                                          "--automation-write-root", str(d)])
        return _SESSION


def fermer():
    global _SESSION
    with _VERROU_SESSION:
        if _SESSION is not None:
            _SESSION.fermer(definitif=True)
        _SESSION = None


def _a_plat(calques):
    """L'arbre de calques de `doc.inspect` (haut -> bas, groupes avec `children`) à plat, groupes compris."""
    for c in calques or []:
        yield c
        yield from _a_plat(c.get("children"))


def _conteneur(c) -> bool:
    return str(c.get("kind", "")).lower() in ("group", "artboard")


# Cache des vignettes : variable de MODULE, clé de base (génération, document, révision), puis une entrée par maxSide.
# La génération fait partie de la clé, donc un redémarrage du moteur l'invalide tout seul ; si une future route
# réinitialise la session SANS changer de génération, elle doit vider ce cache (et les vig-* de rendus/).
_CACHE_VIGNETTES = {"base": None, "tailles": {}}
_VIG = re.compile(r"vig-\d+-\d+-\d+-\d+\.png")
# Seuls les calques qui se rendent seuls de façon parlante ont une vignette : un réglage, un remplissage… n'a rien
# à montrer sans ce qu'il modifie. Un calque d'écrêtage (clipped) est rendu SANS son calque de base : accepté en P2.
_RENDUS_SEULS = {"pixel", "text", "type", "shape", "smart", "smartobject", "video", "frame"}


def vignettes(s: SessionMoteur, max_side: int):
    """(noms, génération) — un rendu PAR CALQUE du document actif, `noms` = {id du calque: fichier sous rendus/}
    (t137, écran P2). Le moteur ne sait rendre ni un calque seul ni une région : on COPIE le document
    (`image.duplicate`), on n'allume que le calque voulu sur la copie, on rend, puis on referme la copie et on
    rend l'original actif — le document de l'utilisateur n'est jamais touché (même révision, mêmes visibilités).
    Tout se passe dans UNE séquence sous le verrou (`SessionMoteur.sequence`) : personne ne voit la copie.
    Cache par (génération, document, révision, maxSide) : une deuxième demande à la même révision ne relance rien.
    Les vignettes d'une autre révision sont supprimées ; le maxSide est dans le nom du fichier (deux tailles de la
    même révision coexistent).
    Coût : le verrou est tenu pendant ~N_calques × 4 appels du moteur (allumer, rendre, éteindre + la mise en
    place) ; acceptable en P2, une version par `batch` est une suite possible."""
    d = dossier_travail() / "rendus"

    def fn(appel, gen):
        sl = appel("session.list") or {}
        actif = sl.get("active")
        if actif is None:
            return {}                                      # aucun document : rien à copier
        n_avant = len(sl.get("documents") or [])
        insp = appel("doc.inspect")
        rev = insp["revision"]
        feuilles = [c for c in _a_plat(insp.get("layers"))
                    if not _conteneur(c) and str(c.get("kind", "")).lower() in _RENDUS_SEULS]
        base = (gen, actif, rev)
        noms = {str(c["id"]): f"vig-{gen}-{c['id']}-{rev}-{max_side}.png" for c in feuilles}
        if (_CACHE_VIGNETTES["base"] == base and max_side in _CACHE_VIGNETTES["tailles"]
                and all((d / n).is_file() for n in noms.values())):
            return dict(_CACHE_VIGNETTES["tailles"][max_side])
        copie, reussi = None, False
        try:
            res = appel("engine.execute", {"command": "image.duplicate", "params": {"name": "dz-vignettes"}})
            # La copie devient le document actif. On la repère d'abord par le compte (un document de plus qu'avant),
            # pour la refermer même si le moteur ne dit pas son index.
            apres = appel("session.list") or {}
            if len(apres.get("documents") or []) == n_avant + 1 and isinstance(apres.get("active"), int):
                copie = apres["active"]
            idx = res.get("document") if isinstance(res, dict) else None
            if not isinstance(idx, int) or isinstance(idx, bool):
                raise MoteurErreur("vignettes : image.duplicate n'a pas rendu l'index du document copié")
            if copie is None:
                copie = idx
            # la copie redonne des identifiants à ses calques : on les apparie PAR POSITION dans l'arbre (même ordre)
            plats = list(_a_plat(appel("doc.inspect").get("layers")))
            ids_origine = [c["id"] for c in _a_plat(insp.get("layers"))]
            if len(plats) != len(ids_origine):
                raise MoteurErreur("vignettes : la copie du document n'a pas la même structure de calques")
            cible = {}                                     # id d'origine -> id dans la copie
            for orig, cp in zip(ids_origine, plats):
                cible[orig] = cp["id"]
                visible = _conteneur(cp)                   # les groupes restent allumés : un enfant seul doit se voir
                if bool(cp.get("visible")) != visible:
                    appel("engine.execute", {"command": "layer.setProps", "params": {"layer": cp["id"], "visible": visible}})
            for c in feuilles:
                lid = cible[c["id"]]
                appel("engine.execute", {"command": "layer.setProps", "params": {"layer": lid, "visible": True}})
                appel("doc.render", {"path": relatif(f"rendus/{noms[str(c['id'])]}"), "maxSide": max_side})
                appel("engine.execute", {"command": "layer.setProps", "params": {"layer": lid, "visible": False}})
            reussi = True
        finally:
            # quoi qu'il arrive la copie est refermée et l'original redevient actif ; si le moteur est mort, ces
            # appels lèvent à leur tour : on ne masque l'erreur d'origine par aucune autre, mais un nettoyage raté
            # APRÈS une réussite est dit (le document de l'utilisateur ne serait pas dans l'état annoncé)
            try:
                if copie is not None:
                    appel("doc.close", {"index": copie})
                    appel("doc.select", {"index": actif})
            except (MoteurErreur, MoteurDelai):
                if reussi:
                    raise
        if _CACHE_VIGNETTES["base"] != base:               # autre révision : toutes les tailles précédentes sont périmées
            _CACHE_VIGNETTES["base"], _CACHE_VIGNETTES["tailles"] = base, {}
        _CACHE_VIGNETTES["tailles"][max_side] = noms
        gardes = {n for t in _CACHE_VIGNETTES["tailles"].values() for n in t.values()}
        for f in d.iterdir():                              # les vignettes d'une autre révision n'ont plus d'usage
            if _VIG.fullmatch(f.name) and f.name not in gardes:
                try:
                    f.unlink()
                except OSError:
                    pass
        return dict(noms)
    return s.sequence(fn)


def historique(s: SessionMoteur, sens: str, n: int):
    """({"inspect": doc.inspect après, "completed": n faits, "failed": n refusés}, génération) — `n` annulations
    (`sens` « annuler ») ou rétablissements, en UNE requête `batch` : le moteur n'a aucun saut direct dans
    l'historique. L'inspection suit dans la même séquence, pour que l'écran voie l'état produit par CES étapes et
    non celui d'une demande intercalée. Demander plus que ce qui existe n'est pas une erreur : `completed` < n et
    `failed` ≥ 1 le disent à l'écran."""
    commande = {"annuler": "edit.undo", "retablir": "edit.redo"}[sens]

    def fn(appel, gen):
        r = appel("batch", {"steps": [{"command": commande} for _ in range(n)], "stopOnError": True}) or {}
        return {"inspect": appel("doc.inspect"), "completed": int(r.get("completed") or 0),
                "failed": int(r.get("failed") or 0)}
    return s.sequence(fn)


def etat_session() -> dict:
    """Génération et vie de la session courante, sans la créer (les routes ne touchent pas à l'état privé)."""
    with _VERROU_SESSION:
        s = _SESSION
    return {"generation": s.generation if s else 0, "vivant": bool(s and s.vivant())}
