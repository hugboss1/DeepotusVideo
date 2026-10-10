# -*- coding: utf-8 -*-
"""Voixbox — conversion de voix LOCALE pour le Direct de DeepotusVideoGen (Avatar live G5, t166, 10/10/2026).

CE FICHIER NE TOURNE PAS DANS L'APPLICATION. Le python embarqué de l'app est stdlib + Pillow ; RVC exige torch,
fairseq et Python 3.10. Environnement séparé (voir README.md) :

    uv venv --python 3.10 tools/voixbox/.venv
    uv pip install --python tools/voixbox/.venv -r tools/voixbox/requirements.txt
    tools\\voixbox\\.venv\\Scripts\\python tools/voixbox/server.py        # écoute 127.0.0.1:17495

Moteur : RVC (Retrieval-based Voice Conversion, licence MIT — décision de l'utilisateur du 10/10 : Seed-VC écarté,
GPL-3.0 et dépôt archivé). Une voix = un modèle ENTRAÎNÉ une fois (RVC WebUI), rangé dans un dossier :
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


class MoteurRVC:
    """Le vrai moteur : la bibliothèque `rvc` (RVC-Project), torch + fairseq, chargés ICI seulement."""

    def __init__(self, racine: Path):
        import numpy as np                                      # noqa: F401 — hors de l'application
        import torch
        from rvc.modules.vc.modules import VC
        self._np, self._torch = np, torch
        self.racine = racine
        self.vc = VC()
        self.charge = None
        self.gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
        print(f"Voixbox : RVC prêt sur {self.gpu} ; modèles dans {racine}")

    def convertir(self, nom: str, pcm: bytes, transpose: int = 0) -> bytes:
        from scipy.signal import resample_poly
        f = fichiers_modele(self.racine, nom)
        if f is None:
            raise KeyError(nom)
        pth, idx = f
        if self.charge != str(pth):
            self.vc.get_vc(str(pth))
            self.charge = str(pth)
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / "in.wav"
            with wave.open(str(src), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
            tgt_sr, audio, _times, _ = self.vc.vc_inference(1, src, f0_up_key=int(transpose), f0_method="rmvpe",
                                                            index_file=str(idx) if idx else None, index_rate=0.75,
                                                            protect=0.33)
        a = self._np.asarray(audio, dtype=self._np.float32)
        if a.dtype.kind == "f" and a.size and float(self._np.abs(a).max()) > 1.5:
            a = a / 32768.0                                     # certaines versions rendent de l'int16 en float
        if int(tgt_sr) != SR:
            g = self._np.gcd(int(tgt_sr), SR)
            a = resample_poly(a, SR // g, int(tgt_sr) // g)
        return (self._np.clip(a, -1, 1) * 32767).astype("<i2").tobytes()


def fabrique(moteur):
    """La classe de requête liée à un moteur (le vrai, ou le faux du banc). Un seul modèle, un seul GPU : les
    conversions passent l'une après l'autre (verrou)."""
    verrou = threading.Lock()

    class Requete(BaseHTTPRequestHandler):
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
    m = MoteurRVC(racine)
    print(f"Voixbox écoute http://{HOST}:{PORT} — {len(lister_modeles(racine))} voix entraînée(s)")
    ThreadingHTTPServer((HOST, PORT), fabrique(m)).serve_forever()
