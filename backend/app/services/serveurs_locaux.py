# -*- coding: utf-8 -*-
"""t223 (lot « Menus : Réglages », 16/10/2026) — les SERVEURS DE LLM LOCAUX : plusieurs, plus un seul Ollama.

Plan docs/superpowers/plans/2026-10-15-optimisation-menus-reglages.md (relevé ligne 4, ligne t223, Risques).
Remontée de l'utilisateur (15/10) : « LLM local : pouvoir ajouter d'autres lignes de serveur (URL), pas un seul
Ollama ». Avant : un seul couple `OLLAMA_URL` / `OLLAMA_MODEL`, et l'API Ollama native seulement ; LM Studio,
llama.cpp et vLLM parlent l'API OpenAI.

Un serveur = une URL, un TYPE et un modèle :
  - `ollama` : l'API Ollama native (GET {url}/api/tags, POST {url}/api/chat) ;
  - `openai` : un serveur compatible OpenAI (LM Studio, llama.cpp, vLLM : GET {url}/models,
    POST {url}/chat/completions ; une URL sans chemin reçoit « /v1 »). Une clé est possible (vLLM --api-key) : même
    modèle que t222, au coffre ou au .env sous `DZL_<ID>_API_KEY`, jamais relue (la vue dit `cle_posee`).
La description vit dans `DATA_ROOT/serveurs_locaux.json`, SANS secret ; chaque serveur est le moteur de texte
`local:<id>` du registre `moteurs_texte`, dans les mêmes listes que les fournisseurs libres `fl:<id>`.

MIGRATION. Le couple `OLLAMA_URL` / `OLLAMA_MODEL` devient la PREMIÈRE LIGNE de la liste, LUE telle quelle (rien
n'est réécrit, ni au .env ni ailleurs) : le moteur `ollama` garde son id, l'encart d'origine le règle toujours, et
les ids intégrés ne changent pas. Cette ligne ne se supprime pas (moteur intégré) ; ses modèles se lisent et elle se
teste comme les autres.

SORTIE RÉSEAU. Ici SEULEMENT, la boucle locale et le réseau privé sont permis — et ils sont EXIGÉS : un serveur local
n'a rien à faire sur une adresse publique (c'est alors un fournisseur libre, https, dans son encart). http ou https,
ni identifiants, ni requête, ni fragment dans l'URL ; jamais une adresse de lien local (169.254.x : métadonnées
d'un nuage), « non spécifiée » ou multicast. La résolution DNS est REFAITE à chaque appel (`_hote_local`) : un nom
qui se met à pointer vers une adresse publique est refusé. Aucune redirection n'est suivie. La garde de
`fournisseurs_llm` (`_adresse_privee`, refusante) n'est PAS touchée : cet assouplissement vit dans ce module seul.

PRIX. Un serveur local est GRATUIT (comme Ollama dans pricing.estimate) : c'est ce qui le distingue de `fl:*`.
Le paquet d'espace (t210) n'emporte rien d'ici : propre à la machine.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from loguru import logger

from app.config import DATA_ROOT, SSL_VERIFY, settings

PREFIXE = "local:"
PREMIERE = "ollama"                 # la première ligne : le couple OLLAMA_URL / OLLAMA_MODEL, moteur intégré `ollama`
TYPES = ("ollama", "openai")
MAX_SERVEURS = 20
MAX_MODELES = 300
MAX_NOM = 60
_ID = re.compile(r"^[a-z][a-z0-9]{0,23}$")
_MODELE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,159}$")

# Les préréglages de l'écran (ports par défaut documentés de chaque logiciel, relevés le 16/10/2026).
PREREGLAGES = [
    {"id": "ollama", "nom": "Ollama", "type": "ollama", "url": "http://127.0.0.1:11434"},
    {"id": "lmstudio", "nom": "LM Studio", "type": "openai", "url": "http://127.0.0.1:1234/v1"},
    {"id": "llamacpp", "nom": "llama.cpp", "type": "openai", "url": "http://127.0.0.1:8080/v1"},
    {"id": "vllm", "nom": "vLLM", "type": "openai", "url": "http://127.0.0.1:8000/v1"},
]

# Remplacés au banc et par le backend de preuve (faux serveurs) : jamais dans le code de l'application.
_TRANSPORT: httpx.BaseTransport | None = None
_resoudre = socket.getaddrinfo


class ServeurInconnu(KeyError):
    """Aucun serveur local de cet id."""


# ── le fichier ──────────────────────────────────────────────────────────────────────────────────────────────────────

def _fichier() -> Path:
    return DATA_ROOT / "serveurs_locaux.json"


def _lire() -> dict:
    f = _fichier()
    if f.is_file():
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and isinstance(doc.get("serveurs"), dict) \
                    and all(_ID.match(k) and k != PREMIERE for k in doc["serveurs"]):
                return doc
        except (OSError, ValueError):
            pass
        cote = f.with_name(f"serveurs_locaux.json.illisible-{datetime.now():%Y%m%d-%H%M%S}")
        f.replace(cote)
        logger.warning(f"serveurs_locaux.json illisible : mis de côté ({cote.name})")
    return {"serveurs": {}}


def _ecrire(doc: dict) -> None:
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


# ── la clé (serveur compatible OpenAI seulement, facultative) ───────────────────────────────────────────────────────

def nom_cle(sid: str) -> str:
    """Le nom de la clé (coffre / .env) d'un serveur local : DZL_<ID>_API_KEY."""
    if not _ID.match(sid or ""):
        raise ValueError(f"identifiant de serveur invalide : {sid}")
    return f"DZL_{sid.upper()}_API_KEY"


def _cle(sid: str) -> str:
    from app.services import coffre
    n = nom_cle(sid)
    return (os.environ.get(n) or coffre.valeur(n) or "").strip()


def _poser_cle(sid: str, valeur_: str) -> str:
    from app.services import comptes
    return comptes._secret_ecrire(nom_cle(sid), (valeur_ or "").strip())


# ── la validation ───────────────────────────────────────────────────────────────────────────────────────────────────

def _adresse_locale(ip: str) -> bool:
    """Boucle locale ou réseau privé — jamais lien local (169.254.x, fe80::), non spécifiée ni multicast."""
    try:
        a = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return False
    if a.is_loopback:
        return True
    if a.is_link_local or a.is_unspecified or a.is_multicast or a.is_reserved:
        return False
    return a.is_private


def verifier_url(url: str, type_: str) -> str:
    """L'URL normalisée (http(s)://hote[:port]/chemin, sans « / » final ; « /v1 » ajouté à un serveur compatible
    OpenAI sans chemin) ; ValueError sinon."""
    if type_ not in TYPES:
        raise ValueError("type de serveur inconnu (ollama ou openai)")
    brut = str(url or "").strip()
    try:
        u = urlsplit(brut)
        port = u.port
    except ValueError:
        raise ValueError("URL du serveur illisible")
    if u.scheme not in ("http", "https"):
        raise ValueError("URL du serveur : http:// ou https:// obligatoire")
    hote = (u.hostname or "").lower().rstrip(".")
    if not hote:
        raise ValueError("URL du serveur illisible")
    if u.username or u.password or u.query or u.fragment:
        raise ValueError("URL du serveur : ni identifiants, ni paramètres dans l'adresse")
    try:
        ipaddress.ip_address(hote.strip("[]"))
        litterale = True
    except ValueError:
        litterale = False
    if litterale and not _adresse_locale(hote.strip("[]")):
        raise ValueError("URL du serveur : adresse publique refusée ici (un service en ligne est un fournisseur libre)")
    hote_ecrit = f"[{hote}]" if ":" in hote else hote
    chemin = re.sub(r"/+$", "", u.path or "")
    if type_ == "openai" and not chemin:
        chemin = "/v1"
    return f"{u.scheme}://{hote_ecrit}{':' + str(port) if port else ''}{chemin}"


def _hote_local(url: str) -> None:
    """Refait à CHAQUE appel : le nom doit encore résoudre vers la boucle locale ou le réseau privé."""
    u = urlsplit(url)
    try:
        infos = _resoudre(u.hostname, u.port or (443 if u.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except OSError:
        raise ValueError("serveur injoignable : nom d'hôte introuvable")
    if not infos or not all(_adresse_locale(i[4][0]) for i in infos):
        raise ValueError("URL du serveur : adresse publique refusée ici (un service en ligne est un fournisseur libre)")


def _texte(v, n=MAX_NOM) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", "", str(v or "")).strip()[:n]


def _modeles(v) -> list[str]:
    """Une liste de noms de modèles : liste, ou texte séparé par des virgules / retours. Dédoublonnée, ordre gardé ;
    un nom qui ressemble à une clé est refusé (ValueError)."""
    from app.services import moteurs_texte as MT
    brut = v if isinstance(v, list) else re.split(r"[,\n;]", str(v or ""))
    out: list[str] = []
    for x in brut:
        s = str(x or "").strip()
        if not s:
            continue
        if MT.ressemble_a_une_cle(s):
            raise ValueError("un nom de modèle ressemble à une clé d'API")
        if not _MODELE.match(s):
            raise ValueError(f"nom de modèle invalide : {s[:40]}")
        if s not in out:
            out.append(s)
    if len(out) > MAX_MODELES:
        raise ValueError(f"{MAX_MODELES} modèles au plus par serveur")
    return out


def _id_neuf(nom: str, pris) -> str:
    base = re.sub(r"[^a-z0-9]", "", nom.lower())
    base = re.sub(r"^[0-9]+", "", base)[:20] or "serveur"
    sid, n = base, 2
    while sid in pris or sid == PREMIERE:
        sid, n = f"{base}{n}", n + 1
    return sid


def _nom_par_defaut(url: str, type_: str) -> str:
    u = urlsplit(url)
    return f"{'Ollama' if type_ == 'ollama' else 'OpenAI'} {u.hostname}{':' + str(u.port) if u.port else ''}"


# ── la vue (jamais un secret) ───────────────────────────────────────────────────────────────────────────────────────

def _premiere() -> dict:
    """La première ligne : OLLAMA_URL / OLLAMA_MODEL lus TELS QUELS (un modèle qui contient une clé n'est pas montré)."""
    from app.services import moteurs_texte as MT
    defaut = MT.modele_sain(PREMIERE)
    return {"id": PREMIERE, "moteur": PREMIERE, "nom": "Ollama", "type": "ollama",
            "url": str(settings.OLLAMA_URL or ""), "modeles": [defaut] if defaut else [], "defaut": defaut,
            "cle": "", "cle_posee": False, "integre": True, "fautif": MT.modele_fautif(PREMIERE), "cree": ""}


def _vue(sid: str, e: dict) -> dict:
    mods = list(e.get("modeles") or [])
    defaut = str(e.get("defaut") or "") or (mods[0] if mods else "")
    t = e.get("type") if e.get("type") in TYPES else "ollama"
    return {"id": sid, "moteur": PREFIXE + sid, "nom": e.get("nom") or sid, "type": t, "url": e.get("url") or "",
            "modeles": mods, "defaut": defaut, "cle": nom_cle(sid) if t == "openai" else "",
            "cle_posee": bool(t == "openai" and _cle(sid)), "integre": False, "fautif": False,
            "cree": e.get("cree") or ""}


def lister() -> list[dict]:
    """La première ligne (Ollama intégré), puis les serveurs ajoutés dans l'ordre de leur création."""
    return [_premiere()] + [_vue(k, e) for k, e in _lire()["serveurs"].items()]


def obtenir(sid: str) -> dict:
    if sid == PREMIERE:
        return _premiere()
    e = _lire()["serveurs"].get(sid)
    if e is None:
        raise ServeurInconnu(sid)
    return _vue(sid, e)


def ids() -> list[str]:
    """Les serveurs AJOUTÉS (la première ligne est le moteur intégré `ollama`, hors de cette liste)."""
    return list(_lire()["serveurs"])


def de_moteur(moteur: str) -> str | None:
    """`local:<id>` -> id s'il existe, sinon None."""
    m = str(moteur or "")
    if not m.startswith(PREFIXE):
        return None
    sid = m[len(PREFIXE):]
    return sid if sid in _lire()["serveurs"] else None


# ── les écritures ───────────────────────────────────────────────────────────────────────────────────────────────────

def _coffre_libre(avec_secret: bool) -> None:
    from app.services import coffre
    if avec_secret and coffre.verrouille():
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le avant d'enregistrer une clé")


def _pas_la_premiere(sid: str) -> None:
    if sid == PREMIERE:
        raise ValueError("la première ligne (Ollama intégré) se règle dans l'encart « LLM local » ci-dessus")


def creer(champs: dict) -> dict:
    """{url, type, nom?, cle?, modeles?, defaut?} -> la vue. Tout est vérifié AVANT d'écrire quoi que ce soit."""
    c = champs if isinstance(champs, dict) else {}
    type_ = str(c.get("type") or "ollama").strip().lower()
    url = verifier_url(c.get("url"), type_)
    nom = _texte(c.get("nom")) or _nom_par_defaut(url, type_)
    mods = _modeles(c.get("modeles"))
    defaut = _texte(c.get("defaut"), 160)
    if defaut and defaut not in mods:
        _modeles([defaut])
        mods = [defaut] + mods
    cle = str(c.get("cle") or "").strip()
    if cle and type_ != "openai":
        raise ValueError("clé : seulement pour un serveur compatible OpenAI")
    doc = _lire()
    if len(doc["serveurs"]) >= MAX_SERVEURS:
        raise ValueError(f"{MAX_SERVEURS} serveurs locaux au plus")
    _coffre_libre(bool(cle))
    sid = _id_neuf(nom, doc["serveurs"])
    doc["serveurs"][sid] = {"nom": nom, "type": type_, "url": url, "modeles": mods, "defaut": defaut,
                            "cree": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    if cle:
        _poser_cle(sid, cle)
    _ecrire(doc)
    _vider_caches()
    return _vue(sid, doc["serveurs"][sid])


def modifier(sid: str, champs: dict) -> dict:
    """nom, url (le type ne change pas), cle (vide = garder ; `effacer_cle` pour la retirer), modeles, defaut."""
    _pas_la_premiere(sid)
    c = champs if isinstance(champs, dict) else {}
    doc = _lire()
    e = doc["serveurs"].get(sid)
    if e is None:
        raise ServeurInconnu(sid)
    neuf = dict(e)
    if "nom" in c:
        neuf["nom"] = _texte(c.get("nom")) or e.get("nom")
    if "url" in c:
        neuf["url"] = verifier_url(c.get("url"), neuf.get("type") or "ollama")
    if "modeles" in c:
        neuf["modeles"] = _modeles(c.get("modeles"))
    if "defaut" in c:
        d = _texte(c.get("defaut"), 160)
        if d:
            _modeles([d])
            if d not in (neuf.get("modeles") or []):
                neuf["modeles"] = [d] + list(neuf.get("modeles") or [])
        neuf["defaut"] = d
    cle = str(c.get("cle") or "").strip()
    effacer = c.get("effacer_cle") is True
    if cle and neuf.get("type") != "openai":
        raise ValueError("clé : seulement pour un serveur compatible OpenAI")
    _coffre_libre(bool(cle) or effacer)
    if cle:
        _poser_cle(sid, cle)
    elif effacer:
        _poser_cle(sid, "")
    doc["serveurs"][sid] = neuf
    _ecrire(doc)
    _vider_caches()
    return _vue(sid, neuf)


def supprimer(sid: str) -> None:
    """Retire le serveur ET efface sa clé éventuelle (coffre posé mais fermé : refus avant tout)."""
    from app.services import coffre
    _pas_la_premiere(sid)
    doc = _lire()
    if sid not in doc["serveurs"]:
        raise ServeurInconnu(sid)
    if coffre.verrouille() and _cle(sid):
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le pour effacer la clé de ce serveur")
    _poser_cle(sid, "")
    doc["serveurs"].pop(sid)
    _ecrire(doc)
    _vider_caches()


def _vider_caches() -> None:
    try:
        from app.services import vector_illustration as VI
        VI._CATALOGUE.clear()
    except Exception:  # noqa: BLE001
        pass


# ── le réseau ───────────────────────────────────────────────────────────────────────────────────────────────────────

def _client(timeout: float) -> httpx.Client:
    return httpx.Client(transport=_TRANSPORT, timeout=timeout, verify=SSL_VERIFY, follow_redirects=False)


def _entetes(cle: str) -> dict:
    h = {"Content-Type": "application/json"}
    if cle:
        h["Authorization"] = f"Bearer {cle}"
    return h


def _cause(r: httpx.Response) -> str:
    """La cause d'un refus, NEUTRE de langue, sans recopier le corps du serveur (il peut citer la clé)."""
    return f"HTTP {r.status_code}"


def lire_modeles(url: str, type_: str, cle: str = "", *, timeout: float = 8.0) -> list[str]:
    """Ollama : GET {url}/api/tags ; OpenAI : GET {url}/models. Les noms publiés, texte seulement, triés.
    ValueError avec la cause sinon. Gratuit (rien n'est généré)."""
    from app.services import moteurs_texte as MT
    from app.services.vector_illustration import _texte_seulement
    url = verifier_url(url, type_)
    if (cle or "").strip() and type_ != "openai":
        raise ValueError("clé : seulement pour un serveur compatible OpenAI")
    _hote_local(url)
    chemin = "/api/tags" if type_ == "ollama" else "/models"
    try:
        with _client(timeout) as c:
            r = c.get(url + chemin, headers=_entetes((cle or "").strip()))
    except httpx.HTTPError as e:
        raise ValueError(f"serveur injoignable : {type(e).__name__}")
    if r.status_code != 200:
        raise ValueError(f"le serveur a refusé la liste : {_cause(r)}")
    try:
        corps = r.json()
        if type_ == "ollama":
            noms = [str(m.get("name") or m.get("model") or "").strip() for m in corps.get("models") or []
                    if isinstance(m, dict)]
        else:
            noms = [str(m.get("id") or "").strip() for m in corps.get("data") or [] if isinstance(m, dict)]
    except (ValueError, AttributeError):
        raise ValueError("réponse du serveur illisible (pas une liste de modèles)")
    noms = [n for n in _texte_seulement(noms) if n and _MODELE.match(n) and not MT.ressemble_a_une_cle(n)]
    return sorted(set(noms))[:MAX_MODELES]


def lire_modeles_de(sid: str, *, timeout: float = 8.0) -> list[str]:
    v = obtenir(sid)
    return lire_modeles(v["url"], v["type"], "" if v["integre"] else _cle(sid), timeout=timeout)


def tester(sid: str) -> dict:
    """« Tester » sans rien générer : la liste des modèles se lit-elle ? Et le modèle par défaut y est-il ?"""
    v = obtenir(sid)
    try:
        publies = lire_modeles_de(sid)
    except ValueError as e:
        return {"id": sid, "ok": False, "etat": "refus", "n": 0, "cause": str(e)}
    d = v["defaut"]
    return {"id": sid, "ok": True, "etat": "ok", "n": len(publies),
            "defaut_publie": (d in publies) if d and publies else None}


def tirer(sid: str, modele: str, prompt: str, systeme: str = "", max_tokens: int = 4000, *,
          timeout: float = 180.0) -> str:
    """UN appel au serveur, au modèle demandé — jamais un repli muet (RuntimeError avec la cause).
    Ollama : POST {url}/api/chat (stream false) ; OpenAI : POST {url}/chat/completions."""
    try:
        v = obtenir(sid)
    except ServeurInconnu:
        raise RuntimeError(f"serveur local inconnu : {sid}")
    mod = (modele or v["defaut"]).strip()
    if not mod:
        raise RuntimeError(f"aucun modèle pour « {v['nom']} »")
    try:
        _hote_local(v["url"])
    except ValueError as e:
        raise RuntimeError(str(e))
    msgs = ([{"role": "system", "content": systeme}] if systeme else []) + [{"role": "user", "content": prompt}]
    if v["type"] == "ollama":
        chemin, corps = "/api/chat", {"model": mod, "messages": msgs, "stream": False,
                                      "options": {"num_predict": int(max_tokens)}}
    else:
        chemin, corps = "/chat/completions", {"model": mod, "max_tokens": int(max_tokens), "messages": msgs}
    try:
        with _client(timeout) as c:
            r = c.post(v["url"] + chemin, headers=_entetes("" if v["integre"] else _cle(sid)), json=corps)
    except httpx.HTTPError as e:
        raise RuntimeError(f"{v['nom']} injoignable : {type(e).__name__}")
    if r.status_code != 200:
        raise RuntimeError(f"{v['nom']} : {_cause(r)}")
    try:
        j = r.json()
        if v["type"] == "ollama":
            return str((j.get("message") or {}).get("content") or "")
        ch = j.get("choices") or []
        return str((ch[0].get("message") or {}).get("content") or "") if ch else ""
    except (ValueError, AttributeError, IndexError):
        raise RuntimeError(f"{v['nom']} : réponse illisible")
