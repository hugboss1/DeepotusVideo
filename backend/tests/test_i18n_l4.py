# -*- coding: utf-8 -*-
"""t144 (09/10/2026) — traduction L4 : les couches sfxstudio (tiroir Sons, rack SFX, vumètre), vfxrack (rack VFX) et
son-vfx-montage (écran Son & VFX, écran Montage DzMontage) passent par dzT(clé)
(consigne docs/superpowers/plans/2026-10-09-traduction-l4-son-vfx-sfx-rack.md, skill traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l4_generer.py --check (couches, table et dictionnaires à jour).
  [2] la réversibilité : chaque couche se défait exactement vers celle de la BASE (ecf945e4) par la table consignée,
      sans git ; la table rejoue chaque couche ; les blocs du bundle SONT les couches (rafraîchies) ;
      avant_i18n_l4(bundle) rend les blocs d'avant L4.
  [3] le dictionnaire : chaque dzT("son.|sfx.|vfx.|montage.…") des trois couches existe, fr et en non vides, mêmes
      variables {x} ; chaque variable d'un texte est fournie par son appel ; aucune clé du lot sans usage ;
      dictionnaire assemblé à jour.
  [4] le runtime sous node : dzT rend le français et l'anglais des clés du lot.
  [5] plus de texte en dur dans les trois couches : le balayage lexical ne trouve plus de texte visible hors dzT,
      sauf les littéraux GARDÉS (motivés dans la saisie) et le bruit technique.
  [6] compteurs figés (x.useState( 731, DzTracks 181), CRLF, aucun dzT( collé à un mot, node --check.
Run : & $PY tests/test_i18n_l4.py   (depuis backend/)
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
ZONES = ("son", "sfx", "vfx", "montage")
TAGS = {"sfxstudio": "SFXSTUDIO", "vfxrack": "VFXRACK", "sonvfx": "SONVFX"}
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
    import i18n_l4_generer as G
    import _i18n_l1_aide as AIDE

    BUNB = (RACINE / REL).read_bytes()
    BUN = BUNB.decode("utf-8")
    COUCHES = {c: (RACINE / rel).read_bytes().decode("utf-8") for c, rel in G.CIBLES.items()}
    TABLE = json.loads((RACINE / "scripts/i18n_l4_paires.json").read_bytes().decode("utf-8"))
    BASES = {c: G.base(c) for c in G.CIBLES}
    n = lambda t: t.replace("\r\n", "\n")                                   # noqa: E731

    print("\n[1] la saisie et le générateur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_l4_generer.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1a générateur --check : couches, table et dictionnaires à jour", p.returncode == 0,
          (p.stdout + p.stderr)[-400:])
    nsub = {c: len(v) for c, v in TABLE["couches"].items()}
    check("1b la table porte la base et des substitutions dans chacune des trois couches (≥ 1 000 en tout)",
          TABLE.get("base") == G.BASE and all(nsub.get(c, 0) >= 100 for c in G.CIBLES) and sum(nsub.values()) >= 1000,
          nsub)
    check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))

    print("\n[2] la réversibilité")
    for c in G.CIBLES:
        try:
            check(f"2a [{c}] la couche d'avant L4 se reconstruit exactement, sans git",
                  n(AIDE.couche_avant_i18n_l4(COUCHES[c], c)) == n(BASES[c]))
        except ValueError as e:
            check(f"2a [{c}] la couche d'avant L4 se reconstruit exactement", False, e)
        check(f"2b [{c}] la table consignée rejoue la couche : base + substitutions = couche du poste",
              n(G.appliquer(c, BASES[c])) == n(AIDE.couche_avant_dzglyph(COUCHES[c], c)))   # icônes G1 posées après L4
        b, e = f"/*__DZ_{TAGS[c]}_BEGIN__*/", f"/*__DZ_{TAGS[c]}_END__*/"
        bloc = BUN.split(b, 1)[1].split(e, 1)[0] if BUN.count(b) == 1 else ""
        check(f"2c [{c}] le bloc {TAGS[c]} du bundle EST la couche (rafraîchie)",
              n(bloc).strip("\n") == n(COUCHES[c]).lstrip("﻿").strip("\n"))
        bloc0 = AIDE.avant_i18n_l4(BUN).split(b, 1)[1].split(e, 1)[0]
        check(f"2d [{c}] avant_i18n_l4(bundle) rend le bloc d'avant L4", n(bloc0).strip("\n") == n(BASES[c]).strip("\n"))
    print("\n[3] le dictionnaire")
    DICO = {}
    for f in sorted((RACINE / "frontend/shared/i18n").glob("*.json")):
        DICO.update(json.loads(f.read_text("utf-8")))
    tout = "\n".join(COUCHES.values())
    motif = r'dzT\("((?:' + "|".join(ZONES) + r')\.[a-z0-9_.]+)"'
    cles = sorted(set(re.findall(motif, tout)))
    check("3a au moins 800 clés du lot sont utilisées", len(cles) >= 800, len(cles))
    absentes = [c for c in cles if c not in DICO]
    check("3b chaque clé utilisée est au dictionnaire", not absentes, absentes[:10])
    vides = [c for c in cles if c in DICO and not (DICO[c].get("fr") and DICO[c].get("en"))]
    check("3c fr et en non vides", not vides, vides[:10])
    var = lambda t: sorted(set(re.findall(r"\{(\w+)\}", t)))      # noqa: E731
    diff = [c for c in cles if c in DICO and var(DICO[c]["fr"]) != var(DICO[c]["en"])]
    check("3d mêmes variables {x} en fr et en", not diff, [(c, DICO[c]) for c in diff[:5]])
    lot = {k for f in G.ZONES.values() for k in json.loads((RACINE / "frontend/shared/i18n" / f).read_text("utf-8"))}
    inutiles = sorted(lot - set(cles))
    check("3e aucune clé des dictionnaires du lot sans usage", not inutiles, inutiles[:10])
    check("3f les clés du lot sont dans les quatre fichiers du lot", set(cles) <= lot, sorted(set(cles) - lot)[:10])
    p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("3g dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])
    manque = []
    for c, corps in re.findall(r'dzT\("((?:' + "|".join(ZONES) + r')\.[a-z0-9_.]+)",\s*\{([^{}]*)\}', tout):
        noms = set(re.findall(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*(?=:|,|$)", corps))
        if c in DICO and set(var(DICO[c]["fr"])) - noms:
            manque.append((c, sorted(set(var(DICO[c]["fr"])) - noms)))
    sans = [c for c in re.findall(r'dzT\("((?:' + "|".join(ZONES) + r')\.[a-z0-9_.]+)"\)', tout)
            if c in DICO and var(DICO[c]["fr"])]
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
        t = pathlib.Path(tempfile.mkdtemp(prefix="dzl4n_"))
        echantillon = [c for z in ZONES for c in [k for k in cles if k.startswith(z + ".")][:10]]
        (t / "cles.json").write_text(json.dumps(echantillon), encoding="utf-8")
        r = subprocess.run([NODE, "-e", HARNAIS, str(RACINE / "frontend/dist/shared/dz-i18n.js"),
                            str(RACINE / "frontend/dist/shared/dz-i18n-dico.js"), str(t / "cles.json")],
                           capture_output=True, text=True, encoding="utf-8")
        shutil.rmtree(t, ignore_errors=True)
        R = json.loads(r.stdout) if r.returncode == 0 and r.stdout else {}
        check("4a chaque zone du lot est échantillonnée", all(any(k.startswith(z + ".") for k in R) for z in ZONES),
              sorted({k.split(".")[0] for k in R}))
        check("4b chaque clé échantillonnée rend son fr et son en du dictionnaire (jamais la clé elle-même)",
              R and all(v == [DICO[k]["fr"], DICO[k]["en"]] for k, v in R.items()),
              [(k, v) for k, v in R.items() if v != [DICO[k]["fr"], DICO[k]["en"]]][:5])
    else:
        check("4- node présent", False, "node absent du PATH")

    print("\n[5] plus de texte en dur dans les trois couches")
    import i18n_l4_perimetre as PER
    R5 = PER.restes(BASES, COUCHES, TABLE["gardes"])
    check("5a aucun texte visible en dur hors dzT dans les trois couches", not R5, R5[:15])
    gardes_ok = all((g["pos"] is None) or BASES[g["cible"]][g["pos"]:g["pos"] + len(g["texte"])] == g["texte"]
                    for g in TABLE["gardes"])
    check("5b chaque littéral gardé est bien à sa place dans la couche de base", gardes_ok)

    print("\n[6] compteurs figés et syntaxe")
    check("6a x.useState( 731, DzTracks 181 (dzT est une fonction globale, pas un hook)",
          BUN.count("x.useState(") == 731 and BUN.count("DzTracks") == 181, (BUN.count("x.useState("), BUN.count("DzTracks")))
    check("6b fins de ligne intactes (bundle et couches en CRLF)",
          BUNB.count(b"\r\n") == BUNB.count(b"\n") > 15000
          and all(t.count("\r\n") == t.count("\n") for t in COUCHES.values()))
    colles = [m for t in COUCHES.values() for m in re.findall(r".{12}[A-Za-z0-9_$]dzT\(", t)]
    check("6c aucun dzT( collé à un mot (returndzT…) dans les couches", not colles, colles[:5])
    if NODE:
        for c, rel in G.CIBLES.items():
            r = subprocess.run([NODE, "--check", str(RACINE / rel)], capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            check(f"6d node --check {rel}", r.returncode == 0, (r.stderr or "")[-300:])
        with (RACINE / REL).open("rb") as fh:
            r = subprocess.run([NODE, "--input-type=module", "--check"], stdin=fh, capture_output=True)
        check("6e node --check du bundle (module)", r.returncode == 0, (r.stderr or b"")[-300:])

    print(f"\n=== {ok} passed, {fail} failed ===")
    return fail


def test_i18n_l4():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
