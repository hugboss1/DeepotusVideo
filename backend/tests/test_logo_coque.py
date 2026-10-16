# -*- coding: utf-8 -*-
"""Logo de la coque (16/10/2026) — le logo de l'APPLICATION, en haut de la colonne de menu, ne change JAMAIS ; celui
de l'encart du bas (slogans + sélecteur d'espace) suit la MARQUE active, à l'aller comme au retour.

Défaut relevé sur 30695018 (reproduit au clic sur un backend de preuve) : `Ch` (la marque du haut de la barre) lisait
`D.brandLogoUrl()` = `/api/branding/logo`, le logo du kit ACTIF de Réglages › Branding, toujours à la MÊME URL. Activer
Rippled puis recharger affichait le logo Rippled en haut ; revenir au kit Deepotus rendait le nom « DEEPOTUS » mais
l'image restait celle de Rippled (même URL : le navigateur ne la relit pas). L'encart du bas, lui, montrait un glyphe
fixe (dz-marque-poulpe) quelle que soit la marque.

Ce que ce banc garde :
  [A] route GET /api/espaces/{id}/logo : le logo du kit que l'espace nomme, sinon celui du kit actif de Branding,
      sinon le logo livré ; espace inconnu ou id hostile → 404 ; Cache-Control no-cache ;
  [B] `dzLogoMarqueSrc(cache, kit, v)` sous node : URL de l'espace ACTIF, change quand l'espace, son kit, le kit de
      Branding ou la version changent (jamais deux marques à la même URL) ; sans cache → « » ;
  [C] `DzLogoMarque` sous node (hooks simulés) : rend l'image de la marque, s'abonne aux espaces et à
      deepotus:brand-refresh (désabonné au démontage), retombe sur le glyphe si l'image échoue ;
  [D] sites : `Ch` affiche le logo LIVRÉ (/deepotus-logo.png) et ne lit plus brandLogoUrl ; l'encart du bas rend
      DzLogoMarque avec le kit de Branding et le glyphe en repli ;
  [E] maillon de queue `dzlogo` : sonde amont (dzreglages, dzespace…), octets, inverse exact, `avant_dzlogo` en tête
      d'`avant_dzreglages`, comptes figés intacts (useState 731, v2.8.0 ×4, DzTracks 181), remplacements G1 intacts,
      aucun .bak.
Run (depuis backend/) : & $PY tests/test_logo_coque.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzlogo_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for d in ("images", "outputs"):
    (_tmp / d).mkdir(parents=True, exist_ok=True)
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
          "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def png(couleur):
    import io
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (8, 8), couleur).save(b, format="PNG")
    return b.getvalue()


print("[A] GET /api/espaces/{id}/logo")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
c = TestClient(app)
LIVRE = (RACINE / "frontend" / "public" / "deepotus-logo.png").read_bytes()
g0 = c.get("/api/espaces/deepotus/logo")
check("A1 Deepotus sans logo de kit → le logo livré", g0.status_code == 200 and g0.content == LIVRE, str(g0.status_code))
check("A2 Cache-Control no-cache", g0.headers.get("cache-control") == "no-cache", str(g0.headers.get("cache-control")))
kr = c.post("/api/brand-kits", json={"name": "Rippled", "app_name": "RIPPLED"}).json()["kit_id"]
OR, ROUGE = png((240, 180, 41)), png((200, 20, 20))
c.post(f"/api/brand-kits/{kr}/logo", files={"file": ("r.png", OR, "image/png")})
OR_N = c.get(f"/api/brand-kits/{kr}/logo").content            # normalisé par Pillow : on compare au servi
esp = c.post("/api/espaces", json={"nom": "Rippled"}).json()["espace"]["id"]
check("A3 espace sans kit → suit le kit actif de Branding (Deepotus, logo livré)",
      lambda: c.get(f"/api/espaces/{esp}/logo").content == LIVRE)
c.post(f"/api/espaces/{esp}", json={"kit_id": kr})
check("A4 espace qui nomme son kit → le logo de CE kit", lambda: c.get(f"/api/espaces/{esp}/logo").content == OR_N)
check("A5 Deepotus reste sur le logo livré pendant ce temps", lambda: c.get("/api/espaces/deepotus/logo").content == LIVRE)
c.post(f"/api/brand-kits/{kr}/activate")
check("A6 Branding sur Rippled : Deepotus (sans kit) suit Branding → logo Rippled",
      lambda: c.get("/api/espaces/deepotus/logo").content == OR_N)
c.post("/api/brand-kits/deepotus/activate")
check("A7 retour à Deepotus : Deepotus → logo livré, Rippled garde le sien",
      lambda: c.get("/api/espaces/deepotus/logo").content == LIVRE and c.get(f"/api/espaces/{esp}/logo").content == OR_N)
c.post("/api/brand-kits/deepotus/logo", files={"file": ("d.png", ROUGE, "image/png")})
DZ_N = c.get("/api/brand-kits/deepotus/logo").content
check("A8 kit Deepotus avec son logo → servi pour l'espace Deepotus", lambda: c.get("/api/espaces/deepotus/logo").content == DZ_N != LIVRE)
check("A9 espace inconnu → 404", lambda: c.get("/api/espaces/esp_inconnu/logo").status_code == 404)
check("A10 id hostile → 404 (jamais le disque)", lambda: all(c.get(f"/api/espaces/{h}/logo").status_code == 404
                                                          for h in ("esp..x", "a b", "deepotus.json", "%2e%2e")))
check("A11 /api/branding/logo inchangé (le kit actif)", lambda: c.get("/api/branding/logo").content == DZ_N)

BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
try{
 const SRC=tranche("function dzLogoMarqueSrc(","function Ch(");
 // hooks simulés : un seul composant, rendu à la demande
 let etat=[],k=0,effets=[],nett=[];const ECOUTE={};
 const x={useReducer(f,i){const j=k++;if(!(j in etat))etat[j]=i;return[etat[j],a=>{etat[j]=f(etat[j],a)}]},
  useEffect(f){effets.push(f)}};
 const r={jsx(t,p){return{t,p}}};
 const win={addEventListener(n,f){(ECOUTE[n]=ECOUTE[n]||[]).push(f)},removeEventListener(n,f){ECOUTE[n]=(ECOUTE[n]||[]).filter(g=>g!==f)}};
 const ENV={x,r,window:win,dzEspCache:null,dzEspAbonnes:[],dzEspCharger:()=>({catch(){}}),encodeURIComponent,Date,Object};
 const M=new Function("ENV","with(ENV){"+SRC+";return{dzLogoMarqueSrc,DzLogoMarque}}")(ENV);
 const C={actif:"deepotus",espaces:[{id:"deepotus",kit_id:null},{id:"esp_r",kit_id:"kit_r"}]};
 const B={};
 B.vide=M.dzLogoMarqueSrc(null,"deepotus",0);
 B.dz=M.dzLogoMarqueSrc(C,"deepotus",0);
 B.dzKit=M.dzLogoMarqueSrc(C,"kit_r",0);
 B.dzV=M.dzLogoMarqueSrc(C,"deepotus",1);
 B.r=M.dzLogoMarqueSrc(Object.assign({},C,{actif:"esp_r"}),"deepotus",0);
 B.rKit=M.dzLogoMarqueSrc({actif:"esp_r",espaces:[{id:"esp_r",kit_id:"kit_z"}]},"deepotus",0);
 B.hostile=M.dzLogoMarqueSrc({actif:"a/b?c",espaces:[]},"k&x",0);
 OUT.B=B;
 const E={};const REPLI={t:"glyphe"};
 function rendre(p){k=0;effets=[];const v=M.DzLogoMarque(p);effets.forEach(f=>{const n=f();if(n)nett.push(n)});return v}
 E.sansCache=rendre({kit:"deepotus",repli:REPLI});
 E.abonnes0=ENV.dzEspAbonnes.length;E.brand0=(ECOUTE["deepotus:brand-refresh"]||[]).length;
 ENV.dzEspCache=C;nett.splice(0).forEach(f=>f());ENV.dzEspAbonnes.length=0;
 E.img=rendre({kit:"deepotus",repli:REPLI});
 ECOUTE["deepotus:brand-refresh"].forEach(f=>f());
 E.apresRefresh=rendre({kit:"deepotus",repli:REPLI});
 E.apresRefresh.p.onError();
 E.apresErreur=rendre({kit:"deepotus",repli:REPLI});
 E.autreKit=rendre({kit:"kit_r",repli:REPLI});
 nett.splice(0).forEach(f=>f());
 E.abonnesFin=ENV.dzEspAbonnes.length;E.brandFin=(ECOUTE["deepotus:brand-refresh"]||[]).length;
 OUT.E=E;
}catch(e){OUT.err=String(e&&e.stack||e)}
process.stdout.write(JSON.stringify(OUT));
"""

print("[B][C] dzLogoMarqueSrc et DzLogoMarque sous node")
d = pathlib.Path(tempfile.mkdtemp(prefix="dzlogo_node_"))
(d / "h.js").write_text(HARNAIS, encoding="utf-8")
(d / "b.js").write_bytes(RAW)
rn = subprocess.run(["node", str(d / "h.js"), str(d / "b.js")], capture_output=True, text=True, encoding="utf-8",
                    errors="replace")
try:
    OUT = json.loads(rn.stdout or "{}")
except ValueError:
    OUT = {"err": rn.stdout[-300:] + rn.stderr[-300:]}
check("B0 aides extraites et exécutées", "err" not in OUT, str(OUT.get("err", ""))[:300])
B, E = OUT.get("B", {}), OUT.get("E", {})
check("B1 sans cache d'espaces → « »", B.get("vide") == "")
check("B2 URL de l'espace ACTIF", str(B.get("dz", "")).startswith("/api/espaces/deepotus/logo?"), str(B.get("dz")))
check("B3 changer d'espace change l'URL", B.get("r", "").startswith("/api/espaces/esp_r/logo?") and B.get("r") != B.get("dz"))
check("B4 changer le kit de Branding change l'URL (retour à Deepotus relu)", B.get("dzKit") not in (None, B.get("dz")))
check("B5 changer le kit de l'espace change l'URL", B.get("rKit") not in (None, B.get("r")))
check("B6 la version change l'URL (logo re-téléversé)", B.get("dzV") not in (None, B.get("dz")))
check("B7 id et kit encodés (rien d'injecté dans le chemin)",
      str(B.get("hostile", "")).startswith("/api/espaces/a%2Fb%3Fc/logo?") and "k%26x" in str(B.get("hostile")),
      str(B.get("hostile")))
img = E.get("img") or {}
check("C1 sans cache : le glyphe en repli, et chargement des espaces", E.get("sansCache") == {"t": "glyphe"})
check("C2 abonné aux espaces et à deepotus:brand-refresh", E.get("abonnes0") == 1 and E.get("brand0") == 1)
check("C3 avec cache : l'image de la marque active", img.get("t") == "img" and img.get("p", {}).get("src") == B.get("dz")
      and img.get("p", {}).get("data-dz-logo-marque") == "1", str(img)[:200])
check("C4 deepotus:brand-refresh → nouvelle URL (relue)",
      (E.get("apresRefresh") or {}).get("p", {}).get("src") not in (None, img.get("p", {}).get("src")))
check("C5 image en échec → le glyphe", E.get("apresErreur") == {"t": "glyphe"})
check("C6 une autre marque après l'échec → de nouveau une image", (E.get("autreKit") or {}).get("t") == "img")
check("C7 démontage : désabonné des deux", E.get("abonnesFin") == 0 and E.get("brandFin") == 0,
      f"{E.get('abonnesFin')} {E.get('brandFin')}")

print("[D] sites")
i_ch = BUNDLE.find("function Ch({compact:e,size:t=16}){")
CH = BUNDLE[i_ch:BUNDLE.find("const Ur=", i_ch)] if i_ch >= 0 else ""
check("D1 Ch affiche le logo LIVRÉ, figé", 'r.jsx("img",{src:"/deepotus-logo.png",alt:n.app_name,"data-dz-logo-app":"1",' in CH)
check("D2 Ch ne lit plus le logo du kit actif", bool(CH) and "brandLogoUrl" not in CH and "/api/branding" not in CH)
ENC = ('r.jsx(DzLogoMarque,{kit:i.kit_id,repli:r.jsx(X,{name:"dz-marque-poulpe",size:14,style:{color:"var(--cyan)"}})}),'
       'r.jsx("span",{style:{fontSize:11.5,color:"var(--ink-strong)"},children:i.tagline_1})')
check("D3 l'encart du bas rend la marque active, le glyphe en repli", BUNDLE.count(ENC) == 1)
check("D4 l'encart garde le sélecteur d'espace", BUNDLE.count("r.jsx(DzEspaceSel,{setView:t}),") == 1)

print("[E] maillon de queue dzlogo")
try:
    import patch_bundle_dzlogo as M                                  # noqa: E402
except ImportError as e:
    M = None
    check("E0 scripts/patch_bundle_dzlogo.py existe", False, str(e))
if M:
    import _i18n_l1_aide as AIDE                                     # noqa: E402
    avant = M.defaire(BUNDLE)
    check("E1 marqueur ×1 dans le livré, absent avant", BUNDLE.count(M.MARKER) == 1 and M.MARKER not in avant)
    check("E2 aller-retour exact", M.appliquer(avant) == BUNDLE)
    check("E3 l'avant = le Ch d'origine (brandLogoUrl) et le glyphe seul",
          'r.jsx("img",{src:D.brandLogoUrl(),alt:n.app_name,width:o,height:o,' in avant and "DzLogoMarque" not in avant)
    check("E4 sonde amont : dzreglages et dzespace", any(t == "dzreglages" for t, _j, _n in M.SONDE_AMONT)
          and any(t == "dzespace" for t, _j, _n in M.SONDE_AMONT))
    check("E5 la sonde amont tient sur l'avant", all(avant.count(j) == n for _t, j, n in M.SONDE_AMONT))
    check("E6 comptes figés intacts (useState 731, v2.8.0 ×4, DzTracks 181)",
          BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
    check("E7 avant_dzlogo = défaire", AIDE.avant_dzlogo(BUNDLE) == avant)
    check("E8 avant_dzlogo sans marqueur : rendu tel quel", AIDE.avant_dzlogo(avant) == avant)
    src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
    j = src_aide.find("def avant_dzreglages(")
    check("E9 avant_dzlogo appelé EN TÊTE d'avant_dzreglages",
          j > 0 and "bundle = avant_dzlogo(bundle)" in src_aide[j:src_aide.find("import patch_bundle_dzreglages", j)])
    check("E10 avant_dzreglages(livré) == avant_dzreglages(avant)", AIDE.avant_dzreglages(BUNDLE) == AIDE.avant_dzreglages(avant))
    try:
        _g1 = [p["remplace"] for p in json.loads((RACINE / "scripts" / "dzglyph_paires.json").read_bytes().decode("utf-8"))["paires"]]
    except (OSError, ValueError, KeyError):
        _g1 = []
    check("E11 aucun remplacement G1 du maillon dzglyph ne bouge", bool(_g1) and all(BUNDLE.count(x) == avant.count(x) for x in _g1),
          [x[:60] for x in _g1 if BUNDLE.count(x) != avant.count(x)][:3])
    check("E12 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
    check("E13 aucun .bak_dzlogo laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzlogo")).exists())
    src_m = (RACINE / "scripts" / "patch_bundle_dzlogo.py").read_text(encoding="utf-8")
    check("E14 le maillon lit et écrit en octets", "read_bytes" in src_m and "write_bytes" in src_m and "read_text" not in src_m)
    rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzlogo.py"), "--check"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    check("E15 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
