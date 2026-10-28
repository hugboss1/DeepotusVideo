# -*- coding: utf-8 -*-
"""t312 (28/10/2026) (C1 Scan, tâche 2) — banc du nettoyage du texte lu (scan_nettoyage, module PUR).
Pages synthétiques : les boîtes des mots sont fabriquées (10 px par caractère, espace de 10 px, lignes de 20 px).
Ce que ce banc garde, par sections numérotées :
  1. incertain() : mots douteux marqués (l0rem, ####, wwww, a|b…), motifs connus non marqués (3e, XIVe, 1er, n°, 10kg…).
  2. depuis_marques() : [[?mot]] -> positions dans le texte sans marques.
  3. Colonnes : deux colonnes lues gauche puis droite ; trois colonnes ; une colonne à retraits = UNE colonne ;
     titre pleine largeur au-dessus de deux colonnes ; ligne fusionnée à travers la gouttière recoupée.
  4. Césures FR/EN : recon-/naître recollé, Jean-/Pierre et États-/Unis gardés, peut-/être et a-t-/il gardés en fr.
  5. Folios (12, — 3 —, XIV) et titres courants (répétés sur ≥ 2 pages) retirés ; titre présent une fois gardé ;
     page faite seulement de folios -> texte vide.
  6. Paragraphes : écart vertical, ligne courte finie par une ponctuation, retrait de première ligne ; suite d'une page à l'autre.
  7. Positions des mots incertains : pointent exactement dans le texte final (y compris un mot recollé par césure).
  8. Mode auto : passe au moins de mots incertains (égalité -> fr), mots lus différemment par les deux passes marqués.
  9. Bords : liste vide, page vide, page sans lignes, lignes sans boîtes, clés manquantes ; Unicode gardé ; module pur.
Aucun réseau, aucun fichier.
Run (depuis backend/) : & $PY tests/test_scan_nettoyage.py"""
import pathlib, sys, textwrap
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


CW, ESP, H = 10, 10, 20


def ligne(texte, x, y, h=H):
    mots, cx = [], x
    for t in texte.split():
        mots.append({"texte": t, "x": cx, "y": y, "l": len(t) * CW, "h": h})
        cx += len(t) * CW + ESP
    return {"texte": texte, "mots": mots}


def page(lignes, W=600, Hp=800, langue="fr"):
    return {"langue": langue, "angle": 0.0, "lignes": lignes, "largeur": W, "hauteur": Hp}


def colonne(texte, x, y0, car, pas=30):
    return [ligne(t, x, y0 + i * pas) for i, t in enumerate(textwrap.wrap(texte, car))]


from app.services import scan_nettoyage as N                        # noqa: E402

# ---------------------------------------------------------------------------------------------------------------
print("[1] incertain")
for m in ("l0rem", "####", "wwww", "a|b", "c0mme", "Zzzz", "mot~", "ab\\cd", "x{y}"):
    check(f"1 « {m} » incertain", N.incertain(m) is True)
for m in ("3e", "XIVe", "1er", "n°", "10kg", "10,5kg", "n°12", "2ème", "1990s", "14h30", "COVID-19", "A4", "MP3",
          "1000000", "aujourd'hui", "c’est", "«Bonjour»", "—", "»,", "États-Unis", "l’été.", "(voir", "10%", "21st",
          "1re", "3D", "m²", "mi-2020", "?", "…", "1914-1918", "dit-il.", "Ça"):
    check(f"1 « {m} » certain", N.incertain(m) is False)
check("1 vide/None -> certain", N.incertain("") is False and N.incertain(None) is False)

# ---------------------------------------------------------------------------------------------------------------
print("[2] depuis_marques")
check("2a le [[?chat]] dort", N.depuis_marques("le [[?chat]] dort") == ("le chat dort", [{"debut": 3, "fin": 7}]),
      N.depuis_marques("le [[?chat]] dort"))
t, p = N.depuis_marques("[[?Un]] deux [[?trois]].")
check("2b deux marques", t == "Un deux trois." and [t[q["debut"]:q["fin"]] for q in p] == ["Un", "trois"], (t, p))
check("2c sans marque", N.depuis_marques("rien ici") == ("rien ici", []))
check("2d marque vide retirée", N.depuis_marques("a [[?]]b") == ("a b", []), N.depuis_marques("a [[?]]b"))
t, p = N.depuis_marques("é « [[?été]] »")
check("2e Unicode", t == "é « été »" and t[p[0]["debut"]:p[0]["fin"]] == "été", (t, p))

# ---------------------------------------------------------------------------------------------------------------
print("[3] colonnes")
GAUCHE = ("Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike novembre oscar papa "
          "quebec romeo sierra tango")
DROITE = ("Uniforme victor whiskey xray yankee zoulou ambre bleu cerise dune ecorce fougere givre houle iris "
          "jade kaki lilas mauve nacre")
lg = colonne(GAUCHE, 60, 100, 38)
ld = colonne(DROITE, 520, 100, 38)
# mêlées dans l'ordre où l'OCR les rend souvent : ligne à ligne en travers
melees = [x for paire in zip(lg, ld) for x in paire]
r = N.nettoyer([page(melees, W=1000, Hp=1000)])
check("3a deux colonnes : gauche puis droite", r["texte"].split() == (GAUCHE + " " + DROITE).split(), r["texte"])
check("3b stats colonnes = 2", r["stats"]["colonnes"] == 2, r["stats"])

C1 = "un deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze quinze"
C2 = "seize dixsept dixhuit dixneuf vingt vingtun vingtdeux vingttrois vingtquatre vingtcinq"
C3 = "trente quarante cinquante soixante septante octante nonante cent mille million"
cols3 = colonne(C1, 50, 100, 30) + colonne(C2, 450, 100, 30) + colonne(C3, 850, 100, 30)
cols3.sort(key=lambda li: (li["mots"][0]["y"], li["mots"][0]["x"]))
r = N.nettoyer([page(cols3, W=1200, Hp=1000)])
check("3c trois colonnes dans l'ordre", r["texte"].split() == (C1 + " " + C2 + " " + C3).split(), r["texte"])
check("3d stats colonnes = 3", r["stats"]["colonnes"] == 3, r["stats"])

# une seule colonne, premières lignes en retrait (classique) : jamais deux colonnes
classique = []
y = 100
for i in range(12):
    x = 100 if i % 4 == 0 else 60          # retrait de 4 % de la largeur
    classique.append(ligne("mot " * 20 if i % 4 != 3 else "fin de paragraphe.", x, y)); y += 30
r = N.nettoyer([page(classique, W=1000, Hp=1000)])
check("3e une colonne à retraits -> 1 colonne", r["stats"]["colonnes"] == 1, r["stats"])

# une seule colonne, ADVERSAIRE : répliques courtes à gauche, lignes en fort retrait (19 %) à droite,
# un blanc vertical libre entre les deux -> sans le critère « lignes côte à côte » on croirait deux colonnes
adv, attendu, y = [], [], 100
for i in range(10):
    if i % 2 == 0:
        t = f"Oui{i} dit-il."; adv.append(ligne(t, 60, y))
    else:
        t = f"Et il reprit la route vers le nord sans un mot de plus ce soir {i} et"; adv.append(ligne(t, 250, y))
    attendu.append(t); y += 30
r = N.nettoyer([page(adv, W=1000, Hp=1000)])
check("3f une colonne adversaire -> 1 colonne", r["stats"]["colonnes"] == 1, r["stats"])
check("3g ... ordre des lignes gardé", r["texte"].split() == " ".join(attendu).split(), r["texte"])

# titre pleine largeur (centré, il traverse la gouttière) au-dessus de deux colonnes
titre = ligne("Chapitre premier de la grande histoire", 300, 40)
r = N.nettoyer([page([titre] + melees, W=1000, Hp=1000)])
check("3h titre puis gauche puis droite",
      r["texte"].split() == ("Chapitre premier de la grande histoire " + GAUCHE + " " + DROITE).split(), r["texte"])
check("3i titre en paragraphe à part", r["texte"].startswith("Chapitre premier de la grande histoire\n\n"), r["texte"][:60])

# l'OCR a fusionné les deux colonnes en une seule ligne : recoupée au grand blanc
fus = []
for a, b in zip(lg, ld):
    fus.append({"texte": a["texte"] + " " + b["texte"], "mots": a["mots"] + b["mots"]})
r = N.nettoyer([page(fus, W=1000, Hp=1000)])
check("3j lignes fusionnées à travers la gouttière recoupées",
      r["texte"].split() == (GAUCHE + " " + DROITE).split() and r["stats"]["colonnes"] == 2, r["texte"])

# ---------------------------------------------------------------------------------------------------------------
print("[4] césures")
pg = page([ligne("Il faut recon-", 60, 100), ligne("naître le travail de Jean-", 60, 130),
           ligne("Pierre et des États-", 60, 160), ligne("Unis en 1914-", 60, 190), ligne("1918 aujourd'hui.", 60, 220)])
r = N.nettoyer([pg])
check("4a recon-/naître, Jean-/Pierre, États-/Unis, 1914-/1918",
      r["texte"] == "Il faut reconnaître le travail de Jean-Pierre et des États-Unis en 1914-1918 aujourd'hui.", r["texte"])
check("4b stats cesures = 4", r["stats"]["cesures"] == 4, r["stats"])
pg = page([ligne("Il dit peut-", 60, 100), ligne("être, a-t-", 60, 130), ligne("il dit, celui-", 60, 160),
           ligne("ci et la for-", 60, 190), ligne("ce du mer-", 60, 220), ligne("ci c'est-à-", 60, 250), ligne("dire.", 60, 280)])
r = N.nettoyer([pg], langue="fr")
check("4c fr : peut-être, a-t-il, celui-ci gardés ; force, merci recollés ; c'est-à-dire",
      r["texte"] == "Il dit peut-être, a-t-il dit, celui-ci et la force du merci c'est-à-dire.", r["texte"])
pg = page([ligne("We must recog-", 60, 100), ligne("nize the work of Mary-", 60, 130), ligne("Jane today.", 60, 160)],
          langue="en")
r = N.nettoyer([pg], langue="en")
check("4d en : recog-/nize recollé, Mary-/Jane gardé", r["texte"] == "We must recognize the work of Mary-Jane today.",
      r["texte"])
pg = page([ligne("un tiret -", 60, 100), ligne("seul puis « mot-", 60, 130), ligne("« suite »", 60, 160)])
r = N.nettoyer([pg])
check("4e tiret isolé ou suite non alphanumérique : pas de recollage",
      r["texte"] == "un tiret - seul puis « mot- « suite »", r["texte"])

# ---------------------------------------------------------------------------------------------------------------
print("[5] folios et titres courants")
corps1 = [ligne("Le voyage commença en 12 jours de marche vers", 60, 100 + 30 * i) for i in range(3)]
p1 = page([ligne("XIV", 280, 40)] + corps1 + [ligne("12", 290, 760)])
p2 = page([ligne("la mer sans fin ni repos", 60, 100), ligne("— 3 —", 270, 760)])
r = N.nettoyer([p1, p2])
check("5a XIV en tête, 12 et — 3 — en pied retirés", "XIV" not in r["texte"] and "— 3 —" not in r["texte"]
      and not r["texte"].rstrip().endswith("12"), r["texte"])
check("5b « 12 » du corps gardé", "en 12 jours" in r["texte"], r["texte"])
check("5c stats folios_retires = 3", r["stats"]["folios_retires"] == 3, r["stats"])

tc1 = page([ligne("LE GRAND VOYAGE", 220, 30)] + [ligne("Première page du récit qui continue", 60, 100)] + [ligne("12", 290, 760)])
tc2 = page([ligne("LE GRAND VOYAGE", 220, 30)] + [ligne("et deuxième page du récit.", 60, 100)] + [ligne("13", 290, 760)])
r = N.nettoyer([tc1, tc2])
check("5d titre courant sur 2 pages retiré", "GRAND VOYAGE" not in r["texte"], r["texte"])
check("5e ... le récit continue d'une page à l'autre",
      r["texte"] == "Première page du récit qui continue et deuxième page du récit.", r["texte"])
check("5f stats titres_retires = 2, folios = 2", r["stats"]["titres_retires"] == 2 and r["stats"]["folios_retires"] == 2,
      r["stats"])
_t = ligne("LE GRAND VOYAGE", 240, 30)
_t["mots"].insert(0, {"texte": "12", "x": 180, "y": 30, "l": 20, "h": H}); _t["texte"] = "12    LE GRAND VOYAGE"    # blanc de 40 px > 1,5 × 20 px
tc1b = page([_t, ligne("Texte un.", 60, 100)])
_t2 = ligne("LE GRAND VOYAGE", 220, 30)
_t2["mots"].append({"texte": "13", "x": 410, "y": 30, "l": 20, "h": H}); _t2["texte"] = "LE GRAND VOYAGE    13"
tc2b = page([_t2, ligne("Texte deux.", 60, 100)])
r = N.nettoyer([tc1b, tc2b])
check("5g titre courant portant un folio séparé (gauche ou droite) retiré", r["texte"] == "Texte un. Texte deux.", r["texte"])
un1 = page([ligne("Préface", 260, 30), ligne("Texte un.", 60, 100)])
un2 = page([ligne("Chapitre", 260, 30), ligne("Texte deux.", 60, 100)])
r = N.nettoyer([un1, un2])
check("5h titre présent une seule fois gardé", "Préface" in r["texte"] and "Chapitre" in r["texte"]
      and r["stats"]["titres_retires"] == 0, r)
r = N.nettoyer([page([ligne("7", 290, 30), ligne("8", 290, 760)]), page([ligne("— 9 —", 270, 770)])])
check("5i pages faites seulement de folios -> texte vide", r["texte"] == "" and r["incertains"] == []
      and r["stats"]["folios_retires"] == 3, r)
r = N.nettoyer([page([ligne("12", 290, 400)])])
check("5j nombre seul au milieu de la page gardé", r["texte"] == "12", r)

# ---------------------------------------------------------------------------------------------------------------
print("[6] paragraphes")
L1 = "Le soleil se levait sur la ville endormie et"
L2 = "les rues restaient encore vides à cette heure"
L3 = "tranquille du matin sous un ciel très clair et"
L4 = "plus tard la foule arriva enfin sur la place"
pg = page([ligne(L1, 60, 100), ligne(L2, 60, 130), ligne(L3, 60, 160), ligne(L4, 60, 230), ligne(L2, 60, 260)])
r = N.nettoyer([pg])
check("6a écart vertical -> ligne vide", r["texte"] == f"{L1} {L2} {L3}\n\n{L4} {L2}", r["texte"])
pg = page([ligne(L1, 60, 100), ligne("fin de la phrase.", 60, 130), ligne(L2, 60, 160), ligne("ligne courte", 60, 190),
           ligne(L3, 60, 220)])
r = N.nettoyer([pg])
check("6b ligne courte finie par « . » -> paragraphe ; courte sans ponctuation -> suite",
      r["texte"] == f"{L1} fin de la phrase.\n\n{L2} ligne courte {L3}", r["texte"])
pg = page([ligne(L1, 60, 100), ligne(L2 + " là.", 60, 130), ligne(L3, 100, 160), ligne(L2, 60, 190)])
r = N.nettoyer([pg])
check("6c retrait de première ligne après une phrase finie -> paragraphe",
      r["texte"] == f"{L1} {L2} là.\n\n{L3} {L2}", r["texte"])
pg = page([ligne("« Viens ici », dit-il, et ils", 60, 100), ligne("partirent ensemble ; c’était l’été —", 60, 130),
           ligne("l’heure où tout s’apaise… Où ?", 60, 160)])
r = N.nettoyer([pg])
check("6d Unicode gardé tel quel (« », —, ’, …, accents)",
      r["texte"] == "« Viens ici », dit-il, et ils partirent ensemble ; c’était l’été — l’heure où tout s’apaise… Où ?"
      and r["incertains"] == [], r)

# ---------------------------------------------------------------------------------------------------------------
print("[7] positions des mots incertains")
pg = page([ligne("Le l0rem ipsum, wwww. puis", 60, 100), ligne("#### et c0m-", 60, 130), ligne("me le . chat", 60, 160),
           ligne("Quoi ? — Oui | non.", 60, 190)])
r = N.nettoyer([pg])
vus = [r["texte"][q["debut"]:q["fin"]] for q in r["incertains"]]
check("7a positions exactes", vus == ["l0rem", "wwww", "####", "c0mme", ".", "|"], (vus, r["texte"]))
check("7b stats incertains", r["stats"]["incertains"] == 6, r["stats"])
check("7c positions croissantes et dans le texte", all(0 <= q["debut"] < q["fin"] <= len(r["texte"]) for q in r["incertains"])
      and [q["debut"] for q in r["incertains"]] == sorted(q["debut"] for q in r["incertains"]), r["incertains"])
r2 = N.nettoyer([page([ligne("un l0rem", 60, 100)]), page([ligne("deux wwww.", 60, 100)])])
vus = [r2["texte"][q["debut"]:q["fin"]] for q in r2["incertains"]]
check("7d positions justes à travers deux pages", vus == ["l0rem", "wwww"], (vus, r2["texte"]))
check("7e stats mots et lignes", r2["stats"]["mots"] == 4 and r2["stats"]["lignes"] == 2 and r2["stats"]["pages"] == 2,
      r2["stats"])

# ---------------------------------------------------------------------------------------------------------------
print("[8] mode auto")
fr = [page([ligne("Le l0rem est ici", 60, 100)], langue="fr")]
en = [page([ligne("Le lorem est ici", 60, 100)], langue="en")]
r = N.nettoyer(fr, langue="auto", autre=en)
check("8a passe au moins d'incertains gardée (en)", r["texte"] == "Le lorem est ici" and r.get("langue") == "en", r)
fr = [page([ligne("Il a été là hier", 60, 100)], langue="fr")]
en = [page([ligne("Il a ete la hier", 60, 100)], langue="en")]
r = N.nettoyer(fr, langue="auto", autre=en)
check("8b égalité -> fr", r["texte"] == "Il a été là hier" and r.get("langue") == "fr", r)
vus = [r["texte"][q["debut"]:q["fin"]] for q in r["incertains"]]
check("8c mots lus différemment par les deux passes marqués", vus == ["été", "là"], vus)
r = N.nettoyer(en, langue="auto", autre=fr)
check("8d égalité -> fr même passée en « autre »", r["texte"] == "Il a été là hier" and r.get("langue") == "fr", r)
decale = [page([ligne("Il a ete", 60, 100), ligne("la hier", 60, 400)], langue="en")]
r = N.nettoyer(fr, langue="auto", autre=decale)
vus = [r["texte"][q["debut"]:q["fin"]] for q in r["incertains"]]
check("8e mot sans vis-à-vis dans l'autre passe : pas marqué", vus == ["été"], vus)
r = N.nettoyer(fr, langue="fr")
check("8f sans autre passe : rien de marqué", r["incertains"] == [] and r.get("langue") == "fr", r)

# ---------------------------------------------------------------------------------------------------------------
print("[9] bords")
VIDE_STATS = {"pages", "lignes", "mots", "incertains", "colonnes", "folios_retires", "titres_retires", "cesures"}
r = N.nettoyer([])
check("9a liste vide -> texte vide", r["texte"] == "" and r["incertains"] == [] and set(r["stats"]) >= VIDE_STATS, r)
r = N.nettoyer([page([])])
check("9b page vide -> texte vide sans erreur", r["texte"] == "" and r["stats"]["pages"] == 1
      and r["stats"]["colonnes"] == 0, r)
r = N.nettoyer([{"lignes": [{"texte": "", "mots": []}, {"mots": [{"texte": "  "}]}]}])
check("9c lignes vides / clés manquantes", r["texte"] == "", r)
r = N.nettoyer([{"lignes": [{"texte": "texte sans boîtes"}, {"texte": "deuxième ligne"}]}])
check("9d lignes sans boîtes : texte gardé dans l'ordre", r["texte"].split() == "texte sans boîtes deuxième ligne".split(), r)
r = N.nettoyer([{"lignes": [{"mots": [{"texte": "a", "x": "x", "y": None, "l": float("nan"), "h": -3}]}]}])
check("9e nombres invalides tolérés", r["texte"] == "a", r)
r = N.nettoyer(None)
check("9f None -> texte vide", r["texte"] == "", r)
src = pathlib.Path(N.__file__).read_text(encoding="utf-8")
check("9g module pur (ni sous-processus, ni fichier, ni réseau)",
      not any(m in src for m in ("subprocess", "open(", "requests", "httpx", "socket", "pathlib", "import os")))

# ---------------------------------------------------------------------------------------------------------------
print("[10] revue de la tâche 2 : titres courants, double interligne, romains")
r = N.nettoyer([page([ligne("Chapitre 1", 250, 30), ligne("Texte un.", 60, 100)]),
                page([ligne("Chapitre 2", 250, 30), ligne("Texte deux.", 60, 100)])])
check("10a « Chapitre 1 » / « Chapitre 2 » gardés (chiffres dans la clé)",
      "Chapitre 1" in r["texte"] and "Chapitre 2" in r["texte"] and r["stats"]["titres_retires"] == 0, r)
r = N.nettoyer([page([ligne("Non.", 60, 30), ligne("Texte un.", 60, 100)]),
                page([ligne("Non.", 60, 30), ligne("Texte deux.", 60, 100)])])
check("10b « Non. » en tête de deux pages gardé (trop court pour un titre courant)",
      r["texte"].count("Non.") == 2 and r["stats"]["titres_retires"] == 0, r)


def tete_folio(titre, folio, x=150, y=30, blanc=40):
    li = ligne(titre, x, y)
    fin = li["mots"][-1]["x"] + li["mots"][-1]["l"]
    li["mots"].append({"texte": folio, "x": fin + blanc, "y": y, "l": len(folio) * CW, "h": H})
    li["texte"] += "    " + folio
    return li


r = N.nettoyer([page([tete_folio("Le Rouge et le Noir", "17"), ligne("Julien entra dans la", 60, 100)]),
                page([tete_folio("Le Rouge et le Noir", "18"), ligne("chambre sans bruit.", 60, 100)])])
check("10c titre courant avec folio nettement séparé retiré",
      r["texte"] == "Julien entra dans la chambre sans bruit." and r["stats"]["titres_retires"] == 2, r)
r = N.nettoyer([page([tete_folio("Le Rouge et le Noir", "17", blanc=10), ligne("Julien entra.", 60, 100)]),
                page([tete_folio("Le Rouge et le Noir", "18", blanc=10), ligne("Il sortit.", 60, 100)])])
check("10d chiffre collé au titre (espace normal) : clés différentes, gardés", r["stats"]["titres_retires"] == 0
      and "Le Rouge et le Noir 17" in r["texte"], r)
D1 = "Le soleil se levait sur la ville endormie et"
dbl = page([ligne(D1, 60, 100), ligne("les rues restaient vides à cette heure recon-", 60, 148),
            ligne("naissable du matin sous un ciel très clair et", 60, 196), ligne(D1, 60, 244),
            ligne("plus tard la foule arriva enfin sur la place", 60, 340), ligne(D1, 60, 388)])
r = N.nettoyer([dbl])
check("10e double interligne : pas de paragraphe par ligne, césure recollée, vrai blanc = paragraphe",
      r["texte"] == f"{D1} les rues restaient vides à cette heure reconnaissable du matin sous un ciel très clair et "
                    f"{D1}\n\nplus tard la foule arriva enfin sur la place {D1}", r["texte"])
r = N.nettoyer([page([ligne("Le récit se termine ici sans", 60, 100), ligne("Dix.", 60, 760)])])
check("10f « Dix. » en pied de page gardé (romains en majuscules seulement)", r["texte"].endswith("Dix.")
      and r["stats"]["folios_retires"] == 0, r)
r = N.nettoyer([page([ligne("XIV", 280, 40), ligne("Texte.", 60, 100)])])
check("10g « XIV » en tête toujours retiré", r["texte"] == "Texte." and r["stats"]["folios_retires"] == 1, r)

print(f"\n{ok} PASS, {fail} FAIL")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
