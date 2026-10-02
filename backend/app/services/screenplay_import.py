"""Tâche #64 (plan chapitres T12, 02/10/2026) — lire un scénario Fountain (.fountain/.txt) ou Final Draft (.fdx) et
le rendre en SCÈNES de l'atelier. PUR : ni base, ni réseau, aucune dépense.

Un seul lecteur : le FDX est d'abord converti en Fountain, puis lu comme tel.

Ce que le plan du 03/09 faisait faux (mesuré le 02/10) et que ce module corrige :
  - le VOCABULAIRE : l'atelier ne connaît que INT / EXT / INT/EXT et JOUR / NUIT / AUBE / CRÉPUSCULE / MATIN / SOIR, et
    `PUT /scenes` réécrit la slugline avec eux à la première édition. DAY, NIGHT, LATER… sont TRADUITS ; un moment
    inconnu devient JOUR et l'original est rendu (`moment_original`, noté par la route dans les notes caméra) ;
  - FDX : seuls les paragraphes de <Content> (pas la page de titre), le dialogue double lu UNE fois, une action en
    capitales forcée en action (`!`), un « . » seul n'est jamais une en-tête ;
  - Fountain : en-têtes insensibles à la casse, `@Nom`, `^` du dialogue double ôté AVANT l'extension, numéros de scène
    `#1A#` ôtés du lieu, page de titre sans ligne vide, valeurs indentées, fins de ligne CR seules ;
  - un texte SANS aucune en-tête n'est pas un scénario (refus) ; le texte avant la première en-tête (le « FADE IN: »)
    est rattaché à la première scène, et c'est dit ;
  - encodage : UTF-8 (BOM compris), sinon cp1252 — jamais latin-1, qui « réussit » toujours et garde des contrôles ;
  - notes [[ ]], boneyard /* */, sections #, synopsis = et sauts de page === sont écartés du texte et COMPTÉS.
Les transitions (CUT TO:, > …) restent dans le texte ; c'est la voix-off qui ne les lit pas (manuscript_agent).
"""
from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET

INT_EXT = ("INT", "EXT", "INT/EXT")
MOMENTS = ("JOUR", "NUIT", "AUBE", "CRÉPUSCULE", "MATIN", "SOIR")

_PREFIXES = [  # (motif, int_ext) — le plus long d'abord ; insensible à la casse
    (r"INT\.?\s*/\s*EXT\.?", "INT/EXT"), (r"EXT\.?\s*/\s*INT\.?", "INT/EXT"), (r"I\s*/\s*E\.?", "INT/EXT"),
    (r"INT\.?-EXT\.?", "INT/EXT"), (r"INT\.", "INT"), (r"EXT\.", "EXT"), (r"EST\.", "EXT"),
    (r"INT(?=\s)", "INT"), (r"EXT(?=\s)", "EXT"), (r"EST(?=\s)", "EXT"),
]
_EN_TETE = re.compile(r"^\s*(" + "|".join(m for m, _ in _PREFIXES) + r")\s*(.*)$", re.IGNORECASE)

_MOMENTS_EXACTS = {
    "JOUR": "JOUR", "DAY": "JOUR", "DAYTIME": "JOUR", "MIDI": "JOUR", "NOON": "JOUR", "APRES-MIDI": "JOUR",
    "AFTERNOON": "JOUR",
    "NUIT": "NUIT", "NIGHT": "NUIT", "MIDNIGHT": "NUIT", "MINUIT": "NUIT",
    "AUBE": "AUBE", "DAWN": "AUBE", "SUNRISE": "AUBE", "LEVER DU JOUR": "AUBE", "LEVER DU SOLEIL": "AUBE",
    "CREPUSCULE": "CRÉPUSCULE", "DUSK": "CRÉPUSCULE", "SUNSET": "CRÉPUSCULE", "TWILIGHT": "CRÉPUSCULE",
    "COUCHER DU SOLEIL": "CRÉPUSCULE", "TOMBEE DE LA NUIT": "CRÉPUSCULE",
    "MATIN": "MATIN", "MORNING": "MATIN", "MATINEE": "MATIN",
    "SOIR": "SOIR", "EVENING": "SOIR", "SOIREE": "SOIR",
}
_MOTS_CLES = (("NUIT", "NUIT"), ("NIGHT", "NUIT"), ("AUBE", "AUBE"), ("DAWN", "AUBE"), ("CREPUSCULE", "CRÉPUSCULE"),
              ("DUSK", "CRÉPUSCULE"), ("SUNSET", "CRÉPUSCULE"), ("MATIN", "MATIN"), ("MORNING", "MATIN"),
              ("SOIR", "SOIR"), ("EVENING", "SOIR"), ("JOUR", "JOUR"), ("DAY", "JOUR"))
# un mot d'enchaînement : le moment est celui de la scène précédente (« CONTINUOUS », « LATER », « SAME »…)
_ENCHAINEMENTS = ("CONTINUOUS", "CONTINUOUSLY", "CONTINU", "CONTINUE", "LATER", "PLUS TARD", "SAME", "MOMENTS LATER",
                  "MEME MOMENT", "SUITE")

_TITRE_CLE = re.compile(r"^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ ]{0,30}):\s*(.*)$")
# les clés de page de titre de la spécification (et leurs équivalents français) : « FADE IN: » n'en est pas une
_CLES_TITRE = {"TITLE", "CREDIT", "AUTHOR", "AUTHORS", "SOURCE", "DRAFT DATE", "DATE", "CONTACT", "COPYRIGHT", "NOTES",
               "REVISION", "TITRE", "AUTEUR", "AUTEURS", "AUTEUR(S)", "D'APRES", "VERSION"}
_NUMERO = re.compile(r"\s*#[^#\s]+#\s*$")
_EXTENSION = re.compile(r"\s*\(([^)]*)\)\s*$")
_TRANSITION = re.compile(r"^[A-ZÀ-Ü0-9 .'’\-]+(?:TO:|IN:|OUT[.:]?)$")


def _plie(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").upper().strip()


def decoder(data: bytes) -> str:
    """UTF-8 (BOM ôté), sinon cp1252 ; fins de ligne CRLF et CR seules ramenées à LF."""
    try:
        t = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        t = data.decode("cp1252", errors="replace")
    return t.replace("\r\n", "\n").replace("\r", "\n")


def moment(brut: str, precedent: str | None = None) -> tuple[str, str | None]:
    """(moment de l'atelier, original s'il n'a pas été traduit EXACTEMENT — à noter), jamais hors de MOMENTS."""
    p = re.sub(r"\s+", " ", _plie(brut).replace("’", "'").strip(" .-")).replace("APRES MIDI", "APRES-MIDI")
    if not p:
        return "JOUR", None                      # aucun moment écrit : JOUR (décision du 02/10), rien à noter
    if p in _MOMENTS_EXACTS:
        return _MOMENTS_EXACTS[p], None
    for cle, m in _MOTS_CLES:
        if re.search(rf"\b{cle}\b", p):
            return m, brut.strip()
    if any(p.startswith(e) for e in _ENCHAINEMENTS) and precedent:
        return precedent, brut.strip()
    return "JOUR", brut.strip()


def en_tete(ligne: str, precedent: str | None = None) -> dict | None:
    """Une ligne d'en-tête -> {int_ext, lieu, moment, moment_original, ie_force} ; None si ce n'en est pas une.
    Forcée par « . » (pas « .. ») : INT par défaut, et c'est dit (`ie_force`)."""
    s = _NUMERO.sub("", ligne.strip())
    ie, reste, force = None, None, False
    if s.startswith(".") and not s.startswith("..") and re.search(r"\w", s[1:]):
        reste, force = s[1:].strip(), True
        m = _EN_TETE.match(reste)
        if m:
            reste = m.group(2)
            ie = next(v for motif, v in _PREFIXES if re.fullmatch(motif, m.group(1).strip(), re.IGNORECASE))
            force = False
    else:
        m = _EN_TETE.match(s)
        if not m or not m.group(2).strip():
            return None
        reste = m.group(2)
        ie = next(v for motif, v in _PREFIXES if re.fullmatch(motif, m.group(1).strip(), re.IGNORECASE))
    reste = reste.strip(" .")
    lieu, brut = reste, ""
    if " - " in reste or " – " in reste or " — " in reste:
        morceaux = re.split(r"\s+[-–—]\s+", reste)
        lieu, brut = " - ".join(morceaux[:-1]).strip(), morceaux[-1].strip()
    mo, orig = moment(brut, precedent)
    lieu = lieu.strip(" .-") or "LIEU"
    return {"int_ext": ie or "INT", "lieu": lieu.upper(), "moment": mo, "moment_original": orig, "ie_force": force}


def slugline(t: dict) -> str:
    return f"{t['int_ext']}. {t['lieu']} - {t['moment']}"


def _ote(texte: str, motif: str, compteur: dict, cle: str) -> str:
    def rempl(m):
        compteur[cle] = compteur.get(cle, 0) + 1
        return ""
    return re.sub(motif, rempl, texte, flags=re.DOTALL)


def _cue(ligne: str) -> str | None:
    """Le nom d'une réplique (sans `@`, `^` ni extension), ou None. Capitales exigées, sauf `@` qui force."""
    s = ligne.strip()
    if not s or s.startswith(("!", ">", "~", "=", "#", ".")):
        return None
    force = s.startswith("@")
    if force:
        s = s[1:]
    s = s.rstrip().rstrip("^").rstrip()
    s = _EXTENSION.sub("", s).strip()
    if not s or len(s) > 40:
        return None
    if not force and (not re.search(r"[A-Za-zÀ-ÿ]", s) or s != s.upper() or _TRANSITION.match(s) or s.endswith(":")):
        return None
    return s


def lire_fountain(texte: str) -> dict:
    """{titre, meta, scenes: [{int_ext, lieu, moment, moment_original, ie_force, slugline, texte, personnages}],
    ignores: {cle: n}, prologue: bool}. ValueError si aucune en-tête de scène."""
    ignores: dict = {}
    t = _ote(texte, r"/\*.*?\*/", ignores, "boneyard")
    t = _ote(t, r"\[\[.*?\]\]", ignores, "notes")
    lignes = t.split("\n")
    # page de titre : des paires « Clé: valeur » en tête (valeurs indentées en continuation), jusqu'à la ligne vide
    # OU jusqu'à la première ligne qui n'en est pas une (sans ligne vide, la 1re en-tête n'est plus avalée)
    meta, i, cle = {}, 0, None
    while i < len(lignes) and not lignes[i].strip():
        i += 1
    debut = i
    while i < len(lignes):
        l = lignes[i]
        if not l.strip():
            break
        m = _TITRE_CLE.match(l)
        if m and _plie(m.group(1)) in _CLES_TITRE:
            cle = m.group(1).strip().lower()
            meta[cle] = m.group(2).strip()
        elif cle and (l.startswith(("   ", "\t"))):
            meta[cle] = (meta[cle] + " " + l.strip()).strip()
        else:
            break
        i += 1
    if not meta:
        i = debut
    scenes, courant, prologue, precedent = [], None, [], None
    for k in range(i, len(lignes)):
        l = lignes[k]
        s = l.strip()
        avant_vide = k == i or not lignes[k - 1].strip()
        if avant_vide and s:                     # une ligne « ! » ne peut pas être une en-tête (_EN_TETE)
            tete = en_tete(s, precedent)
            if tete:
                courant = {**tete, "slugline": slugline(tete), "lignes": [], "personnages": []}
                precedent = tete["moment"]
                scenes.append(courant)
                continue
        if s.startswith("#"):
            ignores["sections"] = ignores.get("sections", 0) + 1
            continue
        if s.startswith("=") and not s.startswith("==="):
            ignores["synopsis"] = ignores.get("synopsis", 0) + 1
            continue
        if re.fullmatch(r"={3,}", s):
            ignores["sauts_de_page"] = ignores.get("sauts_de_page", 0) + 1
            continue
        nom = _cue(s) if avant_vide and k + 1 < len(lignes) and lignes[k + 1].strip() else None
        if nom:
            ext = _EXTENSION.search(s.lstrip("@").rstrip().rstrip("^").rstrip())
            l = nom.upper() + (f" ({ext.group(1).strip()})" if ext else "")
            cible = courant["personnages"] if courant else None
            if cible is not None and _plie(nom) not in [_plie(p) for p in cible]:
                cible.append(nom)
        (courant["lignes"] if courant else prologue).append(l.rstrip())
    if not scenes:
        raise ValueError("Aucune en-tête de scène (INT. / EXT. / « .LIEU ») : ce n'est pas un scénario Fountain.")
    pro = "\n".join(prologue).strip()
    if pro:
        scenes[0]["lignes"] = pro.split("\n") + [""] + scenes[0]["lignes"]
    for sc in scenes:
        sc["texte"] = re.sub(r"\n{3,}", "\n\n", "\n".join(sc.pop("lignes")).strip("\n")).strip()
    return {"titre": meta.get("title", ""), "meta": meta, "scenes": scenes, "ignores": ignores, "prologue": bool(pro)}


# ─────────────────────────────────────────── Final Draft (.fdx) ───────────────────────────────────────────

def _texte(p) -> str:
    return "".join((t.text or "") for t in p.findall("Text")).strip()


def fdx_vers_fountain(data: bytes) -> tuple[str, dict]:
    """(texte Fountain, ignores) d'un .fdx. Refuse tout DOCTYPE (aucune entité) ; ne lit que <Content>."""
    tete = data[:65536]
    if b"<!DOCTYPE" in tete.upper() or b"<!ENTITY" in tete.upper():
        raise ValueError("FDX refusé : DOCTYPE/ENTITY interdits.")
    try:
        racine = ET.fromstring(data)
    except ET.ParseError as e:
        raise ValueError(f"FDX illisible : {e}")
    if racine.tag != "FinalDraft":
        raise ValueError("Ce n'est pas un fichier Final Draft (racine <FinalDraft> absente).")
    ignores: dict = {}
    titre = ""
    for p in racine.findall("./TitlePage/Content/Paragraph"):
        if _texte(p):
            titre = _texte(p)
            break
    contenu = racine.find("Content")
    paras = []
    for p in (contenu.findall("Paragraph") if contenu is not None else []):
        dd = p.find("DualDialogue")
        if dd is not None:                    # le dialogue double : SES paragraphes, une fois (pas l'enveloppe)
            paras += dd.findall("Paragraph")
        else:
            paras.append(p)
    blocs: list[str] = []
    dernier = None
    for p in paras:
        ty, tx = (p.get("Type") or "General"), _texte(p)
        if not tx:
            continue
        dans_replique = dernier in ("Character", "Parenthetical", "Dialogue") and bool(blocs)
        if ty == "Scene Heading":
            if not re.search(r"\w", tx):
                ignores["en_tetes_vides"] = ignores.get("en_tetes_vides", 0) + 1
                continue
            blocs.append(("" if _EN_TETE.match(tx) else ".") + tx)
        elif ty in ("Action", "General", "Shot"):
            douteux = bool((tx == tx.upper() and re.search(r"[A-Za-zÀ-ÿ]", tx)) or _EN_TETE.match(tx) or tx.startswith("."))
            blocs.append(("!" if douteux else "") + tx)
        elif ty == "Character":
            blocs.append(tx.upper())
        elif ty in ("Parenthetical", "Dialogue"):
            ligne = (tx if tx.startswith("(") else f"({tx})") if ty == "Parenthetical" else tx
            if dans_replique:
                blocs[-1] += "\n" + ligne
            else:
                blocs.append(ligne)
        elif ty == "Transition":
            u = tx.upper()
            blocs.append(u if _TRANSITION.match(u) else "> " + u)
        else:
            ignores[ty] = ignores.get(ty, 0) + 1
            continue
        dernier = ty
    entete = f"Title: {titre}\n\n" if titre else ""
    return entete + "\n\n".join(blocs) + "\n", ignores


def lire(data: bytes, nom: str = "") -> dict:
    """Le point d'entrée : FDX (par l'extension OU la signature <FinalDraft) ou Fountain. + `format`."""
    debut = data[:2048].lstrip(b"\xef\xbb\xbf \t\r\n")
    if (nom or "").lower().endswith(".fdx") or (debut.startswith(b"<?xml") and b"<FinalDraft" in data[:4096]) \
            or debut.startswith(b"<FinalDraft"):
        txt, ign = fdx_vers_fountain(data)
        r = lire_fountain(txt)
        for k, v in ign.items():
            r["ignores"][k] = r["ignores"].get(k, 0) + v
        r["format"] = "fdx"
        return r
    r = lire_fountain(decoder(data))
    r["format"] = "fountain"
    return r
