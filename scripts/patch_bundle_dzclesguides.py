# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzclesguides.py
"""Maillon de queue : « Guide » et « Tester » pour chaque clé de service, et un « Guide » par réseau de Comptes
connectés (t520, 13/11/2026 ; banc backend/tests/test_cles_guides_t520.py).

Ce qu'il pose (quatre ancres uniques relevées le 13/11 sur le bundle de 68f475cc, HORS de tout bloc de couche
__DZ_*_BEGIN__, vérifié à l'écriture par `hors_couche`) :
  P0 avant `function DzTestCle(` : le composant DzGuideCompte({ck}) — le lien « Guide » d'un réseau, lu dans le même
     cache que les clés (dzChargerGuides, GET /api/reglages/guides) ; il vise le chapitre du guide (`doc_fr`/`doc_en`)
     s'il existe, sinon la console. Aucun x.useState( (épinglé à 731) : un x.useReducer force le rendu au chargement.
  P1 dans DzTestCle : « Tester » s'affiche dès qu'un guide existe, GRISÉ tant que la clé n'est pas posée (titre
     reglages.cles.tester_sans_cle) ; avant, il disparaissait (Apify « manquante » n'avait que Guide).
  P2 dans dzFuNeuves, APRÈS la ligne Apify de dzapify (son remplacement reste intact) : Tavily, Exa, Serper, la
     recherche web de la prospection (t354), qui ne se posaient que depuis Prospects.
  P3 dans chaque bloc de Comptes connectés, avant « Connecter » : DzGuideCompte du premier champ du réseau
     (X_API_KEY, TELEGRAM_BOT_TOKEN, YOUTUBE_CLIENT_ID, IG_ACCESS_TOKEN, TIKTOK_CLIENT_KEY).
Le MARKER /*dzclesguides*/ ouvre chacune des quatre poses. Épingles intouchées : x.useState( 731, v2.8.0 x4,
DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzigformat (t494, dont il sonde le marqueur) ; il garde un .js.bak_dzclesguides le temps de
l'écriture puis le SUPPRIME. Son INVERSE est `avant_dzclesguides` dans backend/tests/_i18n_l1_aide.py (lu sur les
PAIRES d'ici), appelé EN TÊTE de `avant_dzigformat`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune
paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses paires (`defaire` relit les paires d'ici).
Run : python scripts/patch_bundle_dzclesguides.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzclesguides")
TAG = "dzclesguides"
MARKER = "/*dzclesguides*/"
MARKER_ATTENDU = 4
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzigformat", "/*dzigformat*/", 1),
    ("dzapify", "/*dzapify*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

_TESTCLE = "function DzTestCle({ck:ck,def:def_,verrou:verrou}){"
GUIDE_COMPTE = (
    "function DzGuideCompte({ck:ck}){" + MARKER + "const[,maj]=x.useReducer(v=>v+1,0);"
    "x.useEffect(()=>{let on=!0;dzChargerGuides().then(()=>{if(on)maj()});return()=>{on=!1}},[]);"
    "const gu=(dzGuides||{})[ck];if(!gu)return null;"
    "const en=typeof dzLang===\"function\"&&dzLang()===\"en\";const href=(en?gu.doc_en:gu.doc_fr)||gu.console;"
    "return r.jsx('a',{href:href,target:'_blank',rel:'noreferrer','data-dz-guide-compte':ck,"
    "title:dzT(\"reglages.comptes.guide_titre\")+' — '+(en?gu.en:gu.fr),"
    "style:{fontSize:11,color:'var(--cyan)',textDecoration:'none'},children:dzT(\"reglages.cles.guide\")})}"
)
_TESTER_AVANT = ("gu&&def_?r.jsx(K,{icon:\"dz-action-tester\",variant:'ghost',size:'sm',title:dzT(\"reglages.cles.tester_titre\"),"
                 "onClick:tester,children:dzT(\"reglages.cles.tester\")}):null")
_TESTER_APRES = (MARKER + "gu?r.jsx(K,{icon:\"dz-action-tester\",variant:'ghost',size:'sm',"
                 "title:def_?dzT(\"reglages.cles.tester_titre\"):dzT(\"reglages.cles.tester_sans_cle\"),disabled:!def_,"
                 "onClick:tester,children:dzT(\"reglages.cles.tester\")}):null")
_APIFY = '{k:"APIFY_TOKEN",label:dzT("reglages.cles.apify"),why:dzT("reglages.cles.apify_why")},'
_RECHERCHE = "".join('{k:"%s",label:dzT("reglages.cles.%s"),why:dzT("reglages.cles.%s_why")},' % (k, n, n)
                     for k, n in (("TAVILY_API_KEY", "tavily"), ("EXA_API_KEY", "exa"), ("SERPER_API_KEY", "serper")))
_CONNECTER = 'k.connect&&r.jsx(K,{variant:"outline",size:"sm",icon:"dz-action-connecter"'

PAIRES = [
    # P0 : le lien « Guide » d'un réseau, défini juste avant DzTestCle (même cache de guides)
    (_TESTCLE, GUIDE_COMPTE + _TESTCLE),
    # P1 : « Tester » visible dès qu'un guide existe, grisé sans clé
    (_TESTER_AVANT, _TESTER_APRES),
    # P2 : Tavily, Exa, Serper après la ligne Apify (le remplacement de dzapify reste un sous-texte intact)
    (_APIFY, _APIFY + MARKER + _RECHERCHE),
    # P3 : « Guide » dans chaque bloc de Comptes connectés, avant « Connecter »
    (_CONNECTER, MARKER + "r.jsx(DzGuideCompte,{ck:k.fields[0].k})," + _CONNECTER),
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
    """L'inverse exact (lu par avant_dzclesguides dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzclesguides")
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
