/* Avatar live G4 (t165, 10/10/2026) — le DIRECT : la webcam du PC, transformée en temps réel par Decart Lucy 2.5.

   Le flux ne passe JAMAIS par le backend : navigateur ⇄ Decart en WebRTC (SDK @decartai/sdk 0.2.8, module LOCAL
   ./vendor, licences jointes). Le backend ne fait que : réserver la durée sous le plafond mensuel, frapper un jeton
   client de 60 s limité à lucy-2.5 (la clé permanente DECART_API_KEY ne quitte jamais le serveur), puis noter le
   réel à la fin. Decart COUPE la session à la durée réservée (maxSessionDuration) même si cette page plante ; la
   page coupe aussi d'elle-même : à la borne, à 60 s d'onglet caché, à la fermeture.

   À chaud : Personnage (image de référence) et décor (consigne) par `set()` — l'état COMPLET à chaque appel (doc
   Decart : set() remplace tout). Micro coché : la piste part avec la vidéo et revient CALÉE sur l'image transformée
   (le serveur retarde l'audio) — c'est l'appui de la voix en direct (G5). Enregistrer : MediaRecorder sur la sortie,
   déposé puis converti en rendu mp4 de l'application. */
import { createDecartClient, models } from "./vendor/decart-sdk-0.2.8.js";
import { ouvrirVoixDirect, retardVideoPossible } from "./voix-direct.js";

// G5 : retard appliqué à la vidéo envoyée pour rester calée sur la voix convertie = segment (500 ms) + latence
// de conversion + marge de gigue. MESURES du 10/10 avec le client httpx gardé (tools/voixbox/README.md, « Latence ») :
//   cloud (ElevenLabs) : médiane 969 ms, régime 920-1 330 ms -> 500 + 1 330 + 270 = 2 100 ms
//   local (Voixbox RVC, RTX 2080 Ti) : médiane 110 ms, max 120 ms -> 500 + 120 + 130 = 750 ms
const RETARD_MS = { cloud: 2100, local: 750 };

const API = "/api/avatar-live";
const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);   // G7 : frontend/shared/i18n/avatar.json
const $ = (id) => document.getElementById(id);
const st = { cat: null, rc: null, sess: null, local: null, debut: 0, minuterie: null, cache: null, rec: null, morceaux: [], vd: null };

function eur(v) { return window.__dzPlafonds ? window.__dzPlafonds.usd(v) : (Number(v) || 0).toFixed(2) + " $"; }
function hms(s) { s = Math.max(0, Math.round(s)); return T("avatar.temps.min_s", { m: Math.floor(s / 60), s: String(s % 60).padStart(2, "0") }); }
function dire(t, err) { const m = $("xMsg"); m.textContent = t || ""; m.classList.toggle("err", !!err); }
async function lire(r) {
  let j = null; try { j = await r.json(); } catch (e) { /* vide */ }
  if (!r.ok) { const d = j && j.detail; throw new Error(typeof d === "string" ? d : (d && d.dz_plafond && d.dz_plafond.message) || ("HTTP " + r.status)); }
  return j;
}

function etatCourant() {
  const pid = $("xPerso").value;
  const consigne = [($("xConsigne").value || "").trim(), st.pre ? st.pre.consigne : ""].filter(Boolean).join(", ");
  const prompt = (pid ? "Swap the person for the character in the reference image" : "Keep the person")
    + (consigne ? ", " + consigne : "") + ".";
  return { prompt, image: pid ? location.origin + API + "/personnages/" + pid + "/image/0" : null };
}

function majDevis() {
  if (!st.cat) return;
  const min = Number($("xDuree").value) || 5, rapide = $("xRapide").checked;
  const prix = rapide ? st.cat.prix_rapide_usd_s : st.cat.prix_usd_s;
  $("xDevis").textContent = T("avatar.direct.devis", { total: eur(prix * min * 60), min, par_min: eur(prix * 60) });
}

async function poserCle() {
  const v = ($("xCle").value || "").trim(); if (!v) return;
  try {
    await lire(await fetch("/api/settings/keys", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "DECART_API_KEY", value: v }) }));
    $("xCle").value = ""; await charger();
    dire(T("avatar.direct.cle_posee"));
  } catch (e) { dire(e.message, true); }
}

async function demarrer() {
  if (st.rc) return;
  $("xGo").disabled = true; dire(T("avatar.direct.ouverture_camera"));
  try {
    const [w, h] = $("xFormat").value === "9:16" ? [720, 1280] : [1280, 720];
    const voixChoix = $("xVoix").value;
    st.local = await navigator.mediaDevices.getUserMedia({ video: { width: w, height: h, frameRate: 30 },
      audio: voixChoix ? { echoCancellation: true, noiseSuppression: true, channelCount: 1 } : $("xMicro").checked });
    $("xLocal").srcObject = st.local;
    dire(T("avatar.direct.reservation"));
    const min = Number($("xDuree").value) || 5;
    st.sess = await lire(await fetch(API + "/sessions", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ personnage_id: $("xPerso").value || null, duree_s: min * 60, rapide: $("xRapide").checked,
        voix: !voixChoix ? null : voixChoix === "cloud" ? { moteur: "cloud" }
          : { moteur: "local", modele: voixChoix.slice(6), transpose: Number($("xTranspose").value) || 0 } }) }));
    let fluxEnvoye = st.local;
    if (st.sess.voix) {
      const sid = st.sess.session_id;
      st.vd = await ouvrirVoixDirect({
        camera: st.local, micro: st.local, retardMs: RETARD_MS[st.sess.voix.moteur],
        enVolMax: st.sess.voix.moteur === "local" ? 2 : 4,                // un seul GPU : inutile d'empiler
        convertir: async (buf) => {
          const r = await fetch(API + "/sessions/voix?session_id=" + encodeURIComponent(sid), { method: "POST", body: buf,
            headers: { "Content-Type": "application/octet-stream" } });
          if (!r.ok) { let d = ""; try { d = (await r.json()).detail; } catch (e) { /* binaire */ } throw new Error(d || ("HTTP " + r.status)); }
          return r.arrayBuffer();
        },
        surStats: (s) => {
          const l = s.latences.slice().sort((a, b) => a - b), med = l.length ? l[l.length >> 1] : 0;
          $("xVoixStats").textContent = T("avatar.direct.stats", { n: s.segments, ms: med, retard: s.retardMs })
            + (s.pertes ? T("avatar.direct.stats_pertes", { n: s.pertes }) + (s.erreur ? " (" + s.erreur + ")" : "") : "");
        },
      });
      fluxEnvoye = st.vd.flux;
      if (!st.vd.videoRetardee) dire(T("avatar.direct.pas_de_retard"), true);
    }
    const client = createDecartClient({ apiKey: st.sess.jeton });
    const e0 = etatCourant();
    dire(T("avatar.direct.connexion"));
    st.rc = await client.realtime.connect(fluxEnvoye, {
      model: models.realtime(st.sess.modele),
      speed: st.sess.rapide ? "fast" : undefined,
      mirror: $("xMiroir").checked,
      retries: 2,
      onRemoteStream: (flux) => { $("xSortie").srcObject = flux; st.sortie = flux; },
      initialState: Object.assign({ prompt: { text: e0.prompt, enhance: true } }, e0.image ? { image: e0.image } : {}),
    });
    st.rc.on("sessionEnded", (ev) => arreter(T("avatar.direct.fin_decart", { raison: ev && ev.reason ? " (" + ev.reason + ")" : "" })));
    st.rc.on("error", (ev) => dire(T("avatar.direct.erreur", { raison: (ev && ev.message) || ev }), true));
    st.debut = performance.now();
    st.minuterie = setInterval(tic, 500);
    majBoutons(); dire(T("avatar.direct.en_cours"));
  } catch (e) {
    dire(e.message || String(e), true);
    await arreter(null);
  }
  majBoutons();
}

function tic() {
  if (!st.sess) return;
  const s = (performance.now() - st.debut) / 1000;
  $("xTemps").textContent = hms(s) + " / " + hms(st.sess.duree_max_s);
  $("xCout").textContent = eur(s * st.sess.prix_usd_s);
  if (s >= st.sess.duree_max_s) arreter(T("avatar.direct.borne"));
}

async function appliquer() {
  if (!st.rc) return;
  const e = etatCourant();
  try { await st.rc.set({ prompt: e.prompt, image: e.image, enhance: true }); dire(T("avatar.direct.applique")); }
  catch (x) { dire(T("avatar.direct.refuse", { raison: x.message || x }), true); }
}

async function arreter(motif) {
  clearInterval(st.minuterie); st.minuterie = null;
  if (st.rec && st.rec.state !== "inactive") st.rec.stop();
  const sess = st.sess, rc = st.rc;
  const secondes = sess && st.debut ? (performance.now() - st.debut) / 1000 : 0;
  st.rc = null; st.sess = null; st.debut = 0;
  try { rc && rc.disconnect(); } catch (e) { /* déjà fermé */ }
  if (st.vd) { st.vd.arreter(); st.vd = null; }
  if (st.local) st.local.getTracks().forEach((t) => t.stop());
  st.local = null; $("xLocal").srcObject = null; $("xSortie").srcObject = null;
  if (sess) {
    try {
      const f = await lire(await fetch(API + "/sessions/fin", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sess.session_id, secondes }), keepalive: true }));
      dire(T("avatar.direct.facture", { motif: motif || T("avatar.direct.arrete"), duree: hms(f.secondes), usd: eur(f.reel_usd) })
        + (f.voix_s != null ? T("avatar.direct.facture_voix", { duree: hms(f.voix_s), usd: eur(f.voix_usd) }) : "") + ".");
    } catch (e) { dire(T("avatar.direct.fin_non_notee", { raison: e.message }), true); }
  } else if (motif) dire(motif);
  majBoutons();
}

function enregistrer() {
  if (st.rec && st.rec.state === "recording") { st.rec.stop(); return; }
  if (!st.sortie) return;
  st.morceaux = [];
  const type = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"].find((t) => MediaRecorder.isTypeSupported(t));
  st.rec = new MediaRecorder(st.sortie, type ? { mimeType: type } : undefined);
  st.rec.ondataavailable = (e) => { if (e.data && e.data.size) st.morceaux.push(e.data); };
  st.rec.onstop = async () => {
    majBoutons();
    if (!st.morceaux.length) return;
    dire(T("avatar.direct.rangement"));
    try {
      const fd = new FormData(); fd.append("fichier", new Blob(st.morceaux, { type: "video/webm" }), "direct.webm");
      const dep = await lire(await fetch(API + "/recast/source", { method: "POST", body: fd }));
      const r = await lire(await fetch(API + "/direct/enregistrer", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ depot: dep.depot, personnage_id: $("xPerso").value || null }) }));
      dire(T("avatar.direct.range", { duree: hms(r.duree_s) }));
      window.dispatchEvent(new CustomEvent("dz-avatar-rendu", { detail: r.job_id }));
    } catch (e) { dire(T("avatar.direct.perdu", { raison: e.message }), true); }
  };
  st.rec.start(1000);
  majBoutons();
}

function majBoutons() {
  const actif = !!st.rc;
  $("xGo").disabled = actif || !(st.cat && st.cat.cle);
  $("xStop").disabled = !actif;
  $("xAppliquer").disabled = !actif;
  $("xRec").disabled = !actif;
  $("xRec").querySelector("span").textContent = T(st.rec && st.rec.state === "recording" ? "avatar.direct.arreter_enregistrement" : "avatar.direct.enregistrer");
  $("xDirectEtat").hidden = !actif;
  ["xFormat", "xDuree", "xRapide", "xMicro", "xMiroir", "xVoix", "xTranspose"].forEach((id) => { $(id).disabled = actif; });
}

async function charger() {
  st.cat = await lire(await fetch(API + "/etat"));
  const rc = await lire(await fetch(API + "/recast/modeles"));
  $("xCleZone").hidden = !!st.cat.cle;
  const pre = $("xPre"); pre.textContent = "";
  rc.prereglages.forEach((p) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "puce"; b.textContent = p.label; b.setAttribute("aria-pressed", "false");
    b.onclick = () => {
      st.pre = st.pre && st.pre.id === p.id ? null : { id: p.id, consigne: "the scene now takes place " + (CONSIGNES[p.id] || p.label) };
      pre.querySelectorAll(".puce").forEach((x) => x.setAttribute("aria-pressed", String(x === b && !!st.pre)));
      if (st.rc) appliquer();
    };
    pre.appendChild(b);
  });
  const persos = (await lire(await fetch(API + "/personnages"))).personnages || [];
  const s = $("xPerso"), avant = s.value; s.textContent = "";
  s.appendChild(new Option(T("avatar.direct.garder_visage"), ""));
  persos.forEach((p) => s.appendChild(new Option(p.nom, p.id)));
  s.value = avant || (persos.length ? persos[persos.length - 1].id : "");
  await chargerVoix();
  majDevis(); majBoutons();
}

async function chargerVoix() {
  let e = null;
  try { e = await lire(await fetch(API + "/voix-direct/etat")); } catch (x) { /* la voix reste « telle quelle » */ }
  const s = $("xVoix"), avant = s.value; s.textContent = "";
  s.appendChild(new Option(T("avatar.direct.voix_telle"), ""));
  const o = new Option(T("avatar.direct.voix_cloud", { s: (RETARD_MS.cloud / 1000).toFixed(1).replace(".", ",") }), "cloud");
  o.disabled = !(e && e.cloud.disponible); s.appendChild(o);
  ((e && e.local.modeles) || []).forEach((m) => s.appendChild(new Option(T(m.index ? "avatar.direct.voix_locale" : "avatar.direct.voix_locale_sans_index", { nom: m.nom }), "local:" + m.nom)));
  s.value = [...s.options].some((x) => x.value === avant && !x.disabled) ? avant : "";
  const aide = !e ? "" : !e.local.gpu ? T("avatar.direct.sans_gpu")
    : !e.local.voixbox ? T("avatar.direct.sans_voixbox", { gpu: e.local.gpu.nom })
    : !e.local.modeles.length ? T("avatar.direct.sans_voix_rvc") : "";
  $("xVoixAide").textContent = aide + (retardVideoPossible() ? "" : " " + T("avatar.direct.navigateur"));
  majVoix();
}
function majVoix() {
  $("xTransposeChamp").hidden = !$("xVoix").value.startsWith("local:");
  if ($("xVoix").value) { $("xMicro").checked = true; }
}
// les consignes des préréglages (anglais, comme celles du Recast) — l'écran n'a que les libellés servis
const CONSIGNES = {
  studio_neon: "in a dark studio lit by pink and cyan neon tubes", plateau_tv: "on a bright modern TV news set",
  bureau: "in a modern glass office with soft daylight", tokyo_nuit: "on a rainy Tokyo street at night with neon signs",
  plage: "on a beach at golden-hour sunset", foret: "in a misty pine forest at dawn",
  station: "inside a space station with Earth through the window", bibliotheque: "in an old wooden library",
  desert: "in a vast sand desert", salle_classe: "in a sunny classroom", fond_vert: "in front of a flat chroma-key green background",
  cave_crypto: "in a dim crypto trading den full of glowing charts",
};

$("xCleOk").addEventListener("click", poserCle);
$("xGo").addEventListener("click", demarrer);
$("xStop").addEventListener("click", () => arreter(null));
$("xAppliquer").addEventListener("click", appliquer);
$("xPerso").addEventListener("change", () => { if (st.rc) appliquer(); });
$("xRec").addEventListener("click", enregistrer);
["xDuree", "xRapide"].forEach((id) => $(id).addEventListener("input", majDevis));
$("xVoix").addEventListener("change", majVoix);
document.addEventListener("visibilitychange", () => {
  clearTimeout(st.cache);
  if (document.hidden && st.rc) st.cache = setTimeout(() => arreter(T("avatar.direct.cache")), 60000);
});
window.addEventListener("pagehide", () => { if (st.rc) arreter(null); });
charger().catch((e) => dire(T("avatar.commun.serveur_muet", { raison: e.message }), true));
