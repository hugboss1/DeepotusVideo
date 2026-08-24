# -*- coding: utf-8 -*-
"""Card Forge — CORE : le magasin de decks et les routes du noyau.

Ce fichier appartient à CORE. Les dix pièces ne le touchent jamais ; elles
lisent `contract.py` et écrivent leur propre `<id>.py`.

Stockage — `outputs/decks/deck_xxxxxxxx/meta.json`, voisin de materials/,
sprites/ et assets3d/. AUCUNE table SQL : ni les matières ni les sprites n'en
ont, et un deck n'est pas plus relationnel qu'une matière. `meta.json` est
écrit ATOMIQUEMENT (brouillon à suffixe unique + `replace` patient) —
l'autosave de l'écran tape toutes les 900 ms, une écriture interrompue
laisserait un document tronqué que la prochaine ouverture lirait comme un
deck vide.

À côté des dossiers de jeux vit `decks_index.json`, l'index de LISTING : un
CACHE des quatre champs affichés, revalidé par un stat par jeu. `meta.json`
reste la vérité — l'index ne dispense que de l'OUVRIR. Voir la section
« l'index de listing », plus bas, pour ce qu'il coûte et ce qu'il rapporte.

Le document est PARTITIONNÉ (spec 2.3) : un sous-arbre par pièce, plus les
clés de CORE. `normalize_deck` ne lève jamais — un `meta.json` abîmé se
répare au lieu de faire tomber l'appelant, exactement comme
`material_store.read_material`.

Routes (montées sous `/api/cards` par `app/main.py`) :

    GET    /formats          catalogue des 12 formats + 3 planches + DPI
    GET    /decks            résumés bornés `{decks, total, limit}` — `?limit=`
                             dans [1, 500], 100 par défaut
    POST   /decks            création (corps `{model}` = instanciation)
    POST   /decks/{did}/duplicate   copie complète, dossier compris
    GET    /{did}            document complet
    PATCH  /{did}            autosave (fusion partielle) — spec 2.2 §10
    DELETE /{did}            suppression
    GET    /{did}/geom       géométrie du deck, calculée par `contract.geom`

L'ORDRE DE DÉCLARATION COMPTE : Starlette apparie dans l'ordre. `/formats` et
`/decks` sont déclarés AVANT `/{did}`, sinon ils tomberaient dedans et
répondraient « identifiant de deck invalide ».
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from loguru import logger

from .contract import (
    BLEED_IMPERIAL_MM, BLEED_METRIC_MM, BLEED_MM_MAX, CORNER_MM_MAX,
    CardGeom, DEFAULT_CORNER_MM, DEFAULT_DPI, DEFAULT_FMT, DPI_CHOICES,
    DPI_MAX, DPI_MIN, FORMATS, MODULE_IDS, RULE_TEXT, SAFE_MM_MAX, SHEETS,
    deck_dir, decks_root, format_table, geom, is_valid_did, native_bleed_mm,
    sheet_px,
)

router = APIRouter()

DOC_VERSION = 1
NAME_MAX = 120


# ── document ────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_did() -> str:
    root = decks_root()
    for _ in range(64):
        did = "deck_" + uuid4().hex[:8]
        if not (root / did).exists():
            return did
    raise RuntimeError("Impossible d'allouer un identifiant de deck")


def clean_name(raw, fallback: str = "Mon jeu") -> str:
    """Nom lisible, jamais vide, jamais un roman. Ne lève pas."""
    s = str(raw or "").strip()
    if not s:
        return fallback
    return s[:NAME_MAX]


def default_format() -> dict:
    return {"fmt": DEFAULT_FMT, "dpi": DEFAULT_DPI,
            "bleed_mm": native_bleed_mm(DEFAULT_FMT),
            "safe_mm": native_bleed_mm(DEFAULT_FMT),
            "corner_mm": DEFAULT_CORNER_MM}


def normalize_format(raw, base: dict | None = None) -> dict:
    """Bloc `format` réparé, jamais une exception. Une valeur illisible
    reprend son défaut plutôt que de rendre le deck inouvrable.

    `base` est l'état ACTUEL du bloc — c'est ce qui rend le PATCH réellement
    PARTIEL. Sans lui, `PATCH {"format":{"dpi":600}}` sur un deck `tarot_us`
    repartait de `default_format()` et rendait le deck à `poker_eu` SANS UN
    MOT : la carte changeait de taille (1630x2220 au lieu de 1800x3000) sur
    un réglage de définition. Une clé absente du corps veut dire « ne touche
    pas », jamais « reprends le défaut d'usine ».

    Le changement de `fmt` reprend le fond perdu NATIF du nouveau format
    (0.125 in en impérial, 3 mm en métrique) — même règle que
    `setFormatInternal` côté écran et que l'aperçu de `/geom` — sauf si le
    corps fixe explicitement `bleed_mm` / `safe_mm`.
    """
    raw = raw if isinstance(raw, dict) else {}
    out = default_format()
    if isinstance(base, dict):
        for k in out:
            if k in base:
                out[k] = base[k]
    fmt = str(raw.get("fmt") or "").strip().lower()
    if fmt in FORMATS and fmt != out["fmt"]:
        out["fmt"] = fmt
        out["bleed_mm"] = native_bleed_mm(fmt)
        out["safe_mm"] = native_bleed_mm(fmt)
    elif fmt in FORMATS:
        out["fmt"] = fmt
    if "dpi" in raw:
        try:
            dpi = int(raw.get("dpi"))
            if DPI_MIN <= dpi <= DPI_MAX:
                out["dpi"] = dpi
        except (TypeError, ValueError, OverflowError):
            # OverflowError : json.loads("1e999") rend float('inf') et
            # int(inf) lève — c'était un 500 sur un simple corps mal formé.
            pass
    for key, hi in (("bleed_mm", BLEED_MM_MAX), ("safe_mm", SAFE_MM_MAX),
                    ("corner_mm", CORNER_MM_MAX)):
        if key not in raw:
            continue
        try:
            v = float(raw.get(key))
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(v) and 0.0 <= v <= hi:
            out[key] = v
    return out


def default_doc(did: str, name: str = "Mon jeu") -> dict:
    """Le document neuf, partitionné (spec 2.3). Chaque pièce reçoit son
    sous-arbre VIDE : c'est elle qui décide de son contenu, CORE ne préjuge
    de rien."""
    doc = {"v": DOC_VERSION, "id": did, "name": clean_name(name),
           "format": default_format(),
           "created": _now_iso(), "updated": _now_iso()}
    for mid in MODULE_IDS:
        doc[mid] = {}
    return doc


def normalize_deck(raw: dict | None, did: str | None = None) -> dict:
    """Document complet à partir de n'importe quoi (meta.json abîmé, corps
    client partiel…). NE LÈVE JAMAIS.

    Le PARTITIONNEMENT est appliqué ici, et c'est le seul endroit : une clé
    qui n'est ni une clé de CORE ni l'un des dix ids est jetée. Sans cela,
    un client (ou un module distrait) pourrait faire pousser le document
    n'importe où et deux pièces finiraient par se marcher dessus.

    LE REVERS, payé comptant : ce filtre ne trie pas, il EFFACE. Un id vivant
    au rail mais oublié de `MODULE_IDS` voit son sous-arbre disparaître à
    chaque autosave, sans un message — c'est l'histoire de `doc.forge3d`
    (phases 2a à 3c). La liste et le rail se tiennent la main."""
    raw = raw if isinstance(raw, dict) else {}
    did = did or raw.get("id")
    doc = default_doc(did if is_valid_did(did) else "deck_00000000",
                      raw.get("name"))
    doc["format"] = normalize_format(raw.get("format"))
    created = raw.get("created")
    if isinstance(created, str) and created:
        doc["created"] = created
    updated = raw.get("updated")
    if isinstance(updated, str) and updated:
        doc["updated"] = updated
    for mid in MODULE_IDS:
        sub = raw.get(mid)
        doc[mid] = sub if isinstance(sub, dict) else {}
    return doc


def geom_of(doc: dict) -> CardGeom:
    """Géométrie du deck. Le bloc `format` est déjà normalisé par
    `normalize_deck`, donc cet appel ne peut pas lever."""
    f = normalize_format((doc or {}).get("format"))
    return geom(f["fmt"], f["dpi"], f["bleed_mm"], f["safe_mm"], f["corner_mm"])


# ── magasin sur disque ──────────────────────────────────────────────────────

# LA PATIENCE FACE AU CONFLIT DE PARTAGE, patron T1 (`capture.py:_store_image`,
# RECOPIÉ et non partagé entre modules — règle 8 ; ici, DANS le fichier, un
# seul couple de constantes sert les DEUX bouts du même conflit). Sur Windows,
# `replace` par-dessus un fichier que quelqu'un LIT échoue avec WinError 5,
# deux `replace` visant la même destination se refusent l'un l'autre
# (MoveFileEx), et symétriquement OUVRIR un fichier qu'un `replace` est en
# train de remplacer échoue aussi. Une seconde tentative après un souffle les
# absorbe : le conflit dure le temps d'un appel système, pas d'une requête.
#
# Le plafond est court EXPRÈS : CINQ essais séparés par QUATRE pauses, soit
# 80 ms au pire — et non 100, l'arithmétique de la première écriture comptait
# une pause qui n'existe pas (le cinquième essai lève au lieu de dormir ;
# 82 ms mesurés sur un remplacement qui refuse toujours). Au-delà, ce n'est
# plus une course mais un vrai problème de disque, et il doit se DIRE.
PARTAGE_ESSAIS = 5
PARTAGE_PAUSE_S = 0.02


def _replace_patient(tmp, final) -> None:
    for reste in range(PARTAGE_ESSAIS - 1, -1, -1):
        try:
            tmp.replace(final)
            return
        except OSError:
            if not reste:
                raise
            time.sleep(PARTAGE_PAUSE_S)


# L'ÂGE À PARTIR DUQUEL UN BROUILLON EST UNE ÉPAVE. Il n'est pas décoratif :
# un brouillon JEUNE peut appartenir à une écriture EN COURS dans un autre fil,
# et le ramasser rejouerait, en pire, le défaut du nom fixe. Cinq minutes,
# c'est mille fois la durée d'une écriture (~6 ms) et une fraction de session.
BROUILLON_RASSIS_S = 300.0


def _balaye_les_brouillons(d) -> None:
    """Ramasse les brouillons RASSIS d'un dossier de jeu.

    LE SUFFIXE UNIQUE A UN REVERS, ET IL N'ÉTAIT PAS PAYÉ : une écriture
    interrompue par autre chose qu'une `OSError` — l'arrêt du processus, une
    coupure de courant, un `KeyboardInterrupt` — laisse une épave que plus RIEN
    ne réutilise. Le nom fixe d'avant, lui, était au moins repris au coup
    suivant. Sans ramassage, un dossier de jeu accumule ses épaves pour
    toujours, et `duplicate_deck` les recopiait fidèlement dans chaque copie.

    L'échec du ramassage est SANS GRAVITÉ et se tait : quelqu'un d'autre l'a
    pris, ou le disque refuse — l'écriture qui suit, elle, dira ce qu'il faut.

    LE COÛT EST PAYÉ À CHAQUE AUTOSAVE, donc il a été mesuré : 0,13 ms sur un
    dossier propre, 0,38 ms sur un dossier qui porte huit brouillons, contre
    6,8 ms pour l'écriture entière. Deux pour cent, pour un dossier de jeu qui
    ne grossit plus jamais tout seul."""
    limite = time.time() - BROUILLON_RASSIS_S
    try:
        epaves = list(d.glob("meta.json.*.tmp"))
    except OSError:
        return
    for p in epaves:
        try:
            if p.stat().st_mtime < limite:
                p.unlink()
        except OSError:
            pass


def write_deck(doc: dict) -> dict:
    """Écrit meta.json ATOMIQUEMENT : brouillon à SUFFIXE UNIQUE, puis
    `replace` PATIENT.

    LE TEMPORAIRE À NOM FIXE NE SUFFISAIT PAS, ET C'EST MESURÉ. `meta.json.tmp`
    est le même fichier pour tout le monde : deux autosaves simultanées sur le
    même jeu y écrivent l'une par-dessus l'autre. Et même seule, une autosave
    butait sur le listing : `replace` par-dessus un `meta.json` qu'un balayage
    est en train de LIRE refuse avec WinError 5 — 2 échecs sur 12 autosaves
    face à 8 listings concurrents, mesurés AVANT ce correctif, et un `PATCH`
    qui répondait 500 à l'utilisateur pour une frappe au clavier. Le défaut
    précède l'index de listing (reproduit à l'identique sur l'arbre d'avant) ;
    l'index le rend simplement plus visible, puisqu'il RESTE des lectures.

    Le brouillon unique donne à chaque écriture LE SIEN, la patience absorbe la
    course, et le `replace` reste atomique : le dernier arrivé gagne
    proprement, jamais un document tronqué."""
    did = doc.get("id")
    d = deck_dir(did, create=True)
    _balaye_les_brouillons(d)
    tmp = d / f"meta.json.{uuid4().hex}.tmp"
    try:
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        _replace_patient(tmp, d / "meta.json")
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass               # le brouillon n'a peut-être jamais existé
        raise
    return doc


def create_deck(name: str = "Mon jeu", fmt: dict | None = None,
                did: str | None = None) -> dict:
    did = did or new_did()
    deck_dir(did, create=True)
    doc = default_doc(did, name)
    if fmt is not None:
        doc["format"] = normalize_format(fmt)
    return write_deck(doc)


META_LU = "lu"                # les octets ont été compris
META_CORROMPU = "corrompu"    # les octets sont là, et ce n'est pas du JSON
META_ABSENT = "absent"        # pas de meta.json, ou pas un identifiant de jeu
META_REFUS = "refus"          # le fichier existe, et il s'est REFUSÉ à l'instant


def _lit_meta(did: str) -> tuple[dict | None, str]:
    """(document, état) — LE SEUL endroit du magasin qui OUVRE un meta.json.

    QUATRE ÉTATS, ET LA DISTINCTION QUI COMPTE EST « CORROMPU » CONTRE
    « REFUS ». Les deux se présentaient sous un même `except (OSError,
    ValueError)`, et le remède unique était de RÉPARER — c'est-à-dire de
    fabriquer un document neuf, nommé « Mon jeu », daté de MAINTENANT.

      · CORROMPU (`ValueError`) : les octets sont là et ne sont pas du JSON.
        La réparation est la bonne réponse, et elle ne bouge pas d'un iota —
        re-datage compris, comportement ÉPINGLÉ par les tests. `normalize_deck`
        remplit `created`/`updated` avec l'heure courante, si bien qu'un
        document abîmé est, à chaque lecture, le plus récent du backend.
      · REFUS (`OSError`) : le fichier existe, il est SAIN, et il s'est refusé
        à cet instant précis — sur Windows, ouvrir un `meta.json` qu'un
        `replace` est en train de remplacer échoue ainsi. Une milliseconde plus
        tard, il se lit. Réparer là-dessus, c'est INVENTER un document :
        mesuré 32 courses sur 32, le faux « Mon jeu » prenait la PREMIÈRE
        LIGNE de la galerie, devant le jeu qu'on venait justement de modifier.
        Pire, `PATCH` lit-modifie-écrit : le document inventé, vide, écrasait
        le vrai.

    UN REFUS NE REND DONC RIEN, et c'est à l'appelant de décider. Le listing
    sert ce que l'index sait déjà (vrai, peut-être d'une seconde) ; les routes
    par identifiant répondent « introuvable ». LE MARCHÉ EST DIT : un 404
    passager sur un jeu qui existe est un défaut mineur et qui se corrige au
    rafraîchissement suivant ; écraser ce jeu par un document vide n'en est
    pas un.
    """
    try:
        d = deck_dir(did)
    except ValueError:
        return None, META_ABSENT
    f = d / "meta.json"
    if not f.is_file():
        return None, META_ABSENT
    # LA PATIENCE, DU CÔTÉ DE LA LECTURE. C'est le MÊME conflit de partage que
    # celui du `replace`, vu de l'autre bout : plutôt que d'abandonner au
    # premier refus, on laisse passer l'appel système qui tenait le fichier.
    # Sans elle, la seule bonne réponse au refus — ne rien rendre — faisait
    # SILENCIEUSEMENT SAUTER l'autosave qui l'avait provoqué (mesuré : 1 sur
    # 12 sous bousculade). Avec elle, le refus qui reste est un vrai refus.
    octets = None
    for reste in range(PARTAGE_ESSAIS - 1, -1, -1):
        try:
            octets = f.read_text(encoding="utf-8")
            break
        except OSError as e:
            if not reste:
                # LE CHEMIN ABSOLU NE VA PAS AU JOURNAL : `str(e)` le porte,
                # donc le nom de compte (la jurisprudence de la fuite).
                motif = getattr(e, "strerror", None) or e.__class__.__name__
                logger.debug(
                    f"cards: meta.json refusé pour {did} : {motif}")
                return None, META_REFUS
            time.sleep(PARTAGE_PAUSE_S)
    try:
        raw = json.loads(octets)
    except ValueError as e:
        logger.warning(f"cards: meta.json illisible pour {did}: {e}")
        return normalize_deck({}, did), META_CORROMPU
    return normalize_deck(raw, did), META_LU


def read_deck(did: str) -> dict | None:
    """Document, ou None si le dossier/meta est absent — ou si le fichier s'est
    REFUSÉ à l'instant. Un meta.json CORROMPU, lui, est normalisé plutôt que de
    faire tomber l'appelant.

    Façade de `_lit_meta` : les cinquante appelants du domaine n'ont que faire
    de l'état détaillé, et la signature ne bouge pas d'une virgule."""
    return _lit_meta(did)[0]


DECK_SUMMARY_KEYS = ("id", "name", "created", "updated")


def deck_summary(doc: dict) -> dict:
    """Les QUATRE champs qu'une liste de jeux affiche, et rien d'autre.

    C'EST LA MOITIÉ MESURÉE DE LA DETTE « pagination /decks » : la route
    servait les documents COMPLETS — 13,4 Mo et 18 s sur un poste à 2 191 jeux
    (mesure du 22/08 ; re-mesuré le 23/08 sur le même poste : 2 195 jeux,
    6 607 octets pour un document réel, soit ~13,8 Mo) — que l'écran rabotait À
    L'ARRIVÉE, après les avoir fait traverser le réseau, le parseur JSON et le
    tas de l'onglet. Le rabot passe ici : 2 679 octets servis à `limit=24`.

    CE QUE CELA N'ACHETAIT PAS — et qui est soldé depuis : le disque coûtait
    pareil, puisqu'il fallait ouvrir chaque meta.json pour connaître `updated`,
    donc pour trier (13,5 s mesurées le 23/08, inchangées par le rabot ;
    13,8 s au déployé le 24/08). C'est l'index de listing, plus bas, qui a pris
    cette moitié-là : un stat par jeu, zéro ouverture quand rien n'a bougé.

    L'entrée est un document DÉJÀ NORMALISÉ (`read_deck`) : `name` y est une
    chaîne non vide et les deux dates des chaînes. La coercition ci-dessous est
    une ceinture pour l'appelant hypothétique qui passerait un `meta.json` brut,
    pas une normalisation — celle-là vit dans `normalize_deck`, à un endroit."""
    return {k: str(doc.get(k) or "") for k in DECK_SUMMARY_KEYS}


# ── l'index de listing ──────────────────────────────────────────────────────
# L'AUTRE MOITIÉ DE LA DETTE « pagination /decks ». La 3c a raboté les OCTETS
# servis ; le BALAYAGE, lui, n'avait pas bougé — la route rouvrait CHAQUE
# meta.json pour connaître `updated`, donc pour trier, et elle le refaisait
# intégralement à chaque appel, y compris quand rien n'avait changé.
#
#   · déployé, 24/08 : `GET /decks?limit=1` = 13 850 ms à froid pour
#     2 198 jeux — le même backend répond 177 ms sur /health ;
#   · corpus synthétique de 2 200 jeux minimaux, cache OS CHAUD (la partie
#     reproductible) : 2 200 ouvertures et ~5 800 ms, à chaque appel.
#
# Le remède est un CACHE, et il s'assume comme tel : `meta.json` reste LA
# VÉRITÉ, l'index ne dispense que de l'OUVRIR. Chaque jeu est revalidé par UN
# stat de son meta.json — (mtime, taille) concordants, l'entrée sert ;
# discordants, on relit. Une édition faite HORS de l'app (un script QA, une
# restauration de sauvegarde, un éditeur de texte) est donc vue au stat
# suivant, sans qu'aucun chemin d'écriture ait eu à prévenir qui que ce soit.
# C'est POURQUOI les chemins d'écriture n'entretiennent PAS l'index : la
# revalidation les rattrape tous, et l'autosave de l'écran tape toutes les
# 900 ms. Lui faire relire puis réécrire un fichier de 2 200 entrées, c'est
# +17 ms sur CHAQUE frappe (9,8 de lecture et de vérification, 7,2 d'écriture)
# — un autosave multiplié par deux à quatre selon ce que coûte l'écriture
# elle-même, la fourchette venant du `patch_deck` mesuré, pas du surcoût, qui
# lui ne bouge pas. Et cela ne supprimerait pas UN SEUL des stats de
# revalidation : ils restent nécessaires pour voir les éditions faites hors de
# l'app, ce qu'aucun entretien au fil de l'eau ne peut couvrir.
#
# LE PIÈGE QUI SE NOMME : le mtime du dossier `decks/` NE BOUGE PAS quand un
# `meta.json` imbriqué change — un dossier n'est daté que par les entrées
# qu'on lui AJOUTE ou qu'on lui RETIRE. Invalider l'index sur l'horodatage de
# la racine serait donc FAUX, et faux en silence. C'est le stat PAR JEU qui
# fait foi ; le test `test_le_MTIME_DU_DOSSIER_RACINE_...` le MESURE au lieu
# de le croire sur parole.
#
# LE TROU CONNU, ÉCRIT PLUTÔT QUE MASQUÉ : deux écritures d'un même meta.json
# qui tombent dans le MÊME tic d'horodatage du système de fichiers ET rendent
# le même nombre d'octets sont indiscernables au stat. C'est le trou de tout
# cache (mtime, taille). Sa fenêtre a été MESURÉE ici plutôt que devinée :
# l'horodatage avance de 0,35 ms au plus serré, 1,0 ms en médiane (2 963
# valeurs distinctes en 3 s, NTFS) — et non les ~15 ms qu'affirmait la
# première écriture, qui prenait le quantum d'ordonnancement pour la
# résolution du système de fichiers. Le trou est donc SIX FOIS plus étroit
# qu'annoncé ; la conclusion prudente, elle, ne change pas. L'autosave tape
# toutes les 900 ms et réécrit `updated` à chaque passage : la ronde adverse
# n'a pas réussi à atteindre ce trou par `write_deck` en 500 tentatives.

# LE NOM NE PEUT PAS ÊTRE PRIS POUR UN JEU : il ne satisfait pas `DID_RE`
# (`^deck_[0-9a-f]{8}$`), et le balayage ne retient que des DOSSIERS. Deux
# verrous, la doctrine de `deck_dir` — le motif PUIS le confinement.
INDEX_NAME = "decks_index.json"
INDEX_VERSION = 1

# Drapeau de module : l'avertissement « index non posable » se dit UNE FOIS.
_INDEX_PLAINTE_DITE = False

def _index_lu() -> tuple[dict, bool]:
    """(entrées PROPRES, le fichier était-il déjà propre). NE LÈVE JAMAIS.

    Illisible, tronqué, vide, remplacé par une liste, d'une VERSION inconnue :
    autant de façons de dire « cache absent ». On rebalaye, on réécrit, et
    personne ne s'en aperçoit — sauf le chronomètre du premier passage.

    LE MOTIF EST LA SEULE BRETELLE DE CE CHEMIN-LÀ, et c'est ce qui rend le
    filtre obligatoire ICI. La branche d'index sert `_resume_d_entree` SANS
    jamais passer par `deck_dir` — contrairement à la branche de relecture,
    qui, elle, est bordée deux fois. Une clé qui n'est pas un identifiant de
    jeu s'écarte donc à la LECTURE, et non en espérant qu'un garde-fou plus
    loin la refuse : il n'y en a pas.

    LE SECOND RETOUR EXISTE POUR UNE RAISON PRÉCISE. Écarter une clé à la
    lecture ne la fait pas disparaître du FICHIER : elle n'est plus jamais
    servie, mais elle survit à tous les listings, parce que le cache calculé
    est alors identique au cache lu et que rien ne déclenche la réécriture.
    `intact` faux veut dire « le fichier porte de la pollution » — et cela
    suffit à le faire reposer, propre."""
    try:
        brut = json.loads(
            (decks_root() / INDEX_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, True
    if not isinstance(brut, dict) or brut.get("v") != INDEX_VERSION:
        return {}, True
    entrees = brut.get("decks")
    if not isinstance(entrees, dict):
        return {}, True
    propres, intact = {}, True
    for k, v in entrees.items():
        e = _entree_normalisee(v) if is_valid_did(k) else None
        if e is None:
            intact = False       # clé étrangère, ou entrée qui ne tient pas
            continue
        if e is not v:
            intact = False       # il a fallu la ramener à cinq clés
        propres[k] = e
    return propres, intact


def _index_ecrit(entrees: dict) -> None:
    """Pose l'index ATOMIQUEMENT, et sans jamais faire tomber le listing.

    Brouillon à SUFFIXE UNIQUE puis `_replace_patient`, comme `write_deck` :
    deux listings simultanés ne se disputent pas le même brouillon, et le
    dernier arrivé gagne proprement — l'index est un cache, deux vérités
    concurrentes y sont la même à un balayage près.

    AUCUNE INDENTATION : personne ne lit ce fichier à l'œil, et 2 200 entrées
    indentées, ce sont des octets et du temps de sérialisation pour rien.

    UN ÉCHEC D'ÉCRITURE N'EST PAS UNE ERREUR DE LA ROUTE — disque plein,
    dossier en lecture seule, antivirus qui tient le fichier : la liste est
    déjà calculée et JUSTE, elle sera simplement froide au passage suivant.
    Le journal reçoit `strerror` et RIEN D'AUTRE : `str(e)` porterait le
    chemin absolu, donc le nom de compte (la jurisprudence de la fuite)."""
    racine = decks_root()
    tmp = racine / f"{INDEX_NAME}.{uuid4().hex}.tmp"
    try:
        tmp.write_text(json.dumps({"v": INDEX_VERSION, "decks": entrees},
                                  ensure_ascii=False), encoding="utf-8")
        _replace_patient(tmp, racine / INDEX_NAME)
        return
    except OSError as e:
        global _INDEX_PLAINTE_DITE
        motif = getattr(e, "strerror", None) or e.__class__.__name__
        # « AU-DELÀ, C'EST UN VRAI PROBLÈME DE DISQUE, ET IL DOIT SE DIRE » —
        # la phrase était démentie par un `logger.debug`, muet en exploitation.
        # Un index qu'on ne peut plus poser, ce sont 13,8 s à CHAQUE ouverture
        # de la galerie, pour toujours, sans un signal. UNE SEULE FOIS malgré
        # tout : répété à chaque listing, l'avertissement noierait le journal
        # au lieu de le renseigner.
        if not _INDEX_PLAINTE_DITE:
            _INDEX_PLAINTE_DITE = True
            logger.warning(
                f"cards: l'index de listing n'a pas pu être posé ({motif}) — "
                "la galerie repayera le balayage complet à chaque ouverture. "
                "Message non répété.")
        try:
            tmp.unlink()
        except OSError:
            pass                   # le brouillon n'a peut-être jamais existé


INDEX_CLES = ("name", "created", "updated", "mtime", "size")


def _entree_normalisee(vieille) -> dict | None:
    """L'entrée d'index ramenée à CINQ clés, ou None si elle ne tient pas
    debout. Rend l'objet REÇU quand il est déjà propre — l'appelant se sert de
    cette identité pour savoir s'il a fallu nettoyer.

    RAMENÉE, PAS RELAYÉE, et c'est la différence qui compte : rendre l'ancienne
    telle quelle laissait survivre tout ce qu'une main — ou un schéma défunt —
    y avait glissé. Une clé étrangère de cinq kilo-octets traversait listing
    après listing et grossissait le cache pour toujours.

    Les trois champs servis doivent être des CHAÎNES et les deux empreintes
    des ENTIERS. Un index qui ment sur leur type ne doit pas faire sortir un
    nombre là où l'écran attend un nom : il redevient un cache absent, pour ce
    jeu-là seulement. (`bool` est un `int` en Python — un `true` glissé dans
    `mtime` se refuse comme le reste.)"""
    if not isinstance(vieille, dict):
        return None
    if not all(isinstance(vieille.get(k), str)
               for k in ("name", "created", "updated")):
        return None
    for k in ("mtime", "size"):
        v = vieille.get(k)
        if not isinstance(v, int) or isinstance(v, bool):
            return None
    # DÉJÀ PROPRE : cinq clés présentes et bien typées, donc CES cinq-là. On
    # rend l'objet reçu — reconstruire 2 200 dictionnaires par listing pour
    # aboutir aux mêmes octets coûtait 14 ms mesurées, et le cas courant est
    # justement celui-là.
    if len(vieille) == len(INDEX_CLES):
        return vieille
    return {k: vieille[k] for k in INDEX_CLES}


def _entree_a_jour(vieille, st) -> dict | None:
    """L'entrée d'index si elle CONCORDE avec le disque, sinon None.

    Concorder, c'est porter le MÊME horodatage à la nanoseconde et la MÊME
    taille que le meta.json qu'on vient de stat. L'horodatage est gardé en
    NANOSECONDES ENTIÈRES exprès : `st_mtime` est un flottant, et un flottant
    qui fait l'aller-retour par JSON est une comparaison d'égalité qu'on ne
    veut pas avoir à défendre.

    LA GARDE DE FORME VIT UN CRAN PLUS HAUT : `_index_lu` ne rend que des
    entrées à cinq clés bien typées. Il reste ici le contrôle des trois
    chaînes — trois `isinstance`, pas un dictionnaire de plus — parce que
    c'est `_resume_d_entree` qui les indexera juste après, et qu'un `KeyError`
    dans un listing serait un 500 pour un cache abîmé."""
    if not isinstance(vieille, dict):
        return None
    if (vieille.get("mtime") != st.st_mtime_ns
            or vieille.get("size") != st.st_size):
        return None
    if not all(isinstance(vieille.get(k), str)
               for k in ("name", "created", "updated")):
        return None
    return vieille


def _entree_de_document(doc: dict, st, lisible: bool) -> dict | None:
    """L'entrée d'index d'un document qu'on VIENT de lire — ou None quand il
    ne doit pas être mis en cache.

    Un document RÉPARÉ (`lisible` faux) n'entre JAMAIS : `normalize_deck` lui
    a donné l'heure courante, et cette date-là n'est vraie qu'une seconde. La
    figer ferait mentir l'index pour toujours, et déciderait en douce d'une
    question de produit que la 3c a laissée ouverte."""
    if not lisible:
        return None
    r = deck_summary(doc)
    return {"name": r["name"], "created": r["created"],
            "updated": r["updated"],
            "mtime": st.st_mtime_ns, "size": st.st_size}


def _resume_d_entree(did: str, entree: dict) -> dict:
    """Le résumé servi DEPUIS l'index. `id` vient du NOM DU DOSSIER, jamais de
    l'entrée : un index qui se tromperait d'identifiant ne peut pas faire
    sortir le nom d'un jeu sous l'identifiant d'un autre."""
    return {"id": did, "name": entree["name"],
            "created": entree["created"], "updated": entree["updated"]}


# ── le balayage ─────────────────────────────────────────────────────────────

def _dossiers_de_decks() -> list:
    """Les DOSSIERS de jeux, et rien d'autre. LÈVE si le disque refuse.

    `os.scandir` plutôt qu'`iterdir` : le parcours rend déjà les métadonnées de
    chaque entrée, si bien qu'`is_dir()` ne coûte pas un appel système de plus.
    Le MOTIF est éprouvé D'ABORD — une comparaison de chaîne ne coûte rien —
    ce qui écarte l'index, ses brouillons et tout fichier de service sans même
    les interroger.

    ELLE A AVALÉ L'`OSError` LE TEMPS D'UNE LIVRAISON, et c'était une
    régression en deux temps. La liste vide passait pour « vous n'avez aucun
    jeu », en 200, là où la version d'avant laissait le refus du disque faire
    son erreur ; et le listing CONTINUAIT jusqu'à écraser l'index avec `{}` —
    le cache de 2 200 entrées effacé par un accès refusé passager, et tout à
    repayer au passage suivant.

    UN BALAYAGE QUI N'A PAS EU LIEU N'EST PAS UN BALAYAGE VIDE. Il lève, la
    route le nomme en français, et l'index n'est pas touché puisque
    l'exception n'atteint jamais sa pose. `decks_root()` — qui fait un
    `mkdir` — est appelé ici en connaissance de cause : un dossier de sortie
    irrécupérable doit lever de la même façon."""
    with os.scandir(decks_root()) as it:
        return [e for e in it if is_valid_did(e.name) and e.is_dir()]


def _mtime_meta(e) -> float:
    try:
        return os.stat(os.path.join(e.path, "meta.json")).st_mtime
    except OSError:
        return 0.0


def _trie(rows: list) -> list:
    """LE TRI, à UN SEUL endroit. `updated` n'a qu'une précision d'une
    seconde : le mtime de meta.json départage. Deux boucles jumelles auraient
    été deux tris à maintenir d'accord."""
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return [r[2] for r in rows]


def list_decks() -> list[dict]:
    """Tous les decks ENTIERS, plus récent d'abord.

    AUCUN INDEX ICI, ET C'EST ASSUMÉ : un index de quatre champs ne peut pas
    rendre un document complet, et mettre les documents en cache reviendrait à
    recopier le magasin à côté du magasin. Qui veut TOUT paye le balayage ; la
    route, elle, ne veut que les résumés."""
    rows = []
    for e in _dossiers_de_decks():
        doc = read_deck(e.name)
        if not doc:
            continue
        rows.append((doc.get("updated") or "", _mtime_meta(e), doc))
    return _trie(rows)


def list_deck_summaries() -> list[dict]:
    """Tous les decks en RÉSUMÉS de quatre champs, plus récent d'abord —
    servis par l'INDEX partout où le disque n'a pas bougé.

    UN STAT PAR JEU, ZÉRO OUVERTURE quand rien n'a changé. Les jeux dont
    (mtime, taille) concordent avec l'index en sortent ; les autres — inconnus,
    discordants, illisibles — sont RELUS par le chemin de lecture ORDINAIRE
    (`_lit_meta`, celui de `read_deck` à la réparation près), puis l'index est
    réécrit s'il a changé.

    LE PREMIER PASSAGE EST LE BALAYAGE D'AVANT, une fois. Ensuite l'index
    existe, et il SURVIT au redémarrage du backend — c'est le seul moyen que
    l'ouverture de la galerie ne repaye pas ses 13,8 s après chaque relance.

    L'index ne peut RIEN AJOUTER à la liste : elle ne sort jamais de ce que le
    balayage a réellement vu sur le disque. Une entrée pour un jeu disparu est
    donc muette (et s'efface à la réécriture), et un jeu absent de l'index est
    simplement relu."""
    connues, intact = _index_lu()
    neuves, rows = {}, []
    for e in _dossiers_de_decks():
        chemin = os.path.join(e.path, "meta.json")
        try:
            st = os.stat(chemin)
        except OSError:
            continue           # pas de meta.json : ce dossier n'est pas un jeu
        entree = _entree_a_jour(connues.get(e.name), st)
        if entree is not None:
            neuves[e.name] = entree
            rows.append((entree["updated"], st.st_mtime,
                         _resume_d_entree(e.name, entree)))
            continue
        doc, etat = _lit_meta(e.name)
        if doc is None:
            if etat == META_REFUS:
                # LE FICHIER EST SAIN, il s'est juste refusé à cet instant
                # (un `replace` le tenait). On sert ce que l'index SAIT —
                # vrai, peut-être d'une seconde — et l'entrée reste en place
                # pour que le passage suivant la revalide. On n'INVENTE rien :
                # un faux « Mon jeu » daté de maintenant prendrait la tête de
                # la galerie, devant le jeu qu'on vient de modifier.
                vieille = _entree_normalisee(connues.get(e.name))
                if vieille is not None:
                    neuves[e.name] = vieille
                    rows.append((vieille["updated"], st.st_mtime,
                                 _resume_d_entree(e.name, vieille)))
            continue        # disparu, ou refusé sans rien de connu à servir
        rows.append((doc.get("updated") or "", st.st_mtime, deck_summary(doc)))
        # L'EMPREINTE MISE EN CACHE EST CELLE D'AVANT LA LECTURE — `st`, jamais
        # un stat repris APRÈS — et l'ordre n'est pas une coquetterie. Une
        # écriture peut tomber pendant la lecture ; elle avance le mtime.
        #
        #   · enregistrée avec l'empreinte d'APRÈS, l'entrée porterait un
        #     contenu périmé sous une empreinte à jour, que plus AUCUN stat ne
        #     viendrait contredire : périmée pour toujours ;
        #   · enregistrée avec l'empreinte d'AVANT, la même course laisse une
        #     entrée que le prochain stat invalide d'office. Au pire une
        #     relecture de plus, jamais un mensonge.
        #
        # (Un second stat pour « vérifier » que rien n'a bougé n'ajouterait
        # RIEN : le banc de mutation l'a montré inobservable, parce que la
        # seule course qu'il attraperait est déjà celle du trou de tic nommé
        # plus haut — et dans ce trou-là, les deux stats sont d'accord.)
        fraiche = _entree_de_document(doc, st, etat == META_LU)
        if fraiche is not None:
            neuves[e.name] = fraiche
    # ON N'ÉCRIT QUE SI LE CACHE A CHANGÉ. La comparaison porte sur le
    # CONTENU, pas sur un drapeau « j'ai relu quelque chose » : un jeu
    # ILLISIBLE est relu à chaque balayage sans jamais entrer dans l'index —
    # avec un drapeau, sa seule présence ferait réécrire le fichier entier à
    # chaque ouverture de la galerie, pour rien.
    if neuves != connues or not intact:
        _index_ecrit(neuves)
    return _trie(rows)


def patch_deck(did: str, body: dict | None) -> dict | None:
    """Fusion PARTIELLE du document (autosave). None si le deck n'existe pas.

    `id`, `v` et `created` ne sont jamais repris du client.

    PARTIELLE veut dire : une clé ABSENTE du corps n'est pas touchée. Ni le
    bloc `format` (fusionné sur l'état actuel, cf. `normalize_format`), ni un
    sous-arbre de pièce. C'est ce qui rend deux onglets — ou deux des huit
    builders — inoffensifs l'un pour l'autre : l'écran n'envoie que ce qu'il a
    modifié (`saveBody`, core.js), et ce qu'il n'envoie pas survit.

    En revanche un sous-arbre PRÉSENT et bien formé est remplacé EN BLOC, pas
    fusionné : c'est `CF.patch` qui fusionne côté navigateur, et le sous-arbre
    envoyé ici est déjà son état complet. Fusionner une seconde fois ici
    rendrait la suppression d'une clé impossible.

    Un sous-arbre présent mais MAL FORMÉ (`null`, une liste, une chaîne) est
    IGNORÉ, pas appliqué : le vider effacerait le travail d'une pièce sur une
    faute de frappe d'un client. Pour vider `doc.face`, on envoie `{}`.
    """
    doc = read_deck(did)
    if doc is None:
        return None
    body = body if isinstance(body, dict) else {}
    if "name" in body:
        doc["name"] = clean_name(body.get("name"), fallback=doc["name"])
    if "format" in body:
        doc["format"] = normalize_format(body.get("format"), base=doc["format"])
    for mid in MODULE_IDS:
        if mid in body and isinstance(body.get(mid), dict):
            doc[mid] = body[mid]
    doc["updated"] = _now_iso()
    return write_deck(doc)


def duplicate_deck(did: str) -> dict | None:
    """Copie COMPLÈTE d'un deck : le document ET le dossier (spec §6.4).

    Une duplication copie TOUT, illustrations comprises — c'est
    « enregistrer comme modèle » qui les exclut. Le dossier d'un deck porte
    bien plus que `meta.json` : `texture/`, `solid/`, `gltf/`, `forge3d/`, le
    profil ICC de P7… Copier le seul document aurait rendu un deck qui
    S'OUVRE et dont la moitié des aperçus manquent, sans un message.

    `copytree` refuse une destination existante, et `new_did` ne rend qu'un
    identifiant libre : la copie ne peut pas écraser un voisin.

    LES BROUILLONS SONT EXCLUS, et c'est la seule exception au « tout » :
    `meta.json.<hex>.tmp` n'appartient à personne — c'est l'écriture d'un
    autre, en cours ou interrompue. Recopié, il transformait une épave en
    deux, puis en quatre au duplicata suivant.
    """
    doc = read_deck(did)
    if doc is None:
        return None
    src = deck_dir(did)
    neuf = new_did()
    shutil.copytree(src, deck_dir(neuf),
                    ignore=shutil.ignore_patterns("*.tmp"))
    doc["id"] = neuf
    doc["name"] = clean_name(f"copie de {doc['name']}")
    doc["created"] = doc["updated"] = _now_iso()
    return write_deck(doc)


def delete_deck(did: str) -> bool:
    try:
        d = deck_dir(did)
    except ValueError:
        return False
    if not d.is_dir():
        return False
    shutil.rmtree(d, ignore_errors=True)
    return not d.exists()


def _deck_or_404(did: str) -> dict:
    """Deck existant, ou l'erreur qui va bien. `did` hors
    ^deck_[0-9a-f]{8}$ = 400 (aucune traversée ne peut aller plus loin)."""
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return doc


# ── la coalescence des écritures ────────────────────────────────────────────
# UN VERROU PAR JEU, sur la route qui LIT-MODIFIE-ÉCRIT.
#
# `patch_deck` relit le document, y pose le sous-arbre reçu, et réécrit le
# tout. Deux requêtes qui arrivent ensemble lisent donc le MÊME document
# d'avant : la seconde à écrire efface le travail de la première, sans un
# conflit, sans un journal, sans un message. Mesuré 40 fois sur 40 sur deux
# sous-arbres DIFFÉRENTS — c'est-à-dire très exactement le cas que la
# docstring de `patch_deck` promettait sûr (« ce qu'il n'envoie pas survit »).
# Une prose qui promet plus que le code, c'est la pire espèce de faux.
#
# LE VERROU EST PAR JEU : deux onglets sur la même partie s'attendent le temps
# d'une écriture (~6 ms), deux jeux différents ne s'attendent JAMAIS. Il tient
# à travers l'`await` du `to_thread`, ce qui est tout l'intérêt — c'est
# pendant ce séjour dans le fil de travail que la course avait lieu.
#
# CE QU'IL NE COUVRE PAS, ET IL FAUT LE DIRE : il vit dans CE processus. Deux
# backends sur le même dossier, ou un script qui écrit à côté de l'app, se
# marchent encore dessus. C'est alors `write_deck` — atomique — qui garantit
# qu'aucun document ne sort TRONQUÉ, à défaut de garantir qu'aucun ne se perd.
_VERROUS: dict[str, asyncio.Lock] = {}
_VERROUS_EN_COURS: dict[str, int] = {}


@asynccontextmanager
async def _verrou_du_deck(did: str):
    """Le verrou d'un jeu, créé à la demande et RAMASSÉ par le dernier partant.

    Le ramassage n'est pas de la coquetterie : un backend qui voit passer deux
    mille jeux ne doit pas garder deux mille verrous. Il rend en plus le
    harnais de test honnête — un `asyncio.Lock` reste lié à la boucle qui l'a
    attendu, et une requête suivante, sous une AUTRE boucle, lèverait sur un
    verrou survivant. Ne rien laisser derrière soi, c'est ne rien confondre.

    Le dictionnaire n'a pas de garde : tout ceci vit dans la boucle
    d'événements, un seul fil, et rien n'est attendu entre le `get` et le
    `set`."""
    v = _VERROUS.get(did)
    if v is None:
        v = _VERROUS[did] = asyncio.Lock()
    _VERROUS_EN_COURS[did] = _VERROUS_EN_COURS.get(did, 0) + 1
    try:
        async with v:
            yield
    finally:
        reste = _VERROUS_EN_COURS[did] - 1
        if reste:
            _VERROUS_EN_COURS[did] = reste
        else:
            _VERROUS_EN_COURS.pop(did, None)
            _VERROUS.pop(did, None)


# ── routes ──────────────────────────────────────────────────────────────────
# /formats et /decks D'ABORD : Starlette apparie dans l'ordre de déclaration.

@router.get("/formats")
async def list_formats():
    """Le catalogue de géométrie, calculé — jamais une table recopiée à la
    main dans l'écran.

    C'est la moitié mesurable du domaine : `poker_us` doit sortir à
    825x1125 px de toile et 750x1050 px de rogne, comme nanDECK, avec un
    trait de coupe à 37,5 px. L'écran affiche ces chiffres tels quels ; il
    n'en recalcule aucun."""
    return {
        "formats": format_table(DEFAULT_DPI),
        "sheets": [
            {"id": sid, "label": SHEETS[sid]["label"],
             "size_mm": [round(v, 3) for v in SHEETS[sid]["size_mm"]],
             "px": {str(d): list(sheet_px(sid, d)) for d in DPI_CHOICES}}
            for sid in SHEETS
        ],
        "dpis": list(DPI_CHOICES),
        "dpi_default": DEFAULT_DPI,
        "fmt_default": DEFAULT_FMT,
        # LES CONSTANTES, pas leurs valeurs recopiées : une route dont le
        # docstring dit « calculé, jamais une table à la main » ne peut pas
        # servir 3.175 en littéral. Changer la constante changeait l'API et
        # laissait ce bloc mentir, sans qu'aucun test bronche.
        "bleed": {"metric_mm": BLEED_METRIC_MM,
                  "imperial_mm": BLEED_IMPERIAL_MM,
                  "max_mm": BLEED_MM_MAX},
        "limits": {"dpi": [DPI_MIN, DPI_MAX], "bleed_mm": [0.0, BLEED_MM_MAX],
                   "safe_mm": [0.0, SAFE_MM_MAX],
                   "corner_mm": [0.0, CORNER_MM_MAX]},
        "rule": RULE_TEXT,
    }


DECKS_LIMIT_DEFAULT = 100
DECKS_LIMIT_MIN = 1
DECKS_LIMIT_MAX = 500


def borne_limite(val) -> int:
    """`limit` RAMENÉ dans [1, 500] — jamais refusé, sauf s'il n'est pas un
    nombre (400 + phrase française, patron `_q_num`).

    LE CAS QUI JUSTIFIE LE PLANCHER N'EST PAS `0`, C'EST LE NÉGATIF : un
    `rows[:-5]` de Python ne rend pas une liste vide, il rend TOUTE LA LISTE
    MOINS LES CINQ DERNIERS. Sans plancher, demander −5 servirait donc PLUS de
    jeux que demander 24, et le poste à 2 195 jeux reprendrait ses ~13,8 Mo par
    la porte de derrière."""
    n = _q_num(val, "La limite")
    if n is None:
        return DECKS_LIMIT_DEFAULT
    return int(max(DECKS_LIMIT_MIN, min(DECKS_LIMIT_MAX, n)))


@router.get("/decks")
async def get_decks(limit: str | None = None):
    """Les jeux, plus récent d'abord, en RÉSUMÉS de quatre champs, BORNÉS.

    CHANGEMENT DE CONTRAT, ASSUMÉ ET DIT. La route servait tous les documents
    entiers ; elle sert désormais `{decks, total, limit}` où `decks` sont les
    quatre champs `id/name/created/updated` des `limit` plus récents. La
    raison est mesurée (voir `deck_summary`) : ~13,8 Mo pour une galerie qui
    affiche vingt-quatre lignes de quatre champs, soit 2 679 octets.

    `total` EST LA CONTREPARTIE DU PLAFOND, et il n'est pas décoratif : sans
    lui, un écran qui reçoit vingt-quatre jeux ne peut plus distinguer « ce
    backend en a vingt-quatre » de « il en a deux mille et vous en voyez
    vingt-quatre ». Le plafond sans le total serait un mensonge par omission.

    `limit` est RAMENÉ dans [1, 500], jamais refusé — c'est une commodité
    d'affichage, pas une contrainte métier ; et la valeur RETENUE repart dans
    la réponse, pour que l'appelant sache ce qu'il a vraiment obtenu. Seule
    une valeur qui n'est pas un nombre est un 400 (phrase française, patron
    `_q_num` — défini plus bas dans ce fichier, résolu à l'appel)."""
    n = borne_limite(limit)
    try:
        rows = await asyncio.to_thread(list_deck_summaries)
    except OSError as e:
        # UN BALAYAGE QUI N'A PAS EU LIEU N'EST PAS UN BALAYAGE VIDE. Servir
        # `{"decks": [], "total": 0}` en 200 sur un dossier illisible, c'est
        # dire à l'écran « vous n'avez aucun jeu » — un mensonge poli, et le
        # pire message possible pour qui vient d'en perdre deux mille.
        logger.exception("cards: listing des jeux impossible")
        raise HTTPException(500, "Liste des jeux impossible : lecture refusée "
                                 f"({e.strerror or 'E/S'})")
    return {"decks": rows[:n], "total": len(rows), "limit": n}


@router.post("/decks")
async def post_deck(body: dict | None = None):
    """Crée un deck. Corps {name?, format?, model?} — tout est facultatif.

    `model` INSTANCIE un modèle (spec §6.1) : le deck naît habillé, typographié
    et matiéré, puis il est ORDINAIRE — aucune référence au modèle n'est
    gardée. L'import de `models` est TARDIF, et c'est nécessaire : `models.py`
    importe CE fichier (il a besoin du magasin de decks), et `cards/__init__`
    charge `core` en premier. Un import en tête de module ferait un cycle.
    """
    body = body if isinstance(body, dict) else {}
    modele = body.get("model")
    if modele not in (None, ""):
        from .models import ECHO_MAX, instancier
        # CE QU'UN MESSAGE RECOPIE DU CLIENT SE BORNE. Sans cela, 3 000
        # caractères, du balisage ou un U+202E (qui renverse le sens de
        # lecture de la phrase qui suit) repartaient tels quels vers l'écran
        # qui les affiche. Même règle que les autres échos du lab.
        echo = str(modele)[:ECHO_MAX]
        try:
            doc = await asyncio.to_thread(instancier, modele, body.get("name"))
        except KeyError:
            raise HTTPException(
                404, f"Modèle inconnu : « {echo} » — la liste est servie "
                     "par GET /api/cards/models")
        except ValueError:
            # Le détail (nom de fichier, position JSON) va au journal : il
            # peut porter un chemin, donc le nom de compte.
            logger.exception("cards: modèle perso illisible")
            raise HTTPException(
                400, f"Modèle illisible : « {echo} » — son fichier n'est pas "
                     "un JSON valide")
        except OSError as e:
            logger.exception("cards: instanciation de modèle impossible")
            raise HTTPException(
                500, "Création du deck impossible : écriture refusée "
                     f"({e.strerror or 'E/S'})")
        return {"deck": doc}
    try:
        doc = await asyncio.to_thread(create_deck, body.get("name") or "Mon jeu",
                                      body.get("format"))
    except OSError as e:
        logger.exception("cards: création de deck impossible")
        raise HTTPException(500, "Création du deck impossible : écriture "
                                 f"refusée ({e.strerror or 'E/S'})")
    return {"deck": doc}


@router.post("/decks/{did}/duplicate")
async def duplicate_deck_route(did: str):
    """Duplique un deck, dossier compris (spec §6.4). Trois segments : aucune
    chance de tomber dans le joker `/{did}`, qui n'en apparie qu'un."""
    _deck_or_404(did)
    try:
        doc = await asyncio.to_thread(duplicate_deck, did)
    except OSError as e:
        logger.exception("cards: duplication impossible")
        raise HTTPException(500, "Duplication du deck impossible : copie "
                                 f"refusée ({e.strerror or 'E/S'})")
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return {"deck": doc}


@router.get("/{did}")
async def get_deck(did: str):
    return {"deck": _deck_or_404(did)}


@router.patch("/{did}")
async def patch_deck_route(did: str, body: dict | None = None):
    """Autosave de l'écran (spec 2.2 §10). Fusion partielle de
    {name?, format?, face?, frame?, type?, data?, solid?, texture?, print?,
    gltf?}. Toute clé étrangère est ignorée, toute valeur invalide reprend
    son défaut — jamais d'erreur 500.

    « JAMAIS 500 » VALAIT POUR LE CORPS, PAS POUR LE DISQUE, et c'était le
    trou : cette route était la SEULE des trois qui écrivent à ne pas border
    l'`OSError`. Un refus d'écriture y ressortait en trace nue, quand ses deux
    sœurs (`post_deck`, `duplicate_deck_route`) disent depuis toujours ce que
    l'OS a refusé, en français et SANS le chemin absolu (donc sans le nom de
    compte — la jurisprudence de la fuite).

    LA FUSION EST SÉRIALISÉE PAR JEU (`_verrou_du_deck`). Sans cela, deux
    requêtes qui arrivent ensemble lisent le MÊME document d'avant et la
    seconde à écrire efface le sous-arbre de la première — 40 fois sur 40,
    en silence, contre la promesse même de la fusion partielle."""
    _deck_or_404(did)
    # LE VERROU ENGLOBE LE LIRE-MODIFIER-ÉCRIRE ENTIER, `to_thread` compris :
    # c'est PENDANT ce séjour dans le fil de travail que la course avait lieu.
    # Tout ce qui suit reste DEDANS — une branche sortie d'un cran ferait
    # retomber la garde une variable trop loin, ce que ce dépôt a déjà payé.
    async with _verrou_du_deck(did):
        try:
            doc = await asyncio.to_thread(patch_deck, did, body)
        except OSError as e:
            logger.exception("cards: enregistrement du deck impossible")
            raise HTTPException(
                500, "Enregistrement du deck impossible : écriture refusée "
                     f"({e.strerror or 'E/S'})")
        if doc is None:
            raise HTTPException(404, "Deck introuvable")
        return {"deck": doc}


@router.delete("/{did}")
async def delete_deck_route(did: str):
    _deck_or_404(did)
    ok = await asyncio.to_thread(delete_deck, did)
    if not ok:
        raise HTTPException(409, "Le deck n'a pas pu être supprimé")
    return {"ok": True}


def _q_num(val, what: str) -> float | None:
    """Nombre venant de la CHAÎNE DE REQUÊTE. Les paramètres sont déclarés en
    `str` exprès : typés `int`/`float`, FastAPI rendait un 422 avec une charge
    pydantic EN ANGLAIS là où la spec 2.5 impose 400 + une phrase en
    français — et ce lab est francophone de bout en bout."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(400, f"{what} doit être un nombre (reçu {val!r})")
    if not math.isfinite(f):
        raise HTTPException(400, f"{what} doit être un nombre fini (reçu {val!r})")
    return f


@router.get("/{did}/geom")
async def get_deck_geom(did: str, fmt: str | None = None,
                        dpi: str | None = None,
                        bleed_mm: str | None = None,
                        safe_mm: str | None = None,
                        corner_mm: str | None = None):
    """Géométrie du deck — LA vérité, celle que l'écran affiche et que
    l'export applique. Les paramètres facultatifs simulent un changement de
    format sans l'enregistrer (aperçu du sélecteur)."""
    d_num = _q_num(dpi, "Le DPI")
    dpi = None if d_num is None else int(d_num)
    bleed_mm = _q_num(bleed_mm, "Le fond perdu")
    safe_mm = _q_num(safe_mm, "La zone de sécurité")
    corner_mm = _q_num(corner_mm, "Le rayon de coin")
    doc = _deck_or_404(did)
    f = dict(doc["format"])
    demande = str(fmt).strip().lower() if fmt is not None else None
    if demande and demande != f["fmt"]:
        # CHANGER DE FORMAT REPREND SON FOND PERDU NATIF : 0.125 in en
        # impérial, 3 mm en métrique. Sans cette reprise, prévisualiser
        # `poker_us` depuis un deck `poker_eu` garderait 3 mm et sortirait
        # 821x1121 au lieu de 825x1125 — la parité nanDECK tomberait sur un
        # simple aperçu. Un `bleed_mm`/`safe_mm` passé EXPLICITEMENT reste
        # prioritaire : il est appliqué juste après.
        try:
            f["bleed_mm"] = f["safe_mm"] = native_bleed_mm(demande)
        except KeyError:
            pass          # format inconnu : geom() lèvera, avec son message
    for key, val in (("fmt", demande), ("dpi", dpi), ("bleed_mm", bleed_mm),
                     ("safe_mm", safe_mm), ("corner_mm", corner_mm)):
        if val is not None:
            f[key] = val
    try:
        g = geom(f["fmt"], f["dpi"], f["bleed_mm"], f["safe_mm"], f["corner_mm"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"geom": g.to_dict()}
