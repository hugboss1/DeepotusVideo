# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzrailmotion.py
"""Assert-guarded patcher : les animations de MENU du design 26/08 (§4.4).

BASELINE : bundle POST-patch libsend (queue de chaîne du 28/08).
Backup dédié : .js.bak_dzrailmotion (état juste avant CE patch).

Réf : DESIGN.md §15-4.4 (+ §15-1.3 mouvement), état consigné en §15-ter.
Le rail de navigation du bundle (composant tg) savait se replier mais SANS
les animations du handoff : la largeur glissait sur les anciens tokens
(--dur-3), et les libellés étaient DÉMONTÉS du DOM à l'instant du repli
(`!n&&…`) — rien ne pouvait s'échapper ni rebondir. Le patron appliqué est
celui du rail Cardforge (cardforge.css « échappée + dzRailPop », core.js
setFold) :

  S1  l'aside gagne dzNavRail/dzNavFold et sa largeur anime sur
      --dur-panel / --ease-panel (460 ms, la courbe du handoff) ;
  S2  chaque ligne pose --ri (son rang) pour la cascade 25 ms/ligne ;
      padding et alignement deviennent CONSTANTS : l'icône ne bouge pas
      d'un pixel pendant le repli (§4.4) — le rail replié est aligné à
      gauche, comme le prototype, plus centré ;
  S3  les libellés restent MONTÉS (sans quoi aucune échappée n'est
      jouable) : opacité --dur-label, glissement -22 px / 380 ms, décalage
      25 ms × rang ; le badge « new » se masque au repli (méta flex:none) ;
  S4  la feuille <style id=__dzNavMotion> (injectée avant tg) porte
      l'échappée, le rebond dzNavPop (1→.74→1.08→1 sur --dur-panel) et le
      kill-switch prefers-reduced-motion (§1.3 : états conservés, durées
      à 1 ms, cascades supprimées) ;
  S5  le geste ARME l'animation (classe dzNavAnime sur <body>, retirée à
      700 ms) en étendant l'intercepteur de persistance du patch navrail :
      la restauration au chargement pose l'état final SANS animation
      (§4.6) — la même règle que .rail-anime côté Cardforge. La classe vit
      sur <body> parce que React repeint className de l'aside à chaque
      bascule : une classe posée là serait perdue par le rendu même
      qu'elle doit habiller.

Écart assumé (dit, pas caché) : les largeurs restent 232→64 (les cotes
réelles du bundle, même règle de correspondance que §15-bis « tokens ») —
le handoff prototype disait 236→62.

Run : python scripts/patch_bundle_dzrailmotion.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzrailmotion")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


# ── S4 : la feuille du mouvement (aucun guillemet double : elle voyage dans
#         une chaîne JS délimitée par des doubles) ──────────────────────────
CSS = (
    ".dzNavRail{overflow:hidden}"
    ".dzNavItem .dzNavLbl{transition:"
    "opacity var(--dur-label,200ms) var(--ease-panel,ease) calc(var(--ri,0)*25ms),"
    "transform 380ms var(--ease-panel,ease) calc(var(--ri,0)*25ms)}"
    ".dzNavFold .dzNavItem .dzNavLbl{opacity:0;transform:translateX(-22px)}"
    ".dzNavFold .dzNavItem .dzNavMeta{display:none}"
    "body.dzNavAnime .dzNavFold .dzNavItem>svg{"
    "animation:dzNavPop var(--dur-panel,460ms) var(--ease-panel,ease) both;"
    "animation-delay:calc(var(--ri,0)*25ms)}"
    "@keyframes dzNavPop{0%{transform:scale(1)}35%{transform:scale(.74)}"
    "70%{transform:scale(1.08)}100%{transform:scale(1)}}"
    "@media (prefers-reduced-motion:reduce){"
    ".dzNavItem .dzNavLbl{transition-duration:1ms;transition-delay:0ms}"
    "body.dzNavAnime .dzNavFold .dzNavItem>svg{animation:none}}"
)
PREAMBLE = (
    '(function(){try{if(document.getElementById("__dzNavMotion"))return;'
    'var st=document.createElement("style");st.id="__dzNavMotion";'
    'st.textContent="' + CSS + '";document.head.appendChild(st)}catch(e){}})();'
)


def main():
    # LE PIÈGE DES FINS DE LIGNE (banc card3d, revue 2c-T6) : le bundle du
    # poste est 100 % CRLF et les bancs le tiennent — lire SANS newline=""
    # traduirait tout en LF et le patch livrerait un bundle traduit. On lit
    # donc VERBATIM, et on refuse un état de départ non homogène plutôt que
    # de le propager.
    raw = BUNDLE.read_bytes()
    crlf = raw.count(b"\r\n")
    lf_seul = raw.count(b"\n") - crlf
    cr_seul = raw.count(b"\r") - crlf
    if lf_seul or cr_seul:
        raise SystemExit(
            f"[dzrailmotion] fins de ligne non homogenes AVANT patch "
            f"(CRLF={crlf} LF-isole={lf_seul} CR-isole={cr_seul}). Aborting.")
    s = raw.decode("utf-8")
    if "dzNavMotion" in s:
        raise SystemExit("Bundle déjà patché (dzNavMotion présent). Aborting.")
    if not BAK.exists():
        shutil.copyfile(BUNDLE, BAK)
        print("backup ->", BAK.name)

    # S1 — l'aside : classes d'état + la largeur sur les tokens du handoff
    s = apply(
        s,
        'r.jsxs("aside",{style:{width:n?64:232,background:"var(--bg-panel)",'
        'borderRight:"1px solid var(--stroke)",display:"flex",'
        'flexDirection:"column",transition:"width var(--dur-3) var(--ease)",'
        'minHeight:0},children:[',
        'r.jsxs("aside",{className:"dzNavRail"+(n?" dzNavFold":""),'
        'style:{width:n?64:232,background:"var(--bg-panel)",'
        'borderRight:"1px solid var(--stroke)",display:"flex",'
        'flexDirection:"column",'
        'transition:"width var(--dur-panel,460ms) var(--ease-panel,ease)",'
        'minHeight:0},children:[',
        "S1-aside")

    # S2 — le rang --ri + padding constant (l'icône ne bouge pas d'un pixel)
    s = apply(
        s,
        'children:Uu.map(s=>{const a=e===s.id;return r.jsxs("button",{'
        'onClick:()=>t(s.id),title:n?s.label:"",style:{display:"flex",'
        'alignItems:"center",gap:12,padding:n?"10px":"8px 10px",',
        'children:Uu.map((s,dzri)=>{const a=e===s.id;return r.jsxs("button",{'
        'className:"dzNavItem",onClick:()=>t(s.id),title:n?s.label:"",'
        'style:{"--ri":dzri,display:"flex",'
        'alignItems:"center",gap:12,padding:"8px 10px",',
        "S2-rang")
    s = apply(
        s,
        'textAlign:"left",transition:"all var(--dur-1) var(--ease)",'
        'justifyContent:n?"center":"flex-start"}',
        'textAlign:"left",transition:"all var(--dur-1) var(--ease)",'
        'justifyContent:"flex-start"}',
        "S2-alignement")

    # S3 — les libellés restent montés ; le badge devient une méta masquable
    s = apply(
        s,
        '!n&&r.jsxs(r.Fragment,{children:[r.jsxs("div",{style:{flex:1,'
        'minWidth:0},children:[r.jsx("div",{style:{fontSize:13,'
        'fontWeight:a?600:500},children:s.label}),r.jsx("div",{style:{'
        'fontSize:10.5,color:"var(--ink-soft)"},children:s.desc})]}),'
        's.new&&r.jsx(te,{tone:"violet",children:"new"})]})',
        'r.jsxs(r.Fragment,{children:[r.jsxs("div",{className:"dzNavLbl",'
        'style:{flex:1,minWidth:0},children:[r.jsx("div",{style:{fontSize:13,'
        'fontWeight:a?600:500,whiteSpace:"nowrap",overflow:"hidden"},'
        'children:s.label}),r.jsx("div",{style:{fontSize:10.5,'
        'color:"var(--ink-soft)",whiteSpace:"nowrap",overflow:"hidden"},'
        'children:s.desc})]}),s.new&&r.jsx("span",{className:"dzNavMeta",'
        'children:r.jsx(te,{tone:"violet",children:"new"})})]})',
        "S3-libelles")

    # S4 — la feuille, injectée au chargement du module, juste avant tg
    s = apply(
        s,
        "function tg({view:e,setView:t,collapsed:n,setCollapsed:o}){",
        PREAMBLE + "function tg({view:e,setView:t,collapsed:n,setCollapsed:o}){",
        "S4-feuille")

    # S5 — le geste arme l'animation (extension de l'intercepteur navrail)
    s = apply(
        s,
        'setCollapsed:function(v1){try{localStorage.setItem('
        '"dz_nav_collapsed",v1?"1":"0")}catch(_e){}d(v1)}})',
        'setCollapsed:function(v1){try{localStorage.setItem('
        '"dz_nav_collapsed",v1?"1":"0")}catch(_e){}'
        'try{var dzb=document.body;dzb.classList.add("dzNavAnime");'
        'clearTimeout(window.__dzNavAnimeT);'
        'window.__dzNavAnimeT=setTimeout(function(){'
        'dzb.classList.remove("dzNavAnime")},700)}catch(_e2){}d(v1)}})',
        "S5-geste")

    BUNDLE.write_text(s, encoding="utf-8", newline="")
    fin = BUNDLE.read_bytes()
    if fin.count(b"\n") != fin.count(b"\r\n"):
        raise SystemExit("[dzrailmotion] le patch a traduit des fins de ligne. Aborting.")
    print("bundle écrit :", len(s), "o — animations de menu §4.4 actives")


if __name__ == "__main__":
    main()
