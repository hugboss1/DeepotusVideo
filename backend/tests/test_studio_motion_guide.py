# -*- coding: utf-8 -*-
"""Studio t237 — traduction et guide du lot « Studio : Animation » (18/10/2026).

Relevé (base 332c8b84, t231-t236 et t239-t241 livrées) : les 123 clés `studio.motion.*` de frontend/shared/i18n/motion.json
sont toutes FR + EN et le banc K de test_studio_motion_direction (K1-K8) couvre déjà le maillon dzmotion (aucune chaîne en
dur, clés employées = clés du fichier, mêmes variables). Restaient des écarts de SENS en anglais, relus en contexte :
« précisions » rendu tantôt « specifics », tantôt « details » ; un prix « about {usd} $ » quand toute l'app écrit
« ${usd} » ; le cran « Soignée » de la Finition traduit « Careful », comme le cran « Prudente » de la Créativité. Le
chapitre Studio du guide ne disait rien de l'animation par IA.

Ce que ce banc garde :
  [K] vocabulaire anglais de motion.json et de la personnalisation (backend/app/motion/personnalisation.json) ;
      messages d'erreur backend traduits (i18n_l10_erreurs --check) ;
  [G] la section « Animer avec l'IA » du chapitre Studio (FR et EN, même squelette), ses trois scènes capturées en
      FR et en EN (plan t237), l'encadré licence, le guide construit à jour ;
  [L] garde G3 : les contenus de démonstration (plan, backend de preuve du guide) n'emploient que des hôtes à nous.
Run (depuis la racine) : & $PY backend/tests/test_studio_motion_guide.py"""
import json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent

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


print("[K] vocabulaire FR / EN de Direction motion")
MO = json.loads((RACINE / "frontend/shared/i18n/motion.json").read_text("utf-8"))
check("K1 123 clés studio.motion.*, toutes FR ET EN", len(MO) >= 123 and all(
    k.startswith("studio.motion.") and v.get("fr") and v.get("en") for k, v in MO.items()), str(len(MO)))
prec = {k: v["en"] for k, v in MO.items() if re.search(r"précision", v["fr"], re.I)}
check("K2 « précisions » se dit toujours « specifics » (jamais « details »)",
      bool(prec) and all("specific" in e.lower() and "detail" not in e.lower() for e in prec.values()), str(prec))
check("K3 un prix en dollars s'écrit ${usd} en anglais, comme dans le reste de l'app",
      all("{usd} $" not in v["en"] for v in MO.values()) and "${usd}" in MO["studio.motion.cout_bilan_payant"]["en"],
      MO["studio.motion.cout_bilan_payant"]["en"])
check("K4 « le kit de marque de l'espace » = « the space's brand kit »",
      "the space's brand kit" in MO["studio.motion.remplacements_aide"]["en"])
PE = json.loads((RACINE / "backend/app/motion/personnalisation.json").read_text("utf-8"))
etats = [(c["etat"]["fr"], c["etat"]["en"]) for cur in PE["curseurs"].values() for c in cur["crans"]]
en_vus = {}
for fr, en in etats:
    en_vus.setdefault(en, set()).add(fr.lower().replace("tel quel", "telle quelle"))
check("K5 deux crans différents n'ont jamais la même traduction (Soignée ≠ Prudente)",
      all(len(v) == 1 for v in en_vus.values()), str({k: v for k, v in en_vus.items() if len(v) > 1}))
fin = PE["curseurs"]["finition"]
check("K6 Finition : pôle et cran « soignée » = « polished »", fin["poles"]["en"][1] == "polished"
      and fin["crans"][3]["etat"]["en"] == "Polished", str(fin["poles"]["en"]))
check("K7 « consigne » = « brief » dans les phrases des curseurs et la règle des précisions",
      all("brief" in c["phrase"]["en"] for c in PE["curseurs"]["creativite"]["crans"] if c["phrase"])
      and "brief" in PE["precisions"]["regle"]["en"])
r = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_l10_erreurs.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", cwd=str(RACINE), env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
check("K8 messages d'erreur backend (motion compris) : tous traduits, à jour", r.returncode == 0 and "0 sans traduction" in r.stdout,
      (r.stdout + r.stderr)[-300:])

print("[G] section « Animer avec l'IA » du chapitre Studio")
SRC = RACINE / "docs/guide/src"
FR = (SRC / "fr/studio.html").read_text("utf-8")
EN = (SRC / "en/studio.html").read_text("utf-8")


def squelette(h):
    return re.findall(r"<(h3|ol|li|figure|aside|article|table)\b", h)


def section(h, titre):
    i = h.find(f"<h3>{titre}</h3>")
    return h[i:h.find("<h3>", i + 4)] if i >= 0 else ""


SF, SE = section(FR, "Animer avec l'IA"), section(EN, "Animate with AI")
check("G1 la section existe en FR et en EN", bool(SF) and bool(SE))
check("G2 même squelette FR / EN (chapitre et section)", squelette(FR) == squelette(EN) and squelette(SF) == squelette(SE)
      and len(squelette(SF)) > 8, f"{len(squelette(SF))} / {len(squelette(SE))}")
SCENES = ["studio/motion-choregraphier", "studio/motion-personnaliser", "studio/motion-biblio"]
check("G3 trois scènes dans l'ordre Direction motion → Chorégraphier → aperçu, Personnaliser, Bibliothèque",
      re.findall(r'data-scene="([^"]+)"', SF) == SCENES == re.findall(r'data-scene="([^"]+)"', SE))
for fr_, en_ in (("Direction motion", "Motion direction"), ("Chorégraphier", "Choreograph"), ("Aperçu", "Preview"),
                 ("Personnaliser", "Customise"), ("Effort", "Effort"), ("Importer un prompt", "Import a prompt"),
                 ("Installer un skill", "Install a skill"), ("Lire la licence", "Read the licence"),
                 ("Filtrer par thème", "Filter by theme"), ("Utiliser", "Use"), ("Supprimer", "Delete")):
    check(f"G4 libellé d'écran « {fr_} » / « {en_} »", f'<b class="ui">{fr_}</b>' in SF and f'<b class="ui">{en_}</b>' in SE)
check("G5 l'URL de la fiche d'origine est dite obligatoire ; la licence se lit AVANT l'installation",
      "obligatoire" in SF and "AVANT" in SF and "required" in SE and "BEFORE" in SE)
check("G6 encadré licence : les prompts restent à leurs créateurs",
      re.search(r'<aside class="attention">.*Les prompts restent à leurs créateurs', SF, re.S) is not None
      and re.search(r'<aside class="attention">.*Prompts still belong to their creators', SE, re.S) is not None)
_P = SRC / "scenes/plans/t237.json"
PLAN = json.loads(_P.read_text("utf-8")) if _P.is_file() else {"scenes": [], "base": ""}
check("G7 plan t237 : les trois scènes, backend de preuve hors 8765", [s["scene"] for s in PLAN["scenes"]] == SCENES
      and ":8765" not in PLAN["base"])
for sc in SCENES:
    d = SRC / "scenes" / sc
    j = json.loads((d / "scene.json").read_text("utf-8")) if (d / "scene.json").is_file() else {}
    caps = j.get("captures", [])
    check(f"G8 {sc} : captures FR et EN présentes et distinctes, repères mesurés",
          len(caps) >= 2 and all((d / c[l]).is_file() for c in caps for l in ("fr", "en"))
          and all((d / c["fr"]).read_bytes() != (d / c["en"]).read_bytes() for c in caps)
          and all(any(k in t for k in ("curseur", "surligne")) for t in j.get("temps", [])), str(caps))
r = subprocess.run([sys.executable, str(RACINE / "scripts/guide/construire_guide.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", cwd=str(RACINE), env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
check("G9 guide construit à jour (construire_guide.py --check)", r.returncode == 0, (r.stdout + r.stderr)[-300:])
BUILT = (RACINE / "docs/guide/fr.html").read_text("utf-8"), (RACINE / "docs/guide/en.html").read_text("utf-8")
check("G10 fr.html et en.html publient la section", "Animer avec l'IA" in BUILT[0] and "Animate with AI" in BUILT[1])

print("[L] garde G3 : démonstrations écrites par nous")
_S = RACINE / "scripts/guide/serve_guide_motion.py"
DEMO = (PLAN, _S.read_text("utf-8") if _S.is_file() else "")
hotes = set(re.findall(r"https?://([A-Za-z0-9.-]+)", json.dumps(DEMO[0], ensure_ascii=False) + DEMO[1]))
check("L1 seuls des hôtes à nous ou locaux (deepotus.xyz, 127.0.0.1, github de démonstration)",
      hotes <= {"deepotus.xyz", "127.0.0.1"}, str(hotes))
check("L2 les dépôts de skill de la démo sont ceux de deepotus-demo", set(re.findall(r"[\w-]+/[\w-]+-mit|deepotus-demo/[\w-]+",
      DEMO[1])) >= {"deepotus-demo/rebond-mit"} and all(x.startswith("deepotus-demo/") for x in re.findall(
      r'"source": "([^"]+)"', DEMO[1])))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
