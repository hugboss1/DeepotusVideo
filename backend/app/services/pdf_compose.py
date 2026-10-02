"""Tâche #65 (plan chapitres T14, 02/10/2026) — composer des PDF de TEXTE et d'IMAGES, sur pypdf (décision du 02/10 :
comme Card Forge, `cards/print.py:build_pdf` — aucune table xref écrite à la main, métadonnées bien encodées).

Polices : les 14 standard (Helvetica, Courier…) en WinAnsiEncoding — rien d'embarqué. ’ « » — – … œ € passent ;
ce qui n'est pas dans cp1252 est REMPLACÉ au plus proche (ł→l par décomposition, sinon « ? ») et COMPTÉ : l'appelant
le dit (décision du 02/10). Les largeurs sont MESURÉES : Helvetica par Arial (métriquement identique, présente sous
Windows), Courier à 600/1000 pour tout glyphe ; sans Arial, une table de repli.
Images : JPEG (DCTDecode), alpha composé sur blanc, réduites à la taille utile, et une image identique n'est écrite
qu'UNE fois (clé : sha1 des octets encodés).
"""
from __future__ import annotations

import hashlib
import io
import unicodedata
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFont

A4 = (595.28, 841.89)
LETTER = (612.0, 792.0)
POLICES = {"H": "Helvetica", "HB": "Helvetica-Bold", "HI": "Helvetica-Oblique", "C": "Courier", "CB": "Courier-Bold"}
_TTF = {"H": "arial.ttf", "HB": "arialbd.ttf", "HI": "ariali.ttf"}
_FONTES = Path("C:/Windows/Fonts")


def winansi(s: str) -> tuple[bytes, int]:
    """(octets cp1252, nombre de caractères REMPLACÉS). ł→l, ő→o par décomposition ; le reste -> « ? »."""
    out, n = bytearray(), 0
    for ch in s:
        try:
            out += ch.encode("cp1252")
            continue
        except UnicodeEncodeError:
            pass
        n += 1
        base = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
        repli = {"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O", "ı": "i", "ħ": "h"}.get(ch, base)
        try:
            out += repli.encode("cp1252") if repli else b"?"
        except UnicodeEncodeError:
            out += b"?"
    return bytes(out), n


@lru_cache(maxsize=8)
def _ttf(cle: str):
    f = _FONTES / _TTF.get(cle, "")
    try:
        return ImageFont.truetype(str(f), 1000) if cle in _TTF and f.is_file() else None
    except OSError:
        return None


def largeur(s: str, police: str, taille: float) -> float:
    """La largeur en points de `s` telle qu'elle sera IMPRIMÉE (après remplacement WinAnsi)."""
    if police.startswith("C"):
        return len(s) * 0.6 * taille
    octets, _n = winansi(s)
    txt = octets.decode("cp1252", errors="replace")
    f = _ttf(police)
    if f is not None:
        return f.getlength(txt) * taille / 1000
    return sum(278 if c in " .,;:'!|il" else 1000 if c in "—…MWŒ" else 556 for c in txt) * taille / 1000


def couper(texte: str, police: str, taille: float, largeur_max: float) -> list[str]:
    """Les lignes d'un paragraphe (sans saut), coupées aux espaces ; un mot trop long est coupé au caractère."""
    lignes, cur = [], ""
    for mot in texte.split(" "):
        essai = (cur + " " + mot) if cur else mot
        if largeur(essai, police, taille) <= largeur_max:
            cur = essai
            continue
        if cur:
            lignes.append(cur)
        while largeur(mot, police, taille) > largeur_max and len(mot) > 1:
            k = len(mot)
            while k > 1 and largeur(mot[:k], police, taille) > largeur_max:
                k -= 1
            lignes.append(mot[:k])
            mot = mot[k:]
        cur = mot
    lignes.append(cur)
    return lignes


def _esc(b: bytes) -> bytes:
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _n(v: float) -> str:
    return ("%.2f" % v).rstrip("0").rstrip(".")


class Document:
    """Des pages de texte et d'images ; `octets(titre)` rend le PDF. Coordonnées en points, origine EN HAUT à gauche
    (y descend) : la conversion vers le repère PDF est faite ici."""

    def __init__(self, taille=A4):
        self.l, self.h = taille
        self.pages: list[dict] = []
        self.remplacements = 0
        self._images: dict[str, tuple[bytes, int, int]] = {}
        self.nouvelle_page()

    def nouvelle_page(self) -> None:
        self.pages.append({"ops": [], "images": set()})

    @property
    def _p(self) -> dict:
        return self.pages[-1]

    def texte(self, x: float, y: float, s: str, police: str = "H", taille: float = 11, gris: float | None = None) -> None:
        """`s` posé avec sa LIGNE DE BASE à `y` (depuis le haut)."""
        octets, n = winansi(s)
        self.remplacements += n
        couleur = f"{_n(gris)} g " if gris is not None else ""
        self._p["ops"].append(f"BT {couleur}/{police} {_n(taille)} Tf {_n(x)} {_n(self.h - y)} Td (".encode("ascii")
                              + _esc(octets) + b") Tj ET" + (b" 0 g" if gris is not None else b""))

    def texte_droite(self, x_droite: float, y: float, s: str, police: str = "H", taille: float = 11) -> None:
        self.texte(x_droite - largeur(s, police, taille), y, s, police, taille)

    def trait(self, x1: float, y1: float, x2: float, y2: float, epaisseur: float = 0.5, gris: float = 0.6) -> None:
        self._p["ops"].append(f"q {_n(gris)} G {_n(epaisseur)} w {_n(x1)} {_n(self.h - y1)} m {_n(x2)} {_n(self.h - y2)} l S Q"
                              .encode("ascii"))

    def cadre(self, x: float, y: float, l: float, h: float, gris: float = 0.75, epaisseur: float = 0.5) -> None:
        self._p["ops"].append(f"q {_n(gris)} G {_n(epaisseur)} w {_n(x)} {_n(self.h - y - h)} {_n(l)} {_n(h)} re S Q"
                              .encode("ascii"))

    def image(self, chemin, x: float, y: float, l: float, h: float, dpi: int = 150) -> tuple[float, float, float, float] | None:
        """L'image ENTIÈRE dans la boîte (l×h), proportions gardées, centrée ; rend la boîte réelle, ou None si
        l'image est illisible. Réduite à `dpi` pour la taille posée, alpha composé sur blanc, JPEG."""
        try:
            im = Image.open(chemin)
            im.load()
        except Exception:
            return None
        iw, ih = im.size
        k = min(l / iw, h / ih)
        pl, ph = iw * k, ih * k
        px, py = x + (l - pl) / 2, y + (h - ph) / 2
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            fond = Image.new("RGB", im.size, (255, 255, 255))
            fond.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[3])
            im = fond
        else:
            im = im.convert("RGB")
        cible = (max(1, round(pl / 72 * dpi)), max(1, round(ph / 72 * dpi)))
        if cible[0] < iw:
            im = im.resize(cible, Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85, optimize=True)
        data = buf.getvalue()
        cle = "Im" + hashlib.sha1(data).hexdigest()[:16]
        self._images.setdefault(cle, (data, im.size[0], im.size[1]))
        self._p["images"].add(cle)
        self._p["ops"].append(f"q {_n(pl)} 0 0 {_n(ph)} {_n(px)} {_n(self.h - py - ph)} cm /{cle} Do Q".encode("ascii"))
        return px, py, pl, ph

    def octets(self, titre: str = "", auteur: str = "Deepotus") -> bytes:
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject
        w = PdfWriter()
        fontes = {}
        for cle, nom in POLICES.items():
            f = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                  NameObject("/BaseFont"): NameObject("/" + nom),
                                  NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
            fontes[cle] = w._add_object(f)
        xobj = {}
        for cle, (data, iw, ih) in self._images.items():
            xo = DecodedStreamObject()
            xo.set_data(data)
            xo.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                       NameObject("/Width"): NumberObject(iw), NameObject("/Height"): NumberObject(ih),
                       NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8),
                       NameObject("/Filter"): NameObject("/DCTDecode")})
            xobj[cle] = w._add_object(xo)
        for p in self.pages:
            page = w.add_blank_page(width=self.l, height=self.h)
            res = page[NameObject("/Resources")]
            res[NameObject("/Font")] = DictionaryObject({NameObject("/" + k): v for k, v in fontes.items()})
            if p["images"]:
                res[NameObject("/XObject")] = DictionaryObject({NameObject("/" + k): xobj[k] for k in sorted(p["images"])})
            cs = DecodedStreamObject()
            cs.set_data(b"\n".join(p["ops"]))
            page[NameObject("/Contents")] = w._add_object(cs)
        w.add_metadata({"/Title": titre, "/Producer": "Deepotus Atelier", "/Author": auteur})
        out = io.BytesIO()
        w.write(out)
        return out.getvalue()
