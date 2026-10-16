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
"""
from __future__ import annotations

from app.config import settings

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
