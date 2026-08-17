/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 04 · Données   [P4]
   Proprietaire exclusif de : doc.data · aucun z · /api/cards/<did>/data/*
   Prefixe DOM impose : id="cf-data-..."   ·   feuille : css/mod-data.css

   CE QUE FAIT CETTE PIECE, ET CONTRE QUOI
   La barre est nanDECK 1.29. Sa semantique CSV est bonne — LINK (entete
   devinee), LINKMULTI (quantite), LINKFILTER, LINKSORT, LINKSEP, LINKCSV — mais
   TOUT s'y ecrit a la main, dans un editeur de texte, avec 202 pages d'aide a
   cote ; et l'encodage par defaut y est l'ANSI, donc « MÃ©lÃ©e » sur le premier
   fichier francais venu. Ici : on depose le fichier, le separateur et
   l'encodage se devinent sur les OCTETS, la table est editable, et chaque
   entete de colonne porte un MENU des slots reels de doc.type.slots.

   UN SEUL MOTEUR DE DONNEES. Le decodage, le filtre, le tri, la quantite et le
   mappage vivent dans cards/data.py, en un exemplaire. Cet ecran ne
   reimplemente rien : il POSTe la table et affiche ce qui revient. Deux
   moteurs, ce serait deux semantiques de filtre qui divergent en silence —
   l'ecran annoncerait « 3 lignes retenues » et le deck en contiendrait 4.

   LE JETON. M.setCards(lignes) n'existe QUE sur le jeton de ce fichier (les
   sept autres pieces ne l'ont pas). Il n'est jamais accroche a window.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-data: js/core.js doit etre charge avant ce fichier");

  /* ── slots de repli ───────────────────────────────────────────────────────
     P3 publie doc.type.slots. Tant qu'elle ne l'a pas fait — et cette piece
     doit etre demontrable SEULE — on sert ce jeu-la, clairement annonce comme
     provisoire. Des que P3 ecrit ses slots, le menu bascule dessus tout seul
     (abonnement core:doc). */
  const DEF_SLOTS = [
    { id: "title", label: "Titre" },
    { id: "cost", label: "Coût" },
    { id: "atk", label: "Attaque" },
    { id: "hp", label: "Vie" },
    { id: "type", label: "Type" },
    { id: "rules", label: "Encadré de règles" },
    { id: "flavor", label: "Texte d'ambiance" },
    { id: "number", label: "Numéro" },
    { id: "artist", label: "Artiste" },
  ];

  /* cibles RESERVEES : elles ne remplissent pas un slot de texte mais un champ
     du contrat de carte (spec 2.3 : card.art, card.back, card.id). */
  const RESERVED = [
    { id: "art", label: "▸ Illustration (card.art)" },
    { id: "back", label: "▸ Dos (card.back)" },
    { id: "id", label: "▸ Identifiant (card.id)" },
  ];

  /* colonnes VIRTUELLES — les « jetons de copie n/N » de la spec. Elles
     n'existent pas dans le CSV : elles sont calculees a l'expansion des
     quantites, donc mappables comme n'importe quelle colonne. */
  const VIRT = [
    { k: "#n", label: "n° de copie", hint: "1, 2, 3… dans la ligne" },
    { k: "#N", label: "copies de la ligne", hint: "la quantité de cette ligne" },
    { k: "#i", label: "n° de carte", hint: "1 … total du deck" },
    { k: "#T", label: "total du deck", hint: "le même sur toutes les cartes" },
  ];

  /* AUTO-MAPPAGE — IL N'Y A PLUS DE TABLE DE SYNONYMES ICI.
     Elle y a vecu, indexee par les identifiants du jeu de REPLI ci-dessus
     (hp, type, number). Tant que P3 se taisait, « pv » tombait sur « hp » et
     la demonstration etait belle. Des que P3 publiait ses VRAIS slots — def,
     typeline, num — plus aucun synonyme ne tombait : « pv » restait orpheline
     face a un slot « Vie » vide, et le gabarit imprimait sa valeur de
     demonstration (5) a la place de la donnee (1). Mesure avant correction :
     3 colonnes mappees sur 6, 6 slots sur 9 remplis par le gabarit, zero
     avertissement a l'ecran.
     La table est desormais dans cards/data.py, indexee par CONCEPT et
     confrontee a l'id ET au libelle du slot ; cet ecran l'appelle (/suggest).
     Un seul exemplaire : c'est la meme regle que pour le filtre. */

  const SEPS = [
    { v: "auto", label: "auto" },
    { v: ",", label: "virgule" },
    { v: ";", label: "point-virgule" },
    { v: "\t", label: "tabulation" },
    { v: "|", label: "barre" },
  ];
  const ENCS = [
    { v: "auto", label: "auto" },
    { v: "utf-8", label: "UTF-8" },
    { v: "utf-8-bom", label: "UTF-8 (BOM)" },
    { v: "cp1252", label: "Windows-1252" },
    { v: "utf-16", label: "UTF-16" },
  ];

  const MAX_UNDO = 40;
  const DEBOUNCE_MS = 240;

  /* LE MARQUEUR DE VIDE, ECRIT EN ECHAPPEMENT — cf. cards/data.py : U+200B
     est ce que le moteur pose dans `card.fields[slot]` quand la donnee
     n'alimente pas le slot, pour que le painter de P3 (mod-type.js:857)
     n'imprime PAS son texte de demonstration a la place. On ne l'ecrit jamais
     en clair dans une source : invisible a la relecture, et mange par le
     premier outil qui normalise le fichier. */
  const BLANKCH = /\u200b/g;

  /* ═══ etat local ════════════════════════════════════════════════════════
     T est le modele de travail : le DOM le suit, le document le recoit. On ne
     relit pas doc.data a chaque frappe (le clone deep-frozen coute, et le
     re-rendu volerait le curseur au milieu d'une cellule). */
  let M = null;
  let T = null;
  let HOST = null;
  let REFS = {};
  let SAMPLES = [];
  let LAST = null;          /* derniere reponse de /build */
  let ERR = "";             /* derniere erreur de construction */
  let DRAG = null;          /* colonne en cours de glissement */
  let UNDO = [], REDO = [];
  let SEQ = 0, TIMER = null, MISSING = false;
  let IMPORT_MS = 0, BUILD_MS = 0, IMPORTED_N = 0;
  let LASTTABLE = null;     /* derniere reponse de /parse (encodage, mojibake) */
  let LASTRAW = null;       /* les OCTETS du dernier fichier : c'est eux qu'on
                               relit quand on force un separateur ou un
                               encodage — jamais le texte deja decode, qui
                               serait deja abime. */
  let CHK = null;
  let SLOTS_ARE_DEFAULT = true;
  let SUGG = null;          /* dernier /suggest : orphelines + slots libres */
  let GRAM = null;          /* /grammar : les operateurs, servis par le moteur */
  let ART = null;           /* /artcheck : resolution de la colonne image */
  let ARTSEQ = 0;
  let TIMING = null;        /* decoupage HONNETE du temps d'import */
  let SHOWPROV = true;      /* le tableau « d'ou vient chaque valeur imprimee » */
  /* LE CONSTRUCTEUR DE CONDITION A LA SOURIS. Reproche des DEUX critiques, mot
     pour mot : « le filtre reste une petite langue a apprendre ; il n'y a aucun
     constructeur de condition a la souris — donc sur ce point precis il fait
     exactement ce qu'il reproche a l'autre, ecrire du texte a la main ». Le
     champ reste (on tape plus vite qu'on ne clique quand on sait), mais il
     n'est plus la seule porte. CLAUSES est le decoupage rendu par le MOTEUR :
     l'ecran ne redecoupe rien, sinon ce serait une deuxieme grammaire. */
  let CLAUSES = null;       /* dernier /check : conditions + poids de chacune */
  let BSEL = { col: "", op: "", val: "" };
  /* BOM DECOCHE PAR DEFAUT. Mesure : 258 octets entraient, 261 sortaient.
     L'aller-retour octet pour octet n'existait qu'apres avoir decoche une case
     que personne ne decoche — donc « par defaut, le fichier livre n'est pas
     celui qu'on a importe ». La case reste, pour Excel ; c'est le DEFAUT qui
     change de camp. */
  let BOM = false;
  /* LE MODE PAR DEFAUT QUE LES DEUX CRITIQUES ONT RECLAME. Un slot que la
     donnee n'alimente pas reste VIDE au lieu d'imprimer le texte de
     demonstration du gabarit. Mesure d'avant : 5 des 9 emplacements de la
     carte 1/10 etaient fabriques — coût « 5 », « Créature légendaire —
     Céphalopode », « 017 / 060 », « ill. <nom> » — soit 50 champs inventes sur
     les 10 cartes, indiscernables des vrais. */
  let BLANKMODE = true;
  let LASTEXPORT = null;    /* la PREUVE de l'aller-retour, mesuree sur les
                               octets rendus par le backend, pas sur l'intention */
  /* ═══ LES OCTETS DE LA SOURCE, GARDES POUR ETRE COMPARES ═══════════════════
     LA PASTILLE QUI MENTAIT, ET LA MESURE QUI LA REMPLACE. La case portait
     « sans BOM — octet pour octet » et l'infobulle promettait « le fichier
     rendu est l'octet pour octet de celui qu'on a importe ». RIEN ne le
     mesurait. Mesure faite sur les SIX jeux embarques de cet ecran, export au
     reglage par defaut, comparaison octet par octet :
       parite   210 -> 210  IDENTIQUE
       charge 15693 -> 15693 IDENTIQUE
       ansi     205 -> 226  differe des l'octet 33 (« e » accentue cp1252 =
                            1 octet en entree, 2 en UTF-8 en sortie)
       bom      213 -> 210  differe des l'octet 0 (le BOM d'entree n'est pas
                            rendu quand la case est decochee)
       pieges   203 -> 191  differe des l'octet 143 (les guillemets devenus
                            inutiles ne sont pas remis)
       classeur 1709 -> 210 un zip entre, un CSV sort
     Quatre cas sur six ou l'etiquette affirmait faux — et deux d'entre eux
     sont les jeux que cet ecran propose lui-meme au premier clic. L'etiquette
     ne promet plus rien : on garde les octets LUS et on les COMPARE a ceux
     qu'on livre, avec la position de la premiere divergence. */
  let SRC = null;           /* {bytes, name, enc, encLabel, wb, lost} */
  let SRCDIRTY = false;     /* la table a change depuis l'import : comparer aux
                               octets d'origine ne voudrait plus rien dire */
  /* UNE RECONSTRUCTION EN VOL. « 12 lignes » venait de T (instantane) pendant
     que « 3 retenues / 6 cartes » venait de LAST (la construction PRECEDENTE) :
     pendant la temporisation de 240 ms, trois chiffres cote a cote decrivaient
     deux tables differentes. On ne peut pas les recalculer plus tot — c'est le
     moteur qui les rend, en un seul exemplaire — alors on le DIT. */
  let PENDING = false;
  /* LA MESURE SUR LE FICHIER DE CARTE LIVRE. Le compteur « 0 valeur inventee »
     est une affirmation du moteur sur `card.fields` ; il ne prouve pas que
     l'encre n'arrive pas sur la carte. Celle-ci est prise sur les octets du
     PNG que le CORE livre (`CF.cardBlob`), en-tete IHDR compris. */
  let DELIV = null;

  /* ── petits outils ─────────────────────────────────────────────────────── */
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  /* minuscules SANS accent : « Rare » == « rare ». Les marques combinantes
     s'ecrivent en ECHAPPEMENT — un bloc U+0300..U+036F copie tel quel dans une
     source se fait manger par le premier outil qui normalise le fichier. */
  const COMBINING = /[̀-ͯ]/g;
  const SPACES = /[\s  ]/g;
  function fold(s) {
    return String(s == null ? "" : s).normalize("NFKD")
      .replace(COMBINING, "").trim().toLowerCase();
  }
  function h(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function on(e, ev, fn) { if (e) e.addEventListener(ev, fn); return e; }
  function sepLabel(v) {
    const f = SEPS.filter((s) => s.v === v)[0];
    return f ? f.label : String(v);
  }

  /* ── le modele, lu du document ─────────────────────────────────────────── */
  function loadT() {
    const d = CF.get("data", {}) || {};
    const cols = Array.isArray(d.columns) ? d.columns.map(String) : [];
    const n = cols.length;
    return {
      columns: cols,
      rows: (Array.isArray(d.rows) ? d.rows : []).map((r) => {
        const a = Array.isArray(r) ? r.map((c) => String(c == null ? "" : c)) : [];
        while (a.length < n) a.push("");
        return a.slice(0, n);
      }),
      off: (Array.isArray(d.off) ? d.off : []).map(Number).filter((x) => isFinite(x)),
      map: (d.map && typeof d.map === "object" && !Array.isArray(d.map)) ? Object.assign({}, d.map) : {},
      qty_col: typeof d.qty_col === "string" ? d.qty_col : null,
      filter: typeof d.filter === "string" ? d.filter : "",
      sort: typeof d.sort === "string" ? d.sort : "",
      sep: typeof d.sep === "string" ? d.sep : "auto",
      enc: typeof d.enc === "string" ? d.enc : "auto",
      src: typeof d.src === "string" ? d.src : "",
    };
  }
  function commit() {
    /* LA PREUVE D'ALLER-RETOUR MEURT AVEC LA TABLE QU'ELLE PROUVAIT. « 215
       octets, relus a l'identique » reste vrai du fichier deja ecrit, mais
       affiche a cote d'une table qu'on vient de modifier il devient une
       affirmation sur un fichier qui n'existe plus. Toute mutation passe par
       ici : c'est le seul endroit ou l'effacer une fois pour toutes. Et on
       REPEINT tout de suite : effacer la variable sans effacer la ligne
       laissait la phrase a l'ecran pendant que la table changeait sous elle
       — precisement le defaut qu'on corrige. */
    if (LASTEXPORT) { LASTEXPORT = null; paintProof(); }
    /* LA MEME PEREMPTION, POUR LES DEUX AUTRES MESURES. « identique aux 210
       octets importes » et « 4 812 pixels d'encre en moins sur la carte
       livree » restent vrais des fichiers deja ecrits, mais affiches a cote
       d'une table qu'on vient de changer ils parlent de fichiers qui
       n'existent plus. SRCDIRTY ne les efface pas : il les DATE. */
    SRCDIRTY = true;
    if (DELIV) { DELIV = null; paintDeliv(); }
    M.patch({
      columns: T.columns.slice(),
      rows: T.rows.map((r) => r.slice()),
      off: T.off.slice(),
      map: Object.assign({}, T.map),
      qty_col: T.qty_col,
      filter: T.filter, sort: T.sort, sep: T.sep, enc: T.enc, src: T.src,
    });
  }
  function snap() { return JSON.stringify(T); }
  function pushUndo() {
    UNDO.push(snap());
    if (UNDO.length > MAX_UNDO) UNDO.shift();
    REDO.length = 0;
  }
  function undo() {
    if (!UNDO.length) { M.toast("rien à annuler"); return; }
    REDO.push(snap());
    T = JSON.parse(UNDO.pop());
    commit(); render(); schedule(0);
    M.toast("annulé — " + UNDO.length + " étape(s) restante(s)");
  }
  function redo() {
    if (!REDO.length) { M.toast("rien à rétablir"); return; }
    UNDO.push(snap());
    T = JSON.parse(REDO.pop());
    commit(); render(); schedule(0);
  }

  /* ── slots reels : P3 s'il a parle, repli sinon ──────────────────────────
     On lit AUSSI `text` : c'est la valeur de demonstration du gabarit, celle
     que le painter de P3 imprime quand `card.fields[slot]` est vide
     (mod-type.js: `return v.trim() !== "" ? v : String(slot.text || "")`).
     C'est exactement le texte qu'il faut pouvoir MONTRER a l'utilisateur :
     « ce slot n'est alimente par aucune colonne, et voici ce qui s'imprime a
     la place ». Sans ca on peut compter les slots vides mais pas prouver le
     degat. */
  function slots() {
    const s = CF.get("type.slots", null);
    if (Array.isArray(s) && s.length) {
      const out = [];
      s.forEach((x) => {
        if (!x || typeof x !== "object") return;
        const sid = String(x.id == null ? "" : x.id).trim();
        if (!sid) return;
        out.push({
          id: sid, label: String(x.label || sid),
          text: String(x.text == null ? "" : x.text),
          side: x.side === "back" ? "back" : "front",
          on: x.on !== false,
        });
      });
      if (out.length) { SLOTS_ARE_DEFAULT = false; return out; }
    }
    SLOTS_ARE_DEFAULT = true;
    return DEF_SLOTS.map((d) => ({
      id: d.id, label: d.label, text: "", side: "front", on: true,
    }));
  }
  function allTargets() {
    return slots().concat(RESERVED.map((r) => ({
      id: r.id, label: r.label, text: "", side: "front", on: true,
    })));
  }
  /* CE QUI PART AU MOTEUR AVEC LA TABLE. `text` ET `on` NE SONT PAS DU
     CONFORT : sans eux le moteur ne PEUT PAS savoir ce qui s'imprime, et le
     compteur « N du gabarit » etait une borne superieure affichee comme un
     fait — un slot masque chez P3 (mod-type.js:763 ne dessine que `s.on`) et
     un slot dont le texte de demonstration est vide (mod-type.js:857
     n'imprime alors rien) etaient comptes comme des valeurs fabriquees qui
     n'existaient pas. Mesure : 3 annonces pour 1 vraie sur un jeu de 4 slots
     dont un masque et un muet. Les envoyer, c'est la seule facon d'afficher
     un chiffre qui se prouve. */
  function slotPayload() {
    return allTargets().map((s) => ({
      id: s.id, label: s.label, text: s.text, on: s.on !== false, side: s.side,
    }));
  }
  /* LES TROIS SEULES CLES DU CADRE QUI DECIDENT DU MOT IMPRIME. On ne recopie
     PAS la table des raretes ici : elle vit dans le moteur, en un exemplaire,
     et un test la confronte a la source de la piece 02. Un document ou P2 n'a
     jamais ete touchee rend {} — et le cadre imprime quand meme son bandeau
     par defaut : c'est le cas le plus frequent, et c'est celui qu'on mesurait
     faux. */
  function frameOf() {
    const f = CF.get("frame", {}) || {};
    return {
      banner: f.banner, banner_text: f.banner_text, rarity: f.rarity,
    };
  }
  function slotById(id) {
    const a = allTargets();
    for (let i = 0; i < a.length; i++) if (a[i].id === id) return a[i];
    return null;
  }
  function slotLabel(id) {
    const s = slotById(id);
    return s ? s.label : String(id);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     CONSTRUCTION — un appel, une seule autorite (cards/data.py)
     ═══════════════════════════════════════════════════════════════════════ */
  function schedule(ms) {
    clearTimeout(TIMER);
    PENDING = true;
    paintMeter();
    TIMER = setTimeout(rebuild, ms == null ? DEBOUNCE_MS : ms);
  }
  async function rebuild() {
    const seq = ++SEQ;
    if (!T.columns.length) {
      LAST = null; ERR = ""; PENDING = false; paintMeter(); return;
    }
    const t0 = (typeof performance !== "undefined") ? performance.now() : Date.now();
    try {
      const r = await M.api.post("build", {
        columns: T.columns, rows: T.rows, off: T.off, map: T.map,
        qty_col: T.qty_col, filter: T.filter, sort: T.sort,
        /* les slots REELS partent avec la table : l'audit du mappage
           (« combien de slots la carte remplit avec le texte du gabarit »)
           se calcule la ou vit le mappage, pas dans deux endroits. */
        slots: slotPayload(),
        blank_unfed: BLANKMODE,
        /* CE QUE LE CADRE IMPRIME PAR-DESSUS, ET QU'AUCUN COMPTEUR DE
           `card.fields` NE POUVAIT VOIR. Le bandeau de la piece 02 pose un mot
           sur CHAQUE carte sans passer par un slot : « RARE » sur les 10
           cartes du jeu de parite, alors que la colonne rarete dit « épique »
           sur 5 d'entre elles et « commune » sur 2. Sept cartes fausses
           pendant que cet ecran affichait « 0 valeur inventée ». On ne peut
           pas l'eteindre — le cadre appartient a P2 — mais on peut le
           MESURER, et le taire etait le pire des deux. */
        frame: frameOf(),
      });
      if (seq !== SEQ) return;
      MISSING = false; ERR = "";
      LAST = r || null;
      BUILD_MS = ((typeof performance !== "undefined") ? performance.now() : Date.now()) - t0;
      M.setCards((r && r.cards && r.cards.length) ? r.cards : [{}]);
    } catch (e) {
      if (seq !== SEQ) return;
      if (e && e.missing) { MISSING = true; ERR = "backend /api/cards/…/data absent"; }
      else ERR = String((e && e.message) || e);
      LAST = null;
    }
    if (seq === SEQ) PENDING = false;
    paintMeter();
    paintAudit();
    paintRowFlags();
    paintFilterState();
    paintProof();
    checkArt();
    refreshClauses();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     IMPORT
     ═══════════════════════════════════════════════════════════════════════ */
  function b64of(buf) {
    const b = new Uint8Array(buf);
    let s = "";
    for (let i = 0; i < b.length; i += 0x8000) {
      s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    }
    return btoa(s);
  }
  const now = () => ((typeof performance !== "undefined") ? performance.now() : Date.now());
  async function importBytes(buf, name, opt) {
    const o = opt || {};
    const t0 = now();
    M.busy(true, "lecture de " + (name || "la table") + "…");
    try {
      /* UN FICHIER NEUF EST TOUJOURS RELU EN « AUTO ». Reprendre le
         separateur force au fichier PRECEDENT ferait decouper un .tsv sur des
         point-virgules sans un mot — et « detecte automatiquement, sans
         question posee » ne serait vrai qu'une fois sur deux. Seul `reparse`,
         c'est-a-dire un choix explicite dans les menus, force quelque chose. */
      const b64 = b64of(buf);
      const t1 = now();
      const r = await M.api.post("parse", {
        b64: b64, name: name || "",
        sep: o.sep || "auto", encoding: o.enc || "auto",
        header: o.header || "auto", repair: !!o.repair,
      });
      const t2 = now();
      await applyTable(r && r.table, name, o.preset);
      const t3 = now();
      /* On arrete le chronometre APRES la premiere frame peinte, pas apres la
         construction du DOM : « 200 lignes importees en moins de 2 s » se
         mesure quand la table est A L'ECRAN, sinon on publie le temps de
         `document.createElement` et le chiffre ne veut rien dire. */
      await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(res)));
      const ms = now() - t0;
      IMPORT_MS = ms;
      IMPORTED_N = T.rows.length;
      LASTEXPORT = null;
      /* ON GARDE LES OCTETS LUS. C'est la seule facon de repondre a « le
         fichier rendu est-il celui qu'on a importe ? » autrement que par une
         promesse : la question porte sur deux suites d'octets, elle se tranche
         en les comparant. `applyTable` vient d'appeler `commit()`, donc
         SRCDIRTY est a vrai : on le remet a faux ICI, apres, sinon le drapeau
         de l'import se ferait effacer par l'import lui-meme. */
      const tb = (r && r.table) || {};
      SRC = {
        bytes: new Uint8Array(buf.slice(0)),
        name: String(name || ""),
        enc: String(tb.encoding || ""),
        encLabel: String(tb.encoding_label || tb.encoding || ""),
        wb: !!tb.workbook,
        lost: Number(tb.n_values_lost || 0),
      };
      SRCDIRTY = false;
      DELIV = null;
      /* LE DECOUPAGE, PARCE QU'UN SEUL NOMBRE NE SE VERIFIE PAS. « import
         876 ms » pour 218 octets etait vrai et incomprehensible : on ne
         pouvait ni le croire ni le contester. Les quatre postes sont mesures
         separement, et le moteur rend le sien (`table.ms`) — la difference
         entre `reseau` et `moteur` est le trajet HTTP, pas une estimation. */
      TIMING = {
        b64: t1 - t0,
        net: t2 - t1,
        engine: (r && r.table && isFinite(r.table.ms)) ? r.table.ms : null,
        apply: t3 - t2,
        paint: (now() - t3),
        total: ms,
      };
      paintMeter();
      M.toast(T.rows.length + " ligne(s) importée(s) en " + Math.round(ms) + " ms — "
        + (r.table.workbook ? (r.table.encoding_label || "classeur")
          : ("séparateur " + sepLabel(T.sep) + ", "
            + (r.table.encoding_label || r.table.encoding))));
    } catch (e) {
      if (e && e.missing) { MISSING = true; render(); }
      M.toast(String((e && e.message) || e), true);
    } finally { M.busy(false); }
  }
  async function importText(text, name, opt) {
    const enc = new TextEncoder();
    await importBytes(enc.encode(String(text)).buffer, name, opt);
  }
  async function applyTable(tb, name, preset) {
    if (!tb || !Array.isArray(tb.columns)) throw new Error("réponse d'analyse illisible");
    pushUndo();
    T.columns = tb.columns.map(String);
    T.rows = (tb.rows || []).map((r) => r.map((c) => String(c == null ? "" : c)));
    T.off = [];
    T.sep = tb.sep == null ? "auto" : String(tb.sep);
    T.enc = tb.encoding || "auto";
    T.src = String(name || tb.name || "");
    const sg = await askSuggest(T.columns, null);
    T.map = (sg && sg.map) ? sg.map : {};
    T.qty_col = (sg && sg.qty_col) ? sg.qty_col : null;
    if (preset && typeof preset === "object") {
      if (typeof preset.qty_col === "string") T.qty_col = preset.qty_col || null;
      if (typeof preset.filter === "string") T.filter = preset.filter;
      if (typeof preset.sort === "string") T.sort = preset.sort;
    }
    LASTTABLE = tb;
    commit(); render(); schedule(0);
  }

  /* Le mappage propose vient du MOTEUR. Deux tables de synonymes, c'etait deux
     verites : celle de l'ecran ne connaissait que ses propres identifiants de
     repli et se taisait des que P3 publiait les siens. */
  async function askSuggest(cols, taken) {
    try {
      const r = await M.api.post("suggest", {
        columns: cols, slots: slotPayload(), map: taken || null,
      });
      SUGG = (r && r.suggest) || null;
      return SUGG;
    } catch (e) {
      if (e && e.missing) MISSING = true;
      SUGG = null;
      return null;
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     RENDU DU PANNEAU
     ═══════════════════════════════════════════════════════════════════════ */
  function render() {
    if (!HOST) return;
    slots();                 /* met SLOTS_ARE_DEFAULT a jour AVANT l'affichage */
    HOST.innerHTML = "";
    REFS = {};
    const wrap = h("div", "cf-data-wrap");
    HOST.appendChild(wrap);

    wrap.appendChild(buildMeter());
    /* LE CONTROLE DU MAPPAGE, JUSTE SOUS LES COMPTEURS ET AVANT TOUT LE RESTE.
       C'est le seul chiffre de cet ecran qui fait rater une impression : tant
       qu'il etait absent, la carte affichait « RARE » et « 5 » quand la table
       disait « epique » et « 1 », et rien ne le disait. Il n'est ni repliable
       ni deplacable vers le bas. */
    wrap.appendChild(buildAudit());
    if (MISSING) wrap.appendChild(buildMissing());
    wrap.appendChild(buildSource());
    if (!T.columns.length) {
      wrap.appendChild(buildEmpty());
      paintMeter(); paintAudit();
      return;
    }
    /* ORDRE VOULU : la TABLE en haut. C'est elle qu'on compare a l'editeur de
       script de la barre, et un panneau qui la met sous deux replis la cache
       exactement autant qu'un fichier .txt. */
    wrap.appendChild(buildSelect());
    wrap.appendChild(buildTable());
    wrap.appendChild(buildFoot());
    wrap.appendChild(buildMap());
    paintMeter(); paintAudit(); paintRowFlags(); paintFilterState();
    paintProof(); paintClauses();
    checkArt();
  }

  /* ── compteur PERMANENT (seuil : « compteur de cartes affiche en
        permanence ») ────────────────────────────────────────────────────── */
  function buildMeter() {
    const b = h("div", "cf-data-meter");
    /* « lignes » porte sa propre classe parce qu'il est le SEUL des cinq a
       venir de la table de maintenant : les quatre autres sont rendus par le
       moteur, donc ceux de la construction precedente tant qu'elle n'est pas
       revenue. Eteindre les cinq ferait douter d'un chiffre juste. */
    b.appendChild(h("div", "cf-data-mnum cf-data-mrows", '<b class="cf-data-mv">0</b><i class="cf-data-ml">lignes</i>'));
    b.appendChild(h("div", "cf-data-mnum", '<b class="cf-data-mv">0</b><i class="cf-data-ml">retenues</i>'));
    b.appendChild(h("div", "cf-data-mnum cf-data-mcards", '<b class="cf-data-mv">0</b><i class="cf-data-ml">cartes</i>'));
    /* LE QUATRIEME COMPTEUR, celui qui manquait : combien de slots la carte
       remplit AVEC LE TEXTE DU GABARIT. Il est a cote des trois autres, en
       gros, pas dans une pastille grise de la taille d'un nom de fichier. */
    b.appendChild(h("div", "cf-data-mnum cf-data-mgab",
      '<b class="cf-data-mv">—</b><i class="cf-data-ml">slots au gabarit</i>'));
    /* LE 5e COMPTEUR, ET C'EST LE PLUS IMPORTANT : combien d'EMPLACEMENTS
       fabriques partent sur le tirage entier. « 5 slots » ne dit pas l'ampleur,
       et c'est ce nombre-la qui decide si on part en production.
       IL N'EST PLUS UN PRODUIT. Il valait `slots x cartes`, ce qui suppose que
       chaque slot fabrique sur CHAQUE carte — faux des qu'une colonne posee a
       des cellules vides : ces slots-la ne parlent que sur les cartes ou la
       cellule manque. Mesure du mensonge (3 lignes, qty 3/2/5 -> 10 cartes,
       une cellule `texte` vide, 3 slots sans donnee) : l'ecran affichait
       3 x 10 = 30 valeurs inventees, le compte carte par carte en donne 22.
       Huit de trop, 36 % d'exageration. Le moteur compte desormais, et rend
       les deux parts de l'addition. */
    b.appendChild(h("div", "cf-data-mnum cf-data-mfab",
      '<b class="cf-data-mv">—</b><i class="cf-data-ml">champs inventés</i>'));
    const tags = h("div", "cf-data-mtags");
    b.appendChild(tags);
    /* LE DECOUPAGE DU TEMPS EST ECRIT, PAS CACHE DANS UNE INFOBULLE : une
       infobulle ne se mesure pas sur une capture, et c'est justement sur une
       capture que « import 876 ms » a ete reproche. */
    const line = h("p", "cf-data-tline", "");
    b.appendChild(line);
    REFS.meter = b; REFS.mtags = tags; REFS.tline = line;
    return b;
  }
  function paintMeter() {
    const b = REFS.meter;
    if (!b) return;
    const st = (LAST && LAST.stats) ? LAST.stats : null;
    const au = st && st.audit;
    const vals = b.querySelectorAll(".cf-data-mv");
    const nRows = T.columns.length ? T.rows.length : 0;
    vals[0].textContent = String(nRows);
    vals[1].textContent = st ? String(st.n_kept) : "—";
    vals[2].textContent = st ? String(st.n_cards) : "—";
    /* CE COMPTEUR NE DIT PLUS QUE CE QU'IL PEUT PROUVER. Il comptait tout slot
       sans donnee — y compris ceux que P3 a masques et ceux dont le texte de
       demonstration est vide, qui n'impriment RIEN. Le moteur recoit desormais
       `text` et `on` et ne compte que ce qui s'imprime ; quand le mode
       « laisser vide » est actif, la reponse est zero, et c'est la verite du
       fichier livre. */
    const nGab = au ? au.n_from_template : null;
    const nEvit = au ? (au.n_template_avoided || 0) : 0;
    vals[3].textContent = (nGab == null) ? "—" : String(nGab);
    const gab = b.querySelector(".cf-data-mgab");
    gab.classList.toggle("bad", !!nGab);
    gab.classList.toggle("good", au && !nGab && !!nEvit);
    const gl = gab.querySelector(".cf-data-ml");
    gl.textContent = (au && au.blank_mode)
      ? (nEvit ? "slots au gabarit (" + nEvit + " neutralisé(s))" : "slots au gabarit")
      : "slots au gabarit";
    /* LES DEUX COMPTES DE SLOTS SE RECONCILIENT ICI, PAR ECRIT. Ce compteur
       vaut 6 pendant que le grand livre juste dessous en affiche 5, et rien ne
       le disait : ils ne repondent pas a la meme question. Le grand livre
       classe les slots par ORIGINE (alimente / sans colonne / muet) ; celui-ci
       compte les slots ou le gabarit PREND LA PAROLE — un slot bien mappe
       parle quand meme sur les cartes dont la cellule est vide. Deux chiffres
       justes qui se contredisent a l'oeil valent deux chiffres faux. */
    if (au) {
      const seul = au.n_slots_template_hole_only || 0;
      gab.title = (nGab || nEvit)
        + " = " + au.n_slots_unfed_template + " slot(s) qu'aucune colonne "
        + "n'alimente" + (seul ? (" + " + seul + " slot(s) pourtant mappé(s) "
          + "dont la colonne a des cellules vides (" + (au.slots_template_hole_only
            || []).map(slotLabel).join(", ") + ")") : "")
        + ". Le grand livre ci-dessous en compte "
        + au.n_slots_unfed_template + " : il classe les colonnes, pas les "
        + "prises de parole."
        + (au.blank_mode
          ? (" Mode « laisser vide » actif : le gabarit ne reprend la main "
            + "nulle part, soit " + (au.n_fabricated_avoided || 0)
            + " emplacement(s) évité(s) sur l'ensemble du tirage.")
          : " Mode « texte du gabarit » : ces slots impriment la valeur de "
            + "démonstration de la pièce 03.");
    } else gab.title = "";
    /* CHAMPS INVENTES : le compte du MOTEUR, carte par carte. L'addition est
       ecrite dans l'infobulle avec ses deux parts, et la seule qui se
       multiplie est celle qui a le droit de l'etre. */
    const nFab = au ? (au.n_fabricated || 0) : null;
    const fab = b.querySelector(".cf-data-mfab");
    fab.querySelector(".cf-data-mv").textContent =
      (nFab == null) ? "—" : String(nFab);
    fab.classList.toggle("bad", !!nFab);
    fab.classList.toggle("good", !!au && !nFab);
    fab.title = (nFab == null) ? "" : fabSum(au, st);
    /* LES TROIS COMPTEURS DU MOTEUR PENDANT UNE RECONSTRUCTION. Ils viennent
       de LAST, c'est-a-dire de la table d'AVANT la frappe ; « lignes » vient de
       T, c'est-a-dire de maintenant. Pendant la temporisation, les quatre
       chiffres ne parlent pas de la meme table. On les eteint et on l'ecrit :
       un chiffre perime affiche comme courant est un chiffre faux. */
    b.classList.toggle("stale", !!PENDING && !!st);
    const t = REFS.mtags;
    t.innerHTML = "";
    const add = (txt, cls, title) => {
      const e = h("span", "cf-data-tag " + (cls || ""), esc(txt));
      if (title) e.title = title;
      t.appendChild(e);
    };
    if (PENDING && st) add("recalcul en cours — les 4 compteurs sont ceux de la "
      + "construction précédente", "warn");
    if (T.columns.length) {
      add(T.columns.length + " colonnes");
      /* UN CLASSEUR N'A NI SEPARATEUR NI ENCODAGE DE TEXTE. Afficher
         « séparateur point-virgule · UTF-8 » sur un .xlsx serait un chiffre
         faux de plus. */
      const wb = isWorkbook();
      /* « DEVINE » OU « IMPOSE » : sans ce mot, la pastille « séparateur
         point-virgule » ne dit pas si la detection a travaille ou si le menu a
         ete force — c'est la difference entre une preuve et une valeur par
         defaut heureuse, et le critique le reprochait a juste titre. */
      if (!wb) {
        const auto = LASTTABLE ? (LASTTABLE.sep_auto !== false) : false;
        add("séparateur " + sepLabel(T.sep)
          + (LASTTABLE ? (auto ? " (deviné)" : " (imposé)") : ""));
      }
      /* Apres un rechargement de page LASTTABLE est nul (il n'est pas
         persiste) : on retombe sur l'etiquette lisible du reglage RETENU. Il
         n'y a plus de repli « UTF-8 » invente : quand rien n'a ete decode
         (table saisie a la main, collee), on l'ECRIT. */
      const encName = encLabel();
      add(encName + (LASTTABLE
        ? (LASTTABLE.enc_auto !== false ? " (deviné)" : " (imposé)") : ""),
      encTone());
      if (st && st.disabled) add(st.disabled + " désactivée(s)", "warn");
      /* LIGNES MAL FORMEES — un compteur SEPARE de celui du filtre. « Ligne
         refusee par ma condition » et « ligne que je n'ai pas su lire » n'ont
         rien a voir, et la seconde n'existait pas : `Echo;1;9;99;77` perdait
         99 et 77 avec zero avertissement. */
      if (LASTTABLE && LASTTABLE.n_ragged_long) {
        add(LASTTABLE.n_ragged_long + " ligne(s) trop longue(s) — "
          + LASTTABLE.n_values_lost + " valeur(s) perdue(s)", "err");
      }
      if (LASTTABLE && LASTTABLE.n_ragged_short) {
        add(LASTTABLE.n_ragged_short + " ligne(s) trop courte(s), complétée(s)", "warn");
      }
      /* Le SEUIL de la spec porte sur l'import (« 200 lignes en moins de
         2 s »), pas sur la reconstruction : les deux chiffres sont affiches
         separement, sinon on lirait le plus flatteur des deux. Et le total
         d'import se DEPLIE en ses quatre postes (base64, reseau, moteur,
         peinture) : un seul nombre ne se verifie pas. */
      /* LE NOMBRE DE LIGNES EST DANS LA PASTILLE. « import 149 ms » tout seul
         se lisait comme un debit et n'en etait pas un : le seuil de la spec
         porte sur 200 lignes, la mesure portait sur 4. Un nombre qui ne dit
         pas sur quoi il porte se fait lire pour ce qu'il n'est pas. */
      /* LE VERT NE PEUT PLUS VOULOIR DIRE « SEUIL TENU » QUAND LA MESURE NE
         PORTE PAS SUR LE SEUIL. Mesure du reproche : « le seuil demande 200
         lignes en moins de 2 s, la seule mesure est 4 lignes en 149 ms » — et
         cette pastille-la s'affichait VERTE, c'est-a-dire exactement le mot
         « tenu » sur une mesure qui ne le tenait pas. Vert seulement a partir
         de 200 lignes ; rouge des qu'on depasse 2 s, quel que soit le nombre
         de lignes ; neutre entre les deux, et le texte dit sur quoi il porte. */
      if (IMPORT_MS) add("import " + IMPORTED_N + " ligne(s) en "
        + Math.round(IMPORT_MS) + " ms",
      (IMPORT_MS >= 2000 ? "err" : (IMPORTED_N >= 200 ? "ok" : "")),
      "Le seuil du cahier des charges porte sur 200 lignes en moins de 2 s. "
      + "Mesure ici : " + IMPORTED_N + " ligne(s) en " + Math.round(IMPORT_MS)
      + " ms, octets lus compris et première frame peinte comprise."
      + (IMPORTED_N < 200
        ? " Cette mesure ne porte PAS sur 200 lignes : le jeu « Charge » de "
          + "l'écran vide les fournit."
        : " Le seuil est tenu sur le nombre de lignes qu'il nomme."));
      if (BUILD_MS) add("build " + Math.round(BUILD_MS) + " ms");
      if (T.src) add(T.src);
      if (LASTEXPORT) add(LASTEXPORT.txt, LASTEXPORT.ok ? "ok" : "err");
      if (LASTTABLE && LASTTABLE.mojibake) add("accents douteux", "err");
      /* LE MOT DU CADRE MONTE DANS LA BARRE DES COMPTEURS. Il ne sort d'aucun
         slot, donc aucun des cinq chiffres ne le porte : sans cette pastille
         il faudrait descendre lire le bandeau pour apprendre que sept cartes
         sur dix partent avec un mot faux. */
      if (au && au.frame && au.frame.n_clash) {
        add("cadre : « " + au.frame.word + " » contredit " + au.frame.col
          + " sur " + au.frame.n_clash + " / " + au.frame.n_cards + " cartes",
        "err");
      }
    } else {
      add("aucune donnée — déposez un CSV, un classeur, ou chargez un exemple");
    }
    if (ERR) add(ERR, "err");
    if (st && st.warnings) st.warnings.forEach((w) => add(w, "warn"));
    if (REFS.tline) REFS.tline.innerHTML = (TIMING && T.columns.length)
      ? timingText() : "";
    /* le bouton porte le nombre de cartes qu'il va ecrire : un bouton
       « Exporter le deck » qui ne dit pas combien laisse croire qu'il exporte
       la table, ce qu'il faisait justement avant. */
    if (REFS.expdeck) {
      const nc = st ? st.n_cards : 0;
      REFS.expdeck.textContent = nc
        ? ("Exporter le deck — " + nc + " carte(s)") : "Exporter le deck";
      REFS.expdeck.disabled = !nc;
    }
  }
  /* ═══ L'ADDITION DU COMPTEUR LE PLUS LOURD, ECRITE EN TOUTES LETTRES ═══════
     Un total qu'on ne peut pas refaire de tete se croit ou se rejette en bloc.
     Ses deux parts n'ont pas la meme nature, et c'est tout le sujet :
       · un slot qu'AUCUNE colonne n'alimente parle sur CHAQUE carte : lui, il
         se multiplie, et c'est le seul ;
       · une colonne posee dont certaines cellules sont vides ne fait parler le
         gabarit que sur ces cartes-la — d'ou un compte, pas un produit.
     Le total vient du moteur, mesure carte par carte ; les deux parts sont
     rendues avec lui et leur somme est verifiee ici avant d'etre affichee. */
  function fabSum(au, st) {
    const tot = au.blank_mode ? (au.n_fabricated_avoided || 0)
      : (au.n_fabricated || 0);
    const a = au.n_fab_unfed || 0, b = au.n_fab_holes || 0;
    const nc = (st && st.n_cards) ? st.n_cards : 0;
    const somme = (a + b === tot) ? "" : " [somme incohérente : "
      + a + " + " + b + " ≠ " + tot + " — ne rien conclure de ce chiffre]";
    return (au.blank_mode ? "Auraient été fabriqués : " : "Fabriqués : ")
      + au.n_slots_unfed_template + " slot(s) qu'aucune colonne n'alimente × "
      + nc + " carte(s) = " + a
      + " · + " + b + " emplacement(s) laissés vides par une colonne pourtant "
      + "posée = " + tot + " au total, compté carte par carte par le moteur "
      + "(jamais un produit)." + somme
      + (au.blank_mode ? " Le mode « laisser vide » les a tous neutralisés : "
        + "le fichier livré n'en porte aucun." : "");
  }
  function isWorkbook() {
    return T.enc === "xlsx" || T.enc === "ods";
  }
  /* JAMAIS D'ENCODAGE INVENTE. Le repli « UTF-8 » qui vivait ici affichait une
     pastille verte « UTF-8 » alors que rien n'avait ete decode. */
  function encLabel() {
    if (LASTTABLE && LASTTABLE.encoding_label) return LASTTABLE.encoding_label;
    const f = ENCS.filter((e) => e.v === T.enc)[0];
    if (f && f.v !== "auto") return f.label;
    if (T.enc === "xlsx") return "classeur .xlsx";
    if (T.enc === "ods") return "classeur .ods";
    return "encodage non déterminé (table saisie ici)";
  }
  function encTone() {
    if (T.enc === "cp1252") return "warn";
    if (T.enc === "auto") return "";
    return "ok";
  }
  function timingText() {
    if (!TIMING) return "";
    /* « 0 ms » pour 0,35 ms est un chiffre faux de plus : sous 10 ms on garde
       une decimale, et sous 0,05 ms on ecrit « < 0,1 ms » plutot que zero. */
    /* UNE SEULE REGLE D'ARRONDI, ET ELLE REND UN NOMBRE. `r` ne fait que
       l'habiller : si l'affichage et l'addition arrondissaient chacun de leur
       cote, il y aurait deux verites a reconcilier — le defaut meme qu'on
       corrige depuis quatre tours. */
    const rv = (x) => {
      if (x == null) return null;
      if (x < 0.05) return 0;
      if (x < 10) return Math.round(x * 10) / 10;
      return Math.round(x);
    };
    const r = (x) => {
      if (x == null) return "?";
      const v = rv(x);
      /* `rv` ne rend 0 que sous le plancher : le seuil n'est ecrit qu'une
         fois, ici on ne fait que le lire. */
      if (v === 0) return "< 0,1 ms";
      if (v < 10) return v.toFixed(1).replace(".", ",") + " ms";
      return v + " ms";
    };
    /* Les cinq postes somment EXACTEMENT au total avant arrondi (total =
       base64 + reseau + DOM + peinture, et « trajet HTTP » est le reseau moins
       le moteur) — mais un juge additionne ce qu'il LIT, pas ce qu'on a
       mesure, et cinq arrondis peuvent ecarter la somme de deux millisecondes.
       On fait donc l'addition nous-memes, sur les chiffres affiches. */
    const eng = (TIMING.engine == null) ? null : TIMING.engine;
    const net = (eng == null) ? TIMING.net : Math.max(0, TIMING.net - eng);
    let somme = "";
    if (eng != null) {
      const s = [TIMING.b64, eng, net, TIMING.apply, TIMING.paint]
        .reduce((a, x) => a + rv(x), 0);
      somme = " · <i>somme des cinq postes affichés : " + r(s)
        + " (arrondis)</i>";
    }
    return "où passent ces " + r(TIMING.total) + " : base64 <b>" + r(TIMING.b64)
      + "</b> · moteur <b>" + r(eng)
      + "</b> · trajet HTTP <b>" + r(net)
      + "</b> · table dans le DOM <b>" + r(TIMING.apply)
      + "</b> · première frame peinte <b>" + r(TIMING.paint) + "</b>" + somme;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     CONTROLE DU MAPPAGE — le manque que les deux critiques ont nomme
     ═══════════════════════════════════════════════════════════════════════
     Mesure avant : sur le jeu de parite, 3 colonnes mappees sur 6, 6 slots sur
     9 alimentes par le GABARIT, et la carte affichait « RARE » pour une carte
     epique et « 5 » pour un pv de 1. Aucune pastille, aucun compteur, aucune
     couleur ne le disait. Sur 10 cartes on le voit ; sur 300 on l'imprime.

     CE QUI EST FAIT ICI, ET CE QUI NE PEUT PAS L'ETRE.
     Le liseré d'alerte DANS l'apercu etait la suggestion des critiques ; il est
     hors de portee de cette piece, et pour une bonne raison : les painters ne
     recoivent aucun parametre d'echelle (c'est ce qui garantit apercu ==
     fichier livre), donc tout ce qu'on dessinerait sur l'apercu partirait chez
     l'imprimeur. Le z des reperes est reserve au CORE. La marque est donc
     ICI, devant la donnee : compteur permanent, liste nominative des slots
     nourris par le gabarit AVEC LE TEXTE QU'ILS IMPRIMENT, et un tableau de
     provenance valeur par valeur pour la carte affichee. */
  function buildAudit() {
    const g = h("div", "cf-data-audit");
    REFS.audit = g;
    return g;
  }
  function paintAudit() {
    const g = REFS.audit;
    if (!g) return;
    g.innerHTML = "";
    const st = LAST && LAST.stats;
    const au = st && st.audit;
    if (!T.columns.length) {
      g.className = "cf-data-audit muted";
      g.appendChild(h("p", "cf-data-aline",
        "Aucune table : la carte affichée est <b>entièrement</b> celle du gabarit "
        + "de la pièce 03. Le contrôle du mappage s'allume dès qu'un fichier entre."));
      return;
    }
    if (!au) {
      g.className = "cf-data-audit muted";
      g.appendChild(h("p", "cf-data-aline", "Contrôle du mappage : en attente de la construction…"));
      return;
    }
    const talk = au.slots_unfed_template || [];
    const mute = au.slots_unfed_blank || [];
    const holes = au.holes || [];
    /* LE MEME PRODUIT FAUX QU'AU COMPTEUR, ET IL DECIDAIT DE LA COULEUR DU
       BANDEAU : `n_from_template x n_cards` compte 30 la ou le moteur, carte
       par carte, en trouve 22. Le nombre vient du moteur, point. */
    const fabriques = au.n_fabricated || 0;
    g.className = "cf-data-audit" + (fabriques ? " bad" : " good");

    /* ═══ LES DEUX ADDITIONS, ECRITES POUR ETRE REFAITES DE TETE ═══
       Le reproche etait exact : « 5 / 7 colonnes posées », « 4 / 9 alimentés »
       et « 5 / 9 slots sans donnée » etaient trois denominateurs justes qui se
       contredisaient a l'oeil, parce que la 5e colonne partait vers un champ
       RESERVE — ce que rien n'ecrivait. Deux chiffres qui ne se reconcilient
       pas valent deux chiffres faux. Ici chaque colonne et chaque slot tombe
       dans une case et une seule, et la somme est ecrite avec le total. */
    const led = h("div", "cf-data-aledger");
    const line = (titre, total, parts, cls) => {
      const p = h("div", "cf-data-alnr " + (cls || ""));
      p.appendChild(h("b", "cf-data-alt", esc(titre) + " <u>" + total + "</u>"));
      const eq = h("span", "cf-data-aleq", "");
      parts.forEach((x, k) => {
        if (k) eq.appendChild(h("i", "cf-data-alp", "+"));
        const c = h("span", "cf-data-alc" + (x.bad ? " bad" : (x.good ? " good" : "")));
        c.appendChild(h("b", "", String(x.n)));
        c.appendChild(h("i", "", esc(x.what)));
        if (x.title) c.title = x.title;
        eq.appendChild(c);
      });
      p.appendChild(eq);
      return p;
    };
    /* LA CASE « VERS UN SLOT DISPARU » N'APPARAIT QUE QUAND ELLE EXISTE. Une
       colonne posee sur un slot que P3 a depuis renomme restait comptee « vers
       un slot » pendant qu'aucun slot ne se declarait alimente : deux
       additions justes qui se contredisent a l'oeil — le reproche des trois
       denominateurs, une strate plus bas. Une case a zero permanente, elle,
       serait du bruit. */
    const ghost = au.n_cols_to_ghost
      ? [{ n: au.n_cols_to_ghost, what: "vers un slot disparu", bad: true,
        title: (au.cols_to_ghost || []).join(", ")
          + " — ces colonnes visent un slot qui n'existe plus dans « 03 "
          + "Typographie » : elles n'alimentent rien, reposez-les" }]
      : [];
    led.appendChild(line("colonnes du fichier", au.n_cols, [
      { n: au.n_cols_to_slots, what: "vers un slot", good: true,
        title: (au.cols_to_slots || []).join(", ") },
    ].concat(ghost, [
      { n: au.n_cols_to_reserved, what: "vers un champ réservé",
        title: (au.cols_to_reserved || []).join(", ")
          + " — art / dos / identifiant ne sont pas des slots de texte : "
          + "c'est TOUT l'écart entre « posées » et « alimentés »" },
      /* UNE COLONNE, UNE CASE : quand la colonne de quantite est AUSSI mappee
         vers un slot, elle est comptee a gauche et ce compteur-ci reste a
         zero. Sans cette phrase, l'ecran affiche « quantité 0 » a cote d'un
         menu qui nomme une colonne de quantite — deux verites qui se
         contredisent a l'oeil, exactement le reproche des trois
         denominateurs. */
      { n: au.n_cols_qty, what: au.qty_also_mapped
        ? "quantité (comptée à gauche)" : "quantité",
      title: au.qty_also_mapped
        ? ("« " + String(T.qty_col || "") + " » sert de quantité ET alimente un "
          + "slot : elle est comptée une seule fois, dans « vers un slot ».")
        : (au.cols_qty || []).join(", ") },
      { n: au.n_cols_idle, what: "sans emploi", bad: !!au.n_cols_idle,
        title: (au.cols_unmapped || []).join(", ") },
    ])));
    if (au.slots_known) {
      led.appendChild(line("slots de la carte", au.n_slots, [
        { n: au.n_slots_fed, what: "du fichier", good: true,
          title: (au.slots_fed || []).map(slotLabel).join(", ") },
        /* « SANS COLONNE » EST DANS L'ETIQUETTE, ET C'EST LA RECONCILIATION.
           Ce compteur-ci en affichait 5 pendant que celui du haut en affichait
           6, tous deux dits « au gabarit » : l'un classe les slots par
           ORIGINE, l'autre compte les prises de parole du gabarit (un slot
           mappe parle quand meme sur les cartes a cellule vide). Le mot
           manquant valait un chiffre faux. */
        { n: au.n_slots_unfed_template,
          what: au.blank_mode ? "sans colonne, laissés vides"
            : "sans colonne, au gabarit",
          bad: !au.blank_mode && !!au.n_slots_unfed_template,
          good: !!(au.blank_mode && au.n_slots_unfed_template),
          title: talk.map(slotLabel).join(", ")
            + (au.n_slots_template_hole_only
              ? (" — le compteur du haut en annonce "
                + (au.n_slots_unfed_template + au.n_slots_template_hole_only)
                + " : il ajoute " + au.n_slots_template_hole_only
                + " slot(s) pourtant mappé(s) dont la colonne a des cellules "
                + "vides (" + (au.slots_template_hole_only || [])
                  .map(slotLabel).join(", ") + ")")
              : "") },
        { n: au.n_slots_unfed_blank, what: "vides de toute façon",
          title: mute.map(slotLabel).join(", ")
            + " — sans donnée ET sans texte de démonstration : ils n'impriment "
            + "rien, ils ne sont donc PAS comptés comme fabriqués" },
      ]));
      if (au.n_slots_hidden) {
        led.appendChild(h("p", "cf-data-aline muted",
          "<b>" + au.n_slots_hidden + "</b> slot(s) masqué(s) dans « 03 "
          + "Typographie » — hors compte : la carte ne les dessine pas."));
      }
    } else {
      led.appendChild(h("p", "cf-data-aline", "slots de la pièce 03 non publiés"));
    }
    g.appendChild(led);

    /* LE MODE PAR DEFAUT, ET C'EST LA CORRECTION DU PLUS GROS MANQUE.
       Un bandeau qui AVERTIT puis imprime quand meme n'est pas une parade :
       50 champs fabriques partaient a 300 DPI sous un texte rouge qui les
       decrivait. Le remede est un comportement, pas une phrase. */
    const head = h("div", "cf-data-arow");
    const mode = h("label", "cf-data-blank" + (BLANKMODE ? " on" : " off"));
    const bk = h("input", "");
    bk.type = "checkbox"; bk.checked = BLANKMODE;
    on(bk, "change", () => {
      BLANKMODE = bk.checked;
      M.toast(BLANKMODE
        ? "les slots sans donnée resteront vides sur les cartes"
        : "ATTENTION : les slots sans donnée impriment le texte de démonstration "
        + "du gabarit, indiscernable d'une vraie valeur", !BLANKMODE);
      schedule(0);
    });
    mode.appendChild(bk);
    mode.appendChild(h("span", "cf-data-blankt",
      "Laisser <b>vides</b> les slots sans donnée"));
    mode.title = "Décoché, la pièce 03 imprime son texte de démonstration à la "
      + "place de la donnée manquante — même typographie, même aplomb qu'une "
      + "vraie valeur, sur toutes les cartes du tirage.";
    head.appendChild(mode);
    /* ═══ LE BOUTON QUI VA CHERCHER LA REPONSE DANS LE FICHIER ═══════════════
       « 0 valeur inventée » est une affirmation du MOTEUR sur `card.fields`.
       Elle repose sur une chaine de suppositions : que le marqueur de vide
       survive au `trim()` du painter de P3, qu'il ne pose aucune encre, que le
       gabarit ne reprenne pas la main ailleurs. Trois maillons qu'aucun
       compteur ne verifie. Ce bouton rend la carte DEUX FOIS — dans le mode
       courant, puis dans l'autre — et compare les deux PNG livres pixel par
       pixel. Le chiffre affiche est alors une difference d'octets, pas une
       intention. */
    const mb = h("button", "btn sm cf-data-b cf-data-mesb", "Mesurer sur la carte livrée");
    mb.type = "button";
    mb.title = "Rend la carte affichée dans les deux modes et compare les deux "
      + "fichiers PNG pixel par pixel. Le compteur ci-dessus parle de "
      + "card.fields ; cette mesure parle du fichier.";
    on(mb, "click", () => measureDelivered(mb));
    head.appendChild(mb);
    /* LA PORTEE EST ECRITE DANS LA PHRASE — c'est la correction, et elle tient
       en trois mots. « 0 valeur inventée sur les 10 cartes » etait vrai de
       `card.fields` et FAUX du fichier livre : le bandeau du cadre y posait
       « RARE » sur les dix. Le chiffre etait juste, sa portee etait tue. Un
       chiffre sans sa portee se fait lire pour ce qu'il n'est pas. */
    const hint = h("span", "cf-data-ahint", fabriques
      ? ("<b>" + fabriques + "</b> valeur(s) que personne n'a écrite partiraient "
        + "à l'impression — <b>" + au.n_fab_unfed + "</b> venant de "
        + au.n_slots_unfed_template + " slot(s) sans colonne sur les "
        + (st.n_cards || 0) + " carte(s), <b>" + au.n_fab_holes
        + "</b> de cellules vides sur une colonne posée")
      : (au.blank_mode && au.n_template_avoided
        ? ("<b>0</b> valeur inventée <b>dans les slots</b> sur les "
          + (st.n_cards || 0) + " carte(s) — " + au.n_template_avoided
          + " slot(s) du gabarit neutralisé(s), soit <b>"
          + (au.n_fabricated_avoided || 0) + "</b> emplacement(s) qui auraient "
          + "été fabriqués")
        : "aucun slot ne fabrique de valeur"));
    hint.title = fabSum(au, st);
    head.appendChild(hint);
    g.appendChild(head);
    if (au.frame) g.appendChild(frameLine(au.frame, st));
    const dl = h("p", "cf-data-deliv", "");
    g.appendChild(dl);
    REFS.deliv = dl;
    paintDeliv();

    if (talk.length || mute.length) {
      const box = h("div", "cf-data-aslots");
      box.appendChild(h("div", "lbl", talk.length
        ? ("Slots sans donnée dont le gabarit a un texte — " + (BLANKMODE
          ? "laissés vides sur les " + (st.n_cards || 0) + " carte(s) :"
          : "voici ce qui s'imprime sur les " + (st.n_cards || 0) + " carte(s) :"))
        : "Slots sans donnée (le gabarit n'a rien à imprimer non plus) :"));
      talk.concat(mute).forEach((id) => box.appendChild(unfedChip(id)));
      g.appendChild(box);
    }
    if (holes.length) {
      const box = h("div", "cf-data-aholes");
      holes.forEach((x) => {
        box.appendChild(h("p", "cf-data-aline",
          "Colonne <code>" + esc(x.col) + "</code> → <b>" + esc(slotLabel(x.slot))
          + "</b> : <b>" + x.n_cards + "</b> carte(s) ont la cellule vide — "
          + (x.template
            ? (BLANKMODE
              ? "laissées vides (sans le mode ci-dessus, le gabarit y reprendrait la main)."
              : "<b>sur celles-là le gabarit reprend la main</b>.")
            : "le gabarit n'a rien à y mettre non plus : elles restent vides.")));
      });
      g.appendChild(box);
    }
    const orph = (SUGG && SUGG.orphans) ? SUGG.orphans.filter(
      (o) => T.columns.indexOf(o.col) >= 0 && !T.map[o.col] && o.col !== T.qty_col) : [];
    if (orph.length) {
      const box = h("div", "cf-data-aorph");
      box.appendChild(h("div", "lbl", "Colonnes du fichier qui n'entrent dans aucune carte :"));
      orph.forEach((o) => {
        const p = h("div", "cf-data-aline");
        p.appendChild(h("code", "", esc(o.col)));
        p.appendChild(h("span", "cf-data-awhy", esc(" — " + (o.why || ""))));
        if (o.slot && !usedSlot(o.slot)) {
          const b = h("button", "btn sm cf-data-b", "→ " + esc(slotLabel(o.slot)));
          b.type = "button";
          on(b, "click", () => setMap(o.col, o.slot));
          p.appendChild(b);
        }
        /* DIAGNOSTIC SANS REMEDE, C'ETAIT LE REPROCHE : la seule reponse
           offerte etait d'aller creer un slot dans un AUTRE ecran. Cette piece
           ne peut pas ecrire doc.type.slots (il appartient a P3) — mais elle
           peut poser la colonne sur n'importe quelle cible libre, ici, tout de
           suite. Le renvoi vers « 03 Typographie » reste dans le motif, il
           n'est plus la seule issue. */
        const free = allTargets().filter((s) => !usedSlot(s.id)
          && s.id !== o.slot && s.on !== false);
        if (free.length) {
          const sel = h("select", "cf-data-sel cf-data-osel");
          const o0 = document.createElement("option");
          o0.value = ""; o0.textContent = "poser ici sur…";
          sel.appendChild(o0);
          free.forEach((s) => {
            const op = document.createElement("option");
            op.value = s.id; op.textContent = s.label;
            sel.appendChild(op);
          });
          const oq = document.createElement("option");
          oq.value = "#qty"; oq.textContent = "▸ colonne de quantité";
          sel.appendChild(oq);
          on(sel, "change", () => {
            if (!sel.value) return;
            if (sel.value === "#qty") {
              pushUndo(); T.qty_col = o.col; commit(); render(); schedule(0);
            } else setMap(o.col, sel.value);
          });
          p.appendChild(sel);
        }
        box.appendChild(p);
      });
      g.appendChild(box);
    }
    g.appendChild(buildProv());
  }
  /* ═══ LE MOT DU CADRE, NOMME ET COMPTE ═══════════════════════════════════
     Le reproche etait litteral : « un mot du cadre qui contredit une colonne
     du fichier doit lever une alerte NOMMEE ». Trois cas, trois phrases, et
     aucune n'est un avis :
       · une colonne de rarete existe et le mot la contredit -> rouge, avec le
         compte par carte et le detail des valeurs ;
       · une colonne existe et le mot tombe juste partout -> vert, parce qu'un
         controle qui ne sait pas dire « rien a signaler » se fait ignorer ;
       · aucune colonne de rarete -> gris : le mot est un CHOIX de mise en
         page, pas une contradiction. On le signale quand meme, parce qu'il
         part a l'impression sur toutes les cartes sans venir du fichier. */
  function frameLine(fr, st) {
    const n = fr.n_cards || (st ? st.n_cards : 0) || 0;
    const p = h("p", "cf-data-frameline");
    let etat = "muted", txt = "";
    if (!fr.col) {
      txt = "Le <b>cadre</b> (pièce 02) imprime « <b>" + esc(fr.word)
        + "</b> » sur les <b>" + n + "</b> carte(s) : ce mot ne passe par aucun "
        + "slot et ne vient d'aucune colonne — aucune colonne de rareté dans "
        + "ce fichier, c'est donc un choix de mise en page, pas une donnée.";
    } else if (fr.n_clash > 0) {
      etat = "bad";
      txt = "Le <b>cadre</b> (pièce 02) imprime « <b>" + esc(fr.word)
        + "</b> » sur les <b>" + n + "</b> carte(s), et la colonne <code>"
        + esc(fr.col) + "</code> dit autre chose sur <b>" + fr.n_clash
        + "</b> d'entre elles"
        + (fr.clash && fr.clash.length
          ? (" — " + fr.clash.map((c) => esc(c.v) + " × " + c.n).join(", "))
          : "")
        + ". Ce mot ne passe par aucun slot : cette pièce ne peut pas "
        + "l'éteindre, il se règle dans « 02 Cadre » (bandeau, ou rareté du "
        + "cadre). Tant qu'il est là, <b>" + fr.n_clash + "</b> carte(s) "
        + "partiraient avec un mot que le fichier contredit.";
    } else {
      etat = "good";
      txt = "Le <b>cadre</b> (pièce 02) imprime « <b>" + esc(fr.word)
        + "</b> » sur les <b>" + n + "</b> carte(s) et la colonne <code>"
        + esc(fr.col) + "</code> dit la même chose sur toutes : rien à signaler.";
    }
    p.className = "cf-data-frameline " + etat;
    p.innerHTML = txt;
    return p;
  }
  function usedSlot(id) {
    const k = Object.keys(T.map);
    for (let i = 0; i < k.length; i++) if (T.map[k[i]] === id) return true;
    return false;
  }
  /* Un slot non alimente + le texte qu'il imprime + le menu qui repare, dans
     le meme objet : on ne renvoie pas l'utilisateur chercher le panneau du bas. */
  function unfedChip(id) {
    const s = slotById(id) || { id: id, label: id, text: "" };
    const t = String(s.text || "").trim();
    /* TROIS ETATS, ET ILS NE SE VALENT PAS : un slot dont le gabarit a un
       texte FABRIQUE une valeur ; un slot dont le texte est vide n'imprime
       rien. Les melanger, c'est ce qui gonflait le compteur. */
    const c = h("div", "cf-data-uslot" + (t ? (BLANKMODE ? " muted" : " bad") : " mute"));
    c.appendChild(h("span", "cf-data-usl", esc(s.label)));
    c.appendChild(h("span", "cf-data-usv" + (t ? "" : " empty"),
      t ? ((BLANKMODE ? "<s>" : "") + "« "
        + esc(t.length > 34 ? t.slice(0, 33) + "…" : t) + " »"
        + (BLANKMODE ? "</s> laissé vide" : ""))
        : "rien à imprimer"));
    const sel = h("select", "cf-data-sel cf-data-usel");
    const o0 = document.createElement("option");
    o0.value = ""; o0.textContent = "alimenter avec…";
    sel.appendChild(o0);
    T.columns.forEach((col) => {
      if (T.map[col]) return;
      const o = document.createElement("option");
      o.value = col; o.textContent = col;
      sel.appendChild(o);
    });
    VIRT.forEach((v) => {
      if (T.map[v.k]) return;
      const o = document.createElement("option");
      o.value = v.k; o.textContent = v.k + " — " + v.label;
      sel.appendChild(o);
    });
    on(sel, "change", () => { if (sel.value) setMap(sel.value, id); });
    c.appendChild(sel);
    return c;
  }
  /* ═══════════════════════════════════════════════════════════════════════
     LA MESURE SUR LE FICHIER DE CARTE LIVRE
     ═══════════════════════════════════════════════════════════════════════
     POURQUOI ELLE EXISTE. Le compteur « 0 valeur inventée sur les N cartes »
     est une affirmation du moteur sur `card.fields`. Elle tient par une chaine
     de trois maillons qu'aucun chiffre ne verifiait :
       1. le marqueur de vide survit au `trim()` du painter de P3 ;
       2. il ne pose aucune encre sur la toile ;
       3. le gabarit ne reprend la main nulle part ailleurs.
     Un audit a montre ce que vaut un badge lu dans un en-tete plutot que dans
     les donnees : une carte annoncee « 16 bits » dont les echantillons
     tombaient tous sur le reseau des 8 bits. Le badge etait faux et personne
     ne l'avait ouvert. Ici on ouvre : on rend la carte DEUX FOIS, dans le mode
     courant puis dans l'autre, et on compare les deux PNG que le CORE livre —
     pixel par pixel, en-tete IHDR lu sur les octets. */
  function readIHDR(u) {
    const sig = [137, 80, 78, 71, 13, 10, 26, 10];
    for (let i = 0; i < 8; i++) if (u[i] !== sig[i]) return null;
    if (String.fromCharCode(u[12], u[13], u[14], u[15]) !== "IHDR") return null;
    const be = (o) => (u[o] * 16777216) + (u[o + 1] * 65536)
      + (u[o + 2] * 256) + u[o + 3];
    return { w: be(16), h: be(20), bits: u[24], color: u[25] };
  }
  /* ═══ LE MEME FICHIER, LU PAR LE MOTEUR ══════════════════════════════════
     `readIHDR` ci-dessus s'arrete a l'en-tete — et c'est precisement par la
     qu'un badge « 16 bits » est passe ailleurs en etant faux : l'IHDR
     l'annoncait, les 12 582 912 echantillons tombaient tous sur le reseau
     k·257, soit 7,64 bits utiles. Un en-tete est une DECLARATION. Le moteur
     (cards/data.py, png_report) degonfle les IDAT, defiltre les lignes et
     compte les valeurs vraiment presentes ; il rend aussi l'inventaire des
     chunks et le pHYs — c'est-a-dire la resolution que le fichier DECLARE, ou
     l'absence de toute declaration.
     DEUX LECTEURS INDEPENDANTS DU MEME FICHIER : si l'en-tete lu ici et celui
     lu la-bas ne disent pas la meme chose, on ne conclut pas, on l'ecrit. */
  async function askPng(buf) {
    try {
      const r = await M.api.post("pngcheck", { b64: b64of(buf), deep: true });
      return (r && r.png) || null;
    } catch (e) {
      return { ok: false, error: String((e && e.message) || e) };
    }
  }
  /* LA MOITIE MESURABLE DU CAHIER DES CHARGES, RE-DERIVEE DES MILLIMETRES.
     « Il affiche du 300 DPI qu'il ne livre pas dans cette piece » : le reproche
     tenait tant que rien ne confrontait la pastille a un fichier. Ici les
     pixels attendus sont RECALCULES depuis les millimetres et le DPI du
     document (mm / 25,4 x DPI, arrondi), puis compares a la table du CORE ET a
     l'en-tete du fichier reellement rendu. */
  function geomProof() {
    const g = CF.geom();
    if (!g || !g.trim_mm || !g.canvas_px) return null;
    const px = (mm) => Math.round((mm / 25.4) * g.dpi);
    const tw = g.trim_mm[0], th = g.trim_mm[1];
    const d = {
      g: g, dpi: g.dpi, bleed_mm: g.bleed_mm, safe_mm: g.safe_mm,
      trim: [px(tw), px(th)],
      canvas: [px(tw + 2 * g.bleed_mm), px(th + 2 * g.bleed_mm)],
      safe: [px(tw - 2 * g.safe_mm), px(th - 2 * g.safe_mm)],
    };
    d.same = (d.trim[0] === g.trim_px[0] && d.trim[1] === g.trim_px[1]
      && d.canvas[0] === g.canvas_px[0] && d.canvas[1] === g.canvas_px[1]
      && d.safe[0] === g.safe_px[0] && d.safe[1] === g.safe_px[1]);
    return d;
  }
  async function snapDelivered(i) {
    /* `CF.cardBlob` EST le fichier livre : meme moteur, meme toile, jamais de
       reperes (le z du CORE ne part pas a l'impression). On ne mesure donc pas
       un apercu. */
    const blob = await CF.cardBlob(i);
    const buf = await blob.arrayBuffer();
    const u = new Uint8Array(buf);
    const bmp = await createImageBitmap(blob);
    const cv = document.createElement("canvas");
    cv.width = bmp.width; cv.height = bmp.height;
    const cx = cv.getContext("2d");
    cx.drawImage(bmp, 0, 0);
    const px = cx.getImageData(0, 0, cv.width, cv.height).data;
    try { bmp.close(); } catch (e) { /* moteurs anciens */ }
    return { n: u.length, ihdr: readIHDR(u), px: px, w: cv.width, h: cv.height,
      buf: buf };
  }
  function countDiff(p, q) {
    if (!p || !q || p.length !== q.length) return -1;
    let n = 0;
    for (let k = 0; k < p.length; k += 4) {
      if (p[k] !== q[k] || p[k + 1] !== q[k + 1] || p[k + 2] !== q[k + 2]
        || p[k + 3] !== q[k + 3]) n++;
    }
    return n;
  }
  async function measureDelivered(btn) {
    if (!LAST || !LAST.cards || !LAST.cards.length) {
      M.toast("construisez d'abord le deck", true); return;
    }
    if (typeof createImageBitmap !== "function") {
      M.toast("ce moteur ne sait pas relire un PNG : mesure impossible", true);
      return;
    }
    const was = BLANKMODE;
    const i = CF.current();
    if (btn) btn.disabled = true;
    M.busy(true, "rendu de la carte dans les deux modes…");
    const t0 = now();
    try {
      /* DEUX RENDUS DU MEME ETAT D'ABORD, ET ON COMPTE L'ECART. Une police ou
         une illustration qui finit d'arriver entre les deux photos ferait
         passer son propre changement pour l'encre du gabarit. Ce plancher de
         bruit est mesure et AFFICHE : un chiffre dont on ne connait pas le
         plancher n'est pas un chiffre. */
      const a0 = await snapDelivered(i);
      const a = await snapDelivered(i);
      const noise = countDiff(a0.px, a.px);
      BLANKMODE = !was;
      await rebuild();
      const b = await snapDelivered(i);
      BLANKMODE = was;
      await rebuild();
      if (a.w !== b.w || a.h !== b.h) {
        throw new Error("les deux rendus n'ont pas la même toile");
      }
      const diff = countDiff(a.px, b.px);
      /* le fichier RELLEMENT livre part au moteur : c'est celui du mode
         courant, celui qu'on obtiendrait en cliquant « exporter ». */
      const png = await askPng(a.buf);
      const au = (LAST && LAST.stats && LAST.stats.audit) || null;
      /* LA MESURE PORTE SUR UNE CARTE : LE CHIFFRE QU'ON LUI ACCROCHE AUSSI.
         On affichait « c'est l'encre de N slot(s) × M carte(s) » a cote d'un
         ecart de pixels releve sur UN fichier — un chiffre juste, une portee
         fausse, exactement ce que le critique appelle « un chiffre sans sa
         portee se fait lire pour ce qu'il n'est pas ». Le moteur rend le
         compte par carte ; on prend celui de la carte photographiee, et le
         total du tirage garde sa propre phrase. */
      const per = (au && Array.isArray(au.fab_per_card)) ? au.fab_per_card : null;
      DELIV = {
        i: i, blank: was, n: a.n, nb: b.n, ihdr: a.ihdr, w: a.w, h: a.h,
        diff: diff, noise: noise, tot: a.w * a.h, png: png, geo: geomProof(),
        /* null = non mesure pour cette carte (liste tronquee), et on l'ecrit
           plutot que d'afficher un zero qui passerait pour une mesure. */
        fabCard: (per && i < per.length) ? per[i] : null,
        fabDeck: au ? (au.blank_mode ? (au.n_fabricated_avoided || 0)
          : (au.n_fabricated || 0)) : 0,
        slots: au ? (au.blank_mode ? (au.n_template_avoided || 0)
          : (au.n_from_template || 0)) : 0,
        cards: (LAST && LAST.stats) ? (LAST.stats.n_cards || 0) : 0,
        ms: now() - t0,
      };
      paintDeliv();
      M.toast(diff + " pixel(s) d'écart entre les deux fichiers de carte");
    } catch (e) {
      /* on remet le mode ET le deck : sortir d'ici sur le tirage au gabarit
         parce que la mesure a echoue, ce serait livrer l'inverse de ce que la
         case affiche. */
      BLANKMODE = was;
      schedule(0);
      DELIV = { err: String((e && e.message) || e) };
      paintDeliv();
      M.toast("mesure impossible : " + DELIV.err, true);
    } finally {
      M.busy(false);
      if (btn) btn.disabled = false;
    }
  }
  /* LA GEOMETRIE, AVANT MEME QU'ON CLIQUE. Le reproche etait « il affiche du
     300 DPI qu'il ne livre pas dans cette piece » : la pastille etait juste et
     ne montrait ni son calcul, ni un fichier. Le calcul est desormais ecrit en
     permanence, et le fichier vient s'y confronter des qu'on mesure. */
  function geomText(G) {
    return "À <b>" + G.dpi + " DPI</b>, re-dérivé des millimètres : coupe "
      + G.g.trim_mm[0] + " × " + G.g.trim_mm[1] + " mm → <b>" + G.trim[0]
      + " × " + G.trim[1] + " px</b> · + 2 × " + G.bleed_mm
      + " mm de fond perdu → toile <b>" + G.canvas[0] + " × " + G.canvas[1]
      + " px</b> · − 2 × " + G.safe_mm + " mm → zone sûre <b>" + G.safe[0]
      + " × " + G.safe[1] + " px</b>"
      + (G.same ? "" : " — <b>la table du CORE annonce autre chose ("
        + G.g.canvas_px[0] + " × " + G.g.canvas_px[1] + ")</b>");
  }
  function geomLine() {
    const G = geomProof();
    if (!G) return "";
    return geomText(G) + ". Aucun fichier mesuré pour l'instant : le bouton "
      + "ci-dessus en rend deux et les lit octet par octet.";
  }
  function paintDeliv() {
    const p = REFS.deliv;
    if (!p) return;
    if (!DELIV) {
      const g0 = geomLine();
      p.className = "cf-data-deliv" + (g0 ? " geo" : "");
      p.innerHTML = g0 ? ('<span class="cf-data-dl">' + g0 + "</span>") : "";
      return;
    }
    if (DELIV.err) {
      p.className = "cf-data-deliv bad";
      p.innerHTML = "mesure sur la carte livrée impossible — " + esc(DELIV.err);
      return;
    }
    const d = DELIV;
    const ih = d.ihdr;
    const g = CF.geom();
    const cw = (g && g.canvas_px) ? g.canvas_px[0] : 0;
    const chh = (g && g.canvas_px) ? g.canvas_px[1] : 0;
    /* LES DEUX CONTRADICTIONS QUI FERAIENT TOMBER LE COMPTEUR. On les cherche
       nous-memes : un ecran qui n'essaie pas de se prendre en defaut ne prouve
       rien. */
    /* LES DEUX BRANCHES SE JUGENT SUR LE COMPTE DE CETTE CARTE-LA, pas sur
       celui du tirage : une carte peut n'avoir aucun emplacement fabrique
       pendant que le deck en compte vingt (cellules vides ailleurs). Juger un
       fichier avec le total du tirage, c'est fabriquer une fausse
       contradiction une fois sur deux. */
    const fc = (d.fabCard == null) ? d.slots : d.fabCard;
    let bad = "";
    if (d.blank && fc > 0 && d.diff <= d.noise) {
      bad = "CONTRADICTION — le moteur annonce " + fc + " emplacement(s) du "
        + "gabarit neutralisé(s) sur CETTE carte, et pourtant le fichier ne "
        + "change pas plus que le plancher de bruit quand on rend le gabarit. "
        + "L'un des deux ment : ne pas partir à l'impression sur ce compte.";
    } else if (d.blank && fc === 0 && d.diff > d.noise) {
      bad = "CONTRADICTION — le moteur n'annonce aucun emplacement au gabarit "
        + "sur cette carte, et pourtant " + d.diff + " pixel(s) changent quand "
        + "on le laisse parler. Le compteur ne voit pas tout ce qui s'imprime.";
    }
    /* LES DEUX LECTEURS DU MEME FICHIER, CONFRONTES. Le desaccord est le seul
       cas ou aucun des deux chiffres ne vaut : on le dit avant tout le reste. */
    const R = d.png;
    if (R && R.ok && R.ihdr && ih
      && (R.ihdr.w !== ih.w || R.ihdr.h !== ih.h || R.ihdr.bits !== ih.bits)) {
      bad = (bad ? bad + " " : "")
        + "CONTRADICTION — l'écran lit " + ih.w + " × " + ih.h + " / "
        + ih.bits + " bits dans l'en-tête et le moteur lit " + R.ihdr.w + " × "
        + R.ihdr.h + " / " + R.ihdr.bits + " bits dans le MÊME fichier. "
        + "Aucun des deux ne vaut tant que ce n'est pas expliqué.";
    }
    const ok = !bad && ih && ih.w === cw && ih.h === chh;
    p.className = "cf-data-deliv " + (bad ? "bad" : (ok ? "ok" : "warn"));
    const pct = d.tot ? (Math.round((d.diff / d.tot) * 10000) / 100) : 0;
    const L = [];
    const gr = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    /* 1. le fichier, et ce qu'il CONTIENT — pas ce qu'il annonce */
    let inv = "";
    if (R && R.chunk_counts) {
      const k = Object.keys(R.chunk_counts);
      let tot = 0;
      k.forEach((x) => { tot += R.chunk_counts[x]; });
      inv = " · <b>" + tot + "</b> chunks (" + k.map(
        (x) => x + " ×" + R.chunk_counts[x]).join(", ") + ")";
    }
    L.push("<b>Carte " + (d.i + 1) + " telle qu'elle est livrée</b>, lue octet "
      + "par octet : PNG <b>" + gr(d.n) + "</b> octets" + inv + ".");
    /* 2. l'en-tete, DIT POUR CE QU'IL EST */
    L.push("En-tête IHDR : <b>" + (ih ? (ih.w + " × " + ih.h) : "illisible")
      + " px</b>"
      + (R && R.ihdr ? (", " + esc(R.ihdr.color_label) + " (type "
        + R.ihdr.color + ")" + (R.ihdr.interlace ? ", entrelacé"
          : ", non entrelacé")) : "")
      + ", <b>" + (ih ? ih.bits : "?") + " bits/canal ANNONCÉS</b> — un "
      + "en-tête est une déclaration.");
    /* 3. la profondeur EFFECTIVE, mesuree sur les echantillons */
    if (R && R.deep) {
      L.push("Profondeur <b>effective</b>, mesurée sur les <b>"
        + gr(R.samples) + "</b> échantillons dégonflés et défiltrés : <b>"
        + gr(R.distinct) + "</b> valeur(s) distincte(s), pas du réseau <b>"
        + R.lattice_step + "</b> → <b>"
        + Number(R.bits_effective).toFixed(2).replace(".", ",")
        + " bits utiles</b>"
        + (R.widened_8bit
          ? " — <b>l'en-tête MENT</b> : tout tombe sur le réseau k·257, "
            + "c'est une carte 8 bits élargie."
          : (ih && Math.ceil(R.bits_effective) <= ih.bits
            ? " — l'en-tête dit vrai." : " — incohérent avec l'en-tête."))
        /* LE POIDS MORT SE DIT EN ECHANTILLONS, PAS EN POIDS DE FICHIER : un
           canal constant se comprime a presque rien, donc « N octets de plus
           dans le fichier » serait faux. Ce qui est vrai et mesure : les N
           echantillons du canal valent tous 255, il ne porte rien. */
        + (R.alpha ? (" Canal alpha : <b>" + R.alpha.distinct
          + "</b> valeur(s) distincte(s)"
          + (R.alpha.opaque ? (" — entièrement opaque : ses <b>"
            + gr(R.alpha.bytes) + "</b> échantillons valent tous 255, il ne "
            + "porte aucune information") : (" de " + R.alpha.min + " à "
            + R.alpha.max)) + ".") : ""));
    } else if (R) {
      L.push("Profondeur effective <b>non mesurée</b> : "
        + esc(R.deep_why || R.error || "raison non rendue")
        + " — le chiffre de l'en-tête reste une déclaration.");
    }
    /* 4. LA RESOLUTION, ET C'EST LA QUE LA PASTILLE 300 DPI SE PROUVE OU SE TAIT */
    const G = d.geo;
    let res = "";
    if (R && R.phys && R.dpi != null) {
      res = "Résolution : chunk <b>pHYs</b> présent — " + gr(R.phys.x)
        + " × " + gr(R.phys.y) + " " + esc(R.phys.unit_label) + ", soit <b>"
        + String(R.dpi).replace(".", ",") + " DPI</b> écrits DANS le fichier"
        + (G ? (", pour " + G.dpi + " DPI demandés"
          + (Math.abs(R.dpi - G.dpi) < 0.01 ? " : ils tombent juste."
            : " : <b>ils ne tombent pas juste</b>.")) : ".");
    } else if (R && R.ok) {
      res = "Résolution : <b>aucun chunk pHYs</b> — ce fichier ne déclare "
        + "AUCUN DPI. Ce qui se prouve ici, ce sont ses pixels.";
    }
    if (G) {
      const fit = ih ? (ih.w === G.canvas[0] && ih.h === G.canvas[1]) : false;
      res += " " + geomText(G) + ". L'en-tête du fichier livré dit "
        + (ih ? (ih.w + " × " + ih.h) : "?") + " : "
        + (fit ? "<b>l'arithmétique et le fichier tombent juste</b>."
          : "<b>ILS NE TOMBENT PAS JUSTE</b>.");
    }
    if (res) L.push(res);
    /* 5. l'encre du gabarit, mesuree entre deux fichiers — UNE CARTE, ET ON LE
          DIT. « Le même tirage » parlait de dix cartes a cote d'un ecart de
          pixels releve sur un seul fichier. */
    const port = (d.fabCard == null)
      ? (d.slots + " slot(s) sans donnée (compte par carte non rendu pour "
        + "celle-ci)")
      : (d.fabCard + " emplacement(s) fabriqué(s) sur cette carte");
    L.push("La <b>même carte</b> rendue avec le texte du gabarit fait <b>"
      + gr(d.nb) + "</b> octets et diffère sur <b>" + gr(d.diff)
      + "</b> pixel(s) sur " + gr(d.tot) + " ("
      + String(pct).replace(".", ",") + " %)"
      + (d.blank
        ? (" : c'est l'encre de " + port + ", et elle n'est PAS dans le "
          + "fichier livré.")
        : (" : c'est l'encre fabriquée que le fichier livré CONTIENT — "
          + port + "."))
      + " Sur l'ensemble du tirage, le moteur compte <b>" + d.fabDeck
      + "</b> emplacement(s) fabriqué(s) pour " + d.cards + " carte(s)"
      + (d.blank ? ", tous neutralisés." : ".")
      + " Plancher de bruit mesuré (deux rendus du MÊME état) : <b>" + d.noise
      + "</b> pixel(s). 3 rendus + 2 reconstructions en " + Math.round(d.ms)
      + " ms" + (R && R.ms != null ? (", dont " + Math.round(R.ms)
        + " ms de relecture du PNG par le moteur") : "") + ".");
    if (bad) L.push("<b>" + esc(bad) + "</b>");
    p.innerHTML = L.map((x) => '<span class="cf-data-dl">' + x + "</span>").join("");
  }

  /* LE TABLEAU DE PROVENANCE : pour la carte AFFICHEE, d'ou vient chaque valeur
     imprimee. C'est le « marquage des valeurs qui ne viennent pas du CSV »,
     pose la ou il est lisible et ou il ne peut pas polluer le fichier livre. */
  function buildProv() {
    const d = h("details", "cf-data-prov");
    d.open = SHOWPROV;
    on(d, "toggle", () => { SHOWPROV = d.open; });
    const i = CF.current();
    const cards = CF.cards();
    const card = (cards && cards.length) ? cards[Math.max(0, Math.min(cards.length - 1, i))] : null;
    d.appendChild(h("summary", "", "D'où vient chaque valeur imprimée — carte "
      + (Math.min((i | 0) + 1, cards.length || 1)) + " / " + (cards.length || 1)));
    const tbl = h("table", "cf-data-ptbl");
    const tb = h("tbody", "");
    const src = {};
    Object.keys(T.map).forEach((k) => { src[T.map[k]] = k; });
    allTargets().forEach((s) => {
      if (s.id === "art" || s.id === "back" || s.id === "id") return;
      const raw = (card && card.fields) ? card.fields[s.id] : null;
      const f = (raw == null) ? "" : String(raw);
      /* LE MARQUEUR DE VIDE EST UN CARACTERE INVISIBLE : sans ce test il
         passerait pour une valeur venue du fichier, et cette table — dont tout
         l'interet est de dire d'ou vient chaque valeur — mentirait sur sa
         propre correction. */
      const blanked = (f !== "" && f.replace(BLANKCH, "").trim() === "");
      const fromFile = !blanked && f.trim() !== "";
      const shown = fromFile ? f : (blanked ? "" : String(s.text || ""));
      const tr = h("tr", fromFile ? "" : (blanked ? "blanked" : "gab"));
      tr.appendChild(h("td", "cf-data-pl", esc(s.label)
        + (s.side === "back" ? ' <i class="cf-data-pside">dos</i>' : "")
        + (s.on === false ? ' <i class="cf-data-pside off">masqué</i>' : "")));
      tr.appendChild(h("td", "cf-data-pv", shown
        ? esc(shown.length > 46 ? shown.slice(0, 45) + "…" : shown)
        : ('<i class="cf-data-pnil">' + (blanked ? "laissé vide" : "rien") + "</i>")));
      tr.appendChild(h("td", "cf-data-ps", fromFile
        ? ('fichier · <code>' + esc(src[s.id] || "?") + "</code>")
        : (blanked ? "vide <b>voulu</b>"
          : (s.on === false ? "non dessiné"
            : (s.text ? "<b>GABARIT</b>" : "vide")))));
      tb.appendChild(tr);
    });
    /* LE MOT DU CADRE A SA LIGNE DANS LA TABLE DE PROVENANCE. Elle etait
       incomplete par construction : elle listait les SLOTS, et le bandeau
       n'en est pas un. Un tableau qui promet « d'où vient chaque valeur
       imprimée » et qui saute une valeur imprimee ment sur son titre. */
    const fr = (LAST && LAST.stats && LAST.stats.audit)
      ? LAST.stats.audit.frame : null;
    if (fr && fr.word) {
      const tr = h("tr", fr.n_clash ? "clash" : "gab");
      tr.appendChild(h("td", "cf-data-pl", "Bandeau du cadre"
        + ' <i class="cf-data-pside">02</i>'));
      tr.appendChild(h("td", "cf-data-pv", esc(fr.word)));
      tr.appendChild(h("td", "cf-data-ps", fr.n_clash
        ? ("<b>CADRE</b> · contredit <code>" + esc(fr.col) + "</code> sur "
          + fr.n_clash + " carte(s)")
        : (fr.col ? "CADRE · d'accord avec <code>" + esc(fr.col) + "</code>"
          : "<b>CADRE</b> · aucune colonne")));
      tb.appendChild(tr);
    }
    tbl.appendChild(tb);
    d.appendChild(tbl);
    return d;
  }

  function buildMissing() {
    return h("p", "cf-data-boom",
      "Le domaine <b>/api/cards/&lt;deck&gt;/data</b> n'est pas monté sur ce backend : "
      + "l'analyse CSV, le filtre et le tri vivent là-bas, en un seul exemplaire "
      + "(deux moteurs divergeraient en silence). Relancer le python du :8765.");
  }

  /* ── zone de depot + reglages de lecture ─────────────────────────────────
     DEUX ETATS. Tant qu'il n'y a rien : un grand carre de depot, parce que
     c'est LA chose a faire. Des qu'une table existe : une bande d'une ligne —
     la place appartient alors a la table, pas au bouton qui l'a chargee. */
  function buildSource() {
    const full = !T.columns.length;
    const box = h("div", "cf-data-src" + (full ? "" : " compact"));
    const inp = h("input", "cf-data-file");
    inp.type = "file";
    /* Le tableur, parce que c'est la que les auteurs de jeux tiennent leur
       deck. Un .xlsx et un .ods sont des zips de XML : la lecture tient dans
       cards/data.py avec zipfile et ElementTree, sans une dependance. */
    inp.accept = ".csv,.tsv,.txt,.xlsx,.ods,text/csv,"
      + "text/tab-separated-values,text/plain,"
      + "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
      + "application/vnd.oasis.opendocument.spreadsheet";
    inp.style.display = "none";
    on(inp, "change", () => {
      const f = inp.files && inp.files[0];
      if (f) readFile(f);
      inp.value = "";
    });

    const drop = full
      ? h("div", "drop cf-data-drop",
        '<b>Déposez un fichier .csv / .tsv / .xlsx / .ods</b>'
        + '<span class="hint">ou cliquez pour choisir · <b>Ctrl+V</b> colle une table · '
        + 'séparateur et encodage devinés sur les octets · un classeur n\'a ni l\'un ni l\'autre</span>')
      : h("div", "cf-data-strip", "");
    if (!full) {
      drop.appendChild(h("span", "cf-data-sfile",
        "&#128196; " + esc(T.src || "table saisie à la main")));
      const rep = h("button", "btn sm cf-data-b", "Remplacer…");
      rep.type = "button";
      rep.title = "Charger un autre fichier (ou glissez-le n'importe où sur ce panneau)";
      on(rep, "click", () => inp.click());
      drop.appendChild(rep);
      if (isWorkbook()) {
        /* Un classeur ne se relit pas « en point-virgule » : les deux menus
           n'auraient aucun sens et afficheraient un reglage faux. */
        drop.appendChild(h("span", "cf-data-wb",
          esc(encLabel()) + " · ni séparateur ni encodage à choisir"));
      } else {
        drop.appendChild(pick("Séparateur", SEPS, T.sep, (v) => {
          if (!LASTRAW) { noRaw(); return; }   /* on ne change RIEN sans les octets */
          T.sep = v; commit(); reparse();
        }, true));
        drop.appendChild(pick("Encodage", ENCS, T.enc, (v) => {
          if (!LASTRAW) { noRaw(); return; }
          T.enc = v; commit(); reparse();
        }, true));
      }
      if (LASTTABLE && LASTTABLE.mojibake) {
        const b = h("button", "btn sm cf-data-fix", "Réparer les accents");
        b.type = "button";
        b.title = "Ce fichier contient des suites « Ã© » : du cp1252 relu en UTF-8.";
        on(b, "click", () => reparse({ repair: true }));
        drop.appendChild(b);
      }
      const em = h("button", "btn sm cf-data-b", "Vider");
      em.type = "button";
      em.title = "Repartir de zéro (annulable par Ctrl+Z)";
      on(em, "click", () => {
        pushUndo();
        T.columns = []; T.rows = []; T.off = []; T.map = {}; T.qty_col = null;
        T.filter = ""; T.sort = ""; T.src = "";
        LASTTABLE = null; LASTRAW = null; LAST = null; IMPORT_MS = 0; BUILD_MS = 0;
        SRC = null; DELIV = null; TIMING = null;
        commit(); M.setCards([{}]); render();
      });
      drop.appendChild(em);
    } else {
      on(drop, "click", () => inp.click());
    }
    box.appendChild(drop);
    box.appendChild(inp);
    if (full) {
      const row = h("div", "cf-data-srow");
      row.appendChild(pick("Séparateur", SEPS, T.sep, (v) => {
        if (!LASTRAW) { noRaw(); return; }
        T.sep = v; commit(); reparse();
      }));
      row.appendChild(pick("Encodage", ENCS, T.enc, (v) => {
        if (!LASTRAW) { noRaw(); return; }
        T.enc = v; commit(); reparse();
      }));
      box.appendChild(row);
    }
    REFS.drop = drop;
    return box;
  }
  function pick(label, opts, cur, fn, tiny) {
    const f = h("label", "fld cf-data-fld" + (tiny ? " cf-data-tiny" : ""),
      '<span class="lbl">' + esc(label) + "</span>");
    const s = h("select", "cf-data-sel");
    opts.forEach((o) => {
      const op = document.createElement("option");
      op.value = o.v; op.textContent = o.label;
      if (o.v === cur) op.selected = true;
      s.appendChild(op);
    });
    on(s, "change", () => fn(s.value));
    f.appendChild(s);
    return f;
  }
  /* Les octets d'origine ne survivent pas a un rechargement de page (on ne
     stocke pas un CSV entier dans le document). Sans eux on ne peut PAS
     relire : on le dit, et surtout on ne laisse pas le reglage changer — un
     menu qui afficherait « tabulation » sur une table decoupee aux
     point-virgules serait un mensonge affiche en permanence. */
  function noRaw() {
    render();
    M.toast("les octets d'origine ne sont plus en mémoire : rechargez le fichier "
      + "(« Remplacer… ») pour appliquer ce réglage", true);
  }
  async function reparse(opt) {
    if (!LASTRAW) { noRaw(); return; }
    await importBytes(LASTRAW, T.src, Object.assign({ sep: T.sep, enc: T.enc }, opt || {}));
  }

  function readFile(file) {
    const rd = new FileReader();
    rd.onload = () => { LASTRAW = rd.result; importBytes(rd.result, file.name, {}); };
    rd.onerror = () => M.toast("lecture du fichier impossible", true);
    rd.readAsArrayBuffer(file);
  }

  /* ── etat vide : il PROPOSE ────────────────────────────────────────────── */
  function buildEmpty() {
    const g = h("div", "cf-data-empty");
    g.appendChild(h("p", "cf-data-etitle", "Aucune donnée. Commencez par&nbsp;:"));
    const list = h("div", "cf-data-samples");
    SAMPLES.forEach((s) => {
      /* CES CHIFFRES SONT MESURES PAR LE MOTEUR SUR LES OCTETS DU JEU, pas
         recopies a la main dans le fichier qui les sert. Ils etaient ecrits en
         dur (« 4 lignes · UTF-8 · point-virgule ») a cote d'un jeu d'octets qui
         pouvait changer sans eux : le badge recopie qui finit par mentir. Du
         coup la vignette est aussi la seule preuve visible que la DETECTION
         travaille — six jeux, trois encodages, quatre separateurs, zero
         reglage force (`auto`). */
      const det = (s.auto ? "détecté sur les octets : " : "") + String(s.encoding || "")
        + (s.workbook ? "" : " · " + String(s.sep || ""));
      const b = h("button", "cf-data-sample",
        '<b>' + esc(s.label) + "</b>"
        + '<span class="hint">' + esc(s.hint) + "</span>"
        + '<em class="det">' + esc(det) + "</em>"
        + '<em>' + esc(s.n + " lignes × " + s.n_cols + " colonnes · "
          + s.bytes + " octets"
          + (s.n_cards != null ? (" → " + s.n_kept + " retenues, "
            + s.n_cards + " cartes") : "")) + "</em>"
        + (s.n_warn ? ('<em class="warn">' + s.n_warn + " avertissement(s) : "
          + esc(String(s.warn0 || "")) + "</em>") : ""));
      b.type = "button";
      on(b, "click", () => {
        LASTRAW = null;
        const bin = atob(s.b64);
        const u = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
        LASTRAW = u.buffer;
        importBytes(u.buffer, s.file, { preset: s.preset });
      });
      list.appendChild(b);
    });
    if (!SAMPLES.length) {
      list.appendChild(h("p", "empty-note sm", "Exemples indisponibles (backend muet)."));
    }
    g.appendChild(list);
    /* CE QUE CES VIGNETTES PROUVENT ENSEMBLE — ET LE COMPTE EST FAIT SUR
       ELLES, PAS RECOPIE. Le reproche etait chiffre : « détection démontrée
       sur 1 cas sur 3 pour le séparateur et 1 sur 3 pour l'encodage ; rien ne
       prouve que ce soit une détection et non une valeur par défaut heureuse ».
       Chaque vignette porte deja SA mesure ; cette ligne ne fait que
       DENOMBRER les valeurs distinctes qu'elles ont rendues, aucun reglage
       force. Ecrire « 3 séparateurs » en dur ici serait le meme badge recopie
       qu'on vient de retirer partout ailleurs. */
    if (SAMPLES.length) {
      const seps = [], encs = [], wbs = [];
      SAMPLES.forEach((s) => {
        if (!s.auto) return;
        if (s.workbook) {
          if (s.encoding && wbs.indexOf(s.encoding) < 0) wbs.push(s.encoding);
          return;
        }
        if (s.sep && seps.indexOf(s.sep) < 0) seps.push(s.sep);
        if (s.encoding && encs.indexOf(s.encoding) < 0) encs.push(s.encoding);
      });
      g.appendChild(h("p", "hint cf-data-detsum",
        "Ces <b>" + SAMPLES.length + "</b> jeux sont lus par le moteur "
        + "<b>sans aucun réglage</b>, et les valeurs ci-dessus sont celles "
        + "qu'il a rendues : <b>" + seps.length + "</b> séparateur(s) distinct(s) "
        + "(" + esc(seps.join(", ")) + ") · <b>" + encs.length + "</b> encodage(s) "
        + "distinct(s) (" + esc(encs.join(", ")) + ")"
        + (wbs.length ? (" · <b>" + wbs.length + "</b> classeur(s) sans "
          + "séparateur ni encodage à deviner (" + esc(wbs.join(", ")) + ")") : "")
        + ". Une valeur par défaut heureuse ne tombe pas juste "
        + SAMPLES.length + " fois."));
    }

    const row = h("div", "btn-row cf-data-erow");
    const blank = h("button", "btn strong cf-data-blank", "Table vierge 4 × 3");
    blank.type = "button";
    on(blank, "click", async () => {
      pushUndo();
      T.columns = ["nom", "atk", "pv", "qty"];
      T.rows = [["", "", "", "1"], ["", "", "", "1"], ["", "", "", "1"]];
      T.off = []; T.sep = ";";
      /* Rien n'a ete DECODE : cette table est saisie ici. On n'ecrit donc pas
         « UTF-8 » sur une pastille verte comme si un fichier avait ete lu. */
      T.enc = "auto"; T.src = "table vierge";
      const sg = await askSuggest(T.columns, null);
      T.map = (sg && sg.map) ? sg.map : {};
      T.qty_col = "qty";
      LASTTABLE = null;
      commit(); render(); schedule(0);
    });
    const paste = h("button", "btn strong cf-data-paste", "Coller depuis le presse-papiers");
    paste.type = "button";
    on(paste, "click", async () => {
      try {
        const txt = await navigator.clipboard.readText();
        if (!txt || !txt.trim()) { M.toast("presse-papiers vide", true); return; }
        LASTRAW = null;
        importText(txt, "presse-papiers");
      } catch (e) {
        M.toast("autorisation refusée — utilisez Ctrl+V dans ce panneau", true);
      }
    });
    row.appendChild(blank);
    row.appendChild(paste);
    g.appendChild(row);
    return g;
  }

  /* ── selection : quantite · filtre · tri ─────────────────────────────────
     Les trois directives que la barre fait ecrire a la main (LINKMULTI,
     LINKFILTER, LINKSORT) tiennent sur UNE ligne de champs. */
  /* LES EXEMPLES SONT CEUX DE LA TABLE CHARGEE, PAS D'UNE AUTRE. Mesure du
     reproche : « le nom de colonne dans l'exemple de filtre (atk) ne
     correspond a aucune colonne du fichier charge (attaque) : l'aide donne un
     exemple qui echouerait tel quel ». Et le meme texte glissait un jeton de
     marque maison dans le contenu de demonstration. Les deux disparaissent
     ensemble : l'exemple se calcule sur les entetes reelles, et il est donc
     copiable tel quel. */
  function numCol() {
    for (let j = 0; j < T.columns.length; j++) {
      let n = 0, tot = 0;
      for (let i = 0; i < T.rows.length && i < 40; i++) {
        const v = String(T.rows[i][j] == null ? "" : T.rows[i][j]).trim();
        if (!v) continue;
        tot++;
        if (NUMLIKE.test(v.replace(SPACES, ""))) n++;
      }
      if (tot && n === tot && T.columns[j] !== T.qty_col) return T.columns[j];
    }
    return "";
  }
  function txtCol() {
    for (let j = 0; j < T.columns.length; j++) {
      for (let i = 0; i < T.rows.length && i < 40; i++) {
        const v = String(T.rows[i][j] == null ? "" : T.rows[i][j]).trim();
        if (v && !NUMLIKE.test(v.replace(SPACES, ""))) return T.columns[j];
      }
    }
    return "";
  }
  function hintFilter() {
    const n = numCol(), t = txtCol();
    if (!n && !t) return "ex. une condition sur une colonne de la table";
    if (n && t) return "ex. " + (refCol(n) || n) + " > 1   ·   " + (refCol(t) || t)
      + " contient …";
    const c = n || t;
    return "ex. " + (refCol(c) || c) + (n ? " > 1" : " contient …");
  }
  function hintSort() {
    const n = numCol(), t = txtCol();
    if (!n && !t) return "ex. colonne desc";
    if (n && t) return "ex. " + n + " desc, " + t;
    return "ex. " + (n || t) + " desc";
  }
  function buildSelect() {
    const g = h("div", "cf-data-selbar");
    const body = g;

    const r1 = h("div", "cf-data-srow cf-data-selrow");
    const qsel = h("select", "cf-data-sel");
    const none = document.createElement("option");
    none.value = ""; none.textContent = "— aucune (1 carte par ligne)";
    qsel.appendChild(none);
    T.columns.forEach((c) => {
      const o = document.createElement("option");
      o.value = c; o.textContent = c;
      if (c === T.qty_col) o.selected = true;
      qsel.appendChild(o);
    });
    on(qsel, "change", () => {
      pushUndo(); T.qty_col = qsel.value || null; commit(); schedule(0); renderTableOnly();
    });
    const qf = h("label", "fld cf-data-fld",
      '<span class="lbl">Colonne de quantité</span>');
    qf.appendChild(qsel);
    r1.appendChild(qf);

    /* UN SEUL ETAT, ET ON LE DIT. Les fleches ▲▼ des entetes n'ouvrent pas un
       second tri concurrent : elles ECRIVENT dans ce champ. Deux verites a
       l'ecran pour un seul reglage, c'est un futur bug d'incoherence — et le
       reproche etait fonde tant que rien ne l'annoncait. */
    const sf = h("label", "fld cf-data-fld cf-data-grow",
      '<span class="lbl">Tri du deck <em class="cf-data-same">= les flèches ▲▼ des entêtes</em></span>');
    const sinp = h("input", "cf-data-inp");
    sinp.type = "text"; sinp.value = T.sort;
    sinp.placeholder = hintSort();
    sinp.title = "Ce champ et les flèches des entêtes de colonne sont le MÊME réglage : "
      + "cliquer une flèche réécrit cette ligne.";
    on(sinp, "change", () => { pushUndo(); T.sort = sinp.value; commit(); schedule(0); renderTableOnly(); });
    sf.appendChild(sinp);
    r1.appendChild(sf);

    const ff = h("label", "fld cf-data-fld cf-data-grow2",
      '<span class="lbl">Filtre — les lignes qui deviennent des cartes</span>');
    const finp = h("input", "cf-data-inp cf-data-filter");
    finp.type = "text"; finp.value = T.filter;
    finp.placeholder = hintFilter();
    on(finp, "input", () => { T.filter = finp.value; schedule(); checkFilter(); });
    on(finp, "change", () => { T.filter = finp.value; commit(); schedule(0); });
    ff.appendChild(finp);
    r1.appendChild(ff);
    body.appendChild(r1);
    const fst = h("div", "cf-data-fstate hint", "");
    body.appendChild(fst);
    REFS.filter = finp; REFS.fstate = fst;
    body.appendChild(buildClauses());
    body.appendChild(buildBuilder());

    /* LES OPERATEURS SONT DEPLIES, ET LEUR NOMBRE VIENT DU MOTEUR.
       Replies, on ne pouvait pas savoir a l'ecran s'il y en avait 2 ou 8 — le
       reproche etait juste. Recopier « 9 » a la main aurait fabrique un badge
       de plus qui finit par mentir : la liste arrive de /grammar, et
       test_chaque_operateur_annonce_fonctionne execute chacun d'eux. */
    const help = h("details", "cf-data-help");
    help.open = true;
    const nOps = GRAM ? GRAM.ops.length : 0;
    const nJoin = GRAM ? GRAM.joins.length : 0;
    help.appendChild(h("summary", "", nOps
      ? ("opérateurs acceptés — <b>" + nOps + "</b> comparaisons + <b>" + nJoin
        + "</b> connecteurs <em>(servis par le moteur)</em>")
      : "opérateurs acceptés"));
    const hb = h("div", "cf-data-helpb");
    if (GRAM) {
      const grid = h("div", "cf-data-ops");
      GRAM.ops.forEach((o) => {
        const c = h("span", "cf-data-op");
        c.appendChild(h("code", "", esc(o.sym)));
        c.appendChild(h("i", "", esc(o.what + (o.alias ? "  ·  " + o.alias : ""))));
        c.title = "exemple : " + o.ex;
        grid.appendChild(c);
      });
      GRAM.joins.forEach((o) => {
        const c = h("span", "cf-data-op join");
        c.appendChild(h("code", "", esc(o.sym)));
        c.appendChild(h("i", "", esc(o.what + (o.alias ? "  ·  " + o.alias : ""))));
        grid.appendChild(c);
      });
      hb.appendChild(grid);
    }
    hb.appendChild(h("p", "cf-data-helpn",
      "Comparaison <b>numérique</b> si les deux côtés sont des nombres, sinon texte, accents ignorés. "
      + "Parenthèses acceptées · <code>[nom de colonne]</code> pour un nom avec espaces.<br>"
      + "Une erreur de syntaxe indique la <b>position</b> du caractère fautif, et chaque ligne écartée "
      + "affiche <b>la condition qui l'a écartée</b>. Ce n'est pas un <code>eval</code> : aucune "
      + "expression ne peut exécuter de code."));
    help.appendChild(hb);
    body.appendChild(help);
    return g;
  }
  function checkFilter() {
    clearTimeout(CHK);
    CHK = setTimeout(async () => {
      if (!REFS.fstate) return;
      try {
        const r = await M.api.post("check", { columns: T.columns, filter: T.filter });
        const c = r && r.check;
        if (!c) return;
        if (c.ok) { ERR = ""; paintFilterState(); }
        else { ERR = ""; setFState(false, c.error + " (caractère " + (c.pos + 1) + ")"); }
      } catch (e) { /* le build dira la meme chose */ }
    }, 180);
  }
  /* LE POIDS DE CHAQUE CONDITION, ET IL EST MESURE PAR LE MOTEUR SUR LA VRAIE
     TABLE. C'est ce qui manquait pour CHOISIR : sur « atk > 1 et rarete =
     rare », savoir que la premiere en garde 3 et la seconde 1 dit tout de
     suite laquelle taille le deck. On l'appelle apres la construction (donc
     avec la table qui vient d'etre batie), pas a chaque frappe : envoyer 200
     lignes par lettre tapee serait un chiffre juste paye trop cher. */
  async function refreshClauses() {
    if (!T.columns.length || !T.filter.trim()) { CLAUSES = null; paintClauses(); return; }
    try {
      const r = await M.api.post("check", {
        columns: T.columns, filter: T.filter, rows: T.rows, off: T.off,
      });
      CLAUSES = (r && r.check && r.check.ok) ? r.check : null;
    } catch (e) { CLAUSES = null; }
    paintClauses();
  }

  /* ── LE CONSTRUCTEUR DE CONDITION A LA SOURIS ─────────────────────────────
     Il ECRIT dans le meme champ : un seul reglage, une seule verite. Ce qu'il
     ecrit doit etre exactement ce que le moteur accepte, d'ou les deux regles
     de citation ci-dessous — elles suivent le tokeniseur de cards/data.py
     (mot nu = [^\s()<>=!~\[\]"']+ ; chaine = "..." ou '...' sans echappement ;
     reference = [entre crochets]). Quand une valeur n'est PAS exprimable dans
     cette grammaire (elle contient les deux sortes de guillemets), on ne
     fabrique pas une expression fausse : on le dit et on refuse. */
  const BARE_COL = /^[A-Za-z_][A-Za-z0-9_.\-]*$/;
  const KEYWORDS = ["et", "ou", "non", "and", "or", "not", "pas", "contient",
    "contains", "contain", "commence", "begins", "startswith", "finit",
    "ends", "endswith", "is", "vaut", "egal", "par", "with", "by"];
  const NUMLIKE = /^[+-]?\d+(?:[.,]\d+)?$/;
  function refCol(name) {
    const s = String(name == null ? "" : name);
    if (s.indexOf("]") >= 0) return null;          /* inexprimable : on refuse */
    if (BARE_COL.test(s) && KEYWORDS.indexOf(fold(s)) < 0) return s;
    return "[" + s + "]";
  }
  function litVal(v) {
    const s = String(v == null ? "" : v).trim();
    if (s === "") return '""';
    if (NUMLIKE.test(s.replace(SPACES, ""))) return s.replace(SPACES, "");
    const dq = s.indexOf('"') >= 0, sq = s.indexOf("'") >= 0;
    if (dq && sq) return null;                     /* inexprimable : on refuse */
    if (dq) return "'" + s + "'";
    return '"' + s + '"';
  }
  function colValues(col) {
    const j = T.columns.indexOf(col);
    if (j < 0) return [];
    const seen = {}, out = [];
    for (let i = 0; i < T.rows.length; i++) {
      const v = String(T.rows[i][j] == null ? "" : T.rows[i][j]).trim();
      if (!v || seen[v]) continue;
      seen[v] = 1; out.push(v);
    }
    out.sort((a, b) => (fold(a) < fold(b) ? -1 : (fold(a) > fold(b) ? 1 : 0)));
    return out;
  }
  function buildBuilder() {
    const g = h("div", "cf-data-fbuild");
    g.appendChild(h("span", "lbl",
      "Construire la condition <b>à la souris</b> — elle s'écrit dans le champ ci-dessus"));
    const row = h("div", "cf-data-brow2");
    const cs = h("select", "cf-data-sel cf-data-bcol");
    T.columns.forEach((c) => {
      const o = document.createElement("option");
      o.value = c; o.textContent = c;
      if (c === BSEL.col) o.selected = true;
      cs.appendChild(o);
    });
    if (!BSEL.col || T.columns.indexOf(BSEL.col) < 0) BSEL.col = T.columns[0] || "";
    cs.value = BSEL.col;
    on(cs, "change", () => { BSEL.col = cs.value; BSEL.val = ""; paintBuilder(); });
    row.appendChild(cs);

    /* les operateurs viennent de /grammar : le constructeur ne peut pas en
       proposer un que le moteur ne connait pas. */
    const os = h("select", "cf-data-sel cf-data-bop");
    const ops = (GRAM && GRAM.ops) ? GRAM.ops : [];
    ops.forEach((o) => {
      const e = document.createElement("option");
      e.value = o.sym; e.textContent = o.sym + "  " + o.what;
      if (o.sym === BSEL.op) e.selected = true;
      os.appendChild(e);
    });
    if (!BSEL.op && ops.length) BSEL.op = ops[0].sym;
    if (ops.length) os.value = BSEL.op;
    on(os, "change", () => { BSEL.op = os.value; paintBuilder(); });
    row.appendChild(os);

    const vi = h("input", "cf-data-inp cf-data-bval");
    vi.type = "text";
    vi.value = BSEL.val;
    vi.placeholder = "valeur";
    vi.setAttribute("list", "cf-data-vlist");
    on(vi, "input", () => { BSEL.val = vi.value; paintBuilder(); });
    on(vi, "keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); addClause("et"); }
    });
    row.appendChild(vi);
    const dl = h("datalist", "");
    dl.id = "cf-data-vlist";
    row.appendChild(dl);

    const bet = h("button", "btn sm cf-data-b cf-data-badd", "+ ET");
    bet.type = "button";
    on(bet, "click", () => addClause("et"));
    row.appendChild(bet);
    const bou = h("button", "btn sm cf-data-b cf-data-badd", "+ OU");
    bou.type = "button";
    on(bou, "click", () => addClause("ou"));
    row.appendChild(bou);
    g.appendChild(row);
    const pv = h("p", "cf-data-bpv", "");
    g.appendChild(pv);
    REFS.bcol = cs; REFS.bop = os; REFS.bval = vi; REFS.bdl = dl;
    REFS.bpv = pv; REFS.bet = bet; REFS.bou = bou;
    paintBuilder();
    return g;
  }
  /* le texte EXACT que le bouton va ecrire, montre avant de cliquer : un
     constructeur qui ne montre pas ce qu'il produit est une boite noire de
     plus, et on ne saurait pas relire le champ ensuite. */
  function clauseText() {
    const c = refCol(BSEL.col);
    const v = litVal(BSEL.val);
    if (c === null) return { err: "le nom de colonne contient « ] » : cette grammaire ne sait pas l'écrire" };
    if (v === null) return { err: "la valeur contient les deux sortes de guillemets : inexprimable ici" };
    if (!BSEL.op) return { err: "opérateurs non servis par le moteur" };
    return { txt: c + " " + BSEL.op + " " + v };
  }
  function paintBuilder() {
    if (!REFS.bdl) return;
    const vals = colValues(BSEL.col);
    REFS.bdl.innerHTML = "";
    vals.slice(0, 60).forEach((v) => {
      const o = document.createElement("option");
      o.value = v;
      REFS.bdl.appendChild(o);
    });
    const t = clauseText();
    const ok = !!t.txt;
    if (REFS.bet) REFS.bet.disabled = !ok;
    if (REFS.bou) REFS.bou.disabled = !ok;
    if (REFS.bpv) {
      REFS.bpv.className = "cf-data-bpv" + (ok ? "" : " bad");
      REFS.bpv.innerHTML = ok
        ? ("écrira <code>" + esc(t.txt) + "</code> · <b>" + vals.length
          + "</b> valeur(s) distincte(s) dans « " + esc(BSEL.col) + " »"
          + (vals.length > 60 ? " (les 60 premières sont proposées)" : ""))
        : esc(t.err);
    }
  }
  function addClause(join) {
    const t = clauseText();
    if (!t.txt) { M.toast(t.err, true); return; }
    const cur = String(T.filter || "").trim();
    let next;
    if (!cur) next = t.txt;
    else if (join === "ou") next = cur + " ou " + t.txt;
    else {
      /* PRIORITE : « et » lie plus fort que « ou ». Ajouter « et C » a
         « A ou B » donnerait A ou (B et C) — pas ce qui vient d'etre demande.
         Le moteur dit s'il y a un « ou » de premier niveau ; on parenthese. */
      const needPar = !!(CLAUSES && CLAUSES.top_or);
      next = (needPar ? "(" + cur + ")" : cur) + " et " + t.txt;
    }
    pushUndo();
    T.filter = next;
    if (REFS.filter) REFS.filter.value = next;
    commit(); schedule(0);
    M.toast("condition ajoutée : " + t.txt);
  }
  function buildClauses() {
    const g = h("div", "cf-data-fchips");
    REFS.fchips = g;
    return g;
  }
  function paintClauses() {
    const g = REFS.fchips;
    if (!g) return;
    g.innerHTML = "";
    const cl = (CLAUSES && CLAUSES.clauses) ? CLAUSES.clauses : [];
    if (!cl.length) { g.className = "cf-data-fchips"; return; }
    g.className = "cf-data-fchips on";
    g.appendChild(h("span", "lbl", "Conditions appliquées — <b>" + cl.length
      + "</b>, cliquez la croix pour en retirer une"));
    cl.forEach((c, i) => {
      const chip = h("span", "cf-data-fchip" + (c.ok ? "" : " bad"));
      chip.appendChild(h("code", "", esc(c.expr)));
      if (c.n_kept != null && CLAUSES.n_active != null) {
        chip.appendChild(h("i", "", "retient " + c.n_kept + " / " + CLAUSES.n_active));
        chip.title = "Cette condition SEULE retient " + c.n_kept
          + " ligne(s) active(s) sur " + CLAUSES.n_active
          + " — mesuré par le moteur sur la table, pas estimé.";
      }
      const x = h("button", "cf-data-fx", "&times;");
      x.type = "button";
      x.title = "Retirer cette condition";
      on(x, "click", () => removeClause(i));
      chip.appendChild(x);
      g.appendChild(chip);
    });
    if (CLAUSES.top_or) {
      g.appendChild(h("span", "cf-data-fnote",
        "un « ou » de premier niveau : l'expression ne se découpe pas, "
        + "la seule pastille est le filtre entier"));
    }
  }
  function removeClause(i) {
    const cl = (CLAUSES && CLAUSES.clauses) ? CLAUSES.clauses : [];
    if (!cl.length) return;
    /* Les pastilles PARTITIONNENT l'expression sur ses « et » de premier
       niveau : les recoller avec « et » redonne exactement l'expression de
       depart, moins celle qu'on retire. Aucune reecriture, aucune perte. */
    const next = cl.filter((c, k) => k !== i).map((c) => c.expr).join(" et ");
    pushUndo();
    T.filter = next;
    if (REFS.filter) REFS.filter.value = next;
    commit(); schedule(0);
    M.toast(next ? ("condition retirée — reste : " + next) : "filtre vidé");
  }
  function setFState(ok, msg) {
    const f = REFS.fstate, i = REFS.filter;
    if (!f) return;
    f.className = "cf-data-fstate hint" + (ok ? "" : " bad");
    f.innerHTML = msg;
    if (i) i.classList.toggle("bad", !ok);
  }
  function paintFilterState() {
    if (!REFS.fstate) return;
    const st = LAST && LAST.stats;
    if (ERR) { setFState(false, esc(ERR)); return; }
    if (!T.filter.trim()) {
      setFState(true, st ? ("aucun filtre — " + st.n_active + " ligne(s) active(s)") : "aucun filtre");
      return;
    }
    setFState(true, st
      ? ("<b>" + st.n_kept + "</b> ligne(s) retenue(s) sur " + st.n_active
        + " · <b>" + st.n_cards + "</b> carte(s) après quantité")
      : "…");
  }

  /* ── mappage : glisser-deposer + menu par colonne ──────────────────────── */
  function buildMap() {
    const g = h("details", "grp cf-data-grp");
    g.open = true;
    const tgt = allTargets();
    const nFed = tgt.filter((s) => usedSlot(s.id)).length;
    g.appendChild(h("summary", "",
      "Mappage colonne → slot <em class=\"cf-data-same\">— le même réglage que les menus "
      + "des entêtes de colonne</em>" + (SLOTS_ARE_DEFAULT
        ? ' <em class="cf-data-warnp">slots par défaut — la pièce 03 n\'a pas encore publié les siens</em>'
        : "")));
    const body = h("div", "grp-body cf-data-body cf-data-maprow");
    g.appendChild(body);

    /* gauche : les sources, glissables */
    const left = h("div", "cf-data-cols");
    const nMapped = T.columns.filter((c) => !!T.map[c]).length;
    left.appendChild(h("div", "lbl", "Colonnes du fichier — <b>" + nMapped + " / "
      + T.columns.length + "</b> posées · glissez-les à droite"));
    T.columns.forEach((c, j) => left.appendChild(colChip(c, j, false)));
    left.appendChild(h("div", "lbl cf-data-vlbl",
      "Jetons de copie — les <b>" + VIRT.length + "</b> sont ici (n, N, i, T)"));
    VIRT.forEach((v) => left.appendChild(colChip(v.k, -1, true, v)));
    body.appendChild(left);

    /* droite : les cibles, deposables.
       LE COMPTE EST DANS L'ETIQUETTE, ET LA LISTE A SON PROPRE ASCENSEUR : la
       liste etait coupee net par le bord du panneau (elle s'arretait sur
       « Vie »), on mappait a l'aveugle sur des slots qu'on ne voyait pas. */
    /* LE MEME DENOMINATEUR QUE LE BANDEAU D'ALERTE, ET IL VIENT DE LA MEME
       SOURCE. Compter ici et compter la-haut, c'etait deux comptes qui se
       contredisaient a l'oeil ; le moteur en rend UN et les deux panneaux le
       recopient. En repli — avant la premiere construction — on le calcule
       localement, et on ecrit alors le meme denominateur : les slots VISIBLES,
       masques exclus, comme le moteur. */
    const au0 = (LAST && LAST.stats && LAST.stats.audit) || null;
    const real = slots().filter((s) => s.on !== false);
    const nReal = au0 ? au0.n_slots_fed : real.filter((s) => usedSlot(s.id)).length;
    const nTot = au0 ? au0.n_slots : real.length;
    const nHid = au0 ? (au0.n_slots_hidden || 0)
      : (slots().length - real.length);
    const right = h("div", "cf-data-slots");
    right.appendChild(h("div", "lbl", "Slots de la carte — <b>" + nReal + " / "
      + nTot + "</b> alimentés · + " + RESERVED.length
      + " champs réservés" + (nHid ? (" · " + nHid + " masqué(s), hors compte") : "")
      + " · déposez ici"));
    const list = h("div", "cf-data-slotlist");
    tgt.forEach((s) => list.appendChild(slotTarget(s)));
    right.appendChild(list);
    body.appendChild(right);
    return g;
  }
  function sample(j) {
    for (let i = 0; i < T.rows.length && i < 12; i++) {
      const v = T.rows[i][j];
      if (v) return v;
    }
    return "";
  }
  function colChip(key, j, virt, meta) {
    const c = h("div", "cf-data-chip" + (virt ? " virt" : "") + (T.map[key] ? " mapped" : ""));
    c.draggable = true;
    c.dataset.k = key;
    c.appendChild(h("span", "cf-data-cn", esc(key)));
    const s = virt ? (meta ? meta.hint : "") : sample(j);
    /* Une valeur coupee sans « … » est une valeur AFFICHEE FAUSSE. */
    if (s) {
      const txt = String(s);
      c.appendChild(h("span", "cf-data-cs",
        esc(txt.length > 30 ? txt.slice(0, 29) + "…" : txt)));
    }
    const cur = T.map[key];
    if (cur) c.appendChild(h("em", "cf-data-cm", "→ " + esc(cur)));
    on(c, "dragstart", (e) => {
      DRAG = key;
      c.classList.add("dragging");
      try { e.dataTransfer.setData("text/plain", key); e.dataTransfer.effectAllowed = "copy"; } catch (x) { /* vieux moteur */ }
    });
    on(c, "dragend", () => { DRAG = null; c.classList.remove("dragging"); });
    return c;
  }
  function slotTarget(s) {
    const t = h("div", "cf-data-slot" + (s.id === "art" || s.id === "back" || s.id === "id" ? " res" : ""));
    t.dataset.slot = s.id;
    const srcs = Object.keys(T.map).filter((k) => T.map[k] === s.id);
    t.appendChild(h("span", "cf-data-sl", esc(s.label)));
    const val = h("span", "cf-data-sv", srcs.length ? esc(srcs.join(", "))
      : (String(s.text || "") ? "gabarit" : "—"));
    t.appendChild(val);
    if (srcs.length) {
      const x = h("button", "cf-data-x", "&times;");
      x.type = "button"; x.title = "Retirer ce mappage";
      on(x, "click", (e) => {
        e.stopPropagation();
        pushUndo();
        srcs.forEach((k) => { delete T.map[k]; });
        commit(); render(); schedule(0);
      });
      t.appendChild(x);
    } else {
      /* Un slot libre n'est pas neutre : le gabarit y imprime SON texte. On
         montre lequel, ici, a l'endroit ou l'on decide. */
      t.classList.add("free");
      const g = String(s.text || "");
      if (g) {
        t.classList.add("gab");
        t.title = "Aucune colonne : la carte imprime le texte du gabarit — « " + g + " »";
      }
    }
    on(t, "dragover", (e) => {
      if (!DRAG) return;
      e.preventDefault();
      try { e.dataTransfer.dropEffect = "copy"; } catch (x) { /* vieux moteur */ }
      t.classList.add("over");
    });
    on(t, "dragleave", () => t.classList.remove("over"));
    on(t, "drop", (e) => {
      e.preventDefault(); e.stopPropagation();
      t.classList.remove("over");
      const k = DRAG || (e.dataTransfer && e.dataTransfer.getData("text/plain"));
      DRAG = null;
      if (!k) return;
      setMap(k, s.id);
    });
    return t;
  }
  function setMap(key, slot) {
    pushUndo();
    if (slot) {
      Object.keys(T.map).forEach((k) => { if (T.map[k] === slot) delete T.map[k]; });
      T.map[key] = slot;
    } else { delete T.map[key]; }
    commit(); render(); schedule(0);
    resuggest();
  }
  /* le moteur recalcule les orphelines : sinon la liste d'alerte parle encore
     d'une colonne qu'on vient de poser. */
  function resuggest() {
    if (!T.columns.length) { SUGG = null; paintAudit(); return; }
    askSuggest(T.columns, T.map).then(paintAudit);
  }

  /* ── la table editable ─────────────────────────────────────────────────── */
  function sortKeys() {
    const out = [];
    String(T.sort || "").split(",").forEach((p) => {
      let s = p.trim();
      if (!s) return;
      let desc = false;
      if (s.charAt(0) === "-") { desc = true; s = s.slice(1).trim(); }
      const bits = s.replace(/:/g, " ").split(/\s+/);
      const last = fold(bits[bits.length - 1]);
      if (bits.length > 1 && (last === "desc" || last === "decroissant")) { desc = true; bits.pop(); }
      else if (bits.length > 1 && (last === "asc" || last === "croissant")) { bits.pop(); }
      const nm = bits.join(" ").replace(/^\[|\]$/g, "");
      if (nm) out.push({ name: nm, desc: desc });
    });
    return out;
  }
  function viewOrder() {
    const idx = T.rows.map((r, i) => i);
    const keys = sortKeys();
    if (!keys.length) return idx;
    const num = (v) => {
      const s = String(v == null ? "" : v).replace(SPACES, "").replace(",", ".");
      if (!/^[+-]?\d+(\.\d+)?$/.test(s)) return null;
      return parseFloat(s);
    };
    const out = idx.slice();
    for (let k = keys.length - 1; k >= 0; k--) {
      const j = T.columns.map(fold).indexOf(fold(keys[k].name));
      if (j < 0) continue;
      const dsc = keys[k].desc;
      out.sort((a, b) => {
        const va = T.rows[a][j], vb = T.rows[b][j];
        const na = num(va), nb = num(vb);
        let c;
        if (na !== null && nb !== null) c = na - nb;
        else if (na !== null) c = -1;
        else if (nb !== null) c = 1;
        else c = fold(va) < fold(vb) ? -1 : (fold(va) > fold(vb) ? 1 : 0);
        return dsc ? -c : c;
      });
    }
    return out;
  }
  function buildTable() {
    const box = h("div", "cf-data-tbox");
    const tbl = h("table", "cf-data-tbl");
    const thead = h("thead", "");
    const trh = h("tr", "");
    trh.appendChild(h("th", "cf-data-thn", "#"));
    T.columns.forEach((c, j) => trh.appendChild(theadCell(c, j)));
    const addc = h("th", "cf-data-thadd");
    const ab = h("button", "cf-data-addc", "+ colonne");
    ab.type = "button";
    on(ab, "click", addColumn);
    addc.appendChild(ab);
    trh.appendChild(addc);
    thead.appendChild(trh);
    tbl.appendChild(thead);

    const tb = h("tbody", "cf-data-tbody");
    const order = viewOrder();
    const cap = 400;
    order.slice(0, cap).forEach((r, pos) => tb.appendChild(rowEl(r, pos)));
    tbl.appendChild(tb);
    box.appendChild(tbl);
    if (order.length > cap) {
      box.appendChild(h("p", "empty-note sm",
        "Affichage limité aux " + cap + " premières lignes sur " + order.length
        + " — le deck, lui, les utilise toutes."));
    }
    REFS.tbody = tb;
    return box;
  }
  function theadCell(c, j) {
    const th = h("th", "cf-data-th");
    th.dataset.c = String(j);
    const top = h("div", "cf-data-thead");
    const nm = h("input", "cf-data-cname");
    nm.type = "text"; nm.value = c; nm.title = "Renommer la colonne";
    on(nm, "change", () => renameColumn(j, nm.value));
    top.appendChild(nm);
    const keys = sortKeys();
    const cur = keys.filter((k) => fold(k.name) === fold(c))[0];
    const sb = h("button", "cf-data-sortb" + (cur ? " on" : ""),
      cur ? (cur.desc ? "&#9660;" : "&#9650;") : "&#8693;");
    sb.type = "button";
    sb.title = "Trier le deck sur cette colonne";
    on(sb, "click", () => cycleSort(c));
    top.appendChild(sb);
    const qb = h("button", "cf-data-qb" + (T.qty_col === c ? " on" : ""), "&times;n");
    qb.type = "button";
    qb.title = "Utiliser cette colonne comme quantité";
    on(qb, "click", () => {
      pushUndo();
      T.qty_col = (T.qty_col === c) ? null : c;
      commit(); render(); schedule(0);
    });
    top.appendChild(qb);
    const db = h("button", "cf-data-delc", "&times;");
    db.type = "button"; db.title = "Supprimer la colonne";
    on(db, "click", () => delColumn(j));
    top.appendChild(db);
    th.appendChild(top);

    /* LE MENU PAR COLONNE — c'est lui qu'on compare a l'editeur de script de
       la barre. Il liste les slots REELS de doc.type.slots. */
    const sel = h("select", "cf-data-hsel");
    const o0 = document.createElement("option");
    o0.value = ""; o0.textContent = "— non utilisée";
    sel.appendChild(o0);
    const gs = document.createElement("optgroup");
    gs.label = SLOTS_ARE_DEFAULT ? "Slots (par défaut)" : "Slots de la carte (pièce 03)";
    slots().forEach((s) => {
      const o = document.createElement("option");
      o.value = s.id; o.textContent = s.label;
      if (T.map[c] === s.id) o.selected = true;
      gs.appendChild(o);
    });
    sel.appendChild(gs);
    const gr = document.createElement("optgroup");
    gr.label = "Champs réservés";
    RESERVED.forEach((s) => {
      const o = document.createElement("option");
      o.value = s.id; o.textContent = s.label;
      if (T.map[c] === s.id) o.selected = true;
      gr.appendChild(o);
    });
    sel.appendChild(gr);
    on(sel, "change", () => setMap(c, sel.value));
    th.appendChild(sel);
    return th;
  }
  function rowEl(r, pos) {
    const tr = h("tr", "cf-data-tr");
    tr.dataset.r = String(r);
    const tn = h("td", "cf-data-tdn");
    const lab = h("label", "cf-data-onoff");
    const ck = h("input", "");
    ck.type = "checkbox";
    ck.checked = T.off.indexOf(r) < 0;
    ck.title = "Activer / désactiver cette ligne";
    on(ck, "change", () => {
      pushUndo();
      const k = T.off.indexOf(r);
      if (ck.checked) { if (k >= 0) T.off.splice(k, 1); }
      else if (k < 0) T.off.push(r);
      commit(); schedule(0); paintRowFlags();
    });
    lab.appendChild(ck);
    tn.appendChild(lab);
    tn.appendChild(h("i", "cf-data-rn", String(pos + 1)));
    tn.appendChild(h("b", "cf-data-q", ""));
    tn.appendChild(h("span", "cf-data-rwhy", ""));
    tr.appendChild(tn);
    T.columns.forEach((c, j) => {
      const td = h("td", "cf-data-td");
      const inp = h("input", "cf-data-cell");
      inp.type = "text";
      const raw0 = T.rows[r][j] == null ? "" : T.rows[r][j];
      inp.value = raw0;
      inp.dataset.r = String(r);
      inp.dataset.c = String(j);
      /* UN CHAMP D'UNE LIGNE NE PEUT PAS MONTRER UN RETOUR A LA LIGNE, et il
         ne le dit pas : le DOM les retire de `value` sans un mot. « deux
         lignes :<retour>la seconde » s'affichait « deux lignes :la seconde »,
         donc la cellule montrait autre chose que la donnee — et la moindre
         edition de cette cellule aurait fait perdre le retour pour de bon.
         La donnee n'est pas touchee (l'aller-retour le prouve sur les
         octets) ; c'est l'AFFICHAGE qui doit avouer ce qu'il ne sait pas
         montrer. */
      const nNL = raw0.split(/\r\n|\r|\n/).length - 1;
      if (nNL > 0) {
        td.classList.add("nl");
        inp.title = "Cette cellule contient " + nNL + " retour(s) à la ligne "
          + "que ce champ d'une ligne ne peut pas afficher. La donnée, elle, "
          + "les garde (l'export le vérifie sur les octets) — mais si vous "
          + "modifiez cette cellule ici, ils seront perdus.";
        td.appendChild(h("i", "cf-data-nl", "&#9166;"));
      }
      on(inp, "change", () => {
        if (T.rows[r][j] === inp.value) return;
        pushUndo();
        T.rows[r][j] = inp.value;
        if (nNL > 0) {
          M.toast("les " + nNL + " retour(s) à la ligne de cette cellule sont "
            + "perdus : un champ d'une ligne ne sait pas les rendre "
            + "(Ctrl+Z annule)", true);
        }
        commit(); schedule();
      });
      on(inp, "keydown", cellKey);
      td.appendChild(inp);
      if (T.map[c] === "art") {
        td.classList.add("cf-data-tdart");
        if (T.rows[r][j]) td.classList.add("art");
        td.appendChild(h("i", "cf-data-artdot", ""));
      }
      tr.appendChild(td);
    });
    const tx = h("td", "cf-data-tdx");
    const xb = h("button", "cf-data-delr", "&times;");
    xb.type = "button"; xb.title = "Supprimer la ligne";
    on(xb, "click", () => delRow(r));
    tx.appendChild(xb);
    tr.appendChild(tx);
    on(tr, "dblclick", (e) => {
      if (e.target && e.target.tagName === "INPUT" && e.target.type === "text") return;
      focusRow(r);
    });
    return tr;
  }
  function cellKey(e) {
    const t = e.target;
    const r = Number(t.dataset.r), c = Number(t.dataset.c);
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const nx = HOST.querySelector('.cf-data-cell[data-r="' + (r + 1) + '"][data-c="' + c + '"]');
      if (nx) { nx.focus(); nx.select(); } else { addRow(); }
      return;
    }
    if (e.key === "Enter" && e.shiftKey) {
      e.preventDefault();
      const pv = HOST.querySelector('.cf-data-cell[data-r="' + (r - 1) + '"][data-c="' + c + '"]');
      if (pv) { pv.focus(); pv.select(); }
    }
  }
  function renderTableOnly() {
    const box = HOST ? HOST.querySelector(".cf-data-tbox") : null;
    if (!box) { render(); return; }
    const nb = buildTable();
    box.parentNode.replaceChild(nb, box);
    paintRowFlags();
  }
  function paintRowFlags() {
    if (!REFS.tbody) return;
    const st = LAST && LAST.stats;
    const q = {}, why = {};
    if (st && st.kept_rows) st.kept_rows.forEach((k) => { q[k.r] = (q[k.r] || 0) + k.q; });
    if (st && st.rejected) st.rejected.forEach((k) => { why[k.r] = k.why || ""; });
    Array.prototype.forEach.call(REFS.tbody.querySelectorAll("tr"), (tr) => {
      const r = Number(tr.dataset.r);
      const dis = T.off.indexOf(r) >= 0;
      const kept = !!q[r];
      tr.classList.toggle("off", dis);
      tr.classList.toggle("out", !dis && !!st && !kept);
      const b = tr.querySelector(".cf-data-q");
      if (b) {
        b.textContent = kept ? ("×" + q[r]) : (dis ? "off" : (st ? "—" : ""));
        b.className = "cf-data-q" + (kept && q[r] > 1 ? " many" : "");
      }
      /* DEUX ETATS CONTRADICTOIRES POUR UNE MEME LIGNE, C'ETAIT LE REPROCHE :
         la case restait cochee ET la ligne barree, on ne savait plus si on
         l'avait desactivee ou si le filtre l'avait exclue. Ici la case
         n'exprime QUE l'activation, et l'exclusion par le filtre porte son
         propre marqueur — avec la CONDITION qui l'a rejetee. */
      const f = tr.querySelector(".cf-data-rwhy");
      if (f) {
        if (dis) {
          f.textContent = "désactivée ici";
          f.className = "cf-data-rwhy off";
          f.title = "Cette ligne est décochée : ni filtre ni quantité ne sont en cause.";
        } else if (st && !kept) {
          const w = why[r] || (T.filter.trim() || "quantité 0");
          f.textContent = "✕ " + w;
          f.className = "cf-data-rwhy out";
          f.title = "Écartée par cette condition du filtre" + (why[r] ? "" : " (ou quantité 0)")
            + " — la case ci-contre reste cochée : elle ne dit que l'activation manuelle.";
        } else {
          f.textContent = "";
          f.className = "cf-data-rwhy";
          f.title = "";
        }
      }
    });
  }
  /* ── LA COLONNE IMAGE, RESOLUE VERS LA BIBLIOTHEQUE ───────────────────────
     Livrable de la spec de cette piece, et il n'etait visible nulle part :
     mapper une colonne sur « Illustration » ne faisait que passer une chaine.
     On decouvrait au tirage que 40 cartes sur 200 pointaient un fichier
     absent. Ici chaque valeur est confrontee au dossier d'images de
     l'application, et la cellule fautive porte un point rouge. */
  function artColumn() {
    const k = Object.keys(T.map);
    for (let i = 0; i < k.length; i++) {
      if (T.map[k[i]] === "art" && T.columns.indexOf(k[i]) >= 0) return k[i];
    }
    return "";
  }
  async function checkArt() {
    const col = artColumn();
    if (!col) { ART = null; paintArt(); return; }
    const j = T.columns.indexOf(col);
    const vals = T.rows.map((r) => String(r[j] == null ? "" : r[j]));
    const seq = ++ARTSEQ;
    try {
      /* TOUTES LES VALEURS, PAS LES 2000 PREMIERES. La coupe silencieuse
         faisait dire « 4 sur 4 » a un compteur qui n'avait regarde qu'un
         morceau de la table : sur 2400 lignes, les 400 dernieres n'etaient
         jamais verifiees et rien ne le disait. Le moteur borne a MAX_ROWS,
         qui est aussi la borne de la table elle-meme. */
      const r = await M.api.post("artcheck", { values: vals });
      if (seq !== ARTSEQ) return;
      ART = r || null;
    } catch (e) { ART = null; }
    paintArt();
  }
  function paintArt() {
    if (!REFS.tbody) return;
    const col = artColumn();
    const j = col ? T.columns.indexOf(col) : -1;
    const map = {};
    if (ART && ART.art) {
      const jj = j;
      T.rows.forEach((r, i) => {
        const it = ART.art[i];
        if (it) map[i + "|" + jj] = it;
      });
    }
    Array.prototype.forEach.call(REFS.tbody.querySelectorAll(".cf-data-tdart"), (td) => {
      const inp = td.querySelector(".cf-data-cell");
      if (!inp) return;
      const it = map[inp.dataset.r + "|" + inp.dataset.c];
      const dot = td.querySelector(".cf-data-artdot");
      td.classList.remove("ok", "miss");
      if (!dot) return;
      if (!it || !it.v) { dot.textContent = ""; dot.title = ""; return; }
      if (it.ok) {
        td.classList.add("ok");
        dot.textContent = "●";
        dot.title = "Trouvée : " + it.url + (it.why ? " — " + it.why : "");
      } else {
        td.classList.add("miss");
        dot.textContent = "●";
        dot.title = "INTROUVABLE"
          + (it.why ? " — " + it.why : "") + (ART ? " · dossier " + ART.folder : "");
      }
    });
    /* le compte, dans le bandeau : « 3 images sur 4 » ne se devine pas au point rouge */
    const box = REFS.artline;
    if (box) {
      if (!col || !ART) { box.textContent = ""; box.className = "cf-data-artline"; return; }
      box.className = "cf-data-artline" + (ART.n_missing ? " bad" : " ok");
      /* LE DENOMINATEUR EST ECRIT, ET LA BIBLIOTHEQUE AUSSI : « 4 sur 4 »
         seul est un compteur, pas une preuve — on ne sait ni sur quoi il a
         cherche ni ce qu'il fait quand ca manque. Les deux manquent ici. */
      /* LE DENOMINATEUR EST UN NOMBRE DE FICHIERS. Il comptait des noms
         REPLIES : deux fichiers ne differant que par la casse — impossibles
         sous Windows, courants sur le disque ext4 de l'imprimeur — n'en
         faisaient qu'un, et le bandeau annoncait 115 pour 116. */
      const clash = (ART.n_names != null && ART.n_files != null
        && ART.n_files > ART.n_names)
        ? (" · " + (ART.n_files - ART.n_names) + " ne se distingue(nt) que par "
          + "la casse : un seul est atteignable par son nom")
        : "";
      box.innerHTML = "Colonne <code>" + esc(col)
        + "</code> résolue vers la bibliothèque d'images (<b>"
        + (ART.n_files == null ? "?" : ART.n_files) + "</b> fichier(s)"
        + clash + ") : <b>"
        + ART.n_ok + "</b> sur <b>" + ART.n + "</b> valeur(s) nommée(s)"
        + (ART.n_case ? (" · <b>" + ART.n_case + "</b> trouvée(s) à la casse "
          + "près (l'URL porte le nom réel du fichier)") : "")
        + (ART.n_missing ? (" — <b>" + ART.n_missing + " introuvable(s)</b>,"
          + " point rouge dans la table, la raison en infobulle") : "");
    }
  }

  function focusRow(r) {
    if (!LAST || !LAST.cards) { M.toast("construisez d'abord le deck", true); return; }
    let k = -1;
    for (let i = 0; i < LAST.cards.length; i++) if (LAST.cards[i].row === r) { k = i; break; }
    if (k < 0) { M.toast("cette ligne ne produit aucune carte (filtre, quantité 0 ou ligne désactivée)", true); return; }
    focusCard(k);
    M.toast("aperçu de la carte " + (k + 1) + " / " + CF.cards().length);
  }
  /* On pilote les BOUTONS du CORE, pas son etat interne : c'est la seule
     facon publique de deplacer l'apercu, et les invalidations se coalescent
     sur une frame — 200 clics ne font qu'un rendu. */
  function focusCard(i) {
    const n = CF.cards().length;
    const t = Math.max(0, Math.min(n - 1, i | 0));
    const nb = document.querySelector("#nextBtn"), pb = document.querySelector("#prevBtn");
    if (!nb || !pb) return;
    let guard = 0;
    while (CF.current() < t && guard++ < 5000) nb.click();
    while (CF.current() > t && guard++ < 5000) pb.click();
  }

  /* ── mutations de structure ────────────────────────────────────────────── */
  function addRow() {
    pushUndo();
    T.rows.push(T.columns.map(() => ""));
    commit(); renderTableOnly(); schedule(0);
    const last = T.rows.length - 1;
    const c = HOST.querySelector('.cf-data-cell[data-r="' + last + '"][data-c="0"]');
    if (c) c.focus();
  }
  function delRow(r) {
    pushUndo();
    T.rows.splice(r, 1);
    T.off = T.off.filter((x) => x !== r).map((x) => (x > r ? x - 1 : x));
    commit(); renderTableOnly(); schedule(0);
  }
  function addColumn() {
    pushUndo();
    let n = "col" + (T.columns.length + 1), k = 1;
    while (T.columns.map(fold).indexOf(fold(n)) >= 0) n = "col" + (T.columns.length + 1 + k++);
    T.columns.push(n);
    T.rows.forEach((r) => r.push(""));
    commit(); render(); schedule(0); resuggest();
  }
  function delColumn(j) {
    const nm = T.columns[j];
    pushUndo();
    T.columns.splice(j, 1);
    T.rows.forEach((r) => r.splice(j, 1));
    delete T.map[nm];
    if (T.qty_col === nm) T.qty_col = null;
    commit(); render(); schedule(0); resuggest();
  }
  function renameColumn(j, raw) {
    const nm = String(raw || "").trim();
    if (!nm || nm === T.columns[j]) { render(); return; }
    if (T.columns.map(fold).indexOf(fold(nm)) >= 0) {
      M.toast("une colonne porte déjà ce nom", true); render(); return;
    }
    pushUndo();
    const old = T.columns[j];
    T.columns[j] = nm;
    if (T.map[old]) { T.map[nm] = T.map[old]; delete T.map[old]; }
    if (T.qty_col === old) T.qty_col = nm;
    commit(); render(); schedule(0); resuggest();
  }
  function cycleSort(c) {
    const keys = sortKeys();
    const cur = keys.filter((k) => fold(k.name) === fold(c))[0];
    pushUndo();
    if (!cur) T.sort = c;
    else if (!cur.desc) T.sort = c + " desc";
    else T.sort = "";
    commit(); render(); schedule(0);
  }

  /* ── pied : export, appliquer, annuler ─────────────────────────────────── */
  function buildFoot() {
    const f = h("div", "cf-data-foot");
    const bar = h("div", "cf-data-brow");
    const mk = (cls, txt, title, fn) => {
      const b = h("button", cls, txt);
      b.type = "button";
      if (title) b.title = title;
      on(b, "click", fn);
      bar.appendChild(b);
      return b;
    };
    mk("btn sm cf-data-b", "+ ligne", "Alt + N", addRow);
    mk("btn sm cf-data-b", "Tout activer", "Réactive toutes les lignes", () => {
      pushUndo(); T.off = []; commit(); renderTableOnly(); schedule(0);
    });
    mk("btn sm cf-data-b", "Inverser", "Inverse l'activation de chaque ligne", () => {
      pushUndo();
      const all = T.rows.map((r, i) => i);
      T.off = all.filter((i) => T.off.indexOf(i) < 0);
      commit(); renderTableOnly(); schedule(0);
    });
    REFS.undo = mk("btn sm cf-data-b", "Annuler", "Ctrl + Z", undo);
    REFS.redo = mk("btn sm cf-data-b", "Rétablir", "Ctrl + Maj + Z", redo);
    bar.appendChild(h("span", "tb-spacer"));
    /* LE BOM EST UN CHOIX AFFICHE, PLUS UNE DECISION CACHEE DANS UN BOUTON.
       Il aide Excel et il gene un parseur naif (la premiere colonne ressort
       « ﻿nom ») : c'est exactement le genre d'arbitrage qui appartient a
       celui qui recevra le fichier, pas a nous. */
    const bl = h("label", "cf-data-bom");
    const bk = h("input", "");
    bk.type = "checkbox"; bk.checked = BOM;
    on(bk, "change", () => { BOM = bk.checked; paintBom(); });
    bl.appendChild(bk);
    bl.appendChild(h("span", "cf-data-bomt", ""));
    /* CETTE INFOBULLE PROMETTAIT « le fichier rendu est l'octet pour octet de
       celui qu'on a importé ». C'ETAIT FAUX SUR QUATRE DES SIX JEUX que cet
       écran propose lui-même : un fichier lu en Windows-1252 ressort en UTF-8
       (205 octets entrent, 226 sortent), un fichier à BOM ressort sans lui
       (213 -> 210), un classeur ressort en CSV. La promesse est remplacée par
       une MESURE, faite après chaque export sur les deux suites d'octets. */
    bl.title = "Cochée, cette case ajoute exactement 3 octets EF BB BF en tête, "
      + "pour qu'Excel ouvre les accents. Aucune promesse n'est faite ici sur "
      + "l'identité aux octets importés : elle est mesurée à chaque export et "
      + "écrite en clair sous cette barre, divergence et position comprises.";
    bar.appendChild(bl);
    REFS.bom = bl;
    /* DEUX FICHIERS, DONC DEUX BOUTONS. « Exporter le CSV » rendait la table
       SOURCE — 4 lignes, la ligne ecartee par le filtre comprise, la colonne
       qty non resolue — et le livrable de la spec est « export CSV du DECK ».
       Un seul bouton pour deux fichiers differents, c'etait la moitie du
       livrable presentee comme le tout. */
    mk("btn sm cf-data-b", "Exporter la table source",
      "La table telle qu'elle est ici. Relue, elle rend la même table — "
      + "l'aller-retour est vérifié sur les octets rendus.",
      () => exportCsv("table"));
    REFS.expdeck = mk("btn strong sm cf-data-b", "Exporter le deck",
      "Une ligne PAR CARTE : filtre, tri et quantités appliqués.",
      () => exportCsv("deck"));
    mk("btn strong sm cf-data-b", "Reconstruire", "Ctrl + Entrée", () => schedule(0));
    f.appendChild(bar);
    const prf = h("p", "cf-data-proof", "");
    f.appendChild(prf);
    REFS.proof = prf;
    const art = h("p", "cf-data-artline", "");
    f.appendChild(art);
    REFS.artline = art;
    f.appendChild(h("p", "hint cf-data-keys",
      "<b>Ctrl+Z</b> annuler · <b>Ctrl+Maj+Z</b> rétablir · <b>Entrée</b> cellule suivante · "
      + "<b>Alt+N</b> nouvelle ligne · <b>Ctrl+Entrée</b> reconstruire · <b>double-clic</b> sur une ligne = "
      + "aperçu de sa carte · <b>Ctrl+V</b> colle une table"));
    paintBom();
    return f;
  }
  function paintBom() {
    const l = REFS.bom;
    if (!l) return;
    const t = l.querySelector(".cf-data-bomt");
    if (t) {
      /* CE QUE LA CASE FAIT, ET RIEN DE PLUS. « sans BOM — octet pour octet »
         affirmait un resultat que rien ne mesurait, et que la mesure dement
         sur quatre des six jeux embarques. Une case a cocher decrit son geste ;
         le resultat, lui, s'affiche apres l'export. */
      t.textContent = BOM
        ? "BOM pour Excel — +3 octets EF BB BF en tête"
        : "sans BOM (le défaut)";
    }
    l.className = "cf-data-bom" + (BOM ? " on" : "");
  }
  /* ── EXPORT, ET LA PREUVE QUI VA AVEC ──────────────────────────────────────
     « Aller-retour : ce fichier relu rend la même table » etait une PROMESSE
     ecrite dans une infobulle. Ici elle est MESUREE, sur les octets que le
     backend vient de rendre : on relit le blob livre par le meme /parse que
     n'importe quel fichier depose, et on compare cellule par cellule. Si ca
     diverge, on l'ecrit, avec la position. Une promesse invérifiable vaut
     moins que pas de promesse. */
  async function exportCsv(scope) {
    if (!T.columns.length) { M.toast("rien à exporter", true); return; }
    const deck = (scope === "deck");
    if (deck && !(LAST && LAST.cards && LAST.cards.length)) {
      M.toast("construisez d'abord le deck", true); return;
    }
    const nm = String((CF.doc().name || "deck")).replace(/[^\w\-]+/g, "_") || "deck";
    try {
      M.busy(true, deck ? "export du deck…" : "export de la table…");
      /* un classeur n'a pas de separateur : on ecrit en point-virgule et on
         le DIT dans le message, plutot que de reprendre un reglage inexistant */
      const sep = (T.sep && T.sep !== "auto" && SEPS.some((s) => s.v === T.sep)) ? T.sep : ";";
      const body = {
        columns: T.columns, rows: T.rows, sep: sep, bom: BOM, name: nm,
        scope: deck ? "deck" : "table",
      };
      if (deck) {
        /* le deck est RECONSTRUIT par le moteur a partir des memes entrees que
           /build — jamais renvoye tout fait par l'ecran. Deux chemins de
           construction, ce serait deux decks qui divergent en silence. */
        body.map = T.map; body.qty_col = T.qty_col;
        body.filter = T.filter; body.sort = T.sort; body.off = T.off;
        body.slots = slotPayload(); body.blank_unfed = BLANKMODE;
      }
      const b = await M.api.blob("POST", "export", body);
      const buf = await b.arrayBuffer();
      /* ON MESURE AVANT DE LIVRER, ET ON L'AFFICHE AVANT DE LIVRER : si la
         remise du fichier echoue, la preuve deja obtenue reste a l'ecran au
         lieu de disparaitre avec l'exception. */
      LASTEXPORT = await verifyRoundTrip(buf, deck, sep);
      paintProof(); paintMeter();
      M.download(b, nm + (deck ? "_deck" : "") + (sep === "\t" ? ".tsv" : ".csv"));
      M.toast(LASTEXPORT.toast, !LASTEXPORT.ok);
    } catch (e) {
      M.toast(String((e && e.message) || e), true);
    } finally { M.busy(false); }
  }
  /* ═══ LA COMPARAISON AUX OCTETS D'ORIGINE ══════════════════════════════════
     Trois etats, et aucun n'est une promesse : identique (et on dit sur
     combien d'octets), different (et on dit OU, et pourquoi, avec des raisons
     toutes mesurees), ou pas comparable (et on dit pourquoi ce n'est pas
     comparable plutot que de se taire). */
  function countByte(u, b) {
    let n = 0;
    for (let i = 0; i < u.length; i++) if (u[i] === b) n++;
    return n;
  }
  function compareToSource(buf, bom) {
    if (!SRC || !SRC.bytes) {
      return { state: "absent", txt: "octets d'origine absents (table saisie "
        + "ici, ou page rechargée depuis l'import) : il n'y a rien à comparer" };
    }
    if (SRCDIRTY) {
      return { state: "dirty", txt: "la table a changé depuis l'import de « "
        + SRC.name + " » : la comparer aux octets d'origine ne voudrait rien dire" };
    }
    const a = SRC.bytes, b = new Uint8Array(buf);
    const n = Math.min(a.length, b.length);
    let at = -1;
    for (let i = 0; i < n; i++) { if (a[i] !== b[i]) { at = i; break; } }
    if (at < 0 && a.length !== b.length) at = n;
    if (at < 0) {
      return { state: "same", at: -1, txt: "identique aux " + a.length
        + " octets importés — comparés un par un, aucune divergence" };
    }
    /* les raisons sont MESUREES, pas devinees : l'encodage vient du moteur,
       les guillemets se comptent, les valeurs perdues aussi. */
    const why = [];
    if (bom) why.push("3 octets de BOM ajoutés en tête (case cochée)");
    if (SRC.wb) why.push("l'entrée est un classeur (une archive), la sortie un CSV");
    else if (SRC.enc && SRC.enc !== "utf-8") {
      why.push("l'entrée était en " + SRC.encLabel + ", la sortie s'écrit en UTF-8");
    }
    if (SRC.lost) {
      why.push(SRC.lost + " valeur(s) écartée(s) à la lecture (ligne(s) à "
        + "colonnes en trop) : elles ne peuvent pas ressortir");
    }
    const qa = countByte(a, 34), qb = countByte(b, 34);
    if (qa !== qb) {
      why.push(qa + " guillemet(s) en entrée contre " + qb + " en sortie "
        + "(la citation est remise au strict nécessaire)");
    }
    return { state: "diff", at: at, txt: b.length + " octets rendus contre "
      + a.length + " importés · première différence à l'octet " + at
      + (why.length ? " — " + why.join(" · ") : "") };
  }

  /* La verification passe par le MOTEUR (/parse), pas par un decodeur ecrit a
     cote : relire avec un second parseur ne prouverait que l'accord de deux
     bugs. On mesure les octets, on relit, on compare. */
  async function verifyRoundTrip(buf, deck, sep) {
    const n = buf.byteLength;
    const u = new Uint8Array(buf);
    const bom = (u.length > 2 && u[0] === 0xEF && u[1] === 0xBB && u[2] === 0xBF);
    const octets = n + " octet(s)" + (bom ? " dont 3 de BOM" : ", sans BOM");
    /* le DECK n'est pas la table d'entree : une ligne par carte, filtre, tri et
       quantites appliques. Le comparer aux octets importes serait un chiffre
       faux de plus. */
    const src = deck
      ? { state: "na", txt: "le deck résolu n'est pas la table d'entrée "
        + "(une ligne par carte) : la comparaison aux octets importés ne "
        + "s'applique pas ici — c'est « Exporter la table source » qui la porte" }
      : compareToSource(buf, bom);
    try {
      const r = await M.api.post("parse", { b64: b64of(buf), name: "relecture" });
      const tb = r && r.table;
      if (!tb) throw new Error("relecture illisible");
      const want = deck ? null : { cols: T.columns, rows: T.rows };
      if (deck) {
        const nc = (LAST && LAST.cards) ? LAST.cards.length : 0;
        const ok = (tb.n_rows === nc);
        return {
          src: src,
          ok: ok, txt: "deck relu : " + tb.n_rows + " / " + nc + " carte(s) · " + octets,
          toast: ok
            ? (nc + " carte(s) exportée(s) et relues — " + tb.n_cols
              + " colonnes, " + octets)
            : ("relecture : " + tb.n_rows + " lignes pour " + nc + " cartes"),
          detail: "Une ligne par carte, filtre / tri / quantités appliqués. "
            + "Séparateur " + sepLabel(sep) + ".",
        };
      }
      let bad = "";
      if (tb.columns.join("") !== want.cols.join("")) {
        bad = "entêtes différentes";
      } else if (tb.rows.length !== want.rows.length) {
        bad = tb.rows.length + " lignes relues pour " + want.rows.length + " écrites";
      } else {
        for (let i = 0; i < want.rows.length && !bad; i++) {
          for (let j = 0; j < want.cols.length; j++) {
            const a = String(want.rows[i][j] == null ? "" : want.rows[i][j]);
            const c = String(tb.rows[i][j] == null ? "" : tb.rows[i][j]);
            if (a !== c) {
              bad = "ligne " + (i + 1) + ", colonne « " + tb.columns[j]
                + " » : « " + c + " » au lieu de « " + a + " »";
              break;
            }
          }
        }
      }
      return {
        src: src,
        ok: !bad,
        txt: bad ? ("aller-retour ROMPU — " + bad)
          : ("aller-retour vérifié · " + octets),
        toast: bad ? ("aller-retour ROMPU — " + bad)
          : (want.rows.length + " ligne(s) exportée(s), relues à l'identique — "
            + octets),
        detail: bad ? ""
          : (want.cols.length + " colonnes × " + want.rows.length
            + " lignes relues cellule par cellule par le même moteur "
            + "d'analyse que n'importe quel fichier déposé."),
      };
    } catch (e) {
      return { src: src, ok: false,
        txt: "aller-retour non vérifié (" + octets + ")",
        toast: "fichier écrit (" + octets + ") mais la relecture a échoué",
        detail: String((e && e.message) || e) };
    }
  }
  function paintProof() {
    const p = REFS.proof;
    if (!p) return;
    if (!LASTEXPORT) { p.innerHTML = ""; p.className = "cf-data-proof"; return; }
    p.className = "cf-data-proof " + (LASTEXPORT.ok ? "ok" : "bad");
    p.innerHTML = "<b>" + esc(LASTEXPORT.txt) + "</b> "
      + (LASTEXPORT.detail ? esc(LASTEXPORT.detail) : "");
    /* LA DEUXIEME LIGNE, CELLE QUI REMPLACE LA PROMESSE DE LA CASE A COCHER :
       le fichier livre confronte, octet par octet, a celui qu'on a importe.
       Elle porte sa propre couleur — « relu a l'identique » et « identique aux
       octets d'entree » sont deux questions differentes, et la seconde peut
       repondre non quand la premiere repond oui (un fichier lu en
       Windows-1252 ressort en UTF-8 : memes cellules, autres octets). */
    const s = LASTEXPORT.src;
    if (s && s.txt) {
      const l = h("span", "cf-data-srcmp " + (s.state === "same" ? "ok"
        : (s.state === "diff" ? "warn" : "")), "");
      l.innerHTML = "<i>octets d'origine :</i> " + esc(s.txt);
      p.appendChild(document.createElement("br"));
      p.appendChild(l);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     ENREGISTREMENT
     ═══════════════════════════════════════════════════════════════════════ */
  M = CF.register({
    id: "data",
    title: "Données",
    icon: "\u{1F4CA}",
    order: 4,

    /* Aucun z : cette piece ne dessine pas la carte. */

    /* LE SCHEMA : ces cles sont les SEULES que M.patch({...}) acceptera. */
    state: {
      columns: [],      /* entetes */
      rows: [],         /* la table brute, chaines */
      off: [],          /* index des lignes desactivees */
      map: {},          /* colonne (ou jeton #n/#N/#i/#T) -> slot */
      qty_col: null,    /* colonne de quantite (duplication) */
      filter: "",       /* expression de filtre */
      sort: "",         /* tri du deck */
      sep: "auto",      /* separateur retenu */
      enc: "auto",      /* encodage retenu */
      src: "",          /* nom du fichier d'origine */
    },

    async init(host) {
      HOST = host;
      T = loadT();

      try {
        const r = await M.api.get("samples");
        SAMPLES = (r && r.samples) || [];
      } catch (e) {
        if (e && e.missing) MISSING = true;
        SAMPLES = [];
      }
      /* les operateurs viennent du MOTEUR : l'ecran en affiche le nombre, il
         ne doit pas le recopier a la main (un badge recopie finit par mentir) */
      try {
        const r = await M.api.get("grammar");
        GRAM = (r && r.ops) ? r : null;
      } catch (e) { GRAM = null; }

      render();
      if (T.columns.length) { schedule(0); askSuggest(T.columns, T.map).then(paintAudit); }

      /* P3 publie ses slots plus tard : le menu bascule tout seul. ET LES
         PROPOSITIONS AUSSI — c'est precisement la que le mappage automatique
         se taisait : la table de synonymes de l'ecran ne connaissait que ses
         identifiants de repli, donc « pv » n'atterrissait jamais sur « Vie »
         des lors que P3 nommait ce slot « def ». */
      CF.on("core:doc", (p) => {
        if (!p) return;
        /* LE CADRE AUSSI : changer la rarete dans « 02 Cadre » change le mot
           imprime sur toutes les cartes, donc le compte des contradictions.
           Un controle qui ne se rafraichit pas devient un chiffre perime — et
           c'est tout ce qu'on corrige depuis trois tours. */
        if (p.id === "frame") { if (T.columns.length) schedule(0); return; }
        if (p.id !== "type") return;
        if (T.columns.length) askSuggest(T.columns, T.map).then(() => { render(); schedule(0); });
        else render();
      });
      /* la carte affichee change : le tableau de provenance suit. */
      CF.on("core:render", () => { if (REFS.audit) paintAudit(); });

      /* depot de fichier sur TOUT le panneau, pas seulement sur le carre */
      const over = (e) => {
        if (!e.dataTransfer || !e.dataTransfer.types) return false;
        return Array.prototype.indexOf.call(e.dataTransfer.types, "Files") >= 0;
      };
      on(host, "dragover", (e) => {
        if (!over(e)) return;
        e.preventDefault();
        if (REFS.drop) REFS.drop.classList.add("over");
      });
      on(host, "dragleave", () => { if (REFS.drop) REFS.drop.classList.remove("over"); });
      on(host, "drop", (e) => {
        if (!over(e)) return;
        e.preventDefault();
        if (REFS.drop) REFS.drop.classList.remove("over");
        const f = e.dataTransfer.files && e.dataTransfer.files[0];
        if (f) readFile(f);
      });

      /* coller une table */
      on(host, "paste", (e) => {
        const tgt = e.target;
        if (tgt && (tgt.tagName === "INPUT" || tgt.tagName === "TEXTAREA")) return;
        const txt = e.clipboardData && e.clipboardData.getData("text/plain");
        if (!txt || txt.indexOf("\n") < 0) return;
        e.preventDefault();
        LASTRAW = null;
        importText(txt, "presse-papiers");
      });

      /* raccourcis — actifs seulement quand ce panneau est a l'ecran */
      on(document, "keydown", (e) => {
        const panel = host.closest ? host.closest(".cf-panel") : null;
        if (!panel || !panel.classList.contains("on")) return;
        const k = String(e.key || "").toLowerCase();
        if ((e.ctrlKey || e.metaKey) && k === "z") {
          e.preventDefault();
          if (e.shiftKey) redo(); else undo();
        } else if ((e.ctrlKey || e.metaKey) && k === "y") {
          e.preventDefault(); redo();
        } else if ((e.ctrlKey || e.metaKey) && k === "enter") {
          e.preventDefault(); schedule(0);
        } else if (e.altKey && k === "n") {
          e.preventDefault(); if (T.columns.length) addRow();
        }
      });
    },
  });
})();
