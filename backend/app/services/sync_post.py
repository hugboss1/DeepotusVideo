# -*- coding: utf-8 -*-
"""t322 (Compagnon M5, 26/11/2026) — un contenu neuf né d'une inspiration SUR LE TÉLÉPHONE, remis au PC en brouillon.

Spec jumelle §4, spec mère §7.4 (t313) : le téléphone a extrait la matière, proposé les angles et rédigé le post ; le PC
REJOUE les gardes avant d'écrire quoi que ce soit, comme `inspiration.brouillon` :
  · suite de 12 mots consécutifs repris du texte capté (`reference` = texte capté + transcription de l'image par la
    vision, exactement `capteReference` du téléphone) ;
  · mots interdits de l'espace (ceux du PC, la source de vérité) ;
  · la source (lien, @compte) ne se publie pas ;
  · le visuel, s'il y en a un, est une image de la Bibliothèque (déposée avant par /api/sync/depot) et n'est JAMAIS
    l'image captée (même sha256). Visuel pas encore arrivé : 409 « reessayer » (nouvel essai à la synchro suivante).
Puis `routes.create_scheduled_post` (brouillon, demain 9 h, l'espace du post et les canaux de son projet actif ; les règles
du client — `a_valider` chez un client `valide_par_client` — jouent quand on programme, t309). La source va dans la recette
du visuel et dans le registre du téléphone de l'espace, JAMAIS dans un champ publiable ; le texte capté n'est pas gardé.
Idempotent : l'identifiant de l'élément de file, préfixé par l'appareil du JETON, est rangé avec l'empreinte du corps
(`telephone_posts.json` de l'espace) — renvoi identique : « deja » avec le même post ; même id, autre corps : conflit.
"""
import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone

from loguru import logger

from app import config
from app.services import espaces as _es, inspiration as INS, inspiration_garde as G

FICHIER = "telephone_posts.json"
MAX_REFERENCE = 40000
MAX_RECUS = 2000
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_verrou = asyncio.Lock()


class RefusPost(ValueError):
    """`statut` HTTP (400 forme, 404 espace, 409 garde, conflit ou visuel en route) et `code` du refus."""

    def __init__(self, message: str, code: str, statut: int = 409, garde: dict | None = None):
        super().__init__(message)
        self.code, self.statut, self.garde = code, statut, garde


def _texte(v, n: int) -> str:
    return str(v or "").strip()[:n]


def _empreinte(corps: dict) -> str:
    return hashlib.sha256(json.dumps(corps, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:32]


def _lire(eid: str) -> dict:
    f = _es.chemin(eid, FICHIER)
    try:
        v = json.loads(f.read_text(encoding="utf-8"))
        return v if isinstance(v, dict) else {}
    except FileNotFoundError:
        return {}
    except (ValueError, UnicodeDecodeError):
        f.replace(f.with_name(f"{FICHIER}.illisible-{datetime.now():%Y%m%d-%H%M%S}"))   # mis de côté, jamais écrasé
        return {}


def _forme(corps) -> dict:
    if not isinstance(corps, dict):
        raise RefusPost("corps illisible (objet attendu)", "forme", 400)
    ident = str(corps.get("id") or "")
    if not _ID.match(ident):
        raise RefusPost("identifiant d'élément invalide", "forme", 400)
    post = corps.get("post") if isinstance(corps.get("post"), dict) else None
    ins = corps.get("inspiration") if isinstance(corps.get("inspiration"), dict) else None
    if post is None or ins is None:
        raise RefusPost("post et inspiration exigés", "forme", 400)
    titre = _texte(post.get("title"), 200)
    if not titre:
        raise RefusPost("Le titre est vide.", "titre", 400)
    ref = corps.get("reference")
    if not isinstance(ref, str) or len(ref) > MAX_REFERENCE:
        raise RefusPost("texte de référence de la garde exigé (texte capté et transcription de l'image)", "forme", 400)
    cap = str(ins.get("capture_sha256") or "").lower()
    if not _SHA.match(cap):
        raise RefusPost("empreinte de la capture exigée", "forme", 400)
    v = corps.get("visuel")
    nom = _texte(v.get("nom"), 200) or None if isinstance(v, dict) else None
    src = ins.get("source") if isinstance(ins.get("source"), dict) else {}
    return {"id": ident, "eid": str(post.get("espace_id") or ""), "titre": titre, "accroche": _texte(post.get("hook"), 1000),
            "legende": str(post.get("caption") or "").strip()[:5000], "reference": ref, "capture_sha256": cap,
            "visuel": nom, "source": {"libelle": _texte(src.get("libelle"), 200), "lien": _texte(src.get("lien"), 500),
                                      "le": _texte(src.get("le"), 40)},
            "inspiration_id": _texte(ins.get("id"), 64), "angle": _texte(ins.get("angle"), 200) or None}


def _visuel(p: dict) -> str | None:
    """Le visuel est-il dans la Bibliothèque, lisible, et autre que la capture ? (comme `inspiration._visuel`)."""
    nom = p["visuel"]
    if not nom:
        return None
    if any(c in nom for c in ("/", "\\", ":")) or ".." in nom or nom != nom.strip(". "):
        raise RefusPost("Visuel inconnu dans la Bibliothèque.", "visuel", 400)
    racine = config.settings.images_path.resolve()
    f = (racine / nom).resolve()
    if f.parent != racine or not f.is_file():
        raise RefusPost("Le visuel n'est pas encore arrivé au PC : nouvel essai à la prochaine synchronisation.", "reessayer")
    try:
        e = G.empreinte(f.read_bytes())
    except (OSError, ValueError):
        raise RefusPost("Visuel illisible dans la Bibliothèque.", "visuel", 400) from None
    if G.meme_image({"sha256": p["capture_sha256"]}, e):
        raise RefusPost("Ce visuel est l'image captée : elle ne peut jamais être le visuel du post.", "visuel_capte")
    return nom


async def deposer(appareil: dict, corps) -> dict:
    """{statut: cree|deja, post_id, garde} ; RefusPost sinon (rien n'est écrit)."""
    p = _forme(corps)
    e = _es.lire()["espaces"].get(p["eid"])
    if not e:
        raise RefusPost("espace inconnu", "espace", 404)
    if e.get("archive"):
        raise RefusPost("L'espace de ce post est archivé.", "espace")
    cle = f"{str(appareil['id'])[:8]}:{p['id']}"
    emp = _empreinte({k: v for k, v in corps.items() if k != "id"})
    async with _verrou:
        reg = _lire(p["eid"])
        deja = (reg.get("recus") or {}).get(cle)
        if isinstance(deja, dict):
            if deja.get("empreinte") != emp:
                raise RefusPost("même identifiant, autre contenu : rien n'est écrasé", "conflit")
            return {"statut": "deja", "post_id": deja.get("post_id"), "garde": deja.get("garde")}
        tout = "\n".join(x for x in (p["titre"], p["accroche"], p["legende"]) if x)
        interdits = await INS._interdits(p["eid"])
        garde = G.juger(p["reference"], tout)
        fautifs = INS._fautifs(tout, interdits)
        j = {"garde": {k: garde[k] for k in ("suite", "proximite", "ok")}, "interdits": fautifs}
        if not garde["ok"]:
            raise RefusPost("Trop proche de la capture : une suite de 12 mots ou plus la reprend.", "copie", garde=j)
        if fautifs:
            raise RefusPost("Mots interdits de l'espace : réécris sans eux.", "interdits", garde=j)
        if INS._source_citee({"source": p["source"]}, tout):
            raise RefusPost("La source de l'inspiration (lien ou compte) ne se publie pas.", "source", garde=j)
        nom = await asyncio.to_thread(_visuel, p)
        from app.api import routes as R
        post = await R.create_scheduled_post({"title": p["titre"], "caption": p["legende"], "hook": p["accroche"] or None,
                                              "status": "draft", "run_at": INS._demain(), "espace_id": p["eid"],
                                              "source_image": nom})
        quand = datetime.now(timezone.utc).isoformat(timespec="seconds")
        note = {"id": p["inspiration_id"], "source": p["source"], "reference_composition": True,
                "capture_comme_visuel": False, "post_id": post.get("id"), "le": quand, "origine": "telephone",
                "appareil": str(appareil["id"])[:8]}
        if nom:
            await INS._noter_recette(nom, note)
        recus = reg.get("recus") if isinstance(reg.get("recus"), dict) else {}
        recus[cle] = {"empreinte": emp, "post_id": post.get("id"), "garde": j, "source": p["source"], "angle": p["angle"],
                      "visuel": nom, "le": quand}
        for k in list(recus)[:-MAX_RECUS]:
            recus.pop(k, None)
        reg["recus"] = recus
        _es._ecrire_json(_es.chemin(p["eid"], FICHIER), reg)
    logger.info(f"sync_post : brouillon {str(post.get('id'))[:8]} du téléphone, suite {garde['suite']}, "
                f"visuel {'oui' if nom else 'non'}")
    return {"statut": "cree", "post_id": post.get("id"), "garde": j}
