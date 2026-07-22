"""v1.27.1 — import de documents structurés (non-régression du bug
2026-07-15 : le docx Sol de 13 posts retombait sur 1 post « built-in »).
Recette : (1) les blocs KEY: value se parsent fidèlement SANS LLM (dates,
canaux, formats, champs étendus) ; (2) une sortie LLM TRONQUÉE par
max_tokens est récupérée post par post ; (3) l'extraction .docx préserve
les sauts de ligne intra-paragraphe ; (4) plan_from_document renvoie
engine='document' sans aucune clé LLM. Aucun réseau.
Run: <embedded python -X utf8> backend/tests/test_plan_doc_import.py"""
import asyncio
import io
import json
import os
import pathlib
import sys
import tempfile
import zipfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
# aucun moteur LLM disponible : l'import doit réussir quand même
settings.ANTHROPIC_API_KEY = ""
settings.OPENAI_API_KEY = ""
settings.GEMINI_API_KEY = ""
settings.OLLAMA_MODEL = ""

from app.services import marketing, plan_schema       # noqa: E402

DOC = """DEEPOTUS — Structured Posting Blocks
Global links: Website: https://www.deepotus.xyz
Recommended Fixed Schema
POST_ID
DATE_TIME
Structured Post Blocks
P1
POST_ID: P1
DATE_TIME: Wed 15 Jul 2026 — 19:30 CEST
PLATFORM: X + Telegram
PRIORITY: High
LIVE_PHASE: Pre-live
FORMAT: Static poster
ASPECT_RATIO: 1:1 square
FILE_NAME_SUGGESTION: P1.png
OBJECTIVE: Kickoff announcement
VISUAL_PROMPT: Dark red-and-black poster. Central emblem glowing.
Large title TWO NIGHTS.
ON_IMAGE_TEXT: TWO NIGHTS. ONE PROPHECY.
X_CAPTION: TWO NIGHTS. ONE PROPHECY.
Register. Watch. Decode.
https://www.deepotus.xyz
TG_CAPTION: DEEPOTUS TRANSMISSION // TWO NIGHTS.
Enter: https://www.deepotus.xyz
CTA: Set a reminder.
HASHTAGS: #DEEPOTUS #DEEP
LINKS: https://www.deepotus.xyz
AVATAR_SCRIPT_SHORT: Citizens of the surface. Two movements.
AVATAR_SCRIPT_LONG: Citizens of the surface. For too long, symbols.
SCHEDULING_NOTES: Pin on X for 12 hours.
P2
POST_ID: P2
DATE_TIME: Thu 16 Jul 2026 — 60 min before live
PLATFORM: Telegram first, then X
PRIORITY: Critical
FORMAT: Avatar video
OBJECTIVE: Final push
X_CAPTION: LIVE IN 60 MINUTES.
HASHTAGS: #DEEPOTUS
P3
POST_ID: P3
DATE_TIME: Fri 17 Jul 2026 — 10:30 CEST
PLATFORM: X
FORMAT: Animated countdown poster
OBJECTIVE: Morning reset
X_CAPTION: A chart without a world is noise.
"""


def test_structured_parse():
    posts = marketing.parse_structured_blocks(DOC)
    assert len(posts) == 3, posts
    p1, p2, p3 = posts
    assert p1["day_offset"] == 0 and p1["time"] == "19:30"
    assert p2["day_offset"] == 1 and p2["time"] == "12:00"  # créneau relatif
    assert p3["day_offset"] == 2 and p3["time"] == "10:30"
    assert p1["channels"] == ["x", "telegram"]
    assert p2["channels"] == ["x", "telegram"]  # "Telegram first, then X"
    assert p3["channels"] == ["x"]
    assert p1["format"] == "image" and p2["format"] == "heygen" \
        and p3["format"] == "seedance"
    # valeurs multi-lignes intactes
    assert "Large title TWO NIGHTS." in p1["image_idea"]
    assert "Register. Watch. Decode." in p1["caption"]
    # champs étendus + caption terminée par les hashtags
    assert p1["tg_caption"].startswith("DEEPOTUS TRANSMISSION")
    assert p1["caption"].rstrip().endswith("#DEEPOTUS #DEEP")
    assert p1["priority"] == "High" and p2["priority"] == "Critical"
    assert p1["avatar_script_long"].startswith("Citizens")
    assert "Pin on X" in p1["scheduling_notes"]
    assert "Créneau:" in p2["scheduling_notes"]  # heure relative conservée
    # un texte libre sans blocs -> None (le LLM prend le relais)
    assert marketing.parse_structured_blocks("Semaine 1: teaser.\n"
                                             "Semaine 2: lancement.") is None
    print("parse blocs structurés: PASS")


def test_truncated_json_salvage():
    full = {"posts": [
        {"day_offset": i, "time": "09:00", "title": f"P{i}",
         "format": "image", "hook": "h", "caption": f"cap {i}",
         "hashtags": "#DEEP", "channels": ["x"]} for i in range(5)]}
    text = json.dumps(full)
    cut = text[:text.rfind('"caption": "cap 4"')]  # tronqué en plein post 5
    posts = plan_schema.parse_llm_posts("bla\n" + cut, 7)
    assert posts and len(posts) == 4, posts and len(posts)
    assert posts[0]["caption"].endswith("#DEEP")
    # JSON complet : comportement inchangé
    assert len(plan_schema.parse_llm_posts(text, 7)) == 5
    # accolades dans les chaînes : pas de faux découpage
    tricky = ('{"posts":[{"day_offset":0,"time":"09:00","title":"T",'
              '"format":"image","hook":"h","caption":"brace } inside",'
              '"channels":["x"]},{"day_offset":1,"tronq')
    got = plan_schema.parse_llm_posts(tricky, 7)
    assert len(got) == 1 and got[0]["caption"] == "brace } inside"
    print("récupération JSON tronqué: PASS")


def test_docx_linebreaks():
    xml = ('<?xml version="1.0"?><w:document '
           'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
           '2006/main"><w:body>'
           '<w:p><w:r><w:t>POST_ID: T1</w:t></w:r></w:p>'
           '<w:p><w:r><w:t>X_CAPTION: ligne 1</w:t><w:br/>'
           '<w:t>ligne 2 &amp; fin</w:t></w:r></w:p>'
           '</w:body></w:document>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    txt = marketing.extract_document_text("plan.docx", buf.getvalue())
    assert txt.splitlines() == ["POST_ID: T1", "X_CAPTION: ligne 1",
                                "ligne 2 & fin"], txt
    print("extraction docx (sauts de ligne): PASS")


async def main():
    test_structured_parse()
    test_truncated_json_salvage()
    test_docx_linebreaks()
    # bout en bout : document structuré, ZÉRO clé LLM configurée
    plan = await marketing.plan_from_document(DOC, days=7, channels=["x"],
                                              language="EN")
    assert plan["engine"] == "document"
    assert len(plan["posts"]) == 3
    print("plan_from_document engine=document sans LLM: PASS")
    print("PLAN DOC IMPORT TEST: PASS")


asyncio.run(main())
