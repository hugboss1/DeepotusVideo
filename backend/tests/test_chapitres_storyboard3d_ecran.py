# -*- coding: utf-8 -*-
"""t189 (G7, plan « Génération IA enrichie », 12/10/2026) — l'ÉCRAN de l'Atelier : storyboard 3D (SAM 3 → Plateau) et
vidéo d'un plan, sur chaque carte du storyboard (le serveur est prouvé par test_storyboard3d / test_chapitres_video).

  [S] statique sur frontend/atelier/atelier.js :
      S1 les boutons de la carte dans l'ordre Image de production → Reconstruire en 3D → Générer le plan → Plateau 3D,
         chacun avec title et aria-label par dzT, et une icône EXISTANTE de la suite (dz-icons.js) ;
      S2 les écouteurs sont branchés, la vignette vidéo est posée dans la carte et suivie ;
      S3 pour CHAQUE tir (objets3d, vidéo) : dialogue maison → `if (!choix) return;` → POST, dans cet ORDRE (une
         confirmation court-circuitée ne passe pas) ; la route appelée est la bonne ;
      S4 aucun dialogue natif (window.prompt / alert / confirm, ni prompt( / confirm( nus) dans le script ;
      S5 DzModelesIA.select sur la nature passée ; objets3d pour le storyboard 3D ; video_fl / video_i2v selon
         keyframe_end ; aucune option `disabled` dans le bloc t189 (une clé manquante reste choisissable) ;
      S6 chaque dzT du bloc t189 existe dans atelier.json, fr et en non vides, mêmes variables ; le défaut first-last
         de l'écran est celui de la route (_VIDEO_PLAN_FL) ; la vignette suit GET /api/jobs/{id}, s'arrête quand la carte
         disparaît, puis lit /api/jobs/{id}/video dans un <video> muet avec contrôles ; les classes CSS existent.
  [N] sous node (fonctions EXTRAITES du script, dialogue et API simulés) :
      N1 natureVideoPlan : video_fl avec une borne de fin, video_i2v sans ;
      N2 objetsDuPlan : personnages d'abord, puis objets, puis décors ; dates / ambiances écartées ;
      N3 debutVideoPlan : borne du Plateau > image de production > croquis > rien ;
      N4 videoPlan : avec fin -> nature video_fl, présélection veo-3.1-fast-fal, /video-models non lu ; sans fin ->
         video_i2v, présélection = défaut de l'app (/video-models) ; annulé -> AUCUN POST ; confirmé -> POST
         /shots/{id}/video {video_model} ;
      N5 objets3dPlan : le champ est prérempli ; annulé -> AUCUN POST ; confirmé -> POST /shots/{id}/objets3d
         {modele, prompt} ; plan sans image -> aucun dialogue.
Run (depuis backend/) : & $PY tests/test_chapitres_storyboard3d_ecran.py
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent.parent
FRONT = RACINE / "frontend"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


JS = (FRONT / "atelier" / "atelier.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
CSS = (FRONT / "atelier" / "atelier.css").read_bytes().decode("utf-8")
DICO = json.loads((FRONT / "shared" / "i18n" / "atelier.json").read_text("utf-8"))
ICONES = (FRONT / "shared" / "icons" / "dz-icons.js").read_text("utf-8")
ROUTES = (RACINE / "backend" / "app" / "api" / "routes.py").read_text("utf-8")


def fonction(nom: str) -> str:
    """Le texte d'une fonction de premier niveau (déclaration jusqu'à la première « } » en colonne 0)."""
    m = re.search(r"^(?:async )?function " + re.escape(nom) + r"\(.*?^}\n", JS, flags=re.S | re.M)
    return m.group(0) if m else ""


debut_bloc = JS.find("/* ═════════ t189 (G7)")
fin_bloc = JS.find("/* ═════════ tâche #62 (plan chapitres T6)", debut_bloc)
BLOC = JS[debut_bloc:fin_bloc] if 0 <= debut_bloc < fin_bloc else ""

print("\n[S] statique")
rb = fonction("renderBoard")
pos = [rb.find(f'class="btn ghost act-{k}"') for k in ("prod", "objets3d", "video", "plateau")]
check("S1a les boutons de la carte : prod → objets3d → video → plateau", all(p >= 0 for p in pos) and pos == sorted(pos), pos)
for k, ico in (("objets3d", "dz-lab3d-generer-modele"), ("video", "dz-media-generer-video")):
    m = re.search(r'<button class="btn ghost act-' + k + r'" title="\$\{dzT\("([^"]+)"\)\}" aria-label="\$\{dzT\("([^"]+)"\)\}">\$\{ico\("([^"]+)"\)\}</button>', rb)
    check(f"S1b act-{k} : title et aria-label par dzT, icône {ico}", bool(m) and m.group(3) == ico, m and m.groups())
    check(f"S1c l'icône {ico} existe dans la suite (dz-icons.js)", f'"{ico}"' in ICONES)
check("S2a les écouteurs des deux boutons sont branchés",
      'card.querySelector(".act-objets3d").addEventListener("click", () => objets3dPlan(id));' in rb
      and 'card.querySelector(".act-video").addEventListener("click", () => videoPlan(id));' in rb)
check("S2b la vignette vidéo est posée dans la carte et suivie", "${vignetteVideo(s)}" in rb and "suivreVideo(card, sh());" in rb)

for nom, route in (("objets3dPlan", "/objets3d`"), ("videoPlan", "/video`")):
    f = fonction(nom)
    g = f.find("const choix = await dialoguePlanIA(")
    r = f.find("if (!choix) return;", g) if g >= 0 else -1
    p = f.find('api.send("POST"')
    check(f"S3a {nom} : dialogue maison → if (!choix) return; → POST, dans cet ordre", f and 0 <= g < r < p, (g, r, p))
    check(f"S3b {nom} : un seul POST, vers {route}", f.count('api.send("POST"') == 1 and route in f[p:p + 120], f[p:p + 120])

nat = re.findall(r"\b(?:window\.)?(prompt|alert|confirm)\s*\(", re.sub(r"/\*.*?\*/|//[^\n]*", "", JS, flags=re.S))
check("S4 aucun dialogue natif (prompt / alert / confirm) dans le script", not nat, nat[:5])

dlg = fonction("dialoguePlanIA")
check("S5a dialoguePlanIA remplit le sélecteur par DzModelesIA.select sur la nature demandée",
      "window.DzModelesIA.select(sel, o.nature, { valeur: o.valeur })" in dlg)
check("S5b le storyboard 3D demande la nature « objets3d »", 'nature: "objets3d"' in fonction("objets3dPlan"))
nv = fonction("natureVideoPlan")
check("S5c la vidéo demande video_fl avec une borne de fin, video_i2v sinon",
      'keyframe_end ? "video_fl" : "video_i2v"' in nv and "const nature = natureVideoPlan(s);" in fonction("videoPlan")
      and "nature," in fonction("videoPlan"))
check("S5d aucune option `disabled` dans le bloc t189 (une clé manquante reste choisissable)",
      BLOC and "disabled" not in BLOC and "desactive" not in BLOC)

cles = sorted(set(re.findall(r'"(atelier\.[a-z0-9_.]+)"', BLOC + rb[rb.find("act-objets3d") - 40:rb.find("act-plateau")])))
manque = [c for c in cles if c not in DICO or not DICO[c].get("fr") or not DICO[c].get("en")]
check(f"S6a les {len(cles)} clés dzT du bloc existent, fr et en non vides", len(cles) >= 30 and not manque, manque[:6])
var_ko = [c for c in cles if c in DICO and set(re.findall(r"\{(\w+)\}", DICO[c]["fr"])) != set(re.findall(r"\{(\w+)\}", DICO[c]["en"]))]
check("S6b mêmes variables {x} en fr et en", not var_ko, var_ko)
for c in ("atelier.plan.reconstruire3d", "atelier.plan.objets", "atelier.plan.objets_poses", "atelier.plan.video",
          "atelier.plan.video_fin"):
    check(f"S6c la clé du plan {c} est utilisée", f'"{c}"' in JS and c in DICO)
m = re.search(r'_VIDEO_PLAN_FL = "([^"]+)"', ROUTES)
check("S6d le défaut first-last de l'écran est celui de la route", m and f'const MODELE_VIDEO_FIN = "{m.group(1)}";' in BLOC,
      m and m.group(1))
sv = fonction("suivreVideo")
check("S6e la vignette suit GET /api/jobs/{id}, s'arrête quand la carte disparaît, et au statut final",
      'fetch("/api/jobs/" + encodeURIComponent(job))' in sv and "if (!box.isConnected) return;" in sv
      and 'j.status === "done"' in sv and 'j.status === "failed"' in sv and "setTimeout(tour, 4000)" in sv
      and "clearTimeout(suivisVideo.get(cle));" in sv)
check("S6f la vidéo terminée est lue dans un <video> muet avec contrôles (/api/jobs/{id}/video)",
      re.search(r'<video class="shot-video-lecteur" src="/api/jobs/\$\{encodeURIComponent\(job\)\}/video" muted controls', sv) is not None)
check("S6g les classes du dialogue et de la vignette ont leur CSS",
      all(c in CSS for c in (".dzp-box", ".dzp-body", ".dzp-pied", ".dzp-prix", ".dzp-err", ".shot-video video", ".shot-video-etat")))

print("\n[N] sous node")
if not NODE:
    check("N node introuvable", False)
else:
    morceaux = [re.search(r'^const MODELE_VIDEO_FIN = "[^"]+";', JS, flags=re.M).group(0)]
    for nom in ("objetsDuPlan", "natureVideoPlan", "debutVideoPlan", "prixDzp", "objets3dPlan", "videoPlan"):
        morceaux.append(fonction(nom))
    code = "\n".join(morceaux)
    prog = r"""
const vm = require("vm");
const CODE = %s;
const journal = { dialogues: [], posts: [], gets: [], toasts: [] };
let reponse = null;
const ctx = {
  console, encodeURIComponent, Number, Math, Promise, JSON,
  shots: [], entities: [],
  location: { href: "" },
  window: { __dzDialogue: { confirmer: async () => false }, DzModelesIA: { prix: (u) => "$" + u } },
  dzT: (k, v) => k + (v ? JSON.stringify(v) : ""),
  toast: (m, e) => journal.toasts.push([m, !!e]),
  renderBoard: () => {},
  api: {
    get: async (p) => { journal.gets.push(p); if (p === "/video-models") return { default: "seedance-2.5" }; return {}; },
    send: async (m, p, b) => { journal.posts.push([m, p, b]); return { n: 3, usd: 0.5, video: "job-1" }; },
  },
  dialoguePlanIA: async (o) => { journal.dialogues.push(o); return reponse; },
};
vm.createContext(ctx);
vm.runInContext(CODE + "\nthis.F = { objetsDuPlan, natureVideoPlan, debutVideoPlan, objets3dPlan, videoPlan };", ctx);
const F = ctx.F;
(async () => {
  const R = {};
  R.n1 = [F.natureVideoPlan({ keyframe_end: "fin.png" }), F.natureVideoPlan({ keyframe_end: null }), F.natureVideoPlan({})];
  const ents = [{ id: "t", kind: "object", name: "Table" }, { id: "d", kind: "date", name: "1912" },
                { id: "v", kind: "character", name: "Vane" }, { id: "s", kind: "decor", name: "Salon" },
                { id: "a", kind: "ambiance", name: "Pluie" }, { id: "i", kind: "character", name: "Ilse" }];
  R.n2 = F.objetsDuPlan({ entities: ["t", "d", "v", "s", "a", "i", "inconnue"] }, ents);
  R.n3 = [F.debutVideoPlan({ keyframe_image: "k.png", image: "p.png", sketch_image: "c.png" }),
          F.debutVideoPlan({ image: "p.png", sketch_image: "c.png" }), F.debutVideoPlan({ sketch_image: "c.png" }),
          F.debutVideoPlan({})].map(d => d && d.fichier);
  ctx.entities = ents;
  ctx.shots.push({ id: "fl", idx: 0, duration_s: 5, keyframe_image: "k.png", keyframe_end: "e.png", entities: ["t", "v"] },
                 { id: "i2v", idx: 1, duration_s: 4, image: "p.png", entities: [] },
                 { id: "nu", idx: 2, duration_s: 4, entities: ["v"] });
  // N4 : la vidéo
  reponse = null; await F.videoPlan("fl");
  const d1 = journal.dialogues.pop();
  R.n4_fl = { nature: d1 && d1.nature, valeur: d1 && d1.valeur, gets: journal.gets.slice(), posts: journal.posts.length,
              toasts: journal.toasts.length,
              images: d1 && d1.images.map(x => x.fichier || null) };
  reponse = null; await F.videoPlan("i2v");
  const d2 = journal.dialogues.pop();
  R.n4_i2v = { nature: d2 && d2.nature, valeur: d2 && d2.valeur, gets: journal.gets.slice(), posts: journal.posts.length,
               toasts: journal.toasts.length };
  reponse = { modele: "kling-3-fl", texte: "" }; await F.videoPlan("fl");
  R.n4_post = journal.posts.slice();
  journal.posts.length = 0; journal.dialogues.length = 0;
  // N5 : le storyboard 3D
  journal.toasts.length = 0;
  reponse = null; await F.objets3dPlan("i2v");
  const d3 = journal.dialogues.pop();
  ctx.shots[1].entities = ["t", "v"];
  reponse = null; await F.objets3dPlan("i2v");
  const d4 = journal.dialogues.pop();
  R.n5_annule = { posts: journal.posts.length, toasts: journal.toasts.length, nature: d4 && d4.nature, champ: d4 && d4.champ.valeur, vide: d3 && d3.champ.valeur };
  reponse = { modele: "sam-3-3d-objects", texte: "Vane, Table" }; await F.objets3dPlan("i2v");
  R.n5_post = journal.posts.slice();
  journal.posts.length = 0; journal.dialogues.length = 0;
  reponse = { modele: "sam-3-3d-objects", texte: "x" }; await F.objets3dPlan("nu");
  R.n5_sans_image = { dialogues: journal.dialogues.length, posts: journal.posts.length };
  console.log(JSON.stringify(R));
})().catch(e => { console.log(JSON.stringify({ erreur: String(e && e.stack || e) })); });
""" % json.dumps(code)
    with tempfile.TemporaryDirectory(prefix="dzsb3d_") as tmp:
        f = pathlib.Path(tmp) / "banc.js"
        f.write_text(prog, "utf-8")
        r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        R = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        R = {"erreur": (r.stdout + r.stderr)[-600:]}
    check("N0 le banc node a tourné", "erreur" not in R, R.get("erreur"))
    check("N1 natureVideoPlan : video_fl avec une fin, video_i2v sans", R.get("n1") == ["video_fl", "video_i2v", "video_i2v"], R.get("n1"))
    check("N2 objetsDuPlan : personnages d'abord, puis objets, puis décors ; dates et ambiances écartées",
          R.get("n2") == "Vane, Ilse, Table, Salon", R.get("n2"))
    check("N3 debutVideoPlan : borne du Plateau > production > croquis > rien", R.get("n3") == ["k.png", "p.png", "c.png", None], R.get("n3"))
    a = R.get("n4_fl") or {}
    check("N4a avec fin : nature video_fl, présélection veo-3.1-fast-fal, /video-models non lu, début et fin montrés",
          a.get("nature") == "video_fl" and a.get("valeur") == "veo-3.1-fast-fal" and a.get("gets") == []
          and a.get("images") == ["k.png", "e.png"], a)
    b = R.get("n4_i2v") or {}
    check("N4b sans fin : nature video_i2v, présélection = défaut de l'app (/video-models)",
          b.get("nature") == "video_i2v" and b.get("valeur") == "seedance-2.5" and b.get("gets") == ["/video-models"], b)
    check("N4c annulé : AUCUN POST, aucun toast (rien n'est lancé après le dialogue)",
          a.get("posts") == 0 and b.get("posts") == 0 and a.get("toasts") == 0 and b.get("toasts") == 0, (a, b))
    check("N4d confirmé : POST /shots/fl/video {video_model}",
          R.get("n4_post") == [["POST", "/shots/fl/video", {"video_model": "kling-3-fl"}]], R.get("n4_post"))
    c = R.get("n5_annule") or {}
    check("N5a le champ « Objets à isoler » est prérempli (personnage d'abord), vide sans entité ; nature objets3d",
          c.get("champ") == "Vane, Table" and c.get("vide") == "" and c.get("nature") == "objets3d", c)
    check("N5b annulé : AUCUN POST, aucun toast", c.get("posts") == 0 and c.get("toasts") == 0, c)
    check("N5c confirmé : POST /shots/i2v/objets3d {modele, prompt}",
          R.get("n5_post") == [["POST", "/shots/i2v/objets3d", {"modele": "sam-3-3d-objects", "prompt": "Vane, Table"}]],
          R.get("n5_post"))
    check("N5d plan sans image : ni dialogue ni POST", R.get("n5_sans_image") == {"dialogues": 0, "posts": 0},
          R.get("n5_sans_image"))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
