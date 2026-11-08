# -*- coding: utf-8 -*-
"""t433 (lot M0 « Méthodes », 08/11/2026) — le catalogue des méthodes, ses routes et l'outil d'agent.

Conception : docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md (§3 agents, §5 où ça apparaît).
[1] données     knowledge/methodes.json à jour (scripts/methodes_construire.py --check) ; 94 méthodes, slugs uniques,
                chaque texte présent en FR ET EN avec les mêmes nombres d'étapes, contrôles, pièges, exemples ; chaque
                méthode a un agent connu, une famille connue, des écrans connus, une source scenario.com ; neuf agents
                métier + l'outil Arbitre, chacun avec au moins une méthode ; aucune phrase copiée du site
                (les accroches de l'index ne figurent dans aucun texte) ;
[2] service     lister (filtres cumulés, recherche sans accents, ordre par utilité), fiche (langue, inconnue -> None),
                repères (nombres cohérents) ;
[3] routes      GET /api/methodes, /reperes, /{slug} (404), langue en ;
[4] agent       methodes_lire (liste, fiche, inconnue) en lecture, boîte « methodes » déclarée par le seul agent « mcp »,
                registre sain, Campagnes inchangé.
Run : & $PY tests/test_methodes.py   (depuis backend/)
"""
import asyncio
import json
import pathlib
import subprocess
import sys

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


def main():
    from app.services import methodes as M
    C = M.catalogue()
    ms = C["methodes"]

    print("[1] données")
    r = subprocess.run([sys.executable, "-X", "utf8", str(REPO / "scripts" / "methodes_construire.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("1.1 knowledge/methodes.json à jour (construire --check)", r.returncode == 0, r.stdout + r.stderr)
    check("1.2 94 méthodes, slugs uniques", len(ms) == 94 and len({m["slug"] for m in ms}) == 94, len(ms))
    bil = all(m[k]["fr"] and m[k]["en"] for m in ms for k in ("titre", "resume", "illustration"))
    lst = all(len(m[k]["fr"]) == len(m[k]["en"]) and len(m[k]["fr"]) > 0 and all(m[k]["en"])
              for m in ms for k in ("etapes", "exemples"))
    lst2 = all(len(m[k]["fr"]) == len(m[k]["en"]) and all(m[k]["en"]) for m in ms for k in ("controles", "pieges"))
    check("1.3 chaque texte en FR et EN, mêmes nombres d'éléments", bil and lst and lst2)
    check("1.4 l'anglais n'est pas le français recopié (titres)",
          sum(1 for m in ms if m["titre"]["fr"] == m["titre"]["en"]) <= 3)
    check("1.5 agent, famille et écrans connus ; source scenario.com",
          all(m["agent"] in C["agents"] and m["famille"] in C["familles"] and m["ecrans"]
              and all(e in C["ecrans"] for e in m["ecrans"])
              and m["source"].startswith("https://www.scenario.com/explorations/") for m in ms))
    metiers = [a for a, d in C["agents"].items() if not d["outil"]]
    check("1.6 neuf agents métier + l'outil Arbitre, chacun avec au moins une méthode",
          len(metiers) == 9 and C["agents"]["arbitre"]["outil"] is True
          and all(d["nb"] >= 1 for d in C["agents"].values())
          and sum(d["nb"] for d in C["agents"].values()) == 94, {a: d["nb"] for a, d in C["agents"].items()})
    check("1.7 chaque famille appartient à exactement un agent",
          all(sum(f in d["familles"] for d in C["agents"].values()) == 1 for f in C["familles"]))
    check("1.8 utilité 1-5, effort S/M/L, licence MIT ou rien",
          all(1 <= m["valeur"] <= 5 and m["effort"] in ("S", "M", "L") and m["licence_skill"] in (None, "MIT")
              for m in ms))
    # Les accroches publiques de l'index de Scenario ne doivent figurer nulle part (droits : textes à nous)
    accroches = ["Hide the tile grid with Wang tiles", "One texture. Sixteen tiles. No grid",
                 "Ground that never shows its grid", "name the one change, then list what must stay",
                 "Lock one master photo per product"]
    brut = M.FICHIER.read_text(encoding="utf-8")
    check("1.9 aucune accroche du site recopiée", not any(a in brut for a in accroches),
          [a for a in accroches if a in brut])

    print("\n[2] service")
    tout = M.lister()
    check("2.1 lister sans filtre : 94, triées par utilité décroissante",
          len(tout) == 94 and all(tout[i]["valeur"] >= tout[i + 1]["valeur"] for i in range(93)))
    mo = M.lister(ecran="montage")
    check("2.2 filtre écran", mo and all("montage" in m["ecrans"] for m in mo) and len(mo) < 94, len(mo))
    cumul = M.lister(ecran="montage", agent="monteur")
    check("2.3 filtres cumulés", cumul and all(m["agent"] == "monteur" and "montage" in m["ecrans"] for m in cumul)
          and len(cumul) <= len(mo))
    check("2.4 recherche sans accents ni casse (« ETALONNAGE » trouve video-color-grade)",
          any(m["slug"] == "video-color-grade" for m in M.lister(q="ETALONNAGE")))
    check("2.5 recherche dans l'autre langue (« grading »)", any(m["slug"] == "video-color-grade" for m in M.lister(q="grading")))
    check("2.6 plusieurs mots = tous requis", M.lister(q="etalonnage zzzintrouvable") == [])
    f = M.fiche("edit-one-thing", "en")
    check("2.7 fiche en anglais : étapes, exemples, agent, écrans libellés",
          f and f["titre"] == next(m for m in ms if m["slug"] == "edit-one-thing")["titre"]["en"]
          and f["etapes"] and f["exemples"] and f["agent"] == "retoucheur" and f["ecrans_libelles"], f and f.keys())
    check("2.8 fiche inconnue -> None ; langue inconnue -> français",
          M.fiche("nexiste-pas") is None and M.fiche("edit-one-thing", "de")["titre"] ==
          next(m for m in ms if m["slug"] == "edit-one-thing")["titre"]["fr"])
    R = M.reperes("en")
    check("2.9 repères : total, familles (somme 94), dix agents, écrans avec leur vue",
          R["total"] == 94 and sum(x["nb"] for x in R["familles"]) == 94 and len(R["agents"]) == 10
          and all(x["vue"] for x in R["ecrans"]) and R["source"]["url"].startswith("https://www.scenario.com"))

    print("\n[3] routes")
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/methodes", params={"ecran": "spritelab", "langue": "en"})
    check("3.1 GET /api/methodes?ecran=spritelab&langue=en", r.status_code == 200 and r.json()["total"] >= 1
          and all("spritelab" in m["ecrans"] for m in r.json()["methodes"]), r.text[:200])
    r = c.get("/api/methodes/reperes")
    check("3.2 GET /api/methodes/reperes", r.status_code == 200 and r.json()["total"] == 94)
    r = c.get("/api/methodes/alter", params={"langue": "en"})
    check("3.3 GET /api/methodes/alter (en)", r.status_code == 200 and r.json()["slug"] == "alter"
          and r.json()["etapes"])
    check("3.4 slug inconnu -> 404", c.get("/api/methodes/nexiste-pas").status_code == 404)
    r = c.get("/methodes/")
    check("3.5 la page /methodes/ est servie", r.status_code == 200 and "methodes.js" in r.text, r.status_code)

    print("\n[4] l'outil d'agent")
    from app.services import agent_outils as ao
    from app.services import agent_boites as B
    check("4.1 boîte « methodes » : methodes_lire, agents « mcp » et Monteur (t435), pas sur le téléphone ; registre sain",
          B.BOITES.get("methodes") == {"libelle": "agent.boites.methodes", "outils": ["methodes_lire"],
                                       "agents": ["mcp", "monteur", "realisateur", "retoucheur", "declinaisons", "directeur_acteurs",
                                                  "publicitaire", "artiste_2d"], "mobile": False} and B.verifier() == [], B.verifier())
    check("4.2 methodes_lire est en lecture et visible de « mcp », pas de Campagnes",
          ao.OUTILS["methodes_lire"]["nature"] == "lecture" and "methodes_lire" in B.outils_pour("mcp")
          and "methodes_lire" not in B.outils_pour("campagnes"))
    ctx = ao.Ctx(cid="c1")
    r = asyncio.run(ao.methodes_lire(ctx, ecran="montage"))
    check("4.3 sans slug : la liste filtrée", r["ok"] and r["donnees"]["total"] == len(mo)
          and len(r["donnees"]["methodes"]) <= 30)
    r = asyncio.run(ao.methodes_lire(ctx, slug="auto-edit", langue="en"))
    check("4.4 avec slug : la fiche, textes présentés comme des données", r["ok"] and r["donnees"]["methode"]["slug"] == "auto-edit"
          and "DONNÉES" in r["resume"])
    r = asyncio.run(ao.methodes_lire(ctx, slug="inconnue"))
    check("4.5 slug inconnu : refus propre", r["ok"] is False)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
