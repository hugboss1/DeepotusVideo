# -*- coding: utf-8 -*-
# scripts/patch_bundle_dza2d.py
"""Maillon de queue : les cartes de l'onglet Assets 2D illustrées, et l'onglet en français ET en anglais (t377, lot
« Game Assets : finitions », 30/10/2026).
Avant : le cadre de chaque carte de `DzAssets2D` (maillon assets2d, t125) n'avait que l'icône de sa catégorie, et
« Choisir un outil », les quatre phrases, « Ouvrir » et les infobulles du guide étaient en français en dur.
Maintenant :
  * le cadre passe au 16:9 et montre l'illustration de l'outil, générée une fois par fal (Nano Banana Pro, devis
    accepté le 30/10/2026, 0,60 $) au style de la marque et rangée dans les statiques :
    frontend/dist/assets2d/cartes/<id>.webp (640 × 360). `loading="lazy"`, `decoding="async"`, `alt=""` (le titre de
    la carte dit déjà l'outil). L'icône de la catégorie reste DESSOUS : si l'image manque, `onError` la masque et
    l'icône réapparaît ;
  * chaque texte affiché passe par dzT (frontend/shared/i18n/a2d.json, clés a2d.*), le français repris à
    l'identique. Restent tels quels : les noms propres (Sprite Lab, Tile Lab, Pixel — Vectorlab, Card Forge) et
    « Guide ↗ », déjà traduit par la glyphe G1.

Les paires sont des remplacements exacts, chacun unique dans le bundle. Le MARKER /*dza2d*/ précède le titre de
l'onglet. Aucun état React neuf, aucune confirmation neuve.

Maillon de QUEUE, APRÈS dzga3d (dont il sonde le marqueur) ; il garde un .js.bak_dza2d le temps de l'écriture puis le
SUPPRIME. Son INVERSE est `avant_dza2d` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE
de `avant_dzga3d`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne ;
les ancres sont hors des couches __DZ_*_BEGIN__. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_assets2d_cartes_ecran.py.
Run : python scripts/patch_bundle_dza2d.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dza2d")
TAG = "dza2d"
MARKER = "/*dza2d*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzga3d", "/*dzga3d*/", 1),
    ("assets2d", "function DzAssets2D(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]


def T(k, v=None):
    """dzT("k") ou dzT("k",{…}) écrit dans le bundle."""
    return f'dzT("{k}")' if v is None else f'dzT("{k}",{{{v}}})'


# L'icône de la catégorie, telle que t125 la pose (gardée DESSOUS comme repli)
_ICONE = ('r.jsx("span",{style:{width:40,height:40,display:"flex"},dangerouslySetInnerHTML:{__html:__dzCatSVG[c.id]||""}})')
_IMAGE = ('r.jsx("img",{src:"/assets2d/cartes/"+c.id+".webp",alt:"",loading:"lazy",decoding:"async",'
          'onError:function(ev){ev.currentTarget.style.display="none"},'
          'style:{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover",display:"block"}},"i")')

PAIRES = [
    # ── titre de l'onglet ──
    ('marginBottom:12},children:"Choisir un outil"},"t")', 'marginBottom:12},children:' + MARKER + T("a2d.outils.choisir")
     + '},"t")'),
    # ── les phrases des cartes ──
    ('p:"Une image ou une vidéo devient des cadres puis une planche de sprites : directions, squelette, hitboxes, exports '
     'pour le moteur."', 'p:' + T("a2d.carte.sprites")),
    ('p:"Tuiles sans raccord, blob 47 / 16, variantes et formes, feuilles exportées vers Tiled, LDtk et Godot."',
     'p:' + T("a2d.carte.tiles")),
    ('p:"Retouche au pixel : ligne de temps des cadres, tuile iso 2:1 et ses diagonales, rastériser une image générée."',
     'p:' + T("a2d.carte.pixel")),
    ('p:"Cartes à jouer : gabarits imprimeur, dos et mire, langues, art en lot, livret."', 'p:' + T("a2d.carte.cards")),
    # ── le cadre : 16:9, l'illustration par-dessus l'icône ──
    ('r.jsx("div",{"aria-hidden":"true",style:{height:72,borderRadius:8,display:"flex",alignItems:"center",'
     'justifyContent:"center",background:"var(--cat-fill,var(--bg-base))",color:"var(--cat)"},children:' + _ICONE + '},"v")',
     'r.jsxs("div",{"aria-hidden":"true",style:{aspectRatio:"16 / 9",position:"relative",overflow:"hidden",borderRadius:8,'
     'display:"flex",alignItems:"center",justifyContent:"center",background:"var(--cat-fill,var(--bg-base))",'
     'color:"var(--cat)"},children:[' + _ICONE[:-1] + ',"s")' + ',' + _IMAGE + ']},"v")'),
    # ── boutons ──
    ('title:"Ouvrir "+c.t,children:"Ouvrir"}', 'title:' + T("a2d.carte.ouvrir_titre", "outil:c.t") + ',children:'
     + T("a2d.carte.ouvrir") + '}'),
    ('title:"Le chapitre « "+c.t+" » du guide"', 'title:' + T("a2d.carte.guide_titre", "outil:c.t")),
    ('title:"Pas encore de chapitre « "+c.t+" » dans le guide"', 'title:' + T("a2d.carte.guide_absent", "outil:c.t")),
]


def lire(p):
    b = p.read_bytes()
    bom = b.startswith(b"\xef\xbb\xbf")
    return b.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, texte, bom):
    p.write_bytes((("﻿" if bom else "") + texte).encode("utf-8"))


def appliquer(s: str) -> str:
    for ancre, remplace in PAIRES:
        n = s.count(ancre)
        if n != 1:
            raise SystemExit(f"[{TAG}] ancre x{n} (attendu 1) : {ancre[:80]!r}")
        s = s.replace(ancre, remplace, 1)
    return s


def defaire(s: str) -> str:
    """L'inverse exact (lu par avant_dza2d dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def partiel(s: str) -> bool:
    if MARKER not in s:
        return False
    try:
        defaire(s)
    except AssertionError:
        return True
    return False


def hors_couche(s: str, jeton: str) -> bool:
    """Le jeton n'est dans aucun bloc /*__DZ_<NOM>_BEGIN__*/ … /*__DZ_<NOM>_END__*/."""
    i = s.index(jeton)
    for m in re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", s):
        if m.start() <= i <= s.index("/*__DZ_%s_END__*/" % m.group(1)):
            return False
    return True


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        if partiel(s):
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dza2d")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    if any("\n" in a + z or "x.useState(" in z or CONFIRMER in z for a, z in PAIRES):
        raise SystemExit(f"[{TAG}] paire fautive (fin de ligne, x.useState( ou confirmation directe)")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    if not all(hors_couche(s, a) for a, _z in PAIRES):
        raise SystemExit(f"[{TAG}] une ancre est dans un bloc de couche __DZ_*_BEGIN__")
    neuf = appliquer(s)
    if not all(hors_couche(neuf, z) for _a, z in PAIRES):
        raise SystemExit(f"[{TAG}] une paire tombe dans un bloc de couche __DZ_*_BEGIN__")
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if (neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181
            or neuf.count(CONFIRMER) != 30 or neuf.count("function DzAssets2D(") != 1
            or neuf.count("\r\n") != crlf):
        raise SystemExit(f"[{TAG}] un compte figé a bougé")
    if check:
        print(f"[{TAG}] à appliquer ({len(PAIRES)} paires)")
        return
    shutil.copyfile(BUNDLE, BAK)
    try:
        ecrire(BUNDLE, neuf, bom)
    except BaseException:
        shutil.copyfile(BAK, BUNDLE)                    # jamais un bundle à moitié écrit
        raise
    finally:
        BAK.unlink(missing_ok=True)
    print(f"[{TAG}] appliqué")


if __name__ == "__main__":
    main()
