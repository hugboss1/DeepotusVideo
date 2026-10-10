# Deux sons de démonstration (synthétisés ici, aucun fournisseur) importés sur le backend de PREUVE.
import io
import math
import struct
import sys
import urllib.request
import uuid
import wave

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE


def wav(freqs, secondes, nom):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        n = int(22050 * secondes)
        data = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * freqs[(i * len(freqs)) // n] * i / 22050)
                                              * min(1, i / 2000, (n - i) / 4000))) for i in range(n))
        w.writeframes(data)
    return nom, buf.getvalue()


for nom, octets in (wav([220, 277, 330, 440], 4.0, "nappe-phare.wav"), wav([880, 660], 1.2, "carillon.wav")):
    b = uuid.uuid4().hex
    corps = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nom}\"\r\n"
             f"Content-Type: audio/wav\r\n\r\n").encode() + octets + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/audio/upload", data=corps, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    print(nom, urllib.request.urlopen(req, timeout=60).status)
