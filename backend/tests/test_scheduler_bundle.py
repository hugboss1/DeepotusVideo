# -*- coding: utf-8 -*-
"""L'écran du Scheduler (plan scheduler T11 — tâche #31, 30/09/2026). Banc-miroir : on lit le BUNDLE livré (jamais le
patcher qui prétend l'écrire) et on EXÉCUTE sous node la logique de connexion (faux fetch, faux window).

Écarts au plan du 03/09, tous mesurés sur le bundle d'aujourd'hui : pas de maillon `scheduler` (les sections vivent dans
le maillon montage, groupe P3sc, comme les écrans des Réglages) ; TikTok se connecte par OAuth loopback (plus de « coller
le code », plus de window.prompt — le bundle n'en a plus aucun) ; « Connected accounts » (Tm) passe YouTube et Instagram
en automatique et testables, ajoute TikTok, et gagne un bouton « Connecter » ; chaque bouton neuf porte un title (E-12).
Run : & $PY tests/test_scheduler_bundle.py   (depuis backend/)"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _i18n_l1_aide as AIDE  # noqa: E402  (t141 : dzT sous node, clés des libellés traduits)
# t141 : le prélude dans sa propre portée — son `var window` ne doit pas masquer le globalThis.window du harnais ;
# dzT est publié sur globalThis par le prélude et garde SON window (le dictionnaire)
PRELUDE = "(function(){\n" + AIDE.PRELUDE_DZT + "\n})();\n"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


R = pathlib.Path(__file__).resolve().parents[2]
B = R / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
s = B.read_text("utf-8")
vb = subprocess.run(["git", "show", "23b20bc:frontend/dist/assets/index-BEOJX8L5.js"], cwd=R, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 23b20bc")
check("0.1 TÉMOIN : pas d'écran Scheduler neuf, pas de TikTok dans les canaux", vb and "__dzSchedPanel" not in vb and 'tiktok:{id:"tiktok"' not in vb)

print("\n[1] les panneaux DOM et l'en-tête du Scheduler")
for f in ("__dzSchedApi", "__dzSchedPanel", "__dzSchedBtn", "__dzSchedConnect", "__dzSchedComptes", "__dzSchedValider",
          "__dzSchedCreneaux", "__dzSchedAnalytics"):
    check(f"1.{f} défini une fois", s.count(f"function {f}(") == 1, str(s.count(f"function {f}(")))
ent = s[s.find('children:"New post"})'):s.find('children:"New post"})') + 1400]
boutons = [("__dzSchedComptes()", "Comptes"), ("__dzSchedValider()", "Valider la semaine"),
           ("__dzSchedCreneaux()", "Créneaux"), ("__dzSchedAnalytics()", "Analytics")]
check("1.9 l'en-tête porte les quatre boutons, chacun avec son title (E-12)",
      all(f"onClick:function(){{{fn}}},children:\"{lib}\"" in ent for fn, lib in boutons) and ent.count("title:") >= 4
      and s.count('children:"New post"})') == 1, ent[:300])
for u in ('"/schedule/validate"', '"/schedule/slots"', '"/schedule/quotas"', '"/schedule/analytics?days=28"',
          '"/schedule/analytics/refresh"', '"/schedule/slots/suggest?tz_offset_minutes="', '"/api/oauth/"'):
    check(f"1.route {u}", u in s)
check("1.10 plus AUCUN window.prompt dans le bundle (dialogue maison), ni route « code collé »",
      "window.prompt(" not in s and "/oauth/tiktok/exchange" not in s)
helpers = s[s.find("function __dzSchedApi("):s.find("function __dzSendSched")]
check("1.11 les boutons DOM des panneaux portent un title", helpers.count("__dzSchedBtn(") >= 7
      and "b.title=" in helpers)
check("1.12 un panneau se ferme par Échap, et l'écouteur est retiré à CHAQUE fermeture (bouton, clic dehors, Échap)",
      'document.addEventListener("keydown",esc)' in helpers and 'document.removeEventListener("keydown",esc)' in helpers
      and "if(e.target===h)fermer()" in helpers and ',fermer);' in helpers)

print("\n[2] Connected accounts (Tm)")
tm = s[s.find("function Tm("):s.find("const _t={")]
yt = tm[tm.find('{k:"youtube"'):tm.find('{k:"instagram"')]
ig = tm[tm.find('{k:"instagram"'):tm.find('{k:"tiktok"')]
tk = tm[tm.find('{k:"tiktok"'):tm.find("}];function g(k)")]
check("2.1 YouTube : automatique, testable, état lu dans /health, bouton Connecter", 'auto:!0,testable:!0,connect:"youtube"' in yt
      and "f.youtube_enabled" in yt and "Assisted publishing" not in yt, yt[:300])
check("2.2 Instagram : automatique, testable, état lu dans /health", "auto:!0,testable:!0" in ig and "f.instagram_enabled" in ig
      and "Meta app review" not in ig, ig[:300])
check("2.3 TikTok : entrée neuve, ses quatre clés, connexion OAuth, et le privé sans audit est DIT",
      'connect:"tiktok"' in tk and "f.tiktok_enabled" in tk
      and all(f'k:"{k}"' in tk for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN", "TIKTOK_AUDITED"))
      # t141 (08/10) : la note passe par dzT("reglages.comptes.tiktok_note") ; c'est son français qui DIT le privé
      and 'note:dzT("reglages.comptes.tiktok_note")' in tk and "PRIVÉ" in AIDE.fr("reglages.comptes.tiktok_note"), tk[:300])
check("2.4 le bouton Connecter : à côté du test, seulement pour les canaux OAuth, message dans la ligne du canal",
      tm.count("k.connect&&r.jsx(K,{") == 1 and "__dzSchedConnect(k.connect," in tm and "u(p=>({...p,[k.k]:M}))" in tm
      # t141 (08/10) : le title passe par dzT ; sa clé rend le français d'avant
      and tm.count('title:dzT("reglages.comptes.connecter_titre",{nom:k.label})') == 1
      and AIDE.fr("reglages.comptes.connecter_titre", nom="TikTok").startswith("Ouvrir le consentement TikTok"))

print("\n[3] TikTok dans le Scheduler")
check("3.1 la table des canaux (sélection, aperçus) connaît TikTok", s.count('tiktok:{id:"tiktok",label:"TikTok",icon:"channelTiktok"') == 1)
check("3.2 son icône existe (channelTiktok) : table, carte d'icônes, Distribution, Connected accounts",
      s.count("channelTiktok:r.jsx(") == 1 and s.count('icon:"channelTiktok"') == 3, str(s.count('icon:"channelTiktok"')))
check("3.3 l'écran Distribution affiche TikTok, connecté d'après /health", '{id:"tiktok",label:"TikTok"' in s
      and "connected:!!(f&&f.tiktok_enabled)" in s)

print("\n[4] la logique de connexion, EXÉCUTÉE (node)")
_n = shutil.which("node")
js = helpers + r"""
var sortie = [];
function lancer(reponse, rappel) {
  var ouverte = {closed:false, location:{href:""}, close:function(){this.closed=true}};
  globalThis.window = {open:function(u){ouverte.url0 = u; return ouverte}};
  globalThis.fetch = function(u, o){ ouverte.fetched = u; ouverte.redirect = o && o.redirect; return Promise.resolve(reponse) };
  __dzSchedConnect("youtube", function(m){ rappel(ouverte, m) });
}
lancer({type:"opaqueredirect", status:0}, function(w, m){
  sortie.push({cas:"ok", fetched:w.fetched, redirect:w.redirect, href:w.location.href, closed:w.closed, m:m});
  lancer({type:"basic", status:409, json:function(){return Promise.resolve({detail:"Coffre verrouillé : ouvrez-le"})}}, function(w2, m2){
    sortie.push({cas:"409", href:w2.location.href, closed:w2.closed, m:m2});
    globalThis.fetch = function(){ return Promise.resolve({ok:false, status:400, json:function(){return Promise.resolve({detail:"mauvais"})}}) };
    __dzSchedApi("POST","/schedule/validate",{}).then(function(){ sortie.push({cas:"api", m:"PAS D'ERREUR"}); fin() },
      function(e){ sortie.push({cas:"api", m:e.message}); fin() });
  });
});
function fin(){ process.stdout.write(JSON.stringify(sortie)) }
"""
res = None
if _n and helpers:
    tmp = pathlib.Path(tempfile.mkdtemp()) / "c.js"
    tmp.write_text(PRELUDE + "var document={};function __dzToast(){}\n" + js, "utf-8")
    p = subprocess.run([_n, str(tmp)], capture_output=True, text=True, encoding="utf-8")
    try:
        res = json.loads(p.stdout)
    except ValueError:
        res = None
    if res is None:
        print(p.stderr[-400:])
c = {r["cas"]: r for r in (res or [])}
check("4.1 route prête (redirection) : l'onglet ouvert d'avance part vers /api/oauth/youtube/start, message OK",
      c.get("ok", {}).get("href") == "/api/oauth/youtube/start" and c["ok"].get("redirect") == "manual"
      and c["ok"].get("fetched") == "/api/oauth/youtube/start" and not c["ok"].get("closed") and c["ok"]["m"].startswith("OK"), str(c.get("ok")))
check("4.2 route refusée (409 coffre fermé) : l'onglet est refermé, la raison du serveur est dite",
      c.get("409", {}).get("closed") is True and not c["409"].get("href") and "Coffre verrouillé" in c["409"]["m"]
      and c["409"]["m"].startswith("Échec"), str(c.get("409")))
check("4.3 __dzSchedApi : un refus du serveur devient une erreur portant son detail", c.get("api", {}).get("m") == "mauvais", str(c.get("api")))

print("\n[6] lot 2 (tâche #32 PR4) : campagne, séries, recyclage, suite de fil")
for f in ("__dzSchedBrief", "__dzSchedSeries", "__dzSchedRecycler", "__dzSchedCampagne", "__dzSchedSuite", "__dzSchedChamp"):
    check(f"6.{f} défini une fois", s.count(f"function {f}(") == 1, str(s.count(f"function {f}(")))
helpers2 = s[s.find("function __dzSchedApi("):s.find("function __dzSendSched")]
for u in ('"/marketing/brief"', '"/schedule/series"', '"/schedule/series/"+x.id+"/materialize"', '"/schedule/series/"+x.id',
          '"/schedule/recycle/suggest?days=90&limit=5"', '"/schedule/recycle"', '"/schedule/"+id+"/thread"'):
    check(f"6.route {u}", u in helpers2)
ent2 = s[s.find('children:"New post"})'):s.find('children:"New post"})') + 2000]
check("6.10 l'en-tête gagne « Campagne », avec son title", 'onClick:function(){__dzSchedCampagne()},children:"Campagne"})' in ent2
      and 'icon:"book",title:' in ent2)
ins = s[s.find('onClick:P,children:"Duplicate to next day"})') - 50:s.find('onClick:P,children:"Duplicate to next day"})') + 600]
check("6.11 l'inspecteur gagne « Suite (fil X) » — seulement pour un post sur X, avec son title",
      '(e.channels||[]).indexOf("x")>=0&&r.jsx(K,{' in ins and "__dzSchedSuite(e.id)" in ins and 'children:"Suite (fil X)"' in ins
      and 'title:"Écrire la suite de ce post' in ins
      and s.count('children:"Suite (fil X)"') == 1, ins[:300])
check("6.12 toujours AUCUN window.prompt ni window.alert dans le neuf (formulaires dans les panneaux)",
      "window.prompt(" not in s and "window.alert(" not in helpers2)
check("6.13 le menu de libsend est RÉUTILISÉ pour Campagne, pas recopié", s.count("function __dzSendMenu(") == 1
      and "__dzSendMenu([" in helpers2)
check("6.14 la série se crée par un FORMULAIRE (nom, jours, heure, canaux, gabarit)", all(x in helpers2 for x in
      ('"Nom de la s\\u00e9rie"', '"Jours (0=lundi \\u2026 6=dimanche)"', '"Heure locale (HH:MM)"', '"Canaux (virgules)"')))
check("6.15 le recyclage ne demande JAMAIS le LLM payant depuis l'écran (pas de llm=true)", "llm=true" not in helpers2)
lm = s[s.find("function Lm("):s.find("function Lm(") + 3000]
check("6.17 le Scheduler RECHARGE sa liste sur deepotus:schedule-reload (reloadPosts), écouteur retiré au démontage",
      'window.addEventListener("deepotus:schedule-reload",R)' in lm and 'window.removeEventListener("deepotus:schedule-reload",R)' in lm
      and "function R(){o&&o()}" in lm and "reloadPosts:o" in lm)
check("6.18 chaque action qui crée ou change des posts demande ce rechargement (valider, poser, proposer, suite)",
      helpers2.count("__dzSchedRecharger();") == 4 and "rouvrez la semaine" not in helpers2, str(helpers2.count("__dzSchedRecharger();")))
js2 = helpers2 + r"""
var vu = null;
globalThis.__dzSendMenu = function(items, titre){ vu = {titre: titre, lbls: items.map(function(i){return i.lbl}),
  fns: items.map(function(i){return i.fn === __dzSchedBrief ? "brief" : i.fn === __dzSchedSeries ? "series" : i.fn === __dzSchedRecycler ? "recycler" : "?"})} };
__dzSchedCampagne();
process.stdout.write(JSON.stringify(vu));
"""
res2 = None
if _n and helpers2:
    tmp2 = pathlib.Path(tempfile.mkdtemp()) / "m.js"
    tmp2.write_text("var document={};function __dzToast(){}\n" + js2, "utf-8")
    p2 = subprocess.run([_n, str(tmp2)], capture_output=True, text=True, encoding="utf-8")
    try:
        res2 = json.loads(p2.stdout)
    except ValueError:
        print(p2.stderr[-300:])
check("6.16 Campagne ouvre le menu à trois entrées, chacune branchée sur SON panneau (exécuté sous node)",
      res2 is not None and res2.get("fns") == ["brief", "series", "recycler"] and len(res2.get("lbls", [])) == 3, str(res2))

print("\n[5] le reste")
_nc = subprocess.run([_n, "--check", str(B)], capture_output=True, text=True) if _n else None
check("5.1 node --check du bundle entier", _nc is not None and _nc.returncode == 0, (_nc.stderr[-200:] if _nc else ""))
from app.services import plan_schema                               # noqa: E402
check("5.2 le planificateur peut proposer TikTok (plan_schema), maintenant que l'écran le connaît",
      "tiktok" in plan_schema._CHANNELS and '"tiktok"' in plan_schema.system_prompt(7, 1, "FR")
      and plan_schema.clean_posts([{"title": "t", "channels": ["tiktok", "myspace"]}], 7)[0]["channels"] == ["tiktok"],
      str(plan_schema._CHANNELS))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
