# -*- coding: utf-8 -*-
"""Suite du lot « Menus : Réglages » (16/10/2026) — deux textes restés faux après t222-t224.

Ce que ce banc garde :
  [W] Vectorlab, panneau Vitrail : la bulle du bouton IA (`vectorlab.vitrail.ia_titre`) disait « APPEL PAYANT sur
      votre clé, quelques centièmes de centime » pour TOUT moteur. Le panneau POSTE /api/vector/illustration SANS
      `provider` : la route prend alors le PREMIER moteur configuré (`dispo[0]`), celui que GET …/moteurs rend en tête
      (`actif`). La bulle suit la règle de `bulleGenerer(id)` (js/mod-ia.js, t224) : un serveur local (`ollama`,
      `local:<id>`) est GRATUIT ; un fournisseur libre (`fl:<id>`) est « prix à mesurer », jamais « gratuit » ; les
      intégrés payants — et un moteur encore inconnu — gardent le texte d'avant. js/mod-vitrail.js est sous la table
      L6 : l'édition est consignée en entrées S (scripts/i18n_l6/vitrailcout.py), `i18n_l6_generer --check` à jour ;
  [R] Réglages › Fournisseurs par défaut : l'aide du rôle « Résumé des News » (`reglages.defauts.resume_aide`) ne
      citait qu'« Anthropic, OpenAI ou Gemini » ; le rôle accepte aussi un fournisseur libre et un serveur local
      (summarizer : `fl:` / `local:`). La clé vient de la saisie L1 (scripts/i18n_l1/reglages_comptes.py,
      `i18n_l1_generer --check` à jour) ; une phrase FR = une traduction.
Run (depuis backend/) : & $PY tests/test_textes_moteur.py"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


I18N = RACINE / "frontend" / "shared" / "i18n"
DICO = {}
for f in sorted(I18N.glob("*.json")):
    for k, v in json.loads(f.read_text(encoding="utf-8")).items():
        if isinstance(v, dict) and isinstance(v.get("fr"), str):
            DICO[k] = v
PAR_FR = {}
for k, v in DICO.items():
    if not v.get("contexte"):
        PAR_FR.setdefault(v["fr"], set()).add(v.get("en"))
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def generateur(nom):
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / nom), "--check"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(RACINE), env=ENV)
    return p.returncode, (p.stdout + p.stderr)


print("[W] Vectorlab, panneau Vitrail : la bulle du bouton IA dit le vrai coût du moteur")
AVANT_FR = ("Illustration vectorielle par le modèle de langage configuré (Réglages) — APPEL PAYANT sur votre clé, "
            "quelques centièmes de centime ; pose des masses de verre en un groupe")
AVANT_EN = ("Vector illustration by the configured language model (Settings) — PAID CALL on your key, a few hundredths "
            "of a cent; places glass masses as one group")
VL = json.loads((I18N / "vectorlab.json").read_text(encoding="utf-8"))
G, A = VL.get("vectorlab.vitrail.ia_titre_gratuit", {}), VL.get("vectorlab.vitrail.ia_titre_a_mesurer", {})
check("W1 ia_titre inchangée (payant) ; ia_titre_gratuit et ia_titre_a_mesurer en FR/EN, {moteur} des deux côtés",
      VL.get("vectorlab.vitrail.ia_titre") == {"fr": AVANT_FR, "en": AVANT_EN}
      and all("{moteur}" in d.get("fr", "") and "{moteur}" in d.get("en", "") for d in (G, A)))
check("W2 le local dit « gratuit » / « free », sans « PAYANT » ni « PAID »",
      "gratuit" in G.get("fr", "") and "free" in G.get("en", "").lower()
      and "PAYANT" not in G.get("fr", "") and "PAID" not in G.get("en", ""))
check("W3 le libre dit « prix à mesurer » / « price to be measured », jamais « gratuit » / « free »",
      "prix à mesurer" in A.get("fr", "") and "price to be measured" in A.get("en", "")
      and "gratuit" not in A.get("fr", "") and "free" not in A.get("en", "").lower())
check("W4 les deux phrases neuves : une phrase FR = une traduction, l'anglais n'est pas le français recopié",
      all(len(PAR_FR.get(d.get("fr"), ())) == 1 and d.get("en") != d.get("fr") for d in (G, A)))
VIT = (RACINE / "frontend" / "vectorlab" / "js" / "mod-vitrail.js").read_text(encoding="utf-8")
fn = re.search(r"\n  function bulleIA\(\) \{\r?\n[\s\S]*?\r?\n  \}\r?\n", VIT)
check("W5 mod-vitrail.js : bulleIA() posée, le bouton IA l'appelle, plus de payant en dur hors d'elle",
      fn is not None and 'title="${bulleIA()}"' in VIT and VIT.count("bulleIA(") == 3
      and VIT.count('T("vectorlab.vitrail.ia_titre")') == 1 and 'T("vectorlab.vitrail.ia_titre")' in fn.group(0))
ROUTES = (RACINE / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8")
check("W6 le moteur du panneau est celui de la route : POST sans provider → dispo[0] ; GET …/moteurs : actif = cat[0]",
      'or dispo[0]' in ROUTES and '"actif": cat[0]["moteur"] if cat else None' in ROUTES
      and 'body: JSON.stringify({ prompt: q })' in VIT)
lit = re.search(r'fetch\("/api/vector/illustration/moteurs"\)[\s\S]{0,900}?\.catch', VIT)
check("W7 le panneau lit GET …/moteurs et retient le PREMIER (moteur + modèle par défaut)",
      lit is not None and "d.moteurs[0]" in lit.group(0) and ".defaut" in lit.group(0), lit and lit.group(0))
check("W7b l'arrivée des moteurs (lente : listes réseau) ne redessine PAS le panneau — une saisie en cours survit ; "
      "seule la bulle du bouton change (title, ou data-tip quand l'infobulle la montre)",
      lit is not None and "rendrePanneau" not in lit.group(0)
      and re.search(r'b\.setAttribute\(b\.dataset\.tip !== undefined \? "data-tip" : "title", bulleIA\(\)\)', lit.group(0))
      is not None, lit and lit.group(0))
check("W8 après un appel réussi, le moteur et le modèle RENDUS par la route remplacent ceux du chargement",
      re.search(r"if \(d\.provider\) iaMoteur = \{ moteur: d\.provider, defaut: d\.modele \|\| \"\" \};", VIT) is not None)
NODE = r"""
const fs=require("fs");const [src,ia,dico]=[process.argv[2],process.argv[3],JSON.parse(fs.readFileSync(process.argv[4],"utf8"))];
const out={};
for(const lang of ["fr","en"]){
 const T=(k,v)=>{const e=dico[k];if(!e)return "ABSENTE:"+k;let s=e[lang];return s.replace(/\{(\w+)\}/g,(m,n)=>v&&v[n]!=null?v[n]:m)};
 const bulleGenerer=new Function("T","nomMoteur",ia+";return bulleGenerer")(T,id=>id);
 out[lang]={};out[lang+"_ia"]={};
 for(const id of ["anthropic","openai","gemini","ollama","local:lmstudio","fl:deepseek","fl:groq","localx",""]){
  const iaMoteur=id?{moteur:id,defaut:"m1"}:null;
  out[lang][id||"inconnu"]=new Function("T","iaMoteur",src+";return bulleIA")(T,iaMoteur)();
  if(id)out[lang+"_ia"][id]=bulleGenerer(id);
 }
}
console.log(JSON.stringify(out));
"""
MODIA = (RACINE / "frontend" / "vectorlab" / "js" / "mod-ia.js").read_text(encoding="utf-8")
fia = re.search(r"\n  function bulleGenerer\(id\) \{\r?\n[\s\S]*?\r?\n  \}\r?\n", MODIA)
res = {}
if fn and fia:
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "h.js").write_text(NODE, encoding="utf-8")
        p = subprocess.run(["node", str(pathlib.Path(d) / "h.js"), fn.group(0), fia.group(0),
                            str(I18N / "vectorlab.json")], capture_output=True, text=True, encoding="utf-8")
        try: res = json.loads(p.stdout)
        except Exception: res = {"err": p.stderr[-400:]}
fr, en = res.get("fr", {}), res.get("en", {})
check("W9 (node) anthropic / openai / gemini, et un moteur encore inconnu : le texte d'avant, à l'identique",
      all(fr.get(i) == AVANT_FR and en.get(i) == AVANT_EN for i in ("anthropic", "openai", "gemini", "inconnu")),
      str(res)[:300])
check("W10 (node) ollama et local:<id> : gratuit, le moteur et son modèle nommés, aucun « PAYANT » / « PAID »",
      all("gratuit" in fr.get(i, "") and "PAYANT" not in fr.get(i, "") and "free" in en.get(i, "").lower()
          and "PAID" not in en.get(i, "") and (i + " · m1") in fr.get(i, "") and (i + " · m1") in en.get(i, "")
          for i in ("ollama", "local:lmstudio")), str(fr))
check("W11 (node) fl:<id> : prix à mesurer, jamais gratuit",
      all("prix à mesurer" in fr.get(i, "") and "gratuit" not in fr.get(i, "") and (i + " · m1") in fr.get(i, "")
          and "price to be measured" in en.get(i, "") and "free" not in en.get(i, "").lower()
          for i in ("fl:deepseek", "fl:groq")), str(fr))
check("W12 (node) un id « localx » (sans « : ») reste payant — pas de faux gratuit", fr.get("localx") == AVANT_FR,
      fr.get("localx"))
def classe(s):
    return "gratuit" if "gratuit" in s else ("mesurer" if "prix à mesurer" in s else "payant")
ia_fr = res.get("fr_ia", {})
check("W13 (node) même règle que bulleGenerer (dialogue IA) pour chaque moteur",
      ia_fr and all(classe(fr.get(i, "")) == classe(t) for i, t in ia_fr.items()),
      str({i: (classe(fr.get(i, "")), classe(t)) for i, t in ia_fr.items()}))
code, sortie = generateur("i18n_l6_generer.py")
check("W14 la table L6 est à jour (édition consignée en entrées S, pas à la main)", code == 0 and "à jour" in sortie,
      sortie[-400:])
SAISIE = RACINE / "scripts" / "i18n_l6" / "vitrailcout.py"
check("W15 le groupe de saisie vitrailcout.py consigne l'édition sur la BASE", SAISIE.exists()
      and "bulleIA" in SAISIE.read_text(encoding="utf-8"))

print("[R] Réglages › Fournisseurs par défaut : l'aide du rôle « Résumé des News »")
R = DICO.get("reglages.defauts.resume_aide", {})
check("R1 le FR cite les intégrés, un fournisseur libre et un serveur local",
      all(m in R.get("fr", "") for m in ("Anthropic", "OpenAI", "Gemini", "fournisseur libre", "serveur local")),
      R.get("fr"))
check("R2 l'EN aussi, avec les mots de l'écran (« free provider », « local server »)",
      all(m in R.get("en", "") for m in ("Anthropic", "OpenAI", "Gemini", "free provider", "local server")), R.get("en"))
check("R3 une phrase FR = une traduction ; l'ancienne phrase a disparu des dictionnaires",
      len(PAR_FR.get(R.get("fr"), ())) == 1
      and "Anthropic, OpenAI ou Gemini pour des résumés d'articles neutres" not in PAR_FR)
SUMM = (RACINE / "backend" / "app" / "services" / "summarizer.py").read_text(encoding="utf-8")
check("R4 le rôle accepte bien un fournisseur libre et un serveur local (summarizer : fl: / local:)",
      'provider.startswith(("fl:", "local:"))' in SUMM)
RC = (RACINE / "scripts" / "i18n_l1" / "reglages_comptes.py").read_text(encoding="utf-8")
check("R5 la saisie L1 porte la phrase (reglages_comptes.py), à la même position du bundle",
      re.search(r'L\(684158, "reglages\.defauts\.resume_aide", "' + re.escape(R.get("fr", "?")) + '"', RC) is not None)
code, sortie = generateur("i18n_l1_generer.py")
check("R6 la table L1 et reglages.json sont à jour (i18n_l1_generer --check)", code == 0, sortie[-400:])
ASSEMBLE = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("R7 le dictionnaire assemblé porte la phrase neuve, la copie dist est identique à l'octet",
      R.get("fr", "?").encode("utf-8") in ASSEMBLE
      and ASSEMBLE == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
