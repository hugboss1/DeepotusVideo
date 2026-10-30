# -*- coding: utf-8 -*-
"""Mutations t379 (30/10/2026) : le câblage des emplacements (backend/app/services/emplacements_cablage.py, routes,
lifespan, Job Dock, écran frontend/shared/dz-chemins.js et sa copie, dictionnaire chemins.json).
Chaque mutation doit faire ÉCHOUER son banc : backend/tests/test_emplacements_cablage.py (« serveur ») ou
backend/tests/test_emplacements_ecran.py (« ecran », qui joue aussi frontend/shared/qa/chemins.test.mjs). Les fichiers
sont copiés AVANT, restaurés après chaque mutation et comparés octet à octet à la fin. Une mutation « js » touche la
source ET sa copie de frontend/dist/shared.
Run (depuis la racine) : & $PY scripts/mutations_cablage.py [index…]   (sans index : toutes)"""
import filecmp, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_cablage_"))
F = {"service": RACINE / "backend/app/services/emplacements_cablage.py",
     "reglages": RACINE / "backend/app/api/settings_routes.py", "routes": RACINE / "backend/app/api/routes.py",
     "main": RACINE / "backend/app/main.py",
     "js": RACINE / "frontend/shared/dz-chemins.js", "jsdist": RACINE / "frontend/dist/shared/dz-chemins.js",
     "dico": RACINE / "frontend/shared/i18n/chemins.json"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
BANCS = {"serveur": [sys.executable, "backend/tests/test_emplacements_cablage.py"],
         "ecran": [sys.executable, "backend/tests/test_emplacements_ecran.py"]}
M = [
 # ── sauvegarde : rotation, échéance, échecs ──
 ("serveur", "service", "    for p in siennes[GARDER:]:", "    for p in siennes[GARDER + 1:]:"),
 ("serveur", "service", "if p.is_dir() and _NOM_SAUVEGARDE.match(p.name)\n                      and (p / transfert.MANIFESTE).is_file()),",
  "if p.is_dir() and _NOM_SAUVEGARDE.match(p.name)),"),
 ("serveur", "service", "if derniere and (n - derniere).total_seconds() < INTERVALLE_S:", "if derniere and (n - derniere).total_seconds() < 60:"),
 ("serveur", "service", "        if essai and not s.get(\"ok\") and (n - essai).total_seconds() < REESSAI_S:\n            continue\n", ""),
 ("serveur", "service", "    except Exception as ex:  # noqa: BLE001 — place insuffisante, base illisible, disque plein : un échec dit, au Dock",
  "    except ValueError as ex:  # noqa: BLE001 — place insuffisante, base illisible, disque plein : un échec dit, au Dock"),
 ("serveur", "service", "    if p.is_dir() and not (p / transfert.MANIFESTE).is_file():\n        shutil.rmtree(p, ignore_errors=True)",
  "    if False:\n        shutil.rmtree(p, ignore_errors=True)"),
 # ── miroir ──
 ("serveur", "service", "etat[\"miroir_depuis\"] = datetime.utcnow().isoformat()", "etat[\"miroir_depuis\"] = \"2000-01-01T00:00:00\""),
 ("serveur", "service", "            (JobRecord.provider.is_(None)) | (JobRecord.provider != PROVIDER))", "            True)"),
 ("serveur", "service", "        etat[\"miroir_depuis\"] = j.completed_at.isoformat()", "        etat[\"miroir_depuis\"] = _iso(j.completed_at)"),
 # ── Job Dock ──
 ("serveur", "service", "        j = next((x for x in ouverts if _meme_operation(json.loads(x.cost_meta or \"{}\"), meta)), None)",
  "        j = None"),
 ("serveur", "service", "            if _meme_operation(json.loads(j.cost_meta or \"{}\"), meta):\n                j.status,",
  "            if False:\n                j.status,"),
 ("serveur", "service", "    return msg(cle, lang or langue_ui())", "    return msg(cle, lang or \"fr\")"),
 ("serveur", "routes", "    if j.provider == \"emplacement\":            # t379", "    if False:            # t379"),
 ("serveur", "routes", "    \"emplacement\":   \"Sauvegarde, miroir ou index d'un emplacement (copie locale ou SFTP, t379)\",\n", ""),
 ("serveur", "main", "    empl_task = asyncio.create_task(_EC.boucle())", "    empl_task = None"),
 # ── source de bibliothèque ──
 ("serveur", "service", "dns[:] = sorted(d for d in dns if not d.startswith(\".\") and d not in (DOSSIER_SAUVEGARDES,))",
  "dns[:] = sorted(d for d in dns if d not in (DOSSIER_SAUVEGARDES,))"),
 ("serveur", "service", "            or str(rel) not in {x[\"chemin\"] for x in lire_index(eid)[\"fichiers\"]}:", "            :"),
 ("serveur", "service", "    if \"bibliotheque\" not in (e.get(\"roles\") or []):\n        raise", "    if False:\n        raise"),
 ("serveur", "service", "    if genre is None:\n        raise ValueError(\"import : images et sons seulement\")",
  "    if genre is None:\n        genre = \"image\""),
 ("serveur", "service", "    cache = settings.outputs_path / \"_cache\" / \"emplacements\" / eid", "    cache = DATA_ROOT / \"cache_emplacements\" / eid"),
 ("serveur", "reglages", "async def fichier_emplacement(eid: str, chemin: str, request: Request):\n    \"\"\"Un fichier INDEXÉ d'une source de bibliothèque, servi en lecture (confiné à l'emplacement).\"\"\"\n    _local(request)\n",
  "async def fichier_emplacement(eid: str, chemin: str, request: Request):\n    \"\"\"Un fichier INDEXÉ d'une source de bibliothèque, servi en lecture (confiné à l'emplacement).\"\"\"\n"),
 # ── l'écran (source ET copie) ──
 ("ecran", "js", "c.appendChild(el(\"img\", { src: url(x.chemin), alt: \"\", loading: \"lazy\",", "c.appendChild(el(\"img\", { src: url(x.chemin), alt: \"\","),
 ("ecran", "js", "var IMPORTABLES = /\\.(png|jpe?g|webp|mp3|wav|ogg|flac|m4a)$/i;", "var IMPORTABLES = /\\.(png|jpe?g|webp|mp3|wav|ogg|flac|m4a|mp4)$/i;"),
 ("ecran", "js", "    if (!id || !dock.ids[id]) return false;", "    if (!id) return false;"),
 ("ecran", "js", "    if (!outils || outils.__dzChemins) return Promise.resolve(null);", "    if (!outils) return Promise.resolve(null);"),
 ("ecran", "js", "d.addEventListener(\"click\", surClicDock, true);", "d.addEventListener(\"click\", surClicDock, false);"),
 ("ecran", "js", "        outils.insertAdjacentElement(\"afterend\", panneau);", "        outils.appendChild(panneau);"),
 ("ecran", "js", "if (j.relance === \"emplacement\") ids[j.job_id] = 1;", "ids[j.job_id] = 1;"),
 ("ecran", "dico", "\"en\": \"Back up now\"", "\"en\": \"Sauvegarder maintenant\""),
]


def restaurer():
    for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)


def muter(cle, avant, apres):
    p = F[cle]
    b = p.read_bytes().decode("utf-8")
    lf = b.replace("\r\n", "\n")
    a, z = avant.replace("\r\n", "\n"), apres.replace("\r\n", "\n")
    if lf.count(a) != 1:
        return f"ancre x{lf.count(a)}"
    neuf = lf.replace(a, z, 1)
    if "\r\n" in b: neuf = neuf.replace("\n", "\r\n")
    p.write_bytes(neuf.encode("utf-8"))
    if cle == "js":
        shutil.copyfile(p, F["jsdist"])
    return None


tues = survivants = 0
try:
    SEULES = {int(x) for x in sys.argv[1:]}
    for i, (banc, cle, avant, apres) in enumerate(M):
        if SEULES and i not in SEULES:
            continue
        err = muter(cle, avant, apres)
        if err:
            print(f"  ??  {i:2d}  {err} dans {cle} : {avant[:70]!r}"); survivants += 1; restaurer(); continue
        r = subprocess.run(BANCS[banc], cwd=str(RACINE), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        if r.returncode != 0:
            tues += 1; print(f"  TUÉ {i:2d}  {banc}/{cle} : {avant[:70]!r}")
        else:
            survivants += 1; print(f"  SURVIT {i:2d}  {banc}/{cle} : {avant[:70]!r}")
        restaurer()
finally:
    restaurer()
    egaux = all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items())
    print(f"\n{tues} tués / {survivants} survivants ; sources restaurées à l'octet : {egaux}")
    sys.exit(0 if survivants == 0 and egaux else 1)
