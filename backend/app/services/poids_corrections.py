# -*- coding: utf-8 -*-
"""t396 + t397 (31/10/2026) — les POIDS de peau de l'écran Affiner du 3D Studio : lecture, écriture, corrections.

Relevé de Sorceress (§6 de l'inventaire, « Refine ») : on repeint les poids au pinceau (front, poids_calc.js), puis
quatre corrections automatiques numérotées et un « correctif en un clic ». Ici, en Python pur, sans dépendance :

  - `lire_peau` : le GLB skinné, ses poids (JOINTS_0 / WEIGHTS_0) rapportés aux NŒUDS d'os, ses positions de repos en
    repère monde (rig_local.lire_modele les cuit déjà), et un maillage SOUDÉ : deux sommets de même position (couture
    d'UV) forment un seul POINT, sans quoi une couture d'UV couperait un îlot en deux. Les corrections travaillent sur
    les points ; l'écriture rend à chaque sommet le poids de son point.
  - `ecrire_sommets` : les poids peints au pinceau (par primitive, seuls les sommets touchés) → une version de plus.
  - les CORRECTIONS (chacune rend un compte rendu ; aucune ne touche aux os, aux positions ni aux clips) :
      1. `orphelins`   : pour un os, les composantes connexes (adjacence du maillage soudé) des points où son poids
                         dépasse un seuil ; la plus grande est le membre, les autres sont des ÎLOTS, rendus (option)
                         à l'os qui domine leur bordure ;
      2. `confinement` : clavicule, bras, cuisse (ou un os choisi) — un point loin du SEGMENT de l'os (au-delà de
                         `portee` × sa longueur) perd une part de ce poids (`force`, 70 % par défaut, proportionnelle à
                         l'excès de distance), donnée à l'os voisin déjà présent sur le point le plus proche (à défaut,
                         au parent) ; `epaules` reconstruit la région d'épaule : la masse colonne + clavicule + bras y
                         est répartie par l'inverse de la distance⁴ aux trois segments (un gradient), fondue avec
                         l'existant vers le bord de la région ;
      3. `coutures`    : les frontières entre os dominants, un COLLIER de N anneaux autour, lissé (moyenne des
                         voisins, itérations de Jacobi : l'ordre de parcours ne compte pas, la symétrie est gardée) ;
                         « seulement les déformées » : le collier est réduit aux points dont une arête s'étire de plus
                         de 5 % sous la pose donnée ;
      4. `guerison`    : sous une ou plusieurs POSES (rotations d'os), les arêtes trop étirées ou comprimées (± 25 %)
                         sont repérées par skinning linéaire ; les poids de leurs extrémités sont diffusés vers la
                         moyenne de leurs voisins, et on recommence (quatre passes au plus par pose).
         VERSION SIMPLIFIÉE, assumée : Sorceress corrige aussi les triangles effondrés et les plis ; ici seul
         l'étirement des arêtes est mesuré, et la pose est un ensemble de rotations LOCALES d'os (pas un clip
         interpolé : le front échantillonne le clip en quelques poses).
      `tout` (le correctif en un clic) = épaules → confinement → coutures → guérison sur une petite BATTERIE de poses
      d'amplitude (épaule, coude, hanche, genou, poignet, cheville, cou, torsion), en UNE version.

Les poids écrits restent normalisés (somme 1, quatre influences au plus). L'écriture se fait EN PLACE dans les vues
des accesseurs quand leur format le permet (le fichier ne grossit pas d'une version à l'autre), sinon en accesseurs
neufs. Refus en français (ValueError) : pas de peau, GLB compressé, opération ou paramètre inconnus.
"""
from __future__ import annotations

import copy
import math
import struct
from collections import deque

from app.services import mesh_edit as ME
from app.services import mouvement_rig as MR
from app.services import rig_local as RL

OPERATIONS = ("orphelins", "confinement", "epaules", "coutures", "guerison", "tout")
SEUIL_ORPHELIN = 0.02
EPS = 1e-6
_EGAL = 1e-9          # deux poids plus proches que ça sont ex æquo (les sommes flottantes diffèrent d'un côté à l'autre)
_ROLES_MEMBRES = ("epaule", "bras", "cuisse")

# la batterie de poses d'amplitude du correctif en un clic : (rôle, rotation locale en degrés X, Y, Z) ; chaque pose
# est jouée des DEUX côtés à la fois (le côté droit en miroir : Y et Z changent de signe), pour garder la symétrie
BATTERIE = [
    [("bras", (0, 0, -60))], [("bras", (0, 0, 45))], [("bras", (0, -60, 0))],
    [("avantbras", (0, -100, 0))], [("main", (0, 0, 45))],
    [("cuisse", (-80, 0, 0))], [("cuisse", (0, 0, 35))], [("jambe", (100, 0, 0))], [("pied", (35, 0, 0))],
    [("cou", (35, 0, 0))], [("colonne", (25, 0, 0))],
]
# la TORSION de colonne de Sorceress n'y est pas : une torsion est chirale (son miroir est la torsion opposée), elle
# rendrait le correctif asymétrique ; la flexion avant la remplace.


# ── petits calculs ─────────────────────────────────────────────────────────────────────────────────────────────────

def _normaliser(w: dict, maxi: int = 4) -> dict:
    """Quatre influences au plus, les poids négligeables retirés, somme 1. Un point sans poids reste vide."""
    items = sorted(((k, v) for k, v in w.items() if v > EPS), key=lambda kv: (-kv[1], kv[0]))
    if len(items) > maxi:
        coupe = items[maxi][1]
        # une égalité à la coupe (os gauche et droit sur l'axe) n'est jamais tranchée par l'index : les deux partent
        items = [kv for kv in items[:maxi] if kv[1] > coupe + _EGAL] or items[:maxi]
    s = sum(v for _k, v in items)
    if s <= EPS:
        return {}
    return {k: v / s for k, v in items}


def _dominant(w: dict):
    """L'os qui domine un point ; à égalité, l'ENSEMBLE des ex æquo (une égalité gauche/droite reste symétrique)."""
    if not w:
        return None
    m = max(w.values())
    return frozenset(k for k, v in w.items() if v >= m - _EGAL)


def _moyenne(ws: list[dict]) -> dict:
    out: dict = {}
    for w in ws:
        for k, v in w.items():
            out[k] = out.get(k, 0.0) + v
    n = len(ws) or 1
    return {k: v / n for k, v in out.items()}


def _melange(a: dict, b: dict, t: float) -> dict:
    out = {k: (1 - t) * v for k, v in a.items()}
    for k, v in b.items():
        out[k] = out.get(k, 0.0) + t * v
    return out


def _dist_segment(p, seg) -> float:
    ax, ay, az, dx, dy, dz, l2 = seg
    vx, vy, vz = p[0] - ax, p[1] - ay, p[2] - az
    t = (vx * dx + vy * dy + vz * dz) / l2 if l2 > 1e-20 else 0.0
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    ex, ey, ez = vx - t * dx, vy - t * dy, vz - t * dz
    return math.sqrt(ex * ex + ey * ey + ez * ez)


def _inverse_affine(m: list) -> list:
    """Inverse d'une matrice affine 4×4 colonne-majeure (le bloc 3×3 inversé par cofacteurs)."""
    a, b, c = m[0], m[4], m[8]
    d, e, f = m[1], m[5], m[9]
    g, h, i = m[2], m[6], m[10]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-20:
        return list(ME._IDENTITE)
    inv = [(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det,
           (f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det,
           (d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]   # lignes de l'inverse
    t = (m[12], m[13], m[14])
    out = [0.0] * 16
    for r in range(3):
        for c_ in range(3):
            out[c_ * 4 + r] = inv[r * 3 + c_]
        out[12 + r] = -(inv[r * 3] * t[0] + inv[r * 3 + 1] * t[1] + inv[r * 3 + 2] * t[2])
    out[15] = 1.0
    return out


def _rotation(r) -> list:
    """Matrice 4×4 d'une rotation : [x, y, z] en degrés (X puis Y puis Z, axes locaux) ou quaternion [x, y, z, w]."""
    if len(r) == 4:
        return ME._mat_locale({"rotation": [float(v) for v in r]})
    rx, ry, rz = (math.radians(float(v)) for v in r)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    mx = [1, 0, 0, 0, 0, cx, sx, 0, 0, -sx, cx, 0, 0, 0, 0, 1]
    my = [cy, 0, -sy, 0, 0, 1, 0, 0, sy, 0, cy, 0, 0, 0, 0, 1]
    mz = [cz, sz, 0, 0, -sz, cz, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    return ME._mat_mul(ME._mat_mul(mx, my), mz)


# ── lecture ────────────────────────────────────────────────────────────────────────────────────────────────────────

class Peau:
    """Un GLB skinné, lu pour les corrections. Les os sont désignés par leur index de NŒUD."""

    def __init__(self, data: bytes):
        m = RL.lire_modele(data)
        self.doc, self.binc = m["doc"], m["binc"]
        doc = self.doc
        nodes = doc.get("nodes") or []
        skins = doc.get("skins") or []
        self.groupes: list[dict] = []
        self.positions: list[tuple] = []
        cles_points: dict = {}
        sommets_vus: dict = {}
        aretes: set = set()
        for inst in m["instances"]:
            skin_i = nodes[inst["noeud"]].get("skin")
            if skin_i is None or not 0 <= skin_i < len(skins):
                continue
            jnodes = list(skins[skin_i].get("joints") or [])
            for pr in inst["prims"]:
                att = pr["prim"].get("attributes") or {}
                if att.get("JOINTS_0") is None or att.get("WEIGHTS_0") is None:
                    continue
                cle = (att["JOINTS_0"], att["WEIGHTS_0"])
                if cle not in sommets_vus:
                    js = ME.lire_accesseur(doc, self.binc, att["JOINTS_0"])
                    ws = RL._flottants(doc, self.binc, att["WEIGHTS_0"])
                    pts = []
                    for p in pr["positions"]:
                        k = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
                        pid = cles_points.get(k)
                        if pid is None:
                            pid = cles_points[k] = len(self.positions)
                            self.positions.append(tuple(p))
                        pts.append(pid)
                    g = {"joints_acc": att["JOINTS_0"], "weights_acc": att["WEIGHTS_0"], "skin": skin_i,
                         "jnodes": jnodes, "points": pts, "joints": js, "poids": ws}
                    sommets_vus[cle] = g
                    self.groupes.append(g)
                g = sommets_vus[cle]
                self._aretes(pr["prim"], g["points"], aretes)
        if not self.groupes:
            raise ValueError("ce modèle n'a pas de peau (JOINTS_0 / WEIGHTS_0) : rigge-le d'abord (écran Rig)")
        n = len(self.positions)
        # le poids d'un point : la moyenne de ses sommets (identiques après rig_local)
        acc: list[dict] = [dict() for _ in range(n)]
        cnt = [0] * n
        for g in self.groupes:
            for k, pid in enumerate(g["points"]):
                cnt[pid] += 1
                for j, w in zip(g["joints"][k], g["poids"][k]):
                    if w > 0 and 0 <= int(j) < len(g["jnodes"]):
                        b = g["jnodes"][int(j)]
                        acc[pid][b] = acc[pid].get(b, 0.0) + w
        self.poids = [_normaliser({b: v / max(1, cnt[p]) for b, v in acc[p].items()}) for p in range(n)]
        self.voisins: list[set] = [set() for _ in range(n)]
        for a, b in aretes:
            self.voisins[a].add(b)
            self.voisins[b].add(a)
        self.aretes = sorted(aretes)
        self._os(m["mondes"])
        lo, hi = m["boite"]["min"], m["boite"]["max"]
        self.hauteur = max(hi[1] - lo[1], max(hi[c] - lo[c] for c in range(3)) * 0.25, 1e-6)

    def _aretes(self, prim: dict, pts: list[int], aretes: set) -> None:
        if prim.get("mode", 4) != 4:
            return
        if prim.get("indices") is not None:
            idx = [int(v[0]) for v in ME.lire_accesseur(self.doc, self.binc, prim["indices"])]
        else:
            idx = list(range(len(pts)))
        for t in range(0, len(idx) - 2, 3):
            tri = [pts[idx[t + c]] for c in range(3) if 0 <= idx[t + c] < len(pts)]
            if len(tri) != 3:
                continue
            for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                if a != b:
                    aretes.add((a, b) if a < b else (b, a))

    def _os(self, mondes: dict) -> None:
        doc = self.doc
        nodes = doc.get("nodes") or []
        os_ = []
        for sk in doc.get("skins") or []:
            for j in sk.get("joints") or []:
                if 0 <= j < len(nodes) and j not in os_:
                    os_.append(j)
        parent_noeud = ME._parents(nodes)
        self.parent_noeud = parent_noeud
        ens = set(os_)
        self.mondes = {}
        for j in os_:
            mj = mondes.get(j)
            if mj is None:
                mj = ME._mat_mul(ME._monde_des_ancetres(doc, j), ME._mat_locale(nodes[j]))
            self.mondes[j] = mj
        self.os = {}
        for j in os_:
            p = parent_noeud.get(j)
            vus = set()
            while p is not None and p not in ens and p not in vus:
                vus.add(p)
                p = parent_noeud.get(p)
            nom = nodes[j].get("name") or f"os_{j}"
            self.os[j] = {"noeud": j, "nom": nom, "parent": p if p in ens else None,
                          "tete": tuple(self.mondes[j][12:15]), "role": MR.role(nom)}
        enfants: dict = {}
        for j, o in self.os.items():
            if o["parent"] is not None:
                enfants.setdefault(o["parent"], []).append(j)
        for j, o in self.os.items():
            a = o["tete"]
            ch = enfants.get(j) or []
            if ch:
                prefere = [c for c in ch if (self.os[c]["role"] or "").startswith(("colonne", "cou"))]
                b = self.os[(prefere or ch)[0]]["tete"]
            elif o["parent"] is not None:
                q = self.os[o["parent"]]["tete"]
                b = tuple(a[c] + 0.6 * (a[c] - q[c]) for c in range(3))
            else:
                b = a
            d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            o["segment"] = (a[0], a[1], a[2], d[0], d[1], d[2], d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
            o["longueur"] = math.sqrt(o["segment"][6])
        self.enfants = enfants

    # ── accès commodes ──
    def par_nom(self, nom: str):
        for j, o in self.os.items():
            if o["nom"] == nom:
                return j
        return None

    def par_role(self, role: str):
        return [j for j, o in self.os.items() if o["role"] == role]

    def resume(self) -> dict:
        n = len(self.positions)
        sans = sum(1 for w in self.poids if not w)
        return {
            "os": [{"noeud": j, "nom": o["nom"], "parent": self.os[o["parent"]]["nom"] if o["parent"] is not None else None,
                    "tete": [round(v, 6) for v in o["tete"]], "role": o["role"]} for j, o in self.os.items()],
            "points": n, "sommets": sum(len(g["points"]) for g in self.groupes), "aretes": len(self.aretes),
            "sans_poids": sans, "groupes": len(self.groupes), "hauteur": round(self.hauteur, 6),
        }


def lire_peau(data: bytes) -> Peau:
    return Peau(data)


# ── écriture ───────────────────────────────────────────────────────────────────────────────────────────────────────

_FMT = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}


def _ecrire_accesseur(doc: dict, binc: bytearray, i: int, valeurs: list[tuple], poids: bool) -> bool:
    """Écrit `valeurs` EN PLACE dans la vue de l'accesseur `i` ; False si le format ne s'y prête pas."""
    a = doc["accessors"][i]
    ct = a.get("componentType")
    if a.get("sparse") or a.get("bufferView") is None or ct not in _FMT or a.get("type") != "VEC4":
        return False
    if not poids and ct == 5126:
        return False
    if poids and ct != 5126 and not a.get("normalized"):
        return False
    fmt, taille = _FMT[ct]
    if not poids:
        borne = (1 << (8 * taille)) - 1
        if any(int(c) > borne or int(c) < 0 for v in valeurs for c in v):
            return False
    bv = doc["bufferViews"][a["bufferView"]]
    if bv.get("buffer", 0) != 0:
        return False
    pas = bv.get("byteStride") or taille * 4
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    if base + pas * (len(valeurs) - 1) + taille * 4 > len(binc):
        return False
    st = struct.Struct("<4" + fmt)
    div = {5121: 255.0, 5123: 65535.0}.get(ct)
    for k, v in enumerate(valeurs):
        if poids and div:
            v = [max(0, min(int(div), int(round(c * div)))) for c in v]
        elif poids:
            v = [float(c) for c in v]
        else:
            v = [int(c) for c in v]
        st.pack_into(binc, base + pas * k, *v)
    return True


def _ajouter_accesseur(doc: dict, binc: bytearray, valeurs: list[tuple], poids: bool) -> int:
    binc += b"\x00" * (-len(binc) % 4)
    debut = len(binc)
    fmt = "f" if poids else "H"
    binc += struct.pack(f"<{len(valeurs) * 4}{fmt}", *[c for v in valeurs for c in v])
    doc.setdefault("bufferViews", []).append({"buffer": 0, "byteOffset": debut, "byteLength": len(binc) - debut,
                                              "target": 34962})
    doc.setdefault("accessors", []).append({"bufferView": len(doc["bufferViews"]) - 1,
                                            "componentType": 5126 if poids else 5123, "count": len(valeurs),
                                            "type": "VEC4"})
    return len(doc["accessors"]) - 1


def _quatre(w: dict, locaux: dict) -> tuple[tuple, tuple]:
    """(indices de joints locaux, poids) sur quatre places, à partir de {nœud d'os: poids}."""
    w = _normaliser({b: v for b, v in w.items() if b in locaux})
    items = sorted(w.items(), key=lambda kv: (-kv[1], kv[0]))
    js = [locaux[b] for b, _v in items] + [0] * (4 - len(items))
    ws = [v for _b, v in items] + [0.0] * (4 - len(items))
    return tuple(js), tuple(ws)


def _ecrire_groupe(doc: dict, binc: bytearray, g: dict, js: list[tuple], ws: list[tuple]) -> None:
    ja, wa = g["joints_acc"], g["weights_acc"]
    neuf = {}
    if not _ecrire_accesseur(doc, binc, ja, js, False):
        neuf["JOINTS_0"] = (ja, _ajouter_accesseur(doc, binc, js, False))
    if not _ecrire_accesseur(doc, binc, wa, ws, True):
        neuf["WEIGHTS_0"] = (wa, _ajouter_accesseur(doc, binc, ws, True))
    if neuf:   # tous les primitifs qui partageaient l'ancien accesseur suivent le nouveau
        for m in doc.get("meshes") or []:
            for p in m.get("primitives") or []:
                att = p.get("attributes") or {}
                if att.get("JOINTS_0") == ja and att.get("WEIGHTS_0") == wa:
                    for cle, (_a, n) in neuf.items():
                        att[cle] = n


def _finir(doc: dict, binc: bytearray, generateur: str) -> bytes:
    doc["buffers"] = [{"byteLength": len(binc)}]
    doc.setdefault("asset", {"version": "2.0"})
    doc["asset"]["generator"] = generateur
    return ME.ecrire_glb(doc, bytes(binc))


def ecrire_peau(peau: Peau, poids_points: list[dict]) -> bytes:
    """Le GLB avec les poids des POINTS rendus à chaque sommet. Os, positions, clips et matériaux intacts."""
    doc = copy.deepcopy(peau.doc)
    binc = bytearray(peau.binc)
    for g in peau.groupes:
        locaux = {b: k for k, b in enumerate(g["jnodes"])}
        js, ws = [], []
        for pid in g["points"]:
            j, w = _quatre(poids_points[pid], locaux)
            js.append(j)
            ws.append(w)
        _ecrire_groupe(doc, binc, g, js, ws)
    return _finir(doc, binc, "DeepotusVideo poids_corrections (t397)")


def ecrire_sommets(data: bytes, modifs) -> tuple[bytes, dict]:
    """Les poids PEINTS (écran Affiner) : `modifs` = [{mesh, primitive, sommets: [v…], joints: [4·k], poids: [4·k]}].

    Les indices de joints sont ceux de la peau (comme three.js `skinIndex`). Chaque sommet est renormalisé (quatre
    influences, somme 1). Rend (octets, compte rendu). ValueError en français."""
    if not isinstance(modifs, list) or not modifs:
        raise ValueError("modifs : une liste non vide de {mesh, primitive, sommets, joints, poids} est attendue")
    doc, binc0 = ME.lire_glb(data)
    RL._refuser_compression(doc)
    nodes = doc.get("nodes") or []
    meshes = doc.get("meshes") or []
    skins = doc.get("skins") or []
    if not skins:
        raise ValueError("ce modèle n'a pas de peau (JOINTS_0 / WEIGHTS_0) : rigge-le d'abord (écran Rig)")
    binc = bytearray(binc0)
    total, faits = 0, set()
    for md in modifs:
        if not isinstance(md, dict):
            raise ValueError("modifs : chaque entrée est un objet {mesh, primitive, sommets, joints, poids}")
        mi, pi = md.get("mesh"), md.get("primitive")
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (mi, pi)) \
                or not 0 <= mi < len(meshes) or not 0 <= pi < len(meshes[mi].get("primitives") or []):
            raise ValueError(f"primitive introuvable : maillage {mi}, primitive {pi}")
        prim = meshes[mi]["primitives"][pi]
        att = prim.get("attributes") or {}
        if att.get("JOINTS_0") is None or att.get("WEIGHTS_0") is None:
            raise ValueError(f"maillage {mi}, primitive {pi} : pas de poids de peau")
        skin_i = next((n.get("skin") for n in nodes if n.get("mesh") == mi and n.get("skin") is not None), None)
        if skin_i is None or not 0 <= skin_i < len(skins):
            raise ValueError(f"maillage {mi} : aucun nœud ne le lie à une peau")
        nj = len(skins[skin_i].get("joints") or [])
        som, jf, wf = md.get("sommets"), md.get("joints"), md.get("poids")
        if not isinstance(som, list) or not isinstance(jf, list) or not isinstance(wf, list) \
                or len(jf) != 4 * len(som) or len(wf) != 4 * len(som):
            raise ValueError("sommets, joints, poids : listes de k, 4·k et 4·k valeurs")
        js = [tuple(int(c) for c in v) for v in ME.lire_accesseur(doc, bytes(binc), att["JOINTS_0"])]
        ws = RL._flottants(doc, bytes(binc), att["WEIGHTS_0"])
        n = len(js)
        for k, v in enumerate(som):
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < n:
                raise ValueError(f"sommet {v} hors de 0..{n - 1}")
            jv = jf[4 * k:4 * k + 4]
            wv = wf[4 * k:4 * k + 4]
            if not all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c < nj for c in jv):
                raise ValueError(f"sommet {v} : indice d'os hors de 0..{nj - 1}")
            if not all(isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) and c >= 0
                       for c in wv):
                raise ValueError(f"sommet {v} : poids négatif ou non fini")
            w: dict = {}
            for j, x in zip(jv, wv):
                w[j] = w.get(j, 0.0) + float(x)
            w = _normaliser(w)
            if not w:
                raise ValueError(f"sommet {v} : aucun poids (au moins un os doit le tenir)")
            items = sorted(w.items(), key=lambda kv: (-kv[1], kv[0]))
            js[v] = tuple([j for j, _x in items] + [0] * (4 - len(items)))
            ws[v] = tuple([x for _j, x in items] + [0.0] * (4 - len(items)))
        _ecrire_groupe(doc, binc, {"joints_acc": att["JOINTS_0"], "weights_acc": att["WEIGHTS_0"]}, js, ws)
        total += len(set(som))
        faits.add((mi, pi))
    return _finir(doc, binc, "DeepotusVideo affiner (t396)"), {"sommets": total, "primitives": len(faits),
                                                               "operation": "poids_peints"}


# ── la pose : skinning linéaire des points ─────────────────────────────────────────────────────────────────────────

def _deltas(peau: Peau, pose: dict) -> dict:
    """{nœud d'os: matrice} = monde posé · monde de repos⁻¹. `pose` : {nœud: rotation locale} (voir _rotation).

    Le monde posé d'un nœud = monde posé de son parent · locale · (rotation de la pose s'il est un os posé) ; les
    nœuds intermédiaires (armature tournée, mise à l'échelle) gardent leur transformation."""
    nodes = peau.doc.get("nodes") or []
    memo: dict = {}

    def monde(n):
        if n is None:
            return ME._IDENTITE
        if n not in memo:
            memo[n] = ME._IDENTITE      # garde contre un cycle
            local = ME._mat_locale(nodes[n])
            if n in pose:
                local = ME._mat_mul(local, _rotation(pose[n]))
            memo[n] = ME._mat_mul(monde(peau.parent_noeud.get(n)), local)
        return memo[n]
    return {j: ME._mat_mul(monde(j), _inverse_affine(peau.mondes[j])) for j in peau.os}


def poser(peau: Peau, poids: list[dict], pose: dict) -> list[tuple]:
    D = _deltas(peau, pose)
    out = []
    for p, w in zip(peau.positions, poids):
        if not w:
            out.append(p)
            continue
        x = y = z = 0.0
        for b, v in w.items():
            m = D.get(b)
            if m is None:
                x += v * p[0]; y += v * p[1]; z += v * p[2]
                continue
            x += v * (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12])
            y += v * (m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13])
            z += v * (m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])
        out.append((x, y, z))
    return out


def _etirements(peau: Peau, posees: list[tuple]) -> list[tuple]:
    """[(a, b, rapport longueur posée / longueur de repos)] pour chaque arête de longueur non nulle."""
    out = []
    P = peau.positions
    for a, b in peau.aretes:
        l0 = math.dist(P[a], P[b])
        if l0 > 1e-9:
            out.append((a, b, math.dist(posees[a], posees[b]) / l0))
    return out


def pose_valide(peau: Peau, pose) -> dict:
    """{nœud: rotation} depuis {nom d'os: [x, y, z] (degrés) | [x, y, z, w]} ; ValueError en français."""
    if pose is None:
        return {}
    if not isinstance(pose, dict):
        raise ValueError("pose : un objet {os: [x, y, z]} (degrés) ou {os: [x, y, z, w]} (quaternion) est attendu")
    out = {}
    for nom, r in pose.items():
        j = peau.par_nom(nom)
        if j is None:
            raise ValueError(f"pose : os inconnu « {str(nom)[:40]} »")
        if not isinstance(r, (list, tuple)) or len(r) not in (3, 4) or not all(
                isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) for c in r):
            raise ValueError(f"pose : « {nom} » attend trois angles (degrés) ou un quaternion")
        if len(r) == 4 and sum(c * c for c in r) < 1e-12:
            raise ValueError(f"pose : quaternion nul pour « {nom} »")
        out[j] = list(r)
    return out


def batterie(peau: Peau) -> list[dict]:
    """Les poses d'amplitude du correctif en un clic, traduites en {nœud: rotation} pour CE squelette."""
    out = []
    for pose in BATTERIE:
        p = {}
        for role, (rx, ry, rz) in pose:
            for cote, signe in (("g", 1), ("d", -1)):
                for j in peau.par_role(f"{role}_{cote}"):
                    p[j] = [rx, signe * ry, signe * rz]
            for j in peau.par_role(role):         # rôles sans côté : cou, colonne
                p[j] = [rx, ry, rz]
        if p:
            out.append(p)
    return out


# ── 1. les orphelins ───────────────────────────────────────────────────────────────────────────────────────────────

def _composantes(peau: Peau, ens: set) -> list[list[int]]:
    vus, comps = set(), []
    for s in sorted(ens):
        if s in vus:
            continue
        c, f = [], deque([s])
        vus.add(s)
        while f:
            p = f.popleft()
            c.append(p)
            for q in peau.voisins[p]:
                if q in ens and q not in vus:
                    vus.add(q)
                    f.append(q)
        comps.append(c)
    comps.sort(key=lambda c: (-len(c), c[0]))
    return comps


def orphelins(peau: Peau, poids: list[dict], *, os=None, seuil: float = SEUIL_ORPHELIN, retirer: bool = True):
    """Les îlots de poids détachés du membre de chaque os ; retirés (rendus à l'os de leur bordure) si `retirer`."""
    poids = [dict(w) for w in poids]
    cibles = [os] if os is not None else sorted({b for w in poids for b in w})
    rapport = []
    for b in cibles:
        ens = {p for p, w in enumerate(poids) if w.get(b, 0.0) > seuil}
        comps = _composantes(peau, ens)
        ilots = comps[1:]
        if not ilots:
            continue
        lignes = []
        for c in ilots:
            cs = set(c)
            score: dict = {}
            for p in c:
                for q in peau.voisins[p]:
                    if q not in cs:
                        for k, v in poids[q].items():
                            if k != b:
                                score[k] = score.get(k, 0.0) + v
            if not score:            # aucune bordure : l'os le plus présent DANS l'îlot, à défaut le parent
                for p in c:
                    for k, v in poids[p].items():
                        if k != b:
                            score[k] = score.get(k, 0.0) + v
            if score:
                m = max(score.values())
                cibles_ = sorted(k for k, v in score.items() if v >= m - 1e-9 * max(1.0, m))   # ex æquo : partagé
            else:
                cibles_ = [peau.os[b]["parent"]] if peau.os[b]["parent"] is not None else []
            centre = [round(sum(peau.positions[p][k] for p in c) / len(c), 6) for k in range(3)]
            lignes.append({"points": len(c), "centre": centre, "vers": [peau.os[k]["nom"] for k in cibles_]})
            if retirer and cibles_:
                for p in c:
                    m = poids[p].pop(b, 0.0)
                    for k in cibles_:
                        poids[p][k] = poids[p].get(k, 0.0) + m / len(cibles_)
                    poids[p] = _normaliser(poids[p])
        rapport.append({"os": peau.os[b]["nom"], "membre": len(comps[0]), "ilots": lignes})
    return poids, {"orphelins": rapport, "ilots": sum(len(r["ilots"]) for r in rapport)}


# ── 2. le confinement des membres, l'épaule ────────────────────────────────────────────────────────────────────────

def _os_membres(peau: Peau) -> list:
    return [j for j, o in peau.os.items() if (o["role"] or "").rsplit("_", 1)[0] in _ROLES_MEMBRES
            and "_" in (o["role"] or "")]


def confinement(peau: Peau, poids: list[dict], *, os=None, force: float = 0.7, portee: float = 0.5):
    """Le poids d'un membre loin de son segment est rogné de `force` × l'excès de distance, et donné à l'os voisin
    déjà présent sur le point (le plus proche), à défaut au parent du membre."""
    cibles = [os] if os is not None else _os_membres(peau)
    nouveaux = [dict(w) for w in poids]
    rapport = []
    for b in cibles:
        o = peau.os[b]
        R = max(portee * o["longueur"], 0.03 * peau.hauteur)
        n, masse = 0, 0.0
        for p, w in enumerate(poids):          # Jacobi : les décisions lisent les poids d'AVANT
            wb = w.get(b, 0.0)
            if wb <= EPS:
                continue
            d = _dist_segment(peau.positions[p], o["segment"])
            if d <= R:
                continue
            rogne = wb * force * min(1.0, (d - R) / R)
            if rogne <= EPS:
                continue
            autres = [k for k in w if k != b and k in peau.os]
            if autres:
                ds = {k: _dist_segment(peau.positions[p], peau.os[k]["segment"]) for k in autres}
                dmin = min(ds.values())
                vers = [k for k, d_ in ds.items() if d_ <= dmin + _EGAL]     # ex æquo (sur l'axe) : partagé
            else:
                vers = [o["parent"]] if o["parent"] is not None else []
            if not vers:
                continue
            nouveaux[p][b] = nouveaux[p].get(b, 0.0) - rogne
            for k in vers:
                nouveaux[p][k] = nouveaux[p].get(k, 0.0) + rogne / len(vers)
            n += 1
            masse += rogne
        rapport.append({"os": o["nom"], "points": n, "masse": round(masse, 4), "portee": round(R, 6)})
    return [_normaliser(w) for w in nouveaux], {"confinement": rapport, "points": sum(r["points"] for r in rapport)}


def epaules(peau: Peau, poids: list[dict]):
    """La région de chaque épaule : la masse colonne + clavicule + bras répartie selon la distance aux segments."""
    nouveaux = [dict(w) for w in poids]
    rapport = []
    for cote in ("g", "d"):
        cl = peau.par_role(f"epaule_{cote}")
        br = peau.par_role(f"bras_{cote}")
        if not cl or not br:
            continue
        c, b = cl[0], br[0]
        dos = peau.os[c]["parent"]
        trio = [k for k in (dos, c, b) if k is not None]
        centre = peau.os[b]["tete"]
        autre = peau.par_role(f"bras_{'d' if cote == 'g' else 'g'}")
        axe = (centre[0] + peau.os[autre[0]]["tete"][0]) / 2 if autre else (
            peau.os[dos]["tete"][0] if dos is not None else 0.0)
        sens = 1.0 if centre[0] >= axe else -1.0
        r = max(peau.os[c]["longueur"] + 0.5 * peau.os[b]["longueur"], 0.05 * peau.hauteur)
        n = 0
        for p, w in enumerate(poids):
            d = math.dist(peau.positions[p], centre)
            if d >= r or (peau.positions[p][0] - axe) * sens <= 1e-6 * peau.hauteur:     # ni sur l'axe, ni au-delà
                continue
            M = sum(w.get(k, 0.0) for k in trio)
            if M <= EPS:
                continue
            inv = {k: 1.0 / max(_dist_segment(peau.positions[p], peau.os[k]["segment"]), 1e-4 * peau.hauteur) ** 4
                   for k in trio}
            s = sum(inv.values())
            f = 1.0 - (d / r) ** 2
            nw = dict(w)
            for k in trio:
                nw[k] = (1 - f) * w.get(k, 0.0) + f * M * inv[k] / s
            nouveaux[p] = _normaliser(nw)
            n += 1
        rapport.append({"cote": cote, "clavicule": peau.os[c]["nom"], "bras": peau.os[b]["nom"], "points": n,
                        "rayon": round(r, 6)})
    return nouveaux, {"epaules": rapport, "points": sum(x["points"] for x in rapport)}


# ── 3. les coutures ────────────────────────────────────────────────────────────────────────────────────────────────

def _lisser(peau: Peau, poids: list[dict], ens, force: float, iterations: int) -> list[dict]:
    poids = list(poids)
    ens = sorted(ens)
    for _ in range(max(1, iterations)):
        neuf = list(poids)
        for p in ens:
            vs = peau.voisins[p]
            if vs:
                neuf[p] = _normaliser(_melange(poids[p], _moyenne([poids[q] for q in vs]), force))
        poids = neuf
    return poids


def coutures(peau: Peau, poids: list[dict], *, os=None, anneaux: int = 3, force: float = 0.5,
             pose: dict | None = None, deformees: bool = False):
    dom = [_dominant(w) for w in poids]
    bord = set()
    for a, b in peau.aretes:
        if dom[a] != dom[b] and (os is None or os in (dom[a] or ()) or os in (dom[b] or ())):
            bord.add(a)
            bord.add(b)
    collier, front = set(bord), set(bord)
    for _ in range(max(0, anneaux - 1)):
        suivant = {q for p in front for q in peau.voisins[p]} - collier
        collier |= suivant
        front = suivant
    if deformees and pose:
        posees = poser(peau, poids, pose)
        etire = set()
        for a, b, r in _etirements(peau, posees):
            if abs(r - 1) > 0.05:
                etire.add(a)
                etire.add(b)
        collier &= etire
    nouveaux = _lisser(peau, poids, collier, force, anneaux)
    return nouveaux, {"coutures": {"frontiere": len(bord), "collier": len(collier), "anneaux": anneaux,
                                   "os": peau.os[os]["nom"] if os is not None else None,
                                   "deformees_seulement": bool(deformees and pose)}, "points": len(collier)}


# ── 4. la guérison dynamique ───────────────────────────────────────────────────────────────────────────────────────

def guerison(peau: Peau, poids: list[dict], *, poses: list[dict], tolerance: float = 0.25, force: float = 0.5,
             passes: int = 4):
    poids = list(poids)
    rapport = []
    for pose in poses:
        avant = None
        meilleur = (None, poids)
        for it in range(passes + 1):
            mauvais = set()
            for a, b, r in _etirements(peau, poser(peau, poids, pose)):
                if r > 1 + tolerance or r < 1 - tolerance:
                    mauvais.add(a)
                    mauvais.add(b)
            if avant is None:
                avant = len(mauvais)
            if meilleur[0] is None or len(mauvais) < meilleur[0]:
                meilleur = (len(mauvais), poids)
            if not mauvais or it == passes:
                break
            poids = _lisser(peau, poids, mauvais, force, 1)
        apres, poids = meilleur        # une passe qui empire est abandonnée : on garde la meilleure
        rapport.append({"pose": sorted(peau.os[j]["nom"] for j in pose), "avant": avant, "apres": apres})
    return poids, {"guerison": rapport, "points": sum(r["avant"] - r["apres"] for r in rapport)}


# ── l'entrée unique ────────────────────────────────────────────────────────────────────────────────────────────────

def _nombre(params: dict, cle: str, defaut: float, lo: float, hi: float) -> float:
    v = params.get(cle, defaut)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f"{cle} : un nombre entre {lo} et {hi} est attendu")
    return float(v)


def corriger(data: bytes, operation: str, *, os: str | None = None, parametres: dict | None = None) -> tuple[bytes | None, dict]:
    """Applique une correction ; rend (octets du GLB corrigé ou None en aperçu, compte rendu)."""
    if operation not in OPERATIONS:
        raise ValueError(f"opération inconnue « {str(operation)[:40]} » : orphelins, confinement, epaules, coutures, "
                         "guerison ou tout")
    params = parametres if isinstance(parametres, dict) else {}
    peau = Peau(data)
    j = None
    if os is not None:
        j = peau.par_nom(os) if isinstance(os, str) else None
        if j is None:
            raise ValueError(f"os inconnu « {str(os)[:40]} »")
    apercu = params.get("apercu", False)
    if not isinstance(apercu, bool):
        raise ValueError("apercu : vrai ou faux")
    poids = peau.poids
    if operation == "orphelins":
        seuil = _nombre(params, "seuil", SEUIL_ORPHELIN, 0.001, 0.9)
        poids, rap = orphelins(peau, poids, os=j, seuil=seuil, retirer=not apercu)
    elif operation == "confinement":
        poids, rap = confinement(peau, poids, os=j, force=_nombre(params, "force", 0.7, 0, 1),
                                 portee=_nombre(params, "portee", 0.5, 0.05, 5))
    elif operation == "epaules":
        poids, rap = epaules(peau, poids)
    elif operation == "coutures":
        anneaux = _nombre(params, "anneaux", 3, 1, 12)
        deformees = params.get("deformees", False)
        if not isinstance(deformees, bool):
            raise ValueError("deformees : vrai ou faux")
        pose = pose_valide(peau, params.get("pose"))
        if deformees and not pose:
            raise ValueError("deformees : une pose est requise (lance le test de pose)")
        poids, rap = coutures(peau, poids, os=j, anneaux=int(anneaux), force=_nombre(params, "force", 0.5, 0, 1),
                              pose=pose, deformees=deformees)
    elif operation == "guerison":
        brut = params.get("poses")
        if brut is None and params.get("pose") is not None:
            brut = [params["pose"]]
        if brut is None:
            poses = batterie(peau)
        else:
            if not isinstance(brut, list) or not brut or len(brut) > 32:
                raise ValueError("poses : une liste de 1 à 32 poses est attendue")
            poses = [pose_valide(peau, p) for p in brut]
        poids, rap = guerison(peau, poids, poses=[p for p in poses if p],
                              tolerance=_nombre(params, "tolerance", 0.25, 0.02, 2))
    else:   # tout : le correctif en un clic
        etapes = []
        poids, r = epaules(peau, poids); etapes.append({"etape": "epaules", **r})
        poids, r = confinement(peau, poids, force=_nombre(params, "force", 0.7, 0, 1)); etapes.append({"etape": "confinement", **r})
        poids, r = coutures(peau, poids, anneaux=3); etapes.append({"etape": "coutures", **r})
        poids, r = guerison(peau, poids, poses=batterie(peau)); etapes.append({"etape": "guerison", **r})
        rap = {"etapes": etapes, "points": sum(e.get("points", 0) for e in etapes)}
    rap = {"correction": operation, "os_choisi": os, **rap}     # pas « operation » : le registre la garde
    if apercu:
        return None, rap
    return ecrire_peau(peau, poids), rap


def _fichier(version: int) -> str:
    return "model.glb" if int(version) <= 1 else f"model.v{int(version)}.glb"


def ecrire(job: str, version: int, sortie: bytes, operation: str, rapport: dict, fichier: str | None = None) -> dict:
    """Écrit `sortie` comme version de plus (jamais un écrasement) ; rend la fiche du registre."""
    return ME.ecrire_version(job, sortie, operation=operation, detail={
        "outil": "studio3d", "depuis": {"version": int(version), "fichier": fichier or _fichier(version)}, **rapport})


__all__ = ["OPERATIONS", "BATTERIE", "Peau", "lire_peau", "ecrire_peau", "ecrire_sommets", "poser", "pose_valide",
           "batterie", "orphelins", "confinement", "epaules", "coutures", "guerison", "corriger", "ecrire"]
