"""Contrôle statique des SVG selon CHARTE.md. Usage : python -I lint.py <dossier_svg> [sortie_icons.json]
Écrit aussi un icons.json {cle: svg} pour le banc visuel."""
import json, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
D = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
ALLOWED = {"svg", "path", "rect", "circle", "ellipse", "polygon", "g", "line", "polyline"}
NS = "{http://www.w3.org/2000/svg}"
erreurs, icons = {}, {}
for f in sorted(p for p in D.glob("dz-*.svg") if p.stem != "dz-icons"):
    t = f.read_text(encoding="utf-8").strip()
    e = []
    try:
        root = ET.fromstring(t)
    except ET.ParseError as x:
        erreurs[f.stem] = [f"XML invalide : {x}"]; continue
    if root.get("viewBox") != "0 0 24 24": e.append("viewBox ≠ 0 0 24 24")
    if root.get("fill") != "currentColor": e.append("fill=currentColor absent de <svg>")
    for el in root.iter():
        tag = el.tag.replace(NS, "")
        if tag not in ALLOWED: e.append(f"balise interdite <{tag}>")
        for a, v in el.attrib.items():
            if a in ("fill", "stroke") and v not in ("currentColor", "none"): e.append(f"{a}={v}")
            if a == "opacity" and v not in (".38", "0.38", "1"): e.append(f"opacity={v}")
            if a == "stroke-width" and v != "2.6": e.append(f"stroke-width={v}")
            if a in ("style", "class", "transform") and tag == "svg": e.append(f"{a} sur <svg>")
            if a.startswith("on") or "href" in a: e.append(f"attribut interdit {a}")
        if tag != "svg" and el.get("stroke") not in (None, "none", "currentColor"):
            e.append("stroke non currentColor")
    nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", " ".join(
        el.get(a, "") for el in root.iter() for a in ("x", "y", "cx", "cy") ))]
    if any(n < 0.5 or n > 23.5 for n in nums): e.append("coordonnée hors de 0,5–23,5")
    if e: erreurs[f.stem] = sorted(set(e))
    icons[f.stem] = t
print(json.dumps({"fichiers": len(icons), "en_erreur": len(erreurs)}, ensure_ascii=False))
for k, v in erreurs.items():
    print(k, "→", "; ".join(v))
if out:
    out.write_text(json.dumps(icons, ensure_ascii=False), encoding="utf-8")
