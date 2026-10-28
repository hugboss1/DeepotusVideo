# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzdiffusion.py
"""Maillon de queue : la DIFFUSION WhatsApp d'un post dans le Planificateur (t328 tâche 5, 27/10/2026, plan
docs/superpowers/plans/2026-10-27-t328-diffusions-whatsapp.md, Décisions 6-7). Un compte WhatsApp devient une cible de
post, choisie post par post (comptes.CIBLES_EXPLICITES : jamais un canal par défaut d'un projet ; la boîte des canaux
du projet, frontend/shared/dz-projet-canaux.js, le tait toujours).

Ce qu'il pose (ancres uniques, relevées le 27/10 sur le bundle de 827b35d1, toutes HORS de tout bloc de couche
__DZ_*_BEGIN__, vérifié à l'écriture par `hors_couche`) :
  P1 DzPostComptes (sortie de dzespace) range de nouveau TOUS les comptes de l'espace : juste APRÈS la liste filtrée
     par dzwhatsapp (P2, `c.plateforme!=="whatsapp"`, laissé intact à l'octet pour que son `--check` et son inverse
     restent vrais), `dzPcCache[esp].liste=j.comptes||[]` la remplace par la liste entière. Le MARKER /*dzdiffusion*/
     ouvre ce remplacement ;
  P2 DzPostComptes, sous la liste des comptes : quand UN compte whatsapp est coché, le point de montage
     `<div data-dz-diffusion={post.id}>` dont le ref appelle window.__dzDiffusionWhatsapp.monter(nœud, post.id,
     {compte, espace, statut, delai: 700} ; un statut changé fait relire le panneau) (frontend/shared/dz-diffusion-whatsapp.js, chargé par frontend/dist/index.html ; le
     délai laisse partir le PATCH des comptes, différé de 500 ms ; s'il arrive plus tard, le panneau relit seul sur le
     409 « un seul compte »). Sa clé = post + compte whatsapp : cocher un autre compte ne le remonte pas. Deux comptes
     whatsapp cochés : une ligne dzT("diffusion.panneau.un_seul_compte") à la place ;
  P3 la table des canaux `_t` reçoit `whatsapp` (libellé « WhatsApp », icône du rail WhatsApp `dz-nav-boite-reception`,
     aucune icône neuve) APRÈS le calcul de `Bu` (`__dzWaCanal=(_t.whatsapp={…})` dans la même déclaration) : la carte
     du calendrier, le routage et __dzSchedCanaux le disent ; les boutons de canaux de l'inspecteur et du filtre (Bu) ne
     le proposent pas : un canal whatsapp ne se pose que par son compte. L'entrée commence par `label:` (et non
     `{id:"whatsapp",`, compte épinglé x1 par le banc de whatsapppage pour l'entrée de rail).
  P4/P5 (revue) la carte de routage du canal whatsapp : « automatique » (pastille verte) et le libellé
     dzT("diffusion.routage.kapso") au lieu de « publication manuelle ».
Aucune ancre ne mord sur le remplacement d'un maillon AMONT (dzwhatsapp P2, dzassistant, la table de montage) : chacun
reste présent à l'octet, ce que le banc vérifie en rejouant leurs `--check`.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30 (les
confirmations de la diffusion vivent dans le module partagé, pas dans le bundle).

Maillon de QUEUE, APRÈS whatsapppage (t311, dont il sonde le marqueur, et dzwhatsapp dont il défait P2) ; il garde un
.js.bak_dzdiffusion le temps de l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est
`avant_dzdiffusion` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de
`avant_dzinspiration` (fusion t320 : rejoué APRÈS dzcapture puis dzinspiration, il est la queue de la chaîne). Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne.
DÉFAIRE le maillon AVANT de changer ses paires (`defaire` relit les paires d'ici).
Banc : backend/tests/test_diffusion_ecran.py.
Run : python scripts/patch_bundle_dzdiffusion.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzdiffusion")
TAG = "dzdiffusion"
MARKER = "/*dzdiffusion*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("whatsapppage", "/*whatsapppage*/", 1),
    ("dzwhatsapp", "/*dzwhatsapp*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

# Aucune paire ne touche le texte d'un remplacement d'un maillon AMONT (sinon son `--check` le dirait « partiellement
# appliqué ») : chaque ancre commence APRÈS le remplacement voisin (dzwhatsapp P2, dzassistant, la table de montage) et
# le garde intact à l'octet.
_APRES_FILTRE = ';maj()},function(){delete dzPcCache[esp];maj()}'
SANS_FILTRE = ';' + MARKER + 'dzPcCache[esp].liste=j.comptes||[];maj()},function(){delete dzPcCache[esp];maj()}'
_SOUS_LISTE = '}),esp!=="deepotus"&&!choisis.length&&'
MONTER = "window.__dzDiffusionWhatsapp&&window.__dzDiffusionWhatsapp.monter(n,p.id,{compte:wa[0],espace:esp,statut:p.status,delai:700})"
MONTAGE = ('(function(){var wa=choisis.filter(function(i){var v=liste.find(function(x2){return x2.id===i});'
           'return v&&v.plateforme==="whatsapp"});'
           'return wa.length===1?r.jsx("div",{"data-dz-diffusion":p.id,ref:function(n){n&&' + MONTER + '}},'
           '"dzdiff:"+p.id+":"+wa[0]):'
           'wa.length>1?r.jsx("div",{"data-dz-diffusion-plusieurs":p.id,style:{fontSize:11.5,color:"var(--amber)"},'
           'children:dzT("diffusion.panneau.un_seul_compte")}):null})(),')
_APRES_BU = 'Bu=Object.values(_t),Im=['
CANAL_WA = '{label:"WhatsApp",id:"whatsapp",icon:"dz-nav-boite-reception",color:"#25d366",bg:"#0b2a19",limit:1024}'
TABLE_WA = 'Bu=Object.values(_t),__dzWaCanal=(_t.whatsapp=' + CANAL_WA + '),Im=['
_ROUTE_V = 'if(!A)return null;const V=I==="telegram"&&'
_ROUTE_LIB = 'children:V?dzT("scheduler.routage.pub_bot"):dzT("scheduler.routage.pub_manuelle")'

PAIRES = [
    # P1 : DzPostComptes range de nouveau les comptes whatsapp : la liste filtrée par dzwhatsapp (P2, gardé à l'octet)
    # est remplacée, juste après, par la liste entière (le marqueur)
    (_APRES_FILTRE, SANS_FILTRE),
    # P2 : sous la liste des comptes, le point de montage du panneau de diffusion (un compte whatsapp coché)
    (_SOUS_LISTE, '}),' + MONTAGE + 'esp!=="deepotus"&&!choisis.length&&'),
    # P3 : la table des canaux connaît whatsapp, ajouté APRÈS le calcul de Bu (les boutons de canaux ne le proposent pas)
    (_APRES_BU, TABLE_WA),
    # P4 (revue t328 tâche 5) : la carte de routage tient le canal whatsapp pour automatique (l'adaptateur de diffusion)
    (_ROUTE_V, _ROUTE_V.replace('const V=I==="telegram"', 'const V=I==="whatsapp"||I==="telegram"')),
    # P5 : et son libellé dit « diffusion WhatsApp par Kapso », jamais « publication manuelle »
    (_ROUTE_LIB, 'children:I==="whatsapp"?dzT("diffusion.routage.kapso"):' + _ROUTE_LIB[len("children:"):]),
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
    """L'inverse exact (lu par avant_dzdiffusion dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzdiffusion")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count("\r\n") != crlf or neuf.count('{id:"whatsapp",') != s.count('{id:"whatsapp",')):
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
