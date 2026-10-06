# -*- coding: utf-8 -*-
"""Les vues AVANT le tir — T106 (plan-moteurs-3d T6, R10e P5).

`generate_asset3d` fait tout d'une traite : envoi, vues Seedream, moteur, téléchargements. Une vue ratée (bras coupé,
fond sale, profil de trois quarts) est donc payée DEUX fois — la vue, puis le maillage qu'elle abîme. Ici la passe est
coupée en deux :

    preparer_vues()  envoi + vues -> shot_i.png + views.json (état « en_attente »), AUCUN moteur
    rejouer_vue()    UNE vue seulement, avec un prompt corrigé
    detourer_vue()   fond retiré : local et gratuit (masque des quatre coins), fal en option
    tirer_vues()     asset3d_service.tirer_moteur() sur les vues telles qu'elles sont MAINTENANT

Aucune couture nouvelle : les mêmes `asset3d_service._upload` / `_seedream_edit` / `_download` que le chemin d'un clic.
Chaque vue garde sa CLÉ (front, back, left, right) : c'est elle, pas la position, qui ordonne l'envoi au moteur.
Une vue retouchée sur le disque (détourage local) est marquée `a_renvoyer` : son URL fal montre encore l'ancienne
image, et le tir la ré-envoie. Les gardes de dépense vivent dans les ROUTES, pas ici."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

MAX_VUES = 4                 # le quatuor orthographique d'asset3d_service


def _dir(job) -> Path:
    from app.config import settings
    return settings.outputs_path / "assets3d" / Path(str(job)).name


def _chemin(job) -> Path:
    return _dir(job) / "views.json"


def lire_vues(job) -> dict:
    p = _chemin(job)
    if not p.is_file():
        raise FileNotFoundError(f"aucun jeu de vues pour le job {Path(str(job)).name!r}")
    return json.loads(p.read_text(encoding="utf-8"))


def lister_vues() -> list[dict]:
    """Les jeux de vues du disque, le plus récent d'abord (résumé pour l'écran)."""
    from app.config import settings
    racine = settings.outputs_path / "assets3d"
    out = []
    if not racine.is_dir():
        return out
    for p in racine.glob("*/views.json"):
        try:
            v = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({"job": p.parent.name, "etat": v.get("etat"), "engine": v.get("engine"),
                    "image_filename": v.get("image_filename"), "created_at": v.get("created_at"),
                    "vues": len(v.get("vues") or []),
                    "ratees": sum(1 for x in v.get("vues") or [] if not x.get("file"))})
    return sorted(out, key=lambda x: str(x.get("created_at") or ""), reverse=True)


def _ecrire(job, data: dict) -> dict:
    d = _dir(job)
    d.mkdir(parents=True, exist_ok=True)
    tmp = _chemin(job).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_chemin(job))
    return data


def _ouvert(info: dict) -> None:
    if info.get("etat") == "tire":
        raise ValueError("ce jeu de vues a déjà été tiré : le maillage existe. Prépare un nouveau jeu pour retirer.")


def _vue(info: dict, index) -> dict:
    i = int(index)
    vues = info["vues"]
    if not (0 <= i < len(vues)):
        raise ValueError(f"vue {i} inconnue (0..{len(vues) - 1})")
    return vues[i]


def nombre_de_vues(payload: dict) -> int:
    """Le nombre de vues demandé, borné à 1..4 ; ValueError s'il n'est pas un entier."""
    try:
        n = int(payload.get("views", MAX_VUES))
    except (TypeError, ValueError):
        raise ValueError("views : un entier de 1 à 4")
    return max(1, min(MAX_VUES, n))


async def preparer_vues(payload: dict, job: str, on_step=None) -> dict:
    """Envoi + vues, et RIEN d'autre : le moteur n'est pas appelé, c'est tout l'intérêt."""
    import asyncio
    import shutil
    from app.config import settings
    from app.services import asset3d_service as A3

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in A3.ENGINES:
        raise ValueError(f"Unknown engine: {engine}")
    fn = Path(str(payload.get("image_filename") or "")).name
    src = settings.images_path / fn
    if not fn or not src.is_file() or not str(src.resolve()).startswith(str(settings.images_path.resolve())):
        raise ValueError(f"Image not found in Library: {payload.get('image_filename')!r}")
    n = nombre_de_vues(payload)

    d = _dir(job)
    d.mkdir(parents=True, exist_ok=True)
    await _step("Envoi de la source", 10)
    url = await A3._upload(src)
    shutil.copy2(src, d / "shot_0.png")
    vues = [{"index": 0, "cle": "source", "role": "source", "file": "shot_0.png", "url": url,
             "prompt": None, "rejeux": 0, "detoure": None}]
    for i, pr in enumerate(A3.view_prompts(n, payload.get("subject", "")), 1):
        await _step(f"Vue {i}/{n}", 10 + int(80 * i / n))
        v = {"index": i, "cle": A3.VUES_CLES[i - 1], "role": "vue", "file": None, "url": None,
             "prompt": pr, "rejeux": 0, "detoure": None}
        try:
            u = await A3._seedream_edit(url, pr)
        except Exception as e:                  # noqa: BLE001 — une vue ratée n'annule pas les autres (déjà payées)
            u, v["erreur"] = None, str(e)[:300]
        if u:
            await asyncio.to_thread(A3._download, u, d / f"shot_{i}.png")
            v.update(file=f"shot_{i}.png", url=u)
        elif "erreur" not in v:
            v["erreur"] = "aucune image rendue"
        vues.append(v)

    info = _ecrire(job, {
        "job": Path(str(job)).name, "etat": "en_attente", "engine": engine, "image_filename": fn,
        "payload": {k: v for k, v in payload.items() if k not in ("image_filename", "job")},
        "vues": vues, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    await _step("Vues prêtes — à toi de juger", 100)
    return {"job": info["job"], "etat": info["etat"], "vues": len(vues),
            "ratees": sum(1 for v in vues if not v["file"])}


def verifier_rejeu(job, index: int, prompt: str | None = None) -> tuple[dict, dict, str]:
    """Les refus du rejeu, sans rien faire : la route les appelle AVANT la garde. Rend (info, vue, prompt)."""
    info = lire_vues(job)
    _ouvert(info)
    v = _vue(info, index)
    if v["role"] == "source":
        raise ValueError("la vue 0 est ta source : elle ne se régénère pas — change d'image dans la Bibliothèque.")
    if v["role"] == "planche":
        raise ValueError("cette vue est reprise de la planche de la bible : elle ne se régénère pas ici — refais la "
                         "planche dans la bible, ou détoure la vue.")
    pr = str(prompt or v.get("prompt") or "").strip()
    if not pr:
        raise ValueError("cette vue n'a pas de prompt : donnes-en un")
    return info, v, pr


async def rejouer_vue(job, index: int, *, prompt: str | None = None, on_step=None) -> dict:
    """UNE vue régénérée depuis la source, avec le prompt corrigé si on en donne un. La source de l'utilisateur et
    les vues reprises d'une planche ne se rejouent pas."""
    import asyncio
    from app.services import asset3d_service as A3
    info, v, pr = verifier_rejeu(job, index, prompt)
    if on_step:
        await on_step(f"Vue {v['index']}", 30)
    source = next((x for x in info["vues"] if x["role"] == "source"), info["vues"][0])
    u = await A3._seedream_edit(source["url"], pr)
    if not u:
        raise RuntimeError("aucune image rendue")
    await asyncio.to_thread(A3._download, u, _dir(job) / f"shot_{v['index']}.png")
    v.update(file=f"shot_{v['index']}.png", url=u, prompt=pr, rejeux=int(v.get("rejeux") or 0) + 1, detoure=None)
    v.pop("erreur", None); v.pop("a_renvoyer", None); v.pop("methode", None)
    _ecrire(job, info)
    if on_step:
        await on_step("Complete", 100)
    return {"index": v["index"], "file": v["file"], "rejeux": v["rejeux"]}


def verifier_detourage(job, index: int) -> dict:
    """Les refus du détourage, sans rien faire : la route les appelle AVANT la garde (via fal)."""
    info = lire_vues(job)
    _ouvert(info)
    v = _vue(info, index)
    if v["role"] == "source":
        raise ValueError("la vue 0 est ta source : détoure plutôt l'image dans la Bibliothèque.")
    if not v.get("file") or not (_dir(job) / v["file"]).is_file():
        raise ValueError(f"vue {v['index']} absente : rejoue-la avant de la détourer")
    return v


async def detourer_vue(job, index: int, *, via: str = "local", on_step=None) -> dict:
    """Fond retiré. `local` : masque des quatre coins d'`asset3d_qc`, gratuit et hors ligne — la vue est alors
    marquée `a_renvoyer` (son URL fal montre encore l'image d'avant). `fal` : imageutils/rembg sur un envoi du FICHIER
    courant, tarif `rembg_api_usd`."""
    import asyncio
    from PIL import Image
    from app.services import asset3d_qc, pricing
    from app.services import asset3d_service as A3
    verifier_detourage(job, index)
    info = lire_vues(job)
    v = _vue(info, index)
    p = _dir(job) / v["file"]
    if on_step:
        await on_step(f"Détourage vue {v['index']}", 40)

    if via == "fal":
        from app.services import sprite_service
        u = await sprite_service._rembg_api(await A3._upload(p))
        await asyncio.to_thread(A3._download, u, p)
        usd = float(pricing.DEFAULTS["rembg_api_usd"])
        v["url"] = u
        v.pop("a_renvoyer", None); v.pop("methode", None)
    else:
        def _local():
            masque, methode = asset3d_qc.masque_reference(p)
            im = Image.open(p).convert("RGB")
            rgba = im.convert("RGBA")
            rgba.putalpha(masque.convert("L").resize(im.size, Image.NEAREST))
            rgba.save(p, "PNG")
            return methode
        v["methode"] = await asyncio.to_thread(_local)
        v["a_renvoyer"] = True
        usd = 0.0
    v["detoure"] = via
    _ecrire(job, info)
    if on_step:
        await on_step("Complete", 100)
    return {"index": v["index"], "via": via, "usd": usd, "file": v["file"], "methode": v.get("methode")}


def verifier_tir(job) -> dict:
    """Les refus du tir, sans rien faire : la route les appelle AVANT la garde."""
    info = lire_vues(job)
    _ouvert(info)
    if not any(v.get("file") for v in info["vues"]):
        raise ValueError("aucune vue exploitable : régénère-en au moins une")
    return info


async def tirer_vues(job, on_step=None) -> dict:
    """Le moteur, sur les vues telles qu'elles sont MAINTENANT (ratées écartées, retouchées ré-envoyées)."""
    from app.services import asset3d_service as A3
    info = verifier_tir(job)
    d = _dir(job)
    gardees = [v for v in info["vues"] if v.get("file") and (d / v["file"]).is_file()]
    for v in gardees:
        if v.get("a_renvoyer") or not v.get("url"):
            v["url"] = await A3._upload(d / v["file"])
            v.pop("a_renvoyer", None)
    _ecrire(job, info)                      # les URL fraîches survivent à un échec du moteur
    payload = dict(info.get("payload") or {})
    payload.update(image_filename=info["image_filename"], engine=info["engine"], multiview=True)
    r = await A3.tirer_moteur(Path(str(job)).name, [v["url"] for v in gardees], payload,
                              [v["file"] for v in gardees], on_step, cles=[v["cle"] for v in gardees])
    info["etat"] = "tire"
    info["tire_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _ecrire(job, info)
    return r


async def preparer_depuis_images(job: str, vues: dict, payload: dict, on_step=None) -> dict:
    """Un jeu de vues bâti sur des images qui EXISTENT DÉJÀ dans la Bibliothèque — les panneaux d'une planche de la
    bible (T106, plan-moteurs-3d T7, D1). `vues` = {clé: fichier}, clés parmi front/back/left/right, la face exigée.
    Aucun appel Seedream : l'identité tenue par la bible est ce qu'on ne veut pas régénérer (les envois au stockage
    fal ne sont pas facturés). Les vues sont rangées dans l'ordre d'auteur (front, back, left, right) ; l'ordre imposé
    par un moteur est appliqué au tir par `ordonner_vues`, sur les CLÉS. Rôle « planche » : pas de rejeu, détourage
    permis."""
    import shutil
    from app.config import settings
    from app.services import asset3d_service as A3

    vues = dict(vues or {})
    inconnues = sorted(set(vues) - set(A3.VUES_CLES))
    if inconnues:
        raise ValueError(f"clé(s) de vue inconnue(s) : {', '.join(inconnues)} (attendu : {', '.join(A3.VUES_CLES)})")
    if not (1 <= len(vues) <= MAX_VUES):
        raise ValueError(f"il faut de 1 à 4 vues ; {len(vues)} donnée(s)")
    if "front" not in vues:
        raise ValueError("pas de vue de face (front) : un moteur image→3D en a besoin")
    racine = settings.images_path.resolve()
    chemins = {}
    for k, f in vues.items():
        p = settings.images_path / Path(str(f)).name
        if not p.is_file() or not str(p.resolve()).startswith(str(racine)):
            raise ValueError(f"Image not found in Library: {f!r}")
        chemins[k] = p
    engine = str(payload.get("engine") or "tripo").lower()
    if engine not in A3.ENGINES:
        raise ValueError(f"Unknown engine: {engine}")

    d = _dir(job)
    d.mkdir(parents=True, exist_ok=True)
    ordre = [k for k in A3.VUES_CLES if k in chemins]
    sortie = []
    for i, k in enumerate(ordre):
        if on_step:
            await on_step(f"Vue {k}", 10 + int(80 * (i + 1) / len(ordre)))
        shutil.copy2(chemins[k], d / f"shot_{i}.png")
        sortie.append({"index": i, "cle": k, "role": "planche", "file": f"shot_{i}.png",
                       "url": await A3._upload(chemins[k]), "prompt": None, "rejeux": 0, "detoure": None,
                       "origine": chemins[k].name})
    info = _ecrire(job, {
        "job": Path(str(job)).name, "etat": "en_attente", "engine": engine,
        "source": str(payload.get("source") or "planche"), "entity_id": payload.get("entity_id"),
        "image_filename": chemins["front"].name,
        "payload": {k: v for k, v in payload.items() if k not in ("image_filename", "entity_id", "source", "job")},
        "vues": sortie, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    if on_step:
        await on_step("Vues prêtes — à toi de juger", 100)
    return {"job": info["job"], "etat": info["etat"], "vues": len(sortie), "ratees": 0}
