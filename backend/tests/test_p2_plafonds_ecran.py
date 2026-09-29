# -*- coding: utf-8 -*-
"""Tache #16, PR 2/2 (plan Settings T7, 29/09/2026) — les plafonds mensuels COTE NAVIGATEUR.
1. La couche /shared/dz-plafonds.js (source frontend/shared, copie dist octet pour octet) chargee par la SPA et les
   huit pages a part, EXECUTEE sous node : le 402 `dz_plafond` ouvre le dialogue maison, « Tirer quand meme » rejoue la
   MEME requete avec `X-DZ-Plafond: confirme` ; « Annuler » rend un 402 au detail LISIBLE ; un autre 402 passe intact ;
   les demandes simultanees se suivent ; l'alerte au seuil est dite une fois par mois et par onglet.
2. Les sections P2pl1, P2pl2 du maillon montage : DzPlafonds sous la grille des tarifs, le global en LECTURE (une seule
   verite : « Monthly budget cap »), les plafonds par moteur et le seuil en ecriture.
Temoin : la base 7b714b7 (PR 1 fusionnee) n'a ni la couche, ni les balises, ni DzPlafonds.
Run : & $PY tests/test_p2_plafonds_ecran.py   (depuis backend/)"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(BACKEND))
import patch_bundle_montage as P                              # noqa: E402

BASE = "7b714b7"
NODE = shutil.which("node")
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
SRC = ROOT / "frontend" / "shared" / "dz-plafonds.js"
DIST = ROOT / "frontend" / "dist" / "shared" / "dz-plafonds.js"
BALISE = '<script src="/shared/dz-plafonds.js"></script>'
PAGES = ["frontend/dist/index.html", "frontend/atelier/index.html", "frontend/cardforge/index.html",
         "frontend/etabli/index.html", "frontend/materialforge/index.html", "frontend/spritelab/index.html",
         "frontend/studio3d/index.html", "frontend/tilelab/index.html", "frontend/vectorlab/index.html"]
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


def _git(chemin):
    r = subprocess.run(["git", "show", f"{BASE}:{chemin}"], cwd=ROOT, capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


print("\n[0] temoin : la base %s" % BASE)
vieux = _git("frontend/dist/assets/index-BEOJX8L5.js") or ""
check("0.1 TEMOIN : ni couche, ni balise, ni DzPlafonds dans la base",
      _git("frontend/shared/dz-plafonds.js") is None and all(BALISE not in (_git(p) or "") for p in PAGES)
      and vieux.count("function DzPlafonds(") == 0 and vieux.count('"✓ Saved"}):null]})]});}function xm(') == 1, "")

print("\n[1] la couche partagee et ses balises")
src = SRC.read_bytes() if SRC.is_file() else b""
check("1.1 deux copies identiques a l'octet (shared = dist/shared)", bool(src) and DIST.is_file() and DIST.read_bytes() == src, "")
check("1.2 fins de ligne 100 % CRLF", src.count(b"\n") == src.count(b"\r\n") > 0, "")
for p in PAGES:
    t = (ROOT / p).read_text(encoding="utf-8")
    i = t.find(BALISE)
    autres = [j for j in (t.find('/shared/dialogue.js"'), t.find('/shared/dz-champ-ia.js"')) if j >= 0]
    check(f"1.3 {p} : balise x1, AVANT les autres couches partagees", t.count(BALISE) == 1 and autres and i < min(autres), _d(t.count(BALISE)))
spa = (ROOT / PAGES[0]).read_text(encoding="utf-8")
check("1.4 SPA : script CLASSIQUE (execute avant le module du bundle, donc avant tout fetch de l'app)",
      BALISE in spa and 'type="module"' not in BALISE, "")
nc = subprocess.run([NODE, "--check", str(SRC)], capture_output=True, text=True) if NODE else None
check("1.5 node --check de la couche", nc is not None and nc.returncode == 0, _d(nc.stderr[-300:] if nc else "pas de node"))

print("\n[2] la couche sous node")
HARNAIS = r"""
const journal = [], dialogues = [], minuteries = [];
let ouverts = 0, maxOuverts = 0, reponse = true, etatRendu = null;
const reponses = {};
globalThis.window = globalThis;
globalThis.location = { href: 'http://127.0.0.1:8765/' };
globalThis.sessionStorage = (() => { const m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); } }; })();
const el = () => ({ style: {}, attrs: {}, kids: [], setAttribute(k, v) { this.attrs[k] = v; }, appendChild(c) { this.kids.push(c); c.parentNode = this; return c; }, removeChild(c) { this.kids = this.kids.filter(x => x !== c); } });
globalThis.document = { createElement: el, body: el(), documentElement: el() };
globalThis.setTimeout = (f, ms) => { minuteries.push({ f, ms }); return minuteries.length; };
globalThis.clearTimeout = () => {};
globalThis.fetch = async (i, o) => {
  const req = (i instanceof Request) ? i : new Request(new URL(i, 'http://127.0.0.1:8765/'), o);
  const corps = await req.clone().text();
  journal.push({ url: new URL(req.url).pathname, methode: req.method, entete: req.headers.get('X-DZ-Plafond'), corps });
  const cle = new URL(req.url).pathname;
  if (cle === '/api/reglages/plafonds/etat') return new Response(JSON.stringify(etatRendu), { status: 200 });
  const r = reponses[cle];
  if (!r) return new Response('{}', { status: 200 });
  if (req.headers.get('X-DZ-Plafond') === 'confirme') return new Response('{"images":["a.png"]}', { status: 200 });
  return new Response(JSON.stringify(r.corps), { status: r.statut, headers: { 'Content-Type': 'application/json' } });
};
globalThis.__dzDialogue = { confirmer: async (m, o) => { ouverts++; maxOuverts = Math.max(maxOuverts, ouverts); dialogues.push({ m, o });
  await new Promise(r => setImmediate(r)); ouverts--; return reponse; } };
require(process.argv[2]);
const D = { motif: 'global', moteur: '', categorie: 'cartes', deja_usd: 0, devis_usd: 0.006, plafond_usd: 0.001,
  message: "Plafond mensuel atteint : toutes dépenses confondues a déjà coûté 0,00 $ ce mois-ci ; ce tir (écran « cartes ») ajouterait 0,006 $ et passerait au-dessus de 0,001 $. Confirmez pour tirer quand même, ou relevez le plafond dans Réglages → Pricing & budget." };
reponses['/api/images/generate'] = { statut: 402, corps: { detail: { dz_plafond: D } } };
reponses['/api/dictation'] = { statut: 402, corps: { detail: "Coût recalculé 0,0200 $ supérieur au plafond accepté" } };
(async () => {
  const out = {};
  const corps = JSON.stringify({ prompt: 'un phare', n: 2 });
  let r = await fetch('/api/images/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: corps });
  out.a = { statut: r.status, json: await r.json(), journal: journal.splice(0), dialogues: dialogues.splice(0) };
  reponse = false;
  r = await fetch('/api/images/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: corps });
  out.b = { statut: r.status, json: await r.json(), journal: journal.splice(0), dialogues: dialogues.length };
  dialogues.splice(0);
  r = await fetch('/api/dictation', { method: 'POST', body: 'x' });
  out.c = { statut: r.status, json: await r.json(), journal: journal.splice(0), dialogues: dialogues.splice(0).length };
  reponse = true;
  r = await fetch(new Request('http://127.0.0.1:8765/api/images/generate', { method: 'POST', body: corps, headers: { 'X-Autre': '1' } }));
  out.d = { statut: r.status, journal: journal.splice(0) };
  dialogues.splice(0); ouverts = 0; maxOuverts = 0;
  const rs = await Promise.all([1, 2, 3].map(() => fetch('/api/images/generate', { method: 'POST', body: corps })));
  out.e = { statuts: rs.map(x => x.status), maxOuverts, dialogues: dialogues.splice(0).length };
  journal.splice(0); minuteries.splice(0);
  await fetch('/api/music', { method: 'GET' });
  const apresGet = minuteries.filter(m => m.ms === window.__dzPlafonds.differeMs).length;
  await fetch('/api/reglages/plafonds', { method: 'POST', body: '{}' });
  const apresReglages = minuteries.filter(m => m.ms === window.__dzPlafonds.differeMs).length;
  await fetch('/api/audio/music', { method: 'POST', body: '{}' });
  const apresPost = minuteries.filter(m => m.ms === window.__dzPlafonds.differeMs).length;
  out.f = { apresGet, apresReglages, apresPost };
  etatRendu = { mois: '2026-09', alerte: ['global', 'fal'], plafonds: { alerte_pct: 80 },
    global: { pct: 84.2, effectif_usd: 4.21, plafond_usd: 5 }, par_moteur: { fal: { pct: 90, effectif_usd: 0.9, plafond_usd: 1 } } };
  const n1 = await window.__dzPlafonds.verifierAlerte();
  const bandeaux = document.body.kids.filter(k => k.attrs['data-dz-plafond-alerte']).length;
  const n2 = await window.__dzPlafonds.verifierAlerte();
  out.g = { n1, n2, bandeaux };
  const dlg = globalThis.__dzDialogue; delete globalThis.__dzDialogue; journal.splice(0);
  r = await fetch('/api/images/generate', { method: 'POST', body: corps });
  out.i = { statut: r.status, json: await r.json(), appels: journal.splice(0).length };
  globalThis.__dzDialogue = dlg;
  out.h = [0, 0.006, 0.001, 0.1, 2.5, 0.05, 0.075, 12.345, 0.00012].map(window.__dzPlafonds.usd);
  process.stdout.write(JSON.stringify(out));
})().catch(e => { process.stdout.write(JSON.stringify({ erreur: String(e && e.stack || e) })); });
"""
tmp = pathlib.Path(tempfile.mkdtemp()) / "h.js"
tmp.write_text(HARNAIS, encoding="utf-8")
r = subprocess.run([NODE, str(tmp), str(SRC)], capture_output=True, text=True, encoding="utf-8") if NODE else None
try:
    o = json.loads(r.stdout) if r else {}
except Exception:                                             # noqa: BLE001
    o = {"erreur": (r.stdout + r.stderr)[-500:] if r else "pas de node"}
check("2.0 le harnais tourne", "erreur" not in o, _d(o.get("erreur")))
a = o.get("a", {})
ja = a.get("journal", [])
check("2.1 402 dz_plafond + « Tirer quand meme » : l'appelant recoit la reponse du REJEU (200)", a.get("statut") == 200
      and a.get("json") == {"images": ["a.png"]}, _d(a.get("statut"), a.get("json")))
check("2.2 le rejeu est la MEME requete (methode, corps) avec X-DZ-Plafond: confirme ; la premiere n'en avait pas",
      len(ja) == 2 and ja[0]["entete"] is None and ja[1]["entete"] == "confirme" and ja[1]["methode"] == "POST"
      and ja[1]["corps"] == ja[0]["corps"] == '{"prompt":"un phare","n":2}', _d(ja))
dg = (a.get("dialogues") or [{}])[0]
check("2.3 le dialogue maison dit le message du serveur, titre et boutons explicites",
      dg.get("m", "").startswith("Plafond mensuel atteint") and dg.get("o") == {"titre": "Plafond de dépense mensuel",
      "ok": "Tirer quand même", "annuler": "Annuler"}, _d(dg))
b = o.get("b", {})
check("2.4 « Annuler » : 402, detail = CHAINE lisible, qui dit que rien n'est parti ; aucun rejeu",
      b.get("statut") == 402 and isinstance(b.get("json", {}).get("detail"), str)
      and "rien n'a été envoyé" in b["json"]["detail"] and "0,006 $" in b["json"]["detail"]
      and "Confirmez" not in b["json"]["detail"] and len(b.get("journal", [])) == 1, _d(b))
c = o.get("c", {})
check("2.5 un AUTRE 402 (garde par requete) passe intact, sans dialogue", c.get("statut") == 402 and c.get("dialogues") == 0
      and c.get("json") == {"detail": "Coût recalculé 0,0200 $ supérieur au plafond accepté"} and len(c.get("journal", [])) == 1, _d(c))
dj = o.get("d", {}).get("journal", [])
check("2.6 une Request en entree : corps et en-tetes d'origine conserves au rejeu", o.get("d", {}).get("statut") == 200
      and len(dj) == 2 and dj[1]["entete"] == "confirme" and dj[1]["corps"] == dj[0]["corps"] != "", _d(o.get("d")))
e = o.get("e", {})
check("2.7 trois 402 simultanes : trois dialogues, jamais deux ouverts a la fois", e.get("statuts") == [200, 200, 200]
      and e.get("dialogues") == 3 and e.get("maxOuverts") == 1, _d(e))
f = o.get("f", {})
check("2.8 alerte planifiee apres une ECRITURE /api reussie, pas apres un GET ni /api/reglages",
      f == {"apresGet": 0, "apresReglages": 0, "apresPost": 1}, _d(f))
g = o.get("g", {})
check("2.9 alerte : deux plafonds au seuil dits dans UN bandeau, en clair", g.get("bandeaux") == 1 and g.get("n1") == [
      "plafond global : 84,2 % (4,21 $ sur 5,00 $)", "moteur « fal » : 90 % (0,90 $ sur 1,00 $)"], _d(g))
check("2.10 alerte : une fois par mois et par onglet (second passage muet)", g.get("n2") == [], _d(g))
i_ = o.get("i", {})
check("2.12 sans dialogue maison : REFUS (aucun dialogue natif, aucun rejeu), 402 lisible", i_.get("statut") == 402
      and i_.get("appels") == 1 and "rien n'a été envoyé" in str(i_.get("json", {}).get("detail")), _d(i_))
from app.services import plafonds as PL                      # noqa: E402
vals = [0, 0.006, 0.001, 0.1, 2.5, 0.05, 0.075, 12.345, 0.00012]
check("2.11 montants : la couche formate comme le serveur (plafonds._fr)", o.get("h") == [PL._fr(v) + " $" for v in vals],
      _d(o.get("h"), [PL._fr(v) for v in vals]))

print("\n[3] les sections du bundle")
raw = BUNDLE.read_bytes()
s = raw.decode("utf-8")
bak = BAK.read_bytes().decode("utf-8") if BAK.is_file() else ""
SEC = {t: (a_, r_) for t, a_, r_ in P.PATCHES if t.startswith("P2pl")}
check("3.1 deux sections P2pl, en QUEUE de PATCHES", list(SEC) == ["P2pl1-dzplafonds-sous-la-grille-des-tarifs",
      "P2pl2-la-grille-previent-les-plafonds"] and [t for t, _a, _r in P.PATCHES[-2:]] == list(SEC), _d(list(SEC)))
for t, (a_, r_) in SEC.items():
    check(f"3.x {t} : ancre x1 dans .bak_montage, touchee par aucune autre section, remplacement x1 livre, sans saut de ligne",
          bak.count(a_) == 1 and sum(1 for t2, a2, r2 in P.PATCHES if t2 != t and (a_ in a2 or a_ in r2)) == 0
          and s.count(r_) == 1 and "\n" not in r_ and "\r" not in r_, _d(bak.count(a_), s.count(r_)))
dz = s[s.find("function DzPlafonds("):s.find("function xm(")]
check("3.2 DzPlafonds rendu en dernier enfant de la grille des tarifs", s.count(':null]}),r.jsx(DzPlafonds,{})]});}') == 1, "")
check("3.3 il lit l'etat et ecrit les plafonds par /api/reglages, et seulement la",
      dz.count("fetch('/api/reglages/plafonds/etat')") == 1 and dz.count("fetch('/api/reglages/plafonds',{method:'POST'") == 1
      and dz.count("fetch(") == 2, "")
check("3.4 une seule verite pour le global : DzPlafonds ne l'ecrit JAMAIS (body = par_moteur + alerte_pct)",
      "global_usd" not in dz and dz.count("body:JSON.stringify({par_moteur:par,alerte_pct:") == 1, "")
check("3.5 l'enregistrement de la grille previent DzPlafonds, qui ecoute (et se desabonne)",
      s.count("setSaved(!0);try{window.dispatchEvent(new Event('dz-plafonds'))}catch(z){}") == 1
      and dz.count("window.addEventListener('dz-plafonds',h)") == 1 and dz.count("window.removeEventListener('dz-plafonds',h)") == 1, "")
r1 = SEC["P2pl1-dzplafonds-sous-la-grille-des-tarifs"][1]
check("3.6 tout bouton et tout champ porte un title (E-12)", r1.count("r.jsx(K,{") == 1 and r1.count("r.jsx('input',{") == 2
      and r1.count("title:") >= 5, _d(r1.count("title:")))
check("3.7 fins de ligne du bundle : 100 % CRLF", raw.count(b"\n") == raw.count(b"\r\n"), "")
nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("3.8 node --check du bundle entier", nc is not None and nc.returncode == 0, _d(nc.stderr[-300:] if nc else ""))
i, j = s.find("function dzUsd("), s.find("function DzPlafonds(")
tmp2 = pathlib.Path(tempfile.mkdtemp()) / "u.js"
tmp2.write_text(s[i:j] + "\nprocess.stdout.write(JSON.stringify(%s.map(dzUsd)))" % json.dumps(vals), encoding="utf-8")
r2 = subprocess.run([NODE, str(tmp2)], capture_output=True, text=True, encoding="utf-8") if NODE and 0 <= i < j else None
try:
    u = json.loads(r2.stdout) if r2 else None
except Exception:                                             # noqa: BLE001
    u = None
check("3.9 dzUsd (ecran) = usd (couche) = _fr (serveur)", u == o.get("h") == [PL._fr(v) + " $" for v in vals], _d(u))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
