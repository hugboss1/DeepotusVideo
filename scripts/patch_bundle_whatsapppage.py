# -*- coding: utf-8 -*-
# scripts/patch_bundle_whatsapppage.py
"""Maillon de queue : la page WhatsApp dans la barre des applications et l'entrée « Agent WhatsApp » de Réglages › Espaces
(t311 tâche 8, 27/10/2026, plan docs/superpowers/plans/2026-10-27-t311-agent-whatsapp.md). La page est autonome
(frontend/whatsapp/, montée sur /whatsapp comme /avatar, tâche 7) ; la barre l'ouvre dans une iframe, comme l'Avatar live.

Ce qu'il pose (ancres uniques, relevées le 27/10 sur le bundle de 97cce575, toutes HORS de tout bloc de couche
__DZ_*_BEGIN__, vérifié à l'écriture par `hors_couche`) :
  P1 l'entrée de rail `{id:"whatsapp",…}` entre celle de l'Avatar live et celle des Réglages : libellé
     dzT("whatsapp.rail.titre"), icône Deepotus Glyph `dz-nav-boite-reception` (résolue par __dzGlyphe, maillon dzglyph ;
     aucune icône neuve), description dzT("whatsapp.rail.desc") (frontend/shared/i18n/whatsapp.json). Le MARKER
     /*whatsapppage*/ ouvre cette entrée ;
  P2 la vue : une iframe `/whatsapp/`, clé `pwhatsapp`, après celle de l'Avatar live ;
  P3 `whatsapp` entre dans la liste blanche des vues (`?view=` et « deepotus:navigate ») ;
  P4 Réglages › Espaces (DzEspaces, sortie de dzespace) : sous les comptes de l'espace actif (DzComptesEspace), un
     bouton dzT("whatsapp.espace.ouvrir") [data-dz-wa-espace-ouvrir] qui appelle
     window.__dzWhatsappEspace.ouvrir(st.actif) (frontend/shared/dz-whatsapp-espace.js, chargé par frontend/dist/index.html :
     le panneau des réglages de l'agent de l'espace). Grisé tant que le module n'est pas chargé.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30 (la
confirmation du mode automatique vit dans le module partagé, pas dans le bundle).

Maillon de QUEUE, APRÈS dzwhatsapp (t310, dont il sonde le marqueur) ; il garde un .js.bak_whatsapppage le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_whatsapppage` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzwhatsapp`. Lecture et écriture en
OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses paires
(`defaire` relit les paires d'ici).
Banc : backend/tests/test_whatsapp_page_ecran.py.
Run : python scripts/patch_bundle_whatsapppage.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_whatsapppage")
TAG = "whatsapppage"
MARKER = "/*whatsapppage*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzwhatsapp", "/*dzwhatsapp*/", 1),
    ("avatar", '{id:"avatarlive",', 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_RAIL_AV = '{id:"avatarlive",label:"Avatar live",icon:"dz-media-avatar",desc:dzT("avatar.rail.desc"),new:!0},'
_RAIL_RG = '{id:"settings",label:dzT("commun.objet.reglages"),'
RAIL_WA = ('{id:"whatsapp",label:dzT("whatsapp.rail.titre"),icon:"dz-nav-boite-reception",desc:dzT("whatsapp.rail.desc"),'
           'new:!0},')
_STYLE = 'style:{position:"absolute",inset:0,width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}'
_VUE_AV = ('s==="avatarlive"&&r.jsx("iframe",{src:"/avatar/",title:"Avatar live",allow:"camera; microphone; autoplay",'
           + _STYLE + '},"pavlive"),')
VUE_WA = 's==="whatsapp"&&r.jsx("iframe",{src:"/whatsapp/",title:dzT("whatsapp.page.titre"),' + _STYLE + '},"pwhatsapp"),'
_VUES = '"settings","vectorlab","photolab","avatarlive"],sg=Yu.includes('
OUVRIR = "window.__dzWhatsappEspace&&window.__dzWhatsappEspace.ouvrir(st.actif)"
_CPT = '"cpt:"+st.actif)]})}function DzComptesEspace('
BOUTON_WA = ('st.actif&&r.jsx("div",{style:{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"},children:'
             'r.jsx("button",{type:"button","data-dz-wa-espace-ouvrir":st.actif,style:bt,disabled:!window.__dzWhatsappEspace,'
             'onClick:function(){' + OUVRIR + '},children:dzT("whatsapp.espace.ouvrir")})},"wa:"+st.actif)')

PAIRES = [
    # P1 : l'entrée de rail, entre Avatar live et Réglages (le marqueur l'ouvre)
    (_RAIL_AV + _RAIL_RG, _RAIL_AV + MARKER + RAIL_WA + _RAIL_RG),
    # P2 : la vue, une iframe /whatsapp/ après celle de l'Avatar live
    (_VUE_AV, _VUE_AV + VUE_WA),
    # P3 : la liste blanche des vues (?view= et deepotus:navigate)
    (_VUES, _VUES.replace('"avatarlive"]', '"avatarlive","whatsapp"]')),
    # P4 : Réglages › Espaces, sous les comptes de l'espace actif : « Agent WhatsApp »
    (_CPT, _CPT.replace('"cpt:"+st.actif)]', '"cpt:"+st.actif),' + BOUTON_WA + ']', 1)),
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
    """L'inverse exact (lu par avant_whatsapppage dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_whatsapppage")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count("\r\n") != crlf):
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
