# -*- coding: utf-8 -*-
"""t238 (lot « Studio : Animation », option B validée le 19/10/2026) — Motion code : le moteur écrit une page animée,
rendue en MP4 par un navigateur sans fenêtre, image par image, dans un bac à sable strict.

Plan docs/superpowers/plans/2026-10-17-studio-animation.md (t238). Zéro dépense : un FAUX OLLAMA écoute sur 127.0.0.1
(port tiré au hasard, jamais 8765) ; un FAUX HÔTE note toute requête — une page ne doit JAMAIS l'atteindre. Le VRAI
navigateur du bac à sable (le moteur embarqué, chrome-headless-shell épinglé ; Edge du PC en secours) rend les pages
(le banc est rouge sans lui). Ce que ce banc garde :
  [M] le module et ses bornes (CSP exacte, 10 Mo, 120 s, 12-60 i/s, 1-60 s) ;
  [C] le contrôle statique : page saine (SVG avec espace de noms) admise ; fetch, XHR, WebSocket, import(), Worker,
      top.location, location.href, window.open, iframe / link / object, image http, meta refresh, > 10 Mo REFUSÉS ;
  [E] l'enveloppe : la CSP posée AVANT la page, le cadre W×H ; l'extraction d'une réponse en bloc ```html``` ;
  [B] le rendu : MP4 conforme (W×H, cadence, nombre d'images), horloge VIRTUELLE mesurée dans les images (dzFrame,
      requestAnimationFrame + performance.now, setTimeout, animation CSS, Math.random déterministe) ;
  [P] pages piégées : refus AVANT tout lancement (aucun profil créé) ; navigation et fenêtre construites à l'exécution
      → arrêt ; fetch déguisé → aucune requête reçue ; boucle infinie au chargement et dans dzFrame → arrêt PROPRE
      (aucun navigateur du bac à sable vivant, profil effacé, aucune sortie partielle) ;
  [W] l'écriture : appel au moteur choisi en texte (pas en JSON), plafond vérifié AVANT la requête, contrat de la page
      et direction (style, consigne) dans le prompt système ; page refusée → seconde tentative qui dit pourquoi, puis
      repli ; sans moteur / non configuré → repli sans requête ; plafond dépassé → 402 sans requête ;
  [R] la page de repli : écrite par nous, admise par le contrôle, rendue, ses textes à leur place au bon moment ;
  [H] les routes : écrire (200, 400 traduit, 404), lire (JSON, jamais un document ; id hors motif → 404), rendre (job
      FAIT → MP4 ; page piégée → job en échec avec le message FR / EN), 403 depuis un autre appareil ;
  [A] /api/animate : `base` {source_kind:"motion_code"} rendue au format, à la cadence et à la durée de l'Animation ;
  [L] chaque message d'erreur neuf est traduit (scripts/i18n_l10_erreurs.py --check vert).
Run (depuis backend/) : & $PY tests/test_motion_code.py"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmcode_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for _k in ("GEMINI_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER",
           "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_k, None)
(_tmp / ".env").write_text("# fichier de l'utilisateur\n", encoding="utf-8")
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi import HTTPException                                   # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:400]}")


print("[M] module")
try:
    from app.services import motion_code as MC                      # noqa: E402
except ImportError as e:
    check("M0 app.services.motion_code existe", False, e)
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1)
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import cles_a_chaud as CAC                        # noqa: E402
from app.services import plafonds as PLAF                           # noqa: E402
from app.services import motion_biblio as MB                        # noqa: E402
from PIL import Image                                               # noqa: E402

CAC.appliquer({"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "ANTHROPIC_API_KEY": "", "OLLAMA_MODEL": "",
               "SUMMARIZER_PROVIDER": "", "PLANNER_PROVIDER": ""})
check("M1 CSP exacte du plan", MC.CSP == "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
      "img-src data:", MC.CSP)
check("M2 bornes : 10 Mo, 120 s, 12-60 i/s, 1-60 s", MC.MAX_PAGE == 10 * 1024 * 1024 and MC.DELAI == 120
      and MC.FPS == (12, 60) and MC.DUREE == (1, 60))
check("M3 bornes() : format inconnu → 9:16, fps et durée bornés",
      MC.bornes("x", 500, 900) == ("9:16", 1080, 1920, 60, 60.0) and MC.bornes("16:9", 2, -3)[3:] == (12, 1.0)
      and MC.bornes("1:1", float("nan"), None)[3:] == (30, 8.0), [MC.bornes("x", 500, 900), MC.bornes("16:9", 2, -3)])
EDGE = MC.trouver_moteur()          # le moteur embarqué, ou DEEPOTUS_NAVIGATEUR / DEEPOTUS_EDGE, ou Edge en secours
check("M4 navigateur du bac à sable trouvé sur ce poste", bool(EDGE), EDGE)
NOM_MOTEUR = pathlib.Path(EDGE or "msedge.exe").name

# ── [C] contrôle statique ─────────────────────────────────────────────────────────────────────────────────────────
print("[C] contrôle statique")
SAINE = ('<html><body><svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="5" height="5"/></svg>'
         '<script>var ns="http://www.w3.org/2000/svg";window.dzFrame=function(t){document.title=t}</script></body></html>')
check("C1 page saine (espace de noms SVG compris) admise", MC.controler(SAINE) == [], MC.controler(SAINE))
PIEGES = {
    "fetch": ("<script>fetch('/x')</script>", "reseau"),
    "xhr": ("<script>new XMLHttpRequest()</script>", "reseau"),
    "ws": ("<script>new WebSocket('ws://a')</script>", "reseau"),
    "import": ("<script>import('./m.js')</script>", "reseau"),
    "worker": ("<script>new Worker('w.js')</script>", "reseau"),
    "beacon": ("<script>navigator.sendBeacon('/b')</script>", "reseau"),
    "top": ("<script>top.location='x'</script>", "navigation"),
    "href": ("<script>location.href='x'</script>", "navigation"),
    "open": ("<script>window.open('x')</script>", "navigation"),
    "refresh": ('<meta http-equiv="refresh" content="0;url=x">', "navigation"),
    "lien": ('<a href="x">x</a>', "navigation"),
    "iframe": ("<iframe srcdoc='x'></iframe>", "cadre"),
    "link": ('<link rel="stylesheet" href="s.css">', "cadre"),
    "object": ('<object data="x"></object>', "cadre"),
    "img_http": ('<img src="https://exemple.org/a.png">', "ressource_externe"),
    "font": ("<style>@font-face{src:url(//fonts.exemple.org/a.woff)}</style>", "ressource_externe"),
    "file": ('<img src="file:///C:/Windows/win.ini">', "ressource_externe"),
}
for nom, (h, code) in PIEGES.items():
    check(f"C2 {nom} → refus « {code} »", code in MC.controler("<html>" + h + "</html>"), MC.controler(h))
check("C3 rien sans balise → « vide »", MC.controler("du texte") == ["vide"] and MC.controler(None) == ["vide"])
GROS = "<html><!--" + "x" * (MC.MAX_PAGE + 1) + "--></html>"
check("C4 plus de 10 Mo → « taille »", MC.controler(GROS) == ["taille"])
check("C5 motifs traduits", MC.details_refus(["reseau", "navigation"], "fr") == "appel réseau, navigation"
      and MC.details_refus(["reseau"], "en") == "network call")

# ── [E] enveloppe, extraction ─────────────────────────────────────────────────────────────────────────────────────
print("[E] enveloppe")
env = MC.envelopper("<!DOCTYPE html><html><head><title>t</title></head><body>B</body></html>", 640, 360)
i_csp, i_page = env.find('http-equiv="Content-Security-Policy"'), env.find("<html>")
check("E1 la CSP précède la page, doctype de la page retiré", 0 < i_csp < i_page and env.count("<!doctype") == 1
      and "<!DOCTYPE" not in env and MC.CSP in env, env[:300])
check("E2 cadre 640×360 sans marge", "width:640px;height:360px;overflow:hidden" in env and "margin:0" in env)
rep_md = "Voici la page :\n```html\n<!doctype html><html><body>OK</body></html>\n```\nBonne chance."
check("E3 extraction d'un bloc ```html```", MC.extraire_page(rep_md) == "<!doctype html><html><body>OK</body></html>",
      MC.extraire_page(rep_md))
check("E4 extraction sans bloc : du premier < au dernier >", MC.extraire_page("bla <p>x</p> fin") == "<p>x</p>"
      and MC.extraire_page(42) == "" and MC.extraire_page("rien") == "")

# ── outils de mesure ──────────────────────────────────────────────────────────────────────────────────────────────
OUT = _tmp / "rendus"
OUT.mkdir()


def sonde(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_frames,codec_name,pix_fmt", "-of", "json", str(f)],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)["streams"][0]
    except (ValueError, KeyError, IndexError):
        return {}


def image(f, k):
    """L'image k (0 = la première) du MP4, en RGB."""
    p = OUT / f"_img_{pathlib.Path(f).stem}_{k}.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-vf", f"select=eq(n\\,{k})", "-vframes", "1",
                    str(p)], check=True)
    return Image.open(p).convert("RGB")


def centre_rouge(im):
    """Le centre (x, y) des pixels nettement rouges, sinon None."""
    px, W, H = im.load(), im.width, im.height
    xs, ys = [], []
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            r, g, b = px[x, y]
            if r > 180 and g < 80 and b < 80:
                xs.append(x)
                ys.append(y)
    return (sum(xs) / len(xs), sum(ys) / len(ys)) if xs else None


def profils():
    return sorted(p.name for p in pathlib.Path(tempfile.gettempdir()).glob("dz_motion_code_*"))


def edges_du_bac():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "@(Get-CimInstance Win32_Process -Filter \"Name='%s'\" | Where-Object { $_.CommandLine "
                        "-like '*dz_motion_code_*' }).Count" % NOM_MOTEUR], capture_output=True, text=True)
    try:
        return int((r.stdout or "0").strip() or 0)
    except ValueError:
        return -1


# ── [B] le rendu ──────────────────────────────────────────────────────────────────────────────────────────────────
print("[B] rendu")
P0 = profils()
HORLOGE_PAGE = """<html><body style="background:#000">
<div id="a" style="position:absolute;top:20px;left:0;width:20px;height:20px;background:#f00"></div>
<div id="c" style="position:absolute;top:120px;left:0;width:20px;height:20px;background:#0f0"></div>
<div id="d" style="position:absolute;top:220px;left:0;width:20px;height:20px;background:#00f;animation:k 2s linear forwards"></div>
<style>@keyframes k{from{left:0}to{left:400px}}</style>
<script>
var t0=performance.now(),R=Math.random(),late=0;
setTimeout(function(){late=1},1000);
function boucle(ts){document.getElementById("c").style.left=Math.round((performance.now()-t0)/5)+"px";requestAnimationFrame(boucle)}
requestAnimationFrame(boucle);
window.dzFrame=function(t){document.getElementById("a").style.left=Math.round(t*200)+"px";
document.title=[R,late,Date.now()].join("|")};
</script></body></html>"""
f1 = OUT / "horloge.mp4"
t = time.time()
try:
    r1 = MC.rendre_page(HORLOGE_PAGE, f1, W=640, H=360, fps=25, duree_s=2)
except Exception as e:  # noqa: BLE001
    r1 = {"erreur": repr(e)}
dt1 = time.time() - t
s1 = sonde(f1)
check("B1 MP4 conforme : 640×360, 25 i/s, 50 images, h264 yuv420p",
      s1.get("width") == 640 and s1.get("height") == 360 and s1.get("r_frame_rate") == "25/1"
      and s1.get("nb_read_frames") == "50" and s1.get("codec_name") == "h264" and s1.get("pix_fmt") == "yuv420p", s1)
check("B2 compte rendu : images, cadence, durée", r1.get("images") == 50 and r1.get("fps") == 25
      and r1.get("duree_s") == 2.0 and r1.get("erreurs_js") == 0, r1)
check("B3 2 s de vidéo rendues en moins de 60 s", dt1 < 60, dt1)
if f1.is_file():
    pos = {k: image(f1, k) for k in (0, 25, 49)}
    # dzFrame : a.left = round(t*200) → 0, 200, 392 (centre = left + 10)
    ca = {k: centre_rouge(im) for k, im in pos.items()}
    check("B4 dzFrame(t) suit l'horloge virtuelle (t = k/25)", all(ca[k] and abs(ca[k][0] - (round(k / 25 * 200) + 10)) <= 3
                                                                for k in ca), ca)

    def centre(im, canal):
        px = im.load()
        xs = [x for y in range(100, 300, 2) for x in range(0, im.width) if
              (canal == "g" and px[x, y][1] > 180 and px[x, y][0] < 80) or (canal == "b" and px[x, y][2] > 180
                                                                              and px[x, y][0] < 80 and px[x, y][1] < 80)]
        return sum(xs) / len(xs) if xs else None
    cg = {k: centre(im, "g") for k, im in pos.items()}
    check("B5 requestAnimationFrame + performance.now virtuels (1 s → 200 px)",
          all(cg[k] is not None and abs(cg[k] - (round(k * 40 / 5) + 10)) <= 3 for k in cg), cg)
    cb = {k: centre(im, "b") for k, im in pos.items()}
    check("B6 animation CSS calée sur l'horloge (2 s linéaire : 0 → 400 px)",
          all(cb[k] is not None and abs(cb[k] - (400 * k / 25 / 2 + 10)) <= 4 for k in cb), cb)
check("B7 profil jetable effacé, aucun navigateur du bac à sable vivant", profils() == P0 and edges_du_bac() == 0,
      (profils(), edges_du_bac()))
# déterminisme : Math.random, setTimeout et Date.now virtuels (lus dans le titre au dernier appel)
TITRE = HORLOGE_PAGE.replace('document.title=[R,late,Date.now()].join("|")',
                             'document.title=[R,late,Date.now()].join("|");'
                             'document.body.setAttribute("data-t",document.title)')
TITRE = TITRE.replace("</script>", 'window.dzFrame0=window.dzFrame;window.dzFrame=function(t){window.dzFrame0(t);'
                      'var ok=late===(t>=1?1:0)&&Date.now()===1760832000000+Math.floor(t*1000+1e-6);'
                      'document.getElementById("a").style.background=ok?"#f00":"#ff0"};</script>', 1)
f2 = OUT / "determinisme.mp4"
MC.rendre_page(TITRE, f2, W=640, H=360, fps=12, duree_s=2)
check("B8 setTimeout et Date.now virtuels à chaque image (le carré reste rouge)",
      all(centre_rouge(image(f2, k)) for k in (0, 11, 12, 23)))
COMPTE = ("<html><body><script>var n=0,m=0;setInterval(function(){n++},100);setTimeout(function(){m=1},1500);"
          "window.dzFrame=function(t){var ok=n===Math.floor(t*10+1e-6)&&m===(t>=1.5-1e-9?1:0);"
          "document.body.style.background=ok?'#f00':'#0f0'}</script></body></html>")
f2b = OUT / "minuteries.mp4"
MC.rendre_page(COMPTE, f2b, W=640, H=360, fps=60, duree_s=2)
check("B8b setInterval / setTimeout tirés sur le temps VIRTUEL (rendu plus lent que le réel : un compte réel diverge)",
      all(centre_rouge(image(f2b, k)) for k in (0, 30, 59, 60, 89, 90, 119)))


def mulberry32(graine):
    """La suite de l'horloge virtuelle (mulberry32, graine fixe), recalculée ici en entiers 32 bits."""
    s = graine
    def m(a, b):
        return ((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF)) & 0xFFFFFFFF
    while True:
        s = (s + 0x6D2B79F5) & 0xFFFFFFFF
        t = m(s ^ (s >> 15), 1 | s)
        t = ((t + m(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF) ^ t
        yield ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296


ATTENDU = next(mulberry32(238))
RAND = ("<html><body><script>var v=Math.random();window.dzFrame=function(){document.body.style.background="
        "Math.abs(v-%r)<1e-12?'#f00':'#0f0'}</script></body></html>" % ATTENDU)
f3 = OUT / "rand.mp4"
MC.rendre_page(RAND, f3, W=64, H=64, fps=12, duree_s=1)
check("B9 Math.random à graine fixe : la première valeur est celle de mulberry32(238)",
      centre_rouge(image(f3, 0)) is not None, ATTENDU)

# ── [P] pages piégées ─────────────────────────────────────────────────────────────────────────────────────────────
print("[P] pages piégées")
HITS = []


class _Hote(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        HITS.append(self.path)
        self.send_response(200)
        self.end_headers()

    do_POST = do_GET


_h = ThreadingHTTPServer(("127.0.0.1", 0), _Hote)
HPORT = _h.server_address[1]
threading.Thread(target=_h.serve_forever, daemon=True).start()


def piege(h, delai=20.0, duree=1.0):
    f = OUT / f"piege_{len(os.listdir(OUT))}.mp4"
    t = time.time()
    try:
        MC.rendre_page(h, f, W=320, H=240, fps=12, duree_s=duree, delai=delai)
        return None, time.time() - t, f
    except MC.Arret as e:
        return e, time.time() - t, f


e, dt, f = piege(f"<html><script>fetch('http://127.0.0.1:{HPORT}/statique')</script></html>")
check("P1 fetch écrit en clair → REFUS avant tout lancement (aucun profil créé, rien reçu)",
      e is not None and e.code == "refus" and dt < 2 and profils() == P0 and not HITS and not f.exists(), (e, dt))
e, dt, f = piege("<html><script>top.location='http://127.0.0.1:%d/top'</script></html>" % HPORT)
check("P2 top.location → REFUS (navigation)", e is not None and e.code == "refus" and "navigation" in str(e) and not HITS,
      e)
e, dt, f = piege("<html><script>var u='ht'+'tp:/'+'/127.0.0.1:%d/nav';window['to'+'p']['loc'+'ation']=u</script></html>"
                 % HPORT)
check("P3 navigation construite à l'exécution → ARRÊT « navigation », rien reçu, pas de sortie",
      e is not None and e.code == "navigation" and not HITS and not f.exists() and dt < 30, (e, dt, HITS))
e, dt, f = piege("<html><script>window.dzFrame=function(t){if(t>0.2)window['op'+'en']('ab'+'out:blank')}</script></html>")
check("P4 fenêtre ouverte à l'exécution → ARRÊT « fenetre »", e is not None and e.code == "fenetre", e)
e, dt, f = piege(("<html><body><script>var R='?';window['fet'+'ch']('ht'+'tp:/'+'/127.0.0.1:%d/fetch').then("
                  "function(){R='ok'},function(){R='ko'});var x=new window['XMLHttp'+'Request']();"
                  "x['op'+'en']('GET','ht'+'tp:/'+'/127.0.0.1:%d/xhr');try{x.send()}catch(_e){}"
                  "var im=new Image();im.src='ht'+'tp:/'+'/127.0.0.1:%d/img';"
                  "window.dzFrame=function(){document.body.style.background=R==='ko'?'#f00':'#00f'}</script></body></html>")
                 % (HPORT, HPORT, HPORT), duree=1.0)
time.sleep(0.5)
check("P5 fetch / XHR / image déguisés : AUCUNE requête reçue, l'appel échoue dans la page (CSP), le rendu continue",
      e is None and not HITS and f.is_file() and centre_rouge(image(f, 11)) is not None, (e, HITS))
P_avant = profils()
e, dt, f = piege("<html><script>while(true){}</script></html>", delai=6)
# 19/10 (PR #390) : ce banc fixe un budget TOTAL de 6 s, sous les 20 s par commande : c'est lui qui borne → « delai_total »
# (le message dit le budget) ; en usage réel le budget vaut au moins 120 s et une commande figée donne « delai ».
check("P6 boucle infinie au chargement → ARRÊT PROPRE « delai » / « delai_total » (≈ le délai, pas plus)",
      e is not None and e.code in ("delai", "delai_total") and 5.5 <= dt < 20 and "6 s" in str(e), (e, dt))
check("P7 … Edge du bac à sable tué, profil effacé, aucune sortie partielle",
      edges_du_bac() == 0 and profils() == P_avant and not f.exists(), (edges_du_bac(), profils()))
e, dt, f = piege("<html><script>window.dzFrame=function(t){if(t>0.4)for(;;){}}</script></html>", delai=6)
check("P8 boucle infinie dans dzFrame → ARRÊT « delai » / « delai_total » à l'image fautive, propre",
      e is not None and e.code in ("delai", "delai_total") and ("image 6" in str(e) or "image 7" in str(e)) and edges_du_bac() == 0
      and profils() == P_avant and not f.exists(), (e, dt))
e, dt, f = piege(GROS)
check("P9 page de plus de 10 Mo → refus « taille », sans lancement", e is not None and e.code == "taille" and dt < 3, e)
e_en = None
try:
    MC.rendre_page("<html><script>top.location='x'</script></html>", OUT / "en.mp4", W=64, H=64, langue="en")
except MC.Arret as x:
    e_en = x
check("P10 messages en anglais", e_en is not None and str(e_en).startswith("Page refused by the sandbox: navigation"),
      e_en)
check("P11 alert / confirm neutralisées (aucun dialogue ne bloque)",
      piege("<html><script>alert(1);confirm(2);window.dzFrame=function(){alert(3)}</script></html>")[0] is None)

# ── faux Ollama ───────────────────────────────────────────────────────────────────────────────────────────────────
OLL, FILE = [], []


class _Ollama(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _rendre(self, code, obj):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._rendre(200, {"models": [{"name": "llama3"}]})

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        OLL.append(corps)
        txt = FILE.pop(0) if len(FILE) > 1 else (FILE[0] if FILE else "")
        if self.path == "/api/generate":
            return self._rendre(200, {"response": txt, "done": True})
        if self.path == "/api/chat":
            return self._rendre(200, {"message": {"role": "assistant", "content": txt}, "done": True})
        self._rendre(404, {})


_srv = ThreadingHTTPServer(("127.0.0.1", 0), _Ollama)
PORT = _srv.server_address[1]
assert PORT != 8765 and HPORT != 8765
threading.Thread(target=_srv.serve_forever, daemon=True).start()
settings.OLLAMA_URL = f"http://127.0.0.1:{PORT}"
CAC.appliquer({"OLLAMA_MODEL": "llama3"})
SCRIPT = "Le fond marin s'éveille\nDeepotus plonge"


def ecrire(corps, langue="fr"):
    return asyncio.run(MC.ecrire(corps, langue))


def dans_prompt(c):
    return (c.get("system") or "") + "\n" + (c.get("prompt") or "") + json.dumps(c.get("messages") or [],
                                                                                 ensure_ascii=False)


# ── [W] écriture par le moteur ────────────────────────────────────────────────────────────────────────────────────
print("[W] écriture")
ORDRE = []
_v0 = PLAF.verifier


async def _espion(o, categorie="", ref=None, confirme=None):
    ORDRE.append((o.get("provider"), categorie, len(OLL)))
    return await _v0(o, categorie, ref, confirme)


PLAF.verifier = _espion
PAGE_MODELE = ('<!doctype html><html><body style="background:#000"><div id="a" style="position:absolute;top:100px;'
               'width:40px;height:40px;background:#f00"></div><script>window.dzFrame=function(t){'
               'document.getElementById("a").style.left=Math.round(t*100)+"px"}</script></body></html>')
OLL.clear()
FILE[:] = ["Voici :\n```html\n" + PAGE_MODELE + "\n```"]
r = ecrire({"script": SCRIPT, "direction": {"style": "style-kinetic-type", "consigne": "CONSIGNE-T238-ALPHA"},
            "moteur": "ollama", "modele": "", "aspect": "16:9", "duree_s": 3, "fps": 24})
PLAF.verifier = _v0
check("W1 page écrite, enregistrée, sans repli", r.get("repli") is False and str(r.get("page_id", "")).startswith("mc-")
      and MC.lire(r["page_id"]) == PAGE_MODELE and r.get("taille") == len(PAGE_MODELE.encode()), r)
check("W2 moteur, modèle, coût, format, cadence, durée rendus", r.get("moteur") == "ollama" and r.get("modele") == "llama3"
      and r.get("cout", {}).get("nature") == "gratuit" and (r.get("W"), r.get("H"), r.get("fps"), r.get("duree_s"))
      == (1920, 1080, 24, 3.0), r)
check("W3 appel en TEXTE (pas de format json) au modèle choisi", OLL and OLL[0].get("format") != "json"
      and OLL[0].get("model") == "llama3", OLL[:1])
check("W4 plafond vérifié AVANT la requête, catégorie motion", ORDRE and ORDRE[0] == ("ollama", "motion", 0), ORDRE)
sy = dans_prompt(OLL[0]) if OLL else ""
fiche = MB.lire("style-kinetic-type")
check("W5 contrat de la page dans le prompt : cadre 1920 × 1080, 3 s, 24 i/s, dzFrame, bac à sable",
      "1920 × 1080" in sy and "3 s" in sy and "24 images/s" in sy and "window.dzFrame" in sy and "fetch" in sy
      and "location" in sy and "data:" in sy, sy[:900])
check("W6 direction : consigne du style et consigne éditée", fiche["consigne"]["fr"][:60] in sy
      and "CONSIGNE-T238-ALPHA" in sy)
check("W7 le script part dans le prompt", "Deepotus plonge" in sy)
OLL.clear()
PIEGEE = "<html><script>fetch('http://x.y/')</script></html>"
FILE[:] = [PIEGEE, PIEGEE]
r = ecrire({"script": SCRIPT, "moteur": "ollama", "duree_s": 2})
check("W8 page piégée deux fois → deux tentatives, puis le REPLI (raison page_refusee, motifs dits)",
      r.get("repli") is True and r.get("raison") == "page_refusee" and r.get("tentatives") == 2
      and "reseau" in r.get("refus", []) and len(OLL) == 2, r)
check("W9 la seconde tentative dit pourquoi la page a été refusée", len(OLL) == 2 and "refusée" in dans_prompt(OLL[1])
      and "appel réseau" in dans_prompt(OLL[1]))
check("W10 la page piégée n'est JAMAIS enregistrée", all(PIEGEE not in p.read_text(encoding="utf-8")
                                                       for p in (_tmp / "motion" / "code").glob("*.html")))
OLL.clear()
FILE[:] = [PIEGEE, PAGE_MODELE]
r = ecrire({"script": SCRIPT, "moteur": "ollama", "duree_s": 2})
check("W11 refusée puis saine → la seconde est gardée", r.get("repli") is False and r.get("tentatives") == 2
      and MC.lire(r["page_id"]) == PAGE_MODELE, r)
OLL.clear()
FILE[:] = [PIEGEE]
r = ecrire({"script": SCRIPT, "moteur": "ollama", "duree_s": 2, "direction": {"curseurs": {"finition": 0}}})
check("W12 finition 0 → une seule tentative avant le repli", r.get("tentatives") == 1 and len(OLL) == 1
      and r.get("repli") is True, r)
OLL.clear()
r = ecrire({"script": SCRIPT, "moteur": "", "duree_s": 2})
check("W13 sans moteur → repli, aucune requête", r.get("repli") is True and r.get("raison") == "sans_moteur" and not OLL
      and r.get("tentatives") == 0, r)
r = ecrire({"script": SCRIPT, "moteur": "anthropic", "modele": "claude-x", "duree_s": 2})
check("W14 moteur non configuré → repli sans requête", r.get("raison") == "non_configure" and not OLL, r)
PLAF.enregistrer({"global_usd": 0.000001, "par_moteur": {}})
CAC.appliquer({"OPENAI_API_KEY": "sk-faux-banc-t238-000000000000000000"})
try:
    ecrire({"script": SCRIPT, "moteur": "openai", "modele": "gpt-x", "duree_s": 2})
    r402 = None
except HTTPException as x:
    r402 = x
check("W15 plafond dépassé → 402, AUCUNE requête", r402 is not None and r402.status_code == 402 and not OLL, r402)
CAC.appliquer({"OPENAI_API_KEY": ""})
PLAF.enregistrer({"global_usd": 0, "par_moteur": {}})
try:
    ecrire({"script": "   ", "moteur": ""})
    ev = None
except ValueError as x:
    ev = x
check("W16 script vide → ValueError", ev is not None)

# ── [R] la page de repli ──────────────────────────────────────────────────────────────────────────────────────────
print("[R] repli")
r = ecrire({"script": "AAA\nBBB </script><script>fetch('x')</script>\nNotre location à top.vitesse : https://deepotus.xyz",
            "moteur": "", "aspect": "1:1", "duree_s": 4})
h = MC.lire(r["page_id"])
check("R1 page de repli admise par le contrôle même quand le SCRIPT contient balises et mots « dangereux » (données en "
      "base64, jamais en clair)", MC.controler(h) == [] and "</script><script>fetch" not in h and "location" not in h
      and "deepotus.xyz" not in h, MC.controler(h))
fr_ = OUT / "repli.mp4"
rr = MC.rendre(r["page_id"], fr_, aspect="1:1", fps=12, duree_s=4)
s = sonde(fr_)
check("R2 repli rendu : 1080×1080, 12 i/s, 48 images, aucune erreur JS (base64 décodé, accents compris)", s.get("width") == 1080 and s.get("height") == 1080
      and s.get("nb_read_frames") == "48" and rr.get("erreurs_js") == 0, (s, rr))


def clair(im):
    """Les points du texte : une couleur vive (le cyan d'accent du nœud), loin du fond sombre."""
    return sum(1 for y in range(0, im.height, 6) for x in range(0, im.width, 6) if max(im.getpixel((x, y))) > 200)


check("R3 un texte est visible pendant sa tenue (pixels clairs au centre à 1 s)", clair(image(fr_, 12)) > 20,
      clair(image(fr_, 12)))

# ── [H] routes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[H] routes")
from app.services.storage import init_db                 # noqa: E402
asyncio.run(init_db())
c = TestClient(app)
OLL.clear()
FILE[:] = [PAGE_MODELE]
q = c.post("/api/motion/code/ecrire", json={"script": SCRIPT, "moteur": "ollama", "aspect": "16:9", "duree_s": 2,
                                             "fps": 12})
j = q.json() if q.status_code == 200 else {}
check("H1 POST /api/motion/code/ecrire → 200, page_id", q.status_code == 200 and j.get("page_id", "").startswith("mc-")
      and j.get("refus_texte") == "", (q.status_code, q.text[:300]))
q = c.post("/api/motion/code/ecrire", json={"script": ""}, headers={"Accept-Language": "en"})
check("H2 script vide → 400 traduit (EN)", q.status_code == 400 and "empty" in q.text.lower(), q.text)
q = c.post("/api/motion/code/ecrire", json={"script": "a", "direction": {"style": "style-inexistant"}})
check("H3 style inconnu → 404", q.status_code == 404, q.status_code)
q = c.get(f"/api/motion/code/{j.get('page_id')}")
check("H4 GET /code/{id} : la page en TEXTE dans du JSON, jamais un document",
      q.status_code == 200 and q.headers.get("content-type", "").startswith("application/json")
      and q.json().get("html") == PAGE_MODELE and q.json().get("refus") == [], q.headers.get("content-type"))
check("H5 id hors motif ou absent → 404 (aucun chemin suivi)", all(c.get(f"/api/motion/code/{x}").status_code == 404
                                                                  for x in ("mc-0000000000000000", "mc-%2E%2E", "mc-zz", "MC-0000000000000000")))


def attendre(jid, s=90):
    fin = time.time() + s
    while time.time() < fin:
        q = c.get(f"/api/jobs/{jid}")
        if q.status_code == 200 and q.json().get("status") in ("done", "failed"):
            return q.json()
        time.sleep(0.5)
    return {}


q = c.post("/api/motion/code/rendre", json={"page_id": j.get("page_id"), "aspect": "16:9", "fps": 12, "duree_s": 2,
                                             "title": "Banc t238"})
jb = attendre(q.json().get("job_id")) if q.status_code == 200 else {}
fv = pathlib.Path(jb.get("final_video_path") or jb.get("video_path") or "_")
s = sonde(fv)
check("H6 POST /code/rendre → job FAIT, MP4 1920×1080 12 i/s 24 images", jb.get("status") == "done" and fv.is_file()
      and s.get("width") == 1920 and s.get("nb_read_frames") == "24", (q.text[:200], jb.get("status"), jb.get("error"), s))
cr = centre_rouge(image(fv, 12)) if fv.is_file() else None
check("H7 le MP4 suit la page (carré à x ≈ 100+20 px à 1 s)", cr is not None and abs(cr[0] - 120) <= 4, cr)
pid_p = MC.enregistrer("<html><script>window.dzFrame=function(t){var w=window;w['loc'+'ation']='ht'+'tp:/'+'/127.0.0.1:"
                       f"{HPORT}/route'}}</script></html>")
q = c.post("/api/motion/code/rendre", json={"page_id": pid_p, "fps": 12, "duree_s": 1})
jb = attendre(q.json().get("job_id")) if q.status_code == 200 else {}
check("H8 page piégée → job EN ÉCHEC avec le message FR, rien reçu", jb.get("status") == "failed"
      and "naviguer" in str(jb.get("error")) and not HITS, (jb.get("status"), jb.get("error"), HITS))
pid_f = MC.enregistrer("<html><script>fetch('/x')</script></html>")      # un fichier posé à la main : contrôlé de nouveau
q = c.post("/api/motion/code/rendre", json={"page_id": pid_f, "fps": 12, "duree_s": 1}, headers={"Accept-Language": "en"})
jb = attendre(q.json().get("job_id")) if q.status_code == 200 else {}
check("H9 fichier modifié à la main → refusé au rendu (message EN)", jb.get("status") == "failed"
      and "refused by the sandbox" in str(jb.get("error")), (jb.get("status"), jb.get("error")))
check("H10 rendre une page inconnue → 404", c.post("/api/motion/code/rendre", json={"page_id": "mc-ffffffffffffffff"})
      .status_code == 404)
cd = TestClient(app, client=("192.168.1.50", 5000))
check("H11 autre appareil → refusé", cd.post("/api/motion/code/ecrire", json={"script": "a"}).status_code in (401, 403)
      and cd.post("/api/motion/code/rendre", json={"page_id": j.get("page_id")}).status_code in (401, 403))

# ── [A] base de l'Animation ───────────────────────────────────────────────────────────────────────────────────────
print("[A] base de l'Animation")
q = c.post("/api/animate", json={"base": {"source_kind": "motion_code", "page_id": j.get("page_id"), "aspect": "1:1",
                                          "fps": 12, "duree_s": 2},
                                 "aspect": "1:1", "fps": 12, "duration_s": 2, "elements": [], "title": "Banc t238 base"})
jb = attendre(q.json().get("job_id"), 120) if q.status_code == 200 else {}
fa = pathlib.Path(jb.get("final_video_path") or "_")
bases = list(settings.outputs_path.glob("mcode_base_*.mp4"))
check("A1 Animation sur base motion code → job FAIT, base rendue au format et à la cadence de l'Animation",
      jb.get("status") == "done" and fa.is_file() and len(bases) == 1 and sonde(bases[0]).get("width") == 1080
      and sonde(bases[0]).get("nb_read_frames") == "24", (jb.get("status"), jb.get("error"), bases))
ca = centre_rouge(image(fa, 12)) if fa.is_file() else None
check("A2 la base se voit dans le rendu de l'Animation (carré rouge à x ≈ 120 à 1 s)", ca is not None
      and abs(ca[0] - 120) <= 6, ca)
q = c.post("/api/animate", json={"base": {"source_kind": "motion_code", "page_id": pid_p, "fps": 12, "duree_s": 1},
                                 "fps": 12, "duration_s": 1, "elements": []})
jb = attendre(q.json().get("job_id"), 60) if q.status_code == 200 else {}
check("A3 base piégée → Animation en échec, message du bac à sable", jb.get("status") == "failed"
      and "naviguer" in str(jb.get("error")), (jb.get("status"), jb.get("error")))

# ── [L] traductions des erreurs ───────────────────────────────────────────────────────────────────────────────────
print("[L] erreurs traduites")
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace")
check("L1 i18n_l10_erreurs --check vert", rc.returncode == 0, (rc.stdout or "")[-600:] + (rc.stderr or "")[-300:])
check("L2 fin : aucun navigateur du bac à sable vivant, aucun profil jetable restant", edges_du_bac() == 0 and profils() == P0,
      (edges_du_bac(), profils()))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
