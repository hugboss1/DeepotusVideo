"""D-41 (L7-B, 24/09/2026) — AUTO-CLIPS : les meilleurs extraits de 15 à 60 s
d'une source parlée, notés par le LLM configuré ou, à défaut, par une
heuristique déterministe.

Service PUR (aucun état global, aucun réseau propre) ; les routes vivent dans
`montage_service.py` (`POST /api/montage/autoclips`, `.../autoclips/create`).

* `windows(words, min_s=15, max_s=60, step_s=5)` — `words` = les mots
  horodatés de `transcribe_service` (`align_known_text` / `align_to_audio` /
  `transcribe` : `{raw, punct, start, end, …}`). Les PHRASES sont les suites
  de mots jusqu'à une ponctuation forte de fin (`. ! ? …` dans `punct`) ; une
  queue sans ponctuation finale est une phrase (la fin du texte), et une
  phrase plus longue que `max_s` est coupée à la frontière de mot (un texte
  transcrit sans ponctuation donne encore des fenêtres). Une fenêtre =
  phrases CONSÉCUTIVES dont la durée tient dans `[min_s, max_s]` ; les
  débuts glissent d'au moins `step_s`, et pour un même début les fins
  retenues sont espacées d'au moins `step_s` (sans quoi deux phrases
  voisines doubleraient le nombre de fenêtres). Dédoublonnées par
  `(start, end)`, SANS plafond (revue du 24/09 : un plafond de 400 fenêtres
  chronologiques tronquait la source à ~352 s ; la limite porte sur la
  SÉLECTION, voir `score`). Chacune :
  `{i, start, end, text, words}` (temps de SOURCE, ceux des mots).
* `heuristic(win, persona=None)` — la formule du plan du 03/09 :
  40 + 15·(un « ? ») + 10·(un chiffre) + 5·(mot-clé de persona, par mot-clé
  distinct) − 1 par seconde au-delà de 45 s (au plus 15), borné 0..100,
  entier, DÉTERMINISTE (aucun hasard, aucune horloge). Mots-clés : ceux de
  l'univers (`deepotus`, `abysse`, `marée`, `prophète`) plus les mots de
  4 lettres ou plus de `persona` ; comparaison sans accents ni casse, par
  sous-chaîne (« abysses » compte pour « abysse »). Une LISTE de fenêtres
  rend la liste des scores (forme du banc du 03/09).
* `score(wins, llm=None, n=4, persona=None)` →
  `{clips:[{i, start, end, score, title, hook, segments, origine}], source}`
  (`origine` = "llm" | "heuristique", clip par clip). `llm=False` : aucun
  appel, heuristique directe (case « Classer avec l'IA » décochée).
  `llm(prompt, system, max_tokens) -> (texte|None, fournisseur)` ; par
  défaut `summarizer._chat_dispatch`, lu À L'APPEL (un banc le remplace par
  attribut de module). JSON strict demandé `[{i, score, title, hook}]`,
  `max_tokens=800` ; la réponse est lue du premier `[` au dernier `]` (un
  bloc ```json passe). `None`, exception, JSON cassé, ou aucune entrée
  valide (i hors des fenêtres ; `i` ou `score` booléen, chaîne, non fini
  ou non entier ; une entrée fautive est ignorée seule) → HEURISTIQUE, dit
  par `source == "heuristique"` ; sinon `source == "llm:<fournisseur>"`.
  Au plus 60 fenêtres partent au modèle, prises sur TOUTE la durée : la
  source est coupée en 60 tranches de temps égales et chaque tranche donne
  sa meilleure fenêtre heuristique (ordre chronologique ; texte coupé à
  280 caractères) — revue du 24/09. Le choix du modèle passe par le MÊME
  filtre glouton que l'heuristique (par score décroissant, une fenêtre qui
  chevauche un clip déjà pris est écartée — revue du 24/09), puis est
  complété jusqu'à `n` par l'heuristique (clips `origine: "heuristique"`,
  placés après ceux du modèle). L'heuristique, elle, voit TOUTES les
  fenêtres, choisit gloutonnement des fenêtres disjointes, puis complète par
  les meilleures restantes si la source est trop courte pour `n` extraits
  disjoints. `n` borné 1..8.
  Titre / accroche vides → repli tiré du texte : titre = les six premiers
  mots de la première phrase (48 caractères au plus), accroche = la
  première phrase interrogative de la fenêtre, sinon la première phrase
  (100 caractères au plus).
  `segments` = `transcribe_service.group_words(win.words, max_chars=30)`
  normalisés par `subtitle_service.normalize_segments` (la loi de
  `_subs_cues_to_segments`) et laissés en temps de SOURCE — DÉCISION : un
  clip est une fenêtre de la source (`start`/`end` y sont en temps source),
  ses segments parlent la même langue ; c'est `POST /autoclips/create` qui
  les décale de −start en posant la piste S1 du projet (temps de timeline).
"""
from __future__ import annotations

import json
import re
import unicodedata

_LLM_WINDOWS = 60
_LLM_TEXT = 280
_ENDERS = set(".!?…")
_UNIVERS = ("deepotus", "abysse", "maree", "prophete")


def _f(v, d=0.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return d
    return x if x == x and x not in (float("inf"), float("-inf")) else d


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _raw(w: dict) -> str:
    return str(w.get("raw") or w.get("w") or "").strip()


def _phrases(words: list[dict], max_s: float) -> list[list[dict]]:
    """Mots → phrases (listes de mots), coupées à la ponctuation forte de fin,
    et à la frontière de mot quand une phrase dépasse `max_s`."""
    out, cur = [], []
    for w in words:
        if not isinstance(w, dict) or not _raw(w):
            continue
        if cur and _f(w.get("end")) - _f(cur[0].get("start")) > max_s:
            out.append(cur)
            cur = []
        cur.append(w)
        if set(str(w.get("punct") or "")) & _ENDERS:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def windows(words, min_s: float = 15, max_s: float = 60, step_s: float = 5) -> list[dict]:
    min_s, max_s, step_s = _f(min_s, 15.0), _f(max_s, 60.0), max(0.0, _f(step_s, 5.0))
    if max_s < min_s:
        min_s, max_s = max_s, min_s
    ph = _phrases(list(words or []), max_s)
    out, vus = [], set()
    last_start = None
    for a in range(len(ph)):
        s0 = _f(ph[a][0].get("start"))
        if last_start is not None and s0 - last_start < step_s - 1e-9:
            continue
        emis = False
        last_end = None
        fins = []
        for b in range(a, len(ph)):
            e = _f(ph[b][-1].get("end"))
            d = e - s0
            if d > max_s + 1e-9:
                break
            if d >= min_s - 1e-9:
                fins.append((b, e))
        for k, (b, e) in enumerate(fins):
            # la fin la plus LONGUE est toujours gardée (revue du 24/09 : la
            # dernière phrase d'un texte, à moins de step_s de la précédente,
            # n'était atteinte par AUCUNE fenêtre)
            if (last_end is not None and e - last_end < step_s - 1e-9
                    and k != len(fins) - 1):
                continue
            key = (round(s0, 3), round(e, 3))
            if key in vus:
                continue
            vus.add(key)
            ws = [w for p in ph[a:b + 1] for w in p]
            out.append({"i": len(out), "start": key[0], "end": key[1],
                        "text": " ".join(_raw(w) for w in ws), "words": ws})
            last_end = e
            emis = True
        if emis:
            last_start = s0
    return out


def _mots_cles(persona) -> list[str]:
    extra = [m for m in re.findall(r"\w+", _fold(persona or "")) if len(m) >= 4]
    vus = []
    for m in list(_UNIVERS) + extra:
        if m not in vus:
            vus.append(m)
    return vus


def heuristic(win, persona=None):
    if isinstance(win, list):
        return [heuristic(w, persona) for w in win]
    if not isinstance(win, dict):
        return 0
    text = str(win.get("text") or "")
    t = _fold(text)
    s = 40
    if "?" in text:
        s += 15
    if any(ch.isdigit() for ch in text):
        s += 10
    s += 5 * sum(1 for m in _mots_cles(persona) if m in t)
    dur = _f(win.get("end")) - _f(win.get("start"))
    if dur > 45:
        s -= min(15, int(round(dur - 45)))
    return max(0, min(100, int(s)))


def _phrases_texte(win: dict) -> list[str]:
    ph = _phrases(win.get("words") or [], 1e9)
    return [" ".join(_raw(w) for w in p) for p in ph if p]


def _titre_repli(win: dict) -> str:
    ph = _phrases_texte(win) or [str(win.get("text") or "")]
    mots = re.sub(r"[.!?…]+$", "", ph[0].strip()).split()
    t = " ".join(mots[:6])
    return t if len(t) <= 48 else t[:47].rstrip() + "…"


def _accroche_repli(win: dict) -> str:
    ph = _phrases_texte(win) or [str(win.get("text") or "")]
    h = next((p for p in ph if "?" in p), ph[0]).strip()
    return h if len(h) <= 100 else h[:99].rstrip() + "…"


def _segments(win: dict) -> list[dict]:
    from app.services import subtitle_service as S
    from app.services import transcribe_service as T
    # copies : les mots de la fenêtre sont ceux de l'appelant (pureté)
    ws = [dict(w, speech_end=w.get("speech_end", w.get("end")))
          for w in (win.get("words") or []) if isinstance(w, dict) and "raw" in w]
    cues = T.group_words(ws, max_chars=30)
    return S.normalize_segments(
        [{"start": c["start"], "end": c["end"], "text": c["text"],
          "words": c.get("words")} for c in cues])


def _clip(win: dict, sc, title="", hook="", origine="heuristique") -> dict:
    return {"i": win["i"], "start": win["start"], "end": win["end"], "score": sc,
            "origine": origine,
            "title": str(title or "").strip()[:80] or _titre_repli(win),
            "hook": str(hook or "").strip()[:160] or _accroche_repli(win),
            "segments": _segments(win)}


def _disjoint(w: dict, pris: list) -> bool:
    return all(w["end"] <= q["start"] or w["start"] >= q["end"] for q in pris)


def _glouton(notes: list, n: int, pris: list, completer: bool) -> list:
    """`notes` = [(score, fenêtre, titre, accroche)] déjà triées ; ajoute à
    `pris` (fenêtres) et rend les entrées retenues, disjointes d'abord."""
    out = []
    for it in notes:
        if len(pris) >= n:
            break
        if _disjoint(it[1], pris):
            pris.append(it[1])
            out.append(it)
    if completer:                       # source trop courte : on complète
        for it in notes:
            if len(pris) >= n:
                break
            if all(it[1] is not q for q in pris):
                pris.append(it[1])
                out.append(it)
    return out


def _notes_h(wins: list[dict], persona) -> list:
    return sorted(((heuristic(w, persona), w, "", "") for w in wins),
                  key=lambda p: (-p[0], p[1]["start"], p[1]["end"]))


def _heuristique(wins: list[dict], n: int, persona, pris=None) -> list[dict]:
    pris = [] if pris is None else pris
    ret = _glouton(_notes_h(wins, persona), n, pris, True)
    ret.sort(key=lambda p: (-p[0], p[1]["start"]))
    return [_clip(w, sc, origine="heuristique") for sc, w, _t, _h in ret]


def _entier(v):
    """Un entier fini, jamais un booléen ni une chaîne (M3) ; None sinon."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    try:
        if isinstance(v, float) and not v.is_integer():
            return None
        return int(v)
    except (OverflowError, ValueError):
        return None


def _parse(texte: str, par_i: dict) -> list[tuple]:
    s = str(texte or "")
    a, b = s.find("["), s.rfind("]")
    if a < 0 or b <= a:
        raise ValueError("pas de tableau JSON")
    data = json.loads(s[a:b + 1])
    if not isinstance(data, list):
        raise ValueError("pas une liste")
    out, vus = [], set()
    for it in data:
        if not isinstance(it, dict):
            continue
        i = _entier(it.get("i"))
        sc = it.get("score")
        if i is None or isinstance(sc, bool) or not isinstance(sc, (int, float)):
            continue
        try:                            # M2 : une entrée fautive, seule
            note = max(0, min(100, int(round(sc))))
        except (OverflowError, ValueError):
            continue
        if i not in par_i or i in vus:
            continue
        vus.add(i)
        out.append((note, par_i[i],
                    it.get("title") if isinstance(it.get("title"), str) else "",
                    it.get("hook") if isinstance(it.get("hook"), str) else ""))
    return out


def _bornes_n(n) -> int:
    try:
        k = int(n)
    except (TypeError, ValueError, OverflowError):
        k = 4
    return max(1, min(8, k))


def _candidats(wins: list[dict], persona) -> list[dict]:
    """<= 60 fenêtres réparties sur TOUTE la durée : 60 tranches de temps
    égales, la meilleure fenêtre heuristique de chacune, en ordre
    chronologique."""
    t0 = min(w["start"] for w in wins)
    t1 = max(w["start"] for w in wins)
    pas = (t1 - t0) / _LLM_WINDOWS or 1.0
    best = {}
    for _sc, w, _t, _h in _notes_h(wins, persona):
        k = min(_LLM_WINDOWS - 1, int((w["start"] - t0) / pas))
        best.setdefault(k, w)
    return sorted(best.values(), key=lambda w: (w["start"], w["end"]))


def score(wins, llm=None, n=4, persona=None) -> dict:
    wins = [w for w in (wins or []) if isinstance(w, dict) and "i" in w]
    n = _bornes_n(n)
    if not wins or llm is False:
        return {"clips": _heuristique(wins, n, persona) if wins else [],
                "source": "heuristique"}
    if llm is None:
        from app.services import summarizer
        llm = summarizer._chat_dispatch
    cands = _candidats(wins, persona)
    par_i = {w["i"]: w for w in cands}
    system = (f"Tu es le monteur de {str(persona or 'la chaîne')[:60]}. Tu choisis les "
              f"extraits courts (15 à 60 s) les plus forts pour les réseaux sociaux. "
              f"Réponds UNIQUEMENT par un tableau JSON strict "
              f'[{{"i": <entier>, "score": <0-100>, "title": "<titre court>", '
              f'"hook": "<accroche>"}}], sans aucun texte autour. Les extraits ne '
              f"doivent pas se chevaucher.")
    prompt = (f"Choisis au plus {n} extraits parmi ces fenêtres "
              f"(i | début–fin en secondes | texte) :\n"
              + "\n".join(f"{w['i']} | {w['start']:.1f}–{w['end']:.1f} | "
                          f"{str(w.get('text') or '')[:_LLM_TEXT]}" for w in cands))
    try:
        out, prov = llm(prompt, system, 800)
        choix = _parse(out, par_i) if out else []
    except Exception:
        choix = []
    if not choix:
        return {"clips": _heuristique(wins, n, persona), "source": "heuristique"}
    choix.sort(key=lambda c: (-c[0], c[1]["start"]))
    pris = []
    retenus = _glouton(choix, n, pris, False)
    clips = [_clip(w, sc, t, h, origine="llm") for sc, w, t, h in retenus]
    if len(pris) < n:
        clips += _heuristique(wins, n, persona, pris)
    return {"clips": clips, "source": "llm:%s" % (prov or "?")}
