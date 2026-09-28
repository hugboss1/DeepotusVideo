# -*- coding: utf-8 -*-
"""P1 #12 (28/09/2026) — CHAMPS IA : L'INTERVALLE DE 800 MS ET TROIS PETITS ECARTS.

Mesures du 28/09 (couche `frontend/shared/dz-champ-ia.js` de 5a31bdf) :
  (1) `setInterval(synchroniser, 800)` pose au demarrage, JAMAIS arrete : il
      tourne aussi sur une page sans aucun champ IA ;
  (2) `available:false` de la dictee etait retenu jusqu'au focus SUIVANT d'un
      champ IA -- le micro grise ne donne pas le focus : une cle ajoutee dans
      les Reglages restait ignoree ;
  (3) les regles SANS `page` (application principale) etaient essayees sur les
      pages a part (/vectorlab, /atelier…) ;
  (4) Vectorlab, `#iaTexte` 312 x 40 px, barre 166 px (mesure a l'ecran sur
      8799) : la barre se centrait a droite et couvrait le CENTRE du champ
      (elementFromPoint = le badge), 129 px restaient au texte.
Decisions : balayage pose tant qu'un champ est suivi, arrete sinon et a
`pagehide` (repris a `pageshow`) ; indisponibilite qui expire (30 s) et
oubliee quand un champ neuf est habille ; regles sans page ignorees sur une page
a part ; sur une ligne, une barre qui laisse < 160 px au texte ou couvre plus
de la moitie du champ passe a cheval sur le bord haut (sans marge reservee).
Le DOM simule est celui de test_champ_ia (HARNAIS, jusqu'aux scenarios).
Temoin : la couche de la base (git show). Faute n6 : details par _d().
Run : & $PY tests/test_p1_champ_ia_ecarts.py   (depuis backend/)
"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND / "tests"))
import test_champ_ia as TC                                  # noqa: E402  (le module ne s'execute pas a l'import)

BASE = "5a31bdf"
NODE = shutil.which("node")
SRC = ROOT / "frontend" / "shared" / "dz-champ-ia.js"
DIST = ROOT / "frontend" / "dist" / "shared" / "dz-champ-ia.js"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzp1ci_"))
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:700]
    except Exception as e:                                  # pragma: no cover
        return f"(detail illisible : {e})"


i = TC.HARNAIS.find("(async function () {")
PREAMBULE = TC.HARNAIS[:i] if i > 0 else ""

SCENARIOS = r"""
/* espions : l'intervalle et l'horloge ; la barre peut prendre une largeur mesuree */
const IV = [], CL = []; let ivId = 0, DECALE = 0;
window.setInterval = (f, ms) => { ivId++; IV.push({ id: ivId, ms }); return ivId; };
window.clearInterval = id => { CL.push(id); };
global.setInterval = window.setInterval; global.clearInterval = window.clearInterval;
const dateNow0 = Date.now; Date.now = () => dateNow0() + DECALE;
let BARRE_L = 0;
const gbr0 = Element.prototype.getBoundingClientRect;
Element.prototype.getBoundingClientRect = function () {
  const r = gbr0.call(this);
  if (BARRE_L && this.classList.contains("dzia-barre")) return Object.assign({}, r, { width: BARRE_L, right: r.left + BARRE_L });
  return r;
};
const ouverts = () => IV.filter(v => !CL.includes(v.id));
(async function () {
  const R = {};
  try {
  eval(fs.readFileSync(COUCHE, "utf8"));
  const A = window.DzChampIA;
  // (1) page vide : aucun balayage
  await pause(30);
  R.vide = { poses: IV.length, ouverts: ouverts().length };
  // un champ IA apparait (Quick) -> UN balayage de 800 ms
  const quick = el("div", { class: "quick" }, body);
  const fQ = ie(quick, "Prompt", "textarea");
  OBS.forEach(o => o._vider && o._vider()); await pause(80); A.marquer(document.body); A.synchroniser();
  R.pose = { marque: !!fQ.__dzia, poses: IV.length, ms: IV.map(v => v.ms), ouverts: ouverts().length,
    veille: A.dictee ? A.dictee.etat().veille : null };
  // un second champ : pas de second balayage
  const f2 = ie(quick, "Prompt", "textarea"); A.marquer(document.body); A.synchroniser();
  R.second = { poses: IV.length, ouverts: ouverts().length };
  // les champs disparaissent -> le balayage s'arrete
  body.removeChild(quick); A.synchroniser();
  R.retire = { ouverts: ouverts().length, arrets: CL.length, veille: A.dictee ? A.dictee.etat().veille : null };
  // pagehide / pageshow avec un champ suivi
  const q2 = el("div", {}, body); const f3 = ie(q2, "Prompt", "textarea"); A.marquer(document.body); A.synchroniser();
  const avantPH = ouverts().length;
  Noeud.prototype.dispatchEvent.call(window, new Event("pagehide"));
  const apresPH = ouverts().length;
  Noeud.prototype.dispatchEvent.call(window, new Event("pageshow"));
  R.page = { avant: avantPH, hide: apresPH, show: ouverts().length };
  body.removeChild(q2); A.synchroniser();

  // (3) page a part : les regles SANS page n'y sont pas essayees
  body.textContent = ""; window.location.pathname = "/vectorlab/";
  const hv = el("div", {}, body);
  const tAi = el("textarea", { placeholder: "AI prompt (regle sans page)" }, hv);
  const tIa = el("textarea", { id: "iaTexte", rows: "2" }, hv, { left: 425, top: 348, width: 312, height: 40 });
  // (4) la barre MESUREE a l'ecran : 166 px
  BARRE_L = 166;
  A.marquer(document.body); A.synchroniser();
  const st = tIa.__dzia || {};
  const bIa = tIa.nextSibling, rbIa = bIa && bIa.getBoundingClientRect ? bIa.getBoundingClientRect() : null;
  R.aPart = { sansPage: !!tAi.__dzia, iaTexte: !!tIa.__dzia };
  R.etroit = { coin: !!st.coin, reserve: st.reserve || null, padR: tIa.style.paddingRight || "", top: rbIa ? rbIa.top : null,
    attendu: 348 - (rbIa ? rbIa.height : 0) / 2 };
  // temoin : l'application principale (/) essaie bien la regle sans page ; un champ LARGE garde sa reserve a droite
  body.textContent = ""; window.location.pathname = "/";
  const hs = el("div", {}, body);
  const tAi2 = el("textarea", { placeholder: "AI prompt (spa)" }, hs);
  const large = el("input", { placeholder: "Describe an image to create (large)" }, hs, { left: 10, top: 10, width: 700, height: 30 });
  A.marquer(document.body); A.synchroniser();
  const sl = large.__dzia || {};
  R.spa = { sansPage: !!tAi2.__dzia, largeCoin: !!sl.coin, largeReserve: sl.reserve || null };
  BARRE_L = 0;

  // (2) dictee : available:false expire, et un champ neuf l'oublie
  body.textContent = ""; window.location.pathname = "/";
  const bd = el("div", {}, body);
  const ta = el("textarea", { placeholder: "Describe an image to create… (dictee)" }, bd);
  window.navigator = NAV; window.MediaRecorder = FauxMR; window.Blob = FauxBlob; window.FormData = FauxFD;
  window.HTMLTextAreaElement = protoValeur(); window.HTMLInputElement = protoValeur();
  A.marquer(document.body); await pause(30); A.synchroniser();
  const micro = () => { const b = ta.nextSibling; return b && b.querySelector ? b.querySelector(".dzia-micro") : null; };
  DICT["/api/dictation/estimate"] = () => [200, { duration_s: 5, provider: null, usd: 0, available: false, reason: "Aucune cle de transcription." }];
  micro().click(); await pause(20); micro().click(); await pause(60);
  const e0 = A.dictee.etat();
  R.indispo = { raison: e0.indispo, dis: micro().getAttribute("aria-disabled") };
  DECALE = 29000; A.synchroniser();
  R.a29 = { raison: A.dictee.etat().indispo, dis: micro().getAttribute("aria-disabled") };
  DECALE = 31000; A.synchroniser();
  R.a31 = { raison: A.dictee.etat().indispo, dis: micro().getAttribute("aria-disabled") };
  // a nouveau indisponible, puis un champ NEUF est habille (retour des Reglages) -> oubli
  DECALE = 0;
  micro().click(); await pause(20); micro().click(); await pause(60);
  const r1 = A.dictee.etat().indispo;
  const neuf = el("textarea", { placeholder: "Describe an image to create… (neuf)" }, bd);
  A.marquer(document.body); A.synchroniser();
  R.neuf = { avant: r1, apres: A.dictee.etat().indispo, marque: !!neuf.__dzia };
  } catch (e) { R.erreur = String(e && e.stack || e).slice(0, 600); }
  process.stdout.write(JSON.stringify(R), () => process.exit(0));
})();
"""


def _jouer(couche_txt, nom):
    c = TMP / (nom + "_couche.js")
    c.write_text(couche_txt, encoding="utf-8")
    h = TMP / (nom + "_h.js")
    h.write_text(PREAMBULE + SCENARIOS, encoding="utf-8")
    r = subprocess.run([NODE, str(h), str(c)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    try:
        return json.loads(r.stdout), r.stderr
    except Exception:
        return None, (r.stderr or "")[-500:] + (r.stdout or "")[:300]


neuf_txt = SRC.read_bytes().decode("utf-8")
vieux_txt = subprocess.run(["git", "show", f"{BASE}:frontend/shared/dz-champ-ia.js"], cwd=ROOT, capture_output=True).stdout.decode("utf-8")

print("\n[0] preconditions et temoin (couche de %s)" % BASE)
check("0.1 node, preambule du harnais de test_champ_ia, couche de base", bool(NODE) and len(PREAMBULE) > 5000 and len(vieux_txt) > 20000,
      _d(len(PREAMBULE), len(vieux_txt)))
N, errn = _jouer(neuf_txt, "neuf")
O, erro = _jouer(vieux_txt, "vieux")
check("0.2 les scenarios s'executent sur la couche courante", isinstance(N, dict) and "erreur" not in N, _d(errn, N and N.get("erreur")))
check("0.3 et sur la couche de base (temoin)", isinstance(O, dict) and "erreur" not in O, _d(erro, O and O.get("erreur")))
N = N if isinstance(N, dict) else {}
O = O if isinstance(O, dict) else {}
check("0.4 TEMOIN (1) : a la base, un balayage pose sur une page VIDE, et jamais arrete apres le retrait des champs",
      (O.get("vide") or {}).get("ouverts") == 1 and (O.get("retire") or {}).get("ouverts") == 1, _d(O.get("vide"), O.get("retire")))
check("0.5 TEMOIN (3) : a la base, la regle sans page marque un champ de /vectorlab/",
      (O.get("aPart") or {}).get("sansPage") is True, _d(O.get("aPart")))
check("0.6 TEMOIN (4) : a la base, #iaTexte garde la barre DANS le champ (reserve a droite de 166 px, pas a cheval)",
      (O.get("etroit") or {}).get("coin") is False and str((O.get("etroit") or {}).get("reserve")).startswith("r166"), _d(O.get("etroit")))
check("0.7 TEMOIN (2) : a la base, l'indisponibilite est encore la 31 s apres (micro grise)",
      (O.get("a31") or {}).get("raison") and (O.get("a31") or {}).get("dis") == "true", _d(O.get("a31")))

print("\n[1] le balayage de 800 ms ne vit que tant qu'un champ est suivi")
check("1.1 page vide : aucun balayage pose", N.get("vide") == {"poses": 0, "ouverts": 0}, _d(N.get("vide")))
check("1.2 un champ IA : UN balayage de 800 ms, dit par l'etat", (N.get("pose") or {}) == {"marque": True, "poses": 1, "ms": [800], "ouverts": 1, "veille": True},
      _d(N.get("pose")))
check("1.3 un second champ : pas de second balayage", N.get("second") == {"poses": 1, "ouverts": 1}, _d(N.get("second")))
check("1.4 plus aucun champ : clearInterval, l'etat le dit", (N.get("retire") or {}).get("ouverts") == 0 and (N.get("retire") or {}).get("arrets", 0) >= 1
      and (N.get("retire") or {}).get("veille") is False, _d(N.get("retire")))
check("1.5 pagehide l'arrete, pageshow le reprend (un champ suivi)", N.get("page") == {"avant": 1, "hide": 0, "show": 1}, _d(N.get("page")))

print("\n[2] la dictee : une indisponibilite expire, un champ neuf l'oublie")
check("2.1 available:false : raison retenue, micro grise", (N.get("indispo") or {}).get("raison") and (N.get("indispo") or {}).get("dis") == "true",
      _d(N.get("indispo")))
check("2.2 29 s apres : toujours indisponible", (N.get("a29") or {}).get("raison") and (N.get("a29") or {}).get("dis") == "true", _d(N.get("a29")))
check("2.3 31 s apres : oubliee, le micro redevient cliquable (sans focus)", (N.get("a31") or {}).get("raison") == ""
      and (N.get("a31") or {}).get("dis") != "true", _d(N.get("a31")))
check("2.4 un champ IA neuf (retour des Reglages) oublie aussitot l'indisponibilite",
      bool((N.get("neuf") or {}).get("avant")) and (N.get("neuf") or {}).get("apres") == "" and (N.get("neuf") or {}).get("marque") is True,
      _d(N.get("neuf")))

print("\n[3] les regles sans page restent dans l'application principale")
check("3.1 /vectorlab/ : la regle sans page ne marque rien, #iaTexte est marque", N.get("aPart") == {"sansPage": False, "iaTexte": True},
      _d(N.get("aPart")))
check("3.2 temoin : sur /, la meme regle marque son champ", (N.get("spa") or {}).get("sansPage") is True, _d(N.get("spa")))

print("\n[4] la barre d'un champ etroit ne recouvre plus le texte")
e = N.get("etroit") or {}
check("4.1 #iaTexte (312 x 40, barre 166) : a cheval sur le bord haut, aucune reserve de marge a droite",
      e.get("coin") is True and e.get("reserve") is None and not str(e.get("padR") or "").startswith("1"), _d(e))
check("4.2 et la barre est posee a cheval sur le bord haut (top = haut du champ - demi-hauteur)",
      e.get("top") is not None and abs(e.get("top") - e.get("attendu")) < 1, _d(e))
check("4.3 temoin : un champ LARGE (700 px) garde la barre dans le champ, marge reservee a droite",
      (N.get("spa") or {}).get("largeCoin") is False and str((N.get("spa") or {}).get("largeReserve")).startswith("r166"), _d(N.get("spa")))

print("\n[5] la copie servie")
check("5.1 frontend/dist/shared/dz-champ-ia.js == frontend/shared (octet pour octet)", SRC.read_bytes() == DIST.read_bytes(), "")
_nc = subprocess.run([NODE, "--check", str(SRC)], capture_output=True, text=True) if NODE else None
check("5.2 node --check", _nc is not None and _nc.returncode == 0, _d(_nc.stderr[-300:] if _nc else ""))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
