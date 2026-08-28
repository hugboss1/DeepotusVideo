# -*- coding: utf-8 -*-
# scripts/patch_bundle_libpicker.py
"""Patcher assert-garde : le sélecteur de Bibliothèque unifié (vignettes).

BASELINE : bundle POST-patch print3d (dernier maillon en date).
Backup dedie : `.js.bak_libpicker`. Position : EN QUEUE, apres print3d.
Spec : docs/superpowers/plans/2026-08-28-bibliotheque-unifiee-guide-impression.md

Quatre sections :
  L1  le preambule `__dzLibPicker(opts, cb)` — overlay DOM autonome :
      recherche instantanee, grille de VIGNETTES reelles de la
      Bibliotheque (tri mtime recentes d'abord), import fichier local
      (POST /images/upload) et import Figma (POST /images/import-figma),
      Echap/clic-dehors/Annuler = rien. Feuille injectee une fois.
  L2  greffe « Bibliotheque / Parcourir les vignettes » dans le noeud
      Image du Studio (Bh) — LE dropdown de noms de la plainte. Le
      dropdown reste (additif).
  L3  greffe « Parcourir » sous Start image de Quick (Seedance).
  L4  greffe « Parcourir » sous End image de Quick.

DANGERS : identiques aux patchers recents — jamais `repatch_all.py
--from` sur cette chaine, lancement SEUL, newline='' partout (CRLF),
jamais d'ancre imprimee (console cp1252).

Run :
    python scripts/patch_bundle_libpicker.py              # depot
    python scripts/patch_bundle_libpicker.py --check      # n'ecrit rien
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "libpicker"
MARKER = "__dzLibPicker"
MARKER_ATTENDU = 10     # definition + window x2 + 3 greffes + Host x2 + Style x2

STABLE_PROBES = [
    ("screen-switch", 's==="assets3d"&&r.jsx(DzGameAssetsHub,{variant:e})', 1),
    ("cardforge-pane", 'src:"/cardforge/"', 1),
    ("vectorlab-pane", 'src:"/vectorlab/"', 1),
    ("print3d", "__dzPrint3d", 2),
    ("navrail", "dz_nav_collapsed", 2),
    ("dzdesign", "__dzCatBar", 2),
]

SPEC_CHAR_DELTA = 6981
SPEC_BYTE_DELTA = 7037

_BTN_STYLE = ('style:{width:"100%",fontSize:12,padding:"6px 12px",'
              'borderRadius:7,cursor:"pointer",background:"var(--bg-panel-2)",'
              'border:"1px solid var(--stroke)",color:"var(--ink)"}')

PICKER = (
    "function __dzLibPicker(opts,cb){opts=opts||{};try{"
    'var old=document.getElementById("__dzLibPickerHost");if(old)old.remove();'
    'if(!document.getElementById("__dzLibPickerStyle")){'
    'var st=document.createElement("style");st.id="__dzLibPickerStyle";'
    "st.textContent="
    '".dzlp-fond{position:fixed;inset:0;background:rgba(4,6,10,.62);'
    'z-index:9000;display:flex;align-items:center;justify-content:center}"+'
    '".dzlp{width:min(880px,92vw);max-height:86vh;display:flex;'
    "flex-direction:column;background:var(--bg-panel,#13171c);"
    "border:1px solid var(--stroke,#20262d);border-radius:12px;"
    'box-shadow:0 18px 60px rgba(0,0,0,.55)}"+'
    '".dzlp-tete{display:flex;align-items:center;gap:10px;padding:12px 14px;'
    'border-bottom:1px solid var(--stroke,#20262d)}"+'
    '".dzlp-tete b{color:var(--ink-strong,#eef2f6);font-size:13px}"+'
    '".dzlp-cherche{flex:1;background:var(--bg-base,#0a0c0f);'
    "border:1px solid var(--stroke,#20262d);border-radius:7px;"
    'color:var(--ink,#cfd6dd);padding:6px 10px;font-size:12px}"+'
    '".dzlp-x{background:none;border:0;color:var(--ink-soft,#8b959f);'
    'font-size:16px;cursor:pointer}"+'
    '".dzlp-grille{flex:1;overflow:auto;display:grid;'
    "grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:10px;"
    'padding:14px}"+'
    '".dzlp-case{border:1px solid var(--stroke,#20262d);border-radius:9px;'
    "overflow:hidden;background:var(--bg-base,#0a0c0f);cursor:pointer;"
    'padding:0;text-align:left}"+'
    '".dzlp-case:hover{border-color:var(--cat,var(--accent,#f0b429))}"+'
    '".dzlp-case img{width:100%;height:96px;object-fit:cover;display:block;'
    'background:#0b1016}"+'
    '".dzlp-case span{display:block;padding:5px 7px;font-size:10.5px;'
    "color:var(--ink-soft,#8b959f);white-space:nowrap;overflow:hidden;"
    'text-overflow:ellipsis}"+'
    '".dzlp-pied{display:flex;gap:8px;align-items:center;padding:10px 14px;'
    'border-top:1px solid var(--stroke,#20262d)}"+'
    '".dzlp-btn{background:var(--bg-panel-2,#171c22);'
    "border:1px solid var(--stroke,#20262d);border-radius:7px;"
    'color:var(--ink,#cfd6dd);padding:6px 12px;font-size:12px;cursor:pointer}"+'
    '".dzlp-btn:hover{border-color:var(--cat,var(--accent,#f0b429))}"+'
    '".dzlp-vide{grid-column:1/-1;color:var(--ink-soft,#8b959f);'
    'font-size:12px;padding:22px}";'
    "document.head.appendChild(st)}"
    'var hote=document.createElement("div");hote.id="__dzLibPickerHost";'
    'hote.className="dzlp-fond";'
    "hote.innerHTML='<div class=\"dzlp\" role=\"dialog\">"
    '<div class="dzlp-tete"><b></b>'
    '<input class="dzlp-cherche" placeholder="rechercher une image…">'
    '<button class="dzlp-x" title="Fermer (Échap)">✕</button></div>'
    '<div class="dzlp-grille"></div>'
    '<div class="dzlp-pied">'
    '<button class="dzlp-btn" data-dzlp="fichier">⬆ Importer un fichier…</button>'
    '<button class="dzlp-btn" data-dzlp="figma" '
    'title="Colle le lien d&#39;un calque Figma (clic droit → Copy link) — '
    'FIGMA_TOKEN requis dans le .env">◇ Depuis Figma…</button>'
    '<span style="flex:1"></span>'
    '<button class="dzlp-btn" data-dzlp="annuler">Annuler</button>'
    "<input type=\"file\" accept=\"image/*\" hidden></div></div>';"
    'hote.querySelector("b").textContent=opts.titre'
    '||"Bibliothèque — choisir une image";'
    "document.body.appendChild(hote);"
    'var grille=hote.querySelector(".dzlp-grille"),'
    'cherche=hote.querySelector(".dzlp-cherche"),'
    "fichier=hote.querySelector('input[type=file]');"
    "var tout=[];"
    "function fermer(){hote.remove();"
    'document.removeEventListener("keydown",surTouche,true)}'
    "function choisir(nom){fermer();try{cb&&cb(nom)}catch(e){}}"
    "function peindre(){"
    'var q=(cherche.value||"").toLowerCase();'
    "var vus=tout.filter(function(im){return !q"
    "||im.filename.toLowerCase().indexOf(q)>=0});"
    "grille.innerHTML=vus.length?vus.map(function(im){"
    "return '<button class=\"dzlp-case\" data-nom=\"'"
    '+im.filename.replace(/"/g,"&quot;")'
    "+'\"><img loading=\"lazy\" src=\"/api/images/'"
    "+encodeURIComponent(im.filename)"
    "+'\" alt=\"\"><span>'+im.filename.replace(/</g,\"&lt;\")"
    "+'</span></button>'"
    "}).join(\"\"):'<div class=\"dzlp-vide\">'"
    '+(q?"Aucune image pour « "+q.replace(/</g,"&lt;")+" »"'
    ':"La Bibliothèque est vide — importe un fichier ci-dessous ou génère '
    'une image.")+"</div>"}'
    'fetch("/api/images").then(function(r){return r.json()})'
    ".then(function(d){tout=((d&&d.images)||[]).slice()"
    ".sort(function(a,b){return(b.mtime||0)-(a.mtime||0)});peindre()})"
    ".catch(function(){grille.innerHTML="
    "'<div class=\"dzlp-vide\">Bibliothèque injoignable.</div>'});"
    'grille.addEventListener("click",function(e){'
    'var c=e.target.closest(".dzlp-case");'
    'if(c)choisir(c.getAttribute("data-nom"))});'
    'cherche.addEventListener("input",peindre);'
    'hote.querySelector(".dzlp-x").addEventListener("click",fermer);'
    "hote.querySelector('[data-dzlp=\"annuler\"]')"
    '.addEventListener("click",fermer);'
    'hote.addEventListener("click",function(e){if(e.target===hote)fermer()});'
    'function surTouche(e){if(e.key==="Escape"){fermer();e.stopPropagation()}}'
    'document.addEventListener("keydown",surTouche,true);'
    "hote.querySelector('[data-dzlp=\"fichier\"]')"
    '.addEventListener("click",function(){fichier.click()});'
    'fichier.addEventListener("change",function(){'
    "var f=fichier.files&&fichier.files[0];if(!f)return;"
    'var fd=new FormData();fd.append("file",f);'
    'fetch("/api/images/upload",{method:"POST",body:fd})'
    ".then(function(r){return r.json().then(function(d){"
    "return{ok:r.ok,d:d}})}).then(function(x){"
    "if(x.ok&&x.d&&x.d.filename)choisir(x.d.filename);"
    'else window.alert("Import : "'
    '+String((x.d&&(x.d.detail||x.d.error))||"échec"))})'
    '.catch(function(e){window.alert("Import : "'
    "+String(e&&e.message||e))})});"
    "hote.querySelector('[data-dzlp=\"figma\"]')"
    '.addEventListener("click",function(){'
    "var lien=window.prompt(\"Lien du calque Figma (clic droit sur "
    "l'élément → Copy link) :\",\"\");"
    "if(!lien)return;"
    'fetch("/api/images/import-figma",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({url:lien})})"
    ".then(function(r){return r.json().then(function(d){"
    "return{ok:r.ok,d:d}})}).then(function(x){"
    "if(x.ok&&x.d&&x.d.filename)choisir(x.d.filename);"
    'else window.alert("Figma : "+String((x.d&&x.d.detail)||"échec"))})'
    '.catch(function(e){window.alert("Figma : "'
    "+String(e&&e.message||e))})})"
    '}catch(e){window.alert("Bibliothèque : "+String(e&&e.message||e))}}'
    # exposée sur window : les greffes la voient lexicalement, mais les
    # surfaces sœurs (iframes same-origin) et les preuves passent par window
    "window.__dzLibPicker=__dzLibPicker;"
)

GREFFE_BH = (
    'r.jsx(O,{label:"Bibliothèque",children:r.jsx("button",{' + _BTN_STYLE
    + ',onClick:function(){__dzLibPicker({titre:"Nœud Image — choisir dans '
    'la Bibliothèque"},function(fn){t("filename",fn)})},'
    'children:"📚 Parcourir les vignettes…"},"dzlp")}),'
)

GREFFE_START = (
    ',r.jsx(O,{label:"",children:r.jsx("button",{' + _BTN_STYLE
    + ',onClick:function(){__dzLibPicker({titre:"Image de départ '
    '(Seedance)"},v)},children:"📚 Parcourir les vignettes…"},"dzlps")})'
)

GREFFE_END = (
    ',r.jsx(O,{label:"",children:r.jsx("button",{' + _BTN_STYLE
    + ',onClick:function(){__dzLibPicker({titre:"Image de fin '
    '(optionnelle)"},k)},children:"📚 Parcourir les vignettes…"},"dzlpe")})'
)

_A1 = "var __dzManif3d={};"
_A2 = ('r.jsx(O,{label:"Filename",children:r.jsx(le,{mono:!0,'
       'value:e.filename,onChange:s=>t("filename",s)})})')
_A3 = ',onChange:v}):r.jsx(vd,{label:"upload images in Library",kind:"image"})})'
_A4 = ',onChange:k}):r.jsx(vd,{label:"drop or pick",kind:"image"})})'

PATCHES = [
    ("L1-preambule", _A1, _A1 + PICKER),
    ("L2-noeud-image", _A2, GREFFE_BH + _A2),
    ("L3-quick-start", _A3, _A3 + GREFFE_START),
    ("L4-quick-end", _A4, _A4 + GREFFE_END),
]


def deltas():
    dc = sum(len(r) - len(a) for _t, a, r in PATCHES)
    db = sum(len(r.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, r in PATCHES)
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
                "libpicker doit rester le DERNIER maillon ; jamais de "
                "repatch_all sur cette chaine.")


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
        print(f"[{TAG}] 4 ancres OK, marqueur absent, "
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
    for tag, anchor in (("L1", _A1), ("L2", _A2), ("L3", _A3), ("L4", _A4)):
        if s.count(anchor) != 1:
            problems.append(f"{tag} : ancre x{s.count(anchor)} (want 1)")
    for name, probe, want in STABLE_PROBES:
        if s.count(probe) != want:
            problems.append(f"sonde {name} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print("OK - bundle patche (selecteur de Bibliotheque unifie : picker + "
          "3 greffes).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : copie .mjs + node --check, puis DEPLOYER le bundle")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
