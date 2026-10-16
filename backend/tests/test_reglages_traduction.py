# -*- coding: utf-8 -*-
"""t224 (Menus : Réglages, 16/10/2026) — traduction des écrans t219-t223, bulle « Générer » du Vectorlab selon le moteur,
chapitres du guide.

Ce que ce banc garde :
  [K] le maillon dzreglages (t219-t223, 21 paires) : aucun texte visible en dur (props visibles, placeholders des
      saisies, littéraux d'allure française) ; aucune clé dzT construite ; chaque clé citée existe en FR ET en EN dans
      le catalogue assemblé, l'anglais n'est pas le français recopié ; une phrase FR = une traduction ;
  [V] Vectorlab, dialogue IA : la bulle du bouton « Générer » disait « APPEL PAYANT … quelques centièmes de centime »
      pour TOUT moteur. Un serveur local (`ollama`, `local:<id>`, t223) est GRATUIT ; un fournisseur libre (`fl:<id>`,
      t222) n'a pas de tarif connu : « prix à mesurer », jamais « gratuit » ; les intégrés payants (anthropic, openai,
      gemini) gardent le texte d'avant. js/mod-ia.js est sous la table L6 (positions fixes) : l'édition est consignée
      en entrée S (scripts/i18n_l6/iacout.py) et la table est régénérée (`i18n_l6_generer --check` à jour) ;
  [G] le guide : chapitres `cles`, `modeles-et-cles` et `budget` à jour (pastille → Tarifs et budget, Fournisseurs par
      défaut, fournisseurs libres, serveurs locaux, Diagnostic « Régler »), FR et EN, scènes présentes.
Run (depuis backend/) : & $PY tests/test_reglages_traduction.py"""
import importlib.util, json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def module(nom):
    spec = importlib.util.spec_from_file_location(nom, RACINE / "scripts" / f"{nom}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


I18N = RACINE / "frontend" / "shared" / "i18n"
DICO = {}
for f in sorted(I18N.glob("*.json")):
    for k, v in json.loads(f.read_text(encoding="utf-8")).items():
        if isinstance(v, dict) and isinstance(v.get("fr"), str):
            DICO[k] = v
PAR_FR = {}                                     # bâti UNE fois (t222 : relire les catalogues dans une boucle fige)
for k, v in DICO.items():
    if not v.get("contexte"):
        PAR_FR.setdefault(v["fr"], set()).add(v.get("en"))

print("[K] maillon dzreglages : aucune chaîne visible en dur")
DZR = module("patch_bundle_dzreglages")
check("K0 21 paires (t219-t223), rien d'ajouté par t224", len(DZR.PAIRES) == 21, str(len(DZR.PAIRES)))
NEUF = [n.replace(a, "\x00", 1) for a, n in DZR.PAIRES]          # le code POSÉ (l'ancre d'origine retirée)
durs = []
for n in NEUF:
    durs += re.findall(r'(?:children|placeholder|title|"aria-label"|alt|label):"([^"]*[A-Za-zÀ-ÿ][^"]*)"', n)
durs = [x for x in durs if not re.fullmatch(r"[A-Z0-9_]+", x)]          # un NOM de variable d'env (mono), pas un texte
check("K1 aucune prop visible (children, placeholder, title, aria-label, alt, label) en dur", not durs, str(durs))
EXEMPLES = {"DeepSeek", "LM Studio", "https://api.example.com/v1", "http://127.0.0.1:1234/v1", "http://127.0.0.1:11434"}
ph = []
for n in NEUF:
    ph += re.findall(r'dz(?:Fl|Sl)Saisie\("[^"]*",[^"]*?,"([^"]*)",function', n)     # 3e argument = placeholder
    ph += re.findall(r'f\.type==="openai"\?"(http[^"]+)":"(http[^"]+)"', n)
ph = {x for t in ph for x in (t if isinstance(t, tuple) else (t,))}
check("K2 les exemples de saisie en dur ne sont que des noms propres et des URL", ph and ph <= EXEMPLES,
      str(sorted(ph - EXEMPLES)))
LIT = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
FRANCAIS = re.compile(r"[àâçéèêëîïôûùœÀÂÇÉÈÊ]|\b(?:le|la|les|des|une|aucun|aucune|clé|modèle|serveur|fournisseur|"
                      r"supprimer|ajouter|gratuit|prix)\b", re.I)
fr_durs = sorted({x for n in NEUF for x in LIT.findall(n) if FRANCAIS.search(x) and not re.fullmatch(r"[a-z0-9_./-]+", x)})
check("K3 aucun littéral d'allure française dans le code posé par le maillon", not fr_durs, str(fr_durs))
construites = [m for n in NEUF for m in re.findall(r'dzT\((?:"[^"]*"\s*\+|`)', n)]
check("K4 aucune clé dzT construite (\"x.\"+… ou gabarit)", not construites, str(construites))
CLES = sorted({c for n in NEUF for c in LIT.findall(n) if re.fullmatch(r"[a-z0-9]+(?:\.[a-z0-9_]+){2,}", c)})
check("K5 les clés citées par le maillon sont nombreuses (tables comprises)", len(CLES) >= 75, str(len(CLES)))
absentes = [c for c in CLES if c not in DICO or not DICO[c].get("fr") or not DICO[c].get("en")]
check("K6 chaque clé existe en FR et en EN dans frontend/shared/i18n", not absentes, str(absentes))
recopiees = [c for c in CLES if c in DICO and DICO[c]["en"] == DICO[c]["fr"] and re.search(r"[éèàçêù]|\b(?:le|la|les|des)\b",
             DICO[c]["fr"])]
check("K7 aucun anglais qui recopie le français", not recopiees, str(recopiees))
doubles = {c: sorted(PAR_FR[DICO[c]["fr"]]) for c in CLES if c in DICO and not DICO[c].get("contexte")
           and len(PAR_FR.get(DICO[c]["fr"], ())) > 1}
check("K8 une phrase FR = une traduction pour chaque clé du maillon", not doubles, str(doubles))
ASSEMBLE = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
check("K9 le dictionnaire assemblé porte ces clés (servi) et la copie dist est identique à l'octet",
      all(f'"{c}"' in ASSEMBLE for c in CLES)
      and (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
      == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())
BUNDLE = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
try: rond = DZR.MARKER in BUNDLE and DZR.appliquer(DZR.defaire(BUNDLE)) == BUNDLE
except (AssertionError, SystemExit): rond = False
check("K10 le bundle porte le maillon (marqueur, aller-retour exact)", rond)

print("[V] Vectorlab : la bulle de « Générer » dit le vrai coût du moteur")
MODIA = (RACINE / "frontend" / "vectorlab" / "js" / "mod-ia.js").read_text(encoding="utf-8")
VL = json.loads((I18N / "vectorlab.json").read_text(encoding="utf-8"))
NOUVELLES = ("vectorlab.ia.payant", "vectorlab.ia.gratuit", "vectorlab.ia.a_mesurer")
check("V1 trois clés FR/EN (payant inchangée, gratuit, à mesurer), variable {moteur} des deux côtés",
      all(k in VL and "{moteur}" in VL[k]["fr"] and "{moteur}" in VL[k]["en"] for k in NOUVELLES)
      and VL.get("vectorlab.ia.payant") == {"fr": "APPEL PAYANT sur votre clé {moteur} — quelques centièmes de centime",
                                            "en": "PAID CALL on your {moteur} key — a few hundredths of a cent"})
g, a = VL.get("vectorlab.ia.gratuit", {}), VL.get("vectorlab.ia.a_mesurer", {})
check("V2 le local dit « gratuit » / « free », sans « PAYANT » ni « PAID »",
      "gratuit" in g.get("fr", "") and "free" in g.get("en", "").lower()
      and "PAYANT" not in g.get("fr", "") and "PAID" not in g.get("en", ""))
check("V3 le libre dit « prix à mesurer » / « price to be measured », jamais « gratuit » / « free »",
      "prix à mesurer" in a.get("fr", "") and "price to be measured" in a.get("en", "")
      and "gratuit" not in a.get("fr", "") and "free" not in a.get("en", "").lower())
fn = re.search(r"\n  function bulleGenerer\(id\) \{\r?\n[\s\S]*?\r?\n  \}\r?\n", MODIA)
check("V4 mod-ia.js : bulleGenerer(id) posée, et le titre du bouton « Générer » l'appelle (plus de payant en dur)",
      fn is not None and ": bulleGenerer(choisi)}\"" in MODIA
      and MODIA.count('T("vectorlab.ia.payant"') == 1 and MODIA.count("bulleGenerer(") == 2)
NODE = r"""
const fs=require("fs");const [src,dico]=[process.argv[2],JSON.parse(fs.readFileSync(process.argv[3],"utf8"))];
const out={};
for(const lang of ["fr","en"]){
 const T=(k,v)=>{const e=dico[k];if(!e)return "ABSENTE:"+k;let s=e[lang];return s.replace(/\{(\w+)\}/g,(m,n)=>v&&v[n]!=null?v[n]:m)};
 const nomMoteur=id=>id+" · m1";
 const bulleGenerer=new Function("T","nomMoteur",src+";return bulleGenerer")(T,nomMoteur);
 out[lang]={};
 for(const id of ["anthropic","openai","gemini","ollama","local:lmstudio","local:ollama2","fl:deepseek","fl:groq","localx"])
  out[lang][id]=bulleGenerer(id);
}
console.log(JSON.stringify(out));
"""
res = {}
if fn:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "h.js").write_text(NODE, encoding="utf-8")
        p = subprocess.run(["node", str(pathlib.Path(d) / "h.js"), fn.group(0), str(I18N / "vectorlab.json")],
                           capture_output=True, text=True, encoding="utf-8")
        try: res = json.loads(p.stdout)
        except Exception: res = {"err": p.stderr[-400:]}
fr, en = res.get("fr", {}), res.get("en", {})
check("V5 (node) anthropic / openai / gemini : le texte d'avant, « APPEL PAYANT … » / « PAID CALL … »",
      all(fr.get(i, "").startswith("APPEL PAYANT sur votre clé " + i + " · m1") for i in ("anthropic", "openai", "gemini"))
      and all(en.get(i, "").startswith("PAID CALL on your " + i + " · m1") for i in ("anthropic", "openai", "gemini")),
      str(res)[:300])
check("V6 (node) ollama et local:<id> : gratuit, aucun « PAYANT » / « PAID »",
      all("gratuit" in fr.get(i, "") and "PAYANT" not in fr.get(i, "") and "free" in en.get(i, "")
          and "PAID" not in en.get(i, "") and (i + " · m1") in fr.get(i, "")
          for i in ("ollama", "local:lmstudio", "local:ollama2")), str(fr))
check("V7 (node) fl:<id> : prix à mesurer, jamais gratuit",
      all("prix à mesurer" in fr.get(i, "") and "gratuit" not in fr.get(i, "") and "price to be measured" in en.get(i, "")
          and "free" not in en.get(i, "") for i in ("fl:deepseek", "fl:groq")), str(fr))
check("V8 (node) un id qui commence par « local » sans « : » reste payant (pas de faux gratuit)",
      fr.get("localx", "").startswith("APPEL PAYANT"), fr.get("localx"))
p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l6_generer.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                   env=dict(__import__("os").environ, PYTHONIOENCODING="utf-8"))
check("V9 la table L6 est à jour (édition consignée en entrée S, pas à la main)", "à jour" in p.stdout,
      (p.stdout + p.stderr)[-400:])
SAISIE = RACINE / "scripts" / "i18n_l6" / "iacout.py"
check("V10 le groupe de saisie iacout.py consigne l'édition sur la BASE", SAISIE.exists()
      and "bulleGenerer" in SAISIE.read_text(encoding="utf-8"))

print("[G] guide")
GUIDE = RACINE / "docs" / "guide"
FRH = (GUIDE / "fr.html").read_text(encoding="utf-8") if (GUIDE / "fr.html").exists() else ""
ENH = (GUIDE / "en.html").read_text(encoding="utf-8") if (GUIDE / "en.html").exists() else ""
def chapitre(html, cid):
    m = re.search(r'<section[^>]*id="' + re.escape(cid) + r'"[\s\S]*?</section>', html)
    return m.group(0) if m else ""
for cid, fr_mots, en_mots in [
        ("cles", ["fournisseur libre", "serveur", "Régler"], ["free provider", "server", "Set"]),
        ("modeles-et-cles", ["Fournisseurs par défaut", "prix à mesurer", "gratuit"],
         ["Provider defaults", "price to be measured", "free"]),
        ("budget", ["Tarifs et budget", "pastille"], ["Pricing", "badge"])]:
    cf, ce = chapitre(FRH, cid), chapitre(ENH, cid)
    check(f"G-{cid} le chapitre existe en FR et en EN et cite le neuf",
          cf and ce and all(m.lower() in cf.lower() for m in fr_mots) and all(m.lower() in ce.lower() for m in en_mots),
          f"fr={[m for m in fr_mots if m.lower() not in cf.lower()]} en={[m for m in en_mots if m.lower() not in ce.lower()]}")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
