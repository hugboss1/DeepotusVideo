# -*- coding: utf-8 -*-
"""Plan-studio T6 (tache #69 du suivi, 02/10/2026) — valider un graphe Studio IMPORTE, contre le registre des noeuds.

Le registre (app/assets/studio_nodes.json) est extrait du bundle par scripts/qa/dump_studio_registry.py : le bundle
reste la source, ce JSON en est le miroir cote serveur (un banc surveille la derive).

`valider` ne devine jamais : un type inconnu, un identifiant en double, un cycle ou deux noeuds Render sont des REFUS
qui nomment le fautif (le canevas du Studio plante sur un type inconnu, et son tri topologique avale un cycle sans le
dire). Une arete branchee sur un noeud ou un port inexistant est JETEE et dite — le graphe reste ouvrable. Les sources
absentes de cette machine (image d'un noeud Image, rendu d'un ExistingRender ou d'un UGC) remontent a part, pour que
l'ecran les liste au lieu d'ouvrir un graphe muet. Les autres `filename` (voix, musique, images generees) ne sont pas
verifies : ils sont regeneres ou rechoisis dans leur noeud.

Deux formes sont acceptees : le graphe NU ({name, nodes, edges}, ce qu'ecrit l'export du Studio) et l'enregistrement
du magasin ({id, name, graph, updated_at}). Le graphe rendu n'a jamais d'`id` : il s'ouvre NON enregistre.
"""
import json
from functools import lru_cache
from pathlib import Path

REGISTRE = Path(__file__).resolve().parent.parent / "assets" / "studio_nodes.json"
MAX_NOEUDS = 200
MAX_ARETES = 500
# (type de noeud, champ des props, magasin ou la source doit exister)
SOURCES = (("Image", "filename", "images"), ("ExistingRender", "jobId", "jobs"), ("Upload", "jobId", "jobs"))


@lru_cache(maxsize=1)
def registre() -> dict:
    return json.loads(REGISTRE.read_bytes().decode("utf-8"))["types"]


def _nombre(v, defaut=0.0) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else defaut


def deballer(doc):
    """Le graphe d'un enregistrement du magasin ({graph: {...}}), ou le document lui-meme. Le nom de l'enregistrement
    (celui de la liste « Ouvrir un graphe ») l'emporte sur celui du graphe."""
    if isinstance(doc, dict) and "nodes" not in doc and isinstance(doc.get("graph"), dict):
        g = dict(doc["graph"])
        if isinstance(doc.get("name"), str) and doc["name"].strip():
            g["name"] = doc["name"]
        return g
    return doc


def valider(graphe, images: set | None = None, jobs: set | None = None):
    """Rend (graphe_normalise, avertissements, sources_manquantes).

    `images` / `jobs` : ce qui est disponible sur cette machine. None = on ne verifie pas ; un ensemble VIDE veut
    dire « rien n'est disponible ».
    """
    reg = registre()
    graphe = deballer(graphe)
    if not isinstance(graphe, dict):
        raise ValueError("Le fichier ne contient pas un graphe Studio (objet JSON attendu).")
    noeuds = graphe.get("nodes")
    aretes = graphe.get("edges")
    if aretes is None:
        aretes = []
    if not isinstance(noeuds, list) or not noeuds:
        raise ValueError("Le graphe n'a aucun nœud (champ « nodes »).")
    if not isinstance(aretes, list):
        raise ValueError("Le champ « edges » n'est pas une liste.")
    if len(noeuds) > MAX_NOEUDS:
        raise ValueError(f"{len(noeuds)} nœuds : au-delà de {MAX_NOEUDS}, ce n'est plus un graphe Studio.")
    if len(aretes) > MAX_ARETES:
        raise ValueError(f"{len(aretes)} arêtes : au-delà de {MAX_ARETES}, ce n'est plus un graphe Studio.")

    types, propres, avert = {}, [], []
    for n in noeuds:
        if not isinstance(n, dict):
            raise ValueError("Un nœud n'est pas un objet JSON.")
        nid = str(n.get("id") or "").strip()
        typ = str(n.get("type") or "").strip()
        if not nid:
            raise ValueError(f"Un nœud ({typ or 'sans type'}) n'a pas d'identifiant (« id »).")
        if nid in types:
            raise ValueError(f"Identifiant de nœud en double : {nid}.")
        if typ not in reg:
            raise ValueError(f"Type de nœud inconnu : {typ or '(vide)'} (nœud {nid}). "
                             f"Le registre de cette version en compte {len(reg)}.")
        types[nid] = typ
        props = n.get("props")
        # les props inconnues sont GARDEES : ts(), cote ecran, fusionne les defauts du registre par-dessous, donc un
        # graphe ecrit par une version voisine reste ouvrable.
        propres.append({"id": nid, "type": typ, "x": _nombre(n.get("x")), "y": _nombre(n.get("y")),
                        "props": dict(props) if isinstance(props, dict) else {}})
    rendus = [n["id"] for n in propres if n["type"] == "Render"]
    if len(rendus) > 1:
        raise ValueError(f"{len(rendus)} nœuds Render ({', '.join(rendus)}) : le Studio n'en compile qu'un.")

    gardees, vues = [], set()
    for e in aretes:
        if not isinstance(e, dict):
            avert.append("Une arête n'est pas un objet JSON : jetée.")
            continue
        a, b = str(e.get("from") or ""), str(e.get("to") or "")
        pa, pb = str(e.get("fromPort") or ""), str(e.get("toPort") or "")
        if a not in types or b not in types:
            avert.append(f"Arête vers un nœud absent ({a or '?'} → {b or '?'}) : jetée.")
            continue
        if pa not in reg[types[a]]["out"]:
            avert.append(f"Port de sortie « {pa} » inconnu sur {types[a]} ({a}) : arête jetée.")
            continue
        if pb not in reg[types[b]]["in"]:
            avert.append(f"Port d'entrée « {pb} » inconnu sur {types[b]} ({b}) : arête jetée.")
            continue
        eid = str(e.get("id") or "").strip() or f"e_{a}_{b}_{pb}"
        if eid in vues:
            eid = f"{eid}_{len(gardees)}"
        vues.add(eid)
        gardees.append({"id": eid, "from": a, "fromPort": pa, "to": b, "toPort": pb})

    degre = {nid: 0 for nid in types}
    for e in gardees:
        degre[e["to"]] += 1
    file = [nid for nid, d in degre.items() if not d]
    ordre = []
    while file:
        cur = file.pop(0)
        ordre.append(cur)
        for e in gardees:
            if e["from"] == cur:
                degre[e["to"]] -= 1
                if degre[e["to"]] == 0:
                    file.append(e["to"])
    if len(ordre) != len(propres):
        bloques = sorted(set(types) - set(ordre))
        raise ValueError("Le graphe contient un cycle (" + ", ".join(bloques) + ") : "
                         "le Studio n'exécute que des graphes sans boucle.")

    manques = []
    for n in propres:
        for typ, champ, magasin in SOURCES:
            if n["type"] != typ:
                continue
            v = n["props"].get(champ)
            if not isinstance(v, str) or not v:
                continue
            dispo = images if magasin == "images" else jobs
            if dispo is not None and v not in dispo:
                manques.append({"node_id": n["id"], "type": n["type"], "champ": champ, "valeur": v,
                                "magasin": magasin})

    nom = str(graphe.get("name") or "").strip()[:120] or "Graphe importé"
    return {"name": nom, "nodes": propres, "edges": gardees}, avert, manques
