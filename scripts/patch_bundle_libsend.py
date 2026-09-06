# -*- coding: utf-8 -*-
# scripts/patch_bundle_libsend.py
"""Patcher assert-garde : menu « Envoyer vers… » de la Bibliotheque.

BASELINE : bundle POST-patch libprov (dernier maillon en date).
Backup dedie : `.js.bak_libsend`. Position : EN QUEUE, apres libprov.
Spec : docs/superpowers/plans/2026-08-28-bibliotheque-provenance-envoyer-vers.md

Chaque cible REUTILISE un mecanisme EXISTANT mesure :
  image  -> Studio (Lh consomme deja __dzRenderGraph : graphe a noeud
            Image), Quick (global __dzQuickStart + greffe au mount),
            Template (graphe Image->SpatialCompose port bg), Bible
            (GET/PUT /bible/entities, patron -> Bible du Vectorlab),
            Montage (global __dzMontageAdd + greffe addAsset),
            Cardforge (presse-papier img:<nom> + navigate subtab cards),
            Sprite Lab (__dzToSpriteLab existant), Scheduler
            (createScheduledPost + deepotus:select-post, patron Episodes)
  render -> Montage (clip), Sprite Lab, Scheduler (job_id)
  asset3d-> Impression 3D (__dzPrint3d existant — son pin passe a 3,
            test_print3d.py:309 suit)
  sprite2d-> copie de la sheet vers les Images (route save existante,
            la copie arrive sourcee `sprites`)

DANGERS : jamais `repatch_all.py --from` sur cette chaine, lancement
SEUL, newline='' partout (CRLF), jamais d'ancre imprimee (cp1252).
Validation finale : copie .mjs + `node --check`.

Run :
    python scripts/patch_bundle_libsend.py              # depot
    python scripts/patch_bundle_libsend.py --check      # n'ecrit rien
    python scripts/patch_bundle_libsend.py --deltas     # affiche les deltas
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "libsend"
MARKER = "__dzSendTo"
MARKER_ATTENDU = 2      # la definition + l'appel du bouton du modal

STABLE_PROBES = [
    ("libpicker", "__dzLibPicker", 10),
    ("libprov", "__dzSrcChips", 2),
    ("print3d", "__dzPrint3d", 2),
    ("spritelab", "__dzToSpriteLab", 3),
    ("navrail", "dz_nav_collapsed", 2),
    ("dzdesign", "__dzCatBar", 2),
]

# comptes attendus APRES application (verification post-ecriture)
POST_COUNTS = [
    ("__dzPrint3d", 3),
    ("__dzToSpriteLab", 5),
    ("__dzQuickStart", 3),
    # 4 -> 5 le 05/09/2026 (chantier montage, P7) : la couche
    # montage.js cite le jeton dans un COMMENTAIRE ; str.count est
    # global, le commentaire compte (mesure du 06/09/2026).
    ("__dzMontageAdd", 5),
    ("deepotus:select-post", 6),
    ("__dzLibPicker", 10),
    ("__dzSrcChips", 2),
]

SPEC_CHAR_DELTA = 7457
SPEC_BYTE_DELTA = 7568

# ── S1 : helpers module (inseres avant __dzToSpriteLab) ──────────────────────
HELPERS = (
    "function __dzToast(msg){try{"
    'var t=document.createElement("div");t.textContent=msg;'
    't.style.cssText="position:fixed;bottom:24px;left:50%;'
    "transform:translateX(-50%);background:var(--bg-panel,#13171c);"
    "border:1px solid var(--stroke,#20262d);color:var(--ink,#cfd6dd);"
    "padding:9px 16px;border-radius:9px;z-index:9600;font-size:12.5px;"
    'box-shadow:0 8px 30px rgba(0,0,0,.5)";'
    "document.body.appendChild(t);"
    "setTimeout(function(){t.remove()},3600)}catch(e){}}"

    "function __dzSendNav(view,extra){var d={view:view};"
    "if(extra)for(var k in extra)d[k]=extra[k];"
    'window.dispatchEvent(new CustomEvent("deepotus:navigate",'
    "{detail:d}))}"

    "function __dzSendMenu(items,titre){try{"
    'var old=document.getElementById("__dzSendHost");if(old)old.remove();'
    'var h=document.createElement("div");h.id="__dzSendHost";'
    'h.style.cssText="position:fixed;inset:0;background:rgba(4,6,10,.55);'
    'z-index:9500;display:flex;align-items:center;justify-content:center";'
    'var c=document.createElement("div");'
    'c.style.cssText="min-width:280px;max-width:min(430px,92vw);'
    "max-height:80vh;overflow:auto;background:var(--bg-panel,#13171c);"
    "border:1px solid var(--stroke,#20262d);border-radius:12px;"
    'padding:10px;box-shadow:0 18px 60px rgba(0,0,0,.55)";'
    'var t=document.createElement("div");'
    't.textContent=titre||"Envoyer vers…";'
    't.style.cssText="font-size:13px;font-weight:600;'
    'color:var(--ink-strong,#eef2f6);padding:6px 8px 10px";'
    "c.appendChild(t);"
    "items.forEach(function(it){"
    'var b=document.createElement("button");b.textContent=it.lbl;'
    'b.style.cssText="display:block;width:100%;text-align:left;'
    "background:transparent;border:0;border-radius:8px;"
    'color:var(--ink,#cfd6dd);padding:9px 10px;font-size:12.5px;'
    'cursor:pointer";'
    "b.onmouseenter=function(){"
    'b.style.background="var(--bg-panel-2,#171c22)"};'
    'b.onmouseleave=function(){b.style.background="transparent"};'
    "b.onclick=function(){h.remove();try{it.fn()}catch(e){"
    'window.alert("Envoyer vers : "+String(e&&e.message||e))}};'
    "c.appendChild(b)});"
    'var a=document.createElement("button");a.textContent="Annuler";'
    'a.style.cssText="display:block;width:100%;text-align:center;'
    "background:transparent;border:1px solid var(--stroke,#20262d);"
    "border-radius:8px;color:var(--ink-soft,#8b959f);padding:7px 10px;"
    'margin-top:8px;font-size:12px;cursor:pointer";'
    "a.onclick=function(){h.remove()};c.appendChild(a);"
    "h.addEventListener('click',function(e){if(e.target===h)h.remove()});"
    "h.appendChild(c);document.body.appendChild(h)}catch(e){}}"

    "function __dzSendBible(nom){"
    'fetch("/api/bible/entities").then(function(r){return r.json()})'
    ".then(function(d){var ents=(d&&d.entities)||[];"
    "if(!ents.length){__dzToast("
    '"Aucune entité dans la bible — crée-la dans l\'Atelier d\'abord");'
    "return}"
    "__dzSendMenu(ents.map(function(en){return{"
    'lbl:(en.kind||"?")+" — "+(en.name||en.id),'
    "fn:function(){var insp=(en.inspiration_images||[]).slice();"
    "if(insp.indexOf(nom)<0)insp.push(nom);"
    'fetch("/api/bible/entities/"+encodeURIComponent(en.id),'
    '{method:"PUT",headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({inspiration_images:insp})})"
    ".then(function(r){"
    'if(!r.ok)throw new Error("PUT "+r.status);'
    '__dzToast("Ajouté aux inspirations de « "+(en.name||en.id)'
    '+" » — visible dans l\'Atelier")})'
    '.catch(function(e){window.alert("Bible : "'
    "+String(e&&e.message||e))})}}}),"
    '"Inspiration de quelle entité ?")})'
    '.catch(function(){window.alert("Bible injoignable")})}'

    "function __dzSendSched(post,okmsg){"
    "var I=new Date(Date.now()+2*3600*1000);post.run_at=I.toISOString();"
    'post.channels=post.channels||["x"];post.status="draft";'
    'post.mode="assisted";'
    "D.createScheduledPost(post).then(function(p){"
    'if(p&&p.id){__dzSendNav("scheduler");setTimeout(function(){'
    'window.dispatchEvent(new CustomEvent("deepotus:select-post",'
    "{detail:{id:p.id}}))},140);"
    '__dzToast(okmsg||"Brouillon ajouté au Scheduler")}'
    'else window.alert("Échec de la création du brouillon")})'
    '.catch(function(e){window.alert("Scheduler : "'
    "+String(e&&e.message||e))})}"

    "function __dzSendTo(m,onClose){try{"
    "var items=[];var nom=(m&&m.name)||\"\";"
    'if(m.kind==="image"){'
    'items.push({lbl:"🎬 Studio — nœud Image",fn:function(){'
    "onClose&&onClose();"
    'window.__dzRenderGraph={name:"image.graph",nodes:[{id:"im1",'
    'type:"Image",x:300,y:240,props:{filename:nom}}],edges:[]};'
    '__dzSendNav("studio")}});'
    'items.push({lbl:"⚡ Quick — image de départ",fn:function(){'
    "onClose&&onClose();window.__dzQuickStart=nom;"
    '__dzSendNav("quick")}});'
    'items.push({lbl:"🧩 Template (Studio) — fond du Spatial compose",'
    "fn:function(){onClose&&onClose();"
    'window.__dzRenderGraph={name:"template.graph",nodes:['
    '{id:"im1",type:"Image",x:160,y:240,props:{filename:nom}},'
    '{id:"sc1",type:"SpatialCompose",x:520,y:240,props:{}}],'
    'edges:[{id:"e1",from:"im1",fromPort:"out",to:"sc1",toPort:"bg"}]};'
    '__dzSendNav("studio")}});'
    'items.push({lbl:"📖 Chapitre / Atelier — inspiration d\'une entité",'
    "fn:function(){__dzSendBible(nom)}});"
    'items.push({lbl:"🎞 Montage — overlay à la tête de lecture",'
    "fn:function(){onClose&&onClose();"
    "window.__dzMontageAdd={image:nom};"
    '__dzSendNav("montage")}});'
    'items.push({lbl:"🃏 Cardforge — copier img:… pour une illustration",'
    "fn:function(){onClose&&onClose();"
    'var v="img:"+nom;var done=function(){'
    '__dzToast("« "+v+" » copié — colle-le dans artSource ou '
    'Poser (panneau P1 du Cardforge)");'
    '__dzSendNav("assets3d",{subtab:"cards"})};'
    "if(navigator.clipboard&&navigator.clipboard.writeText){"
    "navigator.clipboard.writeText(v).then(done,function(){"
    'window.prompt("Copie ce chemin d\'illustration :",v);done()})}'
    'else{window.prompt("Copie ce chemin d\'illustration :",v);'
    "done()}}});"
    'items.push({lbl:"🎮 Sprite Lab — source",fn:function(){'
    "onClose&&onClose();"
    '__dzToSpriteLab({kind:"image",filename:nom})}});'
    'items.push({lbl:"📅 Scheduler — brouillon de post",fn:function(){'
    "onClose&&onClose();"
    '__dzSendSched({title:"Post — "+nom,source_image:nom},'
    '"Brouillon créé avec l\'image « "+nom+" »")}});}'
    'if(m.kind==="render"&&m.jobId){'
    'items.push({lbl:"🎞 Montage — clip vidéo",fn:function(){'
    "onClose&&onClose();"
    "window.__dzMontageAdd={job_id:m.jobId,title:nom,dur:0};"
    '__dzSendNav("montage")}});'
    'items.push({lbl:"🎮 Sprite Lab — source",fn:function(){'
    "onClose&&onClose();"
    '__dzToSpriteLab({kind:"job",job_id:m.jobId,label:nom})}});'
    'items.push({lbl:"📅 Scheduler — brouillon de post",fn:function(){'
    "onClose&&onClose();"
    '__dzSendSched({title:"Post — "+nom,job_id:m.jobId},'
    '"Brouillon créé avec le rendu « "+nom+" »")}});}'
    'if(m.kind==="asset3d"&&m.short){'
    'items.push({lbl:"🖨 Impression 3D — export STL/3MF + slicer",'
    "fn:function(){onClose&&onClose();__dzPrint3d(m.short)}});}"
    'if(m.kind==="sprite2d"&&m.short){'
    'items.push({lbl:"🖼 Copier la sheet dans les Images",'
    "fn:function(){onClose&&onClose();"
    'fetch("/api/assets/sprite/"+encodeURIComponent(m.short)+"/save",'
    '{method:"POST"}).then(function(r){return r.json()})'
    ".then(function(d){__dzToast("
    '"Sheet copiée : "+((d&&d.filename)||"?")+" (source Sprite Lab)")})'
    '.catch(function(e){window.alert("Copie : "'
    "+String(e&&e.message||e))})}});}"
    'if(!items.length){__dzToast("Aucune cible pour cet asset");return}'
    '__dzSendMenu(items,"Envoyer « "+nom+" » vers…")'
    '}catch(e){window.alert("Envoyer vers : "'
    "+String(e&&e.message||e))}}"
)

# ── ancres (mesurees au bundle post-libprov) ─────────────────────────────────
_A1 = "function __dzToSpriteLab(src){"
_A2 = 'children:"Rouvrir dans Studio"}),'
_A3 = "f(je),!w&&je.length&&v(je[0]),"
_A4 = "function defaultLen(kind,srcDur){"

GREFFE_MODAL = (
    'm.kind!=="audio"&&r.jsx(K,{variant:"ghost",size:"sm",'
    "onClick:()=>__dzSendTo(m,function(){y(null)}),"
    'children:"Envoyer vers…"},"dzsend"),'
)

GREFFE_QUICK = (
    "f(je),(function(){var dzq=null;"
    "try{dzq=window.__dzQuickStart;delete window.__dzQuickStart}"
    "catch(_e){}"
    "dzq?v(dzq):(!w&&je.length&&v(je[0]))})(),"
)

GREFFE_MONTAGE = (
    "x.useEffect(function(){var p=null;"
    "try{p=window.__dzMontageAdd;delete window.__dzMontageAdd}"
    "catch(_e){}"
    "if(!p)return;setTimeout(function(){try{"
    'if(p.image)addAsset({image:p.image},p.image,"image",0,"v2");'
    "else if(p.job_id)addAsset({job_id:p.job_id},p.title||p.job_id,"
    '"video",p.dur||0,"v2")}catch(_e2){}},450)},[]);'
)

PATCHES = [
    ("S1-helpers", _A1, HELPERS + _A1),
    ("S2-bouton-modal", _A2, _A2 + GREFFE_MODAL),
    ("S3-quick-consomme", _A3, GREFFE_QUICK),
    ("S4-montage-consomme", _A4, GREFFE_MONTAGE + _A4),
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
                f"{TAG} doit rester le DERNIER maillon ; jamais de "
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
    for probe, want in POST_COUNTS:
        if s.count(probe) != want:
            problems.append(f"post {probe} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print("OK - bundle patche (menu Envoyer vers... : 8 cibles image, "
          "3 render, print3d, sheet).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : copie .mjs + node --check, puis DEPLOYER le bundle")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
