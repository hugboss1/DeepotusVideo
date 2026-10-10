# -*- coding: utf-8 -*-
"""t145 (09/10/2026) — traduction L5 : la piste de sous-titres du Montage (bloc SUBS), le transfert entre machines et
les dialogues maison passent par dzT(clé) (plan docs/superpowers/plans/2026-10-09-traduction-l5-sous-titres-transfert-
dialogues.md, skill traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l5_generer.py --check (table, sources et dictionnaires à jour).
  [2] le maillon patch_bundle_i18n_l5.py (bloc SUBS) et les deux sources : REJEU — le bundle de BASE (2b155403), ses
      blocs TRANSFERT et DIALOGUE rafraîchis depuis les sources du poste, puis le maillon rend EXACTEMENT le bundle du
      poste ; double application refusée ; sans L2 en amont refus ; aucun .bak ; la traduction se défait exactement
      (avant_i18n_l5, sans git) ; les sources sont celles du générateur et leur version d'avant se reconstruit ; les
      trois copies de dialogue.js sont identiques ; subs.js n'est pas touché.
  [3] le dictionnaire : chaque clé subs. / transfert. / dialogue. utilisée existe, fr et en non vides, mêmes
      variables des deux côtés et fournies par l'appel ; aucune clé du lot sans usage ; assemblage à jour.
  [4] le runtime sous node : dzT rend le français et l'anglais des clés du lot.
  [5] plus de texte français en dur dans le périmètre (restes de chaque groupe de la saisie).
  [6] compteurs figés (x.useState( 731, DzTracks 181), CRLF, aucun dzT collé à un mot, node --check.
Run : & $PY tests/test_i18n_l5.py   (depuis backend/)
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
# le bundle de référence : tant que t145 n'est pas commis, le bundle du poste ; une fois commis, épingler ici le commit
T145 = None
NODE = shutil.which("node")
ZONES = ("subs", "transfert", "dialogue")
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
    import i18n_l5_generer as G
    import _i18n_l1_aide as AIDE

    BUNB = (RACINE / REL).read_bytes()
    BUN = BUNB.decode("utf-8")
    TABLE = json.loads((RACINE / "scripts/i18n_l5_paires.json").read_bytes().decode("utf-8"))
    SRC = {c: (RACINE / rel).read_bytes().decode("utf-8") for c, rel in G.SOURCES.items()}

    print("\n[1] la saisie et le générateur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_l5_generer.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1a générateur --check : table, sources et dictionnaires à jour", p.returncode == 0, (p.stdout + p.stderr)[-400:])
    check("1b la table porte la base, au moins 400 substitutions dans le bloc SUBS, des substitutions dans chaque source",
          TABLE.get("base") == G.BASE and len(TABLE["paires"]) >= 400 and all(TABLE["sources"].get(c) for c in G.SOURCES),
          (len(TABLE["paires"]), {c: len(v) for c, v in TABLE["sources"].items()}))
    check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))

    print("\n[2] le maillon et les sources")
    SCRIPT = RACINE / "scripts/patch_bundle_i18n_l5.py"
    S = SCRIPT.read_bytes().decode("utf-8")
    check("2a lecture et écriture en octets", "read_text(" not in S and "write_text(" not in S and "read_bytes()" in S)
    eol = b"\r\n" if BUNB.count(b"\r\n") == BUNB.count(b"\n") else b"\n"
    B = G.bases()
    base = B["subs"][0]
    # t143 + icônes G1 (10/10) : L3 (bloc MONTAGE) et G1 (maillon dzglyph, éditions des couches et de transfert.js)
    # sont posés APRÈS la BASE de L5 — on compare dans la vue d'avant G1, couches rafraîchissables prises au poste
    PRE = AIDE.avant_dzglyph(BUN)
    for tag in ("MONTAGE", "SONVFX", "SFXSTUDIO", "VFXRACK"):
        base = G.avec_bloc(base, tag, PRE.split(f"/*__DZ_{tag}_BEGIN__*/", 1)[1].split(f"/*__DZ_{tag}_END__*/", 1)[0])
    SRC0 = {c: AIDE.couche_avant_dzglyph(s, c) for c, s in SRC.items()}
    reference = (subprocess.run(["git", "show", f"{T145}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
                 if T145 else PRE.encode("utf-8")).replace(b"\r\n", b"\n").replace(b"\n", eol)
    rafraichi = base
    for c in G.SOURCES:
        rafraichi = G.avec_bloc(rafraichi, G.TAGS[c], G.sans_marqueurs(SRC0[c], G.TAGS[c]))
    TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzl5_"))
    try:
        (TMP / "frontend/dist/assets").mkdir(parents=True)
        (TMP / "scripts").mkdir()
        shutil.copy(RACINE / "scripts/i18n_l5_paires.json", TMP / "scripts/i18n_l5_paires.json")
        (TMP / REL).write_bytes(rafraichi.encode("utf-8"))
        r1 = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        rejoue = (TMP / REL).read_bytes()
        check("2b rejeu : base + blocs rafraîchis + maillon = bundle de référence, octet pour octet",
              r1.returncode == 0 and rejoue == reference, (r1.returncode, (r1.stdout + r1.stderr)[-300:]))
        check("2c aucun .bak laissé", not list((TMP / "frontend/dist/assets").glob("*.bak_*")))
        r2 = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        check("2d second passage refusé (double application)",
              r2.returncode != 0 and "double application" in r2.stdout + r2.stderr and (TMP / REL).read_bytes() == rejoue)
        (TMP / REL).write_bytes(rafraichi.replace('dzT("studio.palette.titre")', '"Palette"').encode("utf-8"))
        r3 = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        check("2e sans le maillon L2 en amont, refus (sonde)", r3.returncode != 0 and "i18nl2" in r3.stdout + r3.stderr,
              (r3.stdout + r3.stderr)[-200:])
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    check("2f aucun .bak_i18nl5 dans le dépôt", not (RACINE / (REL + ".bak_i18nl5")).exists())
    try:
        check("2g la traduction L5 se défait exactement, sans git : avant_i18n_l5(bundle) == base, octet pour octet",
              AIDE.avant_i18n_l5(BUN) == base, "écart")
        check("2g' même chose sur le bundle lu en LF (read_text)", AIDE.avant_i18n_l5(BUN.replace("\r\n", "\n"))
              == base.replace("\r\n", "\n"))
    except ValueError as e:
        check("2g la traduction L5 se défait exactement", False, e)
    final = G.construire(B)
    for c in G.SOURCES:
        check(f"2h {c} : la source du poste est celle que le générateur produit", SRC[c] == G._g1(final[1][c], G.TAGS[c]))
        try:
            check(f"2i {c} : la source d'avant L5 se reconstruit exactement, sans git",
                  AIDE.source_avant_i18n_l5(SRC0[c], c) == B[c][0])
        except ValueError as e:
            check(f"2i {c} : la source d'avant L5 se reconstruit", False, e)
        tag = G.TAGS[c]
        coeur = BUN.split(f"/*__DZ_{tag}_BEGIN__*/", 1)[1].split(f"/*__DZ_{tag}_END__*/", 1)[0]
        check(f"2j le bloc {tag} du bundle est la source au marqueur près (refresh_layer --layer {c})",
              coeur.strip("\r\n") == G.sans_marqueurs(SRC[c], tag).strip("\r\n"))
    d = (RACINE / "frontend/shared/dialogue.js").read_bytes()
    check("2k les trois dialogue.js sont identiques octet pour octet",
          all((RACINE / x).read_bytes() == d for x in G.COPIES["dialogue"]))
    subs_js = subprocess.run(["git", "diff", "--quiet", G.BASE, "--", "frontend/patches/subs.js"], cwd=str(RACINE))
    check("2l frontend/patches/subs.js n'est pas touché (intouchable : le bloc SUBS passe par le maillon)",
          subs_js.returncode == 0)

    print("\n[3] le dictionnaire")
    DICO = {}
    for f in sorted((RACINE / "frontend/shared/i18n").glob("*.json")):
        DICO.update(json.loads(f.read_text("utf-8")))
    texte = BUN + "".join(SRC.values())
    motif = r'(?:dzT|__dzT)\("((?:' + "|".join(ZONES) + r')\.[a-z0-9_.]+)"'
    cles = sorted(c for c in set(re.findall(motif, texte)) if not c.endswith("_"))     # « …nom_" + k » : préfixe
    # clés composées à l'exécution (« transfert.lot.nom_" + k ») : reconnues par leur préfixe
    composees = set(re.findall(r'dzT\("((?:' + "|".join(ZONES) + r')\.[a-z0-9_.]+_)"\s*\+', texte))
    check("3a au moins 400 clés du lot sont utilisées", len(cles) >= 400, len(cles))
    absentes = [c for c in cles if c not in DICO]
    check("3b chaque clé utilisée est au dictionnaire assemblé", not absentes, absentes[:10])
    vides = [c for c in cles if c in DICO and not (DICO[c].get("fr") and DICO[c].get("en"))]
    check("3c fr et en non vides", not vides, vides[:10])
    var = lambda t: sorted(set(re.findall(r"\{(\w+)\}", t)))      # noqa: E731
    diff = [c for c in cles if c in DICO and var(DICO[c]["fr"]) != var(DICO[c]["en"])]
    check("3d mêmes variables {x} en fr et en", not diff, [(c, DICO[c]) for c in diff[:5]])
    inutiles = [c for c in DICO if c.split(".")[0] in ZONES and c not in cles and not any(c.startswith(p) for p in composees)]
    check("3e aucune clé du lot au dictionnaire sans usage", not inutiles, inutiles[:10])
    p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("3f dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])
    appels = re.findall(r'dzT\("((?:' + "|".join(ZONES) + r')\.[a-z0-9_.]+)",\s*\{([^{}]*)\}', texte)
    manque = []
    for c, corps in appels:
        corps = re.sub(r"/\*.*?\*/", "", corps, flags=re.S)          # un commentaire entre deux variables
        noms = set(re.findall(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*(?=:|,|$)", corps))
        if c in DICO and set(var(DICO[c]["fr"])) - noms:
            manque.append((c, sorted(set(var(DICO[c]["fr"])) - noms)))
    check("3g chaque variable {x} d'un texte du lot est fournie par son appel dzT", not manque, manque[:8])
    sans_var = [c for c in cles if c in DICO and var(DICO[c]["fr"]) and not re.search(r'dzT\("' + re.escape(c) + r'",', texte)]
    check("3h un texte à variables n'est jamais appelé sans elles", not sans_var, sans_var[:8])

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
        t = pathlib.Path(tempfile.mkdtemp(prefix="dzl5n_"))
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
    E = G.entrees()
    groupes = sorted({e["groupe"] for e in E})
    R5 = [(g, r) for g in groupes for r in G.restes(B, g, E)]
    check("5a aucun texte visible en dur hors dzT dans les plages de la saisie", not R5, R5[:15])
    subs_lignes = B["subs"][0].count("\n", B["subs"][3], B["subs"][2]) + 1
    plages = sorted(e["plage"] for e in E if e["cible"] == "subs")
    couvert = set()
    for a, b in plages:
        couvert.update(range(a, b + 1))
    # la dernière ligne est celle du marqueur END
    check("5b les plages de la saisie couvrent tout le bloc SUBS", set(range(1, subs_lignes)) <= couvert,
          sorted(set(range(1, subs_lignes)) - couvert)[:10])

    print("\n[6] compteurs figés et syntaxe")
    check("6a x.useState( 731, DzTracks 181 (dzT est une fonction globale, pas un hook)",
          BUN.count("x.useState(") == 731 and BUN.count("DzTracks") == 181, (BUN.count("x.useState("), BUN.count("DzTracks")))
    check("6b fins de ligne intactes", BUNB.count(b"\r\n") == BUNB.count(b"\n") > 15000)
    # `__dzT(` (repli local de dialogue.js) est un nom, pas un collage
    colles = [m for m in re.findall(r".{12}[A-Za-z0-9_$]dzT\(", BUN) if not m.endswith("__dzT(")]
    check("6c aucun dzT( collé à un mot (returndzT…)", not colles, colles[:5])
    if NODE:
        with (RACINE / REL).open("rb") as fh:
            r = subprocess.run([NODE, "--input-type=module", "--check"], stdin=fh, capture_output=True)
        check("6d node --check du bundle (module)", r.returncode == 0, (r.stderr or b"")[-300:])
        for c, rel in G.SOURCES.items():
            r = subprocess.run([NODE, "--check", str(RACINE / rel)], capture_output=True, text=True, encoding="utf-8")
            check(f"6e node --check {rel}", r.returncode == 0, (r.stderr or "")[-300:])

    print(f"\n=== {ok} passed, {fail} failed ===")
    return fail


def test_i18n_l5():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
