# -*- coding: utf-8 -*-
"""t337 (A7 + C4 du lot Scenario, 29/10/2026) — l'ÉCRAN de la revue du plan et du comparateur commun.
  [C] /shared/dz-comparateur.js et /shared/dz-revue-plan.js : copies dist octet pour octet, balises dans l'Atelier
      (après dialogue.js / dz-plafonds.js / dz-previs-plan.js, avant atelier.js), syntaxe (node --check), chargement
      sans DOM ; le banc de comportement node (frontend/shared/qa/comparateur.test.mjs) est vert ;
  [B] les boutons de la carte : « Revue du plan » (act-revue, après Previs → plan), « Comparer à la référence »
      (act-derive-cmp, sous l'image de production), leurs écouteurs ; saisie L8 t337 à jour (--check) ;
  [P] la boîte Previs → plan ouvre le comparateur sur le dernier rendu (GET /revue) ;
  [T] chaque clé comparateur.* / revueplan.* employée existe en FR et en EN avec les mêmes variables, aucune orpheline ;
  [H] honnêteté : la profondeur est dite non mesurée, l'avis jamais présenté comme une garantie, confirmation avant
      tout envoi payant, aucun innerHTML.
Run (depuis backend/) : & $PY tests/test_revue_plan_ecran.py"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
SH = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
PAGE = RACINE / "frontend" / "atelier" / "index.html"
AT = RACINE / "frontend" / "atelier" / "atelier.js"

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


cmp_js = (SH / "dz-comparateur.js").read_text(encoding="utf-8")
rev_js = (SH / "dz-revue-plan.js").read_text(encoding="utf-8")
pv_js = (SH / "dz-previs-plan.js").read_text(encoding="utf-8")
page = PAGE.read_text(encoding="utf-8")
at = AT.read_text(encoding="utf-8")

print("[C] fichiers")
for f in ("dz-comparateur.js", "dz-revue-plan.js", "dz-previs-plan.js"):
    check(f"C1 {f} : copie dist identique", (DIST / f).read_bytes() == (SH / f).read_bytes())
tags = re.findall(r'<script src="([^"]+)"></script>', page)
try:
    i = {t: tags.index(t) for t in ("/shared/dialogue.js", "/shared/dz-plafonds.js", "/shared/dz-previs-plan.js",
                                    "/shared/dz-comparateur.js", "/shared/dz-revue-plan.js", "atelier.js")}
    bon = i["/shared/dz-plafonds.js"] < i["/shared/dz-comparateur.js"] and i["/shared/dialogue.js"] < i["/shared/dz-comparateur.js"] \
        and i["/shared/dz-previs-plan.js"] < i["/shared/dz-comparateur.js"] < i["/shared/dz-revue-plan.js"] < i["atelier.js"]
except ValueError:
    bon = False
check("C2 balises du comparateur et de la revue dans l'Atelier, dans l'ordre", bon, tags)
noeud = shutil.which("node")
if noeud:
    for f in ("dz-comparateur.js", "dz-revue-plan.js"):
        r = subprocess.run([noeud, "--check", str(SH / f)], capture_output=True, text=True)
        check(f"C3 syntaxe {f}", r.returncode == 0, r.stderr)
    r = subprocess.run([noeud, "-e", "global.window={};global.document={};require(process.argv[1]);require(process.argv[2]);"
                        "process.stdout.write(typeof window.__dzComparateur.ouvrir+typeof window.__dzComparateur.monter"
                        "+typeof window.__dzRevuePlan.ouvrir)", str(SH / "dz-comparateur.js"), str(SH / "dz-revue-plan.js")],
                       capture_output=True, text=True)
    check("C4 les modules se chargent sans DOM et exposent ouvrir / monter", r.stdout == "functionfunctionfunction",
          r.stdout + r.stderr)
    r = subprocess.run([noeud, str(SH / "qa" / "comparateur.test.mjs")], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    check("C5 le banc de comportement node est vert", r.returncode == 0 and "0 failed" in r.stdout, r.stdout[-800:])
else:
    print("  (node absent : C3-C5 sautés)")

print("\n[B] la carte du plan")
i_pv, i_rv = at.find('class="btn ghost act-previs"'), at.find('class="btn ghost act-revue"')
check("B1 act-revue juste après act-previs, glyphe dz-etat-note, title et aria-label par dzT",
      0 < i_pv < i_rv and at[i_pv:i_rv].count("<button") == 1
      and 'aria-label="${dzT("atelier.t337_revue.bouton")}">${ico("dz-etat-note")}</button>' in at)
check("B2 act-derive-cmp sous l'image de production, glyphe dz-action-comparer",
      '<div class="shot-derive"></div>\r\n        <button class="btn ghost act-derive-cmp"' in at.replace("\r\n", "\n").replace("\n", "\r\n")
      and '${ico("dz-action-comparer")}</button>` : ""}' in at)
check("B3 les écouteurs : la revue ouvre __dzRevuePlan, le comparateur lit /derive (gratuit) puis __dzComparateur",
      'window.__dzRevuePlan.ouvrir({ shot: s, numero: (s.idx || 0) + 1, toast })' in at
      and "api.get(`/shots/${encodeURIComponent(id)}/derive`)" in at and "window.__dzComparateur.ouvrir({" in at)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l8_generer.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
check("B4 la saisie L8 (t337) est à jour", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])

print("\n[P] Previs → plan")
check("P1 le dernier rendu se compare à sa previs : GET /revue puis le comparateur, previs à gauche",
      '"/revue");' in pv_js and "window.__dzComparateur.ouvrir({ a: { src: j.previs.url" in pv_js
      and "montrer(E.comparer, !!(dr && dr.job_id && dr.status === \"done\"))" in pv_js)

print("\n[T] textes")
dico = {}
for f in ("comparateur.json", "revueplan.json", "previs.json", "atelier.json"):
    dico.update(json.loads((SH / "i18n" / f).read_text(encoding="utf-8")))
emplois = set(re.findall(r'"((?:comparateur|revueplan)\.[a-z_]+\.[a-z_0-9]+)"', cmp_js + rev_js))
emplois |= {"revueplan.critere." + c for c in ("mouvement", "cadrage", "style", "personnages", "lumiere", "artefacts")}
emplois |= {"revueplan.gravite." + g for g in ("mineur", "moyen", "majeur")}
emplois |= {"revueplan.moment." + m for m in ("debut", "milieu", "fin")}
emplois |= set(re.findall(r'T\("(previs\.recalage\.[a-z_]+)"', pv_js))
emplois |= set(re.findall(r'dzT\("(atelier\.t337_[a-z_]+\.[a-z_]+)"', at))
manque = sorted(k for k in emplois if k not in dico or not dico[k].get("fr") or not dico[k].get("en"))
check("T1 chaque clé employée existe en FR et en EN", not manque, manque)
var = sorted(k for k in emplois if k in dico
             and set(re.findall(r"\{(\w+)\}", dico[k]["fr"])) != set(re.findall(r"\{(\w+)\}", dico[k]["en"])))
check("T2 mêmes variables en FR et en EN", not var, var)
propres = {k for k in dico if k.startswith(("comparateur.", "revueplan."))}
orph = sorted(propres - emplois)
check("T3 aucune clé orpheline (comparateur.*, revueplan.*)", not orph, orph)
check("T4 toutes les clés ont trois segments", all(len(k.split(".")) == 3 for k in propres))

print("\n[H] honnêteté et dépense")
check("H1 la profondeur est dite NON mesurée (FR et EN)", "non mesurée" in dico["revueplan.mesures.profondeur"]["fr"]
      and "not measured" in dico["revueplan.mesures.profondeur"]["en"])
check("H2 l'avis n'est jamais une garantie : avertissement affiché avec l'avis et dans la confirmation",
      "garantie" in dico["revueplan.avis.avertissement"]["fr"] and "guarantee" in dico["revueplan.avis.confirmer"]["en"]
      and 'T("revueplan.avis.avertissement")' in rev_js)
i_conf, i_post = rev_js.find("window.__dzDialogue.confirmer("), rev_js.find('chemin(E, "/note")')
check("H3 confirmation AVANT l'appel payant, qui porte confirme_cout et max_usd ; sans dialogue, rien ne part",
      0 < i_conf < i_post and "confirme_cout: true, max_usd: montant" in rev_js and ": false;" in rev_js[i_conf:i_post])
check("H4 aucun innerHTML", ".innerHTML" not in cmp_js and ".innerHTML" not in rev_js)
check("H5 le bouton d'avis n'est jamais grisé faute de clé (le 503 tombe au clic)",
      "griser(E.btnAvis, false);" in rev_js[rev_js.find("function rendreDevis"):rev_js.find("async function demander")])
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
