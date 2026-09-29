# -*- coding: utf-8 -*-
"""Tâche #20, PR 2/2 (plan Settings T17, 29/09/2026) — L'ÉCRAN DU COFFRE dans le bundle.
Témoin : la base fca4207 (PR 1 fusionnée) n'a ni DzCoffre, ni entrée « Coffre », ni pastille à trois états.
Le banc relit le BUNDLE LIVRÉ : entrée de barre + liste blanche + branche ; chaque route du coffre appelée depuis
l'écran, et seulement elles ; poser passe par une CONFIRMATION (les secrets quittent le .env) ; les mots de passe ne
vont que dans des champs `password`, jamais dans le stockage du navigateur ; la pastille d'une clé connaît le 3e état.
Run : & $PY tests/test_p2_coffre_ecran.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
import patch_bundle_montage as P                              # noqa: E402

BASE = "fca4207"
NODE = shutil.which("node")
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


raw = BUNDLE.read_bytes()
s = raw.decode("utf-8")
vieux = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], cwd=ROOT, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base %s" % BASE)
check("0.1 TÉMOIN : ni DzCoffre, ni entrée, ni branche, ni 3e état", vieux and "function DzCoffre(" not in vieux
      and '{k:"coffre"' not in vieux and 's==="coffre"' not in vieux and 'h.set===null' not in vieux, "")

print("\n[1] l'écran branché")
check("1.1 entrée « Coffre » juste après « Diagnostic »", s.count('[{k:"diag",l:"Diagnostic"},{k:"coffre",l:"Coffre"},{k:"keys",l:"API keys"},') == 1)
check("1.2 'coffre' dans la liste blanche (sinon ?section=coffre retombe sur accounts)", s.count('const ym=["diag","coffre","keys",') == 1)
check("1.3 branche du corps rend DzCoffre", s.count('s==="coffre"&&r.jsx(DzCoffre,{}),') == 1 and s.count("function DzCoffre(") == 1)
dz = s[s.find("function DzCoffre("):s.find("function DzPricing(")]
ROUTES = ["etat", "poser", "ouvrir", "fermer", "retenir", "oublier", "mot-de-passe", "archive", "archive/importer"]
appels = re.findall(r"'/api/reglages/coffre/([a-z/-]+)'", dz)
check("1.4 chaque route du coffre est appelée depuis l'écran, une fois, et rien d'autre",
      sorted(appels) == sorted(ROUTES) and dz.count("fetch(") == 4 and dz.count("poste('") == 6, json.dumps(appels))

print("\n[2] ce qui protège l'utilisateur")
i = dz.find("const poser=")
bloc = dz[i:dz.find("const ouvrir=", i)]
check("2.1 poser passe par une CONFIRMATION du dialogue maison, avant l'appel, qui dit que les clés quittent le .env",
      "const D=window.__dzDialogue;if(!D||!(await D.confirmer(" in bloc and bloc.find("D.confirmer(") < bloc.find("/api/reglages/coffre/poser") and "QUITTENT le fichier .env" in bloc
      and "stocké nulle part" in bloc, "")
check("2.2 poser exige 8 caractères et deux saisies identiques, côté écran aussi", "m1.length<8" in bloc and "m1!==m2" in bloc)
champs = re.findall(r"r\.jsx\('input',\{type:'([a-z]+)'", dz)
check("2.3 les mots de passe ne vont que dans des champs `password` (le seul autre champ est le fichier)", champs == ["password", "file"], json.dumps(champs))
check("2.4 aucun mot de passe dans le stockage du navigateur ni dans la console", "localStorage" not in dz and "sessionStorage" not in dz and "console." not in dz)
check("2.5 les champs se vident après chaque geste", dz.count("setM1('')") >= 3 and "setAnc('')" in dz and "ev.target.value=''" in dz)
check("2.6 l'archive se télécharge par un blob révoqué APRÈS 2 s (un blob révoqué trop tôt n'arrive pas)",
      "setTimeout(()=>URL.revokeObjectURL(u),2000)" in dz and "a.download='DeepotusVideoGen-'" in dz)
check("2.7 importer exige le mot de passe de l'archive AVANT d'envoyer le fichier",
      "if(arc.length<1){dire(!1," in dz and dz.find("if(arc.length<1)") < dz.find("/api/reglages/coffre/archive/importer"))
ks = re.findall(r"r\.jsx\(K,\{(.*?)children:", dz)
check("2.8 tout bouton porte un title (E-12)", len(ks) == 7 and all("title:" in k for k in ks), str(len(ks)))

print("\n[3] la pastille d'une clé : trois états")
check("3.1 coffre verrouillé (set=null) : ambre « coffre », et DzTestCle dit « coffre fermé » avec quoi faire (le badge `te` ne porte pas de bulle, mesuré)",
      s.count('tone:h&&h.set===null?"amber":h&&h.set?"green":"red"') == 1 and s.count('children:h&&h.set===null?"coffre":h&&h.set?"set":"missing"}),') == 1
      and s.count("def:!!(h&&h.set),verrou:!!(h&&h.set===null)})") == 1 and "Coffre verrouillé : ouvrez-le" in s[s.find("function DzTestCle("):s.find("const Fu=[")])
check("3.2 « Tester » reste caché tant que la clé est verrouillée (def = !!set)", s.count("r.jsx(DzTestCle,{ck:k.k,def:!!(h&&h.set),verrou:") == 1)
check("3.3 l'ancienne pastille à deux états a disparu", 'tone:h&&h.set?"green":"red",dot:!0,children:h&&h.set?"set":"missing"}' not in s)

print("\n[4] intégrité du bundle")
check("4.1 fins de ligne : 100 % CRLF", raw.count(b"\n") == raw.count(b"\r\n"))
nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("4.2 node --check du bundle entier", nc is not None and nc.returncode == 0, (nc.stderr[-300:] if nc else ""))
check("4.3 aucune séquence \\u littérale restée dans l'écran", "\\u20" not in dz and "\\u00" not in dz)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
