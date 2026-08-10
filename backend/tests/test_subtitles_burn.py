# -*- coding: utf-8 -*-
"""Piste S1 : le pont panneau <-> moteur, et la GRAVURE au rendu.

Ce que ces tests protegent, dans l'ordre d'importance :

1. **La taille vue est la taille gravee.** Le panneau exprime ses tailles en
   pixels de la LARGEUR de rendu (1080 en portrait, 1920 en paysage), l'ASS en
   pixels ramenes a 1080 de HAUT. Sans conversion, un « 52 px » regle dans
   l'apercu sortirait a 92 px en 9:16. On verifie l'aller (px reels) sur les
   quatre ratios ET l'apercu 480p.
2. **La chaine ffmpeg historique ne bouge pas** quand la piste est vide :
   octet pour octet, sinon tous les rendus d'avant changent.
3. **Le filtre est le DERNIER maillon video** (apres les overlays V2), sinon
   un overlay recouvrirait le texte.
4. **`fontsdir` est toujours pose** : sans lui libass retombe en silence sur
   une fonte systeme et le rendu cesse de ressembler a l'apercu, sans erreur.
5. Le garde-fou de chemin des fontes (table CLOSE, aucun chemin client).

Run : <python embarque> backend/tests/test_subtitles_burn.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import montage_service as M          # noqa: E402
from app.services import subtitle_service as S         # noqa: E402
from app.services import subtitle_ui as SU             # noqa: E402

_dir = tempfile.mkdtemp()
_A = os.path.join(_dir, "a.mp4")
open(_A, "wb").close()
_IMG = os.path.join(_dir, "ov.png")
open(_IMG, "wb").close()
_OUT = os.path.join(_dir, "out.mp4")

UI = {"font": "Impact", "size": 52, "weight": 900, "upper": True,
      "tracking": 1, "color": "#ffffff", "bgOn": False,
      "outOn": True, "outColor": "#1b1b1f", "outW": 6,
      "shOn": True, "shColor": "#00000099", "shX": 0, "shY": 5, "shBlur": 0,
      "karOn": True, "karColor": "#ffd23f", "karMode": "fill", "anim": "none",
      "align": "center", "valign": "bottom", "marginV": 9, "width": 84,
      "maxChars": 30, "lh": 1.0}

SEGS = [{"start": 1.0, "end": 4.0, "text": "SOUS LA SURFACE"},
        {"start": 8.0, "end": 11.0, "text": "QUELQUE CHOSE ECOUTE"}]


def _v1(n=1):
    return [{"path": _A, "src_dur": 30.0, "src_in": 0.0,
             "start": float(i * 5), "end": float(i * 5 + 5),
             "transition": "cut", "transition_s": 0.0, "speed": 0.0,
             "effects": None} for i in range(n)]


def _cmd(**kw):
    kw.setdefault("w", 1080)
    kw.setdefault("h", 1920)
    return M._build_montage_command(
        kw.pop("v1", _v1()), kw.pop("v2", []), [], None, fps=30, mix_db={},
        ducking=False, duration_master=False, preview=False, out=_OUT, **kw)


def test_taille_vue_egale_taille_gravee():
    """Le px du panneau survit a la conversion, sur tous les canevas."""
    for ratio in ("9:16", "16:9", "1:1", "4:5"):
        for preview in (False, True):
            w, h = SU.canvas_for_ratio(ratio, preview)
            st = SU.ui_to_style(UI, (w, h))
            # px reellement dessines par libass = Fontsize * (h / 1080)
            grave = st["size"] * h / S.REF_HEIGHT
            # px reellement dessines par l'apercu = size * (w / canvasW)
            ref_w = 1920 if w > h else 1080
            vu = UI["size"] * w / ref_w
            assert abs(grave - vu) < 0.01, (
                f"{ratio} preview={preview} : grave {grave:.2f} px, "
                f"vu {vu:.2f} px")
    # marges : 9 % de la hauteur, (100-84)/2 % de la largeur
    st = SU.ui_to_style(UI, (1080, 1920))
    assert abs(st["margin_v"] * 1920 / 1080 - 0.09 * 1920) < 2
    assert abs(st["margin_h"] * 1920 / 1080 - 0.08 * 1080) < 2


def test_fonte_systeme_traduite_en_fonte_embarquee():
    """« Impact » n'est pas livre : il doit devenir une fonte EMBARQUEE, pas
    partir tel quel vers un fallback silencieux de libass."""
    assert SU.ui_font("Impact") == "Anton"
    assert SU.ui_font("Courier New") == "JetBrains Mono"
    assert SU.ui_font("Anton") == "Anton"          # deja embarquee
    assert SU.ui_font("Fonte Qui N'Existe Pas") == S.DEFAULT_FONT
    st = SU.ui_to_style(UI, (1080, 1920))
    assert S.font_path(st["font"]) is not None, "fonte non livree"
    assert st.get("font_fallback") is None


def test_chaine_historique_intacte_sans_sous_titres():
    """Piste vide (ou clef absente) : la commande ne change pas d'un octet."""
    ref, _ = _cmd()
    for payload in (None, {}, {"segments": []}, {"style": UI, "segments": []}):
        p, info = M._subs_ass(payload, (1080, 1920), "vide")
        assert p is None and info == {}, payload
        got, _ = _cmd(subs_ass=p)
        assert got == ref, f"commande modifiee par {payload!r}"
    assert "subtitles=" not in " ".join(ref)


def test_gravure_en_dernier_apres_les_overlays():
    """Le texte passe AU-DESSUS des overlays V2 : son filtre doit consommer la
    sortie du dernier overlay, pas celle du montage V1."""
    v2 = [{"path": _IMG, "is_image": True, "src_dur": 0.0, "src_in": 0.0,
           "start": 0.0, "end": 4.0, "opacity": None, "tf": None, "mp": None}]
    cmd, _ = _cmd(v2=v2, subs_ass=os.path.join(_dir, "x.ass"))
    fc = cmd[cmd.index("-filter_complex") + 1]
    last = fc.split(";")[-1]
    assert last.startswith("[ob0]"), last          # ob0 = sortie de l'overlay
    assert "subtitles=" in last and last.endswith("format=yuv420p[outv]")
    # un seul filtre subtitles dans tout le graphe
    assert fc.count("subtitles=") == 1


def test_fontsdir_toujours_pose_et_chemin_echappe():
    """Sans fontsdir, libass ne trouve pas les fontes embarquees et retombe
    sur autre chose SANS erreur ffmpeg — donc il est non negociable."""
    cmd, _ = _cmd(subs_ass=r"C:\Users\x\pi ste\s1.ass")
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "fontsdir=" in fc
    assert r"C\:/Users/x/pi ste/s1.ass" in fc, fc   # ':' et '\' echappes
    assert S.fonts_dir().name == "_fonts"


def test_ass_ecrit_porte_style_et_karaoke():
    """Le fichier ecrit est bien un ASS complet, au canevas du rendu, avec un
    `\\k` par mot — c'est ce que libass lit."""
    p, info = M._subs_ass({"style": UI, "segments": SEGS}, (1080, 1920), "t1")
    try:
        assert p is not None and p.is_file()
        txt = p.read_text(encoding="utf-8")
        assert not txt.startswith("\ufeff"), "BOM : libass decale la 1re ligne"
        assert "PlayResX: 1080" in txt and "PlayResY: 1920" in txt
        assert ",Anton," in txt                     # fonte embarquee gravee
        assert txt.count("Dialogue:") == 2
        assert txt.count("{\\k") == 6               # 3 + 3 mots
        assert info["segments"] == 2 and info["karaoke"] is True
        # apercu 480p : meme fichier, tailles a l'echelle
        p2, _ = M._subs_ass({"style": UI, "segments": SEGS}, (270, 480), "t2")
        assert "PlayResY: 480" in p2.read_text(encoding="utf-8")
        p2.unlink()
    finally:
        if p is not None and p.exists():
            p.unlink()


def test_karaoke_coupe_suit_le_reglage_du_panneau():
    """`karOn:false` doit reellement enlever les `\\k` — pas juste l'apercu."""
    ui = dict(UI, karOn=False)
    p, info = M._subs_ass({"style": ui, "segments": SEGS}, (1080, 1920), "t3")
    try:
        assert info["karaoke"] is False
        assert "{\\k" not in p.read_text(encoding="utf-8")
    finally:
        p.unlink()


def test_ce_qui_ne_se_grave_pas_est_nomme():
    """L'honnetete du WYSIWYG : ce que l'apercu fait et que l'ASS ne sait pas
    faire doit etre NOMME, pas grave a peu pres.

    Les six reglages qui ne pouvaient RIEN produire ont ete retires du panneau
    (cf. l'entete de `subtitle_ui`). Un style enregistre AVANT le retrait les
    porte encore : on ne les grave pas, et on dit pourquoi — c'est la famille
    `legacy:`.
    """
    ancien = dict(UI, bgOn=True, bgMode="fill", bgRadius=10, bgPad=12,
                  outOn=True, shOn=True, shBlur=18, lh=1.4, anim="type",
                  karMode="scale")
    u = SU.ui_unsupported(ancien, (1080, 1920))
    for k in ("outOn", "legacy:bgRadius", "legacy:shBlur", "legacy:lh",
              "legacy:anim", "legacy:karScale", "legacy:bgMode"):
        assert k in u, f"{k} grave en silence"
        assert len(u[k]) > 30, f"{k} : raison trop courte pour etre utile"
    # un style du panneau ACTUEL (plus aucun des six) ne signale rien
    actuel = dict(UI, bgOn=False, outOn=True, shOn=True, shOff=3,
                  anim="pop", karMode="fill")
    for mort in ("bgRadius", "bgMode", "shBlur", "shX", "shY", "lh"):
        actuel.pop(mort, None)
    assert SU.ui_unsupported(actuel, (1080, 1920)) == {}, \
        "un style entierement gravable ne doit rien signaler"


def test_les_animations_gardees_arrivent_vraiment_dans_l_ass():
    """Fondu et pop ont ete GARDES parce qu'ils se gravent (mesure a l'image
    dans la sonde libass). Ils doivent donc atterrir dans le fichier."""
    import re
    for anim, motif in (("fade", r"\\fad\(\d+,0\)"),
                        ("pop", r"\\t\(0,\d+,\\fscx100\\fscy100\)")):
        p, _ = M._subs_ass({"style": dict(UI, anim=anim), "segments": SEGS},
                           (1080, 1920), "tanim")
        try:
            ev = [l for l in p.read_text(encoding="utf-8").splitlines()
                  if l.startswith("Dialogue:")]
            assert ev and all(re.search(motif, l) for l in ev), (anim, ev[:1])
        finally:
            p.unlink()
    # une animation retiree ne laisse AUCUNE trace : pas de tag approximatif
    p, _ = M._subs_ass({"style": dict(UI, anim="type"), "segments": SEGS},
                       (1080, 1920), "tanim")
    try:
        ev = [l for l in p.read_text(encoding="utf-8").splitlines()
              if l.startswith("Dialogue:")]
        assert ev and not any("\\fad" in l or "\\t(" in l for l in ev)
    finally:
        p.unlink()


def test_lignes_repliees_comme_dans_l_apercu():
    """Regression vue A L'IMAGE : le panneau repliait sur 3 lignes, la gravure
    sortait 1 ligne qui debordait du cadre (ASS en WrapStyle 2 : libass ne
    replie rien tout seul). Le repli doit etre celui du panneau, au mot pres."""
    assert SU.ui_wrap("One of the best decisions I", 12) == \
        ["One of the", "best", "decisions I"]
    assert SU.ui_wrap("deja\ncoupe", 4) == ["deja", "coupe"]
    assert SU.ui_wrap("anticonstitutionnellement", 8) == \
        ["anticonstitutionnellement"], "un mot n'est jamais tronconne"
    long = [{"start": 0.0, "end": 3.0,
             "text": "One of the best decisions I made all year"}]
    p, _ = M._subs_ass({"style": dict(UI, maxChars=18), "segments": long},
                       (1080, 1920), "t4")
    try:
        ev = [l for l in p.read_text(encoding="utf-8").splitlines()
              if l.startswith("Dialogue:")]
        assert len(ev) == 1
        assert ev[0].count("\\N") == 2, ev[0]      # 3 lignes gravees
    finally:
        p.unlink()
    # Le SECOND critere : la largeur du cadre. Le preset « Pop » a un corps de
    # 164 px — 27 caracteres tiennent sous maxChars=30 mais PAS dans 1080 px.
    # L'apercu (bloc a `width` %) replie ; la gravure doit replier pareil.
    from app.services import subtitle_service as _S
    if _S._measure_px("A", SU.ui_to_style(UI, (1080, 1920)), 1.0) is None:
        return                                     # PIL absent : critere px NA
    big = SU.style_to_ui(_S.STYLES["pop"], (1080, 1920))
    big["maxChars"] = 30
    p, _ = M._subs_ass(
        {"style": big,
         "segments": [{"start": 0.0, "end": 3.0,
                       "text": "One of the best decisions I"}]},
        (1080, 1920), "t5")
    try:
        ev = [l for l in p.read_text(encoding="utf-8").splitlines()
              if l.startswith("Dialogue:")]
        assert "\\N" in ev[0], (
            "27 caracteres en corps 164 : ca ne tient pas dans le cadre, "
            "la gravure doit replier comme l'apercu — " + ev[0])
    finally:
        p.unlink()


def test_fonte_servie_seulement_depuis_la_table_close():
    """Route /subtitles/fonts/{family} : rien d'autre que les fontes livrees."""
    assert S.font_path("../../../../windows/win.ini") is None
    assert S.font_path("C:/Windows/Fonts/arial.ttf") is None
    assert S.font_path("Anton") is not None


def test_aller_retour_preset_moteur_vers_panneau():
    """Les prereglages exposes au panneau doivent revenir au meme style
    moteur : sinon choisir « Pop » dans la liste ne rendrait pas « Pop »."""
    canvas = (1080, 1920)
    for pre in SU.ui_presets(canvas):
        back = SU.ui_to_style(pre["style"], canvas)
        ref = S.resolve_style(pre["id"])
        for key in ("font", "color", "align", "valign", "uppercase",
                    "chars_per_line"):
            assert back[key] == ref[key], f"{pre['id']}.{key}"
        for key in ("size", "outline"):
            assert abs(back[key] - ref[key]) <= max(1.5, ref[key] * 0.03), \
                f"{pre['id']}.{key} : {back[key]} != {ref[key]}"
        # marges : le panneau ne les regle qu'en POURCENTAGE entier du cadre —
        # 1 % de 1080 = 10.8 px, donc l'aller-retour perd au plus un demi-cran.
        for key in ("margin_v", "margin_h"):
            assert abs(back[key] - ref[key]) <= 5.5, \
                f"{pre['id']}.{key} : {back[key]} != {ref[key]}"


def main():
    fails = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            fails += 1
            print(f"  FAIL {name}: {e}")
    if fails:
        print(f"\n{fails} test(s) en echec")
        sys.exit(1)
    print("\ntous les tests de la gravure S1 passent")


if __name__ == "__main__":
    main()
