# -*- coding: utf-8 -*-
"""t489 (FDA) — banc comparatif de l'Atelier DA : méthode « actuel » contre « ancre » (et « ancre_multi »).

Protocole complet : docs/superpowers/specs/2026-11-09-fiches-modeles-scenario-design.md §8. Règle de décision écrite
AVANT le tir (rappelée dans le rapport).

  python scripts/banc_da_coherence.py                      DEVIS SEUL (gratuit) : écrit devis.json / devis.md, s'arrête
  python scripts/banc_da_coherence.py --confirme --max-usd 10 [--corpus fichier.json]
                                                           tire, mesure M1-M6, écrit rapport.md et vote.html
  python scripts/banc_da_coherence.py --mesurer DOSSIER [--juge]
                                                           remesure sans tirer (--juge : M3 payant, sous --max-usd)
  python scripts/banc_da_coherence.py --decider DOSSIER --vote vote.json
                                                           applique la règle avec le vote M7

ISOLATION. Le tir se fait EN PROCESSUS, sur un dossier de données jetable (DEEPOTUS_DATA_DIR =
outputs/bancs/da-coherence-<date>/donnees) : aucune entité, image ni dépense n'entre dans la Bibliothèque de
l'utilisateur. Les clés sont LUES par un sous-processus sur la configuration de l'utilisateur et passées par
l'environnement ; elles ne sont jamais écrites ni affichées. La garde de dépense de l'app s'applique (plafonds du
dossier jetable), et le script s'arrête de lui-même avant `--max-usd`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import pathlib
import random
import subprocess
import sys
import time
from datetime import datetime

RACINE = pathlib.Path(__file__).resolve().parents[1]
BACKEND = RACINE / "backend"
CLES = ("FAL_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")

# ── le plan du banc (§8) ──────────────────────────────────────────────────────────────────────────────────────────
FOURNISSEURS = {"flux": ("actuel", "ancre"), "nano-banana-2.1": ("actuel", "ancre", "ancre_multi")}
REPETITIONS = 2
PANNEAUX_TIRES = 4                # face_left, front, left, back (le maître est partagé, les miroirs sont gratuits)
CORPUS_DEFAUT = [
    # Elias, le compagnon du teaser CHARGE : son portrait d'ancrage (gen_3e9ae827, 02-refs/bible) sert d'inspiration
    {"id": "realiste", "name": "Elias",
     "description": "a man around forty, short tousled dark hair, full short dark beard with grey hairs, grey-blue "
                    "eyes, weathered skin, dark charcoal wool pea coat with a wide collar over a black crew-neck "
                    "sweater, dark trousers, black leather boots",
     "style": "realistic cinematic photography, natural skin texture, muted blue-grey light",
     "inspiration": "@images/gen_3e9ae827.png"},
    {"id": "manga", "name": "Rin",
     "description": "a teenage girl with long straight black hair and a red hair ribbon, large violet eyes, navy "
                    "sailor school uniform with a red neckerchief, white socks, brown loafers",
     "style": "manga, clean ink lines, cel shading", "inspiration": None},
    {"id": "ligne_claire", "name": "Gaspard",
     "description": "a stocky middle-aged sailor with a big round nose, white beard, blue knit cap, yellow raincoat, "
                    "black rubber boots, a brass pipe",
     "style": "ligne claire franco-belge, gros nez, aplats de couleurs", "inspiration": None},
]
CRITERES_M3 = [
    "Visage : identique au visage maître (traits, âge, forme)",
    "Coiffure et couleur des cheveux : conservées",
    "Tenue : chaque pièce conservée, rien d'ajouté",
    "Couleurs de la tenue : conservées (pas de recoloration)",
    "Accessoires : conservés",
    "Proportions du corps : constantes d'une vue à l'autre",
    "Aucun texte parasite, aucun double visage",
    "Profil gauche du bon côté (nez vers la gauche)",
]


# ── 0. isolation et clés ──────────────────────────────────────────────────────────────────────────────────────────

def lire_cles() -> dict:
    """Les clés de l'utilisateur, lues par un SOUS-PROCESSUS sur SA configuration (fichier .env et coffre) ; rendues
    par un tube, jamais affichées."""
    code = (f"import json,sys;sys.path.insert(0,{str(BACKEND)!r});from app.config import settings as s;"
            f"sys.stdout.write(json.dumps({{k: str(getattr(s, k, '') or '') for k in {list(CLES)!r}}}))")
    env = {k: v for k, v in os.environ.items() if k != "DEEPOTUS_DATA_DIR"}
    r = subprocess.run([sys.executable, "-c", code], cwd=str(BACKEND), capture_output=True, text=True, env=env,
                       timeout=120)
    if r.returncode != 0:
        raise SystemExit("lecture des clés impossible (configuration de l'app illisible)")
    return {k: v for k, v in json.loads(r.stdout.strip().splitlines()[-1]).items() if v}


def chemin_inspiration(v: str | None) -> pathlib.Path | None:
    """« @images/<nom> » = une image de la Bibliothèque de l'utilisateur (lue, jamais modifiée) ; sinon un chemin."""
    if not v:
        return None
    if v.startswith("@images/"):
        racine = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "DeepotusVideoGenData" / "assets" / "images"
        return racine / v[len("@images/"):]
    return pathlib.Path(v)


def preparer_isolation(dossier: pathlib.Path, cles: dict) -> None:
    donnees = dossier / "donnees"
    (donnees / "images").mkdir(parents=True, exist_ok=True)
    os.environ["DEEPOTUS_DATA_DIR"] = str(donnees)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(donnees / 'banc.db').as_posix()}"
    os.environ["IMAGES_FOLDER"] = str(donnees / "images")
    os.environ.update(cles)
    sys.path.insert(0, str(BACKEND))


# ── 1. devis (gratuit) ────────────────────────────────────────────────────────────────────────────────────────────

def devis(corpus: list[dict], juge_reps: int = REPETITIONS) -> dict:
    """Le devis du banc, lu sur la grille de prix de l'app : planches, maîtres, relances au pire, juge M3."""
    sys.path.insert(0, str(BACKEND))
    from app.services import pricing as P, briques as B
    p = P.load()
    kontext = float(p.get("flux_kontext_usd_mpx", 0.025))          # ~1 Mpx par panneau (cadres ≤ 1 Mpx)
    flux_dev = kontext                                               # flux/dev : même ordre, 1 Mpx
    nano = float(P.estimate({"kind": "image", "n": 1, "model": "nano-banana-2.1"})["total_usd"])
    ref = float(P.IMAGE_REF_USD.get("nano-banana-2.1", 0.0))
    n = len(corpus)
    lignes = []
    # maîtres : un par (personnage, fournisseur)
    lignes.append(("Visages maîtres FLUX", n, flux_dev))
    lignes.append(("Visages maîtres Nano Banana 2.1", n, nano))
    for f, bras in FOURNISSEURS.items():
        u = kontext if f == "flux" else nano
        planches = n * len(bras) * REPETITIONS
        lignes.append((f"Panneaux {f} ({planches} planches × {PANNEAUX_TIRES})", planches * PANNEAUX_TIRES, u))
        if f != "flux":
            multi = n * REPETITIONS                                  # ancre_multi : profil + dos, 2 refs chacun
            lignes.append(("Références supplémentaires ancre_multi", multi * 2 * 2, ref))
            lignes.append(("Références simples (édition)", planches * PANNEAUX_TIRES, ref))
        ancre = n * sum(1 for b in bras if b != "actuel") * REPETITIONS
        lignes.append((f"Relance du héros au pire ({f})", ancre, u))
        lignes.append((f"Relances de proportions au pire ({f}, 2 par planche)", planches * 2, u))
    # contrôle de proportions : une mesure vision par tir du corps de face (relances comprises)
    try:
        from app.services import proportion_qc as PQC
        mesure = float(getattr(PQC, "COUT_MESURE_USD", 0.01))
    except Exception:  # noqa: BLE001
        mesure = 0.01
    total_planches = n * sum(len(b) for b in FOURNISSEURS.values()) * REPETITIONS
    lignes.append(("Mesures de proportions (vision, au pire 3 par planche)", total_planches * 3, mesure))
    try:
        juge = float(B.devis_avis(4, CRITERES_M3, contexte="banc DA")["usd"] or 0.0)
    except Exception:  # noqa: BLE001
        juge = 0.035
    jugees = total_planches * max(0, min(juge_reps, REPETITIONS)) // REPETITIONS
    lignes.append((f"Juge M3 à l'aveugle (une planche par appel, {juge_reps} répétition(s) jugée(s))", jugees, juge))
    pire = round(sum(q * u for _, q, u in lignes), 2)
    sans_relance = round(sum(q * u for lib, q, u in lignes if "au pire" not in lib)
                         + total_planches * mesure, 2)
    return {"lignes": [{"libelle": l, "quantite": q, "unitaire_usd": round(u, 4), "usd": round(q * u, 4)}
                       for l, q, u in lignes],
            "planches": total_planches, "maitres": 2 * n, "total_pire_usd": pire,
            "total_probable_usd": sans_relance, "plafond_usd": 10.0}


def ecrire_devis(dossier: pathlib.Path, d: dict, corpus: list[dict]) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "devis.json").write_text(json.dumps({"devis": d, "corpus": corpus}, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    md = ["# Banc DA cohérence — devis", "", f"Planches : {d['planches']} ; visages maîtres : {d['maitres']}.", "",
          "| Poste | Quantité | Unitaire | Total |", "|---|---:|---:|---:|"]
    md += [f"| {l['libelle']} | {l['quantite']} | {l['unitaire_usd']:.4f} $ | {l['usd']:.2f} $ |" for l in d["lignes"]]
    md += ["", f"**Probable (sans relance) : {d['total_probable_usd']:.2f} $ — au pire : {d['total_pire_usd']:.2f} $ "
               f"— plafond : {d['plafond_usd']:.0f} $.**", "", "## Corpus", ""]
    md += [f"- **{c['name']}** ({c['id']}) — {c['description']} — style : {c['style']}"
           + (f" — image de référence : `{c['inspiration']}`" if c.get("inspiration") else "") for c in corpus]
    (dossier / "devis.md").write_text("\n".join(md) + "\n", encoding="utf-8")


# ── 2. mesures (M1, M2, M4, M5, M6 gratuites ; M3 payante) ────────────────────────────────────────────────────────

def _lab(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(x)) for x in rgb)
    x, y, z = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b, \
        (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e_palettes(pa, pb) -> float:
    """M2 — écart moyen (CIE76) de chaque couleur dominante de `pb` à la plus proche de `pa`."""
    if not pa or not pb:
        return float("nan")
    la, lb = [_lab(c) for c in pa], [_lab(c) for c in pb]
    return round(sum(min(math.dist(x, y) for y in la) for x in lb) / len(lb), 2)


def mesurer_planche(images: pathlib.Path, panneaux: dict) -> dict:
    from app.services import board_service as BS
    m1 = {}
    for cle, ancre in (("face_left", "face_front"), ("left", "front"), ("back", "front"), ("front", "face_front")):
        if cle in panneaux and ancre in panneaux:
            m1[cle] = BS.similarite_identite(images, panneaux[ancre], panneaux[cle])
    pal = {k: BS._palette_colors(images, [panneaux[k]], n=6) for k in ("front", "left", "back") if k in panneaux}
    m2 = {k: delta_e_palettes(pal.get("front"), pal.get(k)) for k in ("left", "back") if k in pal}
    return {"m1": m1, "m2": m2}


# ── 3. le tir ─────────────────────────────────────────────────────────────────────────────────────────────────────

def verifier_isolation(dossier: pathlib.Path) -> None:
    """Refuse de tirer si l'app n'est pas sur le dossier jetable : base, images ET racine de données."""
    from app.config import DATA_ROOT, settings
    attendu = (dossier / "donnees").resolve()
    racines = {"DATA_ROOT": pathlib.Path(DATA_ROOT).resolve(), "images": pathlib.Path(settings.images_path).resolve()}
    base = str(getattr(settings, "DATABASE_URL", "") or "")
    hors = [k for k, v in racines.items() if attendu not in (v, *v.parents)]
    if hors or "banc.db" not in base:
        raise SystemExit(f"ISOLATION ROMPUE ({', '.join(hors) or 'base'}) : aucun tir — l'app ne vise pas {attendu}")


async def tirer(dossier: pathlib.Path, corpus: list[dict], max_usd: float) -> dict:
    verifier_isolation(dossier)                     # AVANT toute requête : rien n'écrit chez l'utilisateur
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services.storage import init_db, BibleEntity, async_session_factory
    from app.services import plafonds as PL, pricing as P
    await init_db()
    images = pathlib.Path(os.environ["IMAGES_FOLDER"])
    depense = [0.0]

    async def depense_reelle() -> float:
        try:
            # registre du dossier jetable (les mesures de proportions, appels vision directs, n'y sont pas)
            return float((await PL.etat())["global"]["effectif_usd"])
        except Exception:  # noqa: BLE001
            return depense[0]

    resultats = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://banc", timeout=900) as c:
        for perso in corpus:
            corps = {"kind": "character", "name": perso["name"], "description": perso["description"],
                     "style_notes": perso["style"]}
            if perso.get("inspiration"):
                src = chemin_inspiration(perso["inspiration"])        # COPIÉE dans le dossier jetable
                (images / src.name).write_bytes(src.read_bytes())
                corps["inspiration_images"] = [src.name]
            for fournisseur, bras in FOURNISSEURS.items():
                await c.put("/api/atelier/settings", json={"image_provider": fournisseur})
                eid = (await c.post("/api/bible/entities", json=corps)).json()["id"]
                maitre = None
                for rep in range(REPETITIONS):
                    ordre = list(bras)
                    for methode in ordre:
                        if await depense_reelle() >= max_usd * 0.92:
                            return {"interrompu": f"dépense proche du plafond ({max_usd} $)", "planches": resultats}
                        t0 = time.time()
                        avant = await depense_reelle()
                        body = {"methode": methode, "seed": 1000 + rep}
                        if maitre:
                            body["face_maitre"] = maitre
                        r = await c.post(f"/api/bible/entities/{eid}/generate", json=body)
                        if r.status_code != 200:
                            resultats.append({"perso": perso["id"], "fournisseur": fournisseur, "methode": methode,
                                              "rep": rep, "erreur": r.text[:300]})
                            continue
                        async with async_session_factory() as s:
                            e = await s.get(BibleEntity, eid)
                            rec = json.loads(e.prompt_recipe)
                        panneaux = {p["key"]: p["file"] for p in rec["panels"]}
                        panneaux.update(rec.get("mirrors") or {})
                        maitre = maitre or panneaux["face_front"]
                        apres = await depense_reelle()
                        resultats.append({
                            "perso": perso["id"], "fournisseur": fournisseur, "methode": methode, "rep": rep,
                            "planche": rec["board"], "panneaux": panneaux, "controle_heros": rec.get("controle_heros"),
                            "profondeurs": {p["key"]: p.get("profondeur") for p in rec["panels"]},
                            "tirs_corps": sum(1 for p in rec["panels"] if p["key"] == "front"),
                            "usd": round(apres - avant, 4), "secondes": round(time.time() - t0, 1),
                            "mesures": mesurer_planche(images, panneaux)})
                        (dossier / "planches.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=1),
                                                               encoding="utf-8")
    return {"planches": resultats}


# ── 4. juge M3, rapport, vote ─────────────────────────────────────────────────────────────────────────────────────

async def juger(dossier: pathlib.Path, planches: list[dict], max_usd: float, juge_reps: int = REPETITIONS) -> None:
    """M3 — avis vision À L'AVEUGLE : chaque planche seule (maître, corps de face, profil, dos), sans dire son bras."""
    from app.services import briques as B
    images = pathlib.Path(os.environ["IMAGES_FOLDER"])
    for p in planches:
        if "panneaux" not in p or p.get("m3") or p["rep"] >= juge_reps:
            continue
        chemins = [str(images / p["panneaux"][k]) for k in ("face_front", "front", "left", "back") if k in p["panneaux"]]
        try:
            a = await B.avis(chemins, CRITERES_M3, max_usd=0.2, categorie="atelier",
                             contexte="Image 1 = visage maître. Images 2 à 4 = le même personnage, de face, profil "
                                      "gauche, dos. Juge si les vues 2 à 4 conservent le personnage de l'image 1.")
            p["m3"] = {"moyenne": a.get("moyenne"), "criteres": a.get("criteres"), "usd": a.get("usd")}
        except Exception as e:  # noqa: BLE001
            p["m3"] = {"erreur": str(e)[:200]}
        (dossier / "planches.json").write_text(json.dumps(planches, ensure_ascii=False, indent=1), encoding="utf-8")


def _moy(v):
    v = [x for x in v if isinstance(x, (int, float)) and x == x]
    return round(sum(v) / len(v), 4) if v else None


def synthese(planches: list[dict]) -> dict:
    """Moyennes par (fournisseur, méthode) et par personnage ; M4 = écart profondeur 2 contre profondeur 1."""
    par = {}
    for p in planches:
        if "panneaux" not in p:
            continue
        k = (p["fournisseur"], p["methode"])
        s = par.setdefault(k, {"m1": [], "m2": [], "m3": [], "usd": [], "s": [], "m1_prof2": [], "m1_prof1": [],
                               "par_perso": {}})
        m1 = p["mesures"]["m1"]
        s["m1"] += [v for v in m1.values() if v is not None]
        s["m2"] += [v for v in p["mesures"]["m2"].values()]
        s["m3"].append((p.get("m3") or {}).get("moyenne"))
        s["usd"].append(p["usd"])
        s["s"].append(p["secondes"])
        for cle in ("left", "back"):
            prof = (p.get("profondeurs") or {}).get(cle) or (2 if p["methode"] == "actuel" else 1)
            s["m1_prof2" if prof == 2 else "m1_prof1"].append(m1.get(cle))
        s["par_perso"].setdefault(p["perso"], []).append((p.get("m3") or {}).get("moyenne"))
    return {f"{f}|{m}": {"M1": _moy(s["m1"]), "M2": _moy(s["m2"]), "M3": _moy(s["m3"]), "M6_usd": _moy(s["usd"]),
                         "M6_s": _moy(s["s"]), "M4_m1_prof2": _moy(s["m1_prof2"]), "M4_m1_prof1": _moy(s["m1_prof1"]),
                         "M3_par_perso": {k: _moy(v) for k, v in s["par_perso"].items()}}
            for (f, m), s in par.items()}


def decider(syn: dict, vote: dict | None) -> list[str]:
    """La règle du §8, écrite AVANT le tir. B (ancre) contre A (actuel) par fournisseur ; C (ancre_multi) contre B."""
    out = []
    for f in FOURNISSEURS:
        for neuf, ref in (("ancre", "actuel"), ("ancre_multi", "ancre")):
            a, b = syn.get(f"{f}|{ref}"), syn.get(f"{f}|{neuf}")
            if not a or not b:
                continue
            raisons = []
            if a["M3"] and b["M3"]:
                gain = (b["M3"] - a["M3"]) / a["M3"]
                raisons.append(("M3 +10 % en moyenne", gain >= 0.10, f"{gain:+.1%}"))
                pires = [(b["M3_par_perso"].get(k) or 0) / v - 1 for k, v in a["M3_par_perso"].items() if v]
                raisons.append(("M3 jamais pire de plus de 5 % par personnage", all(x >= -0.05 for x in pires),
                                ", ".join(f"{x:+.0%}" for x in pires)))
            else:
                raisons.append(("M3 mesuré", False, "juge non passé"))
            v = ((vote or {}).get(f) or {}).get(f"{neuf}>{ref}")
            if v:
                gagnes, perdus = v.get("neuf", 0), v.get("ref", 0)
                part = gagnes / (gagnes + perdus) if gagnes + perdus else 0
                raisons.append(("M7 ≥ 60 % des votes non égaux", part >= 0.60, f"{part:.0%} ({gagnes}/{gagnes + perdus})"))
            else:
                raisons.append(("M7 voté", False, "vote absent"))
            if a["M6_usd"] and b["M6_usd"]:
                surcout = b["M6_usd"] / a["M6_usd"] - 1
                raisons.append(("M6 ≤ +20 %", surcout <= 0.20, f"{surcout:+.0%}"))
            ok = all(r[1] for r in raisons)
            out.append(f"**{f} : {neuf} {'REMPLACE' if ok else 'ne remplace pas'} {ref}** — "
                       + " ; ".join(f"{n} {'✓' if v_ else '✗'} ({d})" for n, v_, d in raisons))
    return out or ["Aucune comparaison complète : rien ne change."]


def ecrire_rapport(dossier: pathlib.Path, planches: list[dict], vote: dict | None = None) -> None:
    syn = synthese(planches)
    md = ["# Banc DA cohérence — rapport", "", f"Planches réussies : {sum(1 for p in planches if 'panneaux' in p)} ; "
          f"échecs : {sum(1 for p in planches if 'erreur' in p)}.", "",
          "| Fournisseur | Méthode | M1 identité (CLIP) | M2 ΔE tenue | M3 juge /10 | M4 CLIP prof. 2 / 1 | M6 $ | M6 s |",
          "|---|---|---:|---:|---:|---:|---:|---:|"]
    for k, s in sorted(syn.items()):
        f, m = k.split("|")
        md.append(f"| {f} | {m} | {s['M1']} | {s['M2']} | {s['M3']} | {s['M4_m1_prof2']} / {s['M4_m1_prof1']} | "
                  f"{s['M6_usd']} | {s['M6_s']} |")
    md += ["", "## Décision (règle écrite avant le tir)", ""] + [f"- {x}" for x in decider(syn, vote)]
    md += ["", "M4 explique, il ne décide pas. Si aucune règle n'est remplie, « actuel » reste le défaut.", "",
           "## Planches", ""]
    for p in planches:
        if "planche" in p:
            md.append(f"- {p['perso']} · {p['fournisseur']} · {p['methode']} · rép. {p['rep']} : "
                      f"`donnees/images/{p['planche']}`")
    (dossier / "mesures.json").write_text(json.dumps(syn, ensure_ascii=False, indent=1), encoding="utf-8")
    (dossier / "rapport.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def ecrire_vote(dossier: pathlib.Path, planches: list[dict]) -> None:
    """M7 — paires sans étiquette, ordre tiré au hasard ; le vote se télécharge en vote.json."""
    rnd = random.Random(489)
    paires = []
    for f in FOURNISSEURS:
        for neuf, ref in (("ancre", "actuel"), ("ancre_multi", "ancre")):
            for perso in {p["perso"] for p in planches}:
                xs = [p for p in planches if p.get("planche") and p["fournisseur"] == f and p["perso"] == perso]
                for rep in range(REPETITIONS):
                    a = next((p for p in xs if p["methode"] == ref and p["rep"] == rep), None)
                    b = next((p for p in xs if p["methode"] == neuf and p["rep"] == rep), None)
                    if a and b:
                        g, d = (a, b) if rnd.random() < 0.5 else (b, a)
                        paires.append({"id": f"{f}|{neuf}>{ref}|{perso}|{rep}", "gauche": g["planche"],
                                       "droite": d["planche"], "neuf_a_gauche": g is b})
    rnd.shuffle(paires)
    page = """<!doctype html><meta charset="utf-8"><title>Vote DA</title>
<style>body{font:15px system-ui;background:#111;color:#eee;margin:16px}img{max-width:48vw;max-height:70vh;border:2px solid #333}
.p{display:none}.p.on{display:block}.b{margin:10px 8px 0 0;padding:8px 16px;font-size:15px}</style>
<h1>Quelle planche garde le mieux le personnage ?</h1><p id="n"></p><div id="z"></div>
<button class="b" id="dl">Télécharger vote.json</button>
<script>const P=__PAIRES__;const V={};let i=0;const z=document.getElementById("z");
function f(){if(i>=P.length){z.innerHTML="<p>Fini — télécharge vote.json.</p>";return}const p=P[i];
document.getElementById("n").textContent=(i+1)+" / "+P.length;
z.innerHTML='<img src="donnees/images/'+p.gauche+'"> <img src="donnees/images/'+p.droite+'"><br>'+
'<button class="b" data-c="g">Gauche</button><button class="b" data-c="e">Égal</button><button class="b" data-c="d">Droite</button>';
z.querySelectorAll("button").forEach(b=>b.onclick=()=>{V[p.id]={choix:b.dataset.c,neuf_a_gauche:p.neuf_a_gauche};i++;f()})}
document.getElementById("dl").onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(V,null,1)],{type:"application/json"}));a.download="vote.json";a.click()};f();</script>"""
    (dossier / "vote.html").write_text(page.replace("__PAIRES__", json.dumps(paires)), encoding="utf-8")


def vote_vers_compte(v: dict) -> dict:
    """vote.json (choix par paire) -> {fournisseur: {"neuf>ref": {"neuf": n, "ref": n}}} ; « égal » ne compte pas."""
    out = {}
    for pid, x in (v or {}).items():
        f, duel = pid.split("|")[:2]
        if x.get("choix") == "e":
            continue
        neuf_gagne = (x.get("choix") == "g") == bool(x.get("neuf_a_gauche"))
        c = out.setdefault(f, {}).setdefault(duel, {"neuf": 0, "ref": 0})
        c["neuf" if neuf_gagne else "ref"] += 1
    return out


# ── main ──────────────────────────────────────────────────────────────────────────────────────────────────────────

def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Banc comparatif de l'Atelier DA (t489)")
    ap.add_argument("--confirme", action="store_true", help="tire pour de vrai (payant)")
    ap.add_argument("--max-usd", type=float, default=10.0)
    ap.add_argument("--corpus", help="JSON : liste de personnages {id, name, description, style, inspiration?}")
    ap.add_argument("--dossier", help="dossier du banc (défaut : outputs/bancs/da-coherence-<date>)")
    ap.add_argument("--mesurer", help="remesure un dossier existant sans tirer")
    ap.add_argument("--juge", action="store_true", help="avec --mesurer ou --confirme : passe le juge M3 (payant)")
    ap.add_argument("--juge-reps", type=int, default=REPETITIONS,
                    help="répétitions jugées par M3 (1 : moitié du coût du juge)")
    ap.add_argument("--decider", help="applique la règle à un dossier existant")
    ap.add_argument("--vote", help="vote.json téléchargé depuis vote.html")
    a = ap.parse_args(argv)
    corpus = json.loads(pathlib.Path(a.corpus).read_text(encoding="utf-8")) if a.corpus else CORPUS_DEFAUT
    dossier = pathlib.Path(a.dossier or a.mesurer or a.decider or
                           RACINE / "outputs" / "bancs" / f"da-coherence-{datetime.now():%Y%m%d}")
    if a.decider:
        planches = json.loads((dossier / "planches.json").read_text(encoding="utf-8"))
        vote = vote_vers_compte(json.loads(pathlib.Path(a.vote).read_text(encoding="utf-8"))) if a.vote else None
        ecrire_rapport(dossier, planches, vote)
        print((dossier / "rapport.md").read_text(encoding="utf-8"))
        return 0
    if a.mesurer:
        preparer_isolation(dossier, lire_cles() if a.juge else {})
        planches = json.loads((dossier / "planches.json").read_text(encoding="utf-8"))
        images = pathlib.Path(os.environ["IMAGES_FOLDER"])
        for p in planches:
            if "panneaux" in p:
                p["mesures"] = mesurer_planche(images, p["panneaux"])
        if a.juge:
            asyncio.run(juger(dossier, planches, a.max_usd, a.juge_reps))
        ecrire_rapport(dossier, planches)
        ecrire_vote(dossier, planches)
        print(f"remesuré : {dossier / 'rapport.md'}")
        return 0
    if a.confirme:
        # L'ISOLATION D'ABORD : le devis importe app.config, qui fige DATA_ROOT au premier import. Posée après, elle
        # laissait l'app sur le dossier de données de l'utilisateur (incident du 09/11 : une entité créée et un réglage
        # écrit dans sa vraie base avant l'arrêt du garde-fou).
        preparer_isolation(dossier, lire_cles())
    d = devis(corpus, a.juge_reps if (a.juge or not a.confirme) else 0)
    ecrire_devis(dossier, d, corpus)
    print(f"devis : probable {d['total_probable_usd']:.2f} $, au pire {d['total_pire_usd']:.2f} $ "
          f"(plafond {a.max_usd:.0f} $) -> {dossier / 'devis.md'}")
    if not a.confirme:
        print("rien n'a été tiré (ajouter --confirme après accord)")
        return 0
    if d["total_pire_usd"] > a.max_usd:
        print(f"refus : le devis au pire ({d['total_pire_usd']:.2f} $) dépasse --max-usd {a.max_usd:.0f} $ — le "
              f"script s'arrêtera en cours de route ; relancer avec --max-usd plus haut pour tout tirer")
    res = asyncio.run(tirer(dossier, corpus, a.max_usd))
    planches = res["planches"]
    if a.juge:
        asyncio.run(juger(dossier, planches, a.max_usd, a.juge_reps))
    ecrire_rapport(dossier, planches)
    ecrire_vote(dossier, planches)
    print(f"{len(planches)} planches ; rapport : {dossier / 'rapport.md'} ; vote : {dossier / 'vote.html'}"
          + (f" ; INTERROMPU : {res['interrompu']}" if res.get("interrompu") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
