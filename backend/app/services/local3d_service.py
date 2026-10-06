# -*- coding: utf-8 -*-
"""Service GPU local optionnel — T107 (plan-moteurs-3d T10, R10e D4), patron `voice_providers` (Voicebox).

Le Python EMBARQUÉ de l'application n'a ni numpy ni torch, et n'en aura pas : Hunyuan3D 2.1 demande Python 3.10 et
PyTorch 2.5.1+cu124 (README relu le 03/09/2026). Le service vit donc À CÔTÉ, comme Voicebox : un processus séparé que
l'utilisateur lance ou non, détecté par `GET /health`, réglé par `LOCAL3D_URL` (.env ; vide = 127.0.0.1:8081). Le
moteur `hunyuan-local` reste listé et GRISÉ tant que le service ne répond pas. Branché sans être installé (décision de
l'utilisateur, 06/10/2026) : aucun serveur n'est fourni ici.

Ce que le README de Hunyuan3D-2.1 dit, relu le 03/09/2026 :
  - VRAM : « 10 GB » pour la forme, « 21GB » pour la texture, « 29GB » pour les deux ; `--low_vram_mode` existe.
    Aucune génération de carte n'y est nommée : le seuil mesurable est la VRAM, et c'est celui qu'on applique.
  - `api_server.py` : `POST /generate` (rend le GLB), `GET /health`, port 8081.
  - `GenerationRequest` : `image` (base64), `remove_background`, `texture`, `seed`, `octree_resolution`,
    `num_inference_steps`, `guidance_scale`, `num_chunks`, `face_count`.
Carte de l'utilisateur relue le 06/10/2026 : RTX 2080 Ti, 11 264 Mio (nvidia-smi, pilote 617.14) → forme seule.
"""
from __future__ import annotations

import base64
import json
import subprocess
import time

DEFAULT_LOCAL3D_URL = "http://127.0.0.1:8081"

# README Hunyuan3D-2.1, relu le 03/09/2026 — en Mo, comme nvidia-smi
VRAM_FORME = 10 * 1024
VRAM_TEXTURE = 21 * 1024
VRAM_LES_DEUX = 29 * 1024
VRAM_OPTIMISE = 6 * 1024


def url() -> str:
    from app.config import settings
    return (getattr(settings, "LOCAL3D_URL", "") or "").strip().rstrip("/") or DEFAULT_LOCAL3D_URL


_reach_cache = {"t": 0.0, "ok": False}


def joignable(timeout: float = 2.0, ttl: float = 5.0) -> bool:
    """« Le service tourne » (GET /health), en cache `ttl` secondes : la liste des moteurs est relue à chaque écran."""
    import httpx
    now = time.monotonic()
    if ttl > 0 and now - _reach_cache["t"] < ttl:
        return _reach_cache["ok"]
    try:
        ok = httpx.get(url() + "/health", timeout=timeout).status_code == 200
    except Exception:  # noqa: BLE001 — absent, refusé, délai : tout veut dire « ne tourne pas »
        ok = False
    _reach_cache.update(t=now, ok=ok)
    return ok


# ── la carte, MESURÉE ────────────────────────────────────────────────────────

def _lire_nvidia_smi(timeout: float = 4.0):
    """(nom, VRAM en Mo) ou None. La source juste sur une carte NVIDIA : `memory.total` en MiB, sans plafond."""
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=timeout)
    except Exception:  # noqa: BLE001
        return None
    lignes = (r.stdout or "").strip().splitlines() if r.returncode == 0 else []
    if not lignes:
        return None
    parts = [p.strip() for p in lignes[0].split(",")]
    if len(parts) < 2 or not parts[1].isdigit():
        return None
    return parts[0], int(parts[1])


def _lire_win32(timeout: float = 6.0):
    """(nom, VRAM en Mo) ou None, par WMI. `AdapterRAM` est un uint32 : il plafonne à 4 Gio (4 293 918 720 pour une
    carte de 11 264 Mio, mesuré le 03/09/2026). C'est un repli, pas une source."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            "Get-CimInstance Win32_VideoController | Select-Object -First 1 Name,AdapterRAM | "
                            "ConvertTo-Json"], capture_output=True, text=True, timeout=timeout)
        d = json.loads(r.stdout) if r.returncode == 0 and (r.stdout or "").strip() else None
    except Exception:  # noqa: BLE001
        return None
    if isinstance(d, list):
        d = d[0] if d else None
    if not isinstance(d, dict) or not isinstance(d.get("AdapterRAM"), int):
        return None
    return str(d.get("Name") or "?"), int(d["AdapterRAM"]) // (1 << 20)


_carte_cache = {"t": 0.0, "v": None}


def carte(ttl: float = 60.0) -> dict:
    """{nom, vram_mo, source, avertissement} : nvidia-smi d'abord, WMI ensuite, rien en dernier — et le dire."""
    now = time.monotonic()
    if ttl > 0 and _carte_cache["v"] is not None and now - _carte_cache["t"] < ttl:
        return _carte_cache["v"]
    lu = _lire_nvidia_smi()
    if lu:
        out = {"nom": lu[0], "vram_mo": lu[1], "source": "nvidia-smi", "avertissement": None}
    else:
        lu = _lire_win32()
        if lu:
            out = {"nom": lu[0], "vram_mo": lu[1], "source": "win32",
                   "avertissement": "Win32_VideoController.AdapterRAM est un uint32 : il plafonne à 4 Gio. Une carte "
                                    "plus grosse est sous-évaluée ici — installe les outils NVIDIA (nvidia-smi)."}
        else:
            out = {"nom": None, "vram_mo": None, "source": None,
                   "avertissement": "Ni nvidia-smi ni WMI n'ont répondu : carte inconnue, service local non proposé."}
    _carte_cache.update(t=now, v=out)
    return out


def decision(vram_mo) -> dict:
    """Ce qu'on PROPOSE pour cette VRAM. Aucune génération de carte n'entre dans ce calcul."""
    v = int(vram_mo) if isinstance(vram_mo, (int, float)) and vram_mo else 0
    if v >= VRAM_LES_DEUX:
        return {"moteur": "hunyuan-2.1", "texture": True, "low_vram": False, "verifie": True,
                "pourquoi": f"{v} Mo ≥ 29 Go : forme ET texture tiennent (README Hunyuan3D-2.1)."}
    if v >= VRAM_TEXTURE:
        return {"moteur": "hunyuan-2.1", "texture": True, "low_vram": False, "verifie": True,
                "pourquoi": f"{v} Mo ≥ 21 Go : la texture tient, les deux passes ensemble non."}
    if v >= VRAM_FORME:
        return {"moteur": "hunyuan-2.1", "texture": False, "low_vram": False, "verifie": True,
                "pourquoi": f"{v} Mo ≥ 10 Go : la FORME tient. La texture demande 21 Go — texture par fal ou Meshy."}
    if v >= VRAM_OPTIMISE:
        return {"moteur": "hunyuan-optimise", "texture": False, "low_vram": True, "verifie": False,
                "pourquoi": f"{v} Mo : sous les 10 Go du README. Les variantes communautaires annoncent 3–6 Go avec "
                            "--low_vram_mode — NON VÉRIFIÉ : à mesurer au premier essai."}
    return {"moteur": "fal", "texture": True, "low_vram": False, "verifie": True,
            "pourquoi": (f"{v} Mo" if v else "carte inconnue") + " : trop peu pour Hunyuan3D. fal reste la voie."}


def disponible() -> list[dict]:
    """Pour l'écran : les deux voies et leur état, toujours les deux."""
    from app.config import settings
    c = carte()
    return [
        {"id": "fal", "label": "fal.ai (cloud, clé API)", "ready": bool((settings.FAL_KEY or "").strip())},
        {"id": "local3d", "label": "Service GPU local (Hunyuan3D 2.1)", "ready": joignable(), "url": url(),
         "carte": c, "decision": decision(c["vram_mo"])},
    ]


# ── l'appel ──────────────────────────────────────────────────────────────────

async def _octets_de_l_image(image_url: str) -> bytes:
    """Les octets de l'image d'entrée. `generate_asset3d` passe un data: URI (aucun envoi chez fal) ; une URL http
    (vues déjà sur le stockage fal, chemin « Vues d'abord ») est relue par le réseau."""
    import httpx
    if image_url.startswith("data:"):
        return base64.b64decode(image_url.split(",", 1)[1])
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.get(image_url)
        r.raise_for_status()
        return r.content


async def _poster_generate(cible: str, charge: dict, timeout: float) -> bytes:
    import httpx
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(cible, json=charge)
        r.raise_for_status()
        return r.content


def message_absent() -> str:
    return ("Le service GPU local ne répond pas sur " + url() + " (Hunyuan3D 2.1, port 8081 par défaut). Lance-le à "
            "côté de l'application, ou choisis un moteur fal. Réglage : LOCAL3D_URL dans le fichier .env.")


async def run_engine(engine: str, args: dict) -> dict:
    """La couture appelée par `asset3d_service._run_engine` pour un moteur `local`. Rend la MÊME forme que
    `parse_engine_result` (mesh_url en data: URI, que `_download` relit) : le reste du flux ne sait pas d'où vient
    le GLB."""
    if not joignable():
        raise RuntimeError(message_absent())
    d = decision(carte()["vram_mo"])
    if d["moteur"] == "fal":
        raise RuntimeError("Le service répond, mais cette carte ne suffit pas : " + d["pourquoi"])
    image = await _octets_de_l_image(str(args.get("image_url") or ""))
    charge = {
        "image": base64.b64encode(image).decode("ascii"),
        "remove_background": True,
        "texture": bool(args.get("texture")) and d["texture"],
        "seed": int(args.get("seed") or 1234),
        "octree_resolution": 256, "num_inference_steps": 5, "guidance_scale": 5.0, "num_chunks": 8000,
        "face_count": int(args.get("face_limit") or 40000),
    }
    glb = await _poster_generate(url() + "/generate", charge, timeout=900.0)
    if not glb.startswith(b"glTF"):
        raise RuntimeError(f"le service local n'a pas rendu un GLB ({len(glb)} octets, entête {glb[:8]!r})")
    return {"mesh_url": "data:model/gltf-binary;base64," + base64.b64encode(glb).decode("ascii"),
            "format_urls": {}, "texture_urls": {}, "preview_url": None}
