# -*- coding: utf-8 -*-
"""Piste de sous-titres (s1) du Montage — d'où viennent le TEXTE et le CALAGE.

Le Montage porte des clips typés par `tr` (v1, v2, a1, a2, a3 — voir
montage_service). La piste de sous-titres est `s1`. Ce module ne dessine
rien : il produit les MOTS HORODATÉS et les RÉPLIQUES groupées que la piste
affiche, par deux chemins distincts.

────────────────────────────────────────────────────────────────────────────
CHEMIN 1 — le texte est DÉJÀ CONNU (`align_known_text`, `align_to_audio`)
────────────────────────────────────────────────────────────────────────────
Le tiroir Narration écrit le texte, ElevenLabs le prononce : transcrire ce
qu'on vient de faire dire est absurde et payant. On CALE un texte exact sur
un audio connu — gratuit, hors ligne, et le texte est juste par construction
(aucun nom propre écorché, là où une transcription se trompe).

Trois ingrédients, dans cet ordre :

1. **Poids par mot** (`word_weight`) — pas de parts égales. Le coût d'un mot
   est modélisé par sa STRUCTURE : nombre de noyaux vocaliques (les syllabes
   phonétiques réelles : « eau » = 1, « surface » = 2 parce que le -e final
   est muet) + un coût par consonne (les grappes coûtent du temps) + un
   forfait de frontière de mot. « permission » (3 noyaux, 6 consonnes) pèse
   ainsi 3,0 fois « la » (1 noyau, 1 consonne). La barre, elle, donne EXACTEMENT
   le même temps aux deux (mesuré, voir plus bas).

2. **Poids de pause** (`pause_weight`) — la ponctuation qui suit un mot lui
   ajoute du temps mort : virgule < point-virgule < point < points de
   suspension. Le mot reste contigu au suivant (`end`), mais expose aussi
   `speech_end` = fin de la PAROLE, avant la pause : c'est `speech_end` que
   le surlignage karaoké doit suivre pour ne pas rester allumé sur un silence.

3. **Silences réels** (`detect_silences`, ffmpeg `silencedetect`) — l'intervalle
   est découpé en « travées de parole ». Les mots sont répartis entre les
   travées au prorata de leur poids, chaque mot appartient à UNE travée, et
   AUCUN mot n'est posé dans un silence détecté. Les frontières de travée
   préfèrent tomber après une ponctuation forte (`_PUNCT_PREF`) : c'est
   généralement là que le locuteur respire.

Le résultat couvre EXACTEMENT l'union des travées : les bornes sont arrondies
une seule fois et partagées entre mots voisins, donc `end[i] == start[i+1]`
au millième — jamais de chevauchement ni de trou par arrondi.

────────────────────────────────────────────────────────────────────────────
CHEMIN 2 — le texte est INCONNU (`transcribe`, plan importé / voix off externe)
────────────────────────────────────────────────────────────────────────────
Là il faut vraiment transcrire. Seuls sont retenus les fournisseurs qui
rendent des horodatages AU MOT (pas au segment) :

  * `elevenlabs` — Scribe v1 (`timestamps_granularity=word`), clé déjà
    configurée pour la voix de l'app ;
  * `openai` — `whisper-1` + `timestamp_granularities[]=word`
    (`gpt-4o-transcribe` ne sait PAS faire le mot : volontairement absent).

Convention maison respectée : `estimate_transcription()` annonce le COÛT et
la DURÉE AVANT de lancer (comme le widget de coût partout ailleurs) ; la
barre, elle, ne dit rien et facture ensuite.

────────────────────────────────────────────────────────────────────────────
La barre (Kapwing Studio > SUBTITLES), manipulée le 10/08/2026
────────────────────────────────────────────────────────────────────────────
Sur le clip d'exemple public (z9k-Sample_Video.mp4, 15,972 s) :
  * « Start from scratch » ouvre un bloc FIGÉ à 00:00.000 → 00:03.000 ;
    76 caractères tapés n'ont pas bougé la fin d'un millième — aucun calage
    sur l'audio, c'est à l'utilisateur de saisir les temps à la main ;
  * le karaoké sur texte tapé est un partage UNIFORME par mot : tête de
    lecture à 1,598 s sur 3,000 s (0,533), mot surligné = le 8ᵉ de 14, dont
    la fenêtre uniforme est [7/14, 8/14] = [0,500 ; 0,571]. « la » reçoit
    autant que « permission » ;
  * Download « as .SRT / .VTT / .TXT » renvoie sur « Sign in to upgrade to
    Pro ». Chez nous : local, gratuit, sans filigrane (`to_srt`/`to_vtt`/`to_txt`).

DÉRIVE MESURÉE (10/08/2026) — narration réelle produite par l'app
(ElevenLabs, /api/audio/voiceover, 11,842 s, 27 mots, 7 travées de parole).
Vérité = horodatages AU MOT rendus par Scribe v1 sur le MÊME fichier.
Écart |début calé − début mesuré|, sur les 24 mots que le STT a transcrits
à l'identique :

    calage pondéré (ici)      moyenne 0,106 s | médiane 0,070 s | max 0,633 s
    partage uniforme (barre)  moyenne 0,277 s | médiane 0,235 s | max 0,690 s
    mots sous 0,15 s          19/24  contre  6/24

Le pire mot (0,633 s) tombe sur une respiration SANS ponctuation en plein
milieu d'une proposition — le seul endroit où le texte ne prédit pas le
silence. Et le STT, lui, a écrit « Dipotus » là où le texte disait
« Deepotus » : sur un nom propre, le chemin 1 est exact par construction et
la transcription payante se trompe.

Aucun numpy : arithmétique pure + ffmpeg/ffprobe déjà présents.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from loguru import logger

# ── ffmpeg / ffprobe ────────────────────────────────────────────────────────
# Même résolution que effects_preview.ffmpeg_bin (PATH, sinon binaire embarqué
# par l'installeur) — importée paresseusement pour garder ce module autonome
# et testable sans app.config.


def _bin(name: str) -> str:
    import os
    import shutil
    exe = shutil.which(name)
    if exe:
        return exe
    cand = os.path.expandvars(
        r"%LOCALAPPDATA%\DeepotusVideoGen\bin" + f"\\{name}.exe")
    return cand if os.path.isfile(cand) else name


# ════════════════════════════════════════════════════════════════════════════
#  1. Découpe en mots
# ════════════════════════════════════════════════════════════════════════════

# Ponctuation « collée » au mot précédent, retirée du corps du mot pour le
# calcul de poids mais conservée pour l'affichage.
_TRAIL_PUNCT = ".,;:!?…»\"')]}—–-"
_LEAD_PUNCT = "«\"'([{¿¡—–"


def tokenize(text: str) -> list[dict]:
    """Texte → liste de jetons `{raw, word, punct}`.

    `raw` = la forme telle qu'elle sera affichée (ponctuation comprise),
    `word` = le corps servant au poids, `punct` = la ponctuation finale.
    Les espaces multiples, retours ligne et espaces insécables sont normalisés ;
    la concaténation des `raw` séparés d'un espace reconstitue le texte utile.
    """
    src = (text or "").replace(" ", " ").replace(" ", " ")
    out: list[dict] = []
    pending = ""          # ponctuation ouvrante isolée, en attente du mot suivant
    for raw in src.split():
        # La ponctuation FERMANTE est retirée en premier : le tiret cadratin
        # « — », membre des deux familles, doit compter comme une pause APRÈS
        # le mot précédent, jamais comme un préfixe du suivant.
        body, lead, punct = raw, "", ""
        while body and body[-1] in _TRAIL_PUNCT:
            punct = body[-1] + punct
            body = body[:-1]
        while body and body[0] in _LEAD_PUNCT:
            lead += body[0]
            body = body[1:]
        if not body:
            if punct and out:
                # jeton purement fermant (tiret cadratin isolé, « … », » ) :
                # rattaché au mot précédent — il marque une PAUSE, pas un mot.
                out[-1]["raw"] += " " + raw
                out[-1]["punct"] = (out[-1]["punct"] + punct)[-3:]
            elif lead:
                # jeton purement ouvrant (« isolé) : il appartient au mot
                # SUIVANT, pas au précédent — sinon il salit la ponctuation de
                # fin du précédent et fausse les coupes de réplique.
                pending = (pending + raw + " ")[-8:]
            continue
        out.append({"raw": pending + raw, "word": body, "punct": punct})
        pending = ""
    if pending and out:
        out[-1]["raw"] += " " + pending.strip()
    return out


# ════════════════════════════════════════════════════════════════════════════
#  2. Poids : structure du mot, pas sa part égale
# ════════════════════════════════════════════════════════════════════════════

_VOWELS = set("aeiouyàâäåéèêëíîïòóôöùúûüýÿœæ")

# Pseudo-secondes : seuls les RAPPORTS comptent (tout est renormalisé sur la
# durée réelle), mais les garder à l'échelle de la seconde rend les poids de
# pause commensurables aux poids de parole.
_W_BASE = 0.055      # frontière de mot (attaque + détente)
_W_NUCLEUS = 0.165   # par noyau vocalique (≈ une syllabe)
_W_CONSONANT = 0.038 # par consonne (les grappes coûtent du temps)

# Temps mort ajouté APRÈS le mot selon la ponctuation qui le suit.
_PAUSE = {",": 0.30, ";": 0.45, ":": 0.45, ".": 0.60, "!": 0.60, "?": 0.60,
          "…": 0.85, "—": 0.45, "–": 0.45}
# Ponctuation « forte » : frontière de travée / de réplique privilégiée.
_PUNCT_PREF = set(".!?…;:")


def _fold(word: str) -> str:
    """Minuscule, apostrophes normalisées, diacritiques conservés."""
    return (word or "").lower().replace("’", "'")


def syllables(word: str, lang: str = "fr") -> int:
    """Noyaux vocaliques d'un mot ≈ ses syllabes phonétiques.

    Groupes de voyelles consécutives = 1 noyau (« eau », « ai », « ou »).
    Le -e final muet est retiré quand ce n'est pas la seule syllabe
    (« surface » 3 groupes → 2 syllabes ; « le » reste 1) — vrai en français
    comme en anglais (« make »). Chaque chiffre compte pour un noyau
    (« 2026 » ≈ 4).
    """
    w = _fold(word)
    if not w:
        return 0
    groups: list[str] = []
    cur = ""
    for ch in w:
        if ch.isdigit():
            if cur:
                groups.append(cur)
                cur = ""
            groups.append(ch)
            continue
        if ch in _VOWELS:
            cur += ch
        else:
            if cur:
                groups.append(cur)
                cur = ""
    if cur:
        groups.append(cur)
    n = len(groups)
    if n > 1 and groups[-1] == "e" and not w.endswith(("e'",)):
        n -= 1  # -e final muet
    return max(1, n)


def _consonants(word: str) -> int:
    w = _fold(word)
    return sum(1 for ch in w
               if ch.isalpha() and ch not in _VOWELS)


def word_weight(word: str, lang: str = "fr") -> float:
    """Poids de PAROLE d'un mot (pseudo-secondes, strictement positif)."""
    if not (word or "").strip():
        return _W_BASE
    return (_W_BASE
            + _W_NUCLEUS * syllables(word, lang)
            + _W_CONSONANT * _consonants(word))


def pause_weight(punct: str) -> float:
    """Temps mort induit par la ponctuation finale (le maximum l'emporte)."""
    return max((_PAUSE.get(c, 0.0) for c in (punct or "")), default=0.0)


# ════════════════════════════════════════════════════════════════════════════
#  3. Silences réels (ffmpeg silencedetect)
# ════════════════════════════════════════════════════════════════════════════

_RE_SIL_START = re.compile(r"silence_start:\s*(-?\d+(?:\.\d+)?)")
_RE_SIL_END = re.compile(r"silence_end:\s*(-?\d+(?:\.\d+)?)")


def probe_duration(path: str | Path, timeout: float = 30.0) -> float:
    """Durée du média en secondes (0.0 si illisible)."""
    try:
        out = subprocess.run(
            [_bin("ffprobe"), "-v", "error", "-show_entries",
             "format=duration", "-of", "csv=p=0", str(path)],
            check=False, capture_output=True, text=True,
            timeout=timeout).stdout.strip()
        return max(0.0, float(out))
    except (ValueError, OSError, subprocess.SubprocessError):
        return 0.0


def parse_silencedetect(stderr: str, total_s: float) -> list[tuple[float, float]]:
    """Sorties `silencedetect` → intervalles [(début, fin), …] triés.

    Un `silence_start` sans `silence_end` (silence courant à la fin du
    fichier) est refermé sur `total_s`.
    """
    spans: list[tuple[float, float]] = []
    open_at: float | None = None
    for line in (stderr or "").splitlines():
        m = _RE_SIL_START.search(line)
        if m:
            open_at = max(0.0, float(m.group(1)))
            continue
        m = _RE_SIL_END.search(line)
        if m and open_at is not None:
            e = float(m.group(1))
            if e > open_at:
                spans.append((open_at, e))
            open_at = None
    if open_at is not None and total_s > open_at:
        spans.append((open_at, total_s))
    return sorted(spans)


#: Memo de `detect_silences` — voir `_silence_key` et le commentaire dans la
#: fonction. Plafond bas : ce cache sert une seance d'edition, pas un index.
_SILENCE_MEMO: dict = {}


def _silence_key(p: Path, noise_db: float, min_silence_s: float):
    """Cle du memo de `detect_silences`, ou None si le fichier ne se lit pas.

    Elle porte le CONTENU autant que le chemin : `st_mtime_ns` et `st_size`
    font qu'une voix off re-synthetisee au MEME chemin invalide son entree
    d'elle-meme. Sans eux, une voix refaite en cours de seance aurait servi
    des silences perimes jusqu'au redemarrage — et le panneau « Texte »
    recharge apres chaque coupe, donc toute la seance.

    Les deux seuils entrent aussi dans la cle : deux reglages differents
    mesurent deux choses differentes.

    EXTRAITE de `detect_silences` pour etre MESURABLE sans ffmpeg. Construite
    en ligne, elle etait indefendable : la couper de mtime et de taille
    laissait le banc entierement vert.
    """
    try:
        st = p.stat()
    except OSError:
        return None
    return (str(p.resolve()), st.st_mtime_ns, st.st_size,
            float(noise_db), float(min_silence_s))


def detect_silences(audio_path: str | Path, *, noise_db: float = -33.0,
                    min_silence_s: float = 0.20,
                    timeout: float = 120.0) -> list[tuple[float, float]]:
    """Silences du fichier audio, en secondes absolues.

    `noise_db` : seuil (dBFS) sous lequel c'est du silence ; `min_silence_s` :
    durée minimale retenue (les micro-coupures entre phonèmes ne sont pas des
    respirations). Retourne [] si ffmpeg est absent ou échoue — le calage
    retombe alors proprement sur l'intervalle plein.
    """
    p = Path(audio_path)
    if not p.is_file():
        return []
    # MEMO. Une passe ffmpeg par clip ET PAR COUPE : le panneau « Texte » se
    # recharge apres chaque coupe, et une coupe multiplie les clips. La cle
    # est `_silence_key` — extraite pour etre mesurable, voir sa docstring.
    key = _silence_key(p, noise_db, min_silence_s)
    if key is not None and key in _SILENCE_MEMO:
        return _SILENCE_MEMO[key]
    total = probe_duration(p)
    try:
        r = subprocess.run(
            [_bin("ffmpeg"), "-hide_banner", "-nostdin", "-i", str(p),
             "-af", f"silencedetect=noise={float(noise_db)}dB:"
                    f"d={max(0.01, float(min_silence_s))}",
             "-f", "null", "-"],
            check=False, capture_output=True, text=True, errors="replace",
            timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning(f"transcribe: silencedetect indisponible ({e})")
        return []
    out = parse_silencedetect(r.stderr, total)
    if key is not None:
        if len(_SILENCE_MEMO) >= 64:
            _SILENCE_MEMO.clear()
        _SILENCE_MEMO[key] = out
    return out


def speech_spans(start: float, end: float,
                 silences: list[tuple[float, float]] | None,
                 *, min_span_s: float = 0.12) -> list[tuple[float, float]]:
    """[start, end] moins les silences → travées de parole.

    Les silences sont écrêtés à l'intervalle et fusionnés ; une travée plus
    courte que `min_span_s` est absorbée (elle ne peut pas porter un mot).
    Sans silence exploitable, retourne [(start, end)] — la couverture reste
    exactement l'intervalle demandé.
    """
    if end <= start:
        return []
    clipped: list[tuple[float, float]] = []
    for s, e in sorted(silences or []):
        s, e = max(float(s), start), min(float(e), end)
        if e - s <= 0:
            continue
        if clipped and s <= clipped[-1][1]:
            clipped[-1] = (clipped[-1][0], max(clipped[-1][1], e))
        else:
            clipped.append((s, e))
    spans: list[tuple[float, float]] = []
    cur = start
    for s, e in clipped:
        if s - cur >= min_span_s:
            spans.append((cur, s))
        cur = max(cur, e)
    if end - cur >= min_span_s:
        spans.append((cur, end))
    return spans or [(start, end)]


def _fit_spans(spans: list[tuple[float, float]], n_tokens: int
               ) -> list[tuple[float, float]]:
    """Ramène le nombre de travées à au plus `n_tokens`.

    Chaque travée doit porter au moins un mot ; s'il y a plus de travées que
    de mots, on refusionne à travers les silences les PLUS COURTS (les moins
    signifiants) jusqu'à ce que ça tienne.
    """
    spans = list(spans)
    while len(spans) > max(1, n_tokens):
        gaps = [(spans[i + 1][0] - spans[i][1], i)
                for i in range(len(spans) - 1)]
        _, i = min(gaps)
        spans[i:i + 2] = [(spans[i][0], spans[i + 1][1])]
    return spans


# ════════════════════════════════════════════════════════════════════════════
#  4. Calage d'un texte connu
# ════════════════════════════════════════════════════════════════════════════

def _split_runs(toks: list[dict], weights: list[float],
                spans: list[tuple[float, float]]) -> list[tuple[int, int]]:
    """Découpe les jetons en autant de tranches contiguës que de travées.

    La tranche k reçoit la part de poids proportionnelle à la durée de la
    travée k ; à écart comparable, une frontière juste après une ponctuation
    forte est préférée (le locuteur respire là).

    La cible est RENORMALISÉE à chaque travée sur ce qu'il RESTE (mots
    restants / durée restante), et non calculée sur un cumul global. C'est ce
    qui rend le découpage auto-correcteur : une travée mal servie ne décale
    plus toutes les suivantes. Mesuré le 10/08/2026 sur une narration réelle
    (27 mots, 7 travées, vérité = horodatages au mot d'un STT sur le MÊME
    fichier) : cible cumulée globale = 5 frontières justes sur 6, dérive
    moyenne 0,160 s ; cible renormalisée = 5 sur 6 aussi, mais l'erreur ne se
    propage plus — dérive moyenne 0,106 s, médiane 0,070 s.
    """
    n, k = len(toks), len(spans)
    if k <= 1:
        return [(0, n)]
    prefix = [0.0]
    for w in weights:
        prefix.append(prefix[-1] + w)
    dur = [e - s for s, e in spans]
    runs: list[tuple[int, int]] = []
    idx = 0
    for i in range(k):
        if i == k - 1:
            runs.append((idx, n))
            break
        w_rem = prefix[n] - prefix[idx]
        d_rem = sum(dur[i:]) or 1.0
        target = prefix[idx] + w_rem * dur[i] / d_rem
        j_max = n - (k - i - 1)          # laisser un jeton à chaque travée
        best_j, best_score = idx + 1, None
        for j in range(idx + 1, j_max + 1):
            err = abs(prefix[j] - target)
            if toks[j - 1]["punct"] and set(toks[j - 1]["punct"]) & _PUNCT_PREF:
                err *= 0.6               # bonus « fin de phrase »
            if best_score is None or err < best_score:
                best_j, best_score = j, err
        runs.append((idx, best_j))
        idx = best_j
    return runs


def align_known_text(text: str, *, start: float = 0.0,
                     end: float | None = None,
                     duration_s: float | None = None,
                     silences: list[tuple[float, float]] | None = None,
                     lang: str = "fr") -> dict:
    """Cale un texte EXACT sur un intervalle connu. Aucun réseau, aucun coût.

    Retourne `{ok, source:"align", start, end, lang, words:[…], spans, silences}`
    où chaque mot est `{i, w, raw, start, end, speech_end, punct, weight}` :
      * `w`/`raw` : mot nu / forme affichée (ponctuation comprise) ;
      * `start`→`end` : contigus, `end[i] == start[i+1]` au millième ;
      * `speech_end` : fin de la PAROLE (avant la pause de ponctuation) —
        c'est la borne du surlignage karaoké.

    Les mots ne sont jamais posés dans un silence fourni : ils sont répartis
    entre les travées de parole, au prorata de leur poids structurel.
    """
    if end is None:
        if duration_s is None:
            raise ValueError("align_known_text : end ou duration_s requis.")
        end = float(start) + float(duration_s)
    start, end = float(start), float(end)
    if end <= start:
        raise ValueError(f"Intervalle vide : {start} → {end}.")
    toks = tokenize(text)
    if not toks:
        raise ValueError("Texte vide — rien à caler.")

    speech = [word_weight(t["word"], lang) for t in toks]
    pauses = [pause_weight(t["punct"]) for t in toks]
    if pauses:
        pauses[-1] = 0.0      # rien ne suit le dernier mot

    spans = _fit_spans(speech_spans(start, end, silences), len(toks))

    # Répartition entre travées : parole + pause. Une pause tombée sur un
    # silence mesuré est certes comptée des deux côtés, mais la cible
    # renormalisée de `_split_runs` absorbe ce biais — testé contre la variante
    # « parole seule » et contre un point fixe qui retire les pauses de
    # frontière : les deux dégradent le calage sur narration réelle.
    alloc = [s + p for s, p in zip(speech, pauses)]
    runs = _split_runs(toks, alloc, spans)
    # À l'intérieur d'une travée, la pause du DERNIER mot est portée par le
    # silence qui suit (ou par la fin de l'intervalle) : elle sort du partage.
    ends = {b - 1 for a, b in runs}
    weights = [speech[i] + (0.0 if i in ends else pauses[i])
               for i in range(len(toks))]

    # Bornes exactes puis UN seul arrondi, partagé entre mots voisins :
    # aucun chevauchement ni trou ne peut naître de l'arrondi.
    bounds: list[float] = []
    speech_ends: list[float] = []
    for (a, b), (s_beg, s_end) in zip(runs, spans):
        # Une virgule non mesurée comme silence étire quand même son mot à
        # l'intérieur de la travée ; celle du DERNIER mot en est retirée
        # (cf. `weights`), c'est le silence suivant qui la porte.
        local = weights[a:b]
        run_w = sum(local) or 1.0
        scale = (s_end - s_beg) / run_w
        t = s_beg
        for n, i in enumerate(range(a, b)):
            bounds.append(t)          # un DÉBUT par mot, la fin vient du span
            t_speech = t + speech[i] * scale
            t += local[n] * scale
            speech_ends.append(min(t_speech, t))

    # `bounds` = un début par mot ; la fin de chaque travée ferme sa tranche.
    words: list[dict] = []
    pos = 0
    for (a, b), (_s_beg, s_end) in zip(runs, spans):
        seg = [round(v, 3) for v in bounds[pos:pos + (b - a)]] + [round(s_end, 3)]
        pos += (b - a)
        for n, i in enumerate(range(a, b)):
            w0, w1 = seg[n], seg[n + 1]
            words.append({
                "i": i, "w": toks[i]["word"], "raw": toks[i]["raw"],
                "punct": toks[i]["punct"],
                "start": w0, "end": max(w0, w1),
                "speech_end": max(w0, min(round(speech_ends[i], 3), w1)),
                "weight": round(speech[i], 4),
            })
    return {"ok": True, "source": "align", "lang": lang,
            "start": round(start, 3), "end": round(end, 3),
            "words": words,
            "spans": [[round(a, 3), round(b, 3)] for a, b in spans],
            "silences": [[round(a, 3), round(b, 3)]
                         for a, b in (silences or [])]}


def align_to_audio(text: str, audio_path: str | Path, *,
                   start: float = 0.0, end: float | None = None,
                   lang: str = "fr", noise_db: float = -33.0,
                   min_silence_s: float = 0.20) -> dict:
    """`align_known_text` sur un vrai fichier audio : durée ffprobe + silences
    ffmpeg mesurés, puis calage. Toujours gratuit et hors ligne.

    `start` est la position du clip sur la timeline du Montage ; les silences
    du fichier (relatifs au fichier) sont décalés de `start`.
    """
    p = Path(audio_path)
    if not p.is_file():
        raise FileNotFoundError(f"Audio introuvable : {p}")
    dur = probe_duration(p)
    if dur <= 0:
        raise ValueError(f"Durée illisible : {p.name}")
    if end is None:
        end = float(start) + dur
    sil = [(a + start, b + start)
           for a, b in detect_silences(p, noise_db=noise_db,
                                       min_silence_s=min_silence_s)]
    out = align_known_text(text, start=start, end=end, silences=sil, lang=lang)
    out["audio"] = p.name
    out["audio_duration_s"] = round(dur, 3)
    return out


def align_narration_clips(clips: list[dict], resolve_audio,
                          *, lang: str = "fr") -> dict:
    """Piste s1 depuis les clips de narration du Montage.

    `clips` = le modèle client de montage_service (chaque clip a `tr`,
    `start`, `end`, et pour la narration un champ `text`). Seuls les clips
    a1/a3 porteurs de texte sont calés. `resolve_audio(clip) -> Path|None`
    est fourni par l'appelant (route) : quand il rend un fichier, les
    silences réels sont mesurés ; sinon on cale sur la durée du clip.

    Retourne `{ok, words, cues, blocks}` sur la timeline GLOBALE du Montage.
    """
    words: list[dict] = []
    blocks: list[dict] = []
    for c in clips or []:
        if not isinstance(c, dict) or c.get("tr") not in ("a1", "a3"):
            continue
        txt = (c.get("text") or "").strip()
        if not txt:
            continue
        try:
            s, e = float(c.get("start") or 0.0), float(c.get("end") or 0.0)
        except (TypeError, ValueError):
            continue
        if e <= s:
            continue
        path = None
        try:
            path = resolve_audio(c) if resolve_audio else None
        except Exception as ex:                       # noqa: BLE001
            logger.warning(f"transcribe: audio du clip {c.get('id')} : {ex}")
        try:
            if path and Path(path).is_file():
                # FENETRE DE SOURCE. `detect_silences` mesure le FICHIER ;
                # un clip fendu ou rogne n'en joue qu'une tranche, a partir
                # de `src_in` et a sa vitesse. La formule d'avant (`t + s`)
                # n'etait juste que pour src_in == 0 et speed == 1 : depuis
                # P3, chaque moitie droite d'une coupe a un src_in > 0 et le
                # panneau se recharge apres CHAQUE coupe.
                sil = silences_to_timeline(
                    detect_silences(path), s, e,
                    src_in=float(c.get("srcIn") or c.get("src_in") or 0.0),
                    speed=float(c.get("speed") or 0.0) or 1.0)
                res = align_known_text(txt, start=s, end=e, silences=sil,
                                       lang=lang)
                res["audio"] = Path(path).name
            else:
                res = align_known_text(txt, start=s, end=e, lang=lang)
        except ValueError as ex:
            logger.warning(f"transcribe: clip {c.get('id')} non calé : {ex}")
            continue
        base = len(words)
        for w in res["words"]:
            w = dict(w)
            w["i"] += base
            w["clip"] = c.get("id")
            words.append(w)
        blocks.append({"clip": c.get("id"), "start": res["start"],
                       "end": res["end"], "words": len(res["words"]),
                       "silences": res["silences"], "audio": res.get("audio")})
    return {"ok": True, "source": "align", "words": words,
            "cues": group_words(words), "blocks": blocks}


# ════════════════════════════════════════════════════════════════════════════
#  5. Groupage en répliques + export
# ════════════════════════════════════════════════════════════════════════════

CHARS_PER_SUBTITLE_DEFAULT = 42


def group_words(words: list[dict], *, max_chars: int = CHARS_PER_SUBTITLE_DEFAULT,
                max_dur_s: float = 6.0, max_gap_s: float = 0.7) -> list[dict]:
    """Mots horodatés → répliques (l'équivalent du curseur « Chars per
    subtitle » de la barre, mais qui respecte aussi la ponctuation, la durée
    maximale d'une réplique et les silences).

    Coupe : dépassement de `max_chars`, de `max_dur_s`, trou > `max_gap_s`
    (donc un silence détecté), ou ponctuation forte.
    """
    max_chars = max(8, min(200, int(max_chars or CHARS_PER_SUBTITLE_DEFAULT)))
    cues: list[dict] = []
    cur: list[dict] = []

    def _flush():
        if not cur:
            return
        cues.append({
            "start": cur[0]["start"],
            "end": max(w["end"] for w in cur),
            "text": " ".join(w["raw"] for w in cur),
            "words": [{"w": w["raw"], "start": w["start"],
                       "end": w["end"], "speech_end": w["speech_end"]}
                      for w in cur],
        })
        cur.clear()

    for w in words or []:
        if cur:
            nxt = len(" ".join(x["raw"] for x in cur)) + 1 + len(w["raw"])
            gap = w["start"] - cur[-1]["end"]
            if (nxt > max_chars
                    or w["end"] - cur[0]["start"] > max_dur_s
                    or gap > max_gap_s
                    or w.get("clip") != cur[-1].get("clip")):
                _flush()
        cur.append(w)
        if w.get("punct") and set(w["punct"]) & _PUNCT_PREF:
            _flush()
    _flush()
    return cues


# ------------------------------------------------- mots de remplissage ---
#: DEUX sacs, et pas un seul. La difference n'est pas de degre : elle decide
#: de ce qu'un bouton a le droit d'emporter SANS qu'on lise.
#:
#: HESITATIONS — des non-mots. « euh », « hum », « um », « uh » ne veulent
#: rien dire nulle part ; les retirer en bloc ne peut pas detruire une
#: phrase.
#:
#: TICS — des mots PLEINS qui servent souvent de bequille. MESURE le
#: 04/09/2026 sur deux narrations qui ne contiennent PAS UNE hesitation :
#: « Voilà pourquoi la marée monte. Enfin, ce genre de détail change tout,
#: quoi qu on en dise. Bon, hein, ben oui. » donne CINQ plages et emporte
#: « Voilà », « Enfin », « genre », « quoi », « hein », « ben » — dont
#: quatre portent la phrase. L'equivalent anglais donne TROIS plages et SEPT
#: mots, dont « right » et « Okay » avales dans la meme plage que « um » et
#: « uh », donc inseparables d'eux. Un bouton qui emporte tout cela « sans
#: dire lesquels » ne tient pas la promesse que le reste du module fait.
#:
#: D'ou la regle : le bouton EN BLOC ne prend que les hesitations ; les tics
#: sont MARQUES a l'ecran et ne se coupent qu'a la selection. Et deux mots
#: voisins de sacs DIFFERENTS ne fusionnent jamais — sans quoi « right »
#: repartirait avec « um » quoi qu'on decide ici.
HESITATIONS = {
    "fr": {"euh", "heu", "hum", "hmm", "heum"},
    "en": {"um", "uh", "er", "erm", "hmm"},
}
TICS = {
    "fr": {"bah", "ben", "hein", "voilà", "genre", "enfin", "quoi"},
    "en": {"like", "okay", "so", "well", "right"},
}
#: L'union — ce qui est MARQUE a l'ecran. Conserve sous ce nom : c'est le
#: vocabulaire que le reste du module et les bancs connaissent.
FILLERS = {k: HESITATIONS[k] | TICS[k] for k in HESITATIONS}

#: `_fold` (celui de CE module) ne retire PAS la ponctuation : il faut donc
#: la retirer ici. Celui de subtitle_service le ferait, mais il retire aussi
#: les DIACRITIQUES, et « voilà » y deviendrait « voila » — absent du sac,
#: donc jamais reconnu. Mesure : backend/tests/test_montage_texte.py, [2].
_FILLER_STRIP = " \t\r\n.,;:!?…«»\"'()[]"

#: Garde contre le BRUIT FLOTTANT, et rien d'autre : deux mots dont les temps
#: se touchent au millieme pres sont la meme plage. MESURE sur le seul
#: producteur de ces temps (`align_known_text`) : a l'interieur d'une travee
#: de parole l'ecart entre deux mots vaut EXACTEMENT 0,0 (les bornes sont
#: partagees), et a travers un silence il vaut au moins 0,20 s (le seuil de
#: `detect_silences`). Aucune valeur entre les deux ne change quoi que ce
#: soit. Ce nombre ne separe donc pas « la respiration du locuteur » — une
#: respiration EST un silence, elle est deja de l'autre cote ; il protege
#: seulement contre un arrondi ou un calage venu d'ailleurs.
_FILLER_JOIN_S = 0.02


def _filler_kind(folded: str, lang2: str) -> str | None:
    """« hesitation », « tic », ou None si le mot n'est ni l'un ni l'autre."""
    if folded in HESITATIONS.get(lang2, HESITATIONS["fr"]):
        return "hesitation"
    if folded in TICS.get(lang2, TICS["fr"]):
        return "tic"
    return None


def find_fillers(words, lang: str = "fr", kind: str = "all") -> list[dict]:
    """Plages de mots de remplissage, voisines DE MEME NATURE fusionnees.

    Rend `[{start, end, kind, words:[i]}]`, dans l'ordre de la liste recue.
    `kind` vaut « hesitation » (un non-mot : euh, hum, um, uh) ou « tic » (un
    mot plein qui sert de bequille : voilà, genre, well, right).

    `words` est la liste PLATE des mots horodates (`{i?, w, start, end}`) —
    celle que `align_*` produit, ou celle que la route aplatit depuis des
    repliques.

    Le parametre `kind` FILTRE : « all » (defaut) rend les deux natures,
    « hesitation » ne rend que les non-mots. C'est ce que demande le bouton
    « retirer les N euh », qui coupe sans qu'on relise.

    Deux plages voisines ne fusionnent que si elles sont de MEME nature :
    sinon un « right » colle a un « um » repartirait avec lui, et aucun
    filtrage ne pourrait plus les separer.

    Un mot sans `start`/`end` (ou dont les temps ne se lisent pas) n'est
    JAMAIS une plage : on ne coupe pas a l'aveugle. `i` absent retombe sur
    la POSITION du mot dans la liste — c'est l'index dont l'ecran se sert
    pour surligner le bon bouton, et un `-1` ne designerait rien.
    """
    lang2 = str(lang)[:2].lower()
    if lang2 not in HESITATIONS:
        lang2 = "fr"
    want = str(kind or "all").lower()
    out: list[dict] = []
    for idx, w in enumerate(words or []):
        if not isinstance(w, dict):
            continue
        if w.get("start") is None or w.get("end") is None:
            continue
        k = _filler_kind(
            _fold(str(w.get("w") or w.get("word") or "")).strip(_FILLER_STRIP),
            lang2)
        if k is None or (want != "all" and k != want):
            continue
        try:
            s, e = round(float(w["start"]), 3), round(float(w["end"]), 3)
        except (TypeError, ValueError):
            continue          # un temps illisible n'est pas un temps
        if e < s:
            s, e = e, s
        try:
            wi = int(w.get("i", idx))
        except (TypeError, ValueError):
            wi = idx
        if (out and out[-1]["kind"] == k
                and abs(out[-1]["end"] - s) < _FILLER_JOIN_S):
            out[-1]["end"] = e
            out[-1]["words"].append(wi)
        else:
            out.append({"start": s, "end": e, "kind": k, "words": [wi]})
    return out


def silences_to_timeline(sil, start: float, end: float, *,
                         src_in: float = 0.0, speed: float = 1.0) -> list:
    """Silences mesures dans le FICHIER -> temps de la TIMELINE.

    Un clip joue la fenetre de source `[src_in, src_in + (end-start)*speed[`
    sur l'intervalle `[start, end[` : le temps de fichier `t` tombe donc en
    `start + (t - src_in) / speed`, pas en `t + start`.

    L'ancienne formule (`t + start`) n'etait juste que pour `src_in == 0` et
    `speed == 1`. P3 fend les clips a longueur de journee — chaque moitie
    droite a un `src_in > 0` — et le panneau se RECHARGE apres chaque coupe :
    des la deuxieme coupe d'une seance, les mots auraient ete cales sur les
    silences du DEBUT du fichier. Ce n'etait pas « deja vrai du rognage » :
    le rognage est occasionnel, ici c'est la boucle de la fonction.

    Ce qui sort du clip est ecarte, ce qui le chevauche est borne.
    """
    sp = float(speed) if speed and float(speed) > 0 else 1.0
    si = max(0.0, float(src_in or 0.0))
    s0, e0 = float(start), float(end)
    out = []
    for a, b in sil or []:
        ta = s0 + (float(a) - si) / sp
        tb = s0 + (float(b) - si) / sp
        ta, tb = max(s0, ta), min(e0, tb)
        if tb > ta:
            out.append((round(ta, 4), round(tb, 4)))
    return out


def _ts(t: float, sep: str = ",") -> str:
    t = max(0.0, float(t))
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(cues: list[dict]) -> str:
    """SubRip. Gratuit, local, sans compte — la barre exige un abonnement."""
    out = []
    for n, c in enumerate(cues or [], 1):
        out.append(f"{n}\n{_ts(c['start'])} --> {_ts(c['end'])}\n"
                   f"{c['text']}\n")
    return "\n".join(out)


def to_vtt(cues: list[dict]) -> str:
    """WebVTT."""
    out = ["WEBVTT", ""]
    for c in cues or []:
        out.append(f"{_ts(c['start'], '.')} --> {_ts(c['end'], '.')}")
        out.append(c["text"])
        out.append("")
    return "\n".join(out)


def to_txt(cues: list[dict]) -> str:
    """Transcription nue, sans horodatage."""
    return "\n".join(c["text"] for c in (cues or []))


# ════════════════════════════════════════════════════════════════════════════
#  6. Transcription (texte inconnu) — coût et durée ANNONCÉS D'ABORD
# ════════════════════════════════════════════════════════════════════════════

# Seuls des chemins à horodatage AU MOT. `rt` = facteur temps réel observé
# (fraction de la durée audio), `overhead_s` = latence fixe (upload + file
# d'attente) ; les deux servent l'ETA affichée avant lancement.
STT_PROVIDERS = {
    "elevenlabs": {
        "label": "ElevenLabs Scribe v1",
        "model": "scribe_v1",
        "usd_per_min": 0.0067,     # ≈ 0,40 $/h, tarif public Scribe v1
        "max_mb": 1000,
        "rt": 0.10, "overhead_s": 3.0,
        "settings_key": "ELEVENLABS_API_KEY",
    },
    "openai": {
        "label": "OpenAI Whisper-1",
        "model": "whisper-1",      # gpt-4o-transcribe ne rend PAS le mot
        "usd_per_min": 0.006,
        "max_mb": 25,
        "rt": 0.15, "overhead_s": 4.0,
        "settings_key": "OPENAI_API_KEY",
    },
}
STT_ORDER = ("elevenlabs", "openai")


def _key(provider: str) -> str:
    try:
        from app.config import settings
        return (getattr(settings, STT_PROVIDERS[provider]["settings_key"], "")
                or "").strip()
    except Exception:                                  # noqa: BLE001
        return ""


def _rate(provider: str) -> float:
    """$/minute, overrides `pricing.json` honorés (clé `stt_usd_per_min`)."""
    base = float(STT_PROVIDERS[provider]["usd_per_min"])
    try:
        from app.services import pricing
        table = pricing.load().get("stt_usd_per_min") or {}
        return float(table.get(provider, base))
    except Exception:                                  # noqa: BLE001
        return base


def available_providers() -> list[dict]:
    """Catalogue STT avec `available` (clé présente) — pour l'UI."""
    out = []
    for pid in STT_ORDER:
        spec = STT_PROVIDERS[pid]
        out.append({"id": pid, "label": spec["label"], "model": spec["model"],
                    "word_timestamps": True, "max_mb": spec["max_mb"],
                    "usd_per_min": round(_rate(pid), 5),
                    "available": bool(_key(pid))})
    return out


def resolve_provider(provider: str | None = None) -> str | None:
    """Fournisseur demandé s'il est configuré, sinon le premier disponible."""
    if provider:
        pid = str(provider).strip().lower()
        if pid not in STT_PROVIDERS:
            raise ValueError(f"Fournisseur STT inconnu : {provider!r} — "
                             f"connus : {', '.join(STT_PROVIDERS)}")
        return pid if _key(pid) else None
    return next((p for p in STT_ORDER if _key(p)), None)


def estimate_transcription(duration_s: float,
                           provider: str | None = None) -> dict:
    """COÛT et DURÉE annoncés AVANT de lancer (convention de l'app).

    Retourne `{ok, provider, label, model, duration_s, usd, eta_s,
    word_timestamps, available, breakdown}`. `ok:false` + `reason` si aucun
    fournisseur n'est configuré : l'UI propose alors le chemin gratuit
    (calage d'un texte connu) plutôt qu'un bouton mort.
    """
    dur = max(0.0, float(duration_s or 0.0))
    pid = resolve_provider(provider)
    if not pid:
        want = (provider or "").strip().lower()
        return {"ok": False, "provider": want or None, "duration_s": round(dur, 3),
                "usd": 0.0, "eta_s": 0,
                "reason": "Aucune clé de transcription configurée (Réglages : "
                          "ElevenLabs ou OpenAI). Le calage d'un texte connu "
                          "reste disponible, gratuit et hors ligne.",
                "providers": available_providers()}
    spec = STT_PROVIDERS[pid]
    usd = dur / 60.0 * _rate(pid)
    eta = spec["overhead_s"] + spec["rt"] * dur
    return {"ok": True, "provider": pid, "label": spec["label"],
            "model": spec["model"], "duration_s": round(dur, 3),
            "usd": round(usd, 4), "eta_s": int(round(eta)),
            "word_timestamps": True, "available": True,
            "breakdown": [{"provider": pid, "label": f"Transcription ({spec['label']})",
                           "units": round(dur / 60.0, 3), "unit": "min",
                           "usd": round(usd, 4)}]}


def _check_size(path: Path, pid: str) -> None:
    mb = path.stat().st_size / 1_048_576
    cap = STT_PROVIDERS[pid]["max_mb"]
    if mb > cap:
        raise ValueError(
            f"{path.name} pèse {mb:.1f} Mo — {STT_PROVIDERS[pid]['label']} "
            f"plafonne à {cap} Mo. Extraire l'audio ou découper le plan.")


def _norm_words(raw: list[dict], key_text: str) -> list[dict]:
    """Mots bruts d'un fournisseur → forme interne (mêmes champs que le calage)."""
    words: list[dict] = []
    for r in raw or []:
        if (r.get("type") or "word") != "word":
            continue                       # scribe : « spacing », « audio_event »
        txt = str(r.get(key_text) or "").strip()
        if not txt:
            continue
        try:
            s, e = float(r.get("start")), float(r.get("end"))
        except (TypeError, ValueError):
            continue
        body = txt
        punct = ""
        while body and body[-1] in _TRAIL_PUNCT:
            punct = body[-1] + punct
            body = body[:-1]
        words.append({"i": len(words), "w": body or txt, "raw": txt,
                      "punct": punct, "start": round(s, 3),
                      "end": round(max(s, e), 3),
                      "speech_end": round(max(s, e), 3),
                      "weight": 0.0})
    return words


def transcribe(audio_path: str | Path, *, provider: str | None = None,
               language: str | None = None, timeout: float = 600.0) -> dict:
    """Transcrit un média dont le texte est INCONNU, avec horodatage AU MOT.

    Appel réseau PAYANT : appeler `estimate_transcription()` d'abord et
    faire confirmer, comme partout ailleurs dans l'app.
    Retourne la même forme que `align_known_text` (`words`, plus `cues`,
    `text`, `usd_estimated`).
    """
    p = Path(audio_path)
    if not p.is_file():
        raise FileNotFoundError(f"Média introuvable : {p}")
    pid = resolve_provider(provider)
    if not pid:
        raise RuntimeError(
            "Aucune clé de transcription configurée (Réglages : ElevenLabs "
            "ou OpenAI).")
    _check_size(p, pid)
    dur = probe_duration(p)
    est = estimate_transcription(dur, pid)
    logger.info(f"transcribe: {p.name} ({dur:.1f}s) via {pid} "
                f"≈ {est['usd']:.4f} $ / ~{est['eta_s']}s")

    import httpx
    try:
        from app.config import SSL_VERIFY
    except Exception:                                  # noqa: BLE001
        SSL_VERIFY = True

    with p.open("rb") as fh:
        if pid == "elevenlabs":
            data = {"model_id": STT_PROVIDERS[pid]["model"],
                    "timestamps_granularity": "word", "diarize": "false"}
            if language:
                data["language_code"] = str(language)[:5]
            r = httpx.post("https://api.elevenlabs.io/v1/speech-to-text",
                           headers={"xi-api-key": _key(pid)},
                           data=data, files={"file": (p.name, fh)},
                           timeout=timeout, verify=SSL_VERIFY)
            if r.status_code != 200:
                raise RuntimeError(f"ElevenLabs: HTTP {r.status_code} — "
                                   f"{r.text[:300]}")
            body = r.json()
            words = _norm_words(body.get("words"), "text")
            text = (body.get("text") or "").strip()
            lang = body.get("language_code") or language or ""
        else:
            # `data` DOIT être un mapping : httpx ne sait construire un corps
            # multipart qu'à partir de `.items()`. Une liste de couples passe
            # la validation puis explose dans h11 (« expected a bytes-like
            # object, tuple found »). Les clés répétées se donnent en LISTE.
            data = {"model": STT_PROVIDERS[pid]["model"],
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": ["word"]}
            if language:
                data["language"] = str(language)[:5]
            r = httpx.post("https://api.openai.com/v1/audio/transcriptions",
                           headers={"Authorization": f"Bearer {_key(pid)}"},
                           data=data, files={"file": (p.name, fh)},
                           timeout=timeout, verify=SSL_VERIFY)
            if r.status_code != 200:
                raise RuntimeError(f"OpenAI: HTTP {r.status_code} — "
                                   f"{r.text[:300]}")
            body = r.json()
            words = _norm_words(body.get("words"), "word")
            text = (body.get("text") or "").strip()
            lang = body.get("language") or language or ""

    if not words:
        raise RuntimeError(
            f"{STT_PROVIDERS[pid]['label']} n'a rendu aucun mot horodaté "
            f"(média muet ou format refusé).")
    return {"ok": True, "source": pid, "lang": lang,
            "start": words[0]["start"], "end": words[-1]["end"],
            "words": words, "cues": group_words(words), "text": text,
            "audio": p.name, "audio_duration_s": round(dur, 3),
            "usd_estimated": est["usd"], "silences": [], "spans": []}


# ════════════════════════════════════════════════════════════════════════════
#  7. Garde-fou chemin (mêmes règles que fs_guard / _lut_path)
# ════════════════════════════════════════════════════════════════════════════

_MEDIA_EXT = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac",
              ".mp4", ".mov", ".webm", ".m4v")


def resolve_media(name: str, folder: Path) -> Path | None:
    """Nom venant du client → fichier média réduit au BASENAME, contenu dans
    `folder`, extension connue et fichier existant. Sinon None.

    Même garde-fou que `_lut_path` (effects_engine) : rien d'autre ne doit
    pouvoir désigner un fichier arbitraire du disque.
    """
    if not name:
        return None
    safe = Path(str(name)).name
    if not safe or safe != str(name):
        return None
    if not safe.lower().endswith(_MEDIA_EXT):
        return None
    p = folder / safe
    try:
        if not p.is_file():
            return None
        p.resolve().relative_to(Path(folder).resolve())
    except (OSError, ValueError):
        return None
    return p


__all__ = [
    "tokenize", "syllables", "word_weight", "pause_weight",
    "probe_duration", "parse_silencedetect", "detect_silences",
    "speech_spans", "align_known_text", "align_to_audio",
    "align_narration_clips", "group_words", "to_srt", "to_vtt", "to_txt",
    "STT_PROVIDERS", "available_providers", "resolve_provider",
    "estimate_transcription", "transcribe", "resolve_media",
    "CHARS_PER_SUBTITLE_DEFAULT",
]
