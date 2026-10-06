# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T11-T12, D3) — recherche de sons par DESCRIPTION et par
SIMILARITÉ (index CLAP).

Le backend ne fait JAMAIS tourner le modèle : le python embarqué est stdlib +
Pillow, sans numpy ni torch. Il ne garde que des VECTEURS et fait des produits
scalaires — mesuré dans test_sound_search_gate : 606 × 512 en Python pur, une
requête sous 60 ms, index relu sous 1,5 s. C'est tenable ; le modèle, non.

Table de décision (mesures du 06/10/2026, ne pas la refaire de mémoire) :

| Voie                        | Coût            | Exige                      | Verdict    |
|-----------------------------|-----------------|----------------------------|------------|
| modèle DANS le backend      | 0 $             | torch + numpy embarqués    | IMPOSSIBLE |
| service local « Clapbox »   | 0 $             | un processus Python à part | RETENUE (défaut) |
| endpoint distant (HF dédié) | à l'heure de machine allumée | une URL + une clé | POSSIBLE, même façade |

Détail des mesures du 06/10 : la fiche `laion/clap-htsat-unfused` (API
huggingface.co) porte `pipeline_tag: feature-extraction`,
`library_name: transformers` et un seul `inferenceProviderMapping` —
`hf-inference` au statut « error » : pas de serverless qui marche (le 03/09 il
n'y en avait aucun). fal ne sert pas d'embeddings audio-texte. Le dossier audio
réel compte 15 sons ; le catalogue livré, 606 — c'est lui qui borne la mesure.

Les deux voies ouvertes passent par le même contrat HTTP (le nôtre) :
    GET  /health          → {"ok": true, "model": "...", "dim": 512}
    POST /embed/text      {"texts": ["porte qui grince"]}  → {"dim","model","vectors":[[…]]}
    POST /embed/audio     multipart `files`                → {"dim","model","vectors":[[…]]}
L'implémentation de référence du service local est dans `tools/clapbox/`
(son propre environnement, ses propres poids — jamais dans l'application).

Absence = repli PROPRE, jamais une erreur : `resolve_embedder()` rend "" et le
tiroir Sons affiche la raison. Patron repris de `voice_providers.py`
(détection cachée, provider résolu, `available()`)."""
from __future__ import annotations

import base64
import json
import os
import time
from array import array
from operator import mul
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings

CLAPBOX_DEFAULT_URL = "http://127.0.0.1:17494"
INDEX_NAME = "_clap_index.json"
DEFAULT_DIM = 512          # fiche laion/clap-htsat-unfused ; /health fait foi
BYTEORDER = "little"       # array('f') est natif : un index d'une autre machine est rejeté


def clapbox_url() -> str:
    return (getattr(settings, "CLAPBOX_URL", "") or "").strip().rstrip("/") or CLAPBOX_DEFAULT_URL


def remote_url() -> str:
    return (getattr(settings, "CLAP_REMOTE_URL", "") or "").strip().rstrip("/")


def _reach(url: str, timeout: float = 2.0) -> bool:      # seam (le banc le remplace)
    try:
        return httpx.get(url + "/health", timeout=timeout).status_code == 200
    except Exception:  # noqa: BLE001
        return False


_reach_cache = {"t": 0.0, "ok": False}


def clapbox_reachable(timeout: float = 2.0, ttl: float = 5.0) -> bool:
    """Comme voicebox_reachable : un ping au plus toutes les `ttl` secondes —
    le tiroir Sons interroge le statut à chaque ouverture."""
    now = time.monotonic()
    if ttl > 0 and _reach_cache["t"] and now - _reach_cache["t"] < ttl:
        return _reach_cache["ok"]
    ok = _reach(clapbox_url(), timeout)
    _reach_cache.update(t=now, ok=ok)
    return ok


def resolve_embedder() -> str:
    """« clapbox » | « remote » | « » (aucun). Le local d'abord : gratuit."""
    if clapbox_reachable():
        return "clapbox"
    if remote_url():
        return "remote"
    return ""


def embedder_url(provider: str | None = None) -> str:
    p = provider or resolve_embedder()
    return clapbox_url() if p == "clapbox" else remote_url()


def status() -> dict:
    """Ce que le tiroir Sons affiche : prête ou non, et POURQUOI non."""
    prov = resolve_embedder()
    ix = Index.load()
    return {"ready": bool(prov), "provider": prov, "model": ix.model, "dim": ix.dim,
            "indexed": ix.count(),
            "hint": "" if prov else
                    ("Recherche par description indisponible : lance le service local Clapbox "
                     f"({clapbox_url()}, voir tools/clapbox/) ou renseigne CLAP_REMOTE_URL "
                     "(et CLAP_REMOTE_KEY) dans le .env de l'application.")}


def available() -> list[dict]:
    return [{"id": "clapbox", "label": "Clapbox (local, gratuit)", "ready": clapbox_reachable()},
            {"id": "remote", "label": "Endpoint CLAP distant", "ready": bool(remote_url())}]


# ───────────────────────────── vecteurs, en stdlib ──────────────────────────

def norm(v) -> float:
    return sum(x * x for x in v) ** 0.5


def unit(v, dim: int) -> list[float]:
    if len(v) != dim:
        raise ValueError(f"vecteur de dimension {len(v)}, attendu {dim}")
    n = norm(v)
    if not n or n != n:                      # 0 ou NaN
        raise ValueError("vecteur nul ou non fini — rien à comparer")
    return [float(x) / n for x in v]


def _enc(v: list[float]) -> str:
    return base64.b64encode(array("f", v).tobytes()).decode("ascii")


def _dec(s: str, dim: int) -> list[float]:
    a = array("f")
    a.frombytes(base64.b64decode(s))
    if len(a) != dim:
        raise ValueError(f"vecteur encodé de dimension {len(a)}, attendu {dim}")
    return list(a)


class Index:
    """L'index des sons : un vecteur unitaire par fichier, plus la SIGNATURE
    du fichier au moment du calcul (« mtime:taille ») pour ne réindexer que ce
    qui a bougé. Format : un JSON, des vecteurs en base64 d'array('f') — relu
    en une passe, sans dépendance."""

    def __init__(self, dim: int = DEFAULT_DIM, model: str = "", provider: str = ""):
        self.dim, self.model, self.provider = int(dim), model, provider
        self._v: dict[str, list[float]] = {}
        self._s: dict[str, str] = {}

    @staticmethod
    def path() -> Path:
        from app.services import sfx_service
        return sfx_service._audio_dir() / INDEX_NAME

    def put(self, name: str, vec, sig: str = "") -> None:
        self._v[str(name)] = unit(vec, self.dim)
        self._s[str(name)] = str(sig)

    def drop(self, name: str) -> None:
        self._v.pop(str(name), None)
        self._s.pop(str(name), None)

    def get(self, name: str) -> list[float] | None:
        return self._v.get(str(name))

    def sig(self, name: str) -> str:
        return self._s.get(str(name), "")

    def count(self) -> int:
        return len(self._v)

    def names(self) -> list[str]:
        return list(self._v)

    def save(self) -> Path:
        p = self.path()
        doc = {"dim": self.dim, "model": self.model, "provider": self.provider,
               "byteorder": BYTEORDER,
               "items": {n: {"v": _enc(self._v[n]), "sig": self._s.get(n, "")} for n in self._v}}
        tmp = p.with_name(p.name + ".part")
        tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
        return p

    @classmethod
    def load(cls, dim: int | None = None) -> "Index":
        """Un index absent, illisible, d'une autre dimension ou d'un autre
        boutisme rend un index VIDE — jamais une exception : la recherche se
        contente alors de dire qu'elle n'a rien."""
        p = cls.path()
        if not p.is_file():
            return cls(dim or DEFAULT_DIM)
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            ix = cls(int(d.get("dim") or DEFAULT_DIM), d.get("model") or "", d.get("provider") or "")
            if d.get("byteorder") not in (None, BYTEORDER):
                logger.warning("index CLAP d'un autre boutisme — ignoré")
                return cls(dim or DEFAULT_DIM)
            if dim is not None and ix.dim != int(dim):
                logger.warning(f"index CLAP en dim {ix.dim}, attendu {dim} — ignoré")
                return cls(int(dim))
            for n, e in (d.get("items") or {}).items():
                try:
                    ix._v[n] = _dec(e["v"], ix.dim)
                    ix._s[n] = e.get("sig", "")
                except Exception:  # noqa: BLE001 — un item abîmé ne coûte que lui
                    continue
            return ix
        except Exception as e:  # noqa: BLE001
            logger.warning(f"index CLAP illisible ({e}) — reparti de zéro")
            return cls(dim or DEFAULT_DIM)

    def nearest(self, q, k: int = 8, exclude: str | None = None) -> list[tuple[str, float]]:
        """Cosinus : tout est unitaire, donc un produit scalaire suffit.
        `map(mul, …)` plutôt qu'une boucle : c'est ce qui tient le budget de
        60 ms sur 606 × 512 sans numpy (mesuré au banc)."""
        qn = unit(q, self.dim)
        out = [(n, sum(map(mul, qn, v))) for n, v in self._v.items() if n != exclude]
        out.sort(key=lambda t: -t[1])
        return out[:max(1, int(k))]


# ─────────────────── indexer, chercher, comparer (T103 / plan T12) ───────────────────

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus"}
BATCH_AUDIO = 8            # multipart raisonnable pour un service local
MAX_TEXT = 400


class SearchUnavailable(RuntimeError):
    """Ni Clapbox ni endpoint distant (ou un service qui répond mal) : la
    recherche par description ne peut pas avoir lieu. La similarité, elle, se
    sert de l'index déjà écrit."""


def _headers(prov: str) -> dict:
    # la clé ne part QU'À l'endpoint distant : le service local n'en a pas
    # besoin, et une clé qui voyage pour rien est une clé qui fuit
    key = (getattr(settings, "CLAP_REMOTE_KEY", "") or "").strip()
    return {"Authorization": f"Bearer {key}"} if key and prov == "remote" else {}


async def _post(path: str, **kw) -> dict:
    prov = resolve_embedder()
    if not prov:
        raise SearchUnavailable(status()["hint"])
    url = embedder_url(prov) + path
    try:
        async with httpx.AsyncClient(timeout=300.0) as c:
            r = await c.post(url, headers=_headers(prov), **kw)
    except httpx.HTTPError as e:
        raise SearchUnavailable(f"service d'embeddings ({prov}) injoignable : {e}") from e
    if r.status_code != 200:
        # le message du service, LU : un corps JSON {"error"|"detail": …} est décodé (ses accents arrivent
        # échappés en \uXXXX dans le texte brut — mesuré au banc du serveur de référence), sinon le texte brut
        try:
            j = r.json()
            msg = str((j.get("error") or j.get("detail")) if isinstance(j, dict) else j)
        except ValueError:
            msg = r.text
        raise SearchUnavailable(f"service d'embeddings ({prov}) : HTTP {r.status_code} — {msg[:200]}")
    return r.json()


async def _embed_text(texts: list[str]) -> tuple[list[list[float]], int, str]:   # seam
    d = await _post("/embed/text", json={"texts": [t[:MAX_TEXT] for t in texts]})
    return d["vectors"], int(d.get("dim") or DEFAULT_DIM), str(d.get("model") or "")


async def _embed_audio(paths: list[Path]) -> tuple[list[list[float]], int, str]:  # seam
    files = [("files", (p.name, p.read_bytes(), "application/octet-stream")) for p in paths]
    d = await _post("/embed/audio", files=files)
    return d["vectors"], int(d.get("dim") or DEFAULT_DIM), str(d.get("model") or "")


def _sig(p: Path) -> str:
    st = p.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


async def reindex(force: bool = False) -> dict:
    """Indexe ce qui manque ou a bougé, rien d'autre : un son déjà vu avec la
    même signature ne repasse pas par le service. `force` repart d'un index
    VIDE — c'est la seule sortie après un changement de modèle (une autre
    dimension ne se mélange pas à l'ancienne). Rend {indexed, skipped,
    dropped, dim, model, provider, total}."""
    from app.services import sfx_service
    folder = sfx_service._audio_dir()
    present = sorted(p for p in folder.iterdir()
                     if p.is_file() and p.suffix.lower() in AUDIO_EXT)
    ix = Index() if force else Index.load()
    dropped = [n for n in ix.names() if not (folder / n).is_file()]
    for n in dropped:
        ix.drop(n)
    todo = [p for p in present if force or ix.get(p.name) is None or ix.sig(p.name) != _sig(p)]
    done = 0
    for i in range(0, len(todo), BATCH_AUDIO):
        chunk = todo[i:i + BATCH_AUDIO]
        vecs, dim, model = await _embed_audio(chunk)
        if ix.count() == 0 and (ix.dim != dim or ix.model != model):
            ix = Index(dim=dim, model=model, provider=resolve_embedder())
        elif dim != ix.dim:
            raise SearchUnavailable(
                f"le service rend des vecteurs de dimension {dim}, l'index est en {ix.dim} — "
                "réindexe tout (« tout réindexer ») après un changement de modèle.")
        for p, v in zip(chunk, vecs):
            try:
                ix.put(p.name, v, sig=_sig(p))
            except ValueError as e:
                logger.warning(f"index CLAP : {p.name} ignoré ({e})")
                continue
            done += 1
    ix.provider = resolve_embedder() or ix.provider
    ix.save()
    logger.info(f"index CLAP : {done} indexés, {len(present) - len(todo)} inchangés, "
                f"{len(dropped)} retirés ({ix.count()} au total)")
    return {"indexed": done, "skipped": len(present) - len(todo), "dropped": dropped,
            "dim": ix.dim, "model": ix.model, "provider": ix.provider, "total": ix.count()}


def _rows(pairs) -> list[dict]:
    from app.services import sfx_service
    meta = sfx_service.load_meta()
    out = []
    for n, s in pairs:
        m = meta.get(n) or {}
        out.append({"name": n, "url": f"/api/audio/{n}", "score": round(float(s), 4),
                    "kind": m.get("kind") or sfx_service.classify_kind(n),
                    "tags": m.get("tags") or []})
    return out


async def search(query: str, k: int = 12) -> list[dict]:
    """Description libre → sons. Coûte un embedding de texte (une phrase)."""
    q = (query or "").strip()
    if not q:
        return []
    ix = Index.load()
    if ix.count() == 0:
        return []
    vecs, dim, _model = await _embed_text([q])
    if dim != ix.dim:
        raise SearchUnavailable(f"le service rend du {dim}, l'index est en {ix.dim} — réindexe tout.")
    return _rows(ix.nearest(vecs[0], k))


async def similar(filename: str, k: int = 8) -> list[dict]:
    """« Comme celui-ci » : PUREMENT local, aucun appel — le vecteur est déjà
    dans l'index. Un son non indexé rend une liste vide, pas une erreur."""
    name = Path(str(filename)).name
    ix = Index.load()
    v = ix.get(name)
    if v is None:
        return []
    return _rows(ix.nearest(v, k, exclude=name))
