# Backend de PREUVE du guide pour « Demander à Deepotus » (lot A7, 19/10/2026) : code de ce dépôt, python embarqué,
# dossier de données jetable, port 8815 (jamais le 8765), AUCUNE dépense :
#   - faux Ollama sur 127.0.0.1:8816 : `llava-demo` (capacités completion + vision). Sans image, il répond selon la
#     question (clé → Réglages › Clés d'API ; montage → l'écran Montage ; sinon [VOIR]) ; avec une image, il rend
#     [POINT:x,y:Rail] au milieu du rail de gauche ;
#   - faux Voicebox sur 127.0.0.1:8817 : GET /health seulement (le bouton « Lire » apparaît ; aucune voix n'est
#     produite : la lecture réelle échoue proprement, ce que les scènes ne montrent pas).
# Les réponses sont ÉCRITES PAR DEEPOTUS pour la démonstration et n'emploient que des ancres et chapitres réels.
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, OLLAMA, VOICEBOX = 8815, 8816, 8817
WT = pathlib.Path(__file__).resolve().parents[2] / "backend"
d = pathlib.Path(tempfile.mkdtemp(prefix="dzguide_agent_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(d)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(d / 't.db').as_posix()}"
os.environ["VOICEBOX_URL"] = f"http://127.0.0.1:{VOICEBOX}"
for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "OPENAI_API_KEY", "GEMINI_API_KEY", "OLLAMA_MODEL", "FAL_KEY",
          "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER"):
    os.environ.pop(k, None)
(d / ".env").write_text("# guide A7\n", encoding="utf-8")
sys.path.insert(0, str(WT))
os.chdir(WT)
print("donnees de preuve :", d, flush=True)

REPONSES = [
    (re.compile(r"cl[ée]|key", re.I),
     {"fr": "Ta clé se pose dans Réglages, section Clés d'API.\n1. Ouvre Réglages, puis Clés d'API.\n"
            "2. Colle la clé sur la ligne du fournisseur, puis Enregistrer.\n[POINT:reglages.cles]\n[GUIDE:cles]",
      "en": "Your key goes in Settings, API keys section.\n1. Open Settings, then API keys.\n"
            "2. Paste the key on the provider's line, then Save.\n[POINT:reglages.cles]\n[GUIDE:cles]"}),
    (re.compile(r"mont|edit", re.I),
     {"fr": "Le montage se fait dans l'écran Montage, dans la barre de gauche.\n[POINT:rail.montage]\n[GUIDE:montage]",
      "en": "Editing happens in the Edit screen, in the left bar.\n[POINT:rail.montage]\n[GUIDE:montage]"}),
]
VOIR = {"fr": "Je ne connais pas ce bouton par son nom : je peux regarder ton écran pour le trouver.\n[VOIR]\n[GUIDE:tour]",
        "en": "I don't know this button by name: I can look at your screen to find it.\n[VOIR]\n[GUIDE:tour]"}


class FauxOllama(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _r(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._r({"models": [{"name": "llava-demo"}]})

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show":
            return self._r({"capabilities": ["completion", "vision"]})
        prompt = corps.get("prompt", "")
        en = "langue : English" in corps.get("system", "")
        question = prompt.rsplit("Nouvelle question : ", 1)[-1].split("\n\n", 1)[0]
        if corps.get("images"):
            m = re.search(r"\((\d+)×(\d+) px\)", prompt)
            l, h = (int(m.group(1)), int(m.group(2))) if m else (1280, 800)
            texte = ("It's here, in the left bar." if en else "C'est ici, dans la barre de gauche.") \
                + f"\n[POINT:{max(1, l // 40)},{h // 3}:Rail]"
        else:
            texte = next((r["en" if en else "fr"] for motif, r in REPONSES if motif.search(question)),
                         VOIR["en" if en else "fr"])
        self._r({"response": texte, "done": True})


class FauxVoicebox(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        code = 200 if self.path == "/health" else 404
        self.send_response(code); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"{}")


for port, cls in ((OLLAMA, FauxOllama), (VOICEBOX, FauxVoicebox)):
    s = ThreadingHTTPServer(("127.0.0.1", port), cls)
    threading.Thread(target=s.serve_forever, daemon=True).start()

from app.main import app  # noqa: E402
from app.config import settings  # noqa: E402
from app.services import cles_a_chaud as CAC  # noqa: E402

settings.OLLAMA_URL = f"http://127.0.0.1:{OLLAMA}"
settings.VOICEBOX_URL = f"http://127.0.0.1:{VOICEBOX}"
CAC.appliquer({"OLLAMA_MODEL": "llava-demo"})
import uvicorn  # noqa: E402

uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
