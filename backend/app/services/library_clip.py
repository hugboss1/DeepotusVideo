# -*- coding: utf-8 -*-
"""Tâche #82 PR D (04/10/2026, plan-library T12-T13) — CLIP en LOCAL : chercher par le SENS, et « images semblables ».

Décisions de l'utilisateur (04/10) : le moteur « clip » du sélecteur ; version LÉGÈRE (≈ 186 Mo, accord donné) : CLIP
ViT-B/32 QUANTIFIÉ en ONNX (Hugging Face Xenova/clip-vit-base-patch32, poids d'OpenAI, licence MIT), exécuté sur le
processeur par onnxruntime ; installé À PART, dans <données>/clip (roues décompressées : le Python embarqué n'a pas pip,
et le Python de l'application n'est pas touché) ; rien ne sort du PC pour chercher.
Le plan voulait un service « Clipbox » séparé (inexistant) avec torch + CUDA (≈ 3,5 Go), ou un chemin distant qui aurait
envoyé toutes les images. Mesuré le 04/10 : onnxruntime-gpu pèse 160 Mo ET exige CUDA/cuDNN (plusieurs Go) — le gain
ne vaut pas le poids pour ≈ 1000 images.
Chaque téléchargement a sa version / révision FIGÉE et son empreinte vérifiée (sha256 PyPI, oid LFS Hugging Face).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

from loguru import logger

from app.config import settings, SSL_VERIFY

REVISION = "d15189d7028b43f1d3e65039190477f6af591c2a"
DEPOT = "Xenova/clip-vit-base-patch32"
ROUES = [  # (nom, url, octets, sha256) — relevés sur pypi.org le 04/10/2026
    ("onnxruntime-1.30.0-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/3c/dd/c57c529dbc6dd55eca24b12cfbeab1b6a690de72083824eca689085f55b0/onnxruntime-1.30.0-cp313-cp313-win_amd64.whl",
     14311378, "4b63041bd623a9a9ac5e353948436c6fa7f43edd12d6b4a4ebc340bca959ba93"),
    ("numpy-2.5.3-cp313-cp313-win_amd64.whl",
     "https://files.pythonhosted.org/packages/f3/ec/100f2b1794ede74a9b3d7ec6b9736927f56713414c1dfe19ab6c383494bf/numpy-2.5.3-cp313-cp313-win_amd64.whl",
     12560965, "71cad2b2a7451ab79d8f5e71b453485b6775963d5cf794179144a7463fe6e8ec"),
    ("tokenizers-0.23.2-cp310-abi3-win_amd64.whl",
     "https://files.pythonhosted.org/packages/db/f7/0a69ac6b82dbccf3f71add938a161c497952749294b8dd6dfe03a819dc40/tokenizers-0.23.2-cp310-abi3-win_amd64.whl",
     2863236, "2e96f5699d5249c9c64aa8412e044f727aae3a4098cf830f9901ec1afc361cde"),
]
MODELES = [  # (chemin dans le dépôt, octets, sha256 ou None pour un petit fichier hors LFS)
    ("onnx/vision_model_quantized.onnx", 89117001, "583fd1110a514667812fee7d684952aaf82a99b959760c8d7dca7e0ab9839299"),
    ("onnx/text_model_quantized.onnx", 64504507, "73baab855d406190da9faa498cfedf65f15cf309f4cc7385b7b032e6d08e5c3a"),
    ("tokenizer.json", 2224119, None),
    ("preprocessor_config.json", 520, None),
]
TOTAL_OCTETS = sum(r[2] for r in ROUES) + sum(m[1] for m in MODELES)
INSTALL = {"en_cours": False, "fait": 0, "total": TOTAL_OCTETS, "etape": "", "erreur": ""}
INDEX = {"en_cours": False, "faits": 0, "total": 0, "erreur": ""}
_TACHES: set = set()
_MOTEUR: dict = {}


def dossier() -> Path:
    env = os.environ.get("DEEPOTUS_CLIP_DIR", "").strip()
    return Path(env) if env else settings.images_path.parent.parent / "clip"


def _site() -> Path:
    return dossier() / "site"


def _modeles() -> Path:
    return dossier() / "modeles"


def installe() -> bool:
    return (dossier() / "installe.json").is_file()


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


async def _telecharger(client, url: str, dest: Path, octets: int, sha: str | None) -> None:
    """Télécharge dans un .part, VÉRIFIE taille et empreinte, puis renomme ; un fichier déjà bon n'est pas repris."""
    if dest.is_file() and dest.stat().st_size == octets and (sha is None or _sha(dest) == sha):
        INSTALL["fait"] += octets
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    n = 0
    async with client.stream("GET", url, follow_redirects=True) as r:
        if r.status_code != 200:
            raise RuntimeError(f"{url} : HTTP {r.status_code}")
        with open(part, "wb") as fh:
            async for bloc in r.aiter_bytes(1 << 20):
                fh.write(bloc)
                n += len(bloc)
                INSTALL["fait"] += len(bloc)
    if n != octets:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"{dest.name} : {n} octets reçus, {octets} attendus")
    if sha is not None and _sha(part) != sha:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"{dest.name} : empreinte sha256 différente — fichier refusé")
    os.replace(part, dest)


async def installer() -> None:
    """Télécharge et installe roues + modèles dans dossier() ; l'état se suit dans INSTALL."""
    import httpx
    INSTALL.update(en_cours=True, fait=0, etape="", erreur="")
    try:
        cache = dossier() / "telechargements"
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=120.0) as client:
            for nom, url, octets, sha in ROUES:
                INSTALL["etape"] = nom
                await _telecharger(client, url, cache / nom, octets, sha)
            for chemin, octets, sha in MODELES:
                INSTALL["etape"] = chemin
                url = f"https://huggingface.co/{DEPOT}/resolve/{REVISION}/{chemin}"
                await _telecharger(client, url, _modeles() / Path(chemin).name, octets, sha)
        INSTALL["etape"] = "décompression"
        site = _site()
        if site.exists():
            shutil.rmtree(site)
        site.mkdir(parents=True)
        for nom, *_ in ROUES:
            with zipfile.ZipFile(cache / nom) as z:
                z.extractall(site)
        (dossier() / "installe.json").write_text(json.dumps({"revision": REVISION, "roues": [r[0] for r in ROUES],
                                                             "modeles": [m[0] for m in MODELES]}, indent=1), encoding="utf-8")
        shutil.rmtree(cache, ignore_errors=True)
        INSTALL["etape"] = "installé"
    except Exception as e:  # noqa: BLE001
        INSTALL["erreur"] = str(e)[:300]
        logger.warning(f"library_clip.installer : {e}")
    finally:
        INSTALL["en_cours"] = False


def _fond(coro_fn, etat: dict) -> bool:
    if etat["en_cours"]:
        return False
    etat["en_cours"] = True

    async def _go():
        try:
            await coro_fn()
        finally:
            etat["en_cours"] = False
    t = asyncio.get_running_loop().create_task(_go())
    _TACHES.add(t)
    t.add_done_callback(_TACHES.discard)
    return True


def lancer_installation() -> bool:
    return _fond(installer, INSTALL)


# ----- le moteur : vecteurs d'images et de textes (processeur) -----

MOYENNE, ECART = (0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)   # preprocessor_config.json


def _moteur():
    """Charge onnxruntime / numpy / tokenizers DEPUIS le dossier de CLIP, et les deux modèles (une fois)."""
    if _MOTEUR:
        return _MOTEUR
    if not installe():
        raise RuntimeError("CLIP n'est pas installé.")
    site = str(_site())
    if site not in sys.path:
        sys.path.append(site)
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    _MOTEUR.update(np=np, vision=ort.InferenceSession(str(_modeles() / "vision_model_quantized.onnx"), opts, providers=["CPUExecutionProvider"]),
                   texte=ort.InferenceSession(str(_modeles() / "text_model_quantized.onnx"), opts, providers=["CPUExecutionProvider"]),
                   tok=Tokenizer.from_file(str(_modeles() / "tokenizer.json")))
    return _MOTEUR


def _pixels(chemin: Path):
    """Le prétraitement de CLIP : plus petit côté à 224 (bicubique), recadrage central 224, /255, normalisation."""
    from PIL import Image
    np = _moteur()["np"]
    with Image.open(chemin) as im:
        im = im.convert("RGB")
        w, h = im.size
        k = 224 / min(w, h)
        im = im.resize((max(224, round(w * k)), max(224, round(h * k))), Image.BICUBIC)
        w, h = im.size
        g, t = (w - 224) // 2, (h - 224) // 2
        im = im.crop((g, t, g + 224, t + 224))
        a = np.asarray(im, dtype=np.float32) / 255.0
    a = (a - np.array(MOYENNE, dtype=np.float32)) / np.array(ECART, dtype=np.float32)
    return a.transpose(2, 0, 1)[None, ...]


def _norme(v):
    np = _moteur()["np"]
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)


def vecteur_image(chemin: Path):
    m = _moteur()
    return _norme(m["vision"].run(["image_embeds"], {"pixel_values": _pixels(chemin)})[0][0])


def vecteur_texte(texte: str):
    m = _moteur()
    ids = m["tok"].encode(str(texte or "")).ids[:77]
    return _norme(m["texte"].run(["text_embeds"], {"input_ids": m["np"].array([ids], dtype=m["np"].int64)})[0][0])


# ----- l'index : un vecteur par image, refait quand le fichier change -----

def _fichiers_index() -> tuple[Path, Path]:
    return dossier() / "index.npy", dossier() / "index.json"


def _lire_index():
    np = _moteur()["np"]
    fv, fj = _fichiers_index()
    if not fv.is_file() or not fj.is_file():
        return [], {}, np.zeros((0, 512), dtype=np.float32)
    meta = json.loads(fj.read_text(encoding="utf-8"))
    return meta.get("noms") or [], meta.get("mtimes") or {}, np.load(fv)


def _images() -> list[Path]:
    from app.services.library_index import _IMAGE_EXTS
    d = settings.images_path
    return sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_EXTS) if d.is_dir() else []


def a_indexer() -> list[str]:
    """Les images absentes de l'index ou modifiées depuis (mtime)."""
    if not installe():
        return []
    noms, mt, _v = _lire_index()
    connus = set(noms)
    return [p.name for p in _images() if p.name not in connus or mt.get(p.name) != p.stat().st_mtime]


def indexer_sync() -> None:
    """Met l'index à jour : ajoute / refait les images nouvelles ou modifiées, retire celles qui ont disparu."""
    np = _moteur()["np"]
    noms, mt, V = _lire_index()
    presentes = {p.name: p for p in _images()}
    garde = [i for i, n in enumerate(noms) if n in presentes and mt.get(n) == presentes[n].stat().st_mtime]
    noms2 = [noms[i] for i in garde]
    V2 = [V[i] for i in garde]
    mt2 = {n: mt[n] for n in noms2}
    deja = set(noms2)
    a_faire = [n for n in presentes if n not in deja]
    INDEX.update(faits=0, total=len(a_faire), erreur="")
    for n in a_faire:
        try:
            V2.append(vecteur_image(presentes[n]).astype(np.float32))
            noms2.append(n)
            mt2[n] = presentes[n].stat().st_mtime
        except Exception as e:  # noqa: BLE001 — une image illisible n'arrête pas l'index
            logger.warning(f"library_clip.indexer : {n} ignorée ({e})")
        INDEX["faits"] += 1
    fv, fj = _fichiers_index()
    np.save(fv, np.array(V2, dtype=np.float32).reshape(-1, 512))
    fj.write_text(json.dumps({"revision": REVISION, "noms": noms2, "mtimes": mt2}), encoding="utf-8")


async def _indexer_async():
    try:
        await asyncio.to_thread(indexer_sync)
    except Exception as e:  # noqa: BLE001
        INDEX["erreur"] = str(e)[:300]


def lancer_index() -> bool:
    return _fond(_indexer_async, INDEX)


def _classer(q, exclure: str | None = None, n: int = 60, seuil: float = 0.0) -> list[dict]:
    np = _moteur()["np"]
    noms, _mt, V = _lire_index()
    if not noms:
        return []
    s = V @ q
    out = []
    for i in np.argsort(-s):
        if noms[i] == exclure:
            continue
        if float(s[i]) < seuil:
            break
        out.append({"filename": noms[i], "score": round(float(s[i]), 4)})
        if len(out) >= n:
            break
    return out


#: MESURÉ (04/10) sur des images unies : un texte sans rapport (« a cat ») donne ≈ 0,21 — les scores de CLIP ne se
#: lisent qu'en RELATIF ; le plancher écarte le pur bruit, l'ordre fait le reste. CLIP comprend l'ANGLAIS (« une image
#: rouge » classait mal) : l'écran le dit.
SEUIL_TEXTE = 0.20


def chercher(q: str, n: int = 60) -> dict:
    """Les images les plus PROCHES du texte (cosinus), au-dessus d'un seuil qui écarte le bruit de fond de CLIP."""
    t = str(q or "").strip()
    if not t:
        return {"q": q, "moteur": "clip", "resultats": [], "n": 0}
    r = _classer(vecteur_texte(t), n=n, seuil=SEUIL_TEXTE)
    return {"q": q, "moteur": "clip", "resultats": [{**x, "champs": ["sens"], "extrait": ""} for x in r], "n": len(r)}


def semblables(nom: str, n: int = 24) -> list[dict]:
    """Les images les plus proches d'une image (elle exclue) ; son vecteur vient de l'index, sinon il est calculé."""
    noms, _mt, V = _lire_index()
    q = V[noms.index(nom)] if nom in noms else vecteur_image(settings.images_path / nom)
    return _classer(q, exclure=nom, n=n)


def etat() -> dict:
    ok = installe()
    n_index, reste = 0, 0
    if ok:
        try:
            n_index, reste = len(_lire_index()[0]), len(a_indexer())
        except Exception:  # noqa: BLE001
            pass
    return {"installe": ok, "octets": TOTAL_OCTETS, "installation": dict(INSTALL), "index": dict(INDEX), "indexees": n_index,
            "a_indexer": reste, "modele": f"CLIP ViT-B/32 quantifié ({DEPOT})", "dossier": str(dossier())}
