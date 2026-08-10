"""L'APERÇU DOIT MONTRER LE FICHIER — verrou d'orientation du placage.

Pendant sept rondes, le viewport de Material Forge a rendu la matière EN MIROIR
horizontal sur la sphère et le cylindre, et en miroir + retournée sur le tore.
« or martelé » porte du texte lisible (« $DEEPOTUS », « PROTOCOL ») : il se
lisait à l'envers dans l'aperçu pendant que le PNG basecolor téléchargé, lui,
était à l'endroit. L'écran sur lequel l'artiste juge la matière ne montrait pas
le fichier livré.

Ce fichier verrouille l'invariant, pour TOUS les maillages :

  1. `test_aucun_miroir` — le déterminant UV de chaque triangle est négatif.
     C'est la signature « pas de miroir » : avec un enroulement CCW vu de
     l'extérieur et un v qui DESCEND dans l'image, l'aire signée d'un triangle
     dans le plan (u, -v) doit avoir le même signe que son aire signée à
     l'écran. Ce test est indépendant de la caméra : il ne peut pas être
     satisfait en déplaçant le point de vue.

  2. `test_sondes_orientation` — sur des points de sonde où l'orientation
     d'écran est non ambiguë (face avant, faces du cube, capuchons), dP/du
     pointe vers la DROITE de l'écran et dP/dv vers le BAS.

  3. `test_rendu_damier_asymetrique` — le vrai verrou demandé : un damier
     asymétrique connu est plaqué, la scène est RASTÉRISÉE ici même (z-buffer
     en Python pur, pas de dépendance), et les quadrants du damier doivent
     tomber dans les bons quadrants de l'image. Un miroir ou un retournement
     échangerait deux couleurs.

  4. `test_tangente_suit_les_uv` — inverser u sans inverser la tangente
     casserait l'éclairage du relief : la bitangente reconstruite comme le fait
     un moteur, `cross(N, T) * w`, doit pointer dans le sens de dP/dv.

  5. `test_glb_porte_les_uv_corriges` — l'invariant est relu DANS le GLB
     binaire produit : l'aperçu et le fichier exporté sortent du même code, et
     ce test l'atteste sur les octets.

    runtime\\python\\python.exe -m pytest backend/tests/test_uv_orientation.py -v
"""
import io
import json
import math
import struct

import pytest
from PIL import Image

from app.services.gltf_builder import (MESHES, MESH_UV, build_glb, build_mesh)

GLB_MAGIC = 0x46546C67


# ── petite algèbre ──────────────────────────────────────────────────────────
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-12 else (0.0, 0.0, 0.0)


def _tri(g, t):
    """(p0, p1, p2, uv0, uv1, uv2) du t-ième triangle."""
    idx, pos, uv = g["indices"], g["positions"], g["uvs"]
    out = []
    for k in range(3):
        i = idx[t * 3 + k]
        out.append((pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]))
    for k in range(3):
        i = idx[t * 3 + k]
        out.append((uv[i * 2], uv[i * 2 + 1]))
    return out


def _frame(g, t):
    """(normale géométrique, T = dP/du, B = dP/dv, det) du triangle t.
    Retourne None si le triangle est dégénéré en espace ou en UV."""
    p0, p1, p2, t0, t1, t2 = _tri(g, t)
    e1, e2 = _sub(p1, p0), _sub(p2, p0)
    n = _cross(e1, e2)
    if _dot(n, n) < 1e-24:
        return None
    du1, dv1 = t1[0] - t0[0], t1[1] - t0[1]
    du2, dv2 = t2[0] - t0[0], t2[1] - t0[1]
    det = du1 * dv2 - du2 * dv1
    if abs(det) < 1e-15:
        return None
    f = 1.0 / det
    T = tuple((dv2 * e1[k] - dv1 * e2[k]) * f for k in range(3))
    B = tuple((du1 * e2[k] - du2 * e1[k]) * f for k in range(3))
    return _norm(n), T, B, det


# ═══════════════════════════ 1. aucun miroir ════════════════════════════════
@pytest.mark.parametrize("mesh", MESHES)
def test_aucun_miroir(mesh):
    """Le placage ne retourne JAMAIS la matière, sur aucun triangle.

    Preuve du signe attendu : un triangle vu de face, enroulé CCW, a une aire
    signée d'écran positive ; la même aire mesurée dans le plan (u, -v) — u
    vers la droite, v vers le bas, comme dans l'image — vaut `-det`. Les deux
    doivent avoir le même signe, donc det < 0. Le plan, dont le placage n'a
    jamais été touché, sert de témoin : il vérifie que c'est bien la convention
    de la maison et non un signe choisi après coup.
    """
    g = build_mesh(mesh)
    ntri = len(g["indices"]) // 3
    mirrored = []
    tested = 0
    for t in range(ntri):
        fr = _frame(g, t)
        if fr is None:
            continue
        tested += 1
        if fr[3] > 0.0:
            mirrored.append(t)
    assert tested > 0, f"{mesh} : aucun triangle exploitable"
    assert not mirrored, (
        f"{mesh} : {len(mirrored)}/{tested} triangles portent la texture EN "
        f"MIROIR (det > 0). Le premier est le triangle {mirrored[0]}.")


# ═══════════════════════ 2. sondes d'orientation ════════════════════════════
# (point de la surface, droite écran attendue, haut écran attendu)
# Uniquement des points où l'orientation d'écran est NON AMBIGUË : ni pôle de
# sphère (les méridiens y convergent, aucune direction d'écran ne tient), ni
# couronne intérieure de tore (elle regarde l'observateur par le trou, sa
# tangente est logiquement retournée — c'est la géométrie, pas le placage).
PROBES = {
    "sphere": [
        ((0.0, 0.0, 1.0), (1, 0, 0), (0, 1, 0)),
        ((1.0, 0.0, 0.0), (0, 0, -1), (0, 1, 0)),
        ((0.0, 0.0, -1.0), (-1, 0, 0), (0, 1, 0)),
    ],
    "cube": [
        ((0.0, 0.0, 1.0), (1, 0, 0), (0, 1, 0)),
        ((0.0, 0.0, -1.0), (-1, 0, 0), (0, 1, 0)),
        ((1.0, 0.0, 0.0), (0, 0, -1), (0, 1, 0)),
        ((-1.0, 0.0, 0.0), (0, 0, 1), (0, 1, 0)),
        ((0.0, 1.0, 0.0), (1, 0, 0), (0, 0, -1)),
        ((0.0, -1.0, 0.0), (1, 0, 0), (0, 0, 1)),
    ],
    "torus": [
        ((0.0, 0.0, 1.0), (1, 0, 0), (0, 1, 0)),      # couronne extérieure avant
        ((1.0, 0.0, 0.0), (0, 0, -1), (0, 1, 0)),     # couronne extérieure droite
    ],
    "cylinder": [
        ((0.0, 0.0, 0.7), (1, 0, 0), (0, 1, 0)),      # paroi avant
        ((0.0, 0.9, 0.0), (1, 0, 0), (0, 0, -1)),     # capuchon haut
        ((0.0, -0.9, 0.0), (1, 0, 0), (0, 0, 1)),     # capuchon bas
    ],
    "plane": [((0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0))],
    "tiled": [((0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0))],
}


@pytest.mark.parametrize("mesh", MESHES)
def test_sondes_orientation(mesh):
    """u va vers la droite de l'écran, v vers le bas — là où ça a un sens."""
    g = build_mesh(mesh)
    ntri = len(g["indices"]) // 3
    for point, right, up in PROBES[mesh]:
        best, bestd = None, 1e9
        for t in range(ntri):
            fr = _frame(g, t)
            if fr is None:
                continue
            p0, p1, p2, _, _, _ = _tri(g, t)
            c = tuple((p0[k] + p1[k] + p2[k]) / 3.0 for k in range(3))
            d = sum((c[k] - point[k]) ** 2 for k in range(3))
            if d < bestd:
                best, bestd = fr, d
        assert best is not None, f"{mesh} : aucun triangle près de {point}"
        _, T, B, _ = best
        tr, bu = _dot(_norm(T), right), _dot(_norm(B), up)
        assert tr > 0.7, (
            f"{mesh} en {point} : u ne part pas vers la droite de l'écran "
            f"(dP/du . droite = {tr:+.3f}) — la matière est en miroir.")
        assert bu < -0.7, (
            f"{mesh} en {point} : v ne descend pas dans l'écran "
            f"(dP/dv . haut = {bu:+.3f}) — la matière est retournée.")


# ═══════════════ 3. le rendu d'un damier asymétrique connu ══════════════════
# Damier volontairement ASYMÉTRIQUE dans les deux axes : quatre quadrants de
# couleurs distinctes (rouge en haut-gauche, vert en haut-droite, bleu en
# bas-gauche, jaune en bas-droite) plus un « F » clair, une lettre qu'aucun
# miroir ni aucune rotation ne laisse identique à elle-même.
QUAD = {"TL": (220, 40, 40), "TR": (40, 190, 70),
        "BL": (50, 90, 230), "BR": (235, 200, 40)}


def _mire(size=256):
    im = Image.new("RGB", (size, size))
    px = im.load()
    h = size // 2
    for y in range(size):
        for x in range(size):
            px[x, y] = QUAD["TL" if y < h and x < h else
                            "TR" if y < h else
                            "BL" if x < h else "BR"]
    # un « F » clair, centré, dessiné en pixels (aucune police requise)
    bar = max(2, size // 24)
    x0, y0, w, hh = size // 3, size // 4, size // 3, size // 2
    for y in range(y0, y0 + hh):
        for x in range(x0, x0 + bar):
            px[x, y] = (250, 250, 250)
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + bar):
            px[x, y] = (250, 250, 250)
    for x in range(x0, x0 + int(w * 0.7)):
        for y in range(y0 + hh // 2, y0 + hh // 2 + bar):
            px[x, y] = (250, 250, 250)
    return im


def _raster(mesh, uv_repeat, tex, side=160, span=1.25):
    """Rendu orthographique z-buffer, caméra en +Z regardant -Z, X à droite et
    Y en haut — exactement le repère d'un viewer glTF au chargement. Rendu
    plein écran, sans éclairage : on ne teste pas la lumière, on teste QUEL
    TEXEL arrive à QUEL PIXEL.  Retourne (image, masque de couverture)."""
    g = build_mesh(mesh, uv_repeat)
    tw, th = tex.size
    tpx = tex.load()
    out = Image.new("RGB", (side, side), (0, 0, 0))
    opx = out.load()
    cov = [[False] * side for _ in range(side)]
    zbuf = [[-1e9] * side for _ in range(side)]

    def to_px(p):
        return ((p[0] + span) / (2 * span) * side,
                (span - p[1]) / (2 * span) * side)

    for t in range(len(g["indices"]) // 3):
        p0, p1, p2, t0, t1, t2 = _tri(g, t)
        n = _cross(_sub(p1, p0), _sub(p2, p0))
        if n[2] <= 0.0:                       # face arrière : éliminée
            continue
        a, b, c = to_px(p0), to_px(p1), to_px(p2)
        area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(area) < 1e-9:
            continue
        xs = [a[0], b[0], c[0]]
        ys = [a[1], b[1], c[1]]
        for y in range(max(0, int(min(ys))), min(side, int(max(ys)) + 2)):
            for x in range(max(0, int(min(xs))), min(side, int(max(xs)) + 2)):
                fx, fy = x + 0.5, y + 0.5
                w0 = ((b[0] - a[0]) * (fy - a[1]) - (fx - a[0]) * (b[1] - a[1])) / area
                w1 = ((fx - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (fy - a[1])) / area
                w2 = 1.0 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
                z = w2 * p0[2] + w1 * p1[2] + w0 * p2[2]
                if z <= zbuf[y][x]:
                    continue
                zbuf[y][x] = z
                u = w2 * t0[0] + w1 * t1[0] + w0 * t2[0]
                v = w2 * t0[1] + w1 * t1[1] + w0 * t2[1]
                sx = int((u % 1.0) * tw) % tw          # REPEAT, comme le sampler
                sy = int((v % 1.0) * th) % th
                opx[x, y] = tpx[sx, sy]
                cov[y][x] = True
    return out, cov


def _quadrant_lu(img, cov, x, y):
    """Le quadrant de la mire dont la couleur est rendue en (x, y), ou None."""
    if not cov[y][x]:
        return None
    r, g, b = img.getpixel((x, y))
    best, bd = None, 1e9
    for name, col in QUAD.items():
        d = (r - col[0]) ** 2 + (g - col[1]) ** 2 + (b - col[2]) ** 2
        if d < bd:
            best, bd = name, d
    return best if bd < 6000 else None       # un pixel du « F » ne répond pas


# (maillage, répétition UV, écart des sondes au centre, en fraction d'image).
# Les répétitions sont choisies pour qu'UNE tuile complète couvre la face
# visible ; l'écart place les quatre sondes dans les quatre quadrants de CETTE
# tuile, franchement à l'intérieur de la silhouette.
RENDERS = [
    ("plane", (1.0, 1.0), 0.25),
    ("tiled", (1.0, 1.0), 0.065),     # 3x3 : sondes dans la tuile CENTRALE
    ("sphere", (2.0, 1.0), 0.20),
    ("cylinder", (2.0, 1.0), 0.20),
]


@pytest.mark.parametrize("mesh,rep,off", RENDERS)
def test_rendu_damier_asymetrique(mesh, rep, off):
    """Le rendu correspond à la texture : haut-gauche rouge, haut-droite vert,
    bas-gauche bleu, bas-droite jaune. Un miroir horizontal échangerait rouge
    et vert ; un retournement vertical échangerait rouge et bleu."""
    tex = _mire()
    img, cov = _raster(mesh, rep, tex)
    side = img.size[0]
    d = int(off * side)
    attendu = {"TL": (side // 2 - d, side // 2 - d),
               "TR": (side // 2 + d, side // 2 - d),
               "BL": (side // 2 - d, side // 2 + d),
               "BR": (side // 2 + d, side // 2 + d)}
    for want, (x, y) in attendu.items():
        got = _quadrant_lu(img, cov, x, y)
        assert got is not None, f"{mesh} : rien de rendu en {want} ({x},{y})"
        assert got == want, (
            f"{mesh} : le quadrant {want} de la texture est rendu à la place "
            f"{got} — l'aperçu ne montre pas le fichier.")


def test_le_plan_rend_la_texture_au_pixel():
    """Témoin le plus dur : le plan couvre exactement la tuile, donc le rendu
    DOIT être la mire elle-même. On compare pixel à pixel, « F » compris."""
    tex = _mire()
    img, cov = _raster("plane", (1.0, 1.0), tex, side=120, span=1.0)
    ref = tex.resize((120, 120), Image.NEAREST)
    ecarts = 0
    total = 0
    for y in range(2, 118):
        for x in range(2, 118):
            if not cov[y][x]:
                continue
            total += 1
            a, b = img.getpixel((x, y)), ref.getpixel((x, y))
            if sum((a[k] - b[k]) ** 2 for k in range(3)) > 3000:
                ecarts += 1
    assert total > 10000, "le plan n'a pas couvert l'écran"
    assert ecarts / total < 0.02, (
        f"{ecarts}/{total} pixels ne correspondent pas à la mire — le rendu "
        "n'est pas la texture.")


# ═══════════════ 4. la tangente suit les UV (relief éclairé juste) ══════════
@pytest.mark.parametrize("mesh", MESHES)
def test_tangente_suit_les_uv(mesh):
    """Un moteur reconstruit la bitangente par `cross(N, T) * w`. Elle doit
    tomber dans le sens de dP/dv, sinon la normal map éclaire les creux comme
    des bosses. C'est le piège d'un miroir corrigé à moitié."""
    g = build_mesh(mesh)
    tan, nrm, idx = g["tangents"], g["normals"], g["indices"]
    verifs = 0
    for t in range(len(idx) // 3):
        fr = _frame(g, t)
        if fr is None:
            continue
        _, T, B, _ = fr
        Bn = _norm(B)
        for k in range(3):
            i = idx[t * 3 + k]
            N = (nrm[i * 3], nrm[i * 3 + 1], nrm[i * 3 + 2])
            Tv = (tan[i * 4], tan[i * 4 + 1], tan[i * 4 + 2])
            w = tan[i * 4 + 3]
            assert w in (1.0, -1.0)
            bt = _cross(N, Tv)
            bt = (bt[0] * w, bt[1] * w, bt[2] * w)
            if _dot(bt, bt) < 1e-12:
                continue
            d = _dot(_norm(bt), Bn)
            # sommets partagés entre deux orientations (coutures, pôles) :
            # on n'exige la concordance que là où la tangente est franche.
            if abs(_dot(_norm(Tv), _norm(T))) < 0.6:
                continue
            verifs += 1
            assert d > 0.0, (
                f"{mesh} : bitangente reconstruite opposée à dP/dv "
                f"(produit {d:+.3f}) — le relief serait éclairé à l'envers.")
    assert verifs > 0, f"{mesh} : aucune tangente franche à vérifier"


# ═══════════════ 5. l'invariant survit à l'export GLB ══════════════════════
def _parse_glb(blob):
    magic, ver, total = struct.unpack_from("<III", blob, 0)
    assert magic == GLB_MAGIC and ver == 2 and total == len(blob)
    off, js, bins = 12, None, b""
    while off < total:
        clen, ctype = struct.unpack_from("<II", blob, off)
        off += 8
        chunk = blob[off:off + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bins = chunk
        off += clen
    return js, bins


def _read_acc(js, bins, ai, comps):
    acc = js["accessors"][ai]
    bv = js["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    n = acc["count"]
    fmt = {5126: "f", 5125: "I", 5123: "H"}[acc["componentType"]]
    sz = {"f": 4, "I": 4, "H": 2}[fmt]
    return list(struct.unpack_from("<" + fmt * (n * comps), bins, base)), n


@pytest.mark.parametrize("mesh", MESHES)
def test_glb_porte_les_uv_corriges(mesh):
    """Relu DANS le binaire exporté : mêmes UV, même invariant. L'aperçu du
    viewport et le GLB téléchargé sortent du même générateur — ce test
    l'atteste sur les octets, pas sur l'intention."""
    img = io.BytesIO()
    Image.new("RGB", (8, 8), (128, 128, 128)).save(img, "PNG")
    blob = build_glb({"basecolor": img.getvalue()}, {}, mesh,
                     uv_repeat=MESH_UV[mesh])
    js, bins = _parse_glb(blob)
    prim = js["meshes"][0]["primitives"][0]
    pos, nv = _read_acc(js, bins, prim["attributes"]["POSITION"], 3)
    uv, _ = _read_acc(js, bins, prim["attributes"]["TEXCOORD_0"], 2)
    idx, ni = _read_acc(js, bins, prim["indices"], 1)
    mirrored = 0
    tested = 0
    for t in range(ni // 3):
        i0, i1, i2 = idx[t * 3], idx[t * 3 + 1], idx[t * 3 + 2]
        p = [(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]) for i in (i0, i1, i2)]
        q = [(uv[i * 2], uv[i * 2 + 1]) for i in (i0, i1, i2)]
        n = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
        if _dot(n, n) < 1e-20:
            continue
        det = ((q[1][0] - q[0][0]) * (q[2][1] - q[0][1]) -
               (q[2][0] - q[0][0]) * (q[1][1] - q[0][1]))
        if abs(det) < 1e-12:
            continue
        tested += 1
        if det > 0:
            mirrored += 1
    assert tested > 0
    assert mirrored == 0, (
        f"{mesh} : le GLB exporté contient {mirrored}/{tested} triangles en "
        "miroir — le fichier livré ne correspond pas aux PNG.")
