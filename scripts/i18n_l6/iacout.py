"""t224 (Menus : Réglages, 16/10/2026) — la bulle du bouton « Générer » du dialogue IA (js/mod-ia.js) dit le VRAI coût du
moteur choisi, postérieur à L6. Elle disait « APPEL PAYANT sur votre clé … — quelques centièmes de centime » pour TOUT
moteur : faux pour un serveur local (`ollama`, `local:<id>` de t223 : gratuit, comme pricing.estimate) et trompeur
pour un fournisseur libre (`fl:<id>` de t222 : tarif inconnu, « prix à mesurer », jamais « gratuit »). Les intégrés
payants (anthropic, openai, gemini) gardent le texte d'avant. L'édition est consignée ICI, en éditions S sur la source
de BASE, pour que la table reste réversible (test_i18n_l6 [2]) : la fonction bulleGenerer(id) est posée devant
rendre(), et l'entrée S de la ligne 115 (outils_lab) appelle désormais bulleGenerer(choisi) — la clé
vectorlab.ia.payant, inchangée, est déclarée ici avec ses deux sœurs."""
from outils import L, S, X, H  # noqa: F401

FI = "js/mod-ia.js"


def c(s):
    """fins de ligne de la BASE (CRLF)"""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


ENTREES = [
    S(FI, 62, "  function rendre() {", c('''  // t224 : la bulle de « Générer » dit le vrai coût du moteur — un serveur local (ollama, local:<id>) est gratuit ;
  // un fournisseur libre (fl:<id>) n'a pas de tarif connu : « prix à mesurer », jamais « gratuit »
  function bulleGenerer(id) {
    const v = { moteur: nomMoteur(id) };
    if (id === "ollama" || id.startsWith("local:")) return T("vectorlab.ia.gratuit", v);
    if (id.startsWith("fl:")) return T("vectorlab.ia.a_mesurer", v);
    return T("vectorlab.ia.payant", v);
  }

  function rendre() {'''), {
        "vectorlab.ia.payant": ("APPEL PAYANT sur votre clé {moteur} — quelques centièmes de centime",
                                "PAID CALL on your {moteur} key — a few hundredths of a cent"),
        "vectorlab.ia.gratuit": ("{moteur} tourne sur votre machine ou votre réseau — gratuit, rien n'est débité",
                                 "{moteur} runs on your machine or network — free, nothing is charged"),
        "vectorlab.ia.a_mesurer": ("Appel sur votre clé {moteur} — prix à mesurer : l'application ne connaît pas "
                                   "son tarif",
                                   "Call on your {moteur} key — price to be measured: the app does not know its rate"),
    }),
]
