# -*- coding: utf-8 -*-
"""t148 (traduction L8) — les bancs de l'Atelier, du Material Forge et de l'Établi lisent la source d'AVANT L8.

Les scripts frontend/{atelier,materialforge,etabli}/*.js passent par dzT(clé) ; ces bancs, écrits avant, cherchent
leurs phrases françaises dans la source ou en exécutent des morceaux sous node (où dzT n'existe pas). Importé en tête
d'un banc, ce module fait lire chacun de ces fichiers tel qu'il était AVANT L8 — par Path.read_text, Path.read_bytes
et open() en lecture —, reconstruit sans git par la table scripts/i18n_l8_paires.json
(_i18n_l1_aide.source_avant_i18n_l8). test_i18n_l8 garantit que la traduction se défait exactement et que chaque clé
rend son français : ce que ces bancs vérifient sur la vue d'avant vaut pour la source traduite.

    import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import _labs_avant_l8  # noqa
"""
import builtins
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as _A  # noqa: E402

_RT, _RB, _OPEN = pathlib.Path.read_text, pathlib.Path.read_bytes, builtins.open


def vise(p) -> bool:
    s = str(p).replace("\\", "/")
    return s.endswith(".js") and any(f"frontend/{d}/" in s for d in ("atelier", "materialforge", "etabli"))


def _avant_octets(b: bytes, chemin) -> bytes:
    t = b.decode("utf-8")
    return _A.source_avant_i18n_l8(t, chemin).encode("utf-8")


def _read_text(self, encoding=None, errors=None, newline=None):
    if not vise(self):
        return _RT(self, encoding=encoding, errors=errors, newline=newline)
    t = _avant_octets(_RB(self), str(self)).decode(encoding or "utf-8", errors or "strict")
    return t if newline == "" else t.replace("\r\n", "\n").replace("\r", "\n")


def _read_bytes(self):
    b = _RB(self)
    return _avant_octets(b, str(self)) if vise(self) else b


def _open(file, mode="r", *args, **kw):
    if isinstance(file, (str, pathlib.PurePath)) and vise(file) and set(mode) <= set("rbt"):
        b = _avant_octets(_RB(pathlib.Path(file)), str(file))
        if "b" in mode:
            return io.BytesIO(b)
        enc = kw.get("encoding") or (args[1] if len(args) > 1 else None) or "utf-8"
        nl = kw.get("newline", None)
        return io.TextIOWrapper(io.BytesIO(b), encoding=enc, newline=nl)
    return _OPEN(file, mode, *args, **kw)


if not getattr(pathlib.Path, "_labs_avant_l8", False):
    pathlib.Path.read_text = _read_text
    pathlib.Path.read_bytes = _read_bytes
    builtins.open = _open
    pathlib.Path._labs_avant_l8 = True
