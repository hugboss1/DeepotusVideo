# -*- coding: utf-8 -*-
"""SV1 (14/11/2026) — le STUDIO VIRTUEL 3D côté écran, joué sous node (aucun navigateur, aucun WebGL).
Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md.
[L] dz-studiov-logique.js : couleurs (kit de l'espace, #hex, rôle), champ d'une focale, pose d'une caméra (fixe = sa
    place ; mouvement borné par l'amplitude, nul en moyenne ; orbite à distance constante), fondu entre caméras
    (bornes, milieu), régie (bascule, même caméra = rien, indice ramené), budget de lumières (clé, appoint, contre
    toujours ; plafond selon la qualité ; ambiance jamais comptée), couvrir ;
[D] scène t315 étendue — l'ÉCRAN DÉPORTÉ : hors du mode, rien ne change ; en mode déporté, l'écran et les clics ne sont
    plus peints dans l'image, le caviardage de l'image se tait, et le canevas déporté reçoit l'écran PUIS le cache de
    chaque secret ; mesure en panne -> canevas noir, jamais la source ; un calque tiers qui écrit `s.deporte` ne fait
    PAS taire le caviardage de l'image ; ecranDeporte(false) remet l'écran dans l'image ;
[H] habillage (lot SVH), toujours sous node : usage d'une matière (place dans la pièce, déclaré, deviné), répétition
    d'une texture, pose d'une matière (la recette d'entrée n'est jamais modifiée, la lueur et l'usage sont gardés),
    ambiance lumineuse (clé, appoint, contre ; néons et objets lumineux à tour de rôle), style complet (une matière
    par usage + son ambiance), objet neuf posé au sol, au mur ou au plafond, DANS la pièce ;
[P] livraison : copies shared == dist, balise avant dz-capture.js, three.js chargé depuis /assets (aucun CDN), la
    source « ecran » n'entre jamais dans le moteur (seul le canevas déporté), ni alert/confirm/prompt ni emoji ni
    innerHTML, angles vifs, clés studiov.* FR/EN employées et assemblées, un nom traduit par décor livré.
Run (depuis backend/) : & $PY tests/test_studiov_ecran.py"""
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
FICHIERS = ["dz-studiov.js", "dz-studiov-logique.js", "dz-studiov-moteur.js"]
DICO = json.loads((SH / "i18n" / "studiov.json").read_text("utf-8"))
URL = lambda nom: (SH / nom).resolve().as_uri()               # noqa: E731
LIVRES = json.loads((BACKEND / "app" / "studiov" / "livres.json").read_text("utf-8"))


def node(script: str) -> dict:
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzstudiovjs_"))
    f = d / "banc.mjs"
    f.write_text(script, "utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    out = r.stdout.strip().splitlines()
    try:
        return json.loads(out[-1])
    except Exception:                                       # noqa: BLE001
        return {"_erreur": (r.stderr or r.stdout)[-900:]}


print("[L] logique")
L = node(r"""
import * as G from "%s";
const cx = {kit: {brand_color: "#112233", accent_color: "pas-une-couleur"}};
const pal = G.palette(cx);
const cam = {x: 0, y: 1.4, z: 3, vers: [0, 1.2, 0], focale: 35, mouvement: "fixe", amplitude: 0.5, periode_s: 10};
const ecart = (m) => { let max = 0, sx = 0, sz = 0, n = 0; for (let t = 0; t < 40000; t += 50) { const p = G.poseCamera({...cam, mouvement: m}, t);
  max = Math.max(max, Math.hypot(p.x - cam.x, p.z - cam.z)); sx += p.x - cam.x; sz += p.z - cam.z; n++; } return {max, moy: Math.hypot(sx / n, sz / n)}; };
const orb = []; for (let t = 0; t < 20000; t += 100) { const p = G.poseCamera({...cam, mouvement: "orbite"}, t); orb.push(Math.hypot(p.x - 0, p.z - 0)); }
const a = G.poseCamera(cam, 0), b = G.poseCamera({...cam, x: 2, z: 1, focale: 50}, 0);
const r = G.regie(3); const r0 = r.courante; const b1 = r.basculer(1, 1000); const b2 = r.basculer(1, 1500); const dep = r.depuis; const b7 = r.basculer(7, 2000);
const cams = [cam, {...cam, x: 2}, {...cam, x: -2}];
const r2 = G.regie(3); r2.basculer(1, 1000);
const lum = [{type: "neon", intensite: 9}, {type: "ambiance", intensite: 5}, {type: "contre", intensite: 1}, {type: "appoint", intensite: 1},
  {type: "cle", intensite: 1}, {type: "neon", intensite: 3}, {type: "neon", intensite: 4}, {type: "neon", intensite: 2}, {type: "neon", intensite: 0}];
console.log(JSON.stringify({
  pal, role: G.couleur("accent", pal), hex: G.couleur("#ABCDEF", pal), inconnu: G.couleur("rose", pal, "#010203"), entier: G.entier("#ff0000"),
  champ35: G.champ(35), champ50: G.champ(50), champBorne: G.champ(1) === G.champ(14),
  fixe: G.poseCamera(cam, 12345), resp: ecart("respiration"), trav: ecart("travelling"), pous: ecart("poussee"),
  orbMin: Math.min(...orb), orbMax: Math.max(...orb),
  m0: G.melanger(a, b, 0), m1: G.melanger(a, b, 1), mMilieu: G.melanger(a, b, 0.5), mHors: G.melanger(a, b, 7).x,
  r0, b1, b2, dep, b7, pendant: r2.pose(cams, 1000 + G.FONDU_CAMERA / 2).x, apres: r2.pose(cams, 1000 + G.FONDU_CAMERA + 1).x, avant: r2.pose(cams, 1000).x,
  legere: [...G.budgetLumieres(lum, "legere")].sort(), haute: [...G.budgetLumieres(lum, "haute")].sort(),
  couvrir: G.couvrir(1280, 720, 400, 400), z: [G.Z_STUDIO, G.Z_VIGNETTE],
  nom: G.nomDecor({id: "livre-tech", livre: true, nom: "x"}, (k) => k === "studiov.livre.tech" ? "Traduit" : k),
  nomSans: G.nomDecor({id: "livre-zz", livre: true, nom: "Brut"}, (k) => k), nomEspace: G.nomDecor({id: "ab", livre: false, nom: "Mien"}, () => "T"),
}));
""" % URL("dz-studiov-logique.js"))
check("L0 le module se joue sous node", "_erreur" not in L, L.get("_erreur"))
if "_erreur" not in L:
    check("L1 palette : kit de l'espace, valeur douteuse -> défaut", L["pal"]["principale"] == "#112233" and L["pal"]["accent"] == "#00e5ff")
    check("L2 couleur : rôle, #hex en minuscules, inconnu -> défaut donné ; entier", L["role"] == "#00e5ff" and L["hex"] == "#abcdef"
          and L["inconnu"] == "#010203" and L["entier"] == 0xff0000)
    check("L3 champ : 35 mm ≈ 37,8°, 50 mm ≈ 27°, focale bornée", abs(L["champ35"] - 37.85) < 0.1 and abs(L["champ50"] - 26.99) < 0.1 and L["champBorne"])
    check("L4 caméra fixe : sa place, à tout instant", L["fixe"]["x"] == 0 and L["fixe"]["y"] == 1.4 and L["fixe"]["z"] == 3)
    for nom in ("resp", "trav", "pous"):
        check(f"L5 mouvement {nom} : borné par l'amplitude, nul en moyenne (aucune dérive)", 0.3 < L[nom]["max"] <= 0.5001 and L[nom]["moy"] < 0.03, L[nom])
    check("L6 orbite : distance à la cible constante", abs(L["orbMin"] - 3) < 1e-6 and abs(L["orbMax"] - 3) < 1e-6, (L["orbMin"], L["orbMax"]))
    check("L7 fondu : 0 = départ, 1 = arrivée, milieu = moyenne, hors borne tenu", L["m0"]["x"] == 0 and L["m1"]["x"] == 2 and abs(L["mMilieu"]["x"] - 1) < 1e-9
          and abs(L["mMilieu"]["champ"] - (L["champ35"] + L["champ50"]) / 2) < 1e-9 and L["mHors"] == 2)
    check("L8 régie : bascule, même caméra = rien (l'instant ne bouge pas), indice ramené dans la liste",
          L["r0"] == 0 and L["b1"] == 1 and L["b2"] == 1 and L["dep"] == 1000 and L["b7"] == 1)
    check("L9 régie : fondu de l'ancienne caméra vers la neuve", L["avant"] == 0 and 0.9 < L["pendant"] < 1.1 and L["apres"] == 2, (L["avant"], L["pendant"], L["apres"]))
    check("L10 budget léger : clé, appoint, contre puis les néons les plus forts (5) ; ambiance et lumière éteinte jamais",
          L["legere"] == [0, 2, 3, 4, 6] and L["haute"] == [0, 2, 3, 4, 5, 6, 7], (L["legere"], L["haute"]))
    check("L11 couvrir : l'image déborde et reste centrée", L["couvrir"]["h"] == 400 and abs(L["couvrir"]["l"] - 711.11) < 0.1 and L["couvrir"]["x"] < 0)
    check("L12 le studio est sous le fond du skin (40) et sous l'écran (100)", L["z"][0] < L["z"][1] < 40)
    check("L13 nom d'un décor : clé traduite, sinon nom du serveur ; un décor de l'espace garde son nom",
          L["nom"] == "Traduit" and L["nomSans"] == "Brut" and L["nomEspace"] == "Mien")

print("[H] habillage")
Hn = node(r"""
import * as G from "%s";
const decor = {piece: {l: 6, p: 5, h: 2.8, sol: "sol", mur: "mur", fond: "fond", plafond: "plafond"},
  matieres: {sol: {couleur: "#111111", rugosite: 0.5, metal: 0, emission: 0, motif: "parquet", echelle: 1, texture: "", teinte: false, usage: "autre"},
    mur: {couleur: "#222222", rugosite: 0.9, metal: 0, emission: 0, motif: "uni", echelle: 1, texture: "", teinte: false, usage: "autre"},
    fond: {couleur: "#333333", rugosite: 0.9, metal: 0, emission: 0, motif: "brique", echelle: 1, texture: "", teinte: false, usage: "autre"},
    plafond: {couleur: "#444444", rugosite: 0.9, metal: 0, emission: 0, motif: "uni", echelle: 1, texture: "", teinte: false, usage: "autre"},
    chene: {couleur: "#555555", rugosite: 0.6, metal: 0, emission: 0, motif: "uni", echelle: 2, texture: "", teinte: false, usage: "autre"},
    assise: {couleur: "#666666", rugosite: 0.6, metal: 0, emission: 0, motif: "uni", echelle: 1, texture: "", teinte: false, usage: "cuir"},
    alu: {couleur: "#777777", rugosite: 0.3, metal: 0.9, emission: 0, motif: "uni", echelle: 1, texture: "", teinte: false, usage: "autre"},
    lueur: {couleur: "#18e0ff", rugosite: 0.4, metal: 0, emission: 3, motif: "uni", echelle: 1, texture: "", teinte: false, usage: "bois"},
    divers: {couleur: "#888888", rugosite: 0.4, metal: 0, emission: 0, motif: "uni", echelle: 1, texture: "", teinte: false, usage: "autre"}},
  lumieres: [{type: "cle", couleur: "#000001"}, {type: "appoint", couleur: "#000002"}, {type: "contre", couleur: "#000003"}, {type: "contre", couleur: "#000004"},
    {type: "neon", couleur: "#000005"}, {type: "neon", couleur: "#000006"}, {type: "ambiance", couleur: "#000007"}, {type: "fenetre", couleur: "#000008"}],
  objets: [{type: "bureau", couleur: null}, {type: "ruban_led", couleur: "#000009"}, {type: "lampe", couleur: null}],
  enseigne: {style: "neon", couleur: "#00000a"}};
const avant = JSON.stringify(decor);
const usages = Object.fromEntries(Object.keys(decor.matieres).map((k) => [k, G.usageDe(decor, k)]));
const A = {id: "a", cle: "#aaaaaa", appoint: "#bbbbbb", contre: "#cccccc", neons: ["#111111", "#222222"], ambiance: "#dddddd"};
const amb = G.appliquerAmbiance(decor, A, ["ruban_led", "lampe"]);
const style = {id: "s", ambiance: "a", matieres: {sol: {texture: "stu:parquet", teinte: false}, mur: {texture: "stu:platre", couleur: "accent", teinte: true},
  bois: {texture: "", couleur: "#f2f2ee", rugosite: 0.16, metal: 0, motif: "uni", teinte: false}, metal: {texture: "", couleur: "#d9a941", rugosite: 0.22, metal: 1, motif: "uni", teinte: false}}};
const st = G.appliquerStyle(decor, style, [A], ["ruban_led", "lampe"]);
const pose = G.poserMatiere(decor, "chene", {texture: "cat:noyer"});
const sansAmb = G.appliquerStyle(decor, {id: "x", ambiance: "absente", matieres: {}}, [A], []);
const neufs = ["bureau", "cadre", "mur_lattes", "suspension", "neon_texte"].map((t) => G.objetNeuf(decor, t));
console.log(JSON.stringify({usages, intact: JSON.stringify(decor) === avant,
  rep: [G.repetition(2, 1), G.repetition(0.5, 2), G.repetition(0, 1), G.repetition(1, 99)],
  lum: amb.lumieres.map((l) => l.couleur), obj: amb.objets.map((o) => o.couleur), ens: amb.enseigne.couleur,
  st: {sol: st.matieres.sol, mur: st.matieres.mur, fond: st.matieres.fond, chene: st.matieres.chene, alu: st.matieres.alu, lueur: st.matieres.lueur,
       divers: st.matieres.divers, assise: st.matieres.assise, cle: st.lumieres[0].couleur},
  pose: pose.matieres.chene, inconnue: JSON.stringify(G.poserMatiere(decor, "absente", {texture: "stu:x"})) === avant,
  sansAmb: sansAmb.lumieres[0].couleur, neufs, types: G.TYPES.length, muraux: G.MURAUX.every((t) => G.TYPES.includes(t))}));
""" % URL("dz-studiov-logique.js"))
check("H0 le module se joue sous node", "_erreur" not in Hn, Hn.get("_erreur"))
if "_erreur" not in Hn:
    check("H1 usage : la place dans la pièce (sol, murs, plafond) passe avant tout ; puis l'usage déclaré ; puis le nom, le motif ou le métal ; sinon « autre »",
          Hn["usages"] == {"sol": "sol", "mur": "mur", "fond": "mur", "plafond": "plafond", "chene": "bois", "assise": "cuir", "alu": "metal", "lueur": "bois", "divers": "autre"}, Hn["usages"])
    check("H2 aucune fonction ne modifie la recette qu'on lui donne ; une clé inconnue ne change rien", Hn["intact"] and Hn["inconnue"])
    check("H3 répétition : 1 / (taille × échelle), bornée", Hn["rep"][0] == 0.5 and Hn["rep"][1] == 1 and abs(Hn["rep"][2] - 1) < 1e-9 and abs(Hn["rep"][3] - 0.1) < 1e-9, Hn["rep"])
    check("H4 ambiance : clé et fenêtre, appoint, premier contre, ambiance ; le second contre, les néons puis les objets lumineux prennent les néons à tour de rôle",
          Hn["lum"] == ["#aaaaaa", "#bbbbbb", "#cccccc", "#111111", "#222222", "#111111", "#dddddd", "#aaaaaa"] and Hn["obj"] == [None, "#222222", "#111111"]
          and Hn["ens"] == "#111111", (Hn["lum"], Hn["obj"], Hn["ens"]))
    s7 = Hn["st"]
    check("H5 style : la texture remplace le motif (sol), la teinte et la couleur du kit passent (murs et mur du fond), une finition ôte la texture (bois, métal)",
          s7["sol"]["texture"] == "stu:parquet" and s7["sol"]["motif"] == "uni" and s7["sol"]["teinte"] is False and s7["sol"]["rugosite"] == 0.8
          and s7["mur"]["texture"] == "stu:platre" and s7["mur"]["couleur"] == "accent" and s7["mur"]["teinte"] is True and s7["fond"]["texture"] == "stu:platre"
          and s7["chene"]["texture"] == "" and s7["chene"]["couleur"] == "#f2f2ee" and s7["chene"]["rugosite"] == 0.16 and s7["chene"]["echelle"] == 1
          and s7["alu"]["metal"] == 1 and s7["alu"]["couleur"] == "#d9a941", s7)
    check("H6 style : une matière lumineuse garde sa lueur, un usage sans matière dans le style reste tel quel, l'ambiance du style est posée ; ambiance inconnue = aucune",
          s7["lueur"]["emission"] == 3 and s7["lueur"]["texture"] == "" and s7["lueur"]["couleur"] == "#18e0ff" and s7["divers"]["couleur"] == "#888888"
          and s7["assise"]["couleur"] == "#666666" and s7["cle"] == "#aaaaaa" and Hn["sansAmb"] == "#000001", s7)
    check("H7 poser une matière : la texture ôte le motif, l'échelle revient à 1, l'usage est gardé", Hn["pose"]["texture"] == "cat:noyer" and Hn["pose"]["motif"] == "uni"
          and Hn["pose"]["echelle"] == 1 and Hn["pose"]["usage"] == "autre" and Hn["pose"]["teinte"] is False, Hn["pose"])
    n7 = Hn["neufs"]
    check("H8 objet neuf : au sol devant le présentateur, au mur du fond à hauteur d'yeux (les tasseaux à 1,2 m), la suspension au plafond — toujours DANS la pièce",
          n7[0]["y"] == 0 and n7[0]["z"] == 0.9 and n7[1]["y"] == 1.6 and abs(n7[1]["z"] + 2.48) < 1e-9 and n7[2]["y"] == 1.2 and n7[3]["y"] == 2.8
          and all(abs(o["x"]) <= 3 and -2.5 <= o["z"] <= 2.5 and o["e"] == 1 for o in n7), n7)
    check("H9 127 types ; chaque type mural est au catalogue", Hn["types"] == 127 and Hn["muraux"], Hn["types"])

print("[D] écran déporté (scène t315)")
D = node(r"""
import { creerScene, calqueEcran, calqueClics } from "%s";
const journal = [];
function Ctx(nom){ const ops = []; const c = { ops, nom, save(){}, restore(){}, beginPath(){}, rect(){}, clip(){}, arc(){}, stroke(){}, fillText(){},
  setTransform(){}, strokeRect(){}, fillRect(x, y, l, h){ ops.push(["fill", c.fillStyle, x, y, l, h]); journal.push([nom, "fill", c.fillStyle]); },
  drawImage(v){ ops.push(["image", v && v.nom]); journal.push([nom, "image", v && v.nom]); }, measureText: () => ({width: 10}) };
  return c; }
let n = 0;
const doc = { createElement(){ const nom = "canvas" + (n++); const ctx = Ctx(nom); return { nom, width: 0, height: 0, getContext: () => ctx, ctx }; } };
const video = { nom: "SOURCE_ECRAN", readyState: 4 };
let mesure = () => [{x: 10, y: 20, l: 100, h: 30}];
const scene = creerScene({ largeur: 640, hauteur: 360, doc, maintenant: () => 1000, secrets: () => mesure() });
scene.source("ecran", video); scene.ajouterCalque(calqueEcran()); scene.ajouterCalque(calqueClics());
const image = scene.canvas.ctx;
const vider = () => { image.ops.length = 0; journal.length = 0; };
scene.dessiner(1000);
const sans = { ecran: image.ops.filter(o => o[0] === "image").length, cache: image.ops.filter(o => o[0] === "fill" && o[1] === "#15181d").length, canevas: n };
// un calque tiers tente de faire taire le caviardage en écrivant s.deporte
scene.ajouterCalque({ id: "pirate", z: 50, dessiner(ctx, s){ s.deporte = true; } });
vider(); scene.dessiner(1000);
const pirate = { cache: image.ops.filter(o => o[0] === "fill" && o[1] === "#15181d").length };
scene.retirerCalque("pirate");
// mode déporté
const dep = scene.ecranDeporte(true), meme = scene.ecranDeporte(true) === dep;
vider(); scene.dessiner(1000);
const avec = { ecranImage: image.ops.filter(o => o[0] === "image").length, cacheImage: image.ops.filter(o => o[0] === "fill" && o[1] === "#15181d").length,
  taille: [dep.width, dep.height], ops: dep.ctx.ops.map(o => o[0] + ":" + (o[1] || "")) };
const iImg = dep.ctx.ops.findIndex(o => o[0] === "image"), iCache = dep.ctx.ops.findIndex(o => o[0] === "fill" && o[1] === "#15181d");
// mesure en panne : canevas noir, jamais la source
mesure = () => { throw new Error("panne"); };
dep.ctx.ops.length = 0; vider(); scene.dessiner(1000);
const panne = { images: dep.ctx.ops.filter(o => o[0] === "image").length, noir: dep.ctx.ops.some(o => o[0] === "fill" && o[1] === "#000") };
mesure = () => "pas une liste";
dep.ctx.ops.length = 0; scene.dessiner(1000);
const fausse = { images: dep.ctx.ops.filter(o => o[0] === "image").length };
// source pas prête : noir
mesure = () => []; video.readyState = 1; dep.ctx.ops.length = 0; scene.dessiner(1000);
const pasPrete = { images: dep.ctx.ops.filter(o => o[0] === "image").length };
video.readyState = 4;
// retour dans l'image
mesure = () => [{x: 10, y: 20, l: 100, h: 30}];
const rendu = scene.ecranDeporte(false);
vider(); scene.dessiner(1000);
const retour = { rendu, ecran: image.ops.filter(o => o[0] === "image").length, cache: image.ops.filter(o => o[0] === "fill" && o[1] === "#15181d").length };
console.log(JSON.stringify({ sans, pirate, meme, avec, iImg, iCache, panne, fausse, pasPrete, retour }));
""" % URL("dz-capture-scene.js"))
check("D0 la scène se joue sous node", "_erreur" not in D, D.get("_erreur"))
if "_erreur" not in D:
    check("D1 hors du mode : l'écran est dans l'image, son secret caché, aucun canevas en plus", D["sans"] == {"ecran": 1, "cache": 1, "canevas": 1}, D["sans"])
    check("D2 un calque tiers qui écrit s.deporte ne fait PAS taire le caviardage de l'image", D["pirate"]["cache"] == 1, D["pirate"])
    check("D3 mode déporté : ni écran ni cache dans l'image ; un seul canevas déporté, à la taille de la scène",
          D["avec"]["ecranImage"] == 0 and D["avec"]["cacheImage"] == 0 and D["meme"] and D["avec"]["taille"] == [640, 360], D["avec"])
    check("D4 le canevas déporté reçoit l'écran PUIS le cache du secret", 0 <= D["iImg"] < D["iCache"], D["avec"]["ops"])
    check("D5 mesure en panne ou fausse : canevas noir, la source n'y entre pas", D["panne"] == {"images": 0, "noir": True} and D["fausse"]["images"] == 0, (D["panne"], D["fausse"]))
    check("D6 source pas prête : rien n'est peint", D["pasPrete"]["images"] == 0)
    check("D7 ecranDeporte(false) : l'écran et son cache reviennent dans l'image", D["retour"] == {"rendu": None, "ecran": 1, "cache": 1}, D["retour"])

print("[P] livraison")
for f in FICHIERS + ["dz-capture.js", "dz-capture-scene.js"]:
    check(f"P1 {f} : copie dist identique", (SH / f).read_bytes() == (DI / f).read_bytes())
index = (REPO / "frontend" / "dist" / "index.html").read_text("utf-8")
check("P2 balise dz-studiov.js, AVANT dz-capture.js", 0 < index.find('src="/shared/dz-studiov.js"') < index.find('src="/shared/dz-capture.js"'))
sources = {f: (SH / f).read_text("utf-8") for f in FICHIERS}
tout = "\n".join(sources.values())
check("P3 three.js vient de /assets/three (embarqué), aucun CDN", '"/assets/three/three.module.min.js"' in sources["dz-studiov.js"]
      and not re.search(r"https?://(?!127\.0\.0\.1)", tout))
check("P4 la source « ecran » n'entre jamais dans le moteur : seul le canevas de scene.ecranDeporte y va",
      "sources.ecran" not in tout and "scene.ecranDeporte(true)" in sources["dz-studiov.js"] and "ecran, camera: s.sources.camera" in sources["dz-studiov.js"])
check("P5 ni alert/confirm/prompt, ni innerHTML, ni emoji", not re.search(r"\b(alert|confirm|prompt)\(", tout) and "innerHTML" not in tout
      and not re.search("[\U0001F300-\U0001FAFF☀-➿]", tout))
check("P6 angles vifs : aucun border-radius autre que 0", not re.search(r"border-radius:(?!0[;\"])", sources["dz-studiov.js"]))
# toute clé écrite en toutes lettres : T("…"), mais aussi celles passées aux aides du décorateur (curseur, titre)
cles = {k for k in re.findall(r'"(studiov\.[a-z_.0-9]+)"', tout) if not k.endswith(".")} | {"studiov.qualite.legere", "studiov.qualite.haute", "studiov.niveau.direct", "studiov.niveau.fabrique"}
check("P7 chaque clé employée existe en FR et EN", all(k in DICO and DICO[k].get("fr") and DICO[k].get("en") for k in cles), sorted(k for k in cles if k not in DICO))
# les clés composées à l'exécution (T("studiov.objet." + type)) : leur préfixe est relevé, leurs valeurs sont vérifiées en P12
prefixes = {k for k in re.findall(r'T\("(studiov\.[a-z_.0-9]+)"', tout) if k.endswith(".")} | {"studiov.livre."}
check("P8 aucune clé orpheline (hors noms des décors livrés et clés composées)", all(k in cles or any(k.startswith(p) for p in prefixes) for k in DICO),
      sorted(k for k in DICO if k not in cles and not any(k.startswith(p) for p in prefixes)))
check("P9 un nom FR/EN par décor livré, le FR égal au nom du serveur",
      all(DICO.get("studiov.livre." + k[6:], {}).get("fr") == v["nom"] and DICO["studiov.livre." + k[6:]].get("en") for k, v in LIVRES.items()))
assemble = (SH / "dz-i18n-dico.js").read_text("utf-8")
check("P10 clés assemblées dans dz-i18n-dico.js", all(k in assemble for k in DICO))
sys.path.insert(0, str(BACKEND))
from app.services import studiov as SV                                   # noqa: E402
from app.services import studiov_habillage as HV                         # noqa: E402
composees = ([f"studiov.objet.{t}" for t in SV.TYPES_OBJET] + [f"studiov.famille.{f}" for f in SV.CATALOGUE] + [f"studiov.usage.{u}" for u in SV.USAGES]
             + [f"studiov.lumiere.{t}" for t in SV.TYPES_LUMIERE] + [f"studiov.enseigne.{s}" for s in SV.STYLES_ENSEIGNE]
             + [f"studiov.style.{s['id']}" for s in HV.STYLES] + [f"studiov.ambiance.{a['id']}" for a in HV.AMBIANCES]
             + [f"studiov.finition.{f['id']}" for f in HV.FINITIONS] + [f"studiov.surface.{s}" for s in ("sol", "fond", "mur", "plafond")]
             + [f"studiov.deco.onglet.{o}" for o in ("style", "matieres", "objets", "lumieres", "enseigne")] + ["studiov.deco.role.principale", "studiov.deco.role.accent"])
check("P12 chaque clé composée a son texte FR et EN : objets, catégories, usages, lumières, enseignes, styles, ambiances, finitions, surfaces, onglets",
      all(k in DICO and DICO[k].get("fr") and DICO[k].get("en") for k in composees), sorted(k for k in composees if k not in DICO)[:12])
check("P13 rien d'orphelin parmi les clés composées", all(k in cles or k in composees or k.startswith("studiov.livre.") for k in DICO),
      sorted(k for k in DICO if k not in cles and k not in composees and not k.startswith("studiov.livre."))[:12])
moteur_src = sources["dz-studiov-moteur.js"]
check("P14 le moteur ne fabrique aucune adresse depuis la recette : les textures viennent de l'index servi, les polices de /fonts sous un nom vérifié",
      "/api/" not in moteur_src and "INDEX[m.texture]" in moteur_src and "url(/fonts/${nom}.ttf)" in moteur_src and "/^[A-Za-z0-9]{2,24}$/.test(nom" in moteur_src)
check("P15 le décorateur enregistre par le serveur (PUT) et ne retouche jamais un décor livré", 'api("PUT", "/api/studiov/" + encodeURIComponent(id), d.decor)' in sources["dz-studiov.js"]
      and "if (!apercu || apercu.livre || !apercu.habit) return;" in sources["dz-studiov.js"])
capture = (SH / "dz-capture.js").read_text("utf-8")
check("P11 la capture pose le studio APRÈS le skin et AVANT la première image ; l'option « decor » part de la boîte",
      0 < capture.find("__dzSkins.habiller(scene") < capture.find("__dzStudiov.habiller(scene") < capture.find("scene.dessiner();")
      and "decor: studio ? studio.valeur() : undefined" in capture and "studio ? studio.noeud : null" in capture)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
