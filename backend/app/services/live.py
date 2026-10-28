# -*- coding: utf-8 -*-
"""t318 (28/10/2026) (lot D4) — le DIRECT multi-destinations (spec boîte à outils §8.6, choix de Claude 9 ; plan
docs/superpowers/plans/2026-10-28-t318-live.md).

Chaîne : la page encode la scène de la capture (MediaRecorder) et pousse ses morceaux par WebSocket local ; ici, UN
ffmpeg lit ce flux sur son entrée standard, l'encode UNE fois (H.264 + AAC, GOP de 2 s) et le distribue par le muxer
`tee` à chaque destination RTMP(S), chacune en `onfail=ignore` : une destination tombée ne coupe pas les autres.

- Destinations : les comptes `comptes.LIVE` de l'espace (twitch, youtube_live, kick, rtmp) ; la clé de stream vit au
  coffre (`DZC_<ID>_<CHAMP>`), lue au branchement seulement. L'URL complète (serveur + clé) ne sort JAMAIS d'ici : ni
  réponse, ni journal, ni fichier ; toute ligne d'erreur de ffmpeg passe par `masquer`.
- Discord : pas d'entrée vidéo publique ; un message d'annonce part par le webhook d'un compte `discord`, à
  « Passer en direct ». Le webhook est un secret (qui le tient poste dans le salon).
- Santé : `-progress` (images/s, images perdues, vitesse), débit d'entrée mesuré ici, « Slave muxer #i failed » → la
  destination i est en panne.
- Après : `terminer` écrit `captures/<id>/<id>.dzlive.json` (marqueurs, destinations, sans secret) à côté de la
  capture, pour en tirer des clips (t317).
Aucune dépense. Journaux : identifiants, nombres, plateformes."""
from __future__ import annotations

import atexit
import json
import os
import queue
import re
import secrets as _secrets
import subprocess
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote

from app.config import DATA_ROOT

SERVEURS = {"twitch": "rtmp://live.twitch.tv/app", "youtube_live": "rtmp://a.rtmp.youtube.com/live2"}
# plateforme -> (champ clé, champ serveur, champ lien public)
CHAMPS = {"twitch": ("TWITCH_STREAM_KEY", "TWITCH_SERVEUR", None),
          "youtube_live": ("YOUTUBE_STREAM_KEY", "YOUTUBE_LIVE_SERVEUR", "YOUTUBE_LIVE_LIEN"),
          "kick": ("KICK_STREAM_KEY", "KICK_SERVEUR", None),
          "rtmp": ("RTMP_CLE", "RTMP_SERVEUR", "RTMP_LIEN")}
LIENS_HANDLE = {"twitch": "https://www.twitch.tv/{h}", "kick": "https://kick.com/{h}"}
MASQUE = "••••"
MAX_DESTINATIONS = 6
MAX_MARQUEURS = 200
MAX_TITRE = 100
MAX_ANNONCE = 1500
FILE_MAX = 40                # morceaux de 250 ms en attente d'écriture (~10 s) : au-delà, le flux est déclaré engorgé
BLOCAGE_S = 10               # une écriture dans ffmpeg bloquée plus longtemps = destination figée : on coupe
PRET_MAX_S = 120             # une session ouverte mais jamais branchée (onglet fermé pendant le choix d'écran) expire
ID = re.compile(r"^[a-f0-9]{16}$")
_INTERDITS = re.compile(r"[|\[\]\\\"'\s\x00-\x1f\x7f]")
_RTMP_URL = re.compile(r"(rtmps?://[^\s'\"|]*/)([^/\s'\"|]+)")
_WEBHOOK = re.compile(r"^https://(?:discord|discordapp|ptb\.discord|canary\.discord)\.com/api/webhooks/\d{5,25}/[A-Za-z0-9_-]{20,100}$")
_WEBHOOK_PREUVE = re.compile(r"^http://127\.0\.0\.1:\d{2,5}/api/webhooks/\d{1,25}/[A-Za-z0-9_-]{4,100}$")
_HANDLE = re.compile(r"^[A-Za-z0-9_]{2,40}$")
_ESCLAVE = re.compile(r"Slave muxer #(\d+) failed")


class RefusLive(ValueError):
    """Une demande refusée : `statut` = le code HTTP (400, 404, 409). Levée avec un message littéral (L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


# ---- URL, masque ------------------------------------------------------------------------------------------------------

def valider_serveur(url) -> str:
    """Un serveur RTMP(S) sûr à mettre dans une sortie `tee` : schéma rtmp/rtmps, un hôte, aucun séparateur de `tee`
    (`|`, `[`, `]`, `\\`), ni guillemet, ni espace, ni caractère de contrôle."""
    u = url.strip() if isinstance(url, str) else ""
    if not u or len(u) > 1024 or _INTERDITS.search(u) or not re.match(r"^rtmps?://[A-Za-z0-9.-]+(:\d{1,5})?(/|$)", u):
        raise RefusLive("Serveur du direct invalide : une adresse rtmp:// ou rtmps:// sans espace ni | [ ] est attendue.", 400)
    return u.rstrip("/")


def _valider_cle(cle: str) -> str:
    c = (cle or "").strip()
    if len(c) > 512 or _INTERDITS.search(c) or "/" in c:
        raise RefusLive("Clé de stream invalide (espace, barre ou caractère interdit).", 400)
    return c


def masquer(texte, secrets_=()) -> str:
    """Retire de `texte` chaque secret (et sa forme %-codée), puis le dernier segment de toute adresse rtmp(s)://."""
    t = str(texte or "")
    for s in sorted({x for x in secrets_ if isinstance(x, str) and len(x) >= 3}, key=len, reverse=True):
        t = t.replace(s, MASQUE).replace(quote(s, safe=""), MASQUE)
    return _RTMP_URL.sub(lambda m: m.group(1) + MASQUE, t)


# ---- destinations -----------------------------------------------------------------------------------------------------

def _lien(vue: dict, publics: dict) -> str:
    p = vue["plateforme"]
    champ = CHAMPS[p][2]
    lien = str(publics.get(champ) or "").strip() if champ else ""
    if lien.startswith("https://") and not _INTERDITS.search(lien) and len(lien) <= 300:
        return lien
    h = str(vue.get("handle") or "").strip().lstrip("@")
    if p in LIENS_HANDLE and _HANDLE.match(h):
        return LIENS_HANDLE[p].format(h=h)
    return ""


def destinations(eid: str, ids) -> list:
    """Les destinations choisies, dans l'ordre : {id, plateforme, libelle, lien, url, cle}. `url` et `cle` sont
    SECRÈTES : seules `Diffusion` et `masquer` les voient."""
    from app.services import comptes
    if not isinstance(ids, list) or not ids:
        raise RefusLive("Choisis au moins une destination du direct.", 400)
    out, vus = [], set()
    for cid in ids:
        if not isinstance(cid, str) or cid in vus:
            continue
        try:
            vue = comptes.obtenir(cid)
        except KeyError:
            raise RefusLive("Destination du direct inconnue.", 404) from None
        if vue["plateforme"] not in CHAMPS:
            raise RefusLive("Ce compte n'est pas une destination du direct.", 400)
        if not comptes.de_l_espace(cid, eid):
            raise RefusLive("Cette destination appartient à un autre espace.", 409)
        champ_cle, champ_serveur, _l = CHAMPS[vue["plateforme"]]
        publics = {c["nom"]: c.get("valeur") for c in vue["champs"] if not c["secret"]}
        with comptes.sous_compte(cid):
            cle = _valider_cle(str(comptes.cle(champ_cle) or ""))
        if not cle and vue["plateforme"] != "rtmp":
            libelle = vue["libelle"]
            raise RefusLive(f"Clé de stream absente pour {libelle} : colle-la d'abord.", 400)
        serveur = valider_serveur(str(publics.get(champ_serveur) or "").strip() or SERVEURS.get(vue["plateforme"], ""))
        out.append({"id": cid, "plateforme": vue["plateforme"], "libelle": vue["libelle"], "lien": _lien(vue, publics),
                    "url": serveur + ("/" + cle if cle else ""), "cle": cle})
        vus.add(cid)
    if len(out) > MAX_DESTINATIONS:
        raise RefusLive("Six destinations au plus.", 400)
    return out


# ---- ffmpeg -----------------------------------------------------------------------------------------------------------

def ffmpeg_bin() -> str:
    return os.environ.get("DZ_FFMPEG") or "ffmpeg"


def commande(urls: list, fps: int = 30, video_kbps: int = 4500) -> list:
    """UN encodage (libx264 zerolatency, GOP 2 s, AAC 160k) distribué par `tee`, chaque sortie en onfail=ignore."""
    g = str(2 * fps)
    sorties = "|".join(f"[f=flv:onfail=ignore]{u}" for u in urls)
    return [ffmpeg_bin(), "-hide_banner", "-loglevel", "warning", "-nostats", "-progress", "pipe:1", "-stats_period", "1",
            # un direct n'attend pas 5 s d'analyse : l'en-tête WebM décrit déjà ses pistes
            "-fflags", "+genpts", "-probesize", "1000000", "-analyzeduration", "1000000", "-i", "pipe:0",
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-b:v", f"{video_kbps}k", "-maxrate", f"{video_kbps}k", "-bufsize", f"{2 * video_kbps}k",
            "-pix_fmt", "yuv420p", "-r", str(fps), "-g", g, "-keyint_min", g, "-sc_threshold", "0",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
            "-flags", "+global_header", "-f", "tee", sorties]


class Diffusion:
    """Un ffmpeg vivant : `ecrire(octets)`, `etat()`, `fermer()`. `lancer` = subprocess.Popen (remplaçable au banc)."""

    def __init__(self, urls: list, secrets_=(), fps: int = 30, lancer=subprocess.Popen):
        self.secrets = [s for s in secrets_ if s] + list(urls)
        self.n = len(urls)
        self.pannes = [False] * self.n
        self.progres: dict = {}
        self.erreurs: list = []
        self.octets = 0
        self.debut = time.monotonic()
        self._fenetre = []                     # (instant, octets) des 5 dernières secondes
        self._histo = []                       # (instant, images, temps de sortie en µs) des 6 dernières secondes
        self._verrou = threading.Lock()
        self.ferme = False
        self.engorge = False
        self._casse = False
        self._file = queue.Queue(maxsize=FILE_MAX)
        self._en_ecriture = None               # instant du début de l'écriture en cours (None : aucune)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = lancer(commande(urls, fps), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           creationflags=flags)
        threading.Thread(target=self._lire_progres, daemon=True).start()
        threading.Thread(target=self._lire_erreurs, daemon=True).start()
        threading.Thread(target=self._ecrivain, daemon=True).start()

    def _ecrivain(self):
        """Le SEUL fil qui écrit dans ffmpeg (revue finale C1) : une destination figée bloque ce fil-ci, jamais la boucle
        du WebSocket ni fermer(), qui tue ffmpeg au bout du délai (le write bloqué lève alors et le fil se termine)."""
        while True:
            b = self._file.get()
            if b is None:
                break
            self._en_ecriture = time.monotonic()
            try:
                self.proc.stdin.write(b)
                self.proc.stdin.flush()
            except (OSError, ValueError):
                self._casse = True
                break
            finally:
                self._en_ecriture = None
        try:
            self.proc.stdin.close()
        except (OSError, ValueError):
            pass

    def _lire_progres(self):
        bloc = {}
        for ligne in iter(self.proc.stdout.readline, b""):
            k, _, v = ligne.decode("utf-8", "replace").strip().partition("=")
            if not k:
                continue
            bloc[k] = v
            if k == "progress":
                maintenant = time.monotonic()
                with self._verrou:
                    self.progres = dict(bloc)
                    try:          # la santé se lit sur les 6 dernières secondes, pas en moyenne depuis le départ
                        self._histo = [x for x in self._histo if maintenant - x[0] <= 6] + [
                            (maintenant, int(bloc.get("frame") or 0), int(bloc.get("out_time_us") or 0))]
                    except ValueError:
                        pass
                bloc = {}

    def _lire_erreurs(self):
        for ligne in iter(self.proc.stderr.readline, b""):
            t = masquer(ligne.decode("utf-8", "replace").strip(), self.secrets)
            if not t:
                continue
            m = _ESCLAVE.search(t)
            with self._verrou:
                if m and int(m.group(1)) < self.n:
                    self.pannes[int(m.group(1))] = True
                self.erreurs = (self.erreurs + [t[:300]])[-8:]

    def vivant(self) -> bool:
        return self.proc.poll() is None

    def bloque(self) -> bool:
        e = self._en_ecriture
        return e is not None and time.monotonic() - e > BLOCAGE_S

    def ecrire(self, octets: bytes) -> bool:
        """Met un morceau dans la file d'écriture ; False = le direct ne peut plus suivre (fermé, ffmpeg mort, écriture
        bloquée, file pleine) : l'appelant coupe proprement plutôt que d'amputer le flux WebM."""
        if self.ferme or self._casse or not self.vivant() or self.bloque():
            return False
        try:
            self._file.put_nowait(octets)
        except queue.Full:
            self.engorge = True
            return False
        maintenant = time.monotonic()
        with self._verrou:
            self.octets += len(octets)
            self._fenetre = [x for x in self._fenetre if maintenant - x[0] <= 5] + [(maintenant, len(octets))]
        return True

    def etat(self) -> dict:
        with self._verrou:
            p, fen, pannes, err = dict(self.progres), list(self._fenetre), list(self.pannes), list(self.erreurs)
            histo = list(self._histo)
        duree = max(1.0, min(5.0, time.monotonic() - self.debut))
        debit = round(sum(n for _t, n in fen) * 8 / 1000 / duree)
        vivant = self.vivant() and not self.ferme

        def nombre(k, f=float):
            try:
                return f(p.get(k))
            except (TypeError, ValueError):
                return None
        images = nombre("frame", int)
        etat = "arrete" if not vivant else ("en_direct" if images else "demarrage")
        if vivant and ((pannes and all(pannes)) or self.bloque() or self.engorge):
            etat = "en_panne"
        fps, vitesse = nombre("fps"), nombre("speed", lambda v: float(str(v).rstrip("x")))
        if len(histo) >= 2 and histo[-1][0] - histo[0][0] >= 2:      # fenêtre glissante : l'état d'ICI, pas la moyenne
            dt = histo[-1][0] - histo[0][0]
            fps = round((histo[-1][1] - histo[0][1]) / dt, 1)
            vitesse = round((histo[-1][2] - histo[0][2]) / 1e6 / dt, 2)
        return {"etat": etat, "images": images, "fps": fps, "images_perdues": nombre("drop_frames", int),
                "vitesse": vitesse, "debit_kbps": debit,
                "destinations": ["panne" if x else ("ok" if images else "attente") for x in pannes],
                "erreur": err[-1] if err else ""}

    def fermer(self, delai: float = 5.0) -> int | None:
        """Ne bloque jamais plus de `delai` + 3 s : la fin d'entrée passe par le fil écrivain ; ffmpeg qui ne s'arrête pas
        (destination figée, écriture bloquée) est tué."""
        self.ferme = True
        try:
            self._file.put_nowait(None)
        except queue.Full:
            self.proc.kill()
        try:
            return self.proc.wait(timeout=delai)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            try:
                return self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                return None


# ---- sessions ---------------------------------------------------------------------------------------------------------

_VERROU = threading.Lock()
_SESSIONS: dict = {}          # id -> {vue publique, destinations (secrètes), diffusion, marqueurs, …}


def _publique(s: dict) -> dict:
    d = s.get("diffusion")
    etat = d.etat() if d else None
    dest = [{"id": x["id"], "plateforme": x["plateforme"], "libelle": x["libelle"], "lien": x["lien"],
             "etat": (etat["destinations"][i] if etat else "attente")} for i, x in enumerate(s["destinations"])]
    return {"id": s["id"], "espace_id": s["espace_id"], "titre": s["titre"], "etat": s["etat"],
            "debut_utc": s["debut_utc"], "destinations": dest, "marqueurs": list(s["marqueurs"]),
            "annonce": s.get("annonce"), "sante": etat}


def _session(lid: str) -> dict:
    if not isinstance(lid, str) or not ID.match(lid) or lid not in _SESSIONS:
        raise RefusLive("Direct inconnu.", 404)
    return _SESSIONS[lid]


def ouvrir(eid: str, ids, titre="") -> dict:
    """Une session de direct (une seule en cours à la fois) : les destinations sont résolues ICI (refus avant tout
    flux), leurs secrets restent dans la session."""
    dest = destinations(eid, ids)
    with _VERROU:
        maintenant = time.monotonic()
        for s in _SESSIONS.values():           # revue finale I1 : une session jamais branchée expire
            if s["etat"] == "pret" and maintenant - s["t0"] > PRET_MAX_S:
                s["etat"] = "termine"
                _oublier_secrets(s)
        if any(s["etat"] in ("pret", "en_cours", "fermeture") for s in _SESSIONS.values()):
            raise RefusLive("Un direct est déjà en cours.", 409)
        lid = _secrets.token_hex(8)
        _SESSIONS[lid] = {"id": lid, "espace_id": eid, "titre": (titre.strip() if isinstance(titre, str) else "")[:MAX_TITRE],
                          "etat": "pret", "debut_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                          "t0": time.monotonic(), "destinations": dest, "diffusion": None, "marqueurs": [], "clos": threading.Event(),
                          "annonce": None}
        return _publique(_SESSIONS[lid])


def vue(lid: str) -> dict:
    return _publique(_session(lid))


def brancher(lid: str, lancer=subprocess.Popen, fps: int = 30) -> Diffusion:
    """Lance le ffmpeg de la session (une fois) : appelé à l'ouverture du WebSocket."""
    with _VERROU:
        s = _session(lid)
        if s["etat"] != "pret" or s["diffusion"] is not None:
            raise RefusLive("Ce direct est déjà branché ou terminé.", 409)
        try:
            d = Diffusion([x["url"] for x in s["destinations"]], [x["cle"] for x in s["destinations"]], fps=fps, lancer=lancer)
        except OSError:
            raise RefusLive("ffmpeg introuvable : le direct ne peut pas partir.", 500) from None
        s["diffusion"] = d
        s["etat"] = "en_cours"
        s["t0"] = time.monotonic()
        return d


def _oublier_secrets(s: dict) -> None:
    for x in s["destinations"]:              # revue finale M5 : rien de secret ne reste en mémoire après le direct
        x["url"] = x["cle"] = ""


def debrancher(lid: str) -> None:
    """Fin du flux (WebSocket fermé, onglet fermé, capture coupée) : ffmpeg ne reste jamais vivant. Les transitions
    d'état passent sous _VERROU (revue finale I5) : « fermeture » interdit tout brancher() et tout nouveau direct."""
    with _VERROU:
        s = _SESSIONS.get(lid)
        if s and s["etat"] == "fermeture":
            attente = s["clos"]           # une autre fermeture est en cours : on attend sa fin (bilan complet)
        elif not s or s["etat"] not in ("pret", "en_cours"):
            return
        else:
            attente = None
            d = s.get("diffusion")
            s["etat"] = "fermeture"
    if attente is not None:
        attente.wait(15)
        return
    if d:
        d.fermer()
    with _VERROU:
        s["final"] = d.etat() if d else None
        s["duree_ms"] = int((time.monotonic() - s["t0"]) * 1000)
        s["etat"] = "fini"
        _oublier_secrets(s)
        s["clos"].set()


def marquer(lid: str, t_ms, libelle="") -> dict:
    s = _session(lid)
    if s["etat"] not in ("pret", "en_cours"):
        raise RefusLive("Ce direct est terminé.", 409)
    if len(s["marqueurs"]) >= MAX_MARQUEURS:
        raise RefusLive("Deux cents marqueurs au plus.", 400)
    if not isinstance(t_ms, (int, float)) or isinstance(t_ms, bool) or not 0 <= t_ms <= 7 * 24 * 3600 * 1000:
        raise RefusLive("Instant du marqueur invalide.", 400)
    m = {"t": int(t_ms), "libelle": (libelle.strip() if isinstance(libelle, str) else "")[:60]}
    s["marqueurs"].append(m)
    return m


def _webhook_valide(url: str) -> bool:
    if _WEBHOOK.match(url):
        return True
    return os.environ.get("DZ_LIVE_PREUVE") == "1" and bool(_WEBHOOK_PREUVE.match(url))


async def annoncer(lid: str, compte_id: str, texte: str = "", poster=None) -> dict:
    """Le message d'annonce dans le salon Discord du compte `compte_id` (webhook au coffre) : le texte + les liens
    publics des destinations. Aucune mention (allowed_mentions vide), aucune redirection suivie, 10 s au plus.
    Rend {ok, statut} — jamais l'URL du webhook."""
    from app.services import comptes
    s = _session(lid)
    if s["etat"] not in ("pret", "en_cours"):
        raise RefusLive("Ce direct est terminé.", 409)
    try:
        v = comptes.obtenir(compte_id)
    except KeyError:
        raise RefusLive("Compte Discord inconnu.", 404) from None
    if v["plateforme"] != "discord":
        raise RefusLive("Ce compte n'est pas un compte Discord.", 400)
    if not comptes.de_l_espace(compte_id, s["espace_id"]):
        raise RefusLive("Ce compte Discord appartient à un autre espace.", 409)
    with comptes.sous_compte(compte_id):
        url = str(comptes.cle("DISCORD_WEBHOOK") or "").strip()
    if not _webhook_valide(url):
        raise RefusLive("Webhook Discord invalide : une adresse https://discord.com/api/webhooks/… est attendue.", 400)
    if s.get("annonce"):                       # revue finale M6 : une annonce par direct, jamais de rafale dans le salon
        raise RefusLive("Ce direct a déjà été annoncé.", 409)
    liens = [x["lien"] for x in s["destinations"] if x["lien"]]
    corps = ((texte.strip() if isinstance(texte, str) else "")[:MAX_ANNONCE] or s["titre"] or "Live").strip()
    contenu = "\n".join([corps] + liens)[:1990]
    statut = None
    s["annonce"] = {"ok": False, "statut": None, "compte": compte_id}
    try:
        if poster is None:
            import httpx
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                r = await client.post(url, json={"content": contenu, "allowed_mentions": {"parse": []}})
                statut = r.status_code
        else:
            statut = await poster(url, {"content": contenu, "allowed_mentions": {"parse": []}})
    except Exception:  # noqa: BLE001 — une annonce ratée ne coupe pas le direct ; l'erreur brute pourrait citer l'URL
        statut = None
    ok = isinstance(statut, int) and 200 <= statut < 300
    s["annonce"] = {"ok": ok, "statut": statut, "compte": compte_id}
    return {"ok": ok, "statut": statut}


def terminer(lid: str, capture_id=None) -> dict:
    """Ferme le direct (ffmpeg arrêté) et, si `capture_id` est la capture enregistrée, écrit à côté d'elle
    `<id>.dzlive.json` (marqueurs, destinations et leur état final, annonce) : jamais un secret."""
    from app.services import capture
    s = _session(lid)
    debrancher(lid)
    final = s.get("final") or {}
    etats = final.get("destinations") or []
    doc = {"version": 1, "id": s["id"], "titre": s["titre"], "debut_utc": s["debut_utc"], "duree_ms": s.get("duree_ms", 0),
           "destinations": [{"plateforme": x["plateforme"], "libelle": x["libelle"], "lien": x["lien"],
                             "etat": etats[i] if i < len(etats) else "attente"} for i, x in enumerate(s["destinations"])],
           "marqueurs": sorted(s["marqueurs"], key=lambda m: m["t"]),
           "annonce": {"ok": s["annonce"]["ok"]} if s.get("annonce") else None}
    fichier = None
    if capture_id is not None:
        if not isinstance(capture_id, str) or not capture.ID.match(capture_id):
            raise RefusLive("Capture inconnue.", 404)
        dossier = capture.racine() / capture_id
        if not dossier.is_dir():
            raise RefusLive("Capture inconnue.", 404)
        f = dossier / f"{capture_id}.dzlive.json"
        tmp = f.with_name(f.name + ".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(f)
        fichier = f.name
    s["etat"] = "termine"
    return {"live": doc, "fichier": fichier}


def abandonner(lid: str) -> None:
    s = _session(lid)
    debrancher(lid)
    s["etat"] = "termine"


def arreter_tout() -> None:
    for lid in list(_SESSIONS):
        try:
            debrancher(lid)
        except Exception:  # noqa: BLE001 — à la sortie, on ferme tout ce qu'on peut
            pass


atexit.register(arreter_tout)
