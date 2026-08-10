# -*- coding: utf-8 -*-
"""Recette de la piste de sous-titres s1 — backend/app/services/subtitle_service.py

Tests purs : aucun reseau, aucune app FastAPI, aucun `settings`. Seule
dependance externe : PIL (deja dans le runtime embarque) pour la mesure de
largeur de ligne.

Ce qui est verifie :
  * validite des TROIS formats ecrits (SRT, VTT, ASS) — structure, en-tetes,
    horodatages, comptes ;
  * aller-retour ecriture -> lecture en SRT et en VTT, temps conserves ;
  * decoupe automatique qui ne casse jamais un mot et prefere la ponctuation ;
  * karaoke : la somme des `\\k` egale EXACTEMENT la duree du segment ;
  * avertissements declenches sur des cas construits (trop court, trop long,
    debit, chevauchement, ligne trop large) ;
  * les fontes des prereglages existent reellement sur cette machine.

Lancement (UN PROCESSUS POUR CE FICHIER) :
    runtime\\python\\python.exe -m pytest backend/tests/test_subtitle_service.py -q
"""
import re

import pytest

from app.services.subtitle_service import (
    STYLES, ass_fontsdir, ass_unsupported, auto_break, auto_break_lines,
    autofix, check_fonts, check_quality, distribute_words, font_line_height,
    font_path,
    fonts_dir, karaoke_spans, normalize_segments, parse_srt, parse_subtitles,
    parse_vtt, resolve_style, segment_cs, sniff_format, split_segment,
    split_segments, style_labels, subtitles_filter, to_ass, to_srt, to_vtt)

# --- pistes de reference -----------------------------------------------------

TRACK = [
    {"id": "s1_0001", "start": 0.0, "end": 2.4, "text": "Bonjour le monde",
     "words": [{"w": "Bonjour", "start": 0.0, "end": 0.9},
               {"w": "le", "start": 0.9, "end": 1.1},
               {"w": "monde", "start": 1.1, "end": 2.4}]},
    {"id": "s1_0002", "start": 2.6, "end": 5.25,
     "text": "Deuxieme replique,\navec deux lignes"},
    {"id": "s1_0003", "start": 5.5, "end": 8.125,
     "text": "Et une troisieme pour la route", "style": "pop"},
]

PHRASE = ("Le poulpe prophete emerge des profondeurs, il regarde la camera, "
          "puis il annonce la prochaine bougie verte. Personne ne bouge.")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Fontes : une police absente fait silencieusement retomber ffmpeg ailleurs
# ─────────────────────────────────────────────────────────────────────────────

def test_toutes_les_fontes_du_catalogue_existent():
    st = check_fonts()
    assert st["missing"] == [], f"fontes absentes du paquet : {st['missing']}"
    assert fonts_dir().is_dir()


def test_chaque_preset_pointe_une_fonte_reellement_presente():
    for key, preset in STYLES.items():
        p = font_path(preset["font"])
        assert p is not None and p.exists(), \
            f"preset {key!r} : fonte {preset['font']!r} introuvable"


def test_au_moins_six_presets_nommes_en_francais():
    labels = {s["id"]: s["label"] for s in style_labels()}
    assert len(labels) >= 6
    assert all(v for v in labels.values())
    # l'equivalent des six de la barre
    for k in ("standard", "pop", "surligneur", "beurre", "contour_sombre",
              "prime"):
        assert k in labels


def test_fonte_inconnue_bascule_explicitement_sans_mentir():
    st = resolve_style({"font": "Montserrat"})     # absente de cette machine
    assert st["font_fallback"] == "Montserrat"
    assert font_path(st["font"]) is not None


# ─────────────────────────────────────────────────────────────────────────────
# 2. SRT : validite + aller-retour
# ─────────────────────────────────────────────────────────────────────────────

SRT_CUE = re.compile(
    r"^(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> "
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\n(.+)$", re.S)


def test_srt_structure_valide():
    out = to_srt(TRACK)
    blocks = [b for b in out.split("\n\n") if b.strip()]
    assert len(blocks) == 3
    for i, b in enumerate(blocks, 1):
        m = SRT_CUE.match(b.strip() + "\n")
        assert m, f"bloc SRT invalide :\n{b}"
        assert int(m.group(1)) == i           # numerotation 1..N, dans l'ordre
    assert "-->" in out and "," in out.split("-->")[0]


def test_srt_aller_retour_conserve_les_temps():
    back = parse_srt(to_srt(TRACK))
    assert len(back) == len(TRACK)
    for a, b in zip(TRACK, back):
        assert abs(a["start"] - b["start"]) < 1e-9
        assert abs(a["end"] - b["end"]) < 1e-9
        assert b["text"] == a["text"]


def test_srt_lecture_tolerante_bom_crlf_point_et_sans_numerotation():
    src = ("\ufeff00:00:00.000 --> 00:00:02.400\r\n"
           "Bonjour le monde\r\n"
           "\r\n"
           "00:00:02.600 --> 00:00:05.250\r\n"
           "Deuxieme replique,\r\n"
           "avec deux lignes\r\n")
    segs = parse_srt(src)
    assert len(segs) == 2
    assert segs[0]["text"] == "Bonjour le monde"
    assert segs[1]["text"] == "Deuxieme replique,\navec deux lignes"
    assert abs(segs[1]["end"] - 5.25) < 1e-9


def test_srt_lecture_heures_omises_et_balises():
    segs = parse_srt("1\n00:01.500 --> 00:03.000\n<i>En italique</i>\n")
    assert len(segs) == 1
    assert segs[0]["start"] == 1.5 and segs[0]["end"] == 3.0
    assert segs[0]["text"] == "En italique"


def test_srt_lecture_sans_ligne_blanche():
    src = ("1\n00:00:00,000 --> 00:00:01,000\nUn\n"
           "2\n00:00:01,000 --> 00:00:02,000\nDeux\n")
    segs = parse_srt(src)
    assert [s["text"] for s in segs] == ["Un", "Deux"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. VTT : validite + aller-retour (temps de segment ET de mot)
# ─────────────────────────────────────────────────────────────────────────────

def test_vtt_structure_valide():
    out = to_vtt(TRACK)
    assert out.startswith("WEBVTT")
    cues = re.findall(r"(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})",
                      out)
    assert len(cues) == 3
    assert "," not in out.split("-->")[0].split("WEBVTT")[1]   # point decimal
    assert sniff_format(out) == "vtt"


def test_vtt_aller_retour_conserve_les_temps():
    back = parse_vtt(to_vtt(TRACK))
    assert len(back) == len(TRACK)
    for a, b in zip(TRACK, back):
        assert abs(a["start"] - b["start"]) < 1e-9
        assert abs(a["end"] - b["end"]) < 1e-9
        assert b["text"] == a["text"]


def test_vtt_porte_le_calage_par_mot_et_le_relit():
    out = to_vtt(TRACK[:1], word_timings=True)
    assert "<00:00:00.900>" in out                   # fin du 1er mot
    back = parse_vtt(out)
    ws = back[0]["words"]
    assert [w["w"] for w in ws] == ["Bonjour", "le", "monde"]
    for a, b in zip(TRACK[0]["words"], ws):
        assert abs(a["start"] - b["start"]) < 1e-3
        assert abs(a["end"] - b["end"]) < 1e-3


def test_vtt_lecture_tolerante_identifiants_reglages_et_notes():
    src = ("\ufeffWEBVTT - piste s1\r\n"
           "\r\n"
           "NOTE ceci est un commentaire\r\n"
           "qui tient sur deux lignes\r\n"
           "\r\n"
           "intro\r\n"
           "00:00.000 --> 00:02.400 line:90% align:center\r\n"
           "<c.jaune>Bonjour</c> le monde\r\n"
           "\r\n"
           "00:02.600 --> 00:05.250\r\n"
           "Deuxieme replique\r\n")
    segs = parse_vtt(src)
    assert len(segs) == 2
    assert segs[0]["text"] == "Bonjour le monde"
    assert abs(segs[0]["end"] - 2.4) < 1e-9
    assert segs[1]["text"] == "Deuxieme replique"


def test_detection_de_format():
    assert sniff_format(to_srt(TRACK)) == "srt"
    assert sniff_format(to_vtt(TRACK)) == "vtt"
    assert sniff_format(to_ass(TRACK)) == "ass"
    assert len(parse_subtitles(to_vtt(TRACK))) == 3
    assert len(parse_subtitles(to_srt(TRACK))) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 4. ASS : validite structurelle, style reel, mise a l'echelle du canevas
# ─────────────────────────────────────────────────────────────────────────────

def _ass_sections(text):
    out, cur = {}, None
    for ln in text.split("\n"):
        if ln.startswith("[") and ln.endswith("]"):
            cur = ln
            out[cur] = []
        elif cur:
            out[cur].append(ln)
    return out


def test_ass_structure_valide():
    out = to_ass(TRACK, "standard", canvas=(1080, 1920))
    sec = _ass_sections(out)
    assert set(sec) == {"[Script Info]", "[V4+ Styles]", "[Events]"}
    assert "ScriptType: v4.00+" in sec["[Script Info]"]
    assert "PlayResX: 1080" in sec["[Script Info]"]
    assert "PlayResY: 1920" in sec["[Script Info]"]

    fmt = [l for l in sec["[V4+ Styles]"] if l.startswith("Format:")]
    styles = [l for l in sec["[V4+ Styles]"] if l.startswith("Style:")]
    assert len(fmt) == 1 and styles
    n_fields = len(fmt[0].split("Format:", 1)[1].split(","))
    for s in styles:
        assert len(s.split("Style:", 1)[1].split(",")) == n_fields

    efmt = [l for l in sec["[Events]"] if l.startswith("Format:")]
    events = [l for l in sec["[Events]"] if l.startswith("Dialogue:")]
    assert len(efmt) == 1
    assert len(events) == 3
    # Dialogue: 9 champs + le texte, qui peut lui-meme contenir des virgules
    for e in events:
        assert len(e.split("Dialogue:", 1)[1].split(",", 9)) == 10


def test_ass_horodatage_au_centieme():
    out = to_ass([{"start": 5.5, "end": 8.125, "text": "x"}])
    line = [l for l in out.split("\n") if l.startswith("Dialogue:")][0]
    parts = line.split(",")
    assert parts[1] == "0:00:05.50"
    assert parts[2] == "0:00:08.13"          # 8.125 -> 8.13 (arrondi centieme)
    assert re.match(r"^\d:\d{2}:\d{2}\.\d{2}$", parts[1])


def test_ass_porte_le_style_reel():
    out = to_ass(TRACK[:1], "pop", canvas=(1080, 1080))
    st = [l for l in out.split("\n") if l.startswith("Style:")][0]
    f = st.split("Style:", 1)[1].split(",")
    assert f[1] == "Anton"                        # Fontname = famille reelle
    # Le corps ECRIT n'est pas l'em voulu : libass dessine
    # em = Fontsize / hauteur_de_ligne(fonte) (convention VSFilter, mesuree a
    # l'image). `to_ass` pre-multiplie pour que le px regle sorte grave.
    assert float(f[2]) == pytest.approx(
        92 * 1080 / 1080 * font_line_height("Anton"), rel=1e-4)
    assert f[3].startswith("&H") and len(f[3]) == 10   # &HAABBGGRR
    assert float(f[16]) > 0                       # Outline (contour)
    assert f[18] == "2"                           # Alignment 2 = bas-centre


def test_ass_met_le_style_a_l_echelle_du_canevas():
    a = to_ass(TRACK[:1], "standard", canvas=(1080, 1080))
    b = to_ass(TRACK[:1], "standard", canvas=(1920, 1080))
    c = to_ass(TRACK[:1], "standard", canvas=(1080, 2160))
    fs = lambda t: float(                                        # noqa: E731
        [l for l in t.split("\n") if l.startswith("Style:")][0]
        .split(",")[2])
    assert fs(a) == fs(b)                       # l'echelle suit la HAUTEUR
    # rel= et non abs= : le corps ecrit passe par `%g` (6 chiffres
    # significatifs), et le facteur de fonte lui donne des decimales.
    assert fs(c) == pytest.approx(2 * fs(a), rel=1e-5)


def test_le_corps_ecrit_compense_la_hauteur_de_ligne_de_la_fonte():
    """libass dessine `em = Fontsize / (usWinAscent+usWinDescent)/upm`.

    Sans compensation, un « 110 px » regle au panneau sortait grave a 77 px en
    Inter et a 63 px en Anton — l'ecart apercu/rendu le plus visible de la
    piste. Le facteur est MESURE a l'image (scratchpad/fontprobe3.py) et lu
    dans la table OS/2 : les deux concordent a 0,5 % pres sur huit familles.
    """
    for fam, attendu in (("Anton", 1.7334), ("Inter", 1.4302),
                         ("Bebas Neue", 1.3000), ("Bungee", 2.5740)):
        assert font_line_height(fam) == pytest.approx(attendu, abs=5e-3)
    # famille inconnue : on retombe sur Inter, jamais d'exception en plein rendu
    assert font_line_height("PoliceQuiNExistePas") > 0.5

    out = to_ass(TRACK[:1], {"font": "Anton", "size": 100.0}, canvas=(1080, 1080))
    f = [l for l in out.split("\n") if l.startswith("Style:")][0].split(",")
    assert float(f[2]) == pytest.approx(100.0 * font_line_height("Anton"), rel=1e-4)
    # contour, ombre et interlettrage restent en pixels de script : ils ne
    # passent PAS par le facteur de fonte.
    out2 = to_ass(TRACK[:1], {"font": "Anton", "size": 100.0, "outline": 4.0,
                              "shadow": 3.0, "spacing": 2.0}, canvas=(1080, 1080))
    g = [l for l in out2.split("\n") if l.startswith("Style:")][0].split(",")
    assert float(g[16]) == pytest.approx(4.0)
    assert float(g[17]) == pytest.approx(3.0)
    assert float(g[13]) == pytest.approx(2.0)


def test_ass_fond_opaque_utilise_borderstyle_3():
    out = to_ass(TRACK[:1], "sobre")
    f = [l for l in out.split("\n") if l.startswith("Style:")][0].split(",")
    assert f[15] == "3"                          # BorderStyle 3 = boite opaque
    assert float(f[16]) > 0                      # rembourrage de la boite


def test_ass_couleur_du_fond_va_dans_outlinecolour_pas_backcolour():
    """En BorderStyle 3, libass remplit la boite avec OutlineColour. Poser le
    fond dans BackColour donne une boite NOIRE sans aucune erreur ffmpeg."""
    out = to_ass(TRACK[:1], "surligneur")        # fond vert #00e676 opaque
    f = [l for l in out.split("\n") if l.startswith("Style:")][0].split(",")
    assert f[15] == "3"
    assert f[5] == "&H0076E600"                  # OutlineColour = &H00 BB GG RR
    assert f[6] == "&HFF000000"                  # BackColour = ombre, ici nulle
    # un style sans fond garde bien sa couleur de contour a sa place
    g = [l for l in to_ass(TRACK[:1], "contour_sombre").split("\n")
         if l.startswith("Style:")][0].split(",")
    assert g[15] == "1" and g[5] == "&H000A0A0A"


def test_ass_opacite_du_fond_arrive_dans_l_alpha():
    f = [l for l in to_ass(TRACK[:1], "prime").split("\n")
         if l.startswith("Style:")][0].split(",")
    alpha = int(f[5][2:4], 16)                   # &HAA... : AA = TRANSPARENCE
    assert alpha == round((1 - 0.62) * 255)


def test_ass_style_par_segment_produit_sa_propre_ligne():
    out = to_ass(TRACK, "standard")              # TRACK[2] demande "pop"
    styles = [l for l in out.split("\n") if l.startswith("Style:")]
    assert len(styles) == 2
    names = {l.split("Style:", 1)[1].split(",")[0].strip() for l in styles}
    used = {l.split("Dialogue:", 1)[1].split(",")[3].strip()
            for l in out.split("\n") if l.startswith("Dialogue:")}
    assert used <= names and len(used) == 2


def test_ass_echappe_les_accolades_et_les_sauts_de_ligne():
    out = to_ass([{"start": 0, "end": 2, "text": "a {b} c\nsuite"}],
                 karaoke=False)
    d = [l for l in out.split("\n") if l.startswith("Dialogue:")][0]
    txt = d.split(",", 9)[9]
    assert "\\{b\\}" in txt
    assert "\\N" in txt and "\n" not in txt


def test_ass_declare_ce_qu_il_ne_sait_pas_porter():
    assert ass_unsupported("standard") == {}
    assert "line_height" in ass_unsupported({"line_height": 1.4})
    # fond translucide + karaoke : libass empile une boite par mot, les
    # recouvrements font une couture sombre a chaque frontiere (constate au
    # rendu). Opaque, la couture disparait.
    assert "back_opacity" in ass_unsupported("prime", karaoke=True)
    assert "back_opacity" not in ass_unsupported("prime", karaoke=False)
    assert "back_opacity" not in ass_unsupported("surligneur", karaoke=True)


def test_avertissement_fond_translucide_en_karaoke():
    piste = [{"start": 0.0, "end": 2.5, "text": "Une ligne courte et lisible"}]
    w = check_quality(piste, "prime", karaoke=True)
    f = [x for x in w if x["code"] == "fond_translucide_karaoke"]
    assert len(f) == 1, "l'avertissement de style s'emet UNE fois, pas par segment"
    assert f[0]["index"] is None
    assert f[0]["fix"] == {"champ": "back_opacity", "valeur": 1.0}
    assert check_quality(piste, "prime", karaoke=False) == []
    assert check_quality(piste, "surligneur", karaoke=True) == []


def test_avertissement_de_style_ne_se_repete_pas_par_segment():
    piste = [{"start": i * 3.0, "end": i * 3.0 + 2.5, "text": "Ligne lisible"}
             for i in range(20)]
    w = check_quality(piste, "sobre", karaoke=True)
    assert len([x for x in w if x["code"] == "fond_translucide_karaoke"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 5. Karaoke : la somme des \k doit egaler la duree du segment
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("start,end", [
    (0.0, 2.4), (2.6, 5.25), (5.5, 8.125), (0.0, 1.0), (12.337, 15.972),
    (1.0, 1.03),                                    # plus court qu'un mot
])
def test_karaoke_somme_egale_la_duree(start, end):
    seg = {"start": start, "end": end, "text": PHRASE}
    spans = karaoke_spans(seg)
    assert sum(k for k, _ in spans) == segment_cs(seg)
    assert [w for _, w in spans] == PHRASE.split()
    assert all(k >= 0 for k, _ in spans)


def test_karaoke_somme_egale_la_duree_avec_calage_fourni():
    for seg in TRACK:
        assert sum(k for k, _ in karaoke_spans(seg)) == segment_cs(seg)


def test_segment_cs_est_bien_la_duree_ecrite_dans_le_fichier():
    """La duree de reference du karaoke doit etre celle que l'ASS AFFICHE,
    pas celle du modele : les deux horodatages sont arrondis separement."""
    def _cs_of(s):
        h, m, rest = s.split(":")
        sec, cent = rest.split(".")
        return ((int(h) * 60 + int(m)) * 60 + int(sec)) * 100 + int(cent)

    segs = [{"start": 0.0, "end": 2.4, "text": "un deux trois"},
            {"start": 5.5, "end": 8.125, "text": "quatre cinq"},
            {"start": 12.337, "end": 15.972, "text": PHRASE}]
    out = to_ass(segs, "standard")
    lines = [l for l in out.split("\n") if l.startswith("Dialogue:")]
    for line, seg in zip(lines, segs):
        p = line.split(",")
        assert _cs_of(p[2]) - _cs_of(p[1]) == segment_cs(seg)
        txt = line.split(",", 9)[9]
        assert sum(int(x) for x in re.findall(r"\{\\k(\d+)\}", txt)) \
            == segment_cs(seg)


def test_karaoke_absorbe_les_silences_inter_mots():
    seg = {"start": 0.0, "end": 4.0, "text": "un deux",
           "words": [{"w": "un", "start": 0.0, "end": 1.0},
                     {"w": "deux", "start": 3.0, "end": 4.0}]}
    spans = karaoke_spans(seg)
    assert sum(k for k, _ in spans) == 400
    assert spans == [(100, "un"), (300, "deux")]     # le blanc va au mot suivant


def test_ass_karaoke_balises_k_et_somme_dans_le_fichier():
    out = to_ass(TRACK, "standard", karaoke=True)
    for line, seg in zip(
            [l for l in out.split("\n") if l.startswith("Dialogue:")], TRACK):
        txt = line.split(",", 9)[9]
        ks = [int(x) for x in re.findall(r"\{\\k(\d+)\}", txt)]
        assert ks, "aucune balise de karaoke"
        assert sum(ks) == segment_cs(seg)


def test_ass_karaoke_off_ne_pose_aucune_balise_k():
    out = to_ass(TRACK, "standard", karaoke=False)
    assert not re.search(r"\{\\k", out)


def test_karaoke_inverse_les_couleurs_primaire_secondaire():
    on = to_ass(TRACK[:1], "pop", karaoke=True)
    off = to_ass(TRACK[:1], "pop", karaoke=False)
    fon = [l for l in on.split("\n") if l.startswith("Style:")][0].split(",")
    fof = [l for l in off.split("\n") if l.startswith("Style:")][0].split(",")
    # sans karaoke, le texte sort dans la couleur de base ; avec, la couleur
    # "chantee" (PrimaryColour) est celle du surlignage.
    assert fon[3] == fof[4] and fon[4] == fof[3]
    assert fof[3] == "&H0000E6FF"                # #ffe600 -> &H00 BB GG RR


def test_karaoke_survit_aux_sauts_de_ligne():
    seg = {"start": 0.0, "end": 3.0, "text": "premiere ligne\nseconde ligne"}
    out = to_ass([seg], "standard")
    txt = [l for l in out.split("\n") if l.startswith("Dialogue:")][0].split(",", 9)[9]
    assert txt.count("\\N") == 1
    assert sum(int(x) for x in re.findall(r"\{\\k(\d+)\}", txt)) == segment_cs(seg)


def test_distribute_words_couvre_exactement_l_intervalle():
    ws = distribute_words(PHRASE, 3.0, 9.5)
    assert ws[0]["start"] == 3.0 and ws[-1]["end"] == 9.5
    assert all(a["end"] <= b["start"] + 1e-9 for a, b in zip(ws, ws[1:]))
    assert [w["w"] for w in ws] == PHRASE.split()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Decoupe automatique : jamais au milieu d'un mot
# ─────────────────────────────────────────────────────────────────────────────

LONGS = [
    PHRASE,
    "Anticonstitutionnellement, dit-il, en regardant l'horizon.",
    "a b c d e f g h i j k l m n o p q r s t u v w x y z",
    "Supercalifragilisticexpialidocious",
    "Un mot. Deux mots ! Trois mots ? Quatre mots ; cinq mots : six mots.",
]


@pytest.mark.parametrize("text", LONGS)
@pytest.mark.parametrize("cpl", [12, 16, 24, 32, 42, 60])
def test_decoupe_ne_casse_jamais_un_mot(text, cpl):
    lines = auto_break_lines(text, cpl)
    assert " ".join(lines).split() == text.split(), \
        "des mots ont ete perdus, dupliques ou coupes"
    for ln in lines:
        for w in ln.split():
            assert w in text.split()
        # une ligne ne depasse que si elle contient UN mot plus long que la
        # limite — un mot n'est jamais tronconne pour tenir.
        if len(ln) > cpl:
            assert len(ln.split()) == 1 and len(ln.split()[0]) > cpl


@pytest.mark.parametrize("text", LONGS)
def test_decoupe_en_blocs_respecte_le_nombre_de_lignes(text):
    for cpl in (16, 32, 42):
        for ml in (1, 2, 3):
            blocks = auto_break(text, cpl, ml)
            assert all(len(b) <= ml for b in blocks)
            flat = " ".join(ln for b in blocks for ln in b)
            assert flat.split() == text.split()


def test_decoupe_prefere_la_ponctuation():
    t = "Il arrive enfin, puis il repart aussitot vers le large"
    lines = auto_break_lines(t, 32)
    assert lines[0].endswith(","), lines


def test_decoupe_texte_vide():
    assert auto_break_lines("   ", 20) == []
    assert auto_break("", 20, 2) == []


def test_split_segment_cale_sur_les_mots():
    seg = {"start": 0.0, "end": 8.0, "text": PHRASE}
    parts = split_segment(seg, 30, 2)
    assert len(parts) > 1
    assert parts[0]["start"] == 0.0
    assert parts[-1]["end"] == 8.0
    for a, b in zip(parts, parts[1:]):
        assert b["start"] >= a["end"] - 1e-6
    assert " ".join(p["text"].replace("\n", " ") for p in parts).split() \
        == PHRASE.split()
    for p in parts:                       # le karaoke reste exact apres coupe
        assert sum(k for k, _ in karaoke_spans(p)) == segment_cs(p)


def test_split_segments_sur_toute_la_piste():
    out = split_segments(TRACK, 16, 1)
    assert len(out) > len(TRACK)
    assert all(s["id"] for s in out)
    assert len({s["id"] for s in out}) == len(out)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Controle qualite : avertissements sur des cas construits
# ─────────────────────────────────────────────────────────────────────────────

def _codes(warns):
    return {w["code"] for w in warns}


def test_aucun_avertissement_sur_une_piste_saine():
    sain = [{"start": 0.0, "end": 2.5, "text": "Une ligne courte et lisible"},
            {"start": 3.0, "end": 5.5, "text": "Une autre ligne tres lisible"}]
    assert check_quality(sain, "standard") == []


def test_avertissement_segment_trop_court():
    w = check_quality([{"start": 0.0, "end": 0.4, "text": "Trop bref"}])
    assert "trop_court" in _codes(w)
    f = [x for x in w if x["code"] == "trop_court"][0]
    assert f["value"] == pytest.approx(0.4)
    assert f["limit"] == 1.0
    # le correctif est un PLAN negocie : seul, le segment peut s'etirer
    assert f["plan"]["ok"] and f["plan"]["action"] == "etirer"
    assert f["plan"]["granted"] == pytest.approx(1.0)
    assert f["plan"]["label"] == "Étirer à 1 s"


def test_avertissement_segment_trop_long():
    w = check_quality([{"start": 0.0, "end": 9.0, "text": "Un texte pose la"}])
    assert "trop_long" in _codes(w)


def test_avertissement_debit_de_lecture():
    court = "a" * 60 + " fin"                # 64 caracteres en 2 s -> 32 c/s
    w = check_quality([{"start": 0.0, "end": 2.0, "text": court}])
    assert "debit_illisible" in _codes(w)
    d = [x for x in w if x["code"] == "debit_illisible"][0]
    assert d["value"] == pytest.approx(32.0, abs=0.5)
    assert d["severity"] == "erreur"

    moyen = "b" * 44                        # 44 caracteres en 2 s -> 22 c/s
    w2 = check_quality([{"start": 0.0, "end": 2.0, "text": moyen}])
    assert "debit_eleve" in _codes(w2)


def test_avertissement_chevauchement():
    w = check_quality([{"start": 0.0, "end": 3.0, "text": "Premier segment"},
                       {"start": 2.0, "end": 5.0, "text": "Second segment"}])
    ch = [x for x in w if x["code"] == "chevauchement"]
    assert ch and ch[0]["value"] == pytest.approx(1.0)
    # ancrage : sur le SECOND (celui qui commence trop tot), et le message
    # nomme le premier par son rang affiche
    assert ch[0]["index"] == 1 and ch[0]["about"] == [0, 1]
    assert "n°1" in ch[0]["message"]
    assert ch[0]["plan"]["ok"] and ch[0]["plan"]["action"] == "separer"


def test_avertissement_intervalle_court():
    w = check_quality([{"start": 0.0, "end": 3.0, "text": "Premier segment"},
                       {"start": 3.01, "end": 6.0, "text": "Second segment"}])
    assert "intervalle_court" in _codes(w)


def test_avertissement_ligne_trop_large_en_pixels():
    # 60 caracteres en Anton 92 px ne tiennent pas dans un 1080 de large.
    long_ = "Un titre beaucoup beaucoup trop long pour tenir sur la largeur"
    w = check_quality([{"start": 0.0, "end": 6.0, "text": long_}],
                      "pop", canvas=(1080, 1080))
    lt = [x for x in w if x["code"] == "ligne_trop_large"]
    assert lt, _codes(w)
    assert lt[0]["value"] > lt[0]["limit"]          # mesure en PIXELS
    assert lt[0]["plan"]["ok"]
    assert lt[0]["plan"]["action"] in ("replier", "decouper")
    # ... et la meme phrase passe dans un style sobre
    w2 = check_quality([{"start": 0.0, "end": 6.0, "text": long_}],
                       "sobre", canvas=(1920, 1080))
    assert "ligne_trop_large" not in _codes(w2)


def test_avertissement_trop_de_lignes():
    w = check_quality([{"start": 0.0, "end": 4.0, "text": "un\ndeux\ntrois"}])
    t = [x for x in w if x["code"] == "trop_de_lignes"][0]
    assert t["value"] == 3 and t["limit"] == 2
    assert t["plan"]["ok"] and t["plan"]["action"] in ("replier", "decouper")


def test_avertissement_mots_incoherents():
    seg = {"start": 1.0, "end": 3.0, "text": "un deux",
           "words": [{"w": "un", "start": 1.0, "end": 2.0},
                     {"w": "deux", "start": 2.0, "end": 3.0}]}
    assert "mots_incoherents" not in _codes(check_quality([seg]))
    # on force un calage hors bornes en court-circuitant la normalisation
    seg2 = dict(normalize_segments([seg])[0])
    seg2["words"] = [{"w": "un", "start": 1.0, "end": 2.0},
                     {"w": "deux", "start": 2.0, "end": 9.0}]
    w = [x for x in check_quality([seg2]) if x["code"] == "mots_incoherents"]
    assert w and w[0]["severity"] == "erreur"


def test_autofix_resorbe_chevauchements_et_segments_trop_courts():
    piste = [{"start": 0.0, "end": 3.0, "text": "Premier segment"},
             {"start": 2.0, "end": 2.3, "text": "Second segment"},
             {"start": 6.0, "end": 9.0, "text": "Troisieme segment"}]
    fixe = autofix(piste)
    codes = _codes(check_quality(fixe))
    assert "chevauchement" not in codes
    assert "trop_court" not in codes
    assert [s["text"] for s in fixe] == [s["text"] for s in piste]
    for s in fixe:                       # le karaoke reste exact apres retouche
        assert sum(k for k, _ in karaoke_spans(s)) == segment_cs(s)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Normalisation et garde-fous
# ─────────────────────────────────────────────────────────────────────────────

def test_normalisation_borne_trie_et_deduplique():
    segs = normalize_segments([
        {"start": 5.0, "end": 6.0, "text": " deuxieme ", "id": "x"},
        {"start": -2.0, "end": 1.0, "text": "premier", "id": "x"},
        {"start": 3.0, "end": 2.0, "text": "inverse"},
        {"start": 0.0, "end": 1.0, "text": "   "},          # ecarte
    ])
    assert [s["text"] for s in segs] == ["premier", "inverse", "deuxieme"]
    assert segs[0]["start"] == 0.0                          # negatif borne
    assert segs[1]["start"] == 2.0 and segs[1]["end"] == 3.0
    assert len({s["id"] for s in segs}) == 3


def test_valeurs_absurdes_ne_traversent_pas_le_style():
    st = resolve_style({"size": 1e9, "outline": -50, "back_opacity": 12,
                        "align": "diagonale", "valign": "nulle part",
                        "chars_per_line": 0})
    assert st["size"] <= 400 and st["outline"] == 0.0
    assert st["back_opacity"] == 1.0
    assert st["align"] == "center" and st["valign"] == "bottom"
    assert st["chars_per_line"] >= 8
    to_ass([{"start": 0, "end": 1, "text": "x"}], st)       # ne leve pas


def test_ecriture_sur_piste_vide():
    assert to_srt([]) == ""
    assert to_vtt([]).startswith("WEBVTT")
    assert "[Events]" in to_ass([])
    assert check_quality([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# 9. Filtre ffmpeg : l'echappement Windows est le piege classique
# ─────────────────────────────────────────────────────────────────────────────

def test_filtre_subtitles_echappe_le_chemin_windows():
    f = subtitles_filter(r"C:\Users\olivi\a b\piste.ass")
    assert "\\U" not in f and "\\a" not in f
    assert "C\\:/Users/olivi/a b/piste.ass" in f
    assert f.startswith("subtitles='")
    assert "fontsdir='" in f                 # fontes embarquees par defaut
    assert ass_fontsdir().replace("\\", "/").split("/")[-1] == "_fonts"


def test_filtre_subtitles_sans_fontsdir():
    f = subtitles_filter("/tmp/x.ass", fontsdir="")
    assert f == "subtitles='/tmp/x.ass'"


# ─────────────────────────────────────────────────────────────────────────────
# 10. Preuve au rendu : ffmpeg charge-t-il VRAIMENT la fonte embarquee ?
#     Un fichier ASS syntaxiquement parfait ne prouve rien : si libass ne
#     trouve pas la famille, il retombe sur une autre SANS erreur. On grave
#     donc trois images d'une mire lavfi (aucun asset externe) et on compare.
# ─────────────────────────────────────────────────────────────────────────────

def _ffmpeg_ok():
    import shutil
    return shutil.which("ffmpeg") is not None


@pytest.mark.skipif(not _ffmpeg_ok(), reason="ffmpeg absent du PATH")
def test_ffmpeg_grave_bien_la_fonte_embarquee(tmp_path):
    import hashlib
    import subprocess

    from PIL import Image

    track = [{"start": 0.0, "end": 3.0, "text": "POULPE PROPHETE"}]
    ass_ok = to_ass(track, "pop", canvas=(720, 1280))
    ass_ko = ass_ok.replace(",Anton,", ",FonteQuiNexistePas,")
    assert ",Anton," in ass_ok and ",FonteQuiNexistePas," in ass_ko

    def burn(body, name, fontsdir):
        p = tmp_path / f"{name}.ass"
        p.write_text(body, encoding="utf-8")
        png = tmp_path / f"{name}.png"
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", "color=c=black:s=720x1280:d=1",
             "-vf", subtitles_filter(p, fontsdir=fontsdir),
             "-frames:v", "1", str(png)],
            capture_output=True, text=True)
        assert r.returncode == 0, f"ffmpeg a refuse le filtre : {r.stderr}"
        assert png.exists()
        return hashlib.sha256(
            Image.open(png).convert("RGB").tobytes()).hexdigest()

    from app.services.subtitle_service import ass_fontsdir as _fd
    avec = burn(ass_ok, "avec", _fd())
    sans_fonte = burn(ass_ko, "sans_fonte", _fd())
    sans_dir = burn(ass_ok, "sans_dir", "")

    assert avec != sans_fonte, \
        "meme rendu avec Anton et avec une famille inexistante : libass ne " \
        "charge pas la fonte embarquee, tout part sur le meme fallback"
    assert avec != sans_dir, \
        "meme rendu avec et sans fontsdir : le chemin des fontes embarquees " \
        "n'est pas pris en compte"
