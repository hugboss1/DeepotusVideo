"""Lot G (D7) — le PDF d'impression du Vectorlab, stdlib pure (patron
print3d.py) : une page par tranche, l'image JPEG de la tranche (rendue au
dpi choisi côté client) posée pleine page en XObject DCTDecode. Pages en
POINTS depuis les millimètres (1 mm = 72 / 25.4 pt). Pas de vecteur : un
interpréteur SVG serveur sortirait de D7 — dit dans le plan du lot G.
"""
from __future__ import annotations

_MM_PT = 72.0 / 25.4


def _pt(mm: float) -> str:
    v = round(float(mm) * _MM_PT, 2)
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def creer_pdf(pages: list[dict]) -> bytes:
    """pages = [{w_mm, h_mm, jpeg (bytes), w_px, h_px}] → octets PDF 1.4."""
    if not pages:
        raise ValueError("pdf : aucune page")
    for p in pages:
        if not (float(p.get("w_mm", 0)) > 0 and float(p.get("h_mm", 0)) > 0):
            raise ValueError("pdf : taille de page nulle")
        jpeg = p.get("jpeg") or b""
        if not (jpeg[:2] == b"\xff\xd8" and jpeg[-2:] == b"\xff\xd9"):
            raise ValueError("pdf : une page n'est pas un JPEG (SOI/EOI)")
        if not (int(p.get("w_px", 0)) >= 1 and int(p.get("h_px", 0)) >= 1):
            raise ValueError("pdf : dimensions pixel requises")

    objets: list[bytes] = []          # objets[i] = corps de l'objet i+1

    def ajouter(corps: bytes) -> int:
        objets.append(corps)
        return len(objets)

    catalogue = ajouter(b"")           # 1 : rempli à la fin (référence les pages)
    pages_obj = ajouter(b"")           # 2 : /Pages
    kids = []
    for p in pages:
        w, h = _pt(p["w_mm"]), _pt(p["h_mm"])
        jpeg = p["jpeg"]
        img = ajouter(
            b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB "
            b"/BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n" % (int(p["w_px"]), int(p["h_px"]), len(jpeg))
            + jpeg + b"\nendstream")
        contenu = f"q {w} 0 0 {h} 0 0 cm /Im0 Do Q".encode()
        flux = ajouter(b"<< /Length %d >>\nstream\n" % len(contenu) + contenu + b"\nendstream")
        page = ajouter(
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {w} {h}] "
            f"/Resources << /XObject << /Im0 {img} 0 R >> >> /Contents {flux} 0 R >>".encode())
        kids.append(page)
    objets[pages_obj - 1] = (f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>").encode()
    objets[catalogue - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode()

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, corps in enumerate(objets, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + corps + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(objets) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, catalogue, xref)
    return bytes(out)
