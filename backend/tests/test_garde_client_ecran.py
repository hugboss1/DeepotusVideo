# -*- coding: utf-8 -*-
"""t309 tâche 4 (26/10/2026) — le Planificateur et les règles du CLIENT : les refus 409 se voient, l'état « à valider »
a un libellé, programmer au nom d'un client demande une confirmation nominative.
Plan docs/superpowers/plans/2026-10-26-t309-securites-client.md (tâche 4), spec 2026-10-25-boite-a-outils-design.md §5.5.
La logique vit dans frontend/shared/dz-garde-client.js (window.__dzGardeClient) ; le maillon de QUEUE
scripts/patch_bundle_dzgardeclient.py (APRÈS dzcanauxpre) la branche, toutes ses paires HORS de tout bloc de couche :
  G1 `D.updateScheduledPost` : délègue à window.__dzGardeClient.patch(id, corps, envoyer) quand le script est là, le
     code d'origine sinon (inchangé) ;
  G2 Planificateur `Lm` : un x.useEffect (aucun x.useState) écoute « deepotus:schedule-recharger » et appelle reloadPosts ;
  G3 « a_valider » : couleur Rm ambre comme « ready », pastille de l'inspecteur ambre avec dzT(scheduler.etat.a_valider).
Son inverse `avant_dzgardeclient` (backend/tests/_i18n_l1_aide.py) est appelé EN TÊTE de `avant_dzcanauxpre`.
[M] le maillon   marqueur x1, aucun .bak, --check « déjà appliqué », ancres uniques vues d'avant, hors couche, épingles,
                 octets/CRLF, node --check, aller-retour à l'octet (empreinte de la base), chaîne inverse ;
[F] le script    copie dist identique, balise après dz-espace-assistant.js ; sous node (faux fetch, faux dialogue) :
                 409 confirmation -> dialogue qui nomme le client et ses canaux ; oui -> second PATCH avec confirme_client ;
                 non -> rechargement et null ; 409 a_valider / consentement -> informer(message) + rechargement ; 200 -> json
                 (et rechargement si le serveur a rendu un autre état que celui demandé) ; autre erreur -> null ;
[G] le livré     G1 extraite du bundle sous node : délègue quand __dzGardeClient existe (envoyer = le PATCH d'origine),
                 garde l'ancien comportement sinon ; G2 extraite : l'écouteur appelle reloadPosts et se retire ; G3 (pastille sous node) ;
[K] textes       clés FR et EN mot pour mot, assemblées, shared == dist.
Aucun réseau. Run (depuis backend/) : & $PY tests/test_garde_client_ecran.py"""
import hashlib, json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import _i18n_l1_aide as AIDE                                        # noqa: E402

NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:600]}")


ASSETS = REPO / "frontend" / "dist" / "assets"
BUNDLE = ASSETS / "index-BEOJX8L5.js"
RAW = BUNDLE.read_bytes()
B = RAW.decode("utf-8")
SHARED = REPO / "frontend" / "shared" / "dz-garde-client.js"
DIST = REPO / "frontend" / "dist" / "shared" / "dz-garde-client.js"
MARKER = "/*dzgardeclient*/"
CONFIRMER = "await window.__dzDialogue.confirmer("
# empreinte du bundle d'AVANT le maillon (HEAD e2b750a9, t309 T3 : dzcanauxpre en queue), mesurée avant la pose
BASE_SHA256 = "2950aa314e321d101bc451392fe51f9a9f310fe91e72ccca9f7262f7f2a067b4"


def node(code):
    with tempfile.TemporaryDirectory() as _d:
        f = pathlib.Path(_d) / "h.js"
        f.write_text(code, "utf-8")
        p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except ValueError:
        return {"erreur": (p.stdout + p.stderr)[-800:]}


def blocs(s):
    return [(m.start(), s.index("/*__DZ_%s_END__*/" % m.group(1)))
            for m in re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", s)]


# ── [M] le maillon ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[M] le maillon")
try:
    import patch_bundle_dzgardeclient as PM                 # noqa: E402
except Exception as e:                                      # noqa: BLE001
    PM = None
    check("M0 le maillon patch_bundle_dzgardeclient existe", False, repr(e))
check("M1 le marqueur une fois dans le bundle", B.count(MARKER) == 1, str(B.count(MARKER)))
check("M2 aucun .bak_dzgardeclient laissé", not list(ASSETS.glob("*.bak_dzgardeclient")))
if PM:
    src = (REPO / "scripts" / "patch_bundle_dzgardeclient.py").read_text("utf-8")
    check("M3 lecture et écriture en OCTETS", "read_text(" not in src and "write_text(" not in src
          and "read_bytes(" in src and "write_bytes(" in src)
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzgardeclient.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("M4 --check : « déjà appliqué », bundle inchangé", r.returncode == 0 and "déjà appliqué" in r.stdout
          and BUNDLE.read_bytes() == RAW, r.stdout + r.stderr)
    check("M5 sondes amont : marqueur de dzcanauxpre et épingles", lambda: ("dzcanauxpre", "/*dzcanauxpre*/", 1) in PM.SONDE_AMONT
          and ("useState", "x.useState(", 731) in PM.SONDE_AMONT and ("version", "v2.8.0", 4) in PM.SONDE_AMONT
          and ("montage", "DzTracks", 181) in PM.SONDE_AMONT and ("dialogue", CONFIRMER, 30) in PM.SONDE_AMONT)
    try:
        avant = PM.defaire(B) if MARKER in B else ""
    except AssertionError:
        avant = ""
    check("M6 chaque ancre une fois dans le bundle d'avant, chaque remplacement une fois dans le livré",
          lambda: bool(avant) and all(avant.count(a) == 1 and B.count(z) == 1 for a, z in PM.PAIRES))
    check("M7 les paires n'ont aucune fin de ligne, n'ajoutent aucun x.useState( ni confirmation dans le bundle",
          all("\n" not in a + z and "x.useState(" not in z and CONFIRMER not in z for a, z in PM.PAIRES))
    check("M8 chaque remplacement est HORS de tout bloc de couche __DZ_*_BEGIN__",
          lambda: all(not (s0 <= B.index(z) <= e0) for _a, z in PM.PAIRES for s0, e0 in blocs(B)))
    check("M9 aller-retour exact : appliquer(defaire(B)) == B, defaire(B) sans marqueur",
          lambda: PM.appliquer(PM.defaire(B)) == B and MARKER not in PM.defaire(B))
    check("M10 la base est rendue À L'OCTET (empreinte du bundle d'avant le maillon, CRLF compris)",
          lambda: hashlib.sha256(PM.defaire(B).encode("utf-8")).hexdigest() == BASE_SHA256)
    check("M11 G1 garde le code d'origine ENTIER comme repli (derrière window.__dzGardeClient)",
          lambda: PM.PAIRES[0][0].split("=>{", 1)[1] in PM.PAIRES[0][1] and "window.__dzGardeClient" in PM.PAIRES[0][1])
for jeton, n in {"x.useState(": 731, "v2.8.0": 4, "DzTracks": 181, CONFIRMER: 30, "/*dzcanauxpre*/": 1}.items():
    check(f"M12 compte {jeton!r} = {n}", B.count(jeton) == n, str(B.count(jeton)))
check("M13 CRLF partout (en octets)", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
if NODE:
    with tempfile.TemporaryDirectory() as _d:
        t = pathlib.Path(_d) / "b.mjs"
        t.write_bytes(RAW)
        rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("M14 node --check : le bundle PARSE", rc.returncode == 0, rc.stderr[-300:])

print("\n[M] la chaîne inverse")
check("M20 avant_dzgardeclient existe et rend defaire(B)",
      lambda: PM is not None and AIDE.avant_dzgardeclient(B) == PM.defaire(B))
check("M21 avant_dzgardeclient sans marqueur : rendu tel quel",
      lambda: AIDE.avant_dzgardeclient(PM.defaire(B)) == PM.defaire(B))
check("M22 avant_dzcanauxpre défait dzgardeclient D'ABORD (appel en tête), puis dzcanauxpre",
      lambda: MARKER not in AIDE.avant_dzcanauxpre(B) and "/*dzcanauxpre*/" not in AIDE.avant_dzcanauxpre(B)
      and AIDE.avant_dzcanauxpre(B) == AIDE.avant_dzcanauxpre(AIDE.avant_dzgardeclient(B)))
check("M23 l'appel est en TÊTE de avant_dzcanauxpre (avant le test du marqueur)",
      lambda: (lambda s: 0 <= s.find("avant_dzgardeclient(bundle)") < s.find("_m.MARKER not in bundle"))(
          (BACKEND / "tests" / "_i18n_l1_aide.py").read_text("utf-8").split("def avant_dzcanauxpre(", 1)[1].split("\ndef ", 1)[0]))
check("M24 la chaîne reste complète (avant_dzassistant retire aussi dzgardeclient)",
      lambda: MARKER not in AIDE.avant_dzassistant(B) and "/*__dzassistant*/" not in AIDE.avant_dzassistant(B))

# ── [F] le script partagé ───────────────────────────────────────────────────────────────────────────────────────────
print("\n[F] le script dz-garde-client.js")
check("F1 le script existe, copie dist OCTET POUR OCTET", lambda: SHARED.read_bytes() == DIST.read_bytes())
HTML = (REPO / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
BALISE = '<script src="/shared/dz-garde-client.js"></script>'
check("F2 balise dans la SPA, une fois, après dz-espace-assistant.js (classique : avant le module différé)",
      lambda: HTML.count(BALISE) == 1 and HTML.index("/shared/dz-espace-assistant.js") < HTML.index(BALISE)
      and HTML.index("/shared/dz-i18n.js") < HTML.index(BALISE))
check("F3 ni emoji, ni window.alert/confirm/prompt, ni innerHTML",
      lambda: not re.search("[\U0001F300-\U0001FAFF☀-➿✓✗]", SHARED.read_text("utf-8"))
      and not re.search(r"window\.(alert|confirm|prompt)\(", SHARED.read_text("utf-8"))
      and "innerHTML" not in SHARED.read_text("utf-8"))

HARNAIS_F = r"""
var window=globalThis;var evts=[],dial=[],infos=[],REPONSE=true,AVEC_DIALOGUE=true;
window.dispatchEvent=function(e){evts.push(e.type)};
globalThis.CustomEvent=function(t,o){this.type=t;this.detail=o&&o.detail};
window.dzT=function(k,v){return k+(v?JSON.stringify(v):"")};
window.__dzDialogue={confirmer:function(m,o){dial.push([m,o]);return Promise.resolve(REPONSE)},
  informer:function(m,o){infos.push(m);return Promise.resolve()}};
__SCRIPT__
function rep(st,d){return Promise.resolve({ok:st>=200&&st<300,status:st,json:function(){return d===undefined?Promise.reject(new Error("pas de json")):Promise.resolve(d)}})}
var REFUS={confirmation:{detail:{message:"Confirmez la publication au nom de Société C.",code:"confirmation",client:"esp_c",nom:"Société C",canaux:["X (Société C)","Telegram C"]}},
  a_valider:{detail:{message:"Le client doit valider ce post.",code:"a_valider",client:"esp_c",nom:"Société C",canaux:[]}},
  consentement:{detail:{message:"Consentement manquant pour Telegram C.",code:"consentement",client:"esp_c",nom:"Société C",canaux:["Telegram C"]}}};
async function jouer(nom,suite,corps){
  var envois=[];evts=[];dial=[];infos=[];
  function envoyer(c){envois.push(JSON.parse(JSON.stringify(c)));var r=suite[Math.min(envois.length-1,suite.length-1)];
    if(r==="jette")return Promise.reject(new Error("réseau"));return rep(r[0],r[1])}
  var res=await window.__dzGardeClient.patch("p1",corps||{status:"scheduled"},envoyer);
  return {res:res,envois:envois,evts:evts.slice(),dial:dial.slice(),infos:infos.slice()};
}
(async function(){
  var R={api:typeof window.__dzGardeClient==="object"&&typeof window.__dzGardeClient.patch==="function"
    &&typeof window.__dzGardeClient.etiquette==="function"};
  R.ok=await jouer("ok",[[200,{id:"p1",status:"scheduled"}]]);
  R.autre_etat=await jouer("ae",[[200,{id:"p1",status:"a_valider"}]],{status:"scheduled",caption:"neuf"});
  R.sans_statut=await jouer("ss",[[200,{id:"p1",status:"a_valider"}]],{caption:"neuf"});
  REPONSE=true;R.conf_oui=await jouer("co",[[409,REFUS.confirmation],[200,{id:"p1",status:"scheduled",confirme_client:"esp_c"}]]);
  REPONSE=false;R.conf_non=await jouer("cn",[[409,REFUS.confirmation]]);
  REPONSE=true;R.conf_boucle=await jouer("cb",[[409,REFUS.confirmation],[409,REFUS.confirmation]]);
  R.a_valider=await jouer("av",[[409,REFUS.a_valider]]);
  R.consentement=await jouer("cs",[[409,REFUS.consentement]]);
  R.autre_409=await jouer("a4",[[409,{detail:"conflit ordinaire"}]]);
  R.e500=await jouer("e5",[[500,{detail:"boum"}]]);
  R.jette=await jouer("j",["jette"]);
  R.non_json=await jouer("nj",[[200,undefined]]);
  R.etiq={a:window.__dzGardeClient.etiquette("a_valider"),s:window.__dzGardeClient.etiquette("scheduled")};
  /* fix de revue (26/10/2026) : « Envoyer maintenant » par window.__dzGardeClient.fire, contrat de D.postJson */
  function repT(st,txt){return Promise.resolve({ok:st>=200&&st<300,status:st,json:function(){return Promise.resolve(JSON.parse(txt))},text:function(){return Promise.resolve(txt)}})}
  async function tirer(suite){var envois=[];evts=[];dial=[];infos=[];
    function envoyer(c){envois.push(JSON.parse(JSON.stringify(c)));var r=suite[Math.min(envois.length-1,suite.length-1)];
      if(r==="jette")return Promise.reject(new Error("réseau"));return repT(r[0],r[1])}
    var res=await window.__dzGardeClient.fire("p1",envoyer);return {res:res,envois:envois,evts:evts.slice(),dial:dial.slice(),infos:infos.slice()}}
  R.api_fire=typeof window.__dzGardeClient.fire==="function";
  R.f_ok=await tirer([[200,JSON.stringify({sent:["x"],pending:[]})]]);
  REPONSE=true;R.f_oui=await tirer([[409,JSON.stringify(REFUS.confirmation)],[200,JSON.stringify({sent:["telegram"]})]]);
  REPONSE=false;R.f_non=await tirer([[409,JSON.stringify(REFUS.confirmation)]]);REPONSE=true;
  R.f_cons=await tirer([[409,JSON.stringify(REFUS.consentement)]]);
  R.f_409=await tirer([[409,JSON.stringify({detail:"déjà publié"})]]);
  R.f_500=await tirer([[500,"<html><b>boum</b>  interne</html>"]]);
  R.f_422=await tirer([[422,JSON.stringify({detail:[{msg:"champ requis"}]})]]);
  R.f_jette=await tirer(["jette"]);
  AVEC_DIALOGUE=false;var d=window.__dzDialogue;delete window.__dzDialogue;
  R.sans_dialogue=await jouer("sd",[[409,REFUS.confirmation]]);window.__dzDialogue=d;
  process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
RF = {}
if NODE and SHARED.is_file():
    RF = node(HARNAIS_F.replace("__SCRIPT__", SHARED.read_text("utf-8")))
check("F4 le script s'exécute sous node et pose window.__dzGardeClient {patch, etiquette}",
      bool(RF) and "erreur" not in RF and RF.get("api") is True, str(RF.get("erreur", RF))[:600])
o = RF.get("ok", {})
check("F5 200 : rend le json, un seul envoi du corps tel quel, aucun dialogue, aucun rechargement",
      o.get("res") == {"id": "p1", "status": "scheduled"} and o.get("envois") == [{"status": "scheduled"}]
      and not o.get("dial") and not o.get("infos") and not o.get("evts"), str(o))
o = RF.get("autre_etat", {})
check("F6 200 avec un AUTRE état que celui demandé (scheduled -> a_valider) : json rendu ET deepotus:schedule-recharger",
      o.get("res", {}).get("status") == "a_valider" and o.get("evts") == ["deepotus:schedule-recharger"], str(o))
o = RF.get("sans_statut", {})
check("F7 200 sans état demandé : aucun rechargement (rien à corriger à l'écran)", o.get("evts") == [], str(o))
o = RF.get("conf_oui", {})
dlg = (o.get("dial") or [[None, {}]])[0]
check("F8 409 confirmation : UN dialogue qui nomme le client et ses canaux, titre et bouton dédiés",
      len(o.get("dial") or []) == 1 and dlg[0] == 'scheduler.client.confirmer{"nom":"Société C","canaux":"X (Société C), Telegram C"}'
      and dlg[1].get("titre") == "scheduler.client.confirmer_titre" and dlg[1].get("ok") == "scheduler.client.confirmer_ok", str(o))
check("F9 ... oui : second PATCH = le même corps + confirme_client:<id du client>, json rendu, aucun rechargement",
      o.get("envois") == [{"status": "scheduled"}, {"status": "scheduled", "confirme_client": "esp_c"}]
      and (o.get("res") or {}).get("confirme_client") == "esp_c" and not o.get("evts"), str(o))
o = RF.get("conf_non", {})
check("F10 ... non : rien renvoyé, deepotus:schedule-recharger, null", o.get("res") is None and len(o.get("envois") or []) == 1
      and o.get("evts") == ["deepotus:schedule-recharger"] and not o.get("infos"), str(o))
o = RF.get("conf_boucle", {})
check("F11 ... un second refus malgré confirme_client : pas de boucle (2 envois, 1 dialogue), message + rechargement",
      len(o.get("envois") or []) == 2 and len(o.get("dial") or []) == 1 and o.get("infos") == ["Confirmez la publication au nom de Société C."]
      and o.get("evts") == ["deepotus:schedule-recharger"] and o.get("res") is None, str(o))
o = RF.get("a_valider", {})
check("F12 409 a_valider : informer(message du serveur) + rechargement, null, aucune confirmation",
      o.get("infos") == ["Le client doit valider ce post."] and o.get("evts") == ["deepotus:schedule-recharger"]
      and o.get("res") is None and not o.get("dial") and len(o.get("envois") or []) == 1, str(o))
o = RF.get("consentement", {})
check("F13 409 consentement : informer(message) + rechargement, null",
      o.get("infos") == ["Consentement manquant pour Telegram C."] and o.get("evts") == ["deepotus:schedule-recharger"]
      and o.get("res") is None, str(o))
for k, lib in (("autre_409", "un 409 qui n'est pas du client"), ("e500", "un 500"), ("jette", "le réseau qui jette"),
               ("non_json", "un 200 sans json")):
    o = RF.get(k, {})
    check(f"F14 {lib} : comportement d'origine (null), ni dialogue ni rechargement",
          o.get("res") is None and not o.get("dial") and not o.get("infos") and not o.get("evts"), str(o))
o = RF.get("f_ok", {})
check("F17 fire 200 : {ok:true, …json} comme D.postJson, corps {} envoyé une fois, ni dialogue ni rechargement",
      RF.get("api_fire") is True and o.get("res") == {"ok": True, "sent": ["x"], "pending": []} and o.get("envois") == [{}]
      and not o.get("dial") and not o.get("evts"), str(o))
o = RF.get("f_oui", {})
check("F18 fire 409 confirmation, oui : dialogue nominatif puis second /fire avec {confirme_client}, succès rendu",
      len(o.get("dial") or []) == 1 and (o.get("dial") or [[""]])[0][0].startswith("scheduler.client.confirmer{")
      and "Société C" in (o.get("dial") or [[""]])[0][0]
      and o.get("envois") == [{}, {"confirme_client": "esp_c"}] and o.get("res") == {"ok": True, "sent": ["telegram"]}
      and not o.get("evts"), str(o))
o = RF.get("f_non", {})
check("F19 fire 409 confirmation, non : rien renvoyé, rechargement, {ok:false, dzRefus, error:message} (jamais « envoyé »)",
      len(o.get("envois") or []) == 1 and o.get("evts") == ["deepotus:schedule-recharger"]
      and (o.get("res") or {}).get("ok") is False and (o.get("res") or {}).get("dzRefus") is True
      and (o.get("res") or {}).get("error") == "Confirmez la publication au nom de Société C.", str(o))
o = RF.get("f_cons", {})
check("F20 fire autre 409 du client : informer(message) + rechargement, refus dzRefus, aucun dialogue de confirmation",
      o.get("infos") == ["Consentement manquant pour Telegram C."] and o.get("evts") == ["deepotus:schedule-recharger"]
      and not o.get("dial") and (o.get("res") or {}).get("dzRefus") is True and (o.get("res") or {}).get("ok") is False, str(o))
check("F21 fire, le reste = D.postJson : 409 ordinaire (detail chaîne), 500 HTML, 422 (premier msg), réseau qui jette",
      RF.get("f_409", {}).get("res") == {"ok": False, "status": 409, "error": "déjà publié"}
      and RF.get("f_500", {}).get("res") == {"ok": False, "status": 500, "error": "HTTP 500 : boum interne"}
      and RF.get("f_422", {}).get("res") == {"ok": False, "status": 422, "error": "champ requis"}
      and RF.get("f_jette", {}).get("res") == {"ok": False, "error": "réseau"}
      and not any(RF.get(k, {}).get("evts") or RF.get(k, {}).get("infos") for k in ("f_409", "f_500", "f_422", "f_jette")),
      str({k: RF.get(k) for k in ("f_409", "f_500", "f_422", "f_jette")}))
check("F15 etiquette(a_valider) = dzT(scheduler.etat.a_valider), null pour un autre état",
      RF.get("etiq") == {"a": "scheduler.etat.a_valider", "s": None}, str(RF.get("etiq")))
o = RF.get("sans_dialogue", {})
check("F16 sans couche de dialogue : jamais confirmé par défaut (rien renvoyé), rechargement",
      len(o.get("envois") or []) == 1 and o.get("res") is None and o.get("evts") == ["deepotus:schedule-recharger"], str(o))

# ── [G] le livré ────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[G] les fonctions livrées, sous node")


def tranche(debut, fin):
    i = B.index(debut)
    return B[i:B.index(fin, i)]


G1 = ""
try:
    G1 = tranche("updateScheduledPost:", ",deleteScheduledPost:")
except ValueError:
    pass
check("G1.0 G1 dans le livré : le marqueur et la délégation", MARKER in G1 and "window.__dzGardeClient.patch(e,t," in G1, G1[:300])
HARNAIS_G = r"""
var Te="/api",window=globalThis,appels=[],deleg=[],SUITE=null;
globalThis.fetch=function(u,o){appels.push({u:u,m:o&&o.method,h:o&&o.headers,b:o&&o.body});
  if(SUITE==="jette")return Promise.reject(new Error("réseau"));
  return Promise.resolve({ok:SUITE[0]<300,status:SUITE[0],json:function(){return Promise.resolve(SUITE[1])}})};
var D={__G1__};
(async function(){
  var R={};
  delete window.__dzGardeClient;
  SUITE=[200,{id:"p1",status:"scheduled"}];appels=[];R.orig_ok={r:await D.updateScheduledPost("p1",{status:"scheduled"}),a:appels.slice()};
  SUITE=[409,{detail:{code:"confirmation"}}];appels=[];R.orig_409={r:await D.updateScheduledPost("p1",{status:"scheduled"}),a:appels.slice()};
  SUITE="jette";appels=[];R.orig_jette={r:await D.updateScheduledPost("p1",{status:"scheduled"}),a:appels.slice()};
  window.__dzGardeClient={patch:function(id,corps,envoyer){deleg.push([id,corps,typeof envoyer]);
    return envoyer({status:"scheduled",confirme_client:"esp_c"}).then(function(r){return {via:"garde",status:r.status}})}};
  SUITE=[200,{id:"p1"}];appels=[];R.garde={r:await D.updateScheduledPost("p2",{caption:"c"}),a:appels.slice(),d:deleg.slice()};
  process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
RG = {}
if NODE and G1:
    RG = node(HARNAIS_G.replace("__G1__", G1))
check("G1.1 la fonction livrée s'exécute sous node", bool(RG) and "erreur" not in RG, str(RG.get("erreur", RG))[:600])
o = RG.get("orig_ok", {})
check("G1.2 sans __dzGardeClient, 200 : PATCH d'origine (URL, méthode, en-tête, corps JSON), rend le json",
      o.get("r") == {"id": "p1", "status": "scheduled"} and o.get("a") == [{"u": "/api/schedule/p1", "m": "PATCH",
      "h": {"Content-Type": "application/json"}, "b": '{"status":"scheduled"}'}], str(o))
check("G1.3 sans __dzGardeClient, 409 : null comme avant (un seul envoi)",
      RG.get("orig_409", {}).get("r") is None and len(RG.get("orig_409", {}).get("a") or []) == 1, str(RG.get("orig_409")))
check("G1.4 sans __dzGardeClient, réseau qui jette : null comme avant", RG.get("orig_jette", {}).get("r") is None
      and len(RG.get("orig_jette", {}).get("a") or []) == 1, str(RG.get("orig_jette")))
o = RG.get("garde", {})
check("G1.5 avec __dzGardeClient : patch(id, corps, envoyer) appelé une fois, son résultat rendu",
      o.get("d") == [["p2", {"caption": "c"}, "function"]] and o.get("r") == {"via": "garde", "status": 200}, str(o))
check("G1.6 ... envoyer(corps) = le PATCH d'origine sur /schedule/<id> avec le corps qu'on lui passe, sans autre appel",
      o.get("a") == [{"u": "/api/schedule/p2", "m": "PATCH", "h": {"Content-Type": "application/json"},
                      "b": '{"status":"scheduled","confirme_client":"esp_c"}'}], str(o))

LM = ""
try:
    LM = tranche("function Lm(", "const j=a.find(")
except ValueError:
    pass
EFF = ""
m = re.search(r'x\.useEffect\(\(\)=>\{if\(!window\.__dzGardeClient\)return;.*?\},\[o\]\),', LM)
if m:
    EFF = m.group(0)[:-1]
check("G2.0 Lm : un x.useEffect neuf écoute deepotus:schedule-recharger, aucun x.useState ajouté",
      bool(EFF) and '"deepotus:schedule-recharger"' in EFF and "useState" not in EFF, LM[-1500:])
check("G2.1 l'écouteur d'origine deepotus:schedule-reload est intact",
      'x.useEffect(()=>{function R(){o&&o()}return window.addEventListener("deepotus:schedule-reload",R),'
      '()=>window.removeEventListener("deepotus:schedule-reload",R)},[o])' in LM)
HARNAIS_G2 = r"""
var window=globalThis,ec={},rech=0,effets=[];
window.addEventListener=function(t,f){(ec[t]=ec[t]||[]).push(f)};
window.removeEventListener=function(t,f){ec[t]=(ec[t]||[]).filter(function(g){return g!==f})};
var x={useEffect:function(f,dep){effets.push([f,dep])}};var o=function(){rech++};
function monter(){effets=[];__EFF__;return effets[0]}
(function(){
  var R={};
  delete window.__dzGardeClient;var e=monter();R.sans={retour:typeof e[0](),ec:(ec["deepotus:schedule-recharger"]||[]).length};
  window.__dzGardeClient={};e=monter();var nettoie=e[0]();R.dep=e[1].length;
  (ec["deepotus:schedule-recharger"]||[]).forEach(function(f){f({})});R.rech=rech;
  nettoie();R.apres=(ec["deepotus:schedule-recharger"]||[]).length;
  process.stdout.write(JSON.stringify(R));
})();
"""
RG2 = {}
if NODE and EFF:
    RG2 = node(HARNAIS_G2.replace("__EFF__", EFF))
check("G2.2 sous node : sans __dzGardeClient aucun écouteur ; avec, l'évènement appelle reloadPosts une fois ; retiré au démontage",
      RG2.get("sans") == {"retour": "undefined", "ec": 0} and RG2.get("rech") == 1 and RG2.get("apres") == 0
      and RG2.get("dep") == 1, str(RG2))
PAST = ""
try:
    PAST = tranche('r.jsx(te,e.status==="a_valider"?', '||e.status})') + '||e.status})'
except ValueError:
    pass
check("G3.1 la table des états d'origine (sortie d'i18nfix) est intacte, l'inconnu reste affiché tel quel",
      'skipped:dzT("scheduler.etat.skipped")})[e.status]||e.status})' in B and 'e.status==="ready"?"amber"' in B)
HARNAIS_G3 = r"""
var r={jsx:function(c,p){return p}},te="te",dzT=function(k){return "T:"+k};
var R={};["a_valider","ready","scheduled","draft","inconnu"].forEach(function(st){var e={status:st};var p=__PAST__;
  R[st]={tone:p.tone,dot:p.dot,children:p.children}});
process.stdout.write(JSON.stringify(R));
"""
RG3 = node(HARNAIS_G3.replace("__PAST__", PAST)) if NODE and PAST else {}
check("G3.2 pastille de l'inspecteur sous node : a_valider ambre « À valider » (dzT), ready ambre, scheduled cyan, inconnu brut",
      RG3.get("a_valider") == {"tone": "amber", "dot": True, "children": "T:scheduler.etat.a_valider"}
      and RG3.get("ready") == {"tone": "amber", "dot": True, "children": "T:scheduler.etat.ready"}
      and RG3.get("scheduled", {}).get("tone") == "cyan" and RG3.get("draft", {}).get("tone") == "neutral"
      and RG3.get("inconnu", {}).get("children") == "inconnu", str(RG3)[:600])
check("G3.3 couleur Rm ambre comme ready",
      'const Rm={posted:"var(--green)",failed:"var(--red)",ready:"var(--amber)",a_valider:"var(--amber)",scheduled:"var(--cyan)"' in B)

# ── [G4] « Envoyer maintenant » (fix de revue, 26/10/2026) ─────────────────────────────────────────────────────────────
G4 = ""
try:
    G4 = tranche("fireScheduledPost:", ",marketingPlan:")
except ValueError:
    pass
check("G4.0 G4 dans le livré : délégation à window.__dzGardeClient.fire, D.postJson d'origine en repli",
      "window.__dzGardeClient.fire(e," in G4 and G4.endswith(":D.postJson(`/schedule/${e}/fire`,{})"), G4)
HARNAIS_G4 = r"""
var Te="/api",window=globalThis,appels=[],pj=[],deleg=[];
globalThis.fetch=function(u,o){appels.push({u:u,m:o&&o.method,h:o&&o.headers,b:o&&o.body});return Promise.resolve({ok:true,status:200})};
var D={postJson:function(u,b){pj.push([u,b]);return Promise.resolve({ok:true,via:"postJson"})},__G4__};
(async function(){
  var R={};delete window.__dzGardeClient;
  R.sans={r:await D.fireScheduledPost("p1"),pj:pj.slice(),a:appels.slice()};pj=[];
  window.__dzGardeClient={fire:function(id,envoyer){deleg.push([id,typeof envoyer]);return envoyer({confirme_client:"esp_c"}).then(function(){return {ok:true,via:"garde"}})}};
  R.avec={r:await D.fireScheduledPost("p2"),pj:pj.slice(),a:appels.slice(),d:deleg.slice()};
  process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
RG4 = node(HARNAIS_G4.replace("__G4__", G4)) if NODE and G4 else {}
check("G4.1 sans __dzGardeClient : D.postJson(`/schedule/p1/fire`, {}) d'origine, aucun fetch direct",
      RG4.get("sans") == {"r": {"ok": True, "via": "postJson"}, "pj": [["/schedule/p1/fire", {}]], "a": []}, str(RG4)[:600])
check("G4.2 avec __dzGardeClient : fire(id, envoyer) une fois ; envoyer(corps) = POST brut sur /api/schedule/p2/fire ; pas de postJson",
      (RG4.get("avec") or {}).get("d") == [["p2", "function"]] and (RG4.get("avec") or {}).get("pj") == []
      and (RG4.get("avec") or {}).get("a") == [{"u": "/api/schedule/p2/fire", "m": "POST", "h": {"Content-Type": "application/json"},
                                               "b": '{"confirme_client":"esp_c"}'}]
      and (RG4.get("avec") or {}).get("r") == {"ok": True, "via": "garde"}, str(RG4)[:600])
check("G5 vue Routage (H) : un envoi dzRefus affiche le message du serveur, pas « Marqué prêt »",
      'l(!1),I!=null&&I.dzRefus?u(I.error):I!=null&&I.ok?u(dzT("scheduler.routage.envoye"' in B)
check("G6 inspecteur (N) : un envoi dzRefus affiche le message du serveur, pas « Pas d'envoi automatique »",
      'y(!1),j!=null&&j.dzRefus?v(j.error):j!=null&&j.ok?v(dzT("scheduler.post.envoye_sur"' in B)
check("G3c carte du calendrier : badge « À valider » (dzT) à côté du « READY » d'origine",
      'children:"READY"}),e.status==="a_valider"&&r.jsx("span",{style:{fontSize:8.5,color:"var(--amber)",fontWeight:600},'
      'children:dzT("scheduler.etat.a_valider")}),' in B)

# ── [K] textes ──────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[K] textes")
ATTENDU = {
    "scheduler.etat.a_valider": ("À valider", "Awaiting approval"),
    "scheduler.client.confirmer": ("Publier au nom de {nom} sur {canaux} ? Le consentement du client est en cours pour "
                                   "ces canaux.",
                                   "Publish on behalf of {nom} on {canaux}? The client's consent is current for these "
                                   "channels."),
    "scheduler.client.confirmer_titre": ("Publication au nom du client", "Publishing on behalf of the client"),
    "scheduler.client.confirmer_ok": ("Publier en son nom", "Publish on their behalf"),
}
SRC = {}
for f in (REPO / "frontend" / "shared" / "i18n").glob("*.json"):
    SRC.update(json.loads(f.read_text("utf-8")))
for k, (fr, en) in ATTENDU.items():
    check(f"K1 {k} : FR et EN mot pour mot", SRC.get(k, {}).get("fr") == fr and SRC.get(k, {}).get("en") == en, str(SRC.get(k)))
DICO = (REPO / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("K2 le dictionnaire assemblé porte les quatre clés, shared == dist à l'octet",
      all(json.dumps(k).encode() in DICO for k in ATTENDU)
      and DICO == (REPO / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())
r = subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=str(REPO))
check("K3 i18n_assembler --check : à jour", r.returncode == 0, r.stdout + r.stderr)
check("K4 chaque clé est employée (script ou bundle)",
      lambda: all(k in SHARED.read_text("utf-8") or k in B for k in ATTENDU))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
