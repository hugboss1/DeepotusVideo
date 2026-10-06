# -*- coding: utf-8 -*-
"""Clapbox — service local d'embeddings CLAP pour DeepotusVideoGen (T103, plan son-vfx D3).

CE FICHIER NE TOURNE PAS DANS L'APPLICATION. Le python embarqué de l'app est stdlib + Pillow ; le modèle exige torch
et transformers. Environnement séparé (voir README.md) :

    py -3.11 -m venv .venv
    .venv\\Scripts\\python -m pip install -r tools/clapbox/requirements.txt
    .venv\\Scripts\\python tools/clapbox/server.py          # écoute 127.0.0.1:17494

Contrat (le nôtre, figé par backend/tests/test_sound_search_index.py côté client et
backend/tests/test_clapbox_contrat.py côté serveur) :
    GET  /health       → {"ok": true, "model": "...", "dim": 512}
    POST /embed/text   {"texts": [...]}         → {"dim", "model", "vectors": [[...]]}
    POST /embed/audio  multipart, champ `files`  → {"dim", "model", "vectors": [[...]]}

Le décodage du multipart passe par le paquet stdlib `email` : le module `cgi` du plan d'origine a été RETIRÉ de
Python 3.13. Le serveur HTTP est séparé du moteur (torch n'est importé que dans `MoteurClap`), ce qui permet au
banc de vérifier le contrat sans télécharger 2 Go de poids.
"""
from __future__ import annotations

import json
import tempfile
from email.parser import BytesParser
from email.policy import default as _policy
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MODEL_ID = "laion/clap-htsat-unfused"
SR = 48000
HOST, PORT = "127.0.0.1", 17494
MAX_BODY = 200 * 1024 * 1024        # un lot de huit sons tient très largement dessous


def lire_multipart(corps: bytes, content_type: str) -> list[tuple[str, bytes]]:
    """Les fichiers du champ `files` d'un corps multipart/form-data : [(nom, octets)]. Un nom réduit à sa
    feuille (jamais de chemin). Corps illisible ou sans fichier : liste vide."""
    if "multipart/form-data" not in (content_type or ""):
        return []
    msg = BytesParser(policy=_policy).parsebytes(
        b"Content-Type: " + content_type.encode("latin-1") + b"\r\n\r\n" + corps)
    out = []
    for part in msg.iter_parts():
        if part.get_param("name", header="content-disposition") != "files":
            continue
        nom = Path(part.get_filename() or "x").name or "x"
        out.append((nom, part.get_payload(decode=True) or b""))
    return out


class MoteurClap:
    """Le vrai modèle : torch + transformers + librosa, chargés ICI seulement."""

    def __init__(self):
        import torch                                            # noqa: F401 — hors de l'application
        from transformers import ClapModel, ClapProcessor
        print(f"Clapbox : chargement de {MODEL_ID} (première fois : ~2 Go à télécharger)…")
        self._torch = torch
        self._proc = ClapProcessor.from_pretrained(MODEL_ID)
        self._model = ClapModel.from_pretrained(MODEL_ID).eval()
        self.model = MODEL_ID
        self.dim = int(self._model.config.projection_dim)

    def _vecs(self, t) -> list[list[float]]:
        return [[float(x) for x in row] for row in t.detach()]

    def embed_text(self, texts: list[str]) -> list[list[float]]:
        with self._torch.no_grad():
            i = self._proc(text=list(texts), return_tensors="pt", padding=True)
            return self._vecs(self._model.get_text_features(**i))

    def embed_audio(self, paths: list[Path]) -> list[list[float]]:
        import librosa
        waves = [librosa.load(str(p), sr=SR, mono=True)[0] for p in paths]
        with self._torch.no_grad():
            i = self._proc(audios=waves, sampling_rate=SR, return_tensors="pt", padding=True)
            return self._vecs(self._model.get_audio_features(**i))


def fabrique(moteur) -> type:
    """Le gestionnaire HTTP, lié à un moteur (le vrai, ou celui d'un banc)."""

    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            b = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path == "/health":
                self._json({"ok": True, "model": moteur.model, "dim": moteur.dim})
            else:
                self._json({"error": "introuvable"}, 404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                self._json({"error": "corps trop lourd"}, 413)
                return
            corps = self.rfile.read(n)
            try:
                if self.path == "/embed/text":
                    texts = json.loads(corps or b"{}").get("texts") or []
                    self._json({"dim": moteur.dim, "model": moteur.model, "vectors": moteur.embed_text(texts)})
                elif self.path == "/embed/audio":
                    fichiers = lire_multipart(corps, self.headers.get("Content-Type") or "")
                    tmp = Path(tempfile.mkdtemp(prefix="clapbox_"))
                    chemins = []
                    for i, (nom, octets) in enumerate(fichiers):
                        p = tmp / f"{i:03d}_{nom}"
                        p.write_bytes(octets)
                        chemins.append(p)
                    self._json({"dim": moteur.dim, "model": moteur.model,
                                "vectors": moteur.embed_audio(chemins) if chemins else []})
                else:
                    self._json({"error": "introuvable"}, 404)
            except Exception as e:  # noqa: BLE001 — le client lit le message, le service reste debout
                self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    return Gestionnaire


if __name__ == "__main__":
    m = MoteurClap()
    print(f"Clapbox : prêt sur http://{HOST}:{PORT} (dim={m.dim})")
    HTTPServer((HOST, PORT), fabrique(m)).serve_forever()
