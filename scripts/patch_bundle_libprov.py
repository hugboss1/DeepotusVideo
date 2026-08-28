# -*- coding: utf-8 -*-
# scripts/patch_bundle_libprov.py
"""Patcher assert-garde : chips de PROVENANCE de la Bibliotheque.

BASELINE : bundle POST-patch libpicker (dernier maillon en date).
Backup dedie : `.js.bak_libprov`. Position : EN QUEUE, apres libpicker.
Spec : docs/superpowers/plans/2026-08-28-bibliotheque-provenance-envoyer-vers.md

Trois familles de greffes (toutes ADDITIVES) :
  vm (ecran Library) : items images porteurs de `source`/`srcOrigin`
      (l'API les rend depuis library_assets), etat de filtre dzSF,
      reset au changement d'onglet, filtre au calcul de la liste
      (jamais le repli demo quand un filtre est actif), rangee de chips
      `__dzSrcChips` (Images par fonction productrice — prefixe "~" si
      la source n'est connue que par heuristique de nom — , Renders par
      provider deja present sur les items).
  picker (__dzLibPicker) : chips par source dans l'overlay — patchs sur
      le CORPS du picker uniquement, AUCUNE occurrence du token
      __dzLibPicker ajoutee ni retiree (le pin x10 du banc picker tient).

DANGERS : jamais `repatch_all.py --from` sur cette chaine, lancement
SEUL, newline='' partout (CRLF), jamais d'ancre imprimee (console
cp1252).

Run :
    python scripts/patch_bundle_libprov.py              # depot
    python scripts/patch_bundle_libprov.py --check      # n'ecrit rien
    python scripts/patch_bundle_libprov.py --deltas     # affiche les deltas
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "libprov"
MARKER = "__dzSrcChips"
MARKER_ATTENDU = 2      # la definition + l'appel dans vm
CHIPS_ATTENDU = 4       # dzlp-chips : css + html + 2 querySelector

STABLE_PROBES = [
    ("libpicker", "__dzLibPicker", 10),
    ("print3d", "__dzPrint3d", 2),
    ("navrail", "dz_nav_collapsed", 2),
    ("dzdesign", "__dzCatBar", 2),
    ("cardforge-pane", 'src:"/cardforge/"', 1),
    ("vectorlab-pane", 'src:"/vectorlab/"', 1),
]

SPEC_CHAR_DELTA = 2830
SPEC_BYTE_DELTA = 2835

# ── vm : helper de chips (module, juste avant vm) ────────────────────────────
HELPER = (
    'var __dzSrcLbl={generation:"Générateur",retouche:"Retouche",'
    'matieres:"Matières",atelier:"Atelier",cardforge:"Cardforge",'
    'vectorlab:"Vectorlab",figma:"Figma",news:"News",sprites:"Sprite Lab",'
    'assets3d:"Game Assets 3D","import":"Imports",import_url:"Import URL",'
    'inconnu:"Inconnu"};'
    "function __dzSrcChips(o,T,sf,setSf){"
    'if(o!=="Images"&&o!=="Renders")return null;'
    "var lst=T[o]||[],cnt={},sur={};"
    "lst.forEach(function(z){"
    'var k=o==="Images"?String((z&&z.source)||"inconnu")'
    ':String((z&&z.provider)||"");'
    "if(!k)return;cnt[k]=(cnt[k]||0)+1;"
    'if(o!=="Images"||((z&&z.srcOrigin)!=="heuristique"))sur[k]=1});'
    "var ks=Object.keys(cnt).sort();"
    "if(ks.length<2&&!sf)return null;"
    "var mk=function(k,lbl,nb){var on=sf===k;"
    'return r.jsx("button",{onClick:function(){setSf(on&&k!==""?"":k)},'
    'style:{height:22,padding:"0 10px",fontSize:11,borderRadius:11,'
    'cursor:"pointer",border:"1px solid "+(on?"var(--accent,#f0b429)"'
    ':"var(--stroke)"),background:on?"var(--bg-panel-2)":"transparent",'
    'color:on?"var(--ink-strong)":"var(--ink-soft)"},'
    'children:lbl+(nb!=null?" ("+nb+")":"")},"dzc_"+(k||"tout"))};'
    'var chips=[mk("","Tout",lst.length)];'
    "ks.forEach(function(k){"
    'var lbl=o==="Images"?(__dzSrcLbl[k]||k):k;'
    'if(!sur[k])lbl="≈ "+lbl;'
    "chips.push(mk(k,lbl,cnt[k]))});"
    'return r.jsx("div",{"data-dz":"srcchips",style:{display:"flex",gap:6,'
    'flexWrap:"wrap",alignItems:"center",marginBottom:12},children:chips})}'
)

# ── ancres vm (mesurees au bundle post-libpicker) ────────────────────────────
_V1 = 'function vm({variant:e,uploads:t=[],setUploads:n=()=>{}}){'
_V2 = (_V1 + 'const[o,i]=x.useState("Images"),')
_V3 = 'onClick:()=>i(C),style:{height:26,padding:"0 10px",background:o===C?'
_V4 = ',Y=T[o]||[],q=Lfs(Y.length>0?Y:vo[o]);'
_V5 = ('className:"scroll",style:{flex:1,overflowY:"auto",padding:18},'
       'children:[o==="Audio"&&')
_V6 = ('const W=((ne==null?void 0:ne.images)||[]).map(S=>({name:S.filename,'
       'kind:"image",size:go(S.size),date:mo(S.modified)||"on disk",'
       'url:D.imageUrl(S.filename)}));')

# ── ancres picker (corps de __dzLibPicker, tokens sans le marqueur) ──────────
_P1 = ('.dzlp-vide{grid-column:1/-1;color:var(--ink-soft,#8b959f);'
       'font-size:12px;padding:22px}";document.head.appendChild(st)}')
_P2 = '<div class="dzlp-grille"></div>'
_P3 = 'var tout=[];function fermer(){'
_P4 = ('var vus=tout.filter(function(im){return !q'
       '||im.filename.toLowerCase().indexOf(q)>=0});')
_P5 = 'function peindre(){'
_P6 = ');peindre()})'
_P7 = 'cherche.addEventListener("input",peindre);'

CHIPS_CSS = (
    '.dzlp-vide{grid-column:1/-1;color:var(--ink-soft,#8b959f);'
    'font-size:12px;padding:22px}"+'
    '".dzlp-chips{display:flex;gap:6px;flex-wrap:wrap;'
    'padding:10px 14px 0}"+'
    '".dzlp-chip{background:transparent;'
    'border:1px solid var(--stroke,#20262d);border-radius:11px;'
    'color:var(--ink-soft,#8b959f);padding:3px 10px;font-size:11px;'
    'cursor:pointer}"+'
    '".dzlp-chip.on{border-color:var(--cat,var(--accent,#f0b429));'
    'color:var(--ink-strong,#eef2f6);background:var(--bg-panel-2,#171c22)}'
    '";document.head.appendChild(st)}'
)

DZCHIPS_FN = (
    "function dzChips(){"
    'var bar=hote.querySelector(".dzlp-chips");if(!bar)return;'
    "var cnt={};tout.forEach(function(im){"
    'var k=String(im.source||"inconnu");cnt[k]=(cnt[k]||0)+1});'
    "var ks=Object.keys(cnt).sort();"
    'if(ks.length<2){bar.style.display="none";return}'
    'bar.style.display="flex";'
    'var lbl=(typeof __dzSrcLbl!=="undefined")?__dzSrcLbl:{};'
    'bar.innerHTML=[""].concat(ks).map(function(k){'
    "return '<button class=\"dzlp-chip'+(k===srcA?\" on\":\"\")"
    "+'\" data-src=\"'+k+'\">'"
    "+(k?((lbl[k]||k)+\" (\"+cnt[k]+\")\"):(\"Tout (\"+tout.length+\")\"))"
    "+'</button>'}).join(\"\")}"
)

CHIPS_CLICK = (
    'hote.querySelector(".dzlp-chips").addEventListener("click",'
    "function(e){"
    'var b=e.target.closest(".dzlp-chip");if(!b)return;'
    'var v=b.getAttribute("data-src")||"";'
    'srcA=(v===srcA)?"":v;dzChips();peindre()});'
)

PATCHES = [
    # vm — l'ecran Library
    ("V1-helper", _V1, HELPER + _V1),
    ("V2-etat", _V2, _V2 + '[dzSF,dzSFs]=x.useState(""),'),
    ("V3-reset-onglet", _V3,
     'onClick:()=>{i(C);dzSFs("")},style:{height:26,padding:"0 10px",'
     'background:o===C?'),
    ("V4-filtre", _V4,
     ',Y=T[o]||[],dzYf=dzSF?Y.filter(z=>o==="Images"'
     '?String((z&&z.source)||"inconnu")===dzSF'
     ':o==="Renders"?String((z&&z.provider)||"")===dzSF:!0):Y,'
     'q=Lfs(dzSF?dzYf:(Y.length>0?Y:vo[o]));'),
    ("V5-rangée", _V5, _V5.replace(
        'children:[o==="Audio"&&',
        'children:[__dzSrcChips(o,T,dzSF,dzSFs),o==="Audio"&&')),
    ("V6-items-sourcés", _V6, _V6.replace(
        'url:D.imageUrl(S.filename)}));',
        'url:D.imageUrl(S.filename),source:S.source||"inconnu",'
        'srcOrigin:S.source_origin||""}));')),
    # picker — chips dans l'overlay
    ("P1-css", _P1, CHIPS_CSS),
    ("P2-html", _P2, '<div class="dzlp-chips"></div>' + _P2),
    ("P3-etat", _P3, 'var tout=[],srcA="";function fermer(){'),
    ("P4-filtre", _P4,
     "var vus=tout.filter(function(im){return(!q"
     "||im.filename.toLowerCase().indexOf(q)>=0)"
     '&&(!srcA||String(im.source||"inconnu")===srcA)});'),
    ("P5-fn", _P5, DZCHIPS_FN + _P5),
    ("P6-init", _P6, ");dzChips();peindre()})"),
    ("P7-clic", _P7, CHIPS_CLICK + _P7),
]


def deltas():
    dc = sum(len(rp) - len(a) for _t, a, rp in PATCHES)
    db = sum(len(rp.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, rp in PATCHES)
    return dc, db


def check_spec_parity():
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(
            f"[{TAG}] parite spec rompue : delta calcule {dc} car / {db} o, "
            f"spec {SPEC_CHAR_DELTA} car / {SPEC_BYTE_DELTA} o. Aborting.")
    return dc, db


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. "
                f"{TAG} doit rester en aval de libpicker et en amont de "
                "libsend uniquement ; jamais de repatch_all.")


def ensure_tail_order(bak):
    stem = bak.name.rsplit(".bak_", 1)[0]
    others = [p.stat().st_mtime for p in bak.parent.glob(stem + ".bak_*")
              if p != bak]
    if not others:
        return False
    top = max(others)
    if bak.stat().st_mtime > top:
        return False
    t = max(time.time(), top + 1.0)
    os.utime(bak, (t, t))
    return True


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_src(p):
    return p.read_text(encoding="utf-8", newline="")


def eol_stats(data):
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


def resolve_root(args):
    if "--root" in args:
        return pathlib.Path(args[args.index("--root") + 1]).resolve()
    here = pathlib.Path(".").resolve()
    if (here / REL_BUNDLE).is_file():
        return here
    return pathlib.Path(__file__).resolve().parent.parent


def main():
    args = sys.argv[1:]
    if "--deltas" in args:
        dc, db = deltas()
        print(f"[{TAG}] delta +{dc} car / +{db} o")
        return
    check = "--check" in args
    dc, db = check_spec_parity()
    root = resolve_root(args)
    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)
    if "--force-unchained" not in args:
        guard_downstream(bak)

    if check:
        src = bak if bak.exists() else bundle
        s = read_src(src)
        if s.count(MARKER):
            raise SystemExit(
                f"[{TAG}] marqueur deja present x{s.count(MARKER)} dans "
                f"{src.name} — double application refusee. Une racine d'app "
                "installee se met a jour par COPIE du bundle du depot.")
        for tag, anchor, _r in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(f"[{tag}] anchor count={n} (want 1). "
                                 "Aborting.")
        for name, probe, want in STABLE_PROBES:
            if s.count(probe) != want:
                raise SystemExit(f"[sonde {name}] count={s.count(probe)} "
                                 f"(want {want}). Aborting.")
        raw = src.read_bytes()
        crlf, lf, cr = eol_stats(raw)
        print(f"[{TAG}] applicable sur {src}")
        print(f"[{TAG}] {len(PATCHES)} ancres OK, marqueur absent, "
              f"{len(STABLE_PROBES)} sondes aux comptes")
        print(f"[{TAG}] CRLF={crlf} LF-isole={lf} CR-isole={cr} ; "
              f"delta +{dc} car / +{db} o")
        return

    if not bak.exists():
        if MARKER in read_src(bundle):
            raise SystemExit(
                f"[{TAG}] marqueur present sans {bak.name} : etat ambigu, "
                "abandon sans rien ecrire.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine")
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)

    before = bundle.read_bytes()
    crlf0, lf0, cr0 = eol_stats(before)
    if lf0 or cr0:
        raise SystemExit(f"[{TAG}] fins de ligne non homogenes. Aborting.")
    s = read_src(bundle)
    chars0 = len(s)
    if MARKER in s:
        raise SystemExit(f"[{TAG}] backup empoisonne (marqueur present "
                         "apres restore). Aborting.")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)
    with open(bundle, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)

    after = bundle.read_bytes()
    crlf1, lf1, cr1 = eol_stats(after)
    problems = []
    if (crlf1, lf1, cr1) != (crlf0, 0, 0):
        problems.append("fins de ligne changees")
    if len(after) != len(before) + db:
        problems.append(f"taille {len(after)} o, attendu {len(before) + db}")
    if len(s) != chars0 + dc:
        problems.append(f"caracteres {len(s)}, attendu {chars0 + dc}")
    if s.count(MARKER) != MARKER_ATTENDU:
        problems.append(f"marqueur x{s.count(MARKER)} "
                        f"(want {MARKER_ATTENDU})")
    if s.count("dzlp-chips") != CHIPS_ATTENDU:
        problems.append(f"dzlp-chips x{s.count('dzlp-chips')} "
                        f"(want {CHIPS_ATTENDU})")
    for name, probe, want in STABLE_PROBES:
        if s.count(probe) != want:
            problems.append(f"sonde {name} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print("OK - bundle patche (chips de provenance : ecran Library + "
          "selecteur).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : copie .mjs + node --check, puis DEPLOYER le bundle")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
