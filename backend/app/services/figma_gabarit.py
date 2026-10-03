# -*- coding: utf-8 -*-
"""Plan-templates T10 / D3 (tache #76 du suivi, PR G, 03/10/2026) — IMPORT FIGMA EDITABLE et EXPORT SVG.

Import : le lien d'un CADRE Figma (node-id) devient un GABARIT editable — pas une image :
- GET /v1/files/{cle}/nodes?ids={node} (1 appel) ; parcours RECURSIF des calques (groupes, cadres, instances) ;
- TEXT -> region text (texte, taille, couleur, alignement, fonte reconnue sinon celle par defaut) ;
- un calque a remplissage IMAGE -> case image ; son image est TELECHARGEE dans la Bibliotheque et devient
  l'ECHANTILLON de la case (decision de l'utilisateur, 03/10) — 1 appel de plus (/v1/files/{cle}/images), puis les
  images elles-memes (hors quota) ; coins arrondis / ellipse -> masque de la case ;
- rectangle plein : fin (<= 12 px) -> separateur, sinon bandeau de fond ;
- contraintes Figma -> modes du reagencement (debut, fin, centre, etirer) ;
- tout est BORNE a la toile (un calque qui deborde est coupe, un calque hors cadre est saute) ; ce qui est saute est
  DIT (avertissements). Le gabarit est valide par le moteur avant d'etre enregistre.
Quota : l'API Figma est gratuite mais limitee (Tier 1 : 20 appels/mois sur un siege « View ») ; l'import en fait 1, ou
2 s'il y a des images ; le nombre est rendu. Les deux pas reseau passent par les HOOKS de figma_import (_get_json,
_get_bytes) — le banc les remplace et ne sort jamais.
Export : le gabarit en SVG schematique (fond, cases, textes, bandeaux ; images d'echantillon embarquees) a glisser
dans Figma — l'API Figma n'ecrit pas dans un fichier.
Le plan mappait les contraintes en modes anglais (refuses par le validateur), posait des masques sur des types qui
n'en acceptent pas, ne recuperait pas les images, ne recursait pas dans les groupes et rendait 400 sans jeton.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from xml.sax.saxutils import escape

from app.services import figma_import as FI

_CONTRAINTES = {"LEFT": "debut", "TOP": "debut", "RIGHT": "fin", "BOTTOM": "fin", "CENTER": "centre",
                "LEFT_RIGHT": "etirer", "TOP_BOTTOM": "etirer", "SCALE": "etirer"}
_RECURSIFS = ("GROUP", "FRAME", "COMPONENT", "INSTANCE", "SECTION", "COMPONENT_SET")


def _hex(c: dict, defaut: str = "#000000") -> str:
    if not isinstance(c, dict):
        return defaut
    try:
        return "#%02x%02x%02x" % tuple(max(0, min(255, round(float(c.get(k, 0)) * 255))) for k in ("r", "g", "b"))
    except (TypeError, ValueError):
        return defaut


def _remplissage(n: dict, genre: str):
    for f in n.get("fills") or []:
        if isinstance(f, dict) and f.get("visible", True) is not False and f.get("type") == genre:
            return f
    return None


def _police(nom: str) -> str | None:
    from app.services.template_service import _FONT_FILES
    k = str(nom or "").strip().lower()
    return nom if k in _FONT_FILES else None


def _slot(nom: str, pris: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", str(nom or "").lower()).strip("_")[:40] or "image"
    s, k = base, 2
    while s in pris:
        s, k = f"{base}_{k}", k + 1
    pris.add(s)
    return s


def convertir(cadre: dict) -> tuple:
    """(gabarit sans images, [(slot, imageRef)], avertissements) depuis le noeud CADRE d'une reponse /nodes."""
    bb = cadre.get("absoluteBoundingBox") or {}
    W, H = round(float(bb.get("width") or 0)), round(float(bb.get("height") or 0))
    if W < 8 or H < 8:
        raise ValueError("Le calque visé n'est pas un cadre exploitable (taille nulle) : visez un FRAME.")
    ox, oy = float(bb.get("x") or 0), float(bb.get("y") or 0)
    fond = _remplissage(cadre, "SOLID")
    regions, images, avert, slots, ids = [], [], [], set(), set()
    z = [0]

    def boite(n):
        b = n.get("absoluteBoundingBox") or {}
        x0, y0 = float(b.get("x") or 0) - ox, float(b.get("y") or 0) - oy
        x1, y1 = x0 + float(b.get("width") or 0), y0 + float(b.get("height") or 0)
        cx0, cy0, cx1, cy1 = max(0, round(x0)), max(0, round(y0)), min(W, round(x1)), min(H, round(y1))
        if cx1 - cx0 < 1 or cy1 - cy0 < 1:
            return None, False
        return (cx0, cy0, cx1 - cx0, cy1 - cy0), (cx0, cy0, cx1, cy1) != (round(x0), round(y0), round(x1), round(y1))

    def ident(n):
        base = re.sub(r"[^A-Za-z0-9_-]+", "_", str(n.get("name") or n.get("type") or "r"))[:24].strip("_") or "r"
        s, k = base, 2
        while s in ids:
            s, k = f"{base}_{k}", k + 1
        ids.add(s)
        return s

    def contraintes(n):
        c = n.get("constraints") or {}
        out = {}
        for ax, cle in (("h", "horizontal"), ("v", "vertical")):
            m = _CONTRAINTES.get(str(c.get(cle) or ""))
            if m:
                out[ax] = m
        return out

    def visiter(n):
        if n.get("visible", True) is False:
            return
        t = n.get("type")
        nom = n.get("name") or t
        if t in _RECURSIFS and n is not cadre:
            for e in n.get("children") or []:
                visiter(e)
            return
        if n is cadre:
            for e in n.get("children") or []:
                visiter(e)
            return
        b, coupe = boite(n)
        if b is None:
            avert.append(f"« {nom} » est hors du cadre : sauté.")
            return
        if coupe:
            avert.append(f"« {nom} » débordait du cadre : coupé à la toile.")
        x, y, w, h = b
        z[0] += 1
        r = {"id": ident(n), "x": x, "y": y, "width": w, "height": h, "z_index": z[0]}
        cs = contraintes(n)
        if cs:
            r["constraints"] = cs
        if t == "TEXT":
            st = n.get("style") or {}
            r.update(type="text", text=str(n.get("characters") or ""), size=max(8, round(float(st.get("fontSize") or 32))))
            sol = _remplissage(n, "SOLID")
            if sol:
                r["color"] = _hex(sol.get("color"), "#ffffff")
            if st.get("textAlignHorizontal") == "CENTER":
                r["align"] = "center"
            pol = _police(st.get("fontFamily"))
            if pol:
                r["font"] = pol
            elif st.get("fontFamily"):
                avert.append(f"« {nom} » : la fonte « {st.get('fontFamily')} » n'est pas livrée, celle par défaut la remplace.")
            regions.append(r)
            return
        img = _remplissage(n, "IMAGE")
        if img and img.get("imageRef"):
            r.update(type="image_slot", slot_name=_slot(nom, slots), slot_label=str(nom)[:60], fit="cover")
            if t == "ELLIPSE":
                r["mask"] = {"shape": "ellipse"}
            elif float(n.get("cornerRadius") or 0) > 0:
                r["mask"] = {"shape": "rounded", "radius": round(float(n["cornerRadius"]))}
            images.append((r["slot_name"], img["imageRef"]))
            regions.append(r)
            return
        sol = _remplissage(n, "SOLID")
        if sol and t in ("RECTANGLE", "ELLIPSE", "VECTOR", "LINE", "REGULAR_POLYGON", "STAR"):
            coul = _hex(sol.get("color"))
            if h <= 12 or w <= 12:
                r.update(type="separator", color=coul)
            else:
                r.update(type="brand_strip", background_color=coul, items=[])
                if t != "RECTANGLE" or float(n.get("cornerRadius") or 0) > 0:
                    avert.append(f"« {nom} » : forme ou coins arrondis non repris (fond rectangulaire).")
            regions.append(r)
            return
        avert.append(f"« {nom} » ({t}) n'a pas d'équivalent dans un gabarit : sauté.")

    visiter(cadre)
    if not regions:
        raise ValueError("Le cadre ne contient aucun calque reprenable (texte, image ou rectangle plein).")
    tpl = {"id": "", "name": str(cadre.get("name") or "Import Figma")[:120],
           "canvas": {"width": W, "height": H, "fps": 30, "duration_s": 8, "background_color": _hex(fond.get("color"), "#000000") if fond else "#000000"},
           "regions": regions, "metadata": {"source": "figma"}}
    return tpl, images, avert


async def importer_gabarit(url: str, jeton: str, engine, dossier_images) -> dict:
    """{template_id, name, warnings, appels, images}. ValueError = lien ou cadre fautif (400) ; RuntimeError = Figma
    fautif (502)."""
    cible = FI.figma_cible(url)
    rep = await FI._get_json(f"https://api.figma.com/v1/files/{cible['cle']}/nodes?ids={cible['node']}", jeton)
    appels = 1
    if rep.get("err"):
        raise RuntimeError(str(rep["err"]))
    noeud = ((rep.get("nodes") or {}).get(cible["node"]) or {}).get("document")
    if not isinstance(noeud, dict):
        raise RuntimeError("Figma n'a pas rendu ce calque (lien périmé ou droits insuffisants).")
    tpl, images, avert = convertir(noeud)
    ech, faits = {}, []
    if images:
        rep2 = await FI._get_json(f"https://api.figma.com/v1/files/{cible['cle']}/images", jeton)
        appels += 1
        liens = ((rep2.get("meta") or {}).get("images") or {}) if not rep2.get("err") else {}
        dossier = Path(dossier_images)
        dossier.mkdir(parents=True, exist_ok=True)
        for slot, ref in images:
            lien = liens.get(ref)
            octets = await FI._get_bytes(str(lien)) if lien else b""
            if not octets:
                avert.append(f"L'image de « {slot} » n'a pas pu être récupérée : la case restera vide (mire).")
                continue
            ext = ".png" if octets.startswith(FI._PNG_MAGIC) else ".jpg" if octets[:3] == b"\xff\xd8\xff" else None
            if ext is None:
                avert.append(f"L'image de « {slot} » n'est ni PNG ni JPEG : ignorée.")
                continue
            nom = f"figma_{cible['cle']}_{re.sub(r'[^A-Za-z0-9]+', '', ref)[:24]}{ext}"
            (dossier / nom).write_bytes(octets)
            ech[slot] = nom
            faits.append(nom)
    if ech:
        tpl["metadata"]["samples"] = ech
    tid = engine.save_template(tpl)                  # valide par le moteur (ValueError -> 400)
    return {"template_id": tid, "name": tpl["name"], "warnings": avert, "appels": appels, "images": faits}


def _attr(v) -> str:
    """Une valeur d'ATTRIBUT XML : escape() seul laisse passer les guillemets (une fonte « "x" » cassait le SVG,
    trouve par le banc)."""
    return escape(str(v), {'"': "&quot;"})


def vers_svg(tpl: dict, dossier_images=None) -> str:
    """Le gabarit (deplie, kit applique par l'appelant) en SVG SCHEMATIQUE : a glisser dans Figma."""
    c = tpl.get("canvas") or {}
    W, H = int(c.get("width") or 1080), int(c.get("height") or 1920)
    ech = ((tpl.get("metadata") or {}).get("samples") or {}) if isinstance(tpl.get("metadata"), dict) else {}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<title>{escape(str(tpl.get("name") or "Gabarit"))}</title>',
           f'<rect id="fond" x="0" y="0" width="{W}" height="{H}" fill="{_attr(str(c.get("background_color") or "#000000"))}"/>']
    for r in sorted(tpl.get("regions") or [], key=lambda q: q.get("z_index") or 0):
        if r.get("type") == "audio_slot" or not all(isinstance(r.get(k), (int, float)) for k in ("x", "y", "width", "height")):
            continue
        x, y, w, h = (int(r[k]) for k in ("x", "y", "width", "height"))
        rid = _attr(r.get("id"))
        t = r.get("type")
        m = r.get("mask") or {}
        rx = int(m.get("radius") or 0) if m.get("shape") == "rounded" else 0
        if t in ("video_slot", "image_slot"):
            f = ech.get(r.get("slot_name"))
            p = Path(dossier_images) / Path(f).name if (f and dossier_images) else None
            if p is not None and p.is_file():
                mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
                data = base64.b64encode(p.read_bytes()).decode("ascii")
                out.append(f'<image id="{rid}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" href="data:{mime};base64,{data}"/>')
            else:
                out.append(f'<rect id="{rid}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="none" stroke="#00e5ff" stroke-dasharray="12 8" stroke-width="3"/>')
                out.append(f'<text x="{x + w / 2:g}" y="{y + h / 2:g}" font-family="Space Grotesk" font-size="{max(12, min(w, h) // 10)}" fill="#00e5ff" text-anchor="middle">{escape(str(r.get("slot_label") or r.get("slot_name") or ""))}</text>')
        elif t in ("separator", "brand_strip", "badge", "ticker"):
            coul = r.get("color") if t == "separator" else r.get("background_color") or "#02060d"
            out.append(f'<rect id="{rid}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{_attr(str(coul))}"/>')
        if t in ("text", "text_slot", "badge", "ticker"):
            txt = r.get("text") if t != "text_slot" else r.get("default_text")
            if txt:
                taille = int(r.get("size") or 48)
                ctr = r.get("align") == "center" or t == "badge"
                tx = x + w / 2 if ctr else x
                out.append(f'<text id="{rid}_texte" x="{tx:g}" y="{y + taille:g}" font-family="{_attr(str(r.get("font") or "Space Grotesk"))}" '
                           f'font-size="{taille}" fill="{_attr(str(r.get("color") or "#ffffff"))}"{" text-anchor=\"middle\"" if ctr else ""}>{escape(str(txt))}</text>')
    out.append("</svg>")
    return "\n".join(out)
