# -*- coding: utf-8 -*-
# scripts/patch_bundle_montage.py
"""Patcher assert-gardé : PISTES DYNAMIQUES (P1) du Montage.

Ce que le patch fait, en une phrase : la couche `window.DzTracks`, injectée
EN QUEUE après `subs`, remplace la table figée SVM_TRACKS par un état du
projet — les pistes s'ajoutent, se retirent, se réordonnent, et leur ORDRE
décide de la composition au rendu (montage_service._tracks_meta, champ
`layer`).

BASELINE : bundle POST-patch subs (dernier patch en date de la chaîne bundle).
Backup dédié : .js.bak_montage (état juste avant CE patch).
Position dans la chaîne : EN QUEUE, après `subs`.

AVERTISSEMENT DE CHAÎNE — lire avant de toucher quoi que ce soit, il n'est pas
recopié pour la forme. Une passe qualité a déjà effacé neuf éditions du rack
VFX parce que ses sections vivaient À L'INTÉRIEUR d'un bloc injecté en amont
et qu'un patcher amont a été relancé seul. MESURÉ LE 03/09/2026 SUR CETTE
COPIE : le bloc `sonvfx` du bundle contient AUJOURD'HUI les remplacements
V3/V4/V6/V8/V9 de patch_bundle_vfxrack.py et S3…S17 de patch_bundle_subs.py —
vingt sections. Relancer patch_bundle_sonvfx.py réécrirait ce bloc EN PLACE
depuis sa source et les effacerait toutes, sans un mot, et RIEN ne peut les
rejouer ici : ni .bak_vfxrack ni .bak_subs n'existent dans cette copie (ils
sont gitignorés) et l'ancre V10 de vfxrack est déjà consommée. D'où ce
patcher : tag NEUF (`montage`), .bak dédié, EN QUEUE, et pas une seule
section posée à l'intérieur d'un bloc amont. Ne JAMAIS relancer un patcher
amont seul — `python scripts/repatch_all.py --from <tag>` rejoue la chaîne,
et `--list` la montre.

Sections :
  M1  injecte frontend/patches/montage.js (window.DzTracks) juste après le
      bloc subs — même scope module, alias r/x du bundle disponibles ;
  M2  lie /shared/montage.css dans dist/index.html (idempotent) ;
  M3  la timeline lit svmTracksOf(proj) au lieu de la constante SVM_TRACKS ;
  M4  svmApplyProject resynchronise SVM_TRACK_BUS sur les pistes restaurées ;
  M4b svmTracksSet — le POINT D'ÉCRITURE UNIQUE de proj.tracks (historique,
      bus, état, « NON ENREGISTRÉ ») ; sans lui chaque appelant réécrirait sa
      propre version de la même séquence ;
  M5  payload de rendu : clé `tracks` (le backend y lit l'ordre) ;
  M6  autosave : la même clé, pour que l'ordre survive au rechargement ;
  M7  restauration : proj.tracks reconstruit depuis la sauvegarde serveur ;
  M8  barre de transport : « + vidéo » / « + audio » ;
  M9a/M9b en-tête de piste : poignée de glisser-déposer et ▲ ▼ ×, posés en
      SURIMPRESSION (l'en-tête fait 88 × 40–54 px et il est plein — mesuré,
      voir montage.css) ;
  M10 (P2) chip « mot : couleur / rebond / glow » + bouton « emoji », posés
      DANS le remplacement de M8 (l'ancre A_M8 est déjà consommée, et la
      barre d'outils n'offre pas de seconde ancre unique).

Mécanique identique à patch_bundle_subs.py : restauration du .bak dédié puis
ré-application, chaque ancre devant apparaître EXACTEMENT une fois, sinon
abandon sans rien écrire. Le miroir du résultat est
backend/tests/test_montage_bundle.py (comptes dans le bundle livré + le cœur
JS exécuté sous node).

Run :
    python scripts/patch_bundle_montage.py              # dépôt
    python scripts/patch_bundle_montage.py --root <dir> # app installée
    python scripts/patch_bundle_montage.py --check      # n'écrit rien
    python scripts/patch_bundle_montage.py --strip      # retire le patch

Compatible scripts/repatch_all.py : `--force-unchained` est accepté et ignoré.
"""
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
REL_HTML = pathlib.Path("frontend/dist/index.html")
PATCH_SRC = REPO / "frontend" / "patches" / "montage.js"
TAG = "montage"

BEGIN = "/*__DZ_MONTAGE_BEGIN__*/"
END = "/*__DZ_MONTAGE_END__*/"
ANCHOR_INJECT = "/*__DZ_SUBS_END__*/"

CSS_ANCHOR = '<link rel="stylesheet" href="/shared/subs.css">'
CSS_INSERT = '\n    <link rel="stylesheet" href="/shared/montage.css">'


# ── M3 : les pistes viennent du PROJET, plus de la constante ────────────────
A_M3 = "          SVM_TRACKS.map(function(tr){"
R_M3 = "          svmTracksOf(proj).map(function(tr){"

# ── M4 : bus resynchronisé à l'application d'un projet ──────────────────────
# SVM_TRACK_BUS est lu à neuf endroits du bloc sonvfx ; la couche le MUTE en
# place (voir montage.js) — une seule ancre au lieu de neuf.
A_M4 = "    setProj(np);"
R_M4 = "    svmTrackBusSync(np.tracks);\n    setProj(np);"

# ── M4b : le point d'écriture UNIQUE de proj.tracks ─────────────────────────
A_M4b = "  function svmApplyProject(d){"
R_M4b = ("  /* P1 — TOUTE écriture de proj.tracks passe ici : historique poussé,\n"
         "     SVM_TRACK_BUS resynchronisé, projet réécrit, « NON ENREGISTRÉ »\n"
         "     allumé. Deux appelants (la barre d'outils et les en-têtes de\n"
         "     piste) ; sans ce point unique, chacun aurait sa propre version de\n"
         "     la séquence et l'un des deux finirait par en oublier un morceau.\n"
         "     RESTE CONNU : l'historique ne mémorise que {clips, mixDb} — un\n"
         "     annuler après un retrait de piste ramène les CLIPS, pas la piste.\n"
         "     Ils redeviennent visibles dès qu'on rajoute une piste du même\n"
         "     genre : l'identifiant repris est le plus petit libre, donc le\n"
         "     leur. C'est dit dans la note du bouton, ce n'est pas silencieux. */\n"
         "  function svmTracksSet(ts){pushHistory();svmTrackBusSync(ts);"
         "setProj(function(p){return Object.assign({},p,{tracks:ts})});setDirty(!0)}\n"
         "  function svmApplyProject(d){")

# ── M5 : payload de rendu ───────────────────────────────────────────────────
A_M5 = "      clips:clips.filter(function(c){return c.src}).map(function(c){"
R_M5 = ("      /* P1 — l'ORDRE des pistes, du haut vers le bas : c'est lui que\n"
        "         montage_service._tracks_meta traduit en rang de composition\n"
        "         (`layer`) et en bus de mixage. Un backend qui ne connaît pas\n"
        "         encore la clé l'ignore et rend exactement ce qu'il rendait. */\n"
        "      tracks:svmTracksPayload(proj),\n"
        "      clips:clips.filter(function(c){return c.src}).map(function(c){")

# ── M6 : autosave ───────────────────────────────────────────────────────────
A_M6 = "      duration_master:durMaster,ducking:ducking,clips:clips,"
R_M6 = ("      duration_master:durMaster,ducking:ducking,clips:clips,\n"
        "      /* sans cette clé, une piste ajoutée disparaissait au rechargement\n"
        "         et les clips qu'elle portait retombaient sur une piste inconnue,\n"
        "         donc hors du rendu — silencieusement. */\n"
        "      tracks:svmTracksPayload(proj),")

# ── M7 : restauration ───────────────────────────────────────────────────────
A_M7 = 'var np={demo:!1,name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",'
R_M7 = ('var np={demo:!1,tracks:svmTracksFrom(d.tracks),'
        'name:d.name||"montage",version:"v1",ratio:d.ratio||"9:16",')

# ── M8 : barre de transport ─────────────────────────────────────────────────
A_M8 = ('r.jsx("button",{className:"svm-tbtn",title:"Raccourcis ("'
        '+svmKeyLabel("keys_panel")+") — personnalisables",')

# ── M10 (P2) : la chip « mot : couleur / rebond / glow » et le bouton emoji ──
# ELLES VIVENT DANS R_M8, pas dans une section à elles : l'ancre A_M8 est déjà
# CONSOMMÉE par M8, et il n'existe pas de seconde ancre unique dans cette barre
# d'outils. Le panneau de style, lui, vit dans un tiroir du bloc `sonvfx` que
# cette chaîne ne peut pas rouvrir (vingt sections amont s'y trouvent).
# `DzTracks`, pas `DzMontage` : le bundle déclare DÉJÀ une fonction DzMontage
# au premier niveau (l'écran Montage lui-même) — redéclarer ce nom est une
# SyntaxError en sémantique module, celle sous laquelle index.html charge le
# bundle. C'est ce que `node_check_module` de test_montage_bundle.py garde.
# Le bouton emoji est RÉVERSIBLE : `pushHistory()` avant l'ajout, donc
# « annuler » retire les clips posés, et ce sont des clips ordinaires.
R_M10 = ('r.jsx(DzTracks.WordAnimChip,{value:(proj.subsStyle||{}).wordAnim||"couleur",'
         'onChange:function(v){subsStyleSet({wordAnim:v})}}),\n'
         '        r.jsx(DzTracks.EmojiBtn,{segments:subsSegsOf(clips),'
         'tracks:svmTracksOf(proj),note:fireNote,'
         'onAdd:function(cs){pushHistory();'
         'setClips(function(k){return (k||[]).concat(cs)});setDirty(!0)}}),')

R_M8 = ('r.jsx(DzTracks.TrackAdd,{tracks:svmTracksOf(proj),onChange:svmTracksSet}),\n'
        '        ' + R_M10 + '\n'
        '        /* bouton discret du panneau raccourcis — fin de transport */\n'
        '        ' + A_M8)

# ── M9a / M9b : en-tête de piste ────────────────────────────────────────────
# Le groupe est un FRÈRE des rangées, pas un membre : il est positionné en
# absolu dans l'en-tête (voir montage.css — l'en-tête fait 88px de large et
# il est déjà plein, c'est mesuré). L'ancre est préfixe du remplacement :
# test_montage_bundle.py ne cherche donc pas à la voir disparaître.
_HB = ("DzTracks.headBtns(tr,svmTracksOf(proj),svmTracksSet,clips,setClips,"
       "fireNote)")
A_M9a = 'children:[thAdd,thM,thS,thLock]},"br"),'
R_M9a = 'children:[thAdd,thM,thS,thLock]},"br"),\n                  ' + _HB + ','
A_M9b = 'children:[thType,thLock]},"tr")]}),'
R_M9b = ('children:[thType,thLock]},"tr"),\n                  ' + _HB + ']}),')

PATCHES = [("M3-tracks", A_M3, R_M3), ("M4-bus", A_M4, R_M4),
           ("M4b-setter", A_M4b, R_M4b),
           ("M5-payload", A_M5, R_M5), ("M6-save", A_M6, R_M6),
           ("M7-apply", A_M7, R_M7), ("M8-toolbar", A_M8, R_M8),
           ("M9a-head-audio", A_M9a, R_M9a), ("M9b-head-video", A_M9b, R_M9b)]


def nl(text, crlf):
    """Aligne les fins de ligne d'un fragment sur celles du fichier cible.

    Le bundle est un mélange : la partie minifiée n'a pas de saut de ligne,
    les blocs injectés (sonvfx, sfxstudio, vfxrack) sont en CRLF — git
    normalise les sources du dépôt à la sortie. Une ancre écrite en LF ne
    matcherait donc jamais : on la convertit avant toute comparaison.
    """
    t = text.replace("\r\n", "\n")
    return t.replace("\n", "\r\n") if crlf else t


def apply(s, anchor, replacement, tag):
    """Remplacement assert-gardé : l'ancre doit exister exactement une fois."""
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_text(p):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def write_text(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def patch_html(html, strip):
    """Lien /shared/montage.css — idempotent, indépendant du bundle."""
    ins = nl(CSS_INSERT, "\r\n" in html)
    if strip:
        if "shared/montage.css" in html:
            return html.replace(ins, "").replace(ins.strip(), ""), "lien css retiré"
        return html, ""
    if "shared/montage.css" in html:
        return html, ""
    if html.count(CSS_ANCHOR) != 1:
        raise SystemExit(f"[{TAG}] ancre css introuvable ou multiple. Aborting.")
    return html.replace(CSS_ANCHOR, CSS_ANCHOR + ins), "lien css ajouté"



def guard_downstream(bak):
    """Refuse de tourner si un patcher AVAL est deja passe.

    CE MAILLON RESTAURE SON .bak PUIS REAPPLIQUE : sans cette garde, le
    relancer seul remet le bundle a l'etat d'AVANT lui et efface EN SILENCE
    tout ce que les maillons suivants ont ecrit. Mesure sur la chaine du
    2026-08-11 : materialforge seul = 23 couples ancre->remplacement detruits
    (21 in-bloc vfxrack/subs + 2 cardforge), vfxrack seul = 17, subs seul = 8.
    Le bundle reste syntaxiquement valide, tous les marqueurs BEGIN/END
    restent la, `node --check` passe : c'est exactement le mode de panne qui a
    deja coute 22 correctifs a ce depot. `--force-unchained` la desarme —
    c'est ce que passe repatch_all.py quand il rejoue TOUTE la chaine dans
    l'ordre.
    """
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in sorted(bak.parent.glob(stem + ".bak_*")):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name} (plus "
                f"recent que {bak.name}). Le relancer seul effacerait ce que "
                "les maillons suivants ont ecrit — sans un mot. Rejouer la "
                "chaine entiere (repatch_all) ou forcer avec "
                "--force-unchained en connaissance de cause.")


def main():
    args = sys.argv[1:]
    root = pathlib.Path(".")
    if "--root" in args:
        root = pathlib.Path(args[args.index("--root") + 1]).resolve()
    check = "--check" in args
    strip = "--strip" in args

    bundle = root / REL_BUNDLE
    html_path = root / REL_HTML
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    if not html_path.is_file():
        raise SystemExit(f"[{TAG}] index.html introuvable : {html_path}")
    if not PATCH_SRC.is_file():
        raise SystemExit(f"[{TAG}] source introuvable : {PATCH_SRC}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)

    if "--force-unchained" not in args:
        guard_downstream(bak)

    if check:
        # Contrôle à sec : on valide les ancres sur l'état PRÉ-patch
        # (le .bak s'il existe, sinon le bundle courant), sans rien écrire.
        src = bak if bak.exists() else bundle
        s, _ = read_text(src)
        crlf = "\r\n" in s
        if s.count(ANCHOR_INJECT) != 1:
            raise SystemExit(
                f"[M1-inject] anchor count={s.count(ANCHOR_INJECT)} (want 1) "
                f"dans {src.name}. Aborting.")
        for tag, anchor, _repl in PATCHES:
            n = s.count(nl(anchor, crlf))
            if n != 1:
                raise SystemExit(
                    f"[{tag}] anchor count={n} (want 1) dans {src.name}. Aborting.")
        print(f"[{TAG}] applicable sur {src} ({len(PATCHES) + 1} ancres OK)")
        return

    if strip:
        s, bom = read_text(bundle)
        done = []
        if BEGIN in s:
            head, rest = s.split(BEGIN, 1)
            _old, tail = rest.split(END, 1)
            s = head.rstrip("\n") + tail.lstrip("\n")
            done.append("bloc retiré")
        if bak.exists():
            shutil.copy2(bak, bundle)
            done.append("bundle restauré depuis le .bak")
        else:
            write_text(bundle, s, bom)
        html, hbom = read_text(html_path)
        html, hmsg = patch_html(html, True)
        if hmsg:
            write_text(html_path, html, hbom)
            done.append(hmsg)
        print(f"[{TAG}] strip — {', '.join(done) or 'rien à faire'}")
        return

    if not bak.exists():
        shutil.copy2(bundle, bak)
        print("backup ->", bak)
    else:
        shutil.copy2(bak, bundle)

    s, bom = read_text(bundle)
    crlf = "\r\n" in s
    # M1 — injection de la couche, juste après le bloc subs
    component = PATCH_SRC.read_bytes().decode("utf-8-sig")
    block = nl("\n" + BEGIN + "\n" + component + "\n" + END, crlf)
    if s.count(ANCHOR_INJECT) != 1:
        raise SystemExit(
            f"[M1-inject] anchor count={s.count(ANCHOR_INJECT)} (want 1). Aborting.")
    s = s.replace(ANCHOR_INJECT, ANCHOR_INJECT + block)
    # M3..M9 — ancres du bloc sonvfx (source injectée)
    for tag, anchor, repl in PATCHES:
        s = apply(s, nl(anchor, crlf), nl(repl, crlf), tag)
    write_text(bundle, s, bom)

    # M2 — feuille de style (index.html, hors chaîne des .bak)
    html, hbom = read_text(html_path)
    html, hmsg = patch_html(html, False)
    if hmsg:
        write_text(html_path, html, hbom)

    print("OK — bundle patché (pistes dynamiques : ordre, ajout, retrait, "
          "bus resynchronisé). Size:", bundle.stat().st_size,
          "| index.html:", hmsg or "inchangé")


if __name__ == "__main__":
    main()
