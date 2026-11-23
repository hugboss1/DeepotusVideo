# -*- coding: utf-8 -*-
"""Écran calé sur la fenêtre (23/11/2026) — AUCUN écran de DeepotusVideo ne déborde à 1280×800.

Deux plaintes de l'utilisateur à l'origine de ce banc :
  1. sur un MacBook 13-14 pouces (navigateur, couche hébergée studio.deepotus.tech), le bas du menu latéral
     (WhatsApp, Réglages, choix de l'espace, FR/EN) est hors d'atteinte ;
  2. dans l'app bureau, les labs intégrés (Sprite Lab, 3D Studio, Tile Lab…) ont leurs barres du bas sous le bord.

Le banc lance l'application (données jetables, port tiré au hasard, jamais 8765) et un navigateur SANS FENÊTRE
(le moteur embarqué de motion code, Edge du PC en secours ; DEEPOTUS_NAVIGATEUR pour en imposer un), piloté par CDP.
À chaque taille, il ouvre la coque, clique chaque entrée du menu et chaque onglet (.dzCatTab, .svm-viewbtn), puis
ouvre chaque lab seul ; à chaque vue il passe scripts/qa/dz-debord.js dans la page ET dans ses iframes : tout
bouton, lien, champ, onglet ou iframe qu'on ne peut ni voir ni atteindre en défilant est une faute.

Tailles gardées : 1280×800 et 1440×900 (MacBook), 1366×768 (portable Windows), 1280×800 zoomé à 125 %
(vue CSS 1024×640). Le moindre élément hors d'atteinte rougit le banc.

Run (depuis backend/) : & $PY tests/test_ecran_cale.py [--captures <dossier>] [--tailles 1280x800,1440x900]
                                                       [--base http://127.0.0.1:8831  (une app déjà lancée)]"""
import base64, json, os, pathlib, re, shutil, socket, subprocess, sys, tempfile, threading, time, warnings

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
warnings.filterwarnings("ignore", category=DeprecationWarning)    # websockets : connect() hors « with », voulu
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcale_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ.pop(_k, None)
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
DETECTEUR = (RACINE / "scripts" / "qa" / "dz-debord.js").read_text(encoding="utf-8")

TAILLES = {                     # nom → (largeur CSS, hauteur CSS, facteur d'échelle)
    "1280x800": (1280, 800, 1),
    "1440x900": (1440, 900, 1),
    "1366x768": (1366, 768, 1),
    "1280x800@125": (1024, 640, 1.25),
}
LABS = ("atelier", "avatar", "cardforge", "etabli", "materialforge", "methodes", "photolab", "plateau",
        "spritelab", "studio3d", "tilelab", "vectorlab", "whatsapp")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  OK   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}" + (f"\n       {detail}" if detail else ""))


# ── l'application, sur un port libre ───────────────────────────────────────────────────────────────────────────────
def port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def lancer_app():
    import uvicorn
    from loguru import logger
    logger.remove()
    os.chdir(ICI.parent)
    from app.main import app
    port = port_libre()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=srv.run, daemon=True).start()
    fin = time.monotonic() + 60
    while not srv.started and time.monotonic() < fin:
        time.sleep(0.1)
    return srv, f"http://127.0.0.1:{port}"


# ── le navigateur sans fenêtre, par CDP ─────────────────────────────────────────────────────────────────────────────
class Navigateur:
    def __init__(self):
        from app.services.motion_code import trouver_moteur
        exe = trouver_moteur()
        if not exe:
            raise RuntimeError("aucun navigateur (moteur embarqué ni Edge) : poser DEEPOTUS_NAVIGATEUR")
        self.profil = tempfile.mkdtemp(prefix="dzcale_nav_")
        args = [exe, "--headless=new", f"--user-data-dir={self.profil}", "--remote-debugging-port=0",
                "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-sync",
                "--disable-background-networking", "--disable-component-update", "--hide-scrollbars",
                "--mute-audio", "--deny-permission-prompts",
                # aucune sortie vers Internet (polices Google, CDN) : seul 127.0.0.1 répond
                "--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=127.0.0.1;localhost",
                "about:blank"]
        self.p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        f = pathlib.Path(self.profil) / "DevToolsActivePort"
        fin = time.monotonic() + 30
        ws = None
        while time.monotonic() < fin and ws is None:
            try:
                l = f.read_text(encoding="utf-8").splitlines()
                if len(l) >= 2 and l[0].strip().isdigit():
                    ws = f"ws://127.0.0.1:{l[0].strip()}{l[1].strip()}"
            except OSError:
                pass
            time.sleep(0.05)
        if not ws:
            raise RuntimeError("le navigateur n'a pas ouvert son port de débogage")
        from websockets.sync.client import connect
        self.ws = connect(ws, max_size=256 * 1024 * 1024, open_timeout=10)
        self.n = 0
        self.sid = None
        cible = self.appel("Target.createTarget", {"url": "about:blank"}, sid=False)["targetId"]
        self.sid = self.appel("Target.attachToTarget", {"targetId": cible, "flatten": True}, sid=False)["sessionId"]
        self.appel("Page.enable")
        self.appel("Runtime.enable")

    def appel(self, methode, params=None, sid=True, delai=60):
        self.n += 1
        i = self.n
        m = {"id": i, "method": methode, "params": params or {}}
        if sid and self.sid:
            m["sessionId"] = self.sid
        self.ws.send(json.dumps(m))
        fin = time.monotonic() + delai
        while time.monotonic() < fin:
            try:
                r = json.loads(self.ws.recv(timeout=max(0.1, fin - time.monotonic())))
            except TimeoutError:
                break
            if r.get("id") == i:
                if "error" in r:
                    raise RuntimeError(f"{methode} : {r['error'].get('message')}")
                return r.get("result") or {}
        raise RuntimeError(f"{methode} : pas de réponse en {delai} s")

    def js(self, expr, attendre=True):
        r = self.appel("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": attendre})
        if "exceptionDetails" in r:
            raise RuntimeError("JS : " + str(r["exceptionDetails"].get("exception", {}).get("description", ""))[:300])
        return r.get("result", {}).get("value")

    def taille(self, w, h, dsf):
        self.appel("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": dsf,
                                                          "mobile": False})

    def aller(self, url):
        self.appel("Page.navigate", {"url": url})

    def attendre(self, cond, delai=40.0):
        fin = time.monotonic() + delai
        while time.monotonic() < fin:
            try:
                if self.js(f"!!({cond})"):
                    return True
            except RuntimeError:
                pass
            time.sleep(0.25)
        return False

    def capture(self, chemin):
        r = self.appel("Page.captureScreenshot", {"format": "png"})
        pathlib.Path(chemin).write_bytes(base64.b64decode(r["data"]))

    def fermer(self):
        try:
            self.ws.close()
        except Exception:  # noqa: BLE001
            pass
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(self.p.pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            self.p.kill()
            self.p.wait(timeout=10)
        except Exception:  # noqa: BLE001
            pass
        for _ in range(40):
            shutil.rmtree(self.profil, ignore_errors=True)
            if not os.path.exists(self.profil):
                break
            time.sleep(0.1)


# La mesure : le détecteur dans la page, puis dans chaque iframe de même origine (récursif)
MESURE = """(() => {
  const res = [];
  function run(win, ou) {
    let v;
    try { v = win.eval(window.__dzSrc); } catch (e) { return; }
    for (const h of v.hors) res.push(Object.assign({ ou }, h));
    for (const f of win.document.querySelectorAll('iframe')) {
      try {
        if (f.contentDocument && f.getBoundingClientRect().width > 1)
          run(f.contentWindow, ou + ' › ' + (f.getAttribute('src') || 'iframe'));
      } catch (e) { /* autre origine */ }
    }
  }
  run(window, 'coque');
  return res;
})()"""


def poser_detecteur(nav):
    nav.js("window.__dzSrc = " + json.dumps(DETECTEUR) + "; true")


def nommer(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:40]


def mesurer_vue(nav, nom, vue, captures, fautes):
    poser_detecteur(nav)
    hors = nav.js(MESURE) or []
    if captures:
        nav.capture(captures / f"{nommer(nom)}--{nommer(vue)}.png")
    for x in hors:
        fautes.append((nom, vue, x))
    check(f"[{nom}] {vue} : tout est atteignable", not hors,
          "; ".join(f"{x['ou']} : {x['el']} ({x['cause']})" for x in hors[:6])
          + (f" … +{len(hors) - 6}" if len(hors) > 6 else ""))


PRETE = ("document.querySelectorAll('.dzNavItem').length > 5 && (!document.getElementById('dz-splash') || "
         "document.getElementById('dz-splash').classList.contains('dz-hide'))")


def ouvrir_coque(nav, base, accueil_vu):
    """La coque chargée ; `accueil_vu` False = l'assistant de premier lancement s'affiche par-dessus."""
    nav.aller(base + "/")
    nav.attendre("document.readyState !== 'loading'", 30)
    nav.js("(() => { try { localStorage." + ("setItem('dz_onboarded', '1')" if accueil_vu
                                            else "removeItem('dz_onboarded')") + " } catch (e) {} return true })()")
    nav.aller(base + "/")
    pret = nav.attendre(PRETE, 60)
    time.sleep(1.2)
    return pret


def mesurer_taille(nav, base, nom, w, h, dsf, captures, fautes):
    nav.taille(w, h, dsf)
    # ── l'assistant de premier lancement (sa fenêtre doit tenir, elle aussi) ──
    pret = ouvrir_coque(nav, base, accueil_vu=False)
    check(f"[{nom}] la coque s'ouvre", pret)
    if not pret:
        return
    mesurer_vue(nav, nom, "Accueil (premier lancement)", captures, fautes)
    # ── la coque : chaque entrée du menu, chaque onglet ──
    if not ouvrir_coque(nav, base, accueil_vu=True):
        check(f"[{nom}] la coque se rouvre, accueil passé", False)
        return
    entrees = nav.js("[...document.querySelectorAll('.dzNavItem')].map(b => b.innerText.split('\\n')[0].trim())")
    for i, entree in enumerate(entrees):
        nav.js(f"document.querySelectorAll('.dzNavItem')[{i}].click(); true")
        time.sleep(1.4)
        onglets = nav.js("[...document.querySelectorAll('main .dzCatTab, main .svm-viewbtn')]"
                         ".filter(b => b.getBoundingClientRect().width > 0).map(b => b.innerText.trim())") or []
        vues = [(entree, None)] + [(f"{entree} › {o}", j) for j, o in enumerate(onglets)]
        for vue, j in vues:
            if j is not None:
                nav.js("(() => { const b = [...document.querySelectorAll('main .dzCatTab, main .svm-viewbtn')]"
                       ".filter(b => b.getBoundingClientRect().width > 0)[" + str(j) + "];"
                       " if (b) b.click(); return true })()")
                time.sleep(2.2)
            mesurer_vue(nav, nom, vue, captures, fautes)
    # ── chaque lab ouvert seul ──
    for lab in LABS:
        nav.aller(f"{base}/{lab}/")
        nav.attendre("document.readyState === 'complete'", 30)
        time.sleep(1.5)
        poser_detecteur(nav)
        hors = nav.js(MESURE) or []
        if captures:
            nav.capture(captures / f"{nommer(nom)}--lab-{lab}.png")
        for x in hors:
            fautes.append((nom, "/" + lab + "/", x))
        check(f"[{nom}] /{lab}/ seul : tout est atteignable", not hors,
              "; ".join(f"{x['el']} ({x['cause']})" for x in hors[:6]))


def statique():
    """Ce qui se vérifie sans navigateur : la règle commune est liée par la coque (juste avant dz-bords) et suit la charte."""
    print("[S] la règle commune « écran calé »")
    src = RACINE / "frontend" / "shared" / "dz-cale.css"
    dist = RACINE / "frontend" / "dist" / "shared" / "dz-cale.css"
    check("frontend/shared/dz-cale.css existe", src.is_file())
    check("copie identique dans frontend/dist/shared/", dist.is_file() and dist.read_bytes() == src.read_bytes())
    css = src.read_text(encoding="utf-8") if src.is_file() else ""
    check("aucun border-radius autre que 0 (angles vifs, DESIGN.md)",
          all(v.strip().startswith(("0", "var(--radius")) for v in css.split("border-radius:")[1:]))
    # les commentaires et les sélecteurs d'attribut ([style*="100vh"]) peuvent citer 100vh, pas une déclaration
    code = re.sub(r"\[[^\]]*\]", "", re.sub(r"/\*.*?\*/", "", css, flags=re.S))
    check("aucun 100vh dans la règle (100dvh : la hauteur VISIBLE)", "100vh" not in code)
    coque = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    liens = [l for l in coque.splitlines() if 'rel="stylesheet"' in l and "/shared/" in l]
    # dz-bords.css reste la DERNIÈRE (test_charte_bords) ; la règle commune passe juste avant, après tout le reste
    check("la coque lie /shared/dz-cale.css une fois, juste avant dz-bords.css (la dernière)",
          len(liens) >= 2 and "dz-cale.css" in liens[-2] and "dz-bords.css" in liens[-1]
          and sum("dz-cale.css" in l for l in liens) == 1, liens[-2:])


def principal():
    args = sys.argv[1:]
    captures = None
    tailles = list(TAILLES)
    base = None
    if "--captures" in args:
        captures = pathlib.Path(args[args.index("--captures") + 1]).resolve()
        captures.mkdir(parents=True, exist_ok=True)
    if "--tailles" in args:
        tailles = args[args.index("--tailles") + 1].split(",")
    if "--base" in args:
        base = args[args.index("--base") + 1].rstrip("/")
    if "--sans-statique" not in args:
        statique()
    srv = None
    if not base:
        srv, base = lancer_app()
        check("l'application répond", srv.started)
    nav = Navigateur()
    fautes = []
    try:
        for nom in tailles:
            w, h, dsf = TAILLES[nom]
            print(f"[{nom}] vue CSS {w}×{h}, échelle {dsf}")
            mesurer_taille(nav, base, nom, w, h, dsf, captures, fautes)
    finally:
        nav.fermer()
        if srv:
            srv.should_exit = True
        shutil.rmtree(_tmp, ignore_errors=True)
    if captures:
        (captures / "fautes.json").write_text(json.dumps([{"taille": t, "vue": v, **x} for t, v, x in fautes],
                                                         ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{ok} OK, {fail} FAIL")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    principal()
