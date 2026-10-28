# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzwhatsapp.py
"""Maillon de queue : WhatsApp par Kapso dans le bundle (t310 tâche 7, 27/10/2026, plan
docs/superpowers/plans/2026-10-27-t310-whatsapp-kapso.md, spec docs/superpowers/specs/2026-10-25-boite-a-outils-design.md
§5.3 et §6.1). WhatsApp est un canal de CONVERSATION d'espace, jamais une cible de publication (jusqu'à t328, voir
patch_bundle_dzdiffusion) : rien ne s'ajoute à la table des canaux `_t` ni à `Bu` du Planificateur. Ce maillon porte ses paires, toutes HORS de tout bloc de couche
__DZ_*_BEGIN__ (vérifié à l'écriture par `hors_couche`) :
  P1 Réglages › Clés d'API : `dzFuNeuves()` (les lignes neuves de t221, précédent DECART_API_KEY) reçoit la ligne de la
     clé plate partagée KAPSO_API_KEY, libellé dzT("reglages.cles.kapso"), aide dzT("reglages.cles.kapso_why") ; le
     serveur la range déjà dans la rubrique « keys » (settings_routes.RUBRIQUE_DE_CLE). Le MARKER /*dzwhatsapp*/ ouvre
     cette ligne ;
  P2 Planificateur › éditeur de post : le sélecteur `DzPostComptes` écarte les comptes `plateforme==="whatsapp"` de la
     liste qu'il range (dzPcCache) : un compte whatsapp n'est jamais proposé comme cible d'un post (le serveur le refuse
     aussi : comptes.verifier_cibles) ;
  P3 (a-c) Réglages › Espaces : `DzComptesEspace` ne propose pas whatsapp dans « Ajouter un compte » ; un compte
     whatsapp existant a sa propre rangée (« Vérifier », « Supprimer ») : ni « Identifiants » (aucun champ éditable) ni
     « Tester », la rangée d'origine restant entière derrière la condition (son « Tester » vit dans un remplacement de
     dzassistant, intouché) ; et une ligne en lecture seule dzT("espaces.comptes.whatsapp_assistant") : il se relie par
     l'assistant d'espace. P3d : son badge de disponibilité dit dzT("espaces.comptes.whatsapp_relie") (« relié »), jamais
     « prêt à publier ».
Clés dzT « reglages.cles.kapso » et « reglages.cles.kapso_why » : frontend/shared/i18n/menus.json (FR/EN, à côté de
reglages.cles.decart ; reglages.json est réécrit par scripts/i18n_l1_generer.py), assemblées par scripts/i18n_assembler.py.
Épingles intouchées : x.useState( 731, v2.8.0 x4, DzTracks 181, `await window.__dzDialogue.confirmer(` x30.

Maillon de QUEUE, APRÈS dzgardeclient (t309, dont il sonde le marqueur) ; il garde un .js.bak_dzwhatsapp le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzwhatsapp` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzgardeclient`. Lecture et écriture
en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne. DÉFAIRE le maillon AVANT de changer ses
paires (`defaire` relit les paires d'ici).
Banc : backend/tests/test_whatsapp_ecran.py.
Run : python scripts/patch_bundle_dzwhatsapp.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzwhatsapp")
TAG = "dzwhatsapp"
MARKER = "/*dzwhatsapp*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzgardeclient", "/*dzgardeclient*/", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]

LIGNE_KAPSO = '{k:"KAPSO_API_KEY",label:dzT("reglages.cles.kapso"),why:dzT("reglages.cles.kapso_why")}'

PAIRES = [
    # P1 : la ligne de la clé Kapso, en fin des lignes neuves de Réglages › Clés d'API (dzFuNeuves, sortie de dzreglages)
    ('health:"voiceover_enabled",texte:!0}]}function dzRgCle(',
     'health:"voiceover_enabled",texte:!0},' + MARKER + LIGNE_KAPSO + ']}function dzRgCle('),
    # P2 : DzPostComptes (sortie de dzespace) ne range jamais un compte whatsapp parmi les cibles proposées
    ('dzPcCache[esp]={liste:j.comptes||[],pl:j.plateformes||{}}',
     'dzPcCache[esp]={liste:(j.comptes||[]).filter(function(c){return c.plateforme!=="whatsapp"}),pl:j.plateformes||{}}'),
    # P3 (fix 1, 27/10/2026) : Réglages › Espaces (DzComptesEspace, sortie de dzespace) ne propose jamais whatsapp avec des
    # champs : ses champs publics sont posés par la liaison (le serveur refuse de les écrire), sa clé est plate.
    # P3a : « Ajouter un compte » ne propose pas whatsapp (il se relie par l'assistant d'espace)
    ('children:Object.keys(pl).map(function(k){return r.jsx("option",{value:k,children:pl[k].libelle},k)})',
     'children:Object.keys(pl).filter(function(k){return k!=="whatsapp"}).map(function(k){return r.jsx("option",{value:k,children:pl[k].libelle},k)})'),
    # P3b (revue, 27/10/2026) : un compte whatsapp a SA rangée de boutons, « Vérifier » et « Supprimer » seulement : ni
    # « Identifiants » (aucun champ éditable) ni « Tester » (/api/channels/test ne connaît pas whatsapp). La rangée
    # d'origine reste ENTIÈRE derrière la condition : le bouton « Tester » vit dans un remplacement de dzassistant qu'on ne
    # touche pas (son inverse le relit tel quel).
    ('r.jsxs("span",{style:{marginLeft:"auto",display:"flex",gap:6,flexWrap:"wrap"},children:[',
     'c.plateforme==="whatsapp"?r.jsxs("span",{"data-dz-compte-actions-whatsapp":c.id,style:{marginLeft:"auto",display:"flex",gap:6,flexWrap:"wrap"},children:['
     'window.__dzEspaceAssistant&&r.jsx("button",{type:"button","data-dz-compte-verifier":c.id,style:bt,disabled:window.__dzEspaceAssistant.enCours(c.id),'
     'title:dzT("espaces.assistant.verifier_aide"),onClick:function(){verifier(c)},children:dzT("espaces.comptes.verifier")}),'
     'st.suppr===c.id?r.jsx("button",{type:"button","data-dz-compte-suppr":c.id,style:Object.assign({},bt,{color:"var(--red)",borderColor:"var(--red)"}),'
     'disabled:st.busy,onClick:function(){maj({suppr:""});agir(fetch("/api/comptes/"+encodeURIComponent(c.id),{method:"DELETE"}).then(function(r2){'
     'if(!r2.ok)return r2.json().catch(function(){return{}}).then(function(j){throw new Error(j&&j.detail||"HTTP "+r2.status)})}))},'
     'children:dzT("espaces.comptes.confirmer")}):r.jsx("button",{type:"button",style:bt,onClick:function(){maj({suppr:c.id})},'
     'children:dzT("espaces.comptes.supprimer")})]}):'
     'r.jsxs("span",{style:{marginLeft:"auto",display:"flex",gap:6,flexWrap:"wrap"},children:['),
    # P3c : en plus, une ligne en lecture seule : relié par l'assistant d'espace
    ('c.historique&&r.jsx("div",{style:{fontSize:11,color:"var(--ink-muted)"},children:dzT("espaces.comptes.historique")}),',
     'c.historique&&r.jsx("div",{style:{fontSize:11,color:"var(--ink-muted)"},children:dzT("espaces.comptes.historique")}),'
     'c.plateforme==="whatsapp"&&r.jsx("div",{"data-dz-compte-whatsapp":c.id,style:{fontSize:11,color:"var(--ink-muted)"},'
     'children:dzT("espaces.comptes.whatsapp_assistant")}),'),
    # P3d (preuve à l'écran P2, 27/10/2026) : le badge de disponibilité d'un compte whatsapp ne dit jamais « prêt à
    # publier » (ce n'était pas une cible de publication jusqu'à t328, voir patch_bundle_dzdiffusion) : « relié » quand
    # il est disponible, le badge « incomplet » sinon.
    # Le badge d'origine (`_DISPO`, remplacement de dzassistant P4 que son banc défait tel quel) reste INTACT à l'octet : on
    # pose devant lui la branche whatsapp d'un ternaire dont il est la branche « sinon ».
    ('c.handle&&r.jsx("span",{"data-dz-brut":"1",style:{fontSize:11.5,color:"var(--ink-soft)"},children:c.handle}),',
     'c.handle&&r.jsx("span",{"data-dz-brut":"1",style:{fontSize:11.5,color:"var(--ink-soft)"},children:c.handle}),'
     'c.plateforme==="whatsapp"&&c.disponible?r.jsx("span",{"data-dz-compte-relie":c.id,style:{fontSize:10.5,'
     'color:"var(--green)"},children:dzT("espaces.comptes.whatsapp_relie")}):'),
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
    """L'inverse exact (lu par avant_dzwhatsapp dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzwhatsapp")
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
