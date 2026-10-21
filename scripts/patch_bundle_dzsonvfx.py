# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzsonvfx.py
"""Maillon de queue : SON & VFX en sous-menus à la Game Assets (t268, 21/10/2026, plan
docs/superpowers/plans/2026-10-21-optimisation-menus-son-vfx.md).

L'écran doublait sa navigation : trois onglets texte en haut (Audio / VFX particules / Post-traitement) et un rail de
six cartes de générateurs à gauche, l'onglet « Audio » mêlant Musique, SFX et Voix off. Ce maillon pose `DzSonVfxHub`
devant l'écran :
  - H0 : `DzSonVfxHub` (et sa feuille `<style id=__dzSvHub>`, injectée au premier rendu) devant `const Te="/api";` :
    une barre `dzCatBar` de SIX sous-onglets `dzCatTab` (la barre de Game Assets, patch_bundle_dzdesign, même
    feuille __dzCatBar), une teinte et une icône Deepotus Glyph par famille, dans l'ordre de `SVM_GENS` (Musique,
    SFX, Voix off, VFX particules, VFX IA, Post-traitement) ; un en-tête de page (icône, nom, phrase, pastille de
    coût, lus dans `SVM_GENS` : aucun texte neuf hors l'aria-label de la barre) ; puis l'écran d'origine `DzSonVfx`
    dans un corps encadré. La feuille masque le titre et les onglets texte de l'écran et la liste des générateurs du
    rail : le rail ne garde que son panneau de contexte (voix, familles de sons, de textures, gestes VFX IA…) ;
  - H1 : le dispatch de la coque rend `DzSonVfxHub` au lieu de `DzSonVfx`.
Le bloc SONVFX (couche traduite L4 par positions) n'est PAS touché : le hub pilote la sélection interne de `DzSonVfx`
en cliquant le bouton (masqué) du générateur choisi, et suit les sauts internes (« Ouvrir les jingles » → SFX) par un
MutationObserver sur `data-sel`. Sous-onglet ouvert : `window.__dzSvSub` (gardé d'une visite à l'autre) ou l'événement
`deepotus:sonvfx-subtab` (detail = id ou {id}). Hooks lus par alias DANS la fonction (x.useState( reste à 731).
Textes : clé dzT `sonvfx.hub.barre`, LITTÉRALE dans le livré, dans frontend/shared/i18n/sonvfx_hub.json.

Maillon de QUEUE, APRÈS dzconstats (dont il sonde le marqueur) ; il garde un .js.bak_dzsonvfx le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzsonvfx` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzconstats`. Lecture et écriture
en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne.
Banc : backend/tests/test_sonvfx_hub.py.
Run : python scripts/patch_bundle_dzsonvfx.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzsonvfx")
TAG = "dzsonvfx"
MARKER = "function DzSonVfxHub("
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzconstats", "/*__dzconstats*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

# Teintes des six familles (oklch .72/.13 comme les --cat-* de Game Assets), portées par .dzsvh : l'écran n'a pas
# besoin de jetons globaux. Icônes : Deepotus Glyph existants (DESIGN.md §15).
CSS = (
    ".dzsvh{position:absolute;inset:0;display:flex;flex-direction:column;min-height:0;"
    "background:var(--bg-base,#0a0a0c);"
    "--sv-musique:oklch(.72 .13 145);--sv-sfx:oklch(.72 .13 200);--sv-voix:oklch(.76 .12 80);"
    "--sv-particules:oklch(.72 .13 25);--sv-vfxia:oklch(.72 .13 300);--sv-post:oklch(.72 .13 340)}"
    ".dzsvh .dzsvh-barre{flex:0 0 auto}"
    ".dzsvh-tete{flex:0 0 auto;display:flex;align-items:center;gap:12px;margin:12px 24px 0;padding:10px 16px;"
    "border:1px solid var(--stroke);border-left:3px solid var(--cat);border-radius:10px;background:var(--bg-panel)}"
    ".dzsvh-ico{display:flex;color:var(--cat)}"
    ".dzsvh-txt{flex:1;min-width:0}"
    ".dzsvh-nom{font-size:15px;font-weight:600;color:var(--ink-strong,#f2efe9)}"
    ".dzsvh-desc{font-size:12px;color:var(--ink-soft);margin-top:2px}"
    ".dzsvh-prix{flex:none;font-family:var(--f-mono,monospace);font-size:11px;padding:4px 10px;border-radius:999px;"
    "border:1px solid var(--cat);color:var(--cat);white-space:nowrap}"
    ".dzsvh-corps{position:relative;flex:1;min-height:0;margin:12px 24px 16px;border:1px solid var(--stroke);"
    "border-radius:10px;overflow:hidden}"
    ".dzsvh .svm-rail>.svm-label:first-child,.dzsvh .svm-genlist,.dzsvh .svm-tabs,.dzsvh .svm-title{display:none}"
    ".dzsvh .svm-rail>.svm-genlist+*{margin-top:0!important}"
    ".dzsvh .svm-titlebar{height:36px}"
    ".dzsvh .svm-label{color:var(--cat)}"
    ".dzsvh .svm-content .svm-card{border-top:2px solid var(--cat)}"
)

HUB = (
    'var __dzSvHue={music:"var(--sv-musique)",sfx:"var(--sv-sfx)",voiceover:"var(--sv-voix)",'
    'vfx:"var(--sv-particules)",vfxia:"var(--sv-vfxia)",post:"var(--sv-post)"},'
    '__dzSvIco={music:"dz-cat-audio",sfx:"dz-edit-ripple",voiceover:"dz-media-isoler-voix",vfx:"dz-edit-energie",'
    'vfxia:"dz-etat-ia",post:"dz-edit-effet"};'
    'function __dzSvHubCss(){try{if(document.getElementById("__dzSvHub"))return;'
    'var st=document.createElement("style");st.id="__dzSvHub";st.textContent="' + CSS + '";'
    'document.head.appendChild(st)}catch(e){}}'
    'function DzSonVfxHub(p){var US=x.useState,UE=x.useEffect,UR=x.useRef;__dzSvHubCss();'
    'var G=typeof SVM_GENS!=="undefined"?SVM_GENS:[],ids=G.map(function(g){return g.id});'
    'var s=US(function(){var w=window.__dzSvSub;return ids.indexOf(w)>=0?w:ids[0]||"music"}),sub=s[0],setSub=s[1];'
    'var box=UR(null);'
    'function aller(id){if(ids.indexOf(id)<0)return;try{window.__dzSvSub=id}catch(e){}setSub(id)}'
    # le hub mène : le bouton (masqué) du générateur choisi est cliqué s'il n'est pas déjà sélectionné
    'UE(function(){var el=box.current;if(!el)return;'
    'var b=el.querySelectorAll(".svm-genlist .svm-gen")[ids.indexOf(sub)];'
    'if(b&&!b.hasAttribute("data-sel"))b.click()},[sub]);'
    # l'écran mène (saut interne) : la sélection du rail suit, puis l'événement d'un autre écran
    'UE(function(){var el=box.current;if(!el)return;'
    'var mo=typeof MutationObserver==="function"?new MutationObserver(function(){'
    'var bs=el.querySelectorAll(".svm-genlist .svm-gen");for(var i=0;i<bs.length;i++)'
    'if(bs[i].hasAttribute("data-sel")){if(ids[i])aller(ids[i]);return}}):null;'
    'mo&&mo.observe(el,{subtree:!0,attributes:!0,attributeFilter:["data-sel"]});'
    'function ev(e){var d=e&&e.detail;aller(d&&typeof d==="object"?d.id:d)}'
    'window.addEventListener("deepotus:sonvfx-subtab",ev);'
    'return function(){mo&&mo.disconnect();window.removeEventListener("deepotus:sonvfx-subtab",ev)}},[]);'
    'var g=G[ids.indexOf(sub)]||{};'
    'function tb(q){var on=q.id===sub;return r.jsxs("button",{type:"button",className:"dzCatTab"+(on?" on":""),'
    '"aria-pressed":on?"true":"false","data-sv-sub":q.id,onClick:function(){aller(q.id)},'
    'style:{"--cat":__dzSvHue[q.id]||"var(--accent)"},children:['
    'r.jsx("span",{className:"dzCatFill","aria-hidden":"true"}),'
    'r.jsx("span",{className:"dzCatIco","aria-hidden":"true",children:__dzGl(__dzSvIco[q.id]||"dz-cat-audio",17)}),'
    'r.jsx("span",{className:"dzCatLbl",children:q.name}),'
    'r.jsx("span",{className:"dzCatEdge","aria-hidden":"true"})]},q.id)}'
    'return r.jsxs("div",{className:"dzsvh","data-sv-sub":sub,style:{"--cat":__dzSvHue[sub]||"var(--accent)"},'
    # la feuille __dzCatBar compte les colonnes de Game Assets : la barre porte les siennes
    'children:[r.jsx("div",{className:"dzCatBar dzsvh-barre",role:"group","aria-label":dzT("sonvfx.hub.barre"),'
    'style:{gridTemplateColumns:"repeat("+(G.length||1)+",1fr)"},children:G.map(tb)},"barre"),'
    'r.jsxs("div",{className:"dzsvh-tete",children:['
    'r.jsx("span",{className:"dzsvh-ico","aria-hidden":"true",children:__dzGl(__dzSvIco[sub]||"dz-cat-audio",20)}),'
    'r.jsxs("div",{className:"dzsvh-txt",children:[r.jsx("div",{className:"dzsvh-nom",children:g.name}),'
    'r.jsx("div",{className:"dzsvh-desc",children:g.desc})]}),'
    'r.jsx("span",{className:"dzsvh-prix",children:g.price})]},"tete"),'
    'r.jsx("div",{className:"dzsvh-corps",ref:box,children:r.jsx(DzSonVfx,{variant:p.variant,go:p.go})},"corps")]})}'
    '/*__dzsonvfx*/'
)

PAIRES = [
    ('const Te="/api";',                                                                                         # H0
     HUB + 'const Te="/api";'),
    ('s==="sonvfx"&&r.jsx(DzSonVfx,{variant:e,go:a})',                                                           # H1
     's==="sonvfx"&&r.jsx(DzSonVfxHub,{variant:e,go:a})'),
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
    """L'inverse exact (lu par avant_dzsonvfx dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzsonvfx "
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
            or neuf.count(CONFIRMER) != 30):
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
