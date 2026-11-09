"""t489 (FDA) — les parties PURES du script scripts/banc_da_coherence.py (aucun tir, aucun réseau) :
devis, ΔE des palettes, synthèse des mesures, comptage du vote M7, règle de décision écrite avant le tir, page de vote.

Run: <python embarqué> backend/tests/test_banc_da.py
"""
import importlib.util
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
RACINE = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8")
spec = importlib.util.spec_from_file_location("banc_da", RACINE / "scripts" / "banc_da_coherence.py")
BD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BD)

ok = fail = 0


def check(nom, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {nom}")
    else:
        fail += 1
        print(f"  FAIL  {nom} {detail}")


print("\n[1] devis")
d2, d1 = BD.devis(BD.CORPUS_DEFAUT, 2), BD.devis(BD.CORPUS_DEFAUT, 1)
check("1.1 30 planches, 6 maîtres (3 personnages × (2 bras FLUX + 3 bras Nano) × 2)", d2["planches"] == 30
      and d2["maitres"] == 6, (d2["planches"], d2["maitres"]))
check("1.2 probable < au pire", d2["total_probable_usd"] < d2["total_pire_usd"], d2)
check("1.3 juger une seule répétition coûte moins", d1["total_pire_usd"] < d2["total_pire_usd"], (d1, d2))
check("1.4 avec une répétition jugée, le pire tient sous 10 $", d1["total_pire_usd"] <= 10.0, d1["total_pire_usd"])
check("1.5 juge à 0 répétition : aucune ligne de juge chiffrée",
      [l for l in BD.devis(BD.CORPUS_DEFAUT, 0)["lignes"] if l["libelle"].startswith("Juge")][0]["usd"] == 0)

print("\n[2] mesures pures")
p = [(200, 30, 30), (20, 20, 20), (240, 240, 240)]
check("2.1 ΔE de deux palettes identiques : 0", BD.delta_e_palettes(p, p) == 0.0)
check("2.2 ΔE d'une veste devenue bleue : grand", BD.delta_e_palettes(p, [(30, 30, 200), (20, 20, 20)]) > 20)
check("2.3 ΔE d'une palette vide : non mesuré (nan)", BD.delta_e_palettes([], p) != BD.delta_e_palettes([], p))
check("2.4 l'inspiration « @images/ » vise la Bibliothèque de l'utilisateur, en lecture",
      str(BD.chemin_inspiration("@images/gen_x.png")).replace("\\", "/").endswith("DeepotusVideoGenData/assets/images/gen_x.png")
      and BD.chemin_inspiration(None) is None)


def planche(perso, f, m, rep, m3, usd, m1g=0.8, m1d=0.8):
    return {"perso": perso, "fournisseur": f, "methode": m, "rep": rep, "planche": f"b_{perso}{f}{m}{rep}.png",
            "panneaux": {"face_front": "a"}, "usd": usd, "secondes": 10,
            "profondeurs": {"left": 2 if m == "actuel" else 1, "back": 2 if m == "actuel" else 1},
            "mesures": {"m1": {"left": m1g, "back": m1d}, "m2": {"left": 5.0}}, "m3": {"moyenne": m3}}


print("\n[3] synthèse et règle de décision")
base = [planche(pp, "flux", "actuel", r, 6.0, 0.10, 0.70, 0.70) for pp in ("a", "b") for r in (0, 1)]
neuf = [planche(pp, "flux", "ancre", r, 7.0, 0.11, 0.85, 0.85) for pp in ("a", "b") for r in (0, 1)]
syn = BD.synthese(base + neuf)
check("3.1 M3 moyen par bras", syn["flux|actuel"]["M3"] == 6.0 and syn["flux|ancre"]["M3"] == 7.0, syn)
check("3.2 M4 : la profondeur 2 n'existe qu'en « actuel »", syn["flux|actuel"]["M4_m1_prof2"] == 0.7
      and syn["flux|ancre"]["M4_m1_prof2"] is None and syn["flux|ancre"]["M4_m1_prof1"] == 0.85, syn)
vote = {"flux": {"ancre>actuel": {"neuf": 7, "ref": 3}}}
r = BD.decider(syn, vote)
check("3.3 +16,7 % M3, 70 % des votes, +10 % de coût : « ancre » REMPLACE", any("REMPLACE" in x for x in r), r)
r = BD.decider(syn, {"flux": {"ancre>actuel": {"neuf": 5, "ref": 5}}})
check("3.4 vote à 50 % : ne remplace pas", all("ne remplace pas" in x for x in r), r)
r = BD.decider(syn, None)
check("3.5 vote absent : ne remplace pas, et le dit", all("ne remplace pas" in x and "vote absent" in x for x in r), r)
cher = [dict(x, usd=0.13) for x in neuf]
r = BD.decider(BD.synthese(base + cher), vote)
check("3.6 coût +30 % : ne remplace pas", all("ne remplace pas" in x for x in r), r)
faible = [planche(pp, "flux", "ancre", rr, 6.4, 0.10) for pp in ("a", "b") for rr in (0, 1)]
r = BD.decider(BD.synthese(base + faible), vote)
check("3.7 gain M3 de 6,7 % (< 10 %) : ne remplace pas", all("ne remplace pas" in x for x in r), r)
mixte = [planche("a", "flux", "ancre", rr, 8.5, 0.10) for rr in (0, 1)] + \
        [planche("b", "flux", "ancre", rr, 5.5, 0.10) for rr in (0, 1)]
r = BD.decider(BD.synthese(base + mixte), vote)
check("3.8 un personnage pire de 8 % : ne remplace pas, malgré la moyenne", all("ne remplace pas" in x for x in r), r)

print("\n[4] vote M7")
v = {"flux|ancre>actuel|a|0": {"choix": "g", "neuf_a_gauche": True},
     "flux|ancre>actuel|b|0": {"choix": "d", "neuf_a_gauche": True},
     "flux|ancre>actuel|a|1": {"choix": "e", "neuf_a_gauche": False},
     "flux|ancre>actuel|b|1": {"choix": "d", "neuf_a_gauche": False}}
check("4.1 comptage : « égal » ne compte pas, le côté du neuf est démasqué",
      BD.vote_vers_compte(v) == {"flux": {"ancre>actuel": {"neuf": 2, "ref": 1}}}, BD.vote_vers_compte(v))
tmp = pathlib.Path(tempfile.mkdtemp())
BD.ecrire_vote(tmp, base + neuf)
page = (tmp / "vote.html").read_text(encoding="utf-8")
paires = json.loads(page.split("const P=")[1].split(";const V")[0])
check("4.2 une paire par (personnage, répétition) : 4", len(paires) == 4, len(paires))
check("4.3 l'écran ne montre que deux images et trois boutons : aucune étiquette de bras affichée",
      all(set(x) == {"id", "gauche", "droite", "neuf_a_gauche"} for x in paires)
      and "p.id" not in page.split("z.innerHTML=")[1].split(";")[0], paires[:1])
check("4.4 l'ordre gauche/droite varie (le neuf n'est pas toujours du même côté)",
      len({x["neuf_a_gauche"] for x in paires}) == 2, [x["neuf_a_gauche"] for x in paires])
check("4.5 le vote se télécharge en vote.json", "vote.json" in page)

print("\n[5] isolation (incident du 09/11 : le devis importait app.config avant l'isolation)")
src = (RACINE / "scripts" / "banc_da_coherence.py").read_text(encoding="utf-8")
corps_main = src.split("def main(")[1]
check("5.1 avec --confirme, l'isolation est posée AVANT le devis (premier import de app.config)",
      corps_main.index("preparer_isolation(dossier, lire_cles())") < corps_main.index("d = devis(corpus"))
corps_tir = src.split("async def tirer(")[1]
check("5.2 le tir vérifie l'isolation avant toute requête",
      corps_tir.index("verifier_isolation(dossier)") < corps_tir.index("AsyncClient("))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
