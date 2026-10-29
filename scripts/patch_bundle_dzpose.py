# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzpose.py
"""Maillon de queue : Game Assets 3D, l'interrupteur « T-pose » devient un choix Aucune / T-pose / A-pose (t376, lot
« Game Assets : finitions », plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md,
décision D6).
Avant : un interrupteur `tpose` (booléen) que seul Rodin savait transmettre ; la route refusait les autres moteurs.
  P1 : `dzPoseChoix(p,set,maj)`, posée JUSTE AVANT `DzGameAssets` : trois boutons radio (Aucune / T-pose / A-pose),
       l'état du choix lu par window.__dzPose3d (/shared/dz-pose3d.js : GET /api/assets3d/pose, gratuit) ; T-pose et
       A-pose grisés avec la raison quand le moteur ne sait pas poser, quand le sujet n'est pas un personnage, ou
       quand il manque les vues multiples ; avertissement en cas de doute ; bouton « Vérifier l'image (IA) » quand
       une classification vision aiderait (payante, confirmée avec son montant par dz-pose3d).
  P2 : l'état initial porte `pose:""` au lieu de `tpose:!1`.
  P3 : le champ « T-pose » devient le champ « Pose » (dzT) et son choix ; le MARKER /*dzpose*/ le précède. Le
       rafraîchissement passe par le setPP existant (aucun état React neuf).
  P4 : le corps envoyé à POST /api/assets/3d passe par __dzPose3d.corps : la pose ne part que si le choix est actif.
Clés dzT neuves : frontend/shared/i18n/pose3d.json (pose3d.*).

Maillon de QUEUE, APRÈS dzecartes (dont il sonde le marqueur) ; il garde un .js.bak_dzpose le temps de l'écriture
puis le SUPPRIME. Son INVERSE est `avant_dzpose` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici),
appelé EN TÊTE de `avant_dzecartes`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient
de fin de ligne ; les ancres sont hors des couches __DZ_*_BEGIN__. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_pose3d_ecran.py.
Run : python scripts/patch_bundle_dzpose.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzpose")
TAG = "dzpose"
MARKER = "/*dzpose*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzecartes", "/*dzecartes*/", 1),
    ("ecran", "function DzGameAssets({variant:e}){", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

ECRAN = "function DzGameAssets({variant:e}){"
CHOIX = ('function dzPoseChoix(p,set,maj){var P=window.__dzPose3d,'
         'q={engine:p.engine,multiview:p.multiview,subject:p.subject,image:p.image_filename},'
         'e=P?P.etat(q,maj):null,actif=!!(e&&e.actif),'
         'tx=P?P.textes(e,p.engine):{raison:"",avertissement:"",precision:""},'
         'val=actif?(p.pose||""):"",'
         'OPT=[["",dzT("pose3d.choix.aucune"),dzT("pose3d.aide.aucune")],["t-pose",dzT("pose3d.choix.t"),dzT("pose3d.aide.t")],'
         '["a-pose",dzT("pose3d.choix.a"),dzT("pose3d.aide.a")]],dit=tx.raison||tx.avertissement||tx.precision;'
         'return r.jsxs("div",{"data-dz-pose3d":"",children:['
         'r.jsx("div",{role:"radiogroup","aria-label":dzT("pose3d.choix.champ"),style:{display:"flex"},'
         'children:OPT.map(function(o){var on=val===o[0],off=!actif&&o[0]!=="";'
         'return r.jsx("button",{type:"button",role:"radio","aria-checked":on,disabled:off,"data-pose":o[0]||"aucune",'
         'title:off?tx.raison:o[2],onClick:function(){if(!off)set("pose",o[0])},'
         'style:{flex:1,fontSize:11,padding:"4px 6px",whiteSpace:"nowrap",cursor:off?"not-allowed":"pointer",'
         'background:on?"var(--cyan)":"var(--surface-2)",color:on?"#000":"var(--ink)",'
         'border:"1px solid var(--stroke)",opacity:off?.45:1},children:o[1]},o[0]||"aucune")})}),'
         'dit?r.jsx("div",{"data-dz-pose3d-note":"",style:{fontSize:11,marginTop:4,'
         'color:(!tx.raison&&tx.avertissement)?"var(--amber)":"var(--ink-soft)"},children:dit}):null,'
         '(P&&e&&e.vision_proposee)?r.jsx("button",{type:"button","data-dz-pose3d-vision":"",'
         'onClick:function(){P.classer(q,maj)},style:{marginTop:4,fontSize:11,padding:"2px 8px",cursor:"pointer",'
         'background:"transparent",color:"var(--ink)",border:"1px solid var(--stroke)"},'
         'children:dzT("pose3d.vision.bouton")}):null]})}')

ETAT = 'textures:!0,tpose:!1,formats:["glb"]}),p=PP[0],setPP=PP[1];'
ETAT_NEUF = 'textures:!0,pose:"",formats:["glb"]}),p=PP[0],setPP=PP[1];'

CHAMP = 'r.jsx(O,{label:"T-pose",children:r.jsx(Ze,{checked:p.tpose,onChange:function(v){set("tpose",v)}})}),'
CHAMP_NEUF = (MARKER + 'r.jsx(O,{label:dzT("pose3d.choix.champ"),children:dzPoseChoix(p,set,'
              'function(){setPP(function(o){return Object.assign({},o)})})}),')

ENVOI = 'fetch("/api/assets/3d",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)})'
ENVOI_NEUF = ('fetch("/api/assets/3d",{method:"POST",headers:{"Content-Type":"application/json"},'
              'body:JSON.stringify(window.__dzPose3d?window.__dzPose3d.corps(p):p)})')

PAIRES = [
    # P1 : le choix, défini avant l'écran
    (ECRAN, CHOIX + ECRAN),
    # P2 : l'état initial
    (ETAT, ETAT_NEUF),
    # P3 : le champ « Pose »
    (CHAMP, CHAMP_NEUF),
    # P4 : le corps envoyé
    (ENVOI, ENVOI_NEUF),
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
    """L'inverse exact (lu par avant_dzpose dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzpose")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count(ECRAN) != 1 or neuf.count("\r\n") != crlf):
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
