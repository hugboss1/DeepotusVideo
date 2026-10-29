# -*- coding: utf-8 -*-
"""t376 (29/10/2026) — l'écran du choix de pose : Game Assets 3D (maillon de queue dzpose) et 3D Studio (saisie L9).

Ce que le banc prouve :
  1. le bundle : l'interrupteur « T-pose » a disparu, le champ « Pose » (dzT) appelle dzPoseChoix, l'état initial porte
     pose:"", le corps envoyé passe par __dzPose3d.corps, aucun état React neuf ;
  2. dzPoseChoix JOUÉ sous node avec un faux React : trois boutons radio, T/A grisés avec la raison en bulle et en
     note quand le choix est inactif, « Aucune » toujours cliquable, avertissement ambre en cas de doute, bouton de
     vérification seulement quand la vision est proposée, clic = set("pose", …), état inconnu = rien d'actif ;
  3. le maillon : appliqué, inverse avant_dzpose exact, appelé EN TÊTE de avant_dzecartes, hors couche, sonde de
     dzecartes ;
  4. le module partagé : copie identique dans dist, balises dans la SPA et le 3D Studio, dictionnaire FR/EN complet
     pour chaque clé employée, assemblé à jour ;
  5. le 3D Studio : le crochet L9 posé après le rendu de la modale, saisie à jour, sans texte en dur ;
  6. le banc node du module (frontend/shared/qa/pose3d.test.mjs) passe.
Run : & $PY tests/test_pose3d_ecran.py   (depuis backend/)
"""
import json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))
import _i18n_l1_aide as AIDE                                         # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
bundle = BUNDLE.read_bytes().decode("utf-8")

print("\n[1] le bundle")
check("1.1 l'interrupteur « T-pose » a disparu", 'label:"T-pose"' not in bundle and "checked:p.tpose" not in bundle)
check("1.2 le champ « Pose » traduit appelle dzPoseChoix avec le rafraîchissement par setPP",
      'r.jsx(O,{label:dzT("pose3d.choix.champ"),children:dzPoseChoix(p,set,function(){setPP(function(o){return Object.assign({},o)})})})' in bundle)
check("1.3 l'état initial porte pose:\"\" et plus tpose", 'textures:!0,pose:"",formats:["glb"]}),p=PP[0]' in bundle
      and "tpose:!1" not in bundle)
check("1.4 le corps envoyé passe par __dzPose3d.corps",
      'body:JSON.stringify(window.__dzPose3d?window.__dzPose3d.corps(p):p)' in bundle)
check("1.5 dzPoseChoix est défini une fois, juste avant DzGameAssets",
      bundle.count("function dzPoseChoix(") == 1
      and bundle.index("function dzPoseChoix(") < bundle.index("function DzGameAssets({variant:e}){")
      and "function DzGameAssets(" not in bundle[bundle.index("function dzPoseChoix("):bundle.index("function DzGameAssets({variant:e}){")])
check("1.6 aucun état React neuf (731 x.useState)", bundle.count("x.useState(") == 731)
_def = bundle[bundle.index("function dzPoseChoix("):bundle.index("function DzGameAssets({variant:e}){")]
check("1.7 aucun texte en dur dans le choix (toutes les étiquettes par dzT ou par dz-pose3d)",
      not re.search(r'children:"[A-Za-zÀ-ÿ]', _def) and 'dzT("pose3d.choix.aucune")' in _def and 'dzT("pose3d.vision.bouton")' in _def)
check("1.8 aucun rayon littéral dans le choix (angles vifs)", "borderRadius" not in _def)

print("\n[2] dzPoseChoix joué sous node")
JEU = r"""
const vm = require("node:vm");
const src = process.argv[1];
const out = [];
function rendre(etat, p, txt) {
  const sets = [], classes = [];
  const r = { jsx: (t, pr, k) => ({ t, pr, k }), jsxs: (t, pr, k) => ({ t, pr, k }) };
  const ctx = { r, dzT: (k) => "«" + k + "»", window: { __dzPose3d: etat === undefined ? undefined : {
      etat: () => etat, textes: () => txt, classer: (q) => classes.push(q) } } };
  vm.createContext(ctx);
  vm.runInContext(src + ";globalThis.__f=dzPoseChoix;", ctx);
  const arbre = ctx.__f(p, (k, v) => sets.push([k, v]), () => {});
  return { arbre, sets, classes };
}
const P = { engine: "rodin", multiview: false, subject: "a knight", image_filename: "k.png", pose: "t-pose" };
const VIDE = { raison: "", avertissement: "", precision: "" };
for (const [nom, etat, txt] of [
  ["actif", { actif: true, vision_proposee: false }, VIDE],
  ["objet", { actif: false, vision_proposee: false }, { raison: "RAISON", avertissement: "", precision: "" }],
  ["doute", { actif: true, vision_proposee: true }, { raison: "", avertissement: "AVERT", precision: "" }],
  ["inconnu", null, VIDE],
  ["sans_module", undefined, VIDE]]) {
  const x = rendre(etat, P, txt);
  const enf = x.arbre.pr.children;
  const boutons = enf[0].pr.children;
  const res = { nom, n: boutons.length, poses: boutons.map(b => b.pr["data-pose"]), dis: boutons.map(b => !!b.pr.disabled),
    coche: boutons.map(b => b.pr["aria-checked"]), titres: boutons.map(b => b.pr.title), etiq: boutons.map(b => b.pr.children),
    role: enf[0].pr.role, note: enf[1] ? { txt: enf[1].pr.children, coul: enf[1].pr.style.color } : null,
    vision: enf[2] ? enf[2].pr.children : null, radius: JSON.stringify(x.arbre).includes("adius") };
  boutons.forEach(b => b.pr.onClick());
  res.sets = x.sets;
  if (enf[2]) { enf[2].pr.onClick(); res.classes = x.classes; }
  out.push(res);
}
console.log(JSON.stringify(out));
"""
_r = subprocess.run(["node", "-e", JEU, _def], capture_output=True, text=True, encoding="utf-8")
try:
    J = {x["nom"]: x for x in json.loads(_r.stdout)}
except Exception:                                                    # noqa: BLE001
    J = {}
    check("2.0 le jeu node tourne", False, (_r.stdout + _r.stderr)[-400:])
if J:
    a = J["actif"]
    check("2.1 trois boutons radio Aucune / T-pose / A-pose, dans un radiogroup",
          a["n"] == 3 and a["poses"] == ["aucune", "t-pose", "a-pose"] and a["role"] == "radiogroup"
          and a["etiq"] == ["«pose3d.choix.aucune»", "«pose3d.choix.t»", "«pose3d.choix.a»"], str(a))
    check("2.2 actif : rien de grisé, la pose courante cochée, l'aide en bulle",
          a["dis"] == [False, False, False] and a["coche"] == [False, True, False]
          and a["titres"] == ["«pose3d.aide.aucune»", "«pose3d.aide.t»", "«pose3d.aide.a»"], str(a))
    check("2.3 actif : chaque clic pose la valeur", a["sets"] == [["pose", ""], ["pose", "t-pose"], ["pose", "a-pose"]], str(a["sets"]))
    check("2.4 actif sans rien à dire : ni note ni bouton de vérification", a["note"] is None and a["vision"] is None)
    o = J["objet"]
    check("2.5 inactif : T/A grisés, Aucune cochée et cliquable", o["dis"] == [False, True, True] and o["coche"] == [True, False, False], str(o))
    check("2.6 inactif : la raison en bulle des boutons grisés et en note (gris)", o["titres"][1:] == ["RAISON", "RAISON"]
          and o["note"] == {"txt": "RAISON", "coul": "var(--ink-soft)"}, str(o))
    check("2.7 inactif : un clic sur T/A ne pose rien", o["sets"] == [["pose", ""]], str(o["sets"]))
    d = J["doute"]
    check("2.8 doute : choix actif, avertissement ambre", d["dis"] == [False, False, False]
          and d["note"] == {"txt": "AVERT", "coul": "var(--amber)"}, str(d))
    check("2.9 doute + image : bouton « Vérifier l'image » qui lance le classement avec moteur, sujet et image",
          d["vision"] == "«pose3d.vision.bouton»" and d.get("classes") == [{"engine": "rodin", "multiview": False,
                                                                           "subject": "a knight", "image": "k.png"}], str(d))
    i = J["inconnu"]
    check("2.10 état inconnu (chargement) : T/A grisés, rien coché que Aucune", i["dis"] == [False, True, True]
          and i["coche"] == [True, False, False] and i["note"] is None, str(i))
    check("2.11 module absent : même rendu prudent, sans erreur", J["sans_module"]["dis"] == [False, True, True])
    check("2.12 aucun rayon dans l'arbre rendu", not any(x["radius"] for x in J.values()))

print("\n[3] le maillon de queue")
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzpose.py"), "--check"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   env=dict(__import__("os").environ, PYTHONIOENCODING="utf-8"))
check("3.1 le maillon est appliqué (--check)", r.returncode == 0 and "déjà appliqué" in r.stdout, (r.stdout + r.stderr)[-300:])
import patch_bundle_dzpose as M                                      # noqa: E402
avant = AIDE.avant_dzpose(bundle)
check("3.2 l'inverse avant_dzpose défait le maillon, et le rejouer redonne le bundle à l'octet",
      M.MARKER not in avant and 'label:"T-pose"' in avant and "dzPoseChoix" not in avant and M.appliquer(avant) == bundle)
src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
_ec = src_aide[src_aide.index("def avant_dzecartes("):]
_ec = _ec[:_ec.index("\ndef ", 5)]
check("3.3 avant_dzecartes défait d'abord dzpose (maillon posé après lui)",
      "bundle = avant_dzpose(bundle)" in _ec and _ec.index("avant_dzpose(") < _ec.index("_m.defaire("))
check("3.4 aucune paire dans une couche __DZ_*_BEGIN__", all(M.hors_couche(bundle, z) for _a, z in M.PAIRES))
check("3.5 le maillon suit dzecartes (sonde de son marqueur)", any(j == "/*dzecartes*/" for _t, j, _n in M.SONDE_AMONT))
check("3.6 aucun .bak_dzpose laissé", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzpose")).exists())
check("3.7 un seul marqueur", bundle.count(M.MARKER) == 1)

print("\n[4] module partagé, balises, dictionnaire")
SRC = RACINE / "frontend" / "shared" / "dz-pose3d.js"
check("4.1 copie dist identique à l'octet", SRC.read_bytes() == (RACINE / "frontend" / "dist" / "shared" / "dz-pose3d.js").read_bytes())
idx = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
check("4.2 la SPA charge /shared/dz-pose3d.js (après le dictionnaire et le dialogue)",
      idx.count('<script src="/shared/dz-pose3d.js"></script>') == 1
      and idx.index("dz-i18n-dico.js") < idx.index("dz-pose3d.js"))
s3 = (RACINE / "frontend" / "studio3d" / "index.html").read_text(encoding="utf-8")
check("4.3 le 3D Studio charge /shared/dz-pose3d.js avant studio3d.js",
      s3.count('<script src="/shared/dz-pose3d.js"></script>') == 1 and s3.index("dz-pose3d.js") < s3.index('src="studio3d.js"'))
dico = json.loads((RACINE / "frontend" / "shared" / "i18n" / "pose3d.json").read_text(encoding="utf-8"))
cles = set(re.findall(r'dzT\("(pose3d\.[a-z_.]+)"', bundle)) | set(re.findall(r'"(pose3d\.[a-z_.]+)', SRC.read_text(encoding="utf-8")))
cles |= {f"pose3d.raison.{c}" for c in ("moteur", "objet", "vues")} | {"pose3d.avert.doute"} \
    | {f"pose3d.vision.indispo_{c}" for c in ("cle", "vision")}
manq = sorted(k for k in cles if k not in dico and not k.endswith((".", "_")))
check("4.4 chaque clé employée (bundle, module, codes du serveur) a son FR et son EN",
      not manq and all(dico[k]["fr"] and dico[k]["en"] and dico[k]["fr"] != k for k in cles if k in dico), str(manq))
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True)
check("4.5 dictionnaire assemblé à jour", r.returncode == 0)
check("4.6 les codes de raison du serveur ont tous une clé", all(f"pose3d.raison.{c}" in dico for c in ("moteur", "objet", "vues")))

print("\n[5] le 3D Studio")
sj = (RACINE / "frontend" / "studio3d" / "studio3d.js").read_bytes().decode("utf-8")
i = sj.index("  body.innerHTML = html;\r\n")
check("5.1 le crochet suit le rendu de la modale, seulement pour « preview »",
      sj[i:i + 400].count('if (id === "preview" && window.__dzPose3d) window.__dzPose3d.monterSelect(body.querySelector("#f-pose")') == 1)
check("5.2 moteur meshy, prompt seulement quand la source est le texte, image choisie",
      'engine: "meshy", multiview: true, subject: c.source === "text" ? c.prompt : "", image: c.imageName || ""' in sj)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l9_generer.py"), "--check"], capture_output=True)
check("5.3 saisie L9 à jour (studio3d.js régénéré)", r.returncode == 0, r.stdout[-200:])
check("5.4 la liste pose_mode de Meshy est intacte (a-pose / t-pose / libre)",
      '<select id="f-pose"><option value="a-pose"' in sj and 'c.poseMode = $("#f-pose").value' in sj)

print("\n[6] banc node du module")
r = subprocess.run(["node", str(RACINE / "frontend" / "shared" / "qa" / "pose3d.test.mjs")], capture_output=True,
                   text=True, encoding="utf-8")
check("6.1 pose3d.test.mjs passe", r.returncode == 0, (r.stdout + r.stderr)[-400:])

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
