# -*- coding: utf-8 -*-
"""P9 Forge 3D — LA CHAÎNE, L'ÉLÉMENT, et les règles de l'APERÇU.

COUTURE DE DÉLESTAGE (2c, tâche 6) : forge3d.py avait franchi les 2800 lignes
et le bloc « bibliothèque » allait s'y ajouter. Ce qui vit ici est ce que
l'INSPECTEUR (`POST /node-preview`) et la CONSTRUCTION (`POST /build3d`)
PARTAGENT : la résolution des chaînes du graphe (qui gagne, qui est écarté, et
avec quelle phrase), la fabrique d'UN élément prêt pour la scène, et les règles
du GLB d'un nœud moteur SERVI. Les ROUTES restent dans forge3d.py — ce fichier
n'a pas de routeur (règle 8, patron forge3d_scene.py) et forge3d.py RÉEXPORTE
ces noms : ni les tests ni l'API ne changent d'orthographe.

CE FICHIER N'IMPORTE RIEN DE forge3d.py, et c'est la seule règle qui rend la
couture RÉELLE : un sidecar qui importe son parent n'est pas une couture, c'est
la même pièce en deux fichiers. Les deux primitives qui ne pouvaient pas
traverser sont donc INJECTÉES en paramètres NOMMÉS (`element_local(...,
ouvre_png=, habille=)`) — `_open_png` sert aussi trois routes de forge3d.py, et
`_habille` a besoin de `tile_maps`, qui a besoin de `_num`, deux fondations de
là-bas ; et le job comme le dossier d'un nœud sont DONNÉS par l'appelant
(`glb_servi_path(job, node_dir, nid)`). Ici vivent les RÈGLES et leurs phrases,
là-bas l'accès au magasin. Paramètres NOMMÉS et non positionnels : deux
callables interchangeables au même rang, c'est exactement le swap silencieux
que cette couture existe pour rendre impossible.

PAS « PUR » au sens de forge3d_scene.py, qui ne connaît aucun code de statut :
celui-ci lève des refus NOMMÉS avec le leur — et c'est précisément ce qu'il
faut garder ensemble. Séparer la phrase (« source surnumeraire… ») de la règle
qui la produit est le défaut que cette couture corrige : le grep avait déjà
raté une COPIE de cette phrase, au découpage de littéral près (le résolveur
écrivait « deja retenu », l'aperçu « deja » + « retenu »).
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException

from .forge3d_scene import quad_mesh, relief_mesh, trs_de_face

_PROC_KINDS = ("plane", "relief", "mesh3d")
_CHAIN_MAX = 4        # material + transform + assemble, et une marge : la
                       # boucle de `_chaine_aval` ne suppose PAS le graphe
                       # acyclique (`clean_graph` ne coupe pas les cycles — un
                       # aller-retour d'arêtes ferait tourner un `while` nu).


# ── LES DEUX PHRASES D'AVEU DE LA « PREMIÈRE ARÊTE GAGNANTE » ───────────────
# Elles vivent avec les règles qui les produisent, et NULLE PART AILLEURS
# (N1, re-revue de la tâche 1 : elles étaient recopiées entre le résolveur et
# l'aperçu, et le découpage de littéral suffisait à faire rater la copie au
# grep). Les deux fonctions ci-dessous MUTENT `ignores` — c'est leur contrat :
# un nœud écarté sans phrase serait un mensonge par omission, et `artifact@1`
# promet le contraire.

def _source_gagnante(nid: str, incoming: dict, nodes_by_id: dict,
                     ignores: list) -> dict | None:
    """La couche SOURCE retenue pour un traitement — la PREMIÈRE arête
    `layer -> {nid}` gagne — et les autres AVOUÉES. Rend `None` quand aucune
    couche n'entre : l'appelant décide de ce que « pas de source » veut dire
    chez lui (le résolveur l'AVOUE et passe au suivant, l'aperçu REFUSE avec
    une phrase qui dit quoi câbler), mais la perte des surnuméraires, elle, se
    dit d'UNE seule façon."""
    sources = [nodes_by_id[fid] for fid in incoming.get(nid, [])
               if fid in nodes_by_id and nodes_by_id[fid]["kind"] == "layer"]
    if not sources:
        return None
    src = sources[0]
    for autre in sources[1:]:
        ignores.append({
            "node": autre["id"],
            "why": f"source surnumeraire pour {nid} : {src['id']} deja "
                   "retenu (premiere arete gagnante)"})
    return src


def _chaine_aval(nid: str, nodes_by_id: dict, outgoing: dict,
                 ignores: list) -> tuple:
    """La chaîne AVAL d'un traitement : `material` puis `transform` (0 ou 1 de
    chacun, dans N'IMPORTE QUEL ordre), jusqu'à `assemble`. Rend
    `(noeud material|None, noeud transform|None, atteint l'assemblage)` et
    AVOUE dans `ignores` les maillons PASSÉS.

    LE MODIFICATEUR PASSE AVANT L'ASSEMBLAGE quand les deux partent du même
    nœud : un graphe câblé à la fois `-> material` et `-> assemble` est
    ambigu, et prendre l'assemblage y jetterait la matière EN SILENCE. Deux
    matières (ou deux transforms) sur une même chaîne : refus — la seconde ne
    peut pas gagner sans que la première mente.

    L'ÉVENTAIL DE FRÈRES EST AVOUÉ, pas jeté en douce : deux arêtes parallèles
    vers deux matières, c'est la MÊME perte qu'une source surnuméraire à
    l'entrée (première arête gagnante), et l'entrée, elle, l'avoue depuis la
    tâche 4. L'écran ne produit pas cette topologie, mais l'API brute est
    ouverte à qui la poste — et le contrat `artifact@1` promet de nommer tout
    ce qui a été écarté."""
    mat = trs = None
    cur = nid

    def avoue(freres, retenu):
        for f in freres:
            ignores.append({
                "node": f["id"],
                "why": f"maillon surnumeraire dans la chaine de {nid} : "
                       f"{retenu} deja retenu (premiere arete gagnante)"})

    for _ in range(_CHAIN_MAX):
        suivants = [nodes_by_id[t] for t in outgoing.get(cur, [])
                    if t in nodes_by_id]
        maillons = [s for s in suivants
                    if s["kind"] in ("material", "transform")]
        if not maillons:
            return (mat, trs,
                    any(s["kind"] == "assemble" for s in suivants))
        nxt, freres = maillons[0], maillons[1:]
        avoue(freres, nxt["id"])
        if nxt["kind"] == "material":
            if mat is not None:
                return mat, trs, False
            mat = nxt
        else:
            if trs is not None:
                return mat, trs, False
            trs = nxt
        cur = nxt["id"]
    return mat, trs, False


def _resolve_graph_elements(graph: dict) -> tuple[list[dict], list[dict]]:
    """Chaque chaîne layer->(plane|relief|mesh3d)->[material]->[transform]->
    assemble devient UN candidat `{proc, layer, mat, trs}`, dans l'ORDRE DES
    NŒUDS du graphe (pas l'ordre des edges, pas l'ordre de résolution). Aucune
    E/S ici : c'est une garde, elle tourne AVANT tout travail lourd — le
    plafond `MAX_GRAPH_ELEMENTS` s'applique sur ce qu'elle rend, moteurs
    compris.

    Rend AUSSI `ignored` (REQUIS, revue) : le contrat `artifact@1` s'est figé à
    la tâche 4 — taire un nœud écarté serait un mensonge par omission. Quatre
    motifs, chacun nommé : une source SURNUMÉRAIRE (la première arête entrante
    gagne, patron déjà en vigueur — les suivantes sont d'authentiques pertes,
    pas un bug) ; un traitement SANS AUCUNE source ; un traitement bien sourcé
    mais dont la chaîne NE REJOINT PAS d'assemble (chaîne cassée, deux matières
    empilées, cycle) ; et, 2b, une MATIÈRE chaînée sur un `mesh3d` — le GLB du
    moteur porte déjà ses propres matériaux, la nôtre ne s'y substituerait pas,
    elle s'y ajouterait sans rien habiller."""
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    incoming: dict[str, list[str]] = {}
    outgoing: dict[str, list[str]] = {}
    for e in graph["edges"]:
        incoming.setdefault(e["to"], []).append(e["from"])
        outgoing.setdefault(e["from"], []).append(e["to"])
    candidats: list[dict] = []
    ignores: list[dict] = []
    for n in graph["nodes"]:
        if n["kind"] not in _PROC_KINDS:
            # LES NŒUDS `export` (2c) ET LEURS ARÊTES DEPUIS `artifact` SONT
            # IGNORÉS ICI *SANS ENTRÉE `ignored`*, et c'est une décision, pas
            # un oubli : ce sont des POINTS DE TÉLÉCHARGEMENT — ils n'éteignent
            # rien, le bordereau reste entier. `ignored` nomme ce qui a été
            # PERDU (une source surnuméraire, une chaîne cassée, une matière
            # qui n'habillera rien) ; un export ne perd rien, il DÉSIGNE une
            # sortie que `post_build3d` écrit de toute façon. L'y faire figurer
            # apprendrait à l'utilisateur à ignorer son propre bordereau —
            # exactement ce que le contrat `artifact@1` existe pour empêcher.
            # (Même silence, pour la même raison, pour `assemble` et
            # `artifact` : ce sont des étages, pas des éléments.)
            continue
        src = _source_gagnante(n["id"], incoming, nodes_by_id, ignores)
        if src is None:
            ignores.append({
                "node": n["id"],
                "why": "traitement sans couche source (aucune arete layer "
                       "entrante)"})
            continue
        mat, trs, relie_assemble = _chaine_aval(
            n["id"], nodes_by_id, outgoing, ignores)
        if not relie_assemble:
            ignores.append({"node": n["id"],
                            "why": "traitement non relie a un assemble"})
            continue
        if mat is not None and n["kind"] == "mesh3d":
            ignores.append({
                "node": mat["id"],
                "why": "matiere ignoree : le GLB du moteur porte deja ses "
                       "materiaux (chaine une matiere sur un plan ou un "
                       "relief)"})
            mat = None
        candidats.append({"proc": n, "layer": src, "mat": mat, "trs": trs})
    return candidats, ignores


def _trs_dict(node) -> dict | None:
    """Le nœud `transform` du graphe, traduit pour le writer (millimètres).
    Absent = None, et le writer garde alors le `z_mm` de la 2a."""
    if not isinstance(node, dict):
        return None
    return {"translate": [node["x_mm"], node["y_mm"], node["z_mm"]],
            "rotate_deg": node["rot_deg"], "scale": node["scale"]}


def _layer_filename(layer_node: dict, card_label: str) -> str:
    """Le nom de fichier ESTAMPILLÉ que `post_layers` a écrit (phase 1) pour
    cette source : la couche composite si `composite: true`, sinon le rôle."""
    side = layer_node["side"]
    if layer_node.get("composite"):
        return f"composite_{card_label}_{side}.png"
    return f"{layer_node['role']}_{card_label}_{side}.png"


def _geom_element(g) -> tuple:
    """LES COTES D'UN ÉLÉMENT, dérivées UNE FOIS de la géométrie du deck :
    `(w_mm, h_mm, bleed_px, canvas_px, uv_window)`.

    N2 (re-revue de la tâche 1) : ces cinq valeurs étaient dérivées DEUX FOIS
    — une dans `post_build3d`, une dans `post_node_preview` — puis passées à
    `_element_local` en QUATRE paramètres positionnels dont trois tuples de
    même forme. Un `bleed_px` et un `canvas_px` échangés au point d'appel
    n'aurait levé nulle part : la fenêtre UV serait simplement partie de
    travers, et la seule preuve aurait été un test d'image. La dérivation est
    donc INTERNE à l'élément, et le point d'appel ne passe plus que `g`.

    `bleed_px` vient de `g.bleed_off_px`, DÉJÀ la conversion canonique
    (canvas_px - trim_px)/2 de contract.py:geom — pas une deuxième dérivation
    locale (le domaine a déjà mesuré la dérive d'un recalcul redondant : voir
    `_dpi_to_ppm` dans forge3d.py). La fenêtre UV, elle, réconcilie la TOILE
    (les PNG, fond perdu compris) et la COUPE (le maillage) : sans elle, le
    fond perdu s'affiche sur l'artefact avec ~2,5 % de distorsion anisotrope
    (63/69 != 88/94), mesuré en revue finale de la 2a."""
    w_mm, h_mm = g.trim_mm
    bleed_px = (round(g.bleed_off_px[0]), round(g.bleed_off_px[1]))
    u0, v0 = bleed_px[0] / g.canvas_px[0], bleed_px[1] / g.canvas_px[1]
    return w_mm, h_mm, bleed_px, g.canvas_px, (u0, v0, 1.0 - u0, 1.0 - v0)


def element_local(out: Path, proc: dict, layer: dict, nom_el: str,
                  mat_n, trs_n, card_label: str, g, ignores: list, *,
                  ouvre_png, habille) -> dict:
    """UN élément LOCAL (`plane`/`relief`) prêt pour l'assemblage : lecture
    de la couche, géométrie (quad ou relief, cropée à la coupe), habillage
    matière/finition, TRS — COMMUNS (I2, revue 2c) à `build3d` (la boucle de
    son `work()`) et à l'inspecteur (`post_node_preview`) : mêmes ~40
    lignes, UNE fois, même doctrine que `_open_png` (déjà UNIQUE pour la
    même raison — voir sa docstring). `ignores` est MUTÉ : `habille` y
    ajoute ses motifs (matière introuvable, finition ignorée).

    `ouvre_png` et `habille` sont INJECTÉS, nommés (voir l'en-tête du
    fichier) : ce sont les deux seules primitives de forge3d.py que ce
    module ne peut pas importer sans devenir une fausse couture.

    LE CÔTÉ DE LA COUCHE SOURCE (2d) ne change RIEN à la géométrie : un
    élément de verso est construit dans l'ESPACE RECTO — même quad, même
    relief, même fit, mêmes UV, même TANGENT local — puis POSÉ par un TRS de
    carte retournée (`trs_de_face`). Zéro maillage de plus, zéro borne
    déplacée : c'est la PLACE qui porte le verso, jamais les octets."""
    w_mm, h_mm, bleed_px, canvas_px, uv_window = _geom_element(g)
    fname = _layer_filename(layer, card_label)
    p = out / fname
    # MOTIF 2/2 (distinct du "graphe vide") : le graphe est bien câblé, mais
    # LA couche qu'il vise n'a jamais été livrée pour cette carte/ce côté —
    # exporte-les d'abord (phase 1).
    if not p.is_file():
        raise HTTPException(
            409, f"exporte les couches d'abord : {fname} absent "
                 f"(POST /layers)")
    raw = p.read_bytes()
    im = ouvre_png(raw, fname)
    if proc["kind"] == "plane":
        mesh = quad_mesh(w_mm, h_mm, uv_window=uv_window)
        el = {"name": nom_el, "mesh": mesh, "png": raw,
              "alpha": True, "z_mm": proc["depth_mm"]}
    else:
        # la géométrie/silhouette du relief ne doit voir QUE la coupe —
        # cropper la TOILE au rectangle de coupe (mêmes bornes que
        # `bleed_px`) AVANT l'échantillonnage, sinon le fond perdu pèse sur
        # la hauteur ET la silhouette.
        cx0, cy0 = bleed_px
        cx1 = canvas_px[0] - cx0
        cy1 = canvas_px[1] - cy0
        alpha_img = im.getchannel("A").crop((cx0, cy0, cx1, cy1))
        mesh = relief_mesh(alpha_img, w_mm, h_mm, proc["depth_mm"],
                           proc["base_mm"], proc["grid"], uv_window=uv_window)
        el = {"name": nom_el, "mesh": mesh, "png": raw,
              "alpha": False, "z_mm": 0.0}
    habille(el, mat_n, w_mm, h_mm, ignores)
    trs = _trs_dict(trs_n)
    if layer["side"] == "back":
        # UN ÉLÉMENT DE VERSO PORTE TOUJOURS UN TRS, même sans nœud
        # `transform` : le retournement EST un placement. Sans nœud, l'écart de
        # pile de la 2a (`z_mm`, que `_node_trs` aurait écrit tel quel) devient
        # la translation d'ESPACE RECTO qu'on retourne — une seule règle, la
        # même des deux côtés du `if`, au lieu d'un chemin « sans transform »
        # qui divergerait en silence.
        trs = trs_de_face(
            trs if trs is not None
            else {"translate": [0.0, 0.0, float(el["z_mm"])],
                  "rotate_deg": 0.0, "scale": 1.0},
            w_mm, "back")
    if trs is not None:
        el["trs"] = trs
    return el


# ── LE GLB D'UN NŒUD MOTEUR SERVI — LES RÈGLES, PAS LE MAGASIN ─────────────

def _glb_servi_path(job, node_dir: Path, nid: str) -> Path:
    """Le CHEMIN du GLB d'un nœud mesh3d SERVI — LA SEULE SOURCE (I2, revue
    2c) des trois refus partagés par `_element_externe` (fusion, build3d) et
    `_apercu_mesh3d` (inspecteur, node-preview) : job non servi, nom de
    fichier invalide, fichier disparu du nœud. Chaque appelant garde SES
    gates PROPRES au-delà : `_element_externe` vérifie ENCORE la carte-source
    et `MAX_EXT_GLB_BYTES` (une fusion en mémoire) ; `_apercu_mesh3d` vérifie
    `MAX_APERCU_GLB_BYTES` (un clic dans l'inspecteur — deux dangers
    différents, deux bornes différentes, voir CF2). N'OUVRE PAS le fichier :
    ni celle-ci, ni ses appelants n'ont besoin des octets pour ces trois
    refus.

    `job` et `node_dir` sont DONNÉS (couture de délestage) : la lecture du
    `job.json` et le confinement du dossier appartiennent au magasin, qui vit
    dans forge3d.py ; ce qui vit ICI, ce sont les trois refus et leurs
    phrases. `job` peut valoir `None` — c'est le premier cas."""
    if not isinstance(job, dict) or job.get("status") != "served":
        raise HTTPException(
            409, f"le noeud {nid} n'a pas servi son GLB — lance-le d'abord "
                 f"(POST mesh3d/{nid})")
    fichiers = job.get("files")
    nom_glb = (fichiers or {}).get("glb") if isinstance(fichiers, dict) else None
    nom_glb = str(nom_glb or "model.glb")
    if not re.match(r"^[A-Za-z0-9._-]{1,90}$", nom_glb) or set(nom_glb) == {"."}:
        raise HTTPException(
            409, f"le noeud {nid} annonce un fichier de nom invalide "
                 f"({nom_glb!r}) - relance le noeud")
    p_glb = node_dir / nom_glb
    if not p_glb.is_file():
        raise HTTPException(
            409, f"le noeud {nid} n'a pas servi son GLB — {nom_glb} a disparu "
                 f"du noeud, relance-le")
    return p_glb


def _borne_apercu_glb(job, p_glb: Path, nid: str, borne: int) -> Path:
    """La BORNE DE POIDS de l'inspecteur, PROPRE à lui (`MAX_APERCU_GLB_BYTES`
    — PAS `MAX_EXT_GLB_BYTES`, qui borne une fusion en mémoire, un danger
    différent) : mesurée comme `_element_externe` la mesure, sur le PLUS GRAND
    du chiffre annoncé par le job et du `stat` du disque, SANS ouvrir le
    fichier — `FileResponse` le servira en flux au moment de l'envoi, un clic
    dans l'inspecteur ne doit pas charger 32 Mio en RAM avant de commencer à
    répondre."""
    taille = job.get("bytes")
    if isinstance(taille, bool) or not isinstance(taille, (int, float)) \
            or taille < 0:
        taille = 0
    taille = max(int(taille), p_glb.stat().st_size)
    if taille > borne:
        raise HTTPException(
            409, f"le GLB du noeud {nid} est trop lourd pour l'inspecteur "
                 f"({int(taille)} o, maximum {borne} o) : "
                 f"construis l'artefact pour le voir dans le noeud artefact")
    return p_glb


# ── LE SOUS-GRAPHE SYNTHÉTIQUE DE L'APERÇU D'UN NŒUD ───────────────────────
# Identifiant SYNTHETIQUE, GARANTI SANS COLLISION avec un id de graphe reel
# — HORS ALPHABET, pas seulement long (M1/CF1, revue 2c) : un espace en tete
# n'est PAS dans `[A-Za-z0-9._-]`, le seul charset que `clean_graph` peut
# JAMAIS produire (son `re.sub` REMPLACE tout caractere hors de ce charset
# par "_" — il ne peut donc jamais EMETTRE un espace, ":" ou une parenthese).
# L'argument arithmetique precedent (« un id interne de plus de 24
# caracteres ne peut pas collisionner ») etait FAUX au moment ou il a ete
# ecrit : le suffixe anti-collision de `clean_graph` pouvait depasser 24
# caracteres — un argument STRUCTUREL (l'alphabet, pas la longueur) reste
# vrai meme si `clean_graph` change encore demain.
# Pas de pendant `_ART`: verifie (M2) — `_resolve_graph_elements` ne lit
# JAMAIS le noeud `artifact` (il s'arrete a `assemble`, voir `_chaine_aval`),
# et le nom du GLB d'apercu est un litteral ("apercu") au point d'appel : un
# noeud artefact synthetique n'aurait aucun lecteur, il n'existe plus.
_PREVIEW_ASM_ID = " apercu:assemble (synthetique)"


def _sous_graphe_apercu(graph: dict, nid: str, node: dict, grid_max: int,
                        ignored: list) -> dict:
    """LA CHAÎNE D'UN SEUL NŒUD `plane`/`relief`, résolue comme `build3d` la
    résoudrait — rend le candidat `{proc, layer, mat, trs}`.

    Le sous-graphe est SYNTHETIQUE : {sa couche source (première arête
    gagnante, les autres AVOUÉES), le traitement lui-même (grille PLAFONNÉE
    avant résolution — l'aperçu privilégie la vitesse, le vrai grid ne joue
    qu'au build), sa matière / son placement s'il en a (via `_chaine_aval` sur
    le graphe RÉEL, mêmes maillons surnuméraires AVOUÉS), et un `assemble`
    FABRIQUÉ} — passé au MÊME résolveur que build3d. D'où l'assemble
    synthétique : l'aperçu montre l'option DÉJÀ choisie sur ce nœud, même si
    sa chaîne ne rejoint pas encore un assemble réel.

    UN SEUL nœud synthétique (M2, revue) : `_resolve_graph_elements` ne
    regarde jamais au-delà de l'assemble (voir `_chaine_aval`) — un artifact
    synthétique n'aurait aucun lecteur.

    I1 (revue) : AUCUN aveu ne s'évapore — tout ce que cette résolution écarte
    entre dans `ignored`, que l'appelant joint aux extras du GLB rendu."""
    incoming: dict[str, list[str]] = {}
    outgoing: dict[str, list[str]] = {}
    for e in graph["edges"]:
        incoming.setdefault(e["to"], []).append(e["from"])
        outgoing.setdefault(e["from"], []).append(e["to"])
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    src = _source_gagnante(nid, incoming, nodes_by_id, ignored)
    if src is None:
        raise HTTPException(
            400, f"noeud {nid} sans couche source (relie une couche : "
                 f"layer -> {nid})")
    mat_n, trs_n, _relie = _chaine_aval(nid, nodes_by_id, outgoing, ignored)
    proc = dict(node)
    if proc["kind"] == "relief":
        proc["grid"] = min(proc["grid"], grid_max)
    sub_nodes = [src, proc]
    sub_edges = [{"from": src["id"], "to": proc["id"]}]
    cur = proc["id"]
    for maillon in (mat_n, trs_n):
        if maillon is not None:
            sub_nodes.append(maillon)
            sub_edges.append({"from": cur, "to": maillon["id"]})
            cur = maillon["id"]
    sub_nodes.append({"id": _PREVIEW_ASM_ID, "kind": "assemble"})
    sub_edges.append({"from": cur, "to": _PREVIEW_ASM_ID})
    candidats, sub_ignores = _resolve_graph_elements(
        {"nodes": sub_nodes, "edges": sub_edges})
    ignored.extend(sub_ignores)
    if not candidats:
        # NE DEVRAIT JAMAIS ARRIVER (le sous-graphe ci-dessus est cable a la
        # main, une seule chaine possible) — doctrine jamais-500 : un refus
        # nomme plutot qu'un IndexError si un futur changement de
        # `_resolve_graph_elements` invalidait cette hypothese.
        raise HTTPException(
            400, f"noeud {nid} non prévisualisable : chaine irresoluble")
    return candidats[0]
