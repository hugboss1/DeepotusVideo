# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzstudio.py
"""Maillon de queue : le STUDIO (menus Studio, t225-t229, 16/10/2026).

t225 — chaque lien atterrit au MILIEU du rond du port, à l'entrée comme à la sortie. Défaut relevé sur 02f8162c
(docs/superpowers/specs/2026-10-16-releve-menus-studio.md) : `qi` (géométrie des liens) et `ud` (rendu des ports)
calculaient chacun leur position. `qi` donnait x = 0 / bi et y = Ru+12+i·Mu (48+22i) ; le rond est rendu à x+1 / x+219
(bordure du nœud) et y = 1 + Ru + 10 + 8 (55+22i) ; un libellé long passait sur deux lignes (`alignItems:center`) et
le rond descendait encore de 7. Ce qu'il pose (ancres uniques, relevées le 16/10 sur 02f8162c) :
  - A0 : `dzPortGeo` = {b bordure, oy origine des lignes sous l'en-tête, p pas (Mu), lh hauteur de ligne, r rond},
    posé devant `qi` après les constantes du Studio : LA source unique de géométrie des ports ;
  - A1 : `qi` rend le centre du rond : x = b (entrée) / bi − b (sortie), y = b + Ru + oy + i·p + r/2 ;
  - A2 : `ud` pose la ligne à `oy + i·p`, de hauteur fixe `lh`, rond (`r`) ancré en HAUT (`alignItems:"flex-start"`),
    débordant de r/2 hors du nœud ;
  - A3 : l'étiquette tient sur UNE ligne (nowrap, ellipse, interligne lh) ; son `title` donne le libellé complet.

t226 — le port `brand` de Composition spatiale. Relevé du 16/10 : `dzSpatialSlots` ne créait de port image que pour
les `image_slot` ; la région `r_brand` de tpl_news_reel est un `brand_strip` → pas de port `brand`, alors que le graphe
de départ relie Bandeau de marque → `brand` ; `qi` rendait {x:0,y:0} (coin du nœud). `dzCompose` sautait la région et
le backend la dessine d'après ses `items` : le nœud relié n'était lu par personne. Décision de l'utilisateur, (a) :
  - B1 : `dzSpatialSlots` expose `brand` (type image, slot = id de la région) pour la PREMIÈRE région brand_strip,
    APRÈS les ports existants, si aucune image_slot n'a déjà pris `brand` ; libellé = celui de la région, sinon
    « brand » (aucun texte neuf) ;
  - B2 : `qi` d'un port introuvable rend le bord du nœud à la ligne SOUS le dernier port, jamais plus (0,0) ;
  - B3 : `dzCompose` mappe la région brand_strip à son port (carte région → port de dzSpatialSlots) : si un Bandeau
    de marque y est relié, son texte (ou celui du catalogue, l'espace actif) remplace le 1er item texte ; le logo PNG
    du modèle reste, l'emoji du nœud est ignoré ; texte vide ou identique → région intacte ;
  - B4 : le gabarit modifié part au rendu quand le bandeau a changé (`hasMods`).
Sans lien, rendu identique. La hauteur du corps des ports (t227) n'est PAS touchée ici : t227-t229 ajoutent leurs
familles de paires (C*, D*, E*) à ce maillon.
Aucun useState ajouté (compte figé 731), aucun DzTracks, rien qui touche « v2.8.0 », aucun texte visible neuf (le
`title` réutilise le libellé et le type déjà affichés).

Maillon de QUEUE, APRÈS dzlogo (dont il sonde le marqueur) ; il garde un .js.bak_dzstudio le temps de l'écriture
puis le SUPPRIME, et `version` reste le dernier maillon. Son INVERSE est `avant_dzstudio` dans
backend/tests/_i18n_l1_aide.py (lu sur les PAIRES d'ici), appelé EN TÊTE de `avant_dzlogo`. Lecture et écriture
en OCTETS. Bancs : backend/tests/test_studio_ancrage.py (t225), test_studio_ports_spatial.py (t226).
Run : python scripts/patch_bundle_dzstudio.py [--check]
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_dzstudio")
TAG = "dzstudio"
MARKER = "var dzPortGeo={"
MARKER_ATTENDU = 1

SONDE_AMONT = [
    ("dzlogo", "function DzLogoMarque(", 1),
    ("dzreglages", "function dzOuvrirReglages(", 1),
    ("spatialports", "function dzNodeInPorts(", 1),
    ("version", "v2.8.0", 4),
    ("montage", "DzTracks", 181),
    ("useState", "x.useState(", 731),
]

PAIRES = [
    ('Eh=30;function qi(',                                                                                  # A0
     'Eh=30;var dzPortGeo={b:1,oy:10,p:Mu,lh:16,r:16};function qi('),
    ('const l=t==="in"?0:bi,d=Ru+12+a*Mu;return{x:l,y:d}',                                                  # A1
     'const l=t==="in"?dzPortGeo.b:bi-dzPortGeo.b,d=dzPortGeo.b+Ru+dzPortGeo.oy+a*dzPortGeo.p+dzPortGeo.r/2;'
     'return{x:l,y:d}'),
    ('top:8+n*Mu+2,left:e==="in"?-8:"auto",right:e==="out"?-8:"auto",display:"flex",alignItems:"center",gap:6,'  # A2
     'flexDirection:e==="in"?"row":"row-reverse",width:130},children:[r.jsx("span",{"data-port-side":e,'
     '"data-port-id":t.id,onMouseDown:a=>{a.stopPropagation(),o(a)},onMouseUp:a=>{a.stopPropagation(),i(a)},'
     'style:{width:16,height:16,',
     'top:dzPortGeo.oy+n*dzPortGeo.p,left:e==="in"?-dzPortGeo.r/2:"auto",right:e==="out"?-dzPortGeo.r/2:"auto",'
     'display:"flex",alignItems:"flex-start",height:dzPortGeo.lh,gap:6,'
     'flexDirection:e==="in"?"row":"row-reverse",width:130},children:[r.jsx("span",{"data-port-side":e,'
     '"data-port-id":t.id,onMouseDown:a=>{a.stopPropagation(),o(a)},onMouseUp:a=>{a.stopPropagation(),i(a)},'
     'style:{width:dzPortGeo.r,height:dzPortGeo.r,'),
    ('r.jsxs("span",{style:{fontSize:10.5,color:"var(--ink-soft)",textAlign:e==="in"?"left":"right",'       # A3
     'padding:e==="in"?"0 0 0 4px":"0 4px 0 0"},children:[t.label||t.id,',
     'r.jsxs("span",{title:(t.label||t.id)+" · "+t.type,style:{fontSize:10.5,lineHeight:dzPortGeo.lh+"px",'
     'whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",minWidth:0,color:"var(--ink-soft)",'
     'textAlign:e==="in"?"left":"right",padding:e==="in"?"0 0 0 4px":"0 4px 0 0"},children:[t.label||t.id,'),
    ('ports.push({id:ipool[i1],type:"image",label:imgs[i1].slot_label||imgs[i1].slot_name,slot:imgs[i1].slot_name});'  # B1
     'return{ports:ports,seq:seq,maxN:maxN,n:n}}',
     'ports.push({id:ipool[i1],type:"image",label:imgs[i1].slot_label||imgs[i1].slot_name,slot:imgs[i1].slot_name});'
     'var dzBs=null;for(i1=0;i1<regs.length&&!dzBs;i1++)regs[i1].type==="brand_strip"&&(dzBs=regs[i1]);'
     'dzBs&&!ports.some(function(q){return q.id==="brand"})&&ports.push({id:"brand",type:"image",'
     'label:dzBs.slot_label||dzBs.label||"brand",slot:dzBs.slot_name||dzBs.id});'
     'return{ports:ports,seq:seq,maxN:maxN,n:n}}'),
    ('const a=_lst.findIndex(u=>u.id===n);if(a<0)return{x:0,y:0};',                                         # B2
     'let a=_lst.findIndex(u=>u.id===n);if(a<0)a=_lst.length;'),
    ('var regions=tpl.regions.slice(),zi=60,ovc={};var __trMod=!1;',                                        # B3
     'var regions=tpl.regions.slice(),zi=60,ovc={};var __trMod=!1;'
     'var __brMod=!1;regions=regions.map(function(rg5){var p5=rg5.type==="brand_strip"&&__regionPort[rg5.slot_name||rg5.id],'
     'b5=p5&&Wt(e,l.id,p5);if(!b5||b5.type!=="BrandStrip")return rg5;'
     'var P5=Object.assign({},(Me.BrandStrip&&Me.BrandStrip.props)||{},b5.props||{}),'
     't5=String(P5.text==null?"":P5.text).trim(),k5=-1;if(!t5)return rg5;'
     'var it5=(rg5.items||[]).map(function(it,j){if(k5<0&&it&&it.type==="text"){k5=j;'
     'if(it.text===t5)return it;__brMod=!0;return Object.assign({},it,{text:t5})}return it});'
     'return k5<0?rg5:Object.assign({},rg5,{items:it5})});'),
    ('var hasMods=regions.length!==tpl.regions.length||loud!=null||!!music||__trMod;',                     # B4
     'var hasMods=regions.length!==tpl.regions.length||loud!=null||!!music||__trMod||__brMod;'),
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
    """L'inverse exact (lu par avant_dzstudio dans _i18n_l1_aide)."""
    for ancre, remplace in reversed(PAIRES):
        if s.count(remplace) != 1:
            raise AssertionError(f"[{TAG}] remplacement x{s.count(remplace)} (attendu 1) : {remplace[:80]!r}")
        s = s.replace(remplace, ancre, 1)
    return s


def main() -> None:
    check = "--check" in sys.argv
    s, bom = lire(BUNDLE)
    if MARKER in s:
        if s.count(MARKER) != MARKER_ATTENDU:
            raise SystemExit(f"[{TAG}] marqueur x{s.count(MARKER)}")
        manque = [r[:60] for _a, r in PAIRES if s.count(r) != 1]
        if manque:                                      # t226 : une famille ajoutée après coup (ex. A* sans B*)
            raise SystemExit(f"[{TAG}] partiellement appliqué ({len(manque)} paire(s) absente(s)) — "
                             f"repartir d'avant_dzstudio : {manque[0]!r}")
        print(f"[{TAG}] déjà appliqué")
        return
    for tag, jeton, attendu in SONDE_AMONT:
        if s.count(jeton) != attendu:
            raise SystemExit(f"[{TAG}] sonde {tag} : {jeton!r} x{s.count(jeton)} (attendu {attendu}) — rejouer la chaîne d'abord")
    crlf = s.count("\r\n")
    if crlf < 15000 or s.count("\n") != crlf:
        raise SystemExit(f"[{TAG}] fins de ligne inattendues ({crlf} CRLF / {s.count(chr(10))} LF)")
    neuf = appliquer(s)
    if neuf.count(MARKER) != MARKER_ATTENDU or defaire(neuf) != s:
        raise SystemExit(f"[{TAG}] aller-retour imparfait")
    if neuf.count("x.useState(") != 731 or neuf.count("v2.8.0") != 4 or neuf.count("DzTracks") != 181:
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
