# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzlogo.py
"""Maillon de queue : le LOGO DE LA COQUE (16/10/2026).

Défaut relevé sur 30695018 et reproduit au clic sur un backend de preuve : `Ch` (la marque en haut de la colonne de
menu, « DEEPOTUS VIDEO · v2.8.0 ») lisait `D.brandLogoUrl()` = `/api/branding/logo`, le logo du kit ACTIF de Réglages ›
Branding, toujours à la MÊME URL. Activer Rippled puis recharger mettait le logo Rippled en haut ; revenir au kit
Deepotus rendait le nom « DEEPOTUS » mais l'image restait celle de Rippled (même URL : jamais relue). L'encart du bas
(slogans + sélecteur d'espace) montrait au contraire un glyphe fixe quelle que soit la marque.

Règle de l'utilisateur (16/10) : le logo du HAUT ne change jamais, quel que soit le kit ou l'espace ; celui du BAS suit
la marque active. Ce qu'il pose (ancres uniques, relevées le 16/10 sur 30695018) :
  - L0 : `dzLogoMarqueSrc(cache, kit, v)` et `DzLogoMarque({kit, repli})`, posés devant `Ch`. L'URL est
    `/api/espaces/<espace actif>/logo?k=<kit de Branding>&e=<kit de l'espace>&v=<version>` : elle change dès que
    l'espace, son kit, le kit de Branding ou la version (deepotus:brand-refresh, logo re-téléversé) changent — deux
    marques n'ont donc jamais la même URL. Le composant s'abonne aux espaces (dzEspAbonnes, maillon dzespace) et
    retombe sur le glyphe si l'image échoue ;
  - L1 : `Ch` affiche le logo LIVRÉ `/deepotus-logo.png` (attribut data-dz-logo-app) ;
  - L2 : l'encart du bas rend `DzLogoMarque` avec le kit de Branding (`i.kit_id`) ; le glyphe dz-marque-poulpe reste,
    en repli : son remplacement G1 (scripts/dzglyph_paires.json) garde son compte.
Côté serveur : GET /api/espaces/{id}/logo (routes.py) = le logo de espaces.kit_de_l_espace(id).
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 », aucun texte visible neuf.

Maillon de QUEUE, APRÈS dzreglages (dont il sonde le marqueur) ; il garde un .js.bak_dzlogo le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzlogo` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzreglages`. Lecture et écriture
en OCTETS. Banc : backend/tests/test_logo_coque.py.
Run : python scripts/patch_bundle_dzlogo.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzlogo")
TAG = "dzlogo"
MARKER = "function DzLogoMarque("
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzreglages", "function dzOuvrirReglages(", 1),
    ("dzquick", "class DzQuickGarde ", 1),
    ("dzespace", "function DzEspaceSel(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

# L0 — l'URL du logo de la marque active et l'encart qui la montre (une ligne : minifié à la main)
AIDES = (
    'function dzLogoMarqueSrc(c,k,v){var e=c&&c.actif;if(!e)return"";var es=(c.espaces||[]).filter(function(s){'
    'return s.id===e})[0]||{};return"/api/espaces/"+encodeURIComponent(e)+"/logo?k="+encodeURIComponent(k||"")+"&e="'
    '+encodeURIComponent(es.kit_id||"")+"&v="+(v||0)}'
    'function DzLogoMarque({kit:k,repli:rp}){const[st,maj]=x.useReducer(function(o,n){return Object.assign({},o,n)},'
    '{v:0,ko:""});x.useEffect(function(){var f=function(){maj({})},g=function(){maj({v:Date.now()})};'
    'dzEspAbonnes.push(f);window.addEventListener("deepotus:brand-refresh",g);dzEspCache||dzEspCharger().catch('
    'function(){});return function(){dzEspAbonnes=dzEspAbonnes.filter(function(h){return h!==f});'
    'window.removeEventListener("deepotus:brand-refresh",g)}},[]);var src=dzLogoMarqueSrc(dzEspCache,k,st.v);'
    'if(!src||st.ko===src)return rp;return r.jsx("img",{src:src,alt:"","data-dz-logo-marque":"1",width:18,height:18,'
    'onError:function(){maj({ko:src})},style:{width:18,height:18,objectFit:"contain",borderRadius:"50%",'
    'flexShrink:0}})}'
)

CH = "function Ch({compact:e,size:t=16}){"
GLYPHE = 'r.jsx(X,{name:"dz-marque-poulpe",size:14,style:{color:"var(--cyan)"}})'
SLOGAN = 'r.jsx("span",{style:{fontSize:11.5,color:"var(--ink-strong)"},children:i.tagline_1})'

PAIRES = [
    (CH, AIDES + CH),                                                                                       # L0
    ('r.jsx("img",{src:D.brandLogoUrl(),alt:n.app_name,width:o,height:o,',                                  # L1
     'r.jsx("img",{src:"/deepotus-logo.png",alt:n.app_name,"data-dz-logo-app":"1",width:o,height:o,'),
    (GLYPHE + "," + SLOGAN,                                                                                 # L2
     "r.jsx(DzLogoMarque,{kit:i.kit_id,repli:" + GLYPHE + "})," + SLOGAN),
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
    """L'inverse exact (lu par avant_dzlogo dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
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
    if neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181:
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
