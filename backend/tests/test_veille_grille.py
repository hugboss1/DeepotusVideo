# -*- coding: utf-8 -*-
"""t352 (27/10/2026) : la grille AUTOMATIQUE de la veille (sans modèle, sans dépense) et le rapport (matrice, douleurs,
angles, forces, demandes, limites). Règles du skill veille-concurrents : tendance = 3 auteurs distincts au moins ;
angle seulement là où l'app le règle, preuve à l'appui ; une demande n'est jamais annoncée.
Run : & $PY tests/test_veille_grille.py   (depuis backend/, PYTHONUTF8=1)."""
import os, sys, tempfile, pathlib
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzt352_grille_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from app.services import veille_grille as G                # noqa: E402


def L(texte, concurrent="runway", source="hn", auteur="a1", score=None, url=None, date="2026-06-01T00:00:00Z"):
    return {"concurrent": concurrent, "source": source, "url": url or f"https://x/{hash(texte) & 0xffff}", "date": date,
            "auteur_hash": auteur, "texte": texte, "score": score, "requete": "q"}


print("[1] classer")
check("test_themes : les 14 codes de grille.md", len(G.THEMES) == 14 and G.THEMES[0] == "prix_credits")
c = G.classer(L("The credits burn so fast, way too expensive subscription"))
check("test_classer_prix_credits_fr_en : en", c["theme"] == "prix_credits" and c["polarite"] == "faiblesse", c)
c = G.classer(L("Les crédits partent en fumée, abonnement trop cher"))
check("test_classer_prix_credits_fr_en : fr", c["theme"] == "prix_credits" and c["polarite"] == "faiblesse", c)
check("test_classer : classement auto", c["classement"] == "auto" and c["chez_nous"] == "regle")
c = G.classer(L("Bad — the app crashes and support never answers", source="appstore-us", score=1))
check("test_note_appstore_polarite : 1 étoile = faiblesse", c["polarite"] == "faiblesse" and c["theme"] == "support_fiabilite", c)
c = G.classer(L("Love it — the quality of the video is amazing", source="appstore-us", score=5))
check("test_note_appstore_polarite : 5 étoiles = force", c["polarite"] == "force" and c["theme"] == "qualite_sortie", c)
c = G.classer(L("Total scam, I want a refund for the credits, cancelling now"))
check("test_intensite_3_remboursement", c["intensite"] == 3, c)
c = G.classer(L("Je demande le remboursement, c'est une arnaque"))
check("test_intensite_3_remboursement : fr", c["intensite"] == 3 and c["polarite"] == "faiblesse", c)
c = G.classer(L("The credits are a bit pricey"))
check("test_intensite : remarque = 1", c["intensite"] == 1, c)
c = G.classer(L("I wish they would add an export to Unity for sprites"))
check("test_demande", c["polarite"] == "demande" and c["theme"] in ("game_assets", "flux_travail"), c)
c = G.classer(L("Nice weather today"))
check("test_neutre : aucun thème", c["polarite"] == "neutre" and c["theme"] is None, c)
deja = dict(L("whatever"), theme="coherence", polarite="force", intensite=2, chez_nous="partiel", resume="r")
c = G.classer(deja)
check("test_classement_importe_conserve", c["theme"] == "coherence" and c["polarite"] == "force"
      and c["classement"] == "importe" and c["resume"] == "r", c)
check("test_classer : n'altère pas l'entrée", "classement" not in deja)
check("test_chez_nous : regle porte une preuve", all(v["preuve"] for v in G.CHEZ_NOUS.values() if v["statut"] == "regle"))
check("test_chez_nous : tous les thèmes", set(G.CHEZ_NOUS) == set(G.THEMES))

print("\n[2] rapport")
V = []
for i in range(4):   # prix : 4 auteurs, dont 1 en colère
    V.append(G.classer(L(f"credits too expensive {i}" + (" refund now" if i == 0 else ""), auteur=f"p{i}",
                         concurrent="runway" if i % 2 else "kling")))
for i in range(2):   # cohérence : 2 auteurs seulement → pas une tendance
    V.append(G.classer(L(f"the character changes between shots, not consistent {i}", auteur=f"c{i}")))
V.append(G.classer(L("Nice weather today", auteur="n")))
V.append(G.classer(L("Love the quality, amazing output", auteur="f1", source="appstore-us", score=5)))
for i in range(3):
    V.append(G.classer(L(f"please add better documentation and tutorials {i}, feature request", auteur=f"d{i}")))
V.append(G.classer(L("x " * 300 + " credits too expensive", auteur="p9")))
R = G.rapport(V, {"date": "2026-10-27", "espace_id": "e1", "brut": 20})
check("test_rapport : version et méta", R["version"] == 1 and R["date"] == "2026-10-27" and R["espace_id"] == "e1")
check("test_neutre_ecarte_du_rapport : gardés", R["volumes"]["gardes"] == len(V) - 1, R["volumes"])
check("test_rapport : brut repris", R["volumes"]["brut"] == 20)
check("test_rapport : classement auto", R["classement"] == "auto")
check("test_rapport : matrice f/F", R["matrice"]["kling"]["prix_credits"]["f"] == 2
      and R["matrice"]["runway"]["prix_credits"]["f"] == 3, R["matrice"])
d = {x["theme"]: x for x in R["douleurs"]}
check("test_tendance_trois_auteurs : prix retenu", "prix_credits" in d and d["prix_credits"]["auteurs"] == 5, d.keys())
check("test_tendance_trois_auteurs : cohérence écartée", "coherence" not in d)
check("test_douleurs : n3 compte la colère", d["prix_credits"]["n3"] == 1)
check("test_douleurs : concurrents", set(d["prix_credits"]["concurrents"]) == {"runway", "kling"})
check("test_citation_200_cars", all(len(ct["texte"]) <= 200 for x in R["douleurs"] for ct in x["citations"]))
check("test_citation : 3 au plus", all(len(x["citations"]) <= 3 for x in R["douleurs"]))
check("test_citation : sans auteur", all("auteur_hash" not in ct for x in R["douleurs"] for ct in x["citations"]))
check("test_angles_seulement_regle", R["angles"] and all(G.CHEZ_NOUS[a["theme"]]["statut"] == "regle" for a in R["angles"]))
check("test_angles : preuve", all(a["preuve"] for a in R["angles"]))
check("test_forces", any(f["theme"] == "qualite_sortie" for f in R["forces"]))
check("test_demandes_jamais_annoncees", R["demandes"] and all(x["statut"] == "a_decider" for x in R["demandes"]), R["demandes"])
check("test_limites : classement automatique signalé", any("automatique" in l for l in R["limites"]))
R2 = G.rapport([], {"date": "2026-10-27", "espace_id": "e1"})
check("test_rapport_vide", R2["volumes"]["gardes"] == 0 and R2["douleurs"] == [] and R2["angles"] == [])
imp = [dict(L("credits expensive", auteur=f"i{i}"), theme="prix_credits", polarite="faiblesse", intensite=2,
            chez_nous="regle") for i in range(3)]
R3 = G.rapport([G.classer(x) for x in imp], {"date": "2026-10-27", "espace_id": "e1"})
check("test_rapport : classement importé", R3["classement"] == "importe" and not any("automatique" in l for l in R3["limites"]))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
