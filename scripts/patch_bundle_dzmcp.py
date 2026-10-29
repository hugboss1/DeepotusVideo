# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzmcp.py
"""Maillon de queue : l'onglet « Serveur MCP » de Réglages (t345, D1 du lot Scenario, 29/10/2026, spec
docs/superpowers/specs/2026-10-27-scenario-explorations-design.md). Le panneau lui-même vit dans
frontend/shared/dz-mcp.js (window.__dzMcp.monter) ; le maillon ne pose que la porte d'entrée :
  P1 : « mcp » dans la liste blanche ?section= (`ym`) — le MARKER /*dzmcp*/ la suit ;
  P2 : l'onglet, entre « Tarifs et budget » et « Transfert entre machines », libellé dzT("mcp.reglages.onglet") ;
  P3 : le corps de l'onglet, EN TÊTE des branches du panneau : un <div data-dz-mcp-hote> dont la ref (fonction, aucun
       hook : x.useState( reste à 731) appelle window.__dzMcp.monter ;
  P4 : la rubrique de la recherche des Réglages (dzRubriques), entre « transfert » et « espaces ».
Clés dzT : frontend/shared/i18n/mcp.json (FR/EN), assemblées par scripts/i18n_assembler.py.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzapify (dont il sonde le marqueur) ; il garde un .js.bak_dzmcp le temps de l'écriture puis le
SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzmcp` dans backend/tests/_i18n_l1_aide.py (lu
sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzapify` : P2, P3 et P4 s'insèrent dans des remplacements de maillons
amont (dzespace S5/S7, dzcapture), qui ne se défont donc qu'après lui. Lecture et écriture en OCTETS (le bundle est en
CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_mcp_ecran.py.
Run : python scripts/patch_bundle_dzmcp.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzmcp")
TAG = "dzmcp"
MARKER = "/*dzmcp*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzapify", "/*dzapify*/", 1),
    ("dzespace", "function DzEspaceSel(", 1),
    ("dzcapture", "/*dzcapture*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

HOTE = ('s==="mcp"&&r.jsx("div",{"data-dz-mcp-hote":"1",ref:function(el){if(el&&window.__dzMcp)'
        'window.__dzMcp.monter(el)}}),')

PAIRES = [
    # P1 : la liste blanche ?section= (et dz-reglages-section)
    # (le marqueur est APRÈS la liste : test_agent_connaissance relit la liste ym comme un tableau JSON de chaînes)
    ('"appearance","pricing"];function DzStudioEst',
     '"appearance","pricing","mcp"];' + MARKER + 'function DzStudioEst'),
    # P2 : l'onglet, avant « Transfert entre machines »
    ('{k:"pricing",l:dzT("reglages.onglet.tarifs")},{k:"transfert"',
     '{k:"pricing",l:dzT("reglages.onglet.tarifs")},{k:"mcp",l:dzT("mcp.reglages.onglet")},{k:"transfert"'),
    # P3 : le corps, en tête des branches du panneau
    ('maxWidth:880},children:[s==="accounts"&&r.jsx(Tm,{})',
     'maxWidth:880},children:[' + HOTE + 's==="accounts"&&r.jsx(Tm,{})'),
    # P4 : la rubrique de la recherche des Réglages
    ('transfert:dzT("reglages.onglet.transfert"),espaces:',
     'transfert:dzT("reglages.onglet.transfert"),mcp:dzT("mcp.reglages.onglet"),espaces:'),
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
    """L'inverse exact (lu par avant_dzmcp dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzmcp")
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
