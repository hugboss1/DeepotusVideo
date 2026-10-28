# -*- coding: utf-8 -*-
"""t311 tâche 8 (27/10/2026) — la page WhatsApp dans la barre, « Agent WhatsApp » de Réglages › Espaces, la connaissance
de l'assistant.

Plan docs/superpowers/plans/2026-10-27-t311-agent-whatsapp.md (tâche 8).
[1] le maillon      scripts/patch_bundle_whatsapppage.py : marqueur x1, aucun .bak_whatsapppage, octets, --check « déjà
                    appliqué », sondes (marqueur dzwhatsapp et épingles), 4 paires (ancre x1 dans la vue d'avant,
                    remplacement x1 dans le livré), hors couche, aller-retour exact, épingles intouchées (x.useState( 731),
                    CRLF, node --check ; `version` reste le dernier maillon (aucun .bak_* laissé) ;
[2] réversible      avant_whatsapppage == defaire, appelé EN TÊTE de avant_dzwhatsapp ; la chaîne reste complète ;
[3] les paires      rail (texte exact, entre Avatar live et Réglages, icône dz-nav-boite-reception), iframe /whatsapp/
                    (clé pwhatsapp), liste blanche des vues, et sous node : le bouton de DzEspaces (fonction LIVRÉE) appelle
                    window.__dzWhatsappEspace.ouvrir(st.actif) ;
[4] le panneau      frontend/shared/dz-whatsapp-espace.js sous node (faux DOM, faux fetch) : lecture des réglages, PUT au
                    format EXACT, mode auto jamais sans confirmation (refusée, absente, acceptée), modèles UTILITY
                    approuvés du premier numéro relié, sans numéro ou lecture en échec : champ grisé, note, PUT sans
                    modele_validation ; modèle rangé hors liste gardé ; refus 400 : le message du serveur ;
[5] livraison       shared == dist, balise dans index.html après dz-pour-qui.js, textes FR + EN, assemblé à jour,
                    aucun confirm natif ;
[6] l'assistant     VUES (agent_aide, dz-agent-logique), ancre rail.whatsapp, LABS_CADRES + répondeur de la page,
                    catalogue (LABS, PARTAGES, couverture), fiches rédigées, AGENT.md, AGENTS.md (15 écrans).
Run : & $PY tests/test_whatsapp_page_ecran.py   (depuis backend/)
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "agent"))
import _i18n_l1_aide as AIDE  # noqa: E402
F = AIDE.fr

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
        fail += 1; print(f"  FAIL  {label} {detail}")


ASSETS = REPO / "frontend" / "dist" / "assets"
BUNDLE = ASSETS / "index-BEOJX8L5.js"
RAW = BUNDLE.read_bytes()
B = RAW.decode("utf-8")
SH = REPO / "frontend" / "shared"
DI = REPO / "frontend" / "dist" / "shared"
MODULE = SH / "dz-whatsapp-espace.js"
MARKER = "/*whatsapppage*/"
CONFIRMER = "await window.__dzDialogue.confirmer("
RAIL = ('{id:"avatarlive",label:"Avatar live",icon:"dz-media-avatar",desc:dzT("avatar.rail.desc"),new:!0},' + MARKER
        + '{id:"whatsapp",label:dzT("whatsapp.rail.titre"),icon:"dz-nav-boite-reception",desc:dzT("whatsapp.rail.desc"),'
          'new:!0},{id:"settings",')
VUE = ('s==="whatsapp"&&r.jsx("iframe",{src:"/whatsapp/",title:dzT("whatsapp.page.titre"),style:{position:"absolute",'
       'inset:0,width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}},"pwhatsapp"),')
OUVRIR = "window.__dzWhatsappEspace&&window.__dzWhatsappEspace.ouvrir(st.actif)"


def blocs(s):
    return [(m.start(), s.index("/*__DZ_%s_END__*/" % m.group(1)))
            for m in re.finditer(r"/\*__DZ_([A-Z0-9_]+?)_BEGIN__\*/", s)]


def node(code):
    with tempfile.TemporaryDirectory() as _d:
        f = pathlib.Path(_d) / "h.js"
        f.write_text(code, "utf-8")
        p = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except ValueError:
        return {"erreur": (p.stdout + p.stderr)[-800:]}


_SRC_ASSISTANT = (BACKEND / "tests" / "test_espace_assistant_ecran.py").read_text("utf-8")
FAUX_DOM = re.search(r'FAUX_DOM = r"""(.*?)"""', _SRC_ASSISTANT, re.S).group(1)
FAUX_REACT = re.search(r'FAUX_REACT = r"""(.*?)"""', _SRC_ASSISTANT, re.S).group(1)

# ── [1] le maillon ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[1] le maillon")
try:
    import patch_bundle_whatsapppage as PM                # noqa: E402
except Exception as e:                                   # noqa: BLE001
    PM = None
    check("1.0 le maillon patch_bundle_whatsapppage existe", False, repr(e))
check("1.1 le marqueur une fois dans le bundle", B.count(MARKER) == 1, str(B.count(MARKER)))
check("1.2 aucun .bak_* laissé (le maillon a supprimé le sien : `version` reste le dernier)", not list(ASSETS.glob("*.bak_*")),
      str(list(ASSETS.glob("*.bak_*"))))
avant = ""
if PM:
    src = (REPO / "scripts" / "patch_bundle_whatsapppage.py").read_text("utf-8")
    check("1.3 lecture et écriture en OCTETS", "read_text(" not in src and "write_text(" not in src
          and "read_bytes(" in src and "write_bytes(" in src)
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_whatsapppage.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("1.4 --check : « déjà appliqué », bundle inchangé", r.returncode == 0 and "déjà appliqué" in r.stdout
          and BUNDLE.read_bytes() == RAW, r.stdout + r.stderr)
    check("1.5 sondes amont : marqueur de dzwhatsapp et épingles",
          ("dzwhatsapp", "/*dzwhatsapp*/", 1) in PM.SONDE_AMONT and ("useState", "x.useState(", 731) in PM.SONDE_AMONT
          and ("version", "v2.8.0", 4) in PM.SONDE_AMONT and ("montage", "DzTracks", 181) in PM.SONDE_AMONT
          and ("dialogue", CONFIRMER, 30) in PM.SONDE_AMONT)
    try:
        avant = PM.defaire(B) if MARKER in B else ""
    except AssertionError:
        avant = ""
    check("1.6 quatre paires ; chaque ancre une fois dans le bundle d'avant, chaque remplacement une fois dans le livré",
          lambda: len(PM.PAIRES) == 4 and bool(avant) and all(avant.count(a) == 1 and B.count(z) == 1 for a, z in PM.PAIRES))
    check("1.7 les paires n'ont aucune fin de ligne, n'ajoutent ni x.useState( ni confirmation",
          all("\n" not in a + z and "x.useState(" not in z and CONFIRMER not in z for a, z in PM.PAIRES))
    check("1.8 chaque ancre (vue d'avant) et chaque remplacement (livré) HORS de tout bloc de couche __DZ_*_BEGIN__",
          lambda: all(not (s0 <= B.index(z) <= e0) for _a, z in PM.PAIRES for s0, e0 in blocs(B))
          and all(not (s0 <= avant.index(a) <= e0) for a, _z in PM.PAIRES for s0, e0 in blocs(avant)))
    check("1.9 aller-retour exact : appliquer(defaire(B)) == B, defaire(B) sans marqueur ni whatsapp au rail",
          lambda: PM.appliquer(PM.defaire(B)) == B and MARKER not in PM.defaire(B)
          and '{id:"whatsapp",' not in PM.defaire(B) and "__dzWhatsappEspace" not in PM.defaire(B))
    check("1.10 la vue d'avant porte encore dzwhatsapp (le maillon se pose APRÈS lui)",
          lambda: PM.defaire(B).count("/*dzwhatsapp*/") == 1)
for jeton, n in {"x.useState(": 731, "v2.8.0": 4, "DzTracks": 181, CONFIRMER: 30, "/*dzwhatsapp*/": 1,
                 '{id:"whatsapp",': 1, "function DzEspaces(": 1}.items():
    check(f"1.11 compte {jeton!r} = {n}", B.count(jeton) == n, str(B.count(jeton)))
check("1.12 CRLF partout (en octets)", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
if NODE:
    with tempfile.TemporaryDirectory() as _d:
        t = pathlib.Path(_d) / "b.mjs"
        t.write_bytes(RAW)
        rc = subprocess.run([NODE, "--check", str(t)], capture_output=True, text=True)
    check("1.13 node --check : le bundle PARSE", rc.returncode == 0, rc.stderr[-300:])

# ── [2] réversible ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[2] la chaîne inverse")
# t313 (28/10/2026) : le maillon dzinspiration est posé APRÈS whatsapppage ; avant_whatsapppage le défait d'abord
check("2.1 avant_whatsapppage existe et rend defaire(B d'avant dzinspiration)",
      lambda: PM is not None and AIDE.avant_whatsapppage(B) == PM.defaire(AIDE.avant_dzinspiration(B)))
check("2.2 avant_whatsapppage sans marqueur : rendu tel quel",
      lambda: AIDE.avant_whatsapppage(PM.defaire(AIDE.avant_dzinspiration(B))) == PM.defaire(AIDE.avant_dzinspiration(B)))
check("2.3 avant_dzwhatsapp défait whatsapppage D'ABORD, puis dzwhatsapp",
      lambda: MARKER not in AIDE.avant_dzwhatsapp(B) and "/*dzwhatsapp*/" not in AIDE.avant_dzwhatsapp(B)
      and AIDE.avant_dzwhatsapp(B) == AIDE.avant_dzwhatsapp(AIDE.avant_whatsapppage(B)))
check("2.4 l'appel est en TÊTE de avant_dzwhatsapp (avant le test du marqueur)",
      lambda: (lambda s: 0 <= s.find("avant_whatsapppage(bundle)") < s.find("_m.MARKER not in bundle"))(
          (BACKEND / "tests" / "_i18n_l1_aide.py").read_text("utf-8").split("def avant_dzwhatsapp(", 1)[1].split("\ndef ", 1)[0]))
check("2.5 la chaîne reste complète (avant_dzgardeclient et avant_dzassistant retirent aussi whatsapppage)",
      lambda: MARKER not in AIDE.avant_dzgardeclient(B) and "/*dzgardeclient*/" not in AIDE.avant_dzgardeclient(B)
      and MARKER not in AIDE.avant_dzassistant(B) and "/*__dzassistant*/" not in AIDE.avant_dzassistant(B))

# ── [3] les paires ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[3] les paires")
check("3.1 P1 : l'entrée de rail, texte exact, entre Avatar live et Réglages", B.count(RAIL) == 1)
check("3.2 P2 : la vue iframe /whatsapp/ (clé pwhatsapp), juste après celle de l'Avatar live",
      B.count(VUE) == 1 and B.count('"pwhatsapp"') == 1 and B.index('"pavlive"),') + len('"pavlive"),') == B.index(VUE))
check("3.3 P3 : whatsapp dans la liste blanche des vues",
      '"settings","vectorlab","photolab","avatarlive","whatsapp"],sg=Yu.includes(' in B)
ESP = B[B.find("function DzEspaces("):B.find("function DzComptesEspace(")]
check("3.4 P4 : DzEspaces porte le bouton (une fois), après DzComptesEspace de l'espace actif",
      ESP.count(OUVRIR) == 1 and ESP.index('"cpt:"+st.actif)') < ESP.index(OUVRIR)
      and 'children:dzT("whatsapp.espace.ouvrir")' in ESP and B.count(OUVRIR) == 1)
SONDE_ESP = r"""
var DzDepEspace=function(){},DzOnboardingPersona=function(){},DzIdentite=function(){},DzComptesEspace=function(){},DzEspaceSel=function(){};
var appels=[];
globalThis.fetch=function(u){return Promise.resolve({ok:true,status:200,json:function(){return Promise.resolve(
  u.indexOf("/api/espaces")===0?{espaces:[{id:"esp_a",nom:"A"},{id:"esp_b",nom:"B"}],actif:"esp_a"}:{kits:[]})}})};
__ESP__
(async function(){
 var R={};
 monter(DzEspaces,{});await attendre();
 var b=avec("data-dz-wa-espace-ouvrir");
 R.sans_module=b.length?b[0].p.disabled:null;
 window.__dzWhatsappEspace={ouvrir:function(e){appels.push(e)}};
 monter(DzEspaces,{});await attendre();
 b=avec("data-dz-wa-espace-ouvrir");
 R.n=b.length;R.val=b[0]&&b[0].p["data-dz-wa-espace-ouvrir"];R.dis=b[0]&&b[0].p.disabled;R.txt=texte(b[0]);R.t=b[0]&&b[0].t;
 b[0]&&b[0].p.onClick();R.appels=appels;
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
P3 = {}
if NODE and ESP:
    P3 = node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM + FAUX_REACT + SONDE_ESP.replace("__ESP__", ESP))
check("3.5 la fonction livrée DzEspaces s'exécute sous node", bool(P3) and "erreur" not in P3, str(P3.get("erreur", ""))[:800])
check("3.6 un bouton pour l'espace ACTIF ; le clic appelle __dzWhatsappEspace.ouvrir(\"esp_a\")",
      P3.get("n") == 1 and P3.get("t") == "button" and P3.get("val") == "esp_a" and P3.get("appels") == ["esp_a"]
      and P3.get("dis") is False, str(P3))
check("3.7 libellé dzT(\"whatsapp.espace.ouvrir\") ; grisé tant que le module n'est pas chargé",
      P3.get("txt") in ("whatsapp.espace.ouvrir", F("whatsapp.espace.ouvrir")) and P3.get("sans_module") is True, str(P3))

# ── [4] le panneau ──────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[4] le panneau (dz-whatsapp-espace.js sous node)")
REGLAGES = {"plafond_mois": 1000, "marche_defaut": "33",
            "agent": {"actif": False, "mode": "brouillon", "roles": ["faq"],
                      "horaires": {"jours": [0, 1, 2, 3, 4], "debut": "09:00", "fin": "18:00", "fuseau": "Europe/Paris"},
                      "message_hors_horaires": "", "plafond_jour_contact": 5, "mots_humain": ["humain"],
                      "modele_validation": None, "plafond_redactions_jour": 20}}
SONDE_MOD = r"""
var REGLAGES=__REGLAGES__, SCEN=__SCEN__;
var appels=[], confirmations=[];
function attendre(ms){return new Promise(function(ok){setTimeout(ok,ms||30)})}
function rep(st,j){return Promise.resolve({ok:st<400,status:st,json:function(){return Promise.resolve(j)}})}
globalThis.fetch=function(u,o){o=o||{};var corps=o.body?JSON.parse(o.body):undefined;appels.push({u:u,m:o.method||"GET",c:corps});
  if(u==="/api/espaces/esp_a/whatsapp/reglages"){
    if((o.method||"GET")==="PUT"){if(SCEN.put400)return rep(400,{detail:"agent : heure de début invalide (HH:MM)"});
      var r=JSON.parse(JSON.stringify(REGLAGES));r.plafond_mois=corps.plafond_mois;r.marche_defaut=corps.marche_defaut;
      Object.keys(corps.agent).forEach(function(k){r.agent[k]=corps.agent[k]});return rep(200,r)}
    return rep(200,JSON.parse(JSON.stringify(SCEN.reglages||REGLAGES)))}
  if(u.indexOf("/api/espaces?")===0)return rep(200,{espaces:[{id:"esp_a",nom:"Boulangerie"}],actif:"esp_a"});
  if(u==="/api/comptes?espace=esp_a"){
    if(SCEN.comptes500)return rep(500,{detail:"panne"});
    var cs=[{id:"c_tg",plateforme:"telegram",champs:[]}];
    if(!SCEN.sansNumero)cs.push({id:"c_wa0",plateforme:"whatsapp",champs:[{nom:"WHATSAPP_PHONE_ID",valeur:""}]},
                                 {id:"c_wa",plateforme:"whatsapp",champs:[{nom:"WHATSAPP_PHONE_ID",valeur:"pid1"}]},
                                 {id:"c_wa2",plateforme:"whatsapp",champs:[{nom:"WHATSAPP_PHONE_ID",valeur:"pid2"}]});
    return rep(200,{espace:"esp_a",comptes:cs,plateformes:{}})}
  if(u==="/api/whatsapp/c_wa/modeles?espace=esp_a"){
    if(SCEN.modeles502)return rep(502,{detail:"Kapso injoignable"});
    return rep(200,[{nom:"valid_post",langue:"fr",categorie:"utility",statut:"approved",n_parametres:1},
                    {nom:"promo",langue:"fr",categorie:"marketing",statut:"approved",n_parametres:0},
                    {nom:"attente",langue:"fr",categorie:"utility",statut:"pending",n_parametres:0},
                    {nom:"deux_vars",langue:"fr",categorie:"utility",statut:"approved",n_parametres:2},
                    {nom:"rappel",langue:"en_US",categorie:"utility",statut:"approved",n_parametres:0}])}
  return rep(404,{detail:"inconnu "+u})};
if(SCEN.dialogue!=="absent")window.__dzDialogue={confirmer:function(m,o){confirmations.push({m:m,o:o});return Promise.resolve(SCEN.dialogue==="oui")}};
__MODULE__
function att(a){return tous(body,function(n){return n.getAttribute(a)!==null})}
function un(a){return att(a)[0]||null}
(async function(){
 var R={};
 var fini=false;
 window.__dzWhatsappEspace.ouvrir("esp_a").then(function(){fini=true});
 await attendre(40);
 R.boite=att("data-dz-wa-espace-boite").length;
 R.titre=(un("data-dz-wa-espace-boite")||{getAttribute:function(){return null}}).getAttribute("aria-label");
 R.lectures=appels.map(function(a){return a.m+" "+a.u});
 R.actif=un("data-dz-wa-espace-actif").checked;R.mode=un("data-dz-wa-espace-mode").value;
 R.roles=att("data-dz-wa-espace-role").filter(function(n){return n.checked}).map(function(n){return n.getAttribute("data-dz-wa-espace-role")});
 R.jours=att("data-dz-wa-espace-jour").filter(function(n){return n.checked}).map(function(n){return n.getAttribute("data-dz-wa-espace-jour")});
 R.debut=un("data-dz-wa-espace-debut").value;R.mots=un("data-dz-wa-espace-mots").value;
 var sel=un("data-dz-wa-espace-modele");R.modele_dis=sel.disabled;R.modele_val=sel.value;
 R.modele_opts=sel.enfants.map(function(o){return o.value+"="+o.textContent});
 R.note=un("data-dz-wa-espace-modele-note").textContent;
 R.avert_cache=/display:none/.test(un("data-dz-wa-espace-avertissement").getAttribute("style")||"");
 R.enr_dis=un("data-dz-wa-espace-enregistrer").disabled;
 /* saisies */
 if(SCEN.saisir){
  un("data-dz-wa-espace-actif").checked=true;
  att("data-dz-wa-espace-role").forEach(function(n){n.checked=["faq","validation","commande"].indexOf(n.getAttribute("data-dz-wa-espace-role"))>=0});
  att("data-dz-wa-espace-jour").forEach(function(n){n.checked=["6","0","2"].indexOf(n.getAttribute("data-dz-wa-espace-jour"))>=0});
  un("data-dz-wa-espace-debut").value="22:00";un("data-dz-wa-espace-fin").value="06:00";un("data-dz-wa-espace-fuseau").value=" Europe/Brussels ";
  un("data-dz-wa-espace-hors-horaires").value="Nous revenons demain.";un("data-dz-wa-espace-plafond-jour").value=" 7 ";un("data-dz-wa-espace-plafond-redactions").value="12";
  un("data-dz-wa-espace-mots").value=" conseiller, ,humain\nurgent ";un("data-dz-wa-espace-plafond-mois").value="250";
  un("data-dz-wa-espace-marche").value=" 32 ";
  if(SCEN.modele!==undefined)sel.value=SCEN.modele;
  if(SCEN.plafondTexte)un("data-dz-wa-espace-plafond-jour").value="beaucoup";
 }
 if(SCEN.auto){var m=un("data-dz-wa-espace-mode");m.value="auto";m.declencher("change");await attendre(20);
   R.mode_apres=un("data-dz-wa-espace-mode").value;
   R.avert_cache_apres=/display:none/.test(un("data-dz-wa-espace-avertissement").getAttribute("style")||"")}
 R.erreur_avant=un("data-dz-wa-espace-erreur").textContent;
 if(SCEN.enregistrer){un("data-dz-wa-espace-enregistrer").declencher("click");await attendre(40)}
 R.put=appels.filter(function(a){return a.m==="PUT"}).map(function(a){return a.c});
 R.msg=un("data-dz-wa-espace-msg").textContent;R.err=un("data-dz-wa-espace-erreur").textContent;
 R.confirmations=confirmations;
 un("data-dz-wa-espace-fermer").declencher("click");await attendre(5);
 R.ferme=fini&&att("data-dz-wa-espace-boite").length===0;
 process.stdout.write(JSON.stringify(R));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""


def panneau(**scen):
    if not NODE or not MODULE.exists():
        return {}
    return node(AIDE.PRELUDE_DZT + "\n" + FAUX_DOM
                + SONDE_MOD.replace("__REGLAGES__", json.dumps(REGLAGES)).replace("__SCEN__", json.dumps(scen))
                .replace("__MODULE__", MODULE.read_text("utf-8")))


A = panneau(dialogue="non")
check("4.1 le module s'exécute sous node et ouvre UNE boîte", A.get("boite") == 1 and "erreur" not in A,
      str(A.get("erreur", A))[:800])
check("4.2 lectures : réglages, espaces (titre), comptes de l'espace, modèles du PREMIER numéro relié",
      lambda: set(A["lectures"]) == {"GET /api/espaces/esp_a/whatsapp/reglages", "GET /api/espaces?archives=true",
                                     "GET /api/comptes?espace=esp_a", "GET /api/whatsapp/c_wa/modeles?espace=esp_a"},
      str(A.get("lectures")))
check("4.3 le titre nomme l'espace", lambda: "Boulangerie" in (A.get("titre") or ""), str(A.get("titre")))
check("4.4 le formulaire montre les réglages lus", A.get("actif") is False and A.get("mode") == "brouillon"
      and A.get("roles") == ["faq"] and A.get("jours") == ["0", "1", "2", "3", "4"] and A.get("debut") == "09:00"
      and A.get("mots") == "humain" and A.get("enr_dis") is False, str(A))
check("4.5 modèles : UTILITY approuvés à une variable au plus, rien de rangé -> « Aucun modèle »",
      A.get("modele_dis") is False and A.get("modele_val") == ""
      and [o.split("=", 1)[1] for o in A.get("modele_opts", [])][1:] == ["valid_post (fr)", "rappel (en_US)"], str(A.get("modele_opts")))
check("4.6 en brouillon, la phrase d'avertissement est cachée ; « Fermer » ferme et résout", A.get("avert_cache") is True
      and A.get("ferme") is True, str(A))

S1 = panneau(dialogue="non", saisir=True, modele="1", enregistrer=True)
ATTENDU = {"plafond_mois": 250, "marche_defaut": "32",
           "agent": {"actif": True, "mode": "brouillon", "roles": ["faq", "commande", "validation"],
                     "horaires": {"jours": [0, 2, 6], "debut": "22:00", "fin": "06:00", "fuseau": "Europe/Brussels"},
                     "message_hors_horaires": "Nous revenons demain.", "plafond_jour_contact": 7,
                     "plafond_redactions_jour": 12, "mots_humain": ["conseiller", "humain", "urgent"],
                     "modele_validation": {"nom": "rappel", "langue": "en_US"}}}
check("4.7 PUT au format EXACT (entiers, rôles dans l'ordre du serveur, jours triés, mots coupés et rognés, modèle {nom, langue})",
      S1.get("put") == [ATTENDU], json.dumps(S1.get("put"), ensure_ascii=False)[:600])
check("4.8 enregistré : le message le dit, aucune confirmation demandée en brouillon",
      S1.get("msg") in ("whatsapp.espace.enregistre", F("whatsapp.espace.enregistre")) and S1.get("confirmations") == []
      and not S1.get("err"), str(S1))

S2 = panneau(dialogue="non", auto=True, enregistrer=True)
check("4.9 auto REFUSÉ à la confirmation : le choix revient à « brouillon », le PUT dit brouillon",
      S2.get("mode_apres") == "brouillon" and len(S2.get("confirmations", [])) >= 1
      and [p["agent"]["mode"] for p in S2.get("put", [])] == ["brouillon"], str(S2)[:600])
c0 = (S2.get("confirmations") or [{}])[0]
check("4.10 la confirmation porte la phrase d'avertissement (argent et passage à un humain gardent les brouillons)",
      c0.get("m") in ("whatsapp.espace.auto_avertissement", F("whatsapp.espace.auto_avertissement"))
      and (c0.get("o") or {}).get("danger") is True, str(c0)[:400])
check("4.11 la phrase dit bien que l'argent et le passage à un humain restent des brouillons (FR et EN)",
      "argent" in F("whatsapp.espace.auto_avertissement") and "brouillon" in F("whatsapp.espace.auto_avertissement")
      and "money" in AIDE._dico()["whatsapp.espace.auto_avertissement"]["en"])
S3 = panneau(dialogue="oui", auto=True, enregistrer=True)
check("4.12 auto CONFIRMÉ : le PUT dit auto, l'avertissement est visible, une seule confirmation",
      S3.get("mode_apres") == "auto" and S3.get("avert_cache_apres") is False and len(S3.get("confirmations", [])) == 1
      and [p["agent"]["mode"] for p in S3.get("put", [])] == ["auto"], str(S3)[:600])
S4 = panneau(dialogue="absent", auto=True, enregistrer=True)
check("4.13 sans boîte de dialogue : jamais auto (choix ramené à brouillon, message), PUT brouillon",
      S4.get("mode_apres") == "brouillon" and [p["agent"]["mode"] for p in S4.get("put", [])] == ["brouillon"]
      and S4.get("erreur_avant") in ("whatsapp.espace.auto_sans_dialogue", F("whatsapp.espace.auto_sans_dialogue")), str(S4)[:600])
DEJA_AUTO = json.loads(json.dumps(REGLAGES)); DEJA_AUTO["agent"]["mode"] = "auto"
S5 = panneau(dialogue="non", reglages=DEJA_AUTO, enregistrer=True)
check("4.14 déjà en auto côté serveur : pas de nouvelle confirmation pour enregistrer", S5.get("mode") == "auto"
      and S5.get("confirmations") == [] and [p["agent"]["mode"] for p in S5.get("put", [])] == ["auto"], str(S5)[:500])

S6 = panneau(dialogue="non", sansNumero=True, enregistrer=True)
check("4.15 sans numéro relié : champ grisé et vide, note, aucun appel aux modèles, PUT SANS modele_validation",
      S6.get("modele_dis") is True and S6.get("modele_val") == ""
      and S6.get("note") in ("whatsapp.espace.modele_sans_numero", F("whatsapp.espace.modele_sans_numero"))
      and not any("/modeles" in x for x in S6.get("lectures", []))
      and len(S6.get("put", [])) == 1 and "modele_validation" not in S6["put"][0]["agent"], str(S6)[:600])
S7 = panneau(dialogue="non", modeles502=True, enregistrer=True)
check("4.16 lecture des modèles en échec : note avec le détail, champ grisé, PUT sans modele_validation",
      S7.get("modele_dis") is True and "Kapso injoignable" in (S7.get("note") or "")
      and len(S7.get("put", [])) == 1 and "modele_validation" not in S7["put"][0]["agent"], str(S7)[:600])
S8 = panneau(dialogue="non", comptes500=True)
check("4.17 lecture des comptes en échec : le formulaire s'ouvre quand même, champ grisé, note",
      S8.get("modele_dis") is True and "panne" in (S8.get("note") or "") and S8.get("enr_dis") is False, str(S8)[:500])
RANGE = json.loads(json.dumps(REGLAGES)); RANGE["agent"]["modele_validation"] = {"nom": "ancien", "langue": "fr"}
S9 = panneau(dialogue="non", reglages=RANGE, enregistrer=True)
check("4.18 un modèle rangé absent de la liste reste proposé et choisi : il n'est pas effacé en silence",
      S9.get("modele_val") == "0" and (S9.get("modele_opts") or ["", ""])[1].endswith("ancien (fr)")
      and [p["agent"].get("modele_validation") for p in S9.get("put", [])] == [{"nom": "ancien", "langue": "fr"}], str(S9)[:600])
S10 = panneau(dialogue="non", put400=True, enregistrer=True)
check("4.19 refus 400 : le message du SERVEUR est montré", "heure de début invalide" in (S10.get("err") or ""),
      str(S10.get("err")))
S11 = panneau(dialogue="non", saisir=True, plafondTexte=True, enregistrer=True)
check("4.20 une saisie qui n'est pas un entier part telle quelle (le serveur la refuse) : jamais de conversion silencieuse",
      [p["agent"]["plafond_jour_contact"] for p in S11.get("put", [])] == ["beaucoup"], str(S11.get("put"))[:300])
SRC = MODULE.read_text("utf-8") if MODULE.exists() else ""
check("4.21 l'API publique : window.__dzWhatsappEspace = { ouvrir }", "window.__dzWhatsappEspace = { ouvrir: ouvrir };" in SRC)

# ── [5] livraison ───────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[5] livraison")
check("5.1 shared == dist, octet pour octet", MODULE.exists() and (DI / MODULE.name).exists()
      and MODULE.read_bytes() == (DI / MODULE.name).read_bytes())
HTML = (REPO / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
BALISE = '<script src="/shared/dz-whatsapp-espace.js"></script>'
check("5.2 index.html charge le module UNE fois, après dz-pour-qui.js",
      HTML.count(BALISE) == 1 and HTML.count("dz-whatsapp-espace.js") == 1
      and HTML.index('<script src="/shared/dz-pour-qui.js"></script>') < HTML.index(BALISE))
DICO = AIDE._dico()
cles = set(k for k in re.findall(r'"(whatsapp\.(?:espace|rail)\.[a-z0-9_]+)"', SRC + "\n" + B) if not k.endswith("_")) | {
    "whatsapp.espace.role_" + r for r in ("faq", "rendez_vous", "commande", "validation")} | {"whatsapp.page.titre"}
manq = sorted(k for k in cles if not (DICO.get(k, {}).get("fr") and DICO.get(k, {}).get("en")))
check(f"5.3 chaque clé employée existe en FR et en EN ({len(cles)} clés)", not manq, str(manq))
var = [k for k in cles if k in DICO and set(re.findall(r"\{(\w+)\}", DICO[k]["fr"])) != set(re.findall(r"\{(\w+)\}", DICO[k]["en"]))]
check("5.4 mêmes {variables} en FR et en EN", not var, str(var))
r = subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=str(REPO))
check("5.5 le dictionnaire assemblé est à jour", r.returncode == 0, (r.stdout + r.stderr)[-300:])
sans_com = re.sub(r"/\*.*?\*/", "", SRC, flags=re.S)
check("5.6 aucun confirm/alert/prompt natif ; aucun emoji", not re.search(r"(?<![\w.$])(?:window\.)?(?:confirm|alert|prompt)\(", sans_com)
      and not re.search("[\U0001F300-\U0001FAFF☀-➿]", SRC))

# ── [6] l'assistant ─────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[6] la connaissance de l'assistant")
from app.services import agent_aide as AA                 # noqa: E402
check("6.1 agent_aide.VUES : whatsapp entre avatarlive et settings", lambda: list(AA.VUES[-3:]) == ["avatarlive", "whatsapp", "settings"])
LOG = (SH / "dz-agent-logique.js").read_text("utf-8")
check("6.2 dz-agent-logique.js : la même liste", '"avatarlive", "whatsapp", "settings"]' in LOG)
ANC = {a["id"]: a for a in json.loads((REPO / "docs" / "agent" / "ancres.json").read_text("utf-8"))["ancres"]}
check("6.3 ancre rail.whatsapp (rail, libellé .dzNavLbl, partout, texte FR/EN)",
      lambda: ANC["rail.whatsapp"]["ecran"] == "whatsapp" and ANC["rail.whatsapp"]["libelle"] == ".dzNavLbl"
      and ANC["rail.whatsapp"]["partout"] is True and ANC["rail.whatsapp"]["texte"] == {"fr": "WhatsApp", "en": "WhatsApp"})
AG = (SH / "dz-agent.js").read_text("utf-8")
check("6.4 LABS_CADRES interroge la page WhatsApp, qui charge le répondeur (après dz-plafonds.js)",
      lambda: "whatsapp" in re.search(r"const LABS_CADRES = /\^\\/\(([a-z0-9|]+)\)\\//;", AG).group(1).split("|")
      and (REPO / "frontend" / "whatsapp" / "index.html").read_text("utf-8").count(
          '<script type="module" src="/shared/dz-agent-cadre.js"></script>') == 1)
import catalogue_sources as CS, catalogue_partages as CP, catalogue_commun as CC    # noqa: E402
check("6.5 catalogue : la page est un lab lu (écran whatsapp, cadre /whatsapp/) ; le panneau est aux Réglages",
      CS.LABS.get("whatsapp") == ("whatsapp", "/whatsapp/") and "whatsapp" in CS.LABS_LUS
      and CC.ECRAN_DE_ZONE.get("whatsapp") == "whatsapp" and CC.ecran("whatsapp.espace.enregistrer") == "settings"
      and CP.PARTAGES.get("frontend/shared/dz-whatsapp-espace.js") == ("whatsapp.espace.",))
CAT = REPO / "docs" / "agent" / "catalogue"
COUV = json.loads((CAT / "_couverture.json").read_text("utf-8"))["ecrans"]
check("6.6 l'écran whatsapp est couvert", "whatsapp" in COUV)
fw = json.loads((CAT / "whatsapp.json").read_text("utf-8"))["fiches"] if (CAT / "whatsapp.json").exists() else []
fs = [x for x in json.loads((CAT / "settings.json").read_text("utf-8"))["fiches"] if x["id"].startswith("whatsapp.espace.")]
check(f"6.7 fiches de la page ({len(fw)}) et du panneau ({len(fs)}) rédigées FR/EN avec synonymes",
      len(fw) >= 10 and len(fs) >= 10 and all(x["etat"] == "redige" and x["role"]["fr"] and x["role"]["en"]
                                               and x["synonymes"]["fr"] and x["synonymes"]["en"] for x in fw + fs))
check("6.8 le bouton « Agent WhatsApp » de Réglages › Espaces a sa fiche sur les Réglages, sans cadre",
      any(x["id"] == "whatsapp.espace.ouvrir" and x["ecran"] == "settings" and x["cadre"] is None for x in fs))
AMD = (REPO / "docs" / "agent" / "AGENT.md").read_text("utf-8")
check("6.9 AGENT.md : l'écran WhatsApp ([ALLER:whatsapp]) et l'agent WhatsApp (brouillons, auto, Agent WhatsApp)",
      "[ALLER:whatsapp]" in AMD and "Agent WhatsApp" in AMD and "[POINT:rail.whatsapp]" in AMD)
check("6.10 AGENTS.md : 15 écrans, WhatsApp compris", "15 écrans" in (REPO / "AGENTS.md").read_text("utf-8")
      and "WhatsApp" in (REPO / "AGENTS.md").read_text("utf-8").split("## Architecture")[0])

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
