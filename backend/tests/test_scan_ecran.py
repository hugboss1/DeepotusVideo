# -*- coding: utf-8 -*-
"""t312 tâche 6 (28/10/2026) — l'ÉCRAN de la boîte « Scanner une page » dans l'Atelier/Chapitres.

Plan docs/superpowers/plans/2026-10-28-t312-scan-texte.md, Décisions 6 à 8. Le module partagé
frontend/shared/dz-scan.js (window.__dzScan.ouvrir) est monté par la page autonome de l'Atelier ; atelier.js passe par
la saisie L8 (scripts/i18n_l8/t312.py : la table réversible exige BASE + éditions) et pose les deux boutons.
[1] le script partagé : copie dist OCTET POUR OCTET, balise dans frontend/atelier/index.html après le dictionnaire,
    le runtime, dz-plafonds.js et dialogue.js, avant atelier.js ;
[2] le branchement : scanBoutons() pose #scanBtn après #importFile (« Importer (txt/docx/pdf) ») et #scanChapBtn après
    #msBtn (barre .chapbar) ; scanOuvrir passe inserer / creerChapitres / importerManuscrit ; insérer au curseur puis
    scheduleSave() ; un POST /chapters par chapitre dans la série courante ; manuscrit = File « scan.txt » par msRun ;
[3] les textes : clés atelier.t312_scan.* (saisie L8, FR et EN) et scan.* (frontend/shared/i18n/scan.json, FR et EN,
    mêmes variables, toutes employées) ; dictionnaire assemblé et L8 à jour ; aucun libellé français en dur ajouté ;
[4] garde-fous : jamais de confirm / alert / prompt natifs (dialogue maison), jamais innerHTML dans dz-scan.js ;
    l'icône du bouton seule passe par innerHTML (chaîne fixe de dzIcone), le libellé par un nœud texte ;
[5] la boîte sous node : frontend/shared/qa/scan.test.mjs (faux DOM, faux fetch, vraie enveloppe dz-plafonds.js).
Run : & $PY tests/test_scan_ecran.py   (depuis backend/)
"""
import json, pathlib, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
FRONT = REPO / "frontend"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:400]}")


def lire(rel):
    return (REPO / rel).read_bytes().decode("utf-8")


def bloc_t312(js):
    i = js.find("/* ═════════ t312 (C1 Scan)")
    j = js.find("/* ═════════ utilitaires ═════════ */", i)
    return js[i:j] if 0 <= i < j else ""


def main():
    src = FRONT / "shared" / "dz-scan.js"
    dist = FRONT / "dist" / "shared" / "dz-scan.js"
    S = src.read_bytes().decode("utf-8")
    html = lire("frontend/atelier/index.html")
    js = lire("frontend/atelier/atelier.js")
    bloc = bloc_t312(js)

    print("\n[1] le script partagé")
    check("1a copie dist octet pour octet", dist.is_file() and dist.read_bytes() == src.read_bytes())
    pos = {k: html.find(f'src="{k}"') for k in ("/shared/dz-i18n-dico.js", "/shared/dz-i18n.js", "/shared/dz-plafonds.js",
                                                "/shared/dialogue.js", "/shared/dz-scan.js", "atelier.js")}
    check("1b la page de l'Atelier charge /shared/dz-scan.js une fois", html.count('src="/shared/dz-scan.js"') == 1)
    check("1c après dictionnaire, runtime, dz-plafonds.js et dialogue.js ; avant atelier.js",
          0 <= pos["/shared/dz-i18n-dico.js"] < pos["/shared/dz-i18n.js"] < pos["/shared/dz-scan.js"] < pos["atelier.js"]
          and pos["/shared/dz-plafonds.js"] < pos["/shared/dz-scan.js"] and pos["/shared/dialogue.js"] < pos["/shared/dz-scan.js"], pos)
    check("1d le module expose window.__dzScan.ouvrir et se garde d'un second chargement",
          "window.__dzScan = {" in S and "ouvrir: ouvrir" in S and "if (window.__dzScan) return;" in S)
    check("1e routes de la Décision 6 employées", all(r in S for r in ('"/api/scan/lire"', '"/devis-vision"', '"/vision"',
                                                                     '"/api/scan/decoupage"')))
    check("1f délai 90 s, dix fichiers, 200 caractères", "DELAI_MS = 90000" in S and "MAX_FICHIERS = 10" in S
          and "MIN_MANUSCRIT = 200" in S)
    check("1g accept image/* et PDF, sélection multiple", 'accept: "image/*,application/pdf"' in S and 'multiple: ""' in S)

    print("\n[2] le branchement dans l'Atelier")
    check("2a le bloc t312 est dans atelier.js", bool(bloc))
    check("2b #importFile et #msBtn existent dans la page (voisins des boutons)",
          'id="importFile"' in html and 'id="msBtn"' in html and "chapbar" in html[:html.find('id="msBtn"')])
    check("2c scanBoutons pose #scanBtn après #importFile et #scanChapBtn après #msBtn",
          'poser("scanBtn", "atelier.t312_scan.bouton_t", $("#importFile"));' in bloc
          and 'poser("scanChapBtn", "atelier.t312_scan.chap_t", $("#msBtn"));' in bloc
          and 'insertAdjacentElement("afterend", b)' in bloc)
    check("2d scanBoutons() appelé au chargement", "  scanBoutons();" in js[js.find('window.addEventListener("DOMContentLoaded"'):])
    check("2e ouvrir avec les trois envois de l'hôte", "window.__dzScan.ouvrir({" in bloc and "inserer: scanInserer" in bloc
          and "creerChapitres: scanCreerChapitres" in bloc and "importerManuscrit: scanManuscrit" in bloc)
    check("2f insérer : au curseur de #script puis renderScript() et scheduleSave()",
          'const ta = $("#script");' in bloc and "ta.setRangeText(texte, a, b, \"end\");" in bloc
          and "renderScript(); scheduleSave();" in bloc)
    check("2g insérer refusé sans chapitre ou chapitre emporté (rend false)", "if (!chapter)" in bloc and "ta.readOnly" in bloc
          and bloc.count("return false;") >= 2)
    check("2h créer : un POST /chapters par chapitre, série courante, liste relue",
          'api.send("POST", "/chapters", { title: c.titre, series: serie, script_text: c.texte' in bloc
          and 'const serie = $("#chapterSeries").value;' in bloc and "await loadChapters(premier);" in bloc)
    check("2i manuscrit : File « scan.txt » par msRun, qui accepte ce File imposé",
          'await msRun(new File([texte], "scan.txt", { type: "text/plain" }));' in bloc
          and "async function msRun(impose) {" in js and "impose instanceof File" in js)
    check("2j msRun garde son bouton (l'évènement n'est pas un File)", '$("#msRun").addEventListener("click", msRun);' in js)

    print("\n[3] les textes")
    DIC = {}
    for fj in sorted((FRONT / "shared" / "i18n").glob("*.json")):
        DIC.update(json.loads(fj.read_text("utf-8")))
    cles_at = set(re.findall(r'"(atelier\.t312_scan\.[a-z0-9_]+)"', bloc))
    check("3a les clés atelier.t312_scan.* du bloc existent (fr, en)", len(cles_at) >= 7
          and all(DIC.get(k, {}).get("fr") and DIC.get(k, {}).get("en") for k in cles_at), sorted(cles_at))
    SC = json.loads((FRONT / "shared" / "i18n" / "scan.json").read_text("utf-8"))
    check("3b scan.json : fr et en non vides, mêmes variables",
          all(v.get("fr") and v.get("en") and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
              for v in SC.values()))
    employees = set(re.findall(r'T\("(scan\.[a-z0-9_.]*[a-z0-9_])"', S))
    check("3c chaque T(\"scan.…\") de dz-scan.js est au dictionnaire", employees and employees <= set(SC), sorted(employees - set(SC)))
    orph = [k for k in SC if f'"{k}"' not in S and not (k.startswith("scan.moteur.") and '"scan.moteur." +' in S)]
    check("3d aucune clé scan.* orpheline", not orph, orph)
    dico = lire("frontend/shared/dz-i18n-dico.js")
    check("3e le dictionnaire assemblé porte scan.* et atelier.t312_scan.*",
          '"scan.boite.titre"' in dico and '"atelier.t312_scan.bouton"' in dico)
    for script, args in (("i18n_assembler.py", ["--check"]), ("i18n_l8_generer.py", ["--check"])):
        p = subprocess.run([sys.executable, str(REPO / "scripts" / script), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(REPO))
        check(f"3f {script} --check à jour", p.returncode == 0, (p.stdout + p.stderr)[-300:])
    p = subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_l8_generer.py"), "--restes"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("3g aucun libellé français en dur (i18n_l8_generer --restes)", "restes : 0" in p.stdout, p.stdout[-300:])
    check("3h libellés du bloc par dzT (aucune chaîne française entre guillemets)",
          not re.search(r'(toast|title\s*=|createTextNode)\([^)]*"[^"]*[àâçéèêëîïôûùü][^"]*"', bloc))
    check("3i même « Scanner une page » dans l'Atelier et la boîte", DIC["atelier.t312_scan.bouton"]["fr"] == SC["scan.boite.titre"]["fr"]
          and DIC["atelier.t312_scan.bouton"]["en"] == SC["scan.boite.titre"]["en"])

    print("\n[4] garde-fous")
    nat = re.compile(r"(^|[^.\w])(confirm|alert|prompt)\(", re.M)
    check("4a aucun confirm / alert / prompt natif (dz-scan.js, bloc t312)", not nat.search(S) and not nat.search(bloc))
    check("4b la dépense passe par await window.__dzDialogue (dialogue maison)", "window.__dzDialogue" in S and "await D.confirmer(" in S)
    check("4c jamais innerHTML dans dz-scan.js", "innerHTML" not in S)
    check("4d bloc t312 : innerHTML pour l'icône fixe seulement, libellé en nœud texte",
          bloc.count("innerHTML") == 1 and 'b.innerHTML = ico("dz-media-image");' in bloc and "createTextNode" in bloc)
    check("4e le texte lu va au champ par .value / textContent (jamais en HTML)", "E.champ.value = texte;" in S)

    print("\n[5] la boîte sous node")
    if NODE:
        r = subprocess.run([NODE, str(FRONT / "shared" / "qa" / "scan.test.mjs")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        check("5a frontend/shared/qa/scan.test.mjs : tout passe", r.returncode == 0 and "0 failed" in r.stdout,
              (r.stdout + r.stderr)[-600:])
        r = subprocess.run([NODE, "--check", str(src)], capture_output=True, text=True)
        check("5b node --check dz-scan.js", r.returncode == 0, r.stderr[-200:])
    else:
        check("5 node introuvable", False)

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
