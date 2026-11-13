# -*- coding: utf-8 -*-
"""t521 (13/11/2026) — Réglages › « Moteurs et logiciels 3D », lot 1 : Blender et Godot.

Ce que l'application savait déjà faire avec eux (relevé du 13/11) : Blender sans interface pour les passes du plan,
l'export FBX et l'import FBX (passes_blender, studio3d_export, studio3d_import), « Ouvrir dans Blender » de l'Établi
(mesh_export) ; Godot : SpriteFrames .tres, TileSet, scène .tscn, dépôt et ouverture du projet (mesh_export,
sprite_export, tile_export, mouvement_rig). Mais leurs chemins (BLENDER_PATH, GODOT_PATH, GODOT_PROJECT_DIR) ne se
réglaient qu'en éditant le .env. Ce module donne à l'écran :
  - `etat()` : les champs et leurs valeurs (des chemins, pas des secrets) ;
  - `detecter(id)` : les exécutables trouvés, PROPOSÉS (rien n'est enregistré sans le clic de l'utilisateur) ;
  - `tester(id)` : la version lue SANS ouvrir de fenêtre (Blender `-b --version`, Godot `--headless --version` par
    sa console voisine), et pour Godot la vérification du dossier de projet (project.godot, nom lu).
Une seule règle trouve Blender : celle de passes_blender (BLENDER_PATH, puis Program Files, puis PATH).
Les messages sont des `app.i18n.Message` (logiciels3d.*), rendus dans la langue de l'écran par la route.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from app.i18n import Message

LOGICIELS: dict[str, dict] = {
    "blender": {"nom": "Blender", "min": (4, 2), "guide": "logiciels-3d",
                "champs": [{"cle": "BLENDER_PATH", "genre": "exe"}]},
    "godot": {"nom": "Godot", "min": (4, 0), "guide": "logiciels-3d",
              "champs": [{"cle": "GODOT_PATH", "genre": "exe"}, {"cle": "GODOT_PROJECT_DIR", "genre": "projet"}]},
}
_V_GODOT = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?\.(?:stable|beta|rc|dev|alpha)", re.I)
_V_NOM_GODOT = re.compile(r"godot_v(\d+)\.(\d+)(?:\.(\d+))?", re.I)
_NOM_PROJET = re.compile(r'^\s*config/name\s*=\s*"([^"]*)"', re.M)


def _M(cle, **vars):
    return Message(f"logiciels3d.{cle}", **vars)


def _val(cle: str) -> str:
    return os.environ.get(cle, "").strip().strip('"')


def _connu(lid: str) -> dict:
    if lid not in LOGICIELS:
        raise KeyError(lid)
    return LOGICIELS[lid]


def etat() -> list[dict]:
    return [{"id": lid, "nom": l["nom"], "guide": l["guide"],
             "champs": [{**ch, "valeur": _val(ch["cle"])} for ch in l["champs"]]} for lid, l in LOGICIELS.items()]


# ─────────────────────────────── Godot : trouver ───────────────────────────────

def _racines_godot() -> list[Path]:     # couture : remplacée au banc
    """Où Godot s'installe d'habitude sous Windows : il n'a pas d'installeur, c'est un .exe posé où l'on veut. On
    cherche donc dans Program Files, les programmes de l'utilisateur, Téléchargements et la bibliothèque Steam."""
    out = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        v = os.environ.get(var)
        if v:
            out.append(Path(v) / "Programs" if var == "LOCALAPPDATA" else Path(v))
    home = Path(os.environ.get("USERPROFILE", "") or Path.home())
    out += [home / "Downloads", home / "Desktop", home / "Godot"]
    pf86 = os.environ.get("ProgramFiles(x86)")
    if pf86:
        out.append(Path(pf86) / "Steam" / "steamapps" / "common" / "Godot Engine")
    return out


def _which(nom: str):                   # couture : remplacée au banc
    return shutil.which(nom)


def _exe_godot(p: Path) -> bool:
    n = p.name.lower()
    return n.endswith(".exe") and "godot" in n and "console" not in n and "uninstall" not in n


def _version_nom(p: Path) -> str | None:
    m = _V_NOM_GODOT.search(p.name)
    return ".".join(x for x in m.groups() if x) if m else None


def _candidats_godot() -> list[Path]:
    vus, out = set(), []
    for r in _racines_godot():
        try:
            if not r.is_dir():
                continue
            # deux niveaux suffisent (…/Godot/Godot_v4.3-stable_win64.exe) et gardent la recherche rapide
            for p in list(r.glob("*.exe")) + list(r.glob("*/*.exe")) + list(r.glob("*/*/*.exe")):
                if _exe_godot(p) and str(p) not in vus:
                    vus.add(str(p))
                    out.append(p)
        except OSError:
            continue
    for nom in ("godot", "godot4"):
        w = _which(nom)
        if w and str(w) not in vus:
            vus.add(str(w))
            out.append(Path(w))
    return out


def detecter(lid: str) -> list[dict]:
    _connu(lid)
    if lid == "blender":
        from app.services import passes_blender as PB
        return [{"chemin": str(p)} for p in PB.candidats_auto() if Path(p).is_file()]
    return [{"chemin": str(p), "version": _version_nom(p)} for p in _candidats_godot()]


# ─────────────────────────────── tester ───────────────────────────────

def _executer(argv: list, timeout: int = 20) -> str:   # couture : remplacée au banc
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    r = subprocess.run(argv, capture_output=True, timeout=timeout, creationflags=flags)
    return (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")


def _console(exe: Path) -> Path:
    """Godot pour Windows est livré avec une console voisine (…_console.exe) qui, elle, écrit sur la sortie."""
    c = exe.with_name(exe.stem + "_console.exe")
    return c if c.is_file() else exe


def _res(ok, message, version=None, **details):
    return {"ok": ok, "message": message, "version": version, "details": details}


def _tester_blender() -> dict:
    from app.services import passes_blender as PB
    e = PB.etat_blender(rafraichir=True)
    mini = ".".join(str(x) for x in LOGICIELS["blender"]["min"])
    if e["dispo"]:
        return _res(True, _M("blender.ok", version=e["version"]), e["version"], exe=e["exe"])
    if e["raison"] == "trop_ancien":
        return _res(False, _M("blender.trop_ancien", version=e["version"], minimum=mini), e["version"], exe=e["exe"])
    if _val("BLENDER_PATH"):
        return _res(False, _M("blender.illisible", chemin=_val("BLENDER_PATH")))
    return _res(None, _M("blender.absent", minimum=mini))


def _projet_godot() -> tuple:
    brut = _val("GODOT_PROJECT_DIR")
    if not brut:
        return None, None
    d = Path(brut)
    f = d / "project.godot"
    if not f.is_file():
        return False, _M("godot.projet_invalide", chemin=str(d))
    m = _NOM_PROJET.search(f.read_text("utf-8", errors="replace"))
    return True, (m.group(1) if m else d.name)


def _tester_godot() -> dict:
    brut = _val("GODOT_PATH")
    if not brut:
        return _res(None, _M("godot.sans_chemin"))
    exe = Path(brut)
    if not exe.is_file():
        return _res(False, _M("godot.introuvable", chemin=str(exe)))
    try:
        sortie = _executer([str(_console(exe)), "--headless", "--version"])
    except (OSError, subprocess.SubprocessError):
        sortie = ""
    m = _V_GODOT.search(sortie)
    version = ".".join(x for x in m.groups()[:3] if x) if m else _version_nom(exe)
    if not version:
        return _res(False, _M("godot.version_illisible", chemin=str(exe)))
    if tuple(int(x) for x in version.split(".")[:2]) < LOGICIELS["godot"]["min"]:
        return _res(False, _M("godot.trop_ancien", version=version), version, exe=str(exe))
    pok, pinfo = _projet_godot()
    if pok is False:
        return _res(False, pinfo, version, exe=str(exe))
    if pok:
        return _res(True, _M("godot.ok_projet", version=version, projet=pinfo), version, exe=str(exe), projet=pinfo)
    return _res(True, _M("godot.ok", version=version), version, exe=str(exe))


def tester(lid: str) -> dict:
    _connu(lid)
    return _tester_blender() if lid == "blender" else _tester_godot()
