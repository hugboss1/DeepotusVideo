/* dz-pose3d.js — le choix de POSE de la génération 3D : Aucune / T-pose / A-pose (t376, lot « Game Assets :
   finitions », 29/10/2026, plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md).
   SOURCE : frontend/shared/dz-pose3d.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-pose3d.js, servie à
   /shared/dz-pose3d.js, chargée par une balise classique dans la SPA (frontend/dist/index.html) et dans la page du
   3D Studio (frontend/studio3d/index.html). Serveur : backend/app/api/pose3d_routes.py (service pose3d).

   window.__dzPose3d :
     etat(q, rappel, exact) q = {engine, multiview, subject, image} -> l'état CONNU pour q (ou, sauf `exact`, le
                       dernier connu pour le même moteur pendant le chargement ; sinon null) ; demande GET /api/assets3d/pose (GRATUIT) après
                       250 ms de calme et appelle rappel() quand la réponse arrive. Règle D6 : choix grisé si le sujet
                       n'est pas un personnage, raison affichée ; doute = choix proposé avec avertissement.
     textes(e, moteur) {raison, avertissement, precision} traduits (dzT pose3d.*) ; "" quand rien à dire.
     corps(p)          le corps d'envoi de Game Assets 3D : la pose ne part que si le choix est actif ; l'ancien
                       booléen `tpose` n'est plus envoyé.
     classer(q, rappel) la classification VISION de l'image source, PAYANTE : devis gratuit, confirmation par
                       __dzDialogue.confirmer avec le montant, puis POST /classer {confirme_cout, max_usd} ; un 402 de
                       plafond passe par l'enveloppe de window.fetch (dz-plafonds.js). Une fois par image (le serveur
                       garde la classe).
     monterSelect(sel, q) le 3D Studio (Meshy, `pose_mode`) : grise la liste et la met à « libre » quand le choix
                       est inactif, pose la raison ou l'avertissement juste après, et un bouton de classement si utile.
   Aucun innerHTML ; textes par dzT (frontend/shared/i18n/pose3d.json). Charte : aucun arrondi, jetons de couleur. */
(function () {
  "use strict";
  if (window.__dzPose3d) return;

  var CACHE = {}, DERNIER = {}, ATTENTE = {};
  var minuterie = 0;

  function t(k, v) { return typeof window.dzT === "function" ? window.dzT(k, v) : k; }

  function cle(q) {
    return [q.engine || "", q.multiview ? 1 : 0, (q.subject || "").trim(), q.image || ""].join("|");
  }

  function url(q) {
    return "/api/assets3d/pose?engine=" + encodeURIComponent(q.engine || "") + "&multiview=" + (q.multiview ? "true" : "false")
      + "&subject=" + encodeURIComponent((q.subject || "").trim()) + "&image_filename=" + encodeURIComponent(q.image || "");
  }

  function charger(q, rappel) {
    var k = cle(q);
    if (ATTENTE[k]) return;
    ATTENTE[k] = 1;
    fetch(url(q)).then(function (r) { return r.ok ? r.json() : null; }).then(function (e) {
      delete ATTENTE[k];
      if (!e) return;
      CACHE[k] = e;
      DERNIER[q.engine || ""] = e;
      if (rappel) rappel();
    }).catch(function () { delete ATTENTE[k]; });
  }

  function etat(q, rappel, exact) {
    var k = cle(q);
    if (CACHE[k]) return CACHE[k];
    clearTimeout(minuterie);
    minuterie = setTimeout(function () { charger(q, rappel); }, 250);
    return exact ? null : (DERNIER[q.engine || ""] || null);
  }

  function textes(e, moteur) {
    var o = { raison: "", avertissement: "", precision: "" };
    if (!e) return o;
    if (e.raison) o.raison = t("pose3d.raison." + e.raison, { moteur: moteur || "" });
    if (e.avertissement) o.avertissement = t("pose3d.avert." + e.avertissement);
    if (e.actif && e.mode === "moteur" && moteur === "rodin") o.precision = t("pose3d.precision.rodin");
    if (e.actif && e.mode === "vues") o.precision = t("pose3d.precision.vues");
    return o;
  }

  function corps(p) {
    var b = Object.assign({}, p);
    delete b.tpose;
    var e = CACHE[cle({ engine: p.engine, multiview: p.multiview, subject: p.subject, image: p.image_filename })];
    if (!b.pose || !e || !e.actif) b.pose = "";
    return b;
  }

  function classer(q, rappel) {
    var D = window.__dzDialogue;
    return fetch("/api/assets3d/pose/devis").then(function (r) { return r.json(); }).then(function (d) {
      if (!d.disponible) {
        return D && D.informer(t("pose3d.vision.indispo_" + (d.raison || "cle")), { titre: t("pose3d.vision.titre") });
      }
      var usd = Number(d.usd || 0);
      return (D ? D.confirmer(t("pose3d.vision.confirmer", { usd: usd.toFixed(4) }),
                              { titre: t("pose3d.vision.titre"), ok: t("pose3d.vision.ok") })
                : Promise.resolve(window.confirm(t("pose3d.vision.confirmer", { usd: usd.toFixed(4) }))))
        .then(function (oui) {
          if (!oui) return null;
          return fetch("/api/assets3d/pose/classer", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image_filename: q.image, confirme_cout: true, max_usd: usd, engine: q.engine,
                                   multiview: !!q.multiview, subject: q.subject || "" })
          }).then(function (r) {
            return r.json().then(function (j) { return { ok: r.ok, j: j }; });
          }).then(function (x) {
            if (!x.ok) {
              var det = x.j && x.j.detail;
              return D && D.informer(String((det && (det.message || det)) || t("pose3d.vision.echec")),
                                     { titre: t("pose3d.vision.titre") });
            }
            var e = x.j.etat;
            CACHE[cle(q)] = e;
            DERNIER[q.engine || ""] = e;
            if (rappel) rappel();
            return e;
          });
        });
    });
  }

  /* ── 3D Studio : la liste `pose_mode` de Meshy ────────────────────────────────────────────────────────── */
  function monterSelect(sel, q) {
    if (!sel) return;
    var note = document.createElement("div");
    note.className = "fld-note";
    note.setAttribute("data-dz-pose3d", "");
    note.style.cssText = "margin-top:4px";
    sel.insertAdjacentElement("afterend", note);
    function peindre() {
      var e = etat(q, peindre, true);   // l'état EXACT : un état provisoire d'un autre sujet ne touche pas la liste
      while (note.firstChild) note.removeChild(note.firstChild);
      if (!e) return;
      var tx = textes(e, "meshy");
      sel.disabled = !e.actif;
      if (!e.actif) sel.value = "";
      sel.title = tx.raison || "";
      var dit = tx.raison || tx.avertissement;
      if (dit) {
        var s = document.createElement("span");
        s.style.color = e.actif ? "var(--amber)" : "var(--ink-soft)";
        s.textContent = dit;
        note.appendChild(s);
      }
      if (e.vision_proposee) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = t("pose3d.vision.bouton");
        b.style.cssText = "margin-left:8px;font-size:11px;padding:2px 8px;border-radius:var(--r);cursor:pointer;"
          + "background:transparent;color:var(--ink);border:1px solid var(--stroke)";
        b.addEventListener("click", function () { classer(q, peindre); });
        note.appendChild(b);
      }
    }
    peindre();
  }

  window.__dzPose3d = { etat: etat, textes: textes, corps: corps, classer: classer, monterSelect: monterSelect,
                        _cle: cle, _cache: CACHE };
})();
