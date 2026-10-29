# -*- coding: utf-8 -*-
"""t375 (29/10/2026, lot B « News », plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md)
— banc de la puce « N écartés ce jour » de l'écran News (maillon de queue scripts/patch_bundle_dzecartes.py).
Avant : le survol de la puce ouvrait une bulle `title` GÉANTE, un titre d'article par ligne (souvent des centaines
d'articles hors fenêtre de fraîcheur).
  1. le survol ne montre plus qu'un RÉSUMÉ court : le total, puis un compte par motif (dans l'ordre décroissant), puis
     l'indication « Tout afficher » — exécuté sous node sur 300 écartés ;
  2. la liste complète n'apparaît que par « Tout afficher » : un déroulé natif (<details>, aucun useState neuf),
     titre et motif par ligne, panneau borné en hauteur et défilant, aux jetons de la charte (aucun rayon, aucune
     couleur en dur) ;
  3. textes neufs par dzT, en FR et en EN, dans news_survol.json (news.json est généré par L2) et le dictionnaire assemblé (copies identiques) ;
  4. le maillon : appliqué (--check), inverse avant_dzecartes exact, appelé EN TÊTE de avant_dzcurseur, hors couche.
Run (depuis backend/) : & $PY tests/test_news_ecartes_ecran.py"""
import json, pathlib, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
REPO = _ICI.parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(_ICI))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


FRONT = REPO / "frontend"
B = FRONT / "dist" / "assets" / "index-BEOJX8L5.js"
bundle = B.read_bytes().decode("utf-8")
i_pm = bundle.find("function pm({variant:e,go:Go}){")
pm = bundle[i_pm:bundle.find("async function dzDelTemplate(", i_pm)] if i_pm >= 0 else ""
i_puce = pm.find('dzT("news.liste.ecartes",{n:ranked.ecartes.length})')
zone = pm[max(0, i_puce - 600):i_puce + 2200] if i_puce >= 0 else ""

print("[1] le survol : un résumé court")
check("1.0 l'écran News et sa puce des écartés sont trouvés", len(pm) > 5000 and i_puce > 0)
check("1.1 plus aucune liste des titres dans la bulle de survol",
      "title:ranked.ecartes.map(" not in bundle and not re.search(r'title:[^,]{0,80}ecartes\.map\(function\(z\)\{return z\.title', bundle))
check("1.2 la bulle de la puce est le résumé", 'r.jsx("span",{title:dzNewsEcartesResume(ranked.ecartes),' in zone)
m = re.search(r"function dzNewsEcartesResume\(l\)\{.*?\}(?=function pm\(\{variant:e,go:Go\}\)\{)", bundle, re.S)
check("1.3 la fonction du résumé est définie une fois, AVANT l'écran", m is not None
      and bundle.count("function dzNewsEcartesResume(") == 1 and bundle.find("function dzNewsEcartesResume(") < i_pm)
NODE = shutil.which("node")
if m and NODE:
    prog = ("var dzT=function(k,p){return k+(p?JSON.stringify(p):'')};" + m.group(0) + "\n"
            "var l=[];for(var i=0;i<300;i++)l.push({id:'a'+i,title:'Titre très long numéro '+i,"
            "motif:i<280?'hors fenêtre de fraîcheur':(i<295?'hors mots-clés':'mot sur liste noire')});"
            "process.stdout.write(JSON.stringify({r:dzNewsEcartesResume(l),v:dzNewsEcartesResume([])}))")
    r = subprocess.run([NODE, "-e", prog], capture_output=True, text=True, encoding="utf-8")
    try:
        o = json.loads(r.stdout)
    except ValueError:
        o = {}
    lignes = (o.get("r") or "").split("\n")
    check("1.4 exécuté sur 300 écartés : 5 lignes (total, 3 motifs, indication), aucun titre d'article", len(lignes) == 5
          and "Titre très long" not in o.get("r", ""), (r.stdout + r.stderr)[-400:])
    check("1.5 1re ligne : le total", lignes[0] == 'news.liste.ecartes_resume{"n":300}', lignes[:1])
    check("1.6 puis un compte par motif, du plus fréquent au plus rare",
          lignes[1:4] == ["280 · hors fenêtre de fraîcheur", "15 · hors mots-clés", "5 · mot sur liste noire"], lignes)
    check("1.7 dernière ligne : l'indication « Tout afficher »", lignes[-1] == "news.liste.ecartes_tout_aide", lignes[-1:])
    check("1.8 une liste vide ne casse rien", (o.get("v") or "").startswith('news.liste.ecartes_resume{"n":0}'))
else:
    check("1.4-1.8 node et la fonction sont disponibles", False, f"node={NODE} fonction={m is not None}")

print("\n[2] « Tout afficher » : la liste complète, sur demande")
d = zone[zone.find('r.jsxs("details"'):] if 'r.jsxs("details"' in zone else ""
check("2.1 un déroulé natif suit la puce (aucun useState neuf)", bool(d) and "x.useState(" not in zone)
check("2.2 son bouton dit « Tout afficher » (dzT)", 'r.jsx("summary",' in d[:400]
      and 'dzT("news.liste.ecartes_tout")' in d[:700])
check("2.3 la liste rend, par écarté, son titre et son motif (clé = id)",
      "ranked.ecartes.map(function(z){" in d and "children:z.title" in d and "children:z.motif" in d and "},z.id)" in d)
check("2.4 panneau borné en hauteur, défilant, au-dessus du contenu",
      'maxHeight:"50vh"' in d and 'overflow:"auto"' in d and 'position:"absolute"' in d and "zIndex:" in d)
check("2.5 liste accessible (role list / listitem)", 'role:"list"' in d and 'role:"listitem"' in d)
fin = d[:d.find("},z.id)})})]})") + 14] if "},z.id)})})]})" in d else d[:2000]
check("2.6 charte : aucun rayon, aucune couleur en dur (jetons var(--…))",
      "borderRadius" not in fin and not re.search(r"#[0-9a-fA-F]{3,6}\b|rgba?\(", fin)
      and "var(--bg-panel)" in fin and "var(--stroke" in fin, fin[:300])

print("\n[3] les textes, en FR et en EN")
news = json.loads((FRONT / "shared" / "i18n" / "news_survol.json").read_text(encoding="utf-8"))  # news.json est généré par L2
CLES = {"news.liste.ecartes_resume": ("{n}", "{n}"), "news.liste.ecartes_tout": ("Tout afficher", "List all"),
        "news.liste.ecartes_tout_aide": ("Tout afficher", "List all")}
for k, (fr, en) in CLES.items():
    v = news.get(k) or {}
    check(f"3.1 {k} : FR et EN présents et distincts", fr in v.get("fr", "") and en in v.get("en", "")
          and v.get("fr") != v.get("en"), v)
dico = (FRONT / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
check("3.2 le dictionnaire assemblé porte les trois clés, copie dist identique",
      all(f'"{k}"' in dico for k in CLES)
      and (FRONT / "dist" / "shared" / "dz-i18n-dico.js").read_bytes() == (FRONT / "shared" / "dz-i18n-dico.js").read_bytes())
import _i18n_l1_aide as AIDE
_res = AIDE.DICO.get("news.liste.ecartes_resume") or {}
check("3.3 rendu FR / EN du résumé", (_res.get("fr") or "").replace("{n}", "42") == "Écartés par le filtre : 42"
      and (_res.get("en") or "").replace("{n}", "42") == "Dropped by the filter: 42", _res)

print("\n[4] le maillon de queue")
r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzecartes.py"), "--check"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   env=dict(__import__("os").environ, PYTHONIOENCODING="utf-8"))
check("4.1 le maillon est appliqué (--check)", r.returncode == 0 and "déjà appliqué" in r.stdout, (r.stdout + r.stderr)[-300:])
try:
    import patch_bundle_dzecartes as M
except ImportError:
    M = None
avant = AIDE.avant_dzecartes(bundle) if hasattr(AIDE, "avant_dzecartes") else bundle
check("4.2 l'inverse avant_dzecartes défait le maillon, et le rejouer redonne le bundle à l'octet",
      M is not None and M.MARKER not in avant and "title:ranked.ecartes.map(" in avant
      and M.appliquer(avant) == (AIDE.avant_dzpose(bundle) if hasattr(AIDE, "avant_dzpose") else bundle))   # t376 : dzpose suit dzecartes
src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
_cur = src_aide[src_aide.index("def avant_dzcurseur("):]
_cur = _cur[:_cur.index("\ndef ", 5)]
check("4.3 avant_dzcurseur défait d'abord dzecartes (maillon posé après lui)", "bundle = avant_dzecartes(bundle)" in _cur)
check("4.4 aucune paire dans une couche __DZ_*_BEGIN__", M is not None and all(M.hors_couche(bundle, z) for _a, z in M.PAIRES))
check("4.5 le maillon suit dzcurseur (sonde de son marqueur)", M is not None
      and any(j == "/*dzcurseur*/" for _t, j, _n in M.SONDE_AMONT))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
