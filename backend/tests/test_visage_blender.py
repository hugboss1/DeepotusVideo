# -*- coding: utf-8 -*-
"""Banc de l'animation FACIALE dans Blender (services/visage_blender.py, 22/11/2026).

  [P] le calcul PUR : visèmes depuis un texte (débit, ponctuation, durée imposée), depuis le JSON de Rhubarb, depuis
      l'enveloppe d'un WAV ; courbes (bouche, expressions, clignements déterministes, silences) ; vérification des
      paramètres (énumérations fermées, bornes, noms, chemins) ;
  [G] le GABARIT : un seul trou, l'arbre syntaxique ne dépend pas des paramètres, le vrai validateur du mode sûr de
      mcp-for-blender l'accepte (quand il est installé) ;
  [R] les routes : /api/blender/visage (Blender ouvert, FAUX serveur MCP : seul le script du gabarit part), refus
      (corps vide, clé inconnue, audio hors des données, appareil du réseau local), /visage/fichier (source confinée) ;
  [B] FACULTATIF (Blender installé) — trois personnages fabriqués en arrière-plan : (1) maillage SANS visage animable
      → clés DZ_ sculptées et animées, la mâchoire descend, export .glb avec morphes ; (2) clés ARKit existantes →
      animées sans en créer ; (3) rig à os du visage (style Rigify) → la mâchoire tourne vers le bas, la paupière
      descend, l'animation du corps reste intacte.
AUCUN appel réseau, aucune dépense. Run (depuis backend/) : & $PY tests/test_visage_blender.py"""
import ast
import importlib.util
import json
import math
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import wave

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzvisage_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir()
(_tmp / "outputs").mkdir()
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[_k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from loguru import logger  # noqa: E402
logger.remove()
from app.services import visage_blender as V  # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label}  {str(detail)[:400]}")


def refuse(fn):
    try:
        fn()
    except V.VisageRefuse:
        return True
    return False


# ═══════════════════════════════════════ [P] calcul pur ═══════════════════════════════════════
print("[P] visèmes et courbes")
v = V.visemes_depuis_texte("Bonjour, mon ami. Papa boit.")
lettres = [x["viseme"] for x in v]
check("P1 texte → visèmes : finit au repos", lettres[-1] == "X" and lettres[0] != "X", lettres)
check("P2 « b », « m », « p » → lèvres closes (A)", "A" in lettres, lettres)
check("P3 « ou » → bouche en avant (F)", "F" in lettres, lettres)
check("P4 pas de visèmes identiques consécutifs", all(a != b for a, b in zip(lettres, lettres[1:])), lettres)
check("P5 temps croissants et contigus", all(a["fin"] <= b["debut"] + 1e-6 for a, b in zip(v, v[1:])), v)
v2 = V.visemes_depuis_texte("Bonjour, mon ami. Papa boit.", duree_s=4.0)
check("P6 durée imposée : le texte tient dans les 4 s de l'audio (+ repos final de 0,2 s)",
      3.99 <= v2[-1]["fin"] <= 4.21 and all(x["debut"] < 4.0 for x in v2), v2[-1])
check("P7 texte vide → aucun visème", V.visemes_depuis_texte("  ") == [])

rh = {"mouthCues": [{"start": 0.0, "end": 0.2, "value": "X"}, {"start": 0.2, "end": 0.5, "value": "D"},
                    {"start": 0.5, "end": 0.6, "value": "Z"}, {"start": 0.6, "end": 0.9, "value": "a"}]}
vr = V.visemes_depuis_rhubarb(json.dumps(rh))
check("P8 Rhubarb : visèmes lus, inconnu écarté, minuscules acceptées", [x["viseme"] for x in vr] == ["X", "D", "A"], vr)
check("P9 Rhubarb illisible → refus", refuse(lambda: V.visemes_depuis_rhubarb({"autre": 1})))

wav = _tmp / "voix.wav"
with wave.open(str(wav), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(16000)
    data = []
    for i in range(16000 * 2):                       # 1 s de son, 1 s de silence
        t = i / 16000
        data.append(int(12000 * math.sin(2 * math.pi * 220 * t)) if t < 1.0 else 0)
    w.writeframes(struct.pack("<%dh" % len(data), *data))
env, duree = V.enveloppe_wav(wav, 24)
check("P10 WAV : durée lue", abs(duree - 2.0) < 1e-6, duree)
check("P11 WAV : énergie forte puis silence", env[5] > 0.8 and env[40] < 0.05, (env[5], env[40]))

c = V.courbes(vr, fps=24, expressions=[{"nom": "joie", "debut": 0.0, "fin": 0.5}], clignements=True, duree_s=6)
jaw = dict((f, x) for f, x in c["controles"]["jawOpen"])
check("P12 D (grande ouverte) → jawOpen 0,7 à son début", jaw.get(1 + round(0.2 * 24)) == 0.7, c["controles"]["jawOpen"])
check("P13 une image avant le D, la bouche tient le repos", jaw.get(round(0.2 * 24)) == 0.0, jaw)
check("P14 expression joie → sourire animé", "mouthSmileLeft" in c["controles"] and
      max(x for _, x in c["controles"]["mouthSmileLeft"]) >= 0.79, c["controles"].get("mouthSmileLeft"))
check("P15 clignements sur 6 s (déterministes)", c["clignements"] >= 1 and
      max(x for _, x in c["controles"]["eyeBlinkLeft"]) == 1.0 and
      V.courbes(vr, duree_s=6)["controles"]["eyeBlinkLeft"] == V.courbes(vr, duree_s=6)["controles"]["eyeBlinkLeft"])
check("P16 courbes « visemes » 0/1 et « expression » sans la bouche", set(c["visemes"]) <= set(V.VISEMES) and
      not set(c["expression"]) & set(V.BOUCHE), (list(c["visemes"]), list(c["expression"])))
check("P17 images croissantes, sans doublon", all(a[0] < b[0] for a, b in zip(c["controles"]["jawOpen"],
                                                                                c["controles"]["jawOpen"][1:])))
cs = V.courbes([{"debut": 0, "fin": 2, "viseme": "D"}], enveloppe=env, duree_s=2)
js = dict(cs["controles"]["jawOpen"])
check("P18 l'enveloppe ferme la bouche dans le silence", max(js.values()) > 0.6 and js.get(1 + 47, 0) < 0.25, js)

print("[P] paramètres")
p = V.parametres(texte="Bonjour tout le monde", expressions=[{"nom": "surprise", "debut": 0.5, "fin": 1.2}])
check("P19 paramètres complets et vérifiés", p["mode"] == "auto" and p["controles"] and p["images"][0] == 1, p.keys())
check("P20 expression inconnue → refus", refuse(lambda: V.parametres(texte="a", expressions=[{"nom": "rage"}])))
check("P21 mode inconnu → refus", refuse(lambda: V.parametres(texte="a", mode="libre")))
check("P22 nom d'objet nettoyé (aucun guillemet ni code ne passe)",
      V.parametres(texte="a", objet='Tete"); import os #')["objet"] == "Tete) import os", None)
check("P23 chemin relatif ou « .. » → refus", refuse(lambda: V.parametres(texte="a", sortie_blend="x.blend")) and
      refuse(lambda: V.parametres(texte="a", sortie_blend="C:/a/../b.blend")))
check("P24 os_reglages : canal inconnu → refus", refuse(lambda: V.parametres(
    texte="a", os_reglages={"jaw": {"commande": "jawOpen", "canal": "exec", "gain": 1}})))
check("P25 os_reglages valides acceptés", V.parametres(texte="a", os_reglages={
    "CTRL-Jaw": {"commande": "jawOpen", "canal": "rotation", "gain": -1}})["os_reglages"]["CTRL-Jaw"]["gain"] == -1)
check("P26 repères hors [0, 1] → refus", refuse(lambda: V.parametres(texte="a", reperes={"bouche": [1.4, 0.2]})))
q = dict(p)
q["controles"] = {"jawOpen": [[1, 2.0]]}
check("P27 valeur de courbe > 1 → refus", refuse(lambda: V.verifier(q)))
q = dict(p)
q["controles"] = {"__import__": [[1, 0.5]]}
check("P28 commande hors liste → refus", refuse(lambda: V.verifier(q)))

# ═══════════════════════════════════════ [G] gabarit ═══════════════════════════════════════
print("[G] gabarit")


def arbre(script):
    a = ast.parse(script)
    lit = None
    for n in ast.walk(a):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "P":
            lit = n.value.args[0]
            n.value.args[0] = ast.Constant("X")
    return lit, ast.dump(a)


s1 = V.generer_script(p)
s2 = V.generer_script(V.parametres(texte="Autre chose, très différente !", objet="Perso", mode="os"))
l1, d1 = arbre(s1)
l2, d2 = arbre(s2)
check("G1 un seul trou rempli, le JSON relu à l'identique", "__PARAMS__" not in s1 and isinstance(l1, ast.Constant)
      and json.loads(l1.value) == json.loads(json.dumps(p)))
check("G2 l'arbre du script ne dépend pas des paramètres", d1 == d2)
check("G3 lire_resume lit la ligne DZVISAGE", V.lire_resume('bla\nDZVISAGE {"mode": "os"}\n') == {"mode": "os"})
VALIDEUR = pathlib.Path.home() / ".local" / "venvs" / "mcp-for-blender" / "Lib" / "site-packages" / "blender_mcp" / "safe_mode.py"
if VALIDEUR.exists():
    spec = importlib.util.spec_from_file_location("_safe_mode_mcp", VALIDEUR)
    sm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sm)
    r = sm.is_safe(s1)
    check("G4 le VRAI validateur du mode sûr de mcp-for-blender accepte le script", r[0], r)
else:
    print("  SKIP  G4 mcp-for-blender absent : validateur du mode sûr non lu")

# ═══════════════════════════════════════ [R] routes ═══════════════════════════════════════
print("[R] routes")
import asyncio  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

import app.main as _MAIN  # noqa: E402
from app.services import blender_mcp as BM  # noqa: E402
from app.services.storage import init_db  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
_boucle = asyncio.new_event_loop()
asyncio.set_event_loop(_boucle)
_boucle.run_until_complete(init_db())
FAUX = _ICI / "_faux_mcp_blender.py"
JOURNAL = _tmp / "journal.jsonl"
_VRAI_POPEN = BM._popen
BM._popen = lambda args, env: _VRAI_POPEN([sys.executable, str(FAUX)], {**env, "FAUX_JOURNAL": str(JOURNAL),
                                                                         "FAUX_MODE": "ok", "FAUX_PNG_B64": ""})
os.environ["BLENDER_MCP_EXE"] = str(FAUX)
cl = TestClient(_MAIN.app, client=("127.0.0.1", 50001))
cl.__enter__()
r = cl.post("/api/blender/visage", json={"texte": "Bonjour à tous", "expressions": [
    {"nom": "joie", "debut": 0, "fin": 1}], "mode": "auto"})
codes = [json.loads(l)["params"]["arguments"]["code"] for l in JOURNAL.read_text(encoding="utf-8").splitlines()
         if l.strip() and json.loads(l).get("method") == "tools/call"
         and json.loads(l)["params"]["name"] == "execute_blender_code"] if JOURNAL.exists() else []
check("R1 /visage : 200, un seul execute_blender_code, et c'est le GABARIT du visage",
      r.status_code == 200 and len(codes) == 1 and arbre(codes[0])[1] == d1 and "jawOpen" in r.json()["commandes"],
      (r.status_code, r.text[:300], len(codes)))
check("R2 corps sans texte ni audio → 400", cl.post("/api/blender/visage", json={"mode": "auto"}).status_code == 400)
check("R3 clé inconnue (code) → 400", cl.post("/api/blender/visage", json={"texte": "a", "code": "x"}).status_code == 400)
check("R4 audio hors du dossier de données → 400",
      cl.post("/api/blender/visage", json={"texte": "a", "audio": "C:/Windows/win.ini"}).status_code == 400)
(_tmp / "voix.txt").write_text("x", encoding="utf-8")
check("R5 audio qui n'est pas un .wav → 400",
      cl.post("/api/blender/visage", json={"texte": "a", "audio": "voix.txt"}).status_code == 400)
check("R6 /visage/fichier : source hors données → 400",
      cl.post("/api/blender/visage/fichier", json={"texte": "a", "source": "C:/Windows/win.ini"}).status_code == 400)
lan = TestClient(_MAIN.app, client=("192.168.1.20", 50000))
check("R7 un appareil du réseau local est refusé", lan.post("/api/blender/visage", json={"texte": "a"}).status_code
      in (401, 403))

# ═══════════════════════════════════════ [B] vrai Blender, arrière-plan ═══════════════════════════════════════
FABRIQUE = r'''
import bpy, sys, math
dossier = sys.argv[sys.argv.index("--") + 1]
def vider():
    bpy.ops.wm.read_factory_settings(use_empty=True)
# (1) un personnage GENERE : corps + tete fusionnes, sans cles ni os du visage
vider()
bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=1.4, location=(0, 0, 0.7))
corps = bpy.context.object
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, segments=48, ring_count=32, location=(0, 0, 1.6))
tete = bpy.context.object
corps.select_set(True); tete.select_set(True); bpy.context.view_layer.objects.active = corps
bpy.ops.object.join()
corps.name = "Genere"
bpy.ops.wm.save_as_mainfile(filepath=dossier + "/genere.blend")
# (2) des cles ARKit existantes
vider()
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(0, 0, 1.6))
o = bpy.context.object; o.name = "Arkit"
o.shape_key_add(name="Basis")
for n in ("jawOpen", "eyeBlinkLeft", "eyeBlinkRight", "mouthSmileLeft", "mouthSmileRight"):
    k = o.shape_key_add(name=n)
    for d in k.data:
        d.co.z -= 0.01
bpy.ops.wm.save_as_mainfile(filepath=dossier + "/arkit.blend")
# (3) un rig a os du visage, style Rigify, avec une animation du corps a garder
vider()
bpy.ops.object.armature_add(location=(0, 0, 0))
arm = bpy.context.object; arm.name = "Rig"
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
eb[0].name = "spine"; eb[0].head = (0, 0, 0); eb[0].tail = (0, 0, 1.4)
def os_(nom, h, t, parent="spine"):
    b = eb.new(nom); b.head = h; b.tail = t; b.parent = eb[parent]
os_("head", (0, 0, 1.45), (0, 0, 1.8))
os_("jaw_master", (0, 0.02, 1.58), (0, -0.12, 1.50), "head")
os_("lips.L", (0.05, -0.15, 1.53), (0.05, -0.18, 1.53), "head")
os_("lips.R", (-0.05, -0.15, 1.53), (-0.05, -0.18, 1.53), "head")
os_("lid.T.L", (0.06, -0.15, 1.65), (0.06, -0.17, 1.65), "head")
os_("lid.T.R", (-0.06, -0.15, 1.65), (-0.06, -0.17, 1.65), "head")
os_("brow.T.L", (0.06, -0.15, 1.70), (0.06, -0.17, 1.70), "head")
os_("brow.T.R", (-0.06, -0.15, 1.70), (-0.06, -0.17, 1.70), "head")
bpy.ops.object.mode_set(mode="POSE")
sp = arm.pose.bones["spine"]
for f in (1, 30, 60):
    sp.rotation_quaternion = (1, 0, 0, 0.1 * f / 60); sp.keyframe_insert("rotation_quaternion", frame=f)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.wm.save_as_mainfile(filepath=dossier + "/rig.blend")
'''

INSPECTE = r'''
import bpy, json, sys
from mathutils import Vector
s = bpy.context.scene
out = {}
for o in s.objects:
    if o.type == "MESH" and o.data.shape_keys:
        out[o.name] = {"cles": [k.name for k in o.data.shape_keys.key_blocks]}
        ad = o.data.shape_keys.animation_data
        out[o.name]["anim"] = bool(ad and ad.action)
        kb = o.data.shape_keys.key_blocks.get("DZ_jawOpen")
        if kb:
            dz = [kb.data[i].co.z - o.data.vertices[i].co.z for i in range(len(kb.data))]
            out[o.name]["jaw_min_dz"] = min(dz)
            out[o.name]["jaw_n"] = sum(1 for x in dz if abs(x) > 1e-6)
    if o.type == "ARMATURE":
        r = {}
        for f in (1, 6):
            s.frame_set(f)
        best = None
        for f in range(1, 60):
            s.frame_set(f)
            pb = o.pose.bones["jaw_master"]
            z = (o.matrix_world @ pb.tail).z
            best = z if best is None else min(best, z)
        r["jaw_tail_min_z"] = best
        r["jaw_tail_rest_z"] = (o.matrix_world @ o.data.bones["jaw_master"].tail_local).z
        low = None
        for f in range(1, 140):
            s.frame_set(f)
            z = (o.matrix_world @ o.pose.bones["lid.T.L"].head).z
            low = z if low is None else min(low, z)
        r["lid_min_z"] = low
        r["lid_rest_z"] = (o.matrix_world @ o.data.bones["lid.T.L"].head_local).z
        act = o.animation_data.action if o.animation_data else None
        r["spine_cles"] = 0
        if act:
            try:
                fcs = list(act.fcurves)
            except AttributeError:
                fcs = [fc for l in act.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]
            r["spine_cles"] = sum(len(fc.keyframe_points) for fc in fcs if '"spine"' in fc.data_path)
        out[o.name] = r
print("DZINSPECTE " + json.dumps(out))
'''


def blender_exe():
    try:
        from app.services import passes_blender as PB
        e = PB.etat_blender(rafraichir=True)
        return e.get("exe") if e.get("dispo") else None
    except Exception:
        for d in sorted(pathlib.Path("C:/Program Files/Blender Foundation").glob("Blender */blender.exe"), reverse=True):
            return str(d)
    return None


def lancer(args, timeout=240):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, r.stdout + r.stderr


exe = blender_exe() or next((str(d) for d in sorted(pathlib.Path("C:/Program Files/Blender Foundation").glob(
    "Blender */blender.exe"), reverse=True)), None)
if exe and os.environ.get("VISAGE_SANS_BLENDER") != "1":
    print(f"[B] vrai Blender en arrière-plan ({exe})")
    fab = _tmp / "fabrique.py"
    fab.write_text(FABRIQUE, encoding="utf-8")
    rc, out = lancer([exe, "-b", "--factory-startup", "-noaudio", "--python-exit-code", "3", "--python", str(fab), "--",
                      _tmp.as_posix()])
    check("B0 personnages de test fabriqués", rc == 0 and (_tmp / "rig.blend").exists(), out[-600:])
    insp = _tmp / "inspecte.py"
    insp.write_text(INSPECTE, encoding="utf-8")

    def animer(nom, **kw):
        sortie = (_tmp / f"{nom}_anime.blend").as_posix()
        pr = V.parametres(texte="Bonjour, je suis un personnage anime. Papa boit du lait.", sortie_blend=sortie,
                          expressions=[{"nom": "joie", "debut": 0.2, "fin": 2.0}], **kw)
        sc = _tmp / f"{nom}_script.py"
        sc.write_text(V.generer_script(pr), encoding="utf-8")
        rc, o = lancer(V.argv_headless(exe, sc, (_tmp / f"{nom}.blend").as_posix()))
        res = V.lire_resume(o)
        rc2, o2 = lancer([exe, "-b", sortie, "--factory-startup", "-noaudio", "--python", str(insp)])
        ins = next((json.loads(l[len("DZINSPECTE "):]) for l in o2.splitlines() if l.startswith("DZINSPECTE ")), {})
        return rc, res, ins, o

    rc, res, ins, o = animer("genere", sortie_glb=(_tmp / "genere.glb").as_posix())
    g = ins.get("Genere", {})
    check("B1 maillage généré → mode procédural, sans erreur", rc == 0 and res and res["mode"] == "procedural"
          and not res["erreurs"], (res, o[-800:]))
    check("B2 clés DZ_ sculptées (mâchoire, clignements, sourire) et animées",
          {"DZ_jawOpen", "DZ_eyeBlinkLeft", "DZ_mouthSmileLeft"} <= set(g.get("cles", [])) and g.get("anim"), g)
    check("B3 la mâchoire DESCEND et ne touche qu'une partie du maillage",
          g.get("jaw_min_dz", 0) < -0.005 and 0 < g.get("jaw_n", 0) < 1500, g)
    check("B4 export .glb avec morphes", (_tmp / "genere.glb").exists() and (_tmp / "genere.glb").stat().st_size > 5000)

    rc, res, ins, o = animer("arkit")
    a = ins.get("Arkit", {})
    check("B5 clés ARKit existantes → mode « cles », animées, aucune clé DZ_ créée",
          res and res["mode"] == "cles" and a.get("anim") and not any(k.startswith("DZ_") for k in a.get("cles", []))
          and any(x.startswith("jawOpen") for x in res["animees"]), (res, a))

    rc, res, ins, o = animer("rig", mode="os")
    r = ins.get("Rig", {})
    check("B6 rig à os du visage → mode « os », mâchoire et coins trouvés", res and res["mode"] == "os" and
          any(x.startswith("jaw_master") for x in res["animees"]) and any(x.startswith("lips.L") for x in res["animees"]),
          (res, o[-600:]))
    check("B7 la mâchoire s'ouvre VERS LE BAS", r.get("jaw_tail_min_z", 9) < r.get("jaw_tail_rest_z", 0) - 0.01, r)
    check("B8 la paupière descend au clignement", r.get("lid_min_z", 9) < r.get("lid_rest_z", 0) - 0.001, r)
    check("B9 l'animation du corps (spine) est intacte", r.get("spine_cles") == 12, r)   # 3 images × 4 canaux
    import shutil
    shutil.copy(_tmp / "genere.blend", _tmp / "outputs" / "perso.blend")
    rr = cl.post("/api/blender/visage/fichier", json={"source": "outputs/perso.blend", "texte": "Salut, ca va ?"})
    jj = rr.json() if rr.status_code == 200 else {}
    check("B10 /visage/fichier : .blend et .glb animés rendus", rr.status_code == 200 and jj.get("glb") and
          jj.get("blend") and jj["resume"].get("mode") == "procedural", rr.text[:400])
else:
    print("  SKIP  [B] Blender absent (ou VISAGE_SANS_BLENDER=1)")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
