# -*- coding: utf-8 -*-
"""t339 (lot Scenario, B3) — l'écran des 8 directions du Spritelab (onglet Bible). Le module PUR (directions.js) est
jugé par qa/directions.test.mjs, lancé ICI ; ce fichier vérifie le câblage : le sélecteur 4 / 8, les 3 miroirs COCHÉS
par défaut et nommés comme le backend, la case « objet tenu asymétrique » décochée par défaut qui vide et grise les
miroirs et montre le rappel « ne pas miroiter », le coût lu dans le devis du serveur AVANT le clic, et le tir payant
qui passe par le devis à jour PUIS le dialogue maison PUIS `confirme_cout` — jamais de confirmation sans dialogue.
Témoin : la base (origin/main 6eb7f42d) n'a ni sélecteur, ni route /devis.
Run (depuis backend/) : & $PY tests/test_spritelab_huit_directions.py"""
import pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
SL = RACINE / "frontend" / "spritelab"
BASE = "6eb7f42d"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def main():
    h0 = subprocess.run(["git", "show", f"{BASE}:frontend/spritelab/index.html"], capture_output=True,
                        cwd=str(RACINE)).stdout
    r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
    check("T0 témoin : la base n'a ni sélecteur de directions ni route de devis",
          h0 and b'id="dirN"' not in h0 and r0 and b"/assets/sprite/from-board/devis" not in r0)

    r = subprocess.run(["node", str(SL / "qa" / "directions.test.mjs")], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    check("Q1 le banc node du module pur passe", r.returncode == 0 and "PASS" in r.stdout, (r.stdout + r.stderr)[-600:])

    HTML = (SL / "index.html").read_text(encoding="utf-8")
    JS = (SL / "spritelab.js").read_text(encoding="utf-8")
    PY = (RACINE / "backend" / "app" / "services" / "sprite_directions.py").read_text(encoding="utf-8")
    DEB, FIN = "t339 (lot Scenario, B3) : 4 ou 8 directions depuis la planche", "function bibleWire() {"
    check("B0 le bloc t339 est délimité", DEB in JS and FIN in JS and JS.index(DEB) < JS.index(FIN))
    bloc = JS[JS.index(DEB):JS.index(FIN)] if DEB in JS and FIN in JS else ""
    ids = sorted(set(re.findall(r'\$\$?\("#([A-Za-z0-9]+)', bloc)))
    check(f"H1 les {len(ids)} éléments lus par le bloc existent dans index.html",
          ids and all(f'id="{i}"' in HTML for i in ids), str([i for i in ids if f'id="{i}"' not in HTML]))

    m = re.search(r'<div id="dirN"[^>]*>(.*?)</div>', HTML, re.S)
    segs = re.findall(r'<button type="button" class="seg( on)?" data-n="(\d)" aria-pressed="(\w+)"', m.group(1) if m else "")
    check("H2 sélecteur 4 / 8, « 4 » enfoncé au départ (le gratuit d'avant reste le défaut)",
          segs == [(" on", "4", "true"), ("", "8", "false")], segs)
    huit = re.search(r'<div id="dirHuit" class="([^"]*)"', HTML)
    check("H3 les options des 8 directions sont cachées tant que « 4 » est choisi", huit and "hidden" in huit.group(1))
    mir_py = re.findall(r'"(\w+)": "\w+"', re.search(r"MIROIRS = \{([^}]*)\}", PY).group(1))
    boites = re.findall(r'<input type="checkbox" value="(\w+)"( checked)?>', HTML)
    check("H4 trois miroirs, les noms du backend, COCHÉS par défaut",
          [v for v, _ in boites] == mir_py and all(c for _, c in boites), boites)
    asym = re.search(r'<input type="checkbox" id="dirAsym"( checked)?>', HTML)
    check("H5 la case « objet tenu asymétrique » existe, décochée par défaut", asym and not asym.group(1))
    rap = re.search(r'<div id="dirAsymRappel" class="([^"]*)"[^>]*>(.*?)</div>', HTML, re.S)
    check("H6 le rappel « ne pas miroiter » est écrit, caché au départ",
          rap and "hidden" in rap.group(1) and "ne pas miroiter" in rap.group(2), rap and rap.group(0)[:200])
    check("H7 le coût a sa place à côté du bouton (aria-live)", '<span id="dirCout" class="cost" aria-live="polite">' in HTML)

    md = bloc[bloc.find("function majDir()"):bloc.find("async function devisDir()")]
    check("J1 majDir : asymétrique → miroirs décochés ET grisés, rappel montré en mode 8",
          "if (asym) c.checked = false; c.disabled = asym;" in md
          and '$("#dirAsymRappel").classList.toggle("hidden", !(huit && asym));' in md)
    check("J2 majBible appelle majDir (libellé 4 / 8 du bouton à chaque mise à jour)",
          '$("#bibleCut").disabled = !e || busyBible;\r\n  majDir();' in JS
          or '$("#bibleCut").disabled = !e || busyBible;\n  majDir();' in JS)
    dv = bloc[bloc.find("async function devisDir()"):bloc.find("async function lancerDirections()")]
    check("J3 le coût vient du DEVIS du serveur (aucune dépense), dernier appel gagnant",
          '"/assets/sprite/from-board/devis"' in dv and "seq !== dirSeq" in dv and "d.generations" in dv)
    ld = bloc[bloc.find("async function lancerDirections()"):bloc.find("function dirWire()")]
    i_dev, i_dlg = ld.find("await devisDir();"), ld.find("window.__dzDialogue.confirmer(")
    i_tir = ld.find('api.send("POST", "/assets/sprite/from-board", body)')
    check("J4 tir payant : devis À JOUR, puis dialogue maison, puis l'envoi — dans cet ordre",
          0 < i_dev < i_dlg < i_tir, (i_dev, i_dlg, i_tir))
    check("J5 refus du dialogue (ou dialogue absent) : rien ne part",
          "const ok = window.__dzDialogue && await window.__dzDialogue.confirmer(" in ld and "if (!ok) return;" in ld)
    check("J6 `confirme_cout` seulement quand il y a des vues à générer", "confirme: d.generations > 0" in ld)
    check("J7 « 4 » garde le chemin d'avant (cutFromBible, gratuit)", "if (dirN !== 8) return cutFromBible();" in ld)
    bw = JS[JS.index("function bibleWire() {"):]
    bw = bw[:bw.index("}") + 1]
    check("J8 le bouton lance lancerDirections, et dirWire est câblé",
          '$("#bibleCut").onclick = lancerDirections;' in bw and "dirWire();" in bw, bw)
    check("J9 aucun dialogue natif dans le bloc", not re.search(r"(?<![.\w])(confirm|alert|prompt)\(", bloc))
    CSS = (SL / "spritelab.css").read_text(encoding="utf-8")
    check("C1 la rose a ses trois états (générée = ambre, miroir = vert pointillé)",
          ".dir-case.generee{" in CSS and ".dir-case.miroir{" in CSS and ".dir-rose{" in CSS)

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
