# -*- coding: utf-8 -*-
"""t142 (08/10/2026) — traduction L2 : Quick, Studio, Templates, News, Scheduler et Épisodes passent par dzT(clé)
(plan docs/superpowers/plans/2026-10-08-traduction-l2-quick-studio-templates-news-scheduler-episodes.md, skill
traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l2_generer.py --check (table et dictionnaires à jour).
  [2] le maillon patch_bundle_i18n_l2.py : octets ; REJEU — le bundle de BASE (419caf63, L1 posée) puis le maillon
      rend EXACTEMENT le bundle de référence ; double application refusée ; aucun .bak ; la traduction se défait
      exactement (avant_i18n_l2) ; la couche montage.js est celle du générateur, et la couche de L1 s'en reconstruit.
  [3] le dictionnaire : chaque dzT("quick.|studio.|templates.|news.|scheduler.|episodes.…") du bundle existe, fr et
      en non vides, mêmes variables {x} des deux côtés ; aucune clé du lot sans usage ; dictionnaire assemblé à jour.
  [4] le runtime sous node : dzT rend le français et l'anglais des clés du lot, variables comprises.
  [5] plus de texte en dur dans le périmètre : le balayage lexical des composants du lot ne trouve plus de texte
      visible hors dzT, sauf les littéraux GARDÉS (motivés dans la saisie) et le bruit technique.
  [6] compteurs figés (x.useState( 731, DzTracks 181), CRLF, node --check (script et module).
Run : & $PY tests/test_i18n_l2.py   (depuis backend/)
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
# le bundle de référence : tant que t142 n'est pas commis, le bundle du poste ; une fois commis, épingler ici le commit
T142 = "f395cfdf"
NODE = shutil.which("node")
ZONES = ("quick", "studio", "templates", "news", "scheduler", "episodes")
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
    import i18n_l2_generer as G
    import _i18n_l1_aide as AIDE

    BUNB = (RACINE / REL).read_bytes()
    BUN = BUNB.decode("utf-8")
    # icônes G1 (10/10) : la couche du poste porte aussi G1, posé APRÈS L2 ; L2 se mesure sur la couche d'avant G1
    COUCHE = AIDE.couche_avant_dzglyph((RACINE / "frontend/patches/montage.js").read_bytes().decode("utf-8"), "montage")
    TABLE = json.loads((RACINE / "scripts/i18n_l2_paires.json").read_bytes().decode("utf-8"))

    print("\n[1] la saisie et le générateur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_l2_generer.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1a générateur --check : table et dictionnaires à jour", p.returncode == 0, (p.stdout + p.stderr)[-400:])
    check("1b la table porte la base et au moins 500 substitutions",
          TABLE.get("base") == G.BASE and len(TABLE["paires"]) >= 500, len(TABLE["paires"]))
    check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))

    print("\n[2] le maillon")
    SCRIPT = RACINE / "scripts/patch_bundle_i18n_l2.py"
    SRC = SCRIPT.read_bytes().decode("utf-8")
    check("2a lecture et écriture en octets", "read_text(" not in SRC and "write_text(" not in SRC and "read_bytes()" in SRC)
    eol = b"\r\n" if BUNB.count(b"\r\n") == BUNB.count(b"\n") else b"\n"
    base = G.bundle_base()
    if T142:
        reference = subprocess.run(["git", "show", f"{T142}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
    else:
        reference = BUNB
    reference = reference.replace(b"\r\n", b"\n").replace(b"\n", eol)
    TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzl2_"))
    try:
        (TMP / "frontend/dist/assets").mkdir(parents=True)
        (TMP / "scripts").mkdir()
        shutil.copy(RACINE / "scripts/i18n_l2_paires.json", TMP / "scripts/i18n_l2_paires.json")
        # le maillon reçoit le bundle de base dont la couche MONTAGE est déjà rafraîchie depuis la source actuelle
        (TMP / REL).write_bytes(G.avec_couche(base, AIDE.couche_avant_i18n_l3(COUCHE)).encode("utf-8"))
        r1 =subprocess.run([sys.executable, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        rejoue = (TMP / REL).read_bytes()
        check("2b rejeu : base + maillon = bundle de référence, octet pour octet",
              r1.returncode == 0 and rejoue == reference,
              (r1.returncode, (r1.stdout + r1.stderr)[-300:], len(rejoue), len(reference)))
        check("2c aucun .bak laissé", not list((TMP / "frontend/dist/assets").glob("*.bak_*")))
        r2 = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        check("2d second passage refusé (double application)",
              r2.returncode != 0 and "double application" in r2.stdout + r2.stderr and (TMP / REL).read_bytes() == rejoue,
              (r2.stdout + r2.stderr)[-200:])
        # sans L1 posée, le maillon refuse (il vient APRÈS i18n_l1)
        (TMP / REL).write_bytes(base.replace('dzT("reglages.cadre.titre")', '"Réglages"').encode("utf-8"))
        r3 = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        check("2e sans le maillon L1 en amont, refus (sonde)", r3.returncode != 0 and "i18nl1" in r3.stdout + r3.stderr,
              (r3.stdout + r3.stderr)[-200:])
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    check("2f aucun .bak_i18nl2 dans le dépôt", not (RACINE / (REL + ".bak_i18nl2")).exists())
    try:
        check("2g la traduction L2 se défait exactement : avant_i18n_l2(bundle) == base, octet pour octet",
              AIDE.avant_i18n_l2(BUN) == base, "écart")
    except ValueError as e:
        check("2g la traduction L2 se défait exactement", False, e)
    try:
        import i18n_l1_generer as G1
        check("2h avant_i18n défait L2 puis L1 : le bundle d'avant toute traduction (base de L1), octet pour octet",
              AIDE.avant_i18n(BUN) == G1.base("bundle"), "écart")
    except ValueError as e:
        check("2h avant_i18n défait L2 puis L1", False, e)
    n = lambda t: t.replace("\r\n", "\n")                                   # noqa: E731
    check("2i la couche du poste est celle que le générateur produit (rien d'édité à la main)",
          n(AIDE.couche_avant_i18n_l3(COUCHE)) == n(G.construire({c: G.base(c) for c in G.CIBLES})[1]))
    try:
        check("2j la couche d'avant L2 (celle de L1) se reconstruit exactement, sans git",
              n(AIDE.couche_avant_i18n_l2(COUCHE)) == n(G.base("couche")))
    except ValueError as e:
        check("2j la couche d'avant L2 se reconstruit exactement", False, e)
    check("2k la table consignée rejoue la couche : couche L1 + substitutions L2 = couche du poste",
          n(G.appliquer_couche(G.base("couche"))) == n(AIDE.couche_avant_dzglyph(COUCHE, "montage")))   # icônes G1 posées après

    print("\n[3] le dictionnaire")
    DICO = {}
    for f in sorted((RACINE / "frontend/shared/i18n").glob("*.json")):
        DICO.update(json.loads(f.read_text("utf-8")))
    motif = r'dzT\("((?:' + "|".join(ZONES) + r')\.[a-z0-9_.]+)"'
    cles = sorted(set(re.findall(motif, BUN)))
    check("3a au moins 500 clés du lot sont utilisées", len(cles) >= 500, len(cles))
    absentes = [c for c in cles if c not in DICO]
    check("3b chaque clé utilisée est au dictionnaire assemblé", not absentes, absentes[:10])
    vides = [c for c in cles if c in DICO and not (DICO[c].get("fr") and DICO[c].get("en"))]
    check("3c fr et en non vides", not vides, vides[:10])
    var = lambda t: sorted(set(re.findall(r"\{(\w+)\}", t)))      # noqa: E731
    diff = [c for c in cles if c in DICO and var(DICO[c]["fr"]) != var(DICO[c]["en"])]
    check("3d mêmes variables {x} en fr et en", not diff, [(c, DICO[c]) for c in diff[:5]])
    inutiles = [c for c in DICO if c.split(".")[0] in ZONES and c not in cles]
    check("3e aucune clé du lot au dictionnaire sans usage", not inutiles, inutiles[:10])
    p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("3f dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])
    # chaque appel dzT du lot ne passe que des variables que le texte connaît (sinon {x} resterait affiché)
    appels = re.findall(r'dzT\("((?:' + "|".join(ZONES) + r')\.[a-z0-9_.]+)",\{([^{}]*)\}', BUN)
    manque = []
    for c, corps in appels:
        noms = set(re.findall(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*(?=:|,|$)", corps))
        if c in DICO and set(var(DICO[c]["fr"])) - noms:
            manque.append((c, sorted(set(var(DICO[c]["fr"])) - noms)))
    check("3g chaque variable {x} d'un texte du lot est fournie par son appel dzT", not manque, manque[:8])

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
        t = pathlib.Path(tempfile.mkdtemp(prefix="dzl2n_"))
        echantillon = [c for z in ZONES for c in [k for k in cles if k.startswith(z + ".")][:8]]
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

    print("\n[5] plus de texte en dur dans le périmètre")
    import i18n_l2_perimetre as PER
    R5 = PER.restes(BUN, COUCHE, TABLE["gardes"])
    check("5a aucun texte visible en dur hors dzT dans les composants du lot", not R5, R5[:15])
    check("5b chaque composant du périmètre est trouvé", not [r for r in R5 if "introuvable" in r])

    print("\n[6] compteurs figés et syntaxe")
    check("6a x.useState( 731, DzTracks 181 (dzT est une fonction globale, pas un hook)",
          BUN.count("x.useState(") == 731 and BUN.count("DzTracks") == 181, (BUN.count("x.useState("), BUN.count("DzTracks")))
    check("6b fins de ligne intactes", BUNB.count(b"\r\n") == BUNB.count(b"\n") > 15000)
    # `return"texte"` minifié devenu `returndzT(…)` : identifiant valide (node --check passe), plantage à l'exécution
    colles = re.findall(r".{12}[A-Za-z0-9_$]dzT\(", BUN) + re.findall(r".{12}[A-Za-z0-9_$]dzT\(", COUCHE)
    colles = [m for m in colles if not m.endswith("__dzT(")]          # t145 : repli local de dialogue.js, un nom
    check("6e aucun dzT( collé à un mot (returndzT…) dans le bundle ni la couche", not colles, colles[:5])
    p = subprocess.run([sys.executable, str(RACINE / "scripts/qa/dump_studio_registry.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("6f le miroir du registre des nœuds (studio_nodes.json) reste celui du bundle : titres anglais d'origine",
          p.returncode == 0, (p.stdout + p.stderr)[-300:])
    if NODE:
        r = subprocess.run([NODE, "--check", str(RACINE / REL)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        check("6c node --check (script)", r.returncode == 0, (r.stderr or "")[-300:])
        with (RACINE / REL).open("rb") as fh:
            r = subprocess.run([NODE, "--input-type=module", "--check"], stdin=fh, capture_output=True)
        check("6d node --check (module)", r.returncode == 0, (r.stderr or b"")[-300:])

    print(f"\n=== {ok} passed, {fail} failed ===")
    return fail


def test_i18n_l2():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
