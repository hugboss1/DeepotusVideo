# -*- coding: utf-8 -*-
"""t345 (29/10/2026, D1 du lot Scenario) — le SERVEUR MCP de DeepotusVideo, transport stdio, SANS dépendance.

Lancé par le client MCP (Claude Code) comme un sous-processus ; la commande exacte est affichée dans Réglages › Serveur
MCP (« Copier »), par exemple :
    claude mcp add --scope user deepotus -- "<app>\\runtime\\python\\python.exe" "<app>\\backend\\app\\mcp_stdio.py"
Le fichier se lance par son CHEMIN (le python embarqué ignore PYTHONPATH et `-m` dépend du dossier courant du client) :
il n'importe donc RIEN de l'application, seulement la bibliothèque standard.

Protocole : JSON-RPC 2.0, un message par ligne UTF-8 sur stdin / stdout, aucun saut de ligne dans un message, rien
d'autre sur stdout (le journal va sur stderr) — spec MCP 2025-11-25, « Transports › stdio » et « Lifecycle ».
Méthodes : initialize (version négociée), notifications/initialized, ping, tools/list, tools/call ; resources/list et
prompts/list rendent des listes vides ; toute autre méthode -> -32601. Les erreurs d'un outil reviennent en résultat
`isError: true` (le modèle peut se corriger), jamais en erreur de protocole.

Le serveur ne fait que relayer vers le backend LOCAL de l'app (DEEPOTUS_URL, défaut http://127.0.0.1:8765 ; tout hôte
autre que la boucle locale est refusé au démarrage) et seulement sur deux routes, « /api/mcp/outils » et
« /api/mcp/appel » (liste blanche) : le backend reste la source de vérité des droits, des plafonds et du masquage.
Aucun proxy n'est suivi. Aucun en-tête Origin n'est envoyé : les gestes de l'utilisateur (lancer, refuser) restent
hors de portée du client MCP.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

NOM = "deepotus"
VERSION_SERVEUR = "1.0.0"
VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")     # la première est la plus récente
URL_DEFAUT = "http://127.0.0.1:8765"
CHEMINS = ("/api/mcp/outils", "/api/mcp/appel")
HOTES_LOCAUX = ("127.0.0.1", "localhost", "::1")
DELAI_S = 120.0
INSTRUCTIONS = ("DeepotusVideo, studio vidéo local. Les outils LISENT la Bibliothèque, la bible et les plans des "
                "Chapitres, les recettes, les revues, les pièces 3D ; deviser_generation chiffre une génération "
                "(gratuit) et rend un jeton ; « lancer » transmet la demande à l'UTILISATEUR, qui l'accepte ou non "
                "dans l'app : aucune dépense ne part sans son clic, et les plafonds de l'app s'appliquent.")


class Refus(Exception):
    pass


def journal(texte: str) -> None:
    try:
        sys.stderr.write(f"[deepotus-mcp] {texte}\n")
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 — un journal perdu ne casse pas le protocole
        pass


def base_url() -> str:
    url = (os.environ.get("DEEPOTUS_URL") or URL_DEFAUT).strip().rstrip("/")
    p = urllib.parse.urlsplit(url)
    if p.scheme != "http" or (p.hostname or "") not in HOTES_LOCAUX or p.path not in ("", "/") or p.query:
        raise Refus(f"DEEPOTUS_URL refusée ({url}) : seule la boucle locale http://127.0.0.1:<port> est permise")
    return f"http://{p.netloc}"


_OUVREUR = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # jamais de proxy, même déclaré


def http(methode: str, chemin: str, corps=None, base: str | None = None):
    """(statut, json) ; lève Refus si le backend est injoignable. Liste blanche de chemins."""
    if chemin not in CHEMINS:
        raise Refus(f"chemin hors liste blanche : {chemin}")
    donnees = None if corps is None else json.dumps(corps, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request((base or base_url()) + chemin, data=donnees, method=methode)
    req.add_header("X-Deepotus-MCP", "1")
    req.add_header("Accept", "application/json")
    if donnees is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with _OUVREUR.open(req, timeout=DELAI_S) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8") or "null")
        except ValueError:
            j = None
        return e.code, j
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Refus("DeepotusVideo ne répond pas sur la boucle locale : lancez l'application, puis réessayez "
                    f"({type(e).__name__})") from None


def _detail(j, statut: int) -> str:
    d = j.get("detail") if isinstance(j, dict) else None
    return d if isinstance(d, str) and d else f"HTTP {statut}"


def outils() -> list:
    statut, j = http("GET", "/api/mcp/outils")
    if statut != 200 or not isinstance(j, dict):
        raise Refus(_detail(j, statut))
    out = []
    for o in j.get("outils") or []:
        if not isinstance(o, dict) or not isinstance(o.get("name"), str):
            continue
        t = {"name": o["name"], "description": str(o.get("description") or ""),
             "inputSchema": o.get("inputSchema") if isinstance(o.get("inputSchema"), dict) else {"type": "object"}}
        a = o.get("annotations")
        if isinstance(a, dict):
            t["annotations"] = a
            if isinstance(a.get("title"), str):
                t["title"] = a["title"]
        out.append(t)
    return out


def appeler(nom, arguments) -> dict:
    """Le résultat MCP d'un appel d'outil (content + structuredContent + isError)."""
    try:
        statut, j = http("POST", "/api/mcp/appel", {"outil": nom, "arguments": arguments or {}})
    except Refus as e:
        return {"content": [{"type": "text", "text": str(e)}], "isError": True}
    if statut != 200 or not isinstance(j, dict):
        return {"content": [{"type": "text", "text": _detail(j, statut)}], "isError": True}
    texte = json.dumps({"resume": j.get("resume"), "donnees": j.get("donnees")}, ensure_ascii=False)
    return {"content": [{"type": "text", "text": texte}],
            "structuredContent": {"ok": bool(j.get("ok")), "resume": j.get("resume"), "donnees": j.get("donnees")},
            "isError": not j.get("ok")}


def _erreur(ident, code: int, message: str, data=None) -> dict:
    e = {"code": code, "message": message}
    if data is not None:
        e["data"] = data
    return {"jsonrpc": "2.0", "id": ident, "error": e}


def traiter(msg) -> dict | None:
    """La réponse à UN message (None pour une notification ou une réponse du client)."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _erreur(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
    methode = msg.get("method")
    ident = msg.get("id")
    if methode is None:                         # une réponse du client (nous n'envoyons aucune requête) : ignorée
        return None
    if not isinstance(methode, str):
        return _erreur(ident, -32600, "Invalid Request")
    notification = "id" not in msg
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
    if notification:
        return None                              # notifications/initialized, cancelled… : rien à rendre
    if methode == "initialize":
        demandee = params.get("protocolVersion")
        version = demandee if demandee in VERSIONS else VERSIONS[0]
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}, "resources": {}, "prompts": {}},
            "serverInfo": {"name": NOM, "title": "DeepotusVideo", "version": VERSION_SERVEUR},
            "instructions": INSTRUCTIONS}}
    if methode == "ping":
        return {"jsonrpc": "2.0", "id": ident, "result": {}}
    if methode == "tools/list":
        try:
            return {"jsonrpc": "2.0", "id": ident, "result": {"tools": outils()}}
        except Refus as e:
            return _erreur(ident, -32603, str(e))
    if methode == "tools/call":
        nom = params.get("name")
        if not isinstance(nom, str) or not nom:
            return _erreur(ident, -32602, "Invalid params: name")
        args = params.get("arguments")
        if args is not None and not isinstance(args, dict):
            return _erreur(ident, -32602, "Invalid params: arguments")
        return {"jsonrpc": "2.0", "id": ident, "result": appeler(nom, args or {})}
    if methode == "resources/list":
        return {"jsonrpc": "2.0", "id": ident, "result": {"resources": []}}
    if methode == "resources/templates/list":
        return {"jsonrpc": "2.0", "id": ident, "result": {"resourceTemplates": []}}
    if methode == "prompts/list":
        return {"jsonrpc": "2.0", "id": ident, "result": {"prompts": []}}
    return _erreur(ident, -32601, f"Method not found: {methode}")


def ecrire(sortie, reponse: dict) -> None:
    ligne = json.dumps(reponse, ensure_ascii=False, separators=(",", ":"))   # json.dumps n'émet aucun saut de ligne brut
    sortie.write((ligne + "\n").encode("utf-8"))
    sortie.flush()


def boucle(entree=None, sortie=None) -> int:
    entree = entree or sys.stdin.buffer
    sortie = sortie or sys.stdout.buffer
    for brut in entree:
        brut = brut.strip()
        if not brut:
            continue
        try:
            msg = json.loads(brut.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            ecrire(sortie, _erreur(None, -32700, "Parse error"))
            continue
        try:
            rep = traiter(msg)
        except Exception as e:  # noqa: BLE001 — jamais un serveur muet : l'erreur revient au client
            journal(f"erreur interne : {type(e).__name__} : {e}")
            rep = _erreur(msg.get("id") if isinstance(msg, dict) else None, -32603, "Internal error")
        if rep is not None:
            ecrire(sortie, rep)
    return 0


def main() -> int:
    try:
        url = base_url()
    except Refus as e:
        journal(str(e))
        return 2
    journal(f"prêt : relais vers {url} (stdio)")
    return boucle()


if __name__ == "__main__":
    sys.exit(main())
