# -*- coding: utf-8 -*-
"""Card Forge — série Wałkuski : LA MISE AU TON DÉTERMINISTE (phase 6, T1).

Le levier de formulation est ÉPUISÉ (3 réécritures, part claire 0,002→0,485,
jamais dans la bande) : le générateur n'obéit pas aux consignes tonales. La
passe de mise au ton corrige APRÈS coup, en local, gratuitement — une courbe
de niveaux (noir/blanc/gamma) visant LES GRANDEURS QUE LE JUGE MESURE
(`tons.*` de `style_walkuski.mesurer`), jamais un juge relâché.

Trois contrats, dans l'ordre des dettes :

  1. LE JUGE NE CHANGE PAS. `tonales()` est une EXPOSITION de ce que
     `mesurer` calcule déjà (mêmes nombres, prouvé), la fiche et `verifier`
     restent intouchés — la barre prouvée 2× reste la barre.
  2. LA VOIE NE PAIE RIEN DE PLUS. Un candidat refusé aux seuls axes tonals
     gagne UN frère mis au ton, jugé comme les autres ; la sentinelle compte
     zéro appel réel supplémentaire et la dépense ne bouge pas d'un centime.
  3. LE RESCAPAGE DIT SA COUVERTURE. Le mapping candidat→case vient du
     JOURNAL (la graine FLUX est `fnv1a32("walkuski:" + case)`, déterministe) ;
     ce qui n'est pas mappable est COMPTÉ, jamais tu. Dry-run par défaut,
     `{"appliquer": true}` pour servir, idempotent, `delta_usd=0.0`.

Run : .\\scripts\\run-tests.ps1  (un processus par fichier — la règle) ou
      python -m pytest tests/test_cards_serie_ton.py -x -q
"""
import io
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(__file__))

# L'ENV DU BANC EST CELUI DE `test_cards_face` : l'import pose le dossier de
# données TEMPORAIRE (donc aucune vraie clé — config charge DATA_ROOT/.env en
# override AVANT Settings), le magasin d'images du banc, et fournit l'atelier
# (toiles synthétiques mesurées), la sentinelle et le client API en process.
import test_cards_face as TF                                    # noqa: E402

from PIL import Image, ImageEnhance                             # noqa: E402

from test_cards_face import (_api, _deck, _lancer, _sentinelle,  # noqa: E402
                             _serie_neuve, _settings, _Atelier, FA)

SW = FA._juge_module()

TONALES_CLES = ("L_p05", "L_p50", "L_p95", "etendue_p05_p95",
                "part_sombre_L_moins_64", "part_claire_L_plus_200")
TONALES_CRITIQUES = {"part claire (L>200)", "L median"}


def _toile_trop_claire() -> Image.Image:
    """Le vista_pines du banc : une toile CONFORME sur-éclairée ×2, mesurée
    HORS STYLE 81,2 aux rouges exactement `part claire + L median` — le
    profil des cases que la campagne a perdues faute d'obéissance tonale du
    générateur. La précondition est MESURÉE par le test qui s'en sert : une
    fixture qui ne prouve pas sa nature est un témoin-couvercle."""
    return ImageEnhance.Brightness(TF._toile_conforme()).enhance(2.0)


def _toile_tons_au_corpus() -> Image.Image:
    """Une toile dont TOUS les contrôles sont DANS (mesurée 100 % au juge) :
    la ×1,35 de la conforme — la conforme elle-même garde un L_p95 en bande
    jaune, ce qui laisserait à la passe quelque chose à « améliorer »."""
    return ImageEnhance.Brightness(TF._toile_conforme()).enhance(1.35)


def _poser(im: Image.Image, nom: str) -> pathlib.Path:
    _settings.images_path.mkdir(parents=True, exist_ok=True)
    p = _settings.images_path / nom
    im.save(p, "PNG")
    return p


def _juge(p) -> dict:
    return FA.juger_image(p)


# ── 1. le juge exposé, pas changé ───────────────────────────────────────────

def test_tonales_expose_les_grandeurs_du_juge_sans_le_changer(tmp_path):
    """`style_walkuski.tonales(image)` rend EXACTEMENT le bloc `tons` que
    `mesurer` publie — mêmes clés, mêmes nombres. C'est le test d'or du
    refactor : si `mesurer` cessait de passer par là, les nombres
    divergeraient un jour et ce test le dirait."""
    p = tmp_path / "or.png"
    TF._toile_conforme().save(p, "PNG")
    m = SW.mesurer(str(p))
    t = SW.tonales(Image.open(p).convert("RGB"))
    assert set(t) == set(TONALES_CLES)
    for cle in TONALES_CLES:
        assert t[cle] == m["tons"][cle], cle


def test_la_toile_trop_claire_est_bien_le_cas_vista_pines(tmp_path):
    """LA PRÉCONDITION DU CHANTIER, mesurée : la fixture « trop claire » est
    refusée, et ses axes rouges sont TOUS tonals — le profil exact des cases
    que la campagne a perdues faute d'obéissance tonale du générateur."""
    p = tmp_path / "claire.png"
    _toile_trop_claire().save(p, "PNG")
    n = _juge(p)
    assert n["verdict"] != "TIENT"
    assert n["axes_rouges"], "sans axe rouge le cas ne teste rien"
    assert set(n["axes_rouges"]) <= TONALES_CRITIQUES, n["axes_rouges"]


# ── 2. la passe elle-même ───────────────────────────────────────────────────

def test_la_mise_au_ton_ramene_la_toile_trop_claire_dans_les_bandes(tmp_path):
    """La passe ramène les axes tonals rouges DANS le corpus : le frère
    ajusté n'a plus un seul axe rouge tonal, son score ne baisse pas, et le
    fichier écrit est un PNG RÉEL (pas les octets bruts du fournisseur)."""
    src = tmp_path / "claire.png"
    dst = tmp_path / "claire_ton.png"
    _toile_trop_claire().save(src, "PNG")
    avant = _juge(src)
    r = FA.mise_au_ton(src, dst, FA.fiche_style())
    assert r["applique"] is True
    assert dst.is_file()
    assert Image.open(dst).format == "PNG"
    assert set(r["axes_vises"]) and all(c.startswith("tons.")
                                        for c in r["axes_vises"])
    apres = _juge(dst)
    assert not (set(apres["axes_rouges"]) & TONALES_CRITIQUES), \
        apres["axes_rouges"]
    assert apres["score"] >= avant["score"]


def test_la_mise_au_ton_est_DETERMINISTE_a_l_octet(tmp_path):
    """Deux passes sur la même source rendent LES MÊMES OCTETS : aucune
    horloge, aucun aléa — c'est ce qui rend un rescapage rejouable et un
    banc honnête."""
    src = tmp_path / "claire.png"
    _toile_trop_claire().save(src, "PNG")
    d1, d2 = tmp_path / "a.png", tmp_path / "b.png"
    r1 = FA.mise_au_ton(src, d1, FA.fiche_style())
    r2 = FA.mise_au_ton(src, d2, FA.fiche_style())
    assert r1["applique"] and r2["applique"]
    assert r1["courbe"] == r2["courbe"]
    assert d1.read_bytes() == d2.read_bytes()


def test_la_mise_au_ton_laisse_en_paix_une_toile_aux_tons_au_corpus(tmp_path):
    """Rien à corriger → rien d'écrit. Une passe qui « améliorerait » une
    toile dont les tons sont déjà dans la bande verte fabriquerait des
    différences sans motif — et un jour, une régression silencieuse."""
    src = tmp_path / "ok.png"
    dst = tmp_path / "ok_ton.png"
    _toile_tons_au_corpus().save(src, "PNG")
    r = FA.mise_au_ton(src, dst, FA.fiche_style())
    assert r["applique"] is False, r
    assert not dst.exists()


# ── 3. la voie de campagne : un frère ajusté, zéro centime de plus ──────────

def test_la_voie_sert_la_case_par_le_frere_ajuste_sans_payer_plus(monkeypatch):
    """UN candidat trop clair : hier la case montait l'échelle (la marche de
    secours payée) et finissait refusée ; avec la passe, UN frère mis au ton
    TIENT et la case est servie AU PRIX DU SEUL TIR DE LA PREMIÈRE MARCHE.
    La sentinelle garde la porte : zéro appel réel, et l'espion des voies ne
    voit QUE Nano Banana Pro."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="trop_claire").pose(monkeypatch)
    at._GENRES = dict(_Atelier._GENRES, trop_claire=_toile_trop_claire)
    did = _deck()
    r = _lancer(f"/api/cards/{did}/face/serie/generer?limite=1")
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["traitees"]) == 1 and not d["refusees"], d
    t = d["traitees"][0]
    assert t["verdict"] == "TIENT"
    assert t["voie"] == "nano-banana-pro"
    assert t.get("mise_au_ton") is True
    assert [a[0] for a in at.appels] == ["nano-banana-pro"], at.appels
    m = json.loads((FA.serie_root() / "walkuski.json").read_text("utf-8"))
    case = t["case"]
    assert m["cases"][case]["mise_au_ton"] is True
    # le prix de la case est LE TIR DE LA PREMIÈRE MARCHE SEUL — la passe
    # est gratuite
    assert m["cases"][case]["prix_usd"] == FA.prix_usd("nano-banana-pro", 1)
    assert (_settings.images_path / m["cases"][case]["img"]).is_file()
    s.zero()


def test_la_voie_n_offre_pas_de_frere_aux_axes_non_tonals(monkeypatch):
    """Une toile saturée (chroma hors corpus) n'est PAS rescuable au ton : la
    passe ne doit même pas essayer — pas de faux espoir, pas de travail
    caché. L'échelle monte comme avant et la case est refusée comme avant."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    at = _Atelier(banana_pro="saturee", gpt="saturee").pose(monkeypatch)
    did = _deck()
    r = _lancer(f"/api/cards/{did}/face/serie/generer?limite=1")
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["refusees"]) == 1, d
    assert not d["traitees"]
    assert d["refusees"][0].get("mise_au_ton") is not True
    s.zero()


# ── 4. le rescapage du rebut ────────────────────────────────────────────────

def _case_du_banc() -> str:
    return FA.serie_cases()[0]


def _graine(case: str) -> int:
    return FA.fnv1a32("walkuski:" + case) & 0x7FFFFFFF


def _journal_du_banc(case: str, fichiers: list, seed: int) -> None:
    """Un journal au FORMAT RÉEL du 25/08 : la ligne `_payer` puis la ligne
    de sauvegarde FLUX avec sa graine — c'est elle qui porte le mapping."""
    d = pathlib.Path(os.environ["DEEPOTUS_DATA_DIR"]) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    noms = ", ".join("'" + f + "'" for f in fichiers)
    (d / "deepotus-2026-08-25.log").write_text(
        "2026-08-25 09:00:00.000 | INFO     | app.services.cards.face:_payer:"
        "1962 - cardforge/serie " + case + " : flux x6 = 0.0180 USD "
        "(cumul 0.0000 -> 0.0180, plafond 8.00)\n"
        "2026-08-25 09:00:05.000 | INFO     | app.api.routes:_flux_generate:"
        "4029 - FLUX: saved " + str(len(fichiers)) + " image(s), seed="
        + str(seed) + ": [" + noms + "]\n",
        encoding="utf-8")


def _rebut_du_banc(nom_dossier: str, contenus: dict) -> pathlib.Path:
    d = pathlib.Path(os.environ["DEEPOTUS_DATA_DIR"]) / nom_dossier
    d.mkdir(parents=True, exist_ok=True)
    for nom, im in contenus.items():
        # LES OCTETS BRUTS DU FOURNISSEUR : un JPEG sous extension .png,
        # exactement ce que le rebut réel contient (vérifié le 25/08).
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=92)
        (d / nom).write_bytes(buf.getvalue())
    return d


def test_le_parseur_du_journal_mappe_par_la_graine(tmp_path):
    """L'unité du mapping : la graine FLUX identifie la case (`g` et `g+1`
    pour les lots 4+2), un seed inconnu est compté non mappé."""
    case = _case_du_banc()
    g = _graine(case)
    lignes = [
        "... - FLUX: saved 4 image(s), seed=" + str(g) +
        ": ['gen_aaaa1111.png', 'gen_bbbb2222.png', 'gen_cccc3333.png', "
        "'gen_dddd4444.png']",
        "... - FLUX: saved 2 image(s), seed=" + str(g + 1) +
        ": ['gen_eeee5555.png', 'gen_ffff6666.png']",
        "... - FLUX: saved 1 image(s), seed=424242: ['gen_09090909.png']",
    ]
    mapping, non_mappes = FA.journal_vers_cases(lignes)
    assert mapping["gen_aaaa1111.png"] == case
    assert mapping["gen_eeee5555.png"] == case
    assert len([f for f, c in mapping.items() if c == case]) == 6
    assert non_mappes == ["gen_09090909.png"]


def test_le_rescapage_dry_run_ne_touche_a_rien_et_dit_sa_couverture(
        monkeypatch):
    """SANS corps, la route RAPPORTE : les candidats mappés, les non-mappés,
    les absents — et n'écrit RIEN (ni magasin, ni manifeste). Le patron
    devis-avant-dépense, transposé à une route qui MODIFIE sans dépenser."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    case = _case_du_banc()
    did = _deck()
    # une campagne passée : la case refusée, 7 $ déjà au registre
    FA.manifeste_fusionner(case, {"case": case, "score": 65.0,
                                  "verdict": "HORS STYLE", "voie": "flux",
                                  "prix_usd": 0.138, "at": "2026-08-25T09:00:00Z",
                                  "axes_rouges": ["part claire (L>200)"],
                                  "motif": "banc"}, gagnee=False,
                           delta_usd=7.0)
    _journal_du_banc(case, ["gen_aaaa1111.png", "gen_bbbb2222.png",
                            "gen_absente77.png"], _graine(case))
    _rebut_du_banc("rebut_banc", {
        "gen_aaaa1111.png": _toile_trop_claire(),
        "gen_bbbb2222.png": TF._toile_saturee(),
        "gen_hors9999.png": TF._toile_saturee(),   # dans le rebut, pas au journal
    })
    r = _api("POST", f"/api/cards/{did}/face/serie/rescaper",
             json={"dossier": "rebut_banc"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["applique"] is False
    assert d["cases"][case]["candidats"] == 2          # les deux présentes
    assert d["fichiers_absents"] == 1                  # gen_absente77
    assert d["candidats_non_mappes"] == 1              # gen_hors9999
    assert not d.get("gagnees")
    m = json.loads((FA.serie_root() / "walkuski.json").read_text("utf-8"))
    assert case in m["refus"] and not m["cases"]
    assert m["depense_totale_usd"] == 7.0
    s.zero()


def test_le_rescapage_applique_sert_sans_un_centime_et_reste_idempotent(
        monkeypatch):
    """`{"appliquer": true}` : la case dont un candidat mis au ton TIENT est
    SERVIE — PNG réel au magasin, `prix_usd: 0.0`, refus popé — et la
    dépense totale NE BOUGE PAS. Un second POST ne sert rien deux fois. Le
    rebut, lui, n'est PAS modifié : sa suppression appartient à
    l'utilisateur."""
    s = _sentinelle(monkeypatch)
    _serie_neuve()
    case = _case_du_banc()
    did = _deck()
    FA.manifeste_fusionner(case, {"case": case, "score": 65.0,
                                  "verdict": "HORS STYLE", "voie": "flux",
                                  "prix_usd": 0.138, "at": "2026-08-25T09:00:00Z",
                                  "axes_rouges": ["part claire (L>200)"],
                                  "motif": "banc"}, gagnee=False,
                           delta_usd=7.0)
    _journal_du_banc(case, ["gen_aaaa1111.png", "gen_bbbb2222.png"],
                     _graine(case))
    reb = _rebut_du_banc("rebut_banc", {
        "gen_aaaa1111.png": _toile_trop_claire(),
        "gen_bbbb2222.png": TF._toile_saturee(),
    })
    avant_rebut = sorted(p.name for p in reb.iterdir())
    r = _api("POST", f"/api/cards/{did}/face/serie/rescaper",
             json={"dossier": "rebut_banc", "appliquer": True})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["applique"] is True
    assert case in d["gagnees"], d
    g = d["gagnees"][case]
    assert g["verdict"] == "TIENT" and g["mise_au_ton"] is True
    m = json.loads((FA.serie_root() / "walkuski.json").read_text("utf-8"))
    assert case in m["cases"] and case not in m["refus"]
    c = m["cases"][case]
    assert c["prix_usd"] == 0.0 and c["mise_au_ton"] is True
    assert c["voie"] == "flux"
    p = _settings.images_path / c["img"]
    assert p.is_file() and Image.open(p).format == "PNG"
    assert m["depense_totale_usd"] == 7.0, "le rescapage est GRATUIT"
    assert sorted(q.name for q in reb.iterdir()) == avant_rebut
    # idempotence : la case servie n'est pas resservie
    r2 = _api("POST", f"/api/cards/{did}/face/serie/rescaper",
              json={"dossier": "rebut_banc", "appliquer": True})
    assert r2.status_code == 200
    assert case in r2.json()["deja_servies"]
    assert not r2.json().get("gagnees")
    s.zero()


def test_le_rescapage_refuse_un_dossier_hors_liste_blanche(monkeypatch):
    """Le nom du dossier naît en fullmatch (`[A-Za-z0-9._-]+`) : une
    traversée (`..`, séparateurs) est un 400 français, jamais une lecture
    hors du dossier de données."""
    s = _sentinelle(monkeypatch)
    did = _deck()
    for mauvais in ("../ailleurs", "a/b", "a\\b", ""):
        r = _api("POST", f"/api/cards/{did}/face/serie/rescaper",
                 json={"dossier": mauvais})
        assert r.status_code == 400, (mauvais, r.status_code, r.text)
    s.zero()
