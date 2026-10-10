# -*- coding: utf-8 -*-
"""Le filtre gratuit du flux News (plan 2026-09-03, lot 1, P1).

Banc-miroir : il LIT le fichier de reglages ecrit sur le disque et la liste
rendue, jamais le code qui pretend les produire. Aucun reseau, aucun LLM.

Run (depuis backend/) : python tests/test_news_filter.py
"""
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp   # P1 #5 : jamais le .env ni le dossier news/ reels
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MAINTENANT = "2026-09-03T12:00:00+00:00"


def _item(titre, source="CoinDesk", heures=1, resume="", sid="s1"):
    t = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc) - timedelta(hours=heures)
    return {"id": titre[:8], "title": titre, "source_name": source,
            "source_id": sid, "summary": resume,
            "link": "https://x/" + titre[:4],
            "published": t.isoformat(timespec="seconds")}


def test_les_mots_cles_gardent_et_le_reste_tombe():
    from app.services import news_filter as F
    items = [_item("Bitcoin ETF outflows accelerate"),
             _item("Storm floods southern Spain")]
    reglages = dict(F.REGLAGES_DEFAUT, mots_cles=["bitcoin", "solana"])
    gardes, motifs = F.filtrer(items, reglages, maintenant=MAINTENANT)
    assert [i["title"] for i in gardes] == ["Bitcoin ETF outflows accelerate"]
    assert motifs["Storm fl"] == "hors mots-clés"


def test_une_source_noire_tombe_meme_si_elle_a_le_mot_cle():
    from app.services import news_filter as F
    items = [_item("Bitcoin ETF outflows accelerate", source="Spammy Feed")]
    reglages = dict(F.REGLAGES_DEFAUT, mots_cles=["bitcoin"],
                    sources_noires=["spammy feed"])
    gardes, motifs = F.filtrer(items, reglages, maintenant=MAINTENANT)
    assert gardes == []
    assert motifs[items[0]["id"]] == "source sur liste noire"


def test_un_mot_noir_dans_le_titre_ou_le_resume_tombe():
    from app.services import news_filter as F
    items = [_item("Bitcoin giveaway airdrop now"),
             _item("Bitcoin ETF flows", resume="a free giveaway inside")]
    reglages = dict(F.REGLAGES_DEFAUT, mots_noirs=["giveaway"])
    gardes, motifs = F.filtrer(items, reglages, maintenant=MAINTENANT)
    assert gardes == []
    assert set(motifs.values()) == {"mot sur liste noire"}


def test_la_fenetre_de_fraicheur_coupe_le_vieux():
    from app.services import news_filter as F
    items = [_item("Frais assez recent", heures=5),
             _item("Vieux de quatre jours", heures=100)]
    reglages = dict(F.REGLAGES_DEFAUT, fraicheur_h=48)
    gardes, motifs = F.filtrer(items, reglages, maintenant=MAINTENANT)
    assert [i["title"] for i in gardes] == ["Frais assez recent"]
    assert motifs["Vieux de"] == "hors fenêtre de fraîcheur"


def test_une_date_illisible_ne_fait_pas_tomber_l_article():
    from app.services import news_filter as F
    it = _item("Sans date lisible")
    it["published"] = "pas une date"
    gardes, _ = F.filtrer([it], dict(F.REGLAGES_DEFAUT), maintenant=MAINTENANT)
    assert len(gardes) == 1


def test_les_reglages_sont_relus_du_disque_tels_qu_ecrits():
    from app.services import news_filter as F
    F.ecrire_reglages({"mots_cles": ["Solana", "  BCE  "], "fraicheur_h": 12,
                       "sources_noires": [], "mots_noirs": ["giveaway"]})
    sur_disque = json.loads(F.chemin_reglages().read_text(encoding="utf-8"))
    assert sur_disque["mots_cles"] == ["solana", "bce"]
    assert sur_disque["fraicheur_h"] == 12
    relu = F.lire_reglages()
    assert relu["mots_cles"] == ["solana", "bce"]
    assert relu["mots_noirs"] == ["giveaway"]


def test_un_fichier_de_reglages_corrompu_rend_les_defauts():
    from app.services import news_filter as F
    F.chemin_reglages().write_text("{ pas du json", encoding="utf-8")
    assert F.lire_reglages() == F.REGLAGES_DEFAUT


def test_une_fraicheur_absurde_est_bornee_a_l_ecriture():
    from app.services import news_filter as F
    F.ecrire_reglages(dict(F.REGLAGES_DEFAUT, fraicheur_h=100000))
    assert F.lire_reglages()["fraicheur_h"] == F.FRAICHEUR_MAX_H


# ── Tache 2 : le doublon, avec les couples qui ont FIXE les seuils ──────────

DOUBLONS = [
    ("Bitcoin tumbles below $60,000 as ETF outflows accelerate",
     "Bitcoin falls under $60,000 amid accelerating ETF outflows"),
    ("EU agrees landmark AI Act enforcement delay",
     "EU agrees to delay enforcement of landmark AI Act"),
    ("Fed holds rates steady, signals two cuts in 2026",
     "Federal Reserve holds rates steady and signals two cuts this year"),
    ("China unveils new stimulus package for property sector",
     "Beijing unveils fresh stimulus for the property sector"),
    ("Solana network hits record daily transactions",
     "Solana network hits record daily transactions"),
    ("Trump signs executive order on crypto reserve",
     "Trump signs an executive order creating a crypto reserve"),
    ("Ethereum Dencun upgrade goes live on mainnet",
     "Ethereum's Dencun upgrade is live on mainnet"),
    ("Nvidia beats earnings expectations, shares jump 8%",
     "Nvidia shares jump 8% after beating earnings expectations"),
    ("La BCE laisse ses taux inchanges et evoque deux baisses",
     "La BCE maintient ses taux inchanges, deux baisses evoquees"),
    # Les deux paires qui ont IMPOSE le tronconnage : sans lui, Jaccard 0,250
    # et 0,333, donc deux doublons evidents manques.
    ("Oil prices climb on supply fears",
     "Oil price climbs on supply fear"),
    ("Argentina peso plunges after vote",
     "Argentine peso plunged after the vote"),
]

PAS_DOUBLONS = [
    ("Bitcoin tumbles below $60,000 as ETF outflows accelerate",
     "Bitcoin ETF inflows hit record high in January"),
    ("EU agrees landmark AI Act enforcement delay",
     "EU parliament debates AI Act amendments next week"),
    ("Trump signs executive order on crypto reserve",
     "Crypto reserve order draws criticism from senators"),
    ("Nvidia beats earnings expectations, shares jump 8%",
     "Nvidia supplier warns of chip shortage in 2026"),
    ("Ethereum Dencun upgrade goes live on mainnet",
     "Ethereum gas fees fall after Dencun upgrade"),
    ("La BCE laisse ses taux inchanges et evoque deux baisses",
     "Les marches europeens saluent la decision de la BCE"),
    ("Bitcoin tumbles below $60,000 as ETF outflows accelerate",
     "EU agrees landmark AI Act enforcement delay"),
    ("Fed holds rates steady, signals two cuts in 2026",
     "China unveils new stimulus package for property sector"),
    ("Nvidia beats earnings expectations, shares jump 8%",
     "Storm Bernard floods southern Spain, thousands evacuated"),
    ("Tesla recalls 12,000 vehicles over brake fault",
     "Tesla plans a factory in Mexico next year"),
]

# Deux paires SYNTHETIQUES : la seule maniere d'exercer la CONJONCTION. Sur
# les 21 paires reelles, chaque signal pris seul classe deja tout
# correctement ; sans ces deux-la, remplacer le `and` par un `or` ne ferait
# rougir aucun test (mesure du 03/09).
UNE_SEULE_CONDITION = [
    # ratio 0,839 mais Jaccard 0,000 : les caracteres se ressemblent, aucun
    # jeton n'est commun.
    ("Bitcoin rally halts trading floor",
     "Bitcona rallx haltz tradinq floov"),
    # Jaccard 0,600 mais ratio 0,475 : les jetons communs sont noyes sous
    # deux mots tres longs.
    ("Bitcoin ETF outflow",
     "Bitcoin ETF outflow internationalization supercalifragilistic"),
]

DEPECHE = ("The European Central Bank held its benchmark rate at 2.75 percent "
           "on Thursday and signalled two cuts before the end of the year, "
           "citing slowing core inflation and weak industrial output across "
           "the euro area. President Christine Lagarde told reporters the "
           "council was unanimous and that incoming data would guide the pace.")
REPRISE = ("BRUSSELS - The European Central Bank held its benchmark rate at "
           "2.75 percent on Thursday and signalled two cuts before the end of "
           "the year, citing slowing core inflation and weak industrial "
           "output across the euro area. Lagarde told reporters the council "
           "was unanimous.")
INDEPENDANT = ("Frankfurt policymakers left borrowing costs untouched this "
               "week, a decision widely expected by economists, while opening "
               "the door to easing later in 2026. Markets rallied modestly; "
               "bank shares led the gains as traders priced in a softer path "
               "for deposit rates through the autumn.")


def test_les_seuils_separent_les_deux_familles_avec_de_la_marge():
    """Le banc MESURE au lieu de croire : il recalcule les deux extremes et
    verifie que les seuils tombent dans le vide entre eux."""
    from app.services import news_filter as F
    d_ratio = min(F.ratio_titres(a, b) for a, b in DOUBLONS)
    d_jac = min(F.jaccard_titres(a, b) for a, b in DOUBLONS)
    n_ratio = max(F.ratio_titres(a, b) for a, b in PAS_DOUBLONS)
    n_jac = max(F.jaccard_titres(a, b) for a, b in PAS_DOUBLONS)
    assert round(d_ratio, 3) == 0.753, d_ratio
    assert round(n_ratio, 3) == 0.711, n_ratio
    assert round(d_jac, 3) == 0.417, d_jac
    assert round(n_jac, 3) == 0.333, n_jac
    assert n_ratio < F.SEUIL_TITRE < d_ratio
    assert n_jac < F.SEUIL_JETONS < d_jac


def test_chaque_paire_est_classee_du_bon_cote():
    from app.services import news_filter as F
    for a, b in DOUBLONS:
        assert F.titres_presque_identiques(a, b), (a, b)
    for a, b in PAS_DOUBLONS:
        assert not F.titres_presque_identiques(a, b), (a, b)


def test_la_conjonction_est_bien_exigee():
    """Les deux paires synthetiques passent UNE condition et ratent l'autre :
    elles doivent etre refusees. Sans ce test, remplacer le `and` par un `or`
    ne ferait rougir personne."""
    from app.services import news_filter as F
    a, b = UNE_SEULE_CONDITION[0]
    assert F.ratio_titres(a, b) >= F.SEUIL_TITRE
    assert F.jaccard_titres(a, b) < F.SEUIL_JETONS
    assert not F.titres_presque_identiques(a, b)
    a, b = UNE_SEULE_CONDITION[1]
    assert F.ratio_titres(a, b) < F.SEUIL_TITRE
    assert F.jaccard_titres(a, b) >= F.SEUIL_JETONS
    assert not F.titres_presque_identiques(a, b)


def test_le_tronconnage_rapproche_le_singulier_du_pluriel():
    """La mesure qui a impose _tronc : sans lui, Jaccard 0,250 sur une paire
    que tout le monde lit comme un doublon."""
    from app.services import news_filter as F
    assert round(F.jaccard_titres("Oil prices climb on supply fears",
                                  "Oil price climbs on supply fear"), 3) \
        == 0.667
    # Le tronconnage est GROSSIER, et c'est assume : `prices` devient `pric`
    # tandis que `price` reste `price`. Les deux ne se rejoignent donc PAS —
    # ce sont `climbs`/`climb` et `fears`/`fear` qui font remonter la paire de
    # 0,250 a 0,667. Un vrai lemmatiseur est hors stdlib ; ce banc fige le
    # comportement reel plutot qu'un comportement souhaite.
    assert F._tronc("prices") == "pric"
    assert F._tronc("price") == "price"
    assert F._tronc("climbing") == "climb"
    assert F._tronc("climbs") == "climb"
    assert F._tronc("es") == "es"          # racine trop courte : intacte
    assert F._tronc("gas") == "gas"        # trois lettres : pas de coupe


def test_le_recouvrement_de_contenu_attrape_la_reprise_de_depeche():
    from app.services import news_filter as F
    assert round(F.recouvrement(DEPECHE, REPRISE), 3) == 0.968
    assert round(F.recouvrement(DEPECHE, INDEPENDANT), 3) == 0.031
    assert F.SEUIL_CONTENU == 0.85
    assert F.contenus_se_recouvrent(DEPECHE, REPRISE)
    assert not F.contenus_se_recouvrent(DEPECHE, INDEPENDANT)


def test_un_corps_trop_court_ne_declenche_jamais_le_recouvrement():
    from app.services import news_filter as F
    court = "BCE taux inchanges deux baisses evoquees"
    assert F.recouvrement(court, court) == 1.0
    assert not F.contenus_se_recouvrent(court, court)


def test_le_dedoublonnage_garde_le_plus_recent_et_dit_qui_il_a_fondu():
    from app.services import news_filter as F
    vieux = _item("Bitcoin tumbles below $60,000 as ETF outflows accelerate",
                  source="CoinDesk", heures=6, sid="s1")
    recent = _item("Bitcoin falls under $60,000 amid accelerating ETF outflows",
                   source="Decrypt", heures=1, sid="s2")
    autre = _item("Storm Bernard floods southern Spain", heures=2, sid="s3")
    gardes, fondus = F.dedoublonner([vieux, recent, autre])
    assert [i["title"] for i in gardes] == [recent["title"], autre["title"]]
    assert gardes[0]["doublons"] == [{"source_name": "CoinDesk",
                                      "title": vieux["title"],
                                      "link": vieux["link"]}]
    assert fondus[vieux["id"]] == recent["id"]


def test_le_dedoublonnage_ne_mute_pas_les_articles_d_entree():
    from app.services import news_filter as F
    a = _item("Solana network hits record daily transactions", heures=2)
    b = _item("Solana network hits record daily transactions", heures=1,
              sid="s2")
    b["id"] = "autre-id"
    F.dedoublonner([a, b])
    assert "doublons" not in a and "doublons" not in b


def test_deux_articles_de_la_meme_source_ne_sont_pas_fondus():
    """Un fil qui republie sa propre depeche n'est pas un recoupement entre
    medias : le fondre masquerait un vrai doublon d'identifiant, deja traite
    en amont par news_service."""
    from app.services import news_filter as F
    a = _item("Solana network hits record daily transactions", heures=2,
              sid="s1")
    b = _item("Solana network hits record daily transactions", heures=1,
              sid="s1")
    b["id"] = "autre-id"
    gardes, _ = F.dedoublonner([a, b])
    assert len(gardes) == 2

# ── P1 #5 (28/09/2026) : dedoublonner sur signatures — memes decisions, temps borne ──

def _reference(items):
    """La version PAR PAIRES du plan (fonctions publiques) : le temoin."""
    from app.services import news_filter as F
    ordonnes = sorted(items, key=lambda x: str(x.get("published") or ""), reverse=True)
    gardes, fondus = [], {}
    for it in ordonnes:
        cible = None
        for g in gardes:
            if g.get("source_id") and g.get("source_id") == it.get("source_id"):
                continue
            if (F.titres_presque_identiques(g.get("title") or "", it.get("title") or "")
                    or F.contenus_se_recouvrent(F._corps(g), F._corps(it))):
                cible = g
                break
        if cible is None:
            gardes.append(dict(it, doublons=[]))
        else:
            cible["doublons"].append({"source_name": it.get("source_name") or "",
                                      "title": it.get("title") or "", "link": it.get("link") or ""})
            fondus[it.get("id")] = cible.get("id")
    return gardes, fondus


def _melange():
    """Toutes les paires du banc, chaque membre sur sa source, plus les corps."""
    out, n = [], 0
    for a, b in DOUBLONS + PAS_DOUBLONS + UNE_SEULE_CONDITION:
        for t in (a, b):
            n += 1
            it = _item(t, source=f"S{n}", heures=n % 40, sid=f"s{n}")
            it["id"] = f"i{n}"
            out.append(it)
    # la « reprise augmentee » : containment 1,0 avec la depeche mais Jaccard bas -- seule
    # elle distingue le containment d'un Jaccard (mutant M4 du 28/09, qui survivait sans elle)
    for k, corps in enumerate((DEPECHE, REPRISE, INDEPENDANT, DEPECHE + " " + INDEPENDANT)):
        # titres SANS rapport entre eux : la fusion ne peut venir que du corps
        titre = ("Alpha quartz meridian", "Boreal lantern cascade", "Cobalt harvest ledger",
                 "Delta orchard kiln")[k]
        it = _item(titre, source=f"C{k}", heures=k, resume=corps, sid=f"c{k}")
        it["id"] = f"c{k}"
        out.append(it)
    return out


def test_dedoublonner_rend_exactement_les_decisions_de_la_reference():
    from app.services import news_filter as F
    items = _melange()
    g1, f1 = F.dedoublonner(items)
    g0, f0 = _reference(items)
    assert f1 == f0 and len(f0) >= 13           # onze doublons, la reprise, la reprise augmentee
    assert F.recouvrement(DEPECHE, DEPECHE + " " + INDEPENDANT) == 1.0
    assert F.jaccard_titres(DEPECHE, DEPECHE + " " + INDEPENDANT) < F.SEUIL_CONTENU
    assert [g["id"] for g in g1] == [g["id"] for g in g0]
    assert [g["doublons"] for g in g1] == [g["doublons"] for g in g0]


def test_dedoublonner_450_articles_en_temps_borne():
    """18 sources x 25 = 450 articles au plus avant le plafond. La version par
    paires y passait ~28 s (12,3 s mesures sur 300 le 28/09)."""
    import time
    from app.services import news_filter as F
    items = []
    for i in range(450):
        it = _item(f"Depeche {i} sujet distinct numero {i * 7919 % 1000} "
                   f"mot{i % 37} terme{i % 53} cle{i % 11}",
                   source=f"S{i % 18}", heures=i % 48, sid=f"s{i % 18}",
                   resume=" ".join(f"corps{i}x{j}" for j in range(40)))
        it["id"] = f"n{i}"
        items.append(it)
    t = time.perf_counter()
    F.dedoublonner(items)
    assert time.perf_counter() - t < 5.0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
