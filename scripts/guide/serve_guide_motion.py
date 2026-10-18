# Backend de PREUVE du guide pour « Animer avec l'IA » (t237) : code de ce dépôt, python embarqué, dossier de données
# jetable, port 8811 (jamais le 8765), AUCUNE dépense :
#   - faux Ollama sur 127.0.0.1:8812 : gpt-oss (réflexion low / medium / high, défaut medium) et llama3 (sans) ; il
#     rend une chorégraphie lisible (une ligne du script par élément, entrées échelonnées) ;
#   - faux miroir GitHub sur 127.0.0.1:8813 (DZ_MOTION_MIROIR_GITHUB) : deux dépôts de DÉMONSTRATION écrits par nous,
#     `deepotus-demo/rebond-mit` (SKILL.md + LICENSE MIT) et `deepotus-demo/sans-licence` (SKILL.md seul).
# Garde G3 (spec Studio Animation § B3) : aucun texte, titre, pseudo ni capture d'un catalogue tiers. Les prompts et le
# skill semés ci-dessous sont ÉCRITS PAR DEEPOTUS pour la démonstration.
# Au démarrage : un graphe « Démo motion » (Texte → Animation ← Direction motion → Rendu), un prompt importé et le skill
# de démonstration installé (via les vraies routes), pour que les scènes de la Bibliothèque aient une liste à filtrer.
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, OLLAMA, MIROIR = 8811, 8812, 8813
WT = pathlib.Path(__file__).resolve().parents[2] / "backend"
d = pathlib.Path(tempfile.mkdtemp(prefix="dzguide_motion_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(d)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(d / 't.db').as_posix()}"
os.environ["DZ_MOTION_MIROIR_GITHUB"] = f"http://127.0.0.1:{MIROIR}"
for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "OPENAI_API_KEY", "GEMINI_API_KEY", "OLLAMA_MODEL", "FAL_KEY",
          "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER"):
    os.environ.pop(k, None)
(d / ".env").write_text("# guide t237\n", encoding="utf-8")
sys.path.insert(0, str(WT))
os.chdir(WT)
print("donnees de preuve :", d, flush=True)

MIT = """MIT License

Copyright (c) 2026 Deepotus (démonstration du guide)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY.
"""
SKILL = """---
name: rebond-demo
description: Skill de démonstration du guide Deepotus — chaque mot tombe et rebondit.
---

# Rebond démo

Fais tomber chaque mot du haut de l'écran et laisse-le rebondir deux fois avant de se poser.
"""
FICHIERS = {
    "/raw.githubusercontent.com/deepotus-demo/rebond-mit/HEAD/SKILL.md": SKILL,
    "/raw.githubusercontent.com/deepotus-demo/rebond-mit/HEAD/LICENSE": MIT,
    "/raw.githubusercontent.com/deepotus-demo/sans-licence/HEAD/SKILL.md": SKILL.replace("rebond-demo", "sans-licence-demo"),
    # lu par « Lire la licence » dans la scène du guide, jamais installé (la scène s'arrête avant le clic)
    "/raw.githubusercontent.com/deepotus-demo/vague-mit/HEAD/SKILL.md": SKILL.replace("rebond-demo", "vague-demo").replace(
        "chaque mot tombe et rebondit", "les mots ondulent comme une vague"),
    "/raw.githubusercontent.com/deepotus-demo/vague-mit/HEAD/LICENSE": MIT,
}
SHOW = {"gpt-oss": {"capabilities": ["completion", "thinking"], "thinking": {"values": ["low", "medium", "high"], "default": "medium"}},
        "llama3": {"capabilities": ["completion"]}}


class Miroir(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        c = FICHIERS.get(self.path)
        b = (c if c is not None else "Not Found").encode("utf-8")
        self.send_response(200 if c is not None else 404)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


class FauxOllama(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _r(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._r({"models": [{"name": "gpt-oss"}, {"name": "llama3"}]})

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show":
            return self._r(SHOW.get(corps.get("model") or corps.get("name"), {"capabilities": ["completion"]}))
        script = corps.get("prompt", "").split("SCRIPT :\n", 1)[-1].split("\n\n")[0]
        lignes = [l for l in script.splitlines() if l.strip()][:4]
        n = max(1, len(lignes))
        els = [{"type": "text", "text": l, "start": round(0.3 + 1.0 * i, 2), "dur": 0.5, "hold": round(7.2 - 1.0 * i, 2),
                "easing": "easeOutBack", "style": {"size": 120},
                "keyframes": [{"t": 0, "x": 50, "y": 50 - 9 * (n - 1) + 18 * i + 12, "scale": 0.4, "opacity": 0},
                              {"t": 1, "x": 50, "y": 50 - 9 * (n - 1) + 18 * i, "scale": 1, "opacity": 1}]}
               for i, l in enumerate(lignes)]
        self._r({"response": json.dumps({"elements": els}), "done": True})


for port, cls in ((MIROIR, Miroir), (OLLAMA, FauxOllama)):
    s = ThreadingHTTPServer(("127.0.0.1", port), cls)
    threading.Thread(target=s.serve_forever, daemon=True).start()

from app.main import app  # noqa: E402
from app.config import settings  # noqa: E402
from app.services import cles_a_chaud as CAC  # noqa: E402

settings.OLLAMA_URL = f"http://127.0.0.1:{OLLAMA}"
CAC.appliquer({"OLLAMA_MODEL": "gpt-oss"})

GRAPHES = settings.outputs_path.parent / "studio_graphs"
GRAPHES.mkdir(parents=True, exist_ok=True)
GRAPHE = {"name": "Démo motion", "id": "g_demo_motion",
          "nodes": [{"id": "tx", "type": "Text", "x": 40, "y": 60, "props": {"value": "DEEPOTUS\nDEEP DIVE\n100 % LOCAL"}},
                    {"id": "md", "type": "MotionDirection", "x": 40, "y": 320,
                     "props": {"style": "style-kinetic-type", "source": "", "consigne": "", "moteur": "ollama", "modele": "gpt-oss"}},
                    {"id": "an", "type": "Animation", "x": 330, "y": 170,
                     "props": {"durationS": 8, "fps": 30, "elements": [], "selected": 0, "script": ""}},
                    {"id": "rn", "type": "Render", "x": 620, "y": 170, "props": {}}],
          "edges": [{"id": "e1", "from": "tx", "fromPort": "out", "to": "an", "toPort": "script"},
                    {"id": "e2", "from": "md", "fromPort": "direction", "to": "an", "toPort": "direction"},
                    {"id": "e3", "from": "an", "fromPort": "out", "to": "rn", "toPort": "in"}]}
(GRAPHES / "g_demo_motion.json").write_text(json.dumps(
    {"id": "g_demo_motion", "name": "Démo motion", "graph": GRAPHE, "updated_at": "2026-10-18T10:00:00"},
    ensure_ascii=False), encoding="utf-8")


def semer():
    import httpx
    b = f"http://127.0.0.1:{PORT}/api"
    for _ in range(120):
        try:
            if httpx.get(f"{b}/motion/biblio", timeout=5).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    r1 = httpx.post(f"{b}/motion/biblio", timeout=30, json={
        "titre": "Des barres qui dansent", "auteur": "Equipe Deepotus", "themes": ["charts"],
        "url": "https://deepotus.xyz/demo/barres-qui-dansent",
        "texte": "Fais monter chaque barre du graphique l'une après l'autre, avec un léger rebond, puis affiche le chiffre au-dessus."})
    r2 = httpx.post(f"{b}/motion/skills/installer", timeout=30,
                    json={"source": "deepotus-demo/rebond-mit", "licence": "MIT"})
    print("semis :", r1.status_code, r2.status_code, flush=True)


threading.Thread(target=semer, daemon=True).start()
import uvicorn  # noqa: E402

uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
