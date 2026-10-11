# Modèle de démonstration de l'Établi (t180) sur le backend de PREUVE : un petit phare en OBJ (socle carré, tour
# octogonale effilée, balcon en surplomb, toit en pointe), écrit ici, importé par /api/assets/3d/importer. Gratuit,
# aucune clé. Jamais le 8765. Rend l'identifiant du job créé.
import json
import math
import sys
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE

V, F = [], []


def anneau(r, z, n=8, rot=0.0):
    i0 = len(V)
    for k in range(n):
        a = rot + 2 * math.pi * k / n
        V.append((r * math.cos(a), r * math.sin(a), z))
    return i0


def tronc(r0, z0, r1, z1, n=8, fond=False, haut=True):
    a, b = anneau(r0, z0, n), anneau(r1, z1, n)
    for k in range(n):
        k2 = (k + 1) % n
        F.append((a + k, a + k2, b + k2, b + k))          # flanc, normale vers l'extérieur
    if fond:
        F.append(tuple(a + k for k in reversed(range(n))))
    if haut:
        F.append(tuple(b + k for k in range(n)))


def pointe(r, z0, z1, n=8):
    a = anneau(r, z0, n)
    V.append((0, 0, z1)); s = len(V) - 1
    for k in range(n):
        F.append((a + k, a + (k + 1) % n, s))
    F.append(tuple(a + k for k in reversed(range(n))))


tronc(30, 0, 30, 8, n=4, fond=True)                          # socle carré (4 côtés)
tronc(14, 8, 9, 60, fond=True)                               # tour effilée
tronc(15, 60, 15, 64, fond=True)                             # balcon : déborde de la tour (surplomb)
tronc(8, 64, 8, 72, fond=True)                               # lanterne
pointe(10, 72, 82)                                           # toit

obj = "# phare de démonstration (guide v3, t180)\n" + "".join(f"v {x:.4f} {z:.4f} {-y:.4f}\n" for x, y, z in V) \
      + "".join("f " + " ".join(str(i + 1) for i in f) + "\n" for f in F)
b = uuid.uuid4().hex
corps = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"phare-demo.obj\"\r\n"
         f"Content-Type: text/plain\r\n\r\n").encode() + obj.encode() + f"\r\n--{b}--\r\n".encode()
req = urllib.request.Request(BASE + "/api/assets/3d/importer", data=corps, method="POST",
                             headers={"Content-Type": f"multipart/form-data; boundary={b}"})
with urllib.request.urlopen(req, timeout=120) as r:
    j = json.loads(r.read())
print("job :", j.get("job"), "·", j.get("triangles"), "triangles")
