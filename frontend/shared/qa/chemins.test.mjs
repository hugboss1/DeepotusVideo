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
  get parentNode() { return this.parent; }
  get parentElement() { return this.parent; }
  closest(sel) { for (let n = this; n; n = n.parent) if (n.tagName === sel.toUpperCase()) return n; return null; }
  querySelector(sel) {                            // t379 : « span.mono[title] » seulement (la ligne du Job Dock)
    return tous(this).slice(1).find((x) => sel === "span.mono[title]" && x.tagName === "SPAN"
      && (x.attrs.class || "").split(" ").includes("mono") && "title" in x.attrs) || null;
  }
  insertAdjacentElement(pos, e) {                 // t379 : « afterend » seulement (la galerie après les outils)
    const fr = this.parent.children; fr.splice(fr.indexOf(this) + 1, 0, e); e.parent = this.parent; return e;
  }
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
  ok("1.2 une lecture de la liste et une de l'état des rôles (t379)", appels.length === 2
     && appels.map((a) => a.url).sort().join(",") === "/api/reglages/chemins,/api/reglages/chemins/etat", JSON.stringify(appels));
  C.monter(h);
  await dort(5);
  ok("1.3 monter deux fois ne relit pas (ref de React rappelée)", appels.length === 2);
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

// ── 8. t379 : sauvegarde, index, galerie, import, Bibliothèque, Job Dock ─────────────────────────────────────────
const DISQUE = { ...NAS, id: "disque", nom: "Disque", roles: ["sauvegarde", "bibliotheque"] };
const ETAT = { emplacements: { disque: { sauvegarde: { derniere: "2026-10-30T03:00:00", ok: true },
                                         index: { quand: "2026-10-30T04:15:00", fichiers: 3 } } }, garder: 7 };
const INDEX = { quand: "2026-10-30T04:15:00", fichiers: [
  { chemin: "2025/plage.jpg", genre: "image", octets: 2048 }, { chemin: "clip.mp4", genre: "video", octets: 5 * 1024 ** 2 },
  { chemin: "voix.wav", genre: "audio", octets: 900 }] };
function serveur379(extra = () => null) {
  return serveur([DISQUE], (url, o) => {
    const x = extra(url, o); if (x) return x;
    if (url === "/api/reglages/chemins/etat") return { corps: ETAT };
    if (url === "/api/reglages/chemins/disque/index") return { corps: INDEX };
    if (url === "/api/reglages/chemins/disque/sauvegarder") return { corps: { ok: true, nom: "DeepotusVideo-Sauvegarde-2026-10-30-050000" } };
    if (url === "/api/reglages/chemins/disque/importer") return { corps: { filename: "empl_plage_abc123.jpg", genre: "image" } };
    if (url === "/api/reglages/chemins/disque/indexer") return { corps: { ok: true, ...INDEX, fichiers: INDEX.fichiers.slice(0, 1) } };
    return null;
  });
}
for (const [lang, att] of [["fr", ["Dernière sauvegarde : 30/10 03:00 (7 gardées)", "3 fichiers indexés · 30/10 04:15", "Sauvegarder maintenant", "Parcourir"]],
                           ["en", ["Last backup: 30/10, 03:00 (7 kept)", "3 files indexed · 30/10, 04:15", "Back up now", "Browse"]]]) {
  const { C } = monde(lang, serveur379());
  const h = new Noeud("div");
  C.monter(h);
  await dort(5);
  const t = texte(h);
  const manque = att.filter((a) => !t.includes(a));
  ok(`8.1 ${lang} : dernière sauvegarde, index, boutons des rôles`, !manque.length, manque.join(" / ") + " ⟸ " + t);
}
{
  const { C, appels } = monde("fr", serveur379());
  const h = new Noeud("div");
  C.monter(h);
  await dort(5);
  parAttr(h, "data-dz-chemins-action", "sauvegarder")[0].ec.click();
  ok("8.2 « Sauvegarder maintenant » : en cours, bouton grisé", texte(h).includes("Sauvegarde en cours…")
     && parAttr(h, "data-dz-chemins-action", "sauvegarder")[0].disabled);
  await dort(5);
  ok("8.3 POST …/disque/sauvegarder puis nom affiché", appels.some((a) => a.url === "/api/reglages/chemins/disque/sauvegarder" && a.methode === "POST")
     && texte(h).includes("Sauvegarde faite : DeepotusVideo-Sauvegarde-2026-10-30-050000"), texte(h));
  parAttr(h, "data-dz-chemins-action", "parcourir")[0].ec.click();
  await dort(5);
  const gal = parAttr(h, "data-dz-chemins", "galerie")[0];
  ok("8.4 « Parcourir » ouvre la galerie (lecture seule) et lit l'index", gal && texte(gal).includes("Source de bibliothèque (lecture seule)")
     && appels.some((a) => a.url === "/api/reglages/chemins/disque/index"), gal ? texte(gal) : "absente");
  const imgs = tous(gal).filter((x) => x.tagName === "IMG");
  ok("8.5 l'image vient de la route confinée, paresseuse et décorative", imgs.length === 1
     && imgs[0].attrs.src === "/api/reglages/chemins/disque/fichier?chemin=2025%2Fplage.jpg" && imgs[0].attrs.loading === "lazy"
     && imgs[0].attrs.alt === "", JSON.stringify(imgs.map((i) => i.attrs)));
  ok("8.6 vidéo et son : leur genre, tailles lisibles", texte(gal).includes("Vidéo") && texte(gal).includes("Son")
     && texte(gal).includes("5,0 Mo") && texte(gal).includes("2,0 Ko"), texte(gal));
  const imp = parAttr(gal, "data-dz-chemins-action", "importer");
  ok("8.7 « Importer » sur l'image et le son, pas sur la vidéo", imp.length === 2
     && !parAttr(parAttr(gal, "data-dz-chemins-fichier", "clip.mp4")[0], "data-dz-chemins-action", "importer").length);
  imp[0].ec.click();
  await dort(5);
  const pi = appels.find((a) => a.url === "/api/reglages/chemins/disque/importer");
  ok("8.8 import : POST {chemin}, « Dans la Bibliothèque »", pi && pi.corps.chemin === "2025/plage.jpg"
     && texte(parAttr(h, "data-dz-chemins", "galerie")[0]).includes("Dans la Bibliothèque"), JSON.stringify(pi));
  const filtre = parAttr(h, "data-dz-chemins-champ", "filtre")[0];
  filtre.value = "VOIX"; filtre.ec.input();
  ok("8.9 filtre par nom (sans casse)", parAttr(h, "data-dz-chemins-fichier").map((x) => x.attrs["data-dz-chemins-fichier"]).join() === "voix.wav");
  parAttr(h, "data-dz-chemins-action", "indexer")[0].ec.click();
  await dort(5);
  ok("8.10 « Indexer » : POST puis grille relue", appels.some((a) => a.url === "/api/reglages/chemins/disque/indexer" && a.methode === "POST"));
}
{
  const beaucoup = { quand: "2026-10-30T04:15:00", fichiers: Array.from({ length: 50 }, (_, i) => ({ chemin: `f${i}.png`, genre: "image", octets: 1 })) };
  const { C } = monde("en", () => ({ corps: beaucoup }));
  const h = new Noeud("div");
  await C.galerie(h, "disque");
  ok("8.11 48 vignettes puis « Show 2 more »", parAttr(h, "data-dz-chemins-fichier").length === 48 && texte(h).includes("Show 2 more"));
  parAttr(h, "data-dz-chemins-action", "plus")[0].ec.click();
  ok("8.12 ... qui affiche le reste", parAttr(h, "data-dz-chemins-fichier").length === 50);
}
{
  const { C } = monde("en", serveur379((url) => (url === "/api/reglages/chemins/disque/sauvegarder"
    ? { corps: { ok: false, code: "introuvable", detail: "" } } : null)));
  const h = new Noeud("div");
  C.monter(h);
  await dort(5);
  parAttr(h, "data-dz-chemins-action", "sauvegarder")[0].ec.click();
  await dort(5);
  ok("8.13 en : échec de sauvegarde dit dans la langue", texte(h).includes("Failed: Folder not found or unreachable"), texte(h));
}
{
  const etatEchec = { emplacements: { disque: { index: { quand: "2026-10-30T04:15:00", fichiers: 3, erreur: "acces_refuse" } } } };
  const { C } = monde("en", serveur379((url) => (url === "/api/reglages/chemins/etat" ? { corps: etatEchec } : null)));
  const h = new Noeud("div");
  C.monter(h);
  await dort(5);
  ok("8.13b en : un index en échec dit son motif", texte(h).includes("3 files indexed · 30/10, 04:15 · Failed: Access denied"), texte(h));
}
// la Bibliothèque : greffe du bouton « Emplacements » dans la rangée des outils
for (const [liste, attendu] of [[[], 0], [[DISQUE], 1]]) {
  const { C } = monde("fr", serveur(liste));
  const parent = new Noeud("div");
  const outils = parent.appendChild(new Noeud("div"));
  outils.attrs["data-dz"] = "outils-biblio";
  const rangee = outils.appendChild(new Noeud("div"));
  await C.greffer(outils);
  ok(`8.14 Bibliothèque : bouton « Emplacements » ${attendu ? "posé (une source)" : "absent (aucune source)"}`,
     parAttr(rangee, "data-dz-chemins-biblio").length === attendu);
  await C.greffer(outils);
  ok("8.15 greffé une seule fois", parAttr(rangee, "data-dz-chemins-biblio").length === attendu);
  if (attendu) {
    const b = parAttr(rangee, "data-dz-chemins-biblio")[0];
    b.ec.click();
    await dort(5);
    ok("8.16 clic : la galerie s'ouvre JUSTE après les outils", parent.children[1] && parent.children[1].attrs["data-dz-chemins"] === "biblio"
       && b.attrs["aria-pressed"] === "true" && texte(b) === "Emplacements");
    b.ec.click();
    ok("8.17 second clic : refermée", parent.children.length === 1 && b.attrs["aria-pressed"] === "false");
  }
}
{
  const { w, C, appels } = monde("fr", (url) => (url.endsWith("/j-1/reessayer") ? { corps: { status: "done" } }
    : { ok: false, status: 409, corps: { detail: "job : pas en échec" } }));
  const informe = [];
  w.__dzDialogue.informer = async (m) => { informe.push(m); };
  const b = new Noeud("button");
  const r = await C.reessayer("j-1", b);
  ok("8.18 Job Dock « Réessayer » : POST …/operations/j-1/reessayer", r && r.status === "done"
     && appels[0].url === "/api/reglages/chemins/operations/j-1/reessayer" && appels[0].methode === "POST" && !b.disabled);
  await C.reessayer("j-2", b);
  ok("8.19 refus dit à l'utilisateur", informe[0] === "Échec : job : pas en échec", informe[0]);
}

// le Job Dock : « Réessayer » d'un job « emplacement » intercepté en capture, les autres laissés au Dock
{
  const { w, C, appels } = monde("fr", (url) => {
    if (url.startsWith("/api/jobs?providers=emplacement")) return { corps: [{ job_id: "j-emp", relance: "emplacement" }, { job_id: "j-x", relance: null }] };
    if (url.endsWith("/operations/j-emp/reessayer")) return { corps: { status: "done" } };
    return { corps: {} };
  });
  const ligne = (id, titre) => {
    const row = new Noeud("div");
    const meta = row.appendChild(new Noeud("div"));
    const sp = meta.appendChild(new Noeud("span")); sp.attrs.class = "mono"; sp.attrs.title = id;
    const zone = row.appendChild(new Noeud("div"));
    const b = zone.appendChild(new Noeud("button")); b.attrs.title = titre;
    const svg = b.appendChild(new Noeud("svg"));
    return { row, b, svg };
  };
  const AIDE_REPLI = w.dzT("coque.file.reessayer_direct_aide");
  await C._dockRelire();
  ok("8.20 la liste des jobs « emplacement » en échec est lue", C._dock.ids["j-emp"] === 1 && !C._dock.ids["j-x"]
     && appels.some((a) => a.url === "/api/jobs?providers=emplacement&limit=100"));
  const ev = (cible) => ({ target: cible, arrete: 0, preventDefault() { this.arrete++; }, stopPropagation() { this.arrete++; },
                          stopImmediatePropagation() { this.arrete++; } });
  const a = ligne("j-emp", AIDE_REPLI);
  const e1 = ev(a.svg);
  ok("8.21 clic sur l'icône du bouton d'un job « emplacement » : intercepté avant React", C._surClicDock(e1) === true && e1.arrete === 3);
  await dort(5);
  ok("8.22 ... et rejoué par POST …/operations/j-emp/reessayer", appels.some((x) => x.url === "/api/reglages/chemins/operations/j-emp/reessayer"
     && x.methode === "POST"));
  const autre = ligne("j-motion", AIDE_REPLI);
  const e2 = ev(autre.b);
  ok("8.23 un job ordinaire (motion code) est laissé au Dock", C._surClicDock(e2) === false && e2.arrete === 0);
  const sansTitre = ligne("j-emp", "Copier l'id");
  ok("8.24 un autre bouton de la même ligne est laissé tel quel", C._surClicDock(ev(sansTitre.b)) === false);
}

ok("7.1 aucun innerHTML", INNER.length === 0, INNER.join(","));

if (echecs.length) { console.log(echecs.map((e) => "FAIL " + e).join("\n")); console.log(`${n - echecs.length}/${n}`); process.exit(1); }
console.log(`chemins.test.mjs : ${n}/${n} PASS`);
