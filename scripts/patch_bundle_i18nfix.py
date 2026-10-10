# -*- coding: utf-8 -*-
# scripts/patch_bundle_i18nfix.py
"""Maillon de queue : correctifs de traduction du Planificateur relevés le 10/10/2026 en capturant le guide v3 (t175).

Ce qu'il pose (ancres uniques, relevées le 10/10 sur le bundle de main 86333d74, rejouées sur ebe8cfa8 puis 9d96986f) :
  - F1 l'inspecteur d'un post : la pastille de mode (« auto-publish » / « assisted ») et la pastille d'état (« draft »,
    « scheduled »…) affichaient la VALEUR stockée ; elles passent par dzT (scheduler.mode.*, scheduler.etat.*). Un
    état inconnu du dictionnaire s'affiche tel quel (jamais la clé). Les valeurs stockées ne changent pas ;
  - F2 la liste des canaux du même inspecteur : « assisted » (X sans clé) par dzT ;
  - F3 l'aperçu final : l'URL du PNG porte `&lang=` + dzLang() — une <img> n'a pas l'en-tête Accept-Language du
    runtime, le serveur dessine « zones indicatives · N car. » dans la langue de l'interface ;
  - F4 « Générer un plan marketing » : l'exemple du Brief (placeholder, jamais envoyé) par dzT, et la langue des posts
    part de la langue de l'interface (FR en français, EN en anglais) au lieu d'« EN » toujours — elle reste
    modifiable dans le même sélecteur. Pas de useState ajouté : la valeur initiale seule change.
Les clés vivent dans frontend/shared/i18n/planif_news.json.

Maillon de QUEUE, APRÈS dzbiblio, avnoeuds (t168b) et avatar (dont il sonde les marqueurs) ; comme lui, il garde un .js.bak_i18nfix le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_i18nfix` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici : une seule source). Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_i18nfix.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_i18nfix")
TAG = "i18nfix"
MARKER = 'dzT("scheduler.mode.assiste")'

SONDE_AMONT = [
    ("dzbiblio", '"data-dz-biblio-barre":"1"', 1),
    ("avnoeuds", "function dzAvCompile(", 1),
    ("avatar", '{id:"avatarlive",', 1),
    ("dzgbar", '"data-dz-gbar":"1"', 1),
    ("dzsched", '"data-dz-debord":"1"', 1),
    ("dzglyph", "function __dzGlyphe(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

_ETATS = ("draft", "scheduled", "ready", "posting", "posted", "failed", "skipped")
_ETAT = "({" + ",".join(f'{e}:dzT("scheduler.etat.{e}")' for e in _ETATS) + "})[e.status]||e.status"
_EXEMPLE = ('placeholder:"e.g. Week around the $DEEPOTUS staking launch. Tease Monday, reveal Wednesday 18:00, recap '
            'Sunday. Tone: prophetic, playful.",')

PAIRES = [
    # F1 pastilles de l'inspecteur
    ('r.jsx(te,{children:e.mode==="auto"?"auto-publish":"assisted"})',
     'r.jsx(te,{children:e.mode==="auto"?dzT("scheduler.mode.auto"):dzT("scheduler.mode.assiste")})'),
    ('e.status==="draft"?"neutral":"cyan",dot:!0,children:e.status})',
     'e.status==="draft"?"neutral":"cyan",dot:!0,children:' + _ETAT + '})'),
    # F2 la liste des canaux (X sans clé)
    ('children:i?"auto":"assisted"})]},j.id)', 'children:i?"auto":dzT("scheduler.mode.assiste_canal")})]},j.id)'),
    # F3 l'aperçu final dans la langue de l'interface
    ('/preview.png?channel=${ch}&caption=', '/preview.png?channel=${ch}&lang=${dzLang()}&caption='),
    # F4 « Générer un plan marketing »
    (_EXEMPLE, 'placeholder:dzT("scheduler.plan.brief_exemple"),'),
    ('[v,g]=x.useState("EN")', '[v,g]=x.useState(()=>dzLang()==="fr"?"FR":"EN")'),
]


def lire(p):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def ecrire(p, text, bom):
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    p.write_bytes(out)


def sonder(s):
    for tag, jeton, n in SONDE_AMONT:
        c = s.count(jeton)
        if c != n:
            raise SystemExit(f"[sonde-amont] {tag} : x{c} (attendu {n}) - maillon amont absent ou rejoue. Aborting.")


def crlf_homogene(s):
    return s.count("\n") == s.count("\r\n")


def appliquer(s):
    for k, (a, b) in enumerate(PAIRES):
        c = s.count(a)
        if c != 1:
            raise SystemExit(f"[{TAG}] paire {k} : ancre x{c} (attendu 1) : {a[:80]!r}. Aborting.")
        s = s.replace(a, b, 1)
    return s


def main():
    args = sys.argv[1:]
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)
    if s.count(MARKER):
        raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application refusee.")
    sonder(s)
    if not crlf_homogene(s):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes dans le bundle d'entree. Aborting.")
    if "--check" in args:
        appliquer(s)
        print(f"[{TAG}] --check OK : {len(PAIRES)} paires uniques.")
        return
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
    s2 = appliquer(s)
    if s2.count(MARKER) != 1:
        raise SystemExit(f"[{TAG}] marqueur x{s2.count(MARKER)} apres application (attendu 1).")
    sonder(s2)
    if not crlf_homogene(s2):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes apres application. Aborting.")
    ecrire(BUNDLE, s2, bom)
    BAK.unlink()
    print(f"[{TAG}] applique : {len(PAIRES)} paires, {len(s2) - len(s):+d} car ; {BAK.name} supprime.")


if __name__ == "__main__":
    main()
