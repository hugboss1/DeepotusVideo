# -*- coding: utf-8 -*-
"""t328 tâche 5 (27/10/2026) — la diffusion WhatsApp d'un post dans le Planificateur : le maillon dzdiffusion et le
panneau partagé dz-diffusion-whatsapp.js.

Plan docs/superpowers/plans/2026-10-27-t328-diffusions-whatsapp.md (tâche 5).
[1] le maillon      scripts/patch_bundle_dzdiffusion.py : marqueur x1, aucun .bak_*, octets, --check « déjà appliqué »
                    (bundle inchangé), sondes (marqueurs whatsapppage et dzwhatsapp, épingles), 3 paires (ancre x1 dans la
                    vue d'avant, remplacement x1 dans le livré), hors couche, aller-retour exact, defaire rend l'octet du
                    bundle d'origine (827b35d1, aux CRLF d'extraction près), épingles intouchées, CRLF, node --check ;
[2] réversible      avant_dzdiffusion == defaire, appelé EN TÊTE de avant_whatsapppage ; la chaîne reste complète ;
[3] les paires      sous node, la fonction LIVRÉE DzPostComptes : un compte whatsapp listé et cochable (canal whatsapp),
                    le point de montage data-dz-diffusion et l'appel monter(nœud, post, {compte, espace, delai}) ; deux
                    comptes whatsapp : la ligne « un seul compte », pas de montage ; aucun : rien. La table _t connaît
                    whatsapp, Bu l'écarte ;
[4] livraison       shared == dist, balise dans index.html après dz-whatsapp-espace.js, chaque clé diffusion.* lue par le
                    module existe en FR et EN, assemblé à jour, confirmation par await window.__dzDialogue.confirmer( et
                    texte d'avertissement N3, aucun confirm natif, le banc node vert.
Run : & $PY tests/test_diffusion_ecran.py   (depuis backend/)
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import _i18n_l1_aide as AIDE  # noqa: E402
F = AIDE.fr

NODE = shutil.which("node")
GIT = shutil.which("git")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


ASSETS = REPO / "frontend" / "dist" / "assets"
BUNDLE = ASSETS / "index-BEOJX8L5.js"
RAW = BUNDLE.read_bytes()
B = RAW.decode("utf-8")
SH = REPO / "frontend" / "shared"
DI = REPO / "frontend" / "dist" / "shared"
MODULE = SH / "dz-diffusion-whatsapp.js"
MARKER = "/*dzdiffusion*/"
CONFIRMER = "await window.__dzDialogue.confirmer("
BASE = "827b35d1"                     # le bundle d'avant ce maillon (fin de la tâche 4)


def blocs(s):
    return [(m.start(), s.index("/*__DZ_%s_END__*/" % m.group(1)))
            for m in re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", s)]


def node(code):
    with tempfile.TemporaryDirectory() as _d:
        f = pathlib.Path(_d) / "h.js"
        f.write_text(code, "utf-8")
        p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except ValueError:
        return {"erreur": (p.stdout + p.stderr)[-800:]}


_SRC_ASSISTANT = (BACKEND / "tests" / "test_espace_assistant_ecran.py").read_text("utf-8")
FAUX_DOM = re.search(r'FAUX_DOM = r"""(.*?)"""', _SRC_ASSISTANT, re.S).group(1)
FAUX_REACT = re.search(r'FAUX_REACT = r"""(.*?)"""', _SRC_ASSISTANT, re.S).group(1)

# ── [1] le maillon ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[1] le maillon")
try:
    import patch_bundle_dzdiffusion as PM                 # noqa: E402
except Exception as e:                                   # noqa: BLE001
    PM = None
    check("1.0 le maillon patch_bundle_dzdiffusion existe", False, repr(e))
check("1.1 le marqueur une fois dans le bundle", B.count(MARKER) == 1, str(B.count(MARKER)))
check("1.2 aucun .bak_dzdiffusion laissé (le maillon a supprimé le sien : `version` reste le dernier)",
      not list(ASSETS.glob("*.bak_dzdiffusion")), str(list(ASSETS.glob("*.bak_dzdiffusion"))))
avant = ""
if PM:
    src = (REPO / "scripts" / "patch_bundle_dzdiffusion.py").read_text("utf-8")
    check("1.3 lecture et écriture en OCTETS", "read_text(" not in src and "write_text(" not in src
          and "read_bytes(" in src and "write_bytes(" in src)
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzdiffusion.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("1.4 --check : « déjà appliqué », bundle inchangé", r.returncode == 0 and "déjà appliqué" in r.stdout
          and BUNDLE.read_bytes() == RAW, r.stdout + r.stderr)
    r2 = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzdiffusion.py")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("1.5 rejoué : « déjà appliqué », appliqué UNE fois (octets inchangés)", r2.returncode == 0 and "déjà appliqué" in r2.stdout
          and BUNDLE.read_bytes() == RAW, r2.stdout + r2.stderr)
    check("1.6 sondes amont : marqueurs de whatsapppage et dzwhatsapp, épingles",
          ("whatsapppage", "/*whatsapppage*/", 1) in PM.SONDE_AMONT and ("dzwhatsapp", "/*dzwhatsapp*/", 1) in PM.SONDE_AMONT
          and ("useState", "x.useState(", 731) in PM.SONDE_AMONT and ("version", "v2.8.0", 4) in PM.SONDE_AMONT
          and ("montage", "DzTracks", 181) in PM.SONDE_AMONT and ("dialogue", CONFIRMER, 30) in PM.SONDE_AMONT)
    try:
        avant = PM.defaire(B) if MARKER in B else ""
    except AssertionError:
        avant = ""
    check("1.7 cinq paires ; chaque ancre une fois dans le bundle d'avant, chaque remplacement une fois dans le livré",
          lambda: len(PM.PAIRES) == 5 and bool(avant) and all(avant.count(a) == 1 and B.count(z) == 1 for a, z in PM.PAIRES))
    check("1.8 les paires n'ont aucune fin de ligne, n'ajoutent ni x.useState( ni confirmation",
          all("\n" not in a + z and "x.useState(" not in z and CONFIRMER not in z for a, z in PM.PAIRES))
    check("1.9 chaque ancre (vue d'avant) et chaque remplacement (livré) HORS de tout bloc de couche __DZ_*_BEGIN__",
          lambda: all(not (s0 <= B.index(z) <= e0) for _a, z in PM.PAIRES for s0, e0 in blocs(B))
          and all(not (s0 <= avant.index(a) <= e0) for a, _z in PM.PAIRES for s0, e0 in blocs(avant)))
    check("1.10 aller-retour exact : appliquer(defaire(B)) == B, defaire(B) sans marqueur ni montage",
          lambda: PM.appliquer(PM.defaire(B)) == B and MARKER not in PM.defaire(B)
          and "__dzDiffusionWhatsapp" not in PM.defaire(B) and "__dzWaCanal" not in PM.defaire(B))
    check("1.11 la vue d'avant porte encore whatsapppage et le filtre whatsapp de dzwhatsapp (le maillon se pose APRÈS)",
          lambda: PM.defaire(B).count("/*whatsapppage*/") == 1 and PM.defaire(B).count('return c.plateforme!=="whatsapp"}),pl:') == 1)
    if GIT:
        g = subprocess.run([GIT, "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(REPO))
        base = g.stdout if g.returncode == 0 else b""
        # fusion t320 : dzcapture (t315) et dzinspiration (t313) sont posés entre whatsapppage et ce maillon ; la vue
        # d'avant les trois (avant_dzcapture, qui défait d'abord dzdiffusion puis dzinspiration) est le bundle d'origine
        _vue = AIDE.avant_dzcapture(B) if hasattr(AIDE, "avant_dzcapture") else PM.defaire(B)
        check("1.12 defaire(livré) == le bundle d'origine (827b35d1), OCTET POUR OCTET aux CRLF d'extraction près",
              lambda: bool(base) and _vue.encode("utf-8").replace(b"\r\n", b"\n") == base.replace(b"\r\n", b"\n"))
    if avant:
        import importlib
        mordus = []
        for f in sorted((REPO / "scripts").glob("patch_bundle_*.py")):
            if f.stem == "patch_bundle_dzdiffusion":
                continue
            txt = f.read_text("utf-8", errors="replace")
            if "PAIRES" not in txt and "R_" not in txt:
                continue
            try:
                mod = importlib.import_module(f.stem)
            except BaseException:                         # noqa: BLE001 — un vieux maillon qui ne s'importe pas
                continue
            textes = [p[1] for p in (getattr(mod, "PAIRES", None) or []) if isinstance(p, tuple) and len(p) == 2 and isinstance(p[1], str)]
            textes += [v for k, v in vars(mod).items() if k.startswith("R_") and isinstance(v, str)]
            mordus += [f"{f.stem}:{z[:60]!r}" for z in textes if len(z) > 12 and avant.count(z) == 1 and B.count(z) != 1]
        check("1.16 aucun remplacement d'un maillon AMONT n'est mordu (chacun reste une fois, à l'octet)", not mordus, str(mordus[:5]))
    for amont in ("dzwhatsapp", "whatsapppage", "dzgardeclient"):
        ra = subprocess.run([sys.executable, str(REPO / "scripts" / f"patch_bundle_{amont}.py"), "--check"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
        check(f"1.17 le --check de l'amont {amont} dit encore « déjà appliqué », bundle inchangé",
              ra.returncode == 0 and "déjà appliqué" in ra.stdout and BUNDLE.read_bytes() == RAW, ra.stdout + ra.stderr)
for jeton, n in {"x.useState(": 731, "v2.8.0": 4, "DzTracks": 181, CONFIRMER: 30, "/*whatsapppage*/": 1, "/*dzwhatsapp*/": 1,
                 '{id:"whatsapp",': 1, "function DzPostComptes(": 1, "__dzDiffusionWhatsapp.monter(": 1}.items():
    check(f"1.13 compte {jeton!r} = {n}", B.count(jeton) == n, str(B.count(jeton)))
check("1.14 CRLF partout (en octets)", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
if NODE:
    with tempfile.TemporaryDirectory() as _d:
        t = pathlib.Path(_d) / "b.mjs"
        t.write_bytes(RAW)
        rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("1.15 node --check : le bundle PARSE", rc.returncode == 0, rc.stderr[-300:])

# ── [2] réversible ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[2] la chaîne inverse")
check("2.1 avant_dzdiffusion existe et rend defaire(B)", lambda: PM is not None and AIDE.avant_dzdiffusion(B) == PM.defaire(B))
check("2.2 avant_dzdiffusion sans marqueur : rendu tel quel", lambda: AIDE.avant_dzdiffusion(PM.defaire(B)) == PM.defaire(B))
check("2.3 avant_whatsapppage défait dzdiffusion D'ABORD, puis whatsapppage",
      lambda: MARKER not in AIDE.avant_whatsapppage(B) and "/*whatsapppage*/" not in AIDE.avant_whatsapppage(B)
      and AIDE.avant_whatsapppage(B) == AIDE.avant_whatsapppage(AIDE.avant_dzdiffusion(B)))
# fusion t320 : dzdiffusion est rejoué APRÈS dzcapture (t315) et dzinspiration (t313) : la queue de la chaîne ; son
# inverse ouvre donc avant_dzinspiration, que avant_dzcapture puis avant_whatsapppage appellent
check("2.4 l'appel est en TÊTE de avant_dzinspiration (avant le test du marqueur)",
      lambda: (lambda s: 0 <= s.find("avant_dzdiffusion(bundle)") < s.find("_m.MARKER not in bundle"))(
          (BACKEND / "tests" / "_i18n_l1_aide.py").read_text("utf-8").split("def avant_dzinspiration(", 1)[1].split("\ndef ", 1)[0]))
check("2.5 la chaîne reste complète (avant_dzwhatsapp et avant_dzgardeclient retirent aussi dzdiffusion)",
      lambda: MARKER not in AIDE.avant_dzwhatsapp(B) and "/*dzwhatsapp*/" not in AIDE.avant_dzwhatsapp(B)
      and MARKER not in AIDE.avant_dzgardeclient(B) and "/*dzgardeclient*/" not in AIDE.avant_dzgardeclient(B))

# ── [3] les paires ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[3] les paires")
PC = B[B.find("function DzPostComptes("):B.find("var DZ_ONB_ETAPES=")]
check("3.1 P1 : DzPostComptes remplace la liste filtrée (dzwhatsapp, intact) par la liste entière, juste après",
      bool(PC) and PC.count(";" + MARKER + "dzPcCache[esp].liste=j.comptes||[];maj()}") == 1
      and PC.index('return c.plateforme!=="whatsapp"}),pl:') < PC.index(MARKER))
check("3.2 P2 : le point de montage dans DzPostComptes, avant l'alerte « sans compte »",
      PC.count('"data-dz-diffusion":p.id') == 1 and PC.index("__dzDiffusionWhatsapp.monter(") < PC.index('"data-dz-post-sans-compte"'))
SONDE_PC = r"""
var dzPcCache={};var monts=[];
var LISTE=[{id:"c_t",plateforme:"telegram",libelle:"Telegram C",handle:"",disponible:true},
  {id:"c_w",plateforme:"whatsapp",libelle:"WhatsApp C",handle:"",disponible:true},
  {id:"c_w2",plateforme:"whatsapp",libelle:"WhatsApp D",handle:"",disponible:true}];
globalThis.fetch=function(u){return Promise.resolve({ok:true,status:200,json:function(){return Promise.resolve(
  {espace:"esp_c",comptes:LISTE,plateformes:{telegram:{libelle:"Telegram"},whatsapp:{libelle:"WhatsApp"}}})}})};
__PC__
(async function(){
 var R={};var changes=[];
 monter(DzPostComptes,{post:{id:"p1",espaceId:"esp_c",comptes:["c_w"]},onChange:function(v){changes.push(v)}});await attendre();
 R.listes=avec("data-dz-post-compte").map(function(n){return n.p["data-dz-post-compte"]});
 R.sans_module=avec("data-dz-diffusion").length;
 window.__dzDiffusionWhatsapp={monter:function(n,pid,o){monts.push([!!n&&n.tagName,pid,o])}};
 monter(DzPostComptes,{post:{id:"p1",espaceId:"esp_c",comptes:["c_w"]},onChange:function(v){changes.push(v)}});await attendre();
 var m=avec("data-dz-diffusion");R.montage=m.map(function(n){return [n.p["data-dz-diffusion"],n.t]});R.monts=monts.slice();
 var lab=avec("data-dz-post-compte","c_t")[0];var c=chercher(function(n){return n.t==="input"},lab)[0];c.p.onChange();R.change=changes[0]||null;
 monts=[];monter(DzPostComptes,{post:{id:"p2",espaceId:"esp_c",comptes:["c_w","c_w2"]},onChange:function(){}});await attendre();
 R.deux=[avec("data-dz-diffusion").length,avec("data-dz-diffusion-plusieurs").map(function(n){return texte(n)}),monts.length];
 monts=[];monter(DzPostComptes,{post:{id:"p3",espaceId:"esp_c",comptes:["c_t"]},onChange:function(){}});await attendre();
 R.aucun=[avec("data-dz-diffusion").length,avec("data-dz-diffusion-plusieurs").length,monts.length];
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
P3 = {}
if NODE and PC:
    P3 = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + FAUX_REACT + SONDE_PC.replace("__PC__", PC))
check("3.3 la fonction livrée DzPostComptes s'exécute sous node", bool(P3) and "erreur" not in P3, str(P3.get("erreur", ""))[:800])
check("3.4 les comptes whatsapp sont listés (cochables) avec les autres", P3.get("listes") == ["c_t", "c_w", "c_w2"], str(P3.get("listes")))
check("3.5 module absent : le point de montage est posé, rien ne casse", P3.get("sans_module") == 1, str(P3))
check("3.6 un compte whatsapp coché : UN montage data-dz-diffusion=p1, monter(nœud, \"p1\", {compte, espace, delai:700})",
      P3.get("montage") == [["p1", "div"]] and bool(P3.get("monts"))
      and all(m == ["DIV", "p1", {"compte": "c_w", "espace": "esp_c", "delai": 700}] for m in P3.get("monts", [])), str(P3.get("monts")))
check("3.7 cocher un autre compte : comptes et canaux suivent (whatsapp compris)",
      P3.get("change") == {"comptes": ["c_w", "c_t"], "channels": ["whatsapp", "telegram"]}, str(P3.get("change")))
check("3.8 deux comptes whatsapp : la ligne « un seul compte », aucun montage",
      (P3.get("deux") or [None])[0] == 0 and (P3.get("deux") or [0, []])[1] == [F("diffusion.panneau.un_seul_compte")]
      and (P3.get("deux") or [0, 0, 1])[2] == 0, str(P3.get("deux")))
check("3.9 aucun compte whatsapp coché : rien", P3.get("aucun") == [0, 0, 0], str(P3.get("aucun")))
check("3.9b clé du montage = post + compte whatsapp seulement (cocher un autre compte ne remonte pas le panneau)",
      PC.count('"dzdiff:"+p.id+":"+wa[0]') == 1 and "choisis.join(" not in PC)
ROUTE = B[B.find('e.channels.map(I=>{const A=_t[I];if(!A)return null;'):]
ROUTE = ROUTE[:ROUTE.find("},I)})")]
check("3.12 P4/P5 : la carte de routage tient whatsapp pour automatique, libellé « diffusion par Kapso »",
      bool(ROUTE) and 'const V=I==="whatsapp"||I==="telegram"&&' in ROUTE
      and 'children:I==="whatsapp"?dzT("diffusion.routage.kapso"):V?dzT("scheduler.routage.pub_bot"):dzT("scheduler.routage.pub_manuelle")' in ROUTE)
SONDE_T = r"""
const S=require("fs").readFileSync(process.argv[2],"utf8");
const i=S.indexOf("const _t={x:{id:\"x\""),j=S.indexOf(",Im=[",i);
eval(S.slice(i,j)+";process.stdout.write(JSON.stringify({wa:_t.whatsapp,bu:Bu.map(function(c){return c.id})}))");
"""
T3 = {}
if NODE:
    with tempfile.TemporaryDirectory() as _d:
        h = pathlib.Path(_d) / "t.js"
        h.write_text(SONDE_T, "utf-8")
        p = subprocess.run([NODE, str(h), str(BUNDLE)], capture_output=True, text=True, encoding="utf-8", timeout=60)
        try:
            T3 = json.loads(p.stdout or "{}")
        except ValueError:
            T3 = {"erreur": p.stdout + p.stderr}
check("3.10 P3 : _t.whatsapp (libellé, icône du rail WhatsApp, id)",
      (T3.get("wa") or {}).get("id") == "whatsapp" and (T3.get("wa") or {}).get("label") == "WhatsApp"
      and (T3.get("wa") or {}).get("icon") == "dz-nav-boite-reception", str(T3))
check("3.11 P3 : Bu (boutons de canaux) l'écarte, les cinq canaux d'avant restent dans l'ordre",
      T3.get("bu") == ["x", "telegram", "youtube", "instagram", "tiktok"], str(T3.get("bu")))

# ── [4] livraison ───────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[4] livraison")
SRC = MODULE.read_text("utf-8") if MODULE.is_file() else ""
check("4.1 le module existe ; dist/shared en est la copie OCTET POUR OCTET",
      MODULE.is_file() and (DI / MODULE.name).is_file() and (DI / MODULE.name).read_bytes() == MODULE.read_bytes())
HTML = (REPO / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
BALISE = '<script src="/shared/dz-diffusion-whatsapp.js"></script>'
check("4.2 index.html charge le module UNE fois, après dz-whatsapp-espace.js",
      HTML.count(BALISE) == 1 and HTML.count("dz-diffusion-whatsapp.js") == 1
      and HTML.find('<script src="/shared/dz-whatsapp-espace.js"></script>') < HTML.find(BALISE))
DICO = json.loads((SH / "i18n" / "diffusion.json").read_text("utf-8"))
lues = {k for k in re.findall(r'T\("(diffusion\.[a-z0-9_.]+)"', SRC) if not k.endswith(".")}   # préfixes : la liste dyn
dyn = {"diffusion.categorie." + c for c in ("marketing", "utility", "authentication")} \
    | {"diffusion.statut." + s for s in ("configuree", "preparation", "envoi", "draft", "sending", "completed", "stopped", "failed", "echec")} \
    | {"diffusion.compteur." + k for k in ("envoyes", "livres", "lus", "echecs", "retires")} \
    | {"diffusion.ecarte." + k for k in ("accord", "stop", "marketing", "bsuid")} | {"diffusion.refus.consentement", "diffusion.refus.prix"}
manque = sorted(k for k in lues | dyn if k not in DICO or not DICO[k].get("fr") or not DICO[k].get("en"))
check("4.3 chaque clé diffusion.* lue par le module existe en FR et en EN", len(lues) > 30 and not manque, str(manque))
check("4.4 les clés du maillon existent (FR et EN)", all(DICO.get(k, {}).get("fr") and DICO.get(k, {}).get("en")
      for k in ("diffusion.panneau.un_seul_compte", "diffusion.routage.kapso")))
ra = subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", cwd=str(REPO))
check("4.5 dictionnaire assemblé à jour", ra.returncode == 0, ra.stdout + ra.stderr)
SANS_COMM = re.sub(r"/\*[\s\S]*?\*/", "", SRC)
check("4.6 confirmations par `await window.__dzDialogue.confirmer(` (deux : relance incertaine, liste élargie), aucun natif",
      SANS_COMM.count(CONFIRMER) == 2 and not re.search(r"(?<![\w.$])(?:window\.)?(?:confirm|alert|prompt)\(", SANS_COMM))
check("4.7 le texte de confirmation AVERTIT : les autres canaux du post partent aussi (FR et EN)",
      "autres canaux" in DICO["diffusion.confirmer.texte"]["fr"] and "other channels" in DICO["diffusion.confirmer.texte"]["en"])
check("4.8 jamais un numéro : le module ne lit pas les identités de la config",
      ".identites" not in SANS_COMM and "innerHTML" not in SANS_COMM)
check("4.9 délai de 30 s et jeton de requête", "DELAI_MS = 30000" in SRC and "inst.jeton" in SRC)
if NODE:
    rn = subprocess.run([NODE, str(SH / "qa" / "diffusion.test.mjs")], capture_output=True, text=True, encoding="utf-8",
                        errors="replace", cwd=str(REPO), timeout=120)
    check("4.10 le banc node du panneau est vert (FR et EN)", rn.returncode == 0 and rn.stdout.startswith("OK "), (rn.stdout + rn.stderr)[-600:])

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
