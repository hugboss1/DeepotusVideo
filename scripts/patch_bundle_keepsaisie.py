# -*- coding: utf-8 -*-
# scripts/patch_bundle_keepsaisie.py
"""Patcher assert-gardé : Quick, News et Épisodes gardent leur saisie à la navigation (t129, étape 4 de la spec
docs/superpowers/specs/2026-08-06-preservation-etat-ecrans-design.md).

BASELINE : bundle versionné de main après t127 (90d93b6f) — le bundle commis fait foi (la plupart des maillons n'ont
pas de .bak sur cette machine). Backup dédié .js.bak_keepsaisie au premier passage, à SUPPRIMER après application (aucun
.bak_* en trop : guard_downstream et repatch_all prennent tout .bak_* pour un maillon). Au prochain bump de version :
archiver .bak_version HORS de frontend/dist/assets puis relancer patch_bundle_version.py seul.

Même conservateur que l'étape 1 (`__dzKeep`, patch_bundle_keepstate.py) : EN SESSION, en mémoire, aucun cycle de vie
touché — les écrans se démontent toujours (sondages, raccourcis, audio s'arrêtent), seul le CONTENU revient. Clés
`<écran>.<état>`. Un helper `__dzK(clé, défaut)` est posé à côté du magasin.

  * Quick : la saisie entière est déjà une RECETTE (`dzQuickRecipe` / `dzQuickApply`, celle des presets et de
    « Rejouer ») — rangée dans `__dzKeep["quick.recette"]` au DÉMONTAGE (ref tenue à jour à chaque rendu), rejouée au
    montage SEULEMENT si aucune recette extérieure n'arrive (`window.__dzQuickRecipe`, « Rejouer » de la Bibliothèque,
    prime — précédence exigée par la spec, étape 1).
  * News : articles cochés, requête, tri, voix, longueur, lecture des articles, script généré.
  * Épisodes : le MODE de Chapitres (flux d'origine / Atelier) et, dans le flux d'origine, titre, script, langue,
    voix, résultat, étape, scènes, méthode et style de découpe, compteurs, job d'épisode (son suivi reprend : l'effet
    de sondage repart sur un epJob non terminé), épisode enregistré (id, signature — la liste déroulante se rouvre
    fermée). PIÈGE neutralisé : au montage, la liste des voix remettait la voix par défaut par-dessus la voix
    conservée (`setVid(g.voice_id)`) — elle ne remplit plus qu'une voix VIDE.

Lecture et écriture en OCTETS (le mode texte aplatit les CRLF — mémoire du 07/09/2026).

Run : python scripts/patch_bundle_keepsaisie.py [--check] [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_keepsaisie")
TAG = "keepsaisie"

MARKER = "function __dzK("
MARKER_ATTENDU = 1

HELPER = ('function __dzK(k,d){return Object.prototype.hasOwnProperty.call(__dzKeep,k)?__dzKeep[k]:d}')


def _k(cle, defaut):
    return f'__dzK("{cle}",{defaut})'


PATCHES = [
    # le helper, à côté du magasin (étape 1)
    ("K0-helper", "var __dzG=null,__dzKeep={};", "var __dzG=null,__dzKeep={};" + HELPER, 1),
    # ── Quick : la recette rangée au démontage, rejouée au montage après une recette extérieure ──
    ("Q1-rangement", "dzApplyRef.current=dzQuickApply;",
     "dzApplyRef.current=dzQuickApply;var dzKeepQ=x.useRef(null);dzKeepQ.current=dzQuickRecipe;"
     "x.useEffect(function(){return function(){try{__dzKeep[\"quick.recette\"]=dzKeepQ.current()}catch(_e){}}},[]);", 1),
    ("Q2-reprise", "if(r0)dzApplyRef.current(r0);",
     "if(r0)dzApplyRef.current(r0);else if(__dzKeep[\"quick.recette\"])dzApplyRef.current(__dzKeep[\"quick.recette\"]);", 1),
    # ── News ──
    ("N1-sel", "const[sel,setSel]=x.useState(new Set);",
     "const[sel,setSel]=x.useState(function(){return " + _k("news.sel", "new Set") + "});", 1),
    ("N2-q-tri", 'const[q,setQ]=x.useState("");const[sort,setSort]=x.useState("relevance");',
     "const[q,setQ]=x.useState(" + _k("news.q", '""') + ");const[sort,setSort]=x.useState(" + _k("news.sort", '"relevance"') + ");", 1),
    ("N3-voix-longueur", 'const[voice,setVoice]=x.useState("auto");const[maxw,setMaxw]=x.useState(80);const[readArt,setReadArt]=x.useState(!0);',
     "const[voice,setVoice]=x.useState(" + _k("news.voice", '"auto"') + ");const[maxw,setMaxw]=x.useState(" + _k("news.maxw", "80")
     + ");const[readArt,setReadArt]=x.useState(" + _k("news.readArt", "!0") + ");", 1),
    ("N4-script-miroir", "const[script,setScript]=x.useState(null);",
     "const[script,setScript]=x.useState(" + _k("news.script", "null") + ");Object.assign(__dzKeep,{\"news.sel\":sel,\"news.q\":q,"
     "\"news.sort\":sort,\"news.voice\":voice,\"news.maxw\":maxw,\"news.readArt\":readArt,\"news.script\":script});", 1),
    # ── Épisodes : le mode de Chapitres, puis le flux d'origine ──
    ("E0-mode", "function DzChapitres({variant:e}){const[m,setM]=x.useState(null);",
     "function DzChapitres({variant:e}){const[m,setM]=x.useState(" + _k("chapitres.mode", "null") + ");__dzKeep[\"chapitres.mode\"]=m;", 1),
    ("E1-titre", 'const _t=x.useState(""),title=_t[0]', "const _t=x.useState(" + _k("episodes.title", '""') + "),title=_t[0]", 1),
    ("E2-script", '_s=x.useState(""),script=_s[0]', "_s=x.useState(" + _k("episodes.script", '""') + "),script=_s[0]", 1),
    ("E3-langue", '_l=x.useState("en"),lang=_l[0]', "_l=x.useState(" + _k("episodes.lang", '"en"') + "),lang=_l[0]", 1),
    ("E4-voix", '_v=x.useState(""),vid=_v[0]', "_v=x.useState(" + _k("episodes.vid", '""') + "),vid=_v[0]", 1),
    ("E5-resultat", "_r=x.useState(null),res=_r[0]", "_r=x.useState(" + _k("episodes.res", "null") + "),res=_r[0]", 1),
    ("E6-etape", "_st=x.useState(1),step=_st[0]", "_st=x.useState(" + _k("episodes.step", "1") + "),step=_st[0]", 1),
    ("E7-scenes", "_sc=x.useState([]),scenes=_sc[0]", "_sc=x.useState(" + _k("episodes.scenes", "[]") + "),scenes=_sc[0]", 1),
    ("E8-methode", '_sm=x.useState("paragraph"),sceneMethod', "_sm=x.useState(" + _k("episodes.sceneMethod", '"paragraph"') + "),sceneMethod", 1),
    ("E9-style", '_sst=x.useState(""),sceneStyle', "_sst=x.useState(" + _k("episodes.sceneStyle", '""') + "),sceneStyle", 1),
    ("E10-compteurs", "_cc=x.useState({}),counts", "_cc=x.useState(" + _k("episodes.counts", "{}") + "),counts", 1),
    ("E11-job", '_ej=x.useState(""),epJob', "_ej=x.useState(" + _k("episodes.epJob", '""') + "),epJob", 1),
    ("E12-enregistre-miroir", '_dzE=x.useState({id:"",sig:"",msg:"",list:null,open:!1}),dzE=_dzE[0],setDzE=_dzE[1];',
     "_dzE=x.useState(" + _k("episodes.dzE", '{id:"",sig:"",msg:"",list:null,open:!1}') + "),dzE=_dzE[0],setDzE=_dzE[1];"
     "Object.assign(__dzKeep,{\"episodes.title\":title,\"episodes.script\":script,\"episodes.lang\":lang,\"episodes.vid\":vid,"
     "\"episodes.res\":res,\"episodes.step\":step,\"episodes.scenes\":scenes,\"episodes.sceneMethod\":sceneMethod,"
     "\"episodes.sceneStyle\":sceneStyle,\"episodes.counts\":counts,\"episodes.epJob\":epJob,"
     "\"episodes.dzE\":Object.assign({},dzE,{open:!1})});", 1),
    ("E13-voix-pas-ecrasee", "setVid(g.voice_id)", "setVid(function(c0){return c0||g.voice_id})", 1),
]

SPEC_CHAR_DELTA = 1351       # mesurés le 07/10/2026 (ASCII seul : caractères = octets)
SPEC_BYTE_DELTA = 1351

SONDE_AMONT = [
    ("keepstate", "var __dzG=null,__dzKeep={};", 1),
    ("quick-recette", "function dzQuickApply(rc){", 1),
    ("news", "function pm({variant:e,go:Go}){", 1),
    ("episodes", "function DzEpisodes({variant:e}){", 1),
    ("assets2d", "function DzAssets2D(", 1),
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


def deltas():
    dc = sum(len(rp) - len(a) for _t, a, rp, _n in PATCHES)
    db = sum(len(rp.encode("utf-8")) - len(a.encode("utf-8")) for _t, a, rp, _n in PATCHES)
    return dc, db


def apply(s, anchor, replacement, tag, n=1):
    c = s.count(anchor)
    if c != n:
        raise SystemExit(f"[{tag}] anchor count={c} (want {n}). Aborting.")
    return s.replace(anchor, replacement)


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in sorted(bak.parent.glob(stem + ".bak_*")):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(f"[garde-chaine] backup aval detecte : {other.name} (plus recent que {bak.name}). "
                             f"Utilise `python scripts/repatch_all.py --from {TAG}`.")


def sonder(s):
    for tag, jeton, n in SONDE_AMONT:
        c = s.count(jeton)
        if c != n:
            raise SystemExit(f"[sonde-amont] {tag} : x{c} (attendu {n}) - maillon amont absent ou rejoue. Aborting.")


def main():
    args = sys.argv[1:]
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(f"[{TAG}] parite spec rompue : {dc} car / {db} o, spec {SPEC_CHAR_DELTA} / {SPEC_BYTE_DELTA}.")
    if "--force-unchained" not in args:
        guard_downstream(BAK)
    src = BAK if BAK.exists() else BUNDLE
    s, bom = lire(src)
    if "--check" in args:
        if s.count(MARKER):
            raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application refusee.")
        sonder(s)
        for tag, a, _r, n in PATCHES:
            if s.count(a) != n:
                raise SystemExit(f"[{TAG}] --check : ancre {tag} x{s.count(a)} (attendu {n}).")
        print(f"[{TAG}] --check OK : {len(PATCHES)} ancres, delta {dc} car / {db} o.")
        return
    if s.count(MARKER):
        raise SystemExit(f"[{TAG}] marqueur deja present dans {src.name} : double application refusee.")
    sonder(s)
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    avant_c, avant_o = len(s), len(s.encode("utf-8"))
    for tag, a, r_, n in PATCHES:
        s = apply(s, a, r_, tag, n)
    if s.count(MARKER) != MARKER_ATTENDU:
        raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)} apres application (attendu {MARKER_ATTENDU}).")
    if (len(s) - avant_c, len(s.encode("utf-8")) - avant_o) != (dc, db):
        raise SystemExit(f"[{TAG}] delta mesure != delta spec.")
    ecrire(BUNDLE, s, bom)
    print(f"[{TAG}] applique : {len(PATCHES)} sections, +{dc} car / +{db} o.")


if __name__ == "__main__":
    main()
