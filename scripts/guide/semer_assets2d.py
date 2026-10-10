# Images de démonstration des labs 2D (t178) sur le backend de PREUVE : deux textures (herbe, sable) pour le Tile
# Lab et une planche de sprites (8 cases, fond transparent) pour l'onglet Feuille du Sprite Lab. Dessinées ici,
# gratuites, aucune clé. Jamais le 8765.
import io
import json
import math
import random
import sys
import urllib.request
import uuid

from PIL import Image, ImageDraw, ImageFilter

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE


def envoyer(nom, im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    b = uuid.uuid4().hex
    corps = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nom}\"\r\n"
             f"Content-Type: image/png\r\n\r\n").encode() + buf.getvalue() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/images/upload", data=corps, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["filename"]


def texture(base, ecart, graine, brins=None):
    rnd = random.Random(graine)
    im = Image.new("RGB", (512, 512), base)
    dr = ImageDraw.Draw(im)
    for _ in range(5000):
        x, y = rnd.randrange(512), rnd.randrange(512)
        d = rnd.randint(-ecart, ecart)
        c = tuple(max(0, min(255, v + d)) for v in base)
        if brins:
            dr.line([(x, y), (x + rnd.randint(-3, 3), y - rnd.randint(4, 10))], fill=c, width=2)
        else:
            dr.ellipse((x, y, x + 3, y + 3), fill=c)
    return im.filter(ImageFilter.GaussianBlur(0.6))


def planche():
    # 8 cases de 128 px : un petit personnage qui sautille (corps, tête, pieds), fond transparent
    im = Image.new("RGBA", (128 * 4, 128 * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for k in range(8):
        cx, cy = (k % 4) * 128 + 64, (k // 4) * 128 + 64
        h = int(14 * abs(math.sin(k * math.pi / 4)))
        dr.ellipse((cx - 26, cy - 10 - h, cx + 26, cy + 34 - h), fill=(240, 180, 41, 255), outline=(40, 30, 20, 255), width=3)
        dr.ellipse((cx - 20, cy - 46 - h, cx + 20, cy - 6 - h), fill=(250, 220, 190, 255), outline=(40, 30, 20, 255), width=3)
        dr.ellipse((cx - 9, cy - 32 - h, cx - 3, cy - 26 - h), fill=(30, 30, 30, 255))
        dr.ellipse((cx + 3, cy - 32 - h, cx + 9, cy - 26 - h), fill=(30, 30, 30, 255))
        pas = 8 if k % 2 else -8
        dr.rectangle((cx - 18 + pas, cy + 32 - h, cx - 6 + pas, cy + 44 - h), fill=(70, 70, 90, 255))
        dr.rectangle((cx + 6 - pas, cy + 32 - h, cx + 18 - pas, cy + 44 - h), fill=(70, 70, 90, 255))
    return im


print("herbe :", envoyer("texture-herbe.png", texture((86, 150, 70), 40, 1, brins=True)))
print("sable :", envoyer("texture-sable.png", texture((214, 186, 128), 30, 2)))
print("planche :", envoyer("planche-heros.png", planche()))
