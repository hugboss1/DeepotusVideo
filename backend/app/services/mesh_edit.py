# -*- coding: utf-8 -*-
"""Chirurgie de document glTF — la SEULE plume à GLB du chantier Établi.

Règle de l'option C (spec 2026-08-29-etabli-inspecteur-3d-design §2.1) : le
navigateur voit et manipule, Python écrit. Aucun GLB n'est jamais produit par
le client, de sorte que tout artefact reste versionné, fiché par mesh_report,
et vérifiable par le harnais.

Deux propriétés porteront la sûreté du module, et les bancs des tâches 3 et 5
de ce plan les épingleront (elles n'existent pas encore à la tâche 1) :

* `extraire` est une RECOPIE D'OCTETS, jamais un décodage de géométrie — les
  bufferViews retenus sont copiés tels quels. L'extraction fonctionne donc sur
  un GLB Draco ou meshopt, là où `print3d.lire_glb_triangles` refuse.
* `transformer` ne touche QUE le document JSON — le tampon binaire ressort
  identique octet pour octet, ce qui rend l'opération sûre sur 200 Mo.

Module sans `settings` : de la manipulation d'octets pure, testable sans
environnement.
"""
from __future__ import annotations

import json
import struct

_MAGIC = b"glTF"
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942


def lire_glb(data: bytes) -> tuple[dict, bytes]:
    """Les DEUX moitiés d'un GLB v2 : le document et son tampon.

    `mesh_report._gltf_json` ne rend que le JSON et `print3d` sert son propre
    décodeur ; la chirurgie a besoin des deux et de savoir les recoller.
    """
    if len(data) < 12 or data[:4] != _MAGIC:
        raise ValueError("magic GLB absent — ce fichier n'est pas un .glb")
    version, longueur = struct.unpack_from("<II", data, 4)
    if version != 2:
        raise ValueError(f"GLB v{version} non géré (v2 attendu)")
    doc: dict | None = None
    binc = b""
    off = 12
    # Borner par la longueur DÉCLARÉE dans l'en-tête, comme le fait déjà
    # `print3d._chunks`. Sans cette borne, des octets parasites après la fin
    # du conteneur (téléchargement rejoué, artefact d'un générateur tiers)
    # seraient lus comme des chunks : si les quatre suivants ressemblent à
    # `BIN\0`, le tampon déjà lu serait écrasé EN SILENCE. Un GLB de 200 Mo
    # venu de Meshy ou Tripo mérite mieux qu'une corruption muette.
    while off + 8 <= min(longueur, len(data)):
        clen, ctype = struct.unpack_from("<II", data, off)
        off += 8
        bloc = data[off:off + clen]
        if ctype == _CHUNK_JSON:
            doc = json.loads(bloc.decode("utf-8"))
        elif ctype == _CHUNK_BIN:
            binc = bloc
        off += clen + (-clen % 4)
    if doc is None:
        raise ValueError("chunk JSON introuvable")
    return doc, binc


def ecrire_glb(doc: dict, binc: bytes) -> bytes:
    """Recolle un document et son tampon. Les deux chunks sont alignés sur 4
    octets — le JSON par des espaces, le binaire par des zéros, comme l'exige
    la spec glTF 2.0."""
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * (-len(js) % 4)
    bn = bytes(binc) + b"\x00" * (-len(binc) % 4)
    total = 12 + 8 + len(js) + ((8 + len(bn)) if bn else 0)
    out = struct.pack("<4sII", _MAGIC, 2, total)
    out += struct.pack("<II", len(js), _CHUNK_JSON) + js
    if bn:
        out += struct.pack("<II", len(bn), _CHUNK_BIN) + bn
    return out


def _l(doc: dict, cle: str) -> list:
    """Un tableau glTF absent et un tableau vide se traitent pareil."""
    return doc.get(cle) or []


def rig_inventory(data: bytes) -> dict:
    """Os, hiérarchie, skins et clips — chunk JSON seulement.

    Instantané même sur un GLB de 200 Mo, et c'est le but : le panneau Rig doit
    pouvoir annoncer l'absence de squelette sans rien télécharger.

    CONTRAT À LIRE AVANT DE BÂTIR UN ARBRE DESSUS : `os` ne contient que les
    JOINTS. Un `os[].parent` peut donc désigner un nœud absent de la liste —
    c'est le cas courant des exports Blender ou Mixamo, où la racine
    d'armature (`skins[].skeleton`) porte le déplacement global sans être
    elle-même un os. Un consommateur doit traiter un `parent` introuvable
    comme une racine, jamais supposer qu'il se résout dans `os`.
    """
    doc, _ = lire_glb(data)
    nodes = _l(doc, "nodes")
    skins = _l(doc, "skins")

    parent: dict[int, int] = {}
    for i, n in enumerate(nodes):
        for c in _l(n, "children"):
            parent[c] = i

    joints: list[int] = []
    for s in skins:
        for j in _l(s, "joints"):
            if j not in joints:
                joints.append(j)

    os_: list[dict] = []
    for j in joints:
        n = nodes[j] if 0 <= j < len(nodes) else {}
        os_.append({
            "index": j,
            "nom": n.get("name") or f"os_{j}",
            "parent": parent.get(j),
            "enfants": [c for c in _l(n, "children") if c in joints],
        })

    clips = [{"nom": a.get("name") or f"clip_{i}",
              "canaux": len(_l(a, "channels"))}
             for i, a in enumerate(_l(doc, "animations"))]

    return {
        "a_squelette": bool(skins),
        "nb_os": len(joints),
        "os": os_,
        "skins": [{"nom": s.get("name") or f"skin_{i}",
                   "nb_joints": len(_l(s, "joints")),
                   "racine": s.get("skeleton")}
                  for i, s in enumerate(skins)],
        "clips": clips,
    }


_TAILLES = {"translation": 3, "rotation": 4, "scale": 3}
_TOLERANCE_QUATERNION = 1e-3


def transformer(data: bytes, transforms: dict) -> bytes:
    """Position / rotation / échelle de nœuds nommés.

    N'écrit QUE le document : le tampon binaire ressort identique octet pour
    octet, et le banc l'épingle. `matrix` est retiré du nœud touché — glTF
    interdit de porter à la fois une matrice et un TRS.

    Trois refus explicites plutôt que des corrections silencieuses, parce que
    cette fonction sera exposée par une route HTTP (tâche 8) qui ne traduit
    en 400 que les `ValueError` : entrée non-dictionnaire, clé de nœud non
    numérique, quaternion non normalisé. Normaliser un quaternion en douce
    masquerait un bug amont ; le refuser le montre.

    `scale` négatif ou nul passe DÉLIBÉRÉMENT : une échelle négative par axe
    est un TRS glTF valide (effet miroir). `reparer` refuse au contraire une
    échelle globale ≤ 0. Les deux fonctions n'ont pas la même politique, et
    c'est voulu — ne pas « harmoniser » sans y repenser.
    """
    if transforms is None:
        transforms = {}
    if not isinstance(transforms, dict):
        raise ValueError(
            "transforms attend un dictionnaire noeud -> TRS, reçu "
            f"{type(transforms).__name__}")
    doc, binc = lire_glb(data)
    nodes = _l(doc, "nodes")
    for cle, trs in transforms.items():
        try:
            i = int(cle)
        except (TypeError, ValueError):
            raise ValueError(f"clé de noeud non numérique : {cle!r}") from None
        if not (0 <= i < len(nodes)):
            raise ValueError(f"noeud {i} hors du document ({len(nodes)} noeuds)")
        n = nodes[i]
        n.pop("matrix", None)
        for champ, taille in _TAILLES.items():
            if champ not in trs:
                continue
            v = [float(x) for x in trs[champ]]
            if len(v) != taille:
                raise ValueError(f"{champ} attend {taille} valeurs, reçu {len(v)}")
            if champ == "rotation":
                # glTF exige un quaternion UNITAIRE. Non normalisé, il déforme
                # chez les lecteurs stricts et pas chez les autres : un bug qui
                # ne se voit qu'à l'export, donc à attraper à l'écriture.
                norme = sum(x * x for x in v) ** 0.5
                if abs(norme - 1.0) > _TOLERANCE_QUATERNION:
                    raise ValueError(
                        "rotation attend un quaternion normé [x,y,z,w] ; "
                        f"norme reçue {norme:.4f}")
            n[champ] = v
    return ecrire_glb(doc, binc)


# Y-up est la convention glTF ; Z-up est celle de Blender et d'Unreal.
# La rotation envoie +Y sur +Z : (x, y, z) -> (x, -z, y).
_ROT = {
    "Y": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "Z": ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
}


def _matrice(rot, s: float, t) -> list[float]:
    """Matrice glTF COLONNE-majeure pour p' = R · (s · p) + t.

    Se tromper d'ordre ici donne un modèle couché, et le banc de bascule Z-up
    est là pour l'attraper.
    """
    m = [[rot[r][c] * s for c in range(3)] for r in range(3)]
    return [m[0][0], m[1][0], m[2][0], 0.0,
            m[0][1], m[1][1], m[2][1], 0.0,
            m[0][2], m[1][2], m[2][2], 0.0,
            float(t[0]), float(t[1]), float(t[2]), 1.0]


def reparer(data: bytes, *, axe_haut: str | None = None,
            echelle: float | None = None, recentrer: bool = False) -> bytes:
    """Assise globale : axe haut, échelle, recentrage sur l'origine.

    La correction est portée par un nœud racine NEUF qui adopte les racines de
    la scène — on ne réécrit jamais les transformations existantes, de sorte
    qu'une réparation reste lisible et annulable dans le document.

    `recentrer` est la seule option qui a besoin de la géométrie : elle passe
    par `print3d.lire_glb_triangles`, qui refuse un GLB compressé avec un
    message explicite. Les deux autres options n'ont pas cette limite.

    Seule la scène active (`doc["scene"]`) est corrigée : un GLB multi-scènes
    garderait les autres intactes. C'est la convention de tout le module —
    `print3d.lire_glb_triangles` et `rig_inventory` font de même — et les
    maillages livrés par Meshy, Tripo ou Rodin sont mono-scène en pratique.

    Deux réparations successives EMPILENT deux nœuds `etabli_correction`
    imbriqués : c'est voulu, chaque correction restant ainsi annulable. Mais
    cela veut dire qu'on ne cherche jamais « le » nœud de correction par son
    nom — il peut y en avoir plusieurs.
    """
    from app.services import print3d

    # Types validés AVANT toute lecture : ces deux paramètres viendront d'un
    # corps JSON (tâche 8), et la route ne traduit en 400 que les ValueError.
    # Sans ces gardes, `axe_haut=123` lève AttributeError et `echelle=[1.0]`
    # lève TypeError — deux 500 au lieu de deux refus parlants.
    if axe_haut is not None and not isinstance(axe_haut, str):
        raise ValueError("axe_haut attend une chaîne (Y ou Z), reçu "
                         f"{type(axe_haut).__name__}")
    if echelle is not None and (isinstance(echelle, bool)
                                or not isinstance(echelle, (int, float))):
        # `bool` est un `int` en Python : sans ce garde, `echelle=True`
        # deviendrait silencieusement une échelle de 1.
        raise ValueError("echelle attend un nombre, reçu "
                         f"{type(echelle).__name__}")

    doc, binc = lire_glb(data)
    axe = (axe_haut or "Y").upper()
    if axe not in _ROT:
        raise ValueError(f"axe haut inconnu : {axe} (attendu Y ou Z)")
    rot = _ROT[axe]
    s = 1.0 if echelle is None else float(echelle)
    if s <= 0:
        raise ValueError("echelle doit être strictement positive")

    t = [0.0, 0.0, 0.0]
    if recentrer:
        tris = print3d.lire_glb_triangles(data)
        (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
        c = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
        t = [-sum(rot[r][k] * s * c[k] for k in range(3)) for r in range(3)]

    scenes = doc.get("scenes") or [{"nodes": []}]
    isc = int(doc.get("scene", 0))
    if not (0 <= isc < len(scenes)):
        raise ValueError(f"scène active {isc} hors du document "
                         f"({len(scenes)} scènes)")
    racines = list(scenes[isc].get("nodes") or [])
    doc.setdefault("nodes", []).append({
        "name": "etabli_correction",
        "children": racines,
        "matrix": _matrice(rot, s, t),
    })
    scenes[isc]["nodes"] = [len(doc["nodes"]) - 1]
    doc["scenes"] = scenes
    return ecrire_glb(doc, binc)


def _dependances(doc: dict, garder: set[int]) -> dict:
    """Tout ce qu'un ensemble de nœuds retenus tire derrière lui.

    L'ordre compte : nœuds -> meshes/skins -> accesseurs et matériaux ->
    textures -> images -> bufferViews. Un maillon oublié produit un GLB qui
    référence un index disparu, et le lecteur le dit brutalement.
    """
    nodes = _l(doc, "nodes")
    meshes = {nodes[i]["mesh"] for i in garder
              if nodes[i].get("mesh") is not None}
    skins = {nodes[i]["skin"] for i in garder
             if nodes[i].get("skin") is not None}
    # un skin dont TOUS les joints ne sont pas retenus est lâché : le garder
    # produirait une peau qui vise des os absents
    skins = {s for s in skins
             if all(j in garder for j in _l(_l(doc, "skins")[s], "joints"))}

    acc: set[int] = set()
    mats: set[int] = set()
    for mi in meshes:
        for p in _l(_l(doc, "meshes")[mi], "primitives"):
            acc.update((p.get("attributes") or {}).values())
            if p.get("indices") is not None:
                acc.add(p["indices"])
            for cible in _l(p, "targets"):
                acc.update(cible.values())
            if p.get("material") is not None:
                mats.add(p["material"])
    for si in skins:
        ibm = _l(doc, "skins")[si].get("inverseBindMatrices")
        if ibm is not None:
            acc.add(ibm)

    texs: set[int] = set()

    def _tex(x) -> None:
        if isinstance(x, dict) and x.get("index") is not None:
            texs.add(x["index"])

    for mi in mats:
        m = _l(doc, "materials")[mi]
        pbr = m.get("pbrMetallicRoughness") or {}
        _tex(pbr.get("baseColorTexture"))
        _tex(pbr.get("metallicRoughnessTexture"))
        _tex(m.get("normalTexture"))
        _tex(m.get("occlusionTexture"))
        _tex(m.get("emissiveTexture"))

    imgs: set[int] = set()
    smps: set[int] = set()
    for ti in texs:
        t = _l(doc, "textures")[ti]
        if t.get("source") is not None:
            imgs.add(t["source"])
        if t.get("sampler") is not None:
            smps.add(t["sampler"])

    bvs: set[int] = set()
    for ai in acc:
        a = _l(doc, "accessors")[ai]
        if a.get("bufferView") is not None:
            bvs.add(a["bufferView"])
        sparse = a.get("sparse") or {}
        for part in ("indices", "values"):
            vue = (sparse.get(part) or {}).get("bufferView")
            if vue is not None:
                bvs.add(vue)
    for ii in imgs:
        vue = _l(doc, "images")[ii].get("bufferView")
        if vue is not None:
            bvs.add(vue)
    # compression : la vue Draco est RECOPIÉE sans être décodée — c'est ce qui
    # fait marcher l'extraction là où le lecteur de triangles refuse
    for mi in meshes:
        for p in _l(_l(doc, "meshes")[mi], "primitives"):
            draco = (p.get("extensions") or {}).get(
                "KHR_draco_mesh_compression") or {}
            if draco.get("bufferView") is not None:
                bvs.add(draco["bufferView"])

    return {"meshes": meshes, "skins": skins, "accessors": acc,
            "materials": mats, "textures": texs, "images": imgs,
            "samplers": smps, "bufferViews": bvs}


_IDENTITE = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
             0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def _mat_mul(a: list, b: list) -> list:
    """Produit de deux matrices 4×4 COLONNE-majeures (convention glTF).

    `m[c * 4 + r]` = colonne c, ligne r. Le produit `a · b` applique b PUIS a.

    `print3d` a ses propres matrices, mais en LIGNE-majeur pour ses calculs
    internes. Ici on écrit dans le champ `matrix` d'un nœud glTF, qui est
    colonne-majeur : convertir d'une convention à l'autre serait plus
    fragile que de tenir les seize lignes ci-dessous.
    """
    out = [0.0] * 16
    for c in range(4):
        for r in range(4):
            out[c * 4 + r] = sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4))
    return out


def _mat_locale(node: dict) -> list:
    """Transformation locale d'un nœud, en colonne-majeur.

    glTF autorise soit `matrix`, soit un TRS — jamais les deux.
    """
    if node.get("matrix"):
        return [float(x) for x in node["matrix"]]
    t = node.get("translation") or [0.0, 0.0, 0.0]
    r = node.get("rotation") or [0.0, 0.0, 0.0, 1.0]
    s = node.get("scale") or [1.0, 1.0, 1.0]
    x, y, z, w = (float(v) for v in r)
    rot = ((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
           (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
           (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)))
    m = [0.0] * 16
    for c in range(3):
        for lig in range(3):
            m[c * 4 + lig] = rot[lig][c] * float(s[c])
    m[12], m[13], m[14] = float(t[0]), float(t[1]), float(t[2])
    m[15] = 1.0
    return m


def _monde_des_ancetres(doc: dict, cible: int) -> list:
    """Matrice monde des ancêtres STRICTS de `cible` (elle-même exclue).

    Identité si la cible est déjà une racine. C'est cette matrice qu'il faut
    pré-multiplier dans la racine extraite pour que la pièce sorte là où
    l'utilisateur la voyait — sans quoi une correction d'assise posée par
    `reparer` disparaîtrait en silence à la découpe.

    La boucle garde un ensemble de nœuds vus : un `children` cyclique dans un
    GLB tiers ne doit pas la faire tourner à l'infini.
    """
    nodes = _l(doc, "nodes")
    parent: dict[int, int] = {}
    for i, n in enumerate(nodes):
        for c in _l(n, "children"):
            parent[c] = i
    chaine: list[int] = []
    cur = parent.get(cible)
    vus: set[int] = set()
    while cur is not None and cur not in vus:
        vus.add(cur)
        chaine.append(cur)
        cur = parent.get(cur)
    m = list(_IDENTITE)
    for i in reversed(chaine):          # de la racine vers le parent direct
        m = _mat_mul(m, _mat_locale(nodes[i]))
    return m


def _carte(ref: set[int]) -> tuple[dict[int, int], list[int]]:
    ordre = sorted(ref)
    return {v: i for i, v in enumerate(ordre)}, ordre


def extraire(data: bytes, noeuds) -> bytes:
    """Un GLB qui ne contient QUE le sous-arbre demandé et ses dépendances.

    RECOPIE D'OCTETS : les bufferViews retenus sont copiés tels quels, sans
    décodage. L'opération survit donc à Draco et meshopt, contrairement à tout
    ce qui lit des triangles.
    """
    doc, binc = lire_glb(data)
    nodes = _l(doc, "nodes")

    garder: set[int] = set()
    pile = [int(n) for n in (noeuds or [])]
    while pile:
        i = pile.pop()
        if i in garder or not (0 <= i < len(nodes)):
            continue
        garder.add(i)
        pile.extend(_l(nodes[i], "children"))
    if not garder:
        raise ValueError("aucun noeud retenu — la selection est vide")

    dep = _dependances(doc, garder)
    m_node, o_node = _carte(garder)
    m_mesh, o_mesh = _carte(dep["meshes"])
    m_mat, o_mat = _carte(dep["materials"])
    m_tex, o_tex = _carte(dep["textures"])
    m_img, o_img = _carte(dep["images"])
    m_smp, o_smp = _carte(dep["samplers"])
    m_acc, o_acc = _carte(dep["accessors"])
    m_bv, o_bv = _carte(dep["bufferViews"])
    m_skin, o_skin = _carte(dep["skins"])

    neuf = bytearray()
    vues: list[dict] = []
    for bi in o_bv:
        v = dict(_l(doc, "bufferViews")[bi])
        off, ln = v.get("byteOffset", 0), v["byteLength"]
        while len(neuf) % 4:
            neuf.append(0)
        v["byteOffset"] = len(neuf)
        v["buffer"] = 0
        neuf += binc[off:off + ln]
        vues.append(v)

    out: dict = {"asset": doc.get("asset") or {"version": "2.0"}}
    out["bufferViews"] = vues
    out["buffers"] = [{"byteLength": len(neuf)}]

    out["accessors"] = []
    for ai in o_acc:
        a = dict(_l(doc, "accessors")[ai])
        if a.get("bufferView") is not None:
            a["bufferView"] = m_bv[a["bufferView"]]
        out["accessors"].append(a)

    if o_smp:
        out["samplers"] = [dict(_l(doc, "samplers")[i]) for i in o_smp]
    if o_img:
        out["images"] = []
        for ii in o_img:
            im = dict(_l(doc, "images")[ii])
            if im.get("bufferView") is not None:
                im["bufferView"] = m_bv[im["bufferView"]]
            out["images"].append(im)
    if o_tex:
        out["textures"] = []
        for ti in o_tex:
            t = dict(_l(doc, "textures")[ti])
            if t.get("source") is not None:
                t["source"] = m_img[t["source"]]
            if t.get("sampler") is not None:
                t["sampler"] = m_smp[t["sampler"]]
            out["textures"].append(t)
    if o_mat:
        out["materials"] = []
        for mi in o_mat:
            m = json.loads(json.dumps(_l(doc, "materials")[mi]))
            pbr = m.get("pbrMetallicRoughness") or {}
            for hote, cle in ((pbr, "baseColorTexture"),
                              (pbr, "metallicRoughnessTexture"),
                              (m, "normalTexture"), (m, "occlusionTexture"),
                              (m, "emissiveTexture")):
                cible = hote.get(cle)
                if isinstance(cible, dict) and cible.get("index") is not None:
                    cible["index"] = m_tex[cible["index"]]
            out["materials"].append(m)

    out["meshes"] = []
    for mi in o_mesh:
        me = json.loads(json.dumps(_l(doc, "meshes")[mi]))
        for p in me.get("primitives") or []:
            p["attributes"] = {k: m_acc[v]
                               for k, v in (p.get("attributes") or {}).items()}
            if p.get("indices") is not None:
                p["indices"] = m_acc[p["indices"]]
            if p.get("material") is not None:
                p["material"] = m_mat[p["material"]]
            for cible in p.get("targets") or []:
                for k in list(cible):
                    cible[k] = m_acc[cible[k]]
            draco = (p.get("extensions") or {}).get(
                "KHR_draco_mesh_compression")
            if draco and draco.get("bufferView") is not None:
                draco["bufferView"] = m_bv[draco["bufferView"]]
        out["meshes"].append(me)

    if o_skin:
        out["skins"] = []
        for si in o_skin:
            s = json.loads(json.dumps(_l(doc, "skins")[si]))
            if s.get("inverseBindMatrices") is not None:
                s["inverseBindMatrices"] = m_acc[s["inverseBindMatrices"]]
            s["joints"] = [m_node[j] for j in _l(s, "joints")]
            if s.get("skeleton") in m_node:
                s["skeleton"] = m_node[s["skeleton"]]
            else:
                s.pop("skeleton", None)
            out["skins"].append(s)

    out["nodes"] = []
    for ni in o_node:
        n = json.loads(json.dumps(nodes[ni]))
        enfants = [m_node[c] for c in _l(n, "children") if c in m_node]
        if enfants:
            n["children"] = enfants
        else:
            n.pop("children", None)
        if n.get("mesh") is not None:
            n["mesh"] = m_mesh[n["mesh"]]
        if n.get("skin") is not None:
            if n["skin"] in m_skin:
                n["skin"] = m_skin[n["skin"]]
            else:
                n.pop("skin")
        n.pop("camera", None)
        out["nodes"].append(n)

    # Chaque racine extraite absorbe la transformation de ses ANCÊTRES restés
    # hors sélection. Sans cela, découper un nœud placé sous le nœud
    # `etabli_correction` de `reparer` ferait perdre la correction EN SILENCE :
    # mesuré — la pièce ressortait en ((-1,1), (2,4), (-1,1)), c'est-à-dire
    # couchée, au lieu du monde redressé ((-1,1), (-1,1), (2,4)).
    for i in sorted({int(x) for x in noeuds}):
        if i not in m_node:
            continue
        a = _monde_des_ancetres(doc, i)
        if a == _IDENTITE:
            continue                    # déjà une racine : rien à absorber
        n = out["nodes"][m_node[i]]
        locale = _mat_locale(nodes[i])
        for cle in ("translation", "rotation", "scale"):
            n.pop(cle, None)
        n["matrix"] = _mat_mul(a, locale)

    racines = [m_node[i] for i in sorted({int(x) for x in noeuds})
               if i in m_node]
    out["scenes"] = [{"nodes": racines}]
    out["scene"] = 0
    for cle in ("extensionsUsed", "extensionsRequired"):
        if doc.get(cle):
            out[cle] = doc[cle]
    return ecrire_glb(out, bytes(neuf))
