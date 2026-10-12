# Données de démonstration des calques IA (t193, G11) sur le backend de PREUVE du guide (serve_guide_ia.py) :
#   - Vectorlab : « Affiche à calques », trois calques (Fond dessiné, Image vide, Texte avec le titre) — le calque
#     Image reçoit l'image IA pendant la capture ;
#   - Bibliothèque : « paysage-demo.png », une photo dessinée ici, que le Photolab ouvre.
# Dessiné ici, gratuit, aucune clé. Jamais le 8765.
import io
import json
import sys
import urllib.request
import uuid

from PIL import Image, ImageDraw

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE


def poster_json(chemin, corps):
    req = urllib.request.Request(BASE + chemin, method="POST", data=json.dumps(corps).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def deposer(nom, im):
    b = io.BytesIO()
    im.save(b, "PNG")
    lim = "----dz" + uuid.uuid4().hex
    corps = (f"--{lim}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nom}\"\r\n"
             f"Content-Type: image/png\r\n\r\n").encode() + b.getvalue() + f"\r\n--{lim}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/images/upload", method="POST", data=corps,
                                 headers={"Content-Type": f"multipart/form-data; boundary={lim}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("filename")


affiche = {
    "v": 1, "nom": "Affiche à calques", "taille": {"w": 1080, "h": 1350},
    "calques": [
        {"id": "c1", "nom": "Fond", "visible": True, "verrou": False, "objets": [
            {"id": "ciel", "type": "rect", "x": 0, "y": 0, "w": 1080, "h": 1350, "style": {"fond": "#1F2A52"}},
            {"id": "lune", "type": "ellipse", "cx": 820, "cy": 260, "rx": 110, "ry": 110, "style": {"fond": "#F5C451"}},
            {"id": "sol", "type": "rect", "x": 0, "y": 1080, "w": 1080, "h": 270, "style": {"fond": "#12405E"}},
        ]},
        {"id": "c2", "nom": "Image", "visible": True, "verrou": False, "objets": []},
        {"id": "c3", "nom": "Texte", "visible": True, "verrou": False, "objets": [
            {"id": "titre", "type": "texte", "x": 540, "y": 1230, "contenu": "LA NUIT DES CHATS",
             "style": {"fond": "#F1EEE6", "police": "Segoe UI", "corps": 92, "graisse": "bold", "ancre": "middle"}},
        ]},
    ],
}
print("vectorlab :", poster_json("/api/vector/docs", {"name": "Affiche à calques", "role": "libre", "doc": affiche})["id"])

p = Image.new("RGB", (1600, 1000), (120, 170, 210))
g = ImageDraw.Draw(p)
g.rectangle((0, 620, 1600, 1000), fill=(70, 120, 60))
g.polygon([(0, 640), (380, 330), (760, 640)], fill=(90, 100, 120))
g.polygon([(520, 650), (1000, 250), (1480, 650)], fill=(110, 115, 135))
g.polygon([(890, 330), (1000, 250), (1110, 330)], fill=(240, 240, 245))
g.ellipse((1260, 90, 1420, 250), fill=(250, 220, 120))
print("bibliotheque :", deposer("paysage-demo.png", p))
