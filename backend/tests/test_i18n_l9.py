# -*- coding: utf-8 -*-
"""t149 (10/10/2026) — traduction L9 : le Spritelab, le Tile Lab, le Studio3D, le Plateau et la bibliothèque 3D partagée
(frontend/spritelab, tilelab, studio3d, plateau, lib3d) passent par __dzT9(clé, fr) — dzT dans la page, le français sous
node où les bancs exécutent ces modules ; les textes des pages HTML sont traduits à l'affichage par la surcouche
(entrées H), les <option> et les textes « contexte » de chaque page par une passe au démarrage (consigne
scripts/i18n_l9/CONSIGNE.md, skill traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l9_generer.py --check (scripts, table, dictionnaires à jour).
  [2] la réversibilité : chaque script se défait exactement vers la source de la BASE par la table, sans git
      (_i18n_l1_aide.source_avant_i18n_l9, _labs_avant_l9), et la table rejoue chaque script.
  [3] les dictionnaires sprites/tuiles/studio3d/plateau/lib3d : chaque clé des scripts existe, fr et en non vides,
      mêmes variables {x} ; le français écrit en repli dans la source EST celui du dictionnaire ; aucune clé sans usage ;
      assemblage à jour.
  [4] le repli : un module exécuté sous node rend le français (calc.js du Plateau) ; avec un dzT dans la page, l'anglais.
  [5] plus de texte français en dur : --restes ne trouve rien hors des littéraux GARDÉS (motivés dans la saisie).
  [6] syntaxe : node --check (scripts classiques ; modules copiés en .mjs) ; aucun dzT( collé à un mot ; fins de ligne
      homogènes ; chaque page charge le dictionnaire puis le runtime AVANT son script ; passe de démarrage.
Run : & $PY tests/test_i18n_l9.py   (depuis backend/)
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
ZONES = {"sprites": "spritelab", "tuiles": "tilelab", "studio3d": "studio3d", "plateau": "plateau", "lib3d": "lib3d"}
CLASSIQUES = {"spritelab/spritelab.js", "tilelab/tilelab.js", "tilelab/jeu.js", "tilelab/peintre.js"}
PAGES = {"spritelab/index.html": "spritelab.js", "tilelab/index.html": "tilelab.js",
         "studio3d/index.html": "studio3d.js", "plateau/index.html": "plateau.js"}
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
    import i18n_l9_generer as G
    import _i18n_l1_aide as AIDE
    n = lambda t: t.replace("\r\n", "\n")                                   # noqa: E731
    TABLE = json.loads(G.PAIRES.read_bytes().decode("utf-8"))
    SCRIPTS = sorted(TABLE["fichiers"])

    print("\n[1] la saisie et le générateur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l9_generer.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1a i18n_l9_generer --check : à jour", p.returncode == 0, (p.stdout + p.stderr)[-400:])
    ned = sum(len(v) for v in TABLE["fichiers"].values())
    check("1b la table porte la base et au moins 450 éditions", TABLE.get("base") == G.BASE and ned >= 450, ned)
    check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))
    check("1d les scripts principaux des quatre labs sont traduits",
          {"spritelab/spritelab.js", "tilelab/tilelab.js", "studio3d/studio3d.js", "plateau/plateau.js"} <= set(SCRIPTS),
          SCRIPTS)

    print("\n[2] la réversibilité")
    mauvais, rejoue = [], []
    for f in SCRIPTS:
        cur = (FRONT / f).read_bytes().decode("utf-8")
        base = G.base(f)
        try:
            if n(AIDE.source_avant_i18n_l9(cur, f)) != n(base):
                mauvais.append(f)
        except ValueError as e:
            mauvais.append(f"{f} ({e})")
        try:
            if n(G.appliquer(f, base)) != n(cur):
                rejoue.append(f)
        except ValueError as e:
            rejoue.append(f"{f} ({e})")
    check(f"2a chaque script ({len(SCRIPTS)}) se défait exactement vers sa source de BASE, sans git", not mauvais,
          mauvais[:5])
    check("2b la table rejoue chaque script : base + éditions = source du poste", not rejoue, rejoue[:5])
    code = ("import sys, pathlib; sys.path.insert(0, sys.argv[1]); import _labs_avant_l9; "
            "print(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8').count('__dzT9('))")
    r = subprocess.run([sys.executable, "-c", code, str(HERE), str(FRONT / "spritelab" / "spritelab.js")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("2c _labs_avant_l9 : un banc qui l'importe lit le Spritelab d'avant L9 (aucun __dzT9)", r.stdout.strip() == "0",
          (r.stdout + r.stderr)[-300:])

    print("\n[3] les dictionnaires")
    DICO = {}
    for fj in sorted((FRONT / "shared" / "i18n").glob("*.json")):
        DICO.update(json.loads(fj.read_text("utf-8")))
    import html as _html
    for z, lab in ZONES.items():
        ZON = json.loads((FRONT / "shared" / "i18n" / f"{z}.json").read_text("utf-8"))
        texte = "".join((FRONT / f).read_bytes().decode("utf-8") for f in SCRIPTS if f.startswith(lab + "/"))
        appels = re.findall(r'__dzT9\("(' + z + r'\.[a-z0-9_.]+)", ("(?:[^"\\]|\\.)*")', texte)
        cles = {c for c, _fr in appels}
        check(f"3a [{z}] des clés utilisées", len(cles) >= (1 if z == "lib3d" else 30), len(cles))
        absentes = sorted(c for c in cles if c not in DICO)
        check(f"3b [{z}] chaque clé utilisée est au dictionnaire", not absentes, absentes[:8])
        ecarts = sorted({c for c, fr in appels if c in DICO and json.loads(fr) != DICO[c]["fr"]})
        check(f"3c [{z}] le français de repli écrit dans la source est celui du dictionnaire", not ecarts, ecarts[:6])
        check(f"3d [{z}] fr et en non vides", all(v.get("fr") and v.get("en") for v in ZON.values()))
        vars_ko = [k for k, v in ZON.items()
                   if set(re.findall(r"\{(\w+)\}", v["fr"])) != set(re.findall(r"\{(\w+)\}", v["en"]))]
        check(f"3e [{z}] mêmes variables {{x}} en fr et en", not vars_ko, vars_ko[:6])
        pages = " ".join(re.sub(r"\s+", " ", _html.unescape(p.read_bytes().decode("utf-8")))
                         for p in (FRONT / lab).glob("*.html"))
        sans_usage = [k for k, v in ZON.items() if k not in cles and re.sub(r"\s+", " ", _html.unescape(v["fr"])) not in pages]
        check(f"3f [{z}] aucune clé sans usage (script ou texte d'une page)", not sans_usage, sans_usage[:8])
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("3g dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])

    print("\n[4] le repli sous node, l'anglais dans la page")
    if NODE:
        calc = (FRONT / "plateau" / "calc.js").as_uri()
        js = (f"const C = await import({json.dumps(calc)});\n"
              "const msg = () => { try { C.preset('zz', { orbit: [0, 0, 5], target: [0, 0, 0], fov: 40 }, 2); return ''; } catch (e) { return e.message; } };\n"
              "const fr = msg();\n"
              "globalThis.dzT = (k) => 'EN:' + k;\n"
              "console.log(JSON.stringify([fr, msg()]));\n")
        r = subprocess.run([NODE, "--input-type=module", "-e", js], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        try:
            d = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                           # noqa: BLE001
            d = []
        check("4a calc.js sous node : « preset inconnu » en français, puis la clé du dictionnaire quand dzT existe",
              len(d) == 2 and d[0] == "preset inconnu" and d[1].startswith("EN:plateau."), (r.stdout + r.stderr)[-300:])
    else:
        check("4 node introuvable", False)

    print("\n[5] plus de texte français en dur")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l9_generer.py"), "--restes"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    m = re.search(r"restes : (\d+)", p.stdout)
    check("5a aucun littéral d'allure française en dur hors des gardés (i18n_l9_generer --restes)",
          m and m.group(1) == "0", p.stdout[-600:])

    print("\n[6] syntaxe et chargement")
    syntaxe, colles, eol, aide = [], [], [], []
    with tempfile.TemporaryDirectory(prefix="dzl9s_") as tmp:
        for f in SCRIPTS:
            s = (FRONT / f).read_bytes().decode("utf-8")
            if re.search(r"[\w$]dzT\(|[\w$]__dzT9\(", s):
                colles.append(f)
            if s.count("\r\n") != s.count("\n"):
                eol.append(f)
            if "__dzT9(" in s and "function __dzT9(k, fr, v)" not in s:
                aide.append(f)
            if NODE:
                cible = FRONT / f
                if f not in CLASSIQUES:
                    cible = pathlib.Path(tmp) / (pathlib.Path(f).stem + ".mjs")
                    cible.write_bytes(s.encode("utf-8"))
                r = subprocess.run([NODE, "--check", str(cible)], capture_output=True, text=True)
                if r.returncode:
                    syntaxe.append(f"{f}: {r.stderr.strip()[-160:]}")
    check("6a node --check de chaque script touché", not syntaxe, syntaxe[:3])
    check("6b aucun dzT( / __dzT9( collé à un identifiant (returndzT…)", not colles, colles)
    check("6c fins de ligne homogènes", not eol, eol)
    check("6d chaque script qui appelle __dzT9 la déclare", not aide, aide)
    for page, script in PAGES.items():
        s = (FRONT / page).read_bytes().decode("utf-8")
        i_dico, i_run = s.find('src="/shared/dz-i18n-dico.js"'), s.find('src="/shared/dz-i18n.js"')
        i_lab = s.find(f'src="{script}"')
        check(f"6e {page} charge le dictionnaire puis le runtime AVANT {script}", 0 <= i_dico < i_run < i_lab,
              (i_dico, i_run, i_lab))
        s = (FRONT / pathlib.Path(page).parent / script).read_bytes().decode("utf-8")
        check(f"6f {script} : passe de démarrage (<option> + textes « contexte » de sa page)",
              "t149 (traduction L9) : passe unique au chargement" in s and "__dzI18n" in s and "D[k].contexte" in s)

    print("\n[7] le catalogue serveur du Spritelab (/particles/presets) et les fiches anglaises")
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l9_serveur.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("7a i18n_l9_serveur --check : messages.json à jour, fr = texte de particle_service et du catalogue starter",
          p.returncode == 0, (p.stdout + p.stderr)[-300:])
    import os
    _tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzl9c_"))           # l'application importée : dossier jetable
    os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
    sys.path.insert(0, str(RACINE / "backend"))
    from app.i18n import catalogues as CAT                             # noqa: E402
    from app.services import particle_service as PS                     # noqa: E402
    charge = {"presets": [{"id": q["id"], "name": q["name"], "type": q["type"], "desc": q["desc"]} for q in PS.PRESETS],
              "anims": [{"id": "black-smoke", "name": "Fumée noire"}]}
    en = CAT.particules(charge, "en")
    check("7b en anglais : noms, descriptions et « boucle » traduits, ids inchangés ; la source intacte",
          en["presets"][1]["name"] == "Soft smoke" and en["presets"][1]["type"] == "alpha · loop"
          and en["anims"][0]["name"] == "Black smoke" and [q["id"] for q in en["presets"]] == [q["id"] for q in PS.PRESETS]
          and charge["presets"][1]["name"] == "Fumée douce", en["presets"][:2])
    check("7c en français (ou langue inconnue) : la charge rendue telle quelle",
          CAT.particules(charge, "fr") is charge and CAT.particules(charge, "de") is charge)
    for lab in ("spritelab", "tilelab"):
        idx = json.loads((FRONT / lab / "aide" / "index.json").read_text("utf-8"))
        manque = [f["id"] for f in idx if not (f.get("titre_en") and f.get("phrase_en") and f.get("fichier_en")
                                               and (FRONT / lab / "aide" / f["fichier_en"]).is_file())]
        check(f"7d [{lab}] chaque fiche a sa version anglaise (titre, phrase, animation capturée en anglais)", not manque,
              manque)

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
