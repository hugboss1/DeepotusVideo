# -*- coding: utf-8 -*-
"""L'ecran News trie par le score (plan 2026-09-03 T6, tache #33 PR 2/2, 30/09/2026).

Banc-MIROIR : il lit le BUNDLE ECRIT (groupe P3nr du maillon montage), pas le patcher. Les ponts `__dzNewsRank` /
`__dzNewsFilter` / `__dzNewsListe` et le tri par le classement sont EXECUTES sous node avec un faux `fetch`.
Temoin positif : le bundle de la base (b8dae2f) a encore le tri par longueur de resume et aucun pont — les negations
du banc (« le tri par longueur a disparu », « pas de llm=true au chargement ») y sont mesurees vraies d'abord.
Decision de l'utilisateur : score GRATUIT par defaut ; l'IA seulement par le bouton « Classer avec l'IA ».
Run : & $PY tests/test_news_bundle.py   (depuis backend/)"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_RACINE = pathlib.Path(__file__).resolve().parents[2]
_BUNDLE = _RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BASE = "b8dae2f"

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


s = _BUNDLE.read_bytes().decode("utf-8")
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(_RACINE))
s0 = r0.stdout.decode("utf-8") if r0.returncode == 0 else ""
TRI_LONGUEUR = '(b.summary||"").length-(a.summary||"").length'
i_pm = s.find("function pm({variant:e,go:Go}){")
pm = s[i_pm:s.find("async function dzDelTemplate(", i_pm)]

print("\n[T] temoin : le bundle de la base")
check("T1 la base a le tri par longueur de resume, le libelle « By relevance » et le select de style mort", bool(s0)
      and TRI_LONGUEUR in s0 and '{value:"relevance",label:"By relevance"}' in s0 and 'const[sty,setSty]' in s0)
check("T2 la base n'a aucun pont News ni route de classement", s0 and "__dzNewsRank" not in s0 and "/api/news/rank" not in s0)

print("\n[A] le bundle ecrit")
check("A0 l'ecran News est trouve", i_pm > 0 and len(pm) > 5000, str(len(pm)))
check("A1 le tri par longueur de resume a disparu", TRI_LONGUEUR not in s)
check("A2 un seul appel a chaque route", s.count("/api/news/rank") == 1 and s.count("/api/news/filter") == 1,
      f'{s.count("/api/news/rank")} {s.count("/api/news/filter")}')
check("A3 les trois ponts definis une fois, poses AVANT l'ecran", all(s.count(f"function {f}(") == 1 and s.find(f"function {f}(") < i_pm
                                                                     for f in ("__dzNewsRank", "__dzNewsFilter", "__dzNewsListe")))
check("A4 au chargement le classement est GRATUIT : __dzNewsRank(brief,!1) ; !0 seulement dans rankIA",
      pm.count("__dzNewsRank(brief,!1)") == 2 and pm.count("__dzNewsRank(brief,!0)") == 1
      and pm.find("__dzNewsRank(brief,!0)") > pm.find("async function rankIA(") > 0, "")
check("A5 le bouton « Classer avec l'IA » appelle rankIA, porte un title qui dit « payant » et « plafond »",
      'onClick:rankIA' in pm and 'title:"Classer avec l’IA : payant, sous le plafond de dépense.' in pm)
check("A6 « Score du jour » remplace « By relevance » et devient le tri par defaut",
      '{value:"relevance",label:"Score du jour"}' in pm and 'label:"By relevance"' not in s
      and 'const[sort,setSort]=x.useState(__dzK("news.sort","relevance"));' in pm and 'useState("recent")' not in pm)   # t129 : le defaut passe par le conservateur
check("A7 le select de style mort est retire DES DEUX COTES (etat et JSX)", "sty" not in pm.replace("style", "").replace("Sty", "")
      and "setSty" not in pm and '["deep-sea","cinematic","glitch","documentary"]' not in pm)
check("A8 les items gardent published et doublons ; payload emporte id et published",
      'published:z.published||"",doublons:z.doublons||[]' in pm and 'link:i.link,id:i.id,source_id:i.source_id||"",published:i.published||""}))}' in pm)
check("A16 (tache #34) le sujet deja couvert est recopie du classement et montre en ambre, avec son titre au survol",
      'en_tete:m.en_tete,deja_couvert:m.deja_couvert,' in pm and 'i.deja_couvert?r.jsx("span",{title:"Sujet proche d\u2019un reel d\u00e9j\u00e0 lanc\u00e9 : "+i.deja_couvert,' in pm
      and 'children:"d\u00e9j\u00e0 couvert"' in pm)
check("A9 la carte montre score, motif, etoile de tete et origine IA", 'children:i.score_pourquoi' in pm
      and '(i.en_tete?"★ ":"")+i.score+"/100"' in pm and '"IA · "+i.score_origine' in pm)
check("A10 les ecartes : puce comptee, motifs au survol (span porteur du title : `te` ne le transmet pas)",
      'r.jsx("span",{title:ranked.ecartes.map(function(z){return z.title+" — "+z.motif}).join("\\n"),children:r.jsx(te,{tone:"amber",style:{whiteSpace:"nowrap"}' in pm
      and '" écartés ce jour"' in pm)
check("A11 le panneau du filtre : quatre champs, un bouton titre qui enregistre", all(f'fch("{k}"' in pm for k in
      ("mots_cles", "mots_noirs", "sources_noires", "fraicheur_h")) and 'title:"Enregistrer le filtre gratuit et reclasser",onClick:saveFilt' in pm)
check("A12 le brief remplace le style et se garde (localStorage, lecture/ecriture sous try)",
      'label:"Brief de campagne"' in pm and 'localStorage.getItem("dzNewsBrief")' in pm and 'localStorage.setItem("dzNewsBrief",brief)' in pm)
def _titre_du_bouton(gestion):
    i = pm.find(gestion)
    k = pm.rfind("r.jsx(K,{", 0, i)
    return i > 0 and k > 0 and i - k < 400 and "title:" in pm[k:i]
check("A13 E-12 : les trois boutons neufs (IA, repli, filtre) portent un title AVANT leur onClick",
      all(_titre_du_bouton(g) for g in ("onClick:rankIA", "onClick:function(){setPlie(!plie)}", "onClick:saveFilt")),
      str([_titre_du_bouton(g) for g in ("onClick:rankIA", "onClick:function(){setPlie(!plie)}", "onClick:saveFilt")]))
check("A15 la barre de la liste passe a la ligne et ses puces ne se coupent pas (mesure a l'ecran : grille 1462 px pour 1400)",
      'gap:10,flexWrap:"wrap",rowGap:6,background:"var(--bg-panel)"},children:[r.jsxs("span",{className:"display",style:{fontSize:14,color:"var(--ink-strong)",whiteSpace:"nowrap"}' in pm
      and 'r.jsxs(te,{tone:"cyan",style:{whiteSpace:"nowrap"},children:[sel.size," selected"]})' in pm)
check("A14 aucun window.prompt ni alert dans l'ecran", "window.prompt" not in pm and "alert(" not in pm)

print("\n[N] execution sous node")
node = shutil.which("node")
check("N0 node est present", bool(node))
if node:
    def fonc(nom):
        i = s.find(f"function {nom}(")
        prof, j = 0, s.find("{", i)
        for k in range(j, len(s)):
            prof += {"{": 1, "}": -1}.get(s[k], 0)
            if prof == 0:
                return s[i:k + 1]
    i4 = pm.find('if(sort==="relevance"&&ranked&&ranked.items){')
    tri = pm[i4:pm.find("if(plie)shown=shown.filter(function(z){return z.en_tete})}", i4) + len("if(plie)shown=shown.filter(function(z){return z.en_tete})}")]
    js = "\n".join([fonc("__dzNewsRank"), fonc("__dzNewsFilter"), fonc("__dzNewsListe"), r"""
var journal=[];
function rep(status,corps){return Promise.resolve({status:status,ok:status>=200&&status<300,json:function(){return Promise.resolve(corps)}})}
var suite=[];
globalThis.fetch=function(u,o){journal.push({u:u,o:o||null});return suite.shift()};
function tri(sort,ranked,plie,shown){""" + tri + r"""return shown}
(async function(){
 var out={};
 suite=[rep(200,{items:[{id:"a"}]})]; out.r1=await __dzNewsRank("crypto"); out.j1=journal.pop();
 suite=[rep(200,{items:[]})]; await __dzNewsRank("x",true); out.j2=journal.pop();
 suite=[rep(402,{detail:{}})]; out.r3=await __dzNewsRank("x",true);
 suite=[rep(500,{})]; out.r4=await __dzNewsRank("x");
 suite=[Promise.reject(new Error("reseau"))]; out.r5=await __dzNewsRank("x");
 suite=[rep(200,{fraicheur_h:48})]; out.f1=await __dzNewsFilter(); out.jf1=journal.pop();
 suite=[rep(200,{fraicheur_h:24})]; out.f2=await __dzNewsFilter({fraicheur_h:24}); out.jf2=journal.pop();
 out.l=__dzNewsListe(" solana, , bitcoin ,");
 var items=[{id:"x",title:"X"},{id:"a",title:"A"},{id:"b",title:"B"},{id:"c",title:"C"}];
 var rk={items:[{id:"b",score:80,score_pourquoi:"p",score_origine:"deterministe",en_tete:true},
               {id:"a",score:40,score_pourquoi:"q",score_origine:"deterministe",en_tete:false}]};
 out.t1=tri("relevance",rk,false,items.slice()).map(function(z){return z.id+":"+z.score});
 out.t2=tri("relevance",rk,true,items.slice()).map(function(z){return z.id});
 out.t3=tri("recent",rk,true,items.slice()).map(function(z){return z.id});
 out.t4=tri("relevance",null,true,items.slice()).map(function(z){return z.id});
 console.log(JSON.stringify(out));
})();
"""])
    d = tempfile.mkdtemp(prefix="dznewsb_")
    f = pathlib.Path(d, "t.mjs"); f.write_text(js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-800:])
    b1 = json.loads(((o.get("j1") or {}).get("o") or {}).get("body") or "{}")
    b2 = json.loads(((o.get("j2") or {}).get("o") or {}).get("body") or "{}")
    check("N1 par defaut : POST /api/news/rank avec llm:false", (o.get("j1") or {}).get("u") == "/api/news/rank"
          and o["j1"]["o"]["method"] == "POST" and b1 == {"brief": "crypto", "llm": False}, str(o.get("j1")))
    check("N2 temoin : llm demande -> llm:true", b2 == {"brief": "x", "llm": True}, str(b2))
    check("N3 un 402 (plafond refuse) rend {annule:true}", o.get("r3") == {"annule": True}, str(o.get("r3")))
    check("N4 erreur serveur ou reseau : null, pas d'exception", o.get("r4") is None and o.get("r5") is None and "r5" in o)
    check("N5 filtre : GET sans corps, puis PUT avec le patch", (o.get("jf1") or {}).get("o") is None
          and o.get("f1") == {"fraicheur_h": 48} and o["jf2"]["o"]["method"] == "PUT"
          and json.loads(o["jf2"]["o"]["body"]) == {"fraicheur_h": 24}, str(o.get("jf1")) + str(o.get("jf2")))
    check("N6 la liste saisie est decoupee et nettoyee", o.get("l") == ["solana", "bitcoin"], str(o.get("l")))
    check("N7 Score du jour : ordre du classement, ecartes caches, score recopie", o.get("t1") == ["b:80", "a:40"], str(o.get("t1")))
    check("N8 replie : seulement les articles en tete", o.get("t2") == ["b"], str(o.get("t2")))
    check("N9 « Most recent » : aucun tri ni masquage", o.get("t3") == ["x", "a", "b", "c"], str(o.get("t3")))
    check("N10 classement absent (serveur injoignable) : la liste reste entiere", o.get("t4") == ["x", "a", "b", "c"], str(o.get("t4")))

print("\n[C] la chaine du jour a l'ecran (tache #35 PR3, groupe P3nc)")
check("C1 temoin : la base (b8dae2f) n'a ni __dzNewsChaine ni la voix auto", "__dzNewsChaine" not in s0 and '{value:"auto"' not in s0)
check("C2 le panneau est defini une fois, le bouton « Chaine du jour » l'ouvre avec le brief et porte un title",
      s.count("function __dzNewsChaine(") == 1 and 'title:"Préparer le lot du jour (gratuit), le polir si besoin, le programmer avec son reel cartes",onClick:function(){__dzNewsChaine(brief)},children:"Chaîne du jour"})' in pm)
check("C3 « Send to Studio » reste", 'children:"Send to Studio"})' in pm)
check("C4 voix : « Auto » en tete du selecteur et par defaut ; auto n'envoie pas de voice_mode",
      '{value:"auto",label:"Auto (selon le sujet)"},{value:"oracle"' in pm and 'const[voice,setVoice]=x.useState(__dzK("news.voice","auto"));' in pm   # t129 : le defaut passe par le conservateur
      and 'voice_mode:voice==="auto"?void 0:voice,language:"EN"' in pm and 'useState("oracle")' not in pm)
check("C5 le motif de la voix s'affiche sous le script", ',script.voice_mode_auto?r.jsx("div",{style:{marginTop:6,fontSize:10.5,color:"var(--ink-soft)"},children:"Voix : "+script.voice_mode_auto+" — "+(script.voice_mode_reason||"")' in pm)
check("C6 la tendance est recopiee du classement et montree en vert sur la carte",
      'deja_couvert:m.deja_couvert,tendance:m.tendance,tendance_sources:m.tendance_sources})' in pm
      and 'i.tendance?r.jsx("span",{title:"Cité par "+i.tendance_sources+" médias distincts le même jour",style:{color:"var(--green)"}' in pm)
if node:
    fns = [fonc(n) for n in ("__dzSchedApi", "__dzSchedPanel", "__dzSchedBtn", "__dzSchedRecharger", "__dzSchedOut", "__dzSchedTexte",
                             "__dzSchedChamp", "__dzNewsSel", "__dzNewsChaine")]
    js = "\n".join(fns + [r"""
function El(t){this.tagName=t;this.children=[];this.style={};this._t="";this.value="";this.title="";this.disabled=false;this._ev={}}
Object.defineProperty(El.prototype,"textContent",{set:function(v){this._t=String(v);if(v==="")this.children=[]},get:function(){return this._t}});
El.prototype.appendChild=function(c){this.children.push(c);c.parentNode=this;return c};
El.prototype.addEventListener=function(t,f){this._ev[t]=f};El.prototype.remove=function(){};
Object.defineProperty(El.prototype,"innerHTML",{set:function(v){this.children=[]},get:function(){return ""}});
globalThis.document={createElement:function(t){return new El(t)},getElementById:function(){return null},body:new El("body"),
  addEventListener:function(){},removeEventListener:function(){}};
globalThis.window={dispatchEvent:function(){globalThis.recharge=(globalThis.recharge||0)+1}};globalThis.CustomEvent=function(n){this.n=n};
function tous(e,out){out=out||[];out.push(e);(e.children||[]).forEach(function(c){tous(c,out)});return out}
function rep(st,j){return Promise.resolve({status:st,ok:st>=200&&st<300,json:function(){return Promise.resolve(j)}})}
var appels=[],reponses={};
globalThis.fetch=function(u,o){appels.push({u:u,o:o||null});var f=reponses[u.split("?")[0]];return f?f(u,o):rep(404,{detail:"?"})};
var attendre=function(){return new Promise(function(r){setTimeout(r,20)})};
(async function(){
 var out={};
 reponses["/api/news/forms"]=function(){return rep(200,{forms:[{id:"cartes",label:"Cartes",disponible:true},{id:"avatar",label:"Avatar",disponible:false}]})};
 reponses["/api/news/chain/preview"]=function(){return rep(200,{articles:[{title:"Solana record",score:64,en_tete:true,tendance:true,tendance_sources:3}],
   script:"Brouillon.",caption:"Legende",creneau:"2026-10-04T17:30:00+00:00",forme:"cartes",cout:{total_usd:0},voice_mode:"alpha",voice_mode_reason:"mots du sujet : crash",poli:false})};
 __dzNewsChaine("crypto Solana");await attendre();
 var el=tous(document.body),btn=function(t){return el.filter(function(e){return e.tagName==="button"&&e.textContent===t})[0]};
 var sel=el.filter(function(e){return e.tagName==="select"});
 out.options=sel[0].children.map(function(c){return c.value+":"+c.textContent});
 out.boutons=el.filter(function(e){return e.tagName==="button"}).map(function(b){return [b.textContent,!!b.title,b.style.display||""]});
 sel[0].value="avatar";btn("Préparer (gratuit)").onclick();await attendre();
 var prev=appels.filter(function(a){return a.u==="/api/news/chain/preview"})[0];out.prev=JSON.parse(prev.o.body);
 el=tous(document.body);var champs=el.filter(function(e){return e.tagName==="textarea"||e.tagName==="input"});
 out.champs=champs.map(function(c){return c.title+"="+c.value});
 out.pres=el.filter(function(e){return e.tagName==="pre"}).map(function(p){return p.textContent});
 out.visibles=[btn("Polir avec l’IA").style.display,btn("Programmer le lot").style.display];
 var script=champs.filter(function(c){return c.title==="Script (brouillon)"})[0];script.value="Edite a la main.";
 reponses["/api/news/chain/polish"]=function(){return rep(402,{detail:{dz_plafond:{}}})};
 btn("Polir avec l’IA").onclick();await attendre();
 out.apres402=script.value;out.msg402=tous(document.body).filter(function(e){return e.tagName==="pre"}).map(function(p){return p.textContent}).join("|");
 reponses["/api/news/chain/polish"]=function(){return rep(200,{script:"Poli.",poli:true,fournisseur:"anthropic"})};
 btn("Polir avec l’IA").onclick();await attendre();out.apresPoli=script.value;
 script.value="Edite a la main.";
 reponses["/api/news/chain/commit"]=function(){return rep(200,{post_id:"p123456789",job_id:"j1",message:"ok"})};
 btn("Programmer le lot").onclick();await attendre();
 var com=appels.filter(function(a){return a.u==="/api/news/chain/commit"})[0];out.commit=JSON.parse(com.o.body);
 out.progDesactive=btn("Programmer le lot").disabled;out.recharge=globalThis.recharge||0;
 reponses["/api/news/trends"]=function(){return rep(200,{tendances:[],x:{posts:7,quota:"17/100",restant_jour:2,motif:""}})};
 btn("Signal X").onclick();await attendre();out.x=appels.filter(function(a){return a.u.indexOf("/api/news/trends")===0}).map(function(a){return a.u});
 out.msgX=tous(document.body).filter(function(e){return e.tagName==="pre"}).map(function(p){return p.textContent}).join("|");
 console.log(JSON.stringify(out));
})();
"""])
    f = pathlib.Path(tempfile.mkdtemp(prefix="dznewsc_"), "c.mjs"); f.write_text(js, encoding="utf-8")
    p = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        o = {}
        print(p.stdout[-800:], p.stderr[-1500:])
    check("C7 les formes viennent du serveur, une forme sans cle le dit", o.get("options") == ["cartes:Cartes", "avatar:Avatar (clé absente)"], str(o.get("options")))
    b = {x[0]: x for x in o.get("boutons", [])}
    check("C8 quatre boutons, tous avec un title ; Polir et Programmer caches avant la preparation",
          set(b) >= {"Préparer (gratuit)", "Polir avec l’IA", "Programmer le lot", "Signal X"} and all(x[1] for x in o.get("boutons", []))
          and b.get("Polir avec l’IA", [0, 0, ""])[2] == "none" and b.get("Programmer le lot", [0, 0, ""])[2] == "none", str(o.get("boutons")))
    check("C9 preparer envoie le brief, la forme CHOISIE, 3 articles et le canal", o.get("prev") == {"brief": "crypto Solana", "forme": "avatar",
          "articles_max": 3, "language": "EN", "canal": "x"}, str(o.get("prev")))
    check("C10 le lot s'affiche : articles (etoile, score, tendance), script, legende, creneau editables ; voix et cout dits",
          any("★ 64/100 Solana record — tendance (3 médias)" in t for t in o.get("pres", []))
          and "Script (brouillon)=Brouillon." in o.get("champs", []) and "Légende=Legende" in o.get("champs", [])
          and "Créneau (ISO, UTC)=2026-10-04T17:30:00+00:00" in o.get("champs", [])
          and any("Voix : alpha" in t and "0.00 $" in t for t in o.get("pres", [])) and o.get("visibles") == ["", ""], str(o.get("pres")))
    check("C11 polir refuse par le plafond (402) : le brouillon edite reste, et c'est dit", o.get("apres402") == "Edite a la main."
          and "annulé (plafond" in o.get("msg402", ""), o.get("msg402", "")[:200])
    check("C12 polir accepte : le script est remplace", o.get("apresPoli") == "Poli.")
    lot = (o.get("commit") or {}).get("lot") or {}
    check("C13 programmer envoie le script EDITE, la legende, le creneau et les canaux ; bouton desactive ; Scheduler recharge",
          lot.get("script") == "Edite a la main." and lot.get("caption") == "Legende" and lot.get("creneau") == "2026-10-04T17:30:00+00:00"
          and (o.get("commit") or {}).get("channels") == ["x"] and o.get("progDesactive") is True and o.get("recharge", 0) >= 1, str(o.get("commit"))[:300])
    check("C14 signal X : une lecture sur le brief encode, quota et reste du jour dits", o.get("x") == ["/api/news/trends?x_query=crypto%20Solana"]
          and "7 posts" in o.get("msgX", "") and "17/100" in o.get("msgX", ""), str(o.get("x")) + o.get("msgX", "")[-120:])

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
