"""Les dialogues maison PARTOUT (20/09/2026) : plus aucun confirm / alert /
prompt natif dans le code de l'application, hors commentaires.

Périmètre : tout `frontend/**/*.js` et `*.html` sauf `node_modules`, `vendor`,
`frontend/src` (les sources React ne sont pas servies : le bundle patché
l'est, et `test_dialogue_bundle.py` le juge) et `frontend/dist/assets`
(le bundle lui-même). Les commentaires `/* … */` et `// …` sont retirés avant
la recherche — c'est là que vivent les mentions historiques légitimes.

Et chaque page standalone charge `/shared/dialogue.js` AVANT son script, et
la copie servie `frontend/dist/shared/dialogue.js` est la source
`frontend/shared/dialogue.js` octet pour octet.

Run: python tests/test_dialogues_partout.py
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend"
NATIF = re.compile(r"(?<![\w.$])(?:window\.)?(?:confirm|alert|prompt)\(")
EXCLUS = ("node_modules", "vendor", "frontend/src/", "frontend/dist/assets/", "/qa/")   # les bancs stubent les natifs : ce sont des harnais, pas l'application
STANDALONE = ("atelier", "cardforge", "studio3d", "etabli", "spritelab", "tilelab", "materialforge")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def sans_commentaires(s):
    s = re.sub(r"/\*[\s\S]*?\*/", "", s)
    s = re.sub(r"(?m)^\s*//.*$", "", s)
    s = re.sub(r"(?m)(?<=[;{}\s])//(?![^\n]*[\"'`]).*$", "", s)
    return s


def fichiers():
    for p in FRONT.rglob("*"):
        if p.suffix not in (".js", ".html", ".mjs"):
            continue
        rel = p.relative_to(RACINE).as_posix()
        if any(x in rel for x in EXCLUS):
            continue
        if p.name == "dialogue.js":
            continue
        yield p, rel


def main():
    restes = []
    n = 0
    for p, rel in fichiers():
        n += 1
        txt = sans_commentaires(p.read_text(encoding="utf-8", errors="replace"))
        for m in NATIF.finditer(txt):
            ligne = txt[:m.start()].count("\n") + 1
            restes.append(f"{rel}:{ligne}")
    check(f"aucun confirm/alert/prompt natif hors commentaires ({n} fichiers parcourus)",
          not restes, "\n        " + "\n        ".join(restes[:20]))
    src = FRONT / "shared" / "dialogue.js"
    check("la source frontend/shared/dialogue.js existe et pose saisir/confirmer/informer + window.alert",
          src.exists() and all(k in src.read_text(encoding="utf-8") for k in ("saisir:", "confirmer:", "informer:", "window.alert = function")))
    for copie in (FRONT / "dist" / "shared" / "dialogue.js", FRONT / "patches" / "dialogue.js"):
        check(f"{copie.relative_to(RACINE).as_posix()} = la source octet pour octet",
              copie.exists() and copie.read_bytes() == src.read_bytes())
    for outil in STANDALONE:
        html = re.sub(r"<!--[\s\S]*?-->", "", (FRONT / outil / "index.html").read_text(encoding="utf-8"))
        i = html.find('<script src="/shared/dialogue.js"></script>')
        j = re.search(r'<script[^>]*src="(?!/shared/|/assets/)[^"]+"', html)
        check(f"{outil}/index.html charge /shared/dialogue.js avant son script",
              i >= 0 and j is not None and i < j.start(), f"i={i} j={j.start() if j else None}")
    print(f"\n{ok} PASS, {fail} FAIL")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())


def test_dialogues_partout():
    assert main() == 0
