# -*- coding: utf-8 -*-
"""t143 (09/10/2026) — traduction L3 : la couche frontend/patches/montage.js (window.DzTracks : pistes, barre d'outils,
projets, tiroirs Médias et Texte, étalonnage, scopes, voix off, menus, raccourcis, livraison…) passe par dzT(clé), par-
dessus L1 (Bibliothèque, Réglages) et L2 (Studio, Templates).
(consigne docs/superpowers/plans/2026-10-09-traduction-l3-montage.md, skill traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l3_generer.py --check ; i18n_l2_generer et i18n_l1_generer --check
      (la couche du poste = L1 + L2 + L3).
  [2] la réversibilité : la couche d'avant L3 se reconstruit exactement (sans git), la table rejoue la couche, le bloc
      MONTAGE du bundle EST la couche, avant_i18n_l3 rend le bloc d'avant L3, et la chaîne L3 → L2 → L1 se défait.
  [3] le dictionnaire montage.json : chaque dzT("montage.…") de la couche existe, fr et en non vides, mêmes {x},
      chaque variable fournie par son appel ; aucune clé sans usage ; aucune clé partagée avec montage_svm.json (L4).
  [4] le runtime sous node : dzT rend le français et l'anglais des clés du lot.
  [5] plus de texte en dur dans la couche : rien hors dzT sauf les littéraux GARDÉS (L1, L2, L3) et le bruit technique.
  [6] compteurs figés (x.useState( 731, DzTracks 181), CRLF, aucun dzT( collé à un mot, node --check.
Run : & $PY tests/test_i18n_l3.py   (depuis backend/)
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
REL = "frontend/dist/assets/index-BEOJX8L5.js"
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
    import i18n_l3_generer as G
    import _i18n_l1_aide as AIDE

    BUNB = (RACINE / REL).read_bytes()
    BUN = BUNB.decode("utf-8")
    COUCHE = (RACINE / G.CIBLES["montage"]).read_bytes().decode("utf-8")
    TABLE = json.loads((RACINE / "scripts/i18n_l3_paires.json").read_bytes().decode("utf-8"))
    BASE = G.base("montage")
    n = lambda t: t.replace("\r\n", "\n")                                   # noqa: E731

    print("\n[1] la saisie et les générateurs")
    for script in ("i18n_l3_generer.py", "i18n_l2_generer.py", "i18n_l1_generer.py"):
        p = subprocess.run([sys.executable, str(RACINE / "scripts" / script), "--check"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
        check(f"1a {script} --check : à jour", p.returncode == 0, (p.stdout + p.stderr)[-300:])
    nsub = len(TABLE["couches"].get("montage", []))
    check("1b la table porte la base et au moins 600 substitutions", TABLE.get("base") == G.BASE and nsub >= 600, nsub)
    check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))

    print("\n[2] la réversibilité")
    try:
        check("2a la couche d'avant L3 se reconstruit exactement, sans git (icônes G1 défaites ensuite)",
              n(AIDE.couche_avant_dzglyph(AIDE.couche_avant_i18n_l3(COUCHE), "montage")) == n(BASE))
    except ValueError as e:
        check("2a la couche d'avant L3 se reconstruit exactement", False, e)
    check("2b la table consignée rejoue la couche : base + substitutions = couche du poste",
          n(G.appliquer("montage", BASE)) == n(AIDE.couche_avant_dzglyph(COUCHE, "montage")))   # G1 posées après L3
    b, e = "/*__DZ_MONTAGE_BEGIN__*/", "/*__DZ_MONTAGE_END__*/"
    bloc = BUN.split(b, 1)[1].split(e, 1)[0] if BUN.count(b) == 1 else ""
    check("2c le bloc MONTAGE du bundle EST la couche (rafraîchie)", n(bloc).strip("\n") == n(COUCHE).lstrip("﻿").strip("\n"))
    bloc0 = AIDE.couche_avant_dzglyph(AIDE.avant_i18n_l3(BUN).split(b, 1)[1].split(e, 1)[0].strip("\r\n"), "montage")
    check("2d avant_i18n_l3(bundle) rend le bloc d'avant L3", n(bloc0).strip("\n") == n(BASE).strip("\n"))
    import i18n_l1_generer as G1
    try:
        check("2e la chaîne se défait : L3 puis L2 puis L1 → la couche d'avant toute traduction (base de L1)",
              n(AIDE.couche_avant_i18n(COUCHE)) == n(G1.base("couche")))
    except ValueError as x:
        check("2e la chaîne se défait", False, x)

    print("\n[3] le dictionnaire montage.json")
    DICO = {}
    for f in sorted((RACINE / "frontend/shared/i18n").glob("*.json")):
        DICO.update(json.loads(f.read_text("utf-8")))
    lot = json.loads((RACINE / "frontend/shared/i18n/montage.json").read_text("utf-8"))
    svm = json.loads((RACINE / "frontend/shared/i18n/montage_svm.json").read_text("utf-8"))
    # une clé peut être choisie par un ternaire dans l'appel (dzT(n>1?"….plusieurs":"….un")) : tout littéral de clé du lot
    cles = sorted(set(re.findall(r'"(montage\.[a-z0-9_]+\.[a-z0-9_.]+)"', COUCHE)))
    check("3a au moins 700 clés du lot sont utilisées", len(cles) >= 700, len(cles))
    check("3b chaque clé citée par la couche est au dictionnaire du lot", set(cles) <= set(lot), sorted(set(cles) - set(lot))[:10])
    vides = [c for c in cles if c in DICO and not (DICO[c].get("fr") and DICO[c].get("en"))]
    check("3c fr et en non vides", not vides, vides[:10])
    var = lambda t: sorted(set(re.findall(r"\{(\w+)\}", t)))      # noqa: E731
    diff = [c for c in cles if c in DICO and var(DICO[c]["fr"]) != var(DICO[c]["en"])]
    check("3d mêmes variables {x} en fr et en", not diff, [(c, DICO[c]) for c in diff[:5]])
    inutiles = sorted(set(lot) - set(cles))
    check("3e aucune clé du dictionnaire du lot sans usage", not inutiles, inutiles[:10])
    check("3f aucune clé partagée avec montage_svm.json (L4)", not (set(lot) & set(svm)), sorted(set(lot) & set(svm))[:5])
    p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("3g dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])
    manque = []
    for c, corps in re.findall(r'dzT\("(montage\.[a-z0-9_.]+)",\s*\{([^{}]*)\}', COUCHE):
        noms = set(re.findall(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*(?=:|,|$)", corps))
        if c in DICO and set(var(DICO[c]["fr"])) - noms:
            manque.append((c, sorted(set(var(DICO[c]["fr"])) - noms)))
    sans = [c for c in re.findall(r'dzT\("(montage\.[a-z0-9_.]+)"\)', COUCHE) if c in DICO and var(DICO[c]["fr"])]
    check("3h chaque variable {x} d'un texte du lot est fournie par son appel dzT", not manque and not sans,
          (manque[:5], sans[:5]))

    print("\n[4] le runtime sous node")
    if NODE:
        HARNAIS = r"""
const fs = require("fs");
const [runPath, dicoPath, clesJson] = process.argv.slice(1);
const runSrc = fs.readFileSync(runPath, "utf8"), dicoSrc = fs.readFileSync(dicoPath, "utf8");
function monde(lang) {
  const magasin = { dz_lang: lang };
  const window = { location: { reload() {} } };
  window.localStorage = { getItem: k => (k in magasin ? magasin[k] : null), setItem: (k, v) => { magasin[k] = String(v); } };
  window.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({ ui_lang: lang }) });
  const document = { documentElement: { lang: "fr" }, readyState: "loading", addEventListener() {} };
  return new Function("window", "document", "localStorage", "MutationObserver", "Node", dicoSrc + "\n" + runSrc + "\n;return window;")(
    window, document, window.localStorage, undefined, { TEXT_NODE: 3, ELEMENT_NODE: 1 });
}
const fr = monde("fr"), en = monde("en"), R = {};
for (const c of JSON.parse(fs.readFileSync(clesJson, "utf8"))) R[c] = [fr.dzT(c), en.dzT(c)];
process.stdout.write(JSON.stringify(R));
"""
        t = pathlib.Path(tempfile.mkdtemp(prefix="dzl3n_"))
        echantillon = cles[::max(1, len(cles) // 25)]
        (t / "cles.json").write_text(json.dumps(echantillon), encoding="utf-8")
        r = subprocess.run([NODE, "-e", HARNAIS, str(RACINE / "frontend/dist/shared/dz-i18n.js"),
                            str(RACINE / "frontend/dist/shared/dz-i18n-dico.js"), str(t / "cles.json")],
                           capture_output=True, text=True, encoding="utf-8")
        shutil.rmtree(t, ignore_errors=True)
        R = json.loads(r.stdout) if r.returncode == 0 and r.stdout else {}
        check("4a chaque clé échantillonnée rend son fr et son en du dictionnaire (jamais la clé elle-même)",
              len(R) >= 20 and all(v == [DICO[k]["fr"], DICO[k]["en"]] for k, v in R.items()),
              [(k, v) for k, v in R.items() if v != [DICO[k]["fr"], DICO[k]["en"]]][:5] or len(R))
    else:
        check("4- node présent", False, "node absent du PATH")

    print("\n[5] plus de texte en dur dans la couche")
    import i18n_l3_perimetre as PER
    R5 = PER.restes({"montage": BASE}, {"montage": COUCHE}, TABLE["gardes"])
    check("5a aucun texte visible en dur hors dzT dans montage.js", not R5, R5[:15])
    gardes_ok = all((g["pos"] is None) or BASE[g["pos"]:g["pos"] + len(g["texte"])] == g["texte"] for g in TABLE["gardes"])
    check("5b chaque littéral gardé est bien à sa place dans la couche de base", gardes_ok)

    print("\n[6] compteurs figés et syntaxe")
    check("6a x.useState( 731, DzTracks 181 (dzT est une fonction globale, pas un hook)",
          BUN.count("x.useState(") == 731 and BUN.count("DzTracks") == 181, (BUN.count("x.useState("), BUN.count("DzTracks")))
    check("6b fins de ligne intactes (bundle et couche en CRLF)",
          BUNB.count(b"\r\n") == BUNB.count(b"\n") > 15000 and COUCHE.count("\r\n") == COUCHE.count("\n"))
    colles = re.findall(r".{12}[A-Za-z0-9_$]dzT\(", COUCHE)
    check("6c aucun dzT( collé à un mot (returndzT…) dans la couche", not colles, colles[:5])
    if NODE:
        r = subprocess.run([NODE, "--check", str(RACINE / G.CIBLES["montage"])], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        check("6d node --check montage.js", r.returncode == 0, (r.stderr or "")[-300:])
        with (RACINE / REL).open("rb") as fh:
            r = subprocess.run([NODE, "--input-type=module", "--check"], stdin=fh, capture_output=True)
        check("6e node --check du bundle (module)", r.returncode == 0, (r.stderr or b"")[-300:])

    print(f"\n=== {ok} passed, {fail} failed ===")
    return fail


def test_i18n_l3():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
