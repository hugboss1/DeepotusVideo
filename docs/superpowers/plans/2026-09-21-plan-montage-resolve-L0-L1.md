# Montage « classe Resolve » — lots L0 (socle) et L1 (édition) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Un sous-agent frais par tâche, puis deux revues — conformité d'abord, qualité ensuite. **Demander explicitement à chaque agent de contester le plan avec des mesures** (dix-huit fois sur le chantier précédent, l'agent avait raison contre sa revue).

**Goal :** donner au Montage l'historique complet, une barre OUTILS qui ne couvre plus les pistes, une plage I/O, les cinq modes d'édition, les trims roll / slip / slide, les marqueurs et l'échange de plans — décisions D-0, D-1, D-11, D-2, D-3, D-5, D-4 de `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md`, validées le 21/09/2026.

**Architecture :** RIEN de l'existant n'est réécrit. Chaque fonction nouvelle est **pure**, dans `frontend/patches/montage.js` (exportée sur `window.DzTracks`), jouée sous node par un banc autonome ; le câblage à l'écran est une **section de plus** dans `PATCHES` de `scripts/patch_bundle_montage.py` (ancre unique dans le bundle livré, vérifiée par `--check` avant toute écriture) ; les données nouvelles (`range`, `markers`) voyagent par un champ **optionnel** du payload de sauvegarde que `_save_record` accepte et que `GET /project` resert — absent, rien ne change. Le bloc `sonvfx`, `subs.js`, `vfxrack.js` restent intouchables.

**Tech Stack :** Python 3.13 embarqué (`$PY`, stdlib + Pillow), FastAPI + TestClient, node 24 (`node --check`, bancs du cœur JS par FICHIER shim, jamais `node -e`), bundle `frontend/dist/assets/index-BEOJX8L5.js` en OCTETS (CRLF), chaîne `python scripts/repatch_all.py --list` qui doit finir par `montage OK` puis les maillons aval jusqu'à `version OK`.

---

## Conventions valables pour tout le plan

```powershell
$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"
Set-Location backend                                   # les bancs se lancent d'ici
& $PY tests\test_montage_bundle.py                     # un banc = un processus
& $PY ..\scripts\patch_bundle_montage.py --check       # n'écrit rien : compte les ancres
& $PY ..\scripts\repatch_all.py --from montage         # rejoue montage PUIS les maillons aval
& $PY ..\scripts\repatch_all.py --list                 # doit lister TOUS les maillons OK
node --check ..\frontend\dist\assets\index-BEOJX8L5.js
```

- Un banc = `backend/tests/test_<x>.py` autonome : en tête `sys.stdout.reconfigure(encoding="utf-8")`, variables d'environnement AVANT tout `import app.…`, `check(label, cond, detail)` qui imprime `  PASS  <label>` / `  FAIL  <label> <detail>`, fin `=== N passed, M failed ===`, code de sortie 1 si rouge. **Jamais `pytest tests`.**
- Règle des assertions négatives : chaque banc construit son « état vide » (node muet, route en 503, fichier absent) et mesure qu'une négation ne verdit pas à vide.
- Faute n°6 : aucune lecture nue (`[-1]`, `index`, `json()`) avant un `check` — passer par `J()`, `temoin()`.
- Le bundle se lit et s'écrit en OCTETS (`read_text`/`write_text` du patcher = `read_bytes` + `decode`), jamais `Path.read_text`.
- Après tout rejeu : `repatch_all --list` complet, `node --check`, `git hash-object` ; **la sonde `("montage","DzTracks",60)` de `scripts/patch_bundle_dzcout.py` compte les occurrences de `DzTracks` dans le bundle — chaque tâche qui en ajoute met ce nombre à jour à la valeur MESURÉE** (sinon la chaîne refuse au maillon suivant).
- Commits PowerShell, sans guillemets doubles : `git commit --only <chemins> -m 'montage : <sujet sans accent>' -m '<corps>' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'` ; push de la branche `chantier/montage-resolve` après chaque tâche.

## Fichiers

| Fichier | Rôle dans ce plan |
|---|---|
| `frontend/patches/montage.js` | cœur pur : `dzmHistSnap/Apply`, `dzmRange*`, `dzmInsere`, `dzmSlip/Slide/Roll`, `dzmMarker*`, `dzmSwap` ; composants `DzmRangeBar`, `DzmModeBar`, `DzmMarkers`, `DzmMarkerIndex` ; exports `DzTracks.*` |
| `scripts/patch_bundle_montage.py` | sections nouvelles `H1…H8` (historique), `R1…R5` (plage), `E1…E3` (modes), `T1…T5` (trims), `K1…K6` (marqueurs), `W1…W2` (swap), ajoutées EN QUEUE de `PATCHES` ; textes de R_M17A/B/F réécrits |
| `frontend/dist/shared/montage.css` | `.dzm-tbar` déplacée hors des pistes ; `.dzm-range*`, `.dzm-mk*`, `.dzm-modebar` |
| `backend/app/services/montage_service.py` | `_save_record` accepte `range` et `markers` ; `GET /project` les resert |
| `scripts/patch_bundle_dzcout.py` | sonde `("montage","DzTracks",N)` remesurée |
| `backend/tests/test_montage_historique.py` | NEUF — banc node du cœur historique + plage + swap |
| `backend/tests/test_montage_edition.py` | NEUF — banc node des modes, trims, marqueurs |
| `backend/tests/test_montage_projets.py` | + `range` / `markers` par la route |
| `backend/tests/test_montage_bundle.py` | pins mis à jour (durée annulable, barre hors des pistes, compte de référence) |
| `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md` | ligne « exécuté » par décision, écarts datés |

---

## L0 — socle

### Tâche 1 — D-0 : le cœur pur de l'historique complet

**Files :** modifier `frontend/patches/montage.js` (avant la ligne `var DzTracks={` — chercher `var DzTracks=` ; la fonction s'ajoute juste au-dessus, l'export dans l'objet) ; créer `backend/tests/test_montage_historique.py`.

- [ ] **Étape 1 : écrire le banc rouge.**

```python
# -*- coding: utf-8 -*-
"""L0 — HISTORIQUE COMPLET (D-0), PLAGE I/O (D-11), ECHANGE (D-4) : le cœur
JS est EXECUTE sous node (frontend/patches/montage.js, celui que le patcher
injecte), jamais lu. Shim par FICHIER, jamais `node -e`.
Run : & $PY tests\test_montage_historique.py   (depuis backend/)"""
import json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_PATH = os.path.join(ROOT, "frontend", "patches", "montage.js")
NODE = shutil.which("node")
TMP = tempfile.mkdtemp(prefix="dzl0_")
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def temoin(e): return f"{type(e).__name__}: {e}"
def sh(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")

PROBE = r"""
var T=window.DzTracks,out={};
var P={clips:[{tr:"v1",id:"a",start:0,end:4},{tr:"a1",id:"b",start:0,end:2}],
       mixDb:{dialogue:-6},proj:{tracks:[{id:"v1",kind:"video"}],dur:10,
       subsStyle:{wordAnim:"glow"},range:{in:1,out:3},markers:[{t:2,color:"or"}],demo:!1}};
var s=T.histSnap(P);
out.snap_cles=Object.keys(s).sort();
out.snap_copie=s.clips!==P.clips||s.clips.length===P.clips.length;   /* refs conservees, pas de copie */
out.snap_vide=T.histSnap(null);
out.snap_sans_proj=Object.keys(T.histSnap({clips:[],mixDb:{}})).sort();
var p1={tracks:[{id:"v1"}],dur:99,subsStyle:{wordAnim:"couleur"},range:null,markers:[],mixDb:{dialogue:0},name:"x"};
var a=T.histApply(p1,s);
out.apply_dur=a.dur; out.apply_tracks=a.tracks.length; out.apply_anim=a.subsStyle.wordAnim;
out.apply_range=a.range; out.apply_markers=a.markers.length; out.apply_nom=a.name;
out.apply_pur=p1.dur===99;
/* un instantane PARTIEL (l'ancien {clips,mixDb}) ne touche pas au reste */
var b=T.histApply(p1,{clips:[],mixDb:{dialogue:-3}});
out.partiel_dur=b.dur; out.partiel_mix=b.mixDb.dialogue; out.partiel_tracks=b.tracks.length;
out.apply_nul=T.histApply(p1,null)===p1;
out.apply_mou=T.histApply(null,s).dur;
console.log(JSON.stringify(out));
"""
print("\n[1] histSnap / histApply sous node")
D = {}
if not NODE or not os.path.isfile(SRC_PATH):
    check("js_shim_execute", False, f"node={NODE} src={os.path.isfile(SRC_PATH)}")
else:
    shim = os.path.join(TMP, "shim.js")
    with open(SRC_PATH, "rb") as fh: SRC = fh.read().decode("utf-8-sig")
    with open(shim, "w", encoding="utf-8") as fh:
        fh.write('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + SRC + "\n" + PROBE)
    r = sh([NODE, shim])
    check("js_shim_execute", r.returncode == 0, (r.stderr or "")[-600:])
    lignes = (r.stdout or "").strip().splitlines()
    derniere = lignes[-1] if lignes else ""
    try:
        D = json.loads(derniere) if derniere else {}
    except Exception as e:
        D = {}; check("js_shim_rend_un_objet_json", False, temoin(e))
    check("js_shim_rend_un_objet_json", isinstance(D, dict) and bool(D), repr(derniere)[:160])
check("hist_snap_porte_les_six_cles",
      D.get("snap_cles") == ["clips", "dur", "markers", "mixDb", "range", "subsStyle", "tracks"][:0]
      or D.get("snap_cles") == ["clips", "dur", "markers", "mixDb", "range", "subsStyle", "tracks"],
      D.get("snap_cles"))
check("hist_snap_garde_les_references", D.get("snap_copie") is True)
check("hist_snap_nul_rend_objet_vide", D.get("snap_vide") == {})
check("hist_snap_sans_proj_ne_porte_que_clips_et_mix", D.get("snap_sans_proj") == ["clips", "mixDb"])
check("hist_apply_restaure_duree_pistes_style_plage_marqueurs",
      D.get("apply_dur") == 10 and D.get("apply_tracks") == 1 and D.get("apply_anim") == "glow"
      and D.get("apply_range") == {"in": 1, "out": 3} and D.get("apply_markers") == 1,
      {k: D.get(k) for k in ("apply_dur", "apply_tracks", "apply_anim", "apply_range", "apply_markers")})
check("hist_apply_ne_touche_pas_aux_autres_cles", D.get("apply_nom") == "x")
check("hist_apply_est_pur", D.get("apply_pur") is True)
check("hist_apply_partiel_ne_touche_que_ce_qu_il_porte",
      D.get("partiel_dur") == 99 and D.get("partiel_mix") == -3 and D.get("partiel_tracks") == 1,
      {k: D.get(k) for k in ("partiel_dur", "partiel_mix", "partiel_tracks")})
check("hist_apply_instantane_nul_rend_le_projet_tel_quel", D.get("apply_nul") is True)
check("hist_apply_projet_nul_ne_meurt_pas", D.get("apply_mou") == 10)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```

- [ ] **Étape 2 : lancer → rouge** (`T.histSnap is not a function` dans `js_shim_execute`).

- [ ] **Étape 3 : implémenter** dans `montage.js`, juste au-dessus de `var DzTracks=` :

```javascript
/* ── D-0 (21/09/2026) : L'HISTORIQUE COMPLET ─────────────────────────────
   MESURÉ sur le bundle : `pushHistory` n'empilait que {clips, mixDb} ; les
   pistes, la durée, le style S1, la plage et les marqueurs restaient hors
   d'atteinte de Ctrl+Z, et six titres de l'écran le disaient. Un instantané
   porte désormais SEPT clés, toutes des RÉFÉRENCES (les tableaux sont
   traités en immutable partout : stocker la référence suffit, comme avant).
   `histApply` ne touche QUE les clés que l'instantané PORTE : un h0
   historique {clips, mixDb} capturé par un geste amont reste valable. */
var DZM_HIST_CLES=["tracks","dur","subsStyle","range","markers"];
function dzmHistSnap(o){
  if(!o||typeof o!=="object")return {};
  var s={},p=o.proj,i,k;
  if("clips" in o)s.clips=o.clips;
  if("mixDb" in o)s.mixDb=o.mixDb;
  if(p&&typeof p==="object")for(i=0;i<DZM_HIST_CLES.length;i++){
    k=DZM_HIST_CLES[i];if(k in p)s[k]=p[k]}
  return s}
function dzmHistApply(p,s){
  if(!s||typeof s!=="object")return p;
  var base=(p&&typeof p==="object")?p:{},n=Object.assign({},base),i,k;
  if("mixDb" in s)n.mixDb=s.mixDb;
  for(i=0;i<DZM_HIST_CLES.length;i++){k=DZM_HIST_CLES[i];if(k in s)n[k]=s[k]}
  return n}
```

et dans l'objet `DzTracks` (avant `DEFAULTS:DZM_DEFAULT_TRACKS};`) :

```javascript
  histSnap:dzmHistSnap,histApply:dzmHistApply,HIST_CLES:DZM_HIST_CLES,
```

- [ ] **Étape 4 : lancer → `=== 12 passed, 0 failed ===`** (corriger la ligne `hist_snap_porte_les_six_cles` pour ne garder que la comparaison à la liste de sept clés — la forme `[:0] or` du brouillon est une faute, la retirer).

- [ ] **Étape 5 : commit.** `git commit --only frontend/patches/montage.js backend/tests/test_montage_historique.py -m 'montage : D-0 - coeur pur de l historique complet' -m 'histSnap porte sept cles par reference, histApply ne touche que ce que l instantane porte ; banc node.' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 2 — D-0 : le câblage — huit sections H1…H8

**Files :** modifier `scripts/patch_bundle_montage.py` (sections + textes de `R_M17A`, `R_M17B`, `R_M17F`), `frontend/patches/montage.js` (trois constantes de phrase), `scripts/patch_bundle_dzcout.py` (sonde), `backend/tests/test_montage_bundle.py` (pins).

- [ ] **Étape 1 : vérifier les ancres dans le bundle livré** (comptes MESURÉS le 21/09 : tous à 1) :

```python
# scratchpad/ancres_h.py — python embarqué, sortie UTF-8
import sys; sys.stdout.reconfigure(encoding="utf-8")
b=open("frontend/dist/assets/index-BEOJX8L5.js","rb").read().decode("utf-8")
for c in ['var histRef=x.useRef({u:[],r:[]});',
          'h.u.push(prev||{clips:clipsRef.current,mixDb:mixRef.current});',
          'var undo=x.useCallback(function(){', 'var redo=x.useCallback(function(){',
          'var h0={clips:clipsRef.current,mixDb:mixRef.current},snapAt=null;',
          'onSet:function(v){setProj(function(p){return Object.assign({},p,{dur:v})});setDirty(!0)},',
          'function subsStyleSet(patch){']:
    print(b.count(c), c[:60])
```

Attendu : sept lignes `1 …`. Si l'une n'est pas à 1, s'ARRÊTER et le dire.

- [ ] **Étape 2 : écrire les sections** dans `patch_bundle_montage.py`, avant `PATCHES = [` :

```python
# ── H1 (D-0) : la ref du projet et l'instantané complet, à côté de histRef ─
# `pushHistory`, `undo` et `redo` sont des useCallback à dépendances vides :
# ils ne voient JAMAIS `proj` — d'où une ref relue à chaque rendu, même motif
# que `dzTracksRef` (M16ref). `dzmHistHost()` est LE seul lecteur de l'état
# courant pour l'historique : les gestes qui capturaient h0 à la main passent
# par lui (H5), les autres gardent leur {clips, mixDb} — histApply s'en
# accommode (banc L0 [1], « partiel »).
A_H1 = "var histRef=x.useRef({u:[],r:[]});"
R_H1 = (A_H1 + "\n"
        "  var dzProjRef=x.useRef(null);dzProjRef.current=proj;\n"
        "  function dzmHistHost(){return DzTracks.histSnap({clips:clipsRef.current,"
        "mixDb:mixRef.current,proj:dzProjRef.current})}\n"
        "  var dzStyleHistAt=x.useRef(0);\n"
        "  var dzDurHistAt=x.useRef(0);")

# ── H2 (D-0) : ce que pushHistory empile sans argument ─────────────────────
A_H2 = "h.u.push(prev||{clips:clipsRef.current,mixDb:mixRef.current});"
R_H2 = "h.u.push(prev||dzmHistHost());"

# ── H3 / H4 (D-0) : undo et redo restaurent TOUT l'instantané ──────────────
# Le corps entier est l'ancre : `setClips(s.clips);` seul apparaît deux fois.
A_H3 = ("var undo=x.useCallback(function(){\n"
        "    var h=histRef.current;if(!h.u.length)return;\n"
        "    var s=h.u.pop();\n"
        "    h.r.push({clips:clipsRef.current,mixDb:mixRef.current});\n"
        "    if(h.r.length>60)h.r.shift();\n"
        "    setClips(s.clips);\n"
        "    setProj(function(p){return Object.assign({},p,{mixDb:s.mixDb})});\n"
        "    setDirty(!0);setHistTick(function(t){return t+1})},[]);")
R_H3 = ("var undo=x.useCallback(function(){\n"
        "    var h=histRef.current;if(!h.u.length)return;\n"
        "    var s=h.u.pop();\n"
        "    h.r.push(dzmHistHost());\n"
        "    if(h.r.length>60)h.r.shift();\n"
        "    if(\"clips\" in s)setClips(s.clips);\n"
        "    /* D-0 — pistes, durée, style S1, plage, marqueurs reviennent avec\n"
        "       le mixage ; SVM_TRACK_BUS suit les pistes restaurées. */\n"
        "    if(\"tracks\" in s)svmTrackBusSync(s.tracks);\n"
        "    setProj(function(p){return DzTracks.histApply(p,s)});\n"
        "    setDirty(!0);setHistTick(function(t){return t+1})},[]);")
A_H4 = A_H3.replace("var undo=", "var redo=").replace("!h.u.length", "!h.r.length") \
           .replace("h.u.pop()", "h.r.pop()").replace("h.r.push(", "h.u.push(") \
           .replace("h.r.length>60)h.r.shift", "h.u.length>60)h.u.shift")
R_H4 = R_H3.replace("var undo=", "var redo=").replace("!h.u.length", "!h.r.length") \
           .replace("h.u.pop()", "h.r.pop()").replace("h.r.push(", "h.u.push(") \
           .replace("h.r.length>60)h.r.shift", "h.u.length>60)h.u.shift")

# ── H5 (D-0) : le h0 du glisser de clip capture l'état ENTIER ──────────────
# Sans quoi le relâchement de M17f (qui allonge la durée) empilait un h0 sans
# `dur`, et « Annuler » rendait les clips mais pas la timeline.
A_H5 = "var h0={clips:clipsRef.current,mixDb:mixRef.current},snapAt=null;"
R_H5 = "var h0=dzmHistHost(),snapAt=null;"

# ── H6 (D-0) : le réglage de durée entre dans l'historique (fenêtre 600 ms) ─
A_H6 = ('onSet:function(v){setProj(function(p){return Object.assign({},p,{dur:v})});'
        'setDirty(!0)},')
R_H6 = ('onSet:function(v){var dzN=Date.now();'
        'if(dzN-dzDurHistAt.current>600)pushHistory();dzDurHistAt.current=dzN;'
        'setProj(function(p){return Object.assign({},p,{dur:v})});setDirty(!0)},')

# ── H7 (D-0) : le style S1 entre dans l'historique (même fenêtre) ──────────
A_H7 = "function subsStyleSet(patch){"
R_H7 = ("function subsStyleSet(patch){\n"
        "    var dzN=Date.now();if(dzN-dzStyleHistAt.current>600)pushHistory();"
        "dzStyleHistAt.current=dzN;")
```

et, en QUEUE de `PATCHES` (après `("M26b-traduction-rangee", A_M26B, R_M26B)`) :

```python
           ("H1-hist-ref", A_H1, R_H1), ("H2-hist-push", A_H2, R_H2),
           ("H3-hist-undo", A_H3, R_H3), ("H4-hist-redo", A_H4, R_H4),
           ("H5-hist-h0-clip", A_H5, R_H5), ("H6-hist-duree", A_H6, R_H6),
           ("H7-hist-style", A_H7, R_H7),
```

(`svmTracksSet` appelle déjà `pushHistory()` : les pistes entrent d'elles-mêmes. Pas de H8.)

- [ ] **Étape 3 : réécrire les phrases qui mentaient désormais.** Dans `montage.js` :

```javascript
var DZM_DUR_UNDO=" « Annuler » (Ctrl+Z) rend aussi la durée du projet : elle "+
  "entre dans l'historique depuis le 21/09/2026, avec les pistes, le style "+
  "des sous-titres, la plage et les marqueurs.";
var DZM_TB_H_CLIPS=" « Annuler » (Ctrl+Z) retire d'un coup ce qui vient "+
  "d'être posé : l'historique de cet écran mémorise tout l'état du montage.";
var DZM_TB_H_PISTE=" « Annuler » (Ctrl+Z) retire la piste : l'historique de "+
  "cet écran mémorise les pistes depuis le 21/09/2026. Le « × » de l'en-tête "+
  "de la piste la retire aussi.";
var DZM_TB_H_STYLE=" « Annuler » (Ctrl+Z) revient dessus : ce réglage entre "+
  "dans l'historique (une entrée par rafale de 600 ms).";
```

Dans `patch_bundle_montage.py`, dans `R_M17A`, `R_M17B` et `R_M17F`, remplacer la phrase `« Annuler » retire le clip mais NE raccourcit PAS la timeline — le réglage de durée, à côté du zoom, la reprend.` (et sa variante `« Annuler » rend les clips mais NE raccourcit PAS la timeline — le réglage de durée, à côté du zoom, la reprend.`) par `« Annuler » rend aussi la durée d'avant.` — chercher `NE raccourcit PAS` : trois occurrences attendues, zéro après.

- [ ] **Étape 4 : rejouer et compter.**

```powershell
& $PY ..\scripts\patch_bundle_montage.py --check        # 7 ancres de plus → « (N ancres OK) »
& $PY ..\scripts\repatch_all.py --from montage
```

Le maillon `dzcout` REFUSE (sonde `DzTracks` ≠ 60) : c'est attendu. Mesurer : `python -c "print(open('frontend/dist/assets/index-BEOJX8L5.js','rb').read().count(b'DzTracks'))"` → écrire ce nombre dans `STABLE_PROBES` de `patch_bundle_dzcout.py` (ligne `("montage", "DzTracks", 60)`), puis `repatch_all.py --from montage` de nouveau → `--list` finit par `version OK` ; `node --check` vert.

- [ ] **Étape 5 : mettre à jour les pins du banc bundle** (`test_montage_bundle.py`) :
  - ligne ~1883 `P10_<x>_dit_que_annuler_ne_rend_pas_la_duree` → renommer `P10_<x>_dit_que_annuler_rend_la_duree`, condition `"rend aussi la durée" in _r and "NE raccourcit PAS" not in _r` ;
  - ligne ~1887 : `"« Annuler » (Ctrl+Z) rend aussi la durée du projet" in src` ;
  - ligne ~3408 (sonde node) : `m.indexOf("rend aussi la durée")>=0` ;
  - ligne ~7923 : `"rend aussi la durée du projet" in w.get("ct_note", "")`.
  - AJOUTER, après la boucle sur `P.PATCHES`, sept lignes `D0_<section>_present_une_fois` — inutile : la boucle les émet seule. Ajouter UNE ligne de fond :

```python
check("D0_undo_restaure_tout_l_instantane",
      s.count(nl("setProj(function(p){return DzTracks.histApply(p,s)});")) == 2
      and s.count(nl("h.r.push(dzmHistHost());")) == 1
      and s.count(nl("h.u.push(dzmHistHost());")) == 1
      and s.count(nl("h.u.push(prev||dzmHistHost());")) == 1,
      "undo/redo ne passent pas par histApply, ou pushHistory empile encore {clips,mixDb}")
```

- [ ] **Étape 6 : lancer les DOUZE bancs** depuis `backend/` (bundle, historique, sources, remplacer, projets, texte, subs_animes, etalonnage, pistes_dyn, pistes_rendu, media, effects) → tous `0 failed` ; noter le nouveau compte du banc bundle dans sa docstring (« COMPTE DE REFERENCE, 21/09/2026 (D-0) : N lignes, soit … ») en décomposant les lignes ajoutées.

- [ ] **Étape 7 : preuve à l'écran** (backend 8799, projet réel : poser un clip depuis la Bibliothèque, ajouter une piste par « audio », allonger la timeline de 6 s, Ctrl+Z trois fois) : la timeline revient à sa durée, la piste disparaît, le clip disparaît. Capturer la note.

- [ ] **Étape 8 : commit.** `git commit --only scripts/patch_bundle_montage.py scripts/patch_bundle_dzcout.py frontend/patches/montage.js frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_montage_bundle.py -m 'montage : D-0 - historique complet cable (pistes, duree, style, plage, marqueurs)' -m '...' -m 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`

### Tâche 3 — D-1 : la barre OUTILS ne recouvre plus les pistes

**Files :** modifier `frontend/dist/shared/montage.css` (règle `.dzsvm .dzm-tbar{`), `backend/tests/test_montage_bundle.py`, `docs/superpowers/specs/2026-09-21-montage-vs-resolve-design.md`.

- [ ] **Étape 1 : banc rouge.** Dans `test_montage_bundle.py`, à côté des lectures `_regle(...)` (ligne ~497) :

```python
_R_TBAR = _regle(CSS.read_text(encoding="utf-8"), ".dzsvm .dzm-tbar{")
check("D1_la_barre_flotte_AU_DESSUS_du_transport_pas_sur_les_pistes",
      _R_TBAR is not None and "bottom:calc(100% + 8px)" in _R_TBAR
      and "top:calc(100% + 8px)" not in _R_TBAR and "top:auto" in _R_TBAR,
      f"regle .dzm-tbar : {_R_TBAR!r}")
```

Lancer → FAIL.

- [ ] **Étape 2 : la règle.** Dans `montage.css`, `.dzsvm .dzm-tbar{position:absolute; left:14px; top:calc(100% + 8px);` devient :

```css
.dzsvm .dzm-tbar{position:absolute; left:14px; top:auto; bottom:calc(100% + 8px);
```

et le commentaire qui précède gagne :

```css
/* D-1 (21/09/2026) — MESURÉ : à `top:calc(100% + 8px)` la barre (831 × 83 à
   (246,595) en 1400 × 900) recouvrait V2 et V1 (y 606–700) : un clic sur un
   clip de V2 tombait sur ses boutons. Elle flotte désormais AU-DESSUS du
   bandeau de transport, sur le pied de la zone de prévisualisation ; le
   conteneur de bornage (timeline ∪ prévisualisation) et l'aimantation ne
   changent pas, `dz_svm_tb_off` reste relatif à cette nouvelle origine. */
```

- [ ] **Étape 3 : vérifier que l'ancien décalage persisté ne sort pas de l'écran** : sous node, `DzTracks.tbRecadre` avec un `dz_svm_tb_off` de `{dx:0,dy:300}` et un conteneur 1168 × 796 rend un `dy` borné (le banc `tb_*` existant le couvre : lancer `test_montage_bundle.py`, `0 failed`).

- [ ] **Étape 4 : preuve à l'écran** (1400 × 900) : `#dzm-toolbar.getBoundingClientRect().bottom < .svm-trans.getBoundingClientRect().top` ; les clips de V2 se sélectionnent au clic sans replier la barre.

- [ ] **Étape 5 : écart daté** dans le design (§1.1, ligne D-1) : « exécuté 21/09 — origine au-dessus du transport ». Commit `--only` des trois fichiers.

### Tâche 4 — D-11 : la plage I/O (entrée, sortie, effacer, couper la plage)

**Files :** modifier `frontend/patches/montage.js`, `scripts/patch_bundle_montage.py` (R1…R5), `frontend/dist/shared/montage.css`, `backend/app/services/montage_service.py`, `backend/tests/test_montage_historique.py` (section [2]), `backend/tests/test_montage_projets.py`.

- [ ] **Étape 1 : banc rouge** — ajouter à `PROBE` de `test_montage_historique.py` :

```javascript
/* [2] plage I/O */
out.r_in=T.rangeSet(null,"in",3.2,10);
out.r_out=T.rangeSet({in:3.2,out:null},"out",7,10);
out.r_inverse=T.rangeSet({in:6,out:8},"in",9,10);       /* in > out : out suit */
out.r_borne=T.rangeSet(null,"out",99,10);
out.r_neg=T.rangeSet(null,"in",-4,10);
out.r_clear=T.rangeSet({in:1,out:2},"clear",0,10);
out.r_from=[T.rangeFrom({in:"1.5",out:4}),T.rangeFrom({in:5,out:2}),T.rangeFrom("x"),T.rangeFrom({in:1})];
out.r_len=[T.rangeLen({in:1,out:4.5}),T.rangeLen(null),T.rangeLen({in:2,out:null})];
```

et en Python :

```python
print("\n[2] plage I/O")
check("range_in_pose_l_entree", D.get("r_in") == {"in": 3.2, "out": None})
check("range_out_pose_la_sortie", D.get("r_out") == {"in": 3.2, "out": 7})
check("range_entree_apres_la_sortie_pousse_la_sortie", D.get("r_inverse") == {"in": 9, "out": 10})
check("range_borne_a_la_duree", D.get("r_borne") == {"in": None, "out": 10})
check("range_jamais_negative", D.get("r_neg") == {"in": 0, "out": None})
check("range_clear_rend_null", D.get("r_clear") is None)
check("range_from_assainit",
      D.get("r_from") == [{"in": 1.5, "out": 4}, None, None, None], D.get("r_from"))
check("range_len", D.get("r_len") == [3.5, 0, 0])
```

- [ ] **Étape 2 : implémenter** (montage.js, avant `var DzTracks=`) :

```javascript
/* ── D-11 : LA PLAGE D'ENTRÉE / SORTIE ─────────────────────────────────────
   `proj.range` = {in, out} (secondes, null si non posé) ou null. Pure :
   `dzmRangeSet(range, which, t, dur)` rend la plage suivante ; "in" après
   "out" pousse "out" à dur (jamais une plage inversée) ; "clear" rend null.
   Persistée par POST /save (`range`), restaurée par `dzmRangeFrom`. */
function dzmRangeNum(v,dur){
  var n=Number(v);if(!isFinite(n))return null;
  var d=Number(dur);if(!isFinite(d)||d<0)d=0;
  return Math.max(0,Math.min(d,dzmR3(n)))}
function dzmRangeSet(range,which,t,dur){
  var r=range&&typeof range==="object"?{in:range.in,out:range.out}:{in:null,out:null};
  if(which==="clear")return null;
  var v=dzmRangeNum(t,dur);
  if(v==null)return range||null;
  if(which==="in"){r.in=v;if(r.out!=null&&r.out<=v)r.out=dzmRangeNum(dur,dur)}
  else if(which==="out"){r.out=v;if(r.in!=null&&r.in>=v)r.in=0}
  else return range||null;
  if(r.in==null)r.in=null;if(r.out==null)r.out=null;
  return r}
function dzmRangeFrom(v){
  if(!v||typeof v!=="object")return null;
  var a=Number(v.in),b=Number(v.out);
  if(!isFinite(a)||!isFinite(b)||a<0||b<=a)return null;
  return {in:dzmR3(a),out:dzmR3(b)}}
function dzmRangeLen(r){
  if(!r||typeof r!=="object")return 0;
  var a=Number(r.in),b=Number(r.out);
  return (isFinite(a)&&isFinite(b)&&b>a)?dzmR3(b-a):0}
/* la barre sur la règle : deux poignées et la bande entre elles */
function DzmRangeBar(o){
  var rg=dzmRangeFrom(o&&o.range),d=Number(o&&o.dur)||1;
  if(!rg)return null;
  var l=rg.in/d*100,w=(rg.out-rg.in)/d*100;
  return r.jsx("div",{className:"dzm-range","data-testid":"dzm-range",
    title:"Plage "+rg.in.toFixed(2)+" s → "+rg.out.toFixed(2)+" s — I : entrée, "+
      "U : sortie, X : effacer, Maj+X : couper la plage (toutes pistes, ripple)",
    style:{left:"calc(88px + (100% - 88px) * "+(l/100)+")",width:"calc((100% - 88px) * "+(w/100)+")"}})}
```

Exports : `rangeSet:dzmRangeSet,rangeFrom:dzmRangeFrom,rangeLen:dzmRangeLen,RangeBar:DzmRangeBar,`.

CSS (`montage.css`) :

```css
/* D-11 — la plage I/O sur la règle : bande ambre translucide, 4 px de haut,
   posée au pied de la règle (18 px) ; ne capte aucun pointeur. */
.dzsvm .svm-ruler{position:relative}
.dzsvm .dzm-range{position:absolute; bottom:0; height:4px; pointer-events:none;
  background:var(--gold, #f0b429); opacity:.7; z-index:3}
```

- [ ] **Étape 3 : les sections R1…R5** :

```python
# ── R1 (D-11) : quatre actions dans SVM_ACTIONS (remappables, listées) ─────
# Lettres MESURÉES libres : I, U, X (B D F G J K L M N O R S T pris, C sous Alt).
A_R1 = ' {id:"ripple",sec:"Montage",lbl:"ripple — refermer les trous",combo:"R"},'
R_R1 = (A_R1 + "\n"
        ' {id:"range_in",sec:"Montage",lbl:"plage : point d\'entrée à la tête",combo:"I"},\n'
        ' {id:"range_out",sec:"Montage",lbl:"plage : point de sortie à la tête",combo:"U"},\n'
        ' {id:"range_clear",sec:"Montage",lbl:"plage : effacer",combo:"X"},\n'
        ' {id:"range_cut",sec:"Montage",lbl:"plage : couper (toutes pistes, ripple)",combo:"Maj+X"},')

# ── R2 (D-11) : la branche de dispatch ─────────────────────────────────────
A_R2 = 'if(id==="ripple"){setRipple(function(v){return !v});return}'
R_R2 = (A_R2 + "\n"
        '      if(id==="range_in"||id==="range_out"||id==="range_clear"){'
        'pushHistory();var dzW=id.slice(6);'
        'setProj(function(p){return Object.assign({},p,{range:DzTracks.rangeSet(p.range,dzW,phRef.current,p.dur)})});'
        'setDirty(!0);return}\n'
        '      if(id==="range_cut"){var dzRg=DzTracks.rangeFrom(dzProjRef.current&&dzProjRef.current.range);'
        'if(!dzRg){fireNote("Aucune plage : I pose l\'entrée, U la sortie.");return}'
        'var dzLk={};Object.keys(trackStRef.current).forEach(function(k){if(trackStRef.current[k]&&trackStRef.current[k].l)dzLk[k]=!0});'
        'var dzLoop=svmTracksOf(dzProjRef.current).filter(function(t){return t.loop}).map(function(t){return t.id});'
        'var dzRc=DzTracks.rippleCut(clipsRef.current,dzRg.in,dzRg.out,{loopTracks:dzLoop,locked:dzLk});'
        'pushHistory();setClips(dzRc.clips);'
        'setProj(function(p){return Object.assign({},p,{range:null})});setDirty(!0);'
        'fireNote("Plage "+dzRg.in.toFixed(2)+" → "+dzRg.out.toFixed(2)+" s coupée sur toutes les pistes — "+dzRc.removed+" clip(s) retiré(s), la suite remonte.");return}')

# ── R3 (D-11) : la bande sur la règle, après la gouttière ──────────────────
A_R3 = 'r.jsx("div",{className:"svm-gutter"}),'
R_R3 = A_R3 + 'r.jsx(DzTracks.RangeBar,{range:proj.range,dur:dur}),'

# ── R4 (D-11) : la plage part avec la sauvegarde ───────────────────────────
A_R4 = "      project_id:proj.project_id,"
R_R4 = A_R4 + "\n      range:DzTracks.rangeFrom(proj.range),"

# ── R5 (D-11) : et revient avec elle ───────────────────────────────────────
A_R5 = "v1NonVideo:Array.isArray(d.v1_non_video)?d.v1_non_video:null,"
R_R5 = A_R5 + "range:DzTracks.rangeFrom(d.range),"
```

`PATCHES` : `("R1-plage-actions", A_R1, R_R1), ("R2-plage-dispatch", A_R2, R_R2), ("R3-plage-regle", A_R3, R_R3), ("R4-plage-save", A_R4, R_R4), ("R5-plage-restore", A_R5, R_R5),`. **Vérifier `--check`** : `phRef`, `trackStRef`, `svmTracksOf`, `dzProjRef` (H1) sont dans la portée d'`onKey` (mesuré : `phRef.current` y est déjà lu par `blade`).

- [ ] **Étape 4 : backend.** Dans `_save_record`, après le bloc `tracks` :

```python
    # D-11 : la plage d'entrée/sortie {in, out} en secondes. Assainie ici :
    # deux nombres finis, 0 ≤ in < out. Absente ou invalide → non stockée.
    rg = body.get("range")
    if isinstance(rg, dict):
        try:
            a, b = float(rg.get("in")), float(rg.get("out"))
            if a == a and b == b and 0 <= a < b:
                data["range"] = {"in": round(a, 3), "out": round(b, 3)}
        except (TypeError, ValueError):
            pass
```

Dans `montage_project` (`GET /project`), après le bloc `project_id` :

```python
            if isinstance(saved.get("range"), dict):
                out["range"] = saved["range"]             # D-11 (cf. POST /save)
```

Banc `test_montage_projets.py` : une section `[7] D-11 range` — `POST /save` avec `range:{in:1,out:3}` → `GET /project` rend `range == {"in":1.0,"out":3.0}` ; avec `range:{in:3,out:1}` → clé absente ; avec `range:"x"` → absente ; sans `range` → absente (état vide construit).

- [ ] **Étape 5 : rejouer, remesurer la sonde dzcout, bancs, preuve à l'écran** (I à 2 s, U à 6 s : bande visible sur la règle ; Maj+X : les clips sous la plage sont fendus et la suite remonte ; Ctrl+Z rend tout). Commit `--only`.

---

## L1 — édition

### Tâche 5 — D-2 : les cinq modes d'édition, cœur pur

**Files :** modifier `frontend/patches/montage.js` ; créer `backend/tests/test_montage_edition.py` (même en-tête que `test_montage_historique.py`, préfixe `dzl1_`).

- [ ] **Étape 1 : banc rouge** (`PROBE`) :

```javascript
var T=window.DzTracks,out={};
var C=[{tr:"v1",id:"p1",start:0,end:4,src:{a:1}},{tr:"v1",id:"p2",start:4,end:8,src:{a:1}},
       {tr:"v2",id:"o1",start:1,end:3,src:{a:1}},{tr:"a1",id:"n1",start:0,end:8,src:{a:1}}];
var TS=[{id:"v3",kind:"video"},{id:"v2",kind:"video"},{id:"v1",kind:"video"},{id:"a1",kind:"audio"}];
var N={tr:"v1",id:"x",start:2,end:5,src:{b:1},srcIn:0};
function sv(res,tr){return (res.clips||[]).filter(function(c){return c.tr===tr})
  .sort(function(a,b){return a.start-b.start}).map(function(c){return [c.id,c.start,c.end,c.srcIn==null?null:c.srcIn]})}
out.modes=T.MODES.map(function(m){return m[0]});
/* écraser : ce qui est sous [2,5[ est rogné ou fendu */
var e=T.insere(C,N,"ecraser",{tracks:TS});
out.ecraser=sv(e,"v1"); out.ecraser_autres=sv(e,"a1").length;
/* insérer : tout ce qui commence à ≥ 2 sur v1 recule de 3, p1 est fendu */
var i=T.insere(C,N,"inserer",{tracks:TS});
out.inserer=sv(i,"v1");
/* fin : après le dernier clip de la piste, la tête ignorée */
var f=T.insere(C,N,"fin",{tracks:TS});
out.fin=sv(f,"v1");
/* dessus : sur la piste vidéo LIBRE la plus proche au-dessus de v1 → v3 (v2 est occupée en [1,3[) */
var d=T.insere(C,N,"dessus",{tracks:TS});
out.dessus_piste=d.track; out.dessus=sv(d,"v3");
var d2=T.insere(C,Object.assign({},N,{start:5,end:7}),"dessus",{tracks:TS});
out.dessus_v2_libre=d2.track;
/* ripple_ecraser : remplace le clip sous la tête (p1, 4 s) par x (3 s) ; la suite avance de 1 */
var r=T.insere(C,N,"ripple_ecraser",{tracks:TS,head:2});
out.ripple=sv(r,"v1");
/* remplir : la plage I/O fixe les bornes et la vitesse (source 6 s dans 3 s → ×2) */
var m=T.insere(C,Object.assign({},N,{srcDur:6}),"remplir",{tracks:TS,range:{in:2,out:5}});
out.remplir=sv(m,"v1"); out.remplir_speed=(m.clips.filter(function(c){return c.id==="x"})[0]||{}).speed;
out.remplir_sans_plage=T.insere(C,N,"remplir",{tracks:TS}).mode;
/* jumeau : le clip A1 posé en même temps suit le même mode (insérer décale aussi a1 ? NON — seule la piste visée ripple) */
var j=T.insere(C,N,"inserer",{tracks:TS,twin:{tr:"a1",id:"xa",start:2,end:5,src:{b:1}}});
out.jumeau=sv(j,"a1");
/* mous */
out.mou=[T.insere(null,N,"ecraser",{}).clips.length,T.insere(C,null,"ecraser",{}).clips.length,
         T.insere(C,N,"zzz",{}).mode,T.insere(C,N,"ecraser",{locked:{v1:1}}).refus];
out.pur=C.length===4&&C[0].end===4;
console.log(JSON.stringify(out));
```

Assertions Python :

```python
check("modes_les_six", D.get("modes") == ["ecraser","inserer","fin","dessus","ripple_ecraser","remplir"])
check("ecraser_rogne_et_fend", D.get("ecraser") == [["p1",0,2,None],["x",2,5,0],["p2",5,8,1]], D.get("ecraser"))
check("ecraser_ne_touche_pas_les_autres_pistes", D.get("ecraser_autres") == 1)
check("inserer_fend_et_pousse", D.get("inserer") == [["p1",0,2,None],["x",2,5,0],["p1_r",5,7,2],["p2",7,11,None]], D.get("inserer"))
check("fin_apres_le_dernier", D.get("fin") == [["p1",0,4,None],["p2",4,8,None],["x",8,11,0]], D.get("fin"))
check("dessus_prend_la_piste_libre_la_plus_proche", D.get("dessus_piste") == "v3" and D.get("dessus") == [["x",2,5,0]], D.get("dessus_piste"))
check("dessus_v2_quand_libre", D.get("dessus_v2_libre") == "v2")
check("ripple_ecraser_remplace_et_recale", D.get("ripple") == [["x",2,5,0],["p2",5,9,None]], D.get("ripple"))
check("remplir_fixe_bornes_et_vitesse", D.get("remplir") == [["p1",0,2,None],["x",2,5,0],["p2",5,8,1]] and D.get("remplir_speed") == 2, D.get("remplir_speed"))
check("remplir_sans_plage_retombe_en_ecraser", D.get("remplir_sans_plage") == "ecraser")
check("jumeau_suit_sur_sa_piste", D.get("jumeau") == [["n1",0,2,None],["xa",2,5,None],["n1_r",5,11,2]], D.get("jumeau"))
check("entrees_molles", D.get("mou") == [0, 4, "ecraser", "verrou"], D.get("mou"))
check("insere_est_pur", D.get("pur") is True)
```

- [ ] **Étape 2 : implémenter** (montage.js) :

```javascript
/* ── D-2 : LES MODES D'ÉDITION ─────────────────────────────────────────────
   Chez Resolve : insert, overwrite, replace, fit to fill, place on top,
   append at end, ripple overwrite. Ici SIX modes sur `dzmInsere(clips,clip,
   mode,opts)` (replace = « Remplacer la source… », P6, existe déjà) :
     ecraser         pose et rogne/fend ce qui est dessous (même piste) ;
     inserer         fend au point d'entrée et POUSSE la suite de la piste ;
     fin             pose après le dernier clip de la piste, tête ignorée ;
     dessus          pose sur la piste vidéo LIBRE la plus proche au-dessus ;
     ripple_ecraser  retire le clip sous la tête, pose, recale la suite ;
     remplir         (fit to fill) bornes = plage I/O, vitesse = source/plage.
   Rend {clips, track, mode, refus}. `opts.twin` (le jumeau A1 de P12) suit
   le même mode SUR SA PISTE. Fendre réutilise dzmRippleCut : mêmes ids `_r`. */
var DZM_MODES=[["ecraser","écraser"],["inserer","insérer"],["fin","en fin"],
  ["dessus","au-dessus"],["ripple_ecraser","écraser en ripple"],["remplir","remplir la plage"]];
function dzmModeOk(m){return DZM_MODES.some(function(o){return o[0]===m})?m:"ecraser"}
function dzmTrackEnd(clips,tr){
  var m=0;(clips||[]).forEach(function(c){if(c&&c.tr===tr&&Number(c.end)>m)m=Number(c.end)});
  return dzmR3(m)}
function dzmOverlap(clips,tr,a,b,skip){
  return (clips||[]).some(function(c){return c&&c.tr===tr&&c.id!==skip&&
    Number(c.start)<b-1e-6&&Number(c.end)>a+1e-6})}
/* fend/rogne ce qui est sous [a,b[ sur UNE piste, sans rien décaler */
function dzmCarve(clips,tr,a,b){
  var out=[],taken=Object.create(null);
  (clips||[]).forEach(function(c){if(c&&c.id!=null)taken[String(c.id)]=1});
  function nid(id){var base=String(id)+"_r",n=base,i=2;while(taken[n])n=base+(i++);taken[n]=1;return n}
  (clips||[]).forEach(function(c){
    if(!c||c.tr!==tr){out.push(c);return}
    var s=Number(c.start)||0,e=Number(c.end)||0,sp=dzmSpeedNum(c),si=Number(c.srcIn)||0;
    if(e<=a||s>=b){out.push(c);return}
    if(s<a)out.push(Object.assign({},c,{end:dzmR3(a)}));
    if(e>b)out.push(Object.assign({},c,{id:s<a?nid(c.id):c.id,start:dzmR3(b),
      srcIn:dzmR3(si+(b-s)*sp)}))});
  return out}
function dzmPose(clips,tr,clip,st,en,extra){
  var k=Object.assign({},clip,{tr:tr,start:dzmR3(st),end:dzmR3(en)},extra||{});
  if(k.srcIn==null)k.srcIn=0;
  return clips.concat([k])}
function dzmInsereUn(clips,clip,mode,opts,tr){
  var st=Number(clip.start)||0,len=dzmR3((Number(clip.end)||0)-st),o=opts||{};
  if(!(len>0))len=dzmR3(Number(DZM_CLIP_DEFAUTS.video)||6);
  if(mode==="fin"){st=dzmTrackEnd(clips,tr);return {clips:dzmPose(clips,tr,clip,st,st+len),mode:mode}}
  if(mode==="inserer"){
    var cut=dzmCarve(clips,tr,st,st);            /* fend à st sans rien retirer */
    cut=cut.map(function(c){return (c&&c.tr===tr&&Number(c.start)>=st-1e-6)?
      Object.assign({},c,{start:dzmR3(Number(c.start)+len),end:dzmR3(Number(c.end)+len)}):c});
    return {clips:dzmPose(cut,tr,clip,st,st+len),mode:mode}}
  if(mode==="ripple_ecraser"){
    var h=Number(o.head);if(!isFinite(h))h=st;
    var under=(clips||[]).filter(function(c){return c&&c.tr===tr&&Number(c.start)<=h+1e-6&&Number(c.end)>h+1e-6})[0];
    if(!under)return dzmInsereUn(clips,clip,"ecraser",o,tr);
    var s0=Number(under.start),d=dzmR3(len-(Number(under.end)-s0));
    var rest=(clips||[]).filter(function(c){return c!==under}).map(function(c){
      return (c&&c.tr===tr&&Number(c.start)>=Number(under.end)-1e-6)?
        Object.assign({},c,{start:dzmR3(Number(c.start)+d),end:dzmR3(Number(c.end)+d)}):c});
    return {clips:dzmPose(rest,tr,clip,s0,s0+len),mode:mode}}
  if(mode==="remplir"){
    var rg=dzmRangeFrom(o.range);
    if(!rg)return dzmInsereUn(clips,clip,"ecraser",o,tr);
    var plage=dzmR3(rg.out-rg.in),sd=Number(clip.srcDur)||0,sp=sd>0?dzmR3(sd/plage):1;
    sp=Math.max(.25,Math.min(4,sp));
    return {clips:dzmPose(dzmCarve(clips,tr,rg.in,rg.out),tr,clip,rg.in,rg.out,{speed:sp,srcIn:0}),mode:mode}}
  return {clips:dzmPose(dzmCarve(clips,tr,st,st+len),tr,clip,st,st+len),mode:"ecraser"}}
function dzmInsere(clips,clip,mode,opts){
  var cs=Array.isArray(clips)?clips:[],o=opts||{},m=dzmModeOk(mode);
  if(!clip||typeof clip!=="object")return {clips:cs.slice(),track:null,mode:m,refus:"clip"};
  var tr=clip.tr;
  if(m==="dessus"){
    var ts=Array.isArray(o.tracks)?o.tracks:[],i,t,st=Number(clip.start)||0,en=Number(clip.end)||0,ix=-1;
    for(i=0;i<ts.length;i++)if(ts[i]&&ts[i].id===tr)ix=i;
    var found=null;
    for(i=ix-1;i>=0;i--){t=ts[i];if(t&&t.kind==="video"&&!dzmOverlap(cs,t.id,st,en)){found=t.id;break}}
    if(!found)return Object.assign(dzmInsereUn(cs,clip,"ecraser",o,tr),{track:tr,refus:"aucune piste libre au-dessus"});
    tr=found;m="ecraser"}
  if(o.locked&&o.locked[tr])return {clips:cs.slice(),track:tr,mode:m,refus:"verrou"};
  var res=dzmInsereUn(cs,clip,m,o,tr);
  if(o.twin&&typeof o.twin==="object"&&o.twin.tr){
    var tw=Object.assign({},o.twin,{start:clip.start,end:clip.end});
    if(res.mode==="fin"){var xc=res.clips.filter(function(c){return c.id===clip.id})[0];
      if(xc)tw=Object.assign({},tw,{start:xc.start,end:xc.end})}
    res.clips=dzmInsereUn(res.clips,tw,res.mode==="remplir"?"ecraser":res.mode,
      Object.assign({},o,{head:clip.start}),tw.tr).clips}
  res.track=tr;res.refus=res.refus||"";
  return res}
```

Exports : `insere:dzmInsere,MODES:DZM_MODES,carve:dzmCarve,`.

- [ ] **Étape 3 : lancer → vert** ; si une attente du banc est fausse par rapport à une règle mesurée (ex. ids `_r`), corriger la LIGNE et le dire dans le commit. **Étape 4 : commit** `--only montage.js test_montage_edition.py`.

### Tâche 6 — D-2 : le câblage — sélecteur de mode et `addAsset`

**Files :** modifier `scripts/patch_bundle_montage.py` (E1…E3), `frontend/patches/montage.js` (`DzmModeBar`), `frontend/dist/shared/montage.css`, `test_montage_bundle.py`.

- [ ] **Étape 1 : le composant** (montage.js) :

```javascript
/* la rangée des modes, dans le sélecteur d'assets — six chips exclusives */
function DzmModeBar(o){
  var cur=dzmModeOk(o&&o.mode),on=typeof (o&&o.onMode)==="function"?o.onMode:function(){};
  return r.jsx("div",{className:"dzm-modebar",role:"radiogroup","aria-label":"Mode d'édition",
    children:DZM_MODES.map(function(m){
      var dis=m[0]==="remplir"&&!dzmRangeFrom(o&&o.range);
      return r.jsx("button",{className:"svm-toolchip dzm-modechip",role:"radio",
        "aria-checked":cur===m[0]?"true":"false","data-on":cur===m[0]?"":void 0,
        disabled:dis||void 0,
        title:DZM_MODE_T[m[0]]+(dis?" — posez d'abord une plage (I / U).":""),
        onClick:function(){on(m[0])},children:m[1]},m[0])})})}
var DZM_MODE_T={ecraser:"Écraser : le clip se pose à la tête et rogne ou fend ce qui est dessous.",
  inserer:"Insérer : fend à la tête et pousse la suite de la piste (ripple).",
  fin:"En fin : après le dernier clip de la piste, la tête est ignorée.",
  dessus:"Au-dessus : sur la piste vidéo libre la plus proche au-dessus (titres, PIP).",
  ripple_ecraser:"Écraser en ripple : remplace le clip sous la tête, la suite se recale à la nouvelle durée.",
  remplir:"Remplir la plage : bornes = plage I/O, vitesse calculée pour la remplir (V1)."};
```

Export : `ModeBar:DzmModeBar,MODE_T:DZM_MODE_T,`. CSS : `.dzsvm .dzm-modebar{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}`.

- [ ] **Étape 2 : sections** :

```python
# ── E1 (D-2) : l'état du mode, à côté de dzTracksRef (M16ref) ───────────────
A_E1 = "var dzTracksRef=x.useRef(null);dzTracksRef.current=svmTracksOf(proj);"
R_E1 = (A_E1 + "\n"
        '  var stDzM=x.useState("ecraser"),dzMode=stDzM[0],setDzMode=stDzM[1];\n'
        "  var dzModeRef=x.useRef(dzMode);dzModeRef.current=dzMode;")

# ── E2 (D-2) : la rangée dans le sélecteur, sous son titre ──────────────────
A_E2 = ':("Ajouter sur la piste "+tr2.toUpperCase())}),'
R_E2 = (A_E2 + "\n"
        "      r.jsx(DzTracks.ModeBar,{mode:dzMode,onMode:setDzMode,range:proj.range}),")

# ── E3 (D-2) : l'écriture d'addAsset passe par le mode ──────────────────────
A_E3 = "setClips(clipsRef.current.concat(dzTw&&dzTw.clip?[dzNeuf,dzTw.clip]:[dzNeuf]));"
R_E3 = ("var dzIns=DzTracks.insere(clipsRef.current,Object.assign({},dzNeuf,{srcDur:Number(srcDur)||0}),"
        "dzModeRef.current,{tracks:dzTs,twin:dzTw&&dzTw.clip,head:phRef.current,"
        "range:dzProjRef.current&&dzProjRef.current.range,"
        "locked:(function(){var o={},k;for(k in trackStRef.current)if(trackStRef.current[k]&&trackStRef.current[k].l)o[k]=!0;return o})()});\n"
        "    if(dzIns.refus==='verrou'){fireNote('Piste '+String(dzIns.track).toUpperCase()+' verrouillée — rien n\\'a été posé.');return}\n"
        "    if(dzIns.track&&dzIns.track!==tr2)dzTail+=' Posé sur '+String(dzIns.track).toUpperCase()+' (au-dessus).';\n"
        "    if(dzIns.refus)dzTail+=' '+dzIns.refus+'.';\n"
        "    setClips(dzIns.clips);")
```

`dzTs` existe dans `addAsset` (mesuré : lu par `twinPlan`). `PATCHES` : `("E1-mode-etat", …), ("E2-mode-rangee", …), ("E3-mode-addasset", …)`. **`--check`** avant tout.

- [ ] **Étape 3 : banc bundle** — ajouter :

```python
check("D2_addAsset_ecrit_par_insere_et_plus_par_concat",
      s.count(nl("setClips(dzIns.clips);")) == 1
      and s.count(nl("setClips(clipsRef.current.concat(dzTw&&dzTw.clip?[dzNeuf,dzTw.clip]:[dzNeuf]));")) == 0)
```

et vérifier que le harnais [3-bis] (qui EXÉCUTE `addAsset` sous node avec des bouchons) reçoit `DzTracks.insere` : il joue `DzTracks` réel → le mode « ecraser » d'un ajout sur une piste vide rend le même résultat qu'avant (les lignes existantes `add_*` restent vertes ; si l'une rougit, c'est que `dzmInsere` ne rend pas `srcIn:0` ou pose une autre durée — corriger le CŒUR, pas le banc).

- [ ] **Étape 4 : rejouer la chaîne, sonde dzcout, douze bancs, preuve à l'écran** (mode « insérer » : poser un clip au milieu de V1 fend et pousse ; « au-dessus » : atterrit sur V2 ; « remplir » après I/U : vitesse affichée dans l'inspecteur). Commit.

### Tâche 7 — D-3 : roll, slip, slide

**Files :** modifier `montage.js`, `patch_bundle_montage.py` (T1…T5), `test_montage_edition.py` (section [2]), `montage.css`.

- [ ] **Étape 1 : banc rouge** (`PROBE`, section [2]) :

```javascript
var K=[{tr:"v1",id:"p1",start:0,end:4,srcIn:0,src:{a:1}},{tr:"v1",id:"p2",start:4,end:8,srcIn:2,src:{a:1}},
       {tr:"v1",id:"p3",start:8,end:10,srcIn:0,src:{a:1}}];
function tri(cs){return cs.filter(function(c){return c.tr==="v1"}).sort(function(a,b){return a.start-b.start})
  .map(function(c){return [c.id,c.start,c.end,c.srcIn]})}
/* slip : bornes fixes, srcIn bouge de -ds×vitesse, borné à [0, srcDur-len] */
out.slip=tri(T.slip(K,"p2",1,{srcDur:10}));
out.slip_borne_bas=tri(T.slip(K,"p2",5,{srcDur:10}));
out.slip_borne_haut=tri(T.slip(K,"p2",-9,{srcDur:10}));
out.slip_vitesse=tri(T.slip(K.map(function(c){return c.id==="p2"?Object.assign({},c,{speed:2}):c}),"p2",1,{srcDur:20}));
/* slide : p2 avance de 1 ; p1 s'allonge, p3 se raccourcit (et son srcIn avance) */
out.slide=tri(T.slide(K,"p2",1));
out.slide_neg=tri(T.slide(K,"p2",-1));
out.slide_borne=tri(T.slide(K,"p2",5));      /* p3 ne descend pas sous 0,3 s */
out.slide_sans_voisin=tri(T.slide(K,"p3",1));
/* roll : la jonction p1|p2 recule de 1 : p1 finit à 3, p2 commence à 3 avec srcIn 1 */
out.roll=tri(T.roll(K,"p1","p2",-1));
out.roll_avant=tri(T.roll(K,"p1","p2",1));
out.roll_borne=tri(T.roll(K,"p1","p2",-9));
out.mou=[T.slip(null,"p2",1,{}).length,T.slide(K,"zz",1).length,T.roll(K,"p1","zz",1).length,
         tri(T.roll(K,"p1","p2",NaN))[0][2]];
out.pur=K[1].srcIn===2&&K[0].end===4;
```

Python :

```python
check("slip_deplace_la_source_sans_bouger_le_clip", D.get("slip") == [["p1",0,4,0],["p2",4,8,1],["p3",8,10,0]], D.get("slip"))
check("slip_borne_bas", D.get("slip_borne_bas")[1] == ["p2",4,8,0])
check("slip_borne_haut", D.get("slip_borne_haut")[1] == ["p2",4,8,6])
check("slip_suit_la_vitesse", D.get("slip_vitesse")[1] == ["p2",4,8,0])
check("slide_les_voisins_compensent", D.get("slide") == [["p1",0,5,0],["p2",5,9,2],["p3",9,10,1]], D.get("slide"))
check("slide_negatif", D.get("slide_neg") == [["p1",0,3,0],["p2",3,7,2],["p3",7,10,0]], D.get("slide_neg"))
check("slide_borne_par_le_voisin_droit", D.get("slide_borne")[2][1] - D.get("slide_borne")[2][2] <= -0.3 + 1e-9 and D.get("slide_borne")[2][2] == 10)
check("slide_sans_voisin_droit_ne_bouge_pas", D.get("slide_sans_voisin") == [["p1",0,4,0],["p2",4,8,2],["p3",8,10,0]])
check("roll_recule", D.get("roll") == [["p1",0,3,0],["p2",3,8,1],["p3",8,10,0]], D.get("roll"))
check("roll_avance", D.get("roll_avant") == [["p1",0,5,0],["p2",5,8,3],["p3",8,10,0]], D.get("roll_avant"))
check("roll_borne_a_0_3_s", D.get("roll_borne")[0][2] == 0.3)
check("trims_entrees_molles", D.get("mou") == [0, 3, 3, 4], D.get("mou"))
check("trims_purs", D.get("pur") is True)
```

- [ ] **Étape 2 : implémenter** :

```javascript
/* ── D-3 : ROLL, SLIP, SLIDE (Resolve : trim contextuel) ──────────────────
   Tout est PUR et relatif à l'ÉTAT DU POINTERDOWN (h0.clips) : le geste
   rejoue `ds` depuis l'origine, jamais depuis l'état précédent (dérive).
   slip  : Alt + glisser le centre — bornes fixes, srcIn -= ds × vitesse ;
   slide : Maj + glisser le centre — le clip bouge, le voisin gauche s'allonge,
           le voisin droit se raccourcit (min 0,3 s) et son srcIn avance ;
   roll  : Alt + glisser le losange de jonction — fin du gauche = début du
           droit = jonction + ds (min 0,3 s de chaque côté), srcIn du droit suit. */
function dzmVoisins(cs,c){
  var g=null,d=null;
  cs.forEach(function(k){if(!k||k.tr!==c.tr||k.id===c.id)return;
    if(Math.abs(Number(k.end)-Number(c.start))<=.1&&(!g||Number(k.end)>Number(g.end)))g=k;
    if(Math.abs(Number(k.start)-Number(c.end))<=.1&&(!d||Number(k.start)<Number(d.start)))d=k});
  return {g:g,d:d}}
function dzmSlip(clips,id,ds,opts){
  var cs=Array.isArray(clips)?clips:[],d=Number(ds);if(!isFinite(d))d=0;
  var sd=Number(opts&&opts.srcDur)||0;
  return cs.map(function(c){
    if(!c||c.id!==id)return c;
    var sp=dzmSpeedNum(c),len=dzmSrcLen(c)*sp,si=(Number(c.srcIn)||0)-d*sp;
    if(si<0)si=0;
    if(sd>0&&si>sd-len)si=Math.max(0,sd-len);
    return Object.assign({},c,{srcIn:dzmR3(si)})})}
function dzmSlide(clips,id,ds){
  var cs=Array.isArray(clips)?clips:[],d=Number(ds);if(!isFinite(d))d=0;
  var c=cs.filter(function(k){return k&&k.id===id})[0];
  if(!c||!d)return cs.slice();
  var v=dzmVoisins(cs,c);
  if(!v.d)return cs.slice();                     /* sans voisin droit : pas un slide */
  var dmax=(Number(v.d.end)-Number(v.d.start))-.3,dmin=v.g?-((Number(v.g.end)-Number(v.g.start))-.3):-Number(c.start);
  d=Math.max(dmin,Math.min(dmax,d));
  return cs.map(function(k){
    if(!k)return k;
    if(k.id===c.id)return Object.assign({},k,{start:dzmR3(Number(k.start)+d),end:dzmR3(Number(k.end)+d)});
    if(v.g&&k.id===v.g.id)return Object.assign({},k,{end:dzmR3(Number(k.end)+d)});
    if(k.id===v.d.id)return Object.assign({},k,{start:dzmR3(Number(k.start)+d),
      srcIn:dzmR3(Math.max(0,(Number(k.srcIn)||0)+d*dzmSpeedNum(k)))});
    return k})}
function dzmRoll(clips,leftId,rightId,ds){
  var cs=Array.isArray(clips)?clips:[],d=Number(ds);if(!isFinite(d))d=0;
  var L=cs.filter(function(k){return k&&k.id===leftId})[0],R=cs.filter(function(k){return k&&k.id===rightId})[0];
  if(!L||!R||!d)return cs.slice();
  var dmin=-((Number(L.end)-Number(L.start))-.3),dmax=(Number(R.end)-Number(R.start))-.3;
  d=Math.max(dmin,Math.min(dmax,d));
  return cs.map(function(k){
    if(!k)return k;
    if(k.id===L.id)return Object.assign({},k,{end:dzmR3(Number(k.end)+d)});
    if(k.id===R.id)return Object.assign({},k,{start:dzmR3(Number(k.start)+d),
      srcIn:dzmR3(Math.max(0,(Number(k.srcIn)||0)+d*dzmSpeedNum(k)))});
    return k})}
```

Exports : `slip:dzmSlip,slide:dzmSlide,roll:dzmRoll,voisins:dzmVoisins,`.

- [ ] **Étape 3 : sections** :

```python
# ── T1 (D-3) : les modificateurs sont lus au pointerdown ───────────────────
A_T1 = "var x0=e.clientX,s0=c.start,e0=c.end,moved=!1,tgt=e.currentTarget;"
R_T1 = (A_T1 + "\n"
        '    var dzSlip=!!e.altKey&&edge==="m",dzSlide=!!e.shiftKey&&!e.altKey&&edge==="m";\n'
        "    var dzSd=Number(c.srcDur)||0;")   /* 0 = borne haute inconnue : MESURÉ, aucun cache de durée de source par clip n'existe (dzmSrcDurOr ne sert qu'à l'ajout) ; le rendu borne au disponible */

# ── T2 (D-3) : slip et slide rejouent depuis h0, avant la branche historique ─
A_T2 = "      snapAt=null;\n      var w=0,delta=0;"
R_T2 = ("      snapAt=null;\n"
        "      if(dzSlip){setClips(DzTracks.slip(h0.clips,c.id,ds,{srcDur:dzSd}));return}\n"
        "      if(dzSlide){var dzNs=doSnap(s0+ds);setClips(DzTracks.slide(h0.clips,c.id,dzNs-s0));setSnapT(snapAt);return}\n"
        "      var w=0,delta=0;")

# ── T3 (D-3) : roll sur le losange de jonction avec Alt ────────────────────
A_T3 = "onPointerDown:function(e){transSpanDown(e,j2.right,-1,j2.t)}}),"
R_T3 = "onPointerDown:function(e){if(e.altKey){dzRollDown(e,j2);return}transSpanDown(e,j2.right,-1,j2.t)}}),"

# ── T4 (D-3) : le geste de roll, à côté de transSpanDown ───────────────────
A_T4 = "function transSpanDown(e,jc,edge,t){"
R_T4 = ("function dzRollDown(e,j2){\n"
        "    e.stopPropagation();e.preventDefault();\n"
        "    var tgt=e.currentTarget,span=tgt.parentElement,lane=span?span.parentElement:null;\n"
        "    if(!lane)return;\n"
        "    if(trackStRef.current[j2.right.tr]&&trackStRef.current[j2.right.tr].l)return;\n"
        "    try{tgt.setPointerCapture&&tgt.setPointerCapture(e.pointerId)}catch(_c){}\n"
        "    var pxPerS=Math.max(1,lane.getBoundingClientRect().width)/durRef.current;\n"
        "    var x0=e.clientX,h0=dzmHistHost(),moved=!1;\n"
        "    transHoverShow(j2.t,\"roll\");\n"
        "    function mv(ev){var ds=(ev.clientX-x0)/pxPerS;\n"
        "      if(Math.abs(ev.clientX-x0)>3)moved=!0;if(!moved)return;\n"
        "      transHoverShow(j2.t,\"roll \"+(ds>=0?\"+\":\"\")+ds.toFixed(2)+\" s\");\n"
        "      setClips(DzTracks.roll(h0.clips,j2.left.id,j2.right.id,ds))}\n"
        "    function up(){tgt.removeEventListener(\"pointermove\",mv);tgt.removeEventListener(\"pointerup\",up);\n"
        "      transHoverHide();if(moved){setDirty(!0);pushHistory(h0)}}\n"
        "    tgt.addEventListener(\"pointermove\",mv);tgt.addEventListener(\"pointerup\",up)}\n"
        "  function transSpanDown(e,jc,edge,t){")

# ── T5 (D-3) : le titre des clips dit les trois gestes ─────────────────────
A_T5 = '" — bords : rogner / allonger · centre : déplacer"'
R_T5 = '" — bords : rogner / allonger · centre : déplacer · Alt+centre : slip · Maj+centre : slide · Alt+losange : roll"'
```

**MESURÉ le 21/09** : `transHoverHide()` existe (bloc sonvfx l. 3098, 1 occurrence dans le bundle) ; `DzTracks.srcKey` et `srcDurOr(kind,srcDur,v)` existent mais AUCUN cache de durée de source par clip : la borne haute du slip est donc inconnue à l'écran (0 = sans borne), écart assumé et daté dans le design (le rendu borne la fenêtre au disponible). `seekTo` est `var seekTo=x.useCallback(function(p){…},[])` (1 occurrence) ; `svmTcFF` vit dans le bloc sonvfx (même scope module, 7 occurrences) et n'est appelé qu'au rendu des composants — le shim node ne l'exécute pas ; `ovPicker(),` : 1 occurrence ; `selRef` : 28.

- [ ] **Étape 4 : CSS** : `.dzsvm .svm-clip[data-slip]{cursor:col-resize}` n'est pas nécessaire (le curseur change par `body.dzm-tbdrag` ? non) — laisser le curseur, le titre suffit ; **écart assumé et daté** dans le design (D-3 : « curseur contextuel non livré »).

- [ ] **Étape 5 : chaîne, sonde, bancs, preuve à l'écran** (Alt+glisser un plan V1 : sa vignette de début change, ses bornes non ; Maj+glisser : les voisins compensent ; Alt sur un losange : la coupe glisse). Commit.

### Tâche 8 — D-5 : marqueurs et index

**Files :** `montage.js`, `patch_bundle_montage.py` (K1…K6), `montage.css`, `montage_service.py`, `test_montage_edition.py` [3], `test_montage_projets.py`.

- [ ] **Étape 1 : banc rouge** :

```javascript
var M=[];
M=T.markerAdd(M,2.004,{title:"intro"}); M=T.markerAdd(M,7,{color:"rouge",title:"b"}); M=T.markerAdd(M,4,{});
out.mk_liste=M.map(function(m){return [m.t,m.color,m.title]});
out.mk_ids_uniques=new Set(M.map(function(m){return m.id})).size===3;
out.mk_toggle=T.markerAdd(M,2.1,{}).length;             /* ≤ 0,15 s : retiré, pas doublé */
out.mk_remove=T.markerRemove(M,M[1].id).length;
out.mk_next=[T.markerNext(M,2,1),T.markerNext(M,2,-1),T.markerNext(M,9,1),T.markerNext(M,0,-1)];
out.mk_from=T.markersFrom([{t:"3",color:"zz",title:5},{t:-1},"x",{t:1.5,color:"bleu",title:"ok",note:"n"}]).map(function(m){return [m.t,m.color,m.title,m.note]});
out.mk_colors=T.MARKER_COLORS.map(function(c){return c[0]});
out.mk_pur=M.length===3;
```

Python : `mk_liste == [[2.004,"or","intro"],[4,"or",""],[7,"rouge","b"]]` (trié par t), ids uniques, toggle → 2, remove → 2, `mk_next == [4,null,null,null]`, `mk_from == [[1.5,"bleu","ok","n"],[3,"or","5",""]]`, `mk_colors == ["or","rouge","vert","bleu","violet","cyan"]`, pur.

- [ ] **Étape 2 : implémenter** :

```javascript
/* ── D-5 : MARQUEURS — {id, t, color, title, note} sur la règle, index ────── */
var DZM_MARKER_COLORS=[["or","#f0b429"],["rouge","#e5484d"],["vert","#46a758"],
  ["bleu","#3e8be2"],["violet","#8e4ec6"],["cyan","#12a594"]];
var DZM_MARKER_EPS=.15;
function dzmMarkerColor(c){return DZM_MARKER_COLORS.some(function(o){return o[0]===c})?c:"or"}
function dzmMarkerId(ms){var n=1,id;do{id="m"+n++}while((ms||[]).some(function(m){return m&&m.id===id}));return id}
function dzmMarkersSort(ms){return ms.slice().sort(function(a,b){return a.t-b.t})}
function dzmMarkerAdd(ms,t,o){
  var l=Array.isArray(ms)?ms:[],v=Number(t);if(!isFinite(v)||v<0)return l.slice();
  var near=l.filter(function(m){return m&&Math.abs(Number(m.t)-v)<=DZM_MARKER_EPS})[0];
  if(near&&!(o&&o.force))return l.filter(function(m){return m!==near});
  var m={id:dzmMarkerId(l),t:dzmR3(v),color:dzmMarkerColor(o&&o.color),
    title:String((o&&o.title)||""),note:String((o&&o.note)||"")};
  return dzmMarkersSort(l.concat([m]))}
function dzmMarkerRemove(ms,id){return (Array.isArray(ms)?ms:[]).filter(function(m){return !m||m.id!==id})}
function dzmMarkerNext(ms,t,dir){
  var l=dzmMarkersSort((Array.isArray(ms)?ms:[]).filter(Boolean)),v=Number(t)||0,i;
  if(dir>=0){for(i=0;i<l.length;i++)if(l[i].t>v+1e-6)return l[i].t}
  else{for(i=l.length-1;i>=0;i--)if(l[i].t<v-1e-6)return l[i].t}
  return null}
function dzmMarkersFrom(v){
  var out=[];
  (Array.isArray(v)?v:[]).forEach(function(m){
    if(!m||typeof m!=="object")return;
    var t=Number(m.t);if(!isFinite(t)||t<0)return;
    out.push({id:dzmMarkerId(out),t:dzmR3(t),color:dzmMarkerColor(m.color),
      title:m.title==null?"":String(m.title),note:m.note==null?"":String(m.note)})});
  return dzmMarkersSort(out)}
function DzmMarkers(o){
  var ms=Array.isArray(o&&o.markers)?o.markers:[],d=Number(o&&o.dur)||1,go=o&&o.onSeek;
  return ms.map(function(m){
    var hex=(DZM_MARKER_COLORS.filter(function(c){return c[0]===m.color})[0]||DZM_MARKER_COLORS[0])[1];
    return r.jsx("button",{className:"dzm-mk","aria-label":"Marqueur "+svmTcFF(m.t)+(m.title?" — "+m.title:""),
      title:(m.title||"marqueur")+" · "+svmTcFF(m.t)+(m.note?"\n"+m.note:"")+"\nclic : aller · Maj+M à la tête : retirer",
      style:{left:"calc(88px + (100% - 88px) * "+(m.t/d)+")",background:hex},
      onClick:function(){if(go)go(m.t)}},m.id)})}
function DzmMarkerIndex(o){
  var ms=Array.isArray(o&&o.markers)?o.markers:[];
  return r.jsxs("div",{className:"svm-pop dzm-mkidx",style:{top:96},children:[
    r.jsx("div",{className:"svm-poptitle",children:"Marqueurs — "+ms.length}),
    ms.length?ms.map(function(m){
      return r.jsxs("div",{className:"dzm-mkrow",children:[
        r.jsx("button",{className:"svm-fxchip",onClick:function(){o.onSeek&&o.onSeek(m.t)},children:svmTcFF(m.t)}),
        r.jsx("select",{value:m.color,"aria-label":"Couleur",onChange:function(e){o.onChange&&o.onChange(m.id,{color:e.target.value})},
          children:DZM_MARKER_COLORS.map(function(c){return r.jsx("option",{value:c[0],children:c[0]},c[0])})}),
        r.jsx("input",{value:m.title,placeholder:"titre","aria-label":"Titre",onChange:function(e){o.onChange&&o.onChange(m.id,{title:e.target.value})}}),
        r.jsx("button",{className:"svm-minibtn",title:"Retirer",onClick:function(){o.onRemove&&o.onRemove(m.id)},children:"🗑︎"})]},m.id)}):
      r.jsx("div",{className:"svm-note",children:"Aucun marqueur — Maj+M en pose un à la tête de lecture."}),
    r.jsx("div",{className:"svm-poprow",children:r.jsx("button",{className:"svm-secbtn",onClick:o.onClose,children:"Fermer"})})]})}
```

Exports : `markerAdd:dzmMarkerAdd,markerRemove:dzmMarkerRemove,markerNext:dzmMarkerNext,markersFrom:dzmMarkersFrom,MARKER_COLORS:DZM_MARKER_COLORS,Markers:DzmMarkers,MarkerIndex:DzmMarkerIndex,`. `svmTcFF` est un helper du bloc sonvfx (même scope module : mesuré, la couche l'emploie déjà ? — sinon `DzTracks` reçoit `o.tc` en prop ; le sous-agent mesure `grep -c svmTcFF montage.js`).

CSS : `.dzsvm .dzm-mk{position:absolute;top:2px;width:8px;height:8px;margin-left:-4px;border-radius:2px;border:0;padding:0;cursor:pointer;z-index:4}` · `.dzsvm .dzm-mkrow{display:flex;gap:6px;align-items:center;margin-top:6px}` · `.dzsvm .dzm-mkrow input{flex:1 1 auto;min-width:0}`.

- [ ] **Étape 3 : sections K1…K6** — K1 actions (`marker_toggle` `Maj+M`, `marker_prev` `Ctrl+↑`, `marker_next` `Ctrl+↓`, `marker_index` `Ctrl+M`) après R1 (ancre = la ligne `range_cut` de R_R1) ; K2 dispatch après R2 (`marker_toggle` : `pushHistory();setProj(p→{markers:DzTracks.markerAdd(p.markers,phRef.current,{})})` ; prev/next : `seekTo(t)` si non nul ; index : `setDzMkOn(v=>!v)`) ; K3 état `stDzMk` à côté de E1 (`var stDzMk=x.useState(!1),dzMkOn=…`) ; K4 les marqueurs sur la règle après R3 (`r.jsx(DzTracks.Markers,{markers:proj.markers,dur:dur,onSeek:seekTo}),`) ; K5 la chip « ◆ n » après la chip ripple (ancre : la ligne complète `title:"refermer les trous — …",onClick:function(){setRipple(!ripple)},children:"ripple"}),` → append une chip `svm-toolchip` `children:"◆ "+((proj.markers||[]).length)` qui bascule `dzMkOn`) et le panneau `dzMkOn?r.jsx(DzTracks.MarkerIndex,{markers:proj.markers,onSeek:seekTo,onClose:…,onRemove:…,onChange:…}):null` posé juste après `ovPicker(),` (mesurer l'ancre `ovPicker(),` : 1 attendu) ; K6 save/restore : `markers:(proj.markers||[]),` après la ligne R4 et `markers:DzTracks.markersFrom(d.markers),` après R5. Backend : `_save_record` garde `markers` si liste (max 200 entrées, chaque `{t,color,title,note}` assaini côté client), `GET /project` la resert ; banc projets section [8].

- [ ] **Étape 4 : chaîne, sonde, bancs, preuve** (Maj+M pose une pastille or sur la règle ; Ctrl+↓ y va ; Ctrl+M ouvre l'index, renommer, recharger la page : les marqueurs sont là). Commit.

### Tâche 9 — D-4 : échanger deux plans voisins

**Files :** `montage.js`, `patch_bundle_montage.py` (W1, W2), `test_montage_historique.py` [3].

- [ ] **Étape 1 : banc rouge** : `T.swap(K,"p2",-1)` rend p2 en [0,4[ et p1 en [4,8[ (srcIn conservés) ; `swap(K,"p1",-1)` inchangé ; `swap(K,"p3",1)` inchangé ; `swap(K,"zz",1)` inchangé ; voisin à > 0,1 s (trou) → inchangé ; pur.

- [ ] **Étape 2 : implémenter** :

```javascript
/* ── D-4 : ÉCHANGER un plan avec son voisin de gauche (dir −1) ou de droite ─ */
function dzmSwap(clips,id,dir){
  var cs=Array.isArray(clips)?clips:[],c=cs.filter(function(k){return k&&k.id===id})[0];
  if(!c)return cs.slice();
  var v=dzmVoisins(cs,c),n=dir<0?v.g:v.d;
  if(!n)return cs.slice();
  var a=dir<0?n:c,b=dir<0?c:n;                   /* a précède b */
  var la=Number(a.end)-Number(a.start),lb=Number(b.end)-Number(b.start),s=Number(a.start);
  return cs.map(function(k){
    if(k===b)return Object.assign({},k,{start:dzmR3(s),end:dzmR3(s+lb)});
    if(k===a)return Object.assign({},k,{start:dzmR3(s+lb),end:dzmR3(s+lb+la)});
    return k})}
```

Export `swap:dzmSwap`. Sections : W1 actions `swap_left` `Ctrl+←`, `swap_right` `Ctrl+→` (section Montage, après la ligne `marker_index` de K1 ; les touches `←`/`→` sous Ctrl sont libres : `svmComboOfEvent` rend `Ctrl+←`) ; W2 dispatch : `if(id==="swap_left"||id==="swap_right"){var dzC=clipsRef.current.filter(function(k){return k.id===selRef.current})[0];if(!dzC){fireNote("Échanger : sélectionnez d'abord un plan.");return}pushHistory();setClips(DzTracks.swap(clipsRef.current,dzC.id,id==="swap_left"?-1:1));setDirty(!0);return}` (`selRef` : mesuré, existe — `delClip` le lit).

- [ ] **Étape 3 : chaîne, sonde, bancs, preuve** (Ctrl+← sur plan_02 : il passe devant plan_01). Commit.

### Tâche 10 — clôture des lots : mutations, comptes, documents

- [ ] **Étape 1 : campagne de mutations** `backend/tests/mutations_montage_l0l1.py` (modèle : `mutations_cout_pastille.py`, liste de remplacements sur COPIES, restauration vérifiée par sha256) — au moins douze mutations, une par fonction pure (histApply ignore `dur` ; rangeSet ne pousse pas `out` ; insere « inserer » ne pousse pas ; slip ne borne pas ; slide sans voisin bouge ; roll sans borne ; markerAdd doublonne ; swap sur trou ; …) : chacune doit rougir AU MOINS une ligne nommée, la table des comptes MESURÉS dans la docstring.
- [ ] **Étape 2 : compte de référence** du banc bundle et des deux bancs neufs dans leurs docstrings ; `repatch_all --list` complet ; `node --check` ; `git hash-object` du bundle noté dans le commit.
- [ ] **Étape 3 : le design** gagne une colonne « exécuté le » pour D-0, D-1, D-11, D-2, D-3, D-5, D-4, avec les écarts assumés (curseur contextuel de D-3, pas de trim en lecture, pas d'annotations).
- [ ] **Étape 4 : commit, push, rapport** : ce qui est livré, ce qui est mesuré, ce qui reste (le déploiement vers `%LOCALAPPDATA%` et la relance du backend sont à l'utilisateur — voir `deploiement-localappdata-verification`).

---

## Relecture du plan (faite avant remise)

- Couverture : D-0 (T1–T2), D-1 (T3), D-11 (T4), D-2 (T5–T6), D-3 (T7), D-5 (T8), D-4 (T9) — les sept décisions des lots L0 et L1. Aucune autre décision n'est touchée.
- Ancres : toutes les ancres citées ont été comptées à 1 dans le bundle livré le 21/09/2026 (script de l'étape 1 de la tâche 2, plus `ovPicker(),`, `function transHoverHide`, `var seekTo`, `var dzTs=`) ; chaque tâche relance `--check` AVANT d'écrire.
- Cohérence des noms : `dzmHistHost` (hôte, H1), `DzTracks.histSnap/histApply` (T1), `dzProjRef` (H1, lu par R2/E3), `dzModeRef` (E1, lu par E3), `dzmVoisins` (T7, lu par T9), `dzmRangeFrom` (T4, lu par T5 « remplir » et DzmModeBar).
- Le bloc `sonvfx` n'est jamais réécrit : toute section vise une ancre du bundle et s'ajoute en queue de `PATCHES` ; `guard_downstream` et la sonde dzcout restent les deux gardes.
