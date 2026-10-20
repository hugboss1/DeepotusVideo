# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzconstats.py
"""Maillon de queue : CONSTATS du catalogue de l'assistant (20/10/2026, relevés en rédigeant t248).

Trois défauts vus dans le code en écrivant les rôles du catalogue, corrigés ensemble :
  - C1 « Générer la musique » (Son & VFX) partait au PREMIER clic alors que c'est payant : son code vit dans le bloc
    SONVFX, que les maillons de queue ne touchent pas (couche traduite L4 par positions) ; la confirmation est donc
    posée dans /shared/dz-plafonds.js, avant l'envoi de POST /api/audio/music (pas dans ce maillon) ;
  - C2 le test d'un compte TELEGRAM publie un vrai message dans le canal (POST /api/channels/test →
    publish_telegram), dans Réglages › Comptes (`w`) comme dans les Espaces (`tester`) : confirmation pour Telegram
    seulement (X, YouTube et Instagram ne font que vérifier la connexion) ;
  - C3 les images générées sans `source` tombaient sous le plafond « bibliotheque » : `generateImage` prend un 5e
    paramètre `o` (source, absent = défaut, la Bibliothèque garde le sien), passé par le Studio (« studio » : Image
    gen, sticker, illustration News, et `/images/process` des variantes), les Chapitres (« chapitres ») et le
    Planificateur (« scheduler »). Le serveur ne retient qu'une catégorie connue (`_categorie_image` de routes.py).
    Le DUEL du Studio n'est PAS touché : il vit dans le bloc MONTAGE. Règle : un maillon de queue ne modifie jamais
    les blocs de couche (MONTAGE, SONVFX…) : chacun doit rester sa couche source, et les traductions L3/L4 s'y
    défont par positions.
AUCUN hook neuf (x.useState( reste à 731) ; v2.8.0 ×4, DzTracks 181 intouchés. `await window.__dzDialogue.confirmer(`
passe de 28 à 30 hors couche (épingle de test_dialogue_bundle).
Textes : clés dzT `reglages.comptes.telegram_*` (et `son.musique.*` de dz-plafonds.js), LITTÉRALES dans le livré, dans
frontend/shared/i18n/constats_confirmer.json.

Maillon de QUEUE, APRÈS dzschedconf (dont il sonde le marqueur) ; il garde un .js.bak_dzconstats le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzconstats` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzschedconf`. Lecture et écriture
en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne.
Banc : backend/tests/test_constats_catalogue.py.
Run : python scripts/patch_bundle_dzconstats.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzconstats")
TAG = "dzconstats"
MARKER = "/*__dzconstats*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("
NL = "\r\n"

SONDE_AMONT = [
    ("dzschedconf", "function __dzSchedCanaux(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 28),
]

_TG = ('if(!' + CONFIRMER + 'dzT("reglages.comptes.telegram_q"),{titre:dzT("reglages.comptes.telegram_titre"),'
       'ok:dzT("reglages.comptes.telegram_ok")}))return;')
_IMG = 'localStorage.getItem("dz_image_model")||""'

PAIRES = [
    # C2 : le test Telegram publie un vrai message
    ('async function w(k){u(p=>({...p,[k]:dzT("reglages.comptes.test_en_cours")}));',
     'async function w(k){if(k==="telegram"){' + _TG + '}u(p=>({...p,[k]:dzT("reglages.comptes.test_en_cours")}));'),
    ('function tester(c){dire(c.id,dzT("espaces.comptes.test_en_cours"));',
     'async function tester(c){if(c.plateforme==="telegram"){' + _TG + '}dire(c.id,dzT("espaces.comptes.test_en_cours"));'),
    # C3 : la source des images (catégorie de plafond)
    ('generateImage:(e,t=1,n="portrait_16_9",m)=>D.postJson("/images/generate",{prompt:e,n:t,size:n,model:m||' + _IMG + '})',
     'generateImage:(e,t=1,n="portrait_16_9",m,o)=>D.postJson("/images/generate",{prompt:e,n:t,size:n,model:m||' + _IMG
     + ',source:o' + MARKER + '})'),
    ('D.generateImage(prompt,1,"landscape_16_9",' + _IMG + ')',
     'D.generateImage(prompt,1,"landscape_16_9",' + _IMG + ',"studio")'),
    ('D.generateImage(eff,take,p.size||"portrait_16_9",p.model||"")',
     'D.generateImage(eff,take,p.size||"portrait_16_9",p.model||"","studio")'),
    ('D.generateImage(prm.trim(),1,"square_hd")',
     'D.generateImage(prm.trim(),1,"square_hd",void 0,"studio")'),
    ('setB(!0);setMsg(dzT("studio.imgproc.traitement"));D.postJson("/images/process",body)',
     'setB(!0);setMsg(dzT("studio.imgproc.traitement"));body.source=body.source||"studio";D.postJson("/images/process",body)'),
    ('return;setImgBusy(i);try{var d=await D.generateImage(sc.illustration_prompt.trim(),1,"portrait_16_9",' + _IMG + ')',
     'return;setImgBusy(i);try{var d=await D.generateImage(sc.illustration_prompt.trim(),1,"portrait_16_9",' + _IMG
     + ',"chapitres")'),
    ('continue;setImgBusy(i);try{var d=await D.generateImage(sc.illustration_prompt.trim(),1,"portrait_16_9",' + _IMG + ')',
     'continue;setImgBusy(i);try{var d=await D.generateImage(sc.illustration_prompt.trim(),1,"portrait_16_9",' + _IMG
     + ',"chapitres")'),
    ('p(dzT("scheduler.produire.creation_image"));const A=await D.generateImage(E,1,"portrait_16_9")',
     'p(dzT("scheduler.produire.creation_image"));const A=await D.generateImage(E,1,"portrait_16_9",void 0,"scheduler")'),
    ('p(dzT("scheduler.produire.image_depart"));const M=await D.generateImage(E,1,"portrait_16_9")',
     'p(dzT("scheduler.produire.image_depart"));const M=await D.generateImage(E,1,"portrait_16_9",void 0,"scheduler")'),
    ('D.generateImage(e.image_idea||e.title||"deep-sea key visual, 9:16",1,"portrait_16_9")',
     'D.generateImage(e.image_idea||e.title||"deep-sea key visual, 9:16",1,"portrait_16_9",void 0,"scheduler")'),
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
    """L'inverse exact (lu par avant_dzconstats dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzconstats "
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
