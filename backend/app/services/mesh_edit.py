# -*- coding: utf-8 -*-
"""Chirurgie de document glTF — la SEULE plume à GLB du chantier Établi.

Règle de l'option C (spec 2026-08-29-etabli-inspecteur-3d-design §2.1) : le
navigateur voit et manipule, Python écrit. Aucun GLB n'est jamais produit par
le client, de sorte que tout artefact reste versionné, fiché par mesh_report,
et vérifiable par le harnais.

Deux propriétés porteront la sûreté du module, et les bancs des tâches 3 et 5
de ce plan les épingleront (elles n'existent pas encore à la tâche 1) :

* `extraire` est une RECOPIE D'OCTETS, jamais un décodage de géométrie — les
  bufferViews retenus sont copiés tels quels. L'extraction traverse donc un
  GLB **Draco**, là où `print3d.lire_glb_triangles` refuse. Elle refuse en
  revanche **meshopt**, qui place ses octets dans un buffer et à un décalage
  pouvant différer des champs de premier niveau : les recopier en aveugle
  donnerait un fichier faux en silence, ce qui est pire qu'un refus.
* `transformer` ne touche QUE le document JSON — le tampon binaire ressort
  identique octet pour octet, ce qui rend l'opération sûre sur 200 Mo.

La plaque façon slicer (lot B) ajoute deux écritures, toujours en stdlib :
`assise` (poser sur une face — une rotation ARBITRAIRE par Rodrigues, dans un
nœud de correction neuf, comme `reparer`) et `couper` (le couteau : découpe des
triangles traversés, deux nœuds par pièce, capuchons par triangulation en
oreilles, et un compte rendu qui DIT ce qui n'a pas pu être refermé).

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


def _envelopper(doc: dict, matrice: list) -> None:
    """Un nœud `etabli_correction` NEUF, porteur de `matrice`, adopte les
    racines de la scène active — LE site de l'invariant de `reparer` et
    d'`assise` : aucune transformation existante n'est réécrite, deux
    corrections empilent deux nœuds, et personne ne cherche « le » nœud de
    correction par son nom. Seule la scène active est corrigée."""
    scenes = doc.get("scenes") or [{"nodes": []}]
    isc = int(doc.get("scene", 0))
    if not (0 <= isc < len(scenes)):
        raise ValueError(f"scène active {isc} hors du document "
                         f"({len(scenes)} scènes)")
    racines = list(scenes[isc].get("nodes") or [])
    doc.setdefault("nodes", []).append({
        "name": "etabli_correction",
        "children": racines,
        "matrix": matrice,
    })
    scenes[isc]["nodes"] = [len(doc["nodes"]) - 1]
    doc["scenes"] = scenes


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

    _envelopper(doc, _matrice(rot, s, t))
    return ecrire_glb(doc, binc)


def _renvois_de_texture(materiau: dict) -> list[dict]:
    """Tous les renvois de texture d'un matériau, EXTENSIONS COMPRISES.

    Les emplacements PBR de base ne sont que cinq, mais
    `KHR_materials_clearcoat`, `_sheen`, `_transmission`, `_specular`… en
    ajoutent d'autres. Tenir la liste à jour serait perdre la course : on
    cherche donc toute clé finissant par « Texture » et portant un `index`.

    Rend les sous-dictionnaires eux-mêmes, pour que l'appelant puisse y
    réécrire l'index remappé.
    """
    trouves: list[dict] = []
    pile: list = [materiau]
    while pile:
        cur = pile.pop()
        if isinstance(cur, dict):
            for cle, val in cur.items():
                if cle == "extras":
                    # `extras` est de la donnée LIBRE d'application : la spec
                    # glTF n'y met aucune structure. Un outil tiers peut y
                    # poser une clé finissant par « Texture » avec un `index`
                    # qui ne désigne aucune texture — mesuré : IndexError au
                    # remappage. On ne descend donc jamais dedans.
                    continue
                if (isinstance(cle, str) and cle.endswith("Texture")
                        and isinstance(val, dict)
                        and val.get("index") is not None):
                    trouves.append(val)
                else:
                    pile.append(val)
        elif isinstance(cur, list):
            pile.extend(cur)
    return trouves


def _extensions_presentes(noeud) -> set[str]:
    """Noms des extensions réellement utilisées quelque part dans un document.

    Sert à ne déclarer dans `extensionsUsed` / `extensionsRequired` que ce que
    la pièce extraite porte vraiment.
    """
    trouvees: set[str] = set()
    pile: list = [noeud]
    while pile:
        cur = pile.pop()
        if isinstance(cur, dict):
            ext = cur.get("extensions")
            if isinstance(ext, dict):
                trouvees.update(k for k in ext if isinstance(k, str))
            pile.extend(cur.values())
        elif isinstance(cur, list):
            pile.extend(cur)
    return trouvees


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
    for mi in mats:
        for renvoi in _renvois_de_texture(_l(doc, "materials")[mi]):
            texs.add(renvoi["index"])

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
    # Un quaternion non unitaire ne donne pas une sur-échelle propre mais un
    # CISAILLEMENT du plan perpendiculaire à l'axe — mesuré : pour une norme
    # de 1,2, les termes hors-diagonale ressortent à 1,44 pendant que l'axe
    # reste à 1,0. `transformer` refuse un tel quaternion, parce qu'il vient
    # d'un client. Ici il vient d'un FICHIER qu'on ne fait que lire : refuser
    # rendrait inexploitable un GLB tiers un peu dérivé, alors on normalise —
    # et on le dit, pour que l'asymétrie avec `transformer` soit un choix lu
    # et non une incohérence.
    #
    # CONSÉQUENCE MESURÉE, à connaître : sur un fichier déjà invalide au sens
    # glTF, la pièce extraite ne coïncide plus avec ce que
    # `print3d.lire_glb_triangles` lit de la scène source — le lecteur
    # applique le quaternion brut, donc le cisaillement. Avec une norme de
    # 1,2 : source ((-1,1), (-3.2, 0.56), (2.44, 6.2)), pièce extraite
    # identique au cas unitaire. On restitue la rotation manifestement voulue
    # plutôt que la déformation ; c'est un choix, pas un hasard.
    norme = (x * x + y * y + z * z + w * w) ** 0.5
    if norme and abs(norme - 1.0) > 1e-6:
        x, y, z, w = x / norme, y / norme, z / norme, w / norme
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
    décodage. L'opération traverse donc Draco, contrairement à tout ce qui lit
    des triangles. Elle refuse meshopt, dont les octets vivent hors des champs
    de premier niveau (voir le refus ci-dessous).
    """
    doc, binc = lire_glb(data)
    out, neuf, _ = _extraire_doc(doc, binc, noeuds)
    return ecrire_glb(out, neuf)


def _extraire_doc(doc: dict, binc: bytes, noeuds) -> tuple[dict, bytes, dict]:
    """Le corps d'`extraire` sur un document déjà lu : rend (document, tampon,
    carte des nœuds retenus → index neufs). La carte est ce que `couper`
    consomme pour dire, dans son compte rendu, les index de la version
    compactée — sans refaire la renumérotation de `_carte` à côté. Le
    document reçu n'est pas modifié."""
    nodes = _l(doc, "nodes")

    # meshopt place ses octets dans un buffer et à un décalage qui peuvent
    # différer de ceux déclarés au premier niveau de la bufferView. Ce module
    # ne lit qu'un seul buffer : plutôt que de recopier les mauvais octets en
    # silence — un fichier faux qui ne se voit qu'à l'ouverture — on refuse,
    # et on dit quoi faire à la place.
    if "EXT_meshopt_compression" in (doc.get("extensionsRequired") or []):
        raise ValueError(
            "GLB compressé meshopt — l'extraction ne sait pas le recopier "
            "sans risque (les octets vivent hors des champs de premier "
            "niveau de la bufferView). Pars du model.glb non compressé.")

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
        # COPIE PROFONDE : un accesseur `sparse` porte des sous-objets qu'on
        # va réécrire ; une copie superficielle abîmerait le document source.
        a = json.loads(json.dumps(_l(doc, "accessors")[ai]))
        if a.get("bufferView") is not None:
            a["bufferView"] = m_bv[a["bufferView"]]
        # Un accesseur `sparse` porte DEUX vues de plus, dans des sous-objets.
        # `_dependances` les garde déjà ; sans ce remappage elles resteraient
        # aux index d'origine — mesuré : 11 et 12 dans une pièce réduite à
        # 7 vues, donc hors bornes et GLB invalide.
        sparse = a.get("sparse") or {}
        for part in ("indices", "values"):
            bloc = sparse.get(part)
            if isinstance(bloc, dict) and bloc.get("bufferView") is not None:
                bloc["bufferView"] = m_bv[bloc["bufferView"]]
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
            # Même parcours qu'à la collecte : sans lui, une `clearcoatTexture`
            # survivrait avec un index pointant dans le vide — mesuré.
            for renvoi in _renvois_de_texture(m):
                renvoi["index"] = m_tex[renvoi["index"]]
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

    # Une sélection peut contenir un nœud ET l'un de ses descendants — cocher
    # un parent puis son enfant dans le panneau Parties est un geste naturel.
    # Les lister tous deux comme racines de scène DOUBLERAIT l'enfant : il
    # serait dessiné une fois par la racine, une fois par son parent. Mesuré :
    # 16 triangles au lieu de 14. Seuls les nœuds demandés qui n'ont aucun
    # ANCÊTRE lui-même demandé sont donc des racines ; les autres restent
    # atteignables par leur parent.
    demandes = [i for i in sorted({int(x) for x in noeuds}) if i in m_node]
    demandes_set = set(demandes)
    parent_de: dict[int, int] = {}
    for i, n in enumerate(nodes):
        for c in _l(n, "children"):
            parent_de[c] = i

    def _sous_une_autre_demande(i: int) -> bool:
        vus: set[int] = set()
        cur = parent_de.get(i)
        while cur is not None and cur not in vus:
            if cur in demandes_set:
                return True
            vus.add(cur)
            cur = parent_de.get(cur)
        return False

    vraies_racines = [i for i in demandes if not _sous_une_autre_demande(i)]

    # Chaque VRAIE racine absorbe la transformation de ses ancêtres restés hors
    # sélection. Sans cela, découper un nœud placé sous le nœud
    # `etabli_correction` de `reparer` ferait perdre la correction EN SILENCE :
    # mesuré — la pièce ressortait en ((-1,1), (2,4), (-1,1)), c'est-à-dire
    # couchée, au lieu du monde redressé ((-1,1), (-1,1), (2,4)).
    for i in vraies_racines:
        a = _monde_des_ancetres(doc, i)
        if a == _IDENTITE:
            continue                    # déjà une racine : rien à absorber
        n = out["nodes"][m_node[i]]
        locale = _mat_locale(nodes[i])
        for cle in ("translation", "rotation", "scale"):
            n.pop(cle, None)
        n["matrix"] = _mat_mul(a, locale)

    out["scenes"] = [{"nodes": [m_node[i] for i in vraies_racines]}]
    out["scene"] = 0
    # Ne déclarer que les extensions RÉELLEMENT présentes dans la pièce.
    # Recopier les listes en bloc ferait déclarer `KHR_draco_mesh_compression`
    # à une pièce sans un seul octet compressé — et `lire_glb_triangles` la
    # refuserait alors qu'elle est saine. Mesuré : la fiche de version de la
    # tâche 6 aurait essuyé un refus injustifié, très déroutant à diagnostiquer.
    presentes = _extensions_presentes(out)
    for cle in ("extensionsUsed", "extensionsRequired"):
        gardees = [e for e in (doc.get(cle) or []) if e in presentes]
        if gardees:
            out[cle] = gardees

    # DETTE ASSUMÉE : le sous-objet racine `doc["extensions"]` n'est PAS
    # recopié. Un nœud portant `KHR_lights_punctual.light` sortirait donc avec
    # un index qui ne se résout plus. Les générateurs de ce pipeline (Meshy,
    # Tripo, Rodin) ne posent pas de lumières de scène ; si P4-P5 en amène,
    # c'est ici qu'il faudra regarder — ne pas supposer que c'est déjà couvert.
    return out, bytes(neuf), m_node


# ── l'assise sur une FACE : la rotation arbitraire ───────────────────────────
# « Poser sur une face » (la touche F des slicers) : la face désignée dans le
# canevas devient l'assise. `reparer` ne connaît que deux axes (`_ROT`) ; ici la
# normale est quelconque, et la rotation qui l'amène vers le bas se construit
# par Rodrigues. Le haut de la scène glTF est +Y — après toute correction
# antérieure, puisque le nœud neuf enveloppe les racines COURANTES, correction
# comprise — et « vers le bas » est donc (0, −1, 0).

_BAS = (0.0, -1.0, 0.0)
_I3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _vecteur3(v, quoi: str) -> tuple[float, float, float]:
    """Trois nombres FINIS, ou un refus parlant — ces valeurs viennent d'un
    corps JSON, et la route ne traduit en 400 que les ValueError. `bool` est
    un `int` en Python : sans le garde, `[True, 0, 0]` passerait pour
    (1, 0, 0)."""
    if isinstance(v, (str, bytes)) or not isinstance(v, (list, tuple)):
        raise ValueError(f"{quoi} attend une liste de trois nombres [x, y, z]")
    if len(v) != 3:
        raise ValueError(f"{quoi} attend trois nombres, reçu {len(v)}")
    out = []
    for c in v:
        if isinstance(c, bool) or not isinstance(c, (int, float)):
            raise ValueError(f"{quoi} attend des nombres, reçu "
                             f"{type(c).__name__}")
        c = float(c)
        if c != c or c in (float("inf"), float("-inf")):
            raise ValueError(f"{quoi} : composante non finie")
        out.append(c)
    return out[0], out[1], out[2]


def _unitaire(v, quoi: str) -> tuple[float, float, float]:
    x, y, z = _vecteur3(v, quoi)
    n = (x * x + y * y + z * z) ** 0.5
    if n < 1e-12:
        raise ValueError(f"{quoi} nulle — une direction ne peut pas être "
                         "(0, 0, 0)")
    return x / n, y / n, z / n


def _rodrigues(a, b):
    """La rotation 3×3 (lignes) qui amène le vecteur UNITAIRE a sur b.

    R = I + [v]× + [v]×² · (1 − c) / s², avec v = a × b, s = |v|, c = a · b.
    Deux vecteurs déjà alignés rendent l'identité ; deux vecteurs OPPOSÉS ont
    s = 0 et la formule diverge : c'est un demi-tour autour de n'importe quel
    axe perpendiculaire à a, et l'on prend celui que l'axe du monde le moins
    aligné avec a donne — R = 2·u·uᵀ − I.
    """
    v = (a[1] * b[2] - a[2] * b[1],
         a[2] * b[0] - a[0] * b[2],
         a[0] * b[1] - a[1] * b[0])
    s2 = v[0] * v[0] + v[1] * v[1] + v[2] * v[2]
    c = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    if s2 < 1e-24:
        if c > 0:
            return _I3
        k = min(range(3), key=lambda i: abs(a[i]))
        e = [0.0, 0.0, 0.0]
        e[k] = 1.0
        u = [e[i] - a[k] * a[i] for i in range(3)]
        nu = (u[0] * u[0] + u[1] * u[1] + u[2] * u[2]) ** 0.5
        u = [x / nu for x in u]
        return tuple(tuple(2.0 * u[r] * u[col] - (1.0 if r == col else 0.0)
                           for col in range(3)) for r in range(3))
    k = (1.0 - c) / s2
    vx = ((0.0, -v[2], v[1]), (v[2], 0.0, -v[0]), (-v[1], v[0], 0.0))
    vx2 = tuple(tuple(sum(vx[r][m] * vx[m][col] for m in range(3))
                      for col in range(3)) for r in range(3))
    return tuple(tuple(_I3[r][col] + vx[r][col] + k * vx2[r][col]
                       for col in range(3)) for r in range(3))


def _appliquer3(rot, p):
    return tuple(rot[r][0] * p[0] + rot[r][1] * p[1] + rot[r][2] * p[2]
                 for r in range(3))


def assise(data: bytes, *, normale, point=None) -> bytes:
    """Pose le modèle sur la face de normale MONDE `normale` : la rotation qui
    amène cette normale sur (0, −1, 0), autour du pivot `point` (le point
    cliqué — sans pivot, un modèle loin de l'origine partirait à l'autre bout
    de la scène), puis la translation de CONTACT : min Y du maillage tourné à
    zéro. C'est « Réparer l'assise » en un geste, sans choisir un axe.

    MÊME INVARIANT QUE `reparer`, et il n'est pas négociable : un nœud
    `etabli_correction` NEUF adopte les racines de la scène active. On ne
    réécrit JAMAIS une transformation existante ; deux assises empilent deux
    nœuds, et l'on ne cherche jamais « le » nœud de correction par son nom.

    La translation de contact a besoin de la géométrie : elle passe par
    `print3d.lire_glb_triangles`, qui refuse un GLB compressé en le disant —
    la même limite que `recentrer`, et le même message.
    """
    from app.services import print3d

    n = _unitaire(normale, "normale")
    c = _vecteur3(point, "point") if point is not None else None
    rot = _rodrigues(n, _BAS)
    tris = print3d.lire_glb_triangles(data)
    if c is None:
        (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
        c = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
    rc = _appliquer3(rot, c)
    t = [c[0] - rc[0], c[1] - rc[1], c[2] - rc[2]]
    # Le contact : le plus bas des sommets TOURNÉS touche y = 0. Lu sur les
    # triangles monde de la version telle qu'elle est — corrections
    # antérieures comprises, puisque c'est elles que le nœud neuf enveloppe.
    ymin = min(rot[1][0] * v[0] + rot[1][1] * v[1] + rot[1][2] * v[2]
               for tri in tris for v in tri) + t[1]
    t[1] -= ymin
    doc, binc = lire_glb(data)
    _envelopper(doc, _matrice(rot, 1.0, t))
    return ecrire_glb(doc, binc)


# ── lecture d'accesseurs : le chemin rapide du couteau ───────────────────────
# `print3d._accessor` déballe élément par élément et suffit à lire des
# triangles ; le couteau relit CHAQUE attribut de la pièce et la réécrit, et
# `struct.iter_unpack` sur une vue serrée va bien plus vite (mesuré sur les
# 72 128 sommets du cadre du modèle réel). Le pas explicite (`byteStride`)
# reste lu élément par élément.

_COMPOSANTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
               5125: ("I", 4), 5126: ("f", 4)}
_NB_COMPOSANTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
                  "MAT2": 4, "MAT3": 9, "MAT4": 16}


def _lire_accesseur(doc: dict, binc: bytes, i: int) -> list[tuple]:
    a = _l(doc, "accessors")[i]
    if a.get("sparse"):
        raise ValueError(f"accesseur {i} « sparse » — hors périmètre du couteau")
    if a.get("bufferView") is None:
        raise ValueError(f"accesseur {i} sans bufferView — hors périmètre du "
                         "couteau")
    ct, ty = a["componentType"], a["type"]
    if ct not in _COMPOSANTS or ty not in _NB_COMPOSANTS:
        raise ValueError(f"accesseur {i} : composant {ct} / type {ty} hors "
                         "périmètre")
    fmt, taille = _COMPOSANTS[ct]
    n = _NB_COMPOSANTS[ty]
    bv = _l(doc, "bufferViews")[a["bufferView"]]
    if "uri" in _l(doc, "buffers")[bv.get("buffer", 0)]:
        raise ValueError("buffer externe (uri) — nos GLB sont monolithiques, "
                         "hors périmètre")
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    serre = taille * n
    pas = bv.get("byteStride") or serre
    count = int(a["count"])
    if pas == serre:
        return list(struct.iter_unpack("<" + fmt * n,
                                       binc[base:base + count * serre]))
    f = "<" + fmt * n
    return [struct.unpack_from(f, binc, base + k * pas) for k in range(count)]


# ── le couteau : couper des pièces par un plan, et les REFERMER ──────────────
# La demande : « les outils couteau des slicers ». Le navigateur montre le plan
# et l'aperçu des deux moitiés (clipping three.js, rien n'y est fabriqué) ;
# ICI on coupe pour de vrai, en stdlib pure : chaque triangle traversé est
# découpé (POSITION, NORMAL, TEXCOORD et tout attribut flottant interpolés sur
# l'arête), les deux moitiés sont réparties, et chaque côté est REFERMÉ par un
# capuchon — segments de section → boucles → triangulation par oreilles. Une
# pièce imprimée doit être étanche : c'est tout l'objet de couper avant le
# slicer, et c'est pourquoi un capuchon qu'on ne sait pas poser SE DIT dans
# le compte rendu plutôt que de laisser une géométrie fausse en silence.
#
# CE QUE LE COMPTE RENDU DIT (le `source` de la fiche report.json, lu par
# /api/etabli/productions et par l'onglet Établi de la Bibliothèque) — site
# canonique du format, le miroir vit dans routes.py à côté de la route :
#
#   { "outil": "etabli", "operation": "couper",
#     "plan": { "point": [x, y, z], "normale": [x, y, z], "repere": "monde" },
#     "garder": "deux" | "a" | "b",   a = le côté vers lequel pointe la normale
#     "noeuds": [i, …],              les index DEMANDÉS, dans la version coupée
#     "pieces": [ { "noeud": i, "nom": "cadre", "triangles": N,
#                   "traversee": true,
#                   "cotes": { "a": { "noeud": j,   index dans la version NEUVE
#                                     "nom": "cadre_a", "triangles": Na,
#                                     "capuchon": { "pose": true,
#                                                   "triangles": k, "boucles": 1 }
#                                                | { "pose": false,
#                                                    "raison": "…",
#                                                    "boucles": 0, "ouvertes": 1 } },
#                              "b": { … } },
#                   "retire": [ "b" ] } ],   les côtés que `garder` a écartés
#     "capuchons": { "materiau": "le premier matériau de la pièce",
#                    "uv": [0, 0] } }
#   Une pièce que le plan ne traverse pas a `"traversee": false`, un seul côté
#   sous `"entier"`, et n'est ni renommée ni renumérotée ; si `garder` écarte
#   ce côté-là, elle est retirée et `"retire"` le dit.

_GARDER = ("deux", "a", "b")
_EPS_AIRE = 1e-12


class _Cote:
    """Un côté du plan pour UNE primitive : ses sommets (une colonne par
    attribut), ses triangles, et les deux tables qui évitent de dupliquer un
    sommet — les sommets d'origine par index, les points de section par clé
    d'arête."""
    __slots__ = ("cols", "tris", "orig", "inter")

    def __init__(self, nb_attrs: int):
        self.cols = [[] for _ in range(nb_attrs)]
        self.tris = []
        self.orig = {}
        self.inter = {}

    def sommet_orig(self, i: int, valeurs) -> int:
        k = self.orig.get(i)
        if k is None:
            k = len(self.cols[0])
            self.orig[i] = k
            for col, val in zip(self.cols, valeurs):
                col.append(val[i])
        return k

    def sommet_inter(self, cle, v) -> int:
        k = self.inter.get(cle)
        if k is None:
            k = len(self.cols[0])
            self.inter[cle] = k
            for col, x in zip(self.cols, v):
                col.append(x)
        return k

    def sommet_neuf(self, v) -> int:
        k = len(self.cols[0])
        for col, x in zip(self.cols, v):
            col.append(x)
        return k


def _plan_local(m: list, point, normale):
    """Le plan MONDE (point P, normale N) lu dans le repère LOCAL d'un nœud de
    matrice monde m (colonne-majeure) : d(p) = n_l · p + c_l vaut EXACTEMENT
    (W·p − P) · N. n_l = W_linᵀ · N — la transposée, et non l'inverse : ce
    qu'il faut pour une distance, et ce qui reste juste sous une échelle NON
    UNIFORME, où « tourner la normale » serait faux (le banc le mesure sur une
    boîte 1,3 × 0,7 × 0,4)."""
    nl = tuple(m[c * 4] * normale[0] + m[c * 4 + 1] * normale[1]
               + m[c * 4 + 2] * normale[2] for c in range(3))
    cl = ((m[12] - point[0]) * normale[0] + (m[13] - point[1]) * normale[1]
          + (m[14] - point[2]) * normale[2])
    return nl, cl


def _decouper_primitive(noms: list, valeurs: list, indices: list, d: list,
                        i_nrm):
    """Répartit et découpe les triangles d'UNE primitive de part et d'autre
    du plan. Rend (côté a, côté b, segments de section) — les segments sont
    des paires de POSITIONS, pas d'index : la section se recoud par position,
    ce qui traverse les coutures UV (deux index pour un même point) et les
    frontières de primitives.

    Le côté a est d ≥ 0 (le sens de la normale). Un sommet EXACTEMENT sur le
    plan compte donc côté a ; l'intersection d'une arête qui part de lui est
    lui-même (t = 0), et le triangle plat qui en naît est écarté — ce sont les
    deux seules concessions faites au cas dégénéré, et elles laissent la
    section juste.

    L'enroulement est CONSERVÉ : le sommet seul de son côté ouvre le triangle
    (seul, p, q) — une rotation cyclique de l'original —, et les deux
    triangles de l'autre côté se lisent (x1, p, q), (x1, q, x2).
    """
    ip = noms.index("POSITION")
    pos = valeurs[ip]
    a, b = _Cote(len(noms)), _Cote(len(noms))
    points: dict = {}
    segments: list = []

    def inter(i: int, j: int):
        cle = (i, j) if i < j else (j, i)
        v = points.get(cle)
        if v is None:
            # L'interpolation part TOUJOURS de la plus petite POSITION, pas du
            # plus petit index : une couture UV porte la même arête sous deux
            # paires d'index, souvent dans l'ordre inverse, et a + (b − a)·t
            # ne vaut pas b + (a − b)·(1 − t) au dernier bit. Mesuré : sur le
            # cube du banc, la section restait une chaîne OUVERTE de neuf
            # arêtes non appariées, et aucun capuchon ne se posait.
            i0, j0 = (cle if pos[cle[0]] <= pos[cle[1]] else (cle[1], cle[0]))
            di, dj = d[i0], d[j0]
            t = di / (di - dj)
            v = []
            for k, val in enumerate(valeurs):
                vi, vj = val[i0], val[j0]
                x = tuple(u + (w - u) * t for u, w in zip(vi, vj))
                if k == i_nrm:
                    # une normale interpolée n'est plus unitaire — glTF les
                    # veut normées, et un lecteur strict s'en plaindrait
                    nn = (x[0] * x[0] + x[1] * x[1] + x[2] * x[2]) ** 0.5
                    if nn > 0:
                        x = (x[0] / nn, x[1] / nn, x[2] / nn)
                v.append(x)
            v = tuple(v)
            points[cle] = v
        return cle, v

    def plat(p0, p1, p2) -> bool:
        return p0 == p1 or p1 == p2 or p0 == p2

    for k in range(0, len(indices) - 2, 3):
        i0, i1, i2 = indices[k], indices[k + 1], indices[k + 2]
        s0, s1, s2 = d[i0] >= 0, d[i1] >= 0, d[i2] >= 0
        if s0 == s1 == s2:
            cote = a if s0 else b
            cote.tris.append((cote.sommet_orig(i0, valeurs),
                              cote.sommet_orig(i1, valeurs),
                              cote.sommet_orig(i2, valeurs)))
            continue
        if s0 == s1:
            seul, p, q, cote_seul = i2, i0, i1, s2
        elif s1 == s2:
            seul, p, q, cote_seul = i0, i1, i2, s0
        else:
            seul, p, q, cote_seul = i1, i2, i0, s1
        c1, v1 = inter(seul, p)
        c2, v2 = inter(seul, q)
        solo, autre = (a, b) if cote_seul else (b, a)
        if not plat(pos[seul], v1[ip], v2[ip]):
            solo.tris.append((solo.sommet_orig(seul, valeurs),
                              solo.sommet_inter(c1, v1),
                              solo.sommet_inter(c2, v2)))
        x1 = autre.sommet_inter(c1, v1)
        x2 = autre.sommet_inter(c2, v2)
        pp = autre.sommet_orig(p, valeurs)
        qq = autre.sommet_orig(q, valeurs)
        if not plat(v1[ip], pos[p], pos[q]):
            autre.tris.append((x1, pp, qq))
        if not plat(v1[ip], pos[q], v2[ip]):
            autre.tris.append((x1, qq, x2))
        if v1[ip] != v2[ip]:
            segments.append((v1[ip], v2[ip]))
    return a, b, segments


def _boucles(segments: list):
    """Recoud les segments de section en BOUCLES fermées et en CHAÎNES
    ouvertes, par position exacte. Rend (boucles, ouvertes) : des listes de
    positions. Une chaîne reste ouverte quand un bout n'a qu'un segment (la
    surface n'était pas fermée) ou quand un point en porte trois ou plus (une
    jonction : la section n'est pas une courbe simple)."""
    ident: dict = {}
    pts: list = []
    aretes: list = []
    for p, q in segments:
        ia = ident.setdefault(p, len(pts))
        if ia == len(pts):
            pts.append(p)
        ib = ident.setdefault(q, len(pts))
        if ib == len(pts):
            pts.append(q)
        if ia != ib:
            aretes.append((ia, ib))
    voisins: dict = {}
    for e, (ia, ib) in enumerate(aretes):
        voisins.setdefault(ia, []).append(e)
        voisins.setdefault(ib, []).append(e)
    vus = [False] * len(aretes)

    def avancer(chaine: list):
        while True:
            cur = chaine[-1]
            inc = voisins[cur]
            if len(inc) != 2:
                return
            e = inc[1] if vus[inc[0]] else inc[0]
            if vus[e]:
                return
            vus[e] = True
            x, y = aretes[e]
            chaine.append(y if x == cur else x)
            if chaine[-1] == chaine[0]:
                return

    boucles, ouvertes = [], []
    for e0 in range(len(aretes)):
        if vus[e0]:
            continue
        vus[e0] = True
        chaine = list(aretes[e0])
        avancer(chaine)
        if chaine[-1] != chaine[0]:
            chaine.reverse()
            avancer(chaine)
        if chaine[-1] == chaine[0] and len(chaine) > 3:
            boucles.append([pts[i] for i in chaine[:-1]])
        else:
            ouvertes.append([pts[i] for i in chaine])
    return boucles, ouvertes


def _base_du_plan(n):
    """(e1, e2) orthonormés dans le plan de normale unitaire n."""
    k = min(range(3), key=lambda i: abs(n[i]))
    e = [0.0, 0.0, 0.0]
    e[k] = 1.0
    e1 = [e[i] - n[i] * n[k] for i in range(3)]
    l1 = (e1[0] * e1[0] + e1[1] * e1[1] + e1[2] * e1[2]) ** 0.5
    e1 = (e1[0] / l1, e1[1] / l1, e1[2] / l1)
    e2 = (n[1] * e1[2] - n[2] * e1[1], n[2] * e1[0] - n[0] * e1[2],
          n[0] * e1[1] - n[1] * e1[0])
    return e1, e2


def _dedans_polygone(pt, poly) -> bool:
    """Point dans un polygone 2D — lancer de rayon, pair/impair."""
    x, y = pt
    dedans = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xi:
                dedans = not dedans
    return dedans


def _trianguler(poly: list):
    """Triangulation par OREILLES d'un polygone 2D simple. Rend la liste des
    triplets d'index, ou None quand aucune oreille ne se présente plus — un
    polygone auto-intersecté, typiquement. Les sommets réflexes sont tenus à
    part : ce sont les seuls qui puissent tomber dans une oreille, et les
    tester seuls ramène le coût au carré plutôt qu'au cube."""
    n = len(poly)
    if n < 3:
        return None
    aire2 = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1]
                for i in range(n))
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    diag2 = (max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2
    eps = _EPS_AIRE * diag2
    if abs(aire2) <= eps:
        return None
    idx = list(range(n))
    if aire2 < 0:
        idx.reverse()

    def croix(i, j, k):
        (ax, ay), (bx, by), (cx, cy) = poly[i], poly[j], poly[k]
        return (bx - ax) * (cy - by) - (by - ay) * (cx - bx)

    def dans_triangle(pt, i, j, k):
        (ax, ay), (bx, by), (cx, cy) = poly[i], poly[j], poly[k]
        px, py = pt
        d1 = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        d2 = (cx - bx) * (py - by) - (cy - by) * (px - bx)
        d3 = (ax - cx) * (py - cy) - (ay - cy) * (px - cx)
        return d1 >= -eps and d2 >= -eps and d3 >= -eps

    tris = []
    reflexes = set()
    m = len(idx)
    for k in range(m):
        if croix(idx[k - 1], idx[k], idx[(k + 1) % m]) < -eps:
            reflexes.add(idx[k])
    while len(idx) > 3:
        m = len(idx)
        choix = plate = None
        for k in range(m):
            ip, i, inx = idx[k - 1], idx[k], idx[(k + 1) % m]
            if i in reflexes:
                continue
            c = croix(ip, i, inx)
            if c > eps:
                if any(j not in (ip, i, inx) and dans_triangle(poly[j], ip, i, inx)
                       for j in reflexes):
                    continue
                choix = k
                break
            if plate is None and abs(c) <= eps:
                plate = k
        # Une oreille CONVEXE d'abord ; une oreille PLATE (trois points alignés,
        # le cas de chaque triangle traversé le long d'une face plane) ne se
        # coupe qu'à défaut, et ÉMET son triangle d'aire nulle. Retirée sans
        # triangle, l'arête (ip, inx) du capuchon n'aurait pas de jumelle sur
        # la paroi — une jonction en T. Mesuré sur le cadre du modèle réel :
        # 330 arêtes non appariées par moitié, et 3 sur le cube du banc.
        if choix is None:
            choix = plate
        if choix is None:
            return None
        k = choix
        ip, i, inx = idx[k - 1], idx[k], idx[(k + 1) % m]
        tris.append((ip, i, inx))
        del idx[k]
        m -= 1
        for j in (ip, inx):
            pos = idx.index(j)
            if croix(idx[pos - 1], j, idx[(pos + 1) % m]) < -eps:
                reflexes.add(j)
            else:
                reflexes.discard(j)
    tris.append(tuple(idx))
    return tris


def _capuchon(boucles: list, ouvertes: list, n_unit, vers, noms: list, i_nrm):
    """Les triangles du capuchon d'UN côté, à partir des boucles de la
    section, orientés vers `vers` (l'extérieur de ce côté : −n pour le côté a,
    +n pour le côté b). Rend (sommets, triangles, compte rendu) ; les sommets
    portent la normale du plan, un UV à (0, 0), une tangente dans le plan et
    des zéros pour tout autre attribut — c'est dit dans le compte rendu.

    Des boucles IMBRIQUÉES (une section à trou : un tube, un tore) ne se
    bouchent pas en v1 : boucher chacune remplirait le trou, ce qui serait
    une géométrie fausse. On ne pose rien et on le dit."""
    if not boucles:
        raison = ("surface ouverte : la section ne se referme pas "
                  f"({len(ouvertes)} chaîne(s) ouverte(s)) — rien à boucher"
                  if ouvertes else "le plan ne produit aucune section")
        return [], [], {"pose": False, "raison": raison, "boucles": 0,
                        "ouvertes": len(ouvertes)}
    e1, e2 = _base_du_plan(n_unit)
    plans2d = [[(p[0] * e1[0] + p[1] * e1[1] + p[2] * e1[2],
                 p[0] * e2[0] + p[1] * e2[1] + p[2] * e2[2]) for p in b]
               for b in boucles]
    for i, bi in enumerate(plans2d):
        for j, bj in enumerate(plans2d):
            if i != j and _dedans_polygone(bj[0], bi):
                return [], [], {
                    "pose": False,
                    "raison": f"{len(boucles)} boucles imbriquées (la section "
                              "a un trou) — le couteau v1 ne perce pas, "
                              "capuchon non posé",
                    "boucles": len(boucles), "ouvertes": len(ouvertes)}
    # L'ORIENTATION SE DÉCIDE UNE FOIS POUR TOUTE LA BOUCLE, jamais triangle
    # par triangle. `_trianguler` rend des triangles tournés dans le sens de la
    # base (e1, e2, n) — leur normale géométrique est +n ; on les retourne
    # tous si l'extérieur est −n. Juger chaque triangle à son produit
    # vectoriel semblait équivalent et ne l'est pas : le long d'une face plane,
    # la section aligne des centaines de points et les triangles en aiguille
    # ont une normale noyée dans le bruit — mesuré sur le cadre du modèle réel,
    # 371 arêtes du capuchon dans le MÊME sens que la paroi, donc non
    # appariées, sur une pièce pourtant fermée.
    inverser = (vers[0] * n_unit[0] + vers[1] * n_unit[1]
                + vers[2] * n_unit[2]) < 0
    sommets: list = []
    tris: list = []
    for b3, b2 in zip(boucles, plans2d):
        t = _trianguler(b2)
        if t is None:
            return [], [], {
                "pose": False,
                "raison": "boucle de section non triangulable "
                          "(auto-intersection ?) — capuchon non posé",
                "boucles": len(boucles), "ouvertes": len(ouvertes)}
        base = len(sommets)
        for p in b3:
            v = []
            for k, nom in enumerate(noms):
                if nom == "POSITION":
                    v.append(p)
                elif k == i_nrm:
                    v.append(vers)
                elif nom == "TANGENT":
                    v.append((e1[0], e1[1], e1[2], 1.0))
                else:
                    v.append(None)      # comblé par des zéros à l'emballage
            sommets.append(v)
        for (i, j, k) in t:
            if inverser:
                j, k = k, j
            tris.append((base + i, base + j, base + k))
    return sommets, tris, {"pose": True, "triangles": len(tris),
                           "boucles": len(boucles), "ouvertes": len(ouvertes)}


def _ajouter_vue(doc: dict, tampon: bytearray, octets: bytes, cible: int) -> int:
    while len(tampon) % 4:
        tampon.append(0)
    doc.setdefault("bufferViews", []).append(
        {"buffer": 0, "byteOffset": len(tampon), "byteLength": len(octets),
         "target": cible})
    tampon += octets
    return len(doc["bufferViews"]) - 1


def _ajouter_flottants(doc: dict, tampon: bytearray, valeurs: list, n: int,
                       avec_bornes: bool) -> int:
    plat = [x for v in valeurs for x in v]
    vue = _ajouter_vue(doc, tampon, struct.pack("<%df" % len(plat), *plat),
                       34962)
    a = {"bufferView": vue, "componentType": 5126, "count": len(valeurs),
         "type": {1: "SCALAR", 2: "VEC2", 3: "VEC3", 4: "VEC4"}[n]}
    if avec_bornes:
        a["min"] = [min(v[k] for v in valeurs) for k in range(n)]
        a["max"] = [max(v[k] for v in valeurs) for k in range(n)]
    doc.setdefault("accessors", []).append(a)
    return len(doc["accessors"]) - 1


def _ajouter_indices(doc: dict, tampon: bytearray, tris: list) -> int:
    plat = [i for t in tris for i in t]
    court = max(plat) < 65536
    fmt, ct = ("<%dH", 5123) if court else ("<%dI", 5125)
    vue = _ajouter_vue(doc, tampon, struct.pack(fmt % len(plat), *plat), 34963)
    doc["accessors"].append({"bufferView": vue, "componentType": ct,
                             "count": len(plat), "type": "SCALAR"})
    return len(doc["accessors"]) - 1


def _parents(nodes: list) -> dict:
    parent: dict = {}
    for i, n in enumerate(nodes):
        for c in _l(n, "children"):
            parent[c] = i
    return parent


def couper(data: bytes, noeuds, point, normale, garder: str = "deux"):
    """Coupe les nœuds `noeuds` par le plan MONDE (point, normale) et rend
    (glb, compte rendu). Chaque nœud coupé devient DEUX nœuds `<nom>_a` et
    `<nom>_b` (a : le côté vers lequel pointe la normale), ou un seul si
    `garder` ≠ "deux", portant les mêmes matériaux et textures que l'original ;
    les capuchons prennent le premier matériau de la pièce, UV à (0, 0). Le
    format du compte rendu est décrit en tête de section.

    Refus parlants (ValueError, donc 400 à la route) : GLB compressé (Draco,
    meshopt — comme `print3d.lire_glb_triangles`), normale nulle, nœud hors du
    document ou hors de la scène active, nœud sans maillage (un contenant ne
    se coupe pas : retiens ses pièces), nœud qui est un os d'un skin,
    primitive non TRIANGLES, cibles de morphing, attribut non flottant (une
    peau JOINTS/WEIGHTS), et un plan qui ne traverse AUCUNE des pièces — un
    couteau qui n'a rien coupé n'écrit pas de version.

    Le document ressort COMPACTÉ par l'extraction de la scène entière : le
    maillage d'origine, orphelin, et ses tampons ne sont pas recopiés (le
    cadre du modèle réel pèse 4 Mo), et les nœuds sont renumérotés — le compte
    rendu donne les index de la version NEUVE. C'est pourquoi la coupe ne se
    met pas en file derrière des transformations : leurs index seraient faux.
    """
    from app.services import print3d

    if garder not in _GARDER:
        raise ValueError(f"garder attend deux, a ou b — reçu {garder!r}")
    n_monde = _unitaire(normale, "normale")
    p_monde = _vecteur3(point, "point")
    doc, binc = lire_glb(data)
    for ext in doc.get("extensionsRequired") or []:
        if ext in print3d._REFUS_EXTENSIONS:
            raise ValueError(print3d._REFUS_EXTENSIONS[ext])
    nodes = _l(doc, "nodes")
    try:
        demandes = sorted({int(x) for x in (noeuds or [])})
    except (TypeError, ValueError):
        raise ValueError("noeuds attend des index de nœud entiers") from None
    if not demandes:
        raise ValueError("aucune pièce retenue — le couteau ne tranche jamais "
                         "tout le modèle par défaut")
    scenes = doc.get("scenes") or [{"nodes": []}]
    isc = int(doc.get("scene", 0))
    if not (0 <= isc < len(scenes)):
        raise ValueError(f"scène active {isc} hors du document "
                         f"({len(scenes)} scènes)")
    racines = list(scenes[isc].get("nodes") or [])
    dans_scene: set[int] = set()
    pile = list(racines)
    while pile:
        i = pile.pop()
        if i in dans_scene or not (0 <= i < len(nodes)):
            continue
        dans_scene.add(i)
        pile.extend(_l(nodes[i], "children"))
    os_: set[int] = set()
    for s in _l(doc, "skins"):
        os_.update(_l(s, "joints"))
    for i in demandes:
        if not (0 <= i < len(nodes)):
            raise ValueError(f"noeud {i} hors du document ({len(nodes)} noeuds)")
        if i not in dans_scene:
            raise ValueError(f"noeud {i} hors de la scène active")
        if nodes[i].get("mesh") is None:
            raise ValueError(f"noeud {i} sans maillage — un contenant ne se "
                             "coupe pas, retiens ses pièces")
        if i in os_:
            raise ValueError(f"noeud {i} est un os (joint d'un skin) — hors "
                             "périmètre du couteau")

    tampon = bytearray(binc)
    rapport_pieces: list = []
    produits: dict = {}            # nœud demandé → nœuds neufs (avant compactage)
    traversee = False

    # Du plus PROFOND au moins profond : le remplacement d'un enfant se fait
    # dans la liste de son parent tant que celui-ci est encore l'original.
    def profondeur(i: int) -> int:
        par, k, vus = _parents(nodes), 0, set()
        while i in par and i not in vus:
            vus.add(i)
            i = par[i]
            k += 1
        return k

    for i in sorted(demandes, key=profondeur, reverse=True):
        node = nodes[i]
        nom = node.get("name") or f"noeud_{i}"
        mesh = _l(doc, "meshes")[node["mesh"]]
        m = _mat_mul(_monde_des_ancetres(doc, i), _mat_locale(node))
        nl, cl = _plan_local(m, p_monde, n_monde)
        ln = (nl[0] ** 2 + nl[1] ** 2 + nl[2] ** 2) ** 0.5
        if ln < 1e-18:
            raise ValueError(f"noeud {i} : matrice monde dégénérée (échelle "
                             "nulle), le plan n'y a pas de sens")
        n_unit = (nl[0] / ln, nl[1] / ln, nl[2] / ln)
        if mesh.get("weights"):
            raise ValueError(f"noeud {i} ({nom}) : cibles de morphing — hors "
                             "périmètre du couteau")
        cotes = {"a": [], "b": []}          # une entrée par primitive
        segments_mesh: list = []
        total_tris = 0
        for pr in _l(mesh, "primitives"):
            if pr.get("mode", 4) != 4:
                raise ValueError(f"noeud {i} ({nom}) : primitive non TRIANGLES "
                                 f"(mode {pr.get('mode')}) — hors périmètre")
            if pr.get("targets"):
                raise ValueError(f"noeud {i} ({nom}) : cibles de morphing — "
                                 "hors périmètre du couteau")
            attrs = pr.get("attributes") or {}
            if "POSITION" not in attrs:
                raise ValueError(f"noeud {i} ({nom}) : primitive sans POSITION")
            noms = sorted(attrs, key=lambda k: (k != "POSITION", k))
            valeurs = []
            for nom_attr in noms:
                ai = attrs[nom_attr]
                acc = _l(doc, "accessors")[ai]
                if acc.get("componentType") != 5126:
                    raise ValueError(
                        f"noeud {i} ({nom}) : attribut {nom_attr} en composant "
                        f"{acc.get('componentType')} — le couteau v1 n'interpole "
                        "que des flottants (un maillage peau reste entier)")
                valeurs.append(_lire_accesseur(doc, binc, ai))
            pos = valeurs[0]
            if pr.get("indices") is not None:
                indices = [t[0] for t in _lire_accesseur(doc, binc, pr["indices"])]
            else:
                indices = list(range(len(pos)))
            total_tris += len(indices) // 3
            d = [nl[0] * p[0] + nl[1] * p[1] + nl[2] * p[2] + cl for p in pos]
            i_nrm = noms.index("NORMAL") if "NORMAL" in noms else None
            ca, cb, segs = _decouper_primitive(noms, valeurs, indices, d, i_nrm)
            largeurs = [len(valeurs[k][0]) if valeurs[k] else
                        _NB_COMPOSANTS[_l(doc, "accessors")[attrs[nm]]["type"]]
                        for k, nm in enumerate(noms)]
            cotes["a"].append((noms, ca, pr, largeurs))
            cotes["b"].append((noms, cb, pr, largeurs))
            segments_mesh.extend(segs)

        piece = {"noeud": i, "nom": nom, "triangles": total_tris}
        na = sum(len(c.tris) for _, c, _, _ in cotes["a"])
        nb = sum(len(c.tris) for _, c, _, _ in cotes["b"])
        if not na or not nb:
            entier = "a" if na else "b"
            piece["traversee"] = False
            piece["entier"] = entier
            garde = garder in ("deux", entier)
            piece["retire"] = [] if garde else [entier]
            rapport_pieces.append(piece)
            produits[i] = [i] if garde else []
            continue
        traversee = True
        piece["traversee"] = True
        boucles, ouvertes = _boucles(segments_mesh)
        piece["cotes"] = {}
        piece["retire"] = [c for c in ("a", "b") if garder not in ("deux", c)]
        neufs: list = []
        for cote in ("a", "b"):
            if garder not in ("deux", cote):
                continue
            vers = tuple(-x for x in n_unit) if cote == "a" else n_unit
            noms0, c0, _, largeurs0 = cotes[cote][0]
            i_nrm0 = noms0.index("NORMAL") if "NORMAL" in noms0 else None
            som_cap, tris_cap, bilan_cap = _capuchon(
                boucles, ouvertes, n_unit, vers, noms0, i_nrm0)
            if tris_cap:
                base = [c0.sommet_neuf([
                    x if x is not None else (0.0,) * largeurs0[k]
                    for k, x in enumerate(v)]) for v in som_cap]
                for (p, q, r) in tris_cap:
                    c0.tris.append((base[p], base[q], base[r]))
            primitives = []
            n_tris = 0
            for noms_p, cp, pr, largeurs_p in cotes[cote]:
                if not cp.tris:
                    continue
                n_tris += len(cp.tris)
                prim = {k: v for k, v in pr.items()
                        if k not in ("attributes", "indices", "targets")}
                prim["attributes"] = {
                    nom_attr: _ajouter_flottants(
                        doc, tampon, cp.cols[k], largeurs_p[k],
                        nom_attr == "POSITION")
                    for k, nom_attr in enumerate(noms_p)}
                prim["indices"] = _ajouter_indices(doc, tampon, cp.tris)
                primitives.append(prim)
            doc.setdefault("meshes", []).append(
                {"name": f"{mesh.get('name') or nom}_{cote}",
                 "primitives": primitives,
                 **({"extras": mesh["extras"]} if "extras" in mesh else {})})
            neuf = {k: v for k, v in node.items()
                    if k not in ("mesh", "children", "name", "skin")}
            neuf["name"] = f"{nom}_{cote}"
            neuf["mesh"] = len(doc["meshes"]) - 1
            nodes.append(neuf)
            j = len(nodes) - 1
            neufs.append(j)
            piece["cotes"][cote] = {"noeud": j, "nom": neuf["name"],
                                    "triangles": n_tris, "capuchon": bilan_cap}
        enfants = list(_l(node, "children"))
        if enfants:
            if neufs:
                nodes[neufs[0]]["children"] = enfants
            else:
                # tout écarté par `garder`, mais des enfants à garder : le
                # nœud reste comme simple contenant
                node.pop("mesh", None)
                neufs = [i]
        # le nœud d'origine cède sa place à ses moitiés — chez son parent, ou
        # parmi les racines de la scène
        par = _parents(nodes)
        liste = nodes[par[i]]["children"] if i in par else racines
        k = liste.index(i)
        liste[k:k + 1] = neufs
        produits[i] = neufs
        rapport_pieces.append(piece)

    if not traversee:
        raise ValueError("le plan ne traverse aucune des pièces retenues — "
                         "rien à couper")
    # les pièces entières écartées par `garder`
    for i in demandes:
        if produits.get(i) == [] and nodes[i].get("mesh") is not None:
            par = _parents(nodes)
            liste = nodes[par[i]]["children"] if i in par else racines
            if i in liste:
                liste.remove(i)
    scenes[isc]["nodes"] = racines
    doc["scenes"] = scenes
    doc["buffers"] = [{"byteLength": len(tampon)}]

    # COMPACTAGE par l'extraction de la scène entière : l'orphelin et ses
    # tampons tombent, tout est renuméroté — et la carte des nœuds traduit le
    # compte rendu dans les index de la version neuve.
    out, neuf_bin, m_node = _extraire_doc(doc, bytes(tampon), racines)
    for piece in rapport_pieces:
        for c in (piece.get("cotes") or {}).values():
            c["noeud"] = m_node.get(c["noeud"])
    rapport = {
        "plan": {"point": list(p_monde), "normale": list(n_monde),
                 "repere": "monde"},
        "garder": garder,
        "noeuds": demandes,
        "pieces": sorted(rapport_pieces, key=lambda p: p["noeud"]),
        "capuchons": {"materiau": "le premier matériau de la pièce",
                      "uv": [0, 0]},
    }
    return ecrire_glb(out, neuf_bin), rapport


def ecrire_version(job: str, data: bytes, *, operation: str,
                   detail: dict | None = None) -> dict:
    """Dépose un GLB corrigé comme NOUVELLE version d'un job, avec sa fiche.

    Jamais d'écrasement (doctrine §2.1) : le numéro vient de
    `asset3d_service.next_version`, et `mesh_report.write_report` ajoute la
    fiche au registre en gardant toutes les précédentes.
    """
    from app.services import asset3d_service, mesh_report

    d = mesh_report.job_dir(job)
    d.mkdir(parents=True, exist_ok=True)
    v = asset3d_service.next_version(job)
    nom = f"model.v{v}.glb"
    (d / nom).write_bytes(data)
    return mesh_report.write_report(
        job, nom, version=v,
        extra={"outil": "etabli", "operation": operation,
               **(detail or {})})


def adopter_meshy(task_id: str, fichier: str = "model.glb") -> str:
    """Fait entrer un maillage Meshy dans le monde des jobs `assets3d`.

    Les binaires rapatriés vivent dans `outputs/meshy3d/<id>/`, qui n'a pas de
    registre : sans adoption, une correction n'aurait nulle part où être
    versionnée. Idempotent — adopter deux fois rend le même job.
    """
    import json as _json
    import shutil
    from pathlib import Path as _Path

    from app.services import mesh_report, meshy_service

    tid = _Path(str(task_id)).name
    # `meshy3d_dir()` est la fonction CANONIQUE de ce chemin. Le reconstruire
    # à la main marcherait aujourd'hui et désynchroniserait en silence le jour
    # où la convention de stockage bougerait.
    src = meshy_service.meshy3d_dir() / tid / _Path(str(fichier)).name
    if not src.is_file():
        raise FileNotFoundError(f"meshy3d/{tid}/{_Path(fichier).name} introuvable")

    job = f"meshy_{tid}"
    d = mesh_report.job_dir(job)
    d.mkdir(parents=True, exist_ok=True)

    # Les trois écritures sont gardées SÉPARÉMENT, et c'est le point : une
    # adoption interrompue entre le binaire et sa fiche laisserait sinon un
    # job sans fiche pour toujours — le prochain appel verrait le `.glb`
    # présent et repartirait aussitôt. Ainsi, chaque appel répare ce qui
    # manque et ne réécrit rien de ce qui est déjà là.
    cible = d / "model.glb"
    if not cible.is_file():
        shutil.copy2(src, cible)          # copie par blocs, mtime préservé
    if not (d / "asset.json").is_file():
        (d / "asset.json").write_text(_json.dumps({
            "name": job, "engine": "meshy", "stage": "adopte",
            "version": 1, "adopte_de": f"meshy3d/{tid}",
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    if not (d / "report.json").is_file():
        mesh_report.write_report(job, "model.glb", version=1,
                                 extra={"outil": "etabli",
                                        "operation": "adoption",
                                        "meshy_task": tid})
    return job
