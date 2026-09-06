# -*- coding: utf-8 -*-
"""P16 — TRADUIRE LES RÉPLIQUES (06/09/2026, tâche 22 du plan Montage).

MODULE NEUF plutôt qu'une greffe dans `transcribe_service` — trois raisons
mesurées : (1) transcribe_service est du STT (son → texte), gardé par
25 tests pytest (test_transcribe_service.py) et BOUCHONNÉ par attribut de
module dans trois bancs (`T.transcribe`, `T._key`, `T.align_narration_clips`)
— y greffer une fonction LLM élargirait la surface que ces bouchons doivent
connaître ; (2) la traduction ne partage RIEN avec lui : ni ffmpeg, ni
fichier, ni fournisseur STT — sa seule dépendance est
`summarizer._chat_dispatch` (texte → texte) ; (3) le parseur du contrat
« N lignes numérotées » est pur et se teste seul, sans importer les 900
lignes du STT.

LE CONTRAT, STRICT : le prompt numérote les N répliques (`n|texte`, une par
ligne — un saut de ligne DANS une réplique est aplati en espace, sinon une
réplique ferait deux lignes et le compte mentirait) ; le système exige
N lignes `n|traduction` et rien d'autre. La réponse est re-parsée, re-triée
par numéro ; tout écart de compte ou numéro manquant REFUSE en 400 — aucune
réplique n'est perdue en silence. Le `start`/`end` de chaque segment est
CONSERVÉ tel quel : la traduction ne touche jamais aux temps.

Toute lecture de `summarizer` passe par l'ATTRIBUT du module
(`SZ._chat_dispatch`, `SZ.active_provider`) : c'est ce qui rend le banc
`test_subs_traduction.py` capable de bouchonner sans réseau.
"""
from __future__ import annotations

import math
import re

# ── le gabarit ─────────────────────────────────────────────────────────────
SYSTEM = (
    "Tu traduis des sous-titres vidéo. Réponds par EXACTEMENT une ligne par "
    "réplique numérotée, au format « numéro|traduction », toutes présentes, "
    "chaque numéro une seule fois, dans n'importe quel ordre. RIEN d'autre : "
    "pas de préambule, pas de commentaire, pas de bloc de code. Garde les "
    "noms propres tels quels ; reste bref, ce sont des sous-titres.")

_RE_FENCE = re.compile(r"```[a-z]*", re.I)
_RE_LIGNE = re.compile(r"^(\d{1,4})\s*\|(.*)$")


def _tete(n: int, target: str, source: str | None) -> str:
    src = ("du %s" % source) if source else "de la langue du texte"
    return ("Traduis ces %d répliques de sous-titres %s vers « %s ». "
            "Chaque ligne d'entrée est « numéro|texte ». Rends une ligne "
            "« numéro|traduction » par réplique.\n" % (n, src, target))


def build_prompt(segments: list[dict], target: str,
                 source: str | None = None) -> tuple[str, str]:
    """(prompt, system) — une réplique par ligne, numérotée à partir de 1."""
    lignes = []
    for i, s in enumerate(segments):
        txt = re.sub(r"\s+", " ", str((s or {}).get("text") or "")).strip()
        lignes.append("%d|%s" % (i + 1, txt))
    return _tete(len(segments), target, source) + "\n".join(lignes), SYSTEM


def parse_reply(txt: str, n: int) -> list[str]:
    """Re-parse la réponse du modèle — lève ValueError (→ 400) sur tout écart.

    Le découpage se fait au PREMIER « | » (celui qui suit le numéro) : une
    traduction qui contient elle-même « | » est conservée ENTIÈRE. Une ligne
    sans « numéro| » (préambule, bruit) est ignorée — c'est le COMPTE qui
    tranche : N lignes valides, chaque numéro de 1 à N exactement une fois.
    """
    t = _RE_FENCE.sub("", str(txt or ""))
    vues: dict[int, str] = {}
    for ligne in t.splitlines():
        m = _RE_LIGNE.match(ligne.strip())
        if not m:
            continue
        num = int(m.group(1))
        if num in vues:
            raise ValueError(
                "la traduction a rendu le numéro %d en double — rien n'a "
                "été écrit" % num)
        vues[num] = m.group(2).strip()
    manquants = [i for i in range(1, n + 1) if i not in vues]
    if len(vues) != n or manquants:
        det = (" (numéros manquants : %s)"
               % ", ".join(str(i) for i in manquants[:8])) if manquants else ""
        raise ValueError(
            "la traduction a rendu %d lignes sur %d%s — rien n'a été écrit"
            % (len(vues), n, det))
    return [vues[i] for i in range(1, n + 1)]


def estimate_tokens(chars: float, n: int = 0) -> tuple[int, int]:
    """PROTOCOLE D'ESTIMATION — une estimation, PAS une mesure : aucun
    tokenizer n'est embarqué. Règle d'usage pour les langues latines :
    ≈ 4 caractères par token. L'entrée compte les caractères des répliques,
    plus le gabarit fixe (system + consigne, mesuré par len() ci-dessous),
    plus ~8 caractères de numérotation par réplique ; la sortie est estimée
    à l'entrée utile × 1,2 (une traduction FR↔EN varie d'environ ±20 %).
    """
    c = max(0.0, float(chars or 0))
    gabarit = len(SYSTEM) + len(_tete(max(1, n or 1), "xx", "fr"))
    in_tok = int(math.ceil((c + gabarit + 8 * max(0, n)) / 4.0))
    out_tok = int(math.ceil(c * 1.2 / 4.0))
    return in_tok, out_tok


def estimate(chars: float, target: str = "") -> dict:
    """COÛT annoncé AVANT de lancer (convention de l'app) — {ok, usd,
    provider} ; `ok:false` + `reason` lisible si aucune clé LLM (même
    convention que /subtitles/estimate : l'UI désarme le bouton et dit
    pourquoi)."""
    from app.services import summarizer as SZ
    prov = SZ.active_provider()
    if not prov:
        return {"ok": False, "usd": 0.0, "provider": None,
                "reason": "Aucune clé LLM configurée (Réglages : Anthropic, "
                          "OpenAI ou Gemini) — la traduction des répliques "
                          "est indisponible. Écrire, caler et exporter les "
                          "sous-titres restent gratuits."}
    from app.services import pricing
    it, ot = estimate_tokens(chars)
    est = pricing.estimate({"kind": "llm", "provider": prov,
                            "in_tok": it, "out_tok": ot})
    return {"ok": True, "usd": round(float(est.get("total_usd") or 0), 6),
            "provider": prov, "target": str(target or ""),
            "chars": int(max(0.0, float(chars or 0))),
            "in_tok": it, "out_tok": ot}


def translate(segments: list[dict], target: str,
              source: str | None = None) -> dict:
    """Traduit N répliques — SYNCHRONE (la route l'enveloppe dans
    run_in_executor, comme /vector/illustration). Lève ValueError (→ 400)
    sur un contrat rompu, RuntimeError (→ 502) sur un modèle muet."""
    from app.services import summarizer as SZ
    n = len(segments)
    prompt, system = build_prompt(segments, target, source)
    chars = sum(len(str((s or {}).get("text") or "")) for s in segments)
    it, ot = estimate_tokens(chars, n)
    max_tok = max(400, min(8000, ot * 2 + 60))
    out, prov = SZ._chat_dispatch(prompt, system, max_tok)
    if out is None:
        raise RuntimeError("aucun texte rendu — clé LLM absente ou moteurs "
                           "muets")
    textes = parse_reply(out, n)
    segs = [{"start": (s or {}).get("start"), "end": (s or {}).get("end"),
             "text": textes[i]} for i, s in enumerate(segments)]
    # Le COÛT rendu est la même ESTIMATION que /translate/estimate (les
    # moteurs de _chat_dispatch ne rapportent pas leurs tokens — mesuré :
    # _anthropic_chat ne lit que `content`) ; le protocole est écrit dans
    # estimate_tokens.
    from app.services import pricing
    est = pricing.estimate({"kind": "llm", "provider": prov or "openai",
                            "in_tok": it, "out_tok": ot})
    return {"segments": segs, "provider": prov,
            "usd": round(float(est.get("total_usd") or 0), 6)}
