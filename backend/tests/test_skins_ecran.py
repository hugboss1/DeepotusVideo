# -*- coding: utf-8 -*-
"""t316 (28/10/2026) (D2, tâches 3 et 4) — les skins côté écran, joués sous node (aucun navigateur).
Plan docs/superpowers/plans/2026-10-28-t316-skins.md, spec boîte à outils §8.5.
[L] dz-skins-logique.js : couleurs (kit de l'espace par défaut, #hex, rôle), polices (identité, nom douteux écarté),
    textes par défaut (espace, slogans, phrases traduites), mise en page tenue dans la scène, toucher (élément actif
    seulement), déplacer (copie, borné, signature au coin le plus proche), intro/outro/pause/fin, bandeau après
    l'intro, alertes expirées ;
[Z] scène t315 étendue : vue = cadre ∘ zoom ; le CAVIARDAGE suit le cadre (cache aux coordonnées transformées, jamais
    rogné) ; l'écran rogné au cadre ; zoom stylé (k, durée bornés) ;
[C] dz-skins-calques.js (faux canvas) : calques sous 900, caviardage toujours dernier, cadre posé dans l'état,
    carte d'intro puis rien, signature éteinte, alerte affichée puis expirée, outro, retirer rend la scène ;
[U] dz-skins.js sous faux DOM : groupe « Habillage » (choix de l'espace, forme reprise), options de la capture,
    habiller avant la première image, outro avant l'arrêt (dz-capture.js) ;
[P] livraison : copies shared == dist, balise, ni alert/confirm/prompt ni emoji, angles vifs, clés skins.* FR/EN
    employées, assemblées, phrases FR sans double traduction.
Run (depuis backend/) : & $PY tests/test_skins_ecran.py"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
NODE = shutil.which("node")
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
        fail += 1; print(f"  FAIL  {label} {str(detail)[:700]}")


SH = REPO / "frontend" / "shared"
DI = REPO / "frontend" / "dist" / "shared"
FICHIERS = ["dz-skins.js", "dz-skins-logique.js", "dz-skins-calques.js"]
DICO = json.loads((SH / "i18n" / "skins.json").read_text("utf-8"))
URL = lambda nom: (SH / nom).resolve().as_uri()               # noqa: E731
LIVRES = json.loads((BACKEND / "app" / "skins" / "livres.json").read_text("utf-8"))


def node(script: str) -> dict:
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzskinsjs_"))
    f = d / "banc.mjs"
    f.write_text(script, "utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    out = r.stdout.strip().splitlines()
    if r.returncode or not out:
        raise RuntimeError((r.stderr or r.stdout)[-1500:])
    return json.loads(out[-1])


# un skin normalisé comme le serveur le rend (le livré Deepotus, complété par le défaut du service)
sys.path.insert(0, str(BACKEND))
from app.services import skins as K                                  # noqa: E402
SKIN = K.normaliser(LIVRES["livre-deepotus"])
CTX = {"espace": {"id": "deepotus", "nom": "Deepotus"}, "kit": {"brand_color": "#ef4444", "accent_color": "#00e5ff",
       "tagline_1": "From the deep,", "tagline_2": "for the deep."}, "polices": {"titre": "Playfair Display", "texte": None},
       "logo_espace": "/api/espaces/deepotus/logo"}
TFR = "const T = (k) => (" + json.dumps({k: v["fr"] for k, v in DICO.items()}) + ")[k] || ('<absente ' + k + '>');"

# ── [L] la logique pure ──
print("[L] dz-skins-logique.js")
L = node(r"""
const L = await import(%s);
%s
const skin = %s, ctx = %s, out = {};
out.pal = L.palette(skin, ctx);
out.pal2 = L.palette({couleurs: {principale: "#123456", accent: "rouge", texte: null}}, {kit: {}});
out.coul = [L.couleur("accent", out.pal), L.couleur("#abcdef", out.pal), L.couleur("inconnu", out.pal)];
out.rgba = L.rgba("#ff0000", 0.5);
out.pol = [L.polices(skin, ctx), L.polices({polices: {titre: "x;}</style>", texte: "Georgia"}}, {polices: {titre: "Inter"}}), L.polices({}, {})];
out.font = [L.police("Georgia", 20.4, true), L.police('a"b', 12, false), L.police("system-ui", 3, false)];
out.txt = L.textes(skin, ctx, T);
out.txt2 = L.textes(Object.assign({}, skin, {bandeau: Object.assign({}, skin.bandeau, {titre: "  Épisode 3 "})}), ctx, T);
out.remplir = [L.remplir("{nom} vient de s'abonner {autre}", {nom: "Zoé"}), L.remplir("{nom} : {texte}", {nom: "a", texte: "x".repeat(200)}).length];
const W = 1280, H = 720, R = L.disposer(skin, W, H);
out.R = R;
const bord = L.disposer({logo: {x: 1, y: 1, l: 0.5}, bandeau: {x: 0.9, y: 0.99, l: 0.5}, encart: {x: 0.9, y: 0.9, l: 0.3, h: 0.3}, signature: {coin: "haut-gauche"}}, W, H);
out.bord = bord;
out.toucher = [L.toucher(skin, R, R.logo.x + 2, R.logo.y + 2, false), L.toucher(skin, R, R.encart.x + 3, R.encart.y + 3, true),
  L.toucher(skin, R, R.encart.x + 3, R.encart.y + 3, false), L.toucher(Object.assign({}, skin, {logo: Object.assign({}, skin.logo, {actif: false})}), R, R.logo.x + 2, R.logo.y + 2, false),
  L.toucher(skin, R, 1, H / 2, false)];
const d1 = L.deplacer(skin, "logo", 0.1, 0.05, W, H);
const d2 = L.deplacer(skin, "bandeau", 5, 5, W, H);
const d3 = L.deplacer(skin, "signature", 0, 0, W, H, 0.1, 0.1);
out.depl = {logo: [d1.logo.x, d1.logo.y], intact: skin.logo.x, bandeau: [d2.bandeau.x, d2.bandeau.y], coin: d3.signature.coin,
  maxX: 1 - skin.bandeau.l, maxY: 1 - L.HAUTEURS.bandeau};
const intro = skin.intro.duree_s * 1000;
out.carte = [L.carte(skin, 0, {}), L.carte(skin, intro - 100, {}), L.carte(skin, intro + 1, {}), L.carte(skin, 99999, {outro: 99999 - 200}),
  L.carte(skin, 5, {ecran: "pause", outro: 0}), L.carte(skin, 5, {ecran: "fin"}), L.carte(Object.assign({}, skin, {intro: {actif: false}}), 0, {})];
const b0 = intro + skin.bandeau.debut_s * 1000;
out.bandeau = [L.bandeau(skin, b0 - 1), L.bandeau(skin, b0 + 200), L.bandeau(skin, b0 + 2000), L.bandeau(skin, b0 + skin.bandeau.duree_s * 1000 + 1),
  L.bandeau(Object.assign({}, skin, {bandeau: Object.assign({}, skin.bandeau, {duree_s: 0})}), 1e7)];
out.alertes = [L.alertes([{debut: 0}, {debut: 1000}], 2000, 5).map(a => [a.rang, a.alpha]), L.alertes([{debut: 0}], 6000, 5).length];
out.ajuster = [L.ajuster("abcdef", 100, t => t.length * 10), L.ajuster("abcdefghijkl", 60, t => t.length * 10)];
console.log(JSON.stringify(out));
""" % (json.dumps(URL("dz-skins-logique.js")), TFR, json.dumps(SKIN), json.dumps(CTX)))
check("L1 palette : principale/accent null -> kit de l'espace ; #hex gardé, rôle faux -> défaut, texte null -> blanc",
      L["pal"] == {"principale": "#ef4444", "accent": "#00e5ff", "texte": "#ffffff", "fond": "#0b0f14"}
      and L["pal2"] == {"principale": "#123456", "accent": "#00e5ff", "texte": "#ffffff", "fond": "#0b0f14"}, L["pal2"])
check("L2 couleur : rôle, #hex, inconnue -> principale ; rgba", L["coul"] == ["#00e5ff", "#abcdef", "#ef4444"] and L["rgba"] == "rgba(255,0,0,0.500)")
check("L3 polices : identité de l'espace par défaut, nom douteux écarté, system-ui en dernier recours",
      L["pol"] == [{"titre": "Playfair Display", "texte": "system-ui"}, {"titre": "Inter", "texte": "Georgia"}, {"titre": "system-ui", "texte": "system-ui"}], L["pol"])
check("L4 police CSS : famille citée, guillemet refusé, taille plancher",
      L["font"] == ['700 20px "Georgia", system-ui, sans-serif', "12px system-ui, sans-serif", "6px system-ui, sans-serif"], L["font"])
t = L["txt"]
check("L5 textes par défaut : intro = espace + slogans du kit, outro/pause/fin traduits, signature",
      t["intro"] == {"titre": "Deepotus", "sous_titre": "From the deep, for the deep."} and t["pause"]["titre"] == DICO["skins.defaut.pause"]["fr"]
      and t["fin"]["titre"] == DICO["skins.defaut.fin"]["fr"] and t["outro"]["titre"] == DICO["skins.defaut.outro"]["fr"]
      and t["signature"] == DICO["skins.signature.texte"]["fr"] and "DeepotusVideo" in t["signature"], t)
check("L6 un texte saisi l'emporte (espaces ôtés)", L["txt2"]["bandeau"]["titre"] == "Épisode 3")
check("L7 remplir : {nom} et {texte} seulement, bornés à 80", L["remplir"] == ["Zoé vient de s'abonner {autre}", 84], L["remplir"])
R, B = L["R"], L["bord"]
check("L8 mise en page en px de scène (logo carré, bandeau 11 % de hauteur, signature en bas à droite)",
      abs(R["logo"]["l"] - SKIN["logo"]["l"] * 1280) < 0.01 and R["logo"]["h"] == R["logo"]["l"] and abs(R["bandeau"]["h"] - 0.11 * 720) < 0.01
      and R["signature"]["x"] + R["signature"]["l"] < 1280 and R["signature"]["y"] > 600, R)
check("L9 places tenues dans la scène (bords), signature en haut à gauche",
      all(r["x"] >= 0 and r["y"] >= 0 and r["x"] + r["l"] <= 1280.01 and r["y"] + r["h"] <= 720.01 for r in B.values())
      and B["signature"]["x"] < 20 and B["signature"]["y"] < 20, B)
check("L10 toucher : logo, encart (seulement avec caméra), élément éteint ignoré, vide -> null",
      L["toucher"] == ["logo", "encart", None, None, None], L["toucher"])
dp = L["depl"]
check("L11 déplacer : copie (l'original intact), bornée au cadre, signature au coin le plus proche",
      abs(dp["logo"][0] - (SKIN["logo"]["x"] + 0.1)) < 1e-6 and dp["intact"] == SKIN["logo"]["x"]
      and abs(dp["bandeau"][0] - dp["maxX"]) < 1e-3 and abs(dp["bandeau"][1] - dp["maxY"]) < 1e-3 and dp["coin"] == "haut-gauche", dp)
c = L["carte"]
check("L12 cartes : intro au début (fondu à la fin), rien après, outro lancée, pause/fin prioritaires, intro éteinte",
      c[0]["nom"] == "intro" and c[0]["alpha"] == 1 and c[1]["nom"] == "intro" and 0 < c[1]["alpha"] < 1 and c[2] is None
      and c[3]["nom"] == "outro" and 0 < c[3]["alpha"] <= 1 and c[4] == {"nom": "pause", "alpha": 1} and c[5]["nom"] == "fin" and c[6] is None, c)
check("L13 bandeau : compté après l'intro, fondu d'entrée, plein, éteint après sa durée ; durée 0 = jusqu'au bout",
      L["bandeau"][0] == 0 and 0 < L["bandeau"][1] < 1 and L["bandeau"][2] == 1 and L["bandeau"][3] == 0 and L["bandeau"][4] == 1, L["bandeau"])
check("L14 alertes : rangées, fondu, expirées retirées", L["alertes"][0] == [[0, 1], [1, 1]] and L["alertes"][1] == 0, L["alertes"])
check("L15 ajuster : texte court gardé, long coupé avec « … »", L["ajuster"] == ["abcdef", "abcde…"], L["ajuster"])

# ── [Z] la scène t315 étendue ──
print("[Z] scène : cadre et zoom stylé")
FAUX_CANVAS = r"""
const ops = [];
function Ctx(){ return new Proxy({}, {get(t,k){ if (k in t) return t[k]; if (k === "createLinearGradient") return () => ({addColorStop(){}});
  if (k === "measureText") return (s) => ({width: String(s).length * 7});
  return (...a) => ops.push([k, ...a.map(x => typeof x === "object" ? "obj" : (typeof x === "number" ? Math.round(x * 100) / 100 : x))]); },
  set(t,k,v){ t[k]=v; ops.push(["=" + k, typeof v === "number" ? Math.round(v * 1000) / 1000 : (typeof v === "object" ? "obj" : v)]); return true; }}); }
const doc = { createElement(){ return { width: 0, height: 0, getContext(){ return Ctx(); }, captureStream(){ return {}; } }; } };
const horloge = { demarrer(){ return 1; }, arreter(){} };
"""
Z = node(r"""
const Lg = await import(%s), M = await import(%s);
%s
const out = {};
out.rc = Lg.rectCadre({marge: 0.05}, 1000, 500);
out.rc2 = Lg.rectCadre({marge: 9}, 1000, 500);
out.cv = Lg.composerCadre({k: 2, ox: -100, oy: -50}, {marge: 0.1}, 1000, 500);
out.z = [Lg.vueZoom({cx: 500, cy: 250, debut: 0}, 900, 1000, 500).k, Lg.vueZoom({cx: 500, cy: 250, debut: 0, k: 2, duree: 1000}, 500, 1000, 500).k,
  Lg.vueZoom({cx: 500, cy: 250, debut: 0, k: 9, duree: 1}, 400, 1000, 500).k, Lg.vueZoom({cx: 500, cy: 250, debut: 0, k: 2, duree: 1000}, 1200, 1000, 500).k];
const sc = M.creerScene({largeur: 1000, hauteur: 500, doc, horloge, secrets: () => [{x: 100, y: 100, l: 200, h: 100, ecran: false}]});
sc.source("ecran", {readyState: 4});
sc.ajouterCalque(M.calqueEcran());
sc.etat.cadre = {marge: 0.1};
ops.length = 0; const s = sc.dessiner(0);
out.s = {vue: s.vue, cadre: s.cadre};
const iClip = ops.findIndex(o => o[0] === "clip"), iDraw = ops.findIndex(o => o[0] === "drawImage");
out.rogne = iClip >= 0 && iClip < iDraw && ops.some(o => o[0] === "rect" && o[1] === 100 && o[2] === 50 && o[3] === 800 && o[4] === 400);
const tr = ops.filter(o => o[0] === "setTransform");
out.transforms = tr.map(o => o.slice(1));
// le cache du caviardage est peint SOUS la même transformation que l'écran (k 0,8, décalage 100/50), jamais rogné après
const iCav = ops.map((o, i) => [o, i]).filter(([o]) => o[0] === "fillRect" && o[1] !== 0).map(([o, i]) => i);
const derniereTr = (i) => { let t = null; for (let j = 0; j < i; j++) if (ops[j][0] === "setTransform") t = ops[j].slice(1); return t; };
out.cav = iCav.map(i => ({rect: ops[i].slice(1), tr: derniereTr(i)}));
out.clipApresDraw = ops.slice(iDraw).filter(o => o[0] === "clip").length;
sc.etat.cadre = null; ops.length = 0; const s0 = sc.dessiner(0);
out.sans = {vue: s0.vue, clip: ops.some(o => o[0] === "clip")};
console.log(JSON.stringify(out));
""" % (json.dumps((SH / "dz-capture-logique.js").resolve().as_uri()), json.dumps((SH / "dz-capture-scene.js").resolve().as_uri()), FAUX_CANVAS))
check("Z1 rectCadre : marge 5 % -> écran 90 % centré ; marge bornée à 12 %", Z["rc"] == {"x": 50, "y": 25, "l": 900, "h": 450, "k": 0.9}
      and abs(Z["rc2"]["k"] - 0.76) < 1e-9, Z["rc"])
check("Z2 composerCadre = cadre ∘ zoom (k 2 × 0,8 ; décalages réduits puis translatés)", Z["cv"] == {"k": 1.6, "ox": 20, "oy": 10}, Z["cv"])
check("Z3 zoom stylé : k et durée du skin, bornés (2,5 ; 800 ms), défaut 1,5 / 1 800 ms",
      Z["z"][0] == 1.5 and Z["z"][1] == 2 and abs(Z["z"][2] - 2.5) < 1e-9 and Z["z"][3] == 1, Z["z"])
check("Z4 la scène expose vue (cadre ∘ zoom) et s.cadre", Z["s"]["vue"] == {"k": 0.8, "ox": 100, "oy": 50}
      and Z["s"]["cadre"]["x"] == 100 and Z["s"]["cadre"]["l"] == 800, Z["s"])
check("Z5 l'écran est ROGNÉ au cadre (clip avant le dessin)", Z["rogne"] is True)
check("Z6 le CAVIARDAGE suit le cadre : cache peint sous la transformation de l'écran, jamais rogné",
      len(Z["cav"]) == 1 and Z["cav"][0]["tr"] == [0.8, 0, 0, 0.8, 100, 50] and Z["clipApresDraw"] == 0, Z["cav"])
check("Z7 sans cadre : vue identité, aucun rognage (comportement de t315 inchangé)", Z["sans"] == {"vue": {"k": 1, "ox": 0, "oy": 0}, "clip": False}, Z["sans"])

# ── [C] les calques du skin ──
print("[C] dz-skins-calques.js")
C = node(r"""
const M = await import(%s), H = await import(%s);
%s
%s
const out = {}, skin = %s, contexte = %s;
const sc = M.creerScene({largeur: 1280, hauteur: 720, doc, horloge, secrets: () => [{x: 10, y: 10, l: 50, h: 50, ecran: false}]});
sc.source("ecran", {readyState: 4}); sc.source("camera", {readyState: 4, videoWidth: 640, videoHeight: 480});
sc.ajouterCalque(M.calqueEcran()); sc.ajouterCalque(M.calqueClics()); sc.ajouterCalque(M.calqueEncart());
const logo = {complete: true, naturalWidth: 100, naturalHeight: 50};
const h = H.habiller(sc, skin, {contexte, T, images: {logo, fond: null}, camera: true, halo: true});
out.calques = sc.calques();
out.etat = {cadre: sc.etat.cadre, styleZoom: sc.etat.styleZoom, forme: sc.etat.forme, encart: sc.etat.encart};
const textes = () => ops.filter(o => o[0] === "fillText").map(o => o[1]);
ops.length = 0; sc.dessiner(1000); out.t0 = textes();                         // première image : t = 0 -> intro
const intro = skin.intro.duree_s * 1000;
ops.length = 0; sc.dessiner(1000 + intro + 50); out.t1 = textes();            // après l'intro, avant le bandeau
ops.length = 0; sc.dessiner(1000 + intro + skin.bandeau.debut_s * 1000 + 800); out.t2 = textes();
h.alerte({type: "abonne", nom: "Zoé"}); out.alerteRefus = h.alerte({type: "clavier"});
ops.length = 0; sc.dessiner(1000 + intro + skin.bandeau.debut_s * 1000 + 1300); out.t3 = textes();
ops.length = 0; sc.dessiner(1000 + intro + skin.bandeau.debut_s * 1000 + 1300 + 7000); out.t4 = textes();
h.ecran("pause"); ops.length = 0; sc.dessiner(1000 + 30000); out.t5 = textes(); h.ecran(null);
// l'ordre : le cache du caviardage (fillRect 10,10 transformé) vient APRÈS tous les dessins du skin
ops.length = 0; sc.dessiner(1000 + 30000);
const iCache = ops.map((o, i) => [o, i]).filter(([o]) => o[0] === "fillRect" && o[3] > 50 && o[3] < 70).map(([o, i]) => i);
const iSig = ops.findIndex(o => o[0] === "fillText" && String(o[1]).includes("DeepotusVideo"));
out.ordre = {iCache, iSig};
h.maj(Object.assign({}, skin, {signature: Object.assign({}, skin.signature, {actif: false})}));
ops.length = 0; sc.dessiner(1000 + 30000); out.t6 = textes();
let fini = false; const p = h.outro().then(v => { fini = v; });
ops.length = 0; sc.dessiner(1000 + 30500); out.t7 = textes();
out.encartOmbre = ops.some(o => o[0] === "=shadowBlur");
h.retirer();
out.apres = {calques: sc.calques(), cadre: sc.etat.cadre, styleZoom: sc.etat.styleZoom};
const r = (() => { try { sc.ajouterCalque({id: "skin-triche", z: 950, dessiner(){}}); return "ok"; } catch (e) { return "refus"; } })();
out.triche = r;
// un skin sans caméra ni halo : ni encart ni clics posés
const sc2 = M.creerScene({largeur: 640, hauteur: 360, doc, horloge, secrets: () => []});
sc2.ajouterCalque(M.calqueEcran());
H.habiller(sc2, skin, {contexte, T, images: {}});
out.sansCam = sc2.calques().map(c => c.id);
console.log(JSON.stringify(out));
""" % (json.dumps((SH / "dz-capture-scene.js").resolve().as_uri()), json.dumps(URL("dz-skins-calques.js")), FAUX_CANVAS, TFR,
       json.dumps(SKIN), json.dumps(CTX)))
ids = [c["id"] for c in C["calques"]]
check("C1 calques du skin posés et triés, tous sous 900, caviardage dernier",
      ids == ["skin-fond", "ecran", "skin-cadre", "clics", "encart", "skin-logo", "skin-bandeau", "skin-signature", "skin-alertes", "skin-carte", "caviardage"]
      and all(c["z"] < 900 for c in C["calques"][:-1]), C["calques"])
e = C["etat"]
check("C2 état : cadre (marge du skin), zoom stylé, forme et place de l'encart du skin, bord et ombre",
      e["cadre"] == {"marge": SKIN["cadre"]["marge"]} and e["styleZoom"] == {"k": SKIN["zoom"]["niveau"], "duree": SKIN["zoom"]["duree_ms"]}
      and e["forme"] == "cercle" and e["encart"]["x"] == SKIN["encart"]["x"] and e["encart"]["ombre"] is True and e["encart"]["couleur"] == "#ef4444", e)
check("C3 première image : la carte d'intro (nom de l'espace, slogans), ni bandeau ni signature",
      C["t0"] == ["Deepotus", "From the deep, for the deep."], C["t0"])
check("C4 après l'intro : la signature « Fait avec DeepotusVideo » seule", C["t1"] == [DICO["skins.signature.texte"]["fr"]], C["t1"])
check("C5 le bandeau titre entre après son délai", "Deepotus" in C["t2"] and "From the deep, for the deep." in C["t2"], C["t2"])
check("C6 alerte « abonné » affichée (type inconnu refusé), puis expirée",
      DICO["skins.defaut.abonne"]["fr"].replace("{nom}", "Zoé") in C["t3"] and C["alerteRefus"] is False
      and not any("Zoé" in x for x in C["t4"]), (C["t3"], C["t4"]))
check("C7 écran « pause » : la carte plein cadre, rien d'autre", C["t5"] == [DICO["skins.defaut.pause"]["fr"], "Deepotus"], C["t5"])
check("C8 le caviardage est peint APRÈS les dessins du skin", C["ordre"]["iCache"] and C["ordre"]["iSig"] >= 0
      and all(i > C["ordre"]["iSig"] for i in C["ordre"]["iCache"]), C["ordre"])
check("C9 signature désactivable (maj du skin)", not any("DeepotusVideo" in x for x in C["t6"]), C["t6"])
check("C10 outro jouée : sa carte (« Merci… » + espace), encart avec ombre",
      C["t7"][:2] == [DICO["skins.defaut.outro"]["fr"], "Deepotus"], C["t7"])
check("C11 retirer : calques du skin partis, clics et encart d'origine rendus, cadre et zoom remis",
      [c["id"] for c in C["apres"]["calques"]] == ["ecran", "clics", "encart", "caviardage"] and C["apres"]["cadre"] is None
      and C["apres"]["styleZoom"] is None, C["apres"])
check("C12 aucun calque au-dessus du caviardage (z ≥ 900 refusé par la scène)", C["triche"] == "refus")
check("C13 sans caméra ni halo : le skin ne pose ni encart ni clics", "encart" not in C["sansCam"] and "clics" not in C["sansCam"], C["sansCam"])

# ── [U] dz-skins.js et son branchement dans dz-capture.js, sous le faux DOM du banc de t315 ──
print("[U] dz-skins.js + dz-capture.js")
import ast                                                            # noqa: E402
_src = (BACKEND / "tests" / "test_capture_ecran.py").read_text("utf-8")
_v = {n.targets[0].id: n.value.value for n in ast.parse(_src).body
      if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ("FAUX", "MD_PANNE")}
DICO_CAP = json.loads((SH / "i18n" / "capture.json").read_text("utf-8"))
DICO_TOUT = dict(DICO_CAP, **DICO)
SID = "0123456789abcdef"
SKIN_U = dict(SKIN, id=SID, nom="Mon skin", livre=False, espace_id="deepotus", images=[], modifie="x",
              encart=dict(SKIN["encart"], forme="vif"))
DECOR = r"""
const LOG = [];
const LISTE = {espace: "deepotus", espace_nom: "Deepotus", choisi: "%s", skins: [{id: "%s", nom: "Mon skin", livre: false}],
  livres: [{id: "livre-neon", nom: "Néon", livre: true}]};
const DETAIL = {skin: %s, contexte: %s};
globalThis.fetch = async (u, o) => { const m = (o && o.method) || "GET"; LOG.push(m + " " + u);
  const rep = (j) => ({ok: true, status: 200, headers: {get: () => "application/json"}, json: async () => j});
  if (u === "/api/skins") return rep(LISTE);
  if (u === "/api/skins/%s") return rep(DETAIL);
  if (u === "/api/capture/sessions") return rep({id: "fedcba9876543210"});
  if (u.endsWith("/terminer")) return rep({fichier: "capture.mp4", job_id: "j", clics: {clics: 0, reconnus: 0}});
  return rep({}); };
globalThis.Image = function(){ const im = this; setTimeout(() => { im.naturalWidth = 64; im.naturalHeight = 64; im.complete = true; if (im.onload) im.onload(); }, 0); };
globalThis.MediaStream = function(l){ this.l = l || []; this.getTracks = () => this.l; this.getVideoTracks = () => this.l; this.getAudioTracks = () => []; };
const OPS = [];
const Ctx = () => new Proxy({}, {get: (t, k) => (k in t ? t[k] : (k === "createLinearGradient" ? () => ({addColorStop(){}}) :
  (k === "measureText" ? (s) => ({width: String(s).length * 7}) : (...a) => { OPS.push([k, a[0]]); }))), set: (t, k, v) => { t[k] = v; return true; }});
const creer = document.createElement;
document.createElement = (t) => { const n = creer(t); if (t === "canvas") { n.getContext = Ctx; n.captureStream = () => new MediaStream([]); }
  if (t === "video") n.play = () => Promise.resolve(); return n; };
globalThis.MediaRecorder = function(){ this.state = "inactive"; this.mimeType = "video/webm"; this.ec = {}; };
MediaRecorder.isTypeSupported = () => true;
MediaRecorder.prototype.addEventListener = function(t, f){ (this.ec[t] = this.ec[t] || []).push(f); };
MediaRecorder.prototype.start = function(){ this.state = "recording"; LOG.push("rec:start"); };
MediaRecorder.prototype.stop = function(){ this.state = "inactive"; LOG.push("rec:stop"); (this.ec.stop || []).forEach(f => f()); };
globalThis.setInterval = () => 1; globalThis.clearInterval = () => {};
const pause = (ms) => new Promise(ok => setTimeout(ok, ms || 5));
""" % (SID, SID, json.dumps(SKIN_U), json.dumps(CTX), SID)


def harnais_u(lang, corps):
    dico = json.dumps(DICO_TOUT)
    return ((_v["FAUX"] % (dico, lang, _v["MD_PANNE"])) + DECOR
            + "\nawait import(%s);\nawait import(%s);\n" % (json.dumps(URL("dz-skins.js")), json.dumps(URL("dz-capture.js"))) + corps)


U = node(harnais_u("fr", r"""
const out = {};
const formes = [];
const g = window.__dzSkins.groupeCapture({forme: (f) => formes.push(f)});
out.avant = g.valeur() === undefined ? null : g.valeur();
await pause(30);
const sel = g.noeud.querySelector("[data-dz-skins-choix]");
out.options = sel.enfants.map(o => [o.attrs.value, o.textContent, o.getAttribute("data-dz-brut") !== null]);
out.valeur = g.valeur(); out.formes = formes;
// la boîte de départ de l'enregistreur porte le groupe, et sa forme d'encart suit le skin
window.__dzCapture.ouvrir();
await pause(30);
const boite = document.querySelector("[data-dz-capture-boite]");
out.groupe = !!boite.querySelector("[data-dz-skins-groupe]");
out.forme = boite.querySelector('[data-dz-capture-option="forme"]').value;
boite.remove();
// une capture avec le skin : habillée AVANT la première image, l'outro jouée AVANT l'arrêt des pistes
const vrai = window.__dzSkins.habiller;
window.__dzSkins.habiller = async (scene, o) => { LOG.push("habiller:" + o.skin + ":" + OPS.length);
  const h = await vrai(scene, o); if (h) { const outro = h.outro; h.outro = () => { LOG.push("outro"); outro(); return Promise.resolve(true); }; } return h; };
const r = await window.__dzCapture.demarrer({skin: "%s", voix: false, camera: false, halo: true, zoom: true});
out.r = r;
const s = window.__dzCapture.session();
out.calques = s ? s.scene.calques().map(c => c.id) : null;
out.textes = OPS.filter(o => o[0] === "fillText").map(o => o[1]);
out.styleZoom = s ? s.scene.etat.styleZoom : null;
await window.__dzCapture.arreter();
out.log = LOG.filter(x => x === "outro" || x === "rec:stop" || x === "rec:start" || x.startsWith("habiller"));
console.log(JSON.stringify(out));
""" % SID))
check("U1 groupe « Habillage » : rien tant que la liste n'est pas lue (le skin de l'espace sera pris)", U["avant"] is None, U["avant"])
check("U2 options : sans habillage, skins de l'espace (nom brut), livrés traduits ; choix de l'espace sélectionné",
      U["options"] == [["", DICO["skins.capture.aucun"]["fr"], False], [SID, "Mon skin", True], ["livre-neon", DICO["skins.livre.neon"]["fr"], False]]
      and U["valeur"] == SID, U["options"])
check("U3 la forme d'encart du skin est proposée à la boîte", U["formes"] == ["vif"] and U["groupe"] is True and U["forme"] == "vif", U)
check("U4 la capture démarre habillée : calques du skin posés, zoom stylé", U["r"]["ok"] is True and U["calques"]
      and "skin-carte" in U["calques"] and "skin-bandeau" in U["calques"]
      and U["styleZoom"] == {"k": SKIN["zoom"]["niveau"], "duree": SKIN["zoom"]["duree_ms"]}, U)
check("U5 habillée AVANT la première image : aucun dessin avant habiller, et la première image est l'intro",
      U["log"][0] == "habiller:" + SID + ":0" and U["textes"][:1] == ["Deepotus"], (U["log"], U["textes"][:4]))
log = U["log"]
check("U6 l'outro est jouée AVANT l'arrêt des pistes", "outro" in log and "rec:stop" in log and log.index("outro") < log.index("rec:stop"), log)

U5 = node(harnais_u("en", r"""
// un skin qui ne répond pas : la capture part sans habillage (jamais bloquée)
window.__dzSkins.habiller = () => new Promise(() => {});
const t0 = Date.now();
const r = await window.__dzCapture.demarrer({skin: "", voix: false, camera: false, halo: true});
const s = window.__dzCapture.session();
const out = {r, ids: s.scene.calques().map(c => c.id), sansSkin: s.scene.etat.sansSkin, ms: Date.now() - t0};
await window.__dzCapture.arreter();
console.log(JSON.stringify(out));
"""))
check("U7 habillage en panne (jamais résolu) : la capture démarre sans skin après le délai (4 s au plus)",
      U5["r"]["ok"] is True and U5["ids"] == ["ecran", "clics", "caviardage"] and U5["sansSkin"] is True and U5["ms"] < 6000, U5)

# ── [P] livraison ──
print("[P] livraison")
TXT = (SH / "dz-skins.js").read_text("utf-8")
LOG_ = (SH / "dz-skins-logique.js").read_text("utf-8")
CAL = (SH / "dz-skins-calques.js").read_text("utf-8")
check("P1 copies shared == dist (trois modules des skins et ceux de la capture qu'ils touchent)",
      all((DI / f).is_file() and (DI / f).read_bytes() == (SH / f).read_bytes()
          for f in FICHIERS + ["dz-capture.js", "dz-capture-logique.js", "dz-capture-scene.js"]))
idx = (REPO / "frontend" / "dist" / "index.html").read_text("utf-8")
balise = '<script type="module" src="/shared/dz-skins.js"></script>'
check("P2 index.html charge dz-skins.js une fois, en module, avant dz-capture.js",
      idx.count("dz-skins") == 1 and idx.count(balise) == 1 and idx.index(balise) < idx.index("/shared/dz-capture.js"))
sans_comm = lambda s: re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", s, flags=re.S))   # noqa: E731
check("P3 ni alert/confirm/prompt natifs, aucun emoji", not any(re.search(r"(?<![\w.$])(?:window\.)?(?:confirm|alert|prompt)\(", sans_comm(x))
                                                                for x in (TXT, LOG_, CAL))
      and not any(re.search("[\U0001F300-\U0001FAFF☀-➿]", x) for x in (TXT, LOG_, CAL)))
check("P4 angles vifs : aucun border-radius non nul dans l'éditeur", not re.findall(r"border-radius:[1-9]", TXT)
      and "border-radius:0" in TXT)
check("P5 une seule écoute clavier : le piège Tab/Échap de l'éditeur", len(re.findall(r'addEventListener\("key', sans_comm(TXT))) == 1
      and 'voile.addEventListener("keydown"' in TXT)
check("P6 le logo de l'APPLICATION n'est jamais lu (règle du logo figé) : seul le logo de l'espace ou du skin",
      not any(x in TXT + CAL for x in ("/api/branding", "deepotus-logo", "brand-kits")) and "logo_espace" in TXT)
# clés employées : littérales + dérivées (livrés, sections, champs, options, lecture)
cles = set(re.findall(r'"(skins\.[a-z_]+\.[a-z_]+)"', TXT + LOG_ + CAL))
bloc = TXT[TXT.index("const CHAMPS = ["):TXT.index("const ROLES")]
sections = re.findall(r'^\s{4}\["(\w+)", \[', bloc, re.M)
derivees = {"skins.livre." + x.replace("livre-", "") for x in LIVRES} | {"skins.section." + s for s in sections}
morceaux = re.split(r'^\s{4}\["(\w+)", ', bloc, flags=re.M)
for sec, corps in zip(morceaux[1::2], morceaux[2::2]):
    for cle, typ in re.findall(r'\["([\w.@]+)", "(case|plage|texte|choix|police|hex|kit|ref|image)"',
                               re.sub(r'"choix", \[[^\]]*\]', '"choix"', corps)):
        derivees.add("skins.couleur." + cle if sec == "couleurs" else "skins.police." + cle if sec == "polices"
                     else "skins.champ." + cle.replace(".", "_").replace("@", "image_"))
    for opts in re.findall(r'"choix", \[([^\]]*)\]', corps):
        derivees |= {"skins.option." + o.replace("-", "_") for o in re.findall(r'"([\w-]+)"', opts)}
derivees |= {"skins.couleur." + r for r in ("principale", "accent", "texte", "fond")}
derivees |= {"skins.jouer." + j for j in re.findall(r'lecture\("(\w+)"', TXT)}
derivees |= {"skins.editeur.image_posee", "skins.editeur.image_otee", "skins.editeur.enregistrer_copie"}
emploi = cles | derivees
check("P7 toutes les clés employées existent", not (emploi - set(DICO)), sorted(emploi - set(DICO)))
check("P8 toutes les clés du fichier sont employées", not (set(DICO) - emploi), sorted(set(DICO) - emploi))
var = lambda s: sorted(re.findall(r"\{(\w+)\}", s))                  # noqa: E731
check("P9 FR/EN non vides, mêmes variables, clés à 3 segments au moins",
      all(v["fr"].strip() and v["en"].strip() and var(v["fr"]) == var(v["en"]) and re.fullmatch(r"[a-z0-9]+(\.[a-z0-9_]+){2,}", k)
          for k, v in DICO.items()))
tout = {}
for f in sorted((SH / "i18n").glob("*.json")):
    for k, v in json.loads(f.read_text("utf-8")).items():
        tout.setdefault(v["fr"], set()).add(v["en"])
check("P10 une phrase FR = une seule traduction dans toute l'interface", not [k for k, v in DICO.items() if len(tout[v["fr"]]) > 1],
      [k for k, v in DICO.items() if len(tout[v["fr"]]) > 1])
dico_js = (SH / "dz-i18n-dico.js").read_text("utf-8")
check("P11 dictionnaire assemblé (shared == dist) avec les clés skins.*",
      all(json.dumps(k, ensure_ascii=False) in dico_js for k in DICO) and (DI / "dz-i18n-dico.js").read_bytes() == (SH / "dz-i18n-dico.js").read_bytes())
check("P12 livrés du serveur tous traduits à l'écran", all("skins.livre." + x.replace("livre-", "") in DICO for x in LIVRES))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
