# -*- coding: utf-8 -*-
"""t335 (A5 du lot Scenario, 28/10/2026) — l'ÉCRAN « Previs → plan » : la boîte /shared/dz-previs-plan.js, sa copie
dist, sa balise dans l'Atelier, le bouton act-previs de la carte d'un plan (saisie L8 scripts/i18n_l8/t335.py), ses
textes FR/EN (frontend/shared/i18n/previs.json) et son contrat avec les routes /shots/{id}/previs*.
  [C] copie octet pour octet, balise après dialogue.js / dz-plafonds.js et avant atelier.js, syntaxe (node --check),
      le module se charge sous node et expose window.__dzPrevisPlan.ouvrir ;
  [B] le bouton : après « Plateau 3D », glyphe dz-media-film, title/aria par dzT, écouteur qui ouvre la boîte et relit
      les plans au lancement réussi ; la saisie L8 est à jour (--check) ;
  [T] chaque clé previs.* employée existe en FR et en EN (variables identiques), aucune clé orpheline ;
  [R] le contrat : sources / devis / tir, `confirme_cout: true` seulement après __dzDialogue.confirmer, 409 = nouveau
      devis montré, aucune option de modèle désactivée (un modèle sans clé reste choisissable), devis périmé ignoré.
  [A6] t336 : la boîte du conform (phrase, choix étirer / noir, durée facturée), le dernier rendu et sa dérive.
Run (depuis backend/) : & $PY tests/test_previs_plan_ecran.py"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
SRC = RACINE / "frontend" / "shared" / "dz-previs-plan.js"
DIST = RACINE / "frontend" / "dist" / "shared" / "dz-previs-plan.js"
PAGE = RACINE / "frontend" / "atelier" / "index.html"
AT = RACINE / "frontend" / "atelier" / "atelier.js"
DICO = RACINE / "frontend" / "shared" / "i18n" / "previs.json"
DICO_AT = RACINE / "frontend" / "shared" / "i18n" / "atelier.json"

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


if not SRC.is_file():
    check("C0 la boîte existe", False, SRC)
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)
js = SRC.read_text(encoding="utf-8")
page = PAGE.read_text(encoding="utf-8")
at = AT.read_text(encoding="utf-8")

print("[C] fichiers")
check("C1 copie dist identique octet pour octet", DIST.is_file() and DIST.read_bytes() == SRC.read_bytes())
tags = re.findall(r'<script src="([^"]+)"></script>', page)
check("C2 la balise est posée après dialogue.js et dz-plafonds.js, avant atelier.js",
      "/shared/dz-previs-plan.js" in tags
      and tags.index("/shared/dialogue.js") < tags.index("/shared/dz-previs-plan.js") < tags.index("atelier.js")
      and tags.index("/shared/dz-plafonds.js") < tags.index("/shared/dz-previs-plan.js"), tags)
noeud = shutil.which("node")
if noeud:
    r = subprocess.run([noeud, "--check", str(SRC)], capture_output=True, text=True)
    check("C3 syntaxe de la boîte (node --check)", r.returncode == 0, r.stderr)
    r = subprocess.run([noeud, "--check", str(AT)], capture_output=True, text=True)
    check("C4 syntaxe de atelier.js (node --check)", r.returncode == 0, r.stderr)
    r = subprocess.run([noeud, "-e", "global.window={};global.document={};require(process.argv[1]);"
                        "process.stdout.write(typeof window.__dzPrevisPlan.ouvrir)", str(SRC)],
                       capture_output=True, text=True)
    check("C5 le module se charge sans DOM et expose window.__dzPrevisPlan.ouvrir", r.stdout == "function",
          r.stdout + r.stderr)
else:
    print("  (node absent : C3-C5 sautés)")

print("\n[B] le bouton de la carte du plan")
i_pl, i_pv = at.find('class="btn ghost act-plateau"'), at.find('class="btn ghost act-previs"')
check("B1 act-previs juste après act-plateau, glyphe dz-media-film, title et aria-label par dzT",
      0 < i_pl < i_pv and at[i_pl:i_pv].count("<button") == 1
      and 'title="${dzT("atelier.t335_previs.bouton_t")}" aria-label="${dzT("atelier.t335_previs.bouton")}">${ico("dz-media-film")}'
      in at, at[i_pv:i_pv + 220])
check("B2 l'écouteur ouvre window.__dzPrevisPlan avec la carte et relit les plans au lancement réussi",
      'card.querySelector(".act-previs").addEventListener("click"' in at
      and "window.__dzPrevisPlan.ouvrir({ shot: s, numero: (s.idx || 0) + 1, toast, apres: () => loadShots(true) })" in at)
dat = json.loads(DICO_AT.read_text(encoding="utf-8"))
check("B3 les trois clés atelier.t335_previs.* en FR et EN", all(
    dat.get(k, {}).get("fr") and dat.get(k, {}).get("en") for k in
    ("atelier.t335_previs.bouton", "atelier.t335_previs.bouton_t", "atelier.t335_previs.absent")))
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l8_generer.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
check("B4 la saisie L8 (t335.py) est rejouée : i18n_l8_generer --check à jour", r.returncode == 0,
      (r.stdout + r.stderr)[-400:])

print("\n[T] textes")
d = json.loads(DICO.read_text(encoding="utf-8"))
employees = set(re.findall(r'"(previs\.[a-z0-9_]+\.[a-z0-9_]+)"', js))   # T("…"), ternaires, tables
check("T1 chaque clé employée existe", employees and employees <= set(d), sorted(employees - set(d)))
check("T2 aucune clé orpheline dans previs.json", set(d) <= employees, sorted(set(d) - employees))
mauvaises = [k for k, v in d.items() if not v.get("fr") or not v.get("en")
             or sorted(re.findall(r"\{(\w+)\}", v["fr"])) != sorted(re.findall(r"\{(\w+)\}", v["en"]))]
check("T3 FR et EN présents, mêmes variables", not mauvaises, mauvaises)
check("T4 clés à trois segments", all(len(k.split(".")) == 3 for k in d), [k for k in d if len(k.split(".")) != 3])

print("\n[R] le contrat avec les routes")
check("R1 les trois routes : sources (GET), devis (POST), tir (POST)",
      '"/api/shots/" + encodeURIComponent(E.shot.id) + "/previs/sources"' in js
      and '"/previs/devis"' in js and '+ "/previs",' in js)
i_conf, i_cc = js.find("window.__dzDialogue.confirmer("), js.find("c.confirme_cout = true")
check("R2 confirme_cout n'est posé qu'APRÈS la confirmation maison (et rien ne part sans elle)",
      0 < i_conf < i_cc and "if (!oui || E.ferme) return;" in js[i_conf:i_cc] and js.count("confirme_cout = true") == 1)
check("R3 un 409 montre le NOUVEAU devis (rien n'est parti)",
      "R.status === 409 && j && j.detail && j.detail.devis" in js and "rendreDevis(E, j.detail.devis)" in js)
check("R4 aucune option de modèle n'est désactivée (le sans-clé reste choisissable, clé DITE)",
      "previs.modele.cle_a_ajouter" in js and not re.search(r'option[^;]*disabled', js))
check("R5 un devis périmé est ignoré (jeton)", "if (n !== E.jeton || E.ferme) return;" in js)
check("R6 le devis et le tir envoient le MÊME corps (corpsDe)", js.count("JSON.stringify(corpsDe(E))") == 1
      and "var c = corpsDe(E);" in js)
check("R7 « Lancer » reste inactif tant qu'un refus tient", "griser(E.lancer, !!d.refus);" in js)
check("R8 aucun arrondi (charte Deepotus) : border-radius toujours à 0",
      set(re.findall(r"border-radius:([^;\"]+)", js)) <= {"0"}, set(re.findall(r"border-radius:([^;\"]+)", js)))

print("\n[A6] t336 : durée minimale du modèle et recalage")
check("A1 la boîte du conform : phrase, deux choix (étirer / noir), durée FACTURÉE qui en découle",
      'data-dz-previs": "conform"' in js and '"conform-" + mode' in js and "previs.conform.facture" in js
      and "T(CONFORM[c.mode] || CONFORM.transcoder, v)" in js and "previs.conform.auto" in js)
check("A2 un changement de clip rend le choix au serveur (automatique)",
      "E.choix.clip = c.job_id; E.choix.conform = null;" in js)
check("A3 le dernier rendu du plan montre sa dérive (« dérive : +2 images, recalée »)",
      "rendreDernier(E, E.sources.dernier_rendu)" in js and "previs.recalage.derive_n" in js
      and d.get("previs.recalage.derive_n", {}).get("fr") == "dérive : {d} images, recalée"
      and '(d > 0 ? "+" : "") + d' in js)
if noeud:
    r = subprocess.run([noeud, "-e", "global.window={};global.document={};require(process.argv[1]);"
                        "var E={sources:{modeles:[{id:'s',clip:true},{id:'v',clip:false}]},champ:{value:'p'},"
                        "choix:{modele:'s',clip:'j',tache:'editing',frames:['a'],resolution:'720p',conform:'noir'}};"
                        "var a=window.__dzPrevisPlan._corpsDe(E);E.choix.conform=null;"
                        "var b=window.__dzPrevisPlan._corpsDe(E);E.choix.modele='v';E.choix.conform='noir';"
                        "var c=window.__dzPrevisPlan._corpsDe(E);"
                        "process.stdout.write(JSON.stringify([a.conform,'conform' in b,'conform' in c]))", str(SRC)],
                       capture_output=True, text=True)
    check("A4 corpsDe : « conform » envoyé seulement s'il est choisi, et seulement pour un modèle à clip",
          r.stdout == '["noir",false,false]', r.stdout + r.stderr)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
