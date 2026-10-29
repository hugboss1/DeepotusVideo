# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzcurseur.py
"""Maillon de queue : le curseur de BASE de la coque à la charte (t373, lot A « Finitions esthétiques », décision D1,
plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md).
Le composant `Oe` du bundle (37 usages : Studio, Quick, Modèles, News, Réglages…) dessinait sa propre piste (pilule
--bg-base), un rempli dégradé cyan → violet et une pastille ronde de 14 px, PAR-DESSUS un input invisible
(opacity:0). Le seul curseur de l'app qui échappait à la règle commune /shared/dz-curseur.css.
  P1 : ces quatre éléments deviennent UN input visible (classe dz-curseur, nommé par son libellé `a`), que la règle
       commune dessine en fader : rainure encastrée, rempli --amber, bouton rectangulaire strié, focus --amber.
       Le MARKER /*dzcurseur*/ le précède. `l` (le pourcentage) reste calculé, sans usage : la paire ne touche que le
       rendu.
Aucune clé dzT : aucun texte neuf.

Maillon de QUEUE, APRÈS dzmcp (dont il sonde le marqueur) ; il garde un .js.bak_dzcurseur le temps de l'écriture puis le
SUPPRIME. Son INVERSE est `avant_dzcurseur` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN
TÊTE de `avant_dzmcp`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de
ligne ; l'ancre est hors des couches __DZ_*_BEGIN__. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_curseur_ecran.py.
Run : python scripts/patch_bundle_dzcurseur.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzcurseur")
TAG = "dzcurseur"
MARKER = "/*dzcurseur*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzmcp", "/*dzmcp*/", 1),
    ("curseur", "(Oe,{", 37),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

ANCIEN = ('r.jsxs("div",{style:{position:"relative",height:18,display:"flex",alignItems:"center"},children:['
          'r.jsx("div",{style:{position:"absolute",inset:"7px 0",borderRadius:999,background:"var(--bg-base)",'
          'border:"1px solid var(--stroke)"}}),'
          'r.jsx("div",{style:{position:"absolute",left:0,top:7,bottom:7,width:`${l}%`,'
          'background:"linear-gradient(90deg, var(--cyan), var(--violet))",borderRadius:999}}),'
          'r.jsx("input",{type:"range",min:t,max:n,step:o,value:e,onChange:d=>i==null?void 0:i(Number(d.target.value)),'
          'style:{position:"absolute",inset:0,opacity:0,width:"100%",cursor:"pointer"}}),'
          'r.jsx("div",{style:{position:"absolute",left:`calc(${l}% - 7px)`,width:14,height:14,borderRadius:999,'
          'background:"var(--ink-strong)",boxShadow:"0 0 0 3px var(--bg-base), 0 0 12px var(--cyan-glow)",'
          'pointerEvents:"none"}})]})')
NOUVEAU = (MARKER + 'r.jsx("input",{type:"range",className:"dz-curseur",min:t,max:n,step:o,value:e,"aria-label":a,'
           'onChange:d=>i==null?void 0:i(Number(d.target.value)),style:{display:"block",width:"100%"}})')

PAIRES = [
    # P1 : le curseur de base — piste, rempli, pastille et input invisible → un input visible à la charte
    (ANCIEN, NOUVEAU),
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
    """L'inverse exact (lu par avant_dzcurseur dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzcurseur")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count("(Oe,{") != 37 or neuf.count("\r\n") != crlf):
        raise SystemExit(f"[{TAG}] un compte figé a bougé")
    if check:
        print(f"[{TAG}] à appliquer ({len(PAIRES)} paire)")
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
