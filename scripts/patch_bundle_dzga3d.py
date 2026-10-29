# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzga3d.py
"""Maillon de queue : l'écran Game Assets 3D en français ET en anglais (t376, lot « Game Assets : finitions » ;
constat de la PR #504 traité à la demande de l'utilisateur le 29/10/2026).
Avant : le formulaire, les cartes et le graphe de `DzGameAssets` étaient en anglais en dur (« Source image »,
« Engine », « Generate 3D »…), la rangée Optimiser / LOD / Textures (`DzOptimize`, `DzLod`, `DzTex`) et la boîte
d'impression 3D (`__dzPrint3d`) en français en dur, quelle que soit la langue choisie.
Chaque texte affiché passe par dzT (frontend/shared/i18n/ga3d.json, clés ga3d.*). Le français de `DzOptimize`,
`DzLod`, `DzTex` et `__dzPrint3d` est repris À L'IDENTIQUE (leurs bancs, joués sous node, le lisent) ; celui de
`DzGameAssets` est neuf. Restent tels quels : les noms propres (Game Assets, GLB, LOD, Blender/Web, Unity/Unreal,
AR/USD), les valeurs envoyées au serveur, et les textes que le SERVEUR renvoie (étapes d'un job, motifs de refus,
libellés des budgets LOD), qui ne sont pas du ressort de l'écran.

Les paires sont des remplacements exacts, chacun unique dans le bundle. Le MARKER /*dzga3d*/ précède le titre de
l'écran. Aucun état React neuf, aucune confirmation neuve (les deux confirmations existantes gardent leur forme).

Maillon de QUEUE, APRÈS dzpose (dont il sonde le marqueur) ; il garde un .js.bak_dzga3d le temps de l'écriture puis le
SUPPRIME. Son INVERSE est `avant_dzga3d` dans backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE
de `avant_dzpose`. Lecture et écriture en OCTETS (le bundle est en CRLF) ; aucune paire ne contient de fin de ligne ;
les ancres sont hors des couches __DZ_*_BEGIN__. DÉFAIRE le maillon AVANT de changer ses paires.
Banc : backend/tests/test_ga3d_traduction_ecran.py.
Run : python scripts/patch_bundle_dzga3d.py [--check]
"""
import pathlib
import re
import shutil
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzga3d")
TAG = "dzga3d"
MARKER = "/*dzga3d*/"
MARKER_ATTENDU = 1
CONFIRMER = "await window.__dzDialogue.confirmer("

SONDE_AMONT = [
    ("dzpose", "/*dzpose*/", 1),
    ("ecran", "function DzGameAssets({variant:e}){", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
    ("dialogue", CONFIRMER, 30),
]


def T(k, v=None):
    """dzT("k") ou dzT("k",{…}) écrit dans le bundle."""
    return f'dzT("{k}")' if v is None else f'dzT("{k}",{{{v}}})'


PAIRES = [
    # ── DzGameAssets : en-tête et liste vide ──
    ('r.jsx("h2",{style:{color:"var(--ink-strong)",marginBottom:4},children:"Game Assets · 3D"})',
     MARKER + 'r.jsx("h2",{style:{color:"var(--ink-strong)",marginBottom:4},children:"Game Assets · 3D"})'),
    ('children:"Image → 3D model (Tripo · Hunyuan3D · TRELLIS · Rodin · TripoSR). Export GLB/FBX/OBJ/STL/USDZ. '
     'Each view shot is downloadable."', "children:" + T("ga3d.ecran.intro")),
    ('children:"No 3D assets yet — pick an image and Generate."', "children:" + T("ga3d.ecran.vide")),
    # ── formulaire ──
    ('r.jsx(O,{label:"Source image",children:picker})', 'r.jsx(O,{label:' + T("ga3d.form.source") + ',children:picker})'),
    ('r.jsx(O,{label:"Engine",children:', 'r.jsx(O,{label:' + T("ga3d.form.moteur") + ',children:'),
    ('children:"Add a Meshy API key in Settings to use Meshy 6."', "children:" + T("ga3d.form.meshy_cle")),
    ('r.jsx(O,{label:"Subject (optional)",children:r.jsx(le,{value:p.subject,placeholder:"e.g. a knight character",',
     'r.jsx(O,{label:' + T("ga3d.form.sujet") + ',children:r.jsx(le,{value:p.subject,placeholder:'
     + T("ga3d.form.sujet_exemple") + ','),
    ('r.jsx(O,{label:"Textures",children:r.jsx(Ze,{checked:p.textures,',
     'r.jsx(O,{label:' + T("ga3d.form.textures") + ',children:r.jsx(Ze,{checked:p.textures,'),
    ('r.jsx(O,{label:"Multi-view boost",', 'r.jsx(O,{label:' + T("ga3d.form.vues_multiples") + ','),
    ('r.jsx(O,{label:"Views: "+p.views,', 'r.jsx(O,{label:' + T("ga3d.form.nb_vues", "n:p.views") + ','),
    ('r.jsx(O,{label:"Export formats (GLB always)",', 'r.jsx(O,{label:' + T("ga3d.form.formats") + ','),
    ('["obj","Universal"],["stl","3D printing"]',
     '["obj",' + T("ga3d.format.obj") + '],["stl",' + T("ga3d.format.stl") + ']'),
    ('children:busy?"Generating…":"Generate 3D"}', 'children:busy?' + T("ga3d.form.generation") + ':'
     + T("ga3d.form.generer") + '}'),
    ('alert("Generation 3D refusee : "+String((x2.j&&(x2.j.detail||x2.j.error))||"erreur serveur"))',
     'alert(' + T("ga3d.form.refus", 'detail:String((x2.j&&(x2.j.detail||x2.j.error))||' + T("ga3d.form.erreur_serveur") + ')')
     + ')'),
    ('alert("Generation 3D : "+String((err&&err.message)||err))',
     'alert(' + T("ga3d.form.echec_reseau", "detail:String((err&&err.message)||err)") + ')'),
    # ── cartes ──
    ('alert("Shot enregistré dans la Library (onglet Images) : "+j.filename)',
     'alert(' + T("ga3d.carte.vue_enregistree", "nom:j.filename") + ')'),
    ('children:fail?"failed":done?"done":"generating…"}', 'children:fail?' + T("ga3d.carte.etat_echec") + ':done?'
     + T("ga3d.carte.etat_fait") + ':' + T("ga3d.carte.etat_cours") + '}'),
    ('saisir("Renommer ce rendu 3D :",{titre:"Renommer",valeur:z.title||("3D · "+sh),ok:"Renommer"});'
     'if(nn){D.renameJob(z.job_id,nn).then(refresh)}},title:"Renommer",',
     'saisir(' + T("ga3d.carte.renommer_question") + ',{titre:' + T("ga3d.carte.renommer") + ',valeur:z.title||("3D · "+sh),ok:'
     + T("ga3d.carte.renommer") + '});if(nn){D.renameJob(z.job_id,nn).then(refresh)}},title:' + T("ga3d.carte.renommer") + ','),
    ('confirmer("Supprimer définitivement ce rendu 3D ?")){D.deleteJob(z.job_id).then(refresh)}},title:"Supprimer",',
     'confirmer(' + T("ga3d.carte.supprimer_question") + ')){D.deleteJob(z.job_id).then(refresh)}},title:'
     + T("ga3d.carte.supprimer") + ','),
    ('__dzGlT("dz-media-image","▣ Poster","▣"):__dzGlT("dz-lab3d-rotation","▶ Rotate","▶")',
     '__dzGlT("dz-media-image","▣ "+' + T("ga3d.carte.affiche") + ',"▣"):__dzGlT("dz-lab3d-rotation","▶ "+'
     + T("ga3d.carte.tourner") + ',"▶")'),
    ('title:"Dossier d\'impression STL + 3MF aux mm réels (assets/print3d) puis ouverture du .3mf dans le slicer — '
     'ElegooSlicer/OrcaSlicer",children:__dzGlT("dz-lab3d-impression-3d","→ Impression 3D","→")',
     'title:' + T("ga3d.carte.impression_aide") + ',children:__dzGlT("dz-lab3d-impression-3d","→ "+'
     + T("ga3d.carte.impression") + ',"→")'),
    ('margin:"4px 0"},children:"Shots"}', 'margin:"4px 0"},children:' + T("ga3d.carte.vues") + '}'),
    ('title:"Download shot",', 'title:' + T("ga3d.carte.telecharger_vue") + ','),
    ('onClick:function(){saveShot(sh,i)},title:"Save to Library"',
     'onClick:function(){saveShot(sh,i)},title:' + T("ga3d.carte.vers_bibliotheque")),
    # ── graphe (vue « canevas ») ──
    ('kind:"img",i:0,label:"Input",', 'kind:"img",i:0,label:' + T("ga3d.graphe.entree") + ','),
    ('kind:"img",i:i,label:"View "+i,', 'kind:"img",i:i,label:' + T("ga3d.graphe.vue", "n:i") + ','),
    ('kind:"resp",label:"Response",', 'kind:"resp",label:' + T("ga3d.graphe.reponse") + ','),
    ('children:n.st==="run"?"…generating":"waiting"}', 'children:n.st==="run"?' + T("ga3d.graphe.generation") + ':'
     + T("ga3d.graphe.attente") + '}'),
    ('download:!0,title:"Download",', 'download:!0,title:' + T("ga3d.graphe.telecharger") + ','),
    ('onClick:function(){saveShot(sh,n.i)},title:"Save to Library"',
     'onClick:function(){saveShot(sh,n.i)},title:' + T("ga3d.carte.vers_bibliotheque")),
    ('children:st==="failed"?"failed":"…"}', 'children:st==="failed"?' + T("ga3d.carte.etat_echec") + ':"…"}'),
    ('__dzGlT("dz-action-retour","← New asset","←")', '__dzGlT("dz-action-retour","← "+' + T("ga3d.graphe.nouveau") + ',"←")'),
    ('children:"Pipeline · "+(activeJob.engine||"")', 'children:' + T("ga3d.graphe.titre", 'moteur:activeJob.engine||""')),
    # ── DzOptimize ──
    ('children:"Optimize"},"lb")', 'children:' + T("ga3d.opt.titre") + '},"lb")'),
    ('var opts=[["micro","Micro (500)"],["small","Small (1k)"],["prop","Prop (2.5k)"],["detailed","Detailed (5k)"],'
     '["game","Game Ready (10k)"],["balanced","Balanced (25k)"],["high","High (50k)"],["ultra","Ultra (100k)"]];',
     'var opts=[' + ",".join(f'["{k}",' + T(f"ga3d.opt.{k}") + ']' for k in
                             ("micro", "small", "prop", "detailed", "game", "balanced", "high", "ultra")) + '];'),
    ('setErr(String((x2.j&&x2.j.detail)||"échec optimisation"))',
     'setErr(String((x2.j&&x2.j.detail)||' + T("ga3d.opt.echec") + '))'),
    ('children:busy?"Optimisation…":__dzGlT("dz-lab3d-optimiser","⚙ Optimiser","⚙")',
     'children:busy?' + T("ga3d.opt.en_cours") + ':__dzGlT("dz-lab3d-optimiser","⚙ "+' + T("ga3d.opt.optimiser") + ',"⚙")'),
    ('__dzGlT("dz-action-telecharger","↓ GLB optimisé","↓")', '__dzGlT("dz-action-telecharger","↓ "+' + T("ga3d.opt.glb") + ',"↓")'),
    ('cmp?__dzGlT("dz-action-comparer","▣ Simple","▣"):__dzGlT("dz-action-comparer","⇆ Comparer","⇆")',
     'cmp?__dzGlT("dz-action-comparer","▣ "+' + T("ga3d.opt.simple") + ',"▣"):__dzGlT("dz-action-comparer","⇆ "+'
     + T("ga3d.opt.comparer") + ',"⇆")'),
    ('children:"Original · "+DzOptFmt(info.before.tris)+" tris"}',
     'children:' + T("ga3d.opt.original", "n:DzOptFmt(info.before.tris)") + '}'),
    ('children:"Optimisé · "+DzOptFmt(info.after.tris)+" tris"}',
     'children:' + T("ga3d.opt.optimise", "n:DzOptFmt(info.after.tris)") + '}'),
    # ── DzLod ──
    ('setErr(String((z.j&&z.j.detail)||"échec de la chaîne LOD"))',
     'setErr(String((z.j&&z.j.detail)||' + T("ga3d.lod.echec") + '))'),
    ('title:"Chaîne de LOD locale et gratuite (gltfpack) depuis le maillage courant ; la perte de chaque niveau est '
     'mesurée contre le LOD0",', 'title:' + T("ga3d.lod.aide") + ','),
    ('children:busy?"Chaîne…":__dzGlT("dz-lab3d-lod","⛰ LOD","⛰")',
     'children:busy?' + T("ga3d.lod.en_cours") + ':__dzGlT("dz-lab3d-lod","⛰ LOD","⛰")'),
    ('title:"Les GLB _LODx, lod.json et le LISEZMOI (Unity, Godot)",', 'title:' + T("ga3d.lod.archive_aide") + ','),
    ('__dzGlT("dz-action-telecharger","↓ Archive LOD","↓")', '__dzGlT("dz-action-telecharger","↓ "+' + T("ga3d.lod.archive") + ',"↓")'),
    ('"IoU : silhouettes contre le LOD0 · Δn : part de l\'aire dont la normale a changé"', T("ga3d.lod.mesure_aide")),
    (':" · source",n.aggressive?" · agressif":"",n.cible_tenue===!1?" · cible "+DzOptFmt(n.cible)+" non tenue":""',
     ':' + T("ga3d.lod.niveau_source") + ',n.aggressive?' + T("ga3d.lod.agressif") + ':"",n.cible_tenue===!1?'
     + T("ga3d.lod.cible_ratee", "n:DzOptFmt(n.cible)") + ':""'),
    # ── DzTex ──
    ('throw new Error(j.detail||"échec de l’export")', 'throw new Error(j.detail||' + T("ga3d.tex.export_rate") + ')'),
    ('children:"Textures : "+err}', 'children:' + T("ga3d.tex.inventaire_refus", "detail:err") + '}'),
    ('children:"Textures"},"lb")', 'children:' + T("ga3d.tex.titre") + '},"lb")'),
    ('title:"Convention de nommage du moteur visé",', 'title:' + T("ga3d.tex.convention") + ','),
    ('title:nus?"Ce maillage ne porte aucune texture : texture-le d’abord":"Archive des textures de "+inv.file+'
     '" renommées pour le moteur, avec le bordereau",',
     'title:nus?' + T("ga3d.tex.nu") + ':' + T("ga3d.tex.archive_aide", "fichier:inv.file") + ','),
    ('children:busy?"Export…":__dzGlT("dz-action-exporter","↓ Textures","↓")',
     'children:busy?' + T("ga3d.tex.en_cours") + ':__dzGlT("dz-action-exporter","↓ "+' + T("ga3d.tex.titre") + ',"↓")'),
    ('title:"Dérivées de la basecolor : cartes de MOTIF, pas un bake de maillage — le bordereau le dit",',
     'title:' + T("ga3d.tex.cuites_aide") + ','),
    ('children:"cuites : "+inv.manquants.join(", ")}', 'children:' + T("ga3d.tex.cuites", 'liste:inv.manquants.join(", ")') + '}'),
    # ── __dzPrint3d (la boîte d'impression 3D) ──
    ('saisir("Taille cible en mm ? (ex. 80 figurine, 250 plateau — la Centauri Carbon 2 imprime 256 mm ; vide = taille '
     'du fichier)",{titre:"Impression 3D",valeur:"80",ok:"Continuer"})',
     'saisir(' + T("ga3d.impr.taille") + ',{titre:' + T("ga3d.impr.titre") + ',valeur:"80",ok:' + T("ga3d.impr.continuer") + '})'),
    ('window.alert("taille en mm invalide")', 'window.alert(' + T("ga3d.impr.taille_invalide") + ')'),
    ('throw new Error((x.d&&x.d.detail)||"export impossible")', 'throw new Error((x.d&&x.d.detail)||' + T("ga3d.impr.export_rate") + ')'),
    ('confirmer("Dossier d\'impression écrit : "+x.d.dossier+" ("+x.d.triangles+" triangles) — ouvrir le .3mf dans le slicer ?")',
     'confirmer(' + T("ga3d.impr.ouvrir_slicer", "dossier:x.d.dossier,n:x.d.triangles") + ')'),
    ('throw new Error(od.detail||"ouverture impossible")', 'throw new Error(od.detail||' + T("ga3d.impr.ouverture_ratee") + ')'),
    ('.catch(function(e){window.alert("Impression 3D : "+String((e&&e.message)||e))})}catch(e){window.alert("Impression 3D : "'
     '+String((e&&e.message)||e))}}',
     '.catch(function(e){window.alert(' + T("ga3d.impr.erreur", "detail:String((e&&e.message)||e)") + ')})}catch(e){'
     'window.alert(' + T("ga3d.impr.erreur", "detail:String((e&&e.message)||e)") + ')}}'),
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
    """L'inverse exact (lu par avant_dzga3d dans _i18n_l1_aide)."""
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
            raise SystemExit(f"[{TAG}] partiellement appliqué — repartir d'avant_dzga3d")
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
            or neuf.count(CONFIRMER) != 30 or neuf.count("function DzGameAssets({variant:e}){") != 1
            or neuf.count("\r\n") != crlf):
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
