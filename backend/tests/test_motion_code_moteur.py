# -*- coding: utf-8 -*-
"""Motion code sans Edge (19/10/2026) : le rendu motion code (t238) part d'un moteur sans fenêtre ÉPINGLÉ, livré avec
l'application — chrome-headless-shell 155.0.8059.84 (Chrome for Testing), allégé aux langues fr + en-US — ; Edge du
PC ne sert plus qu'en SECOURS (décision de l'utilisateur, 19/10). Relevé : docs/superpowers/specs/
2026-10-19-motion-code-moteur-embarque.md. Ce que ce banc garde :
  [R] la résolution : DEEPOTUS_NAVIGATEUR (banc) > DEEPOTUS_EDGE (compatibilité) > moteur EMBARQUÉ > Edge du PC ;
      une variable qui pointe vers un fichier absent est ignorée ; rien → Arret « moteur », message FR / EN qui dit de
      réinstaller, AVANT tout profil jetable ;
  [S] le bac à sable n'a pas bougé : mêmes drapeaux de lancement que t238, mêmes délais, même CSP ;
  [V] la livraison : manifeste vendor/chrome-headless-shell.json (URL officielle CfT, sha256, langues, chaque fichier),
      script de récupération (empreinte fausse → rien extrait, entrée hors dossier refusée, langues filtrées),
      .gitignore, NOTICE, build de l'installeur (étape 4d) ; l'application ne télécharge jamais rien ;
  [E] (si le moteur est fourni sur ce poste) l'arbre est conforme au manifeste, et un VRAI rendu passe par lui sans
      aucune variable d'environnement : MP4 conforme, aucun processus du bac à sable vivant, aucun profil restant.
Run (depuis backend/) : & $PY tests/test_motion_code_moteur.py"""
import hashlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmcmot_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("DEEPOTUS_NAVIGATEUR", "DEEPOTUS_EDGE"):
    os.environ.pop(_k, None)
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(RACINE / "scripts"))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:400]}")


from app.services import motion_code as MC                          # noqa: E402

MANIFESTE = RACINE / "vendor" / "chrome-headless-shell.json"
VERSION = "155.0.8059.84"

# ── [R] résolution ────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] résolution du moteur")
check("R0 trouver_moteur et moteur_embarque existent", hasattr(MC, "trouver_moteur") and hasattr(MC, "moteur_embarque"))
if not hasattr(MC, "trouver_moteur"):
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1)
check("R1 version épinglée dans le module = 155.0.8059.84", getattr(MC, "NAVIGATEUR_VERSION", None) == VERSION,
      getattr(MC, "NAVIGATEUR_VERSION", None))
attendu = (RACINE / "vendor" / f"chrome-headless-shell-{VERSION}" / "chrome-headless-shell-win64"
           / "chrome-headless-shell.exe")
check("R2 moteur embarqué cherché sous <app>/vendor/chrome-headless-shell-<version>/",
      pathlib.Path(MC.moteur_embarque()).resolve() == attendu.resolve(), MC.moteur_embarque())

faux = _tmp / "faux"
emb = faux / "app" / "vendor" / f"chrome-headless-shell-{VERSION}" / "chrome-headless-shell-win64" / \
    "chrome-headless-shell.exe"
pf = faux / "pf"
edge = pf / "Microsoft" / "Edge" / "Application" / "msedge.exe"
autre = faux / "autre" / "navigateur.exe"
for f in (emb, edge, autre):
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"MZ")
ENV0 = {k: os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA", "PATH",
                                         "DEEPOTUS_NAVIGATEUR", "DEEPOTUS_EDGE")}
RAC0 = MC.RACINE_APP


def poser(racine=None, edge_ok=True, **env):
    """Un poste fictif : racine de l'application, Program Files (Edge ou pas), PATH vide, variables du banc."""
    MC.RACINE_APP = pathlib.Path(racine) if racine else faux / "vide"
    for k in ("PROGRAMFILES(X86)", "LOCALAPPDATA", "DEEPOTUS_NAVIGATEUR", "DEEPOTUS_EDGE"):
        os.environ.pop(k, None)
    os.environ["PROGRAMFILES"] = str(pf if edge_ok else faux / "sans_edge")
    os.environ["PATH"] = str(faux / "rien")
    for k, v in env.items():
        os.environ[k] = str(v)


def norm(p):
    return pathlib.Path(p).resolve() if p else None


try:
    poser(faux / "app")
    check("R3 embarqué présent ET Edge installé → l'embarqué d'abord", norm(MC.trouver_moteur()) == emb.resolve(),
          MC.trouver_moteur())
    poser(faux / "vide")
    check("R4 embarqué absent, Edge installé → Edge en secours", norm(MC.trouver_moteur()) == edge.resolve(),
          MC.trouver_moteur())
    poser(faux / "vide", edge_ok=False)
    check("R5 ni embarqué ni Edge → None", MC.trouver_moteur() is None, MC.trouver_moteur())
    p0 = sorted(pathlib.Path(tempfile.gettempdir()).glob("dz_motion_code_*"))
    msgs = {}
    for lg in ("fr", "en"):
        try:
            MC.rendre_page("<html><body><script>window.dzFrame=function(t){}</script></body></html>",
                           _tmp / f"x_{lg}.mp4", W=64, H=64, fps=12, duree_s=1, langue=lg)
            msgs[lg] = None
        except MC.Arret as e:
            msgs[lg] = (e.code, str(e))
    check("R6 rien → Arret « moteur » (FR : réinstaller ; EN : reinstall)",
          msgs.get("fr") and msgs["fr"][0] == "moteur" and "réinstall" in msgs["fr"][1].lower()
          and msgs.get("en") and msgs["en"][0] == "moteur" and "reinstall" in msgs["en"][1].lower(), msgs)
    check("R7 … et aucun profil jetable créé, aucune sortie",
          sorted(pathlib.Path(tempfile.gettempdir()).glob("dz_motion_code_*")) == p0
          and not (_tmp / "x_fr.mp4").exists())
    check("R8 messages FR / EN distincts et sans « Microsoft Edge est introuvable » seul",
          "moteur" in MC.MESSAGES and MC.MESSAGES["moteur"]["fr"] != MC.MESSAGES["moteur"]["en"]
          and "edge" not in MC.MESSAGES, list(MC.MESSAGES))
    poser(faux / "app", DEEPOTUS_NAVIGATEUR=autre)
    check("R9 DEEPOTUS_NAVIGATEUR l'emporte sur l'embarqué (bancs)", norm(MC.trouver_moteur()) == autre.resolve(),
          MC.trouver_moteur())
    poser(faux / "app", DEEPOTUS_EDGE=autre)
    check("R10 DEEPOTUS_EDGE reste lu (compatibilité des bancs t238)", norm(MC.trouver_moteur()) == autre.resolve(),
          MC.trouver_moteur())
    poser(faux / "app", DEEPOTUS_NAVIGATEUR=autre, DEEPOTUS_EDGE=edge)
    check("R11 DEEPOTUS_NAVIGATEUR avant DEEPOTUS_EDGE", norm(MC.trouver_moteur()) == autre.resolve(),
          MC.trouver_moteur())
    poser(faux / "app", DEEPOTUS_NAVIGATEUR=faux / "absent.exe", DEEPOTUS_EDGE=faux / "absent2.exe")
    check("R12 variable vers un fichier absent → ignorée, l'embarqué", norm(MC.trouver_moteur()) == emb.resolve(),
          MC.trouver_moteur())
    poser(faux / "app")
    check("R13 trouver_edge ne rend QUE Edge (jamais l'embarqué)", norm(MC.trouver_edge()) == edge.resolve(),
          MC.trouver_edge())
    poser(faux / "app", edge_ok=False)
    p0 = sorted(pathlib.Path(tempfile.gettempdir()).glob("dz_motion_code_*"))
    try:
        MC.rendre_page("<html><body><script>window.dzFrame=function(t){}</script></body></html>", _tmp / "y.mp4",
                       W=64, H=64, fps=12, duree_s=1, langue="fr")
        r = None
    except MC.Arret as e:
        r = (e.code, str(e))
    except Exception as e:  # noqa: BLE001
        r = ("brute", repr(e))
    check("R14 rendre_page part bien de l'embarqué : embarqué abîmé → arrêt « navigateur » propre, profil effacé",
          r and r[0] == "navigateur" and sorted(pathlib.Path(tempfile.gettempdir()).glob("dz_motion_code_*")) == p0, r)
finally:
    MC.RACINE_APP = RAC0
    for k, v in ENV0.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

# ── [S] le bac à sable n'a pas bougé ──────────────────────────────────────────────────────────────────────────────
print("[S] bac à sable inchangé")
ARGS_T238 = ["--headless=new", "--remote-debugging-port=0", "--no-first-run", "--no-default-browser-check",
             "--disable-extensions", "--disable-sync", "--disable-background-networking", "--disable-component-update",
             "--disable-default-apps",
             "--disable-features=Translate,MediaRouter,OptimizationHints,AutofillServerCommunication",
             "--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=<-loopback>", "--block-new-web-contents",
             "--deny-permission-prompts", "--mute-audio", "--hide-scrollbars", "about:blank"]
vus = []


class _FauxP:
    pid = 0

    def poll(self):
        return 1


_popen = subprocess.Popen
MC.subprocess.Popen = lambda args, **kw: (vus.append(list(args)), _FauxP())[1]
try:
    MC._lancer_edge(str(autre), str(_tmp / "profil"), 0.2)
finally:
    MC.subprocess.Popen = _popen
a = vus[0] if vus else []
check("S1 mêmes drapeaux de lancement que t238 (profil jetable compris)",
      a[:1] == [str(autre)] and [x for x in a[1:] if not x.startswith("--user-data-dir=")] == ARGS_T238
      and f"--user-data-dir={_tmp / 'profil'}" in a, a)
check("S2 mêmes bornes : 120 s, 20 s par commande, CSP du plan",
      MC.DELAI == 120 and MC.DELAI_APPEL == 20 and MC.CSP == "default-src 'none'; script-src 'unsafe-inline'; "
      "style-src 'unsafe-inline'; img-src data:")

# ── [V] la livraison ──────────────────────────────────────────────────────────────────────────────────────────────
print("[V] livraison épinglée")
m = json.loads(MANIFESTE.read_text("utf-8")) if MANIFESTE.is_file() else {}
b = m.get("binaire") or {}
check("V1 manifeste : version, URL officielle CfT win64, sha256, taille",
      m.get("version") == VERSION and b.get("url") == "https://storage.googleapis.com/chrome-for-testing-public/"
      f"{VERSION}/win64/chrome-headless-shell-win64.zip"
      and b.get("sha256") == "5ca590a4968864e219ea25ccd134597ef8898a733a4698c07fc3e8b2c480fef4"
      and b.get("taille") == 123681250, m.get("version"))
check("V2 manifeste : dossier et exe d'accord avec le module",
      (RACINE / b.get("dossier", "?") / b.get("exe", "?")).resolve() == attendu.resolve(),
      (b.get("dossier"), b.get("exe")))
fich = m.get("fichiers") or {}
loc = [k for k in fich if "/locales/" in k]
check("V3 manifeste : langues fr + en-US seulement, chaque fichier gardé (exe, licence) épinglé",
      m.get("langues") == ["en-US", "fr"] and len(loc) == 8
      and all(re.search(r"/locales/(en-US|fr)(_[A-Z]+)?\.pak$", k) for k in loc)
      and "chrome-headless-shell-win64/chrome-headless-shell.exe" in fich
      and "chrome-headless-shell-win64/LICENSE.headless_shell" in fich
      and all(re.fullmatch(r"[0-9a-f]{64}", v.get("sha256", "")) and v.get("taille", 0) > 0 for v in fich.values()),
      (m.get("langues"), len(loc), len(fich)))

try:
    import vendor_chrome_headless_shell as VC                       # noqa: E402
except ImportError as e:
    VC = None
    check("V4 scripts/vendor_chrome_headless_shell.py existe", False, e)
if VC:
    z = _tmp / "a.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for n in ("chrome-headless-shell-win64/chrome-headless-shell.exe", "chrome-headless-shell-win64/LICENSE.headless_shell",
                  "chrome-headless-shell-win64/locales/de.pak", "chrome-headless-shell-win64/locales/fr.pak",
                  "chrome-headless-shell-win64/locales/fr_FEMININE.pak", "chrome-headless-shell-win64/locales/en-US.pak",
                  "chrome-headless-shell-win64/locales/en-GB.pak", "chrome-headless-shell-win64/locales/fr-CA.pak"):
            zf.writestr(n, n)
    octets = z.read_bytes()
    sha = hashlib.sha256(octets).hexdigest()
    try:
        VC.verifier(z, "0" * 64, len(octets))
        r = "accepté"
    except VC.EmpreinteFausse as e:
        r = str(e)
    check("V4 sha256 faux → EmpreinteFausse", r != "accepté", r)
    try:
        VC.verifier(z, sha, len(octets) + 1)
        r = "accepté"
    except VC.EmpreinteFausse as e:
        r = str(e)
    check("V5 taille fausse → EmpreinteFausse", r != "accepté", r)
    cible = _tmp / "x"
    exe = VC.extraire(z, cible, ["en-US", "fr"])
    gardes = sorted(p.name for p in (cible / "chrome-headless-shell-win64" / "locales").iterdir())
    check("V6 extraction : seules les langues gardées (en-US, fr et leurs variantes de genre)",
          gardes == ["en-US.pak", "fr.pak", "fr_FEMININE.pak"] and pathlib.Path(exe).name == "chrome-headless-shell.exe",
          gardes)
    zm = _tmp / "m.zip"
    with zipfile.ZipFile(zm, "w") as zf:
        zf.writestr("chrome-headless-shell-win64/chrome-headless-shell.exe", "x")
        zf.writestr("../evil.txt", "x")
    cm = _tmp / "cm"
    try:
        VC.extraire(zm, cm, ["fr"])
        r = "accepté"
    except VC.EmpreinteFausse as e:
        r = str(e)
    check("V7 entrée hors du dossier → refusée, rien extrait", r != "accepté" and not cm.exists()
          and not (_tmp / "evil.txt").exists(), r)
    reel = RACINE / b.get("dossier", "vendor/__absent__")
    avant = reel.stat().st_mtime_ns if reel.exists() else None
    import contextlib, io
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = VC.main(["--archive", str(z)])
    check("V8 main sur une archive à la mauvaise empreinte → code ≠ 0, arrêt À L'EMPREINTE, dossier du moteur intouché",
          rc != 0 and "rien n'est extrait" in err.getvalue() and not reel.with_name(reel.name + ".tmp").exists()
          and (reel.stat().st_mtime_ns if reel.exists() else None) == avant, (rc, err.getvalue()))
    petit = _tmp / "petit"
    (petit / "chrome-headless-shell-win64").mkdir(parents=True)
    (petit / "chrome-headless-shell-win64" / "intrus.dll").write_bytes(b"x")
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = VC.main(["--verifier", str(petit)])
    check("V13 --verifier sur un arbre non conforme (fichiers manquants, DLL en trop) → code ≠ 0, écarts listés",
          rc != 0 and "intrus.dll : en trop" in err.getvalue() and "manquant" in err.getvalue(), (rc, err.getvalue()[:300]))
    (petit / "chrome-headless-shell-win64" / "chrome-headless-shell.exe").write_bytes(b"MZ pas un PE")
    try:
        ec = VC.controler(m, petit)
    except Exception as e:  # noqa: BLE001
        ec = ["TRACE " + repr(e)]
    check("V14 exe illisible (pas un PE) → un écart nommé, jamais une trace",
          any("pas un exécutable Windows lisible" in e for e in ec) and not any(e.startswith("TRACE") for e in ec), ec[-2:])
    # 21/10 : Chrome écrit chrome_debug.log à l'exécution (relevé dans l'app installée) ; ce n'est pas un écart,
    # à toute profondeur, mais un autre fichier .log reste « en trop »
    jt = _tmp / "journaux"
    (jt / "chrome-headless-shell-win64" / "sous").mkdir(parents=True)
    (jt / "chrome-headless-shell-win64" / "a.txt").write_bytes(b"a")
    mj = {"fichiers": {"chrome-headless-shell-win64/a.txt": {"taille": 1, "sha256": hashlib.sha256(b"a").hexdigest()}},
          "binaire": {"exe": "chrome-headless-shell-win64/absent.exe"}}
    for d in (jt, jt / "chrome-headless-shell-win64", jt / "chrome-headless-shell-win64" / "sous"):
        (d / "chrome_debug.log").write_text("[1021/120000.000:ERROR] journal d'exécution")
    ec = VC.controler(mj, jt)
    check("V15 chrome_debug.log (journal d'exécution, à toute profondeur) n'est pas un écart", ec == [], ec)
    check("V16 --ecrire n'épingle jamais un journal d'exécution",
          list(VC.empreintes_moteur(jt)) == ["chrome-headless-shell-win64/a.txt"], list(VC.empreintes_moteur(jt)))
    (jt / "chrome-headless-shell-win64" / "intrus.log").write_text("x")
    ec = VC.controler(mj, jt)
    check("V17 un autre .log reste « en trop » (seuls les journaux de Chrome sont ignorés)",
          ec == ["chrome-headless-shell-win64/intrus.log : en trop (absent de l'archive officielle)"], ec)
gi = (RACINE / ".gitignore").read_text("utf-8")
check("V9 .gitignore : vendor/chrome-headless-shell-*/ jamais versionné", "vendor/chrome-headless-shell-*/" in gi)
notice = RACINE / "vendor" / "NOTICE-chrome-headless-shell.txt"
nt = notice.read_text("utf-8") if notice.is_file() else ""
check("V10 NOTICE : version, BSD, LICENSE.headless_shell, empreinte, Google",
      VERSION in nt and "BSD" in nt and "LICENSE.headless_shell" in nt and b.get("sha256", "?") in nt and "Google" in nt)
ps = (RACINE / "scripts" / "build-installer.ps1").read_text("utf-8")
check("V11 build : appelle le script, vérifie l'arbre préparé, copie manifeste + NOTICE",
      "vendor_chrome_headless_shell.py" in ps and "--verifier" in ps and "chrome-headless-shell.json" in ps
      and "NOTICE-chrome-headless-shell.txt" in ps, "")
src = (RACINE / "backend" / "app" / "services" / "motion_code.py").read_text("utf-8")
check("V12 l'application ne télécharge jamais le moteur (aucun appel réseau dans motion_code ; httpx n'y sert qu'à "
      "reconnaître les exceptions d'un appel au moteur de texte)",
      not re.search(r"\b(urllib|requests)\b|httpx\.(get|post|put|stream|request|Client|AsyncClient)\b", src))

# ── [E] le vrai moteur embarqué, s'il est fourni sur ce poste ─────────────────────────────────────────────────────
print("[E] moteur embarqué réel")
if not attendu.is_file():
    check("E0 moteur fourni sur ce poste (python scripts/vendor_chrome_headless_shell.py)", False, attendu)
else:
    rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "vendor_chrome_headless_shell.py"), "--verifier"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("E1 arbre fourni conforme au manifeste, aucun runtime Visual C++ requis", rc.returncode == 0,
          (rc.stdout or "")[-300:] + (rc.stderr or "")[-600:])
    check("E2 sans variable : trouver_moteur() = l'embarqué", norm(MC.trouver_moteur()) == attendu.resolve(),
          MC.trouver_moteur())
    PAGE = ('<html><body style="margin:0;background:#000"><div id="c" style="position:absolute;left:0;top:0;width:20px;'
            'height:20px;background:#f00"></div><script>window.dzFrame=function(t){document.getElementById("c").style'
            '.left=(t*100)+"px"}</script></body></html>')
    p0 = sorted(pathlib.Path(tempfile.gettempdir()).glob("dz_motion_code_*"))
    out = _tmp / "e.mp4"
    try:
        r = MC.rendre_page(PAGE, out, W=320, H=180, fps=12, duree_s=2)
    except MC.Arret as e:
        r = {"erreur": str(e)}
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                         "stream=width,height,nb_read_frames,r_frame_rate", "-of", "json", str(out)],
                        capture_output=True, text=True) if out.is_file() else None
    st = (json.loads(pr.stdout).get("streams") or [{}])[0] if pr and pr.returncode == 0 else {}
    check("E3 vrai rendu par l'embarqué : MP4 320×180, 12 i/s, 24 images",
          r.get("images") == 24 and st.get("width") == 320 and st.get("height") == 180
          and st.get("nb_read_frames") == "24" and st.get("r_frame_rate") == "12/1", (r, st))
    vivants = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "@(Get-CimInstance Win32_Process -Filter \"Name='chrome-headless-shell.exe'\" | "
                              "Where-Object { $_.CommandLine -like '*dz_motion_code_*' }).Count"],
                             capture_output=True, text=True).stdout.strip()
    check("E4 aucun processus du bac à sable vivant, aucun profil restant",
          vivants == "0" and sorted(pathlib.Path(tempfile.gettempdir()).glob("dz_motion_code_*")) == p0,
          (vivants, p0))

# ── [I] l'étape 4d du build EXÉCUTÉE sur un arbre préparé jetable où Chrome a laissé ses journaux (21/10) ─────────────
print("[I] étape 4d du build")
i4d, i5 = ps.find("# ---- 4d. chrome-headless-shell"), ps.find("# ---- 5. Compile with Inno Setup")
bloc4d = ps[i4d:i5] if 0 < i4d < i5 else ""
check("I1 l'étape 4d retire chrome_debug.log de l'arbre préparé", "chrome_debug.log" in bloc4d and "Remove-Item" in bloc4d)
pwsh = shutil.which("powershell") or shutil.which("pwsh")
if pwsh and bloc4d and attendu.is_file():
    T = pathlib.Path(tempfile.mkdtemp(prefix="dzmc4d_"))
    try:
        (T / "essai.ps1").write_text(
            'param([string]$AppDir, [string]$stageApp, [string]$buildPy, [string]$Bloc)\n$ErrorActionPreference = "Stop"\n'
            'try { Invoke-Expression ([IO.File]::ReadAllText($Bloc)); "ETAPE:OK" } catch { "ETAPE:ARRET " + $_.Exception.Message }\n',
            encoding="utf-8-sig")
        (T / "bloc.ps1").write_text(bloc4d, encoding="utf-8-sig")
        stage = T / "app" / "vendor" / f"chrome-headless-shell-{VERSION}"
        shutil.copytree(attendu.parents[1], stage, ignore=shutil.ignore_patterns("chrome_debug.log"))
        journaux = [stage / "chrome_debug.log", stage / "chrome-headless-shell-win64" / "chrome_debug.log"]
        for j in journaux:
            j.write_text("journal d'exécution du poste de build")
        p = subprocess.run([pwsh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(T / "essai.ps1"), "-AppDir",
                            str(RACINE), "-stageApp", str(T / "app"), "-buildPy", sys.executable, "-Bloc", str(T / "bloc.ps1")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        out = p.stdout + p.stderr
        check("I2 exécutée : l'arbre préparé avec des journaux de Chrome passe, et aucun journal ne part chez l'acheteur",
              "ETAPE:OK" in out and not any(j.exists() for j in journaux) and not list(stage.rglob("chrome_debug.log"))
              and (stage / "chrome-headless-shell-win64" / "chrome-headless-shell.exe").is_file(), out[-500:])
    finally:
        shutil.rmtree(T, ignore_errors=True)
else:
    check("I2 l'étape 4d est exécutable ici (PowerShell, moteur présent)", False, (pwsh, bool(bloc4d), attendu))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
