# -*- coding: utf-8 -*-
"""t148 (10/10/2026) — traduction L8 : l'Atelier, le Material Forge et l'Établi (frontend/atelier, frontend/materialforge,
frontend/etabli ; scripts chargés après /shared/dz-i18n.js) passent par dzT(clé) ; les textes des pages HTML sont
traduits à l'affichage par la surcouche (entrées H), les <option> par une passe au démarrage de chaque lab
(consigne scripts/i18n_l8/CONSIGNE.md, skill traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l8_generer.py --check (scripts, table, dictionnaires à jour).
  [2] la réversibilité : chaque script se défait exactement vers la source de la BASE par la table, sans git
      (_i18n_l1_aide.source_avant_i18n_l8, _labs_avant_l8), et la table rejoue chaque script.
  [3] les dictionnaires atelier/matiere/etabli : chaque dzT("…") des scripts existe, fr et en non vides, mêmes
      variables {x} ; aucune clé sans usage (les clés H : leur français est un texte d'une page) ; assemblage à jour.
  [4] le runtime : une clé de chaque lab rend son français sous le dzT des bancs (PRELUDE_DZT).
  [5] plus de texte français en dur : --restes ne trouve rien hors des littéraux GARDÉS (motivés dans la saisie).
  [6] syntaxe : node --check (scripts classiques ; modules copiés en .mjs) ; aucun dzT( collé à un mot ; fins de ligne
      homogènes ; chaque page charge le dictionnaire puis le runtime AVANT son script ; passe des <option>.
Run : & $PY tests/test_i18n_l8.py   (depuis backend/)
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
RACINE = HERE.parent.parent
FRONT = RACINE / "frontend"
NODE = shutil.which("node")
ZONES = {"atelier": "atelier", "matiere": "materialforge", "etabli": "etabli"}
SCRIPTS = {"atelier/atelier.js": False, "materialforge/materialforge.js": False,
           "etabli/etabli.js": True, "etabli/aide.js": True}                 # True : module ES
PAGES = {"atelier/index.html": "atelier.js", "materialforge/index.html": "materialforge.js",
         "etabli/index.html": "etabli.js"}
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
    import i18n_l8_generer as G
    import _i18n_l1_aide as AIDE
    n = lambda t: t.replace("\r\n", "\n")                                   # noqa: E731
    TABLE = json.loads(G.PAIRES.read_bytes().decode("utf-8"))

    print("\n[1] la saisie et le générateur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l8_generer.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1a i18n_l8_generer --check : à jour", p.returncode == 0, (p.stdout + p.stderr)[-400:])
    ned = sum(len(v) for v in TABLE["fichiers"].values())
    check("1b la table porte la base et au moins 1 000 éditions", TABLE.get("base") == G.BASE and ned >= 1000, ned)
    check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))
    check("1d les quatre scripts sont traduits", sorted(TABLE["fichiers"]) == sorted(SCRIPTS), sorted(TABLE["fichiers"]))

    print("\n[2] la réversibilité")
    mauvais, rejoue = [], []
    for f in TABLE["fichiers"]:
        cur = (FRONT / f).read_bytes().decode("utf-8")
        base = G.base(f)
        try:
            if n(AIDE.source_avant_i18n_l8(cur, f)) != n(base):
                mauvais.append(f)
        except ValueError as e:
            mauvais.append(f"{f} ({e})")
        try:
            if n(G.appliquer(f, base)) != n(cur):
                rejoue.append(f)
        except ValueError as e:
            rejoue.append(f"{f} ({e})")
    check(f"2a chaque script ({len(TABLE['fichiers'])}) se défait exactement vers sa source de BASE, sans git",
          not mauvais, mauvais[:5])
    check("2b la table rejoue chaque script : base + éditions = source du poste", not rejoue, rejoue[:5])
    code = ("import sys, pathlib; sys.path.insert(0, sys.argv[1]); import _labs_avant_l8; "
            "print(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8').count('dzT(\"etabli.'))")
    r = subprocess.run([sys.executable, "-c", code, str(HERE), str(FRONT / "etabli" / "etabli.js")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("2c _labs_avant_l8 : un banc qui l'importe lit l'Établi d'avant L8 (aucun dzT)", r.stdout.strip() == "0",
          (r.stdout + r.stderr)[-300:])

    print("\n[3] les dictionnaires")
    DICO = {}
    for fj in sorted((FRONT / "shared" / "i18n").glob("*.json")):
        DICO.update(json.loads(fj.read_text("utf-8")))
    import html as _html
    for z, lab in ZONES.items():
        ZON = json.loads((FRONT / "shared" / "i18n" / f"{z}.json").read_text("utf-8"))
        texte = "".join((FRONT / f).read_bytes().decode("utf-8") for f in SCRIPTS if f.startswith(lab + "/"))
        cles = set(re.findall(r'\bdzT\("(' + z + r'\.[a-z0-9_.]+)"', texte))
        cles |= {c for c in re.findall(r'"(' + z + r'\.[a-z0-9_.]+)"', texte) if c in ZON}   # dzT(cond ? "a" : "b")
        check(f"3a [{z}] au moins 100 clés utilisées", len(cles) >= 100, len(cles))
        absentes = sorted(c for c in cles if c not in DICO)
        check(f"3b [{z}] chaque clé utilisée est au dictionnaire", not absentes, absentes[:8])
        check(f"3c [{z}] fr et en non vides", all(v.get("fr") and v.get("en") for v in ZON.values()))
        vars_ko = [k for k, v in ZON.items()
                   if set(re.findall(r"\{(\w+)\}", v["fr"])) != set(re.findall(r"\{(\w+)\}", v["en"]))]
        check(f"3d [{z}] mêmes variables {{x}} en fr et en", not vars_ko, vars_ko[:6])
        pages = " ".join(re.sub(r"\s+", " ", _html.unescape(p.read_bytes().decode("utf-8")))
                         for p in (FRONT / lab).glob("*.html"))

        def cite(fr):
            return (re.sub(r"\s+", " ", _html.unescape(fr)) in pages or any(q + fr + q in texte for q in "\"'`"))
        sans_usage = [k for k, v in ZON.items() if k not in cles and not cite(v["fr"])]
        check(f"3e [{z}] aucune clé sans usage (script, texte d'une page ou libellé d'une table)", not sans_usage,
              sans_usage[:8])
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("3f dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])

    print("\n[4] le runtime")
    if NODE:
        echant = {}
        for z in ZONES:
            ZON = json.loads((FRONT / "shared" / "i18n" / f"{z}.json").read_text("utf-8"))
            k = sorted(k for k, v in ZON.items() if not v.get("contexte") and "{" not in v["fr"])[0]
            echant[k] = ZON[k]["fr"]
        js = AIDE.PRELUDE_DZT + "\n" + (
            f"const cles = {json.dumps(sorted(echant))};\n"
            "const fr = Object.fromEntries(cles.map((k) => [k, dzT(k)]));\n"
            "console.log(JSON.stringify(fr));\n")
        with tempfile.TemporaryDirectory(prefix="dzl8_") as tmp:
            f = pathlib.Path(tmp) / "runtime.js"
            f.write_text(js, "utf-8")
            r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            d = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                           # noqa: BLE001
            d = {}
        check("4a sous node, le dzT des bancs rend le français d'une clé de chaque lab", d == echant,
              (r.stdout + r.stderr)[-300:])
    else:
        check("4 node introuvable", False)

    print("\n[5] plus de texte français en dur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l8_generer.py"), "--restes"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    m = re.search(r"restes : (\d+)", p.stdout)
    check("5a aucun littéral d'allure française en dur hors des gardés (i18n_l8_generer --restes)",
          m and m.group(1) == "0", p.stdout[-600:])

    print("\n[6] syntaxe et chargement")
    syntaxe, colles, eol = [], [], []
    with tempfile.TemporaryDirectory(prefix="dzl8s_") as tmp:
        for f, module in SCRIPTS.items():
            s = (FRONT / f).read_bytes().decode("utf-8")
            if re.search(r"[\w$]dzT\(", s):
                colles.append(f)
            if s.count("\r\n") != s.count("\n"):
                eol.append(f)
            if NODE:
                cible = FRONT / f
                if module:
                    cible = pathlib.Path(tmp) / (pathlib.Path(f).stem + ".mjs")
                    cible.write_bytes(s.encode("utf-8"))
                r = subprocess.run([NODE, "--check", str(cible)], capture_output=True, text=True)
                if r.returncode:
                    syntaxe.append(f"{f}: {r.stderr.strip()[-160:]}")
    check("6a node --check de chaque script touché", not syntaxe, syntaxe[:3])
    check("6b aucun dzT( collé à un identifiant (returndzT…)", not colles, colles)
    check("6c fins de ligne homogènes", not eol, eol)
    for page, script in PAGES.items():
        s = (FRONT / page).read_bytes().decode("utf-8")
        i_dico, i_run = s.find('src="/shared/dz-i18n-dico.js"'), s.find('src="/shared/dz-i18n.js"')
        i_lab = s.find(f'src="{script}"')
        check(f"6d {page} charge le dictionnaire puis le runtime AVANT {script}", 0 <= i_dico < i_run < i_lab,
              (i_dico, i_run, i_lab))
    for f in ("atelier/atelier.js", "materialforge/materialforge.js", "etabli/etabli.js"):
        s = (FRONT / f).read_bytes().decode("utf-8")
        check(f"6e {f} traduit les <option> de sa page au démarrage (la surcouche n'y entre pas)",
              "__dzI18n" in s and "option" in s and "t148" in s)

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
