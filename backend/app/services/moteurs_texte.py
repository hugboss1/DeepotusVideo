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


# ── l'effort (t239) ───────────────────────────────────────────────────────────────────────────────────────────────
# Spec 2026-10-18-studio-animation-personnalisation.md § 1.5 / P7. Le niveau se décide sur le modèle RÉELLEMENT choisi
# (celui de l'appel, sinon celui des Réglages › Valeurs par défaut), jamais sur un défaut figé du code. Un niveau que CE
# modèle n'accepte pas n'est jamais envoyé : il retombe sur « Auto » (rien dans la requête, le défaut du modèle joue).
# Relevé de la documentation officielle le 18/10/2026 :
#   - Anthropic : `output_config.effort` = low | medium | high | xhigh | max. Niveaux lus de préférence dans les
#     `capabilities` de l'API Modèles (GET /v1/models, que `vector_illustration.publies` lit déjà pour la liste) ;
#     sinon la table de familles ci-dessous. Défaut : medium (Opus 5.5, Haiku 5.5), high ailleurs.
#   - OpenAI (Chat Completions) : `reasoning_effort`, valeurs PROPRES À CHAQUE MODÈLE ; seules low/medium/high sont
#     prises, sur les modèles de raisonnement (o1, o3, o4-mini, gpt-5*, gpt-6*), hors variantes chat / pro / mini
#     d'o1 dont le jeu diffère. Défaut medium.
#   - Gemini (generateContent) : `generationConfig.thinkingConfig.thinkingLevel`, Gemini 3 et suivants, niveaux du
#     tableau publié par modèle. Gemini 2.5 se règle par un budget de jetons : aucun niveau sûr → Auto.
#   - Ollama : `think` = un nom de `thinking.values` rendu par POST /api/show pour CE modèle (gpt-oss : low/medium/
#     high) ; un modèle booléen ou sans réflexion → Auto.
#   - Fournisseurs libres (fl:) et serveurs locaux ajoutés (local:) : aucune API commune pour le dire → Auto seul.
ORDRE_EFFORTS = ("minimal", "low", "medium", "high", "xhigh", "max")
_CINQ = ("low", "medium", "high", "xhigh", "max")
# la sortie maximale demandée (et estimée) grandit avec l'effort : la réflexion se compte dans la sortie
_FACTEUR_SORTIE = {"minimal": 1.25, "low": 1.5, "medium": 2.0, "high": 3.0, "xhigh": 4.0, "max": 6.0}
PLAFOND_SORTIE = 32_000
_CAPS: dict = {}                            # {moteur: {modele: capabilities}} lues chez le fournisseur

_OPENAI_RAISONNEMENT = re.compile(r"^(o1|o3|o3-mini|o4-mini|gpt-5|gpt-6)(?:$|[.\-])")
_OPENAI_EXCLUS = re.compile(r"(chat|-pro\b|-pro-|^o1-mini|^o1-preview|audio|search|realtime|image)")
_GEMINI = {                                 # id publié → (niveaux, défaut), tableau officiel relevé le 18/10/2026
    "gemini-3.8-flash": (("low", "medium", "high"), "medium"),
    "gemini-3.6-flash": (("minimal", "low", "medium", "high"), "medium"),
    "gemini-3.5-flash-lite": (("minimal", "low", "medium", "high"), "minimal"),
    "gemini-3.1-pro-preview": (("low", "medium", "high"), "high"),
    "gemini-3-flash-preview": (("minimal", "low", "medium", "high"), "high"),
    "gemini-3-pro-preview": (("low", "high"), "high"),
}


def noter_capacites(moteur: str, modele: str, caps) -> None:
    """Retient ce que le fournisseur publie d'un modèle (Anthropic : `capabilities` de /v1/models ; Ollama : réponse
    de /api/show). Une donnée, jamais évaluée."""
    if modele and isinstance(caps, dict):
        _CAPS.setdefault(moteur, {})[str(modele)] = caps


def _version_claude(modele: str):
    m = re.match(r"^claude-(opus|sonnet|haiku|fable|mythos)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?$", modele or "")
    return (m.group(1), (int(m.group(2)), int(m.group(3) or 0))) if m else (None, None)


def _table_anthropic(modele: str) -> tuple:
    fam, v = _version_claude(modele)
    if fam in ("fable", "mythos") and v >= (5, 0):
        niv = _CINQ
    elif fam == "opus":
        niv = _CINQ if v >= (4, 7) else ("low", "medium", "high", "max") if v == (4, 6) \
            else ("low", "medium", "high") if v == (4, 5) else ()
    elif fam == "sonnet":
        niv = _CINQ if v >= (5, 0) else ("low", "medium", "high", "max") if v == (4, 6) else ()
    elif fam == "haiku":
        niv = _CINQ if v >= (5, 5) else ()
    else:
        niv = ()
    return niv, _defaut_anthropic(fam, v)


def _defaut_anthropic(fam, v) -> str:
    return "medium" if (fam, v) in (("opus", (5, 5)), ("haiku", (5, 5))) else "high"


def _caps_anthropic(caps: dict):
    e = caps.get("effort") if isinstance(caps, dict) else None
    if not isinstance(e, dict):
        return None
    if not e.get("supported"):
        return ()
    return tuple(n for n in _CINQ if isinstance(e.get(n), dict) and e[n].get("supported") is True)


def _show_ollama(modele: str, timeout: float = 4.0) -> dict:
    """POST {OLLAMA_URL}/api/show (gratuit, local), retenu : un échec vaut « rien appris » (Auto)."""
    deja = _CAPS.get("ollama", {}).get(modele)
    if deja is not None:
        return deja
    try:
        r = httpx.post(f"{settings.OLLAMA_URL.rstrip('/')}/api/show", json={"model": modele}, timeout=timeout,
                       verify=SSL_VERIFY)
        caps = r.json() if r.status_code == 200 else None
    except Exception:                                           # noqa: BLE001
        caps = None
    if not isinstance(caps, dict):              # injoignable : rien retenu (Ollama peut démarrer plus tard)
        return {}
    noter_capacites("ollama", modele, {"thinking": caps.get("thinking"), "capabilities": caps.get("capabilities")})
    return _CAPS["ollama"][modele]


def efforts(moteur: str, modele: str | None = None) -> dict:
    """`{modele, niveaux, defaut, source}` : les niveaux que CE moteur et CE modèle acceptent (dans l'ordre), le défaut
    du modèle (affiché à côté d'« Auto ») et d'où vient la réponse (`api`, `table`, `aucune`). Modèle absent → celui
    des Réglages (`modele_sain`)."""
    mod = (modele or modele_sain(moteur) or "").strip()
    niv, defaut, source = (), "", "aucune"
    if mod and not ressemble_a_une_cle(mod):
        if moteur == "anthropic":
            lues = _caps_anthropic(_CAPS.get("anthropic", {}).get(mod) or {})
            tniv, defaut = _table_anthropic(mod)
            niv, source = (lues, "api") if lues is not None else (tniv, "table" if tniv else "aucune")
        elif moteur == "openai":
            if _OPENAI_RAISONNEMENT.match(mod) and not _OPENAI_EXCLUS.search(mod):
                niv, defaut, source = ("low", "medium", "high"), "medium", "table"
        elif moteur == "gemini":
            if mod in _GEMINI:
                (niv, defaut), source = _GEMINI[mod], "table"
        elif moteur == "ollama":
            t = _show_ollama(mod).get("thinking")
            vals = t.get("values") if isinstance(t, dict) else None
            if isinstance(vals, list):
                niv = tuple(v for v in vals if isinstance(v, str) and v.strip())[:8]
                d = t.get("default")
                defaut = d if isinstance(d, str) and d in niv else ""
                source = "api" if niv else "aucune"
    if not niv:
        defaut = ""
    return {"modele": mod, "niveaux": list(niv), "defaut": defaut, "source": source}


def effort_applique(moteur: str, modele: str | None, effort) -> str:
    """Le niveau qui partira VRAIMENT : `effort` s'il est accepté par ce modèle, sinon "" (Auto : rien n'est envoyé).
    None, "", "auto" ou tout ce qui n'est pas un niveau connu → ""."""
    if not isinstance(effort, str):
        return ""
    e = effort.strip().lower()
    if not e or e == "auto" or e not in ORDRE_EFFORTS and moteur != "ollama":
        return ""
    return e if e in efforts(moteur, modele)["niveaux"] else ""


def sortie_max(max_tokens: int, applique: str) -> int:
    """La sortie maximale d'un appel à cet effort (déjà appliqué) : inchangée en Auto, plus grande sinon, bornée."""
    f = _FACTEUR_SORTIE.get(applique or "")
    if not f:
        return int(max_tokens)
    return max(int(max_tokens), min(PLAFOND_SORTIE, int(round(int(max_tokens) * f))))


# ── l'appel (t232) ────────────────────────────────────────────────────────────────────────────────────────────────

def nature_cout(moteur: str) -> str:
    """La bulle de coût de `mod-ia.js` (t224) : un serveur local est « gratuit », un fournisseur libre n'a pas de tarif
    connu (« a_mesurer », jamais gratuit), un intégré est « payant »."""
    if moteur == "ollama" or est_local(moteur):
        return "gratuit"
    return "a_mesurer" if est_libre(moteur) else "payant"


def estimer(moteur: str, prompt: str, systeme: str = "", max_tokens: int = 4000, effort=None, *,
            modele: str = "") -> dict:
    """L'op d'estimation d'UN appel, au moteur choisi : ~4 caractères par jeton en entrée, `max_tokens` en sortie (le
    pire cas). `pricing.estimate` la chiffre : 0 pour un local, tarif Anthropic + `a_mesurer` pour un fl.
    t239 : avec un `effort` que le modèle accepte (celui de l'appel, sinon celui des Réglages), la sortie estimée est
    celle qui sera demandée (`sortie_max`) ; sans effort, ou effort refusé, rien ne change."""
    from app.services import plafonds as _PLAF
    n = len(prompt or "") + len(systeme or "")
    out = sortie_max(int(max_tokens), effort_applique(moteur, modele, effort)) if effort is not None else int(max_tokens)
    return _PLAF.op_llm(-(-n // 4), out, str(moteur or ""))


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
          timeout: float = 90.0, effort=None):
    """UN appel, au moteur ET au modèle demandés — jamais un repli muet.

    Lève `RuntimeError` avec la cause : l'écran vient d'afficher le nom du modèle qui va dépenser la clé, un repli
    silencieux le ferait mentir. Le modèle vide prend `modele_sain` ; un modèle qui ressemble à une clé est refusé avant
    tout envoi (il finirait dans une URL ou un corps de requête). `json=True` : rend l'objet (`extraire_json`).
    Aucune garde de dépense ici : c'est `tirer_garde`, ou la route appelante (le Vectorlab a la sienne).
    t239 : `effort` (None / "auto" = rien) n'est envoyé que si CE modèle l'accepte (`effort_applique`) ; la sortie
    maximale et le délai grandissent alors avec lui.
    """
    mod = (modele or modele_sain(moteur)).strip()
    if not mod:
        raise RuntimeError(f"aucun modèle pour « {moteur} »")
    if ressemble_a_une_cle(mod):
        raise RuntimeError(f"le modèle demandé pour « {moteur} » ressemble à une clé d'API, pas à un nom de modèle")
    if json:
        systeme = f"{systeme}\n\n{CONSIGNE_JSON}" if systeme else CONSIGNE_JSON
    eff = effort_applique(moteur, mod, effort) if effort is not None else ""
    if eff:
        max_tokens = sortie_max(max_tokens, eff)
        timeout = min(600.0, timeout * _FACTEUR_SORTIE[eff]) if eff in _FACTEUR_SORTIE else timeout
    txt = _appeler(moteur, mod, prompt, systeme, max_tokens, json, timeout, eff)
    return extraire_json(txt) if json else txt


def _appeler(moteur: str, mod: str, prompt: str, systeme: str, max_tokens: int, json: bool, timeout: float,
             effort: str = "") -> str:
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
        if effort:
            body["output_config"] = {"effort": effort}
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
        if effort:
            body["reasoning_effort"] = effort
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
        if effort:
            body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": effort}
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
        if effort:
            body["think"] = effort
        r = httpx.post(f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
                       json=body, timeout=timeout, verify=SSL_VERIFY)
        if r.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {r.status_code} — {r.text[:200]}")
        return str(r.json().get("response") or "")
    raise RuntimeError(f"moteur inconnu : {moteur}")


async def tirer_garde(moteur: str, modele: str, prompt: str, systeme: str, max_tokens: int = 4000,
                      json: bool = False, *, categorie: str = "motion", ref: str | None = None,
                      timeout: float = 90.0, effort=None):
    """`tirer` sous les gardes d'une route payante, pour un appelant hors Vectorlab (t234) : moteur connu et configuré,
    puis l'estimation et `plafonds.verifier` AVANT l'appel (402 `dz_plafond` si le mois déborderait ; un local est
    gratuit et passe). L'appel lui-même tourne hors de la boucle (il est bloquant). t239 : l'estimation suit l'effort
    réellement appliqué au modèle réellement choisi."""
    import asyncio
    from app.services import plafonds as _PLAF
    if not connu(moteur):
        raise RuntimeError(f"moteur inconnu : {moteur}")
    if not configure(moteur):
        raise RuntimeError(f"moteur « {nom(moteur)} » non configuré (Réglages)")
    await _PLAF.verifier(estimer(moteur, prompt, systeme, max_tokens, effort, modele=modele), categorie, ref)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: tirer(moteur, modele, prompt, systeme, max_tokens, json, timeout=timeout, effort=effort))
