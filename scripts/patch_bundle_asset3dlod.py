# -*- coding: utf-8 -*-
# scripts/patch_bundle_asset3dlod.py
"""Patcher assert-gardé : zone « LOD » dans la carte 3D du hub, sous DzOptimize (T105, plan-moteurs-3d T3).

BASELINE : bundle versionné de main après T104 (c2a1f7f3) — la plupart des maillons récents (srclbl, libsons…) n'ont
pas de .bak sur cette machine, le bundle commis fait foi. Backup dédié : .js.bak_asset3dlod (état juste avant CE
patch), créé au premier passage. Au prochain bump de version : archiver .bak_version HORS de frontend/dist/assets
puis relancer patch_bundle_version.py seul — `version` reste le DERNIER maillon.

DzLod (+ DzLodNum) est DÉFINI juste avant DzOptFmt et GREFFÉ dans la colonne de DzOptimize, juste après sa rangée
de boutons (ancres uniques, mesurées le 06/10) : un select d'usage rempli par GET /api/assets/3d/{sh}/lod (le
`pourquoi` du budget en infobulle), le bouton « LOD » (POST), une ligne par niveau (triangles, IoU min, écart de
normales, « non mesuré » dit), et « Archive LOD » vers /lod-zip. Les budgets viennent du SERVEUR : rien n'est
recopié dans le bundle.

Lecture et écriture en OCTETS (le mode texte aplatit les CRLF — mémoire du 07/09/2026).

Run : python scripts/patch_bundle_asset3dlod.py [--check] [--force-unchained]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_asset3dlod")
TAG = "asset3dlod"

MARKER = "function DzLod("
MARKER_ATTENDU = 1

BTN = ('style:{fontSize:11,padding:"4px 8px",borderRadius:6,cursor:"pointer",'
       'background:"var(--surface-2)",border:"1px solid var(--stroke)",color:"var(--ink)"}')
LIEN = ('style:{fontSize:11,padding:"4px 8px",borderRadius:6,textDecoration:"none",'
        'background:"var(--surface-2)",border:"1px solid var(--stroke)",color:"var(--cyan)"}')

ANCRE_DEF = 'function DzOptFmt(n){'
ANCRE_ZONE = 'children:cmp?"▣ Simple":"⇆ Comparer"},"cp"):null]},"row"),'

DZ_LOD = (
    'function DzLodNum(v){return v==null?"non mesuré":Number(v).toFixed(3)}'
    'function DzLod({sh}){'
    'var DS=x.useState(null),d0=DS[0],setD0=DS[1],'
    'BS=x.useState(!1),busy=BS[0],setBusy=BS[1],'
    'US=x.useState("pc"),us=US[0],setUs=US[1],'
    'ES=x.useState(""),err=ES[0],setErr=ES[1];'
    'x.useEffect(function(){var on=!0;'
    'fetch("/api/assets/3d/"+sh+"/lod")'
    '.then(function(r2){return r2.ok?r2.json():null})'
    '.then(function(j){on&&j&&setD0(j)}).catch(function(){});'
    'return function(){on=!1}},[sh]);'
    'function run(){if(busy)return;setBusy(!0);setErr("");'
    'fetch("/api/assets/3d/"+sh+"/lod",{method:"POST",'
    'headers:{"Content-Type":"application/json"},body:JSON.stringify({usage:us})})'
    '.then(function(r2){return r2.json().then(function(j){return{ok:r2.ok,j:j}})'
    '.catch(function(){return{ok:r2.ok,j:{}}})})'
    '.then(function(z){setBusy(!1);'
    'if(!z.ok){setErr(String((z.j&&z.j.detail)||"échec de la chaîne LOD"));return}'
    'setD0(function(o){return Object.assign({},o||{},{chaine:z.j})})})'
    '.catch(function(e2){setBusy(!1);setErr(String(e2&&e2.message||e2))})}'
    'var bud=(d0&&d0.budgets)||[],ch=d0&&d0.chaine,'
    'bu=bud.filter(function(b){return b.id===us})[0];'
    'return r.jsxs("div",{style:{display:"flex",flexDirection:"column",gap:4,marginTop:4},children:['
    'r.jsxs("div",{style:{display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"},children:['
    'r.jsx("span",{style:{fontSize:11,color:"var(--ink-soft)"},children:"LOD"},"lb"),'
    'r.jsx("select",{value:us,title:bu?bu.pourquoi+" ("+bu.niveaux.join(" / ")+" tris)":"",'
    'onChange:function(ev){setUs(ev.target.value)},' + BTN + ','
    'children:bud.map(function(b){return r.jsx("option",{value:b.id,children:b.label},b.id)})},"sel"),'
    'r.jsx("button",{onClick:run,disabled:busy,title:"Chaîne de LOD locale et gratuite (gltfpack) depuis le maillage '
    'courant ; la perte de chaque niveau est mesurée contre le LOD0",' + BTN + ','
    'children:busy?"Chaîne…":"⛰ LOD"},"go"),'
    'ch?r.jsx("a",{href:"/api/assets/3d/"+sh+"/lod-zip",download:!0,'
    'title:"Les GLB _LODx, lod.json et le LISEZMOI (Unity, Godot)",' + LIEN + ','
    'children:"↓ Archive LOD"},"dl"):null]},"row"),'
    'err?r.jsx("div",{style:{fontSize:11,color:"var(--red)"},children:err},"er"):null,'
    'ch?r.jsx("div",{style:{fontSize:10,fontFamily:"var(--f-mono)",color:"var(--ink-strong)"},'
    'children:ch.niveaux.map(function(n){var p=n.perte||{};'
    'return r.jsxs("div",{title:p.mesure===!1?String(p.raison||""):"IoU : silhouettes contre le LOD0 · Δn : '
    'part de l\'aire dont la normale a changé",children:["LOD",String(n.niveau)," · ",DzOptFmt(n.tris)," tris",'
    'n.niveau?" · IoU "+DzLodNum(p.iou_min)+" · Δn "+DzLodNum(p.ecart_normales):" · source",'
    'n.aggressive?" · agressif":""]},"n"+n.niveau)})},"st"):null]},"lod")}')

GREFFE = 'r.jsx(DzLod,{sh:sh},"lod"+sh),'

# (tag, ancre, remplacement, occurrences attendues)
PATCHES = [
    ("D1-def", ANCRE_DEF, DZ_LOD + ANCRE_DEF, 1),
    ("D2-zone", ANCRE_ZONE, ANCRE_ZONE + GREFFE, 1),
]

SPEC_CHAR_DELTA = 3055
SPEC_BYTE_DELTA = 3076

# les voisins de l'ancre et les maillons de queue
SONDE_AMONT = [
    ("optimize", "function DzOptimize({sh}){", 1),
    ("optimize-use", "r.jsx(DzOptimize", 1),
    ("srclbl", "Object.assign(__dzSrcLbl,", 2),
    ("libsons", "dz-libsons", 1),
]


def lire(p):
    """Le mode texte MENT sur les fins de ligne (mémoire du 07/09/2026) : on lit et on écrit en OCTETS."""
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
            raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans {src.name} : double application "
                             "refusee.")
        sonder(s)
        for tag, a, _, n in PATCHES:
            c = s.count(a)
            if c != n:
                raise SystemExit(f"[{tag}] anchor count={c} (want {n}) dans {src.name}.")
        print(f"[{TAG}] applicable sur {src.name} ({len(PATCHES)} ancres OK, {len(SONDE_AMONT)} sondes ; "
              f"delta +{dc} car / +{db} o)")
        return

    if not BAK.exists():
        if MARKER in s:
            raise SystemExit(f"[{TAG}] marqueur present sans {BAK.name} : etat ambigu, abandon sans rien ecrire.")
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK.name)
    else:
        shutil.copy2(BAK, BUNDLE)
        s, bom = lire(BUNDLE)
        print("restore <-", BAK.name)
    avant = BUNDLE.read_bytes()
    sonder(s)
    if MARKER in s:
        raise SystemExit(f"[{TAG}] backup empoisonne (marqueur present). Aborting.")
    for tag, a, rp, n in PATCHES:
        s = apply(s, a, rp, tag, n)
    ecrire(BUNDLE, s, bom)

    apres = BUNDLE.read_bytes()
    problemes = []
    if len(apres) != len(avant) + db:
        problemes.append(f"taille {len(apres)} o, attendu {len(avant) + db}")
    if apres.count(b"\r\n") != avant.count(b"\r\n") or apres.count(b"\n") != apres.count(b"\r\n"):
        problemes.append("fins de ligne changees")
    if s.count(MARKER) != MARKER_ATTENDU or s.count("r.jsx(DzLod,") != 1:
        problemes.append(f"marqueur x{s.count(MARKER)} / greffe x{s.count('r.jsx(DzLod,')} (want 1/1)")
    if problemes:
        shutil.copy2(BAK, BUNDLE)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  " + "\n  ".join(problemes))
    print(f"OK - {TAG} applique ({len(avant)} -> {len(apres)} o, +{db}).")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
