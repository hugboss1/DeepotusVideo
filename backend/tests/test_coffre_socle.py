# -*- coding: utf-8 -*-
"""Socle du coffre (plan Settings T14 — tâche #20, 29/09/2026) : la primitive AES doit exister ICI.
Ce banc ne teste pas notre code : il teste la DÉPENDANCE (cryptography, ajoutée à requirements.txt) et DPAPI, et il le
dit franchement quand elles manquent. C'est le filet qui empêche le coffre d'être écrit au-dessus de rien.
Tant que le runtime INSTALLÉ n'a pas reçu la roue (déploiement), le lancer avec un runtime qui l'a.
Run : & $PY tests/test_coffre_socle.py   (depuis backend/)"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


try:
    import cryptography
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    presente = True
except ImportError as e:
    presente = False
    check("cryptography importable par CE python", False,
          f"{e} — pip install -r requirements.txt (la roue y est depuis la tâche #20)")

if presente:
    check("version >= 46", int(cryptography.__version__.split(".")[0]) >= 46, cryptography.__version__)
    k = AESGCM.generate_key(bit_length=256)
    check("clé de 256 bits", len(k) == 32)
    a = AESGCM(k); n = os.urandom(12)
    ct = a.encrypt(n, b"bonjour", b"entete")
    check("aller-retour AES-256-GCM", a.decrypt(n, ct, b"entete") == b"bonjour")
    check("le tag GCM fait 16 o et voyage collé", len(ct) == len(b"bonjour") + 16)
    try:
        a.decrypt(n, ct, b"autre-entete"); check("une AAD différente doit lever", False)
    except Exception:
        check("une AAD différente lève : l'en-tête est authentifié", True)
    try:
        a.decrypt(n, ct[:-1] + bytes([ct[-1] ^ 1]), b"entete"); check("un octet retourné doit lever", False)
    except Exception:
        check("un octet retourné lève : le chiffré est authentifié", True)
import ctypes
check("crypt32.CryptProtectData joignable par ctypes (DPAPI)", bool(ctypes.WinDLL("crypt32", use_last_error=True).CryptProtectData))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
