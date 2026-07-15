"""v1.27 — schéma partagé du planner marketing (style « Sol », 2026-07-15).

Un post de plan n'est plus une simple idée : c'est un bloc structuré prêt à
publier, sur le modèle du document de référence
`DEEPOTUS_Content_Automation_Plan_EN_Structured.docx` (généré par OpenAI Sol)
: caption X finale (liens inclus, ligne de hashtags en fin), variante
Telegram, prompt d'illustration détaillé (VISUAL_PROMPT), texte à l'image,
scripts avatar court/long, CTA, liens, priorité, ratio, notes de
programmation.

Ce module est LE contrat de sortie, partagé par les 4 providers du planner
(anthropic/openai/gemini/ollama) : même prompt système, même nettoyage.
Les champs historiques restent des colonnes de scheduled_posts ; les champs
étendus partent dans la colonne JSON `brief` (voir marketing.materialize_plan).
"""

# Champs étendus conservés dans le brief JSON du post, en plus des colonnes
# historiques title/format/hook/caption/script_idea/image_idea/channels.
# Mapping Sol : VISUAL_PROMPT→image_idea, AVATAR_SCRIPT_SHORT→script_idea,
# X_CAPTION→caption ; le reste vit ici.
BRIEF_FIELDS = [
    "objective", "priority", "aspect_ratio", "tg_caption", "on_image_text",
    "cta", "hashtags", "links", "avatar_script_long", "scheduling_notes",
]

# Bornes de taille par champ (anti-débordement ; Text en DB mais on borne).
_CAPS = {
    "title": 200, "time": 5, "format": 20, "hook": 500, "caption": 4000,
    "script_idea": 2000, "image_idea": 2000, "objective": 500,
    "priority": 20, "aspect_ratio": 30, "tg_caption": 4000,
    "on_image_text": 500, "cta": 300, "hashtags": 300, "links": 1000,
    "avatar_script_short": 1200, "avatar_script_long": 3000,
    "scheduling_notes": 500,
}

_CHANNELS = ("x", "telegram", "youtube", "instagram")

# La sortie étant ~5× plus riche qu'avant, les appels providers doivent
# monter leur max_tokens à cette valeur (sinon JSON tronqué → fallback).
MAX_TOKENS = 8000


def system_prompt(days: int, posts_per_day: int, language: str,
                  pdesc: str = "") -> str:
    """Prompt système commun : plan de posts en blocs structurés complets."""
    return (
        "You are a social media content strategist for short-form video "
        "accounts (memecoins, creator brands). Produce a posting plan as "
        "STRICT JSON, no prose, no markdown fences. Schema: {\"posts\":[{"
        f"\"day_offset\":int (0..{days - 1}),"
        "\"time\":\"HH:MM\","
        "\"title\":str (short internal label),"
        "\"format\":\"image|seedance|heygen|composition|news\","
        "\"hook\":str (the angle in one line),"
        "\"caption\":str,"
        "\"tg_caption\":str,"
        "\"image_idea\":str,"
        "\"on_image_text\":str,"
        "\"script_idea\":str,"
        "\"avatar_script_long\":str,"
        "\"cta\":str,"
        "\"hashtags\":str,"
        "\"links\":str,"
        "\"objective\":str,"
        "\"priority\":\"High|Medium|Low\","
        "\"aspect_ratio\":str (e.g. \"1:1\", \"9:16\"),"
        "\"scheduling_notes\":str,"
        "\"channels\":[\"x\"|\"telegram\"|\"youtube\"|\"instagram\"]}]}. "
        f"Exactly {days * posts_per_day} posts ({posts_per_day}/day over "
        f"{days} days). Language: {language}. {pdesc}"
        "Field rules — every post is a COMPLETE ready-to-publish block: "
        "caption = final X post text, line breaks allowed, at most 2 emojis, "
        "includes the relevant links inline and ENDS with the hashtags line; "
        "tg_caption = Telegram variant, longer and community-oriented, ends "
        "with the useful links list; "
        "image_idea = detailed illustration/video prompt in English "
        "(composition, palette, mood, layout, where the on-image text goes) "
        "usable as-is by an image generator; "
        "on_image_text = the exact words rendered ON the visual; "
        "script_idea = avatar/voice-over script, 10-20 seconds, spoken voice; "
        "avatar_script_long = same speech developed for 25-45 seconds; "
        "cta = the single action asked of the audience; "
        "hashtags = 2-5 tags separated by spaces; "
        "links = the URLs used, separated by ' | '. "
        "Formats map to the user's video tool: image=meme still, "
        "seedance=cinematic clip, heygen=talking avatar, composition="
        "clip+avatar, news=news reaction reel. Vary formats and times "
        "(morning/noon/evening). Captions must follow the persona voice. "
        "NEVER invent URLs, dates or times: only reuse links given in the "
        "briefing; if a needed link or time is unknown, write the "
        "placeholder [INSERT ...] exactly like a professional plan does."
    )


def persona_desc(persona: dict | None) -> str:
    if not persona:
        return ""
    return (f"Persona: {persona.get('name', '')}. "
            f"Tone: {persona.get('tone', '')}. "
            f"Audience: {persona.get('audience', '')}. ")


def _s(p: dict, key: str, default: str = "") -> str:
    v = p.get(key, default)
    return str(v if v is not None else "")[:_CAPS.get(key, 2000)]


def clean_posts(posts: list, days: int) -> list[dict] | None:
    """Valide/borne la sortie LLM (tolérante : un post cassé est ignoré).
    Garantit que la caption se termine par la ligne de hashtags."""
    clean: list[dict] = []
    for p in posts or []:
        if not isinstance(p, dict):
            continue
        try:
            out = {
                "day_offset": max(0, min(days - 1,
                                         int(p.get("day_offset", 0)))),
                "time": _s(p, "time", "12:00") or "12:00",
                "title": _s(p, "title"),
                "format": _s(p, "format", "image") or "image",
                "hook": _s(p, "hook"),
                "caption": _s(p, "caption"),
                "script_idea": _s(p, "script_idea"),
                "image_idea": _s(p, "image_idea"),
                "channels": [c for c in (p.get("channels") or ["x"])
                             if c in _CHANNELS] or ["x"],
            }
            for k in BRIEF_FIELDS:
                out[k] = _s(p, k)
            # Caption prête à publier : hashtags en fin si le LLM a oublié.
            tags = out["hashtags"].strip()
            if tags and tags not in out["caption"]:
                out["caption"] = (out["caption"].rstrip() + "\n\n" + tags
                                  )[:_CAPS["caption"]]
            clean.append(out)
        except (TypeError, ValueError):
            continue
    return clean or None
