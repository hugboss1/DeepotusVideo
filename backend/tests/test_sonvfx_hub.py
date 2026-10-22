# -*- coding: utf-8 -*-
"""Son & VFX en sous-menus à la Game Assets (t268, 21/10/2026) — le maillon de queue `dzsonvfx`
(scripts/patch_bundle_dzsonvfx.py, APRÈS dzconstats) pose `DzSonVfxHub` : une barre `dzCatBar` de six sous-onglets
(Musique, SFX, Voix off, VFX particules, VFX IA, Post-traitement), un en-tête de page, puis l'écran d'origine
`DzSonVfx` dont le hub pilote la sélection sans toucher le bloc SONVFX (couche traduite L4).
Sections :
  [A] câblage dans le livré : dispatch, ordre de SVM_GENS, bloc SONVFX intact, aucun texte en dur ;
  [E] sous node, avec la VRAIE fonction extraite du livré (mini-moteur de hooks) : six onglets, onglet actif, en-tête,
      clic du générateur masqué, suivi d'un saut interne, événement deepotus:sonvfx-subtab, __dzSvSub, feuille unique ;
  [D] chaîne : sans le maillon = la base octet pour octet ; aller-retour ; comptes figés ; octets / CRLF ;
  [K] textes : clé FR ET EN dans sonvfx_hub.json, dictionnaire assemblé.
Run (depuis backend/) : & $PY tests/test_sonvfx_hub.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")
BASE = "b2a1b276"            # origin/main (#421 fusionnée), dzconstats en queue
CONF = "await window.__dzDialogue.confirmer("
IDS = ["music", "sfx", "voiceover", "vfx", "vfxia", "post"]


def _hub():
    i = BUNDLE.find("var __dzSvHue=")
    j = BUNDLE.find("/*__dzsonvfx*/")
    return BUNDLE[i:j] if 0 <= i < j else ""


HUB = _hub()

# ── [A] câblage ───────────────────────────────────────────────────────────────────────────────────────────────────
print("[A] câblage dans le livré")
check("A1 le dispatch rend DzSonVfxHub, plus DzSonVfx nu",
      BUNDLE.count('s==="sonvfx"&&r.jsx(DzSonVfxHub,{variant:e,go:a})') == 1
      and 's==="sonvfx"&&r.jsx(DzSonVfx,' not in BUNDLE)
check("A2 DzSonVfxHub posé une fois, HORS des blocs de couche",
      BUNDLE.count("function DzSonVfxHub(") == 1 and HUB
      and not (BUNDLE.find("/*__DZ_SONVFX_BEGIN__*/") < BUNDLE.find(HUB) < BUNDLE.find("/*__DZ_SONVFX_END__*/")))
check("A3 le hub rend l'écran d'origine avec les mêmes props",
      HUB.count("r.jsx(DzSonVfx,{variant:p.variant,go:p.go})") == 1)
_gens = re.search(r"var SVM_GENS=\[(.*?)\];", BUNDLE, re.S)
_ordre = re.findall(r'\{id:"(\w+)"', _gens.group(1)) if _gens else []
_ordre.insert(4, "vfxia") if 'SVM_GENS.splice(4,0,{id:"vfxia"' in BUNDLE else None
check("A4 ordre réel de SVM_GENS (après la carte VFX IA) = l'ordre des sous-onglets", _ordre == IDS, _ordre)
check("A5 aucun texte en dur : libellés lus dans SVM_GENS ou dzT",
      not re.search(r'children:"[^"]*[A-Za-zÀ-ÿ]', HUB) and not re.search(r'"aria-label":"', HUB)
      and 'dzT("sonvfx.hub.barre")' in HUB)
check("A6 hooks par alias dans la fonction (x.useState( ×731 intact)",
      "var US=x.useState,UE=x.useEffect,UR=x.useRef;" in HUB and "x.useState(" not in HUB
      and BUNDLE.count("x.useState(") == 731)
check("A7 une icône Deepotus Glyph par sous-onglet, toutes dans le sprite",
      all(re.search(r'\b%s:"(dz-[a-z-]+)"' % i, HUB) for i in IDS)
      and all(('id="%s"' % n) in (RACINE / "frontend" / "dist" / "shared" / "icons" / "dz-icons.svg").read_text(encoding="utf-8")
              for n in re.findall(r'__dzSvIco=\{(.*?)\}', HUB)[0].split('"')[1::2]))
check("A8 la feuille masque titre, onglets texte et liste des générateurs (pas le panneau de contexte)",
      all(t in HUB for t in (".dzsvh .svm-genlist", ".dzsvh .svm-tabs", ".dzsvh .svm-title",
                             ".dzsvh .svm-rail>.svm-label:first-child"))
      and ".dzsvh .svm-rail{display:none" not in HUB)
_css = re.search(r'st\.textContent="([^"]*)"', HUB)
_css = _css.group(1) if _css else ""
check("A10 aucun arrondi dans Son & VFX : une règle « angles vifs » sur tout le hub, aucun autre border-radius",
      ".dzsvh,.dzsvh *,.dzsvh *::before,.dzsvh *::after{border-radius:0!important}" in _css
      and _css.count("border-radius") == 1, re.findall(r"[^{}]*border-radius[^{}]*", _css))
check("A9 la barre porte ses colonnes (la feuille __dzCatBar compte celles de Game Assets)",
      'style:{gridTemplateColumns:"repeat("+(G.length||1)+",1fr)"}' in HUB)

# ── [E] sous node ─────────────────────────────────────────────────────────────────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
const i=S.indexOf("var __dzSvHue="),j=S.indexOf("/*__dzsonvfx*/");if(i<0||j<i)throw new Error("hub introuvable");
const CODE=S.slice(i,j);
let H=[],HI=0,EFF=[],CLICS=[],STYLES=[],LIST={},MO=null,SEL=1;
const x={useState(v){const k=HI++;if(!(k in H))H[k]=typeof v==="function"?v():v;return [H[k],n=>{H[k]=typeof n==="function"?n(H[k]):n}]},
 useEffect(f,d){const k=HI++;const p=H[k];if(!p||!d||d.some((v,q)=>v!==p[q]))EFF.push(f);H[k]=d||[]},
 useRef(v){const k=HI++;if(!(k in H))H[k]={current:v};return H[k]}};
const r={jsx:(t,p)=>({t,p}),jsxs:(t,p)=>({t,p}),Fragment:"F"};
function dzT(k){return "⟦"+k+"⟧"}
function __dzGl(n,s){return {t:"glyph",p:{name:n,size:s}}}
function DzSonVfx(p){return {t:"DzSonVfx",p}}
function DzSvPistes(p){return {t:"DzSvPistes",p}}
function DzSvAtelier(p){return {t:"DzSvAtelier",p}}
function DzSvVoix(p){return {t:"DzSvVoix",p}}
function DzSvParticules(p){return {t:"DzSvParticules",p}}
function DzSvPost(p){return {t:"DzSvPost",p}}
var SVM_GENS=["music","sfx","voiceover","vfx","vfxia","post"].map(id=>({id,name:"N:"+id,desc:"D:"+id,price:"P:"+id}));
const BOUTONS=SVM_GENS.map((g,q)=>({hasAttribute:a=>a==="data-sel"&&SEL===q,click(){CLICS.push(g.id);SEL=q}}));
const EL={querySelectorAll:s=>s===".svm-genlist .svm-gen"?BOUTONS:[]};
const window={addEventListener:(n,f)=>{LIST[n]=f},removeEventListener:(n,f)=>{if(LIST[n]===f)delete LIST[n]}};
const document={getElementById:id=>STYLES.find(s=>s.id===id)||null,createElement:()=>({}),head:{appendChild:s=>STYLES.push(s)}};
function MutationObserver(cb){MO={cb,obs:null};this.observe=(el,o)=>{MO.obs=o};this.disconnect=()=>{MO=null}}
eval(CODE);
function tout(n,f,acc){if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tout(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)tout(n.p.children,f,acc);return acc}
function texte(n){if(n==null)return "";if(typeof n==="string")return n;if(Array.isArray(n))return n.map(texte).join("");
 return n.p?texte(n.p.children):""}
let ARBRE=null;
function rendre(){HI=0;EFF=[];ARBRE=DzSonVfxHub({variant:"v",go:"g"});
 const corps=tout(ARBRE,n=>n.p&&n.p.ref,[])[0];if(corps)corps.p.ref.current=EL;
 const e=EFF;EFF=[];e.forEach(f=>f());return ARBRE}
function etat(){const tabs=tout(ARBRE,n=>n.t==="button"&&/dzCatTab/.test(n.p.className||""),[]);
 const barre=tout(ARBRE,n=>/dzCatBar/.test((n.p&&n.p.className)||""),[])[0];
 return {sub:ARBRE.p["data-sv-sub"],tabs:tabs.map(t=>({id:t.p["data-sv-sub"],on:t.p["aria-pressed"],cls:t.p.className,
   lbl:texte(tout(t,n=>n.p&&n.p.className==="dzCatLbl",[])[0]),ico:(tout(t,n=>n.t==="glyph",[])[0]||{p:{}}).p.name,
   cat:t.p.style["--cat"]})),
  barre:barre&&barre.p["aria-label"],
  tete:["dzsvh-nom","dzsvh-desc","dzsvh-prix"].map(c=>texte(tout(ARBRE,n=>n.p&&n.p.className===c,[])[0])),
  ecran:(tout(ARBRE,n=>n.t===DzSonVfx,[])[0]||{p:{}}).p,clics:CLICS.slice(),styles:STYLES.length,
  ecoute:!!LIST["deepotus:sonvfx-subtab"],mo:!!(MO&&MO.obs&&MO.obs.attributeFilter[0]==="data-sel"),w:window.__dzSvSub,
  modes:tout(ARBRE,n=>n.p&&n.p["data-sv-mode"],[]).map(b=>[b.p["data-sv-mode"],b.p["aria-pressed"],texte(b)]),
  pistes:(tout(ARBRE,n=>n.t===DzSvPistes,[])[0]||{p:null}).p,
  atelier:(tout(ARBRE,n=>n.t===DzSvAtelier,[])[0]||{p:null}).p,
  voix:(tout(ARBRE,n=>n.t===DzSvVoix,[])[0]||{p:null}).p,
  parti:(tout(ARBRE,n=>n.t===DzSvParticules,[])[0]||{p:null}).p,
  post:(tout(ARBRE,n=>n.t===DzSvPost,[])[0]||{p:null}).p,
  ancien:(tout(ARBRE,n=>n.p&&n.p.className==="dzsvh-ancien",[])[0]||{p:{}}).p.style||null,mus:window.__dzSvMus}}
const R={};
rendre();rendre();R.montage=etat();
const post=etat().tabs.find(t=>t.id==="post");
tout(ARBRE,n=>n.t==="button"&&n.p["data-sv-sub"]==="post",[])[0].p.onClick();rendre();R.clic_post=etat();
SEL=1;MO.cb();rendre();R.saut_sfx=etat();
LIST["deepotus:sonvfx-subtab"]({detail:{id:"vfxia"}});rendre();R.ev_objet=etat();
LIST["deepotus:sonvfx-subtab"]({detail:"voiceover"});rendre();R.ev_texte=etat();
LIST["deepotus:sonvfx-subtab"]({detail:"inconnu"});rendre();R.ev_inconnu=etat();
H=[];CLICS=[];window.__dzSvSub="vfx";SEL=3;rendre();R.retour=etat();
H=[];CLICS=[];window.__dzSvSub="nimporte";rendre();R.retour_inconnu=etat();
H=[];CLICS=[];window.__dzSvSub="music";SEL=0;rendre();
tout(ARBRE,n=>n.p&&n.p["data-sv-mode"]==="pistes",[])[0].p.onClick();rendre();R.mode_pistes=etat();
tout(ARBRE,n=>n.t==="button"&&n.p["data-sv-sub"]==="sfx",[])[0].p.onClick();rendre();R.pistes_sfx=etat();
LIST["deepotus:sonvfx-subtab"]({detail:{id:"music",mode:"generer"}});rendre();R.ev_generer=etat();
LIST["deepotus:sonvfx-subtab"]({detail:{id:"music",mode:"pistes"}});rendre();R.ev_pistes=etat();
H=[];CLICS=[];rendre();R.retour_pistes=etat();
LIST["deepotus:sonvfx-subtab"]({detail:{id:"music",mode:"atelier"}});rendre();R.ev_atelier=etat();
H=[];CLICS=[];rendre();R.retour_atelier=etat();
LIST["deepotus:sonvfx-subtab"]({detail:{id:"music",mode:"nimporte"}});rendre();R.ev_mode_inconnu=etat();
process.stdout.write(JSON.stringify(R));
"""


def _node():
    with tempfile.TemporaryDirectory() as dd:
        h = pathlib.Path(dd) / "h.js"
        h.write_text(HARNAIS, encoding="utf-8")
        p = subprocess.run(["node", str(h), str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return {"erreur": (p.stdout + p.stderr)[:800]}


print("[E] sous node (vraie fonction du livré)")
R = _node()
check("E0 harnais exécuté", "montage" in R, R)
m = R.get("montage", {})
check("E1 six sous-onglets dzCatTab dans l'ordre de SVM_GENS, libellés = noms des générateurs",
      [t["id"] for t in m.get("tabs", [])] == IDS and [t["lbl"] for t in m.get("tabs", [])] == ["N:" + i for i in IDS], m)
check("E2 au premier passage : Musique ouverte, seule pressée",
      m.get("sub") == "music" and [t["on"] for t in m.get("tabs", [])] == ["true"] + ["false"] * 5, m)
check("E3 chaque onglet a sa teinte et son icône, toutes distinctes",
      len({t["cat"] for t in m.get("tabs", [])}) == 6 and len({t["ico"] for t in m.get("tabs", [])}) == 6
      and all(t["ico"].startswith("dz-") for t in m.get("tabs", [])), m)
check("E4 en-tête = nom, phrase et prix du générateur ouvert", m.get("tete") == ["N:music", "D:music", "P:music"], m)
check("E5 l'écran d'origine reçoit variant et go", m.get("ecran") == {"variant": "v", "go": "g"}, m)
check("E6 le générateur masqué de Musique est cliqué une fois (l'écran ouvrait la Voix off)",
      m.get("clics") == ["music"], m)
check("E7 feuille __dzSvHub injectée une seule fois malgré deux rendus", m.get("styles") == 1, m)
check("E8 la barre a un aria-label traduit", m.get("barre") == "⟦sonvfx.hub.barre⟧", m)
check("E9 écoute de l'événement et observation de data-sel posées", m.get("ecoute") and m.get("mo"), m)
c = R.get("clic_post", {})
check("E10 clic sur Post-traitement : onglet pressé, en-tête, générateur cliqué, __dzSvSub gardé",
      c.get("sub") == "post" and [t["on"] for t in c.get("tabs", [])][-1] == "true"
      and c.get("tete") == ["N:post", "D:post", "P:post"] and c.get("clics") == ["music", "post"]
      and c.get("w") == "post", c)
c = R.get("saut_sfx", {})
check("E11 saut interne de l'écran (jingles → SFX) : le hub suit, sans recliquer",
      c.get("sub") == "sfx" and c.get("clics") == ["music", "post"], c)
check("E12 événement {id} : VFX IA ouvert", R.get("ev_objet", {}).get("sub") == "vfxia", R.get("ev_objet"))
check("E13 événement id texte : Voix off ouverte", R.get("ev_texte", {}).get("sub") == "voiceover", R.get("ev_texte"))
check("E14 id inconnu ignoré", R.get("ev_inconnu", {}).get("sub") == "voiceover", R.get("ev_inconnu"))
c = R.get("retour", {})
check("E15 retour sur l'écran : le sous-onglet gardé (__dzSvSub) rouvre, sans clic s'il est déjà choisi",
      c.get("sub") == "vfx" and c.get("clics") == [], c)
check("E16 __dzSvSub inconnu : Musique par défaut", R.get("retour_inconnu", {}).get("sub") == "music",
      R.get("retour_inconnu"))
# t269 : les deux modes de Musique
check("E17 Musique : trois modes traduits (t271 : Atelier), « Générer » choisi d'abord ; aucun mode hors Musique",
      m.get("modes") == [["generer", "true", "⟦sonvfx.hub.mode_generer⟧"], ["pistes", "false", "⟦sonvfx.hub.mode_pistes⟧"],
                         ["atelier", "false", "⟦sonvfx.hub.mode_atelier⟧"]]
      and R.get("clic_post", {}).get("modes") == [] and m.get("pistes") is None and m.get("ancien") is None, m)
c = R.get("mode_pistes", {})
check("E18 « Importer et séparer » : la page reçoit go, l'écran d'origine reste monté mais masqué, mode gardé",
      c.get("pistes") == {"go": "g"} and c.get("ancien") == {"display": "none"}
      and c.get("ecran") == {"variant": "v", "go": "g"} and c.get("mus") == "pistes"
      and [b[1] for b in c.get("modes", [])] == ["false", "true", "false"] and c.get("atelier") is None, c)
c = R.get("pistes_sfx", {})
check("E19 un autre sous-onglet rend l'écran d'origine visible, sans la page", c.get("sub") == "sfx"
      and c.get("pistes") is None and c.get("ancien") is None, c)
check("E20 événement {id:music, mode} : choisit le mode",
      R.get("ev_generer", {}).get("pistes") is None and R.get("ev_generer", {}).get("sub") == "music"
      and R.get("ev_pistes", {}).get("pistes") == {"go": "g"}, [R.get("ev_generer"), R.get("ev_pistes")])
check("E21 retour sur l'écran : le mode gardé (__dzSvMus) rouvre", R.get("retour_pistes", {}).get("pistes") == {"go": "g"},
      R.get("retour_pistes"))
c = R.get("ev_atelier", {})
check("E22 mode Atelier (événement) : l'Atelier reçoit go, la page Pistes sort, l'écran d'origine reste monté masqué",
      c.get("atelier") == {"go": "g"} and c.get("pistes") is None and c.get("ancien") == {"display": "none"}
      and c.get("ecran") == {"variant": "v", "go": "g"} and c.get("mus") == "atelier"
      and [b[1] for b in c.get("modes", [])] == ["false", "false", "true"], c)
check("E23 retour : l'Atelier gardé rouvre ; mode inconnu → Générer",
      R.get("retour_atelier", {}).get("atelier") == {"go": "g"}
      and R.get("ev_mode_inconnu", {}).get("atelier") is None and R.get("ev_mode_inconnu", {}).get("ancien") is None,
      [R.get("retour_atelier"), R.get("ev_mode_inconnu")])

# t273 : la Voix off est la page DzSvVoix, la vue d'origine (et son encart de post-traitement) masquée
c = R.get("ev_texte", {})
check("E24 Voix off : la page DzSvVoix reçoit go, la vue d'origine reste montée mais masquée ; nulle part ailleurs",
      c.get("voix") == {"go": "g"} and c.get("ancien") == {"display": "none"} and c.get("ecran") == {"variant": "v", "go": "g"}
      and m.get("voix") is None and R.get("clic_post", {}).get("voix") is None and R.get("ev_objet", {}).get("voix") is None
      and m.get("ancien") is None, [c.get("voix"), c.get("ancien"), m.get("voix")])

# t274 : les Particules sont la page DzSvParticules, la vue d'origine masquée
c = R.get("retour", {})
check("E25 Particules : la page DzSvParticules reçoit go, la vue d'origine reste montée mais masquée ; nulle part ailleurs",
      c.get("parti") == {"go": "g"} and c.get("ancien") == {"display": "none"} and c.get("ecran") == {"variant": "v", "go": "g"}
      and R.get("ev_texte", {}).get("parti") is None and R.get("clic_post", {}).get("parti") is None
      and R.get("ev_objet", {}).get("parti") is None, [c.get("parti"), c.get("ancien")])

# t276 : le Post-traitement est la page DzSvPost, la vue d'origine masquée
c = R.get("clic_post", {})
check("E26 Post-traitement : la page DzSvPost reçoit go, la vue d'origine reste montée mais masquée ; nulle part ailleurs",
      c.get("post") == {"go": "g"} and c.get("ancien") == {"display": "none"} and c.get("ecran") == {"variant": "v", "go": "g"}
      and m.get("post") is None and R.get("ev_texte", {}).get("post") is None and R.get("retour", {}).get("post") is None
      and R.get("ev_objet", {}).get("post") is None, [c.get("post"), c.get("ancien")])

# ── [D] chaîne ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[D] chaîne dzsonvfx")
try:
    import patch_bundle_dzsonvfx as PS
except Exception as e:  # noqa: BLE001
    PS = None
    print(f"  (maillon introuvable : {e})")


def _base_bytes():
    r_ = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True,
                        cwd=str(RACINE))
    b_ = r_.stdout.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")     # le dépôt garde le bundle en LF
    # t280 : la couche sonvfx retouchée après BASE (L4 + G1) — le bloc attendu est celui du livré ; D6 vérifie
    # qu'il est sa couche source, à l'octet
    return __import__("_i18n_l1_aide").base_avec_sonvfx_livre(b_, RAW)


def _bloc(s):
    a, b = s.find("/*__DZ_SONVFX_BEGIN__*/"), s.find("/*__DZ_SONVFX_END__*/")
    return s[a:b]


def _bloc_est_sa_couche():
    src = (RACINE / "frontend" / "patches" / "son-vfx-montage.js").read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    bloc = _bloc(BUNDLE)[len("/*__DZ_SONVFX_BEGIN__*/"):].encode("utf-8")
    return bloc.strip(b"\r\n") == src.strip(b"\r\n")


check("D1 maillon présent", PS is not None)
check("D2 sans le maillon (avant_dzsonvfx) = la base octet pour octet",
      lambda: __import__("_i18n_l1_aide").avant_dzsonvfx(BUNDLE).encode("utf-8") == _base_bytes())
check("D3 avant_dzconstats défait dzsonvfx d'abord",
      lambda: "DzSonVfxHub" not in __import__("_i18n_l1_aide").avant_dzconstats(BUNDLE))
check("D4 aller-retour exact", lambda: PS.appliquer(PS.defaire(BUNDLE)) == BUNDLE)
check("D5 comptes figés : x.useState( 731, DzTracks 181, v2.8.0 ×4, confirmer ×30",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("DzTracks") == 181 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count(CONF) == 30)
check("D6 bloc SONVFX intact : sa couche source frontend/patches/son-vfx-montage.js, à l'octet", _bloc_est_sa_couche)
check("D7 octets : CRLF partout, aucune paire sur deux lignes",
      RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n")
      and all("\n" not in a + b for a, b in PS.PAIRES))
_src = (RACINE / "scripts" / "patch_bundle_dzsonvfx.py").read_bytes().decode("utf-8")
check("D8 le maillon lit en octets", "read_text(" not in _src and "write_text(" not in _src)
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzsonvfx.py"), "--check"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                    env=dict(__import__("os").environ, PYTHONIOENCODING="utf-8"))
check("D9 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)
check("D10 pas de .bak_dzsonvfx laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzsonvfx")).exists())
rn = subprocess.run(["node", "--check", str(BUN_P)], capture_output=True, text=True)
check("D11 node --check du livré", rn.returncode == 0, rn.stderr[:300])

# ── [K] textes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] textes FR / EN")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "sonvfx_hub.json").read_text(encoding="utf-8"))
# t269 : les clés du hub ET de la page « Importer et séparer » (posée par H0 jusqu'à /*__dzsvpistes*/)
_i, _j = BUNDLE.find("var __dzSvHue="), BUNDLE.find("/*__dzsvpost*/")  # t271 : hub + Pistes + Atelier ; t273 : + Voix ; t274 : + Particules ; t276 : + Post
CLES = sorted(set(re.findall(r'dzT\("(sonvfx\.[a-z0-9_.]+)"', BUNDLE[_i:_j]))) if 0 <= _i < _j else []
check("K0 le fichier porte exactement les clés appelées par le maillon, à trois segments",
      CLES and sorted(DICO) == CLES and all(len(k.split(".")) == 3 for k in CLES),
      sorted(set(DICO) ^ set(CLES)))
_var = lambda t: set(re.findall(r"\{(\w+)\}", t))           # noqa: E731
check("K1 chaque clé : FR et EN présents, mêmes variables, littérale dans le livré",
      all((DICO.get(k) or {}).get("fr") and (DICO.get(k) or {}).get("en")
          and _var(DICO[k]["fr"]) == _var(DICO[k]["en"]) and f'"{k}"' in BUNDLE for k in CLES),
      [k for k in CLES if not ((DICO.get(k) or {}).get("fr") and (DICO.get(k) or {}).get("en"))])
src_dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("K2 dictionnaire assemblé (source = copie de dist)",
      all(k.encode() in src_dico for k in CLES)
      and src_dico == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS / {fail} FAIL")


def test_sonvfx_hub():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
