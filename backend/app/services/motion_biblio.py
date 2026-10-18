# -*- coding: utf-8 -*-
"""Bibliothèque motion (t233, lot « Studio : Animation », 17/10/2026) — trois sources de direction pour le nœud
« Direction motion » (t235) et le chorégraphe (t234).

Décision de l'utilisateur (Q3 = a) : prompt-motion.com n'accorde aucune licence (« les vidéos et les prompts
appartiennent à leurs créateurs »), donc RIEN de ce site n'entre dans le dépôt.

  1. style  : nos PROPRES fiches, une par thème, livrées dans le dépôt (backend/app/motion/styles/*.json), en lecture
              seule. Le vocabulaire est celui du nœud Animation (presets, easings de l'éditeur d'images clés, formats).
  2. prompt : un import de l'utilisateur (titre, texte collé, URL d'attribution OBLIGATOIRE, auteur, thèmes), rangé
              dans DEEPOTUS_DATA_DIR/motion/biblio — jamais dans le dépôt.
  3. skill  : installé À LA DEMANDE depuis un dépôt GitHub public (`owner/repo[:chemin]` ou une URL github.com /
              raw.githubusercontent.com). On ne télécharge QUE SKILL.md et la licence (+ NOTICE pour Apache-2.0), depuis
              raw.githubusercontent.com seulement, sans suivre de redirection ; refus sans licence MIT / Apache-2.0 /
              BSD / ISC. Rien n'est exécuté : on ne lit que du Markdown. Le texte d'origine est gardé à l'octet
              (DEEPOTUS_DATA_DIR/motion/skills/<id>/), `consigne` en est la copie éditable, « revenir à l'original »
              la recopie.

Miroir de preuve : DZ_MOTION_MIROIR_GITHUB (http://127.0.0.1:<port>) n'est suivi que sur une instance ISOLÉE
(DEEPOTUS_DATA_DIR posé) et en boucle locale — le backend de preuve s'en sert, l'application installée jamais.
Erreurs : ValueError → 400, PermissionError → 403, LookupError → 404, RuntimeError → 502 (traduites à la sortie).
"""
import ipaddress
import json
import os
import re
import secrets
import shutil
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.config import DATA_ROOT

STYLES_DIR = Path(__file__).resolve().parent.parent / "motion" / "styles"
THEMES = ("kinetic-type", "product-ui", "charts", "diagrams", "shapes", "particles", "characters", "photos", "phone",
          "code", "music")
# Le vocabulaire du nœud Animation (bundle, composant DzAnimation : PRESETS et EAS) et les formats du rendu.
PRESETS = ("fade-in", "slide-up", "slide-down", "slide-left", "slide-right", "pop", "zoom-in", "ken-burns")
EASINGS = ("linear", "easeIn", "easeOut", "easeInOut", "easeOutBack", "easeOutBounce", "smooth", "easeInOutSine",
           "anticipate", "overshoot")
FORMATS = ("16:9", "9:16", "1:1", "4:5")
LICENCES = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC")

RAW = "https://raw.githubusercontent.com"
HOTES_GITHUB = ("github.com", "www.github.com", "raw.githubusercontent.com")
NOMS_LICENCE = ("LICENSE", "LICENSE.md", "LICENSE.txt")
MAX_SKILL = 256 * 1024
MAX_LICENCE = 64 * 1024
MAX_TITRE, MAX_TEXTE, MAX_AUTEUR, MAX_URL, MAX_SOURCE = 200, 20000, 120, 2048, 400
MAX_ENTREES = 500
PROFONDEUR_MAX = 10

_ID = re.compile(r"^(prompt|skill)-[a-z0-9][a-z0-9-]{0,95}$")
_PROPRIO = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_DEPOT = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_REF = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}$")
_SEGMENT = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}$")

_transport = None                       # remplacé au banc par un faux miroir (httpx.MockTransport)


# ── dossiers ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _racine() -> Path:
    return DATA_ROOT / "motion"


def _dossier_entrees() -> Path:
    return _racine() / "biblio"


def _dossier_skills() -> Path:
    return _racine() / "skills"


def _ecrire_json(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def _maintenant() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ── 1. les fiches maison ──────────────────────────────────────────────────────────────────────────────────────────
def _styles() -> list:
    out = []
    for p in sorted(STYLES_DIR.glob("*.json")):
        try:
            f = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if f.get("theme") != p.stem or p.stem not in THEMES:
            continue
        out.append(dict(f, id=f"style-{p.stem}", nature="style", themes=[p.stem], lecture_seule=True))
    return out


# ── lecture ───────────────────────────────────────────────────────────────────────────────────────────────────────
def _entrees_donnees() -> list:
    d = _dossier_entrees()
    out = []
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            if not _ID.match(p.stem):
                continue
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    return out


def lister(nature: str | None = None, theme: str | None = None) -> list:
    """Styles, puis imports et skills (les plus récents d'abord). La liste ne transporte pas l'original d'un skill."""
    donnees = sorted(_entrees_donnees(), key=lambda e: e.get("cree_le", ""), reverse=True)
    out = _styles() + donnees
    if nature:
        out = [e for e in out if e.get("nature") == nature]
    if theme:
        out = [e for e in out if theme in (e.get("themes") or [])]
    return out


def _fichier_entree(eid: str) -> Path:
    if not isinstance(eid, str) or not _ID.match(eid):
        raise LookupError(f"Entrée inconnue : {eid}")
    return _dossier_entrees() / f"{eid}.json"


def _charger(eid: str) -> dict:
    p = _fichier_entree(eid)
    if not p.is_file():
        raise LookupError(f"Entrée inconnue : {eid}")
    return json.loads(p.read_text(encoding="utf-8"))


def lire(eid: str) -> dict:
    """Une entrée en entier ; pour un skill : l'original, le texte de la licence et du NOTICE."""
    if isinstance(eid, str) and eid.startswith("style-"):
        for s in _styles():
            if s["id"] == eid:
                return s
        raise LookupError(f"Entrée inconnue : {eid}")
    e = _charger(eid)
    if e.get("nature") == "skill":
        d = _dossier_skills() / eid
        e["original"] = (d / "SKILL.md").read_bytes().decode("utf-8")
        e["licence_texte"] = (d / e.get("fichier_licence", "LICENSE")).read_bytes().decode("utf-8", "replace")
        if (d / "NOTICE").is_file():
            e["notice_texte"] = (d / "NOTICE").read_bytes().decode("utf-8", "replace")
    return e


# ── validation des champs ─────────────────────────────────────────────────────────────────────────────────────────
def _texte(v, nom: str, maxi: int, requis: bool = True) -> str:
    if v is None:
        v = ""
    if not isinstance(v, str):
        raise ValueError(f"Champ invalide : {nom}")
    if requis and not v.strip():
        raise ValueError(f"Champ obligatoire : {nom}")
    if len(v) > maxi:
        raise ValueError(f"Champ trop long : {nom} (au plus {maxi} caractères).")
    return v


def _url_attribution(v) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError("L'URL d'attribution est obligatoire : un import cite toujours sa source (lien de la fiche "
                         "ou du post d'origine).")
    v = v.strip()
    if len(v) > MAX_URL or any(ord(ch) < 33 for ch in v):
        raise ValueError("URL d'attribution invalide : une adresse http(s)://… attendue.")
    u = urlsplit(v)
    if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password:
        raise ValueError("URL d'attribution invalide : une adresse http(s)://… attendue.")
    return v


def _themes(v) -> list:
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError("Champ invalide : themes")
    out = []
    for t in v:
        if t not in THEMES:
            raise ValueError(f"Thème inconnu : {t}")
        if t not in out:
            out.append(t)
    return out


# ── 2. imports de l'utilisateur ───────────────────────────────────────────────────────────────────────────────────
def importer_prompt(corps: dict) -> dict:
    if not isinstance(corps, dict):
        raise ValueError("Corps JSON attendu.")
    if len(_entrees_donnees()) >= MAX_ENTREES:
        raise ValueError(f"Bibliothèque pleine : {MAX_ENTREES} entrées au plus.")
    e = {"id": "prompt-" + secrets.token_hex(6), "nature": "prompt",
         "titre": _texte(corps.get("titre"), "titre", MAX_TITRE).strip(),
         "texte": _texte(corps.get("texte"), "texte", MAX_TEXTE),
         "url": _url_attribution(corps.get("url")),
         "auteur": _texte(corps.get("auteur"), "auteur", MAX_AUTEUR, requis=False).strip(),
         "themes": _themes(corps.get("themes")), "cree_le": _maintenant()}
    e["modifie_le"] = e["cree_le"]
    _ecrire_json(_fichier_entree(e["id"]), e)
    return e


_MODIFIABLES = {"prompt": ("titre", "texte", "url", "auteur", "themes"), "skill": ("titre", "themes", "consigne")}


def modifier(eid: str, corps: dict) -> dict:
    if isinstance(eid, str) and eid.startswith("style-"):
        lire(eid)
        raise PermissionError("Les fiches de style maison sont en lecture seule : importez un prompt ou installez un "
                              "skill pour une direction à vous.")
    e = _charger(eid)
    if not isinstance(corps, dict) or not corps:
        raise ValueError("Corps JSON attendu.")
    permis = _MODIFIABLES[e["nature"]]
    for k in corps:
        if k not in permis:
            raise ValueError(f"Champ non modifiable : {k}")
    if "titre" in corps:
        e["titre"] = _texte(corps["titre"], "titre", MAX_TITRE).strip()
    if "themes" in corps:
        e["themes"] = _themes(corps["themes"])
    if "texte" in corps:
        e["texte"] = _texte(corps["texte"], "texte", MAX_TEXTE)
    if "url" in corps:
        e["url"] = _url_attribution(corps["url"])
    if "auteur" in corps:
        e["auteur"] = _texte(corps["auteur"], "auteur", MAX_AUTEUR, requis=False).strip()
    if "consigne" in corps:
        e["consigne"] = _texte(corps["consigne"], "consigne", MAX_SKILL)
        e["modifie"] = e["consigne"] != _original(eid)
    e["modifie_le"] = _maintenant()
    _ecrire_json(_fichier_entree(eid), e)
    return e


def _original(eid: str) -> str:
    return (_dossier_skills() / eid / "SKILL.md").read_bytes().decode("utf-8")


def revenir_original(eid: str) -> dict:
    if isinstance(eid, str) and eid.startswith("style-"):
        lire(eid)
        raise ValueError("Seul un skill a un texte d'origine.")
    e = _charger(eid)
    if e.get("nature") != "skill":
        raise ValueError("Seul un skill a un texte d'origine.")
    e["consigne"], e["modifie"], e["modifie_le"] = _original(eid), False, _maintenant()
    _ecrire_json(_fichier_entree(eid), e)
    return e


def supprimer(eid: str) -> dict:
    if isinstance(eid, str) and eid.startswith("style-"):
        lire(eid)
        raise PermissionError("Les fiches de style maison sont en lecture seule : importez un prompt ou installez un "
                              "skill pour une direction à vous.")
    p = _fichier_entree(eid)
    if not p.is_file():
        raise LookupError(f"Entrée inconnue : {eid}")
    p.unlink()
    d = _dossier_skills() / eid
    if eid.startswith("skill-") and d.is_dir():
        shutil.rmtree(d)
    return {"ok": True, "id": eid}


# ── 3. skills ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _chemin(segments: list, brut: str) -> str:
    while segments and segments[-1] == "":
        segments = segments[:-1]
    if len(segments) > PROFONDEUR_MAX or any(not _SEGMENT.match(s) for s in segments):
        raise ValueError(f"Chemin refusé : {brut} — un dossier du dépôt, sans « .. » ni chemin absolu.")
    return "/".join(segments)


def analyser_source(source) -> dict:
    """`owner/repo[:chemin]`, ou une URL https://github.com/owner/repo[/tree|blob/<ref>/<chemin>] ou
    https://raw.githubusercontent.com/owner/repo/<ref>/<chemin>. Tout refus a lieu ICI, avant la moindre requête."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Source du skill attendue : owner/repo[:chemin] ou une URL github.com.")
    s = source.strip()
    if len(s) > MAX_SOURCE or any(ord(ch) < 33 for ch in s):
        raise ValueError(f"Source refusée : {s}")
    ref, chemin_brut = "HEAD", ""
    if "://" in s:
        u = urlsplit(s)
        hote = (u.hostname or "").lower()
        if u.scheme != "https" or hote not in HOTES_GITHUB or u.port or u.username or u.password \
                or (u.netloc.lower() != hote):
            raise ValueError(f"Hôte refusé : {u.netloc or s} — seuls github.com et raw.githubusercontent.com sont "
                             "permis.")
        parts = u.path.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError("Source du skill attendue : owner/repo[:chemin] ou une URL github.com.")
        proprio, depot, reste = parts[0], parts[1], parts[2:]
        if hote == "raw.githubusercontent.com":
            if not reste:
                raise ValueError("Source du skill attendue : owner/repo[:chemin] ou une URL github.com.")
            ref, reste = reste[0], reste[1:]
        elif reste:
            if reste[0] not in ("tree", "blob") or len(reste) < 2:
                raise ValueError(f"Source refusée : {s}")
            ref, reste = reste[1], reste[2:]
        segments = reste
        chemin_brut = "/".join(reste)
    else:
        tete, _, chemin_brut = s.partition(":")
        parts = tete.split("/")
        if len(parts) != 2:
            raise ValueError("Source du skill attendue : owner/repo[:chemin] ou une URL github.com.")
        proprio, depot = parts
        segments = chemin_brut.split("/") if chemin_brut else []
    depot = depot[:-4] if depot.endswith(".git") else depot
    if not _PROPRIO.match(proprio or "") or not _DEPOT.match(depot or "") or depot.strip(".") == "":
        raise ValueError(f"Dépôt refusé : {proprio}/{depot}")
    if not _REF.match(ref) or ".." in ref:
        raise ValueError(f"Référence refusée : {ref}")
    if segments and segments[-1] == "SKILL.md":
        segments = segments[:-1]
    chemin = _chemin(segments, chemin_brut)
    return {"proprio": proprio, "depot": depot, "ref": ref, "chemin": chemin}


def _base_raw() -> str:
    """raw.githubusercontent.com ; ou le miroir de preuve — instance isolée ET boucle locale seulement."""
    m = os.environ.get("DZ_MOTION_MIROIR_GITHUB", "").strip().rstrip("/")
    if m and os.environ.get("DEEPOTUS_DATA_DIR", "").strip():
        u = urlsplit(m)
        hote = (u.hostname or "").lower()
        try:
            boucle = hote == "localhost" or ipaddress.ip_address(hote).is_loopback
        except ValueError:
            boucle = False
        if u.scheme in ("http", "https") and boucle and not u.path and not u.username:
            return f"{m}/raw.githubusercontent.com"
    return RAW


def _url_permise(url: str) -> bool:
    base = _base_raw()
    return url.startswith(base + "/") and (base == RAW or urlsplit(url).hostname in ("127.0.0.1", "::1", "localhost"))


async def _telecharger(client: httpx.AsyncClient, url: str, nom: str, maxi: int) -> bytes | None:
    if not _url_permise(url):
        raise ValueError(f"Hôte refusé : {url} — seuls github.com et raw.githubusercontent.com sont permis.")
    try:
        async with client.stream("GET", url) as r:
            if r.status_code == 404:
                return None
            if 300 <= r.status_code < 400:
                raise RuntimeError(f"Redirection refusée pour {nom} : le skill doit être servi directement par "
                                   "raw.githubusercontent.com.")
            if r.status_code != 200:
                raise RuntimeError(f"GitHub a répondu HTTP {r.status_code} pour {nom}.")
            lu = bytearray()
            async for morceau in r.aiter_bytes():
                lu += morceau
                if len(lu) > maxi:
                    raise ValueError(f"Fichier trop gros : {nom} (au plus {maxi // 1024} Ko).")
            return bytes(lu)
    except httpx.HTTPError as e:
        raise RuntimeError(f"GitHub injoignable : {e}") from None


def identifier_licence(texte: str) -> str | None:
    """L'identifiant SPDX d'une licence PERMISSIVE reconnue ; None pour toute autre (GPL, CC, source-available…)."""
    t = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", texte or "")).lower()
    interdits = ("gnu general public license", "gnu lesser general public", "gnu affero", "mozilla public license",
                 "creative commons", "commons clause", "business source license", "server side public license",
                 "elastic license", "all advertising materials mentioning")
    if any(i in t for i in interdits):
        return None
    if "apache license" in t and "version 2.0" in t:
        return "Apache-2.0"
    if "permission is hereby granted, free of charge" in t and "without warranty of any kind" in t:
        return "MIT"
    if re.search(r"permission to use, copy, modify, (and/or|and) distribute this software for any purpose with or "
                 r"without fee is hereby granted", t):
        return "ISC"
    if "redistribution and use in source and binary forms, with or without modification, are permitted" in t:
        return "BSD-3-Clause" if ("neither the name" in t or "names of its contributors may" in t) else "BSD-2-Clause"
    return None


def _en_tete(texte: str) -> dict:
    """name / description de l'en-tête YAML d'un SKILL.md (lecture simple, clé: valeur)."""
    out = {}
    lignes = texte.replace("\r\n", "\n").split("\n")
    if lignes and lignes[0].strip() == "---":
        for ligne in lignes[1:60]:
            if ligne.strip() == "---":
                break
            k, sep, v = ligne.partition(":")
            if sep and k.strip() in ("name", "description"):
                out[k.strip()] = v.strip().strip("'\"")[:500]
    return out


def _id_skill(src: dict) -> str:
    brut = "-".join(x for x in (src["proprio"], src["depot"], src["chemin"].replace("/", "-")) if x).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", brut).strip("-")[:90].strip("-")
    return f"skill-{slug or 'sans-nom'}"


async def _lire_skill(src: dict) -> dict:
    """SKILL.md + licence (+ NOTICE pour Apache-2.0) d'une source déjà analysée, téléchargés et vérifiés, SANS rien
    écrire : partagé par l'aperçu (t236, la licence montrée avant de confirmer) et l'installation."""
    eid = _id_skill(src)
    if _fichier_entree(eid).is_file():
        raise ValueError(f"Skill déjà installé : {eid}")
    if len(_entrees_donnees()) >= MAX_ENTREES:
        raise ValueError(f"Bibliothèque pleine : {MAX_ENTREES} entrées au plus.")
    base = f"{_base_raw()}/{src['proprio']}/{src['depot']}/{src['ref']}"
    dossier = f"{base}/{src['chemin']}" if src["chemin"] else base
    depot = f"{src['proprio']}/{src['depot']}"
    async with httpx.AsyncClient(transport=_transport, follow_redirects=False, timeout=20.0,
                                 headers={"User-Agent": "DeepotusVideo-motion"}) as client:
        brut = await _telecharger(client, f"{dossier}/SKILL.md", "SKILL.md", MAX_SKILL)
        if brut is None:
            raise LookupError(f"SKILL.md introuvable dans {depot} ({src['chemin'] or 'racine'}).")
        if b"\0" in brut:
            raise ValueError("SKILL.md n'est pas un texte : installation refusée.")
        try:
            texte = brut.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("SKILL.md n'est pas un texte : installation refusée.") from None
        lic_brut, lic_nom, lic_dossier = None, "", ""
        candidats = ([(dossier, n) for n in NOMS_LICENCE] if src["chemin"] else []) + [(base, "LICENSE"),
                                                                                       (base, "LICENSE.md"),
                                                                                       (base, "LICENSE.txt")]
        for d, n in candidats:
            lic_brut = await _telecharger(client, f"{d}/{n}", n, MAX_LICENCE)
            if lic_brut is not None:
                lic_nom, lic_dossier = n, d
                break
        if lic_brut is None:
            raise ValueError(f"Aucune licence dans {depot} : installation refusée (MIT, Apache-2.0, BSD ou ISC "
                             "requise).")
        spdx = identifier_licence(lic_brut.decode("utf-8", "replace"))
        if spdx is None:
            raise ValueError(f"Licence non reconnue dans {depot} : installation refusée (MIT, Apache-2.0, BSD ou ISC "
                             "requise).")
        notice = None
        if spdx == "Apache-2.0":
            notice = await _telecharger(client, f"{lic_dossier}/NOTICE", "NOTICE", MAX_LICENCE)
    return {"eid": eid, "depot": depot, "brut": brut, "texte": texte, "lic_brut": lic_brut, "lic_nom": lic_nom,
            "spdx": spdx, "notice": notice}


def _url_github(src: dict) -> str:
    return f"https://github.com/{src['proprio']}/{src['depot']}/tree/{src['ref']}" +         (f"/{src['chemin']}" if src["chemin"] else "")


async def apercu_skill(source) -> dict:
    """t236 — ce que l'installation ferait, SANS rien écrire : nom, description, dépôt et la licence lue (identifiant
    et texte), pour que l'écran la montre AVANT que l'utilisateur confirme. Mêmes refus que l'installation."""
    src = analyser_source(source)
    lu = await _lire_skill(src)
    tete = _en_tete(lu["texte"])
    return {"id": lu["eid"], "titre": (tete.get("name") or src["depot"])[:MAX_TITRE],
            "description": tete.get("description", ""),
            "source": {"depot": lu["depot"], "chemin": src["chemin"], "ref": src["ref"], "url": _url_github(src)},
            "licence": lu["spdx"], "fichier_licence": lu["lic_nom"],
            "licence_texte": lu["lic_brut"].decode("utf-8", "replace"), "notice": lu["notice"] is not None,
            "taille": len(lu["brut"])}


async def installer_skill(source, licence=None) -> dict:
    """Installe un skill. `licence` (facultatif, t236) = l'identifiant montré par l'aperçu : s'il ne correspond plus à
    la licence téléchargée maintenant, l'installation est refusée (l'utilisateur confirme ce qu'il a lu)."""
    src = analyser_source(source)
    lu = await _lire_skill(src)
    eid, depot, brut, texte = lu["eid"], lu["depot"], lu["brut"], lu["texte"]
    lic_brut, lic_nom, spdx, notice = lu["lic_brut"], lu["lic_nom"], lu["spdx"], lu["notice"]
    if licence is not None and licence != spdx:
        raise ValueError(f"La licence de {depot} a changé depuis l'aperçu ({licence} → {spdx}) : relisez-la avant "
                         "d'installer.")
    # Écriture : un dossier temporaire, puis renommé — un refus plus haut n'a rien laissé.
    racine = _dossier_skills()
    racine.mkdir(parents=True, exist_ok=True)
    tmp = racine / f".tmp-{eid}-{secrets.token_hex(3)}"
    tmp.mkdir()
    try:
        (tmp / "SKILL.md").write_bytes(brut)
        (tmp / lic_nom).write_bytes(lic_brut)
        if notice is not None:
            (tmp / "NOTICE").write_bytes(notice)
        os.replace(tmp, racine / eid)
    except OSError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    tete = _en_tete(texte)
    url_gh = _url_github(src)
    e = {"id": eid, "nature": "skill", "titre": (tete.get("name") or src["depot"])[:MAX_TITRE],
         "description": tete.get("description", ""), "themes": [],
         "source": {"depot": depot, "chemin": src["chemin"], "ref": src["ref"], "url": url_gh},
         "licence": spdx, "fichier_licence": lic_nom, "fichiers": sorted(p.name for p in (racine / eid).iterdir()),
         "consigne": texte, "modifie": False, "cree_le": _maintenant()}
    e["modifie_le"] = e["cree_le"]
    _ecrire_json(_fichier_entree(eid), e)
    return e
