"""Routeur des réglages (plan Settings, tâche #15 du suivi, 29/09/2026).

Ce que l'écran Settings gagne vit ICI et pas dans les 10 000 lignes de `routes.py` : d'abord le diagnostic (T1-T3),
plus tard plafonds, guides fournisseurs, mise à jour, export, coffre. Monté par `main.py` sous `/api/reglages`,
comme les routeurs montage et cards.

Toute route qui lit ou teste des clés passe par `_local()` — la garde de boucle locale des Réglages
(`routes._require_localhost`, un seul propriétaire de la règle), GET compris : les aperçus de clés sont des Réglages.
"""
from fastapi import APIRouter, HTTPException, Request

from app.config import APP_VERSION

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


async def _soldes() -> dict:
    """Les soldes en direct : un seul producteur (`/cost/balances`), deux lecteurs (la pastille du bandeau et le
    diagnostic). Remplacé au banc."""
    from app.api.routes import cost_balances
    return await cost_balances()


@router.get("/diagnostic")
async def diagnostic_complet(request: Request):
    """L'écran unique : version, poids disque, journal, clés (masquées), soldes."""
    _local(request)
    from app.api.routes import _ALLOWED_ENV_KEYS, _mask, _read_env_file
    from app.services import diagnostic as D
    env = _read_env_file()
    cles = [{"cle": k, "definie": bool(env.get(k, "")), "apercu": _mask(env.get(k, "")), "testable": D.testable(k)}
            for k in sorted(_ALLOWED_ENV_KEYS)]
    try:
        soldes = await _soldes()
    except Exception as e:  # noqa: BLE001 — un solde muet ne masque pas le reste
        soldes = {"erreur": str(e)[:160]}
    return {"version": APP_VERSION, "disque": D.poids_disque(), "journal": D.journal_erreurs(),
            "cles": cles, "soldes": soldes}


@router.post("/diagnostic/cle")
async def diagnostic_cle(body: dict, request: Request):
    """Teste UNE clé. Sans `valeur`, la clé enregistrée est relue du `.env` : l'écran n'a jamais à renvoyer un secret
    au serveur pour le faire tester."""
    _local(request)
    from app.api.routes import _ALLOWED_ENV_KEYS, _read_env_file
    from app.services import diagnostic as D
    nom = str((body or {}).get("nom") or "").strip()
    if nom not in _ALLOWED_ENV_KEYS:
        raise HTTPException(400, f"clé inconnue ou non modifiable : {nom}")
    env = _read_env_file()
    if nom.startswith("X_"):
        return await D.tester_x(env)
    valeur = str((body or {}).get("valeur") or "") or env.get(nom, "")
    return await D.tester_cle(nom, valeur)
