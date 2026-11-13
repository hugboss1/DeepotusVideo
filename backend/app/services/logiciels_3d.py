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

Lot 2 (14/11/2026) : Unreal Engine, Unity et la carte Blender MCP.
  - Unreal : UnrealEditor.exe ; version lue dans Engine/Build/Build.version (JSON), RIEN n'est lancé ; détection par le
    lanceur Epic (%ProgramData%/Epic/UnrealEngineLauncher/LauncherInstalled.dat), puis Program Files/Epic Games/UE_* ;
    projet = dossier qui contient un .uproject. Unreal 5 requis : l'import glTF natif (Interchange) date de la 5.x.
  - Unity : Unity.exe ; version lue dans le dossier de l'éditeur Unity Hub (…/Hub/Editor/<version>/Editor/Unity.exe),
    RIEN n'est lancé ; projet = dossier qui contient Assets/ (version de l'éditeur dans
    ProjectSettings/ProjectVersion.txt) ; sans le paquet glTFast dans Packages/manifest.json, les .glb déposés restent
    inertes : on le dit (comme mesh_export.deposer).
  - Blender MCP : l'exécutable mcp-for-blender et le port de son add-on ; « Tester » = blender_mcp.sonder (lit les
    outils et l'état de la scène, ne modifie rien).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from app.i18n import Message

LOGICIELS: dict[str, dict] = {
    "blender": {"nom": "Blender", "min": (4, 2), "guide": "logiciels-3d",
                "champs": [{"cle": "BLENDER_PATH", "genre": "exe"}]},
    "blender_mcp": {"nom": "Blender MCP", "min": None, "guide": "logiciels-3d",
                    "champs": [{"cle": "BLENDER_MCP_EXE", "genre": "exe"}, {"cle": "BLENDER_MCP_PORT", "genre": "port"}]},
    "godot": {"nom": "Godot", "min": (4, 0), "guide": "logiciels-3d",
              "champs": [{"cle": "GODOT_PATH", "genre": "exe"}, {"cle": "GODOT_PROJECT_DIR", "genre": "projet"}]},
    "unreal": {"nom": "Unreal Engine", "min": (5, 0), "guide": "logiciels-3d",
               "champs": [{"cle": "UNREAL_PATH", "genre": "exe"}, {"cle": "UNREAL_PROJECT_DIR", "genre": "projet"}]},
    "unity": {"nom": "Unity", "min": None, "guide": "logiciels-3d",
              "champs": [{"cle": "UNITY_PATH", "genre": "exe"}, {"cle": "UNITY_PROJECT_DIR", "genre": "projet"}]},
}
_V_UNITY = re.compile(r"^\d+\.\d+\.\d+[a-z]\d+$")
_V_PROJET_UNITY = re.compile(r"m_EditorVersion:\s*(\S+)")
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


# ─────────────────────────────── Unreal, Unity : trouver (lot 2) ───────────────────────────────

def _lanceur_epic() -> Path:            # couture : remplacée au banc
    return Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Epic" / "UnrealEngineLauncher" / "LauncherInstalled.dat"


def _racines_unreal() -> list[Path]:    # couture : remplacée au banc
    return [Path(os.environ[v]) / "Epic Games" for v in ("ProgramFiles", "ProgramFiles(x86)") if os.environ.get(v)]


def _racines_unity() -> list[Path]:     # couture : remplacée au banc
    out = []
    for v in ("ProgramFiles", "ProgramFiles(x86)"):
        if os.environ.get(v):
            out += [Path(os.environ[v]) / "Unity" / "Hub" / "Editor", Path(os.environ[v]) / "Unity"]
    return out


def _exe_unreal(racine: Path) -> Path:
    return racine / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"


def _build_version(exe: Path) -> str | None:
    """Engine/Build/Build.version, voisin de Engine/Binaries/Win64/UnrealEditor.exe : lu, jamais exécuté."""
    try:
        f = exe.parents[2] / "Build" / "Build.version"
        d = json.loads(f.read_text("utf-8", errors="replace"))
        return ".".join(str(int(d[k])) for k in ("MajorVersion", "MinorVersion", "PatchVersion"))
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return None


def _candidats_unreal() -> list[Path]:
    vus, out = set(), []
    try:
        d = json.loads(_lanceur_epic().read_text("utf-8", errors="replace"))
        for x in d.get("InstallationList") or []:
            if str(x.get("AppName", "")).startswith("UE_") and x.get("InstallLocation"):
                p = _exe_unreal(Path(x["InstallLocation"]))
                if p.is_file() and str(p) not in vus:
                    vus.add(str(p)); out.append(p)
    except (OSError, ValueError, AttributeError):
        pass
    for r in _racines_unreal():
        try:
            for d in sorted(r.glob("UE_*"), reverse=True):
                p = _exe_unreal(d)
                if p.is_file() and str(p) not in vus:
                    vus.add(str(p)); out.append(p)
        except OSError:
            continue
    return out


def _version_unity(exe: Path) -> str | None:
    """…/Hub/Editor/<version>/Editor/Unity.exe : la version est le nom du dossier ; rien n'est lancé."""
    try:
        n = exe.parents[1].name
    except IndexError:
        return None
    return n if _V_UNITY.match(n) else None


def _candidats_unity() -> list[Path]:
    vus, out = set(), []
    for r in _racines_unity():
        try:
            for p in sorted(r.glob("*/Editor/Unity.exe"), reverse=True):
                if p.is_file() and str(p) not in vus:
                    vus.add(str(p)); out.append(p)
        except OSError:
            continue
    return out


def detecter(lid: str) -> list[dict]:
    _connu(lid)
    if lid == "blender":
        from app.services import passes_blender as PB
        return [{"chemin": str(p)} for p in PB.candidats_auto() if Path(p).is_file()]
    if lid == "blender_mcp":
        from app.services import blender_mcp as BM
        return [{"chemin": str(BM.EXE_DEFAUT)}] if Path(BM.EXE_DEFAUT).is_file() else []
    if lid == "unreal":
        return [{"chemin": str(p), "version": _build_version(p)} for p in _candidats_unreal()]
    if lid == "unity":
        return [{"chemin": str(p), "version": _version_unity(p)} for p in _candidats_unity()]
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


def _tester_unreal() -> dict:
    brut = _val("UNREAL_PATH")
    if not brut:
        return _res(None, _M("unreal.sans_chemin"))
    exe = Path(brut)
    if not exe.is_file():
        return _res(False, _M("godot.introuvable", chemin=str(exe)))
    version = _build_version(exe)
    if not version:
        return _res(False, _M("unreal.version_illisible", chemin=str(exe)))
    if tuple(int(x) for x in version.split(".")[:2]) < LOGICIELS["unreal"]["min"]:
        return _res(False, _M("unreal.trop_ancien", version=version), version, exe=str(exe))
    pb = _val("UNREAL_PROJECT_DIR")
    if pb:
        projets = sorted(Path(pb).glob("*.uproject")) if Path(pb).is_dir() else []
        if not projets:
            return _res(False, _M("unreal.projet_invalide", chemin=pb), version, exe=str(exe))
        return _res(True, _M("unreal.ok_projet", version=version, projet=projets[0].stem), version, exe=str(exe),
                    projet=projets[0].stem)
    return _res(True, _M("unreal.ok", version=version), version, exe=str(exe))


def _tester_unity() -> dict:
    brut = _val("UNITY_PATH")
    if not brut:
        return _res(None, _M("unity.sans_chemin"))
    exe = Path(brut)
    if not exe.is_file():
        return _res(False, _M("godot.introuvable", chemin=str(exe)))
    version = _version_unity(exe)
    pb = _val("UNITY_PROJECT_DIR")
    if pb:
        d = Path(pb)
        if not (d / "Assets").is_dir():
            return _res(False, _M("unity.projet_invalide", chemin=pb), version, exe=str(exe))
        pv = d / "ProjectSettings" / "ProjectVersion.txt"
        m = _V_PROJET_UNITY.search(pv.read_text("utf-8", errors="replace")) if pv.is_file() else None
        vprojet = m.group(1) if m else "?"
        man = d / "Packages" / "manifest.json"
        if not (man.is_file() and "com.unity.cloud.gltfast" in man.read_text("utf-8", errors="replace")):
            return _res(None, _M("unity.sans_gltfast", projet=d.name), version, exe=str(exe), projet=d.name)
        return _res(True, _M("unity.ok_projet", projet=d.name, version_projet=vprojet), version, exe=str(exe),
                    projet=d.name)
    if not version:
        return _res(None, _M("unity.version_inconnue", chemin=str(exe)), None, exe=str(exe))
    return _res(True, _M("unity.ok", version=version), version, exe=str(exe))


def _tester_blender_mcp() -> dict:
    from app.services import blender_mcp as BM
    brut_port = _val("BLENDER_MCP_PORT")
    if brut_port and not (brut_port.isdigit() and 1024 <= int(brut_port) <= 65535):
        return _res(False, _M("blender_mcp.port_invalide", port=brut_port))
    e = BM.etat_exe()
    if not e["trouve"]:
        return _res(None, _M("blender_mcp.absent", chemin=e["chemin"]))
    try:
        s = BM.sonder()
    except BM.RefusBlender as err:
        return _res(False, Message(err.cle, **err.valeurs))
    except Exception as err:  # noqa: BLE001 — un test ne casse jamais l'écran
        return _res(False, _M("blender_mcp.erreur", detail=str(err)[:160]))
    v = (s.get("serveur") or {}).get("version") or "?"
    n = len(s.get("outils") or [])
    if not s.get("connecte"):
        return _res(None, _M("blender_mcp.blender_ferme", version=v, outils=n, port=BM.port()), v, exe=e["chemin"])
    return _res(True, _M("blender_mcp.ok", version=v, outils=n), v, exe=e["chemin"])


def tester(lid: str) -> dict:
    _connu(lid)
    return {"blender": _tester_blender, "blender_mcp": _tester_blender_mcp, "godot": _tester_godot,
            "unreal": _tester_unreal, "unity": _tester_unity}[lid]()
