"""t189 (G7, génération IA enrichie, 12/10/2026) — l'écran du storyboard 3D et de la vidéo d'un plan, posé APRÈS L8.

La table réversible L8 (scripts/i18n_l8_paires.json) exige : source du poste == base 1515d67b + éditions. Une
modification du code d'après L8 passe donc par ici, comme une édition S() (même mécanisme que t182.py / t183.py).

Sur chaque carte du storyboard, ENTRE « Image de production » et « Plateau 3D » :
- « Reconstruire en 3D (SAM 3) » (act-objets3d) : dialogue maison (dialoguePlanIA) — objets à isoler préremplis avec
  les entités du plan (personnages d'abord, puis objets, puis décors), modèle par DzModelesIA (nature « objets3d »,
  les sans-clé choisissables), prix (0,02 $ la requête, unité fal à confirmer), confirmation ; puis
  POST /shots/{id}/objets3d, toast « N objets posés dans le Plateau » et « Ouvrir le Plateau » ;
- « Générer le plan (vidéo) » (act-video) : même dialogue sur la nature video_fl si le plan a une borne de FIN
  (keyframe_end), video_i2v sinon ; présélection Veo 3.1 Fast first-last avec une fin, le défaut vidéo de l'app sans
  (GET /video-models, le défaut global ne change pas) ; prix = DEVIS du serveur (GET /shots/{id}/video/devis, relu à
  chaque changement de modèle : durée réellement générée, refus, clé absente) ; les images qui servent
  (début : borne du Plateau / image de production / croquis ; fin : borne de fin ou « aucune ») ; puis
  POST /shots/{id}/video, et la VIGNETTE vidéo de la carte suit le job (GET /jobs/{id}, toutes les 4 s, arrêté quand
  la carte disparaît ou que le job finit) avant un <video> muet avec contrôles (GET /jobs/{id}/video).
Un 402 de plafond est déjà pris par /shared/dz-plafonds.js (enveloppe de window.fetch) : rien à faire ici.
"""
from outils import S

_AT = "atelier/atelier.js"


def C(t: str) -> str:
    """Les sources sont en CRLF : le code ci-dessous est écrit en LF puis converti."""
    return t.replace("\r\n", "\n").replace("\n", "\r\n")


BOUTONS = C('''${ico("dz-media-generer-image")}</button>
        <button class="btn ghost act-objets3d" title="${dzT("atelier.at2_obj3d.bouton_t")}" aria-label="${dzT("atelier.plan.reconstruire3d")}">${ico("dz-lab3d-generer-modele")}</button>
        <button class="btn ghost act-video" title="${dzT("atelier.at2_video.bouton_t")}" aria-label="${dzT("atelier.plan.video")}">${ico("dz-media-generer-video")}''')

VIGNETTE = C('''    ${vignetteVideo(s)}
    </div>''')

ECOUTEURS = C('''// t189 : le storyboard 3D (SAM 3 → Plateau) et la vidéo du plan ; la vignette suit le job de la vidéo
    card.querySelector(".act-objets3d").addEventListener("click", () => objets3dPlan(id));
    card.querySelector(".act-video").addEventListener("click", () => videoPlan(id));
    suivreVideo(card, sh());
    // t127 : le Plateau 3D du plan''')

FONCTIONS = C('''/* ═════════ t189 (G7) — le storyboard 3D d'un plan et sa VIDÉO ═════════
   Deux tirs payants, chacun derrière le dialogue maison dialoguePlanIA (modèle par DzModelesIA — les modèles sans clé
   restent choisissables, le serveur refuse en 503 avant toute dépense —, prix affiché, confirmation) ; au-delà d'un
   plafond mensuel, dz-plafonds.js montre le dialogue 402 et rejoue sur confirmation. */
const MODELE_VIDEO_FIN = "veo-3.1-fast-fal";   // le défaut d'un plan AVEC borne de fin (comme la route)

/* les objets préremplis : les entités du plan qui ont un corps — personnages d'abord, puis objets, puis décors */
function objetsDuPlan(s, ents) {
  const ordre = { character: 0, object: 1, decor: 2 };
  return (s.entities || []).map(eid => (ents || []).find(e => e.id === eid))
    .filter(e => e && e.kind in ordre)
    .sort((a, b) => ordre[a.kind] - ordre[b.kind])
    .map(e => e.name).join(", ");
}

/* la nature du catalogue pour la vidéo du plan : une borne de fin ⇒ modèles first-last seulement */
function natureVideoPlan(s) {
  return s && s.keyframe_end ? "video_fl" : "video_i2v";
}

/* l'image de départ de la vidéo, dans l'ordre de la route : borne du Plateau, image de production, croquis */
function debutVideoPlan(s) {
  if (s.keyframe_image) return { cle: "atelier.at2_video.src_plateau", fichier: s.keyframe_image };
  if (s.image) return { cle: "atelier.at2_video.src_prod", fichier: s.image };
  if (s.sketch_image) return { cle: "atelier.at2_video.src_croquis", fichier: s.sketch_image };
  return null;
}

function prixDzp(usd, unite) {
  const DM = window.DzModelesIA;
  if (DM) return DM.prix(usd, unite);
  const v = Number(usd);
  return v > 0 ? "$" + v.toFixed(3) : dzT("atelier.at2_dzp.a_mesurer");
}

/* le dialogue maison d'un tir payant d'un plan : {modele, texte, entree} ou null (annulé).
   o.devis(modele) -> Promise du devis du SERVEUR (relu à l'ouverture et à chaque changement de modèle ; une réponse
   périmée est ignorée) ; o.devisRendu(devis | null) -> {prix, images?, refus, mention} : un refus empêche le tir,
   la mention (clé à ajouter) ne bloque rien. */
function dialoguePlanIA(o) {
  return new Promise((resoudre) => {
    const el = (tag, cls, txt) => { const x = document.createElement(tag); if (cls) x.className = cls; if (txt != null) x.textContent = txt; return x; };
    const voile = el("div", "modal dzp-modal");
    voile.setAttribute("role", "dialog");
    voile.setAttribute("aria-modal", "true");
    const boite = el("div", "modal-box dzp-box");
    const tete = el("div", "modal-head");
    tete.appendChild(el("b", "", o.titre));
    const corps = el("div", "dzp-body");
    const ligne = (lbl, champ) => { const l = el("label", "dzp-l"); l.appendChild(el("span", "", lbl)); l.appendChild(champ); corps.appendChild(l); };
    let champ = null;
    if (o.champ) {
      champ = el("input", "dzp-champ");
      champ.type = "text";
      champ.value = o.champ.valeur || "";
      champ.placeholder = o.champ.placeholder || "";
      ligne(o.champ.label, champ);
    }
    const sel = el("select", "dzp-modele");
    ligne(dzT("atelier.at2_dzp.modele"), sel);
    const aide = el("div", "da-note dzp-aide");
    corps.appendChild(aide);
    const imgs = el("div", "dzp-imgs");
    corps.appendChild(imgs);
    const poserImages = (liste) => {
      imgs.textContent = "";
      (liste || []).forEach(im => {
        const r = el("div", "dzp-img");
        if (im.fichier) {
          const img = el("img");
          img.src = "/api/images/" + encodeURIComponent(im.fichier);
          img.alt = "";
          r.appendChild(img);
        }
        r.appendChild(el("span", "", im.label));
        imgs.appendChild(r);
      });
    };
    poserImages(o.images);
    const prix = el("div", "dzp-prix");
    const mention = el("div", "da-note dzp-mention");
    const err = el("div", "dzp-err");
    corps.appendChild(prix);
    corps.appendChild(mention);
    corps.appendChild(err);
    const pied = el("div", "dzp-pied");
    const annuler = el("button", "btn ghost", dzT("atelier.at2_dzp.annuler"));
    const ok = el("button", "btn primary", o.ok);
    annuler.type = ok.type = "button";
    pied.appendChild(annuler);
    pied.appendChild(ok);
    boite.appendChild(tete);
    boite.appendChild(corps);
    boite.appendChild(pied);
    voile.appendChild(boite);
    let mods = [];
    const courant = () => mods.find(m => m.id === sel.value) || null;
    let jeton = 0, devis = null;                       // devis = {modele, attente, refus} du modèle COURANT
    const lireDevis = () => {
      const modele = sel.value, n = ++jeton;
      const rendre = (d) => {
        if (n !== jeton || sel.value !== modele) return;  // réponse périmée : le modèle a changé entre-temps
        const r = o.devisRendu(d) || {};
        prix.textContent = r.prix || "";
        mention.textContent = r.mention || "";
        if (r.images) poserImages(r.images);
        err.textContent = r.refus || "";
        devis = { modele, attente: null, refus: r.refus || null };
      };
      const attente = o.devis(modele).then(rendre, () => rendre(null));
      devis = { modele, attente, refus: null };
    };
    const maj = () => {
      const m = courant();
      prix.textContent = o.prixDe ? o.prixDe(m) : "";
      aide.textContent = o.aideDe ? o.aideDe(m) : "";
      mention.textContent = "";
      err.textContent = "";
      if (o.devis && sel.value) lireDevis();
    };
    let touche = null;
    const fin = (v) => { document.removeEventListener("keydown", touche, true); voile.remove(); resoudre(v); };
    const valider = async () => {
      if (!sel.value) { err.textContent = dzT("atelier.at2_dzp.choisir"); return; }
      if (devis && devis.attente) await devis.attente;   // le devis du modèle choisi d'abord
      if (devis && devis.modele === sel.value && devis.refus) { err.textContent = devis.refus; return; }
      const m = courant();
      const choix = { modele: sel.value, texte: champ ? champ.value.trim() : "", entree: m };
      const ko = o.verifier ? o.verifier(choix, m) : null;
      if (ko) { err.textContent = ko; return; }
      fin(choix);
    };
    touche = (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fin(null); }
      else if (ev.key === "Enter" && ev.target !== sel) { ev.preventDefault(); ev.stopPropagation(); valider(); }
    };
    ok.addEventListener("click", valider);
    annuler.addEventListener("click", () => fin(null));
    voile.addEventListener("click", (ev) => { if (ev.target === voile) fin(null); });
    sel.addEventListener("change", maj);
    document.addEventListener("keydown", touche, true);
    document.body.appendChild(voile);
    (champ || ok).focus();
    const remplir = (l) => {
      mods = l || [];
      if (!o.valeur) { const d = mods.find(m => m.defaut); if (d) sel.value = d.id; }
      maj();
    };
    if (window.DzModelesIA) {
      window.DzModelesIA.select(sel, o.nature, { valeur: o.valeur }).then(remplir)
        .catch(e => { err.textContent = dzT("atelier.at2_dzp.catalogue_ko", { msg: e.message }); });
    } else {
      api.get("/ia/catalogue?nature=" + encodeURIComponent(o.nature)).then(d => {
        const l = (d && d.modeles) || [];
        sel.innerHTML = l.map(m => `<option value="${escA(m.id)}">${esc(m.label || m.id)}${m.dispo === false && m.cle
          ? " — " + esc(dzT("atelier.t183_da.cle_a_ajouter", { cle: m.cle })) : ""}</option>`).join("");
        if (o.valeur && l.some(m => m.id === o.valeur)) sel.value = o.valeur;
        remplir(l);
      }).catch(e => { err.textContent = dzT("atelier.at2_dzp.catalogue_ko", { msg: e.message }); });
    }
  });
}

/* « Reconstruire en 3D (SAM 3) » : les objets de l'image du plan → GLB posés dans la scène de son Plateau */
/* M5 : un tir à la fois par plan et par action — un second clic pendant le vol ne rouvre rien et ne POSTe pas */
const tirsEnCours = { objets3d: new Set(), video: new Set() };

async function objets3dPlan(id) {
  const s = shots.find(x => x.id === id);
  if (!s) return;
  if (tirsEnCours.objets3d.has(id)) { toast(dzT("atelier.at2_dzp.deja_en_cours", { i: s.idx + 1 }), true); return; }
  tirsEnCours.objets3d.add(id);
  try {
  const source = s.image || s.sketch_image;
  if (!source) { toast(dzT("atelier.at2_obj3d.sans_image"), true); return; }
  const choix = await dialoguePlanIA({
    titre: dzT("atelier.at2_obj3d.titre", { i: s.idx + 1 }),
    nature: "objets3d",
    champ: { label: dzT("atelier.plan.objets"), valeur: objetsDuPlan(s, entities), placeholder: dzT("atelier.at2_obj3d.objets_ph") },
    images: [{ label: s.image ? dzT("atelier.at2_obj3d.src_prod") : dzT("atelier.at2_obj3d.src_croquis"), fichier: source }],
    prixDe: (m) => m ? dzT("atelier.at2_obj3d.prix", { prix: prixDzp(m.usd, m.unite) })
      + (m.unite_a_confirmer ? " " + dzT("atelier.at2_obj3d.unite_a_confirmer") : "") : "",
    aideDe: (m) => m && m.corps ? dzT("atelier.at2_obj3d.corps_facultatif") : dzT("atelier.at2_obj3d.objets_aide"),
    verifier: (c, m) => (!(m && m.corps) && !c.texte ? dzT("atelier.at2_obj3d.objets_requis") : null),
    ok: dzT("atelier.at2_obj3d.reconstruire"),
  });
  if (!choix) return;
  toast(dzT("atelier.at2_obj3d.en_cours", { i: s.idx + 1 }));
  try {
    const corps = { modele: choix.modele };
    if (choix.texte) corps.prompt = choix.texte;
    const r = await api.send("POST", `/shots/${encodeURIComponent(id)}/objets3d`, corps);
    // M8 : SAM 3 peut rendre plus de 32 GLB ; les écartés sont DITS
    const fait = r.tronques > 0 ? dzT("atelier.plan.objets_poses_tronques", { n: r.n, m: r.tronques })
                                : dzT("atelier.plan.objets_poses", { n: r.n });
    toast(fait);
    if (await window.__dzDialogue.confirmer(fait,
        { titre: dzT("atelier.plan.reconstruire3d"), ok: dzT("atelier.at2_obj3d.ouvrir_plateau"), annuler: dzT("atelier.at2_obj3d.rester") }))
      location.href = "/plateau/?shot=" + encodeURIComponent(s.id);   // le Plateau du plan, comme act-plateau
  } catch (e) { toast(dzT("atelier.at2_obj3d.err", { msg: e.message }), true); }
  } finally { tirsEnCours.objets3d.delete(id); }
}

/* « Générer le plan (vidéo) » : début = borne du Plateau / image de production / croquis ; fin = borne de fin */
async function videoPlan(id) {
  const s = shots.find(x => x.id === id);
  if (!s) return;
  if (tirsEnCours.video.has(id)) { toast(dzT("atelier.at2_dzp.deja_en_cours", { i: s.idx + 1 }), true); return; }
  tirsEnCours.video.add(id);
  try {
  const debut = debutVideoPlan(s);
  if (!debut) { toast(dzT("atelier.at2_video.sans_debut"), true); return; }
  const nature = natureVideoPlan(s);
  let defaut = MODELE_VIDEO_FIN;
  if (nature === "video_i2v") {
    try { defaut = (await api.get("/video-models")).default || ""; } catch (e) { defaut = ""; }
  }
  const duree = Number(s.duration_s) || 4;
  const choix = await dialoguePlanIA({
    titre: dzT("atelier.at2_video.titre", { i: s.idx + 1 }),
    nature,
    valeur: defaut,
    images: [{ label: dzT("atelier.at2_video.debut", { source: dzT(debut.cle) }), fichier: debut.fichier },
             s.keyframe_end ? { label: dzT("atelier.plan.video_fin"), fichier: s.keyframe_end }
                            : { label: dzT("atelier.at2_video.fin_aucune") }],
    // le prix est le DEVIS du serveur (durée réellement générée et facturée), jamais un calcul local
    prixDe: () => dzT("atelier.at2_video.devis_attente"),
    devis: (modele) => api.get(`/shots/${encodeURIComponent(id)}/video/devis?video_model=${encodeURIComponent(modele)}`),
    devisRendu: (d) => rendreDevisVideo(d, duree),
    aideDe: () => (nature === "video_fl" ? dzT("atelier.at2_video.aide_fl") : dzT("atelier.at2_video.aide_i2v")),
    ok: dzT("atelier.at2_video.generer"),
  });
  if (!choix) return;
  toast(dzT("atelier.at2_video.en_cours", { i: s.idx + 1 }));
  try {
    const up = await api.send("POST", `/shots/${encodeURIComponent(id)}/video`, { video_model: choix.modele });
    if (up && up.video) s.video = up.video;          // M9 : seul le job du plan entre dans l'état (ni job_id ni usd)
    renderBoard();
    toast(dzT("atelier.at2_video.lancee", { i: s.idx + 1, total: prixDzp(up.usd) }));
  } catch (e) { toast(dzT("atelier.at2_video.err", { msg: e.message }), true); }
  } finally { tirsEnCours.video.delete(id); }
}

/* le devis serveur de la vidéo d'un plan -> ce que montre le dialogue ; null (devis en échec) : coût inconnu, rien
   n'est bloqué */
const ORIGINES_VIDEO = { plateau: "atelier.at2_video.src_plateau", production: "atelier.at2_video.src_prod",
                         croquis: "atelier.at2_video.src_croquis" };
function rendreDevisVideo(d, duree) {
  if (!d) return { prix: dzT("atelier.at2_video.devis_ko"), refus: null, mention: "" };
  const prix = d.usd == null ? dzT("atelier.at2_video.cout_inconnu")
    : dzT("atelier.at2_video.prix_devis", { total: prixDzp(d.usd) })
      + (d.duree_s != null && Number(d.duree_s) !== Number(duree)
        ? " " + dzT("atelier.at2_video.generees", { n: d.duree_s, plan: duree }) : "");
  const images = [d.debut ? { label: dzT("atelier.at2_video.debut", { source: dzT(ORIGINES_VIDEO[d.debut.origine] || "atelier.at2_video.src_prod") }),
                              fichier: d.debut.nom } : { label: dzT("atelier.at2_video.debut_aucune") },
                  d.fin ? { label: dzT("atelier.plan.video_fin"), fichier: d.fin.nom } : { label: dzT("atelier.at2_video.fin_aucune") }];
  return { prix, images, refus: d.refus || null,
           mention: d.cle_absente ? dzT("atelier.at2_video.cle_absente", { cle: d.cle_absente }) : "" };
}

/* la vignette vidéo d'une carte : l'état du job, puis le lecteur muet ; un seul suivi par plan */
function vignetteVideo(s) {
  return s.video ? `<div class="shot-video" data-job="${escA(s.video)}"><span class="shot-video-etat">${dzT("atelier.at2_video.attente")}</span></div>` : "";
}

/* M6 : un suivi BORNÉ — un job terminé (fait, en échec, introuvable) n'est plus jamais réinterrogé (etatsVideo) ; le
   pas croît de 4 s (×1,5) jusqu'à 30 s ; au-delà de 30 min de suivi d'un même job, « suivi arrêté » (rouvrir le
   chapitre le relance) ; toujours arrêté quand la carte est détachée. I1 : un 404 n'est « introuvable » qu'au 3e
   tour CONSÉCUTIF (le job peut ne pas être encore visible), « en attente » avant. */
const SUIVI_VIDEO = { pas: 4000, facteur: 1.5, pasMax: 30000, dureeMax: 30 * 60 * 1000, absentsMax: 3 };
const etatsVideo = new Map(), suivisVideo = new Map(), suivisJob = new Map();
function suivreVideo(card, s) {
  const box = card.querySelector(".shot-video");
  if (!box || !s || !s.video) return;
  const job = s.video, cle = s.id;
  clearTimeout(suivisVideo.get(cle));
  suivisVideo.delete(cle);
  if (etatsVideo.has(job)) { box.innerHTML = etatsVideo.get(job); return; }      // terminal : aucun GET
  const etat = (t, err) => {
    box.innerHTML = `<span class="shot-video-etat${err ? " err" : ""}">${esc(t)}</span>`;
  };
  const terminer = (html) => { etatsVideo.set(job, html); box.innerHTML = html; };
  if (!suivisJob.has(job)) suivisJob.set(job, { debut: Date.now(), pas: SUIVI_VIDEO.pas, absents: 0 });
  const st = suivisJob.get(job);
  const tour = async () => {
    suivisVideo.delete(cle);
    if (!box.isConnected) return;                     // la carte a disparu : le suivi s'arrête
    if (Date.now() - st.debut > SUIVI_VIDEO.dureeMax) { etat(dzT("atelier.at2_video.suivi_arrete"), true); return; }
    let j = null, absent = false;
    try {
      const r = await fetch("/api/jobs/" + encodeURIComponent(job));
      if (r.status === 404) absent = true;
      else if (r.ok) j = await r.json();
    } catch (e) { /* réseau : on réessaie au tour suivant */ }
    if (!box.isConnected) return;
    st.absents = absent ? st.absents + 1 : 0;
    if (st.absents >= SUIVI_VIDEO.absentsMax) {
      terminer(`<span class="shot-video-etat err">${esc(dzT("atelier.at2_video.introuvable"))}</span>`);
      return;
    }
    if (j && j.status === "done") {
      terminer(`<video class="shot-video-lecteur" src="/api/jobs/${encodeURIComponent(job)}/video" muted controls playsinline preload="metadata" aria-label="${escA(dzT("atelier.plan.video"))}"></video>`);
      return;
    }
    if (j && j.status === "failed") {
      terminer(`<span class="shot-video-etat err">${esc(dzT("atelier.at2_video.echec", { msg: j.error || "?" }))}</span>`);
      return;
    }
    if (j) etat(dzT("atelier.at2_video.progres", { pct: Math.round(Number(j.progress) || 0) }));
    else if (absent) etat(dzT("atelier.at2_video.attente"));
    suivisVideo.set(cle, setTimeout(tour, st.pas));
    st.pas = Math.min(SUIVI_VIDEO.pasMax, Math.round(st.pas * SUIVI_VIDEO.facteur));
  };
  tour();
}

''')

DICO = {
    "atelier.plan.reconstruire3d": ("Reconstruire en 3D (SAM 3)", "Rebuild in 3D (SAM 3)"),
    "atelier.plan.objets": ("Objets à isoler", "Objects to isolate"),
    "atelier.plan.objets_poses": ("{n} objets posés dans le Plateau", "{n} objects placed on the Stage"),
    "atelier.plan.video": ("Générer le plan (vidéo)", "Generate the shot (video)"),
    "atelier.plan.video_fin": ("Fin : borne de fin du Plateau", "End: the Stage's last frame"),
    "atelier.at2_obj3d.bouton_t": (
        "Reconstruire en 3D (SAM 3) : les objets de l'image du plan deviennent des modèles 3D posés dans son Plateau "
        "— coût affiché et confirmé avant",
        "Rebuild in 3D (SAM 3): the objects in the shot's image become 3D models placed on its Stage "
        "— cost shown and confirmed first"),
    "atelier.at2_obj3d.titre": ("Storyboard 3D du plan {i}", "3D storyboard for shot {i}"),
    "atelier.at2_obj3d.objets_ph": ("ex. personnage, table, lampe", "e.g. character, table, lamp"),
    "atelier.at2_obj3d.objets_aide": (
        "Les noms séparés par des virgules : SAM 3 isole chacun et le reconstruit en 3D.",
        "Names separated by commas: SAM 3 isolates each one and rebuilds it in 3D."),
    "atelier.at2_obj3d.corps_facultatif": (
        "Corps humain : les personnes de l'image sont reconstruites ; la liste d'objets est facultative.",
        "Human body: the people in the image are rebuilt; the object list is optional."),
    "atelier.at2_obj3d.objets_requis": (
        "Nommez au moins un objet à isoler (ex. « personnage, table »).",
        "Name at least one object to isolate (e.g. “character, table”)."),
    "atelier.at2_obj3d.src_prod": ("Image source : l'image de production", "Source image: the production image"),
    "atelier.at2_obj3d.src_croquis": ("Image source : le croquis", "Source image: the sketch"),
    "atelier.at2_obj3d.prix": ("Coût : {prix} la requête", "Cost: {prix} per request"),
    "atelier.at2_obj3d.unite_a_confirmer": (
        "(l'unité de facturation de fal est à confirmer au premier tir)",
        "(fal's billing unit is to be confirmed on the first run)"),
    "atelier.at2_obj3d.reconstruire": ("Reconstruire", "Rebuild"),
    "atelier.at2_obj3d.sans_image": (
        "Ce plan n'a ni image de production ni croquis : générez-en un d'abord.",
        "This shot has neither a production image nor a sketch: generate one first."),
    "atelier.at2_obj3d.en_cours": ("Storyboard 3D du plan {i}…", "3D storyboard for shot {i}…"),
    "atelier.at2_obj3d.ouvrir_plateau": ("Ouvrir le Plateau", "Open the Stage"),
    "atelier.at2_obj3d.rester": ("Rester ici", "Stay here"),
    "atelier.at2_obj3d.err": ("Storyboard 3D : {msg}", "3D storyboard: {msg}"),
    "atelier.at2_video.bouton_t": (
        "Générer le plan (vidéo) : de son image de départ (borne du Plateau, image de production ou croquis) à sa borne "
        "de fin s'il en a une — coût affiché et confirmé avant",
        "Generate the shot (video): from its start image (Stage frame, production image or sketch) to its last frame "
        "if it has one — cost shown and confirmed first"),
    "atelier.at2_video.titre": ("Vidéo du plan {i}", "Video for shot {i}"),
    "atelier.at2_video.src_plateau": ("borne de début du Plateau", "the Stage's first frame"),
    "atelier.at2_video.src_prod": ("image de production", "production image"),
    "atelier.at2_video.src_croquis": ("croquis", "sketch"),
    "atelier.at2_video.debut": ("Début : {source}", "Start: {source}"),
    "atelier.at2_video.fin_aucune": ("Fin : aucune", "End: none"),
    "atelier.at2_video.aide_fl": (
        "Le plan a une borne de fin : seuls les modèles qui acceptent une image de fin sont proposés.",
        "The shot has a last frame: only models that accept an end image are offered."),
    "atelier.at2_video.aide_i2v": (
        "Pas de borne de fin : la vidéo part de l'image de début (capturez une fin au Plateau pour l'imposer).",
        "No last frame: the video starts from the start image (capture an end frame on the Stage to set one)."),
    "atelier.at2_video.prix_devis": ("Coût : {total}", "Cost: {total}"),
    "atelier.at2_video.generees": ("({n} s générées pour un plan de {plan} s)", "({n} s generated for a {plan} s shot)"),
    "atelier.at2_video.devis_attente": ("Coût : devis en cours…", "Cost: getting a quote…"),
    "atelier.at2_video.devis_ko": ("Coût : inconnu (devis indisponible)", "Cost: unknown (quote unavailable)"),
    "atelier.at2_video.cout_inconnu": ("Coût : inconnu", "Cost: unknown"),
    "atelier.at2_video.debut_aucune": ("Début : aucune", "Start: none"),
    "atelier.at2_video.cle_absente": ("clé {cle} à ajouter dans Réglages", "add the {cle} key in Settings"),
    "atelier.at2_video.generer": ("Générer la vidéo", "Generate the video"),
    "atelier.at2_video.sans_debut": (
        "Ce plan n'a aucune image de départ : capturez-la au Plateau, ou générez son image de production ou son croquis.",
        "This shot has no start image: capture it on the Stage, or generate its production image or its sketch."),
    "atelier.at2_video.en_cours": ("Vidéo du plan {i}…", "Video for shot {i}…"),
    "atelier.at2_video.lancee": ("Vidéo du plan {i} lancée ({total}).", "Video for shot {i} started ({total})."),
    "atelier.at2_video.err": ("Vidéo du plan : {msg}", "Shot video: {msg}"),
    "atelier.at2_video.attente": ("vidéo en attente…", "video queued…"),
    "atelier.at2_video.progres": ("vidéo en cours… {pct} %", "video rendering… {pct}%"),
    "atelier.at2_video.echec": ("vidéo en échec : {msg}", "video failed: {msg}"),
    "atelier.at2_video.introuvable": ("vidéo introuvable", "video not found"),
    "atelier.at2_dzp.modele": ("Modèle", "Model"),
    "atelier.at2_dzp.deja_en_cours": ("Plan {i} : déjà en cours, attendez la fin.", "Shot {i}: already running, wait for it to finish."),
    "atelier.plan.objets_poses_tronques": ("{n} objets posés dans le Plateau ; {m} de plus écartés (32 au plus)",
                                           "{n} objects placed on the Stage; {m} more left out (32 at most)"),
    "atelier.at2_video.suivi_arrete": ("suivi arrêté, rouvrez le chapitre", "tracking stopped, reopen the chapter"),
    "atelier.at2_dzp.annuler": ("Annuler", "Cancel"),
    "atelier.at2_dzp.choisir": ("Choisissez un modèle.", "Choose a model."),
    "atelier.at2_dzp.a_mesurer": ("prix à mesurer", "price to be measured"),
    "atelier.at2_dzp.catalogue_ko": ("Catalogue des modèles illisible : {msg}", "Model catalogue unreadable: {msg}"),
}

ENTREES = [
    S(_AT, 821, '${ico("dz-media-generer-image")}', BOUTONS, {}),
    S(_AT, 828, '    </div>', VIGNETTE, {}),
    S(_AT, 892, '// t127 : le Plateau 3D du plan', ECOUTEURS, {}),
    S(_AT, 972, '/* ═════════ tâche #62 (plan chapitres T6)', FONCTIONS + '/* ═════════ tâche #62 (plan chapitres T6)', DICO),
]
