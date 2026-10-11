# -*- coding: utf-8 -*-
# scripts/patch_bundle_encartsia.py
"""Maillon de queue : les sélecteurs de modèle du bundle s'alignent sur le catalogue unique (t183, G1, plan
« Génération IA enrichie », 11/10/2026).

Décision de l'utilisateur (11/10/2026) : un modèle dont la clé manque reste TOUJOURS choisissable dans tout
sélecteur, avec son prix et la mention dzT("ia.cle.a_ajouter", {cle}) (« clé X à ajouter dans Réglages ») ; le
serveur refuse le tir en 503 AVANT toute dépense. Seule exception gardée de t182 : un modèle vectoriel (sortie
"svg") n'apparaît jamais dans un sélecteur raster.

Ce qu'il pose (ancres uniques, relevées le 11/10 sur le bundle de origin/main 5195eaee) :
  - E1 deux aides au niveau module, posées juste avant DzImgModelSel : `dzImgLbl(m)` (libellé · prix par image
    · mention de clé) et `dzImgOpts(d)` (les entrées RASTER de `tous` de /api/image-models — le catalogue unique —,
    rangées par voie : fal d'abord, puis votre clé OpenAI… ; repli sur `models` pour un serveur d'avant t182) ;
  - E2 DzImgModelSel (nœuds ImageGen / ImageEdit / Variations / Duel du Studio) lit `dzImgOpts` au lieu de `models` ;
  - E3 DzImageModel (le modèle d'image global : Library, Chapitres, News, Planificateur, Réglages) idem ;
  - E4 DzVideoModelSel (Quick, nœud Seedance) : la mention « · clé manquante » devient « · clé X à ajouter dans
    Réglages » (GEMINI_API_KEY pour Veo Google, FAL_KEY sinon) — le modèle y était déjà choisissable ;
  - E5 DzVoModelSel (Voice Over) : idem avec ELEVENLABS_API_KEY.
Le composant `re` (select custom du bundle) n'a pas de groupes : la voie se lit dans l'ORDRE des options et dans
le libellé (« (via fal) », « (OpenAI) ») ; les en-têtes de voie sont dans la liste de la pastille (dz-champ-ia).
Aucun useState ajouté (compte figé 731), aucun DzTracks.

Maillon de QUEUE, APRÈS dzguide (dont il sonde le marqueur) ; comme lui, il garde un .js.bak_encartsia le temps de
l'écriture puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_encartsia` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici : une seule source), appelé EN TÊTE de `avant_dzguide`.
Lecture et écriture en OCTETS.
Run : python scripts/patch_bundle_encartsia.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_encartsia")
TAG = "encartsia"
MARKER = "function dzImgOpts("
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzguide", 'g:"/guide/#cardforge"}', 1),
    ("i18nfix", 'dzT("scheduler.mode.assiste")', 1),
    ("dzbiblio", '"data-dz-biblio-barre":"1"', 1),
    ("avnoeuds", "function dzAvCompile(", 1),
    ("avatar", '{id:"avatarlive",', 1),
    ("imagegen", "function DzImgModelSel(", 1),
    ("dzglyph", "function __dzGlyphe(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

# E1 — les aides (une ligne, comme le code injecté par imagegen)
AIDES = (
    'function dzImgLbl(m){var u=Number(m.usd);'
    'return m.label+(u?" · $"+(u>=.1?u.toFixed(2):u.toFixed(3))+"/image":(m.usd===0?" · "+dzT("ia.prix.a_mesurer"):""))'
    '+(m.dispo===false&&m.cle?" · "+dzT("ia.cle.a_ajouter",{cle:m.cle}):"")}'
    'function dzImgOpts(d){var O=["fal","openai","gemini","elevenlabs","meshy","heygen","local"],'
    't=(d&&d.tous&&d.tous.length?d.tous:(d&&d.models)||[]).filter(function(m){return m.sortie!=="svg"});'
    'function rg(m){var k=O.indexOf(m.voie);return k<0?99:k}'
    'return t.map(function(m,i){return[m,i]}).sort(function(a,b){return rg(a[0])-rg(b[0])||a[1]-b[1]})'
    '.map(function(p){return{value:p[0].id,label:dzImgLbl(p[0])}})}'
)

PAIRES = [
    # E1 + E2 : DzImgModelSel
    ('function DzImgModelSel({value,onChange}){', AIDES + 'function DzImgModelSel({value,onChange}){'),
    ('.concat((mm.models||[]).map(function(m){return{value:m.id,label:m.label}}));'
     'return r.jsx(re,{value:value||"",onChange:onChange,options:opts})}',
     '.concat(dzImgOpts(mm));return r.jsx(re,{value:value||"",onChange:onChange,options:opts})}'),
    # E3 : DzImageModel (le modèle d'image global)
    ('if(d){setModels(d.models||[]);',
     'if(d){setModels(dzImgOpts(d).map(function(o){return{id:o.value,label:o.label}}));'),
    # E4 : DzVideoModelSel
    ('+"/s":"";return m2.label+px+(m2.available?"":dzT("reglages.modeles.cle_manquante"))}',
     '+"/s":"";return m2.label+px+(m2.available?"":" · "+dzT("ia.cle.a_ajouter",'
     '{cle:m2.provider==="google"?"GEMINI_API_KEY":"FAL_KEY"}))}'),
    # E5 : DzVoModelSel
    ('+"/1k":"";return m2.label+px+(m2.available?"":dzT("reglages.modeles.cle_manquante"))}',
     '+"/1k":"";return m2.label+px+(m2.available?"":" · "+dzT("ia.cle.a_ajouter",{cle:"ELEVENLABS_API_KEY"}))}'),
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
    if s2.count(MARKER) != MARKER_ATTENDU:
        raise SystemExit(f"[{TAG}] marqueur x{s2.count(MARKER)} apres application (attendu {MARKER_ATTENDU}).")
    sonder(s2)
    if not crlf_homogene(s2):
        raise SystemExit(f"[{TAG}] fins de ligne heterogenes apres application. Aborting.")
    ecrire(BUNDLE, s2, bom)
    BAK.unlink()
    print(f"[{TAG}] applique : {len(PAIRES)} paires, {len(s2) - len(s):+d} car ; {BAK.name} supprime.")


if __name__ == "__main__":
    main()
