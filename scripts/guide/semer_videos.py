# -*- coding: utf-8 -*-
"""Trois courtes vidéos de démonstration (fabriquées ici par ffmpeg, aucun fournisseur) importées sur le backend de
PREUVE du guide, pour capturer le Montage sur une vraie timeline. Jamais le 8765.

    python scripts/guide/semer_videos.py [http://127.0.0.1:8809] [chemin de ffmpeg]
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE, "jamais le 8765 de l'utilisateur"
FF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.environ["LOCALAPPDATA"], "DeepotusVideoGen", "bin", "ffmpeg.exe")

PLANS = [  # (nom, couleur de fond, fréquence du son, durée)
    ("plan-01-aube.mp4", "0x1a2a4a", 330, 5),
    ("plan-02-phare.mp4", "0x3a2a14", 440, 4),
    ("plan-03-houle.mp4", "0x0f3a3a", 550, 6),
]
with tempfile.TemporaryDirectory() as d:
    for nom, fond, freq, duree in PLANS:
        f = pathlib.Path(d) / nom
        filtre = (f"color=c={fond}:s=1080x1920:d={duree}:r=30,"
                  f"drawbox=x='540+300*sin(t*1.3)-120':y='860+200*cos(t)':w=240:h=240:color=0xf0b429@0.9:t=fill")
        subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi", "-i", filtre,
                        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duree}",
                        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(f)], check=True)
        b = uuid.uuid4().hex
        corps = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nom}\"\r\n"
                 f"Content-Type: video/mp4\r\n\r\n").encode() + f.read_bytes() + f"\r\n--{b}--\r\n".encode()
        req = urllib.request.Request(BASE + "/api/videos/upload", data=corps, method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        print(nom, urllib.request.urlopen(req, timeout=120).status)
