# -*- coding: utf-8 -*-
"""t354 (28/10/2026) — Veille & prospection P3, tâche 5b : les FOURNISSEURS DE RECHERCHE WEB, au choix de l'utilisateur
(décision du 28/10 : Anthropic par défaut avec la clé existante, ou Tavily, Exa, Serper avec leur clé, rangée au coffre).

Une recherche n'est JAMAIS lancée par l'agent seul : elle part d'une carte de devis acceptée (tâche 5d), après
`plafonds.verifier` sur `op(...)` (kind `recherche_web`, que pricing chiffre). Le coût réel est rendu (`cout_usd`).
Prix unitaires relevés le 28/10/2026 (pages de prix et documentation des fournisseurs) :
  anthropic : 10 $ / 1 000 recherches (+ jetons du modèle) ; tavily : 1 crédit ≈ 0,008 $ ; exa : ≈ 0,007 $ (Exa rend
  `costDollars.total`, retenu comme réel) ; serper : 1 $ / 1 000 requêtes.
Adaptateurs en httpx (comme moteurs_texte) ; jamais la clé dans un message d'erreur.
"""
from __future__ import annotations

import json

from app.config import DATA_ROOT, settings

FOURNISSEURS = ("anthropic", "tavily", "exa", "serper")
CLES = {"anthropic": "ANTHROPIC_API_KEY", "tavily": "TAVILY_API_KEY", "exa": "EXA_API_KEY", "serper": "SERPER_API_KEY"}
PRIX = {"anthropic": 0.01, "tavily": 0.008, "exa": 0.007, "serper": 0.001}      # $ par requête, relevés le 28/10/2026
MAX_USAGES_ANTHROPIC = 2
JETONS_ANTHROPIC = (40000, 1500)      # estimation haute d'un tour : les résultats des recherches comptent en entrée
DELAI = 30.0
MAX_RESULTATS = 10


class SansCle(RuntimeError):
    """Le fournisseur choisi n'a pas de clé : rien n'est appelé."""


class RechercheEchouee(RuntimeError):
    """Le fournisseur a répondu par une erreur (statut HTTP, erreur de recherche). `cout_usd` : ce qui a pu être
    facturé quand même (relecture I4 : les jetons d'un tour Anthropic en erreur)."""
    def __init__(self, message: str, cout_usd: float = 0.0):
        super().__init__(message)
        self.cout_usd = float(cout_usd or 0.0)


def _fichier():
    return DATA_ROOT / "prospects" / "recherche.json"


def fournisseur_actif() -> str:
    try:
        f = json.loads(_fichier().read_text(encoding="utf-8")).get("fournisseur")
    except (OSError, ValueError, AttributeError):
        f = None
    return f if f in FOURNISSEURS else "anthropic"


def choisir(fournisseur: str) -> None:
    if fournisseur not in FOURNISSEURS:
        raise ValueError(f"fournisseur de recherche inconnu : {str(fournisseur)[:30]}")
    _fichier().parent.mkdir(parents=True, exist_ok=True)
    _fichier().write_text(json.dumps({"fournisseur": fournisseur}), encoding="utf-8")


def _cle(fournisseur: str) -> str:
    return str(getattr(settings, CLES[fournisseur], "") or "").strip()


def configure(fournisseur: str) -> bool:
    return fournisseur in FOURNISSEURS and bool(_cle(fournisseur))


def etat() -> dict:
    return {"fournisseur": fournisseur_actif(),
            "fournisseurs": [{"id": f, "configure": configure(f), "prix_usd": PRIX[f]} for f in FOURNISSEURS]}


def _modele() -> str:
    from app.services import moteurs_texte as MT
    return MT.modele_agent()


def op(fournisseur: str, max_resultats: int = 5) -> dict:
    """L'op chiffrée par pricing (plafonds) : une requête ; Anthropic = ses recherches + les jetons d'un tour."""
    if fournisseur not in FOURNISSEURS:
        raise ValueError(f"fournisseur de recherche inconnu : {str(fournisseur)[:30]}")
    if fournisseur == "anthropic":
        from app.services import moteurs_texte as MT
        return {"kind": "composition", "parts": [
            {"kind": "recherche_web", "fournisseur": "anthropic", "requetes": MAX_USAGES_ANTHROPIC},
            MT.op_tour(_modele(), *JETONS_ANTHROPIC)]}
    return {"kind": "recherche_web", "fournisseur": fournisseur, "requetes": 1}


def devis(fournisseur: str, max_resultats: int = 5) -> float:
    from app.services import pricing
    return float(pricing.estimate(op(fournisseur, max_resultats))["total_usd"])


async def _post(url: str, headers: dict, corps: dict) -> tuple[int, dict]:
    import httpx
    async with httpx.AsyncClient(timeout=DELAI) as c:
        r = await c.post(url, headers=headers, json=corps)
        try:
            j = r.json()
        except ValueError:
            j = {}
        return r.status_code, j if isinstance(j, dict) else {}


_POST = _post                         # couture du banc


def _forme(titre, url, extrait="") -> dict:
    return {"titre": str(titre or "")[:200], "url": str(url or "")[:500], "extrait": str(extrait or "")[:300]}


async def _appel(fournisseur: str, url: str, headers: dict, corps: dict) -> dict:
    try:
        statut, j = await _POST(url, headers, corps)
    except Exception as e:  # noqa: BLE001 — réseau : dit, sans la clé
        raise RechercheEchouee(f"{fournisseur} injoignable ({type(e).__name__})") from None
    if statut != 200:
        raise RechercheEchouee(f"{fournisseur} a refusé la recherche (HTTP {statut})")
    return j


async def rechercher(requete: str, max_resultats: int = 5, fournisseur: str | None = None) -> dict:
    """{"resultats": [{titre, url, extrait}], "cout_usd", "fournisseur"} ; SansCle, RechercheEchouee, ValueError."""
    f = fournisseur or fournisseur_actif()
    if f not in FOURNISSEURS:
        raise ValueError(f"fournisseur de recherche inconnu : {str(f)[:30]}")
    q = str(requete or "").strip()[:300]
    if not q:
        raise ValueError("requête de recherche vide")
    n = max(1, min(int(max_resultats or 5), MAX_RESULTATS))
    cle = _cle(f)
    if not cle:
        raise SansCle(f"aucune clé pour la recherche {f} : posez-la dans l'onglet Prospects")
    if f == "tavily":
        j = await _appel(f, "https://api.tavily.com/search", {"Authorization": f"Bearer {cle}"},
                         {"query": q, "max_results": n, "search_depth": "basic"})
        res = [_forme(x.get("title"), x.get("url"), x.get("content")) for x in j.get("results") or [] if isinstance(x, dict)]
        return {"resultats": res[:n], "cout_usd": PRIX[f], "fournisseur": f}
    if f == "exa":
        j = await _appel(f, "https://api.exa.ai/search", {"x-api-key": cle}, {"query": q, "numResults": n, "type": "auto"})
        res = [_forme(x.get("title"), x.get("url")) for x in j.get("results") or [] if isinstance(x, dict)]
        cout = (j.get("costDollars") or {}).get("total") if isinstance(j.get("costDollars"), dict) else None
        return {"resultats": res[:n], "cout_usd": float(cout) if isinstance(cout, (int, float)) else PRIX[f], "fournisseur": f}
    if f == "serper":
        j = await _appel(f, "https://google.serper.dev/search", {"X-API-KEY": cle}, {"q": q, "num": n})
        res = [_forme(x.get("title"), x.get("link"), x.get("snippet")) for x in j.get("organic") or [] if isinstance(x, dict)]
        return {"resultats": res[:n], "cout_usd": PRIX[f], "fournisseur": f}
    modele = _modele()
    j = await _appel(f, "https://api.anthropic.com/v1/messages",
                     {"x-api-key": cle, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                     {"model": modele, "max_tokens": JETONS_ANTHROPIC[1],
                      "tools": [{"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_USAGES_ANTHROPIC,
                                 "allowed_callers": ["direct"]}],
                      "messages": [{"role": "user", "content": "Recherche sur le web et liste les sites officiels "
                                                               f"d'entreprises qui correspondent à : {q}"}]})
    res, erreur = [], None
    for b in j.get("content") or []:
        if not isinstance(b, dict) or b.get("type") != "web_search_tool_result":
            continue
        contenu = b.get("content")
        if isinstance(contenu, dict):                   # une erreur est un OBJET, un succès une LISTE
            erreur = str(contenu.get("error_code") or "inconnue")
            continue
        for x in contenu or []:
            if isinstance(x, dict) and x.get("type") == "web_search_result":
                res.append(_forme(x.get("title"), x.get("url")))
    u = j.get("usage") if isinstance(j.get("usage"), dict) else {}
    stu = u.get("server_tool_use") if isinstance(u.get("server_tool_use"), dict) else {}
    nb = int(stu.get("web_search_requests") or 0) if isinstance(stu.get("web_search_requests"), int) else 0
    from app.services import moteurs_texte as MT, pricing
    jetons = float(pricing.estimate(MT.op_tour(modele, int(u.get("input_tokens") or 0) if isinstance(u.get("input_tokens"), int) else 0,
                                               int(u.get("output_tokens") or 0) if isinstance(u.get("output_tokens"), int) else 0))["total_usd"])
    if erreur and not res:
        raise RechercheEchouee(f"anthropic : recherche en erreur ({erreur})", round(nb * PRIX[f] + jetons, 6))
    return {"resultats": res[:n], "cout_usd": round(nb * PRIX[f] + jetons, 6), "fournisseur": f}
