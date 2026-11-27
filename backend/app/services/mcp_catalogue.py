# -*- coding: utf-8 -*-
"""Le CATALOGUE des serveurs MCP utiles à DeepotusVideo (Réglages › Serveur MCP, 22/11/2026).

Un serveur MCP se branche à CLAUDE CODE (ou à tout client MCP) : il donne à l'assistant de l'utilisateur la main sur
un logiciel voisin de l'app (Blender, ElevenLabs, Figma, Canva, Notion, GitHub…), à côté du serveur « deepotus » de
l'app. L'écran montre, pour chacun : à quoi il sert dans l'app, les écrans qu'il aide, la commande à copier, la
licence, et son ÉTAT local quand on peut le lire sans rien lancer :
  * « deepotus »  : le serveur de l'app (actif ou non, mcp_pont) ;
  * « blender »   : mcp-for-blender trouvé ou non (le pont « Scène Blender » de l'app s'en sert aussi) ;
  * les autres    : « branché » si son NOM figure dans la configuration de Claude Code de l'utilisateur
                    (~/.claude.json, mcpServers, au niveau utilisateur) — seuls les noms sont lus, jamais les
                    commandes, les URL ni les clés ; sinon « à brancher ».
Rien n'est installé, lancé ni écrit ici. Aucune clé n'apparaît dans une commande : une clé s'écrit à la place du
repère <VOTRE_CLE>, chez l'utilisateur.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

CATALOGUE: list[dict] = [
    {"id": "deepotus", "nom": "DeepotusVideo",
     "role": {"fr": "Le serveur de l'app : Claude Code lit la Bibliothèque, la bible et les plans des Chapitres, les "
                    "recettes et les pièces 3D, chiffre une génération et demande son lancement (vous cliquez).",
              "en": "The app's own server: Claude Code reads the Library, the Chapters bible and shots, recipes and "
                    "3D parts, quotes a generation and asks to launch it (you click)."},
     "ecrans": ["Chapitres", "Studio", "Quick", "Studio 3D", "Card Forge"], "type": "stdio", "licence": "—",
     "commande": None, "doc": ""},
    {"id": "blender", "nom": "Blender (mcp-for-blender)",
     "role": {"fr": "Pilote le Blender ouvert : scène, captures, assets Poly Haven / Sketchfab / Poly Pizza, scripts. "
                    "Le pont « Scène Blender » de l'app et l'animation faciale passent par lui.",
              "en": "Drives the open Blender: scene, captures, Poly Haven / Sketchfab / Poly Pizza assets, scripts. "
                    "The app's « Blender Scene » bridge and facial animation go through it."},
     "ecrans": ["Chapitres › Plateau 3D", "Studio 3D", "Studio virtuel", "Card Forge"], "type": "stdio",
     "licence": "MIT",
     "commande": "claude mcp add --scope user blender -e DISABLE_TELEMETRY=true -e BLENDER_MCP_SAFE_MODE=1 "
                 "-- uvx mcp-for-blender",
     "apres": {"fr": "Puis dans Blender : uvx mcp-for-blender install-addon, panneau N › MCP › Start MCP Server.",
               "en": "Then in Blender: uvx mcp-for-blender install-addon, N panel › MCP › Start MCP Server."},
     "doc": "https://github.com/ahujasid/blender-mcp"},
    {"id": "elevenlabs", "nom": "ElevenLabs",
     "role": {"fr": "Voix off, clonage, effets sonores et musique depuis Claude Code, avec votre compte ElevenLabs.",
              "en": "Voice-over, cloning, sound effects and music from Claude Code, with your ElevenLabs account."},
     "ecrans": ["Studio › Voix", "Son & VFX", "Quick"], "type": "stdio", "licence": "MIT",
     "commande": "claude mcp add --scope user elevenlabs -e ELEVENLABS_API_KEY=<VOTRE_CLE> -- uvx elevenlabs-mcp",
     "doc": "https://github.com/elevenlabs/elevenlabs-mcp"},
    {"id": "figma", "nom": "Figma",
     "role": {"fr": "Lit et écrit les maquettes Figma : gabarits de cartes, vignettes, charte d'un espace de marque.",
              "en": "Reads and writes Figma designs: card templates, thumbnails, a brand space's guidelines."},
     "ecrans": ["Card Forge", "Vectorlab", "Espaces de marque"], "type": "http", "licence": "—",
     "commande": "claude mcp add --scope user --transport http figma https://mcp.figma.com/mcp",
     "doc": "https://developers.figma.com/docs/figma-mcp-server/"},
    {"id": "canva", "nom": "Canva",
     "role": {"fr": "Crée et décline des visuels Canva (formats sociaux, couvertures) depuis les textes de l'app.",
              "en": "Creates and resizes Canva designs (social formats, covers) from the app's texts."},
     "ecrans": ["Campagnes", "Quick", "Studio"], "type": "http", "licence": "—",
     "commande": "claude mcp add --scope user --transport http canva https://mcp.canva.com/mcp",
     "doc": ""},
    {"id": "notion", "nom": "Notion",
     "role": {"fr": "Scénarios, bibles et plannings rangés dans Notion : les lire pour l'Atelier Chapitre, y écrire "
                    "les comptes rendus.",
              "en": "Scripts, bibles and schedules kept in Notion: read them for the Chapter workshop, write the "
                    "reports there."},
     "ecrans": ["Chapitres › Atelier", "Planificateur"], "type": "http", "licence": "—",
     "commande": "claude mcp add --scope user --transport http notion https://mcp.notion.com/mcp",
     "doc": "https://developers.notion.com/docs/mcp"},
    {"id": "github", "nom": "GitHub",
     "role": {"fr": "Suivre les dépôts des outils 3D libres (gltfpack, AutoRemesher, xatlas…), ouvrir un ticket.",
              "en": "Follow the open-source 3D tools' repositories (gltfpack, AutoRemesher, xatlas…), file an issue."},
     "ecrans": ["Réglages › Moteurs et logiciels 3D"], "type": "http", "licence": "MIT",
     "commande": "claude mcp add --scope user --transport http github https://api.githubcopilot.com/mcp/",
     "doc": "https://github.com/github/github-mcp-server"},
]


def _branches_claude() -> set[str]:
    """Les NOMS des serveurs déjà branchés à Claude Code, au niveau utilisateur (lecture seule, noms seulement)."""
    f = Path.home() / ".claude.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    m = d.get("mcpServers") if isinstance(d, dict) else None
    return {str(k) for k in m} if isinstance(m, dict) else set()


def liste(langue: str = "fr") -> dict:
    from app.services import blender_mcp as BM
    from app.services import mcp_pont as P
    lg = langue if langue in ("fr", "en") else "fr"
    branches = _branches_claude()
    out = []
    for e in CATALOGUE:
        x = {k: e[k] for k in ("id", "nom", "ecrans", "type", "licence", "doc")}
        x["role"] = e["role"][lg]
        x["apres"] = e["apres"][lg] if e.get("apres") else ""
        x["commande"] = e["commande"]
        x["branche"] = e["id"] in branches
        if e["id"] == "deepotus":
            x["commande"] = P.commande()["claude"]
            x["etat"] = "actif" if P.actif() else "inactif"
        elif e["id"] == "blender":
            x["etat"] = "trouve" if BM.etat_exe()["trouve"] else ("uvx" if shutil.which("uvx") else "absent")
        else:
            x["etat"] = "branche" if x["branche"] else "a_brancher"
        out.append(x)
    return {"serveurs": out, "uvx": bool(shutil.which("uvx")), "npx": bool(shutil.which("npx"))}
