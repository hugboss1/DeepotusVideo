// t378 (30/10/2026, lot « Réglages : chemins & apparence ») — dz-chemins.js : les emplacements de Réglages › Chemins
// et leur ligne du Diagnostic, joués avec un fetch et un DOM simulés. Séries : liste vide puis remplie en FR et en EN
// (type, adresse, rôles, état du dernier test et espace libre) ; formulaire d'ajout (dossier puis SFTP, corps envoyé,
// mot de passe) ; modification (type figé, mot de passe jamais renvoyé, effacer) ; « Tester » d'une ligne, d'un
// brouillon et d'un enregistré au mot de passe gardé ; erreur du serveur affichée ; suppression derrière la
// confirmation ; Diagnostic absent sans emplacement, puis joignable / injoignable ; aucun innerHTML.
// Lancer : node frontend/shared/qa/chemins.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-chemins.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 400) : "")); };
const dort = (ms) => new Promise((r) => setTimeout(r, ms));
const INNER = [];

class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.children = []; this.attrs = {}; this.style = {}; this.ec = {};
                     this.parent = null; this.textContent = ""; this.disabled = false; this.value = ""; this.checked = false;
                     this.title = ""; this.placeholder = ""; }
  get firstChild() { return this.children[0] || null; }
  appendChild(c) { c.parent = this; this.children.push(c); return c; }
  removeChild(c) { this.children.splice(this.children.indexOf(c), 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(t, f) { this.ec[t] = f; }
  set innerHTML(_v) { INNER.push(this.tagName); }
}
const tous = (n, acc = []) => { acc.push(n); n.children.forEach((c) => tous(c, acc)); return acc; };
const texte = (n) => tous(n).map((x) => x.textContent).filter(Boolean).join(" | ");
const parAttr = (n, k, v) => tous(n).filter((x) => x.attrs && (v === undefined ? k in x.attrs : x.attrs[k] === v));

function monde(lang, reponses) {
  const appels = [];
  const dialogues = [];
  const w = {
    navigator: { language: lang }, localStorage: { getItem: () => lang, setItem() {} },
    document: { documentElement: { lang }, createElement: (t) => new Noeud(t),
                createTextNode: (t) => { const x = new Noeud("#text"); x.textContent = t; return x; }, addEventListener() {} },
    fetch: async (url, o) => {
      appels.push({ url, methode: (o && o.method) || "GET", corps: o && o.body ? JSON.parse(o.body) : undefined });
      const r = reponses(url, o || {});
      return { ok: r.ok !== false, status: r.status || 200, json: async () => r.corps };
    },
    __dzDialogue: { confirmer: async (m) => { dialogues.push(m); return w.__oui; } },
    __oui: false, setTimeout, clearTimeout, console, Promise, JSON, Date, Object,
  };
  w.window = w;
  w.globalThis = w;
  vm.createContext(w);
  vm.runInContext(DICO, w);
  w.dzLang = () => lang;
  w.dzT = (k, v) => {
    const e = w.DZ_I18N[k]; if (!e) return "⟦" + k + "⟧";
    return String(e[lang]).replace(/\{(\w+)\}/g, (m, x) => (v && v[x] != null ? String(v[x]) : m));
  };
  vm.runInContext(SRC, w);
  return { w, C: w.__dzChemins, appels, dialogues };
}

const NAS = { id: "nas", nom: "NAS du bureau", type: "dossier", roles: ["sauvegarde", "miroir"], adresse: "\\\\NAS\\partage",
              chemin: "\\\\NAS\\partage", dernier_test: { ok: true, code: "ecrit_lu", libre_octets: 12 * 1024 ** 3 } };
const SRV = { id: "serveur", nom: "Serveur", type: "sftp", roles: ["bibliotheque"], adresse: "sftp://olivia@nas.local/sauv",
              hote: "nas.local", port: 22, utilisateur: "olivia", dossier_distant: "/sauv", cle_ssh: "", secret_pose: true,
              dernier_test: null };

function serveur(liste, extra = () => null) {
  return (url, o) => {
    const x = extra(url, o);
    if (x) return x;
    if (url === "/api/reglages/chemins" && (o.method || "GET") === "GET")
      return { corps: { emplacements: liste, types: ["dossier", "sftp"], roles: ["sauvegarde", "miroir", "bibliotheque"],
                        sftp_disponible: true } };
    if (url.endsWith("/tester")) return { corps: { ok: false, code: "acces_refuse", libre_octets: null } };
    return { corps: {} };
  };
}

// ── 1. liste vide, FR ───────────────────────────────────────────────────────────────────────────────────────────
{
  const { C, appels } = monde("fr", serveur([]));
  const h = new Noeud("div");
  C.monter(h);
  await dort(5);
  const t = texte(h);
  ok("1.1 FR : titre, aide, liste vide, bouton d'ajout", t.includes("Emplacements") && t.includes("Aucun emplacement pour l'instant.")
     && t.includes("Ajouter un emplacement") && t.includes("rien ne change"), t);
  ok("1.2 une seule lecture", appels.length === 1 && appels[0].url === "/api/reglages/chemins", JSON.stringify(appels));
  C.monter(h);
  await dort(5);
  ok("1.3 monter deux fois ne relit pas (ref de React rappelée)", appels.length === 1);
}

// ── 2. liste remplie, FR puis EN ─────────────────────────────────────────────────────────────────────────────────
for (const [lang, att] of [["fr", ["NAS du bureau", "Dossier, lecteur réseau ou UNC", "Sauvegarde · Miroir des rendus",
                                    "Écriture et lecture réussies · 12,0 Go libres", "Serveur SFTP", "Source de bibliothèque",
                                    "Jamais testé", "Tester", "Modifier", "Supprimer"]],
                           ["en", ["Folder, network drive or UNC", "Backup · Render mirror",
                                    "Write and read succeeded · 12.0 GB free", "SFTP server", "Library source",
                                    "Never tested", "Test", "Edit", "Delete", "Locations", "Add a location"]]]) {
  const { C } = monde(lang, serveur([NAS, SRV]));
  const h = new Noeud("div");
  C.monter(h);
  await dort(5);
  const t = texte(h);
  const manque = att.filter((a) => !t.includes(a));
  ok(`2.1 ${lang} : lignes, rôles, état et espace libre`, !manque.length, manque.join(" / ") + " ⟸ " + t);
  ok(`2.2 ${lang} : aucune clé manquante`, !t.includes("⟦"), t);
  if (lang === "en") ok("2.3 en : aucun français restant", !/[éèàù«»]|Emplacement|Ajouter|Sauvegarde|Jamais/.test(t), t);
  ok(`2.4 ${lang} : une ligne par emplacement`, parAttr(h, "data-dz-chemin-id").length === 2);
}

// ── 3. ajout : dossier puis SFTP ─────────────────────────────────────────────────────────────────────────────────
{
  const liste = [];
  const { C, appels } = monde("fr", serveur(liste, (url, o) => (url === "/api/reglages/chemins" && o.method === "POST"
    ? (liste.push({ ...NAS, id: "neuf", nom: o.body && JSON.parse(o.body).nom }), { corps: { emplacement: {} } }) : null)));
  const h = new Noeud("div");
  const p = C.monter(h);
  await dort(5);
  parAttr(h, "data-dz-chemins-action", "ajouter")[0].ec.click();
  ok("3.1 le formulaire s'ouvre, type dossier par défaut", parAttr(h, "data-dz-chemins", "form").length === 1
     && parAttr(h, "data-dz-chemins-champ", "chemin").length === 1 && parAttr(h, "data-dz-chemins-champ", "hote").length === 0);
  const champ = (k) => parAttr(h, "data-dz-chemins-champ", k)[0];
  const saisir = (k, v) => { const c = champ(k); c.value = v; c.ec.input(); };
  saisir("nom", "Disque USB");
  saisir("chemin", "E:\\Sauvegardes");
  const roles = parAttr(h, "data-dz-chemins-role");
  ok("3.2 trois rôles cochables, avec leur aide", roles.length === 3 && texte(h).includes("Lu et indexé, jamais modifié."));
  roles[1].checked = true; roles[1].ec.change();
  roles[0].checked = true; roles[0].ec.change();
  parAttr(h, "data-dz-chemins-action", "tester-form")[0].ec.click();
  await dort(5);
  const tb = appels.find((a) => a.url === "/api/reglages/chemins/tester");
  ok("3.3 « Tester » avant d'enregistrer : brouillon envoyé, état affiché", tb && tb.corps.type === "dossier"
     && tb.corps.chemin === "E:\\Sauvegardes" && texte(h).includes("Accès refusé"), JSON.stringify(tb) + texte(h));
  parAttr(h, "data-dz-chemins-action", "enregistrer")[0].ec.click();
  await dort(5);
  const post = appels.find((a) => a.url === "/api/reglages/chemins" && a.methode === "POST");
  ok("3.4 enregistrer : corps exact (rôles dans l'ordre canonique)", post && JSON.stringify(post.corps) ===
     JSON.stringify({ nom: "Disque USB", roles: ["sauvegarde", "miroir"], type: "dossier", chemin: "E:\\Sauvegardes" }),
     JSON.stringify(post));
  ok("3.5 le formulaire se ferme et la liste est relue", !parAttr(h, "data-dz-chemins", "form").length
     && parAttr(h, "data-dz-chemin-id").length === 1 && p.form === null);
  // SFTP
  parAttr(h, "data-dz-chemins-action", "ajouter")[0].ec.click();
  const sel = champ("type"); sel.value = "sftp"; sel.ec.change();
  ok("3.6 SFTP : hôte, port, utilisateur, dossier distant, mot de passe, clé SSH", ["hote", "port", "utilisateur",
     "dossier_distant", "secret", "cle_ssh"].every((k) => champ(k)) && !champ("chemin") && champ("secret").attrs.type === "password");
  ok("3.7 le mot de passe dit qu'il va au coffre", texte(h).includes("Gardé dans le coffre") || champ("secret").placeholder.includes("coffre"));
  saisir("hote", "nas.local"); saisir("utilisateur", "olivia"); saisir("dossier_distant", "/sauv"); saisir("secret", "pw");
  parAttr(h, "data-dz-chemins-action", "enregistrer")[0].ec.click();
  await dort(5);
  const post2 = appels.filter((a) => a.url === "/api/reglages/chemins" && a.methode === "POST")[1];
  ok("3.8 SFTP enregistré avec le mot de passe tapé", post2 && post2.corps.type === "sftp" && post2.corps.secret === "pw"
     && post2.corps.port === "22" && !("chemin" in post2.corps), JSON.stringify(post2));
}

// ── 4. modification : type figé, mot de passe jamais renvoyé ────────────────────────────────────────────────────
{
  const { C, appels } = monde("fr", serveur([NAS, SRV], (url, o) => (url === "/api/reglages/chemins/serveur/tester"
    ? { corps: { ok: true, code: "joignable", libre_octets: 1024 ** 2 } } : null)));
  const h = new Noeud("div");
  C.monter(h);
  await dort(5);
  const ligne = parAttr(h, "data-dz-chemin-id", "serveur")[0];
  parAttr(ligne, "data-dz-chemins-action", "modifier")[0].ec.click();
  const champ = (k) => parAttr(h, "data-dz-chemins-champ", k)[0];
  ok("4.1 type figé, champs repris, mot de passe vide avec « enregistré »", champ("type").disabled && champ("hote").value === "nas.local"
     && champ("secret").value === "" && champ("secret").placeholder.includes("enregistré"), champ("secret").placeholder);
  parAttr(h, "data-dz-chemins-action", "tester-form")[0].ec.click();
  await dort(5);
  ok("4.2 « Tester » sans retaper le mot de passe : celui du coffre (route de l'enregistré)",
     appels.some((a) => a.url === "/api/reglages/chemins/serveur/tester") && !appels.some((a) => a.url === "/api/reglages/chemins/tester")
     && texte(h).includes("Joignable · 1,0 Mo libres"), texte(h));
  parAttr(h, "data-dz-chemins-action", "enregistrer")[0].ec.click();
  await dort(5);
  const m1 = appels.find((a) => a.url === "/api/reglages/chemins/serveur" && a.methode === "POST");
  ok("4.3 enregistrer : ni type, ni mot de passe, ni effacement", m1 && !("type" in m1.corps) && !("secret" in m1.corps)
     && !("effacer_secret" in m1.corps), JSON.stringify(m1));
  parAttr(parAttr(h, "data-dz-chemin-id", "serveur")[0], "data-dz-chemins-action", "modifier")[0].ec.click();
  const cb = champ("effacer_secret"); cb.checked = true; cb.ec.change();
  parAttr(h, "data-dz-chemins-action", "enregistrer")[0].ec.click();
  await dort(5);
  const m2 = appels.filter((a) => a.url === "/api/reglages/chemins/serveur" && a.methode === "POST")[1];
  ok("4.4 « Effacer le mot de passe » envoie effacer_secret", m2 && m2.corps.effacer_secret === true, JSON.stringify(m2));
}

// ── 5. tester une ligne, erreur, supprimer ───────────────────────────────────────────────────────────────────────
{
  const { w, C, appels, dialogues } = monde("en", serveur([NAS], (url, o) => (url === "/api/reglages/chemins" && o.method === "POST"
    ? { ok: false, status: 400, corps: { detail: "folder: absolute path required" } } : null)));
  const h = new Noeud("div");
  C.monter(h);
  await dort(5);
  parAttr(h, "data-dz-chemins-action", "tester")[0].ec.click();
  ok("5.1 « Tester » une ligne : « Testing… » le temps du test", texte(h).includes("Testing…"));
  await dort(5);
  ok("5.2 puis POST …/nas/tester et relecture", appels.some((a) => a.url === "/api/reglages/chemins/nas/tester" && a.methode === "POST")
     && appels.filter((a) => a.url === "/api/reglages/chemins").length === 2);
  parAttr(h, "data-dz-chemins-action", "ajouter")[0].ec.click();
  parAttr(h, "data-dz-chemins-action", "enregistrer")[0].ec.click();
  await dort(5);
  ok("5.3 refus du serveur affiché, formulaire gardé", texte(h).includes("Failed: folder: absolute path required")
     && parAttr(h, "data-dz-chemins", "form").length === 1, texte(h));
  parAttr(h, "data-dz-chemins-action", "annuler")[0].ec.click();
  parAttr(h, "data-dz-chemins-action", "supprimer")[0].ec.click();
  await dort(5);
  ok("5.4 supprimer : confirmation avec le nom, refus = rien d'envoyé", dialogues[0] && dialogues[0].includes("“NAS du bureau”")
     && !appels.some((a) => a.methode === "DELETE"), dialogues[0]);
  w.__oui = true;
  parAttr(h, "data-dz-chemins-action", "supprimer")[0].ec.click();
  await dort(5);
  ok("5.5 accord = DELETE", appels.some((a) => a.methode === "DELETE" && a.url === "/api/reglages/chemins/nas"));
}

// ── 6. Diagnostic ────────────────────────────────────────────────────────────────────────────────────────────────
{
  const { C, appels } = monde("fr", () => ({ corps: { emplacements: [] } }));
  const h = new Noeud("div");
  await C.diag(h);
  ok("6.1 aucun emplacement : le Diagnostic ne change pas", h.children.length === 0 && appels[0].url === "/api/reglages/chemins/verifier");
  await C.diag(h);
  ok("6.2 rappelé aussitôt par la ref : pas de seconde vérification", appels.length === 1);
}
{
  const ES = [{ id: "nas", nom: "NAS", adresse: "\\\\NAS\\p", ok: true, code: "joignable", libre_octets: 5 * 1024 ** 4 },
              { id: "srv", nom: "Serveur", adresse: "sftp://x@y/z", ok: false, code: "hote_introuvable", libre_octets: null }];
  for (const [lang, a, b] of [["fr", "Joignable · 5,0 To libres", "Hôte introuvable"], ["en", "Reachable · 5.0 TB free", "Host not found"]]) {
    const { C } = monde(lang, () => ({ corps: { emplacements: ES } }));
    const h = new Noeud("div");
    await C.diag(h);
    const t = texte(h);
    ok(`6.3 ${lang} : une ligne par emplacement, joignable / injoignable`, t.includes(a) && t.includes(b)
       && parAttr(h, "data-dz-chemin-id").length === 2 && t.includes(lang === "fr" ? "Emplacements" : "Locations"), t);
  }
}

ok("7.1 aucun innerHTML", INNER.length === 0, INNER.join(","));

if (echecs.length) { console.log(echecs.map((e) => "FAIL " + e).join("\n")); console.log(`${n - echecs.length}/${n}`); process.exit(1); }
console.log(`chemins.test.mjs : ${n}/${n} PASS`);
