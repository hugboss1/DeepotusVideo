# -*- coding: utf-8 -*-
"""t475 (lot F0 « Fiches modèle », 09/11/2026) — contrat des fiches modèle, tronc commun, service et règles.

Contrat : docs/agent/modeles/MODELES.md ; conception : docs/superpowers/specs/2026-11-09-fiches-modeles-scenario-design.md.
[1] dépôt       MODELES.md et README présents ; tronc commun FR/EN conforme ; verifier() == [] sur le dépôt ;
                aucun nom de modèle génératif dans les rôles métier ni dans le texte des méthodes (verifier_noms) ;
                AGENTS.md et la licence renvoient au contrat.
[2] règles      sur des fiches d'ESSAI écrites dans un dossier temporaire : une fiche conforme passe ; chaque écart
                (description, date, source, parties, budget, liste vide, nature inconnue, id inconnu, id en double,
                id non rangé, parité FR/EN, plafond de durée recopié, nom de famille) est signalé ;
[3] service     lire_entete (listes), index, famille_de, fiche() : corps + bloc « Membres » tiré du registre (durées
                lues dans VIDEO_MODELS, jamais dans la fiche), titres FR/EN, repli FR, inconnue -> None ;
[4] noms        verifier_noms : nom de modèle dans un rôle ou une étape signalé ; « flux » (mot français), les
                exemples (mots de l'utilisateur) et les champs de données ne le sont pas.
Run : & $PY tests/test_modeles_fiches.py   (depuis backend/)
"""
import json
import pathlib
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


CORPS_FR = ("## Aperçu\n\nUne famille d'essai.\n\n## Référence rapide\n\n- [PROMPT] Écrire en phrases.\n\n"
            "## Exemple\n\nBrief, prompt, réglages.\n\n## Erreurs fréquentes\n\n- Aucune.\n")
CORPS_EN = ("## Overview\n\nA test family.\n\n## Quick reference\n\n- [PROMPT] Write sentences.\n\n"
            "## Example\n\nBrief, prompt, settings.\n\n## Common mistakes\n\n- None.\n")


def entete(famille, natures, ids, desc, releve="2026-11-09", source="essai", voies="[fal]"):
    return (f"---\nfamille: {famille}\nnatures: [{', '.join(natures)}]\nids: [{', '.join(ids)}]\nvoies: {voies}\n"
            f"releve: {releve}\nsource: {source}\ndescription: {desc}\n---\n")


def dossier_essai(fiches_fr, fiches_en):
    """Un dossier de fiches : le tronc commun du dépôt + les fiches données {famille: texte}."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="fiches_essai_"))
    for lg, fiches in (("fr", fiches_fr), ("en", fiches_en)):
        (d / lg).mkdir()
        shutil.copy2(M.DOSSIER / lg / "_commun.md", d / lg / "_commun.md")
        for fam, txt in fiches.items():
            (d / lg / f"{fam}.md").write_text(txt, encoding="utf-8")
    return d


def main():
    global M
    from app.services import modeles_fiches as M
    from app.services import catalogue_ia as C

    print("[1] dépôt")
    check("1.1 MODELES.md et README présents", (M.DOSSIER / "MODELES.md").is_file()
          and (M.DOSSIER / "README.md").is_file())
    for lg in M.LANGUES:
        c = M.commun(lg)
        check(f"1.2 {lg}/_commun.md : quatre parties, budget", c is not None
              and M.lire_entete(c["chemin"].read_text(encoding="utf-8"))[0].get("famille") == "_commun"
              and M.mots(c["corps"]) <= M.BUDGET_COMMUN)
    pb = M.verifier()
    check("1.3 verifier() == [] sur les fiches du dépôt", pb == [], str(pb[:5]))
    pb = M.verifier_noms()
    check("1.4 aucun nom de modèle dans les rôles métier ni dans le texte des méthodes", pb == [], str(pb[:5]))
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    import re as _re
    ligne = next((l for l in agents.splitlines() if l.startswith("| `backend/app/services/modeles_fiches.py`")), "")
    cites = [c for c in _re.findall(r"`([^`]+)`", ligne) if "/" in c and " " not in c]
    check("1.5 AGENTS.md : ligne du service, chemins cités existants, règle « nouveau modèle »",
          ligne and "docs/agent/modeles/MODELES.md" in cites and all((REPO / c).exists() for c in cites)
          and "Nouveau modèle" in ligne, str(cites))
    lic = (REPO / "docs" / "licences" / "scenario-mit.md").read_text(encoding="utf-8")
    check("1.6 licence : section des fiches modèle", "Fiches modèle" in lic and "docs/agent/modeles" in lic)

    print("[2] règles, sur des fiches d'essai")
    ids3d = [e["id"] for e in C.lister("objets3d")]
    bon_fr = entete("essai", ["objets3d"], ids3d, "À utiliser quand on teste le banc.") + CORPS_FR
    bon_en = entete("essai", ["objets3d"], ids3d, "Use when testing the banc.") + CORPS_EN
    d = dossier_essai({"essai": bon_fr}, {"essai": bon_en})
    check("2.1 une fiche conforme passe", M.verifier(d) == [], str(M.verifier(d)))

    def signale(nom, fr, en, attendu):
        dd = dossier_essai(fr, en)
        pb = M.verifier(dd)
        check(nom, any(attendu in p for p in pb), str(pb))
        shutil.rmtree(dd, ignore_errors=True)

    signale("2.2 description qui ne commence pas par « À utiliser quand »",
            {"essai": bon_fr.replace("À utiliser quand on teste", "Sert à tester")}, {"essai": bon_en},
            "doit commencer")
    signale("2.3 description trop longue", {"essai": bon_fr.replace("on teste le banc.", "x" * 520)},
            {"essai": bon_en}, "caractères")
    signale("2.4 date de relevé absente", {"essai": bon_fr.replace("releve: 2026-11-09", "releve: hier")},
            {"essai": bon_en}, "releve")
    signale("2.5 source absente", {"essai": bon_fr.replace("source: essai\n", "")}, {"essai": bon_en}, "source")
    signale("2.6 partie manquante", {"essai": bon_fr.replace("## Exemple\n\nBrief, prompt, réglages.\n\n", "")},
            {"essai": bon_en}, "parties")
    signale("2.7 budget dépassé", {"essai": bon_fr.replace("Une famille d'essai.", "mot " * 1300)},
            {"essai": bon_en}, "mots")
    signale("2.8 liste d'ids vide", {"essai": bon_fr.replace(f"ids: [{', '.join(ids3d)}]", "ids: []")},
            {"essai": bon_en}, "« ids »")
    signale("2.9 nature inconnue", {"essai": bon_fr.replace("natures: [objets3d]", "natures: [objets3d, licorne]")},
            {"essai": bon_en.replace("natures: [objets3d]", "natures: [objets3d, licorne]")}, "nature inconnue")
    signale("2.10 id absent de ses natures",
            {"essai": bon_fr.replace(f"ids: [{', '.join(ids3d)}]", f"ids: [{', '.join(ids3d)}, fantome]")},
            {"essai": bon_en.replace(f"ids: [{', '.join(ids3d)}]", f"ids: [{', '.join(ids3d)}, fantome]")},
            "« fantome » absent")
    signale("2.11 id rangé dans deux fiches",
            {"essai": bon_fr, "autre": bon_fr.replace("famille: essai", "famille: autre")},
            {"essai": bon_en, "autre": bon_en.replace("famille: essai", "famille: autre")}, "déjà rangé")
    signale("2.12 id d'une nature couverte rangé nulle part",
            {"essai": bon_fr.replace(f"ids: [{', '.join(ids3d)}]", f"ids: [{ids3d[0]}]")},
            {"essai": bon_en.replace(f"ids: [{', '.join(ids3d)}]", f"ids: [{ids3d[0]}]")}, "couverture")
    signale("2.13 fiche présente en fr seulement", {"essai": bon_fr}, {}, "parité")
    signale("2.14 ids différents entre fr et en", {"essai": bon_fr},
            {"essai": bon_en.replace(f"ids: [{', '.join(ids3d)}]", f"ids: [{ids3d[0]}]")}, "« ids » de essai")
    vid_fr = entete("videoessai", ["video_i2v"], ["seedance-2"], "À utiliser quand on teste.") + CORPS_FR
    signale("2.15 plafond de durée recopié dans une fiche vidéo",
            {"videoessai": vid_fr.replace("Écrire en phrases.", "Durée jusqu'à 15 s.")},
            {"videoessai": entete("videoessai", ["video_i2v"], ["seedance-2"], "Use when testing.") + CORPS_EN},
            "plafond de durée")
    signale("2.16 plafond « 4 à 12 secondes » recopié",
            {"videoessai": vid_fr.replace("Écrire en phrases.", "Plans de 4 à 12 secondes.")},
            {"videoessai": entete("videoessai", ["video_i2v"], ["seedance-2"], "Use when testing.") + CORPS_EN},
            "plafond de durée")
    signale("2.17 nom de famille invalide",
            {"Essai_2": bon_fr.replace("famille: essai", "famille: Essai_2")},
            {"Essai_2": bon_en.replace("famille: essai", "famille: Essai_2")}, "nom de famille invalide")
    signale("2.18 « famille » différente du nom de fichier",
            {"essai": bon_fr.replace("famille: essai", "famille: autre")}, {"essai": bon_en}, "nom de fichier")
    dd = dossier_essai({}, {})
    (dd / "en" / "_commun.md").unlink()
    check("2.19 tronc commun manquant signalé", any("_commun.md absent" in p for p in M.verifier(dd)))
    shutil.rmtree(dd, ignore_errors=True)

    print("[3] service")
    meta, corps = M.lire_entete(bon_fr)
    check("3.1 lire_entete : listes et texte", meta["natures"] == ["objets3d"] and meta["ids"] == ids3d
          and corps.startswith("## Aperçu"))
    check("3.2 lire_entete : sans front-matter, tout est corps", M.lire_entete("## A\n") == ({}, "## A\n"))
    from app.services.fal_service import VIDEO_MODELS
    dur = VIDEO_MODELS["seedance-2"]["durations"]
    vfr = entete("videoessai", ["video_i2v", "video_fl"], ["seedance-2", "kling-v3-pro"],
                 "À utiliser quand on teste.") + CORPS_FR
    ven = entete("videoessai", ["video_i2v", "video_fl"], ["seedance-2", "kling-v3-pro"], "Use when testing.") + CORPS_EN
    dv = dossier_essai({"videoessai": vfr}, {"videoessai": ven})
    origine = M.DOSSIER
    M.DOSSIER = dv
    try:
        f = M.fiche("videoessai", "fr")
        check("3.3 fiche() : corps, membres dans l'ordre du front-matter",
              f is not None and f["famille"] == "videoessai"
              and [m["id"] for m in f["membres"]] == ["seedance-2", "kling-v3-pro"])
        check("3.4 bloc « Membres » : durées lues dans le registre, absentes de la fiche",
              "## Membres" in f["texte"] and f"{min(dur)}–{max(dur)}" in f["texte"]
              and f"{min(dur)}–{max(dur)}" not in vfr)
        check("3.5 natures cumulées (i2v + fin)", f["membres"][0]["natures"] == ["video_i2v", "video_fl"])
        check("3.6 tronc commun joint", "## Référence rapide" in f["commun"])
        fe = M.fiche("seedance-2", "en")
        check("3.7 fiche par id, en anglais : « Members »", fe is not None and fe["famille"] == "videoessai"
              and "## Members" in fe["texte"] and fe["langue"] == "en")
        check("3.8 famille inconnue -> None", M.fiche("licorne") is None)
        check("3.9 index : famille et description", M.index("fr") == [
            {"famille": "videoessai", "description": "À utiliser quand on teste.",
             "natures": ["video_i2v", "video_fl"], "ids": ["seedance-2", "kling-v3-pro"]}])
        check("3.10 famille_de", M.famille_de("kling-v3-pro") == "videoessai" and M.famille_de("x") is None)
        check("3.11 langue inconnue -> français", M.fiche("videoessai", "de")["langue"] == "fr")
        shutil.rmtree(dv / "en")
        (dv / "en").mkdir()
        check("3.12 anglais absent -> repli français", M.fiche("videoessai", "en")["langue"] == "fr")
    finally:
        M.DOSSIER = origine
        shutil.rmtree(dv, ignore_errors=True)
    lignes = M.bloc_membres([{"id": "x", "label": "X", "voie": "fal", "usd": 0, "unite": "s", "cle": "FAL_KEY",
                              "dispo": False}], "fr")
    check("3.13 prix nul = « prix à mesurer », clé absente dite", "prix à mesurer" in lignes and "(absente)" in lignes
          and "gratuit" not in lignes)

    print("[4] noms de modèles")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="noms_essai_"))
    (tmp / "roles").mkdir()
    (tmp / "roles" / "r.md").write_text("Le flux de travail reste simple.\n", encoding="utf-8")
    data = {"methodes": [{"slug": "s", "etapes": {"fr": ["Suivre le flux"], "en": ["Follow the flow"]},
                          "exemples": {"fr": ["Compare Seedance et Kling"]}, "modeles": ["Seedance 2.5"],
                          "equivalents": ["Kling v3"]}]}
    (tmp / "m.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    check("4.1 « flux » français, exemples et données : rien à signaler",
          M.verifier_noms(tmp / "roles", tmp / "m.json") == [], str(M.verifier_noms(tmp / "roles", tmp / "m.json")))
    (tmp / "roles" / "r.md").write_text("Anime le plan avec Kling.\n", encoding="utf-8")
    check("4.2 nom dans un rôle métier signalé", M.verifier_noms(tmp / "roles", tmp / "m.json") == ["r.md:1: « Kling »"])
    (tmp / "roles" / "r.md").write_text("Rien.\n", encoding="utf-8")
    data["methodes"][0]["controles"] = {"en": ["Check FLUX output"]}
    (tmp / "m.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    check("4.3 nom dans un contrôle de méthode signalé (FLUX en capitales)",
          M.verifier_noms(tmp / "roles", tmp / "m.json") == ["methodes.json s.controles: « FLUX »"])
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(d, ignore_errors=True)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
