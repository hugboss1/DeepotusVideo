# -*- coding: utf-8 -*-
"""Le filtre gratuit du flux News (plan 2026-09-03, lot 1, P1).

Rien ne part vers un fournisseur avant que ce module ait parle : mots-cles,
listes noires (sources, mots), fenetre de fraicheur — puis, tache 2, le
dedoublonnage par titre presque identique et par recouvrement de contenu.

Tout est stdlib (`difflib`, `re`, `unicodedata`, `json`) : le python EMBARQUE
n'a ni numpy ni scikit-learn, et un tri qui coute un appel LLM par article
n'est pas un tri « gratuit ».

Les reglages vivent a cote des sources et du cache, sous le dossier `news/`
des donnees utilisateur : ils survivent aux mises a jour.
"""
import difflib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from app.config import settings

FRAICHEUR_MAX_H = 24 * 30      # un mois : la borne haute d'Inoreader
FRAICHEUR_MIN_H = 1

REGLAGES_DEFAUT: dict = {
    "mots_cles": [],           # vide = tout passe l'etape mots-cles
    "sources_noires": [],
    "mots_noirs": [],
    "fraicheur_h": 48,
}

# Mots vides FR + EN. Volontairement courte : elle sert a comparer des TITRES,
# pas a faire de la linguistique.
MOTS_VIDES = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "as", "at",
    "by", "with", "from", "after", "over", "is", "are", "was", "were", "be",
    "been", "has", "have", "had", "that", "this", "it", "its", "his", "her",
    "they", "their", "he", "she", "said", "says", "but", "not", "also", "new",
    "up", "out", "into", "than", "then", "who", "will",
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "pour",
    "sur", "dans", "que", "qui", "au", "aux", "ses", "son", "sa", "est",
    "sont", "ont", "plus", "ne", "pas",
}


_SUFFIXES = ("ing", "ed", "es", "s")


def _tronc(mot: str) -> str:
    """Tronconnage LEGER : `prices` -> `price`, `climbs` -> `climb`.

    Mesure du 03/09 : sans lui, « Oil prices climb on supply fears » contre
    « Oil price climbs on supply fear » donnait un Jaccard de 0,250 — un
    doublon evident manque, parce que trois jetons singulier/pluriel sont
    trois jetons distincts pour un ensemble. Avec lui la paire monte a 0,667,
    et AUCUNE paire non-doublon ne se rapproche.

    Une racine de deux lettres est laissee intacte : `es` -> `es`, pas `""`.
    """
    for suf in _SUFFIXES:
        if len(mot) > len(suf) + 2 and mot.endswith(suf):
            return mot[:-len(suf)]
    return mot


def jetons(texte: str) -> list[str]:
    """Jetons normalises : sans accents, en minuscules, sans mots vides,
    tronconnes.

    UN SEUL tokeniseur pour tout le module — titres et corps —, sinon les
    seuils mesures dans le plan ne veulent plus rien dire. Les mots vides sont
    filtres AVANT le tronconnage : la liste est ecrite en formes pleines.
    """
    t = unicodedata.normalize("NFKD", texte or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return [_tronc(w) for w in re.findall(r"[a-z0-9]+", t)
            if w not in MOTS_VIDES and len(w) > 1]


def chemin_reglages() -> Path:
    d = settings.outputs_path.parent / "news"
    d.mkdir(parents=True, exist_ok=True)
    return d / "filtre.json"


def _normaliser_liste(v) -> list[str]:
    if not isinstance(v, list):
        return []
    out: list[str] = []
    for x in v:
        s = " ".join(str(x or "").split()).strip().lower()
        if s and s not in out:
            out.append(s)
    return out


def _propre(brut: dict) -> dict:
    h = brut.get("fraicheur_h", REGLAGES_DEFAUT["fraicheur_h"])
    try:
        h = int(h)
    except (TypeError, ValueError):
        h = REGLAGES_DEFAUT["fraicheur_h"]
    h = max(FRAICHEUR_MIN_H, min(FRAICHEUR_MAX_H, h))
    return {
        "mots_cles": _normaliser_liste(brut.get("mots_cles")),
        "sources_noires": _normaliser_liste(brut.get("sources_noires")),
        "mots_noirs": _normaliser_liste(brut.get("mots_noirs")),
        "fraicheur_h": h,
    }


def lire_reglages() -> dict:
    p = chemin_reglages()
    if not p.is_file():
        return dict(REGLAGES_DEFAUT)
    try:
        brut = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("news filtre.json illisible - retour aux defauts")
        return dict(REGLAGES_DEFAUT)
    if not isinstance(brut, dict):
        return dict(REGLAGES_DEFAUT)
    return _propre(brut)


def ecrire_reglages(brut: dict) -> dict:
    """Ecrit les reglages NORMALISES (minuscules, sans doublons, fraicheur
    bornee) et rend ce qui a ete ecrit. L'ecriture passe par un fichier
    temporaire : une coupure ne laisse pas un JSON tronque."""
    propre = _propre(brut if isinstance(brut, dict) else {})
    p = chemin_reglages()
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(propre, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(p)
    return propre


def _quand(item: dict) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(item.get("published") or ""))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _texte(item: dict) -> str:
    return " ".join([str(item.get("title") or ""),
                     str(item.get("summary") or ""),
                     str(item.get("essence") or "")])


def motif_de_rejet(item: dict, reglages: dict,
                   maintenant: datetime) -> str | None:
    """Le PREMIER motif qui fait tomber l'article, ou None s'il passe.

    L'ordre est celui du cout : source (une comparaison), mots noirs (un
    parcours), mots-cles (un parcours), fraicheur (une date). Le motif est
    rendu tel quel a l'ecran : un article ecarte doit dire pourquoi.
    """
    src = " ".join(str(item.get("source_name") or "").split()).lower()
    if any(n in src for n in reglages["sources_noires"]):
        return "source sur liste noire"
    corpus = _texte(item).lower()
    if any(n in corpus for n in reglages["mots_noirs"]):
        return "mot sur liste noire"
    cles = reglages["mots_cles"]
    if cles and not any(c in corpus for c in cles):
        return "hors mots-cles"
    d = _quand(item)
    if d is not None:
        age_h = (maintenant - d).total_seconds() / 3600.0
        if age_h > reglages["fraicheur_h"]:
            return "hors fenetre de fraicheur"
    return None


def filtrer(items: list[dict], reglages: dict | None = None, *,
            maintenant: str | None = None) -> tuple[list[dict], dict]:
    """Rend (gardes, {id: motif de rejet}). Ne mute jamais les articles."""
    reglages = _propre(reglages) if reglages else lire_reglages()
    if maintenant:
        ref = datetime.fromisoformat(maintenant)
        if not ref.tzinfo:
            ref = ref.replace(tzinfo=timezone.utc)
    else:
        ref = datetime.now(timezone.utc)
    gardes: list[dict] = []
    motifs: dict = {}
    for it in items:
        m = motif_de_rejet(it, reglages, ref)
        if m:
            motifs[it.get("id")] = m
        else:
            gardes.append(it)
    return gardes, motifs


# ── Le doublon : titre presque identique (Inoreader) ou recouvrement de
#    contenu au-dela de 85 % (Feedly). Seuils MESURES le 03/09/2026 sur 21
#    paires de titres et 4 paires de corps (plan, « References verifiees ») :
#    le vide mesure est ]0,711 ; 0,753[ sur le ratio et ]0,333 ; 0,417[ sur
#    le Jaccard. La paire la plus dure (« Dencun goes live » contre « gas
#    fees fall after Dencun ») rate les deux.
#    Les deux conditions sont exigees ENSEMBLE. Sur les paires REELLES chaque
#    signal suffirait ; la conjonction est une marge contre une paire qui ne
#    tripperait qu'un signal, et le banc porte deux paires synthetiques pour
#    l'exercer — sans elles, remplacer ce `and` par un `or` ne ferait rougir
#    aucun test.

SEUIL_TITRE = 0.735      # SequenceMatcher sur les jetons TRIES
SEUIL_JETONS = 0.375     # Jaccard sur les jetons du titre
SEUIL_CONTENU = 0.85     # containment sur le corps (parite Feedly)
CORPS_MIN_JETONS = 25    # sous ce compte, un corps ne prouve rien


def ratio_titres(a: str, b: str) -> float:
    """Similarite de deux titres, ordre des mots neutralise.

    Les jetons sont TRIES avant comparaison : « X after Y » et « Y, X »
    doivent se ressembler, sinon une reprise de depeche remontee dans un
    autre ordre passerait au travers.
    """
    return difflib.SequenceMatcher(
        None, " ".join(sorted(jetons(a))), " ".join(sorted(jetons(b)))
    ).ratio()


def jaccard_titres(a: str, b: str) -> float:
    A, B = set(jetons(a)), set(jetons(b))
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def titres_presque_identiques(a: str, b: str) -> bool:
    return (ratio_titres(a, b) >= SEUIL_TITRE
            and jaccard_titres(a, b) >= SEUIL_JETONS)


def recouvrement(a: str, b: str) -> float:
    """Containment : la part du PLUS COURT des deux corps que l'autre couvre.

    Pas un Jaccard : la reprise ajoute un chapeau et coupe une phrase, donc
    les deux corps n'ont pas la meme longueur et l'union punirait la reprise.
    """
    A, B = set(jetons(a)), set(jetons(b))
    if not A or not B:
        return 0.0
    return len(A & B) / min(len(A), len(B))


def contenus_se_recouvrent(a: str, b: str) -> bool:
    if len(set(jetons(a))) < CORPS_MIN_JETONS:
        return False
    if len(set(jetons(b))) < CORPS_MIN_JETONS:
        return False
    return recouvrement(a, b) >= SEUIL_CONTENU


def _corps(item: dict) -> str:
    return str(item.get("essence") or item.get("summary") or "")


# Mesure du 28/09/2026 sur le cache reel (300 articles, 18 sources) : la
# version par paires retokenisait les deux titres et les deux corps A CHAQUE
# comparaison -- 38,7 s sous profilage, 12,3 s sans, dont ~20 s dans jetons()
# et ~16 s dans difflib. Au rafraichissement elle tourne AVANT le plafond (jusqu'a
# 18 x 25 = 450 articles). D'ou une signature calculee UNE fois par article, et
# le Jaccard (ensembles) teste AVANT le ratio difflib : la conjonction de
# titres_presque_identiques rend ce court-circuit exact. Memes decisions que les
# fonctions par paires (banc test_news_filter : equivalence sur le cache reel).

def _signature(item: dict) -> tuple:
    """(titre en jetons tries, ensemble des jetons du titre, ensemble du corps)."""
    t = jetons(item.get("title") or "")
    return " ".join(sorted(t)), set(t), set(jetons(_corps(item)))


def _titres_sig(a: tuple, b: tuple) -> bool:
    """titres_presque_identiques(a, b) sur signatures, Jaccard d'abord."""
    A, B = a[1], b[1]
    if not A or not B or len(A & B) / len(A | B) < SEUIL_JETONS:
        return False
    return difflib.SequenceMatcher(None, a[0], b[0]).ratio() >= SEUIL_TITRE


def _corps_sig(a: tuple, b: tuple) -> bool:
    """contenus_se_recouvrent(a, b) sur signatures."""
    A, B = a[2], b[2]
    if len(A) < CORPS_MIN_JETONS or len(B) < CORPS_MIN_JETONS:
        return False
    return len(A & B) / min(len(A), len(B)) >= SEUIL_CONTENU


def dedoublonner(items: list[dict]) -> tuple[list[dict], dict]:
    """Fond les articles qui racontent la meme chose.

    Rend (gardes, {id fondu: id gardant}). Le gardant est le PLUS RECENT du
    groupe ; il porte une cle `doublons` : la liste des articles fondus
    (media, titre, lien), qui alimente la ligne de sources de la legende
    (tache 9) et l'equilibre des sources (tache 8).

    Deux articles de la MEME source ne sont jamais fondus : un fil qui se
    republie releve du doublon d'identifiant, deja traite par
    `news_service._refresh_blocking`.
    """
    ordonnes = sorted(items, key=lambda x: str(x.get("published") or ""),
                      reverse=True)
    gardes: list[dict] = []
    sigs: list[tuple] = []
    fondus: dict = {}
    for it in ordonnes:
        s_it = _signature(it)
        cible = None
        for g, s_g in zip(gardes, sigs):
            if g.get("source_id") and g.get("source_id") == it.get("source_id"):
                continue
            if _titres_sig(s_g, s_it) or _corps_sig(s_g, s_it):
                cible = g
                break
        if cible is None:
            copie = dict(it)
            copie["doublons"] = []
            gardes.append(copie)
            sigs.append(s_it)
        else:
            cible["doublons"].append({
                "source_name": it.get("source_name") or "",
                "title": it.get("title") or "",
                "link": it.get("link") or "",
            })
            fondus[it.get("id")] = cible.get("id")
    return gardes, fondus
