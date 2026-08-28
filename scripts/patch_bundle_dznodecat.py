# -*- coding: utf-8 -*-
# scripts/patch_bundle_dznodecat.py
"""Assert-guarded patcher : Studio — une teinte PAR catégorie de nœuds, et
le repli de la colonne Nodes au mouvement du design (§4.4).

BASELINE : bundle POST-patch version (v2.6.0, queue de chaîne du 28/08).
Backup dédié : .js.bak_dznodecat (état juste avant CE patch).

Réf : DESIGN.md §15-1.2 (doctrine des teintes) et §15-quater (état). La
carte `Qr` des catégories du Studio portait des DOUBLONS : source ET
motion en ambre, gen (var(--cyan)) et compose (#06b6d4) deux cyans
jumeaux, master sur le ROUGE d'échec, output en blanc. Et la carte de
nœud concaténait `f.color+"66"`/`"22"`/`1a`/`55` en hexa-alpha — du CSS
invalide dès que la couleur est un var() : dégradé d'en-tête, halo de
run et puce d'icône ne teintaient VRAIMENT que compose et output, les
deux seules en hexa littéral.

  S1  `Qr` passe sur HUIT tokens `--nd-*` (deepotus.tokens.css + copie
      dist/shared + theme-v2.css, sombre et clair) : clarté/chroma
      identiques, ROUE À 45° — huit teintes espacées de 45° minimum (le
      premier essai à 25° laissait l'arc bleu trop voisin à l'œil). Les
      sémantiques sont MESURÉES au poste — la couche Cinema remappe
      `--cyan` sur l'or de marque #f0b429 : sélection = or ~83°, succès
      #5ec8a0 ~163°, échec #e35d4a ~33° ; trois proximités bornées et
      dites en §15-quater, les cinq autres teintes à 27° ou plus ;
  S2  les quatre concaténations hexa-alpha deviennent des `color-mix`
      (40 %/33 %/10 %/13 %) — thémables, et l'anomalie latente meurt ;
  S3  les rangées de la colonne Nodes (starters, en-têtes de catégorie,
      nœuds) gagnent la classe `dzNd` — le support de l'échappée ;
  S4  `dzdOpen` (le SEUL chemin de geste : bouton Hide, touche /, Échap,
      poignée) pose `--ri` sur chaque rangée avant de basculer — le rang
      est PLAFONNÉ à 14 (la colonne compte ~40 rangées : une cascade
      complète traînerait 1 s derrière une largeur qui ferme en 460 ms) ;
      la restauration au chargement rend l'état final au premier rendu,
      donc sans animation (§4.6, même règle que le rail) ;
  S5  la feuille <style id=__dzNodeCat> : largeur de grille et fondu du
      conteneur sur --dur-panel/--ease-panel (spécificité DOUBLÉE pour
      battre la feuille nodedock sans la modifier), échappée des rangées
      (--dur-label + translateX(-22px)/380 ms, décalage 25 ms × rang),
      kill-switch prefers-reduced-motion.

Écart assumé (dit, pas caché) : pas de rebond d'icônes ici — le repli va
à ZÉRO, aucune icône ne survit pour rebondir (le rebond du rail anime ce
qui RESTE) ; et le plafond de rang à 14 borne la traîne de cascade.

Run : python scripts/patch_bundle_dznodecat.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dznodecat")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


OLD_QR = (
    'Qr={source:{color:"var(--amber)",label:"Source",icon:"image"},'
    'gen:{color:"var(--cyan)",label:"Generator",icon:"sparkle"},'
    'audio:{color:"var(--green)",label:"Audio",icon:"wave"},'
    'edit:{color:"var(--violet)",label:"Edit",icon:"film"},'
    'compose:{color:"#06b6d4",label:"Composition",icon:"layers"},'
    'motion:{color:"var(--amber)",label:"Animations",icon:"sparkle"},'
    'master:{color:"var(--red)",label:"Master",icon:"warn"},'
    'output:{color:"#ffffff",label:"Output",icon:"download"}}'
)
NEW_QR = (
    'Qr={source:{color:"var(--nd-source)",label:"Source",icon:"image"},'
    'gen:{color:"var(--nd-gen)",label:"Generator",icon:"sparkle"},'
    'audio:{color:"var(--nd-audio)",label:"Audio",icon:"wave"},'
    'edit:{color:"var(--nd-edit)",label:"Edit",icon:"film"},'
    'compose:{color:"var(--nd-compose)",label:"Composition",icon:"layers"},'
    'motion:{color:"var(--nd-motion)",label:"Animations",icon:"sparkle"},'
    'master:{color:"var(--nd-master)",label:"Master",icon:"warn"},'
    'output:{color:"var(--nd-output)",label:"Output",icon:"download"}}'
)

CSS = (
    ".dz-studio-grid.dz-studio-grid{transition:grid-template-columns "
    "var(--dur-panel,460ms) var(--ease-panel,ease)}"
    ".dz-studio-grid.dz-studio-grid>div:first-child{transition:opacity "
    "var(--dur-panel,460ms) var(--ease-panel,ease)}"
    ".dzNd{transition:"
    "opacity var(--dur-label,200ms) var(--ease-panel,ease) calc(var(--ri,0)*25ms),"
    "transform 380ms var(--ease-panel,ease) calc(var(--ri,0)*25ms)}"
    ".dz-dock-hidden .dzNd{opacity:0;transform:translateX(-22px)}"
    "@media (prefers-reduced-motion:reduce){"
    ".dz-studio-grid.dz-studio-grid{transition:none}"
    ".dz-studio-grid.dz-studio-grid>div:first-child{transition:none}"
    ".dzNd{transition-duration:1ms;transition-delay:0ms}}"
)
INJECT = (
    '(function(){try{if(document.getElementById("__dzNodeCat"))return;'
    'var st=document.createElement("style");st.id="__dzNodeCat";'
    'st.textContent="' + CSS + '";document.head.appendChild(st)}catch(_e){}})();'
)

WALK = (
    'try{var rws=document.querySelectorAll('
    '".dz-studio-grid>div:first-child .dzNd");'
    'for(var ri1=0;ri1<rws.length;ri1++)'
    'rws[ri1].style.setProperty("--ri",String(Math.min(ri1,14)))}catch(_e9){}'
)


def main():
    raw = BUNDLE.read_bytes()
    crlf = raw.count(b"\r\n")
    lf_seul = raw.count(b"\n") - crlf
    cr_seul = raw.count(b"\r") - crlf
    if lf_seul or cr_seul:
        raise SystemExit(
            f"[dznodecat] fins de ligne non homogenes AVANT patch "
            f"(CRLF={crlf} LF-isole={lf_seul} CR-isole={cr_seul}). Aborting.")
    s = raw.decode("utf-8")
    if "dzNodeCat" in s:
        raise SystemExit("Bundle déjà patché (dzNodeCat présent). Aborting.")
    if not BAK.exists():
        shutil.copyfile(BUNDLE, BAK)
        print("backup ->", BAK.name)

    # S1 — la carte des catégories : huit teintes, zéro doublon
    s = apply(s, OLD_QR, NEW_QR, "S1-Qr")

    # S2 — les alpha en color-mix (l'hexa-alpha concaténé est mort)
    s = apply(
        s,
        'v=o==="running"?{"--node-color":f.color+"66",'
        'boxShadow:`0 0 0 1px ${f.color}, 0 0 40px ${f.color}55`}',
        'v=o==="running"?{"--node-color":"color-mix(in srgb, "+f.color+" 40%, transparent)",'
        'boxShadow:`0 0 0 1px ${f.color}, 0 0 40px color-mix(in srgb, ${f.color} 33%, transparent)`}',
        "S2-run")
    s = apply(
        s,
        'background:`linear-gradient(180deg, ${f.color}1a 0%, transparent 100%)`',
        'background:`linear-gradient(180deg, color-mix(in srgb, ${f.color} 10%, transparent) 0%, transparent 100%)`',
        "S2-grad")
    s = apply(
        s,
        'background:f.color+"22",color:f.color',
        'background:"color-mix(in srgb, "+f.color+" 13%, transparent)",color:f.color',
        "S2-chip")

    # S3 — les rangées de la colonne portent dzNd
    s = apply(
        s,
        'i=>r.jsxs("button",{onClick:()=>t(i.k),style:{display:"flex",'
        'alignItems:"center",gap:10,width:"100%",padding:"8px 8px"',
        'i=>r.jsxs("button",{className:"dzNd",onClick:()=>t(i.k),style:{display:"flex",'
        'alignItems:"center",gap:10,width:"100%",padding:"8px 8px"',
        "S3-starter")
    s = apply(
        s,
        'r.jsxs("div",{className:"upper",style:{display:"flex",'
        'alignItems:"center",gap:6,marginBottom:6,color:a.color}',
        'r.jsxs("div",{className:"upper dzNd",style:{display:"flex",'
        'alignItems:"center",gap:6,marginBottom:6,color:a.color}',
        "S3-entete")
    s = apply(
        s,
        'return r.jsxs("div",{draggable:!0,'
        'onDragStart:u=>{u.dataTransfer.setData("application/node-type",l)',
        'return r.jsxs("div",{className:"dzNd",draggable:!0,'
        'onDragStart:u=>{u.dataTransfer.setData("application/node-type",l)',
        "S3-rangee")

    # S4 — le geste pose les rangs avant de basculer
    s = apply(
        s,
        'function dzdOpen(v1){var nx=v1===void 0?!dzdSt.open:!!v1;'
        'if(nx===dzdSt.open)return;dzdSt.open=nx;',
        'function dzdOpen(v1){var nx=v1===void 0?!dzdSt.open:!!v1;'
        'if(nx===dzdSt.open)return;dzdSt.open=nx;' + WALK,
        "S4-geste")

    # S5 — la feuille du mouvement, injectée au chargement du module
    s = apply(
        s,
        'window.__dzNodes={open:function(){dzdOpen(!0)}',
        INJECT + 'window.__dzNodes={open:function(){dzdOpen(!0)}',
        "S5-feuille")

    BUNDLE.write_text(s, encoding="utf-8", newline="")
    fin = BUNDLE.read_bytes()
    if fin.count(b"\n") != fin.count(b"\r\n"):
        raise SystemExit("[dznodecat] le patch a traduit des fins de ligne. Aborting.")
    print("bundle écrit :", len(s), "o — huit teintes de catégorie + repli §4.4 de la colonne Nodes")


if __name__ == "__main__":
    main()
