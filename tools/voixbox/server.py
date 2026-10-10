# -*- coding: utf-8 -*-
"""Voixbox — conversion de voix LOCALE pour le Direct de DeepotusVideoGen (Avatar live G5, t166, 10/10/2026).

CE FICHIER NE TOURNE PAS DANS L'APPLICATION. Le python embarqué de l'app est stdlib + Pillow ; RVC exige torch,
CUDA et Python 3.12. Environnement séparé (voir README.md) :

    voir README.md : dépôt RVC WebUI épinglé + son .venv Python 3.12 (torch CUDA), puis
    tools\\voixbox\\rvc-webui\\.venv\\Scripts\\python tools/voixbox/server.py     # écoute 127.0.0.1:17495

Moteur : RVC (Retrieval-based Voice Conversion, licence MIT — décision de l'utilisateur du 10/10 : Seed-VC écarté,
GPL-3.0 et dépôt archivé), par son dépôt RVC WebUI épinglé (VOIXBOX_RVC_WEBUI, défaut tools/voixbox/rvc-webui) : la
même installation entraîne les voix et les fait parler. Une voix = un modèle ENTRAÎNÉ une fois, rangé dans un dossier :
    <VOIXBOX_MODELES>/<nom>/<quelquechose>.pth   (+ <quelquechose>.index facultatif, recommandé)
VOIXBOX_MODELES vaut par défaut %LOCALAPPDATA%\\DeepotusVideoGen\\voix_rvc.

Contrat (le nôtre, figé par backend/tests/test_voixbox_contrat.py côté serveur et backend/tests/test_avatar_voix_direct.py
côté client) :
    GET  /health                                → {"ok": true, "moteur": "rvc", "sr": 16000, "gpu": "...",
                                                    "modeles": [{"nom": "...", "index": true}]}
    POST /convertir?modele=<nom>&transpose=<-12..12>
         corps : PCM s16le mono 16 kHz (application/octet-stream, 10 s au plus)
         → 200 PCM s16le mono 16 kHz, en-tête X-Latence-Ms ; 404 modèle inconnu ; 413 trop long ; 500 lisible
Le serveur HTTP est séparé du moteur (torch n'est importé que dans `MoteurRVC`) : le banc vérifie le contrat sans
télécharger de poids.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST, PORT = "127.0.0.1", 17495
SR = 16000
MAX_OCTETS = SR * 2 * 10                # 10 s de PCM 16 bits mono
_NOM = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def dossier_modeles() -> Path:
    d = os.environ.get("VOIXBOX_MODELES") or os.path.join(os.environ.get("LOCALAPPDATA", "."), "DeepotusVideoGen", "voix_rvc")
    return Path(d)


def lister_modeles(racine: Path) -> list[dict]:
    """Les voix entraînées : un dossier par voix, un .pth dedans (le plus récent), un .index facultatif."""
    out = []
    if racine.is_dir():
        for d in sorted(racine.iterdir()):
            if d.is_dir() and _NOM.match(d.name) and any(d.glob("*.pth")):
                out.append({"nom": d.name, "index": any(d.glob("*.index"))})
    return out


def fichiers_modele(racine: Path, nom: str) -> tuple[Path, Path | None] | None:
    if not isinstance(nom, str) or not _NOM.match(nom):
        return None
    d = racine / nom
    pths = sorted(d.glob("*.pth"), key=lambda p: p.stat().st_mtime) if d.is_dir() else []
    if not pths:
        return None
    idx = sorted(d.glob("*.index"), key=lambda p: p.stat().st_mtime)
    return pths[-1], (idx[-1] if idx else None)


class _IndexReconstruit:
    """Un index faiss DÉJÀ reconstruit : `reconstruct_n(0, ntotal)` rend les vecteurs gardés, le reste est délégué."""

    def __init__(self, index, vecteurs):
        self._index, self._vecteurs = index, vecteurs

    def reconstruct_n(self, debut, n):
        if debut == 0 and n == self._index.ntotal:
            return self._vecteurs
        return self._index.reconstruct_n(debut, n)

    def __getattr__(self, nom):
        return getattr(self._index, nom)


def _index_en_cache():
    """Mesuré le 10/10 (RTX 2080 Ti, voix de 10 min) : la WebUI relit ET reconstruit l'index (100 Mo) à CHAQUE appel
    (infer/vc/pipeline.py : faiss.read_index puis reconstruct_n) — 220 ms sur 295 ms d'inférence. Pour le direct,
    l'index est lu une fois par fichier (et par date de modification) et gardé reconstruit. Aucune ligne de la WebUI
    n'est modifiée : seul `faiss.read_index` est enveloppé, dans CE processus."""
    import faiss
    origine = faiss.read_index
    cache: dict = {}

    def lire(chemin, *a):
        if a:
            return origine(chemin, *a)
        cle = (os.path.abspath(chemin), os.path.getmtime(chemin))
        if cle not in cache:
            cache.clear()                                   # une voix à la fois en mémoire
            idx = origine(chemin)
            cache[cle] = _IndexReconstruit(idx, idx.reconstruct_n(0, idx.ntotal))
        return cache[cle]

    faiss.read_index = lire


class MoteurRVC:
    """Le vrai moteur : le dépôt RVC WebUI (RVC-Project/Retrieval-based-Voice-Conversion-WebUI, MIT) — la MÊME
    installation sert à entraîner les voix (onglet « Train » de sa WebUI) et à les faire parler ici. Son API
    d'inférence est celle de sa ligne de commande `infer/cli.py` : VC(Config()), get_vc(nom), vc_single(...).
    torch n'est importé qu'ICI."""

    def __init__(self, racine: Path, depot_webui: Path):
        import sys
        self.depot = Path(depot_webui).resolve()
        if not (self.depot / "infer" / "vc" / "modules.py").is_file():
            raise SystemExit(f"Voixbox : dépôt RVC WebUI introuvable ({self.depot}) — VOIXBOX_RVC_WEBUI, voir README.md")
        sys.path.insert(0, str(self.depot))
        os.chdir(self.depot)                                    # configs/ et assets/ sont lus en relatif
        # les MÊMES chemins par défaut que la ligne de commande officielle (infer/cli.py) : sans rmvpe_root, le
        # pipeline lève KeyError à la première extraction de hauteur (relevé le 10/10 sur la vraie installation)
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        os.environ.setdefault("weight_root", str(self.depot / "assets" / "weights"))
        os.environ.setdefault("index_root", str(self.depot / "logs"))
        os.environ.setdefault("outside_index_root", str(self.depot / "assets" / "indices"))
        os.environ.setdefault("rmvpe_root", str(self.depot / "assets" / "rmvpe"))
        import numpy as np
        import torch
        from configs.config import Config
        from infer.vc.modules import VC
        argv, sys.argv = sys.argv[:], [sys.argv[0]]
        try:
            cfg = Config()
        finally:
            sys.argv = argv
        self._np = np
        self.racine = racine
        self.vc = VC(cfg)
        _index_en_cache()
        self.charge = None
        self.gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
        print(f"Voixbox : RVC WebUI {self.depot.name} sur {self.gpu} ; voix dans {racine}")

    def convertir(self, nom: str, pcm: bytes, transpose: int = 0) -> bytes:
        from scipy.signal import resample_poly
        f = fichiers_modele(self.racine, nom)
        if f is None:
            raise KeyError(nom)
        pth, idx = f
        if self.charge != str(pth):
            os.environ["weight_root"] = str(pth.parent)
            self.vc.get_vc(pth.name)
            self.charge = str(pth)
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / "in.wav"
            with wave.open(str(src), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
            statut, res = self.vc.vc_single(0, str(src), int(transpose), "rmvpe", str(idx) if idx else "",
                                            0.75 if idx else 0.0, 0, 1.0, 0.33)
        if not res or res[0] is None or res[1] is None:
            raise RuntimeError(str(statut).strip()[-300:])        # la CAUSE est à la fin du traceback de la WebUI
        tgt_sr, audio = int(res[0]), self._np.asarray(res[1])
        a = audio.astype(self._np.float32)
        if audio.dtype.kind in "iu" or (a.size and float(self._np.abs(a).max()) > 1.5):
            a = a / 32768.0                                     # vc_single rend de l'int16
        if tgt_sr != SR:
            g = self._np.gcd(tgt_sr, SR)
            a = resample_poly(a, SR // g, tgt_sr // g)
        return (self._np.clip(a, -1, 1) * 32767).astype("<i2").tobytes()


def fabrique(moteur):
    """La classe de requête liée à un moteur (le vrai, ou le faux du banc). Un seul modèle, un seul GPU : les
    conversions passent l'une après l'autre (verrou)."""
    verrou = threading.Lock()

    class Requete(BaseHTTPRequestHandler):
        # TCP_NODELAY : mesuré le 10/10, sans lui ~450 ms s'ajoutaient à chaque segment (Nagle + ACK différé de Windows
        # sur les petites écritures en-têtes/corps) pour 164 ms de conversion.
        disable_nagle_algorithm = True
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _json(self, code, obj):
            b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if urlparse(self.path).path != "/health":
                return self._json(404, {"detail": "inconnu"})
            self._json(200, {"ok": True, "moteur": "rvc", "sr": SR, "gpu": getattr(moteur, "gpu", "?"),
                             "modeles": lister_modeles(moteur.racine)})

        def do_POST(self):
            u = urlparse(self.path)
            if u.path != "/convertir":
                return self._json(404, {"detail": "inconnu"})
            q = parse_qs(u.query)
            nom = (q.get("modele") or [""])[0]
            try:
                transpose = max(-12, min(12, int((q.get("transpose") or ["0"])[0])))
            except ValueError:
                transpose = 0
            n = int(self.headers.get("Content-Length") or 0)
            if 0 < n <= 64 * 1024 * 1024:
                pcm = self.rfile.read(n)        # lu AVANT tout refus : sinon Windows coupe la connexion (WinError 10054)
            else:
                self.close_connection = True
                return self._json(413 if n else 400, {"detail": "corps absent ou démesuré"})
            if n % 2:
                return self._json(400, {"detail": "PCM 16 bits attendu (longueur paire, non vide)"})
            if n > MAX_OCTETS:
                return self._json(413, {"detail": "segment trop long (10 s au plus)"})
            if fichiers_modele(moteur.racine, nom) is None:
                return self._json(404, {"detail": f"modèle de voix inconnu : {nom[:40]!r}"})
            t0 = time.perf_counter()
            try:
                with verrou:
                    out = moteur.convertir(nom, pcm, transpose)
            except Exception as e:  # noqa: BLE001 — une panne du moteur est DITE, jamais un socket coupé
                return self._json(500, {"detail": f"le moteur RVC a échoué : {type(e).__name__}: {str(e)[:200]}"})
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(out)))
            self.send_header("X-Latence-Ms", str(int((time.perf_counter() - t0) * 1000)))
            self.end_headers()
            self.wfile.write(out)

    return Requete


if __name__ == "__main__":
    racine = dossier_modeles()
    racine.mkdir(parents=True, exist_ok=True)
    depot = os.environ.get("VOIXBOX_RVC_WEBUI") or str(Path(__file__).resolve().parent / "rvc-webui")
    m = MoteurRVC(racine, Path(depot))
    print(f"Voixbox écoute http://{HOST}:{PORT} — {len(lister_modeles(racine))} voix entraînée(s)")
    ThreadingHTTPServer((HOST, PORT), fabrique(m)).serve_forever()
