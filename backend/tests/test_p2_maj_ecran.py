# -*- coding: utf-8 -*-
"""Tache #18 (plan Settings T11, 29/09/2026) — la mise a jour COTE NAVIGATEUR.
1. La couche /shared/dz-maj.js (source frontend/shared, copie dist octet pour octet), chargee par la SPA seulement,
   EXECUTEE sous node : bandeau seulement si une version plus recente existe, « Plus tard » memorise PAR BALISE,
   stockage indisponible toleré, « Telecharger » lance en fond puis suit le pourcentage et dit le chemin, un refus du
   serveur est dit et le bouton rendu.
2. Le bloc version DzMaj dans l'en-tete du Diagnostic (section P2dg1 etendue).
Temoin : la base 6f935d7 n'a ni la couche, ni la balise, ni DzMaj.
Run : & $PY tests/test_p2_maj_ecran.py   (depuis backend/)"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
import patch_bundle_montage as P                              # noqa: E402
sys.path.insert(0, str(BACKEND / "tests"))
import _i18n_l1_aide as AIDE                                  # noqa: E402  t141 : les textes passent par dzT("cle")

BASE = "6f935d7"
NODE = shutil.which("node")
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
SRC = ROOT / "frontend" / "shared" / "dz-maj.js"
DIST = ROOT / "frontend" / "dist" / "shared" / "dz-maj.js"
BALISE = '<script src="/shared/dz-maj.js"></script>'
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:600]
    except Exception as e:                                    # pragma: no cover
        return f"(detail illisible : {e})"


def _git(ch):
    r = subprocess.run(["git", "show", f"{BASE}:{ch}"], cwd=ROOT, capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


print("\n[0] temoin : la base %s" % BASE)
vb = _git("frontend/dist/assets/index-BEOJX8L5.js") or ""
check("0.1 TEMOIN : ni couche, ni balise, ni DzMaj", _git("frontend/shared/dz-maj.js") is None
      and BALISE not in (_git("frontend/dist/index.html") or "") and "function DzMaj(" not in vb and vb, "")

print("\n[1] la couche et sa balise")
src = SRC.read_bytes() if SRC.is_file() else b""
check("1.1 deux copies identiques a l'octet, 100 % CRLF", bool(src) and DIST.read_bytes() == src and src.count(b"\n") == src.count(b"\r\n"), "")
spa = (ROOT / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
check("1.2 SPA : balise x1, script classique, apres la couche des plafonds", spa.count(BALISE) == 1
      and spa.find(BALISE) > spa.find('<script src="/shared/dz-plafonds.js"></script>') >= 0, "")
autres = [p for p in (ROOT / "frontend").glob("*/index.html") if p.parent.name != "dist" and BALISE in p.read_text(encoding="utf-8")]
check("1.3 les pages a part ne posent PAS de second bandeau", autres == [], _d([str(p) for p in autres]))
nc = subprocess.run([NODE, "--check", str(SRC)], capture_output=True, text=True) if NODE else None
check("1.4 node --check", nc is not None and nc.returncode == 0, _d(nc.stderr[-300:] if nc else "pas de node"))

print("\n[2] la couche sous node")
H = r"""
const appels = [], minuteries = [], intervalles = [];
let stockageCasse = false, reponseTel = { statut: 200, corps: { ok: true, lance: true } }, etats = [], etatMaj = null;
const mem = {};
globalThis.window = globalThis;
globalThis.localStorage = { getItem: k => { if (stockageCasse) throw new Error('interdit'); return k in mem ? mem[k] : null; },
  setItem: (k, v) => { if (stockageCasse) throw new Error('interdit'); mem[k] = String(v); } };
function el(tag) { return { tag, style: {}, attrs: {}, kids: [], textContent: '', disabled: false,
  setAttribute(k, v) { this.attrs[k] = v; }, appendChild(c) { this.kids.push(c); c.parentNode = this; return c; },
  removeChild(c) { this.kids = this.kids.filter(x => x !== c); c.parentNode = null; },
  remove() { if (this.parentNode) this.parentNode.removeChild(this); } }; }
globalThis.document = { createElement: el, body: el('body'), documentElement: el('html') };
globalThis.setTimeout = (f, ms) => { minuteries.push({ f, ms }); return 1; };
globalThis.setInterval = (f, ms) => { intervalles.push({ f, ms, actif: true }); return intervalles.length; };
globalThis.clearInterval = id => { intervalles[id - 1].actif = false; };
globalThis.fetch = async (u, o) => { appels.push([u, (o && o.method) || 'GET']);
  if (u === '/api/reglages/maj') return { ok: true, json: async () => etatMaj };
  if (u === '/api/reglages/maj/telecharger') return { ok: reponseTel.statut < 400, json: async () => reponseTel.corps };
  if (u === '/api/reglages/maj/telechargement') return { ok: true, json: async () => etats.shift() };
  return { ok: false, json: async () => ({}) }; };
require(process.argv[2]);
const pause = () => new Promise(r => setImmediate(r));
const bandeaux = () => document.body.kids.filter(k => k.attrs['data-dz-maj']);
const M = { disponible: true, tag: 'v9.1.0', installee: '2.8.0', url: 'https://github.com/hugboss1/DeepotusVideo/releases/tag/v9.1.0',
  asset: { nom: 'DeepotusVideoGen-Setup-9.1.0.exe', octets: 130400236, url: 'https://github.com/x' } };
(async () => {
  const out = {};
  out.depart = minuteries.map(m => m.ms);
  out.rien = window.__dzMaj.poser({ disponible: false, tag: 'v2.8.0' }) === null && bandeaux().length === 0;
  const w = window.__dzMaj.poser(M);
  out.texte = w.kids[0].textContent;
  out.enfants = w.kids.map(k => [k.tag, k.textContent, k.title || '', k.href || '']);
  const plus = w.kids.find(k => k.textContent === 'Plus tard');
  plus.onclick();
  out.apresPlusTard = { bandeaux: bandeaux().length, memo: mem['dz_maj_vu_v9.1.0'] || null,
    reposeMeme: window.__dzMaj.poser(M) === null, autreTag: !!window.__dzMaj.poser(Object.assign({}, M, { tag: 'v9.2.0' })) };
  document.body.kids = [];
  stockageCasse = true;
  const w2 = window.__dzMaj.poser(Object.assign({}, M, { tag: 'v9.3.0' }));
  let jete = null; try { w2.kids.find(k => k.textContent === 'Plus tard').onclick(); } catch (e) { jete = String(e); }
  out.stockageCasse = { pose: !!w2, jete, retire: bandeaux().length === 0 };
  stockageCasse = false;
  const w3 = window.__dzMaj.poser(Object.assign({}, M, { tag: 'v9.4.0' }));
  const dl = w3.kids.find(k => k.textContent === 'Télécharger');
  appels.length = 0;
  dl.onclick(); await pause(); await pause();
  out.post = appels.slice(); out.pendant = [dl.disabled, dl.textContent];
  const iv = intervalles[intervalles.length - 1];
  etats = [{ fini: false, octets: 65200118, total: 130400236 }, { fini: true, erreur: '', chemin: 'C:\\D\\telechargements\\Setup.exe' }];
  iv.f(); await pause(); await pause(); out.pct = dl.textContent;
  iv.f(); await pause(); await pause();
  out.fin = { texte: w3.kids[0].textContent, boutonRetire: !w3.kids.includes(dl), arret: iv.actif === false, rythme: iv.ms };
  document.body.kids = [];
  reponseTel = { statut: 404, corps: { detail: 'aucune mise à jour à télécharger' } };
  const w4 = window.__dzMaj.poser(Object.assign({}, M, { tag: 'v9.5.0' }));
  const dl4 = w4.kids.find(k => k.textContent === 'Télécharger');
  const nIv = intervalles.length;
  dl4.onclick(); await pause(); await pause(); await pause();
  out.refus = { texte: w4.kids[0].textContent, rendu: dl4.disabled === false && dl4.textContent === 'Réessayer', pasDeSuivi: intervalles.length === nIv };
  document.body.kids = [];
  etatMaj = Object.assign({}, M, { tag: 'v9.6.0' });
  await window.__dzMaj.verifier(); out.verifier = bandeaux().map(b => b.attrs['data-dz-maj']);
  process.stdout.write(JSON.stringify(out));
})().catch(e => process.stdout.write(JSON.stringify({ erreur: String(e && e.stack || e) })));
"""
tmp = pathlib.Path(tempfile.mkdtemp()) / "h.js"
tmp.write_text(H, encoding="utf-8")
r = subprocess.run([NODE, str(tmp), str(SRC)], capture_output=True, text=True, encoding="utf-8") if NODE else None
try:
    o = json.loads(r.stdout) if r else {}
except Exception:                                             # noqa: BLE001
    o = {"erreur": (r.stdout + r.stderr)[-500:] if r else "pas de node"}
check("2.0 le harnais tourne", "erreur" not in o, _d(o.get("erreur")))
check("2.1 une lecture du cache 2,5 s apres le chargement", o.get("depart") == [2500], _d(o.get("depart")))
check("2.2 rien a proposer : aucun bandeau", o.get("rien") is True, "")
check("2.3 le bandeau dit la version, l'installee, l'installeur et sa taille (124 Mo)",
      o.get("texte") == "Version v9.1.0 disponible (vous avez la 2.8.0). Installeur : DeepotusVideoGen-Setup-9.1.0.exe — 124 Mo.", _d(o.get("texte")))
en = o.get("enfants") or []
check("2.4 notes (lien GitHub), Telecharger et Plus tard, chacun avec un title", [e[1] for e in en[1:]] == ["Notes de version", "Télécharger", "Plus tard"]
      and all(e[2] for e in en[1:]) and en[1][3].startswith("https://github.com/"), _d(en))
pt = o.get("apresPlusTard") or {}
check("2.5 « Plus tard » : retire, memorise PAR BALISE ; la meme balise ne revient pas, une plus recente si",
      pt == {"bandeaux": 0, "memo": "1", "reposeMeme": True, "autreTag": True}, _d(pt))
check("2.6 stockage indisponible : le bandeau s'affiche et « Plus tard » le retire sans lever",
      o.get("stockageCasse") == {"pose": True, "jete": None, "retire": True}, _d(o.get("stockageCasse")))
check("2.7 « Telecharger » : UN POST, bouton desactive pendant", o.get("post") == [["/api/reglages/maj/telecharger", "POST"]]
      and (o.get("pendant") or [None])[0] is True, _d(o.get("post"), o.get("pendant")))
check("2.8 le pourcentage suit l'etat du serveur", o.get("pct") == "Téléchargement 50 %", _d(o.get("pct")))
fin = o.get("fin") or {}
check("2.9 fini : le chemin est dit, avec la consigne (fermer puis lancer) ; bouton retire, suivi arrete",
      fin.get("texte") == "Installeur enregistré : C:\\D\\telechargements\\Setup.exe — fermez l'application puis lancez-le."
      and fin.get("boutonRetire") is True and fin.get("arret") is True and fin.get("rythme") == 1200, _d(fin))
check("2.10 refus du serveur : le motif est dit, le bouton rendu, aucun suivi lance",
      o.get("refus") == {"texte": "Échec : aucune mise à jour à télécharger", "rendu": True, "pasDeSuivi": True}, _d(o.get("refus")))
check("2.11 verifier() : lit le cache et pose le bandeau", o.get("verifier") == ["v9.6.0"], _d(o.get("verifier")))

print("\n[3] DzMaj dans le Diagnostic")
s = BUNDLE.read_text(encoding="utf-8")
dz = s[s.find("function DzMaj("):s.find("function DzCoffre(")]   # #20 : DzCoffre suit DzMaj
check("3.1 DzMaj x1, rendu dans l'en-tete du Diagnostic juste apres le badge de version",
      s.count("function DzMaj(") == 1 and s.count("children:'v'+d.version}),r.jsx(DzMaj,{}),") == 1, "")
check("3.2 il lit le cache et force une verification, rien d'autre", dz.count("fetch('/api/reglages/maj')") == 1
      and dz.count("fetch('/api/reglages/maj/verifier',{method:'POST'})") == 1 and dz.count("fetch(") == 2, "")
check("3.3 une version trouvee par « Verifier » reveille le bandeau", dz.count("window.__dzMaj.poser(j)") == 1, "")
# t141 (08/10/2026) : la bulle passe par dzT ; la cle est epinglee DANS le title du bouton et son francais dit le dernier echec
check("3.4 le bouton porte un title qui dit le dernier echec", dz.count("r.jsx(K,{") == 1
      and 'title:dzT("reglages.maj.verifier_aide")+(m.erreur?dzT("reglages.maj.dernier_echec",{erreur:m.erreur}):\'\')' in dz
      and AIDE.fr("reglages.maj.dernier_echec", erreur="x") == " — dernier échec : x", "")
t1 = [r for t, a, r in P.PATCHES if t.startswith("P2dg1")][0]
# t141 : la traduction L1 (maillon APRES le montage) a pose des dzT dans la section P2dg1 ; ce que le PATCHER a livre se
# controle sur le bundle d'avant la traduction (exactement reversible : test_i18n_l1). Lu en octets (la table est en CRLF).
s_av = AIDE.avant_i18n(BUNDLE.read_bytes().decode("utf-8"))
check("3.5 livre par la section P2dg1 (une seule verite du bloc Reglages)", "function DzMaj(" in t1 and s_av.count(t1) == 1, "")
nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("3.6 node --check du bundle entier", nc is not None and nc.returncode == 0, _d(nc.stderr[-300:] if nc else ""))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
