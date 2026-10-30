# -*- coding: utf-8 -*-
"""t383 (30/10/2026, lot « Réglages : chemins & apparence ») — le THÈME CLAIR complet, et plus largement toute palette
choisie dans Réglages › Apparence (t382) suivie par les écrans qui avaient leurs propres couleurs.
L'audit écran par écran se fait dans la page avec scripts/clair_audit.js (relevé dans la PR) ; ce banc fige ce qui en a
été corrigé :
  1. frontend/shared/dz-palette.css : copie identique, liée par la SPA APRÈS les feuilles du Montage et de Son & VFX ;
     chaque règle commence par :root[data-dz-apparence (Deepotus sombre, où rien n'est écrit, ne change donc pas d'un
     pixel) ; aucun rayon ;
  2. le Montage / Son & VFX (.dzsvm) : CHACUN de ses jetons locaux de surface, d'encre et de signal est rebranché sur un
     alias --pal-* que dz-apparence.js dérive vraiment ;
  3. theme-v2.css redéclare des jetons sur <body> en !important (le bundle les repose en ligne au démarrage) : chacun est
     repris par dz-palette.css sur `:root[data-dz-apparence] body` en !important ;
  4. clair seulement : violet (pastilles « nouveau ») et teintes des nœuds, relevés à l'AA ; le rouge du kit de marque n'est jamais forcé ; le sol du graphe du Studio suit toute palette
     (les maquettes 9:16, l'œuvre, restent sombres) ;
  5. les DAMIERS de transparence des labs passent par var(--damier-a|b, <ancien littéral>) : en sombre rien ne bouge,
     sous une palette le damier suit le panneau ;
  6. l'outil d'audit scripts/clair_audit.js existe ; AGENTS.md nomme la feuille et l'outil ; dz-bords.css à jour.
Run : & $PY tests/test_clair_ecran.py   (depuis backend/)
"""
import json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def lire(rel):
    p = RACINE / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def regles(css):
    """[(sélecteur, corps)] d'une feuille sans commentaires ni @-règles imbriquées."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(s.strip(), c) for s, c in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


SRC = lire("frontend/shared/dz-palette.css")
JS = lire("frontend/shared/dz-apparence.js")
R = regles(SRC)
# les jetons que dz-apparence.js écrit (clés v["--…"] de deriver)
DERIVES = set(re.findall(r'v\["(--[a-z0-9-]+)"\]\s*=', JS))

print("\n[1] la feuille")
COPIE = RACINE / "frontend" / "dist" / "shared" / "dz-palette.css"
check("1.1 copie identique dans frontend/dist/shared", SRC and COPIE.exists()
      and COPIE.read_bytes() == (RACINE / "frontend" / "shared" / "dz-palette.css").read_bytes())
PAGE = lire("frontend/dist/index.html")
lien = '<link rel="stylesheet" href="/shared/dz-palette.css">'
i = PAGE.find(lien)
check("1.2 la SPA la lie une fois, après montage.css, son-vfx-montage.css, sfxstudio.css et theme-v2.css", PAGE.count(lien) == 1
      and all(0 <= PAGE.find(f) < i for f in ("/shared/montage.css", "/shared/son-vfx-montage.css",
                                              "/shared/sfxstudio.css", "/theme-v2.css")), i)
check("1.3 chaque règle ne vaut que sous une palette choisie (:root[data-dz-apparence…])", R and all(
    all(x.strip().startswith(":root[") for x in re.sub(r"\[[^\]]*\]", "[]", s).split(","))
    and s.startswith(":root[data-dz-apparence") for s, _c in R),
    [s for s, _c in R if not s.startswith(":root[data-dz-apparence")][:5])
check("1.4 aucun rayon (angles vifs)", SRC and "radius" not in SRC)
refs = set(re.findall(r"var\((--pal-[a-z0-9-]+|--damier-[ab])", SRC))
check("1.5 chaque alias employé est dérivé par dz-apparence.js", refs and refs <= DERIVES, sorted(refs - DERIVES))

print("\n[2] le Montage et Son & VFX (.dzsvm)")
SVM = lire("frontend/dist/shared/son-vfx-montage.css")
m = re.search(r"\n\.dzsvm\{(.*?)\}", SVM, flags=re.S)
locaux = [k for k in re.findall(r"(--[a-z0-9-]+)\s*:", m.group(1) if m else "")
          if not k.startswith(("--f-", "--ease", "--c-"))]
corps = " ".join(c for s, c in R if s.startswith(":root[data-dz-apparence] .dzsvm") and "select" not in s)
mapes = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*var\((--[a-z0-9-]+)\)", corps))
check("2.1 chaque jeton local de surface, d'encre et de signal est rebranché sur un alias --pal-*", locaux and all(
    mapes.get(k, "").startswith("--pal-") for k in locaux if k != "--amber"), [k for k in locaux if k not in mapes])
check("2.2 --amber du Montage suit son --accent (déjà var(--accent) dans la feuille)", "--amber:var(--accent)" in m.group(1).replace(" ", "")
      if m else False)
check("2.3 les menus déroulants suivent la clarté de la palette", any(
    s == ':root[data-dz-apparence="light"] .dzsvm select' and "color-scheme:light" in c.replace(" ", "") for s, c in R))
check("2.4 en clair, la rampe des médias du Montage prend ses teintes claires", any(
    s == ':root[data-dz-apparence="light"] .dzsvm' and all(x in c for x in ("--c-image", "--c-video", "--c-audio", "--c-av",
                                                                          "--c-3d", "--c-text")) for s, c in R))

print("\n[3] les jetons redéclarés sur <body>")
T2 = lire("frontend/dist/theme-v2.css")
corps_body = " ".join(c for s, c in regles(T2) if s == "body")
forces = re.findall(r"(--[a-z0-9-]+)\s*:[^;]*!important", corps_body)
cb = " ".join(c for s, c in R if s == ":root[data-dz-apparence] body")
check("3.1 theme-v2.css force au moins --cyan sur body (sinon ce banc ne garde plus rien)", "--cyan" in forces, forces)
check("3.2 chacun est repris sous une palette, en !important, depuis un alias", forces and all(
    re.search(re.escape(k) + r"\s*:\s*var\(--pal-[a-z0-9-]+\)\s*!important", cb) for k in forces), cb)

print("\n[4] clair seulement : violet, nœuds, marque")
CL = " ".join(c for s, c in R if s == ':root[data-dz-apparence="light"]')
for k in ("--violet", "--violet-soft", "--node-image", "--node-video", "--node-audio", "--node-av", "--node-text"):
    check(f"4.1 {k} a sa valeur claire", re.search(re.escape(k) + r"\s*:", CL) is not None)


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


check("4.3 le rouge de marque n'est jamais forcé (couleur du kit de marque de l'utilisateur)", "--brand" not in SRC)
etude = [c for s, c in R if "rgb(2, 6, 13)" in s]
check("4.4 le sol du graphe du Studio suit la palette, reconnu à sa grille (les maquettes 9:16 restent sombres)", etude
      and all('[style*="radial-gradient(circle at center"]' in s for s, _c in R if "rgb(2, 6, 13)" in s)
      and all("var(--pal-fond)" in c for c in etude))
for k in ("--violet", "--node-image", "--node-video", "--node-audio", "--node-av", "--node-text"):
    v = re.search(re.escape(k) + r"\s*:\s*(#[0-9a-f]{6})", CL)
    check(f"4.2 {k} lisible sur un panneau clair (AA 4,5:1 sur #ffffff et sur #f2f0ec)", v and ratio(v.group(1), "#ffffff") >= 4.5
          and ratio(v.group(1), "#f2f0ec") >= 4.5, v and round(ratio(v.group(1), "#f2f0ec"), 2))

print("\n[5] les damiers des labs")
DAMIERS = {"frontend/vectorlab/vectorlab.css": ("#2a2a2a", "#1c1c1c"), "frontend/tilelab/tilelab.css": ("#2a2a2a", "#1c1c1c"),
           "frontend/spritelab/spritelab.css": ("#1e293b", "#0f172a"),
           "frontend/materialforge/materialforge.css": ("#1a1a1f", "#131317")}
for rel, (a, b) in DAMIERS.items():
    css = lire(rel)
    gr = re.findall(r"repeating-conic-gradient\(([^)]*\))[^;]*", css)
    check(f"5.1 {rel} : aucun damier en littéral", css and not re.search(r"repeating-conic-gradient\(\s*#", css))
    check(f"5.2 {rel} : damier par var(--damier-a, {a}) / var(--damier-b, {b}) — le sombre ne bouge pas",
          css.count(f"var(--damier-a,{a})") >= 1 and css.count(f"var(--damier-a,{a})") == css.count(f"var(--damier-b,{b})"))
for rel in ("frontend/dist/shared/dz-apparence.js",):
    check("5.3 la copie de dz-apparence.js est identique", (RACINE / rel).read_bytes()
          == (RACINE / "frontend/shared/dz-apparence.js").read_bytes())

print("\n[6] outil, documentation, bords")
AU = lire("scripts/clair_audit.js")
check("6.1 l'outil d'audit existe (texte sous l'AA, îlots sombres, cadres des labs)", all(
    x in AU for x in ("window.__dzClairAudit", "contentDocument", "data-dz-clair", "4.5", "lum(bg) < 0.05")))
AG = lire("AGENTS.md")
check("6.2 AGENTS.md : la ligne de la feuille nomme aussi l'outil d'audit",
      "| `frontend/shared/dz-palette.css` (+ `scripts/clair_audit.js`) |" in AG)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "charte_bords.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
check("6.3 dz-bords.css à jour (charte_bords.py --check)", r.returncode == 0, (r.stdout + r.stderr)[-300:])
r = subprocess.run(["node", str(RACINE / "frontend" / "shared" / "qa" / "apparence.test.mjs")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=120)
check("6.4 apparence.test.mjs vert (alias --pal-*, damier)", r.returncode == 0, (r.stdout + r.stderr)[-800:])

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
