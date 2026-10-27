# -*- coding: utf-8 -*-
"""t219 (Menus : Réglages, 15/10/2026) — les pastilles de l'en-tête ouvrent la BONNE rubrique des Réglages.

Défaut relevé sur 7a104ba2 : la pastille des dépenses et celle des clés (fal / HeyGen / voix) faisaient
`onClick:()=>i&&i("settings")`. Réglages (`xm`) ne lisait sa rubrique qu'au montage (`vn("section")`, sinon
« accounts ») : un clic ouvrait donc Comptes connectés, et un Réglages déjà ouvert ne bougeait pas du tout.

Ce que ce banc garde :
  [A] `dzOuvrirReglages(section, aller)` sous node, avec une fausse fenêtre : écrit `?section=` par replaceState (les
      autres paramètres gardés), émet `dz-reglages-section` {section}, PUIS appelle aller("settings") — dans cet ordre ;
      sans `aller`, rien ne lève ;
  [B] `dzReglagesEcoute(a)` (l'effet de `xm`) : une rubrique connue de `ym` → a(rubrique) (Réglages déjà ouvert change
      de rubrique), une inconnue est ignorée, le nettoyage retire l'écouteur ;
  [C] sites : pastille des dépenses → « pricing », pastille des clés → « keys », palette « Réglages — comptes » →
      « accounts » et « Réglages — clés » → « keys » ; plus aucun `i&&i("settings")` ; `xm` monte l'écoute dans un
      useEffect sans dépendance ; la bulle des dépenses annonce « Réglages → Tarifs et budget » ;
  [D] clé FR/EN `reglages.pastille.clic_tarifs` dans menus.json (une phrase FR = une traduction), catalogue à jour ;
  [E] maillon de queue `dzreglages` : sonde amont sur dzquick, octets, inverse exact, `avant_dzreglages` en tête
      d'`avant_dzquick`, comptes figés intacts (useState 731, v2.8.0 ×4, DzTracks 181), aucun .bak.
Run (depuis backend/) : & $PY tests/test_reglages_pastilles.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
const JOURNAL=[];const ECOUTE={};
const win={location:{href:"http://127.0.0.1:8799/?lang=fr&section=accounts#x"},
 history:{state:null,replaceState(st,t,u){JOURNAL.push(["url",String(u)]);win.location.href=String(u)}},
 addEventListener(n,f){(ECOUTE[n]=ECOUTE[n]||[]).push(f)},
 removeEventListener(n,f){ECOUTE[n]=(ECOUTE[n]||[]).filter(g=>g!==f)},
 dispatchEvent(ev){JOURNAL.push(["evt",ev.type,ev.detail]);(ECOUTE[ev.type]||[]).slice().forEach(f=>f(ev));return true}};
class CE{constructor(t,o){this.type=t;this.detail=o&&o.detail}}
const ym=["diag","coffre","appareils","keys","accounts","personas","espaces","branding","pack","defaults","paths","news","appearance","pricing"];
const ENV={window:win,CustomEvent:CE,URL,ym,console};
try{
 const SRC=tranche("function dzOuvrirReglages(","function xm(");
 const M=new Function("ENV","with(ENV){"+SRC+";return{dzOuvrirReglages,dzReglagesEcoute}}")(ENV);
 const A={};
 M.dzOuvrirReglages("pricing",v=>JOURNAL.push(["aller",v]));A.j1=JOURNAL.splice(0);
 A.href=win.location.href;
 let err=null;try{M.dzOuvrirReglages("keys")}catch(e){err=String(e)}A.sansAller=err;A.j2=JOURNAL.splice(0);
 OUT.A=A;
 const B={vus:[]};const nett=M.dzReglagesEcoute(k=>B.vus.push(k));
 B.n0=(ECOUTE["dz-reglages-section"]||[]).length;
 M.dzOuvrirReglages("pricing",()=>{});M.dzOuvrirReglages("zzz",()=>{});M.dzOuvrirReglages("keys",()=>{});
 win.dispatchEvent(new CE("dz-reglages-section",{}));
 nett();B.n1=(ECOUTE["dz-reglages-section"]||[]).length;
 M.dzOuvrirReglages("diag",()=>{});B.apres=B.vus.slice();B.nettType=typeof nett;
 OUT.B=B;
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));
"""

print("[A] dzOuvrirReglages sous node")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzreg_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(BUN_P.read_bytes())
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js")], capture_output=True, text=True, encoding="utf-8",
                    errors="replace")
try:
    OUT = json.loads(rn.stdout or "{}")
except ValueError:
    OUT = {"err": rn.stdout[-300:] + rn.stderr[-300:]}
check("A0 helpers extraits et exécutés", "err" not in OUT, str(OUT.get("err", ""))[:300] + rn.stderr[-200:])
A = OUT.get("A", {})
j1 = A.get("j1") or []
check("A1 ordre : URL, puis évènement, puis aller(\"settings\")", [e[0] for e in j1] == ["url", "evt", "aller"], repr(j1))
check("A2 ?section=pricing écrit, autres paramètres et ancre gardés",
      A.get("href") == "http://127.0.0.1:8799/?lang=fr&section=pricing#x", repr(A.get("href")))
check("A3 évènement dz-reglages-section {section:\"pricing\"}",
      len(j1) == 3 and j1[1][1] == "dz-reglages-section" and j1[1][2] == {"section": "pricing"}, repr(j1))
check("A4 aller(\"settings\")", len(j1) == 3 and j1[2] == ["aller", "settings"], repr(j1))
check("A5 sans aller : rien ne lève, URL et évènement quand même",
      A.get("sansAller") is None and [e[0] for e in (A.get("j2") or [])] == ["url", "evt"], repr(A))

print("[B] écoute de xm (Réglages déjà ouvert)")
B = OUT.get("B", {})
check("B1 un écouteur posé", B.get("n0") == 1, repr(B))
check("B2 rubriques connues suivies, inconnue et détail vide ignorés", B.get("vus") == ["pricing", "keys"], repr(B))
check("B3 nettoyage : écouteur retiré, plus rien de suivi", B.get("n1") == 0 and B.get("apres") == ["pricing", "keys"]
      and B.get("nettType") == "function", repr(B))

print("[C] sites")
PAST_DEP = 'r.jsxs("div",{title:__dzCoutBlanc(Cu).titre,onClick:()=>dzOuvrirReglages("pricing",i),'
PAST_CLE = 'title:dzT("coque.entete.ouvrir_cles"),onClick:()=>dzOuvrirReglages("keys",i),'
PAL_CPT = '{l:dzT("coque.palette.reglages_comptes"),icon:"dz-nav-reglages",go:()=>{n("settings"),t(),dzOuvrirReglages("accounts")}}'
PAL_CLE = '{l:dzT("coque.palette.reglages_cles"),icon:"dz-nav-reglages",go:()=>{n("settings"),t(),dzOuvrirReglages("keys")}}]'
check("C1 pastille des dépenses → pricing", BUNDLE.count(PAST_DEP) == 1)
check("C2 pastille des clés → keys", BUNDLE.count(PAST_CLE) == 1)
check("C3 palette « comptes » → accounts", BUNDLE.count(PAL_CPT) == 1)
check("C4 palette « clés » → keys", BUNDLE.count(PAL_CLE) == 1)
check("C5 plus aucun i&&i(\"settings\") dans l'en-tête", 'i&&i("settings")' not in BUNDLE)
check("C6 xm monte l'écoute (useEffect sans dépendance, après ses états)",
      BUNDLE.count('[l,d]=x.useState(null);x.useEffect(function(){return dzReglagesEcoute(a)},[]);return r.jsxs("div",'
                   '{style:{display:"grid",gridTemplateColumns:"240px 1fr"') == 1)
check("C7 la bulle des dépenses annonce Tarifs et budget",
      'titre:t+dzT("reglages.pastille.clic_tarifs")' in BUNDLE and 'dzT("reglages.depenses.clic_reglages")' not in BUNDLE)
check("C8 helpers ×1", BUNDLE.count("function dzOuvrirReglages(") == 1 and BUNDLE.count("function dzReglagesEcoute(") == 1)

print("[D] i18n")
cat = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
v = cat.get("reglages.pastille.clic_tarifs") or {}
check("D1 clé FR/EN dans menus.json", "Tarifs et budget" in v.get("fr", "") and "Pricing & budget" in v.get("en", ""), repr(v))
fr_en = {}
for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    try:
        for k, e in json.loads(f.read_text(encoding="utf-8")).items():
            if isinstance(e, dict) and "fr" in e and "en" in e and k != "reglages.pastille.clic_tarifs":
                fr_en.setdefault(e["fr"], set()).add(e["en"])
    except ValueError:
        pass
check("D2 une phrase FR = une traduction", v.get("fr") not in fr_en or fr_en[v["fr"]] == {v.get("en")})
check("D3 l'onglet garde « Tarifs et budget » / « Pricing & budget »", fr_en.get("Tarifs et budget") == {"Pricing & budget"})
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("D4 catalogue assemblé à jour (i18n_assembler --check)", ra.returncode == 0, (ra.stdout + ra.stderr)[-300:])

print("[E] maillon de queue dzreglages")
try:
    import patch_bundle_dzreglages as DR                              # noqa: E402
except ImportError as e:
    DR = None
    check("E0 maillon présent", False, str(e))
import _i18n_l1_aide as AIDE                                          # noqa: E402
import patch_bundle_dzquick as DQ                                     # noqa: E402
if DR:
    src = (RACINE / "scripts" / "patch_bundle_dzreglages.py").read_text(encoding="utf-8")
    check("E1 sonde amont sur dzquick", DR.SONDE_AMONT and DR.SONDE_AMONT[0][0] == "dzquick"
          and DR.SONDE_AMONT[0][1] == DQ.MARKER)
    check("E2 octets seulement", "read_text(" not in src and "write_text(" not in src)
    check("E3 marqueur ×1", BUNDLE.count(DR.MARKER) == 1)
    try:
        # t310 (27/10/2026) : le maillon dzwhatsapp, posé après, touche dzFuNeuves : le livré se lit vu d'avant dzwhatsapp
        avant = DR.defaire(AIDE.avant_dzwhatsapp(BUNDLE))
    except AssertionError as e:
        avant = str(e)
    try:
        rejoue = DR.appliquer(avant)
    except SystemExit as e:
        rejoue = str(e)
    check("E4 inverse exact : aller-retour à l'octet", DR.MARKER not in avant and rejoue == AIDE.avant_dzwhatsapp(BUNDLE))
    check("E5 l'avant a le défaut d'origine", avant.count('onClick:()=>i&&i("settings")') == 2
          and 'dz-reglages-section' not in avant)
    try:
        a1 = AIDE.avant_dzreglages(BUNDLE)
        a2 = AIDE.avant_dzquick(BUNDLE)
        a2_attendu = DQ.defaire(AIDE.avant_dzlogo(avant))  # dzlogo d'abord
    except Exception as e:                                            # noqa: BLE001
        a1 = a2 = repr(e); a2_attendu = None
    check("E6 avant_dzreglages rend l'avant (dzlogo, posé après, défait d'abord)", a1 == AIDE.avant_dzlogo(avant))
    check("E7 avant_dzquick défait dzreglages d'abord", a2 == a2_attendu)
    check("E8 avant_dzreglages sans marqueur : rendu tel quel", AIDE.avant_dzreglages(avant) == AIDE.avant_dzlogo(avant)
          if isinstance(avant, str) and DR.MARKER not in avant else False)
try:
    import json as _j
    _g1 = [p["remplace"] for p in _j.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
except (OSError, ValueError, KeyError):
    _g1 = []
_av = avant if DR and isinstance(avant, str) else ""
check("E12 aucune paire ne chevauche un remplacement G1 du maillon dzglyph (comptes égaux avant / après dzreglages)",
      bool(_g1) and bool(_av) and all(BUNDLE.count(x) == _av.count(x) for x in _g1),
      [x[:60] for x in _g1 if BUNDLE.count(x) != _av.count(x)][:3])
check("E9 comptes figés intacts", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181)
b = BUN_P.read_bytes()
check("E10 fins de ligne CRLF intactes", b.count(b"\r\n") > 15000 and b.count(b"\n") == b.count(b"\r\n"))
check("E11 aucun .bak_dzreglages laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzreglages")).exists())

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
