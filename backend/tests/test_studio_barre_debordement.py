# -*- coding: utf-8 -*-
"""Studio (10/10/2026) — la barre du graphe reste dans sa colonne, inspecteur déplié.

Mesure d'origine (puppeteer, inspecteur déplié) : la barre du graphe (Nouveau, Enregistrer, Recette, Importer, ouvrir
un graphe, 9:16, Aperçu, ≈ $, Exécuter, Enregistrer le layout, Exporter) est une rangée flex SANS retour à la ligne
dans la colonne centrale `1fr` (608 px à 1 440, 848 px à 1 680). À 1 440 : Aperçu x=1320, Exécuter x=1472 alors que
l'inspecteur commence à x=1100 — elementFromPoint au centre de ces boutons rend l'inspecteur. Après le maillon
scripts/patch_bundle_dzgbar.py, la barre passe à la ligne et le bandeau d'état se place sous sa hauteur réelle.

  [1] le maillon est posé une fois : marqueur, barre `flexWrap:"wrap"` en `minHeight:48` (plus de `height:48`),
      mesure de hauteur `__dzGbarRef` → `--dz-gbar-h`, bandeau d'état en `top:calc(var(--dz-gbar-h…) + 8px)`.
  [2] la chaîne reste saine : node --check, CRLF homogène (octets), aucun `.bak_dzgbar`, double application refusée,
      dzsched et version sondés intacts, lecture en octets, `avant_dzgbar` rend le bundle d'avant octet pour octet.
  [3] au navigateur (backend jetable sur un port libre, aucune clé, Chrome sans tête) : à 1 440 × 900 et 1 680 × 945,
      inspecteur DÉPLIÉ, chaque enfant de la barre est dans la colonne centrale et au premier plan (Aperçu et
      Exécuter compris), et `--dz-gbar-h` suit la hauteur de la barre.
Run : & $PY tests/test_studio_barre_debordement.py   (depuis backend/)
"""
import json, os, pathlib, shutil, socket, subprocess, sys, tempfile, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
PATCHER = ROOT / "scripts" / "patch_bundle_dzgbar.py"
QA = ROOT / "scripts" / "qa" / "qa-studio-barre.js"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}  {str(detail)[:400]}")


raw = BUNDLE.read_bytes()
s = raw.decode("utf-8-sig")
print("[1] le maillon")
check("1.1 marqueur posé une fois", s.count('"data-dz-gbar":"1"') == 1, s.count('"data-dz-gbar":"1"'))
i = s.find('"data-dz-gbar":"1"')
barre = s[max(0, i - 400):i]
check("1.2 la barre passe à la ligne (flexWrap) en minHeight:48, plus de height:48",
      'flexWrap:"wrap"' in barre and "minHeight:48" in barre and "height:48," not in barre.replace("minHeight:48", ""),
      barre[-300:])
check("1.3 la barre mesure sa hauteur (ref __dzGbarRef → --dz-gbar-h)",
      "ref:__dzGbarRef" in s[i - 40:i + 40] and s.count("function __dzGbarRef(") == 1
      and '"--dz-gbar-h"' in s[s.find("function __dzGbarRef("):s.find("function __dzGbarRef(") + 500])
check("1.4 le bandeau d'état se place sous la barre (plus de top:56)",
      s.count('top:"calc(var(--dz-gbar-h, 48px) + 8px)",left:16,right:16,zIndex:5') == 1
      and 'position:"absolute",top:56,left:16,right:16,zIndex:5' not in s)

print("[2] la chaîne")
node = shutil.which("node")
r = subprocess.run([node, "--check", str(BUNDLE)], capture_output=True, text=True) if node else None
check("2.1 bundle node --check", r is not None and r.returncode == 0, r.stderr[-300:] if r else "node absent")
check("2.2 CRLF homogène (octets)", raw.count(b"\r\n") > 15000 and raw.count(b"\n") == raw.count(b"\r\n"))
check("2.3 aucun .bak_dzgbar laissé", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzgbar")).exists())
r = subprocess.run([sys.executable, str(PATCHER), "--check"], capture_output=True, text=True, cwd=str(ROOT))
check("2.4 double application refusée", r.returncode != 0 and "deja present" in (r.stdout + r.stderr), r.stdout + r.stderr)
src = PATCHER.read_text(encoding="utf-8")
check("2.5 le maillon lit le bundle en octets", "read_bytes()" in src and "read_text(" not in src.split('"""', 2)[2])
check("2.6 version intact (v2.8.0 x4) et dzsched intact", s.count("v2.8.0") == 4 and s.count('"data-dz-debord":"1"') == 1)
try:
    import _i18n_l1_aide as _aide
    import patch_bundle_dzgbar as _m
    avant = _aide.avant_dzgbar(s)
    refait = _m.appliquer(avant)
    # dzbiblio, posé APRÈS dzgbar, est défait par avant_dzgbar : la référence est donc le bundle sans dzbiblio
    check("2.7 avant_dzgbar défait le maillon, et le réappliquer rend le bundle (sans dzbiblio) octet pour octet",
          '"data-dz-gbar":"1"' not in avant and "__dzGbarRef" not in avant and refait == _aide.avant_dzbiblio(s))
except Exception as e:  # noqa: BLE001
    check("2.7 avant_dzgbar défait le maillon", False, repr(e))

print("[3] au navigateur, inspecteur déplié")
chrome = os.environ.get("DZ_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
mods = next((p for p in (ROOT / "scripts" / "qa" / "node_modules",
                         ROOT.parent.parent.parent / "scripts" / "qa" / "node_modules")
             if (p / "puppeteer-core").is_dir()), None)
if not (node and mods and pathlib.Path(chrome).is_file()):
    check("3.0 outillage (node, puppeteer-core sous scripts/qa/node_modules, Chrome)", False,
          f"node={node} puppeteer={mods} chrome={chrome}")
else:
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        port = so.getsockname()[1]
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzgbar_banc_"))
    env = dict(os.environ, DEEPOTUS_DATA_DIR=str(d), DATABASE_URL=f"sqlite+aiosqlite:///{(d / 't.db').as_posix()}",
               IMAGES_FOLDER=str(d / "images"), OUTPUTS_FOLDER=str(d / "outputs"))
    for k in ("FAL_KEY", "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
              "MESHY_API_KEY", "GEMINI_API_KEY", "FIGMA_TOKEN", "TELEGRAM_BOT_TOKEN"):
        env[k] = ""
    lanceur = ("import sys,uvicorn; sys.path.insert(0, r'%s'); uvicorn.run('app.main:app', host='127.0.0.1', port=%d, "
               "log_level='warning')" % (ROOT / "backend", port))
    srv = subprocess.Popen([sys.executable, "-c", lanceur], cwd=str(ROOT / "backend"), env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}"
        pret = False
        for _ in range(120):
            try:
                pret = urllib.request.urlopen(base + "/", timeout=2).status == 200
                if pret:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        check("3.0 backend jetable prêt", pret, base)
        if pret:
            r = subprocess.run([node, str(QA), base, "1440x900", "1680x945"], capture_output=True, text=True,
                               encoding="utf-8", timeout=240, env=dict(os.environ, NODE_PATH=str(mods)))
            try:
                mes = json.loads(r.stdout)
            except Exception:  # noqa: BLE001
                mes = {"erreurs": ["sortie illisible : " + (r.stdout + r.stderr)[-300:]], "tailles": []}
            check("3.1 aucune erreur de page", not mes["erreurs"], mes["erreurs"])
            for t in mes["tailles"]:
                w = t["largeur"]
                g, dr = t["centre"]
                hors = [e["texte"] or e["tag"] for e in t["enfants"] if e["gauche"] < g - 0.5 or e["droite"] > dr + 0.5]
                caches = [e["texte"] or e["tag"] for e in t["enfants"] if not e["premier_plan"]]
                check(f"3.2 {w} px : inspecteur déplié, à droite de la colonne centrale",
                      t["inspecteur_deplie"] and abs(t["inspecteur"][0] - dr) < 1, t["inspecteur"])
                check(f"3.3 {w} px : chaque enfant de la barre dans la colonne centrale", not hors, hors)
                check(f"3.4 {w} px : chaque enfant de la barre au premier plan", not caches, caches)
                for nom in ("Aperçu", "Exécuter"):
                    e = next((e for e in t["enfants"] if e["texte"] == nom), None)
                    check(f"3.5 {w} px : « {nom} » présent, dans la colonne et au premier plan",
                          e is not None and e["premier_plan"] and e["droite"] <= dr + 0.5, e)
                hb = t["barre"]["bas"] - t["barre"]["haut"]
                check(f"3.6 {w} px : --dz-gbar-h suit la hauteur de la barre ({hb:.0f} px)",
                      t["var_barre"].endswith("px") and abs(float(t["var_barre"][:-2]) - hb) <= 1, t["var_barre"])
            check("3.7 les deux largeurs mesurées", [t["largeur"] for t in mes["tailles"]] == [1440, 1680],
                  [t["largeur"] for t in mes["tailles"]])
    finally:
        enfants = []
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command",
                                  f"(Get-CimInstance Win32_Process | Where-Object {{ $_.ParentProcessId -eq {srv.pid} }}).ProcessId"],
                                 capture_output=True, text=True, timeout=30).stdout
            enfants = [int(x) for x in out.split() if x.strip().isdigit()]
        except Exception:  # noqa: BLE001
            pass
        srv.kill()
        for pid in enfants:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        shutil.rmtree(d, ignore_errors=True)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
