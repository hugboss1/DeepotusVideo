"""t421 (cartes hexagonales, 07/11/2026, tâche 5) — « Nouveau jeu depuis des images », posé APRÈS L7 (comme t421.py).

core.js :
- la galerie gagne une section « Nouveau jeu depuis des images » (bouton #galImages) en tête de son corps ; le bouton
  ferme la galerie et ouvre le dialogue de js/depuis-images.js (window.CFDepuisImages.ouvrir) ;
- `CF.bibliotheque` : la Bibliothèque en LECTURE (images, projets, projet) et l'import d'un fichier
  (POST /api/images/upload), plus `url(nom)`, l'adresse servie d'une image (GET /api/images/{nom}) — le réseau reste au
  CORE (§8 : aucun fetch dans une pièce), comme CF.images et CF.models ;
- `CF.deckDepuisImages(corps)` : écrit le jeu ouvert, crée le deck par POST /api/cards/decks/depuis-images (route de
  la tâche 4), puis l'OUVRE par ?deck= (galGo, comme « Nouveau jeu depuis ce modèle ») ;
- `CF.libelleFormat(id)` : le libellé affiché d'un format, la règle du sélecteur de format de la barre (les deux
  libellés traduits, les hexagones par hexLabel, sinon la table) ; le sélecteur n'est pas touché.
Les textes du dialogue lui-même (js/depuis-images.js, fichier neuf hors de la base L7) sont des entrées H.
Un rectangle ne change d'aucun pixel : rien du rendu n'est touché. Les sauts de ligne des insertions sont CRLF.
"""
from outils import H, S

C = "js/core.js"


def _crlf(t):
    return t.replace("\n", "\r\n")


_SECTION = r"""    + '<div class="cf-gal-body">'
    /* t421 : « Nouveau jeu depuis des images » (js/depuis-images.js) */
    + '<section class="cf-gal-sec cf-gal-images"><h3>' + dzT("cartes.depuis.gal_titre") + '</h3>'
    + '<p class="cf-gal-note">' + dzT("cartes.depuis.gal_note") + '</p>'
    + '<button class="btn strong sm" id="galImages" type="button">' + dzT("cartes.depuis.gal_bouton") + '</button></section>'"""

_CABLE = r"""if (i) i.addEventListener("click", galImport);
    const gi = el("#galImages"); if (gi) gi.addEventListener("click", galImages);"""

_FONCTIONS = r"""/* ── t421 : NOUVEAU JEU DEPUIS DES IMAGES ────────────────────────────────
     Le dialogue vit dans js/depuis-images.js (window.CFDepuisImages) ; la
     galerie lui cede la place. Ses dehors sont tenus ICI (§8) : la
     Bibliotheque en lecture, l'import d'un fichier, la creation du deck. */
  function galImages() {
    const D = (typeof window !== "undefined") ? window.CFDepuisImages : null;
    if (!D || typeof D.ouvrir !== "function") { toast(dzT("cartes.depuis.absent"), true); return; }
    closeGallery();
    D.ouvrir();
  }
  const bibliotheque = Object.freeze({
    /* GET /api/images : nom, dimensions (lues par le serveur), provenance */
    async images() {
      const d = await jsonNamed("GET", "/images");
      return (Array.isArray(d && d.images) ? d.images : []).filter(isPlain).map((x) => ({
        filename: String(x.filename || ""), width: Number(x.width) || null, height: Number(x.height) || null,
        source: String(x.source || ""),
      })).filter((x) => x.filename);
    },
    async projets() {
      const d = await jsonNamed("GET", "/library/projets");
      return (Array.isArray(d && d.projets) ? d.projets : []).filter(isPlain).map((p) => ({
        id: String(p.id || ""), nom: String(p.nom || ""), n: Number(p.n) || 0,
      })).filter((p) => p.id);
    },
    /* les items d'un projet : `ref` est le nom de fichier pour une image */
    async projet(id) {
      const d = await jsonNamed("GET", "/library/projets/" + encodeURIComponent(String(id == null ? "" : id)));
      return { id: String((d && d.id) || id), nom: String((d && d.nom) || ""),
        refs: (Array.isArray(d && d.items) ? d.items : []).filter(isPlain).map((i) => String(i.ref || "")).filter(Boolean) };
    },
    /* UN fichier par appel (la route n'en prend qu'un) ; le nom RENDU fait foi
       (un homonyme devient « nom-1.png ») */
    async importer(file) {
      if (typeof FormData === "undefined" || !file) throw new Error(dzT("cartes.depuis.import_impossible"));
      const fd = new FormData();
      fd.append("file", file, String(file.name || "image.png"));
      const d = await jsonNamed("POST", "/images/upload", fd);
      return { filename: String((d && d.filename) || "") };
    },
    /* l'adresse SERVIE d'une image (GET /api/images/{nom}, routes.py) — pas
       CF.imageURL, dont /api/images/file/ n'existe pas (mod-face.js) */
    url(nom) { return "/api/images/" + encodeURIComponent(String(nom == null ? "" : nom)); },
  });
  /* corps : celui de POST /api/cards/decks/depuis-images. Le jeu ouvert est
     ecrit d'abord ; le deck cree est OUVERT (la page part, `busy` reste au
     voile) ; une phrase du serveur (404 qui nomme le fichier, 400) remonte. */
  async function deckDepuisImages(corps) {
    if (OFFLINE) throw new Error(dzT("cartes.depuis.hors_ligne"));
    await galFlush();
    const d = await jsonNamed("POST", "/cards/decks/depuis-images", isPlain(corps) ? corps : {});
    const did = d && d.deck && d.deck.id;
    if (!did) throw new Error(dzT("cartes.core.sans_did"));
    galGo(did);
    return d.deck;
  }
  /* le libelle AFFICHE d'un format : la regle du selecteur de la barre */
  function libelleFormat(id) {
    const f = FMT_BY_ID[id];
    if (!f) return String(id == null ? "" : id);
    return id === "square_eu" ? dzT("cartes.core.fmt_carre") : id === "business" ? dzT("cartes.core.fmt_visite")
      : f.forme === "hex" ? hexLabel(id) : f.label;
  }

  /* « Importer une carte » : la galerie ferme et la piece 10 s'ouvre. Le"""

_API = r"""images: images, imageURL: imageURL, ApiMissing: ApiMissing,
    /* t421 : la Bibliotheque et la creation depuis des images (§8, au CORE) */
    bibliotheque: bibliotheque, deckDepuisImages: deckDepuisImages, libelleFormat: libelleFormat,"""

_CORE = {
    "cartes.depuis.gal_titre": ("Nouveau jeu depuis des images", "New deck from images"),
    "cartes.depuis.gal_note": ("Vos visuels finis deviennent les cartes : une image par carte, sans cadre ni texte.",
                               "Your finished artwork becomes the cards: one image per card, no frame or text."),
    "cartes.depuis.gal_bouton": ("Choisir les images…", "Choose images…"),
    "cartes.depuis.absent": ("Le dialogue de création depuis des images n'est pas chargé.",
                             "The create-from-images dialog is not loaded."),
    "cartes.depuis.import_impossible": ("Import impossible depuis ce navigateur.", "Import is not possible from this browser."),
    "cartes.depuis.hors_ligne": ("Hors ligne : impossible de créer un jeu.", "Offline: a deck cannot be created."),
    # clés L7 existantes, reprises à l'identique (le contrôle --seul exige chaque dzT écrit au dico du groupe)
    "cartes.core.sans_did": ("le backend n'a pas rendu d'identifiant de jeu", "the backend returned no deck id"),
    "cartes.core.fmt_carre": ("Carré 70 x 70 mm", "Square 70 x 70 mm"),
    "cartes.core.fmt_visite": ("Carte de visite 2 x 3,5 in", "Business card 2 x 3,5 in"),
}

# les textes du dialogue (js/depuis-images.js)
_DIALOGUE = {
    "e1": ("Nom et format", "Name and format"),
    "e2": ("Images", "Images"),
    "e3": ("Verso", "Back"),
    "e4": ("Récapitulatif", "Summary"),
    "precedent": ("Précédent", "Previous"),
    "suivant": ("Suivant", "Next"),
    "creer": ("Créer le jeu", "Create the deck"),
    "creation": ("Création du jeu ({n} cartes)…", "Creating the deck ({n} cards)…"),
    "nom": ("Nom du jeu", "Deck name"),
    "nom_defaut": ("Mes images", "My images"),
    "format": ("Format", "Format"),
    "groupe_hex": ("Hexagones", "Hexagons"),
    "groupe_rect": ("Rectangles", "Rectangles"),
    "format_propose": ("Format proposé d'après le rapport de vos images : {format}.",
                       "Format suggested from your images' aspect ratio: {format}."),
    "format_aide": ("Chaque image remplit toute la carte. Le format se change ensuite dans la barre du jeu.",
                    "Each image fills the whole card. The format can be changed later in the deck bar."),
    "recherche_ph": ("Rechercher un nom…", "Search a name…"),
    "projet": ("Projet", "Project"),
    "projet_tous": ("Toute la Bibliothèque", "Entire Library"),
    "projet_indispo": ("Projet illisible : {err}", "Project unreadable: {err}"),
    "tout": ("Tout sélectionner", "Select All"),
    "rien": ("Tout désélectionner", "Deselect all"),
    "importer": ("Importer depuis l'ordinateur…", "Import from computer…"),
    "import_cours": ("Import {i} sur {n}…", "Importing {i} of {n}…"),
    "import_bilan": ("Images importées : {n}", "Images imported: {n}"),
    "import_bilan_ko": ("Images importées : {n} — refusées : {ko} (survoler pour le détail)",
                        "Images imported: {n} — refused: {ko} (hover for details)"),
    "import_echec": ("{nom} : {err}", "{nom}: {err}"),
    "import_attendre": ("Attendez la fin de l'import.", "Wait for the import to finish."),
    "selection": ("Sélection : {n} sur {total}", "Selected: {n} of {total}"),
    "dims": ("{w} × {h} px", "{w} × {h} px"),
    "chargement": ("Chargement de la Bibliothèque…", "Loading the Library…"),
    "biblio_vide": ("La Bibliothèque est vide : importez vos images depuis l'ordinateur.",
                    "The Library is empty: import your images from your computer."),
    "biblio_indispo": ("Bibliothèque indisponible : {err}", "Library unavailable: {err}"),
    "aucune_correspondance": ("Aucune image ne correspond.", "No image matches."),
    "aucune_image": ("Choisissez au moins une image.", "Choose at least one image."),
    "aucune_carte": ("Aucune carte : chaque image choisie est un verso.", "No cards: every chosen image is a back."),
    "trop": ("{n} images choisies : {max} au plus par jeu.", "{n} images chosen: {max} at most per deck."),
    "verso_aucun": ("Aucun verso", "No back"),
    "verso_aucun_aide": ("Le dos des cartes reste blanc.", "Card backs stay blank."),
    "verso_commun": ("Une image commune", "One shared image"),
    "verso_commun_aide": ("La même image au dos de chaque carte.", "The same image on the back of every card."),
    "verso_apparie": ("Appariement automatique", "Automatic pairing"),
    "verso_apparie_aide": ("« nom_verso.png » est le dos de « nom_recto.png » ou de « nom.png » ; _back et _front valent de même.",
                           "“name_verso.png” is the back of “name_recto.png” or “name.png”; _back and _front work the same."),
    "verso_image": ("Image du verso", "Back image"),
    "verso_choisir": ("Choisir une image…", "Choose an image…"),
    "verso_manque": ("Choisissez l'image du verso.", "Choose the back image."),
    "apparie_bilan": ("Cartes : {n}, dont {p} avec un verso.", "Cards: {n}, {p} of them with a back."),
    "recap_nom": ("Nom", "Name"),
    "recap_cartes": ("Cartes à créer", "Cards to create"),
    "fond_perdu": ("Mon fichier inclut le fond perdu", "My file includes the bleed"),
    "fond_perdu_aide": ("Cochée d'office si vos images ont le rapport du gabarit (coupe + {mm} mm de fond perdu de chaque côté). "
                        "Décochée : le jeu naît sans fond perdu et rien n'est rogné.",
                        "Ticked automatically when your images have the template's ratio (trim + {mm} mm of bleed on each side). "
                        "Unticked: the deck starts with no bleed and nothing is cropped."),
    "lisere": ("Sans fond perdu, l'image s'arrête à la coupe : une découpe imprécise peut laisser un liseré blanc au bord.",
               "Without bleed, the image stops at the trim line: an imprecise cut can leave a thin white edge."),
    "ecarts": ("Rapport différent du format, ces images seront recadrées ({n})",
               "Aspect ratio differs from the format, these images will be cropped ({n})"),
    "sans_verso": ("Sans verso trouvé, leur dos sortira blanc ({n})", "No back found, their back will be blank ({n})"),
    "orphelins": ("Versos sans recto, ignorés ({n})", "Backs without a front, ignored ({n})"),
    "ordre": ("Ordre des cartes ({n}) — il se reprend ensuite dans Données",
              "Card order ({n}) — it can be changed later in Data"),
}

ENTREES = [
    # la section de la galerie, en tête de son corps
    S(C, 1985, "    + '<div class=\"cf-gal-body\">'", _crlf(_SECTION), _CORE),
    # le câblage du bouton
    S(C, 2009, 'if (i) i.addEventListener("click", galImport);', _crlf(_CABLE), {}),
    # galImages, CF.bibliotheque, CF.deckDepuisImages, CF.libelleFormat — juste avant galImport et son commentaire
    S(C, 2247, "/* « Importer une carte » : la galerie ferme et la piece 10 s'ouvre. Le", _crlf(_FONCTIONS), {}),
    # l'API publique
    S(C, 2622, "images: images, imageURL: imageURL, ApiMissing: ApiMissing,", _crlf(_API), {}),
] + [H("cartes.depuis." + k, fr, en) for k, (fr, en) in _DIALOGUE.items()]
