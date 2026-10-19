# -*- coding: utf-8 -*-
"""Motion code (t238, lot « Studio : Animation », option B validée par l'utilisateur le 19/10/2026).

Le moteur de texte CHOISI (registre `moteurs_texte`, jamais un fournisseur codé en dur) écrit une page HTML / SVG /
Canvas animée — durée, cadence et taille imposées — que l'on rend en MP4 image par image, dans Edge sans fenêtre piloté
par CDP, sur une horloge VIRTUELLE. La page est une DONNÉE : elle n'est jamais évaluée hors du bac à sable.

Bac à sable (plan § t238) :
  - la page est contrôlée AVANT tout lancement (`controler`) : aucun appel réseau, aucune navigation, aucune ressource
    externe, aucun cadre, 10 Mo au plus — sinon REFUS, sans rien exécuter ;
  - elle vit dans un document `data:` (opaque, sans accès fichier) sous la CSP
    `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:` ;
  - Edge part sur un profil JETABLE (dossier temporaire supprimé à la fin), réseau coupé (mandataire mort), domaine
    `Fetch` qui refuse toute requête, téléchargements refusés, fenêtres neuves bloquées ; une navigation demandée par la
    page (top.location…) ARRÊTE le rendu ;
  - délai de 120 s au plus pour tout le rendu : au-delà (boucle infinie…), le processus et ses enfants sont tués et le
    profil effacé — arrêt PROPRE, jamais un Edge orphelin.

Horloge virtuelle : un script posé par `Page.addScriptToEvaluateOnNewDocument` (donc AVANT la page) remplace
performance.now, Date, setTimeout / setInterval, requestAnimationFrame et Math.random (graine fixe) ; pour chaque image
on avance le temps (`__dzAvance`), les animations CSS / WAAPI sont calées sur ce temps, `window.dzFrame(t)` est appelé
s'il existe, puis la capture part dans ffmpeg (H.264, yuv420p).

Coût : estimé AVANT l'appel et vérifié sous les plafonds (`tirer_garde`, catégorie motion). Sans moteur, ou moteur non
configuré : le REPLI déterministe, une page écrite par nous (une ligne du script = un texte qui entre et tient).
"""
import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.config import DATA_ROOT
from app.services import motion_choregraphe as CH

CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:"
MAX_PAGE = 10 * 1024 * 1024             # octets UTF-8 de la page
DELAI = 120.0                           # secondes, tout le rendu
DELAI_APPEL = 20.0                      # secondes, une commande CDP (chargement, une image)
FPS = (12, 60)
FPS_DEFAUT = 30
DUREE = (1, 60)
DUREE_DEFAUT = 8
MAX_TOKENS = 16000
MAX_RAPPELS = 10000                     # minuteries tirées par image au plus (setTimeout(f, 0) récursif)
_ID = re.compile(r"^mc-[0-9a-f]{16}$")

MESSAGES = {
    "refus": {"fr": "Page refusée par le bac à sable : {details}.",
              "en": "Page refused by the sandbox: {details}."},
    "taille": {"fr": "Page refusée : elle dépasse 10 Mo.", "en": "Page refused: it is larger than 10 MB."},
    "navigation": {"fr": "Rendu arrêté : la page a tenté de naviguer ({url}).",
                   "en": "Rendering stopped: the page tried to navigate ({url})."},
    "fenetre": {"fr": "Rendu arrêté : la page a tenté d'ouvrir une fenêtre.",
                "en": "Rendering stopped: the page tried to open a window."},
    "delai": {"fr": "Rendu arrêté : la page ne répond plus ({etape}, délai de {s} s dépassé — boucle infinie ?).",
              "en": "Rendering stopped: the page stopped responding ({etape}, {s} s limit exceeded — infinite loop?)."},
    "edge": {"fr": "Microsoft Edge est introuvable sur ce PC : le rendu motion code en a besoin.",
             "en": "Microsoft Edge was not found on this PC: motion code rendering needs it."},
    "ffmpeg": {"fr": "L'encodage vidéo a échoué (ffmpeg).", "en": "Video encoding failed (ffmpeg)."},
    "navigateur": {"fr": "Le navigateur du bac à sable s'est arrêté ({details}).",
                   "en": "The sandbox browser stopped ({details})."},
}

CODES_REFUS = {
    "taille": {"fr": "plus de 10 Mo", "en": "larger than 10 MB"},
    "reseau": {"fr": "appel réseau", "en": "network call"},
    "navigation": {"fr": "navigation", "en": "navigation"},
    "ressource_externe": {"fr": "ressource externe", "en": "external resource"},
    "cadre": {"fr": "cadre ou objet intégré", "en": "frame or embedded object"},
    "vide": {"fr": "aucun document HTML", "en": "no HTML document"},
}


class Arret(Exception):
    """Un refus ou un arrêt du bac à sable : `code` (clé de MESSAGES) et le message dans la langue demandée."""

    def __init__(self, code: str, langue: str = "fr", **v):
        self.code = code
        self.details = v
        gabarit = MESSAGES[code]["en" if langue == "en" else "fr"]
        super().__init__(gabarit.format(**v))


# ── le contrôle statique ──────────────────────────────────────────────────────────────────────────────────────────
_RESEAU = re.compile(r"\bfetch\s*\(|XMLHttpRequest|\bWebSocket\b|\bEventSource\b|sendBeacon|\bimport\s*\(|"
                     r"\bimportScripts\b|serviceWorker|\bnew\s+(?:Shared)?Worker\b|RTCPeerConnection|"
                     r"\bWebTransport\b|\bopenDatabase\b", re.I)
_NAVIGATION = re.compile(r"\blocation\b|\bwindow\s*\.\s*open\b|\bopen\s*\(\s*['\"`]|\btop\s*[.\[]|\bparent\s*[.\[]|"
                         r"\bopener\b|http-equiv\s*=\s*['\"]?\s*refresh|<\s*form\b|<\s*a\b[^>]*\bhref|"
                         r"\.\s*(?:submit|click)\s*\(\s*\)|\bhistory\s*\.", re.I)
_CADRE = re.compile(r"<\s*(?:iframe|frame|frameset|object|embed|portal|base|link|applet)\b", re.I)
_URL = re.compile(r"(?:https?|ftp|wss?|file|blob|filesystem|javascript)\s*:|//[a-z0-9-]+\.[a-z]", re.I)
_NS_SVG = re.compile(r"https?://www\.w3\.org/[0-9A-Za-z/._#-]*")   # les espaces de noms XML ne sont pas des ressources


def controler(html) -> list:
    """Les motifs de refus de la page (codes de CODES_REFUS, triés) ; liste vide = la page peut entrer dans le bac à
    sable. Contrôle STATIQUE et prudent (une page saine qui nomme `location` est refusée aussi) : la CSP et le domaine
    Fetch gardent ensuite l'exécution."""
    if not isinstance(html, str) or "<" not in html:
        return ["vide"]
    if len(html) > MAX_PAGE or len(html.encode("utf-8")) > MAX_PAGE:
        return ["taille"]                       # rien d'autre n'est lu : la page n'entrera pas
    out = set()
    if _RESEAU.search(html):
        out.add("reseau")
    if _NAVIGATION.search(html):
        out.add("navigation")
    if _CADRE.search(html):
        out.add("cadre")
    if _URL.search(_NS_SVG.sub("", html)):
        out.add("ressource_externe")
    return sorted(out)


def details_refus(codes, langue: str = "fr") -> str:
    lg = "en" if langue == "en" else "fr"
    return ", ".join(CODES_REFUS[c][lg] for c in codes if c in CODES_REFUS)


_FENCE = re.compile(r"```(?:html|HTML)?\s*\n(.*?)```", re.S)


def extraire_page(texte) -> str:
    """Le document HTML d'une réponse de modèle (bloc ```html``` s'il y en a un, sinon du premier `<` au dernier `>`).
    Rien n'est exécuté : c'est du texte."""
    if not isinstance(texte, str):
        return ""
    m = _FENCE.search(texte)
    t = m.group(1) if m else texte
    a, b = t.find("<"), t.rfind(">")
    return t[a:b + 1].strip() if a >= 0 and b > a else ""


_DOCTYPE = re.compile(r"^\s*<!doctype[^>]*>", re.I)


def envelopper(html: str, W: int, H: int) -> str:
    """Le document servi au bac à sable : la CSP en TÊTE (avant tout élément de la page : elle ne peut pas s'en
    défaire, une seconde politique ne ferait que restreindre), le cadre W×H sans marge, puis la page."""
    return ('<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="%s">'
            '<style>html,body{margin:0;padding:0;width:%dpx;height:%dpx;overflow:hidden}</style>' % (CSP, W, H)
            + _DOCTYPE.sub("", html, count=1))


# ── l'horloge virtuelle (posée AVANT la page) ─────────────────────────────────────────────────────────────────────
HORLOGE = r"""(function(){var T=0,E=1760832000000,N=0,Q=[],R=[],W=new WeakMap();
var RD=Date;function VD(){var a=[].slice.call(arguments);if(!(this instanceof VD))return new RD(E+T).toString();
return a.length?new(Function.prototype.bind.apply(RD,[null].concat(a))):new RD(E+T)}
VD.prototype=RD.prototype;VD.now=function(){return E+Math.floor(T)};VD.UTC=RD.UTC;VD.parse=RD.parse;window.Date=VD;
try{performance.now=function(){return T}}catch(_e){}
var s=238;Math.random=function(){s|=0;s=s+0x6D2B79F5|0;var t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;
return((t^t>>>14)>>>0)/4294967296};
function at(f,ms,a,rep){var id=++N;Q.push({id:id,at:T+Math.max(rep?1:0,Number(ms)||0),f:f,a:a,rep:rep?Math.max(1,Number(ms)||0):0});return id}
window.setTimeout=function(f,ms){return at(f,ms,[].slice.call(arguments,2),0)};
window.setInterval=function(f,ms){return at(f,ms,[].slice.call(arguments,2),1)};
window.clearTimeout=window.clearInterval=function(id){Q=Q.filter(function(q){return q.id!==id})};
window.requestAnimationFrame=function(f){var id=++N;R.push({id:id,f:f});return id};
window.cancelAnimationFrame=function(id){R=R.filter(function(q){return q.id!==id})};
window.requestIdleCallback=function(f){return at(f,0,[],0)};window.cancelIdleCallback=window.clearTimeout;
window.alert=window.confirm=window.prompt=window.print=function(){};
window.__dzErreurs=0;function run(f,a){try{typeof f==="function"&&f.apply(window,a)}catch(_e){window.__dzErreurs++}}
window.__dzAvance=function(ms){var k=0;for(;;){var p=null;Q.forEach(function(q){if(q.at<=ms&&(!p||q.at<p.at))p=q});
if(!p||k++>=""" + str(MAX_RAPPELS) + r""")break;T=p.at;if(p.rep)p.at+=p.rep;else Q=Q.filter(function(q){return q!==p});run(p.f,p.a)}
T=ms;var r=R;R=[];r.forEach(function(q){run(q.f,[T])});
try{document.getAnimations().forEach(function(a){if(!W.has(a))W.set(a,ms);a.pause();a.currentTime=ms-W.get(a)})}catch(_e){}
if(typeof window.dzFrame==="function")run(window.dzFrame,[ms/1000]);return window.__dzErreurs}})();"""


# ── Edge sans fenêtre, par CDP ────────────────────────────────────────────────────────────────────────────────────
def trouver_edge():
    """Le chemin de msedge.exe (DEEPOTUS_EDGE l'emporte, pour un banc), sinon None."""
    cands = [os.environ.get("DEEPOTUS_EDGE", "")]
    for var in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        if os.environ.get(var):
            cands.append(os.path.join(os.environ[var], "Microsoft", "Edge", "Application", "msedge.exe"))
    cands.append(shutil.which("msedge") or "")
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def _tuer(p) -> None:
    """Le processus ET ses enfants (Edge en lance plusieurs), sans fenêtre de console."""
    if p is None or p.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        p.kill()
    except OSError:
        pass
    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def _effacer(dossier: str) -> bool:
    """Le profil jetable effacé (Edge relâche ses fichiers quelques instants après sa mort) ; True s'il n'existe plus."""
    for _ in range(40):
        shutil.rmtree(dossier, ignore_errors=True)
        if not os.path.exists(dossier):
            return True
        time.sleep(0.1)
    return not os.path.exists(dossier)


class _Cdp:
    """Un client CDP minimal sur la session aplatie d'un onglet ; chaque événement reçu passe par `surveiller`."""

    def __init__(self, url: str, surveiller, fin: float, total: float):
        from websockets.sync.client import connect
        self.ws = connect(url, max_size=256 * 1024 * 1024, open_timeout=10)
        self.n = 0
        self.sid = None
        self.surveiller = surveiller
        self.fin = fin
        self.total = total

    def envoyer(self, methode: str, params=None, sid=True) -> int:
        self.n += 1
        m = {"id": self.n, "method": methode, "params": params or {}}
        if sid and self.sid:
            m["sessionId"] = self.sid
        self.ws.send(json.dumps(m))
        return self.n

    def appel(self, methode: str, params=None, *, etape: str = "", delai: float = DELAI_APPEL, langue="fr", sid=True):
        i = self.envoyer(methode, params, sid)
        borne = min(time.monotonic() + delai, self.fin)
        while True:
            reste = borne - time.monotonic()
            if reste <= 0:
                raise Arret("delai", langue, etape=etape or methode,
                            s=int(round(self.total if borne >= self.fin else delai)))
            try:
                brut = self.ws.recv(timeout=reste)
            except TimeoutError:
                continue
            except Exception as e:  # noqa: BLE001 — la connexion tombe : le navigateur est mort
                raise Arret("navigateur", langue, details=type(e).__name__) from None
            r = json.loads(brut)
            if r.get("id") == i:
                if "error" in r:
                    raise Arret("navigateur", langue, details=str(r["error"].get("message", ""))[:120])
                return r.get("result") or {}
            if r.get("method"):
                self.surveiller(self, r)

    def fermer(self):
        try:
            self.ws.close()
        except Exception:  # noqa: BLE001
            pass


def _lancer_edge(edge: str, profil: str, delai_demarrage: float = 20.0):
    args = [edge, "--headless=new", f"--user-data-dir={profil}", "--remote-debugging-port=0",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-sync",
            "--disable-background-networking", "--disable-component-update", "--disable-default-apps",
            "--disable-features=Translate,MediaRouter,OptimizationHints,AutofillServerCommunication",
            "--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=<-loopback>", "--block-new-web-contents",
            "--deny-permission-prompts", "--mute-audio", "--hide-scrollbars", "about:blank"]
    p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    f = Path(profil) / "DevToolsActivePort"
    fin = time.monotonic() + delai_demarrage
    while time.monotonic() < fin:
        if p.poll() is not None:
            break
        try:
            lignes = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            lignes = []
        if len(lignes) >= 2 and lignes[0].strip().isdigit():
            return p, f"ws://127.0.0.1:{lignes[0].strip()}{lignes[1].strip()}"
        time.sleep(0.05)
    _tuer(p)
    return None, None


def rendre_page(html: str, sortie, *, W: int, H: int, fps: int = FPS_DEFAUT, duree_s: float = DUREE_DEFAUT,
                delai: float = DELAI, langue: str = "fr", edge=None) -> dict:
    """Rend la page dans le bac à sable → MP4 `sortie` (W×H, `fps`, round(duree_s × fps) images). Lève `Arret` (refus,
    navigation, délai…) après avoir TOUT arrêté : Edge et ses enfants tués, profil effacé, sortie partielle retirée.
    Rend {images, fps, W, H, duree_s, erreurs_js, profil_efface}."""
    refus = controler(html)
    if refus:
        if refus == ["taille"]:
            raise Arret("taille", langue)
        raise Arret("refus", langue, details=details_refus(refus, langue))
    edge = edge or trouver_edge()
    if not edge:
        raise Arret("edge", langue)
    sortie = Path(sortie)
    n = max(1, int(round(float(duree_s) * int(fps))))
    fin = time.monotonic() + float(delai)
    profil = tempfile.mkdtemp(prefix="dz_motion_code_")
    p = enc = cdp = None
    etat = {"arret": None, "frame": None, "ok": False}
    shell = ('<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="%s">' % CSP)
    shell_url = "data:text/html;base64," + base64.b64encode(shell.encode("utf-8")).decode("ascii")

    def surveiller(c, ev):
        m, prm = ev.get("method"), ev.get("params") or {}
        if m == "Fetch.requestPaused":           # toute requête : refusée (data: n'y passe jamais)
            c.envoyer("Fetch.failRequest", {"requestId": prm.get("requestId"), "errorReason": "BlockedByClient"})
            if prm.get("resourceType") == "Document" and etat["ok"]:
                etat["arret"] = etat["arret"] or Arret("navigation", langue, url=str(prm.get("request", {})
                                                                                      .get("url", ""))[:120])
        elif m == "Page.frameRequestedNavigation" and etat["ok"]:
            etat["arret"] = etat["arret"] or Arret("navigation", langue, url=str(prm.get("url", ""))[:120])
        elif m == "Page.windowOpen" or (m == "Target.targetCreated" and etat["ok"]
                                        and (prm.get("targetInfo") or {}).get("type") == "page"):
            etat["arret"] = etat["arret"] or Arret("fenetre", langue)
        elif m == "Page.javascriptDialogOpening":
            c.envoyer("Page.handleJavaScriptDialog", {"accept": False})

    def verifier():
        if etat["arret"]:
            raise etat["arret"]

    try:
        p, url = _lancer_edge(edge, profil, min(20.0, max(1.0, fin - time.monotonic())))
        if not p:
            raise Arret("navigateur", langue, details="démarrage")
        cdp = _Cdp(url, surveiller, fin, float(delai))
        en = langue == "en"
        cdp.appel("Browser.setDownloadBehavior", {"behavior": "deny"}, etape="préparation", langue=langue, sid=False)
        tid = cdp.appel("Target.createTarget", {"url": "about:blank"}, etape="onglet", langue=langue,
                        sid=False)["targetId"]
        cdp.sid = cdp.appel("Target.attachToTarget", {"targetId": tid, "flatten": True}, etape="onglet",
                            langue=langue, sid=False)["sessionId"]
        for m, prm in (("Page.enable", {}), ("Runtime.enable", {}),
                       ("Fetch.enable", {"patterns": [{"urlPattern": "*"}]}),
                       ("Page.addScriptToEvaluateOnNewDocument", {"source": HORLOGE}),
                       ("Emulation.setDeviceMetricsOverride", {"width": W, "height": H, "deviceScaleFactor": 1,
                                                               "mobile": False})):
            cdp.appel(m, prm, etape="setup" if en else "préparation", langue=langue)
        fid = cdp.appel("Page.navigate", {"url": shell_url}, etape="loading" if en else "chargement",
                  langue=langue)["frameId"]
        cdp.appel("Runtime.evaluate", {"expression": "typeof window.__dzAvance", "returnByValue": True},
                  etape="loading" if en else "chargement", langue=langue)
        etat["ok"] = True                         # désormais, toute navigation ou fenêtre est un arrêt
        cdp.appel("Page.setDocumentContent", {"frameId": fid, "html": envelopper(html, W, H)},
                  etape="page loading" if en else "chargement de la page", langue=langue)
        verifier()
        sortie.parent.mkdir(parents=True, exist_ok=True)
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "png", "-i", "-",
             "-frames:v", str(n), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart",
             str(sortie)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        erreurs = 0
        for i in range(n):
            ms = round(i * 1000 / fps, 3)
            r = cdp.appel("Runtime.evaluate", {"expression": "window.__dzAvance(%r)" % ms, "returnByValue": True},
                          etape=("frame %d" if en else "image %d") % (i + 1), langue=langue)
            v = (r.get("result") or {}).get("value")
            erreurs = v if isinstance(v, int) else erreurs
            verifier()
            img = cdp.appel("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True},
                            etape="capture %d" % (i + 1), langue=langue)
            verifier()
            enc.stdin.write(base64.b64decode(img.get("data") or ""))
        enc.stdin.close()
        if enc.wait(timeout=max(5.0, fin - time.monotonic() + 30)) != 0 or not sortie.is_file():
            raise Arret("ffmpeg", langue)
        return {"images": n, "fps": int(fps), "W": W, "H": H, "duree_s": round(n / fps, 4), "erreurs_js": erreurs}
    except BaseException:
        if enc and enc.poll() is None:
            enc.kill()
        if enc:
            try:
                enc.stdin.close()               # le tube d'un encodeur tué : rien à vider
            except (OSError, ValueError):
                pass
            try:
                enc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        sortie.unlink(missing_ok=True)
        raise
    finally:
        if cdp:
            cdp.fermer()
        _tuer(p)
        _effacer(profil)


# ── la page de repli (écrite par nous) ────────────────────────────────────────────────────────────────────────────
_JS_REPLI = r"""var D=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(document.getElementById("dz-donnees").textContent.trim()),
function(c){return c.charCodeAt(0)}))),S=document.getElementById("dz-scene");
function ez(n,t){t=Math.min(1,Math.max(0,t));if(n==="easeOutBack"){var c=1.70158;return 1+(c+1)*Math.pow(t-1,3)+c*Math.pow(t-1,2)}
if(n==="easeOut")return 1-Math.pow(1-t,3);return t}
var E=D.elements.map(function(e){var d=document.createElement("div");d.textContent=e.text;d.style.cssText="position:absolute;left:0;top:0;"
+"transform-origin:center;white-space:nowrap;font:700 "+e.style.size+"px "+D.police+";color:"+e.style.color+";opacity:0";S.appendChild(d);return{e:e,d:d}});
window.dzFrame=function(t){E.forEach(function(o){var e=o.e,k=e.keyframes,a=k[0],b=k[k.length-1],fin=e.start+e.dur+e.hold;
if(t<e.start||t>fin){o.d.style.opacity=0;return}var u=e.dur>0?Math.min(1,(t-e.start)/e.dur):1,v=ez(a.easing,u);
function L(p){return a[p]+(b[p]-a[p])*v}var x=L("x")*D.W/100,y=L("y")*D.H/100,w=o.d.offsetWidth,h=o.d.offsetHeight;
o.d.style.opacity=L("opacity");o.d.style.transform="translate("+(x-w/2)+"px,"+(y-h/2)+"px) scale("+L("scale")+") rotate("+L("rotation")+"deg)"})};"""


def page_repli(script: str, fiche, m: dict, W: int, H: int, duree_s: float, bpm=None) -> str:
    """La page déterministe du repli : les éléments du repli du chorégraphe (une ligne = un texte), sur un fond qui
    dérive lentement aux couleurs de la marque ; `dzFrame(t)` les place. Aucune ressource externe. Les données (le texte
    du script compris) y sont en BASE64 : aucune balise possible, et le contrôle ne lit pas les mots de l'utilisateur
    (« location », « fetch(… ») comme du code — notre propre page n'est jamais refusée à cause d'eux."""
    els = CH.repli(script, fiche, m, duree_s, bpm)
    donnees = json.dumps({"elements": els, "W": W, "H": H,
                          "police": "Impact, 'Arial Black', 'Segoe UI', sans-serif"}, ensure_ascii=True)
    donnees = base64.b64encode(donnees.encode("utf-8")).decode("ascii")
    return ('<!doctype html><html><head><style>#dz-fond{position:absolute;inset:0;background:radial-gradient('
            'circle at 30%% 30%%,%s 0,#02060d 70%%)}#dz-scene{position:absolute;inset:0;overflow:hidden}</style></head>'
            '<body><div id="dz-fond"></div><div id="dz-scene"></div>'
            '<script type="application/octet-stream" id="dz-donnees">%s</script><script>%s'
            'var F=document.getElementById("dz-fond");var f0=window.dzFrame;window.dzFrame=function(t){'
            'F.style.backgroundPosition=(Math.sin(t/%g*6.2832)*4)+"%% 0";f0(t)};</script></body></html>'
            % (m.get("marque") or "#0b2a3a", donnees, _JS_REPLI, max(1.0, float(duree_s))))


# ── le prompt ─────────────────────────────────────────────────────────────────────────────────────────────────────
def taille(aspect: str) -> tuple:
    from app.services.animation_service import _wh
    return _wh(aspect)


def systeme(d: dict, W: int, H: int, duree_s: float, fps: int, m: dict, tempo_bpm=None) -> str:
    """Le prompt système : le contrat de la page (cadre, temps, bac à sable), puis la direction (style aux champs
    substitués, consigne, tempo, curseurs, précisions) — les mêmes pièces que le chorégraphe."""
    lignes = [
        "Tu es l'auteur du nœud « Rendu motion code » de DeepotusVideo. Tu écris UNE page HTML complète et autonome "
        "(HTML, CSS, SVG ou Canvas, JavaScript en ligne) qui joue une animation de motion design.",
        "Ne pose aucune question : tout ce qu'il faut savoir est ci-dessous. Rends SEULEMENT le document HTML, sans "
        "explication.",
        "Cadre : exactement %d × %d pixels, body sans marge, overflow hidden. Durée : %g s. Cadence : %d images/s."
        % (W, H, duree_s, fps),
        "Temps : définis window.dzFrame = function(t){…} qui dessine l'état EXACT à t secondes (0 ≤ t < %g) — c'est la "
        "méthode préférée, déterministe. requestAnimationFrame, setTimeout et les animations CSS marchent aussi : "
        "l'horloge est virtuelle, avancée image par image ; Math.random est déterministe." % duree_s,
        "Bac à sable sans réseau (toute infraction fait REFUSER la page) : aucune URL http(s), aucune police web, "
        "aucune image distante, aucun <link>, <iframe>, <object>, <embed>, <base>, <form> ni lien ; images en data: "
        "seulement ; aucun appel réseau (fetch, XMLHttpRequest, WebSocket, EventSource, sendBeacon, import(), Worker) ;"
        " ne touche jamais à location, top, parent, history ni window.open.",
        "Polices du système seulement (sans-serif, serif, monospace, Arial, Segoe UI, Impact). Couleur d'accent %s, "
        "couleur de marque %s." % (m.get("couleur"), m.get("marque")),
    ]
    f = d.get("fiche")
    lg = d.get("langue", "fr")
    if f:
        lignes += ["", "STYLE — " + CH._loc(f.get("titre"), lg), d.get("consigne_style") or CH._loc(f.get("consigne"), lg),
                   "Rythme : " + CH._loc(f.get("rythme"), lg)]
    if tempo_bpm:
        lignes += ["", "TEMPO : %g BPM — un temps = %g s ; cale les entrées sur les temps." % (tempo_bpm,
                                                                                              round(60 / tempo_bpm, 4))]
    if d.get("consigne"):
        lignes += ["", "CONSIGNE DE DIRECTION :", d["consigne"]]
    lignes += CH._fin_de_direction(d, lg)
    return "\n".join(lignes)


def prompt(script: str, aspect: str, W: int, H: int, duree_s: float, fps: int, erreur: str = "") -> str:
    p = f"Format {aspect} ({W}×{H}), {duree_s:g} s, {fps} images/s.\nSCRIPT :\n{script}"
    if erreur:
        p += f"\n\nTa page précédente a été refusée ({erreur[:200]}). Réécris-la en respectant le bac à sable."
    return p


# ── les pages enregistrées ────────────────────────────────────────────────────────────────────────────────────────
def _dossier() -> Path:
    return DATA_ROOT / "motion" / "code"


def enregistrer(html: str) -> str:
    pid = "mc-" + hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
    d = _dossier()
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{pid}.html").write_bytes(html.encode("utf-8"))
    return pid


def lire(pid) -> str:
    if not isinstance(pid, str) or not _ID.match(pid):
        raise LookupError("Page motion code inconnue.")
    f = _dossier() / f"{pid}.html"
    if not f.is_file():
        raise LookupError("Page motion code inconnue.")
    return f.read_bytes().decode("utf-8", errors="replace")


def bornes(aspect, fps, duree_s) -> tuple:
    """(aspect, W, H, fps, duree_s) bornés : formats du nœud, 12-60 i/s, 1-60 s."""
    aspect = aspect if aspect in CH.FORMATS else "9:16"
    W, H = taille(aspect)
    f = fps if isinstance(fps, (int, float)) and not isinstance(fps, bool) and math.isfinite(fps) else FPS_DEFAUT
    f = int(min(FPS[1], max(FPS[0], round(f))))
    d = float(CH._nombre(duree_s, DUREE_DEFAUT, *DUREE))
    return aspect, W, H, f, d


def rendre(pid, sortie, *, aspect="9:16", fps=FPS_DEFAUT, duree_s=DUREE_DEFAUT, langue="fr", delai=DELAI) -> dict:
    """La page enregistrée `pid`, contrôlée de nouveau (un fichier modifié à la main est refusé aussi), rendue en MP4."""
    aspect, W, H, f, d = bornes(aspect, fps, duree_s)
    return rendre_page(lire(pid), sortie, W=W, H=H, fps=f, duree_s=d, langue=langue, delai=delai)


# ── l'écriture par le moteur ──────────────────────────────────────────────────────────────────────────────────────
async def ecrire(corps: dict, langue: str = "fr") -> dict:
    """{page_id, taille, moteur, modele, cout, repli, raison, refus, tentatives, aspect, W, H, fps, duree_s, effort,
    effort_applique}. ValueError (script vide), LookupError (style / source inconnus) ; un plafond dépassé remonte
    (402). Une page refusée deux fois, une réponse illisible : le repli."""
    from app.services import moteurs_texte as MT
    from app.services import pricing
    if not isinstance(corps, dict):
        raise ValueError("Corps JSON attendu.")
    script = CH._propre(corps.get("script"), CH.MAX_SCRIPT, lignes=True)
    if not script:
        raise ValueError("Le script est vide.")
    d = CH.direction(corps.get("direction"), langue)
    fiche = d["fiche"]
    aspect, W, H, fps, duree = bornes(corps.get("aspect"), corps.get("fps"), corps.get("duree_s"))
    m = CH.marque(corps.get("marque"))
    moteur = corps.get("moteur").strip() if isinstance(corps.get("moteur"), str) else ""
    modele = corps.get("modele").strip() if isinstance(corps.get("modele"), str) else ""
    effort = corps.get("effort").strip().lower()[:16] if isinstance(corps.get("effort"), str) else None
    dd = corps.get("direction") if isinstance(corps.get("direction"), dict) else {}
    bpm = CH.tempo(corps.get("tempo_bpm")) if corps.get("tempo_bpm") is not None else CH.tempo(dd.get("tempo_bpm"))
    rep = {"moteur": moteur, "modele": modele, "aspect": aspect, "W": W, "H": H, "fps": fps, "duree_s": duree,
           "repli": False, "raison": "", "refus": [], "tentatives": 0, "effort": effort or "auto", "effort_applique": "",
           "cout": {"nature": MT.nature_cout(moteur) if moteur else "gratuit", "estime_usd": 0.0}}

    def _fini(r: dict, html: str) -> dict:
        return dict(r, page_id=enregistrer(html), taille=len(html.encode("utf-8")))

    def _repli(raison: str) -> dict:
        return _fini(dict(rep, repli=True, raison=raison), page_repli(script, fiche, m, W, H, duree, bpm))

    if not moteur:
        return _repli("sans_moteur")
    if not MT.connu(moteur):
        return _repli("moteur_inconnu")
    if not MT.configure(moteur):
        return _repli("non_configure")
    if not modele:
        modele = rep["modele"] = MT.modele_sain(moteur)
    if MT.ressemble_a_une_cle(modele):
        rep["modele"] = ""
        return _repli("modele_fautif")
    rep["effort_applique"] = MT.effort_applique(moteur, modele, effort)
    sy = systeme(d, W, H, duree, fps, m, bpm)
    erreur, raison = "", "sortie_invalide"
    for n in ((1,) if d["curseurs"]["finition"] <= 1 else (1, 2)):
        p = prompt(script, aspect, W, H, duree, fps, erreur)
        rep["tentatives"] = n
        rep["cout"]["estime_usd"] = round(rep["cout"]["estime_usd"]
                                          + pricing.estimate(MT.estimer(moteur, p, sy, MAX_TOKENS, effort,
                                                                         modele=modele))["total_usd"], 6)
        try:
            texte = await MT.tirer_garde(moteur, modele, p, sy, MAX_TOKENS, json=False, categorie="motion",
                                         effort=effort, timeout=180.0)
        except RuntimeError as e:
            erreur, raison = str(e), "sortie_invalide"
            continue
        html = extraire_page(texte)
        refus = controler(html)
        if not refus:
            return _fini(dict(rep, refus=[]), html)
        rep["refus"] = refus
        erreur, raison = details_refus(refus, "fr"), "page_refusee"
    return _repli(raison)
