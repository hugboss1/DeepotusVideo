# -*- coding: utf-8 -*-
"""t514 (RV4) et t496 (G6), 26/11/2026 — banc des contrôles PURS du script court (`script_court`).

Sections : 1. lignes et durée lue ; 2. les quatre contrôles (accroche en 3 s, une idée par ligne, fin sur un appel,
mêmes mots à l'écran) en FR et en EN ; 3. vérité des chiffres (fiche d'offre), distance (texte et empreinte), mots
interdits ; 4. controle.md ; 5. déterminisme (deux appels, même verdict).
Run (depuis backend/) : & $PY tests/test_script_court.py"""
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.services import script_court as SC          # noqa: E402
from app.services import inspiration_recette as IR   # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BON = [{"texte": "Tu paies encore chaque mois ?", "ecran": "chaque mois ?"},
       {"texte": "Deepotus se paie une seule fois, à vie.", "ecran": "une seule fois"},
       {"texte": "Le lien est dans la bio.", "ecran": "lien bio"}]


def run():
    print("[1] lignes, durée")
    check("1a texte -> lignes sans vides", [l["texte"] for l in SC.lignes_de("a b\n\n  c  d ")] == ["a b", "c d"])
    check("1b 8 mots à 160 mots/min = 3 s", SC.duree_lue("un deux trois quatre cinq six sept huit", 160) == 3.0)
    check("1c débit absurde borné à 60 mots/min", SC.duree_lue("un deux", 0.1) == 2.0)
    print("[2] quatre contrôles")
    r = SC.controler_script(BON)
    check("2a script conforme : ok, 3 lignes, durée", r["ok"] and r["lignes"] == 3 and r["duree_s"] > 0, r)
    r = SC.controler_script([{"texte": "Voici une très longue accroche qui prend vraiment beaucoup trop de temps"}] + BON[1:])
    check("2b accroche trop longue -> accroche KO", not r["controles"]["accroche"]["ok"] and r["controles"]["accroche"]["detail"]["secondes"] > 3)
    r = SC.controler_script([BON[0], {"texte": "C'est simple. Et c'est rapide."}, BON[2]])
    check("2c deux phrases dans une ligne -> une_idee KO (ligne 2)", not r["controles"]["une_idee"]["ok"]
          and r["controles"]["une_idee"]["detail"][0]["ligne"] == 2, r["controles"]["une_idee"])
    r = SC.controler_script([BON[0], {"texte": " ".join(["mot"] * 17)}, BON[2]])
    check("2d 17 mots dans une ligne -> une_idee KO", not r["controles"]["une_idee"]["ok"])
    r = SC.controler_script(BON[:2])
    check("2e fin sans appel -> appel KO", not r["controles"]["appel"]["ok"])
    r = SC.controler_script([{"texte": "Still paying monthly?"}, {"texte": "Grab it once, for life."}, {"texte": "Link in bio."}], langue="en")
    check("2f anglais : appel reconnu (link)", r["controles"]["appel"]["ok"] and r["ok"], r)
    r = SC.controler_script([BON[0], {"texte": "Deepotus se paie une seule fois.", "ecran": "-70 % GRATUIT"}, BON[2]])
    check("2g mots à l'écran non dits -> ecran KO avec les mots", not r["controles"]["ecran"]["ok"]
          and "gratuit" in r["controles"]["ecran"]["detail"][0]["mots"], r["controles"]["ecran"])
    check("2h script vide -> tout KO", not SC.controler_script([])["ok"])
    print("[3] vérité, distance, interdits")
    s = [{"texte": "Payé une fois 45 €, contre 99 $ par mois."}, {"texte": "Le lien est dans la bio."}]
    v = SC.controler_verite(s, [{"valeur": "45 €", "source": "page d'achat"}])
    check("3a chiffre absent de l'offre (99) signalé, 45 accepté", not v["ok"] and [x["chiffre"] for x in v["detail"]] == ["99$"], v)
    v = SC.controler_verite(s, [{"valeur": "45 €"}, {"valeur": "99 $"}])
    check("3b tous les chiffres sourcés -> ok", v["ok"], v)
    check("3c 1 500 et 1500 sont le même chiffre", SC.controler_verite([{"texte": "1 500 clients"}], [{"valeur": "1500"}])["ok"])
    src = "Tu paies chaque mois pour un outil que tu ouvres deux fois par semaine et personne ne te le dit"
    d = SC.controler_distance([{"texte": "Écoute : un outil que tu ouvres deux fois par semaine et personne ne te le dit"}], src)
    check("3d suite de 12 mots de la source -> distance KO", not d["ok"] and d["detail"]["suite"] >= 12, d)
    d = SC.controler_distance([{"texte": "Un outil que tu ouvres deux fois par semaine et personne ne te le dit"}], "",
                              IR.empreinte_texte(src))
    check("3e après la purge : l'empreinte suffit", not d["ok"] and d["detail"]["empreinte"], d)
    check("3f texte neuf -> distance ok", SC.controler_distance(BON, src)["ok"])
    i = SC.controler_interdits(BON, ["vie"])
    check("3g mot interdit trouvé", not i["ok"] and i["detail"] == ["vie"], i)
    check("3h sans interdits -> ok", SC.controler_interdits(BON, [])["ok"])
    print("[4] controle.md")
    md = SC.controle_md(SC.controler_script(BON[:2]), "fr", "Contrôle du Reel")
    check("4a titre, appel « à revoir », durée", md.startswith("# Contrôle du Reel") and "**Fin sur un appel** : à revoir" in md
          and "Durée lue estimée" in md, md)
    check("4b anglais", "**Hook within 3 s** : pass" in SC.controle_md(SC.controler_script(BON), "en"))
    print("[5] déterminisme")
    check("5a même entrée, même verdict", SC.controler_script(BON) == SC.controler_script(BON))


def test_script_court():
    run()
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    run()
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
