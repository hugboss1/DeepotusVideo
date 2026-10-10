# -*- coding: utf-8 -*-
"""Bibliothèque (10/10/2026) — l'écran tient dans la fenêtre à 1 366 et 1 440 px.

Mesure d'origine (puppeteer, 1 440 × 900) : `<main>` faisait 1 389 px à partir de x=232, ~180 px au-delà du bord
droit. La coque est une grille `auto 1fr` dont la piste `1fr` ne descend pas sous le min-content de `<main>` ; ce
min-content était celui de la barre d'outils de la Bibliothèque, rangée flex SANS retour à la ligne de 1 353 px. La
recherche, le tri, les imports, les pastilles fal/heygen/voix/version de l'en-tête et, puce Audio, les filtres
« Récents » / « Tous » du tiroir Sons étaient coupés à droite. Après le maillon scripts/patch_bundle_dzbiblio.py, la
barre passe à la ligne.

  [1] le maillon est posé une fois : marqueur sur la barre, `flexWrap:"wrap"`, plus de barre sans retour à la ligne.
  [2] la chaîne reste saine : node --check, CRLF homogène (octets), aucun `.bak_dzbiblio`, double application
      refusée, dzgbar/dzsched/version sondés intacts, lecture en octets, `avant_dzbiblio` rend le bundle d'avant
      octet pour octet, et `avant_dzgbar` le défait d'abord.
  [3] au navigateur (backend jetable sur un port libre, aucune clé, Chrome sans tête) : à 1 366 × 768 et 1 440 × 900,
      puce Images puis puce Audio, documentElement.scrollWidth <= innerWidth ET bord droit de `<main>` <= innerWidth
      (la coque a overflow:hidden : scrollWidth seul ne voit pas le débordement), chaque enfant de la barre, chaque
      pastille de l'en-tête et (Audio) « Récents » / « Tous » du tiroir Sons dans la fenêtre.
Run : & $PY tests/test_bibliotheque_debordement.py   (depuis backend/)
"""
import json, os, pathlib, shutil, socket, subprocess, sys, tempfile, time, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
PATCHER = ROOT / "scripts" / "patch_bundle_dzbiblio.py"
QA = ROOT / "scripts" / "qa" / "qa-bibliotheque-largeur.js"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
ok = fail = 0
MARQUEUR = '"data-dz-biblio-barre":"1"'
ANCIENNE = ('r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:12},children:[r.jsx("div",{className:"display",'
            'style:{fontSize:16,color:"var(--ink-strong)"},children:dzT("commun.objet.bibliotheque")})')


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
check("1.1 marqueur posé une fois", s.count(MARQUEUR) == 1, s.count(MARQUEUR))
i = s.find(MARQUEUR)
check("1.2 la barre de la Bibliothèque passe à la ligne (flexWrap)", 'flexWrap:"wrap"' in s[max(0, i - 120):i],
      s[max(0, i - 160):i])
check("1.3 plus de barre de la Bibliothèque sans retour à la ligne", ANCIENNE not in s)

print("[2] la chaîne")
node = shutil.which("node")
r = subprocess.run([node, "--check", str(BUNDLE)], capture_output=True, text=True) if node else None
check("2.1 bundle node --check", r is not None and r.returncode == 0, r.stderr[-300:] if r else "node absent")
check("2.2 CRLF homogène (octets)", raw.count(b"\r\n") > 15000 and raw.count(b"\n") == raw.count(b"\r\n"))
check("2.3 aucun .bak_dzbiblio laissé", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzbiblio")).exists())
r = subprocess.run([sys.executable, str(PATCHER), "--check"], capture_output=True, text=True, cwd=str(ROOT))
check("2.4 double application refusée", r.returncode != 0 and "deja present" in (r.stdout + r.stderr), r.stdout + r.stderr)
src = PATCHER.read_text(encoding="utf-8")
check("2.5 le maillon lit le bundle en octets", "read_bytes()" in src and "read_text(" not in src.split('"""', 2)[2])
check("2.6 version (v2.8.0 x4), dzsched et dzgbar intacts", s.count("v2.8.0") == 4
      and s.count('"data-dz-debord":"1"') == 1 and s.count('"data-dz-gbar":"1"') == 1)
try:
    import _i18n_l1_aide as _aide
    import patch_bundle_dzbiblio as _m
    avant = _aide.avant_dzbiblio(s)
    refait = _m.appliquer(avant)
    check("2.7 avant_dzbiblio défait le maillon, et le réappliquer rend le bundle octet pour octet",
          MARQUEUR not in avant and ANCIENNE in avant and refait == s)
    check("2.8 avant_dzgbar défait dzbiblio d'abord", MARQUEUR not in _aide.avant_dzgbar(s))
except Exception as e:  # noqa: BLE001
    check("2.7 avant_dzbiblio défait le maillon", False, repr(e))

print("[3] au navigateur, Images puis Audio")
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
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzbiblio_banc_"))
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
            r = subprocess.run([node, str(QA), base, "1366x768", "1440x900"], capture_output=True, text=True,
                               encoding="utf-8", timeout=240, env=dict(os.environ, NODE_PATH=str(mods)))
            try:
                mes = json.loads(r.stdout)
            except Exception:  # noqa: BLE001
                mes = {"erreurs": ["sortie illisible : " + (r.stdout + r.stderr)[-300:]], "mesures": []}
            check("3.1 aucune erreur de page", not mes["erreurs"], mes["erreurs"])
            for t in mes["mesures"]:
                w, v, iw = t["largeur"], t["vue"], t["innerWidth"]
                check(f"3.2 {v} {w} px : documentElement.scrollWidth <= innerWidth", t["scrollWidth"] <= iw,
                      (t["scrollWidth"], iw))
                check(f"3.3 {v} {w} px : <main> dans la fenêtre", t["main"][1] <= iw + 0.5, t["main"])
                check(f"3.4 {v} {w} px : barre d'outils marquée, chaque enfant dans la fenêtre",
                      t["barre_marquee"] and bool(t["barre"]) and all(e["droite"] <= iw + 0.5 for e in t["barre"]),
                      t["barre"])
                check(f"3.5 {v} {w} px : les 4 pastilles de l'en-tête dans la fenêtre",
                      len(t["pastilles"]) == 4 and all(e["droite"] <= iw + 0.5 for e in t["pastilles"]), t["pastilles"])
                if v == "Audio":
                    check(f"3.6 Audio {w} px : « Récents » et « Tous » du tiroir Sons dans la fenêtre",
                          any(e["texte"].startswith("Récents") for e in t["filtres"])
                          and any(e["texte"] == "Tous" for e in t["filtres"])
                          and all(e["droite"] <= iw + 0.5 for e in t["filtres"]), t["filtres"])
            vues = [(t["vue"], t["largeur"]) for t in mes["mesures"]]
            check("3.7 les quatre mesures faites",
                  vues == [("Images", 1366), ("Images", 1440), ("Audio", 1366), ("Audio", 1440)], vues)
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
