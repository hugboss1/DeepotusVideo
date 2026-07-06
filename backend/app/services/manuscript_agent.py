"""v1.19 (Atelier) — agent d'ingestion de manuscrit complet.

Quatre passes (voir spec 2026-07-06-atelier-manuscrit-design.md) :
1. segment_chapters : découpe le texte en chapitres (titres importés).
2. extract_chapter  : extraction LLM par chapitre → entités des 6 kinds
   (character/place/object/date/ambiance/decor) avec alias, description
   observée et citations verbatim.
3. consolidate      : relecture globale LLM — fusion des doublons/alias
   inter-chapitres, description canonique ; le fichier compagnon de
   l'auteur est fourni comme source d'autorité.
4. compute_spans    : surlignage — mentions (nom+alias, bornes de mots) +
   passages cités, par chapitre.

Les appels LLM sont synchrones (summarizer._chat_dispatch) : l'orchestrateur
(routes) les exécute dans un thread et met à jour la progression du job.
"""
import json
import re
import unicodedata

from loguru import logger

KINDS = ("character", "place", "object", "date", "ambiance", "decor")

KIND_HINTS = {
    "character": "personnages (avec leurs caractéristiques physiques et traits)",
    "place": "lieux (villes, bâtiments, pièces, paysages)",
    "object": "objets importants / accessoires récurrents",
    "date": "dates, époques, moments précis, marqueurs temporels",
    "ambiance": "ambiances (lumière, météo, sons, ton émotionnel d'une scène)",
    "decor": "indications de décor / set dressing (mobilier, matières, signalétique)",
}

_CHUNK = 11000
_MAX_ENTITIES = 150

# ───────────────────────── 1. segmentation ─────────────────────────

_HEAD_RE = re.compile(
    r"^\s*(?:(?:chapitre|chapter|partie|part|livre|book)\s+"
    r"(?:[0-9]{1,3}|[ivxlc]{1,7}|[a-zà-ü' -]{1,30})|prologue|"
    r"épilogue|epilogue|interlude|prélude|prelude)\b.{0,60}$", re.I)
# Numéral seul, ou numéral + séparateur/espace puis un titre court. Le
# séparateur est OBLIGATOIRE avant le texte, sinon toute phrase commençant
# par I/V/X/L/C ("Vane serre…") serait prise pour un chiffre romain.
_NUMHEAD_RE = re.compile(
    r"^\s*(?:[0-9]{1,3}|[IVXLC]{1,7})"
    r"(?:\s*[.):—–-]\s*.{0,60}|\s+[A-ZÀ-Ü].{0,60})?\s*$")
_CAPS_RE = re.compile(r"^\s*[0-9]*\s*[A-ZÀ-Ü][A-ZÀ-Ü0-9 ,'’&\-:!?.]{3,70}\s*$")


def segment_chapters(text: str) -> list[dict]:
    """Découpe un manuscrit en [{title, text}] via les heuristiques de titres.
    Repli : un seul chapitre. Les segments minuscules (<200 car.) sont fusionnés
    avec le suivant (page de garde, dédicace…)."""
    lines = text.splitlines()
    marks: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        # "\x1f" = marqueur de titre posé par le lecteur docx (styles Heading),
        # ce qui importe les titres même sans convention typographique.
        # NB: \x1f compte comme whitespace pour str.strip() — tester AVANT.
        if "\x1f" in ln:
            marks.append((i, ln.replace("\x1f", "").strip()))
            continue
        t = ln.strip()
        if not t or len(t) > 80:
            continue
        prev_blank = i == 0 or not lines[i - 1].strip()
        if not prev_blank:
            continue
        if _HEAD_RE.match(t):
            marks.append((i, t))
        elif _CAPS_RE.match(t) and not t.rstrip().endswith((",", ";")):
            marks.append((i, t))
        elif _NUMHEAD_RE.match(t) and len(t) <= 40:
            marks.append((i, t))
    if not marks or marks[0][0] > 0:
        marks.insert(0, (0, ""))
    out = []
    for k, (start, title) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        body_start = start + (1 if title else 0)
        body = "\n".join(lines[body_start:end]).strip()
        if not body and not title:
            continue
        out.append({"title": title or "", "text": body})
    # anti-fragments : un segment SANS titre et minuscule (<80 car. — page de
    # garde, dédicace, séparateur) est fondu dans son voisin. On ne fusionne
    # JAMAIS un vrai chapitre titré, même court.
    merged: list[dict] = []
    for seg in out:
        titled = bool(seg["title"])
        tiny = len(seg["text"]) < 80
        if merged and tiny and not titled:
            merged[-1]["text"] = (merged[-1]["text"] + "\n\n" + seg["text"]).strip()
            continue
        if merged and len(merged[-1]["text"]) < 80 and not merged[-1]["title"]:
            prev = merged.pop()
            seg = dict(seg)
            seg["text"] = (prev["text"] + "\n\n" + seg["text"]).strip()
        merged.append(dict(seg))
    for i, seg in enumerate(merged):
        if not seg["title"]:
            seg["title"] = f"Chapitre {i + 1}"
    return merged or [{"title": "Chapitre 1", "text": text.strip()}]


# ───────────────────────── helpers LLM ─────────────────────────

def _parse_json(out: str):
    txt = (out or "").strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt)
        txt = re.sub(r"\n?```$", "", txt).strip()
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = txt.find(opener), txt.rfind(closer)
        if i >= 0 and j > i:
            try:
                return json.loads(txt[i:j + 1])
            except Exception:
                continue
    return None


def _norm_entity(it: dict) -> dict | None:
    if not isinstance(it, dict):
        return None
    kind = str(it.get("kind") or "").strip().lower()
    name = str(it.get("name") or "").strip()
    if kind not in KINDS or not name:
        return None
    aliases = [str(a).strip() for a in (it.get("aliases") or [])
               if str(a).strip() and str(a).strip().lower() != name.lower()]
    quotes = [str(q).strip() for q in (it.get("quotes") or []) if str(q).strip()]
    return {"kind": kind, "name": name[:120], "aliases": aliases[:8],
            "description": str(it.get("description") or "").strip(),
            "quotes": quotes[:6]}


# ───────────────────── 2. extraction par chapitre ─────────────────────

def extract_chapter(chapter_title: str, chapter_text: str,
                    roster: list[dict], lang: str = "fr") -> list[dict]:
    """Extraction LLM des entités d'un chapitre (chunké). roster = entités déjà
    connues, pour la stabilité des noms d'un chapitre à l'autre."""
    from app.services.summarizer import _chat_dispatch
    langname = "French" if lang.startswith("fr") else "English"
    known = "\n".join(f"- {e['name']} ({e['kind']})"
                      for e in roster[:80]) or "(none yet)"
    cats = "\n".join(f"- \"{k}\": {v}" for k, v in KIND_HINTS.items())
    results: list[dict] = []
    chunks = [chapter_text[i:i + _CHUNK]
              for i in range(0, len(chapter_text), _CHUNK)] or [""]
    for ci, chunk in enumerate(chunks):
        system = ("You are a meticulous script supervisor building the "
                  "production bible of a narrated animation. Return ONLY valid JSON.")
        prompt = (
            f"Read this excerpt of the chapter \"{chapter_title}\" and list EVERY "
            f"entity of these categories:\n{cats}\n\n"
            f"Already-known entities (reuse these EXACT names if they appear):\n{known}\n\n"
            f"For each entity return: \"kind\" (one of {list(KINDS)}), \"name\" (short, "
            f"canonical, in {langname}), \"aliases\" (other names/nicknames used in the "
            f"text for it), \"description\" (what THIS text reveals: physical traits, "
            f"role, look — 1-3 sentences in {langname}), \"quotes\" (1-4 SHORT verbatim "
            f"snippets copied EXACTLY from the text, ≤15 words each, that describe or "
            f"establish it). Be exhaustive but no invented facts.\n"
            f"Return ONLY a JSON array.\n\nText:\n{chunk}")
        out, _prov = _chat_dispatch(prompt, system, 6000)
        data = _parse_json(out) or []
        for it in (data if isinstance(data, list) else []):
            ne = _norm_entity(it)
            if ne:
                results.append(ne)
        logger.info(f"manuscrit: '{chapter_title}' chunk {ci+1}/{len(chunks)} "
                    f"-> {len(results)} entités cumulées")
    return results


# ───────────────────── 3. consolidation globale ─────────────────────

def consolidate(raw: list[dict], companion: str = "", lang: str = "fr") -> list[dict]:
    """Relecture globale : fusionne les doublons/alias, produit la description
    canonique. `raw` = entités de tous les chapitres (avec doublons)."""
    from app.services.summarizer import _chat_dispatch
    langname = "French" if lang.startswith("fr") else "English"
    # pré-groupage local pour réduire le payload LLM
    grouped: dict[tuple, dict] = {}
    for e in raw:
        key = (e["kind"], e["name"].strip().lower())
        g = grouped.setdefault(key, {"kind": e["kind"], "name": e["name"],
                                     "aliases": set(), "descs": [], "quotes": []})
        g["aliases"].update(e.get("aliases") or [])
        if e.get("description"):
            g["descs"].append(e["description"])
        g["quotes"].extend(e.get("quotes") or [])
    payload = [{"kind": g["kind"], "name": g["name"],
                "aliases": sorted(g["aliases"])[:8],
                "observations": g["descs"][:6]}
               for g in grouped.values()][:_MAX_ENTITIES]
    comp = f"\n\nAuthor's companion notes (AUTHORITATIVE source):\n{companion[:8000]}" \
        if companion.strip() else ""
    system = ("You are the continuity supervisor consolidating a production "
              "bible after reading the FULL manuscript. Return ONLY valid JSON.")
    prompt = (
        f"Consolidate this entity list extracted chapter by chapter. MERGE entries "
        f"that are the same entity under different names (put the variants in "
        f"\"aliases\"), and write ONE canonical \"description\" per entity in "
        f"{langname} (2-4 sentences, all confirmed traits, useful for generating a "
        f"consistent visual reference). Keep \"kind\" unchanged. Drop trivial "
        f"one-off entities that don't matter for production.\n"
        f"Return ONLY a JSON array of objects {{kind, name, aliases, description}}."
        f"{comp}\n\nEntities:\n{json.dumps(payload, ensure_ascii=False)}")
    out, _prov = _chat_dispatch(prompt, system, 8000)
    data = _parse_json(out)
    final = []
    for it in (data if isinstance(data, list) else []):
        ne = _norm_entity(it)
        if ne:
            final.append(ne)
    if not final:  # repli sans LLM : le groupage local fait déjà l'essentiel
        logger.warning("manuscrit: consolidation LLM vide — repli local")
        final = [{"kind": g["kind"], "name": g["name"],
                  "aliases": sorted(g["aliases"])[:8],
                  "description": " ".join(g["descs"][:3])[:600], "quotes": []}
                 for g in grouped.values()][:_MAX_ENTITIES]
    # ré-attache les citations collectées (par kind+nom OU alias)
    qidx: dict[tuple, list] = {}
    for g in grouped.values():
        qidx[(g["kind"], g["name"].strip().lower())] = g["quotes"][:10]
    for e in final:
        qs = list(qidx.get((e["kind"], e["name"].strip().lower()), []))
        for a in e.get("aliases") or []:
            qs.extend(qidx.get((e["kind"], a.strip().lower()), []))
        e["quotes"] = qs[:10]
    return final


# ───────────── 5. adaptation scénario (v1.20, phase A) ─────────────

LIGHTING_VOCAB = ("soft natural window light", "golden hour rim light",
                  "neon city lights, cyan and magenta", "warm tungsten practicals",
                  "overcast diffused light", "dark moody chiaroscuro",
                  "bioluminescent underwater glow", "rhythmic strobe pulses")
CAMERA_VOCAB = ("slow push-in", "slow pull-out", "360-degree orbit",
                "tracking shot", "handheld with subtle shake",
                "static, locked-off", "low angle dramatic", "rack focus reveal",
                "dolly zoom (vertigo effect)", "whip pan transition",
                "crane shot descending")
TIMES_OF_DAY = ("JOUR", "NUIT", "AUBE", "CRÉPUSCULE", "MATIN", "SOIR")

# Doctrine d'adaptation embarquée dans le prompt (règles de l'art —
# sources: fountain.io/syntax, StudioBinder screenplay format, Story Sense
# scene headings, guides d'adaptation roman→scénario Shore Scripts /
# Writer's Digest / Author Media).
SCREENPLAY_DOCTRINE = """RULES OF THE CRAFT (apply strictly):
1. SHOW, DON'T TELL — inner thoughts become visible actions, gestures,
   glances, physical business. Never narrate feelings in action lines.
2. Every scene must do AT LEAST TWO of: advance the plot, reveal character,
   raise tension. A scene that does only one thing gets merged or cut.
3. Scene heading (slugline): "INT." or "EXT." (or "INT./EXT.") + LOCATION in
   CAPS + " - " + time of day. Reuse the EXACT bible location names.
4. Action lines: present tense, concrete, ≤ 4 lines per block, only what the
   CAMERA SEES and the AUDIENCE HEARS. Introduce a character in CAPS on first
   appearance.
5. Dialogue: character cue in CAPS (EXACT bible names), lines short and
   loaded with subtext — characters rarely say exactly what they mean.
   Parentheticals only when the delivery is not obvious, lowercase, brief.
6. Lighting: choose a lighting that SERVES the narrative beat (dread, hope,
   revelation...) — prefer the provided vocabulary, adapt freely if needed.
7. Camera: one primary camera intention per scene supporting the beat —
   prefer the provided vocabulary.
8. Keep the author's tone and imagery; condense ruthlessly; do not invent
   plot events that are not in or implied by the chapter.
9. 1 script page ≈ 1 minute — aim for scenes of 15 s to 90 s each."""


def adapt_chapter(chapter_title: str, chapter_text: str,
                  bible: list[dict], lang: str = "fr") -> list[dict]:
    """Adapte un chapitre de roman en scènes de scénario (format Fountain),
    SANS modifier le manuscrit. Retourne [{slugline_location, int_ext,
    time_of_day, fountain, lighting, camera_notes, mood, characters, decor,
    source_excerpt}]."""
    from app.services.summarizer import _chat_dispatch
    langname = "French" if lang.startswith("fr") else "English"
    places = [e for e in bible if e["kind"] == "place"]
    chars = [e for e in bible if e["kind"] == "character"]
    decors = [e for e in bible if e["kind"] in ("decor", "ambiance")]
    roster = (
        "KNOWN LOCATIONS:\n" +
        ("\n".join(f"- {e['name']}: {(e['description'] or '')[:100]}" for e in places[:40]) or "(none)") +
        "\n\nKNOWN CHARACTERS:\n" +
        ("\n".join(f"- {e['name']}: {(e['description'] or '')[:100]}" for e in chars[:40]) or "(none)") +
        "\n\nKNOWN DECOR/AMBIANCE ELEMENTS:\n" +
        ("\n".join(f"- {e['name']}" for e in decors[:40]) or "(none)"))
    scenes: list[dict] = []
    chunks = [chapter_text[i:i + _CHUNK]
              for i in range(0, len(chapter_text), _CHUNK)] or [""]
    for ci, chunk in enumerate(chunks):
        system = ("You are a professional screenwriter adapting a novel "
                  "chapter into a screenplay. Return ONLY valid JSON.")
        prompt = (
            f"{SCREENPLAY_DOCTRINE}\n\n{roster}\n\n"
            f"Adapt this part of the chapter \"{chapter_title}\" into screenplay "
            f"SCENES in {langname}. For each scene return:\n"
            f"\"slugline_location\": location name in CAPS (reuse EXACT known "
            f"location names when the scene happens there);\n"
            f"\"int_ext\": \"INT\" | \"EXT\" | \"INT/EXT\";\n"
            f"\"time_of_day\": one of {list(TIMES_OF_DAY)};\n"
            f"\"fountain\": the scene body in Fountain plain-text (action lines, "
            f"CHARACTER cues in caps, dialogue, parentheticals — WITHOUT the "
            f"slugline, it is built separately);\n"
            f"\"lighting\": lighting choice (prefer {list(LIGHTING_VOCAB)});\n"
            f"\"camera_notes\": primary camera intention (prefer {list(CAMERA_VOCAB)}) "
            f"+ one short sentence on WHY it serves the beat;\n"
            f"\"mood\": 2-4 words;\n"
            f"\"characters\": array of character names present (EXACT names);\n"
            f"\"decor\": array of decor/set elements visible (short names — reuse "
            f"known ones, add new ones when the text establishes them);\n"
            f"\"source_excerpt\": first ~10 words of the chapter passage this scene "
            f"adapts, copied verbatim.\n"
            f"Return ONLY a JSON array.\n\nChapter text:\n{chunk}")
        out, _prov = _chat_dispatch(prompt, system, 8000)
        data = _parse_json(out) or []
        for it in (data if isinstance(data, list) else []):
            if not isinstance(it, dict):
                continue
            loc = str(it.get("slugline_location") or "").strip()
            fx = str(it.get("fountain") or "").strip()
            if not loc or not fx:
                continue
            ie = str(it.get("int_ext") or "INT").upper().replace(".", "")
            if ie not in ("INT", "EXT", "INT/EXT"):
                ie = "INT"
            tod = str(it.get("time_of_day") or "JOUR").upper()
            if tod not in TIMES_OF_DAY:
                tod = "JOUR"
            scenes.append({
                "slugline_location": loc[:150],
                "int_ext": ie, "time_of_day": tod, "fountain": fx,
                "lighting": str(it.get("lighting") or "").strip()[:120],
                "camera_notes": str(it.get("camera_notes") or "").strip(),
                "mood": str(it.get("mood") or "").strip()[:120],
                "characters": [str(x).strip() for x in (it.get("characters") or [])
                               if str(x).strip()],
                "decor": [str(x).strip() for x in (it.get("decor") or [])
                          if str(x).strip()][:10],
                "source_excerpt": str(it.get("source_excerpt") or "").strip(),
            })
        logger.info(f"adaptation: '{chapter_title}' chunk {ci+1}/{len(chunks)} "
                    f"-> {len(scenes)} scènes cumulées")
    return scenes


def assemble_fountain(chapter_title: str, scenes: list[dict]) -> str:
    """Assemble le scénario Fountain complet d'un chapitre à partir des scènes
    stockées (dicts de la table Scene, sérialisés)."""
    parts = [f"# {chapter_title}", ""]
    for s in scenes:
        parts.append(s["slugline"])
        parts.append("")
        parts.append((s.get("fountain_text") or "").rstrip())
        parts.append("")
    return "\n".join(parts).strip() + "\n"


# ───────────────────── 4. surlignage (spans) ─────────────────────

def _fold(s: str) -> str:
    """Minuscule sans accents, EN PRÉSERVANT LA LONGUEUR (mapping 1 char → 1
    char) pour que les offsets trouvés dans le texte replié soient directement
    valides dans le texte original. (Un NFD global changerait la longueur sur
    les séquences décomposées → surlignages décalés.)"""
    out = []
    for ch in s:
        d = unicodedata.normalize("NFD", ch)
        base = [c for c in d if unicodedata.category(c) != "Mn"]
        out.append((base[0] if base else ch).lower())
    return "".join(out)


def compute_spans(chapter_text: str, entities: list[dict],
                  per_entity_cap: int = 40) -> list[dict]:
    """Zones à surligner : toutes les mentions (nom + alias, bornes de mots,
    insensible casse/accents) + les passages cités (quotes)."""
    folded = _fold(chapter_text)
    spans: list[dict] = []
    taken: list[tuple[int, int]] = []

    def overlaps(a, b):
        return any(not (b <= s or a >= e) for s, e in taken)

    def add(start, end, ent_id):
        if start < 0 or end <= start or overlaps(start, end):
            return
        spans.append({"start": start, "end": end,
                      "text": chapter_text[start:end], "entity_id": ent_id})
        taken.append((start, end))

    # Passe 1 — les citations d'abord : un passage descriptif cité est plus
    # riche qu'une simple mention de nom, il gagne en cas de chevauchement.
    for e in entities:
        for q in (e.get("quotes") or []):
            fq = _fold(q.strip())
            if len(fq) < 12:
                continue
            i = folded.find(fq)
            if i >= 0:
                add(i, i + len(fq), e["id"])
    # Passe 2 — les mentions (nom + alias, bornes de mots).
    for e in entities:
        ent_id = e["id"]
        count = 0
        terms = [e["name"]] + list(e.get("aliases") or [])
        for term in terms:
            ft = _fold(term.strip())
            if len(ft) < 3:
                continue
            pat = re.compile(r"(?<![0-9a-zà-ÿ])" + re.escape(ft) + r"(?![0-9a-zà-ÿ])")
            for m in pat.finditer(folded):
                if count >= per_entity_cap:
                    break
                add(m.start(), m.end(), ent_id)
                count += 1
    spans.sort(key=lambda s: s["start"])
    return spans
