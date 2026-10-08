# -*- coding: utf-8 -*-
"""t140 (Photolab P5) — le moteur dans l'installeur : manifeste fichier par fichier, vérificateur, étape de build,
aucune dépendance au redistribuable VC++, NOTICE et licences.
  [1] le manifeste (vendor/photocraft.json « fichiers ») et le dossier du moteur s'il est présent ;
  [2] le vérificateur sur un dossier SYNTHÉTIQUE : conforme, octet altéré, fichier manquant, fichier en trop,
      préférences de l'app native (PhotoCraftData) ignorées ;
  [3] les imports des deux exécutables : ni vcruntime, ni msvcp, ni UCRT ; un import CRT est signalé ;
  [4] build-installer.ps1 : l'étape 4c vérifie l'arbre PRÉPARÉ et arrête le build sur écart, avant ISCC ;
  [5] NOTICE : chaque licence livrée y est citée, la version aussi ; vendor_photocraft.py revérifie l'extraction.
Run : & $PY tests/test_photolab_installeur.py   (depuis backend/)"""
import hashlib, json, pathlib, shutil, struct, subprocess, sys, tempfile

sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:400]}")


try:
    import verifier_vendor as V
except Exception as e:                       # le banc rougit, ne meurt pas
    V = None
    print(f"  (import du vérificateur impossible : {e!r})")
M = json.loads((RACINE / "vendor" / "photocraft.json").read_text("utf-8"))
FICHIERS = M.get("fichiers") or {}
DOSSIER = RACINE / M["binaire"]["dossier"]

print("\n[1] le manifeste")
noms = {pathlib.PurePosixPath(k).name for k in FICHIERS}
check("1a le manifeste liste chaque fichier livré (2 exe, 2 licences du moteur, 3 OFL, README, portable.txt)",
      {"photocraft-cli.exe", "photocraft.exe", "LICENSE-MIT", "LICENSE-APACHE", "OFL-biz-ud-mincho.txt",
       "OFL-biz-ud-pgothic.txt", "OFL-shippori-mincho.txt", "README.md", "portable.txt"} == noms, sorted(noms))
check("1b chaque entrée : taille entière > 0 et sha256 de 64 hex, chemins relatifs en /",
      all(isinstance(v.get("taille"), int) and v["taille"] > 0 and len(v.get("sha256", "")) == 64
          and "\\" not in k and not k.startswith("/") and ".." not in k for k, v in FICHIERS.items()), FICHIERS)
check("1c la provenance du manifeste est dite (archive vérifiée)", "9997f7df" in json.dumps(M.get("fichiers_source", "")))
if DOSSIER.is_dir() and V:
    check("1d le dossier du moteur de ce poste est conforme au manifeste", V.comparer(FICHIERS, DOSSIER) == [],
          V.comparer(FICHIERS, DOSSIER))
else:
    check("1d le dossier du moteur est présent sur ce poste (sinon : python scripts/vendor_photocraft.py)", False, DOSSIER)

print("\n[2] le vérificateur, sur un dossier synthétique")
if V:
    T = pathlib.Path(tempfile.mkdtemp(prefix="dzt140v_"))
    try:
        (T / "app").mkdir()
        (T / "app" / "a.exe").write_bytes(b"MZ" + b"\0" * 62)
        (T / "LICENSE-MIT").write_bytes(b"MIT\n")
        man = V.empreintes(T)
        check("2a empreintes : chemins relatifs en /, taille et sha256", man == {
            "LICENSE-MIT": {"taille": 4, "sha256": hashlib.sha256(b"MIT\n").hexdigest()},
            "app/a.exe": {"taille": 64, "sha256": hashlib.sha256(b"MZ" + b"\0" * 62).hexdigest()}}, man)
        check("2b dossier conforme -> aucun écart", V.comparer(man, T) == [])
        # là où le mode portable les écrit vraiment : À CÔTÉ de photocraft.exe, donc un niveau sous la racine (relevé t140)
        (T / "app" / "PhotoCraftData").mkdir()
        (T / "app" / "PhotoCraftData" / "preferences.json").write_text("{}")
        check("2c les préférences de l'app native (app/PhotoCraftData, à côté de l'exe) ne sont pas un écart",
              V.comparer(man, T) == [], V.comparer(man, T))
        (T / "LICENSE-MIT").write_bytes(b"MIX\n")
        e = V.comparer(man, T)
        check("2d un octet altéré (même taille) est dit", len(e) == 1 and "LICENSE-MIT" in e[0] and "sha256" in e[0], e)
        (T / "LICENSE-MIT").unlink()
        e = V.comparer(man, T)
        check("2e un fichier manquant est dit", len(e) == 1 and "manquant" in e[0], e)
        (T / "LICENSE-MIT").write_bytes(b"MIT\n")
        (T / "app" / "intrus.dll").write_bytes(b"x")
        e = V.comparer(man, T)
        check("2f un fichier en trop est dit (une DLL glissée à côté du moteur)", len(e) == 1 and "intrus.dll" in e[0] and "en trop" in e[0], e)
        p = subprocess.run([sys.executable, str(RACINE / "scripts" / "verifier_vendor.py"), str(T)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        check("2g en ligne de commande : un dossier non conforme -> code 1 et l'écart nommé", p.returncode == 1
              and ("manquant" in p.stdout + p.stderr or "en trop" in p.stdout + p.stderr), (p.returncode, p.stdout[-300:], p.stderr[-300:]))
    finally:
        shutil.rmtree(T, ignore_errors=True)
    if DOSSIER.is_dir():
        p = subprocess.run([sys.executable, str(RACINE / "scripts" / "verifier_vendor.py")], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        check("2h en ligne de commande : le dossier du moteur de ce poste -> code 0", p.returncode == 0, (p.stdout[-300:], p.stderr[-300:]))

print("\n[3] redistribuable VC++")
if V and DOSSIER.is_dir():
    for exe in ("photocraft-cli.exe", "photocraft.exe"):
        f = next(DOSSIER.rglob(exe), None)
        imp = V.imports_pe(f) if f else []
        check(f"3a {exe} : imports lus (kernel32 au moins)", any(x.lower() == "kernel32.dll" for x in imp), imp)
        check(f"3b {exe} : ni vcruntime, ni msvcp, ni UCRT — aucun redistribuable à installer", V.crt(imp) == [], V.crt(imp))
    check("3c un import CRT serait signalé", V.crt(["KERNEL32.dll", "VCRUNTIME140.dll", "api-ms-win-crt-runtime-l1-1-0.dll",
                                                   "MSVCP140.dll", "ucrtbase.dll"]) == ["VCRUNTIME140.dll",
          "api-ms-win-crt-runtime-l1-1-0.dll", "MSVCP140.dll", "ucrtbase.dll"])
    check("3d le vérificateur refuse un moteur qui dépendrait du CRT (le build s'arrêterait)",
          "crt(" in (RACINE / "scripts" / "verifier_vendor.py").read_text("utf-8").split("def main", 1)[-1])

print("\n[4] build-installer.ps1")
ps = (RACINE / "scripts" / "build-installer.ps1").read_text("utf-8")
i4c, iscc = ps.find("# ---- 4c. photocraft"), ps.find("# ---- 5. Compile with Inno Setup")
etape = ps[i4c:iscc] if 0 < i4c < iscc else ""
check("4a l'étape 4c existe, AVANT la compilation Inno Setup", bool(etape), (i4c, iscc))
check("4b elle fournit le moteur s'il manque, par vendor_photocraft.py (release officielle, empreinte)",
      "vendor_photocraft.py" in etape)
check("4c elle vérifie l'arbre PRÉPARÉ (stageApp), pas seulement le poste de build",
      "verifier_vendor.py" in etape and "$stageApp" in etape)
check("4d un écart arrête le build (throw sur code de sortie non nul)", "LASTEXITCODE" in etape and "throw" in etape)
check("4e la NOTICE est posée à côté du moteur", "NOTICE-photocraft.txt" in etape)
check("4f le dossier vendor n'est pas retiré par le nettoyage de l'arbre préparé",
      "\"vendor\"" not in ps.split("# ---- 1b.", 1)[-1].split("# ---- 2.", 1)[0])

# l'étape EXÉCUTÉE telle qu'écrite (Invoke-Expression du bloc) sur des arbres préparés jetables
ESSAI = r"""
param([string]$AppDir, [string]$stageApp, [string]$buildPy, [string]$Bloc)
$ErrorActionPreference = "Stop"
try { Invoke-Expression ([IO.File]::ReadAllText($Bloc)); "ETAPE:OK" } catch { "ETAPE:ARRET " + $_.Exception.Message }
"""
pwsh = shutil.which("powershell") or shutil.which("pwsh")
if pwsh and etape and DOSSIER.is_dir():
    T = pathlib.Path(tempfile.mkdtemp(prefix="dzt140b_"))
    try:
        (T / "essai.ps1").write_text(ESSAI, encoding="utf-8-sig")
        (T / "bloc.ps1").write_text(etape, encoding="utf-8-sig")

        def jouer(stage):
            p = subprocess.run([pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(T / "essai.ps1"), "-AppDir", str(RACINE),
                                "-stageApp", str(stage), "-buildPy", sys.executable, "-Bloc", str(T / "bloc.ps1")],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            return p.stdout + p.stderr
        faux = T / "faux" / "vendor" / "photocraft-0.3.0" / "photocraft-0.3.0-windows-x64-portable"
        faux.mkdir(parents=True)
        (faux / "photocraft-cli.exe").write_bytes(b"MZ pas le vrai moteur")
        out = jouer(T / "faux")
        check("4g exécutée : un moteur non conforme dans l'arbre préparé ARRÊTE le build", "ETAPE:ARRET" in out and "ETAPE:OK" not in out, out[-400:])
        vrai = T / "vrai" / "vendor" / "photocraft-0.3.0"
        shutil.copytree(DOSSIER, vrai, ignore=shutil.ignore_patterns("PhotoCraftData"))
        (vrai / "photocraft-0.3.0-windows-x64-portable" / "PhotoCraftData").mkdir()
        (vrai / "photocraft-0.3.0-windows-x64-portable" / "PhotoCraftData" / "preferences.json").write_text("{}")
        out = jouer(T / "vrai")
        check("4h exécutée : le vrai moteur passe ; NOTICE, manifeste et licences posés ; préférences du poste retirées",
              "ETAPE:OK" in out and (T / "vrai" / "vendor" / "NOTICE-photocraft.txt").is_file()
              and (T / "vrai" / "vendor" / "photocraft.json").is_file() and (T / "vrai" / "vendor" / "licences-photocraft" / "NOTICE").is_file()
              and not (vrai / "photocraft-0.3.0-windows-x64-portable" / "PhotoCraftData").exists(), out[-400:])
    finally:
        shutil.rmtree(T, ignore_errors=True)
else:
    check("4g l'étape est exécutable ici (PowerShell, moteur présent)", False, (pwsh, bool(etape), DOSSIER.is_dir()))

print("\n[5] NOTICE et fourniture")
notice = RACINE / "vendor" / "NOTICE-photocraft.txt"
nt = notice.read_text("utf-8") if notice.is_file() else ""
check("5a vendor/NOTICE-photocraft.txt existe", bool(nt))
for n in sorted(x for x in noms if x.startswith(("LICENSE", "OFL"))):
    check(f"5b NOTICE cite {n}", n in nt)
check("5c NOTICE : version, dépôt, double licence, icônes Lucide (ISC)", "0.3.0" in nt and "storytold/photocraft" in nt
      and "MIT" in nt and "Apache" in nt and "Lucide" in nt and "ISC" in nt)
LIC = RACINE / "vendor" / "licences-photocraft"
for n, empreinte in (("NOTICE", "Third-party material"), ("OFL-Inter.txt", "Open Font License"),
                     ("OFL-JetBrainsMono.txt", "Open Font License"), ("LICENSE-SCOWL.txt", "SCOWL"), ("LICENSE-lucide.txt", "ISC")):
    f = LIC / n
    check(f"5e licences-photocraft/{n} livré (requis par la NOTICE amont) et cité par la nôtre",
          f.is_file() and empreinte in f.read_text("utf-8") and f"licences-photocraft/{n}" in nt)
check("5f la NOTICE amont est reproduite TELLE QUELLE (ses mentions requises)",
      (LIC / "NOTICE").is_file() and (LIC / "NOTICE").read_text("utf-8").startswith("PhotoCraft\nCopyright (c) 2026 ArtCraft Team"))
check("5g la licence Lucide du moteur est celle des icônes de l'écran",
      (LIC / "LICENSE-lucide.txt").read_bytes().replace(b"\r\n", b"\n")
      == (RACINE / "frontend/photolab/icones/LICENSE-lucide.txt").read_bytes().replace(b"\r\n", b"\n"))
check("5h l'étape 4c pose aussi licences-photocraft/ dans l'arbre préparé", "licences-photocraft" in etape)
src = (RACINE / "scripts" / "vendor_photocraft.py").read_text("utf-8")
check("5d vendor_photocraft.py revérifie l'extraction contre le manifeste fichier par fichier",
      "comparer(" in src and "fichiers" in src)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
