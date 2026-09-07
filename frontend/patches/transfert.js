/*__DZ_TRANSFERT_BEGIN__*/
/* transfert.js — « Transfert entre machines » : la section des Réglages et
   son modal de progression.

   Demande de l'utilisateur (07/09/2026) : « lancement d'un script
   d'exportation de toute la bibliothèque et de tous les agents packagés
   pour un export inter-machines […] un bouton qui appelle le script
   d'export et indique à l'utilisateur quand l'export est terminé, avec le
   choix du disque ou de la destination […] de même, sur la même catégorie,
   la possibilité depuis l'autre appareil d'importer ce qui a été exporté
   […] un modal respectant les design.md doit apparaître et montrer
   l'avancement de l'export ou de l'import. »

   CHARTE (design_handoff_icones_couleurs, §1 et §2.1) : surfaces
   `--srf-panel` / `--srf-raised`, filets `--brd-hard` / `--brd-soft`,
   textes `--txt-hi` / `--txt-base` / `--txt-mid` / `--txt-low` ; toute
   métadonnée technique en IBM Plex Mono 9,5 px, `letter-spacing:.12em`
   pour les en-têtes en capitales ; icônes 24×24, masses pleines
   `fill="currentColor"`, DEUX niveaux d'opacité — le sujet à 1, le support
   entre .26 et .45 — et aucun arrondi de châssis.

   Le travail vit côté serveur (service `transfert`) : cet écran le lance,
   MONTRE l'avancement, et dit ce qui est arrivé. Il n'écrit rien lui-même.
   Écrit avec le runtime JSX du bundle (`r.jsx` / `r.jsxs`, enfants dans
   `children`) et ses crochets React (`x.useState`…) : c'est la convention
   des couches injectées de ce dépôt. */

var DZT_MONO = "'IBM Plex Mono', ui-monospace, Consolas, monospace";

function dztOctets(n) {
  n = Number(n) || 0;
  if (n < 1024) return n + " o";
  var u = ["Ko", "Mo", "Go", "To"], i = -1;
  do { n /= 1024; i++; } while (n >= 1024 && i < u.length - 1);
  return (n < 10 ? n.toFixed(1) : Math.round(n)) + " " + u[i];
}

/* Deux icônes aux règles du §2.1 : un plateau (support, opacité .38) et une
   flèche (sujet, opacité 1) qui sort ou qui rentre. C'est ce contraste
   interne qui les distingue à 16 px sur fond sombre. */
function dztIcone(sens, taille) {
  var t = taille || 18;
  return r.jsxs("svg", { viewBox: "0 0 24 24", fill: "currentColor",
    width: t, height: t, "aria-hidden": true,
    style: { display: "block" }, children: [
      r.jsx("path", { opacity: ".38",
        d: "M3.4 14.6h2.4v3.8h12.4v-3.8h2.4v6.2H3.4z" }, "p"),
      sens === "export"
        ? r.jsx("path", { d: "M12 2.6 17 8.2h-3.4v6.6h-3.2V8.2H7z" }, "f")
        : r.jsx("path", { d: "M12 15.4 7 9.8h3.4V3.2h3.2v6.6H17z" }, "f")] });
}

var DZT_S = {
  voile: { position: "fixed", inset: 0, zIndex: 60, background: "#0a0c0fcc",
           display: "flex", alignItems: "center", justifyContent: "center",
           padding: 24 },
  modal: { width: 540, maxWidth: "100%", maxHeight: "86vh", display: "flex",
           flexDirection: "column", background: "var(--srf-panel, #13171c)",
           border: "1px solid var(--brd-hard, #20262d)",
           boxShadow: "0 24px 64px rgba(0,0,0,.6)" },
  tete: { display: "flex", alignItems: "center", gap: 10, padding: "12px 14px",
          borderBottom: "1px solid var(--brd-soft, #1c2229)" },
  titre: { fontSize: 13, fontWeight: 600, color: "var(--txt-hi, #eef2f6)" },
  corps: { padding: 14, overflowY: "auto", display: "flex",
           flexDirection: "column", gap: 10 },
  entete: { font: "500 9.5px " + DZT_MONO, letterSpacing: ".12em",
            textTransform: "uppercase", color: "var(--txt-low, #5f6873)" },
  mono: { font: "400 10.5px " + DZT_MONO, color: "var(--txt-mid, #8b959f)" },
  faible: { font: "400 10.5px " + DZT_MONO, color: "var(--txt-low, #5f6873)",
            lineHeight: 1.6 },
  champ: { flex: 1, minWidth: 0, height: 28, padding: "0 8px", fontSize: 12,
           background: "var(--srf-raised, #171c22)",
           color: "var(--txt-base, #cfd6dd)",
           border: "1px solid var(--brd-hard, #20262d)", outline: "none" },
  pied: { display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
          borderTop: "1px solid var(--brd-soft, #1c2229)" },
  erreur: { fontSize: 12.5, color: "#e08a8a", lineHeight: 1.5 },
};

function dztBouton(o) {
  var base = { height: 28, padding: "0 12px", fontSize: 12,
    cursor: o.disabled ? "not-allowed" : "pointer",
    border: "1px solid var(--brd-hard, #20262d)",
    background: o.primaire ? "var(--brand, #4a90e2)"
      : "var(--srf-raised, #171c22)",
    color: o.primaire ? "#0a0c0f" : "var(--txt-base, #cfd6dd)",
    opacity: o.disabled ? .45 : 1, display: "flex", alignItems: "center",
    gap: 6 };
  return r.jsx("button", { type: "button", disabled: !!o.disabled,
    title: o.title || "", onClick: o.disabled ? undefined : o.onClick,
    style: Object.assign(base, o.style || {}), children: o.children });
}

/* La barre d'avancement : un rectangle, aucun arrondi (charte §1.4 du
   handoff Vectorlab, reprise ici — le rayon appartient au dessin, pas au
   châssis). */
function dztBarre(pct) {
  var p = Math.max(0, Math.min(100, Number(pct) || 0));
  return r.jsx("div", { role: "progressbar", "aria-valuenow": p,
    "aria-valuemin": 0, "aria-valuemax": 100,
    style: { height: 6, background: "var(--srf-raised, #171c22)",
             border: "1px solid var(--brd-hard, #20262d)" },
    children: r.jsx("div", { style: { height: "100%", width: p + "%",
      background: "var(--brand, #4a90e2)",
      transition: "width .2s linear" } }) });
}

function DzTransfert() {
  var s1 = x.useState(null), info = s1[0], setInfo = s1[1];
  var s2 = x.useState(""), dest = s2[0], setDest = s2[1];
  var s3 = x.useState(""), dossier = s3[0], setDossier = s3[1];
  var s4 = x.useState(null), modal = s4[0], setModal = s4[1];
  var s5 = x.useState(null), job = s5[0], setJob = s5[1];
  var s6 = x.useState(null), apercu = s6[0], setApercu = s6[1];
  var s7 = x.useState(""), erreur = s7[0], setErreur = s7[1];
  var tic = x.useRef(null);

  x.useEffect(function () {
    fetch("/api/transfer/destinations")
      .then(function (rp) { return rp.ok ? rp.json() : null; })
      .then(function (d) {
        if (!d) return;
        setInfo(d);
        if (d.destinations && d.destinations.length) {
          setDest(d.destinations[0].chemin);
        }
      }).catch(function () { /* hors ligne : le champ libre reste */ });
    return function () { if (tic.current) clearInterval(tic.current); };
  }, []);

  function suivre(jid) {
    if (tic.current) clearInterval(tic.current);
    tic.current = setInterval(function () {
      fetch("/api/transfer/jobs/" + jid)
        .then(function (rp) { return rp.ok ? rp.json() : null; })
        .then(function (j) {
          if (!j) return;
          setJob(j);
          if (j.statut === "fini" || j.statut === "echec") {
            clearInterval(tic.current);
            tic.current = null;
          }
        }).catch(function () { /* un creux réseau ne casse pas le suivi */ });
    }, 700);
  }

  function envoyer(url, corps) {
    return fetch(url, { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps) }).then(function (rp) {
        return rp.json().catch(function () { return {}; })
          .then(function (d) {
            if (!rp.ok) throw new Error(d.detail || rp.statusText);
            return d;
          });
      });
  }

  function lancer(sens) {
    setErreur("");
    setJob(null);
    var url = sens === "export" ? "/api/transfer/export"
      : "/api/transfer/import";
    var corps = sens === "export" ? { destination: dest } : { dossier: dossier };
    envoyer(url, corps).then(function (d) {
      setJob({ statut: "en cours", sens: sens,
               etat: { phase: "démarrage", pct: 0 } });
      suivre(d.job_id);
    }).catch(function (e) { setErreur(String(e.message || e)); });
  }

  function inspecter() {
    setErreur("");
    setApercu(null);
    envoyer("/api/transfer/inspect", { dossier: dossier })
      .then(function (d) { setApercu(d.manifeste); })
      .catch(function (e) { setErreur(String(e.message || e)); });
  }

  function fermer() {
    if (job && job.statut === "en cours") return;   // jamais pendant le travail
    if (tic.current) { clearInterval(tic.current); tic.current = null; }
    setModal(null); setJob(null); setApercu(null); setErreur("");
  }

  var ap = (info && info.apercu) || null;
  var dests = (info && info.destinations) || [];
  var et = (job && job.etat) || null;
  var enCours = !!(job && job.statut === "en cours");
  var fini = !!(job && job.statut === "fini");
  var echec = !!(job && job.statut === "echec");
  var res = (job && job.resultat) || null;

  var dedans = [];
  if (modal === "export" && !job) {
    dedans.push(r.jsxs("div", { style: { display: "flex",
      flexDirection: "column", gap: 10 }, children: [
        r.jsx("div", { style: DZT_S.entete, children: "destination" }, "e"),
        dests.length
          ? r.jsx("div", { style: { display: "flex", flexDirection: "column",
              gap: 4 }, children: dests.map(function (d) {
                var actif = dest === d.chemin;
                return r.jsxs("div", { onClick: function () { setDest(d.chemin); },
                  style: { display: "flex", alignItems: "center", gap: 8,
                    padding: "6px 8px", cursor: "pointer", fontSize: 12,
                    border: "1px solid " + (actif ? "var(--brand, #4a90e2)"
                      : "var(--brd-hard, #20262d)"),
                    background: actif ? "var(--brand-soft, #1c2b3d)"
                      : "var(--srf-raised, #171c22)",
                    color: "var(--txt-base, #cfd6dd)" }, children: [
                      r.jsx("span", { children: d.nom }, "n"),
                      r.jsx("span", { style: { flex: 1 } }, "s"),
                      r.jsx("span", { style: DZT_S.mono,
                        children: dztOctets(d.libre) + " libres" }, "l")] },
                  d.chemin);
              }) }, "v")
          : r.jsx("div", { style: DZT_S.mono,
              children: "aucun volume détecté" }, "v"),
        r.jsxs("div", { style: { display: "flex", alignItems: "center",
          gap: 8 }, children: [
            r.jsx("span", { style: { width: 62, fontSize: 11,
              color: "var(--txt-mid, #8b959f)" }, children: "ou chemin" }, "t"),
            r.jsx("input", { value: dest, placeholder: "D:\\sauvegardes",
              onChange: function (ev) { setDest(ev.target.value); },
              style: DZT_S.champ }, "i")] }, "c"),
        ap ? r.jsx("div", { style: DZT_S.mono,
          children: ap.fichiers + " fichiers · " + dztOctets(ap.octets)
            + " — un dossier daté sera créé à la destination" }, "a") : null,
        r.jsx("div", { style: DZT_S.faible,
          children: "Les clés d'API ne partent JAMAIS : le fichier .env, les "
            + "journaux et tout ce que l'application sait reconstruire "
            + "(caches, aperçus) sont écartés." }, "g")] }, "x"));
  }
  if (modal === "import" && !job) {
    dedans.push(r.jsxs("div", { style: { display: "flex",
      flexDirection: "column", gap: 10 }, children: [
        r.jsx("div", { style: DZT_S.entete,
          children: "dossier du paquet" }, "e"),
        r.jsxs("div", { style: { display: "flex", alignItems: "center",
          gap: 8 }, children: [
            r.jsx("input", { value: dossier,
              placeholder: "E:\\DeepotusVideoGen-Transfert-2026-09-07-1200",
              onChange: function (ev) { setDossier(ev.target.value); },
              style: DZT_S.champ }, "i"),
            dztBouton({ onClick: inspecter, disabled: !dossier.trim(),
              title: "Lit le manifeste du paquet — rien n'est écrit",
              children: "Vérifier" })] }, "c"),
        apercu ? r.jsxs("div", { style: { display: "flex",
          flexDirection: "column", gap: 4, padding: 10,
          background: "var(--srf-raised, #171c22)",
          border: "1px solid var(--brd-hard, #20262d)" }, children: [
            r.jsx("div", { style: DZT_S.mono,
              children: "créé le " + apercu.cree_le + " · machine "
                + (apercu.machine || "?") + " · version "
                + (apercu.app_version || "?") }, "d"),
            r.jsx("div", { style: DZT_S.mono,
              children: apercu.fichiers + " fichiers · "
                + dztOctets(apercu.octets) }, "f"),
            r.jsx("div", { style: DZT_S.mono,
              children: Object.keys(apercu.lignes || {}).filter(function (k) {
                return apercu.lignes[k];
              }).map(function (k) {
                return apercu.lignes[k] + " " + k;
              }).join(" · ") || "aucun enregistrement" }, "l")] }, "p") : null,
        r.jsx("div", { style: DZT_S.faible,
          children: "L'import AJOUTE : ce que cette machine possède déjà n'est "
            + "ni écrasé ni effacé. Les chemins de la machine d'origine sont "
            + "ré-ancrés sur cette installation." }, "g")] }, "i"));
  }
  if (job) {
    dedans.push(r.jsxs("div", { style: { display: "flex",
      flexDirection: "column", gap: 8 }, children: [
        r.jsx("div", { style: DZT_S.entete,
          children: echec ? "échec" : fini ? "terminé" : "en cours" }, "e"),
        dztBarre(et ? et.pct : 0),
        r.jsx("div", { style: DZT_S.mono, children: et
          ? (et.phase + " · " + et.pct + " %"
             + (et.total ? " · " + et.fait + "/" + et.total + " fichiers" : "")
             + (et.octets_total ? " · " + dztOctets(et.octets) + " / "
                + dztOctets(et.octets_total) : ""))
          : "…" }, "m"),
        (et && et.fichier && enCours)
          ? r.jsx("div", { style: Object.assign({}, DZT_S.faible,
              { overflow: "hidden", textOverflow: "ellipsis",
                whiteSpace: "nowrap" }), children: et.fichier }, "f") : null,
        fini ? r.jsxs("div", { style: { fontSize: 12.5, lineHeight: 1.5,
          color: "var(--txt-base, #cfd6dd)" }, children: [
            r.jsx("div", { children: (job.sens === "import"
              || modal === "import") ? "Import terminé."
              : "Export terminé. Le paquet est ici :" }, "t"),
            r.jsx("div", { style: Object.assign({}, DZT_S.mono,
              { marginTop: 4, color: "var(--txt-hi, #eef2f6)",
                wordBreak: "break-all" }),
              children: (res && res.dossier) || (et && et.detail)
                || "" }, "d")] }, "ok") : null,
        echec ? r.jsx("div", { style: DZT_S.erreur,
          children: job.erreur || "raison non fournie" }, "k") : null] }, "p"));
  }
  if (erreur) {
    dedans.push(r.jsx("div", { style: DZT_S.erreur, children: erreur }, "err"));
  }

  var pied = [r.jsx("span", { style: { flex: 1 } }, "sp")];
  if (!job) {
    pied.push(dztBouton({ primaire: true,
      disabled: modal === "export" ? !dest.trim() : !dossier.trim(),
      onClick: function () { lancer(modal); },
      title: modal === "export"
        ? "Écrit un dossier daté à la destination choisie"
        : "Ajoute le contenu du paquet à cette installation",
      children: modal === "export" ? "Lancer l'export" : "Lancer l'import" }));
  } else if (!enCours) {
    pied.push(dztBouton({ primaire: true, onClick: fermer,
      children: "Fermer" }));
  }

  var vue = modal ? r.jsx("div", { style: DZT_S.voile,
    onClick: function (ev) {
      if (ev.target === ev.currentTarget) fermer();
    },
    children: r.jsxs("div", { role: "dialog", "aria-modal": "true",
      "aria-label": modal === "export" ? "Exporter vers une autre machine"
        : "Importer depuis une autre machine",
      style: DZT_S.modal, children: [
        r.jsxs("div", { style: DZT_S.tete, children: [
          r.jsx("span", { style: { color: "var(--brand, #4a90e2)" },
            children: dztIcone(modal, 18) }, "i"),
          r.jsx("span", { style: DZT_S.titre,
            children: modal === "export" ? "Exporter vers une autre machine"
              : "Importer depuis une autre machine" }, "t"),
          r.jsx("span", { style: { flex: 1 } }, "s"),
          dztBouton({ onClick: fermer, disabled: enCours,
            title: enCours ? "Transfert en cours — l'interrompre laisserait "
              + "un paquet incomplet" : "Fermer",
            style: { height: 24, padding: "0 8px" }, children: "×" })] }, "h"),
        r.jsx("div", { style: DZT_S.corps, children: dedans }, "c"),
        r.jsx("div", { style: DZT_S.pied, children: pied }, "f")] }) }) : null;

  return r.jsxs("div", { style: { display: "flex", flexDirection: "column",
    gap: 14, maxWidth: 640 }, children: [
      r.jsx("div", { style: { fontSize: 13, fontWeight: 600,
        color: "var(--txt-hi, #eef2f6)" },
        children: "Transfert entre machines" }, "t"),
      r.jsx("div", { style: { fontSize: 12.5, lineHeight: 1.6,
        color: "var(--txt-mid, #8b959f)" },
        children: "Emporte TOUT ce que cette installation a créé — la "
          + "bibliothèque et ses provenances, les rendus, la bible, les plans "
          + "de communication, les documents vectoriels, les séries de cartes, "
          + "les modèles 3D — vers une autre machine où l'application est "
          + "installée. Les clés d'API restent ici." }, "d"),
      ap ? r.jsx("div", { style: DZT_S.mono,
        children: ap.fichiers + " fichiers · " + dztOctets(ap.octets)
          + " à emporter" }, "a") : null,
      r.jsxs("div", { style: { display: "flex", gap: 8 }, children: [
        dztBouton({ onClick: function () { setModal("export"); },
          title: "Écrire un paquet de transfert sur un disque",
          children: [dztIcone("export", 16),
                     r.jsx("span", { children: "Exporter…" }, "l")] }),
        dztBouton({ onClick: function () { setModal("import"); },
          title: "Reprendre un paquet venu d'une autre machine",
          children: [dztIcone("import", 16),
                     r.jsx("span", { children: "Importer…" }, "l")] })] }, "b"),
      vue] });
}
/*__DZ_TRANSFERT_END__*/
