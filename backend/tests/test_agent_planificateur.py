# -*- coding: utf-8 -*-
"""t285 T9 (24/10/2026) — le mode « Agent Campagnes » du dialogue « Generate a marketing plan » du Planificateur.

Maillon de queue scripts/patch_bundle_dzagentplan.py (source frontend/patches/agent-plan.js, aplatie), posé APRÈS
dzrecette ; son inverse `avant_dzagentplan` (backend/tests/_i18n_l1_aide.py) est appelé EN TÊTE de `avant_dzrecette`.
[1] marqueur_x1             le marqueur une fois, aucun .bak_dzagentplan laissé ;
[2] aller_retour_exact      appliquer(defaire(B)) == B, avant_dzrecette défait dzagentplan d'abord ;
[3] comptes_figes           x.useState( 731, v2.8.0 ×4, DzTracks 181, et les comptes des bancs voisins, CRLF ;
[4] mode_rapide_intact      le texte d'origine du dialogue reste présent, Rapide par défaut ;
[5] bascule_monte_dzcampagnes  le sélecteur, le panneau, DzCampagnes.monter (rôle, espace, brief, contexte),
                            le démontage, l'absence tolérée, le rechargement du calendrier ;
[6] la source jouée par node : le premier message (brief + période en clair + document déposé), le montage ;
[7] textes : clés campagnes.plan.* à trois segments, FR puis EN, un même français = une seule traduction.
Run : & $PY tests/test_agent_planificateur.py   (depuis backend/)
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))

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
RAW = (ASSETS / "index-BEOJX8L5.js").read_bytes()
B = RAW.decode("utf-8")
try:
    import patch_bundle_dzagentplan as PM
except ImportError as e:
    PM = None
    check("0 le maillon patch_bundle_dzagentplan existe", False, repr(e))

MARKER = "/*__dzagentplan*/"
DICO_C = json.loads((REPO / "frontend" / "shared" / "i18n" / "campagnes.json").read_text(encoding="utf-8"))

print("\n[1] marqueur_x1")
check("1.1 marqueur ×1", B.count(MARKER) == 1, str(B.count(MARKER)))
check("1.2 aucun .bak_dzagentplan laissé", not list(ASSETS.glob("*.bak_dzagentplan")))
check("1.3 maillon de QUEUE après dzrecette : sa sonde compte le marqueur de dzrecette",
      lambda: PM and ("dzrecette", "/*__dzrecette*/", 1) in PM.SONDE_AMONT)

print("\n[2] aller_retour_exact")
if PM:
    check("2.1 appliquer(defaire(B)) == B", lambda: PM.appliquer(PM.defaire(B)) == B)
    check("2.2 defaire(B) n'a plus le marqueur ni le panneau", lambda: MARKER not in PM.defaire(B)
          and "DzAgentPlan" not in PM.defaire(B))
    import _i18n_l1_aide as AIDE
    # t307 (25/10/2026) : le maillon dzcanaux est posé APRÈS dzagentplan ; avant_dzagentplan le défait d'abord
    check("2.3 avant_dzagentplan existe et rend defaire(avant_dzcanaux(B))",
          lambda: AIDE.avant_dzagentplan(B) == PM.defaire(AIDE.avant_dzcanaux(B)))
    check("2.4 avant_dzrecette défait dzagentplan d'abord", lambda: MARKER not in AIDE.avant_dzrecette(B)
          and "/*__dzrecette*/" not in AIDE.avant_dzrecette(B))
    check("2.5 avant_dzagentplan sans marqueur : rendu tel quel",
          lambda: AIDE.avant_dzagentplan(PM.defaire(AIDE.avant_dzcanaux(B))) == PM.defaire(AIDE.avant_dzcanaux(B)))
    check("2.6 --check du maillon : déjà appliqué", lambda: "déjà appliqué" in subprocess.run(
        [sys.executable, str(REPO / "scripts" / "patch_bundle_dzagentplan.py"), "--check"], capture_output=True,
        text=True, encoding="utf-8").stdout)

print("\n[3] comptes_figes")
COMPTES = {"x.useState(": 731, "v2.8.0": 4, "DzTracks": 181, "__dzReopenQuick": 5, '"deepotus:quick-recipe"': 4,
           "await window.__dzDialogue.confirmer(": 30, "__dzCoutBlanc": 7, "Object.assign(__dzSrcLbl,": 2,
           "dzRunMaxTake()": 3, "__dzLibPicker": 11, "/*__dzrecette*/": 1}
for jeton, n in COMPTES.items():
    check(f"3 compte {jeton!r} = {n}", B.count(jeton) == n, str(B.count(jeton)))
check("3.x CRLF partout", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
if PM:
    check("3.y la source n'écrit jamais x.useState( (pas même en commentaire)", "x.useState(" not in PM.SOURCE.read_text("utf-8"))

print("\n[4] mode_rapide_intact")
i0 = B.find("function Um({onClose:e,onMaterialized:t,initialTab:n=\"generate\"}){")
i1 = B.find("function Hm(", i0)
UM = B[i0:i1] if 0 <= i0 < i1 else ""
check("4.0 le dialogue Um est trouvé", bool(UM))
for t in ('dzT("scheduler.plan.titre_generer")', 'dzT("scheduler.plan.titre_import")',
          'D.marketingPlan({prompt:a.trim(),days:d,posts_per_day:f,channels:y,language:v,auto_materialize:!1})',
          'D.importPlan(S,{days:F,channels:y,language:v})', 'D.materializePlan(S,p,k)',
          '[["generate",dzT("scheduler.plan.generer")],["import",dzT("scheduler.plan.importer_doc")]]',
          'i==="generate"&&r.jsx(O,{label:dzT("scheduler.plan.brief")', 'dzT("scheduler.plan.arrivent_assistes")'):
    check(f"4 texte d'origine présent : {t[:60]}", UM.count(t) == 1, str(UM.count(t)))
if PM:
    check("4.a chaque ancre d'origine reste entière, une fois (P1 : l'en-tête de Um)", all(B.count(a) == 1 for i, (a, _) in enumerate(PM.PAIRES) if i in (1, 3))
          and B.count(PM._UM) == 1)
    check("4.b les paires n'ajoutent que du texte (P2, P4 : l'ancre entière ; P1 : le crochet après l'en-tête ; P3 : après « div »)",
          all(rp.count(a) == 1 for i, (a, rp) in enumerate(PM.PAIRES) if i in (1, 3)) and PM.PAIRES[0][1].endswith(
              PM._UM + "var __dzAP=__dzAgentPlanMode();const o=bt(),") and PM.PAIRES[0][0] == PM._UM + "const o=bt(),")
check("4.c Rapide est le mode par défaut", 'return US("rapide");' in B)
check("4.d le crochet du mode est appelé en tête du dialogue",
      UM.startswith('function Um({onClose:e,onMaterialized:t,initialTab:n="generate"}){var __dzAP=__dzAgentPlanMode();const o=bt(),'))

print("\n[5] bascule_monte_dzcampagnes")
check("5.1 le sélecteur Rapide / Agent Campagnes dans l'en-tête du dialogue",
      'r.jsx(DzAgentPlanBascule,{mode:__dzAP[0],choisir:' in UM
      and 'dzT("campagnes.plan.rapide")' not in UM and '"campagnes.plan.rapide"' in B and '"campagnes.plan.agent"' in B)
check("5.2 en mode Agent, les onglets Générer / Importer sont masqués", '__dzAP[0]==="agent"?null:r.jsx("div",{style:{display:"flex",gap:2' in UM)
check("5.3 en mode Agent, le corps devient le panneau DzAgentPlan (brief, période, fermeture)",
      'r.jsxs("div"&&__dzAP[0]==="agent"?DzAgentPlan:"div",{...(__dzAP[0]==="agent"?{brief:a,setBrief:l,jours:d,setJours:u,'
      'debut:p,setDebut:h,fermer:e}:{}),className:"scroll"' in UM)
check("5.3b le remplacement G1 de dzglyph qui couvre l'en-tête du dialogue reste entier (scripts/dzglyph_paires.json)",
      lambda: B.count('L},S))}),r.jsx(se,{name:"dz-action-fermer",onClick:e})]}),r.jsxs("') == 1)
check("5.3c le maillon i18nfix garde son remplacement unique (placeholder du brief)",
      B.count('placeholder:dzT("scheduler.plan.brief_exemple"),') == 1)
check("5.4 en mode Agent, le pied (Générer, Ajouter au calendrier) est masqué",
      '__dzAP[0]==="agent"?null:r.jsxs("div",{style:{padding:"12px 18px",borderTop:' in UM)
check("5.5 window.DzCampagnes.monter, rôle campagnes, contexte planificateur, espace et brief",
      'C.monter(hote,opts)' in B and 'var C=window.DzCampagnes;' in B
      and '{role:"campagnes",espace_id:o.espace_id||void 0,brief:o.brief||"",contexte:"planificateur"}' in B)
check("5.6 démonté au démontage du panneau (changement de mode, fermeture du dialogue)", "h.demonter();" in B)
check("5.7 absence de DzCampagnes tolérée (message dzT)", 'if(!hote||!C||typeof C.monter!=="function")return null;' in B
      and 'dzT("campagnes.plan.absent")' in B)
check("5.8 les espaces non archivés, l'actif par défaut", 'fetch("/api/espaces")' in B and "!z.archive" in B
      and "d&&d.actif" in B)
check("5.9 les brouillons : à dz-campagnes-brouillons, deepotus:schedule-reload (l'écouteur du Planificateur)",
      'window.addEventListener("dz-campagnes-brouillons",surBrouillons)' in B
      and 'window.removeEventListener("dz-campagnes-brouillons",surBrouillons)' in B
      and 'new CustomEvent("deepotus:schedule-reload")' in B
      and 'window.addEventListener("deepotus:schedule-reload",R)' in B)
check("5.10 le document : la conversation naît, puis POST /depot (multipart fichier)",
      'fetch("/api/agent/campagnes/",{method:"POST"' in B and '"/depot",{method:"POST",body:fd}' in B
      and 'fd.append("fichier",fichier' in B)
check("5.12 M3 : passer en Agent ne vide plus le plan Rapide (s(\"generate\") seul)",
      'choisir:function(v){v==="agent"&&s("generate");__dzAP[1](v)}' in UM and "N(null),H(\"\"));__dzAP" not in UM)
check("5.13 l'activation de la coque exposée à la carte des brouillons (window.__dzEspActiver = dzEspActiver)",
      'try{if(typeof dzEspActiver==="function")window.__dzEspActiver=dzEspActiver;}catch(e){}' in B and B.count("function dzEspActiver(") == 1)
check("5.14 P3 : l'hôte a une hauteur fixe (le composant remplit, champ en bas)", 'flex:"0 0 auto",minHeight:360,height:"min(62vh,560px)"' in B)
check("5.15 M4 : le premier message ne nomme aucun outil interne", lambda: "lire_document" not in DICO_C["campagnes.plan.document_message"]["fr"] + DICO_C["campagnes.plan.document_message"]["en"])
check("5.16 P5 : en mode Agent, un clic sur le fond ne ferme pas le dialogue (la croix reste)",
      UM.count('r.jsx("div",{onClick:__dzAP[0]==="agent"?void 0:e,style:{position:"fixed",inset:0,zIndex:80,') == 1
      and 'r.jsx("div",{onClick:e,style:{position:"fixed",inset:0,zIndex:80,' not in UM and 'r.jsx(se,{name:"dz-action-fermer",onClick:e})' in UM)
check("5.17 la reprise : bouton « Reprendre la conversation » et cid gardé par espace en sessionStorage",
      'dzT("campagnes.plan.reprendre")' in B and 'window.sessionStorage.setItem(__dzAgentPlanCle(e),String(cid))' in B)
check("5.11 aucun bouton publier ni /fire dans le maillon", lambda: PM and "/fire" not in PM.AIDES
      and "scheduled" not in PM.AIDES and "publier" not in PM.AIDES)

print("\n[6] la source jouée par node")
node = shutil.which("node")
if not node or not PM:
    check("6.0 node disponible", False, "node introuvable")
else:
    js = r"""
const out = {};
const dzT = (k, v) => k + (v ? JSON.stringify(v) : "");
const window = { evts: [], dispatchEvent(e) { this.evts.push(e.type); } };
function CustomEvent(t) { this.type = t; }
const x = {}, r = {};
""" + PM.AIDES + r"""
out.b1 = __dzAgentPlanBrief("Lancement du staking", "2026-11-02", 7, null);
out.b2 = __dzAgentPlanBrief("", "2026-11-02", 7, "plan.txt");
out.b3 = __dzAgentPlanBrief("  brief seul  ", "", 0, null);
out.absent = __dzAgentPlanMonter({}, { espace_id: "e1", brief: "b" });
let vu = null;
window.DzCampagnes = { monter(h, o) { vu = o; return { demonter() {}, cid() { return null; }, recharger() {} }; } };
out.monte = !!__dzAgentPlanMonter({}, { espace_id: "e1", brief: "b", cid: "c1" });
out.opts = vu;
__dzAgentPlanRecharger();
out.evts = window.evts;
/* un rendu à blanc : crochets simulés, aucune référence manquante */
const K = "K", O = "O", re = "re";
x.useState = (v) => [v, () => {}]; x.useEffect = () => {}; x.useRef = (v) => ({ current: v });
r.jsx = (t, p) => ({ t, p }); r.jsxs = r.jsx; r.Fragment = "F";
const texte = (n) => n == null || n === false ? "" : typeof n === "string" ? n : Array.isArray(n) ? n.map(texte).join("|") : n.p ? texte(n.p.children) + (n.p.label ? "|" + n.p.label : "") : "";
const pan = DzAgentPlan({ brief: "b", setBrief() {}, jours: 7, setJours() {}, debut: "2026-11-02", setDebut() {}, fermer() {} });
out.panneau = pan.p["data-dzagentplan"];
out.panneau_texte = texte(pan);
const bas = DzAgentPlanBascule({ mode: "rapide", choisir() {} });
out.bascule = bas.p.children.map((c) => c.p["data-dzagentplan-mode"] + ":" + c.p["aria-pressed"]);
out.mode = __dzAgentPlanMode();
const bouton = (n) => { const a = []; const v = (m) => { if (!m || typeof m !== "object") return; if (Array.isArray(m)) return m.forEach(v); if (m.p && m.p["data-dzagentplan-demarrer"] === "") a.push(m.p); if (m.p) { v(m.p.children); } }; v(n); return a[0]; };
out.demarrer_desactive_en_chargement = bouton(pan).disabled === true;
/* les brouillons : un effet joué pour de bon, la liste des espaces lue, l'évènement de la carte rejoué */
async function scenario(espaceBrouillons) {
  const ecoute = {}, etats = [], ferme = { n: 0 };
  window.addEventListener = (t, f) => { ecoute[t] = f; }; window.removeEventListener = () => {};
  globalThis.fetch = async (u) => ({ ok: true, json: async () => ({ espaces: [{ id: "e1", nom: "A" }, { id: "e2", nom: "B" }], actif: "e1" }) });
  x.useState = (v) => [v, (w) => etats.push(w)]; x.useEffect = (f, deps) => { if (deps && deps.length === 0) f(); };
  DzAgentPlan({ brief: "", setBrief() {}, jours: 7, setJours() {}, debut: "", setDebut() {}, fermer() { ferme.n++; } });
  await new Promise((r) => setTimeout(r, 20));
  ecoute["dz-campagnes-brouillons"]({ detail: { espace_id: espaceBrouillons } });
  await new Promise((r) => setTimeout(r, 20));
  return { ferme: ferme.n, etats: etats.filter((e) => typeof e === "string") };
}
(async () => {
  window.evts = [];
  out.actif = await scenario("e1");
  out.inactif = await scenario("e2");
  out.evts2 = window.evts.slice();
  /* la ligne « pas l'espace actif » sous le sélecteur : un rendu avec choix e2, actif e1 */
  let i = 0; const vals = [[{ id: "e1", nom: "A" }, { id: "e2", nom: "Marque B" }], "e2", null, null, "", false, "e1"];
  x.useState = (v) => [vals[i++], () => {}]; x.useEffect = () => {};
  out.ligne_inactif = texte(DzAgentPlan({ brief: "", setBrief() {}, jours: 7, setJours() {}, debut: "", setDebut() {}, fermer() {} }));
  i = 0; vals[1] = "e1";
  out.ligne_actif = texte(DzAgentPlan({ brief: "", setBrief() {}, jours: 7, setJours() {}, debut: "", setDebut() {}, fermer() {} }));
  /* relecture de branche : le cid gardé par espace, le bouton « Reprendre », l'espace de repli des brouillons */
  const ss = new Map(); window.sessionStorage = { getItem: (k) => (ss.has(k) ? ss.get(k) : null), setItem: (k, v) => ss.set(k, String(v)), removeItem: (k) => ss.delete(k) };
  const P = { brief: "", setBrief() {}, jours: 7, setJours() {}, debut: "", setDebut() {}, fermer() {} };
  i = 0; vals[1] = "e1"; out.sans_reprise = texte(DzAgentPlan(P));
  __dzAgentPlanGarder("e1", "c7");
  i = 0; out.avec_reprise = texte(DzAgentPlan(P));
  i = 0; vals[1] = "e2"; out.autre_espace = texte(DzAgentPlan(P));
  out.cle = [...ss.keys()];
  /* le montage d'une conversation garde son cid sous son espace ; la reprise monte DzCampagnes sur ce cid */
  let vu = null; window.DzCampagnes = { monter(h, o) { vu = o; return { demonter() {} }; } };
  const vals2 = [[{ id: "e1", nom: "A" }, { id: "e3", nom: "C" }], "e3", null, { cid: "c9", espace: "e3", brief: "" }, "", false, "e1"];
  let j = 0; x.useState = (v) => [vals2[j++], () => {}]; x.useRef = (v) => ({ current: v === null ? {} : v });
  x.useEffect = (f, d) => { if (d && d.length === 1) f(); };
  DzAgentPlan(P);
  out.monte_reprise = vu; out.garde_c9 = window.sessionStorage.getItem("dzAgentPlan.cid:e3");
  /* brouillons sans espace dans l'évènement : l'espace de la conversation montée (e3, pas l'actif e1) */
  const ecoute = {}; let ferme = 0, etats = [];
  window.addEventListener = (t, f) => { ecoute[t] = f; };
  j = 0; x.useState = (v) => [vals2[j++], (w) => etats.push(w)]; x.useEffect = (f, d) => { if (d && d.length === 0) f(); };
  DzAgentPlan(Object.assign({}, P, { fermer() { ferme++; } }));
  await new Promise((r) => setTimeout(r, 20));
  ecoute["dz-campagnes-brouillons"]({ detail: { espace_id: null } });
  await new Promise((r) => setTimeout(r, 20));
  out.repli = { ferme, inactif: etats.includes("campagnes.plan.brouillons_inactif") };
  console.log(JSON.stringify(out));
})();
"""
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzt285t9_"))
    (d / "t.js").write_text(js, encoding="utf-8")
    p = subprocess.run([node, str(d / "t.js")], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:                                       # noqa: BLE001
        o = {}
    check("6.0 la source aplatie se lit et tourne sous node", bool(o), p.stderr[:300])
    check("6.1 brief + période en clair (début, nombre de jours)",
          o.get("b1") == 'Lancement du staking\n\ncampagnes.plan.periode_message{"debut":"2026-11-02","n":7}', repr(o.get("b1")))
    check("6.2 sans brief : période et document déposé (nom gardé par /depot)",
          o.get("b2") == 'campagnes.plan.periode_message{"debut":"2026-11-02","n":7}\ncampagnes.plan.document_message{"nom":"plan.txt"}',
          repr(o.get("b2")))
    check("6.3 brief seul, rogné", o.get("b3") == "brief seul", repr(o.get("b3")))
    check("6.4 DzCampagnes absent : null, rien ne casse", o.get("absent") is None)
    check("6.5 monté avec rôle, espace, brief, contexte, cid", o.get("monte") is True and o.get("opts", {}) ==
          {"role": "campagnes", "espace_id": "e1", "brief": "b", "contexte": "planificateur", "cid": "c1"}, json.dumps(o.get("opts")))
    check("6.6 le rechargement émet deepotus:schedule-reload", o.get("evts") == ["deepotus:schedule-reload"], str(o.get("evts")))
    check("6.7 le panneau se rend (avant montage) : espace, brief, période, document, bouton", o.get("panneau") == "panneau"
          and all(k in o.get("panneau_texte", "") for k in ("campagnes.plan.espace", "scheduler.plan.brief",
                  "scheduler.plan.date_debut", "scheduler.plan.jours", "campagnes.plan.joindre", "campagnes.plan.demarrer")),
          o.get("panneau_texte", "")[:300])
    check("6.8 la bascule : Rapide pressé par défaut, Agent à côté ; le crochet rend « rapide »",
          o.get("bascule") == ["rapide:true", "agent:false"] and (o.get("mode") or [None])[0] == "rapide", str(o.get("bascule")))
    check("6.9 M2 : « Ouvrir la conversation » désactivé tant que la liste des espaces n'est pas là",
          o.get("demarrer_desactive_en_chargement") is True)
    check("6.10 brouillons dans l'espace ACTIF : calendrier rechargé, dialogue fermé", (o.get("actif") or {}).get("ferme") == 1
          and "campagnes.plan.brouillons_inactif" not in (o.get("actif") or {}).get("etats", []), json.dumps(o.get("actif")))
    check("6.11 brouillons HORS espace actif : le dialogue reste ouvert et le dit (pas de fermeture silencieuse)",
          (o.get("inactif") or {}).get("ferme") == 0 and "campagnes.plan.brouillons_inactif" in (o.get("inactif") or {}).get("etats", []),
          json.dumps(o.get("inactif")))
    check("6.12 les deux cas rechargent le calendrier", (o.get("evts2") or []).count("deepotus:schedule-reload") == 2, str(o.get("evts2")))
    check("6.13 espace choisi non actif : la ligne sous le sélecteur (avec son nom)",
          'campagnes.plan.espace_inactif{"nom":"Marque B"}' in o.get("ligne_inactif", ""), o.get("ligne_inactif", "")[:300])
    check("6.15 sans conversation gardée : pas de bouton « Reprendre »", "campagnes.plan.reprendre" not in o.get("sans_reprise", "x"))
    check("6.16 un cid gardé pour l'espace choisi : le bouton « Reprendre la conversation »", "campagnes.plan.reprendre" in o.get("avec_reprise", ""))
    check("6.17 …seulement pour CET espace (clé dzAgentPlan.cid:<espace>)", "campagnes.plan.reprendre" not in o.get("autre_espace", "x")
          and o.get("cle") == ["dzAgentPlan.cid:e1"], str(o.get("cle")))
    check("6.18 la reprise remonte DzCampagnes sur le cid gardé, et le montage garde ce cid sous son espace",
          (o.get("monte_reprise") or {}).get("cid") == "c9" and o.get("garde_c9") == "c9", json.dumps(o.get("monte_reprise")))
    check("6.19 M5 : évènement sans espace -> l'espace de la conversation (non actif) : le dialogue reste ouvert",
          o.get("repli") == {"ferme": 0, "inactif": True}, json.dumps(o.get("repli")))
    check("6.14 espace choisi actif : pas de ligne", "campagnes.plan.espace_inactif" not in o.get("ligne_actif", "x"), o.get("ligne_actif", "")[:200])

print("\n[7] textes")
I18N = REPO / "frontend" / "shared" / "i18n"
DICO = json.loads((I18N / "campagnes.json").read_text(encoding="utf-8"))
TOUT = {}
for f in sorted(I18N.glob("*.json")):
    TOUT.update(json.loads(f.read_text(encoding="utf-8")))
src = PM.AIDES if PM else ""
cles = set(re.findall(r'"(campagnes\.plan\.[a-z0-9_]+)"', src)) | set(re.findall(r'"(campagnes\.plan\.[a-z0-9_]+)"', B))
check("7.1 des clés campagnes.plan.* sont posées", len(cles) >= 8, str(len(cles)))
check("7.2 clés à trois segments", all(k.count(".") == 2 for k in cles), sorted(cles)[:5])
check("7.3 toutes traduites FR et EN dans campagnes.json", cles and all(
    k in DICO and DICO[k].get("fr") and DICO[k].get("en") for k in cles), sorted(k for k in cles if k not in DICO))
autres = set(re.findall(r'dzT\("([a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+)"', src)) - cles
check("7.4 les clés reprises existent déjà", all(k in TOUT for k in autres), sorted(k for k in autres if k not in TOUT))
par_fr = {}
for k, v in TOUT.items():
    if not v.get("contexte"):
        par_fr.setdefault(v["fr"], set()).add(v["en"])
check("7.5 un même français = une seule traduction (clés T9)", all(
    DICO[k].get("contexte") or len(par_fr.get(DICO[k]["fr"], ())) == 1 for k in cles if k in DICO),
    [k for k in cles if k in DICO and not DICO[k].get("contexte") and len(par_fr.get(DICO[k]["fr"], ())) != 1])
check("7.6 aucune chaîne visible en dur dans la source (children: littéral)", not re.search(r'children:"[^"]', src),
      re.findall(r'children:"[^"]{0,30}', src)[:3])
ASM = subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                     text=True, encoding="utf-8")
check("7.7 dictionnaire assemblé à jour", ASM.returncode == 0, ASM.stdout.strip())

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
