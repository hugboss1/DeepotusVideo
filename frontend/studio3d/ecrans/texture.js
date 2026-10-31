/* t393 (31/10/2026) — écran TEXTURE du 3D Studio, volet 1/2 : capture, image de référence, retexture IA.

   Relevé de Sorceress (§4 de l'inventaire) : à gauche le modèle d'image, la résolution, le ratio et l'aperçu de la
   référence ; au centre le modèle dans un cadre de capture, la rosace de dix vues, l'orbite par pas, cinq éclairages
   et deux curseurs, le rail des références générées ; à droite « Générer une texture » (prompt facultatif, prompt par
   défaut), la planche de style, et chez nous la RETEXTURE IA de Meshy (D4 : d'abord la retexture « moteur »).

   Générer : la capture du cadre (PNG, rendue à part en 1536 px de grand côté par setViewOffset — exactement ce que le
   cadre montre) part comme image source chez le modèle d'image choisi ; le résultat devient une référence rangée
   avec le job (POST /api/studio3d/texture/{job}/generer). Retexturer : Meshy habille le maillage d'après la référence
   choisie et/ou un texte de style, et écrit une NOUVELLE version (…/retexturer, puis GET /api/jobs/{id}).
   Avant tout POST payant : le devis (gratuit), puis le dialogue maison ; le corps porte alors `confirme_cout` et le
   prix accepté (`max_usd`). Le 402 des plafonds est lu par /shared/dz-plafonds.js.

   Le calcul (vues, orbite, éclairages, cadre, rail) vit dans texture_calc.js, testé sous node. Le volet 2/2 (t394 :
   projection multi-vues, pinceaux, atlas UV) vit dans projection.js : l'onglet « Projection » de la colonne de
   droite et l'atlas à plat de la colonne de gauche ; il reprend d'ici le modèle d'image, la résolution, l'éclairage,
   le devis et le dialogue maison. */
"use strict";
import * as THREE from "three";
import { creerCanevas, charger, vider, cadrer, montrerRepere } from "/lib3d/viewer.js";
import { T, langue } from "./coque_calc.js";
import * as PJ from "./projection.js";
import { VUES, PAS, ECLAIRAGES, RATIOS, RESOLUTIONS, orbiter, positionCamera, poseDepuis, vueDe, eclairage, cadre,
  tailleCapture, modeleParDefaut, resolutionPermise, trierRail, referenceChoisie, usd, vue } from "./texture_calc.js";

const API = "/api/studio3d/texture";
const P = { s: null, ctx: null, api: null, fiche: null, centre: null, distance: 3, pose: { azimut: 45, elevation: 20 },
  pas: 45, eclairage: "doux", vif: 1, ambiant: 1, lumieres: null, reg: null, modele: null, resolution: "1K",
  ratio: "1:1", refs: [], choisie: null, style: null, resMeshy: "2k", occupe: false, suivi: null, charge: 0, volet: "ref" };

const $ = (sel) => P.s.querySelector(sel);

export async function monter(section, ctx) {
  P.s = section;
  P.ctx = ctx;
  const { esc, ico } = ctx;
  section.innerHTML = `<div class="ec-trois tx-ecran">
    <aside class="ec-gauche ec-defile">
      <div class="ec-label">${esc(T("tex.apercu"))}</div>
      <figure class="tx-apercu" id="txApercu"></figure>
      <div class="ec-label">${esc(T("tex.modele"))}</div>
      <div class="tx-modeles" id="txModeles"></div>
      <div class="ec-label">${esc(T("tex.resolution"))}</div>
      <div class="ec-segments ec-plein" id="txRes">${RESOLUTIONS.map((r) => `<button data-res="${r}">${r}</button>`).join("")}</div>
      <div class="ec-label">${esc(T("tex.ratio"))}</div>
      <div class="ec-segments ec-plein" id="txRatio">${RATIOS.map((r) => `<button data-ratio="${r}">${r}</button>`).join("")}</div>
      <div class="ec-note">${esc(T("tex.ratio_aide"))}</div>
      ${PJ.htmlAtlas(esc)}
    </aside>
    <main class="ec-centre">
      <div class="ec-barre-vue tx-barre">
        <div class="tx-rosace" id="txRosace" role="group" aria-label="${esc(T("tex.vues"))}">${VUES.map((v) =>
          `<button data-vue="${v.id}" title="${esc(T("tex.vue_" + v.id))}">${esc(T("tex.vuec_" + v.id))}</button>`).join("")}</div>
        <span class="tx-filet" aria-hidden="true"></span>
        <div class="tx-orbite" id="txOrbite" role="group" aria-label="${esc(T("tex.orbite"))}">
          <button data-orb="-1,0" title="${esc(T("tex.orb_gauche"))}" aria-label="${esc(T("tex.orb_gauche"))}">◀</button>
          <button data-orb="0,1" title="${esc(T("tex.orb_haut"))}" aria-label="${esc(T("tex.orb_haut"))}">▲</button>
          <button data-orb="0,-1" title="${esc(T("tex.orb_bas"))}" aria-label="${esc(T("tex.orb_bas"))}">▼</button>
          <button data-orb="1,0" title="${esc(T("tex.orb_droite"))}" aria-label="${esc(T("tex.orb_droite"))}">▶</button>
        </div>
        <div class="ec-segments" id="txPas" title="${esc(T("tex.pas"))}">${PAS.map((p) => `<button data-pas="${p}">${p}°</button>`).join("")}</div>
        <button class="ec-bouton" id="txCadrer">${ico("dz-lab3d-camera")} ${esc(T("tex.cadrer"))}</button>
      </div>
      <div class="ec-barre-vue tx-barre">
        <span class="tx-titre">${ico("dz-lab3d-lumiere")} ${esc(T("tex.eclairage"))}</span>
        <div class="ec-segments" id="txEcl">${ECLAIRAGES.map((e) =>
          `<button data-ecl="${e}" title="${esc(T("tex.ecla_" + e))}">${esc(T("tex.ecl_" + e))}</button>`).join("")}</div>
        <label class="tx-curseur">${esc(T("tex.vif"))}<input type="range" min="0" max="2" step="0.05" id="txVif" value="1"></label>
        <label class="tx-curseur">${esc(T("tex.ambiant"))}<input type="range" min="0" max="2" step="0.05" id="txAmb" value="1"></label>
      </div>
      <div class="ec-vues"><figure class="ec-vue tx-vue" id="txVue"><canvas id="txCanevas"></canvas>
        <div class="tx-cadre" id="txCadre" aria-hidden="true"></div>
        <figcaption id="txLegende"></figcaption></figure></div>
      <div class="tx-rail" id="txRail" role="list" aria-label="${esc(T("tex.rail"))}"></div>
    </main>
    <aside class="ec-droite ec-defile">
      <div class="ec-segments ec-plein tx-volets" id="txVolets" role="tablist">${["ref", "proj"].map((v) =>
        `<button role="tab" data-volet="${v}" title="${esc(T("tex.voleta_" + v))}">${esc(T("tex.volet_" + v))}</button>`).join("")}</div>
      <div id="txVoletRef">
      <label class="ec-bascule tx-inactif" title="${esc(T("tex.tpose_aide"))}"><input type="checkbox" disabled> ${esc(T("tex.tpose"))}</label>
      <div class="ec-note">${esc(T("tex.tpose_aide"))}</div>
      <div class="ec-label">${esc(T("tex.generer_titre"))}</div>
      <label class="ec-champ">${esc(T("tex.prompt"))}
        <textarea id="txPrompt" rows="5" maxlength="1000" placeholder="${esc(T("tex.prompt_vide"))}"></textarea></label>
      <div class="tx-ligne"><span class="tx-compte" id="txCompte">0/1000</span>
        <button class="ec-bouton" id="txDefaut">${ico("dz-media-prompt")} ${esc(T("tex.prompt_defaut"))}</button></div>
      <button class="ec-principal" id="txGenerer">${ico("dz-media-generer-image")} <span id="txGenererTexte">${esc(T("tex.generer"))}</span></button>
      <div class="ec-note">${esc(T("tex.generer_aide"))}</div>
      <div class="ec-label">${esc(T("tex.style_titre"))}</div>
      <label class="ec-depot petit">${ico("dz-action-importer")} <span>${esc(T("tex.style_deposer"))}</span>
        <input type="file" accept="image/png,image/jpeg" id="txStyleFichier" hidden></label>
      <div class="tx-style" id="txStyle"></div>
      <div class="ec-note">${esc(T("tex.style_aide"))}</div>
      <div class="ec-label">${esc(T("tex.retexture_titre"))}</div>
      <div class="tx-choisie" id="txChoisie"></div>
      <label class="ec-champ">${esc(T("tex.style_texte"))}
        <textarea id="txStyleTexte" rows="3" maxlength="600" placeholder="${esc(T("tex.style_texte_vide"))}"></textarea></label>
      <div class="ec-sous">${esc(T("tex.res_texture"))}</div>
      <div class="ec-segments ec-plein" id="txResMeshy">${["2k", "4k", "8k"].map((r) => `<button data-resm="${r}">${r.toUpperCase()}</button>`).join("")}</div>
      <button class="ec-principal" id="txRetexturer">${ico("dz-lab3d-materiau")} <span id="txRetexturerTexte">${esc(T("tex.retexturer"))}</span></button>
      <div class="ec-note">${esc(T("tex.retexture_aide"))}</div>
      </div>
      <div id="txVoletProj" hidden>${PJ.htmlPanneau(esc, ico)}</div>
      <div class="ec-avis" id="txAvis" role="status"></div>
    </aside>
  </div>`;

  P.api = creerCanevas($("#txCanevas"));
  P.api.scene.background = new THREE.Color(0x2b2e34);
  monterLumieres();
  P.api.controls.addEventListener("change", surOrbiteSouris);
  new ResizeObserver(peindreCadre).observe($("#txVue"));

  section.addEventListener("click", surClic);
  $("#txVif").addEventListener("input", (e) => { P.vif = +e.target.value; appliquerEclairage(); });
  $("#txAmb").addEventListener("input", (e) => { P.ambiant = +e.target.value; appliquerEclairage(); });
  $("#txPrompt").addEventListener("input", peindreCompte);
  $("#txStyleFichier").addEventListener("change", (e) => { if (e.target.files[0]) deposerStyle(e.target.files[0]); e.target.value = ""; });

  PJ.monter({ section, ctx, api: P.api, avis, envoyer, confirmer, modele: modeleCourant,
    resolution: () => resolutionPermise(modeleCourant(), P.resolution), fiche: () => P.fiche, reg: () => P.reg,
    eclairage: () => P.eclairage, lumieresPour, reappliquer: appliquerEclairage,
    ajouterReference: (r) => { if (r && P.fiche) { P.refs = [r, ...P.refs.filter((x) => x.id !== r.id)]; peindreRail(); } } });

  try { P.reg = await ctx.jget(`${API}/modeles`); } catch (e) { P.reg = { modeles: [], ratios: RATIOS, retexture: { devis: {} } }; avis(T("tex.erreur", { m: e.message })); }
  P.modele = modeleParDefaut(P.reg.modeles, P.reg.defaut);
  peindre();
}

export async function ouvrir(fiche) {
  if (!P.s) return;
  const autre = !P.fiche || !fiche || P.fiche.job !== fiche.job;
  P.fiche = fiche;
  if (autre) { P.refs = []; P.choisie = null; P.style = null; }
  peindre();
  const n = ++P.charge;
  PJ.reinitialiser();                                // un autre GLB : l'atlas peint d'hier ne vaut plus
  if (!fiche) { vider(P.api); return; }
  try {
    await charger(P.api, fiche.url);
    if (n !== P.charge) return;
    PJ.reinitialiser();
    P.centre = P.api.controls.target.clone();
    P.distance = P.api.camera.position.distanceTo(P.centre) || 3;
    appliquerEclairage();
    poser(P.pose);
  } catch (e) { avis(T("tex.erreur_modele", { m: e.message })); }
  await lireReferences();
}

export function montre() { peindreCadre(); }

/* ── caméra : rosace, orbite, cadrage ─────────────────────────────────────── */
function poser(pose) {
  if (!P.centre) return;
  P.pose = pose;
  const p = positionCamera(P.centre, P.distance, pose);
  const cam = P.api.camera;
  cam.up.set(0, 1, 0);
  cam.position.set(p.x, p.y, p.z);
  P.api.controls.target.copy(P.centre);
  P.api.controls.update();
  placerLumieres();
  peindreRosace();
}

function surOrbiteSouris() {
  if (!P.centre) return;
  P.pose = poseDepuis(P.api.controls.target, P.api.camera.position);
  P.distance = P.api.camera.position.distanceTo(P.api.controls.target) || P.distance;
  placerLumieres();
  peindreRosace();
}

function recadrer() {
  if (!P.api.racine) return;
  const c = cadrer(P.api);
  if (!c) return;
  P.centre = c.centre.clone();
  P.distance = P.api.camera.position.distanceTo(P.centre) || P.distance;
  poser(P.pose);
}

/* ── lumières : la clé et l'hémisphère du canevas partagé, plus un appoint et un contre-jour ─────────────────── */
function monterLumieres() {
  const sc = P.api.scene;
  const hemi = sc.children.find((o) => o.isHemisphereLight);
  const cle = sc.children.find((o) => o.isDirectionalLight);
  const appoint = new THREE.DirectionalLight(0xdfe8ff, 0);
  const contre = new THREE.DirectionalLight(0xfff1dc, 0);
  sc.add(appoint, contre, appoint.target, contre.target, cle.target);
  P.lumieres = { hemi, cle, appoint, contre };
}

/* la clé à 45° au-dessus et à droite de la caméra, l'appoint de l'autre côté, plus bas, le contre-jour derrière */
function placerLumieres() {
  if (!P.lumieres || !P.centre) return;
  const { cle, appoint, contre } = P.lumieres;
  const a = P.pose.azimut, e = P.pose.elevation, d = P.distance * 2;
  const pose = (l, da, el) => {
    const p = positionCamera(P.centre, d, { azimut: a + da, elevation: Math.max(-80, Math.min(80, el)) });
    l.position.set(p.x, p.y, p.z);
    l.target.position.copy(P.centre);
  };
  pose(cle, 40, e + 35);
  pose(appoint, -50, e + 5);
  pose(contre, 180, e + 30);
}

/* les captures de la texture auto tournent les lumières avec chaque caméra (une vue de dos ne doit pas être à
   contre-jour) ; `null` les remet sur la caméra de l'écran */
function lumieresPour(pose) {
  if (!pose) return placerLumieres();
  const avant = P.pose;
  P.pose = pose;
  placerLumieres();
  P.pose = avant;
}

function appliquerEclairage() {
  const L = eclairage(P.eclairage, P.vif, P.ambiant);
  const { hemi, cle, appoint, contre } = P.lumieres;
  hemi.intensity = L.hemi;
  cle.intensity = L.cle;
  appoint.intensity = L.appoint;
  contre.intensity = L.contre;
  sansLumiere(L.sansLumiere);
  placerLumieres();
  for (const b of P.s.querySelectorAll("#txEcl [data-ecl]")) b.classList.toggle("on", b.dataset.ecl === P.eclairage);
  $("#txVif").disabled = $("#txAmb").disabled = L.sansLumiere;
}

/* « Sans lumière » = albédo pur : chaque maillage passe en matière non éclairée qui garde sa couleur, sa texture
   de base, sa transparence et ses couleurs de sommets ; la matière d'origine revient telle quelle */
function sansLumiere(oui) {
  if (!P.api.racine) return;
  P.api.racine.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.userData.dzMatOrigine) o.userData.dzMatOrigine = o.material;
    if (!oui) { o.material = o.userData.dzMatOrigine; return; }
    if (!o.userData.dzMatAlbedo) {
      const plat = (m) => new THREE.MeshBasicMaterial({ map: m.map || null, color: m.color ? m.color.clone() : 0xffffff,
        transparent: !!m.transparent, opacity: m.opacity ?? 1, alphaTest: m.alphaTest || 0, side: m.side,
        vertexColors: !!m.vertexColors, alphaMap: m.alphaMap || null });
      const orig = o.userData.dzMatOrigine;
      o.userData.dzMatAlbedo = Array.isArray(orig) ? orig.map(plat) : plat(orig);
    }
    o.material = o.userData.dzMatAlbedo;
  });
}

/* ── capture : exactement le cadre, rendu à part en haute définition, SANS la grille ni les axes du canevas (une
   référence de texture montre l'objet, pas l'atelier) ──────────────────────────────────────────────────────── */
function capturer() {
  const api = P.api, r = api.renderer, cam = api.camera, cv = r.domElement;
  const L = cv.clientWidth || 1, H = cv.clientHeight || 1;
  const c = cadre(P.ratio, L, H);
  const t = tailleCapture(P.ratio);
  const pr = r.getPixelRatio();
  r.setPixelRatio(1);
  r.setSize(t.w, t.h, false);
  cam.setViewOffset(L, H, c.x, c.y, c.w, c.h);
  const repere = montrerRepere(api, false);
  r.render(api.scene, cam);
  const url = cv.toDataURL("image/png");
  montrerRepere(api, repere);
  cam.clearViewOffset();
  cam.aspect = L / H;
  cam.updateProjectionMatrix();
  r.setPixelRatio(pr);
  r.setSize(L, H, false);
  r.render(api.scene, cam);
  return url;
}

/* ── peinture ─────────────────────────────────────────────────────────────── */
function peindre() {
  peindreModeles();
  peindreReglages();
  peindreRosace();
  peindreCadre();
  peindreRail();
  peindreCompte();
  peindreBoutons();
  peindreVolet();
  if (P.lumieres) appliquerEclairage();
}

function peindreVolet() {
  for (const b of P.s.querySelectorAll("#txVolets [data-volet]")) {
    b.classList.toggle("on", b.dataset.volet === P.volet);
    b.setAttribute("aria-selected", String(b.dataset.volet === P.volet));
  }
  $("#txVoletRef").hidden = P.volet !== "ref";
  $("#txVoletProj").hidden = P.volet !== "proj";
}

function modeleCourant() { return ((P.reg && P.reg.modeles) || []).find((m) => m.id === P.modele) || null; }

function peindreModeles() {
  const { esc } = P.ctx;
  const l = (P.reg && P.reg.modeles) || [];
  const lg = langue();
  $("#txModeles").innerHTML = l.length ? l.map((m) => `<button class="tx-modele ${m.id === P.modele ? "on" : ""}" data-modele="${esc(m.id)}"
      title="${esc(m.cle_ok ? m.label : T("tex.cle_absente", { cle: m.cle }))}">
      <b>${m.id === (P.reg && P.reg.defaut) ? "★ " : ""}${esc(m.label)}</b>
      <span>${esc(usd(m.usd, lg))}${m.resolutions.length > 1 ? " · " + esc(m.resolutions.join("/")) : ""}${m.cle_ok ? "" : " · " + esc(T("tex.sans_cle"))}</span></button>`).join("")
    : `<div class="ec-note">${esc(T("tex.aucun_modele"))}</div>`;
}

function peindreReglages() {
  const m = modeleCourant();
  const permises = (m && m.resolutions) || ["1K"];
  P.resolution = resolutionPermise(m, P.resolution);
  for (const b of P.s.querySelectorAll("#txRes [data-res]")) {
    b.classList.toggle("on", b.dataset.res === P.resolution);
    b.disabled = !permises.includes(b.dataset.res);
    b.title = b.disabled ? T("tex.res_non", { modele: m ? m.label : "—" }) : "";
  }
  for (const b of P.s.querySelectorAll("#txRatio [data-ratio]")) b.classList.toggle("on", b.dataset.ratio === P.ratio);
  for (const b of P.s.querySelectorAll("#txPas [data-pas]")) b.classList.toggle("on", +b.dataset.pas === P.pas);
  for (const b of P.s.querySelectorAll("#txResMeshy [data-resm]")) b.classList.toggle("on", b.dataset.resm === P.resMeshy);
}

function peindreRosace() {
  const id = vueDe(P.pose);
  for (const b of P.s.querySelectorAll("#txRosace [data-vue]")) b.classList.toggle("on", b.dataset.vue === id);
  peindreLegende();
}

function peindreLegende() {
  const t = tailleCapture(P.ratio);
  const v = vueDe(P.pose);
  $("#txLegende").textContent = T("tex.legende", { ratio: P.ratio, l: t.w, h: t.h,
    vue: v ? T("tex.vue_" + v) : T("tex.vue_libre", { a: Math.round(P.pose.azimut), e: Math.round(P.pose.elevation) }) });
}

function peindreCadre() {
  const fig = $("#txVue"), c = cadre(P.ratio, fig.clientWidth, fig.clientHeight);
  Object.assign($("#txCadre").style, { left: c.x + "px", top: c.y + "px", width: c.w + "px", height: c.h + "px" });
  peindreLegende();
}

function peindreRail() {
  const { esc } = P.ctx;
  const l = trierRail(P.refs);
  P.choisie = referenceChoisie(P.refs, P.choisie);
  if (P.style && !l.some((r) => r.id === P.style)) P.style = null;
  $("#txRail").innerHTML = l.length ? l.map((r) => `<button class="tx-vignette ${r.id === P.choisie ? "choisie" : ""} ${r.id === P.style ? "style" : ""}"
      role="listitem" data-ref="${esc(r.id)}" title="${esc(titreRef(r))}"><img alt="" src="${esc(r.url)}" loading="lazy">
      <span class="tx-sorte">${esc(T("tex.sorte_" + r.sorte))}</span></button>`).join("")
    : `<span class="tx-rail-vide">${esc(T("tex.rail_vide"))}</span>`;
  const ch = l.find((r) => r.id === P.choisie);
  $("#txApercu").innerHTML = ch ? `<img alt="${esc(T("tex.apercu"))}" src="${esc(ch.url)}"><figcaption>${esc(titreRef(ch))}</figcaption>`
    : `<div class="ec-note">${esc(T("tex.apercu_vide"))}</div>`;
  $("#txChoisie").innerHTML = ch ? `<img alt="" src="${esc(ch.url)}"><span>${esc(T("tex.choisie", { quand: heure(ch.cree_le) }))}</span>`
    : `<span class="ec-note">${esc(T("tex.choisie_aucune"))}</span>`;
  const st = l.find((r) => r.id === P.style);
  $("#txStyle").innerHTML = st ? `<img alt="" src="${esc(st.url)}"><span>${esc(T("tex.style_actif"))}</span>
      <button class="ec-bouton" data-action="sans-style">${P.ctx.ico("dz-action-retirer")} ${esc(T("tex.style_retirer"))}</button>`
    : (ch ? `<button class="ec-bouton bloc" data-action="style-choisie">${P.ctx.ico("dz-action-ajouter")} ${esc(T("tex.style_depuis_choisie"))}</button>` : "");
  peindreBoutons();
}

function titreRef(r) {
  if (r.sorte === "style") return T("tex.titre_style", { quand: heure(r.cree_le) });
  return T("tex.titre_generee", { modele: r.modele || "—", res: r.resolution || "", ratio: r.ratio || "", quand: heure(r.cree_le) });
}
const heure = (iso) => { try { return new Date(iso).toLocaleString(T("tex.locale"), { dateStyle: "short", timeStyle: "short" }); } catch { return String(iso || ""); } };

function peindreCompte() { $("#txCompte").textContent = `${$("#txPrompt").value.length}/1000`; }

function peindreBoutons() {
  const lg = langue();
  const m = modeleCourant();
  const g = $("#txGenerer"), r = $("#txRetexturer");
  if (!g) return;
  const prixImg = m ? (m.usd * (P.resolution === "4K" && m.resolutions.includes("4K") ? 2 : 1)) : null;
  $("#txGenererTexte").textContent = T("tex.generer_prix", { usd: usd(prixImg, lg) });
  g.disabled = !P.fiche || !m || P.occupe;
  const dm = P.reg && P.reg.retexture && P.reg.retexture.devis && P.reg.retexture.devis[P.resMeshy];
  $("#txRetexturerTexte").textContent = dm ? T("tex.retexturer_prix", { cr: dm.credits, usd: usd(dm.usd, lg) }) : T("tex.retexturer");
  r.disabled = !P.fiche || P.occupe || !(P.choisie || $("#txStyleTexte").value.trim());
  PJ.repeindre();
}

function avis(t) { const a = $("#txAvis"); if (a) a.textContent = t || ""; }

/* ── événements ───────────────────────────────────────────────────────────── */
function surClic(e) {
  const b = e.target.closest("button");
  if (!b || b.disabled) return;
  const d = b.dataset;
  if (d.volet) { P.volet = d.volet; return peindreVolet(); }
  if (d.vue) return poser(vue(d.vue));
  if (d.orb) { const [x, y] = d.orb.split(",").map(Number); return poser(orbiter(P.pose, x, y, P.pas)); }
  if (d.pas) { P.pas = +d.pas; return peindreReglages(); }
  if (d.ecl) { P.eclairage = d.ecl; return appliquerEclairage(); }
  if (d.modele) { P.modele = d.modele; peindreModeles(); peindreReglages(); return peindreBoutons(); }
  if (d.res) { P.resolution = d.res; peindreReglages(); return peindreBoutons(); }
  if (d.ratio) { P.ratio = d.ratio; peindreReglages(); return peindreCadre(); }
  if (d.resm) { P.resMeshy = d.resm; peindreReglages(); return peindreBoutons(); }
  if (d.ref) { P.choisie = d.ref; return peindreRail(); }
  if (d.action === "sans-style") { P.style = null; return peindreRail(); }
  if (d.action === "style-choisie") { P.style = P.choisie; return peindreRail(); }
  if (b.id === "txCadrer") return recadrer();
  if (b.id === "txDefaut") { $("#txPrompt").value = (P.reg && P.reg.prompt_defaut) || ""; return peindreCompte(); }
  if (b.id === "txGenerer") return generer();
  if (b.id === "txRetexturer") return retexturer();
}

async function envoyer(url, corps) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = j && j.detail;
    throw Object.assign(new Error((typeof d === "string" && d) || (d && d.message) || String(r.status)), { status: r.status, detail: d });
  }
  return j;
}

async function confirmer(texte, ok) {
  const D = window.__dzDialogue;
  if (!D || !D.confirmer) { avis(T("tex.sans_dialogue")); return false; }     // sans dialogue maison : rien ne part
  return D.confirmer(texte, { ok });
}

function occupe(b) { P.occupe = b; peindreBoutons(); }

async function lireReferences() {
  if (!P.fiche) return;
  const job = P.fiche.job;
  try {
    const j = await P.ctx.jget(`${API}/${encodeURIComponent(job)}/references`);
    if (P.fiche && P.fiche.job === job) { P.refs = j.references || []; peindreRail(); }
  } catch (e) { avis(T("tex.erreur", { m: e.message })); }
}

async function generer() {
  const m = modeleCourant(), f = P.fiche;
  if (!m || !f || P.occupe || !P.api.racine) return;
  const res = resolutionPermise(m, P.resolution);
  let d;
  try { d = await envoyer(`${API}/devis`, { action: "generer", modele: m.id, resolution: res }); }
  catch (e) { return avis(T("tex.erreur", { m: e.message })); }
  if (!await confirmer(T("tex.confirmer_generer", { modele: m.label, usd: usd(d.usd, langue()), res, ratio: P.ratio }), T("tex.generer"))) return;
  occupe(true);
  avis(T("tex.en_cours_generer", { modele: m.label }));
  try {
    const capture = capturer();
    const j = await envoyer(`${API}/${encodeURIComponent(f.job)}/generer`, {
      capture, modele: m.id, resolution: res, ratio: P.ratio, prompt: $("#txPrompt").value.trim(),
      vue: vueDe(P.pose) || "libre", eclairage: P.eclairage, style: P.style, confirme_cout: true, max_usd: d.usd });
    if (P.fiche && P.fiche.job === f.job) {
      P.refs = [j.reference, ...P.refs.filter((r) => r.id !== j.reference.id)];
      P.choisie = j.reference.id;
      peindreRail();
    }
    avis(T("tex.fait_generer"));
  } catch (e) {
    avis(T("tex.erreur", { m: e.message }));
  } finally { occupe(false); }
}

async function deposerStyle(fichier) {
  const f = P.fiche;
  if (!f) return;
  if (fichier.size > 15 * 1024 * 1024) return avis(T("tex.style_lourd"));
  const image = await new Promise((ok, ko) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => ko(r.error); r.readAsDataURL(fichier); });
  try {
    const j = await envoyer(`${API}/${encodeURIComponent(f.job)}/style`, { image });
    P.refs = [j.reference, ...P.refs];
    P.style = j.reference.id;
    peindreRail();
    avis(T("tex.style_fait"));
  } catch (e) { avis(T("tex.erreur", { m: e.message })); }
}

async function retexturer() {
  const f = P.fiche;
  if (!f || P.occupe) return;
  const prompt = $("#txStyleTexte").value.trim();
  if (!P.choisie && !prompt) return avis(T("tex.retexture_rien"));
  let d;
  try { d = await envoyer(`${API}/devis`, { action: "retexturer", resolution: P.resMeshy }); }
  catch (e) { return avis(T("tex.erreur", { m: e.message })); }
  const texte = T("tex.confirmer_retexture", { cr: d.credits, usd: usd(d.usd, langue()), res: P.resMeshy.toUpperCase(),
    source: P.choisie ? T("tex.source_image") : T("tex.source_texte") });
  if (!await confirmer(texte, T("tex.retexturer"))) return;
  occupe(true);
  avis(T("tex.en_cours_retexture"));
  try {
    const j = await envoyer(`${API}/${encodeURIComponent(f.job)}/retexturer`, { reference: P.choisie, prompt,
      resolution: P.resMeshy, confirme_cout: true, max_usd: d.usd, approuver: true });
    suivre(j.job_id, f.job);
  } catch (e) {
    avis(T("tex.erreur", { m: e.message }));
    occupe(false);
  }
}

/* le job Meshy tourne en tâche de fond : on lit son état toutes les 4 s ; fini, le modèle ouvert est relu (la
   nouvelle version devient l'ouverte) */
function suivre(id, job) {
  clearTimeout(P.suivi);
  const tour = async () => {
    let j;
    try { j = await P.ctx.jget(`/api/jobs/${encodeURIComponent(id)}`); } catch (e) { P.suivi = setTimeout(tour, 6000); return; }
    if (j.status === "done") {
      occupe(false);
      avis(T("tex.fait_retexture"));
      if (P.fiche && P.fiche.job === job) await P.ctx.rafraichir();
      return;
    }
    if (j.status === "failed") { occupe(false); return avis(T("tex.erreur", { m: j.error || "—" })); }
    avis(T("tex.en_cours_etape", { etape: j.current_step || "…", p: j.progress || 0 }));
    P.suivi = setTimeout(tour, 4000);
  };
  P.suivi = setTimeout(tour, 2000);
}

document.addEventListener("input", (e) => { if (P.s && e.target && e.target.id === "txStyleTexte") peindreBoutons(); });
