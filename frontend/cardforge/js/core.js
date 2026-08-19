/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — core.js — LE CONTRAT.

   Ce fichier ne sait pas ce qu'est un cadre, une police ou un CSV. Il ne sait
   que PARTITIONNER : huit modules ecrivent dans huit sous-arbres disjoints, un
   seul moteur dessine la carte, une seule formule convertit les millimetres en
   pixels. C'est ce qui rend huit builders paralleles inoffensifs les uns pour
   les autres.

   ── CE QUI A CHANGE, ET POURQUOI (revision 2.0.0) ─────────────────────────
   La revision 1 identifiait l'appelant par le NOM DE FICHIER LU DANS LA PILE
   D'APPEL. Trois attaques mesurees l'ont demolie :
     · `eval("CF.patch('face',…)\n//# sourceURL=…/js/mod-face.js")` suffisait a
       ecrire chez autrui — une pile est une CHAINE que l'appelant redige ;
     · le controle portait sur le nom de BASE, donc un `lib/mod-face.js` pose
       n'importe ou avait les pleins droits sur doc.face ;
     · `[{dpi:600}].forEach(CF.setFormat)` blanchissait la pile (le cadre natif
       ne nomme aucun fichier) et setFormat, qui exigeait « pas de module »,
       prenait ce vide pour le CORE. La regle etait INVERSEE entre les API.
   L'identite ne se lit plus dans une chaine : elle se PROUVE une fois, a
   l'enregistrement, par `document.currentScript` — l'element <script> que le
   navigateur execute reellement, que ni eval ni un sourceURL ne peuvent
   contrefaire — et elle est ensuite PORTEE PAR UN OBJET que le CORE rend a ce
   script-la et a personne d'autre. Un module qui garde son jeton ecrit chez
   lui ; un module qui ne l'a pas n'ecrit nulle part. Il n'y a plus de « qui
   appelle ? » a deviner.

   Les garanties centrales, et le mecanisme qui les tient :

   (a) ECRITURE EXCLUSIVE — `M.patch(partial)` n'ecrit que sous doc[M.id], ou
       M est le jeton rendu par CF.register a ce fichier. Une cle absente du
       schema declare a l'enregistrement leve. CF.doc() ne rend jamais l'objet
       vivant : un clone DEEP-FROZEN.

   (b) UN SEUL MOTEUR, UNE SEULE ECHELLE — CF.renderCard(i) rend TOUJOURS une
       toile de geom.canvas_px, celle du fichier livre. Les painters ne
       recoivent AUCUNE echelle : ils ne peuvent donc pas savoir s'ils
       dessinent pour l'ecran ou pour l'imprimeur, et « ne pas faire le grain
       quand c'est petit » — l'optimisation d'apercu la plus naturelle qui
       soit — n'est plus exprimable. L'apercu est le MEME bitmap, reduit par
       drawImage. Ce depot a deja paye ce bug (viewport en miroir du gauntlet
       VFX, test_export_wysiwyg.py).

   (c) LES REPERES NE SORTENT PAS — la couche z=90 n'est pas un parametre
       public : `CF.renderCard` ne sait pas la dessiner. Seul l'apercu du CORE
       y a acces. Aucun fichier telecharge ne peut donc la contenir.

   (d) CE QUI EST TELECHARGE VIENT DU MOTEUR — `CF.download` n'accepte qu'un
       blob de PROVENANCE connue : sorti de `CF.cardBlob` ou d'un appel
       `M.api.blob` vers le sous-domaine du module. Une toile bricolee a cote
       ne se telecharge pas.

   (e) CHACUN CHEZ SOI SUR LE RESEAU — `M.api` est confine a
       /api/cards/<did>/<M.id>/… (le miroir exact de la regle 8 backend). Le
       seul dehors est `CF.images`, tenu par le CORE, parce que c'est LA
       depense de credits et qu'elle doit se compter a un seul endroit.

   TABLE Z GELEE — un module ne peut enregistrer un painter qu'a ses propres z
     10 texture (papier sous l'illustration) · 20 face (illustration)
     30 texture (grain/foil au-dessus) · 40 frame (cadre) · 60 type (tout le
     texte) · 70 frame (ornements de dessus) · 90 CORE (reperes, jamais exporte)
   data · solid · print · gltf n'ont AUCUN painter : ils ne dessinent pas la
   carte.

   Aucune dependance externe, aucun CDN, aucun build. Le bloc de geometrie est
   chargeable tel quel dans Node (aucun acces au DOM au chargement) : c'est ce
   qui permet a qa/test_core_contract.mjs de prouver le contrat — la geometrie
   sans navigateur, le cloisonnement dans un Chrome sans tete.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {

  const VERSION = "2.0.0";

  /* ── les huit ids geles, dans l'ordre du rail (= numero de piece) ───────── */
  const MODULES = ["face", "frame", "type", "data", "solid", "texture", "print", "gltf", "forge3d"];
  const ORDER = {};
  MODULES.forEach((id, i) => { ORDER[id] = i + 1; });

  /* ── la table des z. Cle = z, valeur = proprietaire. "__core__" = reperes ── */
  const Z_TABLE = { 10: "texture", 20: "face", 30: "texture", 40: "frame", 60: "type", 70: "frame", 90: "__core__" };
  const Z_GUIDES = 90;

  /* ── cles du document appartenant au CORE : aucun module ne les patche ──── */
  const CORE_KEYS = ["v", "id", "name", "format"];

  /* ── capacites nominatives : une piece, une permission de plus. Elles sont
       posees sur le JETON, pas sur le global — donc inatteignables sans lui. */
  const CAN_SET_CARDS = "data";    /* P4 detient la liste des cartes */
  const CAN_SET_FORMAT = "print";  /* P7 : « selecteur de format nomme + DPI » */

  /* ── formats. trim_mm est ECRIT EN MILLIMETRES DECIMAUX, jamais derive des
       pouces : en IEEE754, 3.5 * 25.4 = 88.89999999999999 et 1.75 * 25.4 =
       44.449999999999996. La regle d'arrondi est un demi-haut ; un format qui
       tombe pile sur un .5 basculerait d'un pixel selon le chemin de calcul,
       et la parite au pixel avec nanDECK (825x1125, 750x1125, 900x1500,
       600x1125, 675x1125, 1125x1725, 450x600) tomberait. Les pouces ne servent
       QU'A L'AFFICHAGE.
       Fond perdu natif : metrique 3 mm, imperial 0.125 in = 3.175 mm.
       Zone sure par defaut = fond perdu (convention Artscow / Printer's Studio). */
  /* Table RECOPIEE de cards/contract.py:FORMATS — mots pour mots, y compris les
     libelles : l'ecran et l'API doivent nommer un format pareil. La recopie
     n'est pas laissee a la bonne volonte : `test_cards_core.py` relit CE
     tableau depuis ce fichier et le compare a `contract.FORMATS`, libelles
     compris. Une divergence fait ROUGIR la suite. */
  const FORMATS = [
    { id: "poker_us", label: "Poker US 2,5 x 3,5 in", unit: "in", trim_mm: [63.5, 88.9] },
    { id: "poker_eu", label: "Poker 63 x 88 mm", unit: "mm", trim_mm: [63.0, 88.0] },
    { id: "bridge_us", label: "Bridge US 2,25 x 3,5 in", unit: "in", trim_mm: [57.15, 88.9] },
    { id: "bridge_eu", label: "Bridge 59 x 91 mm", unit: "mm", trim_mm: [59.0, 91.0] },
    { id: "tarot_us", label: "Tarot US 2,75 x 4,75 in", unit: "in", trim_mm: [69.85, 120.65] },
    { id: "tarot_eu", label: "Tarot 70 x 120 mm", unit: "mm", trim_mm: [70.0, 120.0] },
    { id: "mini", label: "Mini 44 x 68 mm", unit: "mm", trim_mm: [44.0, 68.0] },
    { id: "square_eu", label: "Carré 70 x 70 mm", unit: "mm", trim_mm: [70.0, 70.0] },
    { id: "domino", label: "Domino 1,75 x 3,5 in", unit: "in", trim_mm: [44.45, 88.9] },
    { id: "business", label: "Carte de visite 2 x 3,5 in", unit: "in", trim_mm: [50.8, 88.9] },
    { id: "jumbo", label: "Jumbo 3,5 x 5,5 in", unit: "in", trim_mm: [88.9, 139.7] },
    { id: "micro", label: "Micro 1,25 x 1,75 in", unit: "in", trim_mm: [31.75, 44.45] },
  ];
  const FMT_BY_ID = {};
  FORMATS.forEach((f) => { FMT_BY_ID[f.id] = f; });

  const MM_PER_INCH = 25.4;
  const BLEED_METRIC_MM = 3.0, BLEED_IMPERIAL_MM = 3.175;   /* 0.125 in */
  const nativeBleed = (id) => (FMT_BY_ID[id] && FMT_BY_ID[id].unit === "in" ? BLEED_IMPERIAL_MM : BLEED_METRIC_MM);
  /* arrondi d'AFFICHAGE, demi-haut. Le backend a le meme (contract.rnd) et NON
     le round() de Python, qui est un arrondi au pair : 0.0625 -> 0.062 la ou
     l'ecran ecrit 0.063. Deux regles pour le meme travail dans un fichier qui
     se declare miroir exact, c'est une derive qui attend son heure. */
  const rnd = (v, n) => { const p = Math.pow(10, n); return Math.round(v * p) / p; };

  const DPIS = [150, 300, 600];
  const LIM = { dpi: [72, 1200], bleed_mm: [0, 10], safe_mm: [0, 10], corner_mm: [0, 10] };
  const DEFAULT_FMT = "poker_eu";

  /* couleur du carton nu. Le CORE pose le SUPPORT (rectangle plein, fond perdu
     compris : sur une vraie carte la decoupe vient APRES l'impression, donc
     l'encre va jusqu'au bord de la toile). P6 le recouvre a z=10. */
  const PAPER = "#ffffff";

  const AUTOSAVE_MS = 900;
  const DID_RE = /^deck_[0-9a-f]{8}$/;
  const LS_DECK = "dz_cf_deck";        /* document de secours (hors ligne) */
  const LS_DECK_ID = "dz_cf_deck_id";  /* dernier jeu ouvert : on le REOUVRE */

  /* Delai de garde d'un painter. Une promesse qui ne se resout jamais — une
     image ou une police qui ne charge pas, cas banal — gelait l'apercu des
     sept autres pieces pour toujours, sans une erreur. Limite honnete : une
     boucle SYNCHRONE infinie reste imparable dans un moteur a un seul fil. */
  const PAINTER_MS = 4000;

  /* ═══════════════════════════════════════════════════════════════════════
     0. OUTILS
     ═══════════════════════════════════════════════════════════════════════ */

  const hasDOM = (typeof document !== "undefined" && !!document.createElement);
  const raf = (fn) => (typeof requestAnimationFrame === "function"
    ? requestAnimationFrame(fn) : setTimeout(fn, 16));
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

  function isPlain(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }

  /* ── D'OU VIENT CE SCRIPT ? ──────────────────────────────────────────────
     Lu UNE FOIS, au chargement : `document.currentScript` pendant l'evaluation
     d'un <script src> est l'element que le navigateur execute. Ni un eval, ni
     un `//# sourceURL`, ni un rappel de timer ne le fabriquent. C'est la seule
     identite de fichier non falsifiable dont dispose une page. */
  const SELF_TAG = (hasDOM && document.currentScript) ? document.currentScript : null;
  const SELF_SRC = (SELF_TAG && SELF_TAG.src)
    ? String(SELF_TAG.src).replace(/[?#].*$/, "") : "";
  /* Le dossier des modules est celui de core.js. Une PAGE — et une page seule,
     jamais un module : les huit builders ne touchent pas au HTML — peut le
     declarer autrement par `data-cf-modules` sur la balise du CORE. C'est ce
     qui permet a qa/contract.html de faire tourner de VRAIS modules d'essai,
     avec painters et schemas, sans ouvrir la moindre porte : l'attribut est
     lu sur la balise <script> du CORE, pas sur un appel. */
  const JS_DIR = (function () {
    if (!SELF_SRC) return "";
    let dir = SELF_SRC.replace(/[^\/]*$/, "");
    try {
      const decl = SELF_TAG && SELF_TAG.getAttribute && SELF_TAG.getAttribute("data-cf-modules");
      if (decl) dir = new URL(decl, document.baseURI).href.replace(/[^\/]*$/, "");
    } catch (e) { /* URL absente : on garde le dossier de core.js */ }
    return dir;
  })();
  function expectedSrc(id) { return JS_DIR + "mod-" + id + ".js"; }
  function currentSrc() {
    if (!hasDOM) return null;
    const cs = document.currentScript;
    if (!cs || !cs.src) return null;
    return String(cs.src).replace(/[?#].*$/, "");
  }

  /* Copie profonde ET validation en un seul passage : ce qui entre dans le
     document doit etre serialisable tel quel (l'autosave le renvoie au disque).
     Un canvas, une fonction, un Date, un noeud DOM levent ICI — pas trois
     heures plus tard dans un PATCH qui echoue en silence. */
  function sanitize(v, path) {
    if (v === null) return null;
    const t = typeof v;
    if (t === "string" || t === "boolean") return v;
    if (t === "number") {
      if (!isFinite(v)) throw new Error("cardforge: valeur numerique non finie en " + path);
      return v;
    }
    if (Array.isArray(v)) return v.map((x, i) => sanitize(x, path + "[" + i + "]"));
    if (isPlain(v)) {
      if (Object.getPrototypeOf(v) !== Object.prototype && Object.getPrototypeOf(v) !== null)
        throw new Error("cardforge: objet de classe non serialisable en " + path);
      const o = {};
      Object.keys(v).forEach((k) => { o[k] = sanitize(v[k], path + "." + k); });
      return o;
    }
    throw new Error("cardforge: valeur non serialisable en " + path + " (" + t + ")");
  }

  function deepFreeze(v) {
    if (v && typeof v === "object" && !Object.isFrozen(v)) {
      Object.freeze(v);
      Object.keys(v).forEach((k) => deepFreeze(v[k]));
    }
    return v;
  }

  function assertId(id) {
    if (MODULES.indexOf(id) >= 0) return;
    if (CORE_KEYS.indexOf(id) >= 0)
      throw new Error("cardforge: doc." + id + " appartient au CORE" + (id === "format" ? " — widget de la barre (ou le jeton de mod-print.js)" : ""));
    throw new Error("cardforge: id inconnu \"" + id + "\" (attendu : " + MODULES.join(", ") + ")");
  }

  /* MODE BACLE (« sloppy ») : les mutations y sont MUETTES. `CF.doc()` rend un
     clone deep-frozen, mais un module sans "use strict" ne recoit AUCUNE
     exception en le mutant — c'est un no-op silencieux, il relit l'ancienne
     valeur et cherche ailleurs pendant une heure. La garantie « mutation =
     TypeError » etait donc integralement sous-traitee a une directive que
     chaque builder ecrit lui-meme, dans des <script> classiques ou le mode
     bâclé est le DEFAUT, et qu'aucun outil ne verifiait.

     Ce qui NE MARCHE PAS, mesure plutot que suppose : tester la strictesse
     d'une fonction depuis le dehors. Le vieux truc `hasOwnProperty("caller")`
     ne distingue plus rien dans V8 moderne —
     `Object.getOwnPropertyNames(f)` rend `["length","name","prototype"]` que
     la fonction soit stricte ou non (mesure dans Chrome sur cette page). Un
     controle qui ne peut pas se declencher serait exactement la garantie
     decorative qu'on est en train de supprimer partout.

     Ce qui MARCHE : lire la SOURCE. `lint_cardforge.py` la refuse au build
     (R9) et `auditStrict()` relit le fichier REELLEMENT SERVI avant d'appeler
     le moindre init() — un module non conforme ne demarre pas et ses painters
     sont retires. Voir §10. */

  /* ═══════════════════════════════════════════════════════════════════════
     1. GEOMETRIE — verite unique.
     Aucun module ne recalcule un pixel a partir des mm. Jamais.
     Le bloc encadre ci-dessous est le MIROIR EXACT du bloc de meme nom dans
     backend/app/services/cards/contract.py : memes noms, meme ordre des
     operations, meme arrondi. Toute divergence est un pixel de decalage entre
     l'ecran et le PDF de l'imprimeur. `test_cards_core.py` EXTRAIT ce bloc du
     present fichier, le transpose mecaniquement en Python et compare les deux
     sorties sur 12 formats x 6 definitions x 5 fonds perdus x 4 zones sures.
     ═══════════════════════════════════════════════════════════════════════ */

  function geomOf(fmt, dpi, bleed_mm, safe_mm, corner_mm) {
    const F = FMT_BY_ID[fmt];
    if (!F) throw new Error("cardforge: format inconnu \"" + fmt + "\"");
    /* LES MEMES BORNES QUE setFormat. Sans elles, geomOf etait la porte de
       service : geomOf('poker_eu', 100000, -50, 0, 0) rendait une toile de
       -145669 px, une geometrie que setFormat aurait refusee — alors que la
       geometrie est censee etre une verite UNIQUE. */
    const chk = (k, v) => {
      const n = Number(v);
      if (!isFinite(n)) throw new Error("cardforge: " + k + " doit etre un nombre");
      if (n < LIM[k][0] || n > LIM[k][1]) throw new Error("cardforge: " + k + " hors bornes [" + LIM[k][0] + ", " + LIM[k][1] + "]");
      return n;
    };
    dpi = Math.round(chk("dpi", dpi));
    bleed_mm = chk("bleed_mm", bleed_mm);
    safe_mm = chk("safe_mm", safe_mm);
    corner_mm = chk("corner_mm", corner_mm);
    const w_mm = F.trim_mm[0], h_mm = F.trim_mm[1];

    /* ═══ CF-GEOM-FORMULA-BEGIN ═══ */
    const R = (x) => Math.floor(Number(x.toFixed(9)) + 0.5);
    const px = (mm, dpi) => R(mm / 25.4 * dpi);
    const canvas_px = [px(w_mm + 2 * bleed_mm, dpi), px(h_mm + 2 * bleed_mm, dpi)];
    const trim_px = [px(w_mm, dpi), px(h_mm, dpi)];
    const bleed_off_px = [(canvas_px[0] - trim_px[0]) / 2, (canvas_px[1] - trim_px[1]) / 2];
    const safe_px = [px(w_mm - 2 * safe_mm, dpi), px(h_mm - 2 * safe_mm, dpi)];
    const safe_off_px = [bleed_off_px[0] + (trim_px[0] - safe_px[0]) / 2, bleed_off_px[1] + (trim_px[1] - safe_px[1]) / 2];
    /* ═══ CF-GEOM-FORMULA-END ═══ */

    /* UNE SEULE CONVERSION PAR LONGUEUR. La zone sure mesure (rogne -
       2*zone sure) : on convertit CETTE longueur d'un bloc, exactement comme
       la toile convertit (rogne + 2*fond perdu). La derivation
       `trim_px - 2*px(safe_mm)` etait l'erreur meme que la regle pretend
       supprimer — 674 px la ou 2,25 pouces valent 675, et le signe de l'erreur
       s'inversait entre formats imperiaux et metriques, donc du texte hors
       zone sure passait le controle avant vol de P7. */

    const mm2px = (v) => v / MM_PER_INCH * dpi;   /* exact, NON arrondi : un rayon
                                                     de coin ou un filet se dessine
                                                     en sous-pixel (le trait de
                                                     coupe tombe a 37,5 px sur les
                                                     formats imperiaux — un
                                                     demi-pixel assume). */
    const px2mm = (v) => v * MM_PER_INCH / dpi;
    /* MEME FORME que CardGeom.to_dict() du backend, aux memes arrondis : les
       millimetres a 3 decimales et les pouces a 4 sont de l'affichage, les
       PIXELS sortent tels quels — ce sont eux qui font le fichier. */
    return deepFreeze({
      fmt: F.id, label: F.label, unit: F.unit, dpi: dpi,
      trim_mm: [rnd(w_mm, 3), rnd(h_mm, 3)],
      trim_in: [rnd(w_mm / MM_PER_INCH, 4), rnd(h_mm / MM_PER_INCH, 4)],
      bleed_mm: rnd(bleed_mm, 3), safe_mm: rnd(safe_mm, 3), corner_mm: rnd(corner_mm, 3),
      trim_px: trim_px, canvas_px: canvas_px, bleed_off_px: bleed_off_px,
      safe_px: safe_px, safe_off_px: safe_off_px,
      corner_px: rnd(corner_mm / MM_PER_INCH * dpi, 1),
      mm2px: mm2px, px2mm: px2mm,
    });
  }

  let GEOM = null;                    /* memoise ; recalcule a chaque setFormat */
  function geom() {
    if (!GEOM) {
      const f = DOC.format;
      GEOM = geomOf(f.fmt, f.dpi, f.bleed_mm, f.safe_mm, f.corner_mm);
    }
    return GEOM;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     2. DOCUMENT — lecture universelle, ecriture exclusive
     ═══════════════════════════════════════════════════════════════════════ */

  function blankFormat(fmt) {
    const F = FMT_BY_ID[fmt] || FMT_BY_ID[DEFAULT_FMT];
    const b = nativeBleed(F.id);
    return { fmt: F.id, dpi: 300, bleed_mm: b, safe_mm: b, corner_mm: 3 };
  }

  const DOC = { v: 1, id: null, name: "Nouveau jeu", format: blankFormat(DEFAULT_FMT) };
  MODULES.forEach((id) => { DOC[id] = {}; });

  const SCHEMA = {};                  /* id -> Set des cles autorisees (declarees a register) */
  let SNAP = null;                    /* clone deep-frozen memoise */
  let REV = 0;

  function touch() { SNAP = null; REV++; }
  function doc() {
    if (!SNAP) SNAP = deepFreeze(sanitize(DOC, "doc"));
    return SNAP;
  }

  function get(path, dflt) {
    if (typeof path !== "string" || !path) throw new Error("cardforge: CF.get attend un chemin");
    const parts = path.split(".");
    let cur = doc();
    for (let i = 0; i < parts.length; i++) {
      /* hasOwnProperty, PAS l'operateur `in` : `in` traverse la chaine de
         prototypes, et une pollution de Object.prototype se serait donnee pour
         une valeur du document des que la cle etait absente — c'est-a-dire
         pendant toute la periode ou les huit pieces sont en construction. */
      if (cur === null || typeof cur !== "object" || !own(cur, parts[i])) return dflt;
      cur = cur[parts[i]];
    }
    return cur === undefined ? dflt : cur;
  }

  /* Ecriture. Appelee UNIQUEMENT par le jeton : `id` n'est pas un argument du
     dehors, c'est l'identite prouvee a l'enregistrement. */
  function patchAs(id, partial) {
    assertId(id);
    if (!isPlain(partial)) throw new Error("cardforge: patch attend un objet simple");
    const allowed = SCHEMA[id];
    if (!allowed) throw new Error("cardforge: " + id + " n'est pas enregistre");
    const keys = Object.keys(partial);
    keys.forEach((k) => {
      if (!allowed.has(k)) throw new Error("cardforge: " + id + " ne possede pas " + k);
    });
    /* fusion SUPERFICIELLE sur le 1er niveau du sous-arbre : la valeur remplace,
       elle ne se melange pas. Et elle est CLONEE — sans quoi l'appelant garderait
       une reference vivante dans le document et contournerait le gel. */
    keys.forEach((k) => { DOC[id][k] = sanitize(partial[k], id + "." + k); });
    touch();
    markDirty(id);
    emitCore("core:doc", { id: id, keys: keys, rev: REV });
    scheduleSave();
    invalidate(id);
    return doc()[id];
  }

  function setFormatInternal(next) {
    if (!isPlain(next)) throw new Error("cardforge: setFormat attend un objet");
    const f = DOC.format, out = { fmt: f.fmt, dpi: f.dpi, bleed_mm: f.bleed_mm, safe_mm: f.safe_mm, corner_mm: f.corner_mm };
    if ("fmt" in next) {
      if (!FMT_BY_ID[next.fmt]) throw new Error("cardforge: format inconnu \"" + next.fmt + "\"");
      out.fmt = next.fmt;
      /* changer de format ramene le fond perdu (et la zone sure, qui le suit par
         defaut) a la valeur NATIVE du nouveau format — 3 mm en metrique,
         0.125 in en imperial — sauf si l'appel les fixe explicitement. */
      if (out.fmt !== f.fmt) {
        const nat = nativeBleed(out.fmt);
        out.bleed_mm = nat; out.safe_mm = nat;
      }
    }
    ["dpi", "bleed_mm", "safe_mm", "corner_mm"].forEach((k) => {
      if (!(k in next)) return;
      const v = Number(next[k]);
      if (!isFinite(v)) throw new Error("cardforge: " + k + " doit etre un nombre");
      if (v < LIM[k][0] || v > LIM[k][1]) throw new Error("cardforge: " + k + " hors bornes [" + LIM[k][0] + ", " + LIM[k][1] + "]");
      out[k] = (k === "dpi") ? Math.round(v) : v;
    });
    DOC.format = out;
    GEOM = null;
    touch();
    markDirty("format");
    emitCore("core:geom", { geom: geom() });
    emitCore("core:doc", { id: "format", keys: Object.keys(next), rev: REV });
    scheduleSave();
    scheduleVerify();
    syncFormatWidget();
    invalidate("format");
    return geom();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     3. CARTES — [{ i, id, fields:{slotId:string}, art, back }]
     ═══════════════════════════════════════════════════════════════════════ */

  let CARDS = [];
  let CARDS_SNAP = null;
  let CUR = 0;

  function normCard(row, i) {
    const r = isPlain(row) ? row : {};
    const fields = {};
    if (isPlain(r.fields)) Object.keys(r.fields).forEach((k) => { fields[k] = String(r.fields[k] == null ? "" : r.fields[k]); });
    return {
      i: i,
      id: typeof r.id === "string" && r.id ? r.id : "c" + (i + 1),
      fields: fields,
      art: typeof r.art === "string" && r.art ? r.art : null,
      back: typeof r.back === "string" && r.back ? r.back : null,
    };
  }
  function setCardsInternal(rows) {
    if (!Array.isArray(rows)) throw new Error("cardforge: setCards attend un tableau");
    CARDS = rows.map(normCard);
    if (!CARDS.length) CARDS = [normCard({}, 0)];
    CARDS_SNAP = null;
    if (CUR >= CARDS.length) CUR = CARDS.length - 1;
    emitCore("core:cards", { n: CARDS.length });
    invalidate("data");
    return cards();
  }
  function cards() {
    if (!CARDS_SNAP) CARDS_SNAP = deepFreeze(sanitize(CARDS, "cards"));
    return CARDS_SNAP;
  }
  function card(i) { const a = cards(); const k = Math.max(0, Math.min(a.length - 1, i | 0)); return a[k]; }

  /* ═══════════════════════════════════════════════════════════════════════
     4. REGISTRE — et la remise du JETON
     ═══════════════════════════════════════════════════════════════════════ */

  const REG = {};        /* id -> module */
  const PAINTERS = [];   /* {z, id, fn} tries par z croissant, stable */
  let BOOTED = false;

  function register(mod) {
    if (BOOTED) throw new Error("cardforge: le registre est gele apres le demarrage — CF.register doit etre appele a l'evaluation du script");
    if (!isPlain(mod)) throw new Error("cardforge: CF.register attend un objet");
    const id = mod.id;
    assertId(id);

    /* ── L'IDENTITE, PROUVEE ─────────────────────────────────────────────
       Le registre de la revision 1 ne verifiait pas QUI enregistre : le
       premier script charge pouvait prendre les sept autres ids, tuer leurs
       modules (« deja enregistre » a l'evaluation de leur fichier), imposer
       leur SCHEMA, leur painter et leur panneau. Ici l'appelant doit ETRE le
       fichier qu'il declare, et `document.currentScript` le dit sans que
       personne puisse l'ecrire. */
    if (!JS_DIR)
      throw new Error("cardforge: core.js doit etre charge par <script src=\"…/js/core.js\"> — sans cela l'identite des modules est invérifiable");
    const src = currentSrc();
    if (!src)
      throw new Error("cardforge: CF.register doit etre appele A L'EVALUATION du script du module (pas dans un timer, une promesse ou un eval) — l'identite se lit sur <script>");
    if (src !== expectedSrc(id))
      throw new Error("cardforge: " + src + " ne peut pas enregistrer \"" + id + "\" — seul " + expectedSrc(id) + " le peut");

    if (REG[id]) throw new Error("cardforge: " + id + " est deja enregistre");
    if (typeof mod.title !== "string" || !mod.title.trim()) throw new Error("cardforge: " + id + " doit declarer un title");
    if ("order" in mod && mod.order !== ORDER[id]) throw new Error("cardforge: order doit valoir " + ORDER[id] + " pour " + id + " (le rang du rail est gele)");
    if (typeof mod.init !== "function") throw new Error("cardforge: " + id + " doit declarer init(host)");
    if (!isPlain(mod.state)) throw new Error("cardforge: " + id + " doit declarer son etat par defaut (state) — c'est lui qui definit les cles patchables");

    const painters = mod.painters || [];
    if (!Array.isArray(painters)) throw new Error("cardforge: painters doit etre un tableau");
    painters.forEach((p, k) => {
      if (!isPlain(p) || typeof p.fn !== "function") throw new Error("cardforge: painter #" + k + " de " + id + " : {z, fn} attendu");
      const z = p.z;
      if (!own(Z_TABLE, String(z)))
        throw new Error("cardforge: z=" + z + " n'existe pas dans la table (z autorises : " + Object.keys(Z_TABLE).join(", ") + ")");
      if (Z_TABLE[z] !== id)
        throw new Error("cardforge: z=" + z + " appartient a " + Z_TABLE[z] + ", pas a " + id);
    });

    /* le schema : les cles declarees ICI sont les SEULES patchables ensuite. */
    const st = sanitize(mod.state, id);
    SCHEMA[id] = new Set(Object.keys(st));
    const stored = DOC[id] || {};
    const merged = {};
    Object.keys(st).forEach((k) => { merged[k] = own(stored, k) ? stored[k] : st[k]; });
    Object.keys(stored).forEach((k) => {
      if (!own(merged, k)) console.warn("cardforge: cle stockee inconnue ignoree — doc." + id + "." + k);
    });
    DOC[id] = merged;
    touch();

    REG[id] = { id: id, title: mod.title.trim(), icon: typeof mod.icon === "string" ? mod.icon : "", order: ORDER[id], init: mod.init, host: null, aside: null, src: src };
    painters.forEach((p) => PAINTERS.push({ z: p.z, id: id, fn: p.fn }));
    PAINTERS.sort((a, b) => a.z - b.z);
    return makeToken(id);
  }

  /* ── LE JETON ────────────────────────────────────────────────────────────
     Rendu par CF.register a ce script-la, une seule fois. Il porte l'identite :
     tout ce qui ECRIT est ici, rien sur le global. Un module qui le garde pour
     lui ecrit chez lui ; un module qui ne l'a pas n'ecrit nulle part. */
  function makeToken(id) {
    const t = {
      id: id,
      patch: (partial) => patchAs(id, partial),
      get: get,
      emit: (name, payload) => {
        if (typeof name !== "string" || !name) throw new Error("cardforge: emit attend un nom");
        fire(id + ":" + name, payload);
      },
      invalidate: () => invalidate(id),
      slot: () => (REG[id] ? REG[id].host : null),
      aside: () => asideOf(id),
      api: makeApi(id),
      download: download,
      toast: toast,
      busy: busy,
    };
    if (id === CAN_SET_CARDS) t.setCards = setCardsInternal;
    if (id === CAN_SET_FORMAT) t.setFormat = setFormatInternal;
    return Object.freeze(t);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     5. EVENEMENTS
     ═══════════════════════════════════════════════════════════════════════ */

  const SUBS = [];
  let SUBID = 0;
  function on(name, fn) {
    if (typeof name !== "string" || !name) throw new Error("cardforge: CF.on attend un nom d'evenement");
    if (typeof fn !== "function") throw new Error("cardforge: CF.on attend une fonction");
    const h = ++SUBID;
    SUBS.push({ h: h, name: name, fn: fn });
    return h;
  }
  function off(h) {
    for (let i = SUBS.length - 1; i >= 0; i--) if (SUBS[i].h === h) SUBS.splice(i, 1);
  }
  function fire(name, payload) {
    SUBS.slice().forEach((s) => {
      if (s.name !== name) return;
      try { s.fn(payload, name); }
      catch (e) { console.error("cardforge: abonne " + name + " en erreur", e); }
    });
  }
  function emitCore(name, payload) { fire(name, payload); }

  /* ═══════════════════════════════════════════════════════════════════════
     6. RENDU — UN SEUL MOTEUR, UNE SEULE ECHELLE
     ═══════════════════════════════════════════════════════════════════════ */

  let SIDE = "front";
  let LAST_ERRORS = [];

  /* Aucun module n'a encore de painter : plutot qu'un rectangle blanc muet, la
     toile dit son etat. La marque disparait au premier painter enregistre. */
  function emptyPlate(ctx, g) {
    const b = g.bleed_off_px, t = g.trim_px, c = g.canvas_px;
    ctx.save();
    ctx.strokeStyle = "rgba(0,0,0,.10)";
    ctx.lineWidth = Math.max(1, g.dpi / 300);
    ctx.beginPath();
    ctx.moveTo(b[0], b[1]); ctx.lineTo(b[0] + t[0], b[1] + t[1]);
    ctx.moveTo(b[0] + t[0], b[1]); ctx.lineTo(b[0], b[1] + t[1]);
    ctx.stroke();
    const s = Math.max(11, c[0] / 26);
    ctx.fillStyle = "rgba(0,0,0,.34)";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "600 " + s + "px sans-serif";
    ctx.fillText("gabarit vide", c[0] / 2, c[1] / 2 - s * 0.8);
    ctx.font = (s * 0.62) + "px sans-serif";
    ctx.fillText("aucun painter enregistré", c[0] / 2, c[1] / 2 + s * 0.5);
    ctx.restore();
  }

  function guidesPainter(ctx, g) {
    /* Reperes prepresse : fond perdu (bord de toile), coupe (trim), zone sure.
       Couleurs FIXES et non tokenisees : cette couche se pose sur une
       illustration quelconque, pas sur le fond de l'interface. Elle n'est pas
       joignable depuis le dehors : `renderCard` n'a pas de parametre `guides`,
       seul l'apercu du CORE appelle `renderRaw` avec. */
    const b = g.bleed_off_px, s = g.safe_off_px, t = g.trim_px, sp = g.safe_px, c = g.canvas_px;
    const u = Math.max(1, g.dpi / 300);           /* epaisseur constante a l'oeil */
    ctx.save();
    ctx.setLineDash([]);
    ctx.lineWidth = u;
    ctx.strokeStyle = "rgba(0,0,0,.45)";
    ctx.strokeRect(0.5 * u, 0.5 * u, c[0] - u, c[1] - u);
    ctx.strokeStyle = "#00b7ff";                   /* fond perdu = bord de toile */
    ctx.setLineDash([6 * u, 5 * u]);
    ctx.strokeRect(0.5 * u, 0.5 * u, c[0] - u, c[1] - u);
    ctx.setLineDash([]);
    ctx.strokeStyle = "#ff2d92";                   /* coupe */
    ctx.strokeRect(b[0], b[1], t[0], t[1]);
    ctx.setLineDash([9 * u, 6 * u]);
    ctx.strokeStyle = "#33d18b";                   /* zone sure */
    ctx.strokeRect(s[0], s[1], sp[0], sp[1]);
    ctx.restore();
  }

  function withTimeout(v, ms, what) {
    if (!v || typeof v.then !== "function") return Promise.resolve(v);
    let t = null;
    return Promise.race([
      Promise.resolve(v).then((x) => { clearTimeout(t); return x; },
        (e) => { clearTimeout(t); throw e; }),
      new Promise((_, rej) => { t = setTimeout(() => rej(new Error("cardforge: " + what + " n'a jamais rendu la main (" + ms + " ms) — image ou police qui ne charge pas ?")), ms); }),
    ]);
  }

  /* LE moteur, en un seul exemplaire et une seule echelle : la toile fait
     TOUJOURS geom.canvas_px, c'est-a-dire le fichier livre. Les painters ne
     recoivent pas d'echelle : ils ne peuvent donc pas distinguer l'apercu de
     l'export, et le bug WYSIWYG n'est plus exprimable. */
  async function renderRaw(i, opt) {
    if (!hasDOM) throw new Error("cardforge: CF.renderCard exige un DOM (canvas)");
    const o = opt || {};
    const guides = !!o.guides;
    const side = o.face === "back" ? "back" : "front";
    const g = geom();
    const cd = card(typeof i === "number" ? i : CUR);
    const w = Math.max(1, g.canvas_px[0]);
    const h = Math.max(1, g.canvas_px[1]);
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    const ctx = cv.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    try { ctx.imageSmoothingQuality = "high"; } catch (e) { /* moteurs anciens */ }

    /* le support : plein cadre, fond perdu compris (la decoupe vient apres). */
    ctx.fillStyle = PAPER;
    ctx.fillRect(0, 0, w, h);
    let draws = false;
    for (let k = 0; k < PAINTERS.length; k++) if (PAINTERS[k].z !== Z_GUIDES) { draws = true; break; }
    if (!draws) emptyPlate(ctx, g);

    const d = doc();
    /* SIDE est une variable partagee : elle ne vaut que parce que les rendus
       sont SERIALISES (renderCard ci-dessous). Deux rendus concurrents — le
       PNG 1:1 pendant que l'apercu se redessine — se la volaient au premier
       `await`, et le painter du verso lisait « front ». C'est la piece 07
       (duplex, miroir bord long) qui aurait livre des planches fausses. */
    SIDE = side;
    const errors = [];
    for (let k = 0; k < PAINTERS.length; k++) {
      const p = PAINTERS[k];
      if (p.z === Z_GUIDES) continue;               /* reserve au CORE */
      ctx.save();
      try {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        await withTimeout(p.fn(ctx, g, d, cd, side), PAINTER_MS, "le painter " + p.id + " (z=" + p.z + ")");
        if (cv.width !== w || cv.height !== h) {
          /* le controle DANS le try : dehors, il faisait tomber le rendu
             ENTIER, l'exception partait dans le .catch() de l'apercu et le
             bandeau restait muet — une panne muette pour les sept autres. */
          cv.width = w; cv.height = h;
          throw new Error("a redimensionne la toile (la toile appartient au CORE)");
        }
      } catch (e) {
        /* un builder en panne ne noircit pas l'ecran des sept autres */
        errors.push({ id: p.id, z: p.z, message: String(e && e.message || e) });
        console.error("cardforge: painter " + p.id + " z=" + p.z, e);
      }
      ctx.restore();
    }
    if (guides) {
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      guidesPainter(ctx, g);
      ctx.restore();
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    LAST_ERRORS = errors;
    emitCore("core:render", { i: cd.i, side: side, w: w, h: h, guides: guides, errors: errors.slice() });
    return cv;
  }

  /* SERIALISATION. Un seul rendu a la fois : `SIDE` et le bandeau d'erreur sont
     partages, et deux rendus concurrents se les echangeaient au premier await.
     La file coute une promesse ; la course coutait un verso imprime au recto. */
  let RENDER_CHAIN = Promise.resolve();
  function renderQueued(i, opt) {
    const run = () => renderRaw(i, opt);
    const p = RENDER_CHAIN.then(run, run);
    RENDER_CHAIN = p.then(() => { }, () => { });
    return p;
  }

  /* L'API publique : ni echelle, ni reperes. Ce qui sort d'ici est ce qui part
     chez l'imprimeur. */
  function renderCard(i, opt) {
    const o = opt || {};
    return renderQueued(i, { face: o.face, guides: false });
  }

  /* le fichier livre : meme appel, JAMAIS de reperes, et une PROVENANCE. */
  const MINTED = (typeof WeakSet === "function") ? new WeakSet() : null;
  function mint(b) { if (MINTED && b && typeof b === "object") { try { MINTED.add(b); } catch (e) { /* non ajoutable */ } } return b; }

  async function cardBlob(i, opt) {
    const o = opt || {};
    const cv = await renderCard(i, { face: o.face });
    const type = o.type === "image/jpeg" ? "image/jpeg" : "image/png";
    const q = isFinite(Number(o.quality)) ? Number(o.quality) : 0.95;
    const b = await new Promise((res, rej) => {
      cv.toBlob((x) => x ? res(x) : rej(new Error("cardforge: encodage impossible")), type, q);
    });
    return mint(b);
  }

  /* ── invalidation coalescee sur une frame ──────────────────────────────── */
  let pending = null;
  function invalidate(id) {
    if (pending) { pending.ids.push(id); return; }
    pending = { ids: [id] };
    raf(() => {
      const ids = pending.ids; pending = null;
      drawPreview(true).catch((e) => console.error("cardforge: apercu", e));
      fire("core:invalidate", { ids: ids });
    });
  }

  /* ═══════════════════════════════════════════════════════════════════════
     7. UI — coquille (rail, hotes, apercu, barre de format, theme)
     ═══════════════════════════════════════════════════════════════════════ */

  const el = (s) => (hasDOM ? document.querySelector(s) : null);
  let toastTimer = null;

  function toast(msg, isErr) {
    if (!hasDOM) { console.log((isErr ? "! " : "") + msg); return; }
    const t = el("#toast");
    if (!t) return;
    t.textContent = String(msg);
    t.classList.toggle("err", !!isErr);
    t.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.add("hidden"), 4600);
  }
  function busy(on_, label) {
    if (!hasDOM) return;
    const b = el("#busy");
    if (!b) return;
    b.querySelector(".busy-l").textContent = label || "traitement…";
    b.classList.toggle("hidden", !on_);
  }
  function asideOf(who) {
    const m = REG[who];
    if (!m || !hasDOM) return null;
    if (!m.aside) {
      const host = document.createElement("div");
      host.className = "cf-aside-body cf-" + who;
      host.dataset.mod = who;
      el("#side").appendChild(host);
      m.aside = host;
    }
    syncPanels();
    return m.aside;
  }

  let ACTIVE = MODULES[0];
  function buildRail() {
    const rail = el("#rail");
    if (!rail) return;
    rail.innerHTML = "";
    MODULES.forEach((id) => {
      const m = REG[id];
      const b = document.createElement("button");
      b.type = "button";
      b.className = "rail-item" + (id === ACTIVE ? " active" : "") + (m ? "" : " off");
      b.dataset.mod = id;
      b.innerHTML = '<i class="ri-n">' + String(ORDER[id]).padStart(2, "0") + '</i>'
        + '<span class="ri-t">' + (m ? esc(m.title) : esc(id)) + '</span>'
        + '<em class="ri-i">' + (m ? esc(m.icon) : "·") + '</em>';
      if (!m) b.title = "module absent : js/mod-" + id + ".js n'est pas chargé";
      b.addEventListener("click", () => show(id));
      rail.appendChild(b);
    });
  }
  function show(id) {
    assertId(id);
    ACTIVE = id;
    syncPanels();
  }
  function syncPanels() {
    if (!hasDOM) return;
    Array.prototype.forEach.call(document.querySelectorAll(".rail-item"), (b) => {
      b.classList.toggle("active", b.dataset.mod === ACTIVE);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".cf-panel"), (s) => {
      s.classList.toggle("on", s.dataset.mod === ACTIVE);
    });
    const side = el("#side");
    if (side) {
      let any = false;
      Array.prototype.forEach.call(side.children, (c) => {
        const vis = c.dataset.mod === ACTIVE;
        c.classList.toggle("on", vis);
        any = any || vis;
      });
      side.classList.toggle("hidden", !any);
    }
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* ── apercu : le MEME bitmap que le fichier livre, REDUIT ────────────────
     Pas « le meme appel a une autre echelle » : le MEME APPEL, point. On rend
     a canvas_px puis on reduit avec drawImage. Un painter ne peut donc pas
     distinguer les deux chemins, et le facteur d'apercu (non entier, dpr
     compris) ne deplace plus aucun trait dans le fichier. */
  let PREV_SCALE = 1, GUIDES = true, PREV_SIDE = "front", drawing = false, again = false;
  let FULL = null, FULL_KEY = "";
  function fullKey() {
    return [REV, GEOM ? GEOM.fmt + GEOM.dpi + GEOM.bleed_mm + GEOM.safe_mm + GEOM.corner_mm : "", CUR, PREV_SIDE, GUIDES ? 1 : 0, cards().length].join("|");
  }
  async function drawPreview(rerender) {
    if (!hasDOM) return;
    const stage = el("#stageWrap"), out = el("#stageCanvas");
    if (!stage || !out) return;
    if (drawing) { again = true; return; }
    drawing = true;
    try {
      const g = geom();
      const key = fullKey();
      if (rerender !== false || !FULL || FULL_KEY !== key) {
        FULL = await renderQueued(CUR, { guides: GUIDES, face: PREV_SIDE });
        FULL_KEY = key;
      }
      const pad = 28;
      const aw = Math.max(80, stage.clientWidth - pad), ah = Math.max(80, stage.clientHeight - pad);
      const fit = Math.min(aw / g.canvas_px[0], ah / g.canvas_px[1]);
      const dpr = Math.min(2, (typeof devicePixelRatio === "number" ? devicePixelRatio : 1) || 1);
      PREV_SCALE = Math.max(0.02, fit);
      out.width = Math.max(1, Math.round(g.canvas_px[0] * PREV_SCALE * dpr));
      out.height = Math.max(1, Math.round(g.canvas_px[1] * PREV_SCALE * dpr));
      out.style.width = Math.round(g.canvas_px[0] * PREV_SCALE) + "px";
      out.style.height = Math.round(g.canvas_px[1] * PREV_SCALE) + "px";
      const c2 = out.getContext("2d");
      c2.imageSmoothingEnabled = true;
      try { c2.imageSmoothingQuality = "high"; } catch (e) { /* moteurs anciens */ }
      c2.clearRect(0, 0, out.width, out.height);
      c2.drawImage(FULL, 0, 0, out.width, out.height);
      const rd = el("#stageRead");
      if (rd) {
        rd.innerHTML = '<b>' + g.canvas_px[0] + ' x ' + g.canvas_px[1] + ' px</b>'
          + '<span>toile @ ' + g.dpi + ' DPI</span>'
          + '<b>' + g.trim_px[0] + ' x ' + g.trim_px[1] + ' px</b><span>coupe</span>'
          + '<b>' + Math.round(PREV_SCALE * 100) + ' %</b><span>aperçu</span>';
      }
      const nav = el("#stageNav");
      if (nav) nav.textContent = "carte " + (CUR + 1) + " / " + cards().length;
      const err = el("#stageErr");
      if (err) {
        err.classList.toggle("hidden", LAST_ERRORS.length === 0);
        err.textContent = LAST_ERRORS.map((e) => e.id + " z=" + e.z + " : " + e.message).join(" · ");
      }
    } finally {
      drawing = false;
      if (again) { again = false; raf(() => drawPreview(false)); }
    }
  }

  /* ── barre de format (CORE seul) ───────────────────────────────────────── */
  function buildFormatWidget() {
    const sel = el("#fmtSel");
    if (!sel) return;
    sel.innerHTML = FORMATS.map((f) => '<option value="' + f.id + '">' + esc(f.label) + '</option>').join("");
    const dpiSeg = el("#dpiSeg");
    dpiSeg.innerHTML = DPIS.map((d) => '<button class="seg-b" type="button" data-v="' + d + '">' + d + '</button>').join("");
    sel.addEventListener("change", () => setFormatInternal({ fmt: sel.value }));
    dpiSeg.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-v]");
      if (b) setFormatInternal({ dpi: Number(b.dataset.v) });
    });
    [["#bleedInp", "bleed_mm"], ["#safeInp", "safe_mm"], ["#cornerInp", "corner_mm"]].forEach(([q, k]) => {
      const inp = el(q);
      inp.addEventListener("change", () => {
        try { setFormatInternal({ [k]: Number(inp.value) }); }
        catch (err) { toast(String(err.message || err), true); syncFormatWidget(); }
      });
    });
    const nm = el("#deckName");
    if (nm) nm.addEventListener("change", () => {
      DOC.name = String(nm.value || "").slice(0, 80) || "Nouveau jeu";
      nm.value = DOC.name;
      touch(); markDirty("name"); emitCore("core:doc", { id: "name", keys: ["name"], rev: REV }); scheduleSave();
    });
    syncFormatWidget();
  }
  function syncFormatWidget() {
    if (!hasDOM) return;
    const g = geom(), f = DOC.format;
    const sel = el("#fmtSel"); if (sel) sel.value = f.fmt;
    Array.prototype.forEach.call(document.querySelectorAll("#dpiSeg .seg-b"), (b) => {
      b.classList.toggle("active", Number(b.dataset.v) === f.dpi);
    });
    const b1 = el("#bleedInp"); if (b1) b1.value = f.bleed_mm;
    const s1 = el("#safeInp"); if (s1) s1.value = f.safe_mm;
    const c1 = el("#cornerInp"); if (c1) c1.value = f.corner_mm;
    const rd = el("#fmtRead");
    if (rd) {
      /* les trois unites ensemble, toujours : un imprimeur ne travaille pas
         avec une seule des trois, et 7 des 12 formats sont imperiaux. */
      rd.innerHTML = '<b>' + g.canvas_px[0] + ' x ' + g.canvas_px[1] + ' px</b><i>toile</i>'
        + '<b>' + g.trim_px[0] + ' x ' + g.trim_px[1] + ' px</b><i>coupe</i>'
        + '<i>' + g.trim_mm[0] + ' x ' + g.trim_mm[1] + ' mm</i>'
        + '<i>' + g.trim_in[0].toFixed(2) + ' x ' + g.trim_in[1].toFixed(2) + ' in</i>'
        + '<i>zone sûre ' + g.safe_px[0] + ' x ' + g.safe_px[1] + '</i>'
        + '<i>coupe à ' + g.bleed_off_px[0] + ' px</i>';
    }
    const nm = el("#deckName"); if (nm && nm.value !== DOC.name) nm.value = DOC.name;
  }

  /* ── theme : rien ne le propage a une iframe aujourd'hui, le CORE le fait ─
     ordre : ?theme= · dz_theme (localStorage, partage avec les autres labs) ·
     l'hote de meme origine · la preference systeme. Un message
     {type:"dz:theme"} le change a chaud, la puce ◐ aussi. */
  function readTheme() {
    try {
      const q = new URLSearchParams(location.search).get("theme");
      if (q === "light" || q === "dark") return q;
    } catch (e) { /* pas d'URL */ }
    try {
      const s = localStorage.getItem("dz_theme");
      if (s === "light" || s === "dark") return s;
    } catch (e) { /* stockage refuse */ }
    try {
      const p = window.parent && window.parent !== window ? window.parent.document.documentElement.getAttribute("data-theme") : null;
      if (p === "light" || p === "dark") return p;
    } catch (e) { /* origine differente : on n'insiste pas */ }
    /* PAS de repli sur prefers-color-scheme : l'app qui entoure cette iframe est
       sombre (theme-v2.css) comme les quatre autres labs. Un poste regle en
       clair ouvrirait un lab blanc dans une application noire. Le clair reste un
       CHOIX — puce ◐, dz_theme, ?theme=light, ou l'hote qui le pousse. */
    return "dark";
  }
  function applyTheme(t) {
    if (!hasDOM) return;
    document.documentElement.setAttribute("data-theme", t === "light" ? "light" : "dark");
    const b = el("#themeBtn");
    if (b) b.title = (t === "light" ? "Passer en sombre" : "Passer en clair");
  }
  function initTheme() {
    applyTheme(readTheme());
    const b = el("#themeBtn");
    if (b) b.addEventListener("click", () => {
      const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      applyTheme(next);
      try { localStorage.setItem("dz_theme", next); } catch (e) { /* stockage refuse */ }
      raf(() => drawPreview(false));
    });
    window.addEventListener("message", (e) => {
      const d = e && e.data;
      if (d && d.type === "dz:theme" && (d.theme === "light" || d.theme === "dark")) applyTheme(d.theme);
    });
    window.addEventListener("storage", (e) => {
      if (e && e.key === "dz_theme" && (e.newValue === "light" || e.newValue === "dark")) applyTheme(e.newValue);
    });
  }

  /* ═══════════════════════════════════════════════════════════════════════
     8. RESEAU — une route absente tombe sur le catch-all SPA : 200 + du HTML.
     ═══════════════════════════════════════════════════════════════════════ */

  class ApiMissing extends Error {
    constructor(path) { super("route absente sur ce backend : /api" + path); this.missing = true; this.path = path; }
  }

  async function rawFetch(method, path, body, headers) {
    const opt = { method: method, headers: Object.assign({}, headers || {}) };
    if (body !== undefined && body !== null) {
      if ((typeof Blob !== "undefined" && body instanceof Blob) || (typeof FormData !== "undefined" && body instanceof FormData)) opt.body = body;
      else { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
    }
    return fetch("/api" + path, opt);
  }
  async function jsonFetch(method, path, body, headers) {
    let r;
    try { r = await rawFetch(method, path, body, headers); }
    catch (e) { throw new Error("backend injoignable (" + (e && e.message) + ")"); }
    const ct = (r.headers.get("content-type") || "").toLowerCase();
    if (r.status === 404 || (r.ok && ct.indexOf("json") < 0)) throw new ApiMissing(path);
    let d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    if (!r.ok) throw new Error((d && (d.detail || d.error)) || (r.status + " " + r.statusText));
    return d || {};
  }

  /* ── L'API D'UN MODULE, CONFINEE ─────────────────────────────────────────
     Le miroir exact de la regle 8 backend (« chemins RELATIFS au sous-prefixe
     /api/cards/<did>/<id> »). La revision 1 exposait un fetch libre : depuis
     mod-frame.js on ecrivait doc.face et doc.gltf sur le disque par
     PATCH /api/cards/<did>, on appelait /api/health, et rien n'empechait
     /api/images/generate — c'est-a-dire de la depense de credits, sans
     compteur. Ici un module ne peut plus formuler ces requetes. */
  function subPath(id, sub) {
    const s = String(sub == null ? "" : sub);
    /* Un chemin qui COMMENCE par « / » ou par un schema est une intention
       d'absolu : « /images/generate », « /health », « /cards/<autre> ». On ne
       le rabote pas en silence — on le refuse en nommant la regle, sans quoi
       le builder verrait un 404 incomprehensible et croirait a une panne. */
    if (/^[a-z]+:/i.test(s) || s.charAt(0) === "/")
      throw new Error("cardforge: " + id + " : chemin absolu interdit (\"" + s + "\") — les chemins sont RELATIFS a /api/cards/<did>/" + id + " (regle 8). Pour generer une image : CF.images.generate({…}).");
    if (s.split("/").indexOf("..") >= 0)
      throw new Error("cardforge: " + id + " : « .. » interdit dans un chemin (" + s + ")");
    return "/cards/" + (DOC.id || "deck_00000000") + "/" + id + (s ? "/" + s : "");
  }
  function makeApi(id) {
    const api = {
      url: (sub) => "/api" + subPath(id, sub),
      get: (sub) => jsonFetch("GET", subPath(id, sub)),
      post: (sub, b) => jsonFetch("POST", subPath(id, sub), b || {}),
      patch: (sub, b) => jsonFetch("PATCH", subPath(id, sub), b || {}),
      del: (sub) => jsonFetch("DELETE", subPath(id, sub)),
      /* pour les binaires : la reponse est un Blob de PROVENANCE connue, donc
         telechargeable. C'est le seul chemin par lequel un fichier fabrique par
         le backend (PDF de P7, GLB/ZIP de P8) peut atteindre CF.download. */
      blob: async (method, sub, b) => {
        const r = await rawFetch(String(method || "GET").toUpperCase(), subPath(id, sub), b);
        if (r.status === 404) throw new ApiMissing(subPath(id, sub));
        if (!r.ok) throw new Error(r.status + " " + r.statusText);
        return mint(await r.blob());
      },
      raw: (method, sub, b, h) => rawFetch(String(method || "GET").toUpperCase(), subPath(id, sub), b, h),
    };
    return Object.freeze(api);
  }

  /* Le SEUL dehors, tenu par le CORE : la generation d'images. C'est la seule
     action qui DEPENSE (regle 17 de la spec) et elle doit se compter a un seul
     endroit — pas dans huit modules avec huit fetch libres. */
  const images = Object.freeze({
    url: imageURL,
    async models() {
      try { return await jsonFetch("GET", "/image-models"); }
      catch (e) { if (e && e.missing) return { models: [] }; throw e; }
    },
    async generate(req) {
      const q = isPlain(req) ? req : {};
      const prompt = String(q.prompt == null ? "" : q.prompt).trim();
      if (!prompt) throw new Error("cardforge: CF.images.generate exige un prompt");
      const n = Math.max(1, Math.min(4, Number(q.n) || 1));
      const body = { prompt: prompt, n: n };
      if (q.size) body.size = String(q.size);
      if (q.model) body.model = String(q.model);
      if (q.seed != null && isFinite(Number(q.seed))) body.seed = Number(q.seed);
      const d = await jsonFetch("POST", "/images/generate", body);
      emitCore("core:images", { n: n, model: d && d.model });
      return d;
    },
  });

  function imageURL(fname) {
    const s = String(fname == null ? "" : fname);
    if (!s) return "";
    if (/^(https?:|data:|blob:|\/)/.test(s)) return s;
    return "/api/images/file/" + encodeURIComponent(s);
  }

  /* ── TELECHARGEMENT : la provenance, pas la politesse ────────────────────
     « Les reperes ne sont jamais exportes » et « renderCard est la seule
     source du fichier livre » n'etaient tenus par rien : CF.download prenait
     n'importe quel blob sous n'importe quel nom. Ici il faut un blob EMIS par
     le CORE (cardBlob) ou rapporte par M.api.blob — donc fabrique par le
     moteur ou par le backend du module. Une toile bricolee a cote ne passe
     pas. */
  function download(blob, name) {
    if (!hasDOM) throw new Error("cardforge: CF.download exige un DOM");
    if (typeof Blob === "undefined" || !(blob instanceof Blob))
      throw new Error("cardforge: CF.download attend un Blob (pas une URL ni une chaine)");
    if (MINTED && !MINTED.has(blob))
      throw new Error("cardforge: blob de provenance inconnue — un telechargement vient de CF.cardBlob (le moteur) ou de M.api.blob (le backend du module), jamais d'une toile fabriquee a cote");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = String(name || "carte.png");
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     9. PERSISTANCE — CORE SEUL. Aucun module n'ecrit le document sur disque.
     ═══════════════════════════════════════════════════════════════════════ */

  let saveTimer = null, OFFLINE = false, HYDRATING = false;
  /* CE QUI A CHANGE : l'autosave envoyait LES HUIT sous-arbres a chaque fois et
     le backend les remplace en bloc. Le disque ne contenait donc pas la fusion
     des huit pieces mais l'etat memoire du DERNIER onglet qui avait sauvegarde
     — deux onglets sur le meme jeu (ou deux builders sur le meme deck, garanti
     a huit en parallele) s'effacaient mutuellement toutes les 900 ms. On
     n'envoie plus que ce qu'on a MODIFIE. Ce qu'un onglet n'a pas touche, il ne
     l'ecrase pas. */
  const DIRTY = new Set();
  function markDirty(k) { if (!HYDRATING) DIRTY.add(k); }

  function scheduleSave() {
    if (!BOOTED || HYDRATING) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveNow, AUTOSAVE_MS);
  }
  function saveBody(keys) {
    const d = doc(), b = {};
    keys.forEach((k) => {
      if (k === "name") b.name = d.name;
      else if (k === "format") b.format = d.format;
      else if (MODULES.indexOf(k) >= 0) b[k] = d[k];
    });
    return b;
  }
  async function saveNow() {
    const keys = Array.from(DIRTY);
    if (!keys.length) return;
    const body = saveBody(keys);
    DIRTY.clear();
    if (OFFLINE || !DOC.id) { localSave({ doc: doc(), cards: cards() }); return; }
    try { await jsonFetch("PATCH", "/cards/" + DOC.id, body); chip("ok", "jeu " + DOC.id + " enregistré (" + keys.join(", ") + ")"); }
    catch (e) {
      keys.forEach((k) => DIRTY.add(k));      /* rien n'est perdu : on retente */
      OFFLINE = true; localSave({ doc: doc(), cards: cards() });
      chip("ko", "hors ligne — sauvegarde locale (" + String(e && e.message || e) + ")");
    }
  }

  /* ── UNE SEULE VERITE, VERIFIEE ─────────────────────────────────────────
     La formule vit des deux cotes (contract.py et le bloc CF-GEOM-FORMULA
     ci-dessus) parce que le rendu est synchrone et ne peut pas attendre le
     reseau. Le risque, c'est qu'elles derivent en silence. Alors on compare :
     a chaque changement de format, le backend est interroge et le moindre
     ecart de pixel devient une alarme visible, pas un decalage d'un pixel
     decouvert chez l'imprimeur. */
  let verifyTimer = null;
  function scheduleVerify() {
    if (OFFLINE || !DOC.id) return;
    clearTimeout(verifyTimer);
    verifyTimer = setTimeout(() => { verifyGeom().catch(() => { }); }, 400);
  }
  async function verifyGeom() {
    if (OFFLINE || !DOC.id) return null;
    const g = geom(), f = DOC.format;
    const qs = "?fmt=" + encodeURIComponent(f.fmt) + "&dpi=" + f.dpi
      + "&bleed_mm=" + f.bleed_mm + "&safe_mm=" + f.safe_mm + "&corner_mm=" + f.corner_mm;
    let r;
    try { r = await jsonFetch("GET", "/cards/" + DOC.id + "/geom" + qs); }
    catch (e) { return null; }                     /* hors ligne : deja signale */
    const b = r && r.geom;
    if (!b) return null;
    const bad = [];
    /* les PIXELS, et aussi les millimetres d'AFFICHAGE : les deux cotes
       arrondissent en demi-haut, une divergence ici veut dire que quelqu'un a
       remis un round() « banquier » quelque part. */
    ["trim_px", "canvas_px", "bleed_off_px", "safe_px", "safe_off_px",
      "trim_mm", "trim_in", "bleed_mm", "safe_mm", "corner_mm", "corner_px"].forEach((k) => {
        if (JSON.stringify(g[k]) !== JSON.stringify(b[k]))
          bad.push(k + " ecran=" + JSON.stringify(g[k]) + " backend=" + JSON.stringify(b[k]));
      });
    const bar = el("#apiBar");
    if (bad.length) {
      console.error("cardforge: GEOMETRIE DIVERGENTE", bad);
      toast("géométrie divergente écran / backend : " + bad[0], true);
      if (bar) {
        bar.classList.remove("hidden");
        const m = el("#apiBarMsg");
        if (m) m.textContent = "La géométrie de l'écran ne correspond pas à celle de "
          + "/api/cards/" + DOC.id + "/geom : " + bad.join(" · ")
          + ". Le fichier exporté et la planche imprimée divergeraient — corriger AVANT de composer.";
      }
      return false;
    }
    return true;
  }
  function localSave(body) {
    try { localStorage.setItem(LS_DECK, JSON.stringify(body)); } catch (e) { /* quota */ }
  }
  function localLoad() {
    try { const s = localStorage.getItem(LS_DECK); return s ? JSON.parse(s) : null; } catch (e) { return null; }
  }
  function rememberDeck(did) {
    try { if (did && DID_RE.test(did)) localStorage.setItem(LS_DECK_ID, did); } catch (e) { /* stockage refuse */ }
  }
  function lastDeck() {
    try { const s = localStorage.getItem(LS_DECK_ID); return (s && DID_RE.test(s)) ? s : null; } catch (e) { return null; }
  }
  function chip(cls, txt) {
    const c = el("#apiChip");
    if (!c) return;
    c.className = "srcchip " + (cls || "");
    c.textContent = txt;
  }
  function randDid() {
    let s = "";
    for (let i = 0; i < 8; i++) s += "0123456789abcdef"[Math.floor(Math.random() * 16)];
    return "deck_" + s;
  }
  function hydrate(data) {
    if (!isPlain(data)) return;
    HYDRATING = true;
    try {
      const d = isPlain(data.doc) ? data.doc : data;
      if (typeof d.id === "string" && DID_RE.test(d.id)) DOC.id = d.id;
      if (typeof d.name === "string" && d.name) DOC.name = d.name.slice(0, 80);
      if (isPlain(d.format)) { try { setFormatInternal(d.format); } catch (e) { console.warn("cardforge: format stocke invalide", e); } }
      MODULES.forEach((id) => {
        if (!isPlain(d[id])) return;
        const allowed = SCHEMA[id];
        Object.keys(d[id]).forEach((k) => {
          if (!allowed || allowed.has(k)) DOC[id][k] = sanitize(d[id][k], id + "." + k);
          else console.warn("cardforge: cle stockee inconnue ignoree — doc." + id + "." + k);
        });
      });
      if (Array.isArray(data.cards) && data.cards.length) setCardsInternal(data.cards);
      touch();
    } finally { HYDRATING = false; }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     10. DEMARRAGE
     ═══════════════════════════════════════════════════════════════════════ */

  /* AUDIT « use strict » — la garantie « une mutation de CF.doc() leve » est
     sous-traitee a une directive que chaque builder ecrit lui-meme, dans des
     <script> classiques ou le mode bâclé est le DEFAUT. lint_cardforge.py la
     refuse au build (R9) ; ici on relit la SOURCE REELLEMENT SERVIE, parce
     qu'un fichier peut avoir ete deploye sans passer par le lint. */
  const DIRECTIVE = /^\s*(?:\/\*[\s\S]*?\*\/|\/\/[^\n]*\n|\s)*["']use strict["']\s*;/;
  async function auditStrict() {
    const fautifs = [];
    await Promise.all(MODULES.map(async (id) => {
      if (!REG[id]) return;
      try {
        const r = await fetch(expectedSrc(id), { cache: "force-cache" });
        if (!r.ok) return;                       /* illisible : le lint tranche */
        const src = await r.text();
        if (!DIRECTIVE.test(src)) fautifs.push(id);
      } catch (e) { /* hors ligne : le lint reste l'autorite */ }
    }));
    if (!fautifs.length) return fautifs;
    /* CONSEQUENCE REELLE, pas un avertissement : le module ne demarre pas et
       ses painters quittent la pile. Un module dont les ecritures sont muettes
       produirait des symptomes incomprehensibles pour les sept autres. */
    fautifs.forEach((id) => {
      REG[id].blocked = true;
      for (let i = PAINTERS.length - 1; i >= 0; i--) if (PAINTERS[i].id === id) PAINTERS.splice(i, 1);
    });
    const msg = "mod-" + fautifs.join(".js, mod-") + ".js ne commence(nt) pas par \"use strict\" : "
      + "dans ce mode une mutation du document est un no-op MUET (le module croit avoir écrit et relit "
      + "l'ancienne valeur). Module non démarré, couches retirées. Règle 9 du lint — build rejeté.";
    console.error("cardforge: " + msg);
    toast("« use strict » manquant : " + fautifs.join(", "), true);
    const bar = el("#apiBar");
    if (bar) {
      bar.classList.remove("hidden");
      const t = el("#apiBarTitle"), m = el("#apiBarMsg");
      if (t) t.textContent = "Module non conforme";
      if (m) m.textContent = msg;
    }
    return fautifs;
  }

  async function openDeck() {
    /* ── UN CHARGEMENT DE PAGE N'EST PAS UNE CREATION ────────────────────
       La revision 1 faisait un POST /cards/decks INCONDITIONNEL des qu'il n'y
       avait pas de ?deck= : chaque ouverture de l'onglet Cartes laissait un
       deck_xxxxxxxx de plus sur le disque de l'utilisateur, sans plafond ni
       ramasse-miettes — le vrai travail se noyait dedans. On REOUVRE le
       dernier jeu (dz_cf_deck_id) et on ne cree que s'il n'existe plus. */
    let did = null;
    try { did = new URLSearchParams(location.search).get("deck"); } catch (e) { /* pas d'URL */ }
    if (!did || !DID_RE.test(did)) did = lastDeck();
    if (did && DID_RE.test(did)) {
      try { return await jsonFetch("GET", "/cards/" + did); }
      catch (e) {
        if (e && e.missing) throw e;               /* domaine absent : hors ligne */
        console.warn("cardforge: dernier jeu " + did + " introuvable, creation d'un nouveau");
      }
    }
    return await jsonFetch("POST", "/cards/decks", { name: DOC.name, format: DOC.format });
  }

  async function boot() {
    if (BOOTED) return;
    BOOTED = true;
    initTheme();
    buildRail();
    buildFormatWidget();
    wireStage();
    if (!CARDS.length) setCardsInternal([{}]);

    /* le jeu : backend s'il repond, disque local sinon. Le lab reste utilisable
       tant que /api/cards n'existe pas encore (la coquille precede le domaine). */
    try {
      const r = await openDeck();
      hydrate(r && r.deck ? r.deck : r);
      rememberDeck(DOC.id);
      chip("ok", "jeu " + (DOC.id || "?"));
    } catch (e) {
      OFFLINE = true;
      const loc = localLoad();
      if (loc) hydrate(loc);
      if (!DOC.id) DOC.id = randDid();
      chip("ko", e && e.missing ? "hors ligne — /api/cards pas encore monté" : "hors ligne — " + String(e.message || e));
      const bar = el("#apiBar");
      if (bar) {
        bar.classList.remove("hidden");
        el("#apiBarMsg").textContent = "Le domaine /api/cards n'est pas monté sur ce backend : le lab tourne en local "
          + "(document conservé dans le navigateur). Tout le reste fonctionne.";
      }
    }

    /* la conformite AVANT le demarrage : un module dont la source n'est pas en
       mode strict n'a pas le droit de tourner (ses ecritures seraient muettes). */
    let bloques = [];
    try { bloques = await auditStrict(); } catch (e) { console.error("cardforge: audit", e); }

    /* les hotes, puis init() de chaque module — apres l'hydratation, pour qu'un
       module lise deja son etat definitif. */
    for (let i = 0; i < MODULES.length; i++) {
      const id = MODULES[i], m = REG[id];
      const host = document.querySelector('.cf-host[data-host="' + id + '"]');
      if (!m) continue;
      m.host = host;
      if (!host) { console.warn("cardforge: pas d'hote pour " + id); continue; }
      host.innerHTML = "";
      if (m.blocked) {
        host.innerHTML = '<p class="cf-boom">Module non démarré : js/mod-' + id
          + '.js ne commence pas par "use strict" (règle 9). Ses écritures dans le document '
          + 'seraient des no-op MUETS et ses couches ont été retirées du rendu.</p>';
        continue;
      }
      try { await m.init(host); }
      catch (e) {
        console.error("cardforge: init " + id, e);
        host.innerHTML = '<p class="cf-boom">Ce module n\'a pas démarré : ' + esc(String(e && e.message || e)) + "</p>";
      }
    }
    syncPanels();
    syncFormatWidget();
    emitCore("core:deck", { id: DOC.id, offline: OFFLINE });
    await drawPreview(true);
    /* la geometrie de l'ecran est confrontee a celle du backend des le premier
       ecran, pas seulement au premier changement de format */
    verifyGeom().then((v) => { if (v === true) console.log("cardforge: geometrie identique ecran / backend"); }).catch(() => { });
    if (typeof ResizeObserver === "function") {
      const stage = el("#stageWrap");
      /* un redimensionnement ne REDESSINE pas : il re-echelonne le bitmap deja
         rendu. Un painter n'est pas rejoue pour une fenetre qu'on etire. */
      if (stage) new ResizeObserver(() => { drawPreview(false).catch(() => { }); }).observe(stage);
    }
  }

  function wireStage() {
    const g = el("#guidesBtn");
    if (g) g.addEventListener("click", () => {
      GUIDES = !GUIDES;
      g.classList.toggle("active", GUIDES);
      invalidate("core");
    });
    const s = el("#sideBtn");
    if (s) s.addEventListener("click", () => {
      PREV_SIDE = PREV_SIDE === "front" ? "back" : "front";
      s.textContent = PREV_SIDE === "front" ? "Recto" : "Verso";
      s.classList.toggle("active", PREV_SIDE === "back");
      invalidate("core");
    });
    const p = el("#prevBtn"), n = el("#nextBtn");
    if (p) p.addEventListener("click", () => { CUR = Math.max(0, CUR - 1); invalidate("core"); });
    if (n) n.addEventListener("click", () => { CUR = Math.min(cards().length - 1, CUR + 1); invalidate("core"); });
    const dl = el("#shotBtn");
    if (dl) dl.addEventListener("click", async () => {
      try {
        busy(true, "rendu de la carte à l'échelle 1…");
        const b = await cardBlob(CUR, {});
        download(b, (DOC.name || "carte").replace(/[^\w\-]+/g, "_") + "_" + (CUR + 1) + ".png");
        toast("carte " + (CUR + 1) + " exportée à " + geom().canvas_px.join(" x ") + " px");
      } catch (e) { toast(String(e && e.message || e), true); }
      finally { busy(false); }
    });
    const gb = el("#guidesBtn");
    if (gb) gb.classList.toggle("active", GUIDES);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LE GLOBAL — gele, et le NOM AVEC.
     Ce qui ECRIT n'est pas ici : c'est sur le jeton rendu par CF.register.
     ═══════════════════════════════════════════════════════════════════════ */

  /* Les noms de la revision 1 qui ecrivaient depuis le global. Ils ne sont pas
     supprimes en silence : ils LEVENT en nommant leur remplacant, sinon un
     builder qui recopie un ancien exemple obtiendrait « CF.patch is not a
     function » et chercherait ailleurs. */
  function gone(name, remplacant) {
    return function () {
      throw new Error("cardforge: CF." + name + " n'existe plus (l'identite ne se lit plus dans la pile d'appel, elle est PORTEE par le jeton) — utiliser " + remplacant);
    };
  }
  function goneObj(name, methods, remplacant) {
    const o = {};
    methods.forEach((m) => { o[m] = gone(name + "." + m, remplacant); });
    return Object.freeze(o);
  }

  const CF = {
    version: VERSION,
    MODULES: Object.freeze(MODULES.slice()),
    Z_TABLE: Object.freeze(Object.assign({}, Z_TABLE)),
    FORMATS: deepFreeze(JSON.parse(JSON.stringify(FORMATS))),
    DPIS: Object.freeze(DPIS.slice()),
    LIM: deepFreeze(JSON.parse(JSON.stringify(LIM))),
    register: register,
    doc: doc, get: get,
    geom: geom, geomOf: geomOf, nativeBleed: nativeBleed,
    cards: cards, card: card,
    current: () => CUR,
    side: () => SIDE,
    renderCard: renderCard, cardBlob: cardBlob,
    renderErrors: () => LAST_ERRORS.slice(),
    on: on, off: off,
    toast: toast, busy: busy, show: show,
    images: images, imageURL: imageURL, ApiMissing: ApiMissing,
    download: download,
    /* ── les noms de la revision 1 ── */
    patch: gone("patch", "le jeton : const M = CF.register({…}) puis M.patch({…})"),
    emit: gone("emit", "M.emit(nom, charge)"),
    setCards: gone("setCards", "le jeton de mod-data.js : M.setCards(lignes)"),
    setFormat: gone("setFormat", "le widget de la barre, ou le jeton de mod-print.js : M.setFormat({…})"),
    api: goneObj("api", ["get", "post", "patch", "del", "raw", "blob", "mine", "url"],
      "M.api.get/post/patch/del/blob(sous-chemin) — confine a /api/cards/<did>/<id>"),
    slot: gone("slot", "M.slot()"),
    aside: gone("aside", "M.aside()"),
    invalidate: gone("invalidate", "M.invalidate()"),
  };
  Object.freeze(CF);

  const g = (typeof window !== "undefined") ? window : (typeof globalThis !== "undefined" ? globalThis : this);
  /* Object.freeze(CF) gele l'OBJET, pas le NOM : `window.CF` restait writable
     et configurable, alors que la premiere ligne de chaque module est
     justement `const CF = window.CF`. Le module charge en premier pouvait donc
     servir un faux contrat aux sept autres — espionner leurs patchs, les
     avaler, leur mentir sur doc() et geom(). Le nom aussi est gele. */
  try {
    Object.defineProperty(g, "CF", { value: CF, writable: false, configurable: false, enumerable: true });
  } catch (e) {
    g.CF = CF;                                   /* moteur exotique : au moins ça */
  }

  if (hasDOM) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => { boot().catch((e) => console.error("cardforge: boot", e)); });
    else raf(() => boot().catch((e) => console.error("cardforge: boot", e)));
  }
})();
