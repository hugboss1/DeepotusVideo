# -*- coding: utf-8 -*-
"""Recette de la piste de sous-titres s1 — transcribe_service.

Tests purs : aucun réseau, aucun appel payant, aucune app FastAPI. Le seul
sous-processus est ffmpeg/ffprobe, et uniquement pour les deux tests marqués
« ffmpeg » (silence fabriqué localement par lavfi, zéro asset livré).

Ce que la recette verrouille :
  * le calage d'un texte connu produit des mots ORDONNÉS, SANS CHEVAUCHEMENT,
    couvrant EXACTEMENT l'intervalle demandé ;
  * les mots LONGS reçoivent plus de temps que les COURTS (le partage n'est
    pas uniforme — c'est précisément ce que fait la barre) ;
  * un SILENCE détecté n'est peuplé d'AUCUN mot ;
  * la ponctuation crée une pause tenue par `end` mais exclue de `speech_end`
    (borne du karaoké) ;
  * le coût et la durée sont annonçables AVANT tout appel réseau ;
  * SRT/VTT/TXT sortent localement, et le garde-fou de chemin tient.

  runtime\\python\\python.exe -m pytest backend/tests/test_transcribe_service.py -v
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.services.transcribe_service import (CHARS_PER_SUBTITLE_DEFAULT,
                                             align_known_text,
                                             align_narration_clips,
                                             align_to_audio,
                                             detect_silences,
                                             estimate_transcription,
                                             group_words, parse_silencedetect,
                                             probe_duration, resolve_media,
                                             speech_spans, syllables, to_srt,
                                             to_txt, to_vtt, tokenize,
                                             word_weight)

TXT = ("Sous la surface, quelque chose remue. La maree ne demande pas la "
       "permission — elle vient, et l'abysse s'ouvre.")


# ── invariants structurels du calage ────────────────────────────────────────

def _assert_sane(res, start, end, spans=None):
    ws = res["words"]
    assert ws, "aucun mot"
    for a, b in zip(ws, ws[1:]):
        assert a["i"] < b["i"], "mots desordonnes"
        assert a["start"] <= a["end"], f"mot inverse: {a}"
        assert a["end"] <= b["start"] + 1e-9, f"chevauchement {a} / {b}"
    assert ws[0]["start"] == pytest.approx(start, abs=1e-3)
    assert ws[-1]["end"] == pytest.approx(end, abs=1e-3)
    for w in ws:
        assert w["start"] <= w["speech_end"] <= w["end"] + 1e-9


def test_align_covers_interval_exactly():
    res = align_known_text(TXT, start=0.0, duration_s=12.0)
    _assert_sane(res, 0.0, 12.0)
    ws = res["words"]
    assert len(ws) == len(tokenize(TXT))
    # contiguite stricte : la fin d'un mot EST le debut du suivant
    for a, b in zip(ws, ws[1:]):
        assert a["end"] == b["start"]
    # somme des durees == duree de l'intervalle
    total = sum(w["end"] - w["start"] for w in ws)
    assert total == pytest.approx(12.0, abs=1e-3)


def test_align_respects_offset_start():
    res = align_known_text(TXT, start=30.72, end=56.32)
    _assert_sane(res, 30.72, 56.32)


def test_align_is_deterministic():
    a = align_known_text(TXT, start=0.0, duration_s=9.5)
    b = align_known_text(TXT, start=0.0, duration_s=9.5)
    assert a == b


def test_align_rejects_empty_and_bad_interval():
    with pytest.raises(ValueError):
        align_known_text("   ", start=0.0, duration_s=5.0)
    with pytest.raises(ValueError):
        align_known_text(TXT, start=5.0, end=5.0)
    with pytest.raises(ValueError):
        align_known_text(TXT, start=0.0)          # ni end ni duration_s


# ── les mots longs recoivent plus de temps que les courts ───────────────────

def test_long_words_get_more_time_than_short_ones():
    res = align_known_text("la permission", start=0.0, duration_s=4.0)
    la, perm = res["words"]
    d_la = la["end"] - la["start"]
    d_perm = perm["end"] - perm["start"]
    assert d_perm > d_la
    # la barre (Kapwing, mesuree le 10/08/2026) donne 1.00 ; on vise ~3.
    ratio = d_perm / d_la
    assert 2.5 < ratio < 3.5, ratio


def test_word_duration_is_monotone_in_structure():
    mots = ["a", "le", "mare", "surface", "permission", "extraordinaire"]
    res = align_known_text(" ".join(mots), start=0.0, duration_s=20.0)
    durs = [w["end"] - w["start"] for w in res["words"]]
    for d1, d2 in zip(durs, durs[1:]):
        assert d2 > d1, (mots, durs)


def test_syllables_counts_phonetic_nuclei():
    assert syllables("surface") == 2       # -e final muet
    assert syllables("eau") == 1           # groupe vocalique = 1 noyau
    assert syllables("permission") == 3
    assert syllables("la") == 1
    assert syllables("le") == 1            # jamais zero
    # « ao » compte pour UN noyau : approximation assumee du modele (4 au lieu
    # des 5 syllabes reelles) — l'ordre relatif des mots reste juste.
    assert syllables("extraordinaire") == 4
    assert word_weight("permission") > word_weight("la") * 2.5


# ── la ponctuation cree une pause, hors karaoke ─────────────────────────────

def test_punctuation_pause_is_held_by_end_not_speech_end():
    res = align_known_text("alpha. alpha alpha", start=0.0, duration_s=6.0)
    w0, w1, w2 = res["words"]
    # meme mot trois fois : seul le premier porte un point
    assert w0["end"] - w0["start"] > w1["end"] - w1["start"]
    assert w0["speech_end"] < w0["end"]          # la pause est exclue du karaoke
    assert w1["speech_end"] == pytest.approx(w1["end"], abs=1e-3)
    assert w2["speech_end"] == pytest.approx(w2["end"], abs=1e-3)


def test_tokenize_keeps_display_form():
    toks = tokenize("Sous la surface, « quelque » chose…")
    assert [t["word"] for t in toks] == ["Sous", "la", "surface", "quelque",
                                         "chose"]
    assert toks[2]["punct"] == ","
    assert toks[-1]["punct"] == "…"
    # le guillemet OUVRANT isole appartient au mot suivant, le FERMANT au precedent
    assert toks[3]["raw"] == "« quelque »"
    assert toks[2]["raw"] == "surface,"
    assert tokenize("") == []
    # un tiret cadratin isole n'est PAS un mot : il devient la pause du precedent
    dash = tokenize("permission — elle")
    assert [t["word"] for t in dash] == ["permission", "elle"]
    assert dash[0]["punct"] == "—" and dash[0]["raw"] == "permission —"


# ── un silence detecte n'est pas peuple de mots ─────────────────────────────

def test_no_word_lands_inside_a_detected_silence():
    sil = [(4.0, 6.5)]
    res = align_known_text(TXT, start=0.0, end=12.0, silences=sil)
    assert res["spans"] == [[0.0, 4.0], [6.5, 12.0]]
    for w in res["words"]:
        assert not (w["start"] < 6.5 and w["end"] > 4.0), \
            f"mot dans le silence : {w}"
    # couverture exacte des DEUX travees
    ws = res["words"]
    assert ws[0]["start"] == 0.0 and ws[-1]["end"] == 12.0
    left = [w for w in ws if w["end"] <= 4.0 + 1e-9]
    right = [w for w in ws if w["start"] >= 6.5 - 1e-9]
    assert len(left) + len(right) == len(ws)
    assert left[-1]["end"] == pytest.approx(4.0, abs=1e-3)
    assert right[0]["start"] == pytest.approx(6.5, abs=1e-3)


def test_multiple_silences_and_leading_silence():
    sil = [(0.0, 1.2), (5.0, 5.9), (11.0, 12.0)]
    res = align_known_text(TXT, start=0.0, end=12.0, silences=sil)
    assert res["spans"] == [[1.2, 5.0], [5.9, 11.0]]
    for w in res["words"]:
        for a, b in sil:
            assert not (w["start"] < b - 1e-9 and w["end"] > a + 1e-9), \
                f"{w} dans le silence {a}-{b}"


def test_more_silences_than_words_merges_spans():
    # 2 mots, 4 travees demandees : les silences les plus courts sont refermes
    sil = [(1.0, 1.4), (2.0, 2.05), (3.0, 3.02)]
    res = align_known_text("alpha beta", start=0.0, end=5.0, silences=sil)
    assert len(res["spans"]) <= 2
    assert len(res["words"]) == 2


def test_speech_spans_helper():
    assert speech_spans(0.0, 10.0, None) == [(0.0, 10.0)]
    assert speech_spans(0.0, 10.0, []) == [(0.0, 10.0)]
    # silence deborde de l'intervalle -> ecrete
    assert speech_spans(2.0, 8.0, [(0.0, 3.0), (7.0, 20.0)]) == [(3.0, 7.0)]
    # silences chevauchants -> fusionnes
    assert speech_spans(0.0, 10.0, [(2.0, 5.0), (4.0, 6.0)]) == [(0.0, 2.0),
                                                                (6.0, 10.0)]
    # travee trop courte -> absorbee (jamais de travee de 10 ms)
    assert speech_spans(0.0, 10.0, [(0.05, 5.0)]) == [(5.0, 10.0)]


def test_parse_silencedetect_closes_trailing_silence():
    err = ("[silencedetect @ 0x1] silence_start: 1.5\n"
           "[silencedetect @ 0x1] silence_end: 2.75 | silence_duration: 1.25\n"
           "[silencedetect @ 0x1] silence_start: 8.0\n")
    assert parse_silencedetect(err, 10.0) == [(1.5, 2.75), (8.0, 10.0)]
    assert parse_silencedetect("", 10.0) == []


# ── groupage en repliques + export ──────────────────────────────────────────

def test_group_words_respects_chars_and_punctuation():
    res = align_known_text(TXT, start=0.0, duration_s=14.0)
    cues = group_words(res["words"], max_chars=32)
    assert cues
    for c in cues:
        assert len(c["text"]) <= 32 or len(c["words"]) == 1
        assert c["end"] > c["start"]
    for a, b in zip(cues, cues[1:]):
        assert a["end"] <= b["start"] + 1e-9
    # le texte des repliques recompose le texte source
    assert " ".join(c["text"] for c in cues) == \
        " ".join(w["raw"] for w in res["words"])


def test_group_words_breaks_on_silence_gap():
    res = align_known_text(TXT, start=0.0, end=12.0, silences=[(4.0, 6.5)])
    cues = group_words(res["words"], max_chars=200, max_dur_s=99.0)
    assert len(cues) > 1
    for c in cues:
        assert not (c["start"] < 6.5 and c["end"] > 4.0)


def test_srt_vtt_txt_export():
    res = align_known_text(TXT, start=0.0, duration_s=12.0)
    cues = group_words(res["words"], max_chars=CHARS_PER_SUBTITLE_DEFAULT)
    srt = to_srt(cues)
    assert srt.startswith("1\n00:00:00,000 --> ")
    assert "-->" in srt and srt.count("-->") == len(cues)
    vtt = to_vtt(cues)
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> " in vtt
    txt = to_txt(cues)
    assert "\n" in txt and "-->" not in txt
    # horodatage > 1 min correctement formate
    long_cue = [{"start": 3725.5, "end": 3726.0, "text": "x", "words": []}]
    assert "01:02:05,500 --> 01:02:06,000" in to_srt(long_cue)


# ── piste s1 depuis les clips du Montage ────────────────────────────────────

def test_align_narration_clips_only_takes_texted_audio_clips():
    clips = [
        {"tr": "v1", "id": "v1c1", "start": 0, "end": 10},
        {"tr": "a1", "id": "a1c1", "start": 1.28, "end": 6.28,
         "text": "Sous la surface, quelque chose remue."},
        {"tr": "a2", "id": "a2c1", "start": 0, "end": 20},
        {"tr": "a1", "id": "a1c2", "start": 8.0, "end": 13.0,
         "text": "Huit bras, une seule volonte."},
        {"tr": "a1", "id": "a1c3", "start": 14.0, "end": 15.0},   # sans texte
    ]
    out = align_narration_clips(clips, lambda c: None)
    assert [b["clip"] for b in out["blocks"]] == ["a1c1", "a1c2"]
    ws = out["words"]
    assert [w["i"] for w in ws] == list(range(len(ws)))
    assert ws[0]["start"] == pytest.approx(1.28, abs=1e-3)
    assert ws[-1]["end"] == pytest.approx(13.0, abs=1e-3)
    # aucun mot du bloc 2 avant la fin du bloc 1
    b1 = [w for w in ws if w["clip"] == "a1c1"]
    b2 = [w for w in ws if w["clip"] == "a1c2"]
    assert b1[-1]["end"] <= b2[0]["start"]
    # les repliques ne melangent jamais deux clips
    for c in out["cues"]:
        assert c["start"] >= 1.28 and c["end"] <= 13.0


# ── non-regression sur une VRAIE narration (donnees mesurees, hors ligne) ───

# Narration reelle produite par l'app le 10/08/2026 (ElevenLabs, 11,842 s).
# SIL = silences reellement mesures par ffmpeg sur ce fichier ; TRUTH = travee
# de chaque mot d'apres les horodatages AU MOT rendus par un STT sur le MEME
# fichier. Le test rejoue le calage hors ligne : aucun reseau, aucun asset.
_REAL_SIL = [(0.827, 1.171), (2.259, 3.138), (3.719, 4.19), (5.428, 5.819),
             (7.392, 8.288), (9.194, 9.705), (11.416, 11.842)]
_REAL_TXT = ("Sous la surface, quelque chose remue. La maree ne demande pas "
             "la permission, elle vient, et l'abysse s'ouvre. Deepotus a "
             "parle : la houle porte deja son nom.")
_REAL_SPAN_OF_WORD = [0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4,
                      5, 5, 5, 6, 6, 6, 6, 6, 6]


def test_real_narration_words_land_in_the_right_speech_span():
    res = align_known_text(_REAL_TXT, start=0.0, end=11.842,
                           silences=_REAL_SIL)
    spans = res["spans"]
    assert len(spans) == 7
    got = [next(j for j, (a, b) in enumerate(spans)
                if w["start"] >= a - 1e-6 and w["end"] <= b + 1e-6)
           for w in res["words"]]
    assert len(got) == len(_REAL_SPAN_OF_WORD)
    exact = sum(1 for a, b in zip(got, _REAL_SPAN_OF_WORD) if a == b)
    # 26/27 au moment de l'ecriture ; le seul ecart est « ne », une respiration
    # SANS ponctuation en plein milieu de proposition — rien dans le texte ne
    # la predit. Le seuil protege contre une regression, pas contre ce cas.
    assert exact >= 25, (exact, got, _REAL_SPAN_OF_WORD)
    # La regression precise trouvee le 10/08 : « parle : » bascule dans la
    # travee SUIVANTE quand la cible est un cumul global au lieu d'etre
    # renormalisee sur ce qu'il reste. Il doit rester avant le silence 9,194.
    parle = next(w for w in res["words"] if w["w"] == "parle")
    assert parle["end"] <= 9.194 + 1e-6, parle
    assert parle["punct"] == ":"


def test_real_narration_cues_follow_the_sentences():
    res = align_known_text(_REAL_TXT, start=0.0, end=11.842,
                           silences=_REAL_SIL)
    cues = group_words(res["words"], max_chars=42)
    assert [c["text"] for c in cues] == [
        "Sous la surface, quelque chose remue.",
        "La maree ne demande pas la permission,",
        "elle vient, et l'abysse s'ouvre.",
        "Deepotus a parle :",
        "la houle porte deja son nom.",
    ]
    srt = to_srt(cues)
    assert "00:00:00,000 --> 00:00:02,259" in srt
    assert srt.rstrip().endswith("la houle porte deja son nom.")


# ── cout et duree annonces AVANT (aucun appel reseau) ───────────────────────

def test_estimate_announces_cost_and_eta_before_any_call():
    est = estimate_transcription(120.0, "openai")
    if est["ok"]:
        assert est["provider"] == "openai"
        assert est["model"] == "whisper-1"        # seul modele OpenAI au mot
        assert est["word_timestamps"] is True
        assert est["usd"] == pytest.approx(0.012, abs=1e-4)   # 2 min x 0.006
        assert est["eta_s"] > 0
        assert est["breakdown"][0]["unit"] == "min"
    else:                                          # clé absente sur la machine
        assert est["reason"]
        assert est["usd"] == 0.0
    assert estimate_transcription(0.0, "openai")["usd"] == 0.0


def test_estimate_rejects_unknown_provider():
    with pytest.raises(ValueError):
        estimate_transcription(10.0, "whisper-local")


# ── garde-fou de chemin (meme regle que _lut_path / fs_guard) ───────────────

def test_resolve_media_guard():
    d = Path(tempfile.mkdtemp(prefix="dz_sub_"))
    try:
        (d / "voix.mp3").write_bytes(b"x")
        assert resolve_media("voix.mp3", d) == d / "voix.mp3"
        assert resolve_media("../voix.mp3", d) is None
        assert resolve_media("sub/voix.mp3", d) is None
        assert resolve_media("C:\\Windows\\win.ini", d) is None
        assert resolve_media("voix.exe", d) is None
        assert resolve_media("absent.mp3", d) is None
        assert resolve_media("", d) is None
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ── ffmpeg reel : un silence fabrique est vraiment detecte et respecte ──────

def _have_ffmpeg():
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


@pytest.mark.skipif(not _have_ffmpeg(), reason="ffmpeg absent du PATH")
def test_detect_silences_on_a_built_file():
    """Ton 2 s / silence 2 s / ton 2 s, fabrique par lavfi : le silence du
    milieu doit ressortir, et aucun mot ne doit s'y poser."""
    d = Path(tempfile.mkdtemp(prefix="dz_sub_ff_"))
    try:
        wav = d / "tone_gap_tone.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error",
             "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
             "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=2",
             "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
             "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]",
             "-map", "[a]", str(wav)],
            check=True, capture_output=True, timeout=90)
        assert probe_duration(wav) == pytest.approx(6.0, abs=0.15)
        sil = detect_silences(wav, noise_db=-45.0, min_silence_s=0.3)
        assert len(sil) == 1, sil
        s, e = sil[0]
        assert s == pytest.approx(2.0, abs=0.15)
        assert e == pytest.approx(4.0, abs=0.15)

        res = align_to_audio("alpha beta gamma delta epsilon zeta", wav,
                             start=0.0)
        assert len(res["spans"]) == 2
        for w in res["words"]:
            assert not (w["start"] < e - 1e-3 and w["end"] > s + 1e-3), w
        assert res["words"][0]["start"] == 0.0
        assert res["words"][-1]["end"] == pytest.approx(
            res["audio_duration_s"], abs=1e-2)
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.mark.skipif(not _have_ffmpeg(), reason="ffmpeg absent du PATH")
def test_align_to_audio_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        align_to_audio("alpha", Path(tempfile.gettempdir()) / "dz_absent.mp3")
