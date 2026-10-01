# -*- coding: utf-8 -*-
"""Plan mobile T4 (tâche #56, 01/10/2026) — un JETON D'APPAREIL valide pour les bancs qui simulent un client du réseau
local. Depuis la garde de jeton (main._device_token_guard, le middleware le plus extérieur), un client du réseau local
SANS jeton reçoit 401 avant toute autre garde. Pour continuer à prouver que les gardes INTÉRIEURES (clés, écritures,
dépenses : 403) refusent même un téléphone APPAIRÉ, ces bancs envoient un vrai jeton, obtenu par les vraies routes
(/pair/start depuis le PC, /pair/claim depuis le réseau local) dans la base DU banc.

Ce n'est pas un banc (le nom ne commence pas par test_)."""


def entetes(app, ip: str = "192.168.1.250") -> dict:
    """Appaire un appareil dans la base courante et rend {"Authorization": "Bearer <jeton>"}."""
    from fastapi.testclient import TestClient
    with TestClient(app, client=("127.0.0.1", 50009)) as loc:
        secret = loc.post("/api/pair/start").json()["secret"]
        lan = TestClient(app, client=(ip, 50009))
        r = lan.post("/api/pair/claim", json={"secret": secret, "nom": "banc"})
        assert r.status_code == 200, (r.status_code, r.text[:200])
        return {"Authorization": "Bearer " + r.json()["jeton"]}
