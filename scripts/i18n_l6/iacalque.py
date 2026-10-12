"""t190 (G8, génération IA) — l'image IA PAR CALQUE du Vectorlab, postérieure à L6 : les éditions de code de
js/mod-image.js (generer() ouvre le panneau, pose sur un calque donné, « Retirer le fond » du panneau Image, dépôt
d'un blob au magasin, initIaCalque), de js/mod-layers.js (bouton « Image IA sur ce calque » de la barre d'actions) et
de js/mod-doc.js (t190-bis : op_image_remplacer, la commande réversible du détourage, à côté d'op_image_rev) sont
consignées ICI, en éditions S sur la source de BASE, pour que la table reste réversible (test_i18n_l6 [2]). Le module
neuf js/mod-iacalque.js n'est pas dans la BASE (ni dans la table ni dans les restes) : ses clés sont des entrées H,
contrôlées par l'usage (test_i18n_l6 [3]). L'ancienne saisie de generer() (texte.py, lignes 223-232 : dialogue
saisir) est retirée : la fonction entière est réécrite par l'édition ci-dessous."""
from outils import L, S, X, H  # noqa: F401

IMG = "js/mod-image.js"
LAY = "js/mod-layers.js"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


GENERER_AVANT = c('''  async function generer() {
    const p = await VL.dialogue.saisir("Décrire l'image à générer (dépense la clé du fournisseur des Réglages) :", { valeur: "", titre: "Générer une image", valider: "Générer" });
    if (!p) return;
    VL.toast("génération en cours…");
    const r = await fetch("/api/images/generate", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: p, n: 1, source: "vectorlab" }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    const nom = (d.images || [])[0];
    if (!nom) throw new Error("la génération n'a rendu aucune image");
    await poserDepuisLibrary(nom);
  }''')

GENERER_APRES = c('''  // t190 : le panneau « Image IA sur le calque » s'ouvre sur le calque actif (calque cible, modèle, prix serveur,
  // détourage) — menu Fichier, flyout Image ; le tir part du panneau (mod-iacalque). t190-bis : la voie « tir direct
  // generer(opts) » est retirée, aucun appelant ne passait d'options
  async function generer() {
    VL.iaCalque.ouvrir(etat.calqueActif);
  }''')

ENTREES = [
    # ── js/mod-image.js ──
    S(IMG, 10, 'reperes_rects } from "./mod-doc.js";',
      c('reperes_rects } from "./mod-doc.js";\nimport { initIaCalque, chercher } from "./mod-iacalque.js";'), {}),
    # t190-bis : un serveur injoignable n'affiche plus « Failed to fetch » brut (chercher traduit le TypeError)
    S(IMG, 92, "    const r = await fetch(`/api/vector/docs/", "    const r = await chercher(`/api/vector/docs/", {}),
    S(IMG, 129, '    const r = await fetch("/api/images/" + encodeURIComponent(nom));',
      '    const r = await chercher("/api/images/" + encodeURIComponent(nom));', {}),
    S(IMG, 116, "async function poserBlob(blob) {", "async function poserBlob(blob, calqueId) {", {}),
    S(IMG, 123, "VL.executer(op_ajouter, etat.calqueActif,", "VL.executer(op_ajouter, calqueId || etat.calqueActif,", {}),
    S(IMG, 128, "async function poserDepuisLibrary(nom) {", "async function poserDepuisLibrary(nom, calqueId) {", {}),
    S(IMG, 131, "    await poserBlob(await r.blob());",
      c('    const id = await poserBlob(await r.blob(), calqueId);\n'
        '    // t190 : VL.executer AVALE l\'échec de op_ajouter (calque verrouillé ou supprimé entre-temps) — jamais « posée »\n'
        '    if (!id) throw new Error(T("vectorlab.image.pose_impossible", { nom }));'),
      {"vectorlab.image.pose_impossible": ("pose de « {nom} » impossible", "could not place “{nom}”")}),
    S(IMG, 133, "  }", c("    return id;\n  }"), {}),
    S(IMG, 222, GENERER_AVANT, GENERER_APRES, {}),
    S(IMG, 293, '    $("#imVectoriser").addEventListener("click", () => { if (VL.vectoriser) VL.vectoriser(o.id); });',
      c('''    $("#imVectoriser").addEventListener("click", () => { if (VL.vectoriser) VL.vectoriser(o.id); });
    // t190 : « Retirer le fond » — une commande réversible (mod-iacalque.retirerFondFlux)
    const ligneDetour = document.createElement("div");
    ligneDetour.className = "ap-ligne"; ligneDetour.id = "imDetourLigne";
    hote.appendChild(ligneDetour);
    VL.iaCalque.ligneDetour(ligneDetour, o);'''), {}),
    S(IMG, 322, "  VL.reperesRects = () => reperes_rects(etat.doc);",
      c('''  VL.reperesRects = () => reperes_rects(etat.doc);
  // t190 : un blob au magasin du DOCUMENT (PNG), sans le poser — le détourage y range sa nouvelle image
  VL.deposerBlob = async (blob) => {
    const im = await decoder(blob);
    const png = await versPNG(blob, im);
    return { href: await deposer(png), nat: { w: im.naturalWidth, h: im.naturalHeight } };
  };
  initIaCalque(VL);       // t190 : le panneau « Image IA sur le calque » (VL.iaCalque)'''), {}),

    # ── js/mod-layers.js : le bouton de la barre d'actions (agit sur le calque ACTIF, comme renommer / fx) ──
    S(LAY, 92, '    section.appendChild(actions);',
      c('    // t190 : « Image IA sur ce calque », après les effets (agit sur le calque actif, comme renommer / fx)\n'
        '    actions.querySelector(\'[data-act="fx"]\').insertAdjacentHTML("afterend", `\n      <button data-act="ia" '
        'title="${T("vectorlab.iacalque.bouton_titre")}" aria-label="${T("vectorlab.iacalque.bouton")}">'
        '${dzi("dz-media-generer-image", 16)}</button>`);\n    section.appendChild(actions);'),
      {"vectorlab.iacalque.bouton": ("Image IA sur ce calque", "AI image on this layer"),
       "vectorlab.iacalque.bouton_titre": ("Générer une image IA sur le calque actif (modèle, prix, détourage)",
                                           "Generate an AI image on the active layer (model, price, background removal)")}),
    S(LAY, 209, 'else if (act === "pixel") {',
      c('else if (act === "ia" && c) VL.iaCalque.ouvrir(c.id);\n    else if (act === "pixel") {'),
      {}),

    # ── js/mod-doc.js : la commande réversible du détourage, à côté d'op_image_rogner / op_image_rev ──
    S("js/mod-doc.js", 1658, "/* ── lot E : doc.pixelart = {tuile {w,h} entiers ≥ 1, palette [hex],",
      c('''// t190 : la commande RÉVERSIBLE du détourage (« Retirer le fond », mod-iacalque) : l'objet désigne une AUTRE
// image du magasin (href) — Annuler rend l'href d'avant, dont le PNG n'a pas été touché. La révision raster et
// l'empreinte de l'ancienne image ne suivent pas ; un rognage qui ne tient plus dans la nouvelle taille native tombe.
// Rend true : VL.executer rend undefined quand il avale un échec. t190-bis : l'image peut être l'ENFANT d'un groupe
// (Ctrl+clic la sélectionne, le panneau Image lui offre « Retirer le fond ») — la recherche descend dans les groupes.
export function image_profonde(doc, id) {
  const visiter = (objs) => {
    for (const o of objs || []) {
      if (o.id === id) return o;
      if (o.type === "groupe") { const x = visiter(o.enfants); if (x) return x; }
    }
    return null;
  };
  for (const c of doc.calques) {
    const o = visiter(c.objets);
    if (o) {
      if (o.type !== "image") throw new Error(T("vectorlab.doc.pas_image", { id }));
      return o;
    }
  }
  throw new Error(T("vectorlab.doc.image_introuvable", { id }));
}
export function op_image_remplacer(doc, id, href, nat) {
  const o = image_profonde(doc, id);
  if (!href || !(nat && nat.w > 0 && nat.h > 0)) throw new Error(T("vectorlab.iacalque.image_invalide"));
  o.href = String(href);
  const memeTaille = o.nat && o.nat.w === nat.w && o.nat.h === nat.h;
  o.nat = { w: nat.w, h: nat.h };
  delete o.rev; delete o.px;
  if (o.rognage && !memeTaille) delete o.rognage;
  return true;
}

/* ── lot E : doc.pixelart = {tuile {w,h} entiers ≥ 1, palette [hex],'''), {}),

    # ── clés reprises de l'ancienne saisie de generer() (texte.py) : mêmes textes ──
    H("vectorlab.image.generation", "génération en cours…", "generating…"),
    H("vectorlab.image.generation_vide", "la génération n'a rendu aucune image", "the generation returned no image"),

    # ── js/mod-iacalque.js (module neuf, hors BASE) ──
    H("vectorlab.iacalque.titre", "Image IA sur le calque", "AI image on layer"),
    H("vectorlab.iacalque.calque", "Calque", "Layer"),
    H("vectorlab.iacalque.calque_aide", "Le calque qui reçoit l'image (les calques verrouillés n'y sont pas)",
      "The layer that receives the image (locked layers are not listed)"),
    H("vectorlab.iacalque.placeholder", "Décrire l'image à générer…", "Describe the image to generate…"),
    H("vectorlab.iacalque.modele_aide",
      "Le modèle qui dépense sa clé ; une option sans clé reste choisissable (clé à ajouter dans Réglages)",
      "The model that spends its key; an option without a key stays selectable (add the key in Settings)"),
    H("vectorlab.iacalque.retirer_fond", "Retirer le fond", "Remove the background"),
    H("vectorlab.iacalque.retirer_fond_titre", "Retirer le fond de cette image (Ctrl+Z rend l'image d'avant)",
      "Remove this image's background (Ctrl+Z brings back the previous image)"),
    H("vectorlab.iacalque.detourage", "Détourage", "Remove BG"),
    H("vectorlab.iacalque.detour_aide", "Le modèle de détourage (prix par image ; local = gratuit)",
      "The background-removal model (price per image; local = free)"),
    H("vectorlab.iacalque.fond", "Fond", "Background", contexte=True),
    H("vectorlab.iacalque.sujet", "Sujet à garder", "Subject to keep"),
    H("vectorlab.iacalque.sujet_aide", "Ce modèle détoure un sujet nommé : dites lequel garder",
      "This model cuts out a named subject: say which one to keep"),
    H("vectorlab.iacalque.sujet_requis", "dites quel sujet garder : ce modèle détoure un sujet nommé",
      "say which subject to keep: this model cuts out a named subject"),
    H("vectorlab.iacalque.prix", "Prix estimé : {prix}", "Estimated price: {prix}"),
    H("vectorlab.iacalque.prix_partiel", " (+ détourage à mesurer)", " (+ background removal to be measured)"),
    H("vectorlab.iacalque.prix_partiel_image", " (+ image à mesurer)", " (+ image to be measured)"),
    H("vectorlab.iacalque.prix_gratuit", "Prix estimé : gratuit (local)", "Estimated price: free (local)"),
    H("vectorlab.iacalque.prix_a_mesurer", "Prix estimé : prix à mesurer", "Estimated price: price to be measured"),
    H("vectorlab.iacalque.prix_inconnu", "Prix estimé : …", "Estimated price: …"),
    H("vectorlab.iacalque.generer_sur", "Générer sur « {nom} »", "Generate on “{nom}”"),
    H("vectorlab.iacalque.en_cours", "en cours…", "in progress…"),
    H("vectorlab.iacalque.posee", "« {nom} » posée sur « {calque} »", "“{nom}” placed on “{calque}”"),
    H("vectorlab.iacalque.calque_absent", "calque inconnu : {id}", "unknown layer: {id}"),
    H("vectorlab.iacalque.calque_verrouille",
      "le calque « {nom} » est verrouillé : déverrouillez-le ou choisissez-en un autre",
      "layer “{nom}” is locked: unlock it or choose another one"),
    H("vectorlab.iacalque.prompt_vide", "décrivez d'abord l'image à générer", "describe the image to generate first"),
    H("vectorlab.iacalque.detour_modele", "choisissez un modèle de détourage", "choose a background-removal model"),
    H("vectorlab.iacalque.detour_vide", "le détourage n'a rendu aucune image", "background removal returned no image"),
    H("vectorlab.iacalque.detour_en_cours", "détourage en cours…", "removing the background…"),
    H("vectorlab.iacalque.detour_fait", "fond retiré (Ctrl+Z rend l'image d'avant)",
      "background removed (Ctrl+Z brings back the previous image)"),
    H("vectorlab.iacalque.cle_absente", "Clé absente — {detail}", "Missing key — {detail}"),
    H("vectorlab.iacalque.catalogue_absent", "liste des modèles indisponible", "model list unavailable"),
    H("vectorlab.iacalque.modeles_vides", "aucun modèle d'image disponible", "no image model available"),
    H("vectorlab.iacalque.calque_disparu", "le calque demandé n'existe plus : l'image ira sur « {nom} »",
      "the requested layer no longer exists: the image will go on “{nom}”"),
    H("vectorlab.iacalque.reessayer", "Réessayer", "Retry"),
    H("vectorlab.iacalque.masque", " (masqué)", " (hidden)"),
    H("vectorlab.iacalque.reseau", "serveur injoignable : vérifiez que DeepotusVideo tourne",
      "server unreachable: check that DeepotusVideo is running"),
    H("vectorlab.iacalque.biblio_sans_nom", "la Bibliothèque n'a rendu aucun nom pour l'image à détourer",
      "the Library returned no name for the image to cut out"),
    H("vectorlab.iacalque.image_introuvable", "image introuvable : {id}", "image not found: {id}"),
    H("vectorlab.iacalque.image_invalide", "image détourée illisible", "unreadable cut-out image"),
    H("vectorlab.iacalque.image_illisible", "image {href} illisible", "image {href} unreadable"),
    H("vectorlab.iacalque.detour_cle",
      "la clé {cle} manque pour ce détourage : ajoutez-la dans Réglages ou décochez « Retirer le fond »",
      "the {cle} key is missing for this background removal: add it in Settings or untick “Remove the background”"),
    H("vectorlab.iacalque.detour_cle_image", "la clé {cle} manque pour ce détourage : ajoutez-la dans Réglages",
      "the {cle} key is missing for this background removal: add it in Settings"),
    H("vectorlab.iacalque.pose_echouee", "{raison} — image gardée en Bibliothèque : {nom}",
      "{raison} — image kept in the Library: {nom}"),
    H("vectorlab.iacalque.pose_refusee", "la pose a été refusée", "placing was refused"),
    H("vectorlab.iacalque.detour_echoue_pose",
      "fond non retiré ({raison}) : l'image est posée telle quelle sur « {calque} » — « Retirer le fond » du panneau Image pour réessayer",
      "background not removed ({raison}): the image is placed as is on “{calque}” — use “Remove the background” in the Image panel to retry"),
    H("vectorlab.iacalque.detour_remplacement",
      "le fond retiré n'a pas remplacé l'image — image détourée gardée en Bibliothèque : {nom}",
      "the cut-out did not replace the image — cut-out image kept in the Library: {nom}"),
    H("vectorlab.iacalque.aucun_calque_libre",
      "tous les calques sont verrouillés : déverrouillez-en un pour y poser l'image",
      "all layers are locked: unlock one to place the image on it"),
    H("vectorlab.iacalque.meme_image", "le détourage rendrait la même image : rien n'est remplacé",
      "background removal would return the same image: nothing is replaced"),
    # suite de t190 (12/10) : la case « Guider par les calques du dessous » (mod-iacalque, hors base L6)
    H("vectorlab.iacalque.guide", "Guider par les calques du dessous",
      "Guide with the layers below"),
    H("vectorlab.iacalque.guide_aide", "Le modèle part du rendu de ce qui est visible SOUS le calque cible (calques inférieurs visibles, au format de la page) ; seuls les modèles qui acceptent une image d'entrée sont proposés",
      "The model starts from a render of what is visible BELOW the target layer (visible lower layers, at the page format); only models that accept an input image are offered"),
    H("vectorlab.iacalque.guide_aucun_modele", "aucun modèle de la liste ne sait partir d'une image : décochez « Guider par les calques du dessous »",
      "no model in the list can start from an image: untick “Guide with the layers below”"),
    H("vectorlab.iacalque.guide_choisir", "choisissez un modèle qui sait partir d'une image pour guider",
      "choose a model that can start from an image to guide"),
    H("vectorlab.iacalque.guide_modele", "« {modele} » ne sait pas partir d'une image : choisissez un modèle qui guide",
      "“{modele}” cannot start from an image: choose a model that can guide"),
    H("vectorlab.iacalque.guide_modele_remplace", "« {avant} » ne sait pas partir d'une image : « {apres} » est choisi pour guider",
      "“{avant}” cannot start from an image: “{apres}” is chosen to guide"),
    H("vectorlab.iacalque.guide_rien", "rien n'est visible sous « {nom} » : aucun calque du dessous à envoyer comme guide",
      "nothing is visible below “{nom}”: no lower layer to send as a guide"),
    H("vectorlab.iacalque.guide_sans_nom", "la Bibliothèque n'a rendu aucun nom pour le guide",
      "the Library returned no name for the guide"),
    H("vectorlab.iacalque.posee_guide", "« {nom} » posée sur « {calque} », guidée par « {guide} »",
      "“{nom}” placed on “{calque}”, guided by “{guide}”"),
]
