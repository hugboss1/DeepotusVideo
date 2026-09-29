"""Guide par fournisseur (plan Settings T8 — tâche #17 du suivi, 29/09/2026).

Une entrée par clé testable (`diagnostic.TESTABLES`) : où la créer, comment on est facturé, à quoi elle sert DANS
CETTE APPLI, en français et en anglais. `verifie_le` est la date à laquelle le lien a été OUVERT dans un navigateur,
pas celle où il a été écrit : un guide qui envoie sur un 404 est pire que pas de guide.

Relevé du 29/09/2026 (navigateur) : les liens du plan du 03/09 avaient bougé pour quatre fournisseurs —
console.anthropic.com → platform.claude.com, elevenlabs.io/app/settings/api-keys → /app/developers/api-keys,
figma.com/developers/api → developers.figma.com/docs/rest-api, ai.google.dev/pricing → /gemini-api/docs/pricing.
Une page de connexion qui renvoie ensuite vers la bonne page compte comme vérifiée (fal, OpenAI, Google, ElevenLabs,
HeyGen, X).
"""

_VU = "2026-09-29"

GUIDES = {
    "FAL_KEY": {
        "nom": "fal.ai",
        "console": "https://fal.ai/dashboard/keys",
        "tarifs": "https://fal.ai/pricing",
        "verifie_le": _VU,
        "fr": "Crée un compte sur fal.ai, ouvre Dashboard → Keys, « Add key », et copie la valeur tout de suite (elle "
              "ne se réaffiche jamais). Facturation à l'usage, sans abonnement : tu paies l'image ou la seconde de "
              "vidéo. C'est la clé indispensable — sans elle, ni image, ni clip, ni musique, ni retrait de fond.",
        "en": "Create a fal.ai account, open Dashboard → Keys, click « Add key » and copy the value right away (it is "
              "never shown again). Pay-as-you-go, no subscription: you pay per image or per second of video. This is "
              "the one required key — without it there are no images, no clips, no music and no background removal.",
    },
    "HEYGEN_API_KEY": {
        "nom": "HeyGen",
        "console": "https://app.heygen.com/settings?nav=API",
        "tarifs": "https://www.heygen.com/pricing",
        "verifie_le": _VU,
        "fr": "Compte HeyGen, Settings → API, « Create token ». Facturé sur le solde du compte (crédits ou dollars "
              "selon l'offre) : le Diagnostic l'affiche. Sert aux avatars parlants (Quick, Studio, Composition) et "
              "aux avatars photo.",
        "en": "HeyGen account, Settings → API, « Create token ». Billed against the account balance (credits or "
              "dollars depending on the plan): Diagnostic shows it. Powers the talking avatars (Quick, Studio, "
              "Composition) and photo avatars.",
    },
    "ELEVENLABS_API_KEY": {
        "nom": "ElevenLabs",
        "console": "https://elevenlabs.io/app/developers/api-keys",
        "tarifs": "https://elevenlabs.io/pricing",
        "verifie_le": _VU,
        "fr": "Compte ElevenLabs, Developers → API Keys. Facturation en CARACTÈRES d'un quota mensuel : le Diagnostic "
              "affiche le restant. Sert à la voix off, aux bruitages et à la transcription des sous-titres. Le "
              "serveur local Voicebox fait la voix gratuitement quand il tourne — la clé reste optionnelle.",
        "en": "ElevenLabs account, Developers → API Keys. Billed in CHARACTERS from a monthly quota: Diagnostic shows "
              "what is left. Powers voiceover, sound effects and subtitle transcription. The local Voicebox server "
              "does voices for free when it runs — this key stays optional.",
    },
    "MESHY_API_KEY": {
        "nom": "Meshy",
        "console": "https://www.meshy.ai/api",
        "tarifs": "https://www.meshy.ai/pricing",
        "verifie_le": _VU,
        "fr": "Compte Meshy avec un plan API, page API. Facturation en CRÉDITS, et Meshy dit exactement combien chaque "
              "tâche a consommé : c'est le moteur dont la colonne « réel » des plafonds est exacte. Sert au "
              "texturage 3D et au 3D Studio. MESHY_MOCK=1 fait tourner toute la chaîne sans clé ni crédit.",
        "en": "Meshy account with an API plan, API page. Billed in CREDITS, and Meshy reports exactly what each task "
              "consumed: its « actual » spend column is exact. Powers 3D texturing and 3D Studio. MESHY_MOCK=1 runs "
              "the whole chain with no key and no credits.",
    },
    "ANTHROPIC_API_KEY": {
        "nom": "Anthropic",
        "console": "https://platform.claude.com/settings/keys",
        "tarifs": "https://claude.com/pricing",
        "verifie_le": _VU,
        "fr": "Console Claude (platform.claude.com), Settings → API keys. Facturation aux jetons (entrée/sortie). "
              "Sert aux résumés News, au planificateur marketing, aux scripts et aux contrôles vision. Le modèle se "
              "règle juste en dessous (ANTHROPIC_MODEL).",
        "en": "Claude console (platform.claude.com), Settings → API keys. Billed per token (input/output). Powers "
              "News summaries, the marketing planner, scripts and vision checks. The model is set just below "
              "(ANTHROPIC_MODEL).",
    },
    "OPENAI_API_KEY": {
        "nom": "OpenAI",
        "console": "https://platform.openai.com/api-keys",
        "tarifs": "https://openai.com/api/pricing/",
        "verifie_le": _VU,
        "fr": "Plateforme OpenAI, API keys. Facturation aux jetons pour le texte, à l'image pour GPT Image. "
              "Alternative à Anthropic pour les résumés et les plans ; sert aussi à la transcription (Whisper) des "
              "sous-titres et aux images GPT.",
        "en": "OpenAI platform, API keys. Billed per token for text and per image for GPT Image. An alternative to "
              "Anthropic for summaries and plans; also powers subtitle transcription (Whisper) and GPT images.",
    },
    "GEMINI_API_KEY": {
        "nom": "Google Gemini",
        "console": "https://aistudio.google.com/apikey",
        "tarifs": "https://ai.google.dev/gemini-api/docs/pricing",
        "verifie_le": _VU,
        "fr": "Google AI Studio, « Get API key ». Facturation aux jetons ; un palier gratuit existe. Sert aux résumés, "
              "aux plans, et aux modèles vidéo Veo servis en direct par Google (les mêmes modèles passés par fal "
              "utilisent FAL_KEY, pas celle-ci).",
        "en": "Google AI Studio, « Get API key ». Billed per token; a free tier exists. Powers summaries, plans, and "
              "the Veo video models served directly by Google (the same models served through fal use FAL_KEY, not "
              "this one).",
    },
    "FIGMA_TOKEN": {
        "nom": "Figma",
        "console": "https://developers.figma.com/docs/rest-api/#access-tokens",
        "tarifs": "",
        "verifie_le": _VU,
        "fr": "figma.com → ton avatar → Settings → Security → Personal access tokens. Gratuit. Sert à importer un "
              "cadre Figma dans la Bibliothèque et dans Card Forge. Sans ce jeton, l'import répond 503 en le disant.",
        "en": "figma.com → your avatar → Settings → Security → Personal access tokens. Free. Used to import a Figma "
              "frame into the Library and into Card Forge. Without it the import answers 503 and says so.",
    },
    "TELEGRAM_BOT_TOKEN": {
        "nom": "Telegram",
        "console": "https://t.me/BotFather",
        "tarifs": "",
        "verifie_le": _VU,
        "fr": "Écris à @BotFather sur Telegram, /newbot : il rend un jeton « 12345:AA… ». Gratuit, sans validation. "
              "C'est le canal de publication de référence du Scheduler. Remplis aussi TELEGRAM_CHAT_ID (l'id du "
              "salon où publier).",
        "en": "Message @BotFather on Telegram, /newbot: it returns a token « 12345:AA… ». Free, no review process. "
              "This is the Scheduler's reference publishing channel. Fill TELEGRAM_CHAT_ID too (the id of the chat "
              "to post into).",
    },
    "X_API_KEY": {
        "nom": "X (Twitter)",
        "console": "https://developer.x.com/en/portal/dashboard",
        "tarifs": "https://developer.x.com/en/portal/products",
        "verifie_le": _VU,
        "fr": "Portail développeur X : crée une App, active « Read and write », puis relève les QUATRE valeurs — API "
              "key, API secret, Access token, Access token secret. Le palier gratuit autorise les publications avec "
              "un quota mensuel. Les quatre se testent ensemble, jamais une par une.",
        "en": "X developer portal: create an App, enable « Read and write », then collect ALL FOUR values — API key, "
              "API secret, Access token, Access token secret. The free tier allows posting within a monthly quota. "
              "All four are tested together, never one by one.",
    },
    "OLLAMA_URL": {
        "nom": "Ollama (local)",
        "console": "https://ollama.com/download",
        "tarifs": "",
        "verifie_le": _VU,
        "fr": "Pas une clé : l'adresse d'un serveur Ollama qui tourne sur ta machine (par défaut "
              "http://127.0.0.1:11434). Gratuit, et rien ne sort du PC. Renseigne aussi OLLAMA_MODEL "
              "(qwen2.5:14b-instruct ou mieux ; 8B est le plancher).",
        "en": "Not a key: the address of an Ollama server running on your machine (http://127.0.0.1:11434 by "
              "default). Free, and nothing leaves the PC. Set OLLAMA_MODEL too (qwen2.5:14b-instruct or better; "
              "8B is the floor).",
    },
}
# Les quatre clés X partagent le guide de X_API_KEY.
for _k in ("X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
    GUIDES[_k] = GUIDES["X_API_KEY"]


def guide(nom: str) -> dict | None:
    return GUIDES.get(nom)


def tous() -> dict:
    return {k: dict(v) for k, v in GUIDES.items()}
