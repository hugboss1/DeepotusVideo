# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzschedconf.py
"""Maillon de queue : PLANIFICATEUR, confirmer avant de publier ou de supprimer (20/10/2026, relevé du catalogue t248).

« Envoyer maintenant » publiait sur Telegram, X, YouTube, Instagram et TikTok au premier clic, et « Supprimer » effaçait
un post pour de bon (DELETE /api/schedule/{id}, sans corbeille), alors que le reste de l'app confirme ses actions
irréversibles par la couche partagée `window.__dzDialogue` (patch_bundle_dialogue). Ce maillon les fait passer par
`__dzDialogue.confirmer` ; annuler = rien n'est envoyé ni supprimé :
  - S0 : `__dzSchedCanaux(liste)`, posée devant la table des canaux `_t` du Planificateur : les canaux visés en clair
    (« X, Telegram »), ou « aucun canal » ;
  - S1 : « Envoyer maintenant » de la vue Routage (H) : confirmation qui nomme le post et ses canaux, bouton « Publier » ;
  - S2 : l'envoi de l'inspecteur du post (N, mêmes appels) : même confirmation ;
  - S3 : « Supprimer » de l'inspecteur (V) : confirmation « définitive, sans corbeille ; le rendu reste dans la
    Bibliothèque » (vrai : la route ne supprime que la ligne ScheduledPost).
Les trois dialogues sont `danger` : bouton rouge, Entrée = Annuler (contrat de la couche).
AUCUN hook neuf (x.useState( reste à 731) ; v2.8.0 ×4, DzTracks 181 intouchés. `await window.__dzDialogue.confirmer(`
passe de 25 à 28 hors couche (épingle de test_dialogue_bundle).
Textes : clés dzT `scheduler.envoi.*` et `scheduler.post.supprimer_*`, toutes LITTÉRALES dans le livré, dans
frontend/shared/i18n/planif_confirmer.json (scheduler.json est ÉCRIT par scripts/i18n_l2_generer.py).

Maillon de QUEUE, APRÈS dzdock (dont il sonde le marqueur) ; il garde un .js.bak_dzschedconf le temps de l'écriture puis
le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzschedconf` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzdock`. Lecture et écriture en OCTETS.
Banc : backend/tests/test_planif_confirmations.py.
Run : python scripts/patch_bundle_dzschedconf.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzschedconf")
TAG = "dzschedconf"
MARKER = "function __dzSchedCanaux("
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzdock", "function __dzRelancer(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 25),
]

CANAUX = ('function __dzSchedCanaux(c){c=(c||[]).map(function(k){return _t[k]&&_t[k].label||k});'
          'return c.length?c.join(", "):dzT("scheduler.envoi.aucun_canal")}')


def _envoi(p):
    """La confirmation d'un envoi immédiat du post `p` (identique dans la vue Routage et l'inspecteur)."""
    return (f'if(!{CONFIRMER}dzT("scheduler.envoi.question",{{titre:{p}.title||"",canaux:__dzSchedCanaux({p}.channels)}}),'
            '{titre:dzT("scheduler.envoi.titre"),ok:dzT("scheduler.envoi.publier"),danger:!0}))return;')


PAIRES = [
    ('}const _t={x:{id:"x",label:"X",',                                                                         # S0
     '}' + CANAUX + 'const _t={x:{id:"x",label:"X",'),
    ('async function H(){l(!0),u("");const I=await D.fireScheduledPost(e.id);',                                 # S1
     'async function H(){' + _envoi("e") + 'l(!0),u("");const I=await D.fireScheduledPost(e.id);'),
    ('async function N(){y(!0),v("");const j=await D.fireScheduledPost(e.id);',                                 # S2
     'async function N(){' + _envoi("e") + 'y(!0),v("");const j=await D.fireScheduledPost(e.id);'),
    ('async function V(){j&&(await D.deleteScheduledPost(j.id),u(null),o==null||o())}',                         # S3
     'async function V(){if(!j||!' + CONFIRMER + 'dzT("scheduler.post.supprimer_q",{titre:j.title||""}),'
     '{titre:dzT("scheduler.post.supprimer_titre"),ok:dzT("scheduler.post.supprimer"),danger:!0}))return;'
     'await D.deleteScheduledPost(j.id),u(null),o==null||o()}'),
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
    """L'inverse exact (lu par avant_dzschedconf dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def partiel(s: str) -> bool:
    """Marqueur présent mais le défaire complet échoue : une paire manque."""
    if MARKER not in s:
        return False
    try:
        defaire(s)
    except AssertionError:
        return True
    return False


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        if partiel(s):
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzschedconf "
                             f"(défaire avec le maillon d'avant l'ajout, puis appliquer)")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    neuf = appliquer(s)
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if (neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181
            or neuf.count(CONFIRMER) != 28):
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
