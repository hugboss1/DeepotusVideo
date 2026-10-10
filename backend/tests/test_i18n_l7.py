# -*- coding: utf-8 -*-
"""t147 (10/10/2026) — traduction L7 : le Card Forge (frontend/cardforge/, scripts classiques chargés après
/shared/dz-i18n.js) passe par dzT(clé) ; les textes de index.html sont traduits à l'affichage par la surcouche
(entrées H) ; deux textes à double sens (« Édition », « Carte ») sont posés par dzT au démarrage
(consigne scripts/i18n_l7/CONSIGNE.md, skill traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l7_generer.py --check (modules, table, dictionnaire à jour).
  [2] la réversibilité : chaque module se défait exactement vers la source de la BASE par la table, sans git
      (_i18n_l1_aide.source_avant_i18n_l7), et la table rejoue chaque module.
  [3] le dictionnaire : chaque dzT("cartes.…") des modules existe, fr et en non vides, mêmes variables {x} ; aucune clé
      du lot sans usage (les clés H : leur français est un texte de index.html) ; dictionnaire assemblé à jour.
  [4] le runtime : un module traduit, exécuté sous node avec le dzT du banc (PRELUDE_DZT, en français), rend le
      français ; avec un dzT anglais, l'anglais.
  [5] plus de texte français en dur : --restes ne trouve rien hors des littéraux GARDÉS (motivés dans la saisie).
  [6] syntaxe : node --check de chaque module touché ; aucun dzT( collé à un mot ; fins de ligne homogènes ; la page
      charge le dictionnaire et le runtime AVANT les modules.
Run : & $PY tests/test_i18n_l7.py   (depuis backend/)
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
RACINE = HERE.parent.parent
LAB = RACINE / "frontend" / "cardforge"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


def main():
    sys.path.insert(0, str(RACINE / "scripts"))
    sys.path.insert(0, str(HERE))
    import i18n_l7_generer as G
    import _i18n_l1_aide as AIDE
    n = lambda t: t.replace("\r\n", "\n")                                   # noqa: E731
    TABLE = json.loads(G.PAIRES.read_bytes().decode("utf-8"))

    print("\n[1] la saisie et le générateur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l7_generer.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1a i18n_l7_generer --check : à jour", p.returncode == 0, (p.stdout + p.stderr)[-400:])
    ned = sum(len(v) for v in TABLE["fichiers"].values())
    check("1b la table porte la base et au moins 2 500 éditions", TABLE.get("base") == G.BASE and ned >= 2500, ned)
    check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))

    print("\n[2] la réversibilité")
    mauvais, rejoue = [], []
    for f in TABLE["fichiers"]:
        cur = (LAB / f).read_bytes().decode("utf-8")
        base = G.base(f)
        try:
            if n(AIDE.source_avant_i18n_l7(cur, f)) != n(base):
                mauvais.append(f)
        except ValueError as e:
            mauvais.append(f"{f} ({e})")
        try:
            if n(G.appliquer(f, base)) != n(cur):
                rejoue.append(f)
        except ValueError as e:
            rejoue.append(f"{f} ({e})")
    check(f"2a chaque module ({len(TABLE['fichiers'])}) se défait exactement vers sa source de BASE, sans git",
          not mauvais, mauvais[:5])
    check("2b la table rejoue chaque module : base + éditions = source du poste", not rejoue, rejoue[:5])
    try:
        vue = n(AIDE.lire_cartes(LAB / "js" / "mod-print.js"))
    except ValueError as e:
        vue = f"ERREUR {e}"
    check("2c lire_cartes rend la source d'avant L7 d'un module", vue == n(G.base("js/mod-print.js")), vue[:120])

    print("\n[3] le dictionnaire")
    DICO = {}
    for fj in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        DICO.update(json.loads(fj.read_text("utf-8")))
    ZON = json.loads((RACINE / "frontend" / "shared" / "i18n" / "cartes.json").read_text("utf-8"))
    sources = {f.name: f.read_bytes().decode("utf-8") for f in (LAB / "js").glob("*.js")}
    texte = "".join(sources.values())
    cles = set(re.findall(r'\bdzT\("(cartes\.[a-z0-9_.]+)"', texte))
    cles |= {c for c in re.findall(r'"(cartes\.[a-z0-9_.]+)"', texte) if c in ZON}     # dzT(cond ? "a" : "b")
    check("3a au moins 2 500 clés du lot sont utilisées", len(cles) >= 2500, len(cles))
    absentes = sorted(c for c in cles if c not in DICO)
    check("3b chaque clé utilisée est au dictionnaire", not absentes, absentes[:8])
    check("3c fr et en non vides", all(v.get("fr") and v.get("en") for v in ZON.values()))
    vars_ko = [k for k, v in ZON.items()
               if set(re.findall(r"\{(\w+)\}", v["fr"])) != set(re.findall(r"\{(\w+)\}", v["en"]))]
    check("3d mêmes variables {x} en fr et en", not vars_ko, vars_ko[:6])
    import html as _html
    html = re.sub(r"\s+", " ", _html.unescape((LAB / "index.html").read_bytes().decode("utf-8")))
    # une clé H sert à la surcouche : son français est un texte de index.html, ou un libellé d'une table des modules
    # (catalogues figés par les bancs miroir, traduits à l'affichage)
    def cite(fr):
        return (re.sub(r"\s+", " ", _html.unescape(fr)) in html
                or any(q + fr + q in texte for q in "\"'`"))
    sans_usage = [k for k, v in ZON.items() if k not in cles and not cite(v["fr"])]
    check("3e aucune clé du lot sans usage (module, texte de index.html ou libellé d'une table)", not sans_usage, sans_usage[:8])
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("3f dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])

    print("\n[4] le runtime")
    if NODE:
        cle = "cartes.edition.titre"
        js = AIDE.PRELUDE_DZT + "\n" + (
            f"const fr = dzT({json.dumps(cle)});\n"
            "globalThis.dzT = (k) => 'EN:' + k;\n"
            f"const en = globalThis.dzT({json.dumps(cle)});\n"
            "console.log(JSON.stringify({ fr, en }));\n")
        import tempfile
        with tempfile.TemporaryDirectory(prefix="dzl7_") as tmp:          # le prélude (dictionnaire) dépasse la ligne de commande
            f = pathlib.Path(tmp) / "runtime.js"
            f.write_text(js, "utf-8")
            r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            d = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                           # noqa: BLE001
            d = {}
        check("4a sous node, le dzT des bancs (PRELUDE_DZT) rend le français d'une clé du lot",
              d.get("fr") == "Édition", (r.stdout + r.stderr)[-300:])
        check("4b dzT rend la langue du runtime (anglais simulé)", d.get("en") == "EN:" + cle, d)
    else:
        check("4 node introuvable", False)

    print("\n[5] plus de texte français en dur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l7_generer.py"), "--restes"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    m = re.search(r"restes : (\d+)", p.stdout)
    check("5a aucun littéral d'allure française en dur hors des gardés (i18n_l7_generer --restes)",
          m and m.group(1) == "0", p.stdout[-600:])

    print("\n[6] syntaxe et chargement")
    syntaxe, colles, eol = [], [], []
    for nom, s in sources.items():
        if re.search(r"[\w$]dzT\(", s):
            colles.append(nom)
        if s.count("\r\n") != s.count("\n"):
            eol.append(nom)
        if NODE and 'dzT("cartes.' in s:
            r = subprocess.run([NODE, "--check", str(LAB / "js" / nom)], capture_output=True, text=True)
            if r.returncode:
                syntaxe.append(f"{nom}: {r.stderr.strip()[-160:]}")
    check("6a node --check de chaque module touché", not syntaxe, syntaxe[:3])
    check("6b aucun dzT( collé à un identifiant (returndzT…)", not colles, colles)
    check("6c fins de ligne homogènes", not eol, eol)
    page = (LAB / "index.html").read_bytes().decode("utf-8")
    i_dico, i_run, i_core = page.find("/shared/dz-i18n-dico.js"), page.find("/shared/dz-i18n.js"), page.find("js/core.js")
    check("6d la page charge le dictionnaire puis le runtime AVANT les modules", 0 <= i_dico < i_run < i_core, (i_dico, i_run, i_core))

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
