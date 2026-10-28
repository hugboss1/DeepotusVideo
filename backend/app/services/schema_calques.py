# -*- coding: utf-8 -*-
"""t314 (28/10/2026) (C2 Scan : illustration ou schéma → base d'animation motion, spec boîte à outils §7.3) — séparer,
classer, relier et ordonner les éléments d'une image détourée.

Pillow seul : le python embarqué n'a pas numpy. L'analyse se fait sur le masque réduit à `COTE_ANALYSE` px de plus
grand côté (composantes 8-connexes par parcours en largeur) ; les découpes rendues sont à la définition d'origine.

- **Masque** (`masque_de`) : l'alpha de l'image s'il y en a un ; sinon la couleur médiane du POURTOUR est le fond
  (« fond estimé ») — même principe que `pixel_ops.chroma_key`, sans sa garde de couverture de 5 % qui refuse un schéma
  au trait (quelques traits fins sur une page blanche). Pourtour pas assez uni → ValueError("fond_non_uni").
- **Étiquettes** : les lignes de la lecture de t312 (`scan_ocr.lire_page`, boîtes dans le repère de l'image d'origine).
  Une composante dont 60 % de la boîte tombe dans une ligne lue est un GLYPHE : elle n'est ni forme ni flèche (le texte
  devient un objet texte du Vectorlab). Les lignes d'une même forme forment UNE étiquette ; une ligne libre se rattache à
  la flèche la plus proche, sinon à rien.
- **Forme ou flèche** : une composante qui ENFERME du fond (≥ 2 % de sa boîte) est une forme ; sinon on mesure sa
  longueur géodésique L (double balayage) : L / √(pixels) ≥ 2,5 → flèche (long et fin), sinon forme (pleine).
- **Pointe** : l'extrémité la plus massive dans un rayon de min(6 × épaisseur, 0,35 L) ; rapport < 1,25 (trait nu,
  double pointe) → flèche NON dirigée : aucun lien orienté n'est inventé.
- **Liens** : la forme dont la boîte, élargie de 3 % de la diagonale, contient la queue (départ) ou la pointe (arrivée).
- **Ordre de révélation** (choix de Claude, §7.3) : tri topologique des formes par les flèches, à égalité l'ordre de
  lecture (bandes de haut en bas, puis de gauche à droite) ; une flèche juste après sa forme de départ ; une étiquette
  juste après son parent ; un cycle se rompt à la forme restante la plus haut-gauche ; une flèche sans départ vient juste
  avant sa cible ; le reste à la fin, en ordre de lecture.
- Au-delà de `MAX_ELEMENTS`, les plus petites formes ou flèches sont fondues dans UN élément « Détails ».

Aucun journal ici ; le texte lu n'est jamais écrit ailleurs que dans le résultat.
"""
from __future__ import annotations

import io
import math
from collections import deque

from PIL import Image, ImageChops, ImageFilter

COTE_ANALYSE = 600
MAX_ELEMENTS = 40
SEUIL_ALLONGE = 2.5
SEUIL_POINTE = 1.25
BRUIT = 0.0002                 # part de l'aire réduite sous laquelle une composante est du bruit
TROU_MIN = 0.02                # part de la boîte : fond enfermé qui fait une forme
GLYPHE = 0.6                   # part de la boîte d'une composante dans une ligne lue : un glyphe
TOLERANCE_LIEN = 0.03          # part de la diagonale : marge d'une forme pour accrocher une extrémité de flèche
ECART_FOND = 40                # écart (niveaux L) au fond estimé au-delà duquel un pixel est du dessin
MAX_NOM = 40

NOMS = {
    "fr": {"forme": "Forme {n}", "fleche": "Flèche {n}", "etiquette": "Étiquette {n}", "details": "Détails"},
    "en": {"forme": "Shape {n}", "fleche": "Arrow {n}", "etiquette": "Label {n}", "details": "Details"},
}


# ── le masque ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _fond_du_pourtour(rgb: Image.Image):
    w, h = rgb.size
    px = rgb.load()
    pas = max(1, (w + h) // 128)
    ech = [px[x, 0] for x in range(0, w, pas)] + [px[x, h - 1] for x in range(0, w, pas)]
    ech += [px[0, y] for y in range(0, h, pas)] + [px[w - 1, y] for y in range(0, h, pas)]
    cle = tuple(sorted(e[i] for e in ech)[len(ech) // 2] for i in range(3))
    proches = sum(1 for e in ech if sum(abs(e[i] - cle[i]) for i in range(3)) <= 84)
    return cle, proches / max(1, len(ech))


def masque_de(img: Image.Image):
    """(masque « L » 0/255, estime). L'alpha s'il y a de la transparence, sinon le fond estimé par le pourtour."""
    rgba = img.convert("RGBA")
    a = rgba.getchannel("A")
    if a.getextrema()[0] < 255:
        return a.point(lambda v: 255 if v > 127 else 0), False
    rgb = rgba.convert("RGB")
    cle, part = _fond_du_pourtour(rgb)
    if part < 0.6:
        raise ValueError("fond_non_uni")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, cle)).convert("L")
    m = diff.point(lambda v: 255 if v > ECART_FOND else 0)
    if m.getbbox() is None:
        raise ValueError("image_vide")
    return m, True


# ── les composantes (masque réduit) ─────────────────────────────────────────────────────────────────────────────────
def _composantes(petit: Image.Image) -> list:
    w, h = petit.size
    d = petit.tobytes()
    lab = bytearray(w * h)          # 0 = pas vu ; 1 = vu
    out = []
    for i0 in range(w * h):
        if not d[i0] or lab[i0]:
            continue
        lab[i0] = 1
        pile = deque([i0])
        pix = []
        while pile:
            i = pile.popleft()
            pix.append(i)
            y, x = divmod(i, w)
            for dy in (-1, 0, 1):
                yy = y + dy
                if yy < 0 or yy >= h:
                    continue
                base = yy * w
                for dx in (-1, 0, 1):
                    xx = x + dx
                    if 0 <= xx < w:
                        j = base + xx
                        if d[j] and not lab[j]:
                            lab[j] = 1
                            pile.append(j)
        xs = [i % w for i in pix]
        ys = [i // w for i in pix]
        out.append({"pix": pix, "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)})
    return out


def _trous(c: dict, w: int) -> int:
    """Le fond enfermé par la composante dans sa boîte (+1) : ce que le remplissage depuis le bord n'atteint pas."""
    x0, y0 = c["x0"] - 1, c["y0"] - 1
    bw, bh = c["x1"] - c["x0"] + 3, c["y1"] - c["y0"] + 3
    plein = bytearray(bw * bh)
    for i in c["pix"]:
        y, x = divmod(i, w)
        plein[(y - y0) * bw + (x - x0)] = 1
    vu = bytearray(bw * bh)
    pile = deque([0])
    vu[0] = 1
    atteint = 1
    while pile:
        i = pile.popleft()
        y, x = divmod(i, bw)
        for j in ((i - bw) if y else -1, (i + bw) if y < bh - 1 else -1, (i - 1) if x else -1, (i + 1) if x < bw - 1 else -1):
            if j >= 0 and not vu[j] and not plein[j]:
                vu[j] = 1
                atteint += 1
                pile.append(j)
    return bw * bh - len(c["pix"]) - atteint


def _bfs_loin(ens: set, depart: int, w: int):
    dist = {depart: 0}
    pile = deque([depart])
    loin = depart
    while pile:
        i = pile.popleft()
        if dist[i] > dist[loin]:
            loin = i
        y, x = divmod(i, w)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                j = (y + dy) * w + (x + dx)
                if (dy or dx) and 0 <= x + dx < w and j in ens and j not in dist:
                    dist[j] = dist[i] + 1
                    pile.append(j)
    return loin, dist[loin]


def _masse(c: dict, w: int, centre: int, r: float) -> int:
    cy, cx = divmod(centre, w)
    r2 = r * r
    return sum(1 for i in c["pix"] if (i % w - cx) ** 2 + (i // w - cy) ** 2 <= r2)


# ── l'analyse ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _boite_orig(c, s, W, H) -> dict:
    x0 = max(0, int(math.floor(c["x0"] / s)))
    y0 = max(0, int(math.floor(c["y0"] / s)))
    x1 = min(W, int(math.ceil((c["x1"] + 1) / s)))
    y1 = min(H, int(math.ceil((c["y1"] + 1) / s)))
    return {"x": x0, "y": y0, "w": max(1, x1 - x0), "h": max(1, y1 - y0)}


def _inter(a: dict, b: dict) -> float:
    l = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    h = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return l * h


def _union(bs: list) -> dict:
    x0, y0 = min(b["x"] for b in bs), min(b["y"] for b in bs)
    x1, y1 = max(b["x"] + b["w"] for b in bs), max(b["y"] + b["h"] for b in bs)
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _centre(b: dict):
    return b["x"] + b["w"] / 2, b["y"] + b["h"] / 2


def _dist_boite(b: dict, x: float, y: float) -> float:
    dx = max(b["x"] - x, 0, x - (b["x"] + b["w"]))
    dy = max(b["y"] - y, 0, y - (b["y"] + b["h"]))
    return math.hypot(dx, dy)


def _dist_segment(px, py, a: dict, b: dict) -> float:
    ax, ay, bx, by = a["x"], a["y"], b["x"], b["y"]
    vx, vy = bx - ax, by - ay
    n = vx * vx + vy * vy
    t = 0 if n == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / n))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def _boite_de_ligne(li: dict):
    mots = [m for m in li.get("mots") or [] if all(isinstance(m.get(k), (int, float)) for k in ("x", "y", "l", "h"))]
    if not mots:
        return None
    return _union([{"x": m["x"], "y": m["y"], "w": m["l"], "h": m["h"]} for m in mots])


def _couleur_texte(rgb: Image.Image, b: dict) -> str:
    x0, y0 = max(0, int(b["x"])), max(0, int(b["y"]))
    x1, y1 = min(rgb.width, int(b["x"] + b["w"]) + 1), min(rgb.height, int(b["y"] + b["h"]) + 1)
    if x1 <= x0 or y1 <= y0:
        return "#1F1512"
    cr = rgb.crop((x0, y0, x1, y1))
    cr.thumbnail((80, 80))
    px = list(cr.getdata())
    quant = {}
    for p in px:
        k = (p[0] // 32, p[1] // 32, p[2] // 32)
        quant[k] = quant.get(k, 0) + 1
    fk = max(quant, key=quant.get)
    fond = (fk[0] * 32 + 16, fk[1] * 32 + 16, fk[2] * 32 + 16)
    loin = [p for p in px if sum(abs(p[i] - fond[i]) for i in range(3)) > 120]
    if not loin:
        return "#1F1512"
    m = [sum(p[i] for p in loin) // len(loin) for i in range(3)]
    return "#%02X%02X%02X" % tuple(m)


def _png(rgba: Image.Image, masque: Image.Image, petit_comp: Image.Image, b: dict, s: float):
    """La découpe RGBA de la boîte `b`, limitée aux pixels de la composante ; (octets PNG, boîte resserrée)."""
    zone = (b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"])
    cm = petit_comp.filter(ImageFilter.MaxFilter(3))
    lx0, ly0 = int(b["x"] * s), int(b["y"] * s)
    lx1 = min(cm.width, max(lx0 + 1, int(math.ceil((b["x"] + b["w"]) * s))))
    ly1 = min(cm.height, max(ly0 + 1, int(math.ceil((b["y"] + b["h"]) * s))))
    m = cm.crop((lx0, ly0, lx1, ly1)).resize((b["w"], b["h"]), Image.NEAREST)
    # l'agrandissement part du coin bas de la zone réduite : on le recale sur la boîte d'origine
    a = ImageChops.multiply(masque.crop(zone), m)
    bb = a.getbbox()
    if bb is None:
        return None, b
    out = rgba.crop(zone)
    out.putalpha(ImageChops.multiply(out.getchannel("A"), a))
    out = out.crop(bb)
    nb = {"x": b["x"] + bb[0], "y": b["y"] + bb[1], "w": bb[2] - bb[0], "h": bb[3] - bb[1]}
    f = io.BytesIO()
    out.save(f, format="PNG", optimize=False)
    return f.getvalue(), nb


def analyser(img: Image.Image, lignes: list, langue: str = "fr") -> dict:
    """Voir l'en-tête du module. `lignes` : celles de `scan_ocr.lire_page` (repère de l'image d'origine)."""
    lg = "en" if langue == "en" else "fr"
    rgba = img.convert("RGBA")
    W, H = rgba.size
    masque, estime = masque_de(rgba)
    if estime:
        rgba.putalpha(masque)
    avert = ["fond_estime"] if estime else []
    s = min(1.0, COTE_ANALYSE / max(W, H))
    sw, sh = max(1, round(W * s)), max(1, round(H * s))
    petit = masque.resize((sw, sh), Image.BOX).point(lambda v: 255 if v > 40 else 0) if s < 1 else masque
    s_x, s_y = sw / W, sh / H
    s = min(s_x, s_y)
    comps = [c for c in _composantes(petit) if len(c["pix"]) >= max(4, BRUIT * sw * sh)]

    # les lignes lues
    lues = []
    for li in lignes or []:
        if not isinstance(li, dict):
            continue
        b = _boite_de_ligne(li)
        t = str(li.get("texte") or "").strip()
        if b and t:
            lues.append({"texte": t, "boite": {k: round(v, 1) for k, v in b.items()}})
    gros = [{"x": l["boite"]["x"] - 2, "y": l["boite"]["y"] - 2, "w": l["boite"]["w"] + 4, "h": l["boite"]["h"] + 4}
            for l in lues]

    diag = math.hypot(W, H)
    rgb = img.convert("RGB")
    elems = []
    for c in comps:
        b = _boite_orig(c, s, W, H)
        aire = b["w"] * b["h"]
        if gros and any(_inter(b, g) >= GLYPHE * aire for g in gros):
            continue                                            # un glyphe : le texte devient une étiquette
        e = {"c": c, "boite": b, "n": len(c["pix"])}
        bw, bh = c["x1"] - c["x0"] + 1, c["y1"] - c["y0"] + 1
        if _trous(c, sw) >= max(4, TROU_MIN * bw * bh):
            e["nature"] = "forme"
        else:
            ens = set(c["pix"])
            a, _ = _bfs_loin(ens, c["pix"][0], sw)
            bpt, L = _bfs_loin(ens, a, sw)
            if L / math.sqrt(len(c["pix"])) >= SEUIL_ALLONGE:
                e["nature"] = "fleche"
                ep = len(c["pix"]) / max(1, L)
                r = max(3.0, min(6 * ep, 0.35 * L))
                ma, mb = _masse(c, sw, a, r), _masse(c, sw, bpt, r)
                tete, queue = (bpt, a) if mb >= ma else (a, bpt)
                rapport = max(ma, mb) / max(1, min(ma, mb))
                e["dirigee"] = rapport >= SEUIL_POINTE
                qy, qx = divmod(queue, sw)
                ty, tx = divmod(tete, sw)
                e["queue"] = {"x": round((qx + 0.5) / s, 1), "y": round((qy + 0.5) / s, 1)}
                e["pointe"] = {"x": round((tx + 0.5) / s, 1), "y": round((ty + 0.5) / s, 1)}
            else:
                e["nature"] = "forme"
        elems.append(e)

    # au-delà de MAX_ELEMENTS (étiquettes comprises, estimées par les lignes) : les plus petites fondues en « Détails »
    place = MAX_ELEMENTS - min(len(lues), MAX_ELEMENTS // 2)
    details = None
    if len(elems) > place:
        elems.sort(key=lambda e: -e["n"])
        reste, elems = elems[place - 1:], elems[:place - 1]
        pix = [i for e in reste for i in e["c"]["pix"]]
        xs, ys = [i % sw for i in pix], [i // sw for i in pix]
        c = {"pix": pix, "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)}
        details = {"c": c, "boite": _boite_orig(c, s, W, H), "n": len(pix), "nature": "details"}

    formes = [e for e in elems if e["nature"] == "forme"]
    fleches = [e for e in elems if e["nature"] == "fleche"]

    # les liens
    tol = TOLERANCE_LIEN * diag

    def forme_pres(pt):
        cands = [(_dist_boite(f["boite"], pt["x"], pt["y"]), f["n"] * -1, k) for k, f in enumerate(formes)]
        cands = [c for c in cands if c[0] <= tol]
        return formes[min(cands)[2]] if cands else None

    for fl in fleches:
        fq, fp = forme_pres(fl["queue"]), forme_pres(fl["pointe"])
        if fq is fp:
            fp = None if fl["dirigee"] else fp
        fl["de"], fl["vers"] = (fq, fp) if fl["dirigee"] else (None, None)
        fl["relie"] = [f for f in (fq, fp) if f is not None]

    # les étiquettes : lignes regroupées par forme qui les contient (la plus petite), sinon une par ligne
    etiqs = []
    par_forme = {}
    for l in lues:
        cx, cy = _centre(l["boite"])
        dedans = [f for f in formes if _dist_boite(f["boite"], cx, cy) == 0]
        if dedans:
            f = min(dedans, key=lambda f: f["boite"]["w"] * f["boite"]["h"])
            par_forme.setdefault(id(f), (f, []))[1].append(l)
        else:
            proche = None
            if fleches:
                dd = min(((_dist_segment(cx, cy, fl["queue"], fl["pointe"]), k) for k, fl in enumerate(fleches)))
                if dd[0] <= 2 * tol:
                    proche = fleches[dd[1]]
            etiqs.append({"nature": "etiquette", "lignes": [l], "parent": proche})
    for f, ls in par_forme.values():
        etiqs.append({"nature": "etiquette", "lignes": ls, "parent": f})
    for e in etiqs:
        e["boite"] = _union([l["boite"] for l in e["lignes"]])
        e["texte"] = "\n".join(l["texte"] for l in e["lignes"])

    # ordre de lecture
    bande = max(1.0, H / 12)

    def cle(e):
        cx, cy = _centre(e["boite"])
        return (int(cy // bande), cx)

    ordre = []
    vus = set()

    def poser(e):
        if id(e) in vus:
            return
        vus.add(id(e))
        ordre.append(e)
        for t in sorted((t for t in etiqs if t["parent"] is e), key=cle):
            poser(t)

    restant = sorted(formes, key=cle)
    while restant:
        prets = [f for f in restant
                 if not any(fl["vers"] is f and fl["de"] is not None and id(fl["de"]) not in vus and fl["de"] is not f
                            for fl in fleches)]
        f = (prets or restant)[0]
        restant.remove(f)
        for fl in sorted((fl for fl in fleches if fl["vers"] is f and fl["de"] is None), key=cle):
            poser(fl)
        poser(f)
        for fl in sorted((fl for fl in fleches if fl["de"] is f), key=lambda fl: cle(fl["vers"] or fl)):
            poser(fl)
        for fl in fleches:
            if not fl["dirigee"] and fl["relie"] and all(id(x) in vus for x in fl["relie"]):
                poser(fl)
    for e in sorted([fl for fl in fleches if id(fl) not in vus] + [t for t in etiqs if id(t) not in vus], key=cle):
        poser(e)
    if details:
        poser(details)

    # identifiants, noms, découpes
    for k, e in enumerate(ordre):
        e["id"] = f"e{k + 1:02d}"
    nums = {}
    for e in ordre:
        nums[e["nature"]] = nums.get(e["nature"], 0) + 1
        e["num"] = nums[e["nature"]]
    titres = NOMS[lg]

    def court(t):
        t = " ".join(str(t).split())
        return t if len(t) <= MAX_NOM else t[:MAX_NOM - 1] + "…"

    def appellation(f):
        lab = next((t for t in etiqs if t["parent"] is f), None)
        return court(lab["lignes"][0]["texte"]) if lab else titres["forme"].format(n=f["num"])

    sortie = []
    for e in ordre:
        nat = e["nature"]
        d = {"id": e["id"], "nature": nat, "ordre": len(sortie)}
        if nat == "forme":
            lab = next((t for t in etiqs if t["parent"] is e), None)
            d["nom"] = titres["forme"].format(n=e["num"]) + (" — " + court(lab["lignes"][0]["texte"]) if lab else "")
        elif nat == "fleche":
            nom = titres["fleche"].format(n=e["num"])
            if e["dirigee"] and (e["de"] or e["vers"]):
                nom += " : " + (appellation(e["de"]) if e["de"] else "?") + " → " + (appellation(e["vers"]) if e["vers"] else "?")
            elif len(e["relie"]) == 2:
                nom += " : " + appellation(e["relie"][0]) + " — " + appellation(e["relie"][1])
            d["nom"] = nom
            d.update(dirigee=e["dirigee"], queue=e["queue"], pointe=e["pointe"],
                     de=e["de"]["id"] if e["de"] else None, vers=e["vers"]["id"] if e["vers"] else None)
        elif nat == "etiquette":
            d["nom"] = titres["etiquette"].format(n=e["num"]) + " : " + court(e["lignes"][0]["texte"])
            d.update(texte=e["texte"], lignes=e["lignes"], couleur=_couleur_texte(rgb, e["boite"]),
                     parent=e["parent"]["id"] if e["parent"] else None)
        else:
            d["nom"] = titres["details"]
        if nat != "etiquette":
            d["parent"] = None
            cm = Image.new("L", (sw, sh), 0)
            px = cm.load()
            for i in e["c"]["pix"]:
                y, x = divmod(i, sw)
                px[x, y] = 255
            png, b = _png(rgba, masque, cm, e["boite"], s)
            e["boite"] = b
            if png is None:
                continue
            d["png"] = png
        d["boite"] = {k: round(v, 1) for k, v in e["boite"].items()}
        sortie.append(d)
    for k, d in enumerate(sortie):
        d["ordre"] = k
    liens = [{"fleche": d["id"], "de": d["de"], "vers": d["vers"]} for d in sortie
             if d["nature"] == "fleche" and d["de"] and d["vers"]]
    return {"largeur": W, "hauteur": H, "elements": sortie, "liens": liens, "avertissements": avert}
