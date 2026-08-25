# -*- coding: utf-8 -*-
"""Le GC des jeux de banc (phase 6, T5) : l'outil qui DÉPLACE, jamais ne
supprime.

Les rondes de preuve des phases 1-5 ont laissé 2 110 jeux « Nouveau jeu »
(6,1 Go mesurés le 25/08) dans le magasin réel — les rondes adverses jouaient
contre le backend DÉPLOYÉ, et chaque preuve posait son deck. L'outil les
range dans un rebut daté, au patron du rebut de série : la suppression
définitive appartient à l'utilisateur, pas à un script.

LA CEINTURE EST DOUBLE, et chaque moitié se mesure ici :
  1. le NOM, exactement « Nouveau jeu » — pas « nouveau jeu », pas
     « Nouveau jeu 2 », pas « Nouveau jeu  » : l'utilisateur nomme ce qu'il
     garde, et l'inventaire du 25/08 l'a montré (les 96 jeux gardés portent
     TOUS un nom) ;
  2. ZÉRO référence externe — l'identifiant du jeu est cherché dans les
     octets de la base ET dans tout .json du dossier de données HORS le
     magasin de jeux lui-même et les rebuts (un id qui vit dans un graphe
     Studio, un post programmé ou un manifeste n'est pas un banc oublié).

Run : python -m pytest tests/test_gc_decks.py -q  (un processus par fichier)
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import pytest                                                   # noqa: E402

import gc_decks as GC                                           # noqa: E402

DATE = "2026-08-26"


def _jeu(racine: pathlib.Path, did: str, nom: str, poids_ko: int = 3) -> None:
    d = racine / "assets" / "outputs" / "decks" / did
    d.mkdir(parents=True)
    (d / "meta.json").write_text(
        json.dumps({"id": did, "name": nom}, ensure_ascii=False),
        encoding="utf-8")
    (d / "layers.bin").write_bytes(b"x" * (poids_ko * 1024))


def _donnees(tmp_path: pathlib.Path) -> pathlib.Path:
    """Un dossier de données de banc : quatre jeux, une base, un graphe."""
    r = tmp_path / "data"
    _jeu(r, "deck_aaaa0001", "Nouveau jeu")            # candidat
    _jeu(r, "deck_bbbb0002", "Vitrine Deepotus")       # gardé : nommé
    _jeu(r, "deck_cccc0003", "Nouveau jeu")            # gardé : cité en base
    _jeu(r, "deck_dddd0004", "Nouveau jeu")            # gardé : cité au graphe
    (r / "deepotus.db").write_bytes(
        b"sqlite blob ... deck_cccc0003 ... fin")
    g = r / "studio_graphs"
    g.mkdir(parents=True)
    (g / "mon_graphe.json").write_text(
        json.dumps({"nodes": [{"deck": "deck_dddd0004"}]}), encoding="utf-8")
    return r


def _ids_dans(dossier: pathlib.Path) -> set:
    return {p.name for p in dossier.iterdir() if p.is_dir()}


def test_le_dry_run_liste_sans_rien_ecrire(tmp_path):
    """SANS `deplacer`, l'outil RAPPORTE : le candidat, les gardés avec leur
    RAISON (nom, ou la référence qui les sauve) — et n'écrit RIEN : ni rebut,
    ni déplacement, pas un octet."""
    r = _donnees(tmp_path)
    avant = sorted(str(p) for p in r.rglob("*"))
    rap = GC.gc(r, deplacer=False, date=DATE)
    assert sorted(str(p) for p in r.rglob("*")) == avant
    assert rap["candidats"] == ["deck_aaaa0001"]
    assert rap["deplaces"] == []
    gardes = {g["id"]: g for g in rap["gardes"]}
    assert gardes["deck_bbbb0002"]["raison"] == "nomme"
    assert gardes["deck_cccc0003"]["raison"] == "reference"
    assert "deepotus.db" in gardes["deck_cccc0003"]["ou"]
    assert gardes["deck_dddd0004"]["raison"] == "reference"
    assert "mon_graphe.json" in gardes["deck_dddd0004"]["ou"]
    assert not (r / ("rebut_decks_" + DATE)).exists()


def test_le_deplacement_range_au_rebut_avec_son_pourquoi(tmp_path):
    """`deplacer=True` : le candidat part ENTIER dans le rebut daté (méta
    comprise), les trois gardés ne bougent pas, le `_POURQUOI.txt` dit le
    compte — et un second passage ne trouve plus rien (idempotent)."""
    r = _donnees(tmp_path)
    rap = GC.gc(r, deplacer=True, date=DATE)
    assert rap["deplaces"] == ["deck_aaaa0001"]
    reb = r / ("rebut_decks_" + DATE)
    assert (reb / "deck_aaaa0001" / "meta.json").is_file()
    assert (reb / "deck_aaaa0001" / "layers.bin").stat().st_size == 3 * 1024
    decks = r / "assets" / "outputs" / "decks"
    assert _ids_dans(decks) == {"deck_bbbb0002", "deck_cccc0003",
                                "deck_dddd0004"}
    pourquoi = (reb / "_POURQUOI.txt").read_text(encoding="utf-8")
    assert "1 jeu" in pourquoi and "Nouveau jeu" in pourquoi
    assert "suppression definitive" in pourquoi.lower().replace("é", "e")
    rap2 = GC.gc(r, deplacer=True, date=DATE)
    assert rap2["candidats"] == [] and rap2["deplaces"] == []


def test_l_outil_ne_supprime_JAMAIS_un_octet(tmp_path):
    """Le déplacement conserve TOUT : le compte de fichiers et la somme des
    octets du dossier de données sont IDENTIQUES avant et après — c'est la
    différence entre ranger et détruire."""
    r = _donnees(tmp_path)
    fichiers = [p for p in r.rglob("*") if p.is_file()]
    n0, o0 = len(fichiers), sum(p.stat().st_size for p in fichiers)
    GC.gc(r, deplacer=True, date=DATE)
    fichiers = [p for p in r.rglob("*") if p.is_file()]
    # +1 : le _POURQUOI.txt du rebut — rien d'autre ne naît ni ne meurt.
    assert len(fichiers) == n0 + 1
    assert sum(p.stat().st_size for p in fichiers) >= o0


def test_un_nom_presque_pareil_est_garde(tmp_path):
    """« nouveau jeu », « Nouveau jeu 2 », « Nouveau jeu  » (espace final),
    un méta illisible, un dossier hors forme deck_[0-9a-f]{8} : TOUS gardés.
    La liste blanche du GC naît exacte — un GC qui devine est un GC qui
    emporte le travail de quelqu'un."""
    r = tmp_path / "data"
    _jeu(r, "deck_eeee0005", "nouveau jeu")
    _jeu(r, "deck_ffff0006", "Nouveau jeu 2")
    _jeu(r, "deck_abab0007", "Nouveau jeu ")
    d = r / "assets" / "outputs" / "decks" / "deck_cdcd0008"
    d.mkdir(parents=True)
    (d / "meta.json").write_text("{pas du json", encoding="utf-8")
    h = r / "assets" / "outputs" / "decks" / "PasUnDeck"
    h.mkdir(parents=True)
    (h / "meta.json").write_text(json.dumps({"name": "Nouveau jeu"}),
                                 encoding="utf-8")
    rap = GC.gc(r, deplacer=True, date=DATE)
    assert rap["candidats"] == [] and rap["deplaces"] == []
    assert _ids_dans(r / "assets" / "outputs" / "decks") == {
        "deck_eeee0005", "deck_ffff0006", "deck_abab0007", "deck_cdcd0008",
        "PasUnDeck"}
    raisons = {g["id"]: g["raison"] for g in rap["gardes"]}
    assert raisons["deck_cdcd0008"] == "meta_illisible"
    assert raisons["PasUnDeck"] == "hors_forme"


def test_un_rebut_precedent_ne_sauve_pas_les_suivants(tmp_path):
    """Le balayage des références EXCLUT les rebuts : un id listé dans le
    `_POURQUOI.txt` d'un rangement précédent (ou dans un .json déplacé) ne
    compte pas comme une référence vivante — sinon le premier GC vaccinerait
    tous les suivants."""
    r = _donnees(tmp_path)
    GC.gc(r, deplacer=True, date="2026-08-25")
    _jeu(r, "deck_aaaa0001", "Nouveau jeu")   # un banc du même id renaît
    rap = GC.gc(r, deplacer=False, date=DATE)
    assert rap["candidats"] == ["deck_aaaa0001"]
