# -*- coding: utf-8 -*-
"""Card Forge — P4 « Import CSV et mapping des champs ».

CHAQUE SEUIL CHIFFRÉ DE LA SPEC A SON TEST, et les nombres attendus sont
ÉCRITS EN DUR — ce sont ceux relevés sur la barre (nanDECK 1.29), pas ceux que
l'implémentation voudrait bien produire.

Les six seuils de la spec (§4, pièce 04) :

  1. CSV de 3 lignes avec `qty` 3/2/1  ->  deck de **6** cartes.
  2. Filtre `atk > 1` sur 4 lignes -> **3** lignes retenues ; combiné avec
     `qty` -> **10** cartes.
  3. **UTF-8 par défaut** : les accents français passent sans directive. (Chez
     nanDECK le défaut est l'ANSI : c'est le piège classique, « MÃ©lÃ©e ».)
  4. Séparateur détecté automatiquement sur les 3 cas `,` `;` tabulation,
     **sans question posée**.
  5. Mappage : 0 ligne de code ; les colonnes non mappées n'entrent pas dans
     la carte, les mappées remplissent `card.fields[slot]`.
  6. Import de 200 lignes en **moins de 2 s**.

Plus ce que la barre ne tient pas et qui doit être verrouillé ici :

  · le filtre n'est PAS un `eval` — aucune expression ne peut exécuter de code,
    et une faute de syntaxe rend la POSITION du caractère fautif ;
  · l'ordre filtre -> tri -> quantité (filtrer après duplication compterait
    juste mais dirait faux, trier après duplication séparerait les copies) ;
  · l'aller-retour export -> import rend la MÊME table ;
  · un corps mal formé fait 400, JAMAIS 500 (spec §2.5).

Run : .\\scripts\\run-tests.ps1 -Filter cards
"""
import asyncio
import os
import pathlib
import sys
import tempfile
import time

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                  # noqa: E402
from fastapi import HTTPException                              # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402

from app.services.cards import data as D                        # noqa: E402


# ═══════════════════════ les jeux d'essai, en dur ═══════════════════════════

# Seuil 1 — la parité LINKMULTI : 3 lignes, quantités 3/2/1 -> 6 cartes.
CSV_QTY = (
    "nom;qty\r\n"
    "Octopode;3\r\n"
    "Oracle;2\r\n"
    "Rebut;1\r\n"
)

# Seuil 2 — la parité LINKFILTER + LINKMULTI : 4 lignes, `atk > 1` en retient
# 3, et 3 + 2 + 5 = 10 cartes. (C'est la planche du relevé de la barre :
# 3 Octopode, 2 Oracle, 5 Rebut, l'Écho à atk 1 écarté.)
CSV_FILTRE = (
    "nom;atk;qty\r\n"
    "Octopode;7;3\r\n"
    "Oracle;2;2\r\n"
    "Rebut;9;5\r\n"
    "Echo;1;4\r\n"
)

ACCENTS = "Mêlée de tentacules — à côté, ça coûte 3 €"
CSV_ACCENTS = "nom;texte\r\nOctopode;" + ACCENTS + "\r\n"


def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


DID = "deck_00000000"
BASE = "/api/cards/" + DID + "/data"


def _parse(raw, **kw):
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return D.parse_table(raw, **kw)


def _build(table, **kw):
    return D.build_deck(table["columns"], table["rows"], **kw)


# ═══════════════ seuil 1 — qty 3/2/1 donne SIX cartes ═══════════════════════

def test_seuil_qty_3_2_1_donne_6_cartes():
    """« CSV de 3 lignes avec qty 3/2/1 -> deck de 6 cartes »."""
    t = _parse(CSV_QTY)
    assert t["n_rows"] == 3, f"3 lignes attendues, {t['n_rows']} lues"
    out = _build(t, mapping={"nom": "title"}, qty_col="qty")
    assert out["stats"]["n_cards"] == 6, \
        f"6 cartes attendues (3+2+1), {out['stats']['n_cards']} produites"
    noms = [c["fields"]["title"] for c in out["cards"]]
    assert noms.count("Octopode") == 3
    assert noms.count("Oracle") == 2
    assert noms.count("Rebut") == 1


def test_qty_absente_vaut_une_copie():
    """Sans colonne de quantité : une ligne = une carte. Et une CELLULE vide
    vaut 1 copie, pas 0 — la parité avec LINKMULTI se joue là."""
    t = _parse(CSV_QTY)
    assert _build(t)["stats"]["n_cards"] == 3
    t2 = _parse("nom;qty\r\nA;\r\nB;2\r\n")
    assert _build(t2, qty_col="qty")["stats"]["n_cards"] == 3


def test_qty_zero_retire_la_ligne():
    t = _parse("nom;qty\r\nA;0\r\nB;2\r\n")
    out = _build(t, mapping={"nom": "title"}, qty_col="qty")
    assert out["stats"]["n_cards"] == 2
    assert {c["fields"]["title"] for c in out["cards"]} == {"B"}


# ═════════ seuil 2 — filtre `atk > 1` : 3 sur 4, puis 10 cartes ═════════════

def test_seuil_filtre_atk_sup_1_retient_3_lignes_sur_4():
    t = _parse(CSV_FILTRE)
    assert t["n_rows"] == 4
    out = _build(t, expr="atk > 1")
    assert out["stats"]["n_kept"] == 3, \
        f"3 lignes retenues attendues, {out['stats']['n_kept']}"
    assert out["stats"]["filtered_out"] == 1


def test_seuil_filtre_plus_qty_donne_10_cartes():
    t = _parse(CSV_FILTRE)
    out = _build(t, mapping={"nom": "title"}, qty_col="qty", expr="atk > 1")
    assert out["stats"]["n_cards"] == 10, \
        f"10 cartes attendues (3+2+5), {out['stats']['n_cards']}"
    noms = [c["fields"]["title"] for c in out["cards"]]
    assert noms.count("Octopode") == 3
    assert noms.count("Oracle") == 2
    assert noms.count("Rebut") == 5
    assert "Echo" not in noms


def test_le_filtre_passe_AVANT_la_quantite():
    """L'ordre compte pour le COMPTE. Filtrer après duplication donnerait le
    même deck mais `n_kept` compterait des copies, pas des lignes — et c'est
    ce nombre-là que l'écran affiche."""
    t = _parse(CSV_FILTRE)
    out = _build(t, qty_col="qty", expr="atk > 1")
    assert out["stats"]["n_kept"] == 3          # des LIGNES
    assert out["stats"]["n_cards"] == 10        # des CARTES


@pytest.mark.parametrize("expr,attendu", [
    ("atk > 1", 3),
    ("atk >= 7", 2),
    ("atk = 9", 1),
    ("atk != 9", 3),
    ("atk > 1 et qty > 2", 2),
    ("atk > 8 ou qty = 2", 2),
    ("non (atk > 1)", 1),
    ("nom contient octo", 1),
    ("nom commence par O", 2),
    ("nom finit par t", 1),
    ("[atk] > 1", 3),                 # syntaxe nanDECK, acceptée telle quelle
    ("qty", 4),                       # valeur seule = « non vide et non nul »
    ("", 4),                          # pas de filtre
])
def test_grammaire_du_filtre(expr, attendu):
    t = _parse(CSV_FILTRE)
    assert _build(t, expr=expr)["stats"]["n_kept"] == attendu, \
        f"filtre {expr!r}"


def test_comparaison_numerique_pas_lexicographique():
    """« 10 » est plus grand que « 9 ». Un filtre qui compare des CHAÎNES
    dirait le contraire et le deck perdrait ses grosses créatures."""
    t = _parse("nom;atk\r\nA;9\r\nB;10\r\nC;2\r\n")
    assert _build(t, expr="atk > 9")["stats"]["n_kept"] == 1
    assert _build(t, expr="atk >= 9")["stats"]["n_kept"] == 2


def test_egalite_insensible_a_la_casse_et_aux_accents():
    t = _parse("nom;rarete\r\nA;Épique\r\nB;commune\r\n")
    assert _build(t, expr="rarete = epique")["stats"]["n_kept"] == 1
    assert _build(t, expr="rarete = ÉPIQUE")["stats"]["n_kept"] == 1


# ═════════ le filtre N'EST PAS un eval — la garantie de sécurité ════════════

@pytest.mark.parametrize("mechant", [
    "__import__('os').system('echo pwn')",
    "().__class__.__bases__[0].__subclasses__()",
    "exec('x=1')",
    "1;import os",
    "open('/etc/passwd').read()",
])
def test_le_filtre_ne_peut_pas_executer_de_code(mechant):
    """Aucune de ces expressions ne doit s'exécuter. Elles lèvent une
    FilterError (grammaire fermée) ou ne retiennent rien — jamais un effet."""
    t = _parse(CSV_FILTRE)
    try:
        out = _build(t, expr=mechant)
    except (D.FilterError, HTTPException):
        return
    assert out["stats"]["n_kept"] <= 4


def test_erreur_de_filtre_donne_la_position():
    """`LINKFILTER` de la barre dit « erreur ». Ici on dit OÙ."""
    with pytest.raises(D.FilterError) as ei:
        D.compile_filter("atk > ", ["atk"])
    assert isinstance(ei.value.pos, int) and ei.value.pos >= 0
    with pytest.raises(D.FilterError) as e2:
        D.compile_filter("atk > 1 et", ["atk"])
    assert e2.value.msg


def test_colonne_inconnue_entre_crochets_est_signalee():
    with pytest.raises(D.FilterError) as ei:
        D.compile_filter("[force] > 1", ["atk", "nom"])
    assert "force" in ei.value.msg


# ═══════════ seuil 3 — UTF-8 PAR DÉFAUT, sans aucune directive ══════════════

def test_seuil_utf8_par_defaut_sans_directive():
    """Le seuil exact : « UTF-8 par défaut, les accents français passent sans
    directive ». Aucun paramètre n'est donné à parse_table."""
    t = _parse(CSV_ACCENTS)
    assert t["encoding"] == "utf-8", t["encoding"]
    assert t["rows"][0][1] == ACCENTS, t["rows"][0][1]
    assert "Ã" not in t["rows"][0][1], "mojibake : le défaut n'est pas UTF-8"


def test_utf8_avec_bom():
    t = D.parse_table(b"\xef\xbb\xbf" + CSV_ACCENTS.encode("utf-8"))
    assert t["encoding"] == "utf-8-bom"
    assert t["columns"][0] == "nom", t["columns"]     # le BOM n'entre pas
    assert t["rows"][0][1] == ACCENTS


def test_cp1252_reconnu_et_accents_preserves():
    """L'ANSI n'est qu'un REPLI : on n'y tombe que si les octets ne sont pas
    de l'UTF-8 valide. Et alors les accents restent justes."""
    t = D.parse_table(CSV_ACCENTS.replace("€", "e").encode("cp1252"))
    assert t["encoding"] == "cp1252"
    assert "Mêlée de tentacules" in t["rows"][0][1], t["rows"][0][1]


def test_utf16_reconnu_par_son_bom():
    t = D.parse_table(CSV_ACCENTS.encode("utf-16"))
    assert t["encoding"] == "utf-16"
    assert t["rows"][0][1] == ACCENTS


def test_mojibake_signale_puis_reparable():
    """Un fichier DÉJÀ abîmé par un exportateur distrait.

    La recette exacte du dégât, dans l'ordre où il se produit dans la vraie
    vie : le texte est écrit en UTF-8, un programme relit ces octets comme du
    cp1252 (« Mêlée » devient « MÃªlÃ©e »), puis ré-enregistre en UTF-8. Le
    fichier est alors de l'UTF-8 PARFAITEMENT VALIDE — aucune détection
    d'encodage ne peut le rattraper — et c'est ce que la barre affiche tel
    quel. Ici on le SIGNALE, et la réparation est un bouton.
    """
    propre = "nom;texte\r\nOctopode;Mêlée à côté, ça coûte cher\r\n"
    raw = propre.encode("utf-8").decode("cp1252").encode("utf-8")
    t = D.parse_table(raw)
    assert t["encoding"] == "utf-8", t["encoding"]      # techniquement valide
    assert "MÃªlÃ©e" in t["rows"][0][1], t["rows"][0][1]
    assert t["mojibake"] is True, "les suites « Ã© » ne sont pas signalées"
    t2 = D.parse_table(raw, repair=True)
    assert t2["repaired"] is True
    assert t2["rows"][0][1] == "Mêlée à côté, ça coûte cher", t2["rows"][0][1]
    assert t2["mojibake"] is False


# ══════ seuil 4 — séparateur deviné sur les 3 cas, sans question posée ══════

@pytest.mark.parametrize("sep,nom", [
    (",", "virgule"), (";", "point-virgule"), ("\t", "tabulation"),
])
def test_seuil_separateur_detecte_sans_question(sep, nom):
    txt = sep.join(["nom", "atk", "qty"]) + "\r\n" \
        + sep.join(["Octopode", "7", "3"]) + "\r\n" \
        + sep.join(["Oracle", "2", "2"]) + "\r\n"
    t = _parse(txt)                       # aucun paramètre : rien n'est demandé
    assert t["sep"] == sep, f"{nom} : séparateur {t['sep']!r}"
    assert t["sep_label"] == nom
    assert t["columns"] == ["nom", "atk", "qty"]
    assert t["n_rows"] == 2


def test_separateur_avec_champs_cites():
    """`"a,b";"c,d"` : la virgule coupe AUSSI, et régulièrement. Le score
    pénalise les champs qui gardent un guillemet — signe qu'on coupe au
    mauvais endroit."""
    t = _parse('nom;texte\r\n"a,b";"c,d"\r\n"e,f";"g,h"\r\n')
    assert t["sep"] == ";", t["sep"]
    assert t["rows"][0] == ["a,b", "c,d"], t["rows"][0]


def test_separateur_force_l_emporte():
    t = _parse("a,b;c\r\n1,2;3\r\n", sep=";")
    assert t["sep"] == ";"
    assert t["columns"] == ["a,b", "c"]


def test_entete_devinee_puis_forcable():
    t = _parse("nom;atk\r\nOctopode;7\r\n")
    assert t["header"] is True and t["columns"] == ["nom", "atk"]
    t2 = _parse("Octopode;7\r\nOracle;2\r\n")
    assert t2["header"] is False, "une ligne de données n'est pas une entête"
    assert t2["columns"] == ["col1", "col2"]
    t3 = _parse("nom;atk\r\nOctopode;7\r\n", header="no")
    assert t3["header"] is False and t3["n_rows"] == 2


def test_colonnes_en_double_sont_desambiguisees():
    t = _parse("nom;nom;atk\r\nA;B;7\r\n")
    assert len(set(t["columns"])) == 3, t["columns"]


# ═══════════════ seuil 5 — mappage : 0 ligne de code à écrire ═══════════════

def test_seuil_mappage_colonne_vers_slot():
    t = _parse(CSV_FILTRE)
    out = _build(t, mapping={"nom": "title", "atk": "atk"})
    c = out["cards"][0]
    assert c["fields"]["title"] == "Octopode"
    assert c["fields"]["atk"] == "7"
    # une colonne NON mappée n'entre pas dans la carte
    assert "qty" not in c["fields"]
    assert set(c["fields"]) == {"title", "atk"}


def test_mappage_champs_reserves_art_back_id():
    """Spec 2.3 : `card.art`, `card.back`, `card.id` ne sont pas des slots de
    texte — le mappage les remplit directement."""
    t = _parse("nom;img;dos;code\r\nA;a.png;b.png;X7\r\n")
    out = _build(t, mapping={"nom": "title", "img": "art", "dos": "back",
                             "code": "id"})
    c = out["cards"][0]
    assert c["art"] == "a.png"
    assert c["back"] == "b.png"
    assert c["id"] == "X7"
    # precedence de la spec : card.art ?? card.fields["art"]
    assert c["fields"]["art"] == "a.png"


def test_jetons_de_copie_n_sur_N():
    """« jetons de copie n/N » : mappables comme n'importe quelle colonne."""
    t = _parse(CSV_QTY)
    out = _build(t, mapping={"nom": "title", "#n": "num", "#N": "tot",
                             "#i": "idx", "#T": "deck"}, qty_col="qty")
    assert out["stats"]["n_cards"] == 6
    trois = [c for c in out["cards"] if c["fields"]["title"] == "Octopode"]
    assert [c["fields"]["num"] for c in trois] == ["1", "2", "3"]
    assert {c["fields"]["tot"] for c in trois} == {"3"}
    assert [c["fields"]["idx"] for c in out["cards"]] == \
        ["1", "2", "3", "4", "5", "6"]
    assert {c["fields"]["deck"] for c in out["cards"]} == {"6"}


def test_mappage_insensible_a_la_casse_du_nom_de_colonne():
    t = _parse("Nom;Atk\r\nA;7\r\n")
    out = _build(t, mapping={"nom": "title"})
    assert out["cards"][0]["fields"]["title"] == "A"


# ═══════════════════════ tri — LINKSORT, et mieux ═══════════════════════════

def test_tri_numerique_et_descendant():
    t = _parse("nom;atk\r\nA;9\r\nB;10\r\nC;2\r\n")
    out = _build(t, mapping={"nom": "title"}, sort="atk")
    assert [c["fields"]["title"] for c in out["cards"]] == ["C", "A", "B"]
    out = _build(t, mapping={"nom": "title"}, sort="atk desc")
    assert [c["fields"]["title"] for c in out["cards"]] == ["B", "A", "C"]
    out = _build(t, mapping={"nom": "title"}, sort="-atk")
    assert [c["fields"]["title"] for c in out["cards"]] == ["B", "A", "C"]


def test_tri_multi_cles_stable():
    t = _parse("nom;r;atk\r\nA;rare;2\r\nB;commune;9\r\nC;rare;9\r\n")
    out = _build(t, mapping={"nom": "title"}, sort="r, atk desc")
    assert [c["fields"]["title"] for c in out["cards"]] == ["B", "C", "A"]


def test_tri_garde_les_copies_ensemble():
    """Trier APRÈS duplication éparpillerait les copies d'une même ligne."""
    t = _parse(CSV_QTY)
    out = _build(t, mapping={"nom": "title"}, qty_col="qty", sort="nom")
    noms = [c["fields"]["title"] for c in out["cards"]]
    assert noms == ["Octopode"] * 3 + ["Oracle"] * 2 + ["Rebut"]


def test_tri_sur_colonne_inconnue_avertit_sans_tomber():
    t = _parse(CSV_QTY)
    out = _build(t, sort="colonne_absente")
    assert out["stats"]["n_cards"] == 3
    assert any("inconnue" in w for w in out["stats"]["warnings"])


# ═══════════ lignes désactivées — ce que la barre n'a pas du tout ═══════════

def test_lignes_desactivees_sortent_du_deck():
    t = _parse(CSV_FILTRE)
    out = _build(t, qty_col="qty", off=[0, 3])
    assert out["stats"]["disabled"] == 2
    assert out["stats"]["n_active"] == 2
    assert out["stats"]["n_cards"] == 7          # 2 (Oracle) + 5 (Rebut)


# ═════════════════ seuil 6 — 200 lignes en moins de 2 s ═════════════════════

def test_seuil_200_lignes_en_moins_de_2s():
    """Import + construction de 200 lignes, chronométrés. Le seuil de la spec
    est 2 s ; on mesure le pipeline complet, pas une étape choisie."""
    raw = D._sample_load(200)
    t0 = time.perf_counter()
    t = D.parse_table(raw)
    out = D.build_deck(t["columns"], t["rows"], {"nom": "title"}, "qty")
    dt = time.perf_counter() - t0
    assert t["n_rows"] == 200, t["n_rows"]
    assert out["stats"]["n_cards"] == 399, out["stats"]["n_cards"]
    assert dt < 2.0, f"200 lignes en {dt:.3f} s (seuil 2 s)"


def test_seuil_200_lignes_par_le_reseau_en_moins_de_2s():
    """Le même seuil, mais par le VRAI chemin : deux appels HTTP.

    CE TEST MESURAIT AUTRE CHOSE QUE CE QU'IL ANNONÇAIT, et il s'est fait
    prendre pendant ce tour : rouge à 2,645 s. `_api` importe `app.main`
    PARESSEUSEMENT, au premier appel — donc le chronomètre englobait
    l'import de toute l'application FastAPI. Mesuré : import 1 437 ms,
    première requête 232 ms, requêtes suivantes 28-29 ms, et le moteur seul
    3,5 ms pour les mêmes 200 lignes. Le test passait tant qu'un autre test
    avait importé l'application avant lui, et virait au rouge dès qu'il
    tournait seul ou sur une machine chargée. Un seuil qui dépend de l'ordre
    des tests ne mesure pas ce qu'il dit — exactement le défaut que ce tour
    traque dans l'interface.

    On chauffe donc HORS du chronomètre, puis on mesure les deux appels.
    """
    import base64
    b64 = base64.b64encode(D._sample_load(200)).decode("ascii")
    # chauffe : import de l'application + première requête, hors chrono
    assert _api("GET", BASE + "/samples").status_code == 200
    t0 = time.perf_counter()
    r = _api("POST", BASE + "/parse", json={"b64": b64, "name": "c.tsv"})
    assert r.status_code == 200, r.text
    tb = r.json()["table"]
    r2 = _api("POST", BASE + "/build",
              json={"columns": tb["columns"], "rows": tb["rows"],
                    "map": {"nom": "title"}, "qty_col": "qty"})
    assert r2.status_code == 200, r2.text
    dt = time.perf_counter() - t0
    assert tb["n_rows"] == 200 and tb["sep"] == "\t"
    assert r2.json()["stats"]["n_cards"] == 399
    assert dt < 2.0, f"aller-retour complet en {dt:.3f} s (seuil 2 s)"
    # et le moteur publie SON temps, qui est l'ordre de grandeur réel :
    assert tb["ms"] < 500, tb["ms"]


# ══════════════════ aller-retour : export -> import ═════════════════════════

def test_aller_retour_export_puis_import_rend_la_meme_table():
    t = _parse(CSV_ACCENTS)
    data = D.write_csv(t["columns"], t["rows"], sep=";", bom=True)
    assert data.startswith(b"\xef\xbb\xbf"), "sans BOM, Excel lit du cp1252"
    t2 = D.parse_table(data)
    assert t2["encoding"] == "utf-8-bom"
    assert t2["columns"] == t["columns"]
    assert t2["rows"] == t["rows"], (t2["rows"], t["rows"])


def test_aller_retour_survit_aux_separateurs_dans_les_cellules():
    cols = ["nom", "texte"]
    rows = [["A;B", 'dit "bonjour", puis part'], ["C,D", "ligne\tavec tab"]]
    for sep in (";", ",", "\t"):
        data = D.write_csv(cols, rows, sep=sep, bom=False)
        t = D.parse_table(data, sep=sep)
        assert t["rows"] == rows, (sep, t["rows"])


# ════════════════════════ jeux d'essai embarqués ════════════════════════════

def test_six_jeux_dessai_embarques():
    """Six depuis que « Pièges du CSV » est là : les cinq premiers couvrent les
    3 séparateurs ET les 3 encodages de la spec d'un clic chacun ; le sixième
    couvre le seul endroit où un importateur casse vraiment (guillemets,
    séparateur dans un champ, retour à la ligne dans une cellule, ligne à
    colonnes en trop) — ce que le critique reprochait au jeu d'essai « trop
    parfaitement formé »."""
    s = D.samples()
    assert len(s) == 6
    ids = [x["id"] for x in s]
    assert ids == ["parite", "ansi", "bom", "pieges", "classeur", "charge"]
    for x in s:
        assert x["b64"] and x["file"] and x["label"]


def test_les_jeux_dessai_couvrent_les_3_separateurs_et_les_3_encodages():
    """La démonstration doit être FAISABLE dans l'écran, pas seulement dans un
    test. On relit les jeux embarqués comme l'écran les relit : par le moteur
    de détection, sans rien forcer."""
    import base64
    seps, encs = set(), set()
    for x in D.samples():
        t = D.parse_table(base64.b64decode(x["b64"]))
        if t["workbook"]:
            continue
        seps.add(t["sep"])
        encs.add(t["encoding"])
    assert {",", ";", "\t"} <= seps, seps
    assert {"utf-8", "utf-8-bom", "cp1252"} <= encs, encs


def test_le_jeu_dessai_de_parite_donne_bien_10_cartes():
    """L'état vide propose un exemple ; cet exemple doit produire EXACTEMENT
    les chiffres du relevé de la barre — sinon la démonstration ment."""
    import base64
    s = {x["id"]: x for x in D.samples()}
    t = D.parse_table(base64.b64decode(s["parite"]["b64"]))
    p = s["parite"]["preset"]
    out = D.build_deck(t["columns"], t["rows"], {"nom": "title"},
                       p["qty_col"], p["filter"], p["sort"])
    assert t["n_rows"] == 4 and t["sep"] == ";" and t["encoding"] == "utf-8"
    assert out["stats"]["n_kept"] == 3
    assert out["stats"]["n_cards"] == 10


def test_le_jeu_dessai_ansi_est_bien_du_cp1252_lisible():
    import base64
    s = {x["id"]: x for x in D.samples()}
    t = D.parse_table(base64.b64decode(s["ansi"]["b64"]))
    assert t["encoding"] == "cp1252", t["encoding"]
    assert t["sep"] == ","
    plat = " ".join(" ".join(r) for r in t["rows"])
    for mot in ("Chimère", "Épée brisée", "Fée d'été", "Créature"):
        assert mot in plat, f"{mot} absent de {plat!r}"
    assert "Ã" not in plat


# ═══════════════════════ les routes, et leur robustesse ═════════════════════

def test_les_routes_data_sont_montees():
    from app.main import app
    chemins = list(app.openapi().get("paths", {}))
    for attendu in ("/api/cards/{did}/data/parse", "/api/cards/{did}/data/build",
                    "/api/cards/{did}/data/check", "/api/cards/{did}/data/export",
                    "/api/cards/{did}/data/samples"):
        assert attendu in chemins, f"{attendu} absent"


def test_route_parse_et_build_de_bout_en_bout():
    import base64
    r = _api("POST", BASE + "/parse",
             json={"b64": base64.b64encode(CSV_FILTRE.encode("utf-8")).decode(),
                   "name": "d.csv"})
    assert r.status_code == 200, r.text
    tb = r.json()["table"]
    assert tb["sep"] == ";" and tb["encoding"] == "utf-8"
    r2 = _api("POST", BASE + "/build",
              json={"columns": tb["columns"], "rows": tb["rows"],
                    "map": {"nom": "title"}, "qty_col": "qty",
                    "filter": "atk > 1"})
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d["stats"]["n_kept"] == 3 and d["stats"]["n_cards"] == 10


def test_export_rend_un_fichier_telechargeable():
    r = _api("POST", BASE + "/export",
             json={"columns": ["nom", "texte"], "rows": [["A", ACCENTS]],
                   "sep": ";", "bom": True, "name": "mon deck"})
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert r.content.startswith(b"\xef\xbb\xbf")
    assert ACCENTS.encode("utf-8") in r.content


def test_check_ne_leve_jamais_sur_un_filtre_fautif():
    """L'écran l'appelle à CHAQUE frappe : un 400 par lettre tapée ferait
    clignoter un bandeau rouge en permanence."""
    r = _api("POST", BASE + "/check",
             json={"columns": ["atk"], "filter": "atk > "})
    assert r.status_code == 200, r.text
    c = r.json()["check"]
    assert c["ok"] is False and c["error"] and c["pos"] >= 0
    r2 = _api("POST", BASE + "/check",
              json={"columns": ["atk"], "filter": "atk > 1"})
    assert r2.json()["check"]["ok"] is True


@pytest.mark.parametrize("route,corps", [
    ("/parse", {}),
    ("/parse", {"b64": "pas du base64 !!! ***"}),
    ("/build", {}),
    ("/build", {"columns": "pas une liste", "rows": []}),
    ("/build", {"columns": ["a"], "rows": [["1"]], "filter": "a > "}),
    ("/export", {"columns": None}),
])
def test_un_corps_mal_forme_ne_fait_jamais_500(route, corps):
    r = _api("POST", BASE + route, json=corps)
    assert r.status_code < 500, f"{route} {corps} -> {r.status_code} {r.text}"
    assert r.status_code in (400, 422), r.status_code


@pytest.mark.parametrize("route", ["/parse", "/build", "/export"])
def test_un_corps_qui_nest_pas_un_objet_ne_fait_jamais_500(route):
    r = _api("POST", BASE + route, json=["une", "liste"])
    assert r.status_code < 500, f"{route} -> {r.status_code} {r.text}"


def test_did_invalide_donne_400_et_pas_du_html():
    """Piège n°7 de la spec : une route hors domaine tombe sur le catch-all de
    la SPA, qui répond 200 + du HTML — et un client le lit comme un succès."""
    r = _api("GET", "/api/cards/pas_un_deck/data/samples")
    assert r.status_code == 400, r.status_code
    assert "html" not in r.headers.get("content-type", "").lower()


def test_samples_par_le_reseau():
    r = _api("GET", BASE + "/samples")
    assert r.status_code == 200, r.text
    j = r.json()["samples"]
    assert len(j) == len(D.samples())
    # la vignette part avec SES MESURES : l'écran n'a rien à recopier
    for x in j:
        for cle in ("n", "n_cols", "bytes", "encoding", "sep", "auto",
                    "n_kept", "n_cards", "n_warn"):
            assert cle in x, (x["id"], cle)


def test_limites_gardees():
    """Aucun corps ne doit pouvoir faire exploser la mémoire du backend."""
    r = _api("POST", BASE + "/build",
             json={"columns": ["a"], "rows": [["1"]] * (D.MAX_ROWS + 1)})
    assert r.status_code == 400
    trop = [["1", "999"]] * 40
    r2 = _api("POST", BASE + "/build",
              json={"columns": ["a", "q"], "rows": trop, "qty_col": "q"})
    assert r2.status_code == 400        # 40 x 999 dépasse MAX_CARDS


# ═══════════════════════════════════════════════════════════════════════════
# LES MANQUES RELEVÉS PAR LES DEUX CRITIQUES — un test par manque corrigé.
# Chaque test porte la MESURE d'avant en commentaire : sans elle, on ne saurait
# plus dans six mois si le test protège une correction ou décrit une évidence.
# ═══════════════════════════════════════════════════════════════════════════

# Les slots RÉELLEMENT publiés par la pièce 03 (relevés à l'écran) : ce ne sont
# PAS les identifiants du jeu de repli de l'écran (`hp`, `type`, `number`).
#
# `text` EST RELEVÉ SUR LA SOURCE DE P3, pas inventé : ce sont les valeurs de
# démonstration du gabarit « champion » (mod-type.js, bloc PRESETS), celles que
# le painter imprime quand `card.fields[slot]` est vide. Sans ce champ dans le
# jeu d'essai, le test ne pourrait pas distinguer un slot qui FABRIQUE une
# valeur d'un slot qui laisse un vide — et c'est exactement la distinction que
# le compteur affichait à tort.
SLOTS_P3 = [
    {"id": "cost", "label": "Coût", "text": "5"},
    {"id": "title", "label": "Titre",
     "text": "Veilleur, Grand Oracle des Marches Profondes"},
    {"id": "typeline", "label": "Ligne de type",
     "text": "Créature légendaire — Céphalopode"},
    {"id": "rules", "label": "Encadré de règles", "text": "Vol, célérité. …"},
    {"id": "flavor", "label": "Texte d'ambiance",
     "text": "« Il compte les marées comme d'autres comptent les jours. »"},
    {"id": "atk", "label": "Attaque", "text": "4"},
    {"id": "def", "label": "Vie", "text": "5"},
    {"id": "num", "label": "Numéro", "text": "017 / 060"},
    {"id": "artist", "label": "Artiste", "text": "ill. A. Nonyme"},
]
COLS_DEMO = ["nom", "atk", "pv", "qty", "rarete", "texte"]


def test_manque1_le_mappage_auto_suit_les_slots_REELS_de_p3():
    """LE manque nommé par les deux critiques, pris à sa racine.

    MESURE AVANT (relevée dans le lab, slots de P3 publiés) : sur les 6
    colonnes du jeu de parité, 3 seulement étaient mappées — `nom`, `atk`,
    `texte` — et `pv` restait orpheline pendant que le slot « Vie » restait
    vide. Cause : la table de synonymes vivait dans l'écran, indexée sur les
    identifiants de son jeu de REPLI (`hp`), et P3 nomme ce slot `def`. Le
    gabarit imprimait alors sa valeur de démonstration (5) à la place de la
    donnée (1), sur toutes les cartes, sans un signe.

    APRÈS : la table est indexée par CONCEPT et confrontée à l'id ET au libellé
    du slot. `pv` -> `def` (« Vie »), quel que soit le nom choisi par P3.
    """
    sg = D.suggest_map(COLS_DEMO, SLOTS_P3)
    assert sg["map"].get("pv") == "def", sg["map"]
    assert sg["map"].get("nom") == "title"
    assert sg["map"].get("atk") == "atk"
    assert sg["map"].get("texte") == "rules"
    assert len(sg["map"]) == 4, sg["map"]          # 3 avant, 4 après
    assert sg["qty_col"] == "qty"                  # et `qty` n'est pas orpheline
    # `rarete` reste orpheline, mais avec son MOTIF : P3 n'a aucun slot de
    # rareté. Le dire est le contraire de le taire.
    orph = {o["col"]: o["why"] for o in sg["orphans"]}
    assert "rarete" in orph and orph["rarete"]
    assert "qty" not in orph


def test_manque1_le_meme_mappage_marche_avec_les_ids_de_repli():
    """La correction ne doit pas retourner le bug : avec le jeu de repli de
    l'écran (`hp`, `type`, `number`), `pv` doit toujours tomber sur « Vie »."""
    repli = [{"id": "hp", "label": "Vie"}, {"id": "title", "label": "Titre"},
             {"id": "type", "label": "Type"}, {"id": "number", "label": "Numéro"}]
    sg = D.suggest_map(["pv", "nom", "type", "no"], repli)
    assert sg["map"].get("pv") == "hp", sg["map"]
    assert sg["map"].get("no") == "number", sg["map"]


def test_manque1_laudit_nomme_les_slots_nourris_par_le_gabarit():
    """MESURE AVANT : l'écran affichait « 4 LIGNES / 3 RETENUES / 10 CARTES »,
    « 6 colonnes », « séparateur point-virgule », « import 876 ms » — tout,
    sauf le seul chiffre qui fait rater une impression : combien de slots la
    carte remplit avec le TEXTE DU GABARIT. Relevé : 6 slots sur 9, zéro
    avertissement.

    APRÈS : `stats.audit` les nomme, un par un.
    """
    t = _parse(CSV_FILTRE)
    out = _build(t, mapping={"nom": "title"}, qty_col="qty", slots=SLOTS_P3,
                 blank_unfed=False)
    a = out["stats"]["audit"]
    assert a["slots_known"] is True
    assert a["n_slots"] == 9
    assert a["n_slots_fed"] == 1 and a["slots_fed"] == ["title"]
    assert set(a["slots_unfed"]) == {"cost", "typeline", "rules", "flavor",
                                     "atk", "def", "num", "artist"}
    assert a["n_from_template"] == 8
    assert a["cols_unmapped"] == ["atk"]           # `qty` est la quantité
    # et quand tout est posé, le compteur retombe à zéro : il ne crie pas
    # en permanence, sinon on cesse de le lire.
    plein = {"nom": "title", "atk": "atk"}
    for sid in ("cost", "typeline", "rules", "flavor", "def", "num", "artist"):
        plein["c_" + sid] = sid
    cols = t["columns"] + ["c_" + s for s in
                           ("cost", "typeline", "rules", "flavor", "def",
                            "num", "artist")]
    rows = [r + ["x"] * 7 for r in t["rows"]]
    out2 = D.build_deck(cols, rows, plein, "qty", slots=SLOTS_P3,
                        blank_unfed=False)
    assert out2["stats"]["audit"]["n_from_template"] == 0


def test_manque1_une_cellule_vide_sur_colonne_mappee_est_signalee():
    """Le même mensonge, une ligne plus bas, et personne ne l'avait vu : une
    colonne BIEN mappée dont la cellule est vide laisse aussi le gabarit
    reprendre la main (mod-type.js : `v.trim() !== "" ? v : slot.text`). Sur
    300 cartes, c'est la ligne 214 qui imprime « RARE »."""
    t = _parse("nom;rar;qty\r\nA;;2\r\nB;épique;1\r\nC;;1\r\n")
    out = _build(t, mapping={"nom": "title", "rar": "typeline"},
                 qty_col="qty", slots=SLOTS_P3)
    holes = out["stats"]["audit"]["holes"]
    assert len(holes) == 1, holes
    assert holes[0]["col"] == "rar" and holes[0]["slot"] == "typeline"
    # 2 copies de A + 1 de C = 3 CARTES touchées, pas « 2 lignes »
    assert holes[0]["n_cards"] == 3, holes


def test_manque2_le_bom_est_un_choix_et_les_deux_branches_marchent():
    """MESURE AVANT : « Exporter le CSV » écrivait TOUJOURS un BOM UTF-8
    (EF BB BF vérifié à l'octet par le critique), si bien qu'un parseur tiers
    lisait la première colonne « ﻿nom ». Défendable pour Excel, mais c'était
    une décision cachée dans un bouton.

    APRÈS : une case à cocher, et les deux chemins tiennent l'aller-retour.
    """
    cols, rows = ["nom", "texte"], [["A", ACCENTS]]
    avec = D.write_csv(cols, rows, sep=";", bom=True)
    sans = D.write_csv(cols, rows, sep=";", bom=False)
    assert avec.startswith(b"\xef\xbb\xbf")
    assert not sans.startswith(b"\xef\xbb\xbf")
    assert avec[3:] == sans                        # même charge utile à l'octet
    # SANS BOM, un csv.reader standard rend « nom » et non « ﻿nom » :
    import csv as _csv
    import io as _io
    lu = list(_csv.reader(_io.StringIO(sans.decode("utf-8")), delimiter=";"))
    assert lu[0][0] == "nom", lu[0]
    # et l'aller-retour reste vrai des deux côtés
    for data in (avec, sans):
        t = D.parse_table(data)
        assert t["columns"] == cols and t["rows"] == rows


def test_manque2_lexport_sans_bom_passe_par_la_route():
    r = _api("POST", BASE + "/export",
             json={"columns": ["nom"], "rows": [["A"]], "sep": ";",
                   "bom": False, "name": "d"})
    assert r.status_code == 200, r.text
    assert not r.content.startswith(b"\xef\xbb\xbf")


def test_manque3_le_moteur_publie_son_propre_temps():
    """MESURE AVANT : l'écran affichait « import 876 ms » pour 218 octets, et
    ce nombre unique n'était ni croyable ni contestable. Le moteur rend
    désormais SON temps (`table.ms`) : l'écran soustrait et affiche les postes
    séparément (base64 · moteur · trajet HTTP · DOM · première frame)."""
    t = D.parse_table(D._sample_load(200))
    assert isinstance(t["ms"], float) and t["ms"] >= 0.0
    assert t["ms"] < 500.0, t["ms"]           # 200 lignes côté moteur
    r = _api("POST", BASE + "/parse",
             json={"b64": __import__("base64").b64encode(
                 D._sample_load(200)).decode(), "name": "c.tsv"})
    assert r.status_code == 200
    assert r.json()["table"]["ms"] >= 0.0


def test_manque5_la_ligne_ecartee_dit_QUELLE_condition_la_rejette():
    """MESURE AVANT : « la ligne rejetée est barrée, mais rien ne dit QUEL
    prédicat l'a rejetée : sur un filtre à plusieurs conditions, l'utilisateur
    devra deviner. » APRÈS : chaque ligne écartée sort avec sa condition."""
    t = _parse(CSV_FILTRE)
    out = _build(t, expr="atk > 1 et qty > 2", qty_col="qty")
    why = {x["r"]: x["why"] for x in out["stats"]["rejected"]}
    assert why[1] == "qty > 2", why       # Oracle : atk=2 passe, qty=2 non
    assert why[3] == "atk > 1", why       # Echo : atk=1 tombe sur la première
    assert len(why) == 2
    # un « ou » de premier niveau : aucune condition n'est seule responsable,
    # on rend l'expression entière — ce qui reste VRAI.
    out2 = _build(t, expr="atk > 8 ou qty = 2")
    assert all(x["why"] == "atk > 8 ou qty = 2"
               for x in out2["stats"]["rejected"])


@pytest.mark.parametrize("op", list(D.FILTER_OPS))
def test_manque5_chaque_operateur_annonce_fonctionne(op):
    """L'écran affiche « 9 comparaisons + 3 connecteurs », servis par
    /grammar. Un nombre affiché doit être vrai : chaque entrée de la liste est
    ici EXÉCUTÉE sur une vraie table. Impossible d'en annoncer une de plus."""
    t = _parse(CSV_FILTRE)
    out = _build(t, expr=op["ex"])
    assert 0 <= out["stats"]["n_kept"] <= 4, op
    for alias in [a.strip() for a in str(op["alias"] or "").split("·") if a.strip()]:
        if alias in ("&", "&&", "||"):
            continue
        expr = op["ex"].replace(op["sym"], alias)
        D.compile_filter(expr, t["columns"])       # ne doit pas lever


@pytest.mark.parametrize("j", list(D.FILTER_JOINS))
def test_manque5_chaque_connecteur_annonce_fonctionne(j):
    t = _parse(CSV_FILTRE)
    expr = ("atk > 1 " + j["sym"] + " qty > 2") if j["sym"] != "non" \
        else "non (atk > 1)"
    assert 0 <= _build(t, expr=expr)["stats"]["n_kept"] <= 4


def test_manque5_la_route_grammar_sert_la_liste():
    r = _api("GET", BASE + "/grammar")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["n_ops"] == len(D.FILTER_OPS) == 9
    assert d["n_joins"] == len(D.FILTER_JOINS) == 3
    assert all(o["sym"] and o["ex"] for o in d["ops"])


def test_manque7_un_classeur_xlsx_est_lu_sans_dependance():
    """MESURE AVANT : « Sources limitées à CSV/TSV. Pas de .xlsx, .ods, ni
    Google Sheets, là où la barre lit les cinq. » APRÈS : .xlsx et .ods, avec
    zipfile + ElementTree, sans une dépendance de plus."""
    t = D.parse_table(D._sample_xlsx())
    assert t["encoding"] == "xlsx"
    assert t["columns"] == ["nom", "atk", "pv", "qty", "rarete", "texte"]
    assert t["n_rows"] == 4
    assert t["rows"][0] == ["Colosse", "7", "5", "3", "rare",
                            "Mêlée de lances"]
    assert t["sheet"] == "Deck" and t["workbook"] is True


def test_manque7_un_classeur_ods_est_lu():
    import zipfile as _z
    cells = [["nom", "atk"], ["Octopode", "7"], ["Oracle", "2"]]
    body = ""
    for r in cells:
        body += "<table:table-row>" + "".join(
            "<table:table-cell><text:p>" + c + "</text:p></table:table-cell>"
            for c in r) + "</table:table-row>"
    xml = ('<?xml version="1.0"?><office:document-content '
           'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
           'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
           'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
           '<office:body><office:spreadsheet><table:table table:name="Feuille1">'
           + body + "</table:table></office:spreadsheet></office:body>"
           "</office:document-content>")
    import io as _io
    buf = _io.BytesIO()
    with _z.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        z.writestr("content.xml", xml)
    t = D.parse_table(buf.getvalue())
    assert t["encoding"] == "ods" and t["sheet"] == "Feuille1"
    assert t["columns"] == ["nom", "atk"] and t["n_rows"] == 2


def test_manque7_un_classeur_nannonce_ni_separateur_ni_encodage_de_texte():
    """La règle des chiffres vrais : un classeur n'a NI séparateur NI encodage
    de texte. Afficher « séparateur point-virgule · UTF-8 » dessus serait un
    badge faux de plus."""
    t = D.parse_table(D._sample_xlsx())
    assert t["sep"] == ""
    assert "point-virgule" not in t["sep_label"] and "virgule" not in t["sep_label"]
    assert t["sep_label"] == "sans objet (classeur)"
    assert "UTF-8" not in t["encoding_label"]
    assert "Deck" in t["encoding_label"]


def test_manque7_un_zip_qui_nest_pas_un_classeur_fait_400_pas_500():
    import io as _io
    import zipfile as _z
    buf = _io.BytesIO()
    with _z.ZipFile(buf, "w") as z:
        z.writestr("hello.txt", "rien")
    with pytest.raises(HTTPException) as ei:
        D.parse_table(buf.getvalue())
    assert ei.value.status_code == 400
    r = _api("POST", BASE + "/parse",
             json={"b64": __import__("base64").b64encode(
                 b"PK\x03\x04pas-un-zip").decode()})
    assert r.status_code == 400, r.status_code


def test_manque7_le_jeu_dessai_classeur_donne_les_memes_10_cartes():
    """Le classeur embarqué doit produire EXACTEMENT les chiffres du relevé de
    la barre, comme le CSV : sinon la démonstration a deux vérités."""
    import base64
    s = {x["id"]: x for x in D.samples()}["classeur"]
    t = D.parse_table(base64.b64decode(s["b64"]))
    p = s["preset"]
    out = D.build_deck(t["columns"], t["rows"], {"nom": "title"},
                       p["qty_col"], p["filter"], p["sort"])
    assert out["stats"]["n_kept"] == 3 and out["stats"]["n_cards"] == 10


def test_manque10_la_colonne_image_est_resolue_vers_la_bibliotheque():
    """MESURE AVANT : « La colonne image résolue vers la bibliothèque, exigée
    par la spec de cette pièce, n'est visible nulle part sur l'écran. » Mapper
    une colonne sur « Illustration » ne faisait que passer une chaîne : on
    découvrait au tirage que 40 cartes sur 200 pointaient un fichier absent."""
    lib = pathlib.Path(os.environ["IMAGES_FOLDER"])
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "octo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    r = _api("POST", BASE + "/artcheck",
             json={"values": ["octo.png", "absent.png", "",
                              "https://exemple/x.png", "C:/ailleurs/octo.png"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["art"][0]["ok"] is True
    assert d["art"][0]["url"].endswith("/octo.png")
    assert d["art"][1]["ok"] is False
    assert d["art"][2]["v"] == "" and d["art"][2]["kind"] == "vide"
    assert d["art"][3]["ok"] is True and d["art"][3]["kind"] == "lien"
    # un chemin absolu ne sort JAMAIS du dossier : seul le nom compte
    assert d["art"][4]["ok"] is True and "ailleurs" not in d["art"][4]["url"]
    assert d["n"] == 4 and d["n_ok"] == 3 and d["n_missing"] == 1


def test_manque10_artcheck_ne_traverse_pas_le_disque():
    r = _api("POST", BASE + "/artcheck",
             json={"values": ["../../../../Windows/win.ini",
                              "..\\..\\secret.txt"]})
    assert r.status_code == 200, r.text
    for it in r.json()["art"]:
        assert it["ok"] is False, it
        assert ".." not in it["url"]


def test_la_route_suggest_est_montee_et_repond():
    r = _api("POST", BASE + "/suggest",
             json={"columns": COLS_DEMO, "slots": SLOTS_P3})
    assert r.status_code == 200, r.text
    sg = r.json()["suggest"]
    assert sg["map"]["pv"] == "def"
    assert "def" not in sg["free"] and "cost" in sg["free"]


def test_les_nouvelles_routes_sont_montees():
    from app.main import app
    chemins = list(app.openapi().get("paths", {}))
    for attendu in ("/api/cards/{did}/data/suggest",
                    "/api/cards/{did}/data/grammar",
                    "/api/cards/{did}/data/artcheck"):
        assert attendu in chemins, f"{attendu} absent"


@pytest.mark.parametrize("corps", [
    {}, {"columns": "pas une liste"}, {"columns": ["a"], "slots": "non"},
])
def test_suggest_et_artcheck_ne_font_jamais_500(corps):
    assert _api("POST", BASE + "/suggest", json=corps).status_code < 500
    assert _api("POST", BASE + "/artcheck", json=corps).status_code < 500


# ═══════════════════════════════════════════════════════════════════════════
# TOUR DE DURCISSEMENT — un test par correction, avec LA MESURE D'AVANT.
#
# Deux exigences dominent ce tour et se lisent dans tout ce qui suit :
#   (1) tout chiffre affiché doit être VRAI, prouvé sur les octets. Un chiffre
#       faux vaut moins que pas de chiffre.
#   (2) rien de ce que cette pièce ne produit pas ne doit être annoncé par
#       elle. Cette pièce ne sort AUCUN PNG, PDF, GLB : elle n'affiche donc
#       aucun DPI, aucun fond perdu, aucune carte de PBR. Le test
#       `test_ma_piece_naffiche_aucun_chiffre_quelle_ne_produit_pas` le tient.
# ═══════════════════════════════════════════════════════════════════════════

# Le même jeu de slots, mais tel qu'un utilisateur le tord en deux clics :
# un slot MASQUÉ (l'œil de P3) et un slot dont on a effacé le texte de
# démonstration. Ni l'un ni l'autre n'imprime quoi que ce soit.
SLOTS_TORDUS = [
    {"id": "title", "label": "Titre", "text": "Deepotus", "on": True},
    {"id": "cost", "label": "Coût", "text": "5", "on": False},      # masqué
    {"id": "flavor", "label": "Ambiance", "text": "", "on": True},  # muet
    {"id": "num", "label": "Numéro", "text": "017 / 060", "on": True},
]


def test_un_slot_masque_ou_muet_nest_plus_compte_comme_du_gabarit():
    """LE CHIFFRE FAUX, PRIS À SA RACINE.

    MESURE AVANT : `n_from_template` valait `len(slots_unfed) + len(holes)`.
    Le moteur ne recevait de chaque slot que `{id, label}` — ni `text` ni
    `on` — il ne POUVAIT donc pas savoir ce qui s'imprime. Sur ces 4 slots
    dont un seul est alimenté, il annonçait **3** valeurs fabriquées. Or le
    slot `cost` est MASQUÉ chez P3 (mod-type.js:763 ne dessine que
    `s.on`) et `flavor` a un texte de démonstration VIDE (mod-type.js:857
    n'imprime alors rien) : la vérité est **1**, le seul `num`.
    C'est le même défaut que l'en-tête « 16 bits » d'un PNG dont les
    échantillons tombent tous sur k*257 — une borne lue comme une mesure.

    APRÈS : `text` et `on` remontent, et chaque slot tombe dans une seule
    case, dont la somme est vérifiable.
    """
    t = _parse(CSV_FILTRE)
    a = _build(t, mapping={"nom": "title"}, qty_col="qty",
               slots=SLOTS_TORDUS, blank_unfed=False)["stats"]["audit"]
    assert a["n_slots"] == 3, "le slot masqué ne compte pas dans le total"
    assert a["n_slots_hidden"] == 1 and a["slots_hidden"] == ["cost"]
    assert a["slots_unfed_template"] == ["num"]
    assert a["slots_unfed_blank"] == ["flavor"]
    assert a["n_from_template"] == 1, "3 annoncés avant, 1 vrai"
    # et la somme du grand livre des slots tombe juste
    assert (a["n_slots_fed"] + a["n_slots_unfed_template"]
            + a["n_slots_unfed_blank"] == a["n_slots"])


def test_les_deux_grands_livres_tombent_juste():
    """LE REPROCHE : « trois dénominateurs différents affichés en même temps
    sans les réconcilier — 5 / 7 colonnes posées, 4 / 9 alimentés, 5 / 9 sans
    donnée ».

    MESURE AVANT, jeu de parité à 7 colonnes (`img` mappée sur l'illustration) :
    l'écran affichait bien 5 colonnes posées et 4 slots alimentés, sans
    JAMAIS écrire que la 5e part vers un champ RÉSERVÉ ni que `qty` sert de
    quantité. Deux additions manquaient ; on ne pouvait pas les refaire de
    tête.

    APRÈS : chaque colonne tombe dans une case et une seule, et la somme vaut
    le total. C'est cette addition-là que l'écran recopie.
    """
    t = _parse("nom;atk;pv;qty;rarete;texte;img\r\n"
               "Octopode;7;5;3;rare;Mêlée;octo.png\r\n"
               "Oracle;2;3;2;commune;Brume;oracle.png\r\n")
    sg = D.suggest_map(t["columns"], SLOTS_P3)
    a = _build(t, mapping=sg["map"], qty_col=sg["qty_col"],
               slots=SLOTS_P3)["stats"]["audit"]
    assert a["n_cols"] == 7
    assert a["n_cols_to_slots"] == 4          # nom, atk, pv, texte
    assert a["n_cols_to_reserved"] == 1       # img -> card.art
    assert a["n_cols_qty"] == 1               # qty
    assert a["n_cols_idle"] == 1              # rarete
    assert (a["n_cols_to_slots"] + a["n_cols_to_reserved"]
            + a["n_cols_qty"] + a["n_cols_idle"] == a["n_cols"]), a
    # l'écart de 1 entre « 5 colonnes posées » et « 4 slots alimentés » est
    # désormais NOMMÉ, et il est exactement le champ réservé.
    assert a["n_cols_mapped"] - a["n_slots_fed"] == a["n_cols_to_reserved"]
    assert (a["n_slots_fed"] + a["n_slots_unfed_template"]
            + a["n_slots_unfed_blank"] == a["n_slots"])


def test_le_mode_laisser_vide_fait_taire_le_gabarit_sur_les_vraies_cartes():
    """LE PLUS GROS MANQUE, NOMMÉ EN PREMIER PAR LES DEUX CRITIQUES.

    MESURE AVANT : sur la carte 1/10 du jeu de parité, 5 des 9 emplacements
    imprimés venaient du GABARIT — Coût « 5 », « Créature légendaire —
    Céphalopode », la citation d'ambiance, « 017 / 060 », « ill. <nom> » — avec
    la même typographie que les vraies valeurs. Sur les 10 cartes : 50 champs
    fabriqués partant chez l'imprimeur. Le produit l'ÉCRIVAIT en rouge et
    l'imprimait quand même.

    APRÈS, et c'est le DÉFAUT : chaque slot visible que la donnée n'alimente
    pas reçoit U+200B, que `mod-type.js:857` accepte (`"\\u200b".trim()` n'est
    pas vide : U+200B est de catégorie Cf, pas Zs) et que le moteur de rendu ne
    dessine pas. Le gabarit ne reprend jamais la main.
    """
    t = _parse(CSV_FILTRE)
    out = _build(t, mapping={"nom": "title"}, qty_col="qty", slots=SLOTS_P3)
    a = out["stats"]["audit"]
    assert a["blank_mode"] is True
    assert a["n_from_template"] == 0, "plus une seule valeur fabriquée"
    assert a["n_template_avoided"] == 8, "et on dit combien ont été évitées"
    # la carte livrée : chaque slot muselé porte le marqueur, et RIEN d'autre
    c = out["cards"][0]
    assert c["fields"]["title"] == "Octopode"
    for sid in ("cost", "typeline", "rules", "flavor", "atk", "def", "num",
                "artist"):
        assert c["fields"][sid] == D.BLANK, sid
        # la garantie qui fait marcher le tout, écrite noir sur blanc :
        assert c["fields"][sid].strip() != "", "sinon le gabarit reparle"
    # et le mode se débraye, pour qui veut son gabarit en aperçu
    out2 = _build(t, mapping={"nom": "title"}, qty_col="qty", slots=SLOTS_P3,
                  blank_unfed=False)
    assert "cost" not in out2["cards"][0]["fields"]
    assert out2["stats"]["audit"]["n_from_template"] == 8


def test_le_marqueur_de_vide_ne_masque_pas_une_cellule_vide_par_carte():
    """La neutralisation est PAR CARTE. Une colonne bien mappée dont la cellule
    est vide sur la ligne 214 seulement doit être muselée sur ces cartes-là et
    sur elles seules — sinon on rate exactement le cas qui imprime « RARE » au
    milieu d'un tirage de 300."""
    t = _parse("nom;rar;qty\r\nA;;2\r\nB;épique;1\r\n")
    out = _build(t, mapping={"nom": "title", "rar": "typeline"},
                 qty_col="qty", slots=SLOTS_P3)
    vals = [c["fields"]["typeline"] for c in out["cards"]]
    assert vals == [D.BLANK, D.BLANK, "épique"], vals
    h = out["stats"]["audit"]["holes"]
    assert h and h[0]["n_cards"] == 2 and h[0]["template"] is True


def test_lexport_du_deck_resolu_nest_plus_la_table_source():
    """LE LIVRABLE QUI MANQUAIT, mesuré par le critique : « Exporter le CSV »
    rendait la table SOURCE — 4 lignes, y compris l'Écho que le filtre venait
    d'écarter, et la colonne `qty` non résolue. Ce n'était pas le deck.

    APRÈS : `scope="deck"` rend une ligne PAR CARTE, filtre, tri et quantités
    appliqués.
    """
    body = {"columns": None, "rows": None}
    t = _parse(CSV_FILTRE)
    body = {"columns": t["columns"], "rows": t["rows"], "scope": "deck",
            "map": {"nom": "title", "atk": "atk"}, "qty_col": "qty",
            "filter": "atk > 1", "sort": "atk desc", "slots": SLOTS_P3,
            "sep": ";", "bom": False, "name": "d"}
    r = _api("POST", BASE + "/export", json=body)
    assert r.status_code == 200, r.text
    lu = D.parse_table(r.content)
    # 10 cartes -> 10 lignes. La table source en faisait 4.
    assert lu["n_rows"] == 10, lu["rows"]
    assert "carte" in lu["columns"] and "title" in lu["columns"]
    noms = [row[lu["columns"].index("title")] for row in lu["rows"]]
    assert noms.count("Rebut") == 5 and noms.count("Octopode") == 3
    assert "Echo" not in noms, "la ligne écartée par le filtre n'y est PAS"
    assert noms[0] == "Rebut", "et le tri atk desc est appliqué"
    # le marqueur de vide n'est JAMAIS écrit dans un fichier livré
    assert D.BLANK not in r.content.decode("utf-8")
    # la portée « table » reste ce qu'elle était
    body["scope"] = "table"
    r2 = _api("POST", BASE + "/export", json=body)
    assert D.parse_table(r2.content)["n_rows"] == 4


def test_lexport_par_defaut_rend_les_octets_dentree(tmp_path):
    """MESURE AVANT : la case « BOM pour Excel » était COCHÉE par défaut. 258
    octets entraient, 261 sortaient — l'identité octet pour octet n'existait
    qu'après avoir décoché une case que personne ne décoche.

    APRÈS : le défaut est décoché, des deux côtés (fonction ET route). Le
    fichier livré est l'octet pour octet de l'entrée.
    """
    src = ("nom;atk;texte\r\n"
           "Écho;1;Ne fait rien, très bien\r\n"
           "Rebut;9;Écrase tout\r\n").encode("utf-8")
    t = D.parse_table(src)
    rendu = D.write_csv(t["columns"], t["rows"])          # sans argument !
    assert rendu == src, (len(rendu), len(src))
    r = _api("POST", BASE + "/export",
             json={"columns": t["columns"], "rows": t["rows"], "sep": ";",
                   "name": "d"})                          # sans « bom » !
    assert r.status_code == 200, r.text
    assert r.content == src, (len(r.content), len(src))
    # et la case reste utile : cochée, elle ajoute EXACTEMENT 3 octets
    r2 = _api("POST", BASE + "/export",
              json={"columns": t["columns"], "rows": t["rows"], "sep": ";",
                    "bom": True, "name": "d"})
    assert r2.content == b"\xef\xbb\xbf" + src
    assert len(r2.content) - len(r.content) == 3


@pytest.mark.parametrize("sep,nom", [(",", "virgule"), (";", "point-virgule"),
                                     ("\t", "tabulation"), ("|", "barre")])
@pytest.mark.parametrize("enc,elab", [("utf-8", "utf-8"),
                                      ("utf-8-sig", "utf-8-bom"),
                                      ("cp1252", "cp1252")])
def test_la_detection_tient_sur_les_12_combinaisons(sep, nom, enc, elab):
    """LE REPROCHE : « détection démontrée sur 1 cas sur 3 pour le séparateur
    et 1 sur 3 pour l'encodage ; rien ne prouve que ce soit une détection et
    non une valeur par défaut heureuse ».

    Le duel n'en montrait qu'un. Ici les 4 séparateurs x 3 encodages sont
    passés au moteur SANS RIEN FORCER, et on vérifie que les cellules
    ressortent intactes — accents compris. Une valeur par défaut heureuse ne
    peut pas tomber juste douze fois.
    """
    base = [["nom", "atk", "texte"], ["Écho", "1", "Ne fait rien, très bien"],
            ["Rebut", "9", "Écrase tout sur son passage"]]
    lignes = [sep.join('"' + c + '"' if sep in c else c for c in r)
              for r in base]
    raw = ("\r\n".join(lignes) + "\r\n").encode(enc)
    t = D.parse_table(raw)                                 # aucun forçage
    assert t["sep"] == sep, f"{nom} deviné {t['sep']!r}"
    assert t["encoding"] == elab, t["encoding"]
    assert t["sep_auto"] is True and t["enc_auto"] is True
    assert t["columns"] == base[0]
    assert t["rows"] == base[1:], t["rows"]


@pytest.mark.parametrize("nom,raw,attendu", [
    ("virgule DANS un champ cité, séparateur virgule",
     b'nom,texte\r\nEcho,"Ne fait rien, tres bien"\r\n',
     [["Echo", "Ne fait rien, tres bien"]]),
    ("guillemet doublé",
     b'nom,texte\r\nEcho,"il dit ""bonjour"" ici"\r\n',
     [["Echo", 'il dit "bonjour" ici']]),
    ("séparateur DANS un champ cité, séparateur point-virgule",
     b'nom;texte\r\nEcho;"a;b;c"\r\n',
     [["Echo", "a;b;c"]]),
])
def test_les_cas_ou_un_importateur_casse_vraiment(nom, raw, attendu):
    """LE REPROCHE : « le jeu d'essai est parfaitement formé — aucun champ
    entre guillemets, aucun séparateur présent dans une valeur. Rien n'est
    prouvé sur le seul endroit où un importateur CSV casse vraiment. Son
    avantage sur la virgule interne tient parce que le séparateur était « ; » ;
    le cas symétrique n'est pas testé. »

    Le voici, symétrique compris."""
    t = D.parse_table(raw)
    assert t["rows"] == attendu, (nom, t["rows"])


def test_une_ligne_mal_formee_est_comptee_et_pas_reparee_en_silence():
    """MESURE AVANT, sur `nom;atk;pv` + la ligne « Echo;1;9;99;77 » : le
    parseur rendait ['Echo','1','9'], les valeurs 99 et 77 étaient PERDUES et
    `warnings` valait []. Un importateur qui jette de la donnée sans un mot,
    c'est le reproche qu'on adressait à la barre pour son ANSI muet.

    Et le critique demandait précisément ce compteur : « aucun compteur de
    lignes rejetées pour cause de FORMAT, par opposition aux lignes écartées
    par le filtre ». Les deux existent maintenant, séparément.
    """
    t = D.parse_table(b"nom;atk;pv\r\nEcho;1;9;99;77\r\nRebut;9;1\r\nA;2\r\n")
    assert t["n_ragged_long"] == 1 and t["ragged_long"] == [1]
    assert t["n_values_lost"] == 2, "99 et 77"
    assert t["n_ragged_short"] == 1 and t["ragged_short"] == [3]
    plat = " ".join(t["warnings"])
    assert "PLUS de 3 champs" in plat and "2 valeur(s) écartée(s)" in plat
    assert "MOINS de 3 champs" in plat
    # un fichier bien formé ne déclenche RIEN : le compteur ne crie pas pour
    # rien, sinon on cesse de le lire.
    propre = D.parse_table(CSV_FILTRE.encode("utf-8"))
    assert propre["n_ragged_long"] == 0 and propre["n_ragged_short"] == 0
    assert propre["warnings"] == []


def test_la_colonne_image_dit_aussi_ce_quelle_ne_trouve_pas():
    """LE REPROCHE : « 4 sur 4 est un compteur, pas une preuve de robustesse :
    les 4 fichiers existent tous, aucun cas d'échec n'est montré. On ne sait
    pas ce qu'il fait quand une image manque. »"""
    from app.config import settings
    (settings.images_path / "octo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    r = _api("POST", BASE + "/artcheck",
             json={"values": ["octo.png", "OCTO.PNG", "absente.png",
                              "octo.jpg", "", "https://x/y.png"]})
    assert r.status_code == 200, r.text
    j = r.json()
    par = {x["v"]: x for x in j["art"]}
    assert par["octo.png"]["ok"] is True
    assert par["absente.png"]["ok"] is False, "le manque est DIT"
    assert par["octo.jpg"]["ok"] is False, "l'extension ne se devine pas"
    assert par["https://x/y.png"]["ok"] is True and par[""]["ok"] is False
    # 5 valeurs nommées, et le compte des manquantes est celui des faux
    assert j["n"] == 5
    assert j["n_ok"] + j["n_missing"] == j["n"]
    assert j["n_missing"] >= 2


def test_lecran_envoie_bien_text_et_on_et_ne_survit_pas_a_sa_table():
    """Deux invariants de l'ÉCRAN sans lesquels les corrections du moteur sont
    mortes, et qu'aucun test Python ne verrait autrement.

    (a) `slotPayload()` doit envoyer `text` ET `on`. Sans eux le moteur retombe
        sur ses valeurs par défaut (`text=""`, `on=True`) et `n_from_template`
        redevient la borne supérieure qu'on vient de corriger — silencieusement,
        car rien ne planterait.
    (b) `commit()` doit effacer la preuve d'aller-retour. « 215 octets relus à
        l'identique » reste vrai du fichier déjà écrit, mais affiché à côté
        d'une table qu'on vient de modifier c'est une affirmation sur un
        fichier qui n'existe plus. Mesuré à l'écran avant correction : la
        phrase survivait à l'édition d'une cellule.
    """
    import pathlib
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-data.js").read_text(encoding="utf-8")
    i = js.index("function slotPayload()")
    corps = js[i:i + 400]
    for cle in ("text: s.text", "on: s.on"):
        assert cle in corps, f"slotPayload n'envoie plus {cle!r}"
    for appel in ('slots: slotPayload()', "blank_unfed: BLANKMODE"):
        assert appel in js, f"{appel!r} absent de l'appel au moteur"
    j = js.index("function commit()")
    assert "LASTEXPORT = null" in js[j:j + 700], \
        "commit() ne périme plus la preuve d'aller-retour"
    # et le marqueur de vide n'est JAMAIS écrit en clair dans une source :
    # invisible à la relecture, mangé par le premier outil qui normalise.
    assert chr(0x200B) not in js, "U+200B littéral dans mod-data.js"
    py = (pathlib.Path(__file__).resolve().parents[2] / "backend" / "app"
          / "services" / "cards" / "data.py").read_text(encoding="utf-8")
    assert chr(0x200B) not in py, "U+200B littéral dans data.py"
    assert D.BLANK == chr(0x200B) and D.BLANK.strip() != ""


def _sans_commentaires(f):
    import re as _re
    src = f.read_text(encoding="utf-8")
    if f.suffix == ".py":
        src = _re.sub(r"(?m)^\s*#.*$", "", src)
        src = _re.sub(r'"""(?:.|\n)*?"""', "", src)
    else:
        src = _re.sub(r"/\*(?:.|\n)*?\*/", "", src)
        src = _re.sub(r"(?m)^\s*//.*$", "", src)
    return src


def _mes_fichiers():
    import pathlib
    racine = pathlib.Path(__file__).resolve().parents[2]
    return [racine / "frontend" / "cardforge" / "js" / "mod-data.js",
            racine / "frontend" / "cardforge" / "css" / "mod-data.css",
            racine / "backend" / "app" / "services" / "cards" / "data.py"]


def test_ma_piece_naffiche_aucun_chiffre_quelle_ne_produit_pas():
    """EXIGENCE (2) — la moitié mesurable du cahier des charges : 300 DPI avec
    fond perdu et zone de sécurité, glTF/GLB avec le jeu de maps PBR complet.

    LA RÈGLE A CHANGÉ DE FORME, ET C'EST VOULU. Au tour précédent ce test
    interdisait les mots : la pièce ne produisait aucun fichier image, donc
    elle n'avait rien à en dire. Depuis, elle en produit un — « Mesurer sur la
    carte livrée » rend deux PNG par `CF.cardBlob` et les lit octet par octet.
    L'interdiction deviendrait un bâillon : elle empêcherait d'écrire la seule
    chose que la consigne réclame, « vérifie-la toi-même sur les fichiers réels
    et pas sur l'interface ».

    La règle est donc : ces mots ne s'écrivent QUE là où la pièce mesure. Ce
    qu'elle ne produit toujours pas — glTF, GLB, maps PBR — reste interdit, mot
    pour mot, sur les octets des trois fichiers.
    """
    import re as _re
    # 1. ce qu'elle ne produit PAS : silence total, hors commentaires
    jamais = _re.compile(r"(?i)\b(pbr|gltf|glb|basecolor|roughness|metallic"
                         r"|normal_?map|ao_?map|occlusion)\b")
    for f in _mes_fichiers():
        assert f.is_file(), f
        trouve = jamais.findall(_sans_commentaires(f))
        assert not trouve, f"{f.name} annonce {trouve} sans rien en produire"
    # 2. ce qu'elle mesure : le mot n'a le droit d'exister qu'avec la mesure
    js = _sans_commentaires(_mes_fichiers()[0])
    py = _sans_commentaires(_mes_fichiers()[2])
    dit = _re.compile(r"(?i)(dpi|fond perdu|zone sûre)").findall(js)
    if dit:
        for cle in ("askPng(", "geomProof(", "pngcheck", "aucun chunk pHYs"):
            assert cle in js, (f"mod-data.js écrit {set(dit)} sans {cle!r} : "
                               "un chiffre affiché sans la mesure qui le prouve")
        # et JAMAIS une résolution en dur : elle vient du document
        assert not _re.search(r"\b300\s*(?:DPI|dpi)\b", js), \
            "une résolution écrite en dur dans l'écran"
        assert "G.dpi" in js and "g.dpi" in js
    if _re.search(r"(?i)\bdpi\b", py):
        assert "def png_report(" in py and "pHYs" in py, \
            "data.py parle de résolution sans lire le chunk qui la porte"


# ═══════════════════════════════════════════════════════════════════════════
#  TOUR 2 — CE QUI RESTAIT DEBOUT APRÈS LE RE-DUEL
#
#  Les deux critiques, séparément, ont fini sur le même reproche : « le filtre
#  reste une petite langue à apprendre : 12 opérateurs, et on tape `atk > 1` au
#  clavier. Il n'y a aucun constructeur de condition à la souris — donc sur ce
#  point précis il fait exactement ce qu'il reproche à l'autre, écrire du texte
#  à la main. » Plus trois chiffres d'écran qui ne se prouvaient pas : les
#  vignettes des jeux d'essai (recopiées à la main), la résolution d'image
#  (dépendante de la casse du système de fichiers) et son dénominateur (coupé
#  aux 2000 premières lignes en silence).
# ═══════════════════════════════════════════════════════════════════════════

CSV_T2 = (
    "nom;atk;rarete;qty\r\n"
    "Garde du pont;2;commune;1\r\n"
    "Sentinelle fêlée;7;rare;2\r\n"
    "Rebut;9;épique;1\r\n"
    "Écho;1;commune;3\r\n"
)


def _clause_ecrite(col: str, sym: str, val: str) -> str:
    """Ce que le constructeur de l'écran ÉCRIT — mêmes règles de citation que
    `refCol`/`litVal` dans mod-data.js. Les deux sont vérifiés l'un contre
    l'autre par `test_t2_lecran_et_le_moteur_citent_pareil`."""
    import re as _re
    bare = bool(_re.match(r"^[A-Za-z_][A-Za-z0-9_.\-]*$", col))
    c = col if bare else "[" + col + "]"
    if _re.match(r"^[+-]?\d+(?:[.,]\d+)?$", val or ""):
        v = val
    elif '"' in val:
        v = "'" + val + "'"
    else:
        v = '"' + val + '"'
    return c + " " + sym + " " + v


@pytest.mark.parametrize("op", [o["sym"] for o in D.FILTER_OPS])
def test_t2_le_constructeur_ecrit_ce_que_le_moteur_lit(op):
    """LE REPROCHE, LE VRAI : il fallait TAPER. Le constructeur à la souris
    fabrique la condition — mais s'il l'écrivait dans un dialecte que le moteur
    ne lit pas, on aurait juste déplacé le problème d'un cran.

    Chacun des opérateurs servis par /grammar est donc écrit comme l'écran
    l'écrit — nom de colonne AVEC UN ESPACE (donc entre crochets) et valeur
    citée — puis compilé et exécuté sur une vraie table. Un opérateur qui ne
    survivrait pas à la citation serait un bouton qui ment.
    """
    t = _parse(CSV_T2)
    val = {"contient": "sentinelle", "commence par": "Garde",
           "finit par": "pont"}.get(op, "2")
    col = "nom" if op in ("contient", "commence par", "finit par") else "atk"
    expr = _clause_ecrite(col, op, val)
    pred = D.compile_filter(expr, t["columns"])
    dicts = [{t["columns"][j]: r[j] for j in range(len(t["columns"]))}
             for r in t["rows"]]
    n = sum(1 for d in dicts if pred(d))
    assert n >= 1, (expr, "aucune ligne : la condition écrite ne mord pas")
    # et le nom de colonne à espaces passe aussi, entre crochets
    t2 = _parse("nom de carte;atk\r\nGarde du pont;2\r\n")
    e2 = _clause_ecrite("nom de carte", "contient", "garde")
    assert e2.startswith("[nom de carte]"), e2
    p2 = D.compile_filter(e2, t2["columns"])
    assert p2({"nom de carte": "Garde du pont", "atk": "2"}) is True


def test_t2_lecran_et_le_moteur_citent_pareil():
    """Les deux règles de citation de l'écran (`refCol`, `litVal`) doivent
    suivre le tokeniseur du moteur, sinon le constructeur produit du texte
    invalide dès qu'une colonne porte un espace. On lit la source de l'écran :
    aucun test Python ne verrait cette dérive autrement.
    """
    import pathlib
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-data.js").read_text(encoding="utf-8")
    for cle in ("function refCol(", "function litVal(", "function addClause(",
                "function removeClause(", "function clauseText("):
        assert cle in js, f"{cle!r} absent : le constructeur a disparu"
    # il ÉCRIT dans le même champ que la saisie — un seul réglage, une vérité
    i = js.index("function addClause(")
    corps = js[i:i + 900]
    assert "T.filter =" in corps and "commit()" in corps
    # et il parenthèse quand il le faut (priorité de « et » sur « ou »)
    assert "top_or" in corps, "la priorité et/ou n'est plus gardée"
    # la valeur inexprimable est REFUSÉE, pas fabriquée de travers
    j = js.index("function litVal(")
    assert "return null" in js[j:j + 500]


def test_t2_les_pastilles_partitionnent_le_filtre_sans_le_reecrire():
    """Les pastilles sont la vue du découpage du MOTEUR (`clause_split`), pas
    d'un second analyseur écrit dans l'écran. Deux propriétés les rendent sûres,
    et les voici mesurées :

      · recoller les pastilles avec « et » redonne EXACTEMENT la sélection de
        départ (donc en retirer une ne réécrit rien d'autre) ;
      · quand il y a un « ou » de premier niveau, il n'y a qu'UNE pastille —
        sinon on découperait une expression dont aucune moitié n'est vraie
        seule.
    """
    t = _parse(CSV_T2)
    dicts = [{t["columns"][j]: r[j] for j in range(len(t["columns"]))}
             for r in t["rows"]]
    for expr in ("atk > 1 et rarete = rare",
                 "atk > 1 et rarete = rare et nom contient e",
                 "(atk > 1 ou atk = 1) et nom commence par G",
                 "atk > 1 ou rarete = rare"):
        rep = D.clause_report(expr, t["columns"], t["rows"])
        parts = [c["expr"] for c in rep["clauses"]]
        recolle = " et ".join(parts)
        a = [D.compile_filter(expr, t["columns"])(d) for d in dicts]
        b = [D.compile_filter(recolle, t["columns"])(d) for d in dicts]
        assert a == b, (expr, recolle)
        if rep["top_or"]:
            assert len(parts) == 1, (expr, parts)
    # retirer une pastille = retirer cette condition, et rien d'autre
    rep = D.clause_report("atk > 1 et rarete = rare", t["columns"], t["rows"])
    reste = " et ".join([c["expr"] for c in rep["clauses"][1:]])
    assert reste == "rarete = rare"


def test_t2_le_poids_de_chaque_condition_est_mesure():
    """Le chiffre affiché sur chaque pastille — « retient N / M » — est compté
    par le moteur sur la table, pas estimé. C'est ce qui manquait pour CHOISIR
    quelle condition retirer.
    """
    t = _parse(CSV_T2)
    rep = D.clause_report("atk > 1 et rarete = rare", t["columns"], t["rows"])
    assert rep["n_active"] == 4
    poids = {c["expr"]: c["n_kept"] for c in rep["clauses"]}
    assert poids["atk > 1"] == 3, poids           # Garde 2, Sentinelle 7, Rebut 9
    assert poids["rarete = rare"] == 1, poids     # Sentinelle seule
    # et le ET des deux vaut bien l'intersection, comptée par /build
    out = _build(t, expr="atk > 1 et rarete = rare")
    assert out["stats"]["n_kept"] == 1
    # les lignes DÉSACTIVÉES sortent du dénominateur : le compteur du haut et
    # celui des pastilles doivent parler de la même population.
    rep2 = D.clause_report("atk > 1", t["columns"], t["rows"], off=[0, 3])
    assert rep2["n_active"] == 2 and rep2["clauses"][0]["n_kept"] == 2


def test_t2_la_route_check_sert_les_pastilles_et_ne_tombe_jamais():
    t = _parse(CSV_T2)
    r = _api("POST", BASE + "/check",
             json={"columns": t["columns"], "rows": t["rows"],
                   "filter": "atk > 1 et rarete = rare"})
    assert r.status_code == 200, r.text
    c = r.json()["check"]
    assert c["ok"] is True and c["n_active"] == 4
    assert [x["expr"] for x in c["clauses"]] == ["atk > 1", "rarete = rare"]
    assert [x["n_kept"] for x in c["clauses"]] == [3, 1]
    assert c["top_or"] is False and c["top_and"] is True
    # un filtre fautif ne fait toujours pas d'erreur HTTP, et rend 0 pastille
    r2 = _api("POST", BASE + "/check",
              json={"columns": t["columns"], "rows": t["rows"],
                    "filter": "atk >>"})
    assert r2.status_code == 200
    assert r2.json()["check"]["ok"] is False
    assert r2.json()["check"]["clauses"] == []
    # sans table, les pastilles existent mais sans poids : on n'invente pas
    r3 = _api("POST", BASE + "/check",
              json={"columns": t["columns"], "filter": "atk > 1 et rarete = rare"})
    c3 = r3.json()["check"]
    assert c3["n_active"] is None
    assert [x["n_kept"] for x in c3["clauses"]] == [None, None]


def test_t2_la_resolution_dimage_ne_depend_plus_du_disque():
    """LE CHIFFRE LE PLUS FRAGILE DE L'ÉCRAN, et personne ne l'avait vu.

    `(dossier / nom).is_file()` répond à la casse du SYSTÈME DE FICHIERS :
    « OCTO.PNG » trouve `octo.png` sous Windows et ne le trouve pas sous ext4.
    Le même CSV, le même dossier, affichaient « 1 sur 1 » ici et « 0 sur 1 »
    chez l'imprimeur. Mesuré ici sur un index replié : identique partout, et
    l'URL rendue porte le nom RÉEL du fichier — pas celui qui a été tapé, qui
    ne serait servi que sur un disque insensible à la casse.
    """
    from app.config import settings
    lib = settings.images_path
    (lib / "t2_carte.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (lib / "T2_Autre.PNG").write_bytes(b"\x89PNG\r\n\x1a\n")
    d = D.resolve_art(["t2_carte.png", "T2_CARTE.PNG", "t2_autre.png",
                       "t2_carte.jpg", "t2_absente.png", "",
                       "D:/ailleurs/t2_carte.png", "https://x/y.png"], lib)
    par = {x["v"]: x for x in d["art"]}
    # 1. le nom exact
    assert par["t2_carte.png"]["ok"] is True
    assert par["t2_carte.png"]["url"] == "/api/images/t2_carte.png"
    # 2. la casse : trouvée, DITE, et l'URL porte le nom réel du fichier
    assert par["T2_CARTE.PNG"]["ok"] is True
    assert par["T2_CARTE.PNG"]["url"] == "/api/images/t2_carte.png"
    assert "casse" in par["T2_CARTE.PNG"]["why"]
    assert par["t2_autre.png"]["url"] == "/api/images/T2_Autre.PNG"
    # 3. l'extension n'est JAMAIS devinée — mais le voisin trouvé est nommé
    assert par["t2_carte.jpg"]["ok"] is False
    assert "t2_carte.png" in par["t2_carte.jpg"]["why"]
    assert "extension" in par["t2_carte.jpg"]["why"]
    # 4. l'absence dit qu'elle est une absence, sans inventer de voisin
    assert par["t2_absente.png"]["ok"] is False
    assert "introuvable" in par["t2_absente.png"]["why"]
    assert "contient" not in par["t2_absente.png"]["why"]
    # 5. le chemin est ignoré, et c'est ÉCRIT
    assert par["D:/ailleurs/t2_carte.png"]["ok"] is True
    assert "chemin ignoré" in par["D:/ailleurs/t2_carte.png"]["why"]
    # 6. les compteurs se refont de tête, et le dénominateur est nommé
    assert d["n"] == 7 and d["n_ok"] + d["n_missing"] == d["n"]
    assert d["n_case"] == 2
    assert d["n_files"] >= 2
    # et la même question posée deux fois rend la même réponse (index stable)
    assert D.resolve_art(["T2_CARTE.PNG"], lib)["n_ok"] == 1


def test_t2_artcheck_regarde_toutes_les_lignes():
    """L'écran coupait à 2000 valeurs : sur une table de 2400 lignes, les 400
    dernières n'étaient jamais vérifiées et le compteur disait quand même
    « n sur n ». La coupe est retirée côté écran (le moteur borne à MAX_ROWS,
    qui est déjà la borne de la table elle-même)."""
    import pathlib
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-data.js").read_text(encoding="utf-8")
    i = js.index("async function checkArt()")
    corps = js[i:i + 900]
    assert "vals.slice(0, 2000)" not in corps, "la coupe silencieuse est revenue"
    assert "values: vals" in corps
    # et la route tient la charge annoncée
    r = _api("POST", BASE + "/artcheck",
             json={"values": ["x%d.png" % k for k in range(D.MAX_ROWS)]})
    assert r.status_code == 200
    assert r.json()["n"] == D.MAX_ROWS
    r2 = _api("POST", BASE + "/artcheck",
              json={"values": ["x.png"] * (D.MAX_ROWS + 1)})
    assert r2.status_code == 400, "au-delà, c'est un refus net, pas une coupe"


def test_t2_les_vignettes_annoncent_ce_que_le_moteur_a_mesure():
    """Les chiffres des vignettes étaient ÉCRITS À LA MAIN dans data.py — « n:
    4 », « UTF-8 », « point-virgule » — à côté d'octets qui pouvaient changer
    sans eux. C'est le badge recopié qui finit par mentir.

    Ils sont maintenant relevés par le moteur sur les octets du jeu. Le test le
    vérifie jeu par jeu, en refaisant la mesure ; et il vérifie qu'elle SUIT les
    octets, en fabriquant un jeu différent.
    """
    import base64
    for s in D.samples():
        raw = base64.b64decode(s["b64"])
        t = D.parse_table(raw)
        assert s["bytes"] == len(raw)
        assert s["n"] == t["n_rows"] and s["n_cols"] == t["n_cols"]
        assert s["encoding"] == D.ENC_LABEL.get(t["encoding"], t["encoding"])
        assert s["sep"] == t["sep_label"]
        assert s["auto"] is True, "une vignette ne force jamais un réglage"
        assert s["workbook"] == bool(t["workbook"])
        p = s["preset"]
        out = D.build_deck(t["columns"], t["rows"], {}, p.get("qty_col") or None,
                           p.get("filter") or "", p.get("sort") or "")
        assert s["n_kept"] == out["stats"]["n_kept"]
        assert s["n_cards"] == out["stats"]["n_cards"]
        assert s["n_warn"] == len(t["warnings"])
        # l'avertissement est CITÉ mot pour mot, pas résumé
        assert s["warn0"] == (t["warnings"][0] if t["warnings"] else "")
    # la mesure SUIT les octets : on en fabrique d'autres, les chiffres bougent
    autre = D._measured({"id": "x", "label": "x", "hint": "", "file": "x.csv",
                         "preset": {},
                         "b64": base64.b64encode(
                             "a\tb\r\n1\t2\r\n3\t4\r\n5\t6\r\n".encode("utf-8")
                         ).decode("ascii")})
    assert autre["n"] == 3 and autre["n_cols"] == 2
    assert autre["sep"] == "tabulation" and autre["encoding"] == "UTF-8"
    # et l'écran affiche CES clés-là, pas les siennes
    import pathlib
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-data.js").read_text(encoding="utf-8")
    i = js.index("SAMPLES.forEach")
    bloc = js[i:i + 1400]
    for cle in ("s.n", "s.n_cols", "s.bytes", "s.encoding", "s.sep", "s.auto"):
        assert cle in bloc, f"la vignette n'affiche plus {cle}"


def test_t2_le_jeu_des_pieges_tient_les_cinq_pieges():
    """« Le jeu d'essai est parfaitement formé : aucune ligne à colonnes en trop
    ou en moins, aucun champ entre guillemets, aucun séparateur présent dans une
    valeur. Rien n'est donc prouvé sur le seul endroit où un importateur CSV
    casse vraiment. » — Le sixième jeu embarqué EST cet endroit, et il est à la
    VIRGULE, donc c'est le cas symétrique que le critique disait non testé.
    """
    import base64
    s = {x["id"]: x for x in D.samples()}["pieges"]
    t = D.parse_table(base64.b64decode(s["b64"]))
    assert t["sep"] == "," and t["encoding"] == "utf-8"
    assert t["n_rows"] == 5 and t["n_cols"] == 4
    val = {r[0]: r[3] for r in t["rows"]}
    # 1. la virgule DANS un champ cité, avec la virgule pour séparateur
    assert val["Écho"] == "Ne fait rien, très bien"
    # 2. le guillemet doublé
    assert val["Rebut"] == 'il dit "bonjour" ici'
    # 3. le retour à la ligne DANS une cellule
    assert "\n" in val["Oracle"] and val["Oracle"].endswith("la seconde")
    # 4. les autres séparateurs, présents comme du texte, ne découpent rien
    assert val["Golem"] == "a;b|c et une tabulation\tici"
    # 5. la ligne à colonnes en trop est COMPTÉE, pas réparée en silence
    assert t["n_ragged_long"] == 1 and t["n_values_lost"] == 2
    assert "PLUS de 4 champs" in " ".join(t["warnings"])
    # et l'aller-retour rend les mêmes cellules, guillemets et sauts compris
    rendu = D.write_csv(t["columns"], t["rows"], ",")
    assert D.parse_table(rendu)["rows"] == t["rows"]


def test_t2_les_exemples_et_le_contenu_de_demonstration_sont_neutres():
    """CONTRÔLE DE LOYAUTÉ, et il porte sur MES octets.

    L'audit du tour 1 a dû poser un pavé gris sur le champ de filtre : son
    exemple disait `nom contient "octo"` — le nom de la mascotte du projet,
    glissé dans le contenu de démonstration d'un seul côté d'un duel aveugle.
    Le jeton est retiré à la source (exemple servi ET jeux d'essai), donc il
    n'y a plus rien à masquer.

    Deuxième moitié : l'exemple du champ ne doit plus nommer une colonne qui
    n'existe pas dans la table chargée (« atk » quand le fichier dit
    « attaque »). Il se calcule sur les entêtes réelles.
    """
    import pathlib
    import re as _re
    racine = pathlib.Path(__file__).resolve().parents[2]
    js = (racine / "frontend" / "cardforge" / "js" / "mod-data.js").read_text(
        encoding="utf-8")
    py = (racine / "backend" / "app" / "services" / "cards" / "data.py").read_text(
        encoding="utf-8")
    # a) le jeton de marque : nulle part dans ce qui est SERVI ou AFFICHÉ
    servi = _re.sub(r"(?m)^\s*#.*$", "", py)
    servi = _re.sub(r'"""(?:.|\n)*?"""', "", servi)
    affiche = _re.sub(r"/\*(?:.|\n)*?\*/", "", js)
    affiche = _re.sub(r"(?m)^\s*//.*$", "", affiche)
    for src, nom in ((servi, "data.py"), (affiche, "mod-data.js")):
        assert "octo" not in src.lower(), f"jeton de marque dans {nom}"
    # b) l'exemple du filtre est CALCULÉ sur les colonnes de la table
    assert "placeholder = hintFilter()" in js
    assert "placeholder = hintSort()" in js
    assert "function hintFilter()" in js and "function numCol()" in js
    # c) et les jeux d'essai n'en portent pas non plus
    for x in D.samples():
        assert "octo" not in x["label"].lower()
        assert "octo" not in x["hint"].lower()
        import base64
        assert b"octo" not in base64.b64decode(x["b64"]).lower()


# ═══════════════════════════════════════════════════════════════════════════
#  TOUR 3 — LA REVUE DE MON PROPRE AFFICHAGE, CHIFFRE PAR CHIFFRE
#
#  Consigne : « tout chiffre, badge ou mention affiché par ton interface doit
#  être vrai, prouvé sur les octets. Ce que tu ne peux pas prouver, tu le
#  corriges ou tu le retires. » Deux affirmations n'ont pas survécu à la
#  mesure, et elles sont ici :
#
#   1. « sans BOM — octet pour octet » sur la case d'export, et son infobulle
#      « le fichier rendu est l'octet pour octet de celui qu'on a importé ».
#      RIEN ne le mesurait. Mesuré sur les six jeux que cet écran propose
#      lui-même : FAUX sur quatre.
#   2. « 0 valeur inventée sur les 10 cartes », pendant que le bandeau du
#      cadre imprimait « RARE » sur les dix, dont sept que le fichier
#      contredit. Le chiffre était juste sur `card.fields` et faux sur le
#      fichier livré : sa PORTÉE n'était pas écrite.
# ═══════════════════════════════════════════════════════════════════════════

def _racine():
    import pathlib
    return pathlib.Path(__file__).resolve().parents[2]


def _js_data():
    return (_racine() / "frontend" / "cardforge" / "js"
            / "mod-data.js").read_text(encoding="utf-8")


def _fn(js: str, nom: str) -> str:
    """Le CORPS d'une fonction de mod-data.js, du `function nom(` jusqu'à la
    suivante.

    Les tests découpaient une fenêtre de N caractères (`js[i:i + 6000]`). Ce
    n'est pas une lecture, c'est un pari : une correction de dix lignes déplace
    la fin de la fonction hors de la fenêtre et le test échoue sans qu'aucune
    règle n'ait été violée — ce qui est arrivé exactement ici. Les fonctions du
    module sont toutes à deux espaces d'indentation : on coupe à la suivante.
    """
    i = js.index("function " + nom + "(")
    j = js.find("\n  function ", i + 1)
    return js[i:] if j < 0 else js[i:j]


def test_t3_le_fichier_rendu_nest_pas_toujours_loctet_pour_octet_de_lentree():
    """LA MESURE QUI CONDAMNE L'ANCIENNE ÉTIQUETTE.

    Les six jeux embarqués, relus puis réécrits au réglage PAR DÉFAUT (sans
    BOM), comparés octet par octet à leurs propres octets d'entrée. Deux
    reviennent identiques, quatre ne peuvent pas : c'est une propriété du
    format, pas un défaut — un fichier lu en Windows-1252 ressort en UTF-8, un
    BOM d'entrée n'est pas rendu quand la case est décochée, un classeur est
    une archive. Ce qui était un défaut, c'est de l'AFFIRMER pour tous.
    """
    import base64
    verdict = {}
    for s in D.samples():
        raw = base64.b64decode(s["b64"])
        t = D.parse_table(raw)
        sep = t["sep"] or ";"
        rendu = D.write_csv(t["columns"], t["rows"], sep, False)
        verdict[s["id"]] = (rendu == raw, len(raw), len(rendu))
    # ceux qui DOIVENT revenir identiques : de l'UTF-8 sans BOM, bien formé.
    for i in ("parite", "charge"):
        assert verdict[i][0], (i, verdict[i])
    # et ceux pour lesquels l'ancienne étiquette mentait, avec leur écart réel
    for i in ("ansi", "bom", "pieges", "classeur"):
        assert not verdict[i][0], (i, "l'étiquette redeviendrait vraie ici : "
                                   "revoir le texte de l'écran")
    assert verdict["ansi"][1] == 205 and verdict["ansi"][2] == 226
    assert verdict["bom"][1] - verdict["bom"][2] == 3      # le BOM d'entrée
    # la position de la première divergence, celle que l'écran affiche
    raw = base64.b64decode({x["id"]: x for x in D.samples()}["ansi"]["b64"])
    t = D.parse_table(raw)
    rendu = D.write_csv(t["columns"], t["rows"], t["sep"], False)
    at = next(i for i in range(min(len(raw), len(rendu))) if raw[i] != rendu[i])
    assert at == 33, at            # le premier « è » : 1 octet contre 2


def test_t3_lecran_mesure_les_octets_au_lieu_de_les_promettre():
    """L'étiquette ne promet plus : elle décrit son geste, et le RÉSULTAT est
    mesuré après chaque export, première divergence comprise.
    """
    import re as _re
    js = _js_data()
    # les deux affirmations retirées, mot pour mot — cherchées dans ce qui est
    # AFFICHÉ, pas dans les commentaires : la prose a le droit de raconter la
    # phrase qu'on vient de retirer, c'est même comme ça qu'on la retrouve.
    aff = _re.sub(r"/\*(?:.|\n)*?\*/", "", js)
    aff = _re.sub(r"(?m)^\s*//.*$", "", aff)
    assert "sans BOM — octet pour octet" not in aff
    assert "le fichier rendu est l'octet pour octet" not in aff
    # ce qui les remplace : une comparaison, et elle porte sur les OCTETS
    assert "function compareToSource(" in js
    i = js.index("function compareToSource(")
    corps = js[i:i + 2600]
    for cle in ("SRC.bytes", "new Uint8Array(buf)", "a[i] !== b[i]",
                "première différence à l'octet", "identique aux "):
        assert cle in corps, f"{cle!r} absent de la comparaison"
    # les octets d'origine sont gardés à l'import, et périmés à la mutation
    assert "bytes: new Uint8Array(buf.slice(0))" in js
    j = js.index("function commit()")
    assert "SRCDIRTY = true" in js[j:j + 1400], \
        "commit() ne périme pas la comparaison aux octets d'origine"
    # et une table modifiée ne se compare pas : on le DIT au lieu de se taire
    assert "la table a changé depuis l'import" in corps


def test_t3_la_table_des_raretes_ne_derive_pas_de_la_piece_02():
    """LE RISQUE ASSUMÉ, ET SA LAISSE. Pour nommer le mot que le cadre
    imprime, le moteur porte une copie de la table des raretés de la pièce 02.
    Une table recopiée finit par mentir : celle-ci est confrontée à sa source à
    chaque exécution de la suite. Si P2 ajoute, renomme ou traduit une rareté,
    ce test tombe avant que l'écran n'annonce un mot qui n'est plus imprimé.
    """
    import re as _re
    src = (_racine() / "frontend" / "cardforge" / "js"
           / "mod-frame.js").read_bytes().decode("utf-8")
    bloc = _re.search(r"const RARITIES = \[(.*?)\];", src, _re.S)
    assert bloc, "la table des raretés de la pièce 02 est introuvable"
    couples = _re.findall(r'id:\s*"([^"]+)",\s*label:\s*"([^"]+)"', bloc.group(1))
    assert tuple(couples) == D.FRAME_RARITY, (couples, D.FRAME_RARITY)
    # le DÉFAUT de la pièce 02 : bandeau allumé, rareté « rare ». C'est lui qui
    # fait qu'un document jamais touché imprime quand même « RARE ».
    defs = _re.search(r"const DEFAULTS = \{(.*?)\n  \};", src, _re.S)
    assert defs, "les défauts de la pièce 02 sont introuvables"
    assert _re.search(r'rarity:\s*"(\w+)"', defs.group(1)).group(1) \
        == D.FRAME_DEFAULT_RARITY
    assert _re.search(r"\bbanner:\s*(\w+)", defs.group(1)).group(1) == "true"
    # et la règle du mot imprimé : `banner_text` sinon le libellé, en capitales
    regle = [x for x in src.splitlines()
             if "banner_text ||" in x and "toUpperCase()" in x]
    assert regle, "la règle du bandeau de la pièce 02 a changé de forme"
    assert D.frame_word({}) == ("RARE", "rareté du cadre")
    assert D.frame_word({"banner_text": " promo "})[0] == "PROMO"
    assert D.frame_word({"rarity": "mythic"})[0] == "MYTHIQUE"
    assert D.frame_word({"rarity": "inconnue"})[0] == "RARE"   # comme P2
    assert D.frame_word({"banner": False}) == ("", "")


def test_t3_le_bandeau_du_cadre_est_confronte_a_la_colonne_de_rarete():
    """LE PLUS GROS MANQUE DU TOUR PRÉCÉDENT, MESURÉ SUR LE JEU QUE CET ÉCRAN
    PROPOSE AU PREMIER CLIC.

    Le reproche : « bandeau RARE imprimé sur les 20 cartes alors que la donnée
    dit mythique — contradiction directe entre le cadre et le fichier, non
    détectée par ses propres compteurs ». Il ne passe par AUCUN slot : aucun
    compteur de `card.fields` ne pouvait le voir, et « 0 valeur inventée »
    s'affichait pendant que sept cartes sur dix partaient avec un mot faux.
    """
    import base64
    s = {x["id"]: x for x in D.samples()}["parite"]
    t = D.parse_table(base64.b64decode(s["b64"]))
    p = s["preset"]
    out = D.build_deck(t["columns"], t["rows"], {"nom": "title"},
                       p["qty_col"], p["filter"], p["sort"], None,
                       [{"id": "title", "label": "Titre", "text": "", "on": True}],
                       True, {})                    # {} = cadre jamais touché
    fr = out["stats"]["audit"]["frame"]
    assert out["stats"]["n_cards"] == 10
    assert fr["word"] == "RARE" and fr["from"] == "rareté du cadre"
    assert fr["col"] == "rarete"                     # trouvée par CONCEPT
    assert fr["n_cards"] == 10
    assert fr["n_match"] == 3 and fr["n_clash"] == 7
    assert fr["clash"] == [{"v": "épique", "n": 5}, {"v": "commune", "n": 2}]
    # le compte est en CARTES, pas en lignes : il parle la langue du bandeau
    assert fr["n_match"] + fr["n_clash"] == out["stats"]["n_cards"]
    # accents et casse ne comptent pas : « Épique » et « épique » sont le même
    out2 = D.build_deck(t["columns"], t["rows"], {"nom": "title"},
                        p["qty_col"], p["filter"], p["sort"], None, None,
                        True, {"rarity": "epic"})
    assert out2["stats"]["audit"]["frame"]["n_match"] == 5    # les 5 Rebut
    # bandeau éteint : aucune alerte, et surtout aucune affirmation
    out3 = D.build_deck(t["columns"], t["rows"], {"nom": "title"},
                        p["qty_col"], p["filter"], p["sort"], None, None,
                        True, {"banner": False})
    assert out3["stats"]["audit"]["frame"] is None
    # aucune colonne de rareté : le mot est un choix de mise en page, pas une
    # contradiction — on le signale, on ne l'accuse pas.
    t2 = _parse("nom;atk\r\nRebut;9\r\n")
    out4 = D.build_deck(t2["columns"], t2["rows"], {"nom": "title"},
                        None, "", "", None, None, True, {})
    fr4 = out4["stats"]["audit"]["frame"]
    assert fr4["col"] is None and fr4["n_clash"] == 0 and fr4["word"] == "RARE"


def test_t3_le_cadre_passe_par_la_route_et_ne_fait_jamais_500():
    """La mesure doit exister DE BOUT EN BOUT : l'écran l'envoie, la route la
    rend. Et un `frame` mal formé ne casse rien — l'écran lit un document, pas
    un formulaire validé.
    """
    t = _parse("nom;atk;qty;rarete\r\nRebut;9;2;épique\r\n")
    body = {"columns": t["columns"], "rows": t["rows"], "qty_col": "qty",
            "map": {"nom": "title"}, "frame": {}}
    r = _api("POST", BASE + "/build", json=body)
    assert r.status_code == 200, r.text
    fr = r.json()["stats"]["audit"]["frame"]
    assert fr["word"] == "RARE" and fr["n_clash"] == 2 and fr["col"] == "rarete"
    for mauvais in ("texte", 12, [1, 2], None):
        b2 = dict(body)
        b2["frame"] = mauvais
        r2 = _api("POST", BASE + "/build", json=b2)
        assert r2.status_code == 200, (mauvais, r2.text)
        assert r2.json()["stats"]["audit"]["frame"] in (None, fr) \
            or r2.json()["stats"]["audit"]["frame"]["word"] == "RARE"


def test_t3_lecran_envoie_le_cadre_et_ecrit_la_portee_de_son_compteur():
    """Les trois gestes de l'écran sans lesquels la correction est morte, et
    qu'aucun test Python ne verrait autrement.
    """
    js = _js_data()
    assert "function frameOf()" in js
    assert "frame: frameOf()" in js, "le cadre ne part pas avec la table"
    i = js.index("function frameOf()")
    for cle in ("banner:", "banner_text:", "rarity:"):
        assert cle in js[i:i + 400], f"{cle!r} n'est pas envoyé"
    # la PORTÉE est écrite dans la phrase : c'est ça, la correction
    assert "valeur inventée <b>dans les slots</b>" in js
    # l'alerte est nommée, et elle renvoie là où ça se règle
    assert "function frameLine(" in js and "au.frame" in js
    j = js.index("function frameLine(")
    corps = js[j:j + 2200]
    assert "02 Cadre" in corps and "n_clash" in corps
    # le mot du cadre a sa ligne dans la table de provenance
    assert "Bandeau du cadre" in js
    # et un changement de cadre relance le compte
    assert 'p.id === "frame"' in js
    # la table des raretés n'est PAS recopiée dans l'écran : un seul exemplaire
    for mot in ('"Peu commune"', '"Légendaire"', '"mythic"'):
        assert mot not in js, f"la table des raretés est recopiée : {mot}"


def test_t3_la_mesure_sur_la_carte_livree_lit_le_vrai_fichier():
    """« Pour chaque chiffre affiché, écris la mesure qui le prouve — pas la
    valeur du curseur, la mesure sur le fichier produit. »

    Le bouton « Mesurer sur la carte livrée » rend la carte par le même appel
    que l'export (`CF.cardBlob`), lit les dimensions dans l'en-tête IHDR du
    PNG plutôt que sur la toile, compare les deux tirages pixel par pixel, et
    mesure son propre plancher de bruit avant de conclure. Il cherche aussi à
    se prendre en défaut : deux branches de CONTRADICTION.
    """
    js = _js_data()
    for cle in ("function readIHDR(", "function snapDelivered(",
                "function countDiff(", "function measureDelivered(",
                "function paintDeliv("):
        assert cle in js, f"{cle!r} absent"
    i = js.index("function snapDelivered(")
    corps = js[i:i + 900]
    assert "CF.cardBlob(" in corps, "la mesure ne porte pas sur le fichier livré"
    assert "readIHDR(u)" in corps and "arrayBuffer()" in corps
    # l'en-tête est lu sur les octets, signature comprise
    k = js.index("function readIHDR(")
    assert "137, 80, 78, 71" in js[k:k + 400], "la signature PNG n'est pas vérifiée"
    assert '"IHDR"' in js[k:k + 400]
    # le plancher de bruit : deux rendus du MÊME état avant de conclure
    mes = _fn(js, "measureDelivered")
    assert "const noise = countDiff(" in mes
    assert "BLANKMODE = !was" in mes and "BLANKMODE = was" in mes
    # et les deux contradictions cherchées
    pd = _fn(js, "paintDeliv")
    assert pd.count("CONTRADICTION") >= 2
    assert "d.diff <= d.noise" in pd and "d.diff > d.noise" in pd


def test_t3_les_compteurs_perimes_sont_eteints_pendant_la_reconstruction():
    """« lignes » vient de la table de maintenant, « retenues / cartes / du
    gabarit » de la construction précédente : pendant la temporisation de
    240 ms, quatre chiffres côte à côte décrivent deux tables. On ne peut pas
    les avancer — c'est le moteur qui les rend, en un exemplaire — donc on les
    éteint et on l'écrit.
    """
    js = _js_data()
    i = js.index("function schedule(")
    assert "PENDING = true" in js[i:i + 300]
    j = js.index("async function rebuild()")
    assert "PENDING = false" in js[j:j + 1800]
    assert 'b.classList.toggle("stale"' in js
    assert "recalcul en cours" in js
    css = (_racine() / "frontend" / "cardforge" / "css"
           / "mod-data.css").read_text(encoding="utf-8")
    assert ".cf-data-meter.stale" in css
    # QUATRE s'éteignent, et le bandeau dit quatre : « lignes » vient de la
    # table de maintenant, il est juste, et l'éteindre ferait douter d'un
    # chiffre vrai. Le compte du texte et la portée du style doivent coller.
    assert "les 4 compteurs" in js
    assert "cf-data-mnum cf-data-mrows" in js
    assert ":not(.cf-data-mrows)" in css, \
        "le style éteint aussi le compteur qui, lui, est à jour"


def test_t3_une_cellule_multi_ligne_ne_ment_plus_a_lecran():
    """LE PLUS PETIT MENSONGE DE L'ÉCRAN, ET IL SE VOIT SUR UNE CAPTURE.

    Le jeu « Pièges » contient un retour à la ligne DANS une cellule. La donnée
    le garde — l'aller-retour le prouve sur les octets — mais un
    `<input type=text>` retire les retours à la ligne de sa valeur sans un mot :
    la table affichait « deux lignes :la seconde ». Une cellule qui montre
    autre chose que sa donnée est un chiffre faux comme un autre, et éditer
    cette cellule aurait perdu le retour pour de bon.
    """
    t = _parse('nom,texte\r\nOracle,"deux lignes :\r\nla seconde"\r\n')
    assert "\n" in t["rows"][0][1], t["rows"]      # la donnée les garde
    rendu = D.write_csv(t["columns"], t["rows"], ",")
    assert D.parse_table(rendu)["rows"] == t["rows"]   # et l'aller-retour aussi
    js = _js_data()
    assert 'td.classList.add("nl")' in js, "la cellule ne s'annonce pas"
    assert "retour(s) à la ligne" in js
    assert "raw0.split(" in js
    css = (_racine() / "frontend" / "cardforge" / "css"
           / "mod-data.css").read_text(encoding="utf-8")
    assert ".cf-data-td.nl" in css


def test_t3_le_resume_de_detection_est_compte_sur_les_jeux():
    """La ligne « 3 séparateurs · 3 encodages » de l'écran vide est un COMPTE
    fait sur les vignettes, pas un chiffre écrit à la main — sinon c'est le
    badge recopié qu'on vient de retirer partout ailleurs. On vérifie les deux
    bouts : l'écran dénombre, et le moteur fournit bien de quoi dénombrer 3, 3
    et 1.
    """
    import base64
    js = _js_data()
    assert "cf-data-detsum" in js
    i = js.index("cf-data-detsum")
    corps = js[max(0, i - 1500):i + 900]
    assert "seps.length" in corps and "encs.length" in corps
    import re as _re
    nu = _re.sub(r"/\*(?:.|\n)*?\*/", "", corps)
    assert not _re.search(r'"\s*3\s*séparateur', nu), "compte écrit en dur"
    seps, encs, wb = set(), set(), set()
    for x in D.samples():
        t = D.parse_table(base64.b64decode(x["b64"]))
        assert t["sep_auto"] and t["enc_auto"], x["id"]
        if t["workbook"]:
            wb.add(t["encoding"])
        else:
            seps.add(t["sep"])
            encs.add(t["encoding"])
    assert len(seps) == 3 and len(encs) == 3 and len(wb) == 1, (seps, encs, wb)


# ═══════════════════════════════════════════════════════════════════════════
#  TOUR 4 — LA CARTE LIVRÉE, LUE OCTET PAR OCTET, ET LE VERT QUI MENTAIT
#
#  Deux consignes, deux corrections.
#
#  (1) « Un audit a démontré, en redécodant les PNG à la main, qu'un badge
#      "16 bits" était FAUX : l'en-tête IHDR annonçait 16 bits et les
#      12 582 912 échantillons tombaient tous sur le réseau k·257, soit 200
#      valeurs distinctes = 7,64 bits utiles. Pire : deux verdicts successifs
#      ont dit l'inverse l'un de l'autre sur le même octet, parce que l'un
#      s'était arrêté à l'en-tête. »
#      Mon écran affichait « en-tête IHDR 815 × 1110, 8 bits/canal ». Les deux
#      dimensions étaient vraies ; la profondeur était lue dans une
#      DÉCLARATION, par le chemin exact qui a laissé passer le faux badge. Elle
#      est désormais MESURÉE : IDAT dégonflés, lignes défiltrées, valeurs
#      comptées, pas du réseau calculé.
#
#  (2) « 300 DPI avec fond perdu et zone de sécurité. Si ta pièce y touche,
#      vérifie-la toi-même sur les fichiers réels et pas sur l'interface. »
#      Elle y touchait par une pastille — reproche littéral du critique :
#      « il affiche du 300 DPI qu'il ne livre pas dans cette pièce ». Le
#      fichier de carte est maintenant lu : pHYs présent ou ABSENT (il est
#      absent, et on l'écrit), et les pixels re-dérivés des millimètres.
#
#  Et la pastille verte : « import 4 ligne(s) en 149 ms » s'affichait en VERT,
#  c'est-à-dire « seuil tenu », sur une mesure qui ne portait pas sur le seuil.
# ═══════════════════════════════════════════════════════════════════════════

def _png(w, h, bits, color, rows, extra=b""):
    """Un PNG fabriqué à la main : c'est le seul moyen d'écrire dans l'en-tête
    autre chose que ce que disent les échantillons."""
    import struct
    import zlib as _z

    def chunk(t, b):
        return (struct.pack(">I", len(b)) + t + b
                + struct.pack(">I", _z.crc32(t + b) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", w, h, bits, color, 0, 0, 0)
    brut = b"".join(b"\x00" + r for r in rows)      # filtre 0 sur chaque ligne
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + extra
            + chunk(b"IDAT", _z.compress(brut)) + chunk(b"IEND", b""))


def test_t4_un_entete_qui_ment_sur_la_profondeur_est_pris_en_defaut():
    """LE CAS EXACT DE L'AUDIT, REJOUÉ.

    Un PNG dont l'IHDR annonce 16 bits et dont TOUS les échantillons valent
    k·257 — une carte 8 bits élargie. Un lecteur qui s'arrête à l'en-tête
    répond « 16 bits » et se trompe. Le moteur redescend aux échantillons :
    200 valeurs distinctes, pas du réseau 257, 7,64 bits utiles.
    """
    import random
    random.seed(3)
    w = h = 64
    faux = _png(w, h, 16, 6, [bytes(b for _ in range(w * 4)
                                    for b in (lambda k: (k, k))(
                                        random.randrange(200)))
                              for _ in range(h)])
    r = D.png_report(faux)
    assert r["ok"] and r["deep"], r
    assert r["ihdr"]["bits"] == 16                      # ce que le fichier DIT
    assert r["distinct"] == 200                         # ce qu'il CONTIENT
    assert r["lattice_step"] == 257                     # le réseau de l'audit
    assert r["bits_effective"] == 7.64                  # au centième près
    assert r["widened_8bit"] is True
    # et un VRAI 16 bits ne se fait pas accuser à tort
    vrai = _png(w, h, 16, 6,
                [bytes(b for _ in range(w * 4)
                       for b in divmod(random.randrange(65536), 256))
                 for _ in range(h)])
    v = D.png_report(vrai)
    assert v["deep"] and v["lattice_step"] == 1 and v["widened_8bit"] is False
    assert v["bits_effective"] > 13


def test_t4_le_dpi_vient_du_chunk_phys_ou_de_nulle_part():
    """La résolution est ce que le fichier DÉCLARE, pas ce que l'écran espère.

    300 DPI s'écrivent 11811 pixels par mètre : 11811 × 0,0254 = 299,9994. Un
    fichier sans pHYs ne déclare RIEN, et le rapport le dit avec un `None` —
    surtout pas un 300 par défaut, qui serait le badge recopié qu'on passe
    trois tours à retirer.
    """
    import struct
    import zlib as _z
    corps = struct.pack(">IIB", 11811, 11811, 1)
    phys = (struct.pack(">I", len(corps)) + b"pHYs" + corps
            + struct.pack(">I", _z.crc32(b"pHYs" + corps) & 0xFFFFFFFF))
    avec = D.png_report(_png(8, 8, 8, 6, [bytes(8 * 4)] * 8, extra=phys))
    assert avec["phys"]["x"] == 11811 and avec["phys"]["unit"] == 1
    assert avec["dpi"] == 299.9994
    sans = D.png_report(_png(8, 8, 8, 6, [bytes(8 * 4)] * 8))
    assert sans["phys"] is None and sans["dpi"] is None
    assert "pHYs" not in sans["chunk_counts"]


def test_t4_le_canal_alpha_inutile_est_chiffre():
    """Reproche mesuré du tour précédent, sur les DEUX camps : « la carte livrée
    déclare un canal alpha dont les 904 650 pixels valent 255 ». On ne peut pas
    le retirer — la toile appartient au CORE — mais un défaut chiffré n'est plus
    un défaut caché.
    """
    w, h = 12, 5
    opaque = D.png_report(_png(w, h, 8, 6, [bytes([9, 9, 9, 255] * w)] * h))
    assert opaque["alpha"]["distinct"] == 1
    assert opaque["alpha"]["opaque"] is True
    assert opaque["alpha"]["bytes"] == w * h
    varie = D.png_report(_png(w, h, 8, 6, [bytes([9, 9, 9, 128] * w)] * h))
    assert varie["alpha"]["opaque"] is False and varie["alpha"]["max"] == 128


def test_t4_un_fichier_illisible_ne_rend_jamais_un_chiffre():
    """« Ce que tu ne peux pas prouver, tu le corriges ou tu le retires. »
    Quatre entrées qui ne se mesurent pas : aucune ne doit produire une
    profondeur, un DPI ou un nombre d'échantillons inventé.
    """
    for mauvais in (b"", b"coucou", b"\x89PNG\r\n\x1a\n", b"\x89PNG\r\n\x1a\ntronque"):
        r = D.png_report(mauvais)
        assert r["dpi"] is None and r["bits_effective"] is None
        assert r["deep"] is False and r["samples"] == 0
        assert r["error"] or r["deep_why"], mauvais
    # entrelacé : mesurable en principe, pas par ce défiltrage — et il le DIT
    import struct
    ent = bytearray(_png(8, 8, 8, 6, [bytes(8 * 4)] * 8))
    ent[8 + 8 + 12] = 1                       # octet « interlace » de l'IHDR
    ent[8 + 8 + 13:8 + 8 + 17] = struct.pack(
        ">I", __import__("zlib").crc32(bytes(ent[8 + 4:8 + 8 + 13])) & 0xFFFFFFFF)
    r = D.png_report(bytes(ent))
    assert r["deep"] is False and "entrelac" in r["deep_why"]
    assert r["bits_effective"] is None


def test_t4_la_route_pngcheck_repond_et_ne_fait_jamais_500():
    import base64
    r = _api("POST", BASE + "/pngcheck",
             json={"b64": base64.b64encode(
                 _png(6, 4, 8, 6, [bytes([1, 2, 3, 255] * 6)] * 4)).decode()})
    assert r.status_code == 200, r.text
    p = r.json()["png"]
    assert p["ihdr"]["w"] == 6 and p["ihdr"]["h"] == 4
    assert p["deep"] and p["samples"] == 6 * 4 * 4
    assert p["chunk_counts"]["IHDR"] == 1 and p["chunk_counts"]["IEND"] == 1
    for corps in (None, [], {"b64": "!!!"}, {"b64": base64.b64encode(b"x").decode()},
                  {"text": "pas un png"}):
        rr = _api("POST", BASE + "/pngcheck", json=corps)
        assert rr.status_code in (200, 400), (corps, rr.status_code, rr.text)
    assert _api("POST", "/api/cards/..%2f../data/pngcheck",
                json={"text": "x"}).status_code in (400, 404)
    from app.main import app
    assert "/api/cards/{did}/data/pngcheck" in app.openapi().get("paths", {})


def test_t4_lecran_ne_lit_plus_la_profondeur_dans_len_tete():
    """L'écran appelle le moteur sur les octets du fichier LIVRÉ, écrit que
    l'en-tête est une déclaration, et confronte SES deux lecteurs — le sien et
    celui du moteur — au lieu d'en croire un.
    """
    js = _js_data()
    assert "async function askPng(" in js
    i = js.index("async function askPng(")
    assert '"pngcheck"' in js[i:i + 400] and "deep: true" in js[i:i + 400]
    # le fichier envoyé est celui du mode courant, pas une toile refaite à côté
    m = js.index("async function measureDelivered(")
    mes = js[m:m + 3000]
    assert "askPng(a.buf)" in mes, "le moteur ne reçoit pas le fichier mesuré"
    d = js.index("function paintDeliv(")
    pd = js[d:d + 6000]
    assert "bits/canal ANNONCÉS" in pd and "une déclaration" in pd
    assert "Profondeur <b>effective</b>" in pd
    assert "R.widened_8bit" in pd and "l'en-tête MENT" in pd
    assert "R.lattice_step" in pd and "R.samples" in pd
    # les deux lecteurs, et le refus de conclure quand ils divergent
    assert pd.count("CONTRADICTION") >= 3
    assert "R.ihdr.bits !== ih.bits" in pd


def test_t4_lecran_ecrit_le_dpi_du_fichier_et_le_calcul_qui_le_prouve():
    """La pastille « 300 DPI » ne vaut plus par elle-même : le pHYs du fichier
    est affiché (ou son absence), et les pixels sont re-dérivés des
    millimètres, à côté de l'en-tête du fichier réellement rendu.
    """
    js = _js_data()
    assert "function geomProof(" in js and "function geomText(" in js
    i = js.index("function geomProof(")
    corps = js[i:i + 1400]
    # le calcul, pas la recopie de la table du CORE
    assert "mm / 25.4" in corps and "Math.round" in corps
    for cle in ("trim:", "canvas:", "safe:", "d.same"):
        assert cle in corps, cle
    pd = _fn(js, "paintDeliv")
    assert "aucun chunk pHYs" in pd and "ne déclare" in pd
    assert "R.phys" in pd and "R.dpi" in pd
    assert "geomText(G)" in pd, "le calcul n'est pas écrit à côté du fichier"
    g = js.index("function geomText(")
    gt = js[g:g + 900]
    assert "fond perdu" in gt and "zone sûre" in gt and "DPI" in gt
    # la géométrie est écrite AVANT toute mesure : une capture la porte
    assert "function geomLine(" in js
    assert "Aucun fichier mesuré pour l'instant" in js
    # 11811 px/m = 300 DPI : la constante du domaine est celle du moteur
    assert D.PX_PER_M_300 == 11811
    assert round(D.PX_PER_M_300 * 0.0254, 4) == 299.9994


def test_t4_le_vert_du_seuil_ne_sallume_quen_dessous_de_200_lignes():
    """« import 4 ligne(s) en 149 ms » s'affichait en VERT. Le vert de cette
    barre veut dire « seuil tenu », et le seuil du cahier des charges porte sur
    200 lignes : une couleur qui affirme sur une mesure qui ne porte pas est un
    chiffre faux avec une autre grammaire.
    """
    import re as _re
    js = _js_data()
    i = js.index('add("import "')
    bloc = js[i:i + 420]
    assert 'IMPORT_MS < 2000 ? "ok"' not in bloc, "le vert s'allume encore sur 4 lignes"
    assert 'IMPORTED_N >= 200 ? "ok"' in bloc
    assert 'IMPORT_MS >= 2000 ? "err"' in bloc
    # et le jeu qui permet de l'allumer existe vraiment, à 200 lignes
    charge = [s for s in D.samples() if s["id"] == "charge"]
    assert charge and charge[0]["n"] == 200, charge
    # les commentaires n'ont pas le droit de porter la correction tout seuls
    aff = _re.sub(r"/\*(?:.|\n)*?\*/", "", js)
    assert 'IMPORTED_N >= 200 ? "ok"' in aff


def test_t4_la_somme_des_postes_de_temps_est_faite_a_lecran():
    """Un juge additionne ce qu'il LIT. « 0,1 + 0,2 + 236 + 23 + 160 = 419,3 »
    à côté de « ces 418 ms » se lit comme une contradiction, alors que ce n'est
    que cinq arrondis. L'écran fait donc l'addition lui-même, sur les chiffres
    affichés — et la règle d'arrondi de l'affichage est la MÊME fonction que
    celle de la somme, sinon on aurait deux arrondis à réconcilier.
    """
    js = _js_data()
    i = js.index("function timingText(")
    corps = js[i:i + 1900]
    assert "somme des cinq postes affichés" in corps
    assert "const rv = (x)" in corps and ".reduce((a, x) => a + rv(x), 0)" in corps
    # UNE SEULE règle d'arrondi : l'affichage habille le nombre que la somme
    # additionne. Deux barèmes d'arrondi = deux vérités à réconcilier.
    assert corps.count("x < 0.05") == 1 and corps.count("x < 10") == 1
    assert "const v = rv(x);" in corps, "l'affichage n'arrondit pas par rv()"
    # et le total affiché reste la mesure, pas la somme des arrondis
    assert 'r(TIMING.total)' in corps


def test_t4_le_seuil_des_200_lignes_tient_par_la_route_pngcheck_comprise():
    """Le seuil de la spec, re-mesuré ici même : 200 lignes du jeu « Charge »,
    lues par la VRAIE route, en moins de 2 s. Et la lecture d'une carte de
    815 × 1110 en RVBA ne doit pas faire exploser le budget du bouton.
    """
    import base64
    b64 = [s for s in D.samples() if s["id"] == "charge"][0]["b64"]
    t0 = time.perf_counter()
    r = _api("POST", BASE + "/parse", json={"b64": b64, "name": "charge.tsv"})
    ms = (time.perf_counter() - t0) * 1000
    assert r.status_code == 200 and r.json()["table"]["n_rows"] == 200
    assert ms < 2000, f"{ms:.0f} ms pour 200 lignes"
    # la relecture d'un PNG de la taille d'une carte : mesurée, pas espérée
    px = _png(815, 1110, 8, 6, [bytes([7, 7, 7, 255] * 815)] * 1110)
    t1 = time.perf_counter()
    rep = D.png_report(px)
    dt = (time.perf_counter() - t1) * 1000
    assert rep["deep"] and rep["samples"] == 815 * 1110 * 4 == 3618600
    assert rep["alpha"]["opaque"] is True and rep["alpha"]["bytes"] == 904650
    assert dt < 6000, f"{dt:.0f} ms pour relire une carte"


# ═══════════════════════════════════════════════════════════════════════════
#  TOUR 5 — LA REVUE LIGNE À LIGNE DE MON PROPRE AFFICHAGE
#
#  Consigne : « pour chaque chiffre affiché, écris la mesure qui le prouve ».
#  La revue a trouvé UN chiffre faux, et il était le plus lourd de l'écran :
#  « champs inventés » valait `slots_au_gabarit × cartes`. Un produit suppose
#  que chaque slot fabrique sur CHAQUE carte — faux dès qu'une colonne posée a
#  des cellules vides. Mesure : 3 lignes (qty 3/2/5 → 10 cartes), une cellule
#  `texte` vide, 3 slots sans donnée → l'écran affichait 30, la vérité comptée
#  carte par carte est 22. Huit valeurs de trop, 36 % d'exagération sur le
#  seul compteur qui décide d'un bon à tirer — et il exagérait dans le sens
#  qui fait peur, ce qui n'est pas une excuse : un compteur d'alerte gonflé
#  finit ignoré, exactement comme celui qu'on avait dégonflé au tour 2.
# ═══════════════════════════════════════════════════════════════════════════

SLOTS_TROUS = [
    {"id": "title", "label": "Titre", "text": "Poulpe des abysses", "on": True},
    {"id": "rules", "label": "Règles", "text": "Texte de démonstration", "on": True},
    {"id": "cost", "label": "Coût", "text": "5", "on": True},
    {"id": "num", "label": "Numéro", "text": "017 / 060", "on": True},
]
CSV_TROUS = ("nom;atk;texte;qty\r\n"
             "Colosse;7;Mêlée;3\r\n"
             "Oracle;2;;2\r\n"          # cellule vide : le trou
             "Rebut;9;Écrase;5\r\n")


def _fab_vrai(out, slots) -> int:
    """La vérité, comptée sur les cartes construites et pas sur un audit :
    combien d'emplacements le gabarit remplirait, carte par carte."""
    talk = [s["id"] for s in slots if s.get("on", True) and s["text"].strip()]
    return sum(
        sum(1 for sid in talk
            if str(c["fields"].get(sid, "")).replace(D.BLANK, "").strip() == "")
        for c in out["cards"])


def test_t5_les_champs_inventes_sont_COMPTES_et_plus_multiplies():
    """LE CHIFFRE FAUX DE CE TOUR, pris sur le seul compteur qui arrête une
    production. 30 affichés, 22 vrais.

    La correction n'est pas un facteur correctif : le moteur compte les
    emplacements carte par carte, avant de neutraliser quoi que ce soit, et
    rend les deux parts de l'addition — la seule qui a le droit de se
    multiplier (un slot que RIEN n'alimente parle sur chaque carte) et celle
    qui ne l'a pas (une cellule vide ne parle que sur ses cartes).
    """
    t = _parse(CSV_TROUS)
    mp = {"nom": "title", "texte": "rules"}
    out = _build(t, mapping=mp, qty_col="qty", slots=SLOTS_TROUS,
                 blank_unfed=False)
    a = out["stats"]["audit"]
    assert out["stats"]["n_cards"] == 10
    # l'ancien affichage, refait ici pour que l'écart soit dans le test
    assert a["n_from_template"] * out["stats"]["n_cards"] == 30
    # la vérité, comptée sur les cartes
    assert _fab_vrai(out, SLOTS_TROUS) == 22
    assert a["n_fabricated"] == 22, "le moteur compte, il ne multiplie plus"
    # et l'addition que l'écran recopie tombe juste
    assert a["n_fab_unfed"] == 2 * 10, "2 slots sans colonne × 10 cartes"
    assert a["n_fab_holes"] == 2, "la cellule vide, sur ses 2 cartes seulement"
    assert a["n_fab_unfed"] + a["n_fab_holes"] == a["n_fabricated"]
    # par carte, pour que la mesure sur UN fichier ait le bon dénominateur
    assert a["fab_per_card"] == [2, 2, 2, 3, 3, 2, 2, 2, 2, 2]
    assert sum(a["fab_per_card"]) == a["n_fabricated"]


def test_t5_les_deux_comptes_de_slots_se_reconcilient_par_ecrit():
    """LE DEUXIÈME CHIFFRE PRIS EN DÉFAUT PAR LA REVUE, ET IL ÉTAIT À L'ÉCRAN,
    À DEUX CENTIMÈTRES DE SON JUMEAU.

    Capture du lab : le compteur du haut affiche « 6 SLOTS AU GABARIT » et le
    grand livre juste dessous « 5 au gabarit ». Les deux sont vrais et ne
    répondent pas à la même question — le grand livre classe les slots par
    ORIGINE, le compteur compte les prises de parole du gabarit, et un slot
    bien mappé parle quand même sur les cartes dont la cellule est vide. Rien
    ne l'écrivait : c'est mot pour mot le reproche des dénominateurs qui se
    contredisent à l'œil, commis par ma propre correction du tour 2.

    Le terme qui les réconcilie est désormais rendu par le moteur et écrit dans
    les deux infobulles.
    """
    t = _parse(CSV_TROUS)
    a = _build(t, mapping={"nom": "title", "texte": "rules"}, qty_col="qty",
               slots=SLOTS_TROUS, blank_unfed=False)["stats"]["audit"]
    assert a["n_slots_unfed_template"] == 2          # cost, num
    assert a["n_slots_template_hole_only"] == 1      # rules : mappé mais vide
    assert a["slots_template_hole_only"] == ["rules"]
    assert (a["n_slots_unfed_template"] + a["n_slots_template_hole_only"]
            == a["n_from_template"]), "les deux comptes ne se recollent pas"
    js = _js_data()
    assert "n_slots_template_hole_only" in js
    assert "sans colonne, au gabarit" in js, "l'étiquette ne dit pas laquelle"
    # la phrase est coupée par le formatage du source : on cherche ses deux moitiés
    assert "il classe les colonnes, pas les " in js and "prises de parole" in js
    assert "slots_template_hole_only" in _fn(js, "paintAudit")


def test_t5_le_mode_laisser_vide_annonce_le_meme_compte_exact():
    """Le mode par défaut ne change pas la vérité, il l'empêche : le nombre
    d'emplacements ÉVITÉS est le même 22, et le fichier n'en porte aucun."""
    t = _parse(CSV_TROUS)
    out = _build(t, mapping={"nom": "title", "texte": "rules"}, qty_col="qty",
                 slots=SLOTS_TROUS)
    a = out["stats"]["audit"]
    assert a["blank_mode"] is True
    assert a["n_fabricated"] == 0 and a["n_fabricated_avoided"] == 22
    assert _fab_vrai(out, SLOTS_TROUS) == 22
    # la carte 4 (première copie d'Oracle) en a UN de plus que les autres
    assert a["fab_per_card"][3] == 3 and a["fab_per_card"][0] == 2
    assert out["cards"][3]["fields"]["rules"] == D.BLANK


def test_t5_sans_trou_le_compte_et_le_produit_tombent_pareil():
    """La correction ne déplace pas le chiffre là où il était juste : quand
    aucune colonne posée n'a de cellule vide, compter et multiplier donnent le
    même nombre. Un correctif qui changerait AUSSI le cas sain serait suspect.
    """
    t = _parse("nom;atk;qty\r\nA;7;3\r\nB;2;2\r\n")
    out = _build(t, mapping={"nom": "title"}, qty_col="qty",
                 slots=SLOTS_TROUS, blank_unfed=False)
    a = out["stats"]["audit"]
    assert out["stats"]["n_cards"] == 5
    assert a["n_slots_unfed_template"] == 3          # rules, cost, num
    assert a["n_fabricated"] == 15 == 3 * 5
    assert a["n_fab_holes"] == 0
    assert _fab_vrai(out, SLOTS_TROUS) == 15


def test_t5_lecran_ne_multiplie_plus_et_ecrit_son_addition():
    """Le geste d'écran sans lequel la correction du moteur ne sert à rien :
    l'écran doit LIRE le compte et non le refabriquer."""
    import re as _re
    js = _js_data()
    aff = _re.sub(r"/\*(?:.|\n)*?\*/", "", js)      # commentaires exclus
    assert "nGab * (st.n_cards" not in aff, "le produit faux est encore là"
    assert "au.n_from_template + \" slot(s) × \"" not in aff
    assert "au.n_fabricated" in aff, "l'écran n'affiche pas le compte du moteur"
    # l'addition est écrite, avec ses deux parts, et vérifiée avant affichage
    f = _fn(js, "fabSum")
    assert "n_fab_unfed" in f and "n_fab_holes" in f
    assert "somme incohérente" in f, "l'écran ne se contrôle pas lui-même"
    assert "jamais un produit" in f
    # les deux endroits qui l'affichaient portent la même source
    assert "fabSum(au, st)" in aff
    assert aff.count("fabSum(au, st)") >= 2


def test_t5_la_mesure_sur_le_fichier_porte_le_compte_de_CETTE_carte():
    """« Le même tirage … diffère sur N pixels » : le pixel était mesuré sur UN
    fichier de carte et la phrase parlait des dix. Un chiffre juste avec une
    portée fausse est un chiffre faux — c'est le reproche mot pour mot du
    critique, appliqué à ma propre ligne."""
    import re as _re
    js = _js_data()
    pd = _re.sub(r"/\*(?:.|\n)*?\*/", "", _fn(js, "paintDeliv"))
    assert "Le même tirage" not in pd, "la portée est encore celle du tirage"
    assert "même carte" in pd
    assert "d.fabCard" in pd, "le compte de la carte mesurée n'est pas lu"
    assert "d.fabDeck" in pd, "et le total du tirage garde sa propre phrase"
    # les deux contradictions se jugent sur la carte, pas sur le deck
    assert "const fc = " in pd and "fc > 0" in pd and "fc === 0" in pd
    md = _fn(js, "measureDelivered")
    assert "au.fab_per_card" in md


def test_t5_une_colonne_posee_sur_un_slot_disparu_a_sa_propre_case():
    """La strate suivante du reproche des dénominateurs : P3 renomme un slot
    APRÈS le mappage. La colonne restait comptée « vers un slot » pendant
    qu'aucun slot ne se déclarait alimenté — deux additions justes qui se
    contredisent à l'œil. Elle a désormais sa case, et la somme tombe juste.
    """
    t = _parse(CSV_TROUS)
    a = _build(t, mapping={"nom": "title", "texte": "fantome"}, qty_col="qty",
               slots=SLOTS_TROUS, blank_unfed=False)["stats"]["audit"]
    assert a["n_cols_to_ghost"] == 1 and a["cols_to_ghost"] == ["texte"]
    assert a["n_cols_to_slots"] == 1 and a["cols_to_slots"] == ["nom"]
    assert (a["n_cols_to_slots"] + a["n_cols_to_ghost"]
            + a["n_cols_to_reserved"] + a["n_cols_qty"]
            + a["n_cols_idle"] == a["n_cols"]), a
    # et le slot fantôme n'alimente rien : c'est tout l'intérêt de la case
    assert a["n_slots_fed"] == 1
    # sans slot fantôme, la case reste vide et l'écran ne l'affiche pas
    b = _build(t, mapping={"nom": "title"}, qty_col="qty", slots=SLOTS_TROUS,
               blank_unfed=False)["stats"]["audit"]
    assert b["n_cols_to_ghost"] == 0
    js = _js_data()
    assert "au.n_cols_to_ghost" in js and "vers un slot disparu" in js


class _FauxDossier:
    """Un dossier d'images sensible à la casse — ce que Windows ne sait pas
    fabriquer et ce que le serveur de l'imprimeur fait tous les jours."""

    class _F:
        def __init__(self, name):
            self.name = name

        def is_file(self):
            return True

    def __init__(self, noms):
        self._n = list(noms)

    def iterdir(self):
        return [self._F(n) for n in self._n]

    def __str__(self):
        return "<faux dossier>"


def test_t5_le_denominateur_de_la_bibliotheque_compte_des_FICHIERS():
    """« bibliothèque d'images (116 fichiers) » comptait des clés REPLIÉES.
    Sur un disque sensible à la casse, `Octo.png` et `octo.png` n'en faisaient
    qu'une : le bandeau annonçait 3 fichiers pour 4. Un dénominateur qui
    rétrécit avec le système de fichiers n'est pas un dénominateur.
    """
    d = _FauxDossier(["Octo.png", "octo.png", "brume.png", "totem.jpg"])
    r = D.resolve_art(["octo.png", "brume.png"], d)
    assert r["n_files"] == 4, "les 4 fichiers doivent être comptés"
    assert r["n_names"] == 3, "et l'écart avec les noms atteignables est dit"
    assert r["n_ok"] == 2 and r["n"] == 2
    # sur un dossier sans collision, les deux chiffres coïncident
    r2 = D.resolve_art([], _FauxDossier(["a.png", "b.png"]))
    assert r2["n_files"] == r2["n_names"] == 2
    js = _js_data()
    assert "ART.n_names" in js, "l'écart n'est pas dit à l'écran"


def test_t5_aucun_compte_recopie_a_cote_de_la_liste_quil_compte():
    """Le badge recopié qui finit par mentir, dernière occurrence trouvée : la
    route /samples annonçait « Trois jeux d'essai » — cette phrase est servie
    telle quelle dans le schéma OpenAPI — et en servait six."""
    doc = D.get_samples.__doc__ or ""
    assert "Trois" not in doc and "trois" not in doc
    assert len(D.samples()) == 6
    # et l'écran ne recopie aucun de ces comptes : il les dénombre
    js = _js_data()
    assert "SAMPLES.length" in js
    assert '"3 séparateur' not in js and '"6 jeux' not in js


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
