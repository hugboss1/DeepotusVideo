# -*- coding: utf-8 -*-
"""Le coffre (plan Settings T15 — tâche #20, 29/09/2026) : DPAPI, dérivation, AES-256-GCM, format DZKV1 figé.
Banc-miroir : le coffre est relu DEPUIS LE FICHIER, le format est vérifié octet par octet, et l'effet sur le processus
(settings, os.environ) est relu après ouvrir/fermer. Exige `cryptography` (requirements.txt) : lancer avec un runtime
qui l'a tant que l'installé ne l'a pas reçue.
Run : & $PY tests/test_coffre.py   (depuis backend/)"""
import json, os, pathlib, struct, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcoffre_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("FAL_KEY", "MESHY_API_KEY", "HEYGEN_API_KEY"):
    os.environ.pop(_k, None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.config import settings                                     # noqa: E402
from app.services import coffre as C, dpapi as D                    # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def leve(exc, f):
    try:
        f()
    except exc as e:
        return e
    except Exception as e:  # noqa: BLE001
        return ("autre", repr(e))
    return None


print("\n[1] DPAPI")
b = D.sceller(b"un-secret-de-32-octets-exactement", b"deepotus")
check("1.1 le blob n'est pas le clair, DPAPI ajoute son enveloppe", b"un-secret" not in b and len(b) > 100, str(len(b)))
check("1.2 aller-retour", D.desceller(b, b"deepotus") == b"un-secret-de-32-octets-exactement")
check("1.3 une autre entropie rend None, jamais une exception nue", D.desceller(b, b"autre") is None)
check("1.4 un blob invalide rend None", D.desceller(b"nimporte quoi", b"deepotus") is None)

print("\n[2] format DZKV1")
obj = {"cles": {"FAL_KEY": "abc"}}
blob = C.chiffrer(obj, "mon mot de passe", iterations=1000)
check("2.1 magie DZKV1", blob[:6] == b"DZKV1\n")
check("2.2 en-tête 38 o + tag 16 o + le JSON compact", len(blob) == 38 + 16 + len(json.dumps(obj, separators=(",", ":")).encode()), str(len(blob)))
check("2.3 les itérations sont dans l'en-tête", struct.unpack(">I", blob[22:26])[0] == 1000)
check("2.4 aller-retour", C.dechiffrer(blob, "mon mot de passe") == obj)
e = leve(C.MotDePasseInvalide, lambda: C.dechiffrer(blob, "mauvais"))
check("2.5 mauvais mot de passe : refus DIT en français", isinstance(e, C.MotDePasseInvalide) and "mot de passe" in str(e).lower(), repr(e))
casse = blob[:22] + struct.pack(">I", 999) + blob[26:]
check("2.6 l'AAD couvre l'en-tête : itérations trafiquées -> refus", isinstance(leve(C.MotDePasseInvalide, lambda: C.dechiffrer(casse, "mon mot de passe")), C.MotDePasseInvalide))
retourne = blob[:-1] + bytes([blob[-1] ^ 1])
check("2.7 un octet du chiffré retourné -> refus", isinstance(leve(C.MotDePasseInvalide, lambda: C.dechiffrer(retourne, "mon mot de passe")), C.MotDePasseInvalide))
_b1, _b2 = C.chiffrer({"a": 1}, "x", 1000), C.chiffrer({"a": 1}, "x", 1000)
check("2.8 un sel neuf à chaque chiffrement", _b1[6:22] != _b2[6:22])
check("2.8b un nonce neuf à chaque chiffrement (réutiliser un nonce casse GCM)", _b1[26:38] != _b2[26:38])
# LE CONTRAT DU MOBILE, lu comme il le lira : un décodeur écrit d'après la SPÉCIFICATION seule (en-tête, PBKDF2,
# AES-256-GCM avec les 38 premiers octets en AAD) — pas par `C.dechiffrer`.
import hashlib as _h                                                # noqa: E402
from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _A  # noqa: E402
_sel, _it, _no = blob[6:22], struct.unpack(">I", blob[22:26])[0], blob[26:38]
_cle = _h.pbkdf2_hmac("sha256", "mon mot de passe".encode("utf-8"), _sel, _it, dklen=32)
try:
    _clair = _A(_cle).decrypt(_no, blob[38:], blob[:38])
except Exception as _e:  # noqa: BLE001
    _clair = repr(_e).encode()
check("2.11 décodeur de référence (spécification seule, AAD = 38 premiers octets) : même objet", _clair == json.dumps(obj, separators=(",", ":")).encode(), _clair[:80])
check("2.9 un fichier qui n'est pas DZKV1 -> refus", isinstance(leve(C.MotDePasseInvalide, lambda: C.dechiffrer(b"PK\x03\x04" + b"0" * 80, "x")), C.MotDePasseInvalide))
check("2.10 itérations aberrantes -> refus sans dériver 4 milliards de fois",
      isinstance(leve(C.MotDePasseInvalide, lambda: C.dechiffrer(blob[:22] + struct.pack(">I", 0xFFFFFFFF) + blob[26:], "x")), C.MotDePasseInvalide))

print("\n[3] poser, ouvrir, écrire, fermer")
check("3.1 aucun coffre au départ", C.est_pose() is False and C.ouvert() is False)
check("3.2 mot de passe trop court : refus", isinstance(leve(ValueError, lambda: C.poser("court", {})), ValueError))
C.poser("mot-de-passe-maitre", {"FAL_KEY": "fal-123", "MESHY_API_KEY": "me-456"})
brut = (_tmp / "coffre.dzk").read_bytes()
check("3.3 rien de lisible dans le fichier : ni la valeur, ni le nom de la clé", b"fal-123" not in brut and b"FAL_KEY" not in brut)
check("3.4 poser ne laisse pas le coffre ouvert, et n'applique rien", C.ouvert() is False and settings.FAL_KEY != "fal-123")
check("3.5 mauvais mot de passe : refus", isinstance(leve(C.MotDePasseInvalide, lambda: C.ouvrir("pas-le-bon")), C.MotDePasseInvalide))
t = time.perf_counter()
cles = C.ouvrir("mot-de-passe-maitre")
duree = time.perf_counter() - t
check("3.6 le coffre rend ses clés", cles == {"FAL_KEY": "fal-123", "MESHY_API_KEY": "me-456"})
check(f"3.7 ouverture en {duree:.2f} s (600 000 itérations ; au-delà de 1,5 s il faudrait baisser)", duree < 1.5, f"{duree:.2f}")
check("3.8 ouvrir APPLIQUE à chaud : settings et os.environ", settings.FAL_KEY == "fal-123" and os.environ.get("MESHY_API_KEY") == "me-456")
C.ecrire_cle("HEYGEN_API_KEY", "hg-789")
check("3.9 écrire une clé l'applique aussi", settings.HEYGEN_API_KEY == "hg-789")
C.fermer()
check("3.10 fermé : plus rien du coffre en mémoire", C.ouvert() is False and C.lire_cle("FAL_KEY") is None)
check("3.11 fermé : ses clés sont RETIRÉES du processus", settings.FAL_KEY == "" and "FAL_KEY" not in os.environ and settings.HEYGEN_API_KEY == "", repr(settings.FAL_KEY))
check("3.12 l'écriture a bien été rechiffrée sur le disque", C.ouvrir("mot-de-passe-maitre")["HEYGEN_API_KEY"] == "hg-789")
C.ecrire_cle("MESHY_API_KEY", "")
check("3.13 une valeur vide efface la clé du coffre", "MESHY_API_KEY" not in C.cles_posees())
C.fermer()
check("3.14 écrire coffre fermé : refus", isinstance(leve(C.CoffreVerrouille, lambda: C.ecrire_cle("FAL_KEY", "x")), C.CoffreVerrouille))

print("\n[4] changer le mot de passe")
C.ouvrir("mot-de-passe-maitre")
C.retenir()
C.changer_mot_de_passe("mot-de-passe-maitre", "un-autre-secret")
check("4.1 changer efface le sceau DPAPI (il portait l'ancien)", not (_tmp / "coffre.pc").exists())
C.ecrire_cle("FAL_KEY", "fal-apres")
C.fermer()
check("4.2 l'ancien mot de passe est mort", isinstance(leve(C.MotDePasseInvalide, lambda: C.ouvrir("mot-de-passe-maitre")), C.MotDePasseInvalide))
check("4.3 le coffre resté ouvert écrit avec le NOUVEAU", C.ouvrir("un-autre-secret")["FAL_KEY"] == "fal-apres")

print("\n[5] retenir sur ce PC")
C.retenir()
scelle = (_tmp / "coffre.pc").read_bytes()
check("5.1 sceau DPAPI écrit, le mot de passe n'y est pas en clair", b"un-autre-secret" not in scelle)
C.fermer()
check("5.2 le coffre s'ouvre seul sur ce PC", C.ouvrir_par_dpapi() is True and C.lire_cle("FAL_KEY") == "fal-apres")
C.fermer()
C.poser("mot-de-passe-tiers", {})          # un autre coffre remplace le fichier : le sceau ne l'ouvre plus
check("5.3 sceau périmé : False, et il est effacé", C.ouvrir_par_dpapi() is False and not (_tmp / "coffre.pc").exists())
C.ouvrir("mot-de-passe-tiers"); C.retenir(); C.oublier(); C.fermer()
check("5.4 oublier() coupe l'ouverture automatique", C.ouvrir_par_dpapi() is False and not (_tmp / "coffre.pc").exists())
check("5.5 retenir coffre fermé : refus", isinstance(leve(C.CoffreVerrouille, C.retenir), C.CoffreVerrouille))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
