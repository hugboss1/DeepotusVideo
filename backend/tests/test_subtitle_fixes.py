# -*- coding: utf-8 -*-
"""Les correctifs de la piste de sous-titres ne doivent JAMAIS casser le voisin.

Deux familles de tests, qui verrouillent les deux defauts trouves par la
critique du gauntlet :

1. **Le correctif qui fabrique le defaut suivant.** « Etirer a 1,35 s »
   poussait la fin du segment 1 au-dela du debut du segment 2 : 190 ms de
   chevauchement, cree par le bouton cense reparer, pendant que la carte du
   dessous avertissait deja que la frontiere etait trop serree. Les tests
   d'INVARIANT ci-dessous interdisent structurellement ce cas : appliquer
   n'importe quel plan de n'importe quel avertissement ne peut ni creer un
   chevauchement, ni resserrer une frontiere.

2. **L'avertissement ancre sur le mauvais segment.** Chaque code a son ancrage
   verrouille par un test nomme, sur une piste ou UN SEUL defaut existe et ou
   l'indice attendu est connu d'avance.

Lance seul (un processus par fichier, cf. scripts/run-tests.ps1) :
    python -m pytest backend/tests/test_subtitle_fixes.py -q
"""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.subtitle_service import (      # noqa: E402
    MIN_GAP, MIN_DURATION, apply_plan, check_quality, normalize_segments,
    plan_boundary, plan_stretch, room_after, room_before,
)

EPS = 1e-9


# ---------------------------------------------------------------------------
# outils de mesure
# ---------------------------------------------------------------------------

def _gaps(track) -> list[float]:
    segs = normalize_segments(track, sort=False, keep_empty=True)
    return [round(segs[i]["start"] - segs[i - 1]["end"], 6)
            for i in range(1, len(segs))]


def _tight(track, min_gap=MIN_GAP) -> int:
    """Nombre de frontieres sous le seuil (chevauchements compris)."""
    return sum(1 for g in _gaps(track) if g < min_gap - EPS)


def _overlaps(track) -> int:
    return sum(1 for g in _gaps(track) if g < -EPS)


def _plans(warns):
    """Tous les plans proposes a l'utilisateur : le principal ET la variante."""
    for w in warns:
        p = w.get("plan")
        if p and p.get("ok"):
            yield w, p
        if p and (p.get("alt") or {}).get("ok"):
            yield w, p["alt"]


# ---------------------------------------------------------------------------
# le corpus : des pistes reelles, avec de vrais defauts
# ---------------------------------------------------------------------------

#: LE cas de la critique, chiffres exacts du verdict : segment 1 trop dense
#: (il faudrait 1,35 s), segment 2 qui commence a 1,419 s, frontiere a 40 ms
#: deja sous le seuil entre les segments 2 et 3.
PISTE_CRITIQUE = [
    {"id": "a", "start": 0.259, "end": 1.109,
     "text": "Vingt-sept caracteres ici!"},
    {"id": "b", "start": 1.419, "end": 3.100, "text": "Le voisin de droite"},
    {"id": "c", "start": 3.140, "end": 5.000, "text": "Et le suivant encore"},
]

CORPUS = {
    "critique": PISTE_CRITIQUE,
    "chevauchement": [
        {"id": "a", "start": 0.0, "end": 3.0, "text": "Premier segment"},
        {"id": "b", "start": 2.0, "end": 5.0, "text": "Second segment"},
    ],
    "colles": [
        {"id": "a", "start": 0.0, "end": 1.0, "text": "Un"},
        {"id": "b", "start": 1.0, "end": 2.0, "text": "Deux"},
        {"id": "c", "start": 2.0, "end": 3.0, "text": "Trois"},
    ],
    "micro_segments": [
        {"id": "a", "start": 0.0, "end": 0.30, "text": "Trop bref"},
        {"id": "b", "start": 0.34, "end": 0.64, "text": "Aussi bref"},
        {"id": "c", "start": 0.68, "end": 0.98, "text": "Encore bref"},
    ],
    "trop_long": [
        {"id": "a", "start": 0.0, "end": 9.5,
         "text": "Une phrase qui reste beaucoup trop longtemps a l'ecran, "
                 "assez longue pour qu'on la coupe en deux morceaux nets."},
        {"id": "b", "start": 10.0, "end": 12.0, "text": "Ensuite"},
    ],
    "dense_sans_place": [
        {"id": "a", "start": 0.0, "end": 1.0,
         "text": "Quarante-huit caracteres tasses dans une seconde"},
        {"id": "b", "start": 1.04, "end": 3.0, "text": "Le voisin colle"},
    ],
    "trois_lignes": [
        {"id": "a", "start": 0.0, "end": 4.0, "text": "un\ndeux\ntrois"},
        {"id": "b", "start": 4.5, "end": 6.0, "text": "quatre"},
    ],
    "avec_un_vide": [
        {"id": "a", "start": 0.0, "end": 2.0, "text": "Premier"},
        {"id": "b", "start": 2.5, "end": 3.5, "text": ""},
        {"id": "c", "start": 3.54, "end": 5.0, "text": "Troisieme"},
    ],
    "desordre": [
        {"id": "a", "start": 4.0, "end": 6.0, "text": "Arrive en premier"},
        {"id": "b", "start": 0.0, "end": 2.0, "text": "Mais joue avant"},
    ],
}


# ===========================================================================
# 1. INVARIANTS — un correctif ne fabrique pas le defaut suivant
# ===========================================================================

@pytest.mark.parametrize("nom", sorted(CORPUS))
def test_aucun_plan_ne_cree_de_chevauchement(nom):
    piste = CORPUS[nom]
    avant_ov, avant_tight = _overlaps(piste), _tight(piste)
    warns = check_quality(piste, "standard")
    vus = 0
    for w, plan in _plans(warns):
        vus += 1
        apres = apply_plan(piste, plan)
        assert _overlaps(apres) <= avant_ov, (
            "%s / %s (%s) : le correctif cree un chevauchement — %s -> %s"
            % (nom, w["code"], plan["label"], _gaps(piste), _gaps(apres)))
        assert _tight(apres) <= avant_tight, (
            "%s / %s (%s) : le correctif resserre une frontiere — %s -> %s"
            % (nom, w["code"], plan["label"], _gaps(piste), _gaps(apres)))
    assert vus or not warns or all(
        not (x.get("plan") or {}).get("ok") for x in warns)


@pytest.mark.parametrize("nom", sorted(CORPUS))
def test_aucun_plan_ne_reduit_un_ecart_deja_sous_le_seuil(nom):
    """Le point precis du verdict : la frontiere a 40 ms ne doit pas devenir
    35 ms parce qu'on a repare la carte du dessus."""
    piste = CORPUS[nom]
    g0 = _gaps(piste)
    for w, plan in _plans(check_quality(piste, "standard")):
        # on ne compare que les pistes de meme longueur : une decoupe ou une
        # fusion change la liste des frontieres, l'invariant global
        # (`_tight`) s'en charge deja.
        g1 = _gaps(apply_plan(piste, plan))
        if len(g1) != len(g0):
            continue
        for k, (a, b) in enumerate(zip(g0, g1)):
            if a < MIN_GAP - EPS:
                assert b >= a - 1e-6, (
                    "%s / %s (%s) : frontiere %d deja serree (%.3f) reduite "
                    "a %.3f" % (nom, w["code"], plan["label"], k, a, b))


def test_le_cas_exact_du_verdict():
    """« Etirer a 1,35 s » poussait la fin a 01.609 alors que le voisin
    commence a 01.419. Le plan doit soit tenir dans le silence, soit annoncer
    ce qu'il fait au voisin — jamais mordre en silence."""
    w = [x for x in check_quality(PISTE_CRITIQUE, "standard")
         if x["code"] in ("debit_eleve", "debit_illisible")]
    assert w, "le segment 1 est bien trop dense"
    plan = w[0]["plan"]
    assert plan["ok"], plan.get("blocked")
    # la place libre avant le voisin vaut 1,419 - 0,08 - 1,109 = 230 ms
    segs = normalize_segments(PISTE_CRITIQUE, sort=False, keep_empty=True)
    assert room_after(segs, 0) == pytest.approx(0.23, abs=1e-6)
    apres = apply_plan(PISTE_CRITIQUE, plan)
    assert apres[0]["end"] <= PISTE_CRITIQUE[1]["start"] - MIN_GAP + 1e-6
    assert _overlaps(apres) == 0
    # le bouton annonce la duree REELLEMENT atteinte, pas celle qu'il rate
    atteinte = apres[0]["end"] - apres[0]["start"]
    assert plan["granted"] == pytest.approx(atteinte, abs=0.002)
    assert plan["label"].startswith("Étirer à")
    # il emprunte le silence des DEUX cotes, et le detaille avant le clic
    assert "230 ms de silence après" in plan["effect"]
    assert "de silence avant" in plan["effect"]
    assert "Aucun voisin ne bouge." in plan["effect"]
    assert plan["touches"] == []
    # la frontiere a 40 ms entre les cartes 2 et 3, elle, n'a pas bouge
    assert _gaps(apres)[1] == pytest.approx(_gaps(PISTE_CRITIQUE)[1], abs=1e-6)
    assert _tight(apres) <= _tight(PISTE_CRITIQUE)


def test_la_renegociation_apparait_quand_le_silence_ne_suffit_pas():
    """Meme cas, mais colle des deux cotes : le plan direct n'atteint pas la
    cible, il le dit, et la variante annonce le decalage des suivants."""
    piste = [{"start": 0.0, "end": 0.85, "text": "Vingt-sept caracteres ici!"},
             {"start": 0.93, "end": 3.10, "text": "Le voisin de droite"},
             {"start": 3.18, "end": 5.00, "text": "Et le suivant encore"}]
    w = [x for x in check_quality(piste, "standard")
         if x["code"] in ("debit_eleve", "debit_illisible")][0]
    plan = w["plan"]
    assert not plan["ok"] and "silence" in plan["blocked"]
    alt = plan["alt"]
    assert alt and alt["ok"] and "décale" in alt["effect"].lower()
    assert alt["touches"] == [1, 2]
    apres = apply_plan(piste, alt)
    assert _overlaps(apres) == 0 and _tight(apres) <= _tight(piste)
    assert apres[0]["end"] - apres[0]["start"] == pytest.approx(1.3, abs=0.01)


def test_pas_de_place_pas_de_bouton():
    """Quand rien ne respecte les contraintes, on le DIT au lieu de proposer
    un bouton qui ment."""
    piste = [{"start": 0.0, "end": 1.2, "text": "Un premier"},
             {"start": 1.28, "end": 2.0, "text": "Court et coince"},
             {"start": 2.08, "end": 4.0, "text": "Le troisieme"}]
    w = [x for x in check_quality(piste, "standard")
         if x["code"] == "trop_court" and x["index"] == 1]
    assert w
    plan = w[0]["plan"]
    assert not plan["ok"]
    assert plan["blocked"] and "silence" in plan["blocked"]
    assert plan["label"] == ""          # rien a cliquer
    # la renegociation, elle, existe et s'annonce
    assert plan["alt"] and plan["alt"]["ok"]
    assert "décale" in plan["alt"]["effect"].lower()


def test_separer_repartit_l_effort_et_le_dit():
    piste = [{"start": 0.0, "end": 3.0, "text": "Premier segment"},
             {"start": 2.0, "end": 5.0, "text": "Second segment"}]
    segs = normalize_segments(piste, sort=False, keep_empty=True)
    plan = plan_boundary(segs, 1)
    assert plan["ok"] and plan["action"] == "separer"
    assert plan["touches"] == [0]                  # le voisin bouge : on le dit
    assert "n°1" in plan["effect"] and "n°2" in plan["effect"]
    apres = apply_plan(piste, plan)
    assert apres[1]["start"] - apres[0]["end"] == pytest.approx(MIN_GAP, abs=1e-3)
    assert all(s["end"] - s["start"] >= MIN_DURATION - 1e-6 for s in apres)


def test_separer_impossible_propose_la_fusion_et_dit_pourquoi():
    piste = [{"start": 0.0, "end": 1.0, "text": "Trop court deja"},
             {"start": 0.9, "end": 1.9, "text": "Et l'autre aussi"}]
    segs = normalize_segments(piste, sort=False, keep_empty=True)
    plan = plan_boundary(segs, 1)
    assert not plan["ok"]
    assert "Fusionnez" in plan["blocked"]
    fus = plan["alt"]
    assert fus and fus["action"] == "fusionner"
    apres = apply_plan(piste, fus)
    assert len(apres) == 1
    assert apres[0]["text"] == "Trop court deja Et l'autre aussi"
    assert apres[0]["words"], "le calage par mot est refait, pas herite"
    assert apres[0]["words"][-1]["end"] == pytest.approx(1.9, abs=1e-3)


def test_decouper_ouvre_une_respiration_entre_les_morceaux():
    """Une decoupe brute colle les deux moities : le correctif fabriquerait
    l'avertissement `intervalle_court` suivant."""
    piste = CORPUS["trop_long"]
    w = [x for x in check_quality(piste, "standard") if x["code"] == "trop_long"]
    assert w
    plan = w[0]["plan"]
    assert plan["ok"] and plan["action"] == "decouper"
    assert "%d sous-titres" % plan["granted"] in plan["label"]
    apres = apply_plan(piste, plan)
    assert len(apres) == len(piste) + plan["granted"] - 1
    assert min(_gaps(apres)) >= MIN_GAP - 1e-6
    assert _tight(apres) == 0


@pytest.mark.parametrize("nom", sorted(CORPUS))
def test_un_plan_applique_fait_taire_son_avertissement(nom):
    """Un correctif qui laisse le meme avertissement en place est un bouton
    decoratif. Il n'y a qu'une exception, et elle est ANNONCEE : un
    etirement partiel, qui dit lui-meme « le probleme sera reduit, pas
    efface ».

    Ce test a attrape un vrai defaut de bord : un plan qui atteignait
    EXACTEMENT 1,000 s laissait `trop_court` se redeclencher, parce que le
    flottant rendait 0,9999999999999998.
    """
    piste = CORPUS[nom]
    avant = [x["code"] for x in check_quality(piste, "standard")]
    for w, plan in _plans(check_quality(piste, "standard")):
        if plan is not w["plan"]:
            continue                         # les variantes ont leur propre but
        if (plan["action"] == "etirer"
                and plan.get("granted", 0) < plan.get("requested", 0) - 0.005):
            assert "pas effacé" in plan["effect"], plan["effect"]
            continue
        apres = apply_plan(piste, plan)
        restants = [x["code"] for x in check_quality(apres, "standard")]
        assert restants.count(w["code"]) < avant.count(w["code"]), (
            "%s / %s (%s) reste apres son propre correctif"
            % (nom, w["code"], plan["label"]))


# ===========================================================================
# 2. ANCRAGE — chaque avertissement s'affiche sur LE segment qu'il mesure
# ===========================================================================

def _un(warns, code):
    got = [w for w in warns if w["code"] == code]
    assert len(got) == 1, "attendu 1 %s, obtenu %s" % (
        code, [w["code"] for w in warns])
    return got[0]


def test_ancrage_intervalle_court():
    """LE bug du verdict : « 60 ms depuis le segment precedent » s'affichait
    sur la carte 12 alors que le seul ecart de 60 ms precede la carte 13."""
    piste = [{"start": 0.0, "end": 1.0, "text": "Un"},          # 0
             {"start": 1.50, "end": 2.5, "text": "Deux"},       # 1
             {"start": 2.52, "end": 3.5, "text": "Trois"},      # 2  <- 20 ms
             {"start": 4.00, "end": 5.0, "text": "Quatre"},     # 3
             {"start": 5.06, "end": 6.0, "text": "Cinq"}]       # 4  <- 60 ms
    ws = [w for w in check_quality(piste, "standard")
          if w["code"] == "intervalle_court"]
    par_indice = {w["index"]: w for w in ws}
    assert sorted(par_indice) == [2, 4]
    a_60 = [w for w in ws if "60 ms" in w["message"]]
    assert len(a_60) == 1
    assert a_60[0]["index"] == 4, "l'ecart de 60 ms precede la carte n°5"
    assert a_60[0]["about"] == [3, 4]
    assert "n°4" in a_60[0]["message"]            # le partenaire est nomme
    assert "20 ms" in par_indice[2]["message"] and "n°2" in par_indice[2]["message"]


def test_ancrage_chevauchement():
    piste = [{"start": 0.0, "end": 2.0, "text": "Un"},
             {"start": 2.5, "end": 4.0, "text": "Deux"},
             {"start": 3.7, "end": 6.0, "text": "Trois"}]
    w = _un(check_quality(piste, "standard"), "chevauchement")
    assert w["index"] == 2, "ancre sur celui qui COMMENCE trop tot"
    assert w["about"] == [1, 2]
    assert "300 ms" in w["message"] and "n°2" in w["message"]


@pytest.mark.parametrize("code,piste,attendu", [
    ("trop_court",
     [{"start": 0.0, "end": 2.0, "text": "Assez long"},
      {"start": 3.0, "end": 5.0, "text": "Encore un"},
      {"start": 6.0, "end": 6.3, "text": "Bref"}], 2),
    ("trop_long",
     [{"start": 0.0, "end": 2.0, "text": "Court"},
      {"start": 3.0, "end": 12.0, "text": "Une phrase qui traine longtemps"}], 1),
    ("debit_illisible",
     [{"start": 0.0, "end": 3.0, "text": "Tranquille"},
      {"start": 4.0, "end": 5.0, "text": "x" * 40 + " tasse dans une seconde"}],
     1),
    ("trop_de_lignes",
     [{"start": 0.0, "end": 2.0, "text": "Une ligne"},
      {"start": 3.0, "end": 5.0, "text": "un\ndeux\ntrois"}], 1),
    ("texte_vide",
     [{"start": 0.0, "end": 2.0, "text": "Present"},
      {"start": 3.0, "end": 5.0, "text": "   "},
      {"start": 6.0, "end": 8.0, "text": "Present aussi"}], 1),
    ("duree_nulle",
     [{"start": 0.0, "end": 2.0, "text": "Bon"},
      {"start": 3.0, "end": 3.0, "text": "Nul"}], 1),
])
def test_ancrage_par_code(code, piste, attendu):
    w = _un(check_quality(piste, "standard"), code)
    assert w["index"] == attendu
    assert w["about"] == [attendu]
    assert w["seg_id"] == normalize_segments(
        piste, sort=False, keep_empty=True)[attendu]["id"]


def test_ancrage_mots_incoherents():
    piste = [{"start": 0.0, "end": 2.0, "text": "Un deux"},
             {"start": 3.0, "end": 5.0, "text": "trois quatre",
              "words": [{"w": "trois", "start": 2.0, "end": 3.5},
                        {"w": "quatre", "start": 3.5, "end": 5.0}]}]
    w = _un(check_quality(piste, "standard"), "mots_incoherents")
    assert w["index"] == 1 and w["about"] == [1]
    apres = apply_plan(piste, w["plan"])
    assert all(x["start"] >= 3.0 - 1e-6 for x in apres[1]["words"])
    assert not [x for x in check_quality(apres, "standard")
                if x["code"] == "mots_incoherents"]


def test_ancrage_ligne_trop_large():
    long_ = "Un titre beaucoup beaucoup trop long pour tenir sur la largeur"
    piste = [{"start": 0.0, "end": 3.0, "text": "Court"},
             {"start": 3.5, "end": 8.0, "text": long_}]
    w = _un(check_quality(piste, "pop", canvas=(1080, 1080)),
            "ligne_trop_large")
    assert w["index"] == 1 and w["about"] == [1]


def test_un_segment_vide_ne_decale_plus_les_indices():
    """La cause mecanique du mauvais ancrage : les segments vides etaient
    ecartes de la mesure, donc tous les indices suivants glissaient d'un cran
    par rapport aux cartes du panneau."""
    piste = [{"start": 0.0, "end": 2.0, "text": "Premier"},
             {"start": 2.5, "end": 3.5, "text": ""},          # <- vide
             {"start": 3.54, "end": 5.0, "text": "Troisieme"}]
    ws = check_quality(piste, "standard")
    vide = _un(ws, "texte_vide")
    assert vide["index"] == 1
    court = _un(ws, "intervalle_court")
    assert court["index"] == 2, "l'ecart de 40 ms precede bien la carte n°3"
    assert court["about"] == [1, 2]


def test_ancrage_avertissement_de_style():
    """Un avertissement de STYLE n'a pas d'indice — mais il dit sur QUELS
    segments il porte, pour qu'on puisse agir la ou ca se voit."""
    piste = [{"start": 0.0, "end": 2.0, "text": "Un"},
             {"start": 2.5, "end": 4.5, "text": "Deux"}]
    w = _un(check_quality(piste, "prime", karaoke=True),
            "fond_translucide_karaoke")
    assert w["index"] is None
    assert w["about"] == [0, 1]
    assert w["fix"] == {"champ": "back_opacity", "valeur": 1.0}


# ===========================================================================
# 3. HONNETETE DES LIBELLES
# ===========================================================================

def test_tout_plan_actif_porte_un_libelle_et_une_consequence():
    for nom, piste in CORPUS.items():
        for w, plan in _plans(check_quality(piste, "standard")):
            assert plan["label"].strip(), "%s / %s sans libelle" % (nom, w["code"])
            assert len(plan["effect"]) > 20, (
                "%s / %s : %r n'annonce pas ce qui va se passer"
                % (nom, w["code"], plan["effect"]))
            assert plan["action"], "%s / %s sans action nommee" % (nom, w["code"])
            # tout plan qui touche un voisin le nomme dans sa consequence
            if plan["touches"]:
                bas = plan["effect"].lower()
                assert ("décal" in bas or "n°" in plan["effect"]
                        or "fusion" in bas), (
                    "%s / %s deplace %s sans le dire : %r"
                    % (nom, w["code"], plan["touches"], plan["effect"]))


def test_tout_plan_bloque_dit_pourquoi():
    for nom, piste in CORPUS.items():
        for w in check_quality(piste, "standard"):
            p = w.get("plan")
            if p and not p["ok"]:
                assert p.get("blocked"), "%s / %s : bloque sans raison" % (
                    nom, w["code"])
                assert len(p["blocked"]) > 20


def test_etirer_annonce_la_duree_reellement_atteinte():
    """« Etirer a 1,35 s » doit produire 1,35 s, ou dire un autre chiffre."""
    for nom, piste in CORPUS.items():
        for w, plan in _plans(check_quality(piste, "standard")):
            if plan["action"] != "etirer":
                continue
            i = w["index"]
            apres = apply_plan(piste, plan)
            if len(apres) != len(normalize_segments(piste, sort=False,
                                                    keep_empty=True)):
                continue
            reel = apres[i]["end"] - apres[i]["start"]
            assert plan["granted"] == pytest.approx(reel, abs=0.003), (
                "%s / %s : annonce %s s, produit %.3f s"
                % (nom, w["code"], plan["granted"], reel))


# ===========================================================================
# 4. LA TRADUCTION VERS LE PANNEAU — c'est LA que l'ancrage se perdait
# ===========================================================================

def _ui(piste, style="standard", **kw):
    from app.api import routes as R
    segs = normalize_segments(piste, sort=False, keep_empty=True)
    raw = check_quality(piste, style, **kw)
    return R._subs_warnings_ui(raw, segs)


def test_la_route_ne_re_ancre_plus_les_regles_de_frontiere():
    """L'ancienne traduction déplaçait `intervalle_court` sur `index - 1` en
    laissant le message écrit du point de vue du segment suivant : « 60 ms
    depuis le segment précédent » atterrissait sur la carte d'avant."""
    piste = [{"start": 0.0, "end": 1.0, "text": "Un"},
             {"start": 1.5, "end": 2.5, "text": "Deux"},
             {"start": 3.0, "end": 4.0, "text": "Trois"},
             {"start": 4.06, "end": 5.0, "text": "Quatre"}]
    seg_w, _ = _ui(piste)
    ws = [w for w in seg_w if w["code"] == "intervalle_court"]
    assert len(ws) == 1
    assert ws[0]["i"] == 3, "la carte doit être celle qui commence trop tôt"
    assert "60 ms" in ws[0]["msg"] and "n°3" in ws[0]["msg"]
    assert ws[0]["about"] == [2, 3]
    # l'id voyage : le panneau n'a plus à se fier à une position
    assert ws[0]["id"] == normalize_segments(
        piste, sort=False, keep_empty=True)[3]["id"]


def test_la_route_transporte_le_plan_et_ses_consequences():
    seg_w, _ = _ui(CORPUS["chevauchement"])
    ch = [w for w in seg_w if w["code"] == "chevauchement"][0]
    p = ch["plan"]
    assert p["ok"] and p["label"] and p["effect"]
    assert p["ops"] and all("id" in o for o in p["ops"])
    assert p["touches"] == [0]


def test_les_avertissements_de_style_sortent_avec_un_geste():
    """Ils étaient calculés puis jetés faute d'index de segment. Ils n'en ont
    pas parce qu'ils portent sur le style : leur geste est un réglage de
    STYLE, dans le vocabulaire du panneau."""
    piste = [{"start": 0.0, "end": 2.0, "text": "Un"},
             {"start": 2.5, "end": 4.5, "text": "Deux"}]
    seg_w, style_w = _ui(piste, "prime", karaoke=True)
    assert not [w for w in seg_w if w["code"] == "fond_translucide_karaoke"]
    assert len(style_w) == 1
    w = style_w[0]
    assert w["about"] == [0, 1], "il dit sur quelles répliques il porte"
    assert w["fix"]["champ"] == "bgOpacity" and w["fix"]["valeur"] == 100
    assert w["fix"]["label"] and len(w["fix"]["effect"]) > 20


def test_plan_stretch_ne_prend_que_le_silence_libre():
    segs = normalize_segments(
        [{"start": 0.0, "end": 1.0, "text": "Un"},
         {"start": 1.5, "end": 3.0, "text": "Deux"}], sort=False,
        keep_empty=True)
    assert room_after(segs, 0) == pytest.approx(0.42, abs=1e-6)
    assert room_before(segs, 0) == 0.0
    p = plan_stretch(segs, 0, 3.0)
    assert p["ok"] and p["granted"] == pytest.approx(1.42, abs=1e-3)
    assert "1,42" in p["label"]
    assert p["touches"] == []
