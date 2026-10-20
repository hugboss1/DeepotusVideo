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
check("1c la provenance du manifeste est dite (archive vérifiée)",
      M["binaire"]["sha256"][:12] in json.dumps(M.get("fichiers_source", "")), M.get("fichiers_source"))
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
        _v = M["version"]   # t251 : le dossier suit la version épinglée
        faux = T / "faux" / "vendor" / f"photocraft-{_v}" / f"photocraft-{_v}-windows-x64-portable"
        faux.mkdir(parents=True)
        (faux / "photocraft-cli.exe").write_bytes(b"MZ pas le vrai moteur")
        out = jouer(T / "faux")
        check("4g exécutée : un moteur non conforme dans l'arbre préparé ARRÊTE le build", "ETAPE:ARRET" in out and "ETAPE:OK" not in out, out[-400:])
        vrai = T / "vrai" / "vendor" / f"photocraft-{_v}"
        shutil.copytree(DOSSIER, vrai, ignore=shutil.ignore_patterns("PhotoCraftData"))
        (vrai / f"photocraft-{_v}-windows-x64-portable" / "PhotoCraftData").mkdir()
        (vrai / f"photocraft-{_v}-windows-x64-portable" / "PhotoCraftData" / "preferences.json").write_text("{}")
        vieux = T / "vrai" / "vendor" / "photocraft-0.3.0"           # t259 : un moteur d'avant laissé sur le poste de build
        (vieux / "photocraft-0.3.0-windows-x64-portable").mkdir(parents=True)
        (vieux / "photocraft-0.3.0-windows-x64-portable" / "photocraft-cli.exe").write_bytes(b"MZ ancien")
        out = jouer(T / "vrai")
        check("4h exécutée : le vrai moteur passe ; NOTICE, manifeste et licences posés ; préférences du poste retirées",
              "ETAPE:OK" in out and (T / "vrai" / "vendor" / "NOTICE-photocraft.txt").is_file()
              and (T / "vrai" / "vendor" / "photocraft.json").is_file() and (T / "vrai" / "vendor" / "licences-photocraft" / "NOTICE").is_file()
              and not (vrai / f"photocraft-{_v}-windows-x64-portable" / "PhotoCraftData").exists(), out[-400:])
        check("4i exécutée (t259) : un moteur d'une AUTRE version laissé sur le poste de build ne part pas chez l'acheteur",
              not vieux.exists() and vrai.is_dir() and (T / "vrai" / "vendor" / "photocraft.json").is_file(), out[-400:])
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
check("5c NOTICE : version, dépôt, double licence, icônes Lucide (ISC)", M["version"] in nt and "storytold/photocraft" in nt
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

print("\n[6] t259 : attributions de photocraft 0.10.0 (ATTRIBUTION amont et licences des matériaux du moteur)")
# Empreintes git (blob) des fichiers du tag v0.10.0 (API GitHub, 21/10/2026) ; COPYING de xorg/app/rgb (GitLab freedesktop,
# blob 7c566482, commit fb06ee0b). Reproduits TELS QUELS : le texte livré doit être celui de l'amont (fins de ligne LF).
AMONT = {"ATTRIBUTION.md": ("1ae19efa6621ced81f8db17e8b0834ddcb5d6b66", "Every non-code asset"),
         "LICENSE-translations.txt": ("93a609f9463c9c718814fc942c3ec56ead5ec2e3", "MIT OR Apache-2.0"),
         "LICENSE-solarized.txt": ("1124be212d80160156bd321f76fd459f03a47b1c", "Ethan Schoonover"),
         "LICENSE-noun-magnetic-lasso.txt": ("7fcb546dd27dcd08a1a7a89be87fbafe66ca1324", "CC BY 3.0"),
         "LICENSE-symmetry-axes.txt": ("2232ec82fb8ee9c917f8cb4a00ac7c5fc0591394", "@shorbank"),
         "COPYING-xorg-rgb.txt": ("7c5664827a8dfdbc54da51ef9f620348105b87e1", "The Open Group")}


def blob(f):
    b = f.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


for n, (empreinte, marque) in AMONT.items():
    f = LIC / n
    check(f"6a licences-photocraft/{n} livré tel que publié (blob {empreinte[:8]})",
          f.is_file() and blob(f) == empreinte and marque in f.read_text("utf-8"), blob(f) if f.is_file() else "absent")
    check(f"6b notre NOTICE cite licences-photocraft/{n}", f"licences-photocraft/{n}" in nt)
check("6c NOTICE : traductions (fr.tsv), rgb.txt X11, palette Solarized, icône Noun Project (CC BY 3.0) nommées",
      all(m in nt for m in ("fr.tsv", "rgb.txt", "Solarized", "Noun Project", "CC BY 3.0", "Lil' Seal")), nt[-600:])
entete = lambda f: (RACINE / "scripts" / f).read_text("utf-8").split("\n", 1)[0]
check("6d les en-têtes des scripts de fourniture ne nomment plus une version périmée du moteur",
      "0.3.0" not in entete("vendor_photocraft.py") and "0.3.0" not in entete("verifier_vendor.py"),
      (entete("vendor_photocraft.py"), entete("verifier_vendor.py")))
check("6e l'étape 4c retire du dossier préparé tout photocraft-* d'une autre version que l'épinglée",
      "photocraft-*" in etape and "$pcVersion" in etape)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
