# -*- coding: utf-8 -*-
"""Card Forge — P4 « Import CSV et mapping des champs ». Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/data`. Les chemins
déclarés ici sont RELATIFS à ce préfixe.

CE FICHIER APPARTIENT À P4. Aucun autre module ne l'importe, et il n'importe
le routeur d'aucun autre (règle 8). Ce dont il a besoin vient de
`cards/contract.py` — jamais d'un voisin.

────────────────────────────────────────────────────────────────────────────
POURQUOI TOUT LE TRAVAIL EST ICI ET PAS DANS L'ÉCRAN

La barre (nanDECK 1.29) fait la même chose en une ligne de script :
`LINK = "data.csv"`, `LINKMULTI = qty`, `LINKFILTER = [atk]>1`, `LINKSORT`,
`LINKSEP`, `LINKCSV`. La sémantique est bonne ; ce qui est mauvais, c'est
qu'elle s'écrit à la main dans un éditeur de texte avec 202 pages d'aide à
côté, et que l'encodage par défaut y est l'ANSI — donc « MÃ©lÃ©e » sur le
premier fichier français venu.

Le pipeline complet (décodage -> séparateur -> entête -> filtre -> tri ->
quantité -> mappage) vit ICI, en UN SEUL exemplaire. L'écran ne réimplémente
rien : il POSTe la table et affiche ce qui revient. Deux moteurs, ce serait
deux sémantiques de filtre qui divergent en silence — la version écran dirait
« 3 lignes retenues » et le deck en contiendrait 4.

DEUX POINTS DE MÉTIER QUI SE PAIENT COMPTANT

1. L'ENCODAGE SE DEVINE SUR DES OCTETS, PAS SUR UNE CHAÎNE. L'écran envoie le
   fichier en base64 (`b64`), jamais un texte déjà décodé par le navigateur :
   une fois que JavaScript a lu le fichier en UTF-8, un fichier cp1252 est
   déjà abîmé et plus rien ne peut le réparer proprement. `decode_bytes` voit
   les octets : BOM UTF-8, BOM UTF-16, UTF-8 strict, sinon cp1252.
2. LE FILTRE N'EST PAS UN `eval`. `eval("atk > 1", row)` marcherait et
   ouvrirait l'exécution de code arbitraire sur un fichier venu du dehors.
   Ici : tokeniseur + descente récursive, une grammaire fermée (comparaisons,
   `and`/`or`/`not`, parenthèses, `contains`/`commence par`/`finit par`), et
   une erreur de syntaxe rend la POSITION du caractère fautif — ce que
   `LINKFILTER` ne fait pas.

Routes (relatives à /api/cards/{did}/data) :

    POST /parse     octets -> table (séparateur, encodage, entête devinés)
    POST /build     table + filtre/tri/quantité/mappage -> cartes
    POST /check     validation du filtre SEULE, ne lève jamais (frappe vive)
    POST /export    table -> text/csv téléchargeable (aller-retour)
    GET  /samples   3 jeux d'essai embarqués (état vide qui propose)
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import csv
import io
import math
import posixpath
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
import zlib
from array import array
from collections import Counter
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, HTTPException, Response
from loguru import logger

from .contract import is_valid_did

router = APIRouter()

# ── limites ────────────────────────────────────────────────────────────────
MAX_BYTES = 8 * 1024 * 1024      # 8 Mo de CSV : très au-delà d'un deck réel
MAX_ROWS = 5000
MAX_COLS = 64
MAX_CARDS = 20000
MAX_QTY = 999
SNIFF_BYTES = 96 * 1024          # ce qu'on regarde pour deviner le séparateur
SNIFF_LINES = 60

# ── séparateurs. L'ORDRE est le départage des ex aequo. ────────────────────
SEP_LABEL = {",": "virgule", ";": "point-virgule", "\t": "tabulation",
             "|": "barre verticale"}
SEP_ORDER = (",", ";", "\t", "|")

ENC_LABEL = {"utf-8": "UTF-8", "utf-8-bom": "UTF-8 (BOM)",
             "cp1252": "Windows-1252", "utf-16": "UTF-16",
             "texte": "texte fourni",
             # Un classeur n'a NI séparateur NI encodage de texte : les deux
             # étiquettes qui vont avec doivent le dire, pas mentir « UTF-8 ».
             "xlsx": "classeur .xlsx", "ods": "classeur .ods"}

# Le tableur : la source que les auteurs de jeux tiennent VRAIMENT, et que la
# barre lit (p.152 : csv/xls/xlsx/ods + feuille nommée). Un .xlsx et un .ods
# sont des zips ; on n'a besoin ni d'openpyxl ni d'odfpy pour en tirer la
# première feuille — zipfile et ElementTree sont dans la bibliothèque standard.
ZIP_MAGIC = b"PK\x03\x04"
XL_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
ODF_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
ODF_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"

# Les cibles RÉSERVÉES du mappage : elles ne sont pas des slots de texte de
# P3, elles remplissent les champs du contrat de carte (spec 2.3).
RESERVED = {"art": "art", "back": "back", "id": "id"}
RESERVED_LABEL = {"art": "Illustration (card.art)", "back": "Dos (card.back)",
                  "id": "Identifiant (card.id)"}

# Colonnes VIRTUELLES : elles n'existent pas dans le CSV, elles sont calculées
# à l'expansion des copies. C'est le « jeton de copie n/N » de la spec.
VIRTUAL = {
    "#n": "numéro de copie dans la ligne",
    "#N": "copies de cette ligne",
    "#i": "numéro de carte dans le deck",
    "#T": "total de cartes du deck",
}

# Mojibake classique : du cp1252 relu en UTF-8 par un exportateur distrait.
# On ne répare pas d'office (on pourrait avoir tort) : on SIGNALE, et l'écran
# offre un bouton. Le silence, c'est ce que fait la barre.
_MOJI = ("Ã©", "Ã¨", "Ãª", "Ã«", "Ã ", "Ã¢", "Ã§", "Ã´", "Ã¹", "Ã»", "Ã®",
         "Ã¯", "Ã‰", "Ãˆ", "Â°", "Â«", "Â»", "Â ", "â€™", "â€œ", "â€\x9d",
         "â€“", "â€”")


# ═══════════════════════════════════════════════════════════════════════════
# 1. OCTETS -> TEXTE
# ═══════════════════════════════════════════════════════════════════════════

def looks_mojibake(text: str) -> bool:
    return any(m in text for m in _MOJI)


def repair_mojibake(text: str) -> tuple[str, bool]:
    """cp1252 relu en UTF-8, remis à l'endroit. (texte, réparé oui/non)."""
    try:
        fixed = text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text, False
    if fixed == text:
        return text, False
    return fixed, True


def decode_bytes(raw: bytes, forced: str = "auto") -> tuple[str, str, list]:
    """Octets -> (texte, étiquette d'encodage, avertissements).

    UTF-8 D'ABORD, TOUJOURS — c'est le point exact où la barre perd : nanDECK
    part en ANSI et il faut `LINKCSV` pour en sortir. Ici l'ANSI n'est qu'un
    REPLI, atteint seulement quand les octets ne sont pas de l'UTF-8 valide.
    """
    warn: list = []
    if forced and forced != "auto":
        table = {"utf-8": "utf-8", "utf-8-bom": "utf-8-sig",
                 "cp1252": "cp1252", "utf-16": "utf-16"}
        codec = table.get(forced)
        if codec is None:
            raise HTTPException(400, "Encodage inconnu : " + str(forced)
                                + " (utf-8, utf-8-bom, cp1252, utf-16)")
        try:
            return raw.decode(codec), forced, warn
        except (UnicodeDecodeError, LookupError):
            warn.append("Le fichier n'est pas du " + ENC_LABEL.get(forced, forced)
                        + " valide : décodage en remplacement.")
            return raw.decode(codec, errors="replace"), forced, warn

    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace"), "utf-8-bom", warn
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace"), "utf-16", warn
    try:
        return raw.decode("utf-8"), "utf-8", warn
    except UnicodeDecodeError:
        pass
    warn.append("Octets non UTF-8 : lu en Windows-1252 (cp1252). "
                "Les accents sont préservés.")
    return raw.decode("cp1252", errors="replace"), "cp1252", warn


# ═══════════════════════════════════════════════════════════════════════════
# 1bis. CLASSEURS .xlsx / .ods — la source que la barre lit et pas nous
# ═══════════════════════════════════════════════════════════════════════════
#
# « Aucune entrée tableur, alors que les auteurs de jeux tiennent leur deck
# dans un tableur » : le reproche est juste, et il ne coûte pas une dépendance.
# Un .xlsx et un .ods sont des archives zip contenant du XML. On lit la
# PREMIÈRE feuille, on rend son nom, et l'écran l'affiche — parce qu'un
# classeur à cinq feuilles dont on lit la première en silence est le même
# piège que l'ANSI silencieux de la barre.

def _cell_col(ref: str) -> int:
    """« B3 » -> 1. Sans ça, une cellule vide décale toute la ligne."""
    n = 0
    for ch in str(ref or ""):
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return max(0, n - 1)


def _xlsx_rows(zf: zipfile.ZipFile) -> tuple[list, str]:
    shared: list = []
    if "xl/sharedStrings.xml" in zf.namelist():
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in root.findall(XL_NS + "si"):
            shared.append("".join(t.text or "" for t in si.iter(XL_NS + "t")))
    sheet_name, target = "", ""
    try:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        first = wb.find(XL_NS + "sheets/" + XL_NS + "sheet")
        if first is not None:
            sheet_name = str(first.get("name") or "")
            rid = first.get(
                "{http://schemas.openxmlformats.org/officeDocument/"
                "2006/relationships}id") or ""
            rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            for rel in rels:
                if rel.get("Id") == rid:
                    target = str(rel.get("Target") or "")
    except (KeyError, ET.ParseError):
        pass
    name = ""
    if target:
        cand = posixpath.normpath(posixpath.join("xl", target)).lstrip("/")
        if cand in zf.namelist():
            name = cand
    if not name:
        sheets = sorted(n for n in zf.namelist()
                        if n.startswith("xl/worksheets/") and n.endswith(".xml"))
        if not sheets:
            raise HTTPException(400, "Ce .xlsx ne contient aucune feuille.")
        name = sheets[0]
    out: list = []
    for row in ET.fromstring(zf.read(name)).iter(XL_NS + "row"):
        cells: list = []
        for c in row.findall(XL_NS + "c"):
            j = _cell_col(c.get("r") or "")
            kind = c.get("t") or ""
            if kind == "s":
                v = c.find(XL_NS + "v")
                try:
                    txt = shared[int(v.text)] if v is not None else ""
                except (ValueError, TypeError, IndexError):
                    txt = ""
            elif kind == "inlineStr":
                node = c.find(XL_NS + "is")
                txt = "".join(t.text or "" for t in node.iter(XL_NS + "t")) \
                    if node is not None else ""
            else:
                v = c.find(XL_NS + "v")
                txt = (v.text or "") if v is not None else ""
                if txt.endswith(".0"):
                    txt = txt[:-2]
            while len(cells) <= j and len(cells) < MAX_COLS:
                cells.append("")
            if j < MAX_COLS:
                cells[j] = txt
        out.append(cells)
        if len(out) > MAX_ROWS + 1:
            break
    return out, sheet_name


def _ods_rows(zf: zipfile.ZipFile) -> tuple[list, str]:
    root = ET.fromstring(zf.read("content.xml"))
    table = None
    for t in root.iter(ODF_TABLE + "table"):
        table = t
        break
    if table is None:
        raise HTTPException(400, "Ce .ods ne contient aucune feuille.")
    sheet_name = str(table.get(ODF_TABLE + "name") or "")
    out: list = []
    for row in table.findall(ODF_TABLE + "table-row"):
        cells: list = []
        for c in row.findall(ODF_TABLE + "table-cell"):
            txt = "".join("".join(p.itertext())
                          for p in c.findall(ODF_TEXT + "p"))
            try:
                rep = int(c.get(ODF_TABLE + "number-columns-repeated") or 1)
            except ValueError:
                rep = 1
            rep = max(1, min(rep, MAX_COLS))
            for _k in range(rep):
                if len(cells) < MAX_COLS:
                    cells.append(txt)
        while cells and cells[-1] == "":
            cells.pop()
        out.append(cells)
        if len(out) > MAX_ROWS + 1:
            break
    return out, sheet_name


def read_workbook(raw: bytes) -> tuple[list, str, str]:
    """Octets d'un classeur -> (lignes, « xlsx »|« ods », nom de la feuille)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, OSError):
        raise HTTPException(400, "Archive illisible : ce fichier commence "
                                 "comme un .xlsx/.ods mais n'est pas un zip.")
    with zf:
        names = zf.namelist()
        try:
            if "xl/workbook.xml" in names:
                rows, sheet = _xlsx_rows(zf)
                return rows, "xlsx", sheet
            if "content.xml" in names:
                rows, sheet = _ods_rows(zf)
                return rows, "ods", sheet
        except ET.ParseError as e:
            raise HTTPException(400, "XML du classeur illisible : " + str(e))
    raise HTTPException(400, "Zip sans feuille de calcul : ni « xl/workbook."
                             "xml » (.xlsx) ni « content.xml » (.ods).")


# ═══════════════════════════════════════════════════════════════════════════
# 2. SÉPARATEUR ET ENTÊTE
# ═══════════════════════════════════════════════════════════════════════════

def _read_rows(text: str, sep: str) -> list:
    try:
        return list(csv.reader(io.StringIO(text, newline=""), delimiter=sep))
    except csv.Error:
        return []


def sniff_sep(text: str, forced: str = "auto") -> tuple[str, list]:
    """Le séparateur, sans question posée. (séparateur, avertissements).

    Le score n'est pas « celui qui coupe le plus » : un point-virgule dans un
    fichier à virgules coupe aussi, une fois. On mesure d'abord la CONSTANCE
    du nombre de champs, puis la proportion de champs qui gardent un guillemet
    (signe qu'on coupe au mauvais endroit : `"a,b";"c,d"` découpé sur la
    virgule laisse un `"` au milieu), puis le nombre de colonnes.
    """
    if forced and forced != "auto":
        if forced not in SEP_LABEL:
            raise HTTPException(400, "Séparateur inconnu (virgule, "
                                     "point-virgule, tabulation, barre)")
        return forced, []
    sample = text[:SNIFF_BYTES]
    lines = [ln for ln in sample.splitlines() if ln.strip()][:SNIFF_LINES]
    sample = "\n".join(lines)
    if not sample:
        return ",", ["Fichier vide."]
    best, best_score = None, None
    for k, sep in enumerate(SEP_ORDER):
        rows = [r for r in _read_rows(sample, sep) if r and any(str(c).strip() for c in r)]
        if not rows:
            continue
        counts = [len(r) for r in rows]
        common, freq = Counter(counts).most_common(1)[0]
        if common < 2:
            continue
        consistency = freq / float(len(counts))
        cells = [c for r in rows for c in r]
        bad = sum(1 for c in cells if '"' in c) / float(max(1, len(cells)))
        score = (round(consistency, 3), -round(bad, 3), common, -k)
        if best_score is None or score > best_score:
            best, best_score = sep, score
    if best is None:
        return ",", ["Aucun séparateur ne découpe ce fichier en colonnes : "
                     "une seule colonne sera créée."]
    return best, []


def _is_num(s: str) -> bool:
    return _num(s) is not None


def sniff_header(rows: list) -> bool:
    """Entête ou pas ? (`LINK` de nanDECK devine aussi, on garde la parité.)"""
    if not rows:
        return False
    head = [str(c).strip() for c in rows[0]]
    body = [r for r in rows[1:] if any(str(c).strip() for c in r)]
    if not head or not any(head):
        return False
    if any(_is_num(c) for c in head):
        return False                     # « 3 » ne nomme pas une colonne
    low = [c.lower() for c in head if c]
    if len(low) != len(set(low)):
        return False                     # deux fois le même nom : ce sont des données
    if not body:
        return True
    for j in range(len(head)):
        col = [str(r[j]).strip() for r in body if j < len(r) and str(r[j]).strip()]
        if col and all(_is_num(v) for v in col):
            return True                  # texte au-dessus, nombres en dessous
    return all(bool(c) for c in head)


def _dedup(names: list) -> list:
    out, seen = [], {}
    for i, raw in enumerate(names):
        n = str(raw or "").strip() or ("col" + str(i + 1))
        key = n.lower()
        if key in seen:
            seen[key] += 1
            n = n + " (" + str(seen[key]) + ")"
        else:
            seen[key] = 1
        out.append(n[:64])
    return out


def parse_table(raw: bytes, sep: str = "auto", encoding: str = "auto",
                header: str = "auto", repair: bool = False) -> dict:
    """Le pipeline complet d'import. Ne lève que des HTTPException 400."""
    t0 = time.perf_counter()
    warn: list = []
    sheet = ""
    if raw.startswith(ZIP_MAGIC):
        # CLASSEUR. Ni séparateur ni encodage de texte : les deux étiquettes
        # doivent le DIRE. Afficher « séparateur point-virgule · UTF-8 » sur un
        # .xlsx serait exactement le genre de chiffre faux qu'on traque ici.
        rows, enc, sheet = read_workbook(raw)
        use_sep, moji, repaired = "", False, False
        if sheet:
            warn.append("Classeur : première feuille « " + sheet + " » lue.")
    else:
        text, enc, warn = decode_bytes(raw, encoding)
        moji = looks_mojibake(text)
        repaired = False
        if repair and moji:
            text, repaired = repair_mojibake(text)
            if repaired:
                moji = looks_mojibake(text)
                warn.append("Accents réparés (cp1252 relu en UTF-8).")
        use_sep, w2 = sniff_sep(text, sep)
        warn.extend(w2)
        rows = _read_rows(text, use_sep)
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if len(rows) > MAX_ROWS + 1:
        warn.append("Fichier tronqué à " + str(MAX_ROWS) + " lignes.")
        rows = rows[:MAX_ROWS + 1]
    rows = [[str(c).strip() for c in r] for r in rows]

    if header == "yes":
        has_head = bool(rows)
    elif header == "no":
        has_head = False
    elif header in ("auto", "", None):
        has_head = sniff_header(rows)
    else:
        raise HTTPException(400, "Entête : auto, yes ou no")

    if has_head and rows:
        names = _dedup(rows[0])
        body = rows[1:]
    else:
        width = max([len(r) for r in rows], default=1)
        names = ["col" + str(i + 1) for i in range(width)]
        body = rows
        if rows:
            warn.append("Aucune ligne d'entête détectée : colonnes nommées "
                        "col1…colN.")
    if len(names) > MAX_COLS:
        names = names[:MAX_COLS]
        warn.append("Au-delà de " + str(MAX_COLS) + " colonnes, le reste est ignoré.")
    n = len(names)

    # ── LES LIGNES MAL FORMÉES ÉTAIENT RÉPARÉES EN SILENCE, ET C'EST PIRE QUE
    #    CE QU'ON ME REPROCHAIT. Mesure d'avant, sur `nom;atk;pv` + la ligne
    #    « Echo;1;9;99;77 » : le parseur rendait ['Echo','1','9'], les valeurs
    #    99 et 77 étaient PERDUES, et `warnings` valait []. Un importateur qui
    #    jette de la donnée sans un mot est exactement le reproche qu'on
    #    adressait à la barre pour son ANSI muet.
    #    Ici on compte, on nomme les lignes (numérotées comme à l'écran, la
    #    première ligne de données = 1) et on le DIT. Le critique demandait un
    #    compteur distinct de celui du filtre : « ligne refusée par ma
    #    condition » et « ligne que je n'ai pas su lire » n'ont rien à voir.
    long_rows = [k + 1 for k, r in enumerate(body) if len(r) > n]
    short_rows = [k + 1 for k, r in enumerate(body) if len(r) < n]
    lost = sum(len(r) - n for r in body if len(r) > n)
    if long_rows:
        warn.append(str(len(long_rows)) + " ligne(s) ont PLUS de " + str(n)
                    + " champs : " + str(lost) + " valeur(s) écartée(s) — "
                    + "ligne(s) " + ", ".join(str(x) for x in long_rows[:8])
                    + ("…" if len(long_rows) > 8 else "") + ".")
    if short_rows:
        warn.append(str(len(short_rows)) + " ligne(s) ont MOINS de " + str(n)
                    + " champs : complétée(s) par du vide — ligne(s) "
                    + ", ".join(str(x) for x in short_rows[:8])
                    + ("…" if len(short_rows) > 8 else "") + ".")
    body = [(r + [""] * n)[:n] for r in body]
    enc_label = ENC_LABEL.get(enc, enc)
    if sheet:
        enc_label += " — feuille « " + sheet + " »"
    return {
        "columns": names, "rows": body,
        "sep": use_sep,
        "sep_label": SEP_LABEL.get(use_sep, use_sep) if use_sep
        else "sans objet (classeur)",
        "encoding": enc, "encoding_label": enc_label, "sheet": sheet,
        "workbook": bool(sheet or enc in ("xlsx", "ods")),
        "header": bool(has_head), "mojibake": bool(moji), "repaired": repaired,
        "n_rows": len(body), "n_cols": n, "warnings": warn,
        # lignes mal formées : un compteur À PART de celui du filtre.
        "n_ragged_long": len(long_rows), "n_ragged_short": len(short_rows),
        "n_values_lost": lost,
        "ragged_long": long_rows[:64], "ragged_short": short_rows[:64],
        # « deviné » ou « imposé » : sans ça, la pastille « séparateur
        # point-virgule » ne dit pas si la détection a travaillé ou si
        # l'utilisateur a forcé le menu. C'est la différence entre une preuve
        # et une valeur par défaut heureuse.
        "sep_auto": sep in ("auto", "", None),
        "enc_auto": encoding in ("auto", "", None),
        "ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. LE FILTRE — une grammaire fermée, jamais un `eval`
# ═══════════════════════════════════════════════════════════════════════════

class FilterError(ValueError):
    def __init__(self, msg: str, pos: int = 0):
        super().__init__(msg)
        self.msg = msg
        self.pos = int(pos)


_NUM_RE = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
# Espace ordinaire, insecable (U+00A0) et fine insecable (U+202F) : les trois
# servent de separateur de milliers dans un CSV francais exporte d'un tableur.
_SPACE_RE = re.compile(r"[\s  ]")


def _num(v: Any):
    """Nombre ou None. Tolère la virgule décimale et l'espace de milliers —
    un CSV français écrit « 1 250,5 » et ce n'est pas du texte."""
    s = str(v if v is not None else "").strip()
    if not s:
        return None
    s = s.replace(" ", "").replace(" ", "")
    s = _SPACE_RE.sub("", s)
    if not _NUM_RE.match(s):
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def _fold(v: Any) -> str:
    """Minuscules SANS accent : « Rare » == « rare » == « rarè » n'est pas du
    laxisme, c'est ce qu'un auteur de jeu attend quand il tape son filtre."""
    s = unicodedata.normalize("NFKD", str(v if v is not None else ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


_FALSY = {"", "0", "false", "faux", "no", "non", "off", "n"}


def _truthy(v: Any) -> bool:
    return _fold(v) not in _FALSY


_TOK = re.compile(r"""
      (?P<ws>\s+)
    | (?P<num>[+-]?\d+(?:[.,]\d+)?)(?![\w.])
    | "(?P<dq>[^"]*)"
    | '(?P<sq>[^']*)'
    | \[(?P<br>[^\]]*)\]
    | (?P<op><=|>=|<>|!=|==|=|<|>|~)
    | (?P<par>[()])
    | (?P<word>[^\s()<>=!~\[\]"']+)
""", re.X)

_AND = {"and", "et", "&&", "&"}
_OR = {"or", "ou", "||"}
_NOT = {"not", "non", "pas", "!"}
_WORD_OPS = {
    "contains": "~", "contient": "~", "contain": "~",
    "startswith": "^", "commence": "^", "begins": "^",
    "endswith": "$", "finit": "$", "ends": "$",
    "is": "=", "vaut": "=", "egal": "=", "égal": "=",
}
# « commence PAR », « finit PAR » : le mot de liaison se mange, mais SEULEMENT
# apres ^ et $. Le manger apres `contient` casserait `nom contient par`.
_SKIP_WORDS = {"par", "with", "by"}


def _tokenize(expr: str) -> list:
    out, i, n = [], 0, len(expr)
    while i < n:
        m = _TOK.match(expr, i)
        if not m:
            raise FilterError("Caractère inattendu « " + expr[i] + " »", i)
        i = m.end()
        if m.lastgroup == "ws":
            continue
        if m.lastgroup == "num":
            out.append(("num", m.group("num"), m.start()))
        elif m.lastgroup == "dq":
            out.append(("str", m.group("dq"), m.start()))
        elif m.lastgroup == "sq":
            out.append(("str", m.group("sq"), m.start()))
        elif m.lastgroup == "br":
            out.append(("ref", m.group("br").strip(), m.start()))
        elif m.lastgroup == "op":
            out.append(("op", m.group("op"), m.start()))
        elif m.lastgroup == "par":
            out.append(("par", m.group("par"), m.start()))
        else:
            out.append(("word", m.group("word"), m.start()))
    out.append(("end", "", n))
    return out


class _Parser:
    """Descente récursive. Rend un prédicat `f(row: dict) -> bool`."""

    def __init__(self, toks: list, cols: list):
        self.t = toks
        self.i = 0
        self.cols = {_fold(c): c for c in cols}

    # -- outillage ---------------------------------------------------------
    def peek(self):
        return self.t[self.i]

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def _word_is(self, tok, bag) -> bool:
        return tok[0] == "word" and _fold(tok[1]) in bag

    # -- grammaire ---------------------------------------------------------
    def parse(self):
        f = self.p_or()
        tok = self.peek()
        if tok[0] != "end":
            raise FilterError("« " + str(tok[1]) + " » est en trop", tok[2])
        return f

    def p_or(self):
        left = self.p_and()
        while self._word_is(self.peek(), _OR):
            self.take()
            right = self.p_and()
            left = (lambda a, b: (lambda r: a(r) or b(r)))(left, right)
        return left

    def p_and(self):
        left = self.p_not()
        while self._word_is(self.peek(), _AND):
            self.take()
            right = self.p_not()
            left = (lambda a, b: (lambda r: a(r) and b(r)))(left, right)
        return left

    def p_not(self):
        if self._word_is(self.peek(), _NOT):
            self.take()
            inner = self.p_not()
            return lambda r: not inner(r)
        return self.p_cmp()

    def p_cmp(self):
        left = self.p_atom()
        tok = self.peek()
        op = None
        if tok[0] == "op":
            op = self.take()[1]
        elif tok[0] == "word" and _fold(tok[1]) in _WORD_OPS:
            op = _WORD_OPS[_fold(self.take()[1])]
            nxt = self.peek()
            if nxt[0] == "word" and _fold(nxt[1]) in _SKIP_WORDS:
                self.take()
        if op is None:
            return lambda r: _truthy(left(r))
        right = self.p_atom()
        return _compare(left, right, op)

    def p_atom(self):
        tok = self.take()
        kind, val, pos = tok
        if kind == "par":
            if val != "(":
                raise FilterError("Parenthèse fermante sans ouvrante", pos)
            inner = self.p_or()
            nxt = self.take()
            if nxt[0] != "par" or nxt[1] != ")":
                raise FilterError("Parenthèse « ) » manquante", nxt[2])
            return inner
        if kind == "num":
            return lambda r: val
        if kind == "str":
            return lambda r: val
        if kind == "ref":
            real = self.cols.get(_fold(val))
            if real is None:
                raise FilterError("Colonne inconnue : « " + val + " »", pos)
            return lambda r: r.get(real, "")
        if kind == "word":
            real = self.cols.get(_fold(val))
            if real is not None:
                return lambda r: r.get(real, "")
            return lambda r: val        # un mot nu = une valeur littérale
        if kind == "end":
            raise FilterError("Expression incomplète", pos)
        raise FilterError("Jeton inattendu « " + str(val) + " »", pos)


def _compare(left, right, op):
    def run(r):
        a, b = left(r), right(r)
        if op in ("~", "^", "$"):
            fa, fb = _fold(a), _fold(b)
            if op == "~":
                return fb in fa
            if op == "^":
                return fa.startswith(fb)
            return fa.endswith(fb)
        na, nb = _num(a), _num(b)
        if na is not None and nb is not None:
            x, y = na, nb
        else:
            x, y = _fold(a), _fold(b)
        if op in ("=", "=="):
            return x == y
        if op in ("!=", "<>"):
            return x != y
        if op == "<":
            return x < y
        if op == "<=":
            return x <= y
        if op == ">":
            return x > y
        return x >= y
    return run


def compile_filter(expr: str, columns: list):
    """Prédicat, ou None si l'expression est vide. Lève FilterError."""
    s = str(expr or "").strip()
    if not s:
        return None
    return _Parser(_tokenize(s), list(columns)).parse()


# LA LISTE DES OPÉRATEURS EST SERVIE PAR LE MOTEUR, PAS RECOPIÉE DANS L'ÉCRAN.
# L'écran affiche « n opérateurs » : ce nombre doit être celui du moteur, sinon
# c'est un badge de plus qui ment. `test_chaque_operateur_annonce_fonctionne`
# exécute chacun d'eux sur une table réelle — impossible d'en annoncer un qui
# n'existe pas.
FILTER_OPS = (
    {"sym": ">", "alias": "", "what": "supérieur",
     "ex": "atk > 1"},
    {"sym": ">=", "alias": "", "what": "supérieur ou égal",
     "ex": "atk >= 7"},
    {"sym": "<", "alias": "", "what": "inférieur",
     "ex": "pv < 5"},
    {"sym": "<=", "alias": "", "what": "inférieur ou égal",
     "ex": "pv <= 3"},
    {"sym": "=", "alias": "== · vaut · égal", "what": "égal",
     "ex": "rarete = rare"},
    {"sym": "!=", "alias": "<>", "what": "différent",
     "ex": "rarete != commune"},
    # LES ALIAS ANNONCÉS SONT CEUX QUI SE TAPENT VRAIMENT. Ce champ portait
    # « ^ » et « $ » : deux symboles que le tokeniseur n'a jamais acceptés
    # (son jeu d'opérateurs est <= >= <> != == = < > ~). C'est le test
    # `test_manque5_chaque_operateur_annonce_fonctionne` qui l'a trouvé, sur
    # ma propre liste — exactement ce qu'il est là pour faire.
    # L'EXEMPLE SERVI NE PORTE AUCUN JETON DE MARQUE. Celui-ci disait
    # `nom contient "octo"` : le nom de la mascotte du projet, glissé dans le
    # contenu de démonstration d'un seul côté d'un duel censé être aveugle. Le
    # contrôle de loyauté a dû poser un pavé gris dessus ; il n'aura plus à le
    # faire, et l'exemple reste exactement aussi parlant.
    {"sym": "contient", "alias": "~ · contains", "what": "sous-chaîne",
     "ex": 'nom contient "gard"'},
    {"sym": "commence par", "alias": "startswith · begins", "what": "préfixe",
     "ex": "nom commence par O"},
    {"sym": "finit par", "alias": "endswith · ends", "what": "suffixe",
     "ex": "nom finit par e"},
)
FILTER_JOINS = (
    {"sym": "et", "alias": "and · && · &", "what": "les deux"},
    {"sym": "ou", "alias": "or · ||", "what": "l'une ou l'autre"},
    {"sym": "non", "alias": "not · pas · !", "what": "négation"},
)


def top_joins(expr: str) -> dict:
    """Les connecteurs de PREMIER niveau, hors parenthèses.

    Le constructeur à la souris en a besoin pour une raison de priorité, pas de
    confort : `et` lie plus fort que `ou`. Ajouter « et C » à « A ou B » donne
    `A ou (B et C)`, jamais ce que l'utilisateur vient de demander. L'écran doit
    donc parenthéser l'existant — et il ne peut le savoir qu'ici, où vit le
    seul analyseur.
    """
    s = str(expr or "").strip()
    if not s:
        return {"or": False, "and": False}
    try:
        toks = _tokenize(s)
    except FilterError:
        return {"or": False, "and": False}
    depth, has_or, has_and = 0, False, False
    for kind, val, _pos in toks:
        if kind == "par":
            depth += 1 if val == "(" else -1
        elif kind == "word" and depth == 0:
            f = _fold(val)
            if f in _OR:
                has_or = True
            elif f in _AND:
                has_and = True
    return {"or": has_or, "and": has_and}


def clause_split(expr: str) -> list:
    """Découpe l'expression sur ses « et » de PREMIER niveau.

    À quoi ça sert : quand une ligne est écartée, dire LAQUELLE des conditions
    l'a écartée. « La ligne 4 est barrée » sans dire pourquoi, sur un filtre à
    trois conditions, oblige l'utilisateur à deviner. S'il y a un « ou » au
    premier niveau, aucune condition n'est seule responsable : on rend
    l'expression entière, ce qui reste vrai.
    """
    s = str(expr or "").strip()
    if not s:
        return []
    try:
        toks = _tokenize(s)
    except FilterError:
        return [s]
    depth, cuts, has_or = 0, [], False
    for kind, val, pos in toks:
        if kind == "par":
            depth += 1 if val == "(" else -1
        elif kind == "word" and depth == 0:
            f = _fold(val)
            if f in _OR:
                has_or = True
            elif f in _AND:
                cuts.append((pos, len(val)))
    if has_or or not cuts:
        return [s]
    parts, prev = [], 0
    for pos, ln in cuts:
        parts.append(s[prev:pos].strip())
        prev = pos + ln
    parts.append(s[prev:].strip())
    return [p for p in parts if p]


# ═══════════════════════════════════════════════════════════════════════════
# 4. TRI ET QUANTITÉ
# ═══════════════════════════════════════════════════════════════════════════

_DESC = {"desc", "descendant", "descending", "decroissant", "décroissant",
         "down", "-"}
_ASC = {"asc", "ascendant", "ascending", "croissant", "up", "+"}


def parse_sort(spec: str, columns: list) -> tuple[list, list]:
    """« atk desc, nom » -> [(col, True), (col, False)]. (clés, inconnues)."""
    keys, unknown = [], []
    known = {_fold(c): c for c in columns}
    for part in str(spec or "").split(","):
        p = part.strip()
        if not p:
            continue
        desc = False
        if p.startswith("-"):
            desc, p = True, p[1:].strip()
        p = p.replace(":", " ")
        bits = p.split()
        if len(bits) > 1 and _fold(bits[-1]) in _DESC:
            desc = True
            bits = bits[:-1]
        elif len(bits) > 1 and _fold(bits[-1]) in _ASC:
            bits = bits[:-1]
        name = " ".join(bits).strip().strip("[]")
        if not name:
            continue
        real = known.get(_fold(name))
        if real is None:
            unknown.append(name)
            continue
        keys.append((real, desc))
    return keys, unknown


def _sort_key(v: Any):
    """Les nombres AVANT le texte, et 2 avant 10 (pas « 10 » avant « 2 »)."""
    n = _num(v)
    if n is None:
        return (1, 0.0, _fold(v))
    return (0, n, "")


def apply_sort(items: list, keys: list, get) -> list:
    """Tri STABLE multi-clés : on trie de la dernière clé vers la première."""
    out = list(items)
    for col, desc in reversed(keys):
        out.sort(key=lambda it: _sort_key(get(it, col)), reverse=desc)
    return out


def read_qty(v: Any) -> int:
    n = _num(v)
    if n is None:
        return 1                      # cellule vide ou illisible = 1 copie
    return max(0, min(MAX_QTY, int(round(n))))


# ═══════════════════════════════════════════════════════════════════════════
# 4bis. MAPPAGE AUTOMATIQUE ET AUDIT DU MAPPAGE
# ═══════════════════════════════════════════════════════════════════════════
#
# LE BUG QUI COÛTAIT LE PLUS CHER, ET QU'AUCUN TEST NE VOYAIT.
# La table de synonymes vivait dans l'écran, indexée par les identifiants de son
# jeu de REPLI : `hp`, `type`, `number`. Tant que P3 se taisait, « pv » tombait
# sur « hp » et la démonstration était belle. Dès que P3 publiait ses VRAIS
# slots — `def`, `typeline`, `num` — plus AUCUN synonyme ne tombait : « pv »
# restait orpheline pendant que le slot « Vie » restait vide, et le gabarit
# imprimait sa valeur de démonstration (5) à la place de la donnée (1). La carte
# contredisait la table posée juste à côté, sans un signe. Mesuré : 3 colonnes
# mappées sur 6, 6 slots sur 9 remplis par le gabarit, 0 avertissement.
#
# On indexe donc par CONCEPT, jamais par identifiant : un slot rejoint un
# concept par son id OU par son libellé replié. `def`, `hp`, `pv`, « Vie » sont
# le même concept, quel que soit le nom que P3 choisit.

CONCEPTS = (
    ("title",
     ("title", "name", "nom", "titre", "libelle", "carte", "intitule"),
     ("title", "titre", "nom", "name", "carte", "card", "libelle",
      "intitule", "designation")),
    ("cost",
     ("cost", "cout", "mana", "prix", "energie", "co"),
     ("cost", "cout", "mana", "prix", "energie", "co", "pa")),
    ("atk",
     ("atk", "attack", "attaque", "force", "power", "puissance", "att"),
     ("atk", "attack", "attaque", "att", "force", "power", "puissance",
      "degats", "dmg")),
    ("def",
     ("def", "hp", "pv", "vie", "life", "health", "defense", "endurance",
      "resistance", "points de vie", "armure"),
     ("def", "hp", "pv", "vie", "life", "health", "defense", "endurance",
      "resistance", "points de vie", "armure", "toughness")),
    ("typeline",
     ("typeline", "type", "ligne de type", "classe", "categorie", "sous-type"),
     ("type", "typeline", "classe", "class", "categorie", "famille",
      "ligne de type", "sous-type", "espece")),
    ("rules",
     ("rules", "regles", "texte", "encadre de regles", "effet", "capacite",
      "texte de regles"),
     ("rules", "regles", "texte", "text", "effet", "effect", "description",
      "desc", "capacite", "pouvoir", "abilities")),
    ("flavor",
     ("flavor", "flavour", "ambiance", "texte d'ambiance", "citation",
      "exergue"),
     ("flavor", "flavour", "ambiance", "citation", "quote", "lore",
      "exergue", "texte d'ambiance")),
    ("num",
     ("num", "number", "numero", "no", "index", "numero de carte", "collector"),
     ("num", "number", "numero", "no", "index", "n", "collector")),
    ("artist",
     ("artist", "artiste", "auteur", "author", "illustrateur", "credit"),
     ("artist", "artiste", "auteur", "author", "illustrateur", "credit",
      "illustration par")),
    ("art",
     ("art", "image", "illustration", "visuel", "picture"),
     ("art", "image", "illustration", "img", "picture", "visuel", "fichier",
      "fichier image", "artwork")),
    ("back",
     ("back", "dos", "verso", "endos"),
     ("back", "dos", "verso", "endos")),
    ("id",
     ("id", "identifiant", "code", "ref", "reference", "sku"),
     ("id", "identifiant", "code", "ref", "reference", "sku", "uid")),
    ("rarity",
     ("rarity", "rarete", "rarite"),
     ("rarity", "rarete", "rarite", "raretes")),
)

QTY_NAMES = ("qty", "quantite", "quantity", "nb", "nombre", "copies", "count",
             "exemplaires", "x", "n copies")

# ═══════════════════════════════════════════════════════════════════════════
# LE MOT QUE LE CADRE IMPRIME TOUT SEUL — et qui contredisait le fichier sans
# que rien ne le dise.
#
# LE REPROCHE, MOT POUR MOT : « Bandeau "RARE" imprimé sur les 20 cartes alors
# que la donnée dit "mythique" — contradiction directe entre le cadre et le
# fichier, non détectée par ses propres compteurs. Un outil qui se vante de ne
# rien inventer doit auditer TOUT ce qui est imprimé, y compris les mots peints
# dans le cadre. Correctif attendu : un mot du cadre qui contredit une colonne
# du fichier doit lever une alerte nommée. »
#
# MESURE FAITE ICI, sur le jeu de parité que cet écran propose au premier clic
# et sur le cadre par défaut (`banner: true`, `rarity: "rare"`) : le bandeau
# imprime « RARE » sur les 10 cartes ; la colonne `rarete` dit `rare` sur 3
# cartes, `épique` sur 5 et `commune` sur 2. SEPT cartes sur dix partaient chez
# l'imprimeur avec un mot faux — pendant que le compteur affichait « 0 valeur
# inventée sur les 10 cartes ». Le compteur ne mentait pas sur ce qu'il
# comptait (`card.fields`) ; il mentait sur ce que l'utilisateur lisait, parce
# que rien n'écrivait la portée. C'est exactement le défaut du badge « 16
# bits » : juste dans l'en-tête, faux dans les données.
#
# CE QUE CETTE PIÈCE PEUT ET NE PEUT PAS. Le bandeau appartient à la pièce 02 :
# on n'y touche pas (règle de propriété). On MESURE, on NOMME, et on renvoie
# l'utilisateur au seul endroit qui peut l'éteindre.
#
# LA TABLE EST RECOPIÉE D'UN AUTRE FICHIER — donc elle peut dériver. C'est le
# risque exact qu'on reproche aux badges recopiés, alors il est tenu par un
# test qui relit la source de la pièce 02 et compare les six couples
# (`test_t3_la_table_des_raretes_ne_derive_pas_de_la_piece_02`). Si P2 ajoute
# une rareté, le test tombe.
FRAME_RARITY = (("common", "Commune"), ("uncommon", "Peu commune"),
                ("rare", "Rare"), ("epic", "Épique"),
                ("legendary", "Légendaire"), ("mythic", "Mythique"))
# Le cadre par DÉFAUT : bandeau allumé, rareté « rare ». Un document où la
# pièce 02 n'a jamais été touchée imprime donc « RARE » — c'est le cas le plus
# fréquent, et c'était le cas mesuré.
FRAME_DEFAULT_RARITY = "rare"


def frame_word(frame: Any) -> tuple[str, str]:
    """Le mot que le bandeau du cadre imprime sur CHAQUE carte, et d'où il
    vient. ("", "") quand le bandeau est éteint.

    On suit la règle de la pièce 02 à la lettre (mod-frame.js:393) :
    `banner_text` s'il est écrit, sinon le libellé de la rareté, le tout en
    capitales ; un libellé vide n'imprime aucun bandeau.
    """
    if frame is None:
        return "", ""
    if not isinstance(frame, dict):
        return "", ""
    if frame.get("banner") is False:
        return "", ""
    txt = str(frame.get("banner_text") or "").strip()
    if txt:
        return txt.upper(), "texte du bandeau"
    rid = _fold(frame.get("rarity"))
    known = {k for k, _lab in FRAME_RARITY}
    if rid not in known:
        rid = FRAME_DEFAULT_RARITY          # la pièce 02 retombe sur celle-ci
    for k, lab in FRAME_RARITY:
        if k == rid:
            return lab.upper(), "rareté du cadre"
    return "", ""


def rarity_column(columns: list) -> str:
    """La colonne du fichier qui porte le concept de rareté, s'il y en a une.

    Par CONCEPT, jamais par identifiant : c'est la même table que le mappage
    automatique, en un seul exemplaire.
    """
    for c in columns:
        if "rarity" in _concept_keys(c, 1):
            return str(c)
    return ""


def _concept_keys(name: str, which: int) -> list:
    f = _fold(name)
    if not f:
        return []
    return [k for (k, sn, cn) in CONCEPTS if f in (sn if which == 0 else cn)]


def _slot_list(slots: Any) -> list:
    """[{id,label,text,on,side}] normalisé, réservés compris.

    `text`, `on` et `side` NE SONT PAS DÉCORATIFS — ce sont les trois données
    sans lesquelles le compteur « N du gabarit » est un chiffre inventé.

      · `text` est la valeur de démonstration que le painter de P3 imprime
        quand `card.fields[slot]` est vide (mod-type.js:857 :
        `return v.trim() !== "" ? v : String(slot.text || "")`). Un slot sans
        donnée ET sans `text` n'imprime RIEN : le compter comme « rempli par
        le gabarit » gonfle l'alerte d'un slot qui ne fabrique aucune valeur.
      · `on` : un slot masqué dans P3 n'est même pas dessiné
        (mod-type.js:763 : `slots.filter((s) => s.on && …)`). Le compter, c'est
        annoncer une fausse valeur imprimée sur un slot qui n'existe pas au
        tirage.

    Tant que ces deux champs ne remontaient pas, le moteur ne POUVAIT PAS
    savoir : il rendait une borne supérieure et l'écran l'affichait comme un
    fait. C'est exactement le défaut du badge « 16 bits » — un en-tête pris
    pour une mesure.
    """
    out, seen = [], set()
    for s in (slots or ()):
        if isinstance(s, dict):
            sid = str(s.get("id") or "").strip()
            lab = str(s.get("label") or sid).strip() or sid
            txt = str(s.get("text") if s.get("text") is not None else "")
            on = s.get("on") is not False
            side = "back" if s.get("side") == "back" else (
                "both" if s.get("side") == "both" else "front")
        else:
            sid = str(s or "").strip()
            lab, txt, on, side = sid, "", True, "front"
        if not sid or sid in seen:
            continue
        seen.add(sid)
        out.append({"id": sid, "label": lab, "text": txt, "on": bool(on),
                    "side": side})
    return out


def guess_qty_col(columns: list) -> str:
    for c in columns:
        if _fold(c) in QTY_NAMES:
            return str(c)
    return ""


def suggest_map(columns: list, slots: Any, taken: Any = None) -> dict:
    """Colonnes -> slots, par concept. Rend AUSSI ce qui reste sur le carreau.

    Rendre le mappage n'est que la moitié du travail : ce qu'on n'a PAS su
    placer doit sortir avec son motif, sinon l'écran ne peut pas le dire.
    """
    tgt = _slot_list(slots)
    for sid, lab in RESERVED_LABEL.items():
        if not any(t["id"] == sid for t in tgt):
            tgt.append({"id": sid, "label": lab, "text": "", "on": True,
                        "side": "front"})
    for t in tgt:
        t["keys"] = _concept_keys(t["id"], 0) or _concept_keys(t["label"], 0)
    used = set()
    if isinstance(taken, dict):
        used = {str(v) for v in taken.values() if v}
    elif isinstance(taken, (list, tuple)):
        used = {str(v) for v in taken}
    qty = guess_qty_col(list(columns))
    out, orphans = {}, []
    for c in columns:
        col = str(c)
        if col == qty:
            continue
        keys = _concept_keys(col, 1)
        if not keys:
            orphans.append({
                "col": col, "slot": "",
                "why": "nom inconnu du moteur — déposez-la à la main sur un "
                       "slot"})
            continue
        hit = None
        for t in tgt:
            if t["id"] in used:
                continue
            if set(keys) & set(t["keys"]):
                hit = t
                break
        if hit is None:
            busy = [t for t in tgt if set(keys) & set(t["keys"])]
            orphans.append({
                "col": col, "slot": busy[0]["id"] if busy else "",
                "why": ("le slot « " + busy[0]["label"] + " » est déjà pris "
                        "par une autre colonne")
                if busy else "aucun slot de la carte ne porte ce concept — "
                             "créez-en un dans « 03 Typographie »"})
            continue
        out[col] = hit["id"]
        used.add(hit["id"])
    return {"map": out, "orphans": orphans, "qty_col": qty,
            "free": [t["id"] for t in tgt if t["id"] not in used],
            "slots": [{"id": t["id"], "label": t["label"]} for t in tgt]}


# ═══════════════════════════════════════════════════════════════════════════
# 5. CONSTRUCTION DU DECK
# ═══════════════════════════════════════════════════════════════════════════

# LE MARQUEUR DE VIDE. U+200B ESPACE SANS CHASSE.
#
# Le painter de P3 imprime son texte de démonstration dès que la valeur est
# vide (mod-type.js:857 : `v.trim() !== "" ? v : String(slot.text || "")`).
# `"".trim()` et `" ".trim()` valent tous deux "" : un espace ordinaire ne
# suffit donc PAS à faire taire le gabarit. U+200B est de catégorie Cf, pas Zs
# — `String.prototype.trim` ne l'enlève pas (il n'enlève que WhiteSpace, c'est
# à dire Zs + TAB/VT/FF/NBSP/U+FEFF, et les terminateurs de ligne). La valeur
# passe donc le test, et le moteur de rendu ne dessine rien : U+200B est un
# code point « default ignorable », d'avance nulle.
#
# C'est le seul levier qu'a cette pièce : elle ne peut pas toucher au painter
# de P3 (règle de propriété), mais elle écrit `card.fields` — donc elle peut
# décider que la case reste VIDE au lieu d'être plausible.
#
# ÉCRIT EN ÉCHAPPEMENT, JAMAIS EN CLAIR : un U+200B posé littéralement dans une
# source est invisible à la relecture et se fait manger par le premier outil
# qui normalise le fichier. Le même piège que les marques combinantes.
BLANK = "\u200b"


def build_deck(columns: list, rows: list, mapping: dict | None = None,
               qty_col: Any = None, expr: str = "", sort: str = "",
               off: Any = None, slots: Any = None,
               blank_unfed: bool = True, frame: Any = None) -> dict:
    """Table -> cartes. LE point de vérité de la pièce 04.

    Ordre imposé, et c'est celui de nanDECK : lignes désactivées, puis
    FILTRE, puis TRI, puis expansion des QUANTITÉS, puis mappage. Filtrer
    après avoir dupliqué donnerait le même deck mais compterait faux, et
    trier après duplication séparerait les copies d'une même ligne.

    `blank_unfed` — LE MANQUE QUE LES DEUX CRITIQUES ONT NOMMÉ EN PREMIER.
    Mesure d'avant, carte 1 sur 10 du jeu de parité : 9 emplacements imprimés,
    4 venant du fichier et 5 du GABARIT — coût « 5 », « Créature légendaire —
    Céphalopode », une citation d'ambiance, « 017 / 060 », « ill. <nom> » —
    avec la même typographie et le même aplomb que les vraies valeurs. Sur les
    10 cartes : 50 champs fabriqués partant à 300 DPI chez l'imprimeur, sous un
    bandeau qui l'AVOUAIT sans rien empêcher. Un jeu sortirait numéroté 017/060
    et crédité à un illustrateur imaginaire.

    À vrai (le DÉFAUT), tout slot visible que la donnée n'alimente pas reçoit
    `BLANK` : le gabarit ne reprend jamais la main, la case reste vide. Le texte
    de démonstration redevient ce qu'il doit être — un aperçu de mise en page,
    pas une valeur imprimée.
    """
    cols = [str(c) for c in columns]
    ncol = len(cols)
    off_set = set()
    if isinstance(off, (list, tuple)):
        for v in off:
            try:
                off_set.add(int(v))
            except (TypeError, ValueError):
                continue
    mapping = mapping if isinstance(mapping, dict) else {}
    warn: list = []

    dicts = []
    for i, r in enumerate(rows):
        r = list(r) if isinstance(r, (list, tuple)) else []
        r = (r + [""] * ncol)[:ncol]
        dicts.append((i, {cols[j]: str(r[j] if r[j] is not None else "")
                          for j in range(ncol)}))

    active = [(i, d) for (i, d) in dicts if i not in off_set]

    pred = compile_filter(expr, cols)
    kept = [(i, d) for (i, d) in active if pred(d)] if pred else active

    keys, unknown = parse_sort(sort, cols)
    if unknown:
        warn.append("Tri : colonne inconnue ignorée — "
                    + ", ".join(unknown[:4]))
    if keys:
        kept = apply_sort(kept, keys, lambda it, c: it[1].get(c, ""))

    qcol = str(qty_col).strip() if qty_col not in (None, "") else ""
    if qcol and qcol not in cols:
        low = {_fold(c): c for c in cols}
        qcol = low.get(_fold(qcol), "")
        if not qcol:
            warn.append("Colonne de quantité introuvable : chaque ligne "
                        "compte pour 1.")

    plan, total = [], 0
    for (i, d) in kept:
        q = read_qty(d.get(qcol, "")) if qcol else 1
        if q <= 0:
            continue
        plan.append((i, d, q))
        total += q
        if total > MAX_CARDS:
            raise HTTPException(400, "Ce jeu ferait plus de "
                                + str(MAX_CARDS) + " cartes : réduire la "
                                "quantité ou le filtre.")

    # mappage : {colonne_ou_virtuelle: slot}. Une colonne absente du mappage
    # n'entre pas dans la carte — c'est ce qui rend la table éditable sans
    # polluer le rendu.
    pairs = []
    for src, slot in mapping.items():
        s = str(slot or "").strip()
        if not s:
            continue
        src = str(src)
        if src in VIRTUAL or src in cols:
            pairs.append((src, s))
        else:
            low = {_fold(c): c for c in cols}
            real = low.get(_fold(src))
            if real:
                pairs.append((real, s))

    # Les slots qui PARLERAIENT à la place de la donnée : visibles chez P3 et
    # porteurs d'un texte de démonstration. Ce sont eux, et EUX SEULS, que le
    # mode « laisser vide » neutralise — un slot masqué ou sans texte n'a
    # jamais rien fabriqué, le neutraliser serait du bruit.
    slot_objs = [s for s in _slot_list(slots) if s["id"] not in RESERVED]
    talkers = [s["id"] for s in slot_objs if s["on"] and s["text"].strip()]

    cards, idx = [], 0
    # ── LE COMPTE EXACT, CARTE PAR CARTE, ET IL REMPLACE UN PRODUIT FAUX.
    #    L'écran affichait « champs inventés » = slots_fabriqués × cartes. Le
    #    produit ne vaut QUE si chaque slot fabrique sur CHAQUE carte, et c'est
    #    faux dès qu'une colonne posée a des cellules vides : ces slots-là ne
    #    parlent que sur les cartes où la cellule manque.
    #    MESURE (3 lignes, qty 3/2/5 -> 10 cartes, `texte` vide sur la ligne 2,
    #    4 slots dont 3 sans donnée) : l'écran affichait 3 × 10 = 30 valeurs
    #    fabriquées ; la vérité, comptée carte par carte, est 22 — 8 de trop,
    #    36 % d'exagération sur le seul chiffre qui décide d'un bon à tirer.
    #    Ici on ne multiplie plus : on compte.
    fab_per_card: list = []
    for (i, d, q) in plan:
        for k in range(q):
            idx += 1
            virt = {"#n": str(k + 1), "#N": str(q), "#i": str(idx),
                    "#T": str(total)}
            fields, art, back, cid = {}, None, None, ""
            for src, slot in pairs:
                val = virt[src] if src in VIRTUAL else d.get(src, "")
                if slot == "art":
                    art = val or None
                elif slot == "back":
                    back = val or None
                elif slot == "id":
                    cid = val
                else:
                    fields[slot] = val
            if art:
                fields.setdefault("art", art)
            # compté AVANT la neutralisation : c'est le nombre d'emplacements
            # que le gabarit remplirait sur CETTE carte-là.
            fab_per_card.append(sum(
                1 for sid in talkers if not str(fields.get(sid, "")).strip()))
            if blank_unfed:
                # PAR CARTE, et pas par colonne : la ligne 214 peut avoir sa
                # cellule vide là où la ligne 213 est pleine. Une neutralisation
                # calculée une fois pour toutes raterait exactement le cas qui
                # imprime « RARE » au milieu d'un tirage de 300.
                for sid in talkers:
                    if not str(fields.get(sid, "")).strip():
                        fields[sid] = BLANK
            cards.append({
                "id": (cid or ("c" + str(idx)))[:64],
                "fields": fields, "art": art, "back": back,
                "row": i, "copy": k + 1, "copies": q,
            })

    # ── POURQUOI cette ligne a été écartée, et pas seulement qu'elle l'a été.
    #    Une ligne barrée sur un filtre à trois conditions oblige à deviner.
    rejected = []
    if pred is not None and len(kept) < len(active):
        clauses = []
        for c in clause_split(expr):
            try:
                f = compile_filter(c, cols)
            except FilterError:
                f = None
            if f is not None:
                clauses.append((c, f))
        keptset = {i for (i, _d) in kept}
        for (i, d) in active:
            if i in keptset:
                continue
            why = ""
            for txt, f in clauses:
                try:
                    if not f(d):
                        why = txt
                        break
                except Exception:                           # noqa: BLE001
                    continue
            rejected.append({"r": i, "why": why or str(expr).strip()})
            if len(rejected) >= 400:
                break

    # ── L'AUDIT DU MAPPAGE : le seul chiffre qui fait rater une impression.
    #    Tout le reste de ce bandeau (lignes, retenues, cartes, séparateur,
    #    encodage, ms) était déjà compté. Ce qui ne l'était pas : combien de
    #    slots la carte remplit AVEC LE TEXTE DU GABARIT parce que la donnée ne
    #    les alimente pas. C'est là qu'on imprime 300 raretés fausses.
    # Les champs RÉSERVÉS (art/back/id) ne sont pas comptés comme « nourris par
    # le gabarit » : une illustration absente laisse un trou visible, elle
    # n'imprime pas une valeur fausse. Mélanger les deux gonflerait le compteur
    # d'alerte — et un compteur gonflé se fait ignorer.
    # ── DEUX GRANDS LIVRES QUI TOMBENT JUSTE. Le reproche exact du critique :
    #    « trois dénominateurs différents affichés en même temps sans les
    #    réconcilier — 5 / 7 colonnes posées, 4 / 9 alimentés, 5 / 9 sans
    #    donnée. 5 colonnes posées mais seulement 4 slots alimentés, et rien ne
    #    l'explique à l'écran. » Il avait raison, et l'écart avait une cause
    #    banale : la 5e colonne (`img`) part vers un champ RÉSERVÉ, qui n'est
    #    pas un slot de texte. Deux chiffres justes qui se contredisent à
    #    l'œil valent deux chiffres faux.
    #    Ici chaque colonne et chaque slot tombe dans UNE case, et la somme est
    #    rendue avec le total : l'écran n'a plus qu'à recopier une addition
    #    vérifiable. `test_les_deux_grands_livres_tombent_juste` la refait.
    fed = {slot for _src, slot in pairs}
    mapped_cols = [c for c in cols if any(src == c for src, _s in pairs)]
    to_reserved = [c for c in mapped_cols
                   if any(src == c and s in RESERVED for src, s in pairs)]
    to_slots = [c for c in mapped_cols if c not in to_reserved]
    qty_cols = [qcol] if (qcol and qcol not in mapped_cols) else []
    idle = [c for c in cols
            if c not in mapped_cols and c not in qty_cols]

    slot_objs = [s for s in _slot_list(slots) if s["id"] not in RESERVED]
    # ── LA CASE QUI MANQUAIT AU GRAND LIVRE : la colonne posée sur un slot QUI
    #    N'EXISTE PLUS. P3 renomme ou supprime un slot après le mappage, et la
    #    colonne restait comptée « vers un slot » pendant qu'aucun slot ne se
    #    déclarait alimenté : deux additions justes qui se contredisent à l'œil,
    #    exactement le reproche des trois dénominateurs, une strate plus bas.
    #    Elle n'apparaît que quand elle vaut autre chose que zéro.
    _known = {s["id"] for s in slot_objs} | set(RESERVED)
    if slot_objs:
        to_ghost = [c for c in to_slots
                    if not any(src == c and s in _known for src, s in pairs)]
        to_slots = [c for c in to_slots if c not in to_ghost]
    else:
        to_ghost = []
    visible = [s for s in slot_objs if s["on"]]
    hidden = [s["id"] for s in slot_objs if not s["on"]]
    slots_fed = [s["id"] for s in visible if s["id"] in fed]
    unfed_talk = [s["id"] for s in visible
                  if s["id"] not in fed and s["text"].strip()]
    unfed_mute = [s["id"] for s in visible
                  if s["id"] not in fed and not s["text"].strip()]
    slot_ids = [s["id"] for s in visible]
    has_text = {s["id"]: bool(s["text"].strip()) for s in slot_objs}

    # cellule VIDE sur une colonne mappée : le gabarit reprend la main aussi,
    # et personne ne l'avait vu — c'est le même mensonge, une ligne plus bas.
    holes = []
    for src, slot in pairs:
        # les champs réservés sont hors sujet ici : une illustration vide
        # laisse un trou visible, elle ne fait pas parler le gabarit. Elle est
        # comptée par /artcheck, avec son propre message.
        if src in VIRTUAL or slot in RESERVED:
            continue
        n = sum(q for (_i, d, q) in plan if not str(d.get(src, "")).strip())
        if n:
            # `template` dit si le gabarit PARLE vraiment sur ces cartes-là :
            # un slot masqué ou sans texte de démonstration laisse un vide, il
            # ne fabrique pas une valeur.
            holes.append({"col": src, "slot": slot, "n_cards": n,
                          "template": bool(has_text.get(slot)
                                           and slot in slot_ids)})
    hole_talk = {h["slot"] for h in holes if h["template"]}

    # ── LE CHIFFRE QUI ÉTAIT UNE BORNE PRÉSENTÉE COMME UN FAIT.
    #    `n_from_template` comptait TOUT slot sans donnée, y compris ceux que
    #    P3 a masqués (jamais dessinés) et ceux dont le texte de démonstration
    #    est vide (rien à imprimer). Il annonçait donc des valeurs fabriquées
    #    qui n'existaient pas. Désormais il ne compte que ce qui S'IMPRIME
    #    vraiment — et il vaut 0 quand `blank_unfed` a fait taire le gabarit,
    #    parce que c'est alors la vérité du fichier livré.
    would = len(unfed_talk) + len(hole_talk - set(unfed_talk))

    # ── LES DEUX PARTS DU COMPTE EXACT, ÉCRITES POUR ÊTRE REFAITES DE TÊTE.
    #    `n_fab_unfed` est le seul terme qui se multiplie honnêtement : un slot
    #    QUE RIEN N'ALIMENTE parle sur toutes les cartes. `n_fab_holes` est le
    #    reste — les cellules vides d'une colonne pourtant posée — et il se
    #    DÉDUIT du compte par carte, jamais d'un produit : deux colonnes visant
    #    le même slot le feraient compter deux fois.
    n_fab = sum(fab_per_card)
    n_fab_unfed = len(unfed_talk) * total
    n_fab_holes = n_fab - n_fab_unfed

    # ── LE MOT DU CADRE, CONFRONTÉ À LA COLONNE QUI DIT LA MÊME CHOSE.
    #    Il ne passe par AUCUN slot : il est peint par la pièce 02, donc aucun
    #    compteur de `card.fields` ne pouvait le voir. Compté par CARTE (donc
    #    quantités appliquées), pour parler la même langue que « 10 cartes ».
    fword, forigin = frame_word(frame)
    fr_audit = None
    if fword:
        rcol = rarity_column(cols)
        n_match = n_clash = 0
        clash: dict = {}
        if rcol:
            for (_i, d, q) in plan:
                v = str(d.get(rcol, "")).strip()
                if _fold(v) == _fold(fword):
                    n_match += q
                else:
                    n_clash += q
                    clash[v] = clash.get(v, 0) + q
        fr_audit = {
            "word": fword, "from": forigin, "col": rcol or None,
            "n_cards": total, "n_match": n_match, "n_clash": n_clash,
            "clash": [{"v": k or "(vide)", "n": n} for k, n in
                      sorted(clash.items(), key=lambda kv: -kv[1])][:6],
        }

    audit = {
        "slots_known": bool(slot_objs),
        # grand livre des COLONNES — la somme vaut n_cols
        "n_cols": ncol, "n_cols_mapped": len(mapped_cols),
        "cols_mapped": mapped_cols,
        "cols_to_slots": to_slots, "n_cols_to_slots": len(to_slots),
        "cols_to_reserved": to_reserved, "n_cols_to_reserved": len(to_reserved),
        "cols_to_ghost": to_ghost, "n_cols_to_ghost": len(to_ghost),
        "cols_qty": qty_cols, "n_cols_qty": len(qty_cols),
        "cols_unmapped": idle, "n_cols_idle": len(idle),
        "qty_also_mapped": bool(qcol and qcol in mapped_cols),
        # grand livre des SLOTS — la somme vaut n_slots (masqués à part)
        "n_slots": len(slot_ids), "n_slots_fed": len(slots_fed),
        "slots_fed": slots_fed,
        "slots_unfed": unfed_talk + unfed_mute,
        "slots_unfed_template": unfed_talk,
        "n_slots_unfed_template": len(unfed_talk),
        # LES DEUX COMPTES DE SLOTS NE PARLENT PAS DE LA MÊME CHOSE, ET L'ÉCRAN
        # LES AFFICHAIT CÔTE À CÔTE : le grand livre classe les slots par
        # ORIGINE (alimenté / sans colonne / muet) et vaut 5 ; le compteur du
        # haut compte les slots où le gabarit PREND LA PAROLE et vaut 6, parce
        # qu'un slot bien mappé parle quand même sur les cartes dont la cellule
        # est vide. Deux chiffres justes qui se contredisent à l'œil valent
        # deux chiffres faux : voici le terme qui les réconcilie, à écrire.
        "slots_template_hole_only": sorted(hole_talk - set(unfed_talk)),
        "n_slots_template_hole_only": len(hole_talk - set(unfed_talk)),
        "slots_unfed_blank": unfed_mute,
        "n_slots_unfed_blank": len(unfed_mute),
        "slots_hidden": hidden, "n_slots_hidden": len(hidden),
        "holes": holes,
        # ce qui s'imprime VRAIMENT, et ce qui a été évité
        "blank_mode": bool(blank_unfed),
        "n_from_template": 0 if blank_unfed else would,
        "n_template_avoided": would if blank_unfed else 0,
        # LE COMPTE DES EMPLACEMENTS, PAS DES SLOTS — c'est lui qui décide d'un
        # bon à tirer, et c'est lui que l'écran multipliait de travers.
        "n_fabricated": 0 if blank_unfed else n_fab,
        "n_fabricated_avoided": n_fab if blank_unfed else 0,
        "n_fab_unfed": n_fab_unfed, "n_fab_holes": n_fab_holes,
        # par carte, pour que la mesure sur le FICHIER d'une carte donnée
        # puisse se confronter au bon nombre et pas à une moyenne
        "fab_per_card": fab_per_card[:MAX_ROWS],
        "fab_truncated": len(fab_per_card) > MAX_ROWS,
        # ce que le CADRE imprime par-dessus, et que `card.fields` ne voit pas
        "frame": fr_audit,
    }

    return {
        "cards": cards,
        "stats": {
            "n_rows": len(dicts), "n_active": len(active),
            "n_kept": len(kept), "n_cards": total,
            # `n_targets_fed` et pas « n_slots » : `audit.n_slots` compte les
            # slots de la CARTE, celui-ci compte les cibles alimentées, champs
            # réservés compris. Deux clés du même nom pour deux dénombrements
            # différents, c'est le bug de demain.
            "n_cols": ncol, "n_targets_fed": len({s for _, s in pairs}),
            "qty_col": qcol or None,
            "filtered_out": len(active) - len(kept),
            "disabled": len(dicts) - len(active),
            "kept_rows": [{"r": i, "q": q} for (i, _d, q) in plan[:MAX_ROWS]],
            "rejected": rejected,
            "audit": audit,
            "warnings": warn,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# 6. EXPORT CSV — l'aller-retour doit rendre la MÊME table
# ═══════════════════════════════════════════════════════════════════════════

def write_csv(columns: list, rows: list, sep: str = ";", bom: bool = False) -> bytes:
    if sep not in SEP_LABEL:
        sep = ";"
    buf = io.StringIO(newline="")
    w = csv.writer(buf, delimiter=sep, quoting=csv.QUOTE_MINIMAL,
                   lineterminator="\r\n")
    cols = [str(c) for c in columns]
    w.writerow(cols)
    n = len(cols)
    for r in rows:
        r = list(r) if isinstance(r, (list, tuple)) else []
        w.writerow([str(c if c is not None else "") for c in (r + [""] * n)[:n]])
    data = buf.getvalue().encode("utf-8")
    # LE BOM N'EST PLUS LE DÉFAUT. Mesuré : 258 octets entrent, 261 sortent —
    # l'identité octet pour octet n'existait qu'après avoir décoché une case
    # que personne ne décoche. Le défaut rend maintenant le fichier de
    # l'utilisateur tel qu'il l'a donné ; la case reste là pour Excel, qui
    # sinon ouvre un CSV UTF-8 en ANSI et affiche « MÃ©lÃ©e ».
    return (b"\xef\xbb\xbf" + data) if bom else data


def deck_table(cards: list, slots: Any = None) -> tuple[list, list]:
    """Les CARTES construites -> une table à plat, prête pour le CSV.

    LE LIVRABLE QUI MANQUAIT. Le critique l'a mesuré et il avait raison :
    « Exporter le CSV » rendait la table SOURCE — 7 colonnes, 4 lignes, y
    compris l'Écho que le filtre venait d'écarter, et la colonne `qty` non
    résolue. Ce n'était donc PAS le deck de 10 cartes que la spec demande
    (« export CSV du deck (aller-retour) »), et cela annulait le reproche que
    cette pièce adressait à la barre sur ce point exact.

    Ici : une ligne PAR CARTE, dans l'ordre du deck, avec le slot alimenté en
    colonne. Le marqueur de vide U+200B est retiré — écrire un caractère
    invisible dans un CSV livré serait un octet caché de plus, exactement ce
    qu'on reproche aux autres.
    """
    order, seen = [], set()
    for s in _slot_list(slots):
        if s["id"] in RESERVED:
            continue
        order.append(s["id"])
        seen.add(s["id"])
    for c in (cards or ()):
        for k in ((c.get("fields") or {}) if isinstance(c, dict) else {}):
            if k not in seen and k not in RESERVED:
                order.append(k)
                seen.add(k)
    used = [k for k in order
            if any(str((c.get("fields") or {}).get(k, "")).replace(BLANK, "").strip()
                   for c in (cards or ()))]
    has_art = any(c.get("art") for c in (cards or ()))
    has_back = any(c.get("back") for c in (cards or ()))
    cols = (["carte", "ligne", "copie", "copies"] + used
            + (["art"] if has_art else []) + (["dos"] if has_back else []))
    rows = []
    for c in (cards or ()):
        f = c.get("fields") or {}
        r = [str(c.get("id") or ""), str(int(c.get("row", 0)) + 1),
             str(c.get("copy") or 1), str(c.get("copies") or 1)]
        r += [str(f.get(k, "")).replace(BLANK, "") for k in used]
        if has_art:
            r.append(str(c.get("art") or ""))
        if has_back:
            r.append(str(c.get("back") or ""))
        rows.append(r)
    return cols, rows


# ═══════════════════════════════════════════════════════════════════════════
# 7. JEUX D'ESSAI EMBARQUÉS — l'état vide doit PROPOSER, pas attendre
# ═══════════════════════════════════════════════════════════════════════════

# La parité nanDECK, littéralement : 4 lignes, filtre `atk > 1` -> 3 retenues,
# quantités 3/2/5 -> 10 cartes. Ce sont les chiffres du relevé de la barre.
_S1 = (
    "nom;atk;pv;qty;rarete;texte\r\n"
    "Colosse;7;5;3;rare;Mêlée de lances\r\n"
    "Oracle;2;3;2;commune;Voit à travers la brume\r\n"
    "Rebut;9;1;5;épique;Écrase tout sur son passage\r\n"
    "Écho;1;9;4;commune;Ne fait rien, très bien\r\n"
)
# Le même jeu, en Windows-1252 et à la virgule : la détection d'encodage se
# prouve à l'écran, pas dans une note de bas de page.
_S2 = (
    "nom,atk,pv,qty,rarete,texte\r\n"
    "Chimère,6,4,2,rare,Créature à trois têtes\r\n"
    "Épée brisée,3,0,3,commune,Déjà servie\r\n"
    "Fée d'été,1,2,1,commune,Légère comme un été\r\n"
    "Golem forgé,8,8,1,épique,Forgé à même la pierre\r\n"
)


def _sample_load(n: int = 200) -> bytes:
    """Le jeu de charge : n lignes en TSV, pour tenir le seuil « 200 lignes
    en moins de 2 s » à l'écran et non sur parole."""
    fam = ["Colosse", "Oracle", "Rebut", "Chimère", "Golem", "Fée",
           "Spectre", "Épée", "Totem", "Sirène"]
    out = ["nom\tatk\tpv\tqty\trarete\ttexte"]
    for i in range(n):
        out.append("\t".join([
            fam[i % len(fam)] + " " + str(i + 1),
            str((i * 7) % 13), str((i * 5) % 11 + 1),
            str(i % 3 + 1),
            ["commune", "rare", "épique"][i % 3],
            "Carte générée n°" + str(i + 1) + " — accents é è ê ç à ù",
        ]))
    return ("\r\n".join(out) + "\r\n").encode("utf-8")


def _sample_xlsx() -> bytes:
    """Un vrai .xlsx, fabriqué avec zipfile — pour que « lit les classeurs » se
    prouve d'un clic dans l'écran vide, et pas dans une note de bas de page."""
    grid = [["nom", "atk", "pv", "qty", "rarete", "texte"],
            ["Colosse", "7", "5", "3", "rare", "Mêlée de lances"],
            ["Oracle", "2", "3", "2", "commune", "Voit à travers la brume"],
            ["Rebut", "9", "1", "5", "épique", "Écrase tout sur son passage"],
            ["Écho", "1", "9", "4", "commune", "Ne fait rien, très bien"]]

    def esc(s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    body = []
    for i, row in enumerate(grid, 1):
        cells = []
        for j, v in enumerate(row):
            ref = chr(65 + j) + str(i)
            cells.append('<c r="' + ref + '" t="inlineStr"><is><t xml:space='
                         '"preserve">' + esc(v) + "</t></is></c>")
        body.append('<row r="' + str(i) + '">' + "".join(cells) + "</row>")
    sheet = ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://'
             'schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             + "".join(body) + "</sheetData></worksheet>")
    wb = ('<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://'
          'schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http'
          '://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="Deck" sheetId="1" r:id="rId1"/></sheets>'
          "</workbook>")
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http'
            '://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/worksheet" Target="worksheets/'
            'sheet1.xml"/></Relationships>')
    root = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http'
            '://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="xl/'
            'workbook.xml"/></Relationships>')
    types = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://'
             'schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxml'
             'formats-package.relationships+xml"/><Default Extension="xml" '
             'ContentType="application/xml"/></Types>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", root)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


# LE JEU QUI CASSE LES IMPORTATEURS, ET QU'AUCUN CÔTÉ N'AVAIT OSÉ MONTRER.
# Le reproche, mot pour mot : « le jeu d'essai est parfaitement formé : aucune
# ligne à colonnes en trop ou en moins, aucun champ entre guillemets, aucun
# séparateur présent dans une valeur. Rien n'est donc prouvé sur le seul
# endroit où un importateur CSV casse vraiment. » Le voici, à la VIRGULE —
# donc le cas symétrique qu'il disait non testé — avec les cinq pièges dans
# quatre lignes : virgule dans un champ cité, guillemet doublé, retour à la
# ligne DANS un champ, les autres séparateurs présents comme texte, et une
# ligne à colonnes en trop pour que le compteur de lignes mal formées se voie.
_S3 = (
    'nom,atk,qty,texte\r\n'
    'Écho,1,1,"Ne fait rien, très bien"\r\n'
    'Rebut,9,2,"il dit ""bonjour"" ici"\r\n'
    'Oracle,2,1,"deux lignes :\r\nla seconde"\r\n'
    'Golem,8,1,"a;b|c et une tabulation\tici"\r\n'
    'Chimère,6,1,trop,de,champs\r\n'
)


def _measured(entry: dict) -> dict:
    """Les chiffres de la vignette, RELEVÉS SUR SES PROPRES OCTETS.

    Ils étaient écrits à la main dans ce fichier — « n: 4 », « UTF-8 »,
    « point-virgule » — à côté d'un jeu d'octets qui pouvait changer sans eux.
    C'est exactement le badge recopié qui finit par mentir, et il n'y a aucune
    raison de le recopier : le moteur qui lira le fichier au clic peut le lire
    tout de suite. La vignette annonce donc ce que la DÉTECTION a rendu, sans
    rien forcer — ce qui la rend, au passage, la seule preuve à l'écran que la
    détection travaille vraiment au lieu de tomber sur une valeur par défaut
    heureuse : six jeux, trois encodages, quatre séparateurs, aucun réglage.
    """
    raw = base64.b64decode(entry["b64"])
    t = parse_table(raw)
    p = entry.get("preset") or {}
    cards = None
    kept = None
    try:
        out = build_deck(t["columns"], t["rows"], {},
                         p.get("qty_col") or None,
                         str(p.get("filter") or ""), str(p.get("sort") or ""))
        cards = out["stats"]["n_cards"]
        kept = out["stats"]["n_kept"]
    except Exception:                                       # noqa: BLE001
        cards = kept = None
    e = dict(entry)
    e.update({
        "n": t["n_rows"], "n_cols": t["n_cols"],
        "encoding": ENC_LABEL.get(t["encoding"], t["encoding"]),
        "sep": t["sep_label"],
        "workbook": bool(t["workbook"]), "sheet": t["sheet"],
        "bytes": len(raw),
        "auto": bool(t["sep_auto"] and t["enc_auto"]),
        "n_kept": kept, "n_cards": cards,
        # L'AVERTISSEMENT EST CITÉ, PAS RÉSUMÉ. « 1 avertissement(s) — c'est le
        # sujet de ce jeu » était une affirmation de plus à croire sur parole,
        # et fausse pour deux des six jeux. Le texte exact que l'import
        # produira tient sur la vignette : il se compare à l'écran d'après.
        "n_warn": len(t["warnings"]),
        "warn0": (t["warnings"][0] if t["warnings"] else ""),
        "ms": t["ms"],
    })
    return e


_SAMPLES: list = []


def samples() -> list:
    """Six jeux d'essai EMBARQUÉS (0 octet réseau) : un écran vide qui ne
    propose rien perd le duel avant la première fonctionnalité.

    Aucun chiffre de vignette n'est écrit ici : ils sont MESURÉS par le moteur
    sur les octets du jeu, une fois, au premier appel (`_measured`).
    """
    global _SAMPLES
    if _SAMPLES:
        return _SAMPLES
    brut = [
        {"id": "parite", "label": "Parité nanDECK — filtre + quantités",
         "hint": "filtre atk > 1, quantités 3/2/5, tri atk décroissant",
         "file": "parite_nandeck.csv",
         "preset": {"qty_col": "qty", "filter": "atk > 1", "sort": "atk desc"},
         "b64": base64.b64encode(_S1.encode("utf-8")).decode("ascii")},
        {"id": "ansi", "label": "Accents ANSI — Windows-1252",
         "hint": "le défaut de nanDECK ; ici l'encodage est reconnu tout seul",
         "file": "accents_ansi.csv",
         "preset": {"qty_col": "qty", "filter": "", "sort": ""},
         "b64": base64.b64encode(_S2.encode("cp1252")).decode("ascii")},
        # LE TROISIÈME ENCODAGE, QUI MANQUAIT À LA DÉMONSTRATION. Le critique
        # a compté : « détection prouvée sur 1 cas sur 3 pour l'encodage —
        # UTF-8 seul ; UTF-8-BOM et cp1252 jamais ». cp1252 était là (jeu
        # « ansi »), UTF-8-BOM ne l'était nulle part. Avec celui-ci les trois
        # encodages ET les trois séparateurs de la spec se prouvent d'un clic,
        # dans l'écran, sans fabriquer un fichier à la main.
        {"id": "bom", "label": "BOM d'Excel — UTF-8 avec BOM",
         "hint": "ce qu'Excel écrit quand on « enregistre sous CSV UTF-8 »",
         "file": "excel_bom.tsv",
         "preset": {"qty_col": "qty", "filter": "", "sort": "nom"},
         "b64": base64.b64encode(
             b"\xef\xbb\xbf" + _S1.replace(";", "\t").encode("utf-8")
         ).decode("ascii")},
        {"id": "pieges", "label": "Pièges du CSV — 5 cas qui cassent",
         "hint": "virgule dans un champ cité, guillemet doublé, retour à la "
                 "ligne dans une cellule, autres séparateurs en texte, ligne "
                 "à colonnes en trop",
         "file": "pieges.csv",
         "preset": {"qty_col": "qty", "filter": "", "sort": ""},
         "b64": base64.b64encode(_S3.encode("utf-8")).decode("ascii")},
        {"id": "classeur", "label": "Classeur .xlsx — feuille « Deck »",
         "hint": "un vrai tableur, sans séparateur ni encodage à deviner",
         "file": "deck_demo.xlsx",
         "preset": {"qty_col": "qty", "filter": "atk > 1", "sort": "atk desc"},
         "b64": base64.b64encode(_sample_xlsx()).decode("ascii")},
        {"id": "charge", "label": "Charge — le seuil des 200 lignes",
         "hint": "mesure le seuil « 200 lignes importées en moins de 2 s »",
         "file": "charge_200.tsv",
         "preset": {"qty_col": "", "filter": "", "sort": ""},
         "b64": base64.b64encode(_sample_load(200)).decode("ascii")},
    ]
    _SAMPLES = [_measured(x) for x in brut]
    return _SAMPLES


# ═══════════════════════════════════════════════════════════════════════════
# 7bis. LA CARTE LIVRÉE, LUE OCTET PAR OCTET (et pas dans son en-tête)
#
# POURQUOI CE CODE EXISTE. Un audit a démontré, en redécodant des PNG à la
# main, qu'un badge « 16 bits » était FAUX : l'en-tête IHDR annonçait 16 bits
# et les 12 582 912 échantillons tombaient tous sur le réseau k·257 — une carte
# 8 bits élargie, 200 valeurs distinctes, 7,64 bits utiles. Pire : deux
# verdicts successifs se sont contredits sur le même octet parce que l'un
# s'était arrêté à l'en-tête. Un en-tête est une DÉCLARATION ; la profondeur
# réelle est une propriété des échantillons, et elle se mesure.
#
# CE QUE CE MODULE MESURE, ET CE QU'IL REFUSE DE DIRE.
#  · l'inventaire des chunks, dans l'ordre, sur les octets ;
#  · pHYs -> la résolution que le fichier DÉCLARE. Absent, on l'écrit : « ce
#    fichier ne déclare aucun DPI ». On n'invente pas 300 parce que l'écran
#    l'affiche ailleurs — c'est exactement le badge recopié qui finit par
#    mentir ;
#  · la profondeur EFFECTIVE : IDAT dégonflé, défiltré, échantillons comptés,
#    pas du réseau (pgcd) et log2 du nombre de valeurs distinctes ;
#  · le canal alpha : constant ou non, et le poids mort qu'il coûte.
# Quand une mesure n'est pas faisable (entrelacé Adam7, profondeur < 8, image
# hors budget), `deep` revient à faux AVEC la raison — jamais un chiffre par
# défaut.
# ═══════════════════════════════════════════════════════════════════════════

PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
PNG_COLOR = {0: "gris", 2: "RVB", 3: "palette", 4: "gris + alpha",
             6: "RVB + alpha"}
# 24 M d'échantillons : une carte 815 x 1110 RVBA en fait 3 619 710, une planche
# A4 300 DPI en RVBA 34 M. Au-delà on le DIT au lieu de faire attendre.
MAX_PNG_SAMPLES = 24_000_000
INCH_MM = 25.4
PX_PER_M_300 = 11811             # 300 DPI exprimés en pixels par mètre


def png_chunks(raw: bytes) -> list:
    """Les chunks dans l'ordre, lus sur les octets, sans aucune tolérance : une
    longueur qui déborde arrête la lecture et se signale (`tronque`)."""
    out: list = []
    n = len(raw)
    i = 8
    while i + 8 <= n:
        ln = int.from_bytes(raw[i:i + 4], "big")
        typ = raw[i + 4:i + 8].decode("latin-1")
        if ln < 0 or i + 12 + ln > n:
            out.append({"type": typ, "len": ln, "tronque": True})
            break
        out.append({"type": typ, "len": ln})
        i += 12 + ln
        if typ == "IEND":
            break
    return out


def _png_unfilter(data: bytes, w: int, h: int, ch: int, depth: int) -> bytes:
    """Les cinq filtres de la spec PNG, à la main. Aucune dépendance : c'est le
    même défiltrage que celui de l'audit, et il doit tenir dans ce fichier."""
    bpp = max(1, ch * depth // 8)
    stride = (w * ch * depth + 7) // 8
    if len(data) < (stride + 1) * h:
        raise ValueError("flux IDAT trop court : "
                         + str(len(data)) + " octets pour "
                         + str((stride + 1) * h) + " attendus")
    out = bytearray(stride * h)
    prev = bytes(stride)
    pos = 0
    for y in range(h):
        f = data[pos]
        pos += 1
        cur = bytearray(data[pos:pos + stride])
        pos += stride
        if f == 1:
            for k in range(bpp, stride):
                cur[k] = (cur[k] + cur[k - bpp]) & 255
        elif f == 2:
            for k in range(stride):
                cur[k] = (cur[k] + prev[k]) & 255
        elif f == 3:
            for k in range(stride):
                a = cur[k - bpp] if k >= bpp else 0
                cur[k] = (cur[k] + ((a + prev[k]) >> 1)) & 255
        elif f == 4:
            for k in range(stride):
                a = cur[k - bpp] if k >= bpp else 0
                b = prev[k]
                c = prev[k - bpp] if k >= bpp else 0
                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[k] = (cur[k] + pr) & 255
        elif f != 0:
            raise ValueError("filtre PNG inconnu (" + str(f) + ") ligne "
                             + str(y + 1))
        out[y * stride:(y + 1) * stride] = cur
        prev = bytes(cur)
    return bytes(out)


def _png_values(px: bytes, depth: int) -> list:
    """Les valeurs d'échantillon PRÉSENTES, comptées sur les octets."""
    if depth == 8:
        return [k for k in range(256) if px.count(k)]
    a = array("H")
    a.frombytes(px[:len(px) - (len(px) % 2)])
    if sys.byteorder == "little":
        a.byteswap()                       # PNG est gros-boutiste
    return sorted(set(a))


def png_report(raw: Any, deep: bool = True) -> dict:
    """Le rapport complet d'un PNG. Ne lève JAMAIS : un fichier illisible rend
    `ok: false` avec la raison, parce qu'un 500 n'apprend rien à personne."""
    t0 = time.perf_counter()
    rep: dict = {"ok": False, "error": "", "bytes": 0, "chunks": [],
                 "chunk_counts": {}, "ihdr": None, "phys": None,
                 "dpi": None, "deep": False, "deep_why": "",
                 "samples": 0, "distinct": 0, "bits_effective": None,
                 "lattice_step": None, "alpha": None, "ms": 0.0}
    if not isinstance(raw, (bytes, bytearray)):
        rep["error"] = "pas d'octets à lire"
        return rep
    raw = bytes(raw)
    rep["bytes"] = len(raw)
    if raw[:8] != PNG_SIG:
        rep["error"] = "signature PNG absente (ce n'est pas un PNG)"
        rep["ms"] = round((time.perf_counter() - t0) * 1000, 3)
        return rep
    ch_list = png_chunks(raw)
    rep["chunks"] = ch_list[:64]
    counts: dict = {}
    for c in ch_list:
        counts[c["type"]] = counts.get(c["type"], 0) + 1
    rep["chunk_counts"] = counts
    if not ch_list or ch_list[0]["type"] != "IHDR":
        rep["error"] = "premier chunk absent ou différent d'IHDR"
        rep["ms"] = round((time.perf_counter() - t0) * 1000, 3)
        return rep
    idat = bytearray()
    pos = 8
    for c in ch_list:
        ln = c["len"]
        body = raw[pos + 8:pos + 8 + ln]
        if c["type"] == "IHDR" and ln >= 13:
            w = int.from_bytes(body[0:4], "big")
            h = int.from_bytes(body[4:8], "big")
            color = body[9]
            rep["ihdr"] = {
                "w": w, "h": h, "bits": body[8], "color": color,
                "color_label": PNG_COLOR.get(color, "type " + str(color)),
                "channels": PNG_CHANNELS.get(color, 0),
                "compression": body[10], "filter": body[11],
                "interlace": body[12],
            }
        elif c["type"] == "pHYs" and ln >= 9:
            x = int.from_bytes(body[0:4], "big")
            y = int.from_bytes(body[4:8], "big")
            unit = body[8]
            rep["phys"] = {"x": x, "y": y, "unit": unit,
                           "unit_label": ("pixels par mètre" if unit == 1
                                          else "sans unité (rapport seul)")}
            if unit == 1:
                # 1 pouce = 0,0254 m : px/m -> DPI, arrondi à 4 décimales pour
                # que 11811 se lise « 299,9994 » et pas « 300 » par charité.
                rep["dpi"] = round(x * 0.0254, 4)
                rep["dpi_y"] = round(y * 0.0254, 4)
        elif c["type"] == "IDAT":
            idat += body
        pos += 12 + ln
        if c.get("tronque"):
            rep["error"] = "chunk tronqué : le fichier est incomplet"
            break
    ih = rep["ihdr"]
    if not ih:
        rep["error"] = rep["error"] or "IHDR illisible"
        rep["ms"] = round((time.perf_counter() - t0) * 1000, 3)
        return rep
    rep["ok"] = not rep["error"]
    if not deep:
        rep["deep_why"] = "mesure des échantillons non demandée"
    elif not idat:
        rep["deep_why"] = "aucun chunk IDAT"
    elif ih["interlace"]:
        rep["deep_why"] = ("image entrelacée (Adam7) : le défiltrage ligne à "
                           "ligne ne s'applique pas")
    elif ih["bits"] < 8:
        rep["deep_why"] = ("profondeur " + str(ih["bits"]) + " bits : les "
                           "échantillons ne tombent pas sur des octets")
    elif not ih["channels"]:
        rep["deep_why"] = "type de couleur " + str(ih["color"]) + " inconnu"
    elif ih["w"] * ih["h"] * ih["channels"] > MAX_PNG_SAMPLES:
        rep["deep_why"] = (str(ih["w"] * ih["h"] * ih["channels"])
                           + " échantillons, au-delà du budget de "
                           + str(MAX_PNG_SAMPLES))
    else:
        try:
            flux = zlib.decompress(bytes(idat))
            px = _png_unfilter(flux, ih["w"], ih["h"], ih["channels"],
                               ih["bits"])
            vals = _png_values(px, ih["bits"])
            rep["deep"] = True
            rep["samples"] = ih["w"] * ih["h"] * ih["channels"]
            rep["distinct"] = len(vals)
            rep["bits_effective"] = (round(math.log2(len(vals)), 2)
                                     if vals else 0.0)
            pas = 0
            for v in vals:
                if v:
                    pas = math.gcd(pas, v)
            rep["lattice_step"] = pas or 1
            # LE CAS EXACT DE L'AUDIT : 16 bits annoncés, tout sur k·257.
            rep["widened_8bit"] = bool(ih["bits"] == 16 and pas
                                       and pas % 257 == 0)
            # LE CANAL ALPHA, ET CE QU'IL COÛTE. Reproche mesuré du tour
            # précédent, sur les DEUX camps : « la carte livrée déclare un
            # canal alpha dont les 904 650 pixels valent 255 — du poids mort
            # et une source d'ennuis chez l'imprimeur ». On ne peut pas le
            # retirer (la toile appartient au CORE), on peut le CHIFFRER.
            if ih["channels"] in (2, 4) and ih["bits"] == 8:
                canal = px[ih["channels"] - 1::ih["channels"]]
                dist = sorted(set(canal))
                rep["alpha"] = {
                    "distinct": len(dist),
                    "min": dist[0] if dist else None,
                    "max": dist[-1] if dist else None,
                    "opaque": bool(len(dist) == 1 and dist[0] == 255),
                    "bytes": ih["w"] * ih["h"],
                }
        except Exception as e:                          # noqa: BLE001
            rep["deep_why"] = "déchiffrage impossible : " + str(e)
    rep["ms"] = round((time.perf_counter() - t0) * 1000, 3)
    return rep


# ═══════════════════════════════════════════════════════════════════════════
# 8. ROUTES — chemins RELATIFS à /api/cards/{did}/data (règle 8)
# ═══════════════════════════════════════════════════════════════════════════

def _guard(did: str) -> None:
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")


def _obj(body: Any, what: str = "Le corps") -> dict:
    """Un corps mal formé fait 400, JAMAIS 500 (spec 2.5)."""
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise HTTPException(400, what + " doit être un objet JSON")
    return body


def _bytes_of(b: dict) -> bytes:
    if "b64" in b and b.get("b64") is not None:
        try:
            raw = base64.b64decode(str(b.get("b64")), validate=False)
        except (binascii.Error, ValueError):
            raise HTTPException(400, "Base64 illisible dans « b64 »")
    elif "text" in b and b.get("text") is not None:
        raw = str(b.get("text")).encode("utf-8")
    else:
        raise HTTPException(400, "Rien à lire : fournir « b64 » (octets du "
                                 "fichier) ou « text »")
    if len(raw) > MAX_BYTES:
        raise HTTPException(400, "Fichier trop volumineux (limite "
                            + str(MAX_BYTES // (1024 * 1024)) + " Mo)")
    return raw


def _table_of(b: dict) -> tuple[list, list]:
    cols = b.get("columns")
    rows = b.get("rows")
    if not isinstance(cols, list) or not isinstance(rows, list):
        raise HTTPException(400, "« columns » et « rows » sont attendus "
                                 "(deux listes)")
    if len(cols) > MAX_COLS:
        raise HTTPException(400, "Trop de colonnes (limite "
                            + str(MAX_COLS) + ")")
    if len(rows) > MAX_ROWS:
        raise HTTPException(400, "Trop de lignes (limite "
                            + str(MAX_ROWS) + ")")
    return [str(c) for c in cols], rows


@router.post("/parse")
async def post_parse(did: str, body: Any = Body(default=None)):
    """Octets -> table. Séparateur, encodage et entête devinés."""
    _guard(did)
    b = _obj(body)
    raw = _bytes_of(b)
    sep = str(b.get("sep") or "auto")
    enc = str(b.get("encoding") or "auto")
    head = str(b.get("header") or "auto")
    repair = bool(b.get("repair"))
    try:
        table = await asyncio.to_thread(parse_table, raw, sep, enc, head, repair)
    except HTTPException:
        raise
    except Exception as e:                                  # noqa: BLE001
        logger.exception("cards/data: parse")
        raise HTTPException(500, "Lecture du fichier impossible : " + str(e))
    table["name"] = str(b.get("name") or "")[:120]
    return {"table": table}


@router.post("/build")
async def post_build(did: str, body: Any = Body(default=None)):
    """Table + filtre/tri/quantité/mappage -> cartes."""
    _guard(did)
    b = _obj(body)
    cols, rows = _table_of(b)
    mapping = b.get("map") if isinstance(b.get("map"), dict) else {}
    blank = b.get("blank_unfed")
    blank = True if blank is None else bool(blank)
    try:
        out = await asyncio.to_thread(
            build_deck, cols, rows, mapping, b.get("qty_col"),
            str(b.get("filter") or ""), str(b.get("sort") or ""),
            b.get("off"), b.get("slots"), blank, b.get("frame"))
    except FilterError as e:
        raise HTTPException(400, "Filtre : " + e.msg
                            + " (caractère " + str(e.pos + 1) + ")")
    except HTTPException:
        raise
    except Exception as e:                                  # noqa: BLE001
        logger.exception("cards/data: build")
        raise HTTPException(500, "Construction impossible : " + str(e))
    return out


def clause_report(expr: str, columns: list, rows: Any = None,
                  off: Any = None) -> dict:
    """L'expression -> ses conditions de premier niveau, CHACUNE PESÉE.

    C'est la matière du constructeur à la souris. Le reproche des deux critiques
    était le même : « le filtre reste une petite langue à apprendre, il n'y a
    aucun constructeur de condition à la souris — sur ce point précis il fait
    exactement ce qu'il reproche à l'autre ». Un constructeur qui écrirait ses
    conditions de son côté referait un second analyseur (deux grammaires, deux
    vérités) : il les fabrique, et c'est le MOTEUR qui les redécoupe et les
    compte, ici.

    `n_kept` est le nombre de lignes actives que la condition retient SEULE.
    C'est ce qui manquait pour choisir : sur `atk > 1 et rarete = rare`, savoir
    que la première en garde 3 et la seconde 1 dit tout de suite laquelle taille
    le deck.
    """
    cols = [str(c) for c in columns]
    parts = clause_split(expr)
    dicts: list = []
    if isinstance(rows, list):
        off_set = set()
        if isinstance(off, (list, tuple)):
            for v in off:
                try:
                    off_set.add(int(v))
                except (TypeError, ValueError):
                    continue
        ncol = len(cols)
        for i, r in enumerate(rows[:MAX_ROWS]):
            if i in off_set:
                continue
            r = list(r) if isinstance(r, (list, tuple)) else []
            r = (r + [""] * ncol)[:ncol]
            dicts.append({cols[j]: str(r[j] if r[j] is not None else "")
                          for j in range(ncol)})
    out = []
    for p in parts:
        item = {"expr": p, "ok": True, "error": "", "n_kept": None}
        try:
            pred = compile_filter(p, cols)
        except FilterError as e:
            item.update(ok=False, error=e.msg)
            pred = None
        if pred is not None and dicts:
            item["n_kept"] = sum(1 for d in dicts if pred(d))
        elif pred is None and item["ok"] and dicts:
            item["n_kept"] = len(dicts)          # condition vide : tout passe
        out.append(item)
    tj = top_joins(expr)
    return {"clauses": out, "top_or": bool(tj["or"]), "top_and": bool(tj["and"]),
            "n_active": len(dicts) if isinstance(rows, list) else None}


@router.post("/check")
async def post_check(did: str, body: Any = Body(default=None)):
    """Validation du filtre SEULE. Ne rend jamais d'erreur HTTP sur une
    expression fautive : l'écran l'appelle à chaque frappe, un 400 y
    ferait clignoter un bandeau rouge à chaque lettre tapée.

    Rend AUSSI le découpage en conditions et le poids de chacune, quand la table
    est jointe : c'est le seul endroit où ce découpage existe, et les pastilles
    du constructeur en sont la vue.
    """
    _guard(did)
    b = _obj(body)
    cols = b.get("columns") if isinstance(b.get("columns"), list) else []
    expr = str(b.get("filter") or "")
    rows = b.get("rows") if isinstance(b.get("rows"), list) else None
    if rows is not None and len(rows) > MAX_ROWS:
        rows = rows[:MAX_ROWS]
    try:
        compile_filter(expr, [str(c) for c in cols])
    except FilterError as e:
        return {"check": {"ok": False, "error": e.msg, "pos": e.pos,
                          "clauses": [], "n_active": None}}
    except Exception as e:                                  # noqa: BLE001
        return {"check": {"ok": False, "error": str(e), "pos": 0,
                          "clauses": [], "n_active": None}}
    rep = clause_report(expr, [str(c) for c in cols], rows, b.get("off"))
    return {"check": {"ok": True, "error": "", "pos": -1,
                      "clauses": rep["clauses"], "top_or": rep["top_or"],
                      "top_and": rep["top_and"], "n_active": rep["n_active"]}}


@router.post("/export")
async def post_export(did: str, body: Any = Body(default=None)):
    """Table -> text/csv téléchargeable.

    DEUX PORTÉES, parce qu'il y a deux fichiers différents et qu'en n'en
    servant qu'un on tenait la moitié du livrable :

      · `scope="table"` (défaut) — la table SOURCE. C'est le retour de
        l'aller-retour : relu par /parse il rend la même table, à l'octet près
        quand le BOM est décoché.
      · `scope="deck"`  — le DECK RÉSOLU : une ligne par carte, filtre, tri et
        quantités appliqués, slots en colonnes. C'est le « export CSV du deck »
        de la spec, et il était absent.

    Le deck est RECONSTRUIT ici à partir des mêmes entrées que /build, pas
    envoyé tout fait par l'écran : deux chemins de construction, ce serait deux
    decks qui divergent en silence — la faute exacte que ce fichier existe pour
    éviter.
    """
    _guard(did)
    b = _obj(body)
    cols, rows = _table_of(b)
    scope = str(b.get("scope") or "table").strip().lower()
    if scope not in ("table", "deck"):
        raise HTTPException(400, "Portée inconnue : « " + scope
                            + " » (table ou deck)")
    sep = str(b.get("sep") or ";")
    bom = b.get("bom")
    bom = False if bom is None else bool(bom)
    name = re.sub(r"[^\w.-]+", "_", str(b.get("name") or "deck")) or "deck"
    if scope == "deck":
        mapping = b.get("map") if isinstance(b.get("map"), dict) else {}
        blank = b.get("blank_unfed")
        blank = True if blank is None else bool(blank)
        try:
            out = await asyncio.to_thread(
                build_deck, cols, rows, mapping, b.get("qty_col"),
                str(b.get("filter") or ""), str(b.get("sort") or ""),
                b.get("off"), b.get("slots"), blank)
        except FilterError as e:
            raise HTTPException(400, "Filtre : " + e.msg
                                + " (caractère " + str(e.pos + 1) + ")")
        cols, rows = deck_table(out["cards"], b.get("slots"))
    if not name.lower().endswith((".csv", ".tsv")):
        name += ".tsv" if sep == "\t" else ".csv"
    try:
        data = await asyncio.to_thread(write_csv, cols, rows, sep, bom)
    except Exception as e:                                  # noqa: BLE001
        logger.exception("cards/data: export")
        raise HTTPException(500, "Export impossible : " + str(e))
    return Response(content=data, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":
                             'attachment; filename="' + name + '"',
                             "Content-Length": str(len(data))})


@router.post("/suggest")
async def post_suggest(did: str, body: Any = Body(default=None)):
    """Colonnes + slots RÉELS -> mappage proposé, et ce qui reste orphelin.

    Un seul exemplaire de la table de synonymes, ici. Quand elle vivait dans
    l'écran, elle était indexée sur les identifiants du jeu de repli et ne
    tombait plus dès que P3 publiait les siens (`def` au lieu de `hp`) : « pv »
    restait orpheline face à un slot « Vie » vide.
    """
    _guard(did)
    b = _obj(body)
    cols = b.get("columns") if isinstance(b.get("columns"), list) else []
    return {"suggest": suggest_map([str(c) for c in cols], b.get("slots"),
                                   b.get("map"))}


@router.get("/grammar")
async def get_grammar(did: str):
    """Les opérateurs du filtre, servis par le MOTEUR.

    L'écran affiche « n opérateurs ». Recopier ce nombre à la main, c'est
    fabriquer un badge qui finit par mentir : il vient d'ici, et chaque entrée
    est exécutée par un test sur une vraie table.
    """
    _guard(did)
    return {"ops": list(FILTER_OPS), "joins": list(FILTER_JOINS),
            "n_ops": len(FILTER_OPS), "n_joins": len(FILTER_JOINS)}


def art_index(root) -> tuple[dict, dict]:
    """Le dossier d'images, indexé UNE fois : (nom replié -> nom réel,
    radical replié -> noms réels).

    POURQUOI UN INDEX ET PAS UN `is_file()` PAR VALEUR — c'est la correction du
    reproche « 4 sur 4 est un compteur, pas une preuve de robustesse ».

    `(root / name).is_file()` répond à la CASSE DU SYSTÈME DE FICHIERS : sous
    Windows « OCTO.PNG » trouve `octo.png` et le compteur affiche « 1 sur 1 » ;
    le même fichier, le même CSV, sur le serveur de l'imprimeur en ext4,
    affichent « 0 sur 1 ». Un chiffre qui change avec le disque n'est pas un
    chiffre : c'était le badge le plus fragile de cet écran.

    Ici la comparaison se fait sur des chaînes repliées, donc identique partout,
    et l'URL rendue porte le nom RÉEL du fichier — pas celui que l'utilisateur a
    tapé, qui ne serait servi que sur un disque insensible à la casse.
    """
    by_name: dict = {}
    by_stem: dict = {}
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name)
    except OSError:
        return {}, {}
    for p in entries:
        try:
            if not p.is_file():
                continue
        except OSError:
            continue
        by_name.setdefault(p.name.lower(), p.name)
        stem = p.name.rsplit(".", 1)[0].lower() if "." in p.name else p.name.lower()
        by_stem.setdefault(stem, []).append(p.name)
    return by_name, by_stem


def resolve_art(values: list, root) -> dict:
    """Chaque valeur de la colonne image -> trouvée ou NON, et POURQUOI.

    « On ne sait pas ce qu'il fait quand une image manque » : il le dit, cas par
    cas — casse différente, extension différente (avec le nom du voisin trouvé
    dans le dossier), chemin ignoré, ou introuvable tout court. Il ne SUBSTITUE
    jamais : deviner l'extension mettrait une autre image sur la carte sans le
    dire, ce qui est pire que le trou.
    """
    by_name, by_stem = art_index(root)
    seen: dict = {}
    out = []
    for v in values:
        s = str(v if v is not None else "").strip()
        if s in seen:
            out.append(seen[s])
            continue
        item = {"v": s, "ok": False, "url": "", "kind": "vide", "why": ""}
        if s.startswith(("http://", "https://", "data:")):
            item.update(ok=True, url=s, kind="lien")
        elif s:
            # jamais de traversée : on ne garde QUE le nom de fichier
            name = s.replace("\\", "/").split("/")[-1]
            item["kind"] = "bibliothèque"
            pre = "chemin ignoré, seul le nom de fichier compte — " \
                if name != s else ""
            real = by_name.get(name.lower()) if name not in ("", ".", "..") else None
            if real:
                item.update(ok=True, url="/api/images/" + quote(real))
                if real != name:
                    item["kind"] = "bibliothèque (casse)"
                    item["why"] = pre + "trouvée à la casse près : « " + real + " »"
                elif pre:
                    item["why"] = pre.rstrip("— ")
            else:
                stem = name.rsplit(".", 1)[0].lower() if "." in name else name.lower()
                near = by_stem.get(stem) or []
                if near:
                    item["why"] = (pre + "introuvable — le dossier contient « "
                                   + "», « ".join(near[:3]) + " » : extension "
                                   "différente, et on ne la devine pas (ce "
                                   "serait poser une autre image sans le dire)")
                else:
                    item["why"] = pre + "introuvable dans la bibliothèque"
        seen[s] = item
        out.append(item)
    named = [x for x in out if x["v"]]
    # LE DÉNOMINATEUR EST UN NOMBRE DE FICHIERS, PAS UN NOMBRE DE CLÉS.
    # `len(by_name)` compte des noms REPLIÉS : sur un disque sensible à la casse
    # — ext4, celui du serveur de l'imprimeur — « Octo.png » et « octo.png »
    # cohabitent, et le bandeau annonçait « 115 fichier(s) » pour 116. Un
    # dénominateur qui rétrécit selon le système de fichiers est exactement le
    # défaut qu'on vient de corriger un cran plus haut. `by_stem` garde chaque
    # fichier, lui, donc il les compte tous.
    n_files = sum(len(v) for v in by_stem.values())
    return {"art": out, "n": len(named),
            "n_ok": sum(1 for x in named if x["ok"]),
            "n_missing": sum(1 for x in named if not x["ok"]),
            "n_case": sum(1 for x in named if x["kind"] == "bibliothèque (casse)"),
            "n_files": n_files, "n_names": len(by_name), "folder": str(root)}


@router.post("/artcheck")
async def post_artcheck(did: str, body: Any = Body(default=None)):
    """La colonne image, RÉSOLUE vers la bibliothèque (livrable de la spec).

    Sans ça, « img » n'est qu'une chaîne : on découvre au tirage que 40 cartes
    sur 200 pointaient un fichier absent. Ici chaque valeur est confrontée au
    dossier d'images de l'application, et l'écran met un point rouge sur la
    cellule fautive.
    """
    _guard(did)
    b = _obj(body)
    vals = b.get("values") if isinstance(b.get("values"), list) else []
    if len(vals) > MAX_ROWS:
        raise HTTPException(400, "Trop de valeurs (limite "
                            + str(MAX_ROWS) + ")")
    try:
        from app.config import settings
        root = settings.images_path
    except Exception as e:                                  # noqa: BLE001
        logger.warning("cards/data: bibliotheque d'images injoignable: %s", e)
        raise HTTPException(503, "Bibliothèque d'images injoignable")
    return await asyncio.to_thread(resolve_art, list(vals), root)


@router.post("/pngcheck")
async def post_pngcheck(did: str, body: Any = Body(default=None)):
    """Le fichier de carte livré, lu OCTET PAR OCTET.

    L'écran affichait « en-tête IHDR 815 × 1110, 8 bits/canal » : deux
    dimensions vraies et une profondeur lue dans une DÉCLARATION. C'est
    exactement par là que le badge « 16 bits » d'un autre lot est passé en
    étant faux. Ici l'en-tête est rendu POUR CE QU'IL EST, et la profondeur
    effective est mesurée sur les échantillons dégonflés et défiltrés.

    Ne lève jamais sur un fichier illisible : `png.ok` vaut faux et `png.error`
    dit pourquoi.
    """
    _guard(did)
    b = _obj(body)
    raw = _bytes_of(b)
    deep = b.get("deep")
    deep = True if deep is None else bool(deep)
    return {"png": await asyncio.to_thread(png_report, raw, deep)}


@router.get("/samples")
async def get_samples(did: str):
    # LE DERNIER COMPTE RECOPIÉ, ET IL ÉTAIT FAUX. Cette docstring annonçait un
    # nombre de jeux écrit à la main pendant que `samples()` en servait six —
    # et FastAPI la sert telle quelle dans le schéma OpenAPI, donc c'était bien
    # un chiffre affiché. Le compte ne s'écrit plus nulle part ailleurs que
    # dans la liste elle-même.
    """Les jeux d'essai EMBARQUÉS (0 octet réseau) : un écran vide qui ne
    propose rien perd le duel avant la première fonctionnalité."""
    _guard(did)
    return {"samples": samples()}
