"""DPAPI par ctypes (plan Settings T15 — tâche #20, 29/09/2026).

Ce que ça fait : sceller un secret POUR CETTE SESSION WINDOWS. Ce que ça ne fait pas : donner un mot de passe maître
(il n'y a rien à saisir) ni produire quoi que ce soit de lisible ailleurs — un blob DPAPI est illisible sur un autre
PC. Il sert donc ici de SERRURE LOCALE sur le mot de passe du coffre (« retenir sur ce PC ») et jamais de coffre à lui
tout seul.

Mesuré le 03/09 et revérifié le 29/09 sous le runtime embarqué (3.13.15) : `crypt32` se charge par ctypes, sans rien
ajouter au runtime. Piège : avec `ctypes.windll`, `get_last_error()` rend 0 même en cas d'échec — d'où
`WinDLL(..., use_last_error=True)`.
"""
import ctypes
import ctypes.wintypes as wt

from loguru import logger

CRYPTPROTECT_UI_FORBIDDEN = 0x01


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


_crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


def _entree(b: bytes) -> tuple:
    buf = ctypes.create_string_buffer(b, len(b))
    return _BLOB(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _sortie(blob: _BLOB) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        _kernel32.LocalFree(blob.pbData)


def _appel(fn, data: bytes, entropie: bytes):
    dedans, _g1 = _entree(data)
    ent, _g2 = _entree(entropie or b"")
    dehors = _BLOB()
    ok = fn(ctypes.byref(dedans), None, ctypes.byref(ent) if entropie else None,
            None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(dehors))
    if not ok:
        logger.info(f"dpapi: appel refusé (GetLastError={ctypes.get_last_error()})")
        return None
    return _sortie(dehors)


def sceller(donnees: bytes, entropie: bytes = b"") -> bytes:
    b = _appel(_crypt32.CryptProtectData, donnees, entropie)
    if b is None:
        raise OSError("DPAPI : CryptProtectData a échoué")
    return b


def desceller(blob: bytes, entropie: bytes = b""):
    """None plutôt qu'une exception : un blob illisible (autre compte, autre machine, fichier corrompu) est un cas
    NORMAL — l'app redemande le mot de passe, elle ne plante pas."""
    try:
        return _appel(_crypt32.CryptUnprotectData, blob, entropie)
    except Exception as e:  # noqa: BLE001
        logger.info(f"dpapi: descellement impossible ({e})")
        return None
