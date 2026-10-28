"""t312 (C1 Scan, tâche 6, 28/10/2026) — la boîte « Scanner une page » dans l'Atelier, posée APRÈS L8.

La table réversible L8 (scripts/i18n_l8_paires.json) exige : source du poste == base 1515d67b + éditions. Une
modification du code d'après L8 passe donc par ici, comme une édition S() (même mécanisme que t182.py / t183.py /
t189.py). Plan docs/superpowers/plans/2026-10-28-t312-scan-texte.md, Décision 7 :
- deux boutons « Scanner une page » (#scanBtn juste après « Importer (txt/docx/pdf) », #scanChapBtn dans la barre des
  chapitres juste après « Manuscrit »), POSÉS PAR scanBoutons() au chargement, libellés par dzT : index.html n'est pas
  réécrit par L8 mais ses gardes X sont relues à leurs positions de BASE (--restes) — une ligne insérée avant elles
  les décalerait ; la page ne gagne donc que la balise <script src="/shared/dz-scan.js"> (en fin de page) ;
- scanOuvrir() ouvre window.__dzScan (/shared/dz-scan.js) avec les trois envois de l'hôte :
  scanInserer (texte au curseur de #script, puis renderScript() et scheduleSave(), comme une frappe),
  scanCreerChapitres (un POST /chapters par chapitre du découpage, série courante, puis loadChapters),
  scanManuscrit (un File « scan.txt » par msRun, le même envoi que le fichier choisi : /atelier/manuscript) ;
- msRun(impose) accepte ce File imposé ; appelé par son bouton, il reçoit l'évènement et lit #msFile comme avant.
Le secours Claude (devis, confirmation, 409, rendu partiel) et le 402 du plafond (dz-plafonds.js) vivent dans la boîte.
"""
from outils import S

_AT = "atelier/atelier.js"


def C(t: str) -> str:
    """Les sources sont en CRLF : le code ci-dessous est écrit en LF puis converti."""
    return t.replace("\r\n", "\n").replace("\n", "\r\n")


MSRUN_AV = C('''async function msRun() {
  const f = $("#msFile").files && $("#msFile").files[0];''')

MSRUN_AP = C('''async function msRun(impose) {
  // t312 : un File imposé (le texte d'un scan, « scan.txt ») suit le même envoi que le fichier choisi
  const f = (typeof File === "function" && impose instanceof File) ? impose : ($("#msFile").files && $("#msFile").files[0]);''')

FONCTIONS = C('''/* ═════════ t312 (C1 Scan) — la boîte « Scanner une page » (/shared/dz-scan.js) ═════════
   Trois envois (Décision 7 du plan t312) : le texte au curseur du script puis scheduleSave() ; un POST /chapters par
   chapitre du découpage, dans la série courante, puis la liste relue ; un manuscrit « scan.txt » par msRun (l'agent
   Manuscrit). Un refus LÈVE une erreur : la boîte (au-dessus des toasts de la page) affiche son message et reste
   ouverte. */
function scanInserer(texte) {
  if (!chapter) throw new Error(dzT("atelier.at3_w.cree_chapitre"));
  const ta = $("#script");
  if (ta.readOnly) throw new Error(dzT("atelier.t312_scan.lecture_seule"));
  // au curseur, SANS remplacer une sélection : le texte va après sa fin
  const b = typeof ta.selectionEnd === "number" ? ta.selectionEnd : ta.value.length;
  ta.setRangeText(texte, b, b, "end");
  renderScript(); scheduleSave();
  if (typeof refreshSelBar === "function") refreshSelBar();
  toast(dzT("atelier.t312_scan.insere", { n: texte.length }));
  return true;
}

async function scanCreerChapitres(liste) {
  const serie = $("#chapterSeries").value;
  let premier = null, crees = 0;
  try {
    for (const c of liste) {
      const ch = await api.send("POST", "/chapters", { title: c.titre, series: serie, script_text: c.texte, spans: [] });
      if (!premier) premier = ch.id;
      crees++;
    }
  } catch (e) {
    const err = new Error(e && e.message ? e.message : String(e));
    err.crees = crees;                            // la boîte dit k sur n et ne recrée que les restants
    throw err;
  } finally {
    if (premier) await loadChapters(premier);     // un échec en route : les chapitres déjà créés sont listés
  }
  toast(dzT("atelier.t312_scan.chapitres", { n: liste.length }));
  return true;
}

async function scanManuscrit(texte) {
  // un seul job manuscrit à la fois : celui du bouton « Lancer » ou un scan déjà envoyé
  if ($("#msRun").disabled || msPolling) throw new Error(dzT("atelier.t312_scan.ms_en_cours"));
  if (!$("#msSeries").value.trim() && $("#chapterSeries").value.trim()) $("#msSeries").value = $("#chapterSeries").value.trim();
  $("#msModal").classList.remove("hidden");
  await msRun(new File([texte], "scan.txt", { type: "text/plain" }));
  return true;
}

/* les deux boutons, chacun après son voisin ; l'icône est la chaîne fixe de dzIcone, le libellé un nœud texte */
function scanBoutons() {
  const poser = (id, titre, voisin) => {
    if (!voisin || document.getElementById(id)) return;
    const b = document.createElement("button");
    b.id = id; b.type = "button"; b.className = "btn"; b.title = dzT(titre);
    b.innerHTML = ico("dz-media-image");
    b.appendChild(document.createTextNode(" " + dzT("atelier.t312_scan.bouton")));
    b.addEventListener("click", scanOuvrir);
    voisin.insertAdjacentElement("afterend", b);
  };
  poser("scanBtn", "atelier.t312_scan.bouton_t", $("#importFile"));
  poser("scanChapBtn", "atelier.t312_scan.chap_t", $("#msBtn"));
}

function scanOuvrir() {
  if (!window.__dzScan) { toast(dzT("atelier.t312_scan.absent"), true); return; }
  window.__dzScan.ouvrir({ hote: "atelier", serie: $("#chapterSeries").value, inserer: scanInserer,
                           creerChapitres: scanCreerChapitres, importerManuscrit: scanManuscrit });
}

''')

POLL_AV = '    msPolling = setInterval(async () => {'
POLL_AP = C('''    if (msPolling) { clearInterval(msPolling); msPolling = null; }   // t312 : jamais deux sondes (la première fuirait)
    msPolling = setInterval(async () => {''')

ECOUTE_AV = '  $("#msRun").addEventListener("click", msRun);'
ECOUTE_AP = C('''  $("#msRun").addEventListener("click", msRun);
  // t312 : « Scanner une page » — près d'« Importer » et dans la barre des chapitres (mêmes envois)
  scanBoutons();''')

DICO = {
    "atelier.t312_scan.lecture_seule": ("Chapitre emporté par le téléphone : lecture seule, rien n'est inséré.",
                                        "Chapter taken by the phone: read-only, nothing is inserted."),
    "atelier.t312_scan.insere": ("{n} caractères insérés depuis le scan.", "{n} characters inserted from the scan."),
    "atelier.t312_scan.chapitres": ("{n} chapitre(s) créé(s) depuis le scan.", "{n} chapter(s) created from the scan."),
    "atelier.t312_scan.bouton": ("Scanner une page", "Scan a page"),
    "atelier.t312_scan.bouton_t": ("Lire le texte d'une à dix pages scannées (image ou PDF) et l'insérer au curseur — "
                                   "lecture locale gratuite, Claude en secours payant après devis",
                                   "Read the text of one to ten scanned pages (image or PDF) and insert it at the cursor — "
                                   "free local reading, Claude as a paid fallback after a quote"),
    "atelier.t312_scan.chap_t": ("Scanner des pages : en faire de nouveaux chapitres de la série, ou un manuscrit pour "
                                 "l'agent Manuscrit",
                                 "Scan pages: turn them into new chapters of the series, or a manuscript for the "
                                 "Manuscript agent"),
    "atelier.t312_scan.ms_en_cours": ("Un manuscrit est déjà en cours d'import : attends sa fin.",
                                      "A manuscript is already being imported: wait for it to finish."),
    "atelier.t312_scan.absent": ("La boîte Scan n'est pas chargée : recharge la page.",
                                 "The Scan box is not loaded: reload the page."),
}

ENTREES = [
    S(_AT, 1603, MSRUN_AV, MSRUN_AP, {}),
    S(_AT, 1619, POLL_AV, POLL_AP, {}),
    S(_AT, 1646, "/* ═════════ utilitaires ═════════ */", FONCTIONS + "/* ═════════ utilitaires ═════════ */", DICO),
    S(_AT, 1898, ECOUTE_AV, ECOUTE_AP, {}),
]
