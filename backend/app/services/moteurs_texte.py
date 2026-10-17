"""Le registre des MOTEURS DE TEXTE (t220, lot « Menus : Réglages », 16/10/2026) — amorcé.

Plan docs/superpowers/plans/2026-10-15-optimisation-menus-reglages.md (section Architecture). Ce module est le seul
endroit qui dit quels moteurs de texte existent, quelle clé les ouvre et quel réglage porte leur modèle par défaut.
Aujourd'hui : les quatre intégrés (`anthropic`, `openai`, `gemini`, `ollama`, ids inchangés : les choix déjà
enregistrés gardent leur sens). t222 (16/10) y ajoute les fournisseurs libres compatibles OpenAI : le moteur `fl:<id>`
(services/fournisseurs_llm.py), dans `tous()` après les intégrés ; `MOTEURS` reste la liste des intégrés seuls.
t223 (16/10) y ajoute les serveurs de LLM locaux (services/serveurs_locaux.py) : le moteur `local:<id>`, après les
fournisseurs libres ; la première ligne de ces serveurs est le couple OLLAMA_URL / OLLAMA_MODEL, c'est-à-dire le
moteur intégré `ollama` lui-même (id inchangé).

LA GARDE. Relevé du 15/10 sur la machine de l'utilisateur : `GEMINI_MODEL` contenait une CLÉ (`AIza…`, la même que
`GEMINI_API_KEY`), parce que Clés d'API présentait ce réglage comme un champ de clé. Chaque appel de texte Gemini
partait alors vers `models/AIza…:generateContent` : il échouait, et la clé était écrite dans une URL. Désormais :
  - `ressemble_a_une_cle(v)` reconnaît une clé collée à la place d'un nom de modèle ;
  - toute écriture d'un `*_MODEL` qui y ressemble est refusée (400, `verifier_modele`) ;
  - une valeur déjà fautive n'est JAMAIS effacée toute seule, mais elle n'est jamais relue non plus : `modele_sain`
    rend "" (l'écran et le Diagnostic la signalent ; les appels retombent sur le défaut du code).

L'APPEL (t232, lot « Studio : Animation », 17/10/2026). `tirer(moteur, modele, prompt, systeme, max_tokens, json)` est
extrait de `vector_illustration.tirer` (qui l'appelle désormais, sans changement de comportement) pour servir hors
Vectorlab — d'abord le chorégraphe du nœud Animation (t234). UN appel, au moteur ET au modèle demandés, jamais un
repli muet. `tirer_garde` ajoute ce que les routes payantes font avant de dépenser : l'estimation (`estimer`) puis la
garde des plafonds (`plafonds.verifier`), AVANT l'appel. `json=True` demande un document JSON (mode natif quand le
moteur en a un) et rend l'objet extrait — une DONNÉE, jamais évaluée.
"""
from __future__ import annotations

import json as _json
import re

import httpx

from app.config import SSL_VERIFY, settings

MOTEURS = ("anthropic", "openai", "gemini", "ollama")

NOMS = {"anthropic": "Anthropic", "openai": "OpenAI", "gemini": "Google Gemini", "ollama": "Ollama"}

# le réglage (.env) qui porte le modèle par défaut de chaque moteur
CLE_MODELE = {"anthropic": "ANTHROPIC_MODEL", "openai": "OPENAI_MODEL",
              "gemini": "GEMINI_MODEL", "ollama": "OLLAMA_MODEL"}

# le réglage qui rend le moteur utilisable (pour Ollama, local : le modèle EST la clé)
CLE_ACCES = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
             "gemini": "GEMINI_API_KEY", "ollama": "OLLAMA_MODEL"}

ALERTE_CLE = "contient une clé, pas un nom de modèle"

_PREFIXES_CLE = ("AIza", "sk-", "msy_")


def ressemble_a_une_cle(valeur: str | None) -> bool:
    """Une clé collée à la place d'un nom de modèle : préfixe connu (`AIza` Google, `sk-` OpenAI/Anthropic, `msy_`
    Meshy), ou plus de 30 caractères sans `-`, `.` ni `:` (aucun nom de modèle publié n'a cette forme :
    `claude-haiku-4-5-20251001`, `gpt-4o-mini`, `gemini-flash-latest`, `qwen2.5:14b-instruct`)."""
    v = (valeur or "").strip()
    if not v:
        return False
    if v.startswith(_PREFIXES_CLE):
        return True
    return len(v) > 30 and not any(c in v for c in "-.:")


def verifier_modele(nom_cle: str, valeur: str | None) -> None:
    """Lève ValueError si `valeur` écrite dans un réglage `*_MODEL` ressemble à une clé."""
    if nom_cle.endswith("_MODEL") and ressemble_a_une_cle(valeur):
        raise ValueError(f"{nom_cle} : cette valeur ressemble à une clé d'API, pas à un nom de modèle")


def libres() -> list[str]:
    """t222 : les moteurs `fl:<id>` des fournisseurs libres, dans l'ordre de leur création."""
    from app.services import fournisseurs_llm as FL
    return [FL.PREFIXE + i for i in FL.ids()]


def locaux() -> list[str]:
    """t223 : les moteurs `local:<id>` des serveurs locaux ajoutés, dans l'ordre de leur création."""
    from app.services import serveurs_locaux as SL
    return [SL.PREFIXE + i for i in SL.ids()]


def tous() -> list[str]:
    """Tous les moteurs de texte connus : les intégrés d'abord (ids inchangés), puis les fournisseurs libres, puis
    les serveurs locaux (t223)."""
    return list(MOTEURS) + libres() + locaux()


def est_libre(moteur: str) -> bool:
    return str(moteur or "").startswith("fl:")


def est_local(moteur: str) -> bool:
    """t223 : un serveur local ajouté (`local:<id>`) — gratuit, comme `ollama`."""
    return str(moteur or "").startswith("local:")


def connu(moteur: str) -> bool:
    return moteur in MOTEURS or moteur in libres() or moteur in locaux()


def _libre(moteur: str) -> dict | None:
    from app.services import fournisseurs_llm as FL
    fid = FL.de_moteur(moteur)
    return FL.obtenir(fid) if fid else None


def _local(moteur: str) -> dict | None:
    from app.services import serveurs_locaux as SL
    sid = SL.de_moteur(moteur)
    return SL.obtenir(sid) if sid else None


def nom(moteur: str) -> str:
    if moteur in NOMS:
        return NOMS[moteur]
    if est_local(moteur):
        v = _local(moteur)
        return v["nom"] if v else str(moteur or "")
    v = _libre(moteur) if est_libre(moteur) else None
    return v["nom"] if v else str(moteur or "")


def modele_brut(moteur: str) -> str:
    if est_local(moteur):
        v = _local(moteur)
        return str((v or {}).get("defaut") or "").strip()
    if est_libre(moteur):
        v = _libre(moteur)
        return str((v or {}).get("defaut") or "").strip()
    cle = CLE_MODELE.get(moteur)
    return str(getattr(settings, cle, "") or "").strip() if cle else ""


def modele_fautif(moteur: str) -> bool:
    return ressemble_a_une_cle(modele_brut(moteur))


def modele_sain(moteur: str) -> str:
    """Le modèle par défaut, ou "" s'il contient une clé (jamais relu, jamais affiché, jamais mis dans une URL)."""
    v = modele_brut(moteur)
    return "" if ressemble_a_une_cle(v) else v


def configure(moteur: str) -> bool:
    if est_local(moteur):         # t223 : un serveur local est prêt dès qu'il a un modèle (clé facultative)
        v = _local(moteur)
        return bool(v and (v["defaut"] or v["modeles"]))
    if est_libre(moteur):
        v = _libre(moteur)
        return bool(v and v["cle_posee"] and (v["defaut"] or v["modeles"]))
    cle = CLE_ACCES.get(moteur)
    return bool(cle and str(getattr(settings, cle, "") or "").strip())


def etat() -> list[dict]:
    """Une ligne par moteur : configuré ou non, le réglage du modèle, le modèle (sain) et l'alerte éventuelle."""
    out = []
    for m in MOTEURS:
        fautif = modele_fautif(m)
        out.append({"moteur": m, "nom": NOMS[m], "configure": configure(m), "cle_modele": CLE_MODELE[m],
                    "modele": modele_sain(m), "fautif": fautif, "alerte": ALERTE_CLE if fautif else ""})
    for m in libres():          # t222 : le modèle par défaut d'un fournisseur libre vit dans fournisseurs_llm.json
        out.append({"moteur": m, "nom": nom(m), "configure": configure(m), "cle_modele": m,
                    "modele": modele_sain(m), "fautif": False, "alerte": "", "libre": True})
    for m in locaux():          # t223 : le modèle par défaut d'un serveur local vit dans serveurs_locaux.json
        out.append({"moteur": m, "nom": nom(m), "configure": configure(m), "cle_modele": m,
                    "modele": modele_sain(m), "fautif": False, "alerte": "", "local": True})
    return out


# ── l'appel (t232) ────────────────────────────────────────────────────────────────────────────────────────────────

def nature_cout(moteur: str) -> str:
    """La bulle de coût de `mod-ia.js` (t224) : un serveur local est « gratuit », un fournisseur libre n'a pas de tarif
    connu (« a_mesurer », jamais gratuit), un intégré est « payant »."""
    if moteur == "ollama" or est_local(moteur):
        return "gratuit"
    return "a_mesurer" if est_libre(moteur) else "payant"


def estimer(moteur: str, prompt: str, systeme: str = "", max_tokens: int = 4000) -> dict:
    """L'op d'estimation d'UN appel, au moteur choisi : ~4 caractères par jeton en entrée, `max_tokens` en sortie (le
    pire cas). `pricing.estimate` la chiffre : 0 pour un local, tarif Anthropic + `a_mesurer` pour un fl."""
    from app.services import plafonds as _PLAF
    n = len(prompt or "") + len(systeme or "")
    return _PLAF.op_llm(-(-n // 4), int(max_tokens), str(moteur or ""))


CONSIGNE_JSON = "Réponds UNIQUEMENT par un document JSON valide, sans texte autour."
MAX_JSON = 200_000                          # caractères : au-delà, la réponse n'est pas lue


def extraire_json(texte: str):
    """Le premier document JSON (objet ou tableau) d'une réponse : seul, dans un bloc ```json, ou entouré de texte.
    `json.loads` seulement — rien n'est jamais évalué. RuntimeError si aucun, ou si la réponse est trop longue."""
    t = str(texte or "").strip()
    if len(t) > MAX_JSON:
        raise RuntimeError("réponse JSON trop longue")
    bloc = re.search(r"```(?:json)?\s*(.*?)```", t, re.S | re.I)
    dec = _json.JSONDecoder()
    for cand in ([bloc.group(1).strip()] if bloc else []) + [t]:
        try:
            v = _json.loads(cand)
        except ValueError:
            v = None
        if isinstance(v, (dict, list)):
            return v
        essais = 0
        for i, ch in enumerate(cand):
            if ch not in "{[":
                continue
            essais += 1
            if essais > 50:
                break
            try:
                v, _ = dec.raw_decode(cand, i)
            except ValueError:
                continue
            if isinstance(v, (dict, list)):
                return v
    raise RuntimeError("réponse illisible : aucun document JSON")


def tirer(moteur: str, modele: str, prompt: str, systeme: str, max_tokens: int = 4000, json: bool = False, *,
          timeout: float = 90.0):
    """UN appel, au moteur ET au modèle demandés — jamais un repli muet.

    Lève `RuntimeError` avec la cause : l'écran vient d'afficher le nom du modèle qui va dépenser la clé, un repli
    silencieux le ferait mentir. Le modèle vide prend `modele_sain` ; un modèle qui ressemble à une clé est refusé avant
    tout envoi (il finirait dans une URL ou un corps de requête). `json=True` : rend l'objet (`extraire_json`).
    Aucune garde de dépense ici : c'est `tirer_garde`, ou la route appelante (le Vectorlab a la sienne).
    """
    mod = (modele or modele_sain(moteur)).strip()
    if not mod:
        raise RuntimeError(f"aucun modèle pour « {moteur} »")
    if ressemble_a_une_cle(mod):
        raise RuntimeError(f"le modèle demandé pour « {moteur} » ressemble à une clé d'API, pas à un nom de modèle")
    if json:
        systeme = f"{systeme}\n\n{CONSIGNE_JSON}" if systeme else CONSIGNE_JSON
    txt = _appeler(moteur, mod, prompt, systeme, max_tokens, json, timeout)
    return extraire_json(txt) if json else txt


def _appeler(moteur: str, mod: str, prompt: str, systeme: str, max_tokens: int, json: bool, timeout: float) -> str:
    if moteur.startswith("fl:"):            # t222 : POST {base}/chat/completions du fournisseur libre
        from app.services import fournisseurs_llm as _FL
        fid = _FL.de_moteur(moteur)
        if not fid:
            raise RuntimeError(f"moteur inconnu : {moteur}")
        return _FL.tirer(fid, mod, prompt, systeme, max_tokens, timeout=timeout)
    if moteur.startswith("local:"):         # t223 : le serveur local (Ollama natif ou compatible OpenAI)
        from app.services import serveurs_locaux as _SL
        sid = _SL.de_moteur(moteur)
        if not sid:
            raise RuntimeError(f"moteur inconnu : {moteur}")
        return _SL.tirer(sid, mod, prompt, systeme, max_tokens, timeout=max(timeout, 180.0))
    if moteur == "anthropic":
        body = {"model": mod, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]}
        if systeme:
            body["system"] = systeme
        r = httpx.post("https://api.anthropic.com/v1/messages",
                       headers={"x-api-key": settings.ANTHROPIC_API_KEY,
                                "anthropic-version": "2023-06-01",
                                "content-type": "application/json"},
                       json=body, timeout=timeout, verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"Anthropic HTTP {r.status_code} — "
                               f"{r.text[:200]}")
        return "".join(b.get("text", "") for b in (r.json().get("content") or [])
                       if b.get("type") == "text")
    if moteur == "openai":
        msgs = ([{"role": "system", "content": systeme}] if systeme else []) \
            + [{"role": "user", "content": prompt}]
        body = {"model": mod, "max_tokens": max_tokens, "messages": msgs}
        if json:
            body["response_format"] = {"type": "json_object"}
        r = httpx.post("https://api.openai.com/v1/chat/completions",
                       headers={"Authorization":
                                f"Bearer {settings.OPENAI_API_KEY}",
                                "Content-Type": "application/json"},
                       json=body,
                       timeout=timeout, verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"OpenAI HTTP {r.status_code} — {r.text[:200]}")
        ch = r.json().get("choices") or []
        return (ch[0].get("message", {}).get("content", "") if ch else "")
    if moteur == "gemini":
        from app.services.gemini_llm import _headers
        from app.services.google_video import GOOGLE_API_BASE
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens}}
        if json:
            body["generationConfig"]["responseMimeType"] = "application/json"
        if systeme:
            body["systemInstruction"] = {"parts": [{"text": systeme}]}
        r = httpx.post(f"{GOOGLE_API_BASE}/models/{mod}:generateContent",
                       headers=_headers(), json=body, timeout=timeout,
                       verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"Gemini HTTP {r.status_code} — {r.text[:200]}")
        cand = r.json().get("candidates") or []
        parts = (cand[0].get("content", {}).get("parts", []) if cand else [])
        return "".join(p.get("text", "") for p in parts)
    if moteur == "ollama":
        body = {"model": mod, "prompt": prompt, "system": systeme, "stream": False}
        if json:
            body["format"] = "json"
        r = httpx.post(f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
                       json=body, timeout=timeout, verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {r.status_code} — {r.text[:200]}")
        return str(r.json().get("response") or "")
    raise RuntimeError(f"moteur inconnu : {moteur}")


async def tirer_garde(moteur: str, modele: str, prompt: str, systeme: str, max_tokens: int = 4000,
                      json: bool = False, *, categorie: str = "motion", ref: str | None = None,
                      timeout: float = 90.0):
    """`tirer` sous les gardes d'une route payante, pour un appelant hors Vectorlab (t234) : moteur connu et configuré,
    puis l'estimation et `plafonds.verifier` AVANT l'appel (402 `dz_plafond` si le mois déborderait ; un local est
    gratuit et passe). L'appel lui-même tourne hors de la boucle (il est bloquant)."""
    import asyncio
    from app.services import plafonds as _PLAF
    if not connu(moteur):
        raise RuntimeError(f"moteur inconnu : {moteur}")
    if not configure(moteur):
        raise RuntimeError(f"moteur « {nom(moteur)} » non configuré (Réglages)")
    await _PLAF.verifier(estimer(moteur, prompt, systeme, max_tokens), categorie, ref)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: tirer(moteur, modele, prompt, systeme, max_tokens, json, timeout=timeout))
