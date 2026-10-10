# -*- coding: utf-8 -*-
"""t146 (10/10/2026) — traduction L6 : le Vectorlab (lab statique frontend/vectorlab/) passe par T(clé)
(frontend/vectorlab/js/mod-i18n.js : dzT du runtime dans la page, français des dictionnaires sous node) ; les textes
de index.html sont traduits à l'affichage par la surcouche (entrées H) ; les fiches didactiques ont leur version
anglaise (consigne scripts/i18n_l6/CONSIGNE.md, skill traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l6_generer.py --check (modules, table, dictionnaire à jour).
  [2] la réversibilité : chaque module se défait exactement vers la source de la BASE par la table, sans git
      (_i18n_l1_aide.source_avant_i18n_l6), et la table rejoue chaque module.
  [3] le dictionnaire : chaque T("vectorlab.…") / vlT(…) des modules existe, fr et en non vides, mêmes variables {x} ;
      aucune clé du lot sans usage (les clés H : leur français est un texte de index.html) ; dictionnaire assemblé.
  [4] le runtime : sous node, T rend le français (mod-statut.phrase_statut) ; avec un window.dzT anglais, l'anglais.
  [5] plus de texte français en dur : --restes ne trouve rien hors des littéraux GARDÉS (motivés dans la saisie).
  [6] syntaxe : node --check de chaque module touché ; chaque module qui appelle T/vlT importe mod-i18n.js ; aucun
      T("vectorlab. dans un module qui déclare un T à lui (masquage) ; CRLF homogène.
  [7] les fiches didactiques : chaque fiche de aide/index.json a titre_en, phrase_en (≤ 25 mots) et fichier_en
      présent ; mod-didact choisit la version de la langue.
Run : & $PY tests/test_i18n_l6.py   (depuis backend/)
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
LAB = RACINE / "frontend" / "vectorlab"
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
    import i18n_l6_generer as G
    import _i18n_l1_aide as AIDE
    n = lambda t: t.replace("\r\n", "\n")                                   # noqa: E731
    TABLE = json.loads(G.PAIRES.read_bytes().decode("utf-8"))

    print("\n[1] la saisie et le générateur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l6_generer.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1a i18n_l6_generer --check : à jour", p.returncode == 0, (p.stdout + p.stderr)[-400:])
    ned = sum(len([e for e in v if e["groupe"] != "import"]) for v in TABLE["fichiers"].values())
    check("1b la table porte la base et au moins 800 éditions", TABLE.get("base") == G.BASE and ned >= 800, ned)
    check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))

    print("\n[2] la réversibilité")
    mauvais, rejoue = [], []
    for f in TABLE["fichiers"]:
        cur = (LAB / f).read_bytes().decode("utf-8")
        base = G.base(f)
        try:
            if n(AIDE.source_avant_i18n_l6(cur, f)) != n(base):
                mauvais.append(f)
        except ValueError as e:
            mauvais.append(f"{f} ({e})")
        if n(G.appliquer(f, base)) != n(cur):
            rejoue.append(f)
    check(f"2a chaque module ({len(TABLE['fichiers'])}) se défait exactement vers sa source de BASE, sans git",
          not mauvais, mauvais[:5])
    check("2b la table rejoue chaque module : base + éditions = source du poste", not rejoue, rejoue[:5])

    print("\n[3] le dictionnaire")
    DICO = {}
    for fj in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        DICO.update(json.loads(fj.read_text("utf-8")))
    ZON = json.loads((RACINE / "frontend" / "shared" / "i18n" / "vectorlab.json").read_text("utf-8"))
    sources = {f.name: f.read_bytes().decode("utf-8") for f in (LAB / "js").glob("*.js")}
    texte = "".join(sources.values())
    cles = set(re.findall(r'\b(?:vl)?T\("(vectorlab\.[a-z0-9_.]+)"', texte))
    cles |= {c for c in re.findall(r'"(vectorlab\.[a-z0-9_.]+)"', texte) if c in ZON}   # T(cond ? "a" : "b")
    check("3a au moins 700 clés du lot sont utilisées", len(cles) >= 700, len(cles))
    absentes = sorted(c for c in cles if c not in DICO)
    check("3b chaque clé utilisée est au dictionnaire", not absentes, absentes[:8])
    check("3c fr et en non vides", all(v.get("fr") and v.get("en") for v in ZON.values()))
    vars_ko = [k for k, v in ZON.items()
               if set(re.findall(r"\{(\w+)\}", v["fr"])) != set(re.findall(r"\{(\w+)\}", v["en"]))]
    check("3d mêmes variables {x} en fr et en", not vars_ko, vars_ko[:6])
    html = (LAB / "index.html").read_bytes().decode("utf-8")
    import html as _html
    html_n = re.sub(r"\s+", " ", _html.unescape(html))
    sans_usage = [k for k, v in ZON.items() if k not in cles and re.sub(r"\s+", " ", v["fr"]) not in html_n]
    check("3e aucune clé du lot sans usage (module, ou texte de index.html)", not sans_usage, sans_usage[:8])
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("3f dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])

    print("\n[4] le runtime")
    if NODE:
        js = (
            "const m = await import('./js/mod-statut.js');"
            "const fr = m.phrase_statut('select', 0, {});"
            "globalThis.window = { dzT: (k, v) => 'EN:' + k };"
            "const en = m.phrase_statut('select', 0, {});"
            "console.log(JSON.stringify({ fr, en }));"
        )
        r = subprocess.run([NODE, "--input-type=module", "-e", js], cwd=str(LAB), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        try:
            d = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                           # noqa: BLE001
            d = {}
        check("4a sous node, T rend le français du dictionnaire (langue de référence des bancs)",
              d.get("fr", "").startswith("**Glisser** pour utiliser un cadre"), (r.stdout + r.stderr)[-300:])
        check("4b dans la page (window.dzT présent), T passe par le runtime", d.get("en") == "EN:vectorlab.statut.select_vide",
              d)
    else:
        check("4 node introuvable", False)

    print("\n[5] plus de texte français en dur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l6_generer.py"), "--restes"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    m = re.search(r"restes : (\d+)", p.stdout)
    check("5a aucun littéral d'allure française en dur hors des gardés (i18n_l6_generer --restes)",
          m and m.group(1) == "0", p.stdout[-600:])

    print("\n[6] syntaxe et imports")
    sans_import, masques, syntaxe, eol = [], [], [], []
    for nom, s in sources.items():
        if nom == "mod-i18n.js":
            continue
        appelle = re.search(r'\b(?:vl)?T\("vectorlab\.', s)
        if appelle and "./mod-i18n.js" not in s and "__vlFr" not in s:          # import, ou T posé dans une feuille
            sans_import.append(nom)
        sans_shim = "\n".join(ligne for ligne in s.split("\n") if "__vlFr" not in ligne)   # le T propre d'une feuille
        if 'T("vectorlab.' in re.sub(r'vlT\("vectorlab\.', "", s) and re.search(r"(?:const|let|var|function)\s+T\b", sans_shim):
            masques.append(nom)
        if s.count("\r\n") != s.count("\n"):
            eol.append(nom)
        if appelle and NODE:
            r = subprocess.run([NODE, "--check", str(LAB / "js" / nom)], capture_output=True, text=True)
            if r.returncode:
                syntaxe.append(f"{nom}: {r.stderr.strip()[-160:]}")
    check("6a chaque module qui appelle T importe mod-i18n.js (une feuille porte son T)", not sans_import, sans_import)
    feuilles_imp = [m for m in sorted(G.FEUILLES) if "import " in (LAB / m).read_bytes().decode("utf-8")]
    check("6a' les modules feuilles restent sans import (test_geo, test_vector_docs)", not feuilles_imp, feuilles_imp)
    check("6b aucun T(\"vectorlab. dans un module qui déclare un T à lui (vlT y est importé)", not masques, masques)
    check("6c node --check de chaque module touché", not syntaxe, syntaxe[:3])
    check("6d fins de ligne homogènes", not eol, eol)

    print("\n[7] les fiches didactiques")
    idx = json.loads((LAB / "aide" / "index.json").read_text("utf-8"))
    sys.path.insert(0, str(RACINE))
    manque = [f["id"] for f in idx if not (f.get("titre_en") and f.get("phrase_en") and f.get("fichier_en"))]
    check(f"7a chaque fiche ({len(idx)}) a titre_en, phrase_en et fichier_en", not manque, manque)
    absents = [f.get("fichier_en") for f in idx if f.get("fichier_en") and not (LAB / "aide" / f["fichier_en"]).is_file()]
    check("7b chaque fichier_en existe", not absents, absents)
    mots = lambda s: len(re.findall(r"[\w’'-]+", s or ""))                  # noqa: E731
    longues = [f["id"] for f in idx if mots(f.get("phrase_en")) > 25]
    check("7c phrase anglaise de 25 mots au plus", not longues, longues)
    distincts = [f["id"] for f in idx if f.get("fichier_en")
                 and (LAB / "aide" / f["fichier_en"]).is_file()
                 and (LAB / "aide" / f["fichier_en"]).read_bytes() == (LAB / "aide" / f["fichier"]).read_bytes()]
    check("7d l'animation anglaise est une capture à part (pas la française recopiée)", not distincts, distincts)
    did = sources.get("mod-didact.js", "")
    check("7e mod-didact choisit titre/phrase/fichier selon la langue", "fichier_en" in did and "phrase_en" in did)

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
