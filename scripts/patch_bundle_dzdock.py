# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzdock.py
"""Maillon de queue : JOB DOCK, « Réessayer » (19/10/2026, option (a) validée par l'utilisateur).

Le bouton « Réessayer » d'un job en échec n'avait AUCUN onClick dans le livré, pour tous les providers. Le serveur dit
maintenant comment relancer (`relance` de `_job_to_dict`, backend/app/api/routes.py `_relance_de`) et ce maillon branche
le bouton :
  - D0 : la ligne du Dock reçoit `relance`, `aspect` et `titre` du job ;
  - D1 : le bouton n'existe que si `relance` est posé (masqué sinon) ; libellé « Réessayer » (direct), « Réessayer dans
    Quick » (quick) ou « Réessayer dans le Studio » (studio), bulle qui dit ce qui se passe ; clic → `__dzRelancer` ;
  - D2 : `__dzRelancer(job, ev)`, posé devant `__dzReopenStudio` :
      * quick  → `__dzReopenQuick` (Quick prérempli : rien ne part avant « Générer », donc estimation et plafond comme
        un lancement normal) ;
      * studio → `__dzReopenStudio` (le graphe rouvert : rien ne part avant le rendu) ;
      * direct → relit GET /api/jobs/{id}/graph, prend LE nœud MotionCode relié à une entrée `in` (comme la compilation
        `dzMotionCodeRendu` de dzmotion M10) et rappelle POST /api/motion/code/rendre avec la même page, la même cadence,
        la même durée, le format et le titre du job (local et gratuit : aucun plafond en jeu). Bouton grisé pendant
        l'envoi ; sans nœud unique ou sans page : repli sur le Studio ; échec du serveur : son message ;
  - D3 : la ligne du Dock fait ~330 px : avec le bouton, la colonne d'actions (auto) prenait 210 px et le badge
    « échoué » de la colonne 2 passait SOUS le bouton. Quand le bouton est là, les actions passent à la ligne dans
    112 px (le bouton au-dessus des icônes) : le badge garde sa place (mesuré en FR et en EN sur le backend de preuve).
AUCUN hook neuf (x.useState( reste à 731, dzMoUS 3) ; dz-action-reessayer reste ×1 ; v2.8.0 ×4, DzTracks 181 intouchés.
Le remplacement G1 `m",icon:"dz-action-reessayer",childre` (scripts/dzglyph_paires.json) reste CONTIGU : `title` et
`onClick` passent AVANT `variant`, sinon le rejeu de dzglyph (test_icones_g1 3.5) ne se défait plus.
Textes : clés dzT `coque.file.reessayer_*`, toutes LITTÉRALES dans le livré, dans frontend/shared/i18n/relance.json
(coque.json est ÉCRIT par scripts/i18n_l1_generer.py : on n'y ajoute rien à la main).

Maillon de QUEUE, APRÈS dzmotion (dont il sonde le marqueur) ; il garde un .js.bak_dzdock le temps de l'écriture puis
le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzdock` dans backend/tests/_i18n_l1_aide.py
(lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzmotion`. Lecture et écriture en OCTETS.
Banc : backend/tests/test_jobdock_reessayer.py.
Run : python scripts/patch_bundle_dzdock.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzdock")
TAG = "dzdock"
MARKER = "function __dzRelancer("
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzmotion", "function DzMotionDirection(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("reessayer", "dz-action-reessayer", 1),
]

RELANCER = (
    'function __dzRelancer(j,ev){var b=ev&&ev.currentTarget||null;'
    'try{ev&&ev.stopPropagation&&ev.stopPropagation()}catch(e_){}'
    'if(j.relance==="quick")return __dzReopenQuick(j.id);'
    'if(j.relance==="studio")return __dzReopenStudio(j.id);'
    'if(j.relance!=="direct")return;'
    'if(b)b.disabled=!0;'
    'return fetch("/api/jobs/"+encodeURIComponent(j.id)+"/graph").then(function(r){return r.ok?r.json():null})'
    '.then(function(g){var mc=null,n=0,vus={};'
    'if(g&&g.nodes&&g.edges)g.nodes.forEach(function(t){var m=Wt(g,t.id,"in");'
    'if(m&&m.type==="MotionCode"&&!vus[m.id]){vus[m.id]=1;mc=m;n++}});'
    'var P=mc?dzMoProps(mc):{};'
    'if(n!==1||!P.pageId){if(b)b.disabled=!1;return __dzReopenStudio(j.id)}'
    'return fetch("/api/motion/code/rendre",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({page_id:String(P.pageId),aspect:j.aspect||void 0,fps:Number(P.fps)||30,'
    'duree_s:Number(P.durationS)||8,title:j.titre||void 0,source_graph:g})})'
    '.then(function(r){return r.json().catch(function(){return null}).then(function(d){'
    'if(!r.ok)throw new Error(d&&typeof d.detail==="string"?d.detail:"HTTP "+r.status);'
    '__dzToast(dzT("coque.file.reessayer_lance",{titre:j.titre||j.id}))})})})'
    '.catch(function(e){if(b)b.disabled=!1;__dzToast(dzT("coque.file.reessayer_echec",{e:e&&e.message||"?"}))})}'
)

PAIRES = [
    ('error:c.error,img:c.image_',                                                                              # D0
     'error:c.error,relance:c.relance||null,aspect:c.aspect_ratio||"",titre:c.title||"",img:c.image_'),
    ('u&&r.jsx(K,{variant:"outline",size:"sm",icon:"dz-action-reessayer",children:dzT("commun.action.reessayer")})',  # D1
     'u&&e.relance&&r.jsx(K,{title:e.relance==="quick"?dzT("coque.file.reessayer_quick_aide"):e.relance==="studio"?'
     'dzT("coque.file.reessayer_studio_aide"):dzT("coque.file.reessayer_direct_aide"),'
     'onClick:function(ev){__dzRelancer(e,ev)},variant:"outline",size:"sm",icon:"dz-action-reessayer",'
     'children:e.relance==="quick"?dzT("coque.file.reessayer_quick"):e.relance==="studio"?'
     'dzT("coque.file.reessayer_studio"):dzT("commun.action.reessayer")})'),
    ('function __dzReopenStudio(id){',                                                                          # D2
     RELANCER + 'function __dzReopenStudio(id){'),
    ('display:"flex",gap:4,position:"relative",gridColumn:3,gridRow:2,justifySelf:"end"}',                      # D3
     'display:"flex",gap:4,position:"relative",gridColumn:3,gridRow:2,justifySelf:"end",flexWrap:"wrap",'
     'justifyContent:"flex-end",rowGap:6,maxWidth:u&&e.relance?112:void 0}'),
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
    """L'inverse exact (lu par avant_dzdock dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzdock "
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
            or neuf.count("dz-action-reessayer") != 1 or neuf.count('m",icon:"dz-action-reessayer",childre') != 1):
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
