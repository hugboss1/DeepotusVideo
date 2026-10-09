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
import zipfile
from pathlib import Path

from app.services import photolab_registre as PR

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
# Familles refusées même si le registre les décrit (t136, complétées t138) : fichiers, application, code, et les
# 5 commandes NON gardées par le moteur qui lisent un chemin arbitraire (image.mode.* `profile`, import .abr / .grd,
# plugin.*) ou écrivent les préférences persistantes (prefs.*), plus l'export CSV du journal de mesures.
PREFIXES_REFUSES = ("file.", "app.", "automate.", "plugin.", "script", "window.", "help.", "edit.preferences",
                    "edit.presets", "edit.keyboardshortcuts", "edit.menus", "image.mode.", "brush.presets.import",
                    "gradient.presets.import", "prefs.", "measurementlog.export")      # comparés sur cid.lower()
_EXT_FICHIER = (".png", ".jpg", ".jpeg", ".psd", ".psb", ".pcraft", ".tif", ".tiff", ".webp", ".gif", ".bmp", ".tga",
                ".exr", ".hdr", ".cube", ".3dl", ".look", ".icc", ".icm", ".abr", ".grd", ".pat", ".json", ".exe",
                ".dll", ".wasm", ".txt", ".csv", ".pdf", ".ai")
_LECTEUR = re.compile(r"^[A-Za-z]:")


def _valeur_fichier(v: str) -> bool:
    """Une chaîne qui ressemble à une référence de fichier : séparateur de chemin, lecteur, extension connue.
    « 16:9 », « #336699 », « normal » passent."""
    return "/" in v or "\\" in v or bool(_LECTEUR.match(v)) or v.lower().endswith(_EXT_FICHIER)


def commande_autorisee(cid, params, registre=None, kind=None, etat=None) -> str:
    """L'id d'une commande moteur que l'écran peut lancer — sinon ValueError. Depuis t138 : LISTE BLANCHE sur le
    registre du moteur épinglé (`PR.verifier` : commande connue, clés décrites, types et bornes), derrière les
    familles refusées (PREFIXES_REFUSES) et le refus de toute valeur « fichier ». Sans registre on refuse tout :
    l'ancienne liste de refus seule laissait passer clés inconnues, mauvais types et `blend: 3`."""
    if registre is None:
        raise ValueError("registre du moteur indisponible")
    PR.verifier(registre, cid, params, kind, etat)
    return cid


# Registre structuré, en cache par (session, génération) : `engine.commands` est lu et parsé UNE fois par démarrage
# du moteur, alors que /commandes (menus) et /executer (chaque geste) le consultent sans cesse.
_CACHE_REGISTRE = {"session": None, "gen": None, "registre": None}
_VERROU_REGISTRE = threading.Lock()


def _structure(s, gen, brut) -> dict:
    with _VERROU_REGISTRE:
        if _CACHE_REGISTRE["session"] is s and _CACHE_REGISTRE["gen"] == gen:
            return _CACHE_REGISTRE["registre"]
    liste = brut if isinstance(brut, list) else (brut or {}).get("commands") or []
    reg = PR.structurer(liste)
    with _VERROU_REGISTRE:
        _CACHE_REGISTRE.update({"session": s, "gen": gen, "registre": reg})
    return reg


def registre(s) -> dict:
    """id -> description structurée (PR.structurer) du registre de la session `s`. Sans appel au moteur si le cache
    est celui de cette session et de sa génération courante, moteur vivant ; sinon `engine.commands` puis parse."""
    with _VERROU_REGISTRE:
        c = dict(_CACHE_REGISTRE)
    # `session` d'abord : une session de remplacement des bancs n'a ni `generation` ni `vivant`
    if c["session"] is s and c["gen"] == getattr(s, "generation", None) and getattr(s, "vivant", lambda: False)():
        return c["registre"]
    brut, gen = s.appeler_g("engine.commands")
    return _structure(s, gen, brut)


def commandes(s):
    """(registre brut du moteur dont chaque entrée gagne ses `champs`, génération). Le brut est relu à chaque fois
    (`enabled` dépend du document ouvert) ; le parse, lui, sort du cache de la génération."""
    brut, gen = s.appeler_g("engine.commands")
    reg = _structure(s, gen, brut)
    liste = brut if isinstance(brut, list) else (brut or {}).get("commands") or []
    return [{**c, "champs": reg.get(c.get("id"), {}).get("champs", [])} for c in liste], gen


# t152 : repères du document. doc.inspect ne les rend pas (Document.guides) ; le .pcraft les enregistre dans
# manifest.json (document.guides {horizontal, vertical}). Cache par (génération, document actif, révision).
_CACHE_REPERES = {"base": None, "reperes": None}
_VERROU_CACHE_REPERES = threading.Lock()
_NOM_REPERES = "reperes-lecture.pcraft"


def _guides(manifeste) -> dict:
    g = ((manifeste or {}).get("document") or {}).get("guides") or {}
    lire = lambda k: [float(x) for x in (g.get(k) or []) if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return {"horizontal": lire("horizontal"), "vertical": lire("vertical")}


def reperes(s: "SessionMoteur"):
    """({"horizontal": [...], "vertical": [...]} du document actif, génération) — None à la place du dict sans
    document. Le document de l'utilisateur n'est jamais touché : on COPIE (image.duplicate), on enregistre la COPIE
    en .pcraft sous rendus/ (doc.save rattache la copie, pas l'original), on la referme, on rend l'original actif,
    puis on lit le zip et on l'efface. Tout dans UNE séquence sous le verrou (personne ne voit la copie). Coût mesuré :
    ~130 ms en 1920 × 1080 ; l'écran ne relit qu'après une opération qui peut déplacer les repères."""
    d = dossier_travail() / "rendus"
    f = d / _NOM_REPERES

    def fn(appel, gen):
        sl = appel("session.list") or {}
        actif = sl.get("active")
        if actif is None:
            return None
        rev = appel("doc.inspect")["revision"]
        base = (gen, actif, rev)
        with _VERROU_CACHE_REPERES:
            if _CACHE_REPERES["base"] == base:
                return dict(_CACHE_REPERES["reperes"])
        n_avant = len(sl.get("documents") or [])
        copie, reussi, lus = None, False, None
        try:
            res = appel("engine.execute", {"command": "image.duplicate", "params": {"name": "dz-reperes"}})
            apres = appel("session.list") or {}
            if len(apres.get("documents") or []) == n_avant + 1 and isinstance(apres.get("active"), int):
                copie = apres["active"]
            idx = res.get("document") if isinstance(res, dict) else None
            if copie is None and isinstance(idx, int) and not isinstance(idx, bool):
                copie = idx
            if copie is None:
                raise MoteurErreur("repères : image.duplicate n'a pas rendu l'index du document copié")
            appel("doc.save", {"path": relatif(f"rendus/{_NOM_REPERES}")})
            reussi = True
        finally:
            try:
                if copie is not None:
                    appel("doc.close", {"index": copie})
                    appel("doc.select", {"index": actif})
            except (MoteurErreur, MoteurDelai):
                if reussi:
                    raise
        try:
            with zipfile.ZipFile(f) as z:
                lus = _guides(json.loads(z.read("manifest.json")))
        except (OSError, KeyError, ValueError, zipfile.BadZipFile) as e:
            raise MoteurErreur(f"repères : lecture du fichier de travail impossible ({e})")
        finally:
            try:
                f.unlink()
            except OSError:
                pass
        with _VERROU_CACHE_REPERES:
            _CACHE_REPERES["base"], _CACHE_REPERES["reperes"] = base, lus
        return dict(lus)
    return s.sequence(fn)


def elaguer_inspect(doc):
    """doc.inspect sans le tableau `lut` des calques Color Lookup (107 811 nombres : 2 Mo par calque, relevé t138),
    que l'écran ne lit pas : remplacé par None et marqué `lutElague`. Récursif dans les groupes (`children`)."""
    if not isinstance(doc, dict):
        return doc
    for c in _a_plat(doc.get("layers")):
        a = c.get("adjustment") if isinstance(c, dict) else None
        cl = a.get("ColorLookup") if isinstance(a, dict) else None
        if isinstance(cl, dict) and cl.get("lut") is not None:
            cl["lut"] = None
            cl["lutElague"] = True
    return doc


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
        # edit.undo / edit.redo partent ici sans passer par la liste blanche : la commande est choisie par le
        # service (deux valeurs possibles), jamais par l'écran.
        r = appel("batch", {"steps": [{"command": commande} for _ in range(n)], "stopOnError": True}) or {}
        return {"inspect": elaguer_inspect(appel("doc.inspect")), "completed": int(r.get("completed") or 0),
                "failed": int(r.get("failed") or 0)}
    return s.sequence(fn)


# ── t138 (P3, Task A3) : aperçu et histogramme calculés par le moteur sur une COPIE du document ─────────────────────
# Liste STRICTE de ce qu'un aperçu peut jouer : ce qui transforme les pixels ou l'apparence d'un calque, rien qui crée,
# supprime, sélectionne, ouvre ou touche au presse-papiers de styles (la copie disparaît à la fin : un geste structurel
# n'y aurait rien à montrer, et copy/pasteLayerStyle laisseraient un état hors du document).
# Filtres : tous sauf ceux qui ne sont pas un calcul de pixels paramétré (conversion en objet dynamique, « dernier
# filtre » qui rejoue un état caché) et les plein-écran D9 (Camera Raw, Liquify, Point de fuite, Grand-angle
# adaptatif). t157 : la galerie a désormais sa liste blanche par effet (photolab_registre._galerie) et son aperçu.
# Point de fuite exclu, plus aucune étape ne porte d'id de calque IMBRIQUÉ (`paste[].layer`) : seul `layer` du
# premier niveau est traduit vers la copie, c'est voulu.
FILTRES_HORS_APERCU = frozenset({"filter.convertForSmartFilters", "filter.lastFilter",
                                 "filter.cameraRaw", "filter.liquify", "filter.vanishingPoint",
                                 "filter.adaptiveWideAngle"})
REGLAGES_HORS_APERCU = frozenset({"image.adjustments.colorLookup.list"})   # une liste, pas un réglage
STYLES_APERCU = frozenset(f"layer.layerStyle.{k}" for k in (
    "dropShadow", "innerShadow", "outerGlow", "innerGlow", "stroke", "colorOverlay", "gradientOverlay",
    "patternOverlay", "bevelEmboss", "satin", "blendingOptions", "clear"))
COMMANDES_APERCU = frozenset({"layer.setAdjustment", "layer.setProps", "edit.transform",      # t154 : transformation manuelle
                              # t157 : réédition d'un filtre dynamique et ses options (aperçu exact, sans empiler un filtre)
                              "layer.smartFilter.setParams", "layer.smartFilter.setVisible",
                              "layer.smartFilter.blendingOptions", "layer.smartFilter.disableSmartFilters"})
MAX_ETAPES_APERCU = 12
GARDES_APV = 3
_APV = re.compile(r"apv-\d+-\d+\.png")
_COMPTEUR_APV = itertools.count(1)


def _admise_en_apercu(cid) -> bool:
    if not isinstance(cid, str):
        return False
    if cid in COMMANDES_APERCU or cid in STYLES_APERCU:
        return True
    if cid.startswith("filter."):
        return cid not in FILTRES_HORS_APERCU
    if cid.startswith("image.adjustments."):
        return cid not in REGLAGES_HORS_APERCU
    return False


def forme_etapes(etapes) -> list:
    """FORME des étapes (liste de 1 à 12 objets, `command` lisible et admise en aperçu, `params` objet) — sans le
    registre : une demande mal formée ne réveille pas le moteur pour lire `engine.commands`. ValueError -> 400."""
    if not isinstance(etapes, list) or not 1 <= len(etapes) <= MAX_ETAPES_APERCU:
        raise ValueError(f"aperçu : de 1 à {MAX_ETAPES_APERCU} étapes attendues")
    propres = []
    for e in etapes:
        if not isinstance(e, dict):
            raise ValueError("aperçu : chaque étape est un objet {command, params}")
        cid, params = e.get("command"), e.get("params")
        params = {} if params is None else params
        if not isinstance(cid, str) or not _ID_COMMANDE.fullmatch(cid):
            raise ValueError(f"commande illisible : {cid!r}")
        if not _admise_en_apercu(cid):
            raise ValueError(f"aperçu impossible pour cette commande : {cid}")
        if not isinstance(params, dict):
            raise ValueError(f"{cid} : les paramètres sont un objet")
        propres.append({"command": cid, "params": dict(params)})
    return propres


def etapes_apercu(propres, reg) -> list:
    """Liste blanche sur des étapes déjà mises en forme (`forme_etapes`), avant tout appel qui modifie quoi que ce
    soit. `layer.setAdjustment` attend la séquence : ses clés dépendent du kind du calque visé (`_verifier_reglage`)."""
    for e in propres:
        if e["command"] != "layer.setAdjustment":
            commande_autorisee(e["command"], e["params"], reg)
    return propres


def _verifier_reglage(etape, insp, reg):
    """layer.setAdjustment : cible FIGÉE (`layer` explicite ou calque actif de l'original, comme /executer) puis
    liste blanche avec le kind lu dans l'inspect de l'ORIGINAL — jamais déclaré par l'écran."""
    p = etape["params"]
    cible = p.get("layer", insp.get("activeLayer"))
    calque = next((c for c in _a_plat(insp.get("layers")) if c.get("id") == cible), None)
    if calque is None:
        raise ValueError(f"layer.setAdjustment : calque introuvable : {cible!r}")
    kind = PR.kind_de(calque)
    if kind is None:
        raise ValueError(f"layer.setAdjustment : le calque {cible} n'est pas un calque de réglage")
    etape["params"] = {**p, "layer": cible}
    commande_autorisee("layer.setAdjustment", etape["params"], reg, kind, calque.get("adjustment"))


def _sur_copie(appel, insp, actif, n_avant, nom, travail):
    """Duplique le document actif (`image.duplicate`, la copie devient active et GARDE la sélection — sonde s20),
    repose sur la copie le calque actif de l'original (la copie active son calque du haut), puis `travail(cible)`
    où `cible` = {id original: id copie}. Les ids sont renumérotés par la copie : on les apparie PAR POSITION dans
    l'arbre `layers` aplati en préordre (comme `vignettes`).
    Le `finally` referme la copie et resélectionne l'original MÊME si une étape a échoué au moteur. `doc.close`
    prend `index` : la clé `document` est ignorée en silence et fermerait le document ACTIF (relevé t138)."""
    copie, reussi = None, False
    try:
        res = appel("engine.execute", {"command": "image.duplicate", "params": {"name": nom}})
        apres = appel("session.list") or {}
        if len(apres.get("documents") or []) == n_avant + 1 and isinstance(apres.get("active"), int):
            copie = apres["active"]
        idx = res.get("document") if isinstance(res, dict) else None
        if not isinstance(idx, int) or isinstance(idx, bool):
            raise MoteurErreur(f"{nom} : image.duplicate n'a pas rendu l'index du document copié")
        if copie is None:
            copie = idx
        plats = [c["id"] for c in _a_plat((appel("doc.inspect") or {}).get("layers"))]
        ids_origine = [c["id"] for c in _a_plat(insp.get("layers"))]
        if len(plats) != len(ids_origine):
            raise MoteurErreur(f"{nom} : la copie du document n'a pas la même structure de calques")
        cible = dict(zip(ids_origine, plats))
        a = insp.get("activeLayer")
        if a in cible:
            appel("engine.execute", {"command": "layer.select", "params": {"layer": cible[a], "mode": "replace"}})
        sortie = travail(cible)
        reussi = True
        return sortie
    finally:
        # même règle que `vignettes` : un nettoyage raté n'écrase pas l'erreur d'origine, mais il est dit s'il suit
        # une réussite (le document de l'utilisateur ne serait pas dans l'état annoncé)
        try:
            if copie is not None:
                appel("doc.close", {"index": copie})
                appel("doc.select", {"index": actif})
        except (MoteurErreur, MoteurDelai):
            if reussi:
                raise


def _ouvrir_original(appel):
    """(index de l'original, nombre de documents, doc.inspect de l'original) au début d'une séquence sur copie."""
    sl = appel("session.list") or {}
    actif = sl.get("active")
    if not isinstance(actif, int) or isinstance(actif, bool):
        raise MoteurErreur("aucun document ouvert")
    return actif, len(sl.get("documents") or []), appel("doc.inspect") or {}


def _traduire(cible, lid):
    if lid not in cible:
        raise ValueError(f"calque inconnu du document : {lid!r}")
    return cible[lid]


def apercu(s: SessionMoteur, etapes, max_side: int):
    """({"fichier": apv-<gen>-<n>.png sous rendus/, "resultats": [result de chaque étape]}, génération) — les
    étapes jouées sur une COPIE, rendue puis refermée : l'original garde révision, calque actif, sélection,
    historique et pile de rétablissement (appliquer puis annuler laisserait l'étape dans la pile : écarté, s20).
    Rendu identique à l'octet à l'application réelle (banc test_photolab_apercu [2]).
    Toutes les étapes passent la liste blanche AVANT le moindre appel ; `layer.setAdjustment` (kind lu dans
    l'original) et les ids de calque (inconnus -> 400) sont vérifiés dans la séquence, avant la copie."""
    propres = forme_etapes(etapes)                         # la forme d'abord : un refus ne lit pas le registre
    reg = registre(s)                                      # hors séquence : registre() prend le verrou lui-même
    etapes_apercu(propres, reg)
    n = next(_COMPTEUR_APV)

    def fn(appel, gen):
        actif, n_avant, insp = _ouvrir_original(appel)
        connus = {c.get("id") for c in _a_plat(insp.get("layers"))}
        for e in propres:
            if e["command"] == "layer.setAdjustment":
                _verifier_reglage(e, insp, reg)
            elif e["command"] == "layer.smartFilter.setParams":
                verifier_filtre_dynamique(reg, e["params"], insp)
            if "layer" in e["params"] and e["params"]["layer"] not in connus:
                raise ValueError(f"{e['command']} : calque inconnu du document : {e['params']['layer']!r}")
        fichier = f"apv-{gen}-{n}.png"

        def travail(cible):
            resultats = []
            for e in propres:
                p = dict(e["params"])
                if "layer" in p:                           # sinon un style viserait le calque d'un autre rang
                    p["layer"] = _traduire(cible, p["layer"])
                resultats.append(appel("engine.execute", {"command": e["command"], "params": p}))
            appel("doc.render", {"path": relatif(f"rendus/{fichier}"), "maxSide": max_side})
            return {"fichier": fichier, "resultats": resultats}
        return _sur_copie(appel, insp, actif, n_avant, "dz-apercu", travail)
    sortie, gen = s.sequence(fn)
    _ranger_apv(dossier_travail() / "rendus")
    return sortie, gen


def _ranger_apv(d: Path):
    """Ne garde que les GARDES_APV derniers aperçus : l'écran n'affiche que le dernier, un glisser en produit des
    dizaines. Deux aperçus rangent en même temps (hors verrou du moteur) : un fichier peut disparaître entre la liste
    et le stat ou l'unlink — toléré, jamais un 500 après un aperçu réussi."""
    def date(f):
        try:
            return (f.stat().st_mtime_ns, f.name)
        except OSError:
            return None                                    # déjà supprimé par l'autre rangement
    try:
        dates = [(k, f) for f in d.iterdir() if _APV.fullmatch(f.name) and (k := date(f)) is not None]
    except OSError:
        return
    for _, f in sorted(dates)[:-GARDES_APV]:
        try:
            f.unlink()
        except OSError:
            pass                                          # ouvert par un lecteur, ou déjà parti : le prochain le reprendra


def histogramme(s: SessionMoteur, sans, max_side: int):
    """({"r","g","b","l": 256 comptes chacun}, génération) — le moteur n'a aucune commande d'histogramme par canal :
    on rend une COPIE (avec le calque `sans` de l'original masqué, ex. le réglage en cours d'édition) et Pillow
    compte ; les pixels d'alpha nul ne comptent pas (rien n'y est peint). Voir `_compter` pour l.
    Le rendu temporaire est supprimé dans un `finally` EXTÉRIEUR à la séquence : même si la fermeture de la copie
    échoue après le rendu, aucun hst-* ne reste dans rendus/."""
    if sans is not None and (not isinstance(sans, int) or isinstance(sans, bool)):
        raise ValueError(f"sans : id de calque entier attendu : {sans!r}")
    n = next(_COMPTEUR_APV)
    chemins = []                                           # rempli dans la séquence, nettoyé hors d'elle quoi qu'il arrive

    def fn(appel, gen):
        actif, n_avant, insp = _ouvrir_original(appel)
        if sans is not None and sans not in {c.get("id") for c in _a_plat(insp.get("layers"))}:
            raise ValueError(f"sans : calque inconnu du document : {sans!r}")
        fichier = f"hst-{gen}-{n}.png"
        chemins.append(dossier_travail() / "rendus" / fichier)

        def travail(cible):
            if sans is not None:
                appel("engine.execute", {"command": "layer.setProps",
                                         "params": {"layer": _traduire(cible, sans), "visible": False}})
            appel("doc.render", {"path": relatif(f"rendus/{fichier}"), "maxSide": max_side})
            return fichier
        return _sur_copie(appel, insp, actif, n_avant, "dz-histogramme", travail)
    try:
        _, gen = s.sequence(fn)
        return _compter(chemins[0]), gen
    finally:
        for chemin in chemins:
            try:
                chemin.unlink()                            # temporaire : seul le compte sort d'ici
            except OSError:
                pass                                       # jamais rendu (échec avant doc.render) : rien à retirer


def _compter(chemin: Path) -> dict:
    """Histogrammes de Pillow sous le masque alpha > 0 (14 ms au pire cas 1024×1024 toutes couleurs distinctes,
    contre 1,6 s par getcolors + formule en Python, mesuré t138). l = convert("L") de Pillow, ITU-R 601 en entiers
    ((R·19595 + G·38470 + B·7471 + 2^15) >> 16) : il diffère de round(0.299 R + 0.587 G + 0.114 B) du plan sur 9 443
    couleurs des 16 777 216 (0,06 %), d'un niveau au plus — invisible sur un histogramme de 256 cases."""
    from PIL import Image
    with Image.open(chemin) as im:
        rgba = im.convert("RGBA")
    masque = rgba.getchannel("A").point(lambda v: 255 if v else 0)
    rgb = rgba.convert("RGB")
    t = rgb.histogram(mask=masque)
    return {"r": t[0:256], "g": t[256:512], "b": t[512:768], "l": rgb.convert("L").histogram(mask=masque)}


def etat_session() -> dict:
    """Génération et vie de la session courante, sans la créer (les routes ne touchent pas à l'état privé)."""
    with _VERROU_SESSION:
        s = _SESSION
    return {"generation": s.generation if s else 0, "vivant": bool(s and s.vivant())}


# ── t153 : vignettes des motifs et contenu des couches alpha (aucune commande du moteur ne les rend) ────────────────
_ID_MOTIF = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_CACHE_MOTIFS: dict = {}                                   # (génération, id) -> octets PNG
_VERROU_CACHE_MOTIFS = threading.Lock()
_COTE_MOTIF = 64


def vignette_motif(s: "SessionMoteur", ident: str):
    """(octets PNG 64×64 du motif `ident` répété, génération) — voir `vignette_preset`."""
    if not isinstance(ident, str) or not _ID_MOTIF.fullmatch(ident):
        raise ValueError(f"motif : identifiant mal formé : {ident!r}")
    return vignette_preset(s, "motif", ident)


# t156 : formes personnalisées et styles de calque, rendus comme les motifs. Le nom d'un préréglage du moteur n'est
# qu'une clé de liste : il est refusé s'il ressemble à un fichier, s'il porte un caractère de contrôle ou dépasse 120.
_GENRES_VIGNETTE = ("motif", "forme", "style")


def _nom_preset(v, quoi):
    if v is None and quoi == "groupe":
        return None
    if not isinstance(v, str) or not 1 <= len(v) <= 120 or any(ord(c) < 32 for c in v) or _valeur_fichier(v):
        raise ValueError(f"{quoi} de préréglage refusé : {v!r}")
    return v


def vignette_preset(s: "SessionMoteur", genre: str, cle: str, groupe=None):
    """(octets PNG 64×64, génération) d'un préréglage : motif (id), forme personnalisée ou style de calque (nom, groupe).
    Le moteur ne rend aucun préréglage : un document temporaire (doc.new transparent, puis calque de motif, forme placée
    ou carré uni stylé, doc.render) refermé dans un `finally`, l'original resélectionné ; le document de l'utilisateur
    n'est jamais touché (ni historique ni révision). Cache par (génération, genre, clé, groupe) : renommer change la clé,
    le contenu d'une clé ne change pas sans nouvelle génération."""
    if genre not in _GENRES_VIGNETTE:
        raise ValueError(f"genre de préréglage inconnu : {genre!r}")
    if genre == "motif":
        if not isinstance(cle, str) or not _ID_MOTIF.fullmatch(cle):
            raise ValueError(f"motif : identifiant mal formé : {cle!r}")
        groupe = None
    else:
        cle, groupe = _nom_preset(cle, "nom"), _nom_preset(groupe, "groupe")
    n = next(_COMPTEUR_APV)
    fichier = dossier_travail() / "rendus" / f"mtf-{n}.png"
    c = _COTE_MOTIF
    if genre == "motif":
        etapes = [("layer.newFillLayer.pattern", {"pattern": cle})]
    elif genre == "forme":
        etapes = [("shape.presets.place", {"preset": cle, **({"group": groupe} if groupe else {}), "rect": [4, 4, c - 8, c - 8],
                                           "fill": "#c8c8c8"})]
    else:
        etapes = [("shape.create", {"kind": "rect", "rect": [12, 12, c - 24, c - 24], "fill": "#9aa0a6"}),
                  ("style.presets.apply", {"preset": cle, **({"group": groupe} if groupe else {})})]
    cache = (genre, cle, groupe)

    def fn(appel, gen):
        with _VERROU_CACHE_MOTIFS:
            if (gen, cache) in _CACHE_MOTIFS:
                return _CACHE_MOTIFS[(gen, cache)]
        sl = appel("session.list") or {}
        actif, n_avant = sl.get("active"), len(sl.get("documents") or [])
        temp, reussi = None, False
        try:
            appel("doc.new", {"width": c, "height": c, "background": "transparent", "name": "dz-" + genre})
            apres = appel("session.list") or {}
            if len(apres.get("documents") or []) == n_avant + 1 and isinstance(apres.get("active"), int):
                temp = apres["active"]
            if temp is None:
                raise MoteurErreur(f"{genre} : le document temporaire n'a pas été créé")
            for cid, params in etapes:
                appel("engine.execute", {"command": cid, "params": params})
            appel("doc.render", {"path": relatif(f"rendus/{fichier.name}"), "maxSide": c})
            octets = fichier.read_bytes()
            reussi = True
        finally:
            try:
                if temp is not None:
                    appel("doc.close", {"index": temp})
                    if isinstance(actif, int) and not isinstance(actif, bool):
                        appel("doc.select", {"index": actif})
            except (MoteurErreur, MoteurDelai):
                if reussi:
                    raise
            try:
                fichier.unlink()
            except OSError:
                pass
        with _VERROU_CACHE_MOTIFS:
            if len(_CACHE_MOTIFS) > 256:
                _CACHE_MOTIFS.clear()
            _CACHE_MOTIFS[(gen, cache)] = octets
        return octets
    return s.sequence(fn)


def couches_alpha(s: "SessionMoteur", max_side: int, index=None):
    """([{"index", "png": data-URL en niveaux de gris}], génération) — le contenu des couches alpha du document actif
    (blanc = sélectionné). doc.render ne rend que le composite : sur une COPIE (_sur_copie), pour chaque alpha, un
    calque uni noir couvre tout, un calque uni blanc le couvre, la couche est chargée comme sélection et devient le
    masque du calque blanc (layerMask.revealSelection ; un calque uni créé sur une sélection N'EST PAS masqué), rendu. L'original n'est pas touché ; les rendus temporaires sont effacés. `index` : une seule couche."""
    import base64
    import io
    from PIL import Image
    if index is not None and (not isinstance(index, int) or isinstance(index, bool) or index < 0):
        raise ValueError(f"index : entier positif attendu : {index!r}")
    n = next(_COMPTEUR_APV)
    chemins = []

    def fn(appel, gen):
        actif, n_avant, insp = _ouvrir_original(appel)
        alphas = [a.get("index") for a in ((insp.get("channels") or {}).get("alpha") or []) if isinstance(a, dict)]
        if index is not None:
            if index not in alphas:
                raise ValueError(f"index : couche alpha inconnue : {index}")
            alphas = [index]
        if not alphas:
            return []

        def travail(_cible):
            sorties = []
            for i in alphas:
                f = f"cha-{gen}-{n}-{i}.png"
                chemins.append(dossier_travail() / "rendus" / f)
                ex = lambda c, p=None: appel("engine.execute", {"command": c, "params": p or {}})
                if (appel("doc.inspect") or {}).get("hasSelection"):
                    ex("select.deselect")                  # refusé sans sélection (« no selection »)
                ex("layer.newFillLayer.solidColor", {"color": "#000000"})
                ex("layer.newFillLayer.solidColor", {"color": "#ffffff"})
                ex("select.loadSelection", {"channel": i, "operation": "new"})
                ex("layer.layerMask.revealSelection")      # le calque blanc ne garde que la sélection
                appel("doc.render", {"path": relatif(f"rendus/{f}"), "maxSide": max_side})
                sorties.append((i, f))
            return sorties
        return _sur_copie(appel, insp, actif, n_avant, "dz-couches", travail)
    try:
        sorties, gen = s.sequence(fn)
        out = []
        for i, f in sorties:
            with Image.open(dossier_travail() / "rendus" / f) as im:
                gris = im.convert("L")
            tampon = io.BytesIO()
            gris.save(tampon, format="PNG")
            out.append({"index": i, "png": "data:image/png;base64," + base64.b64encode(tampon.getvalue()).decode()})
        return out, gen
    finally:
        for chemin in chemins:
            try:
                chemin.unlink()
            except OSError:
                pass


# ── t157 (Photolab parité L7) : masques, filtres dynamiques, Sélectionner et masquer, Galerie de filtres ───────────────

def verifier_filtre_dynamique(reg, params, insp):
    """layer.smartFilter.setParams : `params.params` passe la liste blanche de la commande du filtre VISÉ, lue dans
    doc.inspect (`smartFilters[index].command`, index absent = filtre du haut) — jamais déclarée par l'écran. Le moteur
    fusionne ces clés dans le filtre : une clé d'un autre filtre ou une valeur hors bornes y serait gardée en silence.
    ValueError -> 400."""
    if not isinstance(params, dict):
        raise ValueError("layer.smartFilter.setParams : les paramètres sont un objet")
    cible = params.get("layer", insp.get("activeLayer"))
    calque = next((c for c in _a_plat(insp.get("layers")) if c.get("id") == cible), None)
    if calque is None:
        raise ValueError(f"layer.smartFilter.setParams : calque introuvable : {cible!r}")
    filtres = calque.get("smartFilters") or []
    if not filtres:
        raise ValueError(f"layer.smartFilter.setParams : le calque {cible} n'a pas de filtre dynamique")
    i = params.get("index", len(filtres) - 1)
    if not PR._entier(i) or not 0 <= i < len(filtres):
        raise ValueError(f"layer.smartFilter.setParams : index hors de la pile (0..{len(filtres) - 1}) : {i!r}")
    p = params.get("params", {})
    if not isinstance(p, dict):
        raise ValueError("layer.smartFilter.setParams : params : objet attendu")
    commande = filtres[i].get("command")
    if not isinstance(commande, str):
        raise ValueError("layer.smartFilter.setParams : filtre sans commande (conservé, non modifiable)")
    commande_autorisee(commande, p, reg)


def _ex(appel, c, p=None):
    return appel("engine.execute", {"command": c, "params": p or {}})


def _au_sommet(appel):
    """Rend actif le calque du HAUT de la racine : un calque créé ensuite (remplissage uni) couvre tout le document."""
    racines = (appel("doc.inspect") or {}).get("layers") or []
    if racines:
        _ex(appel, "layer.select", {"layer": racines[0]["id"], "mode": "replace"})


def _remplissage(appel, couleur):
    """Un calque de remplissage uni au-dessus du calque actif -> son id (le calque actif après création)."""
    _ex(appel, "layer.newFillLayer.solidColor", {"color": couleur})
    return (appel("doc.inspect") or {}).get("activeLayer")


def _masquer_par_selection(appel, calque, montrer=True):
    """Masque de `calque` = la sélection courante (montrer) ou son inverse ; une sélection vide (tout noir) n'est pas
    une sélection pour le moteur : tout masquer (ou tout révéler) à la place."""
    sel = (appel("doc.inspect") or {}).get("hasSelection")
    if sel:
        _ex(appel, "layer.layerMask." + ("revealSelection" if montrer else "hideSelection"), {"layer": calque})
    else:
        _ex(appel, "layer.layerMask." + ("hideAll" if montrer else "revealAll"), {"layer": calque})


MAX_MASQUES = 64


def masques(s: "SessionMoteur", max_side: int, calque=None):
    """([{"layer", "png": data-URL en niveaux de gris}], génération) — le masque de fusion de chaque calque masqué du
    document actif (blanc = révélé). doc.render ne rend que le composite (view.layerMask n'y change rien, relevé t157) :
    sur une COPIE (_sur_copie), un calque uni noir puis un blanc au sommet, le masque chargé comme sélection devient le
    masque du blanc, rendu, puis les deux calques retirés. L'original n'est pas touché ; les rendus temporaires sont
    effacés. `calque` : un seul calque (Alt-clic : le masque montré sur la toile)."""
    import base64
    import io
    from PIL import Image
    if calque is not None and (not PR._entier(calque) or calque < 0):
        raise ValueError(f"layer : entier positif attendu : {calque!r}")
    n = next(_COMPTEUR_APV)
    chemins = []

    def fn(appel, gen):
        actif, n_avant, insp = _ouvrir_original(appel)
        cibles = [c["id"] for c in _a_plat(insp.get("layers")) if c.get("hasMask")]
        if calque is not None:
            if calque not in cibles:
                raise ValueError(f"le calque {calque} n'a pas de masque de fusion")
            cibles = [calque]
        cibles = cibles[:MAX_MASQUES]
        if not cibles:
            return []

        def travail(cible):
            sorties = []
            for lid in cibles:
                f = f"msk-{gen}-{n}-{lid}.png"
                chemins.append(dossier_travail() / "rendus" / f)
                if (appel("doc.inspect") or {}).get("hasSelection"):
                    _ex(appel, "select.deselect")             # refusé sans sélection (« no selection »)
                _au_sommet(appel)
                noir = _remplissage(appel, "#000000")
                blanc = _remplissage(appel, "#ffffff")
                _ex(appel, "select.loadSelection", {"channel": "mask", "layer": cible[lid], "operation": "new"})
                _masquer_par_selection(appel, blanc)
                appel("doc.render", {"path": relatif(f"rendus/{f}"), "maxSide": max_side})
                _ex(appel, "layer.delete", {"layer": blanc})
                _ex(appel, "layer.delete", {"layer": noir})
                sorties.append((lid, f))
            return sorties
        return _sur_copie(appel, insp, actif, n_avant, "dz-masques", travail)
    try:
        sorties, gen = s.sequence(fn)
        out = []
        for lid, f in sorties:
            with Image.open(dossier_travail() / "rendus" / f) as im:
                gris = im.convert("L")
            tampon = io.BytesIO()
            gris.save(tampon, format="PNG")
            out.append({"layer": lid, "png": "data:image/png;base64," + base64.b64encode(tampon.getvalue()).decode()})
        return out, gen
    finally:
        for chemin in chemins:
            try:
                chemin.unlink()
            except OSError:
                pass


# Les 7 vues de « Sélectionner et masquer » (référence : Pelure d'oignon, Cadre de sélection actif, Incrustation, Sur
# noir, Sur blanc, Noir et blanc, Sur calques) et les réglages que l'écran envoie. La SORTIE n'est jamais choisie par
# l'écran pour un aperçu : chaque vue impose la sienne (OK passe par /executer avec la sortie de l'utilisateur).
VUES_MASQUER = ("oignon", "fourmis", "incrustation", "noir", "blanc", "nb", "calques")
CLES_MASQUER = frozenset({"radius", "smartRadius", "smooth", "feather", "contrast", "shiftEdge", "decontaminate", "amount",
                          "sampleAllLayers"})


def _cacher_sauf(appel, gardes):
    """Cache tout ce qui n'est pas un calque de `gardes` ni un de leurs parents (les frères des parents aussi)."""
    def voir(liste):
        garde_ici = False
        for c in liste or []:
            enfants = c.get("children") if isinstance(c.get("children"), list) else None
            dedans = c.get("id") in gardes or (enfants is not None and voir(enfants))
            if not dedans and c.get("visible", True):
                _ex(appel, "layer.setProps", {"layer": c["id"], "visible": False})
            garde_ici = garde_ici or dedans
        return garde_ici
    voir((appel("doc.inspect") or {}).get("layers"))


def apercu_masque(s: "SessionMoteur", reglages, vue, transparence, inverser, max_side: int):
    """({"fichier": apv-….png sous rendus/, "bounds"?}, génération) — l'aperçu d'une vue de « Sélectionner et masquer » :
    select.refineEdge joué sur une COPIE (l'original garde sélection, révision, historique), puis la vue composée avec
    des commandes du moteur (calques unis, masques, visibilités), rendue, la copie refermée. `transparence` 0..100 :
    rouge de l'incrustation, calque d'origine sous la pelure d'oignon. ValueError -> 400 (dont « aucune sélection »)."""
    if vue not in VUES_MASQUER:
        raise ValueError(f"vue inconnue : {vue!r} ({', '.join(VUES_MASQUER)})")
    if not PR._nombre_fini(transparence) or not 0 <= transparence <= 100:
        raise ValueError(f"transparence : nombre 0..100 attendu : {transparence!r}")
    if not isinstance(inverser, bool):
        raise ValueError("inverser : booléen attendu")
    if not isinstance(reglages, dict):
        raise ValueError("reglages : objet attendu")
    inconnues = set(reglages) - CLES_MASQUER
    if inconnues:
        raise ValueError(f"select.refineEdge : réglage refusé en aperçu : {', '.join(sorted(map(str, inconnues)))}")
    reg = registre(s)
    commande_autorisee("select.refineEdge", reglages, reg)
    n = next(_COMPTEUR_APV)
    opacite = round(1 - transparence / 100, 4)

    def fn(appel, gen):
        actif, n_avant, insp = _ouvrir_original(appel)
        if not insp.get("hasSelection"):
            raise ValueError("Sélectionner et masquer : aucune sélection (le moteur en exige une)")
        fichier = f"apv-{gen}-{n}.png"

        def travail(cible):
            sortie = {"fichier": fichier}
            if inverser:
                _ex(appel, "select.inverse")
            r = dict(reglages)
            if vue in ("nb", "fourmis", "incrustation"):
                r.update(decontaminate=False, output="selection")      # décontaminer forcerait un nouveau calque
                _ex(appel, "select.refineEdge", r)
                if vue == "fourmis":
                    sortie["bounds"] = (appel("doc.inspect") or {}).get("selectionBounds")
                elif vue == "nb":
                    _au_sommet(appel)
                    _remplissage(appel, "#000000")
                    _masquer_par_selection(appel, _remplissage(appel, "#ffffff"))
                else:
                    _au_sommet(appel)
                    rouge = _remplissage(appel, "#ff0000")
                    _masquer_par_selection(appel, rouge, montrer=False)
                    _ex(appel, "layer.setProps", {"layer": rouge, "opacity": opacite})
            else:
                r["output"] = "newLayerWithMask"
                res = _ex(appel, "select.refineEdge", r)
                copie = res.get("layer") if isinstance(res, dict) else None
                if copie is None:
                    copie = (appel("doc.inspect") or {}).get("activeLayer")
                source = cible.get(insp.get("activeLayer"))
                if vue in ("noir", "blanc"):
                    _cacher_sauf(appel, {copie})
                    fond = _remplissage(appel, "#000000" if vue == "noir" else "#ffffff")
                    _ex(appel, "layer.moveTo", {"layer": fond, "target": copie, "position": "below"})
                elif vue == "oignon":
                    _cacher_sauf(appel, {copie, source})
                    if source is not None:
                        _ex(appel, "layer.setProps", {"layer": source, "visible": True, "opacity": opacite})
            appel("doc.render", {"path": relatif(f"rendus/{fichier}"), "maxSide": max_side})
            return sortie
        return _sur_copie(appel, insp, actif, n_avant, "dz-masquer", travail)
    sortie, gen = s.sequence(fn)
    _ranger_apv(dossier_travail() / "rendus")
    return sortie, gen


_CACHE_GALERIE = {"catalogue": None, "vignettes": {}}
MAX_VIGNETTES_GALERIE = 16
TAILLE_VIGNETTE_GALERIE = (80, 56)


def catalogue_galerie(s: "SessionMoteur"):
    """({"categories", "filters": [{category, command, key, name, params}]}, génération) — filter.filterGallery
    {list:true}, gardé par génération (le catalogue ne dépend pas du document)."""
    def fn(appel, gen):
        c = _CACHE_GALERIE["catalogue"]
        if c and c[0] == gen:
            return c[1]
        r = _ex(appel, "filter.filterGallery", {"list": True})
        _CACHE_GALERIE["catalogue"] = (gen, r)
        return r
    return s.sequence(fn)


def vignettes_galerie(s: "SessionMoteur", cles):
    """({clé: data-URL PNG 80×56}, génération) — chaque filtre de la galerie, réglages par défaut, appliqué par le
    MOTEUR au centre du document (comme l'amont : un morceau du milieu, environ 4× la vignette). Sur une COPIE : image
    aplatie, recadrée au rapport 80:56, réduite à 160×112, puis pour chaque clé : filtre, rendu, annulation. Gardé par
    (génération, document, révision) ; seules les clés manquantes sont calculées."""
    import base64
    import io
    from PIL import Image
    if not isinstance(cles, list) or not 1 <= len(cles) <= MAX_VIGNETTES_GALERIE:
        raise ValueError(f"de 1 à {MAX_VIGNETTES_GALERIE} filtres attendus")
    reg = registre(s)
    connus = PR.cles_galerie(reg)
    for k in cles:
        if k not in connus:
            raise ValueError(f"filtre de la galerie inconnu : {k!r}")
    n = next(_COMPTEUR_APV)
    chemins = []

    def fn(appel, gen):
        actif, n_avant, insp = _ouvrir_original(appel)
        base = (gen, actif, insp.get("revision"))
        cache = _CACHE_GALERIE["vignettes"]
        if cache.get("base") != base:
            cache.clear()
            cache["base"] = base
        manquantes = [k for k in dict.fromkeys(cles) if k not in cache]
        if not manquantes:
            return {}
        w, h = int(insp.get("width") or 1), int(insp.get("height") or 1)
        lw, lh = TAILLE_VIGNETTE_GALERIE
        pw = min(w, 4 * lw)
        ph = round(pw * lh / lw)
        if ph > h:
            ph = h
            pw = max(1, round(ph * lw / lh))

        def travail(_cible):
            if (appel("doc.inspect") or {}).get("hasSelection"):
                _ex(appel, "select.deselect")
            if len((appel("doc.inspect") or {}).get("layers") or []) > 1:
                _ex(appel, "layer.flattenImage")
            _ex(appel, "image.crop", {"x": (w - pw) // 2, "y": (h - ph) // 2, "width": pw, "height": ph})
            _ex(appel, "image.imageSize", {"width": 2 * lw, "height": 2 * lh})
            faits = []
            for k in manquantes:
                f = f"gal-{gen}-{n}-{k}.png"
                chemins.append(dossier_travail() / "rendus" / f)
                _ex(appel, "filter.filterGallery", {"effects": [{"filter": k}]})
                appel("doc.render", {"path": relatif(f"rendus/{f}"), "maxSide": lw})
                _ex(appel, "edit.undo")
                faits.append((k, f))
            return faits
        return _sur_copie(appel, insp, actif, n_avant, "dz-galerie", travail)
    try:
        faits, gen = s.sequence(fn)
        cache = _CACHE_GALERIE["vignettes"]
        for k, f in faits:
            with Image.open(dossier_travail() / "rendus" / f) as im:
                im = im.convert("RGB")
                if im.size != TAILLE_VIGNETTE_GALERIE:
                    im = im.resize(TAILLE_VIGNETTE_GALERIE)
                tampon = io.BytesIO()
                im.save(tampon, format="PNG")
            cache[k] = "data:image/png;base64," + base64.b64encode(tampon.getvalue()).decode()
        return {k: cache[k] for k in dict.fromkeys(cles)}, gen
    finally:
        for chemin in chemins:
            try:
                chemin.unlink()
            except OSError:
                pass
