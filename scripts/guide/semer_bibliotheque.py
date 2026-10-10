# Bibliothèque de démonstration (t176) sur le backend de PREUVE : huit images dessinées ici (Pillow, aucun
# fournisseur), tags, notes, favoris, licences, une lignée mère → fille, un doublon exact, un projet, des
# commentaires et un élément à la corbeille. Gratuit, aucune clé. Jamais le 8765.
import io
import json
import math
import sys
import urllib.parse
import urllib.request
import uuid

from PIL import Image, ImageDraw, ImageFilter

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE


def appel(methode, chemin, corps=None):
    data = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(BASE + chemin, data=data, method=methode,
                                 headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"null")


def envoyer(nom, octets):
    b = uuid.uuid4().hex
    corps = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nom}\"\r\n"
             f"Content-Type: image/png\r\n\r\n").encode() + octets + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/images/upload", data=corps, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["filename"]


def png(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def ciel(w, h, haut, bas):
    im = Image.new("RGB", (w, h))
    dr = ImageDraw.Draw(im)
    for y in range(h):
        t = y / (h - 1)
        dr.line([(0, y), (w, y)], fill=tuple(int(haut[i] + (bas[i] - haut[i]) * t) for i in range(3)))
    return im, dr


def phare():
    im, dr = ciel(1280, 800, (22, 30, 64), (236, 132, 74))
    dr.ellipse((860, 380, 1040, 560), fill=(255, 214, 120))
    dr.rectangle((0, 600, 1280, 800), fill=(18, 52, 78))
    dr.polygon([(300, 600), (360, 220), (420, 220), (480, 600)], fill=(236, 236, 228))
    for y in (300, 400, 500):
        dr.rectangle((330, y, 450, y + 30), fill=(196, 40, 48))
    dr.rectangle((345, 180, 435, 225), fill=(255, 230, 140))
    dr.polygon([(330, 180), (390, 130), (450, 180)], fill=(40, 40, 48))
    return im


def recif():
    im, dr = ciel(1280, 800, (8, 60, 92), (4, 22, 40))
    for i, c in enumerate([(255, 120, 90), (250, 190, 70), (230, 80, 140), (90, 210, 170)]):
        x = 180 + i * 260
        for k in range(7):
            a = -math.pi / 2 + (k - 3) * 0.32
            dr.line([(x, 760), (x + 220 * math.cos(a), 760 + 260 * math.sin(a))], fill=c, width=22)
    for k in range(40):
        dr.ellipse((60 + k * 31 % 1200, 80 + (k * 97) % 500, 72 + k * 31 % 1200, 92 + (k * 97) % 500),
                   outline=(180, 230, 255), width=2)
    return im


def foret():
    im, dr = ciel(1280, 800, (200, 226, 196), (60, 96, 70))
    for i in range(9):
        x = 60 + i * 140
        dr.polygon([(x, 720), (x + 70, 260 + (i % 3) * 60), (x + 140, 720)], fill=(30 + i * 6, 84 + i * 4, 52))
    dr.rectangle((0, 700, 1280, 800), fill=(70, 56, 40))
    return im


def portrait():
    im, dr = ciel(800, 1000, (40, 34, 60), (110, 70, 120))
    dr.ellipse((250, 220, 550, 560), fill=(230, 190, 160))
    dr.rectangle((200, 600, 600, 1000), fill=(60, 90, 160))
    dr.ellipse((320, 340, 360, 380), fill=(40, 30, 30))
    dr.ellipse((440, 340, 480, 380), fill=(40, 30, 30))
    dr.arc((340, 400, 460, 480), 20, 160, fill=(150, 60, 60), width=8)
    return im.filter(ImageFilter.GaussianBlur(1))


def desert():
    im, dr = ciel(1280, 800, (250, 222, 160), (236, 150, 70))
    dr.ellipse((540, 120, 740, 320), fill=(255, 246, 210))
    for i, c in enumerate([(214, 140, 70), (190, 110, 52), (160, 86, 40)]):
        y = 470 + i * 100
        dr.polygon([(0, 800), (0, y), (400, y - 80), (900, y + 30), (1280, y - 40), (1280, 800)], fill=c)
    return im


def neon():
    im = Image.new("RGB", (1080, 1080), (12, 10, 24))
    dr = ImageDraw.Draw(im)
    for r, c in ((420, (255, 40, 160)), (320, (60, 220, 255)), (220, (180, 90, 255))):
        dr.ellipse((540 - r, 540 - r, 540 + r, 540 + r), outline=c, width=14)
    return im.filter(ImageFilter.GaussianBlur(2))


IMAGES = [  # nom, dessin, tags, note, favori, licence
    ("phare-du-recif.png", phare, ["phare", "affiche", "épisode-1"], 5, True, "Créée dans Deepotus"),
    ("recif-corail.png", recif, ["récif", "épisode-1"], 4, True, "Créée dans Deepotus"),
    ("foret-brume.png", foret, ["forêt", "décor"], 3, False, "CC0"),
    ("portrait-capitaine.png", portrait, ["personnage", "épisode-1"], 4, False, "Créée dans Deepotus"),
    ("dunes-midi.png", desert, ["décor", "désert"], 2, False, ""),
    ("anneaux-neon.png", neon, ["miniature", "néon"], 3, False, "Créée dans Deepotus"),
]

noms = {}
for nom, dessin, tags, note, fav, licence in IMAGES:
    octets = png(dessin())
    f = envoyer(nom, octets)
    noms[nom] = f
    champs = {"tags": tags, "note": note, "fav": fav}
    if licence:
        champs["licence"] = licence
    appel("PATCH", "/api/library/asset/" + urllib.parse.quote(f), champs)
    if nom == "foret-brume.png":                       # un doublon exact (le nettoyage le trouve)
        envoyer("foret-brume-copie.png", octets)

# lignée : un recadrage du phare, fille de l'affiche
fille = envoyer("phare-recadre.png", png(phare().crop((200, 100, 700, 700))))
appel("PATCH", "/api/library/asset/" + urllib.parse.quote(fille),
      {"parent_filename": noms["phare-du-recif.png"], "relation": "recadrage", "tags": ["phare", "miniature"],
       "note": 4})

# un projet qui range l'épisode
p = appel("POST", "/api/library/projets", {"nom": "Le phare du récif", "couleur": "#f0b429"})
pid = p.get("id") or p.get("pid")
appel("POST", f"/api/library/projets/{pid}/items",
      {"items": [{"ref": noms[n], "kind": "image"} for n in
                 ("phare-du-recif.png", "recif-corail.png", "portrait-capitaine.png")] +
               [{"ref": fille, "kind": "image"}]})
appel("POST", "/api/library/projets", {"nom": "Miniatures YouTube", "couleur": "#7c5cff"})

# commentaires de revue
ref = noms["phare-du-recif.png"]
appel("POST", "/api/library/commentaires/" + urllib.parse.quote(ref),
      {"texte": "Ciel un peu plus chaud pour la miniature ?", "statut": "a_revoir"})
appel("POST", "/api/library/commentaires/" + urllib.parse.quote(ref),
      {"texte": "Validé pour l'épisode 1.", "statut": "valide"})

# un élément à la corbeille
jet = envoyer("essai-rate.png", png(Image.new("RGB", (640, 360), (90, 90, 90))))
appel("DELETE", "/api/images/" + urllib.parse.quote(jet))
print("bibliothèque semée :", len(noms) + 3, "images, projet", pid)
