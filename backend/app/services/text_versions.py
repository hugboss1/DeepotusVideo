# -*- coding: utf-8 -*-
"""Tâche #61 (plan chapitres P2, 02/10/2026) — les versions du texte des chapitres, des scènes et des scénarios.

Règle unique : `snapshot` garde l'ANCIEN texte — celui qui va disparaître — jamais le neuf. C'est ce qui permet de
revenir en arrière APRÈS avoir vu le résultat. Un texte vide, ou identique au dernier instantané, ne crée rien (dix
passes sans effet ne chassent pas l'historique utile). Élagage aux 10 derniers, comme `vector_store`.

Points d'écrasement (recomptés le 02/10) : édition du chapitre et d'une scène (« manuelle »), adaptation en scénario
(« adaptation ») et remise à zéro du scénario (« suppression ») — le scénario ENTIER est gardé, une seule version, car
ses scènes sont supprimées —, ré-import du manuscrit (« import »), retour du téléphone (« telephone », #105),
restauration elle-même (« restauration »).

Restaurer un chapitre respecte le verrou du téléphone (423) et recalcule le surlignage des entités ; un scénario ne se
restaure pas en scènes (409 : il se lit, se compare et se copie). Stdlib seule (difflib).
"""
from __future__ import annotations

import difflib
import json
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

GARDE = 10
KINDS = ("chapter", "scene", "scenario")
PASSES = ("manuelle", "adaptation", "suppression", "import", "telephone", "reecriture", "restauration",
          "import_scenario")   # tâche #64 : avant qu'un scénario importé ne remplace les scènes


def _dict(v, plein: bool = False) -> dict:
    d = {"id": v.id, "kind": v.kind, "target_id": v.target_id, "n": v.n, "passe": v.passe,
         "taille": len(v.text or ""), "apercu": (v.text or "")[:120].replace("\n", " "),
         "restaurable": v.kind != "scenario",
         "created_at": v.created_at.isoformat(timespec="milliseconds") + "Z" if v.created_at else None}
    if plein:
        d["text"] = v.text or ""
        try:
            d["meta"] = json.loads(v.meta) if v.meta else {}
        except ValueError:
            d["meta"] = {}
    return d


async def _rows(session, kind: str, target_id: str):
    from app.services.storage import TextVersion
    return (await session.execute(select(TextVersion).where(TextVersion.kind == kind, TextVersion.target_id == target_id)
                                  .order_by(TextVersion.n.desc()))).scalars().all()


async def snapshot(session, kind: str, target_id: str, ancien: str | None, passe: str, meta: dict | None = None) -> dict | None:
    """Garde `ancien` avant qu'il soit écrasé ; rend la version créée, ou None s'il n'y avait rien à garder."""
    from app.services.storage import TextVersion
    if kind not in KINDS:
        raise ValueError(f"kind inconnu: {kind}")
    ancien = ancien or ""
    if not ancien.strip():
        return None
    rows = await _rows(session, kind, target_id)
    if rows and (rows[0].text or "") == ancien:
        return None
    v = TextVersion(id=str(uuid4()), kind=kind, target_id=target_id, n=(rows[0].n + 1) if rows else 1,
                    passe=passe if passe in PASSES else "manuelle", text=ancien,
                    meta=json.dumps(meta or {}, ensure_ascii=False), created_at=datetime.utcnow())
    session.add(v)
    for vieux in rows[GARDE - 1:]:
        await session.delete(vieux)
    await session.commit()
    return _dict(v)


def texte_scenario(scenes) -> str:
    """Le scénario d'un chapitre en un texte : chaque scène, sa ligne de tête puis son texte, dans l'ordre."""
    return "\n\n".join(f"{s.slugline or ''}\n\n{s.fountain_text or ''}".strip() for s in sorted(scenes, key=lambda x: x.idx))


async def _scenes(session, chapter_id: str):
    from app.services.storage import Scene
    return (await session.execute(select(Scene).where(Scene.chapter_id == chapter_id).order_by(Scene.idx.asc()))).scalars().all()


async def snapshot_scenario(session, chapter_id: str, passe: str) -> dict | None:
    """Avant que les scènes d'un chapitre ne soient supprimées : le scénario ENTIER, une version."""
    return await snapshot(session, "scenario", chapter_id, texte_scenario(await _scenes(session, chapter_id)), passe)


async def historique(session, kind: str, target_id: str) -> list[dict]:
    """Du plus récent au plus ancien, SANS le texte (aperçu + taille)."""
    return [_dict(v) for v in await _rows(session, kind, target_id)]


async def historique_chapitre(session, chapter_id: str) -> list[dict]:
    """Ce que le tiroir d'un chapitre montre : son texte, son scénario, et ses scènes actuelles — du plus récent."""
    lignes = list(await _rows(session, "chapter", chapter_id)) + list(await _rows(session, "scenario", chapter_id))
    slug = {}
    for s in await _scenes(session, chapter_id):
        for v in await _rows(session, "scene", s.id):
            lignes.append(v)
            slug[v.id] = s.slugline
    # tri sur l'horodatage COMPLET (une seconde tronquée laissait l'ordre au hasard entre texte, scénario et scènes)
    lignes.sort(key=lambda v: v.created_at or datetime.min, reverse=True)
    return [{**_dict(v), **({"slugline": slug[v.id]} if v.id in slug else {})} for v in lignes]


async def lire(session, version_id: str) -> dict | None:
    from app.services.storage import TextVersion
    v = await session.get(TextVersion, version_id)
    return _dict(v, plein=True) if v else None


async def courant(session, kind: str, target_id: str) -> str:
    """Le texte actuel de la cible (ce à quoi une version se compare)."""
    from app.services.storage import Chapter, Scene
    if kind == "chapter":
        c = await session.get(Chapter, target_id)
        return (c.script_text or "") if c else ""
    if kind == "scene":
        s = await session.get(Scene, target_id)
        return (s.fountain_text or "") if s else ""
    return texte_scenario(await _scenes(session, target_id))


def diff(ancien: str, neuf: str) -> dict:
    """Comparaison LIGNE À LIGNE, en paires alignées ; `None` d'un côté = ligne absente de ce côté.
    `~` = modifiée, `+` / `-` = ajoutée / supprimée."""
    a, b = (ancien or "").splitlines(), (neuf or "").splitlines()
    lignes: list[dict] = []
    ajout = retire = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            lignes += [{"op": "=", "a": a[i1 + k], "b": b[j1 + k]} for k in range(i2 - i1)]
        elif op == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                ga = a[i1 + k] if i1 + k < i2 else None
                gb = b[j1 + k] if j1 + k < j2 else None
                lignes.append({"op": "~", "a": ga, "b": gb})
                retire += ga is not None
                ajout += gb is not None
        elif op == "delete":
            lignes += [{"op": "-", "a": a[k], "b": None} for k in range(i1, i2)]
            retire += i2 - i1
        else:
            lignes += [{"op": "+", "a": None, "b": b[k]} for k in range(j1, j2)]
            ajout += j2 - j1
    return {"lignes": lignes, "ajoutees": ajout, "supprimees": retire, "identiques": sum(1 for x in lignes if x["op"] == "=")}


async def restaurer(session, version_id: str) -> dict | None:
    """Réécrit la cible avec cette version — APRÈS avoir gardé le texte courant (« restauration »). Rien n'est perdu,
    dans les deux sens. None : version (ou cible) inconnue. 409 : un scénario. 423 : chapitre emporté par le téléphone."""
    from app.services.storage import Chapter, Scene, TextVersion
    from app.services import sync_verrou
    v = await session.get(TextVersion, version_id)
    if not v:
        return None
    if v.kind == "scenario":
        raise HTTPException(409, "Un scénario gardé ne se restaure pas en scènes : copiez son texte (ou ré-adaptez).")
    cible = await session.get(Chapter if v.kind == "chapter" else Scene, v.target_id)
    if not cible:
        return None
    if v.kind == "chapter":
        await sync_verrou.garde(v.target_id)
    await snapshot(session, v.kind, v.target_id, await courant(session, v.kind, v.target_id), "restauration",
                   {"depuis": v.id, "n": v.n})
    if v.kind == "chapter":
        cible.script_text = v.text or ""
        cible.spans = await sync_verrou._spans(session, cible.script_text)
    else:
        cible.fountain_text = v.text or ""
    cible.updated_at = datetime.utcnow()
    await session.commit()
    return {"kind": v.kind, "target_id": v.target_id, "text": v.text or ""}
