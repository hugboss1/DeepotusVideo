# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzgardeclient.py
"""Maillon de queue : le PLANIFICATEUR et les règles du client (t309 tâche 4, 26/10/2026, plan
docs/superpowers/plans/2026-10-26-t309-securites-client.md, spec docs/superpowers/specs/2026-10-25-boite-a-outils-design.md
§5.5). Le serveur (tâches 1-3) refuse par un 409 structuré `{message, code, client, nom, canaux}` de programmer un post de
client sans consentement en cours, sans validation du client, ou sans confirmation nominative ; or
`D.updateScheduledPost` AVALAIT tout refus (`n.ok?…:null`) et l'écran gardait « programmé ». La logique vit dans le script
externe frontend/shared/dz-garde-client.js (window.__dzGardeClient, ses dialogues par window.__dzDialogue) ; ce maillon
ne fait que le brancher. Trois groupes de paires, toutes HORS de tout bloc de couche __DZ_*_BEGIN__ (mesuré le
26/10/2026 sur le bundle de t309 T3 : G1 à l'offset 336 537, G2 à 1 017 655, G3 à 1 015 591 et 1 034 408 (offsets de la base),
avant SONVFX qui commence à 1 226 492 ; chaque ancre est unique) :
  G1 `D.updateScheduledPost` : si window.__dzGardeClient existe, `return window.__dzGardeClient.patch(e,t,envoyer)` où
     envoyer(corps) est le PATCH d'origine (même URL, méthode, en-tête) ; sinon le code d'origine, ENTIER et inchangé.
     Le MARKER /*dzgardeclient*/ ouvre ce corps ;
  G2 Planificateur `Lm` : un x.useEffect (AUCUN x.useState) posé après l'écouteur d'origine « deepotus:schedule-reload » :
     si window.__dzGardeClient existe, « deepotus:schedule-recharger » appelle reloadPosts (o) ; retiré au démontage ;
  G3 l'état « a_valider » : couleur (Rm) ambre comme « ready » ; pastille de l'inspecteur ambre avec le libellé
     dzT("scheduler.etat.a_valider") (l'objet de props d'origine, sortie d'i18nfix, reste intact derrière la condition).
     Ces deux paires ne sont pas derrière window.__dzGardeClient : elles ne font que nommer une
     valeur que seul le serveur de t309 produit (sans elles, l'écran affichait « a_valider » brut, en cyan).
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30 (la
confirmation nominative est appelée depuis le script externe, pas depuis le bundle).

Maillon de QUEUE, APRÈS dzcanauxpre (t325, dont il sonde le marqueur) ; il garde un .js.bak_dzgardeclient le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzgardeclient` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzcanauxpre`. Lecture et écriture en
OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses paires
(`defaire` relit les paires d'ici).
Banc : backend/tests/test_garde_client_ecran.py.
Run : python scripts/patch_bundle_dzgardeclient.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzgardeclient")
TAG = "dzgardeclient"
MARKER = "/*dzgardeclient*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzcanauxpre", "/*dzcanauxpre*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

# le PATCH d'origine, gardé tel quel (repli) et rejoué par envoyer(corps)
_FETCH = 'fetch(`${Te}/schedule/${e}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(%s)})'
_ORIGINE = 'try{const n=await ' + (_FETCH % "t") + ';return n.ok?await n.json():null}catch{return null}'

PAIRES = [
    # G1 : updateScheduledPost délègue à window.__dzGardeClient.patch quand le script est là, l'origine sinon
    ('updateScheduledPost:async(e,t)=>{' + _ORIGINE + '},',
     'updateScheduledPost:async(e,t)=>{' + MARKER + 'if(window.__dzGardeClient)return window.__dzGardeClient.patch(e,t,'
     'c=>' + (_FETCH % "c") + ');' + _ORIGINE + '},'),
    # G2 : Lm recharge sa liste sur deepotus:schedule-recharger (émis par dz-garde-client.js), sans x.useState
    ('()=>window.removeEventListener("deepotus:schedule-reload",R)},[o]),',
     '()=>window.removeEventListener("deepotus:schedule-reload",R)},[o]),'
     'x.useEffect(()=>{if(!window.__dzGardeClient)return;function __dzGcR(){o&&o()}'
     'return window.addEventListener("deepotus:schedule-recharger",__dzGcR),'
     '()=>window.removeEventListener("deepotus:schedule-recharger",__dzGcR)},[o]),'),
    # G3a : couleur (Rm) ambre comme ready
    ('ready:"var(--amber)",scheduled:"var(--cyan)"',
     'ready:"var(--amber)",a_valider:"var(--amber)",scheduled:"var(--cyan)"'),
    # G3b : pastille de l'inspecteur, tonalité ambre comme ready et libellé traduit. L'objet de props d'origine (sortie
    # du maillon i18nfix, table scheduler.etat.* entière) reste INTACT derrière la condition : on le remplace en bloc
    # pour a_valider au lieu d'insérer une entrée dans la table, que test_i18n_planif_news compte à l'octet.
    ('r.jsx(te,{tone:e.status==="posted"?"green":e.status==="failed"?"red":e.status==="ready"?"amber":',
     'r.jsx(te,e.status==="a_valider"?{tone:"amber",dot:!0,children:dzT("scheduler.etat.a_valider")}:'
     '{tone:e.status==="posted"?"green":e.status==="failed"?"red":e.status==="ready"?"amber":'),
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
    """L'inverse exact (lu par avant_dzgardeclient dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzgardeclient")
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
