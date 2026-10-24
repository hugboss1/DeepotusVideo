# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzagentplan.py
"""Maillon de queue : le mode « Agent Campagnes » du dialogue « Generate a marketing plan » du Planificateur
(t285 T9, 24/10/2026, spec docs/superpowers/specs/2026-10-23-agent-interne-design.md §6).

Quatre paires, toutes dans le dialogue Um (clé scheduler.plan.titre_generer), HORS des blocs de couche, et qui
n'AJOUTENT que du texte (P2, P4 : l'ancre d'origine reste entière dans son remplacement ; P1 glisse le crochet entre
l'en-tête de la fonction et son premier `const` ; P3 glisse le choix du composant et ses propriétés après `"div"`) :
  P1 les aides de frontend/patches/agent-plan.js, APLATIES en une ligne, devant `function Um({…`, et le crochet du
     mode (`var __dzAP=__dzAgentPlanMode();`, « rapide » par défaut) en tête du corps du dialogue ;
  P2 l'en-tête : le sélecteur Rapide / Agent Campagnes (DzAgentPlanBascule) devant les onglets Générer / Importer,
     masqués en mode Agent (passer en Agent remet l'onglet « generate » : le titre reste titre_generer ;
     un plan Rapide généré et non ajouté n'est PAS effacé : on le retrouve en revenant en Rapide) ;
  P3 le corps : en mode Agent, le panneau DzAgentPlan (espace, brief, période, document, puis DzCampagnes.monter) ;
     en mode Rapide, le corps d'origine, inchangé. L'ancre commence APRÈS `r.jsxs("` : le remplacement G1 de dzglyph
     (`…onClick:e})]}),r.jsxs("`, scripts/dzglyph_paires.json) reste entier ; le type devient
     `"div"&&__dzAP[0]==="agent"?DzAgentPlan:"div"` et les propriétés du panneau n'arrivent qu'en mode Agent ;
  P4 le pied (Générer, Ajouter au calendrier) : masqué en mode Agent.
Les brouillons au calendrier : l'évènement que le Planificateur écoute déjà est « deepotus:schedule-reload » (il
appelle reloadPosts) ; le panneau l'émet à « dz-campagnes-brouillons » et au démontage d'une conversation ouverte.
AUCUN `x.useState(` ajouté (hooks par alias : 731 inchangé) ; v2.8.0 ×4, DzTracks 181, confirmations ×30 intouchés.
Textes : clés dzT `campagnes.plan.*` dans frontend/shared/i18n/campagnes.json (FR/EN).

Maillon de QUEUE, APRÈS dzrecette (dont il sonde le marqueur) ; il garde un .js.bak_dzagentplan le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzagentplan` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzrecette`. Lecture et écriture en
OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer sa
source (`defaire` relit la source).
Banc : backend/tests/test_agent_planificateur.py.
Run : python scripts/patch_bundle_dzagentplan.py [--check]
"""
import pathlib
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzagentplan")
SOURCE = RACINE / "frontend" / "patches" / "agent-plan.js"
TAG = "dzagentplan"
MARKER = "/*__dzagentplan*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzrecette", "/*__dzrecette*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]


def aplatir(src: str) -> str:
    """Même règle que patch_bundle_dzrecette.aplatir : commentaires « /* » de lignes entières retirés, lignes rognées,
    jointes par une espace."""
    out, dans = [], False
    for ligne in src.splitlines():
        t = ligne.strip()
        if dans:
            dans = not t.endswith("*/")
            continue
        if t.startswith("/*"):
            dans = not t.endswith("*/")
            continue
        if t.startswith(("//", "(", "[")):
            raise SystemExit(f"[{TAG}] ligne interdite dans la source : {t[:60]!r}")
        if t:
            out.append(t)
    return " ".join(out)


AIDES = aplatir(SOURCE.read_bytes().decode("utf-8"))

_UM = 'function Um({onClose:e,onMaterialized:t,initialTab:n="generate"}){'
_ONGLETS = ('r.jsx("div",{style:{display:"flex",gap:2,padding:3,background:"var(--bg-base)",borderRadius:"var(--r-sm)",'
            'border:"1px solid var(--stroke)"},children:[["generate",dzT("scheduler.plan.generer")]')
_CORPS0 = 'div",{'
_CORPS = ('className:"scroll",style:{flex:1,overflowY:"auto",padding:18,display:"flex",flexDirection:"column",'
          'gap:14},children:[i==="generate"&&r.jsx(O,{label:dzT("scheduler.plan.brief")')
_PIED = ('r.jsxs("div",{style:{padding:"12px 18px",borderTop:"1px solid var(--stroke)",display:"flex",alignItems:"center",'
         'gap:10},children:[r.jsxs("span",{style:{fontSize:10.5,color:"var(--ink-muted)",flex:1},children:[k==="auto"?'
         'dzT("scheduler.plan.arrivent_auto")')
PAIRES = [
    # P1 : les aides, et le crochet du mode en tête du dialogue
    (_UM + "const o=bt(),", AIDES + _UM + "var __dzAP=__dzAgentPlanMode();const o=bt(),"),
    # P2 : le sélecteur dans l'en-tête ; les onglets Générer / Importer masqués en mode Agent
    (_ONGLETS, 'r.jsx(DzAgentPlanBascule,{mode:__dzAP[0],choisir:function(v){v==="agent"&&s("generate");'
               '__dzAP[1](v)}}),__dzAP[0]==="agent"?null:' + _ONGLETS),
    # P3 : le corps : le panneau de l'agent, ou le corps d'origine
    (_CORPS0 + _CORPS, 'div"&&__dzAP[0]==="agent"?DzAgentPlan:"div",{...(__dzAP[0]==="agent"?{brief:a,setBrief:l,jours:d,'
                       'setJours:u,debut:p,setDebut:h,fermer:e}:{}),' + _CORPS),
    # P4 : le pied d'origine, masqué en mode Agent
    (_PIED, '__dzAP[0]==="agent"?null:' + _PIED),
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
    """L'inverse exact (lu par avant_dzagentplan dans _i18n_l1_aide)."""
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


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        if partiel(s):
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzagentplan")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    if "\n" in AIDES or MARKER not in AIDES or "x.useState(" in AIDES:
        raise SystemExit(f"[{TAG}] source mal aplatie (fin de ligne, marqueur absent ou x.useState( direct)")
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
        shutil.copyfile(BAK, BUNDLE)
        raise
    finally:
        BAK.unlink(missing_ok=True)
    print(f"[{TAG}] appliqué")


if __name__ == "__main__":
    main()
