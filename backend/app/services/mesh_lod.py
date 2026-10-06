# -*- coding: utf-8 -*-
"""LOD en chaîne, perte mesurée, budget par usage — T105, plan-moteurs-3d T3 (R10e P2).

Trois choses que `mesh_optimize` ne fait pas :
  1. une CHAÎNE (LOD0 = la source, puis LOD1, LOD2…) écrite ensemble, nommée pour le moteur et livrée en une
     archive ;
  2. la PERTE, mesurée par niveau : IoU des trois silhouettes contre le LOD0 (le rasteriseur de `mesh_report`) ET
     écart de la signature de normales — parce qu'une bosse aplatie garde sa silhouette et perd ses normales ;
  3. un BUDGET par usage, proposé et motivé, jamais imposé.

Tout est local et gratuit. `gltfpack 1.2 -h` relu le 06/10/2026 : `-si R` (ratio), `-se E` (erreur max, 1 % par
défaut — d'où la seconde passe `-sa` quand la cible n'est pas atteinte), `-kn`, `-km`, `-noq`, `-r rapport.json`.
Pas de numpy : la signature de normales est un histogramme sphérique en Python pur, bornée par MAX_TRIS_SIGNATURE.

La source est le GLB COURANT du registre (une version de l'Établi se décline aussi en LOD), jamais modifiée. Le
dossier `lod/` est DÉRIVÉ (recalculable), pas une version au sens de la doctrine §2.1 : une chaîne neuve le remplace
en entier — sinon un LOD3 de la chaîne précédente survivrait à côté d'un LOD1 de la nouvelle. Les refus (niveaux,
usage) passent AVANT tout effacement : une chaîne refusée ne détruit pas la précédente.
"""
from __future__ import annotations

import io
import json
import math
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Budgets par usage. Les nombres sont des CHOIX de départ, pas des mesures : ils sont éditables par `niveaux`, et le
# banc de référence (plan-moteurs-3d T8) les corrigera avec des chiffres du terrain. Ce qui est mesuré ici, c'est la
# PERTE qu'ils coûtent — affichée à côté de chacun.
BUDGETS = {
    "mobile": {
        "label": "Mobile / WebGL",
        "niveaux": [10_000, 4_000, 1_500],
        "pourquoi": "Un personnage de premier plan sur téléphone tient sous 10 000 triangles ; les deux niveaux "
                    "suivants servent aux silhouettes de fond.",
    },
    "pc": {
        "label": "PC / console",
        "niveaux": [60_000, 20_000, 6_000],
        "pourquoi": "Le LOD0 garde le détail du gros plan ; LOD1 tient la distance moyenne, LOD2 le décor lointain.",
    },
    "impression": {
        "label": "Impression 3D",
        "niveaux": [200_000],
        "pourquoi": "L'impression ne fait PAS de LOD : un seul palier, assez haut pour que la buse ne voie pas les "
                    "facettes, assez bas pour que le slicer ne rame pas.",
    },
}
MAX_NIVEAUX = 8            # docs.unity3d.com : 8 LOD au plus dans un LOD Group (LOD0 compris)
MAX_TRIS_SIGNATURE = 400_000
SIG_BINS = 8
SIL_PX = 256               # 3 vues x N niveaux : 65 536 px par IoU, tenable
_VUES = ("face", "profil", "dessus")


def budgets() -> list[dict]:
    """Les budgets, pour l'écran et pour la route."""
    return [{"id": k, **v} for k, v in BUDGETS.items()]


def _job_dir(job):
    from app.services import mesh_report
    return mesh_report.job_dir(job)


# ── nommage moteur ───────────────────────────────────────────────────────────

def _bases(data: bytes) -> list[str]:
    """Les noms de mesh de la SOURCE, sans suffixe _LOD : gltfpack ne les conserve pas (`-kn` garde les NŒUDS, pas
    les meshes — mesuré le 06/10 : un LOD1 sortait « mesh_0 »), or c'est le nom de mesh qu'Unity lit."""
    from app.services import mesh_edit
    doc, _ = mesh_edit.lire_glb(data)
    return [(m.get("name") or f"mesh_{i}").split("_LOD")[0] for i, m in enumerate(doc.get("meshes") or [])]


def _renommer(data: bytes, n: int, bases: list[str] | None = None) -> bytes:
    """Suffixe `_LOD{n}` sur chaque mesh ET sur les nœuds qui en portent un.

    docs.unity3d.com/Manual/lod-group-configure.html (relue le 03/09/2026) : « Add the suffix _LODX to the name of
    each mesh … ExampleMeshName_LOD0 » — le guide exporte en .fbx, donc en GLB l'import Unity ne fabrique pas
    forcément le LOD Group tout seul. Ce qu'on promet est le NOM, pas le composant. Godot (node_type_customization :
    `-col`, `-convcol`, `-rigid`, `-noimp`, `-loop`…) ne documente AUCUN suffixe LOD. Le LISEZMOI le dit aux deux.
    """
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(data)
    suffixe = f"_LOD{int(n)}"
    for i, m in enumerate(doc.get("meshes") or []):
        if bases and i < len(bases):
            base = bases[i]
        elif bases and len(bases) == 1:            # gltfpack a pu fusionner : un seul nom source pour tous
            base = bases[0]
        else:
            base = (m.get("name") or f"mesh_{i}").split("_LOD")[0]
        m["name"] = base + suffixe
    for i, nd in enumerate(doc.get("nodes") or []):
        if "mesh" in nd:
            nd["name"] = (nd.get("name") or f"node_{i}").split("_LOD")[0] + suffixe
    return mesh_edit.ecrire_glb(doc, binc)


# ── la perte : silhouettes + normales ────────────────────────────────────────

def signature_normales(tris, bins: int = SIG_BINS) -> list[float]:
    """Histogramme des normales de face PONDÉRÉ PAR L'AIRE, en (cos θ, φ).

    Rendu normalisé (somme = 1), donc comparable entre deux maillages de comptes très différents : c'est une
    fraction d'aire par direction. Les triangles d'aire nulle n'ont pas de normale et sont ignorés — les compter
    fabriquerait une direction arbitraire (même leçon que les dégénérés de `mesh_report.geometry`)."""
    largeur = 2 * int(bins)
    h = [0.0] * (int(bins) * largeur)
    total = 0.0
    for t in tris:
        ux, uy, uz = (t[1][0] - t[0][0], t[1][1] - t[0][1], t[1][2] - t[0][2])
        vx, vy, vz = (t[2][0] - t[0][0], t[2][1] - t[0][1], t[2][2] - t[0][2])
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        norme = math.sqrt(nx * nx + ny * ny + nz * nz)
        if norme <= 1e-12:
            continue
        aire = norme * 0.5
        i = min(int(bins) - 1, int((nz / norme + 1.0) * 0.5 * int(bins)))
        phi = math.atan2(ny, nx)
        j = min(largeur - 1, int((phi + math.pi) / (2 * math.pi) * largeur))
        h[i * largeur + j] += aire
        total += aire
    if total <= 0:
        raise ValueError("maillage sans aire : signature de normales impossible")
    return [round(v / total, 6) for v in h]


def ecart_normales(a, b) -> float:
    """Distance en variation totale entre deux signatures : 0 = identiques, 1 = disjointes. C'est la FRACTION
    D'AIRE qui a changé de direction — un nombre lisible, pas un score arbitraire."""
    if len(a) != len(b):
        raise ValueError("signatures de tailles différentes")
    return round(0.5 * sum(abs(x - y) for x, y in zip(a, b)), 4)


def _mesurer_perte(dossier: Path, niveau: int, fichier: str, ref_sig=None) -> dict:
    """Silhouettes du niveau + IoU contre le LOD0 + écart de normales. Dégrade proprement : un GLB compressé ou
    trop lourd rend `mesure: False` avec la raison, jamais une exception qui ferait tomber la chaîne."""
    from PIL import Image
    from app.services import asset3d_qc, mesh_report, print3d
    p = dossier / fichier
    try:
        tris = print3d.lire_glb_triangles(p.read_bytes())
    except Exception as e:                       # compressé, buffer externe…
        return {"mesure": False, "raison": str(e)}
    if not tris:
        return {"mesure": False, "raison": "maillage vide"}
    if len(tris) > MAX_TRIS_SIGNATURE:
        return {"mesure": False, "raison": f"{len(tris)} triangles > {MAX_TRIS_SIGNATURE}"}
    try:
        mesh_report.silhouettes(p, dossier / f"sil_lod{niveau}", px=SIL_PX)
        sig = signature_normales(tris)
    except ValueError as e:
        return {"mesure": False, "raison": str(e)}
    if niveau == 0:
        return {"mesure": True, "signature": sig, "iou": {v: 1.0 for v in _VUES}, "iou_min": 1.0,
                "ecart_normales": 0.0}
    ref_dir = dossier / "sil_lod0"
    if ref_sig is None or not ref_dir.is_dir():
        return {"mesure": False, "raison": "le LOD0 n'a pas pu être mesuré : rien à comparer"}
    ious = {}
    for vue in _VUES:
        with Image.open(ref_dir / f"silhouette_{vue}.png") as a, \
                Image.open(dossier / f"sil_lod{niveau}" / f"silhouette_{vue}.png") as b:
            ious[vue] = round(asset3d_qc.iou(a.convert("L"), b.convert("L")), 4)
    return {"mesure": True, "signature": sig, "iou": ious, "iou_min": min(ious.values()),
            "ecart_normales": ecart_normales(ref_sig, sig)}


# ── la chaîne ────────────────────────────────────────────────────────────────

def _normaliser_niveaux(tris_source: int, usage: str, niveaux=None) -> list[int]:
    from app.services import mesh_optimize
    if niveaux is None:
        if usage not in BUDGETS:
            raise ValueError(f"usage inconnu : {usage!r} (attendu : {', '.join(BUDGETS)})")
        niveaux = list(BUDGETS[usage]["niveaux"])
    else:
        try:
            niveaux = [int(v) for v in niveaux]
        except (TypeError, ValueError):
            raise ValueError(f"niveaux invalides : {niveaux!r} — des entiers")
    if not niveaux:
        raise ValueError("il faut au moins un niveau sous le LOD0")
    if len(niveaux) > MAX_NIVEAUX - 1:
        raise ValueError(f"{len(niveaux) + 1} niveaux — Unity en accepte {MAX_NIVEAUX} au plus (LOD Group)")
    out: list[int] = []
    for v in niveaux:
        v = max(mesh_optimize.TARGET_MIN, min(mesh_optimize.TARGET_MAX, v))
        if out and v >= out[-1]:
            raise ValueError(f"les niveaux doivent DÉCROÎTRE strictement — {v} arrive après {out[-1]}")
        out.append(v)
    if out[0] >= tris_source:
        raise ValueError(f"le premier niveau vise {out[0]} triangles pour une source de {tris_source} : la chaîne "
                         "n'allègerait rien. Choisis un budget plus bas, ou un autre usage.")
    return out


def chaine(job, *, usage: str = "pc", niveaux=None) -> dict:
    """Écrit `lod/lod0.glb … lodN.glb` + `lod/lod.json` depuis le GLB courant. Synchrone (gltfpack) — la route
    l'exécute dans un thread."""
    from app.services import asset3d_service as A3, mesh_optimize
    d = _job_dir(job)
    if not d.is_dir():
        raise FileNotFoundError(f"job 3D inconnu : {job}")
    src = d / A3._glb_courant(job)
    if not src.is_file():
        raise FileNotFoundError(f"{src.name} introuvable pour ce job")
    base = mesh_optimize.glb_stats(src)
    cibles = _normaliser_niveaux(base["tris"], usage, niveaux)     # refuse AVANT d'effacer quoi que ce soit
    exe = mesh_optimize._gltfpack()

    dossier = d / "lod"
    if dossier.is_dir():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)

    bases = _bases(src.read_bytes())
    (dossier / "lod0.glb").write_bytes(_renommer(src.read_bytes(), 0, bases))
    niveaux_out = [{"niveau": 0, "file": "lod0.glb", "cible": None, "aggressive": False,
                    **mesh_optimize.glb_stats(dossier / "lod0.glb")}]

    for i, cible in enumerate(cibles, 1):
        out = dossier / f"lod{i}.glb"
        rapport = dossier / f"lod{i}.rapport.json"
        ratio = max(0.001, min(1.0, cible / max(1, base["tris"])))

        def run(extra, _out=out, _rapport=rapport, _ratio=ratio, _i=i):
            r = subprocess.run([exe, "-i", str(src), "-o", str(_out), "-si", f"{_ratio:.6f}",
                                "-noq", "-kn", "-km", "-r", str(_rapport)] + extra,
                               capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not _out.is_file():
                raise RuntimeError(f"gltfpack a échoué au LOD{_i} ({r.returncode}) : "
                                   f"{(r.stderr or r.stdout or '').strip()[:300]}")

        run([])
        agressif = False
        if mesh_optimize.glb_stats(out)["tris"] > cible * 1.15:
            run(["-sa"])                  # même seuil de rattrapage que /optimize
            agressif = True
        out.write_bytes(_renommer(out.read_bytes(), i, bases))
        st = {"niveau": i, "file": out.name, "cible": cible, "aggressive": agressif,
              **mesh_optimize.glb_stats(out)}
        # mesuré sur 8799 le 06/10 : une sphère de 6 240 triangles visée à 200 sort à 334 MÊME après -sa — gltfpack
        # protège la topologie ; la chaîne le DIT au lieu de laisser croire la cible tenue
        st["cible_tenue"] = st["tris"] <= cible * 1.15
        try:
            st["gltfpack"] = json.loads(rapport.read_text(encoding="utf-8"))
        except Exception as e:            # rapport absent ou illisible : le dire
            st["gltfpack"] = {"erreur": str(e)}
        niveaux_out.append(st)

    p0 = _mesurer_perte(dossier, 0, "lod0.glb")
    ref_sig = p0.get("signature")
    niveaux_out[0]["perte"] = {k: v for k, v in p0.items() if k != "signature"}
    for st in niveaux_out[1:]:
        p = _mesurer_perte(dossier, st["niveau"], st["file"], ref_sig)
        st["perte"] = {k: v for k, v in p.items() if k != "signature"}

    info = {"job": Path(str(job)).name, "source": src.name,
            "usage": usage if niveaux is None else "personnalise",
            "niveaux": niveaux_out,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (dossier / "lod.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    return info


def lire(job) -> dict:
    p = _job_dir(job) / "lod" / "lod.json"
    if not p.is_file():
        raise FileNotFoundError("aucune chaîne de LOD pour ce job")
    return json.loads(p.read_text(encoding="utf-8"))


def _lisezmoi(info: dict) -> str:
    L = [f"Chaîne de LOD — job {info['job']} (source {info['source']}, usage {info['usage']}, {info['created_at']})",
         "",
         "Niveau  fichier      triangles     cible   IoU min   écart normales"]
    for n in info["niveaux"]:
        pe = n.get("perte") or {}
        iou, ec = pe.get("iou_min"), pe.get("ecart_normales")
        cible = str(n["cible"]) if n["cible"] is not None else "—"
        s_iou = f"{iou:.4f}" if iou is not None else "non mesuré"
        s_ec = f"{ec:.4f}" if ec is not None else "non mesuré"
        L.append(f"LOD{n['niveau']}    {n['file']:<12} {n['tris']:>9}  {cible:>8}  {s_iou:>9}   {s_ec}"
                 + ("   (cible non tenue : gltfpack n'a pas pu descendre plus bas sans casser la topologie)"
                    if n.get("cible_tenue") is False else ""))
    L += [
        "",
        f"IoU : intersection sur union des silhouettes face/profil/dessus ({SIL_PX} px) contre le LOD0. "
        "1,0 = silhouette identique.",
        "Écart de normales : fraction de l'aire qui a changé de direction (0 = aucune, 1 = tout). Une bosse aplatie "
        "garde sa silhouette et déplace ses normales : c'est ce que ce nombre voit.",
        "",
        "Unity — docs.unity3d.com/Manual/lod-group-configure.html, relue le 03/09/2026 : le suffixe _LODX sur le "
        "nom de chaque mesh est la convention. Le guide exporte en .fbx ; en GLB, l'import ne crée pas forcément le "
        "LOD Group tout seul — ajoute-le sur le parent et glisse les niveaux dedans.",
        "Godot — docs.godotengine.org (node_type_customization), relue le 03/09/2026 : les suffixes documentés sont "
        "-col, -convcol, -rigid, -noimp, -loop… AUCUN suffixe LOD. Les noms _LODX ne déclenchent donc rien : "
        "importe les niveaux comme des scènes séparées.",
        "Unreal — importe chaque GLB puis assigne les LOD dans le Static Mesh Editor. Cette ligne-ci n'est PAS "
        "vérifiée dans la documentation (NON vérifiée) : ne t'appuie pas dessus comme sur les deux précédentes.",
    ]
    return "\n".join(L) + "\n"


def archive(job) -> tuple[str, bytes]:
    """Le ZIP livré : les GLB de la chaîne, lod.json, et le LISEZMOI qui dit ce que chaque moteur fait — ou ne fait
    pas — du suffixe."""
    d = _job_dir(job)
    info = lire(job)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for st in info["niveaux"]:
            z.write(d / "lod" / Path(st["file"]).name, Path(st["file"]).name)
        z.writestr("lod.json", json.dumps(info, indent=1, ensure_ascii=False))
        z.writestr("LISEZMOI.txt", _lisezmoi(info))
    return f"{Path(str(job)).name}_LOD.zip", buf.getvalue()
