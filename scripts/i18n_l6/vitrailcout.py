"""Suite de t224 (Menus : Réglages, 16/10/2026) — la bulle du bouton IA du panneau Vitrail (js/mod-vitrail.js) dit le
VRAI coût du moteur, comme `bulleGenerer(id)` du dialogue IA (iacout.py). Elle disait « APPEL PAYANT sur votre clé,
quelques centièmes de centime » pour TOUT moteur.

Le panneau POSTE /api/vector/illustration SANS `provider` : la route prend alors le PREMIER moteur configuré
(`dispo[0]`), celui que GET /api/vector/illustration/moteurs rend en tête. Le panneau le lit donc au chargement (moteur
et modèle par défaut), puis retient le moteur et le modèle RENDUS par chaque appel réussi. La règle est celle de
bulleGenerer : un serveur local (`ollama`, `local:<id>`) est gratuit ; un fournisseur libre (`fl:<id>`) est « prix à
mesurer », jamais « gratuit » ; les intégrés payants — et un moteur encore inconnu — gardent le texte d'avant (clé
vectorlab.vitrail.ia_titre, inchangée, déclarée ici avec ses deux sœurs ; l'entrée S de la ligne 684 de texte.py
appelle désormais bulleIA()). Éditions S sur la source de BASE, pour que la table reste réversible (test_i18n_l6 [2])."""
from outils import L, S, X, H  # noqa: F401

FV = "js/mod-vitrail.js"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


ENTREES = [
    S(FV, 565, "  async function iaLancer() {", c('''  // le moteur qu'emploie POST /vector/illustration sans `provider` : le premier de GET …/moteurs, puis celui que
  // rend chaque appel réussi — {moteur, defaut}, null tant qu'il est inconnu
  let iaMoteur = null;
  // la bulle du bouton IA dit le vrai coût de ce moteur, comme bulleGenerer (mod-ia.js) : un serveur local (ollama,
  // local:<id>) est gratuit ; un fournisseur libre (fl:<id>) est « prix à mesurer », jamais « gratuit »
  function bulleIA() {
    const id = iaMoteur ? iaMoteur.moteur : "";
    const v = { moteur: iaMoteur && iaMoteur.defaut ? `${id} · ${iaMoteur.defaut}` : id };
    if (id === "ollama" || id.startsWith("local:")) return T("vectorlab.vitrail.ia_titre_gratuit", v);
    if (id.startsWith("fl:")) return T("vectorlab.vitrail.ia_titre_a_mesurer", v);
    return T("vectorlab.vitrail.ia_titre");
  }

  async function iaLancer() {'''), {
        "vectorlab.vitrail.ia_titre": (
            "Illustration vectorielle par le modèle de langage configuré (Réglages) — APPEL PAYANT sur votre clé, "
            "quelques centièmes de centime ; pose des masses de verre en un groupe",
            "Vector illustration by the configured language model (Settings) — PAID CALL on your key, a few hundredths "
            "of a cent; places glass masses as one group"),
        "vectorlab.vitrail.ia_titre_gratuit": (
            "Illustration vectorielle par {moteur} (Réglages) — tourne sur votre machine ou votre réseau : gratuit, "
            "rien n'est débité ; pose des masses de verre en un groupe",
            "Vector illustration by {moteur} (Settings) — runs on your machine or network: free, nothing is charged; "
            "places glass masses as one group"),
        "vectorlab.vitrail.ia_titre_a_mesurer": (
            "Illustration vectorielle par {moteur} (Réglages) — appel sur votre clé, prix à mesurer : l'application ne "
            "connaît pas son tarif ; pose des masses de verre en un groupe",
            "Vector illustration by {moteur} (Settings) — call on your key, price to be measured: the app does not "
            "know its rate; places glass masses as one group"),
    }),
    S(FV, 578, "      const n = VL.iaPoser(d, q);", c('''      if (d.provider) iaMoteur = { moteur: d.provider, defaut: d.modele || "" };
      const n = VL.iaPoser(d, q);'''), {}),
    S(FV, 808, '  fetch("/api/vector/vitrail")', c('''  fetch("/api/vector/illustration/moteurs").then((r) => r.ok ? r.json() : null)
    .then((d) => {
      const m = d && Array.isArray(d.moteurs) && d.moteurs[0];
      iaMoteur = m ? { moteur: m.moteur, defaut: m.defaut || "" } : null;
      // la liste peut arriver tard (les intégrés sont interrogés au réseau) : redessiner le panneau effacerait une
      // saisie en cours — seule la bulle du bouton change (data-tip quand l'infobulle la montre déjà)
      const b = $("#vitIaGo");
      if (b) b.setAttribute(b.dataset.tip !== undefined ? "data-tip" : "title", bulleIA());
    })
    .catch(() => { /* route muette : la bulle garde le texte d'avant */ });
  fetch("/api/vector/vitrail")'''), {}),
]
