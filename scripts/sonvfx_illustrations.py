# -*- coding: utf-8 -*-
"""Illustrations animées des gestes VFX IA (t275, lot « Menus : Son & VFX », 22/10/2026).

Une page HTML / SVG / Canvas par geste de `vfx_ia.REGISTRE` (scripts/sonvfx_illus/<id>.html), écrite par nous selon une
fiche de style MAISON (backend/app/motion/styles, déclarée par `<meta name="dz-skill" content="style-<thème>">`) : elle
montre l'EFFET produit en avant / après, sur 4 s en boucle, pilotée par `window.dzFrame(t)` (l'horloge virtuelle du bac
à sable). Décision Q3 : les illustrations sont rendues AU DÉVELOPPEMENT et livrées en statiques — aucun coût, aucun
navigateur à l'exécution.

Chaîne, pour chaque page :
  1. contrôle statique `motion_code.controler` (aucun réseau, aucune navigation, aucune ressource extérieure) ;
  2. rendu dans le bac à sable de `motion_code.rendre_page` par le chrome-headless-shell EMBARQUÉ (480×270, 30 i/s,
     4 s = 120 images, MP4 sans perte de cadence) ;
  3. ffmpeg : WebM VP9 sans son (≤ 250 Ko, débit abaissé tant qu'il le faut) et une affiche WebP à l'instant
     `dz-affiche` de la page ;
  4. manifeste frontend/dist/sonvfx/illus/index.json : l'EMPREINTE de chaque page rendue (une page modifiée sans
     nouveau rendu est vue par `--check`), les tailles, la version du moteur.

  python scripts/sonvfx_illustrations.py            # rend tout
  python scripts/sonvfx_illustrations.py eau jour-nuit
  python scripts/sonvfx_illustrations.py --check    # pages et rendus à jour (code de sortie 1 sinon)

Le moteur : DEEPOTUS_NAVIGATEUR, puis vendor/ du dépôt, puis celui de l'application installée
(%LOCALAPPDATA%\\DeepotusVideoGen\\vendor) ; jamais Edge, pour que les rendus ne dépendent pas du PC.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))

from app.services import motion_code as MC  # noqa: E402
from app.services import vfx_ia as VI  # noqa: E402

PAGES = RACINE / "scripts" / "sonvfx_illus"
SORTIE = RACINE / "frontend" / "dist" / "sonvfx" / "illus"
STYLES = RACINE / "backend" / "app" / "motion" / "styles"
W, H, FPS, DUREE = 480, 270, 30, 4
MAX_WEBM = 250_000
DEBITS = ("360k", "300k", "240k", "180k", "140k")      # VP9 contraint : le premier qui tient sous MAX_WEBM


def meta(html: str, nom: str):
    m = re.search(r'<meta\s+name="%s"\s+content="([^"]*)"' % re.escape(nom), html)
    return m.group(1) if m else None


def empreinte(html: str) -> str:
    """L'empreinte d'une page (blob git de son texte aux fins de ligne LF : la même sous Windows et ailleurs)."""
    b = html.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def _lire(p: Path) -> str:
    return p.read_bytes().decode("utf-8") if p.is_file() else ""


def verifier(registre=None, pages: Path = PAGES) -> list:
    """Les écarts des pages (liste vide = tout va) : une page par geste, aucune orpheline, contrôle motion_code, fiche
    de style maison, geste nommé, format, instant de l'affiche."""
    registre = VI.REGISTRE if registre is None else registre
    themes = {p.stem for p in STYLES.glob("*.json")}
    out = []
    for gid in registre:
        t = _lire(pages / f"{gid}.html")
        if not t:
            out.append(f"{gid} : aucune page ({gid}.html)")
            continue
        refus = MC.controler(t)
        if refus:
            out.append(f"{gid} : refusée par motion_code ({', '.join(refus)})")
        sk = meta(t, "dz-skill") or ""
        if not (sk.startswith("style-") and sk[6:] in themes):
            out.append(f"{gid} : fiche de style maison absente ou inconnue ({sk!r})")
        if meta(t, "dz-geste") != gid:
            out.append(f"{gid} : dz-geste ne nomme pas le geste")
        if meta(t, "dz-format") != f"{W}x{H}":
            out.append(f"{gid} : format attendu {W}x{H}")
        a = meta(t, "dz-affiche") or ""
        if not (re.fullmatch(r"\d+(\.\d+)?", a) and 0 <= float(a) < DUREE):
            out.append(f"{gid} : instant de l'affiche invalide ({a!r})")
    for p in sorted(pages.glob("*.html")):
        if p.stem not in registre:
            out.append(f"{p.stem} : page orpheline (hors registre)")
    return out


def verifier_rendus(registre=None, pages: Path = PAGES, sortie: Path = SORTIE) -> list:
    """Les écarts des rendus : manifeste, empreinte de la page rendue = page actuelle, fichiers présents et bornés."""
    registre = VI.REGISTRE if registre is None else registre
    man = sortie / "index.json"
    if not man.is_file():
        return ["manifeste absent (index.json)"]
    d = json.loads(_lire(man))
    g = d.get("gestes") or {}
    out = []
    if (d.get("W"), d.get("H"), d.get("fps"), d.get("duree_s")) != (W, H, FPS, DUREE):
        out.append("manifeste : format ou cadence différents")
    for gid in registre:
        e = g.get(gid)
        if not e:
            out.append(f"{gid} : aucun rendu au manifeste")
            continue
        if e.get("source") != empreinte(_lire(pages / f"{gid}.html")):
            out.append(f"{gid} : page modifiée depuis le rendu (relancer sonvfx_illustrations.py {gid})")
        w, a = sortie / f"{gid}.webm", sortie / f"{gid}.webp"
        if not w.is_file():
            out.append(f"{gid} : vidéo absente")
        elif w.stat().st_size > MAX_WEBM or w.stat().st_size != e.get("octets"):
            out.append(f"{gid} : vidéo trop lourde ou différente du manifeste")
        if not a.is_file():
            out.append(f"{gid} : affiche absente")
    for gid in g:
        if gid not in registre:
            out.append(f"{gid} : rendu orphelin (hors registre)")
    return out


def moteur():
    """Le chrome-headless-shell embarqué (jamais Edge : un rendu ne dépend pas du PC)."""
    loc = os.environ.get("LOCALAPPDATA", "")
    install = (Path(loc) / "DeepotusVideoGen" / "vendor" / f"chrome-headless-shell-{MC.NAVIGATEUR_VERSION}"
               / "chrome-headless-shell-win64" / "chrome-headless-shell.exe") if loc else None
    for c in (os.environ.get("DEEPOTUS_NAVIGATEUR", ""), str(MC.moteur_embarque()), str(install or "")):
        if c and os.path.isfile(c):
            return c
    return None


def _ffmpeg(*args) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def rendre(gid: str, navigateur: str, sortie: Path = SORTIE) -> dict:
    html = _lire(PAGES / f"{gid}.html")
    sortie.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dz_illus_") as td:
        mp4 = Path(td) / "r.mp4"
        r = MC.rendre_page(html, mp4, W=W, H=H, fps=FPS, duree_s=DUREE, edge=navigateur)
        if r.get("erreurs_js"):
            raise RuntimeError(f"{gid} : {r['erreurs_js']} erreur(s) JavaScript pendant le rendu")
        webm = sortie / f"{gid}.webm"
        for debit in DEBITS:
            tmp = Path(td) / "v.webm"
            _ffmpeg("-i", str(mp4), "-an", "-c:v", "libvpx-vp9", "-b:v", debit, "-maxrate", debit, "-minrate", "0",
                    "-crf", "36", "-row-mt", "1", "-deadline", "good", "-cpu-used", "1", "-g", str(FPS * DUREE),
                    "-pix_fmt", "yuv420p", "-metadata", "title=", "-fflags", "+bitexact", str(tmp))
            if tmp.stat().st_size <= MAX_WEBM:
                webm.write_bytes(tmp.read_bytes())
                break
        else:
            raise RuntimeError(f"{gid} : la vidéo dépasse {MAX_WEBM} octets même au débit le plus bas")
        img = round(float(meta(html, "dz-affiche")) * FPS)
        _ffmpeg("-i", str(mp4), "-vf", f"select=eq(n\\,{img})", "-frames:v", "1", "-c:v", "libwebp",
                "-quality", "82", "-compression_level", "6", "-fflags", "+bitexact", str(sortie / f"{gid}.webp"))
    return {"source": empreinte(html), "webm": f"{gid}.webm", "affiche": f"{gid}.webp",
            "octets": webm.stat().st_size, "skill": meta(html, "dz-skill")}


def ecrire_manifeste(gestes: dict, sortie: Path = SORTIE) -> None:
    d = {"note": "t275 : illustrations des gestes VFX IA, rendues par scripts/sonvfx_illustrations.py (statiques)",
         "W": W, "H": H, "fps": FPS, "duree_s": DUREE, "navigateur": MC.NAVIGATEUR_VERSION,
         "gestes": {g: gestes[g] for g in VI.REGISTRE if g in gestes}}
    (sortie / "index.json").write_bytes((json.dumps(d, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def main(argv) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--check" in argv:
        e = verifier() + verifier_rendus()
        print("\n".join(e) if e else f"illustrations à jour ({len(VI.REGISTRE)} gestes)")
        return 1 if e else 0
    ids = [a for a in argv if not a.startswith("-")] or list(VI.REGISTRE)
    inconnus = [a for a in ids if a not in VI.REGISTRE]
    if inconnus:
        print("gestes inconnus : " + ", ".join(inconnus))
        return 1
    e = verifier(registre={g: VI.REGISTRE[g] for g in ids})
    if e:
        print("pages refusées :\n  " + "\n  ".join(e))
        return 1
    nav = moteur()
    if not nav:
        print("chrome-headless-shell introuvable (scripts/vendor_chrome_headless_shell.py, ou DEEPOTUS_NAVIGATEUR)")
        return 1
    man = SORTIE / "index.json"
    gestes = (json.loads(_lire(man)).get("gestes") or {}) if man.is_file() else {}
    for gid in ids:
        gestes[gid] = rendre(gid, nav)
        print(f"  {gid:16s} {gestes[gid]['octets']:>7d} o")
        ecrire_manifeste(gestes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
