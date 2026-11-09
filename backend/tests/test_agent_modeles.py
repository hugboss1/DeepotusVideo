# -*- coding: utf-8 -*-
"""t476 (lot F1 « Fiches modèle », 09/11/2026) — l'ACCÈS aux fiches modèle : routes, outils d'agent, boîte, « ? ».

Conception : docs/superpowers/specs/2026-11-09-fiches-modeles-scenario-design.md (§3.B, §7) ; contrat :
docs/agent/modeles/MODELES.md. Les fiches de familles arrivent en F2 : le banc écrit une fiche d'ESSAI dans un dossier
temporaire (modeles_fiches.DOSSIER) pour exercer les chemins « fiche présente ».
[1] routes      GET /api/modeles/index (familles + table id -> famille), /api/modeles/fiche (famille, id, en),
                cle inconnue -> 404 traduite (« unknown model sheet ») ; sans fiche : index vide, 404 ;
[2] agent       boîte « modeles » (deux outils, mcp + neuf agents métier, pas le téléphone, pas Campagnes) ;
                modeles_lister (natures, nature -> modèles + famille de leur fiche, nature inconnue refusée) ;
                modele_fiche (fiche par famille ou id, texte présenté comme DONNÉE, inconnue -> refus qui liste) ;
[3] écran       dz-fiche-modele.js et ses copies identiques dans dist/shared ; chargé AU BESOIN (aucune balise) par
                DzModelesIA.select et la pastille de dz-champ-ia ; clés i18n modeles.fiche.* assemblées ; aucun
                rayon écrit ; aucun innerHTML d'un texte non échappé.
Run : & $PY tests/test_agent_modeles.py   (depuis backend/)
"""
import asyncio
import pathlib
import re
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


CORPS = {"fr": ("## Aperçu\n\nFamille d'essai.\n\n## Référence rapide\n\n- [PROMPT] Décrire le mouvement.\n\n"
                "## Exemple\n\nUn plan.\n\n## Erreurs fréquentes\n\n- Aucune.\n"),
         "en": ("## Overview\n\nTest family.\n\n## Quick reference\n\n- [PROMPT] Describe the motion.\n\n"
                "## Example\n\nOne shot.\n\n## Common mistakes\n\n- None.\n")}
DESC = {"fr": "À utiliser quand on teste l'accès aux fiches.", "en": "Use when testing sheet access."}


def dossier_essai(MF):
    d = pathlib.Path(tempfile.mkdtemp(prefix="fiches_f1_"))
    for lg in ("fr", "en"):
        (d / lg).mkdir()
        shutil.copy2(MF.DOSSIER / lg / "_commun.md", d / lg / "_commun.md")
        (d / lg / "essai.md").write_text(
            f"---\nfamille: essai\nnatures: [video_i2v]\nids: [seedance-2, kling-v3-pro]\nvoies: [fal]\n"
            f"releve: 2026-11-09\nsource: essai\ndescription: {DESC[lg]}\n---\n" + CORPS[lg], encoding="utf-8")
    return d


def main():
    from app.services import modeles_fiches as MF, agent_boites as B, agent_outils as ao
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    origine = MF.DOSSIER

    print("[1] routes")
    vide = pathlib.Path(tempfile.mkdtemp(prefix="fiches_vides_"))
    MF.DOSSIER = vide
    try:
        r = c.get("/api/modeles/index")
        check("1.1 sans fiche : index vide", r.status_code == 200 and r.json() == {"familles": [], "ids": {}}, r.text[:200])
        check("1.2 sans fiche : 404", c.get("/api/modeles/fiche", params={"cle": "seedance-2"}).status_code == 404)
    finally:
        MF.DOSSIER = origine
        shutil.rmtree(vide, ignore_errors=True)
    d = dossier_essai(MF)
    MF.DOSSIER = d
    try:
        r = c.get("/api/modeles/index")
        j = r.json()
        check("1.3 index : la famille et la table id -> famille", r.status_code == 200
              and [f["famille"] for f in j["familles"]] == ["essai"]
              and j["ids"] == {"seedance-2": "essai", "kling-v3-pro": "essai"}, r.text[:300])
        r = c.get("/api/modeles/fiche", params={"cle": "kling-v3-pro"})
        j = r.json()
        check("1.4 fiche par id : famille, membres, bloc « Membres », tronc commun", r.status_code == 200
              and j["famille"] == "essai" and [m["id"] for m in j["membres"]] == ["seedance-2", "kling-v3-pro"]
              and "## Membres" in j["texte"] and "## Référence rapide" in j["commun"], r.text[:300])
        r = c.get("/api/modeles/fiche", params={"cle": "essai", "langue": "en"})
        check("1.5 fiche par famille, en anglais", r.status_code == 200 and r.json()["langue"] == "en"
              and "## Members" in r.json()["texte"] and "Use when" in r.json()["description"])
        r = c.get("/api/modeles/fiche", params={"cle": "licorne"}, headers={"Accept-Language": "en"})
        check("1.6 inconnue -> 404, message traduit", r.status_code == 404
              and r.json().get("detail") == "unknown model sheet", r.text[:200])
        r = c.get("/api/modeles/fiche", params={"cle": "licorne"})
        check("1.7 inconnue -> 404, message français sans en-tête", r.status_code == 404
              and r.json().get("detail") == "fiche modèle inconnue", r.text[:200])

        print("[2] agent")
        check("2.1 boîte « modeles » : deux outils, mcp + neuf agents métier, pas sur le téléphone",
              B.BOITES.get("modeles") == {
                  "libelle": "agent.boites.modeles", "outils": ["modeles_lister", "modele_fiche"],
                  "agents": ["mcp", "monteur", "realisateur", "retoucheur", "declinaisons", "directeur_acteurs",
                             "publicitaire", "artiste_2d", "artiste_3d", "editeur_illustre"], "mobile": False})
        check("2.2 deux outils en lecture, visibles de mcp et du Réalisateur, pas de Campagnes",
              all(ao.OUTILS[o]["nature"] == "lecture" for o in ("modeles_lister", "modele_fiche"))
              and {"modeles_lister", "modele_fiche"} <= set(B.outils_pour("mcp"))
              and {"modeles_lister", "modele_fiche"} <= set(B.outils_pour("realisateur"))
              and not {"modeles_lister", "modele_fiche"} & set(B.outils_pour("campagnes")))
        check("2.3 modele_fiche exige `cle`", ao.OUTILS["modele_fiche"]["schema"]["required"] == ["cle"])
        ctx = ao.Ctx(cid="t476")
        r = asyncio.run(ao.modeles_lister(ctx))
        check("2.4 modeles_lister sans nature : la liste des natures", r["ok"] and "video_i2v" in r["donnees"]["natures"])
        r = asyncio.run(ao.modeles_lister(ctx, nature="video_i2v"))
        mods = {m["id"]: m for m in r["donnees"]["modeles"]}
        check("2.5 modeles_lister(video_i2v) : modèles, prix, clé, famille de leur fiche",
              r["ok"] and mods["seedance-2"]["fiche"] == "essai" and mods["kling-v3-pro"]["fiche"] == "essai"
              and mods.get("wan-3.0", {}).get("fiche", "x") is None and "usd" in mods["seedance-2"], str(r)[:300])
        r = asyncio.run(ao.modeles_lister(ctx, nature="licorne"))
        check("2.6 nature inconnue : refus qui liste les natures", not r["ok"] and "video_i2v" in r["resume"])
        r = asyncio.run(ao.modele_fiche(ctx, cle="seedance-2"))
        check("2.7 modele_fiche par id : la fiche, texte présenté comme DONNÉE", r["ok"]
              and r["donnees"]["fiche"]["famille"] == "essai" and "DONNÉE" in r["resume"])
        r = asyncio.run(ao.modele_fiche(ctx, cle="essai", langue="en"))
        check("2.8 modele_fiche par famille, en anglais", r["ok"] and r["donnees"]["fiche"]["langue"] == "en")
        r = asyncio.run(ao.modele_fiche(ctx, cle="licorne"))
        check("2.9 modele_fiche inconnue : refus qui liste les fiches", not r["ok"] and "essai" in r["resume"])
    finally:
        MF.DOSSIER = origine
        shutil.rmtree(d, ignore_errors=True)

    print("[3] écran")
    sh, di = REPO / "frontend" / "shared", REPO / "frontend" / "dist" / "shared"
    for n in ("dz-fiche-modele.js", "dz-modeles-ia.js", "dz-champ-ia.js"):
        check(f"3.1 {n} : copie identique dans dist/shared", (sh / n).read_bytes() == (di / n).read_bytes())
    pages = [p for p in (REPO / "frontend").rglob("*.html") if "node_modules" not in p.parts]
    check("3.2 aucune page ne charge dz-fiche-modele.js par une balise (chargé au besoin)",
          not [p for p in pages if "dz-fiche-modele.js" in p.read_text(encoding="utf-8", errors="replace")])
    mi = (sh / "dz-modeles-ia.js").read_text(encoding="utf-8")
    check("3.3 DzModelesIA.select pose le « ? » (sauf fiche:false) en chargeant /shared/dz-fiche-modele.js",
          "if (opts.fiche !== false) ficheModele(el);" in mi and '"/shared/dz-fiche-modele.js"' in mi
          and "W.DzFicheModele.bouton(el)" in mi)
    ci = (sh / "dz-champ-ia.js").read_text(encoding="utf-8")
    check("3.4 pastille de dz-champ-ia : pied « fiche » caché par défaut, montré si la famille a une fiche",
          'pied.className = "dzia-fiche";' in ci and "pied.hidden = true;" in ci
          and "F.familleDe(cour).then(function (f) { if (f) pied.hidden = false; });" in ci
          and '"/shared/dz-fiche-modele.js"' in ci and "F.ouvrir(cour, b)" in ci)
    fm = (sh / "dz-fiche-modele.js").read_text(encoding="utf-8")
    check("3.5 dz-fiche-modele : sources /api/modeles/index et /api/modeles/fiche, langue de l'interface",
          '"/api/modeles/index?langue=" + langue()' in fm and '"/api/modeles/fiche?cle=" + encodeURIComponent(cle)' in fm)
    check("3.6 aucun rayon écrit (jetons de la charte)", not re.search(r"border-radius:\s*\d", fm)
          and "border-radius:var(--r)" in fm)
    inner = re.findall(r"\.innerHTML\s*=\s*([^;]+);", fm)
    check("3.7 innerHTML seulement du rendu échappé (rendre / esc)", inner and all(
        re.fullmatch(r"\s*rendre\(.*", x, re.S) for x in inner), str(inner))
    dico = (sh / "dz-i18n-dico.js").read_text(encoding="utf-8")
    check("3.8 clés modeles.fiche.* et agent.boites.modeles assemblées", all(
        f'"{k}"' in dico for k in ("modeles.fiche.ouvrir", "modeles.fiche.fermer", "modeles.fiche.titre",
                                   "modeles.fiche.erreur", "modeles.fiche.commun", "modeles.fiche.releve",
                                   "agent.boites.modeles")))

    import subprocess
    for t in ("fiche_modele.test.mjs", "modeles_ia.test.mjs"):
        r = subprocess.run(["node", str(sh / "qa" / t)], cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        check(f"3.9 node {t}", r.returncode == 0, (r.stdout + r.stderr)[-400:])

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
