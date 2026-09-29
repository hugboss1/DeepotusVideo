# -*- coding: utf-8 -*-
"""Faux réseau pour les bancs du Scheduler (plan scheduler T3-T7 — tâche #25, 29/09/2026). PAS un test (non collecté).

Écart au plan du 03/09 : le plan remplaçait httpx.AsyncClient par une classe maison — elle aurait accepté ce que le
VRAI client refuse (un fichier synchrone passé en `content=` à un client asynchrone lève dans httpx). Ici c'est le vrai
httpx.AsyncClient qui envoie, sur un `httpx.MockTransport` : seul le réseau est simulé. Chaque requête est enregistrée
(méthode, url, en-têtes, corps LU en entier) et reçoit la réponse suivante du script, consommé dans l'ordre.

    rec = Recorder(); module._client = rec.factory
    rec.script[:] = [httpx.Response(200, json={...}), httpx.Response(200, headers={"location": ...})]
"""
from dataclasses import dataclass
from urllib.parse import parse_qs

import httpx


@dataclass
class Call:
    method: str
    url: str
    headers: dict
    body: bytes

    def form(self) -> dict:
        """Corps application/x-www-form-urlencoded, champ -> valeur."""
        return {k: v[0] for k, v in parse_qs(self.body.decode("utf-8")).items()}

    def params(self) -> dict:
        return dict(httpx.URL(self.url).params)


class Recorder:
    def __init__(self):
        self.calls: list[Call] = []
        self.script: list[httpx.Response] = []

    async def _handler(self, request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        self.calls.append(Call(request.method, str(request.url), dict(request.headers), body))
        return self.script.pop(0) if self.script else httpx.Response(200, json={})

    def factory(self, timeout: float = 60.0, **_k) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self._handler), timeout=timeout)
