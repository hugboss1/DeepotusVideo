# -*- coding: utf-8 -*-
"""t314 (28/10/2026) (C2 Scan, spec boîte à outils §7.3) — les calques d'un document du Vectorlab deviennent une base
d'animation : éléments du nœud Animation (t231-t241), page du nœud « Rendu motion code » (t238) et graphe Studio prêt à
ouvrir (contrat `window.__dzRenderGraph` du bundle, celui d'« Envoyer vers › Studio » de la Bibliothèque).

Tout est déterministe, local et gratuit : aucune IA ici. « Chorégraphier » (nœud Animation) et « Écrire la page »
(motion code) restent des boutons du Studio, avec leur devis.

- Le document est ajusté à 90 % du cadre du format choisi (`aspect_pour` : le format du nœud le plus proche de son
  rapport), centré ; un élément est placé par le CENTRE de sa boîte, à l'échelle ajustement × boîte / largeur du PNG
  (`animation_service.render_element` pose l'image à sa taille × scale, centrée sur x/y en %).
- Les éléments entrent dans l'ordre reçu (l'ordre de révélation) et restent jusqu'à la fin : formes « pop », flèches qui
  glissent depuis leur queue, étiquettes en fondu ; clés bornées comme celles du chorégraphe.
- La page motion code est écrite par nous : données en BASE64 (aucune balise ni mot de l'utilisateur lisible par le
  contrôle statique), images en data:, aucune URL ; les flèches se dévoilent de la queue vers la pointe (clip-path).
"""
from __future__ import annotations

import base64
import io
import json
import re

from app.services import animation_service as AS

FORMATS = {"9:16": 9 / 16, "4:5": 4 / 5, "1:1": 1.0, "16:9": 16 / 9}
DUREE = (4.0, 30.0)
ENTREE = 0.6
AJUSTE = 0.9
FPS = 30
_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def aspect_pour(w, h) -> str:
    r = float(w) / max(1.0, float(h))
    return min(FORMATS, key=lambda k: abs(FORMATS[k] - r) / FORMATS[k])


def duree_pour(n: int) -> float:
    return round(min(DUREE[1], max(DUREE[0], 1.5 + 0.7 * max(0, int(n)))), 2)


def couleur(c, defaut="#FFFFFF") -> str:
    return c.upper() if isinstance(c, str) and _COULEUR.match(c) else defaut


def _cadre(largeur, hauteur, aspect):
    W, H = AS._wh(aspect)
    f = AJUSTE * min(W / float(largeur), H / float(hauteur))
    return W, H, f, (W - largeur * f) / 2, (H - hauteur * f) / 2


def _b(v, lo, hi):
    return round(min(hi, max(lo, float(v))), 4)


def _cle(t, x, y, sc, op, ez="linear"):
    return {"t": t, "x": _b(x, 0, 100), "y": _b(y, 0, 100), "scale": round(max(0.01, sc), 5), "rotation": 0,
            "opacity": _b(op, 0, 1), "easing": ez}


def _temps(n, duree_s):
    pas = (duree_s - 1.5) / max(1, n)
    return [round(0.3 + i * pas, 3) for i in range(n)]


def elements(calques: list, largeur, hauteur, aspect: str, duree_s: float) -> list:
    """Les éléments `image` du nœud Animation, un par calque, dans l'ordre reçu. ValueError sans calque."""
    if not calques:
        raise ValueError("aucun calque à animer")
    W, H, f, ox, oy = _cadre(largeur, hauteur, aspect)
    out = []
    for i, (c, debut) in enumerate(zip(calques, _temps(len(calques), duree_s))):
        b = c["boite"]
        x = 100 * (ox + (b["x"] + b["w"] / 2) * f) / W
        y = 100 * (oy + (b["y"] + b["h"] / 2) * f) / H
        sc = f * b["w"] / max(1, c["largeur_png"])
        nat = c.get("nature")
        if nat == "fleche" and c.get("queue") and c.get("pointe"):
            dx = 100 * (c["pointe"]["x"] - c["queue"]["x"]) * f / W
            dy = 100 * (c["pointe"]["y"] - c["queue"]["y"]) * f / H
            kf = [_cle(0, x - 0.3 * dx, y - 0.3 * dy, sc, 0, "easeOut"), _cle(1, x, y, sc, 1)]
        elif nat == "etiquette":
            kf = [_cle(0, x, y + 2, sc, 0, "easeOut"), _cle(1, x, y, sc, 1)]
        else:
            kf = [_cle(0, x, y, sc * 0.3, 0, "easeOutBack"), _cle(1, x, y, sc, 1)]
        dur = ENTREE
        out.append({"id": f"el_s{i:02d}", "type": "image", "filename": c["image"], "nom": str(c.get("nom") or "")[:120],
                    "style": {}, "keyframes": kf, "start": debut, "dur": dur,
                    "hold": round(max(0.0, duree_s - debut - dur), 3), "preset": None})
    return out


def png_fond(aspect: str, fond: str) -> bytes:
    """Le fond plein du cadre (le nœud Animation peint sinon un bleu nuit : un schéma au trait noir y disparaîtrait)."""
    from PIL import Image
    f = io.BytesIO()
    Image.new("RGB", AS._wh(aspect), couleur(fond)).save(f, format="PNG")
    return f.getvalue()


def element_fond(filename: str, duree_s: float) -> dict:
    k = {"x": 50, "y": 50, "scale": 1, "rotation": 0, "opacity": 1, "easing": "linear"}
    return {"id": "el_fond", "type": "image", "filename": filename, "nom": "fond", "style": {},
            "keyframes": [dict(k, t=0), dict(k, t=1)], "start": 0, "dur": 0.05,
            "hold": round(max(0.0, duree_s - 0.05), 3), "preset": None}


_JS = r"""var D=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(document.getElementById("dz-donnees").textContent),
function(c){return c.charCodeAt(0)}))),S=document.getElementById("dz-scene");S.style.background=D.fond;
function ez(n,u){u=Math.min(1,Math.max(0,u));if(n==="pop"){var c=1.70158;return 1+(c+1)*Math.pow(u-1,3)+c*Math.pow(u-1,2)}
return 1-Math.pow(1-u,3)}
var E=D.elements.map(function(e){var im=document.createElement("img");im.src="data:image/png;base64,"+e.png;
im.style.cssText="position:absolute;left:"+e.x+"px;width:"+e.w+"px;height:"+e.h+"px;transform-origin:center;opacity:0";
im.style.marginTop=e.y+"px";S.appendChild(im);return{e:e,d:im}});
window.dzFrame=function(t){E.forEach(function(o){var e=o.e,u=Math.min(1,Math.max(0,(t-e.start)/e.dur));
if(t<e.start){o.d.style.opacity=0;return}
if(e.nature==="fleche"){var p=(1-ez("out",u))*100,dx=e.dx,dy=e.dy,r="0 0 0 0";
if(Math.abs(dx)>=Math.abs(dy))r=dx>=0?"0 "+p+"% 0 0":"0 0 0 "+p+"%";else r=dy>=0?"0 0 "+p+"% 0":p+"% 0 0 0";
o.d.style.clipPath="inset("+r+")";o.d.style.opacity=1}
else if(e.nature==="etiquette"){o.d.style.opacity=ez("out",u);o.d.style.transform="translateY("+((1-ez("out",u))*12)+"px)"}
else{o.d.style.opacity=Math.min(1,u*2);o.d.style.transform="scale("+(0.3+0.7*ez("pop",u))+")"}})};"""


def page(calques: list, largeur, hauteur, aspect: str, duree_s: float, fond: str = "#FFFFFF") -> str:
    """La page du nœud « Rendu motion code » : `calques` portent leurs `octets` PNG ; ValueError sans calque."""
    if not calques:
        raise ValueError("aucun calque à animer")
    W, H, f, ox, oy = _cadre(largeur, hauteur, aspect)
    els = []
    for c, debut in zip(calques, _temps(len(calques), duree_s)):
        b = c["boite"]
        e = {"png": base64.b64encode(c["octets"]).decode("ascii"), "nature": c.get("nature") or "forme",
             "x": round(ox + b["x"] * f, 2), "y": round(oy + b["y"] * f, 2), "w": round(b["w"] * f, 2),
             "h": round(b["h"] * f, 2), "start": debut, "dur": ENTREE, "dx": 0, "dy": 0}
        if c.get("queue") and c.get("pointe"):
            e["dx"] = c["pointe"]["x"] - c["queue"]["x"]
            e["dy"] = c["pointe"]["y"] - c["queue"]["y"]
        els.append(e)
    donnees = json.dumps({"elements": els, "fond": couleur(fond)}, ensure_ascii=True)
    donnees = base64.b64encode(donnees.encode("utf-8")).decode("ascii")
    return ('<!doctype html><html><head><style>#dz-scene{position:absolute;inset:0;overflow:hidden;background:%s}'
            '#dz-scene img{top:0}</style></head><body><div id="dz-scene"></div>'
            '<script type="application/octet-stream" id="dz-donnees">%s</script><script>%s</script></body></html>'
            % (couleur(fond), donnees, _JS))


def graphe(nom: str, elements_: list, page_id: str, script: str, aspect: str, duree_s: float) -> dict:
    """Le graphe Studio : Animation (en tête : le Studio sélectionne le premier nœud), Direction motion, Rendu motion
    code et Render au format."""
    nom = str(nom or "Schéma").strip()[:100] or "Schéma"
    return {"name": nom + ".graph",
            "nodes": [
                {"id": "an1", "type": "Animation", "x": 420, "y": 200,
                 "props": {"durationS": duree_s, "fps": FPS, "elements": elements_, "selected": 0,
                           "script": script}},
                {"id": "md1", "type": "MotionDirection", "x": 120, "y": 120, "props": {}},
                {"id": "mc1", "type": "MotionCode", "x": 420, "y": 420,
                 "props": {"script": script, "durationS": duree_s, "fps": FPS, "pageId": page_id}},
                {"id": "rn1", "type": "Render", "x": 760, "y": 200, "props": {"format": aspect, "name": nom[:60]}}],
            "edges": [
                {"id": "e1", "from": "md1", "fromPort": "direction", "to": "an1", "toPort": "direction"},
                {"id": "e2", "from": "md1", "fromPort": "direction", "to": "mc1", "toPort": "direction"},
                {"id": "e3", "from": "an1", "fromPort": "out", "to": "rn1", "toPort": "in"}]}
