# -*- coding: utf-8 -*-
"""t222 (lot « Menus : Réglages », 16/10/2026) — les FOURNISSEURS LIBRES compatibles OpenAI (DeepSeek, OpenRouter,
Mistral, Groq, Together, xAI… ou tout autre service qui parle l'API OpenAI).

Plan docs/superpowers/plans/2026-10-15-optimisation-menus-reglages.md (ligne t222, Risques). Remontée de
l'utilisateur (15/10) : « Clés d'API : pouvoir ajouter un fournisseur libre ; ses modèles doivent ensuite apparaître
dans les listes de modèles IA de l'application ».

Un fournisseur = un nom, une URL de base (https), une clé et des modèles. Même modèle que les comptes de t203 :
  - la description (nom, base, modèles, modèle par défaut) vit dans `DATA_ROOT/fournisseurs_llm.json`, SANS secret ;
  - la clé vit là où vivent les clés — coffre ouvert, sinon .env — sous `DZF_<ID>_API_KEY` ; un coffre posé mais
    FERMÉ refuse (CoffreVerrouille). Elle n'est JAMAIS relue vers l'écran : la vue dit seulement `cle_posee` ;
  - chaque fournisseur est le moteur de texte `fl:<id>` du registre `moteurs_texte` (Vectorlab, Card Forge, rôles de
    Fournisseurs par défaut, /api/ia/catalogue) : `tirer` = POST {base}/chat/completions, « Lire la liste » et
    « Tester » = GET {base}/models (gratuit).

SORTIE RÉSEAU. Une URL saisie à la main est une sortie réseau : https seulement, ni identifiants ni requête dans
l'URL, et JAMAIS une adresse locale ou privée (localhost, 127.x, 10.x, 192.168.x, fe80::…) — ni écrite, ni obtenue
par la résolution DNS au moment de l'appel (`_hote_public`, refait à chaque requête : un nom public qui se met à
pointer vers le réseau local est refusé). Les serveurs locaux sont l'affaire de t223, pas d'ici. Aucune redirection
n'est suivie.

PRIX. Un fournisseur libre n'a pas de tarif connu : jamais « gratuit ». `pricing.estimate` le chiffre sur une
ESTIMATION par jetons (le tarif Anthropic de la grille, le plus cher des intégrés) pour que les plafonds
s'appliquent ; la ligne porte `a_mesurer` et l'écran dit « prix à mesurer ».

Le paquet d'espace (t210) n'emporte rien d'ici : ce fichier vit hors de `DATA_ROOT/espaces`, il est propre à la
machine.
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

from app.config import DATA_ROOT, SSL_VERIFY

PREFIXE = "fl:"
MAX_FOURNISSEURS = 20
MAX_MODELES = 300
MAX_NOM = 60
_ID = re.compile(r"^[a-z][a-z0-9]{0,23}$")
_MODELE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,159}$")

# Les préréglages de l'écran (URL de base vérifiées le 16/10/2026 sur la documentation de chaque service).
PREREGLAGES = [
    {"id": "deepseek", "nom": "DeepSeek", "base": "https://api.deepseek.com/v1"},
    {"id": "openrouter", "nom": "OpenRouter", "base": "https://openrouter.ai/api/v1"},
    {"id": "mistral", "nom": "Mistral", "base": "https://api.mistral.ai/v1"},
    {"id": "groq", "nom": "Groq", "base": "https://api.groq.com/openai/v1"},
    {"id": "together", "nom": "Together", "base": "https://api.together.xyz/v1"},
    {"id": "xai", "nom": "xAI", "base": "https://api.x.ai/v1"},
]

# Remplacés au banc et par le backend de preuve (faux fournisseur) : jamais dans le code de l'application.
_TRANSPORT: httpx.BaseTransport | None = None
_resoudre = socket.getaddrinfo


class FournisseurInconnu(KeyError):
    """Aucun fournisseur libre de cet id."""


# ── le fichier ──────────────────────────────────────────────────────────────────────────────────────────────────────

def _fichier() -> Path:
    return DATA_ROOT / "fournisseurs_llm.json"


def _lire() -> dict:
    f = _fichier()
    if f.is_file():
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and isinstance(doc.get("fournisseurs"), dict) \
                    and all(_ID.match(k) for k in doc["fournisseurs"]):
                return doc
        except (OSError, ValueError):
            pass
        cote = f.with_name(f"fournisseurs_llm.json.illisible-{datetime.now():%Y%m%d-%H%M%S}")
        f.replace(cote)
        logger.warning(f"fournisseurs_llm.json illisible : mis de côté ({cote.name})")
    return {"fournisseurs": {}}


def _ecrire(doc: dict) -> None:
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


# ── la clé ──────────────────────────────────────────────────────────────────────────────────────────────────────────

def nom_cle(fid: str) -> str:
    """Le nom de la clé (coffre / .env) d'un fournisseur libre : DZF_<ID>_API_KEY."""
    if not _ID.match(fid or ""):
        raise ValueError(f"identifiant de fournisseur invalide : {fid}")
    return f"DZF_{fid.upper()}_API_KEY"


def _cle(fid: str) -> str:
    from app.services import coffre
    n = nom_cle(fid)
    return (os.environ.get(n) or coffre.valeur(n) or "").strip()


def _poser_cle(fid: str, valeur_: str) -> str:
    from app.services import comptes
    return comptes._secret_ecrire(nom_cle(fid), (valeur_ or "").strip())


# ── la validation ───────────────────────────────────────────────────────────────────────────────────────────────────

def _adresse_privee(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return True
    return not a.is_global or a.is_multicast


def verifier_base(url: str) -> str:
    """L'URL de base normalisée (https://hote[:port]/chemin, sans « / » final) ; ValueError sinon."""
    brut = str(url or "").strip()
    try:
        u = urlsplit(brut)
        port = u.port
    except ValueError:
        raise ValueError("URL de base illisible")
    if u.scheme != "https":
        raise ValueError("URL de base : https:// obligatoire")
    hote = (u.hostname or "").lower().rstrip(".")
    if not hote:
        raise ValueError("URL de base illisible")
    if u.username or u.password or u.query or u.fragment:
        raise ValueError("URL de base : ni identifiants, ni paramètres dans l'adresse (la clé a son propre champ)")
    try:
        ipaddress.ip_address(hote.strip("[]"))
        litterale = True
    except ValueError:
        litterale = False
    if hote == "localhost" or hote.endswith((".localhost", ".local", ".internal", ".lan", ".home.arpa")) \
            or "." not in hote and not litterale or litterale and _adresse_privee(hote.strip("[]")):
        raise ValueError("URL de base : adresse locale ou privée refusée ici (les serveurs locaux ont leur encart)")
    hote_ecrit = f"[{hote}]" if ":" in hote else hote
    chemin = re.sub(r"/+$", "", u.path or "")
    return f"https://{hote_ecrit}{':' + str(port) if port else ''}{chemin}"


def _hote_public(base: str) -> None:
    """Refait à CHAQUE appel : le nom doit encore résoudre vers des adresses publiques (ValueError sinon)."""
    u = urlsplit(base)
    try:
        infos = _resoudre(u.hostname, u.port or 443, proto=socket.IPPROTO_TCP)
    except OSError:
        raise ValueError("fournisseur injoignable : nom d'hôte introuvable")
    if not infos or any(_adresse_privee(i[4][0]) for i in infos):
        raise ValueError("URL de base : adresse locale ou privée refusée ici (les serveurs locaux ont leur encart)")


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
        raise ValueError(f"{MAX_MODELES} modèles au plus par fournisseur")
    return out


def _id_neuf(nom: str, pris) -> str:
    base = re.sub(r"[^a-z0-9]", "", nom.lower())
    base = re.sub(r"^[0-9]+", "", base)[:20] or "fournisseur"
    fid, n = base, 2
    while fid in pris:
        fid, n = f"{base}{n}", n + 1
    return fid


# ── la vue (jamais un secret) ───────────────────────────────────────────────────────────────────────────────────────

def _vue(fid: str, e: dict) -> dict:
    mods = list(e.get("modeles") or [])
    defaut = str(e.get("defaut") or "") or (mods[0] if mods else "")
    return {"id": fid, "moteur": PREFIXE + fid, "nom": e.get("nom") or fid, "base": e.get("base") or "",
            "modeles": mods, "defaut": defaut, "cle": nom_cle(fid), "cle_posee": bool(_cle(fid)),
            "cree": e.get("cree") or ""}


def lister() -> list[dict]:
    return [_vue(k, e) for k, e in _lire()["fournisseurs"].items()]


def obtenir(fid: str) -> dict:
    e = _lire()["fournisseurs"].get(fid)
    if e is None:
        raise FournisseurInconnu(fid)
    return _vue(fid, e)


def ids() -> list[str]:
    return list(_lire()["fournisseurs"])


def de_moteur(moteur: str) -> str | None:
    """`fl:<id>` -> id s'il existe, sinon None."""
    m = str(moteur or "")
    if not m.startswith(PREFIXE):
        return None
    fid = m[len(PREFIXE):]
    return fid if fid in _lire()["fournisseurs"] else None


# ── les écritures ───────────────────────────────────────────────────────────────────────────────────────────────────

def _coffre_libre(avec_secret: bool) -> None:
    from app.services import coffre
    if avec_secret and coffre.verrouille():
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le avant d'enregistrer une clé")


def creer(champs: dict) -> dict:
    """{nom, base, cle?, modeles?, defaut?} -> la vue. Tout est vérifié AVANT d'écrire quoi que ce soit."""
    c = champs if isinstance(champs, dict) else {}
    nom = _texte(c.get("nom"))
    if not nom:
        raise ValueError("nom du fournisseur requis")
    base = verifier_base(c.get("base"))
    mods = _modeles(c.get("modeles"))
    defaut = _texte(c.get("defaut"), 160)
    if defaut and defaut not in mods:
        _modeles([defaut])
        mods = [defaut] + mods
    cle = str(c.get("cle") or "").strip()
    doc = _lire()
    if len(doc["fournisseurs"]) >= MAX_FOURNISSEURS:
        raise ValueError(f"{MAX_FOURNISSEURS} fournisseurs libres au plus")
    _coffre_libre(bool(cle))
    fid = _id_neuf(nom, doc["fournisseurs"])
    doc["fournisseurs"][fid] = {"nom": nom, "base": base, "modeles": mods, "defaut": defaut,
                                "cree": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    if cle:
        _poser_cle(fid, cle)
    _ecrire(doc)
    _vider_caches()
    return _vue(fid, doc["fournisseurs"][fid])


def modifier(fid: str, champs: dict) -> dict:
    """nom, base, cle (vide = garder ; `effacer_cle` pour la retirer), modeles, defaut."""
    c = champs if isinstance(champs, dict) else {}
    doc = _lire()
    e = doc["fournisseurs"].get(fid)
    if e is None:
        raise FournisseurInconnu(fid)
    neuf = dict(e)
    if "nom" in c:
        neuf["nom"] = _texte(c.get("nom")) or e.get("nom")
    if "base" in c:
        neuf["base"] = verifier_base(c.get("base"))
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
    _coffre_libre(bool(cle) or effacer)
    if cle:
        _poser_cle(fid, cle)
    elif effacer:
        _poser_cle(fid, "")
    doc["fournisseurs"][fid] = neuf
    _ecrire(doc)
    _vider_caches()
    return _vue(fid, neuf)


def supprimer(fid: str) -> None:
    """Retire le fournisseur ET efface sa clé (coffre posé mais fermé : refus avant tout)."""
    from app.services import coffre
    doc = _lire()
    if fid not in doc["fournisseurs"]:
        raise FournisseurInconnu(fid)
    if coffre.verrouille() and _cle(fid):
        raise coffre.CoffreVerrouille("le coffre est fermé : ouvrez-le pour effacer la clé de ce fournisseur")
    _poser_cle(fid, "")
    doc["fournisseurs"].pop(fid)
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
    return {"Authorization": f"Bearer {cle}", "Content-Type": "application/json"}


def _cause(r: httpx.Response) -> str:
    """La cause d'un refus, NEUTRE de langue (le gabarit du message se traduit), sans jamais recopier ce que le
    fournisseur renvoie : son corps peut citer la clé (« Incorrect API key provided: sk-… »)."""
    return f"HTTP {r.status_code}"


def lire_modeles(base: str, cle: str, *, timeout: float = 8.0) -> list[str]:
    """GET {base}/models (gratuit) -> les ids publiés, triés, texte seulement. ValueError avec la cause sinon."""
    from app.services import moteurs_texte as MT
    from app.services.vector_illustration import _texte_seulement
    base = verifier_base(base)
    if not (cle or "").strip():
        raise ValueError("clé du fournisseur absente")
    _hote_public(base)
    try:
        with _client(timeout) as c:
            r = c.get(base + "/models", headers=_entetes(cle.strip()))
    except httpx.HTTPError as e:
        raise ValueError(f"fournisseur injoignable : {type(e).__name__}")
    if r.status_code != 200:
        raise ValueError(f"le fournisseur a refusé la liste : {_cause(r)}")
    try:
        data = r.json().get("data") or []
    except (ValueError, AttributeError):
        raise ValueError("réponse du fournisseur illisible (pas une liste de modèles OpenAI)")
    ids_ = [str(m.get("id") or "").strip() for m in data if isinstance(m, dict)]
    ids_ = [i for i in _texte_seulement(ids_) if i and _MODELE.match(i) and not MT.ressemble_a_une_cle(i)]
    return sorted(set(ids_))[:MAX_MODELES]


def lire_modeles_de(fid: str, *, timeout: float = 8.0) -> list[str]:
    v = obtenir(fid)
    return lire_modeles(v["base"], _cle(fid), timeout=timeout)


def tester(fid: str) -> dict:
    """« Tester » sans rien dépenser : la liste publiée se lit-elle avec cette clé ? Et le modèle par défaut y est-il ?"""
    v = obtenir(fid)
    if not v["cle_posee"]:
        return {"id": fid, "ok": False, "etat": "sans_cle", "n": 0}
    try:
        publies = lire_modeles(v["base"], _cle(fid))
    except ValueError as e:
        return {"id": fid, "ok": False, "etat": "refus", "n": 0, "cause": str(e)}
    d = v["defaut"]
    return {"id": fid, "ok": True, "etat": "ok", "n": len(publies),
            "defaut_publie": (d in publies) if d and publies else None}


def tirer(fid: str, modele: str, prompt: str, systeme: str = "", max_tokens: int = 4000, *,
          timeout: float = 90.0) -> str:
    """UN appel POST {base}/chat/completions, au modèle demandé — jamais un repli muet (RuntimeError avec la cause)."""
    try:
        v = obtenir(fid)
    except FournisseurInconnu:
        raise RuntimeError(f"fournisseur libre inconnu : {fid}")
    mod = (modele or v["defaut"]).strip()
    if not mod:
        raise RuntimeError(f"aucun modèle pour « {v['nom']} »")
    cle = _cle(fid)
    if not cle:
        raise RuntimeError(f"clé absente pour « {v['nom']} »")
    try:
        _hote_public(v["base"])
    except ValueError as e:
        raise RuntimeError(str(e))
    msgs = ([{"role": "system", "content": systeme}] if systeme else []) + [{"role": "user", "content": prompt}]
    try:
        with _client(timeout) as c:
            r = c.post(v["base"] + "/chat/completions", headers=_entetes(cle),
                       json={"model": mod, "max_tokens": int(max_tokens), "messages": msgs})
    except httpx.HTTPError as e:
        raise RuntimeError(f"{v['nom']} injoignable : {type(e).__name__}")
    if r.status_code != 200:
        raise RuntimeError(f"{v['nom']} : {_cause(r)}")
    try:
        ch = r.json().get("choices") or []
        return str((ch[0].get("message") or {}).get("content") or "") if ch else ""
    except (ValueError, AttributeError, IndexError):
        raise RuntimeError(f"{v['nom']} : réponse illisible")
