# -*- coding: utf-8 -*-
"""t121 — le PDF VECTORIEL du Vectorlab, relu par un VRAI lecteur (pypdf, présent dans le python embarqué).

Le PDF est écrit côté navigateur par frontend/vectorlab/js/mod-pdf.js (pur) : ce banc le rejoue par node, avec la
compression Flate du vrai export, puis le relit comme le ferait une imprimerie — pages, MediaBox, opérateurs, images,
groupes de transparence. Le banc node qa/pdf.test.mjs lit les flux en clair ; celui-ci prouve que le fichier COMPLET
s'ouvre et se décode.

Run: python tests/test_vector_pdf.py   (depuis backend/)"""
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
VL = RACINE / "frontend" / "vectorlab"
NODE = shutil.which("node")

pypdf = pytest.importorskip("pypdf")
pytestmark = pytest.mark.skipif(not NODE, reason="node absent")

# un script node qui écrit les PDF des scénarios dans un dossier
SCRIPT = r"""
import { pdf_page, pdf_assembler } from "%MOD%";
import { writeFileSync } from "node:fs";
const out = process.argv[2];
const base = (objets, extra = {}) => ({ v: 1, nom: "P", taille: { w: 300, h: 200 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }], ...extra });
const C = { x: 0, y: 0, w: 300, h: 200 };

// 1. tout vectoriel : rect, ellipse, chemin transformé, groupe écrêté, texte en glyphes
const vec = base([
  { id: "r", type: "rect", x: 10, y: 10, w: 100, h: 50, rx: 8, style: { fond: "#FF0000", contour: "#000000", epaisseur: 2 } },
  { id: "e", type: "ellipse", cx: 200, cy: 100, rx: 40, ry: 20, style: { fond: "#00FF00" } },
  { id: "p", type: "path", d: "M 0 0 L 30 0 Q 40 10 30 20 Z", transform: "rotate(30 15 10)", style: { fond: "#0000FF", opacite: 0.5 } },
  { id: "g", type: "groupe", clip: "cc", style: {}, enfants: [
    { id: "cc", type: "ellipse", cx: 60, cy: 150, rx: 30, ry: 30, style: {} },
    { id: "rr", type: "rect", x: 20, y: 110, w: 90, h: 90, style: { fond: "#FF00FF" } }] },
  { id: "t", type: "texte", x: 150, y: 180, contenu: "H", style: { fond: "#222222", corps: 20 } },
], { fond: "#FFFFFF" });
writeFileSync(out + "/vectoriel.pdf", await pdf_assembler([pdf_page(vec, C, { dpi: 72,
  glyphes: (o) => o.id === "t" ? [{ car: "H", d: "M 150 165 L 155 165 L 155 180 L 150 180 Z" }] : null })]));

// 2. un raster (effet) fourni en RGBA 4 x 3, dans un calque TRANSLUCIDE (le raster vit dans le Form du calque)
const ras = base([
  { id: "v", type: "rect", x: 0, y: 0, w: 50, h: 50, style: { fond: "#000000" } },
  { id: "fx", type: "rect", x: 60, y: 60, w: 40, h: 30, style: { fond: "#000000", effets: [{ type: "ombre" }] } },
]);
ras.calques[0].opacite = 0.6;
const p = pdf_page(ras, C, { dpi: 72 });
const rgba = new Uint8Array(4 * 4 * 3);
for (let i = 0; i < 12; i++) rgba.set([i * 20, 255 - i * 20, 7, i * 21], 4 * i);
writeFileSync(out + "/raster.pdf", await pdf_assembler([{ ...p, images: { I1: { x: 60, y: 60, w: 40, h: 30, largeur: 4, hauteur: 3, rgba } } }]));
writeFileSync(out + "/raster.json", JSON.stringify({ rasters: p.rasters, stats: p.stats, rgba: [...rgba] }));

// 3. deux pages, dpi 300 : 300 x 200 px → 72 x 48 pt
writeFileSync(out + "/pages.pdf", await pdf_assembler([pdf_page(vec, C, { dpi: 300, glyphes: () => null,
  }), pdf_page(base([]), { x: 0, y: 0, w: 150, h: 100 }, { dpi: 300 })].map((x) => ({ ...x, images: Object.fromEntries(
  x.rasters.map((r) => [r.nom, { x: 0, y: 0, w: 1, h: 1, largeur: 1, hauteur: 1, rgba: new Uint8Array([0, 0, 0, 255]) }])) }))));
"""


@pytest.fixture(scope="module")
def pdfs():
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzpdf_"))
    s = d / "fabrique.mjs"
    s.write_text(SCRIPT.replace("%MOD%", (VL / "js" / "mod-pdf.js").as_uri()), encoding="utf-8")
    r = subprocess.run([NODE, str(s), str(d)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr
    return d


def _ops(contenu):
    return [op.decode() if isinstance(op, bytes) else op for _args, op in contenu.operations]


def test_le_pdf_vectoriel_s_ouvre_et_ne_porte_aucune_image(pdfs):
    lu = pypdf.PdfReader(str(pdfs / "vectoriel.pdf"))
    assert len(lu.pages) == 1
    pg = lu.pages[0]
    assert [float(v) for v in pg.mediabox] == [0, 0, 300, 200]
    ops = _ops(pg.get_contents())
    # du VECTEUR : chemins, cubiques, remplissage, trait, écrêtage
    for op in ("cm", "m", "l", "c", "h", "f", "B", "W", "n"):
        assert op in ops, (op, sorted(set(ops)))
    assert ops.count("q") == ops.count("Q"), "q/Q équilibrés : aucun état graphique ne fuit"
    xobj = pg["/Resources"].get("/XObject", {})
    assert not [k for k, v in xobj.items() if v.get_object().get("/Subtype") == "/Image"], "aucune image"
    # l'opacité du chemin bleu : un ExtGState ca 0.5
    gs = pg["/Resources"]["/ExtGState"]
    assert any(float(g.get_object()["/ca"]) == 0.5 for g in gs.values())


def test_le_raster_relu_au_pixel_avec_son_alpha(pdfs):
    info = json.loads((pdfs / "raster.json").read_text("utf-8"))
    assert [r["id"] for r in info["rasters"]] == ["fx"] and info["rasters"][0]["raison"] == "effet"
    assert info["stats"] == {"vectoriels": 1, "rasterises": 1}
    lu = pypdf.PdfReader(str(pdfs / "raster.pdf"))
    pg = lu.pages[0]
    xobj = {k: v.get_object() for k, v in pg["/Resources"]["/XObject"].items()}
    images = {k: v for k, v in xobj.items() if v["/Subtype"] == "/Image"}
    formes = {k: v for k, v in xobj.items() if v["/Subtype"] == "/Form"}
    assert list(images) == ["/I1"] and len(formes) == 1
    im = images["/I1"]
    assert (im["/Width"], im["/Height"]) == (4, 3)
    rgba = info["rgba"]
    assert im.get_data() == bytes(v for i in range(12) for v in rgba[4 * i:4 * i + 3]), "RGB relu au pixel"
    assert im["/SMask"].get_object().get_data() == bytes(rgba[4 * i + 3] for i in range(12)), "alpha relu au pixel"
    # le calque translucide : UN groupe de transparence, et le raster est posé DANS son flux
    f = next(iter(formes.values()))
    assert f["/Group"]["/S"] == "/Transparency"
    ff = pypdf.generic.ContentStream(f, lu)
    assert "Do" in _ops(ff) and b"/I1 Do" in f.get_data(), f.get_data()[:300]
    assert b"%%RASTER" not in f.get_data() and b"%%RASTER" not in pg.get_contents().get_data()
    assert any(abs(float(g.get_object()["/ca"]) - 0.6) < 1e-9 for g in pg["/Resources"]["/ExtGState"].values())


def test_deux_pages_au_dpi_du_document(pdfs):
    lu = pypdf.PdfReader(str(pdfs / "pages.pdf"))
    assert len(lu.pages) == 2
    assert [round(float(v), 3) for v in lu.pages[0].mediabox] == [0, 0, 72, 48]
    assert [round(float(v), 3) for v in lu.pages[1].mediabox] == [0, 0, 36, 24]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
